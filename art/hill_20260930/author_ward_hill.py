"""Hill and hero-tree base rebuild, Blender 5.2 headless (30 September 2026).

Carl (30 Sep 2026): "having rebuilt the vanguard building and ones close by I would like to do a similar pass on the hero
tree and hill. note the image how its circled in stone, stone like the walls of the other buildings so it matches."
Reference: his edited screenshot (tree ringed by a low masonry wall, planted beds, paved paths). The ring uses the
Vanguard Hall / hall-district stone (shared kit art/ward_masonry_kit, Athen Hill/Masonry Lit), not the brick in the edit.

Run:  blender -b --python-exit-code 1 -P author_ward_hill.py

What it builds (Unity metres local to the hill root at world (0, 0, 0); layout constants in hill_layout.py):
* retaining walls on all four sides of the 14 x 14 m plinth: rough foot course, two dressed courses, quoined corners,
  a 0.42 m coping band flush with the hilltop (the plinth and surface colliders are unchanged);
* the three 4 m stairs (6 x 0.25 m risers, 0.6 m treads, exactly on the saved step colliders) as dressed step stones with
  worn, dished nosings between raking-coped cheek walls with capstones at the stair heads;
* the tree ring: one dressed course (outer face r 3.30) and a curved coping 0.49 m above the paving, inner face r 2.85,
  a root-heaved coping stone repaired with iron cramps, three bronze uplights in the coping;
* hilltop paving: a curved apron round the ring, three flagged paths with landings, kerbed planting beds, stone pads and
  stepping stones for the three terminals, a stone under Linn;
* soil: bed soil and a leaf-litter dome inside the ring; surface roots from the trunk flare; sheltered sand at the wall
  foot and in the stair corners (LOD0); weathering (runoff under copings, rust under cramps, old battle damage).

Outputs: unity/AthenHill/Assets/AthenHill/Art/WardHill/Models/WardHill_LOD0.glb, WardHill_LOD1.glb, ward-hill.json
(colliders, terminal mounts, uplights, ring/soil collider specs, bed polygons) and art/hill_20260930/hill-source.blend.
"""
import bpy, bmesh, json, math, random, sys
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "art/ward_masonry_kit"))
sys.path.insert(0, str(HERE))
import ward_masonry as WM
from ward_masonry import (Part, Frame, stone_tint, ashlar_block, fill_wall, sweep, eroded_bevel, split_edge, finalize_parts,
                          AOBaker, DripSet, U, lerp, smoothstep, drng, export, tri_count, MORTAR_FRONT, ScarSet,
                          scatter_impacts, triangulate, material)
import hill_layout as H

OUT = ROOT / "unity/AthenHill/Assets/AthenHill/Art/WardHill/Models"
OUT.mkdir(parents=True, exist_ok=True)
J = 0.009
QD, QL, QS = 0.092, 0.82, 0.44     # quoins as on the hall-district shops


def V2(x, z):
    return Vector((x, 0.0, z))


def side_axes(n):
    """Outward normal N and lateral axis L (the kit's frame u axis for that normal) as 3D vectors."""
    N = Vector((n[0], 0.0, n[1]))
    L = Vector((N.z, 0.0, -N.x))
    return N, L


# ====================================================================== ring drips (radial runoff)
class HillDrips:
    """Axis-aligned drips (retaining walls, cheeks) plus radial runoff below the ring coping and rust below cramps."""

    def __init__(self):
        self.axis = DripSet(base=0.0, base_top=None, ground_y=0.0)
        self.ring = []   # (angle_deg, width_deg, kind, strength)

    def eval(self, p, n):
        g, r = self.axis.eval(p, n)
        if abs(n.y) < 0.6:
            dx, dz = p.x - H.RING_C[0], p.z - H.RING_C[1]
            rad = math.hypot(dx, dz)
            if H.RI - 0.2 < rad < H.RO + 0.2 and p.y < H.RING_CAP[0] + 0.02:
                radial = (n.x * dx + n.z * dz) / max(rad, 1e-6)
                if abs(radial) > 0.45:
                    t = max(0.0, min(1.0, (H.RING_CAP[0] - p.y) / 0.34))
                    a = math.degrees(math.atan2(dz, dx)) % 360
                    streak = 0.55 + 0.45 * H.vnoise(a * 0.09, 0.0, 1.0, 11)
                    g = max(g, 0.62 * streak * (1 - t) ** 1.3)
                    for ang, width, kind, st in self.ring:
                        da = abs((a - ang + 180) % 360 - 180)
                        if da < width:
                            w = st * (1 - da / width) * (1 - t) ** 1.1
                            if kind == "rust":
                                r = max(r, w)
                            else:
                                g = max(g, w)
        return min(1.0, g), min(1.0, r)


# ====================================================================== geometry helpers
def prism(part, poly, y0, y1, mat, bid=0, bottom=False, top_y=None):
    """Vertical prism over a CCW (x, z) polygon. top_y(x, z) optionally shapes the top face (per vertex)."""
    n = len(poly)
    bm = part.bm
    vb = [bm.verts.new(Vector((x, y0, z))) for x, z in poly]
    vt = [bm.verts.new(Vector((x, top_y(x, z) if top_y else y1, z))) for x, z in poly]
    idx = part.mi(mat)
    faces = []
    top = bm.faces.new(vt)
    faces.append(top)
    if bottom:
        faces.append(bm.faces.new(vb[::-1]))
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new([vb[i], vb[j], vt[j], vt[i]]))
    for f in faces:
        f.material_index = idx
        f[part.blk] = bid
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    # recalc can flip open shells inwards: force the top face up
    top.normal_update()
    if top.normal.y < 0:
        for f in faces:
            f.normal_flip()
    return top, faces


def obox(part, c, t, hu, hv, y0, y1, mat, bid=0):
    """Box centred at c (x, z) with its u axis along the unit xz vector t."""
    tx, tz = t
    nx, nz = -tz, tx
    pts = [(c[0] + tx * a * hu + nx * b * hv, c[1] + tz * a * hu + nz * b * hv) for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    corners = [Vector((x, y0, z)) for x, z in pts] + [Vector((x, y1, z)) for x, z in pts]
    return part.hexa(corners, mat, bid)


def poly_ccw(poly):
    a = sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))
    return poly if a > 0 else poly[::-1]


def flag(part, poly, top, mat="VH_PodiumSlab", thick=0.1, bev=(0.006, 0.014), key=None, rough=True, dish=None):
    """One paving stone (prism) with an eroded bevel round its top face."""
    rr = drng("flag", key) if key is not None else random.Random(0)
    bid = part.new_block(tint=stone_tint("rough" if rough else "ashlar"), erode=0.004 + 0.006 * rr.random())
    t, fs = prism(part, poly_ccw(poly), top - thick, top, mat, bid)
    eroded_bevel(part, list(t.edges), rr.uniform(*bev), 2, seg_len=0.16)
    return t


def circle_pts(r, a0, a1, step=0.25, c=H.RING_C):
    """Points on a circle from angle a0 to a1 (degrees, a1 > a0), about `step` metres apart."""
    n = max(1, int(math.ceil(math.radians(a1 - a0) * r / step)))
    return [(c[0] + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), c[1] + r * math.sin(math.radians(a0 + (a1 - a0) * i / n)))
            for i in range(n + 1)]


