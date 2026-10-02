#!/usr/bin/env python3
"""Meshes for the Outer Berms expansion from work/heightfield.npz (2 Oct 2026). Writes two GLBs straight from numpy
(glb_write.py; no Blender step):

* **BasinExpanse.glb** — the mountain ring around the city and the new western bowl, replacing BasinMountains.glb in
  the scene. One global RTIN (basin_mountains_20261001/basin_mesh.py) over the 2049 x 2049 field with the same
  view-weighted error, now measured from the city rectangle AND the playable floor; triangles under the city, under
  the walkable ground (more than 3 m inside it) and beyond the outer edge are dropped, with full refinement along those
  cut lines. Split into spatial cells (`BasinExpanse_N<x>_<z>` 128 m within 640 m of the city centre,
  `BasinExpanse_F<x>_<z>` 256 m beyond) so camera and shadow-cascade culling skip distant terrain; chunks share every
  border vertex, normal and colour.
* **BermsExpanseGround.glb** — the walkable ground (playable polygon + skirt, outside the original Berms footprint,
  whose old mesh stays): RTIN on a 513 x 513 window at 1 m with a fixed vertical error (LOD0 2.5 cm, LOD1 12 cm),
  fully refined along the old footprint boundary (vertices meet the old mesh's 1 m edge exactly) and along the 64 m tile
  borders (neighbouring tiles join at any LOD mix), split into tiles `Ground_ix_iz_LODk`. Heights are the field + 4 cm,
  like the old Berms ground over the basin.

Per vertex: normal from the field smoothed at the vertex's triangle scale, COLOR (R sun visibility, G sky access,
B = A = 1, as the terrain shaders read), UV0 = XZ / 16.
Run: $O/heavy.sh uv run --with numpy --with numba --with scipy --with matplotlib python expanse_mesh.py [--theta 0.0105] [--survey]
"""
import argparse, json, math, sys, time
from pathlib import Path
import numpy as np
from scipy import ndimage

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'basin_mountains_20261001')); sys.path.insert(0, str(HERE))
import basin_mesh as bm  # noqa: E402
from glb_write import write_glb  # noqa: E402

ROOT = Path('/home/teknetik/code/ao2')
WORK = HERE / 'work'
UNITY_ART = ROOT / 'unity/AthenHill/Assets/AthenHill/Art/BermsExpanse'
FP = json.loads((HERE / 'footprint.json').read_text())
CITY = (62.0, 48.0)
TILE = 64
SUB = dict(n=513, ox=-572.0, oz=-256.0)                   # ground window (whole metres, 512 m square)


def load():
    hf = np.load(WORK / 'heightfield.npz')
    N, CELL, OX, OZ = hf['grid']; N = int(N)
    X, Z = np.meshgrid(OX + np.arange(N) * CELL, OZ + np.arange(N) * CELL)
    return hf, N, float(CELL), float(OX), float(OZ), X, Z


def normals_at(Hs_list, idx, scale, shape):
    out = np.zeros((len(idx), 3))
    sigmas = [0.6, 1.2, 2.5, 5.0, 10.0]
    pick = np.clip(np.searchsorted(sigmas, scale * 0.5), 0, len(sigmas) - 1)
    for k in range(len(sigmas)):
        m = pick == k
        if not m.any(): continue
        gz, gx = Hs_list[k]
        n = np.stack([-gx.ravel()[idx[m]], np.ones(m.sum()), -gz.ravel()[idx[m]]], 1)
        out[m] = n / np.linalg.norm(n, axis=1, keepdims=True)
    return out


def grad_pyramid(H, cell):
    res = []
    for s in [0.6, 1.2, 2.5, 5.0, 10.0]:
        Hs = ndimage.gaussian_filter(H, s / cell, mode='nearest')
        gz, gx = np.gradient(Hs, cell); res.append((gz.astype(np.float32), gx.astype(np.float32)))
    return res


def vertex_scale(tris, Xf, Zf, n):
    el = np.zeros(n); cnt = np.zeros(n)
    for u, v in ((0, 1), (1, 2), (2, 0)):
        L = np.hypot(Xf[tris[:, u]] - Xf[tris[:, v]], Zf[tris[:, u]] - Zf[tris[:, v]])
        np.add.at(el, tris[:, u], L); np.add.at(cnt, tris[:, u], 1)
        np.add.at(el, tris[:, v], L); np.add.at(cnt, tris[:, v], 1)
    return el, cnt


def ground_region(hf, X, Z, cell):
    """Walkable ground mask (playable grown by the skirt) and the distance inside it (old footprint excluded)."""
    ground = (hf['d_out'] <= FP['skirt']) & (X <= -60.0)                # the ground ends at the city wall line
    x0, x1, z0, z1 = FP['old']
    old = (X >= x0) & (X <= x1) & (Z >= z0) & (Z <= z1)
    return ground, old


