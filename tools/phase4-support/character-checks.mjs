import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { pathToFileURL, fileURLToPath } from 'node:url';
const repo = fileURLToPath(new URL('../../', import.meta.url)).replace(/\/$/, '');
const url = path => pathToFileURL(`${repo}/${path}`).href;
const ts = (await import(url('node_modules/typescript/lib/typescript.js'))).default;
const T = await import(url('node_modules/three/build/three.module.js'));
const { GLTFLoader } = await import(url('node_modules/three/examples/jsm/loaders/GLTFLoader.js'));
async function moduleURL(file, replacements = {}) {
  const source = (await fs.readFile(`${repo}/${file}`, 'utf8')).replaceAll('import.meta.env.BASE_URL', "'/'");
  let code = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText;
  code = code.replace(/from '([^']+)'/g, (full, name) => {
    const target = replacements[name] ?? (name === 'three' ? url('node_modules/three/build/three.module.js') : name.startsWith('three/addons/') ? url(`node_modules/three/examples/jsm/${name.slice(13)}`) : null);
    return target ? `from '${target}'` : full;
  });
  return `data:text/javascript;base64,${Buffer.from(code).toString('base64')}`;
}
const { CharacterLibrary } = await import(await moduleURL('src/characters.ts', { './world-assets': await moduleURL('src/world-assets.ts') }));
globalThis.location = { href: 'http://localhost/' };
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };
const disposed = object => { const c = { n: 0 }; object.addEventListener('dispose', () => c.n++); return c; };
class Bitmap { width = 4; height = 4; closed = 0; close() { this.closed++; } }
globalThis.ImageBitmap = Bitmap;
function fixture() {
  const scene = new T.Group(), hip = new T.Bone(), hand = new T.Bone(); hip.name = 'hip'; hand.name = 'hand'; hip.add(hand); scene.add(hip);
  const geometry = new T.BoxGeometry(.4, 1.8, .3).translate(0, .9, 0); const count = geometry.attributes.position.count;
  const indices = new Uint16Array(count * 4), weights = new Float32Array(count * 4); for (let i = 0; i < count; i++) weights[i * 4] = 1;
  geometry.setAttribute('skinIndex', new T.Uint16BufferAttribute(indices, 4)); geometry.setAttribute('skinWeight', new T.Float32BufferAttribute(weights, 4));
  const bitmap = new Bitmap(), map = new T.Texture(bitmap), body = new T.MeshStandardMaterial({ map }), cloth = new T.MeshStandardMaterial({ map }); body.name = 'MAT_body'; cloth.name = 'MAT_cloth';
  const skeleton = new T.Skeleton([hip, hand]);
  for (const [name, material] of [['body', body], ['cloth', cloth]]) { const mesh = new T.SkinnedMesh(geometry, material); mesh.name = name; scene.add(mesh); mesh.bind(skeleton); }
  const animations = ['idle', 'walk', 'run', 'talk'].map((name, i) => new T.AnimationClip(name, 1, [new T.QuaternionKeyframeTrack('hand.quaternion', [0, .5, 1], [0, 0, 0, 1, Math.sin((i + 1) * .1), 0, 0, Math.cos((i + 1) * .1), 0, 0, 0, 1])]));
  return { scene, animations, geometry, body, cloth, bitmap, map, counters: [disposed(geometry), disposed(body), disposed(cloth), disposed(map)] };
}
function loader(player, npc) {
  let requests = 0;
  globalThis.fetch = async (source, { signal } = {}) => { signal?.throwIfAborted(); requests++; return new Response(new Uint8Array([String(source).includes('npcs') ? 2 : 1])); };
  GLTFLoader.prototype.parseAsync = async bytes => new Uint8Array(bytes)[0] === 1 ? player : npc;
  return () => requests;
}
function released(f) { assert.ok(f.counters.every(c => c.n === 1), f.counters.map(c => c.n).join(',')); assert.equal(f.bitmap.closed, 1); }
const checks = [];
{
  const player = fixture(), npc = fixture(), requests = loader(player, npc), library = new CharacterLibrary();
  assert.throws(() => library.create({ id: 'premature', kind: 'npc' }), /finish loading/);
  assert.equal(library.load(), library.load()); await library.load(); assert.equal(requests(), 2); assert.equal(library.diagnostics.state, 'ready');
  const a = library.create({ id: 'mira', kind: 'npc', tint: '#aa5533' }), b = library.create({ id: 'torr', kind: 'npc', tint: '#556677' });
  const meshA = a.root.getObjectByName('body'), meshB = b.root.getObjectByName('body');
  assert.equal(meshA.geometry, meshB.geometry); assert.equal(meshA.material, meshB.material); assert.notEqual(meshA.skeleton, meshB.skeleton); assert.notEqual(meshA.skeleton.bones[0], meshB.skeleton.bones[0]);
  const clothA = a.root.getObjectByName('cloth').material, clothB = b.root.getObjectByName('cloth').material;
  assert.notEqual(clothA, clothB); assert.equal(clothA.map, clothB.map); assert.notEqual(clothA.color.getHex(), clothB.color.getHex());
  const boneB = b.root.getObjectByName('hand'); const before = boneB.quaternion.clone();
  a.update(.25, { speed: 3.4 }); assert.equal(a.diagnostics.animation, 'walk'); assert.equal(a.diagnostics.playbackRate, 1); assert.ok(boneB.quaternion.equals(before)); assert.equal(b.diagnostics.time, 0);
  a.update(.25, { speed: 6 }); assert.equal(a.diagnostics.animation, 'run'); assert.equal(a.diagnostics.playbackRate, 1);
  a.update(.25, { speed: 2 }); assert.equal(a.diagnostics.animation, 'walk'); assert.ok(a.diagnostics.playbackRate < 1);
  a.update(.25, { speed: 0, talking: true }); assert.equal(a.diagnostics.animation, 'talk');
  a.update(.25, { speed: 3.4, talking: true }); assert.equal(a.diagnostics.animation, 'walk');
  a.update(.25, { speed: 0 }); assert.equal(a.diagnostics.animation, 'idle'); assert.equal(requests(), 2);
  assert.throws(() => library.create({ id: 'mira', kind: 'npc' }), /unique/);
  meshA.skeleton.computeBoneTexture(); const boneTextureDispose = disposed(meshA.skeleton.boneTexture), tintDispose = disposed(clothA);
  a.dispose(); a.dispose(); assert.equal(tintDispose.n, 1); assert.equal(boneTextureDispose.n, 1); assert.equal(npc.counters[3].n, 0); assert.equal(library.diagnostics.instances, 1);
  b.update(.1, { speed: 3.4 }); assert.equal(b.diagnostics.animation, 'walk');
  library.dispose(); library.dispose(); released(player); released(npc); assert.equal(library.diagnostics.instances, 0); assert.throws(() => library.create({ id: 'after', kind: 'npc' }), /finish loading/);
  checks.push('Two GLBs load only once; clones share geometry/atlas/body material but have independent bones, mixers, clothing tints and bone textures.');
  checks.push('Actual speed selects idle/walk/run with rate scaling; stationary talk and moving talk transitions work without affecting another clone.');
  checks.push('Actor/library disposal is idempotent, frees skeleton/tint resources, and preserves shared maps until library shutdown.');
}
for (const [name, mutate, message] of [
  ['missing clip', f => f.animations.pop(), /exactly idle/],
  ['bad binding', f => f.animations[0].tracks[0].name = 'absent.quaternion', /invalid animation target/],
  ['bad weight', f => f.geometry.attributes.skinWeight.setX(0, .3), /sum to one/],
  ['bad scale', f => f.scene.scale.setScalar(2), /1.8 m humanoid/],
]) {
  const player = fixture(), npc = fixture(); mutate(player); loader(player, npc); const library = new CharacterLibrary();
  await assert.rejects(library.load(), message); released(player); released(npc); assert.equal(library.diagnostics.state, 'disposed');
  checks.push(`Rejects ${name} and releases both concurrently loaded asset resource sets.`);
}
{
  const player = fixture(), npc = fixture(), pending = [deferred(), deferred()], started = deferred(); let decodes = 0;
  loader(player, npc); GLTFLoader.prototype.parseAsync = bytes => { if (++decodes === 2) started.resolve(); return pending[new Uint8Array(bytes)[0] - 1].promise; };
  const library = new CharacterLibrary(), loading = library.load(); const rejected = assert.rejects(loading, { name: 'AbortError' });
  await started.promise; library.dispose(); pending[0].resolve(player); pending[1].resolve(npc); await rejected; await Promise.resolve(); released(player); released(npc);
  checks.push('Shutdown during simultaneous non-cancellable GLTF decodes releases both late results.');
}
console.log(JSON.stringify({ passed: true, checks, count: checks.length, note: 'Actual source modules and Three.js skinned assets/mixers; only network/decode inputs are fixtures. No project build or runtime asset writes.' }, null, 2));
