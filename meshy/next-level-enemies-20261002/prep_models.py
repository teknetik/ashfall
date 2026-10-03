#!/usr/bin/env python3
"""Next-level enemies (2 Oct 2026): prepare Carl's delivered Meshy models for Unity (numpy + Pillow only; no Meshy calls).

Inputs (meshy/incoming-20261002, delivered by Carl from the Meshy web app; their rig task ids are not retrievable through
the API, so every clip beyond walk/run is authored here procedurally):
  Ironclad Warden   66-joint UE/Mixamo-named biped, walking + running GLBs (same rig, same rest TRS), 11.4k tris, 1.7 m
  Scrap Reaper      43-joint biped, walking + running, 8.6k tris, 1.7 m
  Post Sentinel     static mesh, 8.6k tris, 1.89 m (one-wheeled courier droid with a parasol hat and a rifle)

For each rig:
  <name>/build/<Name>_geo.glb      the Walking GLB without animations and images, WEIGHTS_0 renormalised and the unused
                                   JOINTS_1/2 + WEIGHTS_1/2 sets removed (glTFast skins with four influences only)
  <name>/build/anim/<clip>.glb     animation-only GLBs (node hierarchy + one animation): walk, run (from the delivered
                                   files) and the procedural idle, attack, hit, death (bone rotations + pelvis translation
                                   at 30 fps on the rest pose, world-axis rotations applied in hierarchy order)
  <name>/build/clips/<clip>.glb    the same clips with the geometry, for Blender review renders (review_clips.py)
  <name>/textures/<Name>_*.png     URP Lit set: BaseMap (sRGB), Normal, Mask (R metallic, G 1, B 0, A smoothness =
                                   (1 - roughness) x 0.85 for desert dust), as the ranged-enemy pass
Sentinel: sentinel/build/PostSentinel_geo.glb (origin moved to the wheel's contact point, images stripped) with child
nodes Muzzle (rifle tip), Head and Hat found from vertex clusters; textures as above.
handoff.json records every measurement the Unity installer uses (stride speeds, feet, head, muzzle, clip notes).
Usage: uv run --offline --with pillow --with numpy python prep_models.py"""
import copy, io, json, math, sys
from pathlib import Path
import numpy as np
from PIL import Image
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'ranged-enemies-20261002'))
from gltf_io import GLB, qmul, qinv, qrot, qnorm, q_axis_angle, slerp  # noqa: E402
import strip_clip, strip_images  # noqa: E402
INC = HERE.parent / 'incoming-20261002'
FPS = 30
rec = {'generated_by': 'prep_models.py', 'inputs': {}}

RIGS = {
    'warden': dict(name='IroncladWarden', walk=INC / 'Meshy_AI_Ironclad_Warden_biped/Meshy_AI_Ironclad_Warden_biped_Animation_Walking_withSkin.glb',
                   run=INC / 'Meshy_AI_Ironclad_Warden_biped/Meshy_AI_Ironclad_Warden_biped_Animation_Running_withSkin.glb',
                   attack_seconds=1.1, death_seconds=2.4, style='hammer', talk=True),
    'reaper': dict(name='ScrapReaper', walk=INC / 'Meshy_AI_Scrap_Reaper_biped/Meshy_AI_Scrap_Reaper_biped_Animation_Walking_withSkin.glb',
                   run=INC / 'Meshy_AI_Scrap_Reaper_biped/Meshy_AI_Scrap_Reaper_biped_Animation_Running_withSkin.glb',
                   attack_seconds=0.8, death_seconds=2.0, style='slash'),
}
SENTINEL = INC / 'Meshy_AI_Post_Sentinel_1002142607_texture.glb'


