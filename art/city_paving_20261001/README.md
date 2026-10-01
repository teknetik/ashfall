# City paving — Ward sandstone flag ground (1 Oct 2026)

Next-wins item 2 ("City paving") and the "Texture streaming budget" note. The whole city floor (`Paving`, a 120 × 90 m
render-chunk source) and the plaza bands around the hill block now use a new dressed-sandstone flag material. The old
material and textures are unchanged and kept for rollback. Evidence, numbers and remaining defects:
`unity/evidence/city-paving/20261001/README.md`.

## What the ground is

- **Layout.** A 4 × 4 m tile of 8 courses (0.5 m) running east–west, flags 0.5–1.25 m long in running bond, with a joint
  at every tile edge. The shader maps it in world XZ and gives every world course its own random shift and source
  course, so the 4 m tile never reads as a lattice. Each flag instance (flag id × course × tile) gets its own value/hue
  and smoothness.
- **Flags.** Each flag is a 1:1 crop of the CC0 scan `worn_rock_natural_01` (the Ward masonry kit's ashlar stone),
  graded to the Ward sandstone palette (flag mean sRGB ≈ 186, 165, 136), with a laying tilt, broad cloudiness, grime
  blotches and sand-scoured patches, rare cracks and stains, rounded and chipped arrises.
- **Joints.** 8–15 mm, filled with sand (the masonry kit's `VH_Sand`, darker) 4–7 mm below the arris, with sand spill
  onto the first ~2 cm of each flag. The shader darkens them further near the camera and lifts them beyond ~12–30 m so
  the far field does not read as a ruled grid.
- **Shader extras** (`Athen Hill/Ward Paving Lit`): world-space macro tint/value at ~23 m and ~61 m, dust patches that
  settle in the joints first, a 1 m close-range grain normal that fades out by 18 m, and WeatheredLit's broad dust stains
  (same `_WearStrength/_WearScale/_WearTint` as the old material).
- **Plaza bands.** The three visible `Plaza inset` strips (4.2 m bands framing the hill block) still carried the old
  paving texture; they now use `PV_CityFlags_Band` = the same flags run north–south, slightly cooler and darker.
- **Retired.** `Paving Joints` (50 strips on a 4 m grid; they were already not drawn, `sourceVisibility` false) is now
  inactive. The four `Avenue service band` gunmetal strips (0.22 × 44 m at z = ±20, ±29) were the dark "raised rail"
  in the review captures and are inactive. `COL_Ground` is untouched.

## Review cameras

Root "City paving review cameras" (disabled cameras, eye 1.62 m): `cam_pv_feet`, `cam_pv_east_lane`,
`cam_pv_north_lane`, `cam_pv_west_open`, `cam_pv_courtyard_edge`, `cam_pv_south_lane`. Positions and what each shows:
`unity/evidence/city-paving/20261001/README.md`. Capture at 13:00 and 20:30.

## Testing status

Install verified with `-nographics` (`verify-saved-scene.json`). This pass measured a preliminary material A/B
(+0.31 ms at `cam_pv_north_lane`, ~0 at `cam_hill`) and a budget A/B (no measurable cost); the frame-time record, the
combined lookbook and the city loop are **pending the orchestrator's combined test**.

## Files

| File | Role |
| --- | --- |
| `fetch_polyhaven.py` | Downloads the CC0 sources to `polyhaven/` (git-ignored) and writes `polyhaven/manifest.json`. |
| `author_paving.py` | Bakes the tile: `out/PV_Flags_{BaseMap,Normal,Mask}_{4k,2k}.png`, `out/PV_Grain_Normal_1k.png`, `out/layout.json`. Run through `heavy.sh` (numpy over 4k arrays, ~1–2 min, 3.6 GB peak). |
| `preview_tiling.py` | Top-view emulation of the shader's course shuffle (`review/tiling_shift.jpg`). |
| `tuning.json`, `tuning-band.json` | Material values applied by the Unity pass (`assets`, `bandmat`). One place to tune. |
| `tune_runtime.py` | Writes the runtime tuning file for `ATHEN_MATERIAL_TUNE` (development players: tune without a rebuild). |
| `review_pairs.py` | Before/after pairs and ground crops from two native lookbook folders. |
| `plot_layout.py`, `analyse_source.py` | Planning helpers (city footprint map, source analysis). |

Mask channels: R flag id `(k + 0.5) / 32` (0 in joints), G cavity occlusion, B height (0 sand … 1 flag top),
A smoothness. Normal maps are OpenGL (+Y up the texture), linear.

## Run order

```bash
O=/home/teknetik/.local/state/ward-programme
python3 fetch_polyhaven.py
$O/heavy.sh uv run --with pillow --with numpy python author_paving.py
# Unity (from the repo root): textures + materials, one-time install, plaza bands, verify, A/B builds
$O/unity.sh <log> AthenHill.Editor.CityPavingPass.RunBatch --steps assets,install,bandmat,bands,verify -nographics
$O/unity.sh <log> AthenHill.Editor.CityPavingPass.RunBatch --steps abbuild:on -nographics   # then abbuild:off
```

Other steps: `diag` (paving/streaming diagnostic → `diagnose.json`), `cameras` (adds the `cam_pv_*` review cameras),
`build:<name>` (development player into `Builds/cp-<name>`).

## Sources and licences

- `floor_tiles_04` (Rob Tuytel), Poly Haven, CC0 1.0 — fetched for analysis; not shipped.
- `worn_rock_natural_01`, Poly Haven, CC0 1.0 — flag surfaces (albedo/height) and the grain normal.
- `VH_Sand_BaseMap` (`dense_sand`, Poly Haven CC0, graded by the Ward masonry kit) — joint sand.
- Shader: derived from URP Lit via `Athen Hill/Weathered Lit` (Unity Companion License, `Shaders/Unity-LICENSE.md`).
