#!/usr/bin/env python3
"""Feral gunner droid assembly (2 Oct 2026, numpy only; no Blender, no Meshy calls).

1. gunner/build/FeralGunner.glb: the Meshy rig (gunner/rig/rigged.glb, rig task in record.json) with the prepared
   forearm gun (gunner/ForearmGun.glb from prep_gun.py) added as a rigid child node of the RightForeArm bone, plus its
   'Muzzle' child. The rig's own nodes, skin and mesh are untouched (byte-identical accessors), so every Meshy library
   clip still applies.
   Gun mount: the gun origin (forearm axis under its front strap band) sits on the RightForeArm bone axis 0.26 m from the
   elbow; the gun's barrel runs along the bone (+Y local, toward the wrist) and its top faces the back of the forearm
   (the dorsal side, opposite the claws), measured from the rest pose.
2. Clips (gunner/build/clips/<name>.glb full for review renders, gunner/build/anim/<name>.glb animation-only for Unity):
   library clips re-based on the merged rig (idle, walk, run, death; hit trimmed to 1.0 s and eased back to its first
   frame) and procedural ranged clips layered on library bases:
   aim         idle_alert_2 legs/torso, right arm locked on the target: upper arm forward 12 deg down / 6 deg out,
               forearm (and gun) level, back of the forearm up rolled 15 deg outward, torso bladed 10 deg.
   fire        one shot from the aim pose (shot at 0.05 s; recoil: arm pitches up 12 deg + 6 deg muzzle climb, right
               shoulder kicks back 5 deg, torso leans back 3.5 deg, head 3 deg, hips back 2.5 cm), settled by 0.6 s,
               starts and ends in the aim pose: FeralDroid attack clip with fireClipPerShot (one recoil per bolt).
   fire_raise  raise from the idle arm to aim (0-0.30 s), hold, the same shot at 0.55 s, settled in the aim pose by
               1.2 s: for a flow without a separate aim wind-up.
   strafe_left / strafe_right  cautious crouch side-steps (library 525 / 526) made in place (hips drift removed) with
               the gun arm in the aim override.
All rotations are glTF node-local quaternions on the Meshy skeleton; only bone rotations + Hips translation are written
(what the Unity import keeps). 30 fps. Usage: python3 make_gunner.py"""
import copy, json, math, sys
from pathlib import Path
import numpy as np
from gltf_io import GLB, qmul, qinv, qrot, qnorm, q_from_to, q_axis_angle, slerp
import strip_clip

HERE = Path(__file__).parent
RIG = HERE / 'gunner' / 'rig'
OUT = HERE / 'gunner' / 'build'; (OUT / 'clips').mkdir(parents=True, exist_ok=True); (OUT / 'anim').mkdir(exist_ok=True)
FPS = 30
GUN_A = 0.26          # metres from the elbow along the forearm to the gun origin (front band)
OUTWARD_ROLL = 15     # deg: gun top rolled toward the robot's right in the aim pose
rec = {}