def build_basin(hf, N, CELL, OX, OZ, X, Z, theta, rec, survey=False):
    H = hf['H'].astype(np.float64); t = hf['t'].astype(np.float64); db = hf['d_bowl'].astype(np.float64)
    ground, old = ground_region(hf, X, Z, CELL)
    hidden = ground | old
    gin = ndimage.distance_transform_edt(hidden) * CELL                # metres inside the hidden region
    view = ((np.abs(X) <= CITY[0]) & (np.abs(Z) <= CITY[1])) | hf['playable']
    D = ndimage.distance_transform_edt(~view) * CELL
    W = 1.0 / np.maximum(D, 6.0)
    outer = ~((t < 440) | (db < 430))
    W[outer] = 0.0
    force = ((t > -1.5) & (t < 2.5)) | ((gin > 1.5) & (gin < 4.5))
    t0 = time.time()
    err = bm.rtin_errors(np.ascontiguousarray(H), np.ascontiguousarray(W), force.ravel())
    del W, force, D
    thetas = [theta] if not survey else [0.006, 0.008, 0.0105, 0.014, 0.02]
    for th in thetas:
        tris = bm.rtin_mesh(err, N, th)
        tf = t.ravel(); gf = gin.ravel(); dbf = db.ravel()
        ct = tf[tris].mean(1); cg = gf[tris].mean(1); cdb = dbf[tris].mean(1)
        keep = (ct > -0.75) & (cg < 3.0) & ((ct < 430) | (cdb < 420))
        tris = tris[keep]
        print('basin theta %.4f -> %d triangles (%.1f s)' % (th, len(tris), time.time() - t0), flush=True)
    if survey: return None
    rec['basin'] = dict(theta=theta, triangles=int(len(tris)))
    Xf, Zf, Hf = X.ravel(), Z.ravel(), H.ravel()
    used = np.unique(tris)
    el, cnt = vertex_scale(tris, Xf, Zf, N * N)
    scale = el[used] / np.maximum(cnt[used], 1)
    pyr = grad_pyramid(H, CELL)
    nrm = normals_at(pyr, used, scale, H.shape); del pyr
    sun = hf['sun'].ravel()[used]; sky = hf['sky'].ravel()[used]
    P = np.stack([Xf[used], Hf[used], Zf[used]], 1)
    C = np.stack([sun, sky, np.ones_like(sun), np.ones_like(sun)], 1)
    UV = np.stack([Xf[used] / 16.0, Zf[used] / 16.0], 1)
    remap = np.full(N * N, -1, np.int64); remap[used] = np.arange(len(used))
    T = remap[tris]
    cx = P[T, 0].mean(1); cz = P[T, 2].mean(1)
    # spatial chunks so camera and shadow-cascade culling skip what is far away: 128 m cells within 640 m of the city
    # centre, 256 m cells beyond (a sector split drew whole 550 m wedges into every cascade)
    far = np.hypot(cx, cz) > 640
    cell = np.where(far, 256.0, 128.0)
    gx = np.floor(cx / cell).astype(int); gz = np.floor(cz / cell).astype(int)
    keys = np.stack([far.astype(int), gx, gz], 1)
    objs = []; rec['basin']['chunks'] = {}
    for f, ix, iz in sorted(set(map(tuple, keys.tolist()))):
        if True:
            tt = T[(keys[:, 0] == f) & (keys[:, 1] == ix) & (keys[:, 2] == iz)]
            if len(tt) == 0: continue
            vu = np.unique(tt); rm = np.full(len(P), -1, np.int64); rm[vu] = np.arange(len(vu))
            name = 'BasinExpanse_%s%d_%d' % ('F' if f else 'N', ix, iz)
            objs.append(dict(name=name, P=P[vu], N=nrm[vu], C=C[vu], UV=UV[vu], I=rm[tt]))
            rec['basin']['chunks'][name] = dict(triangles=int(len(tt)), vertices=int(len(vu)),
                                                min=[round(float(v), 1) for v in P[vu].min(0)], max=[round(float(v), 1) for v in P[vu].max(0)])
    UNITY_ART.mkdir(parents=True, exist_ok=True)
    size = write_glb(UNITY_ART / 'BasinExpanse.glb', objs)
    rec['basin']['bytes'] = size
    print('basin glb', size, len(objs), 'chunks', flush=True)


