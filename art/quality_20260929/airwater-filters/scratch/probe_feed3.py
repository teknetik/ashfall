import bpy, bmesh
from mathutils import Vector
A=lambda p:(round(p.x,3),round(p.z,3),round(-p.y,3))
o=bpy.data.objects['air_water Roof to filter downfeed']
bm=bmesh.new(); bm.from_mesh(o.data)
vis=set()
for v in bm.verts:
    if v.index in vis: continue
    st=[v]; c=[]
    while st:
        a=st.pop()
        if a.index in vis: continue
        vis.add(a.index); c.append(a)
        for e in a.link_edges: st.append(e.other_vert(a))
    ps=[A(o.matrix_world@v.co) for v in c]
    print(len(c),[round(min(p[i] for p in ps),3) for i in range(3)],[round(max(p[i] for p in ps),3) for i in range(3)])
o=bpy.data.objects['air_water Filter manifold']
ps=[A(o.matrix_world@v.co) for v in o.data.vertices]
print('manifold',[round(min(p[i] for p in ps),3) for i in range(3)],[round(max(p[i] for p in ps),3) for i in range(3)])
o=bpy.data.objects['air_water Filter canister 0.9']
ps=[A(o.matrix_world@v.co) for v in o.data.vertices]
print('canister',[round(min(p[i] for p in ps),3) for i in range(3)],[round(max(p[i] for p in ps),3) for i in range(3)])
o=bpy.data.objects['air_water Feed retaining clamp 2.4']
ps=[A(o.matrix_world@v.co) for v in o.data.vertices]
print('clamp2.4',[round(min(p[i] for p in ps),3) for i in range(3)],[round(max(p[i] for p in ps),3) for i in range(3)])
# wall face and what's on ground below the bank: porch top at y=0?
for n in ('air_water Closed floor',):
    o=bpy.data.objects[n]; ps=[A(o.matrix_world@v.co) for v in o.data.vertices]
    print(n,[round(min(p[i] for p in ps),3) for i in range(3)],[round(max(p[i] for p in ps),3) for i in range(3)])
