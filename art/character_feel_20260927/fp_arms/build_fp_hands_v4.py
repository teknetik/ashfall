# Blender 5.2 headless: first-person two-hand cup grip v4 (PlayerFPHands_v4), 27 Sep 2026 evening, request #6 rework.
# Review round 1 (t_6c931016 comment #903) rejected v3: straight splayed fingers with tips in open air below the guard,
# a boxy firing palm, detached skin-capsule fingertips with ring seams, a flat glove material and a hidden hip grip.
# v4 changes (same construction principle, authored in the view-model pistol's own frame, Unity axes, metres):
#  - fingers are swept along the grip's OWN measured contour and are clipped by arc length where a real finger ends:
#    firing middle/ring/little wrap from the right panel round the frontstrap and stop on the front-left corner;
#    support fingers sit in the grooves between the firing fingers (interleaved levels, tighter offset) and wrap
#    left -> front -> right, stopping on the right side of the firing fingers.
#  - joint bulges, creases and dorsal knuckles per finger; fingertips are continuous full-finger glove leather (no
#    separate skin capsules, no ring seams).
#  - palms/backs of hands are unions of small spheres following the grip curvature plus metacarpal ridges, instead of
#    convex hulls; thinner thumbs and a smaller thenar mass.
#  - baked tangent-space normal map (leather grain) and AO (pistol, other hand and self occlusion) at 2k, exported as
#    PNG for the Unity glove material, so finger separation survives dusk lighting.
# Usage: blender -b -P build_fp_hands_v4.py -- <out.glb> [render_dir|-] [hipOffset x,y,z] [hipEuler x,y,z]
import bpy, bmesh, sys, math, json, os
import numpy as np
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

FP = '/home/teknetik/code/.snap/ao2-t_6c931016/art/character_feel_20260927/fp_arms/'
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else FP + 'PlayerFPHands_v4.glb'
RENDER = argv[1] if len(argv) > 1 and argv[1] != '-' else None
HIP_OFF = [float(x) for x in argv[2].split(',')] if len(argv) > 2 else None
HIP_EUL = [float(x) for x in argv[3].split(',')] if len(argv) > 3 else None
TEXDIR = os.path.join(os.path.dirname(OUT), 'PlayerFPHands_v4_tex')
TEXRES = int(os.environ.get('FP_TEXRES', '2048'))
VOXEL = float(os.environ.get('FP_VOXEL', '0.0008'))

def U2B(v): return Vector((v[0], v[2], v[1]))
def nrm(v): v = np.asarray(v, float); return v / np.linalg.norm(v)

# ---------------------------------------------------------------- pistol
def load_pistol():
    V = []; F = []; cur = None; start = {}
    for l in open(FP + 'pistol_frame.obj'):
        if l[0] == 'o': cur = l.split()[1]; start[cur] = len(V)
        elif l[0] == 'v': V.append([float(x) for x in l.split()[1:]])
        elif l[0] == 'f' and cur.startswith('pistol'): F.append([int(x) - 1 for x in l.split()[1:]])
    n = start['oldarms_char1']
    return np.array(V[:n]), F
PV, PF = load_pistol()
INFO = json.load(open(FP + 'pistol_frame.json'))

# grip frame: axis tilts ~20 deg forward (measured from the front- and backstrap), fingers wrap perpendicular to it
A = nrm((0, 1, .37)); E1 = np.array([1., 0, 0]); E2 = nrm((0, -A[2], A[1]))
O = np.array([.001, -.055, -.007])

def hull2(pts):
    pts = sorted(set(map(tuple, np.round(pts, 6))))
    if len(pts) < 3: return np.array(pts)
    def cross(o, a, b): return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
    lo = []; up = []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0: up.pop()
        up.append(p)
    return np.array(lo[:-1] + up[:-1])

ZFRONT = float(os.environ.get('FP_ZFRONT', '0.026'))   # frontstrap (Unity z ~ .025); anything ahead is guard/trigger
def grip_section(t, band=.004, front=.042):
    c = O + t * A
    d = PV - c
    m = (np.abs(d @ A) < band) & (PV[:, 2] < ZFRONT)
    uv = np.stack([d[m] @ E1, d[m] @ E2], 1)
    uv = uv[(uv[:, 1] < front) & (np.abs(uv[:, 0]) < .04)]
    return c, hull2(uv)

