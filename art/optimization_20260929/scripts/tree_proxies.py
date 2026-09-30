"""Ward oasis tree: shadow proxy + LOD2 (thinned/enlarged leaf cards + decimated wood).

Stage 1 of the tree: its wood parts (shadow branches/trunk, LOD2 trunk, Blender LOD2
branches) are shipped; its whole-card leaf sets are superseded by tree_lod2_cards.py
(simplified cards) and the final FBX files are written by tree_write.py.

Stage C/D after tree_extract.py. Visible LOD0/LOD1 are not modified.

Leaf cards (connected components of the leaf mesh) are kept whole: a stratified
subset (per 0.8 m cell, at least one card per occupied cell so canopy extremities
survive) is scaled about each card's area centroid. Card UVs, normals and colour are
untouched, so the existing alpha-tested leaves material and wind shader apply. The
enlargement factor is tuned so the alpha-tested opaque coverage (cutoff 0.35, as in
leaves.mat) projected along several sun / view directions matches the source.

Wood: shadow proxy = position-welded quadric collapse (UV irrelevant for opaque
shadow casters, source vertex normals kept for URP normal bias). LOD2 wood =
seam-preserving collapse on render vertices so bark UVs stay exact.
"""
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
import fbxlib  # noqa: E402
import meshtools as mt  # noqa: E402

REPO = "/home/teknetik/code/ao2"
SRC = f"{REPO}/unity/AthenHill/Assets/AthenHill/Art/HeroTree/WardTree_LOD0.fbx"
LEAF_ALBEDO = f"{REPO}/unity/AthenHill/Assets/AthenHill/Art/HeroTree/leaves-albedo.png"
CACHE = f"{REPO}/art/optimization_20260929/cache"
OUT = f"{REPO}/art/optimization_20260929/tree"
CUTOFF = 0.35
CELL = 0.8
SEED = 29092026

SHADOW_FRACTIONS = [0.15, 0.20]
LOD2_FRACTIONS = [0.06]
WOOD = {  # target triangles
    "shadow": {"branches": 150_000, "trunk": 14_000},
    "LOD2": {"branches": 60_000, "trunk": 15_000},
}
SUN_DIRS = {  # (elevation, azimuth) degrees; light travels along -dir
    "sun90": (90, 0), "sun55": (55, 30), "sun30": (30, 200),
}
VIEW_DIRS = {"front": (0, 270), "side": (0, 0), "hill": (25, 135)}


def unit(el, az):
    el, az = np.radians(el), np.radians(az)
    # raw FBX frame is Blender-style Z-up (see README)
    return np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])


