# Basic General neon sign (user-supplied Meshy model), 29 Sep 2026

Task: Ashfall t_196932d9. Source of truth for provenance; nothing here was regenerated with Meshy (0 credits spent).

- Original (never modified): `Meshy_AI_Neon_Command_Sign_0929072950_texture.glb`, 46,180,560 bytes,
  SHA-256 `3f77f2c733b62dfc450924e79bb729403236c253cdbb6056abaf8103e3a04dd1`.
  Copied from `/home/teknetik/.hermes/profiles/boss/attachments/`. Meshy task ID: not recorded in the file (filename timestamp 0929072950 only).
- Source inspection: 1 mesh, 1,241,878 triangles, 1.900 x 0.614 x 0.121 m, three 4096x1320 maps. Lettering "BASIC GENERAL" and "OPEN" is legible.
  Defect: a hard dark rectangle inside the C of BASIC (mesh patch bakes as a black block).
- `bake_sign.py` (Blender 5.2, Cycles): bakes the 1.24M-triangle relief to a 22-triangle front plate + side strips
  (`baked/sign_basecolor|normal|metalgloss|emission.png`, `baked/sign-mesh.json`, `baked/bake-report.json`). Raw bakes retained in `baked/`.
- `fix_artifact.py`: patches the rectangle artifact with feathered panel texture; writes `baked/runtime/*.png` (the Unity source maps). Raw bakes untouched.
- Unity: `Assets/AthenHill/Art/Phase1/BasicGeneral/Sign20260929/` (prefab, mesh, URP Lit material, textures), installed by
  `Editor/BasicGeneralSignPass.cs`. Evidence: `unity/evidence/basic-general-sign/20260929/`.
- Trade-off: the original 1.24M-triangle relief is baked into normal/albedo maps rather than shipped as geometry. Silhouette
  is a flat plate; the chamfered frame relief, letter extrusion and OPEN plate depth exist only as normal-map/albedo detail.
