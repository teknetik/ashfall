# Air + Water three-filter bank: Unity integration (29 Sep 2026)

Task t_3041b425 (Ashfall board), child of t_bd3d9fe3 (asset package) and t_c7c1e1ca (reconciliation). **Status: integrated and natively verified for the checks below. Not visually accepted; no water simulation; no AAA or GTA6-level claim.**

## Scope and what changed

Only the exterior three-filter bank right of the Air + Water front door: mounts, header, valve, gauge, labels and roof riser. The canisters, retainer collars, riser clamps/stand-offs/anchors, feed flanges, facade, door, awning, sign, tanks, 6 building colliders, 9 Sep material/decals and every gameplay root are untouched.

- New editable prefab `Assets/AthenHill/Art/Phase1/AirWater/Filters20260929/AirWaterFilters.prefab`: 5 renderers (AW_FilterMount_1/2/3, AW_FilterHeader, AW_FeedRiser), 8 URP Lit materials, 24 full-resolution BC7 textures (2048 tiling, AW_Labels 4096x512, AW_Dial 1024), 36,152 triangles, no LODs, no colliders.
- Scene: one instance **Air + Water filter fittings** under `Ward shop architecture` (a render-chunk source root), at the building pose (-20.6, 0.5, **-9.0**), yaw 90, uniform scale 1. It is a chunk source, so Rebuild Render Chunks bakes it with the other opaque architecture. Show Sources reveals it as five editable children.
- **Eight superseded 9 Sep renderers were disabled, not deleted** (692 triangles): Filter manifold, manifold inlet 0.9/1.7/2.5, wall mount 0.9/1.7/2.5, Roof to filter downfeed. Retired by exact name: prefix matching would also have caught inlets that share the "Filter manifold" prefix.
- Editor-only `Editor/AirWaterFilterPass.cs` (Prepare / Install / Verify). It refuses to overwrite assets or an installed instance, and refuses if the building is not at the expected pose. Installed in batch: Show Sources, retire, instantiate, Rebuild Render Chunks (6,877 renderers into 146 chunks, +5 sources over the Tool Exchange state), save; Verify reopens the scene from disk.
- Fit: A-space X reflected, winding reversed, tangents regenerated from UV0 and normals, pivots from the handoff `pivotUnityLocalToBuilding`. Materials: BaseMap sRGB; normal map OpenGL (+Y, no green flip); MetalGloss R metallic / A smoothness with both scalars 1; material tiling (1,1) because UV0 carries the metric layout. No emissive, no light, no post/URP/pipeline change.
- **Handoff discrepancy:** `handoff.json` states the building pivot as z **+9.0** (the Tool Exchange's value). The saved Air + Water instance is at z **-9.0** with the same yaw. Local-space pivots apply either way, and the installer checks the real pose. Reopened bounds in building-local space match the handoff (x 0.552, z 3.23 front line).

## Identity

- Baseline scene SHA-256 `79e2cf11…c3081`, baseline dev build `level0` `8cfd2e44…bb544` (19:12, 29 Sep; a copy is kept at `/home/teknetik/code/_snapshots_20260929/airwater-baseline-LinuxDevelopment`), release baseline `3e77f06a…dd92`. Git HEAD `643b7dcc` plus uncommitted work; nothing committed by this task.
- After scene SHA-256 `06123dca…1b` (`06123dcabd295593dcd2d1bdbedb6c41318a75d4329ced1330810f2fd7b2781b`), chunk fingerprint matches after reopening, 725 colliders (unchanged), 12 actor-animation components.
- Development build: Succeeded, 0 errors, 346 warnings (same count as the Tool Exchange build), 89 s (`builds/development-build.json`). Release: Succeeded, 0 errors, 346 warnings, 111 s (`builds/release-build.json`). Launch `unity/AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64` (dev) and `.../Builds/Linux/AthenHill.x86_64` (release). `Builds/START-HERE.txt` is stale and was not edited.

## Rollback

`rollback/before-airwater-filters.unity` is the untouched baseline scene (hash in `baseline-scene-sha256.txt`); `rollback/before-airwater-filters-saved-by-install.unity` is Install's own copy; `rollback/RenderChunks-before/` is the full baseline chunk asset folder (476 MB). To revert: restore the scene and chunk folder (keep or delete `Art/Phase1/AirWater/` and the pass script; nothing else references them). In place: re-enable the eight listed renderers, disable/delete the instance, Rebuild Render Chunks.

## Native evidence

Development player, RTX 3060 / i9-10850K, driver 610.57.04, OpenGLCore, quality "PC" preset 2, render scale 1.0, MSAA 4, shadows 3, VSync off, no frame limit, no frame generation, HUD on, 12 actor components. Windowed and floated (`float_player_window.sh`); every capture asserts a 1920x1080 frame and Play state. (The recorded `settings.json` `video` block reads 1890x2080 because it was snapshotted before the resize; the per-capture assertions are the authority.) Day clock paused at 08:00, 12:00 and 16:00. Diagnostic cameras never qualify traversal.

- Before: `before-native/` (baseline dev build launched from the same commit, four fixed audit cameras and eight player-height first-person views, each at 08/12/16). After: `after-native/`, same set on the new build.
- Side-by-side sheets: `comparison/*-h08|h12|h16-before-after.jpg` (36 sheets, before left, after right).
- Player-height views are real first person (1.65 m eye), reached on foot from the west gate via the 9 Sep validated route (west lane, north lanes, Air + Water lane), every waypoint reached without a stall (`approachRoute` in the capture JSON). Stand positions and yaw are recorded. The two runs land within 0.06 m and 3 degrees of each other (see the fp_label caveat below).

### Traversal and clearance (real X11 keys), `after-native/airwater-captures-traverse.json`, `after-native/after-traversal.mp4` (16.0 s, 1920x1080)

Nine legs on foot, all reached, no blocked step (0.5 to 1.9 s each): lane to bank, onto the porch at vessel 2, porch to valve end, back past the vessels, in front of the door, tight to the wall at the door, tight beside the bank, off the porch, south along the lane. The walked porch positions (x -16.94 to -17.05 against the fittings' front line at x -17.37, and the door at z -9.15..-9.29) confirm the entrance and porch remain open. The porch walk zone starts 70 mm beyond the fittings, and the nearest new geometry is 0.70 m from the door reveal (parent measurement, reconfirmed from the reopened bounds).

`after-native/wall-contact.json` holds W against the wall between vessels 1 and 2: the controller stopped at x -17.52 (the unchanged wall proxy) with 0.000 m further displacement over 1.5 s, grounded, camera overlaps empty. `wall_contact_firstperson.png` shows the camera pressed against the plaster with strap ears either side and no clipping through the vessel shell. The dressing has no colliders by design; `filters-verify-saved-scene.json` and `colliders-before.json` show the 27 frontage colliders (bank plus zone) identical before and after.

### City-loop smoke, `city-native/report.json`

`passed: true`, `route_exit=0`: West Gate to hill to Ring Gate to Lattice traversal, Vex/Torr/Linn dialogue and modal input blocking, Basic General buy and sell with exact credits/inventory, Lattice link and all four NPC objective flags, pause/inventory/notes, Ring Gate offline, return reset. No runtime exceptions. This is the same wrapper as the reconciliation check (1280x720, cross-city, not a nearby-interaction test in itself); the nearby interaction is Vex's prompt, still live at the west-gate spawn ("E · Talk to Vex" in every before and after capture).

### Checks and logs

- EditMode: 82 of 82 passed (`editmode.xml`). No test targets this dressing; the saved-scene verification above is the closest.
- Release smoke (`release-native/report.json`): launched with `--athen-qa`, probe folder stayed **empty** (bridge absent), 1920x1080 window, non-blank render (stddev 107), no exception lines, no development marker, still running after real keys. Bounded smoke, not a release route or perf run.
- Player logs (before, after, city, release): no exception, NullReference or shader error (the single loose grep hit per log is the driver's GL extension list line, not a message); the atlas warning "Reduced additional punctual light shadows resolution" appears once in the baseline log and once in the new one, so it is not new.

### Localised cost (6 s dwells at noon, uncapped, `localised-cost-comparison.json`)

Host load average (1/5/15 min) was 1.6/0.8/1.2 for the before fixed set, 2.9/2.4/2.0 after; 2.7/1.3/1.3 before players, 4.4/3.0/2.2 after. So the after runs were on a somewhat busier host: a local comparison, never qualification. GPU frame time and draw-call counters are unavailable in this player.

| View | fps before / after | p50 ms | p99 ms | SetPass |
| --- | --- | --- | --- | --- |
| audit front | 85.1 / 84.8 | 11.77 / 11.80 | 13.07 / 12.74 | 308 / 290 |
| audit door | 115.5 / 114.4 | 8.65 / 8.75 | 9.88 / 9.68 | 338 / 335 |
| audit side right | 104.4 / 102.8 | 9.61 / 9.77 | 10.84 / 11.08 | 314 / 314 |
| audit side left | 107.5 / 107.5 | 9.21 / 9.26 | 10.58 / 10.72 | 299 / 296 |
| fp front lane | 115.7 / 118.1 | 8.55 / 8.24 | 11.95 / 11.74 | 305 / 290 |
| fp door approach | 141.4 / 139.5 | 7.02 / 7.10 | 7.96 / 8.23 | 253 / 257 |
| fp close 1.6 m | 127.9 / 123.2 | 7.69 / 7.84 | 9.85 / 10.10 | 291 / 299 |
| fp label | 139.3 / 187.3 | 7.14 / 5.29 | 8.15 / 6.35 | 276 / 215 |
| fp joints | 216.2 / 213.5 | 4.54 / 4.62 | 5.62 / 5.47 | 112 / 132 |
| fp valve | 129.3 / 128.1 | 7.67 / 7.77 | 9.08 / 8.87 | 286 / 293 |
| fp oblique left | 158.2 / 154.7 | 6.25 / 6.41 | 7.11 / 7.38 | 241 / 240 |
| fp oblique right | 137.1 / 133.7 | 7.23 / 7.45 | 8.57 / 8.53 | 221 / 226 |

- Most matched views are within about 0.3 ms p50 and 0.3 ms p99 (0 to 4 percent fps), inside run-to-run noise on a host whose load differs. Close views 1.6 m (about 3.7 percent fps, +0.25 ms p99) and joints (+0.1 ms p50) are the likely place the added surfaces show up, and even there the sign of p99 is mixed.
- **fp label's +34 percent is not a gain**: the after run stood 0.06 m further out and yawed 3 degrees differently, and that view is sensitive to what falls in frame (SetPass 276 vs 215). Discard it as a comparison; the stand positions are in the capture JSON.
- Fixed audit cameras include the whole street, so the bank is a small share of the frame: the cost there is essentially unmeasurable. No frame over 33 ms was recorded in any dwell except the noted 25 to 27 ms max in front lane (also present before).
- Texture memory (Unity counters, `after-native/airwater-captures-mem.json` vs `before-native-mem/`): resident `textureCurrentBytes` 4,476,012,616 before vs 4,483,090,168 after (**+6.7 MiB**); desired 4,705,379,916 vs 5,214,202,824 (**+485 MiB, the streaming target, not resident**); theoretical full-resolution 7,683,505,948 vs 7,796,751,820 (**+108 MiB**, which matches the parent's ~108 MiB BC7 estimate). Unity allocated +7.7 MiB. The two memory snapshots were taken at different play times (frame 1,003 vs 51,568), so the resident and desired figures are indicative only. Driver VRAM residency was not measured.
- Fixed-view GPU time is unavailable, and no long-run hitching was measured.

## Visual review (my scoring, not acceptance)

At the three sun positions, from the fixed audit cameras and player-height views:

- **Attachments read as attached.** Each vessel now has two hoop straps with tension lugs and bolts, a cradle under the bottom collar on wall plates, and a distinct outlet (hose, blanked cap, 45-degree bend). The header is a real DN60 pipe with three tees and hangers running into the riser; the valve, red lever, gauge and ISOLATE plate sit on the pipe and wall. No floating fitting or duplicate hidden surface was seen in the native captures. Mineral crust and drip runs follow the joints.
- **Labels are correct, not mirrored** (FILTER 1/2/3 read left to right from the avenue; FILTER 1 is nearest the door). At 0.8 m the FILTER 1 plate is fully legible; at 1.6 m it is legible on all three vessels; from the avenue (4.5 m) they are small marks, as the parent predicted.
- **08:00 shade:** straps and plates can be made out at close range, but the bank is dark and the differences from the old bank are mostly silhouette (straps, header) rather than surface detail. The ISOLATE plate and gauge are hard to read in deep shade.
- **16:00 warm light:** the valve, red lever, gauge and riser read well; the ISOLATE plate is only just legible ("ISOLAT…" partly hidden by the vessel cap from the sampled stand position).
- **Colour:** the new copper/bronze header is strongly orange against the pale plaster at noon (as the parent warned). It reads as fresh metal beside weathered vessels; a tint on `AW_Bronze` would soften it. Not changed.
- Scores (composition/silhouette 4, scale 4, material detail 3.5 to 4 at 0.8 to 1.6 m, lighting/depth 3, density/storytelling 4, temporal stability not assessed beyond one recorded approach, UI unchanged). **Lighting/depth is below 4 (shade), so not accepted.**

## Defects and limitations (honest list)

1. The header is too orange against the plaster at noon; unchanged pending Carl's judgement (tint `AW_Bronze`, not the map).
2. ISOLATE plate (90 x 60 mm) is only readable within about 2 m and is partly occluded by the vessel cap from some stand positions; the gauge needle is not legible below about 2 m either.
3. Shade at 08:00 is muddy for small fittings; no local light was added or tested, by scope.
4. No LOD1 (36k triangles across five modules); the localised cost is small but not zero at 1.6 m.
5. +108 MiB theoretical full-resolution texture memory; resident growth was measured only as +6.7 MiB at differing play times. 1024 tiles for rubber/steel/mineral were not trialled.
6. Small-part overlaps (bolts through flanges, nuts on studs) were not checked in wireframe or a physics test. The fittings carry no collider (as the old bank had none): the unchanged wall proxy stops the capsule 0.35 m from the plaster, so the player capsule can overlap the up-to-0.5 m fittings volume between the vessels. Camera overlaps stayed empty and nothing clipped visibly (`wall_contact_firstperson.png`), but a physical bank collider is not part of this pass.
7. The valve lever (world y 2.62) is at full-stretch reach, as noted by the parent; nothing is interactive and there is no water simulation. Drips and the gauge are static geometry.
8. The city-loop smoke ran at 1280x720 through the shared crafting wrapper and does not exercise a nearby interaction inside the frontage; Vex's prompt at spawn was confirmed in the before/after captures.
9. Cost measurements were on a host whose load differed between runs (up to 4.4); the two texture-memory snapshots are from different play times.
10. Working-tree state only: RenderChunk assets were regenerated by the rebuild (many appear deleted/added in git), so review the scene and prefab, not a line diff. `Builds/` now hold the new dev and release builds. `before-native-mem-unused/` is a launch that was superseded (same content class, kept for honesty). Nothing was committed.

## Tools added under unity/tools

`capture_airwater_filters.py` (fixed, player-height, traversal and memory stages, 08/12/16), `check_airwater_wall_contact.py`, `compare_airwater_stills.py`; `launch_phase1_qa.py` gained an `ATHEN_PLAYER_EXE` override so a preserved baseline build can be launched for matched comparisons. The pass script is `Editor/AirWaterFilterPass.cs`.
