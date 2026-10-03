#!/usr/bin/env bash
set -u; W=/home/teknetik/.local/state/ward-programme; R=/home/teknetik/code/ao2; OUT=$R/unity/evidence/overnight/20261003/bisect; cd "$R"
EXE=$R/unity/AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64
for cam in cam_hill cam_gate; do for v in no_npcs2 all2; do
  set_arg=""; [ $v = no_npcs2 ] && set_arg="WardNpc =0"
  d="$OUT/$v-$cam"; rm -rf "$d"
  $W/native.sh lookbook "$d" --cams $cam --hours 13 --profile 8 --exe "$EXE" --set "$set_arg" > "$d.out" 2>&1
  echo "$(date +%H:%M:%S) $v $cam rc=$? $(cat $d/set-active.json 2>/dev/null | tr -d '\n ')"
done; done
echo NPCBISECTDONE
