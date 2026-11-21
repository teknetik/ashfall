#!/usr/bin/env bash
# Steady Hands, integration: SH/seq.sh tests with -testFilter (seq.sh runs the whole suite only). Same lock, cap and
# compile gate as seq.sh; output editmode-TAG.xml/.log/.summary in the evidence folder.  Usage: tests_filter.sh TAG FILTER
set -u; W=/home/teknetik/.local/state/ward-programme; S=$W/steady-hands-20261120; R=/home/teknetik/code/ao2
EV=$R/unity/evidence/steady_hands/20261120; cd "$R"; TAG=$1; FILTER=$2
n=0; until python3 unity/tools/compile_check.py >/dev/null 2>&1; do n=$((n+1)); [ $n -ge 60 ] && exit 90; sleep 30; done
flock -w 7200 "$W/unity.lock" bash -c '. '"$W"'/lib.sh; run_capped unity '"${P2_MAX:-17G}"' '"${P2_SWAP:-3G}"' timeout 1500 /home/teknetik/Unity/Hub/Editor/6000.6.0f1/Editor/Unity -batchmode -nographics -projectPath unity/AthenHill -runTests -testPlatform EditMode -testFilter "$3" -testResults "$1" -logFile "$2"' _ "$EV/editmode-$TAG.xml" "$EV/editmode-$TAG.log" "$FILTER"
rc=$?
python3 - "$EV/editmode-$TAG.xml" > "$EV/editmode-$TAG.summary" 2>&1 <<'PY'
import sys,xml.etree.ElementTree as ET
r=ET.parse(sys.argv[1]).getroot(); print('editmode', r.get('result'), 'total', r.get('total'), 'passed', r.get('passed'), 'failed', r.get('failed'))
for tc in r.iter('test-case'):
    if tc.get('result')=='Failed':
        f=tc.find('failure'); print('  FAILED', tc.get('fullname'), ((f.find('message').text or '') if f is not None and f.find('message') is not None else '')[:500].replace('\n',' '))
PY
echo "$(date +%H:%M:%S) tests $TAG (filter $FILTER) rc=$rc $(head -1 "$EV/editmode-$TAG.summary")" | tee -a "$S/progress.log"; exit $rc
