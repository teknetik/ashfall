# Basic General - counter stock and service-recess dressing (task t_84b69b7e, 29 Sep 2026)

Status: **source-render reviewed only.** Nothing here is installed in Unity, native-verified or accepted. Blender/Cycles
renders are source evidence, not the game's render. Unity integration, collision/interaction checks, shade readability and
frame time belong to `game-dev` (child card t_7f421ed1).

No Meshy task was run and **no Meshy credits were spent**. Everything is original geometry authored in Blender 5.2.1 with
procedural numpy PBR maps (project original, no third-party imagery, no generative text). The building v1-v3 sources and the
Unity prefab are untouched; the review `.blend` is a copy of the v3 scene with the new modules added.

## What is delivered

Six modules, building-local metres, front = +Z, identity rotation, uniform scale 1:

| Part | Tris LOD0 | LOD1 | Size X x Y x Z (m) | Content |
| --- | --- | --- | --- | --- |
| BGC_Counter | 5,884 | none (small) | 4.245 x 0.949 x 0.510 | box, steel-clad top with rolled nosing, 3 bays with pressed inset frames and stiffener ribs, hatch handle, hasp + padlock, domed fixings, rubber guards/kick strip, banked dust |
| BGC_ShelfBay_L | 11,606 | 4,874 | 0.740 x 0.935 x 0.324 | two steel shelves (rolled lip, down-turn, gussets, back angle, bottle-stop rail), olla jar, 3 flasks, canteen, 3 medkits, roll pack, tags, dust |
| BGC_ShelfBay_R | 14,478 | 6,080 | 0.811 x 0.908 x 0.219 | two shelves, three wire hanks (continuous strand, twine ties), wire spool, ochre cable coil, canteen, 3 flasks, medkit, tags, dust |
| BGC_HookRail_L | 8,162 | 3,427 | 0.817 x 0.415 x 0.158 | wall rail + 5 S-hooks: sling canteen, bottle, hung kit, tag, wire hank |
| BGC_HookRail_R | 9,994 | 4,197 | 0.859 x 0.487 x 0.155 | wall rail + 5 S-hooks: slate cable coil, roll pack, 2 hanks, tag, red flask |
| BGC_CounterProps | 12,776 | 5,358 | 2.600 x 0.313 x 0.397 | flask rack + 3 flasks, medkit stack, ledger, cash tin, receipt spike + slips, sale mat + hank, brass balance scale, loose slips, dust |

Total 62,900 triangles at LOD0 (29,820 if every part uses LOD1 where one is provided), replacing 90 objects / 59,754 triangles of v3 stock,
counter plates, rivets and wear decals. The count is unchanged, but it is spent on distinct shapes at reading distance.
The counter is the only part without LOD1. The dressing sits within 0.51 m of the rear wall.

Saleable shapes: sealed water flasks (three silhouettes, wax-sealed, twine-wrapped, printed paper sleeves), a porous clay
olla, pilgrim canteens with webbing slings, medkits (bone, olive, red; latched, handled), copper wire hanks and a spool,
slate/ochre cable coils, roll packs. Product names are not lettered anywhere: paper carries printed rule bands, tally ticks
and a stamp ring only, so nothing depends on generated text. The existing wall title "WATER / SUPPLIES / SALVAGE" and the
sign are untouched.

Materials respond differently: satin painted steel with chipped edges and rust halos, bare brushed steel, brass, enamel
(6 tints), rubber, clay, kraft paper, webbing, copper (verdigris), cable sheath, twine, settled sand.
Merchant details: shelf lips/brackets, worn painted counter with a polished forearm band, palm patches and slide streaks,
oil rings and weld joins on the counter top (unique 4096x512 map, 966 px/m), scuffed kick zone and bolt rust weeps on the
face (unique 4096x1024, 966 px/m), banked dust.

## Files (all under `art/quality_20260929/basic-general-counter/`)

- Source: `basic-general-counter-source-v1.blend` (v3 building + new modules; superseded stock hidden by custom property
  `bgc_retired`, list in text block `bgc_retired_objects.txt`), `...-with-lods.blend` (plus hidden `_LOD1` duplicates).
