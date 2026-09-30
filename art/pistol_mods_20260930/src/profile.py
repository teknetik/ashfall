# Ray-cast profile of the pistol surface in the metric frame (for fitting attachments).
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import pm_common as C

C.reset()
p = C.import_pistol()
bm = bmesh.new(); bm.from_mesh(p.data); bm.transform(p.matrix_world)
pb = BVHTree.FromBMesh(bm)
def hit(o, d):
    r = pb.ray_cast(Vector(o), Vector(d), 1.0)
    return r[0]
print('--- side silhouette at y=0 and y=+-0.01: top z / bottom z')
for x in np.arange(-0.135, 0.145, 0.005):
    row = []
    for y in (-0.012, 0.0, 0.012):
        t = hit((x, y, 0.3), (0, 0, -1)); b = hit((x, y, -0.3), (0, 0, 1))
        row.append('%s/%s' % ('%.4f' % t.z if t else '  -   ', '%.4f' % b.z if b else '  -   '))
    print('x %.3f  ' % x + '   '.join(row))
print('--- width: y+ / y- extents at z levels')
for x in np.arange(-0.135, 0.145, 0.005):
    row = []
    for z in (0.08, 0.07, 0.059, 0.05, 0.04, 0.03, 0.02, 0.0, -0.03, -0.06, -0.08):
        r = hit((x, 0.3, z), (0, -1, 0)); l = hit((x, -0.3, z), (0, 1, 0))
        row.append('%5.1f/%5.1f' % (r.y * 1000 if r else 99, l.y * 1000 if l else -99))
    print('x %.3f ' % x + ' '.join(row))
print('--- along x at axis (y=0.00075,z=0.05885): first hit from front', hit((-0.3, 0.00075, 0.05885), (1, 0, 0)))
for dz in (0.0, 0.004, 0.008, 0.010, 0.012, 0.0135, 0.015, 0.017, 0.019, 0.022):
    for s in (1, -1):
        h = hit((-0.3, 0.00075, 0.05885 + s * dz), (1, 0, 0))
        print('front hit dz=%+.4f -> x=%s' % (s * dz, '%.4f' % h.x if h else '-'))
for dy in (0.004, 0.008, 0.012, 0.0135, 0.016, 0.019):
    for s in (1, -1):
        h = hit((-0.3, 0.00075 + s * dy, 0.05885), (1, 0, 0))
        print('front hit dy=%+.4f -> x=%s' % (s * dy, '%.4f' % h.x if h else '-'))
