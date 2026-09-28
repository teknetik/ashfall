# Blender 5.2 headless: first-person two-hand cup grip v5 (PlayerFPHands_v5), 27 Sep 2026 evening, request #6 rework.
# v3/v4 built the hands from procedural tubes and spheres; review round 1 (t_6c931016 comment #903) rejected that
# (straight splayed fingers, boxy palm, detached tip capsules, flat material). v5 starts instead from a real anatomical
# hand: the MakeHuman hm08 base mesh and its game-engine skin weights (both released CC0 by the MakeHuman project;
# copies and provenance in fp_arms/makehuman_cc0/). The forearm, hand and finger cage is cut from the base mesh,
# given a finger skeleton from the mesh's own joint helpers, placed on the view-model pistol (authored in the pistol's
# own frame, Unity axes, metres) and each finger joint is curled until it touches the pistol or the other hand
# (collision-driven cup grip), so fingers wrap the grip with ~1.2 mm glove clearance and never pass through it.
# Then: Catmull-Clark subdivision, fingerless leather glove (skin on the distal phalanges, separate nail material),
# bracer/sleeve over the cut forearm, baked tangent-space leather-grain normal map and AO (2k), GLB export.
# Usage: blender -b -P build_fp_hands_v5.py -- <out.glb> [render_dir|-]
import bpy, bmesh, sys, math, json, os
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

FP = os.path.dirname(os.path.abspath(__file__)) + '/'
MH = FP + 'makehuman_cc0/'
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else FP + 'PlayerFPHands_v5.glb'
RENDER = argv[1] if len(argv) > 1 and argv[1] != '-' else None
TEXDIR = os.path.join(os.path.dirname(OUT), 'PlayerFPHands_v5_tex')
TEXRES = int(os.environ.get('FP_TEXRES', '2048'))
SUBDIV = int(os.environ.get('FP_SUBDIV', '2'))
MARGIN = float(os.environ.get('FP_MARGIN', '0.0012'))
HAND_LEN = float(os.environ.get('FP_HAND_LEN', '0.190'))   # wrist joint to middle fingertip, adult male
P = json.loads(os.environ.get('FP_PARAMS', '{}'))            # layout overrides for iteration

def U2B(v): return Vector((v[0], v[2], v[1]))
def nrm(v): v = np.asarray(v, float); return v / np.linalg.norm(v)
def rot(axis, ang):
    a = nrm(axis); c = math.cos(ang); s = math.sin(ang); x, y, z = a
    return np.array([[c + x*x*(1-c), x*y*(1-c) - z*s, x*z*(1-c) + y*s],
                     [y*x*(1-c) + z*s, c + y*y*(1-c), y*z*(1-c) - x*s],
                     [z*x*(1-c) - y*s, z*y*(1-c) + x*s, c + z*z*(1-c)]])

# ---------------------------------------------------------------- pistol (pistol frame, Unity axes)
def load_pistol():
    V = []; F = []; cur = None; start = {}
    for l in open(FP + 'pistol_frame.obj'):
        if l[0] == 'o': cur = l.split()[1]; start[cur] = len(V)
        elif l[0] == 'v': V.append([float(x) for x in l.split()[1:]])
        elif l[0] == 'f' and cur.startswith('pistol'): F.append([int(x) - 1 for x in l.split()[1:]])
    return np.array(V[:start['oldarms_char1']]), F
PV, PF = load_pistol()
INFO = json.load(open(FP + 'pistol_frame.json'))
PBVH = BVHTree.FromPolygons([Vector(v) for v in PV], PF)
# (sign calibrated in main once SIGN exists)

# ---------------------------------------------------------------- MakeHuman hm08 (CC0)
def load_mh():
    V = []; VT = []; faces = []; groups = {}; cur = None
    for l in open(MH + 'base.obj'):
        if l.startswith('v '): V.append([float(x) for x in l.split()[1:4]])
        elif l.startswith('vt '): VT.append([float(x) for x in l.split()[1:3]])
        elif l.startswith('g '): cur = l.split()[1]
        elif l.startswith('f '):
            t = [x.split('/') for x in l.split()[1:]]
            vi = [int(a[0]) - 1 for a in t]; ti = [int(a[1]) - 1 for a in t]
            groups.setdefault(cur, set()).update(vi)
            if cur == 'body': faces.append((vi, ti))
    V = np.array(V) * .1
    V = np.stack([-V[:, 0], V[:, 1], V[:, 2]], 1)   # MakeHuman (Y up, faces +Z, right-handed) -> Unity (left-handed)
    return V, np.array(VT), faces, groups
MV, MVT, MFACES, MGROUPS = load_mh()
MW = json.load(open(MH + 'weights.game_engine.json'))['weights']
def joint(name): return MV[sorted(MGROUPS[name])].mean(0)

FINGERS = ['thumb', 'index', 'middle', 'ring', 'pinky']
def skeleton(s):
    """bones (name, parent, head, tail) in rest, from the base mesh's joint helper cubes"""
    J = lambda n: joint('joint-%s-%s' % (s, n))
    b = [('lowerarm', None, J('elbow'), J('hand')), ('hand', 'lowerarm', J('hand'), J('finger-3-1'))]
    for f, nm in enumerate(FINGERS, 1):
        for k in (1, 2, 3):
            b.append(('%s_0%d' % (nm, k), 'hand' if k == 1 else '%s_0%d' % (nm, k - 1), J('finger-%d-%d' % (f, k)), J('finger-%d-%d' % (f, k + 1))))
    return b

def nail_verts():
    img = bpy.data.images.load(MH + 'mpfb_fingernails.jpg'); w, h = img.size
    px = np.empty(w * h * 4, np.float32); img.pixels.foreach_get(px); px = px.reshape(h, w, 4)[:, :, 0]
    nails = set()
    for vi, ti in MFACES:
        uv = MVT[ti].mean(0); x = min(w - 1, int(uv[0] * w)); y = min(h - 1, int(uv[1] * h))
        if px[y, x] > .5: nails.update(vi)
    return nails
NAILS = None

