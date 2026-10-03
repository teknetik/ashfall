"""Ward buildings that still needed replacing (3 October 2026), Blender 5.2 headless.

Carl (2 Oct 2026): "There are buildings in ward that need replacing too." Audit: AUDIT.md. Each building replaces a group
of the 26 Sep district retrofit (art/ward_retrofit_20260926) with modelled Ward masonry (art/ward_masonry_kit, via the
hall district's Shop class: dressed ashlar with quoins, eroded arrises, chips, ray-traced vertex occlusion, runoff/rust
channels and old battle damage for Athen Hill/Masonry Lit) plus blackened steel and, where the lore is technology,
restrained sci-fi composite work (Carl: "sci-fi, not a 90s woodworking shop").

Run:  $O/blender.sh author_buildings.py -- <key> [<key> ...]      keys: nanofab
Outputs: unity/AthenHill/Assets/AthenHill/Art/WardBuildings/Models/<Model>_LOD{0,1,2}.glb + <key>.json
(colliders, wall-lamp/prop mounts, extra lights, triangles) and art/ward_buildings_20261003/<key>-source.blend.

Coordinates: Unity metres local to the building root (origin = street-face centre at ground level, +Z = street side,
X along the facade, Y up). The root's world position/yaw live in layout.json.
"""
import bpy, bmesh, json, math, random, sys
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "art/ward_masonry_kit"))
sys.path.insert(0, str(ROOT / "art/hall_district_20260930"))
sys.path.insert(0, str(ROOT / "art/north_avenue_20260930"))
import ward_masonry as WM
from ward_masonry import (Part, Frame, stone_tint, ashlar_block, fill_wall, sweep, eroded_bevel, block_wear, lerp, drng,
                          export, tri_count, finalize_parts, lettering, MORTAR_FRONT, DripSet, ScarSet)
import author_ward_shops as AWS
from author_ward_shops import Shop
from north_kit import corrugated_sheet

OUT = ROOT / "unity/AthenHill/Assets/AthenHill/Art/WardBuildings/Models"
OUT.mkdir(parents=True, exist_ok=True)
STENCIL_FONT = ROOT / "art/west_gate_20260926/fonts/stardosstencil__StardosStencil-Bold.ttf"
SD = "Assets/AthenHill/Prefabs/StreetDressing/"


def parcel(hw, d, base=0.0, g_top=4.75):
    """Point the hall district Shop class at another parcel: half-width hw, depth d, ground level base, ground-storey
    courses 0.55 plinth + 0.42 m courses up to g_top, string course 0.25 m above that (module globals of
    author_ward_shops are read at call time)."""
    AWS.HW, AWS.D, AWS.BASE = hw, d, base
    g = [round(base, 3), round(base + 0.55, 3)]
    while g[-1] + 0.42 <= g_top + 1e-3:
        g.append(round(g[-1] + 0.42, 3))
    AWS.G = g
    AWS.STRING = (g[-1], round(g[-1] + 0.25, 3))
    AWS.UP = [AWS.STRING[1]]
    return g


class Building(Shop):
    """Shop plus the pieces this pass needs: corner piers with blackened steel bands, a composite upper module, a
    half-raised loading bay with a lit interior, banners, prop mounts and extra lights."""

    def __init__(self, name, lod, tint, seed, **kw):
        upper = kw.pop("upper", [])
        super().__init__(name, lod, tint, seed, upper=upper, **kw)
        p = lambda s, wear=True: Part(f"{name}_{s}_LOD{lod}", wear=wear)
        self.hard = p("Hardware", False)        # bolts, rivets, small brackets: never cast shadows
        self.interior = p("Interior", False)
        self.extra_parts = [(self.hard, {"ao": False}), (self.interior, {"ao": False})]
        self.rec["props"] = []

    @property
    def HW(self):
        return AWS.HW

    @property
    def D(self):
        return AWS.D

    def prop(self, path, pos, yaw=0.0, name=None):
        self.rec["mounts"].append({"name": name or Path(path).stem, "path": path, "pos": list(pos), "yaw": yaw})

    def rivets(self, F, u0, u1, y, d, step=0.16, r=0.012):
        if self.lod > 0:
            return
        u = u0
        while u <= u1 + 1e-4:
            self.hard.sphere(tuple(F.P(u, y, d)), r, "VH_Steel", 6, hemi_axis=tuple(F.n))
            u += step

    # ------------------------------------------------------------------ riveted steel corner straps over the quoins
    def corner_straps(self, ranges, flange=0.32, base=None):
        """L-section blackened-steel straps over the four corner quoins for each (y0, y1) in ranges, rivet rows on both
        flanges; base = height of a heavier corner shoe plate from the ground (concept: the AQUIFER 3 corners)."""
        HW, D = self.HW, self.D
        m = self.metal
        for (x, z, sx, sz) in ((HW, 0.0, 1, 1), (-HW, 0.0, -1, 1), (HW, -D, 1, -1), (-HW, -D, -1, -1)):
            for (y0, y1, fl, th) in [(a, b, flange, 0.035) for a, b in ranges] + ([(AWS.BASE, base, flange + 0.12, 0.05)] if base else []):
                d0, d1 = 0.105, 0.105 + th
                xa, xb = sorted((x + sx * d0, x + sx * d1))
                za, zb = sorted((z + sz * (d1), z + sz * (d1 - fl - 0.092)))
                m.box((xa, y0, za), (xb, y1, zb), "WB_BlackSteel")
                xa, xb = sorted((x + sx * (d1), x + sx * (d1 - fl - 0.092)))
                za, zb = sorted((z + sz * d0, z + sz * d1))
                m.box((xa, y0, za), (xb, y1, zb), "WB_BlackSteel")
                if self.lod == 0:
                    yy = y0 + 0.08
                    while yy < y1 - 0.05:
                        for off in (0.08, fl - 0.04):
                            self.hard.sphere((x + sx * (d1 + 0.004), yy, z + sz * (d1 - off)), 0.014, "VH_Steel", 6, hemi_axis=(sx, 0, 0))
                            self.hard.sphere((x + sx * (d1 - off), yy, z + sz * (d1 + 0.004)), 0.014, "VH_Steel", 6, hemi_axis=(0, 0, sz))
                        yy += 0.2
                for F, (ua, ub) in ((self.FRONT if sz > 0 else self.REAR, (-HW, HW)),):
                    pass
            fa = self.FRONT if sz > 0 else self.REAR
            fb = self.RIGHT if sx > 0 else self.LEFT
            for y0, y1 in ranges:
                self.fdrip(fb, (0.0 if sz > 0 else D) - 0.4, (0.0 if sz > 0 else D) + 0.4, y0, 1.6, 0.8, "rust", soft=0.1)

    # ------------------------------------------------------------------ corner piers (stone, steel bands)
    def piers(self, top, w=1.05, proj=0.30, bands=(), banner_faces=()):
        """Ashlar piers on the four corners, projecting `proj` beyond both faces (courses alternate which face owns the
        corner block, like quoins), a weathered cap, riveted blackened steel bands at the heights in `bands`."""
        HW, D = self.HW, self.D
        cs = [c for c in self.courses if c < top - 0.2]
        while cs[-1] + 0.42 < top - 0.2:
            cs.append(round(cs[-1] + 0.42, 3))
        cs.append(top)
        corners = [  # (frame A, uA corner sign, frame B ...) per corner: front-right, front-left, rear-left, rear-right
            ("FR", Frame((0, 0, 0), (1, 0, 0), (0, 0, 1)), HW, Frame((HW, 0, 0), (0, 0, -1), (1, 0, 0)), 0.0),
            ("FL", Frame((0, 0, 0), (-1, 0, 0), (0, 0, 1)), HW, Frame((-HW, 0, 0), (0, 0, -1), (-1, 0, 0)), 0.0),
            ("RL", Frame((0, 0, -D), (-1, 0, 0), (0, 0, -1)), HW, Frame((-HW, 0, -D), (0, 0, 1), (-1, 0, 0)), 0.0),
            ("RR", Frame((0, 0, -D), (1, 0, 0), (0, 0, -1)), HW, Frame((HW, 0, -D), (0, 0, 1), (1, 0, 0)), 0.0),
        ]
        J = 0.009
        self.rec.setdefault("piers", [])
        for key, FA, ua, FB, _ in corners:
            for ci, (y0, y1) in enumerate(zip(cs, cs[1:])):
                rough = ci == 0
                mat = "VH_AshlarRough" if rough else "VH_Ashlar"
                ownA = ci % 2 == 0
                # face A block: along A from ua - w to ua (+proj if it owns the corner)
                # one block owns the corner per course (like quoins); the other face's block starts behind it
                a0, a1 = (ua - w, ua + proj) if ownA else (ua - w, ua - 0.32)
                ashlar_block(self.mas, FA, a0 + J / 2, a1 - J / 2, y0 + J / 2, y1 - J / 2, mat=mat, depth=proj, back=-0.32,
                             key=(key, "pa", ci), chip=0.25, bevel=(0.016, 0.03))
                b0, b1 = (0.32, w) if ownA else (-proj, w)
                ashlar_block(self.mas, FB, b0 + J / 2, b1 - J / 2, y0 + J / 2, y1 - J / 2, mat=mat, depth=proj, back=-0.32,
                             key=(key, "pb", ci), chip=0.25, bevel=(0.016, 0.03))
            # mortar core inside the joints
            c = [FA.P(ua - w + 0.02, 0, proj - 0.03), FA.P(ua + proj - 0.03, 0, proj - 0.03), FA.P(ua + proj - 0.03, 0, -w + 0.02),
                 FA.P(ua - w + 0.02, 0, -w + 0.02)]
            # FA.P(u, y, d): the core spans u in [ua-w, ua+proj] and d in [-w.., proj]; build as a hexa
            lo = [Vector((p.x, cs[0], p.z)) for p in c]
            hi = [Vector((p.x, top - 0.01, p.z)) for p in c]
            self.mas.hexa(lo + hi, "VH_Mortar")
            # cap: a weathered stone slab with a chamfered top
            ct = top
            cap = [FA.P(ua - w - 0.06, ct, proj + 0.06), FA.P(ua + proj + 0.06, ct, proj + 0.06), FA.P(ua + proj + 0.06, ct, -w - 0.06),
                   FA.P(ua - w - 0.06, ct, -w - 0.06)]
            capt = [FA.P(ua - w + 0.06, ct + 0.28, proj - 0.06), FA.P(ua + proj - 0.06, ct + 0.28, proj - 0.06),
                    FA.P(ua + proj - 0.06, ct + 0.28, -w + 0.06), FA.P(ua - w + 0.06, ct + 0.28, -w + 0.06)]
            mid = [Vector((p.x, ct + 0.16, p.z)) for p in cap]
            bid = self.trim.new_block(tint=stone_tint())
            vs, made = self.trim.hexa(cap + mid, "VH_Ashlar", bid)
            eroded_bevel(self.trim, list(made["top"].edges), 0.02, 2)
            bid = self.trim.new_block(tint=stone_tint())
            vs, made = self.trim.hexa(mid + capt, "VH_Ashlar", bid, skip=("bottom",))
            self.fdrip(FA, ua - w - 0.06, ua + proj + 0.06, ct, 2.5, 0.8, soft=0.15, plane_off=proj)
            self.fdrip(FB, -proj - 0.06, w + 0.06, ct, 2.5, 0.8, soft=0.15, plane_off=proj)
            # steel bands
            for by in bands:
                for F, u0, u1 in ((FA, ua - w - 0.01, ua + proj + 0.01), (FB, -proj - 0.01, w + 0.01)):
                    F.box(self.metal, u0, u1, by - 0.13, by + 0.13, proj - 0.01, proj + 0.022, "WB_BlackSteel")
                    self.rivets(F, u0 + 0.08, u1 - 0.08, by + 0.07, proj + 0.022, 0.17)
                    self.rivets(F, u0 + 0.08, u1 - 0.08, by - 0.07, proj + 0.022, 0.17)
                    self.fdrip(F, u0, u1, by - 0.13, 1.6, 0.85, "rust", plane_off=proj, soft=0.08)
                # band return on the hidden-from-street inner sides is buried in the wall/module
            self.rec["piers"].append({"corner": key, "top": top})
            if key in banner_faces:
                self.banner(FA, ua - w / 2 + proj / 2 - 0.15, top - 0.75, proj + 0.03, 0.78, 4.2, key)

    def banner(self, F, uc, ytop, d, width, length, key):
        """Torn Warden banner (VH_Banner, double-sided cloth) on a steel rod, hanging flat on the pier face."""
        rr = drng("banner", key)
        bm = self.canvas.bm
        mi = self.canvas.mi("VH_Banner")
        nx = 6 if self.lod == 0 else 2
        ny = 14 if self.lod == 0 else 3
        rows = []
        for j in range(ny + 1):
            t = j / ny
            row = []
            for i in range(nx + 1):
                s = i / nx
                y = ytop - length * t
                if j == ny:   # torn hem: ragged, longer in the middle
                    y += rr.uniform(0.0, 0.5) * (1 - 0.6 * math.sin(math.pi * s))
                bulge = 0.02 * math.sin(math.pi * s) * math.sin(math.pi * t * 0.8) + 0.008 * math.sin(7 * t + s * 3)
                row.append(bm.verts.new(F.P(uc - width / 2 + width * s, y, d + bulge)))
            rows.append(row)
        for j in range(ny):
            for i in range(nx):
                f = bm.faces.new([rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]])
                f.material_index = mi
                f.normal_update()
                if f.normal.dot(F.n) < 0:
                    f.normal_flip()
        self.metal.cyl(tuple(F.P(uc - width / 2 - 0.08, ytop + 0.03, d + 0.02)), tuple(F.P(uc + width / 2 + 0.08, ytop + 0.03, d + 0.02)), 0.02,
                       "VH_Steel", 8)
        for u in (uc - width / 2 - 0.05, uc + width / 2 + 0.05):
            F.box(self.metal, u - 0.025, u + 0.025, ytop - 0.02, ytop + 0.08, d - 0.04, d + 0.03, "VH_Steel")

    # ------------------------------------------------------------------ composite upper module (sci-fi retrofit)
    def module(self, y0, y1, face_spans, posts=2.4, led_y=None, vents=(), scorched=(), patched=(), fresh=()):
        """Graphite composite panels in a blackened steel frame on a riveted sill beam over the string course; a recessed
        cyan LED channel; louvred vents, scorched / replaced / patched panels by (face, index) keys."""
        m, hd = self.metal, self.hard
        led_y = led_y if led_y is not None else lerp(y0, y1, 0.42)
        self.rec["module"] = {"y": [y0, y1], "led": led_y}
        for face, (ua, ub) in face_spans.items():
            F = self.faces[face][0]
            # sill beam, head beam
            F.box(m, ua - 0.02, ub + 0.02, y0, y0 + 0.24, -0.05, 0.2, "VH_Steel")
            F.box(m, ua - 0.02, ub + 0.02, y0 + 0.2, y0 + 0.24, 0.2, 0.24, "VH_Steel")
            F.box(m, ua - 0.02, ub + 0.02, y1 - 0.26, y1, -0.05, 0.2, "VH_Steel")
            self.rivets(F, ua + 0.1, ub - 0.1, y0 + 0.12, 0.2, 0.22)
            self.rivets(F, ua + 0.1, ub - 0.1, y1 - 0.13, 0.2, 0.22)
            n = max(1, round((ub - ua) / posts))
            xs = [lerp(ua, ub, i / n) for i in range(n + 1)]
            for x in xs:
                F.box(m, x - 0.09, x + 0.09, y0 + 0.24, y1 - 0.26, -0.05, 0.17, "VH_Steel")
                if self.lod == 0:
                    for yy in (y0 + 0.5, lerp(y0, y1, 0.5), y1 - 0.5):
                        hd.sphere(tuple(F.P(x, yy, 0.17)), 0.014, "VH_Steel", 6, hemi_axis=tuple(F.n))
            # LED channel: dark recess with a slim cyan strip, steel lips
            F.box(m, ua, ub, led_y - 0.075, led_y + 0.075, -0.05, 0.03, "VH_Dark")
            F.box(self.glow, ua + 0.05, ub - 0.05, led_y - 0.03, led_y + 0.03, 0.03, 0.075, "WB_LedCyan")
            for yy in (led_y - 0.075, led_y + 0.06):
                F.box(m, ua, ub, yy, yy + 0.015, 0.02, 0.085, "VH_Steel")
            self.fdrip(F, ua, ub, y1, 1.0, 0.6, "rust", soft=0.2)
            # panels: two rows per bay
            for i, (a, b) in enumerate(zip(xs, xs[1:])):
                for row, (pa, pb) in enumerate(((y0 + 0.26, led_y - 0.075), (led_y + 0.075, y1 - 0.28))):
                    k = (face, i, row)
                    mat = "WS_PanelDark"
                    if k in scorched:
                        mat = "WB_CompositeScorched"
                    elif k in fresh:
                        mat = "WB_CompositeFresh"
                    u0, u1 = a + 0.1, b - 0.1
                    if k in patched:
                        # blown-out panel: jagged hole behind a riveted steel patch plate (the frame behind shows at the edges)
                        F.box(m, u0, u1, pa, pb, -0.06, -0.04, "VH_Dark")
                        F.box(m, u0 + 0.05, u1 - 0.2, pa + 0.1, pb - 0.12, 0.09, 0.105, "WB_BlackSteel")
                        self.rivets(F, u0 + 0.1, u1 - 0.25, pa + 0.16, 0.105, 0.14)
                        self.rivets(F, u0 + 0.1, u1 - 0.25, pb - 0.18, 0.105, 0.14)
                        self.fdrip(F, u0, u1 - 0.2, pa + 0.1, 1.2, 0.8, "rust", soft=0.06)
                        continue
                    # panel slab with a raised border (reads as a pressed composite skin)
                    F.box(m, u0, u1, pa, pb, -0.02, 0.07, mat)
                    if self.lod == 0:
                        F.box(m, u0, u1, pa, pa + 0.04, 0.07, 0.085, mat)
                        F.box(m, u0, u1, pb - 0.04, pb, 0.07, 0.085, mat)
                        F.box(m, u0, u0 + 0.04, pa + 0.04, pb - 0.04, 0.07, 0.085, mat)
                        F.box(m, u1 - 0.04, u1, pa + 0.04, pb - 0.04, 0.07, 0.085, mat)
                        for (uu, yy) in ((u0 + 0.07, pa + 0.07), (u1 - 0.07, pa + 0.07), (u0 + 0.07, pb - 0.07), (u1 - 0.07, pb - 0.07)):
                            hd.sphere(tuple(F.P(uu, yy, 0.085)), 0.011, "VH_Steel", 6, hemi_axis=tuple(F.n))
                    if k in vents:
                        vc, vy = (u0 + u1) / 2, (pa + pb) / 2
                        F.box(m, vc - 0.32, vc + 0.32, vy - 0.24, vy + 0.24, 0.07, 0.1, "VH_Steel")
                        F.box(m, vc - 0.27, vc + 0.27, vy - 0.19, vy + 0.19, 0.06, 0.102, "VH_Dark")
                        for s in range(6):
                            yy = lerp(vy - 0.16, vy + 0.16, s / 5)
                            c = [F.P(vc - 0.27, yy - 0.025, 0.1), F.P(vc + 0.27, yy - 0.025, 0.1), F.P(vc + 0.27, yy - 0.025, 0.13), F.P(vc - 0.27, yy - 0.025, 0.13),
                                 F.P(vc - 0.27, yy + 0.025, 0.08), F.P(vc + 0.27, yy + 0.025, 0.08), F.P(vc + 0.27, yy + 0.025, 0.1), F.P(vc - 0.27, yy + 0.025, 0.1)]
                            m.hexa(c, "VH_Steel")
                        self.fdrip(F, vc - 0.3, vc + 0.3, vy - 0.24, 1.2, 0.7, "grime", soft=0.08)

    # ------------------------------------------------------------------ half-raised loading bay with a lit room
    def loading_bay(self, face, u0, u1, top, curtain_bottom, room_depth=4.2, hazard=True):
        F = self.faces[face][0]
        lt = top + 0.42
        BASE = AWS.BASE
        self.holes[face] += [(u0, u1, BASE, top), (u0 - 0.2, u1 + 0.2, top, lt)]
        self.rec.setdefault("recesses", []).append({"face": face, "u": [u0, u1], "depth": 0.32, "top": top})
        self.rec["bay"] = {"u": [u0, u1], "top": top, "curtain_bottom": curtain_bottom, "room_depth": room_depth}

        def build():
            trim, metal, glow, room = self.trim, self.metal, self.glow, self.interior
            jy = [BASE] + [c for c in self.courses if BASE < c < top] + [top]
            for (a, b) in ((u0 - 0.001, u0 + 0.07), (u1 - 0.07, u1 + 0.001)):
                for (y0, y1) in zip(jy, jy[1:]):
                    bid = trim.new_block(tint=stone_tint(), ao=0.85, erode=0.006 + 0.008 * block_wear(y0))
                    F.box(trim, a, b, y0 + .004, y1 - .004, -0.42, 0.03, "VH_Ashlar", bid, skip=("bottom", "top"))
            # riveted steel box lintel, stone course above
            F.box(metal, u0 - 0.35, u1 + 0.35, top, top + 0.32, -0.42, 0.1, "VH_PaintedSteel")
            bid = trim.new_block(tint=stone_tint())
            F.box(trim, u0 - 0.35, u1 + 0.35, top + 0.325, lt - .005, 0.0, 0.07, "VH_Ashlar", bid, skip=("s0",))
            self.rivets(F, u0 - 0.28, u1 + 0.28, top + 0.07, 0.1, 0.24)
            self.rivets(F, u0 - 0.28, u1 + 0.28, top + 0.25, 0.1, 0.24)
            self.fdrip(F, u0 - 0.35, u1 + 0.35, top, 1.4, 0.9, "rust", soft=0.15)
            if hazard:
                # hazard-striped steel channel frame proud of the stone (jambs + header), bump guards at the foot
                for (a, b) in ((u0 - 0.34, u0 - 0.02), (u1 + 0.02, u1 + 0.34)):
                    F.box(metal, a, b, BASE, top + 0.02, 0.06, 0.17, "WB_Hazard")
                    F.box(metal, a - 0.02, b + 0.02, BASE, BASE + 0.9, 0.17, 0.24, "VH_Steel")
                    F.box(metal, a, b, BASE + 0.9, BASE + 0.96, 0.17, 0.24, "VH_Steel")
                F.box(metal, u0 - 0.34, u1 + 0.34, top - 0.3, top + 0.02, 0.1, 0.18, "WB_Hazard")
            # guides and roller box
            for a in (u0 + 0.07, u1 - 0.07):
                F.box(metal, a - 0.035, a + 0.035, BASE, top, -0.3, -0.17, "VH_Steel")
            F.box(metal, u0 + 0.04, u1 - 0.04, top - 0.46, top, -0.4, -0.13, "VH_PaintedSteel")
            # curtain from under the box down to curtain_bottom; bottom bar, pull handles, a dent and a scorch
            DZ = -0.22
            y = top - 0.46
            while y - 0.085 >= curtain_bottom + 0.1:
                c = [F.P(u0 + 0.1, y - 0.085, DZ), F.P(u1 - 0.1, y - 0.085, DZ), F.P(u1 - 0.1, y - 0.085, DZ + 0.02), F.P(u0 + 0.1, y - 0.085, DZ + 0.02),
                     F.P(u0 + 0.1, y, DZ), F.P(u1 - 0.1, y, DZ), F.P(u1 - 0.1, y, DZ + 0.035), F.P(u0 + 0.1, y, DZ + 0.035)]
                metal.hexa(c, "WS_Shutter")
                y -= 0.085
            F.box(metal, u0 + 0.1, u1 - 0.1, curtain_bottom, y, DZ - 0.01, DZ + 0.06, "VH_Steel")
            for a in (u0 + 0.6, u1 - 0.6):
                metal.cyl(F.P(a - 0.1, curtain_bottom + 0.05, DZ + 0.09), F.P(a + 0.1, curtain_bottom + 0.05, DZ + 0.09), 0.014, "VH_Steel", 6)
            self.fdrip(F, u0 + 0.1, u1 - 0.1, top - 0.46, 1.4, 0.35, "rust", soft=0.2)
            # the room behind: steel-lined walls, ceiling, deck floor, LED bar
            ra, rb = u0 - 0.6, u1 + 0.6
            RZ = -0.42 - room_depth
            H = top + 0.1
            F.box(room, ra, rb, BASE, H, RZ - 0.05, RZ, "WS_PanelDark")
            F.box(room, ra - 0.05, ra, BASE, H, RZ, -0.42, "WS_PanelDark")
            F.box(room, rb, rb + 0.05, BASE, H, RZ, -0.42, "WS_PanelDark")
            F.box(room, ra, rb, H, H + 0.05, RZ, -0.42, "WS_PanelDark")
            F.box(room, ra, rb, BASE - 0.05, BASE + 0.01, RZ, -0.3, "WS_Deck")
            if self.lod == 0:
                for k in range(1, 6):
                    u = lerp(ra, rb, k / 6)
                    F.box(room, u - 0.01, u + 0.01, BASE, H, RZ, RZ + 0.015, "VH_Steel")
                # floor safety line
                F.box(room, ra + 0.4, rb - 0.4, BASE + 0.01, BASE + 0.014, -1.1, -1.0, "WS_PaintYellow")
            F.box(glow, ra + 0.4, rb - 0.4, H - 0.05, H - 0.02, RZ + 1.2, RZ + 1.35, "WB_LedCyan")
            # the fabricator: steel plinth, four-post gantry, glazed print chamber with LED rings, a servo arm, console
            fc = (u0 + u1) / 2
            fz = RZ + 1.6
            P = lambda u, y, d: F.P(u, y, d)
            F.box(room, fc - 1.1, fc + 1.1, BASE, BASE + 0.45, fz - 0.75, fz + 0.75, "VH_PaintedSteel")
            for su in (-1, 1):
                for sz in (-1, 1):
                    room.cyl(tuple(P(fc + su * 1.0, BASE + 0.45, fz + sz * 0.65)), tuple(P(fc + su * 1.0, BASE + 2.55, fz + sz * 0.65)), 0.05, "VH_Steel", 8)
            for sz in (-1, 1):
                room.cyl(tuple(P(fc - 1.05, BASE + 2.55, fz + sz * 0.65)), tuple(P(fc + 1.05, BASE + 2.55, fz + sz * 0.65)), 0.06, "VH_Steel", 8)
            room.cyl(tuple(P(fc - 1.0, BASE + 2.5, fz)), tuple(P(fc + 1.0, BASE + 2.5, fz)), 0.05, "WS_PaintYellow", 8)
            for su in (-1, 1):
                F.box(glow, fc + su * 1.0 - 0.02, fc + su * 1.0 + 0.02, BASE + 0.6, BASE + 2.4, fz + 0.7, fz + 0.72, "WB_LedCyan")
            F.box(self.clear, fc - 0.6, fc + 0.6, BASE + 0.5, BASE + 1.55, fz - 0.5, fz + 0.5, "WS_ClearGlass")
            for yy in (BASE + 0.5, BASE + 1.55):
                F.box(glow, fc - 0.62, fc + 0.62, yy - 0.015, yy + 0.015, fz + 0.5, fz + 0.52, "WB_LedCyan")
            F.box(glow, fc - 0.25, fc + 0.25, BASE + 0.5, BASE + 0.56, fz - 0.25, fz + 0.25, "WB_LedCyan")  # print bed glow
            F.box(room, fc - 0.18, fc + 0.18, BASE + 0.56, BASE + 0.8, fz - 0.15, fz + 0.15, "VH_Steel")      # part on the bed
            room.tube([tuple(P(fc + 0.9, BASE + 0.45, fz + 0.4)), tuple(P(fc + 0.9, BASE + 1.4, fz + 0.4)), tuple(P(fc + 0.45, BASE + 1.9, fz + 0.15)),
                       tuple(P(fc + 0.2, BASE + 1.62, fz))], 0.055, "WS_PaintYellow", 10)
            F.box(room, rb - 1.0, rb - 0.2, BASE, BASE + 1.05, RZ + 0.2, RZ + 0.75, "VH_PaintedSteel")      # console
            F.box(glow, rb - 0.92, rb - 0.28, BASE + 0.8, BASE + 1.0, RZ + 0.76, RZ + 0.77, "WB_ScreenCyan")
            room.tube([tuple(P(fc, BASE + 2.55, fz)), tuple(P(fc, H - 0.05, fz)), tuple(P(rb - 0.6, H - 0.05, RZ + 0.4))], 0.04, "VH_Rubber", 8)
            # stacked feedstock canisters by the wall
            for i, uu in enumerate((ra + 0.4, ra + 0.85)):
                room.cyl(tuple(P(uu, BASE, RZ + 0.5)), tuple(P(uu, BASE + 0.9, RZ + 0.5)), 0.2, "WB_PaintBone" if i else "WS_PaintRed", 12)
            cp = P(fc, H - 0.4, RZ + 1.4)
            self.rec["lights"].append({"name": "Fab bay interior", "type": "point", "pos": [cp.x, cp.y, cp.z], "color": [0.7, 0.9, 1.0],
                                       "intensity": 4.0, "range": 7.0, "clock": False})
            gp = P(fc, BASE + 1.0, fz + 0.9)
            self.rec["lights"].append({"name": "Fab chamber glow", "type": "point", "pos": [gp.x, gp.y, gp.z], "color": [0.35, 0.85, 1.0],
                                       "intensity": 1.6, "range": 3.0, "clock": False})
        self.later.append(build)

    def stencil(self, text, face, u, y, size, width_limit, d, mat="WB_StencilPaint"):
        F = self.faces[face][0]
        c = F.P(u, y, d)
        ob, w = lettering(text, STENCIL_FONT, size, tuple(c), 0.004, width_limit, mat, self.coll, f"{self.name}_Stencil_{face}_LOD{self.lod}",
                          lod=1, facing=tuple(F.n))   # painted: no bevel, coarse curves
        self.stencils = getattr(self, "stencils", []) + [ob]

    def finish(self):
        objs = super().finish()
        return objs + getattr(self, "stencils", [])


