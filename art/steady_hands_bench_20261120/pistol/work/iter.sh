#!/usr/bin/env bash
# One use of the Blender slot for one look iteration: a staged build of the pistol, then preview renders.
# Usage (through the slot): SH/run.sh TAG SH/slot.sh pistol/work/iter.sh "<build args or ->" "<prev args>" ["<prev args>" ...]
# The build writes to pistol/work/stage/pistol/export (export/ stays as published). "-" skips the build.
set -u
D=/home/teknetik/code/ao2/art/steady_hands_bench_20261120
ST=$D/pistol/work/stage/pistol
BL="env -i HOME=$HOME PATH=/usr/bin:/bin blender -b --factory-startup --python-exit-code 1 -P"
mkdir -p "$ST/export" "$ST/review"
if [ "$1" != "-" ]; then
  $BL $D/pistol/build.py -- $1 --out $ST/export 2>&1 | grep -v "^Blender \|^Read \|^Fra:\|^Saved:\|^ Time:\|^$" | tail -n 60
  rc=${PIPESTATUS[0]}
  echo "[iter] build rc=$rc"
  [ "$rc" != 0 ] && exit "$rc"
fi
shift
for a in "$@"; do
  $BL $D/pistol/prev.py -- $a --out $ST/review 2>&1 | grep "PREV\|Error\|Traceback\|error\|  File \|Exception" | tail -n 20
  echo "[iter] prev rc=${PIPESTATUS[0]} ($a)"
done
