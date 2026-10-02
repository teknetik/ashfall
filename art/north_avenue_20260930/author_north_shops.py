"""North avenue shops: Salvage, Repairs, Thread + Hide, Blender 5.2 headless (30 September 2026).

Carl (30 Sep 2026): "we recently rebuild a lot of the buildings but we still need to rebuild. general, salvage, thread
and repairs. same stone work, same signage, same weathering."

The three shops sit on the same standard parcels as the hall district (facade 18.1 m from the avenue axis, 7.6 x 6.9 m,
kept 0.5 m porch and single step colliders) and reuse the hall district's Shop class, the shared Ward masonry kit
(art/ward_masonry_kit: dressed ashlar, eroded arrises, chips, ray-traced occlusion, runoff/rust channels, old battle
damage) and its materials. Each gets its own silhouette and trade story:

* Salvage (west row, z 18): two storeys, loading-bay roller shutter, first-floor loading door under a cantilevered hoist
  beam with a trolley, chain block and hook; a shell hole in the upper wall filled with rubble and a bolted plate;
  corrugated rooftop shed.
* Repairs (east row, z 9, its south side faces the cross street): tall workshop bay with a steel canopy on knee braces,
  glazed side door, forge flue up the south wall (soot above), rooftop container workshop.
* Thread + Hide (east row, z 18): lit display window (cloth bolts, dress form, hides) under an indigo awning; stone
  balcony on corbels with a railing, dyed cloth drying over it and hides laced into frames; rooftop drying lines.

The Basic General booth is authored by author_basic_general.py (different form: an open stall on its own plinth).

Run:  blender -b --python-exit-code 1 -P author_north_shops.py [-- shop ...]
Outputs: unity/AthenHill/Assets/AthenHill/Art/WardShops/Models/<Shop>_LOD0/1.glb + <shop>.json and north-shops-source.blend.
"""
import bpy, bmesh, json, math, random, sys
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "art/ward_masonry_kit"))
sys.path.insert(0, str(ROOT / "art/hall_district_20260930"))
import ward_masonry as WM
from ward_masonry import (Frame, stone_tint, ashlar_block, eroded_bevel, block_wear, lerp, drng, export, MORTAR_FRONT)
import author_ward_shops as AWS
sys.path.insert(0, str(HERE))
from north_kit import corrugated_sheet
sys.path.insert(0, str(ROOT / "art/salvage_shop_20261001"))
import salvage_interior as walkin
from author_ward_shops import Shop, BASE, HW, D, OUT, UP


def rng_for(*key):
    return drng(*key)


