# tl_kit.py: model-tools helpers (21 Nov 2026), on top of mbk and the programme kit. A new file so that mbk.py, which
# the fixtures family imports too, keeps its behaviour. Geometry builders return linked mesh objects in the tool's own
# frame (metres, the tool along +Y with its working end at +Y, Z up), identity object matrix.
import math, json
import bpy, bmesh
from mathutils import Vector, Matrix, Euler, noise
import mbk
from mbk import G, MT, CT, AP, RG, BK, MM, X, Y, Z, O, T, R4, join, turned, ring_prof, extrude_z


# ====================================================================== material frames
def frame_mat(m, M):
    """Make a material read its object coordinates in the frame M (4x4, object space): every user of the texture
    coordinate 'Object' output sees M^-1 @ p. Used after a tool is tilted to its rest on the bench, so that knurls,
    wraps and bands keep the axes the tool was modelled on."""
    nt = m.node_tree
    tc = next(n for n in nt.nodes if n.bl_idname == 'ShaderNodeTexCoord')
    links = [l for l in nt.links if l.from_node == tc and l.from_socket.name == 'Object']
    Mi = Matrix(M).inverted()
    loc, rot, sc = Mi.decompose()
    mp = nt.nodes.new('ShaderNodeMapping'); mp.vector_type = 'POINT'
    mp.inputs['Location'].default_value = loc
    mp.inputs['Rotation'].default_value = rot.to_euler('XYZ')
    mp.inputs['Scale'].default_value = sc
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    for l in links:
        to = l.to_socket
        nt.links.remove(l)
        nt.links.new(mp.outputs['Vector'], to)
    return m


def frame_mats(objs, M):
    seen = set()
    for o in objs:
        for s in o.material_slots:
            if s.material and s.material.name not in seen and not s.material.get('passthrough', 0):
                seen.add(s.material.name)
                frame_mat(s.material, M)


# ====================================================================== sections and sweeps
def sup(w, h, n=12, p=4.0, phase=0.0):
    """Superellipse outline, w wide and h high (2D points, counter-clockwise from +u)."""
    out = []
    for k in range(n):
        a = phase + 2 * math.pi * k / n
        c, s = math.cos(a), math.sin(a)
        out.append((w / 2 * math.copysign(abs(c) ** (2.0 / p), c), h / 2 * math.copysign(abs(s) ** (2.0 / p), s)))
    return out


def frames(pts, up=(0, 0, 1)):
    """Tangent, side (width) and up (thickness) vectors at each point of a polyline. The up vector is `up` made
    perpendicular to the tangent (a handle lying flat keeps its thickness vertical)."""
    P = [Vector(p) for p in pts]
    n = len(P)
    out = []
    for i in range(n):
        t = (P[min(i + 1, n - 1)] - P[max(i - 1, 0)]).normalized()
        u = Vector(up) - t * t.dot(Vector(up))
        if u.length < 1e-6:
            u = t.orthogonal()
        u.normalize()
        s = t.cross(u)
        out.append((P[i], t, s, u))
    return out


def loft_path(name, pts, sec_fn, mat=None, caps=(True, True), up=(0, 0, 1), smooth=True):
    """Loft a section along a path. sec_fn(i, f) -> list of 2D points (side, up), f = 0..1 along the path by length."""
    F = frames(pts, up)
    L = [0.0]
    for a, b in zip(pts, pts[1:]):
        L.append(L[-1] + (Vector(b) - Vector(a)).length)
    rings = []
    for i, (p, t, s, u) in enumerate(F):
        sec = sec_fn(i, L[i] / L[-1] if L[-1] > 0 else 0.0)
        rings.append([p + s * a + u * b for (a, b) in sec])
    return G.loft(name, rings, mat, caps=caps, smooth=smooth)


def sweep_round(name, pts, radius, segs=10, mat=None, caps=(True, True), up=(0, 0, 1)):
    """A round section of radius(f) (or a number) along a path."""
    rf = radius if callable(radius) else (lambda f: radius)
    return loft_path(name, pts, lambda i, f: [(rf(f) * math.cos(2 * math.pi * k / segs), rf(f) * math.sin(2 * math.pi * k / segs)) for k in range(segs)],
                     mat, caps, up)


def lathe_y(name, prof, segs=24, mat=None, y0=0.0, x=0.0, z=0.0, phase=0.0):
    """Turned part along +Y: prof [(y, r)] with y measured from y0."""
    return turned(name, prof, segs, mat, axis=Y, origin=(x, y0, z), phase=phase)


def placed(o, M):
    """Bake a 4x4 into the mesh (object stays at identity)."""
    o.data.transform(Matrix(M)); o.data.update()
    o.matrix_world = Matrix.Identity(4)
    return o


def baked(o):
    """Bake the object's own matrix into its mesh (for kit builders that place with matrix_world)."""
    bpy.context.view_layer.update()
    return placed(o, o.matrix_world.copy())


