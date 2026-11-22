#!/usr/bin/env bash
# The whole gate for this pass, one Unity job at a time: install, Edit Mode, sight and self-test.  gate.sh TAG
# It waits while any other Editor has the project (other agents start Unity outside the shared lock).
set -u
R=$(cd "$(dirname "$0")/../../.." && pwd); H=$R/art/bench_visibility_20261122; W=~/.local/state/ward-programme; S=$W/steady-hands-20261120
TAG=${1:?tag}; LOG=$R/unity/evidence/bench_visibility/20261122/logs; mkdir -p "$LOG"; cd "$R"
free_editor() {
  for _ in $(seq 1 240); do
    local busy=0 d
    for d in /proc/[0-9]*; do case "$(readlink "$d/exe" 2>/dev/null)" in */Editor/Unity) busy=1;; esac; done
    [ $busy = 0 ] && python3 unity/tools/compile_check.py >/dev/null 2>&1 && return 0
    sleep 5
  done
  echo "the Editor or the compile never came free"; return 1
}
free_editor || exit 90; "$H/unity/install.sh" install > "$LOG/gate-$TAG-install.out" 2>&1; echo "install rc=$?"
free_editor || exit 90; bash "$S/seq.sh" tests "$TAG"; echo "tests rc=$?"
cat "unity/evidence/steady_hands/20261120/editmode-$TAG.summary"
free_editor || exit 90; "$W/unity.sh" "$LOG/gate-$TAG-sight.log" AthenHill.Editor.AssemblyBenchInstall20261120.RunBatch -nographics --steps sight,selftest > /dev/null 2>&1; echo "sight,selftest rc=$?"
grep -h '^AssemblyBenchInstall20261120 \(sight\|selftest\):\|Exception:' "$LOG/gate-$TAG-sight.log" | cut -c1-1800
echo GATE DONE
