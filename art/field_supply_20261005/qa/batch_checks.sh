#!/usr/bin/env bash
# Field Supply batch checks on the 5 Oct development build: city loop, range tutorial, alternating A/B against the
# turret-bench build of 4 Oct (Builds/batch-tb) at the standard views plus the night-facade view of Field Supply.
set -u
R=/home/teknetik/code/ao2; W=/home/teknetik/.local/state/ward-programme; EV=$R/unity/evidence/field-supply/20261005
export DISPLAY=:0 WAYLAND_DISPLAY=wayland-1
cd $R
log(){ echo "$(date +%H:%M:%S) $*" >> $EV/batch.log; }
log start
$W/native.sh cityloop "$EV/cityloop" > "$EV/cityloop.out" 2>&1; log "cityloop rc=$? $(grep -o 'CITY LOOP [A-Z]*' "$EV/cityloop.out" | tail -1)"
bash art/training_range_20261001/run/tutorial.sh "$EV/tutorial" > "$EV/tutorial.out" 2>&1; log "tutorial rc=$? $(tail -3 "$EV/tutorial.out" | tr '\n' ' ' | cut -c1-160)"
$W/ab.sh "$EV/ab" "$R/unity/AthenHill/Builds/batch-tb/AthenHill.x86_64" "$R/unity/AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64" 2 cam_hill,cam_avenue,cam_gate,cam_nf_field_supply > "$EV/ab.out" 2>&1; log "ab rc=$?"
log done
