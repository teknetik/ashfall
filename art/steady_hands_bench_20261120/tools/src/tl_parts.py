# tl_parts.py: the hand tools, part by part (slice set first). Each tool is built along +Y (working end at +Y) about
# its axis, settled onto z = 0 the way it lies on a bench (mbk.rest_tilt), then given its place. See ../PARTS.md.
import math, json
import bpy, bmesh
from mathutils import Vector, Matrix
import mbk
from mbk import G, MT, CT, AP, RG, MM, X, Y, Z, O, T, R4, put, W, Wd, bench_pose, join, box, turned, ring_prof, extrude_z, extrude_x
import tl_mats

FAM = 'tools'
I4 = Matrix.Identity(4)


def bake_place(objs):
    for o in objs:
        o.data.transform(o.matrix_world); o.matrix_world = Matrix.Identity(4)
    return objs


def settle(pieces, about=None, extra=()):
    """Turn and lift the pieces (and `extra`, which do not take part in finding the rest) onto z = 0. Returns the 4x4."""
    Mr = mbk.rest_tilt(pieces, about)
    for o in list(pieces) + list(extra):
        o.data.transform(Mr); o.data.update()
    return Mr


def tool(o, pid, label, verbs, tags, material='steel', mass='light', parent=None, item=None, steps=(), note=None, **kw):
    kw.setdefault('loose', parent is None)
    return CT.tool(o, FAM, pid, label, verbs, tags, parent=parent, material=material, mass=mass, item=item, steps=list(steps), note=note, **kw)


def sub(o, pid, label, parent, material, mass='tiny', note=None):
    return CT.part(o, FAM, pid, label, kind='part', parent=parent, material=material, mass=mass, loose=True,
                   note=note or 'fixed sub-part of %s.%s, never separated on the bench' % (FAM, parent))


def superring(y, hx, hz, n=12, p=6.0, phase=0.0):
    out = []
    for k in range(n):
        a = phase + 2 * math.pi * k / n
        c, s = math.cos(a), math.sin(a)
        out.append(Vector((hx * math.copysign(abs(c) ** (2.0 / p), c), y, hz * math.copysign(abs(s) ** (2.0 / p), s))))
    return out


def circring(y, r, n=12, phase=0.0):
    return [Vector((r * math.cos(phase + 2 * math.pi * k / n), y, r * math.sin(phase + 2 * math.pi * k / n))) for k in range(n)]


def crossring(y, R, r_in, w):
    out = []
    for k in range(4):
        th = math.pi / 2 * k
        d = math.asin(min(0.95, w / R))
        for a, rr in ((th - d, R), (th + d, R), (th + math.pi / 4, r_in)):
            out.append(Vector((rr * math.cos(a), y, rr * math.sin(a))))
    return out


def crossring_round(y, r):
    out = []
    for k in range(4):
        th = math.pi / 2 * k
        for a in (th - math.radians(15), th + math.radians(15), th + math.pi / 4):
            out.append(Vector((r * math.cos(a), y, r * math.sin(a))))
    return out


HEX_AF = 6.35 * MM


def make_bit(name, kind, M):
    """A 45 mm hex-shank bit in its own frame: shank end at the origin, tip at y = 0.045."""
    rc = HEX_AF / 2 / math.cos(math.radians(30))
    shank = G.prism(name + '_sh', G.circle(rc, 6), 0.0255, O, Z, X, Y, M['t_shaft'], w0=0.0)
    G.bevel(shank, 0.0003, 1)
    if kind == 'slot':
        sec = [circring(0.025, 0.0030), circring(0.030, 0.0025), superring(0.038, 0.0026, 0.0014), superring(0.0442, 0.0026, 0.00048), superring(0.045, 0.0026, 0.00036)]
    else:
        sec = [crossring_round(0.025, 0.0030), crossring_round(0.031, 0.0026), crossring(0.0365, 0.0026, 0.0011, 0.00062),
               crossring(0.0425, 0.0013, 0.00055, 0.00034), crossring(0.045, 0.00035, 0.00022, 0.00012)]
    tipm = G.loft(name + '_tip', sec, M['t_steel_bright'], caps=(True, True))
    G.shade(tipm, 40)
    o = join(name, [shank, tipm])
    return o


