"""Before/after pairs (native 1920x1080 lookbook captures, matched cameras and hours) -> compare/<cam>-h<hour>.jpg.
Run from the evidence folder: uv run --with pillow python compare/make_pairs.py [before_dir] [after_dir]"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
B = Path(sys.argv[1] if len(sys.argv) > 1 else "native-before"); A = Path(sys.argv[2] if len(sys.argv) > 2 else "native-after2")
out = Path("compare")
for a in sorted(A.glob("cam_*.png")):
    b = B / a.name
    if not b.exists():
        continue
    ia, ib = Image.open(a).convert("RGB").resize((960, 540)), Image.open(b).convert("RGB").resize((960, 540))
    s = Image.new("RGB", (1920, 560), (15, 15, 15)); s.paste(ib, (0, 20)); s.paste(ia, (960, 20))
    d = ImageDraw.Draw(s); d.text((6, 4), "BEFORE  " + b.stem, fill=(235, 235, 235)); d.text((966, 4), "AFTER  " + a.stem, fill=(235, 235, 235))
    s.save(out / (a.stem + ".jpg"), quality=88)
    print(a.stem)
