#!/usr/bin/env python3
"""Pack Poly Haven CC0 ground sets into the Berms Ground layer format.

Per layer:  <name>_AH.png  RGB albedo (sRGB) + A height (disp, normalised per layer)
            <name>_NRA.png R/G OpenGL normal XY, B roughness, A ambient occlusion (linear)
Layer order must match BermsGroundLayers.asset / BermsGround.shader:
  0 base dry ground with pebbles, 1 wind-deposited sand, 2 compacted road gravel, 3 cracked crust.
"""
import numpy as np
from PIL import Image
from pathlib import Path

SRC = Path(__file__).resolve().parent / "polyhaven/textures"
OUT = Path(__file__).resolve().parents[2] / "unity/AthenHill/Assets/AthenHill/Art/WestGate/Ground"
LOCAL = Path(__file__).resolve().parent / "ground-layers"   # per-layer PNGs stay outside Assets
LOCAL.mkdir(exist_ok=True)
AH_STACK, NRA_STACK = [], []
LAYERS = ["dry_ground_rocks", "dense_sand", "sandy_gravel_02", "dry_ground_01"]


def load(path, mode):
    return np.asarray(Image.open(path).convert(mode), dtype=np.float32) / 255.0


for name in LAYERS:
    d = SRC / name
    diff = load(d / f"{name}_diff_2k.jpg", "RGB")
    disp = load(d / f"{name}_disp_2k.jpg", "L")
    nor = load(d / f"{name}_nor_gl_2k.jpg", "RGB")
    arm = load(d / f"{name}_arm_2k.jpg", "RGB")
    lo, hi = np.percentile(disp, 1), np.percentile(disp, 99)
    h = np.clip((disp - lo) / max(hi - lo, 1e-4), 0, 1)
    ah = np.dstack([diff, h])
    nra = np.dstack([nor[..., 0], nor[..., 1], arm[..., 1], arm[..., 0]])
    Image.fromarray((ah * 255 + .5).astype(np.uint8), "RGBA").save(LOCAL / f"{name}_AH.png")
    Image.fromarray((nra * 255 + .5).astype(np.uint8), "RGBA").save(LOCAL / f"{name}_NRA.png")
    AH_STACK.append(ah); NRA_STACK.append(nra)
    print(name, "albedo mean", diff.reshape(-1, 3).mean(0).round(3), "rough mean", arm[..., 1].mean().round(3))

# Unity imports these as Texture2DArray (flipbook 1 column x 4 rows; slice 0 = top row)
Image.fromarray((np.concatenate(AH_STACK, 0) * 255 + .5).astype(np.uint8), "RGBA").save(OUT / "BermsGroundLayers_AH.png")
Image.fromarray((np.concatenate(NRA_STACK, 0) * 255 + .5).astype(np.uint8), "RGBA").save(OUT / "BermsGroundLayers_NRA.png")
print("stacked arrays written")
