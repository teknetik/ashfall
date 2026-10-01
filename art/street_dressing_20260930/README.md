# Ward street dressing — 30 September 2026

Carl (30 Sep 2026): "A lot of the street trash and props looks very low quality can we rebuild them in blender and or
meshy? I want the area to have a lived in look but not be too mesy. I dont want a clean clinical ward. eventually we will
introduce more NPC to make it look busy". Nothing here is accepted by Carl yet. Evidence, A/B timings and captures:
[unity/evidence/street-dressing/20260930](../../unity/evidence/street-dressing/20260930/README.md).

## What was wrong

The 8 Sep salvage scatter was 58 copies of one 432-triangle trash mound, 21 copies of a 679-triangle "A7" crate, ten
896-triangle scrap stacks and six 1,619-triangle generators, spread at a regular spacing over porch corners and yards
(`audit.json`, `review/layout-map.png`). Primitive cubes stood in for cargo crates, bollards and a plaza bench, and the
26 Sep retrofit left four collider proxies (`COL_*_bin`, 3.4 × 0.9 m) rendering as plain grey slabs on the cross streets.

## The kit (68 props, `Assets/AthenHill/Prefabs/StreetDressing/SD_<id>.prefab`)

| Source | Props | How |
| --- | --- | --- |
| Poly Haven CC0 scans (43 + 4 planted) | drums (red steel, blue poly, blue steel), fire barrel, jerrycans, churn, ammo crates, wooden crates, stacking crates, tote, carton, buckets, tub, watering can, planters, clay pot, stools, bench, broom, dustpan, tyre, rims, gas bottle, galvanised bins, sack truck, rack, toolbox, tool trolley, oil tin, baskets, enamel pot, picnic table | `fetch_polyhaven.py` (unbranded assets only) → `prepare_ph_props.py`: parts merged, scanned size kept, front to +Z, origin at the footprint centre on the ground, LOD1/LOD2 by collapse decimation. The clay pot and wooden planters also come **planted** (soil + the hill's Poly Haven succulents, ice plant, celandine, grass). |
| Meshy (4) | field generator, street water point, handcart, communal refuse bin | [meshy/street-dressing-20260930](../../meshy/street-dressing-20260930/README.md) → `prepare_meshy_props.py` (uniform scale to real size, LODs). |
| Blender-authored (15) | tied hessian refuse/grain sacks (3), tarp cloth-simulated over stacked stock with rope tie-downs, open scrap skip on skids holding sorted salvage (the scanned rims and tyre, pipe offcuts, bent sheet), litter: four paper sheets and a crumpled ball (original notice/form atlas), two flattened cartons, two crushed tins, a rag | `author_street_props.py`; original textures from `prepare_textures.py` (no real product text). |

`prepare_textures.py` copies the source base colour and OpenGL normal maps unchanged and derives URP mask maps from the
ARM / metal-rough maps (1k for props under 1 m, 2k above). Galvanised bins have their metallic scaled to 0.45 (at full
metal they went black against the city's small sky probe). Materials: `Art/StreetDressing/Materials` (URP Lit,
instancing on); potted plants use copies of the hill's wind materials with the bend starting higher (`SD_Potted_*`).
Prefabs: LODGroup (cuts by size, tuned on the A/B), box collider for anything walk-into-able (not litter, not
hand-sized), shadows from LOD0 and, for pieces over 1.2 m, LOD1; stools and benches carry **"NPC sit point"** markers
(13 in the scene) for the crowd pass.

## Layout (`layout.py` → `layout.json`, 145 instances in 30 vignettes, 41 ground decals)

Vignettes explain what people do there, against walls, on porch ends, in the rear service lanes and yard edges:
shop frontages (Relay Works parts stock, Air + Water water point and washing tub, Tool Exchange trolley and display
stool, Salvage wheels, Finery door planters and bench, Field Supply stock and grain sacks, Repairs tea break and a cart
under repair, Thread + Hide sewing stool), Basic General stock and refuse point, benches at the hill foot and the old
plaza-bench spot, planted pots at the three hill stair feet, the Salvage scrap skip, lane stock and water drums, the
Repairs forge gas and rack, the east yard (generator, fuel drums, tarp stack, handcart), caravan goods at the West Gate,
a rest spot on the market edge (picnic table, stool, cooking pot, fire barrel), planters at the hydroponics door, refuse
points behind Finery and beside Vanguard Hall, and a little windblown litter at wall feet, lane edges and porch-step
corners. Ground decals from the district's weathering atlas (one per tight cluster of props, so none bridges a doorway): grime under each working cluster, footprint scuffs where
people stand (refuse points, rest spots, benches).

`layout.py` validates every placement against the saved colliders (surface heights: street 0, steps 0.25, porch decks
0.5), each other (round props as circles), every shop door, bay and side door (front, rear, side), the hill stair
approaches, the terminal slab and hall steps, the walker/mechanic/droid routes (1 m / 1.6 m), NPC stand points, debug
landmarks and the Lattice/Ring interaction areas: **0 problems**. The avenue lanes round the hill stay open.

## Unity (`Editor/StreetDressingPass.cs`, `Editor/StreetDressingInstall.cs`)

**Athen Hill → Street dressing → Build assets** (textures, materials, prefabs), **Install (one time)** — retires the old
scatter and cube dressing (inactive, kept; they were render-chunk sources, so the chunks are rebuilt), hides the four
retrofit slab renderers (collision kept), places the kit under **Ward street dressing/&lt;vignette&gt;** and adds the
**Street dressing review cameras** (`cam_sd_*`) — then **Verify saved scene**. Batch: `-executeMethod
AthenHill.Editor.StreetDressingPass.RunBatch --steps build,install,verify,capture` (`solo:<ids>`, `audition`, `capture`,
`reinstall` for authoring, `toggle:on|off` for A/B timing). The dressing is not a render-chunk source: move, add or
delete instances in the Scene view.

## Run order

```sh
python3 fetch_polyhaven.py
B="env -i HOME=$HOME PATH=/usr/bin:/bin blender -b --factory-startup --python-exit-code 1"
$B -P prepare_ph_props.py && $B -P prepare_meshy_props.py && $B -P author_street_props.py
uv run --with pillow --with numpy python prepare_textures.py
uv run --with matplotlib python layout.py --plot        # needs unity/evidence/street-dressing/20260930/audit.json
# Unity: Build assets, Install (one time), Verify
```

Review: `review_kit.py -- <lod> [prefixes]` (Blender flat-colour grid with a 1.8 m figure) → `review/`; Unity solo and
row auditions (editor captures) in the evidence folder. Heavy media (Poly Haven downloads, blends, logs, review renders)
stays local per `.gitignore`; scripts and JSON are tracked.

## Third-party content

Poly Haven (CC0): the 43 models listed in `polyhaven/manifest.json` (names, authors, source URLs) and the textures
rough_linen, rusty_painted_metal, green_metal_rust (rusty_metal_grid fetched, unused). Plants in the planted props come
from the hill pass's CC0 set (`art/hill_20260930/polyhaven/manifest.json`).
