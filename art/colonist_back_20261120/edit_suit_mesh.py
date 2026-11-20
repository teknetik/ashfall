#!/usr/bin/env python3
"""Fix round (20 Nov 2026): close the colonist's collar and sleeve hems in colonist.glb by moving vertex positions only.

What the renders showed: the suit's collar edge and rolled sleeve ends are the jagged cut left by the 2 Oct jumpsuit
fit, and under them the skin mesh ends in an equally jagged hole edge (the body faces once hidden by the suit were
deleted; the 5 Oct pass then lowered the collar, so a black gap opened at the nape between collar and neck).
For each hem, working along the hem axis in 360 angular sectors:
  - suit: the boundary vertices go exactly onto a smooth target ring (the boundary profile low-pass filtered round
    the loop), the suit vertices within L behind the hem are stretched monotonically per sector (no folding); vertices
    inside the frayed spikes are pulled back onto the ring (degenerate slivers, invisible);
  - skin: the skin's hole edge is pushed the other way, `tuck` metres under the suit, stretching the skin within L
    of its edge, so no gap can open between the two.
Vertex count and order, indices, UVs, weights, joints, inverse bind matrices, normals and tangents are unchanged; only
the POSITION accessors of the PlayerJumpsuit and PlayerSkin primitives (and their min/max) are rewritten.
Usage: edit_suit_mesh.py IN.glb OUT.glb [report.json]"""
import json, os, struct, sys
import numpy as np

def load(p):
    b = bytearray(open(p, 'rb').read()); jl = struct.unpack('<I', b[12:16])[0]
    j = json.loads(bytes(b[20:20 + jl])); return b, j, 28 + jl
def acc(b, j, b0, i):
    a = j['accessors'][i]; v = j['bufferViews'][a['bufferView']]
    n = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}[a['type']]
    dt = {5126: np.float32, 5125: np.uint32, 5123: np.uint16, 5121: np.uint8}[a['componentType']]
    off = b0 + v.get('byteOffset', 0) + a.get('byteOffset', 0)
    stride = v.get('byteStride', 0); size = np.dtype(dt).itemsize * n
    assert stride in (0, size), 'interleaved'
    return np.frombuffer(bytes(b[off:off + size * a['count']]), dt).reshape(a['count'], n).copy(), off

src, dst = sys.argv[1], sys.argv[2]
b, j, b0 = load(src)
mesh = j['meshes'][0]; matnames = [m['name'] for m in j['materials']]
skin = j['skins'][0]; ibm, _ = acc(b, j, b0, skin['inverseBindMatrices'])
names = [j['nodes'][k]['name'] for k in skin['joints']]
def joint(n): return np.linalg.inv(ibm[names.index(n)].reshape(4, 4).T)[:3, 3]

class Prim:
    def __init__(self, mat):
        self.prim = next(p for p in mesh['primitives'] if p.get('material') == matnames.index(mat))
        self.P, self.off = acc(b, j, b0, self.prim['attributes']['POSITION']); self.P = self.P.astype(np.float64)
        self.N, _ = acc(b, j, b0, self.prim['attributes']['NORMAL'])
        I, _ = acc(b, j, b0, self.prim['indices']); I = I.reshape(-1, 3).astype(np.int64)
        key = np.round(self.P / 1e-5).astype(np.int64)
        _, weld = np.unique(key, axis=0, return_inverse=True); weld = weld.ravel()
        W = weld[I]; E = np.sort(np.concatenate([W[:, [0, 1]], W[:, [1, 2]], W[:, [2, 0]]]), axis=1)
        ue, cnt = np.unique(E, axis=0, return_counts=True)
        bw = np.unique(ue[cnt == 1].ravel())
        self.is_bnd = np.isin(weld, bw)          # per original vertex: lies on an open edge
        self.weld = weld; self.E = ue           # welded edges, for smoothing
    def write(self):
        P32 = self.P.astype(np.float32); b[self.off:self.off + P32.nbytes] = P32.tobytes()
        a = j['accessors'][self.prim['attributes']['POSITION']]; a['min'] = P32.min(0).tolist(); a['max'] = P32.max(0).tolist()

