#!/usr/bin/env bash
# Launch the current dev build, float it, run the real-key Tool Exchange traversal (no video), stop only that player. (t_e14abefb)
set -uo pipefail
TAG=$1
export DISPLAY=${DISPLAY:-:0}
T=/home/teknetik/code/ao2/unity/tools
E=/home/teknetik/code/ao2/unity/evidence/tool-exchange/20260929-light
cd "$T"
python3 launch_phase1_qa.py "$E/$TAG-native" > "$E/$TAG-launch.out" 2>&1
PID=$(cat "$E/$TAG-native/pid")
bash float_player_window.sh "$PID"
export ATHEN_NATIVE_DIR="$E/$TAG-native" ATHEN_NATIVE_PID="$PID"
uv run --offline --with python-xlib --with pillow python check_tool_exchange_traversal.py traversal > "$E/$TAG-traversal.out" 2>&1
echo traversal_exit $?
tail -c 700 "$E/$TAG-traversal.out"
grep -c -i "exception\|nullref" "$E/$TAG-native/Player.log"
kill "$PID"
