# Native visual iteration driver — 10 September 2026

`capture_native_iteration.py` captures the **already built, already launched Linux
development player** at 1920×1080 and render scale 1. It never launches Unity,
Blender, a player or a browser. Root owns the only native Client/input operator;
do not run another capture, input, profiling or bridge command concurrently.

Use a new folder under `unity/evidence/reference-street/20260910/` for every launch
and iteration. The driver refuses an existing iteration report or capture. It
keeps failed reports, partial images and videos; investigate failures and launch a
fresh folder rather than overwriting evidence. `--plan` only reads the saved scene
and requires no player, X11, Pillow or python-xlib.

The captured views include both reference-wide cameras, courtyard ground, both
buildings' fronts/doors, all seven district diagnostic cameras and **three saved
prop cameras supplied by root**. The report retains serialized camera lens and
parent transform records so matched angles can be checked against prior evidence.
The authored default hour is reset and paused, with its exact state recorded.

The short movie enters first person using real wheel input, walks both first
treads and porches with real W input, tests left-drag look, and records doors and
thresholds. It uses diagnostic yaw to steer walking, as the existing route checks
do. The expected movie is roughly 45–60 seconds; actual duration is reported. No
teleport occurs inside the movie. Setup resets at West Gate and walks to Field
Supply before recording. Tread centers retain the successfully checked X=14.05 m,
8 cm arrival tolerance and 0.5 second physical settling interval from September
9 V3. Ground height, grounded state, first-person state and camera collision are
asserted. These points rely on this pass preserving the current collision/layout.

The report hashes **every file in LinuxDevelopment**, the saved scene, key bridge
sources, dependencies and the driver before/after the capture. It records actor
state/count, actual settings/environment, PNG hashes and dimensions, video hash
and ffprobe metadata, runtime exception/assertion/shader-error matches and any
native `qa-error.json`. A failure never becomes an art or performance pass.
Logs still need human review. HUD remains visible. This is not full qualification.

## Host command sequence

These launches and real X11 inputs need host execution (`exec_command` with
`sandbox_permissions: "require_escalated"`) under this workspace's managed sandbox.
The existing dependency environment is
`/home/teknetik/.cache/uv/archive-v0/C-D_s9RmoL-ZML5S/bin/python` (Pillow/python-xlib).
The system Python can launch the player and run `--plan`. `ffmpeg` and `ffprobe`
must be available. Substitute the fresh folder and **actual saved camera names**;
the driver rejects names absent from the saved scene.

```bash
python3 art/reference_street_20260910/capture_native_iteration.py --plan
python3 unity/tools/launch_phase1_qa.py unity/evidence/reference-street/20260910/iteration-N-native
/home/teknetik/.cache/uv/archive-v0/C-D_s9RmoL-ZML5S/bin/python art/reference_street_20260910/capture_native_iteration.py unity/evidence/reference-street/20260910/iteration-N-native --prop-cameras CRATE_CAMERA TRASH_CAMERA SCRAP_CAMERA
```

Root closes the player after review. The driver restores follow camera and the
authored clock and releases inputs, but deliberately leaves the player running.
It cannot guarantee input cleanup if its process is killed; release W and the left
mouse button before another attempt. No historical helper/test has been changed.

## Qualification after the critic finds the visual iteration ready

Close authoring apps before timing. Rebuild current development/release players,
verify saved/reopened scene and render chunks, and use a fresh native folder.
Run the existing `unity/tools/check_building_traversal.py --record-warmup` for its
unmeasured 41-point route/movie and separate roughly 134-second measured traversal.
Review all nine actors, preserve routes/collisions, run city-loop interactions
with their own separate profile, and exercise the affected proximity checks.
Record average FPS, p50/p95/p99/max, hitches, actual hardware/API/settings, memory,
and unavailable counters as unavailable. The current target is average ≥60 FPS
and p99 ≤16.67 ms at native 1920×1080. Complete release real-input smoke and disabled
development-bridge checks. Use current dated evidence; September 9 performance or
asset acceptance does not qualify this new build.
