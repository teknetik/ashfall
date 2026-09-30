#!/usr/bin/env python3
"""Prepare Unity texture sets for the Vanguard Hall rebuild (30 Sep 2026).

Run:  uv run --offline --with numpy --with pillow python prepare_textures.py

Poly Haven CC0 sources (polyhaven/, manifest.json) become Unity URP inputs in
unity/AthenHill/Assets/AthenHill/Art/VanguardHall/Textures:
  <Set>_BaseMap.jpg (sRGB albedo, copied), <Set>_Normal.jpg (OpenGL +Y, copied),
  <Set>_Mask.png (R metallic, G occlusion, B 0, A smoothness = 1 - roughness; ARM source).
Also generates the woven Warden banner (VH_Banner_BaseMap.png with frayed alpha, VH_Banner_Mask.png) with an
original abstract twin-stripe mark. No lettering or third-party marks.
"""
import json, shutil
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent
PH = HERE / "polyhaven"
OUT = HERE.parents[1] / "unity/AthenHill/Assets/AthenHill/Art/VanguardHall/Textures"
OUT.mkdir(parents=True, exist_ok=True)

# albedo grade: (saturation multiplier, target mean sRGB) - calmer honey sandstone per the accepted concept
GRADE = {"VH_Ashlar": (0.78, (0.75, 0.665, 0.53)), "VH_Sandstone": (0.72, (0.77, 0.665, 0.53))}

SETS = {  # Unity set name: (poly haven id, mask size)
    "VH_Ashlar": ("worn_rock_natural_01", 2048),
    "VH_Sandstone": ("sandstone_cracks", 2048),
    "VH_Rust": ("rust_coarse_01", 2048),
    "VH_SheetSteel": ("rusty_metal_sheet", 2048),
    "VH_Paint": ("painted_metal_shutter", 2048),
    "VH_Sand": ("dense_sand", 2048),
    "VH_Linen": ("rough_linen", 1024),
}


def find(d, tag):
    for f in sorted(d.glob("*")):
        if tag in f.name:
            return f
    raise FileNotFoundError(f"{d}/{tag}")


def build_sets():
    rec = {}
    for name, (pid, msize) in SETS.items():
        d = PH / pid
        diff, nor, arm = find(d, "_diff_"), find(d, "_nor_gl_"), find(d, "_arm_")
        if name in GRADE:
            sat, target = GRADE[name]
            D = np.asarray(Image.open(diff).convert("RGB")).astype(np.float32) / 255.0
            lum = (D * np.array([0.2126, 0.7152, 0.0722])).sum(-1, keepdims=True)
            D = lum + (D - lum) * sat
            D = D * (np.array(target) / D.reshape(-1, 3).mean(0))
            Image.fromarray((np.clip(D, 0, 1) * 255 + 0.5).astype(np.uint8)).save(OUT / f"{name}_BaseMap.jpg", quality=94)
        else:
            shutil.copyfile(diff, OUT / f"{name}_BaseMap.jpg")
        shutil.copyfile(nor, OUT / f"{name}_Normal.jpg")
        a = Image.open(arm).convert("RGB")
        if a.size[0] != msize:
            a = a.resize((msize, msize), Image.LANCZOS)
        A = np.asarray(a).astype(np.float32) / 255.0
        ao, rough, metal = A[..., 0], A[..., 1], A[..., 2]
        mask = np.stack([metal, ao, np.zeros_like(ao), 1.0 - rough], -1)
        Image.fromarray((mask * 255 + 0.5).clip(0, 255).astype(np.uint8), "RGBA").save(OUT / f"{name}_Mask.png", optimize=True)
        rec[name] = {"grade": GRADE.get(name), "source": pid, "diffuse": diff.name, "normal": nor.name, "arm": arm.name, "maskSize": msize}
        print(name, pid, flush=True)
    return rec


def noise2(h, w, scale, seed, octaves=4):
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        s = max(2, int(scale * (2 ** o)))
        g = rng.random((s + 1, s + 1)).astype(np.float32)
        img = Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
        out += amp * (np.asarray(img).astype(np.float32) / 255.0)
        tot += amp
        amp *= 0.5
    return out / tot


