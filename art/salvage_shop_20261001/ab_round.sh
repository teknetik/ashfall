#!/usr/bin/env bash
# Second round after a cost fix: development build, the shop playthrough, then alternating frame-time walks.
# Usage: ab_round.sh <tag>
set -u
cd /home/teknetik/code/ao2
export DISPLAY=${DISPLAY:-:0} WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-wayland-1}
W=/home/teknetik/.local/state/ward-programme
E=$PWD/unity/evidence/salvage-shop/20261001/$1; mkdir -p $E
echo "== build $(date +%T)"; $W/build_player.sh $E/build-dev.log || exit 1
echo "== salvage shop $(date +%T)"; rm -rf $E/salvage
flock -w 5400 $W/unity.lock bash -c '. /home/teknetik/.local/state/ward-programme/lib.sh; run_capped native 10G 1G timeout 1500 uv run --offline --with python-xlib --with pillow python unity/tools/check_salvage_shop_native.py "$1"' _ $E/salvage > $E/salvage.out 2>&1; echo "rc=$?"; tail -1 $E/salvage.out
for i in 1 2; do
  echo "== walk final $i $(date +%T)"; rm -rf $E/walk-final-$i; $W/native.sh walk $E/walk-final-$i --exe $PWD/unity/AthenHill/Builds/final/AthenHill.x86_64 > $E/walk-final-$i.out 2>&1; echo "rc=$?"
  echo "== walk new $i $(date +%T)"; rm -rf $E/walk-new-$i; $W/native.sh walk $E/walk-new-$i > $E/walk-new-$i.out 2>&1; echo "rc=$?"
done
echo "== done $(date +%T)"