def build_ground(hf, N, CELL, OX, OZ, X, Z, rec, survey=False):
    n, sx, sz = SUB['n'], SUB['ox'], SUB['oz']
    i0, j0 = int(round((sx - OX) / CELL)), int(round((sz - OZ) / CELL))
    sl = (slice(j0, j0 + n), slice(i0, i0 + n))
    H = hf['H'][sl].astype(np.float64) + 0.04
    Xs, Zs = X[sl], Z[sl]
    ground, old = ground_region(hf, X, Z, CELL); ground, old = ground[sl], old[sl]
    region = ground & ~old
    # full refinement along the old footprint's edge, the region's edge and every tile border
    x0, x1, z0, z1 = FP['old']
    on_old_edge = (((np.abs(Xs - x0) < 0.5) | (np.abs(Xs - x1) < 0.5)) & (Zs >= z0 - 0.5) & (Zs <= z1 + 0.5)) | \
                  (((np.abs(Zs - z0) < 0.5) | (np.abs(Zs - z1) < 0.5)) & (Xs >= x0 - 0.5) & (Xs <= x1 + 0.5))
    edge = region ^ ndimage.binary_erosion(region, iterations=2)
    tile_line = ((np.mod(Xs - sx, TILE) < 0.5) | (np.mod(Zs - sz, TILE) < 0.5))
    force = (on_old_edge | edge | tile_line) & ndimage.binary_dilation(region, iterations=2)
    W = np.ones_like(H)
    err = bm.rtin_errors(np.ascontiguousarray(H), np.ascontiguousarray(W), force.ravel())
    pyr = grad_pyramid(H, CELL)
    sun = hf['sun'][sl].ravel(); sky = hf['sky'][sl].ravel()
    Xf, Zf, Hf = Xs.ravel(), Zs.ravel(), H.ravel()
    rf = region.ravel()
    objs = []; rec['ground'] = dict(window=SUB, tile=TILE, lods={})
    for lod, maxe in enumerate([0.025, 0.12]):
        tris = bm.rtin_mesh(err, n, maxe)
        cxs = Xf[tris].mean(1); czs = Zf[tris].mean(1)
        # a triangle belongs to the ground if its centroid's nearest grid node is in the region
        ci = np.clip(np.round((cxs - sx) / CELL).astype(int), 0, n - 1); cj = np.clip(np.round((czs - sz) / CELL).astype(int), 0, n - 1)
        keep = rf[cj * n + ci]
        # strictly outside the old footprint (its edge vertices are shared, its interior belongs to the old mesh)
        keep &= ~((cxs > x0) & (cxs < x1) & (czs > z0) & (czs < z1))
        tris = tris[keep]
        print('ground LOD%d max error %.3f -> %d triangles' % (lod, maxe, len(tris)), flush=True)
        if survey: continue
        el, cnt = vertex_scale(tris, Xf, Zf, n * n)
        txi = np.floor((Xf[tris].mean(1) - sx) / TILE).astype(int); tzi = np.floor((Zf[tris].mean(1) - sz) / TILE).astype(int)
        lodrec = {}
        for key in sorted(set(zip(txi.tolist(), tzi.tolist()))):
            tt = tris[(txi == key[0]) & (tzi == key[1])]
            vu = np.unique(tt); rm = np.full(n * n, -1, np.int64); rm[vu] = np.arange(len(vu))
            scale = el[vu] / np.maximum(cnt[vu], 1)
            P = np.stack([Xf[vu], Hf[vu], Zf[vu]], 1)
            name = 'Ground_%d_%d_LOD%d' % (key[0], key[1], lod)
            objs.append(dict(name=name, P=P, N=normals_at(pyr, vu, scale, H.shape),
                             C=np.stack([sun[vu], sky[vu], np.ones(len(vu)), np.ones(len(vu))], 1),
                             UV=np.stack([Xf[vu] / 16.0, Zf[vu] / 16.0], 1), I=rm[tt]))
            lodrec[name] = dict(triangles=int(len(tt)), vertices=int(len(vu)))
        rec['ground']['lods'][lod] = dict(max_error=maxe, triangles=int(len(tris)), tiles=len(lodrec))
        rec['ground'].setdefault('tiles', {}).update(lodrec)
    if survey: return
    UNITY_ART.mkdir(parents=True, exist_ok=True)
    size = write_glb(UNITY_ART / 'BermsExpanseGround.glb', objs)
    rec['ground']['bytes'] = size
    print('ground glb', size, len(objs), 'objects', flush=True)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--theta', type=float, default=0.0105); ap.add_argument('--survey', action='store_true')
    ap.add_argument('--only', choices=['basin', 'ground'], default=None)
    a = ap.parse_args()
    hf, N, CELL, OX, OZ, X, Z = load()
    rec = dict(source='work/heightfield.npz', footprint_old=FP['old'], skirt=FP['skirt'])
    if a.only in (None, 'ground'): build_ground(hf, N, CELL, OX, OZ, X, Z, rec, a.survey)
    if a.only in (None, 'basin'): build_basin(hf, N, CELL, OX, OZ, X, Z, a.theta, rec, a.survey)
    if not a.survey:
        (HERE / 'mesh.json').write_text(json.dumps(rec, indent=1))
        print(json.dumps({k: (v if k not in ('basin', 'ground') else {kk: vv for kk, vv in v.items() if kk not in ('chunks', 'tiles')}) for k, v in rec.items()}, indent=1))


if __name__ == '__main__':
    main()
