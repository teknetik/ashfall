import {
  AnimationMixer, Box3, Group, Material, Mesh, MeshStandardMaterial, PropertyBinding, ShaderChunk, Skeleton, SkinnedMesh, Texture, Vector3,
  type AnimationAction, type AnimationClip, type Bone, type ColorRepresentation,
} from 'three';
import { GLTFLoader, type GLTF } from 'three/addons/loaders/GLTFLoader.js';
import { clone as cloneSkeleton } from 'three/addons/utils/SkeletonUtils.js';
import { disposeMeshResources, ownMaterialTextures } from './world-assets';

export const CHARACTER_CLIPS = ['idle', 'walk', 'run', 'talk'] as const;
export type CharacterClip = typeof CHARACTER_CLIPS[number];
type LocomotionClip = Extract<CharacterClip, 'walk' | 'run'>;
interface LocomotionCalibration {
  nominalMetersPerSecond: number;
  calibrationSource: 'clip-metadata' | 'mpfb-default' | 'legacy-default';
}
export type CharacterKind = 'player' | 'npc';
export type CharacterVariant = 'default' | 'guard';
type ImportedVariant = Exclude<CharacterVariant, 'default'>;
export interface CharacterOptions { id: string; kind: CharacterKind; variant?: CharacterVariant; tint?: ColorRepresentation }
export interface CharacterMotion { speed: number; talking?: boolean }
export interface CharacterAssetMetrics {
  source: string;
  bytes: number;
  triangles: number;
  visibleTriangles: number;
  shadowProxyTriangles: number;
  meshes: number;
  bones: number;
  materials: string[];
  textures: Array<{ name: string; width: number; height: number }>;
  bounds: { min: number[]; max: number[] };
  clips: Array<{ name: string; duration: number; tracks: number } & Partial<LocomotionCalibration>>;
}
interface CharacterAsset {
  root: Group;
  clips: Record<CharacterClip, AnimationClip>;
  locomotion: Record<LocomotionClip, LocomotionCalibration>;
  metrics: CharacterAssetMetrics;
}

// Player sourcing can change without weakening the small, shared-atlas NPC
// contract. These are import ceilings; the live scene still has its own budget.
const CHARACTER_LIMITS = {
  player: { triangles: 40000, bones: 53, materials: 8 },
  npc: { triangles: 6000, bones: 19, materials: 2 },
  guard: { triangles: 6000, bones: 24, materials: 1 },
} as const;
const POSE_BONE_NAMES = new Set([
  'hips', 'head', 'upper_arm.R', 'forearm.R', 'thigh.L', 'thigh.R',
  'pelvis', 'upperarm_r', 'lowerarm_r', 'thigh_l', 'thigh_r',
  'Hips', 'Head', 'RightArm', 'RightForeArm', 'LeftUpLeg', 'RightUpLeg',
]);
const SHADOW_PROXY_NAME = 'COLONIST_shadow_proxy';

// Recolor only the clothing material. The atlas remains shared with skin and gear.
// Its olive swatch has ~0.085 linear luminance at the bright end; normalizing that
// weave into a 0..1 detail multiplier preserves dirt without darkening the tint
// twice. The square root retains midtones, and the cap never exceeds tint albedo.
const CLOTH_MAP_FRAGMENT = ShaderChunk.map_fragment.replace('diffuseColor *= sampledDiffuseColor;', `
  float clothLuminance = dot( sampledDiffuseColor.rgb, vec3( 0.2126, 0.7152, 0.0722 ) );
  sampledDiffuseColor.rgb = vec3( sqrt( clamp( clothLuminance / 0.085, 0.0, 1.0 ) ) );
  diffuseColor *= sampledDiffuseColor;
`);

function recolorClothing(material: MeshStandardMaterial, tint: ColorRepresentation) {
  material.color.set(tint);
  material.onBeforeCompile = (shader) => {
    shader.fragmentShader = shader.fragmentShader.replace('#include <map_fragment>', CLOTH_MAP_FRAGMENT);
  };
  // All jacket variants share one program; the standard diffuse uniform supplies
  // each color. Keep the untouched player atlas on Three's stock map program.
  material.customProgramCacheKey = () => 'athen-cloth-luminance-v1';
}

