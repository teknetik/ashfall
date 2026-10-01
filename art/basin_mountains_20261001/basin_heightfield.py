#!/usr/bin/env python3
"""Basin mountains heightfield (Ward desert basin backdrop, 1 Oct 2026).

Builds one global 1 m heightfield in Unity world metres (X east, Z north, Y up) for the ring of mountains outside
the city, then bakes the per-vertex lighting fields the terrain shader reads (R = authored noon sun visibility,
G = sky access). The macro layout is the original generator's (blender/scripts/18_desert_terrain.py: front
escarpment, crest ring, distant ring and their angular modulation), so every review camera keeps its composition.
New: plan-view warping of the fronts and crests, cliff-and-talus escarpment profile, ridged-multifractal massifs,
strata benches aligned with the V2 shader's world-Y beds, particle hydraulic erosion (gullies, fans) and talus.

Locked zone keeps the ORIGINAL surface exactly (barycentric on the old DesertBasin.glb triangles):
  the Outer Berms ground footprint (X -104..-60, Z -54..48) plus 0.75 m, blending to new by 7 m outside it.
    The Berms ground mesh is the old basin + 0.04 m, so its toe stays clean. Inside the footprint (> 3 m from its
    edge) the basin is hidden under the Berms ground and is dropped from the mesh (mask 'drop').

Run (memory-capped):  $O/heavy.sh uv run --with numpy --with numba --with scipy --with pillow python basin_heightfield.py
Output: work/heightfield.npz (+ work/hillshade.png)
"""
import json, math, sys, time
from pathlib import Path
import numpy as np
import numba as nb
from scipy import ndimage
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import glb_io, noise, stream_power  # noqa: E402

ROOT = Path('/home/teknetik/code/ao2')
WORK = HERE / 'work'
OLD_GLB = ROOT / 'unity/AthenHill/Assets/AthenHill/Art/Terrain/DesertBasin.glb'
GEOLOGY = ROOT / 'unity/AthenHill/Assets/AthenHill/Art/Terrain/Geology.png'
N, CELL, ORG = 1025, 1.0, -512.0          # grid nodes X = ORG + i*CELL (column i), Z = ORG + j*CELL (row j)
BERMS = (-104.0, -60.0, -54.0, 48.0)       # Outer Berms ground footprint x0, x1, z0, z1 (do not modify that object)
SUN_DIR = np.array([0.4836195, 0.6691307, 0.5642487])   # toward the scene's saved key light (Euler 42, 220.6, 0)
SUN_XZ = np.array([SUN_DIR[0], SUN_DIR[2]]) / math.hypot(SUN_DIR[0], SUN_DIR[2])
SUN_TAN = SUN_DIR[1] / math.hypot(SUN_DIR[0], SUN_DIR[2])
P = dict(  # tuning (recorded in heightfield.json)
    front_warp=12.0, crest_warp=26.0, rise_lo=-6.0, rise_hi=8.0, berms_front_shift=0.0, shoulder_lift=0.0, seed_relief=0.12,
    table_mix=0.75, cliff_at=0.5, cliff_wander=0.14, cliff_w=0.05, talus_frac=0.32, dome=0.12,
    sp_cell=2.0, sp_K=0.022, sp_m=0.45, sp_iters=160, sp_dt=1.0, sp_diff=0.004, sp_area_cap=12000.0, peak_restore_max=1.0, sp_uplift=0.0,
    terrace_beds=3, terrace_riser=0.28, terrace_strength=1.0, rock_detail=1.9, hard_lo=-0.65,
    drops_fine=400000, erode_capacity=1.2, erode_speed=0.15, deposit_speed=0.3,
    sp1_K=0.016, sp1_m=0.33, sp1_iters=60, sp1_diff=0.01, gully_seed=0.8,
    detail_amp=0.55,
)


def grid():
    ax = ORG + np.arange(N) * CELL
    X, Z = np.meshgrid(ax, ax)          # [j, i]
    return X, Z


def polar(X, Z):
    """Original generator's coordinates: script x = -Unity X; angle a, distance t beyond the city rectangle."""
    xs, zs = -X, Z
    a = np.arctan2(zs, xs); r = np.hypot(xs, zs)
    edge = np.minimum(62 / np.maximum(np.abs(np.cos(a)), 1e-4), 48 / np.maximum(np.abs(np.sin(a)), 1e-4))
    return a, r - edge, edge


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def smax(a, b, k):
    h = np.clip(0.5 + 0.5 * (a - b) / k, 0, 1)
    return a * h + b * (1 - h) + k * h * (1 - h)


