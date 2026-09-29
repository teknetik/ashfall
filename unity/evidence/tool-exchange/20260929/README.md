# Tool Exchange display and shutter fittings: Unity integration (29 Sep 2026)

Task t_3513ba55 (Ashfall board), child of t_3751e0fd. **Status: integrated and natively verified for the checks below. Not visually accepted, not a GTA6-level claim.**

## Scope and what changed

Only the street-facing recessed display and the rolling-shutter surround of the accepted revision 04 Tool Exchange. Shell, door, sign, clerestory, awning, porch, steps, 15 colliders, Vex and all routes are untouched.

- New editable prefab `Assets/AthenHill/Art/Phase1/ToolExchange/Display20260929/ToolExchangeDisplay.prefab` (12 renderers, 16 URP Lit materials, 46 full-resolution BC7 textures, 17,926 triangles, no LODs, no colliders).
- Scene: one root-level instance **Tool Exchange display and shutter** at the building pose (-20.6, 0.5, 9.0), yaw 90, scale 1. It is a live set of renderers, deliberately **not** a render-chunk source (chunking would merge the transparent glazing into opaque batches).
- **Seven revision 04 renderers were disabled, not deleted**: dark recess, glass 0/1 (the two opaque near-black panes, 1,036 triangles in all), two shutter guide rails, two lift handles. Mullions, sills, reveals, all 20 slats, drum casing, ground rail and backing stay.
- Editor-only pass `Editor/ToolExchangeDisplayPass.cs` (Prepare / Install / Verify). It refuses to overwrite existing assets, an installed instance, or a building not at the expected pose. Installed via batch; Show Sources then Rebuild Render Chunks ran inside Install (6,872 renderers into 139 chunks); scene saved and reopened by Verify.

Fit: uniform scale 1 on every part (lossy scale 1.0 after reopening). A-space X is reflected, winding reversed, tangents regenerated from UV0 and normals. Part pivots come from the handoff `pivotUnityLocalToBuilding`. Materials: BaseMap sRGB; normal map OpenGL (+Y), no green flip; MetalGloss R metallic / A smoothness with both scalars 1; material tiling stays (1,1) because UV0 carries the metric layout. Glazing is `TE_Glass`: Lit transparent, alpha blend, ZWrite off, queue 3000, no receive-shadows, shadow/depth passes off, no shadow casting on the renderer. Nothing emissive; no light was added.

Orientation checked by eye in native captures: wrench (red) in the left pane from the avenue, bolt cutters right, padlock under the lock box in the middle of the shutter. Not mirrored.

## Identity

- Baseline scene SHA-256 `2b609992…8b931` (the state left by the Basic General pass), baseline dev build `Builds/LinuxDevelopment` level0 07:51, 29 Sep (it postdates the saved scene, so it is the current build). Working tree over `0b4496ad`, uncommitted.
- After scene SHA-256 `34d448cb…aaa27`; prefab `40da89d7…0c9`; pass script `719ef630…191e` (`rollback/after-sha256.txt`).
- Development build: Succeeded, 0 errors, 346 warnings, 156 s (`builds/development-build.json`). Release: Succeeded, 0 errors, 346 warnings, 106 s (`builds/release-build.json`). Launch `unity/AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64` (dev) and `.../Builds/Linux/AthenHill.x86_64` (release).
- `Builds/START-HERE.txt` is stale and was not edited.

## Rollback

`rollback/before-tool-exchange-display.unity` is the untouched baseline scene (matches `baseline-scene-sha256.txt`); `rollback/before-tool-exchange-display-saved-by-install.unity` is Install's own copy. To revert: restore that scene (keep or delete `Display20260929/` and the pass script; nothing else references them). In place: re-enable the seven listed renderers, disable the instance, rebuild render chunks.

## Native evidence

Development player, RTX 3060 / i9-10850K, OpenGLCore, quality "PC", from `settings.json`: 1920x1080 floating window, renderScale 1.0, MSAA 4, main shadow 4096 at 18 m, one cascade, VSync off, no frame limit, no frame generation, day clock paused at the authored 17:00 (dusk light), HUD on, actor count 12. Diagnostic cameras never qualify traversal.

- Before: `before-native/` (four fixed views, six player-height views, memory). `before-native-fixed-dwell/` is a second launch of the same build with fixed-view dwell timing.
- After: `after-native/` (same set, traversal video, noon `-h12` and dusk `-h20.5` player-height sets).
- Side-by-side sheets: `comparison/*-before-after.jpg`. Player-height views are real first person (1.65 m eye), reached on foot from the west gate along the retained salvage route (`approachRoute` in the capture JSON), every waypoint reached without a stall. `fp_display_close` is at 1.6 m from the display glass.

### Traversal and Vex (real X11 keys), `after-native/after-traversal.json` and `.mp4`
Reset at the west gate: Vex's prompt "E · Talk to Vex" was live, E opened his dialogue, movement was blocked while modal (0.0 m), Escape returned to Play. Then on foot along the salvage route to the avenue lane, and a 16 s 1920x1080 recording of the moving approach: lane to display, onto the porch, along the porch past the shutter to its north end, off the porch into the neighbouring lane, back past the frontage and south of it. All seven legs reached their targets in 1 to 2 s with no blocked step. Vex stands at the west gate (41.7, 0, -1.5), not at Tool Exchange, so this shows his root and interaction are unchanged, not that he is near the shop. The porch and avenue collision was not touched (`display-verify-saved-scene.json`: 15 frontage colliders identical before and after, 724 colliders in scene).

