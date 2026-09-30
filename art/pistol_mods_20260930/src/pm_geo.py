# Geometry helpers for the pistol mods (metric Blender pistol frame: forward -X, up +Z, right +Y, metres).
import bpy, bmesh, math
from mathutils import Vector, Matrix

MM = 0.001


def link(o, coll=None):
    (coll or bpy.context.scene.collection).objects.link(o)
    return o


def mesh_obj(name, verts, faces, mat=None, smooth=True, recalc=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.validate(clean_customdata=False)
    me.update()
    o = bpy.data.objects.new(name, me)
    link(o)
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    if recalc:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    if mat:
        me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = smooth
    return o


def frame(axis, ref):
    a = Vector(axis).normalized()
    e1 = Vector(ref) - a * a.dot(Vector(ref)); e1.normalize()
    e2 = a.cross(e1)
    return a, e1, e2


def lathe(name, loops, segs, origin, axis=(-1, 0, 0), ref=(0, 0, 1), mat=None, phase=0.0, arc=None):
    """Revolve profiles. loops: list of (points[(s,r) metres], closed). Open profiles whose end r==0 get a pole.
    arc: (a0, a1) radians for a partial revolve (open ring)."""
    a, e1, e2 = frame(axis, ref)
    O = Vector(origin)
    verts, faces = [], []
    full = arc is None
    nseg = segs if full else segs + 1
    ref_sign = None
    for pts, closed in loops:
        area = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))
        sg = 1 if area > 0 else -1
        if ref_sign is None:
            ref_sign = sg
        elif sg == ref_sign:
            pts = pts[::-1]
        n = len(pts)
        base = len(verts)
        for k in range(nseg):
            th = phase + (2 * math.pi * k / segs if full else arc[0] + (arc[1] - arc[0]) * k / segs)
            c, s = math.cos(th), math.sin(th)
            for (sv, r) in pts:
                verts.append(O + a * sv + (e1 * c + e2 * s) * r)
        kmax = segs if full else segs
        for k in range(kmax):
            k2 = (k + 1) % nseg if full else k + 1
            for i in range(n if closed else n - 1):
                i2 = (i + 1) % n
                faces.append((base + k * n + i, base + k * n + i2, base + k2 * n + i2, base + k2 * n + i))
    o = mesh_obj(name, verts, faces, mat, recalc=False)
    clean(o)
    return o


def signed_volume(bm):
    v = 0.0
    for f in bm.faces:
        vs = [x.co for x in f.verts]
        for i in range(1, len(vs) - 1):
            v += vs[0].dot(vs[i].cross(vs[i + 1])) / 6.0
    return v


def clean(o, dist=1e-6, recalc=False):
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=dist)
    if recalc:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    elif signed_volume(bm) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(o.data); bm.free()
    for p in o.data.polygons:
        p.use_smooth = True


