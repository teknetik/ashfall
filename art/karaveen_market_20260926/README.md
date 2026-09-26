# Karaveen caravan market — 26 September 2026

User request: make Ward feel alive (less blocky, less bright, post-apocalyptic
rough frontier atmosphere) and turn the market stalls into a believable market
with goods, authored in Blender.

This replaces, in the saved scene, the three flat-topped placeholder
`Karaveen artisan stall` instances (kept, **disabled**) beside the Karaveen truck
at the west plaza (x ≈ −30…−48). The truck, salvage scatter, benches and lamps
are unchanged.

## Contents

| Stall | Unity position (x, z) | Stock |
| --- | --- | --- |
| Produce | (−40.0, 12.0), faces +x | tilted display crates of apples, pomegranates, lemons/limes; open sacks of onions and sweet potatoes; baskets; onion strings; striped awning |
| Pottery & water | (−39.7, 5.2), faces +x | clay/ceramic vases, jugs, brass pots on three shelves; jerrycans, floor jars, water barrel, gallon bottles |
| Scrap & tools | (−39.8, −10.8), faces +x | corrugated rust roof, plank tool wall (sledge, spade, gas mask, hatchets, wrenches, hacksaw, crowbar), tins, propane, ammo boxes |
| Cloth & rugs | (−34.0, 16.6), faces −z | three hanging kilim rugs, leather hide, folded cloth stacks, fabric bolts, ground rug |
| Rations | (−34.0, −16.2), faces +z | stacked tins, ration boxes, jerky lines, grain sacks, crates, barrels |
| Cookfire ("Hot chow") | (−35.0, −3.0) | barrel stove with pot, stools, table with bowls, lantern pole; flames, embers and smoke in Unity |

Also: two salvaged pipe masts with lanterns, bunting strung across the lane,
and caravan overflow (barrels, crates, jerrycans) around the truck.

Every stall is hand-built geometry (irregular leaning posts, knee braces, rope
lashings, gapped plank counters with ragged aprons, sagging/wrinkled canvas with
repair patches and scalloped frayed valances, painted signs and chalk price slates).

## Budget (triangles, from `geometry-report.json`)

391k total visible triangles: ~33k structure, the rest goods. Each stall exports as
two meshes (`<Stall> Structure`, `<Stall> Goods`). Goods carry a Unity LODGroup
and cull below 4.5 % screen height (≈ 50–60 m). Poly Haven goods were decimated in
Blender (fruit ≈ 180–220 tris, vases ≈ 1.3k). No native performance qualification
has been run for this pass; measure on the RTX 3060 before accepting.

## Rebuild

```sh
./make_textures.sh                      # tinted canvas, kilim rugs, signs, slates (ImageMagick)
blender -b --factory-startup -P build_market.py   # writes KaraveenMarket.glb + karaveen-market-v1.blend
blender -b --factory-startup -P review_market.py  # optional Eevee stills in review/
```

`build_market.py` authors in Ward world space: Unity (x, y, z) = Blender (−x, −z, y)
(verified with an axis marker through glTFast). Then in Unity:
**Athen Hill → Karaveen → Install caravan market** (refuses if already installed) or,
for authoring iterations, `AthenHill.Editor.DustbowlMarketPass.RunAll` in batch mode.

## Sources and licences

- 45 Poly Haven models and 9 Poly Haven texture sets, **CC0**
  (`sources/polyhaven-manifest.json`, `sources/texture-manifest.json`, downloaded
  from the official API with MD5 checks by `download_polyhaven.py` / `download_textures.py`).
- Sign lettering uses **Rye** by Sorkin Type (SIL OFL 1.1, `sources/fonts/OFL-Rye.txt`);
  only rasterised into sign textures, the font file is not shipped.
- All stall geometry, rugs, canvases, signs and slates are original to this project.
