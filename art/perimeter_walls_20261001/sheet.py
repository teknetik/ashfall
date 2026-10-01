"""Contact sheet of PNG captures: uv run --with pillow python sheet.py OUT.jpg [--cols 3 --width 640] img1.png img2.png ..."""
import sys, argparse
from pathlib import Path
from PIL import Image, ImageDraw

p = argparse.ArgumentParser()
p.add_argument("out"); p.add_argument("imgs", nargs="+"); p.add_argument("--cols", type=int, default=3); p.add_argument("--width", type=int, default=640)
a = p.parse_args()
w = a.width; h = w * 9 // 16
rows = (len(a.imgs) + a.cols - 1) // a.cols
sheet = Image.new("RGB", (a.cols * w, rows * (h + 20)), (20, 20, 20))
d = ImageDraw.Draw(sheet)
for i, f in enumerate(a.imgs):
    with Image.open(f) as im:
        t = im.convert("RGB").resize((w, h))
    x, y = i % a.cols * w, i // a.cols * (h + 20)
    sheet.paste(t, (x, y + 20)); d.text((x + 5, y + 4), Path(f).stem, fill=(230, 220, 200))
sheet.save(a.out, quality=88)
