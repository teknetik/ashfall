"""Is a repaint still pixel-aligned with the view it was painted from? Prints the scores and exits 1 when it is not.
Silhouette overlap and edge agreement: a head turned to the camera fails both.
uv run --offline --with pillow --with numpy python align.py view_<v>.png out_<v>.png"""
import sys
import numpy as np
from PIL import Image, ImageFilter
PASS_IOU, PASS_EDGE = .93, .22   # 22 Nov: aligned .376-.646 edges, turned .046-.122
N = 384
v = np.asarray(Image.open(sys.argv[1]).convert('RGBA').resize((N, N))).astype(float)
o = np.asarray(Image.open(sys.argv[2]).convert('RGB').resize((N, N))).astype(float)
# the backdrop's colour where the source view has no figure (a hat brim can reach the frame's edge)
out_of = np.asarray(Image.fromarray(((v[..., 3] > 8) * 255).astype('uint8')).filter(ImageFilter.MaxFilter(15))) < 128
bg = np.median(o[out_of], 0)
fg = np.abs(o - bg).max(2) > 20
fg = np.asarray(Image.fromarray((fg * 255).astype('uint8')).filter(ImageFilter.MedianFilter(5))) > 128
def fill(m):
    """Each row between its outermost figure pixels (grey hair and collars sit close to the backdrop's colour)."""
    r = np.zeros_like(m)
    for y in range(N):
        x = np.nonzero(m[y])[0]
        if len(x): r[y, x[0]:x[-1] + 1] = True
    return r
a, b = fill(v[..., 3] > 128), fill(fg)
iou = (a & b).sum() / max(1, (a | b).sum())
def edges(x):
    g = np.asarray(Image.fromarray(x.astype('uint8')).convert('L').filter(ImageFilter.GaussianBlur(1.5))).astype(float)
    gy, gx = np.gradient(g); return np.hypot(gx, gy)
inner = np.asarray(Image.fromarray(((v[..., 3] > 250) * 255).astype('uint8')).filter(ImageFilter.MinFilter(13))) > 128
corr = float(np.corrcoef(edges(v[..., :3])[inner], edges(o)[inner])[0, 1])
good = iou >= PASS_IOU and corr >= PASS_EDGE
print(f'{"ok" if good else "bad"} iou={iou:.3f} edges={corr:.3f}')
sys.exit(0 if good else 1)