class Contour:
    """Offset of the grip section at level t: closed CCW loop, arc length s from the backstrap centre (u=0, v<0)
    going right (+u), front (+v), left, back."""
    def __init__(self, t, off):
        self.c, h = grip_section(t)
        ang = np.linspace(0, 2 * np.pi, 32, endpoint=False)
        circ = np.stack([np.cos(ang), np.sin(ang)], 1) * off
        h = hull2((h[:, None, :] + circ[None]).reshape(-1, 2))
        loop = np.vstack([h, h[:1]]); seg = np.linalg.norm(np.diff(loop, axis=0), axis=1)
        cum = np.concatenate([[0], np.cumsum(seg)]); L = cum[-1]
        ss = np.linspace(0, L, 720, endpoint=False)
        pts = np.stack([np.interp(ss, cum, loop[:, 0]), np.interp(ss, cum, loop[:, 1])], 1)
        i0 = np.argmin(np.where(pts[:, 1] < 0, np.abs(pts[:, 0]), 9))
        pts = np.roll(pts, -i0, 0)
        if pts[5, 0] < pts[0, 0]: pts = np.roll(pts[::-1], 1, 0)
        self.p2 = pts; self.L = L; self.ds = L / len(pts)
        self.vmin = pts[:, 1].min(); self.vmax = pts[:, 1].max()
    def uv(self, s):
        i = (s / self.ds) % len(self.p2); i0 = int(i); f = i - i0; i1 = (i0 + 1) % len(self.p2)
        return self.p2[i0] * (1 - f) + self.p2[i1] * f
    def at(self, s):
        uv = self.uv(s); return self.c + uv[0] * E1 + uv[1] * E2
    def normal(self, s):
        t = self.at(s + .002) - self.at(s - .002)
        return -nrm(np.cross(A, t))
    def s_where(self, pred, s_from, dirn, s_max):
        for d in np.arange(0, s_max, .0005):
            s = s_from + dirn * d; u, v = self.uv(s)
            if pred(u, v): return s
        return s_from + dirn * s_max

# ---------------------------------------------------------------- primitives
PARTS = []   # (name, hand, verts, faces, tags)
def tube(points, radii, tags, hand, name, segs=18, flat=None):
    P = np.asarray(points, float); n = len(P)
    R = np.asarray(radii, float)
    if R.ndim == 1: R = np.stack([R, R], 1)
    T = np.gradient(P, axis=0); T = T / np.linalg.norm(T, axis=1)[:, None]
    ref = np.asarray(flat if flat is not None else ([0, 1, 0] if abs(T[0][1]) < .9 else [1, 0, 0]), float)
    N = []; b = nrm(ref - T[0] * (ref @ T[0]))
    for i in range(n):
        if i: b = nrm(b - T[i] * (b @ T[i]))
        N.append(b)
    N = np.array(N); B = np.cross(T, N)
    verts = []; vt = []; faces = []
    ang = np.linspace(0, 2 * np.pi, segs, endpoint=False)
    def ring(c, nn, bb, r1, r2, tag):
        base = len(verts)
        for a in ang: verts.append(c + nn * math.cos(a) * r2 + bb * math.sin(a) * r1); vt.append(tag)
        return base
    rings = []; capn = 6
    for k in range(capn, 0, -1):
        a = k / capn * math.pi / 2
        rings.append(ring(P[0] - T[0] * math.sin(a) * R[0].mean(), N[0], B[0], R[0][0] * math.cos(a) + 1e-4, R[0][1] * math.cos(a) + 1e-4, tags[0]))
    for i in range(n): rings.append(ring(P[i], N[i], B[i], R[i][0], R[i][1], tags[i]))
    for k in range(1, capn + 1):
        a = k / capn * math.pi / 2
        rings.append(ring(P[-1] + T[-1] * math.sin(a) * R[-1].mean(), N[-1], B[-1], R[-1][0] * math.cos(a) + 1e-4, R[-1][1] * math.cos(a) + 1e-4, tags[-1]))
    for a0, a1 in zip(rings, rings[1:]):
        for j in range(segs): faces.append((a0 + j, a0 + (j + 1) % segs, a1 + (j + 1) % segs, a1 + j))
    faces.append(tuple(rings[0] + j for j in range(segs))[::-1]); faces.append(tuple(rings[-1] + j for j in range(segs)))
    PARTS.append((name, hand, verts, faces, vt))

