#!/usr/bin/env bash
# EditMode tests under the shared Unity lock in a capped scope (never -quit with -runTests). Usage: editmode.sh <OUT_DIR> [filter]
set -u; OUT="$1"; FILTER="${2:-}"; mkdir -p "$OUT"; cd /home/teknetik/code/ao2
flock -w 5400 /home/teknetik/.local/state/ward-programme/unity.lock bash -c '. /home/teknetik/.local/state/ward-programme/lib.sh; OUT=$1; F=$2; run_capped unity 17G 3G timeout 3600 /home/teknetik/Unity/Hub/Editor/6000.6.0f1/Editor/Unity -batchmode -nographics -projectPath unity/AthenHill -runTests -testPlatform EditMode ${F:+-testFilter "$F"} -testResults "$OUT/editmode.xml" -logFile "$OUT/editmode.log"' _ "$OUT" "$FILTER"
rc=$?
python3 - "$OUT/editmode.xml" <<'PY'
import sys,xml.etree.ElementTree as ET
try:
    r=ET.parse(sys.argv[1]).getroot()
except Exception as e:
    print('no results',e); sys.exit(0)
print({k:r.get(k) for k in ('result','total','passed','failed','inconclusive','skipped')})
for tc in r.iter('test-case'):
    if tc.get('result') not in ('Passed',):
        msg=tc.find('.//message'); print(tc.get('result'),tc.get('fullname'),(msg.text or '')[:400] if msg is not None else '')
PY
exit $rc