# ----------------------------------------------------------------------------------------------- old surface
@nb.njit(cache=True)
def raster_old(PX, PY, PZ, I, n, org, cell, out):
    for t in range(I.shape[0]):
        a, b, c = I[t, 0], I[t, 1], I[t, 2]
        ax, az, ay = PX[a], PZ[a], PY[a]; bx, bz, by = PX[b], PZ[b], PY[b]; cx, cz, cy = PX[c], PZ[c], PY[c]
        det = (bz - cz) * (ax - cx) + (cx - bx) * (az - cz)
        if abs(det) < 1e-12: continue
        i0 = max(0, int(math.floor((min(ax, bx, cx) - org) / cell)) - 1); i1 = min(n - 1, int(math.ceil((max(ax, bx, cx) - org) / cell)) + 1)
        j0 = max(0, int(math.floor((min(az, bz, cz) - org) / cell)) - 1); j1 = min(n - 1, int(math.ceil((max(az, bz, cz) - org) / cell)) + 1)
        for j in range(j0, j1 + 1):
            z = org + j * cell
            for i in range(i0, i1 + 1):
                x = org + i * cell
                l1 = ((bz - cz) * (x - cx) + (cx - bx) * (z - cz)) / det
                l2 = ((cz - az) * (x - cx) + (ax - cx) * (z - cz)) / det
                l3 = 1 - l1 - l2
                if l1 >= -1e-9 and l2 >= -1e-9 and l3 >= -1e-9:
                    out[j, i] = l1 * ay + l2 * by + l3 * cy


def old_surface():
    js, ms = glb_io.meshes(OLD_GLB)
    out = np.full((N, N), np.nan)
    for m in ms:
        Pm = m['P']
        raster_old(-Pm[:, 0], Pm[:, 1], Pm[:, 2], m['I'], N, ORG, CELL, out)
    return out


# ----------------------------------------------------------------------------------------------- geology
def geology_r(X, Z):
    """Bilinear R of Geology.png at P.xz * _MacroScale (0.009), repeat-wrapped like the shader's sampler."""
    im = np.asarray(Image.open(GEOLOGY).convert('RGBA')).astype(np.float64) / 255.0
    h, w = im.shape[:2]
    u = (X * 0.009) % 1.0; v = (Z * 0.009) % 1.0
    px = u * w - 0.5; py = (1.0 - v) * h - 0.5              # Unity UV v=0 is the bottom image row
    return ndimage.map_coordinates(im[:, :, 0], [py, px], order=1, mode='grid-wrap')


# ----------------------------------------------------------------------------------------------- landform
def blur(A, sigma_m):
    return ndimage.gaussian_filter(A, sigma_m / CELL, mode='nearest')


