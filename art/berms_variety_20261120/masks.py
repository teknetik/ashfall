#!/usr/bin/env python3
"""Region masks for the Outer Berms ground (20 Nov 2026) -> Unity textures + footstep map.

Writes (2048 x 2048 over x -572..-60, z -256..256, 0.25 m per texel, row 0 = south in Unity terms):
  unity/AthenHill/Assets/AthenHill/Art/BermsVariety/Ground/BermsVarietySplatA.png  R clay pan, G hardpan, B wind sand, A gravel fan
  unity/AthenHill/Assets/AthenHill/Art/BermsVariety/Ground/BermsVarietySplatB.png  R varnish, G relief (0.5 flat, +-_VarReliefDepth),
                                                                                 B scorch (> 0.62 glass), A wheel track
  footsteps.json     256 x 256 surface map at 2 m (FootSurface: 0 stone, 1 sand, 2 gravel) for FootstepAudio
  work/regions_preview.png, work/regions_stats.json

What decides each region (all from the expansion heightfield plus features.json):
  wind sand   the lee (ENE side) of anything higher upwind (mesa, knoll, butte, ridges, dunes, the berm lines), hollows,
              broad sand sheets at 100-200 m, dunes and wash banks
  gravel fan  below rock and steep ground (fans out to ~40 m), the mountain foot band and desert-pavement lag on
              high, stable flats; the far, old part of a fan and the pavement carry desert varnish (dark)
  clay pan    closed, flat low hollows (crisp edges, sand fringe), and dried silt in the wash channels
  hardpan     patchy flats in between (packed, darker), at a 60-150 m scale
  washes      braided gravel bars and silt channels in the two dry washes, sand on the banks
  tracks      two-rut Warden trails (sites.json routes), the braided Karaveen trail, old haul-droid treads, Post sentinel
              wheel loops: packed, with ruts in the relief channel, sand-covered in patches
  craters     bowls in the relief channel, blast scorch with radial rays, glassed centres on energy impacts, ejecta gravel
Every weight fades to zero within 4-18 m of the playable edge and 12-30 m of the old Berms ground, so the tiles meet the
basin and the old ground with the V2 look. Run: $O/heavy.sh uv run --with numpy --with scipy --with pillow python masks.py
"""
import base64, json, math
import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree
from scipy.special import erf
from PIL import Image
from bv_common import Field, HERE, ART_OUT, RX0, RZ0, RSIZE, OLD

RES = 2048
TX = RSIZE / RES                       # 0.25 m per texel
RELIEF_RANGE = 0.8                     # metres per 0.5 of the G channel (material _VarReliefDepth)
F = Field()
FEAT = json.loads((HERE / 'features.json').read_text())
WIND = np.array(FEAT['wind'], float)
rng = np.random.default_rng(1120)

c = (np.arange(RES) + 0.5) * TX
X, Z = np.meshgrid(RX0 + c, RZ0 + c)           # [j (z), i (x)]


def ss(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)


def field_at(arr, x=X, z=Z, order=1):
    return ndimage.map_coordinates(arr, [(z - F.oz) / F.cell, (x - F.ox) / F.cell], order=order, mode='nearest').astype(np.float32)


def noise(scale_m, seed, aniso=None):
    """Smooth value-like noise in 0..1 with features about scale_m across (Gaussian-filtered white noise, uniformised)."""
    r = np.random.default_rng(seed)
    cell = scale_m / 4.0
    n = int(math.ceil(RSIZE / cell)) + 8
    g = ndimage.gaussian_filter(r.normal(size=(n, n)), 1.6, mode='wrap')
    g = (g - g.mean()) / g.std()
    zz = (Z - RZ0) / cell + 4; xx = (X - RX0) / cell + 4
    v = ndimage.map_coordinates(g, [zz, xx], order=3, mode='wrap')
    return (0.5 * (1 + erf(v / math.sqrt(2)))).astype(np.float32)


# ------------------------------------------------------------------ base terrain fields (1 m), feature heights
j0, i0 = int(RZ0 - F.oz), int(RX0 - F.ox)
W1 = int(RSIZE) + 1
H1 = F.H[j0 - 64:j0 + W1 + 64, i0 - 64:i0 + W1 + 64].copy()      # 1 m window with a 64 m margin for the lee march
X1, Z1 = np.meshgrid(RX0 - 64 + np.arange(H1.shape[1]), RZ0 - 64 + np.arange(H1.shape[0]))
feat_h = np.zeros_like(H1)


