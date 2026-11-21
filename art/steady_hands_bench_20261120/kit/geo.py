# kit/geo.py: geometry helpers (Blender 5.2, metres, Z up). Copied from art/pistol_mods_20260930/src/pm_geo.py
# (our own, 30 Sep 2026) and extended for the Steady Hands bench programme (20 Nov 2026). The functions below the
# line "additions" are new; `loft`, `chaikin` and `pin` follow the shapes of AnyMachine's hardsurface/guns helpers
# (MIT, see am_parts.py for the notice). Every builder returns a linked mesh object with outward normals.
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


def _volume(o):
    bm = bmesh.new(); bm.from_mesh(o.data)
    v = abs(signed_volume(bm)); bm.free()
    return v


def boolean(target, cutters, op='DIFFERENCE', check=True):
    """Apply cutters to target one after another (DIFFERENCE, UNION or INTERSECT) and remove them.
    Each result is checked against what the volumes allow, because the EXACT solver has returned the intersection in
    place of a difference on a bevelled target (20 Nov 2026): if the result is impossible the cut is tried again with
    the MANIFOLD and then the FLOAT solver, and a RuntimeError is raised if none gives a possible result."""
    for c in cutters:
        vb = _volume(target); vc = _volume(c)
        np0 = len(target.data.polygons); sc0 = solid_check(target)
        tol = 1e-13 + 2e-4 * max(vb, vc)
        lo, hi = {'DIFFERENCE': (vb - vc - tol, vb + tol), 'UNION': (max(vb, vc) - tol, vb + vc + tol),
                  'INTERSECT': (-tol, min(vb, vc) + tol)}[op]
        backup = target.data.copy()
        ok = False
        tried = []
        for solver in ('EXACT', 'MANIFOLD', 'FLOAT'):
            m = target.modifiers.new('bool', 'BOOLEAN')
            m.operation = op
            m.object = c
            try:
                m.solver = solver
            except Exception:
                target.modifiers.remove(m)
                continue
            apply_mods(target)
            va = _volume(target)
            tried.append((solver, va))
            # a fallback solver that refuses the mesh leaves it untouched, which the volume test alone would pass
            noop = bool(tried[:-1]) and len(target.data.polygons) == np0 and abs(va - vb) <= 1e-15 + 1e-9 * vb
            if not check or (lo <= va <= hi and len(target.data.polygons) > 0 and not noop):
                ok = True
                break
            target.data = backup.copy()
        if not ok:
            raise RuntimeError('boolean %s of %s on %s gave an impossible volume with every solver: before %.4g, cutter %.4g, got %s'
                               % (op, c.name, target.name, vb, vc, tried))
        if tried and tried[-1][0] != 'EXACT':
            print('[geo.boolean] %s of %s on %s: EXACT was wrong (%.4g outside %.4g..%.4g), used %s' % (op, c.name, target.name, tried[0][1], lo, hi, tried[-1][0]), flush=True)
        sc1 = solid_check(target)
        if sc1 != (0, 0) and sc1 != sc0:
            print('[geo.boolean] after %s of %s the target %s is not a closed solid: %d open edges, %d non-manifold (before: %d, %d)'
                  % (op, c.name, target.name, sc1[0], sc1[1], sc0[0], sc0[1]), flush=True)
        bpy.data.meshes.remove(backup)
        bpy.data.objects.remove(c, do_unlink=True)
    clean(target)
    heal(target)
    return target


def heal(o, dist=4e-6, sides=8):
    """Weld near-coincident vertices and close the pin-holes a boolean can leave, so the part stays a closed solid."""
    bm = bmesh.new(); bm.from_mesh(o.data)
    if any(e.is_boundary for e in bm.edges):
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)
        bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=dist)
        edges = [e for e in bm.edges if e.is_boundary]
        if edges:
            bmesh.ops.holes_fill(bm, edges=edges, sides=sides)
        bm.to_mesh(o.data)
    bm.free()
    return o


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


