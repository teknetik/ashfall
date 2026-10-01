"""Ward hydroponics kit (1 Oct 2026): geometry helpers for author_hydroponics.py (Blender 5.2, bpy + numpy).

Everything is authored in **Unity coordinates** (x east, y up, z north; metres) into Geo accumulators and converted to
Blender only when an object is created (Blender = (-x, -z, y), the retrofit's U() convention, so the glTF export lands
back on the same Unity coordinates). Plants are built as leaf cards cut from textures/HY_CropAtlas.png (crop_atlas.json
gives each cell's UV rect and the leaf's width/height so cards are never stretched), with "dome" vertex normals so a head
shades as one volume instead of as flat cards.
"""
import json, math, random
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ATLAS = json.loads((HERE / "textures" / "crop_atlas.json").read_text())
GOLDEN = math.pi * (3 - math.sqrt(5))


def norm(v):
    v = np.asarray(v, float); n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    # Unity yaw: rotating +Z toward +X by angle a
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


class Geo:
    """Triangle/quad soup with per-vertex UV, optional per-vertex normals and a material per face."""

    def __init__(self):
        self.v, self.uv, self.n, self.f, self.m = [], [], [], [], []

    def __len__(self):
        return sum(len(f) - 2 for f in self.f)

    def add(self, verts, faces, uvs, mat, normals=None):
        base = len(self.v)
        self.v.extend([tuple(map(float, p)) for p in verts])
        self.uv.extend([tuple(map(float, t)) for t in uvs])
        if normals is None:
            self.n.extend([None] * len(verts))
        else:
            self.n.extend([tuple(map(float, q)) for q in normals])
        for f in faces:
            self.f.append(tuple(base + i for i in f)); self.m.append(mat)
        return base

    def extend(self, other, R=None, t=(0, 0, 0)):
        R = np.eye(3) if R is None else R
        base = len(self.v)
        V = np.asarray(other.v) @ R.T + np.asarray(t) if other.v else []
        self.v.extend([tuple(p) for p in V]); self.uv.extend(other.uv)
        self.n.extend([None if q is None else tuple(R @ np.asarray(q)) for q in other.n])
        self.f.extend([tuple(base + i for i in f) for f in other.f]); self.m.extend(other.m)

    def tris(self):
        return len(self)


