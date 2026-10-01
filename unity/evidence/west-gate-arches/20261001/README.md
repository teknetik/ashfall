# West Gate arches — evidence (1 October 2026, batch 2)

Pass: `art/west_gate_arches_20261001` (README: what is built, run order, sources and licences) and
`Assets/AthenHill/Editor/WestGateArchesPass.cs`. Review item 4 of the 30 Sep art-direction pass ("the arches are
blind"). Installed into the saved scene after the orchestrator's go-ahead (batch-1 build taken, 15:10).

## What changed in the scene

- New root **Ward west gate arches**: `West gate arch A (spawn, wicket)` at (48, 0, 0) and `West gate arch B` at
  (48, 0, 12), prefab instances of `Prefabs/WestGateArches/WGA_GateA/B.prefab` (identity rotation, scale 1).
- New root **West gate arch review cameras**: `cam_wga_spawn`, `cam_wga_front`, `cam_wga_close`, `cam_wga_wicket`,
  `cam_wga_head`, `cam_wga_threshold` (disabled cameras, eye 1.5–1.65 m).
- Two spot lights (`.../Bulkhead light`, unshadowed, 7.5 m, intensity 3) added to `CityLightCircuit.practicalLights`
  and `nightOnlyLights`.
- Nothing retired; no saved collider, render-chunk source or Meshy arch changed (chunk fingerprint matches).
- Scene before the install: `rollback/before-west-gate-arches.unity` (14:57 save). `install.json` is the first
  install (15:36); `reinstall.json` (15:41) is the authoring reinstall after a decal fix (lights unhooked and re-added).

## Verification (`verify-saved-scene.json`, -nographics, 15:41)

installed and active; 2 gates, both prefab-linked, uniform scale; 30 renderers, 0 missing materials; 16 decal
projectors with materials; 6 colliders (two sealing boxes 0.52 × 6.9 × 4.95 m at x 48.4–48.9, four guard-stone
boxes); 2 lights, both on the circuit; spawn clearance 4.14 m, Vex 4.87 m from the nearest new collider; chunk
fingerprint matches, not editing sources; both Meshy `District gate` instances active; 6 review cameras.

Triangles per arch (LOD0 / LOD1 / LOD2): A 25,436 / 11,268 / 1,508; B 24,184 / 10,112 / 1,388. Shadow casters: the
Leaves group (boards, skin, frame, bar, transom, grille) and the guard stones at each LOD; hardware, lamp and bands off.

## Layout validation

`art/west_gate_arches_20261001/layout.py` against `audit-before.json` (fresh audit, 15:10): 6 collider footprints vs
saved colliders, NPC points, routes, landmarks and the spawn: **0 problems** (they touch only the Meshy arch's mesh
collider and the ground). Cart passage between the guard stones 4.36 m (tunnel 4.93 m). Map:
`art/west_gate_arches_20261001/review/layout-map.png`.

## Review

- Blender Cycles renders fitted inside the real arch geometry (flat colours): `art/west_gate_arches_20261001/review/r1`
  (spawn, close three-quarter, wicket, head, guard stone, hinge/pintle; LOD1/LOD2 mid and far; arch B front and back).
- Editor captures, scene lighting as saved (no clock), MainCamera clone with post-processing:
  `editor-pre1/` (gates placed in memory before the install), `editor-after/` (installed, 6 cams, `sheet.jpg`),
  `editor-after2/` (spawn, front, threshold after the stencil-depth fix).
- Fixed during review: guard stones came out blue-grey (the masonry kit's 2–4 m hue drift on two small stones; now a
  warm tint without drift), the KEEP CLEAR stencil printed only on the frame members (projector box stopped 5 mm short
  of the boards), over-worn stencil, bar position clear of the middle pintles, z-fighting cover strip and stirrups.

## Not measured here

Per the revised definition of done, no player build, native lookbook, A/B profile or city loop was run by this pass;
frame time, the 20:30 look and the city loop are for the orchestrator's combined test. Expected cost: two LOD groups
(~25k triangles each only within ~15 m), two unshadowed spot lights, 16 decal projectors (40 m draw distance).

## Known remaining defects

- Night look unverified: the bulkhead intensity/range are a first guess; the lens (`VH_LampLens`) renders white in the
  editor captures (the light circuit dims it by day at runtime).
- The gate number decal on the transom is small (~0.15 m) and easy to miss.
- The rut decals are subtle at noon; no normal-mapped groove.
- Guard stones are plain tapered blocks with a pyramid cap, not carved chasse-roues.
- The outer (strip-side) faces are a plain riveted skin; they are unreachable and only visible from high cameras.
- No moving walkthrough or LOD-transition review (LOD0→1 at ~15 m, LOD1→2 at ~45 m).
- The Meshy arch itself (non-uniform fitted scale, soft 1k atlas tile) is unchanged.

## Needs Carl's decision

- "WEST GATE" is signed on these +X arches, which the compass puts on the east side, and also on the -X Berms gantry.
  The gate was not renamed.
- The sealing colliders make the strip behind the rampart (x 49.7–58) unreachable; nothing there was in use.
