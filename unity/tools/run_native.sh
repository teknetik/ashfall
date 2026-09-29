#!/usr/bin/env bash
# Usage: run_native.sh <native-dir> <script.py> [args...]   (runs a unity/tools script against a launched QA player)
set -euo pipefail
export DISPLAY=:0 XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-1
dir=$1; shift
script=$1; shift
export ATHEN_NATIVE_DIR=$dir
ATHEN_NATIVE_PID=$(cat "$dir/pid")
export ATHEN_NATIVE_PID
cd /home/teknetik/code/ao2/unity/tools
exec uv run --offline --with python-xlib --with pillow python "$script" "$@"
