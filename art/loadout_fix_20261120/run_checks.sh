#!/usr/bin/env bash
# Loadout fix (20 Nov 2026): the loadout check and the three existing checks that touch the pack, loadout and hotbar,
# one after another through P2/native_check.sh. Usage: run_checks.sh BUILD TAG [checks...]
#   BUILD = p2-<name> (Builds/batch-BUILD), TAG = subfolder of unity/evidence/showcase_phase2/20261120/loadout_fix/
#   checks (default all): loadout inventory interface home
set -u
R=/home/teknetik/code/ao2; NC=/home/teknetik/.local/state/ward-programme/showcase-phase2-20261120/native_check.sh
B="$1"; TAG="$2"; shift 2; CHECKS="${*:-loadout inventory interface home}"
EXE=$R/unity/AthenHill/Builds/batch-$B/AthenHill.x86_64; [ -x "$EXE" ] || { echo "no build $EXE"; exit 2; }
Q=$R/unity/evidence/showcase_phase2/20261120/loadout_fix/$TAG; mkdir -p "$Q"; cd "$R"
say(){ echo "$(date +%H:%M:%S) $*" | tee -a "$Q/checks.log"; }
fresh(){ [ -e "$1" ] && mv "$1" "$1.old-$(date +%H%M%S)"; return 0; }
for c in $CHECKS; do
  case $c in
    loadout)   fresh "$Q/loadout";   $NC lf-$TAG-loadout unity/tools/capture_loadout_native.py ATHEN_EXE=$EXE ATHEN_OUT=$Q/loadout ;;
    inventory) fresh "$Q/inventory"; $NC lf-$TAG-inventory art/loadout_fix_20261120/run_inventory_redesign.py ATHEN_EXE=$EXE ATHEN_OUT=$Q/inventory ;;
    interface) fresh "$Q/interface"; $NC lf-$TAG-interface unity/tools/check_showcase_interface.py ATHEN_EXE=$EXE ATHEN_OUT=$Q/interface ;;
    home)      fresh "$Q/home";      $NC lf-$TAG-home unity/tools/check_home_journal_native.py ATHEN_EXE=$EXE ATHEN_OUT=$Q/home ;;
    *) say "unknown check $c"; continue ;;
  esac
  say "$c rc=$?"
done
say "done"