class Leaves:
    def __init__(self):
        d = np.load(f"{CACHE}/tree_leaves.npz")
        self.cp = d["cp"]
        self.corner_cp = d["corner_cp"]
        self.uv = d["uv"]
        self.tri = d["tri_corners"]
        self.poly_start, self.poly_size = d["poly_start"], d["poly_size"]
        c = np.load(f"{CACHE}/tree_cards.npz")
        self.label, self.card_of_tri, self.card_of_poly = c["label"], c["card_of_tri"], c["card_of_poly"]
        self.cen, self.card_tris, self.tri_area = c["centroid"], c["card_tris"], c["tri_area"]
        self.ncards = len(self.cen)
        a = np.asarray(Image.open(LEAF_ALBEDO))
        self.alpha = a[..., 3]
        self.h, self.w = self.alpha.shape

    def select(self, fraction, cell=CELL, seed=SEED):
        rng = np.random.default_rng(seed)
        key = np.floor(self.cen / cell).astype(np.int64)
        key = (key[:, 0] + 4096) * (1 << 26) + (key[:, 1] + 4096) * (1 << 13) + (key[:, 2] + 4096)
        rnd = rng.random(self.ncards)
        order = np.lexsort((rnd, key))
        ks = key[order]
        first = np.concatenate([[0], np.flatnonzero(np.diff(ks)) + 1])
        counts = np.diff(np.concatenate([first, [len(ks)]]))
        start_of = np.repeat(first, counts)
        rank = np.arange(len(ks)) - start_of
        quota = np.maximum(1, np.round(fraction * np.repeat(counts, counts))).astype(np.int64)
        keep = np.zeros(self.ncards, bool)
        keep[order[rank < quota]] = True
        return keep

    def positions(self, k):
        return self.cen[self.label] + k * (self.cp - self.cen[self.label])

    def samples(self, keep, k, density, rng):
        """Opaque (alpha >= cutoff) surface samples of the kept, scaled cards."""
        tris = np.flatnonzero(keep[self.card_of_tri])
        area = self.tri_area[tris] * k * k
        n = rng.poisson(area * density)
        tri_rep = np.repeat(tris, n)
        r1, r2 = rng.random(len(tri_rep)), rng.random(len(tri_rep))
        s = np.sqrt(r1)
        b0, b1, b2 = 1 - s, s * (1 - r2), s * r2
        c = self.tri[tri_rep]
        uv = (self.uv[c[:, 0]] * b0[:, None] + self.uv[c[:, 1]] * b1[:, None] + self.uv[c[:, 2]] * b2[:, None])
        px = np.clip((np.mod(uv[:, 0], 1.0) * self.w).astype(np.int64), 0, self.w - 1)
        py = np.clip(((1.0 - np.mod(uv[:, 1], 1.0)) * self.h).astype(np.int64), 0, self.h - 1)
        opaque = self.alpha[py, px] >= CUTOFF * 255
        pos = self.positions(k)
        cpc = self.corner_cp[c[opaque]]
        b0, b1, b2 = b0[opaque, None], b1[opaque, None], b2[opaque, None]
        return pos[cpc[:, 0]] * b0 + pos[cpc[:, 1]] * b1 + pos[cpc[:, 2]] * b2


def project(points, direction):
    d = direction / np.linalg.norm(direction)
    up = np.array([0, 0, 1.0]) if abs(d[2]) < 0.9 else np.array([1.0, 0, 0])
    u = np.cross(up, d)
    u /= np.linalg.norm(u)
    v = np.cross(d, u)
    return np.stack([points @ u, points @ v], 1)


def occupancy(p2, grid, origin, shape):
    ij = np.floor((p2 - origin) / grid).astype(np.int64)
    ok = (ij[:, 0] >= 0) & (ij[:, 1] >= 0) & (ij[:, 0] < shape[0]) & (ij[:, 1] < shape[1])
    occ = np.zeros(shape, bool)
    occ[ij[ok, 0], ij[ok, 1]] = True
    return occ


def coverage_compare(leaves, variants, density=1500.0, grids=(0.03, 0.10)):
    """Occupancy of opaque samples along each direction: source vs variants."""
    rng = np.random.default_rng(7)
    all_keep = np.ones(leaves.ncards, bool)
    src_pts = leaves.samples(all_keep, 1.0, density, rng)
    out = {}
    dirs = {**SUN_DIRS, **VIEW_DIRS}
    var_pts = {name: leaves.samples(keep, k, density, rng) for name, (keep, k) in variants.items()}
    for dname, (el, az) in dirs.items():
        d = unit(el, az)
        sp = project(src_pts, d)
        lo = sp.min(0) - 2.0
        hi = sp.max(0) + 2.0
        for grid in grids:
            shape = tuple(np.ceil((hi - lo) / grid).astype(int))
            so = occupancy(sp, grid, lo, shape)
            rec = out.setdefault(f"{dname}@{int(grid*100)}cm", {"sourceCells": int(so.sum())})
            for name, pts in var_pts.items():
                vo = occupancy(project(pts, d), grid, lo, shape)
                inter = int((so & vo).sum())
                union = int((so | vo).sum())
                rec[name] = {"coverageRatio": round(float(vo.sum()) / max(1, so.sum()), 4),
                             "iou": round(inter / max(1, union), 4)}
    return out


