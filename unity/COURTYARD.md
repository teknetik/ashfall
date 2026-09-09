# Ward terminal courtyard · 8 September 2026

The focused courtyard pass adds chipped sandstone slabs, shallow shaped sand,
curved dry plants, a patched red canopy, masonry repairs and conduits, a salvaged
drum planter, illustrated notices and handwritten paint. It retains the three
accepted terminals and the existing city, actors, interaction roots and routes.
The user's image in `refs/courtyard_20260908/accepted-target.png` is the reference.
This pass brings the foreground toward that image; it does not establish the
reference's full street density, architecture or character fidelity across Ward.

## Editing

Open `Assets/AthenHill/Scenes/AthenHill.unity`. The saved prefab instance
**Courtyard reference pass** has named groups for Platform, Paving, North stairs,
Shop threshold, Sand deposits, Vegetation, Canopy, Awning hardware, Facade,
Wall graphics, Courtyard props and Gravel. Meshes and materials are ordinary
assets under `Assets/AthenHill/Art/Courtyard`.

Use **City Render Chunks → Show Sources for Editing** before editing these objects,
and **Rebuild Render Chunks** afterward. Original replaced visual renderers stay
disabled, with their collider proxies and gameplay objects retained. The planter
has its own capsule collider; the awning's supports stay above walking clearance.

`art/courtyard_20260908/courtyard-source.blend` and the adjacent FBX/JSON preserve
full source geometry. `author_courtyard.py` was executed through live Blender MCP.
The Editor-only `CourtyardPass` imports that focused asset family and refuses to
install over an existing root. It does not construct the city at runtime.
**Refresh authored geometry** updates only this family's mesh assets, retains
later object offsets and saves source assets before rebuilding the render chunks.
`AuthoredPivots.json` tracks import origins. Final paper positions and rotations
were fitted in Unity and saved into the prefab; see the reference README.

Stone materials expose broad wear and use independently imported base colour,
OpenGL tangent normals and roughness packed into smoothness. The thin-surface
shader lights both sides of leaves and canvas, casts matching moving shadows,
and uses the existing `_AthenAtmosphereTime` so reduced motion freezes the wind.
The local reflection probe is baked and box projected, at intensity 0.32. Existing
URP, OpenGL and user video settings remain the baseline.

## Provenance and verification

Original artwork, generation prompts, actual image dimensions and Poly Haven
CC0 source URLs/hashes are retained under `refs/courtyard_20260908`. Distribution
notices are in `Assets/AthenHill/Art/THIRD_PARTY_LICENSES.txt` and both player folders.
The source comparison, rejected auditions, native captures, moving walkthrough,
build reports, route audit and measurements are under
`unity/evidence/courtyard/20260908`. Read its final report for tested status and
remaining visual gaps. Earlier weathering evidence remains unchanged.
