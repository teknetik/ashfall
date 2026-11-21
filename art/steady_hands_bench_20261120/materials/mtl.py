# materials/mtl.py: what the worked-materials family needs on top of the kit and servo/sv.py.
#   - 'sh_rest': a per-vertex attribute holding where a vertex lies in the UNCUT, UNBENT stock (metres). The alloy
#     materials read it in place of object coordinates, so the paint flakes run unbroken across the cut lines of a
#     sheet and stay the same on a strip before and after it is bent.
#   - the Warden-orange-on-alloy material: large ragged flakes, long scratches, a stencil fragment (SEAM.md section 8).
#   - small builders: tubes of varying radius, hollow tubes, thin ribbons, flat slabs from 2D outlines, boundary loops.
# Millimetre inputs unless a name ends in _m. Blender 5.2, metres, Z up.
import bpy, bmesh, math, os, sys
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
for p in (os.path.join(HERE, '..', 'kit'), os.path.join(HERE, '..', 'servo')):
    if p not in sys.path:
        sys.path.insert(0, p)
import geo as G
import mats as MT
import sv

MM = 0.001
REST = 'sh_rest'


def enc(c):
    """Linear albedo -> the sRGB-coded triple mats.make expects (it converts back)."""
    return tuple(12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055 for x in c)


# SEAM.md section 8, read from the kit's constants at build time (linear albedo there), never typed here: a correction
# to the shared Warden orange reaches this family by itself
# The orchestrator's ruling of 20 Nov 19:25 (SEAM.md section 8): orange stands at linear (0.60, 0.20, 0.076), bare alloy
# becomes a dull dark grey-brown, linear (0.30, 0.285, 0.265). The kit's constants were in an interim state then:
# they are used once PROGRESS.md carries 'model-pistol: KIT RIG FIXED', the ruling's own numbers until that line.
_RULING = {'orange': (0.60, 0.20, 0.076), 'bare': (0.30, 0.285, 0.265)}
try:
    KIT_READY = 'model-pistol: KIT RIG FIXED' in open(os.path.join(HERE, '..', 'PROGRESS.md')).read()
except OSError:
    KIT_READY = False
ORANGE_LIN = tuple(MT.WARDEN_ORANGE) if KIT_READY else _RULING['orange']
BARE_LIN = tuple(MT.BARE_ALLOY) if KIT_READY else _RULING['bare']
ORANGE = enc(ORANGE_LIN)
BARE = enc(BARE_LIN)
FRESH = enc((0.60, 0.59, 0.57))          # alloy where a tool has just been: sheared, filed, scratched bright


# ---------------------------------------------------------------------- rest coordinates
def set_rest(o, coords=None):
    """Write 'sh_rest'. coords: one Vector per vertex (metres); default = where the vertex is now, in world space."""
    me = o.data
    a = me.attributes.get(REST)
    if a is None:
        a = me.attributes.new(REST, 'FLOAT_VECTOR', 'POINT')
    bpy.context.view_layer.update()
    mw = o.matrix_world
    for i, v in enumerate(me.vertices):
        a.data[i].vector = coords[i] if coords is not None else mw @ v.co
    o['has_rest'] = 1
    return o


def use_rest(mat):
    """Make a kit material read 'sh_rest' wherever it read object coordinates."""
    nt = mat.node_tree
    an = nt.nodes.new('ShaderNodeAttribute')
    an.attribute_type = 'GEOMETRY'; an.attribute_name = REST
    for l in list(nt.links):
        if l.from_node.type == 'TEX_COORD' and l.from_socket.name == 'Object':
            to = l.to_socket
            nt.links.remove(l)
            nt.links.new(an.outputs['Vector'], to)
    mat['rest'] = 1
    return mat


# ---------------------------------------------------------------------- material layers
def _sep(mat, vec):
    s = mat.node_tree.nodes.new('ShaderNodeSeparateXYZ')
    mat.node_tree.links.new(vec, s.inputs[0])
    return s.outputs


