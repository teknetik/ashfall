import bpy
from mathutils import Vector
dg=bpy.context.evaluated_depsgraph_get(); sc=bpy.context.scene
# fine scan of wall face z over the bank zone (A-space) using base blend (already A-space, B=(xA,-zA,yA))
def ray(xA,yA):
    o=Vector((xA,-9.0,yA)); d=Vector((0,1,0))    # from +z(front) towards wall: B y = -zA  -> front is -y ; ray starts at zA=9 -> B y=-9, goes +y
    hit,loc,n,i,ob,m=sc.ray_cast(dg,o,d,distance=12)
    return (round(-loc.y,4),ob.name) if hit else (None,None)
from collections import Counter
cnt=Counter(); bad=[]
for iy in range(0,90):
    yA=.15+iy*.025
    for ix in range(0,100):
        xA=.45+ix*.03
        z,n=ray(xA,yA)
        if n and n.startswith('air_water Front masonry'):
            cnt[round(z,3)]+=1
            if abs(z-2.73)>.004: bad.append((round(xA,2),round(yA,2),z))
print(cnt.most_common(6)); print(len(bad)); print(bad[:60])
