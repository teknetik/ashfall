// Public end-to-end check against https://ashfall.teknetik.co through real DNS, Kong and TLS.
// Signs up a disposable account, posts, restarts ONLY ashfall-promo.service, checks the post survived,
// then deletes the post and the account. Credentials stay in memory and are never printed.
// Usage (from promo-site/app so Playwright resolves): node ../ops/deploy-20261001/public_e2e.mjs
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';

// Use the app's pinned Playwright (matches the installed Chromium), not whatever resolves from ops/.
const { chromium } = createRequire(new URL('../../app/package.json', import.meta.url))('playwright');
const BASE = 'https://ashfall.teknetik.co';
const user = `e2e-${crypto.randomBytes(4).toString('hex')}`;
const pass = crypto.randomBytes(18).toString('base64url');
const marker = `Public deploy check ${crypto.randomBytes(3).toString('hex')}: the market lane reads well.`;
const results = [];
const step = async (name, fn) => {
  try { await fn(); results.push(['ok', name]); console.log(`  ok   ${name}`); } catch (e) { results.push(['FAIL', name]); console.log(`  FAIL ${name}: ${String(e.message).split('\n')[0]}`); throw e; }
};

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
const page = await ctx.newPage();
const errors = [];
page.on('pageerror', (e) => errors.push(String(e)));
try {
  await step('home, development and gallery load over trusted TLS', async () => {
    for (const p of ['/', '/development', '/gallery']) {
      const r = await page.goto(`${BASE}${p}`, { waitUntil: 'networkidle' });
      assert.equal(r.status(), 200, p);
    }
    const sec = await page.evaluate(() => location.protocol);
    assert.equal(sec, 'https:');
  });
  await step('sign up with a disposable account', async () => {
    await page.goto(`${BASE}/join`);
    await page.fill('#username', user);
    await page.fill('#password', pass);
    await page.fill('#confirm', pass);
    await page.check('#privacy');
    await Promise.all([page.waitForNavigation(), page.click('form[action="/join"] button[type=submit]')]);
    assert.match(await page.content(), new RegExp(`Signed in as[\\s\\S]*${user}`));
    const cookies = await ctx.cookies(BASE);
    const s = cookies.find((c) => c.name === '__Host-ashfall_session');
    assert.ok(s && s.secure && s.httpOnly && s.sameSite === 'Lax' && !s.domain.startsWith('.'), 'session cookie flags');
  });
  await step('post an idea in General feedback', async () => {
    await page.goto(`${BASE}/discuss/general`);
    await page.fill('#body', marker);
    await Promise.all([page.waitForNavigation(), page.click('#composer button[type=submit]')]);
    assert.ok((await page.content()).includes(marker));
  });
  await step('post survives an app-only service restart', async () => {
    execFileSync('sudo', ['-n', 'systemctl', 'restart', 'ashfall-promo.service']);
    for (let i = 0; i < 30; i++) {
      try { const r = await page.goto(`${BASE}/discuss/general`); if (r.status() === 200) break; } catch { /* restarting */ }
      await page.waitForTimeout(1000);
    }
    assert.ok((await page.content()).includes(marker), 'post still there');
    assert.match(await page.content(), new RegExp(`Signed in as[\\s\\S]*${user}`), 'session still valid');
  });
  await step('delete the post, then the account', async () => {
    page.on('dialog', (d) => d.accept());
    const art = page.locator('article.post', { hasText: marker });
    await Promise.all([page.waitForNavigation(), art.locator('form[action$="/delete"] button').click()]);
    assert.ok(!(await page.content()).includes(marker), 'post text gone');
    await page.goto(`${BASE}/account`);
    await page.fill('#del-pw', pass);
    await Promise.all([page.waitForNavigation(), page.click('form[action="/account/delete"] button[type=submit]')]);
    await page.goto(`${BASE}/login`);
    await page.fill('#username', user);
    await page.fill('#password', pass);
    const r = await Promise.all([page.waitForNavigation(), page.click('form[action="/login"] button[type=submit]')]);
    assert.notEqual(r[0]?.status(), 303);
    assert.ok(!(await page.content()).includes(`Signed in as`), 'deleted account cannot sign in');
  });
  assert.deepEqual(errors, [], 'no page errors');
} finally {
  await browser.close();
  console.log(JSON.stringify({ base: BASE, passed: results.filter((r) => r[0] === 'ok').length, failed: results.filter((r) => r[0] !== 'ok').length }));
}
