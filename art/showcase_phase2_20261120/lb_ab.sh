#!/usr/bin/env bash
# Showcase phase 2: the light budget's own frame-time A/B and check on one build (commands from the light agent).
# Usage: lb_ab.sh BUILD [TUNE]   e.g. lb_ab.sh p2-b5            (installed pool cap)
#                                     lb_ab.sh p2-b5 pools32    (tune file art/light_budget_20261120/tunes/pools32.json)
set -u; R=/home/teknetik/code/ao2; P2=/home/teknetik/.local/state/ward-programme/showcase-phase2-20261120; cd "$R"
B="$1"; T="${2:-}"; EXE=$R/unity/AthenHill/Builds/batch-$B/AthenHill.x86_64; TAG=${B#p2-}${T:+-$T}
OUT=$R/unity/evidence/showcase_phase2/20261120/light_budget/$TAG-ab
[ -e "$OUT" ] && mv "$OUT" "$OUT.old-$(date +%H%M%S)"
extra=(); [ -n "$T" ] && extra=(ATHEN_LB_TUNE=$R/art/light_budget_20261120/tunes/$T.json)
$P2/native_check.sh lb-$TAG-ab art/light_budget_20261120/tools/lb_native.py ATHEN_EXE=$EXE LB_MODE=ab LB_ROUNDS=3 \
  LB_BASE_EXE=$R/unity/AthenHill/Builds/batch-playtest1119/AthenHill.x86_64 \
  LB_CAMS=cam_hill,cam_avenue,cam_night_spawn_apron,cam_night_avenue_west ATHEN_OUT=$OUT "${extra[@]}"
echo "ab rc=$?"
uv run --offline python art/light_budget_20261120/tools/lb_tables.py ab unity/evidence/showcase_phase2/20261120/light_budget/$TAG-ab
if [ -z "$T" ]; then
  $P2/native_check.sh lb-$TAG-check unity/tools/check_showcase_light_budget.py ATHEN_EXE=$EXE ATHEN_OUT=$R/unity/evidence/showcase_phase2/20261120/light_budget/$TAG-check
  echo "check rc=$?"
fi
