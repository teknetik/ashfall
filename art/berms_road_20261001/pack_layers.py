#!/usr/bin/env python3
"""Pack the Berms Ground V2 layer arrays (1 Oct 2026). Run through the heavy wrapper:
    $O/heavy.sh uv run --with pillow --with numpy python art/berms_road_20261001/pack_layers.py

Per layer:  AH  = RGB albedo (sRGB) + A height (displacement normalised per layer to its 1st..99th percentile)
            NRA = R/G OpenGL normal XY, B roughness, A ambient occlusion (linear)
Layer order (must match Shaders/BermsGroundV2.shader and the material):
  0 dry_ground_rocks  pebbly dry ground (the basin's scree; already packed by the West Gate pass)
  1 dense_sand        wind-deposited sand (West Gate pass)
  2 gravel_ground_01  compacted gravel road surface, the wheel paths (new)
  3 dry_ground_01     cracked crust (West Gate pass)
  4 floor_pebbles_01  loose gravel: the crown and shoulder windrows of the road, desert-pavement lag on the flats (new)
New layers get a partial high-pass on albedo (the 3 m scans carry metre-scale stains that would repeat every tile; the
shader's macro and mid noise supply the large-scale variation instead). Unity imports both PNGs as Texture2DArray
(flipbook 1 column x 5 rows, slice 0 = top row).
"""
import json
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
WG = HERE.parent / "west_gate_20260926" / "ground-layers"
PH = HERE / "polyhaven" / "textures"
OUT = HERE.parents[1] / "unity/AthenHill/Assets/AthenHill/Art/BermsRoad/Ground"
LOCAL = HERE / "work" / "layers"
OUT.mkdir(parents=True, exist_ok=True); LOCAL.mkdir(parents=True, exist_ok=True)
N = 2048
LAYERS = [("dry_ground_rocks", "wg"), ("dense_sand", "wg"), ("gravel_ground_01", "ph"), ("dry_ground_01", "wg"), ("floor_pebbles_01", "ph")]
HIGHPASS = {"gravel_ground_01": .55, "floor_pebbles_01": .35}   # share of the >~0.4 m variation removed


def load(path, mode):
    return np.asarray(Image.open(path).convert(mode), dtype=np.float32) / 255.0


def highpass(rgb, amount, radius_px):
    """Divide out a share of the low-frequency albedo (FFT Gaussian: wraps, so the tile stays seamless), keep the mean."""
    n = rgb.shape[0]
    f = np.fft.fftfreq(n)
    g = np.exp(-2 * (np.pi * radius_px) ** 2 * (f[:, None] ** 2 + f[None, :] ** 2)).astype(np.float32)
    lo = np.stack([np.real(np.fft.ifft2(np.fft.fft2(rgb[..., c]) * g)) for c in range(3)], -1).astype(np.float32)
    mean = rgb.reshape(-1, 3).mean(0)
    ratio = mean / np.maximum(lo, 1e-3)
    return np.clip(rgb * (1 + (ratio - 1) * amount), 0, 1)


report = {}
AH, NRA = [], []
for name, src in LAYERS:
    if src == "wg":
        ah = load(WG / f"{name}_AH.png", "RGBA"); nra = load(WG / f"{name}_NRA.png", "RGBA")
    else:
        d = PH / name
        diff = load(d / f"{name}_diff_2k.jpg", "RGB"); disp = load(d / f"{name}_disp_2k.jpg", "L")
        nor = load(d / f"{name}_nor_gl_2k.jpg", "RGB"); arm = load(d / f"{name}_arm_2k.jpg", "RGB")
        if name in HIGHPASS:
            # linearise, high-pass in linear light, back to sRGB
            lin = diff ** 2.2
            lin = highpass(lin, HIGHPASS[name], radius_px=int(N * .4 / 3.0))
            diff = lin ** (1 / 2.2)
        lo, hi = np.percentile(disp, 1), np.percentile(disp, 99)
        h = np.clip((disp - lo) / max(hi - lo, 1e-4), 0, 1)
        ah = np.dstack([diff, h]); nra = np.dstack([nor[..., 0], nor[..., 1], arm[..., 1], arm[..., 0]])
        Image.fromarray((ah * 255 + .5).astype(np.uint8), "RGBA").save(LOCAL / f"{name}_AH.png")
        Image.fromarray((nra * 255 + .5).astype(np.uint8), "RGBA").save(LOCAL / f"{name}_NRA.png")
    assert ah.shape[:2] == (N, N) and nra.shape[:2] == (N, N), name
    lin = ah[..., :3] ** 2.2
    report[name] = {"source": src, "albedo_mean_linear": lin.reshape(-1, 3).mean(0).round(4).tolist(),
                    "albedo_mean_srgb": ah[..., :3].reshape(-1, 3).mean(0).round(4).tolist(),
                    "roughness_mean": round(float(nra[..., 2].mean()), 3), "ao_mean": round(float(nra[..., 3].mean()), 3),
                    "luma_std": round(float((ah[..., :3] @ np.array([.2126, .7152, .0722])).std()), 4),
                    "highpass": HIGHPASS.get(name, 0)}
    AH.append(ah); NRA.append(nra)
    print(name, report[name], flush=True)

Image.fromarray((np.concatenate(AH, 0) * 255 + .5).astype(np.uint8), "RGBA").save(OUT / "BermsRoadLayers_AH.png", compress_level=6)
Image.fromarray((np.concatenate(NRA, 0) * 255 + .5).astype(np.uint8), "RGBA").save(OUT / "BermsRoadLayers_NRA.png", compress_level=6)
(HERE / "layers.json").write_text(json.dumps({"order": [n for n, _ in LAYERS], "layers": report}, indent=1))
print("arrays written", OUT)
