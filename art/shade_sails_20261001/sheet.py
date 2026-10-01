#!/usr/bin/env python3
"""Contact sheet: sheet.py out.jpg cols width img1 img2 ... (labels = file names)."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
out, cols, w = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
imgs = sys.argv[4:]
ims = []
for p in imgs:
    im = Image.open(p).convert("RGB"); h = int(im.height * w / im.width)
    ims.append((Path(p).parent.name + "/" + Path(p).stem, im.resize((w, h), Image.LANCZOS)))
h = max(i.height for _, i in ims); rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGB", (cols * w, rows * (h + 18)), (20, 20, 20)); d = ImageDraw.Draw(sheet)
for k, (name, im) in enumerate(ims):
    x, y = (k % cols) * w, (k // cols) * (h + 18)
    sheet.paste(im, (x, y + 18)); d.text((x + 4, y + 3), name, fill=(240, 240, 200))
sheet.save(out, quality=88); print(out, sheet.size)
