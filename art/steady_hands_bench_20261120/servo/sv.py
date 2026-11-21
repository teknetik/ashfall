# servo/sv.py: builders the servo and materials families need on top of the kit (gears, wound coils, dents, scorch).
# Millimetre helpers: P(x, y, z) is a point in metres from millimetres. Everything else is metres, Z up.
import bpy, bmesh, math, os, sys
from mathutils import Vector, Matrix

KIT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'kit')
if KIT not in sys.path:
    sys.path.insert(0, KIT)
import geo as G
import mats as MT

MM = 0.001
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))


def P(x, y, z):
    return Vector((x * MM, y * MM, z * MM))


def box(name, lo, hi, mat=None):
    """Axis-aligned box from two corners given in millimetres."""
    lo = Vector(lo); hi = Vector(hi)
    c = (lo + hi) / 2 * MM
    s = (hi - lo) * MM
    return G.box(name, c, (abs(s.x), abs(s.y), abs(s.z)), None, mat)


def vcyl(name, x, y, z0, z1, r, segs=16, mat=None, chamfer=0.0):
    """Vertical cylinder at (x, y) from z0 to z1 (millimetres)."""
    return G.cyl(name, P(x, y, z0), P(x, y, z1), r * MM, segs, mat, chamfer=chamfer * MM, ref=(1, 0, 0))


def annulus(name, origin, axis, r_in, r_out, s0, s1, segs=32, mat=None, chamfer=0.0, ref=None):
    """Ring of rectangular section (millimetres) about an axis through origin (metres), from s0 to s1 along it."""
    c = chamfer
    if c > 0:
        prof = [(s0, r_in + c), (s0 + c, r_in), (s1 - c, r_in), (s1, r_in + c), (s1, r_out - c), (s1 - c, r_out), (s0 + c, r_out), (s0, r_out - c)]
    else:
        prof = [(s0, r_in), (s1, r_in), (s1, r_out), (s0, r_out)]
    prof = [(a * MM, b * MM) for a, b in prof]
    if ref is None:
        ref = (1, 0, 0) if abs(Vector(axis).normalized().z) > 0.9 else (0, 0, 1)
    return G.lathe(name, [(prof, True)], segs, origin, axis, ref, mat)


# ---------------------------------------------------------------------- gears
def gear_outline(n, m, phase=0.0, chew=None, add=0.9, ded=1.15, tip_f=0.12, root_f=0.27):
    """2D outline (metres) of a spur gear with n trapezoid teeth of module m (millimetres). A tooth is centred on angle
    phase + k * 2pi / n. chew: {tooth index: fraction of the tooth height left} for worn and stripped teeth."""
    rp = m * n / 2.0
    rt = rp + add * m
    rr = rp - ded * m
    tau = 2 * math.pi / n
    pts = []
    for k in range(n):
        a = phase + k * tau
        f = (chew or {}).get(k, 1.0)
        r1 = rr + (rt - rr) * f
        tf = tip_f + (root_f - tip_f) * (1 - f) * 0.8
        skew = 0.0 if f >= 1.0 else 0.05 * tau * (1 if k % 2 else -1)       # a chewed tooth leans
        for da, r in ((-root_f * tau, rr), (-tf * tau + skew, r1), (tf * tau + skew, r1 * (1.0 if f >= 1.0 else 0.985)), (root_f * tau, rr)):
            pts.append((r * MM * math.cos(a + da), r * MM * math.sin(a + da)))
    return pts, rp, rt, rr


def spur(name, n, m, origin, u, v, w, thick, bore_r, mat, phase=0.0, chew=None, holes=(), hub=None, hub_mat=None):
    """Spur gear: outline in the (u, v) plane at origin (metres), extruded thick (mm) along w from 0. bore_r in mm.
    holes: lightening holes [(radius from centre mm, hole radius mm, count)]. hub: (r mm, height mm) boss on the +w face.
    Returns (object, pitch radius mm, tip radius mm)."""
    pts, rp, rt, rr = gear_outline(n, m, phase, chew)
    hl = [(0.0, 0.0, bore_r * MM)]
    for (rc, rh, cnt) in holes:
        for k in range(cnt):
            a = phase + math.pi / cnt + 2 * math.pi * k / cnt
            hl.append((rc * MM * math.cos(a), rc * MM * math.sin(a), rh * MM))
    o = G.plate(name, pts, thick * MM, origin, u, v, w, holes=hl, mat=mat, w0=0.0, hole_segs=12)
    if hub:
        wv = Vector(w).normalized()
        h = annulus(name + '_hub', Vector(origin), wv, bore_r, hub[0], thick, thick + hub[1], 16, hub_mat or mat, chamfer=min(0.15, hub[1] * 0.3),
                    ref=Vector(u))
        o = G.join(name, [o, h])
    G.shade(o, 35)
    return o, rp, rt


