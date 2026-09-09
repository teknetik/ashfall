# Field Supply and Finery weathering — 9 September 2026

The user accepted the [weathering concept](../../refs/building_weathering_20260909/weathering-concept-v1.png)
and requested Blender implementation on some existing buildings. This pass covers
the installed Field Supply and Finery, retaining their dimensions, placement,
entrances, signs, gameplay roots and collider proxies. It does not reactivate the
rejected district shop candidates or replace the district.

## Editable source and production

Use **weathering-v3.blend**, authored through the live Blender MCP addon in
Blender 4.5.13 LTS. Units are metres. Source meshes were read from the saved Unity
scene into `unity-source.json`, including world positions, normals, UV0,
material paths and original object paths. Unity world coordinates map to Blender
as `(x, -z, y)`. This is a rotation, so triangle winding must be retained.

The authoring scripts `author_weathering_v3.py` and `refine_weathering_v3.py`
retain the steps and deterministic placement seeds. The first writes a base
revision and the second adds the final lettering and elongated plaster failures.
They are intended for an isolated live Blender authoring scene. Run them only
after saving other Blender work; the base script clears the current Blender data.
Version guards preserve the saved sources. Existing versions are not overwritten.

The final geometry consists of shallow, irregular missing plaster with mineral
substrate, chipped stone edges, cracked render, adhered flakes, shutter rust,
ragged curled paper, separately authored lettering and sparse dried blood marks.
Seventeen localized Unity decal projectors add drainage, foundation grime and
sheltered sand using the existing weathering atlas. Geometry changes are visual;
the original collision remains intact.

The export has 33 replacement parts and 391 new editable parts, totaling 21,245
triangles. The replaced originals had 6,024 triangles: the net source increase is
15,221. These are source triangles, not submitted render-pass counts. Render chunks
combine the small pieces for the player. No new texture atlas or source texture
downsampling was introduced.

## Unity installation and recovery

The current assets are in
`unity/AthenHill/Assets/AthenHill/Art/BuildingWeathering/20260909`.
The new prefab root is **Field Supply and Finery weathering**. The 33 existing
source MeshFilters retain their transforms and original materials, and now point
to separately saved weathered meshes. Original mesh assets remain untouched.

`BuildingWeatheringPass.cs` is an Editor-only explicit importer. Its install
operation refuses to overwrite an existing installation. Its update operation
updates this pass's mesh assets while retaining GUIDs and original instance pivots.
Both preserve gameplay/collision signatures and rebuild the derived render chunks.
Show source renderers before subsequent editing and explicitly rebuild afterward.

`unity/evidence/building-weathering/20260909/installation.json` maps every replaced
MeshFilter to its original mesh. To reverse this pass, restore those references,
remove this pass's prefab/root from the scene and chunk source roots, then rebuild
and save. Preserve unrelated scene edits; do not replace the whole scene from the
baseline copy. `before-scene.unity` is a recovery reference, not a reinstall script.

V1 and V2 remain as intermediate sources. Their winding conversion was incorrect;
they are superseded by V3 and must not be installed. The V2 Blender image is only
an intermediate source preview. Final acceptance evidence comes from the native
V3 build, linked below.

## Provenance

- Building geometry and PBR materials: existing project sources, unchanged
  originals recorded in `unity-source.json`.
- Karaveen poster, Ward Holds motif and factory wording: the user's existing
  `refs/courtyard_20260908` originals and generation manifest.
- New chip, crack, paper, rust and stain geometry: authored in Blender for this pass.
- The shutter's two lettering lines use converted DejaVu Sans Condensed Bold
  glyphs, perturbed and clipped across individual slats. The relevant font
  copyright and license are retained in `DejaVu-LICENSE.txt`.
- No Meshy task, external purchase, new faction history or gameplay system was
  created in this pass.

See the [native review and verification](../../unity/evidence/building-weathering/20260909/README.md).
