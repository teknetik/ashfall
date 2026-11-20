#!/usr/bin/env bash
# Final review renders (CPU Cycles through the shared Blender slot) and the two contact sheets.
# Usage: review_final.sh [closeups] [kit] [motion]     (default: all)
set -eu
cd /home/teknetik/code/ao2; A=art/hero_base_20261120/armour
B=~/.local/state/ward-programme/showcase-phase2-20261120/blender.sh; R=$A/blender/review.py
F='REVIEW|Error|Traceback|File "|line [0-9]'
KIT=helmet,vest,arms,gloves,legs,boots; KITC=helmet,carrier,arms,gloves,legs,boots
for step in ${@:-closeups kit motion}; do
  case $step in
    closeups)   # every piece from front, back, both sides and three-quarter, in the neutral (in-game shoulder) pose
      $B $R -- final_closeups pieces=$KIT pose=neutral views=front,back,left,right,q_fl focus=helmet+vest+arms_R+gloves_R+legs_R+boots_R res=520x520 2>&1 | grep -E "$F" || true
      $B $R -- final_carrier pieces=$KITC pose=neutral+rest+idle:0+walk:75 views=front,back,left,right,q_fl,q_br focus=bone:Spine01:0.78 res=520x520 2>&1 | grep -E "$F" || true ;;
    kit)        # all pieces on the body: neutral pose with the vest, neutral pose with the carrier, rest (A-pose) with the vest
      $B $R -- final_kit_vest pieces=$KIT pose=neutral views=front,back,left,right,q_fl focus=body res=620x860 2>&1 | grep -E "$F" || true
      $B $R -- final_kit_carrier pieces=$KITC pose=neutral views=front,back,left,right,q_fl focus=body res=620x860 2>&1 | grep -E "$F" || true
      $B $R -- final_kit_rest pieces=$KIT pose=rest views=front,back,left,right,q_fl focus=body res=620x860 2>&1 | grep -E "$F" || true
      uv run --with pillow python $A/stack.py $A/renders/sheet_kit.jpg 2400 $A/renders/final_kit_vest.jpg $A/renders/final_kit_carrier.jpg $A/renders/final_kit_rest.jpg ;;
    motion)     # walk and run from the front and from behind, the two hand-set poses, the rifle-hold clip
      $B $R -- final_motion pieces=$KIT "pose=walk:25+walk:75+run:25+run:75+rifle+kneel+clip:rifle_573:50" views=front,back,left focus=body res=520x700 2>&1 | grep -E "$F" || true
      uv run --with pillow python $A/stack.py $A/renders/sheet_motion.jpg 2400 --grid 7 3 --regroup 4 $A/renders/final_motion.jpg ;;
  esac
done
