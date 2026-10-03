"""Contact sheet: python sheet.py out.jpg img1 img2 ... (2 columns, 960 px wide tiles)."""
import sys, os
from PIL import Image, ImageDraw
out, fs = sys.argv[1], sys.argv[2:]
W = 960
tiles = []
for f in fs:
    t = Image.open(f).convert("RGB"); h = int(t.height * W / t.width); t = t.resize((W, h))
    ImageDraw.Draw(t).text((8, 8), os.path.basename(f), fill=(255, 255, 0)); tiles.append(t)
H = max(t.height for t in tiles)
im = Image.new("RGB", (W * 2, H * ((len(tiles) + 1) // 2)))
for i, t in enumerate(tiles):
    im.paste(t, ((i % 2) * W, (i // 2) * H))
im.save(out, quality=85)
