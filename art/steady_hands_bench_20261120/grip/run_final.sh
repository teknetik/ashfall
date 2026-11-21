#!/usr/bin/env bash
# One job: baked build, checks, then the pictures: the GLB under the warm lamp (clean set, then the as-found set), the
# fit renders with the servo's unit, and the six views of the GLB under the neutral rig.
# Usage: SH/run.sh mp-grip4 bash grip/run_final.sh [--size 2048 --spp 24]
SH=~/.local/state/ward-programme/steady-hands-20261120
cd "$(dirname "$0")/.." || exit 2
$SH/blender.sh grip/build.py -- "$@" 2>&1 | grep -E "^\[grip|^\[geo|^\[ +[0-9.]+s\] (textures|exported)|WARN|Error|Traceback|line |CONTRACT|FAILED" ; rc=${PIPESTATUS[0]}
echo "build rc=$rc"; [ "$rc" = 0 ] || exit $rc
$SH/blender.sh grip/check.py 2>&1 | grep -E "^CHECK|^   |Error|Traceback|line " ; rc=${PIPESTATUS[0]}
echo "check rc=$rc"; [ "$rc" = 0 ] || exit $rc
$SH/blender.sh kit/review.py -- --family grip --glb --only close --warm --samples 36 2>&1 | grep -E "^REVIEW|Error|Traceback|line " | cut -c1-120 ; echo "glb warm rc=${PIPESTATUS[0]}"
$SH/blender.sh grip/render_asfound.py -- --samples 36 --warm 2>&1 | grep -E "ASFOUND|Error|Traceback|line " ; echo "asfound rc=${PIPESTATUS[0]}"
$SH/blender.sh grip/render_fit.py -- --samples 36 --warm 2>&1 | grep -E "FIT|MISSING|Error|Traceback|line |no servo" ; echo "fit rc=${PIPESTATUS[0]}"
$SH/blender.sh kit/review.py -- --family grip --glb --only six --samples 32 2>&1 | grep -E "^REVIEW|Error|Traceback|line " | cut -c1-120 ; echo "glb six rc=${PIPESTATUS[0]}"
