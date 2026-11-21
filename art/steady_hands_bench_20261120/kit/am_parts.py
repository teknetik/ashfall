# kit/am_parts.py: small mechanical parts as real geometry for a 0.3 m view: screws with slotted, cross and hex
# drives and real (helical) threads, washers, nuts, circlips, knurled bands, hinge knuckles on a pin, springs, wire,
# sleeved leads, spring clips, rivets, tubes.
#
# Every builder returns ONE linked mesh object whose own frame means something: origin at the seat (the underside of a
# screw head, the middle of a washer's lower face, the hinge axis), local +Z out of the hole / along the axis. Place a
# part with `at` (world point) and `axis` (world direction of its +Z); `ref` fixes the turn about the axis. Because
# +Z is the removal direction, a fastener's `__clear` pose is the same frame moved along +Z.
# All sizes in metres (use MM). Triangle counts are in the docstrings so a family can budget.
#
# Parts of this file follow builders in AnyMachine (https://github.com/apekshik/anymachine, commit d5e8889):
# hardsurface/guns/svd/detail_parts.py (the rivet, pin and hex head profiles, the wire ring), svd_parts.py (the cross
# pin, the lathe-with-fluting idea used for the knurled band) and hardsurface/dugout_blender/props_hand/_common/hs.py
# (the alternating hinge knuckles). They were read and rewritten for this kit's frames; nothing is imported from it.
#
#   MIT License. Copyright (c) 2026 Apekshik Panigrahi
#   Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
#   documentation files (the "Software"), to deal in the Software without restriction, including without limitation
#   the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and
#   to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#   The above copyright notice and this permission notice shall be included in all copies or substantial portions of
#   the Software.
#   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
#   THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#   AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
#   TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#   SOFTWARE.
import bpy, bmesh, math
from mathutils import Vector, Matrix
import geo as G

MM = 0.001
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
O = Vector((0, 0, 0))


def frame_matrix(at, axis, ref=None):
    """4x4 world frame with origin `at`, +Z along `axis`, +X toward `ref` (made perpendicular)."""
    z = Vector(axis).normalized()
    r = Vector(ref) if ref is not None else (Vector((1, 0, 0)) if abs(z.x) < 0.9 else Vector((0, 1, 0)))
    x = (r - z * z.dot(r)).normalized()
    y = z.cross(x)
    M = Matrix((x, y, z)).transposed().to_4x4()
    M.translation = Vector(at)
    return M


def place(o, at=(0, 0, 0), axis=(0, 0, 1), ref=None):
    """Give a part built about the origin (+Z up) its world frame. The mesh stays in the part's own frame."""
    o.matrix_world = frame_matrix(at, axis, ref)
    bpy.context.view_layer.update()
    return o