# ------------------------------------------------------------------ textures
def export_textures(g, outdir, stem):
    outdir.mkdir(parents=True, exist_ok=True)
    imgs = {}
    for im in g.j.get('images', []):
        bv = g.j['bufferViews'][im['bufferView']]
        data = bytes(g.bin[bv.get('byteOffset', 0):bv.get('byteOffset', 0) + bv['byteLength']])
        imgs[im.get('name', str(len(imgs)))] = Image.open(io.BytesIO(data)).convert('RGBA')
    mat = g.j['materials'][0]; pbr = mat['pbrMetallicRoughness']
    def tex(idx): return imgs[g.j['images'][g.j['textures'][idx]['source']].get('name')]
    base = tex(pbr['baseColorTexture']['index']); nrm = tex(mat['normalTexture']['index']); mr = tex(pbr['metallicRoughnessTexture']['index'])
    base.convert('RGB').save(outdir / f'{stem}_BaseMap.png'); nrm.convert('RGB').save(outdir / f'{stem}_Normal.png')
    a = np.asarray(mr).astype(np.float32) / 255
    mask = np.dstack([a[..., 2], np.ones_like(a[..., 0]), np.zeros_like(a[..., 0]), np.clip((1 - a[..., 1]) * .85, 0, 1)])
    Image.fromarray((mask * 255 + .5).astype(np.uint8), 'RGBA').save(outdir / f'{stem}_Mask.png')
    return dict(size=list(base.size), metallic_mean=round(float(a[..., 2].mean()), 3), roughness_mean=round(float(a[..., 1].mean()), 3),
                files=[f'{stem}_BaseMap.png', f'{stem}_Normal.png', f'{stem}_Mask.png'])


# ------------------------------------------------------------------ rig helpers
class Rig:
    def __init__(self, path):
        self.g = GLB(path); j = self.g.j
        self.nodes = j['nodes']; self.name = {i: n.get('name') for i, n in enumerate(self.nodes)}; self.idx = {v: k for k, v in self.name.items()}
        self.parent = self.g.parents(); self.roots = j['scenes'][0]['nodes']
        self.rest_r = {self.name[i]: np.array(n.get('rotation', [0, 0, 0, 1]), float) for i, n in enumerate(self.nodes)}
        self.rest_t = {self.name[i]: np.array(n.get('translation', [0, 0, 0]), float) for i, n in enumerate(self.nodes)}
        self.rest_s = {self.name[i]: np.array(n.get('scale', [1, 1, 1]), float) for i, n in enumerate(self.nodes)}
        self.joints = [self.name[k] for k in j['skins'][0]['joints']]
        self.depth = {}
        for n in self.joints:
            d, i = 0, self.idx[n]
            while i in self.parent: d += 1; i = self.parent[i]
            self.depth[n] = d

    def fk(self, L, T):
        P, Q = {}, {}
        def walk(i, pp, pq, ps):
            n = self.name[i]; t = T.get(n, self.rest_t[n]); q = L.get(n, self.rest_r[n]); s = self.rest_s[n]
            P[n] = pp + qrot(pq, ps * t); Q[n] = qnorm(qmul(pq, q)); S = ps * s
            for c in self.nodes[i].get('children', []): walk(c, P[n], Q[n], S)
        for r in self.roots: walk(r, np.zeros(3), np.array([0, 0, 0, 1.0]), np.ones(3))
        return P, Q

    def parent_name(self, n): return self.name[self.parent[self.idx[n]]] if self.idx[n] in self.parent else None

    def rot_world(self, L, T, bone, axis, deg):
        """Rotate a bone (and so its subtree) about a world axis through its own origin."""
        if abs(deg) < 1e-6 or bone not in self.idx: return
        P, Q = self.fk(L, T)
        q = q_axis_angle(axis, math.radians(deg)); Qw = qnorm(qmul(q, Q[bone]))
        p = self.parent_name(bone)
        L[bone] = qnorm(qmul(qinv(Q[p]), Qw)) if p else Qw

    def apply_pose(self, params, pelvis_offset):
        """params: {(bone, axis): deg}; applied in hierarchy order on the rest pose. Returns (L, T)."""
        L = {b: self.rest_r[b].copy() for b in self.joints}; T = {'pelvis': self.rest_t['pelvis'] + np.asarray(pelvis_offset, float)}
        for (bone, axis), deg in sorted(params.items(), key=lambda kv: (self.depth.get(kv[0][0], 99), kv[0][0])):
            self.rot_world(L, T, bone, AX[axis], deg)
        return L, T


AX = {'x': np.array([1.0, 0, 0]), 'y': np.array([0, 1.0, 0]), 'z': np.array([0, 0, 1.0])}


