"""Debug: colour faces by two-sided class (green front-only, red back-only->flip, yellow both->duplicate, blue hidden)
and test repeated decimation. blender.sh debug_vis.py -- <subject/attempt> <len|z> <metres>"""
import bpy, bmesh, sys, math
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
sys.path.insert(0, str(Path(__file__).resolve().parent))
from landmark_lib import import_join, coords, tris, footprint_yaw
import prepare as P
import review as R
a = sys.argv[sys.argv.index('--') + 1:]
src, axis, metres = a[0], a[1], float(a[2])
bpy.ops.wm.read_factory_settings(use_empty=True)
ob = import_join(P.HERE / src / 'model.glb')
P.fit_part(ob, dict(fit=(axis, metres)))
me = ob.data
bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table(); bm.normal_update()
bvh = BVHTree.FromBMesh(bm)
D = P.fib_dirs(); D = D[D[:, 2] > -0.05]
cls = []
for eps in (5e-4,):
    for f in bm.faces:
        n = np.array(f.normal); c = f.calc_center_median(); vis = []
        for sgn in (1.0, -1.0):
            ns = n * sgn; cand = D[D @ ns > 0.15]
            if len(cand) > 14: cand = cand[np.linspace(0, len(cand) - 1, 14).astype(int)]
            o = c + Vector(ns * eps); seen = False
            for d in cand:
                if bvh.ray_cast(o, Vector(d))[0] is None: seen = True; break
            vis.append(seen)
        cls.append(0 if vis == [True, False] else 1 if vis == [False, True] else 2 if vis == [True, True] else 3)
cls = np.array(cls)
print('classes front/back/both/hidden', np.bincount(cls, minlength=4).tolist())
# which hidden faces point down (undersides)?
nz = np.array([f.normal.z for f in bm.faces]); cz = np.array([f.calc_center_median().z for f in bm.faces])
h = cls == 3
print('hidden: normal.z<-0.3', int((h & (nz < -0.3)).sum()), ' centre z<0.3', int((h & (cz < 0.3)).sum()), ' others', int((h & (nz >= -0.3) & (cz >= 0.3)).sum()))
bm.free()
cols = [(0.2, 0.8, 0.2, 1), (0.9, 0.1, 0.1, 1), (1, 0.85, 0.1, 1), (0.15, 0.3, 0.9, 1)]
mats = []
for i, c in enumerate(cols):
    m = bpy.data.materials.new(f'c{i}'); m.use_nodes = True
    m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = c
    me.materials.append(m) if i else None
    mats.append(m)
me.materials.clear()
for m in mats: me.materials.append(m)
mi = cls.astype(np.int32); me.polygons.foreach_set('material_index', mi); me.update()
co = coords(me); size = (co.max(0) - co.min(0)).tolist()
out = P.HERE / src / 'review'
sc, cam = R.scene_setup(samples=8)
d = max(size[0], size[1], size[2] * 1.4) * 1.6 + 4
R.shoot(sc, cam, out, 'vis_tq_front_left', (-d * 0.7, -d * 0.75, size[2] * 0.6 + 3), (0, 0, size[2] * 0.45))
R.shoot(sc, cam, out, 'vis_tq_rear_right', (d * 0.7, d * 0.75, size[2] * 0.6 + 3), (0, 0, size[2] * 0.45))
R.shoot(sc, cam, out, 'vis_low_side', (0, -d * 0.6, 0.6), (0, 0, 1.0))
# decimation test
lod = bpy.data.objects.new('t', ob.data.copy()); bpy.context.scene.collection.objects.link(lod)
bm = bmesh.new(); bm.from_mesh(lod.data); bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4); bm.to_mesh(lod.data); bm.free()
P.select_only(lod)
for r in (0.1, 0.5, 0.5):
    dm = lod.modifiers.new('d', 'DECIMATE'); dm.ratio = r; dm.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier='d'); print('decimate', r, '->', tris(lod.data))
