import { Vector3, type Camera, type Scene } from 'three';
import type { CharacterInstance, CharacterLibrary, CharacterVariant } from './characters';

type Point = readonly [number, number, number];
export type NamedNPCId = 'npc_mira' | 'npc_torr' | 'npc_vex' | 'npc_linn';
export type NPCRole = 'vendor' | 'fixer' | 'guard' | 'loafer';

export interface NPCDefinition {
  readonly id: NamedNPCId;
  readonly name: string;
  readonly role: NPCRole;
  readonly landmark: string;
  readonly position: Point;
  /** Authored character roots face +Z. This is the model's local Y rotation. */
  readonly yaw: number;
  readonly tint: string;
}

/** Feet stay on existing level support surfaces, away from stairs and terminals. */
export const NPC_DEFINITIONS: readonly NPCDefinition[] = [
  { id: 'npc_mira', name: 'Mira', role: 'vendor', landmark: 'basic_general', position: [-8, .5, 15.8], yaw: 0, tint: '#8b3c3a' },
  { id: 'npc_torr', name: 'Torr', role: 'fixer', landmark: 'mission_slab', position: [-9, .25, -12], yaw: 0, tint: '#69735c' },
  { id: 'npc_vex', name: 'Vex', role: 'guard', landmark: 'west_gate', position: [-41.7, 0, -1.5], yaw: -.70, tint: '#645e55' },
  { id: 'npc_linn', name: 'Linn', role: 'loafer', landmark: 'hill_tree', position: [-2.5, 1.5, 4.7], yaw: -2.0, tint: '#ad865c' },
];

interface WalkerDefinition {
  readonly id: string;
  readonly name: string;
  readonly tint: string;
  readonly speed: number;
  readonly phase: number;
  readonly waypoints: readonly Point[];
}

/** These closed loops remain on open, flat pavement; no physics bodies are added. */
export const AMBIENT_WALKERS: readonly WalkerDefinition[] = [
  { id: 'npc_walker_01', name: 'Market porter', tint: '#8a7150', speed: .95, phase: .12,
    waypoints: [[-38, 0, -3.5], [-16, 0, -3.5], [-16, 0, -2.5], [-38, 0, -2.5]] },
  { id: 'npc_walker_02', name: 'Column resident', tint: '#647971', speed: 1.05, phase: .47,
    waypoints: [[-3, 0, 22], [4, 0, 22], [4, 0, 28], [-3, 0, 28]] },
  { id: 'npc_walker_03', name: 'Courtyard runner', tint: '#8b625d', speed: 1.15, phase: .68,
    waypoints: [[-11, 0, -23], [-5, 0, -23], [-5, 0, -19], [-11, 0, -19]] },
];

const ROLE_LABELS: Record<NPCRole, string> = {
  vendor: 'Basic General', fixer: 'Local fixer', guard: 'Free Column guard', loafer: 'Hill regular',
};
const INTERACTION_RANGE = 2.4;
const LABEL_RANGE = 34;
const LABEL_WIDTH = 148;
const LABEL_HEIGHT = 58;
const turnDifference = (to: number, from: number) => Math.atan2(Math.sin(to - from), Math.cos(to - from));

export interface NPCPlayerPose {
  readonly position: { readonly x: number; readonly y: number; readonly z: number };
  /** Optional controller heading: zero faces -Z, matching Player.snapshot.yaw. */
  readonly yaw?: number;
}

export interface NPCInteractionTarget {
  readonly id: NamedNPCId;
  readonly name: string;
  readonly role: NPCRole;
  readonly landmark: string;
  readonly distance: number;
  readonly position: { readonly x: number; readonly y: number; readonly z: number };
}

interface Actor {
  id: string;
  name: string;
  instance: CharacterInstance;
  definition: NPCDefinition | null;
  walker: WalkerDefinition | null;
  routeLengths: number[];
  routeLength: number;
  routeDistance: number;
  talking: boolean;
  gestureRemaining: number;
  label: HTMLDivElement | null;
  action: HTMLSpanElement | null;
  labelVisible: boolean;
}

