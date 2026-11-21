#!/usr/bin/env bash
# Overall reference sheets (first round), four requests at a time. Network only, no heavy compute.
cd "$(dirname "$0")/.." || exit 1
printf '%s\n' "tools tools_roll_turn" "tools tools_hand_turn" "tools tools_bench_turn" "fixtures fix_vise_turn" \
  "fixtures fix_press_turn" "fixtures fix_tester_turn" "fixtures fix_small_turn" "fixtures fix_mats_turn" |
xargs -P 4 -L 1 bash -c 'python3 tools/gen_sheet.py "$0" "$1" "$0/sheets/$1.prompt.txt" 2>&1 | sed "s/^/[$1] /"'
echo "gen_overall done"