def crown(name, n, origin, r_in, r_out, r_disc, z_face, thick, depth, bore_r, mat, phase=math.pi, hub=None, chew=None):
    """Face (crown) gear on a vertical axis through origin (metres; only x and y are used). The disc lies from z_face
    up to z_face + thick (mm); n radial teeth hang depth below z_face between r_in and r_out. One tooth points along
    angle phase."""
    c = Vector((origin[0], origin[1], z_face * MM))
    disc = G.plate(name, G.circle(r_disc * MM, 40), thick * MM, c, X, Y, Z, holes=[(0, 0, bore_r * MM)], mat=mat, w0=0.0, hole_segs=12)
    parts = [disc]
    pitch = 2 * math.pi * (r_in + r_out) / 2 / n
    for k in range(n):
        a = phase + 2 * math.pi * k / n
        f = (chew or {}).get(k, 1.0)
        rad = Vector((math.cos(a), math.sin(a), 0)); tan = Vector((-math.sin(a), math.cos(a), 0))
        wt = pitch * 0.5; wb = pitch * 0.24
        d = depth * f
        poly = [(-wt / 2 * MM, 0.02 * MM), (wt / 2 * MM, 0.02 * MM), (wb / 2 * MM, -d * MM), (-wb / 2 * MM, -d * MM)]
        parts.append(G.prism(name + '_t', poly, (r_out - r_in) * MM, c + rad * (r_in * MM), tan, Z, rad, mat, w0=0.0))
    if hub:
        parts.append(annulus(name + '_hub', c, Z, bore_r, hub[0], thick, thick + hub[1], 16, mat, chamfer=min(0.15, hub[1] * 0.3)))
    o = G.join(name, parts)
    G.shade(o, 35)
    return o


# ---------------------------------------------------------------------- windings
def ridged_ring(name, origin, axis, r0, r1, s0, s1, pitch, depth, segs=40, mat=None, ref=None):
    """A wound coil as a ring of rectangular section (mm) whose faces are scalloped, one ridge per turn of wire."""
    def side(a, b, const, along_s):
        n = max(2, int(round(abs(b - a) / pitch)))
        out = []
        for i in range(2 * n + 1):
            t = a + (b - a) * i / (2 * n)
            off = depth if i % 2 else 0.0
            out.append((t, const, off) if along_s else (const, t, off))
        return out
    prof = []
    for (s, r, off) in side(s0, s1, r1, True):          # outer face, bumps outward
        prof.append((s, r + off))
    for (s, r, off) in side(r1, r0, s1, False)[1:]:      # top face, bumps along +s
        prof.append((s + off, r))
    for (s, r, off) in side(s1, s0, r0, True)[1:]:       # inner face, bumps inward
        prof.append((s, r - off))
    for (s, r, off) in side(r0, r1, s0, False)[1:-1]:    # bottom face
        prof.append((s - off, r))
    prof = [(a * MM, b * MM) for a, b in prof]
    if ref is None:
        ref = (1, 0, 0) if abs(Vector(axis).normalized().z) > 0.9 else (0, 0, 1)
    o = G.lathe(name, [(prof, True)], segs, origin, axis, ref, mat)
    G.shade(o, 50)
    return o


def torus_wrap(name, centre, r_mid, half_r, half_z, a0, a1, turns, depth, mat=None, corner=0.8, sec=3):
    """Toroidal winding on a ring core about the Z axis through centre (metres): the wrap's section is a rounded
    rectangle half_r x half_z (mm) about the core's mid radius, and it runs from angle a0 to a1 with one ridge per
    turn (the section breathes in and out by depth)."""
    def section(grow):
        pts = []
        hr, hz, c = half_r + grow, half_z + grow, corner
        for cx, cz, q in ((hr - c, hz - c, 0), (-hr + c, hz - c, 1), (-hr + c, -hz + c, 2), (hr - c, -hz + c, 3)):
            for k in range(sec + 1):
                t = math.pi / 2 * (q + k / sec)
                pts.append((cx + c * math.cos(t), cz + c * math.sin(t)))
        return pts
    n = turns * 2
    ns = 4 * (sec + 1)
    verts, faces = [], []
    C = Vector(centre)
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        grow = depth if i % 2 else 0.0
        if i in (0, n):
            grow = -0.15
        for (dr, dz) in section(grow):
            r = (r_mid + dr) * MM
            verts.append(C + Vector((r * math.cos(a), r * math.sin(a), dz * MM)))
    for i in range(n):
        for j in range(ns):
            j2 = (j + 1) % ns
            faces.append((i * ns + j, i * ns + j2, (i + 1) * ns + j2, (i + 1) * ns + j))
    faces.append(tuple(range(ns))[::-1])
    faces.append(tuple(range(n * ns, (n + 1) * ns)))
    o = G.mesh_obj(name, verts, faces, mat, recalc=True)
    G.clean(o, recalc=True)
    G.shade(o, 50)
    return o


