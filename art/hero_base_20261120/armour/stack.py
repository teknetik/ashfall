#!/usr/bin/env python3
"""Stack contact sheets under each other (optionally regrouping the rows of one sheet into wider rows) and limit the
width. Usage: stack.py OUT.jpg MAXW [--grid ROWS COLS --regroup N] SHEET [SHEET ...]   (uv run --with pillow)"""
import sys
from PIL import Image
a = sys.argv[1:]; out, maxw = a[0], int(a[1]); a = a[2:]; grid = None; regroup = None
if a and a[0] == '--grid': grid = (int(a[1]), int(a[2])); a = a[3:]
if a and a[0] == '--regroup': regroup = int(a[1]); a = a[2:]
ims = [Image.open(p).convert('RGB') for p in a]
if grid and regroup:                      # one sheet of ROWS x COLS -> rows of `regroup` original rows side by side
    im = ims[0]; rows, cols = grid; rh = im.height // rows; strips = [im.crop((0, r * rh, im.width, (r + 1) * rh)) for r in range(rows)]
    ims = []
    for r in range(0, rows, regroup):
        g = strips[r:r + regroup]; c = Image.new('RGB', (im.width * regroup, rh), (51, 51, 51))
        for i, s in enumerate(g): c.paste(s, (i * im.width, 0))
        ims.append(c)
w = max(i.width for i in ims); c = Image.new('RGB', (w, sum(i.height for i in ims)), (51, 51, 51)); y = 0
for i in ims: c.paste(i, (0, y)); y += i.height
if c.width > maxw: c = c.resize((maxw, c.height * maxw // c.width), Image.LANCZOS)
c.save(out, quality=88); print('SHEET', out, c.size)