function materialsIn(root: Group) {
  const materials = new Set<Material>();
  root.traverse((object) => {
    if (object instanceof Mesh) {
      for (const material of Array.isArray(object.material) ? object.material : [object.material]) materials.add(material);
    }
  });
  return materials;
}

function skeletonsIn(root: Group) {
  const skeletons = new Set<Skeleton>();
  root.traverse((object) => { if (object instanceof SkinnedMesh) skeletons.add(object.skeleton); });
  return skeletons;
}

function releaseAsset(root: Group) {
  for (const skeleton of skeletonsIn(root)) skeleton.dispose();
  disposeMeshResources(root);
  root.removeFromParent();
}

/** Validate the exported rig before any player or NPC becomes visible. */
function validateAsset(gltf: GLTF, kind: CharacterKind | ImportedVariant, source: string, bytes: number): CharacterAsset {
  const root = gltf.scene;
  root.updateMatrixWorld(true);
  const materials = materialsIn(root);
  const boneIDs = new Set<string>();
  const boneNames = new Set<string>();
  const boneRoots = new Set<string>();
  const visualMeshes: SkinnedMesh[] = [], shadowProxies: SkinnedMesh[] = [];
  let triangles = 0, shadowProxyTriangles = 0, meshes = 0;
  root.traverse((object) => {
    const isProxy = object.userData.shadowProxy === true;
    if (isProxy || object.name === SHADOW_PROXY_NAME) {
      if (kind !== 'player' || !isProxy || object.name !== SHADOW_PROXY_NAME || !(object instanceof SkinnedMesh)
        || Array.isArray(object.material)) {
        throw new Error(`${source}: shadow proxy must be one player SkinnedMesh named ${SHADOW_PROXY_NAME}, tagged shadowProxy:true, with one material.`);
      }
      shadowProxies.push(object);
    }
    if (!(object instanceof Mesh)) return;
    if (!(object instanceof SkinnedMesh)) throw new Error(`${source}: ${object.name} is not skinned.`);
    meshes++;
    const { position, skinIndex, skinWeight } = object.geometry.attributes;
    if (!position?.count || !skinIndex || !skinWeight || skinIndex.count !== position.count
      || skinWeight.count !== position.count || skinIndex.itemSize !== 4 || skinWeight.itemSize !== 4) {
      throw new Error(`${source}: ${object.name} has missing or mismatched skin attributes.`);
    }
    if (!object.skeleton.bones.length) throw new Error(`${source}: ${object.name} has no skeleton bones.`);
    for (const bone of object.skeleton.bones) {
      boneIDs.add(bone.uuid);
      boneNames.add(bone.userData.name ?? bone.name);
      if (!bone.parent || !('isBone' in bone.parent)) boneRoots.add(bone.uuid);
      if (!root.getObjectById(bone.id)) throw new Error(`${source}: skeleton bone ${bone.name} is outside its character root.`);
    }
    for (let vertex = 0; vertex < position.count; vertex++) {
      let sum = 0;
      for (let component = 0; component < 4; component++) {
        const weight = skinWeight.getComponent(vertex, component);
        const index = skinIndex.getComponent(vertex, component);
        if (!Number.isFinite(weight) || weight < 0 || (weight > 0 && (!Number.isInteger(index)
          || index < 0 || index >= object.skeleton.bones.length))) {
          throw new Error(`${source}: ${object.name} has invalid skin weights or bone indices.`);
        }
        sum += weight;
      }
      if (Math.abs(sum - 1) > 0.015) throw new Error(`${source}: ${object.name} skin weights must sum to one.`);
    }
    const meshTriangles = (object.geometry.index?.count ?? position.count) / 3;
    triangles += meshTriangles;
    if (isProxy) shadowProxyTriangles += meshTriangles;
    else visualMeshes.push(object);
    object.castShadow = true;
    object.receiveShadow = true;
    // Eight characters are cheaper to submit than to reskin every vertex for a tight
    // animated culling bound. This also prevents a moving hand being clipped offscreen.
    object.frustumCulled = false;
    object.computeBoundingBox();
  });
  if (!meshes || boneRoots.size !== 1) throw new Error(`${source}: expected one complete humanoid skeleton.`);
  if (shadowProxies.length > 1 || (shadowProxies.length > 0 && (shadowProxyTriangles <= 0 || shadowProxyTriangles > 3000))) {
    throw new Error(`${source}: expected at most one shadow proxy with at most 3000 triangles.`);
  }
  if (!visualMeshes.length) throw new Error(`${source}: character has no visible skinned meshes.`);
  if (shadowProxies.length) {
    const visualBones = new Set(visualMeshes.flatMap((mesh) => mesh.skeleton.bones));
    const proxyBones = shadowProxies[0].skeleton.bones;
    if (proxyBones.length !== visualBones.size || proxyBones.some((bone) => !visualBones.has(bone))) {
      throw new Error(`${source}: shadow proxy must use the same complete rig as the visible player.`);
    }
  }
  const limits = CHARACTER_LIMITS[kind];
  if (triangles > limits.triangles) throw new Error(`${source}: ${triangles} triangles exceed the ${limits.triangles} character budget.`);
  if (boneIDs.size > limits.bones) throw new Error(`${source}: ${boneIDs.size} bones exceed the ${limits.bones} character budget.`);
  const names = [...materials].map((material) => material.name).sort();
  if (!materials.size || materials.size > limits.materials || names.some((name) => !name.trim())
    || [...materials].some((material) => !(material instanceof MeshStandardMaterial))) {
    throw new Error(`${source}: expected 1–${limits.materials} named standard PBR materials.`);
  }
  if (kind === 'npc') {
    if (materials.size !== 2 || names.join(',') !== 'MAT_body,MAT_cloth') {
      throw new Error(`${source}: expected exactly MAT_body and MAT_cloth sharing the character atlas.`);
    }
    const atlases = [...materials].map((material) => (material as MeshStandardMaterial).map);
    if (!atlases[0] || atlases.some((atlas) => !atlas || atlas.source !== atlases[0]!.source)) {
      throw new Error(`${source}: body and clothing must use the same loaded color atlas.`);
    }
  } else if ([...materials].some((material) => material.transparent || !material.depthWrite
    || !Number.isFinite(material.alphaTest) || material.alphaTest < 0 || material.alphaTest > 1)) {
    throw new Error(`${source}: character materials must use opaque or alpha-masked rendering with depth writes.`);
  }
  // GLTFLoader retains independent base-color, normal and packed roughness maps,
  // including their color spaces and UV channels. Preserve its MASK alphaTest;
  // Three's shadow pass uses the same map/cutoff for skinned hair and eyelashes.
  // An invisible proxy must not make a wrongly scaled visible player pass QA.
  const bounds = new Box3();
  for (const mesh of visualMeshes) bounds.union(mesh.boundingBox!.clone().applyMatrix4(mesh.matrixWorld));
  const invalidBounds = [bounds, ...(shadowProxies.length ? [new Box3().setFromObject(root, true)] : [])].find((candidate) => {
    const size = candidate.getSize(new Vector3());
    return candidate.isEmpty() || ![...candidate.min.toArray(), ...candidate.max.toArray()].every(Number.isFinite)
      || Math.abs(size.y - 1.8) > 0.12 || Math.abs(candidate.min.y) > 0.08 || size.x > 2 || size.z > 1.2;
  });
  if (invalidBounds) {
    throw new Error(`${source}: expected a feet-origin 1.8 m humanoid; bounds ${JSON.stringify({ min: invalidBounds.min.toArray(), max: invalidBounds.max.toArray() })}.`);
  }
  const clips = {} as Record<CharacterClip, AnimationClip>;
  if (gltf.animations.length !== CHARACTER_CLIPS.length) throw new Error(`${source}: requires exactly idle, walk, run and talk clips.`);
  for (const clip of gltf.animations) {
    if (!CHARACTER_CLIPS.includes(clip.name as CharacterClip) || clips[clip.name as CharacterClip]
      || !Number.isFinite(clip.duration) || clip.duration <= 0 || !clip.tracks.length) {
      throw new Error(`${source}: invalid or duplicate animation ${clip.name}.`);
    }
    for (const track of clip.tracks) {
      const binding = PropertyBinding.parseTrackName(track.name);
      const target = PropertyBinding.findNode(root, binding.nodeName);
      if (!target || !['position', 'quaternion', 'scale'].includes(binding.propertyName)
        || !track.times.length || ![...track.times, ...track.values].every(Number.isFinite)
        || track.values.length !== track.times.length * (binding.propertyName === 'quaternion' ? 4 : 3)
        || track.times.some((time, index) => time < 0 || (index > 0 && time <= track.times[index - 1]))) {
        throw new Error(`${source}: ${clip.name} has an invalid animation target or keyframe: ${track.name}.`);
      }
    }
    clips[clip.name as CharacterClip] = clip;
  }
  // Three's GLTFLoader copies animation extras to clip.userData. Keep authored
  // stride calibration when present, with a rig-specific fallback for exporters
  // that omit action extras. Old NPCs retain their original cadence.
  const mpfbPlayer = kind === 'player' && ['pelvis', 'upperarm_r', 'thigh_l', 'thigh_r'].every((name) => boneNames.has(name));
  const defaults = mpfbPlayer ? { walk: 1.50, run: 3.6104 } : { walk: 3.4, run: 6 };
  const locomotion = {} as Record<LocomotionClip, LocomotionCalibration>;
  for (const name of ['walk', 'run'] as const) {
    const authoredSpeed = clips[name].userData.nominalMetersPerSecond;
    if (authoredSpeed !== undefined && (typeof authoredSpeed !== 'number' || !Number.isFinite(authoredSpeed) || authoredSpeed <= 0)) {
      throw new Error(`${source}: ${name} nominalMetersPerSecond must be finite and positive.`);
    }
    locomotion[name] = {
      nominalMetersPerSecond: authoredSpeed ?? defaults[name],
      calibrationSource: authoredSpeed !== undefined ? 'clip-metadata' : mpfbPlayer ? 'mpfb-default' : 'legacy-default',
    };
  }
  const textures = new Set([...materials].flatMap((material) => Object.values(material).filter((value): value is Texture => value instanceof Texture)));
  return {
    root, clips, locomotion,
    metrics: {
      source, bytes, triangles, visibleTriangles: triangles - shadowProxyTriangles, shadowProxyTriangles,
      meshes, bones: boneIDs.size, materials: names,
      textures: [...textures].map((texture) => {
        const image = texture.image as { width?: number; height?: number } | undefined;
        return { name: texture.name, width: image?.width ?? 0, height: image?.height ?? 0 };
      }),
      bounds: { min: bounds.min.toArray(), max: bounds.max.toArray() },
      clips: gltf.animations.map((clip) => ({ name: clip.name, duration: clip.duration, tracks: clip.tracks.length,
        ...(clip.name === 'walk' || clip.name === 'run' ? locomotion[clip.name] : {}) })),
    },
  };
}

