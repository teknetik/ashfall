// End-to-end browser harness (Playwright + installed Chromium).
// Starts the real production entrypoint against a throwaway temp DB with a temp self-signed
// certificate, maps the canonical host to that loopback port, and drives desktop + mobile flows.
// Never touches real user data; generated test accounts are random and never printed.
// Usage: node scripts/e2e.mjs            (screenshots -> evidence/e2e/<UTC stamp>/)
//        E2E_PORT=3188 node scripts/e2e.mjs   run against an already-running isolated QA instance instead
//        (creates two random throwaway accounts and posts there; never point this at production data).
import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { startServer, genUser, APP, HOST } from '../test/helpers.mjs';

const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d+Z$/, 'Z');
const OUT = path.join(APP, 'evidence', 'e2e', stamp);
fs.mkdirSync(OUT, { recursive: true });
const BASE = `https://${HOST}`;

/** @type {Array<{name: string, ok: boolean, ms: number, error?: string}>} */
const results = [];
async function step(name, fn) {
  const t = Date.now();
  try {
    await fn();
    results.push({ name, ok: true, ms: Date.now() - t });
    console.log(`  ok   ${name}`);
  } catch (e) {
    results.push({ name, ok: false, ms: Date.now() - t, error: String(e && e.message ? e.message : e).split('\n').slice(0, 6).join(' | ') });
    console.log(`  FAIL ${name}\n       ${String(e && e.stack ? e.stack : e).split('\n').slice(0, 8).join('\n       ')}`);
  }
}

const EXTERNAL = process.env.E2E_PORT ? Number(process.env.E2E_PORT) : 0;
const server = EXTERNAL ? { port: EXTERNAL, dir: '', async stop() {} } : await startServer();
const browser = await chromium.launch({ args: [`--host-resolver-rules=MAP ${HOST}:443 127.0.0.1:${server.port}`] });

/** @param {{width:number,height:number}} viewport @param {object} [extra] */
async function newPage(viewport, extra = {}) {
  const ctx = await browser.newContext({ viewport, ignoreHTTPSErrors: true, ...extra });
  const page = await ctx.newPage();
  /** @type {string[]} */
  const errors = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push(String(e)));
  return { ctx, page, errors };
}
const shot = (page, name, full = false) => page.screenshot({ path: path.join(OUT, `${name}.png`), fullPage: full });
const noOverflow = async (page) => {
  const { sw, cw } = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth }));
  assert.ok(sw <= cw, `horizontal overflow: scrollWidth ${sw} > clientWidth ${cw}`);
};
const activeIn = (page, sel) => page.evaluate((s) => !!document.activeElement && !!document.activeElement.closest(s), sel);

const SIZES = [
  { name: 'desktop', viewport: { width: 1440, height: 900 } },
  { name: 'mobile', viewport: { width: 390, height: 844 } },
];

