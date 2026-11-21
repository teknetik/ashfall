#!/usr/bin/env bash
# One job: an unbaked build with the standard review set, then the fit renders with the servo's unit under the warm lamp.
# Usage: SH/run.sh mp-grip bash grip/run_review.sh [extra build args]
SH=~/.local/state/ward-programme/steady-hands-20261120
cd "$(dirname "$0")/.." || exit 2
$SH/blender.sh grip/build.py -- --nobake --review --samples 32 "$@" 2>&1 | grep -E "^\[grip|^\[geo|WARN|Error|Traceback|line |CONTRACT|FAILED" ; rc=${PIPESTATUS[0]}
echo "build rc=$rc"; [ "$rc" = 0 ] || exit $rc
$SH/blender.sh grip/render_fit.py -- --samples 36 --warm 2>&1 | grep -E "FIT|MISSING|Error|Traceback|line |no servo" ; rc=${PIPESTATUS[0]}
echo "fit rc=$rc"; exit $rc
