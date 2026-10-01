# Berms road ground to V2 — 1 October 2026

Art-direction review item 12 (`next-wins.md`): the flat playable Outer Berms floor (road and range,
`Outer Berms/Berms ground`) was still on the 26 Sep *Berms Ground* material — a smooth orange road band
(`sandy_gravel_02` at 2.5 m tiles), the same plain scree everywhere else, and a 7 m fade to flat
SandstoneAlbedo at its edge — plainer than the basin's V2 slopes beside it. This pass gives the floor the basin's
V2 ground model plus a repainted road, and lines the road from the checkpoint to the depot with edge stones.

The ground mesh and its collider are not touched (same `Art/OuterBerms/BermsGround.asset` on the MeshFilter and the
MeshCollider). Routes, encounters, salvage nodes, landmarks and the training range are not moved. The range's
`Backstop earth bank` keeps the old `BermsGround.mat`.

## What changed

| Piece | Where | Notes |
| --- | --- | --- |
| Shader *Athen Hill/Berms Ground V2* | `unity/AthenHill/Assets/AthenHill/Shaders/BermsGroundV2.shader` | V2 natural ground (rock on slopes with Sandstone Cracks detail and strata, scree, sand with wind ripples; index-bombed, height-blended, detail fades to layer means with distance) + painted features from two splats + relief normals; URP PBR with live shadows, SSAO, Forward+ lights and DBuffer decals (the West Gate and range decals keep projecting); basin V3 haze; border band fades to the basin's look. No shadow caster (as before). |
| Material `BermsGroundV2.mat` | `Assets/AthenHill/Art/BermsRoad/Ground/` | Built from `material.json`; natural-ground values copied from `SandstoneBasinV3.mat` so the toe matches. |
| Layer arrays `BermsRoadLayers_AH/NRA.png` | same folder | 5 slices × 2048²: dry_ground_rocks, dense_sand (as before), **gravel_ground_01** (road wheel paths), dry_ground_01 (crust), **floor_pebbles_01** (loose gravel / desert-pavement lag). BC7. |
| Splats `BermsRoadSplat.png` (R road, G sand, B crust, A 1 − compaction) and `BermsRoadSplat2.png` (R loose gravel, G relief, B varnished-lag share of R, A smoothed slope) | same folder | 1024 × 2048 over x −104…−60, z −54…48 (the old rect). Off the road, splat 1 is the West Gate painting reproduced exactly. |
| Edge stones and cairns | scene `Outer Berms/Berms road edge stones` | 24 Poly Haven namaqualand rocks (West Gate `PH_RockA–D` prefabs, uniform scale 1.7–2.6, sunk 28–45 %, no collider, no shadow) just outside the graded shoulders from the checkpoint bend to the depot yard; 2 cairns (6 rocks, 0.65 m) on the outside of the two bends, one box collider each, shadows on. No lights. |
| Footstep map | `Player` → FootstepAudio | Rebaked from the new splat with the CharacterFeelPass rule (+ loose gravel heard as gravel). Previous grid: `unity/evidence/berms-road/20261001/footsteps-before.json`. |
| Review cameras | scene root `Berms road review cameras` | `cam_br_road_bend`, `cam_br_road_south`, `cam_br_road_close`, `cam_br_depot_approach`, `cam_br_west_slope`, `cam_br_road_back`, `cam_br_edge_stones`, `cam_br_cairn` (player height, disabled Camera components; `review_cameras.json`). |

## Run order

`$O` = `/home/teknetik/.local/state/ward-programme` (capped wrappers). From the repo root:

1. `$O/unity.sh <log> AthenHill.Editor.BermsRoadPass.RunBatch --steps survey -nographics` → `survey.json` (ground
   vertices, 0.5 m height grid, colliders, markers, renderers, decals, cameras, material) and the whole-scene audit.
2. `python3 art/berms_road_20261001/fetch_polyhaven.py` (Poly Haven CC0 scans → `polyhaven/`, git-ignored).
3. `$O/heavy.sh uv run --with pillow --with numpy python art/berms_road_20261001/pack_layers.py` → layer arrays, `layers.json`.
4. `$O/heavy.sh uv run --with pillow --with numpy --with scipy python art/berms_road_20261001/make_splat.py [--check]`
   → splats, `road.json`, `splat.json`, `review/splat-preview.png` (`--check` proves the West Gate reproduction).
5. `uv run --with numpy --with matplotlib python art/berms_road_20261001/edge_stones.py` → `edge_stones.json`,
   `layout-check.json` (must say `"ok": true`), `review/edge-stones-map.png`.
6. `python3 art/berms_road_20261001/cams.py` → `review_cameras.json`.
7. Unity, one step per run: `--steps build -nographics` (importers, material) → optional preview captures
   `--steps capture:<dir>:@../../art/berms_road_20261001/review_cameras.json:preview` (graphics, ≤ 6 views, nothing
   saved) → `--steps install -nographics` (one time; rollback scene copy, record) → `--steps cameras,tune,verify
   -nographics` (review cameras; cairn shadows) → after captures `--steps capture:<dir>:cam_a+cam_b…` (≤ 6).
   `--steps toggle:old|new -nographics` swaps material, stones and footstep map for rollback. Before any Editor C#
   change, `art/berms_road_20261001/tools/check_cs.sh <file.cs>` compiles it outside Unity.

## Tuning

Everything visual is on `BermsGroundV2.mat` (edit `material.json` and re-run `build`, or edit the material directly):
`_RoadColor`/`_RoadContrast` (wheel-path gravel), `_LooseColor`/`_LagColor`/`_LooseContrast`/`_LooseSize` (crown,
windrows, desert-pavement lag), `_DriftColor` (sand on and by the road), `_CrustColor`, `_Compaction` (rut darkening),
`_ReliefStrength`/`_ReliefDepth` (ruts, windrows, potholes), `_InnerSand` (natural sand on the floor),
`_RockSlopeInner` (rock on the floor's mounds; the 7 m border band blends to the basin's `_RockSlope`), `_EdgeBlend`.
Natural-ground values (`_GravelColor`, `_Sand`, rock, strata, ripples, haze) are copied from `SandstoneBasinV3.mat` at
build time so the toe stays matched — change them on the basin material, then re-run `build`. Road features themselves
(widths, ruts, windrows, potholes, spurs) are in `make_splat.py`; stones in `edge_stones.py` (re-place them by hand in
the scene, or delete the root and re-run `install` from the rollback scene).

## Rollback

`--steps toggle:old -nographics` restores the previous material and footstep map and hides the stones root
(`toggle:new` re-applies). The full pre-install scene is `unity/evidence/berms-road/20261001/rollback/before-berms-road.unity`.

## Sources and licences

- Poly Haven (CC0): textures `gravel_ground_01`, `floor_pebbles_01` (Rob Tuytel; `polyhaven/manifest.json`, which also
  records the three evaluated and unused scans `rocky_trail_02`, `rock_ground_02`, `pebble_ground_01`); reused from the
  West Gate pass: `dry_ground_rocks`, `dense_sand`, `dry_ground_01` and the `namaqualand_rocks_01` rock prefabs; from
  the basin V2 material: `sandstone_cracks`, SandstoneAlbedo, Geology.
- Everything else (shader, splats, layout) is original in this folder. No Meshy credits used.
