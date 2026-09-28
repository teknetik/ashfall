# Blender 5.2 headless: first-person two-hand cup grip (PlayerFPHands_v2), 27 Sep 2026 pm, request #6.
# The player skeleton has no finger bones, so the hands are a static mesh posed around the view-model pistol.
# Everything is authored in the view-model pistol's own frame, taken from Unity by FPGripPass.Dump()
# (pistol_frame.obj/json: Unity axes, metres; +X right, +Y up, +Z along the barrel).
# Construction: each finger/thumb is a tube swept along the pistol's measured grip contour (offset by its own radius,
# support fingers offset over the firing fingers), palms are hulls of spheres, forearms are tubes; each hand is
# voxel-remeshed into one surface (fingers stay separated by >= 2 mm creases), smoothed and decimated.
# Materials follow the colonist: black fingerless gloves, bare fingertips, olive forearm bracers over a dark sleeve.
# Usage: blender -b -P build_fp_hands_v2.py -- <out.glb> [render_dir]
import bpy, bmesh, sys, math, json
import numpy as np
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

FP = '/home/teknetik/code/.snap/ao2-t_6c931016/art/character_feel_20260927/fp_arms/'
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else FP + 'PlayerFPHands_v2.glb'
RENDER = argv[1] if len(argv) > 1 else None
VOXEL = 0.0011

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

def grip_section(t, band=.004, front=.042):
    c = O + t * A
    d = PV - c
    m = np.abs(d @ A) < band
    uv = np.stack([d[m] @ E1, d[m] @ E2], 1)
    uv = uv[(uv[:, 1] < front) & (np.abs(uv[:, 0]) < .04)]
    return c, hull2(uv)

class Contour:
    """Offset of the grip section at level t: closed CCW loop, arc length s from the backstrap centre (u=0, v<0)
    going right (+u), front (+v), left, back."""
    def __init__(self, t, off, lift=0.0):
        self.c, h = grip_section(t)
        self.c = self.c + lift * A
        ang = np.linspace(0, 2 * np.pi, 32, endpoint=False)
        circ = np.stack([np.cos(ang), np.sin(ang)], 1) * off
        h = hull2((h[:, None, :] + circ[None]).reshape(-1, 2))
        # resample densely
        loop = np.vstack([h, h[:1]]); seg = np.linalg.norm(np.diff(loop, axis=0), axis=1)
        cum = np.concatenate([[0], np.cumsum(seg)]); L = cum[-1]
        ss = np.linspace(0, L, 720, endpoint=False)
        pts = np.stack([np.interp(ss, cum, loop[:, 0]), np.interp(ss, cum, loop[:, 1])], 1)
        # start at backstrap centre, ensure CCW (right after back)
        i0 = np.argmin(np.where(pts[:, 1] < 0, np.abs(pts[:, 0]), 9))
        pts = np.roll(pts, -i0, 0)
        if pts[5, 0] < pts[0, 0]: pts = np.roll(pts[::-1], 1, 0)
        self.p2 = pts; self.L = L; self.ds = L / len(pts)
    def at(self, s):
        i = (s / self.ds) % len(self.p2); i0 = int(i); f = i - i0; i1 = (i0 + 1) % len(self.p2)
        uv = self.p2[i0] * (1 - f) + self.p2[i1] * f
        return self.c + uv[0] * E1 + uv[1] * E2
    def normal(self, s):
        t = self.at(s + .002) - self.at(s - .002)
        n = np.cross(A, t)  # CCW loop around +A: A x tangent points inward
        return -nrm(n)
    def s_of(self, u_sign=None, v_extreme=None):
        return None

