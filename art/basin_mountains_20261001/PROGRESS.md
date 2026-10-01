# Basin mountains remesh + haze — PROGRESS (workstream 06, started 1 Oct 2026 ~12:00)

## Done
- Read BRIEF.md, prompt 06, next-wins item 1, EDITING "Mountains and terrain", shader WardDesertTerrainV2 (reads POSITION,
  NORMAL, COLOR.rg only: R = authored noon shadow, G = sky access; no UVs), DesertTerrainV2Install.cs, generator
  blender/scripts/18_desert_terrain.py (polar grid, Unity X = -x_script, Unity Z = z_script).
- Baseline: audit-before.json (fresh, -nographics), cameras.json (all cam_* world poses), native lookbook
  unity/evidence/basin-mountains/20261001/before-native (8 cams x 13/17/20.5, from the 12:00 LinuxDevelopment build).
- Heightfield (basin_heightfield.py, ~20 s, heavy.sh): original layout envelope -> 2 m stream-power incision -> 1 m
  stream-power gullies -> strata benches (aligned with shader beds) -> droplets -> talus -> rock detail; Berms footprint
  locked to the old surface (exact to 0.75 m, blend to 7 m, fixed base level, no-moat clamp). Sun bake for the scene's
  saved key (42, 220.6). work/heightfield.npz (git-ignored).
- Previews: preview.py ray-marcher from the real camera poses (work/preview/*.png).
- Mesh: basin_mesh.py RTIN, view-weighted error theta 0.006 -> 176,925 triangles (17-30k per chunk), 992 shared border
  vertices; basin_blender.py -> Assets/AthenHill/Art/Terrain/BasinMountains/BasinMountains.glb; verify_glb.py OK
  (positions exact, normals < 0.008, faces up, seam normals < 0.004).

- Shader: WardDesertTerrainV2 haze-shape props (defaults = old haze; backup of the original shader in evidence).
- BasinMountainsPass.cs: cameras, material (V3 from material.json), install, verify, previewbuild, abbuild:on|off.
- Iterations: iter1 (envelope + 2 m/1 m stream power; native iter1-native), iter2 (stronger incision + peak restore:
  spiky pinnacles, gravel heaps -> rejected), iter3 (tableland profile, gentler gullies, no peak restore; theta 0.0075,
  176,857 tris). FINDING: the striped lower west/south slopes in Berms views are the Berms ground mesh itself (1 m resample
  of the old faceted basin, up to 11 m) -> out of scope, reported.
- README.md, DOCS_SNIPPET.md drafted; ab_runs.sh / ab_summary.py adapted from the walls pass.

- iter4 (more benches/rock, sharper crests; theta 0.0105 -> 185,257 tris) accepted for install.
- INSTALLED in the saved scene (~14:45): material V3 (farScale 0.28, falloff 32, tint .88/.93/1.03, rockSlope .06),
  root 'Basin mountains', 8 old chunks inactive; rollback copy evidence/rollback/; verify.json ok.

- 14:50 Carl's change of process: stopped my A/B loop (partial cam_hill numbers kept), deleted Builds/bm-*.
- Review cameras cam_bm_* (6, player height) added and verified; layout_check.py OK; README, evidence README,
  DOCS_SNIPPET written. verify.json ok (185,257 tris, 8 chunks, 0 missing materials, old chunks inactive).

## Next
- Nothing pending on my side. Frame time and the city loop are pending the orchestrator's combined test; expect a fix
  round. Tuning knobs: material.json (haze, rock slope) via --steps material; geometry via run_all.sh then reimport.