# ---------------------------------------------------------------------- damage
def dent(o, dents, axis_point, axis_dir, r_min):
    """Push the outer skin of a round can inward. dents: [(centre point metres, radius mm, depth mm)]. Only vertices
    farther than r_min (mm) from the axis move, toward the axis."""
    A = Vector(axis_point); D = Vector(axis_dir).normalized()
    mw = o.matrix_world
    inv = mw.inverted()
    for v in o.data.vertices:
        p = mw @ v.co
        rad = (p - A) - D * (p - A).dot(D)
        if rad.length < r_min * MM:
            continue
        move = 0.0
        for (c, r, d) in dents:
            t = (p - Vector(c)).length / (r * MM)
            if t < 1.0:
                move += d * MM * (0.5 + 0.5 * math.cos(math.pi * t)) ** 1.5
        if move:
            v.co = inv @ (p - rad.normalized() * move)
    o.data.update()
    return o


def _layer(mat, mask, colour, rough, metal, height=0.0):
    """Lay colour / roughness / metallic over a kit material where mask is 1. The layer goes UNDER the material's
    as-found (wipe) layer when it has one, so dust and corrosion still cover it; the CH_ taps, the packed ORM tap and
    the bake are untouched. height: bump height added (negative for a chip in the paint)."""
    nt = mat.node_tree
    b = MT.NB(mat)
    wiped = bool(mat.get('wipe'))
    for ch, val, idx in (('CH_base', MT.srgb(colour), 6), ('CH_rough', rough, 2), ('CH_metal', metal, 2)):
        r = nt.nodes[ch]
        node, i = (r.inputs[0].links[0].from_node, idx) if wiped else (r, 0)
        src = node.inputs[i].links[0].from_socket if node.inputs[i].links else None
        if src is None:          # a constant on the socket: turn it into a node output first
            if ch == 'CH_base':
                src = b.rgb(tuple(node.inputs[i].default_value)[:3])
            else:
                src = b.value(node.inputs[i].default_value)
        else:
            nt.links.remove(node.inputs[i].links[0])
        new = b.mixc(mask, src, val) if ch == 'CH_base' else b.mixf(mask, src, val)
        nt.links.new(new, node.inputs[i])
    if not wiped:
        orm = nt.nodes.get('ORM')
        if orm:
            for i, ch in ((1, 'CH_rough'), (2, 'CH_metal')):
                for l in list(orm.inputs[i].links):
                    nt.links.remove(l)
                nt.links.new(b.math('MAXIMUM', b.math('MINIMUM', nt.nodes[ch].inputs[0].links[0].from_socket, 1.0), 0.0), orm.inputs[i])
    if height:
        bn = nt.nodes['BUMP']
        if bn.inputs['Height'].links:
            hsrc = bn.inputs['Height'].links[0].from_socket
            nt.links.remove(bn.inputs['Height'].links[0])
            nt.links.new(b.math('ADD', hsrc, b.math('MULTIPLY', mask, height)), bn.inputs['Height'])
    return mask


def _obj(mat):
    return mat.node_tree.nodes.new('ShaderNodeTexCoord').outputs['Object']


def add_patch(mat, centre, radius, colour, rough, metal=0.0, noise_scale=260.0, soft=0.55, bump=0.0, name='PATCH', inner=0.55, amount=1.0):
    """A patch (scorch, stain) within radius (metres, object space) of centre, with a ragged noisy edge. bump: blister
    height inside it."""
    b = MT.NB(mat)
    Pp = _obj(mat)
    d = b.vmath('DISTANCE', Pp, tuple(centre))
    n = b.noise(Pp, noise_scale, 5, 0.65)
    n2 = b.noise(Pp, noise_scale * 5, 3, 0.5)
    dd = b.math('ADD', b.math('DIVIDE', d, radius), b.math('MULTIPLY', b.math('SUBTRACT', b.math('ADD', b.math('MULTIPLY', n, 0.8), b.math('MULTIPLY', n2, 0.2)), 0.5), soft * 2))
    mask = b.math('SUBTRACT', 1.0, b.ramp(dd, inner, 1.0))       # inner: where the fade starts (low = a long soft gradient)
    if amount != 1.0:
        mask = b.math('MULTIPLY', mask, amount)
    _layer(mat, mask, colour, rough, metal)
    if bump:
        nt = mat.node_tree
        bn = nt.nodes['BUMP']
        hsrc = bn.inputs['Height'].links[0].from_socket
        nt.links.remove(bn.inputs['Height'].links[0])
        blister = b.math('MULTIPLY', b.math('MULTIPLY', mask, b.ramp(b.noise(Pp, 900.0, 3, 0.5), 0.45, 0.7)), bump)
        nt.links.new(b.math('ADD', hsrc, blister), bn.inputs['Height'])
    return mask


