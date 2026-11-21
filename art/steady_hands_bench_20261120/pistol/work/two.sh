#!/usr/bin/env bash
# Two staged geometry builds in one slot use: without and with the kit's island alignment.
D=/home/teknetik/code/ao2/art/steady_hands_bench_20261120
for a in "--noalign" ""; do
  env -i HOME=$HOME PATH=/usr/bin:/bin blender -b --factory-startup --python-exit-code 1 -P $D/pistol/build.py -- --nobake --nomods $a --out $D/pistol/work/stage/pistol/export 2>&1 | grep "uv fill\|OUTLINE\|tris\|geo\.\|Error\|Traceback\|CONTRACT\|wrote parts\|crash" | cut -c1-600
  echo "[two] '$a' rc=${PIPESTATUS[0]}"
done
