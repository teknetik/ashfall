#!/usr/bin/env python3
"""Berms ground V2 splats (1 Oct 2026). Run through the heavy wrapper:
    $O/heavy.sh uv run --with pillow --with numpy --with scipy python art/berms_road_20261001/make_splat.py [--check]

Writes Assets/AthenHill/Art/BermsRoad/Ground/BermsRoadSplat.png and BermsRoadSplat2.png (linear RGBA, 1024 x 2048 over
x -104..-60, z -54..48, the West Gate splat's rect, ~4.3 x 5 cm per texel), road.json (the smoothed road centreline,
widths, potholes; edge_stones.py reads it) and review/splat-preview.png.

Splat 1 keeps the West Gate channel meaning (R compacted road gravel, G sand, B crust, A 1 - compaction), which the
footstep map reads. Everything off the road is the West Gate pass's own painting, reproduced exactly from its generator
(art/west_gate_20260926/make_ground_splat.py, same seeds; `--check` compares the reproduction with the shipped PNG). The
road is repainted along a smoothed centreline:
  * two compacted wheel paths (darker, smoother, 2-4 cm ruts, a fainter second pair from wider vehicles) with
    washboard corrugation on the braking stretches before the bends;
  * a loose-gravel crown between them and graded windrows of loose gravel along both shoulders (raised 2-4 cm,
    broken by gaps), sand caught in the lee (west) of the windrows;
  * a few sand-filled potholes in the wheel paths, side tracks where vehicles pulled off to the scrap heaps;
  * wandering, noise-broken edges into the verge.
Splat 2: R loose gravel (road crown/windrows and desert-pavement lag patches on open flats), G relief height
(0.5 = flat, +-0.1 m over the full range, matching the material's _ReliefDepth 0.2), B the share of R that is
varnished lag (darker) rather than fresh road gravel, A the smoothed ground slope x2 (Gaussian 2.5 m over the ground mesh; the shader's layer masks read it).
"""
import json, math, sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage

HERE = Path(__file__).resolve().parent
WG = HERE.parent / "west_gate_20260926"
ASSETS = HERE.parents[1] / "unity/AthenHill/Assets/AthenHill"
OUT1 = ASSETS / "Art/BermsRoad/Ground/BermsRoadSplat.png"
OUT2 = ASSETS / "Art/BermsRoad/Ground/BermsRoadSplat2.png"
OLD = ASSETS / "Art/WestGate/Ground/BermsGroundSplat.png"
X0, X1, Z0, Z1 = -104.0, -60.0, -54.0, 48.0
W, H = 1024, 2048
DX, DZ = (X1 - X0) / W, (Z1 - Z0) / H
RELIEF = .2            # metres over the full 0..1 range of splat 2 G (material _ReliefDepth)
lay = json.loads((WG / "layout.json").read_text())
grid = json.loads((WG / "berms-ground-grid.json").read_text())
survey = json.loads((HERE / "survey.json").read_text())
xs = (np.arange(W) + .5) / W * (X1 - X0) + X0
zs = (np.arange(H) + .5) / H * (Z1 - Z0) + Z0
X, Z = np.meshgrid(xs, zs)          # row 0 = z0 (Unity UV v = 0 is the bottom row -> flip when saving)


