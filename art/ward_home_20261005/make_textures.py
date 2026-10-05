"""Authored textures for the player's home (5 October 2026), Blender 5.2 headless (numpy), no real-world text.

Run:  ~/.local/state/ward-programme/blender.sh art/ward_home_20261005/make_textures.py
Writes art/ward_home_20261005/textures/HP_Insulation.png (512 x 512, tileable, 0.5 m: mineral-wool batt),
HP_Photo.png (512 x 768: a faded sepia snapshot of two figures by the Ward hill
tree, white border, scuffs) and HP_Calendar.png (768 x 1024: a paper wall calendar, a two-tone drawing of the hill
tree and the curtain wall over a 7 x 5 day grid, days crossed off in red, one ringed, two binding holes; no lettering
and no digits). The Unity pass copies them to Assets/AthenHill/Art/WardHome/Textures/ for HP_Photo / HP_Calendar.
"""
import bpy
import numpy as np
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "textures"
OUT.mkdir(exist_ok=True)
rng = np.random.default_rng(1005)


def save(img, name):
    h, w, _ = img.shape
    im = bpy.data.images.new(name, w, h, alpha=False)
    rgba = np.ones((h, w, 4), np.float32)
    rgba[:, :, :3] = np.clip(img, 0, 1)
    im.pixels.foreach_set(rgba[::-1].ravel())          # Blender rows run bottom-up
    im.filepath_raw = str(OUT / f"{name}.png")
    im.file_format = "PNG"
    im.save()
    print("wrote", OUT / f"{name}.png", flush=True)


