import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { chromium } from '@playwright/test';
import { MAIN_ROUTE, CAMERAS, wrappedAngle, horizontalDistance, inspectPixels, inspectGLB, assertHealthy } from './phase3-support/checks.mjs';

const args = process.argv.slice(2);
if (args.includes('--help')) {
  console.log('Usage: ATHEN_QA_URL=http://127.0.0.1:5173 node tools/verify-phase3.mjs [URL] [--visual-only] [--headed] [--require-fps]');
  console.log('Full mode verifies authored-world load, retained real-keyboard traversal/collision, six fixed captures, responsive/touch play, budgets and runtime errors.');
  console.log('Every run writes a new tools/phase3-support/runs/<timestamp>/ directory. Visual-only is explicitly PARTIAL.');
  process.exit(0);
}
const knownFlags = new Set(['--visual-only', '--headed', '--require-fps']);
for (const flag of args.filter(value => value.startsWith('--'))) assert(knownFlags.has(flag), `Unknown option: ${flag}`);
const url = args.find(value => !value.startsWith('--')) ?? process.env.ATHEN_QA_URL ?? 'http://127.0.0.1:5173';
assert(['http:', 'https:'].includes(new URL(url).protocol), 'A browser HTTP(S) URL is required');
const visualOnly = args.includes('--visual-only');
const runName = `${new Date().toISOString().replaceAll(':', '-')}-${process.pid}`;
const relativeOutput = `tools/phase3-support/runs/${runName}`;
const output = fileURLToPath(new URL(`./phase3-support/runs/${runName}/`, import.meta.url));
await mkdir(output, { recursive: true });
const report = {
  url, startedAt: new Date().toISOString(), scope: 'Phase 3 authored-world integration regression; later character/dialogue/shop/audio and final visual acceptance remain separate.',
  inputMethod: 'Playwright keyboard and right-mouse drag. The continuous route never teleports or writes simulation state.',
  screenshotMethod: '__ATHEN__.shot renders the six named scene cameras. The harness archives their PNG PUT payloads in this run folder; the local Vite screenshot writer is not tested.',
  output: relativeOutput, mode: visualOnly ? 'visual-only' : 'full',
  referenceLedger: ['qa-release-checklists.md', 'checklists/visual-verification.md', 'checklists/playtest-qa.md', 'checklists/release.md']
    .map(path => ({ path: `threejs-qa-release/references/${path}`, read: true, failure: null })),
  checks: [], errors: [], warnings: [], assets: [], route: [], samples: [], captures: [],
  limitations: ['Automated pixel/geometry checks do not score silhouette, palette or light direction against refs/01–05.',
    'This command does not run npm run build or start/restart a server. Test the separately built preview before a release claim.',
    'Target-laptop 60 fps remains a separate acceptance requirement; browser/GPU and measured FPS are reported.'],
  phaseAcceptance: 'INCOMPLETE: visual scorecard and target-device performance must be reviewed separately.',
};
if (visualOnly) report.limitations.push('Visual-only mode skips the continuous route and focused collision/pause/reset regressions.');
const started = Date.now();
const networkJobs = [];
const capturedImages = new Map();
let browser, page;

function observe(target, label) {
  target.on('pageerror', error => report.errors.push(`${label} page: ${error.message}`));
  target.on('console', message => {
    if (message.type() === 'error') report.errors.push(`${label} console: ${message.text()}`);
    if (message.type() === 'warning') report.warnings.push(`${label}: ${message.text()}`);
  });
  target.on('requestfailed', request => report.errors.push(`${label} request: ${request.failure()?.errorText} ${request.url()}`));
  target.on('response', response => {
    if (response.status() >= 400) report.errors.push(`${label} network: ${response.status()} ${response.url()}`);
  });
}

