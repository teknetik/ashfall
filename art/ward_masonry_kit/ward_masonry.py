"""Ward masonry kit: shared Blender (5.2, headless) geometry helpers for Ward's authored stone buildings.

30 September 2026. Extracted from art/vanguard_hall_20260930/author_vanguard_hall.py and extended after Carl's review
of the rebuilt hall ("walls in full shade look flat, stone edges are too clean close up, the rain stains are too faint"):

* Dressed blocks (LOD0) get subdivided arrises that are eroded with 3D noise, a 3-5 cm inset margin and a slightly
  pillowed face, more frequent/larger chips and occasional spalls (more at the wall foot and on corner piers).
* Per-vertex sky occlusion is ray-traced against the whole building + ground (AOBaker) instead of analytic guesses.
* Vertex colour RGB = per-block tint x broad (2-4 m) tint drift x wall-foot soil splash; A = sky occlusion.
* UV1 = (runoff, worn arris), UV2 = (rust, 0) for Athen Hill/Masonry Lit. Runoff/rust come from DripSet sources
  registered while authoring (cornices, sills, string courses, scuppers, iron corbels, lamps, plates).

Coordinates are Unity metres local to a building root: X east, Y up, Z north. U() converts to Blender; the glTF export
(+Y up) and glTFast import map Blender (x, y, z) back to Unity (-x, z, -y).

Usage from a building script:
    import sys; sys.path.insert(0, str(KIT)); from ward_masonry import *
    set_state(lod, random.Random(seed), "shopname")
    ... build Parts ...
    finalize_parts(parts); ao = AOBaker(parts, ground_y=0.0); drips = DripSet(...)
    objs = [p.build(coll, ao=ao, drips=drips, ground_y=0.0) for p in masonry_parts] + [...]
"""
import bpy, bmesh, math, random, zlib
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.noise import noise as pnoise


class _State:
    LOD = 0
    LAYOUT = random.Random(0)
    NS = "ward"


S = _State()
ROLE_GENERIC, ROLE_FRONT, ROLE_RING, ROLE_BEVEL, ROLE_RETURN = 0, 1, 2, 3, 4


def set_state(lod, layout, namespace):
    S.LOD, S.LAYOUT, S.NS = lod, layout, namespace


def U(p):
    return Vector((-p[0], -p[2], p[1]))


def lerp(a, b, t):
    return a + (b - a) * t


def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def drng(*key):
    """Detail RNG (LOD0-only decisions) seeded from a stable key so layouts stay identical across LODs and runs."""
    return random.Random(zlib.crc32(repr((S.NS,) + key).encode()))


def nz(p, f, seed=0.0):
    """mathutils Perlin noise in [-1, 1] at frequency f (per metre)."""
    return pnoise(Vector((p[0] * f + seed, p[1] * f + seed * 0.37, p[2] * f - seed * 0.71)))


def split_edge(e, n):
    """Insert n evenly spaced vertices into edge e without re-tessellating its faces (they become n-gons).
    Returns the edge pieces in order."""
    if not e.is_valid:
        return []
    if n <= 0:
        return [e]
    v0, v1 = e.verts[0], e.verts[1]
    cur = e
    pieces = []
    for k in range(n):
        remaining = n + 1 - k
        ne, nv = bmesh.utils.edge_split(cur, v0, 1.0 / remaining)
        if v1 in ne.verts:
            pieces.append(cur)
            cur = ne
        else:
            pieces.append(ne)
        v0 = nv
    pieces.append(cur)
    return pieces


def eroded_bevel(part, edges, offset, segs=2, seg_len=0.15):
    """Bevel edges; at LOD0 split them first so the arris erosion (block 'erode') has vertices to move."""
    if S.LOD == 0 and seg_len > 0:
        edges = [piece for e in edges for piece in split_edge(e, int(e.calc_length() / seg_len))]
    part.bevel_edges(edges, offset, segs)


