"""Author the Basic General counter-face v2 texture set (task t_6f2addb6, 29 Sep 2026).

Reads the untouched v1 BaseColor / MetalSmooth / Normal PNGs and writes *_v2 siblings (v1 is never modified).
Adds only material breakup to the three face panels: paint-chip edge wear with bare-steel exposure, hand-height scuffing, low-frequency tone
variation, bottom-weighted dust/grime with drip streaks, fine scratches. The plinth strip and the dark panel gaps keep their v1 pixels.
Deterministic (fixed seed). Usage: uv run --offline --with pillow --with numpy python author_counter_face_v2.py <Textures dir> [preview dir]
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

rng = np.random.default_rng(29092026)
T = Path(sys.argv[1]); PREV = Path(sys.argv[2]) if len(sys.argv) > 2 else None
W, H = 4096, 1024
PANELS = [(70, 1342), (1406, 2689), (2754, 4027)]  # x ranges (v1 dark gap columns excluded)
PANEL_BOTTOM = 935  # plinth strip starts below this row


def fbm(scales, weights, aspect=(1, 1)):
    out = np.zeros((H, W), np.float32)
    for s, w in zip(scales, weights):
        gh, gw = max(2, int(H / s * aspect[1])), max(2, int(W / s * aspect[0]))
        g = Image.fromarray((rng.random((gh, gw)) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)
        out += w * (np.asarray(g, np.float32) / 255.0)
    out -= out.min(); out /= max(out.max(), 1e-6)
    return out


def blur(a, r):
    return np.asarray(Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r)), np.float32) / 255.0


base = np.asarray(Image.open(T / 'BGC_CounterFace_BaseColor.png').convert('RGB'), np.float32) / 255.0
ms = np.asarray(Image.open(T / 'BGC_CounterFace_MetalSmooth.png').convert('RGBA'), np.float32) / 255.0
nrm = np.asarray(Image.open(T / 'BGC_CounterFace_Normal.png').convert('RGB'), np.float32) / 255.0

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
mask = np.zeros((H, W), np.float32)      # 1 inside the three panels above the plinth
edge = np.full((H, W), 9999, np.float32)  # distance to nearest panel edge
for x0, x1 in PANELS:
    m = (xx >= x0) & (xx < x1) & (yy < PANEL_BOTTOM)
    mask[m] = 1
    d = np.minimum.reduce([xx - x0, x1 - xx, yy - 0, PANEL_BOTTOM - yy])
    edge = np.where(m, np.minimum(edge, d), edge)
mask = blur(mask, 2)

# 1. tone breakup: two scales, kept subtle so each panel keeps its hue
tone = fbm([260, 90], [0.65, 0.35])
lum = 1.0 + (tone - 0.5) * 0.34
# 2. bottom-weighted dust/grime with an irregular upper edge and vertical drips
grime_n = fbm([70, 24], [0.6, 0.4])
height_frac = np.clip((yy - 380) / (PANEL_BOTTOM - 380), 0, 1)
grime = np.clip(height_frac ** 1.6 * 1.05 + (grime_n - 0.5) * 0.55 * height_frac, 0, 1)
streak_src = fbm([6, 260], [0.5, 0.5], aspect=(6, 0.05))  # thin, tall features = drips
streaks = blur(np.clip((streak_src - 0.64) * 3.0, 0, 1), 1.5) * np.clip((yy - 200) / 500, 0, 1) * 0.35
# 3. paint chipping at the panel edges and around fixings (wear at joints, not uniform)
chip_n = fbm([26, 9, 3], [0.45, 0.35, 0.2])
reach = 10 + 34 * fbm([110, 40], [0.6, 0.4])
chip = ((chip_n > 0.70 - 0.16 * np.clip(1 - edge / reach, 0, 1)) & (edge < reach)).astype(np.float32)
chip *= (edge < reach).astype(np.float32)
chip_soft = blur(chip, 1.2)
rim = np.clip(blur(np.asarray(Image.fromarray((chip * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(7)), np.float32) / 255.0, 1.5) - chip_soft, 0, 1)
# 4. hand scuffing: pale worn zone mid-height, right of each handle mark
scuff = np.zeros((H, W), np.float32)
for x0, x1 in PANELS:
    cx = x0 + 0.72 * (x1 - x0); cy = 430
    scuff += np.exp(-(((xx - cx) / 260) ** 2 + ((yy - cy) / 150) ** 2))
scuff = np.clip(scuff * (0.4 + 0.6 * fbm([14, 5], [0.6, 0.4])), 0, 1)
# 5. fine scratches
sc = Image.new('L', (W, H), 0); dr = ImageDraw.Draw(sc)
for x0, x1 in PANELS:
    for _ in range(45):
        x = rng.uniform(x0 + 20, x1 - 20); y = rng.uniform(40, PANEL_BOTTOM - 40)
        ang = rng.normal(0, 0.35) if rng.random() < 0.7 else rng.uniform(-1.5, 1.5); ln = rng.uniform(25, 150)
        dr.line([(x, y), (x + ln * np.cos(ang), y + ln * np.sin(ang))], fill=int(rng.uniform(90, 255)), width=int(rng.choice([1, 1, 2])))
scr = np.asarray(sc.filter(ImageFilter.GaussianBlur(0.6)), np.float32) / 255.0

steel = np.array([0.46, 0.43, 0.39], np.float32)
rust = np.array([0.34, 0.18, 0.09], np.float32)
dust = np.array([0.47, 0.37, 0.25], np.float32)

col = base * lum[..., None]
col = col * (1 - 0.55 * grime[..., None]) + dust * (0.22 * grime[..., None])
col = col * (1 - streaks[..., None] * 0.6) + dust * 0.6 * streaks[..., None] * 0.3
col = col + scuff[..., None] * 0.10 * (np.array([1.0, 0.95, 0.8], np.float32))
col = col * (1 - rim[..., None] * 0.9) + rust * rim[..., None] * 0.9
col = col * (1 - chip_soft[..., None]) + steel * (0.75 + 0.25 * tone[..., None]) * chip_soft[..., None]
col = np.where(scr[..., None] > 0.15, col + (steel - col) * 0.35 * scr[..., None], col)
# gentle contrast curve about the panel mean so the face reads in shade without changing its hue
mean = col.mean(axis=(0, 1), keepdims=True)
col = np.clip(mean + (col - mean) * 1.16, 0, 1)
out_col = base * (1 - mask[..., None]) + col * mask[..., None]

# metallic-smoothness: chips = bare steel (metallic ~0.6, smoother); grime rougher; scuff smoother; paint keeps v1 smoothness
m = ms.copy()
metal = np.clip(chip_soft * 0.62 + scr * 0.18, 0, 1)
smooth = ms[..., 3] * (1 - 0.45 * grime) * (1 - 0.3 * streaks) + 0.20 * scuff + 0.22 * chip_soft
m[..., 0] = ms[..., 0] * (1 - mask) + np.maximum(ms[..., 0], metal) * mask
m[..., 3] = ms[..., 3] * (1 - mask) + np.clip(smooth, 0.03, 0.92) * mask

# normal: chip depressions and scratches folded into the v1 slopes (OpenGL +Y, so green is up)
hgt = blur(1.0 - chip, 1.6) * 0.9 + (1 - scr) * 0.25 + rim * 0.0
gy, gx = np.gradient(hgt)
n = nrm * 2 - 1
strength = 5.0
n[..., 0] = n[..., 0] - gx * strength * mask
n[..., 1] = n[..., 1] + gy * strength * mask
n[..., 2] = np.sqrt(np.clip(1 - n[..., 0] ** 2 - n[..., 1] ** 2, 0.05, 1))
ln_ = np.linalg.norm(n, axis=-1, keepdims=True); n = n / ln_
out_n = np.clip((n * 0.5 + 0.5), 0, 1)

def save(a, name, mode):
    Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8), mode).save(T / name, optimize=False)

save(out_col, 'BGC_CounterFace_v2_BaseColor.png', 'RGB')
save(m, 'BGC_CounterFace_v2_MetalSmooth.png', 'RGBA')
save(out_n, 'BGC_CounterFace_v2_Normal.png', 'RGB')
print('wrote v2 set; chip coverage in panels %.3f, grime mean %.3f' % (float((chip * mask).sum() / mask.sum()), float((grime * mask).sum() / mask.sum())))
if PREV:
    PREV.mkdir(parents=True, exist_ok=True)
    Image.fromarray((out_col * 255).astype(np.uint8)).resize((2048, 512)).save(PREV / 'face_v2_base_preview.png')
    Image.fromarray((base * 255).astype(np.uint8)).resize((2048, 512)).save(PREV / 'face_v1_base_preview.png')