# ====================================================================== NANOFAB 2
def nanofab(lod):
    """Nanofab 2 workshop (SE yard). Replaces `Ward district retrofit/Nanofab workshop` on the same footprint
    (14 x 10 m, root at world (36, 0, -28), street face north). Concept: concept/nanofab_concept_v1.png."""
    parcel(7.0, 10.0, 0.0, 4.75)
    s = Building("Nanofab2", lod, (1.04, 0.97, 0.88), 2003)
    HW, D = s.HW, s.D
    # openings in the stone storey (courses 0 .55 .97 1.39 1.81 2.23 2.65 3.07 3.49 3.91 4.33 4.75)
    s.loading_bay("front", -4.85, -0.35, 3.91, 2.05)
    s.portal("front", 2.35, 1.0, 2.65, kind="single", door_mat="VH_DoorSteel", arch=False, transom=0.0)
    s.window("front", 4.15, 4.95, 1.39, 2.65, kind="bars")
    s.window("left", -7.2, -6.2, 2.23, 3.49, kind="bars")
    s.window("left", -3.4, -2.4, 2.23, 3.49, kind="bars")
    s.window("right", 1.6, 2.4, 2.65, 3.49, kind="bars", lintel=True)
    s.portal("rear", -2.0, 1.0, 2.65, kind="single", door_mat="WS_PaintOlive", arch=False, transom=0.0)
    s.window("rear", 1.5, 2.5, 2.23, 3.49, kind="bars")
    s.scorch("front", -4.9, -0.3, 4.33, 2.4, 0.85)          # the bay burned once: soot up the stone and into the module
    s.scorch("left", -3.5, -2.3, 3.49, 1.6, 0.6)
    s.walls()
    top_stone = AWS.STRING[1]                              # 5.0
    # composite upper module on all four faces between the piers
    W = 1.05
    spans = {"front": (-HW + W - 0.02, HW - W + 0.02), "rear": (-HW + W - 0.02, HW - W + 0.02),
             "right": (W - 0.02, D - W + 0.02), "left": (-D + W - 0.02, -W + 0.02)}
    s.module(top_stone, 8.45, spans, posts=2.45,
             vents={("front", 0, 0), ("front", 4, 1), ("right", 1, 0), ("right", 2, 1), ("left", 0, 1), ("rear", 1, 0), ("rear", 3, 1)},
             scorched={("front", 0, 1), ("front", 1, 1), ("front", 1, 0), ("left", 2, 1)},
             fresh={("front", 3, 0), ("right", 0, 1), ("rear", 2, 1)},
             patched={("front", 4, 0), ("left", 1, 0)})
    s.piers(9.05, w=W, proj=0.3, bands=(1.25, 4.92, 7.05, 8.75), banner_faces=("FR", "FL"))
    # roof deck inside the head beam; steel coping
    s.roof.box((-HW + 0.04, 8.2, -D + 0.04), (HW - 0.04, 8.32, -0.04), "VH_Roof")
    for face, (ua, ub) in spans.items():
        F = s.faces[face][0]
        F.box(s.metal, ua - 0.02, ub + 0.02, 8.45, 8.52, -0.25, 0.24, "WB_BlackSteel")
    s.roof_y = 8.32
    s.top_y = 9.33
    # stencil + company sigil plate on the upper panels
    s.stencil("NANOFAB 2", "front", 0.0, 7.3, 0.62, 2.05, 0.087)
    s.stencil("NO NAKED FLAME", "front", 2.35, 3.42, 0.11, 1.0, 0.09)
    s.stencil("FAB 2", "rear", 0.0, 7.35, 0.5, 2.6, 0.087)
    # roof plant: three cooling-fan housings, ducts, exhaust stack with platform and ladder
    m = s.metal
    ry = s.roof_y
    for i, x in enumerate((-4.4, -1.6, 1.2)):
        z = -3.2
        m.box((x - 1.05, ry, z - 0.85), (x + 1.05, ry + 1.15, z + 0.85), "VH_PaintedSteel")
        m.box((x - 1.1, ry + 1.15, z - 0.9), (x + 1.1, ry + 1.22, z + 0.9), "VH_Steel")
        m.box((x - 0.95, ry + 1.22, z - 0.75), (x + 0.95, ry + 1.25, z + 0.75), "VH_Dark")
        if lod == 0:
            for k in range(12):
                xx = lerp(x - 0.9, x + 0.9, k / 11)
                m.box((xx - 0.012, ry + 1.22, z - 0.78), (xx + 0.012, ry + 1.3, z + 0.78), "VH_Steel")
            for k in range(4):   # side grilles
                yy = ry + 0.25 + k * 0.2
                m.box((x - 1.06, yy, z - 0.7), (x + 1.06, yy + 0.05, z + 0.7), "VH_Steel")
        m.cyl((x, ry + 1.25, z), (x, ry + 1.27, z), 0.7, "VH_Dark", 20)
        m.box((x - 0.15, ry, z + 0.85), (x + 0.15, ry + 0.6, z + 1.25), "VH_Steel")
    s.rec["mounts"].append({"name": "Roof air conditioner", "path": "Assets/AthenHill/Prefabs/WestGate/PH_AirconRusted.prefab",
                            "pos": [3.4, ry, -7.6], "yaw": 180})
    sx, sz = 4.6, -6.6
    m.cyl((sx, ry, sz), (sx, ry + 7.2, sz), 0.48, "VH_Steel", 20)
    for yy in (ry + 1.8, ry + 4.2, ry + 6.6):
        m.cyl((sx, yy, sz), (sx, yy + 0.14, sz), 0.52, "WG_RustSteel", 20)
    m.cyl((sx, ry + 7.2, sz), (sx, ry + 7.5, sz), 0.42, "VH_Dark", 20)
    m.cyl((sx, ry + 4.6, sz), (sx, ry + 4.68, sz), 1.0, "VH_Steel", 16)
    for k in range(10):
        a = 2 * math.pi * k / 10
        m.cyl((sx + math.cos(a) * 0.98, ry + 4.68, sz + math.sin(a) * 0.98), (sx + math.cos(a) * 0.98, ry + 5.6, sz + math.sin(a) * 0.98), 0.018, "VH_Steel", 4)
    m.tube([(sx + math.cos(2 * math.pi * k / 12) * 0.98, ry + 5.6, sz + math.sin(2 * math.pi * k / 12) * 0.98) for k in range(13)], 0.022, "VH_Steel", 6)
    for s_ in (-0.2, 0.2):
        m.cyl((sx + s_, ry, sz + 0.55), (sx + s_, ry + 4.65, sz + 0.55), 0.02, "VH_Steel", 6)
    if lod == 0:
        for k in range(14):
            yy = ry + 0.3 + k * 0.31
            s.hard.cyl((sx - 0.2, yy, sz + 0.55), (sx + 0.2, yy, sz + 0.55), 0.014, "VH_Steel", 6)
    m.tube([(-4.4, ry + 0.6, -2.35), (-4.4, ry + 0.6, -1.4), (3.6, ry + 0.6, -1.4), (3.6, ry + 0.6, -6.6), (sx - 0.48, ry + 1.2, sz)], 0.26, "VH_Steel", 14)
    m.box((-5.2, ry, -9.0), (-4.4, ry + 0.95, -8.2), "VH_Steel")   # roof hatch
    s.rec["notes"].append("roof: three fan housings, duct to the exhaust stack (platform + ladder), hatch, AC unit")
    # front: personnel door canopy, access panel, conduit; lamps; downpipes; junction box
    F = s.FRONT
    F.box(m, 1.6, 3.1, 3.02, 3.07, 0.05, 0.95, "VH_PaintedSteel")
    F.box(m, 1.6, 3.1, 2.96, 3.02, 0.88, 0.95, "VH_PaintedSteel")
    for u in (1.7, 3.0):
        m.cyl((u, 3.07, 0.88), (u, 3.75, 0.1), 0.012, "VH_Steel", 6)
    F.box(m, 3.05, 3.4, 1.15, 1.6, 0.062, 0.13, "WS_PanelDark")
    F.box(s.glow, 3.09, 3.36, 1.36, 1.54, 0.13, 0.135, "WB_ScreenCyan")
    s.conduit([(3.22, 1.6, 0.14), (3.22, 4.6, 0.14)])
    s.lamp("front", -5.55, 3.4, "Lamp bay west")
    s.lamp("front", 0.95, 3.4, "Lamp between bay and door")
    s.lamp("rear", -2.0, 3.25, "Rear door lamp")
    s.lamp("right", 2.0, 4.0, "Gas bank lamp")
    s.junction_box("front", 3.75, 2.2)
    s.downpipe("front", 5.6, 4.95)
    s.downpipe("rear", 4.4, 4.95)
    # east: process-gas bank on a stone plinth, strapped to the wall, lines into the wall under the string course
    RF = s.RIGHT
    bid = s.pod.new_block(tint=stone_tint("rough"))
    vs, made = RF.box(s.pod, 2.6, 8.4, 0.0, 0.42, 0.3, 1.75, "VH_AshlarRough", bid, skip=("bottom",))
    eroded_bevel(s.pod, list(made["top"].edges), 0.02, 2)
    for i, u in enumerate((3.4, 4.6, 5.8, 7.0)):
        c = RF.P(u, 0.42, 1.0)
        mat = ("WB_PaintBone", "WS_PaintRed", "WB_PaintBone", "WB_PaintBone")[i]
        m.cyl((c.x, 0.42, c.z), (c.x, 4.1, c.z), 0.45, mat, 20)
        m.sphere((c.x, 4.1, c.z), 0.44, mat, 16, hemi_axis=(0, 1, 0))
        m.cyl((c.x, 4.5, c.z), (c.x, 4.75, c.z), 0.1, "VH_Steel", 10)
        m.cyl((c.x, 4.68, c.z), (c.x, 4.68, c.z), 0.12, "VH_Brass", 8)
        for yy in (1.4, 3.2):
            m.cyl((c.x, yy, c.z), (c.x, yy + 0.08, c.z), 0.47, "VH_Steel", 20)
        # process line up the wall into the clean-room module, flanged at the panel, clamped to the sill beam
        m.tube([(c.x, 4.75, c.z), (c.x, 5.75 + 0.18 * i, c.z), (HW + 0.32, 5.75 + 0.18 * i, c.z), (HW + 0.32, 5.75 + 0.18 * i, c.z)], 0.04, "VH_Steel", 8)
        m.cyl((HW + 0.32, 5.75 + 0.18 * i, c.z), (HW + 0.06, 5.75 + 0.18 * i, c.z), 0.04, "VH_Steel", 8)
        m.cyl((HW + 0.12, 5.75 + 0.18 * i, c.z), (HW + 0.08, 5.75 + 0.18 * i, c.z), 0.085, "WB_BlackSteel", 10)
        m.box((c.x - 0.08, 5.1, c.z - 0.06), (c.x + 0.08, 5.2, c.z + 0.06), "WB_BlackSteel")
        m.box((HW + 0.18, 5.1, c.z - 0.03), (c.x - 0.04, 5.16, c.z + 0.03), "WB_BlackSteel")
        # wall strap from the cylinder band to the wall
        m.box((HW + 0.05, 3.18, c.z - 0.04), (c.x - 0.4, 3.3, c.z + 0.04), "VH_Steel")
        m.cyl((c.x, 2.3, c.z), (c.x, 2.42, c.z), 0.455, ("WS_PaintYellow", "WB_PaintBone", "WS_PaintTeal", "WS_PaintYellow")[i], 20)
    s.fdrip(RF, 2.6, 8.4, 4.95, 3.0, 0.9, "rust", soft=0.1)
    s.rec["colliders"].append({"name": "COL_GasBank", "center": [HW + 1.0, 2.4, -5.5], "size": [1.6, 4.8, 5.9]})
    # west: corrugated lean-to over a scrap-sorting bay
    LX = -HW - 3.3
    for z in (-1.4, -4.9, -8.4):
        m.box((LX - 0.08, 0.0, z - 0.08), (LX + 0.08, 3.12, z + 0.08), "WG_RustSteel")
        m.box((LX - 0.2, 0.0, z - 0.2), (LX + 0.2, 0.06, z + 0.2), "VH_Steel")
        m.cyl((LX, 2.5, z), (-HW - 0.35, 3.6, z), 0.035, "VH_Steel", 6)
        s.rec["colliders"].append({"name": f"COL_LeanToPost_{z}", "center": [LX, 1.5, z], "size": [0.3, 3.0, 0.3]})
    m.box((LX - 0.12, 3.12, -9.0), (LX + 0.12, 3.3, -0.8), "WG_RustSteel")
    m.box((-HW - 0.2, 3.82, -9.0), (-HW - 0.05, 4.02, -0.8), "VH_Steel")
    # corrugated_sheet runs across x and falls along z: build it, then swap x/z so it falls from the wall to the posts
    fs = corrugated_sheet(s.roof, -9.0, -0.8, (3.3, LX - 0.35), (3.97, -HW - 0.08), "WS_Corrugated", lod=lod)
    for v in {v for f in fs for v in f.verts}:
        v.co.x, v.co.z = v.co.z, v.co.x
    bmesh.ops.reverse_faces(s.roof.bm, faces=fs)
    s.rec["notes"].append("west lean-to: corrugated roof on three rust-steel posts over a scrap-sorting bay (props mounted)")
    s.prop(SD + "SD_crate_wood_deep.prefab", (-HW - 1.4, 0.0, -2.0), 85)
    s.prop(SD + "SD_crate_wood.prefab", (-HW - 1.5, 0.0, -2.9), 10)
    s.prop(SD + "SD_crate_long.prefab", (-HW - 2.2, 0.0, -6.0), 92)
    s.prop(SD + "SD_drum_steel_blue.prefab", (-HW - 0.8, 0.0, -7.6), 0)
    s.prop(SD + "SD_drum_red.prefab", (-HW - 0.85, 0.0, -8.4), 40)
    s.prop(SD + "SD_hand_truck.prefab", (-HW - 2.6, 0.0, -3.9), 120)
    s.prop(SD + "SD_field_generator.prefab", (-HW - 1.6, 0.0, -4.9), 90)
    s.prop(SD + "SD_gas_bottle.prefab", (HW + 0.55, 0.0, -1.0), 0)
    s.prop(SD + "SD_crate_yellow.prefab", (-6.0, 0.0, 1.0), 12)
    s.prop(SD + "SD_ammo_crate_a.prefab", (5.6, 0.0, 0.8), -8)
    s.rec["colliders"].append({"name": "COL_LeanToStock", "center": [-HW - 1.6, 0.6, -5.0], "size": [2.4, 1.2, 7.2]})
    # old battle damage: heavy impact clusters on the street-side piers, under the patched panel and on the rear
    for c, r_, st in (((-6.6, 2.6, 0.32), 1.1, 1.0), ((6.4, 6.2, 0.32), 0.9, 0.9), ((4.8, 4.4, 0.08), 1.3, 0.95),
                      ((-3.0, 1.2, 0.08), 0.8, 0.7), ((7.1, 3.0, -9.2), 1.0, 0.85), ((-1.0, 3.6, -10.08), 1.2, 0.8)):
        s.scars.impact(c, r_, st)
    s.rec["mounts"].append({"name": "Rear air conditioner", "prefab": "PH_AirconRusted", "pos": [2.2, 0.0, -D - 0.4], "yaw": 180})
    s.rec["mounts"].append({"name": "Rear power box", "prefab": "PH_PowerBox", "pos": [-3.6, 1.5, -D - 0.07], "yaw": 180})
    s.conduit([(-3.6, 1.75, -D - 0.14), (-3.6, 4.6, -D - 0.14)])
    # sand drifts at the street face
    if lod == 0:
        for (a, b) in ((-6.0, -5.1), (-0.1, 1.75), (3.0, 5.9)):
            s.drift(a, b, 0.07, key=("drift", a))
    # pier colliders (the piers project 0.3 m beyond the walls)
    for sxx in (-1, 1):
        for zc in (0.0, -D):
            s.rec["colliders"].append({"name": f"COL_Pier_{sxx}_{zc}", "center": [sxx * (HW - W / 2 + 0.15), 4.5, zc - (W / 2 - 0.15) * (1 if zc == 0 else -1)],
                                       "size": [W + 0.3, 9.0, W + 0.3]})
    return s


