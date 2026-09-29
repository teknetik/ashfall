#!/usr/bin/env bash
# Usage: relaunch_qa.sh <NEW-evidence-dir> <left|right>
# Compatibility name only: exactly ONE owned launch + smoke, never a relaunch.
set -euo pipefail
if [[ $# != 2 || ( $2 != left && $2 != right ) ]]; then
    printf 'Usage: %s <NEW-evidence-dir> <left|right>\n' "$0" >&2
    exit 2
fi
export DISPLAY=${DISPLAY:-:0}
export XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-/run/user/$(id -u)}
export WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-wayland-1}
tools=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec uv run --offline --with python-xlib --with pillow python "$tools/launch_phase1_qa.py" "$1" --smoke-leg "$2"
