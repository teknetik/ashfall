import assert from 'node:assert/strict';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { chromium } from '@playwright/test';

const base = process.env.ATHEN_QA_URL ?? 'http://127.0.0.1:4173';
const live = process.argv.includes('--live');
const run = new Date().toISOString().replaceAll(':', '-');
const directory = `tools/character-replacement/runs/${run}`;
await mkdir(directory, { recursive: true });
const candidate = await readFile(`public/assets/${live ? 'player' : 'player-candidate'}.glb`);
const report = { run, directory, base, asset: live ? 'live player.glb' : 'candidate routed to unchanged player.glb URL',
  candidateBytes: candidate.length, sha256: createHash('sha256').update(candidate).digest('hex'),
  errors: [], warnings: [], captures: [], samples: [],
  limitations: ['GPU evidence is this native Mac only.', 'Geometry and gameplay checks do not establish reference likeness.'] };
const browser = await chromium.launch({ headless: false, args: ['--use-angle=metal'] });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
page.on('pageerror', error => report.errors.push(error.message));
page.on('console', message => { if (message.type() === 'error') report.errors.push(message.text());
  if (message.type() === 'warning') report.warnings.push(message.text()); });
page.on('requestfailed', request => report.errors.push(`${request.failure()?.errorText}: ${request.url()}`));
await page.route(/\.glb(?:[?#]|$)/, async route => {
  if (route.request().url().endsWith('/player.glb')) {
    await route.fulfill({ status: 200, contentType: 'model/gltf-binary', body: candidate });
  } else {
    const response = await route.fetch();
    await route.fulfill({ response, body: await response.body() });
  }
});
const sample = label => page.evaluate(label => ({ label, state: window.__ATHEN__.state, error: window.__ATHEN__.error,
  player: window.__ATHEN__.player, animation: window.__ATHEN__.playerAnimation,
  renderer: window.__ATHEN__.renderer, assets: window.__ATHEN__.characters,
  camera: window.__ATHEN__.camera }), label);
async function capture(name) {
  await page.screenshot({ path: `${directory}/${name}.png` });
  report.captures.push(`${directory}/${name}.png`);
}
try {
  await page.goto(base, { waitUntil: 'networkidle' });
  await page.waitForFunction(() => window.__ATHEN__ && window.__ATHEN__.state !== 'boot', null, { timeout: 60000 });
  await page.evaluate(() => window.__ATHEN__.ready);
  await page.waitForTimeout(1500);
  report.initial = await sample('initial');
  assert.equal(report.initial.state, 'play', report.initial.error);
  assert.equal(report.initial.assets.assets.player.bytes, candidate.length);
  await page.evaluate(() => window.__ATHEN__.view('character'));
  await page.waitForTimeout(150);
  await capture('character-full');
  const clean = await page.addStyleTag({ content: '.play-hud { visibility: hidden !important; }' });
  await capture('character-full-clean');
  await clean.evaluate(node => node.remove());
  await page.evaluate(() => window.__ATHEN__.view('portrait'));
  await page.waitForTimeout(150);
  await capture('character-portrait');
  const cleanPortrait = await page.addStyleTag({ content: '.play-hud { visibility: hidden !important; }' });
  await capture('character-portrait-clean');
  await cleanPortrait.evaluate(node => node.remove());
  report.reviewFraming = 'Live world and animated player; additional -clean captures hide only the HUD for unobstructed review.';
  await page.evaluate(() => window.__ATHEN__.view('follow'));
  await page.keyboard.down('w');
  await page.waitForTimeout(900);
  report.samples.push(await sample('walk'));
  await capture('walk');
  await page.keyboard.down('Shift');
  await page.waitForTimeout(700);
  report.samples.push(await sample('run'));
  await capture('run');
  await page.keyboard.up('Shift');
  await page.keyboard.up('w');
  await page.waitForTimeout(500);
  report.samples.push(await sample('idle'));
  assert.equal(report.samples[0].animation.animation, 'walk');
  assert.equal(report.samples[1].animation.animation, 'run');
  assert.equal(report.samples[2].animation.animation, 'idle');
  for (const name of ['cam_gate', 'cam_avenue', 'cam_hill', 'cam_grid', 'cam_whompah', 'cam_hero']) {
    await page.evaluate(name => window.__ATHEN__.view(name), name);
    await page.waitForTimeout(200);
    await capture(name);
    report.samples.push(await sample(name));
  }
  await page.evaluate(() => window.__ATHEN__.view('follow'));
  await page.waitForTimeout(2000);
  report.performance = await page.evaluate(() => ({ fps: window.__ATHEN__.fps, draws: window.__ATHEN__.draws,
    tris: window.__ATHEN__.tris, renderer: window.__ATHEN__.renderer }));
  assert(report.performance.fps >= 58);
  assert(report.samples.every(s => s.renderer.draws <= 80 && s.renderer.tris <= 250000));
  assert.equal(report.errors.length, 0);
  report.result = 'PASS';
} catch (error) {
  report.result = 'FAIL';
  report.failure = error.stack;
  await capture('failure');
  process.exitCode = 1;
} finally {
  await writeFile(`${directory}/report.json`, JSON.stringify(report, null, 2));
  await browser.close();
  console.log(JSON.stringify({ result: report.result, directory, failure: report.failure,
    performance: report.performance, errors: report.errors }, null, 2));
}
