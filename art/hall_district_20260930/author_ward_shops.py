"""Ward shops rebuild around the Vanguard Hall plaza, Blender 5.2 headless (30 September 2026).

Carl (30 Sep 2026): "Rebuild the neighbouring buildings to the same standard: modelled stone, proper doorways, lamps on
the city's day/night timing. That way the Hall doesn't stand alone." and "if you rebuild the tool shop remember sci-fi
not woodworking shop from the 90s as it looks now". Target: concept/street-concept-a.png (not yet accepted).

Run:  blender -b --python-exit-code 1 -P author_ward_shops.py [shop ...]

Every shop sits on the existing standard parcel: facade plane 18.0 m from the avenue axis, 7.6 m wide, 6.9 m deep,
on the existing 0.5 m porch (3.5 m deep in front of the facade) and single 0.25 m step, whose colliders stay in the
scene. Coordinates are Unity metres local to the shop root: origin = facade centre at paving level, +Z = outward
(towards the avenue), X along the facade, Y up. The root is rotated in Unity (west row yaw +90, east row yaw -90).

Construction uses the shared Ward masonry kit (art/ward_masonry_kit): quoined ashlar with dressed margins, eroded
arrises, chips and spalls, ray-traced vertex occlusion, runoff/rust/edge wear channels for Athen Hill/Masonry Lit.

Outputs (unity/AthenHill/Assets/AthenHill/Art/WardShops/Models): <Shop>_LOD0.glb, <Shop>_LOD1.glb, <shop>.json
(colliders, lamp/fitting mounts, lights, sign mounts, display alcove, report) and art/hall_district_20260930/shops-source.blend.
"""
import bpy, bmesh, json, math, random, sys
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "art/ward_masonry_kit"))
import ward_masonry as WM
from ward_masonry import (Part, Frame, stone_tint, ashlar_block, fill_wall, sweep, eroded_bevel, split_edge, block_wear,
                          finalize_parts, AOBaker, DripSet, U, lerp, smoothstep, drng, export, tri_count, MORTAR_FRONT,
                          ScarSet, scatter_impacts)

OUT = ROOT / "unity/AthenHill/Assets/AthenHill/Art/WardShops/Models"
OUT.mkdir(parents=True, exist_ok=True)

BASE = 0.5
HW = 3.8
D = 6.9
QD = 0.092           # quoin face plane (wall block faces at 0.062)
QL, QS = 0.82, 0.44  # quoin long face / short return
J = 0.009
PORCH = 3.6          # porch depth in front of the facade plane (roots at 18.1 m; kept porch collider ends at 14.5 m)
G = [0.5, 1.05] + [round(1.05 + 0.42 * i, 3) for i in range(1, 10)]     # 0.5 .. 4.83 (plinth 0.5-1.05)
STRING = (4.83, 5.08)
UP = [round(5.08 + 0.42 * i, 3) for i in range(7)]                        # 5.08 .. 7.60


def course_of(y, courses):
    for i, c in enumerate(courses):
        if abs(c - y) < 1e-3:
            return i
    raise ValueError(f"{y} is not on a course line")


