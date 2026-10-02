"""Shared Blender helpers for the Berms landmark scripts (review.py, prepare.py)."""
import bpy, math
import numpy as np


def import_join(path):
    """Import a .glb and join its meshes into one object with transforms applied."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    objs = [o for o in set(bpy.data.objects) - before]
    meshes = [o for o in objs if o.type == 'MESH']
    for o in bpy.context.selected_objects: o.select_set(False)
    for o in meshes:
        o.select_set(True)
        if o.parent:
            mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if len(meshes) > 1: bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    for o in objs:
        if o != ob and o.name in bpy.data.objects: bpy.data.objects.remove(o, do_unlink=True)
    return ob


def coords(me):
    co = np.empty(len(me.vertices) * 3, np.float64); me.vertices.foreach_get('co', co); return co.reshape(-1, 3)


def tris(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


def min_area_rect(pts, step=0.5):
    """(angle_deg, centre_xy, extent_uv) of the minimum-area rectangle of 2D points; u = long side."""
    best = None
    for deg in np.arange(0, 90, step):
        a = math.radians(deg); u = np.array([math.cos(a), math.sin(a)]); v = np.array([-math.sin(a), math.cos(a)])
        pu, pv = pts @ u, pts @ v
        eu, ev = pu.max() - pu.min(), pv.max() - pv.min()
        if best is None or eu * ev < best[0]:
            c = u * (pu.max() + pu.min()) / 2 + v * (pv.max() + pv.min()) / 2
            best = (eu * ev, deg, c, np.array([eu, ev]))
    _, deg, c, ext = best
    if ext[1] > ext[0]: deg += 90; ext = ext[::-1]
    return deg, c, ext


def footprint_yaw(co, band=1.0):
    """Yaw (degrees about Z) that turns the minimum-area rectangle of the lowest `band` metres onto the axes, long side
    on X."""
    z0 = co[:, 2].min(); pts = co[co[:, 2] < z0 + band][:, :2]
    if len(pts) < 10: pts = co[:, :2]
    deg, _, _ = min_area_rect(pts)
    return -deg
