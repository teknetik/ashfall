# Character movement candidate — 8 September 2026

The movement pass is implemented and ready for root-agent integration and native review.
This document is not a claim of AAA acceptance. The source characters still have
24-bone rigs without finger articulation or facial blendshapes; motion cannot
resolve their geometry, skin/hair/armour textures or absent lip sync.

The original player GLB had one-key idle plus real walking/running. All four
original guard states were one-key static aliases. `source-audit.json` records
source hashes, bones, animation channels, key counts and durations.

## Motion and preserved behavior

- The player has separately authored takeoff, rising, falling, stationary landing
  and moving landing clips. Anatomical joint arcs, asymmetric leg tucks, arm
  follow-through and planted-foot two-bone constraints provide compression and
  recovery. The moving landing is authored over the supplied running motion, so
  continuing to run does not freeze both feet during recovery. Ordinary editable
  `.anim` assets are baked at 30 Hz; no runtime rig reconstruction is used.
- Guard idle and talk use new Meshy animation on their existing rig. Both full
  exports are retained in `source/`. Action 0 Idle is 4 seconds / 121 frames;
  action 56 Stand_and_Chat is 5.1667 seconds / 156 frames. Each cost 3 credits,
  6 total. `meshy-*-task.json` records IDs, options, corrections and hashes.
  The guard's talk export had an 8.15 cm sole hover and a large X/Z anchor offset;
  the animation-only extraction applies a constant hips correction. Source skin
  sampling found corrected sole clearance of 0–9.2 mm for talk, 0–14.5 mm for idle.
  These are source geometry checks, not native visual approval.
- Original authored guard idle/talk candidates are retained as recovery `.anim`
  files. The installer assigns the Meshy clips to the four guards. Player idle
  and conversational body motion are authored on its own supplied standing pose.
- `ActorAirMotion` takes actual grounded state, accepted jump input and vertical
  velocity. Walking off an edge enters falling without takeoff; brief tread
  contact losses avoid a false landing; a new accepted jump interrupts landing;
  teleport resets the visual state. Airborne motion never drives the controller.
- `PlayerMotor` retains gravity, jump height, walking/running speed, step/collision,
  turn speed and ground snap. Its motion integration only exposes read-only state
  and sends actual movement to animation. No jump-input delay is added.
- Walk/run blends preserve footfall phase. Ambient walkers anticipate the next
  segment and ease their heading instead of rotating instantly at a corner. The
  authored route positions, distance schedule, speeds and model assignments stay
  unchanged. Velocity still follows the original piecewise-linear route; this is
  a preserved route limitation to inspect, not fully authored corner footwork.
- First-person camera behavior is unchanged: visual skin is hidden with shadows
  retained, and camera height remains attached to the controller rather than hips.

## Exact installation

Root owns the shared Editor and native sessions. In the open saved city, after
compilation and while outside Play, execute through Unity MCP:

```csharp
AthenHill.Editor.CharacterMotionPass.Install();
```

The menu is **Athen Hill → Characters → Author and install grounded character
motion**. It imports the new animation-only source files as Legacy, authors clips,
updates existing MeshyPlayer/WardGuard prefab animation fields and scene overrides,
and saves. It does not replace visual roots, materials, meshes, NPC interaction
roots or routes. A before/after identity guard includes those references and
controller tuning. New assets preserve GUIDs on deliberate reauthoring. The
installer does not rebuild city geometry because no static render source changes.

The expected generated report is `animation-authoring.json`. Source imports and
saved clips must survive reopen/build before the pass is accepted.

To reproduce only the external animation extraction from retained source:

```sh
python unity/evidence/quality/20260908/movement/prepare_chat_source.py
python unity/evidence/quality/20260908/movement/prepare_chat_source.py --idle
```

The recipe uses NumPy, preserves original files and emits animation-only GLBs;
existing guard skin/material assets are never replaced by a new generated mesh.

## Verification contract

Run the existing Unity Edit Mode suite after installation. New tests are
`AthenHill.Tests.ActorAirMotionTests` (7 behavioral cases) and
`AthenHill.Tests.CharacterMotionAssetTests` (8 installed-clip cases). The latter
reject static aliases and actor/root translation curves. No tests have been
reported as passing in this candidate document; root records actual results.

After root builds and launches the opt-in development player at native 1080p:

```sh
ATHEN_NATIVE_PID=<pid> ATHEN_NATIVE_DIR=<qa-folder> ATHEN_MOTION_VIDEO=1 \
  uv run --with python-xlib python \
  unity/evidence/quality/20260908/movement/check_character_motion.py
```

This attaches to the provided player; it neither builds nor quits it. It records
standing and running jumps, holding the jump key, repeated jumps, inventory modal
blocking, walking off the hill, jumping down stairs, and first-person wheel zoom
and jumping. Actual movement uses keyboard/wheel events. Existing QA commands
only place the starting landmark, select cameras and record. The fall/stair routes
must be checked against native saved layout; a blocked route is not evidence of
an animation failure or authorization to change unrelated colliders.

