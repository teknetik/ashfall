import bpy, math
from mathutils import Vector
sc = bpy.data.scenes[0]
bpy.context.window.scene = sc
print('engine', sc.render.engine, sc.camera.name if sc.camera else None)
for o in bpy.data.objects:
    if o.type in ('LIGHT','CAMERA'): print(o.name, o.type, tuple(round(v,2) for v in o.location), o.data.energy if o.type=='LIGHT' else o.data.lens)
imgs=[(i.name,i.filepath,i.packed_file is not None) for i in bpy.data.images]
print(imgs[:8])
