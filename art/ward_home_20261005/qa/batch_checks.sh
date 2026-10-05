#!/usr/bin/env bash
# Ward home pass, combined native batch on the development build made after the home install: the home/journal/hotbar
# check, city loop, range tutorial, the rifle quest and Field Supply checks (both now on the new hotbar keys), then
# alternating A/B against the Field Supply build of 5 Oct 01:29 (Builds/batch-fs) at the standard views and the home.
set -u
R=/home/teknetik/code/ao2; W=/home/teknetik/.local/state/ward-programme; EV=$R/unity/evidence/ward-home/20261005/batch
EXE=$R/unity/AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64
export DISPLAY=:0 WAYLAND_DISPLAY=wayland-1
mkdir -p $EV; cd $R
log(){ echo "$(date +%H:%M:%S) $*" >> $EV/batch.log; }
run(){ # name timeout script [env...]
  local name=$1 t=$2 s=$3; shift 3
  flock -w 5400 "$W/unity.lock" bash -c '. '"$W"'/lib.sh; t=$1; s=$2; shift 2; run_capped native 10G 1G timeout $t env "$@" uv run --offline --with python-xlib --with pillow python $s' _ "$t" "$s" "$@" > "$EV/$name.out" 2>&1
}
log start
flock -w 5400 "$W/unity.lock" bash -c '. '"$W"'/lib.sh; run_capped native 10G 1G timeout 1800 uv run --offline --with python-xlib --with pillow python unity/tools/check_home_journal_native.py "$1"' _ "$EV/home" > "$EV/home.out" 2>&1
log "home rc=$? $(tail -1 "$EV/home.out")"
$W/native.sh cityloop "$EV/cityloop" > "$EV/cityloop.out" 2>&1; log "cityloop rc=$? $(grep -o 'CITY LOOP [A-Z]*' "$EV/cityloop.out" | tail -1)"
bash art/training_range_20261001/run/tutorial.sh "$EV/tutorial" > "$EV/tutorial.out" 2>&1; log "tutorial rc=$? $(tail -2 "$EV/tutorial.out" | tr '\n' ' ' | cut -c1-160)"
run quest 2400 unity/tools/check_rifle_quest.py ATHEN_RIFLE_EVIDENCE="$EV/quest" ATHEN_EXE="$EXE"; log "quest rc=$? $(tail -1 "$EV/quest.out" | cut -c1-160)"
flock -w 5400 "$W/unity.lock" bash -c '. '"$W"'/lib.sh; run_capped native 10G 1G timeout 1500 uv run --offline --with python-xlib --with pillow python unity/tools/check_field_supply_native.py "$1"' _ "$EV/fieldsupply" > "$EV/fieldsupply.out" 2>&1
log "fieldsupply rc=$? $(tail -1 "$EV/fieldsupply.out")"
$W/ab.sh "$EV/ab" "$R/unity/AthenHill/Builds/batch-fs/AthenHill.x86_64" "$EXE" 2 cam_hill,cam_avenue,cam_gate,cam_wb_home_south > "$EV/ab.out" 2>&1; log "ab rc=$?"
log done