class Shop:
    def __init__(self, name, lod, tint, seed, wall_top=7.60, upper=None, parapet=0.57, gable=None):
        self.name, self.lod = name, lod
        self.L = random.Random(seed)
        WM.set_state(lod, self.L, name)
        WM.WEAR["ground_y"] = BASE
        WM.TINT[:] = list(tint)
        WM.reset_materials()
        self.coll = bpy.data.collections.new(f"{name}_LOD{lod}")
        bpy.context.scene.collection.children.link(self.coll)
        p = lambda s, wear=True: Part(f"{name}_{s}_LOD{lod}", wear=wear)
        self.mas, self.trim, self.pod = p("Masonry"), p("Trim"), p("Porch")
        self.metal, self.glass, self.roof = p("Metal", False), p("Glass", False), p("Roof", False)
        self.canvas, self.sand, self.glow = p("Canvas", False), p("Sand", False), p("Glow", False)
        self.clear = p("Display", False)
        self.upper = upper if upper is not None else [c for c in UP if c <= wall_top + 1e-3]
        self.wall_top = self.upper[-1] if self.upper else STRING[1]
        self.gable = gable
        self.courses = G + self.upper           # all wall courses (the string band sits between G[-1] and upper[0])
        self.parapet = parapet
        self.drips = DripSet(base=0.2, base_top=self.wall_top, ground_y=BASE)
        self.scars = ScarSet(base=0.12)
        self.scar_rng = random.Random(seed * 7 + 3)
        self.rec = {"colliders": [], "mounts": [], "lights": [], "signs": [], "notes": [], "display": None}
        self.holes = {"front": [], "rear": [], "right": [], "left": []}
        self.later = []                          # opening builders run after the walls
        self.FRONT = Frame((0, 0, 0), (1, 0, 0), (0, 0, 1))
        self.REAR = Frame((0, 0, -D), (-1, 0, 0), (0, 0, -1))
        self.RIGHT = Frame((HW, 0, 0), (0, 0, -1), (1, 0, 0))    # u = -z: 0 (facade) .. D (rear)
        self.LEFT = Frame((-HW, 0, 0), (0, 0, 1), (-1, 0, 0))    # u = z: -D (rear) .. 0 (facade)
        self.faces = {"front": (self.FRONT, -HW, HW), "rear": (self.REAR, -HW, HW),
                      "right": (self.RIGHT, 0.0, D), "left": (self.LEFT, -D, 0.0)}

    # ------------------------------------------------------------------ drips
    def fdrip(self, F, ua, ub, top, length, strength, kind="grime", plane_off=0.0, soft=0.12):
        n = F.n
        a, b = F.P(ua, 0, plane_off), F.P(ub, 0, plane_off)
        if abs(n.z) > 0.5:
            self.drips.add((0, 0, n.z), a.z, a.x, b.x, top, length, strength, kind, soft)
        else:
            self.drips.add((n.x, 0, 0), a.x, a.z, b.z, top, length, strength, kind, soft)

    # ------------------------------------------------------------------ walls + quoins
    def walls(self):
        L = self.L
        cs = self.courses
        for face, (F, ua, ub) in self.faces.items():
            side = face in ("right", "left")
            holes = self.holes[face]
            for ci, (y0, y1) in enumerate(zip(cs, cs[1:])):
                if abs(y0 - STRING[0]) < 1e-3:
                    continue            # string course band
                if self.gable and face in ("front", "rear") and y0 >= self.gable["eave"] - 1e-3:
                    continue
                owned = (ci % 2 == 1) if side else (ci % 2 == 0)
                rough = ci == 0
                mat = "VH_AshlarRough" if rough else "VH_Ashlar"
                depth = 0.1 if rough else 0.062
                qdepth = 0.13 if rough else QD
                a = ua + (QL if owned else QS) + J
                b = ub - (QL if owned else QS) - J
                fill_wall(self.mas, F, a, b, [y0, y1], holes, mat=mat, key=(face, "w"), course_offset=ci,
                          lmin=0.55, lmax=1.2, depth=depth)
                # mortar behind the quoin zones
                F.box(self.mas, ua - QD, a, y0, y1, 0.02, MORTAR_FRONT, "VH_Mortar", skip=("s0", "bottom", "top", "s1", "s3"))
                F.box(self.mas, b, ub + QD, y0, y1, 0.02, MORTAR_FRONT, "VH_Mortar", skip=("s0", "bottom", "top", "s1", "s3"))
                if owned:
                    for (u0, u1) in ((ua - qdepth, ua + QL), (ub - QL, ub + qdepth)):
                        ashlar_block(self.mas, F, u0 + J / 2, u1 - J / 2, y0 + J / 2, y1 - J / 2, mat=mat, depth=qdepth,
                                     back=-QS, key=(face, "q", ci, round(u0, 2)), chip=0.2, bevel=(0.014, 0.026))
        # string course (sweep round all four faces) and plinth cap
        sc = [(-0.04, STRING[0]), (0.1, STRING[0]), (0.1, STRING[0] + 0.05), (0.15, STRING[0] + 0.1),
              (0.15, STRING[1]), (-0.04, STRING[1])]
        loop = [(-HW - QD, QD), (HW + QD, QD), (HW + QD, -D - QD), (-HW - QD, -D - QD)]
        if not self.gable:
            sweep(self.trim, loop, True, sc, "VH_Ashlar", seg=1.25)
        else:
            sweep(self.trim, loop, True, sc, "VH_Ashlar", seg=1.25)
        for face, (F, ua, ub) in self.faces.items():
            self.fdrip(F, ua - 0.2, ub + 0.2, STRING[0], 2.6, 0.65, soft=0.3)

    # ------------------------------------------------------------------ cornice, parapet, roof deck
    def top(self, cornice_h=0.45, dentils=False):
        y0 = self.wall_top
        prof = [(-0.03, y0), (0.08, y0), (0.08, y0 + 0.06), (0.14, y0 + 0.11), (0.22, y0 + 0.18), (0.3, y0 + 0.27),
                (0.34, y0 + 0.3), (0.34, y0 + cornice_h - 0.06), (0.3, y0 + cornice_h), (-0.03, y0 + cornice_h)]
        loop = [(-HW - QD, QD), (HW + QD, QD), (HW + QD, -D - QD), (-HW - QD, -D - QD)]
        sweep(self.trim, loop, True, prof, "VH_Ashlar", seg=1.3)
        if dentils and self.lod == 0:
            F = self.FRONT
            u = -HW + 0.1
            while u < HW - 0.1:
                F.box(self.trim, u, u + 0.09, y0 - 0.16, y0, 0.06, 0.16, "VH_Ashlar", bid=self.trim.new_block(tint=stone_tint()))
                u += 0.2
        py0 = y0 + cornice_h
        py1 = py0 + self.parapet
        pc = [py0, py1]
        PF = Frame((0, 0, 0.0), (1, 0, 0), (0, 0, 1))
        PR = Frame((0, 0, -D), (-1, 0, 0), (0, 0, -1))
        PE = Frame((HW, 0, 0), (0, 0, -1), (1, 0, 0))
        PW = Frame((-HW, 0, 0), (0, 0, 1), (-1, 0, 0))
        for F, (ua, ub) in ((PF, (-HW - QD, HW + QD)), (PR, (-HW - QD, HW + QD)), (PE, (0.02, D - 0.02)), (PW, (-D + 0.02, -0.02))):
            fill_wall(self.mas, F, ua, ub, pc, [], key=("par", F.n.x, F.n.z), lmin=0.8, lmax=1.4)
            F.box(self.mas, ua, ub, py0, py1, -0.4, 0.04, "VH_Mortar", skip=("s2",))
        cop = [(-0.46, py1), (0.08, py1), (0.08, py1 + 0.07), (0.03, py1 + 0.14), (-0.42, py1 + 0.14), (-0.46, py1 + 0.07)]
        sweep(self.trim, [(-HW - QD, QD + 0.02), (HW + QD, QD + 0.02), (HW + QD, -D - QD - 0.02), (-HW - QD, -D - QD - 0.02)],
              True, cop, "VH_Ashlar", seg=1.2)
        self.roof.box((-HW + 0.3, y0 + 0.3, -D + 0.3), (HW - 0.3, y0 + 0.4, -0.3), "VH_Roof")
        # drips: cornice, walls under the cornice, coping
        for face, (F, ua, ub) in self.faces.items():
            self.fdrip(F, ua - 0.3, ub + 0.3, y0, 4.8, 0.9, soft=0.3)
            self.fdrip(F, ua - 0.3, ub + 0.3, py1, 0.6, 0.7, soft=0.3)
        self.roof_y = y0 + 0.4
        self.top_y = py1 + 0.14
        return py1

    # ------------------------------------------------------------------ gable (steel-clad) + corrugated roof
    def gable_roof(self):
        g = self.gable
        eave, ridge, over = g["eave"], g["ridge"], 0.45
        # stone cap at the eave line (a projecting course), then steel-clad gable ends and a corrugated roof
        cap = [(-0.03, eave), (0.12, eave), (0.12, eave + 0.16), (-0.03, eave + 0.16)]
        sweep(self.trim, [(-HW - QD, QD), (HW + QD, QD), (HW + QD, -D - QD), (-HW - QD, -D - QD)], True, cap, "VH_Ashlar", seg=1.2)
        y0 = eave + 0.16
        for zf, nz in ((0.02, 1), (-D - 0.02, -1)):
            # vertical corrugated cladding sheets on the gable triangle (flat-topped strips following the rake)
            x = -HW
            k = 0
            while x < HW - 1e-3:
                w = 0.1
                x1 = min(HW, x + w)
                xm = (x + x1) / 2
                ytop = y0 + (ridge - y0) * (1 - abs(xm) / HW) - 0.02
                ridge_off = 0.022 if k % 2 == 0 else 0.0
                self.metal.box((x, y0, zf - 0.01 * nz + (ridge_off if nz > 0 else -ridge_off)),
                               (x1, ytop, zf + (0.012 + ridge_off) * nz), "WS_CladTeal" if g.get("teal") else "VH_DoorSteel")
                x = x1
                k += 1
        # gable vent (louvred) on the front
        if g.get("vent"):
            vx, vy = 0.0, y0 + (ridge - y0) * 0.45
            self.metal.box((vx - 0.45, vy - 0.35, 0.03), (vx + 0.45, vy + 0.35, 0.07), "VH_Steel")
            self.metal.box((vx - 0.4, vy - 0.3, 0.035), (vx + 0.4, vy + 0.3, 0.05), "VH_Dark")
            for i in range(6):
                yy = lerp(vy - 0.26, vy + 0.26, i / 5)
                c = [(vx - 0.4, yy - 0.03, 0.05), (vx + 0.4, yy - 0.03, 0.05), (vx + 0.4, yy - 0.03, 0.1), (vx - 0.4, yy - 0.03, 0.1),
                     (vx - 0.4, yy + 0.03, 0.04), (vx + 0.4, yy + 0.03, 0.04), (vx + 0.4, yy + 0.03, 0.06), (vx - 0.4, yy + 0.03, 0.06)]
                self.metal.hexa(c, "VH_Steel")
        # roof sheets: two slopes, corrugations along the fall line (x), purlins, bargeboards, ridge cap
        slope = math.atan2(ridge - y0, HW)
        for s in (-1, 1):
            n = int(round((D + 2 * over) / 0.09))
            for i in range(n):
                z0 = QD + over - (D + 2 * over) * i / n
                z1 = QD + over - (D + 2 * over) * (i + 1) / n
                lift = 0.025 if i % 2 == 0 else 0.0
                xa, xb = 0.0, s * (HW + over)
                ya, yb = ridge + 0.06 + lift, y0 - over * math.tan(slope) + 0.06 + lift
                c = [(xa, ya, z0), (xb, yb, z0), (xb, yb, z1), (xa, ya, z1),
                     (xa, ya + 0.012, z0), (xb, yb + 0.012, z0), (xb, yb + 0.012, z1), (xa, ya + 0.012, z1)]
                self.roof.hexa(c, "WS_Corrugated")
            # bargeboards on both gables
            for zf in (QD + over + 0.02, -D - QD - over - 0.02):
                a = (0.0, ridge + 0.1, zf)
                b = (s * (HW + over), y0 - over * math.tan(slope) + 0.1, zf)
                self.metal.cyl(a, b, 0.06, "VH_PaintedSteel", 4)
            # gutter along the eave
            gx = s * (HW + over + 0.05)
            self.metal.cyl((gx, y0 - over * math.tan(slope) - 0.02, QD + over), (gx, y0 - over * math.tan(slope) - 0.02, -D - QD - over),
                           0.07, "VH_Steel", 8)
        self.metal.cyl((0, ridge + 0.1, QD + over + 0.05), (0, ridge + 0.1, -D - QD - over - 0.05), 0.07, "VH_Steel", 6)
        self.roof_y = y0
        self.top_y = ridge + 0.2
        self.rec["gable"] = {"eave": eave, "ridge": ridge}

    # ------------------------------------------------------------------ openings
    def window(self, face, ua, ub, y0, y1, depth=0.3, kind="bars", lintel=True, blinds=False):
        F = self.faces[face][0]
        self.holes[face] += [(ua, ub, y0, y1)]
        lt = y1 + 0.42 if lintel else y1
        if lintel:
            self.holes[face] += [(ua - 0.15, ub + 0.15, y1, lt)]

        def build():
            trim, metal = self.trim, self.metal
            for (u0, u1) in ((ua - 0.001, ua + 0.06), (ub - 0.06, ub + 0.001)):
                j_y = [y0] + [c for c in self.courses if y0 < c < y1] + [y1]
                for (a, b) in zip(j_y, j_y[1:]):
                    bid = trim.new_block(tint=stone_tint(), ao=0.8)
                    F.box(trim, u0, u1, a + .004, b - .004, -depth, 0.03, "VH_Ashlar", bid, skip=("bottom", "top"))
            bid = trim.new_block(tint=stone_tint(), ao=0.72)
            F.box(trim, ua, ub, y1 - 0.06, y1, -depth, 0.03, "VH_Ashlar", bid, skip=("top",))
            bid = trim.new_block(tint=stone_tint())
            vs, made = F.box(trim, ua - 0.1, ub + 0.1, y0 - 0.14, y0, -depth, 0.11, "VH_Ashlar", bid)
            eroded_bevel(trim, list(made["top"].edges) + [e for e in made["s2"].edges if e not in made["top"].edges], 0.014, 2)
            self.fdrip(F, ua - 0.1, ub + 0.1, y0 - 0.14, 1.9, 0.5)
            for u in (ua - 0.05, ub + 0.05):
                self.fdrip(F, u - 0.12, u + 0.12, y0 - 0.14, 2.4, 0.95, soft=0.1)
            if lintel:
                bid = trim.new_block(tint=stone_tint())
                vs, made = F.box(trim, ua - 0.15 + .005, ub + 0.15 - .005, y1 + .005, lt - .005, 0.0, 0.075, "VH_Ashlar", bid, skip=("s0",))
                eroded_bevel(trim, list(made["s2"].edges), 0.02, 2, seg_len=0.2)
            fd = -depth + 0.02
            t = 0.05
            for (u0, u1, a, b) in ((ua, ua + t, y0, y1), (ub - t, ub, y0, y1), (ua, ub, y0, y0 + t), (ua, ub, y1 - t, y1)):
                F.box(metal, u0, u1, a, b, fd - 0.04, fd + 0.03, "VH_Steel")
            um = (ua + ub) / 2
            F.box(metal, um - 0.018, um + 0.018, y0, y1, fd - 0.03, fd + 0.02, "VH_Steel")
            rows = 3 if (y1 - y0) > 1.2 else 2
            for k in range(1, rows):
                yy = lerp(y0, y1, k / rows)
                F.box(metal, ua, ub, yy - 0.016, yy + 0.016, fd - 0.03, fd + 0.02, "VH_Steel")
            F.box(self.glass, ua + t * 0.5, ub - t * 0.5, y0 + t * 0.5, y1 - t * 0.5, fd - 0.02, fd - 0.01, "WS_Glass",
                  skip=("s0", "s1", "s3", "top", "bottom"))
            if kind == "bars":
                nbar = max(3, int((ub - ua) / 0.15))
                for k in range(nbar):
                    u = lerp(ua + 0.08, ub - 0.08, k / (nbar - 1))
                    metal.cyl(F.P(u, y0 - 0.02, -0.11), F.P(u, y1 + 0.02, -0.11), 0.014, "VH_Steel", 8)
                for yy in (lerp(y0, y1, 0.2), lerp(y0, y1, 0.8)):
                    F.box(metal, ua - 0.02, ub + 0.02, yy - 0.022, yy + 0.022, -0.125, -0.1, "VH_Steel")
            elif kind == "shutters":
                # steel louvred shutters folded open against the wall either side
                for sgn, uu in ((-1, ua), (1, ub)):
                    w = (ub - ua) / 2
                    u0, u1 = sorted((uu + sgn * 0.04, uu + sgn * (w + 0.04)))
                    F.box(metal, u0, u1, y0, y1, 0.07, 0.1, "WS_PaintTeal")
                    if self.lod == 0:
                        n = int((y1 - y0) / 0.09)
                        for k in range(n):
                            yy = y0 + 0.06 + k * 0.09
                            F.box(metal, u0 + 0.04, u1 - 0.04, yy, yy + 0.05, 0.1, 0.115, "WS_PaintTeal")
            if self.lod == 0:
                rr = drng(face, round(ua, 2), round(y0, 2))
                F.box(self.sand, ua + rr.uniform(0.0, 0.1), ub - rr.uniform(0.0, 0.1), y0, y0 + rr.uniform(0.008, 0.018),
                      -depth + 0.05, 0.02, "VH_Sand", skip=("bottom",))
        self.later.append(build)

    def portal(self, face, uc, width, head, kind="double", transom=0.42, depth=0.4, arch=True, door_mat="VH_DoorSteel"):
        """Door in a stone surround: alternating jamb stones, flat arch (or lintel) in the course above the transom,
        leaves at the back of the reveal. kind: double (riveted steel), single (painted panel door), glazed (shop door)."""
        F = self.faces[face][0]
        hw = width / 2
        jw = 0.14
        top = head + transom
        lt = top + 0.42
        self.holes[face] += [(uc - hw - jw, uc + hw + jw, BASE, top), (uc - hw - jw - 0.12, uc + hw + jw + 0.12, top, lt)]
        self.rec.setdefault("recesses", []).append({"face": face, "u": [uc - hw, uc + hw], "depth": depth, "top": top})

        def build():
            trim, metal, pod = self.trim, self.metal, self.pod
            jy = [BASE] + [c for c in self.courses if BASE < c < top] + [top]
            for side in (-1, 1):
                for ci, (y0, y1) in enumerate(zip(jy, jy[1:])):
                    wide = ci % 2 == 0
                    u0, u1 = sorted((uc + side * hw, uc + side * (hw + jw + (0.1 if wide else 0.0))))
                    bid = trim.new_block(tint=stone_tint(), erode=0.006 + 0.008 * block_wear(y0))
                    vs, made = F.box(trim, u0 + .004, u1 - .004, y0 + .005, y1 - .005, -depth, 0.1 + (0.02 if wide else 0), "VH_Ashlar", bid,
                                     skip=("s0",))
                    edges = [e for e in {e for f in made.values() for e in f.edges} if max(F.n.dot(v.co - F.o) for v in e.verts) > -depth + 0.02]
                    eroded_bevel(trim, edges, self.L.uniform(0.014, 0.024), 2)
            # lintel: flat arch with keystone, or a single long stone
            if arch:
                n = 5
                xs = [lerp(uc - hw - jw - 0.12, uc + hw + jw + 0.12, i / n) for i in range(n + 1)]
                for i, (a, b) in enumerate(zip(xs, xs[1:])):
                    key = i == n // 2
                    y1 = lt + (0.08 if key else 0.0)
                    bid = trim.new_block(tint=stone_tint())
                    splay = 0.06 * ((a + b) / 2 - uc) / max(hw, 0.3)
                    c = [F.P(a + .005 + splay * 0.3, top, -depth), F.P(b - .005 + splay * 0.3, top, -depth),
                         F.P(b - .005 + splay * 0.3, top, 0.12 if key else 0.09), F.P(a + .005 + splay * 0.3, top, 0.12 if key else 0.09),
                         F.P(a + .005, y1, -depth), F.P(b - .005, y1, -depth), F.P(b - .005, y1, 0.12 if key else 0.09), F.P(a + .005, y1, 0.12 if key else 0.09)]
                    vs, made = trim.hexa(c, "VH_Ashlar", bid, skip=("s0",))
                    eroded_bevel(trim, [e for e in {e for f in made.values() for e in f.edges} if max(F.n.dot(v.co - F.o) for v in e.verts) > -depth + 0.02],
                                 self.L.uniform(0.012, 0.02), 2, seg_len=0.2)
            else:
                bid = trim.new_block(tint=stone_tint())
                vs, made = F.box(trim, uc - hw - jw - 0.12, uc + hw + jw + 0.12, top + .005, lt - .005, -depth, 0.09, "VH_Ashlar", bid, skip=("s0",))
                eroded_bevel(trim, list(made["s2"].edges) + list(made["bottom"].edges), 0.018, 2, seg_len=0.2)
            self.fdrip(F, uc - hw - 0.3, uc + hw + 0.3, top, 1.5, 0.55, soft=0.2)
            # reveal floor / threshold
            bid = pod.new_block(tint=stone_tint("rough"))
            vs, made = F.box(pod, uc - hw, uc + hw, BASE - 0.1, BASE + 0.015, -depth, 0.02, "VH_PodiumSlab", bid, skip=("bottom",))
            eroded_bevel(pod, list(made["top"].edges), 0.008, 2, seg_len=0.2)
            DZ = -depth + 0.04
            # frame
            for u0, u1, y0, y1 in ((uc - hw, uc - hw + 0.08, BASE, top), (uc + hw - 0.08, uc + hw, BASE, top), (uc - hw, uc + hw, top - 0.08, top),
                                   (uc - hw, uc + hw, head - 0.04, head + 0.04)):
                F.box(metal, u0, u1, y0, y1, DZ - 0.05, DZ + 0.09, "VH_Steel")
            # transom: glass over a steel grille
            if transom > 0.05:
                F.box(self.glass, uc - hw + 0.08, uc + hw - 0.08, head + 0.04, top - 0.08, DZ - 0.02, DZ - 0.01, "WS_Glass",
                      skip=("s0", "s1", "s3", "top", "bottom"))
                nb = max(4, int(width / 0.16))
                for i in range(nb):
                    u = lerp(uc - hw + 0.14, uc + hw - 0.14, i / (nb - 1))
                    metal.cyl(F.P(u, head + 0.04, DZ + 0.03), F.P(u, top - 0.08, DZ + 0.03), 0.011, "VH_Steel", 6)
            y0, y1 = BASE + 0.02, head - 0.04
            leaves = [(uc - hw + 0.08, uc - 0.004), (uc + 0.004, uc + hw - 0.08)] if kind in ("double", "glazed_double") else [(uc - hw + 0.08, uc + hw - 0.08)]
            for li, (xa, xb) in enumerate(leaves):
                if kind in ("glazed", "glazed_double"):
                    for (u0, u1, a, b) in ((xa, xa + 0.09, y0, y1), (xb - 0.09, xb, y0, y1), (xa, xb, y0, y0 + 0.42), (xa, xb, y1 - 0.1, y1),
                                           (xa, xb, 1.55, 1.6)):
                        F.box(metal, u0, u1, a, b, DZ - 0.02, DZ + 0.05, door_mat)
                    F.box(self.glass, xa + 0.09, xb - 0.09, y0 + 0.42, y1 - 0.1, DZ, DZ + 0.01, "WS_Glass", skip=("s0", "s1", "s3", "top", "bottom"))
                    F.box(metal, xa + 0.09, xb - 0.09, y0 + 0.08, y0 + 0.3, DZ + 0.05, DZ + 0.06, "VH_Bronze")
                else:
                    F.box(metal, xa, xb, y0, y1, DZ - 0.02, DZ + 0.05, door_mat)
                    # raised stiles/rails
                    for (u0, u1, a, b) in ((xa, xa + 0.1, y0, y1), (xb - 0.1, xb, y0, y1), (xa, xb, y0, y0 + 0.12), (xa, xb, y1 - 0.12, y1),
                                           (xa, xb, 1.28, 1.36), (xa, xb, 2.2, 2.28)):
                        F.box(metal, u0, u1, a, b, DZ + 0.05, DZ + 0.072, door_mat)
                    F.box(metal, xa + 0.12, xb - 0.12, y0 + 0.13, y0 + 0.36, DZ + 0.05, DZ + 0.062, "VH_Bronze" if kind == "double" else "VH_Steel")
                    if self.lod == 0 and kind == "double":
                        for (u0, u1) in ((xa, xa + 0.1), (xb - 0.1, xb)):
                            y = y0 + 0.08
                            while y < y1 - 0.05:
                                metal.sphere(F.P((u0 + u1) / 2, y, DZ + 0.072), 0.011, "VH_Steel", 6, hemi_axis=tuple(F.n))
                                y += 0.18
                    if kind == "double":
                        hx = xb if li == 0 else xa
                        for hy in (y0 + 0.5, (y0 + y1) / 2, y1 - 0.45):
                            h0, h1 = sorted((hx, hx + (0.6 if li == 1 else -0.6)))
                            F.box(metal, h0, h1, hy - 0.04, hy + 0.04, DZ + 0.072, DZ + 0.085, "VH_Steel")
                # pull handle
                hu = (xb - 0.16) if (li == 0 and len(leaves) == 2) else (xa + 0.16 if len(leaves) == 2 else xb - 0.14)
                metal.cyl(F.P(hu, 1.0, DZ + 0.12), F.P(hu, 1.45, DZ + 0.12), 0.016, "VH_Bronze", 8)
                for hy in (1.04, 1.41):
                    metal.cyl(F.P(hu, hy, DZ + 0.05), F.P(hu, hy, DZ + 0.13), 0.012, "VH_Bronze", 6)
            F.box(metal, uc - hw, uc + hw, BASE + 0.005, BASE + 0.02, DZ - 0.02, DZ + 0.3, "VH_Bronze")
        self.later.append(build)

    def shutter(self, face, u0, u1, top=3.57, depth=0.35, note="", open=False):
        """Workshop opening: stone reveals with steel guide angles, painted steel beam lintel, roller box, closed
        slatted curtain with bottom bar, handles and a padlocked hasp. open=True (1 Oct 2026, the walk-in Salvage
        shop): the curtain is rolled up into the box, its bottom bar and pull handles hang just under it."""
        F = self.faces[face][0]
        lt = top + 0.42
        self.holes[face] += [(u0, u1, BASE, top), (u0 - 0.2, u1 + 0.2, top, lt)]
        self.rec.setdefault("recesses", []).append({"face": face, "u": [u0, u1], "depth": 0.12, "top": top})

        def build():
            trim, metal = self.trim, self.metal
            jy = [BASE] + [c for c in self.courses if BASE < c < top] + [top]
            for (a, b) in ((u0 - 0.001, u0 + 0.07), (u1 - 0.07, u1 + 0.001)):
                for (y0, y1) in zip(jy, jy[1:]):
                    bid = trim.new_block(tint=stone_tint(), ao=0.85, erode=0.006 + 0.008 * block_wear(y0))
                    vs, made = F.box(trim, a, b, y0 + .004, y1 - .004, -depth, 0.03, "VH_Ashlar", bid, skip=("bottom", "top"))
            # steel beam lintel (I-section face) and bearing plates
            F.box(metal, u0 - 0.2, u1 + 0.2, top, top + 0.3, -depth, 0.07, "VH_PaintedSteel")
            F.box(metal, u0 - 0.2, u1 + 0.2, top, top + 0.03, 0.07, 0.12, "VH_PaintedSteel")
            F.box(metal, u0 - 0.2, u1 + 0.2, top + 0.27, top + 0.3, 0.07, 0.12, "VH_PaintedSteel")
            bid = trim.new_block(tint=stone_tint())
            F.box(trim, u0 - 0.2, u1 + 0.2, top + 0.3 + .005, lt - .005, 0.0, 0.07, "VH_Ashlar", bid, skip=("s0",))
            if self.lod == 0:
                x = u0 - 0.15
                while x < u1 + 0.15:
                    for yy in (top + 0.06, top + 0.24):
                        metal.sphere(F.P(x, yy, 0.07), 0.013, "VH_Steel", 6, hemi_axis=tuple(F.n))
                    x += 0.25
            self.fdrip(F, u0 - 0.2, u1 + 0.2, top, 1.2, 0.8, "rust", soft=0.15)
            # guides
            for a in (u0 + 0.07, u1 - 0.07):
                F.box(metal, a - 0.03, a + 0.03, BASE, top, -0.2, -0.08, "VH_Steel")
            # roller box
            F.box(metal, u0 + 0.05, u1 - 0.05, top - 0.42, top, -0.3, -0.06, "VH_PaintedSteel")
            # curtain: corrugated slats
            DZ = -0.14
            n = int((top - 0.42 - BASE - 0.12) / 0.085)
            if open:
                # rolled up: two slats still showing under the box, the bottom bar and its pull handles below them
                yb = top - 0.42 - 2 * 0.085
                for k in range(2):
                    y = yb + k * 0.085
                    c = [F.P(u0 + 0.1, y, DZ), F.P(u1 - 0.1, y, DZ), F.P(u1 - 0.1, y, DZ + 0.02), F.P(u0 + 0.1, y, DZ + 0.02),
                         F.P(u0 + 0.1, y + 0.085, DZ), F.P(u1 - 0.1, y + 0.085, DZ), F.P(u1 - 0.1, y + 0.085, DZ + 0.035), F.P(u0 + 0.1, y + 0.085, DZ + 0.035)]
                    metal.hexa(c, "WS_Shutter")
                F.box(metal, u0 + 0.1, u1 - 0.1, yb - 0.11, yb, DZ - 0.01, DZ + 0.06, "VH_Steel")
                for a in (u0 + 0.5, u1 - 0.5):
                    metal.cyl(F.P(a, yb - 0.11, DZ + 0.02), F.P(a, yb - 0.3, DZ + 0.02), 0.008, "VH_Steel", 6)
                    metal.cyl(F.P(a - 0.06, yb - 0.3, DZ + 0.02), F.P(a + 0.06, yb - 0.3, DZ + 0.02), 0.014, "VH_Steel", 6)
                self.fdrip(F, u0 + 0.1, u1 - 0.1, top - 0.42, 0.5, 0.3, "rust", soft=0.2)
                bid = self.pod.new_block(tint=stone_tint("rough"))
                F.box(self.pod, u0 + 0.07, u1 - 0.07, BASE - 0.1, BASE + 0.012, -depth, 0.02, "VH_PodiumSlab", bid, skip=("bottom",))
                return
            for k in range(n):
                y = BASE + 0.12 + k * 0.085
                c = [F.P(u0 + 0.1, y, DZ), F.P(u1 - 0.1, y, DZ), F.P(u1 - 0.1, y, DZ + 0.02), F.P(u0 + 0.1, y, DZ + 0.02),
                     F.P(u0 + 0.1, y + 0.085, DZ), F.P(u1 - 0.1, y + 0.085, DZ), F.P(u1 - 0.1, y + 0.085, DZ + 0.035), F.P(u0 + 0.1, y + 0.085, DZ + 0.035)]
                metal.hexa(c, "WS_Shutter")
            F.box(metal, u0 + 0.1, u1 - 0.1, BASE + 0.01, BASE + 0.12, DZ - 0.01, DZ + 0.06, "VH_Steel")
            for a in (u0 + 0.5, u1 - 0.5):
                metal.cyl(F.P(a - 0.1, BASE + 0.2, DZ + 0.09), F.P(a + 0.1, BASE + 0.2, DZ + 0.09), 0.014, "VH_Steel", 6)
            F.box(metal, (u0 + u1) / 2 - 0.05, (u0 + u1) / 2 + 0.05, BASE + 0.02, BASE + 0.2, DZ + 0.06, DZ + 0.08, "VH_Steel")
            F.box(metal, (u0 + u1) / 2 - 0.035, (u0 + u1) / 2 + 0.035, BASE + 0.06, BASE + 0.13, DZ + 0.08, DZ + 0.11, "VH_Brass")
            self.fdrip(F, u0 + 0.1, u1 - 0.1, top - 0.42, 2.5, 0.35, "rust", soft=0.2)
            bid = self.pod.new_block(tint=stone_tint("rough"))
            F.box(self.pod, u0 + 0.07, u1 - 0.07, BASE - 0.1, BASE + 0.012, -depth, 0.02, "VH_PodiumSlab", bid, skip=("bottom",))
        self.later.append(build)

    # ------------------------------------------------------------------ awnings, lamps, signs, services
    def awning(self, u0, u1, y, proj=1.4, drop=0.45, valance=0.24, stripes=True):
        F = self.FRONT
        canvas, metal = self.canvas, self.metal
        nx = max(6, int((u1 - u0) / 0.25)) if self.lod == 0 else 4
        nz = 6 if self.lod == 0 else 2
        bm = canvas.bm
        mi = canvas.mi("WS_Canvas")
        grid = []
        for j in range(nz + 1):
            t = j / nz
            row = []
            for i in range(nx + 1):
                s = i / nx
                u = lerp(u0, u1, s)
                bay = (u - u0) / ((u1 - u0) / max(1, round((u1 - u0) / 1.2)))
                sag = 0.05 * math.sin(math.pi * (bay % 1.0)) * math.sin(math.pi * t)
                yy = y - drop * t - sag
                zz = 0.1 + (proj - 0.1) * t
                row.append(bm.verts.new(Vector((u, yy, zz))))
            grid.append(row)
        # valance with a scalloped hem
        vrow_top = grid[-1]
        vrow = []
        for i in range(nx + 1):
            u = lerp(u0, u1, i / nx)
            hem = valance - (0.05 * abs(math.sin(math.pi * i / 2)) if self.lod == 0 else 0.0)
            vrow.append(bm.verts.new(Vector((u, vrow_top[i].co.y - hem, proj + 0.01))))
        for rows in (grid, [vrow_top, vrow]):
            for j in range(len(rows) - 1):
                for i in range(nx):
                    f = bm.faces.new([rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]])
                    f.material_index = mi
        # arms: tubes from the wall to the front rail, and the rail + wall bar
        n_arms = max(2, round((u1 - u0) / 1.2) + 1)
        for k in range(n_arms):
            u = lerp(u0 + 0.05, u1 - 0.05, k / (n_arms - 1))
            metal.tube([(u, y - 0.95, 0.05), (u, y - drop - 0.02, proj - 0.02)], 0.018, "VH_Steel", 8)
            metal.box((u - 0.05, y - 1.02, 0.0), (u + 0.05, y - 0.88, 0.03), "VH_Steel")
            self.fdrip(F, u - 0.08, u + 0.08, y - 0.95, 1.3, 0.8, "rust", soft=0.06)
        metal.cyl((u0, y - drop - 0.02, proj - 0.02), (u1, y - drop - 0.02, proj - 0.02), 0.022, "VH_Steel", 8)
        metal.box((u0 - 0.05, y - 0.03, 0.0), (u1 + 0.05, y + 0.06, 0.12), "VH_Steel")
        self.fdrip(F, u0, u1, y - 0.03, 1.0, 0.5, "rust", soft=0.2)
        self.rec["awning"] = {"u": [u0, u1], "y": y, "proj": proj}

    def lamp(self, face, u, y, name):
        F = self.faces[face][0]
        p = F.P(u, y, 0.065)
        yaw = {"front": 0, "rear": 180, "right": 90, "left": -90}[face]
        self.rec["mounts"].append({"name": name, "prefab": "PH_WallLamp", "pos": [p.x, p.y, p.z], "yaw": yaw, "light": True})
        self.fdrip(F, u - 0.08, u + 0.08, y - 0.1, 1.3, 0.8, "rust", soft=0.07)

    def fitting(self, face, u, y, prefab, name, off=0.065):
        F = self.faces[face][0]
        p = F.P(u, y, off)
        yaw = {"front": 0, "rear": 180, "right": 90, "left": -90}[face]
        self.rec["mounts"].append({"name": name, "prefab": prefab, "pos": [p.x, p.y, p.z], "yaw": yaw})

    def sign(self, text, u, y, w, h, style="box", extra=None):
        c = self.FRONT.P(u, y, 0.062)
        rec = {"text": text, "centre": [c.x, c.y, c.z], "size": [w, h], "facing": [0, 0, 1], "style": style}
        if extra:
            rec.update(extra)
        self.rec["signs"].append(rec)
        self.fdrip(self.FRONT, u - w / 2, u + w / 2, y - h / 2 - 0.02, 1.2, 0.55, "rust", soft=0.15)

    def conduit(self, pts, r=0.022):
        self.metal.tube(pts, r, "VH_Steel", clamps=0.6)

    def downpipe(self, face, u, top, name="downpipe"):
        F = self.faces[face][0]
        a = F.P(u, top, 0.14)
        b = F.P(u, BASE + 0.25, 0.14)
        c = F.P(u, BASE + 0.05, 0.32)
        self.metal.tube([a, b, c], 0.055, "VH_Steel", 10, clamps=1.3)
        self.metal.box(tuple(F.P(u - 0.15, top, 0.05)), tuple(F.P(u + 0.15, top + 0.3, 0.3)), "VH_Steel") if False else None
        hb = [F.P(u - 0.14, top, 0.04), F.P(u + 0.14, top, 0.04), F.P(u + 0.14, top, 0.3), F.P(u - 0.14, top, 0.3),
              F.P(u - 0.16, top + 0.28, 0.04), F.P(u + 0.16, top + 0.28, 0.04), F.P(u + 0.16, top + 0.28, 0.32), F.P(u - 0.16, top + 0.28, 0.32)]
        self.metal.hexa(hb, "VH_Steel")
        self.fdrip(F, u - 0.25, u + 0.25, top + 0.3, top - BASE, 0.6, "grime", soft=0.15)
        self.fdrip(F, u - 0.15, u + 0.15, top + 0.3, 1.5, 0.7, "rust", soft=0.1)

    def junction_box(self, face, u, y):
        F = self.faces[face][0]
        F.box(self.metal, u - 0.15, u + 0.15, y - 0.2, y + 0.2, 0.062, 0.2, "VH_PaintedSteel")
        F.box(self.metal, u - 0.16, u + 0.16, y + 0.18, y + 0.22, 0.055, 0.21, "VH_PaintedSteel")
        self.fdrip(F, u - 0.12, u + 0.12, y - 0.2, 1.0, 0.6, "rust", soft=0.08)

    # ------------------------------------------------------------------ porch + step (match the kept colliders)
    def porch(self):
        pod = self.pod
        # slab deck: x -3.88..3.88, z 0..PORCH, top 0.5 (root 18.1 m from the axis; porch collider front at 14.5 m); edge course facing the avenue and the alleys
        z = 0.0
        row = 0
        while z < PORCH - 1e-3:
            dz = min(0.78, PORCH - z)
            x = -3.88 + (0.35 if row % 2 else 0.0)
            first = True
            xs = [-3.88]
            while x < 3.88 - 1e-3:
                ln = self.L.uniform(0.75, 1.15)
                if first and row % 2:
                    ln = 0.35 + 0.4 * self.L.random()
                    x = -3.88
                first = False
                x1 = min(3.88, x + ln)
                if 3.88 - x1 < 0.3:
                    x1 = 3.88
                bid = pod.new_block(tint=stone_tint("rough"))
                vs, made = pod.box((x + .004, BASE - 0.12, z + .004), (x1 - .004, BASE, z + dz - .004), "VH_PodiumSlab", bid, skip=("bottom",))
                eroded_bevel(pod, list(made["top"].edges), self.L.uniform(0.006, 0.014), 2, seg_len=0.2)
                x = x1
            z += dz
            row += 1
        PF = Frame((0, 0, PORCH), (1, 0, 0), (0, 0, 1))
        fill_wall(pod, PF, -3.88, 3.88, [0.0, 0.25, BASE - 0.12], [], mat="VH_AshlarRough", lmin=0.7, lmax=1.3, key="porch_f",
                  depth=0.04)
        for sx in (-1, 1):
            PS = Frame((sx * 3.88, 0, 0), (0, 0, sx * -1) if sx > 0 else (0, 0, 1), (sx, 0, 0))
            ua, ub = (-3.5, 0.0) if sx > 0 else (0.0, 3.5)
            if sx > 0:
                ua, ub = -3.5, 0.0
                PS = Frame((3.88, 0, 0), (0, 0, -1), (1, 0, 0))
                fill_wall(pod, PS, -PORCH, 0.0, [0.0, 0.25, BASE - 0.12], [], mat="VH_AshlarRough", lmin=0.7, lmax=1.3, key="porch_r", depth=0.04)
            else:
                PS = Frame((-3.88, 0, 0), (0, 0, 1), (-1, 0, 0))
                fill_wall(pod, PS, 0.0, PORCH, [0.0, 0.25, BASE - 0.12], [], mat="VH_AshlarRough", lmin=0.7, lmax=1.3, key="porch_l", depth=0.04)
        # the step (collider: x +-2.1, z PORCH..PORCH+0.8, top 0.25)
        x = -2.1
        while x < 2.1 - 1e-3:
            x1 = min(2.1, x + self.L.uniform(0.9, 1.3))
            if 2.1 - x1 < 0.4:
                x1 = 2.1
            bid = pod.new_block(tint=stone_tint("rough"))
            vs, made = pod.box((x + .004, 0.0, PORCH), (x1 - .004, 0.25, PORCH + 0.8), "VH_PodiumSlab", bid, skip=("bottom",))
            eroded_bevel(pod, [e for e in made["top"].edges] + [e for e in made["s2"].edges], 0.018, 2, seg_len=0.2)
            x = x1
        # sheltered sand against the facade and in the step corners (LOD0)
        if self.lod == 0:
            for (a, b) in ((-3.7, -0.5), (0.6, 3.7)):
                self.drift(a, b, 0.0, key=("drift", a))
            for sx in (-1, 1):
                self.sand.box((sx * 2.1 - 0.35 if sx > 0 else -2.1, 0.0, 3.5), (2.1 + 0.35 if sx > 0 else -2.1 + 0.35 * 0, 0.06, 3.8), "VH_Sand") if False else None

    def drift(self, a, b, z0, key, width=0.28, height=0.05, n=12):
        rr = drng(*key) if isinstance(key, tuple) else drng(key)
        bm = self.sand.bm
        mi = self.sand.mi("VH_Sand")
        rows = []
        for i in range(n + 1):
            u = lerp(a, b, i / n)
            env = math.sin(math.pi * i / n) ** 0.6
            h = height * env * rr.uniform(0.6, 1.2)
            w = width * env * rr.uniform(0.7, 1.2) + 0.02
            rows.append([bm.verts.new(Vector((u, BASE - 0.005, z0 + 0.01))), bm.verts.new(Vector((u, BASE + h, z0 + 0.02 + w * 0.3))),
                         bm.verts.new(Vector((u, BASE - 0.005, z0 + 0.02 + w)))])
        for i in range(n):
            for k in range(2):
                f = bm.faces.new([rows[i][k], rows[i + 1][k], rows[i + 1][k + 1], rows[i][k + 1]])
                f.material_index = mi
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

    # ------------------------------------------------------------------ roof furniture
    def roof_hatch_and_ac(self, x, z):
        r = self.roof_y
        self.roof.box((x - 0.45, r, z - 0.45), (x + 0.45, r + 0.35, z + 0.45), "VH_PaintedSteel")
        self.roof.box((x - 0.5, r + 0.35, z - 0.5), (x + 0.5, r + 0.4, z + 0.5), "VH_Steel")
        self.rec["mounts"].append({"name": "Roof air conditioner", "prefab": "PH_AirconRusted", "pos": [x + 1.4, r, z - 0.6], "yaw": 180})

    def mast(self, x, z, h=3.4):
        r = self.roof_y
        m = self.metal
        m.cyl((x, r, z), (x, r + h, z), 0.05, "VH_Steel", 10)
        m.box((x - 0.3, r, z - 0.3), (x + 0.3, r + 0.05, z + 0.3), "VH_Steel")
        for k in range(1, 4):
            yy = r + h * k / 4
            m.cyl((x - 0.35, yy, z), (x + 0.35, yy, z), 0.015, "VH_Steel", 6)
        m.cyl((x, r + h, z), (x, r + h + 1.2, z), 0.012, "VH_Steel", 6)
        m.cyl((x + 0.2, r + h * 0.75, z), (x + 0.2, r + h * 0.75 + 0.9, z), 0.008, "VH_Steel", 6)
        # dish
        c = Vector((x - 0.35, r + h * 0.55, z + 0.25))
        m.sphere(tuple(c), 0.32, "VH_PaintedSteel", 12, hemi_axis=(-0.5, 0.2, 0.8))
        m.cyl((x, r + h * 0.55, z), tuple(c), 0.02, "VH_Steel", 6)
        # guy wires
        for dx, dz in ((1.6, 1.4), (-1.6, 1.4), (0.0, -1.8)):
            m.cyl((x, r + h * 0.8, z), (x + dx, r + 0.05, z + dz), 0.005, "VH_Steel", 4)
        self.rec["beacon"] = [x, r + h + 1.25, z]

    def water_tank(self, x, z, rad=0.85, h=1.5):
        r = self.roof_y
        m = self.metal
        for dx, dz in ((-0.6, -0.6), (0.6, -0.6), (0.6, 0.6), (-0.6, 0.6)):
            m.box((x + dx - 0.05, r, z + dz - 0.05), (x + dx + 0.05, r + 0.7, z + dz + 0.05), "VH_Steel")
        m.box((x - 0.8, r + 0.7, z - 0.8), (x + 0.8, r + 0.78, z + 0.8), "VH_Steel")
        m.cyl((x, r + 0.78, z), (x, r + 0.78 + h, z), rad, "WS_PaintTeal", 20)
        for yy in (r + 1.05, r + 1.6, r + 2.1):
            m.cyl((x, yy - 0.02, z), (x, yy + 0.02, z), rad + 0.015, "VH_Steel", 20)
        m.sphere((x, r + 0.78 + h, z), rad * 0.98, "WS_PaintTeal", 16, hemi_axis=(0, 1, 0))
        m.tube([(x + rad, r + 1.0, z), (x + rad + 0.3, r + 1.0, z), (x + rad + 0.3, r + 0.2, z), (x + rad + 0.3, r + 0.2, z + 1.2)], 0.04, "VH_Steel")
        self.rec["notes"].append("roof water tank")

    # ------------------------------------------------------------------ colliders
    def colliders(self):
        c = self.rec["colliders"]
        top = self.top_y if not self.gable else self.gable["eave"] + 0.2
        rec_depth = max([r["depth"] for r in self.rec.get("recesses", [])] + [0.0])
        # body behind the recesses, then front piers between openings (so doorway recesses can be stepped into)
        c.append({"name": "COL_Body", "center": [0, (BASE + top) / 2, -D / 2 - rec_depth / 2 + 0.02], "size": [2 * HW + 0.18, top - BASE, D - rec_depth + 0.14]})
        spans = [(-HW - 0.09, HW + 0.09)]
        for r in self.rec.get("recesses", []):
            if r["face"] != "front":
                continue
            a, b = r["u"]
            new = []
            for s0, s1 in spans:
                if b <= s0 or a >= s1:
                    new.append((s0, s1)); continue
                if a > s0: new.append((s0, a))
                if b < s1: new.append((b, s1))
            spans = new
        for i, (s0, s1) in enumerate(spans):
            if s1 - s0 < 0.02:
                continue
            c.append({"name": f"COL_FrontPier_{i}", "center": [(s0 + s1) / 2, (BASE + top) / 2, (0.09 - rec_depth) / 2], "size": [s1 - s0, top - BASE, rec_depth + 0.09]})
        for r in self.rec.get("recesses", []):
            if r["face"] == "front":
                a, b = r["u"]
                c.append({"name": f"COL_OverDoor_{round(a, 2)}", "center": [(a + b) / 2, (r["top"] + top) / 2, (0.09 - rec_depth) / 2],
                          "size": [b - a, top - r["top"], rec_depth + 0.09]})
                c.append({"name": f"COL_Door_{round(a, 2)}", "center": [(a + b) / 2, (BASE + r["top"]) / 2, -r["depth"] + 0.02],
                          "size": [b - a, r["top"] - BASE, 0.08]})
        if self.gable:
            g = self.gable
            c.append({"name": "COL_Roof", "center": [0, (g["eave"] + g["ridge"]) / 2, -D / 2], "size": [2 * HW, g["ridge"] - g["eave"], D]})

    # ------------------------------------------------------------------ finish
    def scorch(self, face, ua, ub, top, height=2.2, strength=0.75):
        """Soot from an old fire above an opening (baked into the stone's vertex colour)."""
        F = self.faces[face][0]
        a, b = F.P(ua, 0, 0), F.P(ub, 0, 0)
        if abs(F.n.z) > 0.5:
            self.scars.plume((0, 0, F.n.z), a.z, a.x, b.x, top, height, strength)
        else:
            self.scars.plume((F.n.x, 0, 0), a.x, a.z, b.z, top, height, strength)

    def finish(self):
        for fn in self.later:
            fn()
        # scattered old impact clusters on the street face and the sides (more low down, where fighting was)
        top = self.gable["eave"] if self.gable else self.wall_top
        faces = [(self.FRONT, -HW, HW), (self.FRONT, -HW, HW), (self.RIGHT, 0.0, D), (self.LEFT, -D, 0.0)]
        scatter_impacts(self.scars, faces, 4, self.scar_rng, BASE + 0.3, min(4.5, top), 0.5, 1.3)
        scatter_impacts(self.scars, faces, 2, self.scar_rng, 4.5, top, 0.5, 1.1)
        self.colliders()
        parts = [self.mas, self.trim, self.pod, self.metal, self.glass, self.roof, self.canvas, self.sand, self.glow, self.clear]
        # walk-in interiors (1 Oct 2026, Salvage): extra parts as (part, build kwargs); they shade with the shell
        extra = getattr(self, "extra_parts", [])
        finalize_parts(parts + [p for p, _ in extra])
        ao = AOBaker(parts + [p for p, _ in extra], ground_y=0.0, samples=24 if self.lod == 0 else 10)
        objs = [self.mas.build(self.coll, ao=ao, drips=self.drips, ground_y=BASE, scars=self.scars),
                self.trim.build(self.coll, ao=ao, drips=self.drips, ground_y=BASE, scars=self.scars),
                self.pod.build(self.coll, ao=ao, drips=self.drips, ground_y=0.0, splash=0.22, scars=self.scars),
                self.metal.build(self.coll),
                self.roof.build(self.coll)]
        for p in (self.glass,):
            if len(p.bm.faces):
                objs.append(p.build(self.coll, flat=True))
        for p in (self.canvas, self.sand, self.glow, self.clear):
            if len(p.bm.faces):
                objs.append(p.build(self.coll))
        for p, kw in extra:
            if len(p.bm.faces):
                ob = p.build(self.coll, ao=ao if kw.pop("ao", True) else None, **kw)
                post = getattr(self, "post_build", None)
                if post:
                    post(p, ob)
                objs.append(ob)
        # two-sided canvas: duplicate faces reversed
        rec = self.rec
        rec["triangles"] = tri_count(objs)
        rec["objects"] = {o.name: sum(len(pl.vertices) - 2 for pl in o.data.polygons) for o in objs}
        rec["vertex_ao_rays"] = ao.rays
        rec["top"] = self.top_y
        return objs