### Logs and checks
- Player logs: no exception, shader error, missing material or NullReference in the before or after dev log. The one atlas warning ("Reduced additional punctual light shadows resolution by 2 to make 12 shadow maps fit") appears in the baseline log too, so it is not new.
- Saved-scene reopen: `display-verify-saved-scene.json`, prefab linked, 12 renderers, uniform scale, no dressing colliders, 7 retired renderers all disabled, chunk fingerprint matches, chunk sources hidden.
- EditMode: 70 of 70 passed (`editmode-results.xml`). No test targets this dressing; the scene check above is the closest.
- Release smoke (`release-native/report.json`): launched with `--athen-qa`, probe folder stayed **empty** (bridge absent), 1920x1080 window, non-blank render, no exception lines, still running after real keys. Bounded smoke, not a release route or perf run.

### Localised cost (6 s dwells, uncapped, `localised-cost-comparison.json`)
Host load average was 4 to 10 during runs (another process was rendering video), so this is a local comparison, not qualification. GPU frame time and draw-call counters are unavailable in this player.

| Player-height view | Before fps / p99 ms | After fps / p99 ms | Before / after SetPass |
| --- | --- | --- | --- |
| front lane | 55.8 / 26.7 | 121.2 / 9.9 | 316 / 318 |
| porch door | 62.6 / 25.0 | 119.3 / 10.0 | 331 / 335 |
| display close | 112.5 / 10.8 | 110.8 / 12.7 | 326 / 338 |
| shutter close | 145.5 / 8.9 | 146.2 / 8.6 | 303 / 310 |
| side left | 141.0 / 8.9 | 142.6 / 8.7 | 307 / 308 |
| side right | 86.0 / 13.0 | 85.2 / 13.8 | 283 / 295 |

- The first two rows do **not** show a speed-up. The before pass ran on a freshly launched player under heavier host load; the after numbers are about 2x faster with the same SetPass count, which is a cold-start or load artefact I have not isolated. Do not read it as a gain.
- Views where the runs are comparable (display close, shutter close, sides): change is within noise except display close, where p99 rose about 1.9 ms (first after run 11.2 ms, second 12.7 ms, against 10.8 before) and SetPass rose 12 (326 to 338). That fits the 12 extra live renderers and 16 materials on the focal view. Side right in the first after run had one 30.6 ms p99, gone in the second run (13.8 ms); treat it as host noise.
- **Fixed diagnostic-view dwell was not re-measured after** (the after fixed pass was run without dwell), so no fixed-view before/after cost exists. The before fixed numbers are in `before-native-fixed-dwell/` and were taken at load 8 to 9.
- Texture memory (Unity counters, `memory.json`): current +29.1 MiB, desired +29.1 MiB, theoretical full-resolution +465.4 MiB, Unity allocated +4.1 MiB. Streaming mipmaps are active. Driver VRAM residency was not measured. The parent's ~276 MiB BC7 estimate is an upper bound for full residency.

## Visual review (my scoring, not acceptance)
Dusk (authored 17:00) unless noted.
- The display: the two black panes are gone. From 1.6 m the pegboard, red pipe wrench, hammer, bolt cutters, G-clamp, whetstone and the handsaw outline are legible through a dusty film that is clear enough to read the tools and not a sign. From the avenue lane (5 m) it reads as a lit pegboard with a red wrench. Noon is legible but flatter and browner.
- The shutter: two brass D-handle plates, lock box with keyhole, closed padlock, kick plate and guide channels read as mechanically plausible hardware, not glowing, and not too busy at player height. The kick plate is the busiest element; per the parent's note it can be dropped.
- Scores: composition/silhouette 3.5, scale 4, material detail 3.5 to 4 at 1.6 m, lighting/depth 3 (shade in the recess is muddy; no local light), density/storytelling 3.5 to 4, temporal stability not assessed beyond one recorded approach, UI unchanged. Below the 4 target on lighting, so **not accepted**.

## Unresolved defects and risks
1. **Night**: at 20:30 the display is near-black and only faintly readable. The lamp is geometry only; no practical light was tested, so its effect is unknown. This is the largest gap.
2. The glass film plus the enclosed alcove lowers contrast at dusk and noon; the board reads muddy at 5 m.
3. Small close-range cost at the display (about +2 ms p99, +12 SetPass) and +29 MiB texture memory. Small-prop families use 2k tiles for centimetre-scale objects; sharing or 1k for twine, paper, sand, stone and rubber is untested.
4. Fixed-view after-cost, GPU time, driver VRAM, LOD (none authored) and long-run hitching are unmeasured. The before/after cost for the first two rows is confounded (see above).
5. Small-part overlaps (wrench eyelet on peg, tags on twine) were not checked in wireframe or a physics test.
6. Working tree only: RenderChunk asset files were regenerated by the rebuild (many appear deleted/added in git), so review the scene, not a line diff. The tracked `Builds/` folders now hold the new dev and release builds.
7. Not run: full city loop, the 41-waypoint traversal, WAV-level audio, night walkthrough video, Vex from a Tool Exchange position (he is not there).

## Tools added under unity/tools
`capture_tool_exchange_display.py`, `check_tool_exchange_traversal.py`, `compare_tool_exchange_stills.py`, `compare_tool_exchange_cost.py`, `float_player_window.sh` (floats and sizes the player under Hyprland; a tiled window stalled the render loop and broke the 1920x1080 capture).
