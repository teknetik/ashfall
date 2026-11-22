#!/usr/bin/env bash
# One NPC, stage by stage. make.sh views|project|build|review NAME [VERSION]
set -euo pipefail
H=$(cd "$(dirname "$0")" && pwd); R=$(cd "$H/../.." && pwd)
B=~/.local/state/ward-programme/showcase-phase2-20261120/blender.sh
s=$1; n=$2; v=${3:-v1}; M=$H/rodin/$n/$v/model.glb; F=$H/face/$n; O=$H/build/out/$n
mkdir -p "$F" "$O"
case $s in
views)
  $B "$R/art/hero_base_20261120/face/face_views.py" -- "$M" "$F" --ortho 0.31 --dz -0.016 | grep -E 'VIEWS OK|Error'
  for x in front left45 right45; do
    magick "$F/view_$x.png" -background '#808080' -flatten -resize 1536x1536 -colorspace sRGB -type TrueColor "$F/in_$x.png"
  done
  magick "$F"/in_front.png "$F"/in_left45.png "$F"/in_right45.png -resize 520x520 +append "$F/in_sheet.jpg" ;;
project)
  $B "$H/face/project.py" -- "$M" "$F" "$O/tex" ${4:-} | grep -E 'PROJECT OK|Error' ;;
build)
  $B "$H/build/build_npc.py" -- "$H/rig/$n/$v/rigged.glb" "$O/tex" "$O/rigged_fixed.glb" "${n^}" | grep -E 'BUILD OK|Error'
  a=(); for c in "$H/rig/$n/$v"/idle_*.glb "$H/rig/$n/$v"/talk_*.glb "$H/rig/$n/$v"/walk_*.glb; do [ -f "$c" ] && a+=("$c=$(basename "$c" .glb)"); done
  python3 "$H/build/clips.py" "$O/rigged_fixed.glb" "$O/anim_only" "${a[@]}" ;;
review)
  $B "$H/build/inspect.py" -- "$O/rigged_fixed.glb" "$O/r" | grep -E 'INSPECT|Error'
  magick "$O"/r_front.png "$O"/r_quarter.png "$O"/r_back.png "$O"/r_face.png "$O"/r_face_q.png +append -resize 1900x "$O/sheet.jpg" ;;
esac
