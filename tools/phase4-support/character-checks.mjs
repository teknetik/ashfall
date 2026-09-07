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
function fixture({ external = false, boneCount = external ? 53 : 19, materialCount = external ? 8 : 2, trianglesPerMesh } = {}) {
  const scene = new T.Group(), hip = new T.Bone(), hand = new T.Bone();
  hip.name = external ? 'pelvis' : 'hips'; hand.name = external ? 'upperarm_r' : 'upper_armR';
  hand.userData.name = external ? 'upperarm_r' : 'upper_arm.R'; hip.add(hand); scene.add(hip);
  const bones = [hip, hand];
  if (external) { const root = new T.Bone(); root.name = 'Root'; root.add(hip); scene.add(root); bones.unshift(root); }
  for (const name of external ? ['head', 'lowerarm_r', 'thigh_l', 'thigh_r'] : ['head', 'forearm.R', 'thigh.L', 'thigh.R']) {
    const bone = new T.Bone(); bone.name = name.replaceAll('.', ''); bone.userData.name = name; hip.add(bone); bones.push(bone);
  }
  while (bones.length < boneCount) { const bone = new T.Bone(); bone.name = `extra_${bones.length}`; hip.add(bone); bones.push(bone); }
  const geometry = new T.BoxGeometry(.4, 1.8, .3).translate(0, .9, 0); const count = geometry.attributes.position.count;
  // Repeat valid box indices only to exercise the import triangle ceiling. This
  // synthetic fixture is never exported, rendered or presented as character art.
  if (trianglesPerMesh) { const index = geometry.index.array; geometry.setIndex(Array.from({ length: trianglesPerMesh * 3 }, (_, i) => index[i % index.length])); }
  const indices = new Uint16Array(count * 4), weights = new Float32Array(count * 4); for (let i = 0; i < count; i++) weights[i * 4] = 1;
  geometry.setAttribute('skinIndex', new T.Uint16BufferAttribute(indices, 4)); geometry.setAttribute('skinWeight', new T.Float32BufferAttribute(weights, 4));
  const bitmap = new Bitmap(), map = new T.Texture(bitmap), body = new T.MeshStandardMaterial({ map }), cloth = new T.MeshStandardMaterial({ map }); body.name = 'MAT_body'; cloth.name = 'MAT_cloth';
  const materials = [body, cloth], textures = [map], bitmaps = [bitmap];
  if (external) {
    const normalBitmap = new Bitmap(), surfaceBitmap = new Bitmap(); bitmaps.push(normalBitmap, surfaceBitmap);
    const alternateMap = map.clone(), normalMap = new T.Texture(normalBitmap), surfaceMap = new T.Texture(surfaceBitmap);
    map.colorSpace = alternateMap.colorSpace = T.SRGBColorSpace; textures.push(alternateMap, normalMap, surfaceMap);
    while (materials.length < materialCount) { const material = new T.MeshStandardMaterial({ map: alternateMap }); material.name = `MPFB_material_${materials.length}`; materials.push(material); }
    for (const material of materials) { material.normalMap = normalMap; material.roughnessMap = material.metalnessMap = surfaceMap; material.normalScale.set(.7, .7); }
    const hair = materials.at(-1); hair.name = 'MPFB_hair'; hair.alphaTest = .37; hair.side = T.DoubleSide;
  }
  const skeleton = new T.Skeleton(bones);
  for (const [i, material] of materials.entries()) { const mesh = new T.SkinnedMesh(geometry, material); mesh.name = ['body', 'cloth'][i] ?? `part_${i}`; scene.add(mesh); mesh.bind(skeleton); }
  const animations = ['idle', 'walk', 'run', 'talk'].map((name, i) => new T.AnimationClip(name, 1, [new T.QuaternionKeyframeTrack(`${hand.name}.quaternion`, [0, .5, 1], [0, 0, 0, 1, Math.sin((i + 1) * .1), 0, 0, Math.cos((i + 1) * .1), 0, 0, 0, 1])]));
  return { scene, animations, geometry, body, cloth, bitmap, map, materials, textures, bitmaps, counters: [disposed(geometry), ...materials.map(disposed), ...textures.map(disposed)] };
}
function loader(player, npc) {
  let requests = 0;
  globalThis.fetch = async (source, { signal } = {}) => { signal?.throwIfAborted(); requests++; return new Response(new Uint8Array([String(source).includes('npcs') ? 2 : 1])); };
  GLTFLoader.prototype.parseAsync = async bytes => new Uint8Array(bytes)[0] === 1 ? player : npc;
  return () => requests;
}
function addProxy(f, triangles = 3000) {
  const source = f.scene.getObjectByName('body'), geometry = f.geometry.clone(), indices = geometry.index.array;
  geometry.setIndex(Array.from({ length: triangles * 3 }, (_, i) => indices[i % indices.length]));
  const proxy = new T.SkinnedMesh(geometry, f.body); proxy.name = 'COLONIST_shadow_proxy'; proxy.userData.shadowProxy = true;
  f.scene.add(proxy); proxy.bind(source.skeleton); f.counters.push(disposed(geometry)); return proxy;
}
function released(f) { assert.ok(f.counters.every(c => c.n === 1), f.counters.map(c => c.n).join(',')); assert.ok(f.bitmaps.every(bitmap => bitmap.closed === 1)); }
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
  assert.deepEqual(a.diagnostics.pose.map(bone => bone.name).sort(), ['hips', 'head', 'upper_arm.R', 'forearm.R', 'thigh.L', 'thigh.R'].sort());
  const boneB = b.root.getObjectByName('upper_armR'); const before = boneB.quaternion.clone();
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
{
  const player = fixture({ external: true, trianglesPerMesh: 5000 }), npc = fixture(); loader(player, npc);
  const library = new CharacterLibrary(); await library.load();
  assert.equal(library.diagnostics.assets.player.triangles, 40000); assert.equal(library.diagnostics.assets.player.bones, 53);
  assert.equal(library.diagnostics.assets.player.materials.length, 8); assert.equal(library.diagnostics.assets.player.textures.length, 4);
  const a = library.create({ id: 'external_player', kind: 'player', tint: '#ff0000' });
  const b = library.create({ id: 'second_player', kind: 'player' });
  assert.equal(a.root.getObjectByName('cloth').material, player.cloth, 'Player must never run the original NPC cloth recoloring shader.');
  assert.equal(a.root.getObjectByName('part_7').material, b.root.getObjectByName('part_7').material);
  const hair = a.root.getObjectByName('part_7').material;
  assert.equal(hair.alphaTest, .37); assert.equal(hair.transparent, false); assert.equal(hair.depthWrite, true); assert.equal(hair.side, T.DoubleSide);
  assert.equal(hair.map, player.textures[1]); assert.equal(hair.normalMap, player.textures[2]); assert.equal(hair.roughnessMap, player.textures[3]);
  assert.equal(hair.metalnessMap, hair.roughnessMap); assert.deepEqual(hair.normalScale.toArray(), [.7, .7]);
  assert.equal(hair.map.colorSpace, T.SRGBColorSpace); assert.equal(hair.normalMap.colorSpace, T.NoColorSpace);
  const pose = a.diagnostics.pose; assert.deepEqual(pose.map(bone => bone.name).sort(), ['pelvis', 'head', 'upperarm_r', 'lowerarm_r', 'thigh_l', 'thigh_r'].sort());
  const frozen = b.diagnostics.pose; a.update(.25, { speed: 3.4 });
  assert.notDeepEqual(a.diagnostics.pose, pose); assert.deepEqual(b.diagnostics.pose, frozen);
  assert.equal(a.diagnostics.playbackRate, 3.4 / 1.5); assert.equal(a.diagnostics.nominalMetersPerSecond, 1.5);
  assert.equal(library.diagnostics.assets.player.clips.find(clip => clip.name === 'walk').calibrationSource, 'mpfb-default');
  a.update(.25, { speed: 6 }); assert.equal(a.diagnostics.animation, 'run'); assert.equal(a.diagnostics.playbackRate, 6 / 3.6104);
  const arm = a.root.getObjectByName('upperarm_r'); arm.position.x = .123;
  assert.equal(a.diagnostics.pose.find(bone => bone.name === 'upperarm_r').position[0], .123, 'Diagnostics must read actual clone bones.');
  a.dispose(); assert.ok(player.counters.every(c => c.n === 0), 'Source PBR resources must outlive a disposed actor.');
  library.dispose(); released(player); released(npc);
  checks.push('53-bone/8-material/40k-triangle player preserves independent PBR maps, masked double-sided hair, shared bitmap lifetime and original player materials.');
  checks.push('Legacy and MPFB pose names report actual clone bones; animation changes one instance while the other pose stays frozen.');
  checks.push('MPFB fallback calibrates walk at 1.5m/s and run at 3.6104m/s; the controller walk reaches 2.267x instead of clipping at the old 1.6x cap.');
}
{
  const player = fixture({ external: true }), npc = fixture(), sourceProxy = addProxy(player);
  loader(player, npc); const library = new CharacterLibrary(); await library.load();
  const metrics = library.diagnostics.assets.player;
  assert.equal(metrics.visibleTriangles, 96); assert.equal(metrics.shadowProxyTriangles, 3000); assert.equal(metrics.triangles, 3096);
  assert.equal(library.diagnostics.assets.npc.shadowProxyTriangles, 0);
  const a = library.create({ id: 'proxy_player_a', kind: 'player' }), b = library.create({ id: 'proxy_player_b', kind: 'player' });
  const proxyA = a.root.getObjectByName('COLONIST_shadow_proxy'), proxyB = b.root.getObjectByName('COLONIST_shadow_proxy');
  const visibleA = a.root.getObjectByName('body');
  assert.equal(proxyA.geometry, sourceProxy.geometry); assert.equal(proxyA.skeleton.bones[0], visibleA.skeleton.bones[0]);
  assert.notEqual(proxyA.skeleton.bones[0], proxyB.skeleton.bones[0]);
  assert.notEqual(proxyA.material, proxyB.material); assert.notEqual(proxyA.material, player.body);
  assert.equal(visibleA.material, player.body); assert.equal(player.body.colorWrite, true); assert.equal(player.body.depthWrite, true);
  a.root.traverse(object => { if (object.isMesh) { assert.equal(object.castShadow, object === proxyA); assert.equal(object.receiveShadow, object !== proxyA); } });
  assert.equal(proxyA.visible, true); assert.equal(proxyA.frustumCulled, false); assert.equal(proxyA.layers.mask, visibleA.layers.mask);
  assert.equal(proxyA.material.visible, true); assert.equal(proxyA.material.colorWrite, false); assert.equal(proxyA.material.depthWrite, false);
  assert.equal(proxyA.material.depthTest, true); assert.equal(proxyA.material.transparent, false); assert.equal(proxyA.material.opacity, 1);
  assert.equal(proxyA.material.alphaTest, 0); assert.equal(proxyA.material.alphaMap, null);
  const disposedA = disposed(proxyA.material), disposedB = disposed(proxyB.material);
  a.dispose(); a.dispose(); assert.equal(disposedA.n, 1); assert.equal(disposedB.n, 0); assert.ok(player.counters.every(c => c.n === 0));
  library.dispose(); assert.equal(disposedB.n, 1); released(player); released(npc);
  checks.push('Player proxy alone casts shadows, keeps color/depth writes off without hiding or culling, and shares the cloned rig while visible armour receives shadows.');
  checks.push('Proxy triangle counts include source geometry honestly; per-instance proxy material disposal preserves shared source material/maps until shutdown.');
}
{
  const player = fixture({ external: true }), npc = fixture();
  for (const clip of player.animations) clip.userData.nominalMetersPerSecond = clip.name === 'walk' ? 2 : clip.name === 'run' ? 5.2 : 0;
  loader(player, npc); const library = new CharacterLibrary(); await library.load();
  const a = library.create({ id: 'calibrated_player', kind: 'player' }), b = library.create({ id: 'legacy_npc', kind: 'npc' });
  a.update(.25, { speed: 3.4 }); assert.equal(a.diagnostics.playbackRate, 1.7); assert.equal(a.diagnostics.nominalMetersPerSecond, 2);
  a.update(.25, { speed: 6 }); assert.equal(a.diagnostics.playbackRate, 6 / 5.2);
  assert.equal(library.diagnostics.assets.player.clips.find(clip => clip.name === 'run').calibrationSource, 'clip-metadata');
  b.update(.25, { speed: 3.4 }); assert.equal(b.diagnostics.playbackRate, 1); assert.equal(b.diagnostics.nominalMetersPerSecond, 3.4);
  b.update(.25, { speed: 1 }); assert.equal(b.diagnostics.playbackRate, .55);
  library.dispose(); released(player); released(npc);
  checks.push('Clip metadata overrides rig defaults while the legacy NPC keeps its original speed calibration and lower playback cap.');
}
for (const [name, mutate, message] of [
  ['missing clip', f => f.animations.pop(), /exactly idle/],
  ['bad binding', f => f.animations[0].tracks[0].name = 'absent.quaternion', /invalid animation target/],
  ['bad weight', f => f.geometry.attributes.skinWeight.setX(0, .3), /sum to one/],
  ['bad scale', f => f.scene.scale.setScalar(2), /1.8 m humanoid/],
  ['zero locomotion speed', f => f.animations[1].userData.nominalMetersPerSecond = 0, /nominalMetersPerSecond must be finite and positive/],
  ['nonfinite locomotion speed', f => f.animations[2].userData.nominalMetersPerSecond = NaN, /nominalMetersPerSecond must be finite and positive/],
]) {
  const player = fixture(), npc = fixture(); mutate(player); loader(player, npc); const library = new CharacterLibrary();
  await assert.rejects(library.load(), message); released(player); released(npc); assert.equal(library.diagnostics.state, 'disposed');
  checks.push(`Rejects ${name} and releases both concurrently loaded asset resource sets.`);
}
for (const [name, options, mutate, kind, message] of [
  ['player material overflow', { external: true, materialCount: 9 }, () => {}, 'player', /named standard PBR/],
  ['player bone overflow', { external: true, boneCount: 54 }, () => {}, 'player', /54 bones exceed the 53/],
  ['player triangle overflow', { external: true, trianglesPerMesh: 5001 }, () => {}, 'player', /40008 triangles exceed the 40000/],
  ['blended player hair', { external: true }, f => { f.materials.at(-1).transparent = true; }, 'player', /opaque or alpha-masked/],
  ['external materials on NPC', { external: true, boneCount: 19 }, () => {}, 'npc', /named standard PBR/],
  ['NPC bone overflow', { boneCount: 20 }, () => {}, 'npc', /20 bones exceed the 19/],
  ['split NPC atlas', {}, f => { f.cloth.map = f.map.clone(); f.cloth.map.source = new T.Source(f.bitmap); f.textures.push(f.cloth.map); f.counters.push(disposed(f.cloth.map)); }, 'npc', /same loaded color atlas/],
]) {
  const target = fixture(options), player = kind === 'player' ? target : fixture(), npc = kind === 'npc' ? target : fixture();
  mutate(target); loader(player, npc); const library = new CharacterLibrary();
  await assert.rejects(library.load(), message); released(player); released(npc);
  checks.push(`Rejects ${name} without relaxing NPC contracts or leaking decoded PBR resources.`);
}
for (const [name, configure, kind, message] of [
  ['oversized proxy', f => addProxy(f, 3001), 'player', /at most 3000 triangles/],
  ['duplicate proxy', f => { addProxy(f, 12); addProxy(f, 12); }, 'player', /at most one shadow proxy/],
  ['untagged proxy', f => { delete addProxy(f).userData.shadowProxy; }, 'player', /tagged shadowProxy:true/],
  ['mismatched proxy rig', f => { const proxy = addProxy(f); proxy.skeleton = new T.Skeleton(proxy.skeleton.bones.slice(0, -1)); }, 'player', /same complete rig/],
  ['proxy outside humanoid bounds', f => { addProxy(f).geometry.translate(10, 0, 0); }, 'player', /1.8 m humanoid/],
  ['NPC proxy', f => addProxy(f), 'npc', /one player SkinnedMesh/],
]) {
  const player = fixture({ external: true }), npc = fixture(); configure(kind === 'player' ? player : npc);
  loader(player, npc); const library = new CharacterLibrary(); await assert.rejects(library.load(), message);
  released(player); released(npc); checks.push(`Rejects ${name} and releases source geometry/materials.`);
}
{
  const player = fixture(), npc = fixture(), pending = [deferred(), deferred()], started = deferred(); let decodes = 0;
  loader(player, npc); GLTFLoader.prototype.parseAsync = bytes => { if (++decodes === 2) started.resolve(); return pending[new Uint8Array(bytes)[0] - 1].promise; };
  const library = new CharacterLibrary(), loading = library.load(); const rejected = assert.rejects(loading, { name: 'AbortError' });
  await started.promise; library.dispose(); pending[0].resolve(player); pending[1].resolve(npc); await rejected; await Promise.resolve(); released(player); released(npc);
  checks.push('Shutdown during simultaneous non-cancellable GLTF decodes releases both late results.');
}
console.log(JSON.stringify({ passed: true, checks, count: checks.length, note: 'Actual source modules and Three.js skinned assets/mixers; only network/decode inputs are fixtures. No project build or runtime asset writes.' }, null, 2));
