#!/usr/bin/env bash
# Usage: SH/run.sh kit-cal bash kit/run_calibrate.sh
SH=~/.local/state/ward-programme/steady-hands-20261120
cd "$(dirname "$0")/.." || exit 2
$SH/blender.sh kit/calibrate_rig.py 2>&1 | grep -E "^CAL|Error|Traceback|line " ; exit ${PIPESTATUS[0]}
