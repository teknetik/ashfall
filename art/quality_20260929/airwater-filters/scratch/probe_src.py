import bpy, json, sys
from mathutils import Vector
out = []
for o in bpy.data.objects:
    if o.type != 'MESH':
        continue
    n = o.name
    if any(k in n.lower() for k in ('filter', 'pipe', 'downfeed', 'valve', 'tank', 'manifold', 'entry', 'door', 'porch', 'step', 'canopy', 'awning', 'drain')):
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        mn = [min(v[i] for v in bb) for i in range(3)]
        mx = [max(v[i] for v in bb) for i in range(3)]
        out.append((n, [c.name for c in o.users_collection], [round(x, 3) for x in mn], [round(x, 3) for x in mx], len(o.data.polygons),
                    [m.name for m in o.data.materials]))
for r in out:
    print(r)
print('TOTAL', len(bpy.data.objects), 'scene units', bpy.context.scene.unit_settings.system, bpy.context.scene.unit_settings.scale_length)
print('COLLECTIONS', [c.name for c in bpy.data.collections])
