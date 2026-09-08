# Unity controls — 8 September 2026

The native Unity game now uses left-button drag to look, mouse wheel up to zoom
all the way to first person, mouse wheel down to pull back, and Space to jump.
The HUD and Unity control documentation show the same bindings.

Wheel zoom retains the existing third-person obstruction sweep and limits the
maximum boom to 10 m. At zero boom the camera sits 1.65 m above the player root;
the player renderers switch to shadows only so the head/body do not obstruct the
view. Zooming out restores their original shadow settings. Camera pitch is limited
to ±80 degrees. Jump height is editable (1.2 m by default); one input press is
retained until the physics update consumes it. Ground snap is applied only when
descending, and overhead collisions stop upward velocity.

## Native verification

`native/controls-check.json` passes all ten control groups using actual X11 mouse
and keyboard input against the Linux development player, rendering at 1920×1080:

- Left-drag changes yaw and pitch; release stops look; right-drag and unheld
  movement leave the view unchanged.
- Hotbar clicks still work. A drag beginning on a button and wheel input over a
  button do not change the view.
- One wheel notch changes the boom from 4.2 m to 3.5 m. Zoom reaches a clear
  first-person view, with correct eye position, camera-relative movement and look.
- Zoom out restores the player model and respects the 10 m limit.
- Held Space jumps once and lands. An 8 ms tap also jumps; a second press in the
  air does not double-jump. Observed peak rises were 1.27 m and 1.28 m.
- Pause, dialogue and inventory block look, zoom and jumping without leaking a
  queued jump when closed.
- All 16 tested third-person camera orientations across the gate, both shop rows
  and hill remained outside world colliders.

`native/city-loop.json` also passes the existing four-NPC dialogue, buy/sell,
Lattice link, pause, inventory/notes, reset and city-objective regression checks.
The development Player.log has no runtime exceptions. `first-person.png` and
`third-person.png` record the camera transition; the first-person frame was
visually inspected to confirm that the player model does not obstruct the view.

`release/report.json` passes the native release launch, keyboard responsiveness,
nonblank rendering, pause and no-runtime-exception smoke checks. The release
ignored the development listener flag as expected. Both Linux player builds
completed successfully.

The input test scales its 1080p coordinates to the current fullscreen desktop
size. An early test incorrectly treated desktop pixels as render pixels after
another task restored the display to 4K; the corrected input test passes the
same HUD behavior without a further gameplay code change.

## Repeating the checks

Launch `AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64` fullscreen with
`-screen-width 1920 -screen-height 1080 --athen-qa /absolute/evidence/directory`.
Set `ATHEN_NATIVE_DIR` to that directory and `ATHEN_NATIVE_PID` to the launched
player PID, then run:

```sh
uv run --with python-xlib python unity/tools/controls_check.py
uv run --with python-xlib python unity/tools/city_loop_check.py
```

The development-only bridge reports camera and pointer diagnostics but continues
to accept only its existing named commands. Neither control input nor arbitrary
code execution was added to the QA command surface. The normal release build
ignores `--athen-qa`.
