#!/usr/bin/env python3
"""Ward city paving (1 Oct 2026): bake a 4 x 4 m dressed-sandstone flag tile.

Layout: 8 courses of 0.5 m running east-west (texture u = world X), flags 0.5-1.25 m long in running bond, no stacked
joints, all course lines are joints. The shader (WardPavingLit) shifts every world course by a random offset, so the
4 m tile never shows as a lattice; course k of the texture is always world course k mod 8.

Per flag: a random 1:1 crop of the CC0 scan worn_rock_natural_01 (the Ward masonry kit's ashlar stone, 1 mm/px), graded
to the Ward sandstone palette with per-flag tone/hue, a laying tilt (uneven flags catch grazing light differently),
eroded and chipped arrises, rare cracks and stains. Joints 8-15 mm, filled with sand 4-7 mm below the arris.

Outputs (out/): PV_Flags_BaseMap.png (sRGB), PV_Flags_Normal.png (OpenGL +Y), PV_Flags_Mask.png (R flag id (k+0.5)/32,
0 in joints, G cavity AO, B height 0 joint..1 flag top, A smoothness) at 4k source and 2k shipping size, plus
PV_Grain_Normal.png (1 m tileable close-range grain, high-passed from the same scan) and layout.json.
Run through heavy.sh (numpy over 4k arrays): heavy.sh uv run --with pillow --with numpy python author_paving.py
"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
HERE = Path(__file__).resolve().parent
SRC = HERE / "polyhaven"
OUT = HERE / "out"
N = 4096                    # px per 4 m tile (0.977 mm/px)
MM = 4000.0 / N             # mm per px
COURSES = 8
CH = N // COURSES           # course height in px (0.5 m)
rng = np.random.default_rng(20261001)
f32 = np.float32


# ----------------------------------------------------------------- helpers
def load(path, mode=None):
    im = Image.open(path)
    if mode: im = im.convert(mode)
    return np.asarray(im)


def srgb_to_lin(c): return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4).astype(f32)
def lin_to_srgb(c): return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(np.maximum(c, 0), 1 / 2.4) - 0.055).astype(f32)


def periodic_noise(n, scale_px, seed, octaves=4, persistence=0.55):
    """Tileable fractal noise in [-1,1]-ish: FFT-filtered white noise (periodic by construction)."""
    r = np.random.default_rng(seed)
    fy = np.fft.fftfreq(n).astype(f32)[:, None]; fx = np.fft.rfftfreq(n).astype(f32)[None, :]
    k2 = fx * fx + fy * fy
    out = np.zeros((n, n), f32); amp = 1.0; s = scale_px; total = 0
    for _ in range(octaves):
        w = r.standard_normal((n, n)).astype(f32)
        sigma = 1.0 / (2 * np.pi * s)                           # gaussian low-pass at ~s px features
        filt = np.exp(-k2 / (2 * sigma * sigma)).astype(f32)
        o = np.fft.irfft2(np.fft.rfft2(w) * filt, s=(n, n)).astype(f32)
        o /= (o.std() + 1e-8)
        out += amp * o; total += amp; amp *= persistence; s /= 2.1
    return out / total


def blur_periodic(a, sigma_px):
    n0, n1 = a.shape
    fy = np.fft.fftfreq(n0).astype(f32)[:, None]; fx = np.fft.rfftfreq(n1).astype(f32)[None, :]
    filt = np.exp(-2 * (np.pi ** 2) * (sigma_px ** 2) * (fx * fx + fy * fy)).astype(f32)
    return np.fft.irfft2(np.fft.rfft2(a) * filt, s=a.shape).astype(f32)


def save_rgb(a, path, size=None, srgb_in_linear=False):
    a = np.clip(a, 0, 1)
    im = Image.fromarray((a * 255 + .5).astype(np.uint8))
    if size and size != im.size[0]: im = im.resize((size, size), Image.LANCZOS)
    im.save(path)


# ----------------------------------------------------------------- layout
def make_layout():
    lengths = [4, 5, 6, 7, 8, 10]                   # x 0.125 m -> 0.5 .. 1.25 m
    weights = np.array([2, 3, 4, 3, 4, 2], float); weights /= weights.sum()
    courses = []
    for c in range(COURSES):
        fallback = None
        for attempt in range(4000):
            seq = []; tot = 0
            while tot < 32:
                l = int(rng.choice(lengths, p=weights))
                if tot + l > 32: l = 32 - tot
                if l < 4: break
                seq.append(l); tot += l
            if tot != 32 or len(seq) < 3: continue
            if fallback is None: fallback = list(seq)
            phase = 0     # a joint at every tile edge: the shader's per-instance flag hash (course, tile) never splits a flag
            joints = sorted(((phase + int(np.sum(seq[:i]))) % 32) for i in range(len(seq)))
            ok = True
            for prev in ([courses[-1]] if courses else []) + ([courses[0]] if c == COURSES - 1 else []):
                for j in joints:
                    for pj in prev["joints"]:
                        d = abs(j - pj); d = min(d, 32 - d)
                        if d < 2 and j != 0: ok = False   # no joints closer than 0.25 m across a course line (shader shifts courses anyway)
            if ok: break
        if not ok:      # never leave a course incomplete (1 Oct: an unfilled corner became a black mirror flag)
            seq = fallback; joints = sorted(int(np.sum(seq[:i])) % 32 for i in range(len(seq)))
        assert sum(seq) == 32, seq
        courses.append({"seq": seq, "phase": phase, "joints": joints})
    return courses


def main():
    OUT.mkdir(exist_ok=True)
    courses = make_layout()
    slabs = []
    for c, co in enumerate(courses):
        x = co["phase"] * N // 32
        for l in co["seq"]:
            w = l * N // 32
            slabs.append({"course": c, "x0": x, "w": w})
            x += w
    print("slabs", len(slabs))

    # ---- source stone (worn_rock_natural_01 2k = 2 m, ~1 mm/px)
    sd = load(SRC / "worn_rock_natural_01/worn_rock_natural_01_diff_2k.png", "RGB").astype(f32) / 255
    sh = load(SRC / "worn_rock_natural_01/worn_rock_natural_01_disp_2k.png").astype(f32)
    if sh.ndim == 3: sh = sh[..., 0]
    sh = sh / sh.max()
    sdl = srgb_to_lin(sd)
    # remove lichen specks (saturated yellow-green) by replacing them with a local blur
    r_, g_, b_ = sd[..., 0], sd[..., 1], sd[..., 2]
    sat = np.max(sd, -1) - np.min(sd, -1)
    lichen = ((g_ > r_ * 0.98) & (sat > 0.18)) | ((r_ - b_) > 0.42)
    lichen = blur_periodic(lichen.astype(f32), 3) > 0.05
    # inpaint from a far-shifted copy of the same scan (keeps the grain; a blur left flat blobs)
    for shift in [(611, 1033), (1297, 389), (233, 1501)]:
        alt = np.roll(sdl, shift, (0, 1)); alt_l = np.roll(lichen, shift, (0, 1))
        use = lichen & ~alt_l
        sdl = np.where(use[..., None], alt, sdl); lichen = lichen & ~use
    lum = (sdl * np.array([.2126, .7152, .0722], f32)).sum(-1)
    lum_n = lum / lum.mean()
    # high-passed source height (keep 1-40 mm features; flags are dressed, not rock faces)
    sh_hp = sh - blur_periodic(sh, 40)
    sh_hp /= (sh_hp.std() + 1e-6)

    # ---- per-pixel fields
    H = np.zeros((N, N), f32)          # height in mm, flag top ~ 0
    alb = np.zeros((N, N, 3), f32)     # linear albedo
    sid = np.zeros((N, N), f32)        # flag id
    edge = np.full((N, N), 1e9, f32)   # distance to the flag edge in mm (>0 inside)
    rough = np.full((N, N), 0.95, f32)

    yy, xx = np.mgrid[0:CH, 0:N].astype(f32)
    edge_noise = periodic_noise(N, 10, 11, octaves=3) * 1.6 + periodic_noise(N, 2.5, 12, octaves=2) * 0.5   # mm-ish wobble
    chip_noise = periodic_noise(N, 18, 13, octaves=3)

    # Ward sandstone palette (sRGB targets for flag means) - matched to VH_Sandstone/Ashlar and the old paving
    palette = np.array([[190, 166, 132], [182, 160, 130], [198, 176, 144], [178, 163, 140], [194, 166, 128],
                        [166, 146, 120], [206, 188, 158], [187, 170, 145], [158, 140, 116]], f32) / 255
    pal_w = np.array([5, 4, 3, 3, 2, 2, 2, 2, 1], float); pal_w /= pal_w.sum()

    meta = []
    for i, s in enumerate(slabs):
        c = s["course"]; y0 = c * CH; w = s["w"]
        # local coords inside the flag (wraps in x)
        lx = (xx - s["x0"]) % N            # 0..N
        inside_x = lx < w
        # distance to flag border in mm (rectangle), before joints
        dx = np.minimum(lx, w - 1 - lx) * MM
        dy = np.minimum(yy, CH - 1 - yy) * MM
        d = np.where(inside_x, np.minimum(dx, dy), -1e9).astype(f32)
        cols = np.nonzero(inside_x[0])[0]
        sub = (slice(y0, y0 + CH), cols)
        # joint half width for this flag (joints 8-15 mm total; each side owns half)
        half = rng.uniform(4.0, 7.5)
        dd = d[:, cols] - half + edge_noise[sub] * (1.0 + 0.6 * rng.random())
        # chips: bites into the arris where chip noise is high, more at corners
        corner = np.minimum(dx[:, cols], 9999) + np.minimum(dy[:, cols], 9999)
        chip_amt = rng.uniform(0.0, 1.0) ** 2
        bite = np.clip((chip_noise[sub] - 0.9 + 0.6 * chip_amt) * 22, 0, 18) * np.exp(-np.maximum(dd, 0) / 9)
        bite += np.clip(30 - corner / 4, 0, 30) * 0.35 * (rng.random() < 0.55) * np.clip(chip_noise[sub] + 0.4, 0, 1)
        dd = dd - bite
        edge[sub] = dd
        # stone surface crop (random offset/flip), graded per flag
        ox, oy = int(rng.integers(0, 2048)), int(rng.integers(0, 2048))
        ix = (np.arange(len(cols)) + ox) % 2048; iy = (np.arange(CH) + oy) % 2048
        if rng.random() < 0.5: ix = ix[::-1]
        if rng.random() < 0.5: iy = iy[::-1]
        crop_l = lum_n[np.ix_(iy, ix)]
        crop_c = sdl[np.ix_(iy, ix)] / np.maximum(lum[np.ix_(iy, ix)][..., None], 1e-4)   # chroma
        crop_h = sh_hp[np.ix_(iy, ix)]
        target = palette[rng.choice(len(palette), p=pal_w)] * rng.uniform(0.95, 1.05)
        tl = srgb_to_lin(np.clip(target, 0, 1))
        contrast = rng.uniform(0.75, 1.05)
        L = 1 + (crop_l - 1) * contrast
        chroma_mix = rng.uniform(0.06, 0.16)          # keep a little of the scan's mineral colour
        tint_l = tl / max((tl * np.array([.2126, .7152, .0722], f32)).sum(), 1e-4)
        chroma = tint_l * (1 - chroma_mix) + crop_c * chroma_mix
        lumt = (tl * np.array([.2126, .7152, .0722], f32)).sum()
        col = lumt * L[..., None] * chroma
        # broad within-flag cloudiness and a few stains
        col *= rng.uniform(0.97, 1.03)
        alb[sub] = col
        # laying tilt (mm across the flag) + slight dish + dressed surface relief
        ax, ay = rng.normal(0, 2.2), rng.normal(0, 2.2)
        u = (np.arange(len(cols)) / max(len(cols) - 1, 1) - .5)[None, :]
        v = (np.arange(CH) / (CH - 1) - .5)[:, None]
        Hs = ax * u * (w * MM / 1000) * 2 + ay * v * 1.0 - rng.uniform(0, 0.8) * (u * u + v * v)
        Hs = Hs + crop_h * rng.uniform(0.3, 0.5)
        H[sub] = Hs
        rough[sub] = rng.uniform(0.72, 0.84)
        sid[sub] = (rng.integers(2, 30) + 0.5) / 32     # quantised flag id: shader floor(id*32) survives BC7 + filtering
        meta.append({"course": c, "x0_m": s["x0"] * 4 / N, "len_m": w * 4 / N})
    del xx, yy
    # grade all flags together to the Ward paving mean (keeps per-flag relative variation)
    target_mean = srgb_to_lin(np.array([188, 164, 131], f32) / 255)
    cur = alb.reshape(-1, 3).astype(np.float64).mean(0).astype(f32)
    alb *= (target_mean / np.maximum(cur, 1e-4))[None, None, :]
    # broad cloudiness inside the flags (~20 cm), so no flag is a flat fill
    alb *= (1 + 0.08 * periodic_noise(N, 200, 14, octaves=2))[..., None]
    # weathering: dark grime blotches and pale sand-scoured patches (5-40 cm), sparse
    grime = np.clip((periodic_noise(N, 70, 15, octaves=4) - 0.75) * 1.2, 0, 0.3)
    scour = np.clip((periodic_noise(N, 110, 16, octaves=3) - 0.9) * 1.0, 0, 0.18)
    alb *= (1 - grime)[..., None] * np.array([1.0, 0.99, 0.97], f32)
    alb = alb * (1 - scour[..., None]) + scour[..., None] * srgb_to_lin(np.array([214, 196, 166], f32) / 255)

    # ---- arris rounding / joint recess / sand fill
    e = edge
    r_arris = 7.0
    t = np.clip(e / r_arris, 0, 1)
    drop = (1 - np.sqrt(np.clip(1 - (1 - t) ** 2, 0, 1))) * r_arris * 0.8          # quarter-round arris
    flag = e > 0
    sand_noise = periodic_noise(N, 3, 21, octaves=3)
    sand_level = -5.5 + 1.4 * periodic_noise(N, 60, 22, octaves=2) + 0.5 * sand_noise   # mm below the arris
    Hf = np.where(flag, H - drop, np.maximum(sand_level, H - 9.0 + 0 * e))
    # sand spilled a little onto the arris
    del drop

    # sand colour from the masonry kit's sand (dense_sand, Ward-graded)
    sand = load(HERE.parents[1] / "unity/AthenHill/Assets/AthenHill/Art/VanguardHall/Textures/VH_Sand_BaseMap.jpg", "RGB").astype(f32) / 255
    sand = srgb_to_lin(sand)
    sand = np.tile(sand, (2, 2, 1))[:N, :N] * 0.86          # 2k = 2 m -> tile twice over 4 m, slightly darker in joints
    jf = np.clip(-e / 2.0, 0, 1)                               # joint fill weight (soft over 2 mm)
    near = np.clip(1 - np.maximum(e, 0) / 22.0, 0, 1) ** 2      # sand dust on the first ~2 cm of each flag
    dust_break = np.clip(0.5 + 0.9 * periodic_noise(N, 25, 23, octaves=3), 0, 1)
    spill = near * dust_break * 0.45
    albedo = alb * (1 - jf[..., None]) + sand * jf[..., None]
    albedo = albedo * (1 - spill[..., None]) + sand * 1.05 * spill[..., None]
    # grime packed in the worn arris (dark) except fresh chips (pale)
    arris_band = np.clip(1 - np.abs(e - 3.0) / 6.0, 0, 1) * flag
    albedo *= (1 - 0.18 * arris_band * np.clip(0.6 + periodic_noise(N, 6, 24, octaves=2), 0, 1))[..., None]

    # rare cracks across some flags: thin dark lines from a periodic ridge noise
    rn = periodic_noise(N, 90, 31, octaves=4)
    crack_line = np.clip(1 - np.abs(rn) / 0.025, 0, 1)
    crack_gate = (periodic_noise(N, 300, 32, octaves=1) > 0.9) & flag
    crack = crack_line * crack_gate
    albedo *= (1 - 0.45 * crack)[..., None]
    Hf -= crack * 1.2
    # stains (water/oil) on a few flags
    st = np.clip((periodic_noise(N, 120, 41, octaves=3) - 1.3) * 1.5, 0, 0.35) * flag
    albedo *= 1 - st[..., None] * np.array([0.42, 0.44, 0.46], f32)

    # ---- cavity AO from height
    hb = blur_periodic(Hf, 6)
    cav = np.clip(1 - np.clip(hb - Hf, 0, 6) / 7.0, 0.35, 1)
    hb2 = blur_periodic(Hf, 24)
    cav *= np.clip(1 - np.clip(hb2 - Hf, 0, 8) / 16.0, 0.5, 1)
    albedo *= (0.55 + 0.45 * cav)[..., None]

    # ---- normal from height (OpenGL, +Y = up the texture)
    gx = (np.roll(Hf, -1, 1) - np.roll(Hf, 1, 1)) / (2 * MM)
    gy = (np.roll(Hf, -1, 0) - np.roll(Hf, 1, 0)) / (2 * MM)     # d/d(row) - rows go down = -v
    nx, ny, nz = -gx, gy, np.ones_like(gx)
    inv = 1 / np.sqrt(nx * nx + ny * ny + nz * nz)
    nrm = np.stack([nx * inv, ny * inv, nz * inv], -1) * 0.5 + 0.5
    del gx, gy, nx, ny, nz, inv

    # ---- smoothness: flags dressed and foot-worn, sand very rough, cracks/chips rough
    smooth = np.where(flag, 1 - rough, 0.04) * (1 - 0.6 * crack) * (1 - 0.5 * spill)
    hn = np.clip((Hf + 6) / 6, 0, 1)                          # 0 sand/joint .. 1 flag top
    ids = np.where(flag, sid, 0)

    # ---- final grade: the flags' mean colour lands on the Ward paving target (joints follow the same gains)
    gain = srgb_to_lin(np.array([186, 165, 136], f32) / 255) / np.maximum(albedo[flag].astype(np.float64).mean(0), 1e-4).astype(f32)
    print("final gains", gain)
    albedo *= gain[None, None, :]
    # ---- write (4k sources, 2k shipping)
    base = lin_to_srgb(np.clip(albedo, 0, 1))
    stats = {"albedo_srgb_mean_flags": (base[flag].astype(np.float64).mean(0) * 255).round(1).tolist(), "albedo_srgb_mean_joints": (base[~flag].astype(np.float64).mean(0) * 255).round(1).tolist(), "joint_fraction": float((~flag).mean())}
    print(stats)
    for size, tag in [(4096, "4k"), (2048, "2k")]:
        save_rgb(base, OUT / f"PV_Flags_BaseMap_{tag}.png", size)
        save_rgb(nrm, OUT / f"PV_Flags_Normal_{tag}.png", size)
        # resize each channel on its own: an RGBA resize premultiplies by A (smoothness) and wrecks R/G/B
        chans = []
        for ch in (ids, cav, hn, smooth):
            c8 = Image.fromarray((np.clip(ch, 0, 1) * 255 + .5).astype(np.uint8))
            if size != N: c8 = c8.resize((size, size), Image.NEAREST if ch is ids else Image.LANCZOS)
            chans.append(c8)
        Image.merge("RGBA", chans).save(OUT / f"PV_Flags_Mask_{tag}.png")
    # ---- close-range grain detail normal: 1 m tile, high-passed scan height
    g = sh[:1024, :1024].copy()
    # make tileable: blend with a half-shifted copy across the borders
    sh2 = np.roll(np.roll(sh, 512, 0), 512, 1)[:1024, :1024]
    wv = np.minimum(np.arange(1024), 1023 - np.arange(1024)).astype(f32)
    wmask = np.clip(np.minimum(wv[:, None], wv[None, :]) / 160.0, 0, 1)
    g = g * wmask + sh2 * (1 - wmask)
    g = g - blur_periodic(g, 30)
    g = g / (g.std() + 1e-6) * 0.35                                  # mm of relief
    gx = (np.roll(g, -1, 1) - np.roll(g, 1, 1)) / 2; gy = (np.roll(g, -1, 0) - np.roll(g, 1, 0)) / 2
    inv = 1 / np.sqrt(gx * gx + gy * gy + 1)
    gn = np.stack([-gx * inv, gy * inv, inv], -1) * 0.5 + 0.5
    save_rgb(gn, OUT / "PV_Grain_Normal_1k.png")
    json.dump({"tile_m": 4, "courses": COURSES, "course_m": 0.5, "layout": courses, "flags": meta, "stats": stats},
              open(OUT / "layout.json", "w"), indent=1)
    print("done", OUT)


if __name__ == "__main__":
    main()
