import bpy
from mathutils import Vector
for o in sorted(bpy.data.objects,key=lambda o:o.name):
    if o.type!='MESH' or not o.name.startswith('air_water'): continue
    bb=[o.matrix_world@Vector(c) for c in o.bound_box]
    xa=[9-v.y for v in bb]; ya=[v.z-.5 for v in bb]; za=[v.x+20.6 for v in bb]
    if min(ya)<0.3 and max(za)>2.6 and not any(k in o.name for k in ('Front masonry','anchor','Awning')):
        print(o.name,[round(min(xa),2),round(min(ya),2),round(min(za),2)],[round(max(xa),2),round(max(ya),2),round(max(za),2)])
