#!/usr/bin/env bash
# Next-level combat install (one -nographics Unity job): rifle re-mount, nested-droid removal, DroidThreat defaults,
# trade click, music playlist, verify. Then the Edit Mode tests. Usage: install_batch.sh <tag>
set -u; W=/home/teknetik/.local/state/ward-programme; R=/home/teknetik/code/ao2; EV=$R/unity/evidence/next-level/20261002/combat; cd "$R"; T="${1:-1}"
$W/unity.sh "$EV/install-$T.log" AthenHill.Editor.CombatNextLevelPass.RunBatch -nographics -quit --steps rifle,gunners,threat,trade,music,verify
echo "install rc=$?"
grep -h "CombatNextLevelPass \|RifleArmourInstall rifle\|Exception\|verify failed" "$EV/install-$T.log" | grep -v "^UnityEngine\|^ *at " | head -40
