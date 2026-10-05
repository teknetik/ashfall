#!/usr/bin/env bash
set -uo pipefail
cd /home/teknetik/code/ao2
. /home/teknetik/.local/state/ward-programme/lib.sh
exec 9>"$W/unity.lock"
flock -w 5400 9
wait_for_user_player 'character motion review'
BEFORE=unity/AthenHill/Builds/character-before-20261005/AthenHill.x86_64
AFTER=unity/AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64
E=unity/evidence/character-polish/20261005
if [[ ! -f "$E/motion-before/motion-report.json" ]]; then
 run_capped player 8G 1G uv run --offline --with python-xlib --with pillow python art/character_polish_20261005/native_motion.py "$E/motion-before" "$BEFORE" || exit $?
fi
run_capped player 8G 1G uv run --offline --with python-xlib --with pillow python art/character_polish_20261005/native_motion.py "$E/motion-after" "$AFTER" || exit $?
run_capped player 8G 1G uv run --offline --with python-xlib --with pillow python art/character_polish_20261005/native_motion.py "$E/profile-after-2" "$AFTER" --profile-only || exit $?
run_capped player 8G 1G uv run --offline --with python-xlib --with pillow python art/character_polish_20261005/native_motion.py "$E/profile-before-2" "$BEFORE" --profile-only || exit $?
run_capped player 8G 1G uv run --offline --with python-xlib --with pillow python unity/tools/lookbook.py "$E/after" --cams cam_player_face_20261003_body_front,cam_player_face_20261003_follow_back,cam_player_face_20261003_face_quarter,cam_hill,cam_avenue,cam_gate --hours 13,20.5 --sheet || exit $?
