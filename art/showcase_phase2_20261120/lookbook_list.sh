#!/usr/bin/env bash
# Showcase phase 2: native lookbook of a given camera list on one build. Usage: lookbook_list.sh BUILD TAG CAMFILE [HOURS]
# Eight cameras per player run, each through native_check.sh. Output: unity/evidence/showcase_phase2/20261120/qa/TAG/lookbook-N
set -u; R=/home/teknetik/code/ao2; P2=/home/teknetik/.local/state/ward-programme/showcase-phase2-20261120
B="$1"; TAG="$2"; CAMS="$3"; HOURS="${4:-13,20.5}"; EXE=$R/unity/AthenHill/Builds/batch-$B/AthenHill.x86_64
case "$B" in p2-*) ;; *) echo "phase 2 builds only"; exit 2 ;; esac
Q=$R/unity/evidence/showcase_phase2/20261120/qa/$TAG; mkdir -p "$Q"; cd "$R"; n=0
split -l 8 -d "$CAMS" "$Q/cams-part-"
for part in "$Q"/cams-part-*; do
  n=$((n+1)); [ -e "$Q/lookbook-$n" ] && mv "$Q/lookbook-$n" "$Q/lookbook-$n.old-$(date +%H%M%S)"
  $P2/native_check.sh $TAG-lookbook-$n art/showcase_phase2_20261120/run_lookbook.py ATHEN_EXE=$EXE P2_OUT=$Q/lookbook-$n P2_CAMS=$(paste -sd, "$part") P2_HOURS=$HOURS
  echo "$(date +%H:%M:%S) lookbook part $n rc=$?"
done