def _mapped(mat, vec, scale, rot_z=0.0):
    mp = mat.node_tree.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = scale
    mp.inputs['Rotation'].default_value = (0.0, 0.0, rot_z)
    mat.node_tree.links.new(vec, mp.inputs['Vector'])
    return mp.outputs['Vector']


def flakes(mat, rect_m, colour, rough, metal, scale=34.0, lo=0.52, soft=0.008, edge_w=0.007, edge_gain=0.16, holes_m=(),
           rim=None, depth=-0.8, pits=0.3, shift=(0.0, 0.0, 0.0)):
    """Paint gone in large irregular patches with a ragged coast: three octaves of noise by hand (patch, coast,
    crumbs), pushed further near the stock's own edges (rect_m = x0, y0, x1, y1 in rest metres) and its old bolt
    holes (holes_m = [(x, y, r)]). Returns the mask socket."""
    b = MT.NB(mat)
    P = sv._obj(mat)
    Pq = b.vmath('ADD', P, tuple(shift))
    big = b.noise(Pq, scale, 2, 0.5)
    coast = b.noise(Pq, scale * 5.5, 5, 0.68)
    crumb = b.noise(Pq, scale * 26.0, 3, 0.6)
    n = b.math('ADD', b.math('ADD', b.math('MULTIPLY', big, 0.62), b.math('MULTIPLY', coast, 0.28)), b.math('MULTIPLY', crumb, 0.10))
    x, y, _z = _sep(mat, P)
    x0, y0, x1, y1 = rect_m
    d = b.math('MINIMUM', b.math('MINIMUM', b.math('SUBTRACT', x, x0), b.math('SUBTRACT', x1, x)),
               b.math('MINIMUM', b.math('SUBTRACT', y, y0), b.math('SUBTRACT', y1, y)))
    e = b.math('MULTIPLY', b.math('SUBTRACT', 1.0, b.ramp(d, 0.0, edge_w)), edge_gain)
    for (hx, hy, hr) in holes_m:
        dh = b.math('SQRT', b.math('ADD', b.math('POWER', b.math('SUBTRACT', x, hx), 2.0), b.math('POWER', b.math('SUBTRACT', y, hy), 2.0)))
        e = b.math('ADD', e, b.math('MULTIPLY', b.math('SUBTRACT', 1.0, b.ramp(dh, hr, hr + 0.007)), 0.2))
    n = b.math('ADD', n, e)
    if rim:
        sv._layer(mat, b.ramp(n, lo - soft * 2.2, lo), rim[0], rim[1], 0.0)
    mask = b.ramp(n, lo, lo + soft)
    if pits:
        mask = b.math('MAXIMUM', mask, b.math('MULTIPLY', b.ramp(b.noise(Pq, scale * 60.0, 3, 0.5), 0.70, 0.74), pits))
    sv._layer(mat, mask, colour, rough, metal, height=depth)
    return mask


def scratches(mat, colour, rough, metal, rot_z=0.0, scale=(9.0, 1300.0, 1.0), lo=0.71, hi=0.73, amount=1.0, depth=-0.35):
    """Long thin scratches: a noise stretched along one direction (rot_z, radians about Z), only its peaks kept."""
    b = MT.NB(mat)
    v = _mapped(mat, sv._obj(mat), scale, rot_z)
    mask = b.math('MULTIPLY', b.ramp(b.noise(v, 1.0, 3, 0.55), lo, hi), amount)
    sv._layer(mat, mask, colour, rough, metal, height=depth)
    return mask


