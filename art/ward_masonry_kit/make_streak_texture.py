"""Tileable runoff streak mask for Athen Hill/Masonry Lit (30 Sep 2026).

R = dark grime runoff, G = pale mineral/dust deposit, B = narrow rust trails. Sampled in world space on walls
(one tile ~2.2 m wide x 8 m tall); the per-vertex runoff/rust weights baked by ward_masonry.py decide where it shows.
Run: uv run --with numpy --with pillow python art/ward_masonry_kit/make_streak_texture.py
"""
import numpy as np
from pathlib import Path
from PIL import Image

W, H = 1024, 2048
rng = np.random.default_rng(20260930)
OUT = Path(__file__).resolve().parents[2] / "unity/AthenHill/Assets/AthenHill/Art/VanguardHall/Textures/WardRunoff_Streaks.png"

def value_noise_1d(n, cells, rng):
    pts = rng.random(cells + 1); pts[-1] = pts[0]
    x = np.linspace(0, cells, n, endpoint=False); i = x.astype(int); f = x - i; f = f * f * (3 - 2 * f)
    return pts[i] * (1 - f) + pts[i + 1] * f

def layer(count, wmin, wmax, lmin, lmax, amp, wobble):
    img = np.zeros((H, W), np.float32)
    ys = np.arange(H)
    for _ in range(count):
        x0 = rng.uniform(0, W); w = rng.uniform(wmin, wmax); y0 = rng.uniform(0, H); L = rng.uniform(lmin, lmax)
        a = amp * rng.uniform(0.35, 1.0)
        # streak runs downwards (increasing image row = lower on the wall), wrapping vertically
        dy = (ys - y0) % H
        along = np.clip(dy / L, 0, None)
        fade = np.where(dy < L, np.clip(1 - along, 0, 1) ** rng.uniform(0.6, 1.6), 0.0)
        # soft start (drip gathers) and noisy intensity along the trail
        fade *= np.clip(dy / (0.05 * L + 1), 0, 1)
        fade *= 0.65 + 0.35 * value_noise_1d(H, int(rng.integers(6, 30)), rng)
        xs = x0 + wobble * (value_noise_1d(H, int(rng.integers(3, 9)), rng) - 0.5) * w
        # widen slightly as it runs down
        ww = w * (1 + 0.8 * along.clip(0, 1))
        cols = np.arange(W)[None, :]
        d = (cols - xs[:, None] + W / 2) % W - W / 2
        prof = np.exp(-(d / ww[:, None]) ** 2 * 2.2)
        img = np.maximum(img, prof * (fade * a)[:, None]) if rng.random() < 0.5 else img + prof * (fade * a * 0.6)[:, None]
    return img

def grain(scale, amt):
    small = rng.random((H // scale, W // scale)).astype(np.float32)
    im = np.array(Image.fromarray((small * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32) / 255
    return 1 - amt + amt * im

r = layer(170, 1.5, 11, 250, 1700, 1.0, 1.6) + 0.5 * layer(90, 6, 26, 300, 1200, 0.5, 2.5)
r = np.clip(r * grain(4, 0.35) * grain(16, 0.3), 0, 1)
g = layer(140, 1.2, 7, 150, 900, 1.0, 1.2) * grain(4, 0.4)
g = np.clip(g, 0, 1)
b = layer(160, 0.8, 5, 150, 1000, 1.0, 0.8) * grain(8, 0.3)
b = np.clip(b, 0, 1)
rgb = np.stack([r, g, b], -1)
Image.fromarray((rgb * 255 + 0.5).astype(np.uint8), "RGB").save(OUT)
print("wrote", OUT, rgb.mean(axis=(0, 1)))
