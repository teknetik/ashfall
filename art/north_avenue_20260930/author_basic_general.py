"""Basic General: the open market booth rebuilt in Ward stone (Blender 5.2 headless, 30 September 2026).

Carl (30 Sep 2026): "we still need to rebuild. general, salvage, thread and repairs. same stone work, same signage, same
weathering."

The booth keeps its footprint, its six AuthoredWorld colliders, Mira's root (8, 0.5, 15.8), the counter dressing, the
Stock panels, the back panel and the hall-district family sign (back plane at world z 16.863). Only the structure is
new: dressed-ashlar rear wall and cheek walls on the kept collider lines (the rear wall's inner face stays exactly where
the shelves and the back panel touch it, world z 14.0), two new stone front piers with caps, a riveted red steel box
lintel that carries the sign, a stone attic course and coping above it, a corrugated roof falling to a rear gutter and
downpipe, a roll-up security shutter box with guides (the stall closes at night), a stone-slab porch and step matching
the kept colliders, an aquifer service box and conduit on the rear, sheltered sand, runoff, rust and old impacts from the
shared kit (art/ward_masonry_kit).

Coordinates: Unity metres local to the booth root at world (8, 0, 15.1), yaw 0 (front = +Z, towards the avenue), paving
at y 0, porch top at y 0.5.

Run:  blender -b --python-exit-code 1 -P author_basic_general.py
Outputs: unity/AthenHill/Assets/AthenHill/Art/WardShops/Booth/BasicGeneral_LOD0/1.glb, basic_general.json,
         art/north_avenue_20260930/basic-general-source.blend
"""
import bpy, bmesh, json, math, random, sys
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "art/ward_masonry_kit"))
import ward_masonry as WM
sys.path.insert(0, str(HERE))
from north_kit import corrugated_sheet
from ward_masonry import (Part, Frame, stone_tint, ashlar_block, fill_wall, eroded_bevel, block_wear, finalize_parts, AOBaker,
                          DripSet, ScarSet, scatter_impacts, lerp, drng, export, tri_count, MORTAR_FRONT)

OUT = ROOT / "unity/AthenHill/Assets/AthenHill/Art/WardShops/Booth"
OUT.mkdir(parents=True, exist_ok=True)

BASE = 0.5
J = 0.009
QD = 0.08            # corner stones stand a little proud of the wall blocks (0.062)
COURSES = [0.5, 0.92, 1.34, 1.76, 2.18, 2.60, 3.02]
# kept colliders (local): back x +-2.6, z -1.9..-1.1, y 0.5..3.5; sides x +-(2.2..2.6), z -1.4..0.4, y 0.5..2.9;
# porch x +-2.83, z -1.83..2.30, top 0.5; step x +-1.6, z 2.30..3.10, top 0.25; roof slab y 2.975..3.225
REAR_OUT, REAR_IN = -1.62, -1.101          # dressed faces (inner = the shelf wall, world z 14.0)
SIDE_IN, SIDE_OUT, SIDE_END = 2.2, 2.6, 0.4
PIER_X, PIER_Z = (2.16, 2.64), (1.28, 1.72)
LINTEL = (2.84, 3.16)
ATTIC = (3.16, 3.58)
FRONT = 1.74                               # lintel front face (the family sign hangs 2 cm in front of it)


