#!/usr/bin/env bash
# Samples total GPU memory and the AthenHill player's own GPU memory every 2 s until the player has come and gone
# (or <max seconds>). Usage: vram_sampler.sh <out.csv> [max seconds, default 900]
out="$1"; max="${2:-900}"; t0=$(date +%s); seen=0
echo "t,total_mib,player_mib" > "$out"
while :; do
  now=$(( $(date +%s) - t0 )); [ $now -gt $max ] && break
  total=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -dc 0-9)
  player=$(nvidia-smi 2>/dev/null | awk '/AthenHill/ {gsub("MiB","",$(NF-1)); print $(NF-1)}' | head -1)
  if [ -n "$player" ]; then seen=1; elif [ $seen = 1 ]; then break; fi
  echo "$now,${total:-},${player:-}" >> "$out"; sleep 2
done