# ---------------------------------------------------------------- tubes
PARTS = []   # (name, hand, verts(list of np3), faces, tags per vertex)
def tube(points, radii, tags, hand, name, segs=18, cap0=True, cap1=True, flat=None):
    """points: (n,3) centreline; radii: (n,) or (n,2) elliptic (r along side, r along 'flat' dir); tags: per point material tag."""
    P = np.asarray(points, float); n = len(P)
    R = np.asarray(radii, float)
    if R.ndim == 1: R = np.stack([R, R], 1)
    T = np.gradient(P, axis=0); T = T / np.linalg.norm(T, axis=1)[:, None]
    ref = np.asarray(flat if flat is not None else ([0, 1, 0] if abs(T[0][1]) < .9 else [1, 0, 0]), float)
    N = []; b = ref - T[0] * (ref @ T[0]); b = nrm(b)
    for i in range(n):
        if i: b = b - T[i] * (b @ T[i]); b = nrm(b)
        N.append(b)
    N = np.array(N); B = np.cross(T, N)
    verts = []; vt = []; faces = []
    ang = np.linspace(0, 2 * np.pi, segs, endpoint=False)
    def ring(c, t, nn, bb, r1, r2, tag):
        base = len(verts)
        for a in ang: verts.append(c + nn * math.cos(a) * r2 + bb * math.sin(a) * r1); vt.append(tag)
        return base
    rings = []
    capn = 5
    if cap0:
        for k in range(capn, 0, -1):
            a = k / capn * math.pi / 2
            rings.append(ring(P[0] - T[0] * math.sin(a) * R[0].mean(), T[0], N[0], B[0], R[0][0] * math.cos(a) + 1e-4, R[0][1] * math.cos(a) + 1e-4, tags[0]))
    for i in range(n): rings.append(ring(P[i], T[i], N[i], B[i], R[i][0], R[i][1], tags[i]))
    if cap1:
        for k in range(1, capn + 1):
            a = k / capn * math.pi / 2
            rings.append(ring(P[-1] + T[-1] * math.sin(a) * R[-1].mean(), T[-1], N[-1], B[-1], R[-1][0] * math.cos(a) + 1e-4, R[-1][1] * math.cos(a) + 1e-4, tags[-1]))
    for a0, a1 in zip(rings, rings[1:]):
        for j in range(segs):
            faces.append((a0 + j, a0 + (j + 1) % segs, a1 + (j + 1) % segs, a1 + j))
    faces.append(tuple(rings[0] + j for j in range(segs))[::-1]); faces.append(tuple(rings[-1] + j for j in range(segs)))
    PARTS.append((name, hand, verts, faces, vt))

def sphere_hull(centres, radii, tag, hand, name):
    pts = []
    for c, r in zip(centres, radii):
        for i in range(8):
            th = math.pi * (i + .5) / 8
            for j in range(14):
                ph = 2 * math.pi * j / 14
                pts.append(np.asarray(c) + r * np.array([math.sin(th) * math.cos(ph), math.cos(th), math.sin(th) * math.sin(ph)]))
    bm = bmesh.new()
    for p in pts: bm.verts.new(U2B(p))
    bmesh.ops.convex_hull(bm, input=bm.verts)
    for v in [v for v in bm.verts if not v.link_faces]: bm.verts.remove(v)
    verts = [np.array((v.co.x, v.co.z, v.co.y)) for v in bm.verts]
    idx = {v: i for i, v in enumerate(bm.verts)}
    faces = [tuple(idx[v] for v in f.verts)[::-1] for f in bm.faces]  # mk_obj flips back
    bm.free()
    PARTS.append((name, hand, verts, faces, [tag] * len(verts)))

