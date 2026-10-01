"""Wall-foot drift textures (1 October 2026): the loose-sand material and the dust/grime decals.

Run:  $O/heavy.sh uv run --with pillow --with numpy python make_textures.py      ($O = /home/teknetik/.local/state/ward-programme)

Sand (tiles every 1.5 m on the drift meshes' planar UV0):
  WFD_Sand_BaseMap.png  2048 sRGB. The CC0 Poly Haven scan `dense_sand` (the Ward masonry kit's sand, already in
                        art/vanguard_hall_20260930/polyhaven) with its crusted low-frequency blotches flattened (loose,
                        wind-sorted sand is even in tone), graded to the Ward dust colour (the paving's _DustColor
                        0.8/0.7/0.56 and the masonry _DustTint), plus sparse light quartz and dark lithic grains.
  WFD_Sand_Normal.png   2048 linear, OpenGL (+Y up). The scan's normal at 45 % strength (grain, no crust) plus wind
                        ripples: 20 crests per tile (7.5 cm apart), asymmetric (gentle stoss, steep lee), warped and
                        amplitude-modulated by periodic noise so some patches are smooth. Crests run along U.
Decals (URP projectors with the Ward weathering decal shader: albedo + alpha only):
  WFD_DecalFootBand.png  2048 x 512, repeats along U (2 m of wall per tile): wind-laid sand dust on the ground at a
                         wall foot. V = 0 against the wall, fading out by V = 1 with a lobed, grainy edge.
  WFD_DecalWallSkirt.png 2048 x 512, repeats along U: on the wall face, V = 0 at the ground. A dark contact/splash grime
                         line at the foot, spatter above it and a pale dust coating fading out at an uneven height.
  WFD_DecalPost.png      1024 x 1024: sand round a post footing (centre at U 0.5, V 0.3) with a lee tail towards V = 1.
  WFD_DecalSheet.png     1024 x 1024: a lobed patch of thin sand for alley floors and lee pockets.
All procedural noise is periodic (FFT-filtered), so the tiling textures repeat seamlessly.
"""
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SRC = ROOT / "art/vanguard_hall_20260930/polyhaven/dense_sand"
OUT = ROOT / "unity/AthenHill/Assets/AthenHill/Art/WallFootDrifts/Textures"
OUT.mkdir(parents=True, exist_ok=True)
REV = HERE / "review"
REV.mkdir(exist_ok=True)
rng = np.random.default_rng(20261001)

DUST = np.array([0.80, 0.70, 0.56])          # Ward dust colour (sRGB 0-1), paving _DustColor / masonry _DustTint
# Calibrated on the first editor captures (1 Oct, editor-r1): at the dust colour the sand rendered ~1.6x brighter and
# greyer than the flags beside it (the paving shader's cavity occlusion and warm per-flag tint darken and warm the flags),
# reading as snow in shade. Loose sand now sits a little above the flags' rendered value and in their warm hue.
SAND_MEAN = np.array([0.665, 0.545, 0.415])     # target mean of the loose sand albedo (sRGB)
FILM = np.array([0.68, 0.555, 0.42])         # thin sand/dust film decals on the ground
WALL_DUST = np.array([0.70, 0.59, 0.46])     # dust coating on the wall foot


