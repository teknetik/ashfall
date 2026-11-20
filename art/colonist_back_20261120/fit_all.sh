#!/usr/bin/env bash
# Colonist back pass: re-fit the vest, plate carrier and helmet (fit -> pymeshlab decimate -> skin/export).
# Usage: fit_all.sh [pieces...]   Face targets in FACES below. Output: out/TS_*.glb
set -eu
cd /home/teknetik/code/ao2
P2=~/.local/state/ward-programme/showcase-phase2-20261120
declare -A FACES=([vest]=14000 [carrier]=9000 [helmet]=12000)
for p in "${@:-vest carrier helmet}"; do
  for q in $p; do
    $P2/blender.sh art/colonist_back_20261120/blender/fit_piece.py -- $q fit 2>&1 | grep -E "MERGED|FIT|TRIS|HEM|SNUG|PLATE|Error|Traceback" || true
    ~/.local/state/ward-programme/heavy.sh uv run --with pymeshlab python art/colonist_back_20261120/decimate.py $q ${FACES[$q]}
    $P2/blender.sh art/colonist_back_20261120/blender/fit_piece.py -- $q skin 2>&1 | grep -E "MERGED|UNWEIGHTED|EXPORT|PLATE|PAD|SHOULDER|Error|Traceback" || true
  done
done
