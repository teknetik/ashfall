#!/usr/bin/env bash
# A private display for native QA, so test input never touches Carl's seat (5 Oct 2026).
#
# up:   a headless Hyprland output (WARDQA, 1920x1080 @ 60, scale 1, at 20000x0 so no physical monitor touches it and the
#       cursor cannot reach it) whose default workspace is the named "wardqa" (not a numbered one, so Super+N never lands
#       there), and a rootful 1920x1080 Xwayland on :5 fullscreen on it, unfocused. XTEST into :5 stays inside that X server (its
#       own focus and pointer); Hyprland keeps rendering the output, so the player is not throttled.
# down: stop that Xwayland, remove the output and drop the rules.
# Hyprland moves keyboard focus to a new output, so both put focus back on the window that had it, with cursor warps
# off meanwhile. Everything is runtime state (hyprctl eval/output); no config file is written. A Hyprland config reload
# drops the rules (WARDQA would fall back to position auto, next to DP-2), so run `down` and `up` again after one.
#
# Use: qa_display.sh up|down|status, then run QA jobs with DISPLAY=:5 and WAYLAND_DISPLAY unset, e.g.
#   env -u WAYLAND_DISPLAY DISPLAY=:5 ~/.local/state/ward-programme/native.sh cityloop <OUT>
set -euo pipefail
export XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-/run/user/$(id -u)}
export WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-wayland-1}
export HYPRLAND_INSTANCE_SIGNATURE=${HYPRLAND_INSTANCE_SIGNATURE:-$(ls "$XDG_RUNTIME_DIR/hypr" | head -1)}
OUTPUT=WARDQA NUM=5 UNIT=ward-qa-xwayland
STATE=$HOME/.local/state/ward-programme/qa-display; mkdir -p "$STATE"

monitor_json() { hyprctl monitors -j | jq -c --arg o "$OUTPUT" '.[] | select(.name == $o)'; }
xwayland_up() { [ -S /tmp/.X11-unix/X$NUM ] && systemctl --user is-active -q "$UNIT.scope"; }

# Remember Carl's focused window and monitor; restore_focus puts them back if Hyprland moved focus.
save_focus() {
  FOCUS_WIN=$(hyprctl activewindow -j | jq -r '.address // empty')
  FOCUS_MON=$(hyprctl monitors -j | jq -r '.[] | select(.focused) | .name')
  NO_WARPS=$(hyprctl getoption cursor:no_warps -j | jq -r '.bool // false')
  hyprctl eval 'hl.config({ cursor = { no_warps = true } })' >/dev/null
}
restore_focus() {
  local now; now=$(hyprctl activewindow -j | jq -r '.address // empty')
  if [ -n "$FOCUS_WIN" ] && [ "$now" != "$FOCUS_WIN" ] && hyprctl clients -j | jq -e --arg a "$FOCUS_WIN" 'any(.[]; .address == $a)' >/dev/null; then
    hyprctl dispatch "hl.dsp.focus({ window = \"address:$FOCUS_WIN\" })" >/dev/null
  elif [ -z "$FOCUS_WIN" ] && [ -n "$FOCUS_MON" ] && [ "$(hyprctl monitors -j | jq -r '.[] | select(.focused) | .name')" != "$FOCUS_MON" ]; then
    hyprctl dispatch "hl.dsp.focus({ monitor = \"$FOCUS_MON\" })" >/dev/null
  fi
}
end_focus() { restore_focus; hyprctl eval "hl.config({ cursor = { no_warps = $NO_WARPS } })" >/dev/null; }

up() {
  save_focus; trap end_focus EXIT
  # Rule handles live in Lua globals so `down` can disable them.
  hyprctl eval "if ward_qa_ws then ward_qa_ws:set_enabled(false) end
    ward_qa_ws = hl.workspace_rule({ workspace = \"name:wardqa\", monitor = \"$OUTPUT\", default = true })
    hl.monitor({ output = \"$OUTPUT\", mode = \"1920x1080@60\", position = \"20000x0\", scale = 1 })
    if ward_qa_rule then ward_qa_rule:set_enabled(false) end
    ward_qa_rule = hl.window_rule({ name = \"ward-qa-xwayland\",
      match = { class = \"^org\\\\.freedesktop\\\\.Xwayland\$\", title = \"^Xwayland on :$NUM\" },
      workspace = \"name:wardqa silent\", no_initial_focus = true })" >/dev/null
  if [ -z "$(monitor_json)" ]; then
    hyprctl output create headless "$OUTPUT" >/dev/null
    for _ in $(seq 50); do [ -n "$(monitor_json)" ] && break; sleep .05; done
    restore_focus
  fi
  local m; m=$(monitor_json); [ -n "$m" ] || { echo "headless output $OUTPUT did not appear" >&2; exit 1; }
  jq -e '.width == 1920 and .height == 1080 and .x == 20000 and .scale == 1' <<<"$m" >/dev/null \
    || { echo "unexpected $OUTPUT geometry: $m" >&2; exit 1; }
  if ! xwayland_up; then
    [ -e /tmp/.X11-unix/X$NUM ] && { echo "display :$NUM is taken by something else" >&2; exit 1; }
    systemd-run --user --scope -q --collect --unit="$UNIT" -p MemoryMax=2G -p MemorySwapMax=256M \
      Xwayland ":$NUM" -geometry 1920x1080 -noreset -nolisten tcp >"$STATE/xwayland.log" 2>&1 &
    for _ in $(seq 100); do [ -S /tmp/.X11-unix/X$NUM ] && break; sleep .05; done
    for _ in $(seq 20); do restore_focus; sleep .05; done
  fi
  # Fullscreen it so the 1920x1080 root maps 1:1 onto the output (Xwayland's own -fullscreen left a 640x480 root, and
  # the window rule's fullscreen did not apply).
  local x; x=$(hyprctl clients -j | jq -r --arg t "Xwayland on :$NUM" '.[] | select(.title | startswith($t)) | select(.fullscreen == 0) | .address')
  if [ -n "$x" ]; then
    hyprctl dispatch "hl.dsp.window.fullscreen({ mode = \"fullscreen\", window = \"address:$x\" })" >/dev/null
    for _ in $(seq 10); do restore_focus; sleep .05; done
  fi
  status
}

down() {
  save_focus; trap end_focus EXIT
  systemctl --user stop "$UNIT.scope" 2>/dev/null || true
  if [ -n "$(monitor_json)" ]; then hyprctl output remove "$OUTPUT" >/dev/null; sleep .2; restore_focus; fi
  hyprctl eval 'if ward_qa_rule then ward_qa_rule:set_enabled(false); ward_qa_rule = nil end
    if ward_qa_ws then ward_qa_ws:set_enabled(false); ward_qa_ws = nil end' >/dev/null || true
  status
}

status() {
  echo "output:   $(monitor_json | jq -c '{name, width, height, x, y, scale, refreshRate, focused, ws: .activeWorkspace.name}' 2>/dev/null)"
  echo "xwayland: $(xwayland_up && echo ":$NUM up" || echo down)"
  hyprctl clients -j | jq -c '.[] | select(.title | startswith("Xwayland on")) |
    {address, title, workspace: .workspace.name, monitor, fullscreen, size}'
  echo "focus:    $(hyprctl activewindow -j | jq -r '.address // "none"') on $(hyprctl monitors -j | jq -r '.[] | select(.focused) | .name')"
}

case "${1:-status}" in up) up ;; down) down ;; status) status ;; *) echo "usage: $0 up|down|status" >&2; exit 2 ;; esac
