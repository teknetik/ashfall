# City paving and texture streaming — evidence (1 Oct 2026)

Workstream: next-wins item 2 ("City paving") and the "Texture streaming budget" note. Sources and run order:
`art/city_paving_20261001/README.md`. Unity pass: `Assets/AthenHill/Editor/CityPavingPass.cs`.
Frame-time and city-loop acceptance are **pending the orchestrator's combined test** (per-pass testing stopped at
14:50); the numbers below are what this pass measured before that, on its own builds (now deleted).

## What changed in the saved scene and project

| Change | Where | Rollback |
| --- | --- | --- |
| City floor `Paving` → `PV_CityFlags` (shader `Athen Hill/Ward Paving Lit`) | `Art/CityPaving/` | `Art/Weathering/Paving Local wear.mat` (unchanged) |
| `Plaza inset` north/south/west/east → `PV_CityFlags_Band` (courses north–south) | same | `PlazaPaving Local wear.mat` (unchanged) |
| `Paving Joints` root inactive (50 strips, already not drawn: `sourceVisibility` false, no chunk) | scene | reactivate |
| 4 × `AuthoredWorld/AAA Environment Dressing/Avenue service band` inactive (the dark "raised rail") | scene | reactivate |
| Render chunks rebuilt; **`StaticRenderChunksEditor.Rebuild` now calls `Mesh.RecalculateUVDistributionMetrics()`** | `Editor/StaticRenderChunksEditor.cs` | remove the line |
| **PC `streamingMipmapsMemoryBudget` 4096 → 5632 MB** | `ProjectSettings/QualitySettings.asset` | set back to 4096 |
| Dev-only diagnostics `TextureStreamingProbe` / `MaterialTuneProbe` (env-gated, compiled out of releases) | `Scripts/TextureStreamingProbe.cs` | delete |
| 6 review cameras `cam_pv_*` under root "City paving review cameras" | scene | delete root |

`COL_Ground`, the hill, Vanguard Hall podium, porch decks and the courtyard reference paving are untouched. No objects
were placed; the two retired strip families had no colliders, so routes, doors, stairs and NPC points are unaffected.
Pre-install scene copy: `rollback/before-city-paving.unity`. Records: `install.json`, `install-bands.json`,
`verify-saved-scene.json` (final, 14:5x): installed, 0 missing materials, chunk fingerprint OK, joints and service
bands inactive, `COL_Ground` present, old materials kept, budget 5632, 6 review cameras.

## Step 0 — texture streaming diagnosis (native, `ATHEN_TEXSTREAM_PROBE=1`)

`native-before/texture-streaming*.json` (baseline build, budget 4096):
- **Non-streamed textures alone were 4399 MB, over the 4096 MB budget.** Streaming could never load finer mips: every
  streamed texture sat at its initial `maxLevelReduction` (loaded mip 2); 21 wanted finer and could not get it (hero
  tree leaves/trunk calculated mip 0, loaded mip 2). Desired 4889–5099 MB across views, current 4687 MB.
- **The paving was calculated at mip 2** (1254 px per 6 m → ~52 px/m on screen) because every render-chunk mesh (87/87)
  had UV distribution metric 1: the chunk rebuild never recalculated it, so the streamer thought the 120 × 90 m slab was
  1 m across. Fixed in the chunk rebuild (the paving chunk now reports 10800; 23 chunks still report 1 — not checked).
- The old paving normal map was the albedo file itself converted to a height normal (`Paving_NormalSource.png` is
  byte-identical to `Paving_Albedo.png`) — the "orange peel".
- Budget 6144 via env (`native-before-budget6144`): reduced 0, texture memory 4687 → 4937–5207 MB, leaves visibly
  sharper (`compare/budget_zoom_cam_hill.jpg`).
