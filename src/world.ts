import {
  Box3, BoxGeometry, BufferGeometry, Color, CylinderGeometry, DirectionalLight, Fog,
  HemisphereLight, IcosahedronGeometry, Matrix4, Mesh, MeshStandardMaterial, Object3D,
  Quaternion, Scene, TorusGeometry, Vector3, type Group,
} from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { LANDMARKS, LANDMARK_LABELS, type ColliderDef } from './layout';

export interface ProbeInfo {
  loaded: boolean;
  source: string;
  meshName: string;
  dimensions: { x: number; y: number; z: number } | null;
  bounds: { min: number[]; max: number[] } | null;
  triangles: number;
  animations: string[];
}

type MaterialKey = 'paving' | 'stone' | 'plinth' | 'metal' | 'shadow' | 'grass' | 'bark' | 'leaf' | 'red' | 'cyan' | 'rust';
type Triple = [number, number, number];

/** Phase 1 primitives only. Collision stays separate from batched render geometry. */
export class World {
  readonly scene = new Scene();
  readonly sun = new DirectionalLight('#ffe2b2', 3.0);
  readonly colliderDefs: ColliderDef[] = [];
  readonly probe: ProbeInfo = {
    loaded: false, source: `${import.meta.env.BASE_URL}assets/probe.glb`, meshName: 'PROBE_CUBE',
    dimensions: null, bounds: null, triangles: 0, animations: [],
  };
  imported: Group | null = null;
  private readonly batches = new Map<MaterialKey, BufferGeometry[]>();
  private readonly materials: Record<MaterialKey, MeshStandardMaterial>;

  constructor() {
    this.scene.background = new Color('#a8b8bd');
    this.scene.fog = new Fog('#bfa684', 65, 175);
    this.scene.add(new HemisphereLight('#b9d0dc', '#877251', 2.0));
    this.sun.castShadow = true;
    this.sun.shadow.mapSize.set(2048, 2048);
    this.sun.shadow.camera.left = -68;
    this.sun.shadow.camera.right = 68;
    this.sun.shadow.camera.top = 62;
    this.sun.shadow.camera.bottom = -62;
    this.sun.shadow.camera.near = 1;
    this.sun.shadow.camera.far = 200;
    this.sun.shadow.normalBias = 0.06;
    this.sun.shadow.bias = -0.00008;
    this.scene.add(this.sun, this.sun.target);
    this.setSun(16);
    const swatches: Record<MaterialKey, string> = {
      paving: '#c4ae88', stone: '#c5b89e', plinth: '#8b7a63', metal: '#3a4149',
      shadow: '#282e33', grass: '#686f48', bark: '#665542', leaf: '#4a5a32',
      red: '#8b2e2e', cyan: '#3ec7c2', rust: '#825238',
    };
    this.materials = Object.fromEntries(Object.entries(swatches).map(([key, color]) => [key,
      new MeshStandardMaterial({
        color, roughness: 0.92, metalness: key === 'metal' ? 0.12 : 0,
        ...(key === 'cyan' ? { emissive: color, emissiveIntensity: 0.5 } : {}),
      }),
    ])) as Record<MaterialKey, MeshStandardMaterial>;
    this.buildGreybox();
    this.flushBatches();
    for (const [name, position] of Object.entries(LANDMARKS)) {
      const anchor = new Object3D();
      anchor.name = name;
      anchor.position.set(...position);
      anchor.userData.label = LANDMARK_LABELS[name];
      this.scene.add(anchor);
    }
  }

  private addGeometry(key: MaterialKey, geometry: BufferGeometry, position: Triple, scale: Triple = [1, 1, 1], rotation = new Quaternion()) {
    // Every source is non-indexed so primitive families share one merge convention.
    const prepared = geometry.index ? geometry.toNonIndexed() : geometry;
    prepared.applyMatrix4(new Matrix4().compose(new Vector3(...position), rotation, new Vector3(...scale)));
    if (prepared !== geometry) geometry.dispose();
    const batch = this.batches.get(key) ?? [];
    batch.push(prepared);
    this.batches.set(key, batch);
  }

