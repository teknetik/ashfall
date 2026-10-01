"""Contact sheet: sheet.py out.jpg cols width img1 img2 ... (labels = file names)."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
out, cols, w = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
files = [f for f in sys.argv[4:] if Path(f).exists()]
ims = []
for f in files:
    im = Image.open(f).convert("RGB"); h = int(im.height * w / im.width); ims.append((f, im.resize((w, h))))
h = max(i.height for _, i in ims); rows = (len(ims) + cols - 1) // cols
S = Image.new("RGB", (cols * w, rows * (h + 18)), (20, 20, 20)); d = ImageDraw.Draw(S)
for k, (f, im) in enumerate(ims):
    x, y = (k % cols) * w, (k // cols) * (h + 18)
    S.paste(im, (x, y + 18)); d.text((x + 4, y + 3), Path(f).parent.name + "/" + Path(f).name, fill=(255, 255, 0))
S.save(out, quality=88); print(out, S.size)