- Largest non-streamed: `Imported/Meshy/District/Atlas` 3 × 6144×4096 RGBA32 = 384 MB (west-gate arches); dozens of
  glTF-imported 2k maps (`*_rough_2k`, `PistolMods_*`) uncompressed ARGB32 at 21 MB each. Converting these is the real
  memory fix (not done: other passes' assets).

**Budget decision (for Carl):** 5632 MB, not 6144. It covers the measured desired set (≤ 5.1 GB) with headroom and
keeps worst-case growth to ~1.2 GB of streamed textures, because the shared 12 GB card also holds the desktop and the
programme's VRAM watchdog trips at 11.4–11.7 GB. Measured with the final build: texture memory at `cam_hill` 4703 MB
(4096) vs 4961 MB (5632), +258 MB; up to 5257 MB over a 13-camera session; reduced textures 21 → 0. System VRAM peaks
in this pass's runs: 10.37 GB before, 10.66–11.20 GB after (includes the desktop and other load; not a clean A/B).
Frame time at `cam_hill`: no measurable change (below).

## New ground — textures and memory

- `PV_Flags_BaseMap/Normal/Mask` 2048² BC7 (5.33 MB each) + `PV_Grain_Normal` 1024² BC7 (1.33 MB) = **17.3 MB**,
  **not streamed** (always resident; measured non-streamed total 4399 → 4418 MB). 4 m tile → 512 px/m at mip 0, plus a
  1 m grain normal (1024 px/m) that fades out by 18 m. Old: 2 × 1254² RGBA, effectively mip 2 (~52 px/m) in play.
- Shader cost: 4 texture fetches (3 with explicit gradients) + value-noise macro fields; paving shadows stay off.

## Frame time (preliminary — the orchestrator's combined A/B is the record)

Development builds from one scene snapshot (`abbuild:on/off`: "off" = old paving + old plaza material; retired
strips, chunk metrics and budget identical), OpenGL, 1920×1080, High, 13:00, 8 s, alternating rounds:

| Camera | on (ms) | off (ms) | Δ | Notes |
| --- | --- | --- | --- | --- |
| `cam_hill` (wide) | 15.43, 14.99 | 15.72, 14.97 | −0.14 (drift) | tris 11.71 M both, SetPass 336 both |
| `cam_pv_north_lane` (player height, mostly paving) | 8.50, 8.50 | 8.22, 8.16 | **+0.31** | SetPass 262 vs 260 |

Budget (same "on" build, `ATHEN_TEXSTREAM_BUDGET` override, `cam_hill`, no probe): 5632 → 15.34, 15.90 ms;
4096 → 15.75, 15.54 ms: no measurable difference. (One 5632 run failed to start: `timeSet` not acknowledged.)
City loop: **not run** (pending the combined test).

## Images

- Before (13:00, 20:30): `native-before/` (13 cameras, sheets `sheet-h13.00.jpg`, `sheet-h20.50.jpg`).
- After (look of record before the last tuning step): `native-after3/` (13:00) and `native-after3-night/` (20:30).
- Final tuning, player height: `compare/final/cam_pv_north_lane-h13.00-final-on.png` (vs `-final-off.png`, same build
  snapshot with the old material) and `compare/final/pair-cam_pv_north_lane-h13.00.jpg`.
- Pairs and ground crops: `compare/pairs-13/pair-*.jpg`, `crop-*.jpg`; night `compare/pairs-2050/`.
  Best: `pair-cam_pv_feet`, `crop-cam_sd_avenue_west`, `pair-cam_sd_hill_benches`, `pair-cam_pv_north_lane`.
- Tuning sweep (runtime, no rebuild): `tune-v1` (as built), `tune-v2` (heavy dust), `compare/tune_*.jpg`
  (`tune-v3` is a bad capture: the player window opened at 930×1029).
- Earlier iterations: `native-after1` (black mirror flags = an incomplete course in the bake, fixed), `native-after2`.

## Review cameras (player eye 1.62 m; root "City paving review cameras")

`cam_pv_feet` (40, 1.62, 10) ground at the feet · `cam_pv_east_lane` (31, 1.62, −16) 2–40 m along the east lane ·
`cam_pv_north_lane` (−14, 1.62, 26) grazing view down the north lane · `cam_pv_west_open` (−34, 1.62, −16) west
market paving · `cam_pv_courtyard_edge` (17, 1.62, −4) where the flags meet the courtyard stone ·
`cam_pv_south_lane` (−30, 1.62, −23.5) south lane by the hall. Also useful: `cam_sd_avenue_west`, `cam_sd_bg_stock`,
`cam_sd_hill_benches` (plaza band), `cam_avenue`, `cam_gate`, `cam_hill`.

## Known defects / open points

- One course direction (east–west) for the whole floor except the plaza bands; in long east–west sightlines the
  0.5 m courses read a little like a tiled floor at 20–40 m. Per-street direction changes or bands would help.
- Along a course the flag *surfaces* repeat every 4 m (the shuffle removes the 2D lattice and every instance gets its
  own tone, but a sharp eye can find repeats). Per-flag tone fades out at far mips by design.
- Flags are flat geometry (normal map only, no parallax); in the high noon sun the relief is subtle and the flags read
  somewhat clean next to the battle-worn masonry. Wall-foot junctions are still knife-clean (next-wins item 6).
- The depth/meta passes use the mesh UVs (not the world-shuffled mapping), so `_CameraNormalsTexture` gets approximate
  normals; SSAO uses depth only today, so nothing visible depends on it.
- The four `Avenue service band` strips are simply retired; flush steel duct covers / drain channels would be a better
  piece of aquifer storytelling later.
- Night: the paving responds well under practical lights; the dark gaps between lamps are the lighting stream's.
- VRAM headroom: the budget raise costs ~0.26–0.6 GB of resident textures on a shared 12 GB card that already peaks
  ~10.4–11.2 GB in QA runs. The 4.4 GB of uncompressed non-streamed imports is the real problem (follow-up).
- 23 chunk meshes still report a UV metric of 1 after the rebuild (probably degenerate/absent UVs) — unchecked.
- `TextureStreamingProbe` adds hitches when enabled (full dumps every 8 s); never profile with it on.
