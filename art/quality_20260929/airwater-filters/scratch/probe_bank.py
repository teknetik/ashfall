import bpy
from mathutils import Vector
for o in sorted(bpy.data.objects, key=lambda o: o.name):
    if o.type!='MESH' or not o.name.startswith('air_water'): continue
    bb=[o.matrix_world@Vector(c) for c in o.bound_box]
    xa=[9-v.y for v in bb]; ya=[v.z-.5 for v in bb]; za=[v.x+20.6 for v in bb]
    if any(k in o.name for k in ('Filter','Feed','Downfeed','downfeed','Pipe clamp','Rainwater','Twin','Vessel','Door','door','Entry','entry','Porch','porch','step','Step','Front masonry','Canopy','Awning','Roof tank','tank')):
        print(f"{o.name[:48]:48s} x[{min(xa):6.2f},{max(xa):6.2f}] y[{min(ya):6.2f},{max(ya):6.2f}] z[{min(za):6.2f},{max(za):6.2f}] p{len(o.data.polygons)} m{[m.name[:18] for m in o.data.materials]}")
print('scene', bpy.context.scene.name, [s.name for s in bpy.data.scenes], 'colls', [c.name for c in bpy.data.collections][:20])
