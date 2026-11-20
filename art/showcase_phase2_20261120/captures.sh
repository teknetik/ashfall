#!/usr/bin/env bash
# Showcase phase 2: the native review captures on one build, in priority order, one native job at a time.
# Usage: captures.sh BUILD TAG [steps...]   steps (default all): arms rifle lookbook residents
# Output: unity/evidence/showcase_phase2/20261120/qa/TAG/{arms,rifle_hands,lookbook-N,residents}
set -u; R=/home/teknetik/code/ao2; P2=/home/teknetik/.local/state/ward-programme/showcase-phase2-20261120; NC=$P2/native_check.sh
B="$1"; TAG="$2"; shift 2; STEPS="${*:-arms rifle lookbook residents}"
case "$B" in p2-*) ;; *) echo "phase 2 builds only"; exit 2 ;; esac
EXE=$R/unity/AthenHill/Builds/batch-$B/AthenHill.x86_64; [ -x "$EXE" ] || { echo "no build $EXE"; exit 2; }
Q=$R/unity/evidence/showcase_phase2/20261120/qa/$TAG; mkdir -p "$Q"; cd "$R"
say(){ echo "$(date +%H:%M:%S) $*" | tee -a "$Q/captures.log"; }
fresh(){ [ -e "$1" ] && mv "$1" "$1.old-$(date +%H%M%S)"; return 0; }
for step in $STEPS; do
  case $step in
    arms)      fresh "$Q/arms";        $NC $TAG-arms unity/tools/capture_character_arms_native.py ATHEN_EXE=$EXE ATHEN_OUT=$Q/arms; say "arms rc=$?" ;;
    rifle)     fresh "$Q/rifle_hands"; $NC $TAG-rifle-hands unity/tools/capture_rifle_hands_native.py ATHEN_EXE=$EXE ATHEN_OUT=$Q/rifle_hands; say "rifle rc=$?" ;;
    residents) fresh "$Q/residents";   $NC $TAG-residents unity/tools/capture_residents_native.py ATHEN_EXE=$EXE ATHEN_OUT=$Q/residents; say "residents rc=$?" ;;
    lookbook)  [ -f "$Q/cameras.txt" ] || { say "no $Q/cameras.txt"; continue; }
               art/showcase_phase2_20261120/lookbook_list.sh "$B" "$TAG" "$Q/cameras.txt" "${P2_HOURS:-13,20.5}" >> "$Q/captures.log" 2>&1; say "lookbook rc=$?" ;;
    *) say "unknown step $step" ;;
  esac
done
say "captures $B/$TAG done"
