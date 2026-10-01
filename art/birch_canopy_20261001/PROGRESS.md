# Birch canopy & bed uplights (1 Oct 2026, batch 3) — progress

## State: DONE (17:50), installed + verified (-nographics, 0 problems); pending the orchestrator's combined batch-3 test

## Done
- 17:10 read briefs (14-birch-canopy, BRIEF memory safety + DoD), next-wins item 11 + section 4, courtyard-trees README /
  CourtyardTreesPass.cs, night_life + night_facade READMEs, EDITING.md sections.
- Verified: birch 4b crown = TreesBundleB `leaf y` (URP Lit, yellow `leaf 3 zhel`, tint 1/.895/.703, metallic from HDRP
  mask R = 0.17), brightest mass in batch-2 cam_hill 13:00; no wind. Circuit 90/150 m, lampStrength 1 from 19:00.
- 17:20 survey + audit + before captures + 32-light cull probe: OpenGL Core keeps the 30 NEAREST local lights (+ sun,
  fill) of 68-85 visible in the courtyard; beyond ~26-36 m everything is dropped (district-wide). Bed uplights kept in
  all bed/crown views.
- 17:30 Shaders/WardCanopy (fork of Ward Tree), BirchCanopyPass build (6 materials + lens, 10 baked meshes), preview
  captures r1-r3 (transmission fill, split uplight roles: trunk wash + crown beam, BC_UplightLens .55).
- 17:38 install (rollback copy, originals.json) + verify 0 problems; apply x3 tuning leaf value (base .80 kept; .70 too
  dead); final editor captures editor-after (6 cams); crown stats sat -28 %, value -5 %; verify 0 problems.
- README, evidence README, DOCS_SNIPPET, layout_check.py (0 problems).

## If a fix round comes
- Look/lights: edit canopy-tune.json -> `BirchCanopyPass --steps apply,verify -nographics`.
- Bake (occlusion/season/normals): `--steps build,apply,verify -nographics`.
- Full revert: `--steps rollback -nographics`.
