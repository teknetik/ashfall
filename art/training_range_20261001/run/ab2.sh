#!/usr/bin/env bash
# A/B frame time of the range root with alternating native runs (desktop drift is ±1–1.5 ms between runs):
# toggle off -> -nographics build -> reflink copy Builds/tr-ab-off; toggle on -> build -> Builds/tr-ab-on (the saved
# scene ends ON); then on/off/on/off lookbook profiles (wide cam_range_overview 13:00+20:30, close cam_range_line 13:00).
set -u
O=/home/teknetik/.local/state/ward-programme
E=/home/teknetik/code/ao2/unity/evidence/training-range/20261001
B=/home/teknetik/code/ao2/unity/AthenHill/Builds
mkdir -p $E/ab
for st in off on; do
  $O/unity.sh $E/toggle-ab2-$st.log AthenHill.Editor.TrainingRangePass.RunBatch --steps toggle:$st -nographics; rc=$?
  echo "toggle $st exit=$rc"; grep -E "TrainingRangePass toggle" $E/toggle-ab2-$st.log
  if [ $rc -ne 0 ]; then [ $st = off ] && $O/unity.sh $E/toggle-ab2-restore.log AthenHill.Editor.TrainingRangePass.RunBatch --steps toggle:on -nographics; exit $rc; fi
  $O/build_player.sh $E/build-ab2-$st.log; rc=$?
  if [ $rc -ne 0 ]; then [ $st = off ] && $O/unity.sh $E/toggle-ab2-restore.log AthenHill.Editor.TrainingRangePass.RunBatch --steps toggle:on -nographics; exit $rc; fi
  rm -rf $B/tr-ab-$st; cp -r --reflink=auto $B/LinuxDevelopment $B/tr-ab-$st; echo "copied tr-ab-$st"
done
for round in 1 2; do
  for st in on off; do
    X=$B/tr-ab-$st/AthenHill.x86_64
    $O/native.sh lookbook $E/ab/ab2-r$round-$st-wide --cams cam_range_overview --hours 13,20.5 --profile 8 --exe $X > $E/ab/ab2-r$round-$st-wide.out 2>&1; echo "r$round $st wide exit=$?"
    $O/native.sh lookbook $E/ab/ab2-r$round-$st-close --cams cam_range_line --hours 13 --profile 8 --exe $X > $E/ab/ab2-r$round-$st-close.out 2>&1; echo "r$round $st close exit=$?"
  done
done
