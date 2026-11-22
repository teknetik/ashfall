#!/usr/bin/env bash
# One Unity step while other writers share the checkout: waits until no Unity is running (some jobs skip the lock),
# gates on a clean compile, and records which settings files the step changed. guard.sh <command...>
set -u; R=$(cd "$(dirname "$0")/../../.." && pwd); cd "$R"
# Unity renames its main thread, so match the Editor by its executable (pgrep -x Unity misses a busy one)
unity_running() {
  local d
  for d in /proc/[0-9]*; do
    case "$(readlink "$d/exe" 2>/dev/null)" in */Editor/Unity) return 0 ;; esac
  done
  return 1
}
wait_clear() {
  local i ok=0
  for i in $(seq 1 135); do
    if ! unity_running && python3 unity/tools/compile_check.py >/dev/null 2>&1 \
       && ! unity_running; then return 0; fi
    sleep 4
  done
  echo "guard: Unity busy or tree not compiling"; return 1
}
P=unity/AthenHill/ProjectSettings/ProjectSettings.asset; before=$(mktemp); cp "$P" "$before"
for attempt in 1 2 3 4; do
  wait_clear || exit 90
  t0=$(date +%s); "$@"; rc=$?
  # a quick failure with another Unity alive is a collision with a job that skips the lock: wait and go again
  if [ $rc -ne 0 ] && [ $(( $(date +%s) - t0 )) -lt 25 ] && unity_running; then
    echo "guard: collided (attempt $attempt)"; sleep 5; continue
  fi
  break
done
if ! cmp -s "$before" "$P"; then
  # Only the define Unity drops on every batch run is put back; anything else is reported, never overwritten.
  other=$(diff "$before" "$P" | grep '^[<>]' | grep -v 'SENTIS_ANALYTICS_ENABLED\|^> *Standalone: ' )
  if [ -z "$other" ]; then cp "$before" "$P"; echo "guard: restored the dropped define in ProjectSettings"; else echo "guard: ProjectSettings changed:"; echo "$other"; fi
fi
rm -f "$before"; echo "guard: rc=$rc"; exit $rc
