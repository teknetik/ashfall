#!/usr/bin/env bash
R=/home/teknetik/code/ao2; O=/home/teknetik/.local/state/ward-programme
until [ "$(grep -c 'rc=' $R/art/rooftops_20261001/logs/captures-cited-off-retry.out)" -ge 2 ]; do sleep 5; done
$O/unity.sh $R/art/rooftops_20261001/logs/reinstall3.log AthenHill.Editor.RooftopsPass.RunBatch --steps build,reinstall,verify -nographics
echo "reinstall3 rc=$?"
$R/art/rooftops_20261001/run_captures.sh v3 cam_district_water+cam_district_salvage+cam_hill
$R/art/rooftops_20261001/run_captures.sh v3 cam_rt_west_north+cam_rt_east_north+cam_district_field
