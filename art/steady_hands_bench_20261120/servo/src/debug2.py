import bpy, sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'kit'))
import check as K, contract as CT, rig as RG
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, '..', 'export', 'servo.blend'))
P = CT.parts('servo'); GG = {o.name: K.Geo(o) for o in P.values()}
body = P['servo.case_body']; tb = GG[body.name].bvh(K.world_matrix(body))
wb = GG[body.name].world(K.world_matrix(body)); tbt = GG[body.name].t
for fid, o in P.items():
    d = json.loads(o['sh'])
    if d.get('parent') == 'servo.gimbal_cradle' or fid == 'servo.gimbal_cradle':
        mb = GG[o.name].bvh(K.world_matrix(o), shrunk=True)
        ov = tb.overlap(mb)
        if ov:
            w = GG[o.name].world(K.world_matrix(o)); t = GG[o.name].t
            pts = sorted({tuple(round(x * 1000, 1) for x in (w[t[b][0]] + w[t[b][1]] + w[t[b][2]]) / 3) for a, b in ov})
            print('OVERLAP', fid, len(ov), pts[:5], pts[-3:])