def lin(c):
    """Linear RGB albedo -> the sRGB triple the kit's materials take (they convert back with mats.srgb)."""
    f = lambda x: 12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055
    return tuple(f(x) for x in c)


def add_wear(mat, fields, colour, rough, metal, noise_scale=95.0, soft=0.7, rim=None, depth=-0.7):
    """Paint worn through in a few large patches with a ragged coast (SEAM.md section 8). fields: [(centre, radii)] in
    object space, metres: each is an ellipsoid inside which the paint is gone, its edge broken by noise into bays and
    islands. rim: (colour, rough) a thin dark edge of primer and rust round every patch."""
    b = MT.NB(mat)
    Pp = _obj(mat)
    F = None
    for (c, r) in fields:
        dv = b.vmath('MULTIPLY', b.vmath('SUBTRACT', Pp, tuple(c)), (1.0 / r[0], 1.0 / r[1], 1.0 / r[2]))
        f = b.math('SUBTRACT', 1.0, b.vmath('LENGTH', dv))
        F = f if F is None else b.math('MAXIMUM', F, f)
    n = b.math('ADD', b.math('ADD', b.math('MULTIPLY', b.noise(Pp, noise_scale, 4, 0.6), 0.55), b.math('MULTIPLY', b.noise(Pp, noise_scale * 4.4, 4, 0.6), 0.3)),
               b.math('MULTIPLY', b.noise(Pp, noise_scale * 19.0, 3, 0.5), 0.15))
    dd = b.math('ADD', b.math('SUBTRACT', 1.0, F), b.math('MULTIPLY', b.math('SUBTRACT', n, 0.5), soft * 2))
    if rim:
        _layer(mat, b.math('SUBTRACT', 1.0, b.ramp(dd, 0.80, 0.90)), rim[0], rim[1], 0.0)
    mask = b.math('SUBTRACT', 1.0, b.ramp(dd, 0.66, 0.78))
    _layer(mat, mask, colour, rough, metal, height=depth)
    return mask


def add_scratches(mat, colour, rough, metal, scale=(9.0, 1200.0, 1200.0), lo=0.735, hi=0.75, depth=-0.5):
    """A few long thin scratches: a noise stretched along one object axis (the small number in scale), cut high, and
    gathered into loose groups by a broad second noise."""
    nt = mat.node_tree
    b = MT.NB(mat)
    Pp = _obj(mat)
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = scale
    nt.links.new(Pp, mp.inputs['Vector'])
    mask = b.math('MULTIPLY', b.ramp(b.noise(mp.outputs['Vector'], 1.0, 2, 0.5), lo, hi), b.ramp(b.noise(Pp, 26.0, 2, 0.5), 0.36, 0.5))
    _layer(mat, mask, colour, rough, metal, height=depth)
    return mask


# ---------------------------------------------------------------------- old paint on a can (the last surface pass, 20 Nov)
# The alloy plates of the materials family (materials/mtl.py flakes()) are the accepted Warden paint. Their flakes are
# for flat stock; these are the same flakes, coast and primer rim for a body with handled places: they only cut
# through inside the fields and along outside edges, so there is never a bare island in the middle of a panel.
def _field(mat, fields, plateau=0.0):
    """1 at the centre of the nearest field, falling to 0 at its edge. fields: [(centre, radii)] ellipsoids in object
    space, metres. plateau: above 0, the field is held at 1 over its inner part and only fades over the outer
    `plateau` of its radius (smoothstep), so a small field pushes as hard across its width as at its centre."""
    b = MT.NB(mat)
    Pp = _obj(mat)
    F = None
    for (c, r) in fields:
        dv = b.vmath('MULTIPLY', b.vmath('SUBTRACT', Pp, tuple(c)), (1.0 / r[0], 1.0 / r[1], 1.0 / r[2]))
        f = b.math('SUBTRACT', 1.0, b.vmath('LENGTH', dv))
        F = f if F is None else b.math('MAXIMUM', F, f)
    if plateau:
        return b.ramp(F, 0.0, plateau)
    return b.math('MAXIMUM', F, 0.0)


def _edges(mat, radius=0.0016, convex=True):
    """1 where the surface turns over an edge within radius, 0 on a flat. convex: inside corners are left out (paint
    is knocked off outside edges; inside corners keep theirs and collect grime)."""
    nt = mat.node_tree
    b = MT.NB(mat)
    bev = nt.nodes.new('ShaderNodeBevel'); bev.samples = 8
    bev.inputs['Radius'].default_value = radius
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    e = b.ramp(b.math('SUBTRACT', 1.0, b.vmath('DOT_PRODUCT', bev.outputs['Normal'], geo.outputs['Normal'])), 0.004, 0.05)
    if convex:
        e = b.math('MULTIPLY', e, b.math('SUBTRACT', 1.0, _cavity(mat, 0.003, 0.04, 0.25)))
    return e