def nanofab_lod2():
    """Distance massing (beyond ~70 m): stone box + piers, composite band, roof plant, stack, gas bank."""
    parcel(7.0, 10.0, 0.0, 4.75)
    WM.set_state(2, random.Random(5), "Nanofab2_l2")
    coll = bpy.data.collections.new("Nanofab2_LOD2")
    bpy.context.scene.collection.children.link(coll)
    st, mt = Part("Nanofab2_Masonry_LOD2"), Part("Nanofab2_Metal_LOD2", False)
    HW, D = 7.0, 10.0
    st.box((-HW, 0, -D), (HW, 5.0, 0.06), "VH_Ashlar")
    for sx in (-1, 1):
        for z0 in (0.0, -D):
            xr = (HW - 1.05, HW + 0.3) if sx > 0 else (-HW - 0.3, -HW + 1.05)
            zr = (-1.05, 0.3) if z0 == 0 else (-D - 0.3, -D + 1.05)
            st.box((xr[0], 0, zr[0]), (xr[1], 9.33, zr[1]), "VH_Ashlar")
    mt.box((-HW + 0.95, 5.0, -D + 0.95 - 1.0), (HW - 0.95, 8.5, 0.1), "WS_PanelDark")
    mt.box((-HW + 0.95, 6.48, 0.1), (HW - 0.95, 6.6, 0.12), "WB_LedCyan")
    mt.box((-HW + 0.9, 3.2, -0.4), (-0.3, 3.91, 0.05), "WS_Shutter")
    for x in (-4.4, -1.6, 1.2):
        mt.box((x - 1.05, 8.32, -4.05), (x + 1.05, 9.55, -2.35), "VH_PaintedSteel")
    mt.cyl((4.6, 8.32, -6.6), (4.6, 15.8, -6.6), 0.48, "VH_Steel", 8)
    for z in (-3.4, -4.6, -5.8, -7.0):
        mt.cyl((HW + 1.0, 0.0, z), (HW + 1.0, 4.5, z), 0.45, "WB_PaintBone", 8)
    mt.box((-HW - 3.5, 3.2, -9.0), (-HW - 0.3, 3.95, -0.8), "WS_Corrugated")
    for p in (st, mt):
        p.finalize()
    objs = [st.build(coll, flat=True), mt.build(coll, flat=True)]
    return objs


# ====================================================================== WARDEN CORNER WATCHTOWER (x4)
def watchtower(lod):
    """Warden corner watchtower, one model for the four wall corners. Replaces `Ward district retrofit/Watchtower 1-4`
    (lattice legs + box cabin). Square ashlar shaft 4.4 x 4.4 m on a battered talus, riveted blackened steel bands and
    corner angles, a patched shell hole, an armoured steel observation cabin corbelled out on knee brackets (glazed
    slits with propped shutters, sandbag sill, hipped steel roof), searchlight, antenna with beacon, Warden banner,
    external ladder with a caged landing. Root = door-face centre; the door faces the city. Concept:
    concept/tower_concept_v1.png."""
    parcel(2.2, 4.4, 0.0, 9.37)
    s = Building("Watchtower", lod, (1.02, 0.96, 0.88), 4404)
    HW, D = s.HW, s.D
    m, hd = s.metal, s.hard
    s.portal("front", 0.0, 1.0, 2.23, kind="single", door_mat="VH_DoorSteel", arch=False, transom=0.0)
    # firing slits (narrow, deep) on every face at two levels; the rear faces the wall walk, one slit only
    for face, us in (("front", (-1.05,)), ("left", (-2.2,)), ("right", (2.2,)), ("rear", (0.0,))):
        for u in us:
            s.window(face, u - 0.1, u + 0.1, 4.33, 5.17, depth=0.45, kind="plain")
    for face, us in (("front", (-1.25,)), ("left", (-1.4, -3.0)), ("right", (1.4, 3.0))):
        for u in us:
            s.window(face, u - 0.1, u + 0.1, 6.85, 7.69, depth=0.45, kind="plain")
    s.scorch("right", 1.2, 2.2, 5.17, 1.8, 0.55)
    s.scorch("front", -0.25, 0.25, 7.69, 1.4, 0.6)
    s.walls()
    # battered talus round the base: dressed battered blocks per face (gap at the door) and hipped corner pieces
    TB, TT, TH = 0.55, 0.23, 1.27       # outward offset at the foot / at the top, height
    for face, (F, ua, ub) in s.faces.items():
        spans = [(ua - 0.092, -0.78), (0.78, ub + 0.092)] if face == "front" else [(ua - 0.092, ub + 0.092)]
        for a, b in spans:
            n = max(1, round((b - a) / 0.85))
            cuts = [lerp(a, b, i / n) for i in range(n + 1)]
            for i, (u0, u1) in enumerate(zip(cuts, cuts[1:])):
                j0 = 0.005 if (i > 0 or face != "front" or a > 0) else 0.0
                bid = s.trim.new_block(tint=stone_tint("rough"), erode=0.012)
                c = [F.P(u0 + 0.005, 0.0, -0.02), F.P(u1 - 0.005, 0.0, -0.02), F.P(u1 - 0.005, 0.0, TB), F.P(u0 + 0.005, 0.0, TB),
                     F.P(u0 + 0.005, TH, -0.02), F.P(u1 - 0.005, TH, -0.02), F.P(u1 - 0.005, TH, TT), F.P(u0 + 0.005, TH, TT)]
                vs, made = s.trim.hexa(c, "VH_AshlarRough", bid, skip=("bottom",))
                eroded_bevel(s.trim, [e for e in made["s2"].edges] + [e for e in made["top"].edges if e not in made["s2"].edges], 0.025, 2, seg_len=0.2)
    for (sx, z0, sz) in ((1, 0.0, 1), (-1, 0.0, 1), (1, -D, -1), (-1, -D, -1)):
        x0 = sx * (HW + 0.092)
        zc = z0 + sz * 0.092
        bid = s.trim.new_block(tint=stone_tint("rough"), erode=0.012)
        q = lambda o, y: [(x0, y, zc), (x0 + sx * o, y, zc), (x0 + sx * o, y, zc + sz * o), (x0, y, zc + sz * o)]
        c = q(TB - 0.005, 0.0) + q(TT - 0.005, TH)
        vs, made = s.trim.hexa(c, "VH_AshlarRough", bid, skip=("bottom",))
        eroded_bevel(s.trim, list(made["top"].edges), 0.025, 2, seg_len=0.2)
    # blackened steel: horizontal bands and corner angles, riveted
    for by in (2.75, 6.2, 8.95):
        for face, (F, ua, ub) in s.faces.items():
            if face == "front" and by < 3.0:
                spans = [(ua - 0.12, -0.75), (0.75, ub + 0.12)]
            else:
                spans = [(ua - 0.12, ub + 0.12)]
            for a, b in spans:
                F.box(m, a, b, by - 0.12, by + 0.12, 0.085, 0.125, "WB_BlackSteel")
                s.rivets(F, a + 0.1, b - 0.1, by + 0.065, 0.125, 0.2)
                s.rivets(F, a + 0.1, b - 0.1, by - 0.065, 0.125, 0.2)
                s.fdrip(F, a, b, by - 0.12, 1.8, 0.8, "rust", soft=0.1)
    for (x, z, sx, sz) in ((HW, 0.0, 1, 1), (-HW, 0.0, -1, 1), (HW, -D, 1, -1), (-HW, -D, -1, -1)):
        y0, y1 = 1.3, 9.4
        # riveted corner angle (two 0.2 m flanges) up each arris
        xa, xb = sorted((x + sx * 0.1, x + sx * 0.135))
        za, zb = sorted((z + sz * 0.135, z + sz * (0.135 - 0.22)))
        m.box((xa, y0, za), (xb, y1, zb), "WB_BlackSteel")
        xa, xb = sorted((x + sx * 0.135, x + sx * (0.135 - 0.22)))
        za, zb = sorted((z + sz * 0.1, z + sz * 0.135))
        m.box((xa, y0, za), (xb, y1, zb), "WB_BlackSteel")
    # patched shell hole on the right face: riveted plate over broken stone, heavy impact cluster round it
    RP = s.RIGHT
    RP.box(m, 0.9, 2.05, 3.35, 4.25, 0.1, 0.13, "WB_BlackSteel")
    s.rivets(RP, 0.98, 1.97, 3.42, 0.13, 0.15)
    s.rivets(RP, 0.98, 1.97, 4.18, 0.13, 0.15)
    s.fdrip(RP, 0.9, 2.05, 3.35, 1.6, 0.9, "rust", soft=0.1)
    for c, r_, st in (((HW + 0.08, 3.8, -1.5), 1.4, 1.0), ((0.9, 1.6, 0.08), 0.9, 0.8), ((-HW - 0.08, 7.0, -2.8), 1.0, 0.85),
                      ((-1.2, 8.1, 0.08), 0.8, 0.7)):
        s.scars.impact(c, r_, st)
    # ---- cabin: floor at 9.62 (string course top), corbelled 0.6 m out on knee brackets
    O = 0.62
    cx0, cx1, cz0, cz1 = -HW - O, HW + O, 0.0 + O, -D - O
    fy = AWS.STRING[1]
    m.box((cx0, fy, cz1), (cx1, fy + 0.2, cz0), "WB_BlackSteel")
    for face, (F, ua, ub) in s.faces.items():
        for u in (ua + 0.55, ub - 0.55):
            # triangular knee bracket: web plate from the wall (y 8.4) to the floor edge
            a, b = F.P(u - 0.04, fy, 0.1), F.P(u + 0.04, fy, 0.1)
            c, d = F.P(u - 0.04, fy, O - 0.05), F.P(u + 0.04, fy, O - 0.05)
            e, f = F.P(u - 0.04, fy - 1.25, 0.1), F.P(u + 0.04, fy - 1.25, 0.1)
            m.closed_solid([a, b, c, d, e, f], [[0, 1, 3, 2], [0, 4, 5, 1], [2, 3, 5, 4], [0, 2, 4], [1, 5, 3]], "WB_BlackSteel")
            F.box(m, u - 0.12, u + 0.12, fy - 1.32, fy - 1.18, 0.1, 0.16, "WB_BlackSteel")
            F.box(m, u - 0.12, u + 0.12, fy - 0.05, fy, 0.1, O - 0.02, "WB_BlackSteel")
    # cabin walls: lower armour band, slit band (glass + propped shutters), upper band; posts at corners and mid-face
    yl0, yl1, ys1, yu1 = fy + 0.2, fy + 1.15, fy + 1.75, fy + 2.05
    sides = [  # (frame, u0, u1) round the cabin: outward normals
        (Frame((0, 0, cz0), (1, 0, 0), (0, 0, 1)), cx0, cx1), (Frame((0, 0, cz1), (-1, 0, 0), (0, 0, -1)), -cx1, -cx0),
        (Frame((cx1, 0, 0), (0, 0, -1), (1, 0, 0)), -cz0, -cz1), (Frame((cx0, 0, 0), (0, 0, 1), (-1, 0, 0)), cz1, cz0)]
    for F, u0, u1 in sides:
        F.box(m, u0, u1, yl0, yl1, -0.08, 0.0, "WB_BlackSteel")
        F.box(m, u0, u1, ys1, yu1, -0.08, 0.0, "WB_BlackSteel")
        F.box(m, u0 - 0.02, u1 + 0.02, yl1 - 0.05, yl1, 0.0, 0.32, "VH_Steel")          # sill ledge
        s.rivets(F, u0 + 0.1, u1 - 0.1, yl0 + 0.1, 0.0, 0.2)
        s.rivets(F, u0 + 0.1, u1 - 0.1, (yl0 + yl1) / 2, 0.0, 0.2)
        s.rivets(F, u0 + 0.1, u1 - 0.1, yu1 - 0.1, 0.0, 0.2)
        F.box(m, u0, u1, (yl0 + yl1) / 2 - 0.02, (yl0 + yl1) / 2 + 0.02, 0.0, 0.015, "VH_Steel")   # plate seam strap
        nb = 3
        xs = [lerp(u0, u1, i / nb) for i in range(nb + 1)]
        for x in xs:
            F.box(m, x - 0.09, x + 0.09, yl0, yu1, -0.08, 0.05, "WB_BlackSteel")
        for a, b in zip(xs, xs[1:]):
            F.box(s.glass, a + 0.09, b - 0.09, yl1, ys1, -0.06, -0.05, "WS_Glass", skip=("s0", "s1", "s3", "top", "bottom"))
            # top-hinged armour shutter propped open ~35 degrees, two stays
            ang = math.radians(35)
            L_ = ys1 - yl1 + 0.06
            p0 = [F.P(a + 0.1, ys1, 0.0), F.P(b - 0.1, ys1, 0.0)]
            p1 = [F.P(a + 0.1, ys1 - L_ * math.cos(ang), L_ * math.sin(ang)), F.P(b - 0.1, ys1 - L_ * math.cos(ang), L_ * math.sin(ang))]
            t = F.n * 0.03 + Vector((0, 0.025, 0))
            m.hexa([p0[0], p0[1], p1[1], p1[0], p0[0] + t, p0[1] + t, p1[1] + t, p1[0] + t], "WB_BlackSteel")
            for uu in (a + 0.2, b - 0.2):
                m.cyl(tuple(F.P(uu, yl1 + 0.05, 0.02)), tuple(F.P(uu, ys1 - L_ * math.cos(ang) * 0.6, L_ * math.sin(ang) * 0.6)), 0.012, "VH_Steel", 6)
        s.fdrip(F, u0, u1, yl1 - 0.05, 2.5, 0.8, "rust", soft=0.15)
    # interior back of the slits (dark) so the cabin never looks hollow from below
    m.box((cx0 + 0.1, fy + 0.2, cz1 + 0.1), (cx1 - 0.1, yu1, cz0 - 0.1), "VH_Dark")
    # hipped steel roof with fascia; flat top carrying the searchlight and antenna
    ey, ry = yu1 + 0.05, yu1 + 0.85
    E = 0.35
    ex0, ex1, ez0, ez1 = cx0 - E, cx1 + E, cz0 + E, cz1 - E
    tx0, tx1, tz0, tz1 = -0.75, 0.75, -D / 2 + 0.75, -D / 2 - 0.75
    m.box((cx0 - 0.02, yu1, cz1 - 0.02), (cx1 + 0.02, ey, cz0 + 0.02), "VH_Steel")
    lo = [(ex0, ey, ez0), (ex1, ey, ez0), (ex1, ey, ez1), (ex0, ey, ez1)]
    hi = [(tx0, ry, tz0), (tx1, ry, tz0), (tx1, ry, tz1), (tx0, ry, tz1)]
    s.roof.closed_solid(lo + hi, [[0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7], [4, 5, 6, 7], [3, 2, 1, 0]], "WB_BlackSteel")
    for (a, b) in zip(lo, lo[1:] + lo[:1]):
        m.cyl(a, b, 0.05, "VH_Steel", 6)
    for (a, b) in zip(lo, hi):
        m.cyl(a, (b[0], b[1] + 0.02, b[2]), 0.045, "VH_Steel", 6)
    if lod == 0:   # standing seams on the roof slopes
        for k in range(1, 6):
            t_ = k / 6
            for (a0, a1, b0, b1) in ((lo[0], lo[1], hi[0], hi[1]), (lo[1], lo[2], hi[1], hi[2]), (lo[2], lo[3], hi[2], hi[3]), (lo[3], lo[0], hi[3], hi[0])):
                pa = Vector(a0).lerp(Vector(a1), t_); pb = Vector(b0).lerp(Vector(b1), t_)
                hd.cyl(tuple(pa + Vector((0, 0.02, 0))), tuple(pb + Vector((0, 0.03, 0))), 0.012, "VH_Steel", 4)
    # searchlight on a yoke at the front of the roof top, lens lit at night
    slx, slz = 0.35, tz0 - 0.3
    m.cyl((slx, ry, slz), (slx, ry + 0.45, slz), 0.06, "VH_Steel", 8)
    m.box((slx - 0.32, ry + 0.45, slz - 0.05), (slx + 0.32, ry + 0.5, slz + 0.05), "VH_Steel")
    for sx_ in (-0.3, 0.3):
        m.box((slx + sx_ - 0.025, ry + 0.45, slz - 0.05), (slx + sx_ + 0.025, ry + 0.85, slz + 0.05), "VH_Steel")
    da = Vector((0, -0.25, 0.97)).normalized()
    c0 = Vector((slx, ry + 0.78, slz)) - da * 0.25
    c1 = Vector((slx, ry + 0.78, slz)) + da * 0.25
    m.cyl(tuple(c0), tuple(c1), 0.26, "VH_PaintedSteel", 16)
    m.cyl(tuple(c1), tuple(c1 + da * 0.03), 0.28, "VH_Steel", 16)
    s.glow.cyl(tuple(c1 + da * 0.01), tuple(c1 + da * 0.035), 0.23, "VH_LampLens", 16)
    lp = c1 + da * 0.3
    tgt = lp + da * 12.0 + Vector((0, -6.0, 0))
    s.rec["lights"].append({"name": "Searchlight", "type": "spot", "pos": [lp.x, lp.y, lp.z], "target": [tgt.x, tgt.y, tgt.z],
                            "color": [1.0, 0.86, 0.62], "intensity": 9.0, "range": 26.0, "angle": 24.0, "inner": 12.0})
    # antenna mast with a red beacon at the rear of the roof top
    ax, az = -0.45, tz1 + 0.35
    m.cyl((ax, ry, az), (ax, ry + 3.4, az), 0.045, "VH_Steel", 8)
    for k in range(1, 4):
        yy = ry + k * 0.8
        m.cyl((ax - 0.28, yy, az), (ax + 0.28, yy, az), 0.012, "VH_Steel", 6)
    m.cyl((ax, ry + 3.4, az), (ax, ry + 4.3, az), 0.012, "VH_Steel", 6)
    s.glow.sphere((ax, ry + 3.47, az), 0.06, "VH_BeaconRed", 10)
    for dx, dz in ((1.2, 0.9), (-1.0, 0.9), (0.2, -1.1)):
        m.cyl((ax, ry + 2.6, az), (ax + dx, ry - 0.05, az + dz), 0.005, "VH_Steel", 4)
    # Warden banner hanging from the cabin floor down the front of the shaft
    s.banner(s.FRONT, 0.0, fy - 0.35, 0.16, 0.95, 3.3, "tower")
    # external ladder up the city face beside the door (clear of the corner walls on every tower): ground to a caged
    # landing at 5.6, then up to the cabin floor; hoop cage
    RF = s.FRONT
    lu = 1.45
    for (y0, y1, d0) in ((0.25, 5.6, 0.55), (5.6, fy, 0.55)):
        for sgn in (-1, 1):
            m.cyl(tuple(RF.P(lu + sgn * 0.22, y0, d0)), tuple(RF.P(lu + sgn * 0.22, y1 + 0.9, d0)), 0.022, "VH_Steel", 6)
        k = 0
        yy = y0 + 0.3
        while yy < y1 + 0.05:
            hd.cyl(tuple(RF.P(lu - 0.22, yy, d0)), tuple(RF.P(lu + 0.22, yy, d0)), 0.014, "VH_Steel", 6)
            yy += 0.3
        for yy in [y0 + 2.2 + 0.7 * i for i in range(int((y1 - y0 - 2.2) / 0.7) + 1)] if y1 - y0 > 2.5 else []:
            pts = [RF.P(lu - 0.32, yy, d0 - 0.4)] + [RF.P(lu + 0.36 * math.cos(math.pi - math.pi * i / 6), yy, d0 + 0.36 * math.sin(math.pi * i / 6) + 0.05) for i in range(7)] + [RF.P(lu + 0.32, yy, d0 - 0.4)]
            m.tube([tuple(p) for p in pts], 0.012, "VH_Steel", 4)
        for i in range(4):
            a_ = math.pi * (0.15 + 0.7 * i / 3)
            p = lambda yy: RF.P(lu + 0.36 * math.cos(a_), yy, d0 + 0.36 * math.sin(a_) + 0.05)
            if y1 - y0 > 2.5:
                m.cyl(tuple(p(y0 + 2.2)), tuple(p(y1 + 0.9)), 0.01, "VH_Steel", 4)
        for yy in (max(y0 + 0.6, 1.6), y1 - 0.4):
            for sgn in (-1, 1):
                m.box(tuple(RF.P(lu + sgn * 0.22 - 0.03, yy - 0.03, 0.12)), tuple(RF.P(lu + sgn * 0.22 + 0.03, yy + 0.03, d0)), "VH_Steel")
    RF.box(m, lu - 0.7, lu + 0.7, 5.55, 5.62, 0.1, 1.15, "VH_Steel")       # landing grating
    for sgn in (-1, 1):
        m.cyl(tuple(RF.P(lu + sgn * 0.68, 5.62, 1.12)), tuple(RF.P(lu + sgn * 0.68, 6.65, 1.12)), 0.02, "VH_Steel", 6)
    m.cyl(tuple(RF.P(lu - 0.68, 6.65, 1.12)), tuple(RF.P(lu + 0.68, 6.65, 1.12)), 0.02, "VH_Steel", 6)
    m.cyl(tuple(RF.P(lu - 0.68, 6.1, 1.12)), tuple(RF.P(lu + 0.68, 6.1, 1.12)), 0.016, "VH_Steel", 6)
    s.stencil("WARDEN POST", "front", 0.0, 2.48, 0.13, 1.1, 0.075)
    # door lamp, sandbag sills and a sandbag wall by the door
    s.lamp("front", 0.85, 2.55, "Door lamp")
    s.rec["mounts"].append({"name": "Sandbag sill front", "prefab": "WG_SandbagRoofRow", "pos": [0.0, yl1, cz0 + 0.18], "yaw": 0})
    s.rec["mounts"].append({"name": "Sandbag wall by the door", "prefab": "WG_SandbagWall2mLow", "pos": [-1.15, 0.0, 1.75], "yaw": 8})
    s.roof_y = ry
    s.top_y = fy
    # colliders: shaft + talus, door step; the cabin is out of reach
    TR = HW + 0.55
    s.rec["colliders"].append({"name": "COL_Talus_body", "center": [0.0, 0.6, -(D + 0.55) / 2], "size": [2 * TR, 1.2, D + 0.55]})
    for sx_ in (-1, 1):
        s.rec["colliders"].append({"name": f"COL_Talus_front_{sx_}", "center": [sx_ * (0.78 + (TR - 0.78) / 2), 0.6, 0.275], "size": [TR - 0.78, 1.2, 0.55]})
    s.rec["colliders"].append({"name": "COL_Ladder", "center": [lu, 2.8, 0.75], "size": [0.9, 5.6, 0.7]})
    s.rec["colliders"].append({"name": "COL_Sandbags", "center": [-1.15, 0.5, 1.75], "size": [2.1, 1.0, 0.7], "yaw": 8})
    return s