class Arm:
    def __init__(self, s):
        self.s = s
        bones = skeleton(s)
        self.names = [b[0] for b in bones]; self.parent = [self.names.index(b[1]) if b[1] else -1 for b in bones]
        self.head = np.array([b[2] for b in bones]); self.tail = np.array([b[3] for b in bones])
        # vertices: skinned to the forearm, hand or fingers
        wmap = {}
        for i, nm in enumerate(self.names):
            for vi, w in MW.get(nm + '_' + s, []): wmap.setdefault(vi, {})[i] = w
        keep = [vi for vi, d in wmap.items() if sum(d.values()) > .5 and vi in MGROUPS['body']]
        # cut the forearm 70 mm behind the wrist joint (the bracer covers the cut)
        wr = self.head[1]; fa = nrm(self.head[0] - wr)
        keep = sorted(vi for vi in keep if (MV[vi] - wr) @ fa < .07)
        kset = set(keep); remap = {v: i for i, v in enumerate(keep)}
        self.faces = [[remap[v] for v in vi] for vi, ti in MFACES if all(v in kset for v in vi)]
        used = sorted(set(v for f in self.faces for v in f))
        re2 = {v: i for i, v in enumerate(used)}; self.faces = [[re2[v] for v in f] for f in self.faces]
        src = [keep[u] for u in used]
        self.rest = MV[src]
        W = np.zeros((len(src), len(self.names)))
        for i, vi in enumerate(src):
            for b, w in wmap[vi].items(): W[i, b] = w
        self.W = W / W.sum(1, keepdims=True)
        self.nail = np.array([vi in NAILS for vi in src])
        # uniform scale about the wrist: wrist joint -> middle fingertip = HAND_LEN
        mid_tip = self.tail[self.names.index('middle_03')]
        sc = HAND_LEN / np.linalg.norm(mid_tip - wr); self.scale = sc
        for arr in (self.rest, self.head, self.tail): arr[:] = wr + (arr - wr) * sc
        # palm normal (pointing out of the palm) per finger from its nail: flexion axis = cross(dir, palm normal)
        self.flex = {}
        for f in FINGERS:
            i3 = self.names.index(f + '_03')
            m = self.nail & (self.W[:, i3] > .5)
            nc = self.rest[m].mean(0)
            for k in (1, 2, 3):
                i = self.names.index('%s_0%d' % (f, k)); d = nrm(self.tail[i] - self.head[i])
                dors = nc - self.head[i3]; dors = nrm(dors - d * (dors @ d))
                d3 = nrm(self.tail[i3] - self.head[i3]); dors3 = nrm((nc - self.head[i3]) - d3 * ((nc - self.head[i3]) @ d3))
                pn = -nrm(dors3 - d * (dors3 @ d))
                self.flex[i] = nrm(np.cross(d, pn))
        # hand frame: palm normal from the knuckle line and the middle metacarpal
        kn = nrm(self.head[self.names.index('index_01')] - self.head[self.names.index('pinky_01')])
        ax = nrm(self.head[self.names.index('middle_01')] - wr)
        m = self.nail & (self.W[:, self.names.index('middle_03')] > .5)
        pn = np.cross(kn, ax); pn = nrm(pn)
        if (self.rest[m].mean(0) - self.tail[self.names.index('middle_02')]) @ pn > 0: pn = -pn
        self.palm_n = pn
        self.local = [np.eye(3) for _ in self.names]
        self.G = np.eye(4)
        self.dominant = self.W.argmax(1)

    def idx(self, n): return self.names.index(n)
    def mats(self):
        M = [None] * len(self.names)
        for i in range(len(self.names)):
            T = np.eye(4); T[:3, :3] = self.local[i]; T[:3, 3] = self.head[i] - self.local[i] @ self.head[i]
            M[i] = (M[self.parent[i]] if self.parent[i] >= 0 else self.G) @ T
        return M
    def posed(self, sel=None):
        M = self.mats(); R = self.rest if sel is None else self.rest[sel]; W = self.W if sel is None else self.W[sel]
        Rh = np.c_[R, np.ones(len(R))]
        out = np.zeros((len(R), 3))
        for i, m in enumerate(M):
            w = W[:, i]
            if w.any(): out += w[:, None] * (Rh @ m.T)[:, :3]
        return out
    def pj(self, i, which='head'):
        M = self.mats(); p = self.head[i] if which == 'head' else self.tail[i]
        return (M[i] @ np.r_[p, 1])[:3]
    def chain_sel(self, i):
        """vertices dominated by bone i or its descendants in the same finger"""
        f = self.names[i][:-3]; k = int(self.names[i][-1])
        ids = [self.idx('%s_0%d' % (f, j)) for j in range(k, 4)]
        return np.isin(self.dominant, ids)

SIGN = {}
OCC = {}
def build_occ(bvh, pts, res=.001):
    """solid occupancy grid by majority vote of scanline ray parity along X, Y and Z (the Meshy pistol is not
    watertight, so a nearest-face normal sign is unreliable more than a few mm inside)"""
    lo = np.asarray(pts).min(0) - .003; hi = np.asarray(pts).max(0) + .003
    n = np.ceil((hi - lo) / res).astype(int) + 1
    votes = np.zeros(n, np.int8)
    for ax in range(3):
        a1, a2 = [k for k in range(3) if k != ax]
        d = Vector([1 if k == ax else 0 for k in range(3)])
        for i in range(n[a1]):
            for j in range(n[a2]):
                o = np.zeros(3); o[a1] = lo[a1] + i * res; o[a2] = lo[a2] + j * res; o[ax] = lo[ax] - .01
                q = Vector(o); hits = []
                for _ in range(40):
                    h = bvh.ray_cast(q, d)
                    if h[0] is None: break
                    hits.append(h[0][ax]); q = h[0] + d * 1e-5
                if len(hits) < 2: continue
                if len(hits) % 2: hits = hits[:-1]
                for s0, s1 in zip(hits[0::2], hits[1::2]):
                    k0 = max(0, int(math.ceil((s0 - lo[ax]) / res))); k1 = min(n[ax] - 1, int(math.floor((s1 - lo[ax]) / res)))
                    if k1 < k0: continue
                    idx = [i, j]; sl = [slice(None)] * 3; sl[a1] = i; sl[a2] = j; sl[ax] = slice(k0, k1 + 1)
                    votes[tuple(sl)] += 1
    OCC[id(bvh)] = (lo, res, votes >= 2)
    return int((votes >= 2).sum())

