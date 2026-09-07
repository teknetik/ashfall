# Phase 3 browser regression evidence

Run after the authored world is integrated and the debug API reports phase 3:

```sh
node tools/verify-phase3.mjs
```

The default URL is `http://127.0.0.1:5173`. The script does not build the game,
start a server, or restart an existing server. For production preview, first
build and start the preview separately, then run:

```sh
ATHEN_QA_URL=http://127.0.0.1:4173 node tools/verify-phase3.mjs
```

Optional flags:

- `--headed`: launch Chromium visibly, retaining the same 1080p test viewport.
  On macOS this selects ANGLE Metal and records the actual GPU. Use it for the
  full route on this machine: headless software rendering ran at 3 fps and
  reached the route's wall-clock limit despite continued grounded movement.
- `--require-fps`: fail if the measured active-play average is below 58 fps.
  A software renderer still cannot establish target-laptop acceptance.
- `--visual-only`: capture/import/responsive/input checks with the long route
  and focused collision regressions skipped. The result is `PARTIAL`, never
  a full regression pass.

Each run creates `runs/<timestamp>-<pid>/report.json`, six 1920×1080 named-camera
PNGs, and desktop/laptop/mobile screenshots. Failures retain the current state
and a screenshot. Existing `tools/shots/` files, including Phase 1 evidence,
are untouched. Screenshot capture calls the live `__ATHEN__.shot()` API;
Playwright archives its real PNG upload bytes and returns that archive path.
This verifies the named-camera renderer and restoration, not the Vite writer.

The continuous route starts at the actual west-gate spawn and uses only real
keyboard input and right-mouse drag. Read-only debug snapshots steer toward
the retained Phase 1 checkpoints. It traverses the hill stairs and plaza,
Ring Gate, western bypass, and Lattice Jack without teleports. Subsequent
independent shop, gate, and boundary tests use public landmark teleports only
for setup, then real movement for the collision test itself.

The harness rejects phase 1/2, missing or malformed `world.glb`, missing
`COL_` nodes, world load errors, remaining greybox landmarks when exposed,
blocked routes, missing support heights, capsule penetration, lost camera
occlusion, escaping boundaries, stuck inputs, reset leaks, blank captures,
renderer-budget excess, and browser/page/network errors. It records optional
`__ATHEN__.world`/`worldDiagnostics` and `__THREE_GAME_DIAGNOSTICS__.world` data.
For GLB evidence, Playwright fetches the network response and fulfills the
application request with those exact bytes. This avoids Chromium inspector
cache eviction for the 19.7 MB world and does not substitute a second download
as evidence for the loaded asset. Axis-aligned imported boxes remain subject
to penetration checks even though their diagnostics include an identity
quaternion; genuinely rotated boxes retain swept-controller coverage.

`PASS` means the stated automated regression passed. It does not finish the
visual scorecard, prove laptop-GPU 60 fps, validate later character/shop/audio
phases, or establish production release readiness. Compare the fixed PNGs to
the frozen references and record target-device performance separately.

The full integration run `runs/2026-09-07T09-59-38.809Z-14868/report.json`
passed against the frozen production preview with all eight authored world
landmarks. Command: `node tools/verify-phase3.mjs http://127.0.0.1:4173 --headed`.
It recorded 880 movement samples, a 54.9-second uninterrupted main route,
zero browser errors, six fixed captures, and functional mobile touch input.
The active 1080p sample measured 120 fps on Apple M4 Max Metal, 28 draws and
113,177 triangles. This is the recorded hardware result, not a claim about
an untested medium laptop. Earlier failed attempts remain archived separately.

Reference ledger used while implementing this harness:

| Reference | Read | Failure |
| --- | --- | --- |
| threejs-qa-release/references/qa-release-checklists.md | yes | none |
| threejs-qa-release/references/checklists/visual-verification.md | yes | none |
| threejs-qa-release/references/checklists/playtest-qa.md | yes | none |
| threejs-qa-release/references/checklists/release.md | yes | none |
