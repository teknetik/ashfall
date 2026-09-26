import bpy, json, glob, os
from mathutils import Vector
res = {}
for gl in sorted(glob.glob('/home/teknetik/code/ao2/art/karaveen_market_20260926/sources/polyhaven/*/*.gltf')):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=gl)
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    tris = 0; mn = Vector((1e9,)*3); mx = Vector((-1e9,)*3)
    for o in meshes:
        tris += sum(len(p.vertices) - 2 for p in o.data.polygons)
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c); mn = Vector(map(min, mn, w)); mx = Vector(map(max, mx, w))
    res[os.path.basename(os.path.dirname(gl))] = dict(objects=len(meshes), tris=tris, size=[round(v, 3) for v in (mx - mn)], min=[round(v,3) for v in mn],
        mats=sorted({s.material.name for o in meshes for s in o.material_slots if s.material}))
json.dump(res, open('/home/teknetik/code/ao2/art/karaveen_market_20260926/source-audit.json', 'w'), indent=1)
