"""Contact sheet of PNGs: python sheet.py <out.jpg> <cols> <width> img... (labels = file stems)."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
out, cols, W = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
files = [Path(p) for p in sys.argv[4:]]
ims = [Image.open(f).convert("RGB") for f in files]
w = W // cols; h = int(w * ims[0].height / ims[0].width)
rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGB", (cols * w, rows * (h + 18)), (20, 20, 20))
d = ImageDraw.Draw(sheet)
for i, (f, im) in enumerate(zip(files, ims)):
    x, y = (i % cols) * w, (i // cols) * (h + 18)
    sheet.paste(im.resize((w, h), Image.LANCZOS), (x, y + 18))
    d.text((x + 4, y + 3), f.stem, fill=(240, 240, 240))
sheet.save(out, quality=88)
print(out, sheet.size)
