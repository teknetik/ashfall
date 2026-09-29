# Basic General counter dressing: Unity integration and Mira trade route (29 Sep 2026)

Task t_7f421ed1 (Ashfall board), child of t_84b69b7e. **Status: integrated and natively verified for the checks below. Not visually accepted, not a GTA6-level claim.**

## Scope and what changed

Only Mira's service recess and counter. The frontage, sign, awning, porch, step, shutter, six gameplay colliders, Mira's root and shop data are untouched.

- New editable prefab `Assets/AthenHill/Art/Phase1/BasicGeneral/Counter20260929/BasicGeneralCounterDressing.prefab` (6 modules, 11 renderers, 22 URP Lit materials, 48 full-resolution texture imports, 62,900 LOD0 triangles / 86,836 including the five LOD1s).
- Scene: one root-level instance **Basic General counter dressing** at (8, 0.5, 15.1), scale 1, identity rotation, **no colliders**. It is a live LODGroup instance and is deliberately **not** a render-chunk source (see amendment below).
- The 90 superseded stock/counter renderers (59,754 triangles) are only **disabled**, not deleted. Their chunk sources were rebuilt (139 chunks) and the scene was saved and reopened from disk.
- Editor-only pass `Editor/BasicGeneralCounterPass.cs` (Prepare / Install / SwitchToLiveLods / Verify). It refuses to overwrite existing assets or an installed instance. `BasicGeneralArchitecturePass` was not re-run.

Fit: uniform scale 1 everywhere (verified after reopening). Conversion is X reflected, winding reversed, tangents regenerated from UV0 and normals. Materials: BaseMap sRGB; Normal map as OpenGL/+Y with default Unity handling; MetalGloss R metallic / A smoothness, scalars 1, so no double-scaling; UV0 carries metric tiling, so material tiling stays (1,1). Textures: mip streaming on, aniso 8, BC7 (HQ), max size set to source size, nothing downsampled. Orientation was checked by eye in native captures: left bay (from the avenue) holds the olla and blue canteen, right bay holds copper hanks and the green spool. It is not mirrored.

LOD: LOD0 to LOD1 at about 5 m (6 m for the counter props), cull about 110 m, no cross-fade. These distances are my tuning from the parent's suggestion and have not been inspected for popping in motion.

### Amendment recorded during the work
The first Install added the dressing to the chunk source roots. Chunk baking merges LOD0 and LOD1 into one mesh and ignores the LODGroup, so both LODs would have rendered. I caught this by inspection, backed the scene up (`rollback/after-first-install-chunked-lods.unity`), removed the dressing from the source roots and rebuilt. `SwitchToLiveLods` records that. Only the scene copy saved at that point exhibited the fault; it never reached a build.

### Not added: practical light
No counter light was added. The brief allowed one only if it truly improved shade readability without a shadow-atlas regression. The dressing reads in the existing light in the captures below, and I did not test a light, so its effect is unknown, not "no help". Left as an option.

## Identity
- Baseline scene SHA-256 `4e07d84f…3a9779` (scene file last saved 27 Sep 20:22), baseline dev build `Builds/LinuxDevelopment` level0 mtime 28 Sep 08:16.
- After scene SHA-256 `2b609992…8b931`; prefab `932bf639…b51`; pass script `2a70c1a8…a429` (`rollback/*-sha256.txt`).
- Working tree on top of `0b4496adf34d0eb01a6f5050cac1b163989ad923`; not a clean-commit build. Nothing was committed.
- After development build: Succeeded, 0 errors, 346 warnings, 91.3 s (`builds/development-build.json`). Release: Succeeded, 0 errors, 348 warnings, 87.1 s (`builds/release-build.json`). The dev build log contains an internal Unity artifact-cache `[Error] Failed to free block` message during the build; the build result is Succeeded and no content error accompanied it.
- Launch: `unity/AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64` (dev), `.../Builds/Linux/AthenHill.x86_64` (release). `Builds/START-HERE.txt` is stale (11 Sep) and was not edited.

## Rollback
`rollback/before-basic-general-counter.unity` is the untouched 28 Sep scene copy (matches the before hash). To revert: restore that scene, and delete `Counter20260929/` and the pass script (or leave them; nothing else references them). Prefab and materials are separate assets, so the old stock renderers can also be re-enabled in place.

## Native evidence (development player, RTX 3060 / i9-10850K, OpenGLCore, driver 610.57.04, quality "PC")
Settings per `settings.json`: 1920x1080 window, renderScale 1.0, MSAA 4, main shadow 4096 at 18 m, VSync off, no frame limit, no frame generation, noon held (day clock paused), HUD on. Diagnostic cameras never qualify traversal.

- Before: `before-native/` (4 fixed + 4 player-height stills, dwell timing, memory). After: `after-native/` (same set, `mira-trade-route.json`, memory).
- Side-by-side sheets: `comparison/*-before-after.jpg`. Fixed views: the retained `cam_audit_basic_general_front/door/side_left/side_right`. Player-height (1.65 m first person, walked to with real keys): `fp_street_centre`, `fp_street_left`, `fp_street_right`, `fp_porch_counter`.
- **Unoccluded 1.6 m view showing Mira and stock**: `fp_street_left` and `fp_street_right`. From those oblique positions Mira does not stand in front of either bay or the counter face. From dead centre (`fp_street_centre`, `fp_porch_counter`) she hides the **middle bay wall and part of the counter face**, which is by design (the middle is the open zone); both shelf bays, hook rails, counter props and counter ends stay visible either side of her.

