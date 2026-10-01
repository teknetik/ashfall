#!/usr/bin/env python3
"""Ward shade sails: procedural canvas maps (1 October 2026).

For every sail in Models/sails.json (author_sails.py: the planar UV layout of the form-found canvas, outline, corners,
height samples) this paints one unique 2048 px base map (RGB colour, alpha = worn-through holes for the alpha-clipped
shadow and surface) and one 1024 px tangent-space normal map, plus a shared 512 px canvas-weave detail pair:

* cloths (panels) 1.37 m wide sewn with flat-felled seams (two stitch rows, a raised double layer), each cloth a
  slightly different dye lot; sun fading by panel and over the high side; broad grime;
* a rolled hem band with its stitch line; layered corner reinforcement patches with stitch outlines and a webbing strap
  out to the corner ring; rust weeping from the corner plates along the fall line;
* dust and water-stain streaks that follow the sail's own slope (from the solved surface) down to its low corners,
  tide marks near the low corners;
* repair patches in the other dyes (stitched, frayed, overlapped), a laced tear, a few small worn-through holes;
* the Ward quartermaster's stencil number near one corner; soot on the market sail's barrel side.
Dye tints follow the shops' cloth materials (WS_ClothMadder / Indigo / Bone, Art/WardShops), faded by the sun.

Run: $O/heavy.sh uv run --with numpy --with scipy --with pillow python art/shade_sails_20261001/make_textures.py [Site ...]
Out: unity/AthenHill/Assets/AthenHill/Art/ShadeSails/Textures/SS_Sail_<Site>_BaseMap.png, _Normal.png,
     SS_CanvasWeave_Detail.png, SS_CanvasWeave_Normal.png; previews in review/tex-<Site>.jpg
"""
import json, math, random, sys, zlib
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
from scipy.interpolate import griddata

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MODELS = ROOT / "unity/AthenHill/Assets/AthenHill/Art/ShadeSails/Models"
TEX = ROOT / "unity/AthenHill/Assets/AthenHill/Art/ShadeSails/Textures"
TEX.mkdir(parents=True, exist_ok=True)
FONT = ROOT / "art/west_gate_20260926/fonts/allertastencil__AllertaStencil-Regular.ttf"
N = 2048          # base map
NN = 1024         # normal map


def srgb_to_lin(c):
    c = np.asarray(c, float) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


# faded field dyes (sRGB): the shop cloth tints, sun-bleached
DYES = {
    "madder": (140, 50, 36), "madder_fresh": (128, 40, 28), "indigo": (60, 72, 104), "indigo_fresh": (40, 50, 88),
    "natural": (198, 182, 150), "bone": (186, 172, 142), "ochre": (176, 128, 62), "khaki": (150, 140, 108),
}
SCHEME = {
    "Courtyard": dict(base="madder", panels=None, patches=["natural", "ochre", "natural", "madder_fresh", "bone"], stencil="WQ 07", stencil_corner=3),
    "Market": dict(base="indigo", panels=None, patches=["madder", "natural", "bone", "indigo_fresh"], stencil="M-3", stencil_corner=1, soot=True),
    "Apron": dict(base="natural", panels={2: "madder", 5: "khaki"}, patches=["madder", "bone", "ochre", "natural"], stencil="GATE 2", stencil_corner=0),
    "Lattice": dict(base="natural", panels="alternate_indigo", patches=["indigo", "natural", "ochre"], stencil="LJ 11", stencil_corner=2),
}


def rng(*k):
    return random.Random(zlib.crc32(repr(k).encode()))


