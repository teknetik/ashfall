#!/usr/bin/env bash
SH=~/.local/state/ward-programme/steady-hands-20261120
cd "$(dirname "$0")/../.." || exit 2
$SH/blender.sh grip/build.py -- --size 2048 --spp 24 2>&1 | grep -E "^\[grip +[0-9.]+s\] (built|uv|parts|solid grip_core)|Error|Traceback|line [0-9]|CONTRACT|FAILED|not a closed" ; rc=${PIPESTATUS[0]}
echo "build rc=$rc"; [ "$rc" = 0 ] || exit $rc
$SH/blender.sh grip/check.py 2>&1 | grep -E "^CHECK|^   |Error|Traceback|line [0-9]" ; rc=${PIPESTATUS[0]}
echo "check rc=$rc"; [ "$rc" = 0 ] || exit $rc
$SH/blender.sh kit/review.py -- --family grip --glb --only close --warm --samples 36 2>&1 | grep -E "^REVIEW|Error|Traceback" | cut -c1-120 ; echo "glb warm rc=${PIPESTATUS[0]}"
