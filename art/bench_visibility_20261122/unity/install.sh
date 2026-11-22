#!/usr/bin/env bash
# Small parts in sight, the bit change, the pin (22 Nov 2026).   install.sh install | verify | rollback
# install: the recipe and the instruction lines from their json, then the prefab's places and the pin shot. No scene write.
set -euo pipefail
R=$(cd "$(dirname "$0")/../../.." && pwd); H=$R/art/bench_visibility_20261122
W=~/.local/state/ward-programme; LOG=$R/unity/evidence/bench_visibility/20261122/logs; mkdir -p "$LOG"
cd "$R"; s=$(date +%H%M%S)
run() { "$W/unity.sh" "$LOG/$1-$s.log" "$2" -nographics --steps "$3"; }
case "${1:-}" in
install)
  python3 "$H/apply_data.py" --check
  run recipe AthenHill.Editor.AssemblyBenchInstall20261120.RunBatch recipe
  run lines AthenHill.Editor.BenchTutorInstall20261121.RunBatch lines
  run prefab AthenHill.Editor.BenchVisibilityPass20261122.RunBatch install,verify ;;
verify) run verify AthenHill.Editor.BenchVisibilityPass20261122.RunBatch verify ;;
rollback) run rollback AthenHill.Editor.BenchVisibilityPass20261122.RunBatch rollback
  echo "prefab restored; the code and json as they were are under $H/rollback" ;;
*) echo "install.sh install | verify | rollback"; exit 2 ;;
esac
