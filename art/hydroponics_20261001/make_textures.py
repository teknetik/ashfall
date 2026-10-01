#!/usr/bin/env python3
"""Ward hydroponics (1 Oct 2026): textures for the crop kit and the working yard.

crop_atlas (2048², 4x4 cells of 512 px, RGBA, alpha-clipped): photographed CC0 leaves cut from the Poly Haven plant
atlases (fetch_polyhaven.py), stood upright (petiole at the bottom centre of the cell, tip up), cleaned of spots and
recoloured into crop varieties, plus a few procedural parts (tomato fruit, bean pod, seedling, microgreens, stem):

  row 0  tomato compound leaf A, tomato compound leaf B (leaflets composed on a petiole), mint/nettle leaflet, basil
  row 1  chard (red midrib), rainbow chard (yellow midrib), cos lettuce A, cos lettuce B
  row 2  butterhead A, butterhead B, red oak-leaf, green oak-leaf
  row 3  runner-bean trifoliate A, B, [scarlet flower | bean pod | seedling | stem], [tomato fruit x4 ripeness | microgreens]

crop_atlas.json records each cell's UV rect and the leaf's aspect (width / height) so author_hydroponics.py can size cards
without stretching. Also: crop_atlas_n (OpenGL normal from luminance), pvc (NFT channel white with algae line),
shade_cloth (knitted, alpha), led_diffuser, labels. Run: uv run --with pillow --with numpy --with scipy python make_textures.py
"""
import json, math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

HERE = Path(__file__).resolve().parent
PH = HERE / "polyhaven" / "models"
OUT = HERE / "textures"
OUT.mkdir(exist_ok=True)
rng = np.random.default_rng(20261001)
N, C = 2048, 512


def load(aid):
    d = np.asarray(Image.open(PH / aid / "textures" / f"{aid}_diff_2k.jpg").convert("RGB")).astype(np.float32) / 255
    a = np.asarray(Image.open(PH / aid / "textures" / f"{aid}_alpha_2k.png").convert("L")).astype(np.float32) / 255
    return d, a


SRC = {k: load(k) for k in ("nettle_plant", "weed_plant_02", "dandelion_01", "shrub_sorrel_01")}


def sprite(aid, box, base, tip, clean=True, open_r=5):
    """Cut a leaf (preview coordinates of the 1024 contact sheet, x2 for the 2k maps): box=(x0,y0,x1,y1),
    base = petiole end, tip = leaf tip. Returns an RGBA float image with the base at the bottom centre, tip up."""
    d, a = SRC[aid]
    x0, y0, x1, y1 = [v * 2 for v in box]
    rgb = d[y0:y1, x0:x1].copy(); al = a[y0:y1, x0:x1].copy()
    # keep only the component under the leaf centre line (drop neighbours cut by the box)
    lab, n = ndimage.label(al > .5)
    bx, by = base[0] * 2 - x0, base[1] * 2 - y0; tx, ty = tip[0] * 2 - x0, tip[1] * 2 - y0
    keep = set()
    for t in np.linspace(.15, .85, 15):
        px, py = int(bx + (tx - bx) * t), int(by + (ty - by) * t)
        if 0 <= py < lab.shape[0] and 0 <= px < lab.shape[1] and lab[py, px]: keep.add(lab[py, px])
    m = (al > .5) & (np.isin(lab, list(keep)) if keep else True)
    # cut thin streaks (padding fragments of neighbouring UV islands) and keep the leaf body
    yy, xx = np.mgrid[-open_r:open_r + 1, -open_r:open_r + 1]
    opened = ndimage.binary_opening(m, structure=(xx * xx + yy * yy) <= open_r * open_r)
    lab2, n2 = ndimage.label(opened)
    if n2:
        areas = ndimage.sum(opened, lab2, range(1, n2 + 1))
        body = lab2 == (1 + int(np.argmax(areas)))
        m = ndimage.binary_dilation(body, iterations=min(open_r, 8)) & m
    filled = ndimage.binary_fill_holes(m)
    # colour for filled holes and for spots: normalised blur of the leaf colour
    def fill_from(mask_ok, size):
        w = ndimage.uniform_filter(mask_ok.astype(np.float32), size) + 1e-6
        return np.stack([ndimage.uniform_filter(rgb[..., c] * mask_ok, size) / w for c in range(3)], -1)
    if clean:   # disease spots: replace pixels far darker/redder than the local median
        med = np.stack([ndimage.median_filter(rgb[..., c], size=15) for c in range(3)], -1)
        lum = rgb.mean(-1); mlum = med.mean(-1)
        spot = (lum < mlum * .78) | ((rgb[..., 0] - rgb[..., 1]) > (med[..., 0] - med[..., 1]) + .08)
        spot = ndimage.binary_dilation(spot, iterations=2) & m
        rgb[spot] = med[spot]
    holes = filled & ~m
    if holes.any():
        f = fill_from(m & ~ndimage.binary_dilation(holes, iterations=2), 31)
        rgb[holes] = f[holes]
    al = filled.astype(np.float32)
    img = np.dstack([rgb, al])
    ang = math.degrees(math.atan2(tx - bx, -(ty - by)))     # rotate so base->tip points up
    im = Image.fromarray((img * 255).astype(np.uint8), "RGBA")
    # rotate about the base: pad so the base is the centre
    W, H = im.size
    pad = int(math.hypot(W, H))
    canvas = Image.new("RGBA", (pad * 2, pad * 2), (0, 0, 0, 0))
    canvas.paste(im, (int(pad - bx), int(pad - by)))
    canvas = canvas.rotate(ang, resample=Image.BICUBIC, center=(pad, pad))
    arr = np.asarray(canvas).astype(np.float32) / 255
    ys, xs = np.nonzero(arr[..., 3] > .5)
    y_top, y_bot = ys.min(), pad
    half = max(abs(xs.min() - pad), abs(xs.max() - pad)) + 2
    out = arr[y_top:y_bot + 2, pad - half:pad + half]
    return out


