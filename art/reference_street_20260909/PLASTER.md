# Reference street plaster source · 9 September 2026

`author_plaster.py` is an original Blender authoring recipe for the Field Supply
and Finery plaster. It uses the user's September 9 street image as a visual
reference for worn limewash and localized mineral deposits. It copies no pixels
from that image. Existing plaster meshes, source photos, material bakes and
Blender files remain intact.

Execute the script through the live Blender MCP after inspecting the connected
instance. It creates an independent scene and saves
`reference-plaster-studio-v1.blend`; it refuses to overwrite an existing source.
The editable nodes use the repository's full 4K CC0 Poly Haven `beige_wall_001`
and `rough_concrete` inputs. Their authors, licence records, source URLs and
hashes remain under `refs/quality_20260909/building-materials`.

Run each bake separately through the same live MCP session:

```python
bake_reference_plaster('Plaster')
bake_reference_plaster('MineralRunoff')
```

Alternatively set `FAMILY` and execute `bake_plaster.py`; that entry point extracts
only the bake function with `ast` and works when the live connection does not
preserve Python names between calls. Never repeat one-time scene creation. Each
bake refuses to replace existing outputs and records Blender version, device,
timings and SHA-256 hashes.

The plaster retains four metres per existing UV0 tile and outputs full 4096²
BaseColor, Normal, Roughness and Metallic PNGs under `textures/ReferencePlaster`.
BaseColor is sRGB; other maps are linear. The normal is tangent space OpenGL +Y,
with no green-channel inversion. Use URP Lit and pack metallic into red and
`1 - Roughness` into alpha. Preserve full-size originals, mipmaps, streaming and
anisotropy. The 35 renderer paths in `plaster-manifest.json` are the complete
assignment scope. Existing geometry, UVs, transforms and collision stay intact.

The new layers add uneven mineral exposure, connected repair margins, partial
limewash and gated fine fissures. Procedural layers close at tile borders; source
photographic texture continuity remains inherited from the existing CC0 tile.
Cracks are confined to colour/normal response; there are no raised black fracture
strips. The additional normal relief is below two millimetres. This is source
authoring intent; player-distance and temporal review must assess the final bake.

`plaster-details.json` contains eight optional 1.5 mm offset transparent surface
films at selected coping and jamb joints. Each row provides world Unity positions,
normals, UV0 and triangle indices. Unity coordinates map to Blender `(x, -z, y)`.
Import them under one new editable root, with no colliders and no shadow casting.
They must use the separate **MineralRunoff** material, URP Lit transparent alpha
blend with depth writing off, smoothness 0.03 and metallic 0. BaseColor's sRGB RGB
and linear alpha are packed by Blender into a 4096² RGBA PNG under
`textures/MineralRunoff`; `Alpha.png` retains the original scalar mask. Clamp the
texture rather than repeat. Do not use these films with an opaque material.

No other scene content is targeted. Existing runoff projectors remain; if a film
overlaps one or darkens the facade excessively in native review, omit that optional
film rather than piling up opacity. Source nodes, placements, manifest and all bakes
are reviewable separately. Rebuild Unity render chunks after source material edits.

This directory contains an authoring recipe until the root agent runs it through
Blender. A successful source bake does not establish native visual acceptance.
