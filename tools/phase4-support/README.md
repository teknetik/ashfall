# Phase 4 verification

The production integration check expects a completed build and an already
running preview server. It does not build, restart servers, or change game
source. From the repository, run:

```sh
node tools/verify-phase4.mjs http://127.0.0.1:4173
```

This launches headed Chromium with ANGLE Metal on macOS. The 1080p gate is
mandatory: at least 58 fps, no more than 80 draws and 250,000 rendered triangles.
`--headless` is available, but software-renderer results do not satisfy the
hardware claim and still face the same FPS gate.

The command checks the exact collider/controller configuration against the
successful full Phase 3 route before retaining that route evidence. It then
uses real W, Shift, E, Escape, R and touch events to verify authored movement,
idle/walk/run/talk clip selection, actual bone-pose changes, pause freezing,
NPC motion, reset ownership and mobile labels. It archives six named 1080p
captures via the game's `shot()` API plus active-play images in a new
`runs/<timestamp>-<pid>/` directory. Previous phase evidence is untouched.
Large GLBs are captured through one fetch and the exact bytes fulfilled to the
application, avoiding Chromium's inspector-cache limit.

The independent NPC fixture is reproducible while the dev server is running:

```sh
node tools/phase4-support/verify-npc.mjs
```

It derives the repository path from its own module URL, samples the actual
NPC definitions and waypoint paths against archived world collision geometry,
and runs entity/DOM logic in an isolated page with injected character fixtures.
It checks supported feet, body clearance, deterministic route positions,
nearest-target selection, interaction callbacks, tag projection and disposal.
Each run writes `npc-fixtures/<timestamp>-<pid>.json`. `ATHEN_QA_URL` overrides
the default dev server at `http://127.0.0.1:5173`; `ATHEN_NPC_COLLIDERS` can point
to a newer compatible runtime report. These fixtures do not stand in for live
rig or visual acceptance.

`character-checks.mjs`, `asset-validation.json`, `asset-poses.png` and
`physics-regressions.json` preserve the separate character-library, asset and
physics checks. The runtime harness records loaded asset hashes, so captures
can be associated with the exact final player and NPC binaries.

The authoritative final-asset run is
[`runs/2026-09-07T10-35-27.326Z-21524/report.json`](runs/2026-09-07T10-35-27.326Z-21524/report.json):
all seven runtime groups passed with no browser/network errors. Moving at an
actual 1920×1080 buffer measured 120 fps, 8.6 ms p95 frame time, 57 draws and
224,596 rendered triangles on Apple M4 Max / ANGLE Metal. This is observed
hardware evidence; a medium-laptop performance claim remains unmeasured.
The same run proves exact equivalence of all 263 static collider definitions
and the controller configuration to the successful 54.920-second Phase 3
keyboard route. Six named captures and desktop/mobile active-play captures
are archived beside the report. Visual likeness acceptance is separate from
these runtime checks.