# ====================================================================== screwdriver, bits, bit block
def build_screwdriver(F, M):
    y0 = -0.095
    og = (0, y0, 0)
    hp = [(0, 0), (0.0015, 0.0075), (0.006, 0.0118), (0.018, 0.0138), (0.034, 0.0140), (0.052, 0.0128), (0.0585, 0.0120), (0.0595, 0.0113), (0.0605, 0.0120),
          (0.0635, 0.0118), (0.0645, 0.0111), (0.0655, 0.0117), (0.078, 0.0102), (0.090, 0.0094), (0.097, 0.0092), (0.097, 0)]
    handle = turned('h', hp, 28, M['t_wood'], axis=Y, origin=og)
    # a flat worn on one side of the handle where it has been set down and struck
    fer = turned('f', [(0.0955, 0), (0.0955, 0.0096), (0.0965, 0.0100), (0.1000, 0.0100), (0.1006, 0.0096), (0.1070, 0.0096), (0.1095, 0.0080), (0.1095, 0)],
                 28, M['t_brass'], axis=Y, origin=og)
    shaft = turned('s', [(0.108, 0), (0.108, 0.0031), (0.1675, 0.0031), (0.1690, 0.0048), (0.1893, 0.0048), (0.1900, 0.0042), (0.1900, 0)],
                   20, M['t_shaft'], axis=Y, origin=og)
    rc = (HEX_AF + 0.15 * MM) / 2 / math.cos(math.radians(30))
    shaft = G.boolean(shaft, [G.prism('_hx', G.circle(rc, 6), 0.0132, (0, y0 + 0.190 - 0.013, 0), Z, X, Y, w0=0.0)])
    collar = AP.knurled_band('collar', 0.0122, 0.016, n=26, depth=0.00045, mat=M['t_steel'], at=(0, y0 + 0.171, 0), axis=Y, ref=Z, d_in=0.0099)
    bake_place([collar])
    slot = make_bit('bit_slot', 'slot', M)
    slot.data.transform(T((0, y0 + 0.1775, 0)))
    Mr = settle([handle, fer, shaft, collar, slot], about=-0.03)
    sd = join('screwdriver', [handle, fer, shaft])
    G.shade(sd, 38)
    return dict(root=sd, collar=collar, slot=slot, Mr=Mr, tip=Mr @ Vector((0, y0 + 0.2225, 0)), axis=(Mr.to_3x3() @ Y).normalized(),
                sock=Mr @ Vector((0, y0 + 0.1775, 0)), grab=Mr @ Vector((0, y0 + 0.045, 0)), y_tip=y0 + 0.2225, y_butt=y0, thick=0.029, width=0.029)


def finish_screwdriver(F, M, d, Mw):
    sd, collar, slot = d['root'], d['collar'], d['slot']
    for o in (sd, collar, slot):
        put(o, Mw)
    tool(sd, 'screwdriver', 'Screwdriver', ['turn', 'window'], ['tool:screwdriver'], material='wood', parent='roll', item=None,
         steps=['s1.screw_a', 's1.screw_b', 's2.screws', 's2.trunnion', 's5.torque', 's6.screws'])
    sub(collar, 'screwdriver_collar', 'Bit collar', 'screwdriver', 'steel')
    G.set_origin(collar, W(sd, d['sock']))
    # the slot bit: its own node, seated in the socket, drawn out along the tool axis
    G.set_frame(slot, sd.matrix_world @ (T(d['sock']) @ d['Mr'].to_3x3().to_4x4()))
    tool(slot, 'bit_slot', 'Slotted bit', ['turn'], ['bit:slot'], parent='screwdriver', mass='tiny', symmetry=6, tol_mm=3, tol_deg=20, steps=['s1.screw_a'])
    CT.clear(slot, offset=Wd(sd, d['axis']) * 0.022)
    mbk.tip(slot, (0, 0.045, 0), (0, 1, 0))
    mbk.tip(sd, d['tip'], d['axis'])
    mbk.grab(sd, d['grab'])
    mbk.seat(sd, 'bit', M_local=T(d['sock']) @ d['Mr'].to_3x3().to_4x4(), pose=True, accepts=['tools.bit_slot', 'tools.bit_cross'])
    R = F.new_rig('screwdriver', sd)
    R.slide('screwdriver_bit', W(sd, d['sock']), -Wd(sd, d['axis']), 0.0, 0.004, [collar])
    F.end_rig(R)
    F.param_notes['tools.screwdriver_bit'] = {'note': '0 = collar forward, bit locked (as found); 1 = collar drawn back 4 mm, bit free'}
    for o in (sd, collar, slot):
        F.set_of[o.name] = 'a'
    F.uv_weights[slot.name] = 1.4
    return sd


