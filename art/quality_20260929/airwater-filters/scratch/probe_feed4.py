import bpy, math
A=lambda p:(p.x,p.z,-p.y)
o=bpy.data.objects['air_water Roof to filter downfeed']
pts=[A(o.matrix_world@v.co) for v in o.data.vertices]
lowv=[p for p in pts if 6.0>p[1] and p[0]>3.1]
xs=[p[0] for p in lowv]; zs=[p[2] for p in lowv]; ys=[p[1] for p in lowv]
print('vertical end ring: n',len(lowv),'x',round(min(xs),3),round(max(xs),3),'z',round(min(zs),3),round(max(zs),3),'y',round(min(ys),3),round(max(ys),3))
print('centre est',round((min(xs)+max(xs))/2,3),round((min(zs)+max(zs))/2,3))
top=[p for p in pts if p[1]>6.9 and 3.1<p[0]]
print('top ring x,z',[(round(p[0],3),round(p[2],3)) for p in top][:8])
