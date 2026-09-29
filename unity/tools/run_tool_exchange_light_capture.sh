#!/usr/bin/env bash
# Launch a native player for a tag, float it, run the Tool Exchange light capture, stop only that player. (t_e14abefb)
# Usage: run_tool_exchange_light_capture.sh <tag> [player-exe]
set -uo pipefail
TAG=$1
export DISPLAY=${DISPLAY:-:0}
[ -n "${2:-}" ] && export ATHEN_PLAYER_EXE=$2
T=/home/teknetik/code/ao2/unity/tools
E=/home/teknetik/code/ao2/unity/evidence/tool-exchange/20260929-light
cd "$T"
python3 launch_phase1_qa.py "$E/$TAG-native" > "$E/$TAG-launch.out" 2>&1
PID=$(cat "$E/$TAG-native/pid")
bash float_player_window.sh "$PID"
export ATHEN_NATIVE_DIR="$E/$TAG-native" ATHEN_NATIVE_PID="$PID"
uv run --offline --with python-xlib --with pillow python capture_tool_exchange_light.py > "$E/$TAG-capture.out" 2>&1
echo capture_exit $?
tail -3 "$E/$TAG-capture.out"
kill "$PID"
uptime
