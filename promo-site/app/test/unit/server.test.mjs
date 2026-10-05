import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { hashPassword, verifyPassword, needsRehash, passwordProblem, RateLimiter, safeEqual, USERNAME_RE } from '../../server/security.mjs';
import { html, raw, userText } from '../../server/html.mjs';
import { openDb, migrate, currentVersion, SCHEMA_VERSION } from '../../server/db.mjs';
import { createStore, cleanText } from '../../server/store.mjs';
import { loadConfig } from '../../server/config.mjs';
import { safeNext } from '../../server/app.mjs';
import { selectPrune } from '../../server/cli.mjs';

test('scrypt hash round-trip, unique salts, rejects wrong/malformed', async () => {
  const a = await hashPassword('correct horse battery', 16384);
  const b = await hashPassword('correct horse battery', 16384);
  assert.notEqual(a, b);
  assert.match(a, /^scrypt\$16384\$8\$1\$/);
  assert.equal(await verifyPassword('correct horse battery', a), true);
  assert.equal(await verifyPassword('correct horse batterx', a), false);
  assert.equal(await verifyPassword('x', 'garbage'), false);
  assert.equal(await verifyPassword('x', 'scrypt$999999999$8$1$AA$AA'), false);
  assert.equal(needsRehash(a, 32768), true);
  assert.equal(needsRehash(a, 16384), false);
});

test('password policy: length-based with common/username checks', () => {
  assert.ok(passwordProblem('bob', 'short'));
  assert.ok(passwordProblem('bob', 'password123'));
  assert.ok(passwordProblem('bobby', 'xxbobbyxx-long'));
  assert.ok(passwordProblem('bob', 'aaaaaaaaaaab'));
  assert.equal(passwordProblem('bob', 'dune caravan lantern'), null);
  assert.ok(passwordProblem('bob', 'x'.repeat(201)));
});

test('username pattern', () => {
  assert.ok(USERNAME_RE.test('ok_name-1'));
  for (const bad of ['ab', 'A_upper', 'with space', '<script>', 'x'.repeat(25), 'émile']) assert.ok(!USERNAME_RE.test(bad), bad);
});

test('rate limiter fixed window', () => {
  const r = new RateLimiter();
  try {
    const t = 1_000_000;
    for (let i = 0; i < 3; i++) assert.equal(r.hit('k', 3, 1000, t).ok, true);
    const blocked = r.hit('k', 3, 1000, t + 10);
    assert.equal(blocked.ok, false);
    assert.ok(blocked.retryAfter >= 1);
    assert.equal(r.hit('k', 3, 1000, t + 1001).ok, true);
    r.sweep(t + 5000);
    assert.equal(r.buckets.size, 0);
  } finally { r.close(); }
});

test('safeEqual', () => {
  assert.equal(safeEqual('abc', 'abc'), true);
  assert.equal(safeEqual('abc', 'abd'), false);
  assert.equal(safeEqual('abc', 'abcd'), false);
});

test('html template escapes interpolations; raw only when explicit', () => {
  const evil = `<img src=x onerror="alert(1)">'&`;
  assert.equal(String(html`<p title="${evil}">${evil}</p>`), '<p title="&lt;img src=x onerror=&quot;alert(1)&quot;&gt;&#39;&amp;">&lt;img src=x onerror=&quot;alert(1)&quot;&gt;&#39;&amp;</p>');
  assert.equal(String(html`${raw('<b>')}`), '<b>');
  assert.equal(String(userText('a<b>\nc\n\nd')), '<p>a&lt;b&gt;<br>c</p><p>d</p>');
});

test('cleanText strips control and bidi characters', () => {
  assert.equal(cleanText(' a\u0000b\u202Ec\r\n\r\n\r\n\r\nd\u200B '), 'abc\n\nd');
});

test('safeNext only allows known local paths', () => {
  assert.equal(safeNext('/discuss/world'), '/discuss/world');
  assert.equal(safeNext('/account'), '/account');
  for (const bad of ['//evil.com', 'https://evil.com', '/\\evil', '/discuss/../x', '/discuss?x=1', 'javascript:alert(1)', '/moderation']) assert.equal(safeNext(bad), '', bad);
});

