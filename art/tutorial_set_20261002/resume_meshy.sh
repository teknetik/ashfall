#!/usr/bin/env bash
# Waits for Meshy credits, then (re)starts any piece that has an image but no task yet.
cd "$(dirname "$0")"
K=$(grep ^MESHY_API_KEY= /home/teknetik/code/ao2/.env | cut -d= -f2- | tr -d "\"'")
declare -A POLY=([chest]=30000 [bracer]=12000 [kneeshin]=16000 [bootplates]=12000 [glove]=12000)
for n in chest bracer kneeshin bootplates glove; do
  until [ -f pieces/$n.png ]; do sleep 20; done
  M=/home/teknetik/code/ao2/meshy/tutorial-set-20261002/$n/manifest.json
  if [ -f $M ] && grep -q '"task"' $M; then echo "$n has task"; continue; fi
  until [ "$(curl -s -H "Authorization: Bearer $K" https://api.meshy.ai/openapi/v1/balance | python3 -c 'import sys,json;print(json.load(sys.stdin)["balance"])')" -ge 30 ]; do sleep 60; done
  rm -f $M
  python3 meshy_job.py image3d $n pieces/$n.png ${POLY[$n]} > meshy_$n.log 2>&1 &
  echo "$n launched $(date +%H:%M)"; sleep 15
done
wait; echo RESUMEALL
