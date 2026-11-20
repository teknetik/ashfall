#!/usr/bin/env bash
# Hero base (20 Nov 2026): the Unity install, one Unity job per step on the shared lock (-nographics throughout).
# Usage: install.sh <step> [step...]     steps, in order:
#   code       apply.py (pass file + guards) and the compile check
#   rh-rollback  RifleHandsPass20261120 rollback (must precede MainCharacterInstall: unity/EDITING.md)
#   files      HeroBasePass20261120 files: colonist.glb, TS_*.glb, Source/Player/*.glb (previous files kept for rollback)
#   main       MainCharacterInstall.InstallBatch: prefab, height, clips, grips, weapons, armour, view models
#   check      MainCharacterInstall.CheckBatch
#   arms       CharacterArmsPass20261120 install,verify (the corrector lives on the visual the install just replaced)
#   rh         RifleHandsPass20261120 install
#   rh-base    RifleHandsPass20261120 rebaseline,verify (the reference values belong to the previous body)
#   verify     HeroBasePass20261120 cameras,verify
#   tests      Edit Mode tests (tag hero)
#   all        code rh-rollback files main check arms rh rh-base verify
#   rollback   HeroBasePass20261120 restore, then main arms rh (rebuilds the previous body from the kept files)
# Each step stops the script on failure. Logs: unity/evidence/hero_base/20261120/ and (seq.sh steps)
# unity/evidence/showcase_phase2/20261120/install-hero-*.log.
set -u; W=/home/teknetik/.local/state/ward-programme; S=$W/showcase-phase2-20261120; R=/home/teknetik/code/ao2
EV=$R/unity/evidence/hero_base/20261120; mkdir -p "$EV"; cd "$R"
say(){ echo "$(date +%H:%M:%S) hero: $*" | tee -a "$EV/install.log"; }
seq(){ "$S/seq.sh" install "$1" "AthenHill.Editor.$2.RunBatch" "$3"; }
tailres(){ for f in "$@"; do [ -f "$f" ] && { echo "--- $f"; tail -c 1500 "$f"; echo; }; done; }
run(){
  case "$1" in
    code) python3 art/hero_base_20261120/unity/apply.py && python3 unity/tools/compile_check.py ;;
    rh-rollback) seq hero-rh-rollback RifleHandsPass20261120 rollback ;;
    files) seq hero-files HeroBasePass20261120 files; rc=$?; tailres "$EV/files-result.txt"; return $rc ;;
    files-placeholder) "$S/seq.sh" install hero-files-ph AthenHill.Editor.HeroBasePass20261120.RunBatch files --armour placeholder; rc=$?; tailres "$EV/files-result.txt"; return $rc ;;
    main) "$W/unity.sh" "$EV/install-main.log" AthenHill.Editor.MainCharacterInstall.InstallBatch -nographics; rc=$?
          tailres "$R/unity/evidence/next-level/20261002/character/install-log.txt"; return $rc ;;
    check) "$W/unity.sh" "$EV/check-main.log" AthenHill.Editor.MainCharacterInstall.CheckBatch -nographics; rc=$?
          tailres "$R/unity/evidence/next-level/20261002/character/check-log.txt"; return $rc ;;
    arms) seq hero-arms CharacterArmsPass20261120 install,verify ;;
    rh) seq hero-rh RifleHandsPass20261120 install ;;
    rh-base) seq hero-rh-base RifleHandsPass20261120 rebaseline,verify ;;
    verify) seq hero-verify HeroBasePass20261120 cameras,verify; rc=$?; tailres "$EV/cameras_verify-result.txt"; return $rc ;;
    tests) "$S/seq.sh" tests hero ;;
    restore) seq hero-restore HeroBasePass20261120 restore ;;
    *) echo "unknown step $1"; return 2 ;;
  esac
}
steps=("$@")
[ "${1:-}" = all ] && steps=(code rh-rollback files main check arms rh rh-base verify)
[ "${1:-}" = rollback ] && steps=(rh-rollback restore main arms rh rh-base)
for s in "${steps[@]}"; do
  say "step $s start"; run "$s"; rc=$?; say "step $s rc=$rc"
  [ $rc -ne 0 ] && { say "STOPPED at $s"; exit $rc; }
done
say "done: ${steps[*]}"