def poly_raster(pts, Xg, Zg, step=0.5):
    """Distance from grid points to a polyline (dense resample + KD tree), and index of the nearest dense point."""
    P = np.asarray(pts, float)
    dense = [P[0]]
    for a, b in zip(P[:-1], P[1:]):
        n = max(1, int(np.linalg.norm(b - a) / step))
        for t in np.linspace(0, 1, n + 1)[1:]: dense.append(a + (b - a) * t)
    dense = np.array(dense)
    tree = cKDTree(dense)
    d, k = tree.query(np.stack([Xg.ravel(), Zg.ravel()], 1), distance_upper_bound=40)
    k = np.minimum(k, len(dense) - 1)
    return d.reshape(Xg.shape), k.reshape(Xg.shape), dense


for e in FEAT['earthworks']:
    for seg in e['segments']:
        d, _, _ = poly_raster(seg, X1, Z1)
        t = np.clip(d / (e['w'] * 0.5), 0, 1)
        feat_h = np.maximum(feat_h, e['h'] * (1 - ss(0.25, 1.0, t)))
for du in FEAT['dunes']:
    d, _, _ = poly_raster(du['pts'], X1, Z1)
    t = np.clip(d / (du['w'] * 0.5), 0, 1)
    feat_h = np.maximum(feat_h, du['h'] * (1 - ss(0.0, 1.0, t)))
for l in FEAT['ledges']:
    d = np.hypot(X1 - l['x'], Z1 - l['z'])
    feat_h = np.maximum(feat_h, l['h'] * (1 - ss(l['width'] * 0.35, l['length'] * 0.5, d)))
Haug = H1 + feat_h * 0.45          # man-made and small features shelter less far than the landforms

# lee shelter: steepest upwind horizon (tan) over 3..70 m, ignoring the general rise of the floor
shelter = np.full(H1.shape, -1.0)
for s in np.arange(3, 47, 2.0):
    sx, sz = -WIND[0] * s, -WIND[1] * s
    up = ndimage.shift(Haug, (-sz, -sx), order=1, mode='nearest')     # value at p - wind*s
    shelter = np.maximum(shelter, (up - Haug) / s - 0.025)
gz1, gx1 = np.gradient(ndimage.gaussian_filter(H1, 1.0))
slope1 = np.degrees(np.arctan(np.hypot(gx1, gz1)))
rel1 = H1 - ndimage.gaussian_filter(H1, 18)
rockmask = (F.rocks[j0 - 64:j0 + W1 + 64, i0 - 64:i0 + W1 + 64] > 0.8) | (slope1 > 24)
drock1 = ndimage.distance_transform_edt(~rockmask)


def up(a):
    return ndimage.map_coordinates(a, [(Z - (RZ0 - 64)), (X - (RX0 - 64))], order=1, mode='nearest').astype(np.float32)


SHEL = up(shelter); SLOPE = up(slope1); REL = up(ndimage.gaussian_filter(rel1, 1.5)); DROCK = up(drock1); FEATH = up(feat_h)
DIN = field_at(F.d_in)
x0o, x1o, z0o, z1o = OLD
DOLD = np.hypot(np.maximum(np.maximum(x0o - X, 0), X - x1o), np.maximum(np.maximum(z0o - Z, 0), Z - z1o))
FADE = ss(4, 18, DIN) * ss(12, 30, DOLD)

n12, n20, n30 = noise(12, 1), noise(20, 2), noise(30, 3)
n60, n80, n100, n150, n120b = noise(60, 4), noise(80, 5), noise(100, 6), noise(160, 7), noise(120, 8)
n6 = noise(6, 9)

# ------------------------------------------------------------------ natural regions
lee = ss(0.11, 0.28, SHEL) * ss(16, 8, SLOPE) * (0.55 + 0.45 * n30)
hollow = ss(-0.12, -0.45, REL) * ss(0.35, 0.65, n30)
sheet = ss(0.82, 0.93, n150) * 0.65
dune = ss(0.05, 0.4, FEATH) * 0          # set below from the dune footprints
wind = np.maximum.reduce([lee, hollow * 0.6, sheet])
wind = wind * (0.75 + 0.25 * n12)