def watchtower_lod2():
    parcel(2.2, 4.4, 0.0, 9.37)
    WM.set_state(2, random.Random(7), "Watchtower_l2")
    coll = bpy.data.collections.new("Watchtower_LOD2")
    bpy.context.scene.collection.children.link(coll)
    st, mt = Part("Watchtower_Masonry_LOD2"), Part("Watchtower_Metal_LOD2", False)
    HW, D, fy = 2.2, 4.4, 9.62
    st.box((-HW - 0.3, 0, -D - 0.3), (HW + 0.3, 1.2, 0.3), "VH_AshlarRough")
    st.box((-HW, 0, -D), (HW, fy, 0.06), "VH_Ashlar")
    O = 0.62
    mt.box((-HW - O, fy, -D - O), (HW + O, fy + 2.05, O), "WB_BlackSteel")
    mt.box((-HW - O - 0.02, fy + 1.15, O - 0.06), (HW + O + 0.02, fy + 1.75, O + 0.01), "WS_Glass")
    lo = [(-HW - O - 0.35, fy + 2.1, O + 0.35), (HW + O + 0.35, fy + 2.1, O + 0.35), (HW + O + 0.35, fy + 2.1, -D - O - 0.35), (-HW - O - 0.35, fy + 2.1, -D - O - 0.35)]
    hi = [(-0.75, fy + 2.9, -D / 2 + 0.75), (0.75, fy + 2.9, -D / 2 + 0.75), (0.75, fy + 2.9, -D / 2 - 0.75), (-0.75, fy + 2.9, -D / 2 - 0.75)]
    mt.closed_solid(lo + hi, [[0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7], [4, 5, 6, 7], [3, 2, 1, 0]], "WB_BlackSteel")
    mt.cyl((-0.45, fy + 2.9, -D / 2 - 0.4), (-0.45, fy + 6.3, -D / 2 - 0.4), 0.05, "VH_Steel", 6)
    for p in (st, mt):
        p.finalize()
    return [st.build(coll, flat=True), mt.build(coll, flat=True)]