# ------------------------------------------------------------------ primitives (Unity coordinates)
def box(g, c, s, mat, uvm=1.0, yaw=0.0, top=True, bottom=False):
    """Axis box centred at c with size s (x, y, z), turned by yaw about +Y. UV in metres / uvm per face."""
    R = rot_y(yaw); cx, cy, cz = c; hx, hy, hz = [v / 2 for v in s]
    faces = [((1, 0, 0), (0, 0, -1), (0, 1, 0), hz, hy, hx), ((-1, 0, 0), (0, 0, 1), (0, 1, 0), hz, hy, hx),
             ((0, 0, 1), (1, 0, 0), (0, 1, 0), hx, hy, hz), ((0, 0, -1), (-1, 0, 0), (0, 1, 0), hx, hy, hz)]
    if top: faces.append(((0, 1, 0), (1, 0, 0), (0, 0, -1), hx, hz, hy))
    if bottom: faces.append(((0, -1, 0), (1, 0, 0), (0, 0, 1), hx, hz, hy))
    for nrm, u, v, hu, hv, d in faces:
        nrm, u, v = np.array(nrm, float), np.array(u, float), np.array(v, float)
        ctr = np.array([cx, cy, cz]) + R @ (nrm * d)
        pts = [ctr + R @ (u * a * hu + v * b * hv) for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        uvs = [((a + 1) * hu / uvm, (b + 1) * hv / uvm) for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        g.add(pts, [(0, 1, 2, 3)], uvs, mat)


def quad(g, p, mat, uv=((0, 0), (1, 0), (1, 1), (0, 1)), normals=None):
    g.add(p, [(0, 1, 2, 3)], uv, mat, normals)


def tube(g, pts, r, mat, sides=6, uv_rect=None, uv_len=1.0, caps=False, r_end=None):
    """Tube along a polyline (Unity coords). uv_rect=(u0,v0,u1,v1) maps around x along into an atlas cell."""
    pts = [np.asarray(p, float) for p in pts]
    n = len(pts)
    if n < 2: return
    rings = []
    up = np.array([0, 1, 0.])
    prev_side = None
    L = 0.0; lens = [0.0]
    for i in range(1, n): L += np.linalg.norm(pts[i] - pts[i - 1]); lens.append(L)
    for i, p in enumerate(pts):
        d = norm(pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)])
        ref = up if abs(d @ up) < .95 else np.array([1, 0, 0.])
        side = norm(np.cross(d, ref)) if prev_side is None else norm(prev_side - d * (prev_side @ d))
        prev_side = side; other = np.cross(d, side)
        rr = r if r_end is None else r + (r_end - r) * (lens[i] / max(L, 1e-6))
        rings.append([p + rr * (math.cos(2 * math.pi * k / sides) * side + math.sin(2 * math.pi * k / sides) * other) for k in range(sides + 1)])
    verts, uvs, faces, nrms = [], [], [], []
    for i, ring in enumerate(rings):
        for k, q in enumerate(ring):
            verts.append(q); nrms.append(norm(q - pts[i]))
            a, b = k / sides, (lens[i] / uv_len if uv_len else 0.0)
            if uv_rect:
                u0, v0, u1, v1 = uv_rect
                uvs.append((u0 + (u1 - u0) * a, v0 + (v1 - v0) * ((lens[i] / max(L, 1e-6)) if uv_len == 0 else (b % 1.0))))
            else:
                uvs.append((a, b))
    for i in range(n - 1):
        for k in range(sides):
            a = i * (sides + 1) + k; b = a + sides + 1
            faces.append((a, a + 1, b + 1, b))
    g.add(verts, faces, uvs, mat, nrms)
    if caps:
        for i, sgn in ((0, -1), (n - 1, 1)):
            ring = rings[i][:-1]
            order = list(range(sides)) if sgn > 0 else list(range(sides))[::-1]
            g.add(ring, [tuple(order)], [(0.5, 0.5)] * sides, mat)


def cylinder(g, c, r, h, mat, sides=10, caps=True, uvm=1.0, axis="y"):
    c = np.asarray(c, float)
    d = {"y": np.array([0, 1, 0.]), "x": np.array([1, 0, 0.]), "z": np.array([0, 0, 1.])}[axis]
    a = c - d * h / 2; b = c + d * h / 2
    tube(g, [a, b], r, mat, sides=sides, uv_len=uvm, caps=caps)