def load_channels(g):
    an = g.j['animations'][0]; ch = {}
    for c in an['channels']:
        s = an['samplers'][c['sampler']]
        ch[(g.j['nodes'][c['target']['node']]['name'], c['target']['path'])] = (g.acc(s['input']).astype(float), g.acc(s['output']).astype(float))
    return ch


def sample(ch, name, path, t):
    if (name, path) not in ch: return None
    ts, vs = ch[(name, path)]
    t = min(max(t, ts[0]), ts[-1]); k = int(np.searchsorted(ts, t, side='right') - 1); k = min(max(k, 0), len(ts) - 2)
    u = 0 if ts[k + 1] == ts[k] else (t - ts[k]) / (ts[k + 1] - ts[k])
    return slerp(vs[k], vs[k + 1], u) if path == 'rotation' else vs[k] * (1 - u) + vs[k + 1] * u


def smooth(x): x = min(max(x, 0), 1); return x * x * (3 - 2 * x)
def ease_in(x): x = min(max(x, 0), 1); return x * x
def ease_out(x): x = min(max(x, 0), 1); return 1 - (1 - x) * (1 - x)
EASE = dict(smooth=smooth, out=ease_out, snap=lambda x: ease_out(min(1, x * 1.0)) if x < 1 else 1.0)


def keyframed(rig, keys, seconds):
    """keys: list of (time, params dict, pelvis offset, ease name for the segment ending at this key)."""
    frames = []
    n = int(round(seconds * FPS))
    allk = set(k for _, p, _, _ in keys for k in p)
    for f in range(n + 1):
        t = f / FPS
        k1 = next((i for i, k in enumerate(keys) if k[0] >= t - 1e-9), len(keys) - 1); k0 = max(0, k1 - 1)
        t0, p0, o0, _ = keys[k0]; t1, p1, o1, ease = keys[k1]
        u = EASE.get(ease, smooth)((t - t0) / (t1 - t0)) if t1 > t0 else 1.0
        params = {k: p0.get(k, 0) * (1 - u) + p1.get(k, 0) * u for k in allk}
        off = np.array(o0, float) * (1 - u) + np.array(o1, float) * u
        frames.append(rig.apply_pose(params, off))
    return frames


def write_clip(rig, geo_path, out_dir, name, frames, note, loop):
    g = GLB(geo_path); J = g.j
    while len(g.bin) % 4: g.bin.append(0)
    n = len(frames); times = (np.arange(n) / FPS).astype(np.float32)
    def add(arr, typ):
        arr = np.ascontiguousarray(arr, np.float32)
        while len(g.bin) % 4: g.bin.append(0)
        J['bufferViews'].append(dict(buffer=0, byteOffset=len(g.bin), byteLength=arr.nbytes)); g.bin += arr.tobytes()
        acc = dict(bufferView=len(J['bufferViews']) - 1, componentType=5126, count=len(arr), type=typ)
        if typ == 'SCALAR': acc.update(min=[float(arr.min())], max=[float(arr.max())])
        J['accessors'].append(acc); return len(J['accessors']) - 1
    tin = add(times, 'SCALAR'); samplers, channels = [], []
    for b in rig.joints:
        qs = np.array([f[0].get(b, rig.rest_r[b]) for f in frames])
        for k in range(1, n):
            if qs[k] @ qs[k - 1] < 0: qs[k] = -qs[k]
        samplers.append(dict(input=tin, output=add(qs, 'VEC4'), interpolation='LINEAR'))
        channels.append(dict(sampler=len(samplers) - 1, target=dict(node=rig.idx[b], path='rotation')))
    hp = np.array([f[1]['pelvis'] for f in frames])
    samplers.append(dict(input=tin, output=add(hp, 'VEC3'), interpolation='LINEAR'))
    channels.append(dict(sampler=len(samplers) - 1, target=dict(node=rig.idx['pelvis'], path='translation')))
    J['animations'] = [dict(name=name, samplers=samplers, channels=channels)]
    J['buffers'] = [dict(byteLength=len(g.bin))]
    (out_dir / 'clips').mkdir(parents=True, exist_ok=True); (out_dir / 'anim').mkdir(parents=True, exist_ok=True)
    full = out_dir / 'clips' / f'{name}.glb'; g.save(full)
    strip_clip.strip(str(full), str(out_dir / 'anim' / f'{name}.glb'))
    return dict(frames=n, seconds=round((n - 1) / FPS, 3), loop=loop, note=note)


