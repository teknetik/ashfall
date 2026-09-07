import assert from 'node:assert/strict';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { chromium } from '@playwright/test';
import { PNG } from 'pngjs';

const url = process.argv[2] || 'http://127.0.0.1:4173/';
const visualOnly = process.argv.includes('--visual-only');
const focusedOnly = process.argv.includes('--focused') || visualOnly;
const output = fileURLToPath(new URL('./shots/', import.meta.url));
await mkdir(output, { recursive: true });
const browser = await chromium.launch();
const report = {
  url, scope: 'Phase 1 greybox traversal and collision; no Phase 2 art or NPC acceptance',
  inputMethod: 'Playwright keyboard and right-mouse drag. The main route never teleports or writes simulation state.',
  referenceLedger: [
    ['threejs-qa-release/references/qa-release-checklists.md', true],
    ['threejs-qa-release/references/checklists/visual-verification.md', true],
    ['threejs-qa-release/references/checklists/playtest-qa.md', true],
    ['threejs-qa-release/references/checklists/release.md', true],
    ['threejs-game-ui-designer/references/checklists/game-ui-quality.md', true],
    ['threejs-game-ui-designer/references/checklists/hud-readability.md', true],
    ['threejs-game-ui-designer/references/checklists/responsive-ui-fit.md', true],
    ['threejs-aaa-graphics-builder/references/checklists/procedural-model-quality.md', true],
    ['threejs-aaa-graphics-builder/references/checklists/material-lighting-quality.md', true],
    ['threejs-aaa-graphics-builder/references/checklists/performance-safe-visual-detail.md', true],
  ].map(([path, read]) => ({ path, read, failure: null })),
  checks: [], errors: [], route: [], samples: [], limitations: [],
};
let page;
const started = Date.now();
const wrappedAngle = value => Math.atan2(Math.sin(value), Math.cos(value));
const horizontalDistance = (a, b) => Math.hypot(a.x - b.x, a.z - b.z);

function pixels(buffer) {
  const png = PNG.sync.read(buffer);
  const colors = new Set();
  let min = 255, max = 0, lit = 0;
  for (let i = 0; i < png.data.length; i += 4 * 19) {
    const [r, g, b] = png.data.subarray(i, i + 3);
    colors.add(`${r >> 4},${g >> 4},${b >> 4}`);
    const intensity = (r + g + b) / 3;
    min = Math.min(min, intensity); max = Math.max(max, intensity);
    if (intensity > 20) lit++;
  }
  assert(colors.size > 16 && max - min > 45 && lit > 100, 'Canvas must contain nonblank, varied scene pixels');
  return { width: png.width, height: png.height, colors: colors.size, intensityRange: max - min };
}

async function snapshot() {
  return page.evaluate(() => ({ player: window.__ATHEN__.player, camera: window.__ATHEN__.camera,
    state: window.__ATHEN__.state, activeCamera: window.__ATHEN__.activeCamera,
    physics: window.__ATHEN__.physics, renderer: window.__ATHEN__.renderer }));
}

