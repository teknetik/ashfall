"""Original deterministic PBR maps for the Basic General counter/stock dressing (29 Sep 2026).

Run with the clean-environment system Python (numpy only, no PIL):
    env -i HOME=$HOME PATH=/usr/bin:/bin /usr/bin/python3 make_textures.py

Conventions (match the project's existing Ward maps, e.g. art/quality_20260908/lamps):
  *_BaseColor.png   sRGB albedo (RGB, or RGBA where noted)
  *_Normal.png      tangent-space, OpenGL (+Y up), linear
  *_MetalSmooth.png R metallic, A smoothness (1-roughness), G/B zero  (URP Lit metallic-gloss map)
All maps are 2048x2048 tiles, except the two unique counter maps (4096x512, 4096x1024) at a constant
966 px/m so the wear is painted in true physical position. Nothing is downsampled from a larger source.
"""
import hashlib, json, struct, zlib
from pathlib import Path
import numpy as np

OUT = Path('/home/teknetik/code/ao2/art/quality_20260929/basic-general-counter/textures')
OUT.mkdir(parents=True, exist_ok=True)
N = 2048


# ---------------------------------------------------------------- io
def write_png(path, arr):
    arr = np.ascontiguousarray(arr.astype(np.uint8))
    h, w = arr.shape[:2]
    ct = {3: 2, 4: 6}[arr.shape[2]]
    raw = b''.join(b'\x00' + arr[r].tobytes() for r in range(h))

    def chunk(tag, data):
        c = struct.pack('>I', len(data)) + tag + data
        return c + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, ct, 0, 0, 0)) \
        + chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b'')
    Path(path).write_bytes(png)


# ---------------------------------------------------------------- fields
def smooth(t):
    return t * t * (3 - 2 * t)


def vnoise(rng, H, W, cy, cx):
    """Tileable value noise with cy x cx lattice cells (cells may exceed H, W/2 only mildly)."""
    g = rng.random((cy, cx)).astype(np.float32)
    y = np.arange(H, dtype=np.float32) * cy / H
    x = np.arange(W, dtype=np.float32) * cx / W
    y0 = np.floor(y).astype(int); x0 = np.floor(x).astype(int)
    ty = smooth(y - y0)[:, None]; tx = smooth(x - x0)[None, :]
    y0 %= cy; x0 %= cx; y1 = (y0 + 1) % cy; x1 = (x0 + 1) % cx
    a = g[y0][:, x0]; b = g[y0][:, x1]; c = g[y1][:, x0]; d = g[y1][:, x1]
    return (a * (1 - tx) + b * tx) * (1 - ty) + (c * (1 - tx) + d * tx) * ty


def fbm(rng, H, W, cells, weights=None, aniso=1.0):
    weights = weights or [1.0 / (i + 1) for i in range(len(cells))]
    t = np.zeros((H, W), np.float32)
    for c, w in zip(cells, weights):
        t += w * vnoise(rng, H, W, max(2, int(c)), max(2, int(c * aniso)))
    t /= sum(weights)
    return t


def blur(a, sigma):
    if sigma <= 0:
        return a
    fy = np.fft.fftfreq(a.shape[0])[:, None]; fx = np.fft.rfftfreq(a.shape[1])[None, :]
    k = np.exp(-2 * (np.pi * sigma) ** 2 * (fx ** 2 + fy ** 2))
    return np.fft.irfft2(np.fft.rfft2(a) * k, s=a.shape).astype(np.float32)


def stretch(v, lo, hi):
    return np.clip((v - lo) / (hi - lo), 0, 1)