def occ_inside(bvh, p):
    lo, res, g = OCC[id(bvh)]; k = np.round((np.asarray(p) - lo) / res).astype(int)
    if (k < 0).any() or (k >= g.shape).any(): return False
    return bool(g[tuple(k)])
def calib_sign(bvh, pts):
    """+1 if the BVH's face normals point outwards (rays from outside hit front faces), else -1"""
    c = np.asarray(pts).mean(0); votes = 0
    for d in np.random.default_rng(3).normal(size=(64, 3)):
        d = nrm(d); o = c + d * .6
        hit = bvh.ray_cast(Vector(o), Vector(-d))
        if hit[0] is not None: votes += 1 if hit[1].dot(Vector(-d)) < 0 else -1
    SIGN[id(bvh)] = 1 if votes >= 0 else -1
    return SIGN[id(bvh)]

def dist_arr(pts, bvhs):
    """per-point signed clearance (negative = inside) against the union of the BVHs"""
    out = np.full(len(pts), .05)
    for b in bvhs:
        sg = SIGN.get(id(b), 1); solid = id(b) in OCC
        for k, p in enumerate(pts):
            h = b.find_nearest(Vector(p), .05)
            if h[0] is None: continue
            ins = occ_inside(b, p) if solid else sg * (Vector(p) - h[0]).dot(h[1]) < 0
            v = -h[3] if ins else h[3]
            if v < out[k]: out[k] = v
    return out

def fit(arm, finger, bvhs, tip_target=None, dir_target=None, wrap=1.0, starts=(0., .6, 1.1), sub=2):
    """optimised finger pose: hug the surfaces it faces (palmar side at MARGIN clearance) without penetrating,
    optionally reaching a tip target; MCP flex+abduction, PIP and DIP flex (thumb: flex+abduction on all three)"""
    ids = [arm.idx('%s_0%d' % (finger, k)) for k in (1, 2, 3)]
    thumb = finger == 'thumb'
    axes = []
    for i in ids:
        d = nrm(arm.tail[i] - arm.head[i]); f = arm.flex[i]; axes.append((f, nrm(np.cross(d, f)), nrm(np.cross(f, d))))
    sel = np.where(arm.chain_sel(ids[0]))[0][::sub]
    # palmar-side vertices of this finger (rest pose): offset from the bone line towards the palm
    pal = []
    for vi in sel:
        b = arm.dominant[vi]; j = ids.index(b) if b in ids else 0
        h = arm.head[ids[j]]; d = nrm(arm.tail[ids[j]] - h); off = arm.rest[vi] - h; off = off - d * (off @ d)
        pal.append(off @ axes[j][2] > 0)
    pal = np.array(pal)
    npar = 6 if thumb else 4
    def apply(x):
        if thumb:
            for j, i in enumerate(ids): arm.local[i] = rot(axes[j][0], x[2 * j]) @ rot(axes[j][1], x[2 * j + 1])
        else:
            arm.local[ids[0]] = rot(axes[0][0], x[0]) @ rot(axes[0][1], x[1])
            arm.local[ids[1]] = rot(axes[1][0], x[2]); arm.local[ids[2]] = rot(axes[2][0], x[3])
    lim = [(-.3, 1.6), (-.6, .6)] * 3 if thumb else [(-.2, 1.65), (-.3, .3), (0, 1.85), (0, 1.4)]
    def cost(x):
        apply(x); Pp = arm.posed(sel); d = dist_arr(Pp, bvhs)
        c = 1e7 * np.sum(np.clip(MARGIN - d, 0, None) ** 2)
        c += wrap * 1e4 * np.mean(np.clip(d[pal] - MARGIN, 0, .02) ** 2)
        if tip_target is not None:
            t = arm.pj(ids[2], 'tail'); c += 1e4 * np.sum((t - tip_target) ** 2)
            if dir_target is not None: c += 2 * (1 - nrm(t - arm.pj(ids[1])) @ nrm(dir_target))
        ab = x[1::2] if thumb else x[1:2]
        c += .05 * np.sum(np.asarray(x) ** 2) + 2 * np.sum(np.asarray(ab) ** 2)
        if not thumb: c += .5 * (x[3] - .7 * x[2]) ** 2   # DIP follows PIP (coupled tendon)
        return c
    best = None
    for s0 in starts:
        x = np.zeros(npar)
        if thumb: x[0::2] = s0 * .5
        else: x[0] = s0; x[2] = s0 * 1.1; x[3] = s0 * .8
        cb = cost(x)
        for s in (.25, .12, .06, .03, .015):
            for _ in range(5):
                imp = False
                for j in range(npar):
                    for sg in (1, -1):
                        y = x.copy(); y[j] = min(max(y[j] + sg * s, lim[j][0]), lim[j][1])
                        c = cost(y)
                        if c < cb: x, cb, imp = y, c, True
                if not imp: break
        if best is None or cb < best[1]: best = (x, cb)
    x = best[0]; apply(x)
    d = dist_arr(arm.posed(sel), bvhs)
    LOG.setdefault('fit_' + arm.s, {})[finger] = {'deg': np.round(np.degrees(x), 1).tolist(), 'cost': round(float(best[1]), 3),
                                                   'min_clear_mm': round(float(d.min()) * 1000, 2), 'palmar_mean_gap_mm': round(float(np.mean(d[pal])) * 1000, 1),
                                                   'tip_err_mm': None if tip_target is None else round(float(np.linalg.norm(arm.pj(ids[2], 'tail') - tip_target)) * 1000, 1)}

def min_dist(pts, bvhs):
    """signed minimum clearance (negative = inside) of pts against the BVHs"""
    d = 1e9
    for b in bvhs:
        sg = SIGN.get(id(b), 1); solid = id(b) in OCC
        for p in pts:
            h = b.find_nearest(Vector(p), .06)
            if h[0] is None: continue
            if solid: inside_ = occ_inside(b, p)
            else: inside_ = sg * (Vector(p) - h[0]).dot(h[1]) < 0
            d = min(d, -h[3] if inside_ else h[3])
    return d