### Interaction route (real X11 keys), `after-native/mira-trade-route.json`
Reset at West Gate, walked on foot through the hill stairs to the porch: no blocked step or stall on any waypoint (the route is the retained salvage route). At the porch (8.0, 0.53, 16.92; 1.12 m from Mira's root at 15.8): E opened dialogue; W was ignored while modal (position unchanged to 0.04 m); choice 0 opened the shop; buy: 25 to 21 credits and flask 0 to 1 (the game reports 4 credits for the flask); sell: 21 to 22 credits and scrap 1 to 0 (sells for 1 credit); Escape returned to Play; walked away to (8.0, 0.03, 19.4) and on to the lane. Deltas: -4 / +1 credits, +1 flask, -1 scrap, atomic (both changes appeared together in each snapshot). The starting state was the fresh-run 25 credits, 1 scrap coil. I did not re-run the full city loop or the 41-waypoint traversal in this pass.

### Localised cost, matched dwell (6 s each, uncapped, `localised-cost-comparison.json`)
Host load average was 1.7 to 3.3 during runs, so this is a local comparison, not qualification.

| View | Before avg FPS / p99 ms | After avg FPS / p99 ms | Before / after SetPass |
| --- | --- | --- | --- |
| front | 68.1 / 15.32 | 68.0 / 16.26 | 238 / 214 |
| door | 82.7 / 13.00 | 82.6 / 13.23 | 249 / 231 |
| side left | 82.3 / 13.47 | 82.5 / 13.28 | 200 / 191 |
| side right | 60.0 / 17.48 | 60.0 / 18.58 | 328 / 301 |
| player centre | 95.5 / 11.19 | 89.7 / 12.51 | 196 / 186 |
| player left | 94.8 / 11.38 | 93.1 / 11.99 | 198 / 190 |
| player right | 75.8 / 13.86 | 73.4 / 14.82 | 274 / 256 |
| porch counter | 95.7 / 11.75 | 96.5 / 11.60 | 200 / 186 |

- Fixed distant views are unchanged within noise; SetPass falls about 4 to 10 per cent, as the 90 retired renderers' material families are gone. Player-height views nearest the dressing cost about 0.4 to 1.3 ms p99 more and up to 6 per cent lower average FPS (centre 95.5 to 89.7). That is a real small cost at the focal view and stays well inside 60 FPS here, but I have not shown it is caused by the dressing alone rather than noise.
- The 60 FPS / 18 ms side-right view is a pre-existing scene cost (same before). p99 16.67 ms is not met on it before or after; that is outside this task.
- Counters not available: GPU frame time (null), draw-call count (null); triangle numbers are submitted across passes, not visible geometry.
- Texture memory (Unity counters, same session pattern): current +14.5 MiB, desired +70.7 MiB, theoretical full-resolution +247.0 MiB, Unity-allocated -5.9 MiB. Streaming mipmaps are active (budget 4096 MiB). Driver VRAM residency was not measured. The parent's estimate of about 253 MiB BC7 is therefore an upper bound for full residency; the measured resident increase is much smaller, but only in these views.

### Player logs
Before log: one development-bridge `Unobstructed companion captures require an actual active dialogue` exception, caused by my first attempt to hide the HUD (removed from the script afterwards). After log: no exception lines at all. Neither log has shader errors, missing-material or NullReference lines.

### Release smoke (`release-native/report.json`)
Release player launched with `--athen-qa`; the probe folder stayed **empty** (bridge absent, no command listener), window 1920x1080, screenshot non-blank and showing the game, no exception or shader-error lines, player still running after real keys. (A first attempt failed only because grim lacked the Wayland environment; it is kept as `release-native-attempt1-failed-grim-env`.) This is a bounded smoke, not a release route or trade run.

### EditMode
70 of 70 passed (`editmode-results.xml`; suite run against the post-integration tree). No test targets this dressing; the saved-scene check is `counter-verify-saved-scene.json`: reopened from disk, prefab linked, uniform scale, no dressing colliders, 90 retired renderers disabled, all six frozen colliders unchanged (525 colliders in scene), chunk fingerprint matches, Mira root at (8, 0.5, 15.8).

## Visual review (my scoring, not acceptance)
Composition/silhouette 3.5; scale 4 (counter 0.94 m against the 1.8 m actor reads right); material detail 3.5 (steel, brass, enamel, twine, paper distinguishable; counter face still muted); lighting/depth 3 (recess is warm-dark, the dressing reads but the lower counter face is low-contrast); density/storytelling 3.5; characters/animation not in scope (Ward Guard unchanged, static idle); temporal stability not assessed beyond stills; UI unchanged. Below the 4 target for shade and material contrast, so **not accepted**.

## Unresolved defects and risks
1. Middle bay and counter face are hidden behind Mira from the centre view; the rear wall behind her is a plain flat panel.
2. Lower counter face is low contrast in shade; only a possible practical light (untested) or a brighter face tint would change that.
3. Small localised frame cost at close range; texture desired-memory rises 70.7 MiB. Consider sharing enamel tint tiles and trimming the 4k counter maps.
4. LOD switch distances not judged for popping in motion; nothing recorded on a moving walkthrough video.
5. Non-manifold, overlapping small props were not inspected in wireframe (parent noted the same).
6. Working tree only: RenderChunk asset files were regenerated by the rebuilds (many show as deleted/added in git), so a review needs the scene, not a line diff. The tracked `Builds/` folders now hold the new dev and release builds.
7. Slow-path items not run: full city loop, the 41-waypoint traversal, WAV-level audio, and the developer time-of-day range beyond noon.
