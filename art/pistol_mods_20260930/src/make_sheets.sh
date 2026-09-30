#!/bin/bash
# Contact sheets from review/*.png (ImageMagick). Each tile is labelled; FP = in-game hip eye (crop of a 2880x1620
# render at the in-game 50 deg vertical FOV), 3/4 = inspection camera.
set -e
cd "$(dirname "$0")/../review"
F=Liberation-Sans
lab() { magick "$1" -resize x520 -gravity NorthWest -fill '#f4efe6' -undercolor '#000000a0' -font $F -pointsize 20 -annotate +8+8 " $2 " "$3"; }
T=$(mktemp -d)
for m in grip_stabilised_pistol grip_gyro_braced barrel_bored_alloy barrel_lattice_focused cell_salvaged_capacitor cell_overclocked; do
  lab ${m}_fp_sun.png "$m  FP hip, warm sun" $T/a.png
  lab ${m}_34_sun.png "3/4, warm sun" $T/b.png
  lab ${m}_fp_shade.png "FP hip, open shade" $T/c.png
  lab ${m}_34_shade.png "3/4, open shade" $T/d.png
  magick \( $T/a.png $T/b.png +append \) \( $T/c.png $T/d.png +append \) -background '#202020' -append sheet_${m}.png
done
for c in mk1 mk2; do
  lab combo_${c}_fp_sun.png "all $c  FP hip, warm sun" $T/a.png
  lab combo_${c}_34_sun.png "left, warm sun" $T/b.png
  lab combo_${c}_rear_sun.png "rear-left, warm sun" $T/e.png
  lab combo_${c}_fp_shade.png "FP hip, open shade" $T/c.png
  lab combo_${c}_34_shade.png "left, open shade" $T/d.png
  lab combo_${c}_rear_shade.png "rear-left, open shade" $T/f.png
  magick \( $T/a.png $T/b.png $T/e.png +append \) \( $T/c.png $T/d.png $T/f.png +append \) -background '#202020' -append sheet_combo_${c}.png
done
for c in stock mk1 mk2; do lab fullframe_${c}_fp_sun.png "in-game hip frame 1920x1080: $c" $T/$c.png; done
magick $T/stock.png $T/mk1.png $T/mk2.png +append sheet_fullframe.png
rm -rf $T
ls -1 sheet_*.png
