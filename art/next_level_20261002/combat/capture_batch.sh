#!/usr/bin/env bash
# Graphics editor capture of the rifle review cameras with the muzzle marker (one Unity job, <= 6 cameras), after the
# threat step. Usage: capture_batch.sh <tag> [cams]
set -u; W=/home/teknetik/.local/state/ward-programme; R=/home/teknetik/code/ao2; EV=$R/unity/evidence/next-level/20261002/combat; cd "$R"; T="${1:-1}"
CAMS="${2:-cam_rifle_aim+cam_rifle_side+cam_rifle_carry+cam_rifle_muzzle}"
mkdir -p "$EV/editor-$T"
DISPLAY=:0 WAYLAND_DISPLAY=wayland-1 $W/unity.sh "$EV/capture-$T.log" AthenHill.Editor.CombatNextLevelPass.RunBatch -quit --steps "threat,capture:$EV/editor-$T:$CAMS"
echo "capture rc=$?"
grep -h "CombatNextLevelPass \|Exception\|error CS" "$EV/capture-$T.log" | grep -v "^UnityEngine\|^ *at " | sort -u | head -20
ls "$EV/editor-$T"