def add_flakes(mat, fields, colour, rough, metal, scale=62.0, lo=0.74, soft=0.008, gain=0.30, edge_gain=0.0, edge_r=0.0016,
               rim=None, rim_w=2.2, depth=-0.8, pits=0.0, stretch=None, seed=(0.0, 0.0, 0.0), stain=None, mix=(0.62, 0.28, 0.10),
               plateau=0.0):
    """Paint gone in ragged flakes with the character of the alloy plates: three octaves of noise by hand (patch,
    coast, crumbs) cut at lo. lo sits above the noise, so open paint stays whole; the cut is lowered by `gain` inside
    a handled field (plateau: see _field) and by `edge_gain` along outside edges, which is where the flakes are.
    mix: the weights of the three octaves (the plates' are 0.62, 0.28, 0.10; a can whose fields are smaller than the
    patch octave wants more coast and crumb, or a field lands wholly on a low patch and shows nothing).
    rim: (colour, rough) the thin primer line round every flake, rim_w its width in units of soft.
    stretch: (sx, sy, sz) below 1 on an axis draws the flakes out along it (a dragged side). stain: (colour, rough,
    amount) darker oxide blooms on the bare metal. Returns the mask socket."""
    b = MT.NB(mat)
    Pp = _obj(mat)
    Pq = b.vmath('ADD', Pp, tuple(seed))
    if stretch:
        Pq = b.vmath('MULTIPLY', Pq, tuple(stretch))
    big = b.noise(Pq, scale, 2, 0.5)
    coast = b.noise(Pq, scale * 5.5, 5, 0.68)
    crumb = b.noise(Pq, scale * 26.0, 3, 0.6)
    n = b.math('ADD', b.math('ADD', b.math('MULTIPLY', big, mix[0]), b.math('MULTIPLY', coast, mix[1])), b.math('MULTIPLY', crumb, mix[2]))
    bias = b.math('MULTIPLY', _field(mat, fields, plateau), gain) if fields else None
    if edge_gain:
        e = b.math('MULTIPLY', _edges(mat, edge_r), edge_gain)
        bias = e if bias is None else b.math('ADD', bias, e)
    if bias is not None:
        n = b.math('ADD', n, bias)
    if rim:
        _layer(mat, b.ramp(n, lo - soft * rim_w, lo), rim[0], rim[1], 0.0)
    mask = b.ramp(n, lo, lo + soft)
    if pits and bias is not None:        # pin-head chips, only where the paint is already failing
        pm = b.math('MULTIPLY', b.ramp(b.noise(Pp, scale * 60.0, 3, 0.5), 0.70, 0.74), b.math('MULTIPLY', b.ramp(bias, 0.03, 0.12), pits))
        mask = b.math('MAXIMUM', mask, pm)
    _layer(mat, mask, colour, rough, metal, height=depth)
    if stain:
        sm = b.math('MULTIPLY', b.math('MULTIPLY', mask, b.ramp(b.noise(Pp, scale * 3.2, 4, 0.6), 0.42, 0.68)), stain[2])
        _layer(mat, sm, stain[0], stain[1], metal)
    return mask


def add_rubs(mat, colour, rough, metal, scale=(9.0, 520.0, 520.0), lo=0.70, hi=0.73, fields=None, gain=0.0, group=(26.0, 0.36, 0.5),
             amount=1.0, depth=-0.4):
    """Marks drawn out along one object axis (the small number in scale): long scratches when cut thin (lo close to
    hi, high), broad rub marks when cut wide. fields and gain: more of them inside the fields. group: (noise scale,
    lo, hi) gathers them into loose groups; None for everywhere."""
    nt = mat.node_tree
    b = MT.NB(mat)
    Pp = _obj(mat)
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = scale
    nt.links.new(Pp, mp.inputs['Vector'])
    n = b.noise(mp.outputs['Vector'], 1.0, 2, 0.5)
    if fields and gain:
        n = b.math('ADD', n, b.math('MULTIPLY', _field(mat, fields), gain))
    mask = b.ramp(n, lo, hi)
    if group:
        mask = b.math('MULTIPLY', mask, b.ramp(b.noise(Pp, group[0], 2, 0.5), group[1], group[2]))
    if amount != 1.0:
        mask = b.math('MULTIPLY', mask, amount)
    _layer(mat, mask, colour, rough, metal, height=depth)
    return mask


def add_stains(mat, colour, rough, scale=40.0, lo=0.5, hi=0.72, amount=0.35, detail=4, seed=(0.0, 0.0, 0.0), fields=None, gain=0.0):
    """Soft-edged patches of another tone (hand oil, a spill, sun-fade). fields and gain: gathered where it was held."""
    b = MT.NB(mat)
    Pp = b.vmath('ADD', _obj(mat), tuple(seed))
    n = b.noise(Pp, scale, detail, 0.55)
    if fields and gain:
        n = b.math('ADD', n, b.math('MULTIPLY', _field(mat, fields), gain))
    mask = b.math('MULTIPLY', b.ramp(n, lo, hi), amount)
    _layer(mat, mask, colour, rough, 0.0)
    return mask