# ====================================================================== the shops
def relay_works(lod):
    s = Shop("RelayWorks", lod, (1.05, 0.98, 0.9), 1801)
    s.shutter("front", -0.9, 2.3)
    s.portal("front", -2.2, 0.95, 3.15, kind="single", door_mat="WS_PaintRed", arch=False)
    for x in (-2.3, 0.0, 2.3):
        s.window("front", x - 0.475, x + 0.475, 5.50, 7.18, kind="plain")
    s.window("right", 3.0, 3.9, 5.50, 7.18, kind="bars")
    s.window("left", -3.9, -3.0, 5.50, 7.18, kind="bars")
    s.window("right", 4.55, 5.25, 1.89, 3.15, kind="bars")
    s.portal("rear", 1.2, 0.95, 3.15, kind="single", door_mat="VH_PaintedSteel", arch=False, transom=0.0)
    s.window("rear", -2.4, -1.4, 5.50, 7.18, kind="bars")
    s.window("rear", 1.0, 2.0, 5.50, 7.18, kind="bars")
    s.scorch("front", 1.825, 2.775, 7.18, 1.6, 0.8)          # upper north window burned out once
    s.walls()
    s.top()
    s.porch()
    s.lamp("front", -1.25, 3.3, "Lamp between door and shutter")
    s.lamp("front", 2.95, 3.3, "Lamp shutter north")
    s.lamp("rear", 1.2, 3.75, "Rear door lamp")
    s.sign("RELAY WORKS", 0.7, 4.41, 3.1, 0.66)
    s.junction_box("front", -1.25, 1.35)
    s.conduit([(-1.25, 1.55, 0.14), (-1.25, 3.05, 0.14)])
    s.conduit([(-1.1, 1.55, 0.14), (-1.1, 4.0, 0.14), (-0.9, 4.0, 0.14)])
    s.downpipe("right", 5.6, 7.65)
    s.roof_hatch_and_ac(-1.8, -4.8)
    s.mast(1.9, -3.4)
    s.fitting("right", 1.6, 5.2, "PH_SecurityLight", "Side security light")
    s.fitting("rear", -0.5, BASE, "PH_AirconRusted", "Rear air conditioner", off=0.35)
    s.fitting("left", -5.2, 1.5, "PH_PowerBox", "Side power box")
    return s