class NShop(Shop):
    """The hall district Shop plus the north avenue's pieces (upper loading door, hoist, patched shell hole, balcony,
    drying lines, cloth, hides, rooftop shed / container, canopy on knee braces, flue, gas cage, display alcove)."""

    # ------------------------------------------------------------------ cloth material for the awning
    def awning(self, *a, mat="WS_Canvas", **k):
        orig = self.canvas.mi
        if mat != "WS_Canvas":
            self.canvas.mi = lambda m, _o=orig: _o(mat if m == "WS_Canvas" else m)
        try:
            super().awning(*a, **k)
        finally:
            self.canvas.mi = orig

    # ------------------------------------------------------------------ first-floor doors (loading door, balcony doors)
    def upper_door(self, face, uc, width, y0=5.08, y1=7.18, depth=0.3, kind="loading", rail=True):
        F = self.faces[face][0]
        hw, jw = width / 2, 0.12
        lt = y1 + 0.42
        self.holes[face] += [(uc - hw - jw, uc + hw + jw, y0, y1), (uc - hw - jw - 0.12, uc + hw + jw + 0.12, y1, lt)]

        def build():
            trim, metal = self.trim, self.metal
            jy = [y0] + [c for c in self.courses if y0 < c < y1] + [y1]
            for side in (-1, 1):
                for ci, (a, b) in enumerate(zip(jy, jy[1:])):
                    wide = ci % 2 == 0
                    u0, u1 = sorted((uc + side * hw, uc + side * (hw + jw + (0.09 if wide else 0.0))))
                    bid = trim.new_block(tint=stone_tint(), erode=0.007 + 0.006 * block_wear(a))
                    vs, made = F.box(trim, u0 + .004, u1 - .004, a + .005, b - .005, -depth, 0.09 + (0.02 if wide else 0), "VH_Ashlar", bid,
                                     skip=("s0",))
                    edges = [e for e in {e for f in made.values() for e in f.edges} if max(F.n.dot(v.co - F.o) for v in e.verts) > -depth + 0.02]
                    eroded_bevel(trim, edges, self.L.uniform(0.012, 0.022), 2)
            bid = trim.new_block(tint=stone_tint())
            vs, made = F.box(trim, uc - hw - jw - 0.12, uc + hw + jw + 0.12, y1 + .005, lt - .005, -depth, 0.09, "VH_Ashlar", bid, skip=("s0",))
            eroded_bevel(trim, list(made["s2"].edges) + list(made["bottom"].edges), 0.018, 2, seg_len=0.2)
            # sill slab on the string course
            bid = trim.new_block(tint=stone_tint())
            vs, made = F.box(trim, uc - hw - 0.04, uc + hw + 0.04, y0 - 0.02, y0 + 0.05, -depth, 0.19, "VH_Ashlar", bid)
            eroded_bevel(trim, list(made["top"].edges), 0.012, 2)
            self.fdrip(F, uc - hw - 0.3, uc + hw + 0.3, y1, 1.4, 0.55, soft=0.2)
            self.fdrip(F, uc - hw, uc + hw, y0 - 0.02, 1.6, 0.7, "rust" if kind == "loading" else "grime", soft=0.15)
            DZ = -depth + 0.04
            for (u0, u1, a, b) in ((uc - hw, uc - hw + 0.07, y0, y1), (uc + hw - 0.07, uc + hw, y0, y1), (uc - hw, uc + hw, y1 - 0.07, y1)):
                F.box(metal, u0, u1, a, b, DZ - 0.05, DZ + 0.08, "VH_Steel")
            leaves = [(uc - hw + 0.07, uc - 0.004), (uc + 0.004, uc + hw - 0.07)]
            ya, yb = y0 + 0.05, y1 - 0.07
            for li, (xa, xb) in enumerate(leaves):
                if kind == "loading":
                    F.box(metal, xa, xb, ya, yb, DZ - 0.02, DZ + 0.05, "VH_DoorSteel")
                    for (u0, u1, a, b) in ((xa, xa + 0.09, ya, yb), (xb - 0.09, xb, ya, yb), (xa, xb, ya, ya + 0.1), (xa, xb, yb - 0.1, yb),
                                           ((xa + xb) / 2 - 0.04, (xa + xb) / 2 + 0.04, ya, yb)):
                        F.box(metal, u0, u1, a, b, DZ + 0.05, DZ + 0.07, "VH_DoorSteel")
                    # diagonal brace (Z-frame) on each leaf
                    p0, p1 = F.P(xa + 0.1, ya + 0.12, DZ + 0.06), F.P(xb - 0.1, yb - 0.12, DZ + 0.06)
                    metal.cyl(p0, p1, 0.022, "VH_DoorSteel", 4)
                    hx = xb if li == 0 else xa
                    for hy in (ya + 0.35, yb - 0.35):
                        h0, h1 = sorted((hx, hx + (0.5 if li == 1 else -0.5)))
                        F.box(metal, h0, h1, hy - 0.035, hy + 0.035, DZ + 0.07, DZ + 0.085, "VH_Steel")
                else:
                    # glazed balcony door: painted frame, three lights, kick panel
                    for (u0, u1, a, b) in ((xa, xa + 0.08, ya, yb), (xb - 0.08, xb, ya, yb), (xa, xb, ya, ya + 0.38), (xa, xb, yb - 0.09, yb),
                                           (xa, xb, lerp(ya + 0.38, yb, 0.5) - 0.025, lerp(ya + 0.38, yb, 0.5) + 0.025)):
                        F.box(metal, u0, u1, a, b, DZ - 0.02, DZ + 0.05, "WS_PaintTeal")
                    F.box(self.glass, xa + 0.08, xb - 0.08, ya + 0.38, yb - 0.09, DZ, DZ + 0.01, "WS_Glass", skip=("s0", "s1", "s3", "top", "bottom"))
                    metal.cyl(F.P(xb - 0.12 if li == 0 else xa + 0.12, 1.0 + y0, DZ + 0.1), F.P(xb - 0.12 if li == 0 else xa + 0.12, 1.25 + y0, DZ + 0.1),
                              0.012, "VH_Bronze", 6)
            if rail and kind == "loading":
                for yy in (y0 + 1.0, y0 + 0.55):
                    metal.cyl(F.P(uc - hw - 0.05, yy, 0.08), F.P(uc + hw + 0.05, yy, 0.08), 0.022, "WS_PaintYellow", 8)
                    for u in (uc - hw - 0.03, uc + hw + 0.03):
                        F.box(metal, u - 0.04, u + 0.04, yy - 0.05, yy + 0.05, 0.0, 0.1, "VH_Steel")
                self.fdrip(F, uc - hw - 0.1, uc - hw + 0.05, y0 + 0.95, 1.4, 0.8, "rust", soft=0.05)
                self.fdrip(F, uc + hw - 0.05, uc + hw + 0.1, y0 + 0.95, 1.4, 0.8, "rust", soft=0.05)
        self.later.append(build)

    # ------------------------------------------------------------------ hoist beam with trolley, chain block and hook
    def hoist(self, uc, y=7.26, out=1.55, hook_y=5.55):
        m = self.metal
        F = self.FRONT
        # I-section beam, built into the lintel course
        m.box((uc - 0.013, y + 0.02, -0.4), (uc + 0.013, y + 0.24, out), "WS_PaintYellow")
        for yy in (y, y + 0.24):
            m.box((uc - 0.075, yy - 0.0, -0.4), (uc + 0.075, yy + 0.022, out), "WS_PaintYellow")
        m.box((uc - 0.1, y - 0.04, out - 0.018), (uc + 0.1, y + 0.3, out + 0.004), "VH_Steel")              # end stop
        m.box((uc - 0.2, y - 0.2, 0.062), (uc + 0.2, y + 0.42, 0.09), "VH_Steel")                         # wall plate
        if self.lod == 0:
            for dx in (-0.14, 0.14):
                for dy in (-0.12, 0.34):
                    m.sphere((uc + dx, y + dy, 0.09), 0.018, "VH_Steel", 6, hemi_axis=(0, 0, 1))
        # the beam runs back into the building; a stay from its tip to a plate on the parapet takes the load
        ya = self.top_y - 0.5
        m.box((uc - 0.12, ya - 0.14, 0.062), (uc + 0.12, ya + 0.14, 0.09), "VH_Steel")
        m.cyl((uc, ya, 0.09), (uc, y + 0.24, out - 0.08), 0.02, "VH_Steel", 8)
        m.box((uc - 0.03, y + 0.24, out - 0.14), (uc + 0.03, y + 0.3, out - 0.02), "VH_Steel")
        self.fdrip(F, uc - 0.2, uc + 0.2, y - 0.2, 2.2, 0.9, "rust", soft=0.1)
        self.fdrip(F, uc - 0.1, uc + 0.1, ya - 0.14, 0.7, 0.8, "rust", soft=0.07)
        # trolley and chain block
        tz = out - 0.42
        m.box((uc - 0.1, y - 0.12, tz - 0.12), (uc + 0.1, y - 0.005, tz + 0.12), "VH_Steel")
        for sx in (-1, 1):
            for dz in (-0.07, 0.07):
                m.cyl((uc + sx * 0.02, y + 0.03, tz + dz), (uc + sx * 0.06, y + 0.03, tz + dz), 0.035, "VH_Steel", 10)
        body_top, body_bot = y - 0.16, y - 0.52
        m.cyl((uc, body_top, tz), (uc, body_bot, tz), 0.1, "WS_PaintYellow", 14)
        m.cyl((uc - 0.11, (body_top + body_bot) / 2, tz), (uc + 0.11, (body_top + body_bot) / 2, tz), 0.13, "VH_Steel", 16)
        # load chain down to the hook block, hand chain loop at the side
        def chain(x, z, ya, yb, r=0.011):
            if self.lod > 0:
                m.cyl((x, ya, z), (x, yb, z), r * 1.3, "VH_Steel", 6)
                return
            k, yy = 0, ya
            while yy > yb:
                l = 0.045
                if k % 2 == 0:
                    m.box((x - 0.004, yy - l, z - 0.016), (x + 0.004, yy, z + 0.016), "VH_Steel")
                else:
                    m.box((x - 0.016, yy - l, z - 0.004), (x + 0.016, yy, z + 0.004), "VH_Steel")
                yy -= l * 0.82
                k += 1
        chain(uc, tz, body_bot, hook_y + 0.2)
        chain(uc + 0.13, tz + 0.02, (body_top + body_bot) / 2, hook_y + 0.9, 0.008)
        chain(uc + 0.16, tz - 0.03, (body_top + body_bot) / 2, hook_y + 0.9, 0.008)
        m.box((uc - 0.05, hook_y + 0.04, tz - 0.035), (uc + 0.05, hook_y + 0.2, tz + 0.035), "WS_PaintYellow")
        hook = [(uc, hook_y + 0.04, tz), (uc, hook_y - 0.08, tz), (uc + 0.04, hook_y - 0.17, tz), (uc + 0.1, hook_y - 0.15, tz),
                (uc + 0.11, hook_y - 0.07, tz)]
        m.tube(hook, 0.018, "VH_Steel", 8)
        self.rec["notes"].append(f"hoist beam at u {uc}, out {out} m, hook at y {hook_y}")

    # ------------------------------------------------------------------ battle damage: a shell hole filled with rubble
    def patch(self, face, rects, plate=None, impact=None):
        """rects: course-aligned (ua, ub, y0, y1) pieces of the breach (a stepped outline where whole blocks broke
        out); rebuilt with small rough stones in a fat mortar bed. plate: (ua, ub, y0, y1) riveted steel over the
        worst of it."""
        F = self.faces[face][0]
        self.holes[face] += list(rects)

        def build():
            mas, metal = self.mas, self.metal
            for ri, (ua, ub, y0, y1) in enumerate(rects):
                F.box(mas, ua, ub, y0, y1, 0.012, MORTAR_FRONT + 0.004, "VH_Mortar", skip=("s0", "bottom", "top", "s1", "s3"))
                nsub = 2 if y1 - y0 > 0.3 else 1
                for k in range(nsub):
                    a = lerp(y0, y1, k / nsub)
                    b = lerp(y0, y1, (k + 1) / nsub)
                    u = ua + (self.L.uniform(0.0, 0.1) if k % 2 else 0.0)
                    if u > ua:
                        ashlar_block(mas, F, ua + 0.008, u - 0.008, a + 0.008, b - 0.008, mat="VH_AshlarRough",
                                     depth=self.L.uniform(0.045, 0.07), key=("patch", ri, k, "s"), chip=0.35, wear=1.0)
                    while u < ub - 1e-3:
                        ln = self.L.uniform(0.17, 0.38)
                        if ub - (u + ln) < 0.13:
                            ln = ub - u
                        ashlar_block(mas, F, u + 0.008, u + ln - 0.008, a + 0.008, b - 0.008, mat="VH_AshlarRough",
                                     depth=self.L.uniform(0.042, 0.072), key=("patch", ri, k, round(u, 3)), chip=0.35, wear=1.0)
                        u += ln
            if plate:
                ua, ub, y0, y1 = plate
                F.box(metal, ua, ub, y0, y1, 0.066, 0.078, "VH_PaintedSteel")
                if self.lod == 0:
                    for (pa, pb, n_) in (((ua + 0.04, y0 + 0.04), (ub - 0.04, y0 + 0.04), 6), ((ua + 0.04, y1 - 0.04), (ub - 0.04, y1 - 0.04), 6),
                                         ((ua + 0.04, y0 + 0.04), (ua + 0.04, y1 - 0.04), 4), ((ub - 0.04, y0 + 0.04), (ub - 0.04, y1 - 0.04), 4)):
                        for i in range(n_):
                            t = i / (n_ - 1)
                            metal.sphere(F.P(lerp(pa[0], pb[0], t), lerp(pa[1], pb[1], t), 0.078), 0.014, "VH_Steel", 6, hemi_axis=tuple(F.n))
                self.fdrip(F, ua, ub, y0, 1.8, 0.85, "rust", soft=0.12)
            if impact:
                uc, yc, r = impact
                self.scars.impact(tuple(F.P(uc, yc, 0.07)), r, 1.0)
        self.later.append(build)

    # ------------------------------------------------------------------ balcony: stone slab on corbels, railing, hung tie rods
    def balcony(self, u0, u1, y=5.1, proj=0.95, rail_h=1.0):
        F, trim, metal = self.FRONT, self.trim, self.metal
        # slab in three stones, moulded front edge
        n = 3
        for i in range(n):
            a, b = lerp(u0, u1, i / n), lerp(u0, u1, (i + 1) / n)
            bid = trim.new_block(tint=stone_tint())
            vs, made = F.box(trim, a + 0.004, b - 0.004, y - 0.16, y, -0.05, proj, "VH_Ashlar", bid)
            eroded_bevel(trim, list(made["top"].edges) + list(made["bottom"].edges), 0.014, 2)
        # corbels under both ends and between: three stepped stones each
        for uc in (u0 + 0.35, u1 - 0.35):
            for k, (h, p) in enumerate(((0.18, 0.72), (0.17, 0.5), (0.2, 0.28))):
                yt = y - 0.16 - 0.17 * k
                bid = trim.new_block(tint=stone_tint())
                vs, made = F.box(trim, uc - 0.16, uc + 0.16, yt - h, yt, -0.05, p, "VH_Ashlar", bid)
                eroded_bevel(trim, list(made["s2"].edges) + list(made["bottom"].edges), 0.012, 2)
            self.fdrip(F, uc - 0.2, uc + 0.2, y - 0.7, 2.4, 0.75, soft=0.12)
        self.fdrip(F, u0, u1, y - 0.16, 3.0, 0.5, soft=0.3)
        # railing: posts, balusters, top and bottom rails (painted steel)
        yb, yt = y + 0.08, y + rail_h
        zf = proj - 0.08
        pts = [(u0 + 0.05, zf), (u1 - 0.05, zf)]
        metal.cyl((pts[0][0], yt, zf), (pts[1][0], yt, zf), 0.028, "VH_PaintedSteel", 10)
        metal.box((pts[0][0], yb, zf - 0.02), (pts[1][0], yb + 0.04, zf + 0.02), "VH_PaintedSteel")
        for side_u in (u0 + 0.05, u1 - 0.05):
            metal.cyl((side_u, yt, 0.06), (side_u, yt, zf), 0.028, "VH_PaintedSteel", 10)
            metal.box((side_u - 0.02, yb, 0.06), (side_u + 0.02, yb + 0.04, zf), "VH_PaintedSteel")
            metal.cyl((side_u, y, zf), (side_u, yt, zf), 0.03, "VH_PaintedSteel", 10)
        step = 0.13 if self.lod == 0 else 0.26
        u = u0 + 0.05 + step
        while u < u1 - 0.05 - step * 0.5:
            metal.cyl((u, yb, zf), (u, yt, zf), 0.011, "VH_PaintedSteel", 6)
            u += step
        for side_u in (u0 + 0.05, u1 - 0.05):
            z = 0.06 + step
            while z < zf - step * 0.5:
                metal.cyl((side_u, yb, z), (side_u, yt, z), 0.011, "VH_PaintedSteel", 6)
                z += step
        # hung tie rods from the wall above the doors to the slab edge (the slab is also carried by the corbels)
        for uc in (u0 + 0.9, u1 - 0.9):
            metal.cyl((uc, y + 2.25, 0.08), (uc, y + 0.02, proj - 0.04), 0.014, "VH_Steel", 6)
            metal.box((uc - 0.07, y + 2.18, 0.062), (uc + 0.07, y + 2.34, 0.09), "VH_Steel")
            self.fdrip(F, uc - 0.08, uc + 0.08, y + 2.18, 2.0, 0.85, "rust", soft=0.06)
        self.rec["balcony"] = {"u": [u0, u1], "y": y, "proj": proj, "rail": yt}
        return zf, yt

    def draped_cloth(self, u, width, y_top, z_rail, drop_out, drop_in, mat, key):
        """A length of cloth hung over a rail at (y_top, z_rail): drop_out down the street side, drop_in behind."""
        rr = rng_for(*key) if isinstance(key, tuple) else rng_for(key)
        bm = self.canvas.bm
        mi = self.canvas.mi(mat)
        nu = 5 if self.lod == 0 else 2
        nv = 7 if self.lod == 0 else 3
        # profile: inside hang (up to the rail), over the rail, outside hang (drops lower); small bulge outward
        path = [(y_top - drop_in, z_rail - 0.06), (y_top - drop_in * 0.5, z_rail - 0.045), (y_top + 0.02, z_rail - 0.02),
                (y_top + 0.035, z_rail + 0.0), (y_top + 0.02, z_rail + 0.025)]
        k = nv
        for j in range(1, k + 1):
            t = j / k
            path.append((y_top - drop_out * t, z_rail + 0.035 + 0.04 * math.sin(math.pi * t) + rr.uniform(-0.01, 0.01)))
        rows = []
        for i in range(nu + 1):
            s = i / nu
            uu = u - width / 2 + width * s
            row = []
            for (yy, zz) in path:
                wave = 0.012 * math.sin(uu * 17.0 + yy * 5.0) if self.lod == 0 else 0.0
                row.append(bm.verts.new(Vector((uu, yy - (0.03 * math.sin(math.pi * s) if yy < y_top - 0.3 else 0.0), zz + wave))))
            rows.append(row)
        for i in range(nu):
            for j in range(len(path) - 1):
                f = bm.faces.new([rows[i][j], rows[i + 1][j], rows[i + 1][j + 1], rows[i][j + 1]])
                f.material_index = mi
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

    def hide_frame(self, centre, w, h, key, normal=(0, 0, 1), lean=0.0, feet=True):
        """A hide laced into a steel stretching frame. centre on the frame plane; normal = the side the hide faces.
        lean tilts the frame back (radians) about its bottom edge."""
        rr = rng_for(*key) if isinstance(key, tuple) else rng_for(key)
        c = Vector(centre)
        n = Vector(normal).normalized()
        up = Vector((0, 1, 0))
        side = up.cross(n).normalized()
        bottom = c - up * (h / 2)
        up_l = (up * math.cos(lean) - n * math.sin(lean)).normalized()

        def P(sx, sy, d=0.0):
            return bottom + side * sx + up_l * (sy + h / 2) + n * d
        m = self.metal
        corners = [P(-w / 2, -h / 2), P(w / 2, -h / 2), P(w / 2, h / 2), P(-w / 2, h / 2)]
        for a, b in zip(corners, corners[1:] + corners[:1]):
            m.cyl(a, b, 0.018, "VH_Steel", 6)
        if feet:
            for sx in (-w / 2, w / 2):
                m.cyl(P(sx, -h / 2), P(sx, -h / 2) - up * 0.02 + n * -0.25, 0.015, "VH_Steel", 6)
        # hide: irregular outline (a stretched skin with four leg lobes), slightly cupped
        ctr = P(0, 0, 0.01)
        pts = []
        N = 22 if self.lod == 0 else 12
        for i in range(N):
            a = 2 * math.pi * i / N
            lobe = 0.12 * max(0.0, math.cos(2 * a)) ** 3          # legs at the diagonals
            r = 0.36 + lobe + rr.uniform(-0.03, 0.03)
            pts.append((math.cos(a) * r * (w - 0.2) / 0.96, math.sin(a) * r * (h - 0.2) / 0.96))
        bm = self.canvas.bm
        mi = self.canvas.mi("WS_Hide")
        centre_v = bm.verts.new(ctr + n * 0.025)
        ring = [bm.verts.new(P(px, py, 0.012)) for (px, py) in pts]
        for i in range(N):
            f = bm.faces.new([centre_v, ring[i], ring[(i + 1) % N]])
            f.material_index = mi
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        # lacing: cords from every other outline point to the nearest frame edge
        if self.lod == 0:
            for i in range(0, N, 2):
                px, py = pts[i]
                ex = max(-w / 2, min(w / 2, px * 10))
                ey = max(-h / 2, min(h / 2, py * 10))
                tx, ty = (ex, py) if abs(px) / (w / 2) > abs(py) / (h / 2) else (px, ey)
                m.cyl(P(px, py, 0.012), P(tx, ty, 0.0), 0.004, "VH_Rubber", 4)

    def drying_lines(self, x0, x1, z, h=1.7, cloths=()):
        """Rooftop drying frame (two T posts, three lines) with cloth strips hung over the lines."""
        r = self.roof_y
        m = self.metal
        for x in (x0, x1):
            m.cyl((x, r, z), (x, r + h, z), 0.03, "VH_Steel", 8)
            m.cyl((x, r + h, z - 0.45), (x, r + h, z + 0.45), 0.025, "VH_Steel", 8)
            m.box((x - 0.12, r, z - 0.12), (x + 0.12, r + 0.03, z + 0.12), "VH_Steel")
        for dz in (-0.4, 0.0, 0.4):
            m.cyl((x0, r + h - 0.02, z + dz), (x1, r + h - 0.02, z + dz), 0.005, "VH_Rubber", 4)
        for (xc, dz, w, drop, mat) in cloths:
            self.hang(xc, w, r + h - 0.02, z + dz, drop, mat, key=("line", xc, dz))

    def hang(self, xc, w, y, z, drop, mat, key):
        """Cloth hung over a line running along X at (y, z): two drops either side, a little sag."""
        rr = rng_for(*key)
        bm = self.canvas.bm
        mi = self.canvas.mi(mat)
        nu = 4 if self.lod == 0 else 2
        path = [(y - drop * 0.8, z - 0.05), (y - drop * 0.35, z - 0.03), (y + 0.01, z), (y - drop * 0.4, z + 0.035), (y - drop, z + 0.05)]
        rows = []
        for i in range(nu + 1):
            s = i / nu
            x = xc - w / 2 + w * s
            rows.append([bm.verts.new(Vector((x, yy + (0.02 * math.sin(math.pi * s) * rr.uniform(0.5, 1.5) if yy < y else 0.0),
                                              zz + (0.015 * math.sin(x * 11) if self.lod == 0 else 0.0)))) for (yy, zz) in path])
        for i in range(nu):
            for j in range(len(path) - 1):
                f = bm.faces.new([rows[i][j], rows[i + 1][j], rows[i + 1][j + 1], rows[i][j + 1]])
                f.material_index = mi
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

    # ------------------------------------------------------------------ roof: corrugated shed, container workshop, flue
    def roof_shed(self, x0, x1, z0, z1, h=2.1, door_x=None):
        """Lean-to shed of corrugated steel on the roof deck, pitched towards the rear, with a door and a stovepipe."""
        r = self.roof_y
        m, roof = self.metal, self.roof
        hf, hb = h, h - 0.35
        for x in (x0, x1):
            for z, hh in ((z0, hb), (z1, hf)):
                m.box((x - 0.04, r, z - 0.04), (x + 0.04, r + hh, z + 0.04), "VH_PaintedSteel")
        # corrugated walls: vertical sheets with alternating ribs
        def wall(ax, a0, a1, fixed, top_fn, outward):
            k = 0
            a = a0
            while a < a1 - 1e-3:
                b = min(a1, a + 0.1)
                off = 0.018 if k % 2 == 0 else 0.0
                t0 = top_fn((a + b) / 2)
                if ax == "x":
                    m.box((a, r + 0.02, fixed - 0.006 + outward * off), (b, t0, fixed + 0.006 + outward * off), "WS_Corrugated")
                else:
                    m.box((fixed - 0.006 + outward * off, r + 0.02, a), (fixed + 0.006 + outward * off, t0, b), "WS_Corrugated")
                a = b
                k += 1
        front_top = lambda x: r + hf
        rear_top = lambda x: r + hb
        side_top = lambda z: r + lerp(hb, hf, (z - z0) / (z1 - z0))
        wall("x", x0, x1, z1, front_top, 1)
        wall("x", x0, x1, z0, rear_top, -1)
        wall("z", z0, z1, x0, side_top, -1)
        wall("z", z0, z1, x1, side_top, 1)
        # roof sheet with fall to the rear, overhang (continuous corrugated surface)
        corrugated_sheet(roof, x0 - 0.2, x1 + 0.2, (r + hb + 0.02, z0 - 0.25), (r + hf + 0.06, z1 + 0.25), "WS_Corrugated", lod=self.lod)
        if door_x is not None:
            m.box((door_x - 0.42, r + 0.02, z1 + 0.02), (door_x + 0.42, r + 1.95, z1 + 0.05), "VH_DoorSteel")
            m.box((door_x - 0.46, r + 1.95, z1 + 0.0), (door_x + 0.46, r + 2.0, z1 + 0.06), "VH_PaintedSteel")
            m.cyl((door_x + 0.3, r + 0.95, z1 + 0.06), (door_x + 0.3, r + 1.15, z1 + 0.06), 0.012, "VH_Steel", 6)
        sx, sz = x0 + 0.35, (z0 + z1) / 2
        m.cyl((sx, r + hb, sz), (sx, r + hf + 1.1, sz), 0.07, "VH_Steel", 10)
        m.cyl((sx, r + hf + 1.1, sz), (sx, r + hf + 1.14, sz), 0.14, "VH_Steel", 10)
        self.rec["notes"].append("rooftop shed")

    def container(self, x, z, length=3.0, width=2.1, h=1.9, door_end=1, rot=False):
        """Salvaged shipping-container workshop on steel sleepers. Long axis along X (rot=False) or Z."""
        r = self.roof_y
        m = self.metal
        lx, lz = (length / 2, width / 2) if not rot else (width / 2, length / 2)
        y0 = r + 0.22
        for dz in (-lz + 0.3, lz - 0.3) if not rot else (-lx + 0.3, lx - 0.3):
            if not rot:
                m.box((x - lx - 0.2, r, z + dz - 0.08), (x + lx + 0.2, y0, z + dz + 0.08), "VH_PaintedSteel")
            else:
                m.box((x + dz - 0.08, r, z - lz - 0.2), (x + dz + 0.08, y0, z + lz + 0.2), "VH_PaintedSteel")
        # corner posts and top/bottom rails
        for sx in (-1, 1):
            for sz in (-1, 1):
                m.box((x + sx * lx - 0.08 * (sx > 0), y0, z + sz * lz - 0.08 * (sz > 0)), (x + sx * lx + 0.08 * (sx < 0), y0 + h, z + sz * lz + 0.08 * (sz < 0)),
                      "WS_ContainerRust")
        for yy in (y0, y0 + h - 0.1):
            m.box((x - lx, yy, z - lz), (x + lx, yy + 0.1, z - lz + 0.08), "WS_ContainerRust")
            m.box((x - lx, yy, z + lz - 0.08), (x + lx, yy + 0.1, z + lz), "WS_ContainerRust")
            m.box((x - lx, yy, z - lz), (x - lx + 0.08, yy + 0.1, z + lz), "WS_ContainerRust")
            m.box((x + lx - 0.08, yy, z - lz), (x + lx, yy + 0.1, z + lz), "WS_ContainerRust")
        # corrugated side walls (trapezoid ribs)
        def ribs(axis, a0, a1, fixed, outward):
            k = 0
            a = a0 + 0.08
            while a < a1 - 0.08 - 1e-3:
                b = min(a1 - 0.08, a + 0.11)
                off = 0.03 if k % 2 == 0 else 0.0
                if axis == "x":
                    m.box((a, y0 + 0.1, fixed - 0.01 + outward * off), (b, y0 + h - 0.1, fixed + 0.01 + outward * off), "WS_ContainerRust")
                else:
                    m.box((fixed - 0.01 + outward * off, y0 + 0.1, a), (fixed + 0.01 + outward * off, y0 + h - 0.1, b), "WS_ContainerRust")
                a = b
                k += 1
        ribs("x", x - lx, x + lx, z - lz + 0.04, -1)
        ribs("x", x - lx, x + lx, z + lz - 0.04, 1)
        ribs("z", z - lz, z + lz, x - lx + 0.04, -1) if not (rot is False and door_end == -1) else None
        m.box((x - lx + 0.02, y0 + h - 0.1, z - lz + 0.02), (x + lx - 0.02, y0 + h - 0.02, z + lz - 0.02), "WS_ContainerRust")
        # door end: two leaves with locking bars
        ex = x + door_end * lx
        m.box((ex - 0.03, y0 + 0.1, z - lz + 0.08), (ex + 0.03, y0 + h - 0.1, z + lz - 0.08), "WS_ContainerRust")
        for zz in (z - lz * 0.55, z - lz * 0.15, z + lz * 0.15, z + lz * 0.55):
            m.cyl((ex + door_end * 0.05, y0 + 0.15, zz), (ex + door_end * 0.05, y0 + h - 0.15, zz), 0.018, "VH_Steel", 6)
            m.box((ex + door_end * 0.03 - 0.02, y0 + h * 0.45, zz - 0.05), (ex + door_end * 0.03 + 0.02, y0 + h * 0.55, zz + 0.05), "VH_Steel")
        # a cut-in window and vent on the street side
        m.box((x - 0.35, y0 + 0.9, z + lz + 0.02), (x + 0.35, y0 + 1.45, z + lz + 0.05), "VH_Steel")
        self.glass.box((x - 0.3, y0 + 0.95, z + lz + 0.05), (x + 0.3, y0 + 1.4, z + lz + 0.055), "WS_Glass")
        for i in range(5):
            yy = y0 + 0.97 + i * 0.09
            m.box((x - 0.3, yy, z + lz + 0.055), (x + 0.3, yy + 0.02, z + lz + 0.075), "VH_Steel")
        self.rec["notes"].append("rooftop container workshop")
        return y0 + h

    def flue(self, face, u, y0, y_top, r=0.1):
        """Forge/stove flue: steel pipe from a wall thimble up the face and above the parapet, rain cap, soot plume."""
        F = self.faces[face][0]
        m = self.metal
        a = F.P(u, y0, 0.0)
        b = F.P(u, y0, 0.28)
        c = F.P(u, y_top, 0.28)
        m.cyl(a, b, r, "VH_Steel", 12)
        m.cyl(b + Vector((0, -0.02, 0)), c, r, "VH_Steel", 12)
        m.sphere(b, r * 1.08, "VH_Steel", 10)
        # wall brackets
        y = y0 + 1.2
        while y < y_top - 0.8:
            F.box(m, u - 0.02, u + 0.02, y - 0.03, y + 0.03, 0.06, 0.2, "VH_Steel")
            m.cyl(F.P(u, y, 0.28) + Vector((0, -0.03, 0)), F.P(u, y, 0.28) + Vector((0, 0.03, 0)), r * 1.3, "VH_Steel", 12)
            y += 1.3
        # rain cap
        m.cyl(c, c + Vector((0, 0.25, 0)), r * 0.5, "VH_Steel", 8)
        m.cyl(c + Vector((0, 0.25, 0)), c + Vector((0, 0.32, 0)), r * 2.2, "VH_Steel", 12, r2=r * 0.4)
        self.scorch(face, u - 0.35, u + 0.35, y0 + 0.2, 2.4, 0.55)
        self.fdrip(F, u - 0.3, u + 0.3, y0 - 0.05, 1.4, 0.7, "rust", soft=0.1)

    def gas_cage(self, face, u, w=1.2, d=0.5, h=1.55):
        """Steel mesh cage bolted to the wall at street level with four gas bottles (and a collider)."""
        F = self.faces[face][0]
        m = self.metal
        u0, u1 = u - w / 2, u + w / 2
        # frame
        for uu in (u0, u1):
            for dd in (0.06, 0.06 + d):
                F.box(m, uu - 0.02, uu + 0.02, BASE, BASE + h, dd - 0.02, dd + 0.02, "VH_PaintedSteel")
        for yy in (BASE + 0.05, BASE + h - 0.03):
            F.box(m, u0, u1, yy - 0.02, yy + 0.02, 0.06 + d - 0.02, 0.06 + d + 0.02, "VH_PaintedSteel")
            F.box(m, u0 - 0.02, u0 + 0.02, yy - 0.02, yy + 0.02, 0.06, 0.06 + d, "VH_PaintedSteel")
            F.box(m, u1 - 0.02, u1 + 0.02, yy - 0.02, yy + 0.02, 0.06, 0.06 + d, "VH_PaintedSteel")
        F.box(m, u0, u1, BASE + h - 0.03, BASE + h, 0.06, 0.06 + d + 0.03, "VH_PaintedSteel")       # lid
        # mesh (thin bars) on the open faces
        step = 0.08 if self.lod == 0 else 0.16
        uu = u0 + step
        while uu < u1 - 1e-3:
            m.cyl(F.P(uu, BASE + 0.07, 0.06 + d), F.P(uu, BASE + h - 0.05, 0.06 + d), 0.004, "VH_Steel", 4)
            uu += step
        # bottles
        colours = ["WS_PaintTeal", "WS_PaintRed", "WS_PaintYellow", "WS_PaintTeal"]
        for i in range(4):
            bu = lerp(u0 + 0.16, u1 - 0.16, i / 3)
            base = F.P(bu, BASE + 0.07, 0.06 + d / 2)
            m.cyl(base, base + Vector((0, 1.05, 0)), 0.12, colours[i], 14)
            m.sphere(base + Vector((0, 1.05, 0)), 0.12, colours[i], 12, hemi_axis=(0, 1, 0))
            m.cyl(base + Vector((0, 1.15, 0)), base + Vector((0, 1.27, 0)), 0.03, "VH_Brass", 8)
        # chain across the bottles, padlock
        F.box(m, u0, u1, BASE + 0.9, BASE + 0.93, 0.06 + d - 0.05, 0.06 + d - 0.03, "VH_Steel")
        # collider for the cage (local shop space)
        a, b = F.P(u0, BASE, 0.04), F.P(u1, BASE + h, 0.08 + d)
        lo = [min(a[i], b[i]) for i in range(3)]
        hi = [max(a[i], b[i]) for i in range(3)]
        self.rec["colliders"].append({"name": "COL_GasCage", "center": [(lo[i] + hi[i]) / 2 for i in range(3)], "size": [hi[i] - lo[i] for i in range(3)]})

    def braced_canopy(self, u0, u1, y, proj=1.5, braces=()):
        """Steel canopy: channel fascia and steel deck, carried on raking knee braces from wall plates below."""
        F, m = self.FRONT, self.metal
        F.box(m, u0, u1, y - 0.02, y + 0.03, 0.05, proj, "VH_PaintedSteel")                     # deck
        F.box(m, u0, u1, y - 0.2, y + 0.06, proj - 0.06, proj, "VH_PaintedSteel")               # fascia channel
        F.box(m, u0, u1, y - 0.2, y - 0.17, proj - 0.14, proj, "VH_PaintedSteel")
        F.box(m, u0 - 0.05, u1 + 0.05, y - 0.06, y + 0.09, 0.0, 0.14, "VH_Steel")              # wall angle
        n = max(2, round((u1 - u0) / 0.9) + 1)
        for k in range(n):
            u = lerp(u0 + 0.06, u1 - 0.06, k / (n - 1))
            F.box(m, u - 0.04, u + 0.04, y - 0.2, y - 0.02, 0.05, proj - 0.06, "VH_PaintedSteel")   # rafter
        for u in braces:                                                                          # raking knee braces on the piers
            F.box(m, u - 0.09, u + 0.09, y - 0.78, y - 0.55, 0.062, 0.09, "VH_Steel")
            m.cyl(F.P(u, y - 0.66, 0.09), F.P(u, y - 0.18, proj * 0.6), 0.032, "VH_PaintedSteel", 8)
            self.fdrip(F, u - 0.1, u + 0.1, y - 0.55, 1.5, 0.8, "rust", soft=0.07)
        # gutter spout at one end
        m.cyl(F.P(u1 - 0.1, y - 0.1, proj - 0.03), F.P(u1 + 0.05, y - 0.12, proj + 0.15), 0.03, "VH_Steel", 8)
        self.fdrip(F, u0, u1, y - 0.06, 1.0, 0.55, "rust", soft=0.2)
        self.rec["canopy"] = {"u": [u0, u1], "y": y, "proj": proj}

    def display(self, du0, du1, dy0, dy1, depth=1.25, light=(1.0, 0.8, 0.58), riser_mat="VH_Ashlar"):
        """Lit shop window: stone riser, stone reveals, plain alcove behind clear glass. Returns (F, AZ, glass z)."""
        s = self
        s.holes["front"] += [(du0, du1, dy0, dy1), (du0 - 0.2, du1 + 0.2, dy1, dy1 + 0.42)]
        AZ = -depth

        def build():
            F, trim, metal = s.FRONT, s.trim, s.metal
            bid = trim.new_block(tint=stone_tint())
            vs, made = F.box(trim, du0 - 0.1, du1 + 0.1, dy0 - 0.12, dy0, -0.3, 0.12, "VH_Ashlar", bid)
            eroded_bevel(trim, list(made["top"].edges), 0.014, 2)
            jy = [dy0] + [c for c in s.courses if dy0 < c < dy1] + [dy1]
            for (a, b) in ((du0 - 0.001, du0 + 0.07), (du1 - 0.07, du1 + 0.001)):
                for (y0, y1) in zip(jy, jy[1:]):
                    bid = trim.new_block(tint=stone_tint(), ao=0.85)
                    F.box(trim, a, b, y0 + .004, y1 - .004, -0.3, 0.03, "VH_Ashlar", bid, skip=("bottom", "top"))
            # stone lintel with a relieving flat arch
            n = 5
            xs = [lerp(du0 - 0.2, du1 + 0.2, i / n) for i in range(n + 1)]
            for i, (a, b) in enumerate(zip(xs, xs[1:])):
                key = i == n // 2
                bid = trim.new_block(tint=stone_tint())
                vs, made = F.box(trim, a + .005, b - .005, dy1 + .005, dy1 + 0.42 + (0.07 if key else 0.0) - .005, -0.3, 0.1 if key else 0.08,
                                 "VH_Ashlar", bid, skip=("s0",))
                eroded_bevel(trim, list(made["s2"].edges) + list(made["bottom"].edges), 0.016, 2, seg_len=0.2)
            # alcove shell (cloth-lined back, painted sides, boarded floor)
            F.box(metal, du0, du1, dy0, dy1, AZ - 0.05, AZ, "WS_ClothOchre")
            F.box(metal, du0 - 0.05, du0, dy0, dy1, AZ, -0.3, "WS_PanelDark")
            F.box(metal, du1, du1 + 0.05, dy0, dy1, AZ, -0.3, "WS_PanelDark")
            F.box(metal, du0, du1, dy1 - 0.05, dy1, AZ, -0.3, "WS_PanelDark")
            F.box(metal, du0, du1, dy0 - 0.05, dy0, AZ, -0.3, "WS_Deck")
            GZ = -0.24
            for (u0, u1, a, b) in ((du0, du0 + 0.06, dy0, dy1), (du1 - 0.06, du1, dy0, dy1), (du0, du1, dy0, dy0 + 0.06), (du0, du1, dy1 - 0.06, dy1),
                                   (du0, du1, dy1 - 0.52, dy1 - 0.47)):
                F.box(metal, u0, u1, a, b, GZ - 0.03, GZ + 0.04, "VH_PaintedSteel")
            F.box(s.clear, du0 + 0.03, du1 - 0.03, dy0 + 0.03, dy1 - 0.03, GZ, GZ + 0.008, "WS_ClearGlass", skip=("s0", "s1", "s3", "top", "bottom"))
            # warm strip light behind the transom bar
            F.box(s.glow, du0 + 0.08, du1 - 0.08, dy1 - 0.6, dy1 - 0.57, -0.45, -0.38, "WS_LedWarm")
            s.fdrip(F, du0 - 0.2, du1 + 0.2, dy0 - 0.12, 1.3, 0.55, soft=0.15)
        s.later.append(build)
        s.rec["display"] = {"u": [du0, du1], "y": [dy0, dy1], "back": AZ, "glass": -0.24, "props": [],
                            "light": {"pos": [(du0 + du1) / 2, dy1 - 0.25, -0.6], "target": [(du0 + du1) / 2, dy0, AZ + 0.3],
                                      "color": list(light), "intensity": 3.2, "range": 3.0}}
        return AZ

    def cloth_bolt(self, p, r, length, mat, axis="x"):
        m = self.canvas
        a = Vector(p)
        d = Vector((length, 0, 0)) if axis == "x" else Vector((0, length, 0)) if axis == "y" else Vector((0, 0, length))
        m.cyl(a, a + d, r, mat, 14)
        self.metal.cyl(a - d * 0.03, a + d * 1.03, r * 0.22, "VH_Dark", 8)

    def dress_form(self, p, h=1.6, coat="WS_ClothIndigo"):
        """Tailor's dummy on a steel stand wearing a draped coat (lathed profile)."""
        x, y, z = p
        m = self.metal
        m.cyl((x, y, z), (x, y + 0.03, z), 0.18, "VH_Dark", 12)
        m.cyl((x, y + 0.03, z), (x, y + h * 0.5, z), 0.018, "VH_Brass", 8)
        prof = [(0.0, h * 0.5), (0.16, h * 0.5), (0.19, h * 0.62), (0.15, h * 0.72), (0.18, h * 0.84), (0.2, h * 0.9), (0.12, h * 0.96),
                (0.05, h * 0.99), (0.04, h * 1.04), (0.0, h * 1.05)]
        bm = self.canvas.bm
        mi = self.canvas.mi(coat)
        N = 16 if self.lod == 0 else 8
        rings = []
        for (r, yy) in prof:
            ring = []
            for i in range(N):
                a = 2 * math.pi * i / N
                ring.append(bm.verts.new(Vector((x + math.cos(a) * r * 1.15, y + yy, z + math.sin(a) * r * 0.8))))
            rings.append(ring)
        for j in range(len(rings) - 1):
            for i in range(N):
                f = bm.faces.new([rings[j][i], rings[j][(i + 1) % N], rings[j + 1][(i + 1) % N], rings[j + 1][i]])
                f.material_index = mi
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        # coat skirt: open cone below the waist
        sk = []
        for (r, yy) in ((0.2, h * 0.52), (0.27, h * 0.36), (0.31, h * 0.22)):
            sk.append([bm.verts.new(Vector((x + math.cos(2 * math.pi * i / N) * r * 1.1, y + yy, z + math.sin(2 * math.pi * i / N) * r * 0.85)))
                       for i in range(N)])
        for j in range(len(sk) - 1):
            for i in range(N):
                f = bm.faces.new([sk[j][i], sk[j][(i + 1) % N], sk[j + 1][(i + 1) % N], sk[j + 1][i]])
                f.material_index = mi


