"""Truck LOD1/LOD2 geometry by voxel remesh + collapse decimation (Blender, CPU).

Supersedes the meshoptimizer LOD1/LOD2 geometry: position-only collapse of the Meshy
surface left folded "webbing" between rails and panels (3.9% / 10% of edges folded
> 150 deg) that shaded as dark wedges on flat panels at 16 m even with a clean
texture transfer (review/truck_16m_meshopt_geometry_rejected.jpg). A voxel level set
(VOXEL_MM) rebuilds a clean closed surface first, then Blender's collapse decimate
reaches the triangle target. Writes cache/truck_<LOD>_geometry.npz (positions raw,
tris, geometric normals) and logs fold rates + BVH surface deviation.
"""
import json
import os
import sys
import time

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(__file__))
import blender_common as bc  # noqa: E402
from truck_decimate_eval import welded_source, arrays, fold_stats, deviation, RAW_TO_WORLD_MM, S  # noqa: E402

TARGETS = {"LOD1": (40_000, 8.0), "LOD2": (10_000, 20.0)}  # triangles, voxel size mm (scene scale)


def log(m):
    print(time.strftime("%H:%M:%S"), m, flush=True)


def main():
    bc.reset_scene()
    wp, wt = welded_source()
    wp_s = wp * S
    src = bc.mesh_from_arrays("src", wp_s, wt)
    src_bvh = BVHTree.FromPolygons([tuple(x) for x in wp_s], [tuple(x) for x in wt])
    rng = np.random.default_rng(0)
    src_samples = wp_s[rng.choice(len(wp_s), 20000, replace=False)]
    report = {}
    for lod, (tgt, voxel_mm) in TARGETS.items():
        ob = src.copy()
        ob.data = src.data.copy()
        bpy.context.scene.collection.objects.link(ob)
        r = ob.modifiers.new("vox", "REMESH")
        r.mode = "VOXEL"
        r.voxel_size = voxel_mm / RAW_TO_WORLD_MM * S
        r.adaptivity = 0.0
        r.use_smooth_shade = True
        t0 = time.time()
        _, t_vox = arrays(ob)
        m = ob.modifiers.new("dec", "DECIMATE")
        m.decimate_type = "COLLAPSE"
        m.ratio = tgt / max(len(t_vox), 1)
        m.use_collapse_triangulate = True
        p, t = arrays(ob)
        log(f"{lod}: voxel {voxel_mm} mm -> {len(t_vox)} -> {len(t)} tris ({time.time()-t0:.0f}s)")
        lod_bvh = BVHTree.FromPolygons([tuple(x) for x in p], [tuple(x) for x in t])
        sv = p[rng.choice(len(p), min(len(p), 20000), replace=False)]
        d1 = deviation(src_bvh, sv) / S * RAW_TO_WORLD_MM
        d2 = deviation(lod_bvh, src_samples) / S * RAW_TO_WORLD_MM
        c60, c150 = fold_stats(p, t)
        report[lod] = {"method": f"voxel remesh {voxel_mm} mm + Blender collapse decimate", "voxelMm": voxel_mm,
                       "voxelTriangles": int(len(t_vox)), "triangles": int(len(t)),
                       "creaseGt60": c60, "foldGt150": c150,
                       "lodToSourceMm": {"mean": float(np.nanmean(d1)), "p99": float(np.nanpercentile(d1, 99)),
                                         "max": float(np.nanmax(d1))},
                       "sourceToLodMm": {"mean": float(np.nanmean(d2)), "p95": float(np.nanpercentile(d2, 95)),
                                         "p99": float(np.nanpercentile(d2, 99)), "max": float(np.nanmax(d2))}}
        log(f"{lod}: {report[lod]}")
        np.savez(f"{bc.CACHE}/truck_{lod}_geometry.npz", positions=p / S, tris=t.astype(np.int32),
                 error_raw=float(np.nanpercentile(d1, 99)) / RAW_TO_WORLD_MM)
        bpy.data.objects.remove(ob)
        with open(f"{bc.ROOT}/truck/voxel-lods.json", "w") as fh:
            json.dump(report, fh, indent=1)
    log("done")


main()
