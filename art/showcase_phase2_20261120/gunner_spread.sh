#!/usr/bin/env bash
# Showcase phase 2: is the gunner-separation result run-to-run spread or a change? The same check, alternating the
# phase 1 build (read-only) and a phase 2 build. Usage: gunner_spread.sh BUILD ROUNDS
set -u; R=/home/teknetik/code/ao2; P2=/home/teknetik/.local/state/ward-programme/showcase-phase2-20261120; cd "$R"
B="$1"; N="${2:-3}"; Q=$R/unity/evidence/showcase_phase2/20261120/qa/gunner-spread; mkdir -p "$Q"
for i in $(seq 1 "$N"); do
  for b in playtest1119 "$B"; do
    out=$Q/$b-$i; [ -e "$out" ] && mv "$out" "$out.old-$(date +%H%M%S)"
    $P2/native_check.sh gs-$b-$i unity/tools/check_gunner_separation.py ATHEN_EXE=$R/unity/AthenHill/Builds/batch-$b/AthenHill.x86_64 ATHEN_GUNNER_EVIDENCE=$out >/dev/null
    echo "$b round $i: $(grep 'pairwise separation' $R/unity/evidence/showcase_phase2/20261120/gs-$b-$i.out | cut -c1-140)"
  done
done
