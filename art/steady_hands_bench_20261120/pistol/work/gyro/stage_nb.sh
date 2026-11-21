#!/usr/bin/env bash
# One slot use: staged --nobake build (with the gyro fits) and the kit checks on the staged export.
D=/home/teknetik/code/ao2/art/steady_hands_bench_20261120
BL="env -i HOME=$HOME PATH=/usr/bin:/bin blender -b --factory-startup --python-exit-code 1 -P"
$BL $D/pistol/build.py -- --nobake --nomods --out $D/pistol/work/stage/pistol/export 2>&1 | grep -E "^\[pistol|OUTLINE|Error|Traceback|line [0-9]|gyro" | grep -v "^\[geo" | cut -c1-700
echo "[nb] build rc=${PIPESTATUS[0]}"
$BL $D/pistol/work/check_stage.py 2>&1 | grep -E "^CHECK|^   |Error|Traceback|line [0-9]" | cut -c1-400
echo "[nb] check rc=${PIPESTATUS[0]}"