  private box(name: string, key: MaterialKey, position: Triple, size: Triple, collide = true, rotation = new Quaternion()) {
    this.addGeometry(key, new BoxGeometry(...size), position, [1, 1, 1], rotation);
    if (collide) this.colliderDefs.push({
      name: `COL_${name}`, kind: 'box', position, halfExtents: [size[0] / 2, size[1] / 2, size[2] / 2],
      ...(rotation.equals(new Quaternion()) ? {} : { rotation: rotation.toArray() as [number, number, number, number] }),
    });
  }

  private cylinder(name: string, key: MaterialKey, position: Triple, radius: number, height: number, collide = true, topRadius = radius, segments = 12) {
    this.addGeometry(key, new CylinderGeometry(topRadius, radius, height, segments), position);
    if (collide) this.colliderDefs.push({ name: `COL_${name}`, kind: 'cylinder', position, radius, halfHeight: height / 2 });
  }

  private limb(start: Triple, end: Triple, bottomRadius: number, topRadius: number) {
    const a = new Vector3(...start);
    const b = new Vector3(...end);
    const direction = b.clone().sub(a);
    this.addGeometry('bark', new CylinderGeometry(topRadius, bottomRadius, direction.length(), 7),
      a.add(b).multiplyScalar(0.5).toArray() as Triple, [1, 1, 1],
      new Quaternion().setFromUnitVectors(new Vector3(0, 1, 0), direction.normalize()));
  }

  private flushBatches() {
    for (const [key, geometries] of this.batches) {
      const geometry = mergeGeometries(geometries, false);
      if (!geometry) throw new Error(`Unable to merge greybox material family ${key}.`);
      geometry.computeBoundingSphere();
      const mesh = new Mesh(geometry, this.materials[key]);
      mesh.name = `GREYBOX_${key}`;
      mesh.castShadow = key !== 'paving' && key !== 'cyan';
      mesh.receiveShadow = true;
      this.scene.add(mesh);
      for (const source of geometries) source.dispose();
    }
    this.batches.clear();
  }

  private buildGreybox() {
    this.box('ground', 'paving', [0, -0.3, 0], [120, 0.6, 90], false);
    // An exact plane gives stable capsule contacts; the large thin cuboid produced
    // spurious lateral contact normals. Perimeter walls bound the playable floor.
    this.colliderDefs.push({ name: 'COL_ground', kind: 'halfspace', position: [0, 0, 0], normal: [0, 1, 0] });
    this.box('desert_backdrop', 'plinth', [0, -0.65, 0], [400, 0.2, 400], false);
    // Paving joints use geometry, with no texture or per-tile draw calls.
    for (let x = -56; x <= 56; x += 4) this.box(`paving_x_${x}`, 'plinth', [x, 0.006, 0], [0.035, 0.01, 86], false);
    for (let z = -40; z <= 40; z += 4) this.box(`paving_z_${z}`, 'plinth', [0, 0.007, z], [116, 0.01, 0.035], false);
    for (const z of [-4, 4]) this.box('avenue_edge', 'stone', [-27, 0.018, z], [37, 0.03, 0.18], false);
    for (const x of [-4, 4]) this.box('south_avenue_edge', 'stone', [x, 0.018, 22], [0.18, 0.03, 19], false);
    this.buildHill();
    this.buildGate();
    this.buildShops();
    this.buildHall();
    this.buildLattice();
    this.buildRings();
    this.buildProps();
    this.buildBoundary();
  }

