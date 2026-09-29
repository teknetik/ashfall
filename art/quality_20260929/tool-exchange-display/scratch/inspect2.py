import bpy
from mathutils import Vector
print('scenes',[s.name for s in bpy.data.scenes], 'colls',[c.name for c in bpy.data.collections], 'objs',len(bpy.data.objects))
print('users', sum(1 for o in bpy.data.objects if o.users_collection))
# A-space: Ax=Bx, Ay=Bz, Az=-By
def A(v): return (v[0],v[2],-v[1])
for o in bpy.data.objects:
    if o.type!='MESH': continue
    bb=[A(o.matrix_world@Vector(c)) for c in o.bound_box]
    mn=[min(v[i] for v in bb) for i in range(3)]; mx=[max(v[i] for v in bb) for i in range(3)]
    if mx[0]>-3.2 and mn[0]<-1.1 and mx[2]>1.6 and mn[2]<3.2 and mx[1]>0.3 and mn[1]<2.7:
        print(o.name,[round(x,3) for x in mn],[round(x,3) for x in mx],len(o.data.polygons),[m.name for m in o.data.materials][:2], o.get('group'))
for n in ('Closed_floor','Closed floor'):
    pass
for o in bpy.data.objects:
    if 'floor' in o.name.lower() or 'Rear wall' in o.name or 'Front' in o.name[:30] and 'masonry' not in o.name:
        print('X',o.name,[round(v,2) for v in o.dimensions])
