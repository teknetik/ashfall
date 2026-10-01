#!/usr/bin/env bash
# Real-input West Gate checkpoint / range tutorial check (unity/tools/check_checkpoint.py) on the current development
# build, under the shared Unity/player lock in a capped scope exactly like native.sh. Usage: tutorial.sh <OUT_DIR>
set -u
cd /home/teknetik/code/ao2
flock -w 5400 "/home/teknetik/.local/state/ward-programme/unity.lock" bash -c '. /home/teknetik/.local/state/ward-programme/lib.sh; OUT=$1; run_capped native 10G 1G timeout 1800 env ATHEN_CHECKPOINT_EVIDENCE="$OUT" ATHEN_CHECKPOINT_RECORD=0 uv run --offline --with python-xlib --with pillow python unity/tools/check_checkpoint.py' _ "$1"
