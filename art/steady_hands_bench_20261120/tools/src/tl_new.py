# tl_new.py: the eleven tools model-bench did not build (model-tools, 21 Nov 2026). Ids, tags and params are those of
# briefs/model-tools.md: strippers, wirebrush, pick, scribe (Field Toolkit, in the roll's pockets), file_flat,
# file_round, snips, drill (+ drill_bit), iron (+ iron_stand, solder_reel), applicator, thirdhand (Brann's).
# Each tool is modelled in its own frame (metres, along +Y with its working end at +Y, Z up), settled onto z = 0 the way
# it lies, its materials framed back to the modelling axes (tl_kit.frame_mats), then placed. See ../PARTS.md.
import math
import bpy
from mathutils import Vector, Matrix
import mbk
from mbk import G, MT, CT, AP, RG, MM, X, Y, Z, O, T, R4, put, W, Wd, bench_pose, join, turned, ring_prof, extrude_z
import tl_kit as K
import tl_mats2 as T2
from tl_kit import tool, sub, settle, sup, loft_path, sweep_round, baked, placed

FAM = 'tools'
HAND, ROLLSET, BENCH = 'a', 'r', 'b'          # texture sets: carried hand tools, the roll, things that stand on the bench


def recentre(objs, extra_M=None):
    """Shift the pieces so that the middle of their XY bounds is at the origin (z stays). Returns the 4x4."""
    lo = Vector((1e9, 1e9)); hi = Vector((-1e9, -1e9))
    for o in objs:
        for v in o.data.vertices:
            lo.x = min(lo.x, v.co.x); lo.y = min(lo.y, v.co.y); hi.x = max(hi.x, v.co.x); hi.y = max(hi.y, v.co.y)
    c = (lo + hi) / 2
    Mt = T((-c.x, -c.y, 0))
    for o in objs:
        o.data.transform(Mt); o.data.update()
    return Mt


def interp_path(path, y):
    """x of a polyline at y (it runs monotonically in y)."""
    for a, b in zip(path, path[1:]):
        if min(a[1], b[1]) <= y <= max(a[1], b[1]) and abs(b[1] - a[1]) > 1e-9:
            f = (y - a[1]) / (b[1] - a[1])
            return a[0] + (b[0] - a[0]) * f, f
    return path[-1][0], 1.0


def path_f(path, y):
    """Fraction along a polyline (by length) of its point at y."""
    L = [0.0]
    for a, b in zip(path, path[1:]):
        L.append(L[-1] + (Vector(b) - Vector(a)).length)
    for i, (a, b) in enumerate(zip(path, path[1:])):
        if min(a[1], b[1]) <= y <= max(a[1], b[1]) and abs(b[1] - a[1]) > 1e-9:
            f = (y - a[1]) / (b[1] - a[1])
            return (L[i] + (L[i + 1] - L[i]) * f) / L[-1]
    return 1.0


def sleeve_on(tag, path, from_y, hw, ht, t, mat):
    """A sleeve (cloth tape or dipped rubber) t thick over a handle path below y = from_y, closed over the butt."""
    P = [Vector(p) for p in path]
    xy = [(p.x, p.y) for p in P]
    x0, _ = interp_path(xy, from_y)
    f0 = path_f(xy, from_y)
    pts = [Vector((x0, from_y, P[0].z))] + [p for p in P if p.y < from_y - 0.0005]
    fs = [f0] + [path_f(xy, p.y) for p in pts[1:]]

    def sec(i, f):
        fh = fs[i]
        w = hw(fh) + 2 * t; h = ht(fh) + 2 * t
        if i == 0:
            w -= t * 0.8; h -= t * 0.8
        if fh > 0.965:
            k = (fh - 0.965) / 0.035
            e = math.sqrt(max(0.06, 1 - k * k * 0.9)); w *= e; h *= e
        return sup(w, h, 16, 2.6)
    return loft_path(tag, pts, sec, mat)


def scissor_pair(key, jaw_a, jaw_half, hp_a, hw, ht, th, rj, steel, jaw_mat, hp_b=None, rivet_d=0.0075, extra_a=(), extra_b=(), holes_a=(),
                 bolt=False, sleeve=None):
    """Two forged halves crossing at a lap joint (A keeps the lower half inside the joint disc, B the upper). B is the
    mirror of A unless hp_b (its own handle path) is given. extra_a / extra_b are joined to their half after the cut.
    Returns (a, b)."""
    hp_a = K.smooth_path([Vector((p[0], p[1], 0)) for p in hp_a], 2)
    bs, jw, hd = K.scissor_half(key + '_a', jaw_a, jaw_half, [(p.x, p.y) for p in hp_a], hw, ht, th, rj, steel, jaw_mat)
    if holes_a:
        hd = G.boolean(hd, [G.cyl('_hh', (x, y, -0.01), (x, y, 0.02), r, 14) for (x, y, r) in holes_a])
    jaw_b = [(-x, y) for (x, y) in jaw_a]
    if hp_b is None:
        hp_b = [Vector((-p.x, p.y, 0)) for p in hp_a]
    else:
        hp_b = K.smooth_path([Vector((p[0], p[1], 0)) for p in hp_b], 2)
    bs_b, jw_b, hd_b = K.scissor_half(key + '_b', jaw_b, lambda x, y: jaw_half(-x, y), [(p.x, p.y) for p in hp_b], hw, ht, th, rj, steel, jaw_mat)
    A = K.lap_cut([bs, jw, hd], th, rj, lower=True)
    B = K.lap_cut([bs_b, jw_b, hd_b], th, rj, lower=False, rivet_hole=rivet_d / 2 * 0.72 + 0.00018)
    if bolt:
        head = AP.nut(key + '_bh', 0.0020, 0.0105, 0.0032, steel, at=(0, 0, th + 0.0002))
        baked(head)
        dome = turned(key + '_bd', [(0, 0), (0, 0.0040), (0.0007, 0.0036), (0.0012, 0.0020), (0.0014, 0)], 16, steel, axis=Z, origin=(0, 0, th + 0.0034))
        pin = G.cyl(key + '_pin', (0, 0, 0.0002), (0, 0, th + 0.0003), rivet_d / 2 * 0.72, 14, steel)
        nut = AP.nut(key + '_bn', 0.0020, 0.0095, 0.0024, steel, at=(0, 0, -0.0024))
        baked(nut)
        top = [head, dome, pin, nut]
    else:
        rv = AP.rivet(key + '_rv', rivet_d, rivet_d * 0.22, steel, segs=16, at=(0, 0, th + 0.00025))
        baked(rv)
        pin = G.cyl(key + '_pin', (0, 0, 0.0002), (0, 0, th), rivet_d / 2 * 0.72, 14, steel)
        top = [rv, pin]
    sl_a, sl_b = [], []
    if sleeve:
        sy, st_, ma, mb = sleeve
        zc = th / 2
        sl_a = [sleeve_on(key + '_sla', [Vector((p.x, p.y, zc)) for p in hp_a], sy, hw, ht, st_, ma)]
        sl_b = [sleeve_on(key + '_slb', [Vector((p.x, p.y, zc)) for p in hp_b], sy, hw, ht, st_, mb)]
    a = join(key + '_a', A + top + list(extra_a) + sl_a)
    b = join(key + '_b', B + list(extra_b) + sl_b)
    if sleeve:
        for o in (a, b):
            o.data.transform(T((0, 0, sleeve[1])))
    for o in (a, b):
        G.shade(o, 38)
    return a, b


