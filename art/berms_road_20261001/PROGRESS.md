# Berms road ground to V2 — progress (1 Oct 2026)

Workstream 10 (next-wins item 12). Owner of `Outer Berms/Berms ground` material + splat only.

## Done (installed, verified)
- Survey + refreshed audit; before editor captures (6 cam_br_*).
- Poly Haven fetch, pack_layers.py (5-slice BC7 arrays), make_splat.py (West Gate reproduction exact, new road),
  edge_stones.py (24 stones + 2 cairns, layout ok), cams.py (8 cam_br_*).
- Shader *Athen Hill/Berms Ground V2*, material.json → BermsGroundV2.mat; 3 preview iterations (rock only on steep
  floor slopes, drift sand paler, lag share in splat 2 B, softer windrows, warmer loose gravel) + wide preview.
- 15:55 install (-nographics): rollback scene copy, material swapped, stones + cairns, footstep map rebaked.
- 16:03 cameras,tune (cairn shadows),verify: all checks pass (verify-saved-scene.json).
- After editor captures (12 views) + before-after-sheet.jpg; evidence README; DOCS_SNIPPET; README.

## Next (only if the orchestrator's combined test reports defects)
- Native 13:00/20:30 look of cam_br_*; frame-time A/B is the orchestrator's.
- Possible fix round: loose-gravel texture (rounded pebbles), floor saturation, edge stone tint, more cairns.
