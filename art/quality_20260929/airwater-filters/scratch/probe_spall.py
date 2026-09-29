import bpy
from mathutils import Vector
dg=bpy.context.evaluated_depsgraph_get(); sc=bpy.context.scene
pts=[]
for iy in range(0,230):
    yA=.05+iy*.01
    for ix in range(0,340):
        xA=.30+ix*.01
        hit,loc,n,i,ob,m=sc.ray_cast(dg,Vector((xA,-9.0,yA)),Vector((0,1,0)),distance=12)
        if hit and ob.name.startswith('air_water Front masonry'):
            z=-loc.y
            if z<2.715: pts.append((round(xA,2),round(yA,2),round(z,3)))
print('recess samples',len(pts))
if pts:
    xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
    print('bbox x',min(xs),max(xs),'y',min(ys),max(ys))
# cluster by 0.05 cell
cells={}
for x,y,z in pts: cells.setdefault((int(x/.05),int(y/.05)),[]).append(z)
print(sorted((round(k[0]*.05,2),round(k[1]*.05,2),len(v),round(min(v),3)) for k,v in cells.items()))
