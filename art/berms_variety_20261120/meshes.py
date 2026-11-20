#!/usr/bin/env python3
"""Relief meshes for the Outer Berms ground variety (20 Nov 2026) -> BermsVarietyRelief.glb + the chunk list.

From features.json (layout.py), straight from numpy (art/berms_expanse_20261002/glb_write.py, no Blender step):
  Earthworks_k   old Warden berm segments: rounded earth banks 1.3-1.6 m high, 6.5-9 m at the base, eroded crest,
                 gullies and slumped ends, edges buried 0.2-0.35 m below the ground so they meet it without a seam
  Dunes_k        barchan-like dunes across the wind: gentle windward back, steeper lee face, horns
  Craters_k      raised ejecta rims round the larger craters (the bowl itself is painted in the region mask: the
                 walkable ground mesh may not be dug)
  Outcrops_k     sandstone ledges, tors and tilted slabs: stepped strata rings with a terrace, noisy outline, domed cap,
                 the base buried 0.4 m
Each object has _LOD0, _LOD1 and _COL (= LOD1 geometry, walkable where it is gentle). Vertices are absolute world
positions (the installer puts every chunk at the origin). COLOR: R 1 (lit; the basin rock shader's authored noon shadow
is off for these), G sky access (lower at the foot). Earthworks, dunes and rims use the Berms Ground V3 material, so the
same world-space layers and region mask run over them; outcrops use the basin's SandstoneBasinV3 (cliff rock, strata).
Run: $O/heavy.sh uv run --with numpy --with scipy python meshes.py
"""
import json, math, sys
import numpy as np
from scipy import ndimage
from bv_common import Field, HERE, BX, ART_OUT

sys.path.insert(0, str(BX))
from glb_write import write_glb  # noqa: E402

F = Field()
FEAT = json.loads((HERE / 'features.json').read_text())
WIND = np.array(FEAT['wind'], float)


def ss(e0, e1, x):
    t = np.clip((np.asarray(x, float) - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)


def vnoise1(s, seed, wl):
    r = np.random.default_rng(seed); n = int(np.max(s) / wl) + 4
    v = r.uniform(-1, 1, n)
    return np.interp(np.asarray(s) / wl, np.arange(n), v)


def grid_mesh(P, nu, nv, closed_v=False):
    """Triangles for a (nu x nv) vertex grid stored row-major (u major)."""
    I = []
    vmax = nv if closed_v else nv - 1
    for i in range(nu - 1):
        for j in range(vmax):
            a = i * nv + j; b = i * nv + (j + 1) % nv; c = (i + 1) * nv + j; d = (i + 1) * nv + (j + 1) % nv
            I += [[a, c, b], [b, c, d]]
    return np.array(I, np.int64)


def normals(P, I):
    N = np.zeros_like(P)
    fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    for k in range(3): np.add.at(N, I[:, k], fn)
    N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9)
    return N


def orient_up(P, I):
    """Make every triangle wind counter-clockwise seen from above (Unity space, +Y up) so normals point up/out."""
    fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    flip = fn[:, 1] < 0
    I = I.copy(); I[flip] = I[flip][:, [0, 2, 1]]
    return I


def orient_out(P, I, centre):
    """Wind every triangle so its normal points away from a centre point (outcrop walls and caps)."""
    fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    cen = (P[I[:, 0]] + P[I[:, 1]] + P[I[:, 2]]) / 3
    flip = (fn * (cen - centre)).sum(1) < 0
    I = I.copy(); I[flip] = I[flip][:, [0, 2, 1]]
    return I


def colours(P, sky):
    C = np.ones((len(P), 4), np.float32); C[:, 1] = sky; return C


def resample(pts, step):
    P = np.asarray(pts, float)
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1); s = np.r_[0, np.cumsum(seg)]
    n = max(2, int(round(s[-1] / step)) + 1)
    t = np.linspace(0, s[-1], n)
    return np.stack([np.interp(t, s, P[:, 0]), np.interp(t, s, P[:, 1])], 1), t


