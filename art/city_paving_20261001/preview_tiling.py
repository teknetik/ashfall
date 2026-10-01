"""Emulate WardPavingLit's course shifting over a 16 x 10 m patch (top view) to judge repetition. 5 mm/px."""
import sys, numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
src = np.asarray(Image.open(sys.argv[1]).convert('RGB').resize((800, 800), Image.LANCZOS))   # 4 m -> 800 px (5 mm/px)
W, H = 16, 10                      # metres
px = 200                           # px per metre
out = np.zeros((H * px, W * px, 3), np.uint8)
def h1(n): return (np.sin(n * 12.9898 + 78.233) * 43758.5453) % 1.0
for row in range(H * 2):           # 0.5 m courses, row 0 at the bottom (south)
    c = row % 8
    off = h1(row + 0.37) * 4.0 if len(sys.argv) < 4 else 0.0
    ys = slice((H * px) - (row + 1) * 100, (H * px) - row * 100)
    # texture rows: course c occupies v in [c/8,(c+1)/8]; image row 0 = v 1
    tr0 = 800 - (c + 1) * 100
    band = src[tr0:tr0 + 100]
    xs = (np.arange(W * px) / px + off) % 4.0
    cols = (xs * 200).astype(int) % 800
    out[ys] = band[:, cols]
Image.fromarray(out).save(sys.argv[2], quality=88)
