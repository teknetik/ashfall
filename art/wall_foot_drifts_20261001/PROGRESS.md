# Wall-foot sand & grounding — progress (1 Oct 2026, batch 3)

Status: STARTED. Reading briefs, paving/walls/arches READMEs.

Orchestrator go-ahead received (1 Oct, batch-2 build taken): install into the saved scene is allowed once the kit is reviewed
(one-time install with rollback copy, verify -nographics). Editor captures: close views only, <= 6 cameras, no wide views.

## Done
- Scene audit refreshed: unity/evidence/wall-foot-drifts/20261001/audit.json (16:08).

## Next
- Read paving README (ground material/colours), perimeter walls + west gate arches READMEs (avoid duplicating their sand).
- Refresh scene audit (-nographics).

## 16:50 status
- Kit authored (author_drift_kit.py -> WFD_Kit.glb, kit.json); smooth-max bias bug fixed (flat 4 mm sheets), Blender review r1/r2.
- Textures (make_textures.py): sand albedo/normal (dense_sand CC0 graded, procedural ripples), 4 decals.
- faces.py -> faces.json; probe_faces.py -> probe.json (real wall-foot offsets; shop sides/rear below 0.5 m are the old
  porch slab drawn by render chunks -> fallback offset -5 mm).
- layout.py -> layout.json: ~325 pieces, ~240 decals, 0 problems.
- Unity: WallFootDriftsPass.cs compiled; build step OK (8 prefabs, sand + 4 decal materials).
## Next
- Editor capture round 1 (<= 3 close cams, in memory, never saved) -> tune material/decals/density.
- Install (one-time, rollback copy) + verify -nographics. README, DOCS_SNIPPET.

## 17:05 status — INSTALLED
- Editor rounds r1 (colour too pale/grey, hard decal ends, decal on risers: shared decal graph has angle fade off),
  r2 (recalibrated sand, own WFD_Decal graph with angle fade, soft-ended non-tiling decals, smooth kit fields),
  r3 (band feathering, density, camera fixes).
- Install (one time) done 17:0x: 334 instances, 320 decals, rollback copy evidence/.../rollback/before-wall-foot-drifts.unity.
- verify-saved-scene.json OK (prefab-linked 334/334, 0 missing materials, 0 shadow casters/colliders/lights, chunk fingerprint matches).
- Installed layout re-validated against a post-install audit: 0 problems (review/validate-installed.json).
## Next
- Final editor capture of the saved scene (3 cams on/off), README, DOCS_SNIPPET, evidence README, report.

## 17:10 — DONE (awaiting the orchestrator's combined test)
- Final editor captures of the saved scene: unity/evidence/wall-foot-drifts/20261001/editor-installed (off/on pairs).
- README.md, DOCS_SNIPPET.md, evidence README.md written. Iteration PNGs (r1, r2) converted to JPG; audits gzipped.
- Not done by design (revised DoD): player build, native lookbook, A/B, city loop.
- Known: sparse sand on porch decks (doors/bays/frontage props kept clear), post collars can read as discs, night and
  native look unreviewed.