def dimples(mat, centres_m, r=0.00055, colour=(0.74, 0.73, 0.71)):
    """Centre-punch dimples at the given rest points. They are the CLEAN state (DIRTY = 0); the as-found set has none,
    so the bench reveals each one when it is punched (parts.json wipe 'punch')."""
    b = MT.NB(mat)
    P = sv._obj(mat)
    clean = b.math('SUBTRACT', 1.0, sv._dirty(mat))
    tot = None
    ring = None
    for c in centres_m:
        d = b.vmath('DISTANCE', P, tuple(c))
        m = b.math('SUBTRACT', 1.0, b.ramp(d, r * 0.2, r))
        rg = b.math('MULTIPLY', b.ramp(d, r * 0.9, r * 1.15), b.math('SUBTRACT', 1.0, b.ramp(d, r * 1.15, r * 1.7)))
        tot = m if tot is None else b.math('MAXIMUM', tot, m)
        ring = rg if ring is None else b.math('MAXIMUM', ring, rg)
    tot = b.math('MULTIPLY', tot, clean)
    ring = b.math('MULTIPLY', ring, clean)
    sv._layer(mat, tot, colour, 0.3, 1.0, height=-5.0)
    nt = mat.node_tree
    bn = nt.nodes['BUMP']
    hsrc = bn.inputs['Height'].links[0].from_socket
    nt.links.remove(bn.inputs['Height'].links[0])
    nt.links.new(b.math('ADD', hsrc, b.math('MULTIPLY', ring, 1.6)), bn.inputs['Height'])
    mat['wipe'] = 1
    return mat


def dirty_layer(mat, colour, rough, metal):
    """An as-found state over the whole material (DIRTY = 1): bare copper under tinning, dull legs under fresh solder."""
    sv._layer(mat, sv._dirty(mat), colour, rough, metal)
    mat['wipe'] = 1
    return mat


def alloy_paint(name, rect_m, holes_m=(), stencil=None, lo=0.52, shift=(0, 0, 0), punch=None):
    """Old Warden orange on alloy. stencil: (png, centre_m, ex, ey, width_m, height_m). punch: rest points of dimples."""
    m = MT.make(name, ORANGE, 0.0, 0.58, var=0.09, rough_var=0.05, edge=None, dirt=((0.16, 0.12, 0.09), 0.85, 0.3), grime=0.22,
                bumps=[('noise', 700, 0.28), ('stipple', 2600, 0.10)], bevel_r=0.0,
                tone2=(enc((0.47, 0.19, 0.085)), 55, 0.45, 0.8, 0.55))
    if stencil:
        png, c, ex, ey, w, h = stencil
        sv.add_stencil(m, png, c, ex, ey, w, h, (0.80, 0.76, 0.66), rough=0.62, amount=0.92, depth=0.0006)
    sv.add_streaks(m, (0.20, 0.13, 0.08), 0.85, axis='X', scale=(26.0, 330.0, 330.0), lo=0.56, hi=0.8, amount=0.35)     # dragged grime
    scratches(m, FRESH, 0.40, 1.0, rot_z=0.12, lo=0.715, hi=0.73)
    scratches(m, FRESH, 0.40, 1.0, rot_z=-1.05, scale=(14.0, 1500.0, 1.0), lo=0.73, hi=0.745, amount=0.9)
    flakes(m, rect_m, BARE, 0.60, 1.0, lo=lo, holes_m=holes_m, rim=((0.30, 0.13, 0.06), 0.8), shift=shift)
    if punch:
        dimples(m, punch)
    return use_rest(m)


def alloy_bare(name, rect_m, holes_m=()):
    """The bare, brushed side: dull alloy brushed along the sheet's long edge, oxide blooms, handling scratches."""
    m = MT.make(name, BARE, 1.0, 0.60, var=0.07, rough_var=0.05, edge=None, dirt=((0.16, 0.12, 0.09), 0.85, 0.35), grime=0.3,
                bumps=[('brushed', (0.5, 20.0, 20.0), 0.32), ('noise', 1400, 0.10)], bevel_r=0.0,
                tone2=(enc(tuple(x * 0.55 for x in BARE_LIN)), 38, 0.46, 0.78, 0.6))                 # darker stains and oxide blooms
    sv.add_streaks(m, enc(tuple(x * 1.35 for x in BARE_LIN)), 0.5, axis='X', scale=(9.0, 520.0, 520.0), lo=0.55, hi=0.8, amount=0.3)      # the brushing, along the long edge
    scratches(m, FRESH, 0.36, 1.0, rot_z=0.5, lo=0.70, hi=0.72, depth=-0.5)
    scratches(m, FRESH, 0.36, 1.0, rot_z=-0.8, scale=(16.0, 1500.0, 1.0), lo=0.72, hi=0.735, depth=-0.5)
    scratches(m, (0.13, 0.11, 0.09), 0.8, 0.0, rot_z=1.9, scale=(20.0, 900.0, 1.0), lo=0.73, hi=0.75, depth=0.0)        # dark rub marks
    return use_rest(m)


