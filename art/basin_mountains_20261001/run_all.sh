#!/usr/bin/env bash
# Basin mountains source pipeline (1 Oct 2026). Memory-capped wrappers only.
set -euo pipefail
O=/home/teknetik/.local/state/ward-programme
cd "$(dirname "$0")"
$O/heavy.sh uv run --with numpy --with numba --with scipy --with pillow python basin_heightfield.py   # ~40 s -> work/heightfield.npz
$O/heavy.sh uv run --with numpy --with numba --with scipy python basin_mesh.py --theta "${THETA:-0.006}"  # -> work/chunks, mesh.json
$O/blender.sh "$(pwd)/basin_blender.py"                                                               # -> BasinMountains.glb, .blend
uv run --with numpy --with scipy python verify_glb.py >/dev/null && echo "glb verified (glb-verify.json)"
