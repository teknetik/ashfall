"""Unwrap truck LOD1/LOD2 (Blender) and export corner normals + MikkTSpace tangents.

blender -b --factory-startup --python truck_unwrap.py -- LOD2 LOD1
Normals: smooth with sharp edges > 60 deg. UV0: Smart UV Project (66 deg) computed on a
Laplacian-smoothed copy (same topology) + concave packing with a 4 px margin; copied
back so residual folds do not shatter the islands. Outputs cache/truck_<LOD>_baked_uv.npz
and cache/truck_<LOD>_tangents.npz consumed by truck_transfer.py / truck_write_baked.py.
"""
import json
import math
import os
import sys
import time

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import blender_common as bc  # noqa: E402

RES = {"LOD1": 2048, "LOD2": 1024}
MARGIN_PX = 4
SMOOTH_ITERS = 30
WORK = 100.0


def log(m):
    print(time.strftime("%H:%M:%S"), m, flush=True)


def unwrap(name):
    d = np.load(f"{bc.CACHE}/truck_{name}_geometry.npz")
    ob = bc.mesh_from_arrays(name, d["positions"] * WORK, d["tris"], sharp_angle_deg=60.0)
    sm = bc.mesh_from_arrays(name + "_unwrap", d["positions"] * WORK, d["tris"])
    mod = sm.modifiers.new("smooth", "SMOOTH")
    mod.factor = 0.5
    mod.iterations = SMOOTH_ITERS
    for o in bpy.context.scene.objects:
        o.select_set(o == sm)
    bpy.context.view_layer.objects.active = sm
    bpy.ops.object.modifier_apply(modifier="smooth")
    margin = MARGIN_PX / RES[name]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=margin, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(rotate=True, margin=margin, shape_method="CONCAVE")
    bpy.ops.object.mode_set(mode="OBJECT")
    assert len(sm.data.loops) == len(ob.data.loops) and len(sm.data.polygons) == len(ob.data.polygons)
    uvs = np.zeros(len(sm.data.loops) * 2, np.float32)
    sm.data.uv_layers.active.data.foreach_get("uv", uvs)
    ob.data.uv_layers.new(name="UVMap").data.foreach_set("uv", uvs)
    bpy.data.objects.remove(sm)
    tris, uv, cn = bc.corner_arrays(ob)
    u = uv.reshape(-1, 3, 2)
    a, c = u[:, 1] - u[:, 0], u[:, 2] - u[:, 0]
    cross = a[:, 0] * c[:, 1] - a[:, 1] * c[:, 0]
    stats = {"uvUtilisation": float(0.5 * np.abs(cross).sum()), "flippedUvTris": int((cross < 0).sum()),
             "zeroAreaUvTris": int((np.abs(cross) < 1e-12).sum()), "texture": RES[name], "marginPx": MARGIN_PX,
             "unwrapSmoothIterations": SMOOTH_ITERS, "trianglesAfterBlenderValidate": int(len(tris))}
    if stats["uvUtilisation"] < 0.2 or uv.max() > 1 or uv.min() < 0:
        raise RuntimeError(f"{name}: unwrap quality gate failed {stats}")
    np.savez(f"{bc.CACHE}/truck_{name}_baked_uv.npz", tris=tris, corner_uv=uv, corner_normals=cn)
    me = ob.data
    me.calc_tangents(uvmap="UVMap")
    n = len(me.loops)
    t = np.zeros(n * 3, np.float32)
    s = np.zeros(n, np.float32)
    me.loops.foreach_get("tangent", t)
    me.loops.foreach_get("bitangent_sign", s)
    np.savez(f"{bc.CACHE}/truck_{name}_tangents.npz", tangent=t.reshape(-1, 3), sign=s, normal=cn)
    with open(f"{bc.ROOT}/truck/unwrap-{name}.json", "w") as fh:
        json.dump(stats, fh, indent=1)
    log(f"{name}: {stats}")
    bpy.data.objects.remove(ob)


def main():
    bc.reset_scene()
    for name in sys.argv[sys.argv.index("--") + 1:]:
        unwrap(name)


main()