fan = np.exp(-DROCK / 38.0) * ss(0.8, 2.6, SLOPE) * (0.55 + 0.45 * n20)
foot = (1 - ss(8, 48, DIN)) * 0.85 * (0.6 + 0.4 * n30)
pavement = ss(0.12, 0.55, REL) * ss(4.5, 2.0, SLOPE) * ss(0.4, 0.58, n100)
# varnished lag sheets at 100-250 m: the dark middle-distance tone the bowl was missing (fix round, 20 Nov)
vsheet = ss(0.66, 0.79, noise(140, 12)) * ss(5.0, 2.5, SLOPE) * (0.75 + 0.25 * n20)
pavement = np.maximum(pavement, vsheet)
gravel = np.maximum.reduce([fan, foot, pavement])
varnish = np.clip(ss(18, 70, DROCK) * ss(0.35, 0.7, n60) + pavement * 0.9 + foot * ss(0.5, 0.7, n80) * 0.6, 0, 1)

pan_raw = ss(-0.12, -0.36, REL + (n80 - 0.5) * 0.25) * ss(2.8, 1.0, SLOPE) * ss(0.36, 0.52, n60)
pan = ss(0.3, 0.42, ndimage.gaussian_filter(pan_raw, 6))
pan_fringe = np.clip(ndimage.gaussian_filter(ndimage.maximum_filter(pan, size=int(5 / TX)), 4) - pan, 0, 1)

hard = ss(0.4, 0.56, n120b) * ss(5.0, 2.0, SLOPE) * (0.7 + 0.3 * n20)

# ------------------------------------------------------------------ washes
wash_bed = np.zeros_like(X); bars = np.zeros_like(X); bank = np.zeros_like(X); wash_rel = np.zeros_like(X)
braid = noise(4, 11)
for w in FEAT['washes']:
    d, k, dense = poly_raster(w['pts'], X, Z, step=0.5)
    W = w['width']
    bed = 1 - ss(0.32 * W, 0.52 * W, d)
    # along-channel coordinate for elongated braided bars: arc length of the nearest dense point
    seglen = np.r_[0, np.cumsum(np.linalg.norm(np.diff(dense, axis=0), axis=1))]
    s = seglen[k]
    t = dense[np.minimum(k + 1, len(dense) - 1)] - dense[np.maximum(k - 1, 0)]
    t /= np.maximum(np.linalg.norm(t, axis=-1, keepdims=True), 1e-6)
    u = (X - dense[k][..., 0]) * -t[..., 1] + (Z - dense[k][..., 1]) * t[..., 0]
    bn = ndimage.map_coordinates(np.asarray(rng.random((64, 4096)), np.float32), [(u / 2.2) % 64, (s / 9.0) % 4096], order=1, mode='wrap')
    bn = ndimage.gaussian_filter(bn, 1.2)
    b = ss(0.52, 0.62, bn * 0.7 + braid * 0.3) * bed
    wash_bed = np.maximum(wash_bed, bed); bars = np.maximum(bars, b)
    bank = np.maximum(bank, ss(0.42 * W, 0.6 * W, d) * (1 - ss(0.7 * W, 1.05 * W, d)))
    wash_rel += np.where(bed > 0, b * 0.12 - (bed - b) * 0.04, 0)

# ------------------------------------------------------------------ tracks
track = np.zeros_like(X); relief = np.zeros_like(X)


def meander(pts, amp, wl, seed):
    P = np.asarray(pts, float)
    dense = [P[0]]
    for a, b in zip(P[:-1], P[1:]):
        n = max(1, int(np.linalg.norm(b - a) / 0.5))
        for tt in np.linspace(0, 1, n + 1)[1:]: dense.append(a + (b - a) * tt)
    D = np.array(dense)
    D = np.stack([ndimage.gaussian_filter1d(D[:, 0], 8, mode='nearest'), ndimage.gaussian_filter1d(D[:, 1], 8, mode='nearest')], 1)
    T = np.gradient(D, axis=0); T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-6)
    Nn = np.stack([-T[:, 1], T[:, 0]], 1)
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(D, axis=0), axis=1))]
    r = np.random.default_rng(seed); ph = r.uniform(0, 6.3, 3)
    off = amp * (np.sin(s / wl * 6.283 + ph[0]) * 0.6 + np.sin(s / (wl * 0.43) * 6.283 + ph[1]) * 0.3 + np.sin(s / (wl * 2.3) * 6.283 + ph[2]) * 0.4)
    return D + Nn * off[:, None]


