#!/usr/bin/env python3
"""Before | after contact sheets: pairs.py BEFORE_DIR AFTER_DIR OUT_PREFIX [--hours 13,17,20.5]
One JPEG per hour, a row per camera, before on the left, after on the right (each 640x360)."""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw

p = argparse.ArgumentParser()
p.add_argument('before'); p.add_argument('after'); p.add_argument('out')
p.add_argument('--hours', default='13,17,20.5')
a = p.parse_args()
W, H = 640, 360
for h in [float(x) for x in a.hours.split(',')]:
    tag = 'h%05.2f' % h
    names = sorted(x.name for x in Path(a.after).glob('*-%s.png' % tag) if (Path(a.before) / x.name).exists())
    if not names: continue
    sheet = Image.new('RGB', (2 * W, len(names) * (H + 22)), (20, 20, 20)); d = ImageDraw.Draw(sheet)
    for i, n in enumerate(names):
        y = i * (H + 22)
        for j, src in enumerate([a.before, a.after]):
            with Image.open(Path(src) / n) as im: sheet.paste(im.convert('RGB').resize((W, H)), (j * W, y + 22))
        d.text((6, y + 4), 'BEFORE  ' + n[:-4], fill=(230, 220, 200)); d.text((W + 6, y + 4), 'AFTER  ' + n[:-4], fill=(230, 220, 200))
    sheet.save('%s-%s.jpg' % (a.out, tag), quality=86)
    print('%s-%s.jpg' % (a.out, tag), len(names))