def fbm(shape, scale_px, octaves, seed):
    """Smooth value noise in [-1, 1] (sum of blurred white noise octaves)."""
    r = np.random.default_rng(seed)
    out = np.zeros(shape, np.float32)
    amp, tot = 1.0, 0.0
    s = scale_px
    for _ in range(octaves):
        small = (max(2, int(shape[0] / s)), max(2, int(shape[1] / s)))
        n = r.standard_normal(small).astype(np.float32)
        up = np.array(Image.fromarray(n).resize((shape[1], shape[0]), Image.BICUBIC))
        out += amp * up
        tot += amp
        amp *= 0.5
        s /= 2
    out /= tot
    return np.clip(out / (out.std() * 2.5 + 1e-6), -1, 1)


def poly_mask(points_px, n, ss=2):
    img = Image.new("L", (n * ss, n * ss), 0)
    ImageDraw.Draw(img).polygon([(x * ss, y * ss) for x, y in points_px], fill=255)
    return np.array(img.resize((n, n), Image.LANCZOS), np.float32) / 255.0


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def build(sid, rec, out_preview=True):
    sch = SCHEME[sid]
    R = rng("tex", sid)
    S = rec["uv"]["size"]                      # metres per UV unit
    mpp = S / N                                # metres per pixel (base map)
    # pixel grid in metres (u to the right, v up; row 0 = v 0, flipped on save)
    u = (np.arange(N) + 0.5) / N
    U_, V_ = np.meshgrid(u, u)
    X, Y = U_ * S, V_ * S
    outline = np.array(rec["outline_uv"])
    corners = np.array(rec["corners_uv"])
    ch = np.array(rec["corner_heights"])
    inside = poly_mask([(p[0] * N, p[1] * N) for p in outline], N)
    dist_in = ndimage.distance_transform_edt(inside > 0.5) * mpp          # metres to the hem inside
    dist_out = ndimage.distance_transform_edt(inside <= 0.5) * mpp        # metres outside
    # heights of the solved surface over the texture (for the fall line)
    gu = np.array(rec["grid_uv"]); gy = np.array(rec["grid_y"])
    M = 256
    gx = (np.arange(M) + 0.5) / M
    GU, GV = np.meshgrid(gx, gx)
    H = griddata(gu, gy, (GU, GV), method="linear")
    Hn = griddata(gu, gy, (GU, GV), method="nearest")
    H = np.where(np.isnan(H), Hn, H)
    H = ndimage.gaussian_filter(H, 2)
    dHv, dHu = np.gradient(H, S / M)
    flow = np.stack([-dHu, -dHv], -1)                      # downhill, metres per metre
    fl = np.linalg.norm(flow, axis=-1, keepdims=True) + 1e-6
    flow_n = flow / fl
    big = lambda a: np.array(Image.fromarray(a.astype(np.float32)).resize((N, N), Image.BILINEAR))
    flow_u, flow_v = big(flow_n[..., 0]), big(flow_n[..., 1])
    Hbig = big(H)

    # ---------------------------------------------------------------- base colour (linear)
    base = srgb_to_lin(DYES[sch["base"]])
    col = np.ones((N, N, 3), np.float32) * base
    # cloths: run along the sail's longest corner-to-corner line; seams across the width every 1.37 m
    pairs = [(i, j) for i in range(len(corners)) for j in range(i + 1, len(corners))]
    i, j = max(pairs, key=lambda p: np.linalg.norm(corners[p[0]] - corners[p[1]]))
    d = corners[j] - corners[i]; d /= np.linalg.norm(d)
    perp = np.array([-d[1], d[0]])
    s_coord = (X * perp[0] + Y * perp[1])
    W = 1.37
    panel = np.floor(s_coord / W).astype(int)
    seam_d = np.abs(((s_coord + W / 2) % W) - W / 2)                 # metres to the nearest seam
    pmin, pmax = panel.min(), panel.max()
    for k in range(pmin, pmax + 1):
        m = panel == k
        pr = rng("panel", sid, k)
        f = 1 + pr.uniform(-0.06, 0.06)
        tint = np.array([1 + pr.uniform(-0.03, 0.03), 1 + pr.uniform(-0.03, 0.03), 1 + pr.uniform(-0.03, 0.03)])
        dyename = None
        if isinstance(sch["panels"], dict):
            dyename = sch["panels"].get(k - pmin)
        elif sch["panels"] == "alternate_indigo" and (k - pmin) % 2 == 1:
            dyename = "indigo"
        c = srgb_to_lin(DYES[dyename]) if dyename else base
        col[m] = c * f * tint
    # ---------------------------------------------------------------- seams
    thread = srgb_to_lin((214, 204, 182)) * 0.5 + base * 0.5        # bleached thread, part dyed by the canvas
    bleach = srgb_to_lin((205, 192, 168))
    heightmap = np.zeros((N, N), np.float32)        # metres (for the normal map, downsampled later)
    seam_band = smoothstep(0.018, 0.012, seam_d)          # 3 cm double layer
    col *= (1 - 0.11 * seam_band)[..., None]
    col *= (1 - 0.12 * np.exp(-((seam_d - 0.017) / (1.0 * mpp)) ** 2))[..., None]   # fold edge line
    stitch_rows = np.exp(-((seam_d - 0.0105) / (0.8 * mpp)) ** 2)
    stitch_mod = 0.5 + 0.5 * np.sin((X * d[0] + Y * d[1]) * 2 * math.pi / 0.006)
    st = 0.35 * stitch_rows * stitch_mod
    col = col * (1 - st[..., None]) + thread * st[..., None]

    # ---------------------------------------------------------------- repair patches
    alpha = np.ones((N, N), np.float32)
    placed = []
    tries = 0
    want = 4 + R.randint(0, 2)
    while len(placed) < want and tries < 400:
        tries += 1
        px_ = R.uniform(0.05, 0.95) * S; py_ = R.uniform(0.05, 0.95) * S
        iu, iv = int(px_ / mpp), int(py_ / mpp)
        if iu >= N or iv >= N or dist_in[iv, iu] < 0.35:
            continue
        if any(np.hypot(px_ - q[0], py_ - q[1]) < 1.0 for q in placed):
            continue
        if any(np.hypot(px_ - c[0] * S, py_ - c[1] * S) < 0.8 for c in corners):
            continue
        placed.append((px_, py_))
    for n_, (px_, py_) in enumerate(placed):
        dye = sch["patches"][n_ % len(sch["patches"])]
        w, h = R.uniform(0.22, 0.7), R.uniform(0.18, 0.5)
        ang = math.atan2(d[1], d[0]) + math.radians(R.uniform(-12, 12))
        ca, sa = math.cos(ang), math.sin(ang)
        lx = (X - px_) * ca + (Y - py_) * sa
        ly = -(X - px_) * sa + (Y - py_) * ca
        edge_noise = 0.006 * fbm((N, N), 6, 2, 300 + n_)
        box = np.maximum(np.abs(lx) - w / 2, np.abs(ly) - h / 2) + edge_noise
        m = smoothstep(0.002, -0.002, box) * (inside > 0.5)
        pc = srgb_to_lin(DYES[dye]) * (1 + R.uniform(-0.05, 0.05))
        age = R.uniform(0.0, 0.25)
        pc = pc * (1 - age) + bleach * age
        patch_col = pc * (1 + 0.06 * fbm((N, N), 30, 2, 400 + n_))[..., None]
        col = col * (1 - m[..., None]) + patch_col * m[..., None]
        # overlap shadow line and stitch row 1.2 cm inside the edge
        rim = np.exp(-((box) / (1.2 * mpp)) ** 2)
        col *= (1 - 0.25 * rim)[..., None]
        sl = np.exp(-((box + 0.012) / (0.8 * mpp)) ** 2) * m
        stm = 0.5 + 0.5 * np.sin((lx + ly) * 2 * math.pi / 0.008)
        col = col * (1 - 0.35 * (sl * stm)[..., None]) + thread * 0.35 * (sl * stm)[..., None]
        heightmap += 0.0006 * m
    # sun fading: the high side and broad patches bleach (towards a warm grey), dyes lose saturation
    hi = (Hbig - Hbig.min()) / (Hbig.max() - Hbig.min() + 1e-6)
    fade = 0.10 + 0.22 * hi + 0.10 * fbm((N, N), 300, 3, zlib.crc32(sid.encode()) % 9999)
    grey = col.mean(-1, keepdims=True)
    col = col * (1 - fade[..., None] * 0.42) + (grey * 0.35 + bleach * 0.65) * fade[..., None] * 0.42
    # broad grime and mottling
    grime = fbm((N, N), 160, 5, 11 + len(sid))
    col *= (1 + 0.07 * grime)[..., None]
    fine = fbm((N, N), 12, 3, 23 + len(sid))
    col *= (1 + 0.025 * fine)[..., None]

    # ---------------------------------------------------------------- fall-line streaks (dust and water)
    noise = np.random.default_rng(5 + len(sid)).random((N // 10, N // 10)).astype(np.float32)
    noise = np.array(Image.fromarray(noise).resize((N, N), Image.BILINEAR))
    acc = np.zeros((N, N), np.float32)
    px, py = np.meshgrid(np.arange(N, dtype=np.float32), np.arange(N, dtype=np.float32))
    steps = 30
    for t in range(steps):
        sx = px - flow_u * t * (0.06 / mpp)
        sy = py - flow_v * t * (0.06 / mpp)
        acc += ndimage.map_coordinates(noise, [sy, sx], order=1, mode="reflect")
    acc /= steps
    acc = ndimage.gaussian_filter(acc, 1.5)
    streak = np.clip((acc - acc.mean()) / (acc.std() + 1e-6) - 0.4, 0, 2.0) / 2.0     # sparse, 0..1
    lowness = 1 - hi
    low_ids = np.argsort(ch)[:2]
    near_low = np.zeros((N, N), np.float32)
    for li in low_ids:
        c = corners[li] * S
        r = np.hypot(X - c[0], Y - c[1])
        near_low = np.maximum(near_low, np.exp(-r / 2.2))
    dust = srgb_to_lin((176, 158, 128))
    dust_amt = np.clip(0.07 * lowness + 0.2 * near_low, 0, 0.35) * (0.7 + 0.3 * ndimage.gaussian_filter(streak, 3))
    col = col * (1 - dust_amt[..., None]) + dust * dust_amt[..., None]
    # tide marks near the low corners
    for li in low_ids:
        c = corners[li] * S
        r = np.hypot(X - c[0], Y - c[1])
        for k, rr in enumerate((0.55, 0.9, 1.35)):
            ring = np.exp(-((r - rr - 0.05 * fbm((N, N), 80, 2, 70 + k)) / 0.012) ** 2)
            col *= (1 - 0.10 * ring * (1 - 0.3 * k))[..., None]

    # ---------------------------------------------------------------- hem band (4.5 cm) and outside fill
    hem = smoothstep(0.050, 0.040, dist_in) * (inside > 0.5) + (inside <= 0.5)
    col *= (1 - 0.13 * hem)[..., None]
    hem_stitch = np.exp(-((dist_in - 0.034) / (0.8 * mpp)) ** 2) * (inside > 0.5)
    col = col * (1 - 0.2 * hem_stitch[..., None]) + thread * 0.2 * hem_stitch[..., None]
    edge_grime = np.exp(-dist_in / 0.12) * (inside > 0.5)
    col *= (1 - 0.12 * edge_grime)[..., None]

    # ---------------------------------------------------------------- corner reinforcements, straps, rust
    nc = len(corners)
    cen = corners.mean(0) * S
    for k in range(nc):
        c = corners[k] * S
        a = corners[(k - 1) % nc] * S
        b = corners[(k + 1) % nc] * S
        da = (a - c) / np.linalg.norm(a - c); db = (b - c) / np.linalg.norm(b - c)
        for layer, L in enumerate((0.48, 0.30)):
            tri = [c + da * L, c, c + db * L]
            pts = [((p[0] / S) * N, (p[1] / S) * N) for p in tri]
            m = poly_mask(pts, N) * (inside > 0.5)
            shade = 0.8 - 0.07 * layer
            col *= (1 - (1 - shade) * m)[..., None]
            heightmap += 0.0007 * m
            # stitch outline along the patch's inner edge
            p0, p1 = c + da * (L - 0.025), c + db * (L - 0.025)
            e = p1 - p0; el = np.linalg.norm(e); e /= el
            t = np.clip(((X - p0[0]) * e[0] + (Y - p0[1]) * e[1]) / el, 0, 1)
            dd = np.hypot(X - (p0[0] + e[0] * el * t), Y - (p0[1] + e[1] * el * t))
            sl = np.exp(-(dd / (0.8 * mpp)) ** 2) * m
            col = col * (1 - 0.35 * sl[..., None]) + thread * 0.35 * sl[..., None]
        # webbing strap from the corner along the bisector
        bis = (da + db); bis /= np.linalg.norm(bis)
        t = (X - c[0]) * bis[0] + (Y - c[1]) * bis[1]
        side = np.abs((X - c[0]) * (-bis[1]) + (Y - c[1]) * bis[0])
        strap = smoothstep(0.024, 0.018, side) * smoothstep(0.0, 0.02, t) * smoothstep(0.58, 0.52, t)
        webbing = srgb_to_lin((70, 64, 56))
        col = col * (1 - 0.85 * strap[..., None]) + webbing * 0.85 * strap[..., None]
        heightmap += 0.0012 * strap
        # rust weeping from the corner plate down the fall line
        r = np.hypot(X - c[0], Y - c[1])
        down = (flow_u * (X - c[0]) + flow_v * (Y - c[1])) / (r + 1e-6)
        rust_amt = 0.5 * np.exp(-r / 0.4) * np.clip(down, 0, 1) ** 2 * (0.4 + 0.6 * streak)
        rust = srgb_to_lin((112, 62, 34))
        col = col * (1 - rust_amt[..., None]) + rust * rust_amt[..., None]

    # a laced tear (zigzag repair across a slit)
    if placed or True:
        for tries in range(200):
            tx, ty = R.uniform(0.15, 0.85) * S, R.uniform(0.15, 0.85) * S
            iu, iv = int(tx / mpp), int(ty / mpp)
            if dist_in[iv, iu] > 0.5 and all(np.hypot(tx - q[0], ty - q[1]) > 1.0 for q in placed):
                break
        ang = math.atan2(d[1], d[0]) + math.radians(R.uniform(30, 70))
        ca, sa = math.cos(ang), math.sin(ang)
        lx = (X - tx) * ca + (Y - ty) * sa
        ly = -(X - tx) * sa + (Y - ty) * ca
        L = R.uniform(0.25, 0.4)
        along = smoothstep(L / 2, L / 2 - 0.02, np.abs(lx))
        slit = np.exp(-(ly / (0.9 * mpp)) ** 2) * along
        zig = np.abs(((lx / 0.018) % 2) - 1) * 0.02 - 0.01
        lace = np.exp(-((ly - zig) / (1.2 * mpp)) ** 2) * along * smoothstep(0.016, 0.01, np.abs(ly))
        col *= (1 - 0.55 * slit)[..., None]
        col = col * (1 - 0.5 * lace[..., None]) + srgb_to_lin((60, 52, 44)) * 0.5 * lace[..., None]
        heightmap -= 0.0008 * slit
        heightmap += 0.0006 * lace
    # worn-through holes (alpha) with a darkened frayed ring
    for n_ in range(R.randint(2, 4)):
        for tries in range(200):
            hx, hy = R.uniform(0.05, 0.95) * S, R.uniform(0.05, 0.95) * S
            iu, iv = int(hx / mpp), int(hy / mpp)
            if 0.12 < dist_in[iv, iu] < 1.2:
                break
        r0 = R.uniform(0.012, 0.035)
        rr = np.hypot(X - hx, Y - hy) + 0.006 * fbm((N, N), 4, 2, 500 + n_)
        hole = rr < r0
        alpha[hole] = 0.0
        ring = np.exp(-((rr - r0) / 0.01) ** 2) * (~hole)
        col *= (1 - 0.35 * ring)[..., None]

    # ---------------------------------------------------------------- stencil and soot
    if sch.get("stencil") and FONT.exists():
        k = sch["stencil_corner"]
        c = corners[k] * S
        bis = (cen - c); bis /= np.linalg.norm(bis)
        pos = c + bis * 0.95
        img = Image.new("L", (N, N), 0)
        dr = ImageDraw.Draw(img)
        size_px = int(0.11 / mpp)
        font = ImageFont.truetype(str(FONT), size_px)
        tw = dr.textlength(sch["stencil"], font=font)
        tmp = Image.new("L", (int(tw) + 20, size_px + 20), 0)
        ImageDraw.Draw(tmp).text((10, 5), sch["stencil"], font=font, fill=255)
        ang = math.degrees(math.atan2(d[1], d[0]))
        tmp = tmp.transpose(Image.FLIP_LEFT_RIGHT)     # painted to read from under the sail (the face people see)
        tmp = tmp.rotate(ang, expand=True, resample=Image.BICUBIC)
        cx, cy = int(pos[0] / mpp), int(pos[1] / mpp)
        img.paste(tmp, (cx - tmp.width // 2, (N - cy) - tmp.height // 2), tmp)
        ink = np.flipud(np.array(img, np.float32) / 255.0)  # image rows (v down) -> array rows (v up)
        wear = np.clip(0.75 + 0.45 * fbm((N, N), 8, 3, 900), 0, 1)
        a_ = 0.55 * ink * wear
        col = col * (1 - a_[..., None]) + srgb_to_lin((34, 30, 28)) * a_[..., None]
    if sch.get("soot"):
        # the barrel fire stands under the south-west corner (sails.py): soot on the west part of the canvas
        c = corners[2] * S
        r = np.hypot(X - c[0], Y - c[1])
        soot = 0.35 * np.exp(-((r - 1.6) / 1.1) ** 2) * np.clip(0.6 + 0.4 * fbm((N, N), 60, 3, 77), 0, 1)
        col *= (1 - soot)[..., None]

    # ---------------------------------------------------------------- normal map (1024 px)
    f = N // NN
    Hm = heightmap.reshape(NN, f, NN, f).mean((1, 3))
    Xn, Yn = X[::f, ::f], Y[::f, ::f]
    sd = seam_d[::f, ::f]
    Hm += 0.0011 * smoothstep(0.019, 0.008, sd)                       # raised flat-felled seam
    di = dist_in[::f, ::f]
    Hm += 0.0025 * smoothstep(0.05, 0.0, di) * (di > 0)              # rolled hem
    # tension wrinkles fanning out of the corners
    for k in range(nc):
        c = corners[k] * S
        a = corners[(k - 1) % nc] * S
        b = corners[(k + 1) % nc] * S
        bis = (a - c) / np.linalg.norm(a - c) + (b - c) / np.linalg.norm(b - c); bis /= np.linalg.norm(bis)
        rx, ry = Xn - c[0], Yn - c[1]
        r = np.hypot(rx, ry) + 1e-6
        phi = np.arctan2(rx * bis[1] - ry * bis[0], rx * bis[0] + ry * bis[1])
        env = np.exp(-r / 0.55) * smoothstep(0.2, 0.45, r) * smoothstep(0.75, 0.2, np.abs(phi))
        Hm += 0.0045 * env * np.sin(phi * 24 + 2 * fbm((NN, NN), 60, 2, 600 + k))
    # slack scallops along the hems
    hem_env = np.exp(-di / 0.3) * (di > 0.05)
    Hm += 0.0012 * hem_env * fbm((NN, NN), 40, 2, 700)
    Hm += 0.00012 * fbm((NN, NN), 3, 2, 800)                          # canvas grain
    mppn = S / NN
    gy_, gx_ = np.gradient(Hm, mppn)
    nrm = np.stack([-gx_, -gy_, np.ones_like(Hm)], -1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    nimg = ((nrm * 0.5 + 0.5) * 255).round().astype(np.uint8)
    nimg = np.flipud(nimg)                                          # row 0 = v 1 in the image

    rgb = (lin_to_srgb(col) * 255).round().astype(np.uint8)
    a8 = (alpha * 255).astype(np.uint8)
    rgba = np.dstack([rgb, a8])
    rgba = np.flipud(rgba)
    Image.fromarray(rgba, "RGBA").save(TEX / f"SS_Sail_{sid}_BaseMap.png", optimize=True)
    Image.fromarray(nimg, "RGB").save(TEX / f"SS_Sail_{sid}_Normal.png", optimize=True)
    if out_preview:
        pv = Image.fromarray(rgba[..., :3]).resize((768, 768), Image.LANCZOS)
        nv = Image.fromarray(nimg).resize((768, 768), Image.LANCZOS)
        sheet = Image.new("RGB", (1536, 768)); sheet.paste(pv, (0, 0)); sheet.paste(nv, (768, 0))
        (HERE / "review").mkdir(exist_ok=True)
        sheet.save(HERE / f"review/tex-{sid}.jpg", quality=88)
    return dict(size_m=S, mpp_base=mpp, patches=len(placed))


def weave():
    """Shared plain-weave canvas detail pair: 512 px = 0.2 m (threads ~1.1 mm)."""
    n = 512
    tile = 0.2
    x = (np.arange(n) + 0.5) / n * tile
    X, Y = np.meshgrid(x, x)
    pitch = 0.2 / 180                                  # 180 threads per tile (seamless)
    wu = np.sin(X / pitch * math.pi)
    wv = np.sin(Y / pitch * math.pi)
    rng_ = np.random.default_rng(3)
    jit = ndimage.gaussian_filter(rng_.standard_normal((n, n)), (0.5, 6), mode="wrap") * 0.6
    warp = np.abs(np.sin(X / pitch * math.pi + jit)) * (0.5 + 0.5 * np.sign(wv))
    weft = np.abs(np.sin(Y / pitch * math.pi + jit.T)) * (0.5 - 0.5 * np.sign(wv))
    h = (warp + weft) * 0.00012 + ndimage.gaussian_filter(rng_.standard_normal((n, n)), 1.5, mode="wrap") * 0.00002
    gy_, gx_ = np.gradient(h, tile / n)
    nrm = np.stack([-gx_, -gy_, np.ones_like(h)], -1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    Image.fromarray(np.flipud(((nrm * 0.5 + 0.5) * 255).round().astype(np.uint8)), "RGB").save(TEX / "SS_CanvasWeave_Normal.png")
    a = 128 + 10 * (warp + weft - 1) + 4 * ndimage.gaussian_filter(rng_.standard_normal((n, n)), 1.0, mode="wrap")
    a = np.clip(a, 0, 255).astype(np.uint8)
    Image.fromarray(np.dstack([a, a, a]), "RGB").save(TEX / "SS_CanvasWeave_Detail.png")


def main():
    rec = json.loads((MODELS / "sails.json").read_text())
    only = set(sys.argv[1:])
    weave()
    stats = {}
    for sid, r in rec.items():
        if only and sid not in only:
            continue
        stats[sid] = build(sid, r)
        print(sid, stats[sid], flush=True)
    (HERE / "textures.json").write_text(json.dumps(stats, indent=1))


if __name__ == "__main__":
    main()
