"""Original deterministic PBR maps for the Tool Exchange display vignette and shutter hardware (29 Sep 2026, task t_3751e0fd).

    env -i HOME=$HOME PATH=/usr/bin:/bin /usr/bin/python3 make_te_textures.py [TE_Name ...]

numpy only (no PIL/scipy). Helper functions (noise, painted steel, bare steel, rubber, twine, paper, sand) are the ones
written for the Basic General counter package (t_84b69b7e) and copied unchanged into te_textures_base.py; everything else
in this file is new. Conventions match the project's Ward maps:
  *_BaseColor.png   sRGB albedo (RGB, or RGBA for the glass)
  *_Normal.png      tangent-space OpenGL (+Y up), linear
  *_MetalSmooth.png R metallic, A smoothness (1 - roughness), G/B zero  (URP Lit metallic-gloss map)
Tiling maps are 2048x2048. Unique maps are laid out at a constant 2048 px/m so wear sits in true physical position:
  TE_ToolBoard   3008 x 2880  (1.46875 x 1.40625 m)  perforated tool board with painted shadow-board outlines
  TE_ShutterFit  4096 x 1024  (2.0 x 0.5 m)          shutter handle plates, lock box and hasp atlas, directional hand wear
  TE_DisplayGlass 2806 x 2703 (two 0.685 x 1.32 m panes side by side) clear glass with dust film, rain streaks, wipe arcs
No lettering is painted anywhere: outlines, tally-free paper and wear only.
"""
import sys, json, hashlib
from pathlib import Path
import numpy as np
import te_textures_base as B
from te_textures_base import (fbm, vnoise, blur, stretch, normal_from_height, scratches, pack_metal_smooth, srgb8, emit, write_png,
                              painted, bare_steel, rubber, twine, sand, paper, N, OUT, MANIFEST)
import te_spec as S

B.VARIANTS.clear()
B.VARIANTS.update({'TE_BareSteel': {'Brass': (1.12, .86, .40)}})
ONLY = set(a for a in sys.argv[1:])


def want(k):
    return not ONLY or k in ONLY


PPM = S.PPM


# ------------------------------------------------------------------ new tiling materials
def forged_steel(name, seed, tile_m, note):
    """Drop-forged, oil-blackened tool steel: dark satin scale with bright worn ridges and shallow pitting."""
    rng = np.random.default_rng(seed)
    brushed = vnoise(rng, N, N, 1300, 5) * .6 + vnoise(rng, N, N, 2100, 3) * .4
    scale = fbm(rng, N, N, [40, 150, 520], [1, .8, .6])
    lowf = fbm(rng, N, N, [5, 17], [1, .6])
    pit = stretch(vnoise(rng, N, N, 300, 300), .90, .975)
    oil = stretch(fbm(rng, N, N, [7, 26, 90], [1, .8, .6]), .52, .75)
    bright = stretch(fbm(rng, N, N, [9, 33, 140], [1, .8, .6]), .60, .78) * (0.5 + .5 * brushed)
    sc = np.clip(scratches(rng, N, N, 320, 380, 0.0, 0.10, 0.9), 0, 1)
    dark = np.array((.155, .16, .175), np.float32)[None, None, :] * (0.78 + .44 * scale[..., None]) * (0.92 + .16 * lowf[..., None])
    steel = np.array((.50, .51, .53), np.float32)[None, None, :] * (0.86 + .28 * brushed[..., None])
    c = dark * (1 - oil[..., None] * .35)
    c = c * (1 - bright[..., None] * .75) + steel * bright[..., None] * .75
    c = c * (1 - sc[..., None] * .5) + steel * sc[..., None] * .5
    c = c * (1 - pit[..., None] * .45)
    h = (brushed - .5) * .0025 + (scale - .5) * .002 - pit * .004 - sc * .0015
    metal = np.clip(.72 + bright * .25 - pit * .5, 0, 1)
    smooth_v = .34 + oil * .18 + bright * .32 + (brushed - .5) * .14 - pit * .2
    emit(name, srgb8(c), normal_from_height(h, 150), pack_metal_smooth(metal, smooth_v), tile_m, note)


