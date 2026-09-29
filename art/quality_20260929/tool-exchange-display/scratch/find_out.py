import bpy
col = bpy.data.collections['TE display and shutter (new)']
A = lambda v: (v.x, v.z, -v.y)
for o in col.objects:
    if o.name in ('TE_ShutterGuide_L', 'TE_ShutterGuide_R', 'TE_ShutterHardware', 'TE_DisplayGlazing'):
        continue
    bad = [A(o.matrix_world @ v.co) for v in o.data.vertices]
    bad = [b for b in bad if not (-2.9 - 1e-4 <= b[0] <= -1.4 + 1e-4 and .78 - 1e-4 <= b[1] <= 2.2 + 1e-4)]
    if bad:
        print('OUT', o.name, len(bad), [tuple(round(x, 4) for x in b) for b in bad[:4]])
