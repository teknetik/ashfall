# Basin mountains (1 October 2026)

Replaces the desert basin backdrop ring (`Desert Landscape/DesertBasin_00…07`, `Art/Terrain/DesertBasin.glb`,
640 triangles per chunk, 5,120 in all) with an eroded, adaptively meshed heightfield: scene root **Basin mountains**,
`Art/Terrain/BasinMountains/BasinMountains.glb` (eight chunks `BasinMountains_00…07`, same sector split as the old
`DesertBasin_00…07`), material `Materials/Terrain/SandstoneBasinV3.mat` (Ward Desert Terrain V2 shader).
Art-direction review item 1 (next-wins.md): faceted ridgelines, pale slope stripes, noon bleaching.

## What the old basin got wrong

The 8 Sep generator (`blender/scripts/18_desert_terrain.py`) sampled a good layout on a polar grid of 256 angular steps
and only 11 rings (t = 0, 28, 46, 53, 61, 72, 135, 169, 210, 263, 405 m beyond the city rectangle). Radial gaps of 30–140 m
made every ridge a straight facet, and its 6–30 m noise aliased from vertex to vertex, so the vertex normals flipped the
V2 shader's rock/scree mask column by column: the hard pale stripes down the fall line.

## Pipeline (run order)

`THETA=0.0105 ./run_all.sh` (everything through the memory-capped wrappers, about 2 min):

1. `basin_heightfield.py` (numpy + numba + scipy, `heavy.sh`, ~40 s) → `work/heightfield.npz`, `heightfield.json`.
   One 1025 × 1025 grid at 1 m in Unity world metres (X east, Z north).
   - **Envelope** = the original layout: front escarpment, crest ring, distant ring with their angular amplitudes,
     plan-view warped (bays, promontories, wandering crests), turned into a tableland profile (talus apron, cliff band at
     an irregular contour, slightly domed caprock), blended 75 % with the plain envelope.
   - **Stream-power incision** (`stream_power.py`: implicit Braun–Willett update, priority-flood routing so closed
     hollows drain): 2 m grid, 160 steps, drainage to the city basin and the map edge; area capped at 12,000 m² so no
     runaway gorges. Then a 1 m pass with a lower area exponent and a small seed relief cuts gullies and spurs into the
     short escarpment faces.
   - **Strata benches**: ledges every 3 shader beds (5.1 m), riser share varying per ledge (cliff-and-slope bands), on
     steep ground with a hardness mask, aligned with the V2 shader's world-Y beds (same warp: Geology.png R at 0.009/m,
     `sin(.024x + .018z)·2`), so the colour beds follow the landforms.
   - **Droplet erosion** (400k droplets) rounds bench edges and drops small fans; **talus** (37°) on soft ground;
     **rock outcrops** (ridged noise, 9–16 m) on steep ground.
   - **Outer Berms lock**: inside the Berms ground footprint (X −104…−60, Z −54…48) and 0.75 m around it the surface is the
     OLD basin exactly (barycentric on the old triangles; the Berms ground mesh is that surface + 0.04 m, so its toe is
     untouched), blending to the new terrain by 7 m. The footprint is a fixed base level for the erosion, so gullies grade
     onto the Berms floor, and within 20 m the new ground may not fall below the old more than 0.3 m per metre (no moat).
   - **Vertex lighting** (what the V2 shader reads): R = sun visibility for the scene's saved key (Euler 42, 220.6; the
     shader only uses it when the clock sun is near that key), G = sky access (8-direction horizon, same 0.22 maximum
     occlusion as before).
2. `basin_mesh.py --theta 0.0105` → `work/chunks/*.npz`, `mesh.json` (185,257 triangles: 00 29,516 · 01 24,683 ·
   02 17,404 · 03 22,666 · 04 21,241 · 05 17,823 · 06 25,454 · 07 26,470; 16-bit indices). One global RTIN (longest-edge bisection) with a
   view-weighted error (vertical error ÷ distance to the city rectangle or the Berms footprint): ~1 m triangles next to the
   Berms, 2–6 m on the crests 150–400 m out, large triangles on the hidden back slopes. Split by triangle centroid into the
   eight sectors after meshing, so neighbouring chunks share every border vertex, normal and colour exactly. Triangles
   under the city (> 0.75 m inside its rectangle), under the Berms ground (> 3 m inside its footprint) and beyond the old
   outer edge are dropped, with full refinement along those cut lines. Normals come from the heightfield smoothed at each
   vertex's own triangle scale (no distant shading sparkle).
3. `basin_blender.py` (`blender.sh`, 1 s) → the glb and `basin_mountains.blend`. Unity (X, Y, Z) is authored at Blender
   (−X, −Z, Y), as in the original generator; custom normals, `TerrainLight` colour attribute → COLOR_0, UV0 = XZ / 16.
