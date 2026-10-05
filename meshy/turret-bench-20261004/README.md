# Meshy sentinel turret and cybernetic bench — 4 October 2026

Supplied by Carl (Meshy web exports, downloaded 4 Oct 2026 18:40) "to replace the turret and benches". No task ids came
with the files and no credits were spent in this session.

| File | Triangles | Size (Meshy units) | Maps |
| --- | --- | --- | --- |
| `source/Meshy_AI_Sentinel_Turret_1004174027_texture.glb` | 370,290 | 1.90 × 1.49 × 0.83 (barrel span × height × depth) | 2k base colour, metal-rough, normal |
| `source/Meshy_AI_Cybernetic_Bench_1004174020_texture.glb` | 301,280 | 1.90 × 1.09 × 0.71 | 2k base colour, metal-rough, normal |

Both inspected before installation (`review/sheet_turret.png`, `review/sheet_bench.png`, Blender, four sides): single
clean meshes, no floaters, fused parts or holes; the turret's barrel and the bench's open shelf read correctly. The
bench's cyan strip is in the base colour only (no emission map). Measurements (`measure.py`, `backrest.py`): bench seat top
at 0.733 of the height, backrest on glTF −Z; turret barrel along glTF +X, base plate 0.83 m square, barrel axis 1.085
above the feet. Runtime preparation and installation: `art/turret_bench_20261004/README.md`. The source files are kept
untouched here.
