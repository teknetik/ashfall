# Ashfall inventory and authoring, 2 October 2026

This work is isolated on `codex/ashfall-inventory`. Commit `4d991cf9` preserves the main checkout's in-progress source as it existed at intake. Inventory changes are the diff after that commit. Claude's subsequent Outer Berms work stays in the main checkout and is not overwritten or merged here.

## Implemented

- Compact carried-item grid, persistent inspector on its right, search/filtering and actual pack-slot and carried-weight limits. A slot is one carried item stack; equipped gear contributes to carried weight.
- Primary/secondary loadout tabs with a 2D illustration, attachment slots and a drag-rotated 3D weapon. The new generated Field Rifle is an inventory preview asset; the existing combat visuals are preserved.
- Static X-ray implant anatomy, selectable body slots and three augmentation sockets per installed implant. No 3D preview runs on the implant tab.
- Armour body slots and character preview, with configurable components and actual stat effects. Extra plates and leg motors use the equipment/module model and persist in saves. The preview uses the supplied character mesh; separate visible plate/motor meshes are not authored in this pass.
- Scrollable merchant catalogue left, selected item detail/price/stat comparison right. General traders sell priced gear/implants/modules; parts-only vendors keep their existing policy. Purchases and sales retain the atomic inventory/credit verbs and quest events.
- Item Lab uses server-held OpenAI credentials for reviewed item copy, ideas, item images and built-in voice auditions. Accepting a proposal edits a draft. Draft/media import into Unity remains an explicit authoring operation; generated voice auditions are not automatically assigned to NPC dialogue.

## Verification

Final full EditMode run: **233/233 passed**, Unity 6000.6.0f1, headless, final source revision `835bf6a0`. See `editmode-release.xml` and `editmode-summary.json`. The Linux development build succeeded; `build-record.json` records source and built-runtime hashes. The saved scene remains unchanged.

Native iteration 5 passed the inventory, capacity, click/search/keyboard, fixed X-ray, augmentation/motor effects, equipment drag, weapon preview/rotation, merchant pointer trading and 1280×720 checks. Its walked city route revealed a double-Tab issue leaving the merchant search field; this is fixed in the final source, and the final native harness now explicitly tests forward Tab, Shift+Tab and text editing. Final run `../inventory/20261002/native-redesign-6/report.json` is queued behind the user's open game and has not yet completed. Do not treat the compiled fix or earlier screenshots as final native verification.

The isolated fixture's short native-5 samples showed similar open/closed inventory frame times. These are scene-specific samples, not a whole-game performance qualification. Failed iterations are retained as diagnostic history.

Developer tooling: 27 backend/security tests, existing browser regression, focused authoring regression and JavaScript syntax checks pass. The one explicitly approved live text test succeeded (2,257 input + 94 output tokens); it did not edit game content. Image and voice transports were exercised with fixtures only. See `../inventory/20261002/developer-ui/verification.json` and screenshots.

## Review and recovery

- Run native UI regression: `uv run --offline --with python-xlib --with pillow python unity/tools/check_inventory_redesign.py OUT --exe unity/AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64 --profile-seconds 6` from this worktree, only with other Unity/player jobs stopped.
- Combined headless authoring export/build entrypoint: `AthenHill.Editor.CraftingDataExporter.BuildDevelopmentWithAuthoringExport`.
- Start Item Lab: `python unity/tools/devui/server.py --qa-dir "$HOME/ward-native-qa" --port 8765`, then open its loopback URL. It discovers the primary checkout's `.env` without copying keys into the worktree, browser or player.
- Reference images are in `references/`. Six equipment icon cells, originals and generation prompts: `art/inventory_icons_20261002/`. X-ray generation record: `implant-art.json`. Rifle prompts, task IDs and source exports: `meshy/field-rifle-20261002/`.
- Save schema is version 3, character schema version 2. Existing version 1/2 saves load; older builds must not rewrite saves containing the new nested module state. Native QA uses its own fixture/save directory.

## Continue verification

The queued native command uses the shared `/home/teknetik/.local/state/ward-programme/unity.lock` and waits for manually launched players to close. It uses an isolated save and stops its own player/scope when finished. Read `native-redesign-6/report.json`, inspect the new equipment art at 1080p/720p, confirm the forward/reverse merchant Tab checks and full city route, then update this verification record. If a check fails, use its focus trace and screenshots before changing source. The Item Lab service is `ashfall-item-lab.service` and stays available at http://localhost:8765.
