import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, os.path.join(HERE, '..', '..', 'kit'))
import bpy
from mathutils import Vector
import geo as G, check as CK, pgeom as PG
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, '..', 'export', 'pistol.blend'))
for o in bpy.data.objects:
    if o.type == 'MESH' and 'sh' in o:
        b, nm = G.solid_check(o)
        if b or nm: print('OPEN', o.name, 'boundary', b, 'nonmanifold', nm, flush=True)
def where(a, b):
    A = bpy.data.objects[a]; B = bpy.data.objects[b]
    ga = CK.Geo(A); gb = CK.Geo(B)
    ta = ga.bvh(A.matrix_world, shrunk=True); tb = gb.bvh(B.matrix_world)
    ov = tb.overlap(ta)
    wa = ga.world(A.matrix_world)
    pts = []
    for i, j in ov:
        t = ga.t[j]
        c = (wa[t[0]] + wa[t[1]] + wa[t[2]]) / 3
        pts.append(PG.to_us(c))
    if pts:
        us_ = [p[0] for p in pts]; ss = [p[1] for p in pts]; ys = [p[2] for p in pts]
        print(a, 'x', b, len(ov), 'u %.1f..%.1f  s %.1f..%.1f  y %.1f..%.1f' % (min(us_), max(us_), min(ss), max(ss), min(ys), max(ys)), flush=True)
        import collections
        cnt = collections.Counter((round(p[0] / 4) * 4, round(p[1] / 4) * 4) for p in pts)
        print('    clusters (u,s):', cnt.most_common(8), flush=True)
    else:
        print(a, 'x', b, 'no overlap', flush=True)
where('pistol_scale_l', 'pistol_housing'); where('pistol_scale_r', 'pistol_housing'); where('pistol_scale_r', 'pistol_lead')