# ------------------------------------------------------------------ procedural clips
def idle_clip(rig, seconds=3.0):
    frames = []
    n = int(round(seconds * FPS))
    for f in range(n + 1):
        t = f / FPS; w = 2 * math.pi * t / seconds
        params = {('spine_01', 'x'): 1.2 * math.sin(w), ('spine_02', 'x'): 0.8 * math.sin(w), ('spine_03', 'x'): 0.6 * math.sin(w),
                  ('head', 'y'): 3.0 * math.sin(w + 1.0), ('head', 'x'): 1.0 * math.sin(2 * w),
                  ('upperarm_l', 'x'): 2.0 * math.sin(w + .5), ('upperarm_r', 'x'): -2.0 * math.sin(w + .5),
                  ('upperarm_l', 'z'): 1.2 * math.sin(w), ('upperarm_r', 'z'): -1.2 * math.sin(w),
                  ('pelvis', 'z'): 0.4 * math.sin(w)}
        frames.append(rig.apply_pose(params, [0, -0.008 * (1 - math.cos(w)) / 2, 0]))
    return frames


def attack_clip(rig, style, seconds):
    # Two styles. hammer (Warden): the right fist rises back and up, the torso winds, then an overhand blow with the hips
    # driving forward. slash (Reaper): both arms wind up and sweep across (claw and weapon arm), a quicker strike.
    if style == 'hammer':
        wind = {('upperarm_r', 'x'): 75, ('upperarm_r', 'z'): -20, ('lowerarm_r', 'x'): 55, ('spine_01', 'y'): -22, ('spine_02', 'y'): -10, ('spine_01', 'x'): -10,
                ('upperarm_l', 'x'): -25, ('head', 'y'): 12, ('thigh_l', 'x'): -8, ('calf_l', 'x'): 10}
        strike = {('upperarm_r', 'x'): -70, ('upperarm_r', 'z'): 10, ('lowerarm_r', 'x'): 10, ('spine_01', 'y'): 24, ('spine_02', 'y'): 10, ('spine_01', 'x'): 22,
                  ('spine_02', 'x'): 8, ('upperarm_l', 'x'): 30, ('head', 'x'): 10, ('thigh_r', 'x'): -12, ('calf_r', 'x'): 20, ('thigh_l', 'x'): 10}
        windT, hitT = 0.42, 0.56
    else:
        wind = {('upperarm_r', 'x'): 55, ('upperarm_r', 'z'): -45, ('lowerarm_r', 'x'): 40, ('upperarm_l', 'x'): 50, ('upperarm_l', 'z'): 45, ('lowerarm_l', 'x'): 35,
                ('spine_01', 'y'): -18, ('spine_01', 'x'): -8, ('head', 'x'): -6}
        strike = {('upperarm_r', 'x'): -75, ('upperarm_r', 'z'): 25, ('lowerarm_r', 'x'): -10, ('upperarm_l', 'x'): -80, ('upperarm_l', 'z'): -25, ('lowerarm_l', 'x'): -10,
                  ('spine_01', 'y'): 20, ('spine_01', 'x'): 24, ('spine_02', 'x'): 10, ('head', 'x'): 12, ('thigh_r', 'x'): -14, ('calf_r', 'x'): 24, ('thigh_l', 'x'): 12}
        windT, hitT = 0.40, 0.52
    keys = [(0.0, {}, [0, 0, 0], 'smooth'),
            (seconds * windT, wind, [0, -0.02, -0.06], 'smooth'),
            (seconds * hitT, strike, [0, -0.04, 0.12], 'out'),
            (seconds * (hitT + 0.12), strike, [0, -0.03, 0.10], 'smooth'),
            (seconds, {}, [0, 0, 0], 'smooth')]
    return keyframed(rig, keys, seconds), (windT + hitT) / 2 + 0.03