def spheres(centres, radii, tag, hand, name):
    """union of separate closed UV spheres (fused by the voxel remesh): organic masses rather than convex hulls"""
    verts = []; faces = []; tags = []
    nu, nv = 14, 8
    for c, r in zip(centres, radii):
        base = len(verts); c = np.asarray(c, float)
        verts.append(c + np.array([0, r, 0])); tags.append(tag)
        for i in range(1, nv):
            th = math.pi * i / nv
            for j in range(nu):
                ph = 2 * math.pi * j / nu
                verts.append(c + r * np.array([math.sin(th) * math.cos(ph), math.cos(th), math.sin(th) * math.sin(ph)])); tags.append(tag)
        verts.append(c - np.array([0, r, 0])); tags.append(tag)
        top = base; bot = len(verts) - 1
        for j in range(nu): faces.append((top, base + 1 + (j + 1) % nu, base + 1 + j))
        for i in range(nv - 2):
            r0 = base + 1 + i * nu; r1 = r0 + nu
            for j in range(nu): faces.append((r0 + j, r0 + (j + 1) % nu, r1 + (j + 1) % nu, r1 + j))
        rl = base + 1 + (nv - 2) * nu
        for j in range(nu): faces.append((rl + j, rl + (j + 1) % nu, bot))
    PARTS.append((name, hand, verts, [f[::-1] for f in faces], tags))

def capsule(a, b, ra, rb, hand, name, tag='glove', n=10):
    a = np.asarray(a, float); b = np.asarray(b, float)
    pts = [a + (b - a) * f for f in np.linspace(0, 1, n)]
    tube(pts, np.linspace(ra, rb, n), [tag] * n, hand, name, segs=16)

CENTRELINES = {'R': [], 'L': []}   # (points, radii, name) per finger/thumb: clearance checks and palm push-out

def finger(C, s0, length, r0, r1, dirn, hand, name, step=.0012):
    n = max(12, int(length / step))
    ss = s0 + dirn * np.linspace(0, length, n)
    pts = np.array([C.at(s) for s in ss])
    f = np.linspace(0, 1, n)
    r = r0 + (r1 - r0) * f
    for k in (.44, .72):   # PIP and DIP: bulge at the joint, crease just past it
        r = r * (1 + .075 * np.exp(-((f - k) / .035) ** 2) - .05 * np.exp(-((f - k - .07) / .03) ** 2))
    r[-5:] *= np.linspace(1, .9, 5)
    tube(pts, r, ['glove'] * n, hand, name, flat=A)
    c0 = C.at(s0); o0 = C.normal(s0); d0 = nrm(C.at(s0 + dirn * .004) - c0)
    spheres([c0 + o0 * r0 * .35 - d0 * .004], [r0 * 1.0], 'glove', hand, name + '_mcp')
    for k in (.44, .72):
        i = int(k * (n - 1)); out = C.normal(ss[i])
        spheres([pts[i] + out * r[i] * .42], [r[i] * .62], 'glove', hand, name + '_kn%d' % int(k * 100))
    CENTRELINES[hand].append((pts, r, name))
    return pts, r, ss

def path_finger(ctrl, radii_ctrl, hand, name, step=.0012, knuckle_out=None):
    ctrl = np.asarray(ctrl, float)
    segs = np.linalg.norm(np.diff(ctrl, axis=0), axis=1); L = segs.sum()
    n = max(12, int(L / step))
    cum = np.concatenate([[0], np.cumsum(segs)]) / L
    f = np.linspace(0, 1, n); pts = []
    for x in f:
        i = min(np.searchsorted(cum, x, side='right') - 1, len(ctrl) - 2)
        u = (x - cum[i]) / (cum[i + 1] - cum[i])
        p0 = ctrl[max(i - 1, 0)]; p1 = ctrl[i]; p2 = ctrl[i + 1]; p3 = ctrl[min(i + 2, len(ctrl) - 1)]
        pts.append(.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3))
    pts = np.array(pts)
    r = np.interp(f, np.linspace(0, 1, len(radii_ctrl)), radii_ctrl)
    for k in (.5, .78): r = r * (1 + .06 * np.exp(-((f - k) / .035) ** 2) - .04 * np.exp(-((f - k - .07) / .03) ** 2))
    r[-5:] *= np.linspace(1, .9, 5)
    tube(pts, r, ['glove'] * n, hand, name)
    if knuckle_out is not None:
        out = nrm(knuckle_out)
        for k in (.5, .78):
            i = int(k * (n - 1)); spheres([pts[i] + out * r[i] * .42], [r[i] * .6], 'glove', hand, name + '_kn%d' % int(k * 100))
    CENTRELINES[hand].append((pts, r, name))
    return pts, r

# ---------------------------------------------------------------- layout
FIRE_R = [.0090, .0086, .0074]       # middle, ring, little: proximal radius (gloved adult hand, ~18.5 cm long)
FIRE_TIP = [.0071, .0068, .0059]
FIRE_LEN = [.088, .083, .066]        # MCP to tip
SUP_R = [.0086, .0089, .0085, .0072] # index, middle, ring, little
SUP_TIP = [.0069, .0072, .0069, .0059]
SUP_LEN = [.080, .088, .083, .066]
GAP = .0026
SUP_NEST = float(os.environ.get('FP_SUP_NEST', '1.62'))   # support finger offset = SUP_NEST * firing radius + gap