`motionStart` and `motionStop` are narrow additions to the existing `NativeQa`
command switch. They explicitly enable the new recorder at the physics cadence,
then return `motion.json`. Recorder startup rejects release builds; no new release
listener is introduced. Each scenario saves its own samples and a combined report.
The test requires the unchanged ~1.2 m configured jump to have a discrete simulated
rise of 1.16–1.31 m (the existing integration's first-step velocity is unchanged),
correct phase sequence, no duplicate held-key jump, continued running on moving
landing, modal input isolation, and settled ground contact. These are functional
checks, not an animation quality score.

Independent visual review must inspect normal-speed and slow-motion third-person
front/side/back jumps; foot plant, knees, pelvis compression, arm arcs and the
walk/run return; all four guards from full-body and conversation views through
multiple idle/talk loop seams; walker corners; and first-person camera/near clipping.
Record defects and reject bad deformation or obvious sliding irrespective of
state-machine/test success. No native clip captures have been reviewed yet by the
movement author.

Source API reference: [Meshy animation library](https://docs.meshy.ai/en/api/animation-library).

## Independent-review capture matrix

The independent reviewer rejected the initial single follow-camera video as
insufficient evidence. `capture_motion_matrix.py` now supplies a separate named
clip for each requested view and actor; it does not auto-accept visual quality.
The planned set has **42 clips**: 9 front/side/rear standing/running/repeated jump
shots, 2 edge views, 8 guard loop shots, 3 player transition/control shots, 16
individual ambient route corners and 4 first-person edge-case shots.

Before root's coordinated build, regenerate requests from the current saved scene
and install the Editor-only review cameras through Unity MCP:

```sh
python unity/evidence/quality/20260908/movement/prepare_capture_plan.py
```

```csharp
AthenHill.Editor.MotionReviewSetup.Install();
```

The setup adds 32 disabled, editable cameras under **Movement review cameras** and
two QA start markers under Landmarks. It reads the four NPC placements and the
16 saved walker waypoints; it checks NPC placements before installation and
exports actual clip references, controller tuning and potential blocked sightlines
to `capture-layout.json`. It adds no meshes, colliders or active runtime cameras.
These are requested compositions, not proof of unobstructed native framing. Inspect
the initial native frame of each family and adjust only owned review cameras if
foreground geometry/UI obscures the actor. Actor rigs/route geometry must not be
moved to make a review shot pass.

Run after the root agent builds and launches the opted-in development player:

```sh
ATHEN_NATIVE_PID=<pid> ATHEN_NATIVE_DIR=<qa-folder> \
  uv run --with python-xlib python \
  unity/evidence/quality/20260908/movement/capture_motion_matrix.py --section all
```

Available focused revision sections are `jumps`, `guards`, `player`, `walkers` and
`first-person`. `--actor npc_vex` (repeatable) narrows the guard/walker sections.
Every run gets a new timestamped directory; previous failed videos remain intact.

- Each guard has a continuous full-body and a conversation-distance clip with at
  least **three complete 4-second idle loops, three 5.1667-second talk loops and an
  idle return**. Conversation starts/ends through real E/Escape input. The script
  verifies the intended guard's actual current clip for the required observed span,
  rather than inferring playback from a source file. Modal UI stays active.
- Front, side and rear camera axes allow the same west-gate running trajectory
  through appropriate real W/S/D input. Standing/repeated shots use closer cameras
  than running shots. Real input aligns the player before each matched shot.
- All three travelers and the mechanic are located from native actor samples on
  their unique saved routes. The script waits for each of their four corner
  approaches and records approach/turn/departure without changing route phase,
  speed, position or animation playback. Wait duration follows the real route.
- Player clips include three idle loops, starts/stops, walk/run changes, reversals,
  moving turns and movement immediately after landing. A separate stationary
  orbit records an explicit remaining limitation: current input rotates the camera
  while standing, and there is no separate character turn-in-place verb. That shot
  is not mislabeled as implemented turn-in-place animation.
- First-person clips cover stairs, hill edge, sheltered wall and the existing
  closed Finery doorway. They include movement, jump/landing where appropriate,
  strafe against nearby surfaces and wheel zoom out/in while settling. Camera
  overlaps and final grounding are checked, with clipping/shadow continuity left
  for independent visual inspection.

Each **actually recorded** clip receives an MP4, SHA-256, ffprobe duration/stream
metadata, exact encoded frame timestamp CSV, a JSON index with observed actor
states and input events, and the physics-cadence trace. A generated
`review-index.md` links the clips/details/frame timestamps. The run manifest
records executable/build-data hashes, saved scene hash, settings, environment and
saved animation assignments. No successful media manifest is pre-created.

Input events carry exact monotonic actuation times. Their `videoOffsetEstimate`
is measured from ffmpeg launch and is explicitly approximate because encoder
startup is asynchronous. Use each named clip's encoded PTS/frame index for precise
critic defect timestamps; do not misrepresent process-start offsets as exact video
frame times. Recorder/behavior checks can reject a clip as incomplete, but all
animation/visual decisions remain **Unreviewed** until the independent critic
inspects actual native output. Recording includes diagnostic overhead and is
separate from performance qualification.
