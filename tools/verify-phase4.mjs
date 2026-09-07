import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { chromium } from '@playwright/test';
import { CAMERAS, inspectGLB, inspectPixels, assertHealthy, horizontalDistance } from './phase3-support/checks.mjs';

const args = process.argv.slice(2);
if (args.includes('--help')) {
  console.log('Usage: node tools/verify-phase4.mjs [URL] [--headless]');
  console.log('Default: headed Chromium/Metal at http://127.0.0.1:4173, mandatory >=58fps. Does not build or restart servers.');
  console.log('Requires final Phase4 assets plus player/NPC bone-pose diagnostics; preserves earlier evidence.');
  process.exit(0);
}
for (const flag of args.filter(arg => arg.startsWith('--'))) assert.equal(flag, '--headless', `Unknown option: ${flag}`);
const url = args.find(arg => !arg.startsWith('--')) ?? process.env.ATHEN_QA_URL ?? 'http://127.0.0.1:4173';
const runName = `${new Date().toISOString().replaceAll(':', '-')}-${process.pid}`;
const relativeOutput = `tools/phase4-support/runs/${runName}`;
const output = fileURLToPath(new URL(`./phase4-support/runs/${runName}/`, import.meta.url));
const baselinePath = process.env.ATHEN_PHASE3_REPORT
  ?? fileURLToPath(new URL('./phase3-support/runs/2026-09-07T09-59-38.809Z-14868/report.json', import.meta.url));
await mkdir(output, { recursive: true });
const started = Date.now();
const report = {
  url, output: relativeOutput, scope: 'Phase4 authored player/NPC animation and runtime integration. Dialogue, commerce, audio and final visual scoring remain separate.',
  inputMethod: 'Actual keyboard W/Shift/E/Escape/R and browser touch events; debug fields are read-only except the public paused named-camera screenshot API.',
  referenceLedger: ['qa-release-checklists.md', 'checklists/visual-verification.md', 'checklists/playtest-qa.md', 'checklists/release.md']
    .map(path => ({ path: `threejs-qa-release/references/${path}`, read: true, failure: null })),
  errors: [], warnings: [], assets: [], checks: [], captures: [], samples: [],
  limitations: ['Character style and likeness require the separate visual review.',
    'GPU/FPS evidence applies to the reported hardware, not an untested medium laptop.',
    'Named-camera PNGs are archived from the actual shot() upload; the local Vite writer is not retested.'],
};
const jobs = [], images = new Map();
let browser, page;
const stable = value => Array.isArray(value) ? value.map(stable) : value && typeof value === 'object'
  ? Object.fromEntries(Object.keys(value).sort().map(key => [key, stable(value[key])])) : value;
const canonical = value => JSON.stringify(stable(value));
const sortedColliders = value => [...value].sort((a, b) => a.name.localeCompare(b.name));

function poseDifference(a, b) {
  assert(Array.isArray(a) && a.length >= 4 && Array.isArray(b) && b.length === a.length,
    'Actual bone-local poses must be exposed for multiple authored bones');
  let maximum = 0;
  for (const bone of a) {
    const next = b.find(candidate => candidate.name === bone.name);
    assert(next, `Bone ${bone.name} must remain present`);
    assert([...bone.position, ...bone.quaternion, ...next.position, ...next.quaternion].every(Number.isFinite));
    maximum = Math.max(maximum, Math.hypot(...bone.position.map((value, index) => value - next.position[index])));
    const norm = Math.hypot(...bone.quaternion) * Math.hypot(...next.quaternion);
    const dot = bone.quaternion.reduce((sum, value, index) => sum + value * next.quaternion[index], 0) / norm;
    maximum = Math.max(maximum, 2 * Math.acos(Math.min(1, Math.abs(dot))));
  }
  return maximum;
}

