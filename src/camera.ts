import { PerspectiveCamera, type Scene, Vector3 } from 'three';

export const CAMERA_NAMES = ['cam_gate', 'cam_avenue', 'cam_hill', 'cam_grid', 'cam_whompah', 'cam_hero'] as const;
export type CameraName = typeof CAMERA_NAMES[number];
// Blender's 42 mm lens / 36 mm horizontal sensor at 16:9, in vertical degrees.
export const PROBE_VERTICAL_FOV = 2 * Math.atan(36 / (2 * 42) / (16 / 9)) * 180 / Math.PI;

// Phase 0 uses six actual cameras aimed at the same pipeline probe. Their city views arrive in Phase 1.
const PROBE_VIEWS: Record<CameraName, [number, number, number]> = {
  cam_gate: [-6, 3.5, 6],
  cam_avenue: [-4, 2.4, 6],
  cam_hill: [5, 3.5, 6],
  cam_grid: [4, 5, -5],
  cam_whompah: [-5, 2.8, -5],
  cam_hero: [0, 2.5, 4.2],
};

// Map north is negative Three.js Z. These are future landmark anchors, not authored city assets.
export const LANDMARKS: Record<string, [number, number, number]> = {
  probe: [0, 0, 0], hill_tree: [0, 0, 0], oa_hill: [0, 0, 0],
  shop_row_e: [16, 0, 0], shop_row_w: [-18, 0, 0], west_gate: [-48, 0, 0],
  vanguard_hall: [8, 0, -32], grid_kiosk: [0, 0, -38], whompah: [0, 0, 36],
  mission_slab: [-8, 0, -12], billboard: [8, 0, 5], east_wreck: [52, 0, 0],
  basic_general: [-8, 0, 10],
};

export class Cameras {
  readonly named: Record<CameraName, PerspectiveCamera>;
  readonly follow = new PerspectiveCamera(50, 1, 0.1, 220);
  active: PerspectiveCamera;

  constructor(scene: Scene) {
    this.named = Object.fromEntries(CAMERA_NAMES.map((name) => {
      const camera = new PerspectiveCamera(PROBE_VERTICAL_FOV, 1, 0.1, 220);
      camera.name = name;
      camera.position.set(...PROBE_VIEWS[name]);
      camera.lookAt(0, 1, 0);
      scene.add(camera);
      return [name, camera];
    })) as Record<CameraName, PerspectiveCamera>;
    this.follow.name = 'cam_anchor';
    scene.add(this.follow);
    this.active = this.named.cam_hill;
  }

  select(name: string) {
    if (!CAMERA_NAMES.includes(name as CameraName)) throw new Error(`Unknown camera: ${name}`);
    this.active = this.named[name as CameraName];
  }

  anchor(position: Vector3) {
    this.follow.position.copy(position).add(new Vector3(0, 2.8, 4.2));
    this.follow.lookAt(position.x, position.y + 1.5, position.z);
    this.active = this.follow;
  }

  resize(aspect: number) {
    for (const camera of [...Object.values(this.named), this.follow]) {
      camera.aspect = aspect;
      // Retain the landscape composition's horizontal coverage on narrow displays.
      const baseFov = camera === this.follow ? 50 : PROBE_VERTICAL_FOV;
      camera.fov = 2 * Math.atan(Math.tan(baseFov * Math.PI / 360) * Math.max(1, (16 / 9) / aspect)) * 180 / Math.PI;
      camera.updateProjectionMatrix();
    }
  }
}
