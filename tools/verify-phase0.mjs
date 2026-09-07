import assert from 'node:assert/strict';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { chromium } from '@playwright/test';
import { PNG } from 'pngjs';

const url = process.argv[2] || 'http://127.0.0.1:4173/';
const output = fileURLToPath(new URL('./shots/', import.meta.url));
await mkdir(output, { recursive: true });
const browser = await chromium.launch();
const report = { url, scope: 'Phase 0 pipeline only; not the city performance gate', checks: [], errors: [] };

function pixels(buffer) {
  const png = PNG.sync.read(buffer);
  const colors = new Set();
  let blue = 0;
  for (let i = 0; i < png.data.length; i += 4 * 17) {
    const [r, g, b] = png.data.subarray(i, i + 3);
    colors.add(`${r >> 4},${g >> 4},${b >> 4}`);
    if (b > r * 1.18 && b > g * 1.05 && b > 65) blue++;
  }
  assert(colors.size > 8, 'Canvas must contain multiple rendered colors');
  assert(blue > 80, 'The imported blue probe must be visibly present');
  return { width: png.width, height: png.height, colors: colors.size, blueSamples: blue };
}

try {
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  const page = await context.newPage();
  page.on('pageerror', error => report.errors.push(`page: ${error.message}`));
  page.on('console', message => { if (message.type() === 'error') report.errors.push(`console: ${message.text()}`); });
  page.on('response', response => { if (response.status() >= 400) report.errors.push(`network: ${response.status()} ${response.url()}`); });
  await page.goto(url, { waitUntil: 'networkidle' });
  await page.waitForFunction(() => window.__ATHEN__?.state === 'probe');
  const initial = await page.evaluate(async () => {
    const a = window.__ATHEN__;
    await a.ready;
    return { version: a.version, state: a.state, player: a.player, probe: a.probe, cameras: a.cameras,
      active: a.activeCamera, timeOfDay: a.timeOfDay, functions: [a.shot, a.goto].map(f => typeof f) };
  });
  assert.deepEqual(initial.functions, ['function', 'function']);
  assert.deepEqual(initial.probe.dimensions, { x: 2, y: 2, z: 2 });
  assert.deepEqual(initial.probe.bounds, { min: [-1, 0, -1], max: [1, 2, 1] });
  assert.equal(initial.probe.triangles, 44);
  assert.equal(initial.cameras.length, 6);
  report.initial = initial;
  report.checks.push('Production GLB loaded with exact ground-centred bounds and 44 triangles');

  // Measure normal animation frames separately from screenshots and network work.
  report.performance = await page.evaluate(async () => {
    const times = [];
    await new Promise(resolve => {
      const frame = time => { times.push(time); if (times.length < 181) requestAnimationFrame(frame); else resolve(); };
      requestAnimationFrame(frame);
    });
    const gl = document.querySelector('canvas').getContext('webgl2');
    const extension = gl.getExtension('WEBGL_debug_renderer_info');
    return { fps: 180000 / (times.at(-1) - times[0]),
      renderer: window.__ATHEN__.renderer, userAgent: navigator.userAgent,
      gpu: extension ? gl.getParameter(extension.UNMASKED_RENDERER_WEBGL) : 'unavailable',
      mode: 'Chromium automation on this host, idle probe, DPR 1' };
  });
  assert(report.performance.renderer.draws > 0 && report.performance.renderer.draws <= 80);
  assert(report.performance.renderer.tris > 0 && report.performance.renderer.tris <= 250000);
  await page.screenshot({ path: `${output}phase0-desktop.png` });
  report.desktopPixels = pixels(await page.locator('canvas').screenshot());

  // Exercise the actual form controls, including a repository write.
  await page.getByLabel('View', { exact: true }).selectOption('cam_avenue');
  assert.equal(await page.evaluate(() => window.__ATHEN__.activeCamera), 'cam_avenue');
  await page.getByRole('button', { name: 'Save frame' }).click();
  await page.waitForFunction(() => document.querySelector('#save-status')?.textContent === 'Saved tools/shots/cam_avenue.png');
  report.checks.push('UI selects a camera and saves an actual 1920x1080 PNG');

  const restoreBefore = await page.evaluate(() => ({ camera: window.__ATHEN__.activeCamera, renderer: window.__ATHEN__.renderer }));
  report.captures = await page.evaluate(() => Promise.all(window.__ATHEN__.cameras.map(name => window.__ATHEN__.shot(name))));
  const restoreAfter = await page.evaluate(() => ({ camera: window.__ATHEN__.activeCamera, renderer: window.__ATHEN__.renderer }));
  assert.equal(restoreBefore.camera, restoreAfter.camera);
  for (const key of ['width', 'height', 'pixelRatio', 'draws', 'tris']) assert.equal(restoreBefore.renderer[key], restoreAfter.renderer[key]);
  report.namedPixels = {};
  for (const name of initial.cameras) {
    report.namedPixels[name] = pixels(await readFile(`${output}${name}.png`));
    assert.equal(report.namedPixels[name].width, 1920);
    assert.equal(report.namedPixels[name].height, 1080);
  }
  report.checks.push('Six concurrent captures queue correctly and restore displayed camera, dimensions, DPR and draw counts');

  const anchors = await page.evaluate(() => {
    const a = window.__ATHEN__;
    const result = {};
    for (const name of ['west_gate', 'hill_tree', 'whompah', 'grid_kiosk']) { a.goto(name); result[name] = a.player; }
    a.goto('probe'); a.view('cam_hill');
    let badShot = false, badAnchor = false, badHour = false;
    try { a.goto('__proto__'); } catch { badAnchor = true; }
    try { a.timeOfDay = NaN; } catch { badHour = true; }
    return a.shot('../bad').catch(() => { badShot = true; }).then(() => ({ result, badShot, badAnchor, badHour }));
  });
  assert.equal(anchors.result.west_gate.x, -48);
  assert.equal(anchors.result.grid_kiosk.z, -38);
  assert(anchors.badShot && anchors.badAnchor && anchors.badHour);
  report.anchors = anchors;
  report.checks.push('Landmark anchors work and invalid camera/landmark/time values reject');

  report.responsive = [];
  const fixedHill = await readFile(`${output}cam_hill.png`);
  for (const viewport of [{ width: 1280, height: 720 }, { width: 390, height: 844 }]) {
    await page.setViewportSize(viewport);
    await page.waitForTimeout(100);
    const mode = viewport.width < 600 ? 'mobile' : 'laptop';
    const dimensions = await page.evaluate(() => ({ width: document.documentElement.scrollWidth, viewport: innerWidth }));
    assert(dimensions.width <= dimensions.viewport, 'UI must not overflow horizontally');
    assert(await page.getByRole('button', { name: 'Save frame' }).isVisible());
    const pixelCheck = pixels(await page.locator('canvas').screenshot());
    if (mode === 'mobile') {
      const before = await page.evaluate(() => window.__ATHEN__.cameraTransforms);
      await page.evaluate(() => window.__ATHEN__.shot('cam_hill'));
      assert((await readFile(`${output}cam_hill.png`)).equals(fixedHill), 'Mobile capture must retain the exact fixed desktop composition');
      assert.deepEqual(await page.evaluate(() => window.__ATHEN__.cameraTransforms), before, 'Capture must restore the mobile projection');
    }
    await page.screenshot({ path: `${output}phase0-${mode}.png` });
    report.responsive.push({ mode, viewport, dimensions, pixelCheck });
  }
  report.checks.push('Desktop, laptop and narrow/mobile canvas and UI checks pass');
  assert.deepEqual(report.errors, [], 'Normal browser path must have no console/page/network errors');

  // Deliberate failures are recorded independently from the successful user flow.
  report.endpointRejections = {};
  const origin = new URL(url).origin;
  for (const [name, options, expected] of [
    ['unknown_camera', { method: 'PUT', headers: { Origin: origin, 'Content-Type': 'image/png' }, data: 'bad' }, 400],
    ['cross_origin', { method: 'PUT', headers: { Origin: 'https://example.invalid', 'Content-Type': 'image/png' }, data: 'bad' }, 403],
    ['wrong_method', { method: 'GET', headers: { Origin: origin } }, 405],
    ['malformed_png', { method: 'PUT', headers: { Origin: origin, 'Content-Type': 'image/png' }, data: 'bad' }, 400],
  ]) {
    const path = name === 'unknown_camera' ? 'unknown' : 'cam_hill';
    const response = await context.request.fetch(`${origin}/__athen__/shots/${path}.png`, options);
    report.endpointRejections[name] = response.status();
    assert.equal(response.status(), expected);
  }
  const missing = await context.newPage();
  await missing.route('**/assets/probe.glb', route => route.fulfill({ status: 404, contentType: 'text/plain', body: 'Intentional QA missing asset' }));
  await missing.goto(url);
  await missing.waitForFunction(() => window.__ATHEN__?.state === 'error');
  assert(await missing.getByRole('button', { name: 'Save frame' }).isDisabled());
  report.missingAsset = await missing.locator('#status').innerText();
  await missing.close();
  const unavailable = await context.newPage();
  await unavailable.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (kind, ...args) { return kind === 'webgl2' ? null : original.call(this, kind, ...args); };
  });
  await unavailable.goto(url);
  assert.match(await unavailable.locator('#status').innerText(), /WebGL2 browser is required/);
  assert(await unavailable.getByRole('button', { name: 'Save frame' }).isDisabled());
  await unavailable.close();
  report.checks.push('Missing GLB and unavailable WebGL2 show errors; endpoint rejects invalid inputs and external origins');
  await context.close();
  report.result = 'PASS';
} catch (error) {
  report.result = 'FAIL';
  report.failure = error.stack;
  process.exitCode = 1;
} finally {
  await browser.close();
  await writeFile(`${output}phase0-qa.json`, `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify(report, null, 2));
}
