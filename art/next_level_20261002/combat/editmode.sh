#!/usr/bin/env bash
# Edit Mode tests for the next-level combat pass (one Unity job under the shared lock, -nographics, capped).
# Usage: editmode.sh <tag>   -> unity/evidence/next-level/20261002/combat/editmode-<tag>.{xml,log,summary}
set -u; W=/home/teknetik/.local/state/ward-programme; R=/home/teknetik/code/ao2; EV=$R/unity/evidence/next-level/20261002/combat; cd "$R"; T="${1:-1}"
flock -w 7200 "$W/unity.lock" bash -c '. '"$W"'/lib.sh; run_capped unity 12G 1G timeout 2400 /home/teknetik/Unity/Hub/Editor/6000.6.0f1/Editor/Unity -batchmode -nographics -projectPath unity/AthenHill -runTests -testPlatform EditMode -testResults "$1" -logFile "$2"' _ "$EV/editmode-$T.xml" "$EV/editmode-$T.log"
python3 - "$EV/editmode-$T.xml" <<'PY' > "$EV/editmode-$T.summary" 2>&1
import sys,xml.etree.ElementTree as ET
r=ET.parse(sys.argv[1]).getroot(); print('editmode', r.get('result'), 'total', r.get('total'), 'passed', r.get('passed'), 'failed', r.get('failed'))
for tc in r.iter('test-case'):
    if tc.get('result')=='Failed':
        f=tc.find('failure'); print('  FAILED', tc.get('fullname'), ((f.find('message').text or '') if f is not None and f.find('message') is not None else '')[:400].replace('\n',' '))
PY
cat "$EV/editmode-$T.summary"
