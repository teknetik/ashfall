import {
  BufferGeometry, Camera, Float32BufferAttribute, Group, InstancedMesh,
  MeshBasicMaterial, Object3D, Points, PointsMaterial, Scene, TorusGeometry,
} from 'three';

export type TravelPhase = 'tunnel' | 'map';

export interface TravelNode {
  id: string;
  name: string;
  description: string;
}

export interface TravelSnapshot {
  phase: TravelPhase;
  progress: number;
  nodes: TravelNode[];
  selectedNode: string | null;
}

export interface TravelSelectionResult {
  ok: boolean;
  message: string;
}

export interface TravelOptions {
  reducedMotion?: boolean;
}

const NODES: readonly TravelNode[] = [
  {
    id: 'crosswind_reach',
    name: 'Crosswind Reach',
    description: 'Wind towers and scattered settlements beyond the western ridge.',
  },
  {
    id: 'drywater_works',
    name: 'Drywater Works',
    description: 'Reclamation yards surrounding the old water-processing halls.',
  },
  {
    id: 'beacon_dunes',
    name: 'Beacon Dunes',
    description: 'Signal beacons marking the outer desert routes.',
  },
];

const TRANSITION_SECONDS = 1.25;
const MOTE_COUNT = 28;

/** Local Lattice connection preview; destination selection never moves the player. */
export class TravelSystem {
  private phase: TravelPhase | null = null;
  private elapsed = 0;
  private progress = 0;
  private selectedNode: string | null = null;
  private reducedMotion: boolean;
  private disposed = false;
  private readonly effect = new Group();
  private readonly ringGeometry = new TorusGeometry(1, 0.008, 4, 48);
  private readonly ringMaterial = new MeshBasicMaterial({
    color: 0x3ec7c2,
    transparent: true,
    opacity: 0,
    depthWrite: false,
    toneMapped: false,
  });
  private readonly rings = new InstancedMesh(this.ringGeometry, this.ringMaterial, 2);
  private readonly moteGeometry = new BufferGeometry();
  private readonly moteMaterial = new PointsMaterial({
    color: 0x73dad1,
    size: 0.055,
    sizeAttenuation: true,
    transparent: true,
    opacity: 0,
    depthWrite: false,
    toneMapped: false,
  });
  private readonly motes = new Points(this.moteGeometry, this.moteMaterial);
  private readonly motePositions = new Float32Array(MOTE_COUNT * 3);
  private readonly moteOrigins = new Float32Array(MOTE_COUNT * 3);
  private readonly transform = new Object3D();

  constructor(scene: Scene, options: TravelOptions = {}) {
    this.reducedMotion = options.reducedMotion ?? false;
    this.effect.name = 'VFX_lattice_transition';
    this.effect.position.set(0, 0.58, -38);
    this.effect.visible = false;
    this.rings.name = 'VFX_lattice_sweep';
    this.motes.name = 'VFX_lattice_motes';
    // Two rings share one draw (768 triangles); 28 points use one more draw.
    // Their small fixed spatial envelope is safe to retain while matrices move.
    this.rings.frustumCulled = false;
    this.motes.frustumCulled = false;
    this.effect.add(this.rings, this.motes);

    for (let i = 0; i < MOTE_COUNT; i++) {
      const angle = i * 2.399963229728653;
      const radius = 0.65 + ((i * 11) % MOTE_COUNT) / MOTE_COUNT * 1.65;
      this.moteOrigins[i * 3] = Math.cos(angle) * radius;
      this.moteOrigins[i * 3 + 1] = 0.55 + ((i * 7) % MOTE_COUNT) / MOTE_COUNT * 1.25;
      this.moteOrigins[i * 3 + 2] = Math.sin(angle) * radius;
    }
    this.motePositions.set(this.moteOrigins);
    this.moteGeometry.setAttribute('position', new Float32BufferAttribute(this.motePositions, 3));
    scene.add(this.effect);
  }

  get active(): boolean {
    return this.phase !== null;
  }

  get snapshot(): TravelSnapshot | null {
    if (this.phase === null) return null;
    return {
      phase: this.phase,
      progress: this.progress,
      nodes: NODES.map(node => ({ ...node })),
      selectedNode: this.selectedNode,
    };
  }

  start(): void {
    if (this.disposed) return;
    this.phase = 'tunnel';
    this.elapsed = 0;
    this.progress = 0;
    this.selectedNode = null;
    this.updateEffect();
  }

  update(dt: number, _camera?: Camera): void {
    if (this.phase !== 'tunnel' || this.disposed) return;
    if (Number.isFinite(dt) && dt > 0) {
      this.elapsed = Math.min(TRANSITION_SECONDS, this.elapsed + dt);
      this.progress = this.elapsed / TRANSITION_SECONDS;
      if (this.elapsed >= TRANSITION_SECONDS) this.phase = 'map';
    }
    this.updateEffect();
  }

  selectNode(id: string): TravelSelectionResult {
    if (this.phase !== 'map') {
      return { ok: false, message: 'Wait for the Lattice connection to settle.' };
    }
    const node = NODES.find(candidate => candidate.id === id);
    if (!node) return { ok: false, message: 'That route is unavailable.' };
    this.selectedNode = node.id;
    return { ok: true, message: `Link established to ${node.name}.` };
  }

  setReducedMotion(reducedMotion: boolean): void {
    this.reducedMotion = reducedMotion;
    this.updateEffect();
  }

  close(): void {
    this.phase = null;
    this.elapsed = 0;
    this.progress = 0;
    this.selectedNode = null;
    this.effect.visible = false;
  }

  dispose(): void {
    if (this.disposed) return;
    this.close();
    this.disposed = true;
    this.effect.removeFromParent();
    this.rings.dispose();
    this.ringGeometry.dispose();
    this.ringMaterial.dispose();
    this.moteGeometry.dispose();
    this.moteMaterial.dispose();
  }

  private updateEffect(): void {
    this.effect.visible = this.phase === 'tunnel' && !this.reducedMotion && !this.disposed;
    if (!this.effect.visible) return;

    // One smooth swell and fade; no looping flashes, camera motion, or strobe.
    const envelope = Math.sin(Math.PI * this.progress);
    this.ringMaterial.opacity = envelope * 0.28;
    this.moteMaterial.opacity = envelope * 0.32;
    for (let i = 0; i < 2; i++) {
      const radius = i === 0 ? 0.9 + this.progress * 2.4 : 0.6 + this.progress * 1.6;
      this.transform.position.set(0, i * 0.025, 0);
      this.transform.rotation.set(Math.PI / 2, 0, 0);
      this.transform.scale.set(radius, radius, 1);
      this.transform.updateMatrix();
      this.rings.setMatrixAt(i, this.transform.matrix);
    }
    this.rings.instanceMatrix.needsUpdate = true;

    const position = this.moteGeometry.getAttribute('position');
    const spread = 1 + this.progress * 0.2;
    for (let i = 0; i < MOTE_COUNT; i++) {
      position.setXYZ(
        i,
        this.moteOrigins[i * 3] * spread,
        this.moteOrigins[i * 3 + 1] + this.progress * 0.4,
        this.moteOrigins[i * 3 + 2] * spread,
      );
    }
    position.needsUpdate = true;
  }
}
