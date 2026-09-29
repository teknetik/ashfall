import bpy, json
from mathutils import Vector
rows=[]
for o in bpy.data.objects:
    if o.type!='MESH': continue
    n=o.name
    if any(k in n for k in ('Recessed_tool','Shutter','Shop_sign','Front_masonry','Exact')) or 'display' in n.lower():
        bb=[o.matrix_world@Vector(c) for c in o.bound_box]
        mn=[min(v[i] for v in bb) for i in range(3)]; mx=[max(v[i] for v in bb) for i in range(3)]
        rows.append((n,[round(x,3) for x in mn],[round(x,3) for x in mx],len(o.data.polygons),[m.name for m in o.data.materials]))
for r in rows: print(r)
print(len(bpy.data.objects), bpy.context.scene.unit_settings.system)