/** Authored character instances, deterministic town motion and a small interaction seam.
 * The caller owns input, dialogue/shop states, the render loop and the shared library.
 */
export class NPCSystem {
  readonly root: HTMLDivElement;
  onInteract: (target: NPCInteractionTarget) => void = () => {};
  private readonly actors: Actor[] = [];
  private readonly playerPosition = new Vector3();
  private readonly projected = new Vector3();
  private selected: Actor | null = null;
  private hasPlayer = false;
  private playerYaw: number | undefined;
  private disposed = false;
  private elapsed = 0;
  private interactions = 0;

  constructor(scene: Scene, library: CharacterLibrary, overlayRoot: HTMLElement) {
    this.root = document.createElement('div');
    this.root.className = 'npc-label-layer';
    this.root.setAttribute('aria-hidden', 'true');
    Object.assign(this.root.style, { position: 'absolute', inset: '0', pointerEvents: 'none',
      overflow: 'hidden', zIndex: '2', userSelect: 'none' });
    overlayRoot.append(this.root);
    try {
      for (const definition of NPC_DEFINITIONS) {
        // Legacy browser prototype: interactive colonists use the Ward Guard.
        const actor = this.createActor(library, definition.id, definition.name, definition.tint, 'guard');
        actor.definition = definition;
        actor.instance.root.position.fromArray(definition.position);
        actor.instance.root.rotation.y = definition.yaw;
        this.addLabel(actor, definition);
        scene.add(actor.instance.root);
      }
      for (const walker of AMBIENT_WALKERS) {
        const actor = this.createActor(library, walker.id, walker.name, walker.tint);
        actor.walker = walker;
        actor.routeLengths = walker.waypoints.map((point, index) => {
          const next = walker.waypoints[(index + 1) % walker.waypoints.length];
          return Math.hypot(next[0] - point[0], next[2] - point[2]);
        });
        actor.routeLength = actor.routeLengths.reduce((sum, length) => sum + length, 0);
        actor.routeDistance = actor.routeLength * walker.phase;
        this.placeWalker(actor, 0, true);
        scene.add(actor.instance.root);
      }
    } catch (error) {
      this.dispose();
      throw error;
    }
  }

  private createActor(library: CharacterLibrary, id: string, name: string, tint: string, variant: CharacterVariant = 'default'): Actor {
    const instance = library.create({ id, kind: 'npc', variant, tint });
    instance.root.name = id;
    instance.root.userData.npcId = id;
    const actor: Actor = { id, name, instance, definition: null, walker: null, routeLengths: [],
      routeLength: 0, routeDistance: 0, talking: false, gestureRemaining: 0,
      label: null, action: null, labelVisible: false };
    this.actors.push(actor);
    return actor;
  }

  private addLabel(actor: Actor, definition: NPCDefinition) {
    const label = document.createElement('div');
    label.className = 'npc-nametag';
    label.dataset.npc = definition.id;
    label.hidden = true;
    Object.assign(label.style, { position: 'absolute', left: '0', top: '0', width: `${LABEL_WIDTH}px`,
      maxWidth: `${LABEL_WIDTH}px`, textAlign: 'center', color: '#f0e5cf', fontSize: '12px',
      lineHeight: '1.3', fontWeight: '500', textShadow: '0 1px 3px #101e20,0 0 7px #101e20',
      willChange: 'transform' });
    const name = document.createElement('span');
    name.textContent = definition.name;
    name.style.display = 'block';
    const role = document.createElement('span');
    role.textContent = ROLE_LABELS[definition.role];
    Object.assign(role.style, { display: 'block', color: '#c4d2c4', fontSize: '10px', marginTop: '1px' });
    const action = document.createElement('span');
    action.textContent = `E · Talk to ${definition.name}`;
    action.hidden = true;
    Object.assign(action.style, { display: 'inline-block', marginTop: '5px', padding: '3px 7px',
      color: '#b0efdf', fontSize: '11px', background: '#202c2be8', border: '1px solid #769b8c',
      whiteSpace: 'nowrap' });
    label.append(name, role, action);
    this.root.append(label);
    actor.label = label;
    actor.action = action;
  }

