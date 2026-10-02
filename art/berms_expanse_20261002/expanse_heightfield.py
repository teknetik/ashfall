#!/usr/bin/env python3
"""Outer Berms expansion heightfield (2 Oct 2026), derived from art/basin_mountains_20261001/basin_heightfield.py.

Carl: "expand the outer berms, push back the mountains if required" ... "it needs to be quite big and spread out like
500m". Same generator, layout family and erosion as the basin mountains, on a larger grid (footprint.json `grid`,
2049 x 2049 at 1 m) with these changes:

1. **Bowl.** `bowl` is a hand-drawn outline of the new mountain foot, about 500 m across, warped by noise into bays
   and promontories. New mountains grow outward from it with the original generator's profile (front escarpment with
   talus and a cliff band, crest ring, distant ring, tableland tops), their amplitudes varied by noise along the
   outline instead of the original's angular sines. West of `west.blend_x[1]` they replace the original ring; between
   there and `west.blend_x[0]` they merge with it (smooth max), and east of the gate nothing changes. (A first try
   pushed the original ring outward radially; it stretched every ridge into a circular arc and was dropped.)
2. **Depot rise.** The old Berms ground climbs 7-11 m on its south-west edge (the depot conveyor stands on that slope);
   the old footprint's edge heights are carried outward and fall off with distance, so the slope becomes a spur.
3. **Floor.** Inside the `playable` polygon: a rolling floor (macro swells, dunes, rising gently toward the western
   fans), two dry washes, and rock outcrops (cover and landmarks); the mountains may only start at the polygon edge.
   Erosion runs over everything outside the old footprint, so gullies and fans come off the new mountain fronts and
   the outcrops.
4. The original Berms footprint keeps the OLD surface exactly (same lock as the basin pass), so every installed object
   stays grounded and the old Berms ground mesh is not touched.

`playable` is derived on every run: the warped bowl inset by `outline.inset`, traced and simplified, written back to
footprint.json. `--outline` stops after the landform (work/landform.npz) for a quick look.
Run (memory-capped):  $O/heavy.sh uv run --with numpy --with numba --with scipy --with pillow --with matplotlib python expanse_heightfield.py [--outline]
Output: work/heightfield.npz (+ work/hillshade.png), heightfield.json
"""
import argparse, json, math, sys, time
from pathlib import Path
import numpy as np
from scipy import ndimage
from matplotlib.path import Path as MPath

HERE = Path(__file__).resolve().parent
BASIN = HERE.parent / 'basin_mountains_20261001'
sys.path.insert(0, str(BASIN))
import basin_heightfield as bh  # noqa: E402
import noise, stream_power, glb_io  # noqa: E402

WORK = HERE / 'work'
FPATH = HERE / 'footprint.json'
FP = json.loads(FPATH.read_text())
G = FP['grid']; N, CELL, OX, OZ = int(G['n']), float(G['cell']), float(G['ox']), float(G['oz'])
smoothstep = bh.smoothstep


def save_fp():
    """footprint.json with one line per list of numbers (readable diffs)."""
    import re
    txt = json.dumps(FP, indent=1)
    txt = re.sub(r'\[\s*(-?[\d.]+),\s*(-?[\d.]+)\s*\]', r'[\1, \2]', txt)
    txt = re.sub(r'\[\s*(-?[\d.]+),\s*(-?[\d.]+),\s*(-?[\d.]+),\s*(-?[\d.]+)\s*\]', r'[\1, \2, \3, \4]', txt)
    FPATH.write_text(txt + '\n')


def grid():
    return np.meshgrid(OX + np.arange(N) * CELL, OZ + np.arange(N) * CELL)      # [j, i]


def old_surface():
    """The original DesertBasin surface rastered on this grid (NaN where it has no triangles)."""
    js, ms = glb_io.meshes(bh.OLD_GLB)
    out = np.full((N, N), np.nan)
    for m in ms:
        Pm = m['P']
        # bh.raster_old uses one origin for both axes; shift X so the Z origin serves for X too
        bh.raster_old(-Pm[:, 0] + (OZ - OX), Pm[:, 1], Pm[:, 2], m['I'], N, OZ, CELL, out)
    return out