def kabsch(src, dst, w):
    w = np.asarray(w, float)[:, None]; cs = (src * w).sum(0) / w.sum(); cd = (dst * w).sum(0) / w.sum()
    H = ((src - cs) * w).T @ (dst - cd); U, S, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(Vt.T @ U.T)); D = np.diag([1, 1, d])
    R = Vt.T @ D @ U.T; G = np.eye(4); G[:3, :3] = R; G[:3, 3] = cd - R @ cs
    return G

def place(arm, targets, weights):
    names = list(targets)
    src = np.array([arm.head[arm.idx(n)] if n != 'wrist' else arm.head[1] for n in names])
    arm.G = kabsch(src, np.array([targets[n] for n in names]), [weights[n] for n in names])

def settle(arm, bvhs, direction, sel, start=.012, step=.0004):
    """translate the whole hand from `start` metres out along -direction towards `direction` until `sel` touches"""
    d = nrm(direction); arm.G[:3, 3] -= d * start; moved = -start
    for _ in range(int(start * 2 / step)):
        arm.G[:3, 3] += d * step
        if min_dist(arm.posed(sel)[::2], bvhs) < MARGIN: arm.G[:3, 3] -= d * step; break
        moved += step
    # diagnostic: where the palm touches, in the hand's rest frame (mm along wrist->middle knuckle, across to pinky)
    pts = arm.posed(sel); best = (9, None)
    for i, p in enumerate(pts):
        for b in bvhs:
            h = b.find_nearest(Vector(p), .05)
            if h[0] is not None and h[3] < best[0]: best = (h[3], i)
    if best[1] is not None:
        rv = arm.rest[np.where(sel)[0][best[1]]] - arm.head[1]
        e1 = nrm(arm.head[arm.idx('middle_01')] - arm.head[1]); e2 = nrm(arm.head[arm.idx('pinky_01')] - arm.head[arm.idx('index_01')])
        LOG['settle_contact_' + arm.s] = {'along_mm': round(float(rv @ e1) * 1000), 'across_mm': round(float(rv @ e2) * 1000),
                                          'normal_mm': round(float(rv @ arm.palm_n) * 1000), 'at': np.round(pts[best[1]], 4).tolist()}
    return moved

LOG = {}
RATIO = (1.0, 1.15, .75)   # natural coupled flexion of MCP : PIP : DIP
def curl(arm, finger, bvhs, max_deg=(95, 105, 80), step=1.5, pre=None):
    """collision-driven flexion: all three joints bend together in the natural ratio until any part of the finger
    touches (MARGIN); then the remaining distal joints continue on their own (proximal first). pre = start angles"""
    ids = [arm.idx('%s_0%d' % (finger, k)) for k in (1, 2, 3)]
    ang = list(pre or [0, 0, 0])
    def apply():
        for j, i in enumerate(ids): arm.local[i] = rot(arm.flex[i], math.radians(ang[j]))
    sel = arm.chain_sel(ids[0])
    apply(); floor = min(MARGIN, min_dist(arm.posed(sel)[::2], bvhs))
    while all(ang[j] + step * RATIO[j] <= max_deg[j] for j in range(3)):
        old = ang[:]; ang = [a + step * r for a, r in zip(ang, RATIO)]; apply()
        if min_dist(arm.posed(sel)[::2], bvhs) < floor: ang = old; apply(); break
    for k in (1, 2):
        s2 = arm.chain_sel(ids[k])
        while ang[k] + step <= max_deg[k]:
            ang[k] += step; apply()
            if min_dist(arm.posed(s2)[::2], bvhs) < floor: ang[k] -= step; apply(); break
    LOG.setdefault('curl_' + arm.s, {})[finger] = [round(a, 1) for a in ang]
    return ang

def thumb_fit(arm, tip_target, bvhs, dir_target=None):
    """coordinate search on the thumb's three joints (two axes each) towards a tip target, rejecting contact"""
    ids = [arm.idx('thumb_0%d' % k) for k in (1, 2, 3)]
    sel = arm.chain_sel(ids[0])
    axes = []
    for i in ids:
        d = nrm(arm.tail[i] - arm.head[i]); f = arm.flex[i]; axes.append((f, nrm(np.cross(d, f))))
    x = np.zeros(6)
    def apply(x):
        for j, i in enumerate(ids): arm.local[i] = rot(axes[j][0], x[2 * j]) @ rot(axes[j][1], x[2 * j + 1])
    def cost(x):
        apply(x); t = arm.pj(ids[2], 'tail'); c = np.linalg.norm(t - tip_target)
        if dir_target is not None: c += .01 * (1 - nrm(t - arm.pj(ids[1])) @ nrm(dir_target))
        pen = max(0., MARGIN - min_dist(arm.posed(sel)[::2], bvhs))
        return c + .002 * np.abs(x).sum() + 20 * pen
    best = cost(x)
    for s in (.3, .15, .08, .04, .02):
        for _ in range(4):
            for j in range(6):
                for sg in (1, -1):
                    y = x.copy(); y[j] += sg * s
                    if abs(y[j]) > 1.6: continue
                    c = cost(y)
                    if c < best: x, best = y, c
    apply(x)
    LOG['thumb_clear_mm_' + arm.s] = round(min_dist(arm.posed(sel)[::2], bvhs) * 1000, 2)
    LOG['thumb_' + arm.s] = {'deg': np.round(np.degrees(x), 1).tolist(), 'tip_err_mm': round(float(np.linalg.norm(arm.pj(ids[2], 'tail') - tip_target)) * 1000, 1)}

# ---------------------------------------------------------------- layout (pistol frame; grip frontstrap z~.025,
# backstrap z~-.045 (top) .. -.01 (bottom), side panels x~+-.022, trigger guard bottom y~-.019, trigger z~.06 y~0)
def D(k, v): return np.array(P.get(k, v), float)
GA = nrm((0, 1, .37))                  # grip axis (rakes back towards the bottom)
GF = nrm((0, -GA[2], GA[1]))            # forward, perpendicular to the grip axis

