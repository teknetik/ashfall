import RAPIER from '@dimforge/rapier3d-compat';
import type { ColliderDef } from './layout';

export const FIXED_STEP = 1 / 60;
export const CHARACTER = {
  radius: 0.35,
  height: 1.8,
  offset: 0.015,
  maxStep: 0.3,
  minStepWidth: 0.22,
  groundSnap: 0.4,
  maxSlope: Math.PI / 4,
  walkSpeed: 3.4,
  runSpeed: 6,
  gravity: -20,
} as const;

const identity = { x: 0, y: 0, z: 0, w: 1 };
let initialized: Promise<void> | undefined;

/** Owns simple collision proxies independently from the rendered greybox. */
export class Physics {
  readonly world = new RAPIER.World({ x: 0, y: CHARACTER.gravity, z: 0 });
  private readonly names = new Map<number, string>();
  private readonly definitions = new Map<number, ColliderDef>();
  private readonly cameraShape = new RAPIER.Ball(0.23);
  private disposed = false;
  private steps = 0;

  private constructor(definitions: readonly ColliderDef[]) {
    this.world.timestep = FIXED_STEP;
    for (const definition of definitions) {
      const shape = definition.kind === 'halfspace'
        ? new RAPIER.ColliderDesc(new RAPIER.HalfSpace({
          x: definition.normal[0], y: definition.normal[1], z: definition.normal[2],
        }))
        : definition.kind === 'box'
          ? RAPIER.ColliderDesc.cuboid(...definition.halfExtents)
          : RAPIER.ColliderDesc.cylinder(definition.halfHeight, definition.radius);
      shape.setTranslation(...definition.position).setFriction(0.8).setRestitution(0);
      if (definition.kind === 'box' && definition.rotation) {
        const [x, y, z, w] = definition.rotation;
        shape.setRotation({ x, y, z, w });
      }
      const collider = this.world.createCollider(shape);
      this.names.set(collider.handle, definition.name);
      this.definitions.set(collider.handle, definition);
    }
    // Populate the broad phase before the first character or camera query.
    this.world.step();
  }

  static async create(definitions: readonly ColliderDef[]) {
    initialized ??= RAPIER.init();
    await initialized;
    return new Physics(definitions);
  }

  step(dt: number) {
    this.world.timestep = dt;
    this.world.step();
    this.steps += 1;
  }

  colliderName(collider: RAPIER.Collider) {
    return this.names.get(collider.handle) ?? 'COL_player';
  }

  /** A swept sphere protects the camera's near plane, including around corners. */
  cameraDistance(origin: RAPIER.Vector, direction: RAPIER.Vector, distance: number, player: RAPIER.Collider) {
    const hit = this.world.castShape(
      origin, identity, direction, this.cameraShape, 0.015, distance, true,
      RAPIER.QueryFilterFlags.EXCLUDE_SENSORS, undefined, player,
    );
    return hit ? Math.max(0, hit.time_of_impact - 0.035) : distance;
  }

  nearby(position: RAPIER.Vector, radius = 3) {
    const nearby: ColliderDef[] = [];
    this.world.collidersWithAabbIntersectingAabb(
      { x: position.x, y: position.y + CHARACTER.height / 2, z: position.z },
      { x: radius, y: radius, z: radius },
      (collider) => {
        const definition = this.definitions.get(collider.handle);
        if (definition) nearby.push(definition);
        return true;
      },
    );
    return nearby.sort((a, b) => a.name.localeCompare(b.name));
  }

  get diagnostics() {
    return {
      engine: `Rapier ${RAPIER.version()}`,
      timestep: this.world.timestep,
      steps: this.steps,
      bodies: this.world.bodies.len(),
      colliders: this.world.colliders.len(),
      staticColliders: this.definitions.size,
      characterControllers: this.world.characterControllers.size,
      ccdBodies: 0,
      sensors: 0,
      collisionGroups: 'default; camera excludes player',
      character: { ...CHARACTER },
      cameraCastRadius: 0.23,
      riskyColliders: [] as string[],
    };
  }

  dispose() {
    if (this.disposed) return;
    this.disposed = true;
    this.world.free();
  }
}
