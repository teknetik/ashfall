"""Patch the one source defect in the baked Meshy sign maps: a hard-edged dark rectangle inside the C of 'BASIC'
(the original mesh has a hole/patch there; it bakes as a black block and reads as a white square in the raw GLB).
Fills the rectangle with mirrored samples of the plain panel just to its right, feathered at the edges.
Inputs are the untouched Blender bakes in baked/raw-bake-fixed-source (copy of baked/); outputs go to baked/runtime/.
Run: uv run --offline --with pillow --with numpy python fix_artifact.py
"""
import os, json
import numpy as np
from PIL import Image

D = os.path.dirname(os.path.abspath(__file__)) + '/baked/'
OUT = D + 'runtime/'
os.makedirs(OUT, exist_ok=True)
# Artifact rectangle in the 4096x1320 base map (found by inspection of crop x1500-2000 / y250-550), with margin.
X0, X1, Y0, Y1 = 1636, 1806, 330, 482
SRC_X0, SRC_X1 = 1812, 1896          # plain panel between the C and the G (same rows)
F = 10                               # feather (px)


def patch(arr, scale):
    x0, x1, y0, y1 = [int(round(v * scale)) for v in (X0, X1, Y0, Y1)]
    sx0, sx1 = int(round(SRC_X0 * scale)), int(round(SRC_X1 * scale))
    w = x1 - x0
    src = arr[y0:y1, sx0:sx1]
    tile = np.concatenate([src, src[:, ::-1], src, src[:, ::-1]], axis=1)[:, :w]
    f = max(1, int(round(F * scale)))
    m = np.ones((y1 - y0, w), np.float32)
    ramp = np.linspace(0, 1, f + 1)[1:]
    m[:f, :] *= ramp[:, None]; m[-f:, :] *= ramp[::-1][:, None]
    m[:, :f] *= ramp[None, :]; m[:, -f:] *= ramp[::-1][None, :]
    out = arr.astype(np.float32).copy()
    out[y0:y1, x0:x1] = out[y0:y1, x0:x1] * (1 - m[..., None]) + tile.astype(np.float32) * m[..., None]
    return out


rep = {}
for name, scale in (('sign_basecolor', 1), ('sign_normal', 1), ('sign_metalgloss', 1), ('sign_emission', 0.5)):
    im = Image.open(D + name + '.png')
    a = np.array(im)
    out = np.clip(patch(a, scale), 0, 255).astype(np.uint8)
    Image.fromarray(out, im.mode).save(OUT + name + '.png', optimize=True)
    rep[name] = {'size': im.size, 'mode': im.mode}
json.dump({'rect': [X0, X1, Y0, Y1], 'source_cols': [SRC_X0, SRC_X1], 'feather': F, 'maps': rep}, open(OUT + 'fix-report.json', 'w'), indent=1)
Image.open(OUT + 'sign_basecolor.png').crop((1400, 200, 2100, 600)).save(OUT + 'check_crop.png')
print('done', rep)
