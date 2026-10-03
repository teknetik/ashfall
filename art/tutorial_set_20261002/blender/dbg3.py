import sys; sys.path.insert(0,'/home/teknetik/code/ao2/art/tutorial_set_20261002/blender')
from fitlib import *
bpy.ops.wm.open_mainfile(filepath=str(OUT/'mpfb'/'suit_v5.blend'))
for o in bpy.data.objects:
    if o.type=='MESH':
        uv=o.data.uv_layers
        info=[(l.name, l.active_render) for l in uv]
        us=[d.uv for d in uv.active.data][:2000] if uv.active else []
        print('UV',o.name,info, 'range', (min(u.x for u in us),max(u.x for u in us),min(u.y for u in us),max(u.y for u in us)) if us else None, [s.material.name for s in o.material_slots])
