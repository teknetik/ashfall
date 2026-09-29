"""Author the Basic General central back-panel board texture set (task t_6f2addb6, 29 Sep 2026).

A worn limewashed stock/tally board that hangs on the plain rear wall between the two hook rails. It exists to give the wall behind Mira a lighter,
higher-contrast, readable focal panel in shade. Deliberately no legible lettering (signs are authored separately): ruled ledger lines, tally groups,
price-slot blanks. Board is 0.86 m wide x 1.00 m tall (texture 2048^2 stretched to it; x density 2381 px/m, y 2048 px/m).
Deterministic. Usage: uv run --offline --with pillow --with numpy python author_back_panel_v1.py <Textures dir> [preview dir]
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

rng = np.random.default_rng(29092027)
T = Path(sys.argv[1]); PREV = Path(sys.argv[2]) if len(sys.argv) > 2 else None
N = 2048
BW, BH = 0.86, 1.00
FRAME = 0.055  # m
fx, fy = FRAME / BW * N, FRAME / BH * N  # frame thickness in px per axis


def fbm(scales, weights, aspect=(1, 1)):
    out = np.zeros((N, N), np.float32)
    for s, w in zip(scales, weights):
        gh, gw = max(2, int(N / s * aspect[1])), max(2, int(N / s * aspect[0]))
        g = Image.fromarray((rng.random((gh, gw)) * 255).astype(np.uint8)).resize((N, N), Image.Resampling.BICUBIC)
        out += w * (np.asarray(g, np.float32) / 255.0)
    out -= out.min(); out /= max(out.max(), 1e-6)
    return out


def blur(a, r):
    return np.asarray(Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r)), np.float32) / 255.0


yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
inframe = (xx < fx) | (xx > N - fx) | (yy < fy) | (yy > N - fy)
d_edge = np.minimum.reduce([xx, N - xx, yy, N - yy])

# base: limewash field, darker weathered frame
tone = fbm([300, 110, 30], [0.5, 0.35, 0.15])
field = np.array([0.70, 0.65, 0.53], np.float32)
frame = np.array([0.27, 0.22, 0.17], np.float32)
col = np.where(inframe[..., None], frame, field) * (0.86 + 0.28 * tone[..., None])
# plank seams (three vertical boards) and brush marks
seams = np.zeros((N, N), np.float32)
for sx in (N * 0.36, N * 0.66):
    seams += np.exp(-((xx - sx) / 2.5) ** 2) * (~inframe)
col *= (1 - 0.35 * seams[..., None])
brush = fbm([4, 200], [0.5, 0.5], aspect=(40, 0.05))
col *= (0.96 + 0.08 * brush[..., None] * (~inframe)[..., None])

# ink: ruled lines, header rule, tally groups, price slots (faded iron-gall brown)
ink_img = Image.new('L', (N, N), 0); dr = ImageDraw.Draw(ink_img)
x0, x1 = int(fx * 1.9), int(N - fx * 1.9)
y0 = int(fy * 2.2)
dr.rectangle([x0, y0, x1, y0 + 46], fill=170)  # header band
for i in range(1, 11):  # ruled ledger lines
    y = int(y0 + 46 + i * (N - fy * 2.2 - y0 - 46) / 11)
    dr.line([(x0, y), (x1, y + int(rng.integers(-3, 4)))], fill=int(rng.integers(110, 190)), width=int(rng.choice([3, 4, 5])))
colx = int(x0 + (x1 - x0) * 0.62)
dr.line([(colx, y0 + 46), (colx, int(N - fy * 2.2))], fill=150, width=4)  # price column rule
row_h = (N - fy * 2.2 - y0 - 46) / 11
for i in range(0, 11):
    yb = y0 + 46 + i * row_h
    if rng.random() < 0.85:  # tally group of up to five strokes, struck through
        n = int(rng.integers(1, 6)); tx = x0 + int(rng.integers(30, 260))
        for k in range(min(n, 4)):
            xk = tx + k * 34 + int(rng.integers(-3, 4))
            dr.line([(xk, yb + 14), (xk + int(rng.integers(-4, 5)), yb + row_h - 20)], fill=int(rng.integers(170, 235)), width=7)
        if n == 5: dr.line([(tx - 12, yb + row_h - 30), (tx + 3 * 34 + 14, yb + 22)], fill=200, width=7)
    if rng.random() < 0.7:  # price slot blank: short dash pair right of the column rule
        px = colx + 60 + int(rng.integers(0, 120))
        dr.rounded_rectangle([px, yb + row_h * 0.35, px + int(rng.integers(50, 110)), yb + row_h * 0.60], radius=6, outline=int(rng.integers(120, 190)), width=5)
    if rng.random() < 0.6:  # item mark (short stroke run standing in for a name; not lettering)
        sx = x0 + 340 + int(rng.integers(0, 80))
        for k in range(int(rng.integers(3, 7))):
            dr.line([(sx + k * 46, yb + row_h * 0.55), (sx + k * 46 + int(rng.integers(18, 40)), yb + row_h * 0.55 + int(rng.integers(-8, 9)))], fill=int(rng.integers(110, 170)), width=9)
ink = np.asarray(ink_img.filter(ImageFilter.GaussianBlur(1.3)), np.float32) / 255.0
ink *= 0.55 + 0.45 * fbm([12, 4], [0.6, 0.4])  # faded, uneven
ink_col = np.array([0.24, 0.17, 0.11], np.float32)
col = col * (1 - 0.85 * ink[..., None]) + ink_col * 0.85 * ink[..., None]

# painted muted-teal top stripe ties the board to the counter panels
stripe = ((yy > fy) & (yy < fy + 40) & (~inframe)).astype(np.float32)
col = col * (1 - stripe[..., None] * 0.7) + np.array([0.20, 0.36, 0.34], np.float32) * stripe[..., None] * 0.7

# grime: bottom-weighted plus drip streaks, hand-height scuffing, edge chipping on the frame
gn = fbm([80, 26], [0.6, 0.4])
hf = np.clip((yy - N * 0.45) / (N * 0.55), 0, 1)
grime = np.clip(hf ** 1.5 + (gn - 0.5) * 0.5 * hf, 0, 1)
col = col * (1 - 0.45 * grime[..., None]) + np.array([0.40, 0.31, 0.21], np.float32) * 0.18 * grime[..., None]
st = fbm([6, 260], [0.5, 0.5], aspect=(6, 0.05))
streaks = blur(np.clip((st - 0.64) * 3, 0, 1), 1.6) * np.clip((yy - 300) / 900, 0, 1) * 0.3
col *= (1 - streaks[..., None] * 0.5)
chip_n = fbm([30, 10, 3], [0.45, 0.35, 0.2])
reach = 12 + 40 * fbm([120, 40], [0.6, 0.4])
chip = ((chip_n > 0.66) & (d_edge < reach)).astype(np.float32)
chip_soft = blur(chip, 1.2)
col = col * (1 - chip_soft[..., None]) + np.array([0.43, 0.41, 0.37], np.float32) * chip_soft[..., None]
# gentle contrast about the mean
mean = col.mean(axis=(0, 1), keepdims=True)
col = np.clip(mean + (col - mean) * 1.10, 0, 1)

# metal/smooth: limewash and paint are non-metal (bare steel only in frame chips); rough, slightly smoother frame and scuff
ms = np.zeros((N, N, 4), np.float32)
ms[..., 0] = chip_soft * 0.6
ms[..., 3] = np.clip(np.where(inframe, 0.34, 0.16) * (1 - 0.4 * grime) + 0.25 * chip_soft + 0.06 * ink, 0.03, 0.85)

# normal (OpenGL +Y): plank seams, frame step, ink relief, chips
hgt = (~inframe).astype(np.float32) * -0.35 + seams * -0.15 + ink * 0.06 - chip_soft * 0.25 + (tone - 0.5) * 0.03
hgt = blur(np.clip(hgt + 1, 0, 2) / 2, 1.2) * 2 - 1
gy, gx = np.gradient(hgt)
n = np.stack([-gx * 28, gy * 28, np.ones((N, N), np.float32)], -1)
n /= np.linalg.norm(n, axis=-1, keepdims=True)
nm = np.clip(n * 0.5 + 0.5, 0, 1)


def save(a, name, mode):
    Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8), mode).save(T / name)


save(col, 'BGC_BackPanel_BaseColor.png', 'RGB')
save(ms, 'BGC_BackPanel_MetalSmooth.png', 'RGBA')
save(nm, 'BGC_BackPanel_Normal.png', 'RGB')
print('wrote back panel set; mean colour', col.mean(axis=(0, 1)).round(3))
if PREV:
    PREV.mkdir(parents=True, exist_ok=True)
    Image.fromarray((col * 255).astype(np.uint8)).resize((880, 1024)).save(PREV / 'back_panel_preview.png')