def place_frame(arm, meta_dir, knuckle_dir, anchor_bone, anchor_pos):
    """rigid placement from the hand's rest frame (wrist->middle knuckle, index->pinky knuckle line) to targets"""
    wr = arm.head[1]
    e1 = nrm(arm.head[arm.idx('middle_01')] - wr)
    e2 = arm.head[arm.idx('pinky_01')] - arm.head[arm.idx('index_01')]; e2 = nrm(e2 - e1 * (e2 @ e1))
    t1 = nrm(meta_dir); t2 = np.asarray(knuckle_dir, float); t2 = nrm(t2 - t1 * (t2 @ t1))
    Rr = np.stack([e1, e2, np.cross(e1, e2)], 1); Rt = np.stack([t1, t2, np.cross(t1, t2)], 1)
    R = Rt @ Rr.T; G = np.eye(4); G[:3, :3] = R
    G[:3, 3] = anchor_pos - R @ arm.head[arm.idx(anchor_bone)]
    arm.G = G
    return R @ arm.palm_n

def tilt(v, axis, deg): return rot(axis, math.radians(deg)) @ np.asarray(v, float)

def place_opt(arm, bvhs, targets, tw, name):
    """6-DOF placement: Kabsch start from anatomical landmark targets, then coordinate descent on
    penetration of the palm/proximal phalanges (hard), palmar palm hug (soft) and landmark priors (soft)"""
    lm = {'web': arm.head[arm.idx('thumb_01')], 'wrist': arm.head[1]}
    for n in ('index_01', 'middle_01', 'pinky_01'): lm[n] = arm.head[arm.idx(n)]
    names = list(targets)
    src = np.array([lm[n] for n in names]); dst = np.array([targets[n] for n in names])
    G0 = kabsch(src, dst, [tw[n] for n in names])
    body = np.where(arm.dominant == 1)[0][::2]   # palm only: fingers are fitted afterwards
    palm = np.where(arm.dominant == 1)[0]
    pal = palm[((arm.rest[palm] - arm.head[1]) @ arm.palm_n) > .0][::2]
    wts = np.array([tw[n] for n in names])
    def G_of(x):
        R = rot([1, 0, 0], x[3]) @ rot([0, 1, 0], x[4]) @ rot([0, 0, 1], x[5])
        c = G0[:3, :3] @ lm['middle_01'] + G0[:3, 3]
        G = np.eye(4); G[:3, :3] = R @ G0[:3, :3]; G[:3, 3] = R @ (G0[:3, 3] - c) + c + x[:3]
        return G
    def cost(x):
        arm.G = G_of(x)
        db = dist_arr(arm.posed(body), bvhs); dp = dist_arr(arm.posed(pal), bvhs)
        c = 1e7 * np.sum(np.clip(MARGIN - db, 0, None) ** 2)
        c += 1e4 * np.mean(np.clip(dp - MARGIN, 0, .03) ** 2) * P.get('hug_' + name, 1.0)
        pr = (arm.G[:3, :3] @ src.T).T + arm.G[:3, 3]
        c += 1e4 * np.sum(wts * np.sum((pr - dst) ** 2, 1)) / wts.sum() * P.get('prior_' + name, 1.0)
        return c
    x = np.zeros(6); cb = cost(x)
    for s in (.008, .004, .002, .001, .0005):
        for _ in range(6):
            imp = False
            for j in range(6):
                for sg in (1, -1):
                    y = x.copy(); y[j] += sg * (s if j < 3 else s * 8)
                    c = cost(y)
                    if c < cb: x, cb, imp = y, c, True
            if not imp: break
    arm.G = G_of(x)
    db = dist_arr(arm.posed(body), bvhs); dp = dist_arr(arm.posed(pal), bvhs)
    pr = (arm.G[:3, :3] @ src.T).T + arm.G[:3, 3]
    LOG['place_' + name] = {'cost': round(float(cb), 3), 'body_min_clear_mm': round(float(db.min()) * 1000, 2),
                            'palm_mean_gap_mm': round(float(dp.mean()) * 1000, 1),
                            'landmark_err_mm': {n: round(float(np.linalg.norm(pr[i] - dst[i])) * 1000, 1) for i, n in enumerate(names)}}

def bend_wrist(arm, target_dir, max_deg=45):
    """swing the forearm about the wrist towards target_dir (wrist->elbow) while the hand stays put: the root
    transform rotates about the wrist and the hand bone counter-rotates (linear-blend skinning bends the wrist)"""
    wr = arm.pj(1); d0 = nrm(arm.pj(0) - wr); t = nrm(target_dir)
    ax = np.cross(d0, t); s = np.linalg.norm(ax)
    if s < 1e-6: return
    ang = min(math.atan2(s, d0 @ t), math.radians(max_deg))
    Rw = rot(ax, ang); Gw = np.eye(4); Gw[:3, :3] = Rw; Gw[:3, 3] = wr - Rw @ wr
    G_old = arm.G.copy(); arm.G = Gw @ arm.G
    arm.local[1] = (np.linalg.inv(arm.G) @ G_old)[:3, :3] @ arm.local[1]
    LOG['wrist_bend_deg_' + arm.s] = round(math.degrees(ang), 1)

def pose_right(arm):
    # high firing grip: web of the hand high on the backstrap under the beavertail, knuckles on the front-right
    # corner of the grip, index MCP just below the frame; fingers then wrap the frontstrap
    place_opt(arm, [PBVH], {'web': D('R_web', [.014, -.004, -.050]), 'index_01': D('R_i1', [.036, -.012, .006]),
                            'middle_01': D('R_m1', [.036, -.034, .006]), 'pinky_01': D('R_p1', [.030, -.074, -.004]),
                            'wrist': D('R_wr', [.028, -.062, -.090])},
              {'web': 2, 'index_01': 1, 'middle_01': 2, 'pinky_01': 1, 'wrist': 1}, 'R')
    bend_wrist(arm, D('R_fore', [.34, -.42, -.84]))
    fit(arm, 'index', [PBVH], tip_target=D('R_trig', [-.004, -.006, .070]), wrap=.3)
    for f in ('middle', 'ring', 'pinky'): fit(arm, f, [PBVH])
    fit(arm, 'thumb', [PBVH], tip_target=D('R_thumb_tip', [-.028, .014, .030]), dir_target=[0, .1, 1], wrap=.3)

