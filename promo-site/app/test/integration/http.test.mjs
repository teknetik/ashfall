import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { execFileSync } from 'node:child_process';
import { startServer, Client, genUser, cli, APP } from '../helpers.mjs';

let s;
before(async () => { s = await startServer(); });
after(async () => { await s.stop(); s.cleanup(); });

const csrfOf = (body) => (/name="_csrf" value="([^"]+)"/.exec(body) || [])[1];

test('public pages, health, security headers, host guard', async () => {
  const c = new Client(s);
  for (const p of ['/', '/gallery', '/development', '/about', '/privacy', '/discuss', '/discuss/world']) {
    const r = await c.get(p);
    assert.equal(r.status, 200, p);
    assert.match(r.headers['content-security-policy'], /script-src 'self'/);
    assert.equal(r.headers['x-content-type-options'], 'nosniff');
    assert.equal(r.headers['set-cookie'], undefined, `reading ${p} must not set cookies`);
  }
  const h = JSON.parse((await c.get('/api/health')).body);
  assert.equal(h.status, 'ok');
  assert.equal((await c.get('/', { headers: { Host: 'evil.example' } })).status, 421);
  for (const p of ['/assets/manifest.json', '/content.json', '/../content/WEBSITE_COPY.md', '/originals/ashfall-ward-hero.png', '/community.sqlite', '/img/../content.json']) {
    assert.equal((await c.get(p)).status, 404, p);
  }
});