def finger_on_contour(C, s0, length, r0, r1, dirn, hand, name, skin_from=.68, knuckles=(.47, .77), step=.0015):
    """Finger along contour C from arc s0 for `length`, dirn=+1 (CCW) or -1. Radius tapers r0->r1 with joint bulges."""
    n = max(8, int(length / step))
    ss = s0 + dirn * np.linspace(0, length, n)
    pts = np.array([C.at(s) for s in ss])
    f = np.linspace(0, 1, n)
    r = r0 + (r1 - r0) * f
    for k in knuckles: r = r * (1 + .07 * np.exp(-((f - k) / .045) ** 2))
    r[-6:] *= np.linspace(1, .92, 6)          # fingertip pad narrows a little
    tags = ['skin' if x >= skin_from else 'glove' for x in f]
    tube(pts, r, tags, hand, name, flat=A)
    k = int(np.argmax(f >= skin_from)); rims.append((pts[k], pts[min(k + 1, n - 1)] - pts[max(k - 1, 0)], r[k], .0032, .0011, 1))
    # MCP knuckle bump on the back of the hand
    c0 = C.at(s0); o0 = C.normal(s0); d0 = nrm(C.at(s0 + dirn * .004) - c0)
    sphere_hull([c0 + o0 * r0 * .30 - d0 * .003], [r0 * 1.02], 'glove', hand, name + '_knuckle')
    # nail on the dorsal (outward) side near the tip
    s_n = ss[int(n * .9)]; c = C.at(s_n); out = C.normal(s_n)
    nails.append((c + out * r1 * .78, out, np.array(C.at(ss[-1])) - np.array(C.at(ss[-4])), r1 * .72, hand))
    return pts, r

def path_tube(ctrl, radii_ctrl, tags_frac, hand, name, skin_from=.68, step=.0015, flat=None, nail_out=None):
    """Smooth path through control points (Catmull-Rom), radius interpolated."""
    ctrl = np.asarray(ctrl, float)
    segs = np.linalg.norm(np.diff(ctrl, axis=0), axis=1); L = segs.sum()
    n = max(8, int(L / step))
    cum = np.concatenate([[0], np.cumsum(segs)]) / L
    f = np.linspace(0, 1, n)
    # catmull-rom
    pts = []
    for x in f:
        i = min(np.searchsorted(cum, x, side='right') - 1, len(ctrl) - 2)
        u = (x - cum[i]) / (cum[i + 1] - cum[i])
        p0 = ctrl[max(i - 1, 0)]; p1 = ctrl[i]; p2 = ctrl[i + 1]; p3 = ctrl[min(i + 2, len(ctrl) - 1)]
        pts.append(.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3))
    r = np.interp(f, np.linspace(0, 1, len(radii_ctrl)), radii_ctrl)
    for k in (.45, .75): r = r * (1 + .06 * np.exp(-((f - k) / .045) ** 2))
    tags = ['skin' if x >= skin_from else 'glove' for x in f] if tags_frac is None else tags_frac(f)
    tube(np.array(pts), r, tags, hand, name, flat=flat)
    if tags_frac is None:
        P_ = np.array(pts); k = int(np.argmax(f >= skin_from)); rims.append((P_[k], P_[min(k + 1, n - 1)] - P_[max(k - 1, 0)], r[k], .0032, .0011, 1))
    if nail_out is not None:
        p = np.array(pts); i = int(n * .9)
        nails.append((p[i] + nrm(nail_out) * r[i] * .8, nrm(nail_out), p[-1] - p[-4], r[-1] * .72, hand))
    return np.array(pts), r

nails = []
rims = []   # (centre, axis, radius, width, thickness, material index)

# ---------------------------------------------------------------- layout
FIRE_R = [.0098, .0093, .0080]      # middle, ring, little proximal radius
FIRE_TIP = [.0080, .0076, .0066]
FIRE_LEN = [.089, .084, .068]        # MCP to tip along the grip (adult ~18.5 cm hand)
SUP_R = [.0093, .0096, .0091, .0078] # index, middle, ring, little
SUP_TIP = [.0074, .0078, .0074, .0064]
SUP_LEN = [.080, .089, .084, .068]
GAP = .0024

def level_for_front_y(y_target, off):
    best = None
    for t in np.linspace(-.02, .06, 81):
        if len(grip_section(t)[1]) < 3: continue
        C = Contour(t, off)
        # front-most point of the contour
        fp = max((C.at(s) for s in np.linspace(0, C.L, 90)), key=lambda p: (p - C.c) @ E2)
        if best is None or abs(fp[1] - y_target) < abs(best[1] - y_target): best = (t, fp[1])
    return best[0]