/** A feet-origin +Z-facing clone; callers own its position and heading. */
export class CharacterInstance {
  readonly root = new Group();
  private readonly rig: Group;
  private readonly mixer: AnimationMixer;
  private readonly actions: Record<CharacterClip, AnimationAction>;
  private readonly instanceMaterials = new Set<Material>();
  private readonly poseBones: Bone[];
  private active: CharacterClip = 'idle';
  private speed = 0;
  private playbackRate = 1;
  private disposed = false;

  constructor(private readonly asset: CharacterAsset, readonly options: CharacterOptions, private readonly onDispose: () => void) {
    this.root.name = options.id;
    this.rig = cloneSkeleton(asset.root) as Group;
    this.poseBones = [...new Set([...skeletonsIn(this.rig)].flatMap((skeleton) => skeleton.bones))]
      .filter((bone) => POSE_BONE_NAMES.has(bone.userData.name ?? bone.name));
    if (asset.metrics.shadowProxyTriangles > 0) {
      this.rig.traverse((object) => {
        if (!(object instanceof SkinnedMesh)) return;
        const isProxy = object.userData.shadowProxy === true;
        object.castShadow = isProxy;
        object.receiveShadow = !isProxy;
        if (!isProxy) return;
        const material = (object.material as MeshStandardMaterial).clone();
        material.colorWrite = false;
        material.depthWrite = false;
        material.depthTest = true;
        material.visible = true;
        material.transparent = false;
        material.opacity = 1;
        material.alphaTest = 0;
        material.alphaMap = null;
        // Keep the proxy visible to traversal and uncullable with the animated
        // player. Three's separate shadow depth material still writes depth.
        // The tiny colorless main submission is included in renderer.info.
        object.visible = true;
        object.frustumCulled = false;
        object.material = material;
        this.instanceMaterials.add(material);
      });
    }
    if (options.kind === 'npc' && (!options.variant || options.variant === 'default') && options.tint !== undefined) {
      const variants = new Map<Material, Material>();
      this.rig.traverse((object) => {
        if (!(object instanceof Mesh)) return;
        const tint = (material: Material) => {
          if (material.name !== 'MAT_cloth') return material;
          let variant = variants.get(material);
          if (!variant) {
            variant = material.clone();
            if (variant instanceof MeshStandardMaterial) recolorClothing(variant, options.tint!);
            variants.set(material, variant);
            this.instanceMaterials.add(variant);
          }
          return variant;
        };
        object.material = Array.isArray(object.material) ? object.material.map(tint) : tint(object.material);
      });
    }
    this.root.add(this.rig);
    this.mixer = new AnimationMixer(this.rig);
    this.actions = Object.fromEntries(CHARACTER_CLIPS.map((name) => [name, this.mixer.clipAction(asset.clips[name])])) as Record<CharacterClip, AnimationAction>;
    this.actions.idle.play();
    this.mixer.update(0);
  }

