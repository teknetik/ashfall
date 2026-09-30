import sys
sys.path.insert(0, '/home/teknetik/code/ao2/art/pistol_mods_20260930/src')
import bpy, bmesh, numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import pm_common as C
C.reset(); p = C.import_pistol(); hs = C.import_hands()
def bvh(objs):
    bm = bmesh.new()
    for o in objs:
        t = bmesh.new(); t.from_mesh(o.data); t.transform(o.matrix_world); me = bpy.data.meshes.new('t'); t.to_mesh(me); bm.from_mesh(me)
    return BVHTree.FromBMesh(bm)
PB = bvh([p]); HB = bvh(hs); ALL = bvh([p] + hs)
cam = C.fp_camera('hip'); E = cam.matrix_world.translation
print('PROBE cam', tuple(round(x,3) for x in E))
for z in np.arange(0.05, -0.005, -0.005):
    row = []
    for x in np.arange(0.05, 0.135, 0.005):
        h = PB.ray_cast(Vector((x, -0.2, z)), Vector((0, 1, 0)), 0.3)
        if h[0] is None: row.append('   .   '); continue
        q = h[0]; hd = HB.find_nearest(q, 0.05); hd = hd[3] if hd[0] is not None else 1
        d = (q - E); vis = ALL.ray_cast(E, d.normalized(), d.length - 0.0015)[0] is None
        row.append('%5.1f%s%s' % (q.y * 1000, 'v' if vis else ' ', 'H' if hd < 0.006 else ' '))
    print('PROBE z %.3f ' % z + ' '.join(row))
print('PROBE cols x', ' '.join('%7.3f' % x for x in np.arange(0.05, 0.135, 0.005)))