def finish_scissor(F, a, b, pid, label, open_deg, tip_p, grab_p, verbs, tags, steps, note0, parent, mass='light', mset=HAND):
    tool(a, pid, label, verbs, tags, parent=parent, steps=steps, mass=mass)
    sub(b, pid + '_b', label + ', second half', pid, 'steel', 'light')
    mbk.tip(a, tip_p, (0, 1, 0))
    mbk.grab(a, grab_p)
    R = F.new_rig(pid, a)
    R.hinge(pid + '_jaws', W(a, (0, 0, 0)), Wd(a, (0, 0, 1)), 0.0, -open_deg, [b])
    F.end_rig(R)
    F.param_notes['tools.%s_jaws' % pid] = {'note': note0}
    for o in (a, b):
        F.set_of[o.name] = mset
    return a


# ====================================================================== wire strippers (roll)
def build_strippers(F, M):
    th, rj = 0.0068, 0.0105
    st = T2.forged('t_strip_steel', oxide=0.5)
    jm = T2.forged('t_strip_jaw', base=(0.56, 0.55, 0.53), oxide=0.3, edge=1.0)
    x0 = -0.00008
    inner = [(x0, 0.0098)]
    for yc, r in ((0.0150, 0.00042), (0.0184, 0.00052), (0.0220, 0.00065), (0.0259, 0.00080), (0.0302, 0.00100)):
        inner.append((x0, yc - r))
        for k in range(1, 8):
            a_ = math.pi * k / 8
            inner.append((x0 - r * math.sin(a_), yc - r * math.cos(a_)))
        inner.append((x0, yc + r))
    inner.append((x0, 0.0350))
    jaw = inner + [(-0.0008, 0.0390), (-0.0020, 0.0406), (-0.0036, 0.0406), (-0.0052, 0.0390), (-0.0072, 0.0330), (-0.0094, 0.0240),
                   (-0.0108, 0.0160), (-0.0113, 0.0098)]
    hp = [(0.0048, -0.0050), (0.0068, -0.0100), (0.0098, -0.0200), (0.0126, -0.0380), (0.0142, -0.0600), (0.0150, -0.0840), (0.0147, -0.1030),
          (0.0140, -0.1120)]
    hw = lambda f: 0.0086 + 0.0020 * math.sin(math.pi * f)
    ht = lambda f: th * (0.97 - 0.10 * f)
    sp_hp = K.smooth_path([Vector((p[0], p[1], 0)) for p in hp], 2)
    hpx = [(p.x, p.y) for p in sp_hp]

    def inner_edge(y):
        x, _ = interp_path(hpx, y)
        return x - hw(path_f(hpx, y)) / 2

    # return spring between the handles below the joint (on A, clear of B by 0.5 mm)
    ys = -0.0175
    e = inner_edge(ys)
    spr = AP.spring('st_sp', 2 * e - 0.0012, 0.0042, 0.00065, 5, st, per_turn=10, wire_segs=5, closed_ends=False, at=(-e + 0.0019, ys, th / 2), axis=(1, 0, 0))
    baked(spr)
    # stop screw through A with a locknut and a knurled head, its point 0.8 mm short of B
    yk = -0.043
    ek = inner_edge(yk); xo = ek + hw(path_f(hpx, yk))
    shank = G.cyl('st_sc', (xo + 0.0022, yk, th / 2), (-ek + 0.0018, yk, th / 2), 0.0013, 12, jm, chamfer=0.0004)
    nut = AP.nut('st_nt', 0.0026, 0.0055, 0.0022, st, at=(xo, yk, th / 2), axis=(1, 0, 0)); baked(nut)
    head = AP.knurled_band('st_kh', 0.0080, 0.0042, n=22, depth=0.00035, mat=st, at=(xo + 0.0022, yk, th / 2), axis=(1, 0, 0)); baked(head)
    cap = turned('st_kc', [(0, 0), (0, 0.0036), (0.0006, 0.0030), (0.0008, 0)], 16, st, axis=X, origin=(xo + 0.0064, yk, th / 2))
    a, b = scissor_pair('strippers', jaw, lambda x, y: th / 2 * (1.0 - 0.38 * max(0.0, (y - 0.012) / 0.029)), hp, hw, ht, th, rj, st, jm,
                        rivet_d=0.0078, extra_a=[spr, shank, nut, head, cap], holes_a=[(0.0103, -0.0262, 0.0011), (0.0118, -0.0330, 0.0009)])
    return dict(root=a, b=b, y_tip=0.0403, y_butt=-0.112, thick=th, width=0.050)


def finish_strippers(F, M, d, Mw):
    a, b = d['root'], d['b']
    put(a, Mw); put(b, Mw)
    return finish_scissor(F, a, b, 'strippers', 'Wire strippers', 28.0, (0, 0.0395, 0.0034), (0, -0.075, 0.0034), ['window', 'seat'], ['tool:strippers'],
                          ['s3.strip', 's3.lead'], '0 = closed (as found), 1 = open 28 degrees', 'roll')


# ====================================================================== wire brush (roll, lies on its side)
def build_wirebrush(F, M):
    wd = T2.wood('t_brush_wood', base=(0.52, 0.40, 0.26), dark=(0.26, 0.17, 0.09), rough=0.6, polish=0.4)
    bw = T2.brass_wire('t_brush_wire')
    # modelled bristles down (-Z), head at +Y; turned onto its side at the end
    pts = [Vector((0, y, z)) for (y, z) in ((0.000, 0.0122), (0.010, 0.0128), (0.040, 0.0130), (0.075, 0.0124), (0.105, 0.0108), (0.128, 0.0082),
                                              (0.140, 0.0084), (0.150, 0.0080), (0.165, 0.0080), (0.185, 0.0080), (0.198, 0.0080), (0.2015, 0.0080))]
    pts = [p for p in K.smooth_path(pts, 2)]

    def sec(i, f):
        y = pts[i].y
        if y < 0.135:
            w, h = 0.0180 + 0.0016 * max(0.0, 1 - y / 0.03), 0.0106 + 0.0012 * max(0.0, 1 - y / 0.03)
        elif y < 0.145:
            k = (y - 0.135) / 0.01
            w, h = 0.0180 + (0.0172 - 0.0180) * k, 0.0106 + (0.0160 - 0.0106) * k
        else:
            w, h = 0.0172, 0.0160
        e = 1.0
        if y > 0.197:
            e = max(0.25, math.sqrt(max(0.0, 1 - ((y - 0.197) / 0.0045) ** 2)))
        if y < 0.004:
            e = max(0.3, math.sqrt(max(0.0, 1 - ((0.004 - y) / 0.0045) ** 2)))
        return sup(w * e, h * e, 16, 3.0 if y > 0.14 else 2.4)
    body = loft_path('wb', pts, sec, wd)
    body = G.boolean(body, [G.cyl('_bh', (0, 0.016, -0.01), (0, 0.016, 0.03), 0.0030, 16)])        # hanging hole
    tufts = []
    k = 0
    for row, x in enumerate((-0.0058, -0.0019, 0.0019, 0.0058)):
        for c in range(11):
            y = 0.1478 + c * 0.0047 + (0.0023 if row % 2 else 0.0)
            if y > 0.1978:
                continue
            ax = Vector((x * 9.0, (c - 5.0) * 0.010, -1.0))
            tufts.append(K.tuft('wb_t%d' % k, (x, y, 0.0004), ax, 0.0160, 0.00095, bw, splay=0.75, seed=k, segs=6, bend=0.05)); k += 1
    br = join('wb_bristles', tufts)
    pcs = [body, br]
    Ro = R4(Y, -90.0)                          # onto its side: bristles toward +X
    for o in pcs:
        o.data.transform(Ro)
    Mr = settle(pcs, about=0.10)
    K.frame_mats(pcs, Mr @ Ro)
    o = join('wirebrush', pcs)
    G.shade(o, 40)
    Mt = Mr @ Ro
    tipp = Mt @ Vector((0, 0.173, -0.0150)); tipd = (Mt.to_3x3() @ Vector((0, 0, -1))).normalized()
    return dict(root=o, y_tip=0.2015, tip=tipp, tip_dir=tipd, grab=Mt @ Vector((0, 0.06, 0.012)), thick=0.019, width=0.030)


