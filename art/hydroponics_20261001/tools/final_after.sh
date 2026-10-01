#!/usr/bin/env bash
# Final state: rebuild assets (skin material), verify, development build, native lookbook of record, city loop.
O=/home/teknetik/.local/state/ward-programme
E=/home/teknetik/code/ao2/unity/evidence/hydroponics/20261001
cd /home/teknetik/code/ao2
run_unity() { $O/unity.sh $E/logs/$1.log AthenHill.Editor.HydroponicsPass.RunBatch --steps $2 -nographics > /dev/null 2>&1; }
run_unity final-assets build,verify || { echo "unity retry"; run_unity final-assets-retry build,verify || exit 1; }
echo "unity build,verify ok"; grep -E "HydroponicsPass .*: |error CS" $E/logs/final-assets*.log | cut -c1-120 | head -4
$O/build_player.sh $E/logs/final-build.log || { echo "build retry"; $O/build_player.sh $E/logs/final-build-retry.log || exit 1; }
rm -rf $E/native-after
$O/native.sh lookbook $E/native-after --cams cam_hy_wide,cam_hy_east_yard,cam_hy_harvest,cam_hy_nursery,cam_hy_potting,cam_hy_south_lane,cam_hy_skin_close,cam_hy_gap,cam_hy_compost,cam_hy_pump,cam_retrofit_hydro,cam_sd_hydroponics,cam_hill --hours 13,20.5 --sheet > $E/logs/native-after.out 2>&1; echo "lookbook after exit $?"
rm -rf $E/cityloop-final
$O/native.sh cityloop $E/cityloop-final > $E/logs/cityloop-final.out 2>&1; echo "cityloop exit $?"; grep -E "CITY LOOP" $E/logs/cityloop-final.out | tail -1
