import { MathUtils, PerspectiveCamera, type Scene, Vector3 } from 'three';
import type { Physics } from './physics';
import type { Player } from './player';

export { LANDMARKS } from './layout';
export const CAMERA_NAMES = ['cam_gate', 'cam_avenue', 'cam_hill', 'cam_grid', 'cam_whompah', 'cam_hero'] as const;
export type CameraName = typeof CAMERA_NAMES[number];
// Keep Phase 0's lens available for archived probe comparisons.
export const PROBE_VERTICAL_FOV = 2 * Math.atan(36 / (2 * 42) / (16 / 9)) * 180 / Math.PI;
export const NAMED_VERTICAL_FOV = 50;
const BOOM_DISTANCE = 4.2;

type View = { position: [number, number, number]; target: [number, number, number] };
export const CITY_VIEWS: Record<CameraName, View> = {
  cam_gate: { position: [-32, 9, 18], target: [-48, 3.4, 5] },
  cam_avenue: { position: [-12, 7, 34], target: [0, 9, -5] },
  cam_hill: { position: [23, 14, 27], target: [0, 9, 0] },
  cam_grid: { position: [-10, 6, -28], target: [0, 2, -38] },
  cam_whompah: { position: [13, 6.5, 26], target: [0, 3, 36] },
  cam_hero: { position: [-5, 3.4, 9], target: [0, 9, 0] },
};

export class Cameras {
  readonly named: Record<CameraName, PerspectiveCamera>;
  readonly follow = new PerspectiveCamera(50, 1, 0.08, 240);
  active: PerspectiveCamera;
  private physics?: Physics;
  private player?: Player;
  private readonly feet = new Vector3();
  private readonly target = new Vector3();
  private readonly direction = new Vector3();
  private orbitYaw = -Math.PI / 2;
  private pitch = 0.22;
  private distance = BOOM_DISTANCE;
  private obstructed = false;

  constructor(scene: Scene) {
    this.named = Object.fromEntries(CAMERA_NAMES.map((name) => {
      const camera = new PerspectiveCamera(NAMED_VERTICAL_FOV, 1, 0.1, 240);
      camera.name = name;
      camera.position.set(...CITY_VIEWS[name].position);
      camera.lookAt(...CITY_VIEWS[name].target);
      scene.add(camera);
      return [name, camera];
    })) as Record<CameraName, PerspectiveCamera>;
    this.follow.name = 'cam_follow';
    scene.add(this.follow);
    this.active = this.follow;
  }

  attach(physics: Physics, player: Player) {
    this.physics = physics;
    this.player = player;
    this.anchor(player.position);
  }

  get yaw() { return this.orbitYaw; }

  resetOrbit() {
    this.orbitYaw = -Math.PI / 2;
    this.pitch = 0.22;
    this.update(0, true);
  }

  orbit(deltaX: number, deltaY: number) {
    this.orbitYaw -= deltaX * 0.003;
    this.orbitYaw = Math.atan2(Math.sin(this.orbitYaw), Math.cos(this.orbitYaw));
    this.pitch = MathUtils.clamp(this.pitch + deltaY * 0.003, -0.3, 1.1);
    this.active = this.follow;
  }

  select(name: string) {
    if (name === 'follow') {
      this.active = this.follow;
      this.update(0, true);
      return;
    }
    if (!CAMERA_NAMES.includes(name as CameraName)) throw new Error(`Unknown camera: ${name}`);
    this.active = this.named[name as CameraName];
    if (this.player) this.player.model.visible = true;
  }

  anchor(position: Vector3) {
    this.feet.copy(position);
    this.active = this.follow;
    this.update(0, true);
  }

  update(dt: number, reset = false) {
    if (this.player) this.feet.copy(this.player.position);
    this.target.copy(this.feet);
    this.target.y += 1.5;
    this.direction.set(
      Math.sin(this.orbitYaw) * Math.cos(this.pitch),
      Math.sin(this.pitch),
      Math.cos(this.orbitYaw) * Math.cos(this.pitch),
    );
    const allowed = this.physics && this.player
      ? this.physics.cameraDistance(this.target, this.direction, BOOM_DISTANCE, this.player.collider)
      : BOOM_DISTANCE;
    this.obstructed = allowed < BOOM_DISTANCE - 0.01;
    // Pull in immediately to avoid a frame inside a wall; release the boom gently.
    this.distance = reset || allowed < this.distance
      ? allowed
      : MathUtils.lerp(this.distance, allowed, 1 - Math.exp(-7 * dt));
    this.follow.position.copy(this.target).addScaledVector(this.direction, this.distance);
    this.follow.lookAt(this.target);
    // Avoid filling the view with the inside of the scale marker in tight corners.
    if (this.player) this.player.model.visible = this.active !== this.follow || this.distance > 0.6;
  }

  get snapshot() {
    return {
      active: this.active.name,
      yaw: this.orbitYaw,
      pitch: this.pitch,
      desiredDistance: BOOM_DISTANCE,
      distance: this.distance,
      obstructed: this.obstructed,
      position: { x: this.follow.position.x, y: this.follow.position.y, z: this.follow.position.z },
      target: { x: this.target.x, y: this.target.y, z: this.target.z },
    };
  }

  resize(aspect: number) {
    for (const camera of [...Object.values(this.named), this.follow]) {
      camera.aspect = aspect;
      // Retain horizontal coverage when the browser is narrowed.
      const fov = 2 * Math.atan(Math.tan(NAMED_VERTICAL_FOV * Math.PI / 360) * Math.max(1, (16 / 9) / aspect)) * 180 / Math.PI;
      camera.fov = camera === this.follow ? Math.min(85, fov) : fov;
      camera.updateProjectionMatrix();
    }
  }
}
