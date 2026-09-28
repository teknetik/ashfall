#!/bin/bash
# Derived retrofit textures from CC0 Poly Haven maps plus original stencils/decals (ImageMagick 7).
# Lettering: Nimbus Sans Narrow Bold (URW base35, rasterised only; the font is not shipped).
set -e
cd "$(dirname "$0")"
T=sources/textures; O=textures; mkdir -p $O
FONT=/usr/share/fonts/gsfonts/NimbusSansNarrow-Bold.otf
CON=$T/container_side/container_side_diff_2k.jpg
# Faded container paints: greyscale detail multiplied with a sun-bleached paint colour
paint() { magick $1 -colorspace Gray -auto-level +level 45%,100% -colorspace sRGB \( -size 2048x2048 xc:"$3" \) -compose Multiply -composite -type TrueColor -quality 90 $O/$2.jpg; }
paint $CON container_rust "#9a4a33"; paint $CON container_blue "#5b7282"; paint $CON container_sand "#b59a6e"; paint $CON container_olive "#6f7152"
# Corporate panel paint: faded teal-grey over the blue plate detail, and a bone white variant
paint $T/blue_metal_plate/blue_metal_plate_diff_2k.jpg plate_teal "#6f8c8a"
paint $T/blue_metal_plate/blue_metal_plate_diff_2k.jpg plate_bone "#c9c0ad"
paint $T/metal_plate_02/metal_plate_02_diff_2k.jpg panel_graphite "#7a7b7a"
# HESCO-style barrier: khaki geotextile with welded wire grid
magick /home/teknetik/code/ao2/art/karaveen_market_20260926/sources/textures/hessian_230/hessian_230_diff_1k.jpg -modulate 95,35 \
  \( -size 1024x1024 xc:"#b8aa86" \) -compose Multiply -composite \
  -stroke "#3a3a36" -strokewidth 5 -fill none $(for i in 0 128 256 384 512 640 768 896; do echo "-draw \"line $i,0 $i,1024\" -draw \"line 0,$i 1024,$i\""; done | tr '\n' ' ' | xargs -0 echo) \
  -type TrueColor -quality 90 $O/hesco.jpg 2>/dev/null || \
magick /home/teknetik/code/ao2/art/karaveen_market_20260926/sources/textures/hessian_230/hessian_230_diff_1k.jpg -modulate 95,35 \( -size 1024x1024 xc:"#b8aa86" \) -compose Multiply -composite -type TrueColor $O/hesco_base.jpg
if [ ! -f $O/hesco.jpg ]; then
  args=(); for i in 0 128 256 384 512 640 768 896; do args+=(-draw "line $i,0 $i,1024" -draw "line 0,$i 1024,$i"); done
  magick $O/hesco_base.jpg -stroke "#3a3a36" -strokewidth 5 -fill none "${args[@]}" -type TrueColor -quality 90 $O/hesco.jpg; rm -f $O/hesco_base.jpg
fi
# Worn hazard stripes
RUST=$T/rusty_metal_04/rusty_metal_04_diff_2k.jpg
magick -size 1024x1024 xc:"#c9a227" -fill "#1d1b18" -draw "polygon 0,0 180,0 1024,844 1024,1024 844,1024 0,180" \
  -draw "polygon 360,0 540,0 1024,484 1024,664" -draw "polygon 0,360 0,540 484,1024 664,1024" -draw "polygon 720,0 900,0 1024,124 1024,304" -draw "polygon 0,720 0,900 124,1024 304,1024" \
  \( $RUST -resize 1024x1024! -colorspace Gray -auto-level +level 35%,100% -colorspace sRGB \) -compose Multiply -composite -type TrueColor -quality 90 $O/hazard.jpg
# Distress mask for stencils (noise, speckle)
magick -size 1024x256 xc: +noise Random -colorspace Gray -blur 0x3 -auto-level -threshold 38% -negate /tmp/ward_mask.png 2>/dev/null || true
stencil() { # name text colour width height (auto-fitted lettering, speckled paint wear)
  magick -background none -fill "$3" -font $FONT -size $(( $4 * 94 / 100 ))x$(( $5 * 88 / 100 )) -gravity center label:"$2" -gravity center -extent ${4}x${5} /tmp/ward_txt.png
  magick -size ${4}x${5} xc: +noise Random -colorspace Gray -blur 0x2.4 -auto-level -threshold 33% /tmp/ward_spk.png
  magick /tmp/ward_txt.png \( /tmp/ward_txt.png -alpha extract /tmp/ward_spk.png -compose Multiply -composite \) -compose CopyAlpha -composite PNG32:$O/stencil_$1.png
}
stencil fab2 "NANOFAB 2" "#e6e1d2" 1024 256
stencil fab2b "AUTHORISED ACCESS ONLY" "#d8c35a" 1024 128
stencil aquifer "AQUIFER 3 · PUMP HOUSE" "#e6e1d2" 1024 160
stencil hydroA "HYDRO BAY A" "#e6e1d2" 1024 200
stencil hydroB "HYDRO BAY B" "#e6e1d2" 1024 200
stencil node "NODE 07 · GOODS ONLY" "#bfe9ee" 1024 160
stencil proc "PROCESSING 11" "#d9d2c2" 1024 200
stencil hv "DANGER · HIGH VOLTAGE" "#d8c35a" 1024 128
stencil potable "POTABLE · DO NOT TAP" "#bfe0ee" 1024 128
stencil watch1 "WATCH 1" "#e6e1d2" 512 160
stencil watch2 "WATCH 2" "#e6e1d2" 512 160
stencil watch3 "WATCH 3" "#e6e1d2" 512 160
stencil watch4 "WATCH 4" "#e6e1d2" 512 160
# Faded company sigil (abstract hexagon/chevron mark with registry numbers) on transparent background
magick -size 1024x1024 xc:none -fill none -stroke "#ddd6c4" -strokewidth 46 -draw "polygon 512,90 877,301 877,723 512,934 147,723 147,301" \
  -fill "#ddd6c4" -stroke none -draw "polygon 512,250 740,640 620,640 512,450 404,640 284,640" -draw "rectangle 300,700 724,760" /tmp/ward_sig.png
