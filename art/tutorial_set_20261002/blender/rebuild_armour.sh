#!/usr/bin/env bash
# Re-export every armour piece on the current body tag (no body rebuild).
cd "$(dirname "$0")"
./blender_mpfb.sh fit_helmet.py 2>&1 | grep -E "EXPORT|Traceback|Error"
./blender_mpfb.sh fit_carrier.py -- 0.0 0.0 0.86 0.04 2>&1 | grep -E "EXPORT|Traceback|Error"
./blender_mpfb.sh fit_vest.py -- 0.0 0.0 0.86 0.0 2>&1 | grep -E "EXPORT|Traceback|Error"
for n in bracer kneeshin bootplates; do ./blender_mpfb.sh fit_limbs.py -- $n 2>&1 | grep -E "EXPORT|Traceback|Error"; done
./blender_mpfb.sh fit_gloves.py -- final 2>&1 | grep -E "EXPORT|Traceback|Error"
