#!/usr/bin/env python3
"""Fix round (20 Nov 2026), point 8: the 3 Oct hair shells read as a light stipple from behind in the native frames.
The shell and scalp colours are dark already (shell texels ~37/27/19 sRGB); the dots are sun highlights on hundreds of
alpha-clipped strand bits (PlayerHairShell roughness 0.55, set in patch_glb) and on the painted scalp's skin
specular, with skin showing through the gaps. This makes the shells denser (alpha x1.2 + 0.04, so more texels pass the
0.5 cutoff) and their colour softer (strand-scale contrast halved), and makes the skin matte under the painted hair
(roughness >= 0.88 where tex/hair_mask.png covers the skin UVs: scalp, beard, brows). Skin colour is untouched, so the
face reads as on 3 Oct. Writes tex/hair_shell.png and tex/skin_rough.png (inputs: the shipped images in inspect/).
Run: heavy.sh uv run --with numpy --with pillow --with scipy python hair_tex.py"""
import numpy as np
from PIL import Image
from scipy import ndimage
Image.MAX_IMAGE_PIXELS = None
H = '/home/teknetik/code/ao2/art/colonist_back_20261120/'
h = np.asarray(Image.open(H + 'inspect/colonist/7_hair_shell.png')).astype(np.float32)
rgb = h[..., :3]; blur = ndimage.gaussian_filter(rgb, (2, 2, 0))
rgb = blur + (rgb - blur) * 0.5
a = np.clip(h[..., 3] * 1.2 + 10, 0, 255)
Image.fromarray(np.dstack([rgb, a]).clip(0, 255).astype(np.uint8), 'RGBA').save(H + 'tex/hair_shell.png', optimize=True)
r = np.asarray(Image.open(H + 'inspect/colonist/2_skin_rough.png').convert('RGB')).astype(np.float32)
mk = Image.open('/home/teknetik/code/ao2/art/player_face_20261003/tex/hair_mask.png').convert('L').resize(r.shape[1::-1], Image.BILINEAR)
mk = ndimage.binary_dilation(np.asarray(mk) > 60, iterations=4)
print('skin rough G mean in mask before %.2f' % (r[..., 1][mk].mean() / 255))
r[..., 1] = np.where(mk, np.maximum(r[..., 1], 0.88 * 255), r[..., 1])
Image.fromarray(r.clip(0, 255).astype(np.uint8)).save(H + 'tex/skin_rough.png', optimize=True)
print('alpha>=128 before %.3f after %.3f' % ((h[..., 3] >= 128).mean(), (a >= 128).mean()))
