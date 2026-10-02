"""Where do skinned edges stretch in each clip? Usage: blender.sh inspect_stretch.py -- <record folder>
Writes stretch.json (edges stretched >1.8x AND >1 cm, grouped by dominant bone, worst frame) and close-up renders of the
shoulders and hip/holster at the worst frame of the chosen clips."""
import bpy, sys, json, math
from pathlib import Path
from mathutils import Vector, Matrix
import numpy as np
HERE = Path(sys.argv[sys.argv.index('--') + 1]); OUT = HERE / 'renders'
exec(compile((HERE / 'inspect_blender.py').read_text().split('# 1. Rigged model at rest.')[0].split('report = {}')[1], 'helpers', 'exec'))
res = {}
for stem in ['idle_246', 'idle_252', 'talk_309', 'talk_313', 'talk_314']:
    s = reset(); arm, mesh = load(HERE / f'{stem}.glb'); act = arm.animation_data.action
    groups = {g.index: g.name for g in mesh.vertex_groups}
    n = len(mesh.data.vertices); dom = np.full(n, -1)
    best = np.zeros(n)
    for v in mesh.data.vertices:
        for g in v.groups:
            if g.weight > best[v.index]: best[v.index] = g.weight; dom[v.index] = g.group
    arm.animation_data.action = None
    for pb in arm.pose.bones: pb.matrix_basis = Matrix()
    bpy.context.view_layer.update(); c0, e = world_verts(mesh); L0 = np.linalg.norm(c0[e[:, 0]] - c0[e[:, 1]], axis=1)
    arm.animation_data.action = act
    f0, f1 = map(int, act.frame_range); worst = (-1, 0, None)
    for f in range(f0, f1 + 1, 6):
        s.frame_set(f); bpy.context.view_layer.update(); c, _ = world_verts(mesh)
        L = np.linalg.norm(c[e[:, 0]] - c[e[:, 1]], axis=1)
        bad = (L > 1.8 * L0 + 1e-9) & (L - L0 > .01)
        if bad.sum() > worst[1]: worst = (f, int(bad.sum()), bad.copy(), L.copy())
    f, cnt, bad, L = worst
    by = {}
    if cnt:
        for i in np.nonzero(bad)[0]:
            b = groups.get(int(dom[e[i, 0]]), '?'); d = by.setdefault(b, [0, 0.0]); d[0] += 1; d[1] = max(d[1], float(L[i] - L0[i]))
    res[stem] = dict(worst_frame=f, edges=cnt, by_bone={k: dict(edges=v[0], max_extra_m=round(v[1], 3)) for k, v in sorted(by.items(), key=lambda kv: -kv[1][0])})
    if stem in ('idle_246', 'idle_252', 'talk_313', 'talk_309'):
        s.frame_set(f if f >= 0 else (f0 + f1) // 2); bpy.context.view_layer.update()
        def bone(nm): return arm.matrix_world @ arm.pose.bones[nm].head
        ls, rs = bone('LeftArm'), bone('RightArm'); mid = (ls + rs) / 2
        shoot(f'{stem}_shoulders', (mid.x, mid.y, mid.z - .05), 1.5, 25, mid.z + .1, lens=50, res=(900, 700))
        hp = bone('Hips'); shoot(f'{stem}_hips', (hp.x, hp.y, hp.z - .05), 1.6, -30, hp.z + .15, lens=50, res=(900, 700))
(HERE / 'stretch.json').write_text(json.dumps(res, indent=2)); print('STRETCH DONE')
