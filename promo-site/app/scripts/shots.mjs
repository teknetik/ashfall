// Capture screenshots of a running server for visual review.
// Usage: node scripts/shots.mjs <base-url> <out-dir> [paths...]
// The browser resolves the canonical host to the given loopback server, so Host/TLS match production.
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';

const [base, out, ...paths] = process.argv.slice(2);
if (!base || !out) { console.error('usage: shots.mjs <base> <out> [paths]'); process.exit(2); }
const u = new URL(base);
fs.mkdirSync(out, { recursive: true });
const browser = await chromium.launch({ args: [`--host-resolver-rules=MAP ashfall.teknetik.co:443 127.0.0.1:${u.port}`, '--ignore-certificate-errors'] });
/** @type {Array<[string, number, number]>} */
const sizes = [['desktop', 1440, 900], ['mobile', 390, 844]];
const list = paths.length ? paths : ['/'];
for (const [name, w, h] of sizes) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1, ignoreHTTPSErrors: true, reducedMotion: 'reduce' });
  const page = await ctx.newPage();
  const errors = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push(String(e)));
  for (const p of list) {
    await page.goto(`https://ashfall.teknetik.co${p}`, { waitUntil: 'networkidle' });
    if (p.includes('#')) { await page.locator(p.slice(p.indexOf('#'))).first().scrollIntoViewIfNeeded(); await page.evaluate((id) => document.querySelector(id).scrollIntoView({ block: 'start' }), p.slice(p.indexOf('#'))); await page.waitForTimeout(400); }
    const file = path.join(out, `${name}${p.replace(/[^a-z0-9]+/gi, '_')}.png`);
    await page.screenshot({ path: file, fullPage: process.env.FULL === '1' });
    console.log(file, errors.length ? `ERRORS: ${errors.join(' | ')}` : '');
  }
  await ctx.close();
}
await browser.close();