def normal_from_height(h, strength):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5   # rows run downward
    n = np.stack((-dx * strength, dy * strength, np.ones_like(h)), -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return ((n * 0.5 + 0.5) * 255).astype(np.uint8)


def scratches(rng, H, W, count, length, angle, spread=0.25, width=1):
    """Thin directional scratches (hand tools, cargo), returned as 0..1 mask, tile-wrapped."""
    m = np.zeros((H, W), np.float32)
    for _ in range(count):
        cx = rng.random() * W; cy = rng.random() * H
        a = angle + (rng.random() - .5) * spread * 2
        L = length * (0.3 + rng.random())
        n = int(L)
        t = np.arange(n) - n / 2
        xs = ((cx + t * np.cos(a)) % W).astype(int); ys = ((cy + t * np.sin(a)) % H).astype(int)
        m[ys, xs] = np.maximum(m[ys, xs], 0.4 + 0.6 * rng.random())
    return blur(m, width) * 2.2


def pack_metal_smooth(metal, smoothness):
    o = np.zeros(metal.shape + (4,), np.uint8)
    o[..., 0] = (np.clip(metal, 0, 1) * 255).astype(np.uint8)
    o[..., 3] = (np.clip(smoothness, 0, 1) * 255).astype(np.uint8)
    return o


def srgb8(c):
    return (np.clip(c, 0, 1) * 255 + .5).astype(np.uint8)


MANIFEST = []


VARIANTS = {   # sRGB-space multipliers baked into extra BaseColor maps (Normal + MetalSmooth are shared with the parent)
    'BGC_Enamel': {'Sand': (.78, .65, .45), 'Olive': (.41, .48, .30), 'Blue': (.28, .45, .62), 'Red': (.69, .14, .10),
                   'Bone': (.92, .87, .72), 'Wax': (.35, .075, .05), 'Teal': (.28, .48, .45)},
    'BGC_ShelfPaint': {'Bone': (1.22, 1.08, 1.0), 'Olive': (.62, .70, .50)},
    'BGC_Webbing': {'Olive': (.48, .57, .42), 'Sand': (.90, .80, .65)},
    'BGC_CableSheath': {'Slate': (.45, .50, .60), 'Ochre': (.90, .68, .33)},
    'BGC_BareSteel': {'Brass': (1.12, .86, .40)},
}


def emit(name, base, normal, metalsmooth, tile_m, note, px_per_m=None, mask=None):
    files = {}
    for suffix, arr in (('BaseColor', base), ('Normal', normal), ('MetalSmooth', metalsmooth)):
        p = OUT / f'{name}_{suffix}.png'
        write_png(p, arr)
        files[suffix] = {'file': p.name, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                         'width': int(arr.shape[1]), 'height': int(arr.shape[0]), 'bytes': p.stat().st_size}
    variants = {}
    for vname, tint in VARIANTS.get(name, {}).items():
        t = np.array(tint, np.float32)[None, None, :]
        if mask is not None:
            t = 1.0 + (t - 1.0) * mask[..., None]       # tint the paint only, not exposed steel/rust
        arr = np.clip(base.astype(np.float32) / 255.0 * t, 0, 1)
        arr = (arr * 255 + .5).astype(np.uint8)
        p = OUT / f'{name}_{vname}_BaseColor.png'
        write_png(p, arr)
        variants[vname] = {'file': p.name, 'tintSRGB': list(tint), 'paintMasked': mask is not None,
                           'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes': p.stat().st_size}
    MANIFEST.append({'material': name, 'tileMetres': tile_m, 'note': note, 'pxPerMetre': px_per_m, 'maps': files, 'variants': variants})
    print('wrote', name, {k: v['bytes'] // 1024 for k, v in files.items()}, 'variants', list(variants), 'KiB')


# ---------------------------------------------------------------- tiling materials
def painted(name, seed, base, rough, chip_amount, rust_amount, scratch_count, tile_m, note, orange_peel=0.5):
    """Neutral-ish enamel/paint over steel. `base` is the albedo of the paint; chips reveal steel + rust rim."""
    rng = np.random.default_rng(seed)
    mott = fbm(rng, N, N, [6, 20, 70, 260], [1, .7, .5, .3])
    grain = fbm(rng, N, N, [700, 1400], [1, 1])
    chip_field = 0.55 * fbm(rng, N, N, [30, 90, 300], [1, .8, .6]) + 0.45 * fbm(rng, N, N, [500, 900], [1, 1])
    thr = 1.0 - chip_amount
    chips = stretch(chip_field, thr, thr + 0.02)
    rim = np.clip(blur(chips, 3.5) * 3.0 - chips * 1.0, 0, 1)             # rust halo round each chip
    rust_patch = stretch(fbm(rng, N, N, [9, 33], [1, .7]), 0.62, 0.78) * rust_amount
    sc = np.clip(scratches(rng, N, N, scratch_count, 380, 0.12, 0.5, 1.1), 0, 1)
    paint = np.array(base, np.float32)[None, None, :] * (0.9 + 0.2 * mott[..., None]) * (0.985 + 0.03 * grain[..., None])
    steel = np.array((.36, .36, .37), np.float32)[None, None, :] * (0.8 + 0.4 * grain[..., None])
    rust = np.array((.31, .165, .085), np.float32)[None, None, :] * (0.75 + 0.5 * mott[..., None])
    c = paint
    c = c * (1 - rust_patch[..., None] * .65) + rust * rust_patch[..., None] * .65
    c = c * (1 - rim[..., None] * .8) + rust * rim[..., None] * .8
    c = c * (1 - chips[..., None]) + steel * chips[..., None]
    c = c * (1 - sc[..., None] * .55) + steel * 1.25 * sc[..., None] * .55
    peel = fbm(rng, N, N, [300, 600], [1, 1])
    h = 0.45 * orange_peel * (peel - .5) * .02 - chips * 0.010 - sc * 0.003 + rim * 0.0015 + rust_patch * .002
    metal = np.clip(chips * .9 + sc * .35, 0, 1) * (1 - rim)
    smooth_v = 0.62 - rough * 0.45 + (mott - .5) * .12
    smooth_v = smooth_v * (1 - chips) + .42 * chips
    smooth_v = smooth_v * (1 - rim) + .12 * rim
    smooth_v = smooth_v * (1 - rust_patch * .8) + .10 * rust_patch * .8
    emit(name, np.dstack((srgb8(c),)).reshape(N, N, 3), normal_from_height(h, 110), pack_metal_smooth(metal, smooth_v), tile_m, note, mask=(1 - chips) * (1 - rim * .6))


def bare_steel(name, seed, tile_m, note):
    rng = np.random.default_rng(seed)
    streak = fbm(rng, N, N, [3, 12, 40], [1, .9, .7], aniso=1.0)
    brushed = vnoise(rng, N, N, 1200, 6) * .6 + vnoise(rng, N, N, 2000, 3) * .4
    lowf = fbm(rng, N, N, [5, 17], [1, .6])
    rustm = stretch(fbm(rng, N, N, [11, 40, 160], [1, .8, .6]), .66, .80)
    dark = stretch(fbm(rng, N, N, [7, 24], [1, .6]), .6, .8)
    sc = np.clip(scratches(rng, N, N, 220, 420, 0.0, 0.08, 0.9), 0, 1)
    steelc = np.array((.55, .56, .57), np.float32)[None, None, :] * (0.86 + 0.28 * brushed[..., None]) * (0.95 + 0.1 * lowf[..., None])
    rust = np.array((.30, .16, .085), np.float32)[None, None, :] * (0.7 + 0.6 * streak[..., None])
    c = steelc * (1 - dark[..., None] * .3)
    c = c * (1 - rustm[..., None] * .8) + rust * rustm[..., None] * .8
    c = c + sc[..., None] * .08
    h = (brushed - .5) * .003 - rustm * 0.002 - sc * 0.002
    metal = (1 - rustm * .95) * .96
    smooth_v = 0.55 + (brushed - .5) * .3 - rustm * .4 + (lowf - .5) * .15 - dark * .1
    emit(name, srgb8(c), normal_from_height(h, 160), pack_metal_smooth(metal, smooth_v), tile_m, note)


def rubber(name, seed, tile_m, note):
    rng = np.random.default_rng(seed)
    g = fbm(rng, N, N, [400, 900, 1600], [1, 1, 1])
    lowf = fbm(rng, N, N, [6, 20], [1, .6])
    crack = stretch(vnoise(rng, N, N, 60, 60), .93, .99)
    dust = stretch(fbm(rng, N, N, [10, 40, 180], [1, .8, .6]), .66, .85)
    c = np.array((.32, .32, .30), np.float32)[None, None, :] * (0.7 + 0.6 * g[..., None]) * (0.9 + .2 * lowf[..., None])
    c = c * (1 - crack[..., None] * .5)
    dustc = np.array((.60, .50, .36), np.float32)[None, None, :]
    c = c * (1 - dust[..., None] * .30) + dustc * dust[..., None] * .30
    h = (g - .5) * .006 - crack * .004
    smooth_v = .28 + (g - .5) * .2 - dust * .12
    emit(name, srgb8(c), normal_from_height(h, 90), pack_metal_smooth(np.zeros((N, N), np.float32), smooth_v), tile_m, note)


def webbing(name, seed, tile_m, note, threads=110):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:N, 0:N].astype(np.float32) / N
    u = x * threads; v = y * threads
    fu = u - np.floor(u); fv = v - np.floor(v)
    over = ((np.floor(u) + np.floor(v)) % 2 == 0)
    warp = np.sin(np.pi * fu) ** .6
    weft = np.sin(np.pi * fv) ** .6
    hgt = np.where(over, .55 + .45 * warp, .55 + .45 * weft)
    fibre = fbm(rng, N, N, [700, 1400], [1, 1])
    mott = fbm(rng, N, N, [8, 40, 200], [1, .7, .5])
    soil = stretch(fbm(rng, N, N, [12, 60], [1, .8]), .55, .8)
    col = np.array((.62, .60, .53), np.float32)[None, None, :] * (0.62 + 0.38 * hgt[..., None]) * (0.85 + .3 * fibre[..., None]) * (0.9 + .2 * mott[..., None])
    col = col * (1 - soil[..., None] * .25) + np.array((.34, .27, .18), np.float32)[None, None, :] * soil[..., None] * .25
    h = hgt * .006 + (fibre - .5) * .0015
    smooth_v = .12 + (fibre - .5) * .08 - soil * .05
    emit(name, srgb8(col), normal_from_height(h, 120), pack_metal_smooth(np.zeros((N, N), np.float32), smooth_v), tile_m, note)


def copper_wire(name, seed, tile_m, note):
    rng = np.random.default_rng(seed)
    # U runs round the bundle, V along it: strands run along V, so brightness varies with U only.
    strands = np.tile(vnoise(rng, 1, N, 1, 120)[0][None, :], (N, 1))
    strands2 = np.tile(vnoise(rng, 1, N, 1, 150)[0][None, :], (N, 1))
    lowf = fbm(rng, N, N, [4, 14, 55], [1, .8, .5])
    patina = stretch(fbm(rng, N, N, [6, 20, 70, 300], [1, .8, .6, .5]), .64, .80)
    tarn = stretch(fbm(rng, N, N, [9, 33], [1, .7]), .45, .8)
    groove = 0.5 + 0.5 * np.sin(np.arange(N, dtype=np.float32)[None, :] / N * np.pi * 2 * 32)
    groove = np.repeat(groove, N, 0)
    cu = np.array((.62, .34, .22), np.float32)[None, None, :]
    dark = np.array((.30, .14, .075), np.float32)[None, None, :]
    verd = np.array((.17, .33, .27), np.float32)[None, None, :]
    c = cu * (0.78 + .3 * strands[..., None]) * (0.92 + .16 * lowf[..., None])
    c = c * (1 - tarn[..., None] * .5) + dark * tarn[..., None] * .5
    c = c * (1 - patina[..., None] * .75) + verd * patina[..., None] * .75
    c = c * (0.82 + .18 * groove[..., None])
    h = groove * .006 + (strands2 - .5) * .003 + patina * .003
    metal = 1.0 - patina * .9 - tarn * .12
    smooth_v = .58 + (strands - .5) * .25 - patina * .35 - tarn * .18
    emit(name, srgb8(c), normal_from_height(h, 130), pack_metal_smooth(metal, smooth_v), tile_m, note)


def cable_sheath(name, seed, tile_m, note):
    rng = np.random.default_rng(seed)
    g = fbm(rng, N, N, [500, 1100], [1, 1])
    lowf = fbm(rng, N, N, [5, 18], [1, .6])
    dust = stretch(fbm(rng, N, N, [10, 44, 190], [1, .8, .6]), .62, .82)
    rib = 0.5 + .5 * np.sin(np.arange(N, dtype=np.float32)[:, None] / N * np.pi * 2 * 60) * np.ones((1, N), np.float32)
    c = np.array((.62, .63, .63), np.float32)[None, None, :] * (0.75 + .5 * g[..., None]) * (0.9 + .2 * lowf[..., None]) * (0.88 + .12 * rib[..., None])
    c = c * (1 - dust[..., None] * .3) + np.array((.42, .34, .24), np.float32)[None, None, :] * dust[..., None] * .3
    h = rib * .004 + (g - .5) * .003
    smooth_v = .34 + (g - .5) * .16 - dust * .12
    emit(name, srgb8(c), normal_from_height(h, 90), pack_metal_smooth(np.zeros((N, N), np.float32), smooth_v), tile_m, note)


def twine(name, seed, tile_m, note):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:N, 0:N].astype(np.float32) / N
    tw = 0.5 + 0.5 * np.sin((x * 28 + y * 96) * np.pi * 2)   # 3-ply diagonal lay
    fibre = fbm(rng, N, N, [900, 1700], [1, 1])
    mott = fbm(rng, N, N, [6, 28, 120], [1, .7, .5])
    c = np.array((.64, .55, .40), np.float32)[None, None, :] * (0.55 + .45 * tw[..., None]) * (0.8 + .4 * fibre[..., None]) * (0.85 + .3 * mott[..., None])
    h = tw * .007 + (fibre - .5) * .003
    emit(name, srgb8(c), normal_from_height(h, 140), pack_metal_smooth(np.zeros((N, N), np.float32), .10 + (fibre - .5) * .1), tile_m, note)


def sand(name, seed, tile_m, note):
    rng = np.random.default_rng(seed)
    g = fbm(rng, N, N, [500, 1000, 1800], [1, 1, .8])
    lowf = fbm(rng, N, N, [7, 23, 90], [1, .7, .5])
    pebble = stretch(vnoise(rng, N, N, 220, 220), .86, .95)
    c = np.array((.62, .50, .34), np.float32)[None, None, :] * (0.72 + .5 * g[..., None]) * (0.85 + .3 * lowf[..., None])
    c = c * (1 - pebble[..., None] * .3) + np.array((.34, .28, .21), np.float32)[None, None, :] * pebble[..., None] * .3
    h = (g - .5) * .012 + pebble * .006 + (lowf - .5) * .01
    emit(name, srgb8(c), normal_from_height(h, 100), pack_metal_smooth(np.zeros((N, N), np.float32), .05 + (g - .5) * .05), tile_m, note)


# ---------------------------------------------------------------- unique counter maps
def clay(name, seed, tile_m, note):
    """Unfired/low-fired porous water-jar ceramic (olla): matte, gritty, mineral salt bloom, faint throwing lines."""
    rng = np.random.default_rng(seed)
    g = fbm(rng, N, N, [500, 1000, 1800], [1, 1, .8])
    lowf = fbm(rng, N, N, [5, 17, 60], [1, .7, .5])
    throw = 0.5 + 0.5 * np.sin(np.arange(N, dtype=np.float32)[:, None] / N * np.pi * 2 * 40 + lowf * 3.0)
    grit = stretch(vnoise(rng, N, N, 300, 300), .90, .97)
    salt = stretch(fbm(rng, N, N, [8, 30, 110, 400], [1, .8, .6, .5]), .62, .80)
    c = np.array((.50, .27, .17), np.float32)[None, None, :] * (0.70 + .5 * g[..., None]) * (0.85 + .3 * lowf[..., None]) * (0.93 + .07 * throw[..., None])
    c = c * (1 - grit[..., None] * .4) + np.array((.72, .62, .46), np.float32)[None, None, :] * grit[..., None] * .4
    c = c * (1 - salt[..., None] * .5) + np.array((.78, .74, .66), np.float32)[None, None, :] * salt[..., None] * .5
    h = (g - .5) * .010 + throw * .0025 + grit * .004 + salt * .002
    emit(name, srgb8(c), normal_from_height(h, 110), pack_metal_smooth(np.zeros((N, N), np.float32), .04 + (g - .5) * .05 - salt * .02), tile_m, note)


def paper(name, seed, tile_m, note):
    """Kraft price/label paper. NO lettering: printed rule bands, tally ticks and a stamped seal ring only, so
    packaging never depends on generated text. Bands run along U (round a sleeve / along a card)."""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:N, 0:N].astype(np.float32) / N
    fibre = fbm(rng, N, N, [900, 1700], [1, 1])
    fibre2 = vnoise(rng, N, N, 1600, 40) * .5 + .5 * vnoise(rng, N, N, 700, 20)
    mott = fbm(rng, N, N, [5, 18, 70], [1, .8, .6])
    stain = stretch(fbm(rng, N, N, [7, 26, 100], [1, .8, .6]), .6, .8)
    base = np.array((.74, .64, .47), np.float32)[None, None, :] * (0.86 + .14 * fibre[..., None]) * (0.92 + .08 * fibre2[..., None]) * (0.92 + .16 * mott[..., None])
    ink = np.zeros((N, N), np.float32)
    ink_c = np.zeros((N, N, 3), np.float32)

    def band(y0, y1, col, soft=.002):
        m = np.clip((y - y0) / soft, 0, 1) * np.clip((y1 - y) / soft, 0, 1)
        return m[..., None] * np.array(col, np.float32)[None, None, :], m
    layers = [band(.36, .50, (.10, .20, .17)), band(.53, .545, (.34, .07, .05)), band(.30, .315, (.34, .07, .05)), band(.84, .855, (.12, .12, .10)), band(.145, .16, (.12, .12, .10))]
    col = base.copy()
    for lc, m in layers:
        col = col * (1 - m[..., None] * .92) + lc * .92
    # tally ticks (five-bar gates) in the top band
    for gx in (.10, .29, .48, .67, .86):
        for k in range(4):
            xx = gx + k * .028
            m = np.clip(1 - np.abs(x - xx) / .0045, 0, 1) * ((y > .64) & (y < .80)) * (0.75 + .25 * fibre)
            col = col * (1 - m[..., None] * .8) + np.array((.12, .12, .10), np.float32)[None, None, :] * m[..., None] * .8
        m = np.clip(1 - np.abs((y - .72) - (x - gx - .014) * .05) / .0045, 0, 1) * ((x > gx - .01) & (x < gx + .1))
        col = col * (1 - m[..., None] * .8) + np.array((.12, .12, .10), np.float32)[None, None, :] * m[..., None] * .8
    # rubber-stamp seal: ring, inner ring, cross
    cx, cy = .5, .225
    d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
    ring = np.clip(1 - np.abs(d - .085) / .006, 0, 1) + np.clip(1 - np.abs(d - .062) / .003, 0, 1) * .8
    crossm = np.maximum(np.clip(1 - np.abs(x - cx) / .006, 0, 1) * (np.abs(y - cy) < .045), np.clip(1 - np.abs(y - cy) / .006, 0, 1) * (np.abs(x - cx) < .045))
    st = np.clip(ring + crossm, 0, 1) * (0.55 + .45 * fibre) * (0.6 + .4 * stretch(fbm(rng, N, N, [30, 120], [1, .8]), .3, .7))
    col = col * (1 - st[..., None] * .75) + np.array((.42, .09, .06), np.float32)[None, None, :] * st[..., None] * .75
    col = col * (1 - stain[..., None] * .22) + np.array((.30, .22, .13), np.float32)[None, None, :] * stain[..., None] * .22
    h = (fibre - .5) * .004 + (fibre2 - .5) * .002 - ink * .0
    emit(name, srgb8(col), normal_from_height(h, 90), pack_metal_smooth(np.zeros((N, N), np.float32), .16 + (fibre - .5) * .1), tile_m, note)


