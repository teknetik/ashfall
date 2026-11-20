#!/usr/bin/env python3
"""Recolour Poly Haven Cliff Side to the basin's sandstone (fix round 2, 20 Nov 2026): the scan is a dark, saturated
red-brown; the basin cliffs (Art/Terrain/SandstoneAlbedo.png) are pale warm tan. In linear light every pixel keeps its
luminance ratio to the scan's mean (the bedding, with contrast x1.15) and takes the basin's mean colour, with 20 % of
the scan's own chroma kept. Writes Assets/AthenHill/Art/BermsVariety/Rock/BV_CliffSide_BaseMap.jpg (same GUID).
Run: uv run --with numpy --with pillow python recolour_rock.py"""
import numpy as np
from PIL import Image
from bv_common import HERE, ART_OUT
src = np.asarray(Image.open(HERE / 'polyhaven/cliff_side/cliff_side_diff_2k.jpg').convert('RGB'), np.float32) / 255
tgt_srgb = np.asarray(Image.open(ART_OUT.parent / 'Terrain/SandstoneAlbedo.png').convert('RGB').resize((256, 256)), np.float32).reshape(-1, 3).mean(0) / 255
lin = lambda c: np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
srgb = lambda c: np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(np.clip(c, 0, None), 1 / 2.4) - 0.055)
s = lin(src); t = lin(tgt_srgb)
w = np.array([0.2126, 0.7152, 0.0722])
L = s @ w; Lm = L.mean()
ratio = (L / Lm) ** 1.15
grey = t[None, None, :] * ratio[..., None]
chroma = s / np.maximum(L[..., None], 1e-4) * (t @ w) * ratio[..., None]       # scan hue at the target brightness
out = grey * 0.8 + chroma * 0.2
img = (np.clip(srgb(out), 0, 1) * 255 + 0.5).astype(np.uint8)
Image.fromarray(img).save(ART_OUT / 'Rock/BV_CliffSide_BaseMap.jpg', quality=93)
print('target', tgt_srgb, 'result mean', img.reshape(-1, 3).mean(0) / 255)