def fit(spr, cell_px=C, margin=10):
    """Scale a sprite into a square cell, base at the bottom centre. Returns (RGBA cell, aspect w/h, used height)."""
    h, w = spr.shape[:2]
    s = min((cell_px - 2 * margin) / h, (cell_px - 2 * margin) / w)
    im = Image.fromarray((np.clip(spr, 0, 1) * 255).astype(np.uint8), "RGBA").resize((max(1, int(w * s)), max(1, int(h * s))), Image.LANCZOS)
    cell = Image.new("RGBA", (cell_px, cell_px), (0, 0, 0, 0))
    cell.paste(im, ((cell_px - im.size[0]) // 2, cell_px - margin - im.size[1]), im)
    return np.asarray(cell).astype(np.float32) / 255, w / h, im.size[1] / cell_px, im.size[0] / cell_px


def hsv_adjust(rgba, hue=0., sat=1., val=1., gamma=1.):
    rgb = rgba[..., :3]
    mx = rgb.max(-1); mn = rgb.min(-1); d = mx - mn + 1e-6
    h = np.where(mx == rgb[..., 0], (rgb[..., 1] - rgb[..., 2]) / d % 6, np.where(mx == rgb[..., 1], (rgb[..., 2] - rgb[..., 0]) / d + 2, (rgb[..., 0] - rgb[..., 1]) / d + 4)) / 6
    s = d / (mx + 1e-6); v = mx
    h = (h + hue) % 1; s = np.clip(s * sat, 0, 1); v = np.clip((v ** gamma) * val, 0, 1)
    i = np.floor(h * 6); f = h * 6 - i; p = v * (1 - s); q = v * (1 - f * s); t = v * (1 - (1 - f) * s)
    i = i.astype(int) % 6
    r = np.choose(i, [v, q, p, p, t, v]); g = np.choose(i, [t, v, v, q, p, p]); b = np.choose(i, [p, p, t, v, v, q])
    return np.dstack([r, g, b, rgba[..., 3]])


def edge_dist(alpha):
    return ndimage.distance_transform_edt(alpha > .5)


def tint(rgba, target, amount):
    """Blend towards a target colour keeping luminance detail."""
    rgb = rgba[..., :3]; lum = rgb.mean(-1, keepdims=True)
    t = np.array(target)[None, None]
    col = t * (lum / (t.mean() + 1e-6))
    a = amount if np.ndim(amount) == 0 else amount[..., None]
    return np.dstack([np.clip(rgb * (1 - a) + col * a, 0, 1), rgba[..., 3]])


atlas = np.zeros((N, N, 4), np.float32)
meta = {}


def put(key, cell_rgba, r, c, aspect, used_h, used_w, sub=None):
    """sub=(i, j, n): place into sub-cell (i, j) of an n x n split of cell (r, c)."""
    if sub:
        i, j, n = sub; size = C // n
        y0, x0 = r * C + i * size, c * C + j * size
    else:
        size = C; y0, x0 = r * C, c * C
    atlas[y0:y0 + size, x0:x0 + size] = cell_rgba
    # UV (v up): rect of the full (sub)cell; the leaf occupies used_h from the bottom margin
    u0, u1 = x0 / N, (x0 + size) / N
    v0, v1 = 1 - (y0 + size) / N, 1 - y0 / N
    meta[key] = dict(uv=[round(u0, 5), round(v0, 5), round(u1, 5), round(v1, 5)], aspect=round(aspect, 3),
                     used_h=round(used_h, 3), used_w=round(used_w, 3), margin=round(10 / size, 4))


# ------------------------------------------------------------------ leaves (preview-sheet coordinates, see comp_*.jpg)
leaf = {}
leaf["n4"] = sprite("nettle_plant", (380, 635, 605, 870), (497, 860), (492, 645), open_r=8)
leaf["n3"] = sprite("nettle_plant", (510, 330, 675, 595), (545, 345), (600, 585), open_r=8)
leaf["n2"] = sprite("nettle_plant", (350, 150, 560, 355), (545, 215), (365, 330), open_r=8)
leaf["n1"] = sprite("nettle_plant", (15, 60, 190, 255), (180, 155), (25, 150), open_r=8)
leaf["n7"] = sprite("nettle_plant", (20, 570, 210, 745), (200, 650), (30, 640), open_r=8)
leaf["n9"] = sprite("nettle_plant", (815, 785, 995, 960), (825, 865), (985, 880), open_r=8)
leaf["w3"] = sprite("weed_plant_02", (765, 160, 1012, 530), (893, 525), (905, 170), open_r=24)
leaf["w1"] = sprite("weed_plant_02", (240, 0, 705, 300), (700, 150), (250, 110), open_r=22)
leaf["w2"] = sprite("weed_plant_02", (270, 312, 700, 460), (690, 375), (280, 385), open_r=20)
leaf["w4"] = sprite("weed_plant_02", (145, 495, 690, 800), (675, 635), (155, 715), open_r=13)
leaf["w5"] = sprite("weed_plant_02", (345, 780, 940, 1023), (930, 895), (355, 945), open_r=13)
leaf["d1"] = sprite("dandelion_01", (20, 225, 175, 955), (130, 945), (90, 235))
leaf["d3"] = sprite("dandelion_01", (505, 675, 1005, 875), (515, 765), (995, 800))
leaf["d4"] = sprite("dandelion_01", (315, 805, 1005, 1015), (990, 960), (330, 900))
leaf["s1"] = sprite("shrub_sorrel_01", (5, 15, 400, 372), (190, 188), (200, 30), clean=False)
leaf["s3"] = sprite("shrub_sorrel_01", (18, 438, 438, 818), (218, 616), (230, 450), clean=False)

# sorrel: the trifoliate is centred on its junction; use the whole leaf as a card centred (not base-up)
def centred(aid, box):
    d, a = SRC[aid]
    x0, y0, x1, y1 = [v * 2 for v in box]
    return np.dstack([d[y0:y1, x0:x1], a[y0:y1, x0:x1]])


def lettuce(spr, colour, pale_base=.55, frill=.0, red_edge=None, seed=0):
    """Recolour a leaf into a lettuce: yellow-green base fading to the variety colour, a pale midrib, darker frilled edge."""
    rgba = spr.copy()
    h, w = rgba.shape[:2]
    yy = np.linspace(0, 1, h)[:, None] * np.ones((1, w))            # 0 at the tip, 1 at the base
    lum = rgba[..., :3].mean(-1)
    lum = (lum - lum[rgba[..., 3] > .5].mean()) * 1.1 + .5          # keep vein detail
    base_col = np.array([.78, .86, .42]); var = np.array(colour)
    t = np.clip((yy - (1 - pale_base)) / pale_base, 0, 1) ** 1.3        # 1 near the base
    col = var[None, None] * (1 - t[..., None]) + base_col[None, None] * t[..., None]
    rgb = col * (.62 + .76 * lum[..., None])
    ed = edge_dist(rgba[..., 3])
    if frill:
        edge = np.clip(1 - ed / frill, 0, 1)
        rgb *= (1 - .28 * edge[..., None])
    if red_edge is not None:
        edge = np.clip(1 - ed / red_edge[1], 0, 1) ** .8 * (1 - t) ** .6
        rgb = rgb * (1 - edge[..., None]) + np.array(red_edge[0])[None, None] * (.55 + .7 * lum[..., None]) * edge[..., None]
    # midrib: pale line along the centre column
    cx = w / 2; xx = np.arange(w)[None, :] * np.ones((h, 1))
    rib = np.exp(-((xx - cx) / (w * .018 + 1.5)) ** 2) * (yy ** .5)
    rgb = rgb * (1 - .45 * rib[..., None]) + np.array([.88, .92, .7])[None, None] * .45 * rib[..., None]
    return np.dstack([np.clip(rgb, 0, 1), rgba[..., 3]])


def compound(leaflets, n=7, width=380, height=512, seed=1):
    """Tomato compound leaf: a petiole up the middle with paired, separated leaflets and a terminal leaflet."""
    r = np.random.default_rng(seed)
    cell = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    dr = ImageDraw.Draw(cell)
    cx = width // 2
    dr.line([(cx, height), (cx + 4, 90)], fill=(84, 110, 50, 255), width=6)     # petiole
    pairs = [(.2, 1), (.24, -1), (.44, 1), (.48, -1), (.66, 1), (.7, -1)][:n - 1]
    for k, (t, side) in enumerate(pairs):
        spr = leaflets[k % len(leaflets)]
        im = Image.fromarray((np.clip(spr, 0, 1) * 255).astype(np.uint8), "RGBA")
        s = (.27 - t * .1) * height / im.size[1] * (1 + r.uniform(-.1, .1))
        im = im.resize((max(1, int(im.size[0] * s)), max(1, int(im.size[1] * s))), Image.LANCZOS)
        im = im.rotate(-side * (70 - t * 25), resample=Image.BICUBIC, expand=True)
        y = int(height * (1 - t) - im.size[1] * .62)
        x = cx + 3 if side > 0 else cx - im.size[0] - 3
        cell.alpha_composite(im, (max(0, min(width - im.size[0], x)), max(0, y)))
    term = Image.fromarray((np.clip(leaflets[0], 0, 1) * 255).astype(np.uint8), "RGBA")
    s = .3 * height / term.size[1]
    term = term.resize((int(term.size[0] * s), int(term.size[1] * s)), Image.LANCZOS)
    cell.alpha_composite(term, (cx - term.size[0] // 2 + 4, 4))
    return np.asarray(cell).astype(np.float32) / 255


# tomato leaflets: nettle darkened to a blue-green
tl = [hsv_adjust(leaf[k], hue=.015, sat=.95, val=.78, gamma=1.1) for k in ("n4", "n3", "n2", "n1", "n7", "n9")]
for k, (seed, order) in enumerate([(3, [0, 1, 2, 3, 4]), (7, [2, 4, 5, 1, 0])]):
    comp = compound([tl[i] for i in order], n=7, seed=seed)
    cell, asp, uh, uw = fit(comp)
    put(f"tomato_leaf_{'ab'[k]}", cell, 0, k, asp, uh, uw)
cell, asp, uh, uw = fit(hsv_adjust(leaf["n4"], hue=.02, sat=1.05, val=.95))
put("mint_leaf", cell, 0, 2, asp, uh, uw)
basil = lettuce(leaf["w2"], (.2, .52, .12), pale_base=.2, frill=0)
basil = hsv_adjust(basil, sat=1.1, val=.95)
cell, asp, uh, uw = fit(basil)
put("basil_leaf", cell, 0, 3, asp, uh, uw)

# chard: the dock-like weed leaf has a red midrib; deepen green, gloss
chard = hsv_adjust(leaf["w3"], hue=.02, sat=1.25, val=.82, gamma=1.15)
cell, asp, uh, uw = fit(chard)
put("chard_red", cell, 1, 0, asp, uh, uw)
ch2 = leaf["w4"].copy()
h, w = ch2.shape[:2]
xx = np.arange(w)[None, :] * np.ones((h, 1)); yy = np.linspace(0, 1, h)[:, None]
rib = np.exp(-((xx - w / 2) / (w * .012 * (.4 + yy) + 1.5)) ** 2) * (.35 + .65 * yy)
ch2 = hsv_adjust(ch2, hue=.02, sat=1.2, val=.8, gamma=1.15)
ch2[..., :3] = ch2[..., :3] * (1 - rib[..., None] * .8) + np.array([.88, .78, .3]) * rib[..., None] * .8
cell, asp, uh, uw = fit(ch2)
put("chard_yellow", cell, 1, 1, asp, uh, uw)
cell, asp, uh, uw = fit(lettuce(leaf["w5"], (.3, .6, .16), pale_base=.6))
put("cos_a", cell, 1, 2, asp, uh, uw)
cell, asp, uh, uw = fit(lettuce(leaf["w2"], (.34, .62, .18), pale_base=.55))
put("cos_b", cell, 1, 3, asp, uh, uw)
cell, asp, uh, uw = fit(lettuce(leaf["w3"], (.46, .72, .22), pale_base=.75, frill=18))
put("butter_a", cell, 2, 0, asp, uh, uw)
cell, asp, uh, uw = fit(lettuce(leaf["w1"], (.42, .7, .2), pale_base=.7, frill=18))
put("butter_b", cell, 2, 1, asp, uh, uw)
cell, asp, uh, uw = fit(lettuce(leaf["n2"], (.36, .5, .16), pale_base=.4, frill=12, red_edge=((.4, .06, .11), 95)))
put("oak_red", cell, 2, 2, asp, uh, uw)
cell, asp, uh, uw = fit(lettuce(leaf["d4"], (.44, .74, .2), pale_base=.5, frill=10))
put("oak_green", cell, 2, 3, asp, uh, uw)
for k, box in enumerate([(5, 15, 400, 372), (18, 438, 438, 818)]):
    tri = hsv_adjust(centred("shrub_sorrel_01", box), hue=-.01, sat=1.05, val=.9)
    tri[..., 3] = (tri[..., 3] > .5) * 1.0
    cell, asp, uh, uw = fit(tri[::-1] if k else tri)
    put(f"bean_leaf_{'ab'[k]}", cell, 3, k, asp, uh, uw)

# ------------------------------------------------------------------ procedural parts (row 3, cells 2 and 3 split 2x2)
S = C // 2


def disc(size, fn):
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    return fn((x + .5) / size * 2 - 1, (y + .5) / size * 2 - 1)


# scarlet runner-bean flower cluster (sorrel petals recoloured)
fl = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d, a = SRC["shrub_sorrel_01"]
for k, (bx0, by0, bx1, by1) in enumerate([(585, 438, 687, 578), (693, 500, 826, 616), (482, 562, 633, 666), (565, 632, 668, 781), (675, 627, 822, 744)]):
    p = np.dstack([d[by0 * 2:by1 * 2, bx0 * 2:bx1 * 2], a[by0 * 2:by1 * 2, bx0 * 2:bx1 * 2]])
    p = tint(p, (.95, .16, .08), .9)
    im = Image.fromarray((np.clip(p, 0, 1) * 255).astype(np.uint8), "RGBA").resize((70, 80)).rotate(k * 67, expand=True)
    for j in range(2):
        fl.alpha_composite(im, (int(40 + (k % 3) * 55 + j * 30), int(30 + (k // 3) * 90 + j * 70)))
cell = np.asarray(fl).astype(np.float32) / 255
put("flower", cell, 3, 2, 1., 1., 1., sub=(0, 0, 2))
# bean pod (vertical, slightly curved)
pod = disc(S, lambda x, y: np.clip(1 - np.abs(x + .12 * (y ** 2)) / (.16 * np.sqrt(np.clip(1 - y * y, 0, 1)) + 1e-3), 0, 1))
podc = np.dstack([.3 + .1 * pod, .55 + .15 * pod, .14 + .05 * pod, (pod > 0) * 1.])
put("pod", podc, 3, 2, .3, 1., .3, sub=(0, 1, 2))
# seedling: two cotyledons on a short stem (front view, base at the bottom centre)
sd = Image.new("RGBA", (S, S), (0, 0, 0, 0)); dr = ImageDraw.Draw(sd)
dr.line([(S // 2, S - 8), (S // 2, S // 2)], fill=(150, 170, 90, 255), width=10)
for side in (-1, 1):
    cx, cy = S // 2 + side * 62, S // 2 - 26
    dr.ellipse([cx - 66, cy - 34, cx + 66, cy + 34], fill=(108, 170, 52, 255))
    dr.ellipse([cx - 50, cy - 24, cx + 40, cy + 16], fill=(132, 190, 70, 255))
sd = sd.filter(ImageFilter.GaussianBlur(1.2))
put("seedling", np.asarray(sd).astype(np.float32) / 255, 3, 2, 1., 1., 1., sub=(1, 0, 2))
# stem strip (tube texture, u around, v along): green with fine lengthwise fibres
fib = ndimage.gaussian_filter1d(rng.normal(0, 1, (S, S)), 14, axis=0)
g = .5 + .12 * fib
put("stem", np.dstack([.3 * g + .08, .5 * g + .12, .2 * g + .04, np.ones((S, S))]), 3, 2, 1., 1., 1., sub=(1, 1, 2))
# tomato fruit (planar top projection): red / red-orange / orange / green, calyx star at the centre
Q = S // 2
for k, col in enumerate([(.78, .09, .05), (.86, .24, .07), (.9, .45, .1), (.42, .62, .2)]):
    f = disc(Q, lambda x, y: x * x + y * y)
    rgb = np.array(col)[None, None] * (1 - .25 * f[..., None]) + rng.normal(0, .015, (Q, Q, 1))
    ang = np.arctan2(*np.mgrid[-1:1:Q * 1j, -1:1:Q * 1j]); rr = np.sqrt(f)
    star = (rr < .16 + .1 * np.cos(5 * ang)) & (rr < .26)
    rgb[star] = (.2, .35, .1)
    i, j = divmod(k, 2)
    atlas[3 * C + i * Q:3 * C + (i + 1) * Q, 3 * C + j * Q:3 * C + (j + 1) * Q] = np.dstack([np.clip(rgb, 0, 1), np.ones((Q, Q))])
    u0 = (3 * C + j * Q) / N; v1 = 1 - (3 * C + i * Q) / N
    meta[f"fruit_{k}"] = dict(uv=[round(u0, 5), round(v1 - Q / N, 5), round(u0 + Q / N, 5), round(v1, 5)])
# microgreens: dense top-view mat of tiny leaves on a pale substrate (tiling)
mg = Image.new("RGBA", (S, S), (190, 175, 140, 255)); dr = ImageDraw.Draw(mg)
for _ in range(2600):
    x, y = rng.uniform(0, S, 2); a0 = rng.uniform(0, math.pi)
    g = rng.uniform(.75, 1.15); col = (int(95 * g), int(165 * g), int(55 * g), 255)
    if rng.random() < .15: col = (int(120 * g), int(60 * g), int(95 * g), 255)   # a few red amaranth
    for s in (-1, 1):
        cx, cy = x + s * 4 * math.cos(a0), y + s * 4 * math.sin(a0)
        dr.ellipse([cx - 4.5, cy - 3, cx + 4.5, cy + 3], fill=col)
mg = mg.filter(ImageFilter.GaussianBlur(.6))
put("microgreens", np.asarray(mg).astype(np.float32) / 255, 3, 3, 1., 1., 1., sub=(0, 1, 2))
# rockwool cube / net pot rim (top view): olive-grey fibres
rw = np.clip(.5 + rng.normal(0, .06, (S, S)), 0, 1)
rw = ndimage.gaussian_filter(rw, 1.2)
put("rockwool", np.dstack([rw * .9, rw * .86, rw * .66, np.ones((S, S))]), 3, 3, 1., 1., 1., sub=(1, 0, 2))
# twine / label area: pale hemp
tw = np.clip(.72 + rng.normal(0, .05, (S, S)), 0, 1)
tw = ndimage.gaussian_filter1d(tw, 6, axis=0)
put("twine", np.dstack([tw, tw * .93, tw * .74, np.ones((S, S))]), 3, 3, 1., 1., 1., sub=(1, 1, 2))

# ------------------------------------------------------------------ write atlas (+ bleed colour into transparent texels)
rgb = atlas[..., :3].copy(); al = atlas[..., 3]
solid = al > .5
idx = ndimage.distance_transform_edt(~solid, return_distances=False, return_indices=True)
rgb = rgb[idx[0], idx[1]]
Image.fromarray((np.dstack([rgb, al]) * 255).astype(np.uint8), "RGBA").save(OUT / "HY_CropAtlas.png")
# normal map (OpenGL) from luminance detail, gentle
lum = ndimage.gaussian_filter(rgb.mean(-1), 1.0)
gx = ndimage.sobel(lum, axis=1); gy = ndimage.sobel(lum, axis=0)
nz = np.ones_like(lum) / 6.0
n = np.dstack([-gx, gy, nz]); n /= np.linalg.norm(n, axis=-1, keepdims=True)
Image.fromarray(((n * .5 + .5) * 255).astype(np.uint8), "RGB").save(OUT / "HY_CropAtlas_Normal.png")
(OUT / "crop_atlas.json").write_text(json.dumps(meta, indent=1))

# ------------------------------------------------------------------ PVC channel white (u along the channel, v around the profile)
P = 512
v = np.linspace(0, 1, P)[:, None] * np.ones((1, P))
base = .86 + rng.normal(0, .012, (P, P))
streak = ndimage.gaussian_filter1d(rng.normal(0, 1, (P, P)), 30, axis=1)
base -= .035 * np.clip(streak, 0, None)
algae = np.exp(-((v - .12) / .05) ** 2) * (.5 + .5 * ndimage.gaussian_filter1d(rng.random((P, P)), 20, axis=1))
rgb = np.dstack([base, base, base * .97]) * (1 - .35 * algae[..., None]) + np.array([.25, .32, .14])[None, None] * .35 * algae[..., None]
Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)).save(OUT / "HY_PVC.png")

# ------------------------------------------------------------------ shade cloth (knitted, tiling 0.25 m, alpha)
T = 256
y, x = np.mgrid[0:T, 0:T].astype(np.float32)
knit = (np.sin(x / T * 2 * math.pi * 24 + np.sin(y / T * 2 * math.pi * 48) * 1.2) > -.72) & (np.sin(y / T * 2 * math.pi * 32) > -.8)
a = knit.astype(np.float32)
col = np.array([.1, .14, .08])
rgb = col[None, None] * (.85 + .3 * rng.random((T, T, 1)))
Image.fromarray((np.dstack([np.clip(rgb, 0, 1), a]) * 255).astype(np.uint8), "RGBA").save(OUT / "HY_ShadeCloth.png")

# ------------------------------------------------------------------ polycarbonate skin film: dust and condensation runs (u per bay, v 1/3 arch)
P = 1024
y, x = np.mgrid[0:P, 0:P].astype(np.float32) / P
dust = ndimage.gaussian_filter(rng.random((P, P)), 18)
dust = (dust - dust.min()) / (dust.max() - dust.min())
runs = np.zeros((P, P), np.float32)
for _ in range(260):
    cx = rng.uniform(0, P); ln = rng.uniform(.08, .5) * P; y0 = rng.uniform(0, P)
    ys = (np.arange(int(ln)) + y0).astype(int) % P
    xs = (cx + np.cumsum(rng.normal(0, .35, len(ys)))).astype(int) % P
    runs[ys, xs] = rng.uniform(.4, 1)
runs = ndimage.gaussian_filter(runs, (3, 1.2)) * 6
drops = (ndimage.gaussian_filter(rng.random((P, P)), 1.5) > .56).astype(np.float32) * .5
film = np.clip(.25 + .35 * dust + .45 * np.clip(runs, 0, 1) + .25 * drops, 0, 1)
rgb = np.dstack([.8 + .1 * dust, .82 + .08 * dust, .74 + .06 * dust])
Image.fromarray((np.dstack([np.clip(rgb, 0, 1), film]) * 255).astype(np.uint8), "RGBA").save(OUT / "HY_SkinFilm.png")
print("atlas cells:", len(meta))