def score(cov, name, keys):
    ratios = [cov[k][name]["coverageRatio"] for k in keys]
    ious = [cov[k][name]["iou"] for k in keys]
    return float(np.mean(np.abs(np.log(ratios)))), float(np.mean(ious))


def tune(leaves, fraction, dir_keys, label, scales=(0.70, 0.80, 0.90, 1.0)):
    keep = leaves.select(fraction)
    actual = keep.sum() / leaves.ncards
    k_eq = 1 / np.sqrt(actual)
    ks = [round(float(k_eq * s), 3) for s in scales]
    variants = {f"k{k}": (keep, k) for k in ks}
    # calibration: the full source resampled with a different seed (sampling-noise IoU)
    variants["sourceResampled"] = (np.ones(leaves.ncards, bool), 1.0)
    cov = coverage_compare(leaves, variants, density=900.0)
    best = min(ks, key=lambda k: score(cov, f"k{k}", dir_keys)[0])
    mt.log(f"{label} f={fraction} actual={actual:.4f} ks={ks} best={best} "
           f"score={[score(cov, f'k{k}', dir_keys) for k in ks]} baseline={score(cov, 'sourceResampled', dir_keys)}")
    return {"fraction": fraction, "actualCardFraction": float(actual), "keptCards": int(keep.sum()),
            "keptTriangles": int(leaves.card_tris[keep].sum()), "kCandidates": ks, "bestK": best,
            "bestScore": {"meanAbsLogCoverageRatio": score(cov, f"k{best}", dir_keys)[0],
                          "meanIoU": score(cov, f"k{best}", dir_keys)[1]},
            "samplingBaseline": {"meanAbsLogCoverageRatio": score(cov, "sourceResampled", dir_keys)[0],
                                 "meanIoU": score(cov, "sourceResampled", dir_keys)[1]},
            "scoreDirections": dir_keys, "coverage": cov}, keep, best


def wood_shadow(part, target):
    d = np.load(f"{CACHE}/tree_{part}.npz")
    tri = d["tri_corners"]
    cp, corner_cp, normals = d["cp"], d["corner_cp"], d["normals"]
    pos_w = mt.weld_by_position(cp)
    idx = np.zeros(pos_w.max() + 1, np.int64)
    idx[pos_w] = np.arange(len(pos_w))
    wp = cp[idx]
    # per welded vertex normal: average of corner normals
    wn = np.zeros((len(idx), 3))
    np.add.at(wn, pos_w[corner_cp], normals)
    wn /= np.maximum(np.linalg.norm(wn, axis=1), 1e-12)[:, None]
    wt = pos_w[corner_cp[tri]]
    ok = (wt[:, 0] != wt[:, 1]) & (wt[:, 1] != wt[:, 2]) & (wt[:, 0] != wt[:, 2])
    wt = wt[ok]
    lt, err = mt.simplify(wt, wp, target, lock_border=False)
    used, inv = np.unique(lt, return_inverse=True)
    tris = inv.reshape(-1, 3)
    stats = mt.mesh_report(f"shadow_{part}", wp[used], tris, wn[used], None, np.arange(len(used)))
    stats["sourceTriangles"] = int(len(tri))
    stats["resultErrorM"] = err
    return {"cp": wp[used], "corner_cp": tris.ravel(), "poly_size": np.full(len(tris), 3),
            "normals": wn[used][tris].reshape(-1, 3), "uv": np.zeros((tris.size, 2)),
            "color": np.repeat(d["color"][:1], tris.size, 0)}, stats


