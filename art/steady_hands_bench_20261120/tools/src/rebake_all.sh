#!/usr/bin/env bash
# model-bench: re-bake of both families after the albedo re-tune, checks, publish, review sheets. Three slot holds.
set -e
cd /home/teknetik/code/ao2/art/steady_hands_bench_20261120
B="env -i HOME=$HOME PATH=/usr/bin:/bin blender -b --factory-startup --python-exit-code 1 -P"
R="$B /home/teknetik/code/ao2/art/steady_hands_bench_20261120/tools/src/review_mb.py --"
echo "== hold 1: geometry check of the tools as built, then both bakes and their checks"
/home/teknetik/.local/state/ward-programme/steady-hands-20261120/slot.sh bash -c "set -e; $B /home/teknetik/code/ao2/art/steady_hands_bench_20261120/tools/check.py; $B /home/teknetik/code/ao2/art/steady_hands_bench_20261120/fixtures/build.py -- --size 2048 --spp 12; $B /home/teknetik/code/ao2/art/steady_hands_bench_20261120/fixtures/check.py; $B /home/teknetik/code/ao2/art/steady_hands_bench_20261120/tools/build.py -- --size 2048 --spp 12; $B /home/teknetik/code/ao2/art/steady_hands_bench_20261120/tools/check.py"
python3 /home/teknetik/code/ao2/art/steady_hands_bench_20261120/tools/src/publish.py fixtures tools
echo "== hold 2: fixtures review"
/home/teknetik/.local/state/ward-programme/steady-hands-20261120/slot.sh bash -c "set -e; $R --family fixtures --glb --shots bench; $R --family fixtures --glb --warm --quick --shots views,close"
echo "== hold 3: tools review and the posed sheets"
/home/teknetik/.local/state/ward-programme/steady-hands-20261120/slot.sh bash -c "set -e; $R --family tools --glb --warm --quick --shots views,close; $R --family fixtures --only vise --warm --quick --shots views --samples 16; $R --family tools --only roll,pliers,cutters --warm --quick --shots views --samples 16"
echo "== MB FINAL DONE"
