#!/usr/bin/env bash
# Static dwell A/B (8 s frame timing at one camera, 13:00), alternating the previous final build and the new build.
set -u
cd /home/teknetik/code/ao2
export DISPLAY=${DISPLAY:-:0} WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-wayland-1}
W=/home/teknetik/.local/state/ward-programme
E=$PWD/unity/evidence/salvage-shop/20261001/${DWELL:-dwell}; mkdir -p $E
for cam in ${CAMS:-cam_hill cam_district_salvage}; do
  for i in 1 2; do
    for b in final new; do
      exe=$PWD/unity/AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64; [ $b = final ] && exe=$PWD/unity/AthenHill/Builds/final/AthenHill.x86_64
      o=$E/$cam-$b-$i; rm -rf $o
      $W/native.sh lookbook $o --cams $cam --hours 13 --profile 8 --exe $exe > $o.out 2>&1; echo "$cam $b $i rc=$?"
    done
  done
done