def air_water(lod):
    s = Shop("AirWater", lod, (1.09, 1.07, 1.03), 902)
    # the accepted Air + Water filter bank (29 Sep) stays mounted at local x -3.25..-0.55; keep that wall plain
    s.portal("front", 1.35, 1.6, 3.15, kind="double", arch=True)
    s.window("front", 0.8, 1.9, 5.50, 7.18, kind="bars")
    s.window("front", 2.45, 2.95, 5.92, 6.76, kind="plain", lintel=False)
    s.window("right", 2.4, 3.3, 5.50, 7.18, kind="bars")
    s.window("left", -5.2, -4.3, 5.50, 7.18, kind="bars")
    s.portal("rear", -1.5, 0.95, 3.15, kind="single", door_mat="VH_PaintedSteel", arch=False, transom=0.0)
    s.window("rear", 0.8, 1.8, 5.50, 7.18, kind="bars")
    s.walls()
    s.top()
    s.porch()
    s.lamp("front", 0.05, 3.2, "Door lamp south")
    s.lamp("front", 2.65, 3.2, "Door lamp north")
    s.lamp("rear", -1.5, 3.75, "Rear door lamp")
    s.sign("AIR + WATER", 1.35, 4.41, 2.6, 0.62)
    s.downpipe("left", -1.2, 7.65)
    s.water_tank(-1.4, -3.9)
    s.roof_hatch_and_ac(1.6, -5.4)
    s.fitting("right", 5.4, 1.5, "PH_PowerBox", "Side power box")
    s.fitting("rear", 2.6, BASE, "PH_AirconRusted", "Rear air conditioner", off=0.35)
    s.rec["notes"].append("filter bank zone local x -3.25..-0.55 left plain for the kept Air + Water filter fittings")
    return s


