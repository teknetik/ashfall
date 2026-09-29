# UDS scene-preview investigation — 28 September 2026

Task: `t_d8e8c118`; workspace `/home/teknetik/code/ao2-crafting`, branch `feature/ward-crafting`. No commit/push. The pre-existing crafting work remains uncommitted.

## Diagnosis and smallest repair

The failing hash `uds:/1e/1e80c621078ed4b660caaad45bcd9d32` belongs to the imported **WardenBooth.glb**, GUID `4fc244ec69769395ab5ec45ebcc36fb7`, not KaraveenMarket.glb (`e6d28f8511d80ab9cac79935a54262e2`). The scene-preview stack names `VirtualArtifacts/Primary/4fc244ec69769395ab5ec45ebcc36fb7`; its `.meta` resolves the dependency unambiguously. The nearby market QuickSearch import line in the original log was not evidence that market caused the failure.

`before-quarantine-UDS-Service.log` contains the decisive sequence:

- Line 19: removed broken write entry for this hash from an invalid execution state.
- Line 21: cannot create file because `Library/DataStore/Temp/1e80c621078ed4b660caaad45bcd9d32` already exists.
- `before-quarantine-Editor-UDS.log`: attempts to read that hash fail because its file type is still `Queued`.

That orphan temporary payload was 411,214,555 bytes. The service cleared the broken write registration, but the leftover destination blocked the next write. Repeated startup imports recreated the same broken state. Explicit synchronous booth reimport allowed both assets and a preview scene to load in the same process, but a fresh process still failed. OpenGL-enabled reimport behaved the same, ruling out `-nographics` as a sufficient explanation/fix.

With Unity and UnityDataStore stopped, moved only that one generated temporary file to:

`/home/teknetik/code/ao2-crafting/unity/AthenHill/Library/UdsQuarantine-t_d8e8c118/1e80c621078ed4b660caaad45bcd9d32`

Unity's next startup automatically regenerated the missing booth artifact. No asset, importer, scene reference, package, test assertion, or engine version was changed. No whole-cache purge, city regeneration, or suppression of test logs was needed. The initial event that interrupted the original UDS write is not established; the persistent failure mechanism and repair are established by the service log and controlled before/after runs.

Rollback: the quarantined bytes remain available. Restore them to their exact original `Library/DataStore/Temp` location only with Unity stopped and only if deliberately reproducing the fault; that would reintroduce the collision. Scene/importer snapshots and the initial dirty diff are retained here, not applied over user work.

## Executed validation

All Unity commands used `/home/teknetik/Unity/Hub/Editor/6000.6.0f1/Editor/Unity` and `-projectPath /home/teknetik/code/ao2-crafting/unity/AthenHill`.

1. Baseline: `-batchmode -nographics -runTests -testPlatform EditMode -testFilter AthenHill.Tests.CheckpointAssetTests`. Exit 2, both tests failed; `../uds-baseline.{xml,log}`.
2. Explicit booth reimport: temporary diagnostic entry point `AthenHill.Editor.UdsAssetProbe.ReimportBooth`, with `-quit`. Both headless and `-force-glcore` runs load booth (411 sub-assets, 73 meshes, 16 materials, 26 textures) and market (646 sub-assets, 64 meshes, 82 materials, 204 textures) in-process. Market preview had 64 mesh filters, zero missing meshes/materials. Logs: `reimport-booth.log`, `reimport-booth-gl.log`. A fresh full suite still failed 69/77 (`all-tests-after.{xml,log}`), and fresh checkpoint tests after OpenGL reimport also failed (`after-gl.{xml,log}`). This was NOT accepted as a fix.
3. After quarantining the single orphan: fresh checkpoint suite **2/2 passed**, exit 0 (`after-quarantine.{xml,log}`).
4. Another fresh Unity process, `-batchmode -nographics -runTests -testPlatform EditMode`: full suite **77/77 passed**, no skips, exit 0 (`all-tests-repaired.{xml,log}`). All eight original scene-preview failures are resolved. Zero UDS read-handle errors.
5. Rebuilt native players via `-batchmode -nographics -executeMethod AthenHill.Editor.LinuxBuild.Development -quit` and the corresponding `.Release`. Both **Succeeded, 0 errors, 346 warnings**. Build logs and copied reports are `development-build.*` and `release-build.*`; neither log has UDS read-handle or scene-opening errors. These replace the prior 10-error release result. Warnings remain, so these are not warning-free builds.
6. `uv run --with python-xlib python unity/evidence/crafting/20260928/uds-investigation/check_market.py`: exit 0. Real Enter started the rebuilt development player; QA only selected existing cameras, fixed 16:00 time, and captured frames. `native-market/report.json` lists five captures, reports success, and has an empty runtime-exception/UDS-error list. Its source snapshot and full Player.log are retained.
7. Removed the temporary Editor probe (archived as `UdsAssetProbe.cs.txt`) and restored only Unity's incidental `SENTIS_ANALYTICS_ENABLED` project-setting change. Fresh final checkpoint tests **2/2 passed**, exit 0 (`final-cleanup-tests.{xml,log}`), proving no dependency on the temporary probe.