def bilinear(Hg, X, Z):
    return ndimage.map_coordinates(Hg, [(Z - OZ) / CELL, (X - OX) / CELL], order=1, mode='nearest')


def bake_light(Hg, X, Z):
    """As bh.bake_light (R noon sun visibility for the saved key, G sky access) on this grid."""
    obstruction = np.full(Hg.shape, -1e9, np.float32)
    for step in list(np.arange(2, 40, 2.0)) + list(np.arange(40, 160, 5.0)):
        hs = bilinear(Hg, X + bh.SUN_XZ[0] * step, Z + bh.SUN_XZ[1] * step)
        obstruction = np.maximum(obstruction, hs - Hg - bh.SUN_TAN * step - 1.2)
    sun = 1 - np.clip(np.maximum(obstruction, 0) / 2, 0, 1)
    occ = np.zeros(Hg.shape, np.float32)
    for k in range(8):
        ang = k * math.pi / 4
        dx, dz = math.cos(ang), math.sin(ang)
        hor = np.full(Hg.shape, -1e9, np.float32)
        for d in (4.0, 8.0, 16.0, 32.0, 64.0):
            hor = np.maximum(hor, (bilinear(Hg, X + dx * d, Z + dz * d) - Hg) / d)
        occ += np.clip(hor, 0, 1) * 0.0275
    return sun, 1 - occ


def bowl_fields(X, Z):
    """Warped bowl mask (inside = floor side of the mountain foot) and the distance outside it (m)."""
    inside, d_in, d_out = polygon_fields(X, Z, FP['bowl'])
    bw = FP['bowl_warp']
    sdf = d_in - d_out + bw['a1'] * noise.fbm(X, Z, 201, bw['w1'], 3) + bw['a2'] * noise.fbm(X, Z, 202, bw['w2'], 3)
    sdf = np.where(X > -62, d_in - d_out, sdf)                 # the city wall side stays straight
    bowl = sdf > 0
    j, i = int(round((0 - OZ) / CELL)), int(round((-80 - OX) / CELL))
    lab, _ = ndimage.label(bowl); bowl = ndimage.binary_fill_holes(lab == lab[j, i])
    d = (ndimage.distance_transform_edt(~bowl) * CELL).astype(np.float32)
    return bowl, d


def west_landform(X, Z, d, rec):
    """Mountains rising outward from the bowl edge (d = metres outside it), same envelope family as bh.landform but
    with amplitudes and ring distances varied by noise (true coordinates, so no ridge is stretched)."""
    W = FP['west']; P_ = bh.P
    tw_near = d + 18.0 * noise.fbm(X, Z, 211, 90.0, 4) + 6.0 * noise.fbm(X, Z, 212, 28.0, 3)
    tw_far = d + 48.0 * noise.fbm(X, Z, 213, 170.0, 4) + 12.0 * noise.fbm(X, Z, 214, 45.0, 3)
    front = W['front'] + 5 * noise.fbm(X, Z, 215, 220.0, 2)
    summit = np.clip(W['summit'] + W['summit_var'] * noise.fbm(X, Z, 216, 170.0, 3), 24, 60)
    sv = tw_near - front
    g_near = np.exp(-((sv - 15) / 30) ** 2) * smoothstep(P_['rise_lo'], P_['rise_hi'], sv)   # the front stands right at the foot
    crest = W['crest'] + W['crest_var'] * noise.fbm(X, Z, 217, 300.0, 2)
    g_far = np.exp(-((tw_far - crest) / 57) ** 2)
    g_dist = np.exp(-((tw_far - W['distant']) / 67) ** 2)
    A_far = np.maximum(10, 62 + 42 * noise.fbm(X, Z, 218, 240.0, 3))
    A_dist = np.maximum(15, 72 + 34 * noise.fbm(X, Z, 219, 300.0, 3))
    cn = P_['cliff_at'] + P_['cliff_wander'] * noise.fbm(X, Z, 16, 45.0, 3)
    dome = 1 + P_['dome'] * noise.fbm(X, Z, 17, 70.0, 3)
    def table(g):
        tf = P_['talus_frac']
        prof = tf * smoothstep(0.02, cn - P_['cliff_w'], g) + (1 - tf) * smoothstep(cn - P_['cliff_w'], cn + P_['cliff_w'], g)
        return (1 - P_['table_mix']) * g + P_['table_mix'] * prof * (0.85 + 0.15 * g) * dome
    base = np.maximum(np.maximum(summit * table(g_near), A_far * table(g_far)), A_dist * table(g_dist))
    base = base * (1 + P_['seed_relief'] * noise.fbm(X, Z, 15, 110.0, 4))
    apron = (2 + 3 * (0.5 + 0.5 * noise.fbm(X, Z, 31, 45.0, 3))) * np.minimum(1, d / 15)
    h = bh.smax(apron + 0.35 * noise.fbm(X, Z, 32, 18.0, 3), base, 2.0)
    H = -1.8 + h * smoothstep(0, 8, d) * .66
    rec['west_envelope_max'] = float(H.max())
    return H