def lateral(D, xg, zg, ub):
    tree = cKDTree(D)
    d, k = tree.query(np.stack([xg.ravel(), zg.ravel()], 1), distance_upper_bound=ub)
    ok = np.isfinite(d); k = np.minimum(k, len(D) - 1)
    T = np.gradient(D, axis=0); T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-6)
    q = D[k]; t = T[k]
    u = (xg.ravel() - q[:, 0]) * -t[:, 1] + (zg.ravel() - q[:, 1]) * t[:, 0]
    along = np.abs((xg.ravel() - q[:, 0]) * t[:, 0] + (zg.ravel() - q[:, 1]) * t[:, 1])
    endcap = along > 0.6                                   # beyond the polyline's ends
    u = np.where(ok & ~endcap, u, 1e3)
    return u.reshape(xg.shape)


def gauss(u, w):
    return np.exp(-0.5 * (u / w) ** 2)


cover = ss(0.22, 0.42, n12) * (0.7 + 0.3 * n30)        # where blown sand has not covered the tracks
for k, t in enumerate(FEAT['tracks']):
    kind = t['kind']
    pts = np.asarray(t['pts'], float)
    if kind == 'wheel': pts = np.vstack([pts, pts[:1]])
    if kind == 'warden':
        D = meander(pts, 0.7, 34, 100 + k); u = lateral(D, X, Z, 6)
        band = 1 - ss(1.0, 1.6, np.abs(u))
        ruts = gauss(u - 0.8, 0.17) + gauss(u + 0.8, 0.17)
        track = np.maximum(track, (band * 0.35 + ruts * 0.4) * cover)
        relief -= ruts * 0.05 * cover; relief += gauss(u, 0.35) * 0.012 * cover
    elif kind == 'caravan':
        for m, shift in enumerate((-2.3, 0.0, 2.5)):
            D = meander(pts, 1.4, 46 + m * 13, 200 + m)
            u = lateral(D, X, Z, 10) - shift
            ruts = gauss(u - 0.95, 0.2) + gauss(u + 0.95, 0.2)
            band = 1 - ss(1.3, 2.0, np.abs(u))
            fade = 0.55 + 0.45 * noise(40, 300 + m)
            track = np.maximum(track, (band * 0.3 + ruts * 0.45) * fade * cover)
            relief -= ruts * 0.065 * fade * cover
    elif kind == 'haul':
        D = meander(pts, 1.0, 60, 400 + k); u = lateral(D, X, Z, 6)
        bands = (1 - ss(0.25, 0.42, np.abs(np.abs(u) - 1.05)))
        old = ss(0.3, 0.55, n20)                               # old and half buried
        track = np.maximum(track, bands * 0.45 * old)
        relief -= bands * 0.025 * old
    elif kind == 'wheel':
        D = meander(pts, 0.6, 12, 500 + k); u = lateral(D, X, Z, 3)
        rut = gauss(u, 0.14)
        track = np.maximum(track, rut * 0.55 * (0.6 + 0.4 * n12)); relief -= rut * 0.04

