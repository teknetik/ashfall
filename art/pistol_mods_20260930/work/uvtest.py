import sys, math
sys.path.insert(0, '/home/teknetik/code/ao2/art/pistol_mods_20260930/src')
import bpy
import pm_common as C, pm_mats as PM, mods_barrel as MB, mods_cell as MC, mods_grip as MG
C.reset(); C.import_pistol(); C.import_hands(); M = PM.library()
objs = [fn(M)[0] for fn in (MG.build_stabilised, MG.build_gyro, MB.build_bored_alloy, MB.build_lattice_focused, MC.build_capacitor, MC.build_overclocked)]
def fill():
    a2 = 0
    for o in objs:
        uv = o.data.uv_layers.active.data
        for p in o.data.polygons:
            pts = [uv[li].uv for li in p.loop_indices]
            for i in range(1, len(pts) - 1):
                a2 += abs((pts[i] - pts[0]).cross(pts[i + 1] - pts[0])) / 2
    return a2
bpy.ops.object.select_all(action='DESELECT')
for o in objs: o.select_set(True)
bpy.context.view_layer.objects.active = objs[0]
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(52), island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
bpy.ops.uv.select_all(action='SELECT'); bpy.ops.uv.average_islands_scale()
for kw in (dict(rotate=True, margin_method='FRACTION', margin=0.0035, shape_method='CONCAVE'),
           dict(rotate=True, margin_method='FRACTION', margin=0.002, shape_method='CONCAVE'),
           dict(rotate=True, margin_method='FRACTION', margin=0.002, shape_method='CONVEX'),
           dict(rotate=True, rotate_method='ANY', margin_method='FRACTION', margin=0.002, shape_method='CONCAVE')):
    try:
        bpy.ops.uv.select_all(action='SELECT')
        r = bpy.ops.uv.pack_islands(**kw)
        bpy.ops.object.mode_set(mode='OBJECT')
        print('UVTEST', kw, r, round(fill(), 4))
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    except Exception as e:
        print('UVTEST ERR', kw, e)