- Scripts (re-runnable, deterministic): `make_textures.py`, `bgc_lib.py`, `build_bgc.py`, `export_bgc.py`, `qc_reimport.py`,
  `measure_bgc.py`, `render_review.py`, `render_lod.py`, `compose_*.py`, `make_handoff.py`, `regen_all.sh`, `bl.sh`
  (**runs Blender with a clean PATH**: the Hermes python shadows Blender's own and breaks it).
- Exports: `exports/glb/*.glb` (11 files, Y-up, no embedded images), `exports/interchange/bgc-meshes-v1.json`
  (same layout as the v3 interchange, with per-material submeshes).
- Textures: `textures/BGC_*` (53 PNG, 181 MB) and `textures/manifest.json` (sha256, sizes, seeds).
- Handoff data: `handoff.json` (per-part pivots, placement, guidance), `materials.json` (URP mapping), `measurements.json`,
  `qc-report.json`, `old-stock-stats.json`.
- Evidence: `renders/` (41 PNGs).
  - Eye height 1.6 m: `new_lit_eye_approach`, `new_eye_porch_left/right`, `new_nomira_*`, `new_over_counter`.
  - Old vs new (left/right): `compare_door`, `compare_door_mira`, `compare_eye_approach`, `compare_eye_porch_left/right`, `compare_over_counter`.
  - Sections/scale: `new_side_section_left/right`, `new_measure_front`.
  - Material close-ups: `new_close_*` (bays, hooks, counter face/top, steel).
  - LOD: `compare_lod_3m_near/6m/12m` (LOD0 | LOD1 | 8x difference). Overview: `contact_sheet_new`.

## Placement (for game-dev)

Building pivot Unity (8, 0.5, 15.1), front +Z. Authoring frame: +X is screen-right from the avenue; glTFast's X flip means a part
authored at A-space pivot `(px,py,pz)` goes to building-local `(-px, py, pz)`. Use `handoff.json` -> `parts[].pivotUnityLocalToBuilding`
(and `pivotUnityWorld_atBuildingPivot_8_0p5_15p1`). Check by eye: counter against the rear wall, left bay (from the avenue) holds the olla
jar and blue canteen, right bay holds copper hanks and the green spool. If it is mirrored, the conversion was applied twice.
Pivots: Counter (0,0,-1.10); ShelfBay_L (-1.72,0,-1.10); ShelfBay_R (1.72,0,-1.10); HookRail_L (-0.88,0,-1.10); HookRail_R (0.88,0,-1.10);
CounterProps (0,0,-1.10) - all on the rear-wall face at porch level.

Keep: the two "Stock recessed cabinet" back panels (shelves stand in front of them), the wall title, sign, awning, masonry, porch/step,
all six colliders, Mira. Hide (not delete) the superseded renderer prefixes listed in `handoff.json.supersedesByNamePrefix`.

## Measurements against the 1.8 m actor and the kiosk

Counter top 0.94 m (0.52 x the 1.8 m actor), width 4.24 m (0.77 of the 5.5 m kiosk width), depth 0.51 m.
Shelves at 1.01 m and 1.49 m; hook rails at 1.80 m; the tallest item is 1.825 m above the porch, and the wall title sits above it at about 2.0 m.
Mira's root is 1.29 m from the nearest new geometry (plan). **No new geometry lies in the 0.9 m-wide corridor from Mira to 2.4 m out (the
`interactionRange`).** The nearest item to the player approach is the counter nosing at Z = -0.59, 1.29 m behind Mira.
Nothing enters the awning, side or first-step colliders. Vertices touch the back-collider volume only as the 0.025 m wall-contact embed
(the collider's front face is the wall face where the dressing sits). No source object grows past the rear service relief, and no uniform
or non-uniform object scale is baked: every object has scale (1,1,1) and determinant > 0 (verified on re-import).

## Verification done (Blender only)

- Every GLB was re-imported into a clean scene: triangle counts and bounds match the source to within 2 triangles / 0.002 m; scale 1;
  no negative determinants; UV0 finite, present, **0 degenerate UV triangles**, no loose vertices (`qc-report.json`).
- Non-manifold edges are reported, not failed: bottles, coils and tubes are open/intersecting by construction (modular props, no bake).
- Rendered from the requested cameras with a 1.8 m Mira proxy at her real root, and repeated with the proxy removed.
- LOD1 (collapse decimation, delimited by material/UV seam) was compared with LOD0 in Blender renders at 3, 6 and 12 m. RMS image
  difference is 0.034 / 0.018 / 0.009; the 8x-amplified difference sits on thin twine, hook loops and coil edges, and I saw no silhouette
  break or hole in the renders. This is a judgement from source renders only; the switch distance (suggest LOD1 from about 5 m) is for game-dev to tune in Unity.

## What this does NOT establish (honest gaps)

1. **Not a Unity render.** Materials were wired with the URP channel convention but never loaded in Unity; check normal-map look, the
   Metal/Smooth alpha channel and shade readability there. The Blender fill light used in close-ups is a source-review light only.
2. **Shade.** The recess is dark in the 9 Sep native evidence. Geometry relief and warm tints help, but readability in native shade is untested.
   A modest practical light is an option for game-dev; nothing here relies on one. No emissive material is in the package.
3. **Texture memory is high.** 49 distinct maps are referenced = about 199 Mpx, which is roughly 253 MiB as BC7 with mips (about 1 GiB uncompressed).
   This is source resolution kept per the brief (no downsampling), not a target. The 6 enamel tints, 2 cable tints and 2 shelf tints each have
   their own BaseColor plus a shared Normal/Smooth; a trimmed runtime set should share tiles across the small props. **Measure in the native player
   and use mip streaming.** I did not test frame time.
4. **Triangle cost** is 62,900 for LOD0 in a 4 x 2 m view. That is plausible for a hero focal point but is unmeasured on the target GPU.
5. Small parts are modular and overlap by construction (twine ties round hanks, slings round canteens, wax on caps). I did not inspect every
   contact in wireframe; the non-manifold edge counts in `qc-report.json` are the only measure taken.
6. Mira's stand-in is a review proxy, not the real Ward Guard mesh; her actual silhouette will occlude a slightly different part of the middle bay.
   The middle bay/wall between the two shelf bays is intentionally the most open zone.
7. No visual acceptance, "AAA" or GTA6 claim: quality gates in AGENTS.md section 7 (native captures, real input, frame times) remain open.

## Rollback

Nothing outside `art/quality_20260929/` was written. To revert in Unity: re-enable the hidden v3 stock renderers and disable the new parts;
the prefab, scene, meshes, materials and source `.blend` files for v1-v3 are untouched.
