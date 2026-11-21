#!/usr/bin/env bash
# One job: build (arguments pass through to build.py), then the checks. Usage: SH/run.sh mp-grip bash grip/run_build_check.sh --nobake
SH=~/.local/state/ward-programme/steady-hands-20261120
cd "$(dirname "$0")/.." || exit 2
$SH/blender.sh grip/build.py -- "$@" 2>&1 | grep -E "^\[grip|^\[geo|^\[ +[0-9.]+s\]|WARN|Error|Traceback|line |CONTRACT|FAILED" ; rc=${PIPESTATUS[0]}
echo "build rc=$rc"
[ "$rc" = 0 ] || exit $rc
$SH/blender.sh grip/check.py 2>&1 | grep -E "^CHECK|^   |Error|Traceback|line " ; rc=${PIPESTATUS[0]}
echo "check rc=$rc"; exit $rc
