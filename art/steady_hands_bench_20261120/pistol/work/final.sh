#!/usr/bin/env bash
# The 4096 bake into export/ (published build), the kit's checks, then the review renders (one job; each Blender call takes
# the slot on its own, so others get in between). Usage: SH/run.sh mp-final4k bash pistol/work/final.sh
SH=~/.local/state/ward-programme/steady-hands-20261120
D=/home/teknetik/code/ao2/art/steady_hands_bench_20261120
R=$D/pistol/review/surface
$SH/blender.sh $D/pistol/build.py -- --size 4096 --spp 12 2>&1 | grep -E "^\[pistol|OUTLINE|MODS|Error|Traceback|line [0-9]|gyro|textures|exported" | grep -v "^\[geo" | cut -c1-900
rc=${PIPESTATUS[0]}; echo "[final] build rc=$rc"; [ "$rc" = 0 ] || exit $rc
$SH/blender.sh $D/pistol/check.py 2>&1 | grep -E "^CHECK|^   |Error|Traceback|line [0-9]" | cut -c1-400
rc=${PIPESTATUS[0]}; echo "[final] check rc=$rc"; [ "$rc" = 0 ] || exit $rc
E=$D/pistol/export
$SH/blender.sh $D/pistol/prev.py -- --glb $E/pistol.glb --out $R --tag final_ --light warm,neutral --cams close,close_rear,bench,lie85 --samples 40 2>&1 | grep -E "PREV|Error|Traceback" | tail -3; echo "[final] prev1 rc=${PIPESTATUS[0]}"
$SH/blender.sh $D/pistol/prev.py -- --glb $E/pistol.glb --out $R --tag final_ --light warm --cams m_recv,m_grip,m_muzzle,m_right,m_butt --samples 40 2>&1 | grep -E "PREV|Error|Traceback" | tail -3; echo "[final] prev2 rc=${PIPESTATUS[0]}"
$SH/blender.sh $D/pistol/prev.py -- --glb $E/pistol_hand.glb --out $R --tag hand_ --light warm --cams close,close_rear --samples 32 2>&1 | grep -E "PREV|Error|Traceback" | tail -3; echo "[final] prev3 rc=${PIPESTATUS[0]}"