def noise(h, w, scale, octaves=4):
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        s = max(1, int(scale / (2 ** o)))
        g = rng.random((h // s + 2, w // s + 2)).astype(np.float32)
        yy = np.linspace(0, h / s, h, endpoint=False)
        xx = np.linspace(0, w / s, w, endpoint=False)
        y0, x0 = yy.astype(int), xx.astype(int)
        fy, fx = (yy - y0)[:, None], (xx - x0)[None, :]
        fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
        a = g[y0][:, x0]
        b = g[y0][:, x0 + 1]
        c = g[y0 + 1][:, x0]
        d = g[y0 + 1][:, x0 + 1]
        out += amp * ((a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy)
        tot += amp
        amp *= 0.5
    return out / tot


def disc(Y, X, cy, cx, ry, rx):
    return ((Y - cy) / ry) ** 2 + ((X - cx) / rx) ** 2 <= 1.0


def photo():
    h, w = 768, 512
    Y, X = np.mgrid[0:h, 0:w].astype(np.float32)
    img = np.zeros((h, w, 3), np.float32)
    b = 34                                                       # white border
    iy, ix = Y - b, X - b
    ih, iw = h - 2 * b - 60, w - 2 * b                           # wider bottom border (instant-print style)
    inside = (iy >= 0) & (ix >= 0) & (iy < ih) & (ix < iw)
    t = np.clip(iy / ih, 0, 1)
    # sky gradient, warm ground; hill with the tree; two figures in front
    lum = 0.82 - 0.25 * t
    horizon = 0.62 + 0.04 * np.sin(ix / iw * 6.0)
    ground = t > horizon
    lum = np.where(ground, 0.52 - 0.12 * (t - horizon), lum)
    hill = (t > 0.45 + 0.25 * ((ix / iw - 0.62) / 0.35) ** 2) & ~ground
    lum = np.where(hill, 0.46, lum)
    trunk = (np.abs(ix - iw * 0.62) < 7 + 6 * (t - 0.3)) & (t > 0.28) & (t < 0.48)
    canopy = disc(iy, ix, ih * 0.22, iw * 0.62, ih * 0.13, iw * 0.27) | disc(iy, ix, ih * 0.27, iw * 0.47, ih * 0.08, iw * 0.15) | \
        disc(iy, ix, ih * 0.26, iw * 0.78, ih * 0.08, iw * 0.14)
    canopy &= noise(h, w, 10, 3)[Y.astype(int), X.astype(int)] > 0.35
    lum = np.where(trunk | canopy, 0.2, lum)
    for (cx, hh, ww) in ((0.3, 0.33, 0.06), (0.42, 0.29, 0.055)):
        body = (np.abs(ix - iw * cx) < iw * ww * (0.6 + 0.4 * (t - 0.55) / 0.4)) & (t > 0.98 - hh + 0.06) & (t < 0.98)
        head = disc(iy, ix, ih * (0.98 - hh + 0.03), iw * cx, ih * 0.03, iw * 0.033)
        lum = np.where(body | head, 0.16, lum)
    grain = noise(h, w, 2, 2) * 0.12 - 0.06
    vign = 1 - 0.55 * (((ix / iw - 0.5) * 1.4) ** 2 + ((iy / ih - 0.5) * 1.2) ** 2)
    lum = (lum + grain) * vign
    fade = 0.25
    lum = lum * (1 - fade) + 0.55 * fade
    sep = np.stack([lum * 1.08, lum * 0.9, lum * 0.66], -1)
    paper = np.stack([np.full((h, w), 0.86), np.full((h, w), 0.83), np.full((h, w), 0.74)], -1) - noise(h, w, 30, 3)[..., None] * 0.08
    img = np.where(inside[..., None], sep, paper)
    # scuffs and a crease
    for _ in range(40):
        y0, x0 = rng.integers(0, h), rng.integers(0, w)
        L = rng.integers(10, 60)
        a = rng.uniform(0, np.pi)
        for k in range(L):
            yy, xx = int(y0 + k * np.sin(a)), int(x0 + k * np.cos(a))
            if 0 <= yy < h and 0 <= xx < w:
                img[yy, xx] = img[yy, xx] * 0.6 + 0.35
    crease = np.abs((X - w * 0.3) - (Y - h * 0.1) * 0.15) < 1.5
    img[crease] = img[crease] * 0.8 + 0.15
    save(img, "HP_Photo")


def calendar():
    h, w = 1024, 768
    Y, X = np.mgrid[0:h, 0:w].astype(np.float32)
    paper = np.stack([np.full((h, w), 0.9), np.full((h, w), 0.87), np.full((h, w), 0.78)], -1)
    paper -= noise(h, w, 60, 4)[..., None] * 0.1
    paper -= (np.clip(Y / h - 0.85, 0, 1) * 0.3)[..., None] * np.array([0.3, 0.35, 0.5])      # damp at the foot
    img = paper.copy()
    madder = np.array([0.55, 0.16, 0.1])
    ochre = np.array([0.7, 0.48, 0.18])
    ink = np.array([0.18, 0.13, 0.1])
    # picture panel: ochre sky band, madder hill, ink tree and wall
    px0, px1, py0, py1 = 60, w - 60, 90, 470
    pic = (X >= px0) & (X < px1) & (Y >= py0) & (Y < py1)
    tt = (Y - py0) / (py1 - py0)
    ux = (X - px0) / (px1 - px0)
    img[pic & (tt < 0.55)] = img[pic & (tt < 0.55)] * 0.5 + ochre * 0.5
    hill = pic & (tt > 0.62 + 0.3 * ((ux - 0.5) / 0.45) ** 2)
    img[hill] = madder
    wall = pic & (tt > 0.78) & (tt < 0.86) & ((ux < 0.22) | (ux > 0.78))
    img[wall] = ink * 1.4
    for k in range(6):
        mx = 0.02 + k * 0.04 if k < 3 else 0.82 + (k - 3) * 0.06
        merl = pic & (tt > 0.74) & (tt <= 0.78) & (np.abs(ux - mx) < 0.012)
        img[merl] = ink * 1.4
    trunk = pic & (np.abs(ux - 0.5) < 0.015 + 0.02 * np.clip((tt - 0.4) / 0.25, 0, 1)) & (tt > 0.38) & (tt < 0.68)
    can = pic & (disc(Y, X, py0 + 0.3 * (py1 - py0), px0 + 0.5 * (px1 - px0), 0.18 * (py1 - py0), 0.22 * (px1 - px0)) |
                 disc(Y, X, py0 + 0.36 * (py1 - py0), px0 + 0.36 * (px1 - px0), 0.1 * (py1 - py0), 0.12 * (px1 - px0)) |
                 disc(Y, X, py0 + 0.35 * (py1 - py0), px0 + 0.64 * (px1 - px0), 0.1 * (py1 - py0), 0.12 * (px1 - px0)))
    can &= noise(h, w, 12, 3)[Y.astype(int), X.astype(int)] > 0.38
    img[trunk | can] = ink
    frame = pic & ((X < px0 + 4) | (X >= px1 - 4) | (Y < py0 + 4) | (Y >= py1 - 4))
    img[frame] = ink
    # day grid 7 x 5
    gx0, gx1, gy0, gy1 = 60, w - 60, 520, h - 70
    cw, ch = (gx1 - gx0) / 7, (gy1 - gy0) / 5
    grid = (X >= gx0) & (X <= gx1) & (Y >= gy0) & (Y <= gy1) & ((np.abs(((X - gx0) / cw) - np.round((X - gx0) / cw)) * cw < 1.5) |
                                                                 (np.abs(((Y - gy0) / ch) - np.round((Y - gy0) / ch)) * ch < 1.5))
    img[grid] = ink * 2.2
    # header band above the grid (weekday markers as dots, not letters)
    for c in range(7):
        cx = gx0 + (c + 0.5) * cw
        dot = disc(Y, X, gy0 - 22, cx, 6, 6)
        img[dot] = madder if c in (0, 6) else ink * 1.6
    # crossed-off days (red X) for the first 17 days, day 23 ringed
    red = np.array([0.7, 0.08, 0.06])
    for d in range(35):
        r, c = divmod(d, 7)
        cx, cy = gx0 + (c + 0.5) * cw, gy0 + (r + 0.5) * ch
        if 2 <= d <= 18:
            for sgn in (1, -1):
                line = (np.abs((X - cx) - sgn * (Y - cy) * cw / ch) < 3.2) & (np.abs(X - cx) < cw * 0.32) & (np.abs(Y - cy) < ch * 0.32)
                img[line] = red
        if d == 24:
            ringm = np.abs(np.sqrt(((X - cx) / (cw * 0.4)) ** 2 + ((Y - cy) / (ch * 0.4)) ** 2) - 1.0) < 0.06
            img[ringm] = red
        # a small pip for the day's place (no digits)
        pip = disc(Y, X, cy - ch * 0.3, cx - cw * 0.32, 3, 3)
        img[pip] = ink * 1.8
    # binding holes and a nail tear at the top
    for hx in (w * 0.3, w * 0.7):
        img[disc(Y, X, 40, hx, 9, 9)] = np.array([0.2, 0.18, 0.15])
    save(img, "HP_Calendar")


def pnoise(h, w, cells):
    """Tileable value noise: a periodic grid of cells x cells, smooth-interpolated."""
    g = rng.random((cells, cells)).astype(np.float32)
    yy = np.linspace(0, cells, h, endpoint=False)
    xx = np.linspace(0, cells, w, endpoint=False)
    y0, x0 = yy.astype(int), xx.astype(int)
    fy, fx = (yy - y0)[:, None], (xx - x0)[None, :]
    fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
    y1, x1 = (y0 + 1) % cells, (x0 + 1) % cells
    a, b, c, d = g[y0][:, x0], g[y0][:, x1], g[y1][:, x0], g[y1][:, x1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def insulation():
    """Mineral-wool batt, tileable (512 px = 0.5 m): ochre fibres, dark voids, a few pale tufts."""
    h = w = 512
    base = np.zeros((h, w), np.float32)
    amp = 1.0
    for cells in (4, 8, 16, 32, 64):
        base += amp * pnoise(h, w, cells)
        amp *= 0.55
    base /= base.max()
    # fibres: noise stretched along x (the batt's laid fibres), sharpened
    # fine fibres: high-frequency periodic noise, smeared along x (laid fibres) by averaging shifted copies
    fib = np.zeros((h, w), np.float32)
    for cells in (128, 256):
        n = pnoise(h, w, cells)
        for k in range(-4, 5):
            fib += np.roll(n, k * 2, axis=1)
    fib = (fib - fib.min()) / (fib.max() - fib.min())
    v = 0.6 * base + 0.4 * fib
    v = (v - v.min()) / (v.max() - v.min())
    dark = np.clip((0.3 - v) * 2.5, 0, 1)
    tone = 0.62 + 0.45 * v
    # muted mineral wool: pale ochre-grey, not saturated yellow (it read as a stained yellow board in Unity)
    col = np.stack([0.7 * tone, 0.6 * tone, 0.4 * tone], -1) * (1 - 0.5 * dark)[..., None]
    save(col, "HP_Insulation")


photo()
calendar()
insulation()