def _bevel_clamp_warning(o, width, angle):
    """With clamp on, Blender limits the bevel of the WHOLE part so that no two bevels overlap: one short edge at a
    bevelled corner shrinks it everywhere (20 Nov: a 0.3 mm bevel came to nothing round a plate because one edge
    between two eased corners was 0.3 mm long). Say so when that is about to happen."""
    bm = bmesh.new(); bm.from_mesh(o.data)
    bm.normal_update()
    lim = math.radians(angle)
    worst = None
    for e in bm.edges:
        if len(e.link_faces) != 2 or e.link_faces[0].normal.angle(e.link_faces[1].normal, 0.0) < lim:
            continue
        for v in e.verts:
            for e2 in v.link_edges:
                L = e2.calc_length()
                if worst is None or L < worst:
                    worst = L
    bm.free()
    if worst is not None and worst < 2.0 * width:
        print('[geo.bevel] %s: the shortest edge at a bevelled corner is %.2f mm, under twice the bevel width (%.2f mm): with '
              'clamp=True the bevel shrinks over the whole part, to nothing at worst. Pass clamp=False or weld the short edge'
              % (o.name, worst / MM, width / MM), flush=True)


def bevel(o, width=0.3 * MM, segs=2, angle=30, weighted=True, apply=True, clamp=True):
    """Bevel the edges sharper than `angle`. clamp=True (the default, unchanged) stops bevels overlapping but can shrink
    them over the whole part: a line is printed when a short edge will do that; clamp=False keeps the width."""
    if clamp:
        _bevel_clamp_warning(o, width, angle)
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


# ====================================================================== additions (20 Nov 2026)
def chaikin(pts, it=2, closed=True):
    """Corner-cutting smoothing of a 2D or 3D polygon."""
    pts = [Vector(p) for p in pts]
    for _ in range(it):
        out = []
        n = len(pts)
        for i in range(n if closed else n - 1):
            p, q = pts[i], pts[(i + 1) % n]
            out.append(p * 0.75 + q * 0.25)
            out.append(p * 0.25 + q * 0.75)
        if not closed:
            out = [pts[0]] + out + [pts[-1]]
        pts = out
    return pts


def bezier(p0, p1, p2, p3, n=12):
    p0, p1, p2, p3 = (Vector(p) for p in (p0, p1, p2, p3))
    out = []
    for i in range(n + 1):
        t = i / n; s = 1 - t
        out.append(p0 * s ** 3 + p1 * 3 * s * s * t + p2 * 3 * s * t * t + p3 * t ** 3)
    return out


def resample(pts, n):
    """n points evenly spaced along a polyline."""
    P = [Vector(p) for p in pts]
    L = [0.0]
    for a, b in zip(P, P[1:]):
        L.append(L[-1] + (b - a).length)
    out = []
    for k in range(n):
        d = L[-1] * k / (n - 1)
        i = max(j for j in range(len(L)) if L[j] <= d + 1e-12)
        i = min(i, len(P) - 2)
        seg = L[i + 1] - L[i]
        t = 0.0 if seg < 1e-12 else (d - L[i]) / seg
        out.append(P[i].lerp(P[i + 1], t))
    return out


def helix(origin, axis, ref, radius, pitch, turns, per_turn=16, phase=0.0, r1=None):
    """Points of a helix about axis from origin. r1: end radius (taper)."""
    a, e1, e2 = frame(axis, ref)
    O = Vector(origin)
    n = int(round(turns * per_turn))
    out = []
    for k in range(n + 1):
        th = phase + 2 * math.pi * k / per_turn
        r = radius if r1 is None else radius + (r1 - radius) * k / n
        out.append(O + a * (pitch * k / per_turn) + (e1 * math.cos(th) + e2 * math.sin(th)) * r)
    return out


def loft(name, sections, mat=None, caps=(True, True), closed=True, smooth=True):
    """Skin rings of equal point count (each a list of 3D points, in order along the part)."""
    n = len(sections[0])
    verts = [Vector(p) for s in sections for p in s]
    faces = []
    for k in range(len(sections) - 1):
        for i in range(n if closed else n - 1):
            j = (i + 1) % n
            faces.append((k * n + i, k * n + j, (k + 1) * n + j, (k + 1) * n + i))
    if caps[0]:
        faces.append(tuple(range(n))[::-1])
    if caps[1]:
        faces.append(tuple(range((len(sections) - 1) * n, len(sections) * n)))
    o = mesh_obj(name, verts, faces, mat, smooth=smooth, recalc=True)
    clean(o)
    return o


