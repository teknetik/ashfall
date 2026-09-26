# Masonry v2 topology repair — 10 September 2026

This revision supersedes the **geometry** in hero-masonry-v1 for the same eight wall regions. It preserves the v1 failure outlines, masonry courses, material contract, wall envelopes, and 386 detail objects. It does not broaden the wear or alter gameplay/collision sources.

The v1 source weld tolerance was 0.1 micrometres. Original Unity bevel meshes contain duplicate seam positions separated by floating-point export error. At that tolerance, most original shells retained 88–120 boundary edges. Recalculating normals on the disconnected strips reversed some strips; applying solid Boolean subtraction to them then returned invalid surfaces. The 32–477 m³ signed-volume readings from those open, inconsistently oriented meshes do not represent physical wall volume.

The live Blender diagnostic `hero-masonry-v1-topology-diagnosis.json` tests 0.1, 1, and 10 micrometre welds. Both larger tolerances recover the original closed shells and their original signed volumes. V2 uses 10 micrometres before normal orientation. It also splits exact T-junctions where the previously subdivided stone face meets an unsplit chamfer edge and welds the coincident positions, retaining the surface shape.

Every cutter and source is checked for closed, contiguous, outward-oriented topology before subtraction. Every Boolean output must stay within its input bounds (10 micrometre floating-point tolerance), remain closed and outward-oriented, and have no increased volume. The exported authoring set contains eight replacement solids and 386 detail solids; all 394 pass those topology checks. All 22 cuts pass their envelope/volume checks. The final set has 96,134 triangles.

- `author_hero_masonry_v2.py`: live Blender authoring and guards.
- `hero-masonry-v2-geometry-proof.json`: per-cut and per-part evidence.
- `hero-masonry-v2-{replacements,additions,manifest}.json`: Unity import contract.
- `hero-masonry-v2.blend`: retained editable source, with originals in a hidden collection.

The manifest's `expectedCurrentMeshPath` fields refer to the retained pre-v1 source snapshot. The Unity v2 installer must guard against the actual installed v1 mesh paths separately. Native visual approval, runtime material/shader verification, and traversal remain required. Topology checks alone do not establish AAA quality.
