"""Ward rooftops: the roof kit, Blender 5.2 headless (1 October 2026).

Next-wins item 8 (art-direction review, 30 Sep): "From the street every roofline is an unbroken cornice against the sky
... At 1.6 m eye height, the skyline is what the player sees above every shop. It is also where Ward's survival story
(water, power, air) can be told cheaply." This script authors the single objects that break those rooflines, each one
grounded in how Ward lives: water storage, dew/condensate collection, power and comms, ventilation, access and shade.

Every object is built on the shared Ward kit (art/ward_masonry_kit: Part, box-projected metre UVs, glTF export) and uses
the materials the shops already use (VH_*, WS_* in Art/VanguardHall and Art/WardShops, SD_Sack/SD_Rope from the street
dressing), plus four new ones made by RooftopsPass.cs (RT_DewNet, RT_SolarCell, RT_Ceramic, RT_Cable).

Coordinates are Unity metres: origin at the centre of the footprint on the roof deck (or on the wall / coping for wall
pieces, see each docstring), front = +Z, Y up. Uniform scale only; no object is stretched to fit a parcel - variants
(ladder heights, railing lengths) are authored at their real size.

Run:  $O/blender.sh author_roof_kit.py [-- id ...]
Out:  unity/AthenHill/Assets/AthenHill/Art/Rooftops/Models/RT_<id>_LOD0/1.glb and Models/kit.json
      (size, triangles, materials, shadow flag, anchors for the service cables)
"""
import bpy, bmesh, json, math, random, sys, zlib
from pathlib import Path
from mathutils import Vector, Matrix

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "art/ward_masonry_kit"))
import ward_masonry as WM
from ward_masonry import Part, lerp, export, tri_count, finalize_parts

OUT = ROOT / "unity/AthenHill/Assets/AthenHill/Art/Rooftops/Models"
OUT.mkdir(parents=True, exist_ok=True)

LOD = 0


def rng(*key):
    return random.Random(zlib.crc32(repr(key).encode()))


