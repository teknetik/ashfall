import bpy
from mathutils import Vector
def A(v): return (v[0],v[2],-v[1])
sc=bpy.data.scenes[0]
print('SC',sc.name,sc.camera,sc.render.engine,sc.world, [ (o.name,o.type) for o in sc.objects if o.type!='MESH'])
g={}
for o in bpy.data.objects:
    if o.type!='MESH': continue
    bb=[A(o.matrix_world@Vector(c)) for c in o.bound_box]
    mn=[min(v[i] for v in bb) for i in range(3)]; mx=[max(v[i] for v in bb) for i in range(3)]
    k=o.get('group')
    d=g.setdefault(k,[[9]*3,[-9]*3,0]); d[2]+=1
    for i in range(3): d[0][i]=min(d[0][i],mn[i]); d[1][i]=max(d[1][i],mx[i])
for k,v in g.items(): print('G',k,[round(x,2) for x in v[0]],[round(x,2) for x in v[1]],v[2])
for o in bpy.data.objects:
    if o.get('group') in ('Review only','Stone ground transition','Attached services') : print('R',o.name,o.get('group'))
m=bpy.data.materials['Relay_WardPaint.007']
print([ (n.type, getattr(n,'image',None) and n.image.name) for n in m.node_tree.nodes])