def playable_from_bowl(X, Z, bowl, rec):
    """The walkable floor: the warped bowl inset by outline.inset, traced and simplified (Douglas-Peucker)."""
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    o = FP['outline']
    # inset from the mountain foot only: the city wall side (x > -62) is not an edge
    region = (ndimage.distance_transform_edt(bowl | (X > -62)) * CELL > o['inset']) & bowl
    j, i = int(round((0 - OZ) / CELL)), int(round((-80 - OX) / CELL))
    lab, _ = ndimage.label(region); region = lab == lab[j, i]
    fig = plt.figure(); cs = plt.contour(X, Z, region.astype(float), levels=[0.5]); plt.close(fig)
    seg = np.asarray(max(cs.allsegs[0], key=len))
    def dp(pts, eps):
        if len(pts) < 3: return pts
        a, b = pts[0], pts[-1]; ab = b - a; L = np.hypot(*ab) + 1e-9
        dd = np.abs(ab[0] * (pts[:, 1] - a[1]) - ab[1] * (pts[:, 0] - a[0])) / L
        k = int(np.argmax(dd))
        if dd[k] > eps: return np.vstack([dp(pts[:k + 1], eps)[:-1], dp(pts[k:], eps)])
        return np.array([a, b])
    far = int(np.argmax(np.hypot(seg[:, 0] - seg[0, 0], seg[:, 1] - seg[0, 1])))
    poly = np.vstack([dp(seg[:far + 1], o['simplify'])[:-1], dp(seg[far:], o['simplify'])[:-1]])
    poly = [[round(float(x), 1), round(float(z), 1)] for x, z in poly]
    poly = [[-60.0 if x > -61.5 else x, z] for x, z in poly]        # the east edge is the city wall line
    FP['playable'] = poly
    save_fp()
    rec['playable'] = dict(points=len(poly), area_m2=float(region.sum() * CELL * CELL))
    print('playable', rec['playable'], flush=True)


def polygon_fields(X, Z, poly):
    path = MPath(np.array(poly, float))
    inside = path.contains_points(np.stack([X.ravel(), Z.ravel()], 1)).reshape(X.shape)
    d_in = (ndimage.distance_transform_edt(inside) * CELL).astype(np.float32)
    d_out = (ndimage.distance_transform_edt(~inside) * CELL).astype(np.float32)
    return inside, d_in, d_out


