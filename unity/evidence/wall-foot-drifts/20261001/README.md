# Wall-foot sand and grounding — evidence (1 October 2026)

Pass: `Assets/AthenHill/Editor/WallFootDriftsPass.cs`; sources, run order and licences:
`art/wall_foot_drifts_20261001/README.md`. Batch 3 of the 1 Oct programme. Not accepted by Carl.

## What changed in the saved scene

- New root **Ward wall-foot drifts**: 334 prefab instances (Run_L 56, Run_M 83, Run_S 105, Run_Low 19, Corner_L 6,
  Corner_S 25, Post 20, Sheet 20) and 320 decal projectors (band 134, skirt 123, sheet 43, post 20) in 13 groups.
- New root **Wall-foot drift review cameras** (8 disabled cameras, below).
- Nothing retired, no collider, light or render-chunk source changed (`install.json`: chunk fingerprint unchanged).
- Rollback: `rollback/before-wall-foot-drifts.unity` (the saved scene just before the install).

## Numbers

- Triangles summed over all instances: LOD0 140,418 / LOD1 34,704 / LOD2 11,140 (a view only draws the nearby banks at
  LOD0: LOD0 within ~10 m, LOD1 to ~28 m, LOD2 to ~60 m, culled beyond). 0 shadow casters, 0 colliders, 0 lights.
- Materials: 1 opaque (URP Lit, `WFD_Sand`) + 4 decal materials (one angle-fading decal shader graph, instancing on).
  Decal draw distance 40 m (district cap 45 m).
- Textures (streamed, compressed): sand 2k DXT1 + 2k BC5 normal, two 2048x512 and two 1024² BC7 decals, ≈ 13 MB with mips.
- Frame time: **not measured by this pass** (revised Definition of done: the orchestrator's combined A/B).

## Verification

- `verify-saved-scene.json` (-nographics): installed, active, 334/334 prefab-linked, no non-uniform scale, 0 missing
  materials, 0 shadow casters, 0 colliders, 0 lights, 320/320 decals with material, max decal draw distance 40,
  chunk fingerprint matches, chunks not in editing mode, 8/8 review cameras (all disabled).
- Placement: `art/wall_foot_drifts_20261001/layout.py` validated every piece against colliders, chunk-drawn renderers and
  props (8 cm), the surface level under its visible sand, routes, NPC/landmark points, stair/hall-step approaches, the
  terminal slab, the Basic General counter and the West Gate arches: 0 problems (`audit.json.gz`, 16:08). Re-checked the
  installed layout against a post-install audit (`audit-after-install.json.gz`, 17:03, includes other passes' work up to
  then): 0 problems (`art/wall_foot_drifts_20261001/review/validate-installed.json`).

## Review cameras (eye 1.62 m above the street, or above the deck where noted)

| Camera | Shows |
| --- | --- |
| `cam_wfd_field_step` | Field Supply porch front and step corner (windward east-row front): banks, step-end pockets, ground film |
| `cam_wfd_finery_deck` | Finery porch deck from the deck (eye 1.6 m above it): pier feet, door and planters clear |
| `cam_wfd_alley` | Finery / Field Supply alley: banks on both walls, thin sand floor, wall skirts |
| `cam_wfd_cross_street` | west cross street along the Tool Exchange side riser |
| `cam_wfd_hill_cheek` | hill north stair: cheek corner bank, plinth foot, stair kept clean |
| `cam_wfd_hall_podium` | Vanguard Hall podium west face (windward) |
| `cam_wfd_rear_lane` | west service lane: windward rear walls, a pole collar |
| `cam_wfd_lamp` | avenue utility lamp footing: collar and lee tail |

## Editor captures (MainCamera clone, saved clock, 1920x1080; never saved)

- `editor-r1/` (off/on pairs, `*-pair.jpg` = off left, on right): first look. Sand and films far too pale and grey
  (read as snow in shade), hard decal ends, ground films painted on the porch risers (the shared decal graph has no angle
  fade), stair-stepped toe on the step tread (pieces placed 4 mm above the real tread).
- `editor-r2/`: recalibrated sand, own angle-fading decal graph, soft-ended decals, smooth kit fields, probed deck/tread
  levels. `editor-r3/`: feathering film profile, density +, camera fixes.
- `editor-installed/`: the saved scene after the install, off/on pairs for the hill cheek, alley and lamp.
- Peak VRAM of the capture runs 7.9–9.8 GB (system), ≤ 6 cameras per run.

## Known remaining defects

- Porch decks carry little sand (doors, bays and dressed frontages are kept clear by rule).
- Post collars can read as soft discs from some angles; lee tails are subtle.
- Night look (20:30), native player look, motion/LOD transitions and frame cost are unreviewed by this pass.
- Unity's DataStore logged "Failed to free block" pool warnings during one capture run (engine-internal; captures fine).
