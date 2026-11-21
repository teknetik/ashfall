import bpy, sys, os, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import mbk
from mbk import RG
import check as KC
bpy.ops.wm.open_mainfile(filepath=os.path.join(mbk.PROG, 'tools/export/tools.blend'))
mbk.rest_all()
for a_, b_, rig, par in (('tools_pliers', 'tools_pliers_b', 'tools_pliers_rig', 'pliers_jaws'), ('tools_cutters', 'tools_cutters_b', 'tools_cutters_rig', 'cutters_jaws')):
    a = bpy.data.objects[a_]; b = bpy.data.objects[b_]
    ga, gb = KC.Geo(a), KC.Geo(b)
    for v in (0.1, 0.5, 1.0):
        RG.set_params(bpy.data.objects[rig], {par: v})
        Ma, Mb = KC.world_matrix(a), KC.world_matrix(b)
        ta = ga.bvh(Ma); tb = gb.bvh(Mb, shrunk=True)
        ov = ta.overlap(tb)
        wa = ga.world(Ma)
        Ai = Ma.inverted()
        cs = np.array([tuple(Ai @ ((wa[ga.t[i][0]] + wa[ga.t[i][1]] + wa[ga.t[i][2]]) / 3)) for i, j in ov]) if ov else np.zeros((0, 3))
        print('OVERLAP', a_, v, len(ov), 'A-tri centroids local mm: min', np.round(cs.min(0) * 1000, 2) if len(cs) else None, 'max', np.round(cs.max(0) * 1000, 2) if len(cs) else None)
        seen = set()
        for c in cs:
            k = tuple(np.round(c * 1000, 1))
            if k not in seen:
                seen.add(k)
                if len(seen) <= 10: print('    ', k)
