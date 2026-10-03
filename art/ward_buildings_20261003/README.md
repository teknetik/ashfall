# Ward buildings that still needed replacing — 3 October 2026

Carl (2 Oct 2026): "There are buildings in ward that need replacing too." `AUDIT.md` lists every building in the walls
and ranks the ones not yet rebuilt; this pass rebuilt ranks 1–6 (rank 7, the Lattice hoop, is a gameplay object left for a dedicated pass; rank 8 checked clean).
Round two (defect fixes, the four tower variants, the hall's salvage works and the West Gate bastions): `README_round2.md`. Nothing here is accepted by Carl yet. Per-building notes: `README_nanofab.md`, `README_watchtower.md`,
`README_hall.md`, `README_aquifer.md`, `README_tube_and_homes.md`. Progress / resume notes: `PROGRESS.md`. Unity side: `Assets/AthenHill/Editor/WardBuildingsPass.cs`.
Evidence (install/verify/build JSON, rollback scene copies): `unity/evidence/ward-buildings/20261003/`.

| Building | Scene root | Replaces (now inactive) | LOD0 / LOD1 / LOD2 tris (Unity, incl. lamps/props) | Lights | Review cameras |
| --- | --- | --- | --- | --- | --- |
| Nanofab 2 workshop | `Ward building: Nanofab 2` | `Ward district retrofit/Nanofab workshop` | 118.6k / 26.7k / 0.2k | 4 wall lamps on the clock + 2 always-on interior | `cam_wb_nanofab_{apron,front,bay,door,east,west}` |
| Warden corner watchtowers ×4 | `Ward building: watchtowers` | `Ward district retrofit/Watchtower 1…4` | 64.4k / 17.3k / 0.1k each | door lamp + searchlight per tower (8), on the clock | `cam_wb_tower_{nw,sw,ne,se,door,cabin}` |
| Processing 11 ruin | `Ward building: Processing 11 ruin` | `Ward district retrofit/Processing hall ruin` | 141.5k / 31.1k / 0.2k | none (a ruin) | `cam_wb_hall_{apron,city,door,inside,east,wall}` |
| AQUIFER 3 pump station | `Ward building: Aquifer 3` | `Ward district retrofit/Aquifer pump station` | 102.6k / 34.3k / 0.2k | 4 wall lamps on the clock | `cam_wb_aquifer_{market,front,door,well,tanks,droid}` |
| Quantum Tube goods nodes ×2 + conduit (6 pylon bays, 3 wall-hung spans) | `Ward building: Quantum Tube nodes`, `… conduit (pylon bays)`, `… conduit (wall-hung spans)` | `Ward district retrofit/Quantum Tube conduit` | node 19.0k / 7.7k; bay 6.8k / 0.9k; span 3.1k / 0.4k | 2 always-on status glows | `cam_wb_tube_{gate,node_e,port,node_w,run_e,span_w}` |
| Converted container homes ×5 (A rust, B stacked ×2, C sand) | `Ward building: wall homes (rust / stacked / sand)` | `Ward district retrofit/Perimeter dwellings` | A/C 5.7k / 2.4k, B 8.3k / 4.0k | porch light each (5), on the clock | `cam_wb_home_{south,stair,north,west,porch}` |

Stencils are painted lettering (no bevel, coarse curves; ~1k triangles each). Common construction: the shared Ward masonry kit (`art/ward_masonry_kit`) through the hall district's `Shop` class
(pointed at other parcel sizes by `parcel()`), plus this pass's `Building` (corner piers with riveted blackened-steel
bands, composite sci-fi module, half-raised loading bay with a lit room, Warden banners, stencils, prop mounts) and
`Ruin` (double-faced ashlar walls with broken stepped tops, ashlar piers, trusses, loose fallen blocks, sand mounds)
classes in `author_buildings.py`. Masonry is Athen Hill/Masonry Lit (VH_* hall materials: vertex AO, runoff, rust,
worn arrises, old battle damage). Wall lamps are the shop family (PH_WallLamp + NF bulb + down-and-out cookie spot,
values from the night facade tune). LOD0/LOD1 are full authored meshes, LOD2 a flat massing; LOD switches at about
25–35 m / 75–80 m (PC lod bias 2), culled at 650–900 m.

New materials (`Assets/AthenHill/Art/WardBuildings/Materials`, defined in `layout.json` → `materials`):
WB_BlackSteel (blackened riveted steel), WB_CompositeScorched / WB_CompositeFresh (panel variants beside WS_PanelDark),
WB_Hazard (the 26 Sep retrofit's hazard-stripe texture, copied to `Art/WardBuildings/Textures/WB_Hazard.jpg`),
WB_StencilPaint, WB_PaintBone, WB_PipeTeal, WB_ContainerBlue, WB_ContainerSand, WB_SolarPanel, WB_LedCyan, WB_ScreenCyan (emissive with RealtimeEmissive GI flags so `_EMISSION`
survives saving — see the WS_LedCyan note in PROGRESS.md).

## Run order

```
O=/home/teknetik/.local/state/ward-programme
$O/blender.sh author_buildings.py -- nanofab watchtower hall aquifer tubenode tubeseg tubespan homea homeb homec          # glbs + <key>.json + <key>-source.blend (~30 s each)
$O/blender.sh review_buildings.py -- Nanofab2 views=front,approach,bay,upper,east,west,rear,high   # Cycles CPU source renders
$O/blender.sh review_buildings.py -- Watchtower views=t_front,t_quarter,t_cabin,t_ladder,t_base,t_high
$O/blender.sh review_buildings.py -- Processing11 views=h_city,h_quarter,h_door,h_inside,h_east,h_high
$O/unity.sh <log> AthenHill.Editor.WardBuildingsPass.RunBatch --steps build:nanofab,build:watchtower,build:hall,build:aquifer,build:tubenode,build:tubeseg,build:tubespan,build:homea,build:homeb,build:homec -nographics
$O/unity.sh <log> AthenHill.Editor.WardBuildingsPass.RunBatch --steps install:<key>,verify -nographics   # one time per key
DISPLAY=:0 WAYLAND_DISPLAY=wayland-1 $O/unity.sh <log> AthenHill.Editor.WardBuildingsPass.RunBatch --steps capture:<key>[:cam+cam] --out <dir>
```

`install` refuses when the root exists (`reinstall:<key>` replaces it during authoring and keeps the first rollback copy).
Rebuilding a prefab (`build:<key>`) updates the installed instances through their prefab link. Rollback: re-activate the
retired retrofit group(s) and deactivate the new root, or restore `unity/evidence/ward-buildings/20261003/<key>/rollback/`.

## Sources and licences

- Geometry: authored procedurally in Blender 5.2 (this folder) on the Ward masonry kit; stencil lettering Stardos
  Stencil (SIL OFL, `art/west_gate_20260926/fonts`).
- Props mounted in Unity: Street dressing kit (`Prefabs/StreetDressing/SD_*`, CC0 Poly Haven scans) and West Gate kit
  (`Prefabs/WestGate/PH_*`, `WG_Sandbag*`, CC0) — provenance in their own passes.
- Concepts: Codex image_gen through `codex exec` (ChatGPT plan, no API key), prompts beside the images in `concept/`
  (`*_prompt.txt`); references were native lookbook frames of the old buildings and the accepted West Gate arches.
- No Meshy credits were used.