def finish_wirebrush(F, M, d, Mw):
    o = d['root']
    put(o, Mw)
    tool(o, 'wirebrush', 'Wire brush', ['wipe'], ['tool:brush'], material='wood', parent='roll', steps=['s2.dust', 's3.brush', 's4.mould'])
    mbk.tip(o, d['tip'], d['tip_dir'])
    mbk.grab(o, d['grab'])
    F.set_of[o.name] = HAND
    return o


# ====================================================================== hooked pick (roll)
def build_pick(F, M):
    hm = T2.nickel('t_pick_body', base=(0.55, 0.54, 0.51), rough=0.36)
    T2.knurl_band(hm, (0, 0, 0), (0, 1, 0), -0.0700, -0.0130, n=44, pitch=0.00085)
    sm = T2.bright('t_pick_shaft', base=(0.60, 0.59, 0.57), rough=0.3)
    prof = [(-0.0795, 0), (-0.0795, 0.0024), (-0.0790, 0.0034), (-0.0780, 0.0040), (-0.0765, 0.0042), (-0.0745, 0.0042), (-0.0738, 0.0040),
            (-0.0730, 0.0043), (-0.0060, 0.0043), (-0.0048, 0.0040), (-0.0010, 0.0026), (0.0, 0.0022), (0.0030, 0.0021), (0.0040, 0)]
    h = turned('pk_h', prof, 22, hm, axis=Y)
    path = [Vector((0, 0.0010, 0)), Vector((0, 0.0250, 0)), Vector((0, 0.0500, 0)), Vector((0, 0.0620, 0)), Vector((0, 0.0665, 0)),
            Vector((0.0004, 0.0690, 0)), Vector((0.0014, 0.0703, 0)), Vector((0.0028, 0.0704, 0)), Vector((0.0038, 0.0694, 0)),
            Vector((0.0041, 0.0679, 0)), Vector((0.0039, 0.0664, 0)), Vector((0.0034, 0.0654, 0))]
    path = K.smooth_path(path, 2)
    sh = sweep_round('pk_s', path, lambda f: 0.00125 * (1.0 - 0.45 * f) if f < 0.78 else 0.00125 * 0.55 * max(0.18, 1 - (f - 0.78) / 0.24), 10, sm)
    pcs = [h, sh]
    Mr = settle(pcs)
    K.frame_mats(pcs, Mr)
    o = join('pick', pcs)
    G.shade(o, 40)
    return dict(root=o, y_tip=0.0704, tip=Mr @ Vector((0.0028, 0.0704, 0)), axis=(Mr.to_3x3() @ Y).normalized(), grab=Mr @ Vector((0, -0.040, 0)),
                thick=0.0086, width=0.0086)


def finish_pick(F, M, d, Mw):
    o = d['root']
    put(o, Mw)
    tool(o, 'pick', 'Hooked pick', ['point', 'window'], ['tool:pick'], parent='roll', steps=['s2.pry', 's3.pick'])
    mbk.tip(o, d['tip'], d['axis'])
    mbk.grab(o, d['grab'])
    F.set_of[o.name] = HAND
    F.uv_weights[o.name] = 1.3
    return o


# ====================================================================== scriber with a pocket clip (roll)
def build_scribe(F, M):
    bm = T2.nickel('t_scribe_body')
    T2.knurl_band(bm, (0, 0, 0), (0, 1, 0), -0.0420, 0.0180, n=46, pitch=0.0008)
    nm = T2.bright('t_scribe_needle', base=(0.66, 0.65, 0.63), rough=0.22)
    prof = [(-0.0620, 0), (-0.0620, 0.0020), (-0.0614, 0.0031), (-0.0600, 0.0037), (-0.0580, 0.0040), (-0.0560, 0.0046), (-0.0540, 0.0047),
            (0.0260, 0.0047), (0.0290, 0.0044), (0.0380, 0.0028), (0.0420, 0.0024), (0.0420, 0)]
    b = turned('sc_b', prof, 24, bm, axis=Y)
    ring = turned('sc_r', [(-0.0465, 0), (-0.0465, 0.0049), (-0.0450, 0.0050), (-0.0440, 0.0049), (-0.0440, 0)], 24, bm, axis=Y)
    nd = turned('sc_n', [(0.0410, 0), (0.0410, 0.00150), (0.0740, 0.00145), (0.0810, 0.0011), (0.0878, 0.00018), (0.0882, 0)], 14, nm, axis=Y)
    # pocket clip: a spring-steel strip from the ring along the top of the body, a ball at its free end
    cp = [Vector((0, -0.0455, 0.0050)), Vector((0, -0.0420, 0.0060)), Vector((0, -0.0300, 0.0059)), Vector((0, -0.0100, 0.0055)),
          Vector((0, 0.0060, 0.0052)), Vector((0, 0.0110, 0.0050))]
    clip = K.loft_path('sc_c', K.smooth_path(cp, 2), lambda i, f: sup(0.0042 * (1 - 0.25 * f), 0.0008, 8, 4.0), bm)
    ball = G.cyl('sc_cb', (0, 0.0098, 0.0047), (0, 0.0122, 0.0047), 0.0012, 10, bm, chamfer=0.0005)
    pcs = [b, ring, nd, clip, ball]
    Mr = settle(pcs)
    K.frame_mats(pcs, Mr)
    o = join('scribe', pcs)
    G.shade(o, 38)
    return dict(root=o, y_tip=0.0882, tip=Mr @ Vector((0, 0.0882, 0)), axis=(Mr.to_3x3() @ Y).normalized(), grab=Mr @ Vector((0, -0.020, 0)),
                thick=0.0106, width=0.0094)


def finish_scribe(F, M, d, Mw):
    o = d['root']
    put(o, Mw)
    tool(o, 'scribe', 'Scriber', ['path'], ['tool:scribe'], parent='roll', steps=['s3.scribe'])
    mbk.tip(o, d['tip'], d['axis'])
    mbk.grab(o, d['grab'])
    F.set_of[o.name] = HAND
    F.uv_weights[o.name] = 1.3
    return o


# ====================================================================== files (Brann's)
def file_handle(tag, y0, r_max, length, wm, bm):
    """Brass ferrule and a turned handle behind y0 (the blade's heel), toward -Y."""
    fer = ring_prof(tag + '_f', [(y0 - 0.0120, 0.0), (y0 - 0.0120, r_max * 0.66), (y0 - 0.0112, r_max * 0.70), (y0 - 0.0020, r_max * 0.70),
                                  (y0 + 0.0008, r_max * 0.62), (y0 + 0.0008, 0.0)], 24, bm, axis=Y)
    yb = y0 - 0.0115
    L = length
    prof = [(yb, r_max * 0.63), (yb - 0.004, r_max * 0.70), (yb - L * 0.25, r_max * 0.90), (yb - L * 0.50, r_max * 1.00), (yb - L * 0.72, r_max * 0.98),
            (yb - L * 0.88, r_max * 0.86), (yb - L * 0.96, r_max * 0.62), (yb - L, r_max * 0.15), (yb - L, 0.0)]
    hd = turned(tag + '_h', [(yb + 0.0004, 0.0)] + prof, 26, wm, axis=Y)
    T2.rings(wm, 1, [yb - L * 0.13, yb - L * 0.155])
    return fer, hd


