import RAPIER from '@dimforge/rapier3d-compat';
import { BoxGeometry, CapsuleGeometry, Group, Mesh, MeshStandardMaterial, type Scene, Vector3 } from 'three';
import { CHARACTER, FIXED_STEP, Physics } from './physics';

export interface MoveIntent { forward: number; right: number; run: boolean }
export type FootPosition = readonly [number, number, number];

/** A capsule is deliberately a Phase 1 scale marker; character assets arrive later. */
export class Player {
  readonly model = new Group();
  readonly position = new Vector3();
  readonly collider: RAPIER.Collider;
  private readonly body: RAPIER.RigidBody;
  private readonly controller: RAPIER.KinematicCharacterController;
  private readonly velocity = new Vector3();
  private readonly actualVelocity = new Vector3();
  private readonly corrected = new Vector3();
  private verticalVelocity = 0;
  private yaw = -Math.PI / 2;
  private grounded = false;
  private collisions: string[] = [];
  private disposed = false;

  constructor(readonly physics: Physics, scene: Scene, spawn: FootPosition) {
    this.body = physics.world.createRigidBody(
      RAPIER.RigidBodyDesc.kinematicPositionBased()
        .setTranslation(spawn[0], spawn[1] + CHARACTER.height / 2 + CHARACTER.offset, spawn[2])
        .lockRotations(),
    );
    this.collider = physics.world.createCollider(
      RAPIER.ColliderDesc.capsule(CHARACTER.height / 2 - CHARACTER.radius, CHARACTER.radius)
        .setFriction(0).setRestitution(0), this.body,
    );
    this.controller = physics.world.createCharacterController(CHARACTER.offset);
    this.controller.setSlideEnabled(true);
    this.controller.enableAutostep(CHARACTER.maxStep, CHARACTER.minStepWidth, false);
    this.controller.enableSnapToGround(CHARACTER.groundSnap);
    this.controller.setMaxSlopeClimbAngle(CHARACTER.maxSlope);
    this.controller.setMinSlopeSlideAngle(CHARACTER.maxSlope + 0.05);
    this.controller.setApplyImpulsesToDynamicBodies(false);

    this.model.name = 'CHR_player_greybox';
    const body = new Mesh(
      new CapsuleGeometry(CHARACTER.radius, CHARACTER.height - 2 * CHARACTER.radius, 6, 12),
      new MeshStandardMaterial({ color: 0x8b2e2e, roughness: 1, metalness: 0 }),
    );
    body.name = 'CHR_player_capsule';
    body.position.y = CHARACTER.height / 2;
    body.castShadow = true;
    body.receiveShadow = true;
    this.model.add(body);
    const visor = new Mesh(
      new BoxGeometry(0.36, 0.12, 0.055),
      new MeshStandardMaterial({ color: 0x3ec7c2, roughness: 0.9, emissive: 0x102623 }),
    );
    visor.name = 'CHR_player_forward_marker';
    visor.position.set(0, 1.43, -0.335);
    this.model.add(visor);
    scene.add(this.model);
    this.teleport(spawn);
  }

  /** Root owns the accumulator; each invocation advances exactly one fixed physics tick. */
  update(dt: number, intent: MoveIntent, cameraYaw: number) {
    const length = Math.max(1, Math.hypot(intent.forward, intent.right));
    const forward = intent.forward / length;
    const right = intent.right / length;
    const speed = intent.run ? CHARACTER.runSpeed : CHARACTER.walkSpeed;
    const targetX = (-Math.sin(cameraYaw) * forward + Math.cos(cameraYaw) * right) * speed;
    const targetZ = (-Math.cos(cameraYaw) * forward - Math.sin(cameraYaw) * right) * speed;
    const moving = Math.abs(forward) + Math.abs(right) > 0.001;
    const response = 1 - Math.exp(-(moving ? 20 : 28) * dt);
    this.velocity.x += (targetX - this.velocity.x) * response;
    this.velocity.z += (targetZ - this.velocity.z) * response;
    if (this.velocity.lengthSq() < 0.00001) this.velocity.set(0, 0, 0);
    this.verticalVelocity = this.grounded ? -2 : Math.max(-30, this.verticalVelocity + CHARACTER.gravity * dt);
    this.controller.computeColliderMovement(this.collider, {
      x: this.velocity.x * dt,
      y: this.verticalVelocity * dt,
      z: this.velocity.z * dt,
    }, RAPIER.QueryFilterFlags.EXCLUDE_SENSORS);
    this.controller.computedMovement(this.corrected);
    this.grounded = this.controller.computedGrounded();
    if (this.grounded) this.verticalVelocity = -2;
    const current = this.body.translation();
    this.body.setNextKinematicTranslation({
      x: current.x + this.corrected.x,
      y: current.y + this.corrected.y,
      z: current.z + this.corrected.z,
    });
    this.collisions = [];
    for (let i = 0; i < this.controller.numComputedCollisions(); i++) {
      const collision = this.controller.computedCollision(i);
      if (!collision?.collider) continue;
      const name = this.physics.colliderName(collision.collider);
      if (!this.collisions.includes(name)) this.collisions.push(name);
    }
    this.physics.step(dt);
    this.actualVelocity.copy(this.corrected).divideScalar(dt);
    if (moving) {
      const desiredYaw = Math.atan2(-targetX, -targetZ);
      const difference = Math.atan2(Math.sin(desiredYaw - this.yaw), Math.cos(desiredYaw - this.yaw));
      this.yaw += difference * (1 - Math.exp(-16 * dt));
    }
    this.sync();
  }

  teleport(position: FootPosition) {
    if (!position.every(Number.isFinite)) throw new Error('Player position must contain three finite coordinates.');
    const translation = { x: position[0], y: position[1] + CHARACTER.height / 2 + CHARACTER.offset, z: position[2] };
    this.body.setTranslation(translation, true);
    this.body.setNextKinematicTranslation(translation);
    this.velocity.set(0, 0, 0);
    this.actualVelocity.set(0, 0, 0);
    this.verticalVelocity = 0;
    this.grounded = false;
    this.collisions = [];
    this.physics.step(FIXED_STEP);
    this.sync();
  }

  private sync() {
    const translation = this.body.translation();
    this.position.set(translation.x, translation.y - CHARACTER.height / 2, translation.z);
    this.model.position.copy(this.position);
    this.model.rotation.y = this.yaw;
  }

  get snapshot() {
    return {
      x: this.position.x, y: this.position.y, z: this.position.z, yaw: this.yaw,
      grounded: this.grounded,
      speed: Math.hypot(this.actualVelocity.x, this.actualVelocity.z),
      velocity: { x: this.actualVelocity.x, y: this.actualVelocity.y, z: this.actualVelocity.z },
      collisions: [...this.collisions],
    };
  }

  dispose() {
    if (this.disposed) return;
    this.disposed = true;
    this.physics.world.removeCharacterController(this.controller);
    this.physics.world.removeRigidBody(this.body);
  }
}
