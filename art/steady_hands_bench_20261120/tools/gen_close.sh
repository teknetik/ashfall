#!/usr/bin/env bash
# Close-up sheets, each made from its overall sheet as the input image so it shows the same object.
cd "$(dirname "$0")/.." || exit 1
python3 tools/gen_sheet.py fixtures fix_vise_close fixtures/sheets/fix_vise_close.prompt.txt --ref fixtures/sheets/fix_vise_turn.png 2>&1 | sed 's/^/[vise] /' &
python3 tools/gen_sheet.py fixtures fix_press_close fixtures/sheets/fix_press_close.prompt.txt --ref fixtures/sheets/fix_press_turn.png 2>&1 | sed 's/^/[press] /' &
python3 tools/gen_sheet.py tools tools_drill_close tools/sheets/tools_drill_close.prompt.txt --ref tools/sheets/tools_bench_turn.png 2>&1 | sed 's/^/[drill] /' &
wait; echo "gen_close done"
