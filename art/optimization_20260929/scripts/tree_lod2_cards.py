"""Ward tree LOD2 leaves v2: more cards, each card simplified, smaller enlargement.

The first LOD2 (8% of cards kept whole at ~40 triangles each, enlarged 2.6x) matched
the projected opaque coverage numerically but rendered visibly sparser and lighter at
45 m (review/tree_front45_LOD2v1_rejected.jpg): large enlarged cards leave big holes
and less canopy self-shadowing. v2 keeps CARD_FRACTION of the cards (stratified,
>= 1 per 0.8 m cell), reduces every kept card from ~40 to ~TRIS_PER_CARD triangles with
a UV-weighted quadric collapse (vertices keep their original UV/normal, so the alpha
mask maps exactly at every kept vertex), and tunes the enlargement on the horizontal /
hill view directions. Writes cache/tree_LOD2_leaves_v2.npz and updates the report;
tree_write_lod2.py writes the FBX.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import meshtools as mt  # noqa: E402
from tree_proxies import (Leaves, CUTOFF, VIEW_DIRS, SUN_DIRS, unit, project, occupancy, CACHE, OUT)  # noqa: E402

CARD_FRACTIONS = [0.40, 0.50]
SHADOW_CARD_FRACTIONS = [0.25]
TRIS_PER_CARD = {"lod2": 6, "shadow": 9}
UV_WEIGHT = 4.0
NORMAL_WEIGHT = 0.25
DENSITY = 900.0


def sample_tris(P, UV, alpha, density, rng):
    a, b, c = P[:, 0], P[:, 1], P[:, 2]
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    n = rng.poisson(area * density)
    ti = np.repeat(np.arange(len(P)), n)
    r1, r2 = rng.random(len(ti)), rng.random(len(ti))
    s = np.sqrt(r1)
    w = np.stack([1 - s, s * (1 - r2), s * r2], 1)
    uv = (UV[ti] * w[:, :, None]).sum(1)
    h, wd = alpha.shape
    px = np.clip((np.mod(uv[:, 0], 1.0) * wd).astype(np.int64), 0, wd - 1)
    py = np.clip(((1.0 - np.mod(uv[:, 1], 1.0)) * h).astype(np.int64), 0, h - 1)
    ok = alpha[py, px] >= CUTOFF * 255
    return (P[ti[ok]] * w[ok][:, :, None]).sum(1)


def compare(src_pts, variants, dir_keys):
    out = {}
    dirs = {**SUN_DIRS, **VIEW_DIRS}
    for dname, (el, az) in dirs.items():
        d = unit(el, az)
        sp = project(src_pts, d)
        lo, hi = sp.min(0) - 2.0, sp.max(0) + 2.0
        for grid in (0.03, 0.10):
            shape = tuple(np.ceil((hi - lo) / grid).astype(int))
            so = occupancy(sp, grid, lo, shape)
            rec = out.setdefault(f"{dname}@{int(grid*100)}cm", {"sourceCells": int(so.sum())})
            for name, pts in variants.items():
                vo = occupancy(project(pts, d), grid, lo, shape)
                rec[name] = {"coverageRatio": round(float(vo.sum()) / max(1, so.sum()), 4),
                             "iou": round(float((so & vo).sum()) / max(1, (so | vo).sum()), 4)}
    scores = {}
    for name in variants:
        r = [out[k][name]["coverageRatio"] for k in dir_keys]
        i = [out[k][name]["iou"] for k in dir_keys]
        scores[name] = (float(np.mean(np.abs(np.log(r)))), float(np.mean(i)))
    return out, scores


def simplified_cards(leaves, d, keep, tris_per_card):
    tri_keep = np.flatnonzero(keep[leaves.card_of_tri])
    tc = leaves.tri[tri_keep]                       # corner ids (T,3)
    corner = tc.ravel()
    uvq = np.round(d["uv"][corner].astype(np.float64), 6)
    nq = np.round(d["normals"][corner].astype(np.float64), 4)
    _, ui = np.unique(uvq, axis=0, return_inverse=True)
    _, ni = np.unique(nq, axis=0, return_inverse=True)
    keys = np.stack([leaves.corner_cp[corner], ui.ravel(), ni.ravel()], 1)
    _, first, c2rv = np.unique(keys, axis=0, return_index=True, return_inverse=True)
    c2rv = c2rv.ravel()
    rv_corner = corner[first]                        # a source corner per render vertex
    tris = c2rv.reshape(-1, 3)
    pos1 = leaves.cp[leaves.corner_cp[rv_corner]]
    attrs = np.concatenate([d["uv"][rv_corner], d["normals"][rv_corner]], 1)
    weights = [UV_WEIGHT] * 2 + [NORMAL_WEIGHT] * 3
    target = int(keep.sum() * tris_per_card)
    st, err = mt.simplify(tris, pos1, target, attributes=attrs, weights=weights, lock_border=False)
    return st, rv_corner, err


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "lod2"
    fractions = CARD_FRACTIONS if mode == "lod2" else SHADOW_CARD_FRACTIONS
    leaves = Leaves()
    d = np.load(f"{CACHE}/tree_leaves.npz")
    rng = np.random.default_rng(11)
    src_pts = leaves.samples(np.ones(leaves.ncards, bool), 1.0, DENSITY, rng)
    dirs = VIEW_DIRS if mode == "lod2" else SUN_DIRS
    view_keys = [f"{k}@3cm" for k in dirs] + [f"{k}@10cm" for k in dirs]
    report_path = f"{OUT}/tree-lod-report.json"
    report = json.load(open(report_path))
    best = None
    trials = {}
    for f in fractions:
        keep = leaves.select(f)
        actual = float(keep.sum() / leaves.ncards)
        st, rv_corner, err = simplified_cards(leaves, d, keep, TRIS_PER_CARD[mode])
        k_eq = 1 / np.sqrt(actual)
        variants = {}
        for s in ((0.72, 0.82, 0.92, 1.02) if mode == "shadow" else (0.80, 0.88, 0.96, 1.04)):
            k = round(float(k_eq * s), 3)
            pos = leaves.positions(k)[leaves.corner_cp[rv_corner]]
            P = pos[st]
            UV = d["uv"][rv_corner][st].astype(np.float64)
            variants[f"k{k}"] = sample_tris(P, UV, leaves.alpha, DENSITY, rng)
        variants["sourceResampled"] = leaves.samples(np.ones(leaves.ncards, bool), 1.0, DENSITY, rng)
        cov, scores = compare(src_pts, variants, view_keys)
        ks = [n for n in variants if n.startswith("k")]
        kbest = min(ks, key=lambda n: scores[n][0])
        rec = {"cardFraction": f, "actualCardFraction": actual, "keptCards": int(keep.sum()),
               "triangles": int(len(st)), "cardSimplifyErrorM": err, "scores": scores, "bestK": float(kbest[1:]),
               "coverage": cov}
        trials[f"f{f}"] = rec
        mt.log(f"{mode} f={f} actual={actual:.3f} tris={len(st)} err={err:.4f} best={kbest} scores={scores}")
        if best is None or scores[kbest][1] > best[0]:
            best = (scores[kbest][1], f, keep, st, rv_corner, float(kbest[1:]))
    _, f, keep, st, rv_corner, k = best
    used, inv = np.unique(st, return_inverse=True)
    tris = inv.reshape(-1, 3)
    corners = rv_corner[used]
    pos = leaves.positions(k)[leaves.corner_cp[corners]]
    np.savez(f"{CACHE}/tree_{'LOD2' if mode == 'lod2' else 'Shadow'}_leaves_v2.npz", cp=pos, corner_cp=tris.ravel(), poly_size=np.full(len(tris), 3),
             normals=d["normals"][corners][tris].reshape(-1, 3), uv=d["uv"][corners][tris].reshape(-1, 2),
             color=d["color"][corners][tris].reshape(-1, 4))
    report["lod2LeavesV2" if mode == "lod2" else "shadowLeavesV2"] = {"scoreDirections": view_keys,"chosen": {"cardFraction": f, "k": k, "triangles": int(len(tris))},
                              "trisPerCardTarget": TRIS_PER_CARD[mode], "uvWeight": UV_WEIGHT, "normalWeight": NORMAL_WEIGHT,
                              "trials": trials}
    mt.dump_json(report_path, report)
    mt.log(f"{mode} chosen f={f} k={k} tris={len(tris)}")


if __name__ == "__main__":
    main()
