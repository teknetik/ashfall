"""Torso landmarks of the new and the shipped (old) body, and where the shipped vest/carrier sat on the old one.
Prints the shoulder line (top surface z at |x|), chest front/back y at heights, and piece bounds. work/torso_probe.json"""
import sys; sys.path.insert(0, '/home/teknetik/code/ao2/art/hero_base_20261120/armour/blender')
import bpy, json
from mathutils import Vector
import hlib as H
out = {}
def probe(arm, body, tag):
    bvh, bm = H.body_bvh(body); r = {}
    sh = {}
    for x in (0.04, 0.06, 0.08, 0.10, 0.12, 0.14, 0.16, 0.18, 0.20, 0.22, 0.24, 0.26, 0.28, 0.30):
        best = None
        for yi in range(-12, 16):
            y = yi * 0.01
            for sx in (1, -1):
                hit = bvh.ray_cast(Vector((sx * x, y, 2.2)), Vector((0, 0, -1)), 1.2)
                if hit[0] is not None and (best is None or hit[0].z > best[0]): best = (round(hit[0].z, 4), round(y, 2), sx)
        sh['%.2f' % x] = best
    r['shoulder_top_z_at_x'] = sh
    prof = {}
    for z in (1.50, 1.46, 1.42, 1.38, 1.34, 1.30, 1.26, 1.22, 1.18, 1.14, 1.10, 1.06, 1.02):
        f = bvh.ray_cast(Vector((0, -1, z)), Vector((0, 1, 0)), 2); b = bvh.ray_cast(Vector((0, 1, z)), Vector((0, -1, 0)), 2)
        f8 = bvh.ray_cast(Vector((0.1, -1, z)), Vector((0, 1, 0)), 2); b8 = bvh.ray_cast(Vector((0.1, 1, z)), Vector((0, -1, 0)), 2)
        # flank: from the centre line outwards (inside surface would be hit first from inside; cast from the axis)
        l = bvh.ray_cast(Vector((0, 0.01, z)), Vector((1, 0, 0)), 1)
        prof['%.2f' % z] = dict(front_y=round(f[0].y, 3) if f[0] else None, back_y=round(b[0].y, 3) if b[0] else None,
                                front_y_x10=round(f8[0].y, 3) if f8[0] else None, back_y_x10=round(b8[0].y, 3) if b8[0] else None,
                                flank_x=round(l[0].x, 3) if l[0] else None)
    r['profile'] = prof
    for b in ('neck', 'Spine', 'Spine01', 'Spine02', 'Hips', 'LeftShoulder', 'LeftArm', 'RightArm', 'LeftUpLeg'):
        r[b] = [round(v, 4) for v in H.bone_head(arm, b)]
    bm.free(); out[tag] = r
arm, body = H.load_hero(); probe(arm, body, 'new')
bpy.ops.wm.read_factory_settings(use_empty=True)
objs = H.import_glb(H.OLD_BODY); oarm = next(o for o in objs if o.type == 'ARMATURE'); H.rest(oarm)
obody = max((o for o in objs if o.type == 'MESH'), key=lambda o: len(o.data.vertices)); probe(oarm, obody, 'old')
for key in ('vest', 'carrier'):
    got = H.load_pieces(oarm, [key], H.TS_OLD); p = got[key]; ws = H.world_verts(p)
    lo, hi = H.bounds(p); c = {}
    c['lo'] = [round(v, 4) for v in lo]; c['hi'] = [round(v, 4) for v in hi]
    mid = [w for w in ws if abs(w.x) < 0.10]
    c['mid_lo'] = [round(min(w[i] for w in mid), 4) for i in range(3)]; c['mid_hi'] = [round(max(w[i] for w in mid), 4) for i in range(3)]
    # strap top: highest z per |x| band
    c['top_z_at_x'] = {'%.2f' % x: round(max((w.z for w in ws if abs(abs(w.x) - x) < 0.01), default=0), 4) for x in (0.04, 0.06, 0.08, 0.10, 0.12, 0.14, 0.16, 0.18, 0.20)}
    c['front_y_at_z'] = {'%.2f' % z: round(min((w.y for w in ws if abs(w.z - z) < 0.01 and abs(w.x) < 0.1), default=0), 4) for z in (1.45, 1.40, 1.35, 1.30, 1.25, 1.20, 1.15, 1.10, 1.05)}
    c['back_y_at_z'] = {'%.2f' % z: round(max((w.y for w in ws if abs(w.z - z) < 0.01 and abs(w.x) < 0.1), default=0), 4) for z in (1.45, 1.40, 1.35, 1.30, 1.25, 1.20, 1.15, 1.10, 1.05)}
    c['halfwidth_at_z'] = {'%.2f' % z: round(max((abs(w.x) for w in ws if abs(w.z - z) < 0.01 and w.x < 0), default=0), 4) for z in (1.45, 1.40, 1.35, 1.30, 1.25, 1.20, 1.15, 1.10, 1.05)}
    out['old'][key] = c
(H.WORK / 'torso_probe.json').write_text(json.dumps(out, indent=1))
for tag in ('new', 'old'):
    r = out[tag]; print('PROBE', tag, {k: r[k] for k in ('neck', 'Spine', 'Spine01', 'Spine02', 'Hips', 'LeftArm', 'LeftUpLeg')})
    print('PROBE', tag, 'shoulder', {k: v[0] if v else None for k, v in r['shoulder_top_z_at_x'].items()})
    for z, v in r['profile'].items(): print('PROBE', tag, z, v)
for key in ('vest', 'carrier'):
    for k, v in out['old'][key].items(): print('PROBE old', key, k, v)