async function captureAssets(target, label) {
  // Large worlds can exceed Chromium's inspector response cache. Read the
  // network response through route.fetch and deliver those identical bytes to
  // the application, rather than mistaking inspector eviction for asset loss.
  await target.route(/\.glb(?:[?#]|$)/i, async route => {
    const job = (async () => {
      const asset = { browser: label, url: route.request().url(), capture: 'Exact fetched bytes fulfilled to the application' };
      report.assets.push(asset);
      try {
        const response = await route.fetch();
        const body = await response.body();
        asset.status = response.status();
        if (response.ok()) Object.assign(asset, inspectGLB(body));
        await route.fulfill({ response, body });
      } catch (error) {
        report.errors.push(`${label} GLB: ${asset.url}: ${error.message}`);
        await route.abort();
      }
    })();
    networkJobs.push(job);
    await job;
  });
}

async function boot(target) {
  await target.goto(url, { waitUntil: 'networkidle' });
  await target.waitForFunction(() => window.__ATHEN__ && window.__ATHEN__.state !== 'boot', undefined, { timeout: 45000 });
  await target.evaluate(() => window.__ATHEN__.ready);
  await target.waitForTimeout(300);
  const identity = await target.evaluate(() => ({ phase: window.__ATHEN__.phase, state: window.__ATHEN__.state,
    version: window.__ATHEN__.version, error: window.__ATHEN__.error }));
  assert(identity.phase >= 3, `Expected Phase 3 or later, found ${identity.version} (phase ${identity.phase}); a greybox cannot pass authored-world QA`);
  assert.equal(identity.state, 'play', `City failed to become playable: ${identity.error}`);
  return identity;
}

async function snapshot(target = page) {
  return target.evaluate(() => ({ player: window.__ATHEN__.player, camera: window.__ATHEN__.camera,
    state: window.__ATHEN__.state, activeCamera: window.__ATHEN__.activeCamera, error: window.__ATHEN__.error,
    physics: window.__ATHEN__.physics, renderer: window.__ATHEN__.renderer,
    world: window.__ATHEN__.world ?? window.__ATHEN__.worldDiagnostics ?? window.__THREE_GAME_DIAGNOSTICS__?.world ?? null }));
}

function healthy(sample, label) {
  assertHealthy(sample, label, report.initial.colliders);
  report.samples.push({ label, elapsedMs: Date.now() - started, ...sample });
}

async function release(target = page) {
  for (const key of ['w', 'a', 's', 'd', 'Shift', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight']) await target.keyboard.up(key);
}

async function orient(yaw) {
  for (let attempt = 0; attempt < 8; attempt++) {
    const current = await page.evaluate(() => window.__ATHEN__.camera.yaw);
    const difference = wrappedAngle(yaw - current);
    if (Math.abs(difference) < 0.008) return;
    const dx = Math.max(-450, Math.min(450, difference / report.orbitRadiansPerPixel));
    const viewport = page.viewportSize();
    await page.mouse.move(viewport.width / 2 - dx / 2, viewport.height / 2);
    await page.mouse.down({ button: 'right' });
    await page.mouse.move(viewport.width / 2 + dx / 2, viewport.height / 2, { steps: 3 });
    await page.mouse.up({ button: 'right' });
  }
  assert(Math.abs(wrappedAngle(yaw - (await snapshot()).camera.yaw)) < 0.015, 'RMB drag can orient the camera');
}

async function walkTo(name, coordinates, { sprint = false, tolerance = 0.28, timeout = 45000 } = {}) {
  const target = { x: coordinates[0], y: coordinates[1], z: coordinates[2] };
  const begin = await snapshot();
  const start = Date.now();
  let lastDistance = horizontalDistance(begin.player, target), lastProgress = start, samples = 0;
  try {
    await orient(Math.atan2(-(target.x - begin.player.x), -(target.z - begin.player.z)));
    if (sprint) await page.keyboard.down('Shift');
    await page.keyboard.down('w');
    while (true) {
      await page.waitForTimeout(85);
      const current = await snapshot(); healthy(current, name); samples++;
      const remaining = horizontalDistance(current.player, target);
      if (remaining <= tolerance) break;
      if (remaining < lastDistance - 0.08) { lastDistance = remaining; lastProgress = Date.now(); }
      assert(Date.now() - lastProgress < 5000, `${name}: blocked for five seconds at ${JSON.stringify(current.player)}`);
      assert(Date.now() - start < timeout, `${name}: did not reach target within ${timeout}ms`);
      const desired = Math.atan2(-(target.x - current.player.x), -(target.z - current.player.z));
      if (Math.abs(wrappedAngle(desired - current.camera.yaw)) > 0.065) {
        await page.keyboard.up('w'); await orient(desired); await page.keyboard.down('w');
      }
    }
  } finally { await release(); }
  await page.waitForTimeout(150);
  const end = await snapshot(); healthy(end, `${name}:settled`);
  assert(Math.abs(end.player.y - target.y) <= 0.12, `${name}: expected support height ${target.y}, got ${end.player.y}`);
  assert(end.player.grounded, `${name}: must settle grounded`);
  const entry = { name, target, begin: begin.player, end: end.player, samples, durationMs: Date.now() - start, sprint };
  report.route.push(entry); console.log(`PASS traversal: ${name}`);
}

async function hold(keys, duration, label) {
  for (const key of keys) await page.keyboard.down(key);
  const samples = [];
  try {
    const begin = Date.now();
    while (Date.now() - begin < duration) {
      await page.waitForTimeout(100);
      const sample = await snapshot(); healthy(sample, label); samples.push(sample);
    }
  } finally { await release(); }
  await page.waitForTimeout(120);
  return samples;
}

async function captureActive(target, name) {
  const pixelCheck = inspectPixels(await target.locator('canvas').screenshot());
  await target.screenshot({ path: `${output}${name}.png` });
  return { path: `${relativeOutput}/${name}.png`, pixelCheck, state: await snapshot(target) };
}

async function inspectLayout(target) {
  return target.evaluate(() => {
    const visible = [...document.querySelectorAll('button, select')].filter(e => !e.closest('details:not([open]), [hidden]')
      && e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden');
    return { documentWidth: document.documentElement.scrollWidth, viewport: innerWidth, height: innerHeight,
      controls: visible.map(e => { const r = e.getBoundingClientRect(); return { label: e.textContent || e.getAttribute('aria-label'),
        x: r.x, y: r.y, width: r.width, height: r.height, fits: r.x >= 0 && r.y >= 0 && r.right <= innerWidth + 1 && r.bottom <= innerHeight + 1 }; }) };
  });
}

try {
  const headed = args.includes('--headed');
  const launchArgs = headed && process.platform === 'darwin' ? ['--use-angle=metal'] : [];
  browser = await chromium.launch({ headless: !headed, args: launchArgs });
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  page = await context.newPage(); observe(page, 'desktop'); await captureAssets(page, 'desktop');
  // Exercise the application's screenshot renderer without replacing older evidence files.
  await page.route('**/__athen__/shots/*.png', async route => {
    const request = route.request();
    const camera = /\/([^/]+)\.png$/.exec(new URL(request.url()).pathname)?.[1];
    if (request.method() !== 'PUT' || !CAMERAS.includes(camera)) return route.continue();
    try {
      const png = request.postDataBuffer();
      const pixels = inspectPixels(png);
      assert.equal(pixels.width, 1920); assert.equal(pixels.height, 1080);
      capturedImages.set(camera, { buffer: png, pixels });
      await writeFile(`${output}${camera}.png`, png);
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ path: `${relativeOutput}/${camera}.png` }) });
    } catch (error) {
      report.errors.push(`Capture ${camera}: ${error.message}`);
      await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ error: error.message }) });
    }
  });
  report.identity = await boot(page);
  report.browser = await page.evaluate(() => {
    const gl = document.querySelector('canvas').getContext('webgl2');
    const extension = gl.getExtension('WEBGL_debug_renderer_info');
    return { gpu: extension ? gl.getParameter(extension.UNMASKED_RENDERER_WEBGL) : 'unavailable',
      userAgent: navigator.userAgent, initialFps: window.__ATHEN__.fps };
  });
  report.browser.launchArgs = launchArgs;
  console.log(`Renderer: ${report.browser.gpu}; initial FPS: ${report.browser.initialFps.toFixed(1)}`);
  await Promise.all(networkJobs);
  report.initial = await page.evaluate(() => ({ version: window.__ATHEN__.version, phase: window.__ATHEN__.phase,
    player: window.__ATHEN__.player, physics: window.__ATHEN__.physics, landmarks: window.__ATHEN__.landmarks,
    colliders: window.__ATHEN__.colliders, cameras: window.__ATHEN__.cameras, cameraTransforms: window.__ATHEN__.cameraTransforms,
    scope: window.__ATHEN__.scope, world: window.__ATHEN__.world ?? window.__ATHEN__.worldDiagnostics ?? window.__THREE_GAME_DIAGNOSTICS__?.world ?? null }));
  assert.deepEqual([...report.initial.cameras].sort(), [...CAMERAS].sort(), 'All six fixed scene cameras must exist');
  for (const camera of Object.values(report.initial.cameraTransforms)) assert(camera.sceneObject, 'Named cameras must be objects in the live scene');
  assert(report.initial.colliders.length > 15, 'Imported city must retain collision beyond flat pavement');
  assert.equal(report.initial.physics.bodies, 1); assert.equal(report.initial.physics.characterControllers, 1);
  assert(Math.abs(report.initial.physics.timestep - 1 / 60) < 1e-8, 'Physics remains on a 60 Hz fixed step');
  const world = report.assets.find(asset => asset.browser === 'desktop' && /\/world\.glb(?:[?#]|$)/i.test(asset.url));
  assert(world?.status === 200 && world.meshCount > 0, 'The browser must load an authored world.glb, not only the Phase 0 probe');
  assert(world.collisionNodes.length > 0, 'The authored GLB must include separate COL_ collision proxies');
  if (report.initial.world?.loaded !== undefined) assert(report.initial.world.loaded, 'World loader reports successful authored integration');
  if (Array.isArray(report.initial.world?.greyboxLandmarks)) assert.equal(report.initial.world.greyboxLandmarks.length, 0,
    `Phase 3 authored world is incomplete: ${report.initial.world.greyboxLandmarks.join(', ')} still use greybox geometry`);
  if (!report.initial.world) report.limitations.push('No public world integration diagnostics were exposed; the report contains live GLB/network evidence only.');
  healthy(await snapshot(), 'spawn');
  report.checks.push('Phase >= 3, live authored world.glb loads as valid GLB with separate collision nodes, six scene cameras and fixed-step physics');

  await page.locator('canvas').click({ position: { x: 800, y: 400 } });
  const initialYaw = (await snapshot()).camera.yaw;
  await page.mouse.move(900, 450); await page.mouse.down({ button: 'right' });
  await page.mouse.move(1000, 450, { steps: 3 }); await page.mouse.up({ button: 'right' });
  report.orbitRadiansPerPixel = wrappedAngle((await snapshot()).camera.yaw - initialYaw) / 100;
  assert(Math.abs(report.orbitRadiansPerPixel) > 0.0001, 'RMB drag must orbit the camera');
  const routeStarted = Date.now();
  if (!visualOnly) {
    for (const [name, target] of MAIN_ROUTE) await walkTo(name, target);
    report.checks.push('Continuous keyboard traversal: west spawn, hill steps/plaza, Ring Gate, west bypass, Lattice Jack; no teleports');
  } else { await orient(-Math.PI / 2); await hold(['w'], 700, 'desktop active input'); }
  report.mainRoute = { completed: !visualOnly, teleportCount: 0, durationMs: Date.now() - routeStarted };
  report.desktopActive = await captureActive(page, 'desktop-active');

  if (!visualOnly) {
    // Public teleports only set up the following independent collision regressions.
    await page.evaluate(() => window.__ATHEN__.goto('shop_row_e'));
    await walkTo('east shop porch approach', [12, 0, 9]);
    await walkTo('east shop stairs ascent', [16, 0.5, 9]);
    await walkTo('east shop doorway and stage', [20, 0.5, 9]);
    await orient(Math.PI / 2); await page.waitForTimeout(500);
    report.cameraOcclusion = await snapshot();
    assert(report.cameraOcclusion.camera.obstructed, 'Shop back wall must obstruct the camera boom');
    assert(report.cameraOcclusion.camera.distance < report.cameraOcclusion.camera.desiredDistance - 0.2);
    await page.screenshot({ path: `${output}shop-camera-occlusion.png` });
    await walkTo('east shop stairs descent', [12, 0, 9]); await page.waitForTimeout(400);
    report.cameraRecovery = await snapshot();
    assert(report.cameraRecovery.camera.distance > report.cameraOcclusion.camera.distance + 0.2, 'Boom must recover outside the shop');
    await page.evaluate(() => window.__ATHEN__.goto('west_gate'));
    await walkTo('west gate tunnel passage', [-52, 0, 0]);
    await walkTo('west gate tunnel standing clearance', [-48, 0, 0]);
    await page.screenshot({ path: `${output}west-gate-tunnel.png` });
    report.checks.push('Authored shop porch/stage stair access, camera obstruction/recovery and standable west gate tunnel');

    await page.evaluate(() => window.__ATHEN__.goto('ring_gate'));
    await walkTo('wall test departure', [0, 0, 31]);
    await walkTo('wall test approach', [40, 0, 31], { sprint: true });
    await walkTo('wall test runup', [55, 0, 31], { sprint: true });
    await orient(-Math.PI / 2);
    const wall = await hold(['Shift', 'w'], 1600, 'sprint into city wall');
    report.wall = { start: wall[0].player, end: (await snapshot()).player,
      contacts: [...new Set(wall.flatMap(sample => sample.player.collisions))] };
    assert(report.wall.end.x < 59 && report.wall.end.x > 56 && report.wall.contacts.length > 0, 'Sprint must stop with contacts at the east boundary');
    await orient(-Math.PI / 4);
    const slide = await hold(['Shift', 'w'], 1300, 'diagonal wall slide');
    report.wallSlide = { start: slide[0].player, end: (await snapshot()).player };
    assert(report.wallSlide.end.z < report.wallSlide.start.z - 2 && report.wallSlide.end.x < 59, 'Diagonal input slides along the wall without escaping');

    await orient(Math.PI / 2); await page.keyboard.down('w'); await page.waitForTimeout(350);
    await page.evaluate(() => window.dispatchEvent(new Event('blur'))); await page.waitForTimeout(150);
    const blurStart = await snapshot(); await page.waitForTimeout(450); const blurEnd = await snapshot(); await release();
    assert(horizontalDistance(blurStart.player, blurEnd.player) < 0.03, 'Blur clears movement input');
    await page.keyboard.press('Escape'); await page.waitForTimeout(100);
    const paused = await snapshot(); assert.equal(paused.state, 'paused');
    await page.keyboard.down('w'); await page.waitForTimeout(350); await page.keyboard.up('w');
    assert.deepEqual((await snapshot()).player, paused.player, 'Pause must freeze player movement');
    await page.keyboard.press('Escape'); await page.waitForTimeout(150);
    const physicsBefore = (await snapshot()).physics;
    await page.keyboard.press('r'); await page.waitForTimeout(200); report.reset = await snapshot();
    assert(horizontalDistance(report.reset.player, report.initial.player) < 0.02, 'R restores the west spawn');
    assert(report.reset.player.grounded && Math.abs(report.reset.player.y) < 0.08);
    for (const key of ['bodies', 'colliders', 'staticColliders', 'characterControllers']) assert.equal(report.reset.physics[key], physicsBefore[key], `Reset cannot leak physics ${key}`);
    report.checks.push('Sprint wall collision/slide, blur input release, pause/resume and clean grounded reset');
  }

  await page.keyboard.press('r'); await page.waitForTimeout(150); await orient(-Math.PI / 2);
  await page.keyboard.down('w');
  try {
    report.performance = await page.evaluate(async () => {
      const times = [], renderers = [];
      await new Promise(resolve => {
        const frame = time => { times.push(time); renderers.push(window.__ATHEN__.renderer);
          if (times.length < 121) requestAnimationFrame(frame); else resolve(); };
        requestAnimationFrame(frame);
      });
      const gl = document.querySelector('canvas').getContext('webgl2');
      const extension = gl.getExtension('WEBGL_debug_renderer_info');
      const frameMs = times.slice(1).map((time, index) => time - times[index]).sort((a, b) => a - b);
      return { fps: 120000 / (times.at(-1) - times[0]), medianFrameMs: frameMs[Math.floor(frameMs.length / 2)],
        p95FrameMs: frameMs[Math.floor(frameMs.length * 0.95)], maxFrameMs: frameMs.at(-1),
        maxDraws: Math.max(...renderers.map(r => r.draws)), maxTris: Math.max(...renderers.map(r => r.tris)),
        renderer: window.__ATHEN__.renderer, userAgent: navigator.userAgent,
        gpu: extension ? gl.getParameter(extension.UNMASKED_RENDERER_WEBGL) : 'unavailable',
        physics: window.__ATHEN__.physics, mode: 'Chromium, actual keyboard movement, 1920 × 1080, DPR 1' };
    });
  } finally { await release(); }
  assert(report.performance.maxDraws <= 80 && report.performance.maxTris <= 250000, 'Moving view must meet renderer budgets');
  report.performance.meets58Fps = report.performance.fps >= 58;
  report.performance.softwareGPU = /swiftshader|llvmpipe|software/i.test(report.performance.gpu);
  if (report.performance.softwareGPU) report.limitations.push('This browser reports software rendering; its FPS cannot establish laptop-GPU acceptance.');
  if (args.includes('--require-fps')) assert(report.performance.meets58Fps, `Explicit FPS gate failed: ${report.performance.fps.toFixed(1)} < 58`);
  report.checks.push('1080p active-play renderer counts remain within 80 draws and 250k triangles; FPS/GPU recorded');

  await page.keyboard.press('r'); await page.waitForTimeout(200);
  await page.evaluate(() => window.__ATHEN__.pause(true));
  const captureState = () => page.evaluate(() => ({ player: window.__ATHEN__.player, active: window.__ATHEN__.activeCamera,
    camera: window.__ATHEN__.camera, transforms: window.__ATHEN__.cameraTransforms, renderer: window.__ATHEN__.renderer }));
  const before = await captureState();
  const paths = await page.evaluate(() => Promise.all(window.__ATHEN__.cameras.map(name => window.__ATHEN__.shot(name))));
  const after = await captureState();
  assert.deepEqual(after.player, before.player, 'Named captures preserve the paused player pose');
  assert.equal(after.active, before.active); assert.deepEqual(after.transforms, before.transforms);
  for (const key of ['width', 'height', 'pixelRatio', 'draws', 'tris']) assert.equal(after.renderer[key], before.renderer[key], `Captures restore renderer ${key}`);
  for (const [index, camera] of report.initial.cameras.entries()) {
    assert(capturedImages.has(camera), `shot(${camera}) must produce a real PNG request`);
    report.captures.push({ camera, path: paths[index], ...capturedImages.get(camera).pixels });
  }
  report.checks.push('Six fixed 1080p camera PNGs generated through shot(), with exact paused pose/projection/renderer restoration');
  await page.evaluate(() => window.__ATHEN__.pause(false));

  report.responsive = [];
  await page.setViewportSize({ width: 1280, height: 720 }); await page.waitForTimeout(200);
  const laptopFit = await inspectLayout(page);
  assert(laptopFit.documentWidth <= laptopFit.viewport && laptopFit.controls.every(control => control.fits), 'Laptop controls fit without horizontal overflow');
  report.responsive.push({ mode: 'laptop', fit: laptopFit, capture: await captureActive(page, 'laptop') });
  const mobileContext = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1, isMobile: true, hasTouch: true });
  const mobile = await mobileContext.newPage(); observe(mobile, 'mobile'); await captureAssets(mobile, 'mobile'); await boot(mobile);
  const forward = mobile.locator('[data-move="forward"]');
  assert(await forward.isVisible(), 'Touch movement control must be visible');
  const rect = await forward.boundingBox();
  assert(rect && rect.width >= 40 && rect.height >= 40, 'Touch target must be usable');
  const cdp = await mobileContext.newCDPSession(mobile);
  const touchPoint = [{ x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 }];
  const touchStart = (await snapshot(mobile)).player;
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: touchPoint }); await mobile.waitForTimeout(500);
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] }); await mobile.waitForTimeout(150);
  const touchEnd = (await snapshot(mobile)).player;
  assert(horizontalDistance(touchStart, touchEnd) > 0.5, 'Holding touch forward moves the actual capsule');
  await mobile.waitForTimeout(350);
  assert(horizontalDistance(touchEnd, (await snapshot(mobile)).player) < 0.03, 'Touch release stops movement');
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: touchPoint }); await mobile.waitForTimeout(300);
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchCancel', touchPoints: [] }); await mobile.waitForTimeout(150);
  const cancelStart = (await snapshot(mobile)).player; await mobile.waitForTimeout(350);
  assert(horizontalDistance(cancelStart, (await snapshot(mobile)).player) < 0.03, 'Touch cancel stops movement');
  report.touch = { start: touchStart, end: touchEnd, target: rect };
  const mobileFit = await inspectLayout(mobile);
  assert(mobileFit.documentWidth <= mobileFit.viewport && mobileFit.controls.every(control => control.fits), 'Mobile controls fit without horizontal overflow');
  report.mobileActive = await captureActive(mobile, 'mobile-active');
  assertHealthy(report.mobileActive.state, 'mobile active play', report.initial.colliders);
  report.responsive.push({ mode: 'mobile', fit: mobileFit });
  report.checks.push('Laptop/mobile fit, real touch movement and release/cancel without stuck input; active mobile screenshot');
  await Promise.all(networkJobs);
  assert.deepEqual(report.errors, [], 'Normal authored-world play must have no page/console/network/GLB errors');
  report.result = visualOnly ? 'PARTIAL' : 'PASS';
} catch (error) {
  report.result = 'FAIL'; report.failure = error.stack; process.exitCode = 1;
  if (page) {
    try { await release(); report.failureState = await snapshot(); await page.screenshot({ path: `${output}failure.png` }); } catch {}
  }
} finally {
  await Promise.allSettled(networkJobs);
  await browser?.close();
  report.elapsedMs = Date.now() - started;
  await writeFile(`${output}report.json`, `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify({ result: report.result, scope: report.scope, output: report.output, elapsedMs: report.elapsedMs,
    checks: report.checks, mainRoute: report.mainRoute, performance: report.performance, captures: report.captures,
    sampleCount: report.samples.length, errors: report.errors, failure: report.failure, limitations: report.limitations,
    phaseAcceptance: report.phaseAcceptance }, null, 2));
}