def build_file_flat(F, M):
    fm = T2.file_steel('t_ffile')
    T2.file_teeth(fm, axes=(0, 1), lo=0.012, hi=0.250, along=1)
    wm = T2.wood('t_ffile_wood')
    bm = T2.brass('t_ffile_brass')
    ys = [0.0, 0.004, 0.012, 0.040, 0.100, 0.150, 0.190, 0.220, 0.240, 0.250]
    pts = [Vector((0, y, 0)) for y in ys]

    def sec(i, f):
        y = ys[i]
        if y < 0.012:
            k = y / 0.012
            w = 0.0105 + (0.0240 - 0.0105) * k; t = 0.0042 + (0.0064 - 0.0042) * k
        else:
            k = max(0.0, (y - 0.140) / 0.110)
            w = 0.0240 - 0.0085 * k ** 1.3; t = 0.0064 - 0.0022 * k
        return sup(w, t, 16, 7.0)
    bl = loft_path('ff_b', pts, sec, fm)
    G.bevel(bl, 0.0003, 1, 40)
    fer, hd = file_handle('ff', 0.0, 0.0150, 0.085, wm, bm)
    pcs = [bl, fer, hd]
    Mr = settle(pcs)
    Mt = recentre(pcs)
    K.frame_mats(pcs, Mt @ Mr)
    o = join('file_flat', pcs)
    G.shade(o, 40)
    Mf = Mt @ Mr
    return dict(root=o, tip=Mf @ Vector((0, 0.250, 0)), axis=(Mf.to_3x3() @ Y).normalized(), grab=Mf @ Vector((0, -0.055, 0)), face=Mf @ Vector((0, 0.150, 0.0032)))


def build_file_round(F, M):
    fm = T2.file_steel('t_rfile')
    T2.file_teeth(fm, axes=(1, 2), pitch=0.0007, angle1=70.0, angle2=-60.0, lo=0.010, hi=0.220, along=1, strength=1.3)
    wm = T2.wood('t_rfile_wood', base=(0.33, 0.20, 0.11))
    bm = T2.brass('t_rfile_brass')
    prof = [(-0.0005, 0.0), (-0.0005, 0.0030), (0.004, 0.0034), (0.010, 0.0040), (0.060, 0.0039), (0.120, 0.0032), (0.180, 0.0023), (0.215, 0.0016),
            (0.2195, 0.0010), (0.2200, 0.0)]
    bl = turned('fr_b', prof, 16, fm, axis=Y)
    fer, hd = file_handle('fr', 0.0, 0.0132, 0.078, wm, bm)
    pcs = [bl, fer, hd]
    Mr = settle(pcs)
    Mt = recentre(pcs)
    K.frame_mats(pcs, Mt @ Mr)
    o = join('file_round', pcs)
    G.shade(o, 40)
    Mf = Mt @ Mr
    return dict(root=o, tip=Mf @ Vector((0, 0.220, 0)), axis=(Mf.to_3x3() @ Y).normalized(), grab=Mf @ Vector((0, -0.050, 0)))


def finish_file(F, M, d, key, label, tags, steps):
    o = d['root']
    put(o, bench_pose('tools_' + key))
    tool(o, key, label, ['window', 'path'] if key == 'file_flat' else ['window'], tags, steps=steps)
    mbk.tip(o, d['tip'], d['axis'])
    mbk.grab(o, d['grab'])
    F.set_of[o.name] = HAND
    return o


# ====================================================================== tin snips (Brann's)
def build_snips(F, M):
    th, rj = 0.0080, 0.0125
    st = T2.forged('t_snips_steel', base=(0.47, 0.46, 0.44), oxide=0.6)
    bl = T2.forged('t_snips_blade', base=(0.55, 0.54, 0.52), oxide=0.35, edge=1.0)
    jaw = [(-0.00008, 0.0110), (-0.00008, 0.0700), (-0.0010, 0.0722), (-0.0030, 0.0716), (-0.0062, 0.0640), (-0.0098, 0.0500), (-0.0130, 0.0340),
           (-0.0150, 0.0200), (-0.0156, 0.0110)]
    hp_a = [(0.0030, -0.0030), (0.0085, -0.0140), (0.0125, -0.0350), (0.0148, -0.0700), (0.0158, -0.1100), (0.0160, -0.1450), (0.0154, -0.1700),
            (0.0146, -0.1780)]
    # B: the handle curls back into a closed finger loop at its end
    hp_b = [(-0.0030, -0.0030), (-0.0085, -0.0140), (-0.0125, -0.0350), (-0.0150, -0.0700), (-0.0164, -0.1050), (-0.0172, -0.1350),
            (-0.0176, -0.1460)]
    lp = [Vector((x, y, th / 2)) for (x, y) in ((-0.0175, -0.1400), (-0.0196, -0.1600), (-0.0255, -0.1750), (-0.0335, -0.1790), (-0.0398, -0.1715),
                                                (-0.0410, -0.1530), (-0.0377, -0.1300), (-0.0312, -0.1080), (-0.0248, -0.0925), (-0.0200, -0.0845))]
    loop = loft_path('sn_lp', K.smooth_path(lp, 2), lambda i, f: sup(0.0074, th * 0.86, 14, 3.2), st)
    hw = lambda f: 0.0098 - 0.0022 * f
    ht = lambda f: th * (0.98 - 0.12 * f)
    a, b = scissor_pair('snips', jaw, lambda x, y: th / 2 * (0.32 + 0.68 * min(1.0, abs(x) / 0.0156)) * (1.0 - 0.15 * max(0.0, (y - 0.02) / 0.05)),
                        hp_a, hw, ht, th, rj, st, bl, hp_b=hp_b, rivet_d=0.0090, bolt=True, extra_b=[loop])
    pcs = [a, b]
    Mr = settle(pcs, about=-0.05)
    Mt = recentre(pcs)
    Mf = Mt @ Mr
    K.frame_mats(pcs, Mf)
    return dict(root=a, b=b, Mf=Mf, tip=Mf @ Vector((0, 0.070, th / 2)), axis=(Mf.to_3x3() @ Y).normalized(), grab=Mf @ Vector((0, -0.110, th / 2)),
                pivot=Mf @ Vector((0, 0, 0)), pz=(Mf.to_3x3() @ Z).normalized())


def finish_snips(F, M, d):
    a, b = d['root'], d['b']
    Mw = bench_pose('tools_snips')
    put(a, Mw); put(b, Mw)
    tool(a, 'snips', 'Tin snips', ['path'], ['tool:snips'], steps=['s3.cut'])
    sub(b, 'snips_b', 'Tin snips, second half', 'snips', 'steel', 'light')
    mbk.tip(a, d['tip'], d['axis'])
    mbk.grab(a, d['grab'])
    R = F.new_rig('snips', a)
    R.hinge('snips_jaws', W(a, d['pivot']), Wd(a, d['pz']), 0.0, -22.0, [b])
    F.end_rig(R)
    F.param_notes['tools.snips_jaws'] = {'note': '0 = closed (as found), 1 = open 22 degrees'}
    for o in (a, b):
        F.set_of[o.name] = HAND
    return a


