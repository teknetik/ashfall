import {
  Box3, BufferGeometry, DoubleSide, Group, Material, Matrix4, Mesh, Quaternion, Texture, Vector3,
  type BufferAttribute, type InterleavedBufferAttribute, type Object3D,
} from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import type { ColliderDef } from './layout';

export const WORLD_LANDMARKS = [
  'hill_tree', 'west_gate', 'shop_rows', 'vanguard_hall', 'grid_kiosk', 'whompah', 'props', 'boundary',
] as const;
export type WorldLandmark = typeof WORLD_LANDMARKS[number];

export interface WorldAssetInfo {
  loaded: boolean;
  manifestSource: string;
  source: string | null;
  landmarks: WorldLandmark[];
  greyboxLandmarks: WorldLandmark[];
  bytes: number;
  sourceMeshes: number;
  batches: number;
  triangles: number;
  materialNames: string[];
  textureCount: number;
  textures: Array<{ name: string; width: number; height: number }>;
  colliderCount: number;
  bounds: { min: number[]; max: number[] } | null;
  animations: string[];
}

export function emptyWorldAssetInfo(base: string): WorldAssetInfo {
  return {
    loaded: false, manifestSource: `${base}assets/world-manifest.json`, source: null,
    landmarks: [], greyboxLandmarks: [...WORLD_LANDMARKS], bytes: 0, sourceMeshes: 0,
    batches: 0, triangles: 0, materialNames: [], textureCount: 0, textures: [],
    colliderCount: 0, bounds: null, animations: [],
  };
}

function landmarkList(value: unknown, label: string): WorldLandmark[] {
  if (!Array.isArray(value) || value.some((item) => !WORLD_LANDMARKS.includes(item))) {
    throw new Error(`${label} must list known authored world landmarks.`);
  }
  if (new Set(value).size !== value.length) throw new Error(`${label} contains duplicate landmarks.`);
  return value as WorldLandmark[];
}

function landmarkOf(mesh: Mesh): WorldLandmark {
  for (let node: Mesh['parent'] = mesh; node; node = node.parent) {
    if (node.userData.landmark !== undefined) {
      const value = node.userData.landmark;
      if (!WORLD_LANDMARKS.includes(value)) throw new Error(`${mesh.name} has unknown landmark ${String(value)}.`);
      return value as WorldLandmark;
    }
  }
  throw new Error(`${mesh.name || 'Unnamed world mesh'} is missing its landmark extra.`);
}

function materialTextures(material: Material): Texture[] {
  return Object.values(material).filter((value): value is Texture => value instanceof Texture);
}

/** Material.dispose does not dispose maps. Release shared GLB maps after their last owning material. */
export function ownMaterialTextures(materials: Iterable<Material>) {
  const references = new Map<Texture, number>();
  const bitmapOwners = new Map<ImageBitmap, number>();
  for (const material of new Set(materials)) {
    const textures = [...new Set(materialTextures(material))];
    for (const texture of textures) {
      const image = texture.source.data;
      if (!references.has(texture) && typeof ImageBitmap !== 'undefined' && image instanceof ImageBitmap) {
        bitmapOwners.set(image, (bitmapOwners.get(image) ?? 0) + 1);
      }
      references.set(texture, (references.get(texture) ?? 0) + 1);
    }
    const release = () => {
      material.removeEventListener('dispose', release);
      for (const texture of textures) {
        const remaining = (references.get(texture) ?? 1) - 1;
        references.set(texture, remaining);
        if (remaining !== 0) continue;
        texture.dispose();
        // GLTFLoader uses ImageBitmap when available; Texture.dispose does not close it.
        // Multiple map variants can also share one bitmap, despite being distinct Textures.
        const image = texture.source.data;
        if (typeof ImageBitmap !== 'undefined' && image instanceof ImageBitmap) {
          const owners = (bitmapOwners.get(image) ?? 1) - 1;
          bitmapOwners.set(image, owners);
          if (owners === 0) image.close();
        }
      }
    };
    material.addEventListener('dispose', release);
  }
}

