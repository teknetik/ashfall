# Quantum Tube goods nodes + conduit, and the converted container homes — 3 October 2026

## Quantum Tube (north wall, either side of the Ring Gate)

Replaces `Ward district retrofit/Quantum Tube conduit` (two white boxes with a flat cyan rectangle; a black pipe with
cyan rings on concrete posts). Lore kept: a goods conduit only — "NODE 07 / GOODS ONLY / NO PASSENGERS", a waist-high
cargo port with a roller lip, no door; it does not connect to the Ring Gate.

- **Nodes** (`TubeNode`, 2 instances at world (±9, 0, 40.8), yaw 180, root `Ward building: Quantum Tube nodes`): Ward
  ashlar base to 1.81 m with a string course, armoured node module (blackened-steel frame and rails, graphite panels,
  chamfered roof with heat-sink fins, antenna with a cyan tip), hazard-framed cargo port with a half-raised shutter and an
  inner LED, status screen, vertical cyan strip, flanged conduit collars on both sides (symmetric so one prefab serves
  both nodes), painted stencils, one always-on status glow light each.
- **Conduit bays** (`TubeSeg`, 7.25 m: armoured conduit with riveted jacket rings, cable tray with two cables, inspection
  hatch, status lamp, and an ashlar pylon with a steel saddle at the far end): four east of the gate from x 11.05
  (yaw 0) and two in the west run (yaw 180), root `… conduit (pylon bays)`.
- **Wall-hung spans** (`TubeSpan`, the same bay without a pylon, carried by a riveted cantilever bracket and strut from
  the north wall face): three in the west run over the container homes, where a pylon would stand inside a home, root
  `… conduit (wall-hung spans)`.

Cameras (root `Ward buildings review cameras: Quantum Tube`): `cam_wb_tube_gate` (from the Ring Gate), `_node_e`,
`_port`, `_node_w`, `_run_e`, `_span_w`. Known gaps: the west-run bays' inspection hatches faced the wall (yaw 180) — fixed in round two (hatches on both sides).

## Converted container homes (wall feet)

Replace `Ward district retrofit/Perimeter dwellings` (bare containers, one floating stack). Three prefabs:
`WallHomeA` (rust), `WallHomeB` (blue, stacked with a rust upper container, an external steel stair and a landing that
shelters the lower door), `WallHomeC` (sand). Each: a 20 ft container with modelled vertical corrugation, posts, rails,
castings and end doors, on dressed stone pads; a cut-in steel door with a welded frame, a barred window with a louvred
shutter and rain hood, a stone step and a low stone planter, a canvas awning on poles (A/C), rooftop solar panel on a
raked frame, water drum, cables and junction box, AC unit, laundry line with cloth, a porch light on the clock.

| Instance | Prefab | World position | Yaw |
| --- | --- | --- | --- |
| Wall home south 1 (stacked) | WallHomeB | (19, 0, −41.6) | 0 |
| Wall home west (stacked) | WallHomeB | (−56, 0, −24) | 90 |
| Wall home south 2 | WallHomeA | (27.5, 0, −41.4) | 0 (moved 1 m east of the old home to clear the stacked home's stair) |
| Wall home north 2 | WallHomeA | (−17.5, 0, 41.4) | 180 (moved 2.5 m east) |
| Wall home north 1 | WallHomeC | (−24, 0, 41.2) | 180 (moved 3 m east, clear of greenhouse A's door) |

Cameras (root `Ward buildings review cameras: wall homes`): `cam_wb_home_south`, `_stair`, `_north`, `_west`, `_porch`.
Known gaps: not enterable; the windows are dark interior-mapped glass; no per-home clutter beyond the drum and bucket.