def timber(name, seed, tile_m, note, tone=(.43, .29, .17), polish=.25):
    """Air-dried hardwood (ash/oak): grain runs along U. Oil-darkened, palm-polished patches, open pores, hairline checks."""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:N, 0:N].astype(np.float32) / N
    warp = fbm(rng, N, N, [3, 9, 30], [1, .6, .3])
    ring = .5 + .5 * np.sin((y * 26 + warp * 5.5) * 2 * np.pi)
    late = ring ** 2.2
    pores = stretch(vnoise(rng, N, N, 1500, 6), .72, .95) * (0.4 + .6 * late)
    fibre = vnoise(rng, N, N, 1900, 4) * .6 + vnoise(rng, N, N, 800, 3) * .4
    oil = stretch(fbm(rng, N, N, [4, 13, 45], [1, .8, .6]), .50, .72)
    check = stretch(vnoise(rng, N, N, 40, 3), .955, .99) * stretch(vnoise(rng, N, N, 6, 2), .5, .8)
    pol = stretch(fbm(rng, N, N, [3, 8, 24], [1, .7, .5]), .55, .72) * polish
    t = np.array(tone, np.float32)[None, None, :]
    c = t * (0.70 + .30 * (1 - late[..., None])) * (0.88 + .24 * fibre[..., None])
    c = c * (1 - pores[..., None] * .35) * (1 - oil[..., None] * .30) * (1 - check[..., None] * .55)
    c = c * (1 - pol[..., None] * .10)
    h = -pores * .004 + late * .0022 + (fibre - .5) * .0015 - check * .004
    smooth_v = .20 + pol * .45 + oil * .10 - pores * .10
    emit(name, srgb8(c), normal_from_height(h, 120), pack_metal_smooth(np.zeros((N, N), np.float32), smooth_v), tile_m, note)


def whetstone(name, seed, tile_m, note):
    """Fine sharpening stone (novaculite-like): grey-green, tight grain, dark oil/slurry stain and a dished, polished working face."""
    rng = np.random.default_rng(seed)
    g = fbm(rng, N, N, [700, 1500, 2400], [1, 1, .8])
    lowf = fbm(rng, N, N, [4, 13, 45], [1, .7, .5])
    vein = stretch(vnoise(rng, N, N, 14, 3), .62, .8)
    slurry = stretch(fbm(rng, N, N, [5, 18, 70], [1, .8, .6], aniso=3), .50, .72)
    swirl = stretch(fbm(rng, N, N, [3, 9], [1, .6]), .5, .8)
    sc = np.clip(scratches(rng, N, N, 200, 300, 0.3, .6, 1), 0, 1)
    c = np.array((.42, .43, .39), np.float32)[None, None, :] * (0.82 + .30 * g[..., None]) * (0.9 + .2 * lowf[..., None])
    c = c * (1 - vein[..., None] * .18) + np.array((.30, .28, .22), np.float32)[None, None, :] * vein[..., None] * .18
    c = c * (1 - slurry[..., None] * .42) + np.array((.10, .095, .085), np.float32)[None, None, :] * slurry[..., None] * .42
    c = c * (1 - sc[..., None] * .18)
    h = (g - .5) * .005 - sc * .0015 + (lowf - .5) * .004
    smooth_v = .16 + swirl * .30 - slurry * .10 + (g - .5) * .08
    emit(name, srgb8(c), normal_from_height(h, 110), pack_metal_smooth(np.zeros((N, N), np.float32), smooth_v), tile_m, note)


# ------------------------------------------------------------------ polygon helpers for the board
def poly_field(poly_px_list, y0, y1, x0, x1, X0, Y0, H):
    """Signed distance (metres, negative inside) of the union of polygons in A-space metres, evaluated on the pixel window
    [y0:y1, x0:x1] of a unique map whose left edge is A-x X0, bottom is A-y Y0 and height H px (row 0 = top)."""
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    PX = X0 + (xx + .5) / PPM
    PY = Y0 + (H - 1 - yy + .5) / PPM
    dist = np.full(PX.shape, 9.0, np.float32)
    inside = np.zeros(PX.shape, bool)
    for poly in poly_px_list:
        ins = np.zeros(PX.shape, bool)
        n = len(poly)
        for i in range(n):
            (ax, ay), (bx, by) = poly[i], poly[(i + 1) % n]
            dx, dy = bx - ax, by - ay
            L2 = dx * dx + dy * dy
            t = np.clip(((PX - ax) * dx + (PY - ay) * dy) / L2, 0, 1)
            d = np.hypot(PX - (ax + t * dx), PY - (ay + t * dy))
            dist = np.minimum(dist, d)
            cond = ((ay > PY) != (by > PY)) & (PX < (bx - ax) * (PY - ay) / (by - ay + 1e-12) + ax)
            ins ^= cond
        inside |= ins
    return np.where(inside, -dist, dist), inside


