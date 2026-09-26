# Field Supply and Finery surface revision — 9 September 2026

This implements the requested improvements to surface variation, fine relief and
the angular damage in the previous weathering pass. Field Supply's plaster,
stone trim and shutter are the primary view; the same treatment covers Finery's
plaster, stone and louvres. Building placement, envelopes, entrances, approved
paper/lettering/blood and the existing localized drainage projectors remain.

## Material sources

`facade-material-studio-v1.blend` contains three editable layered materials and a
four-metre bake plane. `prepare_material_bakes.py` creates the nodes; execute
`bake_material.py` through the live Blender MCP with `FAMILY` set to `Plaster`,
`Stone` or `Steel`. The twelve full-resolution source bakes are under `textures/`.
`texture-manifest.json` records their dimensions, hashes, colour spaces and source.

The 4K photographic inputs already in the repository are retained untouched:

- `beige_wall_001`, by Dimitrios Savva and Rico Cilliers;
- `rough_concrete`, by Dimitrios Savva;
- `rock_surface` and `rusty_metal_sheet`, by Amal Kumar.

These are the existing CC0 Poly Haven inputs, with source pages, downloads,
metadata and hashes under `refs/quality_20260909/building-materials`. No new
purchase or external generation service was used. The new layers are original
Blender node authoring and Cycles GPU bakes in Blender 4.5.13 LTS.

Plaster blends faded limewash, ragged repair/aggregate boundaries, small mineral
pits and localized hairline fractures. Stone combines mineral colour variation
with smaller pores. Steel combines faded dark green paint and irregular oxide
patches with different roughness. Field Supply's previous shutter material was
flat WardPaint; it now uses the baked material set.

Four-dimensional periodic noise produces continuous procedural layers across a
tile. Colour, roughness and metallic values are baked through emission, so the
new bakes contain no directional scene lighting. Normal maps are baked in tangent
space with OpenGL +Y convention. The physical source relief distances are 8 mm
for the combined plaster layer, 6 mm for stone and 4 mm for steel, multiplied by
the smaller per-layer height weights. These are shading distances, not displaced
building silhouettes. The photographic normal response is also retained.

## Refined geometry

Use **facade-surfaces-v2.blend** and **facade-meshes-v2.json**. The original V3
weathering sources remain in `art/building_weathering_20260909`.
`refine_facade_geometry.py` reuses the accepted damage locations, substitutes
128-point irregular plaster outlines and detailed asymmetric stone cutters,
and adds small physical fracture bevels. `finish_facade_normals.py` corrects the
large wall planes after the Boolean/bevel operations: planar walls remain flat,
while their small sloped bevel faces can shade smoothly. V1's initial smooth
wall shading was rejected and its source/review retained.

The revision disables 258 old geometric flake, fracture-ribbon and rust-overlay
objects, retaining them for recovery. Fine damage is instead carried by the
baked maps. Existing exposed-substrate objects receive the refined meshes, so
their object identity and placement survive. Source UV0 uses an explicit
four-metre world scale with face-appropriate planar projection. Unity coordinates
map to Blender as `(x, -z, y)`; this rotation preserves triangle winding.

The 348 replaced visual parts comprise 35 plaster pieces, 243 stone pieces
(including 25 exposed substrates), and 70 shutter/louvre pieces. They contain
213,554 source triangles. Compared with the replaced source and disabled overlays,
the net source increase is 141,964 triangles. Source geometry is retained and
runtime render chunks combine it; submitted render-pass triangles are measured
separately. This is not a claim about visible whole-scene geometry.

## Unity import and recovery

`FacadeMaterialPass.cs` is an explicit Editor-only importer that refuses to
overwrite an existing installation. Assets are saved under
`Assets/AthenHill/Art/FacadeMaterials/20260909`. It retains source object transforms,
collider proxies and prefab links, verifies gameplay/collision signatures, and
rebuilds render chunks before saving the scene.

The full 4K source colour and normal PNGs are copied unchanged. Separate full
roughness and metallic bakes remain in this source directory. The importer creates
URP's packed map with metallic in red and `1 - roughness` in alpha. Base colour is
sRGB; normal and packed maps are linear. All runtime maps use full 4096 dimensions,
13 mip levels, mip streaming, 8× anisotropy and high-quality BC7 compression.
No green-channel flip is applied. The original source meshes had no UV1 lightmap
data, as recorded by the import check.

For recovery, use `unity/evidence/facade-materials/20260909/installation.json` to
restore each MeshFilter and material array, and reactivate the listed overlay
objects. Show source renderers before editing and rebuild afterward. Do not
replace the whole scene from the baseline copy over later user edits.

See the [native evidence](../../unity/evidence/facade-materials/20260909/README.md)
for matched captures, first-person and lighting review, traversal and performance.