def ribbon(pts, half, height_fn, nv, step, seed, crest_shift=0.0, bury=0.25, profile=None):
    """Bank along a centreline: cross-section offsets v in [-1, 1] * half plus buried skirts."""
    C, s = resample(pts, step)
    C = np.stack([ndimage.gaussian_filter1d(C[:, 0], 1.5, mode='nearest'), ndimage.gaussian_filter1d(C[:, 1], 1.5, mode='nearest')], 1)
    T = np.gradient(C, axis=0); T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-9)
    N = np.stack([-T[:, 1], T[:, 0]], 1)
    v = np.r_[-1.18, np.linspace(-1, 1, nv), 1.18]
    hs = height_fn(s)
    P = []; sky = []
    for i in range(len(C)):
        for vv in v:
            off = vv * half + crest_shift
            x, z = C[i] + N[i] * off
            g = float(F.ground(x, z))
            if abs(vv) > 1.01: y = g - bury - 0.12
            else:
                p = profile(vv) if profile else (1 - ss(0.22, 1.0, abs(vv)))
                y = g + hs[i] * p - bury * ss(0.85, 1.0, abs(vv))
            P.append([x, y, z]); sky.append(0.9 + 0.08 * (1 - abs(min(vv, 1))))
    P = np.array(P); I = grid_mesh(P, len(C), len(v))
    return P, I, np.array(sky)


def decimate_ribbon(P, nu, nv, su, sv):
    iu = list(range(0, nu, su)); iu[-1:] = [nu - 1] if iu[-1] != nu - 1 else iu[-1:]
    if iu[-1] != nu - 1: iu.append(nu - 1)
    iv = sorted(set([0, 1] + list(range(1, nv - 1, sv)) + [nv - 2, nv - 1]))
    Q = P.reshape(nu, nv, 3)[np.ix_(iu, iv)].reshape(-1, 3)
    return Q, grid_mesh(Q, len(iu), len(iv))


objects = []; chunks = []; stats = {}


def emit(group, k, P0, I0, P1, I1, sky0, sky1, material, shadows, lod1, cull, centre=None):
    name = f'{group}_{k:02d}'
    if centre is None: I0 = orient_up(P0, I0); I1 = orient_up(P1, I1)
    else: I0 = orient_out(P0, I0, centre); I1 = orient_out(P1, I1, centre)
    objects.append(dict(name=name + '_LOD0', P=P0, N=normals(P0, I0), C=colours(P0, sky0), I=I0))
    objects.append(dict(name=name + '_LOD1', P=P1, N=normals(P1, I1), C=colours(P1, sky1), I=I1))
    objects.append(dict(name=name + '_COL', P=P1, N=normals(P1, I1), C=None, I=I1))
    ext = P0.max(0) - P0.min(0)
    chunks.append(dict(name=name, group=group, material=material, shadows=shadows, size=round(float(max(ext[0], ext[2], 4.0)), 2),
                       lod1=lod1, cull=cull, lod0Triangles=int(len(I0)), lod1Triangles=int(len(I1)),
                       centre=[round(float(x), 2) for x in (P0.min(0) + P0.max(0)) / 2]))
    st = stats.setdefault(group, dict(objects=0, lod0=0, lod1=0)); st['objects'] += 1; st['lod0'] += len(I0); st['lod1'] += len(I1)


# ------------------------------------------------------------------ earthworks
k = 0
for e in FEAT['earthworks']:
    for seg in e['segments']:
        seed = 7000 + k
        L = (len(seg) - 1) * 1.0

        def hfn(s, e=e, seed=seed, L=L):
            erosion = 0.78 + 0.22 * vnoise1(s, seed, 11.0) * 0.5 + 0.11
            gully = 1 - 0.32 * np.clip(vnoise1(s, seed + 1, 3.5), 0, 1) ** 3
            ends = ss(0, 4.5, s) * ss(0, 4.5, L - s)
            return e['h'] * erosion * gully * (0.25 + 0.75 * ends)
        nv = 13
        P0, I0, sky0 = ribbon(seg, e['w'] * 0.5, hfn, nv, 0.8, seed, crest_shift=0.3, bury=0.22)
        nu = len(P0) // (nv + 2)
        P1, I1 = decimate_ribbon(P0, nu, nv + 2, 3, 3)
        sky1 = np.full(len(P1), 0.93)
        emit('Earthworks', k, P0, I0, P1, I1, sky0, sky1, 'ground', True, 0.3, 0.006)
        k += 1

