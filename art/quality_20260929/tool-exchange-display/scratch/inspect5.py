import bpy
from mathutils import Vector
def A(v): return (v[0],v[2],-v[1])
print('NOBJ',len(bpy.data.objects))
for o in bpy.data.objects:
    if o.type!='MESH': continue
    bb=[A(o.matrix_world@Vector(c)) for c in o.bound_box]
    mn=[min(v[i] for v in bb) for i in range(3)]; mx=[max(v[i] for v in bb) for i in range(3)]
    n=o.name
    if ('Recessed' in n or 'Workshop' in n or 'Front masonry' in n or 'glass' in n.lower() or 'Rear' in n and 'wall' in n.lower() or 'Lintel' in n or 'Sill' in n or 'sill' in n) and mx[0]>-3.1 and mn[0]<-1.2:
        print('OB',n,[round(x,3) for x in mn],[round(x,3) for x in mx],len(o.data.polygons),[m.name for m in o.data.materials][:2])