NB = 360
class Frame:
    def __init__(self, origin, axis):
        self.o = np.asarray(origin, float); self.a = np.asarray(axis, float) / np.linalg.norm(axis)
        r = np.cross(self.a, [0, 0, 1.0])
        if np.linalg.norm(r) < 1e-3: r = np.cross(self.a, [1.0, 0, 0])
        self.r1 = r / np.linalg.norm(r); self.r2 = np.cross(self.a, self.r1)
    def coords(self, X):
        d = X - self.o; t = d @ self.a
        rad = np.linalg.norm(d - np.outer(t, self.a), axis=1)
        k = ((np.arctan2(d @ self.r2, d @ self.r1) + np.pi) / (2 * np.pi) * NB).astype(int) % NB
        return t, rad, k

def profile(t, k, how):
    prof = np.full(NB, np.nan)
    for i in range(NB):
        s = k == i
        if s.any(): prof[i] = getattr(np, how)(t[s])
    ok = ~np.isnan(prof); xs = np.arange(NB)
    return np.interp(xs, xs[ok], prof[ok], period=NB)
def lowpass(p, sigma_deg):
    sig = sigma_deg / 360 * NB; kx = np.arange(-int(3 * sig), int(3 * sig) + 1)
    ker = np.exp(-kx ** 2 / (2 * sig * sig)); ker /= ker.sum()
    return np.array([np.sum(p[(i + kx) % NB] * ker) for i in range(NB)])

def move(pr, fr, sel_bnd, target, L, rmax, outer_only=False):
    """Boundary vertices of `pr` selected by sel_bnd go to target[k]; others within L of the hem stretch per sector."""
    t, rad, k = fr.coords(pr.P)
    edge = profile(t[sel_bnd], k[sel_bnd], 'min')       # the deepest point of the jagged edge in each sector
    tg = target[k]; e = edge[k]; lo = np.minimum(e, tg) - L
    near = (rad < rmax) & (t > lo) & (t <= t[sel_bnd].max() + 0.005)   # nothing beyond the hem's own extent
    newt = np.where(t <= e, lo + (t - lo) * (tg - lo) / np.maximum(e - lo, 1e-6), tg)   # spikes beyond e: onto the ring
    if outer_only:
        # a folded collar: its under-layer must not be dragged out to the rim through the outer layer (that crumpled
        # it into dark slivers); vertices past the edge that face inwards keep their height
        d = pr.P - fr.o; radial = d - np.outer(d @ fr.a, fr.a); radial /= np.linalg.norm(radial, axis=1, keepdims=True) + 1e-9
        inward = np.sum(pr.N * radial, axis=1) < 0
        newt = np.where((t > e) & inward & ~sel_bnd, t, newt)
    newt = np.where(sel_bnd, tg, newt)
    dt = np.where(near, newt - t, 0.0)
    pr.P += np.outer(dt, fr.a)
    return {'edge': edge.tolist(), 'L': L, 'moved': int((np.abs(dt) > 1e-6).sum()), 'max_move_mm': round(float(np.abs(dt).max() * 1000), 1),
            'edge_range_mm': round(float((edge.max() - edge.min()) * 1000), 1)}

def taubin(pr, wmask, iters=12, lam=0.5, mu=-0.53):
    """Taubin smoothing of the welded vertices in wmask (welded ids), others fixed; split copies follow their weld."""
    nw = pr.weld.max() + 1; Wp = np.zeros((nw, 3)); Wp[pr.weld] = pr.P
    e = pr.E; deg = np.bincount(e.ravel(), minlength=nw).astype(float)
    for it in range(iters):
        for f in (lam, mu):
            acc_ = np.zeros((nw, 3)); np.add.at(acc_, e[:, 0], Wp[e[:, 1]]); np.add.at(acc_, e[:, 1], Wp[e[:, 0]])
            lap = acc_ / np.maximum(deg, 1)[:, None] - Wp
            Wp = Wp + f * lap * wmask[:, None]
    pr.P = Wp[pr.weld]

suit = Prim('PlayerJumpsuit'); skinp = Prim('PlayerSkin')
report = {'hems': {}}
neck, head = joint('neck'), joint('Head')
# hem specs: name, frame origin, axis pointing OUT of the sleeve/collar (away from the suit), region radius, band
specs = [('collar', neck, head - neck, 0.12, (-0.07, 0.06), 28, 0.08)]   # L 0.035 squeezed the collar's fold layers into crumples
for side in ('Left', 'Right'):
    fa, hd = joint(side + 'ForeArm'), joint(side + 'Hand')
    specs.append(('sleeve_' + side[0], fa, hd - fa, 0.10, (-0.10, 0.16), 30, 0.05))