def add_grime(mat, colour, rough, z0, z1, amount=0.5, cav=0.6, scale=75.0, ends=None, tide=None):
    """Grime that thickens downward: nothing above z1, `amount` at z0 and below (object space, metres), broken by a
    broad noise so it is a tide mark and not a ramp, plus what sits in the recesses (cav). ends: (x0, x1, width,
    amount) more of it towards the two ends of a can lying along X (against the end bells).
    tide: (amp, edge, line) a real tide mark: the top of the grime wanders by amp (metres) about z1 and fades over
    only `edge` (metres) instead of the whole z0..z1, with a darker line of `line` along its top where the dirt
    dried; below it the grime still thickens toward z0."""
    nt = mat.node_tree
    b = MT.NB(mat)
    Pp = _obj(mat)
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(Pp, sep.inputs[0])
    low = b.math('SUBTRACT', 1.0, b.ramp(sep.outputs['Z'], z0, z1))
    brk = b.math('ADD', 0.35, b.math('MULTIPLY', b.ramp(b.noise(Pp, scale, 4, 0.6), 0.3, 0.75), 1.3))
    if tide:
        amp, edge, line = tide
        wander = b.math('MULTIPLY', b.math('SUBTRACT', b.math('ADD', b.math('MULTIPLY', b.noise(Pp, scale * 0.6, 3, 0.55), 0.7),
                                                                    b.math('MULTIPLY', b.noise(Pp, scale * 4.0, 3, 0.6), 0.3)), 0.5), 2.0 * amp)
        dz = b.math('SUBTRACT', sep.outputs['Z'], b.math('ADD', z1, wander))          # 0 at the tide line, negative below
        under = b.math('SUBTRACT', 1.0, b.ramp(dz, -edge, 0.0))
        low = b.math('MULTIPLY', under, b.math('ADD', 0.45, b.math('MULTIPLY', low, 0.55)))
        crest = b.math('MULTIPLY', b.math('SUBTRACT', 1.0, b.ramp(b.math('ABSOLUTE', b.math('ADD', dz, edge * 0.5)), 0.0, edge * 0.7)), line)
        low = b.math('ADD', low, crest)
        brk = b.math('ADD', 0.6, b.math('MULTIPLY', b.ramp(b.noise(Pp, scale, 4, 0.6), 0.3, 0.75), 0.6))
    m = b.math('MULTIPLY', b.math('MULTIPLY', low, brk), amount)
    if ends:
        x0, x1, w, a = ends
        e = b.math('ADD', b.math('SUBTRACT', 1.0, b.ramp(sep.outputs['X'], x0, x0 + w)), b.ramp(sep.outputs['X'], x1 - w, x1))
        m = b.math('ADD', m, b.math('MULTIPLY', b.math('MULTIPLY', e, brk), a))
    if cav:
        m = b.math('ADD', m, b.math('MULTIPLY', _cavity(mat, 0.005, 0.06, 0.45), cav))
    m = b.math('MULTIPLY', m, b.math('ADD', 0.8, b.math('MULTIPLY', b.math('SUBTRACT', b.noise(Pp, 620.0, 3, 0.5), 0.5), 0.8)), clamp=True)
    _layer(mat, m, colour, rough, 0.0)
    return m


def add_chalk(mat, colour, rough, amount=0.3, scale=46.0, lo=0.3, hi=0.95):
    """Paint chalked and faded where it faced the sun: upward faces, in broad patches."""
    nt = mat.node_tree
    b = MT.NB(mat)
    Pp = _obj(mat)
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(geo.outputs['Normal'], sep.inputs[0])
    up = b.ramp(sep.outputs['Z'], lo, hi)
    m = b.math('MULTIPLY', b.math('MULTIPLY', up, b.math('ADD', 0.45, b.math('MULTIPLY', b.ramp(b.noise(Pp, scale, 3, 0.5), 0.32, 0.7), 0.55))), amount)
    _layer(mat, m, colour, rough, 0.0)
    return m


def add_cavity(mat, colour, rough, amount=1.0, dist=0.005, lo=0.05, hi=0.4, scale=420.0, metal=0.0, bump=0.8):
    """Rust and grime that sits in the recesses and round bolt heads (a permanent layer, not the as-found one)."""
    nt = mat.node_tree
    b = MT.NB(mat)
    Pp = _obj(mat)
    brk = b.math('ADD', 0.55, b.math('MULTIPLY', b.math('SUBTRACT', b.noise(Pp, scale, 4, 0.6), 0.5), 1.4))
    mask = b.math('MULTIPLY', b.math('MULTIPLY', _cavity(mat, dist, lo, hi), brk, clamp=True), amount, clamp=True)
    _layer(mat, mask, colour, rough, metal, height=bump)
    return mask


