#!/usr/bin/env python3
"""Calm a Meshy armour texture set for the conversation-camera distance without changing its UVs:
base colour: 60-70 % of a 5 px median (kills single-texel speckle, keeps band/rivet shapes) and the high-frequency
contrast that remains cut by `hf`; metallicRoughness (glTF: G = roughness, B = metallic): metallic median-filtered
(isolated metal flecks on canvas/paint removed), roughness median-filtered and raised by `rough_add`.
The normal map is untouched (its strength is set on the material by patch_glb --mat).
Run: heavy.sh uv run --with numpy --with pillow --with scipy python clean_tex.py <dir> <median_mix> <hf> <rough_add>"""
import sys, numpy as np
from PIL import Image
from scipy import ndimage
d, mix, hf, radd = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
a = np.asarray(Image.open(d + '/1_Image_0.jpg').convert('RGB'), np.float32)
med = np.stack([ndimage.median_filter(a[..., c], 5) for c in range(3)], -1)
b = a * (1 - mix) + med * mix
low = ndimage.gaussian_filter(b, (6, 6, 0))
b = low + (b - low) * hf
PADMASK = '/home/teknetik/code/ao2/art/colonist_back_20261120/work/vest_padmask.npy'
pad = None
if 'TS_FieldVest' in d:
    # fix round: the left shoulder pad (UV mask rasterised by fit_piece.py pad_mask) becomes one piece of dark
    # blued steel; rust and the old yellow paint survive only near the pad's 3D edges (mask G channel)
    pm = np.load(PADMASK); mpad = ndimage.binary_dilation(pm[..., 0] > 0, iterations=3)
    # only the steel of the pad (metallic or painted/rusted), not the canvas straps under it
    mm0 = np.asarray(Image.open(d + '/2_Image_1.jpg').convert('RGB'), np.float32)[..., 2] / 255
    paint = (b[..., 0] - b[..., 2]) > 35
    m0 = mpad & ndimage.binary_closing(ndimage.median_filter((mm0 > 0.25) | paint, 5), iterations=2)
    edge = ndimage.grey_dilation(pm[..., 1], size=(5, 5))
    lum = b.mean(-1); lowl = ndimage.gaussian_filter(lum, 12)
    steel = np.array([46, 46, 44], np.float32)[None, None] * (0.85 + 0.3 * (lowl / max(lowl[m0].mean(), 1)))[..., None]
    rusty = np.clip((b[..., 0] - b[..., 2]) / 60.0, 0, 1)
    ra = np.clip(rusty * edge * 1.2, 0, 1)[..., None]
    padcol = steel * (1 - ra) + b * 0.75 * ra
    padcol = padcol + (b - ndimage.gaussian_filter(b, (3, 3, 0))) * 0.25        # keep a little of the hammered detail
    b = np.where(m0[..., None], padcol, b); pad = (m0, ra[..., 0])
    print('PAD steel texels', int(m0.sum()), 'of pad mask', int(mpad.sum()))
Image.fromarray(b.clip(0, 255).astype(np.uint8)).save(d + '/clean_base.png', optimize=True)
m = np.asarray(Image.open(d + '/2_Image_1.jpg').convert('RGB'), np.float32)
r = ndimage.median_filter(m[..., 1], 5) + radd * 255
mt = ndimage.median_filter(m[..., 2], 9)
if pad is not None:
    m0, ra = pad
    r = np.where(m0, (0.62 + 0.25 * ra) * 255, r); mt = np.where(m0, (0.60 - 0.4 * ra) * 255, mt)
out = np.stack([m[..., 0], r, mt], -1)
Image.fromarray(out.clip(0, 255).astype(np.uint8)).save(d + '/clean_mr.png', optimize=True)
print('CLEAN', d, 'rough mean %.2f -> %.2f metal mean %.2f -> %.2f' % (m[..., 1].mean() / 255, r.clip(0, 255).mean() / 255, m[..., 2].mean() / 255, mt.mean() / 255))