function healthy(sample, label) {
  const p = sample.player;
  assert([p.x, p.y, p.z, p.yaw].every(Number.isFinite), `${label}: player coordinates remain finite`);
  assert(p.y >= -0.08, `${label}: feet fell below pavement (${p.y})`);
  assert(Math.abs(p.x) < 60 && Math.abs(p.z) < 46, `${label}: escaped the city collision boundary`);
  assert.equal(sample.state, 'play', `${label}: simulation must remain playable`);
  assert(sample.renderer.draws > 0 && sample.renderer.draws <= 80, `${label}: draw budget exceeded (${sample.renderer.draws})`);
  assert(sample.renderer.tris > 0 && sample.renderer.tris <= 250000, `${label}: triangle budget exceeded`);
  // A conservative capsule-vs-proxy separation check supplements the controller's own contacts.
  // This catches a body stopped inside a wall even when it never falls under the pavement.
  const radius = 0.35;
  const bottom = p.y + radius, top = p.y + 1.8 - radius;
  for (const collider of report.initial?.colliders ?? []) {
    if (collider.kind === 'halfspace') {
      assert(p.y >= collider.position[1] - 0.04, `${label}: feet penetrated the flat pavement plane`);
      continue;
    }
    if (collider.rotation) continue; // Rotated rubble receives runtime swept collision coverage.
    const [x, y, z] = collider.position;
    const halfY = collider.kind === 'box' ? collider.halfExtents[1] : collider.halfHeight;
    const dy = Math.max(y - halfY - top, bottom - y - halfY, 0);
    let horizontal;
    if (collider.kind === 'box') {
      horizontal = Math.hypot(Math.max(Math.abs(p.x - x) - collider.halfExtents[0], 0),
        Math.max(Math.abs(p.z - z) - collider.halfExtents[2], 0));
    } else horizontal = Math.max(0, Math.hypot(p.x - x, p.z - z) - collider.radius);
    assert(Math.hypot(horizontal, dy) >= radius - 0.04, `${label}: capsule penetrated ${collider.name}`);
  }
  report.samples.push({ label, elapsedMs: Date.now() - started, ...sample });
}

async function orient(yaw) {
  // Read-only diagnostics close the loop; the only camera change is a real RMB drag.
  for (let attempt = 0; attempt < 6; attempt++) {
    const current = await page.evaluate(() => window.__ATHEN__.camera.yaw);
    const difference = wrappedAngle(yaw - current);
    if (Math.abs(difference) < 0.008) return;
    const dx = Math.max(-450, Math.min(450, difference / report.orbitRadiansPerPixel));
    const viewport = page.viewportSize();
    const startX = viewport.width / 2 - dx / 2;
    const startY = viewport.height / 2;
    await page.mouse.move(startX, startY);
    await page.mouse.down({ button: 'right' });
    await page.mouse.move(startX + dx, startY, { steps: 3 });
    await page.mouse.up({ button: 'right' });
  }
  const final = await page.evaluate(() => window.__ATHEN__.camera.yaw);
  assert(Math.abs(wrappedAngle(yaw - final)) < 0.015, 'Right-drag camera can orient to the intended route');
}

