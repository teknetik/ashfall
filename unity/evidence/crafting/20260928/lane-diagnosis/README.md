# West-lane traversal diagnosis — 28 September 2026

Task t_72cffc2d. Workspace `/home/teknetik/code/ao2-crafting`; HEAD/base `0b4496adf34d0eb01a6f5050cac1b163989ad923`.

## Finding: baseline test-route assumption, not crafting regression

The old real-keyboard route failed twice in independent QA at (12.0893412, .0299998522, 20.8136311). Those original failures remain in `../independent-qa/city-native` unchanged.

A Unity capsule cast using the saved player controller (height 1.8, radius .35, skin .03, centre y .9) from that exact position towards negative Z hits `Post-war salvage/generator scatter 48`, scene collider fileID **1019093120**, at distance **.0300022587**. Contact (12.0986195,.706670463,20.4337521), normal (-.0265091918,0,.9996486). The generator is at (12,.005,20); its box bounds are x 11.26296–12.73704, y .005–1.003071, z 19.5499249–20.4500751. It is taller than the .3 controller step offset.

The preceding `crate scatter 49` (fileID 1394747008), at (13.65,.005,21.3), spans x 12.9950428–14.3049564 and z 20.6450424–21.9549561. Thus the nominal x=13 straight-line segment first encounters the crate; leftward sliding towards the generator explains the observed x=12.09 stop (inference from geometry and the prior runtime endpoint, not an instrumented contact trace).

`LaneCollisionProbe.cs` loaded the current saved scene and a separate temporary copy of `git show 0b4496ad:unity/AthenHill/Assets/AthenHill/Scenes/AthenHill.unity` with Unity. `current-collision.json` and `base-collision.json` contain identical controller, cast-hit and nearby-collider data after sorting by hierarchy path and excluding only the temporary scene GUID. All 15 nearby colliders match. This comparison uses current project assets: the only dirty prefab assets are the two Outer Berms droids, not these colliders. The crafting scene diff adds its fabricator at x=-75 and does not alter any lane transforms/colliders. PlayerMotor is unchanged. This is not a pristine-base executable run; it is an exact baseline-scene collision comparison plus real-input current-player validation.

The lane remains walkable around the props. Do not delete or move accepted salvage to satisfy an obsolete straight-line test assumption.

## Minimal correction and rollback

Only `unity/tools/walk_route.py` changes outside this evidence directory. Four intermediate waypoints walk around the existing crate/generator and back to the lane: (10.5,0,23), (10.5,0,18.8), (12,0,18.8), (13,0,12). Every original endpoint and its ordering remain, including west_lane_south and west_lane_north. Grounded/height assertions, .20 horizontal arrival tolerance, timeout and stall detection are unchanged. The historical 'north' name still denotes the original negative-Z target; no landmark was renamed.

Rollback is `git apply -R unity/evidence/crafting/20260928/lane-diagnosis/test-route.diff` from the repository root, after checking no later edits overlap. This reverses only this test change. `initial.diff` and `initial-hashes.json` capture the pre-existing dirty work. `verification.json` confirms every initially dirty/untracked file outside this evidence directory is byte-identical after testing, and verifies every original route endpoint remains. No scene, GUID, visual, runtime, prefab or unrelated implementation file was changed. No commit/push/deploy. No devui access. The temporary probe script and copied baseline scene were removed from Assets; a reproducible source copy is retained here.

## Actual execution and results

All commands below ran from `/home/teknetik/code/ao2-crafting`.

1. `/home/teknetik/Unity/Hub/Editor/6000.6.0f1/Editor/Unity -batchmode -nographics -projectPath /home/teknetik/code/ao2-crafting/unity/AthenHill -executeMethod LaneCollisionProbe.Run -quit -logFile /home/teknetik/code/ao2-crafting/unity/evidence/crafting/20260928/lane-diagnosis/collision-probe.log` — exit **0**. Probe was temporarily under Assets/AthenHill/Editor. Separate base/current JSON confirms identical local physics.
2. `uv run --with python-xlib python unity/evidence/crafting/20260928/lane-diagnosis/run_checks.py city` — exit **0**. `city-native/report.json`: passed true, route_exit **0**, no runtime exception lines. `keyboard-route.json`: complete true. `route.log`: all original checkpoints plus four detour checkpoints passed; West Gate → hill/tree/stairs → Ring Gate → west lane → Lattice. Walking used actual W input; QA changed camera yaw, not player position, between route checkpoints. Separate positioned city checks passed Vex/Torr/Linn dialogue, modal blocking, exact shop buy/sell credits, Lattice link, four NPC flags, inventory, notes, pause, offline Ring Gate and R reset.
3. `uv run --with python-xlib python unity/evidence/crafting/20260928/lane-diagnosis/run_checks.py crafting` — exit **0**. `crafting-native/report.json`: passed true, no runtime errors. Actual E/F/Enter drove pistol pickup, four loot events, craft, fit and test fire. Ingredients servo/alloy/residue 2/4/6 → 1/2/1; one grip crafted then consumed into fitted slot; recoil 38 → 31, subsequent kick 1.55000007 degrees. QA positions player/camera for combat and UI stages, as in the existing harness.
4. `/home/teknetik/Unity/Hub/Editor/6000.6.0f1/Editor/Unity -batchmode -nographics -projectPath /home/teknetik/code/ao2-crafting/unity/AthenHill -runTests -testPlatform EditMode -testResults /home/teknetik/code/ao2-crafting/unity/evidence/crafting/20260928/lane-diagnosis/editmode.xml -logFile /home/teknetik/code/ao2-crafting/unity/evidence/crafting/20260928/lane-diagnosis/editmode.log` — exit **0**, fresh XML **77/77 passed, 0 failed/skipped**. Crafting and existing city tests included. This and command 3 ran sequentially with &&; overall exit 0 proves both succeeded.
5. Route AST preservation and initial dirty-file hash verification — exit **0**. `git diff --check -- unity/tools/walk_route.py` — exit **0**. Whole-worktree `git diff --check` — exit **2**, only the five unchanged Unity YAML whitespace warnings already documented upstream.

Native checks deliberately reused the existing independent-QA development player; no runtime/asset change requires a rebuild for this test-only correction. `verification.json` records executable, runtime assembly and level hashes/mtimes. The wrapper executes the existing city/crafting harness source with fresh evidence destinations, preserving earlier evidence. Check `route_exit` as well as `passed`: the inherited city harness can continue after a route failure; this run has route_exit 0.

## Remaining gate and limitations

Independent child t_4d4b6e3a must review the test-expectation correction and rerun full native traversal/crafting before integration t_a915d86c. This diagnosis does not waive that gate. No new release build or release gameplay qualification was performed; previous independent release-build timeout remains for QA to resolve. No 1920×1080 frame-time/visual-quality claim. Native failed-craft/double-spend UI branches were not exercised here; EditMode coverage passed. This investigation classifies the reported local blockage, not every possible collision in the district.