class Booth:
    def __init__(self, lod):
        self.lod = lod
        self.name = "BasicGeneral"
        self.L = random.Random(1504)
        WM.set_state(lod, self.L, self.name)
        WM.WEAR["ground_y"] = BASE
        WM.TINT[:] = [1.06, 0.98, 0.88]
        WM.reset_materials()
        self.coll = bpy.data.collections.new(f"{self.name}_LOD{lod}")
        bpy.context.scene.collection.children.link(self.coll)
        p = lambda s, wear=True: Part(f"{self.name}_{s}_LOD{lod}", wear=wear)
        self.mas, self.trim, self.pod = p("Masonry"), p("Trim"), p("Porch")
        self.metal, self.roof, self.sand = p("Metal", False), p("Roof", False), p("Sand", False)
        self.drips = DripSet(base=0.18, base_top=3.1, ground_y=BASE)
        self.scars = ScarSet(base=0.1)
        self.rec = {"colliders": [], "mounts": [], "notes": []}

    # ------------------------------------------------------------------ drips on axis-aligned faces
    def drip(self, F, ua, ub, top, length, strength, kind="grime", soft=0.12, off=0.0):
        n = F.n
        a, b = F.P(ua, 0, off), F.P(ub, 0, off)
        if abs(n.z) > 0.5:
            self.drips.add((0, 0, n.z), a.z, a.x, b.x, top, length, strength, kind, soft)
        else:
            self.drips.add((n.x, 0, 0), a.x, a.z, b.z, top, length, strength, kind, soft)

    # ------------------------------------------------------------------ a rectangular block of masonry with bonded corners
    def prism(self, x0, x1, z0, z1, courses, hidden=(), key="p", QL=0.62, QS=0.3, face_d=0.062):
        """Dressed ashlar on the four faces of the box x0..x1, z0..z1 (outer dressed faces; frame planes sit face_d
        inside). Corners alternate course by course (front/back faces own even courses); faces narrower than 0.75 m
        get one stone across that returns round both corners. hidden: faces not built ('s' +z, 'n' -z, 'e' +x, 'w' -x)."""
        d = face_d
        X0, X1, Z0, Z1 = x0 + d, x1 - d, z0 + d, z1 - d          # frame planes (the adjacent faces' planes bound each face)
        faces = {
            "s": (Frame((0, 0, Z1), (1, 0, 0), (0, 0, 1)), X0, X1),
            "n": (Frame((0, 0, Z0), (-1, 0, 0), (0, 0, -1)), -X1, -X0),
            "e": (Frame((X1, 0, 0), (0, 0, -1), (1, 0, 0)), -Z1, -Z0),
            "w": (Frame((X0, 0, 0), (0, 0, 1), (-1, 0, 0)), Z0, Z1),
        }
        width = {k: v[2] - v[1] for k, v in faces.items()}
        adj = {"s": ("w", "e"), "n": ("e", "w"), "e": ("s", "n"), "w": ("n", "s")}   # (neighbour at ua, at ub)

        def thin(f):
            return width[f] < 0.7

        def ret(owner, other):          # how far an owner's corner stone returns along the other face
            return min(QL if thin(owner) else QS, width[other] / 2)
        for ci, (y0, y1) in enumerate(zip(courses, courses[1:])):
            rough = ci == 0 and y0 <= BASE + 1e-3
            mat = "VH_AshlarRough" if rough else "VH_Ashlar"
            depth, qd = (0.09, QD + 0.03) if rough else (d, QD)
            for f, (F, ua, ub) in faces.items():
                if f in hidden:
                    continue
                owned = (ci % 2 == 0) == (f in ("s", "n"))
                la, lb = adj[f]
                F.box(self.mas, ua, ub, y0, y1, 0.0, MORTAR_FRONT, "VH_Mortar", skip=("s0", "bottom", "top", "s1", "s3"))
                if owned:
                    if thin(f):
                        ashlar_block(self.mas, F, ua - qd + J / 2, ub + qd - J / 2, y0 + J / 2, y1 - J / 2, mat=mat, depth=qd,
                                     back=-ret(f, la), key=(key, f, ci, "t"), chip=0.25, bevel=(0.014, 0.026))
                        continue
                    ql = min(QL, width[f] / 2 - J)
                    for (u0, u1, o) in ((ua - qd, ua + ql, la), (ub - ql, ub + qd, lb)):
                        ashlar_block(self.mas, F, u0 + J / 2, u1 - J / 2, y0 + J / 2, y1 - J / 2, mat=mat, depth=qd,
                                     back=-ret(f, o), key=(key, f, ci, round(u0, 2)), chip=0.22, bevel=(0.014, 0.026))
                    a, b = ua + ql + J, ub - ql - J
                else:
                    a, b = ua + ret(la, f) + J, ub - ret(lb, f) - J
                if b - a > 0.05:
                    fill_wall(self.mas, F, a, b, [y0, y1], [], mat=mat, key=(key, f), course_offset=ci, lmin=0.5, lmax=1.1, depth=depth,
                              mortar=False)
        return faces

    def coping(self, x0, x1, z0, z1, y, t=0.12, over=0.05, seg=0.85, key="c"):
        """Slabs along the longer axis, overhanging every side, weathered top arrises, drips under the overhang."""
        along_x = (x1 - x0) >= (z1 - z0)
        a0, a1 = (x0, x1) if along_x else (z0, z1)
        n = max(1, round((a1 - a0) / seg))
        for i in range(n):
            a, b = lerp(a0 - over, a1 + over, i / n), lerp(a0 - over, a1 + over, (i + 1) / n)
            bid = self.trim.new_block(tint=stone_tint())
            if along_x:
                lo, hi = (a + 0.004, y, z0 - over), (b - 0.004, y + t, z1 + over)
            else:
                lo, hi = (x0 - over, y, a + 0.004), (x1 + over, y + t, b - 0.004)
            vs, made = self.trim.box(lo, hi, "VH_Ashlar", bid)
            eroded_bevel(self.trim, list(made["top"].edges) + list(made["bottom"].edges), self.L.uniform(0.012, 0.02), 2, seg_len=0.2)

    # ------------------------------------------------------------------ the booth
    def build(self):
        mas, trim, metal, pod = self.mas, self.trim, self.metal, self.pod
        # rear wall (outer face on the old line, inner face = the shelf wall) and cheek walls on the kept colliders
        rear = self.prism(-SIDE_OUT, SIDE_OUT, REAR_OUT, REAR_IN, COURSES, key="rear")
        self.coping(-SIDE_OUT, SIDE_OUT, REAR_OUT, REAR_IN, COURSES[-1], key="rear_cope")
        for sx in (-1, 1):
            x0, x1 = sorted((sx * SIDE_IN, sx * SIDE_OUT))
            self.prism(x0, x1, REAR_IN - 0.25, SIDE_END, COURSES, hidden=("n",), key=("side", sx))
            self.coping(x0, x1, REAR_IN - 0.02, SIDE_END, COURSES[-1], key=("side_cope", sx))
        # front piers, caps, steel lintel, attic course and coping
        for sx in (-1, 1):
            x0, x1 = sorted((sx * PIER_X[0], sx * PIER_X[1]))
            self.prism(x0, x1, PIER_Z[0], PIER_Z[1], COURSES[:6], key=("pier", sx))
            bid = trim.new_block(tint=stone_tint())
            vs, made = trim.box((x0 - 0.06, 2.60, PIER_Z[0] - 0.06), (x1 + 0.06, LINTEL[0], PIER_Z[1] + 0.06), "VH_Ashlar", bid)
            eroded_bevel(trim, [e for f in made.values() for e in f.edges], 0.016, 2, seg_len=0.2)
            self.rec["colliders"].append({"name": f"COL_FrontPier_{'w' if sx < 0 else 'e'}", "center": [(x0 + x1) / 2, (BASE + LINTEL[0]) / 2, sum(PIER_Z) / 2],
                                          "size": [x1 - x0 + 0.12, LINTEL[0] - BASE, PIER_Z[1] - PIER_Z[0] + 0.12]})
        self.lintel()
        self.prism(-PIER_X[1] - 0.06, PIER_X[1] + 0.06, PIER_Z[0] + 0.06, FRONT - 0.005, [ATTIC[0], ATTIC[1]], key="attic", QL=0.55, QS=0.2)
        self.coping(-PIER_X[1] - 0.06, PIER_X[1] + 0.06, PIER_Z[0] + 0.06, FRONT - 0.005, ATTIC[1], t=0.13, over=0.06, key="attic_cope")
        self.roof_and_gutter()
        self.shutter_box()
        self.porch()
        self.services()
        self.weathering(rear)

    def lintel(self):
        """Riveted box girder (painted red, worn) bearing on the pier caps; bearing plates; sign straps."""
        m = self.metal
        x0, x1 = -PIER_X[1] - 0.08, PIER_X[1] + 0.08
        y0, y1 = LINTEL
        z0, z1 = PIER_Z[0] + 0.05, FRONT
        m.box((x0, y0, z1 - 0.012), (x1, y1, z1), "WS_PaintRed")                    # front web plate
        m.box((x0, y0, z0), (x1, y1, z0 + 0.012), "WS_PaintRed")                    # rear web plate
        for yy in (y0, y1 - 0.016):
            m.box((x0 - 0.02, yy, z0 - 0.02), (x1 + 0.02, yy + 0.016, z1 + 0.02), "WS_PaintRed")   # flanges
        for sx in (-1, 1):                                                           # end plates, bearing plates
            m.box((sx * (x1 + 0.02) - 0.008, y0, z0), (sx * (x1 + 0.02) + 0.008, y1, z1), "WS_PaintRed")
            m.box((sx * sum(PIER_X) / 2 - 0.26, y0 - 0.02, PIER_Z[0] - 0.02), (sx * sum(PIER_X) / 2 + 0.26, y0, PIER_Z[1] + 0.02), "VH_Steel")
        # stiffeners every 0.9 m on the front web, rivet rows along both flanges
        x = x0 + 0.45
        while x < x1 - 0.3:
            m.box((x - 0.012, y0 + 0.016, z1), (x + 0.012, y1 - 0.016, z1 + 0.02), "WS_PaintRed")
            x += 0.9
        if self.lod == 0:
            x = x0 + 0.06
            while x < x1 - 0.03:
                for yy in (y0 + 0.035, y1 - 0.035):
                    m.sphere((x, yy, z1), 0.009, "VH_Steel", 6, hemi_axis=(0, 0, 1))
                x += 0.15
        F = Frame((0, 0, z1), (1, 0, 0), (0, 0, 1))
        self.drip(F, x0, x1, y0, 0.2, 0.9, "rust", soft=0.25)
        # rust from the bearings stains the pier caps and faces below
        for sx in (-1, 1):
            u = sx * sum(PIER_X) / 2
            Fp = Frame((0, 0, PIER_Z[1]), (1, 0, 0), (0, 0, 1))
            self.drip(Fp, u - 0.2, u + 0.2, 2.84, 1.6, 0.8, "rust", soft=0.08)
            self.drip(Fp, u - 0.24, u + 0.24, 2.60, 1.9, 0.6, soft=0.12)
        # sign straps (the family sign is hung 2 cm off the web)
        for u in (-0.95, 0.95):
            m.box((u - 0.025, y1 - 0.01, z1 - 0.02), (u + 0.025, y1 + 0.004, z1 + 0.05), "VH_Steel")
            m.box((u - 0.025, y0 + 0.12, z1 + 0.035), (u + 0.025, y1 + 0.004, z1 + 0.05), "VH_Steel")
        self.rec["lintel"] = {"y": [y0, y1], "front": z1}

    def roof_and_gutter(self):
        """Corrugated sheets from the attic (front, high) to a gutter behind the rear wall; purlins, side bearers."""
        m, roof = self.metal, self.roof
        zf, yf = PIER_Z[0] + 0.06, 3.34
        zr, yr = REAR_OUT - 0.28, 3.14
        slope = (yf - yr) / (zf - zr)
        yat = lambda z: yr + (z - zr) * slope
        # side bearers (channels following the fall) on the cheek-wall copings, spanning on to the attic
        for sx in (-1, 1):
            x = sx * (SIDE_IN + SIDE_OUT) / 2
            za, zb = REAR_OUT + 0.05, zf
            c = [(x - 0.05, yat(za) - 0.18, za), (x + 0.05, yat(za) - 0.18, za), (x + 0.05, yat(zb) - 0.18, zb), (x - 0.05, yat(zb) - 0.18, zb),
                 (x - 0.05, yat(za) - 0.005, za), (x + 0.05, yat(za) - 0.005, za), (x + 0.05, yat(zb) - 0.005, zb), (x - 0.05, yat(zb) - 0.005, zb)]
            m.hexa(c, "VH_PaintedSteel")
        # purlins
        for z in (-0.8, 0.0, 0.8):
            y = yat(z) - 0.005
            m.box((-SIDE_OUT, y - 0.1, z - 0.03), (SIDE_OUT, y, z + 0.03), "VH_PaintedSteel")
        # corrugated sheet, ribs along the fall (z), one continuous surface (the underside is seen from the counter)
        corrugated_sheet(roof, -SIDE_OUT - 0.15, SIDE_OUT + 0.15, (yat(zr) + 0.004, zr), (yat(zf) + 0.004, zf), "WS_Corrugated", lod=self.lod)
        # half-round gutter behind the rear wall, downpipe down the rear face to the porch ledge
        gz = zr - 0.02
        m.cyl((-SIDE_OUT - 0.1, yr - 0.06, gz), (SIDE_OUT + 0.1, yr - 0.06, gz), 0.07, "VH_Steel", 8)
        for x in (-1.6, 0.0, 1.6):
            m.box((x - 0.015, yr - 0.14, gz - 0.02), (x + 0.015, yr - 0.02, REAR_OUT), "VH_Steel")
        px = 2.25
        m.tube([(px, yr - 0.08, gz), (px, yr - 0.4, REAR_OUT - 0.1), (px, BASE + 0.18, REAR_OUT - 0.1), (px, BASE + 0.02, REAR_OUT - 0.26)],
               0.05, "VH_Steel", 10, clamps=0.9)
        Fr = Frame((0, 0, REAR_OUT), (-1, 0, 0), (0, 0, -1))
        self.drip(Fr, -px - 0.2, -px + 0.2, yr - 0.3, 2.6, 0.6, soft=0.14)
        self.drip(Fr, -px - 0.1, -px + 0.1, yr - 0.4, 1.4, 0.75, "rust", soft=0.08)
        self.rec["roof"] = {"front": [zf, yf], "rear": [zr, yr]}

    def shutter_box(self):
        """Roll-up security shutter: roller box behind the lintel, steel guides on the piers' inner faces."""
        m = self.metal
        y0, y1 = 2.56, LINTEL[0]
        m.box((-PIER_X[0], y0, PIER_Z[0] + 0.04), (PIER_X[0], y1, PIER_Z[0] + 0.3), "VH_PaintedSteel")
        m.box((-PIER_X[0], y0 - 0.03, PIER_Z[0] + 0.12), (PIER_X[0], y0 + 0.01, PIER_Z[0] + 0.18), "WS_Shutter")   # curtain bottom bar
        for sx in (-1, 1):
            x = sx * PIER_X[0]
            m.box((x - sx * 0.05, BASE, PIER_Z[0] + 0.1), (x, y0, PIER_Z[0] + 0.2), "VH_Steel")
            m.box((x - sx * 0.07, BASE + 0.35, PIER_Z[0] + 0.12), (x - sx * 0.05, BASE + 0.45, PIER_Z[0] + 0.18), "VH_Brass")   # hasp
        self.rec["notes"].append("security shutter rolled up behind the lintel")

    def porch(self):
        pod = self.pod
        x0, x1, z0, z1 = -2.83, 2.83, -1.83, 2.30
        z, row = z0, 0
        while z < z1 - 1e-3:
            dz = min(0.75, z1 - z)
            x = x0
            first = True
            while x < x1 - 1e-3:
                ln = self.L.uniform(0.7, 1.1)
                if first and row % 2:
                    ln *= 0.5
                first = False
                xb = min(x1, x + ln)
                if x1 - xb < 0.3:
                    xb = x1
                bid = pod.new_block(tint=stone_tint("rough"))
                vs, made = pod.box((x + .004, BASE - 0.12, z + .004), (xb - .004, BASE, z + dz - .004), "VH_PodiumSlab", bid, skip=("bottom",))
                eroded_bevel(pod, list(made["top"].edges), self.L.uniform(0.006, 0.014), 2, seg_len=0.2)
                x = xb
            z += dz
            row += 1
        for (F, ua, ub, k) in ((Frame((0, 0, z1), (1, 0, 0), (0, 0, 1)), x0, x1, "pf"), (Frame((x1, 0, 0), (0, 0, -1), (1, 0, 0)), -z1, -z0, "pe"),
                               (Frame((x0, 0, 0), (0, 0, 1), (-1, 0, 0)), z0, z1, "pw"), (Frame((0, 0, z0), (-1, 0, 0), (0, 0, -1)), -x1, -x0, "pn")):
            fill_wall(pod, F, ua, ub, [0.0, 0.25, BASE - 0.12], [], mat="VH_AshlarRough", lmin=0.6, lmax=1.2, key=k, depth=0.04)
        x = -1.6
        while x < 1.6 - 1e-3:
            xb = min(1.6, x + self.L.uniform(0.8, 1.2))
            if 1.6 - xb < 0.4:
                xb = 1.6
            bid = pod.new_block(tint=stone_tint("rough"))
            vs, made = pod.box((x + .004, 0.0, z1), (xb - .004, 0.25, z1 + 0.8), "VH_PodiumSlab", bid, skip=("bottom",))
            eroded_bevel(pod, list(made["top"].edges) + list(made["s2"].edges), 0.018, 2, seg_len=0.2)
            x = xb
        if self.lod == 0:
            # sheltered sand: along the cheek walls inside and out, round the piers, behind the rear wall
            for sx in (-1, 1):
                self.drift_z(sx * (SIDE_IN - 0.01), -sx, REAR_IN + 0.5, SIDE_END - 0.05, ("in", sx))
                self.drift_z(sx * (SIDE_OUT + 0.01), sx, REAR_OUT + 0.1, SIDE_END - 0.1, ("out", sx), width=0.22)
                self.drift_x(sx * PIER_X[0] - sx * 0.35, sx * PIER_X[1], PIER_Z[1] + 0.07, 1, ("pier", sx), width=0.2)
            self.drift_x(-2.4, 2.4, REAR_OUT - 0.08, -1, ("rear",), width=0.16, height=0.035)

    def drift_x(self, a, b, z, side, key, width=0.26, height=0.045, n=12):
        a, b = min(a, b), max(a, b)
        rr = drng("drift", *key)
        bm, mi = self.sand.bm, self.sand.mi("VH_Sand")
        rows = []
        for i in range(n + 1):
            u = lerp(a, b, i / n)
            env = math.sin(math.pi * i / n) ** 0.6
            h = height * env * rr.uniform(0.6, 1.2)
            w = width * env * rr.uniform(0.7, 1.2) + 0.02
            rows.append([bm.verts.new(Vector((u, BASE - 0.005, z))), bm.verts.new(Vector((u, BASE + h, z + side * w * 0.3))),
                         bm.verts.new(Vector((u, BASE - 0.005, z + side * w)))])
        for i in range(n):
            for k in range(2):
                bm.faces.new([rows[i][k], rows[i + 1][k], rows[i + 1][k + 1], rows[i][k + 1]]).material_index = mi
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

    def drift_z(self, x, side, a, b, key, width=0.3, height=0.05, n=12):
        rr = drng("driftz", *key)
        bm, mi = self.sand.bm, self.sand.mi("VH_Sand")
        rows = []
        for i in range(n + 1):
            u = lerp(a, b, i / n)
            env = math.sin(math.pi * i / n) ** 0.6
            h = height * env * rr.uniform(0.6, 1.2)
            w = width * env * rr.uniform(0.7, 1.2) + 0.02
            rows.append([bm.verts.new(Vector((x, BASE - 0.005, u))), bm.verts.new(Vector((x + side * w * 0.3, BASE + h, u))),
                         bm.verts.new(Vector((x + side * w, BASE - 0.005, u)))])
        for i in range(n):
            for k in range(2):
                bm.faces.new([rows[i][k], rows[i + 1][k], rows[i + 1][k + 1], rows[i][k + 1]]).material_index = mi
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

    def services(self):
        """Rear: aquifer service box with valve and meter, conduit to the roof (feeds the sign), lamp mount.
        Lamps: inside each cheek wall (light the counter), on each front pier (porch and sign), one at the rear."""
        m = self.metal
        Fr = Frame((0, 0, REAR_OUT), (-1, 0, 0), (0, 0, -1))
        u0, u1 = -0.2, 0.55                                   # frame u = -x
        Fr.box(m, u0, u1, 0.72, 1.42, 0.0, 0.26, "WS_PaintTeal")
        Fr.box(m, u0 - 0.02, u1 + 0.02, 1.42, 1.47, -0.01, 0.3, "WS_PaintTeal")
        Fr.box(m, u0 + 0.05, u1 - 0.05, 0.8, 1.35, 0.26, 0.27, "VH_Steel")
        c = Fr.P((u0 + u1) / 2, 0.55, 0.13)
        m.tube([Fr.P(0.35, 0.72, 0.13), Fr.P(0.35, 0.55, 0.13), Fr.P(0.35, 0.55, 0.34), Fr.P(0.35, 0.02, 0.34)], 0.04, "VH_Steel", 10)
        m.cyl(Fr.P(0.35, 0.62, 0.3), Fr.P(0.35, 0.62, 0.36), 0.08, "WS_PaintRed", 12)        # valve wheel
        m.cyl(Fr.P(0.0, 0.95, 0.27), Fr.P(0.0, 0.95, 0.3), 0.07, "VH_Brass", 12)               # meter
        self.drip(Fr, u0, u1, 0.72, 0.6, 0.7, "rust", soft=0.08)
        m.tube([Fr.P(-0.9, 1.3, 0.05), Fr.P(-0.9, 3.0, 0.05)], 0.02, "VH_Steel", 8, clamps=0.6)
        Fr.box(m, -1.05, -0.75, 1.1, 1.4, 0.0, 0.14, "VH_PaintedSteel")
        yaw = {"s": 0, "n": 180, "e": 90, "w": -90}
        mounts = self.rec["mounts"]
        for sx in (-1, 1):
            mounts.append({"name": f"Counter lamp {'west' if sx < 0 else 'east'}", "prefab": "PH_WallLamp", "light": True,
                           "pos": [sx * (SIDE_IN - 0.065), 2.4, -0.45], "yaw": yaw["w"] if sx > 0 else yaw["e"]})
            mounts.append({"name": f"Pier lamp {'west' if sx < 0 else 'east'}", "prefab": "PH_WallLamp", "light": True,
                           "pos": [sx * sum(PIER_X) / 2, 2.05, PIER_Z[1] + 0.065], "yaw": 0})
            Fp = Frame((0, 0, PIER_Z[1]), (1, 0, 0), (0, 0, 1))
            self.drip(Fp, sx * sum(PIER_X) / 2 - 0.08, sx * sum(PIER_X) / 2 + 0.08, 1.95, 1.2, 0.75, "rust", soft=0.06)
        mounts.append({"name": "Rear lamp", "prefab": "PH_WallLamp", "light": True, "pos": [-0.9, 2.45, REAR_OUT - 0.065], "yaw": 180})
        mounts.append({"name": "Rear power box", "prefab": "PH_PowerBox", "pos": [1.6, 1.4, REAR_OUT - 0.065], "yaw": 180})

    def weathering(self, rear):
        """Runoff under every coping and cap, rust under the lintel, soil at the wall feet, a few old impacts."""
        top = COURSES[-1]
        for f, (F, ua, ub) in rear.items():
            if f == "s":
                self.drip(F, ua, ub, top, 1.2, 0.45, soft=0.3)       # the shelf wall is sheltered by the roof
            else:
                self.drip(F, ua - 0.1, ub + 0.1, top, 2.6, 0.85, soft=0.25)
        for sx in (-1, 1):
            for n in ((1, 0, 0), (-1, 0, 0)):
                x = sx * (SIDE_OUT if n[0] * sx > 0 else SIDE_IN)
                self.drips.add(n, x, REAR_IN, SIDE_END, top, 2.4, 0.8, "grime", 0.25)
            self.drips.add((0, 0, 1), SIDE_END, sx * SIDE_IN, sx * SIDE_OUT, top, 2.4, 0.8, "grime", 0.1)
        Fa = Frame((0, 0, FRONT), (1, 0, 0), (0, 0, 1))
        self.drip(Fa, -PIER_X[1], PIER_X[1], ATTIC[1], 0.45, 0.8, soft=0.3)
        rng = random.Random(77)
        faces = [(Frame((SIDE_OUT, 0, 0), (0, 0, -1), (1, 0, 0)), -SIDE_END, -REAR_OUT),
                 (Frame((-SIDE_OUT, 0, 0), (0, 0, 1), (-1, 0, 0)), REAR_OUT, SIDE_END),
                 (Frame((0, 0, REAR_OUT), (-1, 0, 0), (0, 0, -1)), -SIDE_OUT, SIDE_OUT)]
        scatter_impacts(self.scars, faces, 3, rng, BASE + 0.3, 2.9, 0.4, 0.9)
        self.scars.impact((PIER_X[1] + 0.07, 1.6, 1.5), 0.5, 0.9)             # a hit on the east pier's side

    def finish(self):
        self.build()
        parts = [self.mas, self.trim, self.pod, self.metal, self.roof, self.sand]
        finalize_parts(parts)
        ao = AOBaker(parts, ground_y=0.0, samples=24 if self.lod == 0 else 10)
        objs = [self.mas.build(self.coll, ao=ao, drips=self.drips, ground_y=BASE, scars=self.scars),
                self.trim.build(self.coll, ao=ao, drips=self.drips, ground_y=BASE, scars=self.scars),
                self.pod.build(self.coll, ao=ao, drips=self.drips, ground_y=0.0, splash=0.22, scars=self.scars),
                self.metal.build(self.coll), self.roof.build(self.coll)]
        if len(self.sand.bm.faces):
            objs.append(self.sand.build(self.coll))
        self.rec["triangles"] = tri_count(objs)
        self.rec["objects"] = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs}
        self.rec["vertex_ao_rays"] = ao.rays
        return objs


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    report = {"source": "art/north_avenue_20260930/author_basic_general.py", "date": "2026-09-30", "shop": "basic_general",
              "root_world": [8.0, 0.0, 15.1], "yaw": 0,
              "units": "Unity metres local to the booth root (porch-front centre line at paving level, +Z towards the avenue)", "lods": {}}
    for lod in (0, 1):
        b = Booth(lod)
        objs = b.finish()
        export(objs, OUT / f"BasicGeneral_LOD{lod}.glb")
        report["lods"][f"LOD{lod}"] = {"triangles": b.rec["triangles"], "objects": b.rec["objects"]}
        if lod == 0:
            report.update({k: v for k, v in b.rec.items() if k not in ("triangles", "objects")})
        print(f"BasicGeneral LOD{lod}: {b.rec['triangles']} triangles", flush=True)
    (OUT / "basic_general.json").write_text(json.dumps(report, indent=1))
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "basic-general-source.blend"))


if __name__ == "__main__":
    main()
