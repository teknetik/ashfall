#!/usr/bin/env bash
# servo/src/slot_run.sh: several Blender runs of the servo family in ONE use of the shared Blender slot.
#   SH/run.sh TAG SH/slot.sh bash servo/src/slot_run.sh "script.py -- args" "script.py -- args" ...
# Each argument is one Blender run (script path relative to servo/). Stops at the first failure.
set -u
D="$(cd "$(dirname "$0")/.." && pwd)"
filter() { grep -v "INFO: \|^Blender \|^Read \|^Fra:\|^Saved:\|^ Time:\|^$\|Extracting primitive\|Primitives created\|^Info: \|Data are loaded\|glTF import finished" ; }
for job in "$@"; do
  set -- $job
  s="$1"; shift
  echo "== $s $*"
  env -i HOME="$HOME" PATH=/usr/bin:/bin blender -b --factory-startup --python-exit-code 1 -P "$D/$s" "$@" 2>&1 | filter
  rc=${PIPESTATUS[0]}; echo "rc=$rc"
  [ "$rc" = 0 ] || exit "$rc"
done