# ====================================================================== eggbeater hand drill (Brann's)
YW = -0.010          # wheel axle (y) ; the spindle runs along Y at x = z = 0
RW = 0.045           # wheel outside radius
ZW0, ZW1 = 0.0075, 0.0125


def build_drill(F, M):
    ci = T2.cast_iron('t_drill_iron')
    wd = T2.wood('t_drill_wood', base=(0.38, 0.23, 0.12))
    st = T2.bright('t_drill_steel', base=(0.55, 0.54, 0.52), rough=0.34)
    nk = T2.nickel('t_drill_chuck', base=(0.56, 0.55, 0.52))
    bs = T2.brass('t_drill_brass')
    # ---- back handle: a mushroom knob on a turned body, brass ferrule
    hp = [(-0.168, 0.0), (-0.1675, 0.0100), (-0.1645, 0.0182), (-0.1585, 0.0225), (-0.1515, 0.0222), (-0.1465, 0.0185), (-0.1440, 0.0110),
          (-0.1400, 0.0104), (-0.1350, 0.0124), (-0.1200, 0.0140), (-0.1040, 0.0137), (-0.0975, 0.0124), (-0.0945, 0.0108), (-0.0945, 0.0)]
    hdl = turned('dr_h', hp, 28, wd, axis=Y)
    T2.rings(wd, 1, [-0.1300, -0.1060])
    fer = ring_prof('dr_f', [(-0.0955, 0.0), (-0.0955, 0.0102), (-0.0945, 0.0108), (-0.0860, 0.0106), (-0.0850, 0.0096), (-0.0850, 0.0)], 24, bs, axis=Y)
    # ---- the frame: bearing bosses at both ends, two rails round the pinion, a bridge carrying the wheel's axle
    bb = turned('dr_bb', [(-0.0855, 0.0), (-0.0855, 0.0082), (-0.0840, 0.0090), (-0.0700, 0.0084), (-0.0680, 0.0070), (-0.0680, 0.0)], 22, ci, axis=Y)
    fb = turned('dr_fb', [(0.0425, 0.0), (0.0425, 0.0064), (0.0445, 0.0078), (0.0585, 0.0080), (0.0600, 0.0070), (0.0600, 0.0)], 22, ci, axis=Y)
    rails = []
    for sg in (1, -1):
        rp = [Vector((sg * 0.0040, -0.0720, 0)), Vector((sg * 0.0088, -0.0620, 0.0006)), Vector((sg * 0.0096, -0.0300, 0.0010)),
              Vector((sg * 0.0094, 0.0200, 0.0010)), Vector((sg * 0.0080, 0.0390, 0.0004)), Vector((sg * 0.0040, 0.0470, 0))]
        rails.append(sweep_round('dr_r', K.smooth_path(rp, 2), lambda f: 0.0032 - 0.0004 * math.sin(math.pi * f), 10, ci))
    bridge = G.cyl('dr_br', (-0.0100, YW, 0.0012), (0.0100, YW, 0.0012), 0.0034, 12, ci)
    boss = turned('dr_ab', [(0.0, 0.0), (0.0, 0.0058), (0.0050, 0.0058), (0.0062, 0.0050), (0.0062, 0.0)], 18, ci, axis=Z, origin=(0, YW, 0.0010))
    axle = G.cyl('dr_ax', (0, YW, 0.0070), (0, YW, 0.0172), 0.0026, 12, st)
    cap = turned('dr_ac', [(0.0, 0.0), (0.0, 0.0046), (0.0016, 0.0044), (0.0030, 0.0030), (0.0036, 0.0)], 14, st, axis=Z, origin=(0, YW, 0.0168))
    frame = [hdl, fer, bb, fb] + rails + [bridge, boss, axle, cap]
    # ---- the wheel: rim with face teeth below, five curved spokes, hub, crank arm, wooden knob
    wc = Vector((0, YW, 0))
    rim = ring_prof('dr_w', [(ZW0, 0.0390), (ZW0, 0.0444), (ZW0 + 0.0006, 0.0450), (ZW1 - 0.0006, 0.0450), (ZW1, 0.0444), (ZW1, 0.0390)], 64, ci,
                    axis=Z, origin=wc)
    teeth = K.bevel_gear('dr_wt', 0.0447, 0.0396, 60, 0.0, ci, face_up=False, tooth_h=0.0024)
    teeth.data.transform(T((0, YW, ZW0 + 0.00005)))
    spokes = []
    for k in range(5):
        a0 = 2 * math.pi * k / 5
        sp = []
        for j in range(7):
            f = j / 6
            r = 0.0085 + (0.0398 - 0.0085) * f
            a = a0 + 0.38 * math.sin(math.pi * f) * 0.8 + 0.25 * f
            sp.append(Vector((math.cos(a) * r, YW + math.sin(a) * r, (ZW0 + ZW1) / 2)))
        spokes.append(loft_path('dr_sp', sp, lambda i, f: sup(0.0042 - 0.0010 * f, 0.0040, 8, 3.0), ci, up=(0, 0, 1)))
    hub = ring_prof('dr_hb', [(0.0074, 0.0029), (0.0074, 0.0088), (0.0080, 0.0098), (0.0140, 0.0098), (0.0148, 0.0090), (0.0148, 0.0029)], 24, ci,
                    axis=Z, origin=wc)
    ac = math.radians(-28.0)
    cd = Vector((math.cos(ac), math.sin(ac), 0))
    arm_p = [wc + cd * r + Vector((0, 0, 0.0146)) for r in (0.0, 0.012, 0.026, 0.040, 0.052)]
    arm = loft_path('dr_ca', arm_p, lambda i, f: sup(0.0094 - 0.0030 * f, 0.0042, 12, 3.0), ci, up=(0, 0, 1))
    pe = wc + cd * 0.053
    eboss = turned('dr_ce', [(0.0, 0.0), (0.0, 0.0058), (0.0050, 0.0058), (0.0058, 0.0050), (0.0058, 0.0)], 18, ci, axis=Z, origin=(pe.x, pe.y, 0.0125))
    kp = [(0.0, 0.0), (0.0, 0.0034), (0.0040, 0.0034), (0.0052, 0.0062), (0.0120, 0.0078), (0.0230, 0.0102), (0.0290, 0.0098), (0.0330, 0.0078),
          (0.0352, 0.0045), (0.0358, 0.0)]
    knob = turned('dr_kn', kp, 22, wd, axis=Z, origin=(pe.x, pe.y, 0.0182))
    kcap = turned('dr_kc', [(0.0, 0.0), (0.0, 0.0030), (0.0007, 0.0026), (0.0011, 0.0)], 12, st, axis=Z, origin=(pe.x, pe.y, 0.0182 + 0.0357))
    wheel = [rim, teeth] + spokes + [hub, arm, eboss, knob, kcap]
    # ---- spindle with its pinion and collar; the chuck; the bit
    yp = YW + 0.0421
    spin = G.cyl('dr_ss', (0, -0.0690, 0), (0, 0.0640, 0), 0.0031, 12, st)
    pin = K.spur_pinion('dr_pn', 0.0036, 0.0049, 12, 0.0052, st, axis=Y, origin=(0, yp - 0.0026, 0))
    col = turned('dr_sc', [(0.0605, 0.0), (0.0605, 0.0066), (0.0640, 0.0066), (0.0640, 0.0)], 18, st, axis=Y)
    spindle = [spin, pin, col]
    shell = AP.knurled_band('dr_ck', 0.0220, 0.0240, n=34, depth=0.00045, mat=nk, at=(0, 0.0645, 0), axis=Y); baked(shell)
    nose = ring_prof('dr_cn', [(0.0880, 0.0019), (0.0880, 0.0107), (0.0905, 0.0103), (0.0965, 0.0072), (0.0990, 0.0058), (0.0990, 0.0019)], 24, nk, axis=Y)
    back = turned('dr_cb', [(0.0640, 0.0), (0.0640, 0.0092), (0.0652, 0.0104), (0.0652, 0.0)], 24, nk, axis=Y)
    jaws = []
    for k in range(3):
        a = 2 * math.pi * k / 3 + math.pi / 6
        c = Vector((math.cos(a), 0, math.sin(a)))
        jaws.append(G.cyl('dr_cj', Vector((0, 0.0975, 0)) + c * 0.0031, Vector((0, 0.1018, 0)) + c * 0.0026, 0.0008, 6, st))
    chuck = [shell, nose, back] + jaws
    bm = T2.bright('t_drill_bit', base=(0.62, 0.61, 0.59), rough=0.26)
    secs = []
    for j in range(23):
        y = 0.0900 + 0.0640 * j / 22
        ph = 2 * math.pi * (y - 0.0900) / 0.0135
        sec = []
        for k in range(16):
            a = 2 * math.pi * k / 16
            fl = 0.0 if y < 0.1050 else (0.55 * max(0.0, math.cos(2 * (a - ph))) ** 3)
            r = 0.0015 * (1.0 - fl)
            if y > 0.1500:
                r *= max(0.08, 1.0 - (y - 0.1500) / 0.0042)
            sec.append(Vector((math.cos(a) * r, y, math.sin(a) * r)))
        secs.append(sec)
    bit = G.loft('drill_bit', secs, bm, caps=(True, True))
    pcs = frame + wheel + spindle + chuck + [bit]
    Mr = settle(pcs)
    Mt = recentre(pcs)
    Mf = Mt @ Mr
    K.frame_mats(pcs, Mf)
    root = join('drill', frame); wh = join('drill_wheel', wheel); sp = join('drill_spindle', spindle); ck = join('drill_chuck', chuck)
    for o in (root, wh, sp, ck, bit):
        G.shade(o, 38)
    return dict(root=root, wheel=wh, spindle=sp, chuck=ck, bit=bit, Mf=Mf, wc=Mf @ wc, wz=(Mf.to_3x3() @ Z).normalized(),
                sax=(Mf.to_3x3() @ Y).normalized(), so=Mf @ Vector((0, 0, 0)), tip=Mf @ Vector((0, 0.1540, 0)),
                grab=Mf @ Vector((0, -0.120, 0)), knob=Mf @ Vector((pe.x, pe.y, 0.036)), ratio=60 / 12)


