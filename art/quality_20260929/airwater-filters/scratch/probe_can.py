import bpy
from mathutils import Vector
o=bpy.data.objects['air_water Filter canister 1.7']
A=lambda p:(p.x,p.z,-p.y)
rows={}
for v in o.data.vertices:
    a=A(o.matrix_world@v.co)
    rows.setdefault(round(a[1],3),[]).append(((a[0]-1.7)**2+(a[2]-2.93)**2)**.5)
for y in sorted(rows): print(y, round(min(rows[y]),3), round(max(rows[y]),3), len(rows[y]))
for n in ('Filter retainer (1.7, 1.94)','Filter wall mount 1.7','Roof to filter downfeed','Filter manifold','Filter manifold inlet 1.7'):
    o=bpy.data.objects['air_water '+n]
    print(n, [ (round(a[0],3),round(a[1],3),round(a[2],3)) for a in sorted({tuple(round(c,3) for c in A(o.matrix_world@v.co)) for v in o.data.vertices})][:14])
for m in ('Retained WardSteel','Baked facade Steel'):
    print(m,[ (n.image.name if n.type=='TEX_IMAGE' else n.type) for n in bpy.data.materials[m].node_tree.nodes][:8])