  private buildHill() {
    this.box('hill', 'plinth', [0, 0.7, 0], [14, 1.4, 14]);
    this.box('hill_grass', 'grass', [0, 1.45, 0], [14, 0.1, 14]);
    // Each flight meets the plateau with six 25 cm rises, never an invisible ramp.
    for (let step = 0; step < 6; step++) {
      const height = (step + 1) * 0.25;
      const distance = 10.3 - step * 0.6;
      this.box(`hill_stair_w_${step}`, 'stone', [-distance, height / 2, 0], [0.6, height, 4]);
      this.box(`hill_stair_s_${step}`, 'stone', [0, height / 2, distance], [4, height, 0.6]);
      this.box(`hill_stair_n_${step}`, 'stone', [0, height / 2, -distance], [4, height, 0.6]);
    }
    this.cylinder('hill_tree_trunk', 'bark', [0, 6, 0], 1.2, 9, true, 0.8, 10);
    this.limb([0, 6.5, 0], [-1.4, 13.5, 0.2], 0.95, 0.5);
    this.limb([-1.4, 13.5, 0.2], [1, 18.4, -0.8], 0.5, 0.15);
    const branches: Array<[Triple, Triple, number, number]> = [
      [[-0.3, 8.7, 0], [-6.2, 14.5, 1.5], 0.65, 0.16],
      [[-1.1, 12.3, 0], [-7.6, 16.2, -3.3], 0.5, 0.1],
      [[0, 9.8, 0], [5.7, 15, 2.6], 0.65, 0.12],
      [[-0.7, 13.2, 0], [5, 18.2, -3.4], 0.45, 0.1],
      [[0, 9.5, 0], [0, 15.7, 6.7], 0.6, 0.15],
      [[-1.1, 12, 0], [-1.8, 18.3, -6.1], 0.4, 0.09],
      [[-5.4, 13.5, 1.1], [-7.7, 16.8, 1.5], 0.22, 0.06],
      [[4.7, 14.1, 2.3], [7.8, 15.8, 3.4], 0.2, 0.035],
    ];
    for (const branch of branches) this.limb(...branch);
    const crowns: Array<[Triple, Triple]> = [
      [[-5, 16, 1.5], [4.4, 3.8, 4.1]], [[-5.7, 17.2, -3.7], [4.2, 3.3, 3.9]],
      [[0.2, 19, -1.2], [5.2, 3.4, 4.3]], [[4.4, 17, 2.6], [4.1, 3.5, 3.6]],
      [[4.1, 18.5, -3.8], [4.2, 3.2, 3.6]], [[-0.4, 17, 5.1], [4.1, 3.6, 3.6]],
      [[-1.4, 18.4, -6], [3.8, 3.2, 3.2]],
    ];
    for (const [position, scale] of crowns) this.addGeometry('leaf', new IcosahedronGeometry(1, 1), position, scale);
    this.box('hill_west_path', 'stone', [-4, 1.507, 0], [6, 0.012, 3], false);
    this.box('hill_south_path', 'stone', [0, 1.507, 4], [3, 0.012, 6], false);
  }

  private buildGate() {
    for (const [from, to] of [[-45, -3.7], [3.7, 8.3], [15.7, 45]]) {
      this.box('west_wall', 'stone', [-48, 3.7, (from + to) / 2], [3, 7.4, to - from]);
      this.box('west_wall_cap', 'plinth', [-48, 7.5, (from + to) / 2], [3.5, 0.3, to - from], false);
    }
    const turn = new Quaternion().setFromAxisAngle(new Vector3(0, 1, 0), Math.PI / 2);
    for (const z of [0, 12]) {
      for (const side of [-1, 1]) this.box('gate_pier', 'stone', [-48, 1.5, z + side * 3.25], [3, 3, 0.9]);
      this.addGeometry('stone', new TorusGeometry(3.25, 0.45, 6, 16, Math.PI), [-46.45, 3, z], [1, 1, 1], turn);
      this.addGeometry('stone', new TorusGeometry(3.25, 0.45, 6, 16, Math.PI), [-49.55, 3, z], [1, 1, 1], turn);
      this.box('gate_tunnel_roof', 'stone', [-48, 6.6, z], [3, 1.6, 5.6]);
      this.box('gate_arch_shoulder_a', 'stone', [-48, 4.8, z - 2.7], [3, 2.4, 0.85]);
      this.box('gate_arch_shoulder_b', 'stone', [-48, 4.8, z + 2.7], [3, 2.4, 0.85]);
    }
    for (const z of [-6, 6, 18]) {
      this.box('gate_banner', 'red', [-46.4, 4.6, z], [0.1, 3.4, 1.3], false);
      this.box('gate_banner_crest', 'stone', [-46.3, 5.4, z], [0.1, 0.15, 0.7], false);
    }
    this.box('gate_avenue_marker', 'cyan', [-45.8, 0.022, 0], [0.15, 0.04, 4], false);
  }

