# debug: why the rotor meets the coil / race, and why the -Y case screws read "solid"
import bpy, sys, os, json, bmesh
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'kit'))
import check as K, contract as CT, rig as RG, geo as G
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, '..', 'export', 'servo.blend'))
P = CT.parts('servo')
GG = {o.name: K.Geo(o) for o in P.values()}
MM = 0.001
C = Vector((0.019, 0, 0.0244))
def bb(name):
    o = P['servo.' + name]; w = GG[o.name].world(K.world_matrix(o))
    lo = [min(p[i] for p in w) for i in range(3)]; hi = [max(p[i] for p in w) for i in range(3)]
    r = [((p.x - C.x) ** 2 + (p.y - C.y) ** 2) ** 0.5 for p in w]
    return [round((a - c) / MM, 2) for a, c in zip(lo, C)], [round((a - c) / MM, 2) for a, c in zip(hi, C)], 'r %.2f..%.2f' % (min(r) / MM, max(r) / MM)
for n in ('gimbal_coil', 'gimbal_rotor', 'gimbal_race', 'gimbal_ring', 'gimbal_retainer', 'gimbal_cradle'):
    print('BB', n, bb(n), 'solid', G.solid_check(P['servo.' + n]))
gim = bpy.data.objects['servo_gimbal_rig']
for v in ((0.5, 0.5), (1.0, 0.5), (0.0, 0.5), (0.5, 1.0), (0.5, 0.0)):
    RG.set_params(gim, {'gimbal_pitch': v[0], 'gimbal_roll': v[1]})
    ro = P['servo.gimbal_rotor']; co = P['servo.gimbal_coil']
    tb = GG[co.name].bvh(K.world_matrix(co)); mb = GG[ro.name].bvh(K.world_matrix(ro), shrunk=True)
    ov = tb.overlap(mb)
    pts = []
    w = GG[ro.name].world(K.world_matrix(ro)); tr = GG[ro.name].t
    for a, b in ov[:400]:
        t = tr[b]; c = (w[t[0]] + w[t[1]] + w[t[2]]) / 3 - C
        pts.append((round(c.x / MM, 1), round(c.y / MM, 1), round(c.z / MM, 1)))
    print('POSE', v, 'overlaps', len(ov), sorted(set(pts))[:6], sorted(set(pts))[-3:])
RG.set_params(gim, {'gimbal_pitch': 0.5, 'gimbal_roll': 0.5})
# rotor lifted 1.2 mm against the race
ro = P['servo.gimbal_rotor']; ra = P['servo.gimbal_race']
from mathutils import Matrix
M = Matrix.Translation((0, 0, 1.2 * MM)) @ K.world_matrix(ro)
tb = GG[ra.name].bvh(K.world_matrix(ra)); mb = GG[ro.name].bvh(M, shrunk=True)
ov = tb.overlap(mb); w = GG[ro.name].world(M); tr = GG[ro.name].t
print('ROTOR+1.2 vs race overlaps', len(ov), sorted({tuple(round(x / MM, 1) for x in ((w[tr[b][0]] + w[tr[b][1]] + w[tr[b][2]]) / 3 - C)) for a, b in ov})[:10])
# the case screws
for k in 'abcd':
    o = P['servo.screw_case_' + k]
    Mw = K.world_matrix(o)
    for tgt in ('case_lid', 'case_body'):
        ox = P['servo.' + tgt]; tree = GG[ox.name].bvh(K.world_matrix(ox))
        votes = []
        for i in range(0, 48, 4):
            p = Mw.translation - Vector((0, 0, 1)) * (0.010 * (i + 0.5) / 48)
            per = []
            for d in ((0.013, 1, 0.021), (0.017, -0.011, 1), (1, 0.02, 0.013)):
                d = Vector(d).normalized(); q = Vector(p); hits = 0
                for _ in range(64):
                    h = tree.ray_cast(q, d, 10.0)
                    if h[0] is None: break
                    hits += 1; q = h[0] + d * 1e-6
                per.append(hits)
            votes.append(per)
        print('SCREW', k, tgt, votes)
print('solid body', G.solid_check(P['servo.case_body']), 'lid', G.solid_check(P['servo.case_lid']), 'stator', G.solid_check(P['servo.stator']))
st = json.load(open(os.path.join(HERE, '..', 'export', 'stats.json')))
print('ANIM', st.get('animation_channels'), {k: v for k, v in st['glb']['animations'].items()})