def wash_depth(X, Z, washes):
    """Dry washes: meandering channels (centre lines warped by noise), widening downstream, fading in and out."""
    out = np.zeros_like(X)
    Xw = X + 13.0 * noise.fbm(X, Z, 95, 75.0, 3); Zw = Z + 13.0 * noise.fbm(X, Z, 96, 75.0, 3)
    for wsh in washes:
        pts = np.array(wsh['pts'], float)
        d = np.full(X.shape, 1e9); along = np.zeros_like(X); acc = 0.0
        total = sum(float(np.hypot(*(pts[k + 1] - pts[k]))) for k in range(len(pts) - 1))
        for k in range(len(pts) - 1):
            a, b = pts[k], pts[k + 1]; ab = b - a; L = float(np.hypot(*ab))
            t = np.clip(((Xw - a[0]) * ab[0] + (Zw - a[1]) * ab[1]) / (L * L), 0, 1)
            dd = np.hypot(Xw - (a[0] + ab[0] * t), Zw - (a[1] + ab[1] * t))
            m = dd < d; d = np.where(m, dd, d); along = np.where(m, acc + t * L, along); acc += L
        f = along / total
        width = wsh['width'] * (0.75 + 0.5 * f) * (1 + 0.3 * noise.fbm(X, Z, 91, 40.0, 2))
        depth = wsh['depth'] * (0.8 + 0.4 * noise.fbm(X, Z, 92, 60.0, 2)) * smoothstep(0.0, 0.08, f) * (1 - smoothstep(0.85, 1.0, f))
        # flat sandy bed with cut banks (not a V)
        q = np.clip(d / np.maximum(width, 1), 0, 1.6)
        prof = 1 - smoothstep(0.45, 1.0, q)
        out = np.maximum(out, depth * prof)
    return out


