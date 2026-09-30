"""Karaveen truck shadow proxy (supersedes the 6.8k proxy written by truck_lods.py).

Position-welded quadric collapse of the 3.09M source (ShadowProxy ~9.5k triangles,
ShadowNear ~160k), then an inset along area-weighted vertex normals so the caster sits inside the
visible surface (measured: the un-inset 7k proxy had 40% of its area > 2 mm outside the
source, p95 24 mm, which self-shadows sunlit panels in Cycles). Normals recomputed
(60 deg split) for URP's shadow normal bias. ShadowNear is the shadows-only caster in
the LOD0 range, ShadowProxy in the LOD1/LOD2 ranges.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import fbxlib  # noqa: E402
import meshtools as mt  # noqa: E402

REPO = "/home/teknetik/code/ao2"
SRC = f"{REPO}/unity/AthenHill/Assets/MeshyImports/Mudrunner Convoy_20260910_162611/Meshy_AI_Mudrunner_Convoy_0910152501_texture.fbx"
OUT = f"{REPO}/art/optimization_20260929/truck"
CACHE = f"{REPO}/art/optimization_20260929/cache"
RAW_TO_WORLD = 6.1975354 * 0.65
CASTERS = {  # name: (target triangles, inset mm)
    "ShadowProxy": (9_500, 15.0),   # LOD1/LOD2 range (>= ~16 m, URP cascades 1-3)
    "ShadowNear": (160_000, 3.0),   # LOD0 range (< ~16 m, cascade 0-1 bias is only a few mm)
}


def main():
    for name, (target, inset) in CASTERS.items():
        build(name, target, inset)


def build(name, TARGET, INSET_MM):
    d = np.load(f"{CACHE}/truck_source_render.npz")
    pos = d["positions"].astype(np.float64)
    tris = d["tris"].astype(np.int64)
    weld = mt.weld_by_position(pos)
    idx = np.zeros(weld.max() + 1, np.int64)
    idx[weld] = np.arange(len(weld))
    wp = pos[idx]
    wt = weld[tris]
    ok = (wt[:, 0] != wt[:, 1]) & (wt[:, 1] != wt[:, 2]) & (wt[:, 0] != wt[:, 2])
    wt = wt[ok]
    st, err = mt.simplify(wt, wp, TARGET, lock_border=False)
    used, inv = np.unique(st, return_inverse=True)
    p = wp[used].copy()
    t = inv.reshape(-1, 3)
    fn, area = mt.face_normals(p, t)
    vn = np.zeros_like(p)
    for i in range(3):
        np.add.at(vn, t[:, i], fn * area[:, None])
    vn /= np.maximum(np.linalg.norm(vn, axis=1), 1e-30)[:, None]
    p -= vn * (INSET_MM / 1000.0 / RAW_TO_WORLD)
    corner_n = mt.smooth_normals_angle(p, t, np.arange(len(p)), 60.0).reshape(-1, 3)
    rep = mt.mesh_report(name, p, t, None, None, np.arange(len(p)))
    rep.update({"resultErrorWorldMm": err * RAW_TO_WORLD * 1000, "insetMm": INSET_MM,
                "normals": "recomputed, area-weighted, 60 degree split", "target": TARGET})
    root, version = fbxlib.load(SRC)
    geom = fbxlib.objects(root, b"Geometry")[0]
    label = f"KaraveenTruck_{name}"
    gw = fbxlib.build_geometry_elem(geom, label, p, t.ravel(), np.full(len(t), 3),
                                    normals=corner_n, uv=np.zeros((t.size, 2)))
    path = f"{OUT}/{label}.fbx"
    fbxlib.write_surgery(root, version, path, {geom.props[0]: gw}, model_renames={"Mesh_0": label})
    np.savez(f"{CACHE}/truck_{name}.npz", positions=p, tris=t.astype(np.int32), normals=corner_n)
    rep["fbx"] = path
    report_path = f"{OUT}/truck-lod-report.json"
    report = json.load(open(report_path))
    report[name] = rep
    mt.dump_json(report_path, report)
    mt.log(f"{name}: {rep}")


if __name__ == "__main__":
    main()
