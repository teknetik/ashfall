# Ward rooftops and service lines — 1 October 2026

Art-direction review of 30 Sep, item 8 (`~/.local/state/ward-programme/next-wins.md`): "From the street every roofline is an
unbroken cornice against the sky … At 1.6 m eye height, the skyline is what the player sees above every shop. It is also
where Ward's survival story (water, power, air) can be told cheaply." Checked on the cited native stills before starting
(`review/before-sheet.jpg`, local): only the Air + Water tank dome, the Repairs container, Relay Works' mast and Salvage's
shed and stovepipe broke the cornices. Nothing here is accepted by Carl yet. Evidence: [unity/evidence/rooftops/20261001](../../unity/evidence/rooftops/20261001/README.md).

## What was added (scene root **Ward rooftops**)

One child per shop roof whose transform equals that shop's root, so its pieces use the shop's own frame (origin = facade
centre at paving level, +Z to the avenue), plus **Service lines** in world space. 36 placements and 8 line groups:

| Roof | Pieces (what they say about Ward) |
| --- | --- |
| Relay Works | 6.4 m HF whip on a guyed stub mast at the front corner (comms), gooseneck cowl; two alley line hooks |
| Air + Water | dew/condensate collector (two 1.3 × 1.6 m knitted nets on three posts, gutter, collection drum) across the front of the roof beside the existing tank; service-line mast; caged ladder up the cross-street wall; conduit drop to a junction box; alley hooks |
| Tool Exchange | two PV panels tilted 32° towards the avenue on a sandbag-ballasted frame raised 0.9 m so they clear the low parapet (the fabricator's power); service-line mast; conduit drop and junction box |
| Salvage | roof terrace: shade canvas (madder) laced to a pipe frame, two street-kit stools and a crate, 3.2 m guard rail on the front parapet |
| Finery | 3 m³ galvanised water tank on a braced stand with ladder and outlet valve, forward on the roof; 6.6 m guard rail along the front parapet; cowl; caged ladder up the south wall |
| Field Supply | two turbine ventilators and a service-line mast on ridge saddles (37° roof); conduit down the north slope and wall to a junction box |
| Repairs | 0.9 m dish on a ballasted mount on the container workshop; service-line mast at the rear (clear of the forge flue); conduit drop and junction box; alley hooks |
| Thread + Hide | horizontal 2 m³ dye/wash-water tank on a 1.15 m braced stand behind the drying lines; 6.6 m guard rail on the drying terrace's front parapet; cowl; alley hooks |
| Service lines | two conductors on pin insulators across each cross street (Air + Water ↔ Tool Exchange 13.2 m, Field Supply ↔ Repairs 15.4 m), one short line pair across each narrow alley, four galvanised conduit drops (mast box → roof deck → over the coping → round the cornice and string course, cleated → junction box → ground) |

No lights, nothing retired, no render-chunk source touched. Shadows only from the two tanks (the street-kit seats on the
Salvage roof have theirs switched off as instance overrides).

## Kit (`Prefabs/Rooftops/RT_<id>.prefab`, 18 objects + 8 line groups)

All original geometry on the shared Ward kit (`art/ward_masonry_kit`: `Part`, metre box-UVs, glTF export), using the
shops' own materials (`VH_Steel`, `VH_PaintedSteel`, `VH_Dark`, `VH_Rubber`, `WS_Paint*`, `WS_ClothMadder`) and the street
kit's `SD_Sack`/`SD_Rope` for sandbags and lacing, plus three new URP Lit materials in `Art/Rooftops/Materials`:
`RT_DewNet` (alpha-clipped, double-sided knitted net, 512 px tile = 0.25 m), `RT_SolarCell` (6 × 6 cells of 156 mm per
tile) and `RT_Ceramic` (insulators). Textures are procedural (`make_textures.py`).

| Id | LOD0 / LOD1 tris | Notes |
| --- | --- | --- |
| TankTall | 3,656 / 2,024 | Ø1.5 × 1.75 m banded tank, cone roof and vent, on a 2 m braced stand with platform and ladder; casts shadows |
| TankLow | 2,864 / 1,236 | Ø1.1 × 2.3 m horizontal tank on saddles on a braced 1.15 m stand, manway, valve, ladder; casts shadows |
| DewNet | 2,148 / 1,448 | two bellied knitted nets (dark green, ~22 % cover) on three posts, the outer two guyed; tension and edge cords, gutter, downpipe, drum |
| SolarFrame | 1,224 / 556 | two 1.0 × 1.65 m panels, combiner box, conduit, sandbags |
| VentCowl, TurbineVent, TurbineVentRidge | 800–1,680 | gooseneck cowl; whirlybird on a flat flashing (spare, not placed) or a 37° ridge saddle |
| Whip, Dish | 964, 1,292 | guyed whip with spring and loading coil; dish with feed arm on crossed channels and sandbags |
| CableMast, CableMastRidge | 1,704, 1,184 | 2.6 m mast, crossarm, three porcelain pin insulators (span anchors in `kit.json`), weatherhead, junction box, guys |
| Rail320/660 | 948–1,500 | parapet-clamped 48 mm guard rail; posts at ≤ 1.7 m; origin = inner coping edge |
| Ladder876/919 | 3,472 / 3,692 | caged ladder for an 8.76 / 9.19 m coping, 0.52 m off the wall (clears the 0.43 m cornices), gooseneck over the coping; box collider over its foot |
| WallHook, JunctionBox | 192, 308 | wall-plate insulator hook; 0.4 × 0.55 m box with hood, hinges, glands |
| Lines_* (8) | 240–912 | spans (parabolic sag 0.04–0.67 m) and conduit drops, one GLB per group with its own origin |

Installed totals (`verify-saved-scene.json`): 44 instances, LOD0 67.4k triangles (~21k of them the three street-kit props'
scan LOD0s), LOD1 28.2k, 4 shadow-casting renderers (the two tanks, 6.5k triangles at LOD0), 0 lights.

## Layout rules (`layout.py`, 0 problems)

Deck pieces inside the parapets and clear of each shop's existing roof furniture (hatches, air conditioners, masts and
their guy wires, tank, shed, container, drying lines) and of each other; all pieces and cables at least 1.8 m from the
night-life smoke columns (Repairs forge flue, Salvage stovepipe); wall pieces and conduit runs clear of windows, doors,
lamps, downpipes, power boxes and the flue; spans at least 0.35 m above every roof they cross; ladder feet and conduit
ends clear of the saved colliders (the invisible retrofit `COL_*_bin` proxies excepted), walker/mechanic/droid routes
and NPC/landmark points. A skyline check reports each piece's height above its roofline and how many of 59 avenue
viewpoints (1.6 m) see at least 0.3 m of it (`review/layout-report.json`).

