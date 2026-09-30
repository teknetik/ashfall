"""Export MikkTSpace tangents (Blender) for the truck source and the rebaked LOD meshes.

blender -b --factory-startup --python truck_tangents.py -- LOD1 LOD2
Writes cache/truck_source_tangents.npz and cache/truck_<LOD>_tangents.npz with
per-corner tangent xyz + bitangent sign, in the corner order of the mesh arrays used
by truck_transfer.py (source: render-vertex tris; LOD: Blender-baked tris).
"""
import os
import sys
import time

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import blender_common as bc  # noqa: E402


def log(m):
    print(time.strftime("%H:%M:%S"), m, flush=True)


def tangents(ob):
    me = ob.data
    me.calc_tangents(uvmap="UVMap")
    n = len(me.loops)
    t = np.zeros(n * 3, np.float32)
    s = np.zeros(n, np.float32)
    me.loops.foreach_get("tangent", t)
    me.loops.foreach_get("bitangent_sign", s)
    nn = np.zeros(n * 3, np.float32)
    me.corner_normals.foreach_get("vector", nn)
    lv = np.zeros(n, np.int32)
    me.loops.foreach_get("vertex_index", lv)
    return t.reshape(-1, 3), s, nn.reshape(-1, 3), lv


def main():
    lods = sys.argv[sys.argv.index("--") + 1:]
    bc.reset_scene()
    out = f"{bc.CACHE}/truck_source_tangents.npz"
    if not os.path.exists(out):
        d = np.load(f"{bc.CACHE}/truck_source_render.npz")
        tris = d["tris"]
        ob = bc.mesh_from_arrays("source", d["positions"] * 100.0, tris, corner_uv=d["uv"][tris].reshape(-1, 2),
                                 vertex_normals=d["normals"])
        assert len(ob.data.polygons) == len(tris), "source faces changed"
        t, s, nn, lv = tangents(ob)
        assert (lv == tris.ravel()).all(), "source loop order changed"
        np.savez(out, tangent=t, sign=s, normal=nn)
        log(f"source tangents {len(t)}")
        bpy.data.objects.remove(ob)
    for name in lods:
        g = np.load(f"{bc.CACHE}/truck_{name}_geometry.npz")
        b = np.load(f"{bc.CACHE}/truck_{name}_baked_uv.npz")
        ob = bc.mesh_from_arrays(name, g["positions"] * 100.0, b["tris"], corner_uv=b["corner_uv"],
                                 corner_normals=b["corner_normals"])
        t, s, nn, lv = tangents(ob)
        assert (lv == b["tris"].ravel()).all(), f"{name} loop order changed"
        np.savez(f"{bc.CACHE}/truck_{name}_tangents.npz", tangent=t, sign=s, normal=nn)
        log(f"{name} tangents {len(t)}")
        bpy.data.objects.remove(ob)


main()