# ------------------------------------------------------------------ craters, scorch, glass
scorch = np.zeros_like(X); ejecta = np.zeros_like(X); crater_in = np.zeros_like(X)
for cr in FEAT['craters']:
    R = cr['r']; ext = R * 2.6
    jj = slice(max(0, int((cr['z'] - ext - RZ0) / TX)), min(RES, int((cr['z'] + ext - RZ0) / TX) + 1))
    ii = slice(max(0, int((cr['x'] - ext - RX0) / TX)), min(RES, int((cr['x'] + ext - RX0) / TX) + 1))
    dx, dz = X[jj, ii] - cr['x'], Z[jj, ii] - cr['z']
    r = np.hypot(dx, dz) / R; a = np.arctan2(dz, dx)
    rr = np.random.default_rng(cr['seed']); ph = rr.uniform(0, 6.3, 4)
    wob = 1 + 0.08 * np.sin(3 * a + ph[0]) + 0.05 * np.sin(5 * a + ph[1])
    r = r / wob
    depth = min(0.38, 0.11 * R)
    relief[jj, ii] += np.where(r < 1, -depth * (1 - r * r), 0) + 0.04 * gauss(r - 1.0, 0.12)
    rays = ss(0.45, 0.8, 0.5 + 0.3 * np.sin(7 * a + ph[2]) + 0.25 * np.sin(13 * a + ph[3]))
    sc = (1 - ss(0.35, 1.5, r)) * 0.75 + rays * (1 - ss(1.0, 2.4, r)) * 0.45
    if cr['glass']:
        sc = np.maximum(sc, (1 - ss(0.25, 0.55, r)) * 1.0)
    else:
        sc = np.minimum(sc, 0.58)
    scorch[jj, ii] = np.maximum(scorch[jj, ii], sc)
    ejecta[jj, ii] = np.maximum(ejecta[jj, ii], gauss(r - 1.25, 0.3) * 0.7)
    crater_in[jj, ii] = np.maximum(crater_in[jj, ii], 1 - ss(0.8, 1.05, r))
# burn scars under battle wrecks
pl = json.loads((HERE / 'placements.json').read_text())
for p in pl['prefabs']:
    if p['group'] != 'Wreckage' or not any(k in p['prefab'] for k in ('DeadWorker', 'WorkerDroidShell', 'CrashedDrone', 'DroneRack', 'Cradle')): continue
    rr = np.random.default_rng(int(abs(p['x'] * 131 + p['z'] * 17)))
    R = rr.uniform(2.5, 4.5); ext = R * 1.6
    jj = slice(max(0, int((p['z'] - ext - RZ0) / TX)), min(RES, int((p['z'] + ext - RZ0) / TX) + 1))
    ii = slice(max(0, int((p['x'] - ext - RX0) / TX)), min(RES, int((p['x'] + ext - RX0) / TX) + 1))
    r = np.hypot(X[jj, ii] - p['x'], Z[jj, ii] - p['z']) / R
    scorch[jj, ii] = np.maximum(scorch[jj, ii], (1 - ss(0.2, 1.3, r + (n6[jj, ii] - 0.5) * 0.6)) * 0.5)
scorch = np.clip(scorch, 0, 1)

# dunes and earthworks: wind sand on dunes, gravelly packed fill on the berms (the meshes sample the same mask)
dune_fp = np.zeros_like(X); berm_fp = np.zeros_like(X)
for du in FEAT['dunes']:
    d, _, _ = poly_raster(du['pts'], X, Z, step=0.5)
    dune_fp = np.maximum(dune_fp, 1 - ss(du['w'] * 0.45, du['w'] * 0.75, d))
for e in FEAT['earthworks']:
    for seg in e['segments']:
        d, _, _ = poly_raster(seg, X, Z, step=0.5)
        berm_fp = np.maximum(berm_fp, 1 - ss(e['w'] * 0.4, e['w'] * 0.6, d))

# ------------------------------------------------------------------ compose
clay = np.maximum(pan, wash_bed * (1 - bars) * 0.75)
wind = np.maximum.reduce([wind * (1 - pan), pan_fringe * 0.7, bank * 0.6, dune_fp])
wind = wind * (1 - wash_bed * 0.85)
gravel = np.maximum(gravel * (1 - wash_bed), bars)
gravel = np.maximum(gravel, ejecta)
hard = hard * (1 - pan) * (1 - wash_bed)
berm_mix = berm_fp * (1 - dune_fp)
hard = np.maximum(hard, berm_mix * 0.35); gravel = np.maximum(gravel, berm_mix * 0.3)
# craters blow the sand off
wind *= 1 - crater_in * 0.9; clay *= 1 - crater_in
# priority: tracks > washes/pans > dunes/sand > gravel > hardpan, normalised so the sum stays <= 1
track = np.clip(track, 0, 1)
rest = 1 - track
clay = clay * rest
wind = wind * np.clip(rest - clay, 0, 1)
gravel = gravel * np.clip(rest - clay - wind, 0, 1)
hard = hard * np.clip(rest - clay - wind - gravel, 0, 1)
varnish = varnish * (1 - wash_bed) * (1 - crater_in) * (1 - track * 0.6)
relief = relief + wash_rel

