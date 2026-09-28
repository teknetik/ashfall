# Ward startup menu · 26 September 2026

The existing Unity city now opens on an authored arrival menu with **Start Game**
and **Settings**. Start Game releases the existing West Gate player and shows the
HUD. Settings uses the existing sound/video panel, adds the persisted reduced
motion control, and returns to the menu when opened before gameplay. Escape,
movement and jump cannot bypass the menu. Music continues. The gameplay camera's
culling mask and clear flags are restored when starting; no city geometry or
shadow passes are needed behind the opaque illustration.

The layout is in `Assets/AthenHill/UI/StartupMenu.uxml` and `StartupMenu.uss`.
The original built-in imagegen artwork and complete prompt are preserved in
`Assets/AthenHill/UI/MenuArt`. This is menu illustration, not a depiction or
qualification of the current playable district. The original 1672×941 image is
retained without source resampling; the importer keeps its aspect ratio, disables
mipmaps, uses sRGB and high-quality compression, and allows up to 4096 pixels.

## Acceptance

[`acceptance/report.json`](acceptance/report.json) records the successful real-input
Linux development check. It verifies initial keyboard focus, mouse Settings,
movement/jump/Escape blocking, hidden HUD, reduced motion, sound/video controls,
video preview/revert, Settings return destinations, display change to 1280×720,
keyboard Start Game, restored HUD, movement and pause. Every captured view also
passes a nonblank-image check. The native startup views at
[1920×1080](acceptance/startup-1920x1080.png) and
[1280×720](acceptance/startup-1280x720.png) were visually inspected, together with
the settings panels and the restored gameplay view.

The four existing `ReducedMotionSettingsTests` passed. Both Linux development
and release builds succeeded; the release retains its development-bridge guard.
The [release launch check](release-verified/report.json) also confirmed rendered
menu, keyboard entry into gameplay, restored camera/HUD, movement and pause, with
no runtime exceptions and no development QA snapshot despite the opt-in flag.
Its [menu capture](release-verified/menu.png) has no development watermark.
The first capture in that run was still the Unity splash; visual inspection
records the actual view represented by each file rather than treating its
original capture label as evidence of a settings panel.
[`build-identity.json`](build-identity.json) records the working-tree base revision,
source and binary hashes, build durations, errors and warnings. Existing/concurrent
district and combat work was preserved; this pass did not edit world geometry.

Native hardware: RTX 3060 (12 GiB), i9-10850K, NVIDIA 610.57.04, OpenGLCore,
Unity 6000.6.0f1 / URP 17.6.0. The development acceptance job explicitly allows
background execution to tolerate desktop focus changes. These are menu/input
checks, not a warmed traversal or a new whole-game performance qualification.

Menu review at the intended viewing sizes: composition 4/5, scale 4/5,
illustration detail 4/5, depth/lighting 4/5, UI readability 4/5. The native
type, buttons and focus states remain separate from the artwork. The artwork is
static and introduces no reduced-motion-dependent animation.

## Retained investigation

Earlier folders `native`, `native-final`, and `native-verified` preserve the
failed desktop-focus/window-sizing attempts. Some state/input assertions passed
while captures were blank; those images are **not** visual acceptance. The test
was strengthened to reject blank captures. On this fractional-scale Hyprland
desktop, resizing through the compositor after Unity had initialized its GL
surface caused blank output. Sizing the test window before the first scene frame
resolved that test setup issue. The application's own 1080p-to-720p Settings
change then rendered correctly and passed the complete acceptance check.

Reproduce with:

```sh
DISPLAY=:0 uv run --with python-xlib --with pillow python unity/tools/check_startup_menu.py
```

The helper uses isolated preferences and targets only its own temporary player
window. It does not edit desktop configuration or the user's game preferences.
