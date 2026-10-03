#!/usr/bin/env bash
cd "$(dirname "$0")"
declare -A POLY=([helmet]=20000 [chest]=30000 [bracer]=12000 [kneeshin]=16000 [bootplates]=12000 [glove]=12000)
for n in helmet chest bracer kneeshin bootplates glove; do
  until [ -f pieces/$n.png ]; do grep -q ALLDONE pieces/gen.out 2>/dev/null && break; sleep 10; done
  [ -f pieces/$n.png ] || { echo "$n no image"; continue; }
  python3 meshy_job.py image3d $n pieces/$n.png ${POLY[$n]} > meshy_$n.log 2>&1 &
  echo "$n launched"
done
wait; echo MESHYALL
