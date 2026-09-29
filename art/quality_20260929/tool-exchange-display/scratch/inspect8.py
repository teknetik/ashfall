import bpy
from mathutils import Vector
def A(v): return (v[0], v[2], -v[1])
for o in bpy.data.objects:
    if o.type != 'MESH':
        continue
    if o.get('group') in ('Workshop shutter', 'Separate shop signage', 'Awning', 'Stone ground transition', 'Attached services'):
        bb = [A(o.matrix_world @ Vector(c)) for c in o.bound_box]
        mn = [min(v[i] for v in bb) for i in range(3)]; mx = [max(v[i] for v in bb) for i in range(3)]
        print('G', o.get('group'), '|', o.name, [round(x, 3) for x in mn], [round(x, 3) for x in mx], len(o.data.polygons), [m.name for m in o.data.materials][:1])