def add_chips(mat, colour, rough, metal, scale=150.0, lo=0.6, hi=0.64, fine=0.45, rim=None, depth=-0.6):
    """Paint chipped away in ragged flakes: where a noise passes a threshold the surface goes to the bare material
    underneath. rim: (colour, rough) a thin rusty or primed edge round each chip. fine: how much small pitting is added."""
    b = MT.NB(mat)
    Pp = _obj(mat)
    n = b.math('ADD', b.math('MULTIPLY', b.noise(Pp, scale, 6, 0.62), 0.75), b.math('MULTIPLY', b.noise(Pp, scale * 4.7, 4, 0.6), 0.25))
    if rim:
        _layer(mat, b.ramp(n, lo - (hi - lo) * 1.6, lo), rim[0], rim[1], 0.0)
    mask = b.ramp(n, lo, hi)
    if fine:
        pits = b.math('MULTIPLY', b.ramp(b.noise(Pp, scale * 9.0, 3, 0.5), 0.66, 0.7), fine)
        mask = b.math('MAXIMUM', mask, pits)
    _layer(mat, mask, colour, rough, metal, height=depth)
    return mask


def _dirty(mat):
    """The Value node the kit's baker drives: 0 = clean set, 1 = as-found set."""
    nt = mat.node_tree
    n = nt.nodes.get('DIRTY')
    if n is None:
        n = nt.nodes.new('ShaderNodeValue'); n.name = 'DIRTY'; n.outputs[0].default_value = 0.0
    return n.outputs[0]


def _cavity(mat, dist=0.0045, lo=0.08, hi=0.5):
    nt = mat.node_tree
    ao = nt.nodes.new('ShaderNodeAmbientOcclusion'); ao.only_local = True; ao.samples = 8
    ao.inputs['Distance'].default_value = dist
    b = MT.NB(mat)
    return b.ramp(b.math('SUBTRACT', 1.0, ao.outputs['AO']), lo, hi)


def add_dust(mat, colour, rough=0.96, amount=1.0, veil=0.2, cav=1.25, up=0.55, scale=1200.0, bump=0.9):
    """The as-found layer for a dusty surface, in place of the kit's wipe=('dust', ...): caked where the surface is
    sheltered (recesses, seams, round fasteners) and where it faces up, a thin powdery veil elsewhere, no camouflage
    blotches. It is the last layer of the material; the kit's baker finds it through the DIRTY node and mat['wipe']."""
    assert not mat.get('wipe'), 'add_dust goes on a material made without wipe='
    nt = mat.node_tree
    b = MT.NB(mat)
    Pp = _obj(mat)
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(geo.outputs['Normal'], sep.inputs[0])
    upm = b.ramp(sep.outputs['Z'], 0.05, 0.95)
    grain = b.noise(Pp, scale, 4, 0.65)
    drift = b.ramp(b.noise(Pp, 48.0, 3, 0.5), 0.3, 0.75)
    m = b.math('ADD', b.math('MULTIPLY', _cavity(mat), cav), b.math('MULTIPLY', b.math('MULTIPLY', upm, b.math('ADD', 0.45, b.math('MULTIPLY', drift, 0.55))), up))
    m = b.math('ADD', m, b.math('MULTIPLY', b.math('ADD', 0.55, b.math('MULTIPLY', drift, 0.9)), veil))
    m = b.math('MULTIPLY', m, b.math('ADD', 0.72, b.math('MULTIPLY', b.math('SUBTRACT', grain, 0.5), 0.9)))
    mask = b.math('MULTIPLY', b.math('MULTIPLY', m, amount, clamp=True), _dirty(mat), clamp=True)
    _layer(mat, mask, colour, rough, 0.0)
    if bump:
        bn = nt.nodes['BUMP']
        hsrc = bn.inputs['Height'].links[0].from_socket
        nt.links.remove(bn.inputs['Height'].links[0])
        nt.links.new(b.math('ADD', hsrc, b.math('MULTIPLY', b.math('MULTIPLY', mask, grain), bump)), bn.inputs['Height'])
    mat['wipe'] = 1
    return mask