PPM = 966.0   # pixels per metre for the unique maps (4.24 m -> 4096 px)


def line_mask(shape, pts, width_px, soft=1.0):
    """Anti-aliased polyline as mask from pixel points (x,y)."""
    m = np.zeros(shape, np.float32)
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        n = int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 2
        t = np.linspace(0, 1, n)
        xs = np.clip((x0 + (x1 - x0) * t).astype(int), 0, shape[1] - 1)
        ys = np.clip((y0 + (y1 - y0) * t).astype(int), 0, shape[0] - 1)
        m[ys, xs] = 1
    return np.clip(blur(m, width_px * soft) * (width_px * 5.0), 0, 1)


def blob(shape, cx, cy, rx, ry, angle=0.0):
    y, x = np.mgrid[0:shape[0], 0:shape[1]].astype(np.float32)
    dx = x - cx; dy = y - cy
    c, s = np.cos(angle), np.sin(angle)
    u = (dx * c + dy * s) / rx; v = (-dx * s + dy * c) / ry
    return np.exp(-(u * u + v * v) * 2.0)


def counter_top():
    """4.24 m x 0.53 m. Image x = Unity x (left..right, -2.12..2.12). Image row 0 = front nosing edge, row 511 = wall side.
    Rows 0..~30 cover the rounded nosing and its drop; the flat top starts near row 55."""
    H, W = 512, 4096
    rng = np.random.default_rng(929101)
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    X = x / PPM - 2.12; V = y / PPM                       # V = metres back from the front edge
    mott = fbm(rng, H, W, [4, 14, 60, 240], [1, .8, .6, .4], aniso=8)
    grain = fbm(rng, H, W, [400, 900], [1, 1], aniso=8)
    # base enamel: cream-green worn steel counter, darker toward the wall (shadowed, less handled)
    paint = np.array((.47, .50, .42), np.float32)[None, None, :] * (0.86 + .24 * mott[..., None])
    steel = np.array((.58, .58, .57), np.float32)[None, None, :] * (0.85 + .3 * grain[..., None])
    oxide = np.array((.30, .16, .085), np.float32)[None, None, :]
    # hand contact: broad leaning band along front edge in the serving zone, elbow patches, and item-slide streaks
    zone = np.exp(-((X + 0.05) / 1.1) ** 4)                                   # serving zone (centre, where Mira works)
    lean = np.clip(np.exp(-((V - 0.11) / 0.07) ** 2), 0, 1) * zone            # forearm band ~11 cm back from the edge
    palms = np.zeros((H, W), np.float32)
    for cx, cy, rx, ry, a in [(-0.62, .14, .075, .05, .3), (-0.22, .13, .07, .045, -.2), (.31, .15, .08, .05, .1), (.83, .16, .07, .05, -.4),
                              (-1.32, .12, .06, .04, .2), (1.28, .13, .06, .04, 0)]:
        palms = np.maximum(palms, blob((H, W), (cx + 2.12) * PPM, cy * PPM, rx * PPM, ry * PPM, a))
    slide = np.zeros((H, W), np.float32)
    for _ in range(90):                                                        # item-slide streaks toward the customer edge
        cx = (rng.normal(0.0, 0.85) + 2.12) * PPM; cy = (0.06 + rng.random() * .22) * PPM
        L = (0.05 + rng.random() * .22) * PPM; a = (rng.random() - .5) * .35
        slide = np.maximum(slide, line_mask((H, W), [(cx - L, cy - L * a), (cx + L, cy + L * a)], 1.2) * (0.35 + .65 * rng.random()))
    nose = stretch(0.06 - V, -0.005, 0.02)                                    # the leading edge always polished
    wear_noise = fbm(rng, H, W, [10, 40, 200], [1, .7, .5], aniso=6)
    wear = np.clip((lean * .75 + palms * 1.0 + slide * .6 + nose * .55) * (0.7 + .6 * wear_noise), 0, 1)
    wear = stretch(wear, .34, .95) * .9
    # oil ring stains, water tide marks, and dust settled toward the wall and into panel joins
    rings = np.zeros((H, W), np.float32)
    for cx, cy, r in [(-1.05, .17, .052), (.98, .20, .045), (-.31, .27, .04), (1.61, .13, .05)]:
        d = np.sqrt((x - (cx + 2.12) * PPM) ** 2 + (y - cy * PPM) ** 2)
        rings = np.maximum(rings, np.exp(-((d - r * PPM) / 5.0) ** 2) * (0.25 + .5 * vnoise(rng, H, W, 6, 6)) * (d < r * PPM * 1.3))
    oil = stretch(fbm(rng, H, W, [5, 22, 90], [1, .8, .6], aniso=5), .58, .74) * (0.4 + 0.6 * stretch(V, .16, .32))
    dust = np.clip(stretch(V, .20, .36) * (0.55 + .6 * fbm(rng, H, W, [30, 130], [1, .8], aniso=5)), 0, 1) * (1 - wear * .85)
    seam = np.zeros((H, W), np.float32)
    for sx in (-1.06, 1.06):                                                    # welded sheet joins, dust and rust bleed
        seam = np.maximum(seam, np.exp(-((X - sx) / 0.0025) ** 2) * (V > .06) * (0.5 + .5 * vnoise(rng, H, W, 3, 80)))
    rustm = stretch(fbm(rng, H, W, [8, 30, 120], [1, .8, .6], aniso=6), .69, .8) * stretch(V, .2, .34) + blur(seam, 6) * .35
    sc = np.clip(scratches(rng, H, W, 240, 90, 0.0, .5, 1.3), 0, 1) * (0.25 + .75 * zone)
    c = paint
    c = c * (1 - oil[..., None] * .35) + np.array((.14, .12, .09), np.float32)[None, None, :] * oil[..., None] * .35
    c = c * (1 - rings[..., None] * .3) + np.array((.23, .2, .14), np.float32)[None, None, :] * rings[..., None] * .3
    c = c * (1 - rustm[..., None] * .5) + oxide * rustm[..., None] * .5
    c = c * (1 - sc[..., None] * .22) + steel * sc[..., None] * .22
    c = c * (1 - wear[..., None] * .8) + steel * wear[..., None] * .8         # paint worn through to polished metal
    sandc = np.array((.60, .49, .34), np.float32)[None, None, :]
    c = c * (1 - dust[..., None] * .5) + sandc * dust[..., None] * .5
    c = c * (1 - seam[..., None] * .22)
    h = (grain - .5) * .0012 - wear * .0012 - seam * .003 - sc * .0012 + rustm * .0012 + dust * .0016
    metal = np.clip(wear * .95 + sc * .3 + .02, 0, 1) * (1 - rustm) * (1 - dust * .7)
    smooth_v = (.60 - .22 * mott) * (1 - wear) + .70 * wear
    smooth_v = smooth_v * (1 - dust * .9) + .06 * dust * .9
    smooth_v = smooth_v * (1 - rustm) + .12 * rustm
    smooth_v = smooth_v * (1 - oil * .5) + .8 * oil * .5
    emit('BGC_CounterTop', srgb8(c), normal_from_height(h, 200), pack_metal_smooth(metal, smooth_v), None,
         'Unique 4096x512, 966 px/m. Row 0 = counter nosing; x = -2.12..2.12 m. Hand-contact polish, streaks, rings, weld joins, dust.', PPM)


