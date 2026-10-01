#!/usr/bin/env bash
# Final hydroponics A/B (1 Oct): rebuild assets + reinstall + verify, pass OFF -> build -> native off3; pass ON -> build ->
# native on3 -> city loop. Non-rendering Unity steps run with -nographics (GPU memory rule).
O=/home/teknetik/.local/state/ward-programme
E=/home/teknetik/code/ao2/unity/evidence/hydroponics/20261001
H=/home/teknetik/code/ao2/art/hydroponics_20261001
cd /home/teknetik/code/ao2
CAMS=cam_hy_wide,cam_hy_east_yard,cam_hy_harvest,cam_hy_nursery,cam_hy_potting,cam_hy_south_lane,cam_hy_skin_close,cam_hy_gap,cam_hy_compost,cam_hy_pump,cam_retrofit_hydro,cam_sd_hydroponics
unity() { $O/unity.sh $E/logs/$1.log AthenHill.Editor.HydroponicsPass.RunBatch --steps $2 -nographics > /dev/null 2>&1; rc=$?
          echo "unity $2 exit $rc"; grep -E "HydroponicsPass .*: |error CS|Exception" $E/logs/$1.log | cut -c1-160 | head -6; return $rc; }
half() {   # tag
  $O/build_player.sh $E/logs/$1-build.log || { echo "build failed, retry once"; $O/build_player.sh $E/logs/$1-build-retry.log || return 1; }
  rm -rf $E/native-$1 $E/native-$1-close $E/native-$1-hill
  $O/native.sh lookbook $E/native-$1 --cams $CAMS --hours 13,20.5 --profile 8 --sheet > $E/logs/native-$1.out 2>&1; echo "lookbook $1 exit $?"
  $O/native.sh lookbook $E/native-$1-close --cams cam_hy_skin_close --hours 13 --profile 8 > $E/logs/native-$1-close.out 2>&1; echo "close exit $?"
  $O/native.sh lookbook $E/native-$1-hill --cams cam_hill --hours 13 --profile 8 > $E/logs/native-$1-hill.out 2>&1; echo "hill exit $?"
  python3 $H/tools/ab_report.py $E native-$1 native-$1-close native-$1-hill
}
unity final-prep "build,reinstall,verify,toggle:off" || exit 1
half off3
unity final-on "toggle:on,verify" || exit 1
half on3
rm -rf $E/cityloop-native
$O/native.sh cityloop $E/cityloop-native > $E/logs/cityloop.out 2>&1; echo "cityloop exit $?"; grep -E "CITY LOOP" $E/logs/cityloop.out | tail -2