def arc_pts(c, r, a0, a1, n, plane='XY', z=0.0):
    out = []
    for k in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * k / n)
        if plane == 'XY':
            out.append(Vector((c[0] + r * math.cos(a), c[1] + r * math.sin(a), z)))
        elif plane == 'YZ':
            out.append(Vector((z, c[0] + r * math.cos(a), c[1] + r * math.sin(a))))
    return out


def smooth_path(pts, it=3):
    return G.chaikin(pts, it, closed=False)


# ====================================================================== scissor-type tools (v2)
def scissor_half(tag, jaw_poly, jaw_half, handle_path, handle_w, handle_t, th, rj, steel, jaw_mat=None, boss_mat=None,
                 butt_round=True, handle_up=None):
    """One forged half lying flat (Z thickness, centred on z = th/2), the pivot at the origin, its jaw on the -X side
    above (y > 0), its handle running down the path. jaw_poly: outline in XY (wedge whose half thickness is
    jaw_half(x, y)); handle_path: centre line of the handle from inside the boss to the butt; handle_w(f), handle_t(f):
    width and thickness along it (f = 0..1). Returns the pieces (boss, jaw, handle) as separate objects."""
    bs = extrude_z(tag + '_bs', G.circle(rj - 0.0004, 32), 0.0, th, boss_mat or steel)
    jw = wedge(tag + '_jw', jaw_poly, th / 2, jaw_half, jaw_mat or steel)
    zc = th / 2
    P = [Vector((p[0], p[1], zc)) for p in handle_path]

    def sec(i, f):
        w = handle_w(f); t = handle_t(f)
        if butt_round and f > 0.97:
            k = (f - 0.97) / 0.03
            w *= math.sqrt(max(0.05, 1 - k * k * 0.85)); t *= math.sqrt(max(0.05, 1 - k * k * 0.85))
        return sup(w, t, 14, 3.2)
    hd = loft_path(tag + '_hd', P, sec, steel)
    return bs, jw, hd