def tool_board():
    W, H = 3072, 2908                     # exactly the 1.500 x 1.420 m opening at 2048 px/m
    X0 = -2.90
    Y0 = 0.78
    rng = np.random.default_rng(929301)
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    Xm = X0 + (x + .5) / PPM
    Ym = Y0 + (H - 1 - y + .5) / PPM
    mott = fbm(rng, H, W, [4, 14, 60, 240], [1, .8, .6, .4])
    grain = fbm(rng, H, W, [500, 1000, 1800], [1, 1, .8])
    lowf = fbm(rng, H, W, [3, 8], [1, .6])
    # ---- base: dusty sage-green enamel on hardboard, sun-faded at the top, greasier and darker toward the bench
    height01 = (Ym - Y0) / (H / PPM)
    paint = np.array((.44, .49, .40), np.float32)[None, None, :] * (0.88 + .22 * mott[..., None]) * (0.985 + .03 * grain[..., None])
    paint = paint * (1 + .06 * (height01[..., None] - .5)) * (0.95 + .10 * lowf[..., None])
    core = np.array((.30, .21, .12), np.float32)[None, None, :] * (0.8 + .4 * grain[..., None])          # hardboard
    steel = np.array((.50, .50, .50), np.float32)[None, None, :]
    # ---- perforations: 25 mm grid, 6.5 mm holes, chamfered and chipped
    P = S.HOLE_PITCH
    fx = ((Xm - X0) / P) % 1.0 - .5
    fy = ((Ym - Y0) / P) % 1.0 - .5
    r = np.hypot(fx, fy) * P
    hole = np.clip((S.HOLE_D / 2 - r) / .0004, 0, 1)
    rim = np.clip(1 - np.abs(r - (S.HOLE_D / 2 + .0012)) / .0012, 0, 1) * (1 - hole)
    cell_id = (np.floor((Xm - X0) / P) * 73.0 + np.floor((Ym - Y0) / P) * 151.0).astype(np.int64)
    rnd = ((cell_id * 2654435761) % 1000).astype(np.float32) / 1000.0
    chipped = (rnd > .74) * rim
    # ---- tool outlines (painted) + missing-saw ghost
    outline = np.zeros((H, W), np.float32)
    inside_any = np.zeros((H, W), np.float32)
    ghost = np.zeros((H, W), np.float32)
    for name, spec in S.PLACEMENT.items():
        polys = [S.place(pl, spec['origin'], spec['deg']) for pl in spec['polys']]
        xs = [p[0] for pl in polys for p in pl]; ys = [p[1] for pl in polys for p in pl]
        pad = .035
        xa = max(0, int((min(xs) - pad - X0) * PPM)); xb = min(W, int((max(xs) + pad - X0) * PPM) + 1)
        ya = max(0, int(H - 1 - (max(ys) + pad - Y0) * PPM)); yb = min(H, int(H - 1 - (min(ys) - pad - Y0) * PPM) + 1)
        sd, ins = poly_field(polys, ya, yb, xa, xb, X0, Y0, H)
        wob = (vnoise(rng, yb - ya, xb - xa, 22, 22) - .5) * .0016 + (vnoise(rng, yb - ya, xb - xa, 90, 90) - .5) * .0005   # brush wobble
        d = sd + wob
        aa = .0005
        band = np.clip((d - S.OUTLINE_GAP) / aa, 0, 1) * np.clip((S.OUTLINE_GAP + S.OUTLINE_W - d) / aa, 0, 1)
        outline[ya:yb, xa:xb] = np.maximum(outline[ya:yb, xa:xb], band)
        inside_any[ya:yb, xa:xb] = np.maximum(inside_any[ya:yb, xa:xb], (d < S.OUTLINE_GAP).astype(np.float32))
        if not spec['drawn']:
            ghost[ya:yb, xa:xb] = np.maximum(ghost[ya:yb, xa:xb], np.clip((S.OUTLINE_GAP + S.OUTLINE_W * .5 - d) / .004, 0, 1))
    # outline paint is patchy: rubbed at hand height / near the grips, chalky and cracked elsewhere
    outline_wear = stretch(fbm(rng, H, W, [12, 45, 160, 600], [1, .8, .6, .4]), .30, .72)
    outline *= (1 - .60 * outline_wear)
    # ---- wear and dirt
    hand = np.zeros((H, W), np.float32)             # rubbed paint where hands take the tools down (handle ends, below the rail)
    for (cx, cy, rx, ry, a) in [(-2.660, 1.900, .075, .085, 0.2), (-2.360, 1.905, .07, .08, -0.1), (-1.98, 1.72, .09, .05, 0.1),
                                (-2.05, 1.31, .10, .05, 0.0), (-1.80, 1.31, .10, .045, .1)]:
        u = ((Xm - cx) * np.cos(a) + (Ym - cy) * np.sin(a)) / rx
        v = (-(Xm - cx) * np.sin(a) + (Ym - cy) * np.cos(a)) / ry
        hand = np.maximum(hand, np.exp(-(u * u + v * v) * 2.0))
    hand *= (0.5 + .8 * fbm(rng, H, W, [10, 40, 160], [1, .8, .6]))
    down_streak = stretch(vnoise(rng, H, W, 6, 500), .55, .9) * stretch(fbm(rng, H, W, [4, 12], [1, .6]), .4, .7)    # vertical rub bands
    dust = np.clip(stretch(.42 - (Ym - Y0) / (H / PPM), 0, .42) * (0.5 + .7 * fbm(rng, H, W, [8, 30, 120], [1, .8, .6])), 0, 1)   # settled from above onto the bench zone
    dust_top = stretch((Ym - Y0) / (H / PPM), .88, 1.0) * .45 * (0.6 + .5 * fbm(rng, H, W, [16, 60], [1, .8]))
    dust = np.clip(dust + dust_top, 0, 1) * (1 - .75 * outline)
    chips = stretch(.55 * fbm(rng, H, W, [30, 90, 300], [1, .8, .6]) + .45 * fbm(rng, H, W, [500, 900], [1, 1]), .93, .95)
    peel_edge = np.clip(blur(chips, 3) * 3, 0, 1)
    oilw = stretch(fbm(rng, H, W, [6, 22, 80], [1, .8, .6]), .62, .78) * stretch(.6 - (Ym - Y0) / (H / PPM), 0, .5)
    # rust weeps below each peg hole row (pegs are bare steel)
    weeps = np.zeros((H, W), np.float32)
    for (px_, py_) in [(-2.660, 1.905), (-2.360, 2.02), (-2.02, 1.665), (-1.94, 1.665), (-1.80, 1.665), (-2.05, 1.276), (-1.62, 1.276)]:
        cx_ = (px_ - X0) * PPM; cy_ = (H - 1) - (py_ - Y0) * PPM
        L = (.03 + rng.random() * .08) * PPM
        yy = np.arange(H, dtype=np.float32)[:, None]; xx = np.arange(W, dtype=np.float32)[None, :]
        weeps = np.maximum(weeps, np.exp(-((xx - cx_) / 3.0) ** 2) * ((yy > cy_) & (yy < cy_ + L)) * (1 - (yy - cy_) / L) * .5)
    c = paint
    c = c * (1 - down_streak[..., None] * .06) + steel * .0
    c = c * (1 - hand[..., None] * .26) + (paint * 1.12) * hand[..., None] * .26                       # polished/lightened by hands
    c = c * (1 - oilw[..., None] * .22) + np.array((.12, .10, .07), np.float32)[None, None, :] * oilw[..., None] * .22
    c = c * (1 - weeps[..., None] * .5) + np.array((.30, .16, .085), np.float32)[None, None, :] * weeps[..., None] * .5
    c = c * (1 - peel_edge[..., None]) + core * peel_edge[..., None] * 1.0
    cream = np.array((.74, .67, .50), np.float32)[None, None, :] * (0.88 + .20 * grain[..., None])
    c = c * (1 - outline[..., None]) + cream * outline[..., None]
    c = np.where((ghost > .5)[..., None], c * np.array((1.16, 1.14, 1.10), np.float32)[None, None, :], c)   # cleaner, unfaded paint where the saw hung
    sandc = np.array((.60, .50, .36), np.float32)[None, None, :]
    c = c * (1 - dust[..., None] * .42) + sandc * dust[..., None] * .42
    # holes: bare dark; chipped rims show hardboard
    c = c * (1 - rim[..., None] * .10)
    c = np.where((chipped[..., None] > .3), core * .9, c)
    c = c * (1 - hole[..., None]) + np.array((.012, .010, .008), np.float32)[None, None, :] * hole[..., None]
    h = (grain - .5) * .0008 - peel_edge * .0006 + outline * .0004 - hole * .010 - rim * .0014 + dust * .0009
    smooth_v = (.30 + .10 * mott) * (1 - hand * .0) + hand * .20 - dust * .22 - oilw * .0
    smooth_v = smooth_v * (1 - peel_edge * .6) + .06 * peel_edge * .6
    smooth_v = smooth_v * (1 - hole) + .02 * hole
    metal = np.zeros((H, W), np.float32)
    emit('TE_ToolBoard', srgb8(c), normal_from_height(h, 220), pack_metal_smooth(metal, smooth_v), None,
         'Unique 3072x2908 at 2048 px/m. A-space x = -2.90 + px/2048; y = 0.78 + (2907-row)/2048; u=(x+2.90)/1.5, v=(y-0.78)/1.42. 25 mm perforation grid, painted outlines of the three hung tools plus the missing handsaw (cleaner ghost), hand rub, dust and hardboard chips.', PPM)
    return dict(X0=X0, Y0=Y0, W=W, H=H)