  /** Pass simulation delta; passing zero freezes movement/animation but refreshes selection. */
  update(dt: number, player?: NPCPlayerPose | null) {
    if (this.disposed) return;
    if (!Number.isFinite(dt) || dt < 0) throw new Error('NPC update requires a finite non-negative delta.');
    this.elapsed += dt;
    this.hasPlayer = !!player;
    if (player) {
      this.playerPosition.copy(player.position);
      this.playerYaw = player.yaw;
    }
    for (const actor of this.actors) {
      actor.gestureRemaining = Math.max(0, actor.gestureRemaining - dt);
      if (actor.walker) this.placeWalker(actor, dt);
      const talking = actor.talking || actor.gestureRemaining > 0;
      if (actor.definition) {
        const targetYaw = talking && player
          ? Math.atan2(player.position.x - actor.instance.root.position.x, player.position.z - actor.instance.root.position.z)
          : actor.definition.yaw;
        actor.instance.root.rotation.y += turnDifference(targetYaw, actor.instance.root.rotation.y) * (1 - Math.exp(-6 * dt));
      }
      actor.instance.update(dt, { speed: actor.walker?.speed ?? 0, talking });
    }
    this.selectNearest();
  }

  private placeWalker(actor: Actor, dt: number, snapYaw = false) {
    const walker = actor.walker;
    if (!walker || !actor.routeLength) return;
    actor.routeDistance = (actor.routeDistance + walker.speed * dt) % actor.routeLength;
    let distance = actor.routeDistance;
    for (let index = 0; index < walker.waypoints.length; index++) {
      const length = actor.routeLengths[index];
      if (distance >= length && index < walker.waypoints.length - 1) { distance -= length; continue; }
      const a = walker.waypoints[index], b = walker.waypoints[(index + 1) % walker.waypoints.length];
      const ratio = length > 0 ? distance / length : 0;
      actor.instance.root.position.set(a[0] + (b[0] - a[0]) * ratio, a[1], a[2] + (b[2] - a[2]) * ratio);
      const yaw = Math.atan2(b[0] - a[0], b[2] - a[2]);
      actor.instance.root.rotation.y = snapYaw ? yaw
        : actor.instance.root.rotation.y + turnDifference(yaw, actor.instance.root.rotation.y) * (1 - Math.exp(-8 * dt));
      return;
    }
  }

  private selectNearest() {
    let selected: Actor | null = null, closest = INTERACTION_RANGE;
    if (this.hasPlayer) for (const actor of this.actors) {
      if (!actor.definition) continue;
      const point = actor.instance.root.position;
      const dx = point.x - this.playerPosition.x, dz = point.z - this.playerPosition.z;
      const distance = Math.hypot(dx, dz);
      if (distance > closest || Math.abs(point.y - this.playerPosition.y) > 1) continue;
      // A generous forward hemisphere avoids accidental prompts behind the
      // player. Very close neighbours remain usable without precise aiming.
      if (distance > .8 && this.playerYaw !== undefined && Number.isFinite(this.playerYaw)) {
        const facing = (-Math.sin(this.playerYaw) * dx - Math.cos(this.playerYaw) * dz) / distance;
        if (facing < -.25) continue;
      }
      closest = distance;
      selected = actor;
    }
    this.selected = selected;
    for (const actor of this.actors) if (actor.action) actor.action.hidden = actor !== selected;
  }

  get nearest(): NPCInteractionTarget | null {
    const actor = this.selected, definition = actor?.definition;
    if (!actor || !definition || !this.hasPlayer) return null;
    const point = actor.instance.root.position;
    return { id: definition.id, name: definition.name, role: definition.role, landmark: definition.landmark,
      distance: Math.hypot(point.x - this.playerPosition.x, point.z - this.playerPosition.z),
      position: { x: point.x, y: point.y, z: point.z } };
  }

