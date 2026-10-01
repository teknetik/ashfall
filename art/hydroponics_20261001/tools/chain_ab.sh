#!/usr/bin/env bash
# One half of the hydroponics A/B: chain_ab.sh <on|off> <tag> [extra Unity steps before the toggle]
# Unity toggle (saved scene) -> development build -> native lookbook of the review cameras at 13:00/20:30 with an 8 s
# profile at cam_hy_wide, then 8 s profiles at cam_hy_skin_close (close) and cam_hill (district wide), all 13:00.
O=/home/teknetik/.local/state/ward-programme
E=/home/teknetik/code/ao2/unity/evidence/hydroponics/20261001
state=$1; tag=$2; pre=${3:-}
cd /home/teknetik/code/ao2
steps="toggle:$state"; [ -n "$pre" ] && steps="$pre,$steps"
if [ "$pre" = "nounity" ]; then echo "skip unity (scene already $state)"; else
$O/unity.sh $E/logs/ab-$tag-unity.log AthenHill.Editor.HydroponicsPass.RunBatch --steps $steps --out $E/editor-$tag > /dev/null 2>&1
rc=$?; echo "unity $steps exit $rc"; grep -E "HydroponicsPass .*: |error CS|Exception" $E/logs/ab-$tag-unity.log | cut -c1-200 | head -8
[ $rc -ne 0 ] && exit $rc
fi
$O/build_player.sh $E/logs/ab-$tag-build.log || exit $?
CAMS=cam_hy_wide,cam_hy_east_yard,cam_hy_harvest,cam_hy_nursery,cam_hy_potting,cam_hy_south_lane,cam_hy_skin_close,cam_hy_gap,cam_hy_compost,cam_hy_pump,cam_retrofit_hydro,cam_sd_hydroponics
rm -rf $E/native-$tag $E/native-$tag-close $E/native-$tag-hill
$O/native.sh lookbook $E/native-$tag --cams $CAMS --hours 13,20.5 --profile 8 --sheet > $E/logs/native-$tag.out 2>&1; echo "lookbook $tag exit $?"
$O/native.sh lookbook $E/native-$tag-close --cams cam_hy_skin_close --hours 13 --profile 8 > $E/logs/native-$tag-close.out 2>&1; echo "close exit $?"
$O/native.sh lookbook $E/native-$tag-hill --cams cam_hill --hours 13 --profile 8 > $E/logs/native-$tag-hill.out 2>&1; echo "hill exit $?"
python3 - <<PY
import json
for d in ("native-$tag", "native-$tag-close", "native-$tag-hill"):
    try:
        L = json.load(open("$E/" + d + "/lookbook.json"))
        for k, p in L["profiles"].items():
            print(d, k, "fps %.1f p50 %.2f p95 %.2f p99 %.2f max %.2f cpu %.2f tris %.0f setpass %.0f" % (p["averageFps"], p["p50Ms"], p["p95Ms"], p["p99Ms"], p["maxMs"], p["cpuMs"]["mean"], p["tris"]["mean"], p["setPass"]["mean"]))
        print(d, "errors", L["errors"], "load", L["loadAverage"])
    except Exception as e:
        print(d, "no report", e)
PY