def build_bitblock(F, M):
    blk = box('blk', (-0.015, 0.0, 0.0), (0.015, 0.024, 0.016), M['t_wood_pale'], bevel=0.0012, segs=2)
    rc = (HEX_AF + 0.2 * MM) / 2 / math.cos(math.radians(30))
    blk = G.boolean(blk, [G.prism('_h', G.circle(rc, 6), 0.0135, (sx * 0.0075, -0.0005, 0.008), Z, X, Y, w0=0.0) for sx in (-1, 1)])
    cross = make_bit('bit_cross', 'cross', M)
    return dict(root=blk, cross=cross, y_tip=0.024, y_butt=-0.033, thick=0.017, width=0.030)


def finish_bitblock(F, M, d, Mw):
    blk, cross = d['root'], d['cross']
    put(blk, Mw)
    CT.part(blk, FAM, 'bitblock', 'Bit block', kind='part', parent='roll', material='wood', mass='tiny', steps=['s2.screws'],
            note='holds the bit that is not in the screwdriver')
    for nm, sx in (('bit_a', -1), ('bit_b', 1)):
        mbk.seat(blk, nm, M_local=T((sx * 0.0075, 0.0125, 0.008)) @ R4('Z', 180), pose=True, accepts=['tools.bit_slot', 'tools.bit_cross'])
    put(cross, Mw @ T((0.0075, 0.0125, 0.008)) @ R4('Z', 180))
    tool(cross, 'bit_cross', 'Cross bit', ['turn'], ['bit:cross'], parent='bitblock', mass='tiny', symmetry=6, tol_mm=3, tol_deg=20, steps=['s2.screws'])
    mbk.clear_local(cross, (0, 0.022, 0))
    mbk.tip(cross, (0, 0.045, 0), (0, 1, 0))
    for o in (blk, cross):
        F.set_of[o.name] = 'a'
    F.uv_weights[cross.name] = 1.4
    return blk


# ====================================================================== pliers and cutters
def serrate(p0, p1, pitch, depth):
    """Points along p0 -> p1 with saw teeth toward -X."""
    a, b = Vector(p0), Vector(p1)
    n = max(2, int(round((b - a).length / pitch)))
    out = []
    for k in range(n):
        out.append(tuple(a.lerp(b, k / n)))
        m = a.lerp(b, (k + 0.5) / n)
        out.append((m.x - depth, m.y))
    out.append(tuple(b))
    return out


def poly_area(poly):
    return 0.5 * sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))


def offset_poly(poly, d):
    """Grow a simple polygon outward by d (vertex normals from the two edges)."""
    sg = 1.0 if poly_area(poly) > 0 else -1.0
    n = len(poly); out = []
    for i in range(n):
        p0 = Vector(poly[i - 1]); p1 = Vector(poly[i]); p2 = Vector(poly[(i + 1) % n])
        e1 = (p1 - p0).normalized(); e2 = (p2 - p1).normalized()
        n1 = Vector((e1.y, -e1.x)) * sg; n2 = Vector((e2.y, -e2.x)) * sg
        m = (n1 + n2)
        if m.length < 1e-9:
            m = n1
        m.normalize()
        k = d / max(0.35, m.dot(n1))
        out.append((p1.x + m.x * k, p1.y + m.y * k))
    return out


def clip_poly_y(poly, ymax):
    """The part of a polygon with y <= ymax."""
    out = []
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        ina, inb = a[1] <= ymax, b[1] <= ymax
        if ina:
            out.append(a)
        if ina != inb:
            f = (ymax - a[1]) / (b[1] - a[1])
            out.append((a[0] + (b[0] - a[0]) * f, ymax))
    return out