def s2l(c):
    c = np.asarray(c, np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def l2s(c):
    c = np.clip(np.asarray(c, np.float32), 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def pnoise(h, w, cutoff, seed, aniso=(1.0, 1.0)):
    """Periodic band-limited noise in [-1, 1]: white noise filtered in frequency space (Gaussian low-pass)."""
    r = np.random.default_rng(seed)
    f = np.fft.fft2(r.standard_normal((h, w)))
    fy = np.fft.fftfreq(h)[:, None] * h / aniso[0]
    fx = np.fft.fftfreq(w)[None, :] * w / aniso[1]
    k = np.exp(-(fx ** 2 + fy ** 2) / (2 * cutoff ** 2))
    n = np.real(np.fft.ifft2(f * k))
    return (n / (np.abs(n).max() + 1e-9)).astype(np.float32)


def blur_wrap(a, sigma):
    h, w = a.shape[:2]
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    k = np.exp(-2 * (np.pi * sigma) ** 2 * (fx ** 2 + fy ** 2))
    if a.ndim == 2:
        return np.real(np.fft.ifft2(np.fft.fft2(a) * k)).astype(np.float32)
    return np.stack([blur_wrap(a[..., c], sigma) for c in range(a.shape[2])], -1)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def save_rgba(path, rgb_srgb, alpha):
    img = np.concatenate([np.clip(rgb_srgb, 0, 1), np.clip(alpha, 0, 1)[..., None]], -1)
    Image.fromarray((img * 255 + 0.5).astype(np.uint8), "RGBA").save(path)


# ====================================================================== sand material
def sand():
    diff = np.asarray(Image.open(SRC / "dense_sand_diff_2k.jpg").convert("RGB"), np.float32) / 255
    nor = np.asarray(Image.open(SRC / "dense_sand_nor_gl_2k.jpg").convert("RGB"), np.float32) / 255
    H, W = diff.shape[:2]
    lin = s2l(diff)
    fine = blur_wrap(lin, 9)
    mid = blur_wrap(lin, 60)
    hi = lin / (fine + 1e-4)                       # grain detail only
    band = fine / (mid + 1e-4)                     # crust blotches (dried patches): mostly removed
    mm = mid.mean((0, 1))
    lin2 = mm * (1 + 0.3 * (mid / mm - 1)) * (1 + 0.3 * (band - 1)) * (1 + 0.9 * (hi - 1))
    # sparse quartz (light) and lithic (dark) grains, 1-2 px
    g = rng.random((H, W))
    lin2 = np.where((g > 0.9965)[..., None], lin2 * 1.45, lin2)
    lin2 = np.where((g < 0.0025)[..., None], lin2 * 0.55, lin2)
    # grade to the target mean colour (per channel gain in linear)
    gain = s2l(SAND_MEAN) / lin2.reshape(-1, 3).mean(0)
    lin2 = lin2 * gain
    rgb = l2s(lin2)
    Image.fromarray((np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8), "RGB").save(OUT / "WFD_Sand_BaseMap.png")

    # ---- normal: scan grain (45 %) + wind ripples
    n = nor * 2 - 1
    nx, ny = n[..., 0] * 0.45, n[..., 1] * 0.45
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    warp = pnoise(H, W, 3.0, 5) * 0.9 + pnoise(H, W, 7.0, 6) * 0.25          # in ripple wavelengths
    crests = 20
    ph = (yy / H * crests + warp) % 1.0                                        # crests run along U (x)
    # asymmetric ripple profile: long gentle stoss rising to the crest at 0.7, short steep lee
    prof = np.where(ph < 0.7, ph / 0.7, (1.0 - ph) / 0.3)
    prof = smoothstep(0, 1, prof)
    amp = np.clip(0.55 + 0.75 * pnoise(H, W, 2.5, 7), 0, 1) ** 1.5           # smooth patches between rippled ones
    hgt = prof * amp * 0.0028                                                  # metres (2.8 mm crest)
    texel = 1.5 / H                                                            # metres per texel (1.5 m tile)
    dhdy = (np.roll(hgt, -1, 0) - np.roll(hgt, 1, 0)) / (2 * texel)
    dhdx = (np.roll(hgt, -1, 1) - np.roll(hgt, 1, 1)) / (2 * texel)
    rx, ry = -dhdx, dhdy                                                       # image rows run down; OpenGL +Y = up the texture
    nx2, ny2 = nx + rx, ny + ry
    nz2 = np.sqrt(np.clip(1 - nx2 ** 2 - ny2 ** 2, 0.05, 1))
    nn = np.stack([nx2, ny2, nz2], -1)
    nn /= np.linalg.norm(nn, axis=-1, keepdims=True)
    Image.fromarray(((nn * 0.5 + 0.5) * 255 + 0.5).astype(np.uint8), "RGB").save(OUT / "WFD_Sand_Normal.png")
    Image.fromarray((np.clip(rgb[:768, :768], 0, 1) * 255).astype(np.uint8)).save(REV / "tex_sand_base_crop.jpg")
    Image.fromarray(((nn[:768, :768] * 0.5 + 0.5) * 255).astype(np.uint8)).save(REV / "tex_sand_normal_crop.jpg")
    print("sand mean sRGB", (rgb.reshape(-1, 3).mean(0) * 255).round(1))


# ====================================================================== decals
def grain_rgb(h, w, base, var, seed):
    """Dusty sand colour with fine speckle and a broad periodic tint drift (sRGB 0-1)."""
    r = np.random.default_rng(seed)
    sp = r.random((h, w)).astype(np.float32)
    broad = pnoise(h, w, 4.0, seed + 1)
    v = 1 + var * (0.6 * broad + 0.8 * (sp - 0.5))
    return np.clip(np.asarray(base)[None, None, :] * v[..., None], 0, 1)


def end_fade(w, frac=0.12):
    """1 in the middle, easing to 0 over the first/last `frac` of U, so overlapping segments blend without seams."""
    u = (np.arange(w, dtype=np.float32) + 0.5) / w
    return (smoothstep(0.0, frac, u) * smoothstep(0.0, frac, 1.0 - u))[None, :]


def foot_band():
    h, w = 512, 2048
    v = (np.arange(h, dtype=np.float32) / (h - 1))[:, None] * np.ones((1, w), np.float32)
    # V = 0 against the wall: the image's first row is the texture's top (V = 1), so build in V and flip at the end
    reach = 0.8 + 0.14 * pnoise(1, w, 3.0, 11)[0][None, :]                   # how far the film runs out (0-1)
    patches = pnoise(h, w, 14.0, 13, aniso=(1.0, 3.0))                       # soft patches stretched along the wall
    grit = pnoise(h, w, 90.0, 14)
    # a plateau over the drift toes (V 0-0.4), easing out to nothing at the reach: it feathers the sand into the paving
    a = 1 - smoothstep(0.32 * reach, reach, v + 0.12 * patches)
    a = a * (0.85 + 0.15 * grit)
    a = np.clip(a, 0, 1) * 0.55 * end_fade(w)
    rgb = grain_rgb(h, w, FILM, 0.06, 16)
    save_rgba(OUT / "WFD_DecalFootBand.png", rgb[::-1], a[::-1])
    return a


def wall_skirt():
    h, w = 512, 2048
    v = (np.arange(h, dtype=np.float32) / (h - 1))[:, None] * np.ones((1, w), np.float32)
    # pale dust coating, strongest at the foot, fading out at an uneven, soft height
    top = 0.65 + 0.15 * pnoise(1, w, 3.0, 21)[0][None, :] + 0.04 * pnoise(1, w, 9.0, 22)[0][None, :]
    dust = np.clip(1 - v / top + 0.08 * pnoise(h, w, 10.0, 23, aniso=(1.0, 2.5)), 0, 1) ** 1.6 * 0.34
    # contact grime: a dark ragged band at the foot with fine spatter above it
    gtop = 0.07 + 0.025 * pnoise(1, w, 10.0, 24)[0][None, :]
    grime = (1 - smoothstep(gtop * 0.35, gtop, v + 0.01 * pnoise(h, w, 40.0, 25))) * 0.5
    g = np.random.default_rng(26).random((h, w)).astype(np.float32)
    spat = ((g > 0.9985) & (v < 0.25)) * (1 - v / 0.25)
    spat = blur_wrap(spat.astype(np.float32), 0.7) * 6
    grime = np.clip(grime + spat * 0.6, 0, 0.6)
    dust_rgb = grain_rgb(h, w, WALL_DUST, 0.05, 27)
    grime_rgb = grain_rgb(h, w, np.array([0.33, 0.26, 0.2]), 0.08, 28)
    a = 1 - (1 - dust) * (1 - grime)
    wgt = np.where(a > 1e-4, grime / np.maximum(a, 1e-4), 0)[..., None]
    rgb = dust_rgb * (1 - wgt) + grime_rgb * wgt
    a = a * end_fade(w, 0.1)
    save_rgba(OUT / "WFD_DecalWallSkirt.png", rgb[::-1], a[::-1])
    return a


def post_ring():
    n = 1024
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32) / (n - 1)
    u, v = xx - 0.5, (1 - yy) - 0.3                       # V up the texture; centre at (0.5, 0.3)
    r = np.hypot(u, v)
    th = np.arctan2(u, v)
    # an uneven collar (thicker upwind, scalloped) that thins into a long lee tongue; no clean disc edge
    rr = 0.2 + 0.05 * np.cos(th * 3 + 1) + 0.04 * pnoise(n, n, 6.0, 33) + 0.05 * np.clip(-np.cos(th), 0, 1)
    ring = (1 - smoothstep(0.06, rr, r)) * (0.6 + 0.4 * np.clip(-np.cos(th), 0, 1))
    tail = np.exp(-(u / (0.09 + 0.1 * np.clip(v, 0, None))) ** 2 - (np.clip(v - 0.1, 0, None) / 0.45) ** 2) * (v > -0.05)
    a = np.maximum(ring, tail * 0.8)
    a = np.clip(a * (0.8 + 0.35 * pnoise(n, n, 18.0, 31)), 0, 1) ** 1.3 * 0.55
    a *= 1 - smoothstep(0.44, 0.5, np.maximum(np.abs(xx - 0.5), np.abs(yy - 0.5)))   # clear at the borders
    rgb = grain_rgb(n, n, FILM, 0.07, 32)
    save_rgba(OUT / "WFD_DecalPost.png", rgb, a)
    return a


def sheet():
    n = 1024
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32) / (n - 1)
    a = np.zeros((n, n), np.float32)
    for (cx, cy, sx, sy, k) in [(0.42, 0.5, 0.26, 0.18, 1.0), (0.62, 0.45, 0.22, 0.16, 0.85), (0.5, 0.6, 0.2, 0.14, 0.7),
                                (0.3, 0.42, 0.13, 0.1, 0.6), (0.72, 0.58, 0.12, 0.09, 0.55)]:
        a = np.maximum(a, k * np.exp(-(((xx - cx) / sx) ** 2 + ((yy - cy) / sy) ** 2)))
    a = smoothstep(0.1, 0.85, a + 0.12 * pnoise(n, n, 16.0, 41) + 0.05 * pnoise(n, n, 50.0, 42)) * 0.55
    a *= 1 - smoothstep(0.44, 0.5, np.maximum(np.abs(xx - 0.5), np.abs(yy - 0.5)))
    rgb = grain_rgb(n, n, FILM, 0.07, 43)
    save_rgba(OUT / "WFD_DecalSheet.png", rgb, a)
    return a


def preview(name, a, rgb_bg=(0.72, 0.62, 0.5)):
    p = np.asarray(Image.open(OUT / name).convert("RGBA"), np.float32) / 255
    bg = np.ones_like(p[..., :3]) * np.asarray(rgb_bg)
    comp = bg * (1 - p[..., 3:]) + p[..., :3] * p[..., 3:]
    Image.fromarray((comp * 255).astype(np.uint8)).save(REV / ("tex_" + name.replace(".png", ".jpg")))


if __name__ == "__main__":
    sand()
    foot_band(); wall_skirt(); post_ring(); sheet()
    preview("WFD_DecalFootBand.png", None)
    preview("WFD_DecalWallSkirt.png", None, (0.6, 0.5, 0.38))
    preview("WFD_DecalPost.png", None)
    preview("WFD_DecalSheet.png", None)
    print("wrote", sorted(p.name for p in OUT.glob("*.png")))