def build():
    # firing (right) hand: middle finger tucked under the trigger guard (guard bottom y -0.019)
    t_mid = level_for_front_y(-.019 - FIRE_R[0] - .0065, FIRE_R[0] + .0006)
    spacing = [0, FIRE_R[0] + FIRE_R[1] + GAP, FIRE_R[0] + 2 * FIRE_R[1] + FIRE_R[2] + 2 * GAP]
    fire_levels = [t_mid - d for d in spacing]
    knuckle_s = [.083, .081, .076]
    fire = []
    for i, (t, r0, r1, L, s0) in enumerate(zip(fire_levels, FIRE_R, FIRE_TIP, FIRE_LEN, knuckle_s)):
        C = Contour(t, r0 + .0006)
        pts, r = finger_on_contour(C, s0, L, r0, r1, +1, 'R', 'R_' + ['middle', 'ring', 'little'][i])
        fire.append((C, s0, pts))
    # support (left) hand fingers: over the firing fingers, index pressed up under the guard
    sup_off = 2 * max(FIRE_R) + GAP
    sup_levels = [t_mid + .006]
    for i in range(1, 4): sup_levels.append(sup_levels[-1] - (SUP_R[i - 1] + SUP_R[i] + GAP))
    sup_mcp_s = []
    for i, (t, r0, r1, L) in enumerate(zip(sup_levels, SUP_R, SUP_TIP, SUP_LEN)):
        C = Contour(t, sup_off + r0 + .0006)
        # MCP on the left side, a little behind the front-left corner; wrap CW (left -> front -> right)
        s0 = C.L * (.735 + .012 * i)
        finger_on_contour(C, s0, L, r0, r1, -1, 'L', 'L_' + ['index', 'middle', 'ring', 'little'][i])
        sup_mcp_s.append((C, s0))
    # trigger finger (firing index): along the right side of the frame, into the guard, pad on the trigger face
    Cm = fire[0][0]
    mcp_i = Cm.at(.079) + A * (FIRE_R[0] + .0092 + GAP) + np.array([.002, 0, 0])
    trig = [
        mcp_i,
        np.array([.0318, .0035, .030]),
        np.array([.0300, .0015, .052]),   # PIP beside the frame above the guard
        np.array([.0185, -.0005, .0715]),
        np.array([.0060, -.0015, .0765]),  # DIP inside the guard
        np.array([-.0045, -.0025, .0725]),  # pad on the trigger face
    ]
    path_tube(trig, [.0095, .0090, .0086, .0080, .0074, .0070], None, 'R', 'R_index', skin_from=.70, nail_out=(0, .3, 1))
    # firing thumb: from the web over the backstrap, forward along the left of the frame, riding on the support thumb
    fthumb = [np.array([.026, -.018, -.058]), np.array([.004, .004, -.052]), np.array([-.020, .017, -.034]),
              np.array([-.0345, .0270, -.006]), np.array([-.0365, .0305, .022]), np.array([-.0360, .0310, .040])]
    path_tube(fthumb, [.0150, .0135, .0118, .0106, .0098, .0090], None, 'R', 'R_thumb', skin_from=.80, nail_out=(-.5, 1, 0))
    # support thumb: below it, pointing forward along the frame above the grip panel
    sthumb = [np.array([-.050, -.040, -.040]), np.array([-.050, -.018, -.022]), np.array([-.044, .004, .000]),
              np.array([-.0355, .0110, .028]), np.array([-.0325, .0120, .055]), np.array([-.0315, .0115, .071])]
    path_tube(sthumb, [.0160, .0140, .0118, .0104, .0096, .0088], None, 'L', 'L_thumb', skin_from=.80, nail_out=(-1, .6, 0))
    # firing palm: two sphere hulls (right panel + backstrap/web) sitting on the grip contour
    Cs = [Contour(t, .0125) for t in (fire_levels[2] - .010, fire_levels[1], fire_levels[0] + .018, fire_levels[0] + .034)]
    right_panel = []; back = []
    for k, C in enumerate(Cs):
        for s in np.linspace(.030, .080, 4): right_panel.append(C.at(s) + C.normal(s) * .0015)
        for s in np.linspace(-.012, .034, 4): back.append(C.at(s) + C.normal(s) * .0015)
    sphere_hull(right_panel, [.0128] * len(right_panel), 'glove', 'R', 'R_palm')
    sphere_hull(back, [.0128] * len(back), 'glove', 'R', 'R_heel')
    # support palm: heel on the free left grip panel, front edge stepped out over the firing fingertips
    sp = []; rr = []
    fire_tip_off = 2 * max(FIRE_R) + GAP
    for t in (sup_levels[3] - .004, sup_levels[1], sup_levels[0] + .010):
        Cg = Contour(t, .0125)
        for f in np.linspace(.56, .84, 6):
            s = Cg.L * f
            # over the firing fingertips at the front-left, directly on the grip panel behind them
            lift = fire_tip_off * float(np.clip((.80 - f) / .06, 0, 1))
            sp.append(Cg.at(s) + Cg.normal(s) * lift); rr.append(.0128)
    for (C, s0) in sup_mcp_s:
        sp.append(C.at(s0) - C.normal(s0) * .001); rr.append(.0105)
    sphere_hull(sp, rr, 'glove', 'L', 'L_palm')
    # wrists, forearms and sleeves (straight wrists, elbows out of frame at hip and ADS)
    def arm(wrist, elbow_dir, hand, side):
        wd = nrm(elbow_dir)
        pts = [wrist + wd * d for d in np.linspace(0, .56, 80)]
        rad = []; tags = []
        for d in np.linspace(0, .56, 80):
            if d < .035: rad.append((.0265 + d * .12, .0205 + d * .08)); tags.append('glove')
            elif d < .050: rad.append((.034, .029)); tags.append('glove')      # glove cuff
            elif d < .215: rad.append((.040 + (d - .05) * .05, .036 + (d - .05) * .05)); tags.append('bracer')
            else: rad.append((.047, .045)); tags.append('sleeve')
        side_v = nrm(np.cross(wd, [0, 1, 0]))
        tube(pts, rad, tags, hand, hand + '_forearm', segs=24, flat=np.cross(side_v, wd))
        rims.append((wrist + wd * .050, wd, (.040, .036), .006, .0022, 2))                      # bracer lip at the wrist
        rims.append((wrist + wd * .215, wd, (.0483, .0443), .007, .0022, 2))                    # bracer lip at the elbow side
        # cyan status strip on the bracer (like the colonist's), a small emissive tab on the top of the wrist
        glow.append((wrist + wd * .065, wd, hand))
    arm(np.array([.022, -.050, -.070]), (.34, -.40, -.85), 'R', 1)
    arm(np.array([-.040, -.066, -.055]), (-.40, -.40, -.82), 'L', -1)
    # join wrist to palm: short tubes from wrist centre into the palm hulls
    tube([np.array([.024, -.050, -.070]), np.array([.036, -.042, -.038]), np.array([.041, -.036, -.008])], [(.027, .021), (.026, .019), (.020, .016)], ['glove'] * 3, 'R', 'R_wristlink', flat=(1, 0, 0))
    tube([np.array([-.040, -.066, -.055]), np.array([-.047, -.054, -.028]), np.array([-.050, -.044, -.002])], [(.027, .021), (.024, .018), (.018, .015)], ['glove'] * 3, 'L', 'L_wristlink', flat=(1, 0, 0))