def outcrop_height(X, Z, rocks):
    """Buttes and knolls: two or three overlapping warped lobes each, with the generator's tableland profile (talus
    apron, cliff band, domed caprock) so they read as eroded sandstone remnants, not ellipses."""
    P_ = bh.P
    out = np.zeros_like(X)
    warp1 = noise.fbm(X, Z, 93, 22.0, 3); warp2 = noise.fbm(X, Z, 94, 7.0, 2)
    cn = P_['cliff_at'] + P_['cliff_wander'] * noise.fbm(X, Z, 16, 45.0, 3)
    dome = 1 + 0.25 * noise.fbm(X, Z, 97, 18.0, 3)
    for n, r in enumerate(rocks):
        rng = np.random.default_rng(__import__('zlib').crc32(r['name'].encode()))
        lobes = [(0.0, 0.0, 1.0, 1.0)] + [(float(rng.uniform(-0.7, 0.7)), float(rng.uniform(-0.6, 0.6)), float(rng.uniform(0.45, 0.7)), float(rng.uniform(0.6, 0.9))) for _ in range(2)]
        c, s = math.cos(math.radians(r['yaw'])), math.sin(math.radians(r['yaw']))
        for (ou, ov, sc, hs) in lobes:
            cx = r['x'] + (ou * r['r'] * r['elong']) * c + (ov * r['r']) * s
            cz = r['z'] - (ou * r['r'] * r['elong']) * s + (ov * r['r']) * c
            u = ((X - cx) * c - (Z - cz) * s) / (r['r'] * r['elong'] * sc); v = ((X - cx) * s + (Z - cz) * c) / (r['r'] * sc)
            d = np.hypot(u, v) * (1 + 0.45 * warp1 + 0.16 * warp2)
            g = np.clip(1 - d, 0, 1)
            tf = 0.62                                          # mostly scree apron, a short cliff band near the top
            cnr = cn + 0.15
            prof = tf * smoothstep(0.0, cnr - 0.08, g) ** 1.3 + (1 - tf) * smoothstep(cnr - 0.08, cnr + 0.1, g)
            prof = 0.35 * g + 0.65 * prof * (0.85 + 0.15 * g) * dome
            out = np.maximum(out, r['h'] * hs * prof)
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--outline', action='store_true'); a = ap.parse_args()
    t0 = time.time(); WORK.mkdir(exist_ok=True)
    P_ = bh.P
    rec = dict(params=P_, footprint={k: v for k, v in FP.items() if k != 'playable'}, playable_points=len(FP['playable']))
    X, Z = grid()
    H0, _, t, _ = bh.landform(X, Z, rec)                    # the original ring (unchanged east of the gate)
    bowl, d_bowl = bowl_fields(X, Z)
    playable_from_bowl(X, Z, bowl, rec)
    Hw = west_landform(X, Z, d_bowl, rec)
    bx0, bx1 = FP['west']['blend_x']
    mW = smoothstep(bx0, bx1, X)                              # 0 near the city, 1 in the far west
    fade = smoothstep(0, 60, d_bowl)                          # the original ring is cut back from the bowl
    H0c = -1.8 + (H0 + 1.8) * fade * (1 - mW)
    Hw = np.where(X < -59.5, -1.8 + (Hw + 1.8) * smoothstep(-60, -110, X), -1.8)
    H = bh.smax(H0c, Hw, 3.0)
    del H0c, H0
    rec['bowl'] = dict(area_m2=float(bowl.sum() * CELL * CELL), extent_x=[float(X[bowl].min()), float(X[bowl].max())], extent_z=[float(Z[bowl].min()), float(Z[bowl].max())])
    print('landform (bowl)', round(time.time() - t0, 1), rec['bowl'], flush=True)
    if a.outline:
        np.savez_compressed(WORK / 'landform.npz', H=H.astype(np.float32), grid=np.array([N, CELL, OX, OZ])); return
    old = old_surface(); rec['old_cover'] = float(np.isfinite(old).mean())
    geo = bh.geology_r(X, Z)
    # ---- old Berms footprint: exact lock and its edge carried outward as the depot rise
    x0, x1, z0, z1 = FP['old']
    dxo = np.maximum(np.maximum(x0 - X, X - x1), 0); dzo = np.maximum(np.maximum(z0 - Z, Z - z1), 0)
    outside = np.hypot(dxo, dzo); del dxo, dzo
    inside_old = np.minimum(np.minimum(X - x0, x1 - X), np.minimum(Z - z0, z1 - Z))
    w = smoothstep(0.75, 7.0, outside)
    have_old = np.isfinite(old)
    oldz = np.where(have_old, old, H)
    in_old = outside == 0
    _, (ji, ii) = ndimage.distance_transform_edt(~in_old, return_indices=True)
    edge_raw = oldz[ji, ii]; del ji, ii
    lockz = np.where(in_old, oldz, edge_raw)
    edge_h = ndimage.gaussian_filter(edge_raw, 3.0 / CELL); del edge_raw
    floor0 = -1.2
    rise = np.maximum(edge_h - floor0, 0) * (1 + 0.12 * noise.fbm(X, Z, 72, 14.0, 3))
    L = (6.0 + 1.3 * rise) * (1 + 0.4 * noise.fbm(X, Z, 71, 24.0, 3))
    spur = floor0 + rise * np.cos(np.clip(outside / np.maximum(L, 4.0), 0, 1) * np.pi / 2) ** 2
    del rise, L, edge_h
    inF, dF_in, dF_out = polygon_fields(X, Z, FP['playable'])
    # ---- the floor: macro swells, dunes, rising toward the western fans; washes; outcrops
    fl = FP['floor']
    gx0, gz0 = -60.0, 0.0                                  # the West Gate
    dist_gate = np.hypot(X - gx0, Z - gz0)
    floorH = (floor0 + 0.4 + fl['west_rise'] * smoothstep(60, 520, dist_gate) ** 1.6
              + fl['macro'] * noise.fbm(X, Z, 101, 160.0, 3) * smoothstep(30, 120, dist_gate)
              + fl['dunes'] * np.abs(noise.fbm(X, Z, 102, 38.0, 3)) * smoothstep(60, 160, dist_gate)
              + fl['small'] * noise.fbm(X, Z, 103, 9.0, 2))
    del dist_gate
    floorH = floorH - wash_depth(X, Z, FP['washes'])
    rocks = outcrop_height(X, Z, FP['outcrops'])
    floorH = floorH + rocks
    floorH = np.maximum(floorH, spur)                       # the depot rise stands on the floor
    rocky = rocks > 1.0
    capm = inF & ~in_old
    ramp = np.maximum(fl['edge_ramp'] - dF_in, 0) * fl['edge_slope']
    Hin = np.where(dF_in >= fl['edge_ramp'], floorH, np.minimum(np.maximum(H, floorH), floorH + ramp))
    H = np.where(capm, Hin, H); del Hin
    near = (~inF) & (dF_out < 25)
    H = np.where(near, np.maximum(H, floorH - 0.5), H)     # no trench just outside the edge
    H = lockz + (H - lockz) * w
    print('floor', round(time.time() - t0, 1), flush=True)
    # ---- stream-power incision (2 m): drainage to the city basin, the old footprint, the open floor and the grid
    # border; mountain fronts, outcrops and the spur erode, the floor far from them is base level
    on_floor = inF & (dF_in > 30) & ~rocky & (spur < floor0 + 1.0)
    k = int(P_['sp_cell'] / CELL)
    Hc = np.ascontiguousarray(H[::k, ::k]).astype(np.float64)
    tc = t[::k, ::k]
    outlet = (tc < 6.0) | (outside[::k, ::k] == 0) | on_floor[::k, ::k]
    outlet[0, :] = outlet[-1, :] = outlet[:, 0] = outlet[:, -1] = True
    erod = np.ascontiguousarray((0.75 + 0.5 * (0.5 + 0.5 * noise.fbm(X[::k, ::k], Z[::k, ::k], 61, 80.0, 3))) * w[::k, ::k])
    H0c = Hc.copy()
    stream_power.incise(Hc, outlet, np.zeros_like(Hc), erod, P_['sp_K'], P_['sp_m'], P_['sp_dt'], P_['sp_iters'], P_['sp_diff'], P_['sp_cell'], P_['sp_area_cap'])
    pk0 = ndimage.maximum_filter(H0c + 1.8, size=31); pk1 = ndimage.maximum_filter(Hc + 1.8, size=31)
    ratio = ndimage.gaussian_filter(np.clip(pk0 / np.maximum(pk1, 0.5), 1.0, P_['peak_restore_max']), 12)
    Hc = (Hc + 1.8) * ratio - 1.8
    dc = Hc - H0c
    rec['incision'] = dict(min=float(dc.min()), p1=float(np.percentile(dc, 1)), max=float(dc.max()))
    yy = np.arange(N) / k
    dcu = ndimage.map_coordinates(dc, np.meshgrid(yy, yy, indexing='ij'), order=3, mode='nearest')
    H = H + dcu; del dcu, Hc, H0c, dc, pk0, pk1, ratio, erod
    print('stream power', round(time.time() - t0, 1), rec['incision'], flush=True)
    outlet1 = (t < 6.0) | (outside == 0) | on_floor; outlet1[0, :] = outlet1[-1, :] = outlet1[:, 0] = outlet1[:, -1] = True
    erod1 = np.ascontiguousarray((0.7 + 0.6 * (0.5 + 0.5 * noise.fbm(X, Z, 62, 40.0, 3))) * w)
    gy, gx = np.gradient(bh.blur(H, 2.0), CELL); slope0 = np.hypot(gx, gy); del gy, gx
    seed = P_['gully_seed'] * (noise.fbm(X, Z, 63, 13.0, 3) + 0.5 * noise.fbm(X, Z, 64, 5.0, 2))
    H = np.ascontiguousarray(H + seed * smoothstep(0.15, 0.6, slope0) * w); del seed, slope0
    H1 = H.copy()
    stream_power.incise(H, outlet1, np.zeros_like(H), erod1, P_['sp1_K'], P_['sp1_m'], 1.0, P_['sp1_iters'], P_['sp1_diff'], CELL)
    rec['incision1'] = dict(min=float((H - H1).min()), p1=float(np.percentile(H - H1, 1))); del H1, erod1, outlet1
    print('stream power 1 m', round(time.time() - t0, 1), flush=True)
    Ht, hard = bh.terrace(H, X, Z, geo, rec); del geo
    H = H + (Ht - H) * w; del Ht
    mount = smoothstep(1.0, 6.0, H - np.minimum(floorH - rocks, 6) + 0.2) * w
    drops = int(P_['drops_fine'] * (N * N) / (1025 * 1025))
    bh.erode(H, mount.astype(np.float64), drops, 8, 2, 0.05, P_['erode_capacity'], 0.01, P_['erode_speed'], P_['deposit_speed'], 0.015, 4.0, 40)
    print('fine erosion', round(time.time() - t0, 1), flush=True)
    H = bh.thermal(H, smoothstep(2, 6, H + 1.8) * (1 - hard) * 0.6 * w * ((~inF) | rocky), 37.0, 6)
    gy, gx = np.gradient(H, CELL); slope = np.hypot(gx, gy); del gy, gx
    H = H + P_['detail_amp'] * noise.fbm(X, Z, 51, 7.0, 3) * smoothstep(0.3, 1.0, slope) * mount
    rk = noise.ridged(X, Z, 52, 14.0, 3, gain=1.5) - 0.45
    H = H + P_['rock_detail'] * rk * smoothstep(0.35, 1.1, slope) * mount * (0.5 + 0.5 * hard); del rk, slope, mount, hard
    # ---- final playable floor: walkable relief (rills from the fans kept shallow); outcrops and the spur keep their
    # eroded form; the edge ramp limits how steeply the mountain foot rises inside the polygon
    cap = floorH + ramp
    keep = rocky | (spur > floor0 + 1.0)
    Hfl = np.where(keep, H, np.minimum(H, cap + 0.35))
    Hfl = np.maximum(Hfl, floorH - np.where(keep, 2.5, 0.9))   # rills, not pits or trenches
    soft = smoothstep(0, 6, dF_in)
    H = np.where(capm, H + (Hfl - H) * soft, H); del Hfl, cap
    floor_ok = np.where(outside < 45, spur - 0.6 - 0.2 * np.maximum(spur - floor0, 0), -1e9)
    H = np.maximum(H, floor_ok); del floor_ok
    Hf = lockz + (H - lockz) * w
    Hf = np.where(t < 0, -1.8, Hf)
    ground_in = dF_out <= FP['skirt']
    d_ground_in = ndimage.distance_transform_edt(ground_in) * CELL
    drop = (d_ground_in > 3.0) | (inside_old > 3.0)
    rec['lock'] = dict(berms=FP['old'], berms_exact_margin=0.75, berms_blend_to=7.0, drop_inside=3.0, ground='playable + skirt')
    print('bake', round(time.time() - t0, 1), flush=True)
    Hf32 = Hf.astype(np.float32)
    sun, sky = bake_light(Hf32, X.astype(np.float32), Z.astype(np.float32))
    dev = np.where(have_old & in_old, Hf - old, np.nan)
    gy, gx = np.gradient(Hf, CELL); sl = np.degrees(np.arctan(np.hypot(gx, gy)))
    walk = inF & ~in_old & (dF_in > 10) & ~rocky & ~(spur > floor0 + 1.0)
    rec['stats'] = dict(h_min=float(Hf.min()), h_max=float(Hf.max()),
                        lock_max_dev=float(np.nanmax(np.abs(dev))),
                        playable_h=[float(Hf[inF].min()), float(np.percentile(Hf[inF], 50)), float(Hf[inF].max())],
                        floor_slope_p50_p95_p99_max=[float(v) for v in np.percentile(sl[walk], [50, 95, 99, 100])],
                        playable_area_m2=float(inF.sum() * CELL * CELL), old_area_m2=float(in_old.sum() * CELL * CELL),
                        playable_extent=dict(x=[float(X[inF].min()), float(X[inF].max())], z=[float(Z[inF].min()), float(Z[inF].max())]),
                        seconds=time.time() - t0)
    np.savez_compressed(WORK / 'heightfield.npz', H=Hf32, sun=sun.astype(np.float32), sky=sky.astype(np.float32),
                        old=old.astype(np.float32), w=w.astype(np.float32), drop=drop, t=t.astype(np.float32),
                        playable=inF, d_in=dF_in, d_out=dF_out, rocks=rocks.astype(np.float32), spur=spur.astype(np.float32),
                        d_bowl=d_bowl, grid=np.array([N, CELL, OX, OZ]))
    (HERE / 'heightfield.json').write_text(json.dumps(rec, indent=1))
    print(json.dumps(rec['stats'], indent=1))


if __name__ == '__main__':
    main()