def clip_outside_circle(poly, r, step=0.04):
    """Push the parts of a convex polygon that fall inside the circle r (about RING_C) out onto it."""
    pts = []
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        k = max(1, int(L / step))
        for s in range(k):
            t = s / k
            pts.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    out = []
    inside = 0
    for x, z in pts:
        d = math.hypot(x - H.RING_C[0], z - H.RING_C[1])
        if d < r:
            inside += 1
            x, z = H.RING_C[0] + (x - H.RING_C[0]) * r / max(d, 1e-6), H.RING_C[1] + (z - H.RING_C[1]) * r / max(d, 1e-6)
        out.append((x, z))
    if inside == len(pts):
        return None
    # drop collinear/duplicate points (keep arc points)
    clean = []
    for p in out:
        if not clean or math.hypot(p[0] - clean[-1][0], p[1] - clean[-1][1]) > 0.012:
            clean.append(p)
    if len(clean) > 2 and math.hypot(clean[0][0] - clean[-1][0], clean[0][1] - clean[-1][1]) < 0.012:
        clean.pop()
    # simplify straight runs
    simp = []
    for i, p in enumerate(clean):
        a, b = clean[i - 1], clean[(i + 1) % len(clean)]
        cross = (p[0] - a[0]) * (b[1] - p[1]) - (p[1] - a[1]) * (b[0] - p[0])
        if abs(cross) > 1e-5:
            simp.append(p)
    return simp if len(simp) >= 3 else None


def poly_area(poly):
    return abs(sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))) / 2


def strip_stones(part, outer, closed, width, y0, y1, seg=(0.55, 0.85), joint=0.008, mat="VH_PodiumSlab", key="strip",
                 bev=(0.006, 0.012), inward=1):
    """Stones along a CCW polyline (the strip lies on its left, i.e. inside the polygon, when inward = 1),
    cut every seg metres with joints; corners handled by mitred offsets."""
    P = [Vector((x, 0, z)) for x, z in outer]
    n = len(P)
    m = n if closed else n - 1

    def left(i):
        a, b = P[i % n], P[(i + 1) % n]
        d = (b - a).normalized()
        return Vector((-d.z, 0, d.x)) * inward

    inner = []
    for i in range(n):
        if not closed and i == 0:
            nn = left(0)
            inner.append(P[0] + nn * width)
        elif not closed and i == n - 1:
            nn = left(n - 2)
            inner.append(P[i] + nn * width)
        else:
            n1, n2 = left(i - 1), left(i)
            bis = (n1 + n2)
            cosh = max(0.3, bis.length / 2)
            inner.append(P[i] + bis.normalized() * (width / cosh))
    # cumulative length along the outer polyline
    cum = [0.0]
    for i in range(m):
        cum.append(cum[-1] + (P[(i + 1) % n] - P[i]).length)
    total = cum[-1]
    rr = drng(key, "cuts")
    cuts = [0.0]
    while cuts[-1] < total - 1e-4:
        ln = rr.uniform(*seg)
        if total - (cuts[-1] + ln) < seg[0] * 0.55:
            ln = total - cuts[-1]
        cuts.append(min(total, cuts[-1] + ln))

    def at(s, which):
        s = max(0.0, min(total, s))
        for i in range(m):
            if s <= cum[i + 1] + 1e-9:
                t = (s - cum[i]) / max(cum[i + 1] - cum[i], 1e-9)
                A = (P if which == 0 else inner)[i]
                B = (P if which == 0 else inner)[(i + 1) % n]
                return A + (B - A) * t, i
        return (P if which == 0 else inner)[(m) % n], m - 1

    stones = []
    for k in range(len(cuts) - 1):
        s0, s1 = cuts[k] + joint / 2, cuts[k + 1] - joint / 2
        if s1 - s0 < 0.05:
            continue
        o0, i0 = at(s0, 0)
        o1, i1 = at(s1, 0)
        n0, _ = at(s0, 1)
        n1, _ = at(s1, 1)
        outer_pts = [o0] + [P[(i + 1) % n] for i in range(i0, i1)] + [o1]
        inner_pts = [n0] + [inner[(i + 1) % n] for i in range(i0, i1)] + [n1]
        poly = [(p.x, p.z) for p in outer_pts + inner_pts[::-1]]
        # joints across a corner: pull the inner points along with the outer cut (approximate)
        if poly_area(poly) < 0.004:
            continue
        stones.append(flag(part, poly, y1, mat, thick=y1 - y0, bev=bev, key=(key, k)))
    return stones


def arc_solid(part, rc, a0, a1, profile, mat, bid, seg_len=0.1, lift=None):
    """Closed solid: a (o, y) profile (o = radial offset from rc) swept along the arc a0..a1 (degrees, CCW)."""
    L = math.radians(a1 - a0) * rc
    k = max(2, int(math.ceil(L / seg_len)))
    rings = []
    for i in range(k + 1):
        t = i / k
        a = math.radians(a0 + (a1 - a0) * t)
        ca, sa = math.cos(a), math.sin(a)
        dy = lift(t) if lift else 0.0
        rings.append([Vector((H.RING_C[0] + (rc + o) * ca, y + (dy(o) if callable(dy) else dy), H.RING_C[1] + (rc + o) * sa))
                      for o, y in profile])
    verts = [p for ring in rings for p in ring]
    m = len(profile)
    faces = []
    for i in range(k):
        for j in range(m):
            jj = (j + 1) % m
            faces.append([i * m + j, i * m + jj, (i + 1) * m + jj, (i + 1) * m + j])
    faces.append(list(range(m))[::-1])
    faces.append([k * m + j for j in range(m)])
    vs, fs = part.closed_solid(verts, faces, mat, bid)
    return vs, fs


def bevel_sharp(part, fs, bev, split=0.14):
    edges = {e for f in fs for e in f.edges}
    sharp = [e for e in edges if e.is_valid and len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(40)]
    if WM.S.LOD == 0:
        pieces = []
        for e in sharp:
            if e.calc_length() > split * 1.5:
                pieces += split_edge(e, int(e.calc_length() / split))
            else:
                pieces.append(e)
        sharp = [e for e in pieces if e.is_valid]
    part.bevel_edges(sharp, bev, 2)


def bend(part, v0, f0, R, inner):
    """Wrap geometry authored on a straight frame (u along x, face normal +z) round the ring."""
    bm = part.bm
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    for i in range(v0, len(bm.verts)):
        v = bm.verts[i]
        x, y, z = v.co
        th, r = ((-x / R), R - z) if inner else ((x / R), R + z)
        v.co = Vector((H.RING_C[0] + r * math.cos(th), y, H.RING_C[1] + r * math.sin(th)))
    bmesh.ops.reverse_faces(bm, faces=[bm.faces[i] for i in range(f0, len(bm.faces))])


