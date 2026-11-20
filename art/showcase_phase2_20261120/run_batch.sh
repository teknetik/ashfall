#!/usr/bin/env bash
# Showcase phase 2: the combined native batch on one private build copy. One native job at a time through
# native_check.sh (Unity lock, memory cap, private display :5, waits while Carl's own game is running).
# Usage: run_batch.sh BUILD TAG [steps...]      BUILD = p2-<name> (Builds/batch-BUILD), TAG = evidence subfolder
# Steps (default: all, in this order):
#   regression   city loop, range tutorial, rifle quest, home/journal, Field Supply, Berms expansion, gunners, enemies
#   packages     the phase 1 package checks plus the light budget check (when it exists)
#   lookbook     every phase 2 review camera (cam_lb_, cam_cb_, cam_bv_, cam_res_, cam_rh_) at 13:00 and 20:30
#   ab           check_showcase_ab.py against Builds/batch-playtest1119 (read-only)
# Bring the display up first: unity/tools/qa_display.sh up. Results: unity/evidence/showcase_phase2/20261120/qa/TAG.
set -u
R=/home/teknetik/code/ao2; P2=/home/teknetik/.local/state/ward-programme/showcase-phase2-20261120; NC=$P2/native_check.sh
B="$1"; TAG="$2"; shift 2; STEPS="${*:-regression packages lookbook ab}"
case "$B" in p2-*) ;; *) echo "build must be a phase 2 build (p2-*)"; exit 2 ;; esac
EXE=$R/unity/AthenHill/Builds/batch-$B/AthenHill.x86_64; [ -x "$EXE" ] || { echo "no build $EXE"; exit 2; }
BASE=$R/unity/AthenHill/Builds/batch-playtest1119/AthenHill.x86_64
Q=$R/unity/evidence/showcase_phase2/20261120/qa/$TAG; mkdir -p "$Q"; cd "$R"
say(){ echo "$(date +%H:%M:%S) $*" | tee -a "$Q/batch.log"; }
fresh(){ [ -e "$1" ] && mv "$1" "$1.old-$(date +%H%M%S)"; return 0; }   # keep earlier runs, never delete evidence
say "batch $B/$TAG steps: $STEPS (tree $(git rev-parse --short HEAD), $(git status --short | wc -l) changed files)"
for step in $STEPS; do
  case $step in
    regression)
      fresh "$Q/cityloop";    $NC $TAG-cityloop unity/evidence/hill/20260930/run_cityloop.py ATHEN_EXE=$EXE ATHEN_OUT=$Q/cityloop; say "cityloop rc=$?"
      fresh "$Q/tutorial"; mkdir -p "$Q/tutorial"; $NC $TAG-tutorial unity/tools/check_checkpoint.py ATHEN_EXE=$EXE ATHEN_CHECKPOINT_EVIDENCE=$Q/tutorial ATHEN_CHECKPOINT_RECORD=0; say "tutorial rc=$?"
      fresh "$Q/rifle";       $NC $TAG-rifle unity/tools/check_rifle_quest.py ATHEN_EXE=$EXE ATHEN_RIFLE_EVIDENCE=$Q/rifle; say "rifle rc=$?"
      fresh "$Q/home";        $NC $TAG-home unity/tools/check_home_journal_native.py ATHEN_EXE=$EXE ATHEN_OUT=$Q/home; say "home rc=$?"
      fresh "$Q/fieldsupply"; $NC $TAG-fieldsupply unity/tools/check_field_supply_native.py ATHEN_EXE=$EXE ATHEN_OUT=$Q/fieldsupply; say "fieldsupply rc=$?"
      fresh "$Q/expanse"; mkdir -p "$Q/expanse"; $NC $TAG-expanse unity/tools/check_berms_expanse.py ATHEN_EXE=$EXE ATHEN_EXPANSE_EVIDENCE=$Q/expanse; say "expanse rc=$?"
      fresh "$Q/gunners";     $NC $TAG-gunners unity/tools/check_gunner_separation.py ATHEN_EXE=$EXE ATHEN_GUNNER_EVIDENCE=$Q/gunners; say "gunners rc=$?"
      fresh "$Q/enemies";     $NC $TAG-enemies unity/tools/check_next_level_enemies.py ATHEN_EXE=$EXE ATHEN_NEXTLEVEL_EVIDENCE=$Q/enemies; say "enemies rc=$?"
      ;;
    packages)
      for c in combat_feel combat_audio npc_life camera interface world_map weather gate_names light_budget; do
        [ -f unity/tools/check_showcase_$c.py ] || { say "package $c: no check script, skipped"; continue; }
        fresh "$Q/$c"; $NC $TAG-pkg-$c unity/tools/check_showcase_$c.py ATHEN_EXE=$EXE ATHEN_OUT=$Q/$c; say "package $c rc=$?"
      done ;;
    lookbook)
      # Review cameras are read from the saved scene by name; eight cameras per player run.
      grep -oE 'm_Name: cam_(lb|cb|bv|res|rh)_[A-Za-z0-9_]+' unity/AthenHill/Assets/AthenHill/Scenes/AthenHill.unity | sed 's/m_Name: //' | sort -u > "$Q/cameras.txt"
      say "lookbook: $(wc -l < "$Q/cameras.txt") cameras"
      n=0; split -l 8 -d "$Q/cameras.txt" "$Q/cams-part-"
      for part in "$Q"/cams-part-*; do
        n=$((n+1)); fresh "$Q/lookbook-$n"
        $NC $TAG-lookbook-$n art/showcase_phase2_20261120/run_lookbook.py ATHEN_EXE=$EXE P2_OUT=$Q/lookbook-$n P2_CAMS=$(paste -sd, "$part") P2_HOURS=${P2_HOURS:-13,20.5}; say "lookbook part $n rc=$?"
      done ;;
    ab)
      fresh "$Q/ab"; $NC $TAG-ab unity/tools/check_showcase_ab.py ATHEN_BASE_EXE=$BASE ATHEN_EXE=$EXE ATHEN_OUT=$Q/ab AB_ROUNDS=${AB_ROUNDS:-3}; say "ab rc=$?" ;;
    *) say "unknown step $step" ;;
  esac
done
say "batch $B/$TAG done"