def icosphere(g, c, r, mat, uv_rect, sub=0, squash=1.0):
    t = (1 + 5 ** .5) / 2
    V = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t), (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    F = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
         (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    V = [norm(v) for v in V]
    for _ in range(max(0, sub)):   # loop subdivision on the unit sphere (sub=1: 80 tris)
        mid = {}
        def m(a, b):
            k = (min(a, b), max(a, b))
            if k not in mid:
                mid[k] = len(V); V.append(norm(np.add(V[a], V[b]) / 2))
            return mid[k]
        F2 = []
        for a, b, c_ in F:
            ab, bc, ca = m(a, b), m(b, c_), m(c_, a)
            F2 += [(a, ab, ca), (b, bc, ab), (c_, ca, bc), (ab, bc, ca)]
        F = F2
    if sub == -1:   # octahedron (8 tris) for far LODs
        V = [norm(v) for v in [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]]
        F = [(2, 4, 0), (2, 0, 5), (2, 5, 1), (2, 1, 4), (3, 0, 4), (3, 5, 0), (3, 1, 5), (3, 4, 1)]
    c = np.asarray(c, float)
    u0, v0, u1, v1 = uv_rect
    verts = [c + np.array([p[0] * r, p[1] * r * squash, p[2] * r]) for p in V]
    uvs = [(u0 + (u1 - u0) * (.5 + .45 * p[0]), v0 + (v1 - v0) * (.5 + .45 * p[2])) for p in V]
    g.add(verts, F, uvs, mat, [norm(p) for p in V])


def cell_uv(key):
    return ATLAS[key]["uv"]


# ------------------------------------------------------------------ leaves
def leaf(g, mat, base, azimuth, elevation, length, cell, width_scale=1.0, droop=.35, cup=.22, twist=0.0,
         nu=2, nv=3, centre=None, dome=.65, flip=False, rng=None):
    """A leaf card from `base`: spine leaves at `elevation` (radians above horizontal) towards `azimuth` (Unity yaw),
    bending down by `droop` towards the tip; cupped across its width. UVs follow the atlas cell (petiole at v=0)."""
    info = ATLAS[cell]
    u0, v0, u1, v1 = info["uv"]; du, dv = u1 - u0, v1 - v0
    uh, uw, mg = info["used_h"], info["used_w"], info["margin"]
    width = length * info["aspect"] * width_scale
    base = np.asarray(base, float)
    hor = np.array([math.sin(azimuth), 0, math.cos(azimuth)])
    side = np.array([math.cos(azimuth), 0, -math.sin(azimuth)])
    if twist:
        c, s = math.cos(twist), math.sin(twist)
    verts, uvs, nrm = [], [], []
    # spine points
    spine = [base]; ang = []
    step = length / nv
    p = base.copy()
    for j in range(nv + 1):
        s_ = j / nv
        a = elevation - droop * (s_ ** 1.4) * 1.6
        ang.append(a)
    pts = [base.copy()]
    for j in range(nv):
        a = (ang[j] + ang[j + 1]) / 2
        p = p + (hor * math.cos(a) + np.array([0, 1, 0]) * math.sin(a)) * step
        pts.append(p.copy())
    cen = np.asarray(centre if centre is not None else base, float)
    for j in range(nv + 1):
        s_ = j / nv
        a = ang[j]
        fwd = hor * math.cos(a) + np.array([0, 1., 0]) * math.sin(a)
        up = np.cross(fwd, side) * (-1 if flip else 1)     # leaf normal (upper surface)
        sd = side
        if twist:
            sd = side * math.cos(twist * s_) + up * math.sin(twist * s_); up = np.cross(fwd, sd)
        # width profile: the sprite already carries the outline; keep the card full width, a little narrower at the base
        wprof = .75 + .25 * min(1, s_ * 3)
        for i in range(nu + 1):
            t = i / nu - .5
            q = pts[j] + sd * t * width * wprof + up * cup * width * (2 * t) ** 2 * (0.3 + s_)
            if rng is not None and j > 0:
                q = q + up * rng.uniform(-.012, .012) * length
            verts.append(q)
            uvs.append((u0 + du * (.5 + t * uw * wprof), v0 + dv * (mg + s_ * uh)))
            fn = up
            dn = norm(q - (cen + np.array([0, -.03, 0])))
            nrm.append(norm(fn * (1 - dome) + dn * dome))
    faces = []
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i; b = a + nu + 1
            faces.append((a, b, b + 1, a + 1))
    g.add(verts, faces, uvs, mat, nrm)


def cross_card(g, mat, base, height, width, cell, yaw=0.0, n=2, centre=None):
    """n vertical cards crossing at the base (seedlings, flower clusters, far LODs)."""
    info = ATLAS[cell]; u0, v0, u1, v1 = info["uv"]
    base = np.asarray(base, float)
    for k in range(n):
        a = yaw + math.pi * k / n
        sd = np.array([math.cos(a), 0, -math.sin(a)]) * width / 2
        p = [base - sd, base + sd, base + sd + [0, height, 0], base - sd + [0, height, 0]]
        cen = np.asarray(centre if centre is not None else base, float)
        nrm = [norm(q - cen + [0, .05, 0]) for q in p]
        g.add(p, [(0, 1, 2, 3)], [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], mat, nrm)


# ------------------------------------------------------------------ crops (base at origin; y up)
LETTUCE = {
    #  kind: (cells, leaves, spread elevation outer..inner (deg), droop, cup, leaf length factor outer..inner)
    "butter": (["butter_a", "butter_b"], 13, (18, 72), .45, .34, (.62, .38)),
    "cos": (["cos_a", "cos_b"], 10, (48, 82), .25, .2, (1.0, .7)),
    "lollo": (["oak_red"], 12, (22, 62), .4, .22, (.6, .42)),
    "rocket": (["oak_green"], 11, (28, 58), .35, .12, (.8, .55)),
}


def lettuce(g, mat, kind, size, rng, lod=0, at=(0, 0, 0), yaw=0.0):
    """A head of lettuce `size` metres across (0.08 seedling .. 0.3 mature)."""
    cells, n, (e_out, e_in), droop, cup, (l_out, l_in) = LETTUCE[kind]
    at = np.asarray(at, float)
    if lod >= 1:
        n = max(4, n // 2 + (1 if lod == 1 else -1))
    centre = at + np.array([0, size * .25, 0])
    for k in range(n):
        t = k / max(n - 1, 1)          # 0 outer .. 1 inner
        az = yaw + k * GOLDEN * (1 if lod == 0 else 1.9)
        el = math.radians(e_out + (e_in - e_out) * t + rng.uniform(-6, 6))
        L = size * (l_out + (l_in - l_out) * t) * rng.uniform(.9, 1.1) * (1.12 if lod else 1.0)
        b = at + np.array([math.sin(az), 0, math.cos(az)]) * size * .04 * (1 - t) + np.array([0, .004 + .01 * t, 0])
        leaf(g, mat, b, az, el, L, cells[k % len(cells)], width_scale=1.0 + (.15 if lod else 0), droop=droop * (1 - .6 * t),
             cup=cup * (1 + t), nu=2 if lod < 2 else 1, nv=3 if lod == 0 else 1, centre=centre, rng=rng if lod == 0 else None)


def chard(g, mat, size, rng, lod=0, at=(0, 0, 0), yaw=0.0, yellow=False):
    at = np.asarray(at, float)
    cell = "chard_yellow" if yellow else "chard_red"
    n = 7 if lod == 0 else 4
    centre = at + np.array([0, size * .5, 0])
    info = ATLAS[cell]; u0, v0, u1, v1 = info["uv"]
    rib = (u0 + (u1 - u0) * .495, v0 + (v1 - v0) * .05, u0 + (u1 - u0) * .505, v0 + (v1 - v0) * .3)
    for k in range(n):
        az = yaw + k * GOLDEN * (1 if lod == 0 else 2)
        el = math.radians(rng.uniform(58, 80))
        stalk = size * rng.uniform(.28, .4)
        hor = np.array([math.sin(az), 0, math.cos(az)])
        top = at + hor * stalk * math.cos(el) + np.array([0, stalk * math.sin(el), 0])
        if lod == 0:
            tube(g, [at + hor * .005, top], .006, mat, sides=3, uv_rect=rib, uv_len=0)
        leaf(g, mat, top, az, el - .15, size * rng.uniform(.55, .7), cell, droop=.35, cup=.15, nu=2 if lod == 0 else 1,
             nv=3 if lod == 0 else 1, centre=centre, rng=rng if lod == 0 else None)


def basil(g, mat, size, rng, lod=0, at=(0, 0, 0), yaw=0.0, cell="basil_leaf"):
    """Bushy herb: a few stems, opposite leaf pairs at nodes, a terminal cluster."""
    at = np.asarray(at, float)
    stems = 4 if lod == 0 else 3
    centre = at + np.array([0, size * .45, 0])
    for s in range(stems):
        az = yaw + s * 2 * math.pi / stems + rng.uniform(-.3, .3)
        lean = rng.uniform(.1, .35)
        h = size * rng.uniform(.75, 1.0)
        top = at + np.array([math.sin(az) * lean * h, h, math.cos(az) * lean * h])
        if lod == 0:
            tube(g, [at, top], .004, mat, sides=3, uv_rect=cell_uv("stem"), uv_len=0)
        nodes = 3 if lod == 0 else 2
        for j in range(nodes):
            f = (j + 1) / (nodes + .5)
            p = at + (top - at) * f
            pa = az + (math.pi / 2 if j % 2 else 0)
            for side in (0, math.pi):
                leaf(g, mat, p, pa + side, math.radians(rng.uniform(15, 35)), size * .38 * (1.1 - .3 * f), cell, droop=.3, cup=.25,
                     nu=1 if lod else 2, nv=1 if lod else 2, centre=centre)
        for k in range(3 if lod == 0 else 2):
            leaf(g, mat, top, az + k * 2.1, math.radians(55), size * .26, cell, droop=.2, cup=.3, nu=1, nv=1 if lod else 2, centre=centre)


def seedling_patch(g, mat, x0, x1, z0, z1, y, pitch, rng, lod=0, cell="seedling", h=(.035, .06)):
    if lod >= 1:
        return
    xs = np.arange(x0 + pitch / 2, x1, pitch); zs = np.arange(z0 + pitch / 2, z1, pitch)
    for x in xs:
        for z in zs:
            if rng.random() < .08: continue
            hh = rng.uniform(*h)
            cross_card(g, mat, (x + rng.uniform(-.004, .004), y, z + rng.uniform(-.004, .004)), hh, hh * 1.1, cell, yaw=rng.uniform(0, math.pi))


def tomato_vine(g, mat, base, top_y, rng, lod=0, facing=0.0, trusses=4, string=True):
    """Cordon tomato on a string: bare lower stem (leaves stripped), ripening trusses low (red) to high (green), compound
    leaves on the upper stem, a growing tip under the wire. `facing` = yaw of the aisle-side (leaves spread across it)."""
    base = np.asarray(base, float)
    H = top_y - base[1] - .12
    sides = 4 if lod == 0 else 3
    segs = 14 if lod == 0 else 5
    ph = rng.uniform(0, 6.28)
    pts = []
    for i in range(segs + 1):
        t = i / segs
        a = ph + t * H / .55 * 2 * math.pi
        rr = .018 if lod == 0 else 0
        pts.append(base + np.array([math.cos(a) * rr, H * t, math.sin(a) * rr]))
    tube(g, pts, .011 if lod == 0 else .013, mat, sides=sides, uv_rect=cell_uv("stem"), uv_len=0, r_end=.006)
    if string and lod == 0:
        s0 = base + np.array([0, H * .95, 0]); s1 = base + np.array([0, top_y - base[1], 0])
        tube(g, [s0, s1], .002, mat, sides=3, uv_rect=cell_uv("twine"), uv_len=0)
    # trusses: heights and ripeness (0 red .. 3 green)
    for k in range(trusses):
        y = base[1] + .38 + k * .24 + rng.uniform(-.03, .03)
        ripe = min(3, max(0, k - 1 + (1 if rng.random() < .3 else 0)))
        az = facing + rng.uniform(-.9, .9)
        d = np.array([math.sin(az), 0, math.cos(az)])
        stem_p = base + np.array([0, y - base[1], 0])
        tip = stem_p + d * .09 + np.array([0, -.05, 0])
        if lod == 0:   # truss stalk: a little thicker so it reads green, not as a dark line
            tube(g, [stem_p, stem_p + d * .05 + [0, .01, 0], tip], .0045, mat, sides=4, uv_rect=cell_uv("stem"), uv_len=0)
        nfr = (5 if lod == 0 else 3) - (1 if ripe == 3 else 0)
        for f in range(nfr):
            p = tip + d * (f * .045) + np.array([0, -.035 - (f % 2) * .03, 0]) + np.cross(d, [0, 1, 0]) * ((f % 2) - .5) * .05
            r = rng.uniform(.026, .036) * (.8 if ripe == 3 else 1)
            icosphere(g, p, r, mat, cell_uv(f"fruit_{ripe if rng.random() > .25 else max(0, ripe - 1)}"), sub=1 if lod == 0 else -1, squash=.86)
    # leaves: the lower third is stripped (growers de-leaf below the ripening trusses), dense compound leaves above,
    # spiralling round the stem so the row reads as a green wall from the skin and the aisle
    y = base[1] + H * .3
    k = 0
    while y < base[1] + H * .97:
        az = (k * 2.4 + rng.uniform(-.4, .4)) if k % 3 else (math.pi / 2 if k % 2 else -math.pi / 2) + rng.uniform(-.7, .7)
        p = base + np.array([0, y - base[1], 0])
        top = (y - base[1]) / H
        leaf(g, mat, p, az, math.radians(rng.uniform(10, 38)), rng.uniform(.32, .44) * (1.05 - .25 * max(0, top - .75) / .25),
             "tomato_leaf_a" if k % 3 else "tomato_leaf_b", droop=.55, cup=-.05, nu=2 if lod == 0 else 1, nv=3 if lod == 0 else 1,
             centre=p + [0, .1, 0], dome=.35)
        y += rng.uniform(.12, .17) * (1 if lod == 0 else 1.7)
        k += 1
    # a few stubs where lower leaves were taken off, and the growing tip
    if lod == 0:
        tip_p = base + np.array([0, H, 0])
        for j in range(3):
            leaf(g, mat, tip_p, rng.uniform(0, 6.28), math.radians(60), .12, "tomato_leaf_b", droop=.2, cup=0, nu=1, nv=2, centre=tip_p)


def bean_vine(g, mat, base, top_y, rng, lod=0, facing=0.0):
    """Runner bean twining up a string: trifoliate leaves all the way up, scarlet flower sprays, hanging pods."""
    base = np.asarray(base, float)
    H = top_y - base[1] - .1
    segs = 16 if lod == 0 else 5
    ph = rng.uniform(0, 6.28)
    pts = [base + np.array([math.cos(ph + t * H / .3 * 6.28) * .012 * (lod == 0), H * t, math.sin(ph + t * H / .3 * 6.28) * .012 * (lod == 0)])
           for t in np.linspace(0, 1, segs + 1)]
    tube(g, pts, .005 if lod == 0 else .008, mat, sides=3, uv_rect=cell_uv("stem"), uv_len=0)
    if lod == 0:
        tube(g, [base + [0, H * .9, 0], base + [0, top_y - base[1], 0]], .002, mat, sides=3, uv_rect=cell_uv("twine"), uv_len=0)
    y = base[1] + .12; k = 0
    while y < base[1] + H:
        az = (k * 2.4 + rng.uniform(-.5, .5)) if k % 3 == 2 else (math.pi / 2 if k % 2 else -math.pi / 2) + rng.uniform(-.9, .9)
        p = base + np.array([0, y - base[1], 0])
        # trifoliate: a short petiole then the leaf card laid out (centred cell: base at card centre)
        leaf(g, mat, p, az, math.radians(rng.uniform(5, 30)), rng.uniform(.14, .19), "bean_leaf_a" if k % 2 else "bean_leaf_b",
             droop=.3, cup=.08, nu=2 if lod == 0 else 1, nv=2 if lod == 0 else 1, centre=p, dome=.4)
        if lod == 0 and .55 < (y - base[1]) / H < .95 and rng.random() < .35:
            cross_card(g, mat, p + np.array([math.sin(az), 0, math.cos(az)]) * .05, .08, .07, "flower", yaw=az, n=2, centre=p)
        if .2 < (y - base[1]) / H < .7 and rng.random() < (.45 if lod == 0 else .25):
            pp = p + np.array([math.sin(az + 1.2), 0, math.cos(az + 1.2)]) * .04
            q = [pp + [-.008, -.16, 0], pp + [.008, -.16, 0], pp + [.008, 0, 0], pp + [-.008, 0, 0]]
            u0, v0, u1, v1 = cell_uv("pod")
            g.add(q, [(0, 1, 2, 3)], [(u0 + (u1 - u0) * .35, v0), (u0 + (u1 - u0) * .65, v0), (u0 + (u1 - u0) * .65, v1), (u0 + (u1 - u0) * .35, v1)], mat,
                  [norm([math.sin(az), .3, math.cos(az)])] * 4)
        y += rng.uniform(.075, .105) * (1 if lod == 0 else 1.7); k += 1