def q_mat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def mat_q(m):
    t = np.trace(m)
    if t > 0:
        s = math.sqrt(t + 1) * 2; return qnorm(np.array([(m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s, s / 4]))
    i = int(np.argmax(np.diag(m)))
    if i == 0:
        s = math.sqrt(1 + m[0, 0] - m[1, 1] - m[2, 2]) * 2; return qnorm(np.array([s / 4, (m[0, 1] + m[1, 0]) / s, (m[0, 2] + m[2, 0]) / s, (m[2, 1] - m[1, 2]) / s]))
    if i == 1:
        s = math.sqrt(1 + m[1, 1] - m[0, 0] - m[2, 2]) * 2; return qnorm(np.array([(m[0, 1] + m[1, 0]) / s, s / 4, (m[1, 2] + m[2, 1]) / s, (m[0, 2] - m[2, 0]) / s]))
    s = math.sqrt(1 + m[2, 2] - m[0, 0] - m[1, 1]) * 2; return qnorm(np.array([(m[0, 2] + m[2, 0]) / s, (m[1, 2] + m[2, 1]) / s, s / 4, (m[1, 0] - m[0, 1]) / s]))


def frame_q(a_from, b_from, a_to, b_to):
    """Rotation taking orthonormalised frame (a_from, b_from) onto (a_to, b_to)."""
    def basis(a, b):
        a = a / np.linalg.norm(a); b = b - a * (a @ b); b /= np.linalg.norm(b); return np.c_[a, b, np.cross(a, b)]
    return mat_q(basis(a_to, b_to) @ basis(a_from, b_from).T)


# ------------------------------------------------------------------ 1. merge the gun into the rig
def merge(rig_path, gun_path, parent_name, gun_rotation, gun_translation, gun_scale):
    r, g = GLB(rig_path), GLB(gun_path)
    J = r.j
    off = {k: len(J.get(k, [])) for k in ('nodes', 'meshes', 'materials', 'textures', 'images', 'samplers', 'accessors', 'bufferViews')}
    while len(r.bin) % 4: r.bin.append(0)
    base = len(r.bin)
    for bv in g.j['bufferViews']:
        bv = dict(bv); bv['byteOffset'] = bv.get('byteOffset', 0) + base; bv['buffer'] = 0; J['bufferViews'].append(bv)
    r.bin += g.bin
    for a in g.j['accessors']:
        a = dict(a); a['bufferView'] += off['bufferViews']; J['accessors'].append(a)
    for im in g.j.get('images', []):
        im = dict(im)
        if 'bufferView' in im: im['bufferView'] += off['bufferViews']
        J.setdefault('images', []).append(im)
    for sm in g.j.get('samplers', []): J.setdefault('samplers', []).append(dict(sm))
    for t in g.j.get('textures', []):
        t = dict(t); t['source'] += off['images']
        if 'sampler' in t: t['sampler'] += off['samplers']
        J.setdefault('textures', []).append(t)
    def fix_tex(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k.endswith('Texture') and isinstance(v, dict) and 'index' in v: v['index'] += off['textures']
                fix_tex(v)
    for m in g.j.get('materials', []):
        m = copy.deepcopy(m); fix_tex(m); m['name'] = 'FeralGunner_ForearmGun'; J['materials'].append(m)
    for me in g.j['meshes']:
        me = copy.deepcopy(me)
        for p in me['primitives']:
            p['attributes'] = {k: v + off['accessors'] for k, v in p['attributes'].items()}
            if 'indices' in p: p['indices'] += off['accessors']
            if 'material' in p: p['material'] += off['materials']
        J['meshes'].append(me)
    for n in g.j['nodes']:
        n = copy.deepcopy(n)
        if 'mesh' in n: n['mesh'] += off['meshes']
        if 'children' in n: n['children'] = [c + off['nodes'] for c in n['children']]
        J['nodes'].append(n)
    gun_idx = next(i for i, n in enumerate(J['nodes']) if n.get('name') == 'ForearmGun')
    gn = J['nodes'][gun_idx]
    for k in ('matrix',): gn.pop(k, None)
    gn['rotation'] = [float(x) for x in gun_rotation]; gn['translation'] = [float(x) for x in gun_translation]
    gn['scale'] = [float(gun_scale)] * 3
    J['nodes'][r.node_index(parent_name)].setdefault('children', []).append(gun_idx)
    for k in ('extensionsUsed', 'extensionsRequired'):
        u = sorted(set(J.get(k, [])) | set(g.j.get(k, [])))
        if u: J[k] = u
    J['buffers'] = [dict(byteLength=len(r.bin))]
    J.pop('animations', None)
    return r


rig = GLB(RIG / 'rigged.glb')
NODES = rig.j['nodes']; NAME = {i: n.get('name') for i, n in enumerate(NODES)}; IDX = {v: k for k, v in NAME.items()}
PARENT = rig.parents()
REST_R = {NAME[i]: np.array(n.get('rotation', [0, 0, 0, 1]), float) for i, n in enumerate(NODES)}
REST_T = {NAME[i]: np.array(n.get('translation', [0, 0, 0]), float) for i, n in enumerate(NODES)}
REST_S = {NAME[i]: np.array(n.get('scale', [1, 1, 1]), float) for i, n in enumerate(NODES)}
ROOTS = rig.j['scenes'][0]['nodes']


def fk(L, T):
    """World (position, rotation) of every node; L/T: local rotation/translation overrides by name."""
    P, Q, S = {}, {}, {}
    def walk(i, pp, pq, ps):
        n = NAME[i]; t = T.get(n, REST_T[n]); q = L.get(n, REST_R[n]); s = REST_S[n]
        P[n] = pp + qrot(pq, ps * t); Q[n] = qnorm(qmul(pq, q)); S[n] = ps * s
        for c in NODES[i].get('children', []): walk(c, P[n], Q[n], S[n])
    for r_ in ROOTS: walk(r_, np.zeros(3), np.array([0, 0, 0, 1.0]), np.ones(3))
    return P, Q


# rest-pose dorsal direction of the right forearm (opposite the claw centroid, measured on the skinned rest mesh)
P0, Q0 = fk({}, {})
E0, W0 = P0['RightForeArm'], P0['RightHand']
F0 = (W0 - E0) / np.linalg.norm(W0 - E0)
X = np.load(HERE / 'gunner' / 'rest_world.npy')
pr = rig.j['meshes'][0]['primitives'][0]
Jn, Wt = rig.acc(pr['attributes']['JOINTS_0']), rig.acc(pr['attributes']['WEIGHTS_0'])
joints = rig.j['skins'][0]['joints']; dom = np.array(joints)[Jn[np.arange(len(Jn)), Wt.argmax(1)]]
hand = X[dom == IDX['RightHand']] - W0
claw = (hand - np.outer(hand @ F0, F0)).mean(0)
dorsal_world = -claw - F0 * (-claw @ F0); dorsal_world /= np.linalg.norm(dorsal_world)
D_LOCAL = qrot(qinv(Q0['RightForeArm']), dorsal_world); D_LOCAL[1] = 0; D_LOCAL /= np.linalg.norm(D_LOCAL)  # orthogonal to the bone axis
Y_LOCAL = np.array([0, 1.0, 0])
rec['forearm_dorsal_local'] = D_LOCAL.round(4).tolist()
# gun node: +Z (muzzle) -> bone +Y, +Y (gun top) -> dorsal; translation on the bone axis (bone-local units are cm)
GUN_Q = frame_q(np.array([0, 0, 1.0]), np.array([0, 1.0, 0]), Y_LOCAL, D_LOCAL)
parent_scale = 1.0
i = IDX['RightForeArm']
while i is not None: parent_scale *= REST_S[NAME[i]][0]; i = PARENT.get(i)
GUN_T = Y_LOCAL * GUN_A / parent_scale
merged = merge(RIG / 'rigged.glb', HERE / 'gunner' / 'ForearmGun.glb', 'RightForeArm', GUN_Q, GUN_T, 1 / parent_scale)
merged.save(OUT / 'FeralGunner.glb')
rec['merged'] = dict(path=str((OUT / 'FeralGunner.glb').relative_to(HERE)), gun_parent='RightForeArm',
                     gun_local_rotation=GUN_Q.round(6).tolist(), gun_local_translation=GUN_T.round(4).tolist(),
                     gun_local_scale=round(1 / parent_scale, 4), bone_world_scale=parent_scale)
MG = GLB(OUT / 'FeralGunner.glb')
for k, n in enumerate(NODES):   # the rig's own nodes are unchanged apart from the gun child on RightForeArm
    m = dict(MG.j['nodes'][k])
    if NAME[k] == 'RightForeArm': m['children'] = [c for c in m['children'] if c < len(NODES)]
    assert m == n, NAME[k]


# ------------------------------------------------------------------ clip sampling
def load_clip(path):
    g = GLB(path); an = g.j['animations'][0]; ch = {}
    for c in an['channels']:
        s = an['samplers'][c['sampler']]
        ch[(g.j['nodes'][c['target']['node']]['name'], c['target']['path'])] = (g.acc(s['input']).astype(float), g.acc(s['output']).astype(float))
    return ch


def sample(ch, name, path, t):
    if (name, path) not in ch: return None
    ts, vs = ch[(name, path)]
    t = min(max(t, ts[0]), ts[-1]); k = int(np.searchsorted(ts, t, side='right') - 1); k = min(max(k, 0), len(ts) - 2)
    u = 0 if ts[k + 1] == ts[k] else (t - ts[k]) / (ts[k + 1] - ts[k])
    if path == 'rotation': return slerp(vs[k], vs[k + 1], u)
    return vs[k] * (1 - u) + vs[k + 1] * u


def duration(ch): return max(v[0][-1] for v in ch.values())


BONES = [NAME[j] for j in joints]


def base_pose(ch, t):
    L = {b: sample(ch, b, 'rotation', t) for b in BONES}
    L = {b: q for b, q in L.items() if q is not None}
    T = {'Hips': sample(ch, 'Hips', 'translation', t)}
    return L, T


# ------------------------------------------------------------------ aim override
FWD, UP = np.array([0, 0, 1.0]), np.array([0, 1.0, 0])
def Rx(deg): return q_axis_angle([1, 0, 0], math.radians(deg))
def Ry(deg): return q_axis_angle([0, 1, 0], math.radians(deg))
def Rz(deg): return q_axis_angle([0, 0, 1], math.radians(deg))
AIM = dict(arm_down=12, arm_out=6, twist=10, roll=OUTWARD_ROLL)
RECOIL = dict(arm=12, climb=6, kick=5, lean=3.5, head=3, hips_cm=2.5)


def set_world(L, name, q_world, Q):
    L[name] = qnorm(qmul(qinv(Q[NAME[PARENT[IDX[name]]]]), q_world))


def override(L0, T0, w, r, twist=True):
    """Layer the aim (weight w) and recoil (r in 0..1) onto a base pose; returns new local rotations/translations."""
    L, T = dict(L0), {k: v.copy() for k, v in T0.items()}
    P, Q = fk(L, T)
    if twist: set_world(L, 'Spine02', qmul(Ry(AIM['twist'] * w), Q['Spine02']), Q)
    P, Q = fk(L, T)
    set_world(L, 'Spine', qmul(qmul(Ry(-RECOIL['kick'] * r), Rx(-RECOIL['lean'] * r)), Q['Spine']), Q)
    P, Q = fk(L, T)
    set_world(L, 'Head', qmul(Rx(-RECOIL['head'] * r), Q['Head']), Q)
    T['Hips'] = T['Hips'] + np.array([0, 0, -RECOIL['hips_cm'] * r])
    P, Q = fk(L, T)
    pitch_up = RECOIL['arm'] * r
    # upper arm: forward, a little down and out (robot's right is -X), pitched up by the recoil
    U = qrot(qmul(Rx(-pitch_up), qmul(Ry(-AIM['arm_out']), Rx(AIM['arm_down']))), FWD)
    cur = qrot(Q['RightArm'], REST_T['RightForeArm']); cur /= np.linalg.norm(cur)
    tgt = {}
    tgt['RightArm'] = qmul(qinv(Q['RightShoulder']), qmul(q_from_to(cur, U), Q['RightArm']))
    L['RightArm'] = slerp(L0['RightArm'], tgt['RightArm'], w)
    P, Q = fk(L, T)
    climb = Rx(-(pitch_up + RECOIL['climb'] * r))
    F = qrot(climb, FWD); Up = qrot(climb, qrot(Rz(AIM['roll']), UP))
    R_target = frame_q(Y_LOCAL, D_LOCAL, F, Up)
    tgt['RightForeArm'] = qmul(qinv(Q['RightArm']), R_target)
    L['RightForeArm'] = slerp(L0['RightForeArm'], tgt['RightForeArm'], w)
    L['RightHand'] = slerp(L0['RightHand'], REST_R['RightHand'], w)
    return L, T


def recoil_curve(t, ts):
    if t < ts: return 0.0
    u = t - ts; peak = max((1 - math.exp(-x / .018)) * math.exp(-x / .16) for x in np.linspace(0, .3, 600))
    return (1 - math.exp(-u / .018)) * math.exp(-u / .16) / peak


def smooth(x): x = min(max(x, 0), 1); return x * x * (3 - 2 * x)


# ------------------------------------------------------------------ writer
def write_clip(name, frames, note):
    """frames: list of (L, T) at 30 fps. Writes clips/<name>.glb (merged rig + animation) and anim/<name>.glb."""
    g = GLB(OUT / 'FeralGunner.glb'); J = g.j
    while len(g.bin) % 4: g.bin.append(0)
    n = len(frames); times = (np.arange(n) / FPS).astype(np.float32)
    def add(arr, typ):
        arr = np.ascontiguousarray(arr, np.float32)
        while len(g.bin) % 4: g.bin.append(0)
        J['bufferViews'].append(dict(buffer=0, byteOffset=len(g.bin), byteLength=arr.nbytes)); g.bin += arr.tobytes()
        acc = dict(bufferView=len(J['bufferViews']) - 1, componentType=5126, count=len(arr), type=typ)
        if typ == 'SCALAR': acc.update(min=[float(arr.min())], max=[float(arr.max())])
        J['accessors'].append(acc); return len(J['accessors']) - 1
    tin = add(times, 'SCALAR')
    samplers, channels = [], []
    for b in BONES:
        qs = np.array([f[0].get(b, REST_R[b]) for f in frames])
        for k in range(1, n):
            if qs[k] @ qs[k - 1] < 0: qs[k] = -qs[k]
        samplers.append(dict(input=tin, output=add(qs, 'VEC4'), interpolation='LINEAR'))
        channels.append(dict(sampler=len(samplers) - 1, target=dict(node=IDX[b], path='rotation')))
    hp = np.array([f[1]['Hips'] for f in frames])
    samplers.append(dict(input=tin, output=add(hp, 'VEC3'), interpolation='LINEAR'))
    channels.append(dict(sampler=len(samplers) - 1, target=dict(node=IDX['Hips'], path='translation')))
    J['animations'] = [dict(name=name, samplers=samplers, channels=channels)]
    J['buffers'] = [dict(byteLength=len(g.bin))]
    full = OUT / 'clips' / f'{name}.glb'; g.save(full)
    # per-frame gun world matrices (glTF metres): Blender's importer misplaces bone-parented nodes on this centimetre
    # armature, so the review renders place the gun from these
    mats = []
    for L, T in frames:
        P, Q = fk(L, T); gq = qmul(Q['RightForeArm'], GUN_Q); gp = P['RightForeArm'] + qrot(Q['RightForeArm'], Y_LOCAL * GUN_A)
        m = np.eye(4); m[:3, :3] = q_mat(gq); m[:3, 3] = gp; mats.append(m.round(6).tolist())
    (OUT / 'clips' / f'{name}.gun.json').write_text(json.dumps(mats))
    strip_clip.strip(str(full), str(OUT / 'anim' / f'{name}.glb'))
    rec.setdefault('clips', {})[name] = dict(frames=n, seconds=round((n - 1) / FPS, 3), note=note)


def resample(ch, t0, t1):
    return [base_pose(ch, t) for t in np.arange(t0, t1 + 1e-6, 1 / FPS)]


lib = {k: load_clip(RIG / f'{v}.glb') for k, v in dict(idle='idle_alert_2', walk='basic_walking', run='basic_running',
       hit='hit_gunshot_177', death='death_back_183', sl='strafe_left_crouch_525', sr='strafe_right_crouch_526').items()}
# library clips on the merged rig (Meshy keys start at 1/30 s; resampled from 0)
for name, key, note in (('idle', 'idle', 'Meshy library 2 "Alert", as is'), ('walk', 'walk', 'Meshy rig basic walk (in place)'),
                        ('run', 'run', 'Meshy rig basic run (in place)'), ('death', 'death', 'Meshy library 183 "Shot and Fall Backward", falls ~1.1 m back')):
    ch = lib[key]; write_clip(name, resample(ch, 0, duration(ch)), note)
# hit: Gunshot Reaction trimmed to 1.0 s, last 0.35 s eased back to its first frame so it returns to the stance
ch = lib['hit']; fr = resample(ch, 0, 1.0); L0, T0 = fr[0]
for k, (L, T) in enumerate(fr):
    w = smooth((k / FPS - .65) / .35)
    fr[k] = ({b: slerp(L[b], L0[b], w) for b in L}, {'Hips': T['Hips'] * (1 - w) + T0['Hips'] * w})
write_clip('hit', fr, 'Meshy library 177 "Gunshot Reaction", first 1.0 s, eased back to its first frame over the last 0.35 s')
# aim (loop over the whole alert idle)
ch = lib['idle']; fr = resample(ch, 0, duration(ch))
write_clip('aim', [override(L, T, 1, 0) for L, T in fr], 'idle_alert_2 base + aim override (loop)')
# fire: raise 0-0.30 s, shot at 0.55 s, 1.2 s
RAISE_SHOT, FIRE_SHOT = .55, .05
fr = resample(ch, 0, 1.2)
write_clip('fire_raise', [override(L, T, smooth(k / FPS / .30), recoil_curve(k / FPS, RAISE_SHOT)) for k, (L, T) in enumerate(fr)],
           f'raise 0-0.30 s, shot at {RAISE_SHOT} s, recoil settles by 1.2 s; ends in the aim pose')
fr = resample(ch, 1.2, 1.8)
write_clip('fire', [override(L, T, 1, recoil_curve(k / FPS, FIRE_SHOT)) for k, (L, T) in enumerate(fr)],
           f'one shot from the aim pose at {FIRE_SHOT} s, settled by 0.6 s; starts and ends in the aim pose')
rec['shot_times'] = dict(fire=FIRE_SHOT, fire_raise=RAISE_SHOT)
# strafes: in place (remove the linear hips drift in x/z) + aim override, no torso blading
for name, key, src in (('strafe_left', 'sl', 525), ('strafe_right', 'sr', 526)):
    ch = lib[key]; d = duration(ch); fr = resample(ch, 0, d)
    h0, h1 = fr[0][1]['Hips'].copy(), fr[-1][1]['Hips'].copy(); n = len(fr)
    speed = float(np.linalg.norm((h1 - h0)[[0, 2]]) / 100 / ((n - 1) / FPS))
    out = []
    for k, (L, T) in enumerate(fr):
        T = {'Hips': T['Hips'] - (h1 - h0) * np.array([1, 0, 1]) * k / (n - 1)}
        out.append(override(L, T, 1, 0, twist=False))
    write_clip(name, out, f'Meshy library {src} cautious crouch side-step, in place (native sideways speed {speed:.2f} m/s) + aim override')
    rec['clips'][name]['native_speed_mps'] = round(speed, 3)

# aim check: forearm direction and gun muzzle in the aim/fire poses (world, glTF metres, model faces +Z)
def muzzle_world(L, T):
    P, Q = fk(L, T)
    gq = qmul(Q['RightForeArm'], GUN_Q); gp = P['RightForeArm'] + qrot(Q['RightForeArm'], Y_LOCAL * GUN_A)
    mz = json.loads((HERE / 'gunner' / 'forearm_gun.json').read_text())['muzzle_gltf']
    return gp + qrot(gq, np.array(mz)), qrot(gq, FWD)
ch = lib['idle']
checks = {}
for label, (L, T) in (('aim_t0', override(*base_pose(ch, 0), 1, 0)), ('fire_recoil_peak', override(*base_pose(ch, 1.2 + FIRE_SHOT + .05), 1, 1)),
                      ('idle_t0', base_pose(ch, 0))):
    p, d = muzzle_world(L, T); checks[label] = dict(muzzle=p.round(3).tolist(), barrel_dir=d.round(3).tolist(),
                                                      elevation_deg=round(math.degrees(math.asin(d[1])), 1))
rec['muzzle_checks'] = checks
(OUT / 'build.json').write_text(json.dumps(rec, indent=1)); print(json.dumps(checks)); print('GUNNER BUILD DONE')
