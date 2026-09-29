import bpy
from mathutils import Vector
A=lambda p:(p.x,p.z,-p.y)
for o in sorted(bpy.data.objects,key=lambda o:o.name):
    if o.type!='MESH': continue
    bb=[A(o.matrix_world@Vector(c)) for c in o.bound_box]
    mn=[min(b[i] for b in bb) for i in range(3)]; mx=[max(b[i] for b in bb) for i in range(3)]
    n=o.name
    if any(k in n for k in ('Filter','Feed','downfeed','Twin','Vessel','Pipe clamp','Rainwater')) or ('Front masonry' in n) or ('Service entry' in n and 'hinge' not in n and 'seal' not in n) or any(k in n for k in ('porch','Porch','step','Step','Awning','Canopy','Door','door','Roof')):
        print(f"{n[:46]:46s} x[{mn[0]:6.2f},{mx[0]:6.2f}] y[{mn[1]:6.2f},{mx[1]:6.2f}] z[{mn[2]:6.2f},{mx[2]:6.2f}] p{len(o.data.polygons)} {[m.name[:14] for m in o.data.materials]}")