def add_tarnish(mat, colour, rough=0.9, amount=1.0, base=0.3, cav=1.0, patch=0.55, scale=320.0, pit=0.0, bump=0.6):
    """The as-found layer for bare metal: grime in the recesses, an even dull film (base), and patches that thicken
    it (rust on steel: patch high, pit above 0 for fine pitting). Last layer of the material, as add_dust."""
    assert not mat.get('wipe'), 'add_tarnish goes on a material made without wipe='
    nt = mat.node_tree
    b = MT.NB(mat)
    Pp = _obj(mat)
    big = b.ramp(b.noise(Pp, scale, 5, 0.62), 0.46, 0.62)
    fine = b.ramp(b.noise(Pp, scale * 5.0, 4, 0.6), 0.3, 0.65)
    m = b.math('ADD', b.math('ADD', base, b.math('MULTIPLY', _cavity(mat, 0.003), cav)), b.math('MULTIPLY', b.math('MULTIPLY', big, fine), patch))
    if pit:
        m = b.math('ADD', m, b.math('MULTIPLY', b.ramp(b.noise(Pp, scale * 11.0, 3, 0.5), 0.62, 0.68), pit))
    mask = b.math('MULTIPLY', b.math('MULTIPLY', m, amount, clamp=True), _dirty(mat), clamp=True)
    _layer(mat, mask, colour, rough, 0.0)
    if bump:
        bn = nt.nodes['BUMP']
        hsrc = bn.inputs['Height'].links[0].from_socket
        nt.links.remove(bn.inputs['Height'].links[0])
        nt.links.new(b.math('ADD', hsrc, b.math('MULTIPLY', b.math('MULTIPLY', mask, fine), bump)), bn.inputs['Height'])
    mat['wipe'] = 1
    return mask


def add_stencil(mat, image_path, centre, ex, ey, width, height, colour, rough=0.62, amount=0.85, depth=0.004):
    """Stencilled lettering from a mask image (white = paint), projected flat onto the surface about centre (object
    space, metres): ex runs along the text, ey up it, width x height in metres. Only faces within depth of the
    plane take it. Call it BEFORE add_chips so the chips cut through the lettering."""
    import bpy
    nt = mat.node_tree
    b = MT.NB(mat)
    Pp = _obj(mat)
    ex = Vector(ex).normalized(); ey = Vector(ey).normalized(); n = ex.cross(ey)
    dv = b.vmath('SUBTRACT', Pp, tuple(centre))
    u = b.math('ADD', b.math('DIVIDE', b.vmath('DOT_PRODUCT', dv, tuple(ex)), width), 0.5)
    v = b.math('ADD', b.math('DIVIDE', b.vmath('DOT_PRODUCT', dv, tuple(ey)), height), 0.5)
    w = b.math('ABSOLUTE', b.vmath('DOT_PRODUCT', dv, tuple(n)))
    comb = nt.nodes.new('ShaderNodeCombineXYZ')
    nt.links.new(u, comb.inputs[0]); nt.links.new(v, comb.inputs[1])
    img = nt.nodes.new('ShaderNodeTexImage')
    img.image = bpy.data.images.load(image_path, check_existing=True)
    img.image.colorspace_settings.name = 'Non-Color'
    img.extension = 'CLIP'
    nt.links.new(comb.outputs[0], img.inputs['Vector'])
    gate = b.math('SUBTRACT', 1.0, b.ramp(w, depth * 0.7, depth))
    worn = b.ramp(b.noise(Pp, 520.0, 4, 0.6), 0.34, 0.5)            # the lettering is faded and partly gone
    mask = b.math('MULTIPLY', b.math('MULTIPLY', b.math('MULTIPLY', img.outputs['Color'], gate), worn), amount)
    _layer(mat, mask, colour, rough, 0.0)
    return mask


def add_streaks(mat, colour, rough, axis='Z', scale=(260.0, 260.0, 22.0), lo=0.52, hi=0.72, amount=0.6):
    """Grime or rust run down a surface: a noise stretched along one object axis."""
    b = MT.NB(mat)
    mp = mat.node_tree.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = scale
    mat.node_tree.links.new(_obj(mat), mp.inputs['Vector'])
    mask = b.math('MULTIPLY', b.ramp(b.noise(mp.outputs['Vector'], 1.0, 5, 0.6), lo, hi), amount)
    _layer(mat, mask, colour, rough, 0.0)
    return mask


def tube(name, pts, d, mat=None, segs=8, smooth=2, n=None):
    """Round wire or lead along points in metres (smoothed, resampled)."""
    Pp = G.chaikin(pts, smooth, False) if smooth else [Vector(p) for p in pts]
    if n:
        Pp = G.resample(Pp, n)
    return G.tube_path(name, Pp, d / 2, segs, mat)


def path_length(pts):
    return sum((Vector(b) - Vector(a)).length for a, b in zip(pts, pts[1:]))


def cut_path(pts, d0, d1):
    """The part of a polyline between arc lengths d0 and d1 (metres), ends interpolated."""
    Pp = [Vector(p) for p in pts]
    L = [0.0]
    for a, b in zip(Pp, Pp[1:]):
        L.append(L[-1] + (b - a).length)

    def at(d):
        d = min(max(d, 0.0), L[-1])
        for i in range(len(Pp) - 1):
            if L[i + 1] >= d - 1e-12:
                seg = L[i + 1] - L[i]
                return Pp[i].lerp(Pp[i + 1], 0.0 if seg < 1e-12 else (d - L[i]) / seg)
        return Pp[-1]
    out = [at(d0)] + [p for p, l in zip(Pp, L) if d0 + 1e-9 < l < d1 - 1e-9] + [at(d1)]
    return out
