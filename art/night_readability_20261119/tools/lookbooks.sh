#!/usr/bin/env bash
# Usage: lookbooks.sh TAG EXE HOURS [env...]   -> unity/evidence/night-readability/20261119/TAG-s{1,2,3}
set -u; R=/home/teknetik/code/ao2; cd $R
TAG=$1; EXE=$2; HOURS=$3; shift 3
EV=$R/unity/evidence/night-readability/20261119; mkdir -p $EV
S1=cam_hill,cam_avenue,cam_gate,cam_courtyard,cam_player_face_20261003_face_quarter,cam_player_face_20261003_body_front,cam_npcs_vex_face,cam_npcs_mira_body
S2=cam_npcs_mira_face,cam_npcs_torr_face,cam_npcs_linn_face,cam_npcs_ossa_face,cam_npcs_rell_face,cam_ss_brann,cam_fs_tamsin,cam_npcs_torr_body
S3=${S3:-cam_walkers_porter_face,cam_walkers_nanotech_face,cam_walkers_grower_face,cam_walkers_porter_body,cam_nl_south_lane,cam_nl_hall_corner,cam_nl_courtyard,cam_npcs_linn_body}
for s in ${SETS:-1 2 3}; do
  eval cams=\$S$s
  env -u WAYLAND_DISPLAY DISPLAY=:5 ATHEN_QA_MUTE=1 "$@" ~/.local/state/ward-programme/native.sh lookbook $EV/$TAG-s$s --cams $cams --hours $HOURS --sheet --exe $EXE > $EV/$TAG-s$s.out 2>&1
  echo "$TAG-s$s rc=$? $(tail -c 300 $EV/$TAG-s$s.out | tr '\n' ' ')"
done