def talk_clip(rig, seconds=4.0):
    """Counter talk for Brann (the delivered human rig): head nods and glances, the right hand rises in an explaining gesture
    and settles, a small weight shift. Loops (ends on the start pose)."""
    frames = []; n = int(round(seconds * FPS))
    for f in range(n + 1):
        t = f / FPS; u = t / seconds; w = 2 * math.pi * u
        g = smooth((t - .3) / .5) * (1 - smooth((t - 2.3) / .7))      # gesture envelope: up by 0.8 s, down by 3.0 s
        params = {('head', 'x'): 4.0 * math.sin(2 * w) * (0.5 + 0.5 * g) + 1.5 * math.sin(w), ('head', 'y'): 5.0 * math.sin(w + .8), ('head', 'z'): 1.5 * math.sin(2 * w + 1.0),
                  ('spine_01', 'x'): 1.0 * math.sin(w), ('spine_01', 'y'): 3.0 * math.sin(w + .4), ('spine_02', 'x'): 0.8 * math.sin(w),
                  ('upperarm_r', 'x'): -38 * g + 1.5 * math.sin(w), ('upperarm_r', 'z'): -14 * g, ('lowerarm_r', 'x'): -55 * g, ('lowerarm_r', 'y'): 20 * g * math.sin(3 * w),
                  ('hand_r', 'x'): -20 * g + 10 * g * math.sin(4 * w), ('upperarm_l', 'x'): 2.0 * math.sin(w + .5), ('upperarm_l', 'z'): 1.0 * math.sin(w),
                  ('pelvis', 'z'): 1.2 * math.sin(w + 2.0)}
        frames.append(rig.apply_pose(params, [0.012 * math.sin(w + 2.0), -0.006 * (1 - math.cos(w)) / 2, 0]))
    return frames


def hit_clip(rig, seconds=0.6):
    flinch = {('spine_01', 'x'): -12, ('spine_02', 'x'): -6, ('head', 'x'): -14, ('upperarm_l', 'x'): -22, ('upperarm_r', 'x'): -22, ('upperarm_l', 'z'): 8, ('upperarm_r', 'z'): -8,
              ('thigh_l', 'x'): -6, ('thigh_r', 'x'): -6, ('calf_l', 'x'): 10, ('calf_r', 'x'): 10}
    keys = [(0.0, {}, [0, 0, 0], 'out'), (seconds * .25, flinch, [0, -0.03, -0.07], 'out'), (seconds, {}, [0, 0, 0], 'smooth')]
    return keyframed(rig, keys, seconds)


def death_clip(rig, seconds):
    stagger = {('spine_01', 'x'): -8, ('head', 'x'): -10, ('upperarm_l', 'x'): -15, ('upperarm_r', 'x'): -15}
    kneel = {('thigh_l', 'x'): -70, ('thigh_r', 'x'): -62, ('calf_l', 'x'): 125, ('calf_r', 'x'): 118, ('spine_01', 'x'): 10, ('head', 'x'): 18,
             ('upperarm_l', 'x'): -20, ('upperarm_r', 'x'): -25, ('foot_l', 'x'): -40, ('foot_r', 'x'): -40}
    prone = {('pelvis', 'x'): 86, ('thigh_l', 'x'): 6, ('thigh_r', 'x'): 10, ('calf_l', 'x'): 8, ('calf_r', 'x'): 14, ('spine_01', 'x'): -6, ('spine_02', 'x'): -4,
             ('head', 'x'): -30, ('upperarm_l', 'x'): -75, ('upperarm_r', 'x'): -70, ('upperarm_l', 'z'): 20, ('upperarm_r', 'z'): -20, ('lowerarm_l', 'x'): -30, ('lowerarm_r', 'x'): -30,
             ('foot_l', 'x'): -20, ('foot_r', 'x'): -20}
    p = rig.rest_t['pelvis'][1]
    keys = [(0.0, {}, [0, 0, 0], 'smooth'), (seconds * .14, stagger, [0, -0.04, -0.05], 'out'),
            (seconds * .42, kneel, [0, 0.52 - p, -0.02], 'smooth'), (seconds * .55, kneel, [0, 0.50 - p, 0.0], 'smooth'),
            (seconds * .85, prone, [0, 0.26 - p, 0.42], 'out'), (seconds, prone, [0, 0.24 - p, 0.44], 'smooth')]
    return keyframed(rig, keys, seconds)


