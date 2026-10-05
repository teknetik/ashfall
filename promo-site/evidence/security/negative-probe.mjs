import assert from 'node:assert/strict';
import { startServer, Client, genUser } from '../../app/test/helpers.mjs';

const s = await startServer({ env: { ASHFALL_CLIENT_IP_HEADER: '' } });
let checks = 0;
const expect = async (label, promise, status) => {
  const r = await promise;
  assert.equal(r.status, status, label);
  checks++;
  return r;
};
try {
  const a = new Client(s);
  const b = new Client(s);
  const anon = new Client(s);
  const ua = genUser('sec_a');
  const ub = genUser('sec_b');
  await expect('join a', a.join(ua), 303);
  await expect('join b', b.join(ub), 303);
  const token = (html) => /name="_csrf" value="([^"]+)"/.exec(html)?.[1];
  const ta = token((await a.get('/discuss/general')).body);
  const tb = token((await b.get('/discuss/general')).body);
  const p = await expect('create', a.post('/discuss/general/posts', { _csrf: ta, type: 'idea', body: '<img src=x onerror=alert(1)> sample idea' }), 303);
  const id = /post-(\d+)/.exec(p.headers.location)?.[1];
  assert.ok(id);
  checks++;
  const publicPage = (await anon.get('/discuss/general')).body;
  assert.ok(publicPage.includes('&lt;img src=x onerror=alert(1)&gt;') && !publicPage.includes('<img src=x onerror=alert(1)>'));
  checks++;
  await expect('foreign account edit', b.post(`/posts/${id}/edit`, { _csrf: tb, body: 'unauthorized edit attempt' }), 403);
  await expect('foreign account delete', b.post(`/posts/${id}/delete`, { _csrf: tb }), 403);
  await expect('anonymous edit', anon.get(`/posts/${id}/edit`), 303);
  await expect('member moderation', b.get('/moderation'), 403);
  await expect('member suspend', b.post('/moderation/users/1/suspend', { _csrf: tb }), 403);
  await expect('cross origin', a.post(`/posts/${id}/delete`, { _csrf: ta }, { origin: 'https://evil.example' }), 403);
  await expect('missing origin', a.post(`/posts/${id}/delete`, { _csrf: ta }, { origin: null }), 403);
  await expect('missing CSRF', a.post(`/posts/${id}/delete`, {}), 403);
  await expect('wrong CSRF', a.post(`/posts/${id}/delete`, { _csrf: tb }), 403);
  await expect('forged forwarding ignored without config', anon.get('/api/health', { headers: { 'X-Forwarded-For': '8.8.8.8', Host: '127.0.0.1' } }), 200);
  await expect('wrong Host', anon.get('/account', { headers: { Host: 'evil.example' } }), 421);
  await expect('path traversal', anon.get('/%2e%2e/%2e%2e/community.sqlite'), 404);
  const oldCookie = a.jar.get('__Host-ashfall_session');
  await expect('logout', a.post('/logout', { _csrf: ta }), 303);
  const stolen = new Client(s);
  stolen.jar.set('__Host-ashfall_session', oldCookie);
  await expect('logout invalidates saved cookie', stolen.get('/account'), 303);
  assert.equal(stolen.jar.has('__Host-ashfall_session'), false);
  checks++;
  await expect('SQL metacharacter username refused', anon.join({ username: "x' OR 1=1--", password: ua.password }), 400);
  assert.ok(!s.logs.includes(ua.password) && !s.logs.includes(ub.password) && !s.logs.includes('<img'));
  checks++;
  console.log(JSON.stringify({ result: 'PASS', checks, isolated: true, passwordsPrinted: false }));
} finally {
  await s.stop();
  s.cleanup();
}
