#!/usr/bin/env bash
# Next-level enemies pass (2 Oct 2026): re-runnable install. 1) catalog/USS/objective text patches, 2) the Unity Editor
# install (import, visual + gameplay prefabs, loot tables, scene POIs, verify) under the shared lock, 3) a graphics capture
# of the six cam_nextlevel_* review cameras (droid visuals stood at their spawns) and a contact sheet.
# Usage: art/next_level_20261002/enemies/install.sh [all|data|unity|capture]
set -u; R=/home/teknetik/code/ao2; EV=$R/unity/evidence/next-level/20261002/enemies; W=/home/teknetik/.local/state/ward-programme; cd "$R"; mkdir -p "$EV"
step=${1:-all}
if [[ $step == all || $step == data ]]; then uv run --offline --with pyyaml python art/next_level_20261002/enemies/apply_data.py; fi
if [[ $step == all || $step == unity ]]; then
  "$W/unity.sh" "$EV/install.log" AthenHill.Editor.NextLevelEnemiesInstall.InstallAll -nographics -quit; rc=$?
  grep -h "NextLevelEnemiesInstall " "$EV/install.log" | tail -8; [[ $rc == 0 ]] || { echo "install rc=$rc"; exit $rc; }
fi
if [[ $step == all || $step == capture ]]; then
  export DISPLAY=:0 WAYLAND_DISPLAY=wayland-1
  "$W/unity.sh" "$EV/capture.log" AthenHill.Editor.NextLevelEnemiesInstall.RunBatch -quit --steps "capture:$EV/editor:cam_nextlevel_post_relay+cam_nextlevel_reaper_den+cam_nextlevel_ironclad_camp+cam_nextlevel_southern_cache+cam_nextlevel_sentinel_close+cam_nextlevel_ironclad_close"; rc=$?
  [[ $rc == 0 ]] || { echo "capture rc=$rc"; exit $rc; }
  magick montage "$EV"/editor/cam_nextlevel_*.png -tile 3x2 -geometry 640x360+4+4 -title "next-level enemies review cameras, editor capture" "$EV/editor/contact-sheet.png" && echo "sheet: $EV/editor/contact-sheet.png"
fi
