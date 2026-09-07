// Numerical controller regressions: no browser, renderer, or authored world mutation.
// Load the production TypeScript modules in memory so the test exercises their exact code.
import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';
import { Group, Scene } from 'three';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const moduleUrl = (source) => `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`;
async function compile(relative) {
  return ts.transpileModule(await readFile(resolve(root, relative), 'utf8'), {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext },
  }).outputText
    .replace("'@dimforge/rapier3d-compat'", JSON.stringify(import.meta.resolve('@dimforge/rapier3d-compat')))
    .replace("'three'", JSON.stringify(import.meta.resolve('three')));
}
const physicsUrl = moduleUrl(await compile('src/physics.ts'));
const playerUrl = moduleUrl((await compile('src/player.ts')).replace("'./physics'", JSON.stringify(physicsUrl)));
const { Physics, FIXED_STEP } = await import(physicsUrl);
const { Player } = await import(playerUrl);
const plane = { name: 'COL_ground', kind: 'halfspace', position: [0, 0, 0], normal: [0, 1, 0] };
const oldFloor = { name: 'COL_old_box_ground', kind: 'box', position: [0, -0.3, 0], halfExtents: [60, 0.3, 45] };
const results = { result: 'PASS', checks: [], formerFailure: null };

function tick(player, ticks, intent, yaw = -Math.PI / 2) {
  for (let i = 0; i < ticks; i++) player.update(FIXED_STEP, intent, yaw);
  return player.snapshot;
}
async function fixture(colliders, spawn, test) {
  const physics = await Physics.create(colliders);
  const scene = new Scene();
  const player = new Player(physics, scene, spawn, { root: new Group(), update() {}, dispose() {} });
  try { return await test(player, physics); }
  finally {
    player.dispose();
    assert.equal(physics.diagnostics.bodies, 0, 'dispose removes the player body');
    assert.equal(physics.diagnostics.characterControllers, 0, 'dispose removes the controller');
    physics.dispose();
    scene.traverse((object) => { object.geometry?.dispose(); object.material?.dispose(); });
  }
}

async function straightFloor(floor, yaw, spawn) {
  return fixture([floor], spawn, (player) => {
    let maxLateralDrift = 0;
    let minimumFeet = Infinity;
    let maximumFeet = -Infinity;
    let stalledTicks = 0;
    for (let i = 0; i < 360; i++) {
      const state = tick(player, 1, { forward: 1, right: 0, run: false }, yaw);
      const perpendicular = (state.x - spawn[0]) * Math.cos(yaw) - (state.z - spawn[2]) * Math.sin(yaw);
      maxLateralDrift = Math.max(maxLateralDrift, Math.abs(perpendicular));
      minimumFeet = Math.min(minimumFeet, state.y);
      maximumFeet = Math.max(maximumFeet, state.y);
      if (i > 15 && state.speed < 3) stalledTicks += 1;
    }
    return { maxLateralDrift, minimumFeet, maximumFeet, stalledTicks, final: player.snapshot };
  });
}

// The old thin 120x90 m box triggered Rapier 0.20 capsule-query drift on level paving.
// Record its result without requiring an upstream defect to persist in future releases.
results.formerFailure = await straightFloor(oldFloor, -Math.PI / 2, [-43, 0, 0]);
for (const [name, yaw, spawn] of [
  ['east', -Math.PI / 2, [-43, 0, 0]],
  ['west', Math.PI / 2, [43, 0, 0]],
  ['north', -0.002937688661981963, [-11.167313575744629, 0, 27.953319549560547]],
]) {
  const result = await straightFloor(plane, yaw, spawn);
  assert(result.maxLateralDrift < 0.002, `${name}: straight input must stay straight`);
  assert(result.minimumFeet > 0.01 && result.maximumFeet < 0.02, `${name}: feet remain above level paving`);
  assert.equal(result.stalledTicks, 0, `${name}: no level-ground stalls`);
  results.checks.push({ name: `six seconds ${name}`, ...result });
}

const stairs = Array.from({ length: 6 }, (_, i) => ({
  name: `COL_step_${i}`, kind: 'box', position: [i * 0.65 + 1, (i + 1) * 0.25 / 2, 0],
  halfExtents: [0.325, (i + 1) * 0.25 / 2, 2],
}));
const plateau = { name: 'COL_plateau', kind: 'box', position: [6.275, 0.75, 0], halfExtents: [1.7, 0.75, 2] };
await fixture([plane, ...stairs, plateau], [-2, 0, 0], (player) => {
  const ascent = tick(player, 190, { forward: 1, right: 0, run: false });
  assert(ascent.grounded && ascent.y > 1.45 && ascent.y < 1.55, 'climb six .25m risers');
  const descent = tick(player, 180, { forward: -1, right: 0, run: false });
  assert(descent.grounded && descent.y >= 0 && descent.y < 0.025, 'descend stairs to paving');
  results.checks.push({ name: 'stair ascent and descent', ascent, descent });
});

const wall = { name: 'COL_wall', kind: 'box', position: [10, 2, 0], halfExtents: [0.2, 2, 10] };
await fixture([plane, wall], [5, 0, 5], (player, physics) => {
  const blocked = tick(player, 100, { forward: 1, right: 0, run: true });
  assert(blocked.x < 9.5 && blocked.collisions.includes('COL_wall'), 'sprint cannot tunnel through wall');
  const slide = tick(player, 35, { forward: 1, right: 1, run: true });
  assert(slide.z > blocked.z + 2 && slide.x < 9.5, 'diagonal movement slides along wall');
  const cameraDistance = physics.cameraDistance({ x: 9.4, y: 1.5, z: 5 }, { x: 1, y: 0, z: 0 }, 4.2, player.collider);
  assert(cameraDistance > 0 && cameraDistance < 0.2, 'camera sphere stops before wall');
  player.teleport([5, 0, 5]);
  assert.equal(physics.diagnostics.bodies, 1, 'teleport does not duplicate the player');
  results.checks.push({ name: 'sprint wall, slide, camera and teleport', blocked, slide, cameraDistance });
});

const lip = { name: 'COL_half_metre_lip', kind: 'box', position: [3, 0.25, 0], halfExtents: [1, 0.25, 2] };
await fixture([plane, lip], [0, 0, 0], (player) => {
  const blocked = tick(player, 180, { forward: 1, right: 0, run: true });
  assert(blocked.x < 2 && blocked.y < 0.1, 'a .5m vertical lip cannot be auto-stepped');
  results.checks.push({ name: 'over-height lip', blocked });
});

const destination = resolve(root, process.env.ATHEN_QA_OUTPUT ?? 'tools/physics-regressions.json');
await writeFile(destination, `${JSON.stringify(results, null, 2)}\n`);
console.log(`PASS: ${results.checks.length} controller checks; ${destination}`);