# ------------------------------------------------------------------ measurements
def stride_speed(rig, ch, feet, duration):
    """In-place locomotion: the planted foot slides backward at the travel speed. Median |dz/dt| of the lowest foot."""
    ts = np.arange(0, duration, 1 / FPS); pos = {f: [] for f in feet}
    for t in ts:
        L = {b: sample(ch, b, 'rotation', t) for b in rig.joints}; L = {b: q for b, q in L.items() if q is not None}
        T = {'pelvis': sample(ch, 'pelvis', 'translation', t)}
        P, _ = rig.fk(L, T)
        for f in feet: pos[f].append(P[f])
    speeds = []
    for f in feet:
        p = np.array(pos[f]); vz = np.abs(np.diff(p[:, 2]) * FPS); low = p[:-1, 1] < np.percentile(p[:, 1], 35)
        if low.any(): speeds.append(np.median(vz[low]))
    sole = min(float(np.min(np.array(pos[f])[:, 1])) for f in feet)
    return float(np.mean(speeds)), sole


def build_rig(key, spec):
    out = HERE / key / 'build'; out.mkdir(parents=True, exist_ok=True)
    g = GLB(spec['walk']); r = {'source_walk': spec['walk'].name, 'source_run': spec['run'].name}
    rec['inputs'][key] = dict(walk=str(spec['walk'].relative_to(HERE.parent)), run=str(spec['run'].relative_to(HERE.parent)))
    # textures
    r['textures'] = export_textures(g, HERE / key / 'textures', spec['name'])
    # skin: four influences only, renormalised
    pr = g.j['meshes'][0]['primitives'][0]; w0 = g.acc(pr['attributes']['WEIGHTS_0']); s = w0.sum(1, keepdims=True); s[s == 0] = 1
    g.write_acc(pr['attributes']['WEIGHTS_0'], w0 / s)
    dropped = [k for k in list(pr['attributes']) if k in ('JOINTS_1', 'JOINTS_2', 'WEIGHTS_1', 'WEIGHTS_2')]
    for k in dropped: del pr['attributes'][k]
    r['skin'] = dict(dropped_sets=dropped, weights0_sum_min_before=round(float(w0.sum(1).min()), 3), joints=len(g.j['skins'][0]['joints']))
    g.j.pop('animations', None)
    tmp = out / '_tmp_geo.glb'; g.save(tmp)
    geo = out / f"{spec['name']}_geo.glb"; strip_images.strip(str(tmp), str(geo)); tmp.unlink()
    rig = Rig(geo)
    mesh_pos = GLB(spec['walk']).acc(pr['attributes']['POSITION']) if False else None
    P0, Q0 = rig.fk({}, {})
    r['rest'] = dict(pelvis=P0['pelvis'].round(3).tolist(), head=P0['head'].round(3).tolist(), headfront=P0['headfront'].round(3).tolist(),
                     faces_plus_z=bool((P0['headfront'] - P0['head'])[2] > 0), feet={f: P0[f].round(3).tolist() for f in ('ball_l', 'ball_r', 'foot_l', 'foot_r')},
                     hands={h: P0[h].round(3).tolist() for h in ('hand_l', 'hand_r')})
    # locomotion clips from the delivered files
    clips = {}
    for cname, src in (('walk', spec['walk']), ('run', spec['run'])):
        sg = GLB(src); ch = load_channels(sg); dur = float(max(v[0][-1] for v in ch.values()))
        (out / 'anim').mkdir(exist_ok=True); strip_clip.strip(str(src), str(out / 'anim' / f'{cname}.glb'))
        speed, sole = stride_speed(rig, ch, ['ball_l', 'ball_r'], dur)
        clips[cname] = dict(seconds=round(dur, 3), loop=True, native_speed_mps=round(speed, 3), lowest_sole=round(sole, 3), note=f'Meshy delivered {cname} (in place), as is')
    # procedural clips
    clips['idle'] = write_clip(rig, geo, out, 'idle', idle_clip(rig), 'procedural: breathing sway on the rest pose (3 s loop)', True)
    fr, impact = attack_clip(rig, spec['style'], spec['attack_seconds'])
    clips['attack'] = write_clip(rig, geo, out, 'attack', fr, f"procedural {spec['style']} strike; blow lands at normalized {impact:.2f}", False); clips['attack']['impact_normalized'] = round(impact, 3)
    clips['hit'] = write_clip(rig, geo, out, 'hit', hit_clip(rig), 'procedural flinch (0.6 s, returns to the stance)', False)
    clips['death'] = write_clip(rig, geo, out, 'death', death_clip(rig, spec['death_seconds']), 'procedural: stagger, drop to the knees, topple forward prone (ClampForever)', False)
    if spec.get('talk'): clips['talk'] = write_clip(rig, geo, out, 'talk', talk_clip(rig), 'procedural counter talk for Brann: nods, right-hand explaining gesture, weight shift (4 s loop)', True)
    r['clips'] = clips
    r['geo'] = str(geo.relative_to(HERE)); r['anim_dir'] = str((out / 'anim').relative_to(HERE))
    r['bones'] = dict(root='pelvis', feet=['ball_l', 'ball_r'], head='head', headfront='headfront', hand_r='hand_r', hand_l='hand_l')
    rec[key] = r