# ---------------------------------------------------------------------- geometry
def slab(name, poly_mm, z0, z1, origin_m=(0, 0, 0), mat=None):
    """A flat piece: 2D outline (mm, in the layout frame at origin_m) from z0 to z1 (mm)."""
    O = Vector(origin_m)
    return G.prism(name, [(a * MM, b * MM) for a, b in poly_mm], (z1 - z0) * MM, O + Vector((0, 0, z0 * MM)), (1, 0, 0), (0, 1, 0), (0, 0, 1), mat, w0=0.0)


def paint_faces(o, classify, mats):
    """Give each face the material classify(world centre, world normal) names. mats: {key: material}."""
    me = o.data
    me.materials.clear()
    keys = list(mats)
    for k in keys:
        me.materials.append(mats[k])
    bpy.context.view_layer.update()
    R = o.matrix_world.to_3x3()
    for p in me.polygons:
        p.material_index = keys.index(classify(o.matrix_world @ p.center, (R @ p.normal).normalized()))
    return o


def tri_safe(o):
    """Triangulate by ear clipping. The kit triangulates with the BEAUTY method, which left a flipped sliver (a hole
    seen from above) in one many-cornered plate face; a mesh that is already triangles passes through it unchanged."""
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.triangulate(bm, faces=bm.faces, quad_method='FIXED', ngon_method='EAR_CLIP')
    bm.to_mesh(o.data); bm.free()
    o.data.update()
    return o


def plane_loops(o, z_m, up=True, tol=2e-6):
    """Ordered boundary loops (object space) of the faces of o that lie in the plane z = z_m facing up (or down)."""
    bm = bmesh.new(); bm.from_mesh(o.data)
    sel = set(f for f in bm.faces if abs(f.calc_center_median().z - z_m) < tol and (f.normal.z > 0.99 if up else f.normal.z < -0.99))
    nxt = {}
    for f in sel:
        for l in f.loops:
            other = [g for g in l.edge.link_faces if g is not f and g in sel]
            if not other:
                nxt[l.vert.index] = l.link_loop_next.vert.index
    co = {v.index: v.co.copy() for v in bm.verts}
    bm.free()
    loops = []
    while nxt:
        a0 = next(iter(nxt)); a = a0; lp = []
        while True:
            lp.append(co[a]); b_ = nxt.pop(a)
            a = b_
            if a == a0:
                break
        loops.append(lp)
    loops.sort(key=lambda lp: -sum((lp[i] - lp[i - 1]).length for i in range(len(lp))))
    return loops


def plane_edges(o, z_m, up=True, tol=2e-6):
    """The boundary of the faces of o that lie in the plane z = z_m facing up (or down), as unordered edges
    [(point, point)] in object space. (Ordered loops are not always there: after a bevel two loops can share a vertex.)"""
    bm = bmesh.new(); bm.from_mesh(o.data)
    sel = set(f for f in bm.faces if abs(f.calc_center_median().z - z_m) < tol and (f.normal.z > 0.99 if up else f.normal.z < -0.99))
    out = []
    for f in sel:
        for l in f.loops:
            if not [g for g in l.edge.link_faces if g is not f and g in sel]:
                out.append((l.vert.co.copy(), l.link_loop_next.vert.co.copy()))
    bm.free()
    return out


