#!/usr/bin/env bash
# Showcase phase 2: before the final build, re-run the arms install (the residents were rebuilt after it), then every
# phase 2 pass's verify step on the saved scene, the Edit Mode suite, and the build. One Unity job at a time.
# Usage: final_sweep.sh BUILDNAME        (e.g. final -> Builds/batch-p2-final)
set -u; R=/home/teknetik/code/ao2; P2=/home/teknetik/.local/state/ward-programme/showcase-phase2-20261120; cd "$R"
N="$1"; E=AthenHill.Editor; fail=0
say(){ echo "$(date +%H:%M:%S) $*"; }
step(){ # name class steps
  $P2/seq.sh install "$1" "$E.$2.RunBatch" "$3"; rc=$?; say "sweep $1 ($3) rc=$rc"; [ $rc -ne 0 ] && fail=1
}
step sweep-arms       CharacterArmsPass20261120     install,verify
step sweep-residents  WardResidentsInstall20261120  verify
step sweep-light      LightBudgetPass20261120       verify
step sweep-colonist   ColonistBackPass20261120      verify
step sweep-berms      BermsVarietyPass20261120      verify
step sweep-rifle      RifleHandsPass20261120        verify
git status --short -- unity/AthenHill/ProjectSettings unity/AthenHill/Packages unity/AthenHill/Assets/Settings unity/AthenHill/Assets/Resources
$P2/seq.sh tests sweep; trc=$?; say "sweep tests rc=$trc"
# The Edit Mode run is known to drop a scripting define from ProjectSettings: put that one file back before building.
if ! git diff --quiet -- unity/AthenHill/ProjectSettings/ProjectSettings.asset; then
  git diff -- unity/AthenHill/ProjectSettings/ProjectSettings.asset | grep '^[+-] ' | head -4
  git checkout -- unity/AthenHill/ProjectSettings/ProjectSettings.asset; say "ProjectSettings.asset restored"
  $P2/seq.sh install sweep-settle "$E.LightBudgetPass20261120.RunBatch" verify; say "settle rc=$?"
fi
say "verify failures: $fail; tests rc=$trc"
$P2/build_to.sh "p2-$N"; say "build p2-$N rc=$?"
