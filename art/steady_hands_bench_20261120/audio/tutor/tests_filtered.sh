#!/usr/bin/env bash
# tutor agent, 21 Nov 2026: seq.sh's `tests` step with a -testFilter (same compile gate, shared Unity lock and memory cap).
# Usage: tests_filtered.sh TAG FILTER     e.g. tests_filtered.sh tutor-c1 AthenHill.Tests.SteadyHandsCraftTests
set -u; W=/home/teknetik/.local/state/ward-programme; S=$W/steady-hands-20261120; R=/home/teknetik/code/ao2
EV=$R/unity/evidence/steady_hands/20261120; TAG=$1; FILTER=$2; cd "$R"
n=0; until python3 unity/tools/compile_check.py >/dev/null 2>&1; do n=$((n+1)); [ $n -ge 60 ] && { echo "compile gate timed out"; exit 90; }; sleep 30; done
flock -w 7200 "$W/unity.lock" bash -c '. '"$W"'/lib.sh; run_capped unity '"${P2_MAX:-17G}"' '"${P2_SWAP:-3G}"' timeout 2400 /home/teknetik/Unity/Hub/Editor/6000.6.0f1/Editor/Unity -batchmode -nographics -projectPath unity/AthenHill -runTests -testPlatform EditMode -testFilter "$3" -testResults "$1" -logFile "$2"' _ "$EV/editmode-$TAG.xml" "$EV/editmode-$TAG.log" "$FILTER"
rc=$?
python3 - "$EV/editmode-$TAG.xml" > "$EV/editmode-$TAG.summary" 2>&1 <<'PY'
import sys,xml.etree.ElementTree as ET
r=ET.parse(sys.argv[1]).getroot(); print('editmode', r.get('result'), 'total', r.get('total'), 'passed', r.get('passed'), 'failed', r.get('failed'), 'skipped', r.get('skipped'))
for tc in r.iter('test-case'):
    if tc.get('result')=='Failed':
        f=tc.find('failure'); print('  FAILED', tc.get('fullname'), ((f.find('message').text or '') if f is not None and f.find('message') is not None else '')[:500].replace('\n',' '))
PY
echo "$(date +%H:%M:%S) tests $TAG ($FILTER) rc=$rc $(head -1 "$EV/editmode-$TAG.summary")" | tee -a "$S/progress.log"
cd "$R" && git diff --quiet -- unity/AthenHill/ProjectSettings/ProjectSettings.asset || echo "NOTE: ProjectSettings.asset changed"
exit $rc
