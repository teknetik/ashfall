"""Customer's view across a trade counter: each clip at three phases, with a 1.0 m counter box in front of Brann.
Also measures hand reach (forward of the root, metres) so the scene placement keeps hands out of the counter top.
Usage: blender.sh inspect_counter.py -- <record folder>"""
import bpy, sys, json, math
from pathlib import Path
from mathutils import Vector, Matrix
import numpy as np
HERE = Path(sys.argv[sys.argv.index('--') + 1]); OUT = HERE / 'renders'
exec(compile((HERE / 'inspect_blender.py').read_text().split('# 1. Rigged model at rest.')[0].split('report = {}')[1], 'helpers', 'exec'))
res = {}
for stem in ['idle_246', 'idle_252', 'talk_313', 'talk_314', 'talk_309']:
    s = reset(); s.cycles.samples = 16; arm, mesh = load(HERE / f'{stem}.glb'); act = arm.animation_data.action
    groups = {g.name: g.index for g in mesh.vertex_groups}
    hand_ids = {groups[n] for n in ('LeftHand', 'RightHand', 'LeftForeArm', 'RightForeArm') if n in groups}
    hand = np.array([any(g.group in hand_ids and g.weight > .5 for g in v.groups) for v in mesh.data.vertices])
    f0, f1 = map(int, act.frame_range); reach = []; low = []
    for f in range(f0, f1 + 1, 3):
        s.frame_set(f); bpy.context.view_layer.update(); c, _ = world_verts(mesh); hv = c[hand]
        reach.append(float(-hv[:, 1].min())); low.append(float(hv[:, 2].min()))
        # forward reach of hand vertices that are below 1.05 m (where a counter top would be)
    res[stem] = dict(hand_forward_max_m=round(max(reach), 3), hand_lowest_m=round(min(low), 3))
    # Counter: top at 0.95 m (feet will be grounded in Unity; here lift the figure by the clip's foot offset).
    s.frame_set(f0); bpy.context.view_layer.update(); c, _ = world_verts(mesh); off = -float(c[:, 2].min())
    arm.location.z += off
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -0.62, .475)); box = bpy.context.object
    box.scale = (1.8, .5, .95); m = bpy.data.materials.new('counter'); m.use_nodes = True
    m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.25, .2, .16, 1); box.data.materials.append(m)
    frames = [f0 + (f1 - f0) * k // 6 for k in (1, 3, 5)]
    for k, f in enumerate(frames):
        s.frame_set(f); bpy.context.view_layer.update()
        shoot(f'counter_{stem}_{k}', (0, 0, 1.3), 2.6, 8, 1.62, lens=40, res=(520, 600))
    res[stem]['frames'] = frames; res[stem]['foot_offset_m'] = round(off, 4)
(HERE / 'counter.json').write_text(json.dumps(res, indent=2)); print('COUNTER DONE')