try {
  for (const size of SIZES) {
    console.log(`[e2e] ${size.name} ${size.viewport.width}x${size.viewport.height}`);
    const { ctx, page, errors } = await newPage(size.viewport, { reducedMotion: 'reduce' });

    await step(`${size.name}: public pages render with real art, alt text, no overflow or console errors`, async () => {
      for (const p of ['/', '/gallery', '/development', '/discuss', '/about', '/privacy', '/discuss/world']) {
        const r = await page.goto(`${BASE}${p}`, { waitUntil: 'networkidle' });
        assert.equal(r.status(), 200, `${p} status`);
        await noOverflow(page);
        const imgs = await page.evaluate(() => Array.from(document.images).filter((i) => !i.closest('.lightbox')).map((i) => ({ src: i.currentSrc || i.src, alt: i.getAttribute('alt'), complete: i.complete, w: i.naturalWidth, lazy: i.loading === 'lazy' })));
        assert.ok(imgs.every((i) => i.alt !== null), `${p}: every <img> has an alt attribute`);
        const eager = imgs.filter((i) => !i.lazy);
        assert.ok(eager.every((i) => i.complete && i.w > 0), `${p}: eager images decoded`);
      }
      await page.goto(`${BASE}/`, { waitUntil: 'networkidle' });
      const hero = await page.evaluate(() => { const i = /** @type {HTMLImageElement|null} */ (document.querySelector('.hero img')); return i ? { w: i.naturalWidth, src: i.currentSrc } : null; });
      assert.ok(hero && hero.w > 0 && /ashfall-ward-hero/.test(hero.src), `hero art loaded (${JSON.stringify(hero)})`);
      const text = await page.evaluate(() => document.body.innerText.length);
      assert.ok(text > 15000, `home has substantial copy (${text} chars)`);
      await shot(page, `${size.name}-home`);
      await shot(page, `${size.name}-home-full`, true);
      await page.goto(`${BASE}/development`, { waitUntil: 'networkidle' });
      await shot(page, `${size.name}-development`);
      await shot(page, `${size.name}-development-full`, true);
      assert.deepEqual(errors, [], 'no console errors');
    });

    await step(`${size.name}: navigation menu opens as a modal, traps focus, closes on Escape`, async () => {
      await page.goto(`${BASE}/`, { waitUntil: 'networkidle' });
      const btn = page.locator('.site-header .menu-btn');
      if (!(await btn.isVisible())) {
        // Desktop shows inline nav; the menu button is hidden at >= 1180px.
        const navLinks = await page.locator('.site-header nav a:visible').count();
        assert.ok(navLinks >= 4, `desktop inline nav visible (${navLinks} links)`);
        await page.keyboard.press('Tab');
        assert.equal(await page.evaluate(() => document.activeElement?.textContent?.trim().toLowerCase().startsWith('skip')), true, 'first Tab reaches skip link');
        return;
      }
      await btn.click();
      const menu = page.locator('#site-menu');
      await menu.waitFor({ state: 'visible' });
      assert.equal(await btn.getAttribute('aria-expanded'), 'true');
      assert.ok(await activeIn(page, '#site-menu'), 'focus moved into menu');
      assert.equal(await page.evaluate(() => document.querySelector('body > main').hasAttribute('inert')), true, 'background inert');
      await shot(page, `${size.name}-menu-open`);
      for (let i = 0; i < 25; i++) { await page.keyboard.press('Tab'); assert.ok(await activeIn(page, '#site-menu'), `Tab ${i} stays in menu`); }
      for (let i = 0; i < 5; i++) { await page.keyboard.press('Shift+Tab'); assert.ok(await activeIn(page, '#site-menu'), `Shift+Tab ${i} stays in menu`); }
      await page.keyboard.press('Escape');
      await menu.waitFor({ state: 'hidden' });
      assert.equal(await btn.getAttribute('aria-expanded'), 'false');
      assert.equal(await page.evaluate(() => document.activeElement === document.querySelector('.site-header .menu-btn')), true, 'focus restored to menu button');
      assert.equal(await page.evaluate(() => document.querySelector('body > main').hasAttribute('inert')), false, 'background no longer inert');
    });

    await step(`${size.name}: gallery filters and keyboard lightbox`, async () => {
      await page.goto(`${BASE}/gallery`, { waitUntil: 'networkidle' });
      const all = await page.locator('.gallery .fig').count();
      assert.ok(all >= 10, `gallery figures (${all})`);
      await page.locator('.filters button[data-filter="build"]').click();
      const visBuild = await page.locator('.gallery .fig:not([hidden])').count();
      assert.ok(visBuild >= 1 && visBuild < all, `build filter narrows (${visBuild}/${all})`);
      const badges = await page.locator('.gallery .fig:not([hidden]) .fig__badge').allInnerTexts();
      assert.ok(badges.length === visBuild && badges.every((b) => /build/i.test(b)), `visible build figures carry an IN BUILD label: ${badges.join(',')}`);
      assert.equal(await page.locator('.filters button[data-filter="build"]').getAttribute('aria-pressed'), 'true');
      assert.match(await page.locator('.filter-intro').innerText(), new RegExp(`Showing ${visBuild} image`));
      await page.locator('.filters button[data-filter="concept"]').click();
      const conceptBadges = await page.locator('.gallery .fig:not([hidden]) .fig__badge').allInnerTexts();
      assert.ok(conceptBadges.length > 0 && conceptBadges.every((b) => /concept/i.test(b)), `concept filter shows concept labels: ${conceptBadges.join(',')}`);
      await page.locator('.filters button[data-filter="all"]').click();
      assert.equal(await page.locator('.gallery .fig:not([hidden])').count(), all);

      const first = page.locator('.gallery a[data-lightbox]').first();
      await first.focus();
      await page.keyboard.press('Enter');
      const lb = page.locator('.lightbox');
      await lb.waitFor({ state: 'visible' });
      assert.ok(await activeIn(page, '.lightbox'), 'focus inside lightbox');
      const c1 = await page.locator('.lightbox__count').innerText();
      assert.match(c1, /^1 \/ \d+$/);
      await page.waitForFunction(() => { const i = /** @type {HTMLImageElement|null} */ (document.querySelector('.lightbox img')); return i && i.complete && i.naturalWidth > 0; });
      assert.ok((await page.locator('.lightbox img').getAttribute('alt')).length > 10, 'lightbox image has alt text');
      assert.ok((await page.locator('.lightbox__badge').innerText()).length > 0, 'lightbox shows concept/build label');
      await shot(page, `${size.name}-lightbox`);
      await page.keyboard.press('ArrowRight');
      assert.match(await page.locator('.lightbox__count').innerText(), /^2 \//);
      await page.keyboard.press('ArrowLeft');
      await page.keyboard.press('ArrowLeft');
      assert.match(await page.locator('.lightbox__count').innerText(), new RegExp(`^${all} /`));
      for (let i = 0; i < 8; i++) { await page.keyboard.press('Tab'); assert.ok(await activeIn(page, '.lightbox'), 'Tab trapped in lightbox'); }
      await page.keyboard.press('Escape');
      await lb.waitFor({ state: 'hidden' });
      assert.equal(await page.evaluate(() => document.activeElement === document.querySelector('.gallery a[data-lightbox]')), true, 'focus returns to opener');
    });

    await step(`${size.name}: Lattice capacity explainer reports usage and overload`, async () => {
      await page.goto(`${BASE}/`, { waitUntil: 'networkidle' });
      const cap = page.locator('.capacity').first();
      await cap.scrollIntoViewIfNeeded();
      const status = cap.locator('.capacity__status');
      assert.match(await status.innerText(), /Using 0 of 100/);
      await cap.locator('input[data-cap-id="mapping"]').check();
      await cap.locator('input[data-cap-id="threat"]').check();
      assert.match(await cap.locator('.capacity__readout').innerText(), /^40 \/ 100$/);
      assert.match(await status.innerText(), /Running: Mapping, Threat analysis/);
      await cap.locator('input[data-cap-id="fab"]').check();
      assert.match(await status.innerText(), /CAPACITY EXCEEDED — using 95 of 100|Using 95 of 100/);
      await cap.locator('input[data-cap-id="env"]').check();
      assert.match(await status.innerText(), /CAPACITY EXCEEDED — using 115 of 100/);
      assert.ok(await cap.evaluate((el) => el.classList.contains('is-over')), 'over class set');
      await cap.screenshot({ path: path.join(OUT, `${size.name}-capacity-over.png`) });
      await cap.locator('input[data-cap-id="none"]').check();
      assert.match(await status.innerText(), /Using 60 of 100/);
    });

    await step(`${size.name}: atlas regions open (map hotspot on desktop, region list on mobile)`, async () => {
      await page.goto(`${BASE}/`, { waitUntil: 'networkidle' });
      const spot = page.locator('.spot[data-region]').first();
      assert.ok(await spot.count(), 'atlas hotspots rendered');
      const slug = await spot.getAttribute('data-region');
      const region = page.locator(`#region-${slug}`);
      if (await spot.isVisible()) {
        await spot.scrollIntoViewIfNeeded();
        await spot.click();
      } else {
        // Hotspots are intentionally hidden below 768px; the region list is the mobile control.
        await region.locator('summary').scrollIntoViewIfNeeded();
        await region.locator('summary').click();
      }
      assert.equal(await region.evaluate((d) => /** @type {HTMLDetailsElement} */ (d).open), true, 'region opened');
      await region.screenshot({ path: path.join(OUT, `${size.name}-atlas-region.png`) });
    });

    await ctx.close();
  }

  console.log('[e2e] motion preferences');
  await step('reduced motion: content shown statically; full motion: reveal + typing run', async () => {
    const reduced = await newPage({ width: 1280, height: 800 }, { reducedMotion: 'reduce' });
    await reduced.page.goto(`${BASE}/`, { waitUntil: 'networkidle' });
    const r = await reduced.page.evaluate(() => ({
      reveals: document.querySelectorAll('.reveal').length,
      shown: document.querySelectorAll('.reveal.is-in').length,
      caret: !!document.querySelector('.hero__boot .caret'),
      boot: document.querySelector('.hero__boot-text')?.textContent || '',
      full: document.querySelector('.hero__boot')?.getAttribute('data-text') || '',
    }));
    assert.ok(r.reveals > 0 && r.shown === r.reveals, `all reveal blocks visible without animation (${r.shown}/${r.reveals})`);
    assert.equal(r.caret, false, 'no typing caret under reduced motion');
    assert.ok(r.boot.length > 0 && (!r.full || r.boot === r.full), 'boot line shown in full immediately');
    await reduced.ctx.close();

    const full = await newPage({ width: 1280, height: 800 }, { reducedMotion: 'no-preference' });
    await full.page.goto(`${BASE}/`, { waitUntil: 'domcontentloaded' });
    await full.page.waitForTimeout(150);
    const f = await full.page.evaluate(() => ({ caret: !!document.querySelector('.hero__boot .caret'), pending: document.querySelectorAll('.reveal:not(.is-in)').length }));
    assert.ok(f.caret, 'typing caret runs with motion allowed');
    assert.ok(f.pending > 0, 'off-screen reveal blocks wait for scroll');
    await full.ctx.close();
  });

  await step('no-JS: pages are complete and filters stay hidden', async () => {
    const nojs = await newPage({ width: 1280, height: 800 }, { javaScriptEnabled: false });
    await nojs.page.goto(`${BASE}/gallery`, { waitUntil: 'networkidle' });
    assert.equal(await nojs.page.locator('.filters').isHidden(), true);
    assert.ok(await nojs.page.locator('.gallery .fig').count() >= 10);
    await nojs.page.goto(`${BASE}/`, { waitUntil: 'networkidle' });
    const vis = await nojs.page.evaluate(() => { const el = document.querySelector('.reveal'); return el ? getComputedStyle(el).opacity : '1'; });
    assert.equal(vis, '1', 'reveal content visible without JS');
    await nojs.ctx.close();
  });

  console.log('[e2e] community flow');
  for (const size of SIZES) {
    await step(`${size.name}: signup -> post -> reload -> logout -> login -> like persists`, async () => {
      const { ctx, page, errors } = await newPage(size.viewport, { reducedMotion: 'reduce' });
      const u = genUser(size.name === 'desktop' ? 'e2ed' : 'e2em');
      await page.goto(`${BASE}/discuss/lattice`, { waitUntil: 'networkidle' });
      await page.locator('a[href="/join?next=/discuss/lattice"]').first().click();
      await page.waitForURL(/\/join/);
      await page.fill('#username', u.username);
      await page.fill('#password', u.password);
      await page.fill('#confirm', u.password);
      await page.check('#privacy');
      await shot(page, `${size.name}-join`);
      await Promise.all([page.waitForURL(/\/discuss\/lattice/), page.locator('form[action="/join"] button[type="submit"]').click()]);
      const cookies = await ctx.cookies(BASE);
      const sess = cookies.find((c) => c.name.startsWith('__Host-'));
      assert.ok(sess && sess.secure && sess.httpOnly && sess.sameSite === 'Lax', `secure session cookie (${JSON.stringify(sess && { name: sess.name, secure: sess.secure, httpOnly: sess.httpOnly, sameSite: sess.sameSite })})`);
      assert.equal(await page.evaluate(() => document.cookie.includes('__Host-')), false, 'session cookie hidden from JS');

      const marker = `E2E ${size.name} feedback ${Date.now()} <b>not bold</b> & "quoted"`;
      await page.locator('#composer input[name="type"][value="feedback"]').check();
      await page.selectOption('#tag', 'mechanics');
      await page.fill('#body', marker);
      await Promise.all([page.waitForURL(/\/discuss\/lattice/), page.locator('#composer button[type="submit"]').click()]);
      const post = page.locator('.post', { hasText: marker });
      await post.first().waitFor();
      assert.equal(await page.locator('.post b', { hasText: 'not bold' }).count(), 0, 'user HTML not rendered');
      await page.locator('form[action="/discuss/lattice/like"] button').click();
      await page.waitForLoadState('networkidle');
      assert.equal(await page.locator('form[action="/discuss/lattice/like"] button').getAttribute('aria-pressed'), 'true');
      await post.first().scrollIntoViewIfNeeded();
      await shot(page, `${size.name}-topic-after-post`);

      await page.reload({ waitUntil: 'networkidle' });
      assert.ok(await page.locator('.post', { hasText: marker }).count() === 1, 'post persisted across reload');
      assert.match(await page.locator('.like-form .counts').innerText(), /[1-9]\d* likes?/i);

      // Logout (menu on mobile, header on desktop) then sign back in from a fresh context.
      await page.goto(`${BASE}/account`, { waitUntil: 'networkidle' });
      assert.ok((await page.locator('main').innerText()).includes(u.username), 'account page shows username');
      assert.ok(await page.locator('main', { hasText: marker.slice(0, 20) }).count(), 'account lists own post');
      await shot(page, `${size.name}-account`);
      const logout = page.locator('form[action="/logout"] button').first();
      if (!(await logout.isVisible())) await page.locator('.site-header .menu-btn').click();
      await Promise.all([page.waitForURL(/\/\?done=signedout/), page.locator('form[action="/logout"] button:visible').first().click()]);
      const after = await page.goto(`${BASE}/account`, { waitUntil: 'networkidle' });
      assert.match(page.url(), /\/login/, `signed-out account redirects to login (status ${after.status()})`);
      await ctx.close();

      const second = await newPage(size.viewport, { reducedMotion: 'reduce' });
      await second.page.goto(`${BASE}/login?next=/discuss/lattice`, { waitUntil: 'networkidle' });
      await second.page.fill('#username', u.username);
      await second.page.fill('#password', u.password);
      await Promise.all([second.page.waitForURL(/\/discuss\/lattice/), second.page.locator('form[action="/login"] button[type="submit"]').click()]);
      assert.equal(await second.page.locator('.post', { hasText: marker }).count(), 1, 'post visible after new login');
      assert.equal(await second.page.locator('form[action="/discuss/lattice/like"] button').getAttribute('aria-pressed'), 'true', 'like persisted for account');
      assert.ok(await second.page.locator('.post', { hasText: marker }).locator('a[href$="/edit"], button', { hasText: /edit|delete/i }).count() > 0, 'owner controls present');
      await second.ctx.close();
      assert.deepEqual(errors, [], 'no console errors');
    });
  }
} finally {
  await browser.close();
  await server.stop();
  if (server.dir) fs.rmSync(server.dir, { recursive: true, force: true });
}

const failed = results.filter((r) => !r.ok);
const report = { stamp, chromium: browser.version(), server: EXTERNAL ? `existing instance 127.0.0.1:${EXTERNAL}` : 'server/index.mjs over TLS, temp DB (deleted)', pass: results.length - failed.length, fail: failed.length, results };
fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify(report, null, 2));
console.log(`[e2e] ${report.pass} passed, ${report.fail} failed; evidence ${path.relative(APP, OUT)}`);
process.exit(failed.length ? 1 : 0);