# ------------------------------------------------------------------ dunes (across the wind; profile asymmetric along it)
for k, d in enumerate(FEAT['dunes']):
    L = float(np.sum(np.linalg.norm(np.diff(np.asarray(d['pts']), axis=0), axis=1)))

    def hfn(s, d=d, L=L):
        return d['h'] * np.sin(np.pi * np.clip(s / L, 0, 1)) ** 0.7 * (0.9 + 0.1 * vnoise1(s, 900 + k, 6))

    # the ribbon's normal points to one side of the crest; make v > 0 the downwind (lee) side
    C, _ = resample(d['pts'], 1.0); T = C[-1] - C[0]; Nn = np.array([-T[1], T[0]])
    lee_sign = 1.0 if np.dot(Nn, WIND) > 0 else -1.0

    def prof(v, ls=lee_sign):
        v = v * ls; c = 0.38                         # crest 38 % of the half width toward the lee
        up = 1 - ss(0, 1, (c - v) / (1 + c))          # long windward back
        down = 1 - ss(0, 1, (v - c) / (1 - c)) ** 0.8  # short lee face
        return np.where(v <= c, up, down)
    P0, I0, sky0 = ribbon(d['pts'], d['w'] * 0.5, hfn, 17, 1.0, 900 + k, bury=0.25, profile=prof)
    nu = len(P0) // 19
    P1, I1 = decimate_ribbon(P0, nu, 19, 3, 3)
    emit('Dunes', k, P0, I0, P1, I1, sky0, np.full(len(P1), 0.95), 'ground', True, 0.3, 0.006)

# ------------------------------------------------------------------ crater rims
k = 0
for c in FEAT['craters']:
    if not c['rim']: continue
    R = c['r']; r = np.random.default_rng(c['seed']); ph = r.uniform(0, 6.3, 3)

    def rim(na, nr):
        a = np.linspace(0, 2 * np.pi, na, endpoint=False)
        rr = np.linspace(0.55, 1.75, nr)
        wob = 1 + 0.08 * np.sin(3 * a + ph[0]) + 0.05 * np.sin(5 * a + ph[1])
        hr = min(0.55, 0.12 * R) * (0.75 + 0.35 * (0.5 + 0.5 * np.sin(4 * a + ph[2])))
        P = []
        for i, q in enumerate(rr):
            for j in range(na):
                rad = q * R * wob[j]
                x, z = c['x'] + rad * math.cos(a[j]), c['z'] + rad * math.sin(a[j])
                g = float(F.ground(x, z))
                if q < 1: h = -0.18 + (hr[j] + 0.18) * ss(0.55, 1.0, q)
                else: h = hr[j] * math.exp(-((q - 1) / 0.32) ** 2) - 0.22 * ss(1.3, 1.75, q)
                P.append([x, g + h, z])
        P = np.array(P); I = grid_mesh(P, nr, na, closed_v=True)
        return P, I
    P0, I0 = rim(48, 10); P1, I1 = rim(20, 5)
    emit('Craters', k, P0, I0, P1, I1, np.full(len(P0), 0.92), np.full(len(P1), 0.92), 'ground', False, 0.25, 0.03)
    k += 1

# ------------------------------------------------------------------ outcrops (fix round 20 Nov: eroded, chamfered, UV-mapped)
# Walls: a grid of columns along the outline (~0.45 m) by rows (~0.3 m) displaced by a foot flare, a rounded top
# chamfer, recessed soft beds that run with the bedding (world height), vertical joints and two octaves of noise.
# They carry cylindrical UVs (u = arc length, v = height, 2.3 m per tile) for the tiling Poly Haven "Cliff Side" rock
# (URP Lit, BermsVarietyRock.mat), so the bedding in the texture runs level. Cap and foot apron (drifted sand against
# the wall, deeper on the lee side) are a second mesh on the ground material, so the top and the foot read as the floor.
UVS = 2.3


