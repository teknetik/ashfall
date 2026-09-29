# Air + Water: three-filter mounts and fittings (task t_bd3d9fe3, 29 Sep 2026)

Status: **source-render reviewed only.** Nothing here is installed in Unity, native-verified or accepted. Blender/Cycles renders are
source evidence, not the game's render. Unity integration, collision checks, shade readability and frame time belong to `game-dev`.
No scene, prefab or Unity asset was touched; every file written is under `art/quality_20260929/airwater-filters/`.

No Meshy task was run and **no Meshy credits were spent**. All geometry is original, authored in Blender 5.2.1; the PBR maps are
procedural (numpy); lettering is Liberation Sans Bold (SIL OFL 1.1), rasterised as real text. No third-party or generative imagery.
No credit line is required.

## Scope

Only the three exterior cylindrical filter vessels right of the door and their visible connections. The canisters, retainer collars,
facade, door, awning, sign, roof, riser clamps/stand-offs/anchors, colliders and the 9 Sep surface pass are unchanged. Nothing is a
wall-wide pipe network, a roof change, a relight or a lore addition. There is no water simulation: the valve, gauge and drips are static geometry.

## What is delivered (5 modules, 36,152 triangles LOD0)

Building-local "A-space" metres: +X screen-right from the avenue, +Y up, +Z to the avenue, origin = building pivot, Y=0 porch top.
Identity rotation and uniform scale 1 on every object (verified on GLB re-import).

| Module | Tris | Size X x Y x Z (m) | Pivot (A) | Content |
| --- | --- | --- | --- | --- |
| AW_FilterMount_1 | 7,712 | 0.600 x 1.853 x 0.502 | (0.9, 0.5, 2.93) | Vessel 1: two 40 mm hoop straps with rubber liners, wall ears on sleeve anchors, tension lug with M8 through-bolt and two nuts; U-cradle under the bottom collar with two gusseted wall plates; curved FILTER 1 plate; HOSE outlet (union, elbow, hose tail, rubber hose, clamp); inlet union with gasket; mineral crust, stalactites, skin runs |
| AW_FilterMount_2 | 8,238 | 0.600 x 1.794 x 0.543 | (1.7, 0.5, 2.93) | Vessel 2: different strap heights and lug sides; cradle plates hand-fitted 30 mm higher and packed out over a plaster spall; FILTER 2 plate; CAPPED outlet (gasketed blanking cap); bolted gasketed FLANGE inlet with domed reducer |
| AW_FilterMount_3 | 7,446 | 0.600 x 1.969 x 0.502 | (2.5, 0.5, 2.93) | Vessel 3: FILTER 3 plate; 45-degree drain BEND ending in a four-bolt gasketed flange; inlet union, reducing bush and capped vent stub |
| AW_FilterHeader | 9,190 | 2.561 x 0.431 x 0.320 | (1.7, 2.12, 2.93) | New DN60 header replacing the old manifold and wall-mount bars: blanked end, three tees with dropped bosses, two anchored hangers, flanged isolation ball valve with red lever, bottom-entry pressure gauge (unique dial map), 45-degree set to the riser, ISOLATE plate (SHUT / OPEN) on the wall |
| AW_FeedRiser | 3,566 | 1.616 x 5.109 x 2.308 | (3.18, 2.12, 3.03) | Union at the header joint, elbow, riser at the existing axis with a gasketed four-bolt flange joint, roof turns, end flange at the existing roof pipe |

The three vessels differ on purpose: each has its own outlet type (hose, capped, bend), inlet type (union, flange, reducer + vent), strap
heights, lug sides and mineral pattern. Materials are separated: painted metal (`AW_Paint`), bare steel fasteners (`AW_Steel`), bronze
fittings (`AW_Bronze`), rubber seals/liners/hose (`AW_Rubber`), red enamel lever/flag (`AW_ValveRed`), mineral deposits (`AW_Mineral`), plus
unique maps for the service plates (`AW_Labels`, 4096 x 512 at 6000 px/m) and gauge face (`AW_Dial`, 1024 x 1024).

Every word is functional: FILTER 1/2/3, ISOLATE, SHUT | OPEN, BAR and numerals 0-6. Gauge: needle 2.6 bar, green 1.0-3.5, amber 3.5-4.5,
red 4.5-6.0, fixed red limit flag at 4.5. No lore, no invented names.

Reach: valve lever at y 2.12 m above the porch top, gauge centre y 2.262 m. Standing overhead reach for the 1.8 m figure is about 2.2 m, so
the lever is reachable at full stretch and the gauge readable from eye height (1.6 m) at about 0.6 m above it. No step is modelled.

## Files

- Source: `airwater-filters-source-v1.blend` (old geometry in collection "Air + Water rev04 + surface pass (old)" with the eight superseded
  objects flagged `aw_retired`, new geometry in "AW filter fittings (new)"); `airwater-review-base.blend` (the 9 Sep geometry re-expressed in A-space, from
  `art/relay_airwater_surfaces_20260909/relay-airwater-surfaces-v2.blend`, which is never saved over).
- Scripts (deterministic, `bl.sh` runs Blender with a clean PATH): `build_base.py`, `make_aw_textures.py` + `aw_textures_base.py`, `aw_lib.py`,
  `build_aw.py`, `export_aw.py`, `qc_reimport.py`, `measure_aw.py`, `make_clearance_diagram.py`, `make_handoff_aw.py`, `render_review_aw.py`; `scratch/` holds probes.