A = np.stack([clay, hard, wind, gravel], -1) * FADE[..., None]
B = np.stack([varnish * FADE, 0.5 + np.clip(relief * FADE, -RELIEF_RANGE, RELIEF_RANGE) / (2 * RELIEF_RANGE), scorch * FADE, track * FADE], -1)


def save(arr, path):
    img = (np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8)
    Image.fromarray(np.flipud(img), 'RGBA').save(path, optimize=True)


ART_OUT.joinpath('Ground').mkdir(parents=True, exist_ok=True)
save(A, ART_OUT / 'Ground/BermsVarietySplatA.png')
save(B, ART_OUT / 'Ground/BermsVarietySplatB.png')

# ------------------------------------------------------------------ footsteps (2 m cells)
FS = 256
def pool(a): return a.reshape(FS, RES // FS, FS, RES // FS).mean(axis=(1, 3))
pc, ph_, pw, pg, pt = pool(A[..., 0]), pool(A[..., 1]), pool(A[..., 2]), pool(A[..., 3]), pool(B[..., 3])
pglass = pool((B[..., 2] > 0.62).astype(np.float32))
natural = 1 - (pc + ph_ + pw + pg + pt)
stack = np.stack([pc + ph_ + pglass, pw, pg + pt + natural * 0.9], -1)     # stone, sand, gravel
surf = np.argmax(stack, -1).astype(np.uint8)                                # 0 stone, 1 sand, 2 gravel (FootSurface)
(HERE / 'footsteps.json').write_text(json.dumps(dict(
    rect=[RX0, RZ0, 1 / RSIZE, 1 / RSIZE], width=FS, height=FS, cells=base64.b64encode(surf.tobytes()).decode(),
    colliders=['berms expanse/ground', 'berms variety/earthworks', 'berms variety/craters', 'berms variety/dunes'],
    legend={'0': 'Stone (clay pan, hardpan, glass)', '1': 'Sand', '2': 'Gravel (fans, tracks, natural scree)'},
    counts={str(k): int((surf == k).sum()) for k in range(3)})) + '\n')

# ------------------------------------------------------------------ preview + stats
cols = np.array([[0.85, 0.80, 0.70], [0.55, 0.40, 0.30], [0.95, 0.75, 0.40], [0.45, 0.45, 0.50]])
prev = np.einsum('jik,kc->jic', A, cols) + (1 - A.sum(-1, keepdims=True)) * 0.6
prev *= (1 - B[..., 2:3] * 0.8); prev = prev * (1 - B[..., 0:1] * 0.5 * A[..., 3:4])
prev = np.where(B[..., 3:4] > 0.25, prev * 0.6 + np.array([0.2, 0.3, 0.7]) * 0.4, prev)
prev = np.clip(prev + (B[..., 1:2] - 0.5) * 1.2, 0, 1)
pv = (prev[::2, ::2] * 255).astype(np.uint8)
Image.fromarray(np.flipud(pv)).save(HERE / 'work/regions_preview.png')
inside = (DIN > 4) & (DOLD > 12)
stats = {k: round(float(v[inside].mean()), 3) for k, v in dict(clay=A[..., 0], hard=A[..., 1], wind=A[..., 2], gravel=A[..., 3], track=B[..., 3], scorch=B[..., 2], varnish=B[..., 0]).items()}
stats['natural_share'] = round(float((1 - A[..., :4].sum(-1) - B[..., 3])[inside].mean()), 3)
stats['glass_m2'] = round(float((B[..., 2] > 0.62).sum() * TX * TX), 1)
stats['footsteps'] = {['stone', 'sand', 'gravel'][k]: int((surf == k).sum()) for k in range(3)}
(HERE / 'work/regions_stats.json').write_text(json.dumps(stats, indent=1) + '\n')
print(json.dumps(stats))