def tool_exchange(lod):
    """Sci-fi fabrication shop: glazed display alcove (nanofab bench, powered tool wall, servo arm, drone) lit by
    cyan LED strips; access-panel door; cyan status strip over the display."""
    s = Shop("ToolExchange", lod, (1.0, 0.96, 0.92), 3303, upper=[5.08, 5.50, 5.92], parapet=0.55)
    du0, du1, dy0, dy1 = -3.0, -0.2, 1.05, 3.57
    s.holes["front"] += [(du0, du1, dy0, dy1), (du0 - 0.2, du1 + 0.2, dy1, dy1 + 0.42)]
    s.portal("front", 1.55, 1.05, 3.15, kind="glazed", door_mat="VH_PaintedSteel", arch=False)
    s.window("right", 2.6, 3.5, 1.89, 3.15, kind="bars")
    s.portal("rear", 0.9, 0.95, 3.15, kind="single", door_mat="VH_PaintedSteel", arch=False, transom=0.0)
    s.window("rear", -2.2, -1.2, 1.89, 3.15, kind="bars")

    def display():
        F, trim, metal, glow = s.FRONT, s.trim, s.metal, s.glow
        # stall riser (stone under the glass) and deep steel-lined alcove
        bid = trim.new_block(tint=stone_tint())
        vs, made = F.box(trim, du0 - 0.1, du1 + 0.1, dy0 - 0.12, dy0, -0.3, 0.1, "VH_Ashlar", bid)
        eroded_bevel(trim, list(made["top"].edges), 0.014, 2)
        for (a, b) in ((du0 - 0.001, du0 + 0.07), (du1 - 0.07, du1 + 0.001)):
            for (y0, y1) in zip([dy0, 1.47, 1.89, 2.31, 2.73, 3.15], [1.47, 1.89, 2.31, 2.73, 3.15, dy1]):
                bid = trim.new_block(tint=stone_tint(), ao=0.85)
                F.box(trim, a, b, y0 + .004, y1 - .004, -0.3, 0.03, "VH_Ashlar", bid, skip=("bottom", "top"))
        F.box(metal, du0 - 0.2, du1 + 0.2, dy1, dy1 + 0.3, -0.3, 0.07, "VH_PaintedSteel")
        bid = trim.new_block(tint=stone_tint())
        F.box(trim, du0 - 0.2, du1 + 0.2, dy1 + 0.305, dy1 + 0.415, 0.0, 0.07, "VH_Ashlar", bid, skip=("s0",))
        AZ = -1.55       # alcove back wall
        F.box(metal, du0, du1, dy0, dy1, AZ - 0.05, AZ, "WS_PanelDark")                     # back wall
        F.box(metal, du0 - 0.05, du0, dy0, dy1, AZ, -0.3, "WS_PanelDark")                  # side walls
        F.box(metal, du1, du1 + 0.05, dy0, dy1, AZ, -0.3, "WS_PanelDark")
        F.box(metal, du0, du1, dy1 - 0.05, dy1, AZ, -0.3, "WS_PanelDark")                  # ceiling
        F.box(metal, du0, du1, dy0 - 0.05, dy0, AZ, -0.3, "WS_Deck")                        # floor
        # panel seams and cyan LED strips (ceiling front edge, back wall verticals, floor kick)
        if s.lod == 0:
            for k in range(1, 5):
                u = lerp(du0, du1, k / 5)
                F.box(metal, u - 0.006, u + 0.006, dy0, dy1 - 0.05, AZ, AZ + 0.012, "VH_Steel")
        F.box(glow, du0 + 0.05, du1 - 0.05, dy1 - 0.08, dy1 - 0.055, -0.45, -0.38, "WS_LedCyan")
        F.box(glow, du0 + 0.05, du1 - 0.05, dy0 + 0.02, dy0 + 0.035, AZ + 0.02, AZ + 0.04, "WS_LedCyan")
        for u in (du0 + 0.06, du1 - 0.06):
            F.box(glow, u - 0.012, u + 0.012, dy0 + 0.05, dy1 - 0.1, AZ + 0.01, AZ + 0.03, "WS_LedCyan")
        # glazing: steel frame, mullion, clear glass
        GZ = -0.26
        for (u0, u1, a, b) in ((du0, du0 + 0.06, dy0, dy1), (du1 - 0.06, du1, dy0, dy1), (du0, du1, dy0, dy0 + 0.06),
                               (du0, du1, dy1 - 0.06, dy1), ((du0 + du1) / 2 - 0.025, (du0 + du1) / 2 + 0.025, dy0, dy1)):
            F.box(metal, u0, u1, a, b, GZ - 0.03, GZ + 0.04, "VH_PaintedSteel")
        F.box(s.clear, du0 + 0.03, du1 - 0.03, dy0 + 0.03, dy1 - 0.03, GZ, GZ + 0.008, "WS_ClearGlass",
              skip=("s0", "s1", "s3", "top", "bottom"))
        # security grille rail and cyan status strip over the display, access panel by the door
        F.box(metal, du0 - 0.15, du1 + 0.15, dy1 + 0.43, dy1 + 0.5, 0.06, 0.16, "VH_Steel")
        F.box(glow, du0 - 0.05, du1 + 0.05, dy1 + 0.445, dy1 + 0.47, 0.16, 0.17, "WS_LedCyan")
        F.box(metal, 2.35, 2.6, 1.25, 1.65, 0.062, 0.12, "WS_PanelDark")
        F.box(glow, 2.38, 2.57, 1.45, 1.6, 0.12, 0.125, "WS_ScreenCyan")
        s.rec["display"] = {"u": [du0, du1], "y": [dy0, dy1], "back": AZ, "glass": GZ,
                            "props": [{"name": "nanofab_bench", "pos": [-2.0, dy0, -1.12], "yaw": 0, "size": [1.4, 1.35, 0.7]},
                                      {"name": "tool_wall", "pos": [-0.95, 2.35, AZ + 0.12], "yaw": 0, "size": [1.1, 0.8, 0.18]},
                                      {"name": "servo_arm", "pos": [-0.75, dy0, -0.95], "yaw": -35, "size": [0.5, 1.0, 0.5]},
                                      {"name": "drone_chassis", "pos": [-1.2, dy0, -0.55], "yaw": 25, "size": [0.5, 0.2, 0.5]},
                                      {"name": "plasma_cutter", "pos": [-2.55, dy0, -0.45], "yaw": 70, "size": [0.34, 0.18, 0.1]}],
                            "light": {"pos": [-1.6, dy1 - 0.2, -0.9], "target": [-1.6, dy0, -1.1]}}
        s.fdrip(F, du0 - 0.2, du1 + 0.2, dy1, 1.0, 0.7, "rust", soft=0.15)
    s.later.append(display)
    s.walls()
    s.top(cornice_h=0.4)
    s.porch()
    s.lamp("front", 0.55, 3.2, "Door lamp south")
    s.lamp("front", 2.85, 3.2, "Door lamp north")
    s.lamp("rear", 0.9, 3.75, "Rear door lamp")
    s.sign("TOOL EXCHANGE", -0.6, 4.41, 3.3, 0.62, extra={"accent": "cyan_strong"})
    s.conduit([(2.47, 1.65, 0.14), (2.47, 3.0, 0.14), (2.85, 3.0, 0.14)])
    s.downpipe("right", 5.6, 5.97)
    s.roof_hatch_and_ac(1.2, -4.6)
    s.mast(-2.2, -2.8, h=2.0)
    s.fitting("left", -3.5, 1.5, "PH_PowerBox", "Side power box")
    return s


