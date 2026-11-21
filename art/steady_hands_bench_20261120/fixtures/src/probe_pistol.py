# Probe of the pistol family's export for the fixtures that hold it (read-only): the stripped frame's outline along
# its length, so the vise seat, the cradle saddles and the work-mat seat are placed on real numbers.
#   SH/blender.sh fixtures/src/probe_pistol.py  -> fixtures/layout/pistol_profile.json
# Pistol frame P: metres, muzzle -X, up +Z, the player's right +Y.
import bpy, os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
PROG = os.path.abspath(os.path.join(HERE, '..', '..'))
bpy.ops.wm.open_mainfile(filepath=os.path.join(PROG, 'pistol', 'export', 'pistol.blend'))
P = {}
for o in bpy.data.objects:
    if o.type == 'MESH' and 'sh' in o:
        P[json.loads(o['sh'])['id']] = o
dg = bpy.context.evaluated_depsgraph_get()


def pts(ids):
    out = []
    for i in ids:
        o = P[i].evaluated_get(dg); me = o.to_mesh()
        co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
        mw = np.array(o.matrix_world)
        out.append(co @ mw[:3, :3].T + mw[:3, 3]); o.to_mesh_clear()
    return np.vstack(out)


STRIPPED = [i for i in ('pistol.frame', 'pistol.barrel', 'pistol.dust_cover', 'pistol.trigger', 'pistol.cell_bus', 'pistol.cell_latch', 'pistol.status_lamp') if i in P]
res = {'frame': 'P: metres, muzzle -X, up +Z, right +Y', 'stripped_parts': STRIPPED, 'bins': []}
A = pts(STRIPPED)
res['stripped_bounds'] = [[round(float(x), 5) for x in A.min(0)], [round(float(x), 5) for x in A.max(0)]]
for x0 in np.arange(-0.135, 0.105, 0.005):
    m = (A[:, 0] >= x0) & (A[:, 0] < x0 + 0.005)
    if m.sum() < 3:
        continue
    q = A[m]
    top = q[q[:, 2] > q[:, 2].max() - 0.028]
    low = q[q[:, 2] < q[:, 2].min() + 0.012]
    res['bins'].append({'x': round(float(x0 + 0.0025), 4), 'zmin': round(float(q[:, 2].min()), 4), 'zmax': round(float(q[:, 2].max()), 4),
                        'ymin': round(float(q[:, 1].min()), 4), 'ymax': round(float(q[:, 1].max()), 4),
                        'top28_y': [round(float(top[:, 1].min()), 4), round(float(top[:, 1].max()), 4)],
                        'low12_y': [round(float(low[:, 1].min()), 4), round(float(low[:, 1].max()), 4)]})
for i in ('pistol.cell', 'pistol.frame', 'pistol.card_a', 'pistol.card_b'):
    if i in P:
        q = pts([i]); res[i] = {'min': [round(float(x), 5) for x in q.min(0)], 'max': [round(float(x), 5) for x in q.max(0)],
                                'matrix_world': [[round(float(x), 6) for x in r] for r in P[i].matrix_world]}
        res[i]['marks'] = {e.name: [[round(float(x), 6) for x in r] for r in e.matrix_world] for e in bpy.data.objects
                           if e.type == 'EMPTY' and e.name.startswith(P[i].name + '__')}
# the underside of the stripped frame, by rays cast upward on a 1 mm grid (vertices alone miss long flat faces)
from mathutils import Vector
from mathutils.bvhtree import BVHTree
V, T_ = [], []
for i in STRIPPED:
    o = P[i].evaluated_get(dg); me = o.to_mesh(); me.calc_loop_triangles()
    off = len(V)
    V += [o.matrix_world @ v.co for v in me.vertices]
    T_ += [tuple(off + k for k in t.vertices) for t in me.loop_triangles]
    o.to_mesh_clear()
tree = BVHTree.FromPolygons(V, T_, all_triangles=True)
under = []
for xi in range(-132, 100):
    x = xi * 0.001
    zs, ys = [], []
    for yi in range(-28, 29):
        h = tree.ray_cast(Vector((x, yi * 0.001, -0.2)), Vector((0, 0, 1)))
        if h[0] is not None:
            zs.append(h[0].z); ys.append(yi * 0.001)
    if zs:
        zm = min(zs)
        lowy = [y for y, z in zip(ys, zs) if z < zm + 0.0015]
        under.append([round(x, 4), round(zm, 5), round(min(lowy), 4), round(max(lowy), 4), round(min(ys), 4), round(max(ys), 4)])
res['under'] = {'columns': ['x', 'z of the underside', 'y from', 'y to of the lowest 1.5 mm', 'y from', 'y to of everything'], 'rows': under}
json.dump(res, open(os.path.join(PROG, 'fixtures', 'layout', 'pistol_profile.json'), 'w'), indent=1)
print('PROBE DONE', len(res['bins']))
