# Night facade tune (1 Oct 2026) — progress

Go-ahead received 1 Oct (batch-2 build taken): scene and shared material saves allowed.

## State: DONE (17:10), pending the orchestrator's combined native test (night look, frame time, city loop)

## Done
- 16:10 read briefs, night_life docs, EDITING.md, review item 10 + defects; looked at SD-F/SD-1 and batch-1 images.
- 16:30 WardWindowInterior.shader: _NeutralLight/_NeutralFraction (0 = previous look); original in rollback/.
  NightFacadePass.cs (offline compile check each time) + facade-tune.json.
- 16:34 runA (graphics): survey, shadercheck OK, build, editor-before captures.
- 16:40 runB (-nographics): remnant (floating-shadow caster = old Tool Exchange jib hoist), decalaudit (Finery
  Foundation grime 9/10 orphaned), install (originals.json, rollback scene), verify OK.
- 16:46 runC: fixdefects (2 decals off, hoist stripped into a mesh copy), verify, editor-after1: shadow gone; discs
  gone but facades too dark; cyan rooms too many.
- Round 2: cookie plateau, 130/90, tilt 10, out 0.15, x1.1; bulb 1.5; NF_WallLampGlass glowing globes; softer/fewer
  cool rooms; orchestrator's West Gate bulkhead request -> NF_BulkheadLens + bulkhead spot retune.
- 16:49 runD failed on another agent's compile error (nothing saved); 16:55 runD2: lightprobe, build, apply, verify,
  editor-after2 (incl. cam_wga_wicket).
- 16:58 runE bandprobe + 17:02 runF moonscan: the Finery porch band is the moon shadow of avenue lamp 02's mast, not a
  decal/reflection/specular (left to Carl: night key-light shadow strength).
- 17:06 runG round 3 (final): 140/95, x1.3; apply, verify (34/34 lamps OK, 0 missing materials, chunks match),
  editor-after3. Evidence README, comparison sheets, art README, DOCS_SNIPPET.

## If a fix round comes
- Edit facade-tune.json -> `NightFacadePass --steps apply,verify -nographics` (positions recomputed from originals).
- Cookie off if it costs: lamps.cookie false -> apply. Full revert: `--steps rollback`.
