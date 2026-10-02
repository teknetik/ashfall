#!/usr/bin/env bash
# EditMode tests through the Ward programme's Unity lock and memory cap (no -quit with -runTests).
# Usage: run_tests.sh <out-dir> [filter]
set -u; . /home/teknetik/.local/state/ward-programme/lib.sh
OUT="$1"; FILTER="${2:-}"; mkdir -p "$OUT"
cd /home/teknetik/code/ao2
EXTRA=(); [ -n "$FILTER" ] && EXTRA=(-testFilter "$FILTER")
flock -w 5400 "$W/unity.lock" bash -c '. /home/teknetik/.local/state/ward-programme/lib.sh; run_capped unity 17G 3G timeout 3600 /home/teknetik/Unity/Hub/Editor/6000.6.0f1/Editor/Unity -batchmode -nographics -projectPath unity/AthenHill -runTests -testPlatform EditMode "$@"' _ -testResults "$OUT/editmode.xml" -logFile "$OUT/editmode.log" "${EXTRA[@]}"
echo "exit $?"
python3 - "$OUT/editmode.xml" <<'PY'
import sys,xml.etree.ElementTree as E
try: r=E.parse(sys.argv[1]).getroot()
except Exception as e: print("no results:",e); sys.exit(1)
print({k:r.get(k) for k in ("total","passed","failed","skipped","result")})
for t in r.iter("test-case"):
    if t.get("result")!="Passed":
        m=t.find(".//message"); print("FAIL",t.get("fullname"),(m.text or "")[:400] if m is not None else "")
PY
