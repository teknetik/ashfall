#!/usr/bin/env bash
# Showcase phase 2: build p2-NAME once the named install runs have finished (whatever their result), so the build
# contains them. Usage: build_after.sh NAME INSTALL_RUN [INSTALL_RUN ...]     e.g. build_after.sh b3 berms_variety-10
# Waits up to 40 minutes for the runs to appear in the phase 2 progress log, then calls build_to.sh (which itself
# waits while Carl's game is running and for a tree that compiles).
set -u; P2=/home/teknetik/.local/state/ward-programme/showcase-phase2-20261120; NAME="$1"; shift
end=$(( $(date +%s) + 2400 ))
for run in "$@"; do
  until grep -q "install $run rc=" "$P2/progress.log"; do
    [ "$(date +%s)" -gt "$end" ] && { echo "gave up waiting for install $run"; break; }
    sleep 10
  done
  grep "install $run rc=" "$P2/progress.log" | tail -1
done
exec "$P2/build_to.sh" "p2-$NAME"
