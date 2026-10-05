#!/usr/bin/env bash
# Re-runs after the QA harness fixes (compositor cursor parked outside the game window; pointer centred before camera
# commands): the real-mouse check, the home check, the rifle quest and Field Supply, on the same build.
set -u
R=/home/teknetik/code/ao2; W=/home/teknetik/.local/state/ward-programme; EV=$R/unity/evidence/ward-home/20261005/rerun
EXE=$R/unity/AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64
export DISPLAY=:0 WAYLAND_DISPLAY=wayland-1
mkdir -p $EV; cd $R
log(){ echo "$(date +%H:%M:%S) $*" >> $EV/rerun.log; }
log start
for name in mouselook home fieldsupply quest; do
  case $name in
    mouselook) s=unity/tools/check_mouse_look_native.py; env="";;
    home) s=unity/tools/check_home_journal_native.py; env="";;
    fieldsupply) s=unity/tools/check_field_supply_native.py; env="";;
    quest) s=unity/tools/check_rifle_quest.py; env="ATHEN_RIFLE_EVIDENCE=$EV/quest ATHEN_EXE=$EXE";;
  esac
  flock -w 5400 "$W/unity.lock" bash -c '. '"$W"'/lib.sh; s=$1; o=$2; shift 2; run_capped native 10G 1G timeout 2400 env "$@" uv run --offline --with python-xlib --with pillow python $s $o' _ "$s" "$([ $name = quest ] || echo $EV/$name)" $env > "$EV/$name.out" 2>&1
  log "$name rc=$? $(tail -1 "$EV/$name.out" | cut -c1-200)"
done
log done