glow = []

# ---------------------------------------------------------------- mesh assembly
def mk_obj(name, verts, faces):
    me = bpy.data.meshes.new(name)
    me.from_pydata([U2B(v) for v in verts], [], [f[::-1] for f in faces])  # U2B mirrors: flip winding
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

def assemble():
    # sRGB albedo sampled from the colonist texture (fingertip skin, glove, bracer, under-sleeve); no lighting baked in
    mat('FPHandsSkin', (.63, .44, .37), .52)
    mat('FPHandsGlove', (.26, .255, .235), .58)
    mat('FPHandsBracer', (.27, .27, .19), .48, .15)
    mat('FPHandsSleeve', (.14, .145, .14), .85)
    mat('FPHandsNail', (.70, .55, .50), .35)
    mat('FPHandsGlow', (.05, .25, .30), .4, 0, (.25, .85, 1.0))
    order = ['FPHandsSkin', 'FPHandsGlove', 'FPHandsBracer', 'FPHandsSleeve', 'FPHandsNail', 'FPHandsGlow']
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
        sm = o.modifiers.new('smooth', 'CORRECTIVE_SMOOTH'); sm.factor = .5; sm.iterations = 6; sm.smooth_type = 'SIMPLE'; sm.use_only_smooth = True
        bpy.ops.object.modifier_apply(modifier='smooth')
        # material by nearest source vertex tag
        kd = KDTree(len(V))
        for i, v in enumerate(V): kd.insert(U2B(v), i)
        kd.balance()
        for mname in order: o.data.materials.append(MATS[mname])
        for p in o.data.polygons:
            _, i, _ = kd.find(p.center); p.material_index = tagmat[T[i]]
        d = o.modifiers.new('dec', 'DECIMATE'); d.ratio = 1.0; d.use_symmetry = False
        hands[hand] = o
    # decimate to budget
    for hand, o in hands.items():
        tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
        target = 11000 if hand == 'R' else 10000
        o.modifiers['dec'].ratio = min(1, target / tris)
        bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_apply(modifier='dec')
        for p in o.data.polygons: p.use_smooth = True
    # nails and glow tabs (separate small pieces, not remeshed)
    extra = []
    for c, out, along, r, hand in nails:
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=1)
        out = nrm(out); al = nrm(np.asarray(along) - out * (np.asarray(along) @ out)); side = np.cross(out, al)
        M = Matrix([[*(U2B(side) * r * .78), 0], [*(U2B(al) * r * 1.0), 0], [*(U2B(out) * r * .22), 0], [0, 0, 0, 1]]).transposed()
        M.translation = U2B(c)
        bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
        me = bpy.data.meshes.new('nail'); bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new('nail', me); bpy.context.scene.collection.objects.link(o)
        for mname in order: o.data.materials.append(MATS[mname])
        for p in o.data.polygons: p.material_index = 4; p.use_smooth = True
        extra.append(o)
    for c, wd, hand in glow:
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1)
        up = nrm(np.cross(np.cross(wd, [0, 1, 0]), wd)); up = up if up[1] > 0 else -up
        side = np.cross(up, wd)
        base = c + up * .0395
        M = Matrix([[*(U2B(side) * .008), 0], [*(U2B(wd) * .018), 0], [*(U2B(up) * .004), 0], [0, 0, 0, 1]]).transposed(); M.translation = U2B(base)
        bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
        me = bpy.data.meshes.new('glow'); bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new('glow', me); bpy.context.scene.collection.objects.link(o)
        for mname in order: o.data.materials.append(MATS[mname])
        for p in o.data.polygons: p.material_index = 5
        extra.append(o)
    for c, ax, r, w, th, mi in rims:
        ax = nrm(ax); ref = np.array([0, 1., 0]) if abs(ax[1]) < .9 else np.array([1., 0, 0])
        u = nrm(np.cross(ax, ref)); v = np.cross(ax, u)
        # elliptic sections for the forearm: u is sideways, v is up
        ru, rv = (r, r) if np.isscalar(r) or np.ndim(r) == 0 else r
        verts = []; faces = []; M = 20; K = 6
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
        for mname in order: o.data.materials.append(MATS[mname])
        for p in o.data.polygons: p.material_index = mi; p.use_smooth = True
        extra.append(o)
    return hands, extra

