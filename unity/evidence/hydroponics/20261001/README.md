# Hydroponics greenhouses — evidence (1 Oct 2026)

Carl: "green houses look bare." Pass: `Editor/HydroponicsPass.cs` (scene root **Ward hydroponics**), sources
`art/hydroponics_20261001` (README there: run order, sources, licences). Not accepted by Carl.

## What changed

- **Interior of both quonsets** (14 prefab instances under `Ward hydroponics/Interior`): fit-out per bay (rack legs and
  bearers, NFT channels, feed manifolds/returns, slim LED bars on wires, vine gutters with grow bags, strings and top
  wires, ridge fans, misting line, concrete floor, weed mat, duckboards, harvest trolley, a nutrient mixing drum and a
  wall dosing unit at the tank end) and 12 crop sections (lettuces, chard, basil, mint, rocket at staggered ages and a
  freshly cut stretch; seedling and microgreen trays; cordon tomatoes and runner beans on strings), each a 3-level
  LODGroup. Crop-tier LEDs on the light clock (`HY_LED` in `CityLightCircuit.emissiveMaterials`), propagation-tier LEDs
  always on.
- **Skin**: the Structure renderer's polycarbonate slot overridden to `HY_Polycarbonate` (light dust/condensation film,
  double-sided, no shadow pass). The retrofit skin's shadow pass had put the entire interior in shade.
- **Retired** (inactive, kept): `Hydroponics bays Detail` (102,208 triangles drawn at every distance, 93k of them desert
  succulents) → replaced by a filtered copy with the planters, tank bands and ladders (8,788 triangles,
  `Art/Hydroponics/Retrofit/Hydroponics_bays_Detail_kept.asset`); `Hydroponics bays Glow` (flat pink slabs).
- **Yard** (`Ward hydroponics/Yard`, layout `art/hydroponics_20261001/layout.json`, 0 validation problems): harvest
  stack and herb pots by the A door, potting bench at B's east end, nursery tables under a shade frame with herbs drying,
  growers' rest bench, a handcart loaded for the market, nutrient totes and a skin-repair corner in the south lane,
  dosing trolley and boots/hose reel at the west end, compost bays in the north alley, herbs in the three planters between
  the bays. 10 grime/scuff decals. NPC sit points on three stools and the bench (5).
- **Night**: four night-only grow-glow point lights (no shadows) on the light circuit.
- Collision unchanged for the quonsets (still solid). The yard props add box colliders (potting bench, compost bays, IBC
  totes, nursery tables, shade-frame posts, dosing trolley, street-kit props).

## Files

| File | What |
| --- | --- |
| `audit-before.json` | scene inventory before the pass (renderers, colliders, markers) |
| `probe-retrofit-bays.json` | retrofit bay materials/shadow passes (why the interior was dark) |
| `native-before-existing/`, `native-before/` | native lookbook before (13:00, 20:30), the second with the `cam_hy_*` review cameras |
| `editor-before/`, `editor-after1/`, `editor-after2/`, `editor-off1/` | editor captures (MainCamera clone): before, first install, after the skin/cloth fixes, with the market cart |
| `install.json`, `reinstall.json`, `verify-saved-scene.json`, `build-assets.json` | install records and the saved-scene check |
| `native-after/` | **native lookbook of record** after the final skin follow-up (13:00, 20:30; all `cam_hy_*`, `cam_retrofit_hydro`, `cam_sd_hydroponics`, `cam_hill`) |
| `native-ab1-*`, `native-ab2-*` | snapshot A/B profiles (on, off, noyard) at `cam_hy_wide`, `cam_hy_skin_close`, `cam_hill` |
| `native-off1/3`, `native-on2/3` | earlier A/B halves from the shared build folder (not clean pairs; captures useful) |
| `cityloop-native/`, `cityloop-final/` | real-input city loop with the pass installed (both PASS) |
| `rollback/before-hydroponics.unity` | the scene before the first install |
| `logs/` | Unity, build and lookbook logs |

## Numbers

Triangles (LOD0 / LOD1 / LOD2): interior crops 359,740 / 47,568 / 14,652 in 12 sections (largest section 50,874 at
LOD0, 4.6 m long; full plants only within ~9 m); fit-outs 9,044 + 8,924 / 4,130 + 4,010. Whole pass, every LODGroup's
LOD0 summed: 866,638 (interior 377,708, retrofit planters/tank fittings 8,788, yard ~480k, most of it the street kit's
scanned crates and the Poly Haven props at LOD0, which only draw within a few metres). The retired retrofit Detail
mesh drew 102,208 triangles at every distance up to its 3 % cull.