  update(dt: number, motion: CharacterMotion) {
    if (this.disposed) return;
    if (!Number.isFinite(dt) || dt < 0 || !Number.isFinite(motion.speed)) throw new Error('Character animation requires finite delta time and speed.');
    this.speed = Math.max(0, motion.speed);
    const next: CharacterClip = this.speed < 0.12 ? (motion.talking ? 'talk' : 'idle')
      : this.speed > (this.active === 'run' ? 4.1 : 4.5) ? 'run' : 'walk';
    if (next !== this.active) {
      this.actions[this.active].fadeOut(0.16);
      this.actions[next].reset().setEffectiveWeight(1).fadeIn(0.16).play();
      this.active = next;
    }
    this.playbackRate = next === 'walk' || next === 'run'
      // The MPFB 1.5 m/s walk needs 2.267x at the controller's 3.4 m/s. A 1.6x
      // player cap would preserve foot sliding even with correct stride metadata.
      ? Math.max(0.55, Math.min(this.options.kind === 'player' ? 3 : 1.6,
        this.speed / this.asset.locomotion[next].nominalMetersPerSecond)) : 1;
    this.actions[next].setEffectiveTimeScale(this.playbackRate);
    this.mixer.update(dt);
  }

  get diagnostics() {
    return { id: this.options.id, kind: this.options.kind, variant: this.options.variant ?? 'default', source: this.asset.metrics.source,
      staticPose: this.asset.clips[this.active].userData.staticPose === true,
      animation: this.active, speed: this.speed, playbackRate: this.playbackRate,
      nominalMetersPerSecond: this.active === 'walk' || this.active === 'run' ? this.asset.locomotion[this.active].nominalMetersPerSecond : 0,
      time: this.mixer.time, triangles: this.asset.metrics.triangles, bones: this.asset.metrics.bones,
      visibleTriangles: this.asset.metrics.visibleTriangles, shadowProxyTriangles: this.asset.metrics.shadowProxyTriangles,
      poseSpace: 'bone-local',
      pose: this.poseBones.map((bone) => ({ name: bone.userData.name ?? bone.name,
        position: bone.position.toArray(), quaternion: bone.quaternion.toArray() })) };
  }

