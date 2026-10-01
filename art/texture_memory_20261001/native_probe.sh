#!/usr/bin/env bash
# One native measurement run with the paving pass's texture-streaming probe and a VRAM sampler.
# Usage: native_probe.sh <tag> <exe>   -> unity/evidence/texture-memory/20261001/native-<tag>/
# Never profile frame times with the probe on (it hitches every 8 s); this run is for memory only.
set -u
R=/home/teknetik/code/ao2; O=/home/teknetik/.local/state/ward-programme; E=$R/unity/evidence/texture-memory/20261001
tag=$1; exe=$2; out=$E/native-$tag
[ -e "$out" ] && { echo "exists: $out"; exit 2; }
"$R/art/texture_memory_20261001/vram_sampler.sh" "$E/vram-$tag.csv" 5400 &
s=$!
ATHEN_TEXSTREAM_PROBE=1 "$O/native.sh" lookbook "$out" --cams cam_hill,cam_avenue,cam_gate --hours 13 --exe "$exe" > "$E/native-$tag.out" 2>&1
rc=$?
sleep 3; kill $s 2>/dev/null; wait $s 2>/dev/null
echo "native $tag rc=$rc"; tail -1 "$O/jobs.log" | cut -c1-140
