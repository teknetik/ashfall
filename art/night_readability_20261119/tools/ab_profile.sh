#!/usr/bin/env bash
# Alternating A/B frame-time runs at 20:30: before (batch-showcase1) vs after (batch-nightfinal), two runs each, per camera.
set -u; R=/home/teknetik/code/ao2; cd $R; EV=$R/unity/evidence/night-readability/20261119/ab
mkdir -p $EV
B=$R/unity/AthenHill/Builds/batch-showcase1/AthenHill.x86_64; A=$R/unity/AthenHill/Builds/batch-nightfinal/AthenHill.x86_64
for run in 1 2; do for cam in cam_hill cam_avenue cam_gate; do for side in before after; do
  exe=$B; [ $side = after ] && exe=$A
  env -u WAYLAND_DISPLAY DISPLAY=:5 ATHEN_QA_MUTE=1 ~/.local/state/ward-programme/native.sh lookbook $EV/$side-$cam-r$run --cams $cam --hours 20.5 --profile 8 --exe $exe > $EV/$side-$cam-r$run.out 2>&1
  echo "$side $cam r$run rc=$?"
done; done; done
