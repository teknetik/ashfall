#!/usr/bin/env bash
# Second round: waits for batch.sh, then Brann's and Ossa's fixes and the three walkers.
cd "$(dirname "$0")"
while ! grep -q 'BATCH DONE' batch.log; do sleep 5; done
for n in porter nanotech grower; do ./make.sh views $n > logs/views-$n.log 2>&1; echo "$(date +%H:%M:%S) views $n rc=$?"; done
./batch.sh brann ossa porter nanotech grower
echo BATCH2 DONE