  /** Host input calls this on E; Phase 5 supplies dialogue/shop through the hook. */
  interact(): NPCInteractionTarget | null {
    if (this.disposed) return null;
    const target = this.nearest;
    if (!target) return null;
    this.selected!.gestureRemaining = 1.2;
    this.interactions += 1;
    this.onInteract(target);
    return target;
  }

  setTalking(id: NamedNPCId, talking: boolean) {
    const actor = this.actors.find(candidate => candidate.id === id && candidate.definition);
    if (!actor) throw new Error(`Unknown named NPC: ${id}`);
    actor.talking = talking;
    if (!talking) actor.gestureRemaining = 0;
  }

  /** Project only after the active camera has updated. Hidden/offscreen tags never clamp to an edge. */
  projectLabels(camera: Camera, canvas: HTMLCanvasElement, visible = true) {
    if (this.disposed) return;
    this.root.hidden = !visible;
    if (!visible) return;
    camera.updateMatrixWorld();
    const width = canvas.clientWidth, height = canvas.clientHeight;
    const canvasRect = canvas.getBoundingClientRect(), overlayRect = this.root.getBoundingClientRect();
    const offsetX = canvasRect.left - overlayRect.left, offsetY = canvasRect.top - overlayRect.top;
    const accepted: Array<{ x: number; y: number }> = [];
    // Prefer the interactable neighbour when two distant nametags would overlap.
    const named = this.actors.filter(actor => actor.label).sort((a, b) =>
      Number(b === this.selected) - Number(a === this.selected)
      || a.instance.root.position.distanceToSquared(camera.position) - b.instance.root.position.distanceToSquared(camera.position));
    for (const actor of named) {
      const label = actor.label!;
      actor.labelVisible = false;
      label.hidden = true;
      if (!actor.instance.root.visible || actor.instance.root.position.distanceToSquared(camera.position) > LABEL_RANGE ** 2) continue;
      this.projected.copy(actor.instance.root.position);
      this.projected.y += 2.13;
      this.projected.project(camera);
      if (this.projected.z < -1 || this.projected.z > 1) continue;
      const x = (this.projected.x * .5 + .5) * width;
      const y = (-this.projected.y * .5 + .5) * height;
      // Reserve header and bottom/touch areas; avoid partial labels at every edge.
      if (x < LABEL_WIDTH / 2 + 8 || x > width - LABEL_WIDTH / 2 - 8
        || y < Math.min(118, height * .24) + LABEL_HEIGHT || y > height - 86) continue;
      if (accepted.some(other => Math.abs(other.x - x) < LABEL_WIDTH + 4 && Math.abs(other.y - y) < LABEL_HEIGHT + 4)) continue;
      accepted.push({ x, y });
      label.style.transform = `translate3d(${offsetX + x}px,${offsetY + y}px,0) translate(-50%,-100%)`;
      label.hidden = false;
      actor.labelVisible = true;
    }
  }

  get diagnostics() {
    return { namedCount: NPC_DEFINITIONS.length, ambientCount: AMBIENT_WALKERS.length,
      instanceCount: this.actors.length, interactionRange: INTERACTION_RANGE,
      interactions: this.interactions, elapsed: this.elapsed, nearest: this.nearest,
      collisionPolicy: 'Nonblocking authored actors; named feet use fixed level support surfaces and walkers stay on bounded pavement routes.',
      actors: this.actors.map(actor => ({ id: actor.id, name: actor.name, role: actor.definition?.role ?? 'ambient',
        landmark: actor.definition?.landmark ?? null, position: actor.instance.root.position.toArray(),
        yaw: actor.instance.root.rotation.y, talking: actor.talking || actor.gestureRemaining > 0,
        labelVisible: actor.labelVisible, routeDistance: actor.walker ? actor.routeDistance : null,
        speed: actor.walker?.speed ?? 0, character: actor.instance.diagnostics })) };
  }

  dispose() {
    if (this.disposed) return;
    this.disposed = true;
    this.selected = null;
    this.root.remove();
    for (const actor of this.actors) {
      actor.instance.root.removeFromParent();
      actor.instance.dispose();
    }
    this.actors.length = 0;
    this.onInteract = () => {};
  }
}