  dispose() {
    if (this.disposed) return;
    this.disposed = true;
    this.mixer.stopAllAction();
    this.mixer.uncacheRoot(this.rig);
    for (const skeleton of skeletonsIn(this.rig)) skeleton.dispose();
    for (const material of this.instanceMaterials) material.dispose();
    this.root.removeFromParent();
    this.onDispose();
  }
}

/** Load once, then share source geometry/maps across independent skeletons and mixers. */
export class CharacterLibrary {
  private readonly loading = new AbortController();
  private readonly assets = new Map<CharacterKind | ImportedVariant, CharacterAsset>();
  private readonly importedPending = new Map<ImportedVariant, Promise<void>>();
  private readonly instances = new Set<CharacterInstance>();
  private pending: Promise<void> | null = null;
  private state: 'unloaded' | 'loading' | 'ready' | 'disposed' = 'unloaded';

  load() {
    if (this.state === 'disposed') return Promise.reject(new Error('The character library is disposed.'));
    if (this.pending) return this.pending;
    this.state = 'loading';
    this.pending = Promise.all((['player', 'npc'] as const).map(async (kind) => {
      const source = `${import.meta.env.BASE_URL}assets/${kind === 'player' ? 'player' : 'npcs'}.glb`;
      const response = await fetch(source, { signal: this.loading.signal });
      if (!response.ok) throw new Error(`Character asset load failed (${response.status}): ${source}.`);
      const bytes = await response.arrayBuffer();
      const gltf = await new GLTFLoader().parseAsync(bytes, new URL('.', new URL(source, location.href)).href);
      ownMaterialTextures(materialsIn(gltf.scene));
      try {
        this.loading.signal.throwIfAborted();
        const asset = validateAsset(gltf, kind, source, bytes.byteLength);
        this.assets.set(kind, asset);
      } catch (error) {
        releaseAsset(gltf.scene);
        throw error;
      }
    })).then(() => {
      this.loading.signal.throwIfAborted();
      this.state = 'ready';
    }).catch((error: unknown) => {
      this.dispose();
      throw error;
    });
    return this.pending;
  }