def wedge(name, poly, zmid, half_fn, mat):
    """A prism whose half thickness varies over the outline (half_fn(x, y))."""
    n = len(poly)
    verts = [(x, y, zmid - half_fn(x, y)) for x, y in poly] + [(x, y, zmid + half_fn(x, y)) for x, y in poly]
    faces = [tuple(range(n))[::-1], tuple(range(n, 2 * n))] + [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    return G.mesh_obj(name, verts, faces, mat, recalc=True)


def lap_cut(pieces, th, rj, lower, gap=0.00012, rivet_hole=None, bevel=(0.0006, 0.0006, 0.0008)):
    """Cut the lap joint: inside the disc of radius rj the lower half keeps z < th/2, the upper half z > th/2."""
    d = 0.0002
    out = []
    for o, bw in zip(pieces, bevel):
        if bw:
            G.bevel(o, bw, 1)
        if lower:
            cut = [G.cyl('_cc', (0, 0, th / 2 - 0.00006), (0, 0, th + d + 0.004), rj + gap, 40)]
        else:
            cut = [G.cyl('_cc', (0, 0, -d - 0.004), (0, 0, th / 2 + 0.00006), rj + gap, 40)]
        if rivet_hole and o is pieces[0]:
            cut.append(G.cyl('_ch', (0, 0, -0.01), (0, 0, 0.02), rivet_hole, 16))
        o = G.boolean(o, cut)
        out.append(o)
    return out


# ====================================================================== small mechanical parts
def bevel_gear(name, r_out, r_in, n, h, mat, face_up=True, tooth_h=None):
    """A ring of n teeth standing on a disc's face (a face or crown gear as the eggbeater drill's wheel carries), as
    geometry: the disc z 0..h, teeth from z = 0 down to -tooth_h when face_up is False (teeth below)."""
    th = tooth_h or (r_out - r_in) * 0.45
    teeth = []
    for k in range(n):
        a = 2 * math.pi * k / n
        w = 2 * math.pi * (r_in + r_out) / 2 / n * 0.46
        c = Vector((math.cos(a), math.sin(a), 0)); s = Vector((-math.sin(a), math.cos(a), 0))
        z0, z1 = (0.0, -th) if not face_up else (h, h + th)
        pts = []
        for rr, ww in ((r_in, w * 0.9), (r_out, w)):
            pts += [c * rr + s * (-ww / 2), c * rr + s * (ww / 2)]
        # a tooth: base quad at z0, top ridge narrower at z1
        b0, b1, b2, b3 = pts[0], pts[1], pts[3], pts[2]
        top = [b0 * 1.0 + s * (ww * 0.25), b1 - s * (ww * 0.25), b2 - s * (ww * 0.25), b3 + s * (ww * 0.25)]
        v = [b0 + Vector((0, 0, z0)), b1 + Vector((0, 0, z0)), b2 + Vector((0, 0, z0)), b3 + Vector((0, 0, z0)),
             top[0] + Vector((0, 0, z1)), top[1] + Vector((0, 0, z1)), top[2] + Vector((0, 0, z1)), top[3] + Vector((0, 0, z1))]
        f = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
        teeth.append(G.mesh_obj('%s_t%d' % (name, k), v, f, mat, smooth=False))
    return join(name, teeth)


def spur_pinion(name, r_root, r_tip, n, length, mat, axis=Y, origin=O):
    """A small toothed pinion along `axis` (teeth as a star prism with flat tips)."""
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        for da, rr in ((-0.30, r_root), (-0.16, r_tip), (0.16, r_tip), (0.30, r_root)):
            aa = a + da * 2 * math.pi / n
            pts.append((rr * math.cos(aa), rr * math.sin(aa)))
    ax = Vector(axis).normalized()
    ref = Z if abs(ax.z) < 0.9 else X
    e1 = (ref - ax * ax.dot(ref)).normalized(); e2 = ax.cross(e1)
    o = G.prism(name, pts, length, Vector(origin), e1, e2, ax, mat, w0=0.0)
    G.bevel(o, 0.00015, 1, 40)
    return o


def croc_clip(name, mat, length=0.032, width=0.0075, open_deg=6.0):
    """A crocodile clip along +Y in its own frame, its mouth at y = length. Two pressed-steel U channels facing each other,
    their walls serrated along the mouth, the tails flared apart for the fingers; a pivot pin and a coil spring."""
    parts = []
    L = length
    n = 22
    for sg in (1, -1):
        ys = [L * k / n for k in range(n + 1)]
        path = []
        for y in ys:
            t = max(0.0, (0.32 * L - y) / (0.32 * L))
            path.append(Vector((0, y, sg * (0.0007 + 0.0026 * t * t + (math.radians(open_deg / 2) * (y - 0.28 * L) if y > 0.28 * L else 0.0)))))

        def sec(i, f, sg=sg):
            y = ys[i]
            w = width * (1.0 - 0.62 * max(0.0, (y / L - 0.40)) / 0.60)
            wall = 0.0022 * (1.0 - 0.3 * y / L)
            if y > 0.5 * L:
                ph = (y / 0.0014) % 1.0
                wall += 0.0007 * (1.0 - abs(ph - 0.5) * 2.0)
            tk = 0.00045
            # U section opening toward the other jaw (-sg along z): base at 0, walls reaching -sg * wall
            return [(w / 2, 0.0), (w / 2, -sg * wall), (w / 2 - tk, -sg * wall), (w / 2 - tk, -sg * tk), (-w / 2 + tk, -sg * tk),
                    (-w / 2 + tk, -sg * wall), (-w / 2, -sg * wall), (-w / 2, 0.0)]
        ch = loft_path('%s_c%d' % (name, sg), path, sec, mat, up=(0, 0, 1))
        parts.append(ch)
    pin = G.cyl(name + '_pin', (-width / 2 - 0.0006, L * 0.30, 0), (width / 2 + 0.0006, L * 0.30, 0), 0.0007, 8, mat)
    spring = AP.spring(name + '_sp', 0.0060, 0.0036, 0.0005, 4, mat, per_turn=10, wire_segs=5, at=(-0.0030, L * 0.30, 0), axis=(1, 0, 0))
    baked(spring)
    return join(name, parts + [pin, spring])


def tuft(name, base, axis, length, r0, mat, splay=0.25, seed=0, segs=6, bend=0.18):
    """A tuft of bristles: a tapered, slightly splayed and bent cone from `base` along `axis` (the tips frayed)."""
    ax = Vector(axis).normalized()
    pts = []
    n = 5
    bend = noise.noise_vector(Vector((seed * 1.7, seed * 0.3, 2.1))) * bend
    for k in range(n + 1):
        f = k / n
        pts.append(Vector(base) + (ax + bend * f * f) .normalized() * length * f)
    return sweep_round(name, pts, lambda f: r0 * (1.0 + splay * f), segs, mat, caps=(True, True))


# ====================================================================== the contract, as the old tools used it
FAM = 'tools'


def tool(o, pid, label, verbs, tags, material='steel', mass='light', parent=None, item=None, steps=(), note=None, **kw):
    kw.setdefault('loose', parent is None)
    return CT.tool(o, FAM, pid, label, verbs, tags, parent=parent, material=material, mass=mass, item=item, steps=list(steps), note=note, **kw)


def sub(o, pid, label, parent, material, mass='tiny', note=None):
    return CT.part(o, FAM, pid, label, kind='part', parent=parent, material=material, mass=mass, loose=True,
                   note=note or 'fixed sub-part of %s.%s, never separated on the bench' % (FAM, parent))


def settle(pieces, about=None, extra=()):
    """Tilt and lift the pieces (and `extra`) onto z = 0 the way they lie on a bench. Returns the 4x4."""
    Mr = mbk.rest_tilt(pieces, about)
    for o in list(pieces) + list(extra):
        o.data.transform(Mr); o.data.update()
    return Mr
