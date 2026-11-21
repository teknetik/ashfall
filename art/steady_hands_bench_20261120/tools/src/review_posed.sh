#!/usr/bin/env bash
# The posed review sheets (rigs at both ends), from the source .blend files: vise, roll, pliers, cutters.
SH=~/.local/state/ward-programme/steady-hands-20261120
D="$(cd "$(dirname "$0")/../.." && pwd)"
$SH/blender.sh $D/tools/src/review_mb.py -- --family fixtures --only vise --quick --shots views --samples 16 || exit 1
$SH/blender.sh $D/tools/src/review_mb.py -- --family tools --only roll,pliers,cutters --quick --shots views --samples 16
