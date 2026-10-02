#!/usr/bin/env bash
# Combined native test for the walk-in Salvage shop (1 Oct 2026): development build, the shop/quest playthrough, the city
# loop, the range tutorial check and alternating frame-time walks against the previous batch's final build.
set -u
cd /home/teknetik/code/ao2
export DISPLAY=${DISPLAY:-:0} WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-wayland-1}
W=/home/teknetik/.local/state/ward-programme
E=$PWD/unity/evidence/salvage-shop/20261001/combined
mkdir -p $E
run_native() { flock -w 5400 $W/unity.lock bash -c '. /home/teknetik/.local/state/ward-programme/lib.sh; T=$1; shift; run_capped native 10G 1G timeout $T "$@"' _ "$@"; }
echo "== build $(date +%T)"; $W/build_player.sh $E/build-dev.log || exit 1
echo "== salvage shop $(date +%T)"; rm -rf $E/salvage; run_native 1500 uv run --offline --with python-xlib --with pillow python unity/tools/check_salvage_shop_native.py $E/salvage > $E/salvage.out 2>&1; echo "rc=$?"; tail -3 $E/salvage.out
echo "== city loop $(date +%T)"; rm -rf $E/cityloop; $W/native.sh cityloop $E/cityloop > $E/cityloop.out 2>&1; echo "rc=$?"; tail -3 $E/cityloop.out
echo "== range tutorial $(date +%T)"; rm -rf $E/tutorial; bash art/training_range_20261001/run/tutorial.sh $E/tutorial > $E/tutorial.out 2>&1; echo "rc=$?"; tail -3 $E/tutorial.out; python3 -c "import json;r=json.load(open('$E/tutorial/report.json'));print('tutorial passed',r.get('passed'),len(r.get('checks',[])))" 2>/dev/null
for i in 1 2; do
  echo "== walk final $i $(date +%T)"; rm -rf $E/walk-final-$i; $W/native.sh walk $E/walk-final-$i --exe $PWD/unity/AthenHill/Builds/final/AthenHill.x86_64 > $E/walk-final-$i.out 2>&1; echo "rc=$?"
  echo "== walk new $i $(date +%T)"; rm -rf $E/walk-new-$i; $W/native.sh walk $E/walk-new-$i > $E/walk-new-$i.out 2>&1; echo "rc=$?"
done
echo "== done $(date +%T)"
