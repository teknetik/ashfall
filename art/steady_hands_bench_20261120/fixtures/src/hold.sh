#!/usr/bin/env bash
# model-bench: several Blender runs of the fixtures family in ONE hold of the Blender slot (the queue is long).
# Usage: SH/run.sh TAG bash fixtures/src/hold.sh "build args" "check" "review args" ...
#   each argument is one step: 'build <args>', 'check', 'review <args>', 'publish'
set -e
cd /home/teknetik/code/ao2/art/steady_hands_bench_20261120
B="env -i HOME=$HOME PATH=/usr/bin:/bin blender -b --factory-startup --python-exit-code 1 -P"
P=$PWD
steps=""
for a in "$@"; do
  case "$a" in
    build*) steps="$steps $B $P/fixtures/build.py -- ${a#build};" ;;
    check) steps="$steps $B $P/fixtures/check.py || echo CHECK_RC_NONZERO;" ;;
    review*) steps="$steps $B $P/fixtures/src/review_fx.py -- --family fixtures ${a#review};" ;;
  esac
done
echo "== HOLD: $steps"
/home/teknetik/.local/state/ward-programme/steady-hands-20261120/slot.sh bash -c "set -e; $steps"
echo "== HOLD DONE"