TUCK = 0.012
for name, o, ax, rmax, (t0, t1), sigma, L in specs:
    fr = Frame(o, ax)
    t, rad, k = fr.coords(suit.P)
    region = (rad < rmax) & (t > t0) & (t < t1)
    sb = suit.is_bnd & region
    if name != 'collar':      # the sleeve end: the outermost boundary band along the arm
        tmax = t[sb].max(); sb &= t > tmax - 0.10
    else:
        sb &= t > np.percentile(t[sb], 5)
    # the rims are partly closed folds (no open edge): add every suit vertex within 4 mm of the outermost point of its
    # sector, so the folded collar/cuff edge itself is flattened, not only the open boundary
    secmax = profile(t[region], k[region], 'max')
    if name == 'collar':
        d_ = suit.P - fr.o; rad_ = d_ - np.outer(d_ @ fr.a, fr.a); rad_ /= np.linalg.norm(rad_, axis=1, keepdims=True) + 1e-9
        if os.environ.get('CB_COLLAR_RIM', '1') == '1': sb |= region & (t > secmax[k] - 0.004) & (np.sum(suit.N * rad_, axis=1) > 0.2)
    else:
        sb |= region & (t > secmax[k] - 0.004)
    prof = profile(t[sb], k[sb], os.environ.get('CB_PROF', 'median'))
    target = lowpass(prof, sigma)
    if name == 'collar' and os.environ.get('CB_RAISE', '0') == '1':
        target = np.maximum(target, lowpass(profile(t[sb], k[sb], 'max'), sigma))
    r = {'suit': move(suit, fr, sb, target, L, rmax, outer_only=(name == 'collar' and os.environ.get('CB_OUTER', '1') == '1'))}
    # skin: the hole edge under this hem, pushed `TUCK` back under the suit (frame reversed: skin lies beyond the hem)
    frs = Frame(o, -fr.a)
    ts, rads, ks = frs.coords(skinp.P)
    sk = skinp.is_bnd & (rads < rmax) & (ts > -(target.max() + 0.06)) & (ts < -(target.min() - 0.08))
    if sk.any():
        r['skin'] = move(skinp, frs, sk, -(target - TUCK), 0.03, rmax)
    report['hems'][name] = {'origin': fr.o.tolist(), 'axis': fr.a.tolist(), 'ref': fr.r1.tolist(), 'ref2': fr.r2.tolist(),
                            'target': target.tolist(), 'rmax': rmax, **r}
# the collar band under the new rim: the 5 Oct collar lowering left it a crumpled crease (dark slivers once the
# patchwork texture no longer hid it); smooth the suit 1-7 cm below the rim, fading in and out
h = report['hems']['collar']; frc = Frame(h['origin'], h['axis'])
tc, radc, kc = frc.coords(suit.P); tgc = np.array(h['target'])[kc]
w = np.clip(((tgc - tc) - 0.004) / 0.012, 0, 1) * np.clip((0.085 - (tgc - tc)) / 0.02, 0, 1) * (radc < 0.13) * ~suit.is_bnd
wm = np.zeros(suit.weld.max() + 1); np.maximum.at(wm, suit.weld, w)
P_before = suit.P.copy(); taubin(suit, wm, iters=int(os.environ.get('CB_SMOOTH', '15')))
report['collar_smooth'] = {'verts': int((wm > 0).sum()), 'max_move_mm': round(float(np.linalg.norm(suit.P - P_before, axis=1).max() * 1000), 1)}
print('collar smooth', report['collar_smooth'])
suit.write(); skinp.write()
js = json.dumps(j, separators=(',', ':')).encode(); js += b' ' * ((4 - len(js) % 4) % 4)
jl0 = struct.unpack('<I', b[12:16])[0]; binpart = bytes(b[20 + jl0:])
open(dst, 'wb').write(b'glTF' + struct.pack('<II', 2, 12 + 8 + len(js) + len(binpart)) + struct.pack('<I', len(js)) + b'JSON' + js + binpart)
print(json.dumps({k: {kk: {x: y for x, y in vv.items() if x != 'edge'} for kk, vv in v.items() if kk in ('suit', 'skin')} for k, v in report['hems'].items()}, indent=1))
if len(sys.argv) > 3: json.dump(report, open(sys.argv[3], 'w'), indent=1)
