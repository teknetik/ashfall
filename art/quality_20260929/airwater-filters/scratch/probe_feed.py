import bpy
o = bpy.data.objects['air_water Roof to filter downfeed']
pts = sorted({(round(9-(o.matrix_world@v.co).y,3), round((o.matrix_world@v.co).z-.5,3), round((o.matrix_world@v.co).x+20.6,3)) for v in o.data.vertices}, key=lambda p:(-p[1],p[0]))
print('FEED verts (xA,yA,zA)', len(pts))
for p in pts: print(p)
for n in ('air_water Feed flange (1.7, 0.65)','air_water Feed retaining clamp 2.4','air_water Feed stand-off 2.4'):
    ob=bpy.data.objects[n]; vs=[(9-(ob.matrix_world@v.co).y,(ob.matrix_world@v.co).z-.5,(ob.matrix_world@v.co).x+20.6) for v in ob.data.vertices]
    print(n,[round(min(v[i] for v in vs),3) for i in range(3)],[round(max(v[i] for v in vs),3) for i in range(3)])
