import bpy
from mathutils import Vector
print('OBJS', len(bpy.data.objects), 'MATS', len(bpy.data.materials))
n = 0
for o in sorted(bpy.data.objects, key=lambda o: o.name):
    if 'air_water' not in o.name.lower():
        continue
    n += 1
    if any(k in o.name for k in ('Filter canister', 'Filter manifold', 'Filter wall mount', 'Roof to filter', 'Filter retainer (0.9, 0.52)', 'Front masonry segment 0 0', 'Service entry leaf 0')):
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        mn = [min(v[i] for v in bb) for i in range(3)]
        mx = [max(v[i] for v in bb) for i in range(3)]
        print(o.name, o.type, [round(x, 3) for x in mn], [round(x, 3) for x in mx], len(o.data.polygons) if o.type == 'MESH' else '', [m.name for m in o.data.materials] if o.type == 'MESH' else '',
              o.parent.name if o.parent else None, [round(x, 3) for x in o.location], [round(x, 3) for x in o.rotation_euler])
print('air_water objs', n)
print([c.name for c in bpy.data.collections])
for m in bpy.data.materials:
    if 'ater' in m.name or 'Filter' in m.name or 'Steel' in m.name:
        print('MAT', m.name)