  private buildShops() {
    for (const side of [-1, 1]) {
      for (let index = 0; index < 4; index++) {
        const z = [-18, -9, 9, 18][index];
        const name = `shop_${side === 1 ? 'e' : 'w'}_${index + 1}`;
        const height = [8, 10, 7, 9][index] + (side === -1 && index === 0 ? 2 : 0);
        this.box(`${name}_first_step`, 'stone', [side * 14.1, 0.125, z], [0.8, 0.25, 4.2]);
        this.box(`${name}_porch`, 'plinth', [side * 17, 0.25, z], [5, 0.5, 7.6]);
        this.box(`${name}_interior_floor`, 'plinth', [side * 20.25, 0.25, z], [1.5, 0.5, 6.5]);
        this.box(`${name}_back`, 'metal', [side * 23, height / 2 + 0.5, z], [4, height, 7]);
        // Door opens 2.4 m wide and 2.5 m high into a two-metre stage set.
        for (const edge of [-1, 1]) {
          this.box(`${name}_jamb`, 'stone', [side * 18.7, 1.75, z + edge * 2.35], [0.8, 2.5, 2.3]);
          this.box(`${name}_side`, 'metal', [side * 20, 1.75, z + edge * 3.25], [2.5, 2.5, 0.5]);
        }
        this.box(`${name}_lintel`, 'metal', [side * 19.6, 3.8, z], [2.6, 1.6, 7]);
        this.box(`${name}_roof`, 'plinth', [side * 21.8, 4.8, z], [7.8, 0.35, 7.5]);
        this.box(`${name}_recess`, 'shadow', [side * 20.97, 1.75, z], [0.05, 2.5, 2.5], false);
        this.box(`${name}_sign`, 'cyan', [side * 18.22, 3.8, z], [0.1, 0.52, 4.8], false);
        this.box(`${name}_upper_slit`, 'cyan', [side * 20.96, height - 1, z], [0.06, 0.22, 5.6], false);
        this.box(`${name}_roof_trim`, 'plinth', [side * 23, height + 0.55, z], [4.4, 0.2, 7.4], false);
        if (index % 2 === 0) this.box(`${name}_banner`, 'red', [side * 18.15, 2.2, z + 2.4], [0.08, 1.8, 0.7], false);
      }
    }
    this.box('general_first_step', 'stone', [-8, 0.125, 17.8], [3.2, 0.25, 0.8]);
    this.box('general_porch', 'plinth', [-8, 0.25, 15.7], [5.2, 0.5, 3.4]);
    this.box('general_back', 'metal', [-8, 2, 13.6], [5.2, 3, 0.8]);
    for (const x of [-10.4, -5.6]) this.box('general_side', 'stone', [x, 1.7, 14.6], [0.4, 2.4, 1.8]);
    this.box('general_awning', 'red', [-8, 3.1, 15.1], [5.5, 0.25, 3.5]);
    this.box('general_sign', 'cyan', [-8, 2.7, 16.88], [3.6, 0.35, 0.1], false);
  }

  private buildHall() {
    this.box('hall_step', 'stone', [10, 0.125, -23.9], [6, 0.25, 0.8]);
    this.box('hall_plinth', 'plinth', [10, 0.25, -30.8], [13, 0.5, 13]);
    this.box('hall_main', 'metal', [10, 6, -32.5], [11, 11, 8]);
    for (const x of [5.5, 14.5]) this.box('hall_front_pier', 'stone', [x, 2.2, -27.5], [2, 3.4, 2]);
    this.box('hall_lintel', 'plinth', [10, 4.4, -27.5], [11.5, 1, 2.5]);
    this.box('hall_crown', 'plinth', [10, 11.7, -32.5], [11.7, 0.5, 8.7], false);
    this.box('hall_crest', 'red', [10, 8, -28.4], [2.5, 4, 0.1], false);
    this.box('hall_antenna', 'metal', [10, 14.2, -32.5], [0.45, 4.7, 0.45], false);
    this.box('hall_antenna_crossbar', 'metal', [10, 15.4, -32.5], [4, 0.3, 0.3], false);
    this.box('hall_light', 'cyan', [10, 4.4, -26.2], [5.6, 0.15, 0.08], false);
  }

