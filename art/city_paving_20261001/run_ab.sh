#!/usr/bin/env bash
# Alternating A/B frame-time runs (8 s profile at 13:00) for the city paving pass: Builds/cp-ab-on vs cp-ab-off.
# Usage: run_ab.sh <round tag>   (writes unity/evidence/city-paving/20261001/ab/<cam>-<arm>-<tag>/)
set -u
O=/home/teknetik/.local/state/ward-programme; R=/home/teknetik/code/ao2; E=$R/unity/evidence/city-paving/20261001/ab
mkdir -p $E; tag=$1
for cam in cam_hill cam_pv_north_lane; do
  for arm in on off; do
    out=$E/$cam-$arm-$tag
    [ -e $out ] && continue
    $O/native.sh lookbook $out --cams $cam --hours 13 --profile 8 --exe $R/unity/AthenHill/Builds/cp-ab-$arm/AthenHill.x86_64 > $out.log 2>&1
    echo "$cam $arm $tag rc=$?"
  done
done
