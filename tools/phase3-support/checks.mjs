import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { PNG } from 'pngjs';

// Retained Phase 1 acceptance route, independent of the runtime's route table.
// A changed authored asset must preserve these passages and support surfaces.
export const MAIN_ROUTE = [
  ['west avenue', [-12, 0, 0]],
  ['hill west stairs ascent', [-4, 1.5, 0]],
  ['hill west plaza', [-4, 1.5, 4]],
  ['hill south plaza', [0, 1.5, 4]],
  ['hill south stairs descent', [0, 0, 12]],
  ['ring gate approach', [0, 0, 31]],
  ['ring gate raised pad', [0, 0.5, 36]],
  ['ring gate steps descent', [0, 0, 31]],
  ['western bypass south', [-13, 0, 28]],
  ['western bypass north', [-13, 0, -29]],
  ['lattice jack approach', [0, 0, -31]],
  ['lattice jack raised pad', [0, 0.5, -36.5]],
];

export const CAMERAS = ['cam_gate', 'cam_avenue', 'cam_hill', 'cam_grid', 'cam_whompah', 'cam_hero'];
export const wrappedAngle = value => Math.atan2(Math.sin(value), Math.cos(value));
export const horizontalDistance = (a, b) => Math.hypot(a.x - b.x, a.z - b.z);

export function inspectPixels(buffer) {
  const png = PNG.sync.read(buffer);
  const colors = new Set();
  let minimum = 255, maximum = 0, lit = 0;
  for (let offset = 0; offset < png.data.length; offset += 4 * 19) {
    const [r, g, b] = png.data.subarray(offset, offset + 3);
    colors.add(`${r >> 4},${g >> 4},${b >> 4}`);
    const intensity = (r + g + b) / 3;
    minimum = Math.min(minimum, intensity);
    maximum = Math.max(maximum, intensity);
    if (intensity > 20) lit++;
  }
  assert(colors.size > 16 && maximum - minimum > 45 && lit > 100,
    'Canvas must contain nonblank, varied scene pixels');
  return { width: png.width, height: png.height, colors: colors.size,
    intensityRange: maximum - minimum, sha256: createHash('sha256').update(buffer).digest('hex') };
}

export function inspectGLB(buffer) {
  assert(buffer.length >= 28 && buffer.toString('ascii', 0, 4) === 'glTF', 'Loaded world must be a GLB binary');
  assert.equal(buffer.readUInt32LE(4), 2, 'GLB version must be 2');
  assert.equal(buffer.readUInt32LE(8), buffer.length, 'GLB declared size must match the network response');
  const jsonLength = buffer.readUInt32LE(12);
  assert.equal(buffer.toString('ascii', 16, 20), 'JSON', 'GLB must contain its JSON asset description');
  assert(20 + jsonLength <= buffer.length, 'GLB JSON must fit in the binary');
  const gltf = JSON.parse(buffer.toString('utf8', 20, 20 + jsonLength).trim());
  assert.equal(gltf.asset?.version, '2.0');
  const nodes = gltf.nodes ?? [];
  const meshes = gltf.meshes ?? [];
  const names = nodes.map(node => node.name ?? '');
  const triangles = meshes.reduce((sum, mesh) => sum + mesh.primitives.reduce((count, primitive) => {
    if ((primitive.mode ?? 4) !== 4) return count;
    const accessor = primitive.indices === undefined ? primitive.attributes.POSITION : primitive.indices;
    return count + (gltf.accessors?.[accessor]?.count ?? 0) / 3;
  }, 0), 0);
  return { bytes: buffer.length, sha256: createHash('sha256').update(buffer).digest('hex'),
    generator: gltf.asset.generator, nodeCount: nodes.length, meshCount: meshes.length,
    materialCount: gltf.materials?.length ?? 0, imageCount: gltf.images?.length ?? 0,
    trianglesInSourceMeshes: triangles, names,
    collisionNodes: names.filter(name => name.startsWith('COL_')),
    externalURIs: [...(gltf.buffers ?? []), ...(gltf.images ?? [])].map(item => item.uri)
      .filter(uri => uri && !uri.startsWith('data:')) };
}

export function assertHealthy(sample, label, colliders) {
  const p = sample.player;
  assert(p && [p.x, p.y, p.z, p.yaw].every(Number.isFinite), `${label}: player coordinates remain finite`);
  assert(p.y >= -0.08, `${label}: feet fell below pavement (${p.y})`);
  assert(Math.abs(p.x) < 60 && Math.abs(p.z) < 46, `${label}: escaped the city collision boundary`);
  assert.equal(sample.state, 'play', `${label}: simulation must remain playable`);
  assert.equal(sample.error, '', `${label}: game must not report a loading/runtime error`);
  assert(sample.renderer.draws > 0 && sample.renderer.draws <= 80,
    `${label}: draw budget exceeded (${sample.renderer.draws})`);
  assert(sample.renderer.tris > 0 && sample.renderer.tris <= 250000,
    `${label}: triangle budget exceeded (${sample.renderer.tris})`);
  const radius = 0.35;
  const bottom = p.y + radius, top = p.y + 1.8 - radius;
  for (const collider of colliders) {
    if (collider.kind === 'halfspace') {
      assert(p.y >= collider.position[1] - 0.04, `${label}: feet penetrated the pavement plane`);
      continue;
    }
    // The GLB importer exposes a quaternion even for axis-aligned boxes. Only
    // genuinely rotated proxies need to defer to swept controller coverage.
    if (collider.rotation && Math.hypot(...collider.rotation.slice(0, 3)) > 1e-6) continue;
    const [x, y, z] = collider.position;
    const halfY = collider.kind === 'box' ? collider.halfExtents[1] : collider.halfHeight;
    const dy = Math.max(y - halfY - top, bottom - y - halfY, 0);
    const horizontal = collider.kind === 'box'
      ? Math.hypot(Math.max(Math.abs(p.x - x) - collider.halfExtents[0], 0),
        Math.max(Math.abs(p.z - z) - collider.halfExtents[2], 0))
      : Math.max(0, Math.hypot(p.x - x, p.z - z) - collider.radius);
    assert(Math.hypot(horizontal, dy) >= radius - 0.04, `${label}: capsule penetrated ${collider.name}`);
  }
}
