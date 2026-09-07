import {
  AnimationMixer, Box3, Group, Material, Mesh, MeshStandardMaterial, PropertyBinding, ShaderChunk, Skeleton, SkinnedMesh, Texture, Vector3,
  type AnimationAction, type AnimationClip, type Bone, type ColorRepresentation,
} from 'three';
import { GLTFLoader, type GLTF } from 'three/addons/loaders/GLTFLoader.js';
import { clone as cloneSkeleton } from 'three/addons/utils/SkeletonUtils.js';
import { disposeMeshResources, ownMaterialTextures } from './world-assets';

export const CHARACTER_CLIPS = ['idle', 'walk', 'run', 'talk'] as const;
export type CharacterClip = typeof CHARACTER_CLIPS[number];
export type CharacterKind = 'player' | 'npc';
export interface CharacterOptions { id: string; kind: CharacterKind; tint?: ColorRepresentation }
export interface CharacterMotion { speed: number; talking?: boolean }
export interface CharacterAssetMetrics {
  source: string;
  bytes: number;
  triangles: number;
  meshes: number;
  bones: number;
  materials: string[];
  textures: Array<{ name: string; width: number; height: number }>;
  bounds: { min: number[]; max: number[] };
  clips: Array<{ name: string; duration: number; tracks: number }>;
}
interface CharacterAsset {
  root: Group;
  clips: Record<CharacterClip, AnimationClip>;
  metrics: CharacterAssetMetrics;
}

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
function validateAsset(gltf: GLTF, kind: CharacterKind, source: string, bytes: number): CharacterAsset {
  const root = gltf.scene;
  root.updateMatrixWorld(true);
  const materials = materialsIn(root);
  const boneIDs = new Set<string>();
  const boneRoots = new Set<string>();
  let triangles = 0, meshes = 0;
  root.traverse((object) => {
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
    triangles += (object.geometry.index?.count ?? position.count) / 3;
    object.castShadow = true;
    object.receiveShadow = true;
    // Eight characters are cheaper to submit than to reskin every vertex for a tight
    // animated culling bound. This also prevents a moving hand being clipped offscreen.
    object.frustumCulled = false;
    object.computeBoundingBox();
  });
  if (!meshes || boneRoots.size !== 1) throw new Error(`${source}: expected one complete humanoid skeleton.`);
  const triangleLimit = kind === 'player' ? 18000 : 6000;
  if (triangles > triangleLimit) throw new Error(`${source}: ${triangles} triangles exceed the ${triangleLimit} character budget.`);
  const names = [...materials].map((material) => material.name).sort();
  if (materials.size !== 2 || names.join(',') !== 'MAT_body,MAT_cloth' || [...materials].some((material) => !(material instanceof MeshStandardMaterial))) {
    throw new Error(`${source}: expected exactly MAT_body and MAT_cloth sharing the character atlas.`);
  }
  const atlases = [...materials].map((material) => (material as MeshStandardMaterial).map);
  if (!atlases[0] || atlases.some((atlas) => !atlas || atlas.source !== atlases[0]!.source)) {
    throw new Error(`${source}: body and clothing must use the same loaded color atlas.`);
  }
  const bounds = new Box3().setFromObject(root, true);
  const size = bounds.getSize(new Vector3());
  if (bounds.isEmpty() || ![...bounds.min.toArray(), ...bounds.max.toArray()].every(Number.isFinite)
    || Math.abs(size.y - 1.8) > 0.12 || Math.abs(bounds.min.y) > 0.08 || size.x > 2 || size.z > 1.2) {
    throw new Error(`${source}: expected a feet-origin 1.8 m humanoid; bounds ${JSON.stringify({ min: bounds.min.toArray(), max: bounds.max.toArray() })}.`);
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
  const textures = new Set([...materials].flatMap((material) => Object.values(material).filter((value): value is Texture => value instanceof Texture)));
  return {
    root, clips,
    metrics: {
      source, bytes, triangles, meshes, bones: boneIDs.size, materials: names,
      textures: [...textures].map((texture) => {
        const image = texture.image as { width?: number; height?: number } | undefined;
        return { name: texture.name, width: image?.width ?? 0, height: image?.height ?? 0 };
      }),
      bounds: { min: bounds.min.toArray(), max: bounds.max.toArray() },
      clips: gltf.animations.map((clip) => ({ name: clip.name, duration: clip.duration, tracks: clip.tracks.length })),
    },
  };
}

/** A feet-origin +Z-facing clone; callers own its position and heading. */
export class CharacterInstance {
  readonly root = new Group();
  private readonly rig: Group;
  private readonly mixer: AnimationMixer;
  private readonly actions: Record<CharacterClip, AnimationAction>;
  private readonly tintMaterials = new Set<Material>();
  private readonly poseBones: Bone[];
  private active: CharacterClip = 'idle';
  private speed = 0;
  private playbackRate = 1;
  private disposed = false;

  constructor(private readonly asset: CharacterAsset, readonly options: CharacterOptions, private readonly onDispose: () => void) {
    this.root.name = options.id;
    this.rig = cloneSkeleton(asset.root) as Group;
    const poseNames = new Set(['hips', 'head', 'upper_arm.R', 'forearm.R', 'thigh.L', 'thigh.R']);
    this.poseBones = [...new Set([...skeletonsIn(this.rig)].flatMap((skeleton) => skeleton.bones))]
      .filter((bone) => poseNames.has(bone.userData.name ?? bone.name));
    if (options.tint !== undefined) {
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
            this.tintMaterials.add(variant);
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
      ? Math.max(0.55, Math.min(1.6, this.speed / (next === 'walk' ? 3.4 : 6))) : 1;
    this.actions[next].setEffectiveTimeScale(this.playbackRate);
    this.mixer.update(dt);
  }

  get diagnostics() {
    return { id: this.options.id, kind: this.options.kind, animation: this.active, speed: this.speed, playbackRate: this.playbackRate,
      time: this.mixer.time, triangles: this.asset.metrics.triangles, bones: this.asset.metrics.bones,
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
    for (const material of this.tintMaterials) material.dispose();
    this.root.removeFromParent();
    this.onDispose();
  }
}

/** Load once, then share source geometry/maps across independent skeletons and mixers. */
export class CharacterLibrary {
  private readonly loading = new AbortController();
  private readonly assets = new Map<CharacterKind, CharacterAsset>();
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

  create(options: CharacterOptions) {
    const asset = this.assets.get(options.kind);
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