def cyl(name, p0, p1, r, segs=16, mat=None, r1=None, chamfer=0.0, ref=None):
    """Cylinder (or cone) between two points, optional chamfered ends."""
    p0, p1 = Vector(p0), Vector(p1)
    ax = p1 - p0; L = ax.length
    r1 = r if r1 is None else r1
    c = min(chamfer, L * 0.45)
    prof = [(0, 0), (0, r - c), (c, r), (L - c, r1), (L, r1 - c), (L, 0)] if c > 0 else [(0, 0), (0, r), (L, r1), (L, 0)]
    if ref is None:
        ref = (0, 0, 1) if abs(ax.normalized().z) < 0.9 else (1, 0, 0)
    return lathe(name, [(prof, False)], segs, p0, ax, ref, mat)


def pin(name, p0, p1, r, segs=12, mat=None, chamfer=None):
    """Cross pin with chamfered ends (AnyMachine's xpin)."""
    return cyl(name, p0, p1, r, segs, mat, chamfer=r * 0.22 if chamfer is None else chamfer)


def ring(name, origin, axis, R, r, segs=24, tube_segs=8, mat=None, ref=None, arc=None):
    """Torus (wire ring, O-ring) about axis: major radius R, wire radius r. arc=(a0, a1) for an open ring."""
    prof = [(r * math.sin(2 * math.pi * k / tube_segs), R - r * math.cos(2 * math.pi * k / tube_segs)) for k in range(tube_segs)]
    if ref is None:
        ref = (0, 0, 1) if abs(Vector(axis).normalized().z) < 0.9 else (1, 0, 0)
    o = lathe(name, [(prof, True)], segs, origin, axis, ref, mat, arc=arc)
    if arc is not None:
        fill_holes(o)
    return o


def fill_holes(o, sides=0):
    bm = bmesh.new(); bm.from_mesh(o.data)
    edges = [e for e in bm.edges if e.is_boundary]
    if edges:
        bmesh.ops.holes_fill(bm, edges=edges, sides=sides)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(o.data); bm.free()
    return o


def plate(name, outline, thick, origin, u, v, w, holes=(), mat=None, w0=None, bevel_w=0.0, hole_segs=16, slots=()):
    """Flat plate: 2D outline extruded along w, with round holes [(cu, cv, r)] and slots [(cu, cv, length, width, angle)]
    cut through. bevel_w: edge break."""
    o = prism(name, outline, thick, origin, u, v, w, mat, w0=w0)
    cutters = []
    w0c = (-thick / 2 if w0 is None else w0) - thick
    for (cu, cv, r) in holes:
        cutters.append(prism('_hole', circle(r, hole_segs), thick * 3, Vector(origin) + Vector(u).normalized() * cu + Vector(v).normalized() * cv,
                             u, v, w, w0=w0c))
    for (cu, cv, ln, wd, ang) in slots:
        ca, sa = math.cos(ang), math.sin(ang)
        uu = Vector(u).normalized() * ca + Vector(v).normalized() * sa
        vv = Vector(w).normalized().cross(uu)
        cutters.append(prism('_slot', stadium(ln, wd, 6), thick * 3, Vector(origin) + Vector(u).normalized() * cu + Vector(v).normalized() * cv,
                             uu, vv, w, w0=w0c))
    if cutters:
        boolean(o, cutters)
    if bevel_w > 0:
        bevel(o, bevel_w, 1, 30)
    return o


def duplicate(o, name=None):
    d = o.copy(); d.data = o.data.copy()
    link(d)
    if name:
        d.name = name; d.data.name = name
    return d


def mirror(o, axis=1, about=0.0):
    """Mirror the mesh in place across the plane <axis> = about (world axes; object must have an identity matrix)."""
    S = Matrix.Identity(4); S[axis][axis] = -1; S[axis][3] = 2 * about
    o.data.transform(S)
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.reverse_faces(bm, faces=bm.faces); bm.to_mesh(o.data); bm.free()
    o.data.update()
    return o


def set_origin(o, point):
    """Move the object's origin to a world point without moving the mesh."""
    p = Vector(point)
    mw = o.matrix_world.copy()
    local = mw.inverted() @ p
    o.data.transform(Matrix.Translation(-local))
    o.matrix_world = mw @ Matrix.Translation(local)
    o.data.update()
    return o


def set_frame(o, M):
    """Give the object the world frame M (4x4: origin and axes) without moving the mesh."""
    M = Matrix(M)
    o.data.transform(M.inverted() @ o.matrix_world)
    o.matrix_world = M
    o.data.update()
    return o


