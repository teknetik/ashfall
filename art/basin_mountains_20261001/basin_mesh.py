#!/usr/bin/env python3
"""Adaptive, crack-free basin mesh from work/heightfield.npz, split into the eight original sectors.

One global RTIN (right-triangulated irregular network, Martini-style longest-edge bisection) over the 1025 x 1025
heightfield. The split test uses a view-weighted error: vertical error divided by the distance to where the player
and cameras can be (the city rectangle and the Outer Berms footprint), so detail goes where it is seen: about
1 m triangles at the Berms toe, a few metres on the crests 150-400 m out, large triangles on hidden back slopes.
Because the mesh is one watertight network before it is split, neighbouring chunks share every border vertex and its
normal and colour exactly (no seams). Triangles under the city (beyond 0.75 m inside its rectangle), under the Berms
ground (more than 3 m inside its footprint) and beyond the original outer edge are dropped; full refinement along
those cut lines keeps the edges within 1 m.

Per vertex: Unity position, a normal from the heightfield smoothed at the vertex's own triangle scale (no distant
shading sparkle), COLOR (R sun visibility, G sky access, B = A = 1, as the V2 shader reads), UV0 = XZ / 16.

Run: $O/heavy.sh uv run --with numpy --with numba --with scipy python basin_mesh.py [--theta 0.0012]
Out: work/chunks/BasinMountains_0s.npz (Unity space) + mesh.json (counts)
"""
import argparse, json, math, sys, time
from pathlib import Path
import numpy as np
import numba as nb
from scipy import ndimage

HERE = Path(__file__).resolve().parent
WORK = HERE / 'work'
N, CELL, ORG = 1025, 1.0, -512.0
CITY = (62.0, 48.0)
BERMS = (-104.0, -60.0, -54.0, 48.0)
NAMES = ['BasinMountains_%02d' % s for s in range(8)]


@nb.njit(cache=True)
def rtin_errors(H, W, force):
    size = H.shape[0]; tile = size - 1
    h = H.ravel(); w = W.ravel()
    errors = np.zeros(size * size)
    for v in range(size * size):
        if force[v]: errors[v] = 1e9
    num_tri = tile * tile * 2 - 2
    num_parent = num_tri - tile * tile
    for i in range(num_tri - 1, -1, -1):
        idd = i + 2
        ax = ay = bx = by = cx = cy = 0
        if idd & 1:
            bx = tile; by = tile; cx = tile
        else:
            ax = tile; ay = tile; cy = tile
        idd >>= 1
        while idd > 1:
            mx = (ax + bx) >> 1; my = (ay + by) >> 1
            if idd & 1:
                bx = ax; by = ay; ax = cx; ay = cy
            else:
                ax = bx; ay = by; bx = cx; by = cy
            cx = mx; cy = my
            idd >>= 1
        mx = (ax + bx) >> 1; my = (ay + by) >> 1
        cx = mx + my - ay; cy = my + ax - mx
        interp = (h[ay * size + ax] + h[by * size + bx]) * 0.5
        mid = my * size + mx
        err = abs(interp - h[mid]) * w[mid]
        if err > errors[mid]: errors[mid] = err
        if i < num_parent:
            lc = ((ay + cy) >> 1) * size + ((ax + cx) >> 1)
            rc = ((by + cy) >> 1) * size + ((bx + cx) >> 1)
            e = max(errors[lc], errors[rc])
            if e > errors[mid]: errors[mid] = e
    return errors


@nb.njit(cache=True)
def _push(st, sp, a, b, c, d, e, f):
    st[sp, 0] = a; st[sp, 1] = b; st[sp, 2] = c; st[sp, 3] = d; st[sp, 4] = e; st[sp, 5] = f
    return sp + 1


@nb.njit(cache=True)
def rtin_mesh(errors, size, max_err):
    tile = size - 1
    out = np.empty((size * size * 2, 3), np.int64); n = 0
    st = np.empty((4096, 6), np.int64); sp = 0
    sp = _push(st, sp, 0, 0, tile, tile, tile, 0)
    sp = _push(st, sp, tile, tile, 0, 0, 0, tile)
    while sp > 0:
        sp -= 1
        ax, ay, bx, by, cx, cy = st[sp, 0], st[sp, 1], st[sp, 2], st[sp, 3], st[sp, 4], st[sp, 5]
        mx = (ax + bx) >> 1; my = (ay + by) >> 1
        if abs(ax - cx) + abs(ay - cy) > 1 and errors[my * size + mx] > max_err:
            sp = _push(st, sp, cx, cy, ax, ay, mx, my)
            sp = _push(st, sp, bx, by, cx, cy, mx, my)
        else:
            out[n, 0] = ay * size + ax; out[n, 1] = by * size + bx; out[n, 2] = cy * size + cx; n += 1
    return out[:n]


def fields():
    hf = np.load(WORK / 'heightfield.npz')
    H = hf['H'].astype(np.float64); t = hf['t'].astype(np.float64)
    ax = ORG + np.arange(N) * CELL
    X, Z = np.meshgrid(ax, ax)
    x0, x1, z0, z1 = BERMS
    inside = np.minimum(np.minimum(X - x0, x1 - X), np.minimum(Z - z0, z1 - Z))
    view = (np.abs(X) <= CITY[0]) & (np.abs(Z) <= CITY[1]) | (inside >= 0)
    D = ndimage.distance_transform_edt(~view) * CELL
    return hf, H, t, X, Z, inside, D