def vn2(a, b, seed, sa, sb):
    """2D value noise (bilinear) in [-1, 1] at coordinates a/sa, b/sb."""
    r = np.random.default_rng(seed); g = r.uniform(-1, 1, (64, 64))
    x = np.asarray(a) / sa; y = np.asarray(b) / sb
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int); fx = x - x0; fy = y - y0
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy)
    def G(i, j): return g[i % 64, j % 64]
    return (G(x0, y0) * (1 - fx) + G(x0 + 1, y0) * fx) * (1 - fy) + (G(x0, y0 + 1) * (1 - fx) + G(x0 + 1, y0 + 1) * fx) * fy


def outcrop(l):
    r = np.random.default_rng(l['seed']); seed = l['seed'] % 100000
    O = np.asarray(l['outline'], float); cx, cz = l['x'], l['z']
    th = np.arctan2(O[:, 1] - cz, O[:, 0] - cx); rad = np.hypot(O[:, 0] - cx, O[:, 1] - cz)
    o = np.argsort(th); th, rad = th[o], rad[o]
    dense = np.linspace(-np.pi, np.pi, 1024, endpoint=False)
    rd = np.interp(dense, np.r_[th - 2 * np.pi, th, th + 2 * np.pi], np.r_[rad, rad, rad])
    seg = np.hypot(np.diff(np.r_[rd, rd[0]] * np.cos(np.r_[dense, dense[0] + 2 * np.pi])), np.diff(np.r_[rd, rd[0]] * np.sin(np.r_[dense, dense[0] + 2 * np.pi])))
    arc = np.r_[0, np.cumsum(seg)]; per = arc[-1]
    gc = float(F.ground(cx, cz)); h = l['h']; tilt = math.radians(l.get('tilt', 0)); yaw = math.radians(l['yaw'])
    tdir = np.array([math.cos(yaw), math.sin(yaw)])
    rh = min(0.9, (0.45 if l['kind'] in ('block', 'tor') else 0.32) * h)
    joints = r.uniform(0, per, max(2, int(per / 5.5)))

    def wall(col_step, row_step):
        ncol = max(24, int(round(per / col_step)))
        s = np.linspace(0, per, ncol + 1)                       # last column duplicates the first (UV seam)
        a = np.interp(s, arc, np.r_[dense, dense[0] + 2 * np.pi])
        rb = np.interp(s, arc, np.r_[rd, rd[0]])
        nrow = max(5, int(round(h / row_step)))
        fs = np.r_[-0.18, np.linspace(0, 1, nrow + 1)]
        P = np.zeros((len(fs), len(s), 3)); UV = np.zeros((len(fs), len(s), 2))
        for j, (sj, aj, rbj) in enumerate(zip(s, a, rb)):
            ca, sa = math.cos(aj), math.sin(aj)
            xb, zb = cx + rbj * ca, cz + rbj * sa
            g = float(F.ground(xb, zb))
            top = max(gc + h + math.tan(tilt) * float(np.dot([xb - cx, zb - cz], tdir)), g + 0.35)
            jn = sum(0.32 * math.exp(-((((sj - jp + per / 2) % per) - per / 2) / 0.35) ** 2) for jp in joints)
            for i, f in enumerate(fs):
                if f < 0: y = g - 0.45; inset = -0.2
                else:
                    y = g + (top - g) * f
                    hh = (top - g)
                    fr = 1 - rh / max(hh, 0.5)
                    cham = rh * 1.15 * (1 - math.sqrt(max(0.0, 1 - ((f - fr) / max(1 - fr, 1e-3)) ** 2))) if f > fr else 0.0
                    flare = -0.22 * (1 - ss(0, 0.18, f))
                    bed = 0.5 + 0.5 * math.sin(2 * math.pi * y / 0.47 + 1.6 * math.sin(2 * math.pi * y / 1.37 + 0.8))
                    groove = 0.13 * bed ** 3 * (0.55 + 0.45 * vn2(sj, 0, seed, 3.0, 1)) * ss(0.05, 0.2, f) * (1 - ss(0.85, 1, f))
                    nz = 0.09 * vn2(sj, y, seed + 1, 1.1, 0.9) + 0.16 * vn2(sj, y, seed + 2, 3.4, 2.6)
                    inset = flare + cham + groove + jn * ss(0.08, 0.3, f) + nz * ss(0.0, 0.1, f)
                rr = max(rbj - inset, 0.3)
                P[i, j] = [cx + rr * ca, y, cz + rr * sa]
                UV[i, j] = [sj / UVS, y / UVS]
        I = grid_mesh(P.reshape(-1, 3), len(fs), len(s))
        return P, UV, I

    def caps(Pw, qs):
        """Rock top (rock material, planar UVs) and the sand lying on it (ground material): the sand surface is the rock
        surface plus a noisy offset that sinks below the rock toward the rim, so sand shows only in irregular patches and
        hollows, thinnest at the edges (fix round 2, 20 Nov: the cap was a hard-edged slab)."""
        top = Pw[-1, :-1]; n = len(top)
        cen = np.array([cx, 0, cz]); mt = top[:, 1].mean()
        rock = []; sand = []
        for q in qs:
            R = cen + (top - cen) * np.array([q, 0, q])
            R[:, 1] = top[:, 1] * q + (mt + h * 0.12 * (1 - q * q)) * (1 - q) + (0.07 * vn2(R[:, 0], R[:, 2], seed + 3, 1.8, 1.8) if q < 1 else 0)
            rock.append(R)
            S = R.copy()
            off = -0.24 * q ** 1.5 + 0.05 * (1 - q) + 0.13 * vn2(R[:, 0], R[:, 2], seed + 5, 1.6, 1.6) + 0.05 * vn2(R[:, 0], R[:, 2], seed + 6, 0.6, 0.6) - 0.03
            S[:, 1] = R[:, 1] + off
            sand.append(S)
        cr = np.array([cx, mt + h * 0.12, cz])
        def close(rings, centre):
            P = np.vstack(rings + [centre]); I = grid_mesh(P[:-1], len(rings), n, closed_v=True).tolist(); c0 = len(P) - 1
            for j in range(n): I.append([(len(rings) - 1) * n + j, (len(rings) - 1) * n + (j + 1) % n, c0])
            return P, np.array(I)
        Pr, Ir = close(rock, cr)
        Ps, Is = close(sand, cr + np.array([0, 0.04, 0]))
        UVr = np.stack([Pr[:, 0] / UVS, Pr[:, 2] / UVS], 1)
        return Pr, Ir, UVr, Ps, Is

    def apron(Pw):
        base = Pw[1, :-1]; n = len(base); cen = np.array([cx, 0, cz])
        out = base - cen; out[:, 1] = 0; out /= np.maximum(np.linalg.norm(out, axis=1, keepdims=True), 1e-6)
        lee = np.clip(out[:, 0] * WIND[0] + out[:, 2] * WIND[1], 0, 1)
        arcpos = np.arange(n) * per / n
        nzA = vn2(arcpos, 0, seed + 4, 2.5, 1) * 0.6 + vn2(arcpos, 0, seed + 7, 0.9, 1) * 0.4
        ha = np.clip(0.14 + 0.5 * lee + 0.2 * nzA, 0.05, None); wa = 1.3 + 3.4 * lee + 0.8 * nzA
        A = []
        for t, hf in ((0.0, 1.0), (0.18, 0.75), (0.4, 0.45), (0.7, 0.15), (1.0, -0.12)):
            R = np.zeros((n, 3))
            for j in range(n):
                x = base[j, 0] + out[j, 0] * (wa[j] * t - 0.15); z = base[j, 2] + out[j, 2] * (wa[j] * t - 0.15)
                g = float(F.ground(x, z))
                R[j] = [x, g + (ha[j] * hf * (1 + 0.25 * vn2(x, z, seed + 8, 0.8, 0.8)) if hf > 0 else hf), z]
            A.append(R)
        return np.vstack(A), grid_mesh(np.vstack(A), 5, n, closed_v=True)

    Pw0, UV0, Iw0 = wall(0.45, 0.3); Pw1, UV1, Iw1 = wall(1.35, 0.6)
    Pr0, Ir0, Ur0, Ps0, Is0 = caps(Pw0, (1.0, 0.9, 0.79, 0.67, 0.55, 0.43, 0.31, 0.19, 0.08))
    Pr1, Ir1, Ur1, Ps1, Is1 = caps(Pw1, (1.0, 0.7, 0.4, 0.12))
    Pa0, Ia0 = apron(Pw0); Pa1, Ia1 = apron(Pw1)
    def merge(*parts):
        P, I, off = [], [], 0
        for p_, i_ in parts: P.append(p_); I.append(np.asarray(i_) + off); off += len(p_)
        return np.vstack(P), np.vstack(I)
    nw0 = Pw0.reshape(-1, 3); nw1 = Pw1.reshape(-1, 3)
    R0, RI0 = merge((nw0, Iw0), (Pr0, Ir0)); R1, RI1 = merge((nw1, Iw1), (Pr1, Ir1))
    RU0 = np.vstack([UV0.reshape(-1, 2), Ur0]); RU1 = np.vstack([UV1.reshape(-1, 2), Ur1])
    G0, GI0 = merge((Ps0, Is0), (Pa0, Ia0)); G1, GI1 = merge((Ps1, Is1), (Pa1, Ia1))
    centre = np.array([cx, gc + h * 0.4 - 0.5, cz])
    sky0 = np.r_[np.repeat(np.linspace(0.78, 1.0, Pw0.shape[0]), Pw0.shape[1]), np.ones(len(Pr0))]
    sky1 = np.r_[np.repeat(np.linspace(0.78, 1.0, Pw1.shape[0]), Pw1.shape[1]), np.ones(len(Pr1))]
    return [dict(suffix='', P0=R0, I0=RI0, UV0=RU0, P1=R1, I1=RI1, UV1=RU1, sky0=sky0, sky1=sky1, material='rock', shadows=True, orient=centre),
            dict(suffix='_GND', P0=G0, I0=GI0, P1=G1, I1=GI1, sky0=np.full(len(G0), 0.95), sky1=np.full(len(G1), 0.95),
                 material='ground', shadows=False, orient=None)]