# ====================================================================== PROCESSING 11 (ruined ore processing hall)
class Ruin:
    """Free-standing ruined masonry: double-faced ashlar walls with broken stepped tops, ashlar piers, steel."""

    def __init__(self, name, lod, tint, seed):
        self.name, self.lod = name, lod
        self.L = random.Random(seed)
        WM.set_state(lod, self.L, name)
        WM.WEAR["ground_y"] = 0.0
        WM.TINT[:] = list(tint)
        WM.reset_materials()
        self.coll = bpy.data.collections.new(f"{name}_LOD{lod}")
        bpy.context.scene.collection.children.link(self.coll)
        p = lambda s_, wear=True: Part(f"{name}_{s_}_LOD{lod}", wear=wear)
        self.mas, self.rub = p("Masonry"), p("Rubble")
        self.glass = p("Glass", False)
        self.metal, self.hard, self.roof = p("Metal", False), p("Hardware", False), p("Roof", False)
        self.canvas, self.sand, self.glow = p("Canvas", False), p("Sand", False), p("Glow", False)
        self.drips = DripSet(base=0.25, base_top=8.0, ground_y=0.0)
        self.scars = ScarSet(base=0.2)
        self.rec = {"colliders": [], "mounts": [], "lights": [], "notes": []}
        self.stencils = []

    def fdrip(self, F, ua, ub, top, length, strength, kind="grime", plane_off=0.0, soft=0.12):
        a, b = F.P(ua, 0, plane_off), F.P(ub, 0, plane_off)
        if abs(F.n.z) > 0.5:
            self.drips.add((0, 0, F.n.z), a.z, a.x, b.x, top, length, strength, kind, soft)
        else:
            self.drips.add((F.n.x, 0, 0), a.x, a.z, b.z, top, length, strength, kind, soft)

    def wall(self, Fo, Fi, u0, u1, T, top_fn, holes=(), key="w", courses=None):
        """Double-faced ashlar wall between u0..u1 on outer frame Fo / inner frame Fi (same u axis direction mirrored:
        Fi.P(u) must be the same point as Fo.P(u) moved through the wall). top_fn(u) = broken top height at u."""
        cs = courses or ([0.0, 0.55] + [round(0.55 + 0.42 * i, 3) for i in range(1, 24)])
        J = 0.009
        L = self.L
        for ci, (y0, y1) in enumerate(zip(cs, cs[1:])):
            if y1 > max(top_fn(u) for u in [lerp(u0, u1, k / 40) for k in range(41)]) + 1e-3:
                break
            rough = ci == 0
            mat = "VH_AshlarRough" if rough else "VH_Ashlar"
            rects = []
            for h in holes:
                if isinstance(h, dict):      # round-arched opening: rectangle to the springing, then the ring's extrados
                    uc, w, sill, spring, ring = h["arch"]
                    ro = w / 2 + ring
                    if y1 <= sill + 1e-3 or y0 >= spring + ro - 1e-3:
                        continue
                    if y0 < spring - 1e-3:
                        rects.append((uc - w / 2, uc + w / 2, y0, y1))
                    else:
                        half = math.sqrt(max(0.0, ro * ro - (y0 - spring) ** 2)) + 0.01
                        rects.append((uc - half, uc + half, y0, y1))
                else:
                    rects.append(h)
            for (sa, sb) in WM.course_intervals(u0, u1, rects, y0, y1):
                u = sa
                first = True
                while u < sb - 1e-4:
                    ln = L.uniform(0.6, 1.25)
                    if first:
                        ln *= (0.45 + 0.35 * L.random()) if ci % 2 else 1.0
                        first = False
                    if sb - (u + ln) < 0.3:
                        ln = sb - u
                    a, b = u, u + ln
                    u += ln
                    um = (a + b) / 2
                    if top_fn(um) < y1 - 1e-3:
                        continue
                    for F, side in ((Fo, 0), (Fi, 1)):
                        aa, bb = (a, b) if side == 0 else (-b, -a)
                        ashlar_block(self.mas, F, aa + J / 2, bb - J / 2, y0 + J / 2, y1 - J / 2, mat=mat, depth=0.062 if not rough else 0.1,
                                     back=-T / 2, key=(key, side, ci, round(a, 3)), top=True, bottom=(ci == 0), chip=0.18)
                        F.box(self.mas, aa - J, bb + J, y0, y1, 0.02, MORTAR_FRONT, "VH_Mortar", skip=("s0", "bottom", "top", "s1", "s3"))

    def arch(self, Fo, T, uc, w, sill, spring, ring, top_fn, key, n=11):
        """Through-stone sill and a semicircular ring of voussoirs (proud 7 cm of both faces) for an arched opening cut
        by a {"arch": ...} hole; voussoirs above the broken wall top are left out (a half-fallen arch). Mortar packing
        plates behind the ring on both faces fill the gaps the rectangular courses leave against the extrados."""
        ri, ro = w / 2, w / 2 + ring
        bid = self.mas.new_block(tint=stone_tint())
        c = [Fo.P(uc - ri - 0.1, sill - 0.13, 0.12), Fo.P(uc + ri + 0.1, sill - 0.13, 0.12), Fo.P(uc + ri + 0.1, sill, 0.12), Fo.P(uc - ri - 0.1, sill, 0.12),
             Fo.P(uc - ri - 0.1, sill - 0.13, -T - 0.12), Fo.P(uc + ri + 0.1, sill - 0.13, -T - 0.12), Fo.P(uc + ri + 0.1, sill, -T - 0.12), Fo.P(uc - ri - 0.1, sill, -T - 0.12)]
        vs, made = self.mas.hexa(c, "VH_Ashlar", bid)
        eroded_bevel(self.mas, list({e for f in made.values() for e in f.edges}), 0.014, 2, seg_len=0.2)
        rr = drng("arch", key)
        for i in range(n):
            a0, a1 = math.pi * i / n + 0.006, math.pi * (i + 1) / n - 0.006
            am = (a0 + a1) / 2
            r_out = ro + (0.06 if i == n // 2 else 0.0)          # keystone stands a little proud
            top_here = top_fn(uc + ro * math.cos(am))
            if spring + r_out * math.sin(a1 if am < math.pi / 2 else a0) > top_here - 0.05:
                continue
            P = lambda r_, a_, d_: Fo.P(uc + r_ * math.cos(a_), spring + r_ * math.sin(a_), d_)
            f0, f1 = 0.07 + (0.03 if i == n // 2 else 0.0), -T - 0.07 - (0.03 if i == n // 2 else 0.0)
            c = [P(ri, a0, f0), P(ri, a1, f0), P(r_out, a1, f0), P(r_out, a0, f0), P(ri, a0, f1), P(ri, a1, f1), P(r_out, a1, f1), P(r_out, a0, f1)]
            bid = self.mas.new_block(tint=stone_tint(), erode=0.012)
            vs, made = self.mas.hexa(c, "VH_Ashlar", bid)
            eroded_bevel(self.mas, list(made["bottom"].edges) + list(made["top"].edges), rr.uniform(0.012, 0.022), 2, seg_len=0.2)
            # mortar packing behind this voussoir, out past the extrados (fills the gaps the rectangular courses leave)
            for d0, d1 in ((0.02, MORTAR_FRONT), (-T - MORTAR_FRONT, -T - 0.02)):
                cc = [P(ro - 0.03, a0 - 0.006, d0), P(ro - 0.03, a1 + 0.006, d0), P(ro + 0.24, a1 + 0.006, d0), P(ro + 0.24, a0 - 0.006, d0),
                      P(ro - 0.03, a0 - 0.006, d1), P(ro - 0.03, a1 + 0.006, d1), P(ro + 0.24, a1 + 0.006, d1), P(ro + 0.24, a0 - 0.006, d1)]
                self.mas.hexa(cc, "VH_Mortar")
        self.fdrip(Fo, uc - ri - 0.1, uc + ri + 0.1, sill - 0.13, 2.4, 0.7, soft=0.15)

    def pier(self, cx, cz, w, top, key, jag=0.0, bands=()):
        """Square ashlar pier centred (cx, cz), side w, courses of 0.42 m; jag > 0 breaks the top course(s) unevenly."""
        cs = [0.0, 0.55]
        while cs[-1] + 0.42 <= top + 1e-3:
            cs.append(round(cs[-1] + 0.42, 3))
        if top - cs[-1] > 0.15:
            cs.append(round(top, 3))
        h = w / 2
        fr = [Frame((cx, 0, cz + h), (1, 0, 0), (0, 0, 1)), Frame((cx + h, 0, cz), (0, 0, -1), (1, 0, 0)),
              Frame((cx, 0, cz - h), (-1, 0, 0), (0, 0, -1)), Frame((cx - h, 0, cz), (0, 0, 1), (-1, 0, 0))]
        J = 0.009
        rr = drng("pier", key)
        n = len(cs) - 1
        for ci, (y0, y1) in enumerate(zip(cs, cs[1:])):
            rough = ci == 0
            mat = "VH_AshlarRough" if rough else "VH_Ashlar"
            own = ci % 2
            last = ci >= n - (2 if jag > 0 else 0)
            for k, F in enumerate(fr):
                if last and jag > 0 and rr.random() < jag * (0.5 + 0.5 * (ci - (n - 3))):
                    continue        # broken top: block knocked off
                ext = 0.062 if not rough else 0.1
                if k % 2 == own:    # owning faces: a 0.3 m band across the whole face, round both corners
                    a, b = -h - ext, h + ext
                else:               # the other two faces: between the owning bands
                    a, b = -h + 0.30, h - 0.30
                ashlar_block(self.mas, F, a + J / 2, b - J / 2, y0 + J / 2, y1 - J / 2, mat=mat, depth=ext,
                             back=-0.30, key=(key, k, ci), top=True, bottom=(ci == 0), chip=0.22, bevel=(0.014, 0.028))
        core_top = cs[max(1, n - 2)] if jag > 0 else cs[-1]
        self.mas.box((cx - h + 0.03, cs[0], cz - h + 0.03), (cx + h - 0.03, core_top - 0.02, cz + h - 0.03), "VH_Mortar")
        if jag > 0:     # rubble and sand lodged on the broken top
            for i in range(4):
                self.block((cx + rr.uniform(-h * 0.6, h * 0.6), core_top + 0.12, cz + rr.uniform(-h * 0.6, h * 0.6)),
                           (rr.uniform(0.25, 0.45), rr.uniform(0.15, 0.3), rr.uniform(0.25, 0.4)), (rr.uniform(-0.4, 0.4), rr.uniform(0, 3), rr.uniform(-0.4, 0.4)),
                           mat="VH_AshlarRough")
        for by in bands:
            if by > top - 0.3:
                continue
            for F in fr:
                F.box(self.metal, -h - 0.08, h + 0.08, by - 0.13, by + 0.13, 0.07, 0.1, "WB_BlackSteel")
                if self.lod == 0:
                    u = -h + 0.02
                    while u < h:
                        for yy in (by - 0.07, by + 0.07):
                            self.hard.sphere(tuple(F.P(u, yy, 0.1)), 0.012, "VH_Steel", 6, hemi_axis=tuple(F.n))
                        u += 0.17
                self.fdrip(F, -h - 0.08, h + 0.08, by - 0.13, 1.5, 0.8, "rust", plane_off=0.07, soft=0.08)
        for F in fr:
            self.fdrip(F, -h, h, top, 3.0, 0.7, soft=0.15)
        self.rec["colliders"].append({"name": f"COL_Pier_{key}", "center": [cx, top / 2, cz], "size": [w + 0.2, top, w + 0.2]})
        return fr

    def bar(self, part, a, b, w, d, mat):
        """Rectangular bar from a to b (w across horizontally, d vertical-ish)."""
        a, b = Vector(a), Vector(b)
        t = (b - a).normalized()
        up = Vector((0, 1, 0)) if abs(t.y) < 0.95 else Vector((1, 0, 0))
        sx = t.cross(up).normalized() * (w / 2)
        sy = sx.cross(t).normalized() * (d / 2)
        c = [a - sx - sy, a + sx - sy, a + sx + sy, a - sx + sy, b - sx - sy, b + sx - sy, b + sx + sy, b - sx + sy]
        # hexa wants bottom ring then top ring: treat the a-end as bottom
        return part.hexa(c, mat)

    def ibeam(self, part, a, b, h, w, mat):
        a, b = Vector(a), Vector(b)
        up = Vector((0, 1, 0))
        self.bar(part, a, b, 0.02, h - 0.04, mat)
        self.bar(part, a + up * (h / 2 - 0.01), b + up * (h / 2 - 0.01), w, 0.02, mat)
        self.bar(part, a - up * (h / 2 - 0.01), b - up * (h / 2 - 0.01), w, 0.02, mat)

    def truss(self, a, b, depth, mat, panels=6, broken_at=None):
        """Pratt truss in the vertical plane through a-b (top chord a->b at the given points, bottom chord depth below)."""
        a, b = Vector(a), Vector(b)
        dn = Vector((0, -depth, 0))
        pts_t = [a.lerp(b, i / panels) for i in range(panels + 1)]
        pts_b = [p + dn for p in pts_t]
        m = self.metal
        for i in range(panels):
            if broken_at is not None and i == broken_at:
                continue
            self.bar(m, pts_t[i], pts_t[i + 1], 0.16, 0.14, mat)
            self.bar(m, pts_b[i], pts_b[i + 1], 0.14, 0.12, mat)
        for i in range(panels + 1):
            if broken_at is not None and i in (broken_at, broken_at + 1) and 0 < i < panels:
                continue
            self.bar(m, pts_t[i], pts_b[i], 0.1, 0.1, mat)
        for i in range(panels):
            if broken_at is not None and i == broken_at:
                continue
            if i < panels / 2:
                self.bar(m, pts_t[i], pts_b[i + 1], 0.09, 0.09, mat)
            else:
                self.bar(m, pts_b[i], pts_t[i + 1], 0.09, 0.09, mat)
        return pts_t, pts_b

    def block(self, c, size, rot, mat="VH_Ashlar", part=None):
        """A loose fallen ashlar block: centre, (sx, sy, sz), rotation (rx, ry, rz) radians, eroded edges."""
        from mathutils import Euler
        part = part or self.rub
        R = Euler(rot, "XYZ").to_matrix()
        hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
        loc = [(-hx, -hy, -hz), (hx, -hy, -hz), (hx, -hy, hz), (-hx, -hy, hz), (-hx, hy, -hz), (hx, hy, -hz), (hx, hy, hz), (-hx, hy, hz)]
        cv = Vector(c)
        corners = [cv + R @ Vector(p) for p in loc]
        bid = part.new_block(tint=stone_tint("rough" if mat.endswith("Rough") else "ashlar"), erode=0.014)
        vs, made = part.hexa(corners, mat, bid)
        eroded_bevel(part, list({e for f in made.values() for e in f.edges}), self.L.uniform(0.015, 0.03), 2, seg_len=0.18)

    def mound(self, c, rx, rz, h, mat="VH_Sand"):
        fs = self.sand.sphere((0, 0, 0), 1.0, mat, 12 if self.lod == 0 else 8, hemi_axis=(0, 1, 0))
        for v in {v for f in fs for v in f.verts}:
            v.co = Vector((c[0] + v.co.x * rx, c[1] + max(0.0, v.co.y) * h - 0.02, c[2] + v.co.z * rz))

    def stencil(self, text, F, u, y, size, width_limit, d, mat="WB_StencilPaint"):
        c = F.P(u, y, d)
        ob, w = lettering(text, STENCIL_FONT, size, tuple(c), 0.004, width_limit, mat, self.coll, f"{self.name}_Stencil_{len(self.stencils)}_LOD{self.lod}",
                          lod=1, facing=tuple(F.n))   # painted: no bevel, coarse curves
        self.stencils.append(ob)

    def finish(self):
        parts = [self.mas, self.rub, self.metal, self.roof, self.canvas, self.sand, self.glow, self.hard, self.glass]
        finalize_parts(parts)
        ao = WM.AOBaker([self.mas, self.rub, self.metal, self.roof], ground_y=0.0, samples=20 if self.lod == 0 else 8)
        objs = []
        if len(self.mas.bm.faces):
            objs.append(self.mas.build(self.coll, ao=ao, drips=self.drips, ground_y=0.0, scars=self.scars))
        if len(self.rub.bm.faces):
            objs.append(self.rub.build(self.coll, ao=ao, drips=self.drips, ground_y=0.0, scars=self.scars, splash=0.5))
        for p_ in (self.metal, self.roof, self.canvas, self.sand, self.glow, self.hard):
            if len(p_.bm.faces):
                objs.append(p_.build(self.coll))
        if len(self.glass.bm.faces):
            objs.append(self.glass.build(self.coll, flat=True))
        objs += self.stencils
        self.rec["triangles"] = tri_count(objs)
        self.rec["objects"] = {o.name: sum(len(pl.vertices) - 2 for pl in o.data.polygons) for o in objs}
        return objs


def processing_hall(lod):
    """PROCESSING 11: roofless ruin of a pre-war ore processing hall (NE yard). Replaces `Ward district retrofit/
    Processing hall ruin`. Root at world (36, 0, 33), yaw 0: local = world - (36, 0, 33). Footprint x -8..8, z -5.4..5.4
    (world x 28..44, z 27.6..38.4), clear of the NE watchtower's door and ladder (world x 40.5..45, z > 36.5).
    Concept: concept/hall_concept_v1.png."""
    r = Ruin("Processing11", lod, (1.03, 0.97, 0.88), 1111)
    m = r.metal
    T = 0.8
    ZS = -5.4                      # south (city) wall outer face
    # south wall: outer face looks south (-z); u runs east->west on the outer frame so the inner frame mirrors it
    Fo = Frame((0, 0, ZS), (-1, 0, 0), (0, 0, -1))
    Fi = Frame((0, 0, ZS + T), (1, 0, 0), (0, 0, 1))

    def south_top(u):          # u = -x
        x = -u
        if x < -4.0:
            return 8.38
        if x < -2.2:
            return 8.38 - (x + 4.0) * 0.25
        if x < 1.6:
            return 7.54
        if x < 3.0:
            return 7.54 - (x - 1.6) * 1.2
        if x < 5.0:
            return 5.44
        return max(2.2, 5.44 - (x - 5.0) * 1.1)

    win = [(-6.3, 2.65, 4.33), (-3.3, 2.65, 4.33), (5.6, 2.65, 3.91)]     # (x centre, sill, springing) round-arched windows
    WW, RING = 1.9, 0.42
    door = (1.6, 3.4, 4.33)                                               # (x centre, width, head)
    holes = []
    for (x, y0, y1) in win:
        holes.append({"arch": (-x, WW, y0, y1, RING)})
    holes += [(-door[0] - door[1] / 2, -door[0] + door[1] / 2, 0.0, door[2]), (-door[0] - door[1] / 2 - 0.3, -door[0] + door[1] / 2 + 0.3, door[2], door[2] + 0.42)]
    # shell holes punched through (stepped outlines made of block-sized gaps)
    holes += [(-(-1.4) - 0.7, -(-1.4) + 0.6, 5.59, 6.43), (-(-1.4) - 0.35, -(-1.4) + 0.3, 6.43, 6.85), (-(-0.9) - 0.4, -(-0.9) + 0.4, 5.17, 5.59)]
    r.wall(Fo, Fi, -8.0, 8.0, T, south_top, holes, key="south")
    # window dressings: through-stone sills, voussoir rings (broken where the wall top has fallen), bent grilles
    for (x, y0, y1) in win:
        u = -x
        r.arch(Fo, T, u, WW, y0, y1, RING, south_top, key=("s", x))
        # grille in the outer reveal: some bars missing, two bent outwards
        rr = drng("grille", x)
        for k in range(9):
            if rr.random() < 0.2:
                continue
            ux = lerp(u - 0.8, u + 0.8, k / 8)
            bend = 0.18 if rr.random() < 0.2 else 0.0
            ytop = min(y1 + math.sqrt(max(0.0, (WW / 2) ** 2 - (ux - u) ** 2)) - 0.04, south_top(ux) - 0.25)
            p0, p1, p2 = Fo.P(ux, y0, -0.12), Fo.P(ux, lerp(y0, ytop, 0.5), -0.12 + bend), Fo.P(ux, ytop, -0.12)
            m.tube([tuple(p0), tuple(p1), tuple(p2)], 0.016, "WB_BlackSteel", 6)
            r.fdrip(Fo, ux - 0.05, ux + 0.05, y0, 2.0, 0.9, "rust", soft=0.04)
        for yy in (lerp(y0, y1, 0.25), lerp(y0, y1, 0.75)):
            Fo.box(m, u - 0.88, u + 0.88, yy - 0.025, yy + 0.025, -0.15, -0.09, "WB_BlackSteel")
        r.scars.plume((0, 0, -1), ZS, -x - 1.0, -x + 1.0, y1, 2.4, 0.85) if False else None
    # door: riveted steel box lintel, jamb stones, worn steel threshold
    dx, dw, dh = door
    u = -dx
    for F, sgn in ((Fo, 1), (Fi, -1)):
        uu = u if sgn > 0 else -u
        F.box(m, uu - dw / 2 - 0.3, uu + dw / 2 + 0.3, dh, dh + 0.42, -T / 2, 0.1, "VH_PaintedSteel")
        if lod == 0:
            k = uu - dw / 2 - 0.22
            while k < uu + dw / 2 + 0.25:
                for yy in (dh + 0.08, dh + 0.34):
                    r.hard.sphere(tuple(F.P(k, yy, 0.1)), 0.013, "VH_Steel", 6, hemi_axis=tuple(F.n))
                k += 0.24
        r.fdrip(F, uu - dw / 2 - 0.3, uu + dw / 2 + 0.3, dh, 1.6, 0.9, "rust", soft=0.15)
    Fo.box(m, u - dw / 2, u + dw / 2, 0.0, 0.02, -T, 0.0, "VH_Steel")
    # soot plumes over the burned openings, heavy battle damage on the city face
    for (x0, x1, y0, h) in ((-7.3, -5.3, 5.17, 3.0), (-4.3, -2.3, 5.17, 2.4), (-0.1, 3.3, 4.75, 2.6), (4.6, 6.6, 4.75, 0.7)):
        r.scars.plume((0, 0, -1), ZS, x0, x1, y0, h, 0.85)
    for c, rad, st in (((-1.2, 6.0, ZS - 0.06), 1.6, 1.0), ((4.2, 3.6, ZS - 0.06), 1.4, 0.95), ((-5.0, 1.4, ZS - 0.06), 1.0, 0.8),
                       ((7.0, 1.8, ZS - 0.06), 1.3, 1.0), ((-7.2, 6.8, ZS - 0.06), 0.9, 0.7), ((2.8, 6.5, ZS + T + 0.06), 1.2, 0.8)):
        r.scars.impact(c, rad, st)
    WM.scatter_impacts(r.scars, [(Fo, -8.0, 8.0)], 7, random.Random(31), 0.5, 7.5, 0.4, 1.0)
    r.stencil("PROCESSING 11", Fo, -dx, dh + 0.85, 0.42, 3.6, 0.075)
    r.rec["colliders"] += [{"name": "COL_SouthWall_W", "center": [(-8.0 + dx - dw / 2) / 2, 4.0, ZS + T / 2], "size": [dx - dw / 2 + 8.0, 8.0, T + 0.1]},
                           {"name": "COL_SouthWall_E", "center": [(dx + dw / 2 + 8.0) / 2, 2.7, ZS + T / 2], "size": [8.0 - dx - dw / 2, 5.4, T + 0.1]},
                           {"name": "COL_SouthWall_OverDoor", "center": [dx, (dh + 7.5) / 2, ZS + T / 2], "size": [dw, 7.5 - dh, T + 0.1]}]
    # banner between the west windows on the city face
    rr_b = drng("hallbanner")
    bm = r.canvas.bm
    mi = r.canvas.mi("VH_Banner")
    nxb, nyb = (6, 14) if lod == 0 else (2, 3)
    rows = []
    for j in range(nyb + 1):
        t = j / nyb
        row = []
        for i in range(nxb + 1):
            sx_ = i / nxb
            y = 7.85 - 1.6 * t + (rr_b.uniform(0.0, 0.18) * (1 - 0.6 * math.sin(math.pi * sx_)) if j == nyb else 0.0)
            row.append(bm.verts.new(Fo.P(4.8 - 0.4 + 0.8 * sx_, y, 0.11 + 0.02 * math.sin(math.pi * sx_) * math.sin(math.pi * t))))
        rows.append(row)
    for j in range(nyb):
        for i in range(nxb):
            f = bm.faces.new([rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]])
            f.material_index = mi
            f.normal_update()
            if f.normal.dot(Fo.n) < 0:
                f.normal_flip()
    m.cyl(tuple(Fo.P(4.3, 7.9, 0.12)), tuple(Fo.P(5.3, 7.9, 0.12)), 0.02, "VH_Steel", 8)
    # west wall: outer face looks west; stepped down towards the north
    Wo = Frame((-8.0, 0, 0), (0, 0, -1), (-1, 0, 0))
    Wi = Frame((-8.0 + T, 0, 0), (0, 0, 1), (1, 0, 0))

    def west_top(u):           # u = -z
        z = -u
        if z < -1.0:
            return 8.38 if z < -3.0 else 6.7
        if z < 2.0:
            return 5.0
        return max(1.39, 5.0 - (z - 2.0) * 1.3)
    wholes = [{"arch": (2.4, 1.3, 2.65, 3.91, 0.36)}]
    r.wall(Wo, Wi, -5.4 + T, 5.4, T, west_top, wholes, key="west")
    r.arch(Wo, T, 2.4, 1.3, 2.65, 3.91, 0.36, west_top, key=("w", 2.4))
    r.rec["colliders"].append({"name": "COL_WestWall", "center": [-8.0 + T / 2, 3.0, 0.0 + T / 2], "size": [T + 0.1, 6.0, 10.8 - T]})
    # piers: a row of three on z = -1.4 and two on z = 2.6 (the north-east one toppled), steel bands
    piers = {"p1": (-4.8, -1.4, 8.11, 0.0), "p2": (0.0, -1.4, 8.11, 0.0), "p3": (4.8, -1.4, 5.17, 0.8),
             "p4": (-4.8, 2.6, 8.11, 0.0), "p5": (0.0, 2.6, 6.43, 0.9)}
    for k, (px, pz, ph, jag) in piers.items():
        r.pier(px, pz, 1.1, ph, k, jag=jag, bands=(1.3, 4.1, 6.9))
    # toppled pier: stump and a line of fallen courses lying east-south-east, half buried in sand
    r.pier(4.8, 2.6, 1.1, 1.39, "p6", jag=0.6, bands=())
    rr = drng("topple")
    for i in range(9):
        t = i / 8
        c = (5.6 + t * 3.6 * 0.85, 0.32 + rr.uniform(-0.05, 0.12), 2.2 - t * 3.6 * 0.5)
        r.block(c, (1.1 + rr.uniform(-0.1, 0.1), 0.42, 0.55 + rr.uniform(-0.05, 0.1)), (rr.uniform(-0.2, 0.2), 0.55 + rr.uniform(-0.3, 0.3), rr.uniform(-0.25, 0.25)))
        if rr.random() < 0.6:
            r.block((c[0] + rr.uniform(-0.4, 0.4), 0.75, c[2] + rr.uniform(-0.4, 0.4)), (0.55, 0.42, 0.5), (rr.uniform(-0.6, 0.6), rr.uniform(0, 3), rr.uniform(-0.6, 0.6)))
    r.rec["colliders"].append({"name": "COL_ToppledPier", "center": [7.1, 0.5, 1.3], "size": [3.6, 1.0, 2.4], "yaw": 27})
    # rubble heaps under the broken wall tops and the shell holes; sand drifts
    for (cx, cz, rad, n_) in ((6.2, -4.3, 1.6, 26), (3.6, -4.2, 1.1, 14), (-1.0, -3.9, 0.9, 10), (-7.0, 3.6, 1.3, 18), (6.6, -2.2, 0.9, 8)):
        rr2 = drng("heap", cx, cz)
        for i in range(n_):
            a_ = rr2.uniform(0, 2 * math.pi)
            d_ = rad * math.sqrt(rr2.random())
            h_ = 0.2 + (1 - d_ / rad) * 0.55 * rr2.random()
            sz = (rr2.uniform(0.35, 0.9), rr2.uniform(0.25, 0.42), rr2.uniform(0.3, 0.6))
            r.block((cx + math.cos(a_) * d_, h_, cz + math.sin(a_) * d_), sz, (rr2.uniform(-0.8, 0.8), rr2.uniform(0, 3.1), rr2.uniform(-0.8, 0.8)),
                    mat="VH_AshlarRough" if rr2.random() < 0.4 else "VH_Ashlar")
        r.mound((cx, 0.0, cz), rad * 1.15, rad * 1.0, 0.45)
        r.rec["colliders"].append({"name": f"COL_Heap_{cx}_{cz}", "center": [cx, 0.35, cz], "size": [rad * 1.6, 0.7, rad * 1.6]})
    for (cx, cz, rx, rz, h) in ((-6.0, -4.3, 1.6, 0.6, 0.18), (-2.6, 4.2, 2.2, 1.0, 0.16), (2.0, -4.5, 1.2, 0.5, 0.12), (-7.0, 0.5, 0.5, 2.0, 0.2)):
        r.mound((cx, 0.0, cz), rx, rz, h)
    # crane rails (I-beams) on steel corbels along the pier rows; the east end of the south rail snapped and hangs
    for pz, x0, x1 in ((-1.4, -7.2, 4.2), (2.6, -7.2, 0.6)):
        r.ibeam(m, (x0, 7.15, pz), (x1, 7.15, pz), 0.42, 0.26, "WB_BlackSteel")
        for px in (-4.8, 0.0):
            for sgn in (-1, 1):
                m.box((px - 0.2, 6.55, pz + sgn * 0.55), (px + 0.2, 6.95, pz + sgn * 0.75), "WB_BlackSteel")
            m.box((px - 0.25, 6.9, pz - 0.75), (px + 0.25, 6.95, pz + 0.75), "WB_BlackSteel")
    r.ibeam(m, (4.2, 7.15, -1.4), (6.4, 4.9, -1.25), 0.42, 0.26, "WB_BlackSteel")      # snapped end, hanging over p3
    # west ends of the rails sit in pockets in the west wall
    # stranded crane bridge across the rails, trolley, chains and hook block
    bx = -2.6
    r.ibeam(m, (bx, 7.75, -2.0), (bx, 7.75, 3.2), 0.6, 0.3, "WS_PaintYellow")
    r.ibeam(m, (bx + 0.7, 7.75, -2.0), (bx + 0.7, 7.75, 3.2), 0.6, 0.3, "WS_PaintYellow")
    for zz in (-1.4, 2.6):
        m.box((bx - 0.3, 7.37, zz - 0.35), (bx + 1.0, 7.5, zz + 0.35), "WS_PaintYellow")
    m.box((bx - 0.2, 7.95, 0.2), (bx + 0.9, 8.5, 1.3), "VH_PaintedSteel")
    for dz in (0.55, 0.95):
        m.cyl((bx + 0.35, 7.9, dz), (bx + 0.35 + 0.05, 3.6, dz + 0.05), 0.015, "VH_Steel", 6)
    m.box((bx + 0.12, 3.05, 0.55), (bx + 0.62, 3.65, 1.05), "WS_PaintYellow")
    m.tube([(bx + 0.37, 3.05, 0.8), (bx + 0.37, 2.75, 0.8), (bx + 0.22, 2.6, 0.8), (bx + 0.37, 2.45, 0.8), (bx + 0.55, 2.62, 0.8)], 0.05, "VH_Steel", 8)
    # roof trusses: one intact from the south wall to pier p4 (x -4.8), one sagged onto the broken pier p5 (x 0),
    # a third collapsed in the middle bay; purlins and a few holed corrugated sheets, two hanging loose
    # top chords rest on the masonry: wall courses top out at 8.11 (x < -4) and 7.27 (x ~ 0); piers p4 8.11, p5 6.43
    pt_a, _ = r.truss((-4.8, 8.11 + 0.08, ZS + 0.4), (-4.8, 8.11 + 0.08, 2.6), 1.4, "WB_BlackSteel", panels=6)
    pt_b, _ = r.truss((0.0, 7.27 + 0.08, ZS + 0.4), (0.0, 6.43 + 0.08, 2.6), 1.2, "WG_RustSteel", panels=6, broken_at=4)
    for i in range(0, 2):       # purlins from truss A to the west wall where it still stands full height (z < -3)
        a_, b_ = pt_a[i], (Vector((-7.6, pt_a[i].y, pt_a[i].z)))
        r.bar(m, a_ + Vector((0, 0.1, 0)), b_ + Vector((0, 0.1, 0)), 0.08, 0.14, "WB_BlackSteel")
    for i in (0, 2, 4):         # purlins between trusses A and B (sagging with B)
        r.bar(m, pt_a[i] + Vector((0, 0.1, 0)), pt_b[i] + Vector((0, 0.1, 0)), 0.08, 0.14, "WG_RustSteel")
    rrs = drng("sheets")
    for i in range(2):
        z0 = ZS + 0.5 + i * 1.25
        y0 = pt_a[i].y + 0.2
        fs = corrugated_sheet(r.roof, -7.9, -4.85, (y0 - 0.06, z0), (y0, z0 + 1.15), "WS_Corrugated", lod=lod)
        if i == 5:   # loose sheet hanging down from one corner
            piv = Vector((-4.85, y0, z0))
            for v in {v for f in fs for v in f.verts}:
                q = v.co - piv
                v.co = piv + Vector((q.x * 0.35 + q.y, -abs(q.x) * 0.9 + q.y, q.z))
    for (c, rot) in (((2.4, 0.35, 0.6), (0.4, 0.8, 0.15)), ((-3.6, 0.08, 4.2), (0.05, 2.1, 0.02)), ((6.8, 0.6, -3.0), (-0.6, 0.2, 0.4))):
        fs = corrugated_sheet(r.roof, -1.2, 1.2, (0.0, -0.55), (0.0, 0.55), "WS_Corrugated", lod=lod)
        from mathutils import Euler
        R = Euler(rot, "XYZ").to_matrix()
        for v in {v for f in fs for v in f.verts}:
            v.co = Vector(c) + R @ v.co
    # fallen bent truss segment in the middle bay
    r.bar(m, (1.0, 0.25, 0.4), (3.6, 1.6, 1.8), 0.16, 0.14, "WG_RustSteel")
    r.bar(m, (1.0, 0.25, 0.4), (1.3, 1.25, 0.2), 0.1, 0.1, "WG_RustSteel")
    r.bar(m, (2.3, 0.95, 1.1), (2.0, 0.1, 1.5), 0.09, 0.09, "WG_RustSteel")
    r.bar(m, (3.6, 1.6, 1.8), (3.3, 0.2, 2.3), 0.1, 0.1, "WG_RustSteel")
    r.rec["colliders"].append({"name": "COL_FallenTruss", "center": [2.3, 0.6, 1.1], "size": [3.0, 1.2, 1.0], "yaw": -28})
    # pockets / bearing plates where the rails meet the west wall
    for pz in (-1.4, 2.6):
        m.box((-8.0 + T - 0.02, 6.85, pz - 0.3), (-7.15, 7.45, pz + 0.3), "WB_BlackSteel")
    r.rec["notes"] += ["south (city) wall with three tall barred windows, a cart door with a riveted lintel, shell holes, soot",
                       "piers p1-p5 + toppled p6, crane rails, stranded crane bridge, intact/sagged/collapsed trusses, sheets"]
    r.top_y = 8.6
    return r


def processing_hall_lod2():
    WM.set_state(2, random.Random(9), "Processing11_l2")
    coll = bpy.data.collections.new("Processing11_LOD2")
    bpy.context.scene.collection.children.link(coll)
    st, mt = Part("Processing11_Masonry_LOD2"), Part("Processing11_Metal_LOD2", False)
    st.box((-8.0, 0, -5.4), (-1.0, 8.2, -4.6), "VH_Ashlar")
    st.box((-1.0, 4.6, -5.4), (3.3, 7.5, -4.6), "VH_Ashlar")
    st.box((3.3, 0, -5.4), (8.0, 4.4, -4.6), "VH_Ashlar")
    st.box((-8.0, 0, -4.6), (-7.2, 6.0, 5.4), "VH_Ashlar")
    for (px, pz, ph) in ((-4.8, -1.4, 8.2), (0.0, -1.4, 8.2), (4.8, -1.4, 5.0), (-4.8, 2.6, 8.2), (0.0, 2.6, 6.4)):
        st.box((px - 0.55, 0, pz - 0.55), (px + 0.55, ph, pz + 0.55), "VH_Ashlar")
    mt.box((-7.2, 6.95, -1.6), (4.2, 7.35, -1.2), "WB_BlackSteel")
    mt.box((-7.2, 6.95, 2.4), (0.6, 7.35, 2.8), "WB_BlackSteel")
    mt.box((-2.9, 7.45, -2.0), (-1.6, 8.05, 3.2), "WS_PaintYellow")
    mt.box((-4.9, 7.0, -5.0), (-4.7, 8.4, 2.6), "WB_BlackSteel")
    mt.box((-0.1, 6.4, -5.0), (0.1, 7.6, 2.6), "WG_RustSteel")
    for p_ in (st, mt):
        p_.finalize()
    return [st.build(coll, flat=True), mt.build(coll, flat=True)]


# ====================================================================== AQUIFER 3 pump station
def riveted_tank(s, x, z, r, h, mat, plinth_h=0.55, patched=False, ladder_a=0.0, lod=0):
    """Riveted steel storage tank on a round stone plinth: banded shell, conical roof, caged ladder, outlet."""
    m, hd = s.metal, s.hard
    # plinth: eight dressed wedge blocks round a mortar core
    n = 8
    for i in range(n):
        a0, a1 = 2 * math.pi * i / n + 0.01, 2 * math.pi * (i + 1) / n - 0.01
        ro = r + 0.22
        pts = [(x + math.cos(a) * rr_, y_, z + math.sin(a) * rr_) for (a, rr_) in ((a0, r - 0.3), (a1, r - 0.3), (a1, ro), (a0, ro)) for y_ in (0.0,)]
        top = [(px, plinth_h, pz) for (px, _, pz) in pts]
        top[2] = (x + math.cos(a1) * (ro - 0.05), plinth_h, z + math.sin(a1) * (ro - 0.05))
        top[3] = (x + math.cos(a0) * (ro - 0.05), plinth_h, z + math.sin(a0) * (ro - 0.05))
        bid = s.pod.new_block(tint=stone_tint("rough"), erode=0.012)
        vs, made = s.pod.hexa(pts + top, "VH_AshlarRough", bid, skip=("bottom",))
        eroded_bevel(s.pod, list(made["top"].edges), 0.02, 2, seg_len=0.2)
    y0 = plinth_h
    m.cyl((x, y0, z), (x, y0 + h, z), r, mat, 24 if lod == 0 else 14)
    m.cyl((x, y0 + h, z), (x, y0 + h + 0.7, z), r + 0.04, mat, 24 if lod == 0 else 14, r2=0.35)
    m.cyl((x, y0 + h + 0.7, z), (x, y0 + h + 0.95, z), 0.32, "VH_Steel", 12)
    k = 1
    while k * 1.15 < h:
        yy = y0 + k * 1.15
        m.cyl((x, yy - 0.04, z), (x, yy + 0.04, z), r + 0.018, "WB_BlackSteel", 24 if lod == 0 else 14)
        if lod == 0:
            for j in range(28):
                a = 2 * math.pi * j / 28
                hd.sphere((x + math.cos(a) * (r + 0.02), yy, z + math.sin(a) * (r + 0.02)), 0.014, "VH_Steel", 5)
        k += 1
    m.cyl((x, y0, z), (x, y0 + 0.08, z), r + 0.05, "WB_BlackSteel", 24 if lod == 0 else 14)
    if patched:
        for (a, yy, w_, h_) in ((ladder_a + 2.2, y0 + 2.1, 0.7, 0.55), (ladder_a + 2.6, y0 + 3.3, 0.5, 0.45)):
            c = Vector((x + math.cos(a) * (r + 0.02), yy, z + math.sin(a) * (r + 0.02)))
            nrm = Vector((math.cos(a), 0, math.sin(a)))
            tng = Vector((-math.sin(a), 0, math.cos(a)))
            pts = [c - tng * w_ / 2 - Vector((0, h_ / 2, 0)), c + tng * w_ / 2 - Vector((0, h_ / 2, 0)), c + tng * w_ / 2 + Vector((0, h_ / 2, 0)), c - tng * w_ / 2 + Vector((0, h_ / 2, 0))]
            m.hexa(pts + [p_ + nrm * 0.025 for p_ in pts], "WB_BlackSteel")
            s.scars.impact(tuple(c), 0.6, 0.9)
    # caged ladder at angle ladder_a
    nrm = Vector((math.cos(ladder_a), 0, math.sin(ladder_a)))
    tng = Vector((-math.sin(ladder_a), 0, math.cos(ladder_a)))
    base = Vector((x, 0, z)) + nrm * (r + 0.22)
    for sg in (-1, 1):
        m.cyl(tuple(base + tng * sg * 0.2 + Vector((0, y0 + 0.2, 0))), tuple(base + tng * sg * 0.2 + Vector((0, y0 + h + 0.9, 0))), 0.02, "VH_Steel", 6)
    yy = y0 + 0.4
    while yy < y0 + h + 0.6:
        hd.cyl(tuple(base - tng * 0.2 + Vector((0, yy, 0))), tuple(base + tng * 0.2 + Vector((0, yy, 0))), 0.013, "VH_Steel", 6)
        yy += 0.3
    yy = y0 + 2.4
    while yy < y0 + h + 0.8:
        pts = [base + tng * 0.36 * math.cos(math.pi * i_ / 6) + nrm * (0.36 * math.sin(math.pi * i_ / 6)) + Vector((0, yy, 0)) for i_ in range(7)]
        m.tube([tuple(p_) for p_ in pts], 0.011, "VH_Steel", 4)
        yy += 0.75
    # roof handrail ring
    m.tube([(x + math.cos(2 * math.pi * j / 16) * (r - 0.1), y0 + h + 0.9, z + math.sin(2 * math.pi * j / 16) * (r - 0.1)) for j in range(17)], 0.018, "VH_Steel", 5)


def aquifer(lod):
    """AQUIFER 3 pump station (SW quadrant). Replaces `Ward district retrofit/Aquifer pump station` on its site: pump hall
    front at world z -30 (root (-35, 0, -30), yaw 0, street face north to the mining droid's patrol), tanks behind at
    world z -39, well head east. Concept: concept/aquifer_concept_v1.png."""
    parcel(4.5, 6.4, 0.0, 4.75)
    s = Building("Aquifer3", lod, (1.06, 0.99, 0.9), 3303, upper=[5.0, 5.42, 5.84, 6.26])
    HW, D = s.HW, s.D
    m, hd = s.metal, s.hard
    s.portal("front", -1.4, 2.4, 3.07, kind="double", transom=0.42, arch=True)
    for u in (1.7, 3.3):
        s.window("front", u - 0.45, u + 0.45, 1.39, 3.07, kind="bars")
    for u in (-3.1, 2.6):
        s.window("front", u - 0.4, u + 0.4, 5.0, 5.84, kind="bars", lintel=True)
    s.window("right", 4.2, 5.2, 1.81, 3.49, kind="bars")
    s.window("left", -2.6, -1.6, 1.81, 3.49, kind="bars")
    s.window("left", -5.2, -4.2, 1.81, 3.49, kind="bars")
    s.portal("rear", 2.6, 1.0, 2.65, kind="single", door_mat="WS_PaintTeal", arch=False, transom=0.0)
    s.scorch("front", 1.2, 3.8, 3.07, 2.2, 0.7)
    s.scorch("left", -5.3, -4.1, 3.49, 2.0, 0.6)
    s.walls()
    s.top(cornice_h=0.45)
    ry = s.roof_y
    # clerestory ventilation monitor on the roof deck: steel frame, louvres on the long sides, pitched corrugated cap
    mx0, mx1, mz0, mz1 = -3.2, 3.2, -1.6, -4.8
    mh = 1.35
    for x in (mx0, 0.0, mx1):
        for z in (mz0, mz1):
            m.box((x - 0.07, ry, z - 0.07), (x + 0.07, ry + mh, z + 0.07), "WB_BlackSteel")
    for z in (mz0, mz1):
        m.box((mx0, ry + mh - 0.12, z - 0.07), (mx1, ry + mh, z + 0.07), "WB_BlackSteel")
        m.box((mx0, ry, z - 0.07), (mx1, ry + 0.15, z + 0.07), "WB_BlackSteel")
        sgn = 1 if z == mz0 else -1
        nl = 7 if lod == 0 else 3
        for k in range(nl):
            yy = lerp(ry + 0.25, ry + mh - 0.22, k / (nl - 1))
            c = [(mx0 + 0.08, yy - 0.06, z), (mx1 - 0.08, yy - 0.06, z), (mx1 - 0.08, yy - 0.06, z + sgn * 0.12), (mx0 + 0.08, yy - 0.06, z + sgn * 0.12),
                 (mx0 + 0.08, yy + 0.06, z - sgn * 0.04), (mx1 - 0.08, yy + 0.06, z - sgn * 0.04), (mx1 - 0.08, yy + 0.06, z + sgn * 0.05), (mx0 + 0.08, yy + 0.06, z + sgn * 0.05)]
            m.hexa(c, "VH_PaintedSteel")
        m.box((mx0, ry + 0.15, z - 0.2 * sgn - 0.02), (mx1, ry + mh - 0.12, z - 0.2 * sgn + 0.02), "VH_Dark")
    for x in (mx0, mx1):
        m.box((x - 0.05, ry, mz1), (x + 0.05, ry + mh, mz0), "VH_PaintedSteel")
    zc = (mz0 + mz1) / 2
    for za, zb in ((mz0 + 0.3, zc), (mz1 - 0.3, zc)):
        corrugated_sheet(s.roof, mx0 - 0.3, mx1 + 0.3, (ry + mh, za), (ry + mh + 0.45, zb), "WS_Corrugated", lod=lod)
    m.cyl((mx0 - 0.3, ry + mh + 0.47, zc), (mx1 + 0.3, ry + mh + 0.47, zc), 0.06, "VH_Steel", 6)
    s.rec["mounts"].append({"name": "Roof air conditioner", "prefab": "PH_AirconRusted", "pos": [3.2, ry, -5.6], "yaw": 180})
    # hoist beam over the double door (pump columns are pulled out through it); projects 0.95 m and the chain block and
    # hook are hung up high, clear of the mining droid's patrol 2 m in front
    ux, hy, out = -1.4, 4.33, 0.95
    m.box((ux - 0.012, hy, -0.3), (ux + 0.012, hy + 0.26, out), "WS_PaintYellow")
    for yy in (hy, hy + 0.24):
        m.box((ux - 0.08, yy, -0.3), (ux + 0.08, yy + 0.022, out), "WS_PaintYellow")
    m.box((ux - 0.1, hy - 0.04, out - 0.02), (ux + 0.1, hy + 0.3, out + 0.02), "VH_Steel")
    m.box((ux - 0.22, hy - 0.22, 0.062), (ux + 0.22, hy + 0.44, 0.09), "WB_BlackSteel")
    m.cyl((ux, 6.1, 0.09), (ux, hy + 0.26, out - 0.08), 0.02, "VH_Steel", 8)
    m.box((ux - 0.16, 5.95, 0.062), (ux + 0.16, 6.25, 0.09), "WB_BlackSteel")
    m.box((ux - 0.12, hy - 0.14, 0.5), (ux + 0.12, hy, 0.8), "VH_PaintedSteel")
    m.box((ux - 0.14, hy - 0.55, 0.52), (ux + 0.14, hy - 0.18, 0.78), "WS_PaintYellow")
    m.tube([(ux, hy - 0.55, 0.65), (ux, hy - 0.72, 0.65), (ux - 0.1, hy - 0.82, 0.65), (ux, hy - 0.9, 0.65), (ux + 0.1, hy - 0.8, 0.65)], 0.035, "VH_Steel", 8)
    for dz in (0.58, 0.72):   # slack hand chain looped up to the beam
        m.tube([(ux + 0.1, hy - 0.45, dz), (ux + 0.16, hy - 1.1, dz), (ux + 0.12, hy - 0.5, dz + 0.02)], 0.01, "VH_Steel", 4)
    s.fdrip(s.FRONT, ux - 0.3, ux + 0.3, hy - 0.22, 2.0, 0.9, "rust", soft=0.08)
    s.stencil("AQUIFER 3", "front", 2.45, 4.25, 0.44, 2.15, 0.075)
    s.stencil("POTABLE - NO ENTRY", "front", 2.45, 3.72, 0.12, 1.5, 0.075)
    s.lamp("front", -3.25, 3.25, "Door lamp west")
    s.lamp("front", 0.42, 3.25, "Door lamp east")
    s.corner_straps([(1.2, 2.4), (3.6, 4.6), (5.3, 6.2)], base=0.75)
    s.banner(s.FRONT, -3.95, 4.62, 0.13, 0.62, 3.0, "aq_w")
    # louvred steel vents in the upper front wall either side of the hoist
    for u in (-1.4, 0.6):
        F = s.FRONT
        F.box(m, u - 0.42, u + 0.42, 5.12, 5.74, 0.05, 0.11, "WB_BlackSteel")
        F.box(m, u - 0.36, u + 0.36, 5.18, 5.68, 0.04, 0.112, "VH_Dark")
        for k in range(5):
            yy = lerp(5.24, 5.62, k / 4)
            c = [F.P(u - 0.36, yy - 0.03, 0.11), F.P(u + 0.36, yy - 0.03, 0.11), F.P(u + 0.36, yy - 0.03, 0.14), F.P(u - 0.36, yy - 0.03, 0.14),
                 F.P(u - 0.36, yy + 0.03, 0.08), F.P(u + 0.36, yy + 0.03, 0.08), F.P(u + 0.36, yy + 0.03, 0.1), F.P(u - 0.36, yy + 0.03, 0.1)]
            m.hexa(c, "WB_BlackSteel")
        s.fdrip(F, u - 0.4, u + 0.4, 5.12, 1.4, 0.8, "rust", soft=0.06)
    s.lamp("rear", 2.6, 3.1, "Rear door lamp")
    s.lamp("right", 2.2, 3.6, "Well lamp")
    s.downpipe("front", 4.25, 6.31) if False else s.downpipe("left", -0.5, 6.31)

    # well head east of the hall: dressed stone kerb, flanged casing, valve, the rising main into the east wall
    WX, WZ = 7.6, -1.0
    n = 10
    for i in range(n):
        a0, a1 = 2 * math.pi * i / n + 0.012, 2 * math.pi * (i + 1) / n - 0.012
        ri, ro = 0.7, 1.15
        b_ = [(WX + math.cos(a0) * ri, 0.0, WZ + math.sin(a0) * ri), (WX + math.cos(a1) * ri, 0.0, WZ + math.sin(a1) * ri),
              (WX + math.cos(a1) * ro, 0.0, WZ + math.sin(a1) * ro), (WX + math.cos(a0) * ro, 0.0, WZ + math.sin(a0) * ro)]
        t_ = [(px, 0.72, pz) for (px, _, pz) in b_]
        bid = s.pod.new_block(tint=stone_tint(), erode=0.012)
        vs, made = s.pod.hexa(b_ + t_, "VH_Ashlar", bid, skip=("bottom",))
        eroded_bevel(s.pod, list(made["top"].edges), 0.025, 2, seg_len=0.2)
    m.cyl((WX, 0.0, WZ), (WX, 1.15, WZ), 0.42, "WB_BlackSteel", 20)
    m.cyl((WX, 1.15, WZ), (WX, 1.27, WZ), 0.6, "VH_Steel", 20)
    if lod == 0:
        for j in range(12):
            a = 2 * math.pi * j / 12
            hd.cyl((WX + math.cos(a) * 0.52, 1.1, WZ + math.sin(a) * 0.52), (WX + math.cos(a) * 0.52, 1.34, WZ + math.sin(a) * 0.52), 0.025, "VH_Steel", 6)
    main_pts = [(WX, 1.27, WZ), (WX, 2.7, WZ), (WX - 0.6, 3.2, WZ), (HW + 0.05, 3.2, WZ)]
    m.tube(main_pts, 0.21, "WB_PipeTeal", 16)
    for (px, py, pz) in ((WX, 2.1, WZ), (WX - 1.6, 3.2, WZ), (HW + 0.6, 3.2, WZ)):
        if abs(py - 3.2) < 0.01:
            m.cyl((px - 0.05, py, pz), (px + 0.05, py, pz), 0.3, "WB_BlackSteel", 16)
        else:
            m.cyl((px, py - 0.05, pz), (px, py + 0.05, pz), 0.3, "WB_BlackSteel", 16)
    for px in (WX - 1.5, HW + 1.0):      # H-frame trestles under the main
        for dz in (-0.45, 0.45):
            m.box((px - 0.07, 0.0, WZ + dz - 0.07), (px + 0.07, 2.98, WZ + dz + 0.07), "WB_BlackSteel")
            m.box((px - 0.2, 0.0, WZ + dz - 0.2), (px + 0.2, 0.04, WZ + dz + 0.2), "VH_Steel")
        m.box((px - 0.08, 2.84, WZ - 0.6), (px + 0.08, 2.99, WZ + 0.6), "WB_BlackSteel")
        m.box((px - 0.05, 1.2, WZ - 0.45), (px + 0.05, 1.3, WZ + 0.45), "WB_BlackSteel")
        m.cyl((px, 0.25, WZ - 0.45), (px, 2.75, WZ + 0.45), 0.025, "WB_BlackSteel", 6)
    vc = Vector((WX + 0.62, 1.9, WZ))
    m.cyl(tuple(vc - Vector((0.16, 0, 0))), tuple(vc + Vector((0.12, 0, 0))), 0.14, "VH_Steel", 10)
    m.tube([(vc.x + 0.12, vc.y + 0.4 * math.cos(a), vc.z + 0.4 * math.sin(a)) for a in [2 * math.pi * k / 16 for k in range(17)]], 0.03, "WS_PaintRed", 6)
    for a in (0.0, math.pi / 2):
        m.cyl((vc.x + 0.12, vc.y - 0.4 * math.cos(a), vc.z - 0.4 * math.sin(a)), (vc.x + 0.12, vc.y + 0.4 * math.cos(a), vc.z + 0.4 * math.sin(a)), 0.015, "WS_PaintRed", 6)
    s.fdrip(s.RIGHT, -WZ - 0.4, -WZ + 0.4, 3.0, 3.0, 1.0, "rust", soft=0.1)        # leak stain under the wall entry
    s.rec["colliders"].append({"name": "COL_WellHead", "center": [WX, 0.6, WZ], "size": [2.4, 1.2, 2.4]})
    for i_, px in enumerate((WX - 1.5, HW + 1.0)):
        s.rec["colliders"].append({"name": f"COL_Trestle_{i_}", "center": [px, 1.5, WZ], "size": [0.4, 3.0, 1.2]})
    # storage tanks behind the hall, headers into the rear wall
    for i, (tx, mat) in enumerate(((-5.5, "WB_PaintBone"), (-1.5, "WS_PaintTeal"), (2.5, "WG_RustSteel"))):
        riveted_tank(s, tx, -9.0, 1.45, 4.6, mat, patched=(i == 2), ladder_a=math.pi * (0.85 if i < 2 else 0.15), lod=lod)
        m.tube([(tx, 1.0, -7.5), (tx, 1.0, -6.95), (tx, 1.0, -D - 0.08)], 0.12, "WB_PipeTeal", 12)
        m.cyl((tx, 1.0, -7.2), (tx, 1.0, -7.1), 0.2, "WB_BlackSteel", 12)
        s.rec["colliders"].append({"name": f"COL_Tank_{i}", "center": [tx, 3.0, -9.0], "size": [3.4, 6.0, 3.4]})
    m.tube([(-6.6, 5.4, -7.9), (-6.6, 5.6, -6.7), (3.6, 5.6, -6.7)], 0.16, "WB_PipeTeal", 12)
    s.prop(SD + "SD_tool_cart.prefab", (-HW - 0.8, 0.0, -3.0), 90)
    s.prop(SD + "SD_drum_steel_blue.prefab", (HW + 0.7, 0.0, -5.6), 0)
    s.prop(SD + "SD_drum_blue.prefab", (HW + 0.75, 0.0, -4.85), 30)
    s.prop(SD + "SD_jerrycan_green.prefab", (HW + 1.1, 0.0, -5.3), 75)
    # Warden guard post by the well: sandbag walls
    s.rec["mounts"].append({"name": "Guard post sandbags east", "prefab": "WG_SandbagWall2mLow", "pos": [10.4, 0.0, -2.6], "yaw": 90})
    s.rec["mounts"].append({"name": "Guard post sandbags south", "prefab": "WG_SandbagWall2mLow", "pos": [9.4, 0.0, -4.0], "yaw": 0})
    s.rec["colliders"].append({"name": "COL_GuardSandbagsE", "center": [10.4, 0.5, -2.6], "size": [0.7, 1.0, 2.1]})
    s.rec["colliders"].append({"name": "COL_GuardSandbagsS", "center": [9.4, 0.5, -4.0], "size": [2.1, 1.0, 0.7]})
    for c, r_, st in (((-3.6, 1.6, 0.08), 1.2, 0.95), ((3.9, 4.0, 0.08), 1.0, 0.85), ((HW + 0.08, 2.4, -5.5), 1.0, 0.8), ((-2.0, 3.2, -D - 0.08), 1.1, 0.8)):
        s.scars.impact(c, r_, st)
    if lod == 0:
        for (a, b) in ((-4.2, -3.0), (-0.1, 0.9), (2.2, 4.3)):
            s.drift(a, b, 0.07, key=("drift", a))
    return s


def aquifer_lod2():
    parcel(4.5, 6.4, 0.0, 4.75)
    WM.set_state(2, random.Random(11), "Aquifer3_l2")
    coll = bpy.data.collections.new("Aquifer3_LOD2")
    bpy.context.scene.collection.children.link(coll)
    st, mt = Part("Aquifer3_Masonry_LOD2"), Part("Aquifer3_Metal_LOD2", False)
    st.box((-4.6, 0, -6.5), (4.6, 7.3, 0.1), "VH_Ashlar")
    mt.box((-3.2, 6.66, -4.8), (3.2, 8.3, -1.6), "VH_PaintedSteel")
    mt.box((-2.6, 0.0, 0.0), (-0.2, 3.07, 0.12), "VH_DoorSteel")
    for (tx, mat) in ((-5.5, "WB_PaintBone"), (-1.5, "WS_PaintTeal"), (2.5, "WG_RustSteel")):
        mt.cyl((tx, 0.0, -9.0), (tx, 5.15, -9.0), 1.45, mat, 10)
        mt.cyl((tx, 5.15, -9.0), (tx, 5.85, -9.0), 1.49, mat, 10, r2=0.35)
    mt.cyl((7.6, 0.0, -1.0), (7.6, 1.3, -1.0), 1.1, "VH_Ashlar", 8)
    mt.box((4.5, 3.0, -1.2), (7.8, 3.4, -0.8), "WB_PipeTeal")
    for p_ in (st, mt):
        p_.finalize()
    return [st.build(coll, flat=True), mt.build(coll, flat=True)]


# ====================================================================== QUANTUM TUBE goods node + conduit (north wall)
def tube_node(lod):
    """Quantum Tube goods node housing (two, either side of the Ring Gate axis). Replaces the white boxes of
    `Ward district retrofit/Quantum Tube conduit`. Goods only (lore: no passenger transport is implied): a cargo port at
    waist height with a shutter and a roller lip, not a door. Root = city-face centre, yaw 180 at world (+-9, 0, 40.8);
    symmetric conduit collars on both sides (the unused one carries a blanking flange)."""
    parcel(1.5, 2.8, 0.0, 1.81)
    s = Building("TubeNode", lod, (1.02, 0.96, 0.9), 707)
    HW, D = s.HW, s.D
    m, hd, g = s.metal, s.hard, s.glow
    s.walls()
    y0 = AWS.STRING[1]                    # 2.06: module sits on the stone base
    y1 = 5.2
    # armoured node module: blackened steel frame, composite panels, chamfered top corners
    F = s.FRONT
    ox = 0.1                              # module overhangs the stone 0.1 m
    x0, x1, z0, z1 = -HW - ox, HW + ox, ox, -D - ox
    m.box((x0, y0, z1), (x1, y0 + 0.18, z0), "WB_BlackSteel")
    m.box((x0 + 0.06, y0 + 0.18, z1 + 0.06), (x1 - 0.06, y1 - 0.25, z0 - 0.06), "WS_PanelDark")
    ch = 0.35
    top = [(x0 + 0.06, y1 - 0.25, z0 - 0.06), (x1 - 0.06, y1 - 0.25, z0 - 0.06), (x1 - 0.06, y1 - 0.25, z1 + 0.06), (x0 + 0.06, y1 - 0.25, z1 + 0.06),
           (x0 + 0.06 + ch, y1, z0 - 0.06 - ch), (x1 - 0.06 - ch, y1, z0 - 0.06 - ch), (x1 - 0.06 - ch, y1, z1 + 0.06 + ch), (x0 + 0.06 + ch, y1, z1 + 0.06 + ch)]
    m.hexa(top, "WB_BlackSteel")
    for (xx, zz) in ((x0, z0), (x1, z0), (x1, z1), (x0, z1)):          # corner posts
        m.box((xx - 0.07, y0, zz - 0.07), (xx + 0.07, y1 - 0.2, zz + 0.07), "WB_BlackSteel")
    for yy in (3.1, 4.25):                                               # horizontal frame rails on all sides
        m.box((x0 - 0.02, yy - 0.05, z0 - 0.02), (x1 + 0.02, yy + 0.05, z0 + 0.03), "WB_BlackSteel")
        m.box((x0 - 0.02, yy - 0.05, z1 - 0.03), (x1 + 0.02, yy + 0.05, z1 + 0.02), "WB_BlackSteel")
        for xx in (x0, x1):
            m.box((xx - 0.03, yy - 0.05, z1), (xx + 0.03, yy + 0.05, z0), "WB_BlackSteel")
    if lod == 0:
        for (xx, zz, nx, nz) in ((x0, None, -1, 0), (x1, None, 1, 0)):
            for yy in (y0 + 0.4, 3.1, 4.25, y1 - 0.4):
                for zq in (z0 - 0.3, (z0 + z1) / 2, z1 + 0.3):
                    hd.sphere((xx + nx * 0.065, yy, zq), 0.014, "VH_Steel", 6, hemi_axis=(nx, 0, 0))
    # cargo port on the city face: hazard frame, steel shutter half up, roller lip, guide rails, status screen
    pu0, pu1, pv0, pv1 = -0.75, 0.75, 2.45, 3.75
    for (a, b, c_, d_) in ((pu0 - 0.22, pu0, pv0 - 0.22, pv1 + 0.22), (pu1, pu1 + 0.22, pv0 - 0.22, pv1 + 0.22),
                           (pu0, pu1, pv1, pv1 + 0.22), (pu0, pu1, pv0 - 0.22, pv0)):
        F.box(m, a, b, c_, d_, ox - 0.06, ox + 0.05, "WB_Hazard")
    # the port's lined reveal (the module is hollow behind it)
    F.box(m, pu0 - 0.02, pu0, pv0, pv1, ox - 0.5, ox, "VH_Steel")
    F.box(m, pu1, pu1 + 0.02, pv0, pv1, ox - 0.5, ox, "VH_Steel")
    F.box(m, pu0, pu1, pv1, pv1 + 0.02, ox - 0.5, ox, "VH_Steel")
    F.box(m, pu0, pu1, pv0, pv1, ox - 0.5, ox - 0.45, "VH_Dark")
    for (a, b) in ((pu0 - 0.02, pu0 + 0.02), (pu1 - 0.02, pu1 + 0.02)):
        F.box(m, a, b, pv0, pv1, ox - 0.45, ox + 0.05, "VH_Steel")
    yb = 3.2
    yy = pv1 - 0.04
    while yy - 0.07 > yb:
        F.box(m, pu0 + 0.03, pu1 - 0.03, yy - 0.07, yy, ox - 0.12, ox - 0.09, "WS_Shutter")
        yy -= 0.07
    F.box(m, pu0 + 0.03, pu1 - 0.03, yb - 0.06, yb, ox - 0.13, ox - 0.07, "VH_Steel")
    F.box(g, pu0 + 0.1, pu1 - 0.1, pv0 + 0.25, pv0 + 0.27, ox - 0.44, ox - 0.42, "WB_LedCyan")
    F.box(m, pu0 - 0.1, pu1 + 0.1, pv0 - 0.05, pv0, ox - 0.45, ox + 0.35, "VH_Steel")       # roller lip
    for k in range(7 if lod == 0 else 3):
        uu = lerp(pu0, pu1, k / (6 if lod == 0 else 2))
        m.cyl(tuple(F.P(uu, pv0 + 0.03, ox - 0.4)), tuple(F.P(uu, pv0 + 0.03, ox + 0.3)), 0.025, "VH_Steel", 8) if False else None
    for k in range(5):
        dd = lerp(ox - 0.4, ox + 0.3, k / 4)
        m.cyl(tuple(F.P(pu0 - 0.05, pv0 + 0.03, dd)), tuple(F.P(pu1 + 0.05, pv0 + 0.03, dd)), 0.03, "VH_Steel", 8)
    for sgn in (-1, 1):   # lip brackets
        m.box(tuple(F.P(sgn * (pu1 + 0.05) - 0.03, pv0 - 0.45, ox)), tuple(F.P(sgn * (pu1 + 0.05) + 0.03, pv0 - 0.05, ox + 0.3)), "WB_BlackSteel")
    F.box(m, 1.0, 1.4, 2.7, 3.2, ox + 0.0, ox + 0.06, "WS_PanelDark")
    F.box(g, 1.04, 1.36, 2.85, 3.12, ox + 0.06, ox + 0.065, "WB_ScreenCyan")
    F.box(g, -1.48, -1.44, 2.3, 4.9, ox + 0.0, ox + 0.04, "WB_LedCyan")                # vertical status strip
    s.stencil("NODE 07", "front", 0.0, 4.6, 0.32, 1.4, ox + 0.004)
    s.stencil("GOODS ONLY", "front", 0.0, 4.15, 0.16, 1.2, ox + 0.004)
    s.stencil("NO PASSENGERS", "front", 0.0, 2.25, 0.09, 0.9, ox + 0.004)
    # conduit collars on both sides at the conduit height (4.3 world), flanged; the outer flange faces carry bolts
    CY, CZ = 4.3, -D / 2 + 0.0
    for sx in (-1, 1):
        xa = sx * (HW + ox)
        m.cyl((xa, CY, CZ), (xa + sx * 0.35, CY, CZ), 0.66, "WB_BlackSteel", 20)
        m.cyl((xa + sx * 0.35, CY, CZ), (xa + sx * 0.45, CY, CZ), 0.74, "VH_Steel", 20)
        if lod == 0:
            for j in range(12):
                a = 2 * math.pi * j / 12
                hd.cyl((xa + sx * 0.43, CY + math.sin(a) * 0.68, CZ + math.cos(a) * 0.68), (xa + sx * 0.5, CY + math.sin(a) * 0.68, CZ + math.cos(a) * 0.68), 0.025, "VH_Steel", 6)
        # gusset plates from the collar to the module frame
        for dy in (-0.55, 0.55):
            m.box((min(xa, xa + sx * 0.35), CY + dy - 0.03, CZ - 0.5), (max(xa, xa + sx * 0.35), CY + dy + 0.03, CZ + 0.5), "WB_BlackSteel")
    # roof: heat-sink fins and a short antenna with a cyan tip
    for k in range(7):
        zz = lerp(z1 + 0.6, z0 - 0.6, k / 6)
        m.box((-0.75, y1, zz - 0.02), (0.75, y1 + 0.32, zz + 0.02), "VH_Steel")
    m.cyl((0.9, y1, -D / 2), (0.9, y1 + 1.4, -D / 2), 0.03, "VH_Steel", 8)
    g.sphere((0.9, y1 + 1.43, -D / 2), 0.045, "WB_LedCyan", 8)
    s.lamp("front", -1.2, 1.55, "Node lamp") if False else None
    s.rec["lights"].append({"name": "Node status glow", "type": "point", "pos": [0.0, 3.0, ox + 0.6], "color": [0.4, 0.86, 1.0],
                            "intensity": 1.0, "range": 3.5, "clock": False})
    for c, r_, st in (((-1.0, 1.0, 0.08), 0.9, 0.85), ((1.6, 1.4, -1.6), 0.8, 0.7)):
        s.scars.impact(c, r_, st)
    s.roof_y = y1
    s.top_y = y1
    s.rec["colliders"].append({"name": "COL_Module", "center": [0.0, (y0 + y1) / 2, -D / 2], "size": [2 * HW + 0.2, y1 - y0, D + 0.2]})
    return s


def tube_node_lod2():
    WM.set_state(2, random.Random(13), "TubeNode_l2")
    coll = bpy.data.collections.new("TubeNode_LOD2")
    bpy.context.scene.collection.children.link(coll)
    st, mt = Part("TubeNode_Masonry_LOD2"), Part("TubeNode_Metal_LOD2", False)
    st.box((-1.6, 0, -2.9), (1.6, 2.06, 0.1), "VH_Ashlar")
    mt.box((-1.6, 2.06, -2.9), (1.6, 5.2, 0.1), "WS_PanelDark")
    mt.box((-0.95, 2.25, 0.08), (0.95, 3.95, 0.12), "WB_Hazard")
    for sx in (-1, 1):
        mt.cyl((sx * 1.6, 4.3, -1.4), (sx * 2.05, 4.3, -1.4), 0.7, "WB_BlackSteel", 8)
    for p_ in (st, mt):
        p_.finalize()
    return [st.build(coll, flat=True), mt.build(coll, flat=True)]


SEG = 7.25


def tube_segment(lod, span=False):
    """One 7.25 m bay of the goods conduit: armoured conduit on +X from the root (conduit axis, ground level) with an
    ashlar pylon and steel saddle at the far end, a cable tray on top, an inspection hatch and one cyan status lamp.
    Instanced along both runs (yaw 0 east of the Ring Gate, 180 west)."""
    WM.set_state(lod, random.Random(7250), "TubeSeg")
    WM.WEAR["ground_y"] = 0.0
    WM.TINT[:] = [1.02, 0.96, 0.88]
    WM.reset_materials()
    r = Ruin.__new__(Ruin)
    Ruin.__init__(r, "TubeSeg", lod, (1.02, 0.96, 0.88), 7250)
    m, hd, g = r.metal, r.hard, r.glow
    CY, R = 4.3, 0.5
    sides = 22 if lod == 0 else 12
    m.cyl((0.0, CY, 0.0), (SEG, CY, 0.0), R, "WS_PanelDark", sides)
    n = int(SEG / 1.2)
    for k in range(n + 1):
        x = k * SEG / n
        m.cyl((x - 0.09, CY, 0.0), (x + 0.09, CY, 0.0), R + 0.06, "WB_BlackSteel", sides)
        if lod == 0:
            for j in range(10):
                a = 2 * math.pi * j / 10
                hd.sphere((x, CY + math.sin(a) * (R + 0.065), math.cos(a) * (R + 0.065)), 0.016, "VH_Steel", 5)
    # cable tray on top with two cables
    m.box((0.0, CY + R + 0.08, -0.22), (SEG, CY + R + 0.1, 0.22), "VH_Steel")
    for zz in (-0.22, 0.22):
        m.box((0.0, CY + R + 0.08, zz - 0.01), (SEG, CY + R + 0.18, zz + 0.01), "VH_Steel")
    for zz in (-0.08, 0.07):
        m.cyl((0.0, CY + R + 0.14, zz), (SEG, CY + R + 0.14, zz), 0.035, "VH_Rubber", 6)
    for k in range(n):
        x = (k + 0.5) * SEG / n
        m.box((x - 0.02, CY + R - 0.02, -0.24), (x + 0.02, CY + R + 0.1, 0.24), "VH_Steel")
    # inspection hatch on the city side (local -z for the pylon bays east of the gate, +z for the wall-hung spans west),
    # status lamp
    hx = SEG * 0.5
    sz = 1 if span else -1
    za, zb = sorted((sz * (R + 0.04), sz * (R - 0.12)))
    m.box((hx - 0.35, CY - 0.28, za), (hx + 0.35, CY + 0.28, zb), "WB_BlackSteel")
    za, zb = sorted((sz * (R + 0.06), sz * (R + 0.03)))
    m.box((hx - 0.3, CY - 0.23, za), (hx + 0.3, CY + 0.23, zb), "WS_PanelDark")
    za, zb = sorted((sz * (R + 0.03), sz * (R - 0.05)))
    g.box((hx + 0.42, CY - 0.05, za), (hx + 0.5, CY + 0.05, zb), "WB_LedCyan")
    if span:
        # wall-hung span (west run, yaw 180: the north wall's inner face is 1.5 m behind the axis on local -z): riveted
        # wall plate, cantilever arm to a clamp band, diagonal strut
        px = SEG
        WZ = -1.48
        m.box((px - 0.3, CY - 1.5, WZ - 0.04), (px + 0.3, CY + 0.6, WZ), "WB_BlackSteel")
        m.box((px - 0.07, CY + 0.35, WZ), (px + 0.07, CY + 0.55, 0.0), "WB_BlackSteel")
        r.bar(m, (px, CY - 1.3, WZ), (px, CY - 0.35, -0.42), 0.1, 0.1, "WB_BlackSteel")
        m.cyl((px - 0.12, CY, 0.0), (px + 0.12, CY, 0.0), R + 0.1, "WB_BlackSteel", sides)
        if lod == 0:
            for (yy, xx) in ((CY - 1.35, px - 0.2), (CY - 1.35, px + 0.2), (CY + 0.45, px - 0.2), (CY + 0.45, px + 0.2)):
                hd.sphere((xx, yy, WZ), 0.02, "VH_Steel", 6, hemi_axis=(0, 0, 1))
        r.rec["colliders"] = []
        r.top_y = CY + 0.7
        return r
    r.stencil("GOODS ONLY", Frame((hx, 0, -R - 0.06), (-1, 0, 0), (0, 0, -1)), 0.0, CY + 0.36, 0.1, 0.8, 0.0) if False else None
    # ashlar pylon at the far end: courses to under the saddle, steel saddle cradle and clamp band
    px = SEG
    top = 3.49
    r.pier(px, 0.0, 0.8, top, "pyl", jag=0.0, bands=(1.3,))
    m.box((px - 0.35, top, -0.55), (px + 0.35, top + 0.12, 0.55), "WB_BlackSteel")
    for zz in (-0.42, 0.42):
        m.box((px - 0.3, top + 0.12, zz - 0.06), (px + 0.3, CY - 0.2, zz + 0.06), "WB_BlackSteel")
    m.cyl((px - 0.12, CY, 0.0), (px + 0.12, CY, 0.0), R + 0.1, "WB_BlackSteel", sides)
    r.fdrip(Frame((px, 0, -0.4), (-1, 0, 0), (0, 0, -1)), -0.4, 0.4, top, 2.5, 0.9, "rust", soft=0.1)
    r.fdrip(Frame((px, 0, 0.4), (1, 0, 0), (0, 0, 1)), -0.4, 0.4, top, 2.5, 0.9, "rust", soft=0.1)
    r.rec["colliders"] = [{"name": "COL_Pylon", "center": [px, top / 2, 0.0], "size": [1.0, top, 1.0]}]
    r.top_y = CY + 0.7
    return r


def tube_span(lod):
    r = tube_segment(lod, span=True)
    r.name = "TubeSpan"
    return r


def tube_span_lod2():
    WM.set_state(2, random.Random(19), "TubeSpan_l2")
    coll = bpy.data.collections.new("TubeSpan_LOD2")
    bpy.context.scene.collection.children.link(coll)
    mt = Part("TubeSpan_Metal_LOD2", False)
    mt.cyl((0.0, 4.3, 0.0), (SEG, 4.3, 0.0), 0.53, "WS_PanelDark", 8)
    mt.box((SEG - 0.1, 2.9, -1.5), (SEG + 0.1, 4.8, -0.5), "WB_BlackSteel")
    mt.finalize()
    return [mt.build(coll, flat=True)]


def tube_segment_lod2():
    WM.set_state(2, random.Random(17), "TubeSeg_l2")
    coll = bpy.data.collections.new("TubeSeg_LOD2")
    bpy.context.scene.collection.children.link(coll)
    st, mt = Part("TubeSeg_Masonry_LOD2"), Part("TubeSeg_Metal_LOD2", False)
    st.box((SEG - 0.42, 0, -0.42), (SEG + 0.42, 3.49, 0.42), "VH_Ashlar")
    mt.cyl((0.0, 4.3, 0.0), (SEG, 4.3, 0.0), 0.53, "WS_PanelDark", 8)
    for p_ in (st, mt):
        p_.finalize()
    return [st.build(coll, flat=True), mt.build(coll, flat=True)]


# ====================================================================== converted container homes on the wall feet
def corrugated_wall(part, F, u0, u1, y0, y1, d, mat, pitch=0.28, amp=0.035, lod=0):
    """Vertical trapezoidal corrugation on frame F (u along the wall, d outward), closed slab 3 cm thick."""
    step = pitch / 4 if lod == 0 else pitch / 2
    pat = [0.0, amp, amp, 0.0] if lod == 0 else [0.0, amp]
    us, hs = [], []
    u, k = u0, 0
    while u < u1 - 1e-6:
        us.append(u); hs.append(pat[k % len(pat)]); u += step; k += 1
    us.append(u1); hs.append(pat[k % len(pat)])
    bm = part.bm
    mi = part.mi(mat)
    def row(y, off):
        return [bm.verts.new(F.P(uu, y, d + h + off)) for uu, h in zip(us, hs)]
    to, tb = row(y0, 0.0), row(y1, 0.0)
    io, ib = row(y0, -0.03), row(y1, -0.03)
    fs = []
    for i in range(len(us) - 1):
        fs.append(bm.faces.new([to[i], to[i + 1], tb[i + 1], tb[i]]))
        fs.append(bm.faces.new([io[i], ib[i], ib[i + 1], io[i + 1]]))
        fs.append(bm.faces.new([to[i], io[i], io[i + 1], to[i + 1]]))
        fs.append(bm.faces.new([tb[i], tb[i + 1], ib[i + 1], ib[i]]))
    fs.append(bm.faces.new([to[0], tb[0], ib[0], io[0]]))
    fs.append(bm.faces.new([to[-1], io[-1], ib[-1], tb[-1]]))
    for f in fs:
        f.material_index = mi
    bmesh.ops.recalc_face_normals(bm, faces=fs)


def container_box(s, cx, y0, cz, mat, door_end=True, front_door=True, window=True, lod=0, tag="c"):
    """A converted 20 ft ISO container (6.06 x 2.44 x 2.59) centred (cx, cz), floor at y0: corrugated walls, posts,
    rails, castings, end doors with lock rods; a cut-in steel door and a shuttered window on the front (+z) side."""
    m, hd = s.metal, s.hard
    L, W, H = 6.06, 2.44, 2.59
    x0, x1, z0, z1 = cx - L / 2, cx + L / 2, cz - W / 2, cz + W / 2
    Ff = Frame((0, 0, z1), (1, 0, 0), (0, 0, 1))
    Fb = Frame((0, 0, z0), (-1, 0, 0), (0, 0, -1))
    Fr = Frame((x1, 0, 0), (0, 0, -1), (1, 0, 0))
    Fl = Frame((x0, 0, 0), (0, 0, 1), (-1, 0, 0))
    yb, yt = y0 + 0.16, y0 + H - 0.1
    du0, du1 = cx + 0.9, cx + 1.85          # front door
    wu0, wu1 = cx - 1.9, cx - 0.7           # front window
    if front_door:
        corrugated_wall(m, Ff, x0 + 0.1, du0 - 0.06, yb, yt, -0.04, mat, lod=lod)
        corrugated_wall(m, Ff, du1 + 0.06, x1 - 0.1, yb, yt, -0.04, mat, lod=lod)
        corrugated_wall(m, Ff, du0 - 0.06, du1 + 0.06, y0 + 2.15, yt, -0.04, mat, lod=lod)
    else:
        corrugated_wall(m, Ff, x0 + 0.1, x1 - 0.1, yb, yt, -0.04, mat, lod=lod)
    corrugated_wall(m, Fb, -x1 + 0.1, -x0 - 0.1, yb, yt, -0.04, mat, lod=lod)
    corrugated_wall(m, Fl, z0 + 0.1, z1 - 0.1, yb, yt, -0.04, mat, lod=lod)
    if not door_end:
        corrugated_wall(m, Fr, -z1 + 0.1, -z0 - 0.1, yb, yt, -0.04, mat, lod=lod)
    else:
        for (a, b) in ((-z1 + 0.08, -cz - 0.01), (-cz + 0.01, -z0 - 0.08)):
            Fr.box(m, a, b, yb, yt, -0.03, 0.01, mat)
            for k in range(1, 4):
                uu = lerp(a, b, k / 4)
                Fr.box(m, uu - 0.03, uu + 0.03, yb + 0.05, yt - 0.05, 0.01, 0.035, mat)
            for uu in (lerp(a, b, 0.3), lerp(a, b, 0.7)):
                m.cyl(tuple(Fr.P(uu, yb + 0.1, 0.06)), tuple(Fr.P(uu, yt - 0.1, 0.06)), 0.018, "VH_Steel", 6)
    # floor/roof plates, corner posts, rails, castings
    m.box((x0 + 0.05, y0 + 0.02, z0 + 0.05), (x1 - 0.05, y0 + 0.16, z1 - 0.05), "WB_BlackSteel")
    m.box((x0 + 0.04, yt, z0 + 0.04), (x1 - 0.04, y0 + H - 0.02, z1 - 0.04), mat)
    for (xx, zz) in ((x0, z0), (x1, z0), (x1, z1), (x0, z1)):
        sx, sz = (1 if xx < cx else -1), (1 if zz < cz else -1)
        m.box((min(xx, xx + sx * 0.16), y0, min(zz, zz + sz * 0.16)), (max(xx, xx + sx * 0.16), y0 + H, max(zz, zz + sz * 0.16)), mat)
        for yy in (y0, y0 + H - 0.12):
            m.box((min(xx, xx + sx * 0.18), yy, min(zz, zz + sz * 0.18)), (max(xx, xx + sx * 0.18), yy + 0.12, max(zz, zz + sz * 0.18)), "WG_RustSteel")
    for zz in (z0, z1):
        m.box((x0 + 0.1, y0, min(zz, zz + (0.12 if zz < cz else -0.12))), (x1 - 0.1, y0 + 0.17, max(zz, zz + (0.12 if zz < cz else -0.12))), mat)
        m.box((x0 + 0.1, y0 + H - 0.12, min(zz, zz + (0.1 if zz < cz else -0.1))), (x1 - 0.1, y0 + H, max(zz, zz + (0.1 if zz < cz else -0.1))), mat)
    if front_door:
        Ff.box(m, du0 - 0.06, du1 + 0.06, y0 + 0.15, y0 + 2.18, -0.06, 0.06, "WB_BlackSteel")   # welded frame
        Ff.box(m, du0, du1, y0 + 0.17, y0 + 2.12, -0.05, -0.02, "WS_PaintTeal" if mat != "WB_ContainerBlue" else "WS_PaintOchre")
        for yy in (y0 + 0.5, y0 + 1.15, y0 + 1.8):
            Ff.box(m, du0 + 0.05, du1 - 0.05, yy - 0.025, yy + 0.025, -0.02, 0.0, "WB_BlackSteel")
        m.cyl(tuple(Ff.P(du1 - 0.12, y0 + 1.0, 0.02)), tuple(Ff.P(du1 - 0.12, y0 + 1.15, 0.02)), 0.015, "VH_Bronze", 6)
    if window:
        Ff.box(m, wu0 - 0.06, wu1 + 0.06, y0 + 1.05, y0 + 1.95, -0.06, 0.06, "WB_BlackSteel")
        Ff.box(s.glass, wu0, wu1, y0 + 1.11, y0 + 1.89, -0.05, -0.04, "WS_Glass", skip=("s0", "s1", "s3", "top", "bottom"))
        for k in range(1, 6):
            uu = lerp(wu0, wu1, k / 6)
            m.cyl(tuple(Ff.P(uu, y0 + 1.08, 0.03)), tuple(Ff.P(uu, y0 + 1.92, 0.03)), 0.011, "VH_Steel", 6)
        # one louvred shutter folded open beside it
        Ff.box(m, wu0 - 0.68, wu0 - 0.08, y0 + 1.05, y0 + 1.95, 0.06, 0.09, "WS_PaintOlive")
        if lod == 0:
            for k in range(8):
                yy = y0 + 1.1 + k * 0.105
                Ff.box(m, wu0 - 0.64, wu0 - 0.12, yy, yy + 0.05, 0.09, 0.105, "WS_PaintOlive")
        # rain hood
        Ff.box(m, wu0 - 0.15, wu1 + 0.15, y0 + 2.0, y0 + 2.04, 0.0, 0.32, "WB_BlackSteel")
    s.rec.setdefault("containers", []).append({"tag": tag, "centre": [cx, y0, cz]})


def wall_home(lod, variant="A"):
    """Converted container home against the curtain wall. Variants: A single (rust), C single (sand), B stacked two
    high with an external steel stair. Root = container centre at ground, +Z = street side. The container stands on
    dressed stone blocks; a stone step, a low planter wall, a canvas awning on poles, rooftop solar, water drum, AC,
    laundry line. Replaces the 26 Sep `Perimeter dwellings` containers."""
    s = Ruin(f"WallHome{variant}", lod, (1.03, 0.97, 0.88), {"A": 501, "B": 502, "C": 503}[variant])
    s.top_y = 3.0
    m, hd = s.metal, s.hard
    mat = {"A": "WS_ContainerRust", "B": "WB_ContainerBlue", "C": "WB_ContainerSand"}[variant]
    Y0 = 0.32
    # dressed stone pad blocks under the corners and middle (the container sits on them)
    for xx in (-2.75, 0.0, 2.75):
        for zz in (-0.95, 0.95):
            s.block((xx, Y0 / 2, zz), (0.55, Y0, 0.5), (0.0, 0.0, 0.0), mat="VH_AshlarRough")
    container_box(s, 0.0, Y0, 0.0, mat, door_end=True, front_door=True, window=True, lod=lod, tag="lower")
    top = Y0 + 2.59
    if variant == "B":
        container_box(s, 0.35, top, 0.0, "WS_ContainerRust", door_end=False, front_door=True, window=True, lod=lod, tag="upper")
        top2 = top + 2.59
        # external steel stair up the right end to a landing in front of the upper door
        sx0 = 3.35
        nsteps = 10
        for i in range(nsteps):
            yy = 0.3 + (top - 0.1) * (i + 1) / (nsteps + 1)
            zz = 1.9 - 2.7 * (i + 1) / (nsteps + 1) * 0.0
            xs = sx0 + 0.1
            m.box((xs, yy - 0.03, 1.25 + 0.0 - (i * 0.0)), (xs + 0.85, yy, 1.25 + 0.26), "VH_Steel") if False else None
        # straight flight along -x on the front side, from the ground at x 3.6 up to the landing at x 0.9
        for i in range(nsteps):
            t = (i + 1) / (nsteps + 1)
            xx = lerp(4.6, 2.3, t)
            yy = lerp(0.0, top, t)
            m.box((xx - 0.14, yy - 0.04, 1.32), (xx + 0.14, yy, 2.12), "VH_Steel")
        for zz in (1.3, 2.14):
            s.bar(m, (4.75, 0.0, zz), (2.15, top, zz), 0.06, 0.2, "WB_BlackSteel")
            s.bar(m, (4.75, 1.0, zz + (0.0)), (2.15, top + 1.0, zz), 0.03, 0.03, "VH_Steel")
            m.box((4.7, 0.0, zz - 0.06), (4.8, 1.0, zz + 0.06), "VH_Steel")
        m.box((-0.2, top - 0.08, 1.24), (2.3, top, 2.2), "VH_Steel")             # landing grating
        for xx in (-0.15, 1.05, 2.25):
            m.box((xx - 0.05, 0.0, 2.1), (xx + 0.05, top, 2.2), "WB_BlackSteel")
        m.cyl((-0.15, top + 1.0, 2.15), (2.25, top + 1.0, 2.15), 0.025, "VH_Steel", 6)
        m.cyl((-0.15, top + 0.5, 2.15), (2.25, top + 0.5, 2.15), 0.02, "VH_Steel", 6)
        for xx in (-0.15, 1.05):
            m.cyl((xx, top, 2.15), (xx, top + 1.0, 2.15), 0.025, "VH_Steel", 6)
        s.rec["colliders"].append({"name": "COL_Stair", "center": [3.45, 1.4, 1.72], "size": [2.6, 2.8, 0.9]})
        s.rec["colliders"].append({"name": "COL_LandingPosts", "center": [1.05, 1.4, 2.15], "size": [2.5, 2.8, 0.15]})
        s.top_y = top2 + 0.5
        roof_y, roof_cx = top2, 0.35
    else:
        roof_y, roof_cx = top, 0.0
    # stone step at the front door, low stone planter wall with soil and a scraggy plant bed
    s.block((1.38, 0.15, 1.62), (1.3, 0.3, 0.6), (0.0, 0.0, 0.0), mat="VH_Ashlar")
    for i, (xx, ww) in enumerate(((-2.6, 0.9), (-1.65, 0.9), (-0.72, 0.85))):
        s.block((xx, 0.24, 1.75), (ww - 0.02, 0.48, 0.32), (0.0, s.L.uniform(-0.03, 0.03), 0.0), mat="VH_AshlarRough")
    s.sand.box((-3.0, 0.3, 1.25), (-0.3, 0.42, 1.6), "VH_Sand")
    # canvas awning on two poles over the door and window (the stacked home's landing shelters its door instead)
    cloth = {"A": "WS_ClothMadder", "B": "WS_ClothIndigo", "C": "WS_ClothOchre"}[variant]
    bm = s.canvas.bm
    aw_y0, aw_y1 = Y0 + 2.45, Y0 + 2.05
    if variant != "B":
        bm = s.canvas.bm
        mi = s.canvas.mi(cloth)
        nx, nz = (10, 4) if lod == 0 else (3, 1)
        grid = []
        for j in range(nz + 1):
            t = j / nz
            row = []
            for i in range(nx + 1):
                u = i / nx
                xx = lerp(-2.6, 2.2, u)
                sag = 0.08 * math.sin(math.pi * u) * math.sin(math.pi * t)
                row.append(bm.verts.new(Vector((xx, lerp(aw_y0, aw_y1, t) - sag, 1.24 + 1.5 * t))))
            grid.append(row)
        for j in range(nz):
            for i in range(nx):
                f = bm.faces.new([grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]])
                f.material_index = mi
        for xx in (-2.55, 2.15):
            m.cyl((xx, 0.0, 2.72), (xx, aw_y1 + 0.02, 2.72), 0.03, "VH_Steel", 6)
            m.cyl((xx, aw_y1, 2.72), (xx + (0.6 if xx < 0 else -0.6), 0.0, 3.3), 0.006, "VH_Steel", 4)
        m.box((-2.65, aw_y0 - 0.04, 1.2), (2.25, aw_y0 + 0.02, 1.27), "WB_BlackSteel")
        s.rec["colliders"].append({"name": "COL_AwningPoleW", "center": [-2.55, 1.2, 2.72], "size": [0.15, 2.4, 0.15]})
        s.rec["colliders"].append({"name": "COL_AwningPoleE", "center": [2.15, 1.2, 2.72], "size": [0.15, 2.4, 0.15]})
    # roof: solar panel on a raked frame, water drum, cables down to a junction box
    rx = roof_cx
    m.box((rx - 2.3, roof_y, -0.9), (rx - 0.3, roof_y + 0.05, 0.9), "WB_BlackSteel")
    pts = [(rx - 2.25, roof_y + 0.35, -0.85), (rx - 0.35, roof_y + 0.35, -0.85), (rx - 0.35, roof_y + 0.9, 0.75), (rx - 2.25, roof_y + 0.9, 0.75)]
    m.hexa([Vector(p_) for p_ in pts] + [Vector(p_) + Vector((0, 0.04, 0)) for p_ in pts], "WB_SolarPanel")
    for (xx, zz, h) in ((rx - 2.2, -0.8, 0.35), (rx - 0.4, -0.8, 0.35), (rx - 2.2, 0.7, 0.88), (rx - 0.4, 0.7, 0.88)):
        m.box((xx - 0.025, roof_y, zz - 0.025), (xx + 0.025, roof_y + h, zz + 0.025), "VH_Steel")
    m.cyl((rx + 1.6, roof_y, -0.3), (rx + 1.6, roof_y + 0.68, -0.3), 0.36, "WB_PaintBone" if variant != "C" else "WS_PaintTeal", 16)
    m.cyl((rx + 1.6, roof_y + 0.68, -0.3), (rx + 1.6, roof_y + 0.73, -0.3), 0.37, "VH_Steel", 16)
    m.tube([(rx + 1.6, roof_y + 0.2, 0.06), (rx + 1.6, roof_y + 0.2, 1.3), (rx + 1.6, Y0 + 0.4, 1.3)], 0.025, "VH_Steel", 6)
    m.tube([(rx - 0.4, roof_y + 0.3, 1.0), (rx - 0.4, roof_y + 0.05, 1.27), (rx - 0.4, Y0 + 1.6, 1.27)], 0.012, "VH_Rubber", 5)
    m.box((rx - 0.55, Y0 + 1.35, 1.24), (rx - 0.25, Y0 + 1.65, 1.36), "VH_PaintedSteel")
    s.rec["mounts"].append({"name": "Air conditioner", "prefab": "PH_AirconRusted", "pos": [-1.4, Y0 + 0.2, -1.3], "yaw": 180})
    # laundry line from the awning pole to the wall end, cloth hanging
    lp0, lp1 = Vector((-2.55, aw_y1 - 0.15, 2.72)), Vector((-3.4, aw_y1 - 0.1, -0.4))
    if variant == "B":
        m.cyl((-2.55, 0.0, 2.72), (-2.55, aw_y1, 2.72), 0.03, "VH_Steel", 6)
        s.rec["colliders"].append({"name": "COL_LinePole", "center": [-2.55, 1.2, 2.72], "size": [0.15, 2.4, 0.15]})
    m.cyl(tuple(lp0), tuple(lp1), 0.006, "VH_Steel", 4)
    m.box((-3.45, 0.0, -0.45), (-3.35, aw_y1, -0.35), "VH_Steel")
    for k, (t, w_, h_, cm) in enumerate(((0.2, 0.5, 0.7, "WS_ClothBone"), (0.45, 0.45, 0.55, cloth), (0.72, 0.6, 0.8, "WS_ClothOchre"))):
        c = lp0.lerp(lp1, t)
        dvec = (lp1 - lp0).normalized()
        a, b = c - dvec * w_ / 2, c + dvec * w_ / 2
        mi2 = s.canvas.mi(cm)
        vs = [bm.verts.new(a), bm.verts.new(b), bm.verts.new(b + Vector((0, -h_, 0.03))), bm.verts.new(a + Vector((0, -h_ - 0.05, 0.02)))]
        f = bm.faces.new(vs)
        f.material_index = mi2
    s.rec["colliders"].append({"name": "COL_Container", "center": [0.0, 1.45, 0.0], "size": [6.2, 2.9, 2.6]})
    if variant == "B":
        s.rec["colliders"].append({"name": "COL_ContainerUpper", "center": [0.35, top + 1.3, 0.0], "size": [6.2, 2.6, 2.6]})
    s.rec["colliders"].append({"name": "COL_Planter", "center": [-1.65, 0.25, 1.75], "size": [2.8, 0.5, 0.4]})
    s.rec["colliders"].append({"name": "COL_Step", "center": [1.38, 0.15, 1.62], "size": [1.3, 0.3, 0.6]})
    s.rec["mounts"].append({"name": "Water barrel", "path": SD + "SD_drum_blue.prefab", "pos": [-3.55, 0.0, 0.8], "yaw": 20})
    s.rec["mounts"].append({"name": "Bucket", "path": SD + "SD_bucket_wood.prefab", "pos": [0.2, 0.0, 1.8], "yaw": 0})
    s.rec["lights"].append({"name": "Porch light", "type": "point", "pos": [1.4, Y0 + 2.25, 1.6], "color": [1.0, 0.72, 0.45], "intensity": 1.6, "range": 4.5})
    m.box((1.25, Y0 + 2.18, 1.22), (1.55, Y0 + 2.3, 1.3), "WB_BlackSteel")
    s.glow.sphere((1.4, Y0 + 2.2, 1.34), 0.05, "NF_WallLampBulb", 8)
    for c, r_, st in (((-2.9, Y0 + 1.2, 1.24), 0.6, 0.8),):
        s.scars.impact(c, r_, st)
    return s


