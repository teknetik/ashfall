#!/usr/bin/env bash
# Rebake after the ledge-corner fix: 4096 bake into export/, pistol checks, the grip family's checks against it, two renders.
SH=~/.local/state/ward-programme/steady-hands-20261120
D=/home/teknetik/code/ao2/art/steady_hands_bench_20261120
R=$D/pistol/review/surface; E=$D/pistol/export
$SH/blender.sh $D/pistol/build.py -- --size 4096 --spp 12 2>&1 | grep -E "^\[pistol|OUTLINE|Error|Traceback|line [0-9]|gyro|textures|exported|not valid" | grep -v "^\[geo" | cut -c1-600
rc=${PIPESTATUS[0]}; echo "[final2] build rc=$rc"; [ "$rc" = 0 ] || exit $rc
$SH/blender.sh $D/pistol/check.py 2>&1 | grep -E "^CHECK|^   |Error|Traceback|line [0-9]" | cut -c1-400
rc=${PIPESTATUS[0]}; echo "[final2] check rc=$rc"; [ "$rc" = 0 ] || exit $rc
$SH/blender.sh $D/grip/check.py 2>&1 | grep -E "^CHECK|^   |Error|Traceback|line [0-9]" | cut -c1-400; echo "[final2] grip check rc=${PIPESTATUS[0]}"
$SH/blender.sh $D/pistol/prev.py -- --glb $E/pistol.glb --out $R --tag final_ --light warm --cams close,lie85,bench --samples 40 2>&1 | grep -E "PREV|Error|Traceback" | tail -2; echo "[final2] prev rc=${PIPESTATUS[0]}"