def fill_edges(name, edges, mat=None, flip=False):
    """Planar faces filling what a set of edges [(point, point)] encloses (outer boundaries and holes alike)."""
    bm = bmesh.new()
    seen = {}

    def vert(p):
        k = (round(p[0] * 1e7), round(p[1] * 1e7), round(p[2] * 1e7))
        if k not in seen:
            seen[k] = bm.verts.new(p)
        return seen[k]
    for a, b in edges:
        va, vb = vert(a), vert(b)
        if va is not vb and bm.edges.get((va, vb)) is None:
            bm.edges.new((va, vb))
    bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=bm.edges[:], normal=(0, 0, -1 if flip else 1))
    bm.normal_update()
    for f in bm.faces:
        if (f.normal.z < 0) != flip:
            f.normal_flip()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); G.link(o)
    if mat:
        me.materials.append(mat)
    return o


def fill_between(name, loops, mat=None, flip=False):
    """Planar faces filling the region bounded by closed loops (the first is the outside, the rest are holes)."""
    bm = bmesh.new()
    for lp in loops:
        vs = [bm.verts.new(p) for p in lp]
        for i in range(len(vs)):
            bm.edges.new((vs[i - 1], vs[i]))
    bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=bm.edges[:], normal=(0, 0, -1 if flip else 1))
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    for f in bm.faces:
        if (f.normal.z < 0) != flip:
            f.normal_flip()
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); G.link(o)
    if mat:
        me.materials.append(mat)
    return o


def wall(name, loop, z0_m, z1_m, mat=None, outward=True):
    """A vertical wall on a closed loop of points (x, y used) from z0 to z1, facing out of (or into) the loop."""
    n = len(loop)
    verts = [Vector((p[0], p[1], z0_m)) for p in loop] + [Vector((p[0], p[1], z1_m)) for p in loop]
    area = sum(loop[i][0] * loop[(i + 1) % n][1] - loop[(i + 1) % n][0] * loop[i][1] for i in range(n))
    ccw = area > 0
    faces = []
    for i in range(n):
        j = (i + 1) % n
        f = (i, j, n + j, n + i)
        faces.append(f if (ccw == outward) else f[::-1])
    return G.mesh_obj(name, verts, faces, mat, recalc=False)


def var_tube(name, pts, radii, segs=8, mat=None, caps=True, twist_ref=(0, 0, 1)):
    """Round section of varying radius along a polyline (metres), parallel-transport frames."""
    P = [Vector(p) for p in pts]
    n = len(P)
    T = [(P[min(i + 1, n - 1)] - P[max(i - 1, 0)]).normalized() for i in range(n)]
    ref = Vector(twist_ref)
    N0 = ref - T[0] * T[0].dot(ref)
    if N0.length < 1e-6:
        N0 = Vector((1, 0, 0)) - T[0] * T[0].x
    N = [N0.normalized()]
    for i in range(1, n):
        v = N[-1] - T[i] * T[i].dot(N[-1])
        N.append(v.normalized())
    verts, faces = [], []
    for i in range(n):
        B = T[i].cross(N[i])
        r = radii[i] if hasattr(radii, '__len__') else radii
        for k in range(segs):
            th = 2 * math.pi * k / segs
            verts.append(P[i] + (N[i] * math.cos(th) + B * math.sin(th)) * r)
    for i in range(n - 1):
        for k in range(segs):
            k2 = (k + 1) % segs
            faces.append((i * segs + k, i * segs + k2, (i + 1) * segs + k2, (i + 1) * segs + k))
    if caps:
        faces.append(tuple(range(segs))[::-1])
        faces.append(tuple(range((n - 1) * segs, n * segs)))
    return G.mesh_obj(name, verts, faces, mat)