def counter_face():
    """4.24 m x 1.06 m. Image x = Unity x; row 1023 = porch floor (y 0), row 0 = y 1.06 m. Bays: teal | ochre | olive."""
    H, W = 1024, 4096
    rng = np.random.default_rng(929102)
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    X = x / PPM - 2.12; Y = (H - 1 - y) / PPM
    mott = fbm(rng, H, W, [4, 14, 60, 240], [1, .8, .6, .4])
    grain = fbm(rng, H, W, [500, 1000], [1, 1])
    stiles = [(-2.12, -2.045), (-0.735, -0.66), (0.66, 0.735), (2.045, 2.12)]
    bays = [(-2.045, -0.735), (-0.66, 0.66), (0.735, 2.045)]
    bay_col = [(.24, .36, .34), (.55, .42, .22), (.31, .37, .22)]
    in_stile = np.zeros((H, W), bool)
    for a, b in stiles:
        in_stile |= (X >= a) & (X < b)
    plinth = Y < 0.09
    col = np.zeros((H, W, 3), np.float32)
    bayid = np.full((H, W), -1)
    for i, (a, b) in enumerate(bays):
        m = (X >= a) & (X < b)
        col[m] = np.array(bay_col[i], np.float32)
        bayid[m] = i
    col[in_stile] = np.array((.20, .21, .21), np.float32)
    col *= (0.80 + .40 * mott[..., None]) * (0.985 + .03 * grain[..., None]) * (0.92 + .16 * fbm(rng, H, W, [3, 9], [1, .6])[..., None])
    steel = np.array((.56, .56, .55), np.float32)[None, None, :] * (0.85 + .3 * grain[..., None])
    oxide = np.array((.30, .16, .085), np.float32)[None, None, :]
    # edge wear: bare metal along the stile edges and panel borders, where hands and cargo touch
    edge_d = np.full((H, W), 9.0, np.float32)
    for a, b in bays:
        edge_d = np.minimum(edge_d, np.minimum(np.abs(X - a), np.abs(X - b)))
    edge_d = np.minimum(edge_d, np.abs(Y - 0.9) + 0.006)
    ew = stretch(0.010 - edge_d, 0, 0.010) * (0.15 + 1.1 * fbm(rng, H, W, [30, 120, 400], [1, .8, .6]) ** 2)
    ew = stretch(ew, .30, .85) * .85
    # kick scuffs: lots low down, few high up; scratches biased horizontal
    kick = stretch(0.55 - Y, 0, .5) ** 1.5
    scuff = np.clip(scratches(rng, H, W, 700, 80, 0.0, .6, 1.2), 0, 1) * (0.06 + kick)
    boot = np.zeros((H, W), np.float32)
    for _ in range(40):
        cx = rng.random() * W; cy = (H - 1) - (rng.random() * .32 * PPM + .06 * PPM)
        boot = np.maximum(boot, blob((H, W), cx, cy, (.04 + rng.random() * .06) * PPM, (.015 + rng.random() * .02) * PPM, (rng.random() - .5) * .5) * (.4 + .6 * rng.random()))
    grime = stretch(fbm(rng, H, W, [6, 24, 100], [1, .8, .6]), .5, .78) * stretch(0.7 - Y, 0, .7)
    # rust weeps below the fixing bolts (matches bolt positions used in the mesh)
    weeps = np.zeros((H, W), np.float32)
    for bx in (-2.0825, -0.6975, 0.6975, 2.0825, -1.35, -0.06, 1.42):
        for by in (0.16, 0.74):
            L = (0.05 + rng.random() * .16) * PPM
            xx = (bx + 2.12) * PPM + rng.normal(0, 1.5); yy = (H - 1) - by * PPM
            weeps = np.maximum(weeps, line_mask((H, W), [(xx, yy), (xx + rng.normal(0, 2), yy + L)], 3.5) * (.25 + .35 * rng.random()))
            weeps = np.maximum(weeps, blob((H, W), xx, yy, 7, 7) * .8)
    rustm = stretch(fbm(rng, H, W, [8, 30, 120], [1, .8, .6]), .68, .80) * stretch(0.5 - Y, -.2, .5)
    # dents (soft) in bay 1 lower and bay 3 mid: real cargo strikes
    dents = np.zeros((H, W), np.float32)
    for cx, cy, r in [(-1.5, .30, .09), (-1.18, .21, .05), (1.62, .42, .07)]:
        dents = np.maximum(dents, blob((H, W), (cx + 2.12) * PPM, (H - 1) - cy * PPM, r * PPM, r * PPM * .8))
    # dust: banked along the plinth top and the underside of the counter slab
    dustline = np.exp(-((Y - 0.095) / 0.018) ** 2) * (0.55 + .6 * fbm(rng, H, W, [40, 200], [1, .8])) + stretch(Y, .86, .9) * .0
    dust = np.clip(dustline * .9 + stretch(0.14 - Y, 0, .14) * .35 * grime, 0, 1)
    # hand plate on centre bay & handle grip wear (right bay), padlock hasp scuffs
    palm = np.maximum(blob((H, W), (0.0 + 2.12) * PPM, (H - 1) - 0.60 * PPM, .11 * PPM, .075 * PPM), blob((H, W), (1.66 + 2.12) * PPM, (H - 1) - 0.47 * PPM, .05 * PPM, .09 * PPM))
    c = col
    c = c * (1 - grime[..., None] * .35) + np.array((.10, .09, .07), np.float32)[None, None, :] * grime[..., None] * .35
    c = c * (1 - weeps[..., None] * .6) + oxide * weeps[..., None] * .6
    c = c * (1 - rustm[..., None] * .55) + oxide * rustm[..., None] * .55
    c = c * (1 - scuff[..., None] * .32) + steel * scuff[..., None] * .32
    c = c * (1 - boot[..., None] * .45) + np.array((.11, .10, .09), np.float32)[None, None, :] * boot[..., None] * .45
    c = c * (1 - ew[..., None]) + steel * ew[..., None]
    c = c * (1 - palm[..., None] * .18) + steel * palm[..., None] * .18
    c = c * (1 - dents[..., None] * .12)
    plinth_col = np.array((.40, .36, .30), np.float32)[None, None, :] * (0.75 + .5 * grain[..., None]) * (0.85 + .3 * mott[..., None])
    c = np.where(plinth[..., None], plinth_col, c)
    sandc = np.array((.60, .49, .34), np.float32)[None, None, :]
    c = c * (1 - dust[..., None] * .55) + sandc * dust[..., None] * .55
    h = (grain - .5) * .0012 - ew * .0016 - scuff * .0018 - dents * .006 + rustm * .0016 + weeps * .0012 + dust * .002
    for a, b in stiles:                                                            # stiles stand proud of bays
        h += ((X >= a) & (X < b)) * .006
    h += (np.abs(Y - 0.9) < .003) * -.003 + (np.abs(Y - .09) < .003) * -.004
    metal = np.clip(ew * .95 + scuff * .35 + palm * .5 + .02, 0, 1) * (1 - rustm) * (1 - dust * .7)
    metal = np.where(plinth, 0, metal)
    smooth_v = (.56 - .26 * mott + (.08 if False else 0)) * (1 - ew) + .70 * ew
    smooth_v = smooth_v * (1 - grime * .4) - grime * .1
    smooth_v = smooth_v * (1 - rustm) + .10 * rustm
    smooth_v = smooth_v * (1 - dust * .9) + .06 * dust * .9
    smooth_v = np.where(plinth, .12, smooth_v)
    emit('BGC_CounterFace', srgb8(c), normal_from_height(h, 200), pack_metal_smooth(metal, smooth_v), None,
         'Unique 4096x1024, 966 px/m. x = -2.12..2.12 m, row 1023 = porch level. Bays teal|ochre|olive, kick scuffs, bolt rust weeps, plinth dust.', PPM)