# ====================================================================== the shops
def salvage(lod):
    """West row, z 18 (local +X = south towards the Tool Exchange). Loading bay, loading door and hoist, shell-hole repair.
    Since 1 Oct 2026 a walk-in shop: the bay's shutter is rolled up and the ground floor is fitted out
    (art/salvage_shop_20261001/salvage_interior.py; the exterior's random layout is unchanged)."""
    s = NShop("Salvage", lod, (1.02, 0.95, 0.86), 1818 + 4)
    walkin.prepare(s)
    s.shutter("front", -3.0, 0.3, open=True)
    s.portal("front", 1.95, 0.95, 3.15, kind="single", door_mat="WS_PaintOlive", arch=False)
    s.upper_door("front", -1.35, 1.3)
    s.window("front", 1.35, 2.25, 5.50, 7.18, kind="bars")
    # the old breach: whole blocks shot out left of the upper window, rebuilt in rubble, worst part plated over
    s.patch("front", [(0.05, 0.75, 5.50, 5.92), (-0.25, 0.95, 5.92, 6.34), (-0.1, 1.0, 6.34, 6.76), (0.2, 0.7, 6.76, 7.18)],
            plate=(0.05, 0.62, 5.98, 6.62), impact=(0.45, 6.3, 1.2))
    s.window("right", 2.4, 3.3, 5.50, 7.18, kind="bars")
    s.window("right", 4.4, 5.3, 1.89, 3.15, kind="bars")
    s.window("left", -5.3, -4.4, 5.50, 7.18, kind="bars")
    s.portal("rear", -1.0, 0.95, 3.15, kind="single", door_mat="VH_PaintedSteel", arch=False, transom=0.0)
    s.window("rear", 1.2, 2.2, 5.50, 7.18, kind="bars")
    s.scorch("front", -2.0, -0.7, 7.18, 1.4, 0.65)                # fire through the loading door once
    s.scorch("left", -5.4, -4.3, 7.18, 1.2, 0.6)
    s.walls()
    s.top(cornice_h=0.42)
    s.porch()
    s.hoist(-1.35)
    s.lamp("front", 0.8, 3.3, "Lamp between shutter and door")
    s.lamp("front", 3.05, 3.3, "Door lamp south")
    s.lamp("rear", -1.0, 3.75, "Rear door lamp")
    s.sign("SALVAGE", -1.35, 4.41, 2.6, 0.66)
    s.junction_box("front", 0.8, 1.35)
    s.conduit([(0.8, 1.55, 0.14), (0.8, 3.05, 0.14)])
    s.conduit([(0.95, 1.55, 0.14), (0.95, 4.2, 0.14), (0.15, 4.2, 0.14)])
    s.downpipe("left", -1.1, 7.65)
    s.roof_shed(-3.0, -0.7, -3.3, -1.1, door_x=-1.85)
    s.roof_hatch_and_ac(1.7, -5.0)
    s.fitting("right", 1.4, 5.2, "PH_SecurityLight", "Side security light")
    s.fitting("rear", 2.5, BASE, "PH_AirconRusted", "Rear air conditioner", off=0.35)
    s.fitting("left", -2.2, 1.5, "PH_PowerBox", "Side power box")
    walkin.add(s)
    return s