def wood_lod2(part, target):
    d = np.load(f"{CACHE}/tree_{part}.npz")
    tri = d["tri_corners"]
    cp, corner_cp = d["cp"], d["corner_cp"]
    nq = np.round(d["normals"].astype(np.float64), 5)
    uq = np.round(d["uv"].astype(np.float64), 6)
    _, ninv = np.unique(nq, axis=0, return_inverse=True)
    _, uinv = np.unique(uq, axis=0, return_inverse=True)
    first, c2rv = mt.render_vertices(mt.pack_keys(corner_cp, ninv.ravel(), uinv.ravel()))
    rv_pos = cp[corner_cp[first]]
    tris_rv = c2rv[tri]
    weld = mt.weld_by_position(rv_pos)
    lt, err = mt.simplify(tris_rv, rv_pos, target, lock_border=True)
    floor_note = None
    if len(lt) > target * 1.3:
        floor_note = f"seam-preserving floor {len(lt)} > target {target}"
    used, inv = np.unique(lt, return_inverse=True)
    tris = inv.reshape(-1, 3)
    corner_first = first[used]
    # control points: unique source cp among used render vertices
    ucp, cp_inv = np.unique(corner_cp[corner_first], return_inverse=True)
    stats = mt.mesh_report(f"LOD2_{part}", rv_pos[used], tris, d["normals"][corner_first], d["uv"][corner_first],
                           weld[used])
    stats.update({"sourceTriangles": int(len(tri)), "resultErrorM": err, "uv": "source UV exact (seams preserved)",
                  "floorNote": floor_note})
    return {"cp": cp[ucp], "corner_cp": cp_inv.ravel()[tris].ravel(), "poly_size": np.full(len(tris), 3),
            "normals": d["normals"][corner_first][tris].reshape(-1, 3), "uv": d["uv"][corner_first][tris].reshape(-1, 2),
            "color": d["color"][corner_first][tris].reshape(-1, 4)}, stats


def blender_branches():
    path = f"{CACHE}/tree_LOD2_branches_blender.npz"
    b = np.load(path)
    col = np.load(f"{CACHE}/tree_branches.npz")["color"][:1]
    tris = b["tris"].astype(np.int64)
    pos = b["positions"].astype(np.float64)
    stats = mt.mesh_report("LOD2_branches", pos, tris, None, None, np.arange(len(pos)))
    stats.update({"method": "Blender collapse decimate (tree_lod2_branches.py)",
                  "uv": "source bark UVs interpolated per corner", "sourceTriangles": 1231286})
    return {"cp": pos, "corner_cp": tris.ravel(), "poly_size": np.full(len(tris), 3),
            "normals": b["corner_normals"].reshape(-1, 3), "uv": b["corner_uv"].reshape(-1, 2),
            "color": np.repeat(col, tris.size, 0)}, stats


def leaves_output(leaves, keep, k):
    polys = np.flatnonzero(keep[leaves.card_of_poly])
    starts = leaves.poly_start[polys]
    sizes = leaves.poly_size[polys]
    corners = np.repeat(starts, sizes) + (np.arange(sizes.sum()) - np.repeat(np.cumsum(sizes) - sizes, sizes))
    ccp = leaves.corner_cp[corners]
    ucp, inv = np.unique(ccp, return_inverse=True)
    pos = leaves.positions(k)[ucp]
    d = np.load(f"{CACHE}/tree_leaves.npz")
    return {"cp": pos, "corner_cp": inv.ravel(), "poly_size": sizes, "normals": d["normals"][corners],
            "uv": d["uv"][corners], "color": d["color"][corners]}


def write_tree(path, prefix, parts):
    root, version = fbxlib.load(SRC)
    geoms = {o.props[0]: o for o in fbxlib.objects(root, b"Geometry")}
    reps = {}
    renames = {}
    for part, data in parts.items():
        uid = int(np.load(f"{CACHE}/tree_{part}.npz")["geometry_uid"])
        template = geoms[uid]
        reps[uid] = fbxlib.build_geometry_elem(
            template, f"{prefix}_{part}", data["cp"], data["corner_cp"], data["poly_size"],
            normals=data["normals"], uv=data["uv"], extra_corner_layers={"LayerElementColor": data["color"]})
        renames[f"WardTree_LOD0_{part}"] = f"{prefix}_{part}"
    fbxlib.write_surgery(root, version, path, reps, model_renames=renames)
    mt.log(f"wrote {path} ({os.path.getsize(path)/1e6:.1f} MB)")