def finish_drill(F, M, d):
    root, wh, sp, ck, bit = d['root'], d['wheel'], d['spindle'], d['chuck'], d['bit']
    Mw = bench_pose('tools_drill')
    for o in (root, wh, sp, ck, bit):
        put(o, Mw)
    tool(root, 'drill', 'Hand drill', ['turn'], ['tool:drill'], mass='medium', steps=['s3.drill'])
    sub(wh, 'drill_wheel', 'Drill crank wheel', 'drill', 'steel', 'light')
    sub(sp, 'drill_spindle', 'Drill spindle and pinion', 'drill', 'steel', 'tiny')
    sub(ck, 'drill_chuck', 'Drill chuck', 'drill', 'steel', 'tiny')
    CT.part(bit, FAM, 'drill_bit', 'Twist drill bit, 3 mm', kind='part', parent='drill', material='steel', mass='tiny', symmetry=0, tol_mm=3, tol_deg=20,
            steps=['s3.drill'], note='held in the chuck; turns with the spindle')
    CT.clear(bit, offset=Wd(root, d['sax']) * 0.045)
    mbk.tip(root, d['tip'], d['sax'])
    mbk.grab(root, d['grab'])
    mbk.mark(root, 'crank_knob', d['knob'], d['wz'])
    R = F.new_rig('drill', root)
    R.continuous('drill_crank', W(root, d['wc']), Wd(root, d['wz']), [wh])
    R.continuous('drill_spindle', W(root, d['so']), Wd(root, d['sax']), [sp, bit])
    R.hinge('drill_chuck', W(root, d['so']), Wd(root, d['sax']), 0.0, -150.0, [ck], parent='drill_spindle')
    F.end_rig(R)
    F.param_notes['tools.drill_crank'] = {'note': 'continuous: the crank wheel turns about its axle; the bench drives it from the turn count. '
                                                  'Turn tools.drill_spindle with it at ratio x the crank angle, the opposite hand'}
    F.param_notes['tools.drill_spindle'] = {'note': 'continuous: spindle, pinion, chuck and bit; turns %.1f times per crank turn (60 teeth on the wheel, 12 on the pinion)' % d['ratio'],
                                            'ratio': d['ratio']}
    F.param_notes['tools.drill_chuck'] = {'note': '0 = chuck shell tightened on the bit (as found), 1 = turned back 150 degrees, the bit free'}
    for o in (root, wh, sp, ck, bit):
        F.set_of[o.name] = HAND
    F.uv_weights[bit.name] = 1.4
    return root


# ====================================================================== soldering iron, its stand and the solder reel (Brann's)
Z_IRON = 0.0315


def build_iron(F, M):
    ck = T2.cork('t_iron_cork')
    T2.rings(ck, 1, [-0.0880, -0.0820, -0.0280, -0.0220], width=0.0010, depth=-2.0, col=(0.22, 0.15, 0.09))
    st = T2.nickel('t_iron_steel', base=(0.52, 0.51, 0.49), rough=0.4)
    cu = T2.copper_tip('t_iron_tip')
    cl = T2.cloth_lead('t_iron_lead')
    grip = turned('ir_g', [(-0.1010, 0.0), (-0.1010, 0.0060), (-0.0990, 0.0084), (-0.0940, 0.0096), (-0.0560, 0.0106), (-0.0200, 0.0099),
                           (-0.0130, 0.0089), (-0.0110, 0.0076), (-0.0110, 0.0)], 26, ck, axis=Y)
    guard = turned('ir_gd', [(-0.0125, 0.0), (-0.0125, 0.0070), (-0.0110, 0.0080), (-0.0030, 0.0080), (-0.0020, 0.0072), (0.0020, 0.0058),
                             (0.0040, 0.0047), (0.0040, 0.0)], 24, st, axis=Y)
    barrel = turned('ir_b', [(0.0030, 0.0), (0.0030, 0.0042), (0.0830, 0.0042), (0.0840, 0.0058), (0.0915, 0.0058), (0.0925, 0.0046), (0.0925, 0.0)], 20, st, axis=Y)
    nut = AP.knurled_band('ir_n', 0.0118, 0.0070, n=20, depth=0.0003, mat=st, at=(0, 0.0840, 0), axis=Y); baked(nut)
    tp = []
    for j in range(9):
        y = 0.0915 + 0.0370 * j / 8
        f = max(0.0, (y - 0.1190) / 0.0095)
        w = 0.0026 * (1.0 - 0.05 * f); h = 0.0026 * (1.0 - 0.82 * f)
        if j == 8:
            w *= 0.85; h *= 0.6
        tp.append([Vector((w * c, y, h * s)) for (c, s) in sup(2.0, 2.0, 14, 2.0 + 4.0 * f)])
    tip = G.loft('ir_t', tp, cu, caps=(True, True))
    relief = AP.spring('ir_rs', 0.020, 0.0090, 0.0010, 8, st, per_turn=10, wire_segs=6, at=(0, -0.1010, 0), axis=(0, -1, 0)); baked(relief)
    # the cloth lead: out of the butt, down and forward, coiled twice under the handle and tied
    lead = [Vector((0, -0.1030, 0)), Vector((0, -0.1150, -0.0020)), Vector((0.0010, -0.1225, -0.0100)), Vector((0.0030, -0.1235, -0.0200)),
            Vector((0.0060, -0.1185, -0.0262))]
    for k in range(16):
        a = math.radians(-80 - 700 * k / 15)
        r = 0.0185 + 0.0015 * math.sin(k * 0.9)
        lead.append(Vector((0.0010 + math.cos(a) * r * 0.6, -0.1000 + math.sin(a) * r, -Z_IRON + 0.0024 + 0.0030 * (k % 2) * 0.5 + 0.00020 * k)))
    cab = sweep_round('ir_c', K.smooth_path(lead, 1), 0.0022, 7, cl)
    tie = G.ring('ir_tie', (0.0010 - 0.0185 * 0.6, -0.1000, -Z_IRON + 0.0042), (0, 1, 0), 0.0042, 0.0010, 12, 6, cl)
    pcs = [grip, guard, barrel, nut, tip, relief, cab, tie]
    o = join('iron', pcs)
    G.shade(o, 40)
    return dict(root=o, tip=Vector((0, 0.1285, 0)), grab=Vector((0, -0.055, 0)))