def prism(name, poly, depth, origin, u, v, w, mat=None, w0=None):
    """Extrude a 2D polygon [(pu,pv)] along w from w0 to w0+depth (w0 default -depth/2), in frame (u,v,w) at origin."""
    u, v, w = Vector(u).normalized(), Vector(v).normalized(), Vector(w).normalized()
    O = Vector(origin)
    w0 = -depth / 2 if w0 is None else w0
    n = len(poly)
    verts = [O + u * p[0] + v * p[1] + w * w0 for p in poly] + [O + u * p[0] + v * p[1] + w * (w0 + depth) for p in poly]
    faces = [tuple(range(n))[::-1], tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    return mesh_obj(name, verts, faces, mat)


def rounded_rect(w, h, r, seg=4):
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for k in range(seg + 1):
            t = math.radians(a0 + 90 * k / seg)
            pts.append((cx + r * math.cos(t), cy + r * math.sin(t)))
    return pts


def stadium(length, width, seg=6):
    r = width / 2
    pts = []
    for k in range(seg + 1):
        t = -math.pi / 2 + math.pi * k / seg
        pts.append((length / 2 - r + r * math.cos(t), r * math.sin(t)))
    for k in range(seg + 1):
        t = math.pi / 2 + math.pi * k / seg
        pts.append((-length / 2 + r + r * math.cos(t), r * math.sin(t)))
    return pts


def circle(r, seg, phase=0.0):
    return [(r * math.cos(phase + 2 * math.pi * k / seg), r * math.sin(phase + 2 * math.pi * k / seg)) for k in range(seg)]


def box(name, center, size, rot=None, mat=None):
    sx, sy, sz = size
    poly = [(-sx / 2, -sy / 2), (sx / 2, -sy / 2), (sx / 2, sy / 2), (-sx / 2, sy / 2)]
    R = rot or Matrix.Identity(3)
    return prism(name, poly, sz, center, R.col[0], R.col[1], R.col[2], mat)


def tube_path(name, pts, radius, segs=8, mat=None, closed=False, twist_ref=(0, 0, 1)):
    """Sweep a circle along a polyline (parallel transport frames)."""
    P = [Vector(p) for p in pts]
    n = len(P)
    T = []
    for i in range(n):
        if closed:
            t = P[(i + 1) % n] - P[i - 1]
        else:
            t = (P[min(i + 1, n - 1)] - P[max(i - 1, 0)])
        T.append(t.normalized())
    ref = Vector(twist_ref)
    N0 = (ref - T[0] * T[0].dot(ref))
    if N0.length < 1e-6:
        N0 = Vector((1, 0, 0)) - T[0] * T[0].x
    N0.normalize()
    Ns = [N0]
    for i in range(1, n):
        Nprev = Ns[-1]
        Nn = Nprev - T[i] * T[i].dot(Nprev)
        Ns.append(Nn.normalized())
    verts, faces = [], []
    for i in range(n):
        B = T[i].cross(Ns[i])
        for k in range(segs):
            th = 2 * math.pi * k / segs
            verts.append(P[i] + (Ns[i] * math.cos(th) + B * math.sin(th)) * radius)
    rng = n if closed else n - 1
    for i in range(rng):
        i2 = (i + 1) % n
        for k in range(segs):
            k2 = (k + 1) % segs
            faces.append((i * segs + k, i * segs + k2, i2 * segs + k2, i2 * segs + k))
    if not closed:
        faces.append(tuple(range(segs))[::-1])
        faces.append(tuple(range((n - 1) * segs, n * segs)))
    return mesh_obj(name, verts, faces, mat)


def band_path(name, pts, width, thick, normal_fn, mat=None, closed=True, offset=0.0):
    """Flat strap swept along a polyline: cross-section width along side vector, thickness along normal_fn(p, t)."""
    P = [Vector(p) for p in pts]
    n = len(P)
    verts, faces = [], []
    for i in range(n):
        t = (P[(i + 1) % n] - P[i - 1]) if closed else (P[min(i + 1, n - 1)] - P[max(i - 1, 0)])
        t.normalize()
        nn = Vector(normal_fn(P[i], t)); nn = (nn - t * t.dot(nn)).normalized()
        side = t.cross(nn)
        for (a, b) in ((-width / 2, offset), (width / 2, offset), (width / 2, offset + thick), (-width / 2, offset + thick)):
            verts.append(P[i] + side * a + nn * b)
    rng = n if closed else n - 1
    for i in range(rng):
        i2 = (i + 1) % n
        for k in range(4):
            k2 = (k + 1) % 4
            faces.append((i * 4 + k, i * 4 + k2, i2 * 4 + k2, i2 * 4 + k))
    if not closed:
        faces.append((3, 2, 1, 0)); faces.append(tuple(range((n - 1) * 4, n * 4)))
    return mesh_obj(name, verts, faces, mat)


def boolean(target, cutters, op='DIFFERENCE'):
    for c in cutters:
        m = target.modifiers.new('bool', 'BOOLEAN')
        m.operation = op
        m.object = c
        try:
            m.solver = 'EXACT'
        except Exception:
            pass
        apply_mods(target)
        bpy.data.objects.remove(c, do_unlink=True)
    clean(target)
    return target


def apply_mods(o):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = o.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
    old = o.data
    o.modifiers.clear()
    o.data = me
    me.name = o.name
    if old.users == 0:
        bpy.data.meshes.remove(old)


def bevel(o, width=0.3 * MM, segs=2, angle=30, weighted=True, apply=True, clamp=True):
    m = o.modifiers.new('bev', 'BEVEL')
    m.width = width
    m.segments = segs
    m.limit_method = 'ANGLE'
    m.angle_limit = math.radians(angle)
    m.use_clamp_overlap = clamp
    m.harden_normals = False
    m.miter_outer = 'MITER_ARC'
    if weighted:
        w = o.modifiers.new('wn', 'WEIGHTED_NORMAL')
        w.keep_sharp = True
        w.mode = 'FACE_AREA'
        w.weight = 50
    if apply:
        apply_mods(o)
    return o


def sharp_by_angle(o, deg=40):
    try:
        o.data.set_sharp_from_angle(angle=math.radians(deg))
    except Exception:
        pass


def join(name, objs):
    objs = [o for o in objs if o]
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    o.name = name
    o.data.name = name
    return o


def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


def transform_obj(o, M):
    o.data.transform(M)
    o.data.update()
