#!/usr/bin/env bash
# materials/run_all.sh: build, check and (optionally) review in ONE use of the shared Blender slot.
#   SH/run.sh mm-geo SH/slot.sh materials/run_all.sh "<build args>" "<review --only list or ->" [review samples]
# e.g. run_all.sh "--nobake" "sheets,hero" 24      run_all.sh "--size 2048 --spp 16" -
set -u
D="$(cd "$(dirname "$0")" && pwd)"
B="env -i HOME=$HOME PATH=/usr/bin:/bin blender -b --factory-startup --python-exit-code 1 -P"
filter() { grep -v "INFO: \|^Blender \|^Read \|^Fra:\|^Saved:\|^ Time:\|^$\|Extracting primitive\|Primitives created" ; }
echo "== build ${1:-}"; $B "$D/build.py" -- ${1:-} 2>&1 | filter; brc=${PIPESTATUS[0]}; echo "build rc=$brc"
[ "$brc" = 0 ] || { echo "build failed: check and review not run (the export is stale)"; exit 1; }
echo "== check"; $B "$D/check.py" 2>&1 | filter | tail -30; echo "check rc=${PIPESTATUS[0]}"
if [ "${2:--}" != "-" ]; then echo "== review $2"; $B "$D/review.py" -- --only "$2" --samples "${3:-24}" ${4:-} 2>&1 | filter | tail -15; echo "review rc=${PIPESTATUS[0]}"; fi