def landform(X, Z, rec):
    """Uplift envelope on the original layout (front escarpment, crest ring, distant ring with the old angular
    amplitudes), with plan-view warping and a seed relief for the drainage network. Valleys are cut later by
    stream-power incision, so ridges keep about the envelope height."""
    a, t, edge = polar(X, Z)
    aw = np.angle(np.exp(1j * a))                                   # (-pi, pi], 0 = Unity west (script +x)
    tw_near = t + P['front_warp'] * noise.fbm(X, Z, 11, 90.0, 4) + 4.0 * noise.fbm(X, Z, 12, 28.0, 3)
    tw_far = t + P['crest_warp'] * noise.fbm(X, Z, 13, 160.0, 4) + 8.0 * noise.fbm(X, Z, 14, 45.0, 3)
    front = 39 + 12 * np.sin(a * 3 + 1.2) + 8 * np.sin(a * 7 - .8)
    front = front + P['berms_front_shift'] * np.exp(-(aw / 0.5) ** 2)   # keep the escarpment foot at the Berms edge
    summit = np.maximum(17, 38 + 17 * np.sin(a * 3 + .9) + 12 * np.sin(a * 5 - 1.1))
    s = tw_near - front
    shoulder = np.exp(-((s - 19) / 39) ** 2)
    rise = smoothstep(P['rise_lo'], P['rise_hi'], s)
    crest = 145 + 23 * np.sin(a * 4 + .7)
    g_near = shoulder * rise
    g_far = np.exp(-((tw_far - crest) / 57) ** 2)
    g_dist = np.exp(-((tw_far - 278) / 67) ** 2)
    A_far = 61 + 29 * np.sin(a * 3 - 2) + 17 * np.sin(a * 8 + .6)
    A_dist = 68 + 27 * np.sin(a * 5 + .2)
    # tableland profile: a talus apron, then a cliff band at an irregular contour of the ring weight, then a slightly
    # domed caprock top; blended with the plain envelope so not every slope becomes a wall
    cn = P['cliff_at'] + P['cliff_wander'] * noise.fbm(X, Z, 16, 45.0, 3)
    dome = 1 + P['dome'] * noise.fbm(X, Z, 17, 70.0, 3)
    def table(g):
        tf = P['talus_frac']
        prof = tf * smoothstep(0.02, cn - P['cliff_w'], g) + (1 - tf) * smoothstep(cn - P['cliff_w'], cn + P['cliff_w'], g)
        return (1 - P['table_mix']) * g + P['table_mix'] * prof * (0.85 + 0.15 * g) * dome
    near = summit * table(g_near)
    far = A_far * table(g_far)
    distant = A_dist * table(g_dist)
    base = np.maximum(np.maximum(near, far), distant)
    # broad tops: lift the shoulders of each massif so incision leaves tablelands and spurs, not cones
    peak = ndimage.maximum_filter(base, size=int(60 / CELL))
    base = base + P['shoulder_lift'] * (peak - base) * smoothstep(0.35, 0.8, base / np.maximum(peak, 1e-3))
    base = base * (1 + P['seed_relief'] * noise.fbm(X, Z, 15, 110.0, 4))
    apron = (2 + 3 * (0.5 + 0.5 * noise.fbm(X, Z, 31, 45.0, 3))) * np.minimum(1, np.maximum(t, 0) / 15)
    floor_detail = 0.35 * noise.fbm(X, Z, 32, 18.0, 3)
    h = smax(apron + floor_detail, base, 2.0)
    H = -1.8 + h * smoothstep(0, 23, t) * .66
    rec['envelope_max'] = float(H.max())
    return H, a, t, s


def terrace(H, X, Z, geo_r, rec):
    """Strata benches on steep ground, aligned with the shader's bed boundaries (warpY = y + (geo.r-.5)*6 +
    sin(.024x + .018z)*2, beds every _StrataThickness 1.7 m). Each ledge spans P['terrace_beds'] beds; its riser
    share varies per ledge (hard beds make tall cliffs, soft beds slopes), so the face reads as cliff-and-slope bands."""
    step = 1.7 * P['terrace_beds']
    off = (geo_r - 0.5) * 6.0 + np.sin(X * 0.024 + Z * 0.018) * 2.0
    q = H + off
    k = q / step; kf = np.floor(k); f = k - kf
    rnd = np.mod(np.sin(kf * 12.9898 + 4.1) * 43758.5453, 1.0)
    r = P['terrace_riser'] * (0.55 + 0.9 * rnd)                       # riser fraction 0.17..0.44 of each ledge
    fr = smoothstep(1 - r, 1.0, f)
    qt = (kf + fr) * step
    gy, gx = np.gradient(blur(H, 1.5), CELL)
    slope = np.hypot(gx, gy)
    hard = smoothstep(P['hard_lo'], P['hard_lo'] + 0.6, noise.fbm(X, Z, 41, 70.0, 3))                 # some faces benched, others smooth
    m = smoothstep(0.2, 0.6, slope) * hard * smoothstep(3.0, 7.0, H) * P['terrace_strength']
    rec['terrace_area_frac'] = float((m > 0.3).mean())
    return H + m * (qt - q), hard