# ====================================================================== primitives on top of the kit's Part
def sweep_tube(part, pts, r, mat, sides=8, cap=True, r_end=None, min_sides=4):
    """Continuous tube along a polyline (parallel-transport frames, one ring per point, no joint spheres)."""
    pts = [Vector(p) for p in pts]
    n = len(pts)
    if n < 2:
        return []
    if LOD > 0:
        sides = max(min_sides, sides // 2)
    T = []
    for i in range(n):
        if i == 0:
            t = pts[1] - pts[0]
        elif i == n - 1:
            t = pts[-1] - pts[-2]
        else:
            t = (pts[i + 1] - pts[i]).normalized() + (pts[i] - pts[i - 1]).normalized()
        T.append(t.normalized())
    ref = Vector((0, 1, 0)) if abs(T[0].y) < 0.9 else Vector((1, 0, 0))
    N = T[0].cross(ref).normalized()
    rings = []
    for i in range(n):
        if i > 0:
            b = T[i - 1].cross(T[i])
            if b.length > 1e-7:
                N = Matrix.Rotation(T[i - 1].angle(T[i]), 3, b.normalized()) @ N
        B = T[i].cross(N).normalized()
        rr = r if r_end is None else lerp(r, r_end, i / (n - 1))
        # mitre: at a bend the ring is stretched along the in-plane perpendicular by 1/cos(half angle)
        perp, k = None, 1.0
        if 0 < i < n - 1:
            a_in, a_out = (pts[i] - pts[i - 1]).normalized(), (pts[i + 1] - pts[i]).normalized()
            q = a_out - a_in
            q = q - T[i] * q.dot(T[i])
            if q.length > 1e-6:
                perp = q.normalized()
                k = 1.0 / max(0.5, a_in.dot(T[i]))
        ring = []
        for s_ in range(sides):
            a = 2 * math.pi * s_ / sides
            d = N * math.cos(a) + B * math.sin(a)
            if perp is not None:
                d = d + perp * d.dot(perp) * (k - 1)
            ring.append(part.bm.verts.new(pts[i] + d * rr))
        rings.append(ring)
    idx = part.mi(mat)
    fs = []
    for i in range(n - 1):
        for s_ in range(sides):
            j = (s_ + 1) % sides
            fs.append(part.bm.faces.new([rings[i][s_], rings[i][j], rings[i + 1][j], rings[i + 1][s_]]))
    if cap:
        fs.append(part.bm.faces.new(rings[0][::-1]))
        fs.append(part.bm.faces.new(rings[-1]))
    for f in fs:
        f.material_index = idx
    return fs


def arc(c, r, a0, a1, u, v, n):
    """Points on an arc centre c, radius r, angles a0..a1 (deg) in the plane spanned by unit vectors u, v."""
    c, u, v = Vector(c), Vector(u), Vector(v)
    return [c + (u * math.cos(math.radians(lerp(a0, a1, i / n))) + v * math.sin(math.radians(lerp(a0, a1, i / n)))) * r for i in range(n + 1)]


def torus(part, c, axis, R, r, mat, n=24, m=8):
    """Closed ring (bands, hoops). axis = ring normal."""
    if LOD > 0:
        n, m = max(10, n // 2), max(4, m // 2)
    c, ax = Vector(c), Vector(axis).normalized()
    ref = Vector((0, 1, 0)) if abs(ax.y) < 0.9 else Vector((1, 0, 0))
    u = ax.cross(ref).normalized()
    v = ax.cross(u).normalized()
    verts, faces = [], []
    for i in range(n):
        t = 2 * math.pi * i / n
        d = u * math.cos(t) + v * math.sin(t)
        for j in range(m):
            p = 2 * math.pi * j / m
            verts.append(tuple(c + d * (R + r * math.cos(p)) + ax * r * math.sin(p)))
    for i in range(n):
        for j in range(m):
            a = i * m + j
            b = ((i + 1) % n) * m + j
            faces.append([a, b, ((i + 1) % n) * m + (j + 1) % m, i * m + (j + 1) % m])
    part.closed_solid(verts, faces, mat)


def bbox(part, c, s, mat, bev=0.0, bid=0, skip=()):
    lo = (c[0] - s[0] / 2, c[1] - s[1] / 2, c[2] - s[2] / 2)
    hi = (c[0] + s[0] / 2, c[1] + s[1] / 2, c[2] + s[2] / 2)
    vs, made = part.box(lo, hi, mat, bid, skip)
    if bev > 0 and LOD == 0:
        part.bevel_edges(list({e for f in made.values() for e in f.edges}), bev, 1)
    return made


def oriented_box(part, c, x_axis, y_axis, s, mat):
    """Box centred at c with its local x along x_axis, y along y_axis (z = x cross y), sizes s."""
    c = Vector(c)
    X = Vector(x_axis).normalized()
    Y = Vector(y_axis).normalized()
    Z = X.cross(Y).normalized()
    Y = Z.cross(X).normalized()
    hx, hy, hz = s[0] / 2, s[1] / 2, s[2] / 2
    pts = []
    for (sx, sz) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        pts.append(tuple(c + X * sx * hx - Y * hy + Z * sz * hz))
    for (sx, sz) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        pts.append(tuple(c + X * sx * hx + Y * hy + Z * sz * hz))
    return part.hexa(pts, mat)


def rod(part, a, b, r, mat, sides=8, cap=True):
    return part.cyl(a, b, r, mat, sides, cap)


def bolt_ring(part, c, axis, R, n, r, h, mat):
    if LOD > 0:
        return
    c, ax = Vector(c), Vector(axis).normalized()
    ref = Vector((0, 1, 0)) if abs(ax.y) < 0.9 else Vector((1, 0, 0))
    u = ax.cross(ref).normalized()
    v = ax.cross(u).normalized()
    for i in range(n):
        t = 2 * math.pi * (i + 0.5) / n
        p = c + (u * math.cos(t) + v * math.sin(t)) * R
        part.cyl(tuple(p), tuple(p + ax * h), r, mat, 6)


def sandbag(part, c, yaw, w=0.5, d=0.3, h=0.14, key=0):
    """Hessian sandbag (ballast): a rounded pillow, SD_Sack tiling linen at its own scale."""
    R = rng("bag", key)
    bid = part.new_block(scale=2.2, off=(R.uniform(0, 4), R.uniform(0, 4)))
    c = Vector(c)
    ca, sa = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    nu, nv = (6, 4) if LOD == 0 else (3, 2)
    verts, faces = [], []
    # a superellipsoid-ish pillow: rows over u (length) x v (width), top and bottom shells
    def P(u, v, top):
        x = u * w / 2
        z = v * d / 2
        edge = max(abs(u), abs(v)) ** 4
        y = (h * (1 - 0.85 * edge) * (0.92 + 0.08 * R.random())) if top else 0.0
        xw = x * (1 - 0.06 * (1 - abs(v)) * (1 if top else 0))
        return (c.x + xw * ca + z * sa, c.y + y, c.z - xw * sa + z * ca)
    us = [lerp(-1, 1, i / nu) for i in range(nu + 1)]
    vs = [lerp(-1, 1, j / nv) for j in range(nv + 1)]
    for top in (True, False):
        base = len(verts)
        for u in us:
            for v in vs:
                verts.append(P(u, v, top))
        for i in range(nu):
            for j in range(nv):
                a = base + i * (nv + 1) + j
                q = [a, a + nv + 1, a + nv + 2, a + 1]
                faces.append(q if top else q[::-1])
    # weld the rims: top and bottom share the outer ring (closed_solid merges by index only, so stitch side quads)
    vs_ = [part.bm.verts.new(Vector(p)) for p in verts]
    idx = part.mi("SD_Sack")
    fs = []
    for q in faces:
        fs.append(part.bm.faces.new([vs_[i] for i in q]))
    nt = (nu + 1) * (nv + 1)
    rim = [(i, 0) for i in range(nu + 1)] + [(nu, j) for j in range(1, nv + 1)] + [(i, nv) for i in range(nu - 1, -1, -1)] + [(0, j) for j in range(nv - 1, 0, -1)]
    for k in range(len(rim)):
        (i0, j0), (i1, j1) = rim[k], rim[(k + 1) % len(rim)]
        a, b = i0 * (nv + 1) + j0, i1 * (nv + 1) + j1
        try:
            fs.append(part.bm.faces.new([vs_[a], vs_[b], vs_[nt + b], vs_[nt + a]]))
        except ValueError:
            pass
    for f in fs:
        f.material_index = idx
        f[part.blk] = bid
    bmesh.ops.recalc_face_normals(part.bm, faces=fs)


def dish(part, c, aim, R0, depth, mat, ring=16):
    """Shallow paraboloid reflector (front and back faces), centre c, opening towards aim."""
    if LOD > 0:
        ring = 10
    aim = Vector(aim).normalized()
    ref = Vector((0, 1, 0)) if abs(aim.y) < 0.9 else Vector((1, 0, 0))
    s1 = aim.cross(ref).normalized()
    s2 = aim.cross(s1).normalized()
    c = Vector(c)
    rows = 4 if LOD == 0 else 2
    for back in (False, True):
        off = -aim * 0.012 if back else Vector()
        verts = [tuple(c + off)]
        for k in range(1, rows + 1):
            r = R0 * k / rows
            dd = depth * (k / rows) ** 2
            for i in range(ring):
                t = 2 * math.pi * i / ring
                verts.append(tuple(c + off + aim * dd + (s1 * math.cos(t) + s2 * math.sin(t)) * r))
        faces = [[0, 1 + (i + 1) % ring, 1 + i] for i in range(ring)]
        for k in range(rows - 1):
            for i in range(ring):
                a0 = 1 + k * ring + i
                a1 = 1 + k * ring + (i + 1) % ring
                faces.append([a0, a1, a1 + ring, a0 + ring])
        vs = [part.bm.verts.new(Vector(p)) for p in verts]
        idx = part.mi(mat)
        for f in faces:
            q = [vs[i] for i in (f[::-1] if back else f)]
            ff = part.bm.faces.new(q)
            ff.material_index = idx
    # rolled rim
    torus(part, tuple(c + aim * depth), aim, R0, 0.012, mat, 20, 5)


# ====================================================================== the kit
class Obj:
    def __init__(self, oid):
        self.id = oid
        self.parts = {}
        self.anchors = {}
        self.notes = ""
        self.shadows = False

    def p(self, key, wear=False):
        if key not in self.parts:
            self.parts[key] = Part(f"RT_{self.id}_{key}_LOD{LOD}", wear=wear)
        return self.parts[key]


def tank_tall(o):
    """Galvanised water tank on a braced four-leg stand with a ladder and platform: the roof's water store, filled by the
    Ward's aquifer line and the dew collectors. 1.5 m diameter, 1.75 m tall body on a 2.0 m stand (about 3 m3)."""
    o.notes = "galvanised 3 m3 water tank on a braced steel stand"
    o.shadows = True
    m = o.p("metal")
    L = 0.72                       # leg half-spacing
    H = 2.0                        # stand height
    for sx in (-1, 1):
        for sz in (-1, 1):
            x, z = sx * L, sz * L
            bbox(m, (x, H / 2, z), (0.07, H, 0.07), "VH_PaintedSteel", 0.006)
            bbox(m, (x, 0.008, z), (0.22, 0.016, 0.22), "VH_Steel")            # foot plate
            for bx, bz in ((-0.07, -0.07), (0.07, -0.07), (0.07, 0.07), (-0.07, 0.07)):
                rod(m, (x + bx, 0.0, z + bz), (x + bx, 0.05, z + bz), 0.009, "VH_Steel", 6)
    # ring beams and X bracing on each face
    for y in (0.18, H - 0.04):
        for sz in (-1, 1):
            bbox(m, (0, y, sz * L), (2 * L + 0.07, 0.06, 0.07), "VH_PaintedSteel", 0.005)
        for sx in (-1, 1):
            bbox(m, (sx * L, y, 0), (0.07, 0.06, 2 * L - 0.07), "VH_PaintedSteel", 0.005)
    for (a, b) in (((-L, -L), (L, -L)), ((L, -L), (L, L)), ((L, L), (-L, L)), ((-L, L), (-L, -L))):
        rod(m, (a[0], 0.24, a[1]), (b[0], H - 0.1, b[1]), 0.011, "VH_Steel", 6)
        rod(m, (b[0], 0.24, b[1]), (a[0], H - 0.1, a[1]), 0.011, "VH_Steel", 6)
    # platform deck (open grating as two plates with slots at LOD0)
    bbox(m, (0, H + 0.02, 0), (1.62, 0.04, 1.62), "VH_Dark", 0.004)
    # tank body
    r, y0, y1 = 0.75, H + 0.05, H + 1.8
    rod(m, (0, y0, 0), (0, y1, 0), r, "VH_Steel", 28)
    for y in (y0 + 0.06, y0 + 0.45, y0 + 0.9, y0 + 1.35, y1 - 0.06):
        torus(m, (0, y, 0), (0, 1, 0), r + 0.004, 0.014, "VH_Steel", 28, 5)
    if LOD == 0:
        for i in range(8):                                                       # vertical seams
            t = 2 * math.pi * (i + 0.5) / 8
            c = Vector((math.cos(t) * (r + 0.004), (y0 + y1) / 2, math.sin(t) * (r + 0.004)))
            oriented_box(m, tuple(c), (-math.sin(t), 0, math.cos(t)), (0, 1, 0), (0.03, y1 - y0 - 0.02, 0.008), "VH_Steel")
    # conical roof, hatch, vent
    m.cyl((0, y1, 0), (0, y1 + 0.26, 0), r + 0.03, "VH_Steel", 28, True, 0, 0.12)
    m.cyl((0, y1 + 0.26, 0), (0, y1 + 0.4, 0), 0.06, "VH_Steel", 10)
    m.cyl((0, y1 + 0.4, 0), (0, y1 + 0.47, 0), 0.13, "VH_Steel", 12, True, 0, 0.04)   # mushroom vent cap
    bbox(m, (0.0, y1 + 0.17, 0.42), (0.36, 0.05, 0.36), "VH_PaintedSteel", 0.004)   # roof hatch (on the cone, roughly)
    # outlet: from the bottom side down a leg to the deck and away to the roof hatch
    rod(m, (0.3, y0 + 0.08, r - 0.05), (0.3, y0 + 0.08, r + 0.12), 0.035, "VH_Steel", 10)
    sweep_tube(m, [(0.3, y0 + 0.08, r + 0.12), (0.3, 0.3, r + 0.12), (0.3, 0.06, r + 0.25), (0.3, 0.06, r + 0.7)], 0.035, "VH_Steel", 10)
    rod(m, (0.24, 0.9, r + 0.12), (0.36, 0.9, r + 0.12), 0.06, "WS_PaintRed", 10)        # valve body
    rod(m, (0.3, 0.9, r + 0.12), (0.3, 0.9, r + 0.26), 0.012, "VH_Steel", 6)
    torus(m, (0.3, 0.9, r + 0.27), (0, 0, 1), 0.07, 0.008, "WS_PaintRed", 12, 4)          # hand wheel
    # overflow
    sweep_tube(m, [(-0.35, y1 - 0.12, -r + 0.02), (-0.35, y1 - 0.12, -r - 0.12), (-0.35, y0 - 0.02, -r - 0.12), (-0.35, y0 - 0.15, -r - 0.2)], 0.025, "VH_Steel", 8)
    # ladder up the +X side of the stand and the tank
    lx = L + 0.24
    for zz in (-0.2, 0.2):
        rod(m, (lx, 0.0, zz), (lx, y1 + 0.35, zz), 0.016, "VH_Steel", 6)
    y = 0.3
    while y < y1 + 0.2:
        rod(m, (lx, y, -0.2), (lx, y, 0.2), 0.01, "VH_Steel", 6)
        y += 0.3
    for yy in (0.6, H - 0.2, H + 0.9):
        rod(m, (lx, yy, -0.18), (L if yy < H else r, yy, -0.18), 0.008, "VH_Steel", 5)
        rod(m, (lx, yy, 0.18), (L if yy < H else r, yy, 0.18), 0.008, "VH_Steel", 5)
    o.size_hint = (1.9, y1 + 0.47, 1.9)


def tank_low(o):
    """Horizontal painted tank (dye and wash water) on saddles atop a braced 1.15 m steel stand, so it clears the parapet:
    2.3 m long, 1.1 m diameter (about 2 m3), outlet and valve down to the deck."""
    o.notes = "horizontal painted 2 m3 tank on saddles on a raised stand"
    o.shadows = True
    m = o.p("metal")
    ST = 1.15                                                          # stand height
    r, Lh, yc = 0.55, 1.0, ST + 0.3 + 0.55
    # stand: four legs, ring frame at the top and near the foot, X bracing on the long sides, foot plates
    for sx in (-1, 1):
        for sz in (-1, 1):
            x, z = sx * 0.85, sz * 0.48
            bbox(m, (x, ST / 2, z), (0.07, ST, 0.07), "VH_PaintedSteel", 0.005)
            bbox(m, (x, 0.008, z), (0.2, 0.016, 0.2), "VH_Steel")
    for y in (0.16, ST - 0.04):
        for sz in (-1, 1):
            bbox(m, (0, y, sz * 0.48), (1.77, 0.07, 0.07), "VH_PaintedSteel", 0.004)
        for sx in (-1, 1):
            bbox(m, (sx * 0.85, y, 0), (0.07, 0.07, 0.9), "VH_PaintedSteel", 0.004)
    for sz in (-1, 1):
        rod(m, (-0.85, 0.2, sz * 0.48), (0.85, ST - 0.08, sz * 0.48), 0.01, "VH_Steel", 6)
        rod(m, (0.85, 0.2, sz * 0.48), (-0.85, ST - 0.08, sz * 0.48), 0.01, "VH_Steel", 6)
    bbox(m, (0, ST + 0.012, 0), (1.85, 0.024, 1.04), "VH_Dark", 0.003)                  # deck plate
    m.cyl((-Lh, yc, 0), (Lh, yc, 0), r, "WS_PaintOlive", 28, cap=False)
    for s_ in (-1, 1):                                                  # dished ends
        m.cyl((s_ * Lh, yc, 0), (s_ * (Lh + 0.12), yc, 0), r, "WS_PaintOlive", 28, cap=False, r2=r * 0.78)
        m.cyl((s_ * (Lh + 0.12), yc, 0), (s_ * (Lh + 0.17), yc, 0), r * 0.78, "WS_PaintOlive", 28, cap=True, r2=r * 0.35)
    for x in (-0.62, 0.0, 0.62):
        torus(m, (x, yc, 0), (1, 0, 0), r + 0.004, 0.013, "VH_Steel", 28, 5)
    for x in (-0.62, 0.62):                                           # saddles
        bbox(m, (x, ST + 0.17, 0), (0.08, 0.3, 0.84), "VH_PaintedSteel", 0.005)
        for z in (-0.38, 0.38):
            m.hexa([(x - 0.05, ST + 0.3, z - 0.06), (x + 0.05, ST + 0.3, z - 0.06), (x + 0.05, ST + 0.3, z + 0.06), (x - 0.05, ST + 0.3, z + 0.06),
                    (x - 0.05, yc - 0.32, z * 0.9 - 0.06), (x + 0.05, yc - 0.32, z * 0.9 - 0.06),
                    (x + 0.05, yc - 0.32, z * 0.9 + 0.06), (x - 0.05, yc - 0.32, z * 0.9 + 0.06)], "VH_PaintedSteel")
    # manway, vent, outlet down to the deck with a valve, fill hose
    m.cyl((0.3, yc + r - 0.03, 0), (0.3, yc + r + 0.1, 0), 0.22, "WS_PaintOlive", 20)
    m.cyl((0.3, yc + r + 0.1, 0), (0.3, yc + r + 0.14, 0), 0.25, "VH_Steel", 20)
    bolt_ring(m, (0.3, yc + r + 0.14, 0), (0, 1, 0), 0.22, 12, 0.012, 0.02, "VH_Steel")
    sweep_tube(m, [(-0.5, yc + r - 0.02, 0), (-0.5, yc + r + 0.32, 0), (-0.5, yc + r + 0.42, 0.1), (-0.5, yc + r + 0.36, 0.2)], 0.03, "VH_Steel", 8)
    sweep_tube(m, [(-1.2, yc - 0.3, 0), (-1.32, yc - 0.3, 0), (-1.32, 0.08, 0.0), (-1.32, 0.05, 0.45)], 0.032, "VH_Steel", 8)
    rod(m, (-1.32, 0.75, -0.07), (-1.32, 0.75, 0.07), 0.055, "WS_PaintRed", 10)
    torus(m, (-1.32, 0.75, 0.12), (0, 0, 1), 0.06, 0.008, "WS_PaintRed", 12, 4)
    sweep_tube(m, [(0.9, yc + r - 0.05, 0.2), (0.9, yc + r + 0.25, 0.2), (0.9, yc + r + 0.25, 0.62), (0.9, 0.06, 0.62)], 0.028, "VH_Rubber", 8)
    # access ladder up the +X end
    for zz in (-0.2, 0.2):
        rod(m, (1.05, 0.0, zz), (1.05, ST + 0.05, zz), 0.016, "VH_Steel", 6)
    y = 0.3
    while y < ST:
        rod(m, (1.05, y, -0.2), (1.05, y, 0.2), 0.01, "VH_Steel", 6)
        y += 0.3
    o.size_hint = (2.9, yc + r + 0.42, 1.2)


def dew_net(o):
    """Dew/condensate collector: two knitted shade-cloth nets between three steel posts (the outer two guyed), a gutter
    under them draining to a drum. Night air off the basin condenses on the mesh; Air + Water's slow trickle, made visible.
    Nets 2 x 1.3 x 1.6 m, 3.0 m tall."""
    o.notes = "dew/fog collector net on guyed posts, gutter and collection drum"
    m = o.p("metal")
    net = o.p("net")
    X, H = 1.42, 3.0
    for x in (-X, X):
        rod(m, (x, 0.0, 0), (x, H, 0), 0.038, "VH_Steel", 10)
        m.cyl((x, H, 0), (x, H + 0.04, 0), 0.045, "VH_Steel", 10)
        bbox(m, (x, 0.01, 0), (0.3, 0.02, 0.3), "VH_Steel")
        sandbag(m, (x, 0.02, 0.26), 0, 0.42, 0.24, 0.13, key=("dn", x, 1))
        sandbag(m, (x, 0.02, -0.26), 4, 0.42, 0.24, 0.13, key=("dn", x, 2))
        # guy wires fore and aft to plate anchors
        for dz in (-0.9, 0.9):
            rod(m, (x, H - 0.1, 0), (x * 0.85, 0.06, dz), 0.0045, "VH_Steel", 4, cap=False)
            bbox(m, (x * 0.85, 0.02, dz), (0.14, 0.04, 0.14), "VH_Steel")
    y0n, y1n = 1.32, 2.92
    rod(m, (0, 0.0, 0), (0, H - 0.08, 0), 0.03, "VH_Steel", 10)                       # centre post: two panels
    bbox(m, (0, 0.01, 0), (0.24, 0.02, 0.24), "VH_Steel")
    for y in (y0n - 0.03, y1n + 0.02):
        rod(m, (-X, y, 0), (X, y, 0), 0.016, "VH_Steel", 8)
    # two nets, each bellied between its posts and the rails (double-sided alpha-clipped knitted mesh)
    nu, nv = (8, 8) if LOD == 0 else (4, 4)
    idx = net.mi("RT_DewNet")
    for (xa, xb) in ((-X + 0.05, -0.05), (0.05, X - 0.05)):
        verts = []
        for i in range(nu + 1):
            for j in range(nv + 1):
                u, v = i / nu, j / nv
                x = lerp(xa, xb, u)
                y = lerp(y0n, y1n, v)
                belly = 0.09 * math.sin(math.pi * u) * math.sin(math.pi * v)
                verts.append((x, y - 0.035 * math.sin(math.pi * u) * (1 - 0.5 * v), belly))
        vs = [net.bm.verts.new(Vector(p)) for p in verts]
        for i in range(nu):
            for j in range(nv):
                a_ = i * (nv + 1) + j
                ff = net.bm.faces.new([vs[k] for k in (a_, a_ + nv + 1, a_ + nv + 2, a_ + 1)])
                ff.material_index = idx
        # a horizontal tension cord across the middle of each net, edge cords, lacing to the posts
        ym = (y0n + y1n) / 2
        sweep_tube(m, [(lerp(xa, xb, k / 8), ym - 0.035 * math.sin(math.pi * k / 8) * 0.5, 0.09 * math.sin(math.pi * k / 8) + 0.004)
                       for k in range(9)], 0.005, "SD_Rope", 4)
        for x in (xa, xb):
            rod(m, (x, y0n, 0), (x, y1n, 0), 0.006, "SD_Rope", 5)
            post = -X if x < -X + 0.1 else (X if x > X - 0.1 else 0.0)
            for k in range(5):
                y = lerp(y0n + 0.1, y1n - 0.1, k / 4)
                rod(m, (x, y, 0), (post, y, 0), 0.005, "SD_Rope", 4)
    # gutter trough under the net, falling to +X, downpipe into a drum
    gy = y0n - 0.16
    for z, h in ((-0.07, 0.1), (0.07, 0.1)):
        oriented_box(m, (0, gy, z), (1, -0.012, 0), (0, 1, 0), (2 * X - 0.1, h, 0.01), "VH_Steel")
    oriented_box(m, (0, gy - 0.05, 0), (1, -0.012, 0), (0, 1, 0), (2 * X - 0.1, 0.01, 0.15), "VH_Steel")
    for x in (-X + 0.1, X - 0.1):
        rod(m, (x, gy + 0.05, 0), (x, y0n - 0.03, 0), 0.008, "VH_Steel", 5)
    sweep_tube(m, [(X - 0.1, gy - 0.07, 0), (X + 0.05, gy - 0.2, 0.05), (X + 0.18, 0.95, 0.25), (X + 0.18, 0.86, 0.25)], 0.028, "VH_Steel", 8)
    rod(m, (X + 0.18, 0.0, 0.25), (X + 0.18, 0.86, 0.25), 0.29, "WS_PaintTeal", 20)           # collection drum
    for y in (0.29, 0.58):
        torus(m, (X + 0.18, y, 0.25), (0, 1, 0), 0.292, 0.012, "WS_PaintTeal", 20, 4)
    sweep_tube(m, [(X + 0.18 - 0.2, 0.08, 0.25 + 0.2), (X - 0.3, 0.05, 0.8), (X - 1.2, 0.05, 0.85)], 0.022, "VH_Rubber", 6)
    o.size_hint = (2 * X + 0.8, H + 0.04, 2.4)


def solar_frame(o):
    """Two photovoltaic panels on a ballasted galvanised frame, tilted 32 degrees and raised 0.9 m so they clear the low
    parapet and read from the avenue, with a combiner box and conduit."""
    o.notes = "two PV panels on a tilted ballasted frame"
    m = o.p("metal")
    g = o.p("glass")
    tilt = math.radians(32)
    W, Lp = 1.0, 1.65                            # panel width (x) and length along the slope
    y_front, z_front = 0.9, 0.62
    up = Vector((0, math.sin(tilt), -math.cos(tilt)))         # up the slope (towards the back, -Z)
    nrm = Vector((0, math.cos(tilt), math.sin(tilt)))         # panel normal (faces +Z and up)
    base = Vector((0, y_front, z_front))
    for i, xc in enumerate((-0.52, 0.52)):
        c = base + up * (Lp / 2) + Vector((xc, 0, 0)) + nrm * 0.035
        oriented_box(m, tuple(c - nrm * 0.015), (1, 0, 0), tuple(nrm), (W, 0.04, Lp), "VH_Steel")          # frame tray
        oriented_box(g, tuple(c + nrm * 0.008), (1, 0, 0), tuple(nrm), (W - 0.04, 0.01, Lp - 0.04), "RT_SolarCell")
        if LOD == 0:
            box_j = c - nrm * 0.05 + up * 0.3
            oriented_box(m, tuple(box_j), (1, 0, 0), tuple(nrm), (0.14, 0.04, 0.1), "VH_Dark")
    # trusses at x -0.95, 0, 0.95: front post, back post, rafter, brace, sole rail
    top_back = base + up * Lp
    for x in (-0.98, 0.0, 0.98):
        fb = Vector((x, 0.0, z_front))
        bb = Vector((x, 0.0, top_back.z))
        rod(m, tuple(fb), (x, y_front, z_front), 0.022, "VH_Steel", 8)
        rod(m, tuple(bb), (x, top_back.y, top_back.z), 0.022, "VH_Steel", 8)
        rod(m, (x, y_front, z_front), (x, top_back.y, top_back.z), 0.022, "VH_Steel", 8)
        rod(m, (x, 0.08, z_front), (x, top_back.y - 0.1, top_back.z), 0.012, "VH_Steel", 6)
        bbox(m, (x, 0.025, (z_front + top_back.z) / 2), (0.06, 0.05, z_front - top_back.z + 0.3), "VH_Steel", 0.004)
    for z in (z_front + 0.05, top_back.z - 0.05):
        bbox(m, (0, 0.03, z), (2.1, 0.04, 0.05), "VH_Steel", 0.004)
    for x in (-0.6, 0.6):
        for z in (z_front + 0.1, top_back.z - 0.15):
            sandbag(m, (x, 0.05, z), 3 if x > 0 else -2, 0.5, 0.3, 0.13, key=("sf", x, z))
    # combiner box and conduit down to the deck
    bbox(m, (1.12, 0.55, top_back.z + 0.1), (0.26, 0.32, 0.12), "VH_PaintedSteel", 0.006)
    sweep_tube(m, [(1.12, 0.39, top_back.z + 0.1), (1.12, 0.06, top_back.z + 0.1), (1.12, 0.04, top_back.z - 0.5)], 0.016, "VH_Rubber", 6)
    o.size_hint = (2.3, top_back.y + 0.08, z_front - top_back.z + 0.4)


def vent_cowl(o):
    """Gooseneck ventilation cowl: 200 mm galvanised stack from the space below, turned down against sand, with a bird mesh."""
    o.notes = "gooseneck vent cowl"
    m = o.p("metal")
    r, H, Rb = 0.1, 1.05, 0.17
    bbox(m, (0, 0.01, 0), (0.42, 0.02, 0.42), "VH_Steel", 0.004)                      # flashing plate
    m.cyl((0, 0.02, 0), (0, 0.16, 0), 0.2, "VH_Steel", 16, True, 0, 0.115)              # flashing cone
    rod(m, (0, 0.1, 0), (0, H, 0), r, "VH_Steel", 16)
    torus(m, (0, 0.5, 0), (0, 1, 0), r + 0.003, 0.012, "VH_Steel", 16, 4)
    # gooseneck: up, over a 180 degree bend of radius Rb towards +Z, mouth turned down
    pts = [Vector((0, H - 0.02, 0))]
    for k in range(9):
        a = math.radians(180 - 180 * k / 8)                     # 180 -> 0 degrees round the bend centre (0, H, Rb)
        pts.append(Vector((0, H + Rb * math.sin(a), Rb + Rb * math.cos(a))))
    pts.append(Vector((0, H - 0.12, 2 * Rb)))
    sweep_tube(m, pts, r, "VH_Steel", 16, cap=False)
    # mesh disc at the mouth and a mouth band
    c = Vector((0, H - 0.12, 2 * Rb))
    m.cyl(tuple(c + Vector((0, 0.005, 0))), tuple(c - Vector((0, 0.005, 0))), r - 0.004, "VH_Dark", 16)
    torus(m, tuple(c), (0, 1, 0), r + 0.004, 0.012, "VH_Steel", 16, 4)
    o.size_hint = (0.45, H + Rb + r, 2 * Rb + 2 * r)


def turbine_vent(o, ridge_deg=None):
    """Wind-driven turbine ventilator (whirlybird) on a short stack. ridge_deg: saddle flashing for a pitched ridge."""
    o.notes = "turbine ventilator" + (f" on a ridge saddle ({ridge_deg:.0f} deg)" if ridge_deg else "")
    m = o.p("metal")
    rs, Hs = 0.12, 0.55
    if ridge_deg is None:
        bbox(m, (0, 0.01, 0), (0.46, 0.02, 0.46), "VH_Steel", 0.004)
        m.cyl((0, 0.02, 0), (0, 0.14, 0), 0.21, "VH_Steel", 16, True, 0, rs + 0.02)
    else:
        t = math.tan(math.radians(ridge_deg))
        # two sloped flashing plates meeting at the ridge under the stack (origin = ridge line at the top of the sheets)
        for s in (-1, 1):
            a, b = 0.0, s * 0.42
            m.hexa([(a, 0.02, -0.3), (b, -0.42 * t + 0.02, -0.3), (b, -0.42 * t + 0.02, 0.3), (a, 0.02, 0.3),
                    (a, 0.035, -0.3), (b, -0.42 * t + 0.035, -0.3), (b, -0.42 * t + 0.035, 0.3), (a, 0.035, 0.3)], "VH_Steel")
        m.cyl((0, -0.06, 0), (0, 0.14, 0), rs + 0.035, "VH_Steel", 16, True, 0, rs + 0.02)
    rod(m, (0, 0.1, 0), (0, Hs, 0), rs, "VH_Steel", 16)
    torus(m, (0, Hs, 0), (0, 1, 0), rs + 0.02, 0.015, "VH_Steel", 16, 4)
    # head: 16 twisted vanes between two rings
    R, h0, h1 = 0.26, Hs + 0.03, Hs + 0.36
    torus(m, (0, h0, 0), (0, 1, 0), R * 0.86, 0.012, "VH_Steel", 20, 4)
    torus(m, (0, h1, 0), (0, 1, 0), R * 0.5, 0.012, "VH_Steel", 16, 4)
    nv = 16 if LOD == 0 else 10
    for i in range(nv):
        a0 = 2 * math.pi * i / nv
        pts = []
        for k in range(6):
            t = k / 5
            rr = lerp(R * 0.86, R * 0.5, t ** 1.6) + 0.06 * math.sin(math.pi * t)
            a = a0 + 0.6 * t
            pts.append(Vector((math.cos(a) * rr, lerp(h0, h1, t), math.sin(a) * rr)))
        for k in range(5):
            p0, p1 = pts[k], pts[k + 1]
            tang = (p1 - p0).normalized()
            radial = Vector((p0.x, 0, p0.z)).normalized()
            side = tang.cross(radial).normalized()
            oriented_box(m, tuple((p0 + p1) / 2), tuple(side), tuple(tang), (0.07, (p1 - p0).length + 0.004, 0.004), "VH_Steel")
    m.sphere((0, h1 + 0.01, 0), R * 0.5, "VH_Steel", 16 if LOD == 0 else 8, hemi_axis=(0, 1, 0))
    rod(m, (0, h1 + R * 0.5 - 0.02, 0), (0, h1 + R * 0.5 + 0.04, 0), 0.025, "VH_Steel", 8)
    o.size_hint = (0.6, h1 + R * 0.5 + 0.04, 0.6)


def whip(o):
    """HF whip antenna on a guyed stub mast with a loading coil and spring base; coax down to the deck. 6.4 m tall."""
    o.notes = "whip antenna on a guyed stub mast"
    m = o.p("metal")
    bbox(m, (0, 0.01, 0), (0.36, 0.02, 0.36), "VH_Steel", 0.004)
    bolt_ring(m, (0, 0.02, 0), (0, 1, 0), 0.13, 4, 0.012, 0.03, "VH_Steel")
    rod(m, (0, 0.0, 0), (0, 1.3, 0), 0.042, "VH_PaintedSteel", 12)
    for a in (90, 210, 330):
        t = math.radians(a)
        p = (math.cos(t) * 0.75, 0.05, math.sin(t) * 0.75)
        rod(m, (0, 1.15, 0), p, 0.004, "VH_Steel", 4, cap=False)
        bbox(m, (p[0], 0.02, p[2]), (0.1, 0.04, 0.1), "VH_Steel")
    m.cyl((0, 1.3, 0), (0, 1.36, 0), 0.06, "VH_Dark", 12)                                 # insulator base
    m.cyl((0, 1.36, 0), (0, 1.5, 0), 0.026, "VH_Steel", 10)                               # spring
    if LOD == 0:
        for k in range(6):
            torus(m, (0, 1.37 + k * 0.022, 0), (0, 1, 0), 0.028, 0.006, "VH_Steel", 10, 4)
    m.cyl((0, 1.5, 0), (0, 1.82, 0), 0.04, "VH_Dark", 12)                                 # loading coil
    m.cyl((0, 1.82, 0), (0, 6.35, 0), 0.011, "VH_Steel", 8, True, 0, 0.004)                # whip
    m.sphere((0, 6.36, 0), 0.012, "VH_Steel", 8)
    sweep_tube(m, [(0.03, 1.55, 0.03), (0.06, 1.3, 0.05), (0.06, 0.1, 0.05), (0.08, 0.03, 0.35), (0.08, 0.03, 0.9)], 0.009, "VH_Rubber", 6)
    o.size_hint = (1.6, 6.37, 1.6)


def comms_dish(o):
    """0.9 m comms dish on a non-penetrating mount (crossed channels with sandbag ballast), feed arm and LNB."""
    o.notes = "0.9 m dish on a ballasted non-penetrating mount"
    m = o.p("metal")
    for ang in (45, 135):
        t = math.radians(ang)
        oriented_box(m, (0, 0.04, 0), (math.cos(t), 0, math.sin(t)), (0, 1, 0), (1.25, 0.08, 0.06), "VH_PaintedSteel")
    for k, ang in enumerate((45, 135, 225, 315)):
        t = math.radians(ang)
        sandbag(m, (math.cos(t) * 0.48, 0.08, math.sin(t) * 0.48), ang + 90, 0.44, 0.26, 0.12, key=("dish", k))
    rod(m, (0, 0.08, 0), (0, 1.05, 0), 0.038, "VH_Steel", 10)
    for ang in (45, 135, 225, 315):
        t = math.radians(ang)
        rod(m, (math.cos(t) * 0.5, 0.08, math.sin(t) * 0.5), (0, 0.65, 0), 0.012, "VH_Steel", 6)
    aim = Vector((0, math.sin(math.radians(35)), math.cos(math.radians(35))))
    c = Vector((0, 1.12, 0.06))
    rod(m, (0, 1.0, 0), tuple(c - aim * 0.05), 0.03, "VH_Steel", 8)
    bbox(m, tuple(c - aim * 0.04), (0.18, 0.12, 0.05), "VH_Steel", 0.004)
    dish(m, tuple(c), tuple(aim), 0.45, 0.13, "VH_PaintedSteel")
    feed = c + aim * 0.42
    low = aim.cross(Vector((1, 0, 0))).normalized()
    if low.y > 0:
        low = -low
    rod(m, tuple(c + aim * 0.1 + low * 0.43), tuple(feed), 0.012, "VH_Steel", 6)     # feed arm from the lower rim
    m.cyl(tuple(feed), tuple(feed + aim * 0.12), 0.03, "VH_Dark", 10)
    sweep_tube(m, [tuple(feed - aim * 0.02), tuple(c + Vector((0, -0.25, -0.05))), (0.02, 0.9, -0.05), (0.03, 0.1, -0.04), (0.05, 0.03, -0.6)], 0.008, "VH_Rubber", 6)
    o.size_hint = (1.2, 1.5, 1.2)


def railing(o, length):
    """Parapet guard rail clamped to the inner face of the parapet: galvanised 48 mm tube, posts at <= 1.7 m, top rail
    1.0 m above the coping. Origin: coping top, inner edge, centre of the run; the run follows X; +Z = towards the street."""
    o.notes = f"parapet guard rail, {length:.2f} m"
    m = o.p("metal")
    n = max(2, int(math.ceil(length / 1.7)) + 1)
    xs = [lerp(-length / 2 + 0.06, length / 2 - 0.06, i / (n - 1)) for i in range(n)]
    zr = -0.05                                                     # just behind the inner coping edge
    for x in xs:
        rod(m, (x, -0.62, zr), (x, 0.98, zr), 0.024, "VH_Steel", 10)
        for y in (-0.18, -0.5):                                    # clamps on the parapet's inner face
            bbox(m, (x, y, zr + 0.035), (0.09, 0.07, 0.03), "VH_Steel", 0.003)
            rod(m, (x - 0.03, y, zr + 0.03), (x - 0.03, y, zr + 0.09), 0.008, "VH_Steel", 6)
            rod(m, (x + 0.03, y, zr + 0.03), (x + 0.03, y, zr + 0.09), 0.008, "VH_Steel", 6)
    for y in (1.0, 0.5):
        sweep_tube(m, [(xs[0], y, zr), (xs[-1], y, zr)], 0.024 if y == 1.0 else 0.02, "VH_Steel", 10)
        for x in (xs[0], xs[-1]):
            m.sphere((x, y, zr), 0.03, "VH_Steel", 8)
    if LOD == 0:
        for x in xs[1:-1]:
            for y in (1.0, 0.5):
                rod(m, (x - 0.04, y, zr), (x + 0.04, y, zr), 0.033, "VH_Steel", 10)      # tee fittings
    o.size_hint = (length, 1.62, 0.12)


def shade_frame(o):
    """Roof terrace shade: four steel pipe posts on sandbagged base plates, a pipe frame pitched to the back and a dyed
    canvas laced to it with rope, sagging. 3.0 x 2.4 m, 2.45 m at the front. Seats come from the street kit."""
    o.notes = "pipe-frame shade with a laced canvas, sandbag ballast"
    m = o.p("metal")
    c = o.p("cloth")
    X, Z = 1.4, 1.1
    hf, hb = 2.45, 2.1
    corners = [(-X, Z, hf), (X, Z, hf), (X, -Z, hb), (-X, -Z, hb)]
    for (x, z, h) in corners:
        rod(m, (x, 0.0, z), (x, h, z), 0.032, "VH_Steel", 10)
        bbox(m, (x, 0.01, z), (0.26, 0.02, 0.26), "VH_Steel", 0.003)
        ix, iz = -math.copysign(1, x), -math.copysign(1, z)          # bags on the inner side of each foot
        sandbag(m, (x + ix * 0.2, 0.02, z), 90, 0.42, 0.24, 0.12, key=("sh", x, z, 0))
        sandbag(m, (x, 0.02, z + iz * 0.2), 0, 0.42, 0.24, 0.12, key=("sh", x, z, 1))
        sandbag(m, (x + ix * 0.12, 0.13, z + iz * 0.12), 45, 0.42, 0.24, 0.11, key=("sh", x, z, 9))
    for a, b in zip(corners, corners[1:] + corners[:1]):
        rod(m, (a[0], a[2], a[1]), (b[0], b[2], b[1]), 0.028, "VH_Steel", 8)
    # diagonal brace on the back pair
    rod(m, (-X, 0.3, -Z), (X * 0.2, hb - 0.05, -Z), 0.015, "VH_Steel", 6)
    # canvas: grid inset from the frame, sagging in the middle and between lacings
    nu, nv = (14, 12) if LOD == 0 else (6, 5)
    ins = 0.12
    verts, faces = [], []
    R = rng("shade")
    for i in range(nu + 1):
        for j in range(nv + 1):
            u, v = i / nu, j / nv
            x = lerp(-X + ins, X - ins, u)
            z = lerp(Z - ins, -Z + ins, v)
            y = lerp(hf, hb, v) - 0.03
            sag = 0.1 * math.sin(math.pi * u) * math.sin(math.pi * v) + 0.025 * abs(math.sin(math.pi * u * 4)) * (1 - abs(2 * v - 1))
            verts.append((x, y - sag, z))
    for i in range(nu):
        for j in range(nv):
            a = i * (nv + 1) + j
            faces.append([a, a + nv + 1, a + nv + 2, a + 1])           # normal up (URP Lit does not flip back faces)
    vs = [c.bm.verts.new(Vector(p)) for p in verts]
    idx = c.mi("WS_ClothMadder")
    bid = c.new_block(off=(0.3, 0.7))
    for f in faces:
        ff = c.bm.faces.new([vs[k] for k in f])
        ff.material_index = idx
        ff[c.blk] = bid
    # lacing: short ropes from the canvas edge to the frame
    if LOD == 0:
        for i in range(0, nu + 1, 2):
            for j in (0, nv):
                p = Vector(verts[i * (nv + 1) + j])
                q = Vector((p.x, lerp(hf, hb, j / nv) + 0.02, Z if j == 0 else -Z))
                rod(m, tuple(p), tuple(q), 0.006, "SD_Rope", 4)
        for j in range(0, nv + 1, 2):
            for i in (0, nu):
                p = Vector(verts[i * (nv + 1) + j])
                q = Vector((-X if i == 0 else X, lerp(hf, hb, j / nv) + 0.02, p.z))
                rod(m, tuple(p), tuple(q), 0.006, "SD_Rope", 4)
    o.size_hint = (2 * X + 0.5, hf + 0.05, 2 * Z + 0.3)


def ladder(o, height):
    """Caged steel service ladder fixed to a wall: the street-to-roof access. Origin: the wall's frame plane at the foot
    (y 0 = street), +Z away from the wall. The rails stand 0.52 m off the wall to clear the shop cornices (0.43 m), rise
    1.05 m above the coping (height) and return over it to the roof deck (0.76 m below the coping)."""
    o.notes = f"caged service ladder to a {height:.2f} m coping"
    m = o.p("metal")
    zr, xr = 0.52, 0.23
    top = height + 1.05
    for x in (-xr, xr):
        pts = [(x, 0.0, zr), (x, top - 0.25, zr)]
        pts += [tuple(p) for p in arc((x, top - 0.25, zr - 0.25), 0.25, 0, 90, (0, 0, 1), (0, 1, 0), 5)][1:]
        pts += [(x, top, -0.42)]
        pts += [tuple(p) for p in arc((x, top - 0.2, -0.42), 0.2, 0, 90, (0, 1, 0), (0, 0, -1), 4)][1:]
        pts += [(x, height - 0.74, -0.62)]
        sweep_tube(m, pts, 0.03, "VH_Steel", 10)
        bbox(m, (x, 0.01, zr), (0.12, 0.02, 0.12), "VH_Steel")
    y = 0.3
    while y < height - 0.05:
        rod(m, (-xr, y, zr), (xr, y, zr), 0.013, "VH_Steel", 8)
        y += 0.3
    # wall brackets every ~1.8 m (stand-off arms from a plate on the stone)
    y = 0.6
    while y < height - 1.2:
        for x in (-xr, xr):
            bbox(m, (x, y, (zr + 0.06) / 2), (0.05, 0.06, zr - 0.06), "VH_Steel", 0.003)
            bbox(m, (x, y, 0.068), (0.12, 0.14, 0.012), "VH_Steel")
            if LOD == 0:
                for by in (-0.04, 0.04):
                    rod(m, (x, y + by, 0.074), (x, y + by, 0.09), 0.009, "VH_Steel", 6)
        y += 1.8
    # safety cage: hoops every 0.9 m from 2.4 m, five vertical straps
    hr = 0.36
    cz = zr + hr - 0.06
    hoops = []
    yc = 2.4
    while yc < top - 0.2:
        hoops.append(yc)
        yc += 0.9
    for yh in hoops:
        pts = [(-xr, yh, zr)]
        for k in range(11):
            a = math.radians(lerp(195, -15, k / 10))          # round the outside of the ladder
            pts.append((math.cos(a) * hr, yh, cz + math.sin(a) * hr))
        pts.append((xr, yh, zr))
        sweep_tube(m, pts, 0.012, "VH_Steel", 6, cap=False)
    if len(hoops) > 1:
        for k in range(5):
            a = math.radians(lerp(170, 10, k / 4))
            x, z = math.cos(a) * hr, cz + math.sin(a) * hr
            oriented_box(m, (x, (hoops[0] + hoops[-1]) / 2, z), (-math.sin(a), 0, math.cos(a)), (0, 1, 0),
                         (0.04, hoops[-1] - hoops[0] + 0.05, 0.006), "VH_Steel")
    o.size_hint = (0.9, top, 1.6)
    o.collider = {"center": [0, 1.1, (zr + 0.03 + 0.12) / 2], "size": [0.56, 2.2, zr + 0.03 - 0.12]}


def cable_mast(o, ridge_deg=None):
    """Service-line mast: 2.6 m galvanised pipe on a ballasted base (or a ridge saddle), crossarm with three porcelain pin
    insulators, a weatherhead and a junction box; three guy wires. Span cables leave the insulators along +-Z."""
    o.notes = "roof service-line mast with crossarm and pin insulators" + (f", ridge saddle {ridge_deg:.0f} deg" if ridge_deg else "")
    m = o.p("metal")
    ins = o.p("ceramic")
    H = 2.6
    if ridge_deg is None:
        bbox(m, (0, 0.012, 0), (0.5, 0.024, 0.5), "VH_Steel", 0.004)
        for k, (dx, dz) in enumerate(((0.38, 0), (-0.38, 0), (0, 0.38), (0, -0.38))):
            sandbag(m, (dx, 0.024, dz), 90 if dx else 0, 0.42, 0.24, 0.13, key=("cm", k))
        y0 = 0.02
        guy_y = lambda dx: 0.05
    else:
        t = math.tan(math.radians(ridge_deg))
        for s in (-1, 1):                                                   # saddle plates on both slopes
            m.hexa([(0, 0.03, -0.25), (s * 0.45, -0.45 * t + 0.03, -0.25), (s * 0.45, -0.45 * t + 0.03, 0.25), (0, 0.03, 0.25),
                    (0, 0.05, -0.25), (s * 0.45, -0.45 * t + 0.05, -0.25), (s * 0.45, -0.45 * t + 0.05, 0.25), (0, 0.05, 0.25)], "VH_Steel")
        bbox(m, (0, 0.08, 0), (0.16, 0.08, 0.5), "VH_Steel", 0.004)
        y0 = 0.04
        guy_y = lambda dx: -abs(dx) * t + 0.05
    rod(m, (0, y0, 0), (0, H, 0), 0.045, "VH_Steel", 12)
    m.cyl((0, H, 0), (0, H + 0.03, 0), 0.05, "VH_Steel", 12)
    # crossarm (along X; along Z on the ridge saddle so it lies across the span), braces, three pin insulators
    along_z = ridge_deg is not None
    A = (lambda a, y, b: (b, y, a)) if along_z else (lambda a, y, b: (a, y, b))       # (along-arm, y, across) -> xyz
    bbox(m, A(0, H - 0.18, 0), (0.07, 0.07, 1.1) if along_z else (1.1, 0.07, 0.07), "VH_PaintedSteel", 0.005)
    for s_ in (-1, 1):
        rod(m, A(0, H - 0.6, 0), A(s_ * 0.4, H - 0.22, 0), 0.012, "VH_Steel", 6)
    anchors = {}
    for k, a_ in enumerate((-0.45, 0.0, 0.45)):
        b_ = 0.0 if a_ != 0.0 else 0.09            # centre insulator offset to clear the pipe
        rod(m, A(a_, H - 0.145, b_), A(a_, H - 0.08, b_), 0.012, "VH_Steel", 6)
        if b_:
            bbox(m, A(0, H - 0.165, 0.05), (0.1, 0.03, 0.06) if along_z else (0.06, 0.03, 0.1), "VH_Steel")
        y = H - 0.08
        for (r0, h) in ((0.03, 0.03), (0.05, 0.025), (0.042, 0.03), (0.034, 0.025), (0.026, 0.03)):
            ins.cyl(A(a_, y, b_), A(a_, y + h, b_), r0, "RT_Ceramic", 12)
            y += h
        anchors["wire" + "abc"[k]] = [round(v, 4) for v in A(a_, y - 0.02, b_)]
    # weatherhead on top: a short gooseneck for the drop
    pts = [Vector((0.0, H + 0.03, 0))] + [Vector((0.0, H + 0.03 + 0.12 * math.sin(math.radians(a)), 0.12 - 0.12 * math.cos(math.radians(a)))) for a in range(20, 181, 32)]
    sweep_tube(m, [tuple(p) for p in pts], 0.022, "VH_Steel", 8)
    anchors["weatherhead"] = [0.0, round(H + 0.0, 4), 0.24]
    # junction box on the pipe and guy wires
    bbox(m, (0, 0.95, 0.1), (0.26, 0.34, 0.14), "VH_PaintedSteel", 0.006)
    anchors["box"] = [0.0, 0.8, 0.12]
    for a in (60, 180, 300):
        t_ = math.radians(a)
        dx, dz = math.cos(t_) * 0.8, math.sin(t_) * 0.8
        gy = guy_y(dx)
        rod(m, (0, H - 0.5, 0), (dx, gy + 0.02, dz), 0.0045, "VH_Steel", 4, cap=False)
        bbox(m, (dx, gy, dz), (0.1, 0.04, 0.1), "VH_Steel")
    o.anchors = anchors
    o.size_hint = (2.3, H + 0.18, 2.3)


def wall_hook(o):
    """Insulator hook on a wall plate for a service line between buildings. Origin: wall face; +Z out of the wall."""
    o.notes = "wall-plate insulator hook"
    m = o.p("metal")
    ins = o.p("ceramic")
    bbox(m, (0, 0, 0.006), (0.12, 0.16, 0.012), "VH_Steel")
    for by in (-0.05, 0.05):
        rod(m, (0, by, 0.012), (0, by, 0.03), 0.01, "VH_Steel", 6)
    sweep_tube(m, [(0, 0.0, 0.012), (0, 0.0, 0.16), (0, 0.05, 0.2)], 0.012, "VH_Steel", 6)
    y = 0.05
    for (r0, h) in ((0.026, 0.025), (0.04, 0.02), (0.03, 0.025)):
        ins.cyl((0, y, 0.2), (0, y + h, 0.2), r0, "RT_Ceramic", 10)
        y += h
    o.anchors = {"wire": [0.0, round(y - 0.015, 4), 0.2]}
    o.size_hint = (0.12, 0.3, 0.25)


def junction_box(o):
    """Wall-mounted steel junction/meter box with a hinged lid, glands below and a stub above. Origin: wall face at the box's
    bottom centre; +Z out of the wall. 0.4 x 0.55 x 0.2 m."""
    o.notes = "wall junction box"
    m = o.p("metal")
    W, Hh, Dd = 0.4, 0.55, 0.2
    bbox(m, (0, Hh / 2, Dd / 2 - 0.01), (W, Hh, Dd - 0.02), "VH_PaintedSteel", 0.008)
    bbox(m, (0, Hh / 2, Dd - 0.005), (W - 0.02, Hh - 0.02, 0.012), "VH_PaintedSteel", 0.004)       # lid
    bbox(m, (0, Hh + 0.02, Dd / 2), (W + 0.06, 0.02, Dd + 0.04), "VH_Steel", 0.003)                 # drip hood
    for y in (0.1, Hh - 0.1):
        rod(m, (W / 2 - 0.005, y - 0.04, Dd - 0.005), (W / 2 - 0.005, y + 0.04, Dd - 0.005), 0.012, "VH_Steel", 6)
    bbox(m, (-W / 2 + 0.04, Hh / 2, Dd + 0.005), (0.03, 0.08, 0.02), "VH_Steel")                     # latch
    bbox(m, (0.0, Hh - 0.12, Dd + 0.002), (0.12, 0.1, 0.004), "WS_PaintYellow")                     # warning plate (blank)
    for x in (-0.11, 0.0, 0.11):
        rod(m, (x, -0.04, 0.09), (x, 0.0, 0.09), 0.022, "VH_Dark", 8)
    rod(m, (0.12, Hh, 0.08), (0.12, Hh + 0.06, 0.08), 0.02, "VH_Dark", 8)
    o.anchors = {"top": [0.12, round(Hh + 0.06, 4), 0.08], "bottom": [0.0, -0.04, 0.09]}
    o.size_hint = (W + 0.06, Hh + 0.1, Dd + 0.04)


# ====================================================================== registry
RAIL_LENGTHS = [6.6, 3.2]
LADDER_HEIGHTS = [8.76, 9.19]
KIT = {
    "TankTall": tank_tall, "TankLow": tank_low, "DewNet": dew_net, "SolarFrame": solar_frame, "VentCowl": vent_cowl,
    "TurbineVent": turbine_vent, "TurbineVentRidge": lambda o: turbine_vent(o, ridge_deg=37.0), "Whip": whip, "Dish": comms_dish,
    "ShadeFrame": shade_frame, "CableMast": cable_mast, "CableMastRidge": lambda o: cable_mast(o, ridge_deg=37.0),
    "WallHook": wall_hook, "JunctionBox": junction_box,
}
for L_ in RAIL_LENGTHS:
    KIT[f"Rail{int(round(L_ * 100))}"] = (lambda L: (lambda o: railing(o, L)))(L_)
for H_ in LADDER_HEIGHTS:
    KIT[f"Ladder{int(round(H_ * 100))}"] = (lambda H: (lambda o: ladder(o, H)))(H_)


def build(oid, lod):
    global LOD
    LOD = lod
    WM.set_state(lod, random.Random(zlib.crc32(oid.encode())), "rt_" + oid)
    WM.reset_materials()
    o = Obj(oid)
    o.collider = None
    KIT[oid](o)
    coll = bpy.data.collections.new(f"RT_{oid}_LOD{lod}")
    bpy.context.scene.collection.children.link(coll)
    parts = [p for p in o.parts.values() if len(p.bm.faces)]
    finalize_parts(parts)
    objs = [p.build(coll, ao=None, macro=0.0, splash=0.0) for p in parts]
    return o, objs


def bounds(objs):
    # Blender -> Unity: (x, y, z)_b = (-x_u, -z_u, y_u)
    xs, ys, zs = [], [], []
    for ob in objs:
        for v in ob.data.vertices:
            xs.append(-v.co.x); ys.append(v.co.z); zs.append(-v.co.y)
    return [round(min(xs), 4), round(min(ys), 4), round(min(zs), 4)], [round(max(xs), 4), round(max(ys), 4), round(max(zs), 4)]


def main():
    ids = [a for a in sys.argv[sys.argv.index("--") + 1:]] if "--" in sys.argv else list(KIT)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rec_path = OUT / "kit.json"
    rec = json.loads(rec_path.read_text()) if rec_path.exists() else {}
    for oid in ids:
        entry = {"source": "art/rooftops_20261001/author_roof_kit.py", "lods": {}}
        for lod in (0, 1):
            o, objs = build(oid, lod)
            export(objs, OUT / f"RT_{oid}_LOD{lod}.glb")
            entry["lods"][f"LOD{lod}"] = tri_count(objs)
            if lod == 0:
                lo, hi = bounds(objs)
                entry.update(notes=o.notes, shadows=o.shadows, anchors=o.anchors, collider=o.collider, min=lo, max=hi,
                             size=[round(hi[i] - lo[i], 3) for i in range(3)],
                             materials=sorted({m.name for ob in objs for m in ob.data.materials}))
            print(f"RT_{oid} LOD{lod}: {tri_count(objs)} triangles", flush=True)
        rec[oid] = entry
    rec_path.write_text(json.dumps(rec, indent=1))
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "roof-kit-source.blend"))


if __name__ == "__main__":
    main()