# ============================================================ West Gate generator (verbatim logic, same seeds)
def fbm(scale, octaves=5, seed=0):
    r = np.random.default_rng(seed); out = np.zeros((H, W), np.float32); amp = 1; tot = 0
    for o in range(octaves):
        s = max(2, int(scale * 2 ** o))
        g = r.random((s * 2 + 1, s + 1)).astype(np.float32)
        out += np.asarray(Image.fromarray((g * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32) / 255 * amp
        tot += amp; amp *= .5
    return out / tot


hg = {(round(p[0]), round(p[2])): p[1] for p in grid}
gx = np.arange(int(X0), int(X1) + 1); gz = np.arange(int(Z0), int(Z1) + 1)
Hm = np.array([[hg.get((x, z), -1.5) for x in gx] for z in gz], np.float32)
hmap = np.asarray(Image.fromarray(Hm).resize((W, H), Image.BILINEAR), np.float32)


def box_blur(a, r):
    k = 2 * r + 1; pad = np.pad(a, r, mode="edge"); c = np.cumsum(np.cumsum(pad, 0), 1)
    c = np.pad(c, ((1, 0), (1, 0)))
    return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)


blur = np.asarray(Image.fromarray(box_blur(Hm, 6).astype(np.float32)).resize((W, H), Image.BILINEAR), np.float32)
hollow = np.clip((blur - hmap) * 1.5 - .12, 0, 1)
dzdx = np.gradient(hmap, axis=1) / DX; dzdz = np.gradient(hmap, axis=0) / DZ
slope_wg = np.clip(np.hypot(dzdx, dzdz), 0, 2)


def seg_dist(px, pz, a, b):
    ax, az = a; bx, bz = b; dx, dz = bx - ax, bz - az; L2 = dx * dx + dz * dz
    t = np.clip(((px - ax) * dx + (pz - az) * dz) / L2, 0, 1)
    return np.hypot(px - (ax + t * dx), pz - (az + t * dz)), t


def poly_dist(pts):
    best = np.full((H, W), 1e9, np.float32); along = np.zeros((H, W), np.float32); acc = 0
    side = np.zeros((H, W), np.float32)
    for a, b in zip(pts[:-1], pts[1:]):
        d, t = seg_dist(X, Z, a, b); L = math.dist(a, b)
        m = d < best; best = np.where(m, d, best); along = np.where(m, acc + t * L, along)
        sx, sz = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        cross = (X - a[0]) * sz - (Z - a[1]) * sx
        side = np.where(m, cross, side)
        acc += L
    return best, along, side


n_edge = fbm(10, 5, 1); n_med = fbm(28, 4, 2); n_fine = fbm(80, 3, 3); n_big = fbm(4, 4, 4)


def west_gate(road_r=None):
    """The West Gate splat. With road_r=None it reproduces the shipped PNG (old road included); with an array it
    paints everything except the old road (no old road gravel, ruts or crown sand) and uses road_r for the crust mask."""
    R = np.zeros((H, W), np.float32); G = np.zeros((H, W), np.float32); B = np.zeros((H, W), np.float32)
    K = np.zeros((H, W), np.float32)
    if road_r is None:
        road = lay["anchors"]["road"]
        d, along, side = poly_dist(road)
        half = np.interp(along, [0, 8, 20, 60, 90], [3.4, 3.0, 2.6, 2.3, 2.0])
        edge = half + (n_edge - .5) * 1.6 + (n_fine - .5) * .35
        R = np.clip((edge - d) / .9, 0, 1)
        for off in (-.9, .9):
            rut = np.exp(-((side - off - (n_med - .5) * .25) / .22) ** 2)
            K = np.maximum(K, rut * R * (.75 + .25 * n_fine))
        crown = np.exp(-(side / .45) ** 2) * R
        G = np.maximum(G, crown * .35 * (n_med > .45))
        Rc = R
    else:
        Rc = road_r

    def blob(cx, cz, rx, rz, strength, chan):
        q = ((X - cx) / rx) ** 2 + ((Z - cz) / rz) ** 2
        v = np.clip(1 - q, 0, 1) ** .7 * strength * (0.75 + .5 * n_med)
        chan[:] = np.maximum(chan, v)
    blob(-71.5, -3.5, 5.0, 1.8, .7, K); blob(-68.0, -5.2, 1.6, 1.8, .6, K); blob(-66.8, 7.8, 2.0, 1.6, .6, K)
    blob(-64.0, -4.0, 1.3, 1.2, .5, K); blob(-61.8, -1.8, 1.4, 1.4, .45, K); blob(-68.6, 6.6, 1.2, 1.0, .5, K)
    Gt = np.zeros((H, W), np.float32)
    blob(-71.5, -3.5, 5.0, 1.8, .55, Gt); blob(-66.8, 7.8, 2.0, 1.6, .45, Gt)
    G = np.maximum(G, Gt)
    for path in ([(-66.0, 2.8), (-66.6, 5.5), (-66.5, 7.3)], [(-69.5, -1.8), (-70.5, -3.2)], [(-67.2, -1.8), (-67.9, -4.6)], [(-63.0, -1.5), (-63.9, -3.6)]):
        pd, _, _ = poly_dist(path)
        K = np.maximum(K, np.clip(1 - pd / .5, 0, 1) * (.5 + .3 * n_fine))
    wallband = np.clip(1 - (-60.0 - X) / (1.4 + n_edge * 1.4), 0, 1) * ((Z < -2.8) | (Z > 5.2))
    G = np.maximum(G, wallband * .9)
    G = np.maximum(G, hollow * np.clip(1 - slope_wg * 2, 0, 1) * (n_med * .8 + .2))
    for it in lay["items"]:
        if it.get("drift", 0) <= 0: continue
        cx, cz, s = it["x"], it["z"], it["drift"]
        for dx, rx, rz, k in ((.5, .9, .8, .8), (-1.4, 2.2, .9, .6)):
            q = ((X - (cx + dx * s * 1.5)) / (rx * (1 + s))) ** 2 + ((Z - cz) / (rz * (1 + s))) ** 2
            G = np.maximum(G, np.clip(1 - q, 0, 1) ** 1.5 * k * np.clip(n_med * 1.6 - .3, 0, 1))
    G = np.maximum(G, np.clip((n_big - .6) * 3, 0, 1) * .7 * (1 - Rc) * np.clip(1 - slope_wg * 2.5, 0, 1))
    flat = np.clip(1 - slope_wg * 3, 0, 1)
    far = np.clip((np.hypot(X + 68, Z) - 14) / 8, 0, 1)
    B = np.maximum(B, np.clip((n_med - .62) * 3.5, 0, 1) * flat * .7 * (1 - Rc) * (1 - G) * far)
    ap = lay["anchors"]["apron"]
    inap = (X > ap["x0"] - .3) & (X < ap["x1"]) & (Z > ap["z0"] - .3) & (Z < ap["z1"] + .3)
    G = np.where(inap, np.maximum(G, .15), G)
    return R, G, B, K


def finish(R, G, B, K):
    tot = R + G + B; scale = np.where(tot > 1, 1 / np.maximum(tot, 1e-4), 1)
    return R * scale, G * scale, B * scale, 1 - np.clip(K, 0, 1) * .85


def to_png(chans):
    img = np.dstack(chans)[::-1]
    return (np.clip(img, 0, 1) * 255 + .5).astype(np.uint8)


if "--check" in sys.argv:
    ref = np.asarray(Image.open(OLD).convert("RGBA"), np.int16)
    rep = to_png(finish(*west_gate())).astype(np.int16)
    diff = np.abs(ref - rep)
    print("reproduction vs shipped splat: max diff per channel", diff.reshape(-1, 4).max(0), "mean", diff.reshape(-1, 4).mean(0).round(4))
    sys.exit(0)

# ============================================================ new road
rng = np.random.default_rng(1001)
road_pts = np.array(lay["anchors"]["road"], np.float64)


def catmull(pts, step=.2):
    """Centripetal-ish Catmull-Rom through the West Gate road points (bends become curves, ends kept)."""
    P = np.vstack([pts[0] * 2 - pts[1], pts, pts[-1] * 2 - pts[-2]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        n = max(2, int(np.linalg.norm(p2 - p1) / step))
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-2])
    return np.array(out)


C = catmull(road_pts)
seg = np.diff(C, axis=0); segL = np.linalg.norm(seg, axis=1)
S = np.concatenate([[0], np.cumsum(segL)])
T = np.vstack([seg / segL[:, None], seg[-1:] / segL[-1]])                    # tangent per centreline sample
L = S[-1]
# curvature (for the braking stretches before bends)
ang = np.unwrap(np.arctan2(T[:, 1], T[:, 0])); curv = np.abs(np.gradient(ang, S))

# nearest centreline sample per texel via a distance transform on the rasterised centreline
mask = np.ones((H, W), bool); idx_img = np.full((H, W), -1, np.int32)
ci = np.clip(((C[:, 0] - X0) / DX).astype(int), 0, W - 1); cj = np.clip(((C[:, 1] - Z0) / DZ).astype(int), 0, H - 1)
mask[cj, ci] = False; idx_img[cj, ci] = np.arange(len(C))
_, (nj, ni) = ndimage.distance_transform_edt(mask, sampling=(DZ, DX), return_indices=True)
near = idx_img[nj, ni]
cx, cz = C[near, 0], C[near, 1]; tx, tz = T[near, 0], T[near, 1]
along = S[near]
side = ((X - cx) * tz - (Z - cz) * tx).astype(np.float32)                     # + = right of travel (gate -> depot)
dist = np.abs(side)
beyond = ((X - cx) * tx + (Z - cz) * tz)                                        # past the ends
dist = np.where((near == 0) & (beyond < 0), np.hypot(dist, beyond), dist)
dist = np.where((near == len(C) - 1) & (beyond > 0), np.hypot(dist, beyond), dist).astype(np.float32)
excess = np.where(near == 0, np.maximum(-beyond, 0), 0) + np.where(near == len(C) - 1, np.maximum(beyond, 0), 0)
endcap = np.clip(1 - excess / 1.2, 0, 1).astype(np.float32)                 # painted road features stop at the ends

half = np.interp(along, [0, 6, 14, 40, L - 10, L], [3.2, 3.0, 2.7, 2.6, 2.4, 2.2]).astype(np.float32)
edgeN = (n_edge - .5) * 1.1 + (n_fine - .5) * .3
edgeW = half + edgeN
inroad = np.clip((edgeW - dist) / .7, 0, 1)                                     # soft, wandering edge
band = endcap                                                                   # windrows/lee sand: same caps
n_rut = fbm(40, 3, 11); n_gap = fbm(18, 3, 12); n_sp = fbm(140, 2, 13); n_lag = fbm(7, 4, 21)

relief = np.zeros((H, W), np.float32)
Kr = np.zeros((H, W), np.float32); loose = np.zeros((H, W), np.float32); Gr = np.zeros((H, W), np.float32)
# wheel paths: main pair at +-0.95 m (wander a little), a fainter, wider pair at +-1.2 m
wobble = (n_med - .5) * .3
for off, depth, width, k in ((-.95, .035, .26, .85), (.95, .035, .26, .85), (-1.22, .015, .2, .45), (1.22, .015, .2, .45)):
    u = (side - off - wobble) / width
    prof = np.exp(-u * u)
    relief -= depth * prof * inroad * (.7 + .5 * n_rut)
    Kr = np.maximum(Kr, prof * inroad * k * (.75 + .25 * n_fine))
# tyre-pushed lips beside each main rut (fines squeezed out)
for off in (-.95, .95):
    u = (np.abs(side - off - wobble) - .36) / .1
    relief += .008 * np.exp(-u * u) * inroad
# washboard on the braking stretches before bends (wavelength ~0.75 m, 6 mm), in the wheel paths only
brake = np.interp(along, S, ndimage.maximum_filter1d(curv, size=int(9 / .2)))   # within ~9 m ahead/behind a bend
brake = np.clip(brake * 6, 0, 1).astype(np.float32)
paths = np.clip(np.exp(-((dist - .95) / .35) ** 2), 0, 1)
relief += .006 * np.sin(along * 2 * np.pi / .75 + n_med * 2) * paths * brake * inroad
# crown: loose gravel and a slight hump
crown = np.exp(-(side / .5) ** 2) * inroad
relief += .012 * crown
loose = np.maximum(loose, crown * np.clip(.35 + (n_rut - .5) * 1.2, 0, 1))
Gr = np.maximum(Gr, crown * .3 * (n_med > .5))
# graded windrows along both shoulders, broken by gaps where vehicles and boots crossed
for sgn in (-1, 1):
    u = (side * sgn - (edgeW - .15)) / .42
    wr = np.exp(-u * u) * np.clip((n_gap - .32) * 4, 0, 1) * np.clip(along / 4, 0, 1) * band
    relief += .035 * wr * (.7 + .6 * n_fine)
    loose = np.maximum(loose, wr * .85)
    # sand caught in the lee of the windrow (wind from the east: west side, i.e. the side facing -x)
    lee = np.exp(-((side * sgn - (edgeW + .45)) / .35) ** 2) * np.clip((n_gap - .32) * 4, 0, 1) * band
    westward = np.clip(-(sgn * tz) * 2 + .3, 0, 1)        # right-hand normal (tz, -tx): its x = tz*sgn; west if negative
    Gr = np.maximum(Gr, lee * .55 * westward * (n_med * .8 + .4))
# potholes in the wheel paths (sand-filled)
pots = []
for s0 in np.linspace(10, L - 6, 9) + rng.uniform(-3, 3, 9):
    k = int(np.searchsorted(S, s0)); sgn = rng.choice([-1, 1]); r = rng.uniform(.35, .65)
    p = C[k] + np.array([T[k, 1], -T[k, 0]]) * sgn * .95 * rng.uniform(.8, 1.15)
    pots.append({"x": round(float(p[0]), 2), "z": round(float(p[1]), 2), "r": round(r, 2)})
    q = ((X - p[0]) ** 2 + (Z - p[1]) ** 2) / (r * r)
    bowl = np.clip(1 - q, 0, 1)
    relief -= .045 * bowl ** .8
    relief += .01 * np.exp(-((np.sqrt(q) - 1.05) / .18) ** 2)     # broken lip
    Gr = np.maximum(Gr, np.clip(bowl * 1.6, 0, 1) * .8)
# side tracks where vehicles pulled off: to the first-contact scrap heap and the roadside mound heap
spurs = [[(-85.0, -15.5), (-86.6, -16.6), (-87.6, -17.1)], [(-82.6, -27.0), (-80.6, -27.1), (-79.6, -27.0)]]
for sp in spurs:
    pd, al, sd = poly_dist(sp)
    for off in (-.9, .9):
        u = (sd - off) / .24
        tr = np.exp(-u * u) * np.clip(1 - al / 4.5, 0, 1) * (pd < 2.2)
        Kr = np.maximum(Kr, tr * .55); relief -= .012 * tr
# the gate approach: the old West Gate road ran here too; keep the gravel where it was wider than the new edge
Rnew = inroad * (1 - .25 * crown)
Rnew = np.clip(Rnew, 0, 1)

# ============================================================ assemble splat 1
R0, G0, B0, K0 = west_gate(road_r=Rnew)
R1 = Rnew
G1 = np.maximum(G0 * (1 - .8 * inroad), Gr)                                    # old sand mostly cleared off the road
B1 = B0 * (1 - inroad)
K1 = np.maximum(K0, Kr)
S1 = finish(R1, G1, B1, K1)

# ============================================================ splat 2
v = np.array(survey["ground"]["vertices"], np.float64)
gxs = np.unique(v[:, 0]); gzs = np.unique(v[:, 2])
Hg = np.full((len(gzs), len(gxs)), np.nan); Hg[np.searchsorted(gzs, v[:, 2]), np.searchsorted(gxs, v[:, 0])] = v[:, 1]
Hs = ndimage.gaussian_filter(Hg, 2.5, mode="nearest")
gzd, gxd = np.gradient(Hs, gzs, gxs)
ny = 1 / np.sqrt(1 + gxd ** 2 + gzd ** 2)
slope_s = 1 - ny
# bilinear to the texel grid
fx = np.interp(X, gxs, np.arange(len(gxs))); fz = np.interp(Z, gzs, np.arange(len(gzs)))
slope_t = ndimage.map_coordinates(slope_s, [fz, fx], order=1, mode="nearest").astype(np.float32)
height_t = ndimage.map_coordinates(Hg, [fz, fx], order=1, mode="nearest").astype(np.float32)

# keep-out for natural features: gameplay markers, colliders (props, structures), the road and the trodden areas
keep = np.zeros((H, W), bool)
for c in survey["colliders"]:
    if c["trigger"]: continue
    mn, mx = c["min"], c["max"]
    if mx[0] - mn[0] > 30 or mx[2] - mn[2] > 30: continue
    keep |= (X > mn[0] - .8) & (X < mx[0] + .8) & (Z > mn[2] - .8) & (Z < mx[2] + .8)
for m in survey["markers"]:
    keep |= (X - m["pos"][0]) ** 2 + (Z - m["pos"][2]) ** 2 < 3.0 ** 2
keepf = ndimage.gaussian_filter(keep.astype(np.float32), 8)
open_ground = np.clip(1 - keepf * 2, 0, 1) * (1 - np.clip(inroad * 2 + Kr, 0, 1)) * np.clip(1 - K0 * 2, 0, 1)
# desert-pavement lag: wind-winnowed gravel on open flats, not on sand
lag = np.clip((n_lag - .53) * 4.0, 0, 1) * np.clip(.6 + (n_sp - .5) * 1.5, 0, 1) * np.clip(1 - slope_t * 12, 0, 1) * open_ground * (1 - np.clip(G1 * 2, 0, 1))
loose2 = np.maximum(loose, lag * .8)
G2 = np.clip(.5 + relief / RELIEF, 0, 1)
A2 = np.clip(slope_t * 2, 0, 1)
lagshare = np.where(loose2 > 1e-3, np.clip(lag * .8 / np.maximum(loose2, 1e-3), 0, 1), 0) * (loose2 > 1e-3)
S2 = (loose2, G2, lagshare, A2)

OUT1.parent.mkdir(parents=True, exist_ok=True)
Image.fromarray(to_png(S1), "RGBA").save(OUT1)
Image.fromarray(to_png(S2), "RGBA").save(OUT2)

# ============================================================ records and preview
(HERE / "road.json").write_text(json.dumps({
    "what": "Smoothed Berms road centreline (Catmull-Rom through the West Gate road anchors), sampled every ~0.2 m; half width per sample; potholes; pull-off spurs.",
    "length_m": round(float(L), 2),
    "centreline": [[round(float(a), 3), round(float(b), 3)] for a, b in C[::5]],
    "along": [round(float(s), 2) for s in S[::5]],
    "half_width": [round(float(h), 3) for h in np.interp(S[::5], [0, 6, 14, 40, L - 10, L], [3.2, 3.0, 2.7, 2.6, 2.4, 2.2])],
    "potholes": pots, "spurs": spurs, "relief_range_m": RELIEF,
}, indent=1))
stats = {"road_texels": int((R1 > .5).sum()), "sand_texels": int((G1 > .5).sum()), "crust_texels": int((B1 > .5).sum()),
         "loose_texels": int((loose2 > .5).sum()), "lag_texels": int((lag > .5).sum()),
         "relief_min_m": round(float(relief.min()), 3), "relief_max_m": round(float(relief.max()), 3),
         "slope_smoothed_max": round(float(slope_t.max()), 3)}
(HERE / "splat.json").write_text(json.dumps(stats, indent=1))
print(stats)
prev = np.dstack([S1[0], S1[1], S1[2]])[::-1]
prev2 = np.dstack([S2[0], (S2[1] - .5) * 4 + .5, S2[2]])[::-1]
canvas = np.concatenate([prev, np.ones((H, 8, 3)), prev2, np.ones((H, 8, 3)), np.dstack([1 - S1[3]] * 3)[::-1]], 1)
(HERE / "review").mkdir(exist_ok=True)
Image.fromarray((np.clip(canvas, 0, 1) * 255).astype(np.uint8)).resize((3 * 512 + 8, 1024)).save(HERE / "review/splat-preview.png")
print("splats written", OUT1, OUT2)