def _thread_ridge(name, r_root, r_crest, pitch, z0, z1, segs=10, mat=None, lead=0.75):
    """Helical V ridge from z0 up to z1 (open shell lying on a core of radius r_root). 2 quads per step."""
    turns = max(1.0, (z1 - z0 - pitch) / pitch)
    n = int(round(turns * segs))
    verts, faces = [], []
    for k in range(n + 1):
        th = 2 * math.pi * k / segs
        z = z0 + pitch * k / segs
        ramp = min(1.0, k / (segs * lead), (n - k) / (segs * lead))      # run-in and run-out
        rc = r_root + (r_crest - r_root) * max(0.0, ramp)
        c, s = math.cos(th), math.sin(th)
        verts += [(r_root * 0.97 * c, r_root * 0.97 * s, z), (rc * c, rc * s, z + pitch * 0.5), (r_root * 0.97 * c, r_root * 0.97 * s, z + pitch)]
    for k in range(n):
        a, b = 3 * k, 3 * (k + 1)
        faces += [(a, b, b + 1, a + 1), (a + 1, b + 1, b + 2, a + 2)]
    o = G.mesh_obj(name, verts, faces, mat, recalc=False)
    # outward: flank normals must point away from the axis
    me = o.data
    p = me.polygons[len(me.polygons) // 2]
    if Vector((p.center.x, p.center.y, 0)).dot(p.normal) < 0:
        bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.reverse_faces(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    return o


def _drive_cutters(drive, head_r, top_z, depth, turn=0.0):
    c = []
    if drive == 'slot':
        w = head_r * 0.30
        c.append(G.prism('_s', [(-head_r * 1.3, -w / 2), (head_r * 1.3, -w / 2), (head_r * 1.3, w / 2), (-head_r * 1.3, w / 2)], depth * 2,
                         (0, 0, top_z), Matrix.Rotation(turn, 3, 'Z') @ X, Matrix.Rotation(turn, 3, 'Z') @ Y, Z, w0=-depth))
    elif drive == 'cross':
        w = head_r * 0.26; L = head_r * 0.82
        for a in (turn, turn + math.pi / 2):
            R = Matrix.Rotation(a, 3, 'Z')
            # tapered arm: wider at the top than at the bottom, as a driver leaves it
            c.append(G.prism('_c', [(-L, -w / 2), (L, -w / 2), (L, w / 2), (-L, w / 2)], depth * 2, (0, 0, top_z), R @ X, R @ Y, Z, w0=-depth))
    elif drive == 'hex':
        c.append(G.prism('_h', G.circle(head_r * 0.55, 6), depth * 2, (0, 0, top_z), X, Y, Z, w0=-depth))
    return c


def screw(name, d, length, head='pan', drive='slot', head_d=None, head_h=None, mat=None, thread=True, thread_len=None,
          pitch=None, segs=14, thread_segs=10, at=(0, 0, 0), axis=(0, 0, 1), ref=None, turn=0.0, point=True):
    """Machine or self-tapping screw. Origin at the underside of the head ('csk': at the top face, flush with the
    surface), +Z out of the hole, the shank runs to z = -length. head: pan, cheese, dome, hex, csk, socket, none.
    drive: slot, cross, hex, none. thread: a real helical ridge over thread_len from the tip (default the lower 60 %).
    About 150 triangles for the head and shank, plus about 4 * thread_segs per turn of thread."""
    r = d / 2
    hd = head_d or d * 1.9
    hh = head_h or d * 0.62
    hr = hd / 2
    pitch = pitch or d * 0.28
    parts = []
    tip = r * 0.55 if point else 0.0
    core_r = r - pitch * 0.32 if thread else r
    tl = min(length - 0.2 * MM, thread_len if thread_len is not None else length * 0.6) if thread else 0.0
    # head
    if head == 'pan':
        prof = [(0, 0), (0, hr), (hh * 0.45, hr), (hh * 0.8, hr * 0.86), (hh, hr * 0.6), (hh, 0)]
        top = hh
    elif head == 'cheese':
        c = hh * 0.16
        prof = [(0, 0), (0, hr), (hh - c, hr), (hh, hr - c), (hh, 0)]
        top = hh
    elif head == 'dome':
        prof = [(0, 0), (0, hr), (hh * 0.35, hr * 0.94), (hh * 0.7, hr * 0.72), (hh * 0.92, hr * 0.42), (hh, 0)]
        top = hh
    elif head == 'hex':
        c = hh * 0.2
        prof = [(0, 0), (0, hr), (hh - c, hr), (hh, hr * 0.84), (hh, 0)]
        top = hh
    elif head == 'socket':
        c = hh * 0.12
        prof = [(0, 0), (0, hr), (hh - c, hr), (hh, hr - c), (hh, 0)]
        top = hh
    elif head == 'csk':
        prof = [(-hh, 0), (-hh, r), (0, hr), (0, 0)]
        top = 0.0
    else:
        prof = None; top = 0.0
    if prof:
        hs = 6 if head == 'hex' else segs
        h = G.lathe(name + '_head', [(prof, False)], hs, O, Z, X, mat, phase=turn)
        cut = _drive_cutters(drive, hr if head != 'hex' else hr * 0.8, top, hh * 0.52, turn) if drive != 'none' else []
        if cut:
            G.boolean(h, cut)
        parts.append(h)
    # shank (profile runs down the -Z axis): plain part under the head, the core of the threaded part, the point
    s0 = hh if head == 'csk' else 0.0
    s_tt = length - tl                       # where the thread starts
    if tl < length - 1e-6:
        prof = [(s0, 0), (s0, r), (s_tt, r)]
        if thread:
            prof.append((s_tt + pitch * 0.3, core_r))
    else:
        prof = [(s0, 0), (s0, core_r)]
    prof += [(length - tip, core_r), (length, core_r * (0.45 if point else 1.0)), (length, 0)]
    z_thread_top = -s_tt
    sh = G.lathe(name + '_shank', [(prof, False)], segs, O, -Z, X, mat)
    parts.append(sh)
    if thread and tl > pitch * 1.5:
        parts.append(_thread_ridge(name + '_thread', core_r, r, pitch, -length + tip * 0.6, z_thread_top, thread_segs, mat))
    o = G.join(name, parts)
    G.shade(o, 38)
    return place(o, at, axis, ref)


def rivet(name, d, h=None, mat=None, segs=12, at=(0, 0, 0), axis=(0, 0, 1), ref=None):
    """Domed rivet head (about 100 triangles). Origin on the surface it sits on."""
    r = d / 2; h = h or d * 0.3
    prof = [(-0.15 * MM, 0), (-0.15 * MM, r), (0.4 * h, r * 0.93), (0.72 * h, r * 0.7), (0.93 * h, r * 0.4), (h, 0)]
    o = G.lathe(name, [(prof, False)], segs, O, Z, X, mat)
    return place(o, at, axis, ref)


def washer(name, d_in, d_out, t, mat=None, segs=20, at=(0, 0, 0), axis=(0, 0, 1), ref=None):
    """Flat washer lying on z = 0 (about 160 triangles at 20 segments)."""
    c = min(t * 0.25, (d_out - d_in) * 0.1)
    ri, ro = d_in / 2, d_out / 2
    prof = [(0, ri), (0, ro - c), (c, ro), (t - c, ro), (t, ro - c), (t, ri)]
    o = G.lathe(name, [(prof, True)], segs, O, Z, X, mat)
    return place(o, at, axis, ref)


def tube(name, d_out, d_in, length, mat=None, segs=20, at=(0, 0, 0), axis=(0, 0, 1), ref=None, chamfer=None):
    """Hollow cylinder from z = 0 to z = length (bush, sleeve, spacer, ferrule)."""
    ro, ri = d_out / 2, d_in / 2
    c = chamfer if chamfer is not None else min((ro - ri) * 0.25, length * 0.1)
    prof = [(0, ri), (0, ro - c), (c, ro), (length - c, ro), (length, ro - c), (length, ri)]
    o = G.lathe(name, [(prof, True)], segs, O, Z, X, mat)
    return place(o, at, axis, ref)


def nut(name, d, af, h, mat=None, at=(0, 0, 0), axis=(0, 0, 1), ref=None):
    """Hex nut lying on z = 0, across flats af, with its hole (about 120 triangles)."""
    rc = af / 2 / math.cos(math.radians(30))
    c = h * 0.18
    prof = [(0, d / 2), (0, rc * 0.9), (c, rc), (h - c, rc), (h, rc * 0.9), (h, d / 2)]
    o = G.lathe(name, [(prof, True)], 6, O, Z, X, mat, phase=math.radians(30))
    G.shade(o, 30)
    return place(o, at, axis, ref)


def circlip(name, d_shaft, width, t, gap_deg=42.0, mat=None, segs=22, ears=True, at=(0, 0, 0), axis=(0, 0, 1), ref=None):
    """External circlip lying on z = 0, opening toward +X, with two eared lugs and plier holes (about 250 triangles)."""
    ri = d_shaft / 2; ro = ri + width
    g = math.radians(gap_deg) / 2
    out_, in_ = [], []
    for k in range(segs + 1):
        a = g + (2 * math.pi - 2 * g) * k / segs
        w = 1.0 - 0.35 * math.cos(a)            # wider opposite the gap, as a real one is
        out_.append((math.cos(a) * (ri + width * min(1.0, w)), math.sin(a) * (ri + width * min(1.0, w))))
        in_.append((math.cos(a) * ri, math.sin(a) * ri))
    poly = out_ + in_[::-1]
    o = G.prism(name, poly, t, O, X, Y, Z, mat, w0=0.0)
    if ears:
        lugs = []
        for sgn in (1, -1):
            a = sgn * g
            c = Vector((math.cos(a) * (ri + width * 0.75), math.sin(a) * (ri + width * 0.75) + sgn * width * 0.15, 0))
            lug = G.prism(name + '_lug', G.circle(width * 0.85, 10), t, c, X, Y, Z, mat, w0=0.0)
            G.boolean(lug, [G.prism('_lh', G.circle(width * 0.32, 8), t * 3, c, X, Y, Z, w0=-t)])
            lugs.append(lug)
        o = G.join(name, [o] + lugs)
    G.shade(o, 30)
    return place(o, at, axis, ref)


def knurled_band(name, d, length, n=32, depth=None, mat=None, at=(0, 0, 0), axis=(0, 0, 1), ref=None, chamfer=None, d_in=0.0):
    """Straight-knurled band from z = 0 to z = length: n flutes as real geometry with chamfered ends
    (about 8 n triangles). d_in > 0 leaves a bore."""
    r = d / 2; depth = depth or d * 0.04
    c = chamfer if chamfer is not None else depth * 1.5
    rings = []
    for z, shrink in ((0.0, c), (c, 0.0), (length - c, 0.0), (length, c)):
        ring = []
        for k in range(2 * n):
            a = math.pi * k / n
            rr = (r if k % 2 == 0 else r - depth) - shrink
            ring.append(Vector((math.cos(a) * rr, math.sin(a) * rr, z)))
        rings.append(ring)
    o = G.loft(name, rings, mat, caps=(True, True))
    if d_in > 0:
        G.boolean(o, [G.cyl('_kb', (0, 0, -length), (0, 0, 2 * length), d_in / 2, 16)])
    G.shade(o, 25)
    return place(o, at, axis, ref)


def hinge(name, length, r_pin, r_knuckle, n=3, gap=0.15 * MM, mat=None, pin_mat=None, at=(0, 0, 0), axis=(0, 0, 1), ref=None,
          pin_proud=0.6 * MM, segs=14):
    """Hinge barrel on the Z axis from z = 0 to z = length: n knuckles alternating between two leaves, on a pin.
    Returns (knuckles_a, knuckles_b, pin): three objects in the same frame, to be joined to their leaves (a carries
    knuckles 0, 2, ..; b carries 1, 3, ..). The pin is a part of its own (it can be driven out)."""
    seg = length / n
    A, B = [], []
    for i in range(n):
        z0 = i * seg + (gap / 2 if i else 0.0); z1 = (i + 1) * seg - (gap / 2 if i < n - 1 else 0.0)
        c = min(seg * 0.08, (r_knuckle - r_pin) * 0.3)
        prof = [(z0, r_pin * 1.04), (z0, r_knuckle - c), (z0 + c, r_knuckle), (z1 - c, r_knuckle), (z1, r_knuckle - c), (z1, r_pin * 1.04)]
        k = G.lathe('%s_k%d' % (name, i), [(prof, True)], segs, O, Z, X, mat)
        (A if i % 2 == 0 else B).append(k)
    a = G.join(name + '_a', A)
    b = G.join(name + '_b', B) if B else None
    p = G.pin(name + '_pin', (0, 0, -pin_proud), (0, 0, length + pin_proud), r_pin, 10, pin_mat or mat)
    M = frame_matrix(at, axis, ref)
    for o in (a, b, p):
        if o:
            o.matrix_world = M
    bpy.context.view_layer.update()
    return a, b, p


def spring(name, length, d_coil, d_wire, turns, mat=None, per_turn=12, wire_segs=6, closed_ends=True, at=(0, 0, 0),
           axis=(0, 0, 1), ref=None, d_coil_end=None):
    """Compression spring on the Z axis from z = 0 to z = length (per_turn * wire_segs * 2 triangles per turn).
    closed_ends: the end coils lie flat, as a ground spring's do. d_coil_end: taper to another diameter."""
    r = d_coil / 2 - d_wire / 2
    r1 = (d_coil_end / 2 - d_wire / 2) if d_coil_end else r
    n = int(round(turns * per_turn))
    pts = []
    flat = per_turn if closed_ends else 0
    body = length - d_wire
    for k in range(n + 1):
        th = 2 * math.pi * k / per_turn
        if closed_ends and k < flat:
            z = d_wire / 2 + d_wire * 0.9 * (k / flat) * 0.5
        elif closed_ends and k > n - flat:
            z = d_wire / 2 + body - d_wire * 0.9 * ((n - k) / flat) * 0.5
        else:
            t = (k - flat) / max(1, n - 2 * flat)
            z = d_wire / 2 + d_wire * 0.45 + (body - d_wire * 0.9) * t if closed_ends else d_wire / 2 + body * k / n
        rr = r + (r1 - r) * k / n
        pts.append((math.cos(th) * rr, math.sin(th) * rr, z))
    o = G.tube_path(name, pts, d_wire / 2, wire_segs, mat)
    return place(o, at, axis, ref)


def wire(name, pts, d, mat=None, segs=6, smooth=1, closed=False):
    """Round wire along world points (already in place: the object keeps an identity frame; set its origin after)."""
    P = G.chaikin(pts, smooth, closed) if smooth else pts
    return G.tube_path(name, P, d / 2, segs, mat, closed=closed)


def lead(name, pts, d_sleeve, d_core, strip0=0.0, strip1=0.0, sleeve_mat=None, core_mat=None, segs=8, smooth=2, n=None):
    """Sleeved lead along world points with stripped ends. Returns (sleeve, core): the sleeve stops strip0 / strip1 short
    of the ends, the bare core shows there. Join them for a lead that stays whole; keep them apart for one that is
    stripped on the bench."""
    P = G.chaikin(pts, smooth, False) if smooth else [Vector(p) for p in pts]
    P = G.resample(P, n or max(8, len(P)))
    L = [0.0]
    for a, b in zip(P, P[1:]):
        L.append(L[-1] + (b - a).length)
    total = L[-1]
    sl = [p for p, l in zip(P, L) if strip0 - 1e-9 <= l <= total - strip1 + 1e-9]
    sleeve = G.tube_path(name + '_sleeve', sl, d_sleeve / 2, segs, sleeve_mat) if len(sl) >= 2 else None
    core = G.tube_path(name + '_core', P, d_core / 2, max(5, segs - 2), core_mat)
    return sleeve, core


def clip(name, width, t, r, mat=None, legs=2.0 * MM, open_deg=70.0, n=10, at=(0, 0, 0), axis=(0, 0, 1), ref=None):
    """Spring clip for a round lead or rod of radius r: an open sheet-metal C with flared lips, standing on z = 0 with its
    mouth toward +Z, the held axis along local Y (about 100 triangles)."""
    a0 = math.radians(90 + open_deg / 2); a1 = math.radians(450 - open_deg / 2)
    pts = []
    cz = r + t
    for k in range(n + 1):
        a = a0 + (a1 - a0) * k / n
        pts.append(Vector((math.cos(a) * (r + t / 2), 0, cz + math.sin(a) * (r + t / 2))))
    # flared lips
    d0 = (pts[0] - pts[1]).normalized(); d1 = (pts[-1] - pts[-2]).normalized()
    pts = [pts[0] + (d0 + Vector((-0.6, 0, 0.6))).normalized() * legs] + pts + [pts[-1] + (d1 + Vector((0.6, 0, 0.6))).normalized() * legs]
    o = G.band_path(name, pts, width, t, lambda p, tg: (p - Vector((0, 0, cz))) if (p - Vector((0, 0, cz))).length > 1e-6 else Z,
                    mat, closed=False, offset=-t / 2)
    G.shade(o, 40)
    return place(o, at, axis, ref)


def solder_blob(name, d, h, mat=None, segs=10, at=(0, 0, 0), axis=(0, 0, 1), ref=None):
    """Solder joint or pad: a low dome on z = 0 (about 80 triangles)."""
    r = d / 2
    prof = [(-0.05 * MM, 0), (-0.05 * MM, r), (h * 0.25, r * 0.92), (h * 0.6, r * 0.68), (h * 0.9, r * 0.35), (h, 0)]
    o = G.lathe(name, [(prof, False)], segs, O, Z, X, mat)
    return place(o, at, axis, ref)


def hole_cutter(d, depth, at, axis, segs=16, csk=0.0, over=0.2 * MM):
    """Cutter for a screw hole: opening at `at`, running `depth` against `axis` (axis points out of the hole, the way
    the screw comes out). csk: countersink diameter at the surface. Use with geo.boolean(target, [cutter])."""
    r = d / 2
    prof = [(over, 0), (over, max(r, csk / 2)), (0, max(r, csk / 2))]
    if csk > d:
        prof += [(-(csk - d) / 2, r)]
    prof += [(-depth, r), (-depth, 0)]
    ax = Vector(axis).normalized()
    return G.lathe('_holecut', [(prof, False)], segs, at, ax, (1, 0, 0) if abs(ax.x) < 0.9 else (0, 1, 0), None)