# ================================================================ geometry builder
class Part:
    """One output object. Geometry is authored in Unity coordinates, converted on build()."""

    def __init__(self, name, wear=True):
        self.name = name
        self.bm = bmesh.new()
        self.blk = self.bm.faces.layers.int.new("blk")
        self.role = self.bm.faces.layers.int.new("role")
        self.mats = []
        self.blocks = [dict(off=(0.0, 0.0), tint=(0.5, 0.5, 0.5), scale=1.0, ao=None, erode=0.0)]  # 0 = default
        self.pending = {}   # (offset, segments) -> edges; bevelled together in finalize()
        self.wear = wear    # export the UV1/UV2 wear channels (masonry materials)
        self.finalized = False

    def mi(self, m):
        if m not in self.mats:
            self.mats.append(m)
        return self.mats.index(m)

    def new_block(self, tint=None, off=None, scale=1.0, ao=None, erode=None, cyl=None):
        """cyl = (point on axis, axis direction): faces of this block get cylindrical UVs (u round the circumference in
        metres, v along the axis) instead of the box projection; caps (normal along the axis) keep the box projection.
        Added 3 Oct 2026 (ward buildings round two) for painted tanks/cylinders; default None = unchanged behaviour."""
        if off is None:
            off = (S.LAYOUT.uniform(0, 8), S.LAYOUT.uniform(0, 8))
        if erode is None:
            erode = 0.006 if self.wear else 0.0
        self.blocks.append(dict(off=off, tint=tint or (0.5, 0.5, 0.5), scale=scale, ao=ao, erode=erode, cyl=cyl))
        return len(self.blocks) - 1

    # ---- primitives
    def hexa(self, c, mat, bid=0, skip=(), role=ROLE_GENERIC):
        """c = 8 corners: bottom ring b0..b3 then top ring t0..t3 (same order). Convex hexahedron."""
        vs = [self.bm.verts.new(Vector(p)) for p in c]
        centre = sum((v.co for v in vs), Vector()) / 8
        faces = {"bottom": [0, 3, 2, 1], "top": [4, 5, 6, 7], "s0": [0, 1, 5, 4], "s1": [1, 2, 6, 5],
                 "s2": [2, 3, 7, 6], "s3": [3, 0, 4, 7]}
        made = {}
        idx = self.mi(mat)
        for k, ids in faces.items():
            if k in skip:
                continue
            f = self.bm.faces.new([vs[i] for i in ids])
            fc = sum((vs[i].co for i in ids), Vector()) / 4
            n = (vs[ids[1]].co - vs[ids[0]].co).cross(vs[ids[3]].co - vs[ids[0]].co)
            if n.dot(fc - centre) < 0:
                f.normal_flip()
            f.material_index = idx
            f[self.blk] = bid
            f[self.role] = role
            made[k] = f
        return vs, made

    def box(self, lo, hi, mat, bid=0, skip=()):
        x0, y0, z0 = lo
        x1, y1, z1 = hi
        c = [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1), (x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)]
        return self.hexa(c, mat, bid, skip)

    def bevel_edges(self, edges, offset, segs):
        if S.LOD > 0:
            segs = 1
            offset *= 0.8
        if not edges or offset <= 0:
            return
        key = (round(offset / 0.002) * 0.002, segs)
        self.pending.setdefault(key, []).extend(edges)

    def finalize(self):
        """Run the deferred bevels, tag bevel faces as arrises and erode them (LOD0)."""
        if self.finalized:
            return
        bevel_verts = set()
        TEMP = 32000   # bevel faces are born with this material index so they can be told apart from the faces
        #                the bevel merely reshapes (bmesh.ops.bevel's "faces" output contains both)
        for (offset, segs), edges in sorted(self.pending.items()):
            edges = list({e for e in edges if e.is_valid})
            if edges:
                bmesh.ops.bevel(self.bm, geom=edges, offset=offset, offset_type="OFFSET", segments=segs, profile=0.5,
                                affect="EDGES", clamp_overlap=True, loop_slide=True, material=TEMP)
                for f in self.bm.faces:
                    if f.material_index == TEMP:
                        f[self.role] = ROLE_BEVEL
                        bevel_verts.update(f.verts)
                        src = next((g for e in f.edges for g in e.link_faces if g.material_index != TEMP), None)
                        f.material_index = src.material_index if src else 0
                        if src is not None:
                            f[self.blk] = src[self.blk]
        self.pending = {}
        if S.LOD == 0 and bevel_verts:
            self.bm.normal_update()
            moves = []
            for v in bevel_verts:
                if not v.is_valid:
                    continue
                er = 0.0
                for f in v.link_faces:
                    if f[self.blk] < len(self.blocks):
                        er = max(er, self.blocks[f[self.blk]]["erode"])
                if er <= 0:
                    continue
                p = v.co
                n1 = nz(p, 7.0, 3.1) * 0.5 + 0.5
                n2 = nz(p, 23.0, 8.7) * 0.5 + 0.5
                d = er * (0.25 + 0.75 * n1 ** 1.6) + er * 0.35 * n2
                moves.append((v, -v.normal * d))
            for v, dv in moves:
                v.co += dv
        self.finalized = True

    def cyl(self, a, b, r, mat, sides=12, cap=True, bid=0, r2=None):
        a, b = Vector(a), Vector(b)
        d = (b - a)
        L = d.length
        if L < 1e-6:
            return
        if S.LOD > 0:
            sides = max(6, sides // 2)
        dn = d.normalized()
        ref = Vector((0, 1, 0)) if abs(dn.y) < 0.9 else Vector((1, 0, 0))
        s1 = dn.cross(ref).normalized()
        s2 = dn.cross(s1).normalized()
        r2 = r if r2 is None else r2
        ring0 = [self.bm.verts.new(a + (s1 * math.cos(t) + s2 * math.sin(t)) * r)
                 for t in [2 * math.pi * i / sides for i in range(sides)]]
        ring1 = [self.bm.verts.new(b + (s1 * math.cos(t) + s2 * math.sin(t)) * r2)
                 for t in [2 * math.pi * i / sides for i in range(sides)]]
        idx = self.mi(mat)
        fs = []
        for i in range(sides):
            j = (i + 1) % sides
            fs.append(self.bm.faces.new([ring0[i], ring0[j], ring1[j], ring1[i]]))
        if cap:
            fs.append(self.bm.faces.new(ring0[::-1]))
            fs.append(self.bm.faces.new(ring1))
        for f in fs:
            f.material_index = idx
            f[self.blk] = bid
        bmesh.ops.recalc_face_normals(self.bm, faces=fs)
        return fs

    def tube(self, pts, r, mat, sides=10, bid=0, clamps=0.0, clamp_mat=None):
        """Polyline conduit with mitre-free joints (short sleeves at bends)."""
        pts = [Vector(p) for p in pts]
        for a, b in zip(pts, pts[1:]):
            self.cyl(a, b, r, mat, sides, cap=True, bid=bid)
        for p in pts[1:-1]:
            self.sphere(p, r * 1.15, mat, 8 if S.LOD == 0 else 6)
        if clamps > 0 and S.LOD == 0:
            for a, b in zip(pts, pts[1:]):
                L = (b - a).length
                n = int(L / clamps)
                for k in range(1, n + 1):
                    p = a + (b - a) * (k / (n + 1))
                    self.cyl(p - (b - a).normalized() * 0.02, p + (b - a).normalized() * 0.02, r * 1.45, clamp_mat or mat, 8)

    def sphere(self, c, r, mat, seg=8, bid=0, hemi_axis=None):
        res = bmesh.ops.create_uvsphere(self.bm, u_segments=seg, v_segments=max(4, seg // 2), radius=r)
        vs = res["verts"]
        c = Vector(c)
        fs = list({f for v in vs for f in v.link_faces})
        if hemi_axis is not None:
            ax = Vector(hemi_axis).normalized()
            kill = [v for v in vs if v.co.dot(ax) < -1e-4]
            bmesh.ops.delete(self.bm, geom=kill, context="VERTS")
            vs = [v for v in vs if v.is_valid]
            fs = list({f for v in vs for f in v.link_faces})
        for v in vs:
            v.co = v.co + c
        idx = self.mi(mat)
        for f in fs:
            f.material_index = idx
            f[self.blk] = bid
        return fs

    def closed_solid(self, verts, faces, mat, bid=0):
        vs = [self.bm.verts.new(Vector(p)) for p in verts]
        idx = self.mi(mat)
        fs = []
        for ids in faces:
            f = self.bm.faces.new([vs[i] for i in ids])
            f.material_index = idx
            f[self.blk] = bid
            fs.append(f)
        bmesh.ops.recalc_face_normals(self.bm, faces=fs)
        return vs, fs

    # ---- finalise
    def build(self, collection, ao=None, drips=None, ground_y=0.0, ao_fn=None, flat=False, macro=0.1, splash=0.38, scars=None):
        """ao: AOBaker (per-vertex sky occlusion) or ao_fn(p, n) legacy; drips: DripSet for the wear UVs.
        macro: broad tint drift amplitude; splash: wall-foot soiling strength (0 disables)."""
        self.finalize()
        bm = self.bm
        bm.faces.ensure_lookup_table()
        bm.verts.index_update()
        uv = bm.loops.layers.uv.new("UVMap")
        uvw = bm.loops.layers.uv.new("Wear") if self.wear else None
        uvr = bm.loops.layers.uv.new("Rust") if self.wear else None
        col = bm.loops.layers.color.new("Col")
        bm.normal_update()
        vcache = {}
        for f in bm.faces:
            info = self.blocks[f[self.blk]] if f[self.blk] < len(self.blocks) else self.blocks[0]
            n = f.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            ou, ov = info["off"]
            s = info["scale"]
            tr, tg, tb = info["tint"]
            role = f[self.role]
            cyluv = None
            if info.get("cyl") is not None:
                ca, cd = Vector(info["cyl"][0]), Vector(info["cyl"][1]).normalized()
                if abs(n.dot(cd)) < 0.7:
                    rf = Vector((0, 1, 0)) if abs(cd.y) < 0.9 else Vector((1, 0, 0))
                    e1 = cd.cross(rf).normalized()
                    e2 = cd.cross(e1).normalized()
                    angs, rads, alongs = [], [], []
                    for l in f.loops:
                        q = l.vert.co - ca
                        al = q.dot(cd)
                        rv = q - cd * al
                        angs.append(math.atan2(rv.dot(e2), rv.dot(e1)))
                        rads.append(rv.length)
                        alongs.append(al)
                    if max(angs) - min(angs) > math.pi:
                        angs = [a_ + 2 * math.pi if a_ < 0 else a_ for a_ in angs]
                    rm = sum(rads) / len(rads)
                    cyluv = [(a_ * rm, al) for a_, al in zip(angs, alongs)]
            for li, l in enumerate(f.loops):
                v = l.vert
                p = v.co
                if ax == 0:
                    u_, v_ = (-p.z if n.x > 0 else p.z), p.y
                elif ax == 2:
                    u_, v_ = (p.x if n.z > 0 else -p.x), p.y
                else:
                    u_, v_ = p.x, (p.z if n.y > 0 else -p.z)
                if cyluv is not None:
                    u_, v_ = cyluv[li]
                l[uv].uv = (u_ * s + ou, v_ * s + ov)
                vk = v.index
                if vk not in vcache:
                    a = 1.0
                    if ao is not None:
                        a = ao.vertex(self, v)
                    elif ao_fn is not None:
                        a = ao_fn(p, v.normal)
                    m = 1.0
                    hue = 0.0
                    if macro > 0:
                        m += macro * nz(p, 0.33, 11.0) + macro * 0.5 * nz(p, 0.9, 4.0)
                        hue = macro * 0.6 * nz(p, 0.21, 21.0)
                    sp = 0.0
                    if splash > 0:
                        h = p.y - ground_y
                        sp = splash * (1 - smoothstep(0.0, 0.95, h)) * (0.55 + 0.45 * (nz(p, 2.3, 7.0) * 0.5 + 0.5))
                    rw = rs = 0.0
                    if drips is not None and self.wear:
                        rw, rs = drips.eval(p, v.normal)
                    dmg = soot = 0.0
                    if scars is not None and self.wear:
                        dmg = scars.damage(p)
                        soot = scars.soot(p, v.normal)
                        m *= 1 - 0.62 * soot
                    vcache[vk] = (a, m, hue, sp, rw, rs, dmg)
                a, m, hue, sp, rw, rs, dmg = vcache[vk]
                if info["ao"] is not None:
                    a *= info["ao"]
                cr = tr * m * (1 + hue) * (1 - sp * 0.2)
                cg = tg * m * (1 - sp * 0.28)
                cb = tb * m * (1 - hue) * (1 - sp * 0.38)
                l[col] = (min(1.0, cr), min(1.0, cg), min(1.0, cb), max(0.0, min(1.0, a)))
                if uvw is not None:
                    edge = 0.0
                    if role == ROLE_BEVEL:
                        edge = 1.0
                    elif role == ROLE_RING and any(lf[self.role] == ROLE_BEVEL for lf in v.link_faces):
                        edge = 0.75       # the 1-4.5 cm dressed margin fades from the broken arris to the face
                    l[uvw].uv = (rw, edge)
                    l[uvr].uv = (rs, dmg)
        # Unity -> Blender (a reflection): move verts and flip winding to keep outward normals
        for v in bm.verts:
            v.co = U(v.co)
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
        me = bpy.data.meshes.new(self.name)
        bm.to_mesh(me)
        bm.free()
        for mname in self.mats:
            me.materials.append(material(mname))
        ob = bpy.data.objects.new(self.name, me)
        collection.objects.link(ob)
        me.color_attributes.active_color_name = "Col"
        me.color_attributes.render_color_index = 0
        me.uv_layers.active_index = 0
        if flat:
            for p in me.polygons:
                p.use_smooth = False
        else:
            for p in me.polygons:
                p.use_smooth = True
            me.set_sharp_from_angle(angle=math.radians(38))
            bpy.context.view_layer.objects.active = ob
            wn = ob.modifiers.new("wn", "WEIGHTED_NORMAL")
            wn.keep_sharp = True
            wn.mode = "FACE_AREA"
            wn.weight = 50
            for o in bpy.context.selected_objects:
                o.select_set(False)
            ob.select_set(True)
            bpy.ops.object.modifier_apply(modifier="wn")
        triangulate(ob)
        return ob


MATERIALS = {}


def triangulate(ob):
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    t = ob.modifiers.new("tri", "TRIANGULATE")
    t.quad_method = "BEAUTY"
    t.ngon_method = "BEAUTY"
    t.keep_custom_normals = True
    bpy.ops.object.modifier_apply(modifier="tri")


def material(name):
    if name not in MATERIALS:
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        MATERIALS[name] = m
    return MATERIALS[name]


def reset_materials():
    MATERIALS.clear()


def finalize_parts(parts):
    for p in parts:
        p.finalize()


# ================================================================ sky occlusion
class AOBaker:
    """Per-vertex sky occlusion ray-traced against every part of the building plus a ground plane.
    Values are cached per (part, vertex index); call after finalize_parts() and before any build()."""

    def __init__(self, parts, ground_y=0.0, extra=(), samples=24, dist=3.2, strength=1.0, floor=0.22, ground_size=40.0,
                 near=0.09, ground_weight=0.35):
        verts, polys = [], []
        for part in list(parts) + list(extra):
            bm = part.bm
            bm.verts.index_update()
            off = len(verts)
            verts.extend(v.co.copy() for v in bm.verts)
            polys.extend([off + v.index for v in f.verts] for f in bm.faces)
        g = ground_size
        off = len(verts)
        verts.extend([Vector((-g, ground_y, -g)), Vector((g, ground_y, -g)), Vector((g, ground_y, g)), Vector((-g, ground_y, g))])
        polys.append([off, off + 1, off + 2, off + 3])
        self.tree = BVHTree.FromPolygons(verts, polys, all_triangles=False, epsilon=0.0)
        self.ground_index = len(polys) - 1
        self.near, self.ground_weight = near, ground_weight
        self.dist, self.strength, self.floor = dist, strength, floor
        # cosine-weighted hemisphere (Fibonacci spiral), local frame z = normal
        self.dirs = []
        ga = math.pi * (3 - math.sqrt(5))
        for i in range(samples):
            r = math.sqrt((i + 0.5) / samples)
            th = i * ga
            self.dirs.append((r * math.cos(th), r * math.sin(th), math.sqrt(max(0.0, 1 - r * r))))
        self.cache = {}
        self.rays = 0

    def vertex(self, part, v):
        key = (id(part), v.index)
        if key in self.cache:
            return self.cache[key]
        n = v.normal
        if n.length < 1e-6:
            n = Vector((0, 1, 0))
        n = n.normalized()
        t = n.cross(Vector((0, 1, 0)) if abs(n.y) < 0.9 else Vector((1, 0, 0))).normalized()
        b = n.cross(t)
        p = v.co + n * 0.012
        occ = 0.0
        # rays start `near` metres out: joint-scale occlusion is left to the mortar recess, SSAO and the texture AO,
        # so the vertex term carries only building-scale shelter (reveals, soffits, cornices, portal, ground line)
        for dx, dy, dz in self.dirs:
            d = t * dx + b * dy + n * dz
            hit, _n, idx, dd = self.tree.ray_cast(p + d * self.near, d, self.dist)
            if hit is not None:
                w = self.ground_weight if idx == self.ground_index else 1.0
                occ += w * (1.0 - ((dd + self.near) / self.dist) ** 0.7 * 0.6)
        self.rays += len(self.dirs)
        vis = 1.0 - self.strength * occ / len(self.dirs)
        a = self.floor + (1 - self.floor) * max(0.0, vis)
        self.cache[key] = a
        return a


# ================================================================ runoff / rust sources
class Drip:
    """A drip edge on a vertical face. normal = outward face normal (unit X or Z, sign), plane = face coordinate on
    that axis (x or z), u0..u1 = horizontal extent along the other axis, top = drip height, length = how far the
    stain runs down, strength = 0..1 at the top, kind 'grime' or 'rust', soft = horizontal feather (m)."""
    __slots__ = ("axis", "sign", "plane", "u0", "u1", "top", "length", "strength", "rust", "soft", "reach")

    def __init__(self, normal, plane, u0, u1, top, length, strength=1.0, kind="grime", soft=0.12, reach=0.9):
        self.axis = 0 if abs(normal[0]) > 0.5 else 2
        self.sign = 1 if normal[self.axis] > 0 else -1
        self.plane, self.u0, self.u1 = plane, min(u0, u1), max(u0, u1)
        self.top, self.length, self.strength, self.rust, self.soft, self.reach = top, length, strength, kind == "rust", soft, reach


class DripSet:
    def __init__(self, base=0.1, base_top=None, ground_y=0.0):
        self.items = []
        self.base, self.base_top, self.ground_y = base, base_top, ground_y

    def add(self, *a, **k):
        self.items.append(Drip(*a, **k))

    def eval(self, p, n):
        if abs(n.y) > 0.6:
            return 0.0, 0.0
        grime = rust = 0.0
        for d in self.items:
            if n[d.axis] * d.sign < 0.45:
                continue
            if abs(p[d.axis] - d.plane) > d.reach:
                continue
            if p.y > d.top + 0.03 or p.y < d.top - d.length:
                continue
            u = p[2 if d.axis == 0 else 0]
            if u < d.u0 - d.soft or u > d.u1 + d.soft:
                continue
            hw = smoothstep(d.u0 - d.soft, d.u0 + d.soft * 0.4, u) * (1 - smoothstep(d.u1 - d.soft * 0.4, d.u1 + d.soft, u))
            t = max(0.0, min(1.0, (d.top - p.y) / d.length))
            w = d.strength * hw * (1 - t) ** 1.25
            if d.rust:
                rust = max(rust, w)
            else:
                grime = max(grime, w)
        if self.base > 0 and self.base_top:
            grime = max(grime, self.base * smoothstep(self.ground_y + 1.5, self.base_top, p.y))
        return min(1.0, grime), min(1.0, rust)


class ScarSet:
    """Old battle damage (Carl, 30 Sep 2026: "this place saw a battle take place long ago"). impact(): a cluster of
    shrapnel scars and dense pitting around a wall point (UV2.y damage weight for Masonry Lit); plume(): soot from an
    old fire rising above an opening, baked as vertex-colour darkening. base = light scattered damage everywhere."""

    def __init__(self, base=0.1):
        self.base = base
        self.impacts = []
        self.plumes = []

    def impact(self, centre, radius, strength=1.0):
        self.impacts.append((Vector(centre), radius, strength))

    def plume(self, normal, plane, u0, u1, y0, height, strength=0.8):
        self.plumes.append(Drip(normal, plane, u0, u1, y0, height, strength, "grime", soft=0.35, reach=0.8))

    def damage(self, p):
        w = self.base
        for c, r, st in self.impacts:
            d = (p - c).length
            if d < r:
                w = max(w, st * (1 - smoothstep(r * 0.25, r, d)))
        return min(1.0, w)

    def soot(self, p, n):
        if abs(n.y) > 0.6:
            return 0.0
        s = 0.0
        for d in self.plumes:
            if n[d.axis] * d.sign < 0.45 or abs(p[d.axis] - d.plane) > d.reach:
                continue
            if p.y < d.top - 0.15 or p.y > d.top + d.length:
                continue
            t = max(0.0, min(1.0, (p.y - d.top) / d.length))
            widen = d.soft + t * 0.6
            u = p[2 if d.axis == 0 else 0]
            hw = smoothstep(d.u0 - widen, d.u0 + 0.1, u) * (1 - smoothstep(d.u1 - 0.1, d.u1 + widen, u))
            s = max(s, d.strength * hw * (1 - t) ** 0.8 * smoothstep(d.top - 0.15, d.top + 0.1, p.y))
        return min(1.0, s)


def scatter_impacts(scars, faces, n, rng, y0, y1, rmin=0.5, rmax=1.4):
    """faces: list of (Frame, u0, u1); n clusters at random points on them (wall surface, d = 0.07)."""
    for _ in range(n):
        F, u0, u1 = rng.choice(faces)
        c = F.P(rng.uniform(u0, u1), rng.uniform(y0, y1), 0.07)
        scars.impact(tuple(c), rng.uniform(rmin, rmax), rng.uniform(0.6, 1.0))


# ================================================================ stone helpers
TINT = [1.0, 1.0, 1.0]     # per-building stone colour multiplier (set by the building script)


def stone_tint(kind="ashlar", sigma=0.125):
    r = S.LAYOUT
    v = max(0.76, min(1.22, r.gauss(1.0, sigma)))
    warm = r.gauss(0, 0.035)
    t = [v * (1 + warm), v, v * (1 - warm * 1.6)]
    roll = r.random()
    if roll < 0.06:          # later replacement stone: paler, slightly cooler
        t = [c * f for c, f in zip(t, (1.12, 1.11, 1.12))]
    elif roll < 0.11:        # darker weathered stone
        t = [c * f for c, f in zip(t, (0.82, 0.78, 0.74))]
    elif roll < 0.15:        # iron-stained bed: warmer, slightly pink
        t = [c * f for c, f in zip(t, (1.035, 0.96, 0.9))]
    if kind == "rough":
        t = [c * 0.95 for c in t]
    return tuple(0.5 * c * k for c, k in zip(t, TINT))


class Frame:
    """Axis-aligned wall frame: P(u, y, d) = origin + u * uaxis + (0, y, 0) + d * n."""

    def __init__(self, origin, uaxis, n):
        self.o, self.u, self.n = Vector(origin), Vector(uaxis), Vector(n)

    def P(self, u, y, d):
        return self.o + self.u * u + Vector((0, y, 0)) + self.n * d

    def box(self, part, u0, u1, y0, y1, d0, d1, mat, bid=0, skip=()):
        c = [self.P(u0, y0, d0), self.P(u1, y0, d0), self.P(u1, y0, d1), self.P(u0, y0, d1),
             self.P(u0, y1, d0), self.P(u1, y1, d0), self.P(u1, y1, d1), self.P(u0, y1, d1)]
        return part.hexa(c, mat, bid, skip)


WEAR = dict(ground_y=0.0, wear_scale=1.0)
MORTAR_FRONT = 0.036     # fill_wall's mortar plane (block faces at ~0.062): joints read ~2.6 cm deep


def block_wear(y):
    """0..1 weathering level for a block whose bottom is at height y (more at the wall foot)."""
    return WEAR["wear_scale"] * (0.45 + 0.55 * (1 - smoothstep(WEAR["ground_y"] + 0.3, WEAR["ground_y"] + 2.6, y)))


def ashlar_block(part, F, u0, u1, y0, y1, mat="VH_Ashlar", depth=0.062, back=0.035, bevel=(0.010, 0.022),
                 key=None, tint=None, chip=0.10, ao=None, face_jitter=0.003, bottom=False, top=False, rough=None,
                 wear=None, mortar_d=MORTAR_FRONT):
    """One dressed block on frame F. Only the front, its four returns (and optionally bottom/top) are built.
    LOD0: chipped/spalled corners, subdivided + eroded arrises, inset margin and pillowed face."""
    rough = (mat.endswith("Rough")) if rough is None else rough
    wl = block_wear(y0) if wear is None else wear
    erode = (0.004 + 0.009 * wl) * (1.35 if rough else 1.0)
    bid = part.new_block(tint=tint or stone_tint("rough" if rough else "ashlar"), ao=ao, erode=erode)
    L = S.LAYOUT
    d1 = depth + L.uniform(-0.004, 0.004)
    corners = [F.P(u0, y0, back), F.P(u1, y0, back), F.P(u1, y0, d1), F.P(u0, y0, d1),
               F.P(u0, y1, back), F.P(u1, y1, back), F.P(u1, y1, d1), F.P(u0, y1, d1)]
    # facet tilt of the dressed face (a little more than a sawn face)
    fj = face_jitter * (1.6 if S.LOD == 0 else 1.0)
    for i in (2, 3, 6, 7):
        corners[i] = corners[i] + F.n * L.uniform(-fj, fj)
    rr = drng(part.name, key or (round(u0, 3), round(y0, 3)))
    skip = ["s0"]  # the back face (b0,b1,t1,t0 lies at d=back)
    # LOD0 keeps the bed faces so the top/bottom arrises have two faces to bevel (open edges cannot be bevelled)
    if not bottom and S.LOD > 0:
        skip.append("bottom")
    if not top and S.LOD > 0:
        skip.append("top")
    vs, made = part.hexa(corners, mat, bid, skip=tuple(skip), role=ROLE_RETURN)
    front = made.get("s2")
    if front is None:
        return bid
    front[part.role] = ROLE_FRONT
    b = L.uniform(*bevel)
    if S.LOD == 0:
        # dressed margin: inset the clean quad (insetting an n-gon with collinear split vertices collapses the margin)
        corner_pos = {i: vs[i].co.copy() for i in (2, 3, 6, 7)}
        w_, h_ = abs(u1 - u0), abs(y1 - y0)
        th = max(0.012, min(0.045, 0.16 * min(w_, h_)))
        front.normal_update()               # inset_individual offsets along the face normal (zero until updated)
        res = bmesh.ops.inset_individual(part.bm, faces=[front], thickness=th, depth=0.0, use_even_offset=True)
        ring = [f for f in res["faces"] if f is not front]
        ring_set = set(ring)
        for f in ring:
            f[part.role] = ROLE_RING
            f[part.blk] = bid
            f.material_index = front.material_index
            f.normal_update()
            if f.normal.dot(F.n) < 0:
                f.normal_flip()
        # inset_individual moves the original vertices inwards: the outer boundary (to bevel) is made of the ring
        # edges that border neither the dressed face nor another ring face
        bnd = list({e for f in ring for e in f.edges
                    if all(g is f or (g is not front and g not in ring_set) for g in e.link_faces)})
        outer_verts = {v for e in bnd for v in e.verts}
        outer_corner = {i: min(outer_verts, key=lambda v, c=c: (v.co - c).length) for i, c in corner_pos.items()} if outer_verts else {}
        # split the outer arrises so the erosion noise has vertices to move (only within reach/eye range)
        hgt = y0 - WEAR["ground_y"]
        seg = 0.15 if hgt < 2.4 else (0.3 if hgt < 4.2 else 0.0)
        if seg > 0:
            bnd = [piece for e in bnd for piece in split_edge(e, int(e.calc_length() / seg))]
        pillow = rr.uniform(0.006, 0.014) * (1.4 if rough else 1.0)   # cushioned face: the margin slopes read in shade
        for v in front.verts:
            v.co += F.n * pillow
        # chips and spalls: dig out a front corner (and its neighbours along both arrises) without crossing the
        # mortar plane behind the joints; only the margin/bevel/returns deform, the dressed face stays true
        room = max(0.0, d1 - back - 0.008)      # chips may bite below the mortar line (the joint shows in the break)
        pchip = min(0.8, chip * 2.4 + 0.3 * wl)
        nchips = (1 if rr.random() < pchip else 0) + (1 if rr.random() < pchip * 0.4 else 0)
        for ci_ in (rr.sample((2, 3, 6, 7), nchips) if outer_corner else ()):
            c = outer_corner[ci_]
            big = rr.random() < 0.3 + 0.3 * wl
            depth_ = min(room, rr.uniform(0.01, 0.02) * (2.0 if big else 1.0))
            inward_u = F.u * (1 if ci_ in (3, 7) else -1)
            inward_y = Vector((0, 1 if ci_ in (2, 3) else -1, 0))
            reach = th * (1.0 if big else 0.65)
            c.co += -F.n * depth_ + inward_u * rr.uniform(0.3, 1.0) * reach + inward_y * rr.uniform(0.3, 1.0) * reach
            # neighbours along the two arrises from this corner
            for e in c.link_edges:
                o = e.other_vert(c)
                if any(f[part.role] == ROLE_FRONT for f in o.link_faces):
                    continue          # inner margin vertex
                if (o.co - c.co).dot(F.n) < -0.02:
                    continue          # the return's back edge
                o.co += -F.n * depth_ * rr.uniform(0.35, 0.7)
            if big:
                # the break runs into the dressed face: pull the nearest face corner and its margin neighbours in
                inner = min(front.verts, key=lambda v: (v.co - c.co).length)
                inner.co += -F.n * depth_ * 0.75 + inward_u * rr.uniform(0.0, 0.03) + inward_y * rr.uniform(0.0, 0.025)
        part.bevel_edges(bnd, b, 2)
    else:
        part.bevel_edges(list(front.edges), b, 2)
    return bid


def course_intervals(u0, u1, holes, y0, y1):
    """Free [a, b] spans of [u0, u1] in the course y0..y1, removing holes (ua, ub, va, vb) that overlap it."""
    cuts = sorted((h[0], h[1]) for h in holes if h[2] < y1 - 1e-3 and h[3] > y0 + 1e-3)
    spans, a = [], u0
    for ha, hb in cuts:
        if hb <= a:
            continue
        if ha > a:
            spans.append((a, min(ha, u1)))
        a = max(a, hb)
        if a >= u1:
            break
    if a < u1:
        spans.append((a, u1))
    return [(a, b) for a, b in spans if b - a > 0.05]


def fill_wall(part, F, u0, u1, courses, holes, mat="VH_Ashlar", lmin=0.62, lmax=1.28, joint=0.009,
              mortar=True, ulimit=None, key="w", ao=None, mortar_mat="VH_Mortar", course_offset=0, depth=0.062):
    """Ashlar courses on frame F over u0..u1; courses = list of y boundaries. ulimit(y0, y1) -> (u0, u1) overrides.
    course_offset shifts the running-bond parity (for walls built one course at a time)."""
    L = S.LAYOUT
    for ci0, (y0, y1) in enumerate(zip(courses, courses[1:])):
        ci = ci0 + course_offset
        a0, a1 = (u0, u1) if ulimit is None else ulimit(y0, y1)
        for (sa, sb) in course_intervals(a0, a1, holes, y0, y1):
            u = sa
            first = True
            while u < sb - 1e-4:
                ln = L.uniform(lmin, lmax)
                if first:
                    ln *= (0.45 + 0.35 * L.random()) if ci % 2 else 1.0
                    first = False
                if sb - (u + ln) < lmin * 0.5:
                    ln = sb - u
                ashlar_block(part, F, u + joint / 2, u + ln - joint / 2, y0 + joint / 2, y1 - joint / 2, mat=mat,
                             key=(key, ci, round(u, 3)), ao=ao, depth=depth)
                u += ln
            if mortar:
                F.box(part, sa, sb, y0, y1, 0.02, MORTAR_FRONT, mortar_mat, skip=("s0", "bottom", "top", "s1", "s3"))


def sweep(part, path, closed, profile, mat, seg=1.2, joint=0.008, bev=0.006, tint=True, erode=None, key=None):
    """Extrude a closed profile [(o, y)] (o = outward offset) along a horizontal path of (x, z) points.
    The outward side is to the right of travel (path drawn clockwise seen from above in Unity)."""
    P = [Vector((p[0], 0, p[1])) for p in path]
    n = len(P)
    edges = list(range(n if closed else n - 1))

    def nrm(i):
        a, b = P[i], P[(i + 1) % n]
        d = (b - a).normalized()
        return Vector((d.z, 0, -d.x)) * -1

    for ei in edges:
        a, b = P[ei], P[(ei + 1) % n]
        d = (b - a)
        L = d.length
        dn = d.normalized()
        nn = nrm(ei)
        prev_n = nrm((ei - 1) % n) if (closed or ei > 0) else None
        next_n = nrm((ei + 1) % n) if (closed or ei < n - 2) else None
        k = max(1, round(L / seg))
        cuts = [L * i / k for i in range(k + 1)]
        for si in range(k):
            ta, tb = cuts[si] + (joint / 2 if si > 0 else 0), cuts[si + 1] - (joint / 2 if si < k - 1 else 0)

            def pt(t, o, y, end):
                base = a + dn * t + nn * o
                if end == 0 and si == 0 and prev_n is not None:
                    base = a + nn * o + prev_n * o
                if end == 1 and si == k - 1 and next_n is not None:
                    base = b + nn * o + next_n * o
                return Vector((base.x, y, base.z))

            ring_a = [pt(ta, o, y, 0) for o, y in profile]
            ring_b = [pt(tb, o, y, 1) for o, y in profile]
            m = len(profile)
            verts = ring_a + ring_b
            faces = [[i, (i + 1) % m, m + (i + 1) % m, m + i] for i in range(m)]
            faces.append(list(range(m))[::-1])
            faces.append([m + i for i in range(m)])
            y_lo = min(y for _, y in profile)
            er = (0.003 + 0.006 * block_wear(y_lo)) if erode is None else erode
            bid = part.new_block(tint=stone_tint() if tint else (0.5, 0.5, 0.5), erode=er)
            vs, fs = part.closed_solid(verts, faces, mat, bid)
            if bev > 0:
                sharp = [e for e in {e for f in fs for e in f.edges} if e.calc_face_angle(0) > math.radians(40)]
                if S.LOD == 0 and y_lo - WEAR["ground_y"] < 3.2:
                    # subdivide the long arrises for the erosion noise (only trims within reach of the eye)
                    for e in sharp:
                        split_edge(e, int(e.calc_length() / 0.14))
                    fs = [f for f in {f for v in vs for f in v.link_faces}]
                    sharp = [e for e in {e for f in fs for e in f.edges} if e.calc_face_angle(0) > math.radians(40)]
                part.bevel_edges(sharp, bev, 2)


def lettering(text, font_path, size, centre, depth, width_limit, mat, coll, name, lod=0, spacing=1.08,
              facing=(0, 0, 1)):
    """Raised 3D lettering (Blender text -> mesh), centred at Unity point `centre` on a plane facing `facing`
    (+Z or -Z / +X / -X in Unity). Returns the object (already triangulated, Col/UVMap layers)."""
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = text
    cu.font = bpy.data.fonts.load(str(font_path), check_existing=True)
    cu.size = size
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.extrude = depth / 2
    cu.bevel_depth = min(0.0025, depth * 0.25) if lod == 0 else 0.0
    cu.bevel_resolution = 1
    cu.space_character = spacing
    cu.resolution_u = 5 if lod == 0 else 2
    txt = bpy.data.objects.new(name, cu)
    coll.objects.link(txt)
    # Blender text lies in XY facing +Z(blender). Stand it up to face Unity +Z (= Blender -Y), then yaw.
    fx, _, fz = facing
    # +90 about Blender X stands the text up facing Blender -Y (= Unity +Z), reading along Blender +X (= Unity -X,
    # the viewer's right). A Blender Z rotation then turns it to the other Unity facings.
    rotz = {(0, 1): 0.0, (0, -1): math.pi, (1, 0): -math.pi / 2, (-1, 0): math.pi / 2}[(int(round(fx)), int(round(fz)))]
    txt.rotation_euler = (math.radians(90), 0, rotz)
    txt.location = U(centre)
    bpy.context.view_layer.update()
    for o in bpy.context.selected_objects:
        o.select_set(False)
    txt.select_set(True)
    bpy.context.view_layer.objects.active = txt
    bpy.ops.object.convert(target="MESH")
    txt = bpy.context.view_layer.objects.active
    # fit width
    pts = [txt.matrix_world @ v.co for v in txt.data.vertices]
    horiz = 0 if abs(fz) > 0.5 else 1
    width = max(p[horiz] for p in pts) - min(p[horiz] for p in pts)
    if width > width_limit:
        k = width_limit / width
        txt.scale = (k, k, k)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    txt.data.materials.clear()
    txt.data.materials.append(material(mat))
    me = txt.data
    uvl = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uvl.data[li].uv = (co.x + co.y, co.z)
    colattr = me.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
    for d in colattr.data:
        d.color = (0.5, 0.5, 0.5, 1.0)
    for p in me.polygons:
        p.use_smooth = False
    triangulate(txt)
    return txt, width


def export(objs, path):
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True, export_yup=True,
                              export_image_format="NONE", export_tangents=True, export_normals=True, export_apply=True,
                              export_vertex_color="ACTIVE", export_extras=False, export_materials="EXPORT")


def tri_count(objs):
    return sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs)
