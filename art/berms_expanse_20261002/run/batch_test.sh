#!/usr/bin/env bash
# Combined native test for the Outer Berms expansion (AGENTS.md §7 batch): development build, A/B builds (expansion on/off
# from one scene snapshot), lookbook of the review cameras at 13:00 and 20:30, alternating frame-time runs, city loop,
# range tutorial, the expansion check. Usage: batch_test.sh <OUT>
set -u
W=/home/teknetik/.local/state/ward-programme; R=/home/teknetik/code/ao2; EV="$1"; mkdir -p "$EV"; cd "$R"
log(){ echo "$(date +%H:%M:%S) $*" | tee -a "$EV/run.log"; }
log "batch start ($(git rev-parse --short HEAD) + working tree)"
$W/build_player.sh "$EV/build.log" | tee "$EV/build.result"; grep -q "Result: Success" "$EV/build.result" || { log "BUILD FAILED"; exit 1; }
for arm in on off; do
  $W/unity.sh "$EV/abbuild-$arm.log" AthenHill.Editor.BermsExpansePass.RunBatch -nographics -quit --steps abbuild:$arm >/dev/null 2>&1
  grep -E "BermsExpansePass abbuild" "$EV/abbuild-$arm.log" | tail -1 | tee -a "$EV/run.log"
done
ON=$R/unity/AthenHill/Builds/bx-ab-on/AthenHill.x86_64; OFF=$R/unity/AthenHill/Builds/bx-ab-off/AthenHill.x86_64
CAMS="cam_hill,cam_avenue,cam_gate,cam_grid,cam_whompah,cam_hero,cam_market,cam_courtyard,cam_westgate_mouth,cam_berms_overview,cam_bx_gate_west,cam_bx_depot_rise,cam_bx_waystation,cam_bx_relay_knoll,cam_bx_west_outpost,cam_bx_tube_pylon,cam_bx_scrapyard,cam_bx_caravan,cam_bx_derrick,cam_bx_far_west_back,cam_bx_south_edge,cam_bx_north_mesa"
echo "$CAMS" | tr ',' '\n' > "$EV/cameras.txt"
$W/lookbook_chunks.sh "$EV/lookbook" "$EV/cameras.txt" "$R/unity/AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64" 11 13,20.5 >> "$EV/run.log" 2>&1; log "lookbook done"
$W/ab.sh "$EV/ab" "$OFF" "$ON" 2 cam_hill,cam_avenue,cam_gate,cam_westgate_mouth,cam_berms_overview >> "$EV/run.log" 2>&1; log "A/B off->on done"
$W/native.sh cityloop "$EV/cityloop" > "$EV/cityloop.out" 2>&1; log "cityloop rc=$? $(grep -o 'CITY LOOP [A-Z]*' "$EV/cityloop.out" | tail -1)"
bash art/training_range_20261001/run/tutorial.sh "$EV/tutorial" > "$EV/tutorial.out" 2>&1; log "range tutorial rc=$? $(python3 -c "import json;r=json.load(open('$EV/tutorial/report.json'));print(r['passed'],len(r['checks']),r.get('error',''))" 2>&1)"
art/berms_expanse_20261002/run/native_check.sh "$EV/expanse" > "$EV/expanse.out" 2>&1; log "expanse check rc=$? $(python3 -c "import json;r=json.load(open('$EV/expanse/report.json'));print(r['passed'],len(r['checks']),r.get('error',''))" 2>&1)"
log "batch done"