`before-sha256.json` and final verification establish that the dirty saved scene and both importer metas remain byte-identical. `before.diff` preserves the starting tracked modifications. Source GLB SHA-256 values at intake: booth `d734ea44711ba93496156a1d2ab232d9a35b5293e017b1d88193cdbeaee475f4`; market `df798a4f015254af13b3bdfe23794fc9d04ca90eb9f37bfef47b1a0ea2c823ee`.

Runtime assembly hashes are in `build-identities.json`. They are unchanged from earlier builds because this is an imported-content cache repair, not a runtime-code change; assembly timestamps alone do not establish this rebuild. The new BuildReports/logs establish the actual build execution.

## Native visual integrity

Inspected actual rebuilt-player captures: `cam_market.png`, `cam_market_produce.png`, `cam_market_cookfire.png`, `cam_market_lane.png`, and `cam_checkpoint_locker.png` under `native-market/`.

- Market overview: populated stalls, corrugated and striped roofs, truck, bunting, signage, shelving and goods present.
- Produce close-up: canopy, wooden frame, crates, hanging produce, sacks, and price placard present and textured.
- Cookfire: lit barrel/pot, serving table, stools, bowls, sign and stall props present.
- Lane: continuous paving, market structures, truck, lamps and surrounding buildings present.
- Checkpoint close-up: textured locker, corrugated structure, cargo and chair present.
- No obvious missing mesh, magenta/error material, texture corruption, or broken major geometry visible in these views. Strong warm grading, shadows and HUD occlude some details. The checkpoint angle is tight; these are bounded visual-integrity observations, not full art acceptance or exhaustive coverage.

Environment: Unity 6000.6.0f1, OpenGLCore, NVIDIA RTX 3060, driver 610.57.04, Intel i9-10850K, PC quality. Requested 1920×1080; the compositor actually supplied **1890×1029**, as recorded by `environment.json`. No 1080p performance claim is made.

## Remaining scope and handoff

The UDS/market blocker is resolved. No runtime or asset-source repair is left in the tree; only evidence/documentation and the generated-cache quarantine were added by this investigation. Existing unrelated dirty work was preserved. Parent `t_64912f44` can resume verification; existing follow-up `t_bbb7e8e0` can independently confirm this diagnosis without repeating the failed market reimport.

The 346 build warnings were not remediated. Release bridge refusal and release gameplay were not exercised here; rebuilt release output is available for the parent's/QA's existing acceptance scope. The earlier crafting real-input smoke was not rerun because no gameplay source changed. No claim of complete city-loop QA, temporal/LOD review, performance qualification, or visual-quality-target acceptance.

Final preservation check (`final-verification.json`) passed every assertion, including exact equality of the full tracked diff before/after this investigation. `git diff --check` exits 2 on five pre-existing trailing-space lines in the dirty droid prefabs/scene; these were deliberately preserved, not introduced or reformatted here.
