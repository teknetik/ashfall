#!/usr/bin/env bash
# After the follow-ups: the rifle quest and Field Supply checks again with the harness parking the XTEST pointer at the
# window centre before camera commands (qa.centre_pointer, 5 Oct 2026).
set -u
R=/home/teknetik/code/ao2; W=/home/teknetik/.local/state/ward-programme; EV=$R/unity/evidence/ward-home/20261005/batch
EXE=$R/unity/AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64
export DISPLAY=:0 WAYLAND_DISPLAY=wayland-1
cd $R
until grep -q "followup-done" $EV/batch.log 2>/dev/null; do sleep 20; done
log(){ echo "$(date +%H:%M:%S) $*" >> $EV/batch.log; }
flock -w 5400 "$W/unity.lock" bash -c '. '"$W"'/lib.sh; run_capped native 10G 1G timeout 2400 env ATHEN_RIFLE_EVIDENCE="$1" ATHEN_EXE="$2" uv run --offline --with python-xlib --with pillow python unity/tools/check_rifle_quest.py' _ "$EV/quest2" "$EXE" > "$EV/quest2.out" 2>&1
log "quest2 rc=$? $(tail -1 "$EV/quest2.out" | cut -c1-160)"
flock -w 5400 "$W/unity.lock" bash -c '. '"$W"'/lib.sh; run_capped native 10G 1G timeout 1500 uv run --offline --with python-xlib --with pillow python unity/tools/check_field_supply_native.py "$1"' _ "$EV/fieldsupply2" > "$EV/fieldsupply2.out" 2>&1
log "fieldsupply2 rc=$? $(tail -1 "$EV/fieldsupply2.out")"
log followup2-done
