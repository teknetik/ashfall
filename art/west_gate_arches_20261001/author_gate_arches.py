"""West Gate arches: sealed working gates for the two District gate arches at the +X spawn (1 Oct 2026, Blender 5.2).

Run:  $O/blender.sh author_gate_arches.py [-- A B]
Writes Assets/AthenHill/Art/WestGateArches/Models/WGA_Gate<K>.glb (LOD0-2 of every group, COL_ boxes, LIGHT_ empty)
and gate-arches.json (triangles per group/LOD, colliders, light, dimensions) here and next to the models.

Coordinates are Unity metres LOCAL to one arch: origin at world (48.0, 0, zc) (zc = 0 for arch A, the spawn arch;
12 for arch B), X = depth through the rampart (+X outward, the city is at -X), Y up, Z along the opening. The two Meshy
arches are identical (measure_opening.py -> opening.json): a 2.1 m arch wall (x -0.95..0.95 tunnel, chamfered
reveals to +-1.1) with a 4.93 m opening (jambs z +-2.465), vertical jambs to y ~5.0 and a basket head, crown y 6.74.

What is built (inside the tunnel, set back 1.6 m from the arch wall's city face so the arch gets a shadowed passage):
  * two steel-faced timber leaves per arch, closed: vertical boards on a riveted steel skin, framed, ledged and
    braced on the city face, steel shoe, kick plates and meeting-edge cover strip, strap hinges on pintles let into
    the jambs, cane bolts into the threshold; arch A's south leaf carries a wicket door
  * a timber drop bar across both leaves in steel stirrups, its ends in steel-framed pockets in the jambs
  * a heavy timber transom at the leaf head and a fixed steel grille filling the arch head to the soffit
  * a worn steel threshold plate with a leaf stop, steel stop angles at the jambs
  * wheel guards: dressed guard stones (Ward masonry kit) at the tunnel mouth, steel corner angles with rubber
    buffers on the jamb arrises; a caged bulkhead lamp on the transom (LIGHT_ empty for the Unity spot light)
Groups (Unity sets shadows per group): Leaves (timber, skin, transom, grille: cast), Iron (hardware: no shadow),
Stone (guard stones, Masonry Lit: cast), Lamp (no shadow). LOD0 bevelled + bolts, LOD1 single bevels without bolts and
rivets, LOD2 plain blocks. UVs in metres (timber grain along each member's long axis), as the West Gate kit.
"""
import bpy, bmesh, json, math, random, sys
from pathlib import Path
from mathutils import Vector, Matrix

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT = REPO / "unity/AthenHill/Assets/AthenHill/Art/WestGateArches/Models"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(REPO / "art/ward_masonry_kit"))
import ward_masonry as wm  # noqa: E402

OPEN = json.loads((HERE / "opening.json").read_text())["0.0"]
SOFFIT = sorted((float(k), v) for k, v in OPEN["soffit"].items() if abs(float(k)) <= 2.451)

# ------------------------------------------------------------------ dimensions (local metres)
JZ = 2.465          # jamb faces (z = +-JZ)
TUN = 0.95          # tunnel x extent (+-), reveals beyond
X_SKIN = (0.788, 0.800)     # outer steel skin
X_BOARD = (0.705, 0.788)    # boards
X_FRAME = (0.605, 0.705)    # stiles, rails, braces (city side)
X_STRAP = (0.590, 0.605)    # strap hinges, plates on the frame face
LEAF_Y = (0.035, 4.55)
LEAF_Z = (0.012, 2.445)     # +z leaf (the -z leaf mirrors)
STILE_W = 0.20
RAILS = [(0.10, 0.34), (2.18, 2.42), (4.28, 4.50)]     # bottom, lock, top rail (y)
BAR_X, BAR_Y = (0.420, 0.590), (2.440, 2.660)          # drop bar section (in stirrups just above the lock rail)
TRANSOM_Y, TRANSOM_X = (4.58, 4.86), (0.50, 0.80)
GRILLE_X = (0.630, 0.690)
HINGE_Y = [0.22, 2.30, 4.39]
PIN_X = 0.575
WICKET = dict(z=(-1.80, -0.92), y=(0.34, 2.14))       # arch A, -z leaf
THRESH_X = (0.25, 1.00)


def soffit(dz):
    """Arch soffit height at offset dz from the arch centre (piecewise linear over the measured samples)."""
    pts = SOFFIT
    if dz <= pts[0][0]:
        return pts[0][1]
    for (z0, y0), (z1, y1) in zip(pts, pts[1:]):
        if z0 <= dz <= z1:
            return y0 + (y1 - y0) * (dz - z0) / (z1 - z0)
    return pts[-1][1]


