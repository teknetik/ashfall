#!/usr/bin/env bash
# Showcase phase 2, playtest fix round: verify the three fix passes and the six phase 2 passes on the saved scene,
# build p2-NAME, then run the notes batch on it. One Unity or native job at a time.
# Usage: notes_chain.sh NAME TAG      (e.g. notes_chain.sh notes notes -> Builds/batch-p2-notes, qa/notes)
set -u; R=/home/teknetik/code/ao2; P2=/home/teknetik/.local/state/ward-programme/showcase-phase2-20261120; cd "$R"
N="$1"; TAG="$2"; E=AthenHill.Editor; fail=0
say(){ echo "$(date +%H:%M:%S) $*"; }
step(){ $P2/seq.sh install "$1" "$E.$2.RunBatch" verify; rc=$?; say "verify $1 rc=$rc"; [ $rc -ne 0 ] && fail=1; }
step notes-loadout   LoadoutFixPass20261120
step notes-barrels   GateBarrelsPass20261120
step notes-linn      LinnVoicePass20261120
step notes-arms      CharacterArmsPass20261120
step notes-residents WardResidentsInstall20261120
step notes-light     LightBudgetPass20261120
step notes-colonist  ColonistBackPass20261120
step notes-berms     BermsVarietyPass20261120
step notes-rifle     RifleHandsPass20261120
git status --short -- unity/AthenHill/ProjectSettings unity/AthenHill/Packages unity/AthenHill/Assets/Settings unity/AthenHill/Assets/Resources
say "verify failures: $fail"
$P2/build_to.sh "p2-$N"; brc=$?; say "build p2-$N rc=$brc"
[ $brc -eq 0 ] || exit 1
art/showcase_phase2_20261120/notes_batch.sh "p2-$N" "$TAG"
say "chain done"
