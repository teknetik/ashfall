"""Experiment: which upper-arm share lets the vest's shoulder pad ride the deltoid with least poke-through?
Loads out/TS_FieldVest.glb, re-weights the pad for each share and counts pad vertices inside the deformed body."""
import sys; sys.path.insert(0, '/home/teknetik/code/ao2/art/hero_base_20261120/armour/blender')
import bpy, bmesh
from mathutils.bvhtree import BVHTree
import hlib as H
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []; opt = dict(a.split('=', 1) for a in args if '=' in a)
CUR = float(opt.get('cur', 0.4)); SHARES = [float(x) for x in opt.get('shares', '0.25,0.4,0.55,0.7,0.85').split(',')]
POSES = 'rest,idle:0,walk:25,walk:75,run:25,run:75,rifle,clip:rifle_573:50,clip:aim_95:50,clip:carry_334:50,clip:draw_222:50'.split(',')
arm, body = H.load_hero(); v = H.load_pieces(arm, ['vest'])['vest']
ga = v.vertex_groups['LeftArm']; gs = v.vertex_groups['LeftShoulder']
f = {}; ls = {}
for vt in v.data.vertices:
    wa = next((g.weight for g in vt.groups if g.group == ga.index), 0.0)
    if wa > 1e-4: f[vt.index] = min(1.0, wa / CUR); ls[vt.index] = next((g.weight for g in vt.groups if g.group == gs.index), 0.0)
pad = [i for i, x in f.items() if x > 0.5]
print('PADTRY pad verts', len(f), 'core', len(pad))
for sh in SHARES:
    for i, x in f.items():
        ga.add([i], x * sh, 'REPLACE'); gs.add([i], max(0.0, ls[i] - x * (1 - CUR) + x * (1 - sh)), 'REPLACE')
    row = []
    for pose in POSES:
        H.set_pose(arm, body, pose)
        dg = bpy.context.evaluated_depsgraph_get()
        bm = bmesh.new(); bm.from_object(body, dg); bm.transform(body.matrix_world); bm.normal_update(); bvh = BVHTree.FromBMesh(bm)
        ws = H.eval_world_verts(v); n = 0; worst = 0.0; far = 0.0
        for i in pad:
            hit = bvh.find_nearest(ws[i], 0.15)
            if hit[0] is None: continue
            sd = (ws[i] - hit[0]).dot(hit[1])
            if sd < 0: n += 1; worst = min(worst, sd)
            far = max(far, sd)
        bm.free(); row.append('%d/%.0f/%.0f' % (n, worst * 1000, far * 1000))
    print('PADTRY share %.2f' % sh, ' '.join(row), flush=True)
print('PADTRY poses', ' '.join(POSES), '(inside / worst mm / farthest off mm)')