def repairs(lod):
    """East row, z 9 (local -X = south, the side the cross street and Basic General look at). Tall workshop bay under a
    braced steel canopy, glazed door, forge flue, gas cage; container workshop on the roof."""
    s = NShop("Repairs", lod, (0.98, 0.93, 0.86), 909 + 7, upper=[5.08, 5.50, 5.92, 6.34], parapet=0.55)
    s.shutter("front", -3.05, 0.35, top=3.99)
    s.portal("front", 1.95, 1.0, 3.15, kind="glazed", door_mat="WS_PaintOchre", arch=True)
    s.window("front", 1.15, 2.05, 5.50, 6.34, kind="bars", lintel=False)
    s.window("left", -3.2, -2.3, 1.89, 3.15, kind="bars")
    s.window("left", -4.5, -3.6, 5.50, 6.34, kind="bars", lintel=False)
    s.window("left", -2.3, -1.4, 5.50, 6.34, kind="bars", lintel=False)
    s.portal("left", -5.35, 0.95, 3.15, kind="single", door_mat="WS_PaintOchre", arch=False, transom=0.0)
    s.window("right", 2.2, 3.1, 1.89, 3.15, kind="bars")
    s.portal("rear", 1.4, 0.95, 3.15, kind="single", door_mat="VH_PaintedSteel", arch=False, transom=0.0)
    s.window("rear", -2.4, -1.4, 1.89, 3.15, kind="bars")
    s.scorch("front", -3.0, 0.3, 4.41, 1.1, 0.5)                   # sooted over the bay (welding and the old fire)
    s.scorch("left", -3.3, -2.2, 3.57, 1.9, 0.75)
    s.walls()
    s.top(cornice_h=0.4)
    s.porch()
    s.braced_canopy(-3.35, 0.9, 4.36, proj=1.55, braces=(-3.42, 0.72))
    s.lamp("front", 0.85, 3.0, "Lamp between bay and door")
    s.lamp("front", 3.05, 3.3, "Door lamp north")
    s.lamp("left", -5.35, 3.75, "Side door lamp")
    s.lamp("rear", 1.4, 3.75, "Rear door lamp")
    s.sign("REPAIRS", -1.35, 5.71, 2.4, 0.62)
    s.flue("left", -1.75, 1.6, s.top_y + 0.9)
    # (no gas cage: the retrofit bin cluster - grey locker, green cabinet, drums - already dresses this wall)
    s.junction_box("front", 0.85, 1.35)
    s.conduit([(0.85, 1.55, 0.14), (0.85, 3.15, 0.14)])
    s.downpipe("right", 5.6, 6.39)
    s.container(-0.4, -2.35, length=3.2, width=2.1, h=1.9, door_end=-1)
    s.roof_hatch_and_ac(1.2, -5.0)
    s.fitting("right", 1.3, 4.2, "PH_SecurityLight", "Side security light")
    s.fitting("rear", -0.3, BASE, "PH_AirconRusted", "Rear air conditioner", off=0.35)
    s.fitting("left", -2.75, 4.15, "PH_PowerBox", "Side power box")
    return s


