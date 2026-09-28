#!/usr/bin/env python3
"""Decal textures for the West Gate outpost (URP screen-space decals, base colour + alpha)."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).resolve().parents[2] / "unity/AthenHill/Assets/AthenHill/Art/WestGate/Textures"
rng = np.random.default_rng(77)


def noise(h, w, scale, octaves=4, seed=0):
    r = np.random.default_rng(seed); out = np.zeros((h, w), np.float32); amp = 1; tot = 0
    for o in range(octaves):
        sy, sx = max(2, int(scale * 2 ** o * h / max(h, w))), max(2, int(scale * 2 ** o * w / max(h, w)))
        g = r.random((sy + 1, sx + 1)).astype(np.float32)
        out += np.asarray(Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32) / 255 * amp
        tot += amp; amp *= .5
    return out / tot


def save(name, rgb, a):
    img = np.dstack([np.broadcast_to(rgb, a.shape + (3,)) if np.ndim(rgb) == 1 else rgb, a])
    Image.fromarray((np.clip(img, 0, 1) * 255 + .5).astype(np.uint8), "RGBA").save(OUT / f"{name}.png")


# tyre tracks: two treads (1.8 m track) along V, 2.4 m x 8 m strip
W, H = 512, 1706
im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
for cx in (W * .5 - W * .375, W * .5 + W * .375):
    tw = W * .13
    for y in range(-40, H + 40, 22):
        wob = 6 * np.sin(y / 190)
        x = cx + wob
        d.polygon([(x - tw / 2, y), (x - tw * .05, y + 12), (x - tw * .05, y + 20), (x - tw / 2, y + 8)], fill=255)
        d.polygon([(x + tw / 2, y + 11), (x + tw * .05, y + 23), (x + tw * .05, y + 31), (x + tw / 2, y + 19)], fill=255)
    d.line([(cx - tw * .02, 0), (cx - tw * .02, H)], fill=160, width=3)
a = np.asarray(im.filter(ImageFilter.GaussianBlur(1.6)), np.float32) / 255
n = noise(H, W, 6, 4, 1); fade = np.clip(np.minimum(np.arange(H), H - np.arange(H)) / 260, 0, 1)[:, None]
a = a * np.clip(n * 1.6 - .25, 0, 1) * fade * .75
save("WG_DecalTyreTracks", np.array([.30, .24, .18]), a)

# oil / fuel stain
S = 1024; yy, xx = np.mgrid[0:S, 0:S] / S - .5
r = np.hypot(xx * 1.2, yy) + (noise(S, S, 5, 5, 2) - .5) * .25
a = np.clip((.36 - r) / .12, 0, 1) ** 1.2
a = a * (.55 + .45 * noise(S, S, 20, 3, 3)); a = np.maximum(a, np.clip((.2 - r) / .05, 0, 1) * .85)
save("WG_DecalOilStain", np.array([.06, .055, .05]), a * .9)

# sand spill: loose drifted sand with rippled edge
n1 = noise(S, S, 4, 5, 4); n2 = noise(S, S, 30, 3, 5)
r = np.hypot(xx, yy * 1.6)
a = np.clip((.42 - r + (n1 - .5) * .35) / .15, 0, 1) * (.75 + .25 * n2)
col = np.dstack([.72 + .06 * n2, .60 + .05 * n2, .44 + .04 * n2])
save("WG_DecalSandSpill", col, a)

# grime / dust skirt: darker at the bottom edge (wall/base contact), fading up
H2 = 512; g = np.linspace(1, 0, H2)[:, None] ** 1.6
n = noise(H2, S, 10, 4, 6)
a = np.clip(g * (.6 + .6 * n), 0, 1) * .7
col = np.dstack([.36 + .1 * n, .30 + .08 * n, .22 + .06 * n])
save("WG_DecalGrime", col, a)
print("decals written")
