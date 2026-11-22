#!/usr/bin/env bash
# Repaint (gated), project, build and review for every generated colonist. Queues on the shared Blender slot.
set -uo pipefail
cd "$(dirname "$0")"; mkdir -p logs
ALL=${*:-linn brann ossa mira torr vex rell tamsin}
step() { ./make.sh "$@" > "logs/$1-$2.log" 2>&1; echo "$(date +%H:%M:%S) $1 $2 rc=$?"; }
for n in $ALL; do
  ( python3 meshy_run.py face "$n" > "logs/face-$n.log" 2>&1; echo "$(date +%H:%M:%S) face $n rc=$?" ) &
done; wait
for n in $ALL; do step project "$n"; step build "$n"; step review "$n"; done
echo BATCH DONE
