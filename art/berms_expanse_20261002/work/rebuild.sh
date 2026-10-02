#!/usr/bin/env bash
# terrain -> layout -> scatter -> meshes (memory-capped). Usage: work/rebuild.sh <tag>
set -e
cd /home/teknetik/code/ao2/art/berms_expanse_20261002
O=/home/teknetik/.local/state/ward-programme
$O/heavy.sh uv run --offline --with numpy --with numba --with scipy --with pillow --with matplotlib python expanse_heightfield.py > work/run_$1.log 2>&1
uv run --offline --with numpy --with scipy --with matplotlib python layout.py >> work/run_$1.log 2>&1
$O/heavy.sh uv run --offline --with numpy --with scipy --with matplotlib python scatter.py >> work/run_$1.log 2>&1
$O/heavy.sh uv run --offline --with numpy --with numba --with scipy --with matplotlib python expanse_mesh.py --theta 0.012 >> work/run_$1.log 2>&1
echo done >> work/run_$1.log