def finery(lod):
    s = Shop("Finery", lod, (1.07, 1.0, 0.89), 1818, upper=UP + [8.02], parapet=0.55)
    s.portal("front", 0.0, 1.3, 3.15, kind="glazed_double", door_mat="WS_PaintTeal", arch=True)
    for x in (-2.15, 2.15):
        s.window("front", x - 0.72, x + 0.72, 1.47, 3.57, kind="plain")
    for x in (-2.15, 0.0, 2.15):
        s.window("front", x - 0.5, x + 0.5, 5.50, 7.18, kind="shutters")
    s.window("right", 2.4, 3.4, 5.50, 7.18, kind="shutters")
    s.window("left", -3.4, -2.4, 5.50, 7.18, kind="shutters")
    s.window("right", 4.4, 5.3, 1.89, 3.15, kind="bars")
    s.portal("rear", 0.0, 0.95, 3.15, kind="single", door_mat="VH_PaintedSteel", arch=False, transom=0.0)
    s.window("rear", -2.4, -1.4, 5.50, 7.18, kind="bars")
    s.window("rear", 1.4, 2.4, 5.50, 7.18, kind="bars")
    s.walls()
    s.top(cornice_h=0.48, dentils=True)
    s.porch()
    s.awning(-3.35, 3.35, 3.93, proj=1.55, drop=0.5)
    s.lamp("front", -0.98, 3.35, "Door lamp south")
    s.lamp("front", 0.98, 3.35, "Door lamp north")
    s.lamp("rear", 0.0, 3.75, "Rear door lamp")
    s.sign("FINERY", 0.0, 4.43, 2.2, 0.62)
    s.downpipe("left", -1.0, 8.07)
    s.roof_hatch_and_ac(-1.6, -4.9)
    s.fitting("rear", -2.8, BASE, "PH_AirconRusted", "Rear air conditioner", off=0.35)
    return s