async function observe(target, label) {
  target.on('pageerror', error => report.errors.push(`${label} page: ${error.message}`));
  target.on('console', message => {
    if (message.type() === 'error') report.errors.push(`${label} console: ${message.text()}`);
    if (message.type() === 'warning') report.warnings.push(`${label}: ${message.text()}`);
  });
  target.on('requestfailed', request => report.errors.push(`${label} request: ${request.failure()?.errorText} ${request.url()}`));
  target.on('response', response => { if (response.status() >= 400) report.errors.push(`${label} HTTP ${response.status()}: ${response.url()}`); });
  await target.route(/\.glb(?:[?#]|$)/i, async route => {
    const job = (async () => {
      const asset = { browser: label, url: route.request().url(), capture: 'Exact fetched bytes fulfilled to the application' };
      report.assets.push(asset);
      try {
        const response = await route.fetch(), body = await response.body();
        asset.status = response.status();
        if (response.ok()) Object.assign(asset, inspectGLB(body));
        await route.fulfill({ response, body });
      } catch (error) { report.errors.push(`${label} GLB: ${error.message}`); await route.abort(); }
    })();
    jobs.push(job); await job;
  });
}

async function boot(target) {
  await target.goto(url, { waitUntil: 'networkidle' });
  await target.waitForFunction(() => window.__ATHEN__ && window.__ATHEN__.state !== 'boot', undefined, { timeout: 45000 });
  await target.evaluate(() => window.__ATHEN__.ready);
  await target.waitForTimeout(400);
  const identity = await target.evaluate(() => ({ phase: window.__ATHEN__.phase, version: window.__ATHEN__.version,
    state: window.__ATHEN__.state, error: window.__ATHEN__.error }));
  assert(identity.phase >= 4, `Expected final Phase4 build, found ${identity.version}`);
  assert.equal(identity.state, 'play', identity.error);
  return identity;
}

async function snapshot(target = page) {
  return target.evaluate(() => ({ player: window.__ATHEN__.player, playerAnimation: window.__ATHEN__.playerAnimation,
    npcs: window.__ATHEN__.npcs, characters: window.__ATHEN__.characters, camera: window.__ATHEN__.camera,
    physics: window.__ATHEN__.physics, renderer: window.__ATHEN__.renderer, state: window.__ATHEN__.state,
    error: window.__ATHEN__.error, activeCamera: window.__ATHEN__.activeCamera }));
}

function healthy(sample, label) {
  assertHealthy(sample, label, report.initial.colliders);
  assert.equal(sample.characters.instances, 8, `${label}: one player plus seven NPC instances remain alive`);
  assert.equal(sample.npcs.actors.length, 7);
  for (const actor of sample.npcs.actors) {
    assert(actor.position.every(Number.isFinite) && Number.isFinite(actor.yaw), `${label}: ${actor.id} has finite transforms`);
    assert(Math.abs(actor.position[0]) < 60 && Math.abs(actor.position[2]) < 45 && actor.position[1] >= 0 && actor.position[1] <= 1.5,
      `${label}: ${actor.id} remains on the city support surfaces`);
    assert(actor.character.bones > 0 && actor.character.triangles > 0, `${label}: ${actor.id} uses the authored rig`);
    poseDifference(actor.character.pose, actor.character.pose);
  }
  poseDifference(sample.playerAnimation.pose, sample.playerAnimation.pose);
  report.samples.push({ label, elapsedMs: Date.now() - started, ...sample });
}

async function release(target = page) {
  for (const key of ['w', 'a', 's', 'd', 'Shift']) await target.keyboard.up(key);
}

async function activeCapture(target, name) {
  const pixels = inspectPixels(await target.locator('canvas').screenshot());
  await target.screenshot({ path: `${output}${name}.png` });
  return { path: `${relativeOutput}/${name}.png`, pixels };
}

function animationState(sample) {
  return { player: sample.player, playerAnimation: sample.playerAnimation,
    npcs: sample.npcs.actors.map(actor => ({ id: actor.id, position: actor.position, yaw: actor.yaw,
      talking: actor.talking, character: actor.character })) };
}

try {
  const baseline = JSON.parse(await readFile(baselinePath, 'utf8'));
  assert.equal(baseline.result, 'PASS'); assert(baseline.mainRoute.completed && baseline.mainRoute.teleportCount === 0);
  const headless = args.includes('--headless');
  const launchArgs = !headless && process.platform === 'darwin' ? ['--use-angle=metal'] : [];
  browser = await chromium.launch({ headless, args: launchArgs });
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  page = await context.newPage(); await observe(page, 'desktop');
  await page.route('**/__athen__/shots/*.png', async route => {
    const camera = /\/([^/]+)\.png$/.exec(new URL(route.request().url()).pathname)?.[1];
    if (route.request().method() !== 'PUT' || !CAMERAS.includes(camera)) return route.continue();
    try {
      const png = route.request().postDataBuffer(), pixels = inspectPixels(png);
      assert.equal(pixels.width, 1920); assert.equal(pixels.height, 1080);
      images.set(camera, pixels); await writeFile(`${output}${camera}.png`, png);
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ path: `${relativeOutput}/${camera}.png` }) });
    } catch (error) {
      report.errors.push(`Capture ${camera}: ${error.message}`);
      await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ error: error.message }) });
    }
  });
  report.identity = await boot(page);
  report.initial = await page.evaluate(() => ({ colliders: window.__ATHEN__.colliders, cameras: window.__ATHEN__.cameras,
    cameraTransforms: window.__ATHEN__.cameraTransforms, world: window.__ATHEN__.world,
    physics: window.__ATHEN__.physics, characters: window.__ATHEN__.characters }));
  const physicsKeys = ['engine', 'timestep', 'bodies', 'colliders', 'staticColliders', 'characterControllers', 'ccdBodies', 'sensors',
    'collisionGroups', 'character', 'cameraCastRadius'];
  const oldColliders = canonical(sortedColliders(baseline.initial.colliders));
  const newColliders = canonical(sortedColliders(report.initial.colliders));
  const oldPhysics = canonical(Object.fromEntries(physicsKeys.map(key => [key, baseline.initial.physics[key]])));
  const newPhysics = canonical(Object.fromEntries(physicsKeys.map(key => [key, report.initial.physics[key]])));
  report.routeEquivalence = { baseline: baselinePath, baselineRoute: baseline.mainRoute, colliderCount: report.initial.colliders.length,
    identicalColliderDefinitions: oldColliders === newColliders, identicalControllerConfiguration: oldPhysics === newPhysics,
    colliderSHA256: createHash('sha256').update(newColliders).digest('hex') };
  assert(report.routeEquivalence.identicalColliderDefinitions && report.routeEquivalence.identicalControllerConfiguration,
    'Physical configuration changed: repeat the full Phase3 traversal before retaining its evidence');
  assert.deepEqual([...report.initial.cameras].sort(), [...CAMERAS].sort());
  assert.equal(report.initial.characters.state, 'ready'); assert.equal(report.initial.characters.instances, 8);
  assert.equal(report.initial.world.greyboxLandmarks.length, 0);
  await Promise.all(jobs);
  for (const [kind, file] of [['player', 'player.glb'], ['npc', 'npcs.glb']]) {
    const asset = report.assets.find(entry => entry.browser === 'desktop' && new URL(entry.url).pathname.endsWith(`/${file}`));
    assert(asset?.status === 200 && asset.meshCount > 0, `Actual ${file} must load`);
    assert.equal(asset.bytes, report.initial.characters.assets[kind].bytes, 'Library diagnostics describe the actual delivered bytes');
    assert.deepEqual(report.initial.characters.assets[kind].clips.map(clip => clip.name).sort(), ['idle', 'run', 'talk', 'walk']);
  }
  const initial = await snapshot(); healthy(initial, 'spawn');
  const roles = Object.fromEntries(initial.npcs.actors.filter(actor => actor.role !== 'ambient').map(actor => [actor.id, actor.role]));
  assert.deepEqual(roles, { npc_mira: 'vendor', npc_torr: 'fixer', npc_vex: 'guard', npc_linn: 'loafer' });
  assert.equal(initial.npcs.actors.filter(actor => actor.role === 'ambient').length, 3);
  assert.equal(initial.playerAnimation.animation, 'idle');
  report.checks.push('Both authored rig assets loaded; eight independent character instances, four named roles and three ambient walkers; prior full route retained by exact physics equivalence');

  await page.locator('canvas').click({ position: { x: 800, y: 400 } });
  await page.waitForFunction(() => window.__ATHEN__.npcs.nearest?.id === 'npc_vex');
  const beforeTalk = await snapshot();
  await page.keyboard.press('e');
  await page.waitForFunction(() => window.__ATHEN__.npcs.actors.find(actor => actor.id === 'npc_vex').character.animation === 'talk');
  await page.waitForTimeout(180); const talkA = await snapshot();
  await page.waitForTimeout(230); const talkB = await snapshot();
  const vexA = talkA.npcs.actors.find(actor => actor.id === 'npc_vex'), vexB = talkB.npcs.actors.find(actor => actor.id === 'npc_vex');
  report.talk = { before: beforeTalk.npcs.interactions, after: talkB.npcs.interactions,
    animation: vexB.character.animation, poseDifference: poseDifference(vexA.character.pose, vexB.character.pose) };
  assert.equal(report.talk.after, report.talk.before + 1); assert(report.talk.poseDifference > 1e-4, 'E must move actual NPC bones');
  assert(await page.locator('[data-npc="npc_vex"]').isVisible(), 'Nearby guard nametag must be visible');
  report.guardCapture = await activeCapture(page, 'vex-talk');
  healthy(talkB, 'Vex real E interaction');
  report.checks.push('Real E at the west spawn selects Vex, increments interaction and drives changing talk bone poses');

  const walkingStart = await snapshot();
  await page.keyboard.down('w');
  await page.waitForFunction(() => window.__ATHEN__.playerAnimation.animation === 'walk' && window.__ATHEN__.player.speed > 2.5);
  const walkA = await snapshot(); await page.waitForTimeout(240); const walkB = await snapshot();
  report.walk = { start: walkingStart.player, end: walkB.player, animation: walkB.playerAnimation,
    poseDifference: poseDifference(walkA.playerAnimation.pose, walkB.playerAnimation.pose) };
  assert(horizontalDistance(walkingStart.player, walkB.player) > .5 && report.walk.poseDifference > 1e-4);
  report.walkCapture = await activeCapture(page, 'player-walk'); healthy(walkB, 'real keyboard walk');
  await page.keyboard.down('Shift');
  await page.waitForFunction(() => window.__ATHEN__.playerAnimation.animation === 'run' && window.__ATHEN__.player.speed > 4.8);
  const runA = await snapshot(); await page.waitForTimeout(230); const runB = await snapshot();
  report.run = { start: runA.player, end: runB.player, animation: runB.playerAnimation,
    poseDifference: poseDifference(runA.playerAnimation.pose, runB.playerAnimation.pose) };
  assert(horizontalDistance(runA.player, runB.player) > .8 && report.run.poseDifference > 1e-4);
  report.runCapture = await activeCapture(page, 'player-run'); healthy(runB, 'real keyboard run');
  await release();
  await page.waitForFunction(() => window.__ATHEN__.playerAnimation.animation === 'idle' && window.__ATHEN__.player.speed < .12);
  const stopped = await snapshot(); await page.waitForTimeout(400); report.stopped = await snapshot();
  assert.equal(report.stopped.playerAnimation.animation, 'idle');
  assert(horizontalDistance(stopped.player, report.stopped.player) < .04, 'Stopping input leaves the capsule stationary');
  const ambientBefore = initial.npcs.actors.filter(actor => actor.role === 'ambient');
  report.ambient = report.stopped.npcs.actors.filter(actor => actor.role === 'ambient').map(actor => {
    const before = ambientBefore.find(entry => entry.id === actor.id);
    const distance = Math.hypot(actor.position[0] - before.position[0], actor.position[2] - before.position[2]);
    assert(distance > .1 && actor.character.animation === 'walk', `${actor.id} must walk its pavement route`);
    return { id: actor.id, before: before.position, after: actor.position, distance };
  });
  for (const actor of report.stopped.npcs.actors.filter(actor => actor.role !== 'ambient')) {
    assert.deepEqual(actor.position, initial.npcs.actors.find(entry => entry.id === actor.id).position, 'Named NPCs keep their supported positions');
  }
  report.checks.push('Real W/Shift drive capsule movement and changing walk/run bone poses; stopping returns to idle; three ambient walkers move independently');

  await page.keyboard.press('Escape'); await page.waitForFunction(() => window.__ATHEN__.state === 'paused');
  const pausedA = await snapshot(); await page.waitForTimeout(400); const pausedB = await snapshot();
  assert.deepEqual(animationState(pausedB), animationState(pausedA), 'Pause must freeze player bones, NPC bones and ambient root motion exactly');
  await page.keyboard.press('e'); await page.waitForTimeout(100);
  assert.equal((await snapshot()).npcs.interactions, pausedA.npcs.interactions, 'E is inactive while paused');
  await page.keyboard.press('Escape'); await page.waitForFunction(() => window.__ATHEN__.state === 'play');
  await page.waitForTimeout(250); const resumed = await snapshot();
  assert(resumed.playerAnimation.time > pausedB.playerAnimation.time, 'Player animation resumes');
  assert(resumed.npcs.elapsed > pausedB.npcs.elapsed, 'Town animation resumes');
  await page.keyboard.press('r'); await page.waitForTimeout(250); report.reset = await snapshot();
  assert(horizontalDistance(report.reset.player, initial.player) < .02 && report.reset.player.grounded);
  assert.equal(report.reset.characters.instances, 8); assert.equal(report.reset.physics.bodies, initial.physics.bodies);
  report.checks.push('Escape freezes actual bone transforms and walkers, suppresses E, then resumes; R restores grounded spawn without new character/physics instances');

  await page.keyboard.down('w');
  try {
    report.performance = await page.evaluate(async () => {
      const times = [], metrics = [];
      await new Promise(resolve => { const frame = time => { times.push(time); metrics.push(window.__ATHEN__.renderer);
        if (times.length < 121) requestAnimationFrame(frame); else resolve(); }; requestAnimationFrame(frame); });
      const gl = document.querySelector('canvas').getContext('webgl2');
      const ext = gl.getExtension('WEBGL_debug_renderer_info');
      const intervals = times.slice(1).map((time, index) => time - times[index]).sort((a, b) => a - b);
      return { fps: 120000 / (times.at(-1) - times[0]), p95FrameMs: intervals[Math.floor(intervals.length * .95)],
        maxDraws: Math.max(...metrics.map(metric => metric.draws)), maxTris: Math.max(...metrics.map(metric => metric.tris)),
        gpu: ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : 'unavailable', renderer: window.__ATHEN__.renderer,
        characterInstances: window.__ATHEN__.characters.instances, viewport: [innerWidth, innerHeight], userAgent: navigator.userAgent };
    });
  } finally { await release(); }
  assert(report.performance.fps >= 58, `1080p FPS gate failed: ${report.performance.fps.toFixed(1)} < 58`);
  assert(report.performance.maxDraws <= 80 && report.performance.maxTris <= 250000);
  assert.equal(report.performance.characterInstances, 8);
  report.checks.push('1080p moving scene with all eight character instances meets >=58fps, <=80 draws and <=250k triangles');

  await page.keyboard.press('r'); await page.waitForTimeout(250); await page.keyboard.press('Escape');
  await page.waitForFunction(() => window.__ATHEN__.state === 'paused');
  const captureBefore = await snapshot();
  const transformsBefore = await page.evaluate(() => window.__ATHEN__.cameraTransforms);
  const paths = await page.evaluate(() => Promise.all(window.__ATHEN__.cameras.map(name => window.__ATHEN__.shot(name))));
  const captureAfter = await snapshot();
  assert.deepEqual(animationState(captureAfter), animationState(captureBefore), 'Six shots preserve every character pose');
  assert.deepEqual(await page.evaluate(() => window.__ATHEN__.cameraTransforms), transformsBefore);
  assert.equal(captureAfter.activeCamera, captureBefore.activeCamera);
  for (const key of ['width', 'height', 'pixelRatio', 'draws', 'tris']) assert.equal(captureAfter.renderer[key], captureBefore.renderer[key]);
  for (const [index, camera] of report.initial.cameras.entries()) {
    assert(images.has(camera)); report.captures.push({ camera, path: paths[index], ...images.get(camera) });
  }
  report.checks.push('Six real named-camera 1080p PNGs archived without changing any actor pose, projection, active view or renderer buffer');
  await page.keyboard.press('Escape');

  const mobileContext = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1, isMobile: true, hasTouch: true });
  const mobile = await mobileContext.newPage(); await observe(mobile, 'mobile'); await boot(mobile);
  const button = mobile.locator('[data-move="forward"]'); assert(await button.isVisible());
  const box = await button.boundingBox(); assert(box && box.width >= 40 && box.height >= 40);
  const cdp = await mobileContext.newCDPSession(mobile), mobileBefore = await snapshot(mobile);
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: box.x + box.width / 2, y: box.y + box.height / 2 }] });
  await mobile.waitForTimeout(450); const mobileMoving = await snapshot(mobile);
  assert.equal(mobileMoving.playerAnimation.animation, 'walk');
  assert(horizontalDistance(mobileBefore.player, mobileMoving.player) > .5);
  assert(poseDifference(mobileBefore.playerAnimation.pose, mobileMoving.playerAnimation.pose) > 1e-4);
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
  await mobile.waitForFunction(() => window.__ATHEN__.playerAnimation.animation === 'idle');
  healthy(await snapshot(mobile), 'mobile authored player');
  report.mobileCapture = await activeCapture(mobile, 'mobile-active');
  const fit = await mobile.evaluate(() => ({ width: document.documentElement.scrollWidth, viewport: innerWidth,
    labels: [...document.querySelectorAll('.npc-nametag')].filter(element => !element.hidden).map(element => {
      const rect = element.getBoundingClientRect(); return { id: element.dataset.npc,
        fits: rect.left >= 0 && rect.top >= 0 && rect.right <= innerWidth + 1 && rect.bottom <= innerHeight + 1 }; }) }));
  assert(fit.width <= fit.viewport && fit.labels.every(label => label.fits), 'Mobile labels remain inside the viewport');
  report.mobile = { before: mobileBefore, moving: mobileMoving, fit };
  report.checks.push('Mobile touch moves and animates the authored player, releases to idle and keeps visible labels within the viewport');
  await Promise.all(jobs); assert.deepEqual(report.errors, []);
  report.result = 'PASS';
} catch (error) {
  report.result = 'FAIL'; report.failure = error.stack; process.exitCode = 1;
  if (page) try { await release(); report.failureState = await snapshot(); await page.screenshot({ path: `${output}failure.png` }); } catch {}
} finally {
  await Promise.allSettled(jobs); await browser?.close();
  report.elapsedMs = Date.now() - started;
  await writeFile(`${output}report.json`, `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify({ result: report.result, output: report.output, elapsedMs: report.elapsedMs,
    checks: report.checks, routeEquivalence: report.routeEquivalence, performance: report.performance,
    captures: report.captures, errors: report.errors, failure: report.failure, limitations: report.limitations }, null, 2));
}
