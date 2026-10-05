#!/usr/bin/env bash
# Ward home pass, early native checks on the 03:28 build (before the home is installed): city loop, range tutorial and
# the hotbar/journal/lease part of check_home_journal_native.py (it stops at the first home landmark).
set -u
R=/home/teknetik/code/ao2; W=/home/teknetik/.local/state/ward-programme; EV=$R/unity/evidence/ward-home/20261005/early
export DISPLAY=:0 WAYLAND_DISPLAY=wayland-1
mkdir -p $EV; cd $R
log(){ echo "$(date +%H:%M:%S) $*" >> $EV/batch.log; }
log start
$W/native.sh cityloop "$EV/cityloop" > "$EV/cityloop.out" 2>&1; log "cityloop rc=$? $(grep -o 'CITY LOOP [A-Z]*' "$EV/cityloop.out" | tail -1)"
bash art/training_range_20261001/run/tutorial.sh "$EV/tutorial" > "$EV/tutorial.out" 2>&1; log "tutorial rc=$? $(tail -3 "$EV/tutorial.out" | tr '\n' ' ' | cut -c1-160)"
flock -w 5400 "$W/unity.lock" bash -c '. '"$W"'/lib.sh; run_capped native 10G 1G timeout 1500 uv run --offline --with python-xlib --with pillow python unity/tools/check_home_journal_native.py "$1"' _ "$EV/home" > "$EV/home.out" 2>&1; log "home rc=$? $(tail -2 "$EV/home.out" | tr '\n' ' ' | cut -c1-200)"
log done