def level_for_front_y(y_target, off):
    best = None
    for t in np.linspace(-.02, .06, 81):
        if len(grip_section(t)[1]) < 3: continue
        C = Contour(t, off)
        fp = max((C.at(s) for s in np.linspace(0, C.L, 90)), key=lambda p: (p - C.c) @ E2)
        if best is None or abs(fp[1] - y_target) < abs(best[1] - y_target): best = (t, fp[1])
    return best[0]

LAYOUT = {}
def build():
    # ---------------- firing (right) hand: middle finger tucked up under the trigger guard (guard bottom y -0.019)
    t_mid = level_for_front_y(-.019 - FIRE_R[0] - .004, FIRE_R[0] + .0006)
    spacing = [0, FIRE_R[0] + FIRE_R[1] + GAP, FIRE_R[0] + 2 * FIRE_R[1] + FIRE_R[2] + 2 * GAP]
    fire_levels = [t_mid - d for d in spacing]
    fire = []
    for i, (t, r0, r1, L) in enumerate(zip(fire_levels, FIRE_R, FIRE_TIP, FIRE_LEN)):
        C = Contour(t, r0 + .0006)
        # MCP on the right panel, ~40% of the way from the back to the front (the knuckle line of a high grip)
        s_front = C.s_where(lambda u, v: v > C.vmax - .004, .01, +1, C.L * .5)
        s0 = max(.012, s_front - .026 - .003 * i)
        # wrap the frontstrap; the tip ends on the left panel just behind the front-left corner, never beyond
        s_fl = C.s_where(lambda u, v: u < 0 and v < C.vmax - .006, s_front + .01, +1, C.L)
        Lc = min(L, s_fl + .010 - s0)
        pts, r, ss = finger(C, s0, Lc, r0, r1, +1, 'R', 'R_' + ['middle', 'ring', 'little'][i])
        fire.append((C, s0, pts, Lc))
    LAYOUT['fire_len_mm'] = [round(float(x[3]) * 1000, 1) for x in fire]
    # ---------------- support (left) hand fingers: nested into the grooves between the firing fingers
    sup_levels = [fire_levels[0] + .5 * (FIRE_R[0] + SUP_R[0]) + .003]   # index high, pressed under the guard
    for i in range(1, 4): sup_levels.append(sup_levels[-1] - (SUP_R[i - 1] + SUP_R[i] + GAP * .6))
    sup = []
    for i, (t, r0, r1, L) in enumerate(zip(sup_levels, SUP_R, SUP_TIP, SUP_LEN)):
        C = Contour(t, SUP_NEST * max(FIRE_R) + GAP + r0 + .0006)
        # MCP on the left side behind the front-left corner; wrap clockwise (left -> front -> right)
        s_fl = C.s_where(lambda u, v: u < 0 and v > C.vmax - .004, C.L * .5, +1, C.L * .5)   # reaching the front going CCW
        s_fl_back = C.s_where(lambda u, v: v < C.vmax - .004, s_fl, +1, C.L * .5)              # leaving the front (left corner)
        s0 = s_fl_back + .016 + .002 * i
        s_fr = C.s_where(lambda u, v: u > 0 and v < C.vmax - .006, s0 - .02, -1, C.L)         # front-right corner going CW
        Lc = min(L, s0 - (s_fr - .012))
        pts, r, ss = finger(C, s0, Lc, r0, r1, -1, 'L', 'L_' + ['index', 'middle', 'ring', 'little'][i])
        sup.append((C, s0, pts, Lc))
    LAYOUT['sup_len_mm'] = [round(float(x[3]) * 1000, 1) for x in sup]
    # ---------------- trigger finger: along the right of the frame, into the guard, pad on the trigger face
    Cm, s_m = fire[0][0], fire[0][1]
    mcp_i = Cm.at(s_m) + A * (FIRE_R[0] + .0086 + GAP) + np.array([.002, 0, -.002])
    trig = [mcp_i, np.array([.0312, .0030, .030]), np.array([.0294, .0012, .051]), np.array([.0182, -.0006, .0705]),
            np.array([.0060, -.0016, .0760]), np.array([-.0040, -.0026, .0722])]
    path_finger(trig, [.0088, .0084, .0080, .0074, .0068, .0064], 'R', 'R_index', knuckle_out=(1, .35, 0))
    # ---------------- firing thumb: web low on the backstrap, forward along the left of the frame on the support thumb
    FT_Y, ST_Y = .0190, .0000
    fthumb = [np.array([.020, -.024, -.044]), np.array([.007, -.008, -.029]), np.array([-.011, .002, -.019]),
              np.array([-.0258, .0102, -.007]), np.array([-.0280, FT_Y, .012]), np.array([-.0272, FT_Y - .001, .033])]
    path_finger(fthumb, [.0122, .0110, .0100, .0090, .0083, .0075], 'R', 'R_thumb', knuckle_out=(-.5, 1, 0))
    spheres([np.array([.024, -.032, -.050]), np.array([.016, -.021, -.044]), np.array([.008, -.012, -.037]),
             np.array([.020, -.044, -.036]), np.array([.028, -.050, -.052])], [.0125, .0112, .0095, .0118, .0125], 'glove', 'R', 'R_thenar')
    # ---------------- firing palm on the right panel and backstrap: spheres riding the grip contour
    pc = []; pr = []
    for t in np.linspace(fire_levels[2] - .008, fire_levels[0] + .024, 8):
        C = Contour(t, .0098)
        s_front = C.s_where(lambda u, v: v > C.vmax - .004, .01, +1, C.L * .5)
        for s in np.arange(-.014, s_front - .030, .0045):
            pc.append(C.at(s)); pr.append(.0098)
    spheres(pc, pr, 'glove', 'R', 'R_palm')
    carpus_R = np.array([.036, -.040, -.046])
    mcps = [mcp_i + np.array([.003, 0, -.002])] + [x[0].at(x[1]) + x[0].normal(x[1]) * .002 for x in fire]
    for k, m in enumerate(mcps):
        capsule(carpus_R + np.array([0, .006 - .006 * k, 0]), m, .0100, .0088, 'R', 'R_meta%d' % k)
    # ---------------- support thumb: forward along the frame under the firing thumb
    sthumb = [np.array([-.046, -.040, -.036]), np.array([-.044, -.024, -.018]), np.array([-.0375, -.010, .001]),
              np.array([-.0292, ST_Y, .022]), np.array([-.0284, ST_Y, .045]), np.array([-.0280, ST_Y, .060])]
    path_finger(sthumb, [.0126, .0112, .0100, .0090, .0084, .0076], 'L', 'L_thumb', knuckle_out=(-1, .5, 0))
    spheres([np.array([-.046, -.046, -.040]), np.array([-.040, -.031, -.025])], [.0128, .0108], 'glove', 'L', 'L_thenar')
    # ---------------- support palm: heel on the free left grip panel, pushed out clear of the firing fingers
    fire_pts = np.vstack([p for p, r, nm in CENTRELINES['R']]); fire_rad = np.concatenate([r for p, r, nm in CENTRELINES['R']])
    sc = []; sr = []
    for t in np.linspace(sup_levels[3] - .004, sup_levels[0] + .002, 7):
        C = Contour(t, .0102)
        s_fl = C.s_where(lambda u, v: u < 0 and v > C.vmax - .004, C.L * .5, +1, C.L * .5)
        s_fl_back = C.s_where(lambda u, v: v < C.vmax - .004, s_fl, +1, C.L * .5)
        s_back = C.s_where(lambda u, v: v < C.vmin + .010, s_fl_back, +1, C.L)
        for s in np.arange(s_fl_back - .002, s_back, .0045):
            p = C.at(s); nn = C.normal(s); rad = .0102
            for _ in range(40):
                d = np.linalg.norm(fire_pts - p, axis=1) - fire_rad
                if d.min() > rad + .0010: break
                p = p + nn * .0008
            sc.append(p); sr.append(rad)
    spheres(sc, sr, 'glove', 'L', 'L_palm')
    carpus_L = np.array([-.050, -.050, -.030])
    for k, (C, s0, pts, Lc) in enumerate(sup):
        capsule(carpus_L + np.array([0, .004 - .005 * k, 0]), C.at(s0) + C.normal(s0) * .002, .0096, .0084, 'L', 'L_meta%d' % k)
    # ---------------- wrists and forearms: glove cuff, olive bracer, dark sleeve
    def arm(wrist, elbow_dir, hand):
        wd = nrm(elbow_dir)
        pts = [wrist + wd * d for d in np.linspace(0, .56, 80)]
        rad = []; tags = []
        for d in np.linspace(0, .56, 80):
            if d < .035: rad.append((.0245 + d * .12, .0190 + d * .08)); tags.append('glove')
            elif d < .050: rad.append((.031, .026)); tags.append('glove')
            elif d < .205: rad.append((.036 + (d - .05) * .05, .032 + (d - .05) * .05)); tags.append('bracer')
            else: rad.append((.042, .040)); tags.append('sleeve')
        side_v = nrm(np.cross(wd, [0, 1, 0]))
        tube(pts, rad, tags, hand, hand + '_forearm', segs=24, flat=np.cross(side_v, wd))
        rims.append((wrist + wd * .050, wd, (.036, .032), .006, .0020, 2))
        rims.append((wrist + wd * .205, wd, (.0435, .0395), .007, .0020, 2))
        glow.append((wrist + wd * .065, wd, hand))
    arm(np.array([.030, -.052, -.072]), (.34, -.40, -.85), 'R')
    arm(np.array([-.046, -.064, -.050]), (-.40, -.40, -.82), 'L')
    tube([np.array([.031, -.052, -.072]), np.array([.035, -.045, -.056]), carpus_R], [(.023, .018), (.021, .017), (.016, .014)], ['glove'] * 3, 'R', 'R_wristlink', flat=(1, 0, 0))
    tube([np.array([-.046, -.064, -.050]), np.array([-.049, -.057, -.040]), carpus_L], [(.023, .018), (.020, .016), (.015, .013)], ['glove'] * 3, 'L', 'L_wristlink', flat=(1, 0, 0))