def wedge(name, poly, zmid, half_fn, mat):
    """A prism whose half thickness varies over the outline: half_fn(x, y) -> half thickness (keep it linear and the
    top and bottom stay flat)."""
    n = len(poly)
    verts = [(x, y, zmid - half_fn(x, y)) for x, y in poly] + [(x, y, zmid + half_fn(x, y)) for x, y in poly]
    faces = [tuple(range(n))[::-1], tuple(range(n, 2 * n))] + [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    return G.mesh_obj(name, verts, faces, mat, recalc=True)


def scissor(F, M, key, jaw, handle, th, rj, steel, jaw_half, sleeve_mat_fn, sleeve_t, sleeve_bevel, sleeve_from, rivet_d=0.0085, jaw_mat=None):
    """Two forged halves crossing at a round lap joint on a rivet. Outlines of half A in XY: jaw (on the -X side, a
    wedge: jaw_half(x, y) is its half thickness) and handle (steel core on the +X side); both run into the joint disc
    of radius rj. Inside the disc A keeps the lower half and B the upper, and nothing of full thickness comes nearer
    the pivot than rj, so the halves turn freely. A sleeve (tape or dipped rubber) is built over the handle below
    y = sleeve_from. Half B is the mirror. Returns (a, b), lifted so that the sleeves rest on z = 0."""
    d = 0.0002
    gap = 0.00012
    disc = G.circle(rj - 0.0004, 32)

    def half(tag, mirror):
        bs = extrude_z(tag + '_bs', disc, 0.0, th, steel)
        jw = wedge(tag + '_jw', jaw, th / 2, jaw_half, jaw_mat or steel)
        hc = extrude_z(tag + '_hc', handle, 0.0, th, steel)
        sl = extrude_z(tag + '_sl', offset_poly(clip_poly_y(handle, sleeve_from), sleeve_t), -sleeve_t, th + sleeve_t, sleeve_mat_fn(mirror))
        if mirror:
            for o in (bs, jw, hc, sl):
                G.mirror(o, 0)
        return bs, jw, hc, sl
    A = half(key + '_a', False)
    B = half(key + '_b', True)
    out = []
    for (bs, jw, hc, sl), lower in ((A, True), (B, False)):
        res = []
        for o, bw in ((bs, 0.0006), (jw, 0.0006), (hc, 0.0010)):
            G.bevel(o, bw, 1)          # break the edges first: a bevel after the cut would fill the lap's inside corners
            if lower:                  # A keeps the lower half inside the joint
                cut = [G.cyl('_cc', (0, 0, th / 2 - 0.00006), (0, 0, th + d + 0.002), rj + gap, 32)]
            else:
                cut = [G.cyl('_cc', (0, 0, -d - 0.002), (0, 0, th / 2 + 0.00006), rj + gap, 32)]
                if o is bs:            # the rivet's hole goes through the joint disc only
                    cut.append(G.cyl('_ch', (0, 0, -0.01), (0, 0, 0.02), rivet_d / 2 * 0.72 + 0.00018, 14))
            o = G.boolean(o, cut)
            res.append(o)
        G.bevel(sl, sleeve_bevel, 2)
        out.append(res + [sl])
    rv = AP.rivet(key + '_rv', rivet_d, rivet_d * 0.22, steel, segs=12, at=(0, 0, th + 0.00025))
    pin = G.cyl(key + '_pin', (0, 0, 0.0002), (0, 0, th), rivet_d / 2 * 0.72, 12, steel)
    bake_place([rv])
    a = join(key + '_a', out[0] + [rv, pin])
    b = join(key + '_b', out[1])
    for o in (a, b):
        o.data.transform(T((0, 0, sleeve_t)))
        G.shade(o, 38)
    return a, b


def finish_scissor(F, M, a, b, pid, label, Mw, open_deg, tip, grab, verbs, tags, steps, note0):
    put(a, Mw); put(b, Mw)
    tool(a, pid, label, verbs, tags, parent='roll', steps=steps)
    sub(b, pid + '_b', label + ', second half', pid, 'steel', 'light')
    mbk.tip(a, tip, (0, 1, 0))
    mbk.grab(a, grab)
    R = F.new_rig(pid, a)
    R.hinge(pid + '_jaws', W(a, (0, 0, 0)), Wd(a, (0, 0, 1)), 0.0, -open_deg, [b])
    F.end_rig(R)
    F.param_notes['tools.%s_jaws' % pid] = {'note': note0}
    for o in (a, b):
        F.set_of[o.name] = 'a'
    return a


def build_pliers(F, M):
    th, st = 0.0095, 0.0009
    teeth = serrate((-0.0002, 0.050), (-0.0002, 0.0295), 0.0011, 0.00055)
    jaw = teeth + [(-0.0026, 0.0268), (-0.0036, 0.0210), (-0.0022, 0.0152), (-0.0002, 0.0122), (-0.0002, 0.0100), (-0.0121, 0.0100),
                   (-0.0108, 0.0220), (-0.0082, 0.0380), (-0.0050, 0.0500)]
    handle = [(0.0026, -0.0095), (0.0112, -0.0062), (0.0136, -0.0150), (0.0178, -0.0330), (0.0224, -0.0560), (0.0250, -0.0800), (0.0246, -0.1020), (0.0222, -0.1125),
              (0.0190, -0.1150), (0.0164, -0.1128), (0.0162, -0.1010), (0.0170, -0.0800), (0.0146, -0.0580), (0.0102, -0.0360), (0.0050, -0.0180)]

    def jaw_half(x, y):          # thinner toward the tip: 9.5 mm at the joint, 6.4 mm at the nose
        return th / 2 * (1.0 - 0.33 * max(0.0, (y - 0.0125) / 0.0375))

    def sleeve(mirror):
        sg = -1 if mirror else 1
        return tl_mats.tape('pliers_tape_%s' % ('b' if mirror else 'a'), (sg * 0.0125, -0.030, th / 2 + st), (sg * 0.105, -0.994, 0), 0.0, 0.088, pitch=0.0072)
    a, b = scissor(F, M, 'pliers', jaw, handle, th, 0.0128, M['t_steel_pliers'], jaw_half, sleeve, st, 0.0030, -0.030)
    return dict(root=a, b=b, y_tip=0.050, y_butt=-0.116, thick=th + 2 * st, width=0.054, z0=st)


def build_cutters(F, M):
    th, st = 0.009, 0.0014
    jaw = [(-0.00006, 0.0345), (-0.00006, 0.0100), (-0.0109, 0.0100), (-0.0106, 0.0140), (-0.0088, 0.0225), (-0.0056, 0.0300), (-0.0022, 0.0345)]
    handle = [(0.0022, -0.0085), (0.0100, -0.0055), (0.0124, -0.0135), (0.0162, -0.0280), (0.0200, -0.0480), (0.0216, -0.0700), (0.0206, -0.0920), (0.0182, -0.1022),
              (0.0152, -0.1045), (0.0128, -0.1022), (0.0130, -0.0910), (0.0138, -0.0700), (0.0122, -0.0490), (0.0088, -0.0300), (0.0044, -0.0160)]

    def jaw_half(x, y):          # a blade: thick at its back, ground to an edge along the centre line
        return th / 2 * (0.10 + 0.90 * min(1.0, abs(x) / 0.0109))
    a, b = scissor(F, M, 'cutters', jaw, handle, th, 0.0114, M['t_steel'], jaw_half, lambda mirror: M['t_rubber_red'], st, 0.0036, -0.024,
                   rivet_d=0.0078, jaw_mat=M['t_steel_bright'])
    return dict(root=a, b=b, y_tip=0.0345, y_butt=-0.1055, thick=th + 2 * st, width=0.048, z0=st)


# ====================================================================== pin punch
def build_punch(F, M):
    y0 = -0.060
    og = (0, y0, 0)
    head = turned('ph', [(0, 0), (0.0002, 0.0034), (0.0012, 0.0050), (0.0026, 0.0054), (0.0040, 0.0049), (0.0058, 0.0041), (0.0125, 0.0040), (0.0125, 0)], 18, M['t_steel'], axis=Y, origin=og)
    rc = 0.004 / math.cos(math.radians(22.5))
    body = G.prism('pb', G.circle(rc, 8, phase=math.radians(22.5)), 0.0735, (0, y0 + 0.012, 0), Z, X, Y, M['t_steel'], w0=0.0)
    G.bevel(body, 0.0004, 1)
    nose = turned('pn', [(0.0850, 0), (0.0850, 0.0040), (0.0865, 0.0040), (0.0945, 0.0019), (0.0952, 0.0015), (0.1196, 0.0015), (0.1200, 0.0012), (0.1200, 0)],
                  12, M['t_steel_bright'], axis=Y, origin=og)
    Mr = settle([head, body, nose])
    p = join('punch', [head, body, nose])
    G.shade(p, 35)
    return dict(root=p, Mr=Mr, tip=Mr @ Vector((0, y0 + 0.120, 0)), axis=(Mr.to_3x3() @ Y).normalized(), strike=Mr @ Vector((0, y0, 0)),
                grab=Mr @ Vector((0, y0 + 0.05, 0)), y_tip=y0 + 0.120, y_butt=y0, thick=0.0115, width=0.011)


def finish_punch(F, M, d, Mw):
    p = d['root']
    put(p, Mw)
    tool(p, 'punch', 'Pin punch', ['window', 'point'], ['tool:punch'], parent='roll', steps=['s1.pin', 's3.punch', 's6.pin'])
    mbk.tip(p, d['tip'], d['axis'])
    mbk.grab(p, d['grab'])
    mbk.mark(p, 'strike', d['strike'], -Vector(d['axis']))
    F.set_of[p.name] = 'a'
    return p


# ====================================================================== mallet (Brann's)
def build_mallet(F, M):
    y0 = -0.140
    hp = [(0, 0), (0.0015, 0.0095), (0.006, 0.0128), (0.016, 0.0136), (0.060, 0.0126), (0.104, 0.0112), (0.118, 0.0104), (0.200, 0.0098), (0.238, 0.0101),
          (0.277, 0.0101), (0.2785, 0.0093), (0.2785, 0)]
    grip = turned('mg', [p for p in hp if p[0] <= 0.1045] + [(0.1045, 0)], 26, None, axis=Y, origin=(0, y0, 0))
    hd = turned('mh', [(0.1035, 0)] + [p for p in hp if p[0] >= 0.104], 26, M['t_wood_pale'], axis=Y, origin=(0, y0, 0))
    for o in (grip, hd):
        o.data.transform(Matrix.Diagonal((1.0, 1.0, 0.86, 1.0)))
    yc = y0 + 0.258
    c = (0, yc, 0)
    brass = turned('mb', [(-0.0400, 0), (-0.0400, 0.0162), (-0.0388, 0.0186), (-0.0375, 0.0191), (-0.0262, 0.0189), (-0.0255, 0.0180), (-0.0255, 0)], 32, M['t_brass_face'], axis=X, origin=c)
    barrel = turned('ms', [(-0.0258, 0), (-0.0258, 0.0176), (-0.0245, 0.0176), (-0.0240, 0.0190), (-0.0190, 0.0190), (-0.0185, 0.0176), (0.0135, 0.0176), (0.0140, 0.0190),
                           (0.0190, 0.0190), (0.0195, 0.0176), (0.0208, 0.0176), (0.0208, 0)], 32, M['t_steel'], axis=X, origin=c)
    hide = turned('mr', [(0.0205, 0), (0.0205, 0.0182), (0.0215, 0.0188), (0.0340, 0.0192), (0.0380, 0.0197), (0.0396, 0.0186), (0.0400, 0.0165), (0.0400, 0)], 32, M['t_rawhide'], axis=X, origin=c)
    wedge = box('mw', (-0.0045, yc + 0.0180, -0.0012), (0.0045, yc + 0.0212, 0.0012), M['t_steel'], bevel=0.0003)
    pcs = [grip, hd, brass, barrel, hide, wedge]
    Mr = settle(pcs, about=yc - 0.06)
    grip.data.materials.append(tl_mats.tape('mallet_tape', Mr @ Vector((0, y0, 0)), Mr.to_3x3() @ Y, 0.012, 0.106, pitch=0.008))
    m = join('mallet', pcs)
    G.shade(m, 40)
    return dict(root=m, Mr=Mr, tip=Mr @ Vector((-0.040, yc, 0)), soft=Mr @ Vector((0.040, yc, 0)), grab=Mr @ Vector((0, y0 + 0.06, 0)))


def finish_mallet(F, M, d):
    m = d['root']
    put(m, bench_pose('tools_mallet'))
    tool(m, 'mallet', 'Mallet', ['window'], ['tool:mallet'], material='wood', mass='medium', steps=['s1.screw_b', 's1.pin', 's3.punch', 's4.flash', 's6.pin'])
    mbk.tip(m, d['tip'], (-1, 0, 0))
    mbk.mark(m, 'face_soft', d['soft'], (1, 0, 0))
    mbk.grab(m, d['grab'])
    F.set_of[m.name] = 'b'
    return m


# ====================================================================== oil dropper and its bottle (Brann's)
def build_oil(F, M):
    g = M['glass_amber']
    bottle = turned('ob', [(0, 0), (0, 0.0138), (0.0012, 0.0152), (0.0030, 0.0160), (0.0400, 0.0160), (0.0445, 0.0148), (0.0478, 0.0118), (0.0500, 0.0090),
                           (0.0600, 0.0090), (0.0608, 0.0084), (0.0608, 0.0072), (0.0500, 0.0072), (0.0468, 0.0108), (0.0440, 0.0134), (0.0400, 0.0144),
                           (0.0045, 0.0144), (0.0032, 0.0130), (0.0030, 0)], 32, g, axis=Z)
    # the oil leaves a well down the middle for the pipette (a liquid would close round it; a mesh cannot)
    oil = ring_prof('oo', [(0.0033, 0.0037), (0.0033, 0.0128), (0.0046, 0.0141), (0.0300, 0.0141), (0.0300, 0.0037)], 20, M['t_oil'], axis=Z)
    bottle = join('oil_bottle', [bottle, oil])
    G.shade(bottle, 50)
    # the dropper: bakelite cap with ribs, glass pipette with oil standing in it; the rubber bulb is on its own bone
    cap = ring_prof('oc', [(0.0528, 0.0094), (0.0528, 0.0108), (0.0650, 0.0108), (0.0662, 0.0098), (0.0662, 0.0040), (0.0640, 0.0040), (0.0640, 0.0094)], 22, M['t_bakelite'], axis=Z)
    ribs = AP.knurled_band('or', 0.0228, 0.0105, n=22, depth=0.0006, mat=M['t_bakelite'], at=(0, 0, 0.0534), axis=Z, d_in=0.0214)
    bake_place([ribs])
    pip = turned('op', [(0.0655, 0), (0.0655, 0.0030), (0.0200, 0.0030), (0.0120, 0.0016), (0.0085, 0.0013), (0.0085, 0)], 10, M['glass_clear'], axis=Z)
    col = turned('ol', [(0.0420, 0), (0.0420, 0.0022), (0.0205, 0.0022), (0.0125, 0.0009), (0.0095, 0.0007), (0.0095, 0)], 8, M['t_oil'], axis=Z)
    drop = join('oil_dropper', [cap, ribs, pip, col])
    G.shade(drop, 45)
    bulb = turned('obu', [(0.0655, 0), (0.0655, 0.0042), (0.0668, 0.0064), (0.0705, 0.0076), (0.0800, 0.0085), (0.0900, 0.0081), (0.0965, 0.0062),
                          (0.0995, 0.0030), (0.1002, 0)], 24, M['t_black_rubber'], axis=Z)
    G.shade(bulb, 60)
    Mw = bench_pose('tools_oil_bottle')
    for o in (bottle, drop, bulb):
        put(o, Mw)
    CT.part(bottle, FAM, 'oil_bottle', 'Oil bottle', kind='fixture', material='glass', mass='light', loose=True, steps=['s1.screw_b', 's3.oil'])
    tool(drop, 'oil_dropper', 'Oil dropper', ['point'], ['tool:oil'], material='glass', mass='tiny', parent='oil_bottle', symmetry=0, tol_mm=6, tol_deg=30,
         steps=['s1.screw_b', 's3.oil'])
    CT.clear(drop, offset=(0, 0, 0.070))
    sub(bulb, 'oil_dropper_bulb', 'Dropper bulb', 'oil_dropper', 'rubber')
    G.set_origin(bulb, W(drop, (0, 0, 0.0655)))
    mbk.tip(drop, (0, 0, 0.0085), (0, 0, -1))
    mbk.grab(drop, (0, 0, 0.082))
    mbk.seat(bottle, 'dropper', p=(0, 0, 0), pose=True, accepts=['tools.oil_dropper'])
    mbk.scale_rig(F, 'dropper', 'dropper_bulb', drop, W(drop, (0, 0, 0.0655)), Wd(drop, (0, 0, 1)), [bulb], (1, 1, 1), (0.55, 0.96, 0.78),
                  note='0 = bulb full (as found), 1 = squeezed: the bone scales, the bulb flattens between finger and thumb')
    for o in (bottle, drop, bulb):
        F.set_of[o.name] = 'b'
    F.uv_weights[bottle.name] = 1.2
    return bottle
