# Diagnostic (model-bench): is the cavity cutter really the core grown by 0.5 mm?
import bpy, os, sys
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, '..', '..', 'tools', 'src')]
bpy.ops.wm.read_factory_settings(use_empty=True)
import mbk, fx_m3 as F3
from mbk import G
g = F3.grip_core_live()
raw = bpy.data.objects.new('raw', g['mesh'].copy()); bpy.context.scene.collection.objects.link(raw)
raw.data.transform(F3.core_in_die() @ g['matrix'])
cut = F3.core_cutter('cut', 0.0005, 1.0)
print('DIAG solid raw', G.solid_check(raw), 'cut', G.solid_check(cut), 'verts', len(raw.data.vertices), len(cut.data.vertices))
tc = BVHTree.FromObject(cut, bpy.context.evaluated_depsgraph_get())
d = []
for v in raw.data.vertices:
    loc, n, i, dist = tc.find_nearest(v.co)
    inside = (v.co - loc).dot(n) < 0
    d.append(dist if inside else -dist)
d = np.array(d)
print('DIAG core verts: inside the cutter', int((d > 0).sum()), 'outside', int((d <= 0).sum()), 'min clearance mm', round(float(d.min()) * 1000, 3), 'median', round(float(np.median(d)) * 1000, 3))
blk = mbk.box('blk', (-0.06, -0.073, 0.0), (0.06, 0.073, 0.034))
v0 = G._volume(blk)
blk = G.boolean(blk, [cut])
print('DIAG block volume removed (cm3)', round((v0 - G._volume(blk)) * 1e6, 2), 'core half volume approx (cm3)', round(G._volume(raw) * 1e6 / 2, 2))
