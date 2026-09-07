// Derive a bounded runtime mesh from the supplied GLB. Original files are never edited.
import assert from 'node:assert/strict';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { MeshoptSimplifier } from 'meshoptimizer';
import { Object3D, Quaternion, Vector3 } from 'three';

const root = new URL('../', import.meta.url);
const source = new URL('meshy/ward-guard/model/character-rigged.glb', root);
const target = new URL('unity/staging/ward-guard.glb', root);
const raw = await readFile(source);
assert.equal(raw.toString('ascii', 0, 4), 'glTF');
assert.equal(raw.readUInt32LE(8), raw.length);
const jsonLength = raw.readUInt32LE(12);
const doc = JSON.parse(raw.subarray(20, 20 + jsonLength));
const binary = raw.subarray(28 + jsonLength);
assert.equal(doc.meshes.length, 1);
assert.equal(doc.meshes[0].primitives.length, 1);
assert.equal(doc.skins[0].joints.length, 24);
const primitive = doc.meshes[0].primitives[0];
const arities = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4 };
const types = { 5121: Uint8Array, 5123: Uint16Array, 5125: Uint32Array, 5126: Float32Array };
function array(id) {
  const a = doc.accessors[id], v = doc.bufferViews[a.bufferView], Type = types[a.componentType];
  assert(!v.byteStride && !a.sparse && !(a.byteOffset ?? 0));
  const offset = binary.byteOffset + (v.byteOffset ?? 0);
  return new Type(binary.buffer.slice(offset, offset + a.count * arities[a.type] * Type.BYTES_PER_ELEMENT));
}
const attributes = Object.fromEntries(Object.entries(primitive.attributes).map(([name, id]) => [name, array(id)]));
const positions = attributes.POSITION, count = positions.length / 3;
const indices = Uint32Array.from(array(primitive.indices));
// Include UVs, normals and a per-bone weight vector in the collapse error.
// Keep surviving vertices and their original four normalized skin influences.
const channels = 29, weightedAttributes = new Float32Array(count * channels);
for (let i = 0; i < count; i++) {
  weightedAttributes.set(attributes.NORMAL.subarray(i * 3, i * 3 + 3), i * channels);
  weightedAttributes.set(attributes.TEXCOORD_0.subarray(i * 2, i * 2 + 2), i * channels + 3);
  for (let k = 0; k < 4; k++) weightedAttributes[i * channels + 5 + attributes.JOINTS_0[i * 4 + k]] += attributes.WEIGHTS_0[i * 4 + k];
}
await MeshoptSimplifier.ready;
const [reduced, error] = MeshoptSimplifier.simplifyWithAttributes(indices, positions, 3,
  weightedAttributes, channels, [.3, .3, .3, 1, 1, ...Array(24).fill(1)], null, 6000 * 3, .01, ['RegularizeLight']);
