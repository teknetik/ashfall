#!/usr/bin/env bash
# Mastheads in the project's sign font (Noto Sans Black/Bold, OFL; art/hall_district_20260930/fonts) over the generated
# cover art, then a 2048 x 2048 screen atlas (four 512 x 768 covers across the top, the 256 px FIELD READS band under them) that
# the magazine shelf's slate screens map into (cover i: u i/4..(i+1)/4, v 0.625-1; band v 0.5-0.625). Square, so one box
# projection scale per screen keeps the 2:3 covers undistorted (field_supply_interior.py _screen).
set -eu; cd "$(dirname "$0")"
F=../../hall_district_20260930/fonts
cover() {  # name title subtitle issue fg band
  local n=$1 t=$2 s=$3 i=$4 fg=$5 band=$6
  magick "${n}_art.png" -resize 1024x1536^ -gravity center -extent 1024x1536 \
    \( -size 1024x300 xc:none -fill "$band" -draw "rectangle 0,0 1024,300" \) -gravity north -compose over -composite \
    -font "$F/NotoSans-Black.ttf" -fill "$fg" -pointsize 112 -gravity north -annotate +0+40 "$t" \
    -font "$F/NotoSans-Bold.ttf" -pointsize 44 -annotate +0+176 "$s" \
    -font "$F/NotoSans-Bold.ttf" -pointsize 40 -fill "$fg" -gravity south \
    \( -size 1024x110 xc:none -fill "rgba(10,14,14,0.55)" -draw "rectangle 0,0 1024,110" \) -compose over -composite \
    -fill "#efe6d4" -annotate +0+30 "$i" -resize 512x768 "${n}_cover.png"
}
cover packcraft "PACKCRAFT" "QUARTERLY  ·  FIELD-SEWN GEAR" "ISSUE 12  ·  RUCKSACK · POUCHES · HIP BELT" "#2b1d12" "rgba(226,203,160,0.92)"
cover freight   "KARAVEEN" "FREIGHT NOTES  ·  VOL. 3" "FRAME PACK · PORTER'S LOAD CARRIER" "#f3e2c4" "rgba(120,52,22,0.90)"
cover nanoweave "NANOWEAVE" "MONTHLY  ·  LOAD TECH" "EXPANSION POUCH · SERVO LIFTER · CARGO RIG" "#d8fbf8" "rgba(18,58,62,0.92)"
cover armourer  "ARMOURER'S" "WARD DIGEST  ·  LINERS & PLATES" "IMPACT · THERMAL · ABLATIVE" "#f4efe6" "rgba(78,84,88,0.92)"
magick -size 2048x2048 xc:"#0b1416" \
  packcraft_cover.png -geometry +0+0 -composite freight_cover.png -geometry +512+0 -composite \
  nanoweave_cover.png -geometry +1024+0 -composite armourer_cover.png -geometry +1536+0 -composite \
  \( -size 2048x256 gradient:"#0f4247"-"#051c1f" \) -geometry +0+768 -composite \
  -font "$F/NotoSans-Black.ttf" -fill "#9ff4f0" -pointsize 120 -gravity northwest -annotate +80+824 "FIELD READS" \
  -font "$F/NotoSans-Bold.ttf" -pointsize 46 -fill "#d6c49a" -gravity northeast -annotate +90+880 "DIGITAL ISSUES · DOWNLOAD AT THE COUNTER" \
  magazine_atlas.png
magick identify magazine_atlas.png
