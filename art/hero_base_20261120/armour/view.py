#!/usr/bin/env python3
"""Cut a contact sheet into viewable parts: view.py SHEET rows cols r0:r1 [c0:c1] OUT [maxw]. (uv run --with pillow)"""
import sys
from PIL import Image
src, rows, cols, rr = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
cc = sys.argv[5] if ':' in sys.argv[5] else None
out = sys.argv[6 if cc else 5]; maxw = int(sys.argv[7 if cc else 6]) if len(sys.argv) > (7 if cc else 6) else 2000
im = Image.open(src).convert('RGB'); w, h = im.size; cw, rh = w // cols, h // rows
r0, r1 = [int(x) for x in rr.split(':')]; c0, c1 = [int(x) for x in cc.split(':')] if cc else (0, cols)
im = im.crop((c0 * cw, r0 * rh, c1 * cw, r1 * rh))
if im.width > maxw: im = im.resize((maxw, im.height * maxw // im.width))
im.save(out, quality=88); print(out, im.size)