glow = []
rims = []

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
GLOVE_SRGB = (.46, .38, .29)
def assemble():
    mat('FPHandsSkin', (.63, .44, .37), .52)
    mat('FPHandsGlove', GLOVE_SRGB, .60)
    mat('FPHandsBracer', (.27, .27, .19), .48, .15)
    mat('FPHandsSleeve', (.14, .145, .14), .85)
    mat('FPHandsNail', (.70, .55, .50), .35)
    mat('FPHandsGlow', (.05, .25, .30), .4, 0, (.25, .85, 1.0))
    tagmat = {'skin': 0, 'glove': 1, 'bracer': 2, 'sleeve': 3}
    hands = {}
    for hand in 'RL':
        V = []; F = []; T = []
        for name, h, verts, faces, tags in PARTS:
            if h != hand: continue
            b = len(V); V += verts; T += tags; F += [tuple(i + b for i in f) for f in faces]
        o = mk_obj('hand_' + hand, V, F)
        m = o.modifiers.new('remesh', 'REMESH'); m.mode = 'VOXEL'; m.voxel_size = VOXEL; m.adaptivity = 0
        bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_apply(modifier='remesh')
        sm = o.modifiers.new('smooth', 'CORRECTIVE_SMOOTH'); sm.factor = .5; sm.iterations = 5; sm.smooth_type = 'SIMPLE'; sm.use_only_smooth = True
        bpy.ops.object.modifier_apply(modifier='smooth')
        kd = KDTree(len(V))
        for i, v in enumerate(V): kd.insert(U2B(v), i)
        kd.balance()
        for mname in ORDER: o.data.materials.append(MATS[mname])
        for p in o.data.polygons:
            _, i, _ = kd.find(p.center); p.material_index = tagmat[T[i]]
        hands[hand] = o
    for hand, o in hands.items():
        tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
        target = 14000 if hand == 'R' else 13000
        d = o.modifiers.new('dec', 'DECIMATE'); d.ratio = min(1, target / tris)
        bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_apply(modifier='dec')
        for p in o.data.polygons: p.use_smooth = True
    extra = []
    for c, wd, hand in glow:
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1)
        up = nrm(np.cross(np.cross(wd, [0, 1, 0]), wd)); up = up if up[1] > 0 else -up
        side = np.cross(up, wd); base = c + up * .0355
        M = Matrix([[*(U2B(side) * .008), 0], [*(U2B(wd) * .018), 0], [*(U2B(up) * .004), 0], [0, 0, 0, 1]]).transposed(); M.translation = U2B(base)
        bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
        me = bpy.data.meshes.new('glow'); bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new('glow', me); bpy.context.scene.collection.objects.link(o)
        for mname in ORDER: o.data.materials.append(MATS[mname])
        for p in o.data.polygons: p.material_index = 5
        extra.append(o)
    for c, ax, r, w, th, mi in rims:
        ax = nrm(ax); ref = np.array([0, 1., 0]) if abs(ax[1]) < .9 else np.array([1., 0, 0])
        u = nrm(np.cross(ax, ref)); v = np.cross(ax, u)
        ru, rv = r
        verts = []; faces = []; M = 24; K = 6
        for i in range(M):
            a = 2 * math.pi * i / M
            d = u * math.cos(a) * ru + v * math.sin(a) * rv; out = nrm(d)
            for j in range(K):
                b = 2 * math.pi * j / K
                verts.append(c + d + out * (math.cos(b) * th + th * .4) + ax * math.sin(b) * w * .5)
        for i in range(M):
            for j in range(K):
                a0 = i * K + j; a1 = i * K + (j + 1) % K; b0 = ((i + 1) % M) * K + j; b1 = ((i + 1) % M) * K + (j + 1) % K
                faces.append((a0, b0, b1, a1))
        o = mk_obj('rim', verts, faces)
        for mname in ORDER: o.data.materials.append(MATS[mname])
        for p in o.data.polygons: p.material_index = mi; p.use_smooth = True
        extra.append(o)
    return hands, extra

