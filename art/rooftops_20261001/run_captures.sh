#!/usr/bin/env bash
# Editor captures (<= 6 cameras per Unity run, BRIEF memory safety). Usage: run_captures.sh <tag> <cam+cam+...> [off]
# "off" deactivates the Ward rooftops root in memory for a matched before view (nothing is saved).
set -u
O=/home/teknetik/.local/state/ward-programme; R=/home/teknetik/code/ao2; TAG="$1"; CAMS="$2"; MODE="${3:-}"
$O/unity.sh $R/art/rooftops_20261001/logs/capture-$TAG-${MODE:-on}.log AthenHill.Editor.RooftopsPass.RunBatch --steps "capture:../evidence/rooftops/20261001/editor-$TAG:$CAMS${MODE:+:$MODE}"
echo "$TAG ${MODE:-on} rc=$?"