def pose_left(arm, bvhs):
    # support: heel of the palm fills the free left panel, knuckles outside the firing fingertips at the front-left,
    # fingers wrap round the front of the firing fingers; thumb forward along the frame under the firing thumb
    place_opt(arm, bvhs, {'web': D('L_web', [-.036, -.028, -.020]), 'index_01': D('L_i1', [-.046, -.036, .036]),
                          'middle_01': D('L_m1', [-.048, -.056, .034]), 'pinky_01': D('L_p1', [-.046, -.092, .020]),
                          'wrist': D('L_wr', [-.058, -.098, -.050])},
              {'web': 1, 'index_01': 1, 'middle_01': 2, 'pinky_01': 1, 'wrist': 1}, 'L')
    bend_wrist(arm, D('L_fore', [-.40, -.42, -.81]))
    for f in ('index', 'middle', 'ring', 'pinky'): fit(arm, f, bvhs)
    fit(arm, 'thumb', bvhs, tip_target=D('L_thumb_tip', [-.028, -.004, .058]), dir_target=[0, 0, 1], wrap=.3)

def pose_right_old(arm):
    # high grip: MCP knuckles on the right panel ~mid-depth, metacarpals forward (perpendicular to the grip axis),
    # knuckle line down the grip axis; the palm settles onto the right panel/backstrap, fingers then curl round
    # the frontstrap and end on the left front corner
    meta = tilt(GF, [1, 0, 0], -P.get('R_meta_pitch', 0)); meta = tilt(meta, [0, 1, 0], P.get('R_meta_yaw', -5))
    pn = place_frame(arm, meta, -GA, 'middle_01', D('R_mcp', [.048, -.036, -.012]))
    LOG['R_palm_normal'] = np.round(pn, 3).tolist()
    body = np.isin(arm.dominant, [1])
    LOG['settle_R_mm'] = round(settle(arm, [PBVH], pn, body, start=P.get('R_settle_start', .02)) * 1000, 1)
    fit(arm, 'index', [PBVH], tip_target=D('R_trig', [-.004, -.006, .070]), wrap=.3)
    for f in ('middle', 'ring', 'pinky'): fit(arm, f, [PBVH])
    fit(arm, 'thumb', [PBVH], tip_target=D('R_thumb_tip', [-.030, .016, .034]), dir_target=[0, .1, 1], wrap=.3)

def pose_left_old(arm, bvhs):
    # (superseded) palm heel on the free left panel, MCPs at the left front just outside the firing fingertips,
    # metacarpals canted down ~20 deg; fingers curl round the front of the firing fingers to the right side
    meta = tilt(GF, [1, 0, 0], P.get('L_meta_pitch', 20)); meta = tilt(meta, [0, 1, 0], P.get('L_meta_yaw', 15))
    pn = place_frame(arm, meta, tilt(-GA, [1, 0, 0], P.get('L_roll', 0)), 'middle_01', D('L_mcp', [-.058, -.048, .020]))
    LOG['L_palm_normal'] = np.round(pn, 3).tolist()
    body = np.isin(arm.dominant, [1])
    LOG['settle_L_mm'] = round(settle(arm, bvhs, pn, body, start=P.get('L_settle_start', .02)) * 1000, 1)
    for f in ('index', 'middle', 'ring', 'pinky'): fit(arm, f, bvhs)
    fit(arm, 'thumb', bvhs, tip_target=D('L_thumb_tip', [-.030, -.004, .060]), dir_target=[0, 0, 1], wrap=.3)

# ---------------------------------------------------------------- mesh assembly
def mk_obj(name, verts, faces):
    me = bpy.data.meshes.new(name)
    me.from_pydata([U2B(v) for v in verts], [], [f[::-1] for f in faces])
    me.validate()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    return o

MATS = {}
def mat(name, col, rough, metal=0, emit=None):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    lin = tuple(((c + .055) / 1.055) ** 2.4 if c > .04045 else c / 12.92 for c in col)
    b.inputs['Base Color'].default_value = (*lin, 1); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    if emit: b.inputs['Emission Color'].default_value = (*emit, 1); b.inputs['Emission Strength'].default_value = 2.0
    MATS[name] = m; return m
ORDER = ['FPHandsSkin', 'FPHandsGlove', 'FPHandsBracer', 'FPHandsSleeve', 'FPHandsNail', 'FPHandsGlow']

def hand_object(arm):
    V = arm.posed()
    o = mk_obj('hand_' + arm.s, V, arm.faces)
    for mname in ORDER: o.data.materials.append(MATS[mname])
    distal = [arm.idx(f + '_03') for f in FINGERS]
    wd = arm.W[:, distal].sum(1)
    cut = P.get('skin_cut', .6)
    for p in o.data.polygons:
        vs = list(p.vertices)
        if all(arm.nail[v] for v in vs): p.material_index = 4
        elif wd[vs].mean() > cut: p.material_index = 0
        else: p.material_index = 1
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(o.data); bm.free()
    # outward check: normals should point away from the bone lines (flip if the majority point inwards)
    ctr = np.array([arm.pj(arm.dominant[p.vertices[0]]) for p in o.data.polygons])
    nn = np.array([(p.normal.x, p.normal.z, p.normal.y) for p in o.data.polygons]); cc = np.array([(p.center.x, p.center.z, p.center.y) for p in o.data.polygons])
    if (((cc - ctr) * nn).sum(1) < 0).mean() > .5:
        for p in o.data.polygons: p.flip()
    if SUBDIV:
        m = o.modifiers.new('sub', 'SUBSURF'); m.levels = SUBDIV; m.render_levels = SUBDIV
        bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_apply(modifier='sub')
    # glove leather thickness: push glove-only vertices out 0.7 mm (0.35 at the fingerless cut) for a readable edge
    me = o.data; gl = np.zeros(len(me.vertices)); ot = np.zeros(len(me.vertices))
    for p in me.polygons:
        for v in p.vertices:
            if p.material_index == 1: gl[v] += 1
            else: ot[v] += 1
    for v in me.vertices:
        if gl[v.index]: v.co += v.normal * (.0007 if not ot[v.index] else .00035)
    for p in me.polygons: p.use_smooth = True
    return o

