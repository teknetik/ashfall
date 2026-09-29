import bpy
from mathutils import Vector
for o in sorted(bpy.data.objects, key=lambda o: o.name):
    if o.type != 'MESH':
        continue
    n = o.name
    if any(k in n for k in ('Filter', 'Front filter', 'downfeed', 'Downfeed', 'Pipe', 'pipe', 'Feed', 'feed', 'header', 'Header', 'Manifold', 'Roof tank', 'Tank ')) and 'gallery' not in n and 'Tank lid' not in n and 'saddle' not in n:
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        mn = [min(v[i] for v in bb) for i in range(3)]
        mx = [max(v[i] for v in bb) for i in range(3)]
        print(n, [round(x, 3) for x in mn], [round(x, 3) for x in mx], len(o.data.polygons), [m.name for m in o.data.materials], o.parent.name if o.parent else None)
