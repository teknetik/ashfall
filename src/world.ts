import { Box3, Color, DirectionalLight, Fog, HemisphereLight, Mesh, MeshStandardMaterial, PlaneGeometry, Scene, Vector3, type Group } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

export interface ProbeInfo {
  loaded: boolean;
  source: string;
  meshName: string;
  dimensions: { x: number; y: number; z: number } | null;
  bounds: { min: number[]; max: number[] } | null;
  triangles: number;
  animations: string[];
}

export class World {
  readonly scene = new Scene();
  readonly sun = new DirectionalLight('#ffe3b8', 3.2);
  readonly probe: ProbeInfo = {
    loaded: false, source: `${import.meta.env.BASE_URL}assets/probe.glb`, meshName: 'PROBE_CUBE',
    dimensions: null, bounds: null, triangles: 0, animations: [],
  };
  imported: Group | null = null;

  constructor() {
    this.scene.background = new Color('#b7bec0');
    this.scene.fog = new Fog('#b8956a', 38, 140);
    this.scene.add(new HemisphereLight('#a7c5d7', '#826449', 2));
    this.sun.position.set(-8, 12, 7);
    this.sun.castShadow = true;
    this.sun.shadow.mapSize.set(1024, 1024);
    this.sun.shadow.camera.left = -10;
    this.sun.shadow.camera.right = 10;
    this.sun.shadow.camera.top = 10;
    this.sun.shadow.camera.bottom = -10;
    this.sun.shadow.normalBias = 0.025;
    this.scene.add(this.sun);
    const ground = new Mesh(new PlaneGeometry(160, 140), new MeshStandardMaterial({ color: '#c4a574', roughness: 0.92 }));
    ground.name = 'PROBE_GROUND';
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    this.scene.add(ground);
  }

  async load() {
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
    this.imported = gltf.scene;
    this.scene.add(gltf.scene);
    this.probe.dimensions = { x: size.x, y: size.y, z: size.z };
    this.probe.bounds = { min: bounds.min.toArray(), max: bounds.max.toArray() };
    this.probe.animations = gltf.animations.map((clip) => clip.name);
    this.probe.loaded = true;
  }

  setSun(hour: number) {
    // Fixed late afternoon by default; useful for repeatable future visual comparisons.
    const angle = ((hour - 6) / 12) * Math.PI;
    this.sun.position.set(Math.cos(angle) * 13, Math.max(1, Math.sin(angle) * 16), 7);
  }
}
