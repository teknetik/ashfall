# Ashfall inventory and authoring, 2 October 2026

This work is isolated on `codex/ashfall-inventory`. Commit `4d991cf9` preserves the main checkout's in-progress source as it existed at intake. Inventory changes are the diff after that commit. Claude's subsequent Outer Berms work stays in the main checkout and is not overwritten or merged here.

## Main-checkout integration

Merged into `ward/next-level` on 2 October 2026, preserving the completed Berms and rifle work. The normal development player was rebuilt. Combined verification and build identity are recorded in [the integration report](../inventory-merged-20261002/README.md); the results below remain the isolated-build history.

## Implemented

- Compact carried-item grid, persistent inspector on its right, search/filtering and actual pack-slot and carried-weight limits. A slot is one carried item stack; equipped gear contributes to carried weight.
- Primary/secondary loadout tabs with a 2D illustration, attachment slots and a drag-rotated 3D weapon. The new generated Field Rifle is an inventory preview asset; the existing combat visuals are preserved.
- Static X-ray implant anatomy, selectable body slots and three augmentation sockets per installed implant. No 3D preview runs on the implant tab.
- Armour body slots and character preview, with configurable components and actual stat effects. Extra plates and leg motors use the equipment/module model and persist in saves. The preview uses the supplied character mesh; separate visible plate/motor meshes are not authored in this pass.
- Scrollable merchant catalogue left, selected item detail/price/stat comparison right. General traders sell priced gear/implants/modules; parts-only vendors keep their existing policy. Purchases and sales retain the atomic inventory/credit verbs and quest events.
- Item Lab uses server-held OpenAI credentials for reviewed item copy, ideas, item images and built-in voice auditions. Accepting a proposal edits a draft. Draft/media import into Unity remains an explicit authoring operation; generated voice auditions are not automatically assigned to NPC dialogue.

## Verification

Final full EditMode run: **233/233 passed**, Unity 6000.6.0f1, headless, final source revision `835bf6a0`. See `editmode-release.xml` and `editmode-summary.json`. The Linux development build succeeded; `build-record.json` records source and built-runtime hashes. The saved scene remains unchanged.

Final native run **40/40 passed**, source revision `835bf6a0`, Unity 6000.6.0f1 / Linux OpenGL Core. This covers capacity, pointer/keyboard/search behavior, fixed X-ray and three implant sockets without a 3D camera, augmentation and motor effects, real armour drag in both directions, weapon previews and rotation, atomic trades, 1280×720 controls and the full walked city loop. Forward Tab, Shift+Tab, text entry and clearing the merchant search pass after the earlier double-Tab fix. The city route completes all four conversations, flask purchase, scrap sale, hill/porch access and Lattice travel. The player log has no runtime errors. See `native-progress.json` for the compact summary and `native-final/report.json` for the full report; raw layouts and diagnostic traces remain in `../inventory/20261002/native-redesign-6/`.

All ten final UI captures were visually reviewed and are preserved in `native-final/`: pack details, implant augmentations, armour motor, both weapon views before/after rotation, merchant details and the two 1280×720 views. The equipment atlas renders cleanly, the whole X-ray stays visible and the independent detail scroll keeps actions reachable. The narrow 3D rifle pane is small and dark compared with the clear larger 2D illustration; this is a remaining presentation limitation. Separate visible plate/motor meshes remain outside this inventory pass.

The isolated fixture's short native-6 samples measured 37.1 FPS / 26.67 ms p50 with the inventory closed and 38.9 FPS / 25.70 ms p50 open (about 6.2 seconds each). These are scene-specific samples, not a whole-game performance qualification or evidence about the later combined build. Failed iterations are retained as diagnostic history.

Developer tooling: 27 backend/security tests, existing browser regression, focused authoring regression and JavaScript syntax checks pass. The one explicitly approved live text test succeeded (2,257 input + 94 output tokens); it did not edit game content. Image and voice transports were exercised with fixtures only. See `../inventory/20261002/developer-ui/verification.json` and screenshots.

## Review and recovery

- Run native UI regression: `uv run --offline --with python-xlib --with pillow python unity/tools/check_inventory_redesign.py OUT --exe unity/AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64 --profile-seconds 6` from this worktree, only with other Unity/player jobs stopped.
- Combined headless authoring export/build entrypoint: `AthenHill.Editor.CraftingDataExporter.BuildDevelopmentWithAuthoringExport`.
- Start Item Lab: `python unity/tools/devui/server.py --qa-dir "$HOME/ward-native-qa" --port 8765`, then open its loopback URL. It discovers the primary checkout's `.env` without copying keys into the worktree, browser or player.
- Reference images are in `references/`. Six equipment icon cells, originals and generation prompts: `art/inventory_icons_20261002/`. X-ray generation record: `implant-art.json`. Rifle prompts, task IDs and source exports: `meshy/field-rifle-20261002/`.
- Save schema is version 3, character schema version 2. Existing version 1/2 saves load; older builds must not rewrite saves containing the new nested module state. Native QA uses its own fixture/save directory.

## Integration boundary

This evidence certifies the isolated inventory development build and its intake scene, not the main checkout with Claude’s later Outer Berms, rifle and plate-carrier changes. Integrate the inventory delta after `4d991cf9`, preserve the later gameplay changes, and verify the combined development build separately. Native jobs use the shared `/home/teknetik/.local/state/ward-programme/unity.lock`, an isolated save and a wait for manually launched players to close. The Item Lab service is `ashfall-item-lab.service` and is available at http://localhost:8765.