# ---------------------------------------------------------------- checks
def bvh_of(o):
    bm = bmesh.new(); bm.from_mesh(o.data); bm.transform(o.matrix_world)
    t = BVHTree.FromBMesh(bm); bm.free(); return t

RAYS = [Vector(d).normalized() for d in ((0.0123, 0.0071, 1), (1, .013, .021), (-.02, 1, .031), (.6, -.7, -.3), (-.5, -.2, .8))]
def inside(pb, p):
    # majority vote of ray parity: the Meshy pistol is not watertight
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
    res = {}
    pb = bvh_of(pistol)
    for name, h, verts, faces, tags in PARTS:
        bad = [v for v in verts if inside(pb, U2B(v)) and pb.find_nearest(U2B(v))[3] > .0015]
        if bad: res['part_inside_' + name] = [len(bad), [round(float(x), 4) for x in np.mean(bad, 0)]]
    for h, o in hands.items():
        res['tris_' + h] = sum(len(p.vertices) - 2 for p in o.data.polygons)
        res['hand_' + h + '_x_pistol_face_pairs'] = len(bvh_of(o).overlap(pb))
    res['R_x_L_face_pairs'] = len(bvh_of(hands['R']).overlap(bvh_of(hands['L'])))
    # vertices of the final hands that are inside the pistol (ray parity against the pistol mesh)
    for h, o in hands.items():
        ins = [v.co for v in o.data.vertices if inside(pb, v.co)]
        res['verts_inside_pistol_' + h] = len(ins)
        deep = [p for p in ins if pb.find_nearest(p)[3] > .002]
        res['verts_inside_pistol_deeper_2mm_' + h] = len(deep)
        # coarse clusters (Unity frame, 2 cm cells) for diagnosis
        cl = {}
        for p in deep: k = tuple(int(math.floor(c / .02)) for c in (p.x, p.z, p.y)); cl[k] = cl.get(k, 0) + 1
        res['deep_cells_' + h] = {str([round(c * .02 + .01, 2) for c in k]): n for k, n in cl.items()}
    # right/left hand mutual penetration: right-hand verts inside the left hand and vice versa
    bl = {h: bvh_of(o) for h, o in hands.items()}
    for a, b in (('R', 'L'), ('L', 'R')):
        ins = [v.co for v in hands[a].data.vertices if inside(bl[b], v.co)]
        deep = [p for p in ins if bl[b].find_nearest(p)[3] > .0015]
        res['verts_' + a + '_inside_' + b] = len(ins); res['verts_' + a + '_inside_' + b + '_deeper_1p5mm'] = len(deep)
        cl = {}
        for p in deep: k = tuple(int(math.floor(c / .02)) for c in (p.x, p.z, p.y)); cl[k] = cl.get(k, 0) + 1
        res['cells_' + a + '_in_' + b] = {str([round(c * .02 + .01, 2) for c in k]): n for k, n in cl.items()}
    return res

