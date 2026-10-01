#!/usr/bin/env bash
# Alternating A/B frame-time runs of the perimeter walls (1 Oct 2026): two pinned player builds (walls root on / off,
# otherwise identical scenes), the same review camera, 13:00, 8 s profile per run, alternating on/off so this desktop's
# ±1-1.5 ms drift between runs shows up in both arms. Usage: ab_runs.sh <OUTROOT> <cam> [rounds]
set -u
O=/home/teknetik/.local/state/ward-programme
B=/home/teknetik/code/ao2/unity/AthenHill/Builds
OUT="$1"; CAM="$2"; ROUNDS="${3:-2}"
mkdir -p "$OUT"
for r in $(seq 1 "$ROUNDS"); do
  for arm in on off; do
    if [ $(( r % 2 )) -eq 0 ]; then arm=$([ "$arm" = on ] && echo off || echo on); fi
    d="$OUT/$CAM-$arm-$r"
    echo "$(date +%T) $d load $(cut -d' ' -f1-3 /proc/loadavg) $(grep some /proc/pressure/memory)" >> "$OUT/conditions.txt"
    "$O/native.sh" lookbook "$d" --cams "$CAM" --hours 13 --profile 8 --exe "$B/pw-ab-$arm/AthenHill.x86_64" > "$d.out" 2>&1
    tail -1 "$d.out"
  done
done
