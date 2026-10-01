#!/usr/bin/env bash
# A/B frame time of the range root: toggle (saved scene) -> dev build -> native profile at the wide and the close camera.
# Usage: ab.sh <on|off> <tag>. Always finish with "on" (the saved scene must end with the range on).
set -u
O=/home/teknetik/.local/state/ward-programme
E=/home/teknetik/code/ao2/unity/evidence/training-range/20261001
mkdir -p $E/ab
$O/unity.sh $E/toggle-$2.log AthenHill.Editor.TrainingRangePass.RunBatch --steps toggle:$1 -nographics; rc=$?; echo "toggle $1 exit=$rc"; [ $rc -ne 0 ] && exit $rc
grep -E "TrainingRangePass toggle" $E/toggle-$2.log
$O/build_player.sh $E/build-$2.log || exit $?
$O/native.sh lookbook $E/ab/$2-wide --cams cam_range_overview --hours 13,20.5 --profile 8 > $E/ab/$2-wide.out 2>&1; echo "wide exit=$?"
$O/native.sh lookbook $E/ab/$2-close --cams cam_range_line --hours 13 --profile 8 > $E/ab/$2-close.out 2>&1; echo "close exit=$?"
