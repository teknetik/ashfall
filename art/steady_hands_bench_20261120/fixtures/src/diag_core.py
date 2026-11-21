# Diagnostic (model-bench): where grip.core at fixtures_mould_tang__mark_seat_core meets the tang mould.
import bpy, os, sys, json
import numpy as np
from mathutils import Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, '..', '..', 'tools', 'src')]
import mbk
import check as KC
PROG = mbk.PROG
bpy.ops.wm.open_mainfile(filepath=os.path.join(PROG, 'fixtures', 'export', 'fixtures.blend'))
tang = bpy.data.objects['fixtures_mould_tang']; mk = bpy.data.objects['fixtures_mould_tang__mark_seat_core']
ext = KC.load_external(os.path.join(PROG, 'grip', 'export', 'grip.blend'), ids=['grip.core'], after_sequence=False)
core = ext['grip.core']
Mc = KC.world_matrix(mk)
gt = KC.Geo(tang); gc = KC.Geo(core)
tt = gt.bvh(KC.world_matrix(tang)); tc = gc.bvh(Mc)
pairs = tt.overlap(tc)
Ti = KC.world_matrix(tang).inverted()
dg = bpy.context.evaluated_depsgraph_get()
me = tang.evaluated_get(dg).to_mesh(); me.calc_loop_triangles()
pts = []
for a, b in pairs[:4000]:
    t = me.loop_triangles[a]
    pts.append(tuple(sum((me.vertices[v].co for v in t.vertices), me.vertices[0].co * 0) / 3))
pts = np.array(pts) * 1000
print('DIAG pairs', len(pairs), 'die tris', len(me.loop_triangles))
if len(pts):
    print('DIAG die-local mm min', pts.min(0).round(1), 'max', pts.max(0).round(1))
    h, e = np.histogram(pts[:, 2], bins=8)
    print('DIAG z hist', h.tolist(), e.round(1).tolist())
print('DIAG core mark local', [round(x, 5) for x in (Ti @ Mc).translation])
