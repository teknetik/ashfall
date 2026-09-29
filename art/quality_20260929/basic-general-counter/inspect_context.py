"""Read-only inspection of the v3 Basic General source scene (does not modify it)."""
import bpy, json
from pathlib import Path
SRC = '/home/teknetik/code/ao2/art/quality_20260909/basic-general/basic-general-source-v3.blend'
with bpy.data.libraries.load(SRC, link=False) as (src, dst):
    print('SCENES', src.scenes)
    dst.scenes = ['Basic General architectural repair']
sc = dst.scenes[0]
bpy.context.window.scene = sc
print('units', sc.unit_settings.system, sc.unit_settings.scale_length)
names = {}
for o in sc.objects:
    key = o.name.split('.')[0].rstrip('0123456789 -')
    names.setdefault(o.get('group'), []).append(o.name)
for g, l in names.items():
    print(g, len(l))
for o in sc.objects:
    if o.get('group') in ('Stock',) or o.name.startswith(('Counter', 'Service ledge', 'Stock', 'Rear wall core', 'Supplies')):
        d = o.dimensions
        print(o.name, [round(v, 3) for v in o.location], [round(v, 3) for v in d])
print('camera', sc.camera, [o.name for o in sc.objects if o.type in ('CAMERA', 'LIGHT')])