def banner():
    W, H = 1024, 3072          # banner 1.10 m x 3.39 m
    y = np.linspace(0, 1, H)[:, None] * np.ones((1, W))   # 0 = bottom (UV v), image row 0 = top
    y = y[::-1]
    x = np.ones((H, 1)) * np.linspace(0, 1, W)[None, :]
    lin = Image.open(find(PH / "rough_linen", "_diff_")).convert("L").resize((256, 256), Image.LANCZOS)
    L = np.asarray(lin).astype(np.float32) / 255.0
    L = np.tile(L, (H // 256 + 1, W // 256 + 1))[:H, :W]
    weave = (L - L.mean()) * 0.9
    dye = noise2(H, W, 3, 7) - 0.5
    blotch = noise2(H, W, 10, 11) - 0.5
    base = np.array([0.47, 0.075, 0.06])
    col = base[None, None, :] * (1 + 0.28 * dye[..., None] + 0.12 * blotch[..., None] + weave[..., None])
    # sun fade towards the top and the outer folds, dust at the hem
    fade = np.clip((y - 0.35) / 0.65, 0, 1) ** 1.5 * 0.35
    col = col * (1 - fade[..., None]) + np.array([0.62, 0.36, 0.3])[None, None, :] * fade[..., None]
    dust = np.clip((0.22 - y) / 0.22, 0, 1) ** 1.6 * (0.55 + 0.45 * noise2(H, W, 8, 5))
    col = col * (1 - 0.55 * dust[..., None]) + np.array([0.42, 0.33, 0.24])[None, None, :] * 0.55 * dust[..., None]
    # woven side borders: darker band with a pale thread line
    bw = 0.05 / 1.10
    edge = np.minimum(x, 1 - x)
    border = edge < bw
    col[border] *= 0.62
    thread = np.abs(edge - bw * 1.25) < 0.004
    col[thread] = col[thread] * 0.4 + np.array([0.78, 0.68, 0.5]) * 0.6
    # emblem: two pale vertical bars (left shorter), slanted tops, worn edges
    em = np.zeros((H, W), bool)
    wear = noise2(H, W, 40, 3)
    for (cx, y0, y1, slant) in ((0.40, 0.40, 0.68, 0.03), (0.60, 0.34, 0.80, 0.03)):
        hw = 0.075
        inside = (np.abs(x - cx) < hw) & (y > y0) & (y < y1 - slant * (x - (cx - hw)) / (2 * hw))
        em |= inside
    em &= wear > 0.12
    ivory = np.array([0.80, 0.70, 0.52])
    col[em] = ivory * (1 + 0.25 * (noise2(H, W, 20, 9)[em, None] - 0.5)) * (1 - 0.5 * fade[em, None] * 0) + weave[em, None] * 0.25
    # alpha: swallowtail notch at the bottom and frayed edges, a few small holes
    notch_h = 0.34 / 3.39
    notch = y < notch_h * (1 - np.abs(x - 0.5) / 0.5) ** 1.0 * 1.0
    notch = y < notch_h * (1 - np.abs(x - 0.5) * 2)
    fray = noise2(H, W, 60, 21)
    alpha = np.ones((H, W), np.float32)
    alpha[notch] = 0
    near_edge = (y < notch_h * (1 - np.abs(x - 0.5) * 2) + 0.012) | (y < 0.01) | (edge < 0.004)
    alpha[near_edge & (fray < 0.55)] = 0
    holes = noise2(H, W, 30, 33)
    alpha[(holes > 0.9) & (y < 0.28)] = 0
    rgb = (np.clip(col, 0, 1) ** (1 / 1.0) * 255 + 0.5).astype(np.uint8)
    a = (alpha * 255).astype(np.uint8)
    Image.fromarray(np.dstack([rgb, a]), "RGBA").save(OUT / "VH_Banner_BaseMap.png", optimize=True)
    rough = 0.9 - 0.1 * weave
    mask = np.dstack([np.zeros_like(rough), np.ones_like(rough) * (0.9 + 0.1 * weave), np.zeros_like(rough), 1 - rough])
    Image.fromarray((np.clip(mask, 0, 1) * 255).astype(np.uint8), "RGBA").resize((512, 1536), Image.LANCZOS).save(OUT / "VH_Banner_Mask.png")
    print("banner", flush=True)


if __name__ == "__main__":
    rec = build_sets()
    banner()
    man = json.loads((PH / "manifest.json").read_text())
    (OUT / "textures.json").write_text(json.dumps({"sets": rec, "polyhaven": man,
                                                   "banner": "generated by prepare_textures.py (original mark)"}, indent=1))