assert(reduced.length <= 6000 * 3, 'Guard exceeds its six-thousand-triangle runtime budget.');
const [remap, vertexCount] = MeshoptSimplifier.compactMesh(reduced);
const replacements = new Map();
function replace(id, values, newCount) {
  const a = doc.accessors[id], view = a.bufferView;
  assert.equal(doc.accessors.filter(candidate => candidate.bufferView === view).length, 1);
  replacements.set(view, Buffer.from(values.buffer, values.byteOffset, values.byteLength));
  a.count = newCount;
  if (a.min || a.max) {
    const stride = arities[a.type];
    a.min = Array.from({ length: stride }, (_, c) => Math.min(...Array.from({ length: newCount }, (_, i) => values[i * stride + c])));
    a.max = Array.from({ length: stride }, (_, c) => Math.max(...Array.from({ length: newCount }, (_, i) => values[i * stride + c])));
  }
}
for (const [name, id] of Object.entries(primitive.attributes)) {
  const data = attributes[name], stride = arities[doc.accessors[id].type];
  const compact = new data.constructor(vertexCount * stride);
  for (let i = 0; i < count; i++) if (remap[i] < vertexCount) compact.set(data.subarray(i * stride, (i + 1) * stride), remap[i] * stride);
  replace(id, compact, vertexCount);
}
replace(primitive.indices, Uint16Array.from(reduced), reduced.length);
doc.accessors[primitive.indices].componentType = 5123;
doc.materials[0].name = 'MAT_guard';
assert.equal(doc.animations.length, 1);
const pose = doc.animations[0];
assert(pose.samplers.every(s => doc.accessors[s.input].count === 1), 'Expected the supplied single standing pose.');
// Pose the existing rig; retain the source geometry and original inverse bind matrices.
const nodes = doc.nodes.map(n => {
  const object = new Object3D(); object.name = n.name;
  if (n.translation) object.position.fromArray(n.translation);
  if (n.rotation) object.quaternion.fromArray(n.rotation);
  if (n.scale) object.scale.fromArray(n.scale);
  return object;
});
doc.nodes.forEach((n, i) => n.children?.forEach(child => nodes[i].add(nodes[child])));
for (const channel of pose.channels) {
  const object = nodes[channel.target.node], value = array(pose.samplers[channel.sampler].output);
  object[{ translation: 'position', rotation: 'quaternion', scale: 'scale' }[channel.target.path]].fromArray(value);
}
const roots = nodes.filter(n => !n.parent), armPoses = {};
for (const side of ['Left', 'Right']) {
  const sign = side === 'Left' ? 1 : -1;
  for (const [joint, child, direction] of [
    ['Arm', 'ForeArm', [sign * .13, -1, .02]],
    ['ForeArm', 'Hand', [sign * .07, -1, .12]],
  ]) {
    roots.forEach(n => n.updateMatrixWorld(true));
    const index = doc.nodes.findIndex(n => n.name === side + joint), object = nodes[index];
    const end = nodes.find(n => n.name === side + child);
    const current = end.getWorldPosition(new Vector3()).sub(object.getWorldPosition(new Vector3())).normalize();
    const delta = new Quaternion().setFromUnitVectors(current, new Vector3(...direction).normalize());
    const world = delta.multiply(object.getWorldQuaternion(new Quaternion()));
    object.quaternion.copy(object.parent.getWorldQuaternion(new Quaternion()).invert().multiply(world)).normalize();
    doc.nodes[index].rotation = object.quaternion.toArray();
    const channel = pose.channels.find(c => c.target.node === index && c.target.path === 'rotation');
    replace(pose.samplers[channel.sampler].output, Float32Array.from(object.quaternion.toArray()), 1);
    armPoses[side + joint] = object.quaternion.toArray();
  }
}
// These are explicit static fallbacks, not authored locomotion or talking clips.
doc.animations = ['idle', 'walk', 'run', 'talk'].map(name => ({ ...structuredClone(pose), name,
  extras: { staticPose: true, sourceClip: pose.name, fallback: 'relaxed-standing-pose' } }));
doc.asset.extras = { ...doc.asset.extras, source: 'meshy/ward-guard/model/character-rigged.glb',
  sourceSha256: createHash('sha256').update(raw).digest('hex'), sourceTriangles: indices.length / 3,
  runtimeTriangles: reduced.length / 3, simplificationError: error,
  armPoses, animationNote: 'Relaxed arms-down pose derived from the supplied rig. Walk/run FBX sources are retained separately.' };
const chunks = []; let offset = 0;
for (const [i, view] of doc.bufferViews.entries()) {
  const bytes = replacements.get(i) ?? binary.subarray(view.byteOffset ?? 0, (view.byteOffset ?? 0) + view.byteLength);
  view.byteOffset = offset; view.byteLength = bytes.length;
  const padding = Buffer.alloc((-bytes.length >>> 0) % 4);
  chunks.push(bytes, padding); offset += bytes.length + padding.length;
}
doc.buffers = [{ byteLength: offset }];
const json = Buffer.from(JSON.stringify(doc));
const jsonPadding = Buffer.alloc((-json.length >>> 0) % 4, 32);
const head = Buffer.alloc(20), binHead = Buffer.alloc(8);
head.write('glTF'); head.writeUInt32LE(2, 4); head.writeUInt32LE(28 + json.length + jsonPadding.length + offset, 8);
head.writeUInt32LE(json.length + jsonPadding.length, 12); head.write('JSON', 16);
binHead.writeUInt32LE(offset); binHead.writeUInt32LE(0x004e4942, 4);
await mkdir(new URL('unity/staging/', root), { recursive: true });
await writeFile(target, Buffer.concat([head, json, jsonPadding, binHead, ...chunks]));
assert.equal(createHash('sha256').update(await readFile(source)).digest('hex'), doc.asset.extras.sourceSha256);
await mkdir(new URL('tools/model-import/', root), { recursive: true });
await writeFile(new URL('tools/model-import/guard-import.json', root), JSON.stringify(doc.asset.extras, null, 2) + '\n');
console.log(JSON.stringify({ file: fileURLToPath(target), vertices: vertexCount, ...doc.asset.extras }, null, 2));
