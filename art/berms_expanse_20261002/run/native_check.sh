#!/usr/bin/env bash
# Native Outer Berms expansion check (unity/tools/check_berms_expanse.py) on the current development build, under the
# shared Unity/player lock in a capped scope like native.sh. Usage: native_check.sh <OUT_DIR> [exe]
set -u; cd /home/teknetik/code/ao2
. /home/teknetik/.local/state/ward-programme/lib.sh; wait_for_user_player "berms expanse check"
flock -w 5400 /home/teknetik/.local/state/ward-programme/unity.lock bash -c '. /home/teknetik/.local/state/ward-programme/lib.sh; OUT=$1; EXE=$2; run_capped native 10G 1G timeout 1200 env ATHEN_EXPANSE_EVIDENCE="$OUT" ${EXE:+ATHEN_EXE="$EXE"} uv run --offline --with python-xlib --with pillow python unity/tools/check_berms_expanse.py' _ "$1" "${2:-}"
