#!/bin/bash
# Derived market textures from CC0 Poly Haven maps: tinted canvases, kilim rugs, painted signs.
set -e
cd "$(dirname "$0")"
T=sources/textures; O=textures; mkdir -p $O
LIN=$T/rough_linen/rough_linen_diff_1k.jpg
# Sun-bleached canvas tints (multiply over a lightened linen base)
tint() { magick $LIN -modulate 115,20 -colorspace sRGB \( -size 1024x1024 xc:"$2" \) -compose Multiply -composite -quality 90 $O/canvas_$1.jpg; }
tint cream  "#e8dcc4"; tint rust "#a4523a"; tint ochre "#c79a4e"; tint indigo "#56657a"; tint olive "#7d7a55"; tint stripe_base "#d8c8a8"
# Striped awning canvas (faded red/cream ticking)
magick $LIN -modulate 120,15 -colorspace sRGB -type TrueColor \( -size 1024x1024 xc:"#dccbb0" -fill "#9c4432" -draw "rectangle 0,0 170,1024" -draw "rectangle 341,0 511,1024" -draw "rectangle 682,0 852,1024" -blur 0x0.8 \) \
  -compose Multiply -composite -type TrueColor -quality 90 $O/canvas_stripe.jpg
# Kilim rugs: geometric bands and diamonds multiplied over dirty carpet texture
CAR=$T/dirty_carpet/dirty_carpet_diff_1k.jpg
rug() { # name bg band1 band2 accent
 magick -size 1024x1024 xc:"$2" \
  -fill "$3" -draw "rectangle 0,60 1024,150" -draw "rectangle 0,874 1024,964" \
  -fill "$4" -draw "rectangle 0,180 1024,215" -draw "rectangle 0,809 1024,844" \
  -fill "$5" -draw "polygon 512,300 700,512 512,724 324,512" -fill "$2" -draw "polygon 512,380 630,512 512,644 394,512" \
  -fill "$4" -draw "polygon 512,440 575,512 512,584 449,512" \
  -fill "$3" -draw "polygon 120,420 200,512 120,604 40,512" -draw "polygon 904,420 984,512 904,604 824,512" \
  -colorspace sRGB -type TrueColor \( $CAR -colorspace Gray -auto-level +level 62%,100% -colorspace sRGB \) -compose Multiply -composite -type TrueColor -quality 90 $O/rug_$1.jpg
}
rug crimson "#8e2a22" "#e0c9a0" "#2b2622" "#c8872f"
rug indigo  "#34405e" "#d9c49b" "#8e3325" "#c49a4a"
rug ochre   "#b07a35" "#5a2a20" "#e6d6b4" "#3b4a5c"
# Painted signs on weathered planks: name text colour
PL=$T/weathered_planks/weathered_planks_diff_2k.jpg
sign() {
 magick $PL -resize 1024x1024! -crop 1024x384+0+${4:-200} +repage -modulate 80,70 \
  \( -size 1024x384 xc:none -font sources/fonts/Rye-Regular.ttf -pointsize ${5:-120} -fill "$3" -gravity center -annotate +0+6 "$2" \
     \( -size 1024x384 plasma:gray50-gray50 -colorspace Gray -blur 0x1.5 -threshold 30% -alpha copy \) -compose DstIn -composite \) \
  -compose Over -composite -type TrueColor -quality 90 $O/sign_$1.jpg
}
sign produce "FRESH PRODUCE" "#e9dcc0" 120 110
sign water "WATER - CLAY" "#d9e2e0" 300 118
sign tools "SCRAP & TOOLS" "#e4a24a" 500 118
sign cloth "CLOTH - RUGS" "#f0e2c6" 650 124
sign rations "RATIONS" "#e05a3c" 100 170
sign chow "HOT CHOW" "#f2c14e" 420 150
# Price chalk slates
slate() { magick -size 512x384 xc:"#2a2c2e" \( -size 512x384 plasma:gray40-gray60 -colorspace Gray -blur 0x3 -colorspace sRGB \) -compose Overlay -composite -compose Over \
  -font sources/fonts/Rye-Regular.ttf -pointsize 58 -fill "#e8e4da" -gravity center -annotate +0-60 "$2" -pointsize 70 -annotate +0+50 "$3" \
  -bordercolor "#6b4a2e" -border 24 -resize 512x384! -quality 90 $O/slate_$1.jpg; }
slate a "FRUIT" "1 cr"; slate b "WATER" "2 cr/L"; slate c "TINS" "1 cr"
# Dried meat / jerky albedo from leather
magick $T/brown_leather/brown_leather_albedo_1k.jpg -modulate 70,140,95 -fill "#5a1e14" -colorize 35% -quality 90 $O/jerky.jpg
echo done; ls $O