def main():
    os.makedirs(OUT, exist_ok=True)
    report_path = f"{OUT}/tree-lod-report.json"
    report = json.load(open(report_path)) if os.path.exists(report_path) else {}
    leaves = Leaves()
    mt.log(f"leaves: {leaves.ncards} cards")
    sun_keys = [f"{k}@3cm" for k in SUN_DIRS] + [f"{k}@10cm" for k in SUN_DIRS]
    view_keys = [f"{k}@3cm" for k in VIEW_DIRS] + [f"{k}@10cm" for k in VIEW_DIRS]

    # --- shadow proxy leaves
    # smallest card fraction whose tuned coverage error is within 3% (else the largest)
    chosen = None
    for f in SHADOW_FRACTIONS:
        rec, keep, k = tune(leaves, f, sun_keys, "shadow")
        report[f"shadowLeaves_f{f}"] = rec
        mt.dump_json(report_path, report)
        err, iou = score(rec["coverage"], f"k{k}", sun_keys)
        if chosen is None and err < 0.03:
            chosen = (f, keep, k)
        last = (f, keep, k)
    f_s, keep_s, k_s = chosen if chosen is not None else last
    report["shadowLeavesChosen"] = {"fraction": f_s, "k": k_s}

    # --- LOD2 leaves (tuned on horizontal / hill view directions)
    rec, keep_2, k_2 = tune(leaves, LOD2_FRACTIONS[0], view_keys, "lod2", scales=(0.50, 0.58, 0.66, 0.74))
    report["lod2Leaves"] = rec
    mt.dump_json(report_path, report)

    # --- wood
    shadow_parts = {"leaves": leaves_output(leaves, keep_s, k_s)}
    lod2_parts = {"leaves": leaves_output(leaves, keep_2, k_2)}
    for part in ("branches", "trunk"):
        data, stats = wood_shadow(part, WOOD["shadow"][part])
        shadow_parts[part] = data
        report[f"shadow_{part}"] = stats
        mt.log(f"shadow {part}: {stats}")
        if part == "branches":
            # seam-preserving collapse floors at ~300k with zero-area seam slivers (tiled bark
            # UVs, open twig tubes); Blender's collapse decimate keeps per-corner UVs instead.
            data, stats = blender_branches()
        else:
            data, stats = wood_lod2(part, WOOD["LOD2"][part])
        lod2_parts[part] = data
        report[f"LOD2_{part}"] = stats
        mt.log(f"LOD2 {part}: {stats}")
        mt.dump_json(report_path, report)
    for name, parts in (("ShadowProxy", shadow_parts), ("LOD2", lod2_parts)):
        tri_total = 0
        for part, data in parts.items():
            t = int((data["poly_size"] - 2).sum())
            report.setdefault(f"{name}_triangles", {})[part] = t
            tri_total += t
        report[f"{name}_triangles"]["total"] = tri_total
        np.savez(f"{CACHE}/tree_{name}.npz", **{f"{p}_{k}": v for p, dd in parts.items() for k, v in dd.items()})
    mt.dump_json(report_path, report)
    write_tree(f"{OUT}/WardTree_ShadowProxy.fbx", "WardTree_Shadow", shadow_parts)
    write_tree(f"{OUT}/WardTree_LOD2.fbx", "WardTree_LOD2", lod2_parts)
    report["fbx"] = [f"{OUT}/WardTree_ShadowProxy.fbx", f"{OUT}/WardTree_LOD2.fbx"]
    mt.dump_json(report_path, report)
    mt.log("done")


if __name__ == "__main__":
    main()
