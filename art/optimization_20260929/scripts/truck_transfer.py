"""Closest-point texture transfer ("bake") for the truck LOD1/LOD2 (numpy + scipy).

Why not Cycles selected-to-active: the LOD vertices are a subset of the source
vertices, so the LOD surface is inscribed in the source (cuts inside convex areas,
bridges concave ones). A ray cage large enough to reach the outer shell also hits
rails/ladders a few cm in front of panels and smeared them across the panels (see
review/truck_16m_raybake_rejected.jpg). Here every covered texel takes the source
attributes at the *closest point* on the source surface instead.

For each LOD texel: position/normal/tangent from the LOD triangle (UV rasterised),
closest point on the source (KD-tree over source triangle centroids, exact
point-triangle distance over the k nearest candidates), source UV / TBN interpolated
there; base colour + metallic/smoothness sampled bilinearly; the source tangent-space
normal is taken to world space with the source Mikk TBN and re-expressed in the LOD
Mikk TBN (Blender MikkTSpace = Unity's CalculateMikk from the same normals/UVs).
Island edges are dilated by the margin.
"""
import json
import os
import sys
import time

import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(__file__))
import meshtools as mt  # noqa: E402

REPO = "/home/teknetik/code/ao2"
MESHY = f"{REPO}/unity/AthenHill/Assets/MeshyImports/Mudrunner Convoy_20260910_162611"
CACHE = f"{REPO}/art/optimization_20260929/cache"
TEX = f"{REPO}/art/optimization_20260929/truck/textures"
RES = {"LOD1": 2048, "LOD2": 1024}
DILATE = 8
K = 8
Image.MAX_IMAGE_PIXELS = None


def closest_on_triangles(p, a, b, c):
    """Vectorised closest point on triangles (Ericson). Returns point and barycentrics."""
    ab, ac, ap = b - a, c - a, p - a
    d1 = (ab * ap).sum(-1)
    d2 = (ac * ap).sum(-1)
    bp = p - b
    d3 = (ab * bp).sum(-1)
    d4 = (ac * bp).sum(-1)
    cp = p - c
    d5 = (ab * cp).sum(-1)
    d6 = (ac * cp).sum(-1)
    va = d3 * d6 - d5 * d4
    vb = d5 * d2 - d1 * d6
    vc = d1 * d4 - d3 * d2
    denom = va + vb + vc
    denom = np.where(np.abs(denom) < 1e-30, 1e-30, denom)
    v = vb / denom
    w = vc / denom
    u = 1 - v - w
    bary = np.stack([u, v, w], -1)
    # region tests (vertex / edge regions override the face region)
    def setb(mask, bu, bv, bw):
        bary[mask] = np.stack([bu[mask], bv[mask], bw[mask]], -1)
    one = np.ones_like(d1)
    zero = np.zeros_like(d1)
    # edge regions
    m_ab = (vc <= 0) & (d1 >= 0) & (d3 <= 0)
    t = np.where(m_ab, d1 / np.where(d1 - d3 == 0, 1e-30, d1 - d3), 0)
    setb(m_ab, 1 - t, t, zero)
    m_ac = (vb <= 0) & (d2 >= 0) & (d6 <= 0)
    t = np.where(m_ac, d2 / np.where(d2 - d6 == 0, 1e-30, d2 - d6), 0)
    setb(m_ac, 1 - t, zero, t)
    m_bc = (va <= 0) & ((d4 - d3) >= 0) & ((d5 - d6) >= 0)
    t = np.where(m_bc, (d4 - d3) / np.where((d4 - d3) + (d5 - d6) == 0, 1e-30, (d4 - d3) + (d5 - d6)), 0)
    setb(m_bc, zero, 1 - t, t)
    # vertex regions
    setb((d1 <= 0) & (d2 <= 0), one, zero, zero)
    setb((d3 >= 0) & (d4 <= d3), zero, one, zero)
    setb((d6 >= 0) & (d5 <= d6), zero, zero, one)
    q = a * bary[..., :1] + b * bary[..., 1:2] + c * bary[..., 2:3]
    return q, bary


