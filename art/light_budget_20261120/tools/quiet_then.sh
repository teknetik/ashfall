#!/usr/bin/env bash
# Wait (max QUIET_MAX checks of 10 s, default 360 = 60 min) until no other ward Blender/heavy/Unity scope runs and swap is under
# QUIET_SWAP MB (default 23000) for three checks running, then run "$@". If it never gets quiet, exit 75 without running it.
n=0; t=0
MAX=${QUIET_MAX:-360}; LIM=${QUIET_SWAP:-23000}
while [ $t -lt $MAX ]; do
  s=$(free -m | awk '/Swap/{print $3}')
  busy=$(systemctl --user list-units --type=scope --state=running --no-legend 2>/dev/null | grep -cE 'ward-(heavy|blender|unity|build|native)')
  if [ "$busy" = 0 ] && [ "$s" -lt "$LIM" ]; then n=$((n+1)); else n=0; fi
  [ $n -ge 3 ] && break
  t=$((t+1)); sleep 10
done
echo "$(date +%T) quiet_then: swap=${s}MB busy=$busy waited=$((t*10))s"
[ $n -ge 3 ] || { echo "never quiet: not running $*"; exit 75; }
exec "$@"