def forearm_shell(arm, name):
    """bracer and sleeve over the cut forearm: follows the posed forearm axis back from the wrist"""
    wr = arm.pj(1); el = arm.pj(0); wd = nrm(el - wr)
    V = arm.posed(); m = arm.dominant == 0
    rel = V[m] - wr; along = rel @ wd; radial = np.linalg.norm(rel - np.outer(along, wd), axis=1)
    r_cut = np.percentile(radial[(along > .03) & (along < .075)], 95) if ((along > .03) & (along < .075)).any() else .03
    side = nrm(np.cross(wd, [0, 1, 0])); up = nrm(np.cross(side, wd))
    verts = []; faces = []; tags = []; segs = 24
    prof = [(0.040, r_cut + .002, 'glove'), (0.052, r_cut + .004, 'glove'), (0.056, r_cut + .007, 'bracer'), (0.19, r_cut + .012, 'bracer'),
            (0.20, r_cut + .016, 'sleeve'), (0.56, r_cut + .024, 'sleeve')]
    rings = []
    for d, r, t in prof:
        c = wr + wd * d; base = len(verts)
        for j in range(segs):
            a = 2 * math.pi * j / segs; verts.append(c + side * math.cos(a) * r * 1.08 + up * math.sin(a) * r * .95); tags.append(t)
        rings.append(base)
    for a0, a1 in zip(rings, rings[1:]):
        for j in range(segs): faces.append((a0 + j, a0 + (j + 1) % segs, a1 + (j + 1) % segs, a1 + j))
    faces.append(tuple(rings[-1] + j for j in range(segs)))
    o = mk_obj(name, verts, faces)
    for mname in ORDER: o.data.materials.append(MATS[mname])
    tm = {'glove': 1, 'bracer': 2, 'sleeve': 3}
    for p in o.data.polygons: p.material_index = tm[tags[p.vertices[0]]]; p.use_smooth = True
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(o.data); bm.free()
    m2 = o.modifiers.new('sub', 'SUBSURF'); m2.levels = 1; bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_apply(modifier='sub')
    # glow strip on the bracer (existing HUD motif)
    c = wr + wd * .085 + up * (r_cut + .0075)
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1)
    M = Matrix([[*(U2B(side) * .008), 0], [*(U2B(wd) * .02), 0], [*(U2B(up) * .003), 0], [0, 0, 0, 1]]).transposed(); M.translation = U2B(c)
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    me = bpy.data.meshes.new('glow_' + name); bm.to_mesh(me); bm.free()
    g = bpy.data.objects.new('glow_' + name, me); bpy.context.scene.collection.objects.link(g)
    for mname in ORDER: g.data.materials.append(MATS[mname])
    for p in g.data.polygons: p.material_index = 5
    return [o, g]

