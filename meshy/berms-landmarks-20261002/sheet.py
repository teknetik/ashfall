"""Contact sheet: uv run --with pillow python sheet.py OUT.jpg COLS IMG... (each tile 480 px wide, labelled)."""
import sys
from PIL import Image, ImageDraw
out, cols, files = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
W = 480
tiles = []
for f in files:
    im = Image.open(f).convert('RGB'); h = int(im.height * W / im.width); im = im.resize((W, h))
    ImageDraw.Draw(im).text((6, 4), f.split('/')[-1], fill=(255, 255, 0))
    tiles.append(im)
rows = [tiles[i:i + cols] for i in range(0, len(tiles), cols)]
H = [max(t.height for t in r) for r in rows]
sheet = Image.new('RGB', (W * cols, sum(H)), (30, 30, 30))
y = 0
for r, h in zip(rows, H):
    for i, t in enumerate(r): sheet.paste(t, (i * W, y))
    y += h
sheet.save(out, quality=85); print(out, sheet.size)