def build_iron_stand(F, M):
    ci = T2.cast_iron('t_stand_iron', base=(0.30, 0.29, 0.28))
    wr = T2.forged('t_stand_wire', base=(0.46, 0.45, 0.43), oxide=0.45)
    base = G.prism('is_p', G.rounded_rect(0.058, 0.135, 0.010, 4), 0.0065, (0, 0.0, 0), X, Y, Z, ci, w0=0.0)
    G.bevel(base, 0.0012, 2, 30)
    lip = G.prism('is_l', G.rounded_rect(0.046, 0.052, 0.006, 4), 0.0030, (0, -0.030, 0.0060), X, Y, Z, ci, w0=0.0)
    lipc = G.prism('_lc', G.rounded_rect(0.040, 0.046, 0.004, 4), 0.006, (0, -0.030, 0.0072), X, Y, Z, w0=0.0)
    lip = G.boolean(lip, [lipc])
    # the spring coil the barrel lies in: a cone of wire, wide end toward the handle
    coil = []
    n = 6 * 14
    for k in range(n + 1):
        f = k / n
        a = 2 * math.pi * 6 * f
        r = 0.0098 + 0.0060 * (1 - f)
        coil.append(Vector((math.cos(a) * r, 0.0120 + 0.0560 * f, Z_IRON + math.sin(a) * r)))
    cw = G.tube_path('is_c', coil, 0.0008, 6, wr)
    legs = []
    for (y, rr) in ((0.0130, 0.0158), (0.0670, 0.0100)):
        for sg in (1, -1):
            p = [Vector((sg * rr * 0.7, y, Z_IRON - rr * 0.7)), Vector((sg * 0.016, y, 0.012)), Vector((sg * 0.019, y, 0.0062))]
            legs.append(G.tube_path('is_lg', p, 0.0011, 6, wr))
    # the V rest under the grip
    vr = [Vector((-0.0180, -0.0560, 0.0062)), Vector((-0.0160, -0.0560, 0.0200)), Vector((-0.0075, -0.0560, 0.0225)), Vector((0.0, -0.0560, 0.0205)),
          Vector((0.0075, -0.0560, 0.0225)), Vector((0.0160, -0.0560, 0.0200)), Vector((0.0180, -0.0560, 0.0062))]
    vrest = G.tube_path('is_v', K.smooth_path(vr, 2), 0.0012, 6, wr)
    o = join('iron_stand', [base, lip, cw] + legs + [vrest])
    G.shade(o, 40)
    return o


def build_solder_reel(F, M):
    pl = T2.plastic_dark('t_reel', base=(0.20, 0.19, 0.18))
    sd = T2.solder('t_solder')
    fl = []
    for z0 in (0.0, 0.0285):
        fl.append(ring_prof('sr_f', [(z0, 0.0045), (z0, 0.0196), (z0 + 0.0003, 0.0200), (z0 + 0.0022, 0.0200), (z0 + 0.0025, 0.0196), (z0 + 0.0025, 0.0045)],
                            32, pl, axis=Z))
    core = ring_prof('sr_c', [(0.0025, 0.0045), (0.0025, 0.0072), (0.0285, 0.0072), (0.0285, 0.0045)], 24, pl, axis=Z)
    wound = ring_prof('sr_w', [(0.0026, 0.0072), (0.0030, 0.0148), (0.0050, 0.0152), (0.0270, 0.0152), (0.0280, 0.0148), (0.0284, 0.0072)], 40, sd, axis=Z)
    free = [Vector((0.0152, 0.0, 0.0200)), Vector((0.0175, -0.0060, 0.0230)), Vector((0.0230, -0.0150, 0.0290)), Vector((0.0300, -0.0210, 0.0300)),
            Vector((0.0380, -0.0230, 0.0260)), Vector((0.0430, -0.0240, 0.0180))]
    fw = G.tube_path('sr_e', K.smooth_path(free, 2), 0.0007, 6, sd)
    o = join('solder_reel', fl + [core, wound, fw])
    G.shade(o, 40)
    return o


def finish_iron(F, M, d, stand, reel):
    o = d['root']
    Ms = bench_pose('tools_iron_stand')
    put(stand, Ms)
    put(o, Ms @ T((0, 0, Z_IRON)))
    put(reel, bench_pose('tools_solder_reel'))
    tool(o, 'iron', 'Soldering iron', ['window'], ['tool:solder'], material='wood', steps=['s3.tin', 's3.loop'])
    mbk.tip(o, d['tip'], (0, 1, 0))
    mbk.grab(o, d['grab'])
    CT.part(stand, FAM, 'iron_stand', 'Soldering iron stand', kind='fixture', material='steel', mass='medium', loose=True, steps=['s3.tin', 's3.loop'],
            note='the iron rests in it: tools.iron is exported in its seat')
    mbk.seat(stand, 'iron', M_local=T((0, 0, Z_IRON)), pose=True, accepts=['tools.iron'])
    CT.part(reel, FAM, 'solder_reel', 'Reel of solder', kind='fixture', material='plastic', mass='light', loose=True, steps=['s3.tin', 's3.loop'])
    F.set_of[o.name] = HAND
    F.set_of[stand.name] = BENCH
    F.set_of[reel.name] = BENCH
    return o


