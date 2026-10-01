#!/usr/bin/env bash
# City-view cost of the range: alternating on/off profiles of the existing Builds/tr-ab-on|off at cam_hill and
# cam_westgate_mouth (13:00), 8 s each. Usage: ab_city.sh
set -u
O=/home/teknetik/.local/state/ward-programme
E=/home/teknetik/code/ao2/unity/evidence/training-range/20261001
B=/home/teknetik/code/ao2/unity/AthenHill/Builds
for round in 1 2; do
  for st in on off; do for cam in cam_hill cam_westgate_mouth; do
    D=$E/ab/city-r$round-$st-$cam
    $O/native.sh lookbook $D --cams $cam --hours 13 --profile 8 --exe $B/tr-ab-$st/AthenHill.x86_64 > $D.out 2>&1; rc=$?
    if [ $rc -ne 0 ]; then echo "r$round $st $cam exit=$rc, retry"; rm -rf $D
      $O/native.sh lookbook $D --cams $cam --hours 13 --profile 8 --exe $B/tr-ab-$st/AthenHill.x86_64 > $D.out 2>&1; rc=$?; fi
    echo "r$round $st $cam exit=$rc"
  done; done
done