class Source:
    def __init__(self):
        d = np.load(f"{CACHE}/truck_source_render.npz")
        self.pos = d["positions"].astype(np.float64)
        self.tris = d["tris"].astype(np.int64)
        self.uv = d["uv"][self.tris]  # (T,3,2)
        tg = np.load(f"{CACHE}/truck_source_tangents.npz")
        self.tan = tg["tangent"].reshape(-1, 3, 3)
        self.sign = tg["sign"].reshape(-1, 3)
        self.nrm = tg["normal"].reshape(-1, 3, 3)
        self.a, self.b, self.c = (self.pos[self.tris[:, i]] for i in range(3))
        cen = (self.a + self.b + self.c) / 3
        mt.log("source KD-tree")
        self.kd = cKDTree(cen)

    def closest(self, q, chunk=200_000):
        n = len(q)
        tri = np.empty(n, np.int64)
        bary = np.empty((n, 3))
        dist = np.empty(n)
        for s in range(0, n, chunk):
            qq = q[s:s + chunk]
            _, cand = self.kd.query(qq, k=K)
            P = qq[:, None, :]
            pts, bb = closest_on_triangles(P, self.a[cand], self.b[cand], self.c[cand])
            d2 = ((pts - P) ** 2).sum(-1)
            best = np.argmin(d2, 1)
            r = np.arange(len(qq))
            tri[s:s + chunk] = cand[r, best]
            bary[s:s + chunk] = bb[r, best]
            dist[s:s + chunk] = np.sqrt(d2[r, best])
        return tri, bary, dist

    def attributes(self, tri, bary):
        w = bary[..., None]
        uv = (self.uv[tri] * w).sum(1)
        n = (self.nrm[tri] * w).sum(1)
        t = (self.tan[tri] * w).sum(1)
        s = np.where(self.sign[tri, 0] < 0, -1.0, 1.0)
        return uv, n, t, s


def bilinear(img, uv):
    h, w = img.shape[:2]
    x = np.mod(uv[:, 0], 1.0) * w - 0.5
    y = (1.0 - np.mod(uv[:, 1], 1.0)) * h - 0.5
    x0 = np.floor(x).astype(np.int64)
    y0 = np.floor(y).astype(np.int64)
    fx = (x - x0)[:, None]
    fy = (y - y0)[:, None]
    x0c, x1c = np.clip(x0, 0, w - 1), np.clip(x0 + 1, 0, w - 1)
    y0c, y1c = np.clip(y0, 0, h - 1), np.clip(y0 + 1, 0, h - 1)
    im = img.astype(np.float32)
    top = im[y0c, x0c] * (1 - fx) + im[y0c, x1c] * fx
    bot = im[y1c, x0c] * (1 - fx) + im[y1c, x1c] * fx
    return top * (1 - fy) + bot * fy


def normalize(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-20)


def rasterize(uv_tri, res):
    """Texel centres covered by UV triangles. Returns (tri index, bary (N,3), texel y, x)."""
    out_t, out_b, out_y, out_x = [], [], [], []
    p = uv_tri * res  # texel units, origin bottom-left
    for i in range(len(p)):
        a, b, c = p[i]
        xmin = int(np.floor(min(a[0], b[0], c[0]) - 0.5))
        xmax = int(np.ceil(max(a[0], b[0], c[0]) + 0.5))
        ymin = int(np.floor(min(a[1], b[1], c[1]) - 0.5))
        ymax = int(np.ceil(max(a[1], b[1], c[1]) + 0.5))
        xs = np.arange(max(xmin, 0), min(xmax, res - 1) + 1) + 0.5
        ys = np.arange(max(ymin, 0), min(ymax, res - 1) + 1) + 0.5
        if len(xs) == 0 or len(ys) == 0:
            continue
        X, Y = np.meshgrid(xs, ys)
        X, Y = X.ravel(), Y.ravel()
        v0, v1 = b - a, c - a
        den = v0[0] * v1[1] - v1[0] * v0[1]
        if abs(den) < 1e-12:
            continue
        px, py = X - a[0], Y - a[1]
        l1 = (px * v1[1] - v1[0] * py) / den
        l2 = (v0[0] * py - px * v0[1]) / den
        l0 = 1 - l1 - l2
        eps = -1e-6
        m = (l0 >= eps) & (l1 >= eps) & (l2 >= eps)
        if not m.any():
            continue
        out_t.append(np.full(m.sum(), i))
        out_b.append(np.stack([l0[m], l1[m], l2[m]], 1))
        out_x.append((X[m] - 0.5).astype(np.int64))
        out_y.append((Y[m] - 0.5).astype(np.int64))
    return (np.concatenate(out_t), np.concatenate(out_b), np.concatenate(out_y), np.concatenate(out_x))


