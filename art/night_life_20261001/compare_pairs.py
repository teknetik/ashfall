"""Before/after contact sheets from two lookbook folders: compare_pairs.py OFF ON OUT.jpg hour cam1 cam2 ...
Each row: before | after at the given hour (labels from the folder names)."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
off, on, out, hour = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], float(sys.argv[4])
cams = sys.argv[5:]
W = 960; H = W * 9 // 16
S = Image.new("RGB", (2 * W, len(cams) * (H + 20)), (18, 18, 18)); d = ImageDraw.Draw(S)
for i, c in enumerate(cams):
    for j, folder in enumerate((off, on)):
        p = folder / f"{c}-h{hour:05.2f}.png"
        if not p.exists(): continue
        im = Image.open(p).convert("RGB").resize((W, H))
        S.paste(im, (j * W, i * (H + 20) + 20))
        d.text((j * W + 6, i * (H + 20) + 4), f"{'BEFORE' if j == 0 else 'AFTER'}  {c}  {hour:05.2f}  ({folder.name})", fill=(255, 230, 120))
S.save(out, quality=88); print(out, S.size)
