"""Ward tree LOD2 branches: Blender collapse decimate with per-corner UV interpolation.

blender -b --factory-startup --python tree_lod2_branches.py
Input cache/tree_branches.npz (from tree_extract.py). The bark UVs tile along branch
length (v up to ~598) and every twig tube is its own island with open ends, so a
seam-preserving collapse cannot reach the LOD2 budget; BMesh collapse keeps each
face corner's own UV (interpolated) instead. Smooth normals (bark tubes).
"""
import os
import sys
import time

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import blender_common as bc  # noqa: E402

TARGET = 47_000  # ratio target; Blender collapse lands ~30% above it (~61k)


def main():
    bc.reset_scene()
    d = np.load(f"{bc.CACHE}/tree_branches.npz")
    tri = d["tri_corners"]
    ob = bc.mesh_from_arrays("branches", d["cp"], d["corner_cp"][tri], corner_uv=d["uv"][tri].reshape(-1, 2))
    n0 = len(ob.data.polygons)
    m = ob.modifiers.new("dec", "DECIMATE")
    m.decimate_type = "COLLAPSE"
    m.ratio = TARGET / n0
    m.use_collapse_triangulate = True
    t0 = time.time()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    me.calc_loop_triangles()
    nv = len(me.vertices)
    pos = np.zeros(nv * 3, np.float32)
    me.vertices.foreach_get("co", pos)
    lt = me.loop_triangles
    tris = np.zeros(len(lt) * 3, np.int32)
    lt.foreach_get("vertices", tris)
    loops = np.zeros(len(lt) * 3, np.int32)
    lt.foreach_get("loops", loops)
    uv = np.zeros(len(me.loops) * 2, np.float32)
    me.uv_layers.active.data.foreach_get("uv", uv)
    cn = np.zeros(len(me.loops) * 3, np.float32)
    me.corner_normals.foreach_get("vector", cn)
    uv = uv.reshape(-1, 2)[loops]
    cn = cn.reshape(-1, 3)[loops]
    np.savez(f"{bc.CACHE}/tree_LOD2_branches_blender.npz", positions=pos.reshape(-1, 3), tris=tris.reshape(-1, 3),
             corner_uv=uv, corner_normals=cn)
    print(time.strftime("%H:%M:%S"), f"branches {n0} -> {len(lt)} tris in {time.time()-t0:.0f}s", flush=True)


main()