/** Release each shared mesh resource once, including materials not attached to a mesh yet. */
export function disposeMeshResources(root: Object3D, additionalMaterials: Iterable<Material> = []) {
  const geometries = new Set<BufferGeometry>();
  const materials = new Set(additionalMaterials);
  root.traverse((object) => {
    if (!(object instanceof Mesh)) return;
    geometries.add(object.geometry);
    for (const material of Array.isArray(object.material) ? object.material : [object.material]) materials.add(material);
  });
  for (const geometry of geometries) geometry.dispose();
  for (const material of materials) material.dispose();
}

/** Keep local box bounds plus world rotation: a world AABB would fatten rotated beams. */
export function colliderFromMesh(mesh: Mesh): ColliderDef {
  const { colliderKind: kind } = mesh.userData;
  if (kind !== 'box' && kind !== 'cylinder') throw new Error(`${mesh.name} requires colliderKind box or cylinder.`);
  const position = new Vector3(), rotation = new Quaternion(), scale = new Vector3();
  mesh.matrixWorld.decompose(position, rotation, scale);
  if (![...position.toArray(), ...rotation.toArray(), ...scale.toArray()].every(Number.isFinite)
    || scale.toArray().some((n) => n <= 0)) throw new Error(`${mesh.name} has invalid or unapplied negative scale.`);
  const recomposed = new Matrix4().compose(position, rotation, scale);
  if (recomposed.elements.some((n, index) => Math.abs(n - mesh.matrixWorld.elements[index]) > 0.0001)) {
    throw new Error(`${mesh.name} has a sheared collider transform; apply transforms in Blender.`);
  }
  mesh.geometry.computeBoundingBox();
  const bounds = mesh.geometry.boundingBox;
  if (!bounds || bounds.isEmpty()) throw new Error(`${mesh.name} has empty collision geometry.`);
  const size = bounds.getSize(new Vector3()).multiply(scale);
  const center = bounds.getCenter(new Vector3()).applyMatrix4(mesh.matrixWorld);
  if (![...size.toArray(), ...center.toArray()].every(Number.isFinite) || size.toArray().some((n) => n <= 0)) {
    throw new Error(`${mesh.name} has invalid collision dimensions.`);
  }
  if (kind === 'box') return {
    name: mesh.name, kind, position: center.toArray(), halfExtents: size.multiplyScalar(0.5).toArray(),
    rotation: rotation.toArray(),
  };
  // Cylinders must stand along world Y. The GLB may carry Blender's Z-to-Y root rotation,
  // so final world bounds determine height/radius instead of assuming the local cylinder axis.
  const worldSize = new Box3().setFromObject(mesh, true).getSize(new Vector3());
  const radius = worldSize.x / 2;
  const halfHeight = worldSize.y / 2;
  if (Math.abs(worldSize.x - worldSize.z) > Math.max(0.04, radius * 0.04)) {
    throw new Error(`${mesh.name} must export an upright circular cylinder with applied scale.`);
  }
  // Optional dimensions are validation hints in final metre units, after scale is applied.
  for (const [key, measured] of [['colliderRadius', radius], ['colliderHalfHeight', halfHeight]] as const) {
    const declared = mesh.userData[key];
    if (declared !== undefined && (typeof declared !== 'number' || !Number.isFinite(declared)
      || declared <= 0 || Math.abs(declared - measured) > Math.max(0.04, measured * 0.04))) {
      throw new Error(`${mesh.name} ${key} does not match its exported world dimensions.`);
    }
  }
  return { name: mesh.name, kind, position: center.toArray(), radius, halfHeight };
}

interface WorldImport {
  root: Group;
  colliders: ColliderDef[];
  colliderLandmarks: Map<ColliderDef, WorldLandmark>;
  info: WorldAssetInfo;
}

