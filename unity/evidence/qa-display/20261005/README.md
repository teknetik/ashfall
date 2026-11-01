# Private QA display trial, 5 October 2026

Question (Carl): can native testing run while he keeps using the PC? The Cua driver's background input is qualified
for native-Wayland Inkscape only (XWayland unqualified, kit ABI does not match this host), and the player is an X11
client, so it was not used. Instead the player ran in its own X server on a virtual monitor.

## Setup

`unity/tools/qa_display.sh up`: a headless Hyprland output `WARDQA` (1920x1080 @ 60, scale 1, at 20000x0, away from
the three physical outputs so the cursor cannot reach it) on its own named workspace `wardqa`, and a rootful
`Xwayland :5 -geometry 1920x1080` fullscreen on it. Jobs run with `DISPLAY=:5`, `WAYLAND_DISPLAY` unset and
`ATHEN_QA_MUTE=1` (game muted through its QA Sound preference). `:5` has no window manager; the harness
(`desktop_input.py`, `qa.py`) finds the player among the mapped top-level windows and sets X focus directly. XTEST input
stays inside `:5`. `qa_display.sh down` removes everything. All of it is runtime state: no config file is written.

- Build: `unity/AthenHill/Builds/LinuxDevelopment` (data 5 Oct 07:55), repository HEAD `f39dfa4b` plus the harness
  edits listed below.
- Player: X11 backend on `XWAYLAND0` 1920x1080, OpenGL Core 4.5, NVIDIA 610.57.04, RTX 3060, quality PC (High).
- Carl was working normally throughout (browser, Slack, file manager, terminal).

## Results

| Run | Result | Carl's desktop during the run |
| --- | --- | --- |
| City loop (`native.sh cityloop`, 180 s) | **CITY LOOP PASS**: four NPCs, flask/scrap trade, shop steps and porches, Lattice | 347 samples: 19 focus changes by Carl, focus on the QA window 0, `WARDQA` focused 0, cursor on `WARDQA` 0 |
| Mouse look (`check_mouse_look_native.py`, private-display mode) | **PASSED 14/14** | 63 samples: all 0 as above |

Logs `cityloop-desktop.log` and `mouselook-desktop.log` hold the 0.5 s samples (time, focused window address,
`QA`/`other`, focused output, cursor position); application names were removed.

Mouse look on `:5` uses relative XTEST motion (`XtestMouse`) instead of a uinput device, which would move Carl's real
cursor: 180 px turned the camera 23.4°, the camera stopped dead (0.0° drift) after every move, pitch, pack, Left Alt
and the left button behaved as on the real-mouse run. Finding: an absolute XTEST move while the cursor is locked still
turns the camera in one jump (150 px right of centre gave 144.3°, about the pointer's absolute X times the relative
gain), here with no compositor pointer lock involved. That suggests the game reads XI2 raw valuators, which carry
absolute coordinates for an absolute XTEST move. Keep `qa.pointer_locked()`; use relative XTEST for mouse moves
while locked.

## Limits and incidents

- Not covered: libinput, Hyprland's pointer lock and a physical mouse. The uinput real-mouse check stays a run
  for when Carl is away.
- Frame-time A/B runs share the GPU with Carl's desktop and are not comparable while he works; keep them for idle time.
- VRAM: system peak 10.6 GB of 12 GB during the city loop (desktop about 4.4 GB). The watchdog guard is 11.4 GB.
- First `up` attempt: creating the output moved keyboard focus onto it, and the new output took the empty numbered
  workspace 5. Focus was restored by hand within seconds; the script now gives the output its own named workspace and
  restores focus (cursor warps off meanwhile) after creating or removing the output. Second `up` and `down` left
  focus where it was.
- First mouse-look run: all steps passed, then the wrapper crashed in cleanup (XtestMouse placed inside the uinput
  class) and left the player running; it was stopped and the check re-run clean (above).
- A Hyprland config reload drops the runtime rules (`WARDQA` would move next to DP-2). Run `down`/`up` after one.

## Harness edits

`unity/tools/qa_display.sh` (new), `unity/tools/desktop_input.py` and `unity/evidence/gameplay-v2/20260930-reqa2/qa.py`
(no-window-manager window lookup and focus), `unity/tools/lookbook.py` and `qa.py` (`ATHEN_QA_MUTE`),
`unity/tools/check_mouse_look_native.py` (private-display mode with `XtestMouse`). Behaviour on `DISPLAY=:0` is unchanged.
