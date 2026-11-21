#!/usr/bin/env bash
# Bisecting a crash at exit: several staged geometry builds in one slot use, each with other switches (PX_DIAG).
D=/home/teknetik/code/ao2/art/steady_hands_bench_20261120
if [ "$1" = open ]; then
  env -i HOME=$HOME PATH=/usr/bin:/bin blender -b --factory-startup --python-exit-code 1 -P $D/pistol/work/openclose.py -- $2 > $D/pistol/work/diag_open.txt 2>&1
  echo "[diag] open $2 rc=$? $(grep -c 'crash' $D/pistol/work/diag_open.txt) $(grep openclose $D/pistol/work/diag_open.txt)"
  shift 2
fi
i=0
for v in "$@"; do
  i=$((i+1))
  env -i HOME=$HOME PATH=/usr/bin:/bin PX_DIAG="$v" blender -b --factory-startup --python-exit-code 1 -P $D/pistol/build.py -- --nobake --nomods --out $D/pistol/work/diag_out > $D/pistol/work/diag_$i.txt 2>&1
  echo "[diag] $v rc=$? crash=$(grep -c 'crash' $D/pistol/work/diag_$i.txt) $(grep 'Error\|Traceback' $D/pistol/work/diag_$i.txt | tail -2)"
done