async function release() {
  for (const key of ['w', 'a', 's', 'd', 'Shift', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight']) await page.keyboard.up(key);
}

async function walkTo(name, coordinates, { sprint = false, tolerance = 0.28, timeout = 30000 } = {}) {
  const target = { x: coordinates[0], y: coordinates[1], z: coordinates[2] };
  const begin = await snapshot();
  const start = Date.now();
  let lastDistance = horizontalDistance(begin.player, target);
  let lastProgress = start;
  let samples = 0;
  try {
    await orient(Math.atan2(-(target.x - begin.player.x), -(target.z - begin.player.z)));
    if (sprint) await page.keyboard.down('Shift');
    await page.keyboard.down('w');
    while (true) {
      await page.waitForTimeout(85);
      const current = await snapshot();
      healthy(current, name);
      samples++;
      const remaining = horizontalDistance(current.player, target);
      if (remaining <= tolerance) break;
      if (remaining < lastDistance - 0.08) { lastDistance = remaining; lastProgress = Date.now(); }
      assert(Date.now() - lastProgress < 4000, `${name}: blocked for four seconds at ${JSON.stringify(current.player)}`);
      assert(Date.now() - start < timeout, `${name}: did not reach target within ${timeout}ms`);
      // Rounded mouse pixels or wall sliding can change the bearing; release before steering.
      const desired = Math.atan2(-(target.x - current.player.x), -(target.z - current.player.z));
      if (Math.abs(wrappedAngle(desired - current.camera.yaw)) > 0.065) {
        await page.keyboard.up('w'); await orient(desired); await page.keyboard.down('w');
      }
    }
  } finally { await release(); }
  await page.waitForTimeout(150);
  const end = await snapshot();
  healthy(end, `${name}:settled`);
  assert(Math.abs(end.player.y - target.y) <= 0.12, `${name}: expected support height ${target.y}, got ${end.player.y}`);
  assert(end.player.grounded, `${name}: must settle grounded`);
  const entry = { name, target, begin: begin.player, end: end.player, samples, durationMs: Date.now() - start, sprint };
  report.route.push(entry);
  console.log(`PASS traversal: ${name} (${entry.durationMs}ms)`);
  return entry;
}

async function hold(keys, duration, label) {
  for (const key of keys) await page.keyboard.down(key);
  const samples = [];
  try {
    const start = Date.now();
    while (Date.now() - start < duration) {
      await page.waitForTimeout(100);
      const sample = await snapshot(); healthy(sample, label); samples.push(sample);
    }
  } finally { await release(); }
  await page.waitForTimeout(120);
  return samples;
}

try {
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  page = await context.newPage();
  page.on('pageerror', error => report.errors.push(`page: ${error.message}`));
  page.on('console', message => { if (message.type() === 'error') report.errors.push(`console: ${message.text()}`); });
  page.on('response', response => { if (response.status() >= 400) report.errors.push(`network: ${response.status()} ${response.url()}`); });
  page.on('requestfailed', request => report.errors.push(`request: ${request.failure()?.errorText} ${request.url()}`));
  await page.goto(url, { waitUntil: 'networkidle' });
  await page.waitForFunction(() => window.__ATHEN__?.state === 'play');
  await page.evaluate(() => window.__ATHEN__.ready);
  await page.waitForTimeout(250);
  report.initial = await page.evaluate(() => ({ version: window.__ATHEN__.version, phase: window.__ATHEN__.phase,
    player: window.__ATHEN__.player, physics: window.__ATHEN__.physics, landmarks: window.__ATHEN__.landmarks,
    colliders: window.__ATHEN__.colliders, cameras: window.__ATHEN__.cameras, scope: window.__ATHEN__.scope }));
  assert.equal(report.initial.phase, 1);
  assert.equal(report.initial.cameras.length, 6);
  assert(report.initial.colliders.length > 15, 'City must have collision geometry, not only a pavement plane');
  assert.equal(report.initial.physics.bodies, 1);
  assert.equal(report.initial.physics.characterControllers, 1);
  assert(Math.abs(report.initial.physics.timestep - 1 / 60) < 1e-8, 'Physics uses a 60 Hz fixed timestep');
  healthy(await snapshot(), 'spawn');

  await page.locator('canvas').click({ position: { x: 800, y: 400 } });
  const initialYaw = await page.evaluate(() => window.__ATHEN__.camera.yaw);
  await page.mouse.move(900, 450); await page.mouse.down({ button: 'right' });
  await page.mouse.move(1000, 450, { steps: 3 }); await page.mouse.up({ button: 'right' });
  report.orbitRadiansPerPixel = wrappedAngle(await page.evaluate(() => window.__ATHEN__.camera.yaw) - initialYaw) / 100;
  assert(Math.abs(report.orbitRadiansPerPixel) > 0.0001, 'RMB drag must orbit the camera');
  await orient(-Math.PI / 2);

  // A single uninterrupted player route from the actual spawn. No goto/reset calls occur here.
  const routeStart = Date.now();
  if (!focusedOnly) for (const [name, target] of [
    ['west avenue', [-12, 0, 0]], ['hill west stairs ascent', [-4, 1.5, 0]],
    ['hill west plaza', [-4, 1.5, 4]], ['hill south plaza', [0, 1.5, 4]],
    ['hill south stairs descent', [0, 0, 12]], ['ring gate approach', [0, 0, 31]],
    ['ring gate raised pad', [0, 0.5, 36]], ['ring gate steps descent', [0, 0, 31]],
    ['western bypass south', [-13, 0, 28]], ['western bypass north', [-13, 0, -29]],
    ['lattice jack approach', [0, 0, -31]], ['lattice jack raised pad', [0, 0.5, -36.5]],
  ]) await walkTo(name, target);
  report.mainRoute = { durationMs: Date.now() - routeStart, teleportCount: 0, completed: !focusedOnly };
  if (!focusedOnly) report.checks.push('Actual keyboard traversal: west spawn → six hill stair risers → hill plaza → south stair descent → Ring Gate pad → Lattice Jack pad; no teleports or fallthrough');
  else report.limitations.push('Focused regression mode skips the continuous route. It is not full Phase 1 acceptance.');
  await page.screenshot({ path: `${output}phase1-active-desktop.png` });
  report.desktopPixels = pixels(await page.locator('canvas').screenshot());

  // Focused regressions use safe public landmark teleports only to begin each independent test.
  if (!visualOnly) {
  await page.evaluate(() => window.__ATHEN__.goto('shop_row_e'));
  await walkTo('east shop porch approach', [12, 0, 9]);
  await walkTo('east shop porch stairs ascent', [16, 0.5, 9]);
  await walkTo('east shop doorway and stage', [20, 0.5, 9]);
  await orient(Math.PI / 2);
  await page.waitForTimeout(500);
  report.cameraOcclusion = await snapshot();
  assert(report.cameraOcclusion.camera.obstructed, 'Stage rear wall must obstruct and shorten the third-person boom');
  assert(report.cameraOcclusion.camera.distance < report.cameraOcclusion.camera.desiredDistance - 0.2);
  await page.screenshot({ path: `${output}phase1-camera-occlusion.png` });
  await walkTo('east shop porch stairs descent', [12, 0, 9]);
  await page.waitForTimeout(400);
  report.cameraRecovery = await snapshot();
  assert(report.cameraRecovery.camera.distance > report.cameraOcclusion.camera.distance + 0.2, 'Boom must extend again after leaving the obstruction');
  report.checks.push('Shop porch stair ascent/descent, doorway access, camera boom obstruction and recovery');

  await page.evaluate(() => window.__ATHEN__.goto('west_gate'));
  await walkTo('west gate tunnel through passage', [-52, 0, 0]);
  await walkTo('west gate tunnel standing headroom', [-48, 0, 0]);
  report.tunnel = await snapshot();
  await page.screenshot({ path: `${output}phase1-gate-tunnel.png` });
  report.checks.push('1.8 m capsule traverses and stands inside the west gate tunnel');

  await page.evaluate(() => window.__ATHEN__.goto('whompah'));
  await walkTo('boundary test ring departure', [0, 0, 31]);
  await walkTo('boundary test approach', [40, 0, 31], { sprint: true });
  await walkTo('east boundary runup', [55, 0, 31], { sprint: true });
  await orient(-Math.PI / 2);
  const tunnelSamples = await hold(['Shift', 'w'], 1600, 'sprint into city wall');
  report.wall = { start: tunnelSamples[0].player, end: (await snapshot()).player,
    maxX: Math.max(...tunnelSamples.map(s => s.player.x)), contacts: [...new Set(tunnelSamples.flatMap(s => s.player.collisions))] };
  assert(report.wall.end.x < 59 && report.wall.end.x > 56, 'Full sprint must stop at the east wall');
  assert(report.wall.contacts.length > 0, 'Wall test must exercise collision contacts');
  await orient(-Math.PI / 4);
  const sliding = await hold(['Shift', 'w'], 1300, 'diagonal wall slide');
  report.wallSlide = { start: sliding[0].player, end: (await snapshot()).player };
  assert(report.wallSlide.end.z < report.wallSlide.start.z - 2, 'Diagonal input must slide along the wall');
  assert(report.wallSlide.end.x < 59, 'Sliding must stay inside the wall');
  report.checks.push('Full-speed sprint cannot tunnel through the city wall; diagonal input slides along it');

  // Focus loss is the browser event path; never write the input set or movement vectors.
  await orient(Math.PI / 2);
  await page.keyboard.down('w'); await page.waitForTimeout(350);
  await page.evaluate(() => window.dispatchEvent(new Event('blur')));
  await page.waitForTimeout(150);
  const blurStart = await snapshot();
  await page.waitForTimeout(550);
  const blurEnd = await snapshot(); await release();
  report.blur = { start: blurStart.player, end: blurEnd.player };
  assert(horizontalDistance(blurStart.player, blurEnd.player) < 0.03, 'Blur must clear held movement');
  report.checks.push('Browser blur clears a held movement key');

  await page.keyboard.press('Escape');
  await page.waitForTimeout(100);
  const paused = await snapshot();
  assert.equal(paused.state, 'paused');
  await page.keyboard.down('w'); await page.waitForTimeout(350); await page.keyboard.up('w');
  assert.deepEqual((await snapshot()).player, paused.player, 'Pause must stop simulation movement');
  await page.keyboard.press('Escape'); await page.waitForTimeout(150);
  assert.equal((await snapshot()).state, 'play');
  const beforeResetPhysics = (await snapshot()).physics;
  await page.keyboard.press('r'); await page.waitForTimeout(200);
  report.reset = await snapshot();
  assert(horizontalDistance(report.reset.player, report.initial.player) < 0.02, 'R must restore the west spawn');
  assert(report.reset.player.grounded && Math.abs(report.reset.player.y) < 0.08);
  report.resetPhysicsBefore = beforeResetPhysics;
  for (const key of ['bodies', 'colliders', 'staticColliders', 'characterControllers']) {
    assert.equal(report.reset.physics[key], beforeResetPhysics[key], `Reset must not leak physics ${key}`);
  }
  report.checks.push('Escape pause/resume and R reset return to grounded spawn');

  await orient(-Math.PI / 2);
  report.directionalInput = [];
  for (const [key, axis, sign] of [['d', 'z', 1], ['a', 'z', -1], ['s', 'x', -1], ['ArrowUp', 'x', 1]]) {
    const before = (await snapshot()).player;
    await hold([key], 420, `direction key ${key}`);
    const after = (await snapshot()).player;
    assert((after[axis] - before[axis]) * sign > 0.7, `${key}: camera-relative movement has the expected direction`);
    report.directionalInput.push({ key, before, after });
  }
  report.checks.push('A/D strafe, S reverse and arrow-key movement follow the camera axes');

  // Active movement sampling is separate from screenshots and upload work.
  await orient(-Math.PI / 2);
  await page.keyboard.down('w');
  report.performance = await page.evaluate(async () => {
    const times = [], renderers = [];
    await new Promise(resolve => {
      const frame = time => { times.push(time); renderers.push(window.__ATHEN__.renderer);
        if (times.length < 91) requestAnimationFrame(frame); else resolve(); };
      requestAnimationFrame(frame);
    });
    const gl = document.querySelector('canvas').getContext('webgl2');
    const extension = gl.getExtension('WEBGL_debug_renderer_info');
    return { fps: 90000 / (times.at(-1) - times[0]), minFrameMs: Math.min(...times.slice(1).map((t, i) => t - times[i])),
      maxFrameMs: Math.max(...times.slice(1).map((t, i) => t - times[i])),
      maxDraws: Math.max(...renderers.map(r => r.draws)), maxTris: Math.max(...renderers.map(r => r.tris)),
      renderer: window.__ATHEN__.renderer, userAgent: navigator.userAgent,
      gpu: extension ? gl.getParameter(extension.UNMASKED_RENDERER_WEBGL) : 'unavailable',
      physics: window.__ATHEN__.physics, mode: 'Headless Chromium, real movement, 1920 × 1080, DPR 1' };
  });
  await release();
  assert(report.performance.maxDraws <= 80 && report.performance.maxTris <= 250000);
  if (/swiftshader|llvmpipe|software/i.test(report.performance.gpu)) report.limitations.push('Headless browser uses a software GPU. Its FPS is not the medium laptop GPU 60 fps acceptance result. Native browser evidence is required separately.');
  }

  await page.evaluate(() => window.__ATHEN__.reset()); await page.waitForTimeout(200);
  // Pause through the asynchronous uploads so ongoing contact-solver ticks cannot alter the pose.
  await page.evaluate(() => window.__ATHEN__.pause(true));
  const captureBefore = await page.evaluate(() => ({ player: window.__ATHEN__.player, active: window.__ATHEN__.activeCamera,
    camera: window.__ATHEN__.camera, transforms: window.__ATHEN__.cameraTransforms, renderer: window.__ATHEN__.renderer }));
  report.captures = await page.evaluate(() => Promise.all(window.__ATHEN__.cameras.map(name => window.__ATHEN__.shot(name))));
  const captureAfter = await page.evaluate(() => ({ player: window.__ATHEN__.player, active: window.__ATHEN__.activeCamera,
    camera: window.__ATHEN__.camera, transforms: window.__ATHEN__.cameraTransforms, renderer: window.__ATHEN__.renderer }));
  assert.deepEqual(captureAfter.player, captureBefore.player, 'Captures must preserve the paused player pose exactly');
  assert.equal(captureAfter.active, captureBefore.active);
  assert.deepEqual(captureAfter.transforms, captureBefore.transforms);
  for (const key of ['width', 'height', 'pixelRatio', 'draws', 'tris']) assert.equal(captureBefore.renderer[key], captureAfter.renderer[key]);
  report.namedPixels = {};
  for (const name of report.initial.cameras) {
    report.namedPixels[name] = pixels(await readFile(`${output}${name}.png`));
    assert.equal(report.namedPixels[name].width, 1920); assert.equal(report.namedPixels[name].height, 1080);
  }
  report.checks.push('Six fixed 1080p camera captures queue correctly and restore player, active view, named camera projections, renderer size/DPR and draw counts');
  await page.evaluate(() => window.__ATHEN__.pause(false));

  await page.getByText('Survey tools', { exact: true }).click();
  await page.getByLabel('View', { exact: true }).selectOption('cam_avenue');
  assert.equal(await page.evaluate(() => window.__ATHEN__.activeCamera), 'cam_avenue');
  await page.getByRole('button', { name: 'Save frame', exact: true }).click();
  await page.waitForFunction(() => document.querySelector('#save-status')?.textContent === 'Saved tools/shots/cam_avenue.png');
  await page.getByLabel('View', { exact: true }).selectOption('follow');
  await page.getByText('Survey tools', { exact: true }).click();
  report.checks.push('Survey UI selects a named camera, saves an actual frame, and returns to the player camera');

  report.responsive = [];
  const fixedHill = await readFile(`${output}cam_hill.png`);
  for (const viewport of [{ width: 1280, height: 720 }, { width: 390, height: 844 }]) {
    await page.setViewportSize(viewport); await page.waitForTimeout(150);
    const mode = viewport.width < 600 ? 'mobile' : 'laptop';
    const fit = await page.evaluate(() => {
      const visible = [...document.querySelectorAll('button, select')].filter(e => !e.closest('details:not([open]), [hidden]')
        && e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden');
      return { documentWidth: document.documentElement.scrollWidth, viewport: innerWidth,
        controls: visible.map(e => { const r = e.getBoundingClientRect(); return { label: e.textContent || e.getAttribute('aria-label'), x: r.x, y: r.y, width: r.width, height: r.height,
          fits: r.x >= 0 && r.y >= 0 && r.right <= innerWidth + 1 && r.bottom <= innerHeight + 1 }; }) };
    });
    report.lastLayoutInspection = { mode, fit };
    assert(fit.documentWidth <= fit.viewport, `${mode}: no horizontal page overflow`);
    assert(fit.controls.every(c => c.fits), `${mode}: controls stay inside the viewport`);
    const pixelCheck = pixels(await page.locator('canvas').screenshot());
    if (mode === 'mobile') {
      const before = await page.evaluate(() => window.__ATHEN__.cameraTransforms);
      await page.evaluate(() => window.__ATHEN__.shot('cam_hill'));
      assert((await readFile(`${output}cam_hill.png`)).equals(fixedHill), 'Narrow display still saves the fixed landscape composition');
      assert.deepEqual(await page.evaluate(() => window.__ATHEN__.cameraTransforms), before);
    }
    await page.screenshot({ path: `${output}phase1-${mode}.png` });
    report.responsive.push({ mode, viewport, fit, pixelCheck });
  }
  report.checks.push('Desktop, laptop and narrow viewport nonblank canvas and UI bounds; narrow-screen captures preserve fixed camera projection');

  // Test the exposed touch controls via browser touch events on a touch-capable context.
  const mobileContext = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1, isMobile: true, hasTouch: true });
  const mobile = await mobileContext.newPage();
  mobile.on('pageerror', error => report.errors.push(`mobile page: ${error.message}`));
  await mobile.goto(url, { waitUntil: 'networkidle' }); await mobile.waitForFunction(() => window.__ATHEN__?.state === 'play');
  const forward = mobile.locator('[data-move="forward"]');
  assert(await forward.isVisible(), 'Touch movement control must be visible on narrow touch screens');
  const rect = await forward.boundingBox();
  assert(rect.width >= 40 && rect.height >= 40, 'Touch target must remain usable');
  const cdp = await mobileContext.newCDPSession(mobile);
  const touchStart = await mobile.evaluate(() => window.__ATHEN__.player);
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 }] });
  await mobile.waitForTimeout(500);
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
  await mobile.waitForTimeout(150);
  const touchEnd = await mobile.evaluate(() => window.__ATHEN__.player);
  assert(horizontalDistance(touchStart, touchEnd) > 0.5, 'Holding touch forward must move the actual capsule');
  await mobile.waitForTimeout(350);
  assert(horizontalDistance(touchEnd, await mobile.evaluate(() => window.__ATHEN__.player)) < 0.03, 'Touch release must stop movement');
  report.touch = { start: touchStart, end: touchEnd, target: rect };
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 }] });
  await mobile.waitForTimeout(300);
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchCancel', touchPoints: [] });
  await mobile.waitForTimeout(150);
  const cancelStart = await mobile.evaluate(() => window.__ATHEN__.player);
  await mobile.waitForTimeout(350);
  const cancelEnd = await mobile.evaluate(() => window.__ATHEN__.player);
  assert(horizontalDistance(cancelStart, cancelEnd) < 0.03, 'Touch cancellation must clear held movement');
  report.touch.cancel = { start: cancelStart, end: cancelEnd };
  await mobile.screenshot({ path: `${output}phase1-mobile-active.png` });
  await mobileContext.close();
  report.checks.push('Actual touch hold moves the capsule; release and pointer cancellation clear movement');

  assert.deepEqual(report.errors, [], 'Normal production play must have no console/page/network errors');
  await context.close();
  report.elapsedMs = Date.now() - started;
  report.result = 'PASS';
} catch (error) {
  report.result = 'FAIL'; report.failure = error.stack; report.elapsedMs = Date.now() - started;
  if (page) {
    try { report.failureState = await snapshot(); await page.screenshot({ path: `${output}phase1-failure.png` }); } catch {}
  }
  process.exitCode = 1;
} finally {
  await browser.close();
  await writeFile(`${output}phase1-qa${visualOnly ? '-visual' : focusedOnly ? '-focused' : ''}.json`, `${JSON.stringify(report, null, 2)}\n`);
  // Keep the console concise. The full route/physics sample trace is the saved evidence.
  console.log(JSON.stringify({ result: report.result, elapsedMs: report.elapsedMs, checks: report.checks,
    mainRoute: report.mainRoute, performance: report.performance, captures: report.captures,
    sampleCount: report.samples.length, colliderCount: report.initial?.colliders.length,
    limitations: report.limitations, errors: report.errors, failure: report.failure }, null, 2));
}
