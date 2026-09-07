/** Map north is -Z; positions use metres and Y is up. Teleports specify feet. */
export type ColliderDef =
  | { name: string; kind: 'box'; position: [number, number, number]; halfExtents: [number, number, number]; rotation?: [number, number, number, number] }
  | { name: string; kind: 'cylinder'; position: [number, number, number]; radius: number; halfHeight: number }
  | { name: string; kind: 'halfspace'; position: [number, number, number]; normal: [number, number, number] };

export const LANDMARKS: Record<string, [number, number, number]> = {
  west_gate: [-43, 0, 0], hill_tree: [-4, 1.5, 0], oa_hill: [-4, 1.5, 4],
  shop_row_e: [16, 0.5, 9], shop_row_w: [-16, 0.5, 9], basic_general: [-8, 0.5, 16],
  vanguard_hall: [10, 0.5, -25.5], grid_kiosk: [0, 0.5, -36.5], lattice_jack: [0, 0.5, -36.5],
  whompah: [0, 0.5, 36], ring_gate: [0, 0.5, 36], mission_slab: [-8, 0.25, -12.5],
  billboard: [5, 1.5, -5], east_wreck: [51, 0, 0], probe: [-52, 0, 23.5],
};

export const LANDMARK_LABELS: Record<string, string> = {
  west_gate: 'West Gate', hill_tree: 'Hill Tree', oa_hill: 'Hill Plaza',
  shop_row_e: 'East Shop Row', shop_row_w: 'West Shop Row', basic_general: 'Basic General',
  vanguard_hall: 'Vanguard Hall', grid_kiosk: 'Lattice Jack', lattice_jack: 'Lattice Jack',
  whompah: 'Ring Gate', ring_gate: 'Ring Gate', mission_slab: 'Mission Slab',
  billboard: 'Hill Beacon', east_wreck: 'East Wreck', probe: 'Blender Probe',
};

/** Grounded route checkpoints for keyboard traversal QA. Stairs are actual .25 m steps. */
export const WALK_ROUTE: Array<{ name: string; position: [number, number, number] }> = [
  { name: 'west_gate', position: [-43, 0, 0] },
  { name: 'west_stair_approach', position: [-12, 0, 0] },
  { name: 'hill_tree', position: [-4, 1.5, 0] },
  { name: 'hill_southwest', position: [-4, 1.5, 4] },
  { name: 'south_stair_top', position: [0, 1.5, 4] },
  { name: 'south_stair_bottom', position: [0, 0, 12] },
  { name: 'ring_approach', position: [0, 0, 31] },
  { name: 'ring_gate', position: [0, 0.5, 36] },
  { name: 'ring_departure', position: [0, 0, 31] },
  { name: 'west_lane_south', position: [-13, 0, 28] },
  { name: 'west_lane_north', position: [-13, 0, -29] },
  { name: 'lattice_approach', position: [0, 0, -31] },
  { name: 'lattice_jack', position: [0, 0.5, -36.5] },
];
