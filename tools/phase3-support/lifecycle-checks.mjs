import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { pathToFileURL, fileURLToPath } from 'node:url';
const repo = fileURLToPath(new URL('../../', import.meta.url)).replace(/\/$/, '');
const url = path => pathToFileURL(`${repo}/${path}`).href;
const ts = (await import(url('node_modules/typescript/lib/typescript.js'))).default;
const three = await import(url('node_modules/three/build/three.module.js'));
const { GLTFLoader } = await import(url('node_modules/three/examples/jsm/loaders/GLTFLoader.js'));
const { BoxGeometry, Group, Mesh, MeshStandardMaterial, Texture, TextureLoader, Scene, Vector3, PMREMGenerator, WebGLRenderTarget } = three;
async function moduleURL(file, replacements = {}) {
  let source = await fs.readFile(`${repo}/${file}`, 'utf8');
  source = source.replaceAll('import.meta.env.BASE_URL', "'/'");
  let code = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText;
  code = code.replace(/from '([^']+)'/g, (full, name) => {
    const target = replacements[name] ?? (name === 'three' ? url('node_modules/three/build/three.module.js') : name.startsWith('three/addons/') ? url(`node_modules/three/examples/jsm/${name.slice(13)}`) : null);
    return target ? `from '${target}'` : full;
  });
  return `data:text/javascript;base64,${Buffer.from(code).toString('base64')}`;
}
const assetsURL = await moduleURL('src/world-assets.ts');
const { ownMaterialTextures } = await import(assetsURL);
const { World } = await import(await moduleURL('src/world.ts', { './world-assets': assetsURL, './layout': await moduleURL('src/layout.ts') }));
const { Atmosphere } = await import(await moduleURL('src/atmosphere.ts'));
globalThis.location = { href: 'http://localhost/' };
const tests = [];
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };
const countDisposals = object => { const counter = { count: 0 }; object.addEventListener('dispose', () => counter.count++); return counter; };
class TestBitmap { width = 4; height = 4; closed = 0; close() { this.closed++; } }
globalThis.ImageBitmap = TestBitmap;
function mappedMaterial() { const bitmap = new TestBitmap(); const map = new Texture(bitmap); const material = new MeshStandardMaterial({ map }); return { bitmap, map, material, disposed: countDisposals(material), textureDisposed: countDisposals(map) }; }
function authoredFixture() {
  const scene = new Group(); scene.userData.authoredLandmarks = ['hill_tree'];
  const resources = mappedMaterial(); resources.material.name = 'MAT_stone';
  const geometry = new BoxGeometry(2, 2, 2); const geometryDisposed = countDisposals(geometry);
  const mesh = new Mesh(geometry, resources.material); mesh.name = 'TREE'; mesh.userData.landmark = 'hill_tree'; scene.add(mesh);
  const collider = new Mesh(new BoxGeometry(2, 2, 2), new MeshStandardMaterial()); collider.name = 'COL_tree'; collider.userData = { landmark: 'hill_tree', colliderKind: 'box' }; scene.add(collider);
  return { scene, animations: [], resources, geometryDisposed };
}
function probeFixture(valid = true) {
  const scene = new Group(); const resources = mappedMaterial(); const geometry = new BoxGeometry(2, 2, 2).translate(0, 1, 0); const geometryDisposed = countDisposals(geometry);
  const mesh = new Mesh(geometry, resources.material); mesh.name = valid ? 'PROBE_CUBE' : 'WRONG'; scene.add(mesh);
  return { scene, animations: [], resources, geometryDisposed };
}
function mockWorldFetch() {
  globalThis.fetch = async (source, { signal } = {}) => {
    signal?.throwIfAborted();
    return String(source).endsWith('.json') ? new Response(JSON.stringify({ source: 'world.glb', landmarks: ['hill_tree'] }), { headers: { 'content-type': 'application/json' } }) : new Response(new Uint8Array([1, 2, 3]));
  };
}
function assertReleased(fixture) {
  assert.equal(fixture.geometryDisposed.count, 1);
  assert.equal(fixture.resources.disposed.count, 1);
  assert.equal(fixture.resources.textureDisposed.count, 1);
  assert.equal(fixture.resources.bitmap.closed, 1);
}
// Shared texture variants must retain their decoded bitmap until the last material releases it.
{
  const bitmap = new TestBitmap(), first = new Texture(bitmap), second = new Texture(bitmap);
  const a = new MeshStandardMaterial({ map: first }), b = new MeshStandardMaterial({ map: first }), c = new MeshStandardMaterial({ map: second });
  const firstDisposals = countDisposals(first), secondDisposals = countDisposals(second);
  ownMaterialTextures([a, b, c]); a.dispose(); assert.equal(firstDisposals.count, 0); b.dispose(); assert.equal(firstDisposals.count, 1); assert.equal(bitmap.closed, 0);
  c.dispose(); c.dispose(); assert.equal(secondDisposals.count, 1); assert.equal(bitmap.closed, 1);
  tests.push('Shared textures and bitmap variants release exactly once after their final owner.');
}
// Disposing before TextureLoader finishes must not attach a map to an already disposed material.
{
  const pending = deferred(); TextureLoader.prototype.loadAsync = () => pending.promise;
  let fetchCalls = 0; globalThis.fetch = () => { fetchCalls++; throw new Error('Unexpected fetch'); };
  const world = new World(); const materialCounters = Object.values(world.materials).map(countDisposals);
  const loading = world.load(); const rejection = assert.rejects(loading, { name: 'AbortError' });
  world.dispose(); world.dispose(); const texture = new Texture(); const disposed = countDisposals(texture); pending.resolve(texture); await rejection;
  assert.equal(disposed.count, 1); assert.equal(fetchCalls, 0); assert.equal(world.scene.children.length, 0); assert.equal(world.colliderDefs.length, 0); assert.ok(materialCounters.every(c => c.count === 1));
  tests.push('Shutdown during paving load releases the late texture and all 11 unmounted materials, without starting GLB loading.');
}
// A decode already in flight cannot be aborted, so its result must be adopted then released.
{
  const fixture = authoredFixture(); const pending = deferred(), started = deferred();
  TextureLoader.prototype.loadAsync = async () => new Texture(); mockWorldFetch();
  GLTFLoader.prototype.parseAsync = () => { started.resolve(); return pending.promise; };
  const world = new World(), loading = world.load(); const rejection = assert.rejects(loading, { name: 'AbortError' });
  await started.promise; world.dispose(); pending.resolve(fixture); await rejection;
  assertReleased(fixture); assert.equal(world.scene.children.length, 0); assert.equal(world.assets.loaded, false);
  tests.push('Shutdown during GLTF decode releases late geometry, material, map, and ImageBitmap without attaching the authored world.');
}
// A successfully attached world must also clean a historical probe arriving later.
{
  const fixture = authoredFixture(), probe = probeFixture(), pending = deferred(), started = deferred();
  TextureLoader.prototype.loadAsync = async () => new Texture(); mockWorldFetch(); GLTFLoader.prototype.parseAsync = async () => fixture;
  GLTFLoader.prototype.loadAsync = () => { started.resolve(); return pending.promise; };
  const world = new World(), loading = world.load(); const rejection = assert.rejects(loading, { name: 'AbortError' });
  await started.promise; assert.equal(world.assets.loaded, true); world.dispose(); pending.resolve(probe); await rejection;
  assertReleased(fixture); assertReleased(probe); assert.equal(world.scene.children.length, 0); assert.equal(world.probe.loaded, false);
  tests.push('Shutdown after world attachment releases existing assets and a late probe; no disposed scene is repopulated.');
}
// Validation errors before probe attachment must not orphan its decoded resources.
{
  const fixture = authoredFixture(), probe = probeFixture(false);
  TextureLoader.prototype.loadAsync = async () => new Texture(); mockWorldFetch(); GLTFLoader.prototype.parseAsync = async () => fixture; GLTFLoader.prototype.loadAsync = async () => probe;
  const world = new World(); await assert.rejects(world.load(), /missing the Blender render mesh/); world.dispose();
  assertReleased(fixture); assertReleased(probe); assert.equal(world.scene.children.length, 0);
  tests.push('Malformed probe rejection releases both decoded probe resources and the partially loaded world.');
}
// A normal load then repeated dispose must release shared scene resources only once.
{
  const fixture = authoredFixture(), probe = probeFixture();
  TextureLoader.prototype.loadAsync = async () => new Texture(); mockWorldFetch(); GLTFLoader.prototype.parseAsync = async () => fixture; GLTFLoader.prototype.loadAsync = async () => probe;
  const world = new World(); await world.load(); assert.equal(world.probe.loaded, true); assert.ok(world.colliderDefs.length > 0);
  const geometry = new BoxGeometry(), material = new MeshStandardMaterial(); const gd = countDisposals(geometry), md = countDisposals(material);
  world.scene.add(new Mesh(geometry, material), new Mesh(geometry, material)); world.dispose(); world.dispose();
  assertReleased(fixture); assertReleased(probe); assert.equal(gd.count, 1); assert.equal(md.count, 1); assert.equal(world.colliderDefs.length, 0);
  tests.push('Completed world disposal is idempotent and deduplicates geometry/material shared by scene meshes.');
}
// Mock only the GPU bake, keeping actual Three resources and atmosphere state transitions.
{
  let calls = 0, generatorDisposals = 0, fail = false; const targets = [], targetDisposals = [];
  PMREMGenerator.prototype.fromScene = function(scene) {
    calls++; assert.equal(scene.children.length, 1); assert.equal(scene.children[0].material.uniforms.showSunDisc.value, 0);
    if (fail) throw new Error('Bake failed');
    const target = new WebGLRenderTarget(128, 128); targets.push(target); targetDisposals.push(countDisposals(target)); return target;
  };
  PMREMGenerator.prototype.dispose = function() { generatorDisposals++; };
  const scene = new Scene(), sun = new Vector3(1, 2, 3), atmosphere = new Atmosphere({}, scene, sun);
  assert.equal(calls, 1); assert.equal(scene.environment, targets[0].texture); assert.equal(atmosphere.sky.parent, scene);
  atmosphere.syncSun(sun.clone()); assert.equal(calls, 1);
  const nextSun = new Vector3(4, 5, 6); atmosphere.syncSun(nextSun); assert.equal(calls, 2); assert.equal(scene.environment, targets[1].texture); assert.equal(targetDisposals[0].count, 1); assert.equal(targetDisposals[1].count, 0);
  fail = true; assert.throws(() => atmosphere.syncSun(new Vector3(7, 8, 9)), /Bake failed/); assert.equal(scene.environment, targets[1].texture); assert.ok(atmosphere.sky.material.uniforms.sunPosition.value.equals(nextSun)); assert.equal(atmosphere.sky.parent, scene); assert.equal(atmosphere.sky.material.uniforms.showSunDisc.value, 1);
  atmosphere.dispose(); atmosphere.dispose(); atmosphere.syncSun(sun); assert.equal(calls, 3); assert.equal(generatorDisposals, 3); assert.equal(targetDisposals[1].count, 1); assert.equal(scene.environment, null);
  atmosphere.sky.geometry.dispose(); atmosphere.sky.material.dispose();
  tests.push('Explicit sun changes rebake once, release the previous target, preserve sky ownership/state on failure, and do not rebake after disposal.');
}
console.log(JSON.stringify({ passed: true, count: tests.length, checks: tests, note: 'Read source via TypeScript transpilation in memory. Deferred asset loaders and GPU bake backend are controlled fixtures; actual Three.js resources and lifecycle code are exercised. No dist files changed.' }, null, 2));
