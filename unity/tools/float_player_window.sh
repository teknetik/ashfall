#!/usr/bin/env bash
# Float and size the native Athen Hill QA player under Hyprland (a tiled window stalls the render loop and breaks the 1920x1080 capture).
# Usage: float_player_window.sh <pid>
set -euo pipefail
export XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-/run/user/$(id -u)}
export WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-wayland-1}
export HYPRLAND_INSTANCE_SIGNATURE=${HYPRLAND_INSTANCE_SIGNATURE:-$(ls "$XDG_RUNTIME_DIR/hypr" | head -1)}
pid=$1
addr=$(hyprctl clients -j | tr -d '\n ' | sed 's/},{/}\n{/g' | grep "\"pid\":$pid," | sed 's/.*"address":"\([^"]*\)".*/\1/' | head -1)
[ -n "$addr" ] || { echo "no window for pid $pid" >&2; exit 1; }
hyprctl dispatch "hl.dsp.window.float({ action = 'enable', window = 'address:$addr' })" >/dev/null 2>&1 || true
hyprctl dispatch "hl.dsp.window.resize({ x = 1920, y = 1080, window = 'address:$addr' })" >/dev/null 2>&1 || true
sleep 1
hyprctl clients -j | tr -d '\n ' | sed 's/},{/}\n{/g' | grep "\"pid\":$pid," | grep -o '"floating":[a-z]*\|"size":\[[0-9,]*\]'
