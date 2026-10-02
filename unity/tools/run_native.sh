#!/usr/bin/env bash
# Attach an existing native QA player: run_native.sh <native-dir> <script.py> [args...]
# Never starts/stops Unity or a player, and never targets an unrelated window.
set -euo pipefail
if (( $# < 2 )); then
  echo "Usage: $0 <existing-native-dir> <script.py> [args...]" >&2
  exit 2
fi
export DISPLAY=${DISPLAY:-:0} XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-/run/user/$(id -u)} WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-wayland-1}
dir=$(realpath -e -- "$1"); shift
script=$1; shift
export ATHEN_NATIVE_DIR=$dir
ATHEN_NATIVE_PID=$(cat "$dir/pid")
export ATHEN_NATIVE_PID
# Refuse stale/recycled PIDs or a run directory belonging to a different player.
python3 - <<'CHECK'
import os
from pathlib import Path
pid = int(os.environ['ATHEN_NATIVE_PID'])
run = Path(os.environ['ATHEN_NATIVE_DIR']).resolve()
try:
    exe = Path(f'/proc/{pid}/exe').resolve(strict=True)
    args = Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
    index = args.index(b'--athen-qa')
    actual = Path(os.fsdecode(args[index + 1])).resolve()
except (OSError, ValueError, IndexError) as error:
    raise SystemExit(f'No live QA player for {run}: {error}')
if exe.name != 'AthenHill.x86_64' or actual != run:
    raise SystemExit(f'PID {pid} is not the QA player for {run}')
CHECK
cd -- "$(dirname -- "$(realpath -- "${BASH_SOURCE[0]}")")"
exec uv run --offline --with python-xlib --with pillow python "$script" "$@"