def dilate(img, mask, steps):
    img = img.copy()
    mask = mask.copy()
    for _ in range(steps):
        acc = np.zeros_like(img)
        cnt = np.zeros(mask.shape, np.float32)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            sm = np.roll(np.roll(mask, dy, 0), dx, 1)
            si = np.roll(np.roll(img, dy, 0), dx, 1)
            acc += si * sm[..., None]
            cnt += sm
        new = (~mask) & (cnt > 0)
        img[new] = acc[new] / cnt[new][:, None]
        mask = mask | new
    return img, mask


def main():
    lods = sys.argv[1:] or ["LOD2", "LOD1"]
    src = Source()
    mt.log("textures")
    base = np.asarray(Image.open(f"{MESHY}/meshy_basecolor.png").convert("RGB"))
    nmap = np.asarray(Image.open(f"{MESHY}/meshy_normal.png").convert("RGB"))
    msm = np.asarray(Image.open(f"{MESHY}/meshy_metallic_smoothness.png").convert("RGBA"))
    report = {}
    for name in lods:
        res = RES[name]
        g = np.load(f"{CACHE}/truck_{name}_geometry.npz")
        b = np.load(f"{CACHE}/truck_{name}_baked_uv.npz")
        tg = np.load(f"{CACHE}/truck_{name}_tangents.npz")
        pos = g["positions"].astype(np.float64)
        tris = b["tris"].astype(np.int64)
        uv = b["corner_uv"].reshape(-1, 3, 2).astype(np.float64)
        ln = tg["normal"].reshape(-1, 3, 3)
        lt = tg["tangent"].reshape(-1, 3, 3)
        ls = tg["sign"].reshape(-1, 3)
        mt.log(f"{name}: rasterise {len(tris)} tris at {res}")
        ti, bary, ty, tx = rasterize(uv, res)
        w = bary[..., None]
        P = (pos[tris[ti]] * w).sum(1)
        Nl = normalize((ln[ti] * w).sum(1))
        Tl = (lt[ti] * w).sum(1)
        Tl = normalize(Tl - Nl * (Tl * Nl).sum(1, keepdims=True))
        Bl = np.where(ls[ti, 0] < 0, -1.0, 1.0)[:, None] * np.cross(Nl, Tl)
        mt.log(f"{name}: {len(ti)} texels, closest points")
        stri, sbary, dist = src.closest(P)
        suv, sn, st, ss = src.attributes(stri, sbary)
        sn = normalize(sn)
        st = normalize(st - sn * (st * sn).sum(1, keepdims=True))
        sb = ss[:, None] * np.cross(sn, st)
        col = bilinear(base, suv)
        ms = bilinear(msm, suv)
        nts = bilinear(nmap, suv) / 255.0 * 2.0 - 1.0
        W = normalize(st * nts[:, :1] + sb * nts[:, 1:2] + sn * nts[:, 2:3])
        out_n = normalize(np.stack([(W * Tl).sum(1), (W * Bl).sum(1), (W * Nl).sum(1)], 1))
        # write images (row 0 = top => y flip)
        row = res - 1 - ty
        maps = {}
        for key, data, ch in (("BaseColor", col, 3), ("MetallicSmoothness", ms, 4),
                              ("Normal", (out_n * 0.5 + 0.5) * 255.0, 3)):
            img = np.zeros((res, res, ch), np.float32)
            mask = np.zeros((res, res), bool)
            img[row, tx] = data[:, :ch]
            mask[row, tx] = True
            img, m2 = dilate(img, mask, DILATE)
            fill = data[:, :ch].mean(0)
            img[~m2] = fill
            maps[key] = img
            mode = "RGBA" if ch == 4 else "RGB"
            Image.fromarray(np.clip(np.round(img), 0, 255).astype(np.uint8), mode).save(
                f"{TEX}/KaraveenTruck_{name}_{key}.png", optimize=True)
        dist_mm = dist * 6.1975354 * 0.65 * 1000
        report[name] = {"resolution": res, "texels": int(len(ti)),
                        "coverage": float(len(np.unique(row * res + tx)) / res / res),
                        "closestDistanceMm": {"mean": float(dist_mm.mean()), "p95": float(np.percentile(dist_mm, 95)),
                                              "p99": float(np.percentile(dist_mm, 99)), "max": float(dist_mm.max())},
                        "method": "closest-point transfer (truck_transfer.py)"}
        mt.log(f"{name}: {report[name]}")
        with open(f"{REPO}/art/optimization_20260929/truck/transfer-{name}.json", "w") as fh:
            json.dump(report[name], fh, indent=1)
    mt.log("done")


if __name__ == "__main__":
    main()