def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    build()
    hands, extra = assemble()
    pistol = mk_obj('pistol_ref', [np.array(v) for v in PV], [tuple(f) for f in PF])
    res = checks(hands, pistol)
    allv = [v for o in list(hands.values()) + extra for v in o.data.vertices]
    res['total_tris'] = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in list(hands.values()) + extra)
    # hand length check: firing hand wrist crease (glove cuff start) to middle fingertip is reported by the layout
    print('CHECKS', json.dumps(res))
    json.dump(res, open(FP + 'build_checks.json', 'w'), indent=1)
    if RENDER:
        import render_views
        render_views.run(hands, extra, pistol, RENDER, INFO)
    # export: join, rotate 180 deg about Blender Z so glTF->glTFast lands in Unity's pistol frame
    pistol.select_set(False); bpy.data.objects.remove(pistol)
    for o in bpy.context.scene.objects: o.select_set(o.type == 'MESH')
    bpy.context.view_layer.objects.active = hands['R']
    bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active; o.name = 'PlayerFPHands_v2'; o.data.name = 'PlayerFPHands_v2'
    o.data.transform(Matrix.Rotation(math.pi, 4, 'Z'))
    for p in o.data.polygons: p.use_smooth = True
    bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True, export_materials='EXPORT', export_normals=True, export_apply=True)
    bpy.ops.wm.save_as_mainfile(filepath=OUT.replace('.glb', '.blend'))
    print('EXPORTED', OUT, res['total_tris'])

if __name__ == '__main__':
    main()