def thread_hide(lod):
    """East row, z 18. Lit cloth display, indigo awning, stone balcony with dyed cloth and hides, drying lines."""
    s = NShop("ThreadHide", lod, (1.08, 0.99, 0.9), 1818 + 11, parapet=0.57)
    du0, du1, dy0, dy1 = -3.0, -0.35, 1.05, 3.57
    AZ = s.display(du0, du1, dy0, dy1, depth=1.25)
    s.portal("front", 1.25, 1.1, 3.15, kind="glazed", door_mat="WS_PaintTeal", arch=True)
    s.window("front", 2.45, 2.9, 1.89, 3.15, kind="bars", lintel=False)
    s.upper_door("front", -1.55, 1.2, kind="glazed", rail=False)
    s.upper_door("front", 1.55, 1.2, kind="glazed", rail=False)
    s.window("right", 2.4, 3.3, 5.50, 7.18, kind="shutters")
    s.window("right", 4.4, 5.3, 1.89, 3.15, kind="bars")
    s.window("left", -3.3, -2.4, 5.50, 7.18, kind="shutters")
    s.window("left", -5.3, -4.4, 1.89, 3.15, kind="bars")
    s.portal("rear", 0.0, 0.95, 3.15, kind="single", door_mat="VH_PaintedSteel", arch=False, transom=0.0)
    s.window("rear", -2.4, -1.4, 5.50, 7.18, kind="bars")
    s.window("rear", 1.4, 2.4, 5.50, 7.18, kind="bars")
    s.scorch("left", -5.4, -4.3, 3.15, 1.6, 0.55)

    def display_goods():
        F = s.FRONT
        # shelf rack of cloth bolts against the back, a dress form in a coat, folded hides on a low bench
        F.box(s.metal, du0 + 0.1, du1 - 0.1, 2.35, 2.38, AZ + 0.02, AZ + 0.4, "VH_Steel")
        F.box(s.metal, du0 + 0.1, du1 - 0.1, 1.65, 1.68, AZ + 0.02, AZ + 0.4, "VH_Steel")
        mats = ["WS_ClothIndigo", "WS_ClothMadder", "WS_ClothOchre", "WS_ClothBone", "WS_ClothIndigo", "WS_ClothOchre", "WS_ClothMadder"]
        for row, yy in enumerate((1.68, 2.38)):
            n = 6
            for i in range(n):
                x = lerp(du0 + 0.25, du1 - 0.25, i / (n - 1))
                s.cloth_bolt((x, yy + 0.075, AZ + 0.05), 0.07, 0.33, mats[(i + row * 3) % len(mats)], axis="z")
        s.dress_form((du1 - 0.55, dy0, AZ + 0.72), h=1.62, coat="WS_ClothIndigo")
        F.box(s.metal, du0 + 0.15, du0 + 1.05, dy0, dy0 + 0.4, AZ + 0.55, AZ + 1.0, "VH_Dark")
        for k, mat in enumerate(("WS_Hide", "WS_Hide", "WS_ClothBone")):
            F.box(s.canvas, du0 + 0.2 + k * 0.03, du0 + 1.0 - k * 0.04, dy0 + 0.4 + k * 0.06, dy0 + 0.46 + k * 0.06, AZ + 0.58 + k * 0.02, AZ + 0.97 - k * 0.03, mat)
        s.hide_frame((du0 + 0.75, dy0 + 1.1, AZ + 0.12), 0.9, 0.8, ("disp_hide",), normal=(0, 0, 1), feet=False)
    s.later.append(display_goods)
    s.walls()
    s.top(cornice_h=0.45)
    s.porch()
    s.awning(-3.25, 2.05, 3.93, proj=1.45, drop=0.48, mat="WS_ClothIndigo")
    zf, yt = s.balcony(-3.05, 3.05, y=5.1, proj=0.95)
    for k, (u, w, mat) in enumerate(((-2.55, 0.55, "WS_ClothMadder"), (-1.75, 0.6, "WS_ClothOchre"), (1.1, 0.5, "WS_ClothIndigo"),
                                     (1.8, 0.55, "WS_ClothBone"))):
        s.draped_cloth(u, w, yt + 0.03, zf, 0.95 + 0.1 * (k % 2), 0.5, mat, ("drape", k))
    s.hide_frame((0.0, 5.1 + 0.68, 0.3), 0.9, 1.25, ("bal_hide", 0), normal=(0, 0, 1), lean=0.1)
    s.hide_frame((2.72, 5.1 + 0.6, 0.38), 0.6, 1.05, ("bal_hide", 1), normal=(-0.25, 0, 1), lean=0.08)
    s.lamp("front", 0.35, 3.25, "Lamp between window and door")
    s.lamp("front", 2.15, 3.25, "Door lamp north")
    s.lamp("rear", 0.0, 3.75, "Rear door lamp")
    s.sign("THREAD + HIDE", -0.35, 4.43, 3.2, 0.62)
    s.downpipe("left", -1.0, 7.65)
    s.drying_lines(-2.6, 1.6, -1.7, h=2.0, cloths=((-2.0, -0.4, 0.5, 0.9, "WS_ClothIndigo"), (-1.2, 0.0, 0.45, 1.0, "WS_ClothMadder"),
                                            (-0.3, 0.4, 0.55, 0.8, "WS_ClothOchre"), (0.6, -0.4, 0.4, 0.95, "WS_ClothBone"),
                                            (1.0, 0.0, 0.5, 0.7, "WS_Hide")))
    s.roof_hatch_and_ac(1.9, -5.6)
    s.fitting("rear", -2.4, BASE, "PH_AirconRusted", "Rear air conditioner", off=0.35)
    s.fitting("right", 5.6, 1.5, "PH_PowerBox", "Side power box")
    return s


SHOPS = {"salvage": salvage, "repairs": repairs, "thread_hide": thread_hide}


def main():
    names = [a for a in sys.argv[sys.argv.index("--") + 1:]] if "--" in sys.argv else list(SHOPS)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for key in names:
        report = {"source": "art/north_avenue_20260930/author_north_shops.py", "date": "2026-09-30", "shop": key,
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
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "north-shops-source.blend"))


if __name__ == "__main__":
    main()