def build_sentinel():
    """Carl (2 Oct, after the brief): the Post Sentinel is a wheeled mobile droid, not a turret. The delivered mesh is one
    triangle soup, so the tyre is split off per triangle (every vertex inside a 0.215 m cylinder about the hub axis and
    within the tyre's 15 cm width; the fork sits outside that band) into its own mesh under a 'Wheel' node pivoted on the
    hub, so FeralDroid can spin it with the ground speed. Body keeps the rest; Muzzle (rifle tip), Head and Hat nodes."""
    out = HERE / 'sentinel' / 'build'; out.mkdir(parents=True, exist_ok=True)
    g = GLB(SENTINEL); r = {'source': SENTINEL.name}
    rec['inputs']['sentinel'] = str(SENTINEL.relative_to(HERE.parent))
    r['textures'] = export_textures(g, HERE / 'sentinel' / 'textures', 'PostSentinel')
    pr = g.j['meshes'][0]['primitives'][0]; pos = g.acc(pr['attributes']['POSITION']); lo, hi = pos.min(0), pos.max(0)
    lift = -lo[1]; pos2 = pos.copy(); pos2[:, 1] += lift
    nrm = g.acc(pr['attributes']['NORMAL']); uv = g.acc(pr['attributes']['TEXCOORD_0']); idx = g.acc(pr['indices']).reshape(-1, 3)
    r['bounds'] = dict(min=pos2.min(0).round(3).tolist(), max=pos2.max(0).round(3).tolist(), height=round(float(hi[1] - lo[1]), 3), lifted=round(float(lift), 4))
    # wheel: hub on the tyre's axis (model-right/left = X), radius from the tyre's top
    low = pos2[pos2[:, 1] < 0.36]; tyre = pos2[(np.abs(pos2[:, 0] - low[:, 0].mean()) < 0.07) & (pos2[:, 1] < 0.42)]
    hub = np.array([low[:, 0].mean(), tyre[:, 1].max() / 2, tyre[:, 2].mean()]); R = float(tyre[:, 1].max() / 2)
    tri = pos2[idx]
    inwheel = (np.hypot(tri[:, :, 1] - hub[1], tri[:, :, 2] - hub[2]) < R * 1.03).all(1) & (np.abs(tri[:, :, 0] - hub[0]) < 0.075).all(1)
    r['wheel'] = dict(hub=hub.round(4).tolist(), radius=round(R, 4), triangles=int(inwheel.sum()), body_triangles=int((~inwheel).sum()))
    # rifle: thin vertical cluster on the model's right (-X) side between the hip and the knee; its lowest vertex is the muzzle
    side = pos2[(pos2[:, 0] < -0.16) & (pos2[:, 1] > 0.15) & (pos2[:, 1] < 1.25)]
    r['rifle_cluster'] = dict(count=int(len(side)), min=side.min(0).round(3).tolist() if len(side) else None, max=side.max(0).round(3).tolist() if len(side) else None)
    muzzle = side[np.argmin(side[:, 1])] if len(side) else np.array([-0.2, 0.3, 0.1])
    headband = pos2[(pos2[:, 1] > 1.42) & (pos2[:, 1] < 1.66) & (np.hypot(pos2[:, 0], pos2[:, 2]) < 0.18)]
    head = headband.mean(0) if len(headband) else np.array([0, 1.55, 0])
    hat = pos2[pos2[:, 1] > 1.72]; hatc = hat.mean(0) if len(hat) else np.array([0, 1.8, 0])
    r['head'] = head.round(3).tolist(); r['hat'] = dict(centre=hatc.round(3).tolist(), radius=round(float(np.hypot(hat[:, 0], hat[:, 2]).max()), 3) if len(hat) else None)
    r['muzzle'] = muzzle.round(3).tolist()
    # two meshes from one: re-index each part's vertices (same material, UVs and normals)
    j = g.j; mat = pr.get('material', 0)
    bin2 = bytearray(); views = []; accs = []
    def add(arr, typ, comp, target=None):
        arr = np.ascontiguousarray(arr)
        while len(bin2) % 4: bin2.append(0)
        v = dict(buffer=0, byteOffset=len(bin2), byteLength=arr.nbytes)
        if target: v['target'] = target
        views.append(v); bin2.extend(arr.tobytes())
        a = dict(bufferView=len(views) - 1, componentType=comp, count=len(arr), type=typ)
        if typ == 'VEC3' and comp == 5126: a['min'] = arr.min(0).tolist(); a['max'] = arr.max(0).tolist()
        accs.append(a); return len(accs) - 1
    meshes = []
    for name, sel, origin in (('Body', ~inwheel, np.zeros(3)), ('Wheel', inwheel, hub)):
        used = np.unique(idx[sel]); remap = np.full(len(pos2), -1, np.int64); remap[used] = np.arange(len(used))
        P = (pos2[used] - origin).astype(np.float32); N = nrm[used].astype(np.float32); U = uv[used].astype(np.float32)
        I = remap[idx[sel]].astype(np.uint32).ravel()
        prim = dict(attributes=dict(POSITION=add(P, 'VEC3', 5126, 34962), NORMAL=add(N, 'VEC3', 5126, 34962), TEXCOORD_0=add(U, 'VEC2', 5126, 34962)), indices=add(I, 'SCALAR', 5125, 34963), material=mat, mode=4)
        meshes.append(dict(name=name, primitives=[prim]))
    nodes = [dict(name='Body', mesh=0, children=[1, 2, 3, 4]), dict(name='Wheel', mesh=1, translation=[float(x) for x in hub]),
             dict(name='Muzzle', translation=[float(x) for x in muzzle + np.array([0, -0.01, 0])]), dict(name='Head', translation=[float(x) for x in head]), dict(name='Hat', translation=[float(x) for x in hatc])]
    out_j = dict(asset=dict(version='2.0', generator='prep_models.py'), scene=0, scenes=[dict(nodes=[0])], nodes=nodes, meshes=meshes,
                 materials=[dict(name='PostSentinel', pbrMetallicRoughness=dict(baseColorFactor=[1, 1, 1, 1], metallicFactor=1, roughnessFactor=1), doubleSided=False)],
                 accessors=accs, bufferViews=views, buffers=[dict(byteLength=len(bin2))])
    g2 = GLB.__new__(GLB); g2.j = out_j; g2.bin = bin2; geo = out / 'PostSentinel_geo.glb'; g2.save(geo)
    r['geo'] = str(geo.relative_to(HERE)); r['triangles'] = int(len(idx)); r['nodes'] = [n['name'] for n in nodes]
    rec['sentinel'] = r


for k, spec in RIGS.items(): build_rig(k, spec)
build_sentinel()
(HERE / 'handoff.json').write_text(json.dumps(rec, indent=1))
print(json.dumps({k: {c: (v.get('seconds'), v.get('native_speed_mps')) for c, v in rec[k]['clips'].items()} for k in RIGS}))
print('sentinel', json.dumps({k: rec['sentinel'][k] for k in ('bounds', 'muzzle', 'head', 'hat', 'rifle_cluster', 'wheel')}))
print('PREP DONE')