import sys
ONLY = set(sys.argv[1:])


def want(k):
    return not ONLY or k in ONLY


if __name__ == '__main__':
    old = json.loads((OUT / 'manifest.json').read_text())['materials'] if ONLY and (OUT / 'manifest.json').exists() else []
    if want('BGC_Enamel'): painted('BGC_Enamel', 929201, (.80, .79, .75), 0.30, 0.055, 0.35, 90, 0.30,
            'Neutral light enamel over steel; tint per use (sand flask, olive flask, bone case, red cross). Chips expose steel, rust halo.')
    if want('BGC_ShelfPaint'): painted('BGC_ShelfPaint', 929202, (.50, .55, .48), 0.55, 0.11, 0.60, 260, 0.60,
            'Satin painted structural steel (shelving, hardware brackets); heavier chipping and rust than enamel.', orange_peel=0.8)
    if want('BGC_BareSteel'): bare_steel('BGC_BareSteel', 929203, 0.50, 'Brushed bare steel: shelf lips, brackets, latches, hooks, loops. Also tinted brass for fittings.')
    if want('BGC_Rubber'): rubber('BGC_Rubber', 929204, 0.30, 'Dark rubber: corner guards, caps, sale mat, feet. Fine grain, crazing, dust bloom.')
    if want('BGC_Webbing'): webbing('BGC_Webbing', 929205, 0.12, 'Woven twill webbing (straps, roll pack). Tint per use.')
    if want('BGC_CopperWire'): copper_wire('BGC_CopperWire', 929206, 0.10, 'Stranded copper: U round bundle, V along; verdigris and tarnish patches.')
    if want('BGC_CableSheath'): cable_sheath('BGC_CableSheath', 929207, 0.20, 'Insulated cable sheath with ribbing; tint per use.')
    if want('BGC_Twine'): twine('BGC_Twine', 929208, 0.10, '3-ply twine ties.')
    if want('BGC_Sand'): sand('BGC_Sand', 929209, 0.50, 'Fine settled desert dust for local drifts (opaque geometry, no alpha).')
    if want('BGC_Clay'): clay('BGC_Clay', 929210, 0.40, 'Porous unglazed water-jar ceramic (olla): matte grit, salt bloom, throwing lines. Wet base = darker tint + higher smoothness at material level.')
    if want('BGC_Paper'): paper('BGC_Paper', 929211, 0.35, 'Kraft label/tag paper with printed rule bands, tally ticks and stamped seal ring; deliberately no lettering.')
    if want('BGC_CounterTop'): counter_top()
    if want('BGC_CounterFace'): counter_face()
    done = {m['material'] for m in MANIFEST}
    MANIFEST.extend(m for m in old if m['material'] not in done)
    (OUT / 'manifest.json').write_text(json.dumps({
        'author': 'Original deterministic Ward material synthesis (numpy), Basic General counter dressing',
        'date': '2026-09-29', 'licence': 'Project original; no third-party source imagery',
        'seed': 'per-material seeds 929201-929209, 929101, 929102 in make_textures.py',
        'normal': 'OpenGL +Y tangent space', 'packed': 'R metallic; A smoothness; G/B zero',
        'colourSpace': 'BaseColor sRGB; Normal + MetalSmooth linear', 'materials': MANIFEST}, indent=2))
    print('done', len(MANIFEST), 'materials')