  private buildLattice() {
    this.box('lattice_step', 'stone', [0, 0.125, -33.6], [4.4, 0.25, 0.8]);
    this.box('lattice_pad', 'plinth', [0, 0.25, -38], [8, 0.5, 8]);
    this.cylinder('lattice_terminal_base', 'metal', [0, 1.05, -39], 0.7, 1.1);
    this.box('lattice_terminal', 'metal', [0, 1.8, -39], [1.3, 0.5, 0.8]);
    this.box('lattice_terminal_screen', 'cyan', [0, 1.84, -38.56], [1.03, 0.32, 0.07], false);
    this.cylinder('lattice_column', 'metal', [0, 3, -41], 0.3, 5, true, 0.3, 8);
    this.addGeometry('cyan', new TorusGeometry(2.3, 0.12, 5, 32), [0, 4, -40.7]);
    for (const x of [-3.4, 3.4]) this.box('lattice_corner', 'cyan', [x, 0.53, -38], [0.12, 0.05, 6.5], false);
  }

  private buildRings() {
    this.box('ring_step_n', 'stone', [0, 0.125, 32.8], [4.4, 0.25, 0.8]);
    this.box('ring_step_s', 'stone', [0, 0.125, 39.4], [4.4, 0.25, 0.8]);
    this.box('ring_pad', 'plinth', [0, 0.25, 36.1], [12, 0.5, 5.8]);
    const turn = new Quaternion().setFromAxisAngle(new Vector3(0, 1, 0), Math.PI / 2);
    for (const x of [-4.2, 4.2]) {
      this.addGeometry('stone', new TorusGeometry(2.65, 0.5, 6, 16), [x, 3.6, 36.1], [1, 1, 1], turn);
      this.addGeometry('cyan', new TorusGeometry(2.08, 0.065, 5, 24), [x, 3.6, 36.1], [1, 1, 1], turn);
      this.box('ring_foot', 'stone', [x, 0.8, 36.1], [1.4, 0.6, 3]);
      for (let segment = 0; segment < 12; segment++) {
        const angle = segment * Math.PI / 6;
        const rotation = new Quaternion().setFromAxisAngle(new Vector3(1, 0, 0), angle);
        this.colliderDefs.push({
          name: `COL_ring_${x}_${segment}`, kind: 'box',
          position: [x, 3.6 + Math.cos(angle) * 2.65, 36.1 + Math.sin(angle) * 2.65],
          halfExtents: [0.5, 0.48, 0.7], rotation: rotation.toArray() as [number, number, number, number],
        });
      }
    }
  }

  private buildProps() {
    this.box('mission_plinth', 'plinth', [-8, 0.125, -13], [7, 0.25, 3.5]);
    for (const x of [-10, -8, -6]) this.terminal(`mission_${x}`, x, 0.25, -13.8);
    for (const [x, z] of [[-5, -4], [5, -4], [5, 1]]) this.terminal('hill_market', x, 1.5, z);
    this.box('billboard_post', 'metal', [5.4, 4.6, 5.1], [0.35, 6.2, 0.35]);
    this.box('billboard_frame', 'metal', [5.4, 7.5, 5.1], [4.6, 2.8, 0.35], false);
    this.box('billboard_glow', 'cyan', [5.4, 7.5, 5.3], [4.2, 2.4, 0.06], false);
    this.box('billboard_mark_a', 'metal', [5.4, 7.7, 5.34], [2.8, 0.18, 0.05], false);
    this.box('billboard_mark_b', 'metal', [5.4, 7.1, 5.34], [1.7, 0.12, 0.05], false);
    for (const [x, z] of [[-31, -8], [-30, 8], [29, 8], [28, -10]]) {
      this.box('bench_base', 'metal', [x, 0.3, z], [2.4, 0.6, 0.7]);
      this.box('bench_top', 'plinth', [x, 0.65, z], [2.8, 0.12, 0.9], false);
    }
    for (const [x, z] of [[-29, -23], [-31, -22], [28, 22], [30, 23], [29, -24]]) this.box('crate', 'rust', [x, 0.65, z], [1.3, 1.3, 1.3]);
    for (const [x, z] of [[-35, -5], [-35, 5], [-12, -25], [12, 25], [32, 5]]) {
      this.box('avenue_lamp', 'metal', [x, 2.3, z], [0.18, 4.6, 0.18]);
      this.box('avenue_lamp_cap', 'cyan', [x, 4.5, z], [0.45, 0.45, 0.45], false);
    }
    this.box('wreck_plinth_n', 'plinth', [53, 1.5, -7], [7, 3, 3]);
    this.box('wreck_plinth_s', 'plinth', [54, 2, 8], [6, 4, 3]);
    this.box('wreck_beam_a', 'rust', [53, 5.2, -6], [0.9, 8, 0.8], true,
      new Quaternion().setFromAxisAngle(new Vector3(0, 0, 1), -0.24));
    this.box('wreck_beam_b', 'rust', [55, 4.7, 7], [0.7, 8, 0.7], true,
      new Quaternion().setFromAxisAngle(new Vector3(0, 0, 1), 0.25));
    this.box('wreck_crossbeam', 'rust', [54, 8.5, 0], [1, 1, 15], true,
      new Quaternion().setFromAxisAngle(new Vector3(1, 0, 0), 0.15));
  }