def root_mesh(name, paths, coll, lod):
    """Surface roots: tapered tubes with real tube UVs (metres), RootBark material."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    col = bm.loops.layers.color.new("Col")
    sides = 9 if lod == 0 else 5
    for pts, r0, r1 in paths:
        P = [Vector(p) for p in pts]
        # resample by arc length
        cum = [0.0]
        for a, b in zip(P, P[1:]):
            cum.append(cum[-1] + (b - a).length)
        total = cum[-1]
        step = 0.06 if lod == 0 else 0.16
        ns = max(2, int(total / step))
        rings = []
        for s in range(ns + 1):
            d = total * s / ns
            i = min(len(P) - 2, max(0, next(k for k in range(len(cum) - 1) if d <= cum[k + 1] + 1e-9)))
            t = (d - cum[i]) / max(cum[i + 1] - cum[i], 1e-9)
            c = P[i] + (P[i + 1] - P[i]) * t
            tan = (P[i + 1] - P[i]).normalized()
            ref = Vector((0, 1, 0)) if abs(tan.y) < 0.9 else Vector((1, 0, 0))
            s1 = tan.cross(ref).normalized()
            s2 = tan.cross(s1).normalized()
            rad = lerp(r0, r1, (s / ns) ** 0.8) * (1 + 0.1 * math.sin(d * 7.3 + r0 * 40) + 0.06 * math.sin(d * 23.0 + r0 * 90))
            flat = 0.62    # roots at the surface are flattened oval sections
            ring = []
            for j in range(sides + 1):
                a = 2 * math.pi * j / sides
                off = s1 * math.cos(a) * rad + s2 * math.sin(a) * rad * flat
                ring.append((bm.verts.new(c + off) if j < sides else None, (j / sides * 2 * math.pi * rad / 0.9, d / 0.9)))
            ring[sides] = (ring[0][0], ring[sides][1])
            rings.append(ring)
        for s in range(ns):
            for j in range(sides):
                a, b = rings[s][j], rings[s][j + 1]
                c, e = rings[s + 1][j + 1], rings[s + 1][j]
                f = bm.faces.new([a[0], b[0], c[0], e[0]])
                for loop, (_, u) in zip(f.loops, (a, b, c, e)):
                    loop[uv].uv = u
                    loop[col] = (0.5, 0.5, 0.5, 1.0)
        # tip cap
        last = rings[-1]
        cap = bm.faces.new([last[j][0] for j in range(sides)][::-1])
        for loop in cap.loops:
            loop[uv].uv = (0, 0)
            loop[col] = (0.5, 0.5, 0.5, 1.0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for v in bm.verts:
        v.co = U(v.co)
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(material("RootBark"))
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True
    triangulate(ob)
    return ob


# ====================================================================== the build
def build(lod):
    L = random.Random(20260930)
    WM.set_state(lod, L, "ward_hill")
    WM.WEAR["ground_y"] = 0.0
    WM.TINT[:] = [1.0, 1.0, 1.0]
    WM.reset_materials()
    coll = bpy.data.collections.new(f"WardHill_LOD{lod}")
    bpy.context.scene.collection.children.link(coll)
    p = lambda s, wear=True: Part(f"WH_{s}_LOD{lod}", wear=wear)
    walls, stairs, ring, pave = p("Walls"), p("Stairs"), p("Ring"), p("Paving")
    metal, sand = p("Metal", False), p("Sand", False)
    bed, litter = p("BedSoil", False), p("RingSoil", False)
    drips = HillDrips()
    scars = ScarSet(base=0.12)
    srng = random.Random(1918)
    rec = {"colliders": [], "mounts": [], "lights": [], "notes": [], "beds": [], "exclusions": H.exclusions()}
    faces_for_scars = []

    # ------------------------------------------------------------------ retaining walls + quoins
    Ep = H.E - H.BLOCK                          # frame plane (block faces at E)
    cs = H.WALL_COURSES
    for si, (name, n, has_stair) in enumerate(H.SIDES):
        N, Lx = side_axes(n)
        F = Frame(N * Ep, Lx, N)
        ua, ub = -Ep, Ep
        segs = [(ua, -H.CHEEK_OUT), (H.CHEEK_OUT, ub)] if has_stair else [(ua, ub)]
        for ci, (y0, y1) in enumerate(zip(cs, cs[1:])):
            owned = (ci % 2 == 1) if si in (2, 3) else (ci % 2 == 0)
            rough = ci == 0
            mat = "VH_AshlarRough" if rough else "VH_Ashlar"
            depth = 0.1 if rough else 0.062
            qdepth = 0.13 if rough else QD
            for (a, b) in segs:
                a2 = a + (QL if owned else QS) + J if a <= ua + 1e-6 else a + J
                b2 = b - (QL if owned else QS) - J if b >= ub - 1e-6 else b - J
                fill_wall(walls, F, a2, b2, [y0, y1], [], mat=mat, key=(name, "w", round(a, 2)), course_offset=ci,
                          lmin=0.55, lmax=1.2, depth=depth)
                if a <= ua + 1e-6:
                    F.box(walls, ua - QD, a2, y0, y1, 0.02, MORTAR_FRONT, "VH_Mortar", skip=("s0", "bottom", "top", "s1", "s3"))
                    if owned:
                        ashlar_block(walls, F, ua - qdepth + J / 2, ua + QL - J / 2, y0 + J / 2, y1 - J / 2, mat=mat, depth=qdepth,
                                     back=-QS, key=(name, "q", ci, "a"), chip=0.25, bevel=(0.014, 0.026))
                if b >= ub - 1e-6:
                    F.box(walls, b2, ub + QD, y0, y1, 0.02, MORTAR_FRONT, "VH_Mortar", skip=("s0", "bottom", "top", "s1", "s3"))
                    if owned:
                        ashlar_block(walls, F, ub - QL + J / 2, ub + qdepth - J / 2, y0 + J / 2, y1 - J / 2, mat=mat, depth=qdepth,
                                     back=-QS, key=(name, "q", ci, "b"), chip=0.25, bevel=(0.014, 0.026))
            # runoff under the coping along the whole face
        a = F.P(-H.E, 0, 0.062)
        b = F.P(H.E, 0, 0.062)
        if abs(N.z) > 0.5:
            drips.axis.add((0, 0, N.z), a.z, a.x, b.x, H.COPE_BOT, 0.7, 0.42, soft=0.25)
        else:
            drips.axis.add((N.x, 0, 0), a.x, a.z, b.z, H.COPE_BOT, 0.7, 0.42, soft=0.25)
        for (a_, b_) in segs:
            faces_for_scars.append((F, a_, b_))

    # coping round the plinth (open runs from stair cheek to stair cheek, mitred at the corners)
    prof = [(-H.COPE_IN, H.COPE_BOT), (H.COPE_OUT, H.COPE_BOT), (H.COPE_OUT, H.COPE_TOP - 0.05), (H.COPE_OUT - 0.022, H.COPE_TOP - 0.008),
            (H.COPE_OUT - 0.05, H.COPE_TOP), (-H.COPE_IN, H.COPE_TOP)]
    c = H.CHEEK_OUT
    runs = [[(c, -H.E), (H.E, -H.E), (H.E, -c)],            # north-west(+x) corner: north cheek -> west (+x) side
            [(H.E, c), (H.E, H.E), (c, H.E)],               # +x side -> south
            [(-c, H.E), (-H.E, H.E), (-H.E, -H.E), (-c, -H.E)]]   # south -> the stairless -x side -> north
    for ri, run in enumerate(runs):
        # sweep's outward side is (-d.z, d.x); make sure it points away from the hill centre
        a, b = Vector((run[0][0], 0, run[0][1])), Vector((run[1][0], 0, run[1][1]))
        d = (b - a).normalized()
        outward = Vector((-d.z, 0, d.x))
        mid = (a + b) / 2
        if outward.dot(mid) < 0:
            run = run[::-1]
        sweep(walls, run, False, prof, "VH_Ashlar", seg=1.05, joint=0.009, bev=0.007, key=("cope", ri))

    # ------------------------------------------------------------------ stairs: cheeks, capstones, step stones
    def y_top(w):
        if w <= H.RUN:
            return H.HT + H.CHEEK_ABOVE
        return H.HT - (w - H.RUN) * (H.RISE / H.RUN) + H.CHEEK_ABOVE

    def y_bot(w):
        return y_top(w) - H.CHEEK_COPE

    def tread(w):
        """Tread top at outward distance w (0 = plinth face)."""
        if w < 0:
            return H.HT
        k = min(H.NSTEP - 1, int((H.STAIR_LEN - w) / H.RUN))
        return H.RISE * (k + 1)

    for si, (name, n, has_stair) in enumerate(H.SIDES):
        if not has_stair:
            continue
        N, Lx = side_axes(n)
        base = N * H.E

        def W(u, w, y):
            return base + Lx * u + N * w + Vector((0, y, 0))

        for sgn in (-1, 1):
            # ---- outer face (away from the stair) and inner face (towards it)
            for which in ("outer", "inner"):
                if which == "outer":
                    Nc = Lx * sgn
                    origin = base + Lx * sgn * (H.CHEEK_OUT - H.BLOCK)
                else:
                    Nc = -Lx * sgn
                    origin = base + Lx * sgn * (H.STAIR_HW + H.BLOCK)
                uax = Vector((Nc.z, 0, -Nc.x))
                Fc = Frame(origin, uax, Nc)
                sgn_w = 1 if uax.dot(N) > 0 else -1          # frame u = sgn_w * w
                w0, w1 = (0.0 if which == "outer" else 0.0), H.STAIR_LEN
                ua_, ub_ = sorted((sgn_w * w0, sgn_w * w1))
                bm = walls.bm
                v0 = len(bm.verts)
                ccs = cs + [H.HT + 0.02]      # the head section (w < 0.6) rises one more short course
                for ci, (y0, y1) in enumerate(zip(ccs, ccs[1:])):
                    # w-range where this course is below the rake bottom (at its bottom) and above the treads (inner)
                    wmax = H.STAIR_LEN
                    while wmax > 0 and y_bot(wmax) < y0 + 0.08:
                        wmax -= 0.02
                    wmin = 0.0
                    if which == "inner":
                        while wmin < wmax and tread(wmin + 0.001) >= y1 - 0.001:
                            wmin += 0.02
                        wmin = max(0.0, wmin - 0.02)
                    if wmax - wmin < 0.12:
                        continue
                    a_, b_ = sorted((sgn_w * wmin, sgn_w * wmax))
                    rough = ci == 0
                    fill_wall(walls, Fc, a_, b_, [y0, y1], [], mat="VH_AshlarRough" if rough else "VH_Ashlar",
                              key=(name, sgn, which, ci), course_offset=ci, lmin=0.5, lmax=1.05, depth=0.1 if rough else 0.062)
                # clamp everything above the rake onto it (raking-cut blocks), below the coping
                bm.verts.ensure_lookup_table()
                for i in range(v0, len(bm.verts)):
                    v = bm.verts[i]
                    w = (v.co - base).dot(N)
                    lim = y_bot(max(0.0, w)) - 0.004
                    if v.co.y > lim:
                        v.co.y = lim
                if which == "outer":
                    faces_for_scars.append((Fc, ua_, ub_))
            # ---- end face at the plaza (w = STAIR_LEN)
            Fe = Frame(base + N * (H.STAIR_LEN - H.BLOCK) + Lx * sgn * (H.STAIR_HW + H.CHEEK / 2), Lx, N)
            v0 = len(walls.bm.verts)
            fill_wall(walls, Fe, -H.CHEEK / 2 - 0.02, H.CHEEK / 2 + 0.02, [cs[0], cs[1]], [], mat="VH_AshlarRough",
                      key=(name, sgn, "end"), lmin=0.5, lmax=0.6, depth=0.1)
            walls.bm.verts.ensure_lookup_table()
            for i in range(v0, len(walls.bm.verts)):
                v = walls.bm.verts[i]
                v.co.y = min(v.co.y, y_bot(H.STAIR_LEN) - 0.004)
            # ---- core fill (hidden) so the rake has something under the coping between the two faces
            u0, u1 = sgn * H.STAIR_HW, sgn * H.CHEEK_OUT
            # ---- raking coping stones and the head capstone
            cu0, cu1 = sorted((u0 - sgn * 0.04, u1 + sgn * 0.045))
            wcuts = [H.CHEEK_HEAD, H.RUN]
            wq = H.RUN
            rr = drng(name, sgn, "cope")
            while wq < H.STAIR_LEN - 1e-3:
                ln = rr.uniform(0.85, 1.15)
                if H.STAIR_LEN - (wq + ln) < 0.45:
                    ln = H.STAIR_LEN - wq
                wq = min(H.STAIR_LEN + 0.03, wq + ln)
                wcuts.append(wq)
            wcuts[-1] = H.STAIR_LEN + 0.035
            for k in range(len(wcuts) - 1):
                wa, wb = wcuts[k] + (J / 2 if k else 0), wcuts[k + 1] - J / 2
                bid = walls.new_block(tint=stone_tint(), erode=0.006)
                if k == 0:
                    # head capstone: sits on the hilltop band behind the plinth face and on the courses in front of it
                    ya = H.HT - 0.05
                    corners = [W(cu0, wa, ya), W(cu1, wa, ya), W(cu1, wb, ya), W(cu0, wb, ya),
                               W(cu0, wa, y_top(0) + 0.02), W(cu1, wa, y_top(0) + 0.02), W(cu1, wb, y_top(0) + 0.02), W(cu0, wb, y_top(0) + 0.02)]
                else:
                    ya, yb = y_bot(wa), y_bot(wb)
                    corners = [W(cu0, wa, ya), W(cu1, wa, ya), W(cu1, wb, yb), W(cu0, wb, yb),
                               W(cu0, wa, y_top(wa)), W(cu1, wa, y_top(wa)), W(cu1, wb, y_top(wb)), W(cu0, wb, y_top(wb))]
                vs, made = walls.hexa(corners, "VH_Ashlar", bid)
                eroded_bevel(walls, [e for f in (made.get("top"),) if f for e in f.edges], rr.uniform(0.01, 0.018), 2, seg_len=0.15)
                if k == 0 and lod == 0:
                    pass
            # drips down the cheek faces under the coping (approximate: a band at mid height)
            # ---- cheek colliders (per tread segment + head)
            cc = (u0 + u1) / 2
            rec["colliders"].append({"name": f"COL_{name}_cheek_{'L' if sgn < 0 else 'R'}_head",
                                     "center": list(W(cc, (H.CHEEK_HEAD + H.RUN) / 2, 0)) , "size": None, "_w": [H.CHEEK_HEAD, H.RUN], "_u": [u0, u1], "_top": y_top(0) + 0.02, "_side": name})
            for k in range(H.NSTEP - 1):
                wa, wb = H.RUN * (k + 1), H.RUN * (k + 2)
                rec["colliders"].append({"name": f"COL_{name}_cheek_{'L' if sgn < 0 else 'R'}_{k}", "_w": [wa, wb], "_u": [u0, u1],
                                         "_top": y_top(wa), "_side": name})

        # ---- step stones (exactly on the saved colliders), worn and dished nosings
        for k in range(H.NSTEP):
            wf = H.STAIR_LEN - H.RUN * k           # front (nosing) of step k
            wb = wf - H.RUN - 0.06                 # runs 6 cm under the next step up
            y1 = H.RISE * (k + 1)
            y0 = y1 - H.RISE - 0.06
            rr = drng(name, "step", k)
            cuts = [-H.STAIR_HW]
            while cuts[-1] < H.STAIR_HW - 1e-3:
                ln = rr.uniform(1.15, 1.75)
                if H.STAIR_HW - (cuts[-1] + ln) < 0.6:
                    ln = H.STAIR_HW - cuts[-1]
                cuts.append(min(H.STAIR_HW, cuts[-1] + ln))
            for ci in range(len(cuts) - 1):
                ua2, ub2 = cuts[ci] + (J / 2 if ci else 0), cuts[ci + 1] - (J / 2 if ci < len(cuts) - 2 else 0)
                bid = stairs.new_block(tint=stone_tint("rough"), erode=0.009)
                corners = [W(ua2, wb, y0), W(ub2, wb, y0), W(ub2, wf + 0.025, y0), W(ua2, wf + 0.025, y0),
                           W(ua2, wb, y1), W(ub2, wb, y1), W(ub2, wf + 0.025, y1), W(ua2, wf + 0.025, y1)]
                vs, made = stairs.hexa(corners, "VH_PodiumSlab", bid)
                top = made["top"]
                if lod == 0:
                    # grid the tread so it can be dished where feet land (centre of the flight, near the nosing)
                    res = bmesh.ops.subdivide_edges(stairs.bm, edges=list(top.edges), cuts=7, use_grid_fill=True)
                    for v in [v for v in res["geom_inner"] if isinstance(v, bmesh.types.BMVert)] + \
                             [v for v in res["geom_split"] if isinstance(v, bmesh.types.BMVert)]:
                        if abs(v.co.y - y1) > 1e-4:
                            continue
                        uu = (v.co - base).dot(Lx)
                        ww = (v.co - base).dot(N)
                        near = max(0.0, 1 - (wf - ww) / H.RUN)
                        v.co.y -= 0.013 * math.exp(-(uu / 1.05) ** 2) * near ** 0.7 * (0.8 + 0.4 * rr.random())
                nose = [e for e in stairs.bm.edges if e.is_valid and all(abs((v.co - base).dot(N) - (wf + 0.025)) < 1e-3 and v.co.y > y1 - 0.02 for v in e.verts)]
                eroded_bevel(stairs, nose, rr.uniform(0.02, 0.03), 2, seg_len=0.12)
                ends = [e for e in made["s2"].edges] if made.get("s2") and made["s2"].is_valid else []
                stairs.bevel_edges([e for e in ends if e.is_valid and e not in nose], 0.008, 1)

    # ------------------------------------------------------------------ the tree ring
    WM.WEAR["ground_y"] = H.HT
    Ro_base = H.RO - H.BLOCK
    C = 2 * math.pi * Ro_base
    Fs = Frame((0, 0, 0), (1, 0, 0), (0, 0, 1))
    v0, f0 = len(ring.bm.verts), len(ring.bm.faces)
    fill_wall(ring, Fs, 0.0, C, [H.RING_BOT, H.RING_TOP], [], mat="VH_Ashlar", key="ringO", lmin=0.52, lmax=0.8, mortar=False)
    u = 0.0
    while u < C - 1e-4:
        Fs.box(ring, u, min(C, u + 0.2), H.RING_BOT, H.RING_TOP, 0.02, MORTAR_FRONT, "VH_Mortar", skip=("s0", "bottom", "top", "s1", "s3"))
        u += 0.2
    bend(ring, v0, f0, Ro_base, inner=False)
    Ri_base = H.RI + H.BLOCK
    Ci = 2 * math.pi * Ri_base
    v0, f0 = len(ring.bm.verts), len(ring.bm.faces)
    fill_wall(ring, Fs, 0.0, Ci, [H.SOIL_EDGE - 0.12, H.RING_TOP], [], mat="VH_Ashlar", key="ringI", lmin=0.5, lmax=0.72, mortar=False)
    u = 0.0
    while u < Ci - 1e-4:
        Fs.box(ring, u, min(Ci, u + 0.2), H.SOIL_EDGE - 0.12, H.RING_TOP, 0.02, MORTAR_FRONT, "VH_Mortar", skip=("s0", "bottom", "top", "s1", "s3"))
        u += 0.2
    bend(ring, v0, f0, Ri_base, inner=True)
    # coping: curved stones, one lifted by a root and cracked, iron cramps over the crack and joint
    rc = (H.RO + H.RI) / 2
    hw = (H.RO - H.RI) / 2 + H.RING_CAP_OVER
    y0c, y1c = H.RING_CAP
    cprof = [(-hw, y0c), (hw, y0c), (hw, y1c - 0.035), (hw - 0.02, y1c - 0.008), (hw - 0.05, y1c), (0.0, y1c + 0.004),
             (-hw + 0.05, y1c), (-hw + 0.02, y1c - 0.008), (-hw, y1c - 0.035)]
    cprof = cprof[::-1]
    rr = drng("ringcap")
    a = 7.0
    caps = []
    while a < 367.0 - 1e-3:
        span = math.degrees(rr.uniform(0.95, 1.25) / rc)
        if 367.0 - (a + span) < math.degrees(0.6 / rc):
            span = 367.0 - a
        caps.append((a, a + span))
        a += span
    jd = math.degrees(J / rc)
    heave = min(range(len(caps)), key=lambda i: abs(((caps[i][0] + caps[i][1]) / 2 - H.HEAVE_ANGLE + 180) % 360 - 180))
    for i, (a0, a1) in enumerate(caps):
        bid = ring.new_block(tint=stone_tint(), erode=0.008)
        if i == heave:
            # the root lifts the inner edge towards the stone's far end; the stone cracked a third of the way along
            crack = a0 + (a1 - a0) * 0.38
            for (b0, b1, lift0, lift1) in ((a0 + jd / 2, crack - 0.12, 0.0, 0.012), (crack + 0.12, a1 - jd / 2, 0.016, 0.034)):
                def lift(t, l0=lift0, l1=lift1):
                    base_ = lerp(l0, l1, t)
                    return lambda o, b=base_: b * (0.55 + 0.45 * (-o / hw))     # more on the inner (root) side
                bid = ring.new_block(tint=stone_tint(), erode=0.01)
                vs, fs = arc_solid(ring, rc, b0, b1, cprof, "VH_Ashlar", bid, lift=lift)
                bevel_sharp(ring, fs, 0.009)
            for ca in (crack, a1):
                rad = math.radians(ca)
                cx, cz = H.RING_C[0] + rc * math.cos(rad), H.RING_C[1] + rc * math.sin(rad)
                tx, tz = -math.sin(rad), math.cos(rad)
                ytop = y1c + (0.024 if ca == crack else 0.036)
                for off in (-0.07, 0.07):
                    ox, oz = cx + math.cos(rad) * off, cz + math.sin(rad) * off
                    # dog cramp: an iron bar over the joint, its turned-down ends leaded into both stones
                    obox(metal, (ox, oz), (tx, tz), 0.09, 0.011, ytop - 0.006, ytop + 0.011, "VH_Steel")
                    for e_ in (-0.082, 0.082):
                        obox(metal, (ox + tx * e_, oz + tz * e_), (tx, tz), 0.011, 0.014, ytop - 0.012, ytop - 0.004, "VH_Dark")
                drips.ring.append((ca % 360, 3.5, "rust", 0.85))
            rec["notes"].append(f"heaved coping stone at {round((a0 + a1) / 2 % 360, 1)} deg, cracked at {round(crack % 360, 1)} deg, 4 iron cramps")
            continue
        vs, fs = arc_solid(ring, rc, a0 + jd / 2, a1 - jd / 2, cprof, "VH_Ashlar", bid)
        bevel_sharp(ring, fs, 0.008)
    # ring colliders and specs (built in Unity as mesh colliders)
    rec["ring"] = {"centre": list(H.RING_C), "outer": H.RO + H.RING_CAP_OVER, "inner": H.RI - H.RING_CAP_OVER, "bottom": H.HT - 0.1,
                   "top": H.RING_CAP[1], "soil_top": (H.SOIL_EDGE + H.SOIL_MID) / 2}
    # old damage on the ring (the side facing the West Gate took the worst of it)
    scars.impact((H.RO * math.cos(math.radians(-20)), 1.7, H.RO * math.sin(math.radians(-20))), 0.7, 0.85)
    scars.impact((H.RO * math.cos(math.radians(200)), 1.75, H.RO * math.sin(math.radians(200))), 0.5, 0.7)

    # uplights in the coping (bronze housings with a lens; the lens material is on the city light clock)
    for ua_ in H.UPLIGHT_ANGLES:
        rad = math.radians(ua_)
        cx, cz = H.RING_C[0] + (rc + 0.06) * math.cos(rad), H.RING_C[1] + (rc + 0.06) * math.sin(rad)
        ytop = y1c + 0.004
        metal.cyl((cx, ytop - 0.02, cz), (cx, ytop + 0.018, cz), 0.075, "VH_Bronze", 20)
        metal.cyl((cx, ytop + 0.018, cz), (cx, ytop + 0.024, cz), 0.058, "VH_LampLens", 20)
        for k in range(4):
            aa = rad + math.pi / 4 + k * math.pi / 2
            metal.cyl((cx + 0.066 * math.cos(aa), ytop + 0.018, cz + 0.066 * math.sin(aa)),
                      (cx + 0.066 * math.cos(aa), ytop + 0.024, cz + 0.066 * math.sin(aa)), 0.006, "VH_Steel", 6)
        # aim up into the crown, leaning slightly towards the trunk
        tgt = (cx * 0.35, 8.5, cz * 0.35)
        rec["lights"].append({"name": f"Tree uplight {int(ua_)}", "type": "Spot", "pos": [cx, ytop + 0.05, cz], "target": list(tgt),
                              "intensity": 60.0, "range": 16.0, "angle": 56.0, "inner": 24.0, "color": [1.0, 0.87, 0.7]})   # crown 6-9 m away

    # irrigation standpipe from the aquifer line (inside the ring, by the wall) with a valve wheel
    rad = math.radians(203.0)
    px, pz = (H.RI - 0.28) * math.cos(rad), (H.RI - 0.28) * math.sin(rad)
    ys = H.ring_soil_y(px, pz)
    metal.cyl((px, ys - 0.1, pz), (px, ys + 0.42, pz), 0.028, "VH_Steel", 12)
    metal.cyl((px, ys + 0.42, pz), (px + 0.14 * math.cos(rad + 1.2), ys + 0.42, pz + 0.14 * math.sin(rad + 1.2)), 0.022, "VH_Steel", 10)
    metal.cyl((px, ys + 0.30, pz), (px, ys + 0.36, pz), 0.045, "VH_Bronze", 14)
    for k in range(6):
        aa = k * math.pi / 3
        metal.cyl((px, ys + 0.47, pz), (px + 0.075 * math.cos(aa), ys + 0.47, pz + 0.075 * math.sin(aa)), 0.007, "VH_Bronze", 6)
    metal.cyl((px, ys + 0.462, pz), (px, ys + 0.478, pz), 0.08, "VH_Bronze", 18)
    metal.cyl((px, ys + 0.462, pz), (px, ys + 0.478, pz), 0.066, "VH_Bronze", 18)

    # ------------------------------------------------------------------ hilltop paving
    WM.WEAR["ground_y"] = H.HT
    # apron: one ring of curved flags between the ring foot and APRON
    n_ap = int(round(2 * math.pi * H.APRON / 0.78))
    for k in range(n_ap):
        a0 = 360.0 * k / n_ap + 2.0
        a1 = 360.0 * (k + 1) / n_ap + 2.0
        jd2 = math.degrees(0.004 / H.APRON)
        outer = circle_pts(H.APRON, a0 + jd2, a1 - jd2, 0.12)
        inner = circle_pts(H.RO + 0.004, a0 + jd2 * 1.2, a1 - jd2 * 1.2, 0.12)[::-1]
        flag(pave, outer + inner, H.HT, key=("apron", k))
    # paths and landings, flagged in running bond; flags clipped to the apron circle
    for si, (name, n, has_stair) in enumerate(H.SIDES):
        if not has_stair:
            continue
        N, Lx = side_axes(n)
        rr = drng("path", name)

        def XZ(a_, b_):
            v = Lx * a_ + N * b_
            return (v.x, v.z)
        rows = []
        b = H.APRON - 0.4
        while b < H.BAND - H.LANDING_D - 1e-3:
            d = rr.uniform(0.62, 0.78)
            if H.BAND - H.LANDING_D - (b + d) < 0.35:
                d = H.BAND - H.LANDING_D - b
            rows.append((b, b + d, H.PATH_HW))
            b += d
        b = H.BAND - H.LANDING_D
        while b < H.E - 1e-3:
            d = min(rr.uniform(0.62, 0.72), H.E - b)
            if H.E - (b + d) < 0.3:
                d = H.E - b
            rows.append((b, b + d, H.STAIR_HW))
            b += d
        for ri, (b0, b1, hw_) in enumerate(rows):
            a_ = -hw_
            first = True
            while a_ < hw_ - 1e-3:
                ln = rr.uniform(0.7, 1.15)
                if first and ri % 2:
                    ln *= 0.55
                first = False
                if hw_ - (a_ + ln) < 0.35:
                    ln = hw_ - a_
                poly = [XZ(a_ + 0.004, b0 + 0.004), XZ(a_ + ln - 0.004, b0 + 0.004), XZ(a_ + ln - 0.004, b1 - 0.004), XZ(a_ + 0.004, b1 - 0.004)]
                poly = clip_outside_circle(poly, H.APRON + 0.004)
                if poly and poly_area(poly) > 0.02:
                    flag(pave, poly, H.HT, key=("path", name, ri, round(a_, 2)))
                a_ += ln

    # kerbs round the planted beds (the kerb strip lies inside each bed polygon)
    def bed_polys():
        beds = []
        hw, lw, lb, band, ap = H.PATH_HW, H.STAIR_HW, H.BAND - H.LANDING_D, H.BAND, H.APRON
        zc = math.sqrt(ap * ap - hw * hw)
        a_lo, a_hi = math.degrees(math.asin(hw / ap)), 90 - math.degrees(math.asin(hw / ap))
        # +X/+Z quadrant (CCW, x right z up)
        q = [(zc, hw), (lb, hw), (lb, lw), (band, lw), (band, band), (lw, band), (lw, lb), (hw, lb), (hw, zc)]
        q += circle_pts(ap, a_lo, a_hi, 0.3)[::-1][1:-1]
        beds.append(("bed_southwest", q))
        # +X/-Z quadrant: mirror z (and reverse to keep CCW)
        beds.append(("bed_northwest", [(x, -z) for x, z in q][::-1]))
        # -X half (one C-shaped bed round the stairless side)
        w = [(-hw, -zc), (-hw, -lb), (-lw, -lb), (-lw, -band), (-band, -band), (-band, band), (-lw, band), (-lw, lb), (-hw, lb), (-hw, zc)]
        w += circle_pts(ap, 90 + math.degrees(math.asin(hw / ap)), 270 - math.degrees(math.asin(hw / ap)), 0.3)[1:-1]
        beds.append(("bed_east", w))
        return beds
    for bname, poly in bed_polys():
        poly = poly_ccw(poly)
        rec["beds"].append({"name": bname, "polygon": [[round(x, 4), round(z, 4)] for x, z in poly]})
        strip_stones(pave, poly, True, H.KERB, H.HT - 0.12, H.KERB_TOP, seg=(0.5, 0.8), key=("kerb", bname), bev=(0.006, 0.01))

    # terminal pads and stepping stones, a stone under Linn
    for tname, tp in H.TERMINALS:
        flag(pave, H.pad_corners(tp), H.PAD_TOP, thick=0.2, bev=(0.012, 0.02), key=("pad", tname))
        yaw = H.face_yaw_to_tree(tp)
        rec["mounts"].append({"name": tname, "prefab": "WardSaveTerminal", "pos": [tp[0], H.PAD_TOP, tp[1]], "yaw": yaw})
        for k, sp in enumerate(H.stepping_stones(tp)):
            rr = drng("stone", tname, k)
            rad_ = rr.uniform(0.22, 0.27)
            pts = []
            for j in range(9):
                aa = 2 * math.pi * j / 9 + rr.uniform(-0.15, 0.15)
                rj = rad_ * rr.uniform(0.82, 1.1)
                pts.append((sp[0] + rj * math.cos(aa), sp[1] + rj * 0.82 * math.sin(aa)))
            flag(pave, pts, H.HT + 0.015, thick=0.12, bev=(0.012, 0.02), key=("step", tname, k))
    rr = drng("linn")
    pts = [(H.LINN[0] + 0.46 * rr.uniform(0.85, 1.08) * math.cos(2 * math.pi * j / 11), H.LINN[1] + 0.4 * rr.uniform(0.85, 1.08) * math.sin(2 * math.pi * j / 11)) for j in range(11)]
    flag(pave, pts, H.HT + 0.012, thick=0.12, bev=(0.012, 0.02), key="linn")

    # ------------------------------------------------------------------ soil
    step = 0.16 if lod == 0 else 0.4
    bmb = bed.bm
    mi_bed = bed.mi("WH_BedSoil")
    for bname, poly in bed_polys():
        xs = [x for x, _ in poly]
        zs = [z for _, z in poly]
        gx = int((max(xs) - min(xs)) / step) + 2
        gz = int((max(zs) - min(zs)) / step) + 2
        vmap = {}

        def vert(i, j):
            if (i, j) not in vmap:
                x, z = min(xs) + i * step, min(zs) + j * step
                vmap[(i, j)] = bmb.verts.new(Vector((x, H.bed_y(x, z), z)))
            return vmap[(i, j)]
        for i in range(gx):
            for j in range(gz):
                x, z = min(xs) + (i + 0.5) * step, min(zs) + (j + 0.5) * step
                if H.in_bed(x, z, H.KERB - 0.05 - step * 0.75):
                    f = bmb.faces.new([vert(i, j), vert(i + 1, j), vert(i + 1, j + 1), vert(i, j + 1)])
                    f.material_index = mi_bed
    bmesh.ops.recalc_face_normals(bmb, faces=bmb.faces[:])
    for f in bmb.faces:
        f.normal_update()
        if f.normal.y < 0:
            f.normal_flip()
    # ring litter: polar grid tucked under the inner wall
    bml = litter.bm
    mi_l = litter.mi("WH_RingLitter")
    nr = 16 if lod == 0 else 6
    na = 96 if lod == 0 else 36
    rows = []
    for i in range(nr + 1):
        r = 0.15 + (H.RI + 0.03 - 0.15) * i / nr
        row = []
        for j in range(na):
            a_ = 2 * math.pi * j / na
            x, z = H.RING_C[0] + r * math.cos(a_), H.RING_C[1] + r * math.sin(a_)
            row.append(bml.verts.new(Vector((x, H.ring_soil_y(x, z), z))))
        rows.append(row)
    for i in range(nr):
        for j in range(na):
            jj = (j + 1) % na
            f = bml.faces.new([rows[i][j], rows[i][jj], rows[i + 1][jj], rows[i + 1][j]])
            f.material_index = mi_l
    cap = bml.faces.new(rows[0])
    cap.material_index = mi_l
    for f in bml.faces:
        f.normal_update()
        if f.normal.y < 0:
            f.normal_flip()

    # ------------------------------------------------------------------ sheltered sand (LOD0)
    def drift(a, b, width, height, key, y=0.0, nrm=None, n_=12):
        rr = drng("drift", key)
        bm = sand.bm
        mi = sand.mi("VH_Sand")
        A, B = Vector(a), Vector(b)
        d = (B - A)
        nn = nrm or Vector((-d.z, 0, d.x)).normalized()
        rows_ = []
        for i in range(n_ + 1):
            t = i / n_
            env = math.sin(math.pi * t) ** 0.6
            hgt = height * env * rr.uniform(0.6, 1.2)
            wdt = width * env * rr.uniform(0.7, 1.2) + 0.02
            c_ = A + d * t
            rows_.append([bm.verts.new(c_ + Vector((0, y - 0.005, 0)) + nn * 0.005), bm.verts.new(c_ + Vector((0, y + hgt, 0)) + nn * (0.02 + wdt * 0.3)),
                          bm.verts.new(c_ + Vector((0, y - 0.005, 0)) + nn * (0.02 + wdt))])
        for i in range(n_):
            for k in range(2):
                f = bm.faces.new([rows_[i][k], rows_[i + 1][k], rows_[i + 1][k + 1], rows_[i][k + 1]])
                f.material_index = mi
    if lod == 0:
        for si, (name, n, has_stair) in enumerate(H.SIDES):
            N, Lx = side_axes(n)
            fp = N * (H.E + 0.1)
            spans = [(-H.E + 0.2, -H.CHEEK_OUT - 0.05), (H.CHEEK_OUT + 0.05, H.E - 0.2)] if has_stair else [(-H.E + 0.2, -1.2), (0.9, H.E - 0.2)]
            for k, (a_, b_) in enumerate(spans):
                # pockets against the wall, strongest in the internal corners by the stair cheeks
                A = fp + Lx * a_
                B = fp + Lx * b_
                drift(tuple(A), tuple(B), 0.34, 0.07, (name, k), nrm=N)
            if has_stair:
                for sgn in (-1, 1):
                    for kk in range(H.NSTEP):
                        wf = H.STAIR_LEN - H.RUN * kk
                        yk = H.RISE * (kk + 1)
                        A = N * H.E + Lx * sgn * (H.STAIR_HW - 0.01) + N * (wf - H.RUN + 0.05)
                        B = A + N * (H.RUN - 0.12)
                        drift(tuple(A), tuple(B), 0.16, 0.035, (name, sgn, kk), y=yk, nrm=-Lx * sgn, n_=6)

    # ------------------------------------------------------------------ roots from the trunk flare
    # (angle from the trunk centre, reach, base radius): long flat surface roots, knobbly, arching in and out of the
    # litter; the one at HEAVE_ANGLE runs to the wall and has lifted the coping above it
    root_specs = [(14, 2.2, 0.095), (76, 1.95, 0.085), (124, 2.35, 0.09), (H.HEAVE_ANGLE, 3.02, 0.115), (199, 2.05, 0.085),
                  (250, 2.35, 0.09), (303, 1.85, 0.08), (338, 1.6, 0.07)]
    paths = []
    for k, (deg, reach, r0) in enumerate(root_specs):
        rr = drng("root", k)
        a_ = math.radians(deg)
        pts = []
        start = 0.62
        s = start
        w1, w2 = rr.uniform(0, 6.28), rr.uniform(0, 6.28)
        heave = abs(deg - H.HEAVE_ANGLE) < 1e-6
        while s <= reach:
            t = (s - start) / (reach - start)
            aa = a_ + (0.13 * math.sin(s * 2.1 + w1) + 0.05 * math.sin(s * 6.3 + w2)) * min(1.0, t * 3)
            x = H.TRUNK_C[0] + s * math.cos(aa)
            z = H.TRUNK_C[1] + s * math.sin(aa)
            rad_ = lerp(r0, r0 * 0.28, t ** 0.75)
            # rises out of the flare, lies half-buried along the surface, then dives under the litter
            collar = max(0.0, 1 - (s - start) / 0.35)
            hump = 0.5 + 0.5 * math.sin(s * 2.7 + w1)
            above = -0.2 + 0.5 * hump + 0.7 * collar - 1.0 * smoothstep(0.55, 1.0, t)
            if heave:
                above = 0.35 + 0.25 * hump + 0.5 * collar
            y = H.ring_soil_y(x, z) + rad_ * 0.6 * above
            pts.append((x, y, z))
            s += 0.07
        paths.append((pts, r0, r0 * 0.28))
        # side roots off the larger ones
        if r0 >= 0.08 and len(pts) > 10:
            for frac, side in ((0.32, rr.choice((-1, 1))), (0.6, 0)):
                if side == 0:
                    if r0 < 0.09:
                        continue
                    side = rr.choice((-1, 1))
                b0 = pts[int(len(pts) * frac)]
                sp = []
                ln = rr.uniform(0.45, 0.8)
                steps = max(4, int(ln / 0.07))
                for i in range(steps + 1):
                    t = i / steps
                    aa = a_ + side * (0.55 + 0.35 * t) + 0.1 * math.sin(i * 1.3 + w2)
                    sx = b0[0] + ln * t * math.cos(aa)
                    sz = b0[2] + ln * t * math.sin(aa)
                    rr_ = r0 * 0.42 * (1 - 0.7 * t)
                    sp.append((sx, H.ring_soil_y(sx, sz) + rr_ * 0.6 * (0.4 - 1.2 * smoothstep(0.5, 1.0, t)), sz))
                paths.append((sp, r0 * 0.42, r0 * 0.12))

    # ------------------------------------------------------------------ battle damage + finish
    scatter_impacts(scars, faces_for_scars, 7, srng, 0.3, 1.25, 0.45, 1.1)
    # the +X side faced the West Gate: two heavy clusters there
    FW = Frame(Vector((H.E - H.BLOCK, 0, 0)), Vector((0, 0, -1)), Vector((1, 0, 0)))
    scars.impact(tuple(FW.P(4.6, 0.8, 0.1)), 1.3, 1.0)
    scars.impact(tuple(FW.P(-5.1, 0.55, 0.1)), 1.0, 0.85)

    # colliders: resolve cheek boxes into axis-aligned world boxes
    cols = []
    for c_ in rec["colliders"]:
        name = c_["_side"]
        n = dict((s[0], s[1]) for s in H.SIDES)[name]
        N, Lx = side_axes(n)
        (wa, wb), (u0, u1), top = c_["_w"], c_["_u"], c_["_top"]
        p0 = N * H.E + Lx * u0 + N * wa
        p1 = N * H.E + Lx * u1 + N * wb
        lo = Vector((min(p0.x, p1.x), 0.0, min(p0.z, p1.z)))
        hi = Vector((max(p0.x, p1.x), top, max(p0.z, p1.z)))
        cols.append({"name": c_["name"], "center": [round((lo.x + hi.x) / 2, 4), round(top / 2, 4), round((lo.z + hi.z) / 2, 4)],
                     "size": [round(hi.x - lo.x, 4), round(top, 4), round(hi.z - lo.z, 4)]})
    for tname, tp in H.TERMINALS:
        pass
    rec["colliders"] = cols

    parts = [walls, stairs, ring, pave, metal, bed, litter] + ([sand] if lod == 0 else [])
    finalize_parts(parts)
    # low walls: the lit plaza bounces light back, so the ground plane occludes less than on the tall hall facades
    ao = AOBaker([walls, stairs, ring, pave, bed, litter], ground_y=0.0, samples=24 if lod == 0 else 10, ground_weight=0.16, strength=0.85)
    objs = [walls.build(coll, ao=ao, drips=drips, ground_y=0.0, scars=scars),
            stairs.build(coll, ao=ao, drips=drips, ground_y=0.0, splash=0.18, scars=scars),
            ring.build(coll, ao=ao, drips=drips, ground_y=H.HT, splash=0.3, scars=scars),
            pave.build(coll, ao=ao, drips=drips, ground_y=H.HT, splash=0.1, scars=scars),
            metal.build(coll),
            bed.build(coll, macro=0.0, splash=0.0),
            litter.build(coll, macro=0.0, splash=0.0),
            root_mesh(f"WH_Roots_LOD{lod}", paths, coll, lod)]
    if lod == 0:
        objs.append(sand.build(coll, macro=0.0, splash=0.0))
    else:
        sand.bm.free()
    rec["triangles"] = tri_count(objs)
    rec["objects"] = {o.name: sum(len(pl.vertices) - 2 for pl in o.data.polygons) for o in objs}
    rec["vertex_ao_rays"] = ao.rays
    return coll, objs, rec


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    report = {"source": "art/hill_20260930/author_ward_hill.py", "date": "2026-09-30",
              "units": "Unity metres local to the hill root at world (0, 0, 0)", "lods": {}}
    for lod in (0, 1):
        coll, objs, rec = build(lod)
        export(objs, OUT / f"WardHill_LOD{lod}.glb")
        report["lods"][f"LOD{lod}"] = {"triangles": rec["triangles"], "objects": rec["objects"]}
        if lod == 0:
            report.update({k: v for k, v in rec.items() if k not in ("triangles", "objects")})
        print(f"WardHill LOD{lod}: {rec['triangles']} triangles", rec["objects"], flush=True)
    report["terminal_yaws"] = {n: H.face_yaw_to_tree(p) for n, p in H.TERMINALS}
    (OUT / "ward-hill.json").write_text(json.dumps(report, indent=1))
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "hill-source.blend"))


main()
