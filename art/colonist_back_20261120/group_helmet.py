#!/usr/bin/env python3
"""Fix round (20 Nov 2026): group the helmet's Meshy texture into three readable values without remodelling.
Each texel is classed (soft, then smoothed so no class speckles) as
  canvas  (straps, liner, chin strap: low metallic, tan hue)     -> worn tan canvas, matte, non-metal
  band    (riveted bands, rivets, rims: metallic and bright)       -> worn bare steel, a lighter mid tone
  shell   (everything else: the painted dome)                      -> one dark olive-grey painted steel
and gets its class tone times a gentle low-frequency variation of the original plus 15 % of its fine detail, so the
shape language (bands, rivets, scratches at edges) stays but the speckle and the teal/yellow paint noise go.
Run: heavy.sh uv run --with numpy --with pillow --with scipy python group_helmet.py work/tex/TS_Helmet"""
import sys, numpy as np
from PIL import Image
from scipy import ndimage
d = sys.argv[1]
a = np.asarray(Image.open(d + '/1_Image_0.jpg').convert('RGB'), np.float32)
mr = np.asarray(Image.open(d + '/2_Image_1.jpg').convert('RGB'), np.float32)
metal = ndimage.median_filter(mr[..., 2], 5) / 255; L = a.mean(-1)
Ls = ndimage.median_filter(L, 5)
warm = ndimage.median_filter(a[..., 0] - a[..., 2], 5)
canvas = (metal < 0.35) & (warm > 12) & (Ls > 60)
band = (metal >= 0.45) & (Ls > np.percentile(Ls, 55)) & ~canvas
cls = np.stack([~(canvas | band), band, canvas], -1).astype(np.float32)     # shell, band, canvas
cls = ndimage.gaussian_filter(cls, (2.5, 2.5, 0)); lab = cls.argmax(-1)
TONE = np.array([[60, 62, 56], [104, 98, 88], [116, 101, 76]], np.float32)   # shell, band, canvas (sRGB)
MR = np.array([[0.62, 0.55], [0.40, 0.88], [0.90, 0.0]], np.float32)       # roughness, metallic
w = cls / cls.sum(-1, keepdims=True)
base = np.einsum('hwc,ck->hwk', w, TONE)
lo = ndimage.gaussian_filter(Ls, 10); var = np.clip(lo / max(lo.mean(), 1), 0.75, 1.25)
detail = a - ndimage.gaussian_filter(a, (3, 3, 0))
out = base * (1 + 0.35 * (var - 1))[..., None] + 0.15 * detail
Image.fromarray(out.clip(0, 255).astype(np.uint8)).save(d + '/group_base.png', optimize=True)
rm = np.einsum('hwc,ck->hwk', w, MR)
Image.fromarray(np.stack([mr[..., 0], rm[..., 0] * 255, rm[..., 1] * 255], -1).clip(0, 255).astype(np.uint8)).save(d + '/group_mr.png', optimize=True)
print('GROUP shell %.2f band %.2f canvas %.2f' % tuple((lab == i).mean() for i in range(3)))
Image.fromarray((np.array([[0, 0, 0], [200, 200, 200], [200, 150, 60]], np.uint8))[lab]).resize((512, 512)).save(d + '/group_classes.png')
