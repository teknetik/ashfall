#!/usr/bin/env python3
"""URP Lit maps for the depot's Meshy props: <Name>_BaseMap.jpg (4k, sRGB), _Normal.png (OpenGL), _Mask.png
(R metallic, G occlusion = 1, A smoothness = 1 - roughness). Sources: meshy/outer-berms-depot-20260927/*/texture_*.png."""
from pathlib import Path
import numpy as np
from PIL import Image
HERE = Path(__file__).resolve().parent
SRC = HERE.parents[1] / "meshy/outer-berms-depot-20260927"
OUT = HERE.parents[1] / "unity/AthenHill/Assets/AthenHill/Art/OuterBermsDepot/Meshy"
for name, folder in {"MX_ScrapHeapA": "scrap-heap-a", "MX_ScrapHeapB": "scrap-heap-b"}.items():
    d = SRC / folder
    Image.open(d / "texture_base_color.png").convert("RGB").save(OUT / f"{name}_BaseMap.jpg", quality=93)
    Image.open(d / "texture_normal.png").convert("RGB").save(OUT / f"{name}_Normal.png")
    rough = np.asarray(Image.open(d / "texture_roughness.png").convert("L"), np.float32) / 255
    metal = np.asarray(Image.open(d / "texture_metallic.png").convert("L").resize(rough.shape[::-1]), np.float32) / 255
    mask = np.dstack([metal, np.ones_like(rough), np.zeros_like(rough), 1 - rough])
    Image.fromarray((mask * 255 + .5).astype(np.uint8), "RGBA").save(OUT / f"{name}_Mask.png")
    print(name, "metal mean", metal.mean().round(3), "rough mean", rough.mean().round(3))
