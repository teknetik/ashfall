# West Gate checkpoint pass — 26 September 2026

The disc with pillow feet was the original range target. User feedback accepted the existing worker droid, mining droid and yellow hover drone; all three remain. The replacement is a Meshy steel silhouette target on an authored hinged, braced stand.

## Delivered scene and build

Two named, visibly armed Wardens (Ossa and Rell), an open guard booth, a cyan-lit labelled arms locker, four defensive barriers, ten drought shrubs, local grass, an inspectable briefing board, three numbered knockdown plates and a range reset control. Guard conversations do not count toward the original four-colonist objective. Original city dialogue/trade/travel data and combat tutorial progression are retained. Secured guard pistols are visual equipment, not new combat AI.

Both final Linux builds succeeded with zero errors. The ordinary release was reopened for the user afterward; `release-smoke.json` records the running process and clean startup log. See `development-build.json` and `release-build.json` for timings, sizes and warning counts. Existing broader-project physics/import warnings remain; the reports preserve them. The scene was explicitly saved and reopened after the range and sign passes. `identity.json` records the final scene and executable hashes against this dirty working tree. Unrelated prior district, menu and combat changes were preserved.

## Verification and limits

`edit-mode-tests.json`: 56/56 existing/scoped Edit Mode checks passed, followed by a strengthened saved-scene checkpoint test (1/1) checking the persisted range reset, plate decals and connections.

`native-clean/report.json`: all ten checks passed with real keyboard/wheel input: gate walking, both named guard dialogues, briefing board, first person, one-time pistol pickup and guidance transition, range reset response, all three new plates falling and tutorial advancing, automatic holstering on return to Ward, and the complete existing city regression. The city test covers all four original colonist dialogues, modal movement blocking, atomic flask purchase/scrap sale, both Lattice selections, pause, pack/notes, mute/reduced motion, credits and reset. There were no runtime exceptions in the tested route. Day/night, player-height locker/target close-ups, original service-road drone and matching named-camera captures are under `native-clean/`. Moving walkthrough video of this same build is in `native-verified-final/walkthrough.mp4`.

`performance-review.json`: the clean 20.25-second warmed checkpoint route passes the local frame target: 242.8 FPS average, p99 14.77 ms at 1920×1080, 100% scale, uncapped, RTX 3060 / i9-10850K, OpenGL. All 12 active scene actors, HUD, shadows and effects were enabled; authoring apps were closed and recording stopped. Full settings/hardware, allocator and texture counters, raw frames and limitations are retained. This is a focused checkpoint measurement, not a full-district production qualification. GPU timing and zero-valued draw/batch counters are unavailable, not zero cost. Loading was not timed separately.

The previous slow runs and intermittent UI test failures are retained. A second ordinary game was observed sharing GPU and desktop input. After the user closed it, the clean performance and complete city loop passed. `performance-concurrent-review.json` records the earlier failing sample; it has not been removed or retroactively accepted. The Lattice test now waits for actual readiness instead of assuming a fixed delay.

`visual-review.json` records local scores and remaining defects. The guards’ existing bright armour/stiff source animation and the broader repetitive berm/soil surfaces remain. This pass improves entry readability and activity; it is not whole-game GTA6/AAA acceptance.

## Before/after and recovery

`before/` retains the old native gate/post captures at 1896×1040 (compositor-tiled window). New `gate-matched` and `post-matched` captures use the same named cameras at 1920×1080; resolution differs, so these are not pixel-identical comparisons. `scene-before-checkpoint.unity` retains the authored scene before this pass. Original target visual remains inactive inside the target prefab for recovery.

`art/checkpoint_20260926/` retains accepted/rejected user reference images, Blender source, source-scale audits and authoring scripts. `meshy/checkpoint-robots-20260926/` retains all task IDs/options/usage and full source geometry/PBR textures, including unused robot candidates generated before the target was identified. Only the new target is installed. Earlier failed/timing/concurrent runs remain intact; final checks are not retroactively attributed to them.
