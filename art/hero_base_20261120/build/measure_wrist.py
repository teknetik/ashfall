"""Where the wrist is on the mesh against where the rig put the Hand joint (both sides). blender.sh measure_wrist.py"""
import bpy, json, numpy as np
from pathlib import Path
H = Path('/home/teknetik/code/ao2/art/hero_base_20261120/build')
bpy.ops.wm.open_mainfile(filepath=str(H / 'hero.blend'))
rig = bpy.data.objects['Armature']; char = bpy.data.objects['char1']
co = np.array([char.matrix_world @ v.co for v in char.data.vertices])
gi = {g.index: g.name for g in char.vertex_groups}
P = lambda n: np.array(rig.matrix_world @ rig.data.bones[n].head_local)
for sd, side in (('l', 'Left'), ('r', 'Right')):
    e = P(side + 'ForeArm'); k = P(f'middle_01_{sd}'); w = P(side + 'Hand'); ax = k - e; L = np.linalg.norm(ax); ax /= L
    arm = {side + 'ForeArm', side + 'Hand'} | {f'{d}_0{j}_{sd}' for d in ('index', 'middle', 'ring', 'pinky', 'thumb') for j in (1, 2, 3)}
    idx = [v.index for v in char.data.vertices if sum(g.weight for g in v.groups if gi[g.group] in arm) > .6]
    p = co[idx] - e; s = p @ ax; r = np.linalg.norm(p - np.outer(s, ax), axis=1)
    bins = np.arange(0.0, L, 0.005); prof = []
    for b0 in bins:
        m = (s >= b0) & (s < b0 + .005)
        prof.append(float(np.percentile(r[m], 90)) if m.sum() > 8 else np.nan)
    prof = np.array(prof); lo = int(len(bins) * .55)
    i = lo + int(np.nanargmin(prof[lo:])); wrist_s = bins[i] + .0025
    print('WRIST', side, 'elbow->knuckle', round(L * 1000), 'mm; Hand joint at', round(float((w - e) @ ax) * 1000), 'mm; narrowest section (wrist) at', round(wrist_s * 1000), 'mm, radius', round(prof[i] * 1000, 1), 'mm;',
          'joint is', round((wrist_s - float((w - e) @ ax)) * 1000), 'mm short of the wrist; forearm bone', round(float(np.linalg.norm(w - e)) * 1000), 'mm')
    print('   profile (mm from elbow: p90 radius mm):', ' '.join(f'{int(b*1000)}:{p_*1000:.0f}' for b, p_ in zip(bins[lo-4:], prof[lo-4:]) if not np.isnan(p_)))