def field_supply(lod):
    s = Shop("FieldSupply", lod, (0.96, 0.92, 0.86), 909, upper=[], gable={"eave": 5.08, "ridge": 8.1, "vent": True, "teal": False})
    s.shutter("front", -2.1, 0.9)
    s.portal("front", 2.2, 0.9, 3.15, kind="single", door_mat="WS_PaintTeal", arch=False)
    s.window("right", 2.2, 3.1, 1.89, 3.15, kind="bars")
    s.window("left", -4.6, -3.7, 1.89, 3.15, kind="bars")
    s.portal("rear", -1.6, 0.95, 3.15, kind="single", door_mat="VH_PaintedSteel", arch=False, transom=0.0)
    s.scorch("front", 1.65, 2.75, 3.57, 1.5, 0.7)             # door surround scorched
    s.scorch("left", -4.7, -3.6, 3.15, 1.8, 0.6)
    s.walls()
    s.gable_roof()
    s.porch()
    # loading canopy (steel sheet on tie rods) over the shutter
    F = s.FRONT
    F.box(s.metal, -2.35, 1.15, 3.97, 4.02, 0.05, 1.6, "VH_PaintedSteel")
    F.box(s.metal, -2.35, 1.15, 3.9, 3.97, 1.52, 1.6, "VH_PaintedSteel")
    for u in (-2.2, -0.6, 1.0):
        s.metal.cyl((u, 4.02, 1.5), (u, 4.8, 0.08), 0.012, "VH_Steel", 6)
        s.metal.box((u - 0.06, 4.72, 0.0), (u + 0.06, 4.86, 0.07), "VH_Steel")
    s.fdrip(F, -2.4, 1.2, 3.97, 1.0, 0.6, "rust", soft=0.15)
    s.lamp("front", 1.35, 3.25, "Lamp between shutter and door")
    s.lamp("front", 3.0, 3.25, "Door lamp north")
    s.lamp("rear", -1.6, 3.75, "Rear door lamp")
    s.sign("FIELD SUPPLY", 0.0, 6.05, 3.2, 0.66, extra={"on": "gable"})
    s.junction_box("front", 1.35, 1.35)
    s.conduit([(1.35, 1.55, 0.14), (1.35, 3.05, 0.14)])
    s.fitting("rear", 1.8, BASE, "PH_AirconRusted", "Rear air conditioner", off=0.35)
    s.fitting("right", 5.5, 1.5, "PH_PowerBox", "Side power box")
    return s


SHOPS = {"relay_works": relay_works, "air_water": air_water, "tool_exchange": tool_exchange, "finery": finery,
         "field_supply": field_supply}


def main():
    names = [a for a in sys.argv[sys.argv.index("--") + 1:]] if "--" in sys.argv else list(SHOPS)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for key in names:
        report = {"source": "art/hall_district_20260930/author_ward_shops.py", "date": "2026-09-30", "shop": key,
                  "units": "Unity metres local to the shop root (facade centre at paving level, +Z towards the avenue)", "lods": {}}
        for lod in (0, 1):
            shop = SHOPS[key](lod)
            objs = shop.finish()
            export(objs, OUT / f"{shop.name}_LOD{lod}.glb")
            report["lods"][f"LOD{lod}"] = {"triangles": shop.rec["triangles"], "objects": shop.rec["objects"]}
            if lod == 0:
                report.update({k: v for k, v in shop.rec.items() if k not in ("triangles", "objects")})
            print(f"{shop.name} LOD{lod}: {shop.rec['triangles']} triangles", flush=True)
        (OUT / f"{key}.json").write_text(json.dumps(report, indent=1))
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "shops-source.blend"))


if __name__ == "__main__":        # imported by art/north_avenue_20260930/author_north_shops.py
    main()
