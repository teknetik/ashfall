import bpy
A=lambda p:(p.x,p.z,-p.y)
o=bpy.data.objects['air_water Roof to filter downfeed']
pts=sorted({tuple(round(c,2) for c in A(o.matrix_world@v.co)) for v in o.data.vertices},key=lambda p:(p[1],p[0]))
# centre-line: group by rounded y or x
import collections
g=collections.defaultdict(list)
for p in pts: g[(round(p[1],1))].append(p)
for k in sorted(g): 
    xs=[p[0] for p in g[k]]; zs=[p[2] for p in g[k]]
    print(k, 'x',min(xs),max(xs),'z',min(zs),max(zs),len(g[k]))
