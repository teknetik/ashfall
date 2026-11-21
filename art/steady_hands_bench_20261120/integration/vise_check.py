#!/usr/bin/env python3
"""Steady Hands bench, integration: is the pistol, clamped at fixtures.vise/seat_work, clear of the jaws where the
player works on it (the grip, its wrap, wires, screws, scales), and reachable from above and from the player's side?
By numbers from the two GLBs (no Unity, no Blender): the pistol's frame node takes the pose mark's transform
(SEAM.md section 2), the jaw is closed to the family's own snug value. Writes vise_check.json beside the evidence."""
import json, struct, sys, os
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
ART = os.path.join(ROOT, 'unity/AthenHill/Assets/AthenHill/Art/Bench')
OUT = os.path.join(ROOT, 'unity/evidence/steady_hands/20261120/integration/vise_check.json')

def load(path):
    with open(path, 'rb') as f:
        f.read(12); jl, _ = struct.unpack('<II', f.read(8)); js = json.loads(f.read(jl)); bl, _ = struct.unpack('<II', f.read(8)); blob = f.read(bl)
    return js, blob

def local(n):
    if 'matrix' in n: return np.array(n['matrix'], float).reshape(4, 4).T
    t = np.array(n.get('translation', [0, 0, 0]), float); q = np.array(n.get('rotation', [0, 0, 0, 1]), float); s = np.array(n.get('scale', [1, 1, 1]), float)
    x, y, z, w = q
    r = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    m = np.eye(4); m[:3, :3] = r * s; m[:3, 3] = t
    return m

class Model:
    def __init__(self, path):
        self.js, self.blob = load(path); self.nodes = self.js['nodes']; self.parent = {}
        for i, n in enumerate(self.nodes):
            for c in n.get('children', []): self.parent[c] = i
        self.byname = {n.get('name'): i for i, n in enumerate(self.nodes)}
        self.override = {}
    def world(self, i):
        m = self.override.get(i, local(self.nodes[i]))
        return self.world(self.parent[i]) @ m if i in self.parent else m
    def points(self, name):
        """Vertices of a mesh node in the model's own space (skinning ignored: the vise parts are rigid on their bones)."""
        i = self.byname[name]; n = self.nodes[i]; out = []
        for pr in self.js['meshes'][n['mesh']]['primitives']:
            a = self.js['accessors'][pr['attributes']['POSITION']]; bv = self.js['bufferViews'][a['bufferView']]
            off = bv.get('byteOffset', 0) + a.get('byteOffset', 0); stride = bv.get('byteStride', 12)
            raw = np.frombuffer(self.blob, dtype=np.uint8, count=(a['count'] - 1) * stride + 12, offset=off)
            pts = np.lib.stride_tricks.as_strided(raw, shape=(a['count'], 12), strides=(stride, 1)).copy().view('<f4').reshape(-1, 3)
            out.append(pts.astype(float))
        p = np.vstack(out); w = self.world(i)
        return (w[:3, :3] @ p.T).T + w[:3, 3]

def box(p): return {'min': [round(float(v) * 1000, 1) for v in p.min(0)], 'max': [round(float(v) * 1000, 1) for v in p.max(0)]}

fx = Model(os.path.join(ART, 'Fixtures/fixtures.glb')); ps = Model(os.path.join(ART, 'Pistol/pistol.glb'))
fparts = json.load(open(os.path.join(ART, 'Fixtures/fixtures.parts.json')))
jaw = next(p for p in fparts['params'] if p['id'] == 'fixtures.vise_jaw')
snug = jaw['snug_at']['pistol.frame']['jaw']
# the jaw parameter is a slide of the bone vise_jaw: read the clip's two ends
anim = next(a for a in fx.js['animations'] if a['name'] == 'vise_jaw_param'); ch = anim['channels'][0]; sm = anim['samplers'][ch['sampler']]
def acc(i, comps):
    a = fx.js['accessors'][i]; bv = fx.js['bufferViews'][a['bufferView']]
    return np.frombuffer(fx.blob, dtype='<f4', count=a['count'] * comps, offset=bv.get('byteOffset', 0) + a.get('byteOffset', 0)).reshape(-1, comps)
times = acc(sm['input'], 1)[:, 0]; values = acc(sm['output'], 3)
t0, t1 = values[0].astype(float), values[-1].astype(float)
bone = ch['target']['node']; n = fx.nodes[bone]
def set_jaw(v):
    m = local(n); m[:3, 3] = t0 + (t1 - t0) * v; fx.override[bone] = m
vise_inv = np.linalg.inv(fx.world(fx.byname['fixtures_vise']))
def in_vise(p): return (vise_inv[:3, :3] @ p.T).T + vise_inv[:3, 3]

