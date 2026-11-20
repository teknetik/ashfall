#!/usr/bin/env bash
# Hero armour re-fit: rebuild pieces (fit -> pymeshlab decimate -> skin/export on the hero rig -> graft the current
# game material). Usage: fit_all.sh [helmet vest carrier arms legs boots gloves]   (default: all)
# Every Blender step goes through the shared single slot (CPU only); nothing here starts Unity.
# The defaults below are the constants the files in out/ were built with (README.md); *_ARGS override them.
set -eu
cd /home/teknetik/code/ao2; A=art/hero_base_20261120/armour
B=~/.local/state/ward-programme/showcase-phase2-20261120/blender.sh; HV=~/.local/state/ward-programme/heavy.sh
T=$A/ref_shipped   # the pieces as shipped for the old body (git HEAD copies; see blender/hlib.py)
F='ARMOUR|DECIMATE|GRAFT|Error|Traceback|File "|line [0-9]'
dec() { $HV uv run --with pymeshlab python $A/decimate.py $A/work/$1_fit.obj $A/work/$1_dec.obj $2 2>&1 | grep -E "$F" || true; }
bl() { $B "$@" 2>&1 | grep -E "$F" || true; }
graft() { python3 $A/graft.py $A/work/stage/$1 $T/$1 $A/out/$1; }
mkdir -p $A/work/stage $A/out
for p in ${@:-helmet vest carrier arms legs boots gloves}; do
  case $p in
    helmet)  bl $A/blender/fit_helmet.py -- fit ${HELMET_ARGS:-mult=1.04 dy=-0.006 dz=0.01}; dec helmet 12000; bl $A/blender/fit_helmet.py -- skin; graft TS_Helmet.glb ;;
    vest)    bl $A/blender/fit_torso.py -- vest fit ${VEST_ARGS:-mult=1.05}; dec vest 14000; bl $A/blender/fit_torso.py -- vest skin ${VEST_ARGS:-mult=1.05}; graft TS_FieldVest.glb ;;
    carrier) bl $A/blender/fit_torso.py -- carrier fit ${CARRIER_ARGS:-}; dec carrier 8990; bl $A/blender/fit_torso.py -- carrier skin ${CARRIER_ARGS:-}; graft TS_WardenCarrier.glb ;;
    arms)    bl $A/blender/fit_limbs.py -- bracer fit ${ARMS_ARGS:-}; dec bracer 3626; bl $A/blender/fit_limbs.py -- bracer skin ${ARMS_ARGS:-}; graft TS_ArmGuards.glb ;;
    legs)    bl $A/blender/fit_limbs.py -- kneeshin fit ${LEGS_ARGS:-}; dec kneeshin 4188; bl $A/blender/fit_limbs.py -- kneeshin skin ${LEGS_ARGS:-}; graft TS_LegArmour.glb ;;
    boots)   bl $A/blender/fit_limbs.py -- bootplates fit ${BOOTS_ARGS:-}; dec bootplates 3773; bl $A/blender/fit_limbs.py -- bootplates skin ${BOOTS_ARGS:-}; graft TS_Boots.glb ;;
    gloves)  bl $A/blender/fit_gloves.py -- ${GLOVES_ARGS:-}; graft TS_Gloves.glb ;;
  esac
done
