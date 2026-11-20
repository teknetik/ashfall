#!/usr/bin/env bash
# Showcase phase 2, playtest fix round (20 Nov 2026): the native batch for Carl's six notes on one build.
# Usage: notes_batch.sh BUILD TAG     (e.g. notes_batch.sh p2-notes notes)
# Order: the checks for the six notes first (loadout and hotbar, gate barrels, Linn's voice), then the regression
# checks that touch the same code (city loop, range tutorial through the West Gate, rifle quest, Field Supply, NPC
# life, conversation camera). One native job at a time through native_check.sh.
set -u; R=/home/teknetik/code/ao2; P2=/home/teknetik/.local/state/ward-programme/showcase-phase2-20261120; NC=$P2/native_check.sh
B="$1"; TAG="$2"; case "$B" in p2-*) ;; *) echo "phase 2 builds only"; exit 2 ;; esac
EXE=$R/unity/AthenHill/Builds/batch-$B/AthenHill.x86_64; [ -x "$EXE" ] || { echo "no build $EXE"; exit 2; }
Q=$R/unity/evidence/showcase_phase2/20261120/qa/$TAG; mkdir -p "$Q"; cd "$R"
say(){ echo "$(date +%H:%M:%S) $*" | tee -a "$Q/batch.log"; }
fresh(){ [ -e "$1" ] && mv "$1" "$1.old-$(date +%H%M%S)"; return 0; }
say "notes batch $B/$TAG (tree $(git rev-parse --short HEAD), $(git status --short | wc -l) changed files)"
art/loadout_fix_20261120/run_checks.sh "$B" "$TAG" >> "$Q/batch.log" 2>&1; say "loadout checks rc=$?"
fresh "$Q/gate_barrels"; $NC $TAG-gate-barrels unity/tools/check_gate_barrels.py ATHEN_EXE=$EXE ATHEN_OUT=$Q/gate_barrels; say "gate barrels rc=$?"
if [ -f unity/tools/check_linn_voice_native.py ]; then
  fresh "$Q/linn_voice"; $NC $TAG-linn-voice unity/tools/check_linn_voice_native.py ATHEN_EXE=$EXE ATHEN_OUT=$Q/linn_voice; say "linn voice rc=$?"
else say "linn voice: no check script yet"; fi
fresh "$Q/npc_life";    $NC $TAG-npc-life unity/tools/check_showcase_npc_life.py ATHEN_EXE=$EXE ATHEN_OUT=$Q/npc_life; say "npc life rc=$?"
fresh "$Q/cityloop";    $NC $TAG-cityloop unity/evidence/hill/20260930/run_cityloop.py ATHEN_EXE=$EXE ATHEN_OUT=$Q/cityloop; say "cityloop rc=$?"
fresh "$Q/tutorial"; mkdir -p "$Q/tutorial"; $NC $TAG-tutorial unity/tools/check_checkpoint.py ATHEN_EXE=$EXE ATHEN_CHECKPOINT_EVIDENCE=$Q/tutorial ATHEN_CHECKPOINT_RECORD=0; say "tutorial rc=$?"
fresh "$Q/rifle";       $NC $TAG-rifle unity/tools/check_rifle_quest.py ATHEN_EXE=$EXE ATHEN_RIFLE_EVIDENCE=$Q/rifle; say "rifle rc=$?"
fresh "$Q/fieldsupply"; $NC $TAG-fieldsupply unity/tools/check_field_supply_native.py ATHEN_EXE=$EXE ATHEN_OUT=$Q/fieldsupply; say "fieldsupply rc=$?"
fresh "$Q/camera";      $NC $TAG-camera unity/tools/check_showcase_camera.py ATHEN_EXE=$EXE ATHEN_OUT=$Q/camera; say "camera rc=$?"
say "notes batch $B/$TAG done"
