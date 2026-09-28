# t_6c931016 attempt 3: 27 Sep 2026, 16:22–17:25 BST (snapshot only; for review, not self-accepted)

Workspace: `/home/teknetik/code/.snap/ao2-t_6c931016`, the isolated btrfs reflink snapshot. The shared checkout
`/home/teknetik/code/ao2` is untouched (still 793 porcelain entries). Nothing is committed. This follows
STATUS-t_6c931016.md and the ops recovery t_1c5d2f32.

Unity, Blender and every native player ran in their own `systemd-run --user` units with memory caps, so oomd did not
recur.

## Changes in the snapshot
- `Assets/AthenHill/Editor/WardenGroundFix.cs` (new): request #2 follow-up. It moves only the Warden's visual child
  (`ward-guard`) and leaves the gameplay root alone.
  - Rell went from +56.2 mm to −3.0 mm (localY 0.241 → 0.182).
  - Ossa is at +6.3 mm, inside tolerance, so it was unchanged.
  - The fix is idempotent, and the scene was saved. Log: `warden-ground-fix.txt`.
- Request #6, FP hands v3: `art/character_feel_20260927/fp_arms/build_fp_hands_v3.py` produces `PlayerFPHands_v3.glb`
  (26,064 tris, the same budget as v2). The v2 source and output are archived in `fp_arms/v2-archive/`.
  - Firing thumb: the root runs low and tight over the backstrap under the beavertail, then forward along the left of
    the frame, resting on the support thumb with a ~3 mm crease. The v2 tube that crossed the back of the firing hand
    is gone, and the v3a "hook" above the backstrap is reduced.
  - Thumb root: a thenar/web hull joins it to the palm.
  - Support thumb: straight forward along the frame.
  - Fingers: the creases are 3.2 mm (was 2.4 mm), and the voxel size is 0.9 mm (was 1.1 mm), so the fingers stay
    separated after the remesh.
  - Glove: worn tan leather, sRGB .40/.33/.25 (was .26/.255/.235, which read as a black blob at dusk).
  - Diagnostics are in `fp_arms/build_checks_v3.json`. Only 4 firing-thumb source vertices sit >1.5 mm inside the
    pistol mesh (the Meshy pistol isn't watertight, so ray parity is approximate). The remaining hand-in-hand counts are
    firing fingertips tucked under the support palm, which is hidden and by design (as in v2).
- `FPGripPass.cs`: installs v3 when present (else v2), and the glove material colour is updated. The v2 glb stays in the
  project. Rollback: rename `PlayerFPHands_v3.glb` and run Install, or `UseOldArms(vm,true)` for the v1 arms.

## Final state: builds r6, 17:06–17:11
- Sequence: WardenGroundFix (idempotent, no change) → FPGripPass Install → Editor renders → #1–5 read-back → builds.
- Linux Development: Succeeded, 0 errors, 79 s.
- Linux Release: Succeeded, 0 errors, 112 s.
- Both use OpenGLCore at 1920×1080. See `linux-build-dev.json` and `linux-build-release.json`.
- **Edit Mode tests on the final state (17:11–17:13): 66/66 passed, 0 failed, 65.6 s.** See
  `editmode-results-final.xml`.

## Native checks on the r6 dev build (Editor closed), 17:13–17:23
Hardware: RTX 3060 12 GB, driver 610.57.04, OpenGLCore, render scale 1, 1920×1080.

- `check_character_feel.py`: PASSED. Wardens and colonists were recorded (far and near), footsteps logged over
  Stone/Concrete/Gravel/Sand, the pistol worked in third person and first person (draw, ADS, fire, first-person walk,
  walls), and it holsters inside the walls. Output: `native/character-feel/` (`guards.mp4`, `surfaces.mp4`,
  `pistol-third-person.mp4`, `pistol-first-person.mp4`).
- `check_checkpoint.py`: PASSED (`native/checkpoint/walkthrough.mp4`).
- `check_depot.py`: PASSED (`native/depot/depot-fight.mp4`).
- `capture_requests.py`: `native/requests-1-6/`, at the default start hour with no timeSet. `time-state` reads hour
  17.0 and default 17.0. It covers spawn, avenue, hill, gate, market, West Gate, road, depot, range, the Wardens and the
  post, plus a real Shift+W run video and a first-person hip/ADS/fire video with the pistol collected by real E input
  (hasPistol and armed true, 3 shots).
- Exceptions: 0 in all four Player.logs.

Frame timing is uncapped, from the checks' profilers (`native/frame-timing-summary.json`):

| Route | Duration | Average FPS | p50 | p95 | p99 | Max | Frames >16.67 ms |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Checkpoint | 20 s | 228 | 4.0 | 14.2 | 16.2 | 19.2 ms | 30 of 4,624 |
| Depot route | 28 s | 189 | 4.5 | 13.3 | 15.5 | 17.4 ms | 2 of 5,320 |
| Depot fight | 11 s | 169 | 5.7 | 7.4 | 8.1 | 10.8 ms | 0 |

- The average FPS is at least 60 and the p99 is at most 16.67 ms on every route.
- GPU ms is unavailable (the bridge reports 0).
- Submitted triangles peak at about 27.9 M across all passes (checkpoint).

Earlier runs are kept for comparison, and all of them passed:
- `native-hands-v2/`
- `native-hands-v3b/`

## Request status (saved scene read-back `requests-1-5-verify.json`, native captures in `native/requests-1-6/`)
1. Run cadence: run playback is 1.457 at 6 m/s (stride 4.12 m/s; was 1.714), and the movement speed is unchanged. The
   native run video is `01-run-dusk.mp4`, and `surfaces.mp4` has more. Applied.
2. Warden feet: Ossa +6.3 mm and Rell −3.0 mm (the lowest skinned vertex over the idle cycle, relative to the ground).
   Native captures: `02-warden-*.png`, `02-wardens-post.png`, `native/character-feel/guard-*-near.png`. Applied.
3. Road tree: `searsiasmall` was moved to (−87.5, −1.18, −7.0), off the service road, with its collider disabled.
   `34-cam_berms_road.png` shows a clear road, and the depot route ran without obstruction in `check_depot` and the
   feel check. Applied.
4. Truck: uniform scale 0.65 (no axis stretch). Its bounds are 8.2 × 3.39 × 5.56 m, and the box collider is
   7.65 × 2.96 × 3.39 m. The native `34-cam_berms_gate.png` and `34-cam_market*` show it beside the West Gate at
   plausible scale. It's applied, but flagged for review:
   - The collider width is ~3.4 m, wider than Carl's ~2.5 m guide (the height is inside 3.5–4 m).
   - The nearest wall segments leave a ~7 m opening (south wall ends z −2.5, north wall starts z 4.5), so it would
     clear.
   - Carl may still want it narrower. A further uniform reduction to ~0.5 would give ~2.6 m width but ~2.6 m height,
     so the model's own proportions are the limit.
   - The truck is static, so there's no drive-through test.
5. Dusk: the default hour is 17.0, with the sun at ~11° (direction y 0.19), intensity 0.98, post exposure −0.12,
   Trilight ambient, and 17 lamp lights on at 0.47. Native captures `01-spawn-default-hour.png` and `05-dusk-*.png`
   show low warm sun and long shadows, with readable UI and shade that isn't crushed. Applied.
6. FP grip v3: installed, and verified natively in hip, ADS, fire, walk and draw. It matches the reference in its
   essentials: two hands, support fingers wrapping the firing hand, thumbs forward and stacked along the left of the
   frame, the slide centred and level, no visible interpenetrating fingers, adult hand size (~18.5 cm), and it's
   aligned to the view-model pistol so sway, recoil and draw move it unchanged. Evidence:
   - `fp-grip/editor-before` (v1)
   - `editor-after-v2`, `-v3a`, `-v3b`
   - `editor-after` (final)
   - `blender-v3/` (orthographic sides, behind, ADS eye)
   - `native/requests-1-6/06-fp-*.png` and `06-fp-pistol-dusk.mp4`
   - `native/character-feel/fp-*.png` and `pistol-first-person.mp4`

   Remaining defects (not photo-grade):
   - The fingers are smooth procedural forms with no knuckle creases, tendons or texture or normal detail. The
     materials are flat albedo.
   - From the ADS eye, the firing hand's thumb root is still a large rounded mass behind the slide.
   - The hold is static; the trigger finger doesn't animate.
   - A photo-grade result needs a sculpted or rigged hand with finger bones, a posed grip, and baked normals and
     texture. That's a separate art card, suggested as follow-up.
7. New NPCs: not in scope.

## Rollback
- Rell: set `Warden Rell/ward-guard` localY back to 0.241.
- Hands: rename v3 so v2 installs, or `UseOldArms`.
- Whole snapshot: the baseline is `/home/teknetik/code/.snap/ao2-t_6c931016-baseline`.
- Porting this work to the shared checkout needs an explicit, reviewed copy step. That has not been done.
