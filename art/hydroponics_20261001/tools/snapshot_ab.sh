#!/usr/bin/env bash
# Clean hydroponics A/B from one scene snapshot (HydroponicsPass abbuild:on / abbuild:off -> Builds/hy-ab-on|off), then
# alternating native profiles (on, off, on, off) at cam_hy_wide (13:00 and 20:30), cam_hy_skin_close and cam_hill (13:00).
O=/home/teknetik/.local/state/ward-programme
E=/home/teknetik/code/ao2/unity/evidence/hydroponics/20261001
H=/home/teknetik/code/ao2/art/hydroponics_20261001
B=/home/teknetik/code/ao2/unity/AthenHill/Builds
cd /home/teknetik/code/ao2
$O/unity.sh $E/logs/abprep.log AthenHill.Editor.HydroponicsPass.RunBatch --steps build,verify -nographics > /dev/null 2>&1
echo "build,verify exit $?"; grep -E "HydroponicsPass .*: |error CS|Exception" $E/logs/abprep.log | cut -c1-160 | head -4
for arm in on off noyard; do
  $O/unity.sh $E/logs/abbuild-$arm.log AthenHill.Editor.HydroponicsPass.RunBatch --steps abbuild:$arm -nographics > /dev/null 2>&1
  rc=$?; echo "abbuild:$arm exit $rc"; grep -E "HydroponicsPass .*: |error CS|Exception" $E/logs/abbuild-$arm.log | cut -c1-160 | head -4
  if [ $rc -ne 0 ]; then echo "retry once"; $O/unity.sh $E/logs/abbuild-$arm-retry.log AthenHill.Editor.HydroponicsPass.RunBatch --steps abbuild:$arm -nographics > /dev/null 2>&1 || exit 1; fi
done
for round in 1 2; do
  arms="on off"; [ $round = 1 ] && arms="on off noyard"
  for arm in $arms; do
    t=ab$round-$arm
    rm -rf $E/native-$t $E/native-$t-close $E/native-$t-hill
    $O/native.sh lookbook $E/native-$t --cams cam_hy_wide,cam_hy_east_yard,cam_hy_skin_close,cam_hy_harvest --hours 13,20.5 --profile 8 --exe $B/hy-ab-$arm/AthenHill.x86_64 > $E/logs/native-$t.out 2>&1
    $O/native.sh lookbook $E/native-$t-close --cams cam_hy_skin_close --hours 13 --profile 8 --exe $B/hy-ab-$arm/AthenHill.x86_64 > $E/logs/native-$t-close.out 2>&1
    $O/native.sh lookbook $E/native-$t-hill --cams cam_hill --hours 13 --profile 8 --exe $B/hy-ab-$arm/AthenHill.x86_64 > $E/logs/native-$t-hill.out 2>&1
    python3 $H/tools/ab_report.py $E native-$t native-$t-close native-$t-hill
  done
done