# ====================================================================== nanite applicator (Brann's)
def build_applicator(F, M):
    al = T2.alloy_barrel('t_app_barrel')
    ce = T2.ceramic('t_app_nib')
    bs = T2.brass('t_app_brass')
    ps = T2.paste('t_app_paste')
    dk = T2.plastic_dark('t_app_dark')
    prof = [(0.0, 0.0), (0.0, 0.0052), (0.0012, 0.0068), (0.0032, 0.0078), (0.0060, 0.0080), (0.0068, 0.0076), (0.0076, 0.0080), (0.1140, 0.0080),
            (0.1150, 0.0072), (0.1150, 0.0)]
    bar = turned('ap_b', prof, 32, al, axis=Y)
    win = G.prism('_aw', G.stadium(0.0440, 0.0056, 6), 0.0060, (0, 0.0640, 0.0080), Y, X, Z, w0=-0.0026)
    sl = G.prism('_as', G.stadium(0.0170, 0.0042, 6), 0.0060, (0, 0.0975, 0.0080), Y, X, Z, w0=-0.0018)
    bar = G.boolean(bar, [win, sl])
    paste = G.prism('ap_p', G.stadium(0.0436, 0.0052, 6), 0.0040, (0, 0.0640, 0.0080), Y, X, Z, ps, w0=-0.0062)
    knob = G.prism('ap_k', G.stadium(0.0080, 0.0036, 6), 0.0042, (0, 0.0935, 0.0080), Y, X, Z, dk, w0=-0.0018)
    G.bevel(knob, 0.0004, 1, 30)
    ribs = [G.box('ap_kr', (0, 0.0935 + (k - 1.5) * 0.0016, 0.0101), (0.0032, 0.0006, 0.0008), None, dk) for k in range(4)]
    col = turned('ap_c', [(0.1145, 0.0), (0.1145, 0.0075), (0.1160, 0.0078), (0.1235, 0.0074), (0.1250, 0.0060), (0.1250, 0.0)], 28, bs, axis=Y)
    nib = turned('ap_n', [(0.1245, 0.0), (0.1245, 0.0056), (0.1300, 0.0050), (0.1420, 0.0021), (0.1470, 0.0014), (0.1485, 0.0008), (0.1490, 0.0)], 22, ce, axis=Y)
    clip = K.loft_path('ap_cl', K.smooth_path([Vector((0, y, z)) for (y, z) in ((0.0060, 0.0082), (0.0110, 0.0098), (0.0300, 0.0094), (0.0420, 0.0089),
                                                                               (0.0450, 0.0084))], 2),
                       lambda i, f: sup(0.0040, 0.0009, 8, 4.0), al)
    pcs = [bar, paste, knob] + ribs + [col, nib, clip]
    Mr = settle(pcs)
    Mt = recentre(pcs)
    Mf = Mt @ Mr
    K.frame_mats(pcs, Mf)
    o = join('applicator', pcs)
    G.shade(o, 40)
    return dict(root=o, tip=Mf @ Vector((0, 0.1490, 0)), axis=(Mf.to_3x3() @ Y).normalized(), grab=Mf @ Vector((0, 0.050, 0)))


def finish_applicator(F, M, d):
    o = d['root']
    put(o, bench_pose('tools_applicator'))
    tool(o, 'applicator', 'Nanite applicator', ['point', 'path'], ['tool:applicator'], material='alloy', steps=['s5.seam', 's4.pressfit'])
    mbk.tip(o, d['tip'], d['axis'])
    mbk.grab(o, d['grab'])
    F.set_of[o.name] = HAND
    F.uv_weights[o.name] = 1.3
    return o


# ====================================================================== third hand (Brann's, stands on the work surface)
CLIP_Z = 0.095
CLIP_X = 0.0085
CLIP_Y = -0.032


def build_thirdhand(F, M):
    ci = T2.cast_iron('t_th_base', base=(0.27, 0.26, 0.25))
    st = T2.nickel('t_th_steel', base=(0.58, 0.57, 0.54))
    cp = T2.nickel('t_th_clip', base=(0.62, 0.60, 0.56), rough=0.34)
    base = turned('th_b', [(0.0, 0.0), (0.0, 0.0398), (0.0010, 0.0400), (0.0090, 0.0392), (0.0130, 0.0350), (0.0150, 0.0300), (0.0158, 0.0160),
                           (0.0170, 0.0130), (0.0170, 0.0)], 48, ci, axis=Z)
    post = G.cyl('th_p', (0, 0, 0.0160), (0, 0, 0.1240), 0.0040, 14, st, chamfer=0.0006)
    blk = G.box('th_k', (0, 0, 0.1180), (0.0150, 0.0130, 0.0140), None, st); G.bevel(blk, 0.0010, 2)
    ws = AP.knurled_band('th_ws', 0.0090, 0.0060, n=16, depth=0.0004, mat=st, at=(0, 0.0065, 0.1180), axis=(0, 1, 0)); baked(ws)
    bar = G.cyl('th_br', (-0.0620, 0, 0.1180), (0.0620, 0, 0.1180), 0.0030, 12, st, chamfer=0.0005)
    parts = [base, post, blk, ws, bar]
    for sg in (-1, 1):
        ball = turned('th_bl', [(0.0, 0.0), (0.0, 0.0010), (0.0015, 0.0042), (0.0045, 0.0055), (0.0075, 0.0042), (0.0090, 0.0010), (0.0090, 0.0)],
                      14, st, axis=X if sg > 0 else -X, origin=(sg * 0.0600, 0, 0.1180))
        p0 = Vector((sg * 0.0640, -0.0010, 0.1210)); p1 = Vector((sg * 0.0560, -0.0200, 0.1420)); p2 = Vector((sg * 0.0300, -0.0300, 0.1280))
        mouth = Vector((sg * CLIP_X, CLIP_Y, CLIP_Z))
        j = G.cyl('th_j', p1 + Vector((0, -0.0045, 0)), p1 + Vector((0, 0.0045, 0)), 0.0042, 12, st, chamfer=0.0008)
        w = AP.knurled_band('th_wn', 0.0080, 0.0030, n=12, depth=0.0005, mat=st, at=p1 + Vector((0, 0.0045, 0)), axis=(0, 1, 0)); baked(w)
        a1 = G.cyl('th_a', p0, p1, 0.0021, 10, st)
        # the clip hangs from the second joint toward the middle, mouth at the seat
        cd = (mouth - p2).normalized()
        clip = K.croc_clip('th_c', cp, length=0.030)
        Mc = mbk.AP.frame_matrix(mouth - cd * 0.030, cd, Vector((0, 0, 1)) if abs(cd.z) < 0.9 else Vector((1, 0, 0)))
        # croc_clip runs along +Y; frame_matrix puts +Z along cd: turn the clip's +Y onto +Z first
        clip.data.transform(Mc @ R4(X, 90.0))
        a2 = G.cyl('th_a2', p1, mouth - cd * 0.030, 0.0020, 10, st)
        parts += [ball, j, w, a1, a2, clip]
    o = join('thirdhand', parts)
    G.shade(o, 40)
    return o


def finish_thirdhand(F, M, o):
    put(o, bench_pose('tools_thirdhand'))
    CT.part(o, FAM, 'thirdhand', 'Third hand', kind='fixture', material='steel', mass='medium', loose=True, steps=['s3.loop'],
            note='stands on the work surface; the two crocodile clips hold the leads, the resistor sits between them')
    mbk.seat(o, 'lead_l', M_local=T((-CLIP_X, CLIP_Y, CLIP_Z)), pose=True, accepts=['materials.lead_a', 'materials.lead_b'])
    mbk.seat(o, 'lead_r', M_local=T((CLIP_X, CLIP_Y, CLIP_Z)), pose=True, accepts=['materials.lead_a', 'materials.lead_b'])
    mbk.seat(o, 'resistor', M_local=T((0, CLIP_Y, CLIP_Z)), pose=True, accepts=['materials.resistor'])
    F.set_of[o.name] = BENCH
    return o