@nb.njit(cache=True)
def erode(hm, mask, n_drops, seed, radius, inertia, capacity, min_cap, erode_speed, deposit_speed, evaporate, gravity, lifetime):
    np.random.seed(seed)
    H, W = hm.shape
    # brush
    bx = []; by = []; bw = []
    for oy in range(-radius, radius + 1):
        for ox in range(-radius, radius + 1):
            d = math.sqrt(ox * ox + oy * oy)
            if d <= radius:
                bx.append(ox); by.append(oy); bw.append(1 - d / radius)
    sw = 0.0
    for w in bw: sw += w
    nb_ = len(bx)
    for d_ in range(n_drops):
        x = 1 + np.random.random() * (W - 3); y = 1 + np.random.random() * (H - 3)
        if mask[int(y), int(x)] < np.random.random(): continue
        dx = 0.0; dy = 0.0; speed = 1.0; water = 1.0; sed = 0.0
        for it in range(lifetime):
            nx = int(x); ny = int(y); fx = x - nx; fy = y - ny
            h00 = hm[ny, nx]; h10 = hm[ny, nx + 1]; h01 = hm[ny + 1, nx]; h11 = hm[ny + 1, nx + 1]
            gx = (h10 - h00) * (1 - fy) + (h11 - h01) * fy
            gy = (h01 - h00) * (1 - fx) + (h11 - h10) * fx
            h = h00 * (1 - fx) * (1 - fy) + h10 * fx * (1 - fy) + h01 * (1 - fx) * fy + h11 * fx * fy
            dx = dx * inertia - gx * (1 - inertia); dy = dy * inertia - gy * (1 - inertia)
            l = math.sqrt(dx * dx + dy * dy)
            if l < 1e-9: break
            dx /= l; dy /= l
            x += dx; y += dy
            if x < 1 or y < 1 or x >= W - 2 or y >= H - 2: break
            mx = int(x); my = int(y); gfx = x - mx; gfy = y - my
            nh = (hm[my, mx] * (1 - gfx) * (1 - gfy) + hm[my, mx + 1] * gfx * (1 - gfy)
                  + hm[my + 1, mx] * (1 - gfx) * gfy + hm[my + 1, mx + 1] * gfx * gfy)
            dh = nh - h
            cap = max(-dh * speed * water * capacity, min_cap)
            if sed > cap or dh > 0:
                amt = min(dh, sed) if dh > 0 else (sed - cap) * deposit_speed
                sed -= amt
                hm[ny, nx] += amt * (1 - fx) * (1 - fy); hm[ny, nx + 1] += amt * fx * (1 - fy)
                hm[ny + 1, nx] += amt * (1 - fx) * fy; hm[ny + 1, nx + 1] += amt * fx * fy
            else:
                amt = min((cap - sed) * erode_speed, -dh)
                for k in range(nb_):
                    ex = nx + bx[k]; ey = ny + by[k]
                    if ex >= 0 and ey >= 0 and ex < W and ey < H:
                        w = bw[k] / sw * amt
                        hm[ey, ex] -= w
                        sed += w
            speed = math.sqrt(max(0.0, speed * speed - dh * gravity))
            water *= (1 - evaporate)


def thermal(H, mask, repose_deg, iters, rate=0.25):
    """Talus: move material downhill where the slope exceeds the angle of repose (only where mask > 0)."""
    tan_r = math.tan(math.radians(repose_deg))
    for _ in range(iters):
        delta = np.zeros_like(H)
        for dj, di, dist in ((0, 1, 1.0), (1, 0, 1.0), (1, 1, 1.4142), (1, -1, 1.4142)):
            Hn = np.roll(np.roll(H, -dj, 0), -di, 1)
            diff = H - Hn
            excess = (np.abs(diff) - tan_r * dist * CELL)
            move = np.where(excess > 0, np.sign(diff) * excess * rate * 0.5, 0.0) * mask
            delta -= move
            delta += np.roll(np.roll(move, dj, 0), di, 1)
        H = H + delta
    return H


# ----------------------------------------------------------------------------------------------- bakes
def bilinear(Hg, X, Z):
    return ndimage.map_coordinates(Hg, [(Z - ORG) / CELL, (X - ORG) / CELL], order=1, mode='nearest')


def bake_light(Hg, X, Z):
    """R: sun visibility for the scene's saved key light (the original rule: 2 m soft obstruction + 1.2 m bias, denser
    march; used by the shader only when the clock sun sits near the saved key); G: sky access (8 directions)."""
    obstruction = np.full(Hg.shape, -1e9)
    for step in list(np.arange(2, 40, 2.0)) + list(np.arange(40, 160, 5.0)):   # horizontal metres toward the sun
        hs = bilinear(Hg, X + SUN_XZ[0] * step, Z + SUN_XZ[1] * step)
        obstruction = np.maximum(obstruction, hs - Hg - SUN_TAN * step - 1.2)
    sun = 1 - np.clip(np.maximum(obstruction, 0) / 2, 0, 1)
    occ = np.zeros_like(Hg)
    for k in range(8):
        ang = k * math.pi / 4
        dx, dz = math.cos(ang), math.sin(ang)
        hor = np.full(Hg.shape, -1e9)
        for d in (4.0, 8.0, 16.0, 32.0, 64.0):
            hor = np.maximum(hor, (bilinear(Hg, X + dx * d, Z + dz * d) - Hg) / d)
        occ += np.clip(hor, 0, 1) * 0.0275
    return sun, 1 - occ


