# Scene survey used for retrofit placement

Produced 26 Sep 2026 from the saved `AthenHill.unity` at commit 31720d5 by
`AthenHill.Editor.DistrictRetrofitSurvey.Heightmap` (batch mode).

- `top.f32` — highest visible surface (m) on a 0.25 m grid, raycast against temporary
  MeshColliders built from every enabled MeshRenderer (render chunks, props, trees).
- `block.f32` — 1 where a player-blocking collider exists between 0.2 m and 3 m.
- `grid.json` — origin/step/size (Unity x/z). Row-major, z rows, little-endian float32.

Regenerate after layout changes; `kit.py` reads these to seat roof equipment and to
check that infill avoids existing obstacles.
