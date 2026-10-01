#!/usr/bin/env bash
# Native evidence for the night-life pass (1 Oct 2026). Both arms come from ONE snapshot of the saved scene
# (NightLifePass abbuild:on / abbuild:off -> Builds/nl-ab-on, Builds/nl-ab-off). Usage:
#   native_runs.sh captures <tag>      lookbook of every review view, both arms, 13:00 and 20:30
#   native_runs.sh ab <tag> <cam> [n]  alternating off/on 8 s profiles at <cam>, 13:00 and 20:30, n rounds (default 2)
set -u
O=/home/teknetik/.local/state/ward-programme
cd /home/teknetik/code/ao2
EV=unity/evidence/night-life/20261001
B=/home/teknetik/code/ao2/unity/AthenHill/Builds
NL="cam_nl_courtyard,cam_nl_terminals,cam_nl_lattice,cam_nl_hall_corner,cam_nl_hill_benches,cam_nl_apron_south,cam_nl_apron_north,cam_nl_south_collapse,cam_nl_south_lane,cam_nl_north_collapse,cam_nl_rampart_south,cam_nl_market_fire,cam_nl_air_water_steam,cam_nl_generator,cam_nl_repairs_flue,cam_nl_salvage_stack"
WIDE="cam_hill,cam_avenue,cam_gate,cam_courtyard,cam_grid"
case "$1" in
  captures)
    tag=$2
    for arm in off on; do
      out=$EV/native-$arm-$tag
      [ -e "$out" ] && { echo "exists: $out"; continue; }
      $O/native.sh lookbook "$out" --cams "$WIDE,$NL" --hours 13,20.5 --sheet --exe "$B/nl-ab-$arm/AthenHill.x86_64" 2>&1 | tail -4
    done ;;
  ab)
    tag=$2; cam=$3; n=${4:-2}
    for i in $(seq 1 "$n"); do
      for arm in off on; do
        out=$EV/ab/$tag-$cam-$arm-$i
        [ -e "$out" ] && { echo "exists: $out"; continue; }
        mkdir -p $EV/ab
        $O/native.sh lookbook "$out" --cams "$cam" --hours 13,20.5 --profile 8 --exe "$B/nl-ab-$arm/AthenHill.x86_64" 2>&1 | tail -12 | grep -E "averageFps|p50|p99|errors" | head -8
      done
    done ;;
esac