def hillshade(Hg, path, extra=None):
    gy, gx = np.gradient(Hg, CELL)
    nrm = np.dstack([-gx, np.ones_like(Hg), -gy]); nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    L = np.array([0.5, 0.6, 0.62]); L /= np.linalg.norm(L)
    sh = np.clip((nrm * L[[0, 1, 2]]).sum(2), 0, 1)
    img = (0.25 + 0.75 * sh)
    c = np.dstack([img * 0.85, img * 0.7, img * 0.55])
    if extra is not None: c[extra] = c[extra] * 0.5 + np.array([0.0, 0.2, 0.5]) * 0.5
    Image.fromarray((np.flipud(np.clip(c, 0, 1)) * 255).astype(np.uint8)).save(path)


def main():
    t0 = time.time(); WORK.mkdir(exist_ok=True)
    rec = dict(params=P, grid=dict(n=N, cell=CELL, origin=ORG))
    X, Z = grid()
    old = old_surface(); rec['old_cover'] = float(np.isfinite(old).mean())
    print('old raster', time.time() - t0, flush=True)
    geo = geology_r(X, Z)
    H, a, t, s = landform(X, Z, rec)
    print('landform', time.time() - t0, flush=True)
    # ---- Berms lock up front: the footprint keeps the original surface and acts as a fixed base level, so the
    # escarpment's gullies grade onto the Berms floor at its present height (no trench outside the toe)
    x0, x1, z0, z1 = BERMS
    dxo = np.maximum(np.maximum(x0 - X, X - x1), 0); dzo = np.maximum(np.maximum(z0 - Z, Z - z1), 0)
    outside = np.hypot(dxo, dzo)                                       # 0 inside the footprint
    inside = np.minimum(np.minimum(X - x0, x1 - X), np.minimum(Z - z0, z1 - Z))  # >0 inside
    w = smoothstep(0.75, 7.0, outside)
    have_old = np.isfinite(old)
    oldz = np.where(have_old, old, H)
    H = oldz + (H - oldz) * w
    # stream-power incision on a 2 m grid: drainage to the city basin (t < 6 m) and to the grid border
    k = int(P['sp_cell'] / CELL)
    Hc = np.ascontiguousarray(H[::k, ::k]).astype(np.float64)
    tc = t[::k, ::k]
    outlet = (tc < 6.0) | (outside[::k, ::k] == 0)
    outlet[0, :] = outlet[-1, :] = outlet[:, 0] = outlet[:, -1] = True
    erod = np.ascontiguousarray((0.75 + 0.5 * (0.5 + 0.5 * noise.fbm(X[::k, ::k], Z[::k, ::k], 61, 80.0, 3))) * w[::k, ::k])
    H0c = Hc.copy()
    area = stream_power.incise(Hc, outlet, np.zeros_like(Hc), erod, P['sp_K'], P['sp_m'], P['sp_dt'], P['sp_iters'], P['sp_diff'], P['sp_cell'], P['sp_area_cap'])
    # keep the skyline: restore each massif's local peak height (62 m window) to the envelope's, valleys stay cut
    pk0 = ndimage.maximum_filter(H0c + 1.8, size=31); pk1 = ndimage.maximum_filter(Hc + 1.8, size=31)
    ratio = ndimage.gaussian_filter(np.clip(pk0 / np.maximum(pk1, 0.5), 1.0, P['peak_restore_max']), 12)
    Hc = (Hc + 1.8) * ratio - 1.8
    dc = Hc - H0c
    rec['incision'] = dict(min=float(dc.min()), p1=float(np.percentile(dc, 1)), max=float(dc.max()))
    yy = np.arange(N) / k
    dcu = ndimage.map_coordinates(dc, np.meshgrid(yy, yy, indexing='ij'), order=3, mode='nearest')
    H = H + dcu
    print('stream power', time.time() - t0, rec['incision'], flush=True)
    # face gullies: a second, 1 m stream-power pass with a lower area exponent incises the short escarpment faces
    outlet1 = (t < 6.0) | (outside == 0); outlet1[0, :] = outlet1[-1, :] = outlet1[:, 0] = outlet1[:, -1] = True
    erod1 = np.ascontiguousarray((0.7 + 0.6 * (0.5 + 0.5 * noise.fbm(X, Z, 62, 40.0, 3))) * w)
    gy, gx = np.gradient(blur(H, 2.0), CELL); slope0 = np.hypot(gx, gy)
    seed = P['gully_seed'] * (noise.fbm(X, Z, 63, 13.0, 3) + 0.5 * noise.fbm(X, Z, 64, 5.0, 2))   # lets flow converge
    H = np.ascontiguousarray(H + seed * smoothstep(0.15, 0.6, slope0) * w)
    H1 = H.copy()
    stream_power.incise(H, outlet1, np.zeros_like(H), erod1, P['sp1_K'], P['sp1_m'], 1.0, P['sp1_iters'], P['sp1_diff'], CELL)
    rec['incision1'] = dict(min=float((H - H1).min()), p1=float(np.percentile(H - H1, 1)))
    print('stream power 1 m', time.time() - t0, rec['incision1'], flush=True)
    Ht, hard = terrace(H, X, Z, geo, rec)
    H = H + (Ht - H) * w
    mount = smoothstep(1.0, 6.0, H + 1.8) * (t > 8) * w
    # light droplet pass: rounds the bench edges, cuts rills and drops small fans at the feet
    erode(H, mount.astype(np.float64), P['drops_fine'], 8, 2, 0.05, P['erode_capacity'], 0.01, P['erode_speed'], P['deposit_speed'], 0.015, 4.0, 40)
    print('fine erosion', time.time() - t0, flush=True)
    H = thermal(H, smoothstep(2, 6, H + 1.8) * (1 - hard) * 0.6 * w, 37.0, 6)
    gy, gx = np.gradient(H, CELL); slope = np.hypot(gx, gy)
    H = H + P['detail_amp'] * noise.fbm(X, Z, 51, 7.0, 3) * smoothstep(0.3, 1.0, slope) * mount
    # rock outcrops and buttresses on steep ground (ridged, 9-16 m), strongest on hard beds
    rk = noise.ridged(X, Z, 52, 14.0, 3, gain=1.5) - 0.45
    H = H + P['rock_detail'] * rk * smoothstep(0.35, 1.1, slope) * mount * (0.5 + 0.5 * hard)
    # ---- final lock: the original surface at the Berms ground footprint (+0.75 m), blended to new by 7 m
    # no moat outside the playable edge: within 20 m of the footprint the new ground may fall at most 0.3 m per metre
    # below the original surface
    floor_ok = np.where(have_old & (outside < 20), oldz - 0.3 * np.maximum(outside - 0.75, 0), -1e9)
    H = np.maximum(H, floor_ok)
    Hf = np.where(have_old, old + (H - np.where(have_old, old, 0)) * w, H)
    Hf = np.where(t < 0, -1.8, Hf)                                     # under the city (hidden): flat at the old rim level
    drop = (inside > 3.0)
    rec['lock'] = dict(berms=BERMS, berms_exact_margin=0.75, berms_blend_to=7.0, drop_inside=3.0)
    print('locks', time.time() - t0, flush=True)
    sun, sky = bake_light(Hf, X, Z)
    print('bake', time.time() - t0, flush=True)
    dev = np.where(have_old, Hf - old, np.nan)
    rec['stats'] = dict(h_min=float(Hf.min()), h_max=float(Hf.max()), old_max=float(np.nanmax(old)),
                        dev_p1=float(np.nanpercentile(dev, 1)), dev_p99=float(np.nanpercentile(dev, 99)),
                        lock_max_dev=float(np.nanmax(np.abs(np.where(w == 0, dev, 0)))),
                        sun_mean=float(sun.mean()), sky_min=float(sky.min()), seconds=time.time() - t0)
    np.savez_compressed(WORK / 'heightfield.npz', H=Hf.astype(np.float32), sun=sun.astype(np.float32), sky=sky.astype(np.float32),
                        old=old.astype(np.float32), w=w.astype(np.float32), drop=drop, t=t.astype(np.float32))
    (HERE / 'heightfield.json').write_text(json.dumps(rec, indent=1))
    hillshade(Hf, WORK / 'hillshade.png', extra=drop)
    print(json.dumps(rec['stats'], indent=1))


if __name__ == '__main__':
    main()
