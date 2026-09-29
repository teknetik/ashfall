# Tool Exchange: practical light for the display (29 Sep 2026)

Task t_e14abefb (Ashfall board), follow-up to t_3513ba55. **Status: integrated and natively verified for the checks below. Not visually accepted, not a GTA6-level claim.**

## What changed (one object, no assets)

One new scene object, **Tool Exchange display practical light**, parented under the existing `Tool Exchange display and shutter` instance. Spot light, world (-18.27, 2.50, 7.22) (at the swan-neck lamp head, `TE_DisplayLamp` centre (-18.36, 2.60, 7.22)), aimed at (-18.53, 1.75, 6.85) (pegboard, wrench-to-cutters). Warm (1.0, 0.78, 0.52), intensity 2.5, range 2.4 m, spot 120 / inner 60, **shadows None** (no point/spot-shadow atlas use), realtime. Bound into the existing `CityLightCircuit` (`practicalLights` 62 to 63) and listed in `nightOnlyLights` (11 to 12), so the clock drives it like the other fixtures: full at night, ramping through dusk, off in daylight (circuit strength below 0.2). Nothing else changed: display prefab, materials, glazing, shutter, colliders, Vex, RenderChunks untouched; the chunk fingerprint is identical, so chunks were not rebuilt (the light is not a chunk source).

Parameters are in `light-params.json` (kept as `light-params-v1.json`; the first pair I tried was the final one, no tuning loop). Editor-only pass: `Editor/ToolExchangeLightPass.cs` (Inspect / Apply / Verify; Apply is idempotent by object name and refuses a dirty scene).

Rollback: restore `rollback/before-light.unity` (sha `85ab02ce...c8ae`), or delete the object and remove it from both circuit arrays. Baseline dev build copy: `/home/teknetik/code/_snapshots_20260929/tefirst-baseline-LinuxDevelopment`.

## Identity
Scene sha `85ab02ce...` to `b7367172...7ae7` (diff is the light object, its PrefabInstance added-object entry, a stripped parent transform and the two circuit array entries). Working tree over HEAD 643b7dcc; nothing committed. Dev build Succeeded 0 errors 346 warnings (105 s); release Succeeded 0 errors 346 warnings (107 s). Launch `unity/AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64` / `Builds/Linux/AthenHill.x86_64`.

## Native evidence
Development player, RTX 3060 / i9-10850K, OpenGLCore, 1920x1080 floating window, render scale 1.0, paused clock at 17:00 (dusk), 20:30 (night), 12:00 (daylight control), HUD on. Three real-input player-height views (1.65 m eye, same salvage route from the west gate): `fp_front_lane` (5 m, avenue lane), `fp_door_porch`, `fp_display_close` (1.6 m). Before: `before-native/` (baseline build, `tefirst-baseline-LinuxDevelopment`). After: `v1-native/`. Repeat of the baseline: `before-repeat-native/`. Sheets (before left, after right, x1 and x4 gain): `comparison-v1/`.

Mean luma of the display crop (0-255), before to after:

| View | 12:00 | 17:00 | 20:30 |
| --- | --- | --- | --- |
| display close | 48.3 to 48.3 | 55.2 to 72.7 | 6.2 to 56.6 |
| front lane, 5 m | 46.3 to 45.9 | 64.3 to 72.5 | 5.0 to 31.8 |
| door porch | 36.2 to 36.2 | 56.2 to 56.2 | 4.2 to 4.2 |

Daylight is unchanged (as designed). Door porch is unchanged at every hour: the camera looks past the display along the frontage, so the alcove is not in the crop; it was kept as a spill/blowout check and shows none.

Seen by eye: at night from 1.6 m the pegboard, red wrench, saw outline, hammer, bolt cutters, G-clamp, whetstone and file all read, with a warm pool centred on the upper right and a soft falloff; from 5 m it reads as a lit shop window with the red wrench and hammer distinguishable. At dusk the muddy right-hand half of the board is lifted and gets a warm hotspot around the hammer; the effect is subtle, not glowing. The glazing stays clear and does not bloom.