def wall_home_lod2(variant="A"):
    WM.set_state(2, random.Random(23), f"WallHome{variant}_l2")
    coll = bpy.data.collections.new(f"WallHome{variant}_LOD2")
    bpy.context.scene.collection.children.link(coll)
    mt = Part(f"WallHome{variant}_Metal_LOD2", False)
    mat = {"A": "WS_ContainerRust", "B": "WB_ContainerBlue", "C": "WB_ContainerSand"}[variant]
    mt.box((-3.03, 0.32, -1.22), (3.03, 2.91, 1.22), mat)
    if variant == "B":
        mt.box((-2.68, 2.91, -1.22), (3.38, 5.5, 1.22), "WS_ContainerRust")
    mt.box((-2.6, 2.3, 1.22), (2.2, 2.4, 2.72), "WS_ClothBone")
    mt.finalize()
    return [mt.build(coll, flat=True)]


BUILDINGS = {"nanofab": (nanofab, nanofab_lod2), "watchtower": (watchtower, watchtower_lod2), "hall": (processing_hall, processing_hall_lod2), "aquifer": (aquifer, aquifer_lod2), "tubenode": (tube_node, tube_node_lod2), "tubeseg": (tube_segment, tube_segment_lod2),
             "tubespan": (tube_span, tube_span_lod2),
             "homea": (lambda lod: wall_home(lod, "A"), lambda: wall_home_lod2("A")),
             "homeb": (lambda lod: wall_home(lod, "B"), lambda: wall_home_lod2("B")),
             "homec": (lambda lod: wall_home(lod, "C"), lambda: wall_home_lod2("C"))}


def main():
    names = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else list(BUILDINGS)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for key in names:
        fn, fn2 = BUILDINGS[key]
        report = {"source": "art/ward_buildings_20261003/author_buildings.py", "date": "2026-10-03", "building": key,
                  "units": "Unity metres local to the building root (street-face centre at ground level, +Z = street side)", "lods": {}}
        for lod in (0, 1):
            b = fn(lod)
            objs = b.finish()
            export(objs, OUT / f"{b.name}_LOD{lod}.glb")
            report["lods"][f"LOD{lod}"] = {"triangles": b.rec["triangles"], "objects": b.rec["objects"]}
            if lod == 0:
                report.update({k: v for k, v in b.rec.items() if k not in ("triangles", "objects")})
                model = b.name
            print(f"{b.name} LOD{lod}: {b.rec['triangles']} triangles", flush=True)
        objs = fn2()
        export(objs, OUT / f"{model}_LOD2.glb")
        report["lods"]["LOD2"] = {"triangles": tri_count(objs)}
        print(f"{model} LOD2: {tri_count(objs)} triangles", flush=True)
        (OUT / f"{key}.json").write_text(json.dumps(report, indent=1))
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE / f"{key}-source.blend"))


if __name__ == "__main__":
    main()
