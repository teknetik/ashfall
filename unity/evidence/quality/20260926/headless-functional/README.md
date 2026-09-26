# Isolated native input test availability — 26 September 2026

No functional tests were run: the required independent virtual-display tools are
not installed. [Availability record](availability.json).

`Xvfb`, `xvfb-run`, `Xephyr`, Weston, Cage, Sway and Gamescope were not found.
Openbox, Fluxbox, twm and Matchbox were also absent. The installed Xorg has only
modesetting and NVIDIA drivers, with no dummy display driver. Existing
`ATHEN_UI_XVFB` branches in the repository remain useful harnesses but do not
supply their missing virtual display server.

Installed Xwayland needs a Wayland compositor. Installed Hyprland is the user's
locked desktop compositor; starting another instance against physical DRM or the
existing desktop would not establish the independent virtual-display setup
requested for this check. No such session was started, no packages were installed,
no existing lock was bypassed, no preferences were changed and no QA script
assertions were altered. There are no owned processes to clean up.

Renderer, resolution, input behavior and performance are **unavailable** for this
attempt. The native city loop, traversal, movement and toggle/relaunch checks
remain outstanding. This availability check does not weaken their requirements.

Reference inspected while evaluating the installed Hyprland alternative:
[Hyprland compositor backend initialization](https://github.com/hyprwm/Hyprland/blob/main/src/Compositor.cpp).
