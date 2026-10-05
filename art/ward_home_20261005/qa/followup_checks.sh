#!/usr/bin/env bash
# After the combined batch: the home check again (pointer re-centred after every window) and the real-mouse check
# (uinput relative mouse) on the same build.
set -u
R=/home/teknetik/code/ao2; W=/home/teknetik/.local/state/ward-programme; EV=$R/unity/evidence/ward-home/20261005/batch
export DISPLAY=:0 WAYLAND_DISPLAY=wayland-1
cd $R
until grep -q " done$" $EV/batch.log 2>/dev/null; do sleep 20; done
log(){ echo "$(date +%H:%M:%S) $*" >> $EV/batch.log; }
for name in mouselook home2; do
  s=unity/tools/check_mouse_look_native.py; [ $name = home2 ] && s=unity/tools/check_home_journal_native.py
  flock -w 5400 "$W/unity.lock" bash -c '. '"$W"'/lib.sh; run_capped native 10G 1G timeout 1800 uv run --offline --with python-xlib --with pillow python "$1" "$2"' _ "$s" "$EV/$name" > "$EV/$name.out" 2>&1
  log "$name rc=$? $(tail -1 "$EV/$name.out")"
done
log followup-done