## Run order

```sh
O=~/.local/state/ward-programme
$O/blender.sh art/rooftops_20261001/author_roof_kit.py            # kit GLBs + Models/kit.json (anchors, bounds)
uv run --with matplotlib python art/rooftops_20261001/layout.py --plot   # layout.json, validation, review/layout-map.png
$O/blender.sh art/rooftops_20261001/author_cables.py              # line GLBs + Models/lines.json (needs layout.json)
uv run --with pillow --with numpy python art/rooftops_20261001/make_textures.py
python3 art/rooftops_20261001/review_cams.py                       # review-cameras.json
$O/unity.sh <log> AthenHill.Editor.RooftopsPass.RunBatch --steps build,install,verify -nographics
art/rooftops_20261001/run_captures.sh <tag> <cam+cam+...> [off]    # editor captures, <= 6 cameras per run; off = root hidden in memory
```

Blender reviews: `review_kit.py -- <lod> [ids] [front|back|top] [aim-y]` (line-up with a 1.8 m figure) and
`review_street.py -- [cams] [before]` (the shops, booth, hall and hill LOD1s with the kit, from the `cam_rt_*` views).
`scene_cams.py` reads any `cam_*` from the saved scene. `roofs.py` holds the roof data (decks, copings, obstacles, smoke).

## Licences

All geometry and textures are original to this project. The two stools and the crate on the Salvage roof are the street
dressing pass's CC0 Poly Haven props (`art/street_dressing_20260930/polyhaven/manifest.json`). No Meshy credits used.