- Exports: `exports/glb/*.glb` (5, Y-up, A-space, no embedded images), `exports/interchange/aw-meshes-v1.json` (per-material submeshes).
- Textures: `textures/AW_*` (24 PNG at up to 4096 x 2048), `manifest.json` (sha256, seeds), `layout.json` (label rectangles).
- Data: `handoff.json` (pivots, placement, retire list), `materials.json` (URP mapping), `measurements.json`, `qc-report.json`, `build-stats-raw.json`,
  `scene-inspection.txt`, `wall-recess-samples.json`.
- Renders (`renders/`, Cycles, AgX, noon sun and shade): `front` (1.6 m eye, 8.4 m out), `oblique` (right), `oblique_l` (left), `eye_valve`, `top`,
  `close_clamp` (**extreme close-up: strap tension lug, bolt, nuts, liner and anchor ear**), `close_valve` (valve, lever, gauge), `close_label`, `close_inlet`,
  `close_feed`, `close_foot`; `new_front_noon_scale.png` / `new_oblique_noon_scale.png` (1.8 m and 1.0 m rods; the 1.8 m figure stands beside the bank in the other
  renders); `clearance-diagram.png` (plan and elevation, door clearance); old/new comparisons `compare_<view>_<noon|shade>.jpg` (old left, new right);
  `old_*` renders are the 9 Sep geometry from the same cameras.

## Placement for game-dev

Building pivot Unity (-20.6, 0.5, 9.0), yaw 90. glTFast flips X: place a part with A pivot (px, py, pz) at building-local (-px, py, pz), identity rotation,
scale 1 (see `handoff.json` -> `parts[].pivotUnityLocalToBuilding`). Check by eye from the avenue: FILTER 1 is nearest the door, the valve, gauge and riser are at the far end.

Retire (disable, do not delete) eight prefab renderers: `air_water Filter manifold`, `Filter manifold inlet 0.9 / 1.7 / 2.5`, `Filter wall mount 0.9 / 1.7 / 2.5`, and
`Roof to filter downfeed`. Everything else stays. **Scene mismatch:** the saved scene instance already sets `m_Enabled = 0` on all 65 bank renderers (they
are baked into render chunks), so the retire step needs Show Sources for Editing, then the install, then Rebuild Render Chunks (unity/EDITING.md).

## Measurements and clearances (`measurements.json`)

- Nearest new geometry to the door is x = 0.552, 0.702 m from the masonry reveal (x -0.15) and 1.022 m from the leaf (x -0.47); the rev 04 manifold started at x 0.55, so
  nothing is added toward the door. The door approach and threshold (to z 3.14) are untouched.
- Front-most new geometry is z 3.23 (strap ears and cradle), 10 mm beyond the retained collar front (3.22) and 70 mm short of the porch walk zone start (z 3.30). Header front z 3.05, riser 3.10.
- Wall plane z 2.73, wall collider face z 2.70. The wall carries plaster spalls 43 mm deep (z 2.687); `wall-recess-samples.json` maps them and `build_aw.py` checks every plate against them.

## Verification done (Blender only)

- All five GLBs re-imported into a clean scene: triangle counts and bounds match the source (within 2 tris / 0.002 m), scale 1, no negative determinant, UV0 present and
  finite, **0 degenerate UV triangles**, no loose vertices. Non-manifold edges: mounts 1 and 2 none, mount 3 three, header 100, riser 60. They are reported, not failed: overlapping
  solids (bolts through flanges, nuts on studs) are intentional.
- Every map and render was inspected at full size, not only as thumbnails. Defects found and fixed in this pass: mineral collars read as floating fins on horizontal joints (now weighted to
  the underside and sunk into the fitting); flange crusts too thick (thinned); the strap tension lugs first faced the wall and were invisible (moved to the front); the dial, lever and label were checked legible in close-ups.
- Old vs new rendered from identical cameras at noon and in shade.

## What this does NOT establish (honest gaps)

1. **Not a Unity render.** Materials are wired with the URP channel convention but never loaded in Unity; shade look and normal-map orientation are untested. The Blender lights are source-review lights.
2. **Legibility at range.** The FILTER plates (170 x 60 mm) are readable within about 3 m; from the avenue they read as small bright marks. The gauge needle and ISOLATE plate need to be within about 2 m.
3. **Copper reads very orange** against the pale plaster in the noon comparisons; it is a strong change from the old dull brass header. If it is too loud in the native player, tint `AW_Bronze` down in the material, not the map.
4. **Texture memory:** 24 maps, about 85 Mpx referenced, roughly 108 MiB as BC7 with mips (432 MiB uncompressed). Source resolution is kept; trial 1024 tiles for rubber, steel and mineral with mip streaming. Not measured in Unity.
5. No LOD1 was authored; 36k triangles across five modules for a 3.5 x 2 m area. Small-part overlaps were checked visually, not in wireframe or a physics test.
6. The old silhouette is preserved: the header runs at the old manifold height (y 2.12) and the riser on its existing axis.
7. No visual acceptance, native capture, frame-time claim, "AAA" claim or gameplay verification. Source-view scores against AGENTS.md section 7 (composition 3.5, scale 4, material detail 3.5, lighting/depth 3, density/storytelling 3.5).

## Credit / task ledger and recoverables

- Meshy: none. Credits spent: 0. Task IDs: none. Other generative tools: none. Rights: all project original; Liberation Sans Bold is SIL OFL 1.1 (no attribution required for the rasterised text).
- Originals preserved and never saved over: `art/relay_airwater_surfaces_20260909/relay-airwater-surfaces-v2.blend`, revision-04 prefab, scene and chunk assets. The 9 Sep objects that these modules replace remain in the review `.blend`.
- Rollback: in Unity, re-enable the eight retired renderers and disable the five new parts; nothing was overwritten.