  loadGuard() { return this.loadImported('guard'); }

  /** Each supplied NPC variant shares its own geometry/maps and retains an independent rig per actor. */
  private loadImported(variant: ImportedVariant) {
    if (this.state === 'disposed') return Promise.reject(new Error('The character library is disposed.'));
    if (this.assets.has(variant)) return Promise.resolve();
    const pending = this.importedPending.get(variant);
    if (pending) return pending;
    const loading = (async () => {
      const source = `${import.meta.env.BASE_URL}assets/ward-guard.glb`;
      const response = await fetch(source, { signal: this.loading.signal });
      if (!response.ok) throw new Error(`Character asset load failed (${response.status}): ${source}.`);
      const bytes = await response.arrayBuffer();
      const gltf = await new GLTFLoader().parseAsync(bytes, new URL('.', new URL(source, location.href)).href);
      ownMaterialTextures(materialsIn(gltf.scene));
      try {
        this.loading.signal.throwIfAborted();
        this.assets.set(variant, validateAsset(gltf, variant, source, bytes.byteLength));
      } catch (error) {
        releaseAsset(gltf.scene);
        throw error;
      }
    })().catch((error: unknown) => {
      this.importedPending.delete(variant);
      throw error;
    });
    this.importedPending.set(variant, loading);
    return loading;
  }

  create(options: CharacterOptions) {
    const assetKey = options.kind === 'npc' && options.variant && options.variant !== 'default' ? options.variant : options.kind;
    const asset = this.assets.get(assetKey);
    if (this.state !== 'ready' || !asset) throw new Error('Character assets must finish loading before creating actors.');
    if (!options.id || [...this.instances].some((instance) => instance.options.id === options.id)) throw new Error(`Character instance id must be unique: ${options.id}.`);
    const instance = new CharacterInstance(asset, options, () => this.instances.delete(instance));
    this.instances.add(instance);
    return instance;
  }

  get diagnostics() {
    return { state: this.state, instances: this.instances.size,
      assets: Object.fromEntries([...this.assets].map(([kind, asset]) => [kind, asset.metrics])) };
  }

  dispose() {
    if (this.state === 'disposed') return;
    this.state = 'disposed';
    this.loading.abort();
    for (const instance of [...this.instances]) instance.dispose();
    for (const asset of this.assets.values()) releaseAsset(asset.root);
    this.assets.clear();
  }
}
