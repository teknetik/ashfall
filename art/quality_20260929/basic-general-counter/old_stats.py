import bpy, json
from pathlib import Path
OUT = Path('/home/teknetik/code/ao2/art/quality_20260929/basic-general-counter')
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'basic-general-counter-source-v1.blend'))
sc = bpy.data.scenes['Basic General architectural repair']
t = 0; n = 0
for o in sc.objects:
    if o.get('bgc_retired') and o.type == 'MESH':
        o.data.calc_loop_triangles(); t += len(o.data.loop_triangles); n += 1
print('OLD_RETIRED', n, t)
(OUT / 'old-stock-stats.json').write_text(json.dumps({'retiredObjects': n, 'retiredTriangles': t}))
