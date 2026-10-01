#!/usr/bin/env python3
"""Decal textures for the West Gate arches (URP screen-space decals: base colour + alpha, as the West Gate kit's).

  WGA_DecalCartRuts.png   two worn wheel tracks (1.45 m gauge) through an arch, 2.4 m x 7.2 m (V along the track);
                          darker, grimy, polished bands with streaks, fading out towards the city (v = 1) end
  WGA_DecalJambScrape.png horizontal hub/load scrapes on a jamb face, 1.6 m x 0.9 m: dark rubbed streaks + paler
                          abraded stone

Run: uv run --with pillow --with numpy python make_decals.py
"""
from pathlib import Path
import numpy as np
from PIL import Image

OUT = Path(__file__).resolve().parents[2] / "unity/AthenHill/Assets/AthenHill/Art/WestGateArches/Textures"
OUT.mkdir(parents=True, exist_ok=True)


def noise(h, w, scale, octaves=4, seed=0, aniso=(1.0, 1.0)):
    r = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        sy = max(2, int(scale * aniso[0] * 2 ** o * h / max(h, w)))
        sx = max(2, int(scale * aniso[1] * 2 ** o * w / max(h, w)))
        g = r.random((sy + 1, sx + 1)).astype(np.float32)
        out += np.asarray(Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32) / 255 * amp
        tot += amp
        amp *= .5
    return out / tot


def save(name, rgb, a):
    img = np.dstack([rgb, a[..., None]])
    Image.fromarray((np.clip(img, 0, 1) * 255 + .5).astype(np.uint8), "RGBA").save(OUT / f"{name}.png")
    print("wrote", OUT / f"{name}.png", img.shape)


# ---------------------------------------------------------------- cart ruts (u across 2.4 m, v along 7.2 m)
W, H = 512, 1536
u = (np.arange(W) + .5) / W * 2.4 - 1.2          # metres across, centred
v = (np.arange(H) + .5) / H                       # 0 = threshold end (image top row), 1 = city end
U_, V_ = np.meshgrid(u, v)
streak = noise(H, W, 10, 4, 3, aniso=(0.12, 3.0))     # long streaks along the track
blot = noise(H, W, 6, 4, 4)
wob = (noise(H, 8, 3, 3, 5)[:, :1] - .5) * .10        # tracks wander a little
a = np.zeros((H, W), np.float32)
for c, k, core in ((-.725, 1.0, .085), (.725, 1.0, .085), (-.64, .45, .05), (.64, .45, .05)):   # main gauge + a narrower one
    d = np.abs(U_ - c - wob)
    band = np.clip(1 - (d - core) / .11, 0, 1) ** 1.5 * k      # ~0.17 m core, soft 11 cm shoulders
    a = np.maximum(a, band)
between = np.clip(1 - np.abs(U_ - wob) / .55, 0, 1) * .18 * blot          # hoof/foot wear between the tracks
a = np.maximum(a * (.55 + .55 * streak), between)
fade = np.clip((1 - V_) / .55, 0, 1) ** 1.2 * np.clip(V_ / .02, 0, 1)    # strong at the gate, gone by the apron
a = np.clip(a * fade * (.75 + .35 * blot), 0, 1) * .75
col = np.dstack([.26 + .08 * streak, .21 + .06 * streak, .16 + .05 * streak])   # oily, dusty grey-brown
save("WGA_DecalCartRuts", col, a)

# ---------------------------------------------------------------- jamb scrapes (u along the wall 1.6 m, v up 0.9 m)
W, H = 768, 432
x = (np.arange(W) + .5) / W
y = (np.arange(H) + .5) / H
X_, Y_ = np.meshgrid(x, y)
rng = np.random.default_rng(9)
a = np.zeros((H, W), np.float32)
pale = np.zeros((H, W), np.float32)
for i in range(26):
    yc = rng.uniform(.15, .85)
    th = rng.uniform(.006, .03)
    x0, x1 = sorted(rng.uniform(0, 1, 2))
    x1 = min(1, x0 + rng.uniform(.25, .8))
    tilt = rng.uniform(-.05, .05)
    d = np.abs(Y_ - yc - tilt * (X_ - x0))
    m = np.clip(1 - d / th, 0, 1) * ((X_ > x0) & (X_ < x1)) * np.clip(np.minimum(X_ - x0, x1 - X_) / .08, 0, 1)
    if rng.random() < .55:
        a = np.maximum(a, m * rng.uniform(.4, .9))
    else:
        pale = np.maximum(pale, m * rng.uniform(.3, .7))
n = noise(H, W, 8, 4, 11, aniso=(.3, 3))
edge = np.clip(np.minimum(np.minimum(X_, 1 - X_), np.minimum(Y_, 1 - Y_)) / .08, 0, 1)
dark = a * (.6 + .5 * n)
col = np.dstack([.12 + .55 * pale, .10 + .47 * pale, .08 + .38 * pale])
alpha = np.clip(np.maximum(dark, pale * .8) * edge, 0, 1) * .8
save("WGA_DecalJambScrape", col, alpha)

# ---------------------------------------------------------------- painted stencils (OFL Stardos Stencil, West Gate kit)
# atlas 2048 x 512: top half "KEEP CLEAR" (leaves, 3.6 m x 0.45 m), bottom half gate numbers "1" | "2" (transoms)
from PIL import ImageDraw, ImageFont
FONT = str(Path(__file__).resolve().parents[1] / "west_gate_20260926/fonts/stardosstencil__StardosStencil-Bold.ttf")
W, H = 2048, 512
mask = Image.new("L", (W, H), 0)
d = ImageDraw.Draw(mask)


def fit(text, box, size):
    x0, y0, x1, y1 = box
    f = ImageFont.truetype(FONT, size)
    while True:
        bb = d.textbbox((0, 0), text, font=f)
        if bb[2] - bb[0] <= (x1 - x0) * .94 and bb[3] - bb[1] <= (y1 - y0) * .8:
            break
        size = int(size * .95)
        f = ImageFont.truetype(FONT, size)
    bb = d.textbbox((0, 0), text, font=f)
    d.text(((x0 + x1 - (bb[2] - bb[0])) / 2 - bb[0], (y0 + y1 - (bb[3] - bb[1])) / 2 - bb[1]), text, font=f, fill=255)


fit("KEEP CLEAR", (0, 0, W, H // 2), 230)
fit("1", (0, H // 2, W // 2, H), 220)
fit("2", (W // 2, H // 2, W, H), 220)
m = np.asarray(mask, np.float32) / 255
wear = noise(H, W, 18, 5, 21)
chips = noise(H, W, 60, 2, 22)
spray = np.clip((m - .05) / .9, 0, 1)
m = spray * np.clip((wear - .08) * 3.2, 0, 1) * np.clip((chips - .06) * 4.0, 0, 1)
col = np.dstack([np.full((H, W), .82), np.full((H, W), .78), np.full((H, W), .68)]) * (.9 + .1 * wear[..., None])
save("WGA_DecalStencil", col, m * .78)