  private terminal(name: string, x: number, foot: number, z: number) {
    this.box(`${name}_body`, 'metal', [x, foot + 0.65, z], [0.75, 1.3, 0.65]);
    this.box(`${name}_screen`, 'cyan', [x, foot + 1.1, z + 0.34], [0.58, 0.35, 0.04], false);
  }

  private buildBoundary() {
    this.box('boundary_w', 'plinth', [-59, 1.5, 0], [2, 3, 90]);
    this.box('boundary_e', 'plinth', [59, 1.5, 0], [2, 3, 90]);
    for (const z of [-44.5, 44.5]) this.box('boundary_ns', 'plinth', [0, 2.5, z], [120, 5, 1]);
    for (const [x, z, height, radius] of [[-80, -65, 13, 25], [-28, -86, 19, 32], [27, -85, 13, 30], [85, -61, 20, 28], [99, 1, 18, 24], [95, 46, 13, 28], [-87, 63, 16, 30]]) {
      this.cylinder('distant_butte', 'plinth', [x, height / 2 - 1, z], radius, height, false, radius * 0.45, 6);
    }
  }

  async load() {
    // Keep the verified Blender round-trip as an archived exhibit off the route.
    const gltf = await new GLTFLoader().loadAsync(this.probe.source);
    const cube = gltf.scene.getObjectByName(this.probe.meshName);
    if (!cube) throw new Error('probe.glb is missing the Blender render mesh PROBE_CUBE.');
    gltf.scene.updateMatrixWorld(true);
    const bounds = new Box3().setFromObject(cube);
    const size = bounds.getSize(new Vector3());
    if (![size.x, size.y, size.z].every((n) => Math.abs(n - 2) < 0.02) || Math.abs(bounds.min.y) > 0.02) {
      throw new Error(`Blender probe must be a ground-centred 2 m cube; received ${size.toArray().map((n) => n.toFixed(3)).join(' × ')} m, base ${bounds.min.y.toFixed(3)} m.`);
    }
    gltf.scene.traverse((object) => {
      if (object instanceof Mesh) {
        object.castShadow = true;
        object.receiveShadow = true;
        this.probe.triangles += (object.geometry.index?.count ?? object.geometry.attributes.position.count) / 3;
      }
    });
    gltf.scene.position.set(-52, 0, 20);
    this.imported = gltf.scene;
    this.scene.add(gltf.scene);
    this.colliderDefs.push({ name: 'COL_PROBE_CUBE', kind: 'box', position: [-52, 1, 20], halfExtents: [1, 1, 1] });
    this.probe.dimensions = { x: size.x, y: size.y, z: size.z };
    this.probe.bounds = { min: bounds.min.toArray(), max: bounds.max.toArray() };
    this.probe.animations = gltf.animations.map((clip) => clip.name);
    this.probe.loaded = true;
  }

  setSun(hour: number) {
    const angle = ((hour - 6) / 12) * Math.PI;
    this.sun.position.set(Math.cos(angle) * 72, Math.max(12, Math.sin(angle) * 80), 42);
  }
}