# ---------------------------------------------------------------- bake: tangent normal (leather grain) + AO
def bake(hands, pistol):
    os.makedirs(TEXDIR, exist_ok=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 32; sc.cycles.device = 'CPU'
    objs = list(hands.values())
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=.004, area_weight=0.0, scale_to_bounds=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    img_n = bpy.data.images.new('FPHands_v4_normal', TEXRES, TEXRES, alpha=False); img_n.colorspace_settings.name = 'Non-Color'
    img_ao = bpy.data.images.new('FPHands_v4_ao', TEXRES, TEXRES, alpha=False); img_ao.colorspace_settings.name = 'Non-Color'
    bm_ = bpy.data.materials.new('bake'); bm_.use_nodes = True; nt = bm_.node_tree
    bsdf = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    noise = nt.nodes.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 900.0; noise.inputs['Detail'].default_value = 6.0
    noise.inputs['Roughness'].default_value = .62
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
    tex.image = img_n; sc.render.bake.normal_space = 'TANGENT'
    bpy.ops.object.bake(type='NORMAL')
    tex.image = img_ao
    bpy.ops.object.bake(type='AO')
    for o in objs:
        for s, m in zip(o.material_slots, saved[o.name]): s.material = m
    px = np.empty(TEXRES * TEXRES * 4, np.float32); img_ao.pixels.foreach_get(px)
    ao = px.reshape(-1, 4)[:, 0]
    # base map: neutral white times a mild cavity term (half the AO), tinted by the material colour; no light baked in
    cav = 1 - .45 * (1 - np.clip(ao, 0, 1))
    img_b = bpy.data.images.new('FPHands_v4_base', TEXRES, TEXRES, alpha=False)
    img_b.pixels.foreach_set(np.stack([cav, cav, cav, np.ones_like(cav)], 1).astype(np.float32).ravel())
    for img, nm in ((img_n, 'normal'), (img_ao, 'ao'), (img_b, 'base')):
        img.filepath_raw = os.path.join(TEXDIR, 'FPHands_v4_%s.png' % nm); img.file_format = 'PNG'; img.save()
    g = MATS['FPHandsGlove']; gn = g.node_tree; gb = gn.nodes['Principled BSDF']
    t_b = gn.nodes.new('ShaderNodeTexImage'); t_b.image = img_b
    rgb = gn.nodes.new('ShaderNodeMix'); rgb.data_type = 'RGBA'; rgb.blend_type = 'MULTIPLY'; rgb.inputs['Factor'].default_value = 1
    rgb.inputs['A'].default_value = gb.inputs['Base Color'].default_value[:]
    gn.links.new(t_b.outputs['Color'], rgb.inputs['B']); gn.links.new(rgb.outputs['Result'], gb.inputs['Base Color'])
    t_n = gn.nodes.new('ShaderNodeTexImage'); t_n.image = img_n
    nm_ = gn.nodes.new('ShaderNodeNormalMap'); gn.links.new(t_n.outputs['Color'], nm_.inputs['Color']); gn.links.new(nm_.outputs['Normal'], gb.inputs['Normal'])
    return {'tex_dir': TEXDIR, 'res': TEXRES, 'ao_mean': round(float(ao.mean()), 3), 'ao_p05': round(float(np.percentile(ao, 5)), 3)}

# ---------------------------------------------------------------- checks
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

def checks(hands, pistol):
    res = dict(LAYOUT)
    pb = bvh_of(pistol)
    fire_pts = np.vstack([p for p, r, nm in CENTRELINES['R'] if nm in ('R_middle', 'R_ring', 'R_little')])
    fire_rad = np.concatenate([r for p, r, nm in CENTRELINES['R'] if nm in ('R_middle', 'R_ring', 'R_little')])
    tips = {}
    for h in 'RL':
        for pts, r, nm in CENTRELINES[h]:
            p = pts[-1]
            d_pistol = pb.find_nearest(U2B(p))[3] - r[-1]
            d_fire = (np.linalg.norm(fire_pts - p, axis=1) - fire_rad).min() - r[-1] if h == 'L' else None
            tips[nm] = {'gap_to_pistol_mm': round(d_pistol * 1000, 1), 'gap_to_firing_fingers_mm': None if d_fire is None else round(float(d_fire) * 1000, 1)}
    res['fingertips'] = tips
    # finger-finger clearance inside each hand and between hands (centreline tubes; negative = interpenetration)
    def min_clear(a, b):
        pa, ra, _ = a; pb_, rb, _ = b
        D = np.linalg.norm(pa[:, None] - pb_[None], axis=2) - ra[:, None] - rb[None]
        return round(float(D.min()) * 1000, 1)
    names = [(h, c) for h in 'RL' for c in CENTRELINES[h]]
    pair = {}
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            (ha, a), (hb, b) = names[i], names[j]
            if 'thumb' in a[2] or 'thumb' in b[2]: continue
            pair[a[2] + '|' + b[2]] = min_clear(a, b)
    res['finger_min_clearance_mm'] = pair
    res['finger_pairs_interpenetrating_gt1mm'] = [k for k, v in pair.items() if v < -1.0]
    for h, o in hands.items():
        res['tris_' + h] = sum(len(p.vertices) - 2 for p in o.data.polygons)
        ins = [v.co for v in o.data.vertices if inside(pb, v.co)]
        res['verts_inside_pistol_' + h] = len(ins)
        res['verts_inside_pistol_deeper_2mm_' + h] = len([p for p in ins if pb.find_nearest(p)[3] > .002])
    bl = {h: bvh_of(o) for h, o in hands.items()}
    for a, b in (('R', 'L'), ('L', 'R')):
        ins = [v.co for v in hands[a].data.vertices if inside(bl[b], v.co)]
        res['verts_' + a + '_inside_' + b] = len(ins)
        res['verts_' + a + '_inside_' + b + '_deeper_1p5mm'] = len([p for p in ins if bl[b].find_nearest(p)[3] > .0015])
    return res

def unity_euler_q(e):
    qx = Quaternion((1, 0, 0), math.radians(e[0])); qy = Quaternion((0, 1, 0), math.radians(e[1])); qz = Quaternion((0, 0, 1), math.radians(e[2]))
    return qy @ qx @ qz

def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    build()
    hands, extra = assemble()
    pistol = mk_obj('pistol_ref', [np.array(v) for v in PV], [tuple(f) for f in PF])
    res = checks(hands, pistol)
    if TEXRES > 0: res['bake'] = bake(hands, pistol)
    res['total_tris'] = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in list(hands.values()) + extra)
    print('CHECKS', json.dumps(res))
    json.dump(res, open(os.path.join(os.path.dirname(OUT), 'build_checks_v4.json'), 'w'), indent=1)
    if RENDER:
        sys.path.insert(0, FP)
        import render_views_v4 as rv
        info = dict(INFO)
        # FP_HIPS="name:ox,oy,oz:ex,ey,ez;..." candidate hip offsets/eulers (camera space, as FirstPersonViewModel)
        extra_h = []
        for spec in filter(None, os.environ.get('FP_HIPS', '').split(';')):
            nm, o_, e_ = spec.split(':')
            off = Vector([float(x) for x in o_.split(',')]); q = unity_euler_q([float(x) for x in e_.split(',')]); qi = q.inverted()
            p = -(qi @ off)
            extra_h.append((nm, '%f,%f,%f' % tuple(p), '%f,%f,%f,%f' % (qi.x, qi.y, qi.z, qi.w)))
        info['hip_extra'] = extra_h
        if extra_h: print('HIPS', extra_h)
        rv.run(hands, extra, pistol, RENDER, info)
    pistol.select_set(False); bpy.data.objects.remove(pistol)
    bpy.ops.object.select_all(action='DESELECT')
    for o in bpy.context.scene.objects: o.select_set(o.type == 'MESH')
    bpy.context.view_layer.objects.active = hands['R']
    bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active; o.name = 'PlayerFPHands_v4'; o.data.name = 'PlayerFPHands_v4'
    o.data.transform(Matrix.Rotation(math.pi, 4, 'Z'))
    for p in o.data.polygons: p.use_smooth = True
    bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True, export_materials='EXPORT', export_normals=True,
                              export_tangents=True, export_texcoords=True, export_apply=True)
    bpy.ops.wm.save_as_mainfile(filepath=OUT.replace('.glb', '.blend'))
    print('EXPORTED', OUT, res['total_tris'])

if __name__ == '__main__':
    main()