# ------------------------------------------------------------------ shutter fittings atlas
ATLAS = {                     # zone: (x0 m, y0 m, width m, height m) on the 2.0 x 0.5 m atlas, y measured up from the bottom
    'HandlePlate_L': (0.00, 0.00, 0.40, 0.16),
    'HandlePlate_R': (0.42, 0.00, 0.40, 0.16),
    'LockBox':       (0.84, 0.00, 0.26, 0.20),
    'Hasp':          (1.12, 0.00, 0.14, 0.26),
    'Escutcheon':    (1.28, 0.00, 0.10, 0.10),
    'KickPlate':     (0.00, 0.20, 1.20, 0.10),
}


def shutter_atlas():
    W, H = 4096, 1024
    rng = np.random.default_rng(929302)
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    Xm = (x + .5) / PPM
    Ym = (H - 1 - y + .5) / PPM
    mott = fbm(rng, H, W, [4, 14, 60, 240], [1, .8, .6, .4])
    grain = fbm(rng, H, W, [500, 1000, 1800], [1, 1, .8])
    zone = np.full((H, W), -1)
    zx0 = np.zeros((H, W), np.float32); zy0 = np.zeros((H, W), np.float32); zw = np.ones((H, W), np.float32); zh = np.ones((H, W), np.float32)
    for i, (k, (ax, ay, w, h)) in enumerate(ATLAS.items()):
        m = (Xm >= ax) & (Xm < ax + w) & (Ym >= ay) & (Ym < ay + h)
        zone[m] = i; zx0[m] = ax; zy0[m] = ay; zw[m] = w; zh[m] = h
    lx = np.where(zone >= 0, Xm - zx0, 0); ly = np.where(zone >= 0, Ym - zy0, 0)          # local metres inside a zone
    inz = zone >= 0
    paint = np.array((.16, .17, .16), np.float32)[None, None, :] * (0.82 + .36 * mott[..., None]) * (0.985 + .03 * grain[..., None])
    steel = np.array((.36, .355, .34), np.float32)[None, None, :] * (0.85 + .3 * grain[..., None])
    oxide = np.array((.30, .16, .085), np.float32)[None, None, :]
    brassc = np.array((.66, .50, .22), np.float32)[None, None, :]
    edge = np.minimum(np.minimum(lx, zw - lx), np.minimum(ly, zh - ly))
    ew = stretch(.006 - edge, 0, .006) * (0.2 + 1.0 * fbm(rng, H, W, [30, 120, 400], [1, .8, .6]) ** 2)
    ew = stretch(ew, .25, .8) * .9
    wear = np.zeros((H, W), np.float32)
    zid = list(ATLAS.keys())

    def zmask(k):
        return zone == zid.index(k)

    def blobz(k, cx, cy, rx, ry, a=0.0):
        ax, ay, w, h = ATLAS[k]
        u = ((Xm - ax - cx) * np.cos(a) + (Ym - ay - cy) * np.sin(a)) / rx
        v = (-(Xm - ax - cx) * np.sin(a) + (Ym - ay - cy) * np.cos(a)) / ry
        return np.exp(-(u * u + v * v) * 2.0) * zmask(k)
    # handle plates: paint rubbed off by fingertips above the bar (lifting hands travel upward), a palm-heel smear at the lower right,
    # a dark grease band where the wrist rests on the plate top. Left plate is used far more than the right one.
    for k, s in (('HandlePlate_L', 1.0), ('HandlePlate_R', .55)):
        wear = np.maximum(wear, blobz(k, .20, .105, .115, .030, 0.0) * s)               # the grasp
        wear = np.maximum(wear, blobz(k, .16, .13, .055, .022, 0.5) * s * .8)
        wear = np.maximum(wear, blobz(k, .26, .04, .05, .02, -.3) * s * .55)             # thumb knock
    wear = np.maximum(wear, blobz('LockBox', .13, .105, .05, .05) * .55)
    wear = np.maximum(wear, blobz('Escutcheon', .05, .05, .03, .03) * 1.0)
    wear = np.maximum(wear, blobz('Hasp', .07, .18, .035, .045) * .9)
    wear = np.maximum(wear, blobz('Hasp', .07, .06, .03, .03) * .5)
    kick = np.zeros((H, W), np.float32)
    ax, ay, w, h = ATLAS['KickPlate']
    kick = zmask('KickPlate') * stretch(fbm(rng, H, W, [40, 160, 500], [1, .8, .6], aniso=8), .40, .75) * (stretch(.05 - (Ym - ay), -.05, .05) * .8 + .3)
    wear = np.clip(wear * (0.55 + .9 * fbm(rng, H, W, [16, 60, 240], [1, .8, .6], aniso=3)), 0, 1)
    wear = stretch(wear, .28, .9) * .95
    sc = np.clip(scratches(rng, H, W, 260, 110, 0.05, .4, 1.2), 0, 1) * (0.2 + .8 * blur(wear, 4) * 3)
    grease = stretch(fbm(rng, H, W, [5, 20, 80], [1, .8, .6], aniso=2), .58, .78) * stretch(.09 - np.abs(Ym - 0.0), -.5, .5)
    rustm = stretch(fbm(rng, H, W, [8, 30, 120], [1, .8, .6]), .68, .80) * .8
    dust = np.clip(.9 * stretch(fbm(rng, H, W, [10, 60, 220], [1, .8, .6]), .55, .8), 0, 1) * (1 - wear)
    # rust weeps from bolt heads (bolt rows sit 12 mm in from the plate ends)
    weeps = np.zeros((H, W), np.float32)
    for k in ('HandlePlate_L', 'HandlePlate_R'):
        ax, ay, w, h = ATLAS[k]
        for bx in (.03, w - .03):
            for by in (.03, h - .03):
                cx_ = (ax + bx) * PPM; cy_ = (H - 1) - (ay + by) * PPM
                yy = np.arange(H, dtype=np.float32)[:, None]; xx = np.arange(W, dtype=np.float32)[None, :]
                L = (.03 + rng.random() * .06) * PPM
                weeps = np.maximum(weeps, np.exp(-((xx - cx_) / 3.0) ** 2) * ((yy > cy_) & (yy < cy_ + L)) * (1 - (yy - cy_) / L) * .55)
    c = paint
    c = c * (1 - rustm[..., None] * .4) + oxide * rustm[..., None] * .4
    c = c * (1 - weeps[..., None] * .6) + oxide * weeps[..., None] * .6
    c = c * (1 - grease[..., None] * .5)
    c = c * (1 - sc[..., None] * .3) + steel * sc[..., None] * .3
    c = c * (1 - ew[..., None] * .85) + steel * ew[..., None] * .85
    c = c * (1 - wear[..., None]) + steel * (0.95 + .1 * grain[..., None]) * wear[..., None]
    c = c * (1 - kick[..., None] * .8) + steel * kick[..., None] * .8
    # brass escutcheon ring
    esc = zmask('Escutcheon')
    d = np.hypot(Xm - ATLAS['Escutcheon'][0] - .05, Ym - ATLAS['Escutcheon'][1] - .05)
    disc = (d < .042) * esc
    c = np.where(disc[..., None], brassc * (0.8 + .3 * grain[..., None]) * (1 - .3 * grease[..., None]), c)
    keyhole = ((d < .0045) | ((np.abs(Xm - ATLAS['Escutcheon'][0] - .05) < .0018) & (Ym - ATLAS['Escutcheon'][1] - .05 < 0) & (Ym - ATLAS['Escutcheon'][1] - .05 > -.014))) & esc
    c = np.where(keyhole[..., None], np.array((.01, .01, .01), np.float32)[None, None, :], c)
    sandc = np.array((.60, .49, .34), np.float32)[None, None, :]
    c = c * (1 - dust[..., None] * .25) + sandc * dust[..., None] * .25
    c = np.where(inz[..., None], c, np.array((.10, .10, .10), np.float32)[None, None, :])
    h_ = (grain - .5) * .0010 - ew * .0012 - sc * .0012 - wear * .0007 + rustm * .0012 + weeps * .0010 + dust * .0012 - keyhole * .004 + (disc * .0012)
    metal = np.clip(ew * .95 + sc * .5 + wear * .95 + kick * .8 + .05, 0, 1) * (1 - rustm * .9) * (1 - dust * .7)
    metal = np.where(disc, .95, metal)
    smooth_v = (.42 - .18 * mott) * (1 - wear) + .72 * wear
    smooth_v = smooth_v * (1 - grease * .3) + .55 * grease * .3
    smooth_v = smooth_v * (1 - rustm) + .12 * rustm
    smooth_v = smooth_v * (1 - dust * .8) + .06 * dust * .8
    smooth_v = np.where(disc, .70, smooth_v)
    emit('TE_ShutterFit', srgb8(c), normal_from_height(h_, 200), pack_metal_smooth(metal, smooth_v), None,
         'Unique 4096x1024 at 2048 px/m atlas (2.0 x 0.5 m). Zones in make_te_textures.ATLAS: two handle plates, lock box, hasp, brass escutcheon, kick strip. Directional hand wear: fingertip grasp, thumb knock, left plate used ~2x the right.', PPM)
    return {k: dict(x0=v[0], y0=v[1], w=v[2], h=v[3]) for k, v in ATLAS.items()}


