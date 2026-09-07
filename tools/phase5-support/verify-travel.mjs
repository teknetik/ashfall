// Exercise the actual travel module without a DOM, renderer, or replacement model.
// TypeScript is erased in memory; its Three.js import resolves to the installed package.
import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { Camera, Group, Scene } from 'three';
import ts from 'typescript';

const source = await readFile(new URL('../../src/travel.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext },
}).outputText.replace(/from (['"])three\1/g, `from ${JSON.stringify(import.meta.resolve('three'))}`);
const { TravelSystem } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`);
const checks = [];

function fixture(options) {
  const scene = new Scene();
  const unrelated = new Group();
  scene.add(unrelated);
  const travel = new TravelSystem(scene, options);
  const effect = scene.getObjectByName('VFX_lattice_transition');
  const rings = scene.getObjectByName('VFX_lattice_sweep');
  const motes = scene.getObjectByName('VFX_lattice_motes');
  assert.ok(effect && rings?.isInstancedMesh && motes?.isPoints);
  return { scene, unrelated, travel, effect, rings, motes };
}

function drawBudget(effect) {
  let draws = 0, triangles = 0, points = 0, textures = 0;
  effect.traverseVisible(object => {
    if (!object.isMesh && !object.isPoints) return;
    draws++;
    const vertices = object.geometry.index?.count ?? object.geometry.attributes.position.count;
    if (object.isMesh) triangles += vertices / 3 * (object.isInstancedMesh ? object.count : 1);
    if (object.isPoints) points += vertices;
    for (const value of Object.values(object.material)) if (value?.isTexture) textures++;
    assert.equal(object.castShadow, false, 'Transient effects must not add shadow draws.');
    assert.equal(object.material.depthWrite, false, 'Transparent pulses must not obscure later geometry.');
  });
  return { draws, triangles, points, textures };
}

{
  const { travel, effect } = fixture();
  assert.equal(travel.active, false);
  assert.equal(travel.snapshot, null);
  assert.equal(effect.visible, false);
  assert.equal(travel.selectNode('crosswind_reach').ok, false);
  travel.update(2);
  assert.equal(travel.snapshot, null);
  travel.start();
  const initial = travel.snapshot;
  assert.equal(travel.active, true);
  assert.equal(initial.phase, 'tunnel');
  assert.equal(initial.progress, 0);
  assert.equal(initial.selectedNode, null);
  assert.equal(travel.selectNode(initial.nodes[0].id).ok, false);
  travel.update(0.5);
  assert.equal(travel.snapshot.progress, 0.4);
  travel.update(0.749);
  assert.equal(travel.snapshot.phase, 'tunnel');
  assert.ok(travel.snapshot.progress < 1);
  travel.update(0.0011);
  assert.equal(travel.snapshot.phase, 'map');
  assert.equal(travel.snapshot.progress, 1);
  assert.equal(effect.visible, false);
  travel.update(100);
  assert.equal(travel.snapshot.progress, 1);
  assert.equal(initial.progress, 0, 'Earlier snapshots must remain fixed when the session advances.');
  travel.dispose();
  checks.push('A closed session is inert; a new tunnel stays open before 1.25 seconds and reaches the map at the threshold, hiding its world VFX.');
}

{
  const { travel } = fixture();
  travel.start();
  const before = travel.snapshot;
  for (const dt of [-1, -Infinity, Infinity, NaN, undefined, null, '1', {}, 0]) {
    travel.update(dt);
    assert.deepEqual(travel.snapshot, before);
  }
  travel.update(0.625);
  assert.equal(travel.snapshot.progress, 0.5);
  travel.update(0.625);
  assert.equal(travel.snapshot.phase, 'map');
  travel.start();
  travel.update(Number.MAX_VALUE);
  assert.equal(travel.snapshot.phase, 'map');
  assert.equal(travel.snapshot.progress, 1);
  travel.dispose();
  checks.push('Invalid/negative deltas cannot corrupt time; exact midpoint and threshold timing work; a very large finite delta clamps to map progress 1.');
}

{
  const { travel } = fixture();
  travel.start();
  travel.update(1.25);
  const routes = travel.snapshot.nodes;
  assert.deepEqual(routes.map(node => node.name), ['Crosswind Reach', 'Drywater Works', 'Beacon Dunes']);
  assert.equal(new Set(routes.map(node => node.id)).size, 3);
  assert.ok(routes.every(node => node.description.length > 20));
  for (const node of routes) {
    const previous = travel.snapshot;
    assert.deepEqual(travel.selectNode(node.id), { ok: true, message: `Link established to ${node.name}.` });
    assert.equal(travel.snapshot.selectedNode, node.id);
    assert.equal(travel.snapshot.phase, 'map');
    assert.deepEqual(travel.snapshot.nodes, routes);
    assert.notEqual(previous, travel.snapshot);
  }
  const before = travel.snapshot;
  for (const id of ['', '__proto__', 'constructor', 'toString', 'CROSSWIND_REACH', 'missing', null, undefined, 0, NaN, {}, Object.create(null)]) {
    assert.equal(travel.selectNode(id).ok, false);
    assert.deepEqual(travel.snapshot, before);
  }
  travel.dispose();
  checks.push('Exactly three original routes return their link message; unknown, prototype and non-string IDs fail without changing the selected route or map.');
}

{
  const { travel } = fixture();
  travel.start();
  const detached = travel.snapshot;
  const original = structuredClone(detached);
  // The API provides detached value snapshots, not frozen objects. Neither nested
  // consumer edits nor future state changes may alter the model or an older value.
  detached.phase = 'map';
  detached.progress = -99;
  detached.selectedNode = 'missing';
  detached.nodes[0].name = 'changed';
  detached.nodes[0].id = 'changed';
  detached.nodes.push({ id: 'extra', name: 'extra', description: 'extra' });
  assert.deepEqual(travel.snapshot, original);
  travel.update(1.25);
  travel.selectNode(original.nodes[0].id);
  assert.equal(original.progress, 0);
  assert.equal(original.selectedNode, null);
  assert.equal(original.nodes.length, 3);
  travel.dispose();
  checks.push('Snapshots are detached at every exposed nesting level and remain stable across later state changes; caller edits cannot modify the route catalogue or live session.');
}

let vfxBudget;
{
  const { travel, effect, rings, motes } = fixture();
  const camera = new Camera();
  camera.position.set(5, 7, 9);
  const cameraBefore = camera.matrix.toArray();
  const positionBefore = camera.position.toArray();
  travel.start();
  travel.update(0.625, camera);
  vfxBudget = drawBudget(effect);
  assert.deepEqual(vfxBudget, { draws: 2, triangles: 768, points: 28, textures: 0 });
  assert.ok(vfxBudget.draws <= 6 && vfxBudget.triangles <= 3000);
  assert.deepEqual(camera.position.toArray(), positionBefore);
  assert.deepEqual(camera.matrix.toArray(), cameraBefore);
  assert.ok(rings.material.opacity > 0 && rings.material.opacity <= 0.3);
  assert.ok(motes.material.opacity > 0 && motes.material.opacity <= 0.35);
  assert.ok([...rings.instanceMatrix.array, ...motes.geometry.attributes.position.array].every(Number.isFinite));
  travel.close();
  assert.deepEqual(drawBudget(effect), { draws: 0, triangles: 0, points: 0, textures: 0 });
  travel.dispose();
  checks.push('The active pulse uses two unshadowed draws, 768 triangles, 28 points and no textures; its opacity stays restrained and the optional camera is unchanged.');
}

{
  const { travel, effect, motes } = fixture({ reducedMotion: true });
  const positions = Array.from(motes.geometry.attributes.position.array);
  travel.start();
  travel.update(0.625);
  assert.equal(effect.visible, false);
  assert.deepEqual(drawBudget(effect), { draws: 0, triangles: 0, points: 0, textures: 0 });
  assert.deepEqual(Array.from(motes.geometry.attributes.position.array), positions);
  assert.equal(travel.snapshot.progress, 0.5);
  travel.setReducedMotion(false);
  assert.equal(effect.visible, true);
  assert.equal(travel.snapshot.progress, 0.5);
  travel.setReducedMotion(true);
  assert.equal(effect.visible, false);
  travel.update(0.625);
  assert.equal(travel.snapshot.phase, 'map');
  travel.dispose();
  checks.push('Reduced motion hides all world VFX and leaves particle positions still while preserving travel timing; a live preference change does not restart the transition.');
}

{
  const { travel, scene, effect, rings, motes } = fixture();
  const geometryIds = [rings.geometry.uuid, motes.geometry.uuid];
  for (let i = 0; i < 25; i++) {
    travel.start();
    travel.update(1.25);
    travel.selectNode(travel.snapshot.nodes[i % 3].id);
    travel.start();
    assert.equal(travel.snapshot.phase, 'tunnel');
    assert.equal(travel.snapshot.progress, 0);
    assert.equal(travel.snapshot.selectedNode, null);
    travel.update(0.4);
    travel.close();
    assert.equal(travel.active, false);
    assert.equal(travel.snapshot, null);
    assert.equal(effect.visible, false);
    assert.equal(scene.children.length, 2);
    assert.deepEqual([rings.geometry.uuid, motes.geometry.uuid], geometryIds);
  }
  travel.dispose();
  checks.push('Twenty-five open/select/restart/cancel cycles clear stale selection and reuse the same scene objects and geometry.');
}

let disposedResources = 0;
for (const stage of ['never-started', 'tunnel', 'map']) {
  const { travel, scene, unrelated, effect, rings, motes } = fixture();
  if (stage !== 'never-started') { travel.start(); travel.update(stage === 'map' ? 1.25 : 0.5); }
  const counters = [rings, rings.geometry, rings.material, motes.geometry, motes.material].map(resource => {
    const counter = { count: 0 };
    resource.addEventListener('dispose', () => counter.count++);
    return counter;
  });
  travel.dispose();
  travel.dispose();
  travel.start();
  travel.update(1.25);
  travel.setReducedMotion(false);
  travel.close();
  assert.equal(travel.active, false);
  assert.equal(travel.snapshot, null);
  assert.equal(effect.parent, null);
  assert.equal(effect.visible, false);
  assert.deepEqual(scene.children, [unrelated]);
  assert.ok(counters.every(counter => counter.count === 1));
  disposedResources += counters.reduce((sum, counter) => sum + counter.count, 0);
}
checks.push('Disposal before start, during the tunnel and on the map removes only the owned group and releases its instance buffer, two geometries and two materials exactly once; later calls cannot revive it.');

{
  const scene = new Scene();
  const first = new TravelSystem(scene), second = new TravelSystem(scene);
  first.start(); first.update(1.25); first.selectNode(first.snapshot.nodes[0].id);
  assert.equal(second.snapshot, null);
  second.start();
  assert.equal(second.snapshot.selectedNode, null);
  first.dispose();
  assert.equal(second.active, true);
  assert.equal(scene.children.length, 1);
  second.update(1.25);
  assert.equal(second.snapshot.phase, 'map');
  second.dispose();
  assert.equal(scene.children.length, 0);
  checks.push('Independent sessions do not share selection or lifecycle ownership.');
}

const report = {
  result: 'PASS', source: 'src/travel.ts', checks, vfxBudget,
  transitionSeconds: 1.25, repeatedCycles: 25, disposedResources,
  note: 'Actual source-model and Three.js lifecycle checks; browser rendering, controls and OS preference wiring are separate integration checks.',
};
await writeFile(new URL('./travel-checks.json', import.meta.url), `${JSON.stringify(report, null, 2)}\n`);
console.log(JSON.stringify(report, null, 2));
