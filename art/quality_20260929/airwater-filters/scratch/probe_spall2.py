import bpy, json
from mathutils import Vector
dg=bpy.context.evaluated_depsgraph_get(); sc=bpy.context.scene
pts=[]
for iy in range(0,230):
    yA=.05+iy*.01
    for ix in range(0,340):
        xA=.30+ix*.01
        hit,loc,n,i,ob,m=sc.ray_cast(dg,Vector((xA,-9.0,yA)),Vector((0,1,0)),distance=12)
        if hit and ob.name.startswith('air_water Front masonry') and -loc.y<2.715: pts.append((round(xA,2),round(yA,2),round(-loc.y,3)))
json.dump({'note':'wall-face samples (A-space x,y,z) at 1 cm pitch, x .30-3.69, y .05-2.34, where the front plaster face is recessed (z<2.715); plane elsewhere is z=2.73. Source: airwater-review-base.blend ray casts.','samples':pts}, open('/home/teknetik/code/ao2/art/quality_20260929/airwater-filters/wall-recess-samples.json','w'))
print(len(pts))