# ------------------------------------------------------------------ mesh accumulator (Unity coordinates)
class Acc:
    """Collects elements in Unity coordinates; each element is built in its own frame (bevel, metre UVs with the
    grain along the element's long axis), then copied in."""

    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")
        self.mats = []

    def mi(self, m):
        if m not in self.mats:
            self.mats.append(m)
        return self.mats.index(m)

    def _copy(self, tmp, R, c, mat, smooth=True):
        uvt = tmp.loops.layers.uv.active
        vmap = {}
        for v in tmp.verts:
            vmap[v] = self.bm.verts.new(R @ v.co + c)
        idx = self.mi(mat)
        for f in tmp.faces:
            try:
                nf = self.bm.faces.new([vmap[v] for v in f.verts])
            except ValueError:
                continue
            nf.material_index = idx
            nf.smooth = smooth
            for lo, ln in zip(f.loops, nf.loops):
                ln[self.uv].uv = lo[uvt].uv
        tmp.free()

    def box(self, c, size, mat, R=None, bevel=0.0, segs=1, grain=None, off=None, rnd=None, smooth=True):
        """Box of `size` (sx, sy, sz) centred at c, rotated by R (3x3, Unity frame). grain: local axis index for
        the texture V direction (default: the longest)."""
        R = R if R is not None else Matrix.Identity(3)
        tmp = bmesh.new()
        bmesh.ops.create_cube(tmp, size=1.0)
        for v in tmp.verts:
            v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
        if bevel > 0:
            b = min(bevel, min(size) * 0.45)
            bmesh.ops.bevel(tmp, geom=list(tmp.edges), offset=b, offset_type="OFFSET", segments=segs, profile=0.5,
                            affect="EDGES", clamp_overlap=True)
        uvl = tmp.loops.layers.uv.new("UVMap")
        g = grain if grain is not None else max(range(3), key=lambda i: size[i])
        r = rnd or random
        o = off if off is not None else (r.random() * 6, r.random() * 6)
        tmp.normal_update()
        for f in tmp.faces:
            n = f.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            plane = [i for i in range(3) if i != ax]
            va = g if g in plane else max(plane, key=lambda i: size[i])
            ua = [i for i in plane if i != va][0]
            s = 1.0 if n[ax] > 0 else -1.0
            for lo in f.loops:
                co = lo.vert.co
                lo[uvl].uv = (co[ua] * s * (1 if ax != 1 else 1) + o[0], co[va] + o[1])
        self._copy(tmp, R, Vector(c), mat, smooth)

    def beam(self, a, b, w, d, mat, normal=(1, 0, 0), bevel=0.0, segs=1, rnd=None):
        """Member from a to b (Unity points); w across (in the plane perpendicular to `normal`), d along `normal`."""
        a, b = Vector(a), Vector(b)
        ax = (b - a)
        L = ax.length
        ez = ax.normalized()
        ex = Vector(normal).normalized()
        ex = (ex - ez * ex.dot(ez)).normalized()
        ey = ez.cross(ex)
        R = Matrix((ex, ey, ez)).transposed()
        self.box((a + b) / 2, (d, w, L), mat, R=R, bevel=bevel, segs=segs, grain=2, rnd=rnd)

    def cyl(self, a, b, r, mat, sides=10, cap=True, r2=None, smooth=True):
        a, b = Vector(a), Vector(b)
        d = b - a
        if d.length < 1e-6:
            return
        dn = d.normalized()
        ref = Vector((0, 1, 0)) if abs(dn.y) < 0.9 else Vector((1, 0, 0))
        s1 = dn.cross(ref).normalized()
        s2 = dn.cross(s1).normalized()
        r2 = r if r2 is None else r2
        tmp = bmesh.new()
        uvl = tmp.loops.layers.uv.new("UVMap")
        ring0 = [tmp.verts.new(a + (s1 * math.cos(t) + s2 * math.sin(t)) * r) for t in [2 * math.pi * i / sides for i in range(sides)]]
        ring1 = [tmp.verts.new(b + (s1 * math.cos(t) + s2 * math.sin(t)) * r2) for t in [2 * math.pi * i / sides for i in range(sides)]]
        fs = []
        for i in range(sides):
            j = (i + 1) % sides
            f = tmp.faces.new([ring0[i], ring0[j], ring1[j], ring1[i]])
            for lo, (u, v) in zip(f.loops, [(i, 0), (i + 1, 0), (i + 1, 1), (i, 1)]):
                lo[uvl].uv = (u * 2 * math.pi * r / sides, v * d.length)
            fs.append(f)
        if cap:
            for ring in (ring0[::-1], ring1):
                f = tmp.faces.new(ring)
                for lo in f.loops:
                    p = lo.vert.co
                    lo[uvl].uv = (p.dot(s1), p.dot(s2))
                fs.append(f)
        bmesh.ops.recalc_face_normals(tmp, faces=fs)
        self._copy(tmp, Matrix.Identity(3), Vector((0, 0, 0)), mat, smooth)

    def bolt(self, p, n, r=0.018, h=0.012, mat="WG_RustSteel", sides=8):
        """Domed bolt head / rivet on a face with outward normal n."""
        p, n = Vector(p), Vector(n).normalized()
        self.cyl(p - n * 0.002, p + n * h * 0.6, r, mat, sides, cap=False)
        self.cyl(p + n * h * 0.6, p + n * h, r, mat, sides, cap=True, r2=r * 0.55)

    def poly_prism(self, outline, x0, x1, mat):
        """Planar polygon (list of (z, y)) extruded along X from x0 to x1 (grilles, bands)."""
        tmp = bmesh.new()
        uvl = tmp.loops.layers.uv.new("UVMap")
        a = [tmp.verts.new((x0, y, z)) for z, y in outline]
        b = [tmp.verts.new((x1, y, z)) for z, y in outline]
        fs = [tmp.faces.new(a[::-1]), tmp.faces.new(b)]
        n = len(outline)
        for i in range(n):
            j = (i + 1) % n
            fs.append(tmp.faces.new([a[i], a[j], b[j], b[i]]))
        bmesh.ops.recalc_face_normals(tmp, faces=fs)
        for f in fs:
            for lo in f.loops:
                co = lo.vert.co
                lo[uvl].uv = (co.z + co.x, co.y)
        self._copy(tmp, Matrix.Identity(3), Vector((0, 0, 0)), mat)

    def build(self, coll, weighted=True, sharp=35):
        if not self.bm.faces:
            self.bm.free()
            return None
        for v in self.bm.verts:
            v.co = wm.U(v.co)
        bmesh.ops.reverse_faces(self.bm, faces=self.bm.faces[:])
        me = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(me)
        self.bm.free()
        for m in self.mats:
            me.materials.append(wm.material(m))
        ob = bpy.data.objects.new(self.name, me)
        coll.objects.link(ob)
        me.set_sharp_from_angle(angle=math.radians(sharp))
        if weighted:
            bpy.context.view_layer.objects.active = ob
            for o in bpy.context.selected_objects:
                o.select_set(False)
            ob.select_set(True)
            wn = ob.modifiers.new("wn", "WEIGHTED_NORMAL")
            wn.keep_sharp = True
            wn.mode = "FACE_AREA"
            bpy.ops.object.modifier_apply(modifier="wn")
        wm.triangulate(ob)
        return ob


def mirror_z(p, s):
    return (p[0], p[1], p[2] * s)