**A/B frame time** (native development build, OpenGL, 1920×1080 PC preset, RTX 3060, 8 s profiles; both arms built
from ONE snapshot of the saved scene by `HydroponicsPass abbuild:on|off|noyard` into `Builds/hy-ab-*`, so other
workstreams' scene edits cannot leak into the comparison; runs alternated on, off, noyard, on, off; GPU time not
available, frame time ≈ CPU frame mean because the player is GPU-bound):

| View | Pass off (fps / mean ms) | Pass on (fps / mean ms) | Cost | Yard off (interior + skin only) |
| --- | --- | --- | --- | --- |
| `cam_hy_wide` 13:00 (the yard and both bays, 15 m) | 94.9, 93.3 / 10.63 | 87.6, 88.5 / 11.36 | **+0.73 ms** | 92.2 / 10.85 |
| `cam_hy_wide` 20:30 | 81.8, 83.3 / 12.11 | 75.9, 76.9 / 13.09 | **+0.98 ms** | 80.0 / 12.50 |
| `cam_hy_skin_close` 13:00 (player height, 3 m from B's skin) | 353.5, 365.2 / 2.78 | 222.7, 221.9 / 4.50 | +1.72 ms (at ~220 fps) | 236.9 / 4.22 |
| `cam_hill` 13:00 (district wide) | 68.0, 68.6 / 14.64 | 67.5, 67.8 / 14.78 | **+0.14 ms** | (64.9, outlier run) |

p99 stays under 16.7 ms at all hydroponics views (worst 14.67 ms at `cam_hy_wide` 20:30, pass on); `cam_hill` p99
16.40/16.72 on vs 16.74/16.34 off. Profiles: `native-ab1-*`, `native-ab2-*` (`lookbook.json`), summary
`logs/snapshot_ab.out`. Earlier, not-clean pairs (`native-off1`, `native-on2`, `native-off3`, `native-on3`) were taken
from the shared build folder while other workstreams were building; they agree within ~0.3 ms.

The cost at the yard's own wide view is above the programme's ~0.5 ms guide: about 0.5 ms is the yard (58 props,
nested LODGroups, ~40 materials, 10 decals), 0.2–0.4 ms the interior and skin (more at night: four point lights and the
LED emission). At the district view it is 0.14 ms. Further savings, if needed: drop the yard decals or the composite
crates' nested LODGroups, share materials, cast yard shadows from LOD1 proxies.

**City loop**: `CITY LOOP PASS` with the pass installed (`cityloop-native/`, 09:41, and `cityloop-final/` after the skin
follow-up).

## Best before/after pairs

Side-by-side sheets (left before, right after) in `art/hydroponics_20261001/review/` (git-ignored renders):
`final-pairs-day.jpg` (`cam_hy_skin_close`, `cam_hy_east_yard`, `cam_retrofit_hydro`, `cam_hy_gap` at 13:00),
`final-pairs-night.jpg` (the same at 20:30), `final-pairs-hill.jpg` (`cam_hill`). Sources: `native-before/` (or
`native-before-existing/` for `cam_hill`) and `native-after/`, e.g. `native-before/cam_hy_skin_close-h13.00.png` →
`native-after/cam_hy_skin_close-h13.00.png`.

## Remaining defects (honest)

- Frame cost at the yard's own wide view is +0.7 ms (day) / +1.0 ms (night), above the ~0.5 ms guide; +0.14 ms at
  `cam_hill`. See the options above.
- The quonsets are still solid and not enterable; the interior is seen only through the skin and the end panels. The
  doors are the retrofit's closed graphite panels.
- Crops are leaf cards: at 2–3 m through the skin they read as plants, but lettuces are flatter than real heads and the
  tomato trusses are spheres with an atlas colour (no calyx geometry). LOD2 far cards can pop at ~25 m on the long
  racks (no cross-fade).
- The interior aisle crates, trolley, drum and dosing unit are simple authored shapes (flat colours) — fine through the
  skin, plain if ever seen up close.
- The bench (street kit `SD_bench_painted`) reads as a dark red box at a distance; the shade frame's posts are bright
  galvanised steel against the sand.
- Night: the pink grow glow is subtle from the yard; the skin has no direct highlight now (moon hotspot removed), so at
  night it reads mostly through the ribs.
- Not yet accepted by Carl.
