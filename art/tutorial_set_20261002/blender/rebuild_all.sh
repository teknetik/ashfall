#!/usr/bin/env bash
# Full tutorial-set rebuild on the current body tag (fitlib.BODY_TAG): finish body, then every armour piece.
cd "$(dirname "$0")"; set -e
T=$(grep "^BODY_TAG" fitlib.py | cut -d"'" -f2)
./blender_mpfb.sh finish_body.py -- $T | grep -E "CHAR|CLIP|Traceback|Error" || true
./blender_mpfb.sh fit_helmet.py | grep -E "HELMET|Traceback|Error" || true
./blender_mpfb.sh fit_carrier.py -- 0.0 0.0 0.86 0.04 | grep -E "^FIT|^PEN|Traceback|Error" || true
./blender_mpfb.sh fit_vest.py -- 0.0 0.0 0.86 0.0 | grep -E "^FIT|^PEN|Traceback|Error" || true
for n in bracer kneeshin bootplates; do ./blender_mpfb.sh fit_limbs.py -- $n | grep -E "^FIT|^PEN|Traceback|Error" || true; done
./blender_mpfb.sh fit_gloves.py -- final | grep -E "SHELL|Traceback|Error" || true
ls -la out/
