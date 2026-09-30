"""Evaluate alternative truck LOD1/LOD2 geometry in Blender (CPU only, one asset).

Compares Blender Decimate (collapse) and voxel-remesh + decimate against the
meshoptimizer position-only result using fold rate (adjacent faces > 150 deg),
crease rate (> 60 deg) and two-sided surface deviation measured with BVH trees.
Candidates are written to cache/truck_<LOD>_<method>_geometry.npz.
"""
import os, sys, time, math
import bpy, bmesh
import numpy as np
from mathutils.bvhtree import BVHTree
sys.path.insert(0, os.path.dirname(__file__))
import blender_common as bc

RAW_TO_WORLD_MM = 6.1975354 * 0.65 * 1000
S = 100.0  # work scale (see truck_bake.py)


def log(m):
    print(time.strftime("%H:%M:%S"), m, flush=True)


def welded_source():
    d = np.load(f"{bc.CACHE}/truck_source_render.npz")
    p = d["positions"].astype(np.float64)
    t = d["tris"].astype(np.int64)
    q = np.round(p, 6)
    _, inv = np.unique(q, axis=0, return_inverse=True)
    inv = inv.ravel()
    idx = np.zeros(inv.max() + 1, np.int64)
    idx[inv] = np.arange(len(inv))
    wt = inv[t]
    k = (wt[:, 0] != wt[:, 1]) & (wt[:, 1] != wt[:, 2]) & (wt[:, 0] != wt[:, 2])
    return p[idx], wt[k]


def arrays(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    me.calc_loop_triangles()
    v = np.zeros(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", v)
    tr = np.zeros(len(me.loop_triangles) * 3, np.int32)
    me.loop_triangles.foreach_get("vertices", tr)
    ev.to_mesh_clear()
    return v.reshape(-1, 3).astype(np.float64), tr.reshape(-1, 3).astype(np.int64)


def fold_stats(p, t):
    a, b, c = p[t[:, 0]], p[t[:, 1]], p[t[:, 2]]
    fn = np.cross(b - a, c - a)
    fn /= np.maximum(np.linalg.norm(fn, axis=1), 1e-30)[:, None]
    e = np.concatenate([t[:, [0, 1]], t[:, [1, 2]], t[:, [2, 0]]])
    f = np.tile(np.arange(len(t)), 3)
    es = np.sort(e, 1)
    key = es[:, 0] * (1 << 31) + es[:, 1]
    o = np.argsort(key)
    ks, fs = key[o], f[o]
    s = ks[1:] == ks[:-1]
    dd = (fn[fs[:-1][s]] * fn[fs[1:][s]]).sum(1)
    return float((dd < 0.5).mean()), float((dd < -0.866).mean())


def deviation(bvh_ref, pts):
    d = np.empty(len(pts))
    for i, q in enumerate(pts):
        hit = bvh_ref.find_nearest(q)
        d[i] = hit[3] if hit[0] is not None else np.nan
    return d


def report(name, p, t, src_bvh, src_samples):
    lod_bvh = BVHTree.FromPolygons([tuple(x) for x in p], [tuple(x) for x in t])
    rng = np.random.default_rng(1)
    sample_v = p[rng.choice(len(p), min(len(p), 20000), replace=False)]
    d1 = deviation(src_bvh, sample_v) / S * RAW_TO_WORLD_MM  # LOD -> source
    d2 = deviation(lod_bvh, src_samples) / S * RAW_TO_WORLD_MM  # source -> LOD
    c60, c150 = fold_stats(p, t)
    log(f"{name}: tris {len(t)} crease>60 {c60:.3f} fold>150 {c150:.3f} | LOD->src mean {np.nanmean(d1):.1f} "
        f"p99 {np.nanpercentile(d1, 99):.1f} max {np.nanmax(d1):.1f} mm | src->LOD mean {np.nanmean(d2):.1f} "
        f"p99 {np.nanpercentile(d2, 99):.1f} max {np.nanmax(d2):.1f} mm")


def main():
    bc.reset_scene()
    log("welded source")
    wp, wt = welded_source()
    wp_s = wp * S
    src = bc.mesh_from_arrays("src", wp_s, wt)
    src_bvh = BVHTree.FromPolygons([tuple(x) for x in wp_s], [tuple(x) for x in wt])
    rng = np.random.default_rng(0)
    src_samples = wp_s[rng.choice(len(wp_s), 20000, replace=False)]
    log("source ready")
    # meshopt baselines
    for lod in ("LOD1", "LOD2"):
        d = np.load(f"{bc.CACHE}/truck_{lod}_geometry.npz")
        report(f"{lod} meshopt", d["positions"] * S, d["tris"].astype(np.int64), src_bvh, src_samples)
    targets = {"LOD1": 40000, "LOD2": 10000}
    # Blender collapse decimate
    for lod, tgt in targets.items():
        ob = src.copy()
        ob.data = src.data.copy()
        bpy.context.scene.collection.objects.link(ob)
        m = ob.modifiers.new("dec", "DECIMATE")
        m.decimate_type = "COLLAPSE"
        m.ratio = tgt / len(wt)
        m.use_collapse_triangulate = True
        t0 = time.time()
        p, t = arrays(ob)
        log(f"{lod} blender-decimate {time.time()-t0:.0f}s")
        report(f"{lod} blender-decimate", p, t, src_bvh, src_samples)
        np.savez(f"{bc.CACHE}/truck_{lod}_bdec_geometry.npz", positions=p / S, tris=t.astype(np.int32))
        bpy.data.objects.remove(ob)
    # voxel remesh + decimate
    for lod, tgt, voxel_mm in (("LOD1", 40000, 12.0), ("LOD2", 10000, 25.0)):
        ob = src.copy()
        ob.data = src.data.copy()
        bpy.context.scene.collection.objects.link(ob)
        r = ob.modifiers.new("vox", "REMESH")
        r.mode = "VOXEL"
        r.voxel_size = voxel_mm / RAW_TO_WORLD_MM * S
        r.adaptivity = 0.0
        t0 = time.time()
        p0, t0_ = arrays(ob)
        log(f"{lod} voxel {voxel_mm}mm -> {len(t0_)} tris in {time.time()-t0:.0f}s")
        m = ob.modifiers.new("dec", "DECIMATE")
        m.decimate_type = "COLLAPSE"
        m.ratio = tgt / max(len(t0_), 1)
        m.use_collapse_triangulate = True
        p, t = arrays(ob)
        report(f"{lod} voxel{voxel_mm:.0f}+decimate", p, t, src_bvh, src_samples)
        np.savez(f"{bc.CACHE}/truck_{lod}_vox_geometry.npz", positions=p / S, tris=t.astype(np.int32))
        bpy.data.objects.remove(ob)
    log("done")


if __name__ == "__main__":
    main()
