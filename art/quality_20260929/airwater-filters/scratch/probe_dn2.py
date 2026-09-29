import bpy
A=lambda p:(p.x,p.z,-p.y)
o=bpy.data.objects['air_water Roof to filter downfeed']
P=[A(o.matrix_world@v.co) for v in o.data.vertices]
for p in sorted(P,key=lambda p:(round(p[0],1),p[1],p[2])):
    if p[1]<3 : print(tuple(round(c,3) for c in p))
print('---vertical')
V=[p for p in P if 3<p[1]<7.0]
print(len(V))
lo=[p for p in P if p[1]<2.5]
