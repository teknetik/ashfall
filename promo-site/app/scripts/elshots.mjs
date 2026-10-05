// Screenshot specific elements for close visual review.
// Usage: node scripts/elshots.mjs <port> <out-dir> <width> <path>::<selector> ...
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';

const [port, out, w, ...specs] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
const b = await chromium.launch({ args: [`--host-resolver-rules=MAP ashfall.teknetik.co:443 127.0.0.1:${port}`] });
const ctx = await b.newContext({ viewport: { width: +w, height: 900 }, ignoreHTTPSErrors: true, reducedMotion: 'reduce' });
const page = await ctx.newPage();
let cur = '';
for (const spec of specs) {
  const [p, sel] = spec.split('::');
  if (p !== cur) { await page.goto(`https://ashfall.teknetik.co${p}`, { waitUntil: 'networkidle' }); cur = p; }
  const el = page.locator(sel).first();
  await el.scrollIntoViewIfNeeded();
  await page.waitForTimeout(200);
  const f = path.join(out, `${w}${(p + sel).replace(/[^a-z0-9]+/gi, '_')}.png`);
  await el.screenshot({ path: f });
  console.log(f);
}
await b.close();
