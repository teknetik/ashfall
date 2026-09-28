#!/usr/bin/env python3
"""Paint the Berms ground splat (RGBA, linear) from layout.json and the saved ground grid.
R compacted road gravel, G wind-deposited sand, B cracked crust (open flats only), A compaction
(1 = loose, lower = darker packed ground: tyre ruts, trodden areas, footpaths).
Covers x -104..-60, z -54..48 at 1024 x 2048 (~4.3 x 5 cm per texel)."""
import json, math
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / "unity/AthenHill/Assets/AthenHill/Art/WestGate/Ground/BermsGroundSplat.png"
X0, X1, Z0, Z1 = -104.0, -60.0, -54.0, 48.0
W, H = 1024, 2048
lay = json.loads((HERE / "layout.json").read_text())
grid = json.loads((HERE / "berms-ground-grid.json").read_text())
xs = (np.arange(W) + .5) / W * (X1 - X0) + X0
zs = (np.arange(H) + .5) / H * (Z1 - Z0) + Z0
X, Z = np.meshgrid(xs, zs)          # row 0 = z0 (Unity UV v=0 is the bottom row -> flip when saving)
rng = np.random.default_rng(26)


def fbm(scale, octaves=5, seed=0):
    r = np.random.default_rng(seed); out = np.zeros((H, W), np.float32); amp = 1; tot = 0
    for o in range(octaves):
        s = max(2, int(scale * 2 ** o))
        g = r.random((s * 2 + 1, s + 1)).astype(np.float32)
        out += np.asarray(Image.fromarray((g * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32) / 255 * amp
        tot += amp; amp *= .5
    return out / tot


# ground height / slope on the texel grid (bilinear from the 1 m mesh grid)
hg = {(round(p[0]), round(p[2])): p[1] for p in grid}
gx = np.arange(int(X0), int(X1) + 1); gz = np.arange(int(Z0), int(Z1) + 1)
Hm = np.array([[hg.get((x, z), -1.5) for x in gx] for z in gz], np.float32)
hmap = np.asarray(Image.fromarray(Hm).resize((W, H), Image.BILINEAR), np.float32)
def box_blur(a, r):
    k = 2 * r + 1; pad = np.pad(a, r, mode="edge"); c = np.cumsum(np.cumsum(pad, 0), 1)
    c = np.pad(c, ((1, 0), (1, 0)))
    return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)
blur = np.asarray(Image.fromarray(box_blur(Hm, 6).astype(np.float32)).resize((W, H), Image.BILINEAR), np.float32)
hollow = np.clip((blur - hmap) * 1.5 - .12, 0, 1)        # broad low spots collect sand
dzdx = np.gradient(hmap, axis=1) / ((X1 - X0) / W); dzdz = np.gradient(hmap, axis=0) / ((Z1 - Z0) / H)
slope = np.clip(np.hypot(dzdx, dzdz), 0, 2)


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
        # signed side for ruts
        sx, sz = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        cross = (X - a[0]) * sz - (Z - a[1]) * sx
        side = np.where(m, cross, side)
        acc += L
    return best, along, side


n_edge = fbm(10, 5, 1); n_med = fbm(28, 4, 2); n_fine = fbm(80, 3, 3); n_big = fbm(4, 4, 4)
R = np.zeros((H, W), np.float32); G = np.zeros((H, W), np.float32); B = np.zeros((H, W), np.float32)
K = np.zeros((H, W), np.float32)   # compaction amount (stored as A = 1 - K)

# --- road: compacted gravel track, width narrows toward the depot; wandering edges
road = lay["anchors"]["road"]
d, along, side = poly_dist(road)
half = np.interp(along, [0, 8, 20, 60, 90], [3.4, 3.0, 2.6, 2.3, 2.0])
edge = half + (n_edge - .5) * 1.6 + (n_fine - .5) * .35
R = np.clip((edge - d) / .9, 0, 1)
# tyre ruts: two compacted, darker tracks either side of the centre line
for off in (-.9, .9):
    rut = np.exp(-((side - off - (n_med - .5) * .25) / .22) ** 2)
    K = np.maximum(K, rut * R * (.75 + .25 * n_fine))
# centre crown collects loose sand
crown = np.exp(-(side / .45) ** 2) * R
G = np.maximum(G, crown * .35 * (n_med > .45))

# --- trodden ground around the post / board / range and footpaths
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

# --- sand: along the wall base (not in the gate mouth), in hollows, lee of objects (west/south-west drift)
wallband = np.clip(1 - (-60.0 - X) / (1.4 + n_edge * 1.4), 0, 1) * ((Z < -2.8) | (Z > 5.2))
G = np.maximum(G, wallband * .9)
G = np.maximum(G, hollow * np.clip(1 - slope * 2, 0, 1) * (n_med * .8 + .2))
for it in lay["items"]:
    if it.get("drift", 0) <= 0: continue
    cx, cz, s = it["x"], it["z"], it["drift"]
    # drift tail to the lee (wind from the east, sand piles on the upwind face and trails west)
    # upwind apron (east face) and a longer lee tail to the west, broken up by noise
    for dx, rx, rz, k in ((.5, .9, .8, .8), (-1.4, 2.2, .9, .6)):
        q = ((X - (cx + dx * s * 1.5)) / (rx * (1 + s))) ** 2 + ((Z - cz) / (rz * (1 + s))) ** 2
        G = np.maximum(G, np.clip(1 - q, 0, 1) ** 1.5 * k * np.clip(n_med * 1.6 - .3, 0, 1))
# wind ripples: broad sand sheets on the open basin
G = np.maximum(G, np.clip((n_big - .6) * 3, 0, 1) * .7 * (1 - R) * np.clip(1 - slope * 2.5, 0, 1))
# --- crust: flat open floor away from slopes, patchy
flat = np.clip(1 - slope * 3, 0, 1)
far = np.clip((np.hypot(X + 68, Z) - 14) / 8, 0, 1)   # keep the cracked crust away from the outpost
B = np.maximum(B, np.clip((n_med - .62) * 3.5, 0, 1) * flat * .7 * (1 - R) * (1 - G) * far)
# keep the concrete apron footprint free (it has its own mesh)
ap = lay["anchors"]["apron"]
inap = (X > ap["x0"] - .3) & (X < ap["x1"]) & (Z > ap["z0"] - .3) & (Z < ap["z1"] + .3)
G = np.where(inap, np.maximum(G, .15), G)
# normalise so R+G+B <= 1 (base fills the rest)
tot = R + G + B; scale = np.where(tot > 1, 1 / np.maximum(tot, 1e-4), 1)
R, G, B = R * scale, G * scale, B * scale
img = np.dstack([R, G, B, 1 - np.clip(K, 0, 1) * .85])
img = img[::-1]   # PIL row 0 is the top (v = 1); our row 0 is z0 (v = 0)
Image.fromarray((np.clip(img, 0, 1) * 255 + .5).astype(np.uint8), "RGBA").save(OUT)
prev = (np.clip(np.dstack([R, G, B])[::-1], 0, 1) * 255).astype(np.uint8)
Image.fromarray(prev).resize((512, 1024)).save(HERE / "ground-splat-preview.png")
print("splat written", OUT)