test('config refuses unsafe settings', () => {
  const base = { ASHFALL_PUBLIC_ORIGIN: 'https://ashfall.teknetik.co', ASHFALL_DB_PATH: '/tmp/x.sqlite' };
  assert.equal(loadConfig(base).host, '127.0.0.1');
  assert.equal(loadConfig(base).port, 3187);
  assert.throws(() => loadConfig({ ...base, ASHFALL_PUBLIC_ORIGIN: 'http://ashfall.teknetik.co' }));
  assert.throws(() => loadConfig({ ...base, ASHFALL_HOST: '0.0.0.0' }));
  assert.throws(() => loadConfig({ ASHFALL_PUBLIC_ORIGIN: base.ASHFALL_PUBLIC_ORIGIN }));
  assert.throws(() => loadConfig({ ...base, ASHFALL_SCRYPT_N: '1024' }));
  assert.throws(() => loadConfig({ ...base, ASHFALL_SIGNUP_INVITE_CODE: 'short' }));
});

test('migrations are idempotent and record versions; newer DB refused', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ashfall-unit-'));
  try {
    const f = path.join(dir, 'db.sqlite');
    const db = openDb(f, { topics: ['world'] });
    assert.equal(currentVersion(db), SCHEMA_VERSION);
    assert.deepEqual(migrate(db), []);
    assert.equal((fs.statSync(f).mode & 0o777), 0o600);
    db.prepare('INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)').run(999, 'future', 0);
    assert.throws(() => migrate(db), /newer/);
    db.close();
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('store: ownership-preserving deletes and account erasure', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ashfall-unit-'));
  try {
    const db = openDb(path.join(dir, 'db.sqlite'), { topics: ['world', 'ward'] });
    const s = createStore(db);
    const a = s.createUser('alice_t', 'scrypt$x');
    const b = s.createUser('bob_t', 'scrypt$x');
    const p1 = s.createPost({ topic: 'world', userId: a, type: 'idea', body: 'alice idea one' });
    const r1 = s.createPost({ topic: 'world', userId: b, parentId: p1, type: 'reply', body: 'bob reply' });
    const p2 = s.createPost({ topic: 'world', userId: a, type: 'feedback', body: 'alice feedback' });
    s.togglePostLike(b, p1);
    assert.equal(s.topicPosts('world', 'new', 20).posts.find((p) => p.id === p1).likes, 1);
    assert.equal(s.toggleTopicLike(a, 'world'), true);
    assert.equal(s.toggleTopicLike(a, 'world'), false);
    s.deleteAccount(a);
    // p1 has a live reply: becomes an anonymous, empty placeholder. p2 is gone.
    const ph = s.post(p1);
    assert.equal(ph.body, '');
    assert.equal(ph.user_id, null);
    assert.ok(ph.deleted_at);
    assert.equal(s.post(p2), undefined);
    assert.equal(s.findUser('alice_t'), undefined);
    assert.ok(!JSON.stringify(db.prepare('SELECT * FROM posts').all()).includes('alice'));
    // When the reply goes, the placeholder is cleaned up.
    s.deletePost(r1);
    assert.equal(s.post(p1), undefined);
    db.close();
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('backup retention keeps 7 daily + 4 weekly', () => {
  const files = [];
  for (let d = 1; d <= 40; d++) {
    const dt = new Date(Date.UTC(2026, 9, 1) + d * 86400000);
    files.push(`community-${dt.toISOString().slice(0, 10).replace(/-/g, '')}T030000Z.sqlite`);
  }
  const prune = selectPrune(files, 7, 4);
  const kept = files.filter((f) => !prune.includes(f));
  assert.ok(kept.length >= 7 && kept.length <= 11, String(kept.length));
  for (const f of [...files].sort().slice(-7)) assert.ok(kept.includes(f));
});