## Real input and logs
`trav-native/traversal.json`: Vex prompt live and E dialogue, movement blocked while modal, Escape back to Play, salvage route on foot, all seven avenue/porch legs reached (lane to display, onto the porch, past the shutter, north end, off the porch, back past the frontage, south lane), no stall. Player logs (before, v1, traversal): no exception, NullReference or shader error; one "Reduced additional punctual light shadows resolution" line in each, **including the baseline**, so it is not new. Release smoke (`release-native/report.json`): bridge absent (probe folder empty), 1920x1080, non-blank, no exception lines, still running.

Saved-scene reopen (`verify-saved-scene.json`): light present, Spot, shadows None, parented to the display, bound to the circuit and night-only, display still 12 renderers and 0 colliders, chunk fingerprint matches and sources hidden, Vex root (41.7, 0, -1.5) unchanged, 725 colliders by this count (the Tool Exchange pass recorded 724, the earlier Basic General pass 525/526 with other counting; the light adds none). 8 enabled non-directional lights in the scene cast shadows, none of them this one.

## Local frame cost (6 s uncapped dwells per view and hour, `localised-cost-before-vs-v1.json`)
Host load average 1.1 to 4.5 during the runs, so local only; GPU time and draw counters unavailable in this player. Before vs after p50 and p99 differ by no more than 0.15 ms and 0.3 ms in any view (e.g. display close 20:30: p50 8.89 to 8.96, p99 10.28 to 10.44, fps 110.8 to 109.9); SetPass differs by under 1.1 on average. A repeat of the baseline against itself (`localised-cost-before-vs-repeat.json`) moves by similar amounts, so the change sits inside run-to-run noise. Not measured: the light's cost at other locations in the district, since the circuit culls it beyond 42 m and its 2.4 m range touches little geometry. Texture and VRAM cost: none (no assets).

## Visual review (my scoring, not acceptance)
- Lighting/depth at the display: **3 to 4** (was 3 at dusk, about 1 at night). The night close view reaches 4 for legibility; the dusk 5 m view is a modest lift.
- Composition, scale, material detail: unchanged from t_3513ba55 (3.5, 4, 3.5 to 4).
- The light is a single warm pool, so the left pane (wrench, saw) is dimmer than the right; dusk 5 m view still shows the left half in shade.

## Unresolved issues
1. Light distribution is lopsided at dusk: hotspot on the hammer, wrench and saw side dimmer. A second, wider fill or a shifted aim would even it; I did not iterate to keep the change small.
2. At night the case is much brighter than its surroundings (5 m view: a lit window on a black frontage). Reads plausible for a shop, but it is the only visibly lit part of the frontage, and the shutter and door remain near-black. No shutter/door light was added (out of scope).
3. No hero-view score reaches 4 across all categories; temporal stability not assessed (stills plus one traversal run without video).
4. Light has no flicker, cookie or emissive lamp-head; the `TE_DisplayLamp` material is still not emissive, so the housing is not lit at night. Not tested.
5. Noon `-h12` and porch views were checked by numbers and eye only; no video walkthrough.
6. Full city loop and the 41-waypoint traversal not re-run.
7. Working tree only, nothing committed. Builds tracked under `Builds/` now include the new dev and release players. Scene overlaps: the scene still carries uncommitted Basic General, Air + Water and Tool Exchange edits; the crafting/dev-UI worktrees are already merged (t_c7c1e1ca) and were not touched.

## Tools added (unity/tools, Editor)
`Editor/ToolExchangeLightPass.cs`, `capture_tool_exchange_light.py`, `compare_tool_exchange_light_stills.py`, `compare_tool_exchange_light_cost.py`, `run_tool_exchange_light_capture.sh`, `run_tool_exchange_light_traversal.sh`, `summarise_tool_exchange_inspect.py`. Reused: `launch_phase1_qa.py`, `float_player_window.sh`, `capture_tool_exchange_display.py`, `check_tool_exchange_traversal.py`, `check_release_counter_smoke.py`.

## Correction recorded
The first "v1" capture reused a shell environment variable that still pointed at the baseline build, so it was a second baseline run, not an after run. It is kept as `before-repeat-native/` and used as a repeatability check; the real after run is `v1-native/` (launch command confirmed in `v1-launch.out`).