4. `verify_glb.py` → `glb-verify.json`: positions exact, normals within 0.008, colours exact, all faces up, chunk-border
   vertices identical (normals within 0.002).

Previews without Unity: `preview.py` ray-marches old vs new heightfields from the scene's review cameras (`cameras.json`
from `BasinMountainsPass --steps cameras`) with a shader-like look and the haze curves; `profiles.py` plots old/new
radial profiles. Both write to `work/` (git-ignored).

## Unity

`Assets/AthenHill/Editor/BasinMountainsPass.cs` (`RunBatch --steps …`, menu Athen Hill → Basin mountains):
`material` (creates/updates SandstoneBasinV3 from `material.json`), `install` (one time; rollback scene copy, record),
`addcams` (review cameras), `verify`, `previewbuild` (iteration build from a temporary scene copy), `abbuild:on|off`
(A/B arms from one snapshot), `cameras` (dumps every `cam_*` pose for the previews).

Shader: `Shaders/WardDesertTerrainV2.shader` gained five haze-shape properties whose defaults reproduce the old haze
exactly (SandstoneBasinV2 and the Berms ground are unchanged): `_HazeFarStart`, `_HazeFarScale` (thinner haze beyond
38 + far start metres), `_HazeHeightFalloff`, `_HazeBaseHeight` (optical depth averaged through an exponential layer
above the base height), `_HazeNoonTint` (linear multiplier applied only under a high, strong sun: noon, not 17:00 or the
night key). V3 keeps the V2 density 0.0068 up to 138 m so the Berms ground toe still matches.

## Review cameras

Skyline (existing): `cam_hill`, `cam_avenue`, `cam_gate`, `cam_courtyard`, `cam_whompah`, `cam_westgate_mouth`,
`cam_berms_road`, `cam_berms_overview` — judge at 13:00, 17:00 and 20:30.
Player height (new, root **Basin mountains review cameras**, `review_cameras.json`, eye = Berms ground + 1.7 m):
`cam_bm_berms_west_toe` (west escarpment toe and face), `cam_bm_depot_south` (south-west massif over the depot),
`cam_bm_range_northwest` (north-west ring beyond the range), `cam_bm_toe_north_edge` and `cam_bm_toe_south_edge` (the
Berms ground's north and south edges, where the old surface hands over to the new), `cam_bm_apron_southeast` (the south
ring past the city's south-west corner). `BasinMountainsPass --steps addcams` rebuilds them.

## Layout check

`layout_check.py` → `layout-check.json`: inside the Berms footprint + 0.75 m the surface equals the old basin (0.6 mm),
along the city rectangle it stays at the old rim level, no marker or camera lies outside the city and the Berms footprint.

## Known defects / limits

- The pale, striped lower slopes beside the Berms road (west and south-west, up to about 11 m) belong to the **Outer
  Berms ground** mesh (a 1 m resample of the old faceted basin, `OuterBermsInstaller`), not to the basin; they are
  unchanged by this pass. Re-deriving that mesh's outer slopes from the new basin is a Berms ground task.
- Noon: the far massifs keep their form now but still read pale cream under the 13:00 sun (lit sandstone albedo plus
  haze); 17:00 is the strong hour.
- Some far crests are serrated (thin fins between gullies) and a few large gullies are straight V-gorges.
- The near west hills at 40–100 m read partly as rounded scree mounds at noon; at 17:00 their benches and gullies read.
- The inner edge follows the city rectangle to within about 1 m (triangles more than 0.75 m inside it are dropped) at the
  old rim level; a future wall-foot drift pass should sample this surface (or `work/heightfield.npz`), not the old one.
- Frame time and the city loop: pending the orchestrator's combined test (partial cam_hill A/B in the evidence README).

## Sources and licences

All terrain is procedural and original (this folder). Textures are the existing V2 set (Poly Haven CC0 Sandstone Cracks,
the Berms ground arrays, Ward SandstoneAlbedo/Geology). No downloads, no Meshy.

## Files

`basin_heightfield.py`, `stream_power.py`, `noise.py`, `basin_mesh.py`, `basin_blender.py`, `glb_io.py`,
`verify_glb.py`, `preview.py`, `profiles.py`, `layout_check.py`, `run_all.sh`, `ab_runs.sh`, `ab_summary.py`,
`material.json`, `review_cameras.json`, `layout-check.json`,
`heightfield.json`, `mesh.json`, `blender-export.json`, `glb-verify.json`, `PROGRESS.md`, `DOCS_SNIPPET.md`.
Git-ignored: `work/` (heightfield, chunks, previews), `basin_mountains.blend`.