# ------------------------------------------------------------------ the gate
def build_gate(key, lod, coll):
    rnd = random.Random(f"{key}-boards")
    hw = random.Random(f"{key}-hw")
    leaves = Acc(f"WGA_Gate{key}_Leaves_LOD{lod}")
    iron = Acc(f"WGA_Gate{key}_Iron_LOD{lod}")
    lamp = Acc(f"WGA_Gate{key}_Lamp_LOD{lod}")
    bev = {0: 1.0, 1: 0.8, 2: 0.0}[lod]
    seg = 2 if lod == 0 else 1
    bolts = lod == 0

    for s in (1, -1):                 # +z leaf, -z leaf (the -z leaf of arch A has the wicket)
        wicket = key == "A" and s == -1
        z0, z1 = LEAF_Z
        def Z(z):
            return z * s
        # ---- steel skin (outer face) and boards
        leaves.box((sum(X_SKIN) / 2, sum(LEAF_Y) / 2, Z((z0 + z1) / 2)), (X_SKIN[1] - X_SKIN[0], LEAF_Y[1] - LEAF_Y[0], z1 - z0),
                   "WG_PlateSteel", bevel=0.003 * bev, rnd=rnd)
        if lod < 2:
            # riveted seam straps on the outer skin (plates ~1.2 m high, two across the leaf)
            for ys in (1.17, 2.34, 3.51):
                iron.box((X_SKIN[1] + 0.005, ys, Z((z0 + z1) / 2)), (0.010, 0.09, z1 - z0 - 0.02), "WG_PlateSteel", bevel=0.002 * bev, rnd=hw)
            iron.box((X_SKIN[1] + 0.005, sum(LEAF_Y) / 2, Z((z0 + z1) / 2)), (0.010, LEAF_Y[1] - LEAF_Y[0] - 0.04, 0.09), "WG_PlateSteel",
                     bevel=0.002 * bev, rnd=hw)
        if lod == 2:
            leaves.box((sum(X_BOARD) / 2, sum(LEAF_Y) / 2, Z((z0 + z1) / 2)), (X_BOARD[1] - X_BOARD[0], LEAF_Y[1] - LEAF_Y[0], z1 - z0),
                       "TR_Timber", grain=1, rnd=rnd)
        else:
            z = z0
            bi = 0
            while z < z1 - 0.05:
                w = min(rnd.uniform(0.21, 0.29), z1 - z)
                if z1 - (z + w) < 0.12:
                    w = z1 - z
                fresh = (key, s, bi) in (("A", 1, 6), ("A", -1, 2), ("B", 1, 3), ("B", -1, 7), ("B", -1, 8))
                matb = "TR_TimberFresh" if fresh else ("TR_TimberDark" if rnd.random() < 0.12 else "TR_Timber")
                zc_ = z + w / 2
                gap = 0.004
                ylo = LEAF_Y[0] + rnd.uniform(0.0, 0.025)      # ragged, worn board feet behind the shoe
                yhi = LEAF_Y[1] - rnd.uniform(0.0, 0.012)
                cup = rnd.uniform(-0.004, 0.004)
                segs_y = [(ylo, yhi)]
                # the wicket cuts the boards it crosses (its own boards are built below)
                zw0, zw1 = WICKET["z"]
                if wicket and (zw0 - 0.08) < Z(zc_) < (zw1 + 0.08):
                    segs_y = [(ylo, WICKET["y"][0]), (WICKET["y"][1] + 0.04, yhi)]
                for ya, yb in segs_y:
                    leaves.box((sum(X_BOARD) / 2 + cup, (ya + yb) / 2, Z(zc_)), (X_BOARD[1] - X_BOARD[0], yb - ya, w - gap),
                               matb, bevel=0.006 * bev, segs=seg, grain=1, rnd=rnd)
                z += w
                bi += 1
        # ---- frame: stiles, rails, braces (city face)
        fx = (sum(X_FRAME) / 2, X_FRAME[1] - X_FRAME[0])
        hinge_z = (z1 - STILE_W / 2)
        meet_z = (z0 + STILE_W / 2)
        for zc_ in (hinge_z, meet_z):
            leaves.box((fx[0], (RAILS[0][0] + RAILS[2][1]) / 2, Z(zc_)), (fx[1], RAILS[2][1] - RAILS[0][0], STILE_W),
                       "TR_TimberDark", bevel=0.012 * bev, segs=seg, grain=1, rnd=rnd)
        for ya, yb in RAILS:
            leaves.box((fx[0], (ya + yb) / 2, Z((z0 + z1) / 2)), (fx[1] - 0.004, yb - ya, z1 - z0 - 2 * STILE_W + 0.02),
                       "TR_TimberDark", bevel=0.012 * bev, segs=seg, grain=2, rnd=rnd)
        # braces rise from the hinge side (compression struts); the wicket leaf keeps only the upper one
        panels = [(RAILS[0][1], RAILS[1][0]), (RAILS[1][1], RAILS[2][0])]
        for pi_, (ya, yb) in enumerate(panels):
            if wicket and pi_ == 0:
                continue
            a = (fx[0] + 0.004, ya + 0.10, Z(z1 - STILE_W - 0.02))
            b = (fx[0] + 0.004, yb - 0.10, Z(z0 + STILE_W + 0.02))
            leaves.beam(a, b, 0.17, fx[1] - 0.012, "TR_TimberDark", normal=(1, 0, 0), bevel=0.010 * bev, segs=seg, rnd=rnd)
        # wicket: frame posts, its own boards, ledges and brace
        if wicket:
            zw0, zw1 = WICKET["z"]
            yw0, yw1 = WICKET["y"]
            for zp in (zw0 - 0.045, zw1 + 0.045):
                leaves.box((fx[0], (yw0 + RAILS[1][0]) / 2, zp), (fx[1], RAILS[1][0] - yw0, 0.09), "TR_TimberDark",
                           bevel=0.010 * bev, segs=seg, grain=1, rnd=rnd)
            leaves.box((fx[0], yw1 + 0.02, (zw0 + zw1) / 2), (fx[1], 0.04, zw1 - zw0), "TR_TimberDark", bevel=0.006 * bev, rnd=rnd)
            dz = zw1 - zw0 - 0.012
            if lod == 2:
                leaves.box((sum(X_BOARD) / 2 - 0.01, (yw0 + yw1) / 2, (zw0 + zw1) / 2), (X_BOARD[1] - X_BOARD[0], yw1 - yw0 - 0.01, dz),
                           "TR_Timber", grain=1, rnd=rnd)
            else:
                nb = 4
                for k in range(nb):
                    zb = zw0 + 0.006 + dz * (k + 0.5) / nb
                    leaves.box((sum(X_BOARD) / 2 - 0.012, (yw0 + yw1) / 2 + 0.003, zb), (X_BOARD[1] - X_BOARD[0], yw1 - yw0 - 0.014, dz / nb - 0.004),
                               "TR_TimberFresh" if k == 2 else "TR_Timber", bevel=0.005 * bev, segs=seg, grain=1, rnd=rnd)
            wx = (X_BOARD[0] - 0.012 - 0.035, 0.07)
            for yl in (yw0 + 0.12, (yw0 + yw1) / 2, yw1 - 0.13):
                leaves.box((wx[0], yl, (zw0 + zw1) / 2), (wx[1], 0.13, dz - 0.04), "TR_TimberDark", bevel=0.008 * bev, segs=seg, grain=2, rnd=rnd)
            leaves.beam((wx[0] + 0.004, yw0 + 0.20, zw0 + 0.10), (wx[0] + 0.004, (yw0 + yw1) / 2 - 0.08, zw1 - 0.10), 0.11, wx[1] - 0.012,
                        "TR_TimberDark", bevel=0.008 * bev, segs=seg, rnd=rnd)
            leaves.beam((wx[0] + 0.004, (yw0 + yw1) / 2 + 0.08, zw0 + 0.10), (wx[0] + 0.004, yw1 - 0.21, zw1 - 0.10), 0.11, wx[1] - 0.012,
                        "TR_TimberDark", bevel=0.008 * bev, segs=seg, rnd=rnd)

        # ---- steel: shoe, kick plates, cover strip, straps, corner plates, cane bolt
        iron.box(((X_FRAME[0] + X_SKIN[1]) / 2, 0.075, Z((z0 + z1) / 2)), (X_SKIN[1] - X_FRAME[0] + 0.012, 0.08, z1 - z0),
                 "WG_RustSteel", bevel=0.004 * bev, rnd=hw)     # steel shoe (channel) along the leaf foot
        iron.box((X_FRAME[0] - 0.013, 0.04, Z((z0 + z1) / 2)), (0.008, 0.055, z1 - z0 - 0.02), "WG_Rubber", rnd=hw)   # sand sweep
        kick = [(z0 + STILE_W, z1 - STILE_W)]
        if wicket:
            zw0, zw1 = WICKET["z"]
            kick = [(z0 + STILE_W, -zw1 - 0.09), (-zw0 + 0.09, z1 - STILE_W)]
        for ka, kb in kick:
            if kb - ka < 0.1:
                continue
            iron.box((X_BOARD[0] - 0.005, 0.64, Z((ka + kb) / 2)), (0.010, 0.60, kb - ka), "WG_PlateSteel", bevel=0.002 * bev, rnd=hw)
            if bolts:
                for zz in [ka + 0.05 + i * 0.12 for i in range(int((kb - ka - 0.1) / 0.12) + 1)]:
                    for yy in (0.375, 0.905):
                        iron.bolt((X_BOARD[0] - 0.010, yy, Z(zz)), (-1, 0, 0), r=0.011, h=0.008)
        if wicket:
            zw0, zw1 = WICKET["z"]
            iron.box((X_BOARD[0] - 0.024, 0.62, (zw0 + zw1) / 2), (0.008, 0.50, zw1 - zw0 - 0.06), "WG_PlateSteel", bevel=0.002 * bev, rnd=hw)
        if s == 1:      # cover strip on the meeting edge (the +z leaf closes last)
            iron.box((X_STRAP[0] - 0.0075, (RAILS[0][0] + RAILS[2][1]) / 2, 0.035), (0.015, RAILS[2][1] - RAILS[0][0] - 0.02, 0.11),
                     "WG_RustSteel", bevel=0.003 * bev, rnd=hw)
            if bolts:
                for yy in [0.2 + i * 0.25 for i in range(17)]:
                    if not (BAR_Y[0] - 0.02 < yy < BAR_Y[1] + 0.02):
                        iron.bolt((X_STRAP[0] - 0.015, yy, 0.035), (-1, 0, 0), r=0.012, h=0.009)
        # strap hinges: tapered straps along the rails from the knuckle at the pintle
        for yh in HINGE_Y:
            L = 1.85
            zk = JZ - 0.065
            n_seg = 6 if lod < 2 else 1
            for k in range(n_seg):
                za = zk - L * k / n_seg
                zb = zk - L * (k + 1) / n_seg
                wa = 0.11 - 0.035 * k / n_seg
                iron.box((sum(X_STRAP) / 2, yh, Z((za + zb) / 2)), (X_STRAP[1] - X_STRAP[0], wa, abs(za - zb) + 0.002), "WG_RustSteel",
                         bevel=0.003 * bev, rnd=hw)
            if lod == 2:
                continue
            iron.cyl((PIN_X, yh - 0.055, Z(zk)), (PIN_X, yh + 0.055, Z(zk)), 0.042, "WG_RustSteel", 12 if lod == 0 else 8)
            iron.box((PIN_X + 0.02, yh, Z(zk - 0.05)), (0.05, 0.10, 0.06), "WG_RustSteel", bevel=0.003 * bev, rnd=hw)
            if bolts:
                for k in range(7):
                    iron.bolt((X_STRAP[0], yh + (0.025 if k % 2 else -0.025), Z(zk - 0.20 - k * 0.24)), (-1, 0, 0), r=0.015, h=0.011)
            # pintle let into the jamb: pin below the knuckle, tang into the stone, lead-run patch on the jamb face
            iron.cyl((PIN_X, yh - 0.13, Z(zk)), (PIN_X, yh + 0.06, Z(zk)), 0.024, "WG_RustSteel", 8)
            iron.box((PIN_X, yh - 0.10, Z((zk + JZ + 0.06) / 2)), (0.06, 0.05, JZ + 0.06 - zk), "WG_RustSteel", bevel=0.002 * bev, rnd=hw)
            iron.box((PIN_X, yh - 0.10, Z(JZ - 0.002)), (0.13, 0.12, 0.012), "VH_Dark", bevel=0.003 * bev, rnd=hw)
        # corner plates at the meeting-side rail junctions
        for ya, yb in RAILS:
            yc = (ya + yb) / 2
            iron.box((X_STRAP[0] + 0.0075, yc, Z(z0 + STILE_W * 0.75)), (0.012, (yb - ya) + 0.08, STILE_W * 1.4), "WG_RustSteel",
                     bevel=0.003 * bev, rnd=hw)
            if bolts:
                for dy in (-(yb - ya) / 2 + 0.02, (yb - ya) / 2 - 0.02):
                    for dzz in (0.06, 0.22):
                        iron.bolt((X_STRAP[0] - 0.003, yc + dy, Z(z0 + dzz)), (-1, 0, 0), r=0.013, h=0.009)
        if lod == 2:
            continue
        # cane bolt on the meeting stile into the threshold
        cz = Z(z0 + 0.10)
        iron.cyl((X_STRAP[0] - 0.03, 0.03, cz), (X_STRAP[0] - 0.03, 0.98, cz), 0.016, "WG_RustSteel", 8)
        iron.cyl((X_STRAP[0] - 0.03, 0.98, cz), (X_STRAP[0] - 0.18, 0.98, cz), 0.014, "WG_RustSteel", 8)
        for yg in (0.32, 0.78):
            iron.box((X_STRAP[0] - 0.02, yg, cz), (0.05, 0.05, 0.07), "WG_RustSteel", bevel=0.003 * bev, rnd=hw)
        # bar stirrups (two per leaf): U straps sitting on the lock rail, back plates bolted through the boards
        for zs in (0.45, 1.75):
            xa, xb = BAR_X[0] - 0.016, X_BOARD[0]
            iron.box(((xa + xb) / 2, BAR_Y[0] - 0.008, Z(zs)), (xb - xa, 0.016, 0.07), "WG_RustSteel", bevel=0.003 * bev, rnd=hw)
            iron.box((BAR_X[0] - 0.008, (BAR_Y[0] + BAR_Y[1] + 0.06) / 2 - 0.008, Z(zs)), (0.016, BAR_Y[1] - BAR_Y[0] + 0.06, 0.07),
                     "WG_RustSteel", bevel=0.003 * bev, rnd=hw)
            iron.box((X_BOARD[0] - 0.0075, (RAILS[1][1] + BAR_Y[1] + 0.14) / 2, Z(zs)), (0.015, BAR_Y[1] + 0.14 - RAILS[1][1], 0.13),
                     "WG_RustSteel", bevel=0.003 * bev, rnd=hw)
            if bolts:
                iron.bolt((X_BOARD[0] - 0.015, BAR_Y[1] + 0.08, Z(zs)), (-1, 0, 0), r=0.017, h=0.012)
        # wicket hardware
        if wicket:
            zw0, zw1 = WICKET["z"]
            yw0, yw1 = WICKET["y"]
            wf = X_BOARD[0] - 0.012 - 0.07         # wicket ledge face
            for yh in (yw0 + 0.12, yw1 - 0.13):
                iron.box((wf - 0.006, yh, zw0 + 0.30), (0.012, 0.075, 0.58), "WG_RustSteel", bevel=0.002 * bev, rnd=hw)
                iron.cyl((wf - 0.02, yh - 0.04, zw0 - 0.02), (wf - 0.02, yh + 0.04, zw0 - 0.02), 0.022, "WG_RustSteel", 8)
                if bolts:
                    for k in range(3):
                        iron.bolt((wf - 0.012, yh, zw0 + 0.10 + k * 0.18), (-1, 0, 0), r=0.011, h=0.008)
            # ring pull, latch keeper, slide bolt, vision hatch
            iron.box((wf - 0.006, 1.10, zw1 - 0.12), (0.012, 0.16, 0.10), "WG_RustSteel", bevel=0.002 * bev, rnd=hw)
            ring_c = Vector((wf - 0.03, 1.02, zw1 - 0.12))
            for k in range(10 if lod == 0 else 6):
                t0 = 2 * math.pi * k / (10 if lod == 0 else 6)
                t1 = 2 * math.pi * (k + 1) / (10 if lod == 0 else 6)
                iron.cyl(ring_c + Vector((0, math.cos(t0) * 0.07, math.sin(t0) * 0.07)), ring_c + Vector((0, math.cos(t1) * 0.07, math.sin(t1) * 0.07)),
                         0.009, "WG_RustSteel", 6)
            iron.box((wf - 0.01, 1.42, zw1 - 0.05), (0.02, 0.05, 0.22), "WG_RustSteel", bevel=0.003 * bev, rnd=hw)
            iron.box((wf - 0.006, 1.42, zw1 + 0.06), (0.012, 0.09, 0.06), "WG_RustSteel", bevel=0.002 * bev, rnd=hw)
            iron.box((wf - 0.008, 1.66, (zw0 + zw1) / 2), (0.016, 0.16, 0.26), "WG_PlateSteel", bevel=0.003 * bev, rnd=hw)
            iron.box((wf - 0.018, 1.66, (zw0 + zw1) / 2), (0.006, 0.035, 0.18), "VH_Dark", rnd=hw)
        # arch B: riveted repair plate over old shell damage (+z leaf, upper panel)
        if key == "B" and s == 1:
            R = Matrix.Rotation(math.radians(4), 3, "X")
            iron.box((X_FRAME[0] + 0.03, 3.25, 1.25), (0.012, 0.72, 0.86), "WG_PlateSteel", R=R, bevel=0.003 * bev, rnd=hw)
            if bolts:
                for k in range(8):
                    a = 2 * math.pi * k / 8
                    iron.bolt((X_FRAME[0] + 0.024, 3.25 + math.sin(a) * 0.31, 1.25 + math.cos(a) * 0.38), (-1, 0, 0), r=0.012, h=0.009)

    # ---- drop bar (both leaves), jamb pockets
    bx = (sum(BAR_X) / 2, BAR_X[1] - BAR_X[0])
    by = (sum(BAR_Y) / 2, BAR_Y[1] - BAR_Y[0])
    leaves.box((bx[0], by[0], 0), (bx[1], by[1], 2 * JZ + 0.10), "TR_TimberDark", bevel=0.014 * bev, segs=seg, grain=2, rnd=rnd)
    for s in (1, -1):
        iron.box((bx[0], by[0], s * (JZ - 0.10)), (bx[1] + 0.012, by[1] + 0.012, 0.14), "WG_RustSteel", bevel=0.003 * bev, rnd=hw)
        # lifting handle on the bar front
        hz = s * 1.10
        iron.cyl((BAR_X[0] - 0.003, by[0], hz - 0.12), (BAR_X[0] - 0.07, by[0], hz - 0.12), 0.012, "WG_RustSteel", 8)
        iron.cyl((BAR_X[0] - 0.003, by[0], hz + 0.12), (BAR_X[0] - 0.07, by[0], hz + 0.12), 0.012, "WG_RustSteel", 8)
        iron.cyl((BAR_X[0] - 0.07, by[0], hz - 0.12), (BAR_X[0] - 0.07, by[0], hz + 0.12), 0.013, "WG_RustSteel", 8)
        # pocket frame let into the jamb around the bar end
        zf = s * (JZ - 0.006)
        for (cx, cy, sx, sy) in [(bx[0], BAR_Y[1] + 0.035, bx[1] + 0.12, 0.05), (bx[0], BAR_Y[0] - 0.035, bx[1] + 0.12, 0.05),
                                 (BAR_X[0] - 0.035, by[0], 0.05, by[1] + 0.02), (BAR_X[1] + 0.035, by[0], 0.05, by[1] + 0.02)]:
            iron.box((cx, cy, zf), (sx, sy, 0.016), "WG_RustSteel", bevel=0.003 * bev, rnd=hw)
        if bolts:
            for (cx, cy) in [(BAR_X[0] - 0.035, BAR_Y[1] + 0.035), (BAR_X[1] + 0.035, BAR_Y[1] + 0.035),
                             (BAR_X[0] - 0.035, BAR_Y[0] - 0.035), (BAR_X[1] + 0.035, BAR_Y[0] - 0.035)]:
                iron.bolt((cx, cy, s * (JZ - 0.014)), (0, 0, -s), r=0.014, h=0.010)

    # ---- transom and head grille
    leaves.box((sum(TRANSOM_X) / 2, sum(TRANSOM_Y) / 2, 0), (TRANSOM_X[1] - TRANSOM_X[0], TRANSOM_Y[1] - TRANSOM_Y[0], 2 * JZ + 0.06),
               "TR_TimberDark", bevel=0.016 * bev, segs=seg, grain=2, rnd=rnd)
    iron.box((TRANSOM_X[0] - 0.006, TRANSOM_Y[0] + 0.03, 0), (0.012, 0.06, 2 * JZ - 0.02), "WG_RustSteel", bevel=0.002 * bev, rnd=hw)
    gy0 = TRANSOM_Y[1]
    # band following the soffit (flat bar, 3 cm inside the measured soffit)
    pts = [(dz, soffit(dz) - 0.03) for dz in [x * 0.05 for x in range(-48, 49)] if soffit(dz) - 0.03 > gy0 + 0.02]
    band_w = 0.07
    if lod < 2:
        outline = [(z, y) for z, y in pts] + [(z, y - band_w) for z, y in reversed(pts)]
        # clip the band's lower ends to the transom top
        outline = [(z, max(y, gy0)) for z, y in outline]
        leaves.poly_prism(outline, GRILLE_X[0] - 0.005, GRILLE_X[1] + 0.005, "WG_RustSteel")
    else:
        leaves.box((sum(GRILLE_X) / 2, soffit(0) - 0.065, 0), (GRILLE_X[1] - GRILLE_X[0], 0.07, 2.2), "WG_RustSteel")
    pitch = 0.17
    nbar = int((2 * JZ - 0.1) / pitch)
    for k in range(nbar + 1):
        dz = -JZ + 0.05 + k * (2 * JZ - 0.1) / nbar
        top = soffit(dz) - 0.03 - (band_w * 0.5 if lod < 2 else 0.0)
        if top - gy0 < 0.06:
            continue
        if lod == 2 and k % 2:
            continue
        leaves.box((sum(GRILLE_X) / 2, (gy0 + top) / 2, dz), (GRILLE_X[1] - GRILLE_X[0], top - gy0, 0.024), "WG_RustSteel",
                   bevel=0.003 * bev, grain=1, rnd=hw)
    for yt in (5.45, 6.12):
        # horizontal ties, clipped to the soffit band
        span = [dz for dz in [x * 0.01 for x in range(-247, 248)] if soffit(dz) - 0.03 - band_w > yt + 0.03]
        if span:
            za, zb = min(span), max(span)
            leaves.box((GRILLE_X[0] - 0.012, yt, (za + zb) / 2), (0.024, 0.06, zb - za), "WG_RustSteel", bevel=0.003 * bev, rnd=hw)
            if bolts:
                for k in range(nbar + 1):
                    dz = -JZ + 0.05 + k * (2 * JZ - 0.1) / nbar
                    if za + 0.02 < dz < zb - 0.02:
                        iron.bolt((GRILLE_X[0] - 0.024, yt, dz), (-1, 0, 0), r=0.011, h=0.007)

    # ---- stops, threshold
    for s in (1, -1):
        iron.box((0.85, (0.0 + TRANSOM_Y[0]) / 2, s * (JZ - 0.03)), (0.10, TRANSOM_Y[0], 0.06), "WG_RustSteel", bevel=0.003 * bev, rnd=hw)
        iron.box((0.815, 1.6, s * (JZ - 0.065)), (0.03, 0.30, 0.03), "WG_Rubber", bevel=0.004 * bev, rnd=hw)   # leaf buffer
    tx = (sum(THRESH_X) / 2, THRESH_X[1] - THRESH_X[0])
    nplates = 3
    for k in range(nplates):
        za = -JZ + 0.005 + k * (2 * JZ - 0.01) / nplates
        zb = za + (2 * JZ - 0.01) / nplates - 0.006
        iron.box((tx[0], 0.006, (za + zb) / 2), (tx[1], 0.014, zb - za), "WG_PlateSteel", bevel=0.003 * bev, grain=2, rnd=hw)
        if bolts:
            for zz in [za + 0.08 + i * 0.30 for i in range(int((zb - za - 0.16) / 0.30) + 1)]:
                for xx in (THRESH_X[0] + 0.05, THRESH_X[1] - 0.05):
                    iron.cyl((xx, 0.012, zz), (xx, 0.016, zz), 0.016, "WG_RustSteel", 8)
    iron.box((0.82, 0.026, 0), (0.04, 0.03, 2 * JZ - 0.02), "WG_RustSteel", bevel=0.004 * bev, rnd=hw)     # leaf stop bar
    for s in (1, -1):
        iron.cyl((X_STRAP[0] - 0.03, 0.0145, s * (LEAF_Z[0] + 0.10)), (X_STRAP[0] - 0.03, 0.0155, s * (LEAF_Z[0] + 0.10)), 0.026, "VH_Dark", 10)

    # ---- tunnel-mouth corner guards: steel angles with a rubber buffer on the jamb arrises
    for s in (1, -1):
        zc_ = s * JZ
        # the arris is rounded (r ~0.15) between the jamb (x -0.97) and the wall face (x -1.12): one leg on the jamb,
        # one across the round to the face
        iron.box((-0.92, 1.10, zc_ - s * 0.005), (0.10, 0.90, 0.010), "WG_RustSteel", bevel=0.002 * bev, rnd=hw)
        iron.box((-0.992, 1.10, zc_ + s * 0.040), (0.010, 0.90, 0.09), "WG_RustSteel", bevel=0.002 * bev, rnd=hw)
        iron.box((-0.92, 0.92, zc_ - s * 0.045), (0.07, 0.30, 0.08), "WG_Rubber", bevel=0.01 * bev, segs=seg, rnd=hw)
        if bolts:
            for yy in (0.72, 1.20, 1.48):
                iron.bolt((-0.90, yy, zc_ - s * 0.010), (0, 0, -s), r=0.013, h=0.009)
                iron.bolt((-0.997, yy, zc_ + s * 0.050), (-1, 0, 0), r=0.013, h=0.009)

    # ---- bulkhead lamp on the transom, conduit to the south jamb
    lx = TRANSOM_X[0] - 0.07
    lamp.box((lx, TRANSOM_Y[0] + 0.10, 0), (0.14, 0.17, 0.26), "VH_Steel", bevel=0.012 * bev, segs=seg, rnd=hw)
    lamp.box((lx - 0.02, TRANSOM_Y[0] - 0.005, 0), (0.10, 0.04, 0.20), "VH_LampLens", bevel=0.006 * bev, rnd=hw)
    if lod < 2:
        for dz in (-0.07, 0.0, 0.07):
            lamp.box((lx - 0.02, TRANSOM_Y[0] - 0.03, dz), (0.11, 0.012, 0.012), "VH_Steel", rnd=hw)
        lamp.box((lx - 0.02, TRANSOM_Y[0] - 0.03, 0), (0.012, 0.012, 0.21), "VH_Steel", rnd=hw)
        iron.cyl((TRANSOM_X[0] - 0.02, TRANSOM_Y[1] + 0.02, -0.12), (TRANSOM_X[0] - 0.02, TRANSOM_Y[1] + 0.02, -JZ + 0.04), 0.012, "WG_RustSteel", 8)
        iron.cyl((TRANSOM_X[0] - 0.02, TRANSOM_Y[1] + 0.02, -JZ + 0.04), (TRANSOM_X[0] - 0.02, 3.4, -JZ + 0.04), 0.012, "WG_RustSteel", 8)
        iron.cyl((lx, TRANSOM_Y[0] + 0.19, -0.12), (TRANSOM_X[0] - 0.02, TRANSOM_Y[1] + 0.02, -0.12), 0.012, "WG_RustSteel", 8)
        iron.box((TRANSOM_X[0] - 0.02, 3.3, -JZ + 0.06), (0.10, 0.18, 0.12), "WG_RustSteel", bevel=0.006 * bev, rnd=hw)
    out = [a.build(coll) for a in (leaves, iron, lamp)]
    return [o for o in out if o]