def build(theta, hf, H, t, X, Z, inside, D, rec):
    W = 1.0 / np.maximum(D, 6.0)
    W[t > 440] = 0.0
    force = ((t > -1.5) & (t < 2.5)) | ((inside > 1.5) & (inside < 4.5))
    t0 = time.time()
    err = rtin_errors(np.ascontiguousarray(H), np.ascontiguousarray(W), force.ravel())
    tris = rtin_mesh(err, N, theta)
    rec['rtin_seconds'] = round(time.time() - t0, 1); rec['triangles_raw'] = int(len(tris))
    # drop: under the city, under the Berms ground, beyond the old outer edge
    tf = t.ravel(); inf = inside.ravel()
    ct = tf[tris].mean(1); ci = inf[tris].mean(1)
    keep = (ct > -0.75) & (ci < 3.0) & (ct < 430)
    return tris[keep]


def normals_at(H, idx, scale):
    """Normals from the heightfield smoothed at each vertex's triangle scale (sigma 0.6..10 m)."""
    out = np.zeros((len(idx), 3))
    sigmas = [0.6, 1.2, 2.5, 5.0, 10.0]
    pick = np.clip(np.searchsorted(sigmas, scale * 0.5), 0, len(sigmas) - 1)
    for k, s in enumerate(sigmas):
        m = pick == k
        if not m.any(): continue
        Hs = ndimage.gaussian_filter(H, s / CELL, mode='nearest')
        gz, gx = np.gradient(Hs, CELL)
        n = np.stack([-gx.ravel()[idx[m]], np.ones(m.sum()), -gz.ravel()[idx[m]]], 1)
        out[m] = n / np.linalg.norm(n, axis=1, keepdims=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--theta', type=float, default=0.0012)
    ap.add_argument('--survey', action='store_true', help='only print triangle counts for a theta range')
    a = ap.parse_args()
    hf, H, t, X, Z, inside, D = fields()
    if a.survey:
        for th in (0.004, 0.006, 0.008, 0.011, 0.015):
            r = {}; tris = build(th, hf, H, t, X, Z, inside, D, r)
            print('theta %.4f -> %d triangles' % (th, len(tris)), flush=True)
        return
    rec = dict(theta=a.theta)
    tris = build(a.theta, hf, H, t, X, Z, inside, D, rec)
    # winding: counter-clockwise seen from above in Blender space (x_b = -X, y_b = -Z)
    Xf, Zf, Hf = X.ravel(), Z.ravel(), H.ravel()
    pa, pb, pc = tris[:, 0], tris[:, 1], tris[:, 2]
    bx = lambda i: -Xf[i]; by = lambda i: -Zf[i]
    cross = (bx(pb) - bx(pa)) * (by(pc) - by(pa)) - (by(pb) - by(pa)) * (bx(pc) - bx(pa))
    flip = cross < 0
    tris[flip] = tris[flip][:, [0, 2, 1]]
    used = np.unique(tris)
    # per-vertex triangle scale (mean adjacent edge length)
    el = np.zeros(N * N); cnt = np.zeros(N * N)
    for u, v in ((0, 1), (1, 2), (2, 0)):
        L = np.hypot(Xf[tris[:, u]] - Xf[tris[:, v]], Zf[tris[:, u]] - Zf[tris[:, v]])
        np.add.at(el, tris[:, u], L); np.add.at(cnt, tris[:, u], 1)
        np.add.at(el, tris[:, v], L); np.add.at(cnt, tris[:, v], 1)
    scale = el[used] / np.maximum(cnt[used], 1)
    nrm = normals_at(H, used, scale)
    sun = hf['sun'].ravel()[used]; sky = hf['sky'].ravel()[used]
    P = np.stack([Xf[used], Hf[used], Zf[used]], 1)
    C = np.stack([sun, sky, np.ones_like(sun), np.ones_like(sun)], 1)
    UV = np.stack([Xf[used] / 16.0, Zf[used] / 16.0], 1)
    remap = np.full(N * N, -1, np.int64); remap[used] = np.arange(len(used))
    T = remap[tris]
    # sector of each triangle by centroid angle in the original generator's frame (script x = -X)
    cxs = -P[T, 0].mean(1); czs = P[T, 2].mean(1)
    sector = (np.floor(np.mod(np.arctan2(czs, cxs), 2 * np.pi) / (np.pi / 4)).astype(int)) % 8
    out = WORK / 'chunks'; out.mkdir(parents=True, exist_ok=True)
    rec['chunks'] = {}
    for s in range(8):
        tt = T[sector == s]
        vu = np.unique(tt)
        rm = np.full(len(P), -1, np.int64); rm[vu] = np.arange(len(vu))
        np.savez_compressed(out / (NAMES[s] + '.npz'), P=P[vu].astype(np.float32), N=nrm[vu].astype(np.float32),
                            C=C[vu].astype(np.float32), UV=UV[vu].astype(np.float32), I=rm[tt].astype(np.int32))
        b0 = P[vu].min(0); b1 = P[vu].max(0)
        rec['chunks'][NAMES[s]] = dict(triangles=int(len(tt)), vertices=int(len(vu)),
                                       bounds_min=[round(float(v), 2) for v in b0], bounds_max=[round(float(v), 2) for v in b1])
    rec['triangles'] = int(len(T)); rec['vertices_shared'] = int(len(used))
    # seam check: every vertex on a chunk border must be identical in both chunks (same global source vertex)
    owners = {}
    for s in range(8):
        for v in np.unique(T[sector == s]): owners.setdefault(int(v), []).append(s)
    rec['border_vertices'] = int(sum(1 for v in owners.values() if len(v) > 1))
    (HERE / 'mesh.json').write_text(json.dumps(rec, indent=1))
    print(json.dumps({k: v for k, v in rec.items() if k != 'chunks'}, indent=1))
    for k, v in rec['chunks'].items(): print(k, v['triangles'], v['vertices'])


if __name__ == '__main__':
    main()