magick -size 1024x1024 xc: +noise Random -colorspace Gray -blur 0x5 -auto-level -threshold 42% /tmp/ward_spk.png
magick /tmp/ward_sig.png \( /tmp/ward_sig.png -alpha extract /tmp/ward_spk.png -compose Multiply -composite -evaluate multiply 0.75 \) -compose CopyAlpha -composite PNG32:$O/sigil.png
# Warden banner: faded olive cloth, bone wall-and-spire emblem, frayed hem
CL=/home/teknetik/code/ao2/art/karaveen_market_20260926/sources/textures/rough_linen/rough_linen_diff_1k.jpg
magick $CL -resize 512x1024! -modulate 90,25 \( -size 512x1024 xc:"#4d5238" \) -compose Multiply -composite \
  -fill "#2d2a24" -draw "rectangle 0,0 512,70" -draw "rectangle 0,950 512,1024" \
  -fill "#d6ccb4" -draw "polygon 256,230 296,330 296,560 216,560 216,330" -draw "rectangle 120,560 392,620" \
  -draw "rectangle 120,500 150,560" -draw "rectangle 190,500 220,560" -draw "rectangle 292,500 322,560" -draw "rectangle 362,500 392,560" \
  -fill "#8a3a2a" -draw "rectangle 0,660 512,690" -type TrueColor -quality 90 $O/warden_banner.jpg
# Scorch / blast scar (RGBA): dark soot, irregular edge
magick -size 1024x1024 radial-gradient:white-black \( -size 1024x1024 xc: +noise Random -colorspace Gray -blur 0x9 -auto-level \) -compose Multiply -composite -level 4%,55% /tmp/ward_sc.png
magick -size 1024x1024 xc:"#17130f" /tmp/ward_sc.png -compose CopyAlpha -composite PNG32:$O/scorch.png
# Bullet/shrapnel pocks (RGBA)
args=(); for i in $(seq 1 70); do x=$((RANDOM%1000+12)); y=$((RANDOM%1000+12)); r=$((RANDOM%9+4)); args+=(-draw "circle $x,$y $((x+r)),$y"); done
magick -size 1024x1024 xc:none -fill "#16130fe0" "${args[@]}" -blur 0x1.2 PNG32:$O/pocks.png
# Rust/grime streaks (RGBA) for under vents, pipes and roof edges
magick -size 512x1024 xc: +noise Random -colorspace Gray -motion-blur 0x120+90 -auto-level -level 25%,90% \( -size 512x1024 gradient:white-black \) -compose Multiply -composite /tmp/ward_st.png
magick -size 512x1024 xc:"#4a2c1a" /tmp/ward_st.png -compose CopyAlpha -composite PNG32:$O/streaks.png
# Grow-light panel glow (magenta/white LED rows) for hydroponic interiors
magick -size 256x256 xc:"#2a1a2c" -fill "#f0a8e8" -draw "rectangle 0,40 256,70" -draw "rectangle 0,168 256,198" -blur 0x3 -type TrueColor $O/growlight.jpg
rm -f /tmp/ward_*.png
ls $O
# Vertical lit blade signs: pale lettering on a dark acrylic face (used as base colour + emission map)
blade() { # name text colour
  magick -size 1024x256 xc:"#101418" -background none -fill "$3" -font $FONT -size 940x220 -gravity center label:"$2" -gravity center -compose Over -composite \
    -rotate 90 -type TrueColor $O/blade_$1.jpg
}
blade relay "RELAY" "#9fe8f2"; blade water "WATER" "#9fe8f2"; blade tools "TOOLS" "#ffc27a"; blade salvage "SALVAGE" "#ffc27a"
blade finery "FINERY" "#f2b3e0"; blade supply "SUPPLY" "#9fe8f2"; blade repairs "REPAIRS" "#ffc27a"; blade thread "THREAD" "#f2b3e0"
