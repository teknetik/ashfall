#!/usr/bin/env bash
# Starts the development build only once the machine has room for it (a player build needs ~14-15 GB; on 5 Oct 01:15 two
# attempts were killed by the ward watchdog at MemAvailable < 1.2 GB with ~12 GB free). Polls every 60 s for up to 4 h.
set -u
R=/home/teknetik/code/ao2; EV=$R/unity/evidence/field-supply/20261005; LOG=$EV/wait_build.out
for i in $(seq 1 240); do
  avail=$(awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo)
  if [ "$avail" -ge 15 ]; then
    echo "$(date +%H:%M:%S) MemAvailable ${avail} GB: building" >> $LOG
    /home/teknetik/.local/state/ward-programme/build_player.sh $EV/build.log >> $LOG 2>&1; rc=$?
    echo "$(date +%H:%M:%S) build rc=$rc" >> $LOG
    [ $rc -eq 0 ] && exit 0
    sleep 300
  else
    [ $((i % 10)) -eq 1 ] && echo "$(date +%H:%M:%S) waiting: MemAvailable ${avail} GB" >> $LOG
    sleep 60
  fi
done
echo "$(date +%H:%M:%S) gave up" >> $LOG; exit 1
