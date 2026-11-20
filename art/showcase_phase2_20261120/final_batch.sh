#!/usr/bin/env bash
# Showcase phase 2: the combined native batch on the final build, one native job at a time, in the order the results
# are needed: review captures first (arms, residents, rifle), then the review-camera lookbook, the regression checks,
# the phase 1 package checks plus the light budget check, the frame-time A/B against batch-playtest1119, and the
# light budget's own three-way A/B. Usage: final_batch.sh BUILD TAG     (e.g. final_batch.sh p2-final final)
# Waits for the final sweep (run.sh job "final-sweep") to finish and for the build to exist.
set -u; R=/home/teknetik/code/ao2; P2=/home/teknetik/.local/state/ward-programme/showcase-phase2-20261120; cd "$R"
B="$1"; TAG="$2"; A=art/showcase_phase2_20261120
while [ "$(cat $P2/jobs/final-sweep.rc 2>/dev/null)" = running ]; do sleep 15; done
[ -x "unity/AthenHill/Builds/batch-$B/AthenHill.x86_64" ] || { echo "no build batch-$B: the sweep or the build failed"; exit 2; }
echo "$(date +%H:%M:%S) final batch on $B starts"
$A/captures.sh  "$B" "$TAG" arms residents rifle
$A/run_batch.sh "$B" "$TAG" lookbook regression packages ab
$A/lb_ab.sh     "$B"
echo "$(date +%H:%M:%S) final batch on $B done"