def hollow_tube(name, pts, r_out, r_in, segs=8, mat=None):
    """A sleeve: outer and inner wall along a polyline with annular ends (a closed solid with a hole through it)."""
    P = [Vector(p) for p in pts]
    n = len(P)
    T = [(P[min(i + 1, n - 1)] - P[max(i - 1, 0)]).normalized() for i in range(n)]
    N0 = Vector((0, 0, 1)) - T[0] * T[0].z
    if N0.length < 1e-6:
        N0 = Vector((1, 0, 0))
    N = [N0.normalized()]
    for i in range(1, n):
        v = N[-1] - T[i] * T[i].dot(N[-1])
        N.append(v.normalized())
    verts, faces = [], []
    for i in range(n):
        B = T[i].cross(N[i])
        for r in (r_out, r_in):
            for k in range(segs):
                th = 2 * math.pi * k / segs
                verts.append(P[i] + (N[i] * math.cos(th) + B * math.sin(th)) * r)
    S2 = 2 * segs
    for i in range(n - 1):
        for k in range(segs):
            k2 = (k + 1) % segs
            a, b_ = i * S2, (i + 1) * S2
            faces.append((a + k, a + k2, b_ + k2, b_ + k))                                   # outer
            faces.append((a + segs + k2, a + segs + k, b_ + segs + k, b_ + segs + k2))       # inner
    for i, rev in ((0, True), (n - 1, False)):
        a = i * S2
        for k in range(segs):
            k2 = (k + 1) % segs
            f = (a + k, a + k2, a + segs + k2, a + segs + k)
            faces.append(f[::-1] if not rev else f)
    o = G.mesh_obj(name, verts, faces, mat, recalc=True)
    bm = bmesh.new(); bm.from_mesh(o.data)
    if G.signed_volume(bm) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
        bm.to_mesh(o.data)
    bm.free()
    return o


def ribbon(name, pts, normals, width, mat=None):
    """A paper-thin two-sided ribbon (drill swarf): one quad strip seen from both sides."""
    P = [Vector(p) for p in pts]
    n = len(P)
    verts, faces = [], []
    for side in (0, 1):
        for i in range(n):
            t = (P[min(i + 1, n - 1)] - P[max(i - 1, 0)]).normalized()
            nn = Vector(normals[i]); nn = (nn - t * t.dot(nn)).normalized()
            s = t.cross(nn)
            off = nn * (0.00003 if side == 0 else -0.00003)
            verts += [P[i] - s * width / 2 + off, P[i] + s * width / 2 + off]
    for side in (0, 1):
        b0 = side * 2 * n
        for i in range(n - 1):
            f = (b0 + 2 * i, b0 + 2 * i + 1, b0 + 2 * i + 3, b0 + 2 * i + 2)
            faces.append(f if side == 0 else f[::-1])
    return G.mesh_obj(name, verts, faces, mat, recalc=False)


def arc_lengths(P):
    L = [0.0]
    for a, b in zip(P, P[1:]):
        L.append(L[-1] + (Vector(b) - Vector(a)).length)
    return L


def point_at(P, d):
    """(point, unit tangent) at arc length d (metres) on a polyline."""
    P = [Vector(p) for p in P]
    L = arc_lengths(P)
    d = min(max(d, 0.0), L[-1])
    for i in range(len(P) - 1):
        if L[i + 1] >= d - 1e-12:
            seg = L[i + 1] - L[i]
            t = 0.0 if seg < 1e-12 else (d - L[i]) / seg
            return P[i].lerp(P[i + 1], t), (P[i + 1] - P[i]).normalized()
    return P[-1], (P[-1] - P[-2]).normalized()


def dist_to_poly(p, poly):
    """Distance from 2D point p to the boundary of a closed polygon (same units)."""
    best = 1e9
    px, py = p
    n = len(poly)
    for i in range(n):
        ax, ay = poly[i]; bx, by = poly[(i + 1) % n]
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 < 1e-18 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
        best = min(best, math.hypot(px - ax - t * dx, py - ay - t * dy))
    return best