def emit_parts(group, k, parts, lod1, cull):
    name = f'{group}_{k:02d}'
    colP, colI, t0, t1 = [], [], 0, 0; allP = []
    for pt in parts:
        for lod in ('0', '1'):
            P, I = pt['P' + lod], pt['I' + lod]
            I = orient_up(P, I) if pt['orient'] is None else orient_out(P, I, pt['orient'])
            pt['I' + lod] = I
            objects.append(dict(name=f"{name}{pt['suffix']}_LOD{lod}", P=P, N=normals(P, I), C=colours(P, pt['sky' + lod]), I=I, UV=pt.get('UV' + lod)))
        off = sum(len(p) for p in colP); colP.append(pt['P1']); colI.append(pt['I1'] + off)
        t0 += len(pt['I0']); t1 += len(pt['I1']); allP.append(pt['P0'])
    CP = np.vstack(colP); CI = np.vstack(colI)
    objects.append(dict(name=name + '_COL', P=CP, N=normals(CP, CI), C=None, I=CI))
    AP = np.vstack(allP); ext = AP.max(0) - AP.min(0)
    chunks.append(dict(name=name, group=group, parts=[dict(suffix=p['suffix'], material=p['material'], shadows=p['shadows']) for p in parts],
                       material=parts[0]['material'], shadows=any(p['shadows'] for p in parts), size=round(float(max(ext[0], ext[2], 4.0)), 2),
                       lod1=lod1, cull=cull, lod0Triangles=int(t0), lod1Triangles=int(t1),
                       centre=[round(float(x), 2) for x in (AP.min(0) + AP.max(0)) / 2]))
    st = stats.setdefault(group, dict(objects=0, lod0=0, lod1=0)); st['objects'] += 1; st['lod0'] += t0; st['lod1'] += t1


for k, l in enumerate(FEAT['ledges']):
    emit_parts('Outcrops', k, outcrop(l), 0.3, 0.004)

ART_OUT.joinpath('Meshes').mkdir(parents=True, exist_ok=True)
size = write_glb(ART_OUT / 'Meshes/BermsVarietyRelief.glb', objects, generator='ao2 berms variety 20261120')
pl_path = HERE / 'placements.json'
pl = json.loads(pl_path.read_text()); pl['chunks'] = chunks
pl_path.write_text(json.dumps(pl, indent=0) + '\n')
(HERE / 'mesh.json').write_text(json.dumps(dict(glb='Assets/AthenHill/Art/BermsVariety/Meshes/BermsVarietyRelief.glb', bytes=size, groups=stats, chunks=len(chunks)), indent=1) + '\n')
print(json.dumps(stats), size)
