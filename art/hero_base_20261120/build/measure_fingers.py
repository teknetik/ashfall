"""Finger and thumb radii of the hero hands (median distance of the skin to each joint's axis). blender.sh measure_fingers.py"""
import bpy, json, numpy as np
from pathlib import Path
H = Path('/home/teknetik/code/ao2/art/hero_base_20261120/build')
bpy.ops.wm.open_mainfile(filepath=str(H / 'hero.blend'))
rig = bpy.data.objects['Armature']; char = bpy.data.objects['char1']
co = np.array([char.matrix_world @ v.co for v in char.data.vertices])
gi = {g.name: g.index for g in char.vertex_groups}; out = {}
for sd in 'lr':
    for d in ('index', 'middle', 'ring', 'pinky', 'thumb'):
        for j in (1, 2, 3):
            n = f'{d}_0{j}_{sd}'; b = rig.data.bones[n]; h = np.array(rig.matrix_world @ b.head_local); t = np.array(rig.matrix_world @ b.tail_local)
            ax = (t - h); L = np.linalg.norm(ax); ax /= L
            idx = [v.index for v in char.data.vertices if any(g.group == gi[n] and g.weight > .5 for g in v.groups)]
            if len(idx) < 6: out[n] = None; continue
            p = co[idx] - h; s = p @ ax; keep = (s > .15 * L) & (s < .85 * L)
            r = np.linalg.norm(p - np.outer(s, ax), axis=1)[keep]
            out[n] = {'radius_mm': round(float(np.median(r)) * 1000, 1), 'length_mm': round(float(L) * 1000, 1), 'n': int(keep.sum())}
hand = {}
for sd, side in (('l', 'Left'), ('r', 'Right')):
    w = np.array(rig.matrix_world @ rig.data.bones[side + 'Hand'].head_local); m1 = np.array(rig.matrix_world @ rig.data.bones[f'middle_01_{sd}'].head_local)
    i1 = np.array(rig.matrix_world @ rig.data.bones[f'index_01_{sd}'].head_local); p1 = np.array(rig.matrix_world @ rig.data.bones[f'pinky_01_{sd}'].head_local)
    hand[side] = {'wrist_to_middle_knuckle_mm': round(float(np.linalg.norm(m1 - w)) * 1000, 1), 'knuckle_width_mm': round(float(np.linalg.norm(i1 - p1)) * 1000, 1)}
res = {'fingers': out, 'hand': hand, 'file_height_m': float(co[:, 2].max() - co[:, 2].min()), 'game_scale': 1.8 / float(co[:, 2].max() - co[:, 2].min())}
(H / 'fingers.json').write_text(json.dumps(res, indent=1)); print('FINGERS', json.dumps(res['hand']), 'scale', round(res['game_scale'], 4))
for d in ('index', 'middle', 'ring', 'pinky', 'thumb'):
    print('FINGERS', d, [out[f'{d}_0{j}_r'] and out[f'{d}_0{j}_r']['radius_mm'] for j in (1, 2, 3)], [out[f'{d}_0{j}_r'] and out[f'{d}_0{j}_r']['length_mm'] for j in (1, 2, 3)])
