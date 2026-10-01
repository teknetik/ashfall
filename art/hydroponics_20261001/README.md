# Ward hydroponics greenhouses (1 Oct 2026)

Carl: "green houses look bare." The two retrofit quonsets in the north-west quadrant ("Ward district
retrofit/Hydroponics bays", built by `art/ward_retrofit_20260926/build_retrofit.py`) had bare grey trays with a sparse
scatter of desert succulents, flat pink LED slabs and a polycarbonate skin whose shadow pass put the whole interior in
shade. Lore: the hydroponics complex feeds Ward and supplies its markets; the aquifer is its water. This pass makes the
bays read as the working, tended heart of the food supply: lush and busy, but orderly.

Unity side: `unity/AthenHill/Assets/AthenHill/Editor/HydroponicsPass.cs` (scene root **Ward hydroponics**).
Evidence: `unity/evidence/hydroponics/20261001/`.

## What is built

| Part | Source | Notes |
| --- | --- | --- |
| Fit-out per bay (`HY_Fitout_A/B`, LOD0/1) | `author_hydroponics.py` + `hykit.py` | rack legs and bearers every 1.53 m, four white NFT channels per tray, feed manifold and spaghetti lines (west), return gutter and drains (east), slim LED bars in 1.15 m fixtures hung on wires (crop tiers `HY_LED` on the city light clock, propagation tiers `HY_LEDProp` always on), vine gutters with grow bags, rockwool cubes, drip lines, strings and top wires, ridge fans and misting line, concrete floor, weed mat, duckboards, a harvest trolley, crates, stool and hose |
| Crops (12 sections `HY_Crops_<bay>_<side>_<third>`, LOD0/1/2) | `author_hydroponics.py`, `hykit.py`, `make_textures.py` | butterhead, red lollo, cos, rocket, chard (red/yellow), basil, mint at staggered ages and a freshly harvested stretch; seedling and microgreen trays; cordon tomatoes (stripped lower stems, ripening trusses, dense upper leaves) and runner beans (flowers, pods) on strings. Leaf cards cut from CC0 Poly Haven leaf photographs (nettle, dandelion, weed plant, sorrel), recoloured into crop varieties (`textures/HY_CropAtlas.png`, `crop_atlas.json`) |
| Skin | `prepare_textures.py` (`HY_PolyFilm`) | copy of the retrofit polycarbonate with a light dust/condensation film (alpha 0.12–0.42), double-sided as authored, **no shadow pass** so sun reaches the crops, no direct specular highlight (the moon put a hotspot on it); swapped on the Structure renderer as a prefab-instance override |
| Yard props | `hyprops.py` | potting bench, compost bays, shade frame (3.6 × 3.0 m) with drying herb bunches, IBC nutrient tote with hose, nursery table, pallet, herbs and soil for the three retrofit planters, hose run; produce fills for the street kit's scanned yellow crate and wicker basket (lettuce, cos, tomato, beans, chard, onion; tomato, herbs, beans) |
| Poly Haven scans | `fetch_polyhaven.py` → `hyprops.py` | hose reel (on an authored timber post), trowel, spade, rubber boots, work hat, nutrient jug, dosing trolley, step ladder, onion (fill) |
| Layout | `layout.py` → `layout.json` | 58 placements in 12 vignettes, validated against the saved colliders, door thresholds and walking lines (`review/layout-map.png`, 0 problems); 10 ground decals; 4 night-only grow-glow point lights |

## Run order

```
O=<scratchpad>/overnight
python3 fetch_polyhaven.py                                   # CC0 downloads (git-ignored)
uv run --with pillow --with numpy --with scipy python make_textures.py      # crop atlas, PVC, shade cloth, skin film
$O/blender.sh author_hydroponics.py -- --only interior       # fit-outs + crop sections -> Art/Hydroponics/Interior
$O/blender.sh author_hydroponics.py -- --only props          # yard props -> Art/Hydroponics/Props (hy-manifest.json)
$O/heavy.sh uv run --with pillow --with numpy python prepare_textures.py   # Unity maps + Textures/materials.json
uv run --with matplotlib python layout.py --plot              # layout.json
$O/unity.sh <log> AthenHill.Editor.HydroponicsPass.RunBatch --steps build,install,verify,capture --out <dir>
```

Re-run after an install: `--steps build,reinstall,verify` (authoring only; the first install made the rollback copy).
Non-rendering Unity steps take `-nographics`; editor captures (`capture[:filter]`) render at most six views per run.

Review: `review_hydroponics.py` (Cycles, interior in a stand-in quonset), `review_props.py` (props; fills shown inside
the scanned containers), `tools/pair.py` (before/after sheets).

Measurement: `tools/snapshot_ab.sh` builds both A/B arms from one snapshot of the saved scene
(`HydroponicsPass abbuild:on|off|noyard` → `unity/AthenHill/Builds/hy-ab-*`, git-ignored) and alternates native
profiles; `tools/final_after.sh` = build assets, verify, development build, native lookbook of record, city loop.
Numbers and remaining defects: `unity/evidence/hydroponics/20261001/README.md`.

## Sources and licences

All downloads are CC0 from Poly Haven (`polyhaven/manifest.json` records names, authors and URLs): nettle_plant,
dandelion_01, weed_plant_02, shrub_sorrel_01 (leaf photographs for the crop atlas), seeding_tray_01,
garden_hose_wall_mounted_01, trowel_01, rusted_spade_01, rubber_boots, fishermans_hat, plastic_bottle_gallon,
industrial_storage_cart, wooden_ladder, yellow_onion; textures weathered_planks, farm_soil, wood_chip_path,
gravel_concrete_03. Street-kit containers (SD_crate_yellow = plastic_crate_02, SD_basket_flat = wicker_basket_01) are
reused from `art/street_dressing_20260930`. Everything else is original Blender geometry. No branded assets.
