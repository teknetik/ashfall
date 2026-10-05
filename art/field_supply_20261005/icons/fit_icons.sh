#!/usr/bin/env bash
# Trim the 1024 px Codex icons and fit them to the 192 x 192 item-icon canvas (transparent, ~8 px margin),
# straight into UI/Art/<icon>.png (import settings: copy of UI/Art/scrap.png.meta with a fresh guid).
set -eu; cd "$(dirname "$0")"
ART=../../../unity/AthenHill/Assets/AthenHill/UI/Art
for f in *.png; do
  id=${f%.png}; case "$id" in *.192) continue;; esac
  magick "$f" -trim +repage -filter Lanczos -resize 176x176 -background none -gravity center -extent 192x192 -strip "PNG32:$id.192.png"
  cp "$id.192.png" "$ART/$id.png"
  if [ ! -f "$ART/$id.png.meta" ]; then
    sed "s/^guid: .*/guid: $(python3 -c 'import uuid;print(uuid.uuid4().hex)')/" "$ART/scrap.png.meta" > "$ART/$id.png.meta"
  fi
done
magick identify *.192.png