test('development log: chart, timeline, labelled captures and concept pairs', async () => {
  const b = (await new Client(s).get('/development')).body;
  assert.match(b, /<h1>[^<]+<\/h1>/);
  assert.match(b, /<svg class="chart"[^>]*role="img"/);
  assert.ok((b.match(/class="timeline__item/g) || []).length >= 3, 'timeline entries');
  assert.ok((b.match(/class="pair reveal"/g) || []).length >= 1, 'concept-to-build pairs');
  // Every figure shows its concept or in-build label, so captures are never mistaken for concept art or vice versa.
  const figs = b.split('<figure class="fig"').slice(1).map((f) => f.slice(0, f.indexOf('</figure>')));
  assert.ok(figs.length >= 10, `figures (${figs.length})`);
  for (const f of figs) assert.match(f, /class="badge badge--(concept|build)"/);
  assert.ok(!/ style="/.test(b), 'no inline style attributes under the strict CSP');
  assert.match(b, /<a href="\/development" aria-current="page">/);
});

test('signup -> post -> logout -> login; secure cookie flags', async () => {
  const c = new Client(s);
  const u = genUser();
  const r = await c.join(u);
  assert.equal(r.status, 303);
  const sc = c.setCookies.find((x) => x.startsWith('__Host-ashfall_session='));
  assert.match(sc, /; Secure/); assert.match(sc, /HttpOnly/); assert.match(sc, /SameSite=Lax/); assert.match(sc, /Path=\//);
  assert.ok(!/Domain=/i.test(sc));
  const t = csrfOf((await c.get('/discuss/ward')).body);
  const p = await c.post('/discuss/ward/posts', { _csrf: t, type: 'feedback', tag: 'art', body: 'The market lane reads beautifully.' });
  assert.equal(p.status, 303);
  assert.match((await c.get('/discuss/ward')).body, /The market lane reads beautifully\./);
  await c.post('/logout', { _csrf: t });
  assert.equal((await c.get('/account')).status, 303);
  const bad = await c.login({ ...u, password: 'wrong-password-123' });
  assert.equal(bad.status, 401);
  assert.equal((await c.login(u)).status, 303);
  assert.equal((await c.get('/account')).status, 200);
});

test('unauthenticated posting is denied; CSRF and origin enforced', async () => {
  const anon = new Client(s);
  const r = await anon.post('/discuss/world/posts', { type: 'idea', body: 'anon attempt at posting' });
  assert.equal(r.status, 403); // no CSRF token
  const c = new Client(s);
  await c.join(genUser());
  const t = csrfOf((await c.get('/discuss/world')).body);
  assert.equal((await c.post('/discuss/world/posts', { _csrf: 'forged-token-forged-token', type: 'idea', body: 'forged token post' })).status, 403);
  assert.equal((await c.post('/discuss/world/posts', { _csrf: t, type: 'idea', body: 'cross origin post' }, { origin: 'https://evil.example' })).status, 403);
  assert.equal((await c.post('/discuss/world/posts', { _csrf: t, type: 'idea', body: 'no origin post here' }, { origin: null })).status, 403);
  assert.equal((await c.post('/discuss/world/posts', { _csrf: t, type: 'idea', body: 'cross site fetch meta' }, { headers: { 'Sec-Fetch-Site': 'cross-site' } })).status, 403);
  assert.equal((await c.request('POST', '/discuss/world/posts', { body: '{"x":1}', headers: { 'Content-Type': 'application/json' } })).status, 415);
  assert.equal((await c.post('/discuss/world/posts', { _csrf: t, type: 'idea', body: 'x'.repeat(20000) })).status, 413);
  assert.equal((await c.post('/discuss/world/posts', { _csrf: t, type: 'idea', body: 'short' })).status, 400);
  assert.equal((await c.post('/discuss/world/posts', { _csrf: t, type: 'admin', body: 'invalid type here' })).status, 400);
  assert.equal((await c.post('/discuss/nope/posts', { _csrf: t, type: 'idea', body: 'unknown topic post' })).status, 404);
});

test('stored XSS is escaped everywhere it renders', async () => {
  const c = new Client(s);
  await c.join(genUser());
  const t = csrfOf((await c.get('/discuss/general')).body);
  const payload = '<script>alert(1)</script><img src=x onerror=alert(2)> "quoted" \'single\'';
  await c.post('/discuss/general/posts', { _csrf: t, type: 'idea', body: payload });
  for (const p of ['/discuss/general', '/', '/account']) {
    const b = (await c.get(p)).body;
    assert.ok(!b.includes('<script>alert(1)'), p);
    assert.ok(!b.includes('<img src=x'), p);
    assert.ok(b.includes('&lt;script&gt;alert(1)&lt;/script&gt;') || p === '/', p);
  }
});

test('ownership: others cannot edit/delete; owner can; reply + likes', async () => {
  const a = new Client(s); await a.join(genUser('a'));
  const b = new Client(s); await b.join(genUser('b'));
  let t = csrfOf((await a.get('/discuss/lattice')).body);
  const r = await a.post('/discuss/lattice/posts', { _csrf: t, type: 'idea', body: 'Threat analysis first, always.' });
  const id = /post-(\d+)/.exec(r.headers.location)[1];
  const tb = csrfOf((await b.get('/discuss/lattice')).body);
  assert.equal((await b.post(`/posts/${id}/delete`, { _csrf: tb })).status, 403);
  assert.equal((await b.post(`/posts/${id}/edit`, { _csrf: tb, body: 'hijacked text here' })).status, 403);
  assert.equal((await b.get(`/posts/${id}/edit`)).status, 403);
  assert.equal((await b.post(`/posts/${id}/like`, { _csrf: tb })).status, 303);
  assert.equal((await a.post(`/posts/${id}/like`, { _csrf: t })).status, 400); // own post
  assert.equal((await b.post('/discuss/lattice/posts', { _csrf: tb, type: 'reply', parent: id, body: 'Agreed!' })).status, 303);
  assert.equal((await b.post('/discuss/lattice/like', { _csrf: tb })).status, 303);
  const page = (await a.get('/discuss/lattice')).body;
  assert.match(page, /Agreed!/);
  assert.match(page, /1 like</);
  t = csrfOf(page);
  assert.equal((await a.post(`/posts/${id}/edit`, { _csrf: t, body: 'Threat analysis first, then mapping.' })).status, 303);
  assert.match((await a.get('/discuss/lattice')).body, /then mapping\.[\s\S]*\(edited\)|\(edited\)[\s\S]*then mapping/);
  assert.equal((await a.post(`/posts/${id}/delete`, { _csrf: t })).status, 303);
  const after = (await a.get('/discuss/lattice')).body;
  assert.ok(!after.includes('then mapping'));
  assert.match(after, /Deleted by its author/);
});

test('moderation requires server-granted role; remove/restore/lock/suspend', async () => {
  const m = new Client(s); const mu = genUser('m'); await m.join(mu);
  const u = new Client(s); const uu = genUser('u'); await u.join(uu);
  let tu = csrfOf((await u.get('/discuss/atlas')).body);
  const r = await u.post('/discuss/atlas/posts', { _csrf: tu, type: 'idea', body: 'Spam spam spam spam' });
  const id = /post-(\d+)/.exec(r.headers.location)[1];
  let tm = csrfOf((await m.get('/discuss/atlas')).body);
  assert.equal((await m.get('/moderation')).status, 403);
  assert.equal((await m.post(`/moderation/posts/${id}/remove`, { _csrf: tm, reason: 'spam' })).status, 403);
  assert.equal((await m.post(`/posts/${id}/report`, { _csrf: tm, reason: 'spam' })).status, 303);
  cli(s, 'grant-moderator', mu.username);
  assert.equal((await m.get('/moderation')).status, 200);
  assert.equal((await m.post(`/moderation/posts/${id}/remove`, { _csrf: tm, reason: 'spam' })).status, 303);
  assert.match((await u.get('/discuss/atlas')).body, /Removed by moderator/);
  assert.equal((await m.post(`/moderation/posts/${id}/restore`, { _csrf: tm })).status, 303);
  assert.equal((await m.post('/moderation/topics/atlas/lock', { _csrf: tm })).status, 303);
  tu = csrfOf((await u.get('/discuss/atlas')).body);
  assert.equal((await u.post('/discuss/atlas/posts', { _csrf: tu, type: 'idea', body: 'posting into a locked topic' })).status, 403);
  await m.post('/moderation/topics/atlas/unlock', { _csrf: tm });
  const uid = /moderation\/users\/(\d+)\/suspend/.exec((await m.get('/moderation')).body.split(uu.username).at(-1) || '')?.[1];
  assert.ok(uid);
  tm = csrfOf((await m.get('/moderation')).body);
  assert.equal((await m.post(`/moderation/users/${uid}/suspend`, { _csrf: tm })).status, 303);
  assert.equal((await u.post('/discuss/atlas/posts', { _csrf: tu, type: 'idea', body: 'suspended user posting' })).status, 403);
});

test('signup validation, reserved names, duplicate names, login throttle', async () => {
  const c = new Client(s);
  const u = genUser();
  assert.equal((await c.join({ ...u, username: 'admin' })).status, 400);
  assert.equal((await c.join({ ...u, username: '<x>' })).status, 400);
  assert.equal((await c.join({ ...u, password: 'short' })).status, 400);
  assert.equal((await c.join(u, { privacy: '' })).status, 400);
  assert.equal((await c.join(u)).status, 303);
  const d = new Client(s);
  assert.equal((await d.join(u)).status, 400);
  const e = new Client(s);
  let last;
  for (let i = 0; i < 10; i++) last = await e.login({ ...u, password: `wrong-${i}-password` });
  assert.equal(last.status, 429);
});

test('account deletion erases data; persistence across restart', async () => {
  const keep = new Client(s); const ku = genUser('k'); await keep.join(ku);
  let t = csrfOf((await keep.get('/discuss/testing')).body);
  await keep.post('/discuss/testing/posts', { _csrf: t, type: 'feedback', body: 'Persistence check message.' });
  const gone = new Client(s); const gu = genUser('g'); await gone.join(gu);
  t = csrfOf((await gone.get('/discuss/testing')).body);
  await gone.post('/discuss/testing/posts', { _csrf: t, type: 'idea', body: 'Please erase this text.' });
  t = csrfOf((await gone.get('/account')).body);
  assert.equal((await gone.post('/account/delete', { _csrf: t, password: 'wrong-password-1' })).status, 400);
  assert.equal((await gone.post('/account/delete', { _csrf: t, password: gu.password })).status, 303);
  assert.ok(!(await keep.get('/discuss/testing')).body.includes('Please erase this text.'));
  const backupOut = cli(s, 'backup', `${s.dir}/backups`);
  assert.match(backupOut, /"posts":/);
  await s.stop();
  s = await startServer({ dir: s.dir, port: s.port });
  const again = new Client(s);
  assert.match((await again.get('/discuss/testing')).body, /Persistence check message\./);
  assert.equal((await again.login(ku)).status, 303);
  assert.equal((await new Client(s).login(gu)).status, 401);
  assert.equal((await keep.get('/account')).status, 200, 'session survives restart');
});

test('CLI runs when invoked through a release symlink, as the units and runbook do', () => {
  // Production calls /srv/ashfall-promo/current/server/cli.mjs, where `current` is a symlink.
  const link = `${s.dir}/current`;
  fs.symlinkSync(APP, link);
  const out = execFileSync(process.execPath, [`${link}/server/cli.mjs`, 'status'], { env: s.env, encoding: 'utf8' });
  assert.match(out, /"schema"/, 'status printed through the symlink');
  const backup = JSON.parse(execFileSync(process.execPath, [`${link}/server/cli.mjs`, 'backup', `${s.dir}/via-link`], { env: s.env, encoding: 'utf8' }));
  assert.ok(fs.existsSync(backup.backup), 'backup written through the symlink');
});

test('restore drill: backup -> new data -> stop -> restore -> data matches backup', async () => {
  const c = new Client(s); const u = genUser('r'); await c.join(u);
  let t = csrfOf((await c.get('/discuss/general')).body);
  await c.post('/discuss/general/posts', { _csrf: t, type: 'idea', body: 'Present in the backup.' });
  const out = JSON.parse(cli(s, 'backup', `${s.dir}/drill`, '--keep-daily', '3'));
  assert.ok(out.backup && fs.existsSync(out.backup), 'backup file written');
  assert.equal((fs.statSync(out.backup).mode & 0o077), 0, 'backup is not group/world readable');
  assert.match(cli(s, 'verify', out.backup), /"integrity": "ok"/);
  const left = fs.readdirSync(`${s.dir}/drill`).filter((f) => !/^community-\d{8}T\d{6}Z\.sqlite(\.json)?$/.test(f));
  assert.deepEqual(left, [], 'a backup is one self-contained file plus its metadata (no -wal/-shm/partial leftovers)');
  t = csrfOf((await c.get('/discuss/general')).body);
  await c.post('/discuss/general/posts', { _csrf: t, type: 'idea', body: 'Written after the backup.' });
  assert.throws(() => cli(s, 'restore', out.backup), /--yes/, 'restore requires explicit --yes');
  await s.stop();
  const restored = JSON.parse(cli(s, 'restore', out.backup, '--yes').split('\n').filter((l) => !l.startsWith('current database saved')).join('\n'));
  assert.equal(restored.counts.posts, out.counts.posts);
  assert.ok(fs.readdirSync(s.dir).some((f) => f.startsWith('community.sqlite.pre-restore-')), 'pre-restore copy kept');
  s = await startServer({ dir: s.dir, port: s.port });
  const body = (await new Client(s).get('/discuss/general')).body;
  assert.match(body, /Present in the backup\./);
  assert.doesNotMatch(body, /Written after the backup\./);
});
