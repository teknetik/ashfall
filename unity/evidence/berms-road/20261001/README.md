# Berms road ground to V2 — evidence (1 October 2026)

Pass: `Assets/AthenHill/Editor/BermsRoadPass.cs`, sources and run order in `art/berms_road_20261001/README.md`.
Working tree on branch `ward/next-level` (uncommitted, on top of 3ebd801b plus the other 1 Oct passes). Installed into the
saved scene at 2026-10-01 14:54 UTC; cameras and the cairn shadow tune at ~15:02 UTC.

## What changed in the scene

- `Outer Berms/Berms ground`: material `Art/WestGate/Ground/BermsGround.mat` → `Art/BermsRoad/Ground/BermsGroundV2.mat`
  (shader *Athen Hill/Berms Ground V2*). Mesh and collider unchanged (`Art/OuterBerms/BermsGround.asset`, 4,635 vertices,
  8,976 triangles, same asset on MeshFilter and MeshCollider). Shadow casting stays off (as before).
- New `Outer Berms/Berms road edge stones`: 24 edge stones + 2 cairns (6 rocks each), 36 prefab instances of the West
  Gate `PH_RockA–D` (Poly Haven namaqualand rocks), uniform scale 1.7–2.7. LOD0 180k triangles if all were at LOD0
  (5k each; LOD0 only within ~3.6 m of a 0.5 m stone), LOD1 45k (1.25k each, culled beyond ~25 m). Edge stones: no
  collider, no shadows (as the West Gate scatter). Cairns: one box collider each (0.89 × 0.81 × 0.84 m and
  0.76 × 0.74 × 0.80 m), shadow casting on (12 rocks × 2 LODs). **No lights.**
- Player `FootstepAudio` Berms map rebaked from the new splat (88 × 204 cells: sand 16,244, gravel 1,708; 220 cells
  changed). Previous grid: `footsteps-before.json`.
- New root `Berms road review cameras` (8 disabled cameras, see below).
- Not touched: the training range (its `Backstop earth bank` keeps `BermsGround.mat`), basin mountains, perimeter walls,
  decals (they still project: the shader keeps DBuffer decals), routes, encounters, salvage nodes, landmarks, tutorial.

## Verification (`verify-saved-scene.json`, -nographics)

Material is V2, shader supported, 0 shader errors, 0 missing textures; ground mesh and collider unchanged; earth bank
still on the old material; 36 prefab instances, 0 broken links, 0 missing materials, uniform scale; 0 floating stones
(every LOD0 bottom at or below the ground); landmarks unmoved (14); 3 encounters, 3 tutorial targets; footstep map
17,952 cells; render-chunk fingerprint matches, not in source-editing mode; 8 review cameras.
Layout check (`art/berms_road_20261001/layout-check.json`): every stone outside the graded road width + 0.2 m, off the
pull-off spurs, ≥ 0.5 m from colliders, ≥ 2.2 m from markers (cairns ≥ 3 m), ≥ 0.35 m from the West Gate scatter;
16 candidate positions rejected (outpost props, landmarks, scatter, depot apron, spurs). `ok: true`.

## Captures (editor, MainCamera clone with post, 1920 × 1080, scene's saved key light; not native)

- `before-editor/` — the 6 first `cam_br_*` poses on the old material (`cam_br_west_slope` before is an earlier,
  higher-aimed pose; the camera was lowered afterwards).
- `preview-1…3/` (JPEG) — three material iterations applied in memory, not saved; `preview-4-wide/` — the existing
  wide cameras (`cam_berms_road`, `cam_berms_overview`, `cam_depot_approach`, `cam_berms_depot`,
  `cam_bm_berms_west_toe`, `cam_bm_toe_south_edge`) on iteration 3.
- `after-editor/` — the installed saved scene: all 8 `cam_br_*`, plus `cam_range_backstop`, `cam_range_overview`
  (earth bank vs new floor), `cam_bm_berms_west_toe`, `cam_berms_overview`.
- `before-after-sheet.jpg` — matched before/after pairs.

## Numbers (estimates, not measured — the orchestrator's combined test measures frame time)

- Ground shader cost: the old shader sampled all four layers (two taps for the base) plus the splat and three geology
  taps in **both** the forward pass and DepthNormals (~15 + ~15 samples per pixel). V2 samples only the layers with
  weight (index bombing adds a second tap only in blend zones): typically 15–20 in the forward pass, and 3 (splat-2
  relief) in DepthNormals. Expected cost about equal or lower; rock pixels on the slopes add the V2 rock taps.
- Texture memory: +2 × 5 × 2048² BC7 arrays (~53 MB with mips), splat 1 BC7 (~2.8 MB), splat 2 RGBA32 (~11 MB): ~67 MB.
  The old Berms arrays stay resident (earth bank, basin V2/V3 use them).
- Stones: 36 LODGroups; typical view ~3 LOD0 + ~30 LOD1 ≈ 50k triangles; 24 shadow-casting cairn renderers (12 LOD0/1 pairs).

## Review cameras (for the combined lookbook)

`cam_br_road_bend`, `cam_br_road_south`, `cam_br_road_close`, `cam_br_depot_approach`, `cam_br_west_slope`,
`cam_br_road_back`, `cam_br_edge_stones`, `cam_br_cairn` (root `Berms road review cameras`, eye = ground + 1.6–1.7 m).

## Known defects / remaining work

- The outer 7 m band reproduces the basin V3 look on purpose (seamless toe), so where it is steep it shows the V2
  SandstoneAlbedo "marbled" swirls, which read poorly at player height (`after-editor/cam_bm_berms_west_toe.png`); the
  same look is the basin's own close-up texture. Inside the floor, slopes stay scree (rock only above slope 0.18).
- Floor colour is paler and less saturated than the old orange (by design closer to the basin's V2 scree/sand values);
  check at 13:00/20:30 natively. Off-road flats are still fairly plain at mid distance; the desert-pavement lag
  patches are subtle.
- Windrows and the crown use `floor_pebbles_01` (rounded pebbles); at close range they read slightly like garden gravel.
- Edge stones/cairns are the cool-grey namaqualand scan; they read darker than the warm floor. The cairns are small
  (0.65 m) and only 2 (the outpost bend had no free spot clear of the scatter and props).
- No edge stones between the outpost and the checkpoint bend (the West Gate scatter already lines that stretch).
- Not measured: native frame time, 20:30 look, city loop, range tutorial (orchestrator's combined test).
