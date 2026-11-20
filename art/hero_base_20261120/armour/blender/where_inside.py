"""Which body part does each piece sink into? Per pose and piece: vertices inside the deformed body, grouped by the
body bone that owns the nearest skin there. Usage: blender.sh where_inside.py -- pieces=vest,carrier poses=rest,idle:0"""
import sys; sys.path.insert(0, '/home/teknetik/code/ao2/art/hero_base_20261120/armour/blender')
import bpy, bmesh
from mathutils.bvhtree import BVHTree
import hlib as H
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []; opt = dict(a.split('=', 1) for a in args if '=' in a)
PIECES = opt.get('pieces', 'vest,carrier').split(','); POSES = opt.get('poses', 'rest,idle:0').split(',')
arm, body = H.load_hero(); got = H.load_pieces(arm, PIECES)
gn = {g.index: g.name for g in body.vertex_groups}
dom = [gn[max(v.groups, key=lambda g: g.weight).group] if v.groups else '-' for v in body.data.vertices]
for pose in POSES:
    H.set_pose(arm, body, pose)
    dg = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new(); bm.from_object(body, dg); bm.transform(body.matrix_world); bm.normal_update(); bm.faces.ensure_lookup_table()
    bvh = BVHTree.FromBMesh(bm)
    for k in PIECES:
        tot = {}
        for w in H.eval_world_verts(got[k]):
            hit = bvh.find_nearest(w, 0.1)
            if hit[0] is None: continue
            sd = (w - hit[0]).dot(hit[1])
            if sd < 0:
                b = dom[bm.faces[hit[2]].verts[0].index]; t = tot.setdefault(b, [0, 0.0, 0]); t[0] += 1; t[1] = min(t[1], sd)
                if sd < -0.003: t[2] += 1
        print('WHERE %-20s %-8s' % (pose, k), ' '.join('%s:%d/%d/%.0fmm' % (b, t[0], t[2], t[1] * 1000) for b, t in sorted(tot.items(), key=lambda kv: -kv[1][0])), flush=True)
    bm.free()