# ---------------------------------------------------------------- bake: tangent normal (leather grain) + AO
def bake(objs):
    os.makedirs(TEXDIR, exist_ok=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 48; sc.cycles.device = 'CPU'
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=.003, area_weight=0.0, scale_to_bounds=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    img_n = bpy.data.images.new('FPHands_v5_normal', TEXRES, TEXRES, alpha=False); img_n.colorspace_settings.name = 'Non-Color'
    img_ao = bpy.data.images.new('FPHands_v5_ao', TEXRES, TEXRES, alpha=False); img_ao.colorspace_settings.name = 'Non-Color'
    bm_ = bpy.data.materials.new('bake'); bm_.use_nodes = True; nt = bm_.node_tree
    bsdf = nt.nodes['Principled BSDF']; tc = nt.nodes.new('ShaderNodeTexCoord')
    noise = nt.nodes.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 900.0; noise.inputs['Detail'].default_value = 6.0; noise.inputs['Roughness'].default_value = .62
    vor = nt.nodes.new('ShaderNodeTexVoronoi'); vor.inputs['Scale'].default_value = 420.0
    mix = nt.nodes.new('ShaderNodeMath'); mix.operation = 'MULTIPLY_ADD'; mix.inputs[1].default_value = .6
    nt.links.new(tc.outputs['Object'], noise.inputs['Vector']); nt.links.new(tc.outputs['Object'], vor.inputs['Vector'])
    nt.links.new(noise.outputs['Fac'], mix.inputs[0]); nt.links.new(vor.outputs['Distance'], mix.inputs[2])
    bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .35; bump.inputs['Distance'].default_value = .0004
    nt.links.new(mix.outputs[0], bump.inputs['Height']); nt.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    tex = nt.nodes.new('ShaderNodeTexImage'); nt.nodes.active = tex
    saved = {o.name: [s.material for s in o.material_slots] for o in objs}
    for o in objs:
        for s in o.material_slots: s.material = bm_
    sc.render.bake.margin = 8
    tex.image = img_n; sc.render.bake.normal_space = 'TANGENT'; bpy.ops.object.bake(type='NORMAL')
    tex.image = img_ao; bpy.ops.object.bake(type='AO')
    for o in objs:
        for s, m in zip(o.material_slots, saved[o.name]): s.material = m
    px = np.empty(TEXRES * TEXRES * 4, np.float32); img_ao.pixels.foreach_get(px); ao = px.reshape(-1, 4)[:, 0]
    for img, nm in ((img_n, 'normal'), (img_ao, 'ao')):
        img.filepath_raw = os.path.join(TEXDIR, 'FPHands_v5_%s.png' % nm); img.file_format = 'PNG'; img.save()
    for mname in ('FPHandsGlove', 'FPHandsSkin', 'FPHandsNail'):
        g = MATS[mname]; gn = g.node_tree; gb = gn.nodes['Principled BSDF']
        t_n = gn.nodes.new('ShaderNodeTexImage'); t_n.image = img_n
        nm_ = gn.nodes.new('ShaderNodeNormalMap'); gn.links.new(t_n.outputs['Color'], nm_.inputs['Color']); gn.links.new(nm_.outputs['Normal'], gb.inputs['Normal'])
        t_a = gn.nodes.new('ShaderNodeTexImage'); t_a.image = img_ao
        mul = gn.nodes.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1
        mul.inputs['A'].default_value = gb.inputs['Base Color'].default_value[:]
        gn.links.new(t_a.outputs['Color'], mul.inputs['B']); gn.links.new(mul.outputs['Result'], gb.inputs['Base Color'])
    return {'tex_dir': TEXDIR, 'res': TEXRES, 'ao_mean': round(float(ao.mean()), 3), 'ao_p05': round(float(np.percentile(ao, 5)), 3)}

# ---------------------------------------------------------------- checks on the final (subdivided) meshes
def bvh_of(o):
    bm = bmesh.new(); bm.from_mesh(o.data); bm.transform(o.matrix_world)
    t = BVHTree.FromBMesh(bm); bm.free(); return t
RAYS = [Vector(d).normalized() for d in ((0.0123, 0.0071, 1), (1, .013, .021), (-.02, 1, .031), (.6, -.7, -.3), (-.5, -.2, .8))]
def inside(pb, p):
    votes = 0
    for d in RAYS:
        hits = 0; q = p.copy()
        for _ in range(30):
            hit = pb.ray_cast(q, d)
            if hit[0] is None: break
            hits += 1; q = hit[0] + d * 1e-5
        votes += hits % 2
    return votes >= 4

def checks(hands, arms, pistol):
    res = dict(LOG); pb = bvh_of(pistol)
    for a in arms:
        Vp = a.posed(); ins = np.array([occ_inside(PBVH, p) for p in Vp])
        cnt = {}
        for b in a.dominant[ins]: cnt[a.names[b]] = cnt.get(a.names[b], 0) + 1
        res['cage_inside_pistol_by_bone_' + a.s] = cnt
    res['scale_from_makehuman'] = {a.s: round(a.scale, 4) for a in arms}
    tips = {}
    for a in arms:
        for f in FINGERS:
            t = a.pj(a.idx(f + '_03'), 'tail'); h = pb.find_nearest(U2B(t))
            tips[a.s + '_' + f] = round(h[3] * 1000, 1)
    res['fingertip_joint_to_pistol_mm'] = tips
    for h, o in hands.items():
        res['tris_' + h] = sum(len(p.vertices) - 2 for p in o.data.polygons)
        ins = [v.co for v in o.data.vertices if occ_inside(PBVH, (v.co.x, v.co.z, v.co.y))]
        res['verts_inside_pistol_' + h] = len(ins)
        res['verts_inside_pistol_deeper_1mm_' + h] = len([p for p in ins if pb.find_nearest(p)[3] > .001])
    bl = {h: bvh_of(o) for h, o in hands.items()}
    for a, b in (('r', 'l'), ('l', 'r')):
        ins = [v.co for v in hands[a].data.vertices if inside(bl[b], v.co)]
        res['verts_' + a + '_inside_' + b] = len(ins)
        res['verts_' + a + '_inside_' + b + '_deeper_1mm'] = len([p for p in ins if bl[b].find_nearest(p)[3] > .001])
    # self-intersection between fingers of the same hand (finger-dominated vertices inside another finger's tube)
    return res

def main():
    global NAILS
    bpy.ops.wm.read_factory_settings(use_empty=True)
    NAILS = nail_verts()
    mat('FPHandsSkin', (.60, .43, .35), .55)
    mat('FPHandsGlove', (.40, .33, .25), .62)
    mat('FPHandsBracer', (.27, .27, .19), .48, .15)
    mat('FPHandsSleeve', (.14, .145, .14), .85)
    mat('FPHandsNail', (.72, .58, .52), .35)
    mat('FPHandsGlow', (.05, .25, .30), .4, 0, (.25, .85, 1.0))
    R = Arm('r'); L = Arm('l')
    LOG['sign_pistol'] = calib_sign(PBVH, PV)
    LOG['pistol_occ_voxels_1mm'] = build_occ(PBVH, PV)
    pose_right(R)
    rmesh = R.posed(); rbv = BVHTree.FromPolygons([Vector(v) for v in rmesh], R.faces)
    LOG['sign_rhand'] = calib_sign(rbv, rmesh)
    pose_left(L, [PBVH, rbv])
    hands = {'r': hand_object(R), 'l': hand_object(L)}
    extra = forearm_shell(R, 'shell_r') + forearm_shell(L, 'shell_l')
    pistol = mk_obj('pistol_ref', [np.array(v) for v in PV], [tuple(f) for f in PF])
    res = checks(hands, [R, L], pistol)
    if TEXRES > 0: res['bake'] = bake(list(hands.values()) + [o for o in extra if o.name.startswith('shell_')])
    res['total_tris'] = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in list(hands.values()) + extra)
    print('CHECKS', json.dumps(res))
    json.dump(res, open(os.path.join(os.path.dirname(OUT), 'build_checks_v5.json'), 'w'), indent=1)
    if RENDER:
        sys.path.insert(0, FP)
        import render_views_v4 as rv
        info = dict(INFO); info['hip_extra'] = []
        rv.run(hands, extra, pistol, RENDER, info)
    pistol.select_set(False); bpy.data.objects.remove(pistol)
    bpy.ops.object.select_all(action='DESELECT')
    for o in bpy.context.scene.objects: o.select_set(o.type == 'MESH')
    bpy.context.view_layer.objects.active = hands['r']
    bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active; o.name = 'PlayerFPHands_v5'; o.data.name = 'PlayerFPHands_v5'
    o.data.transform(Matrix.Rotation(math.pi, 4, 'Z'))
    bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True, export_materials='EXPORT', export_normals=True,
                              export_tangents=True, export_texcoords=True, export_apply=True)
    bpy.ops.wm.save_as_mainfile(filepath=OUT.replace('.glb', '.blend'))
    print('EXPORTED', OUT, res['total_tris'])

if __name__ == '__main__':
    main()
