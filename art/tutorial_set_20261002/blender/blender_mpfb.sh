#!/usr/bin/env bash
# Headless Blender 5.2 WITH user extensions (MPFB2), capped like ward-programme/blender.sh. Usage: blender_mpfb.sh script.py [-- args]
set -u; . /home/teknetik/.local/state/ward-programme/lib.sh
while :; do
  for s in 1 2; do
    exec {fd}>"/home/teknetik/.local/state/ward-programme/blender-$s.lock"
    if flock -n $fd; then
      run_capped blender 6G 1G timeout 3600 env -i HOME=$HOME PATH=/usr/bin:/bin blender -b --python-exit-code 1 -P "$@"
      exit $?
    fi
    exec {fd}>&-
  done
  sleep 5
done
