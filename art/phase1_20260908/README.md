# Phase 1 Blender source — 8 September 2026

Original root repair and Finery frontage authored through the existing live
Blender MCP addon, Blender 4.5.13. Unity assembly uses the connected Unity MCP.
No runtime city generation, extracted game assets or source downsampling.

- `tree-audition.blend` retains the imported original tree.
- `tree-root-repaired.blend` retains the original trunk/root collection and the
  separately joined root flare. `repair_tree_roots.py` adds local junction volume,
  voxel-unions and smooths it; `refine_tree_uv.py` replaces a rejected hard UV
  projection switch with continuous flared-cylinder coordinates. `tree-root-mesh.json`
  carries the final normals/UVs into the saved Unity mesh without changing the
  existing root collision or upper crown. Root side stretching/crown work remains.
- `finery-frontage.blend` contains the separate measured building and practical
  entrance lamp. `author_finery.py` creates 263 modular parts / 50,300 triangles;
  `add_finery_lamp.py` adds four parts. Source inspection corrected the original
  door-band obstruction, a coplanar soffit edge and a missing front belt before
  installation. `review_finery.py` makes source previews; Unity/native images are
  the rendering authority. FBX exports retain the main construction; the saved
  blend and separate lamp interchange contain the later fixture addition.
- Finery's nominal parcel remains x16.2–25, z−21.8–−14.2 metres. Roof coping tops
  at 7.86m; closed double door leaves are 0.886m wide × 2.35m tall. The canopy,
  notices, planter, crates, porch and ground from the prior task are retained.
- Finery materials reuse the existing attributed courtyard sandstone/painted metal.
  Tree bark uses Poly Haven's CC0 Bark Willow 02. Full maps, source URLs and hashes
  remain under `refs/phase1_20260908/materials`; the shipping licence notice is updated.

The saved Unity prefabs, source geometry, materials and overrides remain editable.
Use `unity/EDITING.md`: show source renderers, edit, save assets, rebuild chunks,
then save/reopen. Exact scoped import/refit recipes and native evidence are under
`unity/evidence/phase1/20260908`. The complete Phase 1 visual target remains open.
