// Walk a page viewport-by-viewport and save screenshots (visual review helper).
// Usage: node scripts/walk.mjs <port> <out-dir> <path> <width> <height> [maxShots]
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';

const [port, out, p, w, h, max = '40'] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
const b = await chromium.launch({ args: [`--host-resolver-rules=MAP ashfall.teknetik.co:443 127.0.0.1:${port}`] });
const ctx = await b.newContext({ viewport: { width: +w, height: +h }, ignoreHTTPSErrors: true, reducedMotion: 'reduce' });
const page = await ctx.newPage();
const errors = [];
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
page.on('pageerror', (e) => errors.push(String(e)));
await page.goto(`https://ashfall.teknetik.co${p}`, { waitUntil: 'networkidle' });
const total = await page.evaluate(() => document.documentElement.scrollHeight);
let i = 0;
for (let y = 0; y < total && i < +max; y += +h - 60, i++) {
  await page.evaluate((yy) => window.scrollTo(0, yy), y);
  await page.waitForTimeout(250);
  await page.screenshot({ path: path.join(out, `${String(i).padStart(2, '0')}.png`) });
}
console.log(`height=${total} shots=${i} errors=${errors.length ? errors.join(' | ') : 'none'}`);
await b.close();
