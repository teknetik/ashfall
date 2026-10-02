# Inventory integrated with the finished Berms build — 2 October 2026

The inventory/loadout/merchant redesign and Item Lab are merged into `ward/next-level` in the normal checkout, `/home/teknetik/code/ao2`. Merge commit `2259e9b9` combines the inventory branch with recovery checkpoint `e4f88037`; `83b4a810` brings its final isolated verification, and `0c372233` records the combined authoring export and native equipment test adaptations. The whole `codex/ashfall-inventory` branch is an ancestor of this checkout.

The normal Linux development player was rebuilt successfully at `unity/AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64`. See [build identity and hashes](build-record.json). Unity 6000.6.0f1, native Linux, OpenGL Core. The Item Lab runs from this checkout at http://localhost:8765; its existing drafts and generation history were copied intact from the isolated worktree, and credentials remain server-side in the existing root `.env`.

## Integration decisions

- Preserved Claude's saved scene, prefabs/world art, expanded Berms, rifle combat/poses, visible carrier, recipes, seven field orders and save migration. [Preservation audit](preservation.json) verifies 313 protected paths unchanged from the pre-merge recovery checkpoint.
- Kept the rifle earned through Long Arm, its starting quantity zero, and the receiver/carrier quest-only. The combined catalogue has 52 items, 16 equipment entries and 12 modification types.
- Added outer plate, inner plate and liner sockets to the Warden plate carrier while preserving its reward identity, weight and base protection. The authoring script now retains these settings on repeated runs.
- Used the large rifle illustration in inventory and kept Claude's cropped rifle icon for the combat hotbar.
- Saved module state remains schema 3 / character schema 2. The combined save test covers an earned rifle plus carrier with plate/liner, preserving stat bonuses, mass, inventory and order progress.

## Verification of this combined build

- **Unity EditMode: 239/239 passed**, including both integration regressions. [Summary](editmode-summary.json), [full results](editmode.xml).
- **Inventory native: 40/40 passed**, including compact slots/capacity, click/keyboard details, X-ray/no 3D camera, three implant sockets, augmentation/motor effects, equipment dragging, two weapon previews, merchant search/keyboard/wheel/atomic trades, 1080p/720p and the walked city loop. [Report](native-inventory/report.json).
- **Rifle and carrier quest: 34/34 passed**, including new-game primer, receiver report, fabrication, real drag equip, draw/holster/switch/burst, caravan strongbox, visible carrier and save persistence. [Report](rifle/report.json).
- **Range tutorial: 10/10 passed**, including Wardens, locker, range plates and city regression. [Report](range/report.json).
- **Outer Berms expansion: 8/8 passed**, including waystation discovery/respawn, caravan activation and ranged drone encounters. [Report](berms/report.json).
- **Developer UI: 27 backend/security tests passed**; browser checks against the actual combined export passed. No paid OpenAI request was made during integration. [Actual export browser result](../inventory-redesign-20261002/authoring-export/results.json).
- Reviewed all ten combined UI captures: no new clipping, missing icons or atlas bleed. Selected images are in [review](review/); [visual review notes](visual-review.json).

The first EditMode attempt exceeded its 12 GB + 512 MB swap cap before producing results. The retry passed using the established 17 GB + 3 GB profile; the build used the same cap. Jobs ran sequentially under the shared Unity lock. The range test finished successfully; its enclosing batch then exited while waiting for the deliberately terminated memory sampler, so the remaining expansion test was launched separately. No failed gameplay assertion was bypassed.

Short six-second samples from the loaded inventory fixture were 30 FPS closed (p50 33.22 ms, p95 36.67 ms) and 32 FPS open (p50 31.21 ms, p95 33.97 ms). These are a single QA view, not a before/after world comparison or a whole-game 60 FPS qualification. The snapshot dimensions were 1920×1080; the report's environment block was captured before the initial window resize and has stale dimensions.

Known presentation limits remain: the narrow 3D rifle view is small/dark; separate visible plate/motor component meshes are not authored. Claude's existing rifle first-person view-model limitation remains. The merge does not change the saved world or these source assets. All gameplay checks used isolated saves, and their players were stopped afterward.
