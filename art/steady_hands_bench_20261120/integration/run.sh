#!/usr/bin/env bash
# Steady Hands bench, integration: one -nographics Unity run of SteadyHandsBenchInstall20261120 on the shared Unity lock.
# Usage: integration/run.sh NAME STEPS            e.g.  run.sh real1 install,verify,benchverify,benchselftest
#        integration/run.sh NAME rollback         removes the look's two scene roots AND rebuilds the bench from stand-ins
# The families that are real come from data/sources.json; the same list goes to the bench installer as --real.
# Start it detached and wait:  SH/run.sh integ-NAME art/steady_hands_bench_20261120/integration/run.sh NAME STEPS ; SH/wait.sh integ-NAME
set -u
HERE=$(cd "$(dirname "$0")" && pwd); P=$(dirname "$HERE"); SH=$HOME/.local/state/ward-programme/steady-hands-20261120
NAME=$1; STEPS=$2; shift 2
real() { python3 - "$P/data/sources.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1]))
print(','.join(f for f in ('fixtures', 'tools', 'pistol', 'grip', 'servo', 'materials') if s.get(f) == 'real') or 'none')
PY
}
if [ "$STEPS" = rollback ]; then
  cp "$P/data/sources.json" "$P/integration/sources-before-rollback.json"
  python3 - "$P/data/sources.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
for k in ('fixtures', 'tools', 'pistol', 'grip', 'servo', 'materials'): d[k] = 'greybox'
json.dump(d, open(sys.argv[1], 'w'), indent=2); open(sys.argv[1], 'a').write('\n')
PY
  STEPS=rollback,bind
fi
free -g | awk '/Mem/{a=$7} /Swap/{s=$3} END{print "before: RAM available " a " GB, swap used " s " GB"}'
exec "$SH/seq.sh" install "integ-$NAME" AthenHill.Editor.SteadyHandsBenchInstall20261120.RunBatch "$STEPS" --real "$(real)" "$@"