/** A missing manifest means the earlier greybox milestone; a malformed published asset is an error. */
export async function loadWorldAsset(base: string, signal?: AbortSignal): Promise<WorldImport | null> {
  signal?.throwIfAborted();
  const info = emptyWorldAssetInfo(base);
  const manifestResponse = await fetch(info.manifestSource, { cache: 'no-cache', signal });
  if (manifestResponse.status === 404) return null;
  if (!manifestResponse.ok) throw new Error(`World manifest load failed (${manifestResponse.status}).`);
  // Vite/static history fallback may answer an absent optional file with index.html.
  if (manifestResponse.headers.get('content-type')?.includes('text/html')) return null;
  const manifest: unknown = await manifestResponse.json();
  if (!manifest || typeof manifest !== 'object' || Array.isArray(manifest)) throw new Error('World manifest must be an object.');
  const { source, landmarks } = manifest as { source?: unknown; landmarks?: unknown };
  const declared = landmarks === undefined ? undefined : landmarkList(landmarks, 'World manifest landmarks');
  if (declared?.length === 0 && source === undefined) return null;
  if (typeof source !== 'string' || !source || !/^[\w./-]+\.glb$/.test(source)
    || source.startsWith('/') || source.split('/').includes('..')) {
    throw new Error('World manifest source must be a relative GLB path inside assets.');
  }
  info.source = new URL(source, new URL(`${base}assets/`, location.href)).href;
  const response = await fetch(info.source, { cache: 'no-cache', signal });
  if (!response.ok) throw new Error(`Authored world load failed (${response.status}).`);
  const bytes = await response.arrayBuffer();
  info.bytes = bytes.byteLength;
  const gltf = await new GLTFLoader().parseAsync(bytes, new URL('.', info.source).href);
  const sourceGeometries = new Set<BufferGeometry>(), sourceMaterials = new Set<Material>();
  gltf.scene.traverse((object) => {
    if (!(object instanceof Mesh)) return;
    sourceGeometries.add(object.geometry);
    for (const material of Array.isArray(object.material) ? object.material : [object.material]) sourceMaterials.add(material);
  });
  ownMaterialTextures(sourceMaterials);
  const prepared: BufferGeometry[] = [];
  const root = new Group();
  root.name = 'AUTHORED_WORLD';
  try {
    // GLTF decoding itself cannot be cancelled. Adopt its resources before checking so
    // an abort during parse still releases decoded textures, bitmaps and geometry.
    signal?.throwIfAborted();
    if (gltf.animations.length) throw new Error('world.glb must contain static world geometry; animated characters load separately.');
    gltf.scene.updateMatrixWorld(true);
    const sceneLandmarks = gltf.scene.userData.authoredLandmarks === undefined
      ? undefined : landmarkList(gltf.scene.userData.authoredLandmarks, 'GLB authoredLandmarks');
    const observed = new Set<WorldLandmark>();
    const meshCounts = new Map<WorldLandmark, number>(), collisionCounts = new Map<WorldLandmark, number>();
    const colliders: ColliderDef[] = [], colliderLandmarks = new Map<ColliderDef, WorldLandmark>();
    const batches = new Map<string, { material: Material; geometries: BufferGeometry[]; names: string[]; castShadow: boolean }>();
    const usedMaterials = new Set<Material>(), colliderNames = new Set<string>();
    gltf.scene.traverse((object) => {
      if (!(object instanceof Mesh)) return;
      const landmark = landmarkOf(object);
      observed.add(landmark);
      if (object.name.startsWith('COL_')) {
        if (colliderNames.has(object.name)) throw new Error(`Duplicate collider name ${object.name}.`);
        const collider = colliderFromMesh(object);
        colliders.push(collider); colliderLandmarks.set(collider, landmark); colliderNames.add(object.name);
        collisionCounts.set(landmark, (collisionCounts.get(landmark) ?? 0) + 1);
        return;
      }
      if ('isSkinnedMesh' in object || 'isInstancedMesh' in object) {
        throw new Error(`${object.name} must export as static mesh nodes for world batching.`);
      }
      if (Array.isArray(object.material)) throw new Error(`${object.name} must use one material per exported mesh primitive.`);
      const material = object.material;
      if (!material.name.startsWith('MAT_')) throw new Error(`${object.name} requires an authored MAT_* material.`);
      // Blender's dithered foliage may arrive as BLEND. Cutout leaves need depth writes
      // and alpha-tested shadow silhouettes, without sorting every overlapping card.
      if (material.name === 'MAT_leaf') {
        material.alphaTest = 0.35;
        material.transparent = false;
        material.depthWrite = true;
        material.side = DoubleSide;
        material.needsUpdate = true;
      }
      if (object.matrixWorld.determinant() <= 0) throw new Error(`${object.name} has mirrored or singular transforms; apply scale before export.`);
      if (!object.geometry.attributes.position?.count) throw new Error(`${object.name} has no render vertices.`);
      const geometry = object.geometry.index ? object.geometry.toNonIndexed() : object.geometry.clone();
      prepared.push(geometry);
      geometry.applyMatrix4(object.matrixWorld);
      geometry.computeBoundingBox();
      if (!geometry.boundingBox || geometry.boundingBox.isEmpty()
        || ![...geometry.boundingBox.min.toArray(), ...geometry.boundingBox.max.toArray()].every(Number.isFinite)) {
        throw new Error(`${object.name} has invalid render bounds.`);
      }
      if (!geometry.attributes.normal) geometry.computeVertexNormals();
      geometry.clearGroups();
      const castShadow = material.name === 'MAT_leaf' || (object.userData.castShadow !== false && !material.transparent);
      // Preserve UV/color layouts instead of silently throwing away imported texture attributes.
      const attributes = Object.entries(geometry.attributes as Record<string, BufferAttribute | InterleavedBufferAttribute>)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([key, value]) => `${key}:${value.itemSize}:${value.normalized}:${value.array.constructor.name}`).join('|');
      const key = `${material.uuid}/${castShadow}/${attributes}`;
      const batch = batches.get(key) ?? { material, geometries: [] as BufferGeometry[], names: [] as string[], castShadow };
      batch.geometries.push(geometry); batch.names.push(object.name); batches.set(key, batch);
      usedMaterials.add(material);
      info.sourceMeshes += 1;
      info.triangles += geometry.attributes.position.count / 3;
      meshCounts.set(landmark, (meshCounts.get(landmark) ?? 0) + 1);
    });
    const complete = sceneLandmarks ?? declared ?? [...observed];
    if (complete.length === 0) throw new Error('world.glb contains no complete authored landmark.');
    for (const list of [declared, sceneLandmarks, [...observed]]) {
      if (list && (list.length !== complete.length || list.some((name) => !complete.includes(name)))) {
        throw new Error('Manifest, GLB authoredLandmarks and mesh landmark extras disagree.');
      }
    }
    for (const landmark of complete) {
      if (!meshCounts.get(landmark) || !collisionCounts.get(landmark)) {
        throw new Error(`${landmark} must include both render meshes and collision proxies before replacing its greybox.`);
      }
    }
    for (const batch of batches.values()) {
      const geometry = mergeGeometries(batch.geometries, false);
      if (!geometry) throw new Error(`Cannot batch authored material ${batch.material.name}.`);
      geometry.computeBoundingBox(); geometry.computeBoundingSphere();
      const mesh = new Mesh(geometry, batch.material);
      mesh.name = `AUTHORED_${batch.material.name}_${root.children.length}`;
      mesh.castShadow = batch.castShadow; mesh.receiveShadow = true;
      mesh.userData.sourceMeshes = batch.names;
      root.add(mesh);
    }
    const textures = new Set([...usedMaterials].flatMap(materialTextures));
    info.loaded = true;
    info.landmarks = [...complete];
    info.greyboxLandmarks = WORLD_LANDMARKS.filter((name) => !complete.includes(name));
    info.batches = root.children.length;
    info.materialNames = [...usedMaterials].map((material) => material.name).sort();
    info.textureCount = textures.size;
    info.textures = [...textures].map((texture) => {
      const image = texture.image as { width?: number; height?: number } | undefined;
      return { name: texture.name, width: Number(image?.width ?? 0), height: Number(image?.height ?? 0) };
    });
    info.colliderCount = colliders.length;
    const bounds = new Box3().setFromObject(root, true);
    info.bounds = { min: bounds.min.toArray(), max: bounds.max.toArray() };
    for (const material of sourceMaterials) if (!usedMaterials.has(material)) material.dispose();
    return { root, colliders, colliderLandmarks, info };
  } catch (error) {
    root.traverse((object) => { if (object instanceof Mesh) object.geometry.dispose(); });
    for (const material of sourceMaterials) material.dispose();
    throw error;
  } finally {
    for (const geometry of [...sourceGeometries, ...prepared]) geometry.dispose();
  }
}
