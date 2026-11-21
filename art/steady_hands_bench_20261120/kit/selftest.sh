#!/usr/bin/env bash
# Kit self-test after a kit change: the example family builds, bakes small and passes its checks. (It runs no
# other family's check: a check rewrites that family's export/check.json, which belongs to its owner.) Usage: SH/run.sh kit-selftest bash kit/selftest.sh ; SH/wait.sh kit-selftest
SH=~/.local/state/ward-programme/steady-hands-20261120
cd "$(dirname "$0")/.." || exit 2
rc=0
$SH/blender.sh kit/example/build.py -- --size 512 --spp 8 2>&1 | grep -E "example |Error|Traceback|line " ; [ "${PIPESTATUS[0]}" = 0 ] || rc=1
$SH/blender.sh kit/example/check.py 2>&1 | grep -E "^CHECK|^   |Error|Traceback|line " ; [ "${PIPESTATUS[0]}" = 0 ] || rc=1
echo "kit selftest rc=$rc"; exit $rc
