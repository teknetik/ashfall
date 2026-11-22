#!/usr/bin/env bash
# NPC rebuild: install.sh backup | build [keys] | arms | verify [keys] | rollback
# backup runs automatically before the first build. rollback restores the files; run `install.sh arms` after it.
set -euo pipefail
H=$(cd "$(dirname "$0")/.." && pwd); R=$(cd "$H/../.." && pwd); A=$R/unity/AthenHill/Assets/AthenHill
P=~/.local/state/ward-programme/steady-hands-20261120; W=~/.local/state/ward-programme
B=$H/rollback/assets; LOG=$H/unity/logs; mkdir -p "$LOG"; stamp=$(date +%H%M%S)
backup() {
  [ -e "$B/.done" ] && return 0
  mkdir -p "$B/WardNpcs" "$B/prefabs"
  cp -a --reflink=auto "$A/Art/Imported/Meshy/WardNpcs/." "$B/WardNpcs/"
  cp -a "$A"/Prefabs/WardNpcs/. "$B/prefabs/WardNpcs/"
  cp -a "$A/Prefabs/SalvageDealer.prefab" "$B/prefabs/SalvageDealer.prefab"
  cp -a --reflink=auto "$A/Art/Imported/Meshy/WardWalkers" "$B/WardWalkers"
  cp -a "$A/Prefabs/WardWalkers" "$B/prefabs/WardWalkers"
  cp --reflink=auto "$A/Scenes/AthenHill.unity" "$B/AthenHill.before.unity"
  touch "$B/.done"
}
keys() { [ -n "${1:-}" ] && echo "--npcs $1" || true; }
case "${1:-}" in
backup) backup ;;
build) backup; "$W/unity.sh" "$LOG/build-$stamp.log" AthenHill.Editor.NpcRebuildPass20261122.RunBatch -nographics --steps build $(keys "${2:-}") ;;
walkers) backup; "$W/unity.sh" "$LOG/walkers-$stamp.log" AthenHill.Editor.NpcRebuildPass20261122.RunBatch -nographics --steps walkers ;;
verify) "$W/unity.sh" "$LOG/verify-$stamp.log" AthenHill.Editor.NpcRebuildPass20261122.RunBatch -nographics --steps verify $(keys "${2:-}") ;;
arms) cp --reflink=auto "$A/Scenes/AthenHill.unity" "$LOG/scene-before-arms-$stamp.unity"
      "$W/unity.sh" "$LOG/arms-$stamp.log" AthenHill.Editor.CharacterArmsPass20261120.RunBatch -nographics --steps install,verify ;;
rollback)
  [ -e "$B/.done" ] || { echo "no backup"; exit 1; }
  cp -a "$B/WardNpcs/." "$A/Art/Imported/Meshy/WardNpcs/"
  cp -a "$B/prefabs/WardNpcs/." "$A/Prefabs/WardNpcs/"
  cp -a "$B/prefabs/SalvageDealer.prefab" "$A/Prefabs/SalvageDealer.prefab"
  cp -a "$B/WardWalkers/." "$A/Art/Imported/Meshy/WardWalkers/"
  cp -a "$B/prefabs/WardWalkers/." "$A/Prefabs/WardWalkers/"
  echo "files restored; now: install.sh arms" ;;
*) sed -n 2,4p "$0"; exit 2 ;;
esac
