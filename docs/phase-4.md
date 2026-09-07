# Phase 4 — colonist and townspeople

Original Blender geometry and shared material atlas replace the scale capsule.
Two skinned material families share the same atlas: jacket/sleeves are tintable,
while skin, hair, cargo trousers, boots and metal retain their original colours.
The player has a beard; the lower-cost NPC master is clean-shaven. The NPC kit
uses the same body and equipment rather than four unrelated models.

Current authoring: 19 bones; feet origin; Three +Z facing; in-place idle, walk,
run and talk clips. Runtime player visual rotates by PI to match the established
-Z controller heading. Physics dimensions and the fixed-step controller are
unchanged. CharacterLibrary owns decoded geometry/materials/textures; each
instance owns an independent skeleton, mixer and jacket material. Asset errors
remain visible loading errors; the capsule is not a silent fallback.

Four NPCs: Mira at Basic General, Torr at the mission slab, Vex at the west gate,
Linn on the hill. Three ambient pedestrians follow clear pavement loops.
Names project above the actors; the nearest valid target exposes an E prompt
and gesture hook. Full conversations, commerce and travel verbs are Phase 5.

The source atlas is native 1254-square RGB, not 2048; generated eight-cell
materials and exact provenance are immutable under `refs/materials/07_*`.
The native source is retained unchanged; UVs inset from swatch boundaries.

## Verification

- Eight character ownership/validation/transition fixture checks pass.
- Six numerical controller regressions pass with an asset-independent visual
  fixture; new results are in `tools/phase4-support/physics-regressions.json`.
- Actual GLBs were decoded and rendered with four clips and independently
  tinted NPC instances. Final head/clothing geometry and production input captures are complete.
- First full city/native rendering: 120 fps, 57 draws, approximately 213k
  rendered triangles at 1920×1080, all eight animated bodies loaded. This is
  development-machine evidence; final target-laptop qualification remains open.
- Full production QA passes: `tools/phase4-support/runs/2026-09-07T10-35-27.326Z-21524/report.json`.
  120 fps at 1080p, 8.6 ms p95, 57 draws and 224,596 rendered triangles.
  Real E/W/Shift, actual bone movement, idle recovery, ambient motion, exact
  pause freezing, reset, six named captures and mobile input pass without errors.
  All 263 collider definitions/controller settings match the Phase 3 full route.
- Final hair-cap correction only removes inward scalp intersections; topology,
  rig, animation and physics are unchanged. Refreshed production capture/perf
  run: `tools/phase3-support/runs/2026-09-07T10-39-44.998Z-23126/report.json`.
  Its PARTIAL label means visual-only scope, combined with the full Phase 4 run.
  It passes 120.04 fps, 57 draws, 224,596 triangles, six captures and no errors.
- Final player: 12,648 triangles; NPC master: 5,262. Four clips, 19 bones,
  two skinned meshes/materials and one 1254-square source atlas per export.
  All sampled animation cycles have zero horizontal root drift. A walking sole
  can dip about 1 cm below the pavement after player offset; this is an animation
  contact detail, not a capsule/collision failure.
- Phase 4 accepted. The characters are stylized original geometry; final art
  comparison, audio and target-laptop performance remain Phase 6 work.
