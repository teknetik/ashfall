#!/usr/bin/env bash
# Training range AFTER set: dev build -> native lookbook (13:00, 20:30) + profiles. Usage: after.sh <tag>
set -u
O=/home/teknetik/.local/state/ward-programme
E=/home/teknetik/code/ao2/unity/evidence/training-range/20261001
T=$1
CAMS=cam_range_overview,cam_range_line,cam_range_bays,cam_range_backstop,cam_range_plates,cam_range_machine_lane,cam_range_droid,cam_range_apron,cam_range_lane_start,cam_range_bench,cam_checkpoint_range,cam_checkpoint_target_close,cam_westgate_range,cam_berms_overview
$O/build_player.sh $E/build-$T.log || exit $?
$O/native.sh lookbook $E/native-$T --cams $CAMS --hours 13,20.5 --profile 8 --sheet > $E/native-$T.out 2>&1; echo "lookbook exit=$?"
$O/native.sh lookbook $E/native-$T-close --cams cam_range_line --hours 13 --profile 8 > $E/native-$T-close.out 2>&1; echo "lookbook close exit=$?"
