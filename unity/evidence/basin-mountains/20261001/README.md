# Basin mountains — evidence (1 October 2026)

Pass: `Assets/AthenHill/Editor/BasinMountainsPass.cs`; sources and pipeline: `art/basin_mountains_20261001/README.md`.
Scene root **Basin mountains** (8 chunks, 185,257 triangles, material SandstoneBasinV3) replaces
`Desert Landscape/DesertBasin_00…07` (8 × 640 = 5,120 triangles; now inactive, kept for rollback).

## Files

| What | Where |
| --- | --- |
| Scene audit before the pass (gzipped, local only) | `audit-before.json.gz` |
| Review-camera world poses (all `cam_*`) and the saved key/fog | `cameras.json` |
| Install record (renderers, triangles, retired chunks, rollback) | `install.json` |
| Saved-scene verification (`ok: true`, 0 problems, 0 missing materials, old chunks inactive, review cameras) | `verify.json` |
| Pass review cameras (player height, Berms ground + 1.7 m) | `review-cameras.json` |
| Scene before the install | `rollback/AthenHill-before-basin-mountains.unity` |
| Shader before the haze edit | `WardDesertTerrainV2.shader.before` |
| Old vs new top-down hillshade (±400 m) | `hillshade-old-vs-new.png` |
| Native baseline (12:00 LinuxDevelopment build, old basin), 8 cameras × 13:00 / 17:00 / 20:30 | `before-native/` |
| Native iterations from temporary scene copies (`previewbuild`), 13:00 + 17:00 | `iter1-native/` … `iter4-native/` |
| Partial A/B (stopped on Carl's change of process, see below) | `ab/h13/`, `ab/h13-summary.json` |
| Batch logs | `logs/` |

`iter4-native` is the installed geometry (iteration 4) with the iteration-3 material; the installed material differs
only in two haze values (far density 0.33 → 0.28, high-sun tint (.90, .95, 1.05) → (.88, .93, 1.03)) and has not been
captured natively. Captures of iterations 1–4 also contain other passes' scene changes made between 12:00 and 14:30
(paving, training range, night life), so compare only the mountains.

## Iterations (native, judged at 13:00 and 17:00)

1. Original layout envelope + 2 m and 1 m stream-power incision: facets and stripes gone; rounded "dumpling" hilltops.
2. Stronger incision + peak-height restoration: spiky pinnacles and scree heaps. Rejected.
3. Tableland profile (talus, cliff band, caprock), no peak restoration, gentler 1 m gullies: steep eroded faces, strong
   17:00 depth.
4. Wider strata benches, more rock outcrops, sharper crests (installed). A little more serration on some far crests.

Best before/after pairs (same camera, same hour):
`before-native/cam_hill-h17.00.png` → `iter4-native/cam_hill-h17.00.png`;
`before-native/cam_avenue-h13.00.png` → `iter4-native/cam_avenue-h13.00.png`;
`before-native/cam_westgate_mouth-h17.00.png` → `iter4-native/cam_westgate_mouth-h17.00.png`;
`before-native/cam_berms_road-h13.00.png` → `iter4-native/cam_berms_road-h13.00.png`;
`before-native/cam_courtyard-h13.00.png` → `iter4-native/cam_courtyard-h13.00.png`.

## Layout check (`art/basin_mountains_20261001/layout-check.json`)

Render-only, no colliders (as before). Inside the Outer Berms ground footprint + 0.75 m the surface equals the old basin
to 0.6 mm; along the city rectangle (0–3 m) it stays at the old rim level (−1.80…−1.76 m); within 15 m of the city it
peaks at 2.5 m (old: 5.7 m). No scene marker, route point or camera lies outside the city and the Berms footprint, so
nothing can be buried. The Berms ground object is untouched.

## Frame time and city loop

**Pending the orchestrator's combined test** (Carl's 14:50 change of process stopped per-pass builds and runs).
Measured before the stop, from two builds of one scene snapshot (`abbuild:on|off`, development, OpenGL, 1920 × 1080
High, 13:00, 8 s profile per run, alternating arms):

| Camera | Arm | Runs | Avg FPS per run | p50 ms (mean) | Submitted triangles |
| --- | --- | --- | --- | --- | --- |
| cam_hill (wide) | old basin | 3 | 34.9*, 62.6, 65.2 | 15.49 | 11.70 M |
| cam_hill (wide) | new basin | 3 | 64.5, 62.0, 63.3 | 15.74 | 12.39 M |

\* the first old-arm run had a 3.5 s hitch (desktop/load); without it the old arm averages 63.9 FPS. The p50 difference
(+0.25 ms) is inside this desktop's ±1–1.5 ms run-to-run drift; submitted triangles rise by about 0.69 M per frame
(colour, depth and four shadow cascades). The close camera (`cam_berms_road`) got one run per arm with incompatible
results (45.6 vs 152.3 FPS, the old arm stuttering at p95 41 ms): not usable. No city-loop run was made after the install.