def clear_custom_normals(o):
    """Drop custom split normals (a boolean after a weighted-normal pass leaves them wrong on the new faces)."""
    me = o.data
    try:
        a = me.attributes.get('custom_normal')
        if a is not None:
            me.attributes.remove(a)
    except Exception:
        pass
    try:
        with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o]):
            bpy.ops.mesh.customdata_custom_splitnormals_clear()
    except Exception:
        pass
    me.update()


def shade(o, angle=40, weighted=False):
    """Smooth shading with edges sharper than `angle` kept hard. Always call it last on a part: it throws away any
    custom normals first. weighted: face-area weighted normals, so large flat faces stay flat next to their bevels."""
    clear_custom_normals(o)
    for p in o.data.polygons:
        p.use_smooth = True
    sharp_by_angle(o, angle)
    if weighted:
        w = o.modifiers.new('wn', 'WEIGHTED_NORMAL'); w.keep_sharp = True; w.mode = 'FACE_AREA'; w.weight = 50
        apply_mods(o)
    return o


def displace(o, fn):
    """Move every vertex: fn(co) -> new co (object space). For dents, bends, sag."""
    for v in o.data.vertices:
        v.co = fn(v.co.copy())
    o.data.update()
    return o


def subdivide(o, cuts=1):
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=cuts, use_grid_fill=True)
    bm.to_mesh(o.data); bm.free()
    return o


def solid_check(o):
    """(boundary edges, non-manifold edges): both 0 for a closed solid (booleans and the sweep's inside tests need it)."""
    bm = bmesh.new(); bm.from_mesh(o.data)
    b = sum(1 for e in bm.edges if e.is_boundary); nm = sum(1 for e in bm.edges if not e.is_manifold and not e.is_boundary)
    bm.free()
    return b, nm


def _folded_by_beauty(bm):
    """Indices of the faces that BEAUTY triangulation folds: at least one of their triangles faces against the face."""
    cp = bm.copy()
    cp.normal_update()
    cp.faces.ensure_lookup_table(); cp.verts.ensure_lookup_table()
    cp.faces.index_update(); cp.verts.index_update()
    big = [f for f in cp.faces if len(f.verts) > 3]
    if not big:
        cp.free(); return []
    normal = {}; of_vert = {}
    for f in big:
        normal[f.index] = f.normal.copy()
        for v in f.verts:
            of_vert.setdefault(v.index, set()).add(f.index)
    sets = {f.index: frozenset(v.index for v in f.verts) for f in big}
    bmesh.ops.triangulate(cp, faces=big, quad_method='BEAUTY', ngon_method='BEAUTY')
    bad = set()
    for t in cp.faces:
        if len(t.verts) != 3 or t.calc_area() < 1e-14:
            continue
        vi = [v.index for v in t.verts]
        cand = of_vert.get(vi[0], set()) & of_vert.get(vi[1], set()) & of_vert.get(vi[2], set())
        cand = [c for c in cand if set(vi) <= sets[c]]
        c0, c1, c2 = [v.co for v in t.verts]
        tn = (c1 - c0).cross(c2 - c0)              # by the winding (a new face's stored normal is not always set)
        if tn.length < 1e-18:
            continue
        tn.normalize()
        if cand and all(tn.dot(normal[c]) < -1e-4 for c in cand):
            bad.update(cand)
    cp.free()
    return sorted(bad)


def triangulate(o):
    """Triangulate in place (n-gons stop the exporter computing tangents; the normal bake must see the same triangles).
    BEAUTY, as before, except for a face BEAUTY would fold (a triangle facing against its face, seen as a hole from
    one side: it happened on a many-cornered plate face, 20 Nov): such a face is ear-clipped."""
    bm = bmesh.new(); bm.from_mesh(o.data)
    bm.faces.ensure_lookup_table(); bm.faces.index_update(); bm.verts.index_update()
    bad = _folded_by_beauty(bm)
    if bad:
        bm.faces.ensure_lookup_table()
        bmesh.ops.triangulate(bm, faces=[bm.faces[i] for i in bad], quad_method='FIXED', ngon_method='EAR_CLIP')
        print('[geo.triangulate] %s: %d face(s) ear-clipped, BEAUTY would have folded them' % (o.name, len(bad)), flush=True)
    rest = [f for f in bm.faces if len(f.verts) > 3]
    if rest:
        bmesh.ops.triangulate(bm, faces=rest, quad_method='BEAUTY', ngon_method='BEAUTY')
    bm.to_mesh(o.data); bm.free()
    o.data.update()
    return o
