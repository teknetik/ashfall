"""Measure the new hero body and, for comparison, the shipped (old) body with its seven fitted pieces.
Writes work/inspect.json. Usage: blender.sh inspect_bodies.py"""
import sys; sys.path.insert(0, '/home/teknetik/code/ao2/art/hero_base_20261120/armour/blender')
import bpy, json, math
from mathutils import Vector
import hlib as H

out = {}


def measures(arm, body, tag):
    ws = H.world_verts(body); r = {}
    lo = Vector([min(w[i] for w in ws) for i in range(3)]); hi = Vector([max(w[i] for w in ws) for i in range(3)])
    r['bounds'] = [[round(x, 4) for x in lo], [round(x, 4) for x in hi]]
    r['bones'] = {b.name: {'head': [round(x, 4) for x in H.bone_head(arm, b.name)], 'tail': [round(x, 4) for x in H.bone_tail(arm, b.name)],
                           'parent': b.parent.name if b.parent else None} for b in arm.data.bones}
    NECKZ = H.bone_head(arm, 'neck').z; HIPZ = H.bone_head(arm, 'Hips').z
    band = [w for w in ws if NECKZ - 0.25 < w.z < NECKZ - 0.17 and abs(w.x) < 0.09]
    ys = [w.y for w in band]; r['chest_band'] = {'depth': round(max(ys) - min(ys), 4), 'cy': round((max(ys) + min(ys)) / 2, 4), 'ymin': round(min(ys), 4), 'ymax': round(max(ys), 4)}
    top = hi.z; cap = [w for w in ws if w.z > top - 0.13]
    xs = [w.x for w in cap]; ys = [w.y for w in cap]
    r['head_cap'] = {'top': round(top, 4), 'width': round(max(xs) - min(xs), 4), 'depth': round(max(ys) - min(ys), 4),
                     'cx': round((max(xs) + min(xs)) / 2, 4), 'cy': round((max(ys) + min(ys)) / 2, 4)}
    # torso widths/depths at stations below the neck joint, arms excluded by dominant bone
    gn = {g.index: g.name for g in body.vertex_groups}
    def dom(v):
        return gn[max(v.groups, key=lambda g: g.weight).group] if v.groups else None
    doms = [dom(v) for v in body.data.vertices]
    r['dom_counts'] = {}
    for d in doms: r['dom_counts'][d] = r['dom_counts'].get(d, 0) + 1
    torso = [w for w, d in zip(ws, doms) if d in ('Hips', 'Spine02', 'Spine01', 'Spine', 'neck', 'LeftShoulder', 'RightShoulder')]
    st = {}
    for dz in (0.0, -0.05, -0.10, -0.15, -0.20, -0.25, -0.30, -0.35, -0.40, -0.45, -0.50, -0.55):
        sl = [w for w in torso if abs(w.z - (NECKZ + dz)) < 0.012]
        if sl: st['%.2f' % dz] = {'w': round(max(w.x for w in sl) - min(w.x for w in sl), 3), 'd': round(max(w.y for w in sl) - min(w.y for w in sl), 3),
                                  'ymin': round(min(w.y for w in sl), 3), 'ymax': round(max(w.y for w in sl), 3)}
    r['torso_stations_below_neck'] = st; r['neck_z'] = round(NECKZ, 4); r['hips_z'] = round(HIPZ, 4)
    # limb radii along the segment (right side)
    def limb(seg, fracs=(0.1, 0.25, 0.4, 0.55, 0.7, 0.85, 1.0)):
        a = H.bone_head(arm, seg[0]); b = H.bone_head(arm, seg[1]); ax = (b - a).normalized(); L = (b - a).length; res = {'len': round(L, 4)}
        for f in fracs:
            c = a + ax * L * f
            rs = sorted(((w - c) - ax * (w - c).dot(ax)).length for w in ws if abs((w - c).dot(ax)) < 0.012 and ((w - c) - ax * (w - c).dot(ax)).length < 0.13)
            if rs: res['%.2f' % f] = {'r50': round(rs[len(rs) // 2], 4), 'r90': round(rs[int(len(rs) * .9)], 4), 'rmax': round(rs[-1], 4), 'n': len(rs)}
        return res
    r['forearm_R'] = limb(('RightForeArm', 'RightHand')); r['upperarm_R'] = limb(('RightArm', 'RightForeArm'))
    r['shin_R'] = limb(('RightLeg', 'RightFoot')); r['thigh_R'] = limb(('RightUpLeg', 'RightLeg'))
    foot = [w for w in ws if w.z < 0.16 and w.x < -0.04]
    r['boot_R'] = {'lo': [round(min(q[i] for q in foot), 4) for i in range(3)], 'hi': [round(max(q[i] for q in foot), 4) for i in range(3)]}
    hand = [w for w, d in zip(ws, doms) if d and (d == 'RightHand' or d.endswith('_r'))]
    r['hand_R'] = {'lo': [round(min(q[i] for q in hand), 4) for i in range(3)], 'hi': [round(max(q[i] for q in hand), 4) for i in range(3)], 'verts': len(hand)}
    r['shoulder_width_joints'] = round((H.bone_head(arm, 'LeftArm') - H.bone_head(arm, 'RightArm')).length, 4)
    sl = [w for w in ws if abs(w.z - H.bone_head(arm, 'LeftArm').z) < 0.02]
    r['width_at_shoulder_joint_z'] = round(max(w.x for w in sl) - min(w.x for w in sl), 4)
    r['tris'] = H.tris(body); r['verts'] = len(body.data.vertices); r['materials'] = [m.name for m in body.data.materials]
    r['uv_layers'] = [u.name for u in body.data.uv_layers]
    out[tag] = r


# ---- new body
arm, body = H.load_hero()
measures(arm, body, 'new')
out['new']['actions'] = {a.name: [a.frame_range[0], a.frame_range[1]] for a in bpy.data.actions}

# ---- old body + its pieces (the shipped files), measured the same way
bpy.ops.wm.read_factory_settings(use_empty=True)
objs = H.import_glb(H.OLD_BODY)
oarm = next(o for o in objs if o.type == 'ARMATURE')
for o in objs:
    if o.type == 'MESH' and o.name.startswith('Icosphere'): bpy.data.objects.remove(o)
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
bpy.ops.object.select_all(action='DESELECT')
for o in meshes: o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1: bpy.ops.object.join()
obody = bpy.context.view_layer.objects.active
H.rest(oarm)
measures(oarm, obody, 'old')
out['old']['pieces'] = {}
for key, fn in H.FILES.items():
    po = H.import_glb(H.TS_OLD / fn)
    pm = next(o for o in po if o.type == 'MESH'); pa = next(o for o in po if o.type == 'ARMATURE')
    H.rest(pa)
    lo, hi = H.bounds(pm)
    out['old']['pieces'][key] = {'lo': [round(x, 4) for x in lo], 'hi': [round(x, 4) for x in hi], 'tris': H.tris(pm),
                                 'gap': H.gap_stats(pm, obody), 'mesh': pm.name, 'material': pm.data.materials[0].name}
    for o in po: bpy.data.objects.remove(o, do_unlink=True)

# ---- sources: raw bounds and triangle counts
out['sources'] = {}
for key, path in (('helmet', H.MESHY / 'helmet/model.glb'), ('vest', H.MESHY / 'chest/model.glb'), ('carrier', H.CARRIER_SRC),
                  ('bracer', H.MESHY / 'bracer/model.glb'), ('kneeshin', H.MESHY / 'kneeshin/model.glb'),
                  ('bootplates', H.MESHY / 'bootplates/model.glb'), ('glove_retex', H.MESHY / 'glove_retex/model.glb')):
    p = H.import_piece(path, 'src_' + key); n0 = len(p.data.vertices); t = H.tris(p); m = H.merge_splits(p)
    lo, hi = H.bounds(p)
    out['sources'][key] = {'size': [round(x, 4) for x in hi - lo], 'tris': t, 'verts_split': n0, 'verts_merged': len(p.data.vertices),
                           'islands': len(H.islands(p)), 'materials': [mm.name for mm in p.data.materials]}
    bpy.data.objects.remove(p, do_unlink=True)

(H.WORK / 'inspect.json').write_text(json.dumps(out, indent=1))
print('INSPECT done')
