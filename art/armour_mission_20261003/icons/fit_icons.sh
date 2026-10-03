#!/usr/bin/env bash
# Trim the 1024 px Codex icons and fit them to the 192 x 192 item-icon canvas (transparent, ~8 px margin).
# apply_data.py installs <id>.192.png as UI/Art/{webbing,liner,rivets}.png.
set -eu; cd "$(dirname "$0")"
for id in strap_webbing padded_liner rivet_stock; do
  magick "$id.png" -trim +repage -filter Lanczos -resize 176x176 -background none -gravity center -extent 192x192 -strip "PNG32:$id.192.png"
done
magick identify *.192.png