# ------------------------------------------------------------------ display glass (unique, alpha)
def display_glass():
    """Two panes 0.685 x 1.32 m side by side, 2048 px/m. A = opacity: clean glass ~9 %, dust film, edge grime and rain streaks up to ~55 %.
    RGB = the film colour (dark teal-black where clean, sand where dusty). MetalSmooth A = smoothness (clean .92, dusty .30)."""
    pw, ph = 1403, 2703
    W, H = pw * 2, ph
    rng = np.random.default_rng(929303)
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    px = (x % pw) / PPM                # local metres within a pane (0 = left)
    py = (H - 1 - y + .5) / PPM        # 0 = bottom
    pane = (x // pw).astype(np.int32)
    Wm, Hm = pw / PPM, ph / PPM
    top = py / Hm
    edge = np.minimum(np.minimum(px, Wm - px), np.minimum(py, Hm - py))
    edge_g = stretch(.055 - edge, 0, .055) * (0.4 + 1.0 * fbm(rng, H, W, [20, 80, 300], [1, .8, .6])) ** 1.2
    film = stretch(fbm(rng, H, W, [4, 14, 60, 250], [1, .8, .6, .4]), .35, .80) * .28 + .05
    settle = stretch(.55 - top, 0, .55) ** 1.3 * (0.5 + .7 * fbm(rng, H, W, [6, 24, 100], [1, .8, .6]))
    streak_src = stretch(vnoise(rng, H, W, 3, 700), .60, .95)
    streaks = blur(np.repeat(streak_src[:1], H, 0) * 0 + streak_src, 1.2) * stretch(fbm(rng, H, W, [3, 9, 40], [1, .7, .5]), .40, .75) * (0.4 + .6 * top)
    # cloth wipe arcs: clean sweeps starting on the left and rising (a keeper wipes the display, not the whole pane)
    wipe = np.zeros((H, W), np.float32)
    for (cx, cy, r0, r1, a0, a1, pn) in [(.05, .30, .30, .42, -.2, 1.15, 0), (.10, .18, .50, .60, -.15, .9, 1), (.62, .34, .28, .36, 1.9, 3.2, 1)]:
        dx = px - cx; dy = py - cy
        r = np.hypot(dx, dy); a = np.arctan2(dy, dx)
        band = np.clip(1 - np.abs(r - (r0 + r1) / 2) / ((r1 - r0) / 2), 0, 1) * ((a > a0) & (a < a1)) * (pane == pn)
        wipe = np.maximum(wipe, blur(band, 6) * 2.0)
    wipe = np.clip(wipe * (0.5 + .8 * fbm(rng, H, W, [10, 40, 160], [1, .8, .6])), 0, 1)
    finger = np.zeros((H, W), np.float32)
    for (cx, cy, pn) in [(.22, .80, 0), (.24, .79, 0), (.26, .78, 0), (.55, 1.02, 1), (.57, 1.01, 1), (.59, 1.00, 1)]:
        d = np.hypot(px - cx, py - cy) * (pane == pn) + 9 * (pane != pn)
        finger = np.maximum(finger, np.exp(-(d / .010) ** 2) * .5)
    dirt = np.clip(edge_g * .95 + settle * .55 + streaks * .30 + film, 0, 1)
    dirt = np.clip(dirt * (1 - .8 * wipe) + finger * .5, 0, 1)
    alpha = .09 + .46 * dirt
    tint = np.array((.05, .085, .09), np.float32)[None, None, :]
    dustc = np.array((.55, .46, .34), np.float32)[None, None, :] * (0.85 + .3 * fbm(rng, H, W, [40, 200], [1, .8])[..., None])
    rgb = tint * (1 - dirt[..., None]) + dustc * dirt[..., None]
    rgba = np.dstack((srgb8(rgb), np.clip(alpha * 255 + .5, 0, 255).astype(np.uint8)))
    h_ = dirt * .0010 - wipe * .0004 + (fbm(rng, H, W, [500, 1000], [1, 1]) - .5) * .0002
    smooth_v = .92 * (1 - dirt) + .28 * dirt
    emit('TE_DisplayGlass', rgba, normal_from_height(h_, 100), pack_metal_smooth(np.zeros((H, W), np.float32), smooth_v), None,
         'Unique 2806x2703 RGBA at 2048 px/m; left pane u 0..0.5, right pane u 0.5..1. Alpha = opacity (URP transparent/alpha blend). Dust film, edge grime, rain streaks, wipe arcs, fingertip prints. No text.', PPM)


if __name__ == '__main__':
    layout = {}
    if want('TE_ToolPaintRed'):
        painted('TE_ToolPaintRed', 929311, (.55, .10, .075), .40, .10, .30, 160, .50,
                'Enamel-red pipe-wrench paint over cast steel: chipped to bare metal, rust halos, scratches.', orange_peel=.6)
    if want('TE_CastIron'):
        painted('TE_CastIron', 929312, (.15, .145, .14), .70, .05, .35, 120, .40,
                'Dark cast-iron/black-painted frames (clamps, vice jaws): gritty, rust bloom on chips.', orange_peel=1.0)
    if want('TE_ToolSteel'):
        forged_steel('TE_ToolSteel', 929313, .50, 'Oil-blackened drop-forged tool steel with bright worn ridges, pitting.')
    if want('TE_BareSteel'):
        bare_steel('TE_BareSteel', 929314, .50, 'Brushed bare steel: pegs, screws, file, cutting edges. Brass variant for the padlock body.')
    if want('TE_Timber'):
        timber('TE_Timber', 929315, .50, 'Oiled hardwood: grain along U. Rail, bench top, hammer haft, file handle, alcove lining.', tone=(.42, .28, .165), polish=.30)
    if want('TE_TimberPolished'):
        timber('TE_TimberPolished', 929316, .50, 'Palm-polished ash: hammer haft grip and file handle where hands hold them. Darker, satin.', tone=(.36, .23, .13), polish=.75)
    if want('TE_Rubber'):
        rubber('TE_Rubber', 929317, .30, 'Dipped rubber grips on bolt-cutter handles: fine grain, crazing, dust bloom.')
    if want('TE_Twine'):
        twine('TE_Twine', 929318, .10, '3-ply twine: repair-tag strings, hasp loop.')
    if want('TE_Paper'):
        paper('TE_Paper', 929319, .35, 'Kraft repair-tag paper, rule bands and stamp ring, NO lettering.')
    if want('TE_Sand'):
        sand('TE_Sand', 929320, .50, 'Fine dust for local drifts on the bench and rail top.')
    if want('TE_ShutterPaint'):
        painted('TE_ShutterPaint', 929321, (.20, .21, .20), .55, .07, .55, 220, .60,
                'Dark satin painted structural steel for the shutter guide caps, bolts, straps (matches the existing shutter slat tone).', orange_peel=.8)
    if want('TE_Stone'):
        whetstone('TE_Stone', 929322, .25, 'Fine grey-green sharpening stone with oil slurry stain and polished dished face.')
    if want('TE_ToolBoard'):
        layout['board'] = tool_board()
    if want('TE_ShutterFit'):
        layout['atlas'] = shutter_atlas()
    if want('TE_DisplayGlass'):
        display_glass()
    old = json.loads((OUT / 'manifest.json').read_text())['materials'] if ONLY and (OUT / 'manifest.json').exists() else []
    done = {m['material'] for m in MANIFEST}
    MANIFEST.extend(m for m in old if m['material'] not in done)
    prev_layout = json.loads((OUT / 'layout.json').read_text()) if ONLY and (OUT / 'layout.json').exists() else {}
    prev_layout.update(layout)
    (OUT / 'layout.json').write_text(json.dumps(prev_layout, indent=2))
    (OUT / 'manifest.json').write_text(json.dumps({
        'author': 'Original deterministic Ward material synthesis (numpy), Tool Exchange display and shutter hardware',
        'date': '2026-09-29', 'licence': 'Project original; no third-party source imagery; no generative-model output',
        'seed': 'per-material seeds 929301-929321 in make_te_textures.py',
        'normal': 'OpenGL +Y tangent space', 'packed': 'R metallic; A smoothness; G/B zero',
        'colourSpace': 'BaseColor sRGB; Normal + MetalSmooth linear', 'materials': MANIFEST}, indent=2))
    print('done', len(MANIFEST), 'materials')
