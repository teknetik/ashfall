#!/usr/bin/env bash
# Showcase phase 2: where does the light budget's cost at cam_night_avenue_west come from? Off vs on with a pool-cap
# tune, one camera, three alternating rounds. Usage: lb_isolate.sh BUILD TUNE [TUNE...]
set -u; R=/home/teknetik/code/ao2; P2=/home/teknetik/.local/state/ward-programme/showcase-phase2-20261120; cd "$R"
B="$1"; shift; EXE=$R/unity/AthenHill/Builds/batch-$B/AthenHill.x86_64
for T in "$@"; do
  OUT=$R/unity/evidence/showcase_phase2/20261120/light_budget/${B#p2-}-iso-$T
  [ -e "$OUT" ] && mv "$OUT" "$OUT.old-$(date +%H%M%S)"
  $P2/native_check.sh lb-iso-$T art/light_budget_20261120/tools/lb_native.py ATHEN_EXE=$EXE LB_MODE=ab LB_ROUNDS=3 \
    LB_CAMS=cam_night_avenue_west ATHEN_OUT=$OUT ATHEN_LB_TUNE=$R/art/light_budget_20261120/tunes/$T.json
  echo "== $T rc=$?"
  uv run --offline python art/light_budget_20261120/tools/lb_tables.py ab unity/evidence/showcase_phase2/20261120/light_budget/${B#p2-}-iso-$T
done