report = {'frame': 'vise node space, millimetres: glTF axes, +Y up; Unity bench-local x is -X here', 'snugValue': snug, 'clipTravelMm': round(float(np.linalg.norm(t1 - t0)) * 1000, 2)}
set_jaw(0); open_m = in_vise(fx.points('fixtures_vise_pad_m'))
set_jaw(snug); pad_m = in_vise(fx.points('fixtures_vise_pad_m')); pad_f = in_vise(fx.points('fixtures_vise_pad_f')); slide = in_vise(fx.points('fixtures_vise_slide')); body = in_vise(fx.points('fixtures_vise'))
report['padFixed'] = box(pad_f); report['padMovingAtSnug'] = box(pad_m); report['padMovingOpen'] = box(open_m)
# which axis the jaw closes along, and the gap between the two pads at snug
axis = int(np.argmax(np.abs(open_m.mean(0) - pad_m.mean(0)))); report['closingAxis'] = 'XYZ'[axis]
lo, hi = sorted([(pad_f[:, axis].min(), pad_f[:, axis].max()), (pad_m[:, axis].min(), pad_m[:, axis].max())])
gap = (lo[1], hi[0]); report['gapAtSnugMm'] = round(float(gap[1] - gap[0]) * 1000, 2)
jaw_top = max(pad_f[:, 1].max(), pad_m[:, 1].max()); report['jawTopMm'] = round(float(jaw_top) * 1000, 1)

# the pistol: its frame node takes the mark's transform
mark = local(fx.nodes[fx.byname['fixtures_vise__mark_seat_work']])   # in the vise node's space already (a child of it)
frame_inv = np.linalg.inv(ps.world(ps.byname['pistol_frame']))
def pistol(name):
    p = ps.points(name); p = (frame_inv[:3, :3] @ p.T).T + frame_inv[:3, 3]
    return (mark[:3, :3] @ p.T).T + mark[:3, 3]
parts = {}
work = ['pistol_wrap', 'pistol_bind_wire_a', 'pistol_bind_wire_b', 'pistol_scale_l', 'pistol_scale_r', 'pistol_screw_grip_a', 'pistol_screw_grip_b', 'pistol_housing', 'pistol_housing_pin', 'pistol_lead_plug', 'pistol_cell', 'pistol_cell_latch']
others = ['pistol_frame', 'pistol_barrel', 'pistol_dust_cover', 'pistol_trigger']
pads_lo = np.minimum(pad_f.min(0), pad_m.min(0)); pads_hi = np.maximum(pad_f.max(0), pad_m.max(0))
jaws_lo = np.minimum(np.minimum(body.min(0), slide.min(0)), pads_lo); jaws_hi = np.maximum(np.maximum(body.max(0), slide.max(0)), pads_hi)
problems = []
for name in work + others:
    if name not in ps.byname: continue
    p = pistol(name); row = box(p)
    # share of the part's vertices between the pads (inside the pads' box): what the jaws bite on
    inside = np.all((p >= pads_lo - 1e-4) & (p <= pads_hi + 1e-4), axis=1)
    row['verticesBetweenThePads'] = int(inside.sum()); row['shareBetweenThePads'] = round(float(inside.mean()), 3)
    row['lowestAboveJawTopMm'] = round(float(p[:, 1].min() - jaw_top) * 1000, 1)
    # squeezed: reaches past the pad faces along the closing axis while level with the pads
    level = (p[:, 1] >= pads_lo[1]) & (p[:, 1] <= pads_hi[1]) & np.all((np.delete(p, axis, 1) >= np.delete(pads_lo, axis) - 1e-4) & (np.delete(p, axis, 1) <= np.delete(pads_hi, axis) + 1e-4), axis=1)
    if level.any():
        over = max(float(gap[0] - p[level, axis].min()), float(p[level, axis].max() - gap[1]))
        row['pastThePadFacesMm'] = round(over * 1000, 2)
    parts[name] = row
    if name in work and row['shareBetweenThePads'] > 0.02: problems.append(f"{name}: {row['shareBetweenThePads'] * 100:.0f} % of it lies between the pads (it is one of the parts the player works on)")
    if name in work and row['lowestAboveJawTopMm'] < 0 and name not in ('pistol_cell', 'pistol_cell_latch'): problems.append(f"{name}: reaches {-row['lowestAboveJawTopMm']:.1f} mm below the top of the jaws")
report['parts'] = parts
fr = pistol('pistol_frame'); wr = pistol('pistol_wrap') if 'pistol_wrap' in ps.byname else fr
report['clampedBy'] = [k for k, v in parts.items() if v.get('verticesBetweenThePads', 0) > 0]
report['frameWidthBetweenThePadsMm'] = None
lvl = (fr[:, 1] >= pads_lo[1]) & (fr[:, 1] <= pads_hi[1])
if lvl.any(): report['frameWidthBetweenThePadsMm'] = round(float(fr[lvl, axis].max() - fr[lvl, axis].min()) * 1000, 2)
report['gripAboveJawTopMm'] = [round(float(wr[:, 1].min() - jaw_top) * 1000, 1), round(float(wr[:, 1].max() - jaw_top) * 1000, 1)]
report['problems'] = problems
os.makedirs(os.path.dirname(OUT), exist_ok=True); json.dump(report, open(OUT, 'w'), indent=1)
print(json.dumps({k: v for k, v in report.items() if k != 'parts'}, indent=1))
for k, v in parts.items(): print(f"{k:24s} y {v['min'][1]:7.1f}..{v['max'][1]:7.1f}  x {v['min'][0]:7.1f}..{v['max'][0]:7.1f}  z {v['min'][2]:7.1f}..{v['max'][2]:7.1f}  between pads {v['shareBetweenThePads']:.3f}  past faces {v.get('pastThePadFacesMm')}")