# ------------------------------------------------------------------ guard stones (Ward masonry kit)
GUARD = dict(x=(-1.48, -1.06), z_in=2.18, z_out=2.62, h=0.66)


def guard_stones(key, lod, coll):
    wm.set_state(lod, random.Random(f"{key}-guard"), f"wga{key}")
    wm.reset_materials()
    part = wm.Part(f"WGA_Gate{key}_Stone_LOD{lod}")
    for s in (1, -1):
        x0, x1 = GUARD["x"]
        za, zb = s * GUARD["z_in"], s * GUARD["z_out"]
        z0, z1 = min(za, zb), max(za, zb)
        h = GUARD["h"]
        v = random.Random(f"{key}{s}-tint").uniform(0.94, 1.04)
        tint = (0.5 * v * 1.03, 0.5 * v, 0.5 * v * 0.93)      # warm sandstone (the kit's random tint can drift cool)
        bid = part.new_block(tint=tint, erode=0.012 if lod == 0 else 0.0)
        # tapered block: the street faces lean back, the top is a low pyramid (wheels ride off it)
        ix, iz = 0.07, 0.06
        bot = [(x0, 0.0, z0), (x1, 0.0, z0), (x1, 0.0, z1), (x0, 0.0, z1)]
        # the street face (toward the arch centre) and the city face lean back (batter); the wall side stays plumb
        top = [(x0 + ix, h, z0 + (iz if s > 0 else 0.0)), (x1, h, z0 + (iz if s > 0 else 0.0)),
               (x1, h, z1 - (iz if s < 0 else 0.0)), (x0 + ix, h, z1 - (iz if s < 0 else 0.0))]
        vs, faces = part.hexa(bot + top, "VH_Ashlar", bid, skip=("bottom",))
        cap_c = Vector(((x0 + ix + x1) / 2, h + 0.09, (z0 + z1) / 2))
        ring = [vs[4], vs[5], vs[6], vs[7]]
        apex = part.bm.verts.new(cap_c)
        tf = faces.get("top")
        if tf is not None:
            part.bm.faces.remove(tf)
        idx = part.mi("VH_Ashlar")
        for i in range(4):
            f = part.bm.faces.new([ring[i], ring[(i + 1) % 4], apex])
            f.material_index = idx
            f[part.blk] = bid
        bmesh.ops.recalc_face_normals(part.bm, faces=list({f for v in vs for f in v.link_faces}))
        edges = [e for e in part.bm.edges if (e.verts[0] in vs or e.verts[0] is apex) and (e.verts[1] in vs or e.verts[1] is apex)
                 and not (e.verts[0].co.y < 0.01 and e.verts[1].co.y < 0.01)]
        part.bevel_edges(edges, 0.035 if lod == 0 else 0.025, 3 if lod == 0 else 1)
    wm.finalize_parts([part])
    ao = wm.AOBaker([part], ground_y=0.0, samples=16)
    ob = part.build(coll, ao=ao, ground_y=0.0, macro=0.0)   # no broad 2-4 m drift on two 0.4 m stones
    # steel wear band round the street faces (separate, Iron materials)
    band = Acc(f"WGA_Gate{key}_StoneBand_LOD{lod}")
    for s in (1, -1):
        x0, x1 = GUARD["x"]
        zi = s * GUARD["z_in"]
        yb = 0.42
        lean = yb / GUARD["h"]
        band.box((x0 + 0.07 * lean - 0.004, yb, s * (GUARD["z_in"] + GUARD["z_out"]) / 2), (0.012, 0.06, GUARD["z_out"] - GUARD["z_in"] - 0.03),
                 "WG_RustSteel", bevel=0.002 if lod < 2 else 0.0)
        band.box(((x0 + x1) / 2 + 0.03, yb, zi + s * (0.06 * lean - 0.004)), (x1 - x0 - 0.06, 0.06, 0.012), "WG_RustSteel",
                 bevel=0.002 if lod < 2 else 0.0)
        if lod == 0:
            for xx in (x0 + 0.12, x1 - 0.10):
                band.bolt((xx, yb, zi + s * (0.06 * lean - 0.010)), (0, 0, -s), r=0.012, h=0.008)
    return [ob, band.build(coll)]


# ------------------------------------------------------------------ colliders, light, export
def col_box(coll, name, c, size):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = wm.U(Vector((c[0] + v.co.x * size[0], c[1] + v.co.y * size[1], c[2] + v.co.z * size[2])))
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(wm.material("WG_Collider"))
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def empty(coll, name, pos):
    e = bpy.data.objects.new(name, None)
    e.location = wm.U(Vector(pos))
    coll.objects.link(e)
    return e


def tris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons) if ob and ob.type == "MESH" else 0


def main(keys):
    rec = {}
    for key in keys:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        wm.reset_materials()
        coll = bpy.context.scene.collection
        objs = []
        r = {"lods": {}}
        for lod in (0, 1, 2):
            built = build_gate(key, lod, coll) + guard_stones(key, lod, coll)
            objs += built
            r["lods"][lod] = {o.name: tris(o) for o in built}
            r["lods"][lod]["total"] = sum(tris(o) for o in built)
        # sealing collider: the whole opening at the leaves (bar front to the stop), up to the soffit
        objs.append(col_box(coll, f"COL_WGA_Gate{key}_Leaves", (0.66, 3.45, 0.0), (0.52, 6.9, 2 * JZ + 0.02)))
        for s, n in ((1, "N"), (-1, "S")):
            x0, x1 = GUARD["x"]
            objs.append(col_box(coll, f"COL_WGA_Gate{key}_Guard{n}", ((x0 + x1) / 2, 0.36, s * (GUARD["z_in"] + GUARD["z_out"]) / 2),
                                (x1 - x0, 0.72, GUARD["z_out"] - GUARD["z_in"])))
        objs.append(empty(coll, f"LIGHT_WGA_Gate{key}_Bulkhead", (TRANSOM_X[0] - 0.09, TRANSOM_Y[0] - 0.08, 0.0)))
        objs.append(empty(coll, f"AIM_WGA_Gate{key}_Bulkhead", (-0.8, 0.0, 0.0)))
        path = OUT / f"WGA_Gate{key}.glb"
        wm.export(objs, path)
        r["glb"] = str(path.relative_to(REPO))
        r["colliders"] = [o.name for o in objs if o.name.startswith("COL_")]
        r["light"] = {"pos": [TRANSOM_X[0] - 0.09, TRANSOM_Y[0] - 0.08, 0.0], "aim": [-0.8, 0.0, 0.0]}
        rec[key] = r
        print("exported", key, {k: v["total"] for k, v in r["lods"].items()}, flush=True)
    rec["dims"] = dict(JZ=JZ, tunnel=TUN, skin=X_SKIN, boards=X_BOARD, frame=X_FRAME, leafY=LEAF_Y, leafZ=LEAF_Z, rails=RAILS,
                      bar=[BAR_X, BAR_Y], transom=[TRANSOM_X, TRANSOM_Y], grille=GRILLE_X, threshold=THRESH_X, wicket=WICKET,
                      guard=GUARD, crown=soffit(0.0))
    for p in (HERE / "gate-arches.json", OUT / "gate-arches.json"):
        old = json.loads(p.read_text()) if p.exists() else {}
        old.update(rec)
        p.write_text(json.dumps(old, indent=1))


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    main(args or ["A", "B"])
