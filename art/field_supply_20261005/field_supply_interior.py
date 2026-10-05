"""Walk-in Field Supply (5 October 2026): the loading shutter is rolled up and the ground floor is Tamsin's outfitter's shop.

Carl (4-5 Oct 2026): "Open another shop - field supply. have a choice of low tech to mid tier packs for storage upgrades.
a digital magazine shelf that are basically recipes for crafting upgrades and packs. also sell med kits and nano
recharges."

Used by art/hall_district_20260930/author_ward_shops.py field_supply(): prepare(s) right after the shop is created (the
porch sand stops at the open bay, walk-in colliders), add(s) last (the interior is a deferred builder after every exterior
one, so the exterior's random layout is identical to the 30 Sep shop). Same approach and kit as the walk-in Salvage shop
(art/salvage_shop_20261001/salvage_interior.py), which this module follows.

Shop-local Unity metres (origin = facade centre at paving level, +Z out to the avenue, X along the facade, Y up). The root
sits at world (18.1, 0, -9), yaw -90, so local +X is world +Z (north) and local -Z is world +X (east, away from the avenue).

Ground floor (clear 6.76 x 6.06 m, 3.95 m to a storage-loft deck): rough dado and coursed ashlar on the inner skin, flagged
floor, two painted steel beams carrying timber joists and a board deck, and the shop:
  - Tamsin's counter along the north side: steel frame clad in teal sheet, timber top, a glazed case of nano cells.
  - the med and nano cabinet on the north wall behind her (glass doors; medkits, trauma kits, nano cells, surge packs).
  - the pack wall across the rear: steel uprights, two hook rails and a slatted shelf (the Meshy packs hang in Unity).
  - the digital magazine shelf on the south wall by the bay: three tiers of field slates whose screens show the four
    magazine covers (art/field_supply_20261005/covers/magazine_atlas.png, exact UVs per screen) under a FIELD READS
    lightbox.
  - a free-standing timber pack stand in the room, conduit, a breaker panel and three enamel pendant lamps.
The keeper, the packs, crates and lights are placed in Unity (Editor/FieldSupplyShopPass.cs) from rec["interior"].

Separate parts so Unity can give the room its own ambient, light layer and shadow settings: InteriorMasonry,
InteriorFloor (Masonry Lit), InteriorMetal, InteriorTimber, InteriorDeck (deck boards and the counter top, grain along
the boards), InteriorGlow (bulbs), InteriorScreens (FS_Screens, the cover atlas), InteriorSupplies (med and nano stock),
InteriorGlass (case and cabinet glazing).
"""
import math
import bmesh
import ward_masonry as WM
from ward_masonry import Part, Frame, stone_tint, fill_wall, eroded_bevel, lerp, drng
import sys
# author_ward_shops is usually run as the Blender script itself (__main__); imported by name from other authoring scripts
_AWS = sys.modules.get("author_ward_shops") or sys.modules["__main__"]
BASE, HW, D = _AWS.BASE, _AWS.HW, _AWS.D

IN = 0.42
XI = HW - IN                 # 3.38: inner faces of the side walls
ZF = -IN                     # -0.42: inner face of the front wall
ZR = -D + IN                 # -6.48: inner face of the rear wall
CEIL = 4.45                  # underside of the loft deck
COURSES = [0.5, 1.05, 1.47, 1.89, 2.31, 2.73, 3.15, 3.57, 3.99, CEIL]
BEAMS_X = (-1.15, 1.45)      # painted steel beams along z
BAY = (-2.1, 0.9, 3.57)      # the loading shutter's opening: x0, x1, top
BAY_REVEAL = 0.07
DOOR_F = (1.75, 2.65, 3.57)  # teal front door (closed): x0, x1, top (head 3.15 + transom)
DOOR_R = (1.125, 2.075, 3.15)  # rear door (closed)
COUNTER = dict(x0=1.0, x1=1.7, z0=-4.05, z1=-1.45, top=BASE + 1.0)
CASE = dict(z0=-3.95, z1=-3.1, h=0.3)                       # glazed nano-cell case on the counter's rear end
CABINET = dict(x0=XI - 0.36, x1=XI, z0=-3.7, z1=-1.7, y0=BASE + 0.8, y1=BASE + 2.1)
PACKWALL = dict(x0=-3.25, x1=0.8, z=ZR, rail_top=2.42, rail_low=1.52, shelf=0.98)
SHELF = dict(x=-XI, z0=-2.75, z1=-1.2, tiers=(1.2, 1.55, 1.9), tilt=15.0)   # magazine shelf on the south wall
STAND = dict(x=-0.95, z=-4.35, yaw=0.0)                    # free-standing pack stand (A-frame, hooks both faces)
LAMPS = [("Pendant over the counter", (1.3, 3.35, -2.75)), ("Pendant over the floor", (-0.75, 3.45, -2.6)),
         ("Pendant over the pack wall", (-1.2, 3.45, -5.45))]
COVER_V = (0.625, 1.0)      # the covers' row in the 2048 x 2048 atlas (v up; four 512 x 768 px covers across)
BAND_V = (0.5, 0.625)       # the FIELD READS band under them


def _parts(s):
    n, lod = s.name, s.lod
    s.imas = Part(f"{n}_InteriorMasonry_LOD{lod}", wear=True)
    s.ifloor = Part(f"{n}_InteriorFloor_LOD{lod}", wear=True)
    s.imetal = Part(f"{n}_InteriorMetal_LOD{lod}", wear=False)
    s.iwood = Part(f"{n}_InteriorTimber_LOD{lod}", wear=False)
    s.ideck = Part(f"{n}_InteriorDeck_LOD{lod}", wear=False)
    s.iglow = Part(f"{n}_InteriorGlow_LOD{lod}", wear=False)
    s.iscreen = Part(f"{n}_InteriorScreens_LOD{lod}", wear=False)
    s.isup = Part(f"{n}_InteriorSupplies_LOD{lod}", wear=False)
    s.iglass = Part(f"{n}_InteriorGlass_LOD{lod}", wear=False)
    s.extra_parts = [
        (s.imas, dict(drips=None, ground_y=BASE, splash=0.3, scars=None)),
        (s.ifloor, dict(drips=None, ground_y=BASE, splash=0.0, scars=None, macro=0.14)),
        (s.imetal, dict(ao=False)),
        (s.iwood, dict(ao=False)),
        (s.ideck, dict(ao=False)),
        (s.iglow, dict(ao=False)),
        (s.iscreen, dict(ao=False, macro=0.0, splash=0.0, flat=True)),
        (s.isup, dict(ao=False)),
        (s.iglass, dict(ao=False, macro=0.0, splash=0.0, flat=True)),
    ]


def prepare(s):
    """Before the porch is built: keep the facade sand out of the open bay; walk-in colliders."""
    _parts(s)
    orig_drift = s.drift

    def drift(a, b, z0, key, **k):
        # the porch lays sand along the facade foot; Tamsin sweeps the bay every morning, so the run stops at its reveal
        if a < BAY[1] and b > BAY[0]:
            if a < BAY[0] - 0.3:
                orig_drift(a, BAY[0] - 0.05, z0, key, **k)
            if b > BAY[1] + 0.3:
                orig_drift(BAY[1] + 0.05, b, z0, key + ("b",) if isinstance(key, tuple) else (key, "b"), **k)
            return
        orig_drift(a, b, z0, key, **k)
    s.drift = drift
    s.colliders = lambda: colliders(s)
    s.post_build = post_build


def add(s):
    s.later.append(lambda: build(s))


# ---------------------------------------------------------------------------------------------------------- helpers
def box(part, lo, hi, mat, bid=0, skip=()):
    return part.box(tuple(lo), tuple(hi), mat, bid, skip)


def stone(s, part, lo, hi, mat="VH_Ashlar", bevel=0.012, rough=False):
    bid = part.new_block(tint=stone_tint("rough" if rough else "ashlar"), erode=0.008 if s.lod == 0 else 0.0)
    vs, made = box(part, lo, hi, mat, bid)
    if s.lod == 0:
        eroded_bevel(part, list({e for f in made.values() for e in f.edges}), bevel, 2, seg_len=0.2)
    return made


def post_build(part, ob):
    """Deck boards and the counter top run along z: turn their UVs so the timber grain follows the boards. Magazine
    screens: Part.build's box projection runs u along -z on a face looking +x, which in Unity's left-handed frame is the
    viewer's left, so each cover (and the band) is mirrored back within its own atlas cell."""
    uv = ob.data.uv_layers["UVMap"]
    if "_InteriorScreens_" in part.name:
        for poly in ob.data.polygons:
            us = [uv.data[i].uv[0] for i in poly.loop_indices]
            vs = [uv.data[i].uv[1] for i in poly.loop_indices]
            um, vm = sum(us) / len(us), sum(vs) / len(vs)
            if vm >= COVER_V[0] - 1e-3:
                lo = math.floor(min(max(um, 0.0), 0.9999) * 4) * 0.25
                hi = lo + 0.25
            elif vm >= BAND_V[0] - 1e-3:
                lo, hi = 0.0, 1.0
            else:
                continue
            for i in poly.loop_indices:
                u, v = uv.data[i].uv
                uv.data[i].uv = (lo + hi - u, v)
        return
    if "_InteriorDeck_" not in part.name:
        return
    for d in uv.data:
        u, v = d.uv
        d.uv = (v, -u)


def _wall_frames():
    return {
        "front": (Frame((0, 0, ZF + 0.062), (1, 0, 0), (0, 0, -1)), -XI, XI,
                  [(BAY[0], BAY[1], BASE, BAY[2]), (BAY[0] - 0.2, BAY[1] + 0.2, BAY[2], 3.99),
                   (DOOR_F[0], DOOR_F[1], BASE, DOOR_F[2]), (DOOR_F[0] - 0.14, DOOR_F[1] + 0.14, DOOR_F[2], 3.99)]),
        "rear": (Frame((0, 0, ZR - 0.062), (1, 0, 0), (0, 0, 1)), -XI, XI,
                 [(DOOR_R[0], DOOR_R[1], BASE, DOOR_R[2]), (DOOR_R[0] - 0.14, DOOR_R[1] + 0.14, DOOR_R[2], 3.57)]),
        "west": (Frame((-XI - 0.062, 0, 0), (0, 0, 1), (1, 0, 0)), ZR, ZF, []),
        "east": (Frame((XI + 0.062, 0, 0), (0, 0, 1), (-1, 0, 0)), ZR, ZF, []),
    }


# ---------------------------------------------------------------------------------------------------------- build
def build(s):
    walls(s)
    linings(s)
    floor(s)
    ceiling(s)
    counter(s)
    cabinet(s)
    pack_wall(s)
    magazine_shelf(s)
    pack_stand(s)
    services(s)
    lamps(s)
    s.rec["interior"] = {
        "note": "walk-in ground floor (art/field_supply_20261005/field_supply_interior.py); shop-local metres",
        "bounds": [[-XI, BASE, ZR], [XI, CEIL, ZF]],
        "bay": {"x": [BAY[0], BAY[1]], "top": BAY[2], "z": [ZF, 0.0]},
        "counter": {"x": [COUNTER["x0"], COUNTER["x1"]], "z": [COUNTER["z0"], COUNTER["z1"]], "top": COUNTER["top"]},
        "keeper": [2.35, BASE, -2.7],
        "case": {"z": [CASE["z0"], CASE["z1"]], "top": COUNTER["top"] + 0.055 + CASE["h"]},
        "cabinet": {"x": [CABINET["x0"], CABINET["x1"]], "z": [CABINET["z0"], CABINET["z1"]], "y": [CABINET["y0"], CABINET["y1"]]},
        "shelf": {"x": SHELF["x"], "z": [SHELF["z0"], SHELF["z1"]], "glow": [SHELF["x"] + 0.35, 2.35, (SHELF["z0"] + SHELF["z1"]) / 2]},
        "pack_hooks": s.rec.get("_hooks", []),
        "beams_x": list(BEAMS_X), "ceiling": CEIL,
        "lamps": [{"name": n, "pos": list(p)} for n, p in LAMPS],
        "doors_closed": {"front": [DOOR_F[0], DOOR_F[1]], "rear": [DOOR_R[0], DOOR_R[1]]},
    }
    s.rec.pop("_hooks", None)


def walls(s):
    for face, (F, u0, u1, holes) in _wall_frames().items():
        if s.lod > 0:
            for ci, (y0, y1) in enumerate(zip(COURSES, COURSES[1:])):
                for (a, b) in WM.course_intervals(u0, u1, holes, y0, y1):
                    F.box(s.imas, a, b, y0, y1, 0.02, 0.062, "VH_AshlarRough" if ci == 0 else "VH_Ashlar",
                          s.imas.new_block(tint=stone_tint()), skip=("s0",))
            continue
        for ci, (y0, y1) in enumerate(zip(COURSES, COURSES[1:])):
            rough = ci == 0
            fill_wall(s.imas, F, u0, u1, [y0, y1], holes, mat="VH_AshlarRough" if rough else "VH_Ashlar",
                      key=("fs_in", face), course_offset=ci, lmin=0.5, lmax=1.15, depth=0.062)


def linings(s):
    """Close the wall void at the openings: stone jambs and lintels from the inner skin to the outer reveals."""
    zi = ZF - 0.005
    for (x0, x1) in ((BAY[0], BAY[0] + BAY_REVEAL), (BAY[1] - BAY_REVEAL, BAY[1])):
        ys = [c for c in COURSES if c <= BAY[2]]
        for (a, b) in zip(ys, ys[1:]):
            stone(s, s.imas, (x0 + 0.003, a + 0.004, zi), (x1 - 0.003, b - 0.004, -0.345))
    m = s.imetal
    box(m, (BAY[0] - 0.2, BAY[2], ZF - 0.03), (BAY[1] + 0.2, 3.99, -0.33), "VH_PaintedSteel")
    box(m, (BAY[0] - 0.2, BAY[2] - 0.02, ZF - 0.07), (BAY[1] + 0.2, BAY[2] + 0.03, ZF - 0.02), "VH_PaintedSteel")
    box(m, (BAY[0] - 0.2, 3.94, ZF - 0.07), (BAY[1] + 0.2, 3.99, ZF - 0.02), "VH_PaintedSteel")
    if s.lod == 0:
        x = BAY[0] - 0.15
        while x < BAY[1] + 0.15:
            for yy in (BAY[2] + 0.08, 3.9):
                m.sphere((x, yy, ZF - 0.03), 0.012, "VH_Steel", 6, hemi_axis=(0, 0, -1))
            x += 0.3
    for (x0, x1, top), (za, zb), lz in (((DOOR_F[0], DOOR_F[1], DOOR_F[2]), (ZF - 0.005, -0.385), (ZF - 0.04, -0.38)),
                                        ((DOOR_R[0], DOOR_R[1], DOOR_R[2]), (-6.515, ZR + 0.005), (-6.52, ZR + 0.04))):
        for (a, b) in ((x0 - 0.1, x0), (x1, x1 + 0.1)):
            ys = [c for c in COURSES if c < top] + [top]
            for (y0, y1) in zip(ys, ys[1:]):
                stone(s, s.imas, (a + 0.003, y0 + 0.004, min(za, zb)), (b - 0.003, y1 - 0.004, max(za, zb)), bevel=0.008)
        stone(s, s.imas, (x0 - 0.14 + 0.004, top + 0.004, min(lz)), (x1 + 0.14 - 0.004, top + 0.42 - 0.004, max(lz)), bevel=0.014)
        stone(s, s.ifloor, (x0, BASE - 0.1, min(za, zb)), (x1, BASE + 0.012, max(za, zb)), "VH_PodiumSlab", bevel=0.006, rough=True)


FX = XI + 0.06
FZ0, FZ1 = ZR - 0.06, ZF + 0.045


def floor(s):
    f = s.ifloor
    if s.lod > 0:
        box(f, (-FX, BASE - 0.12, FZ0), (FX, BASE, FZ1), "VH_PodiumSlab", f.new_block(tint=stone_tint("rough")), skip=("bottom",))
        box(f, (BAY[0] + BAY_REVEAL, BASE - 0.12, FZ1), (BAY[1] - BAY_REVEAL, BASE, -0.34), "VH_PodiumSlab", skip=("bottom",))
        return
    L = WM.S.LAYOUT
    z, row = FZ1, 0
    while z > FZ0 + 1e-3:
        dz = min(L.uniform(0.6, 0.85), z - FZ0)
        if z - dz - FZ0 < 0.3:
            dz = z - FZ0
        x = -FX
        first = True
        while x < FX - 1e-3:
            ln = L.uniform(0.7, 1.1)
            if first and row % 2:
                ln *= 0.5
            first = False
            x1 = min(FX, x + ln)
            if FX - x1 < 0.3:
                x1 = FX
            bid = f.new_block(tint=stone_tint("rough"), erode=0.01)
            vs, made = box(f, (x + 0.004, BASE - 0.12, z - dz + 0.004), (x1 - 0.004, BASE - L.uniform(0.0, 0.006), z - 0.004),
                           "VH_PodiumSlab", bid, skip=("bottom",))
            eroded_bevel(f, list(made["top"].edges), L.uniform(0.006, 0.014), 2, seg_len=0.2)
            x = x1
        z -= dz
        row += 1
    x = BAY[0] + BAY_REVEAL
    while x < BAY[1] - BAY_REVEAL - 1e-3:
        x1 = min(BAY[1] - BAY_REVEAL, x + L.uniform(0.8, 1.2))
        bid = f.new_block(tint=stone_tint("rough"), erode=0.012)
        vs, made = box(f, (x + 0.004, BASE - 0.1, FZ1 + 0.004), (x1 - 0.004, BASE, -0.344), "VH_PodiumSlab", bid, skip=("bottom",))
        eroded_bevel(f, list(made["top"].edges), 0.01, 2, seg_len=0.2)
        x = x1
    # a worn rubber mat inside the bay (customers' boots) and a drain grate
    m = s.imetal
    box(m, (BAY[0] + 0.35, BASE - 0.001, -1.75), (BAY[1] - 0.35, BASE + 0.012, -0.62), "VH_Rubber")
    box(m, (-2.95, BASE - 0.004, -5.95), (-2.35, BASE + 0.004, -5.7), "VH_Dark")
    for k in range(8):
        xx = lerp(-2.92, -2.38, k / 7)
        box(m, (xx - 0.012, BASE - 0.004, -5.94), (xx + 0.012, BASE + 0.006, -5.71), "VH_Steel")


def ceiling(s):
    m, w, d = s.imetal, s.iwood, s.ideck
    for bx in BEAMS_X:
        mat = "VH_PaintedSteel"
        z0, z1 = ZR - 0.12, ZF + 0.12
        box(m, (bx - 0.08, CEIL - 0.018, z0), (bx + 0.08, CEIL, z1), mat)
        box(m, (bx - 0.08, CEIL - 0.3, z0), (bx + 0.08, CEIL - 0.282, z1), mat)
        box(m, (bx - 0.006, CEIL - 0.282, z0), (bx + 0.006, CEIL - 0.018, z1), mat)
        for zz, sgn in ((ZR, 1), (ZF, -1)):
            za, zb = sorted((zz, zz + sgn * 0.06))
            pad_bottom = 4.0 if zz == ZF else CEIL - 0.62
            stone(s, s.imas, (bx - 0.22, pad_bottom, za), (bx + 0.22, CEIL - 0.322, zb), bevel=0.01)
            za, zb = sorted((zz, zz + sgn * 0.24))
            box(m, (bx - 0.12, CEIL - 0.322, za), (bx + 0.12, CEIL - 0.3, zb), "VH_Steel")
            for dz in (0.12, 0.3):
                zc = zz + sgn * dz
                box(m, (bx + 0.006, CEIL - 0.282, zc - 0.006), (bx + 0.075, CEIL - 0.018, zc + 0.006), mat)
                box(m, (bx - 0.075, CEIL - 0.282, zc - 0.006), (bx - 0.006, CEIL - 0.018, zc + 0.006), mat)
        if s.lod == 0:
            z = z0 + 0.25
            while z < z1 - 0.2:
                for sx in (-0.05, 0.05):
                    m.sphere((bx + sx, CEIL - 0.3, z), 0.01, "VH_Steel", 6, hemi_axis=(0, -1, 0))
                z += 0.5
    spans = [(-XI, BEAMS_X[0] - 0.08), (BEAMS_X[0] + 0.08, BEAMS_X[1] - 0.08), (BEAMS_X[1] + 0.08, XI)]
    if s.lod == 0:
        z = ZF - 0.32
        k = 0
        while z > ZR + 0.15:
            for (a, b) in spans:
                rr = drng("fs_joist", k, round(a, 2))
                bid = w.new_block(off=(rr.uniform(0, 8), rr.uniform(0, 8)), tint=(0.5, 0.5, 0.5))
                vs, made = box(w, (a, CEIL - 0.2 - rr.uniform(0.0, 0.006), z - 0.038), (b, CEIL, z + 0.038), "SS_Timber", bid)
                w.bevel_edges([e for e in made["bottom"].edges], 0.006, 1)
                if a > -XI + 0.01:
                    box(m, (a, CEIL - 0.205, z - 0.042), (a + 0.05, CEIL - 0.02, z + 0.042), "VH_Steel")
                if b < XI - 0.01:
                    box(m, (b - 0.05, CEIL - 0.205, z - 0.042), (b, CEIL - 0.02, z + 0.042), "VH_Steel")
            z -= 0.55
            k += 1
        x = -XI
        k = 0
        while x < XI - 1e-3:
            rr = drng("fs_board", k)
            x1 = min(XI, x + rr.uniform(0.14, 0.2))
            if XI - x1 < 0.06:
                x1 = XI
            bid = d.new_block(off=(rr.uniform(0, 8), rr.uniform(0, 8)), tint=(0.5, 0.5, 0.5))
            box(d, (x + 0.003, CEIL + rr.uniform(-0.003, 0.0), ZR), (x1 - 0.003, CEIL + 0.03, ZF), "SS_Boards", bid, skip=("top",))
            x = x1
            k += 1
        box(d, (-XI, CEIL + 0.03, ZR), (XI, CEIL + 0.04, ZF), "VH_Dark", skip=("bottom",))
    else:
        box(d, (-XI, CEIL, ZR), (XI, CEIL + 0.04, ZF), "SS_Boards", skip=("top",))


def counter(s):
    """Tamsin's counter: a steel frame clad in teal sheet (Field Supply's door colour) with a stencilled kick, a timber top
    with a steel nosing, a shelf of stock on her side and a glazed case of nano cells at the rear end."""
    m, d, sup, gl = s.imetal, s.ideck, s.isup, s.iglass
    c = COUNTER
    x0, x1, z0, z1, top = c["x0"], c["x1"], c["z0"], c["z1"], c["top"]
    box(m, (x0 + 0.06, BASE, z0 + 0.06), (x1 - 0.02, BASE + 0.1, z1 - 0.06), "VH_Dark")
    box(m, (x0 + 0.02, BASE + 0.1, z0 + 0.02), (x1 - 0.02, top - 0.04, z1 - 0.02), "VH_Dark", skip=("top",))
    posts_z = [z0, lerp(z0, z1, 1 / 3), lerp(z0, z1, 2 / 3), z1]
    for i, pz in enumerate(posts_z):
        for px in (x0, x1) if i in (0, len(posts_z) - 1) else (x0,):
            box(m, (px - 0.02, BASE + 0.08, pz - 0.022), (px + 0.025, top - 0.04, pz + 0.022), "VH_Steel")
    for yy in (BASE + 0.1, top - 0.08):
        box(m, (x0 - 0.02, yy, z0), (x0 + 0.02, yy + 0.04, z1), "VH_Steel")
    for i, (a, b) in enumerate(zip(posts_z, posts_z[1:])):
        rr = drng("fs_cpanel", i)
        box(m, (x0 - 0.012 - rr.uniform(0, 0.003), BASE + 0.14, a + 0.03), (x0 + 0.004, top - 0.085, b - 0.03), "WS_PaintTeal")
        if s.lod == 0:
            for yy in (BASE + 0.17, top - 0.11):
                zz = a + 0.07
                while zz < b - 0.05:
                    m.sphere((x0 - 0.014, yy, zz), 0.006, "VH_Steel", 6, hemi_axis=(-1, 0, 0))
                    zz += 0.16
            # scuffed kick plate where boots meet it
            box(m, (x0 - 0.016, BASE + 0.14, a + 0.05), (x0 - 0.011, BASE + 0.3, b - 0.05), "VH_Steel")
    for zz, sgn in ((z1, 1), (z0, -1)):
        box(m, (x0 + 0.03, BASE + 0.14, min(zz, zz + 0.012 * sgn)), (x1 - 0.03, top - 0.085, max(zz, zz + 0.012 * sgn)), "WS_PaintTeal")
    box(d, (x0 - 0.07, top, z0 - 0.06), (x1 + 0.05, top + 0.055, z1 + 0.06), "SS_Timber")
    box(m, (x0 - 0.085, top - 0.012, z0 - 0.06), (x0 - 0.065, top + 0.062, z1 + 0.06), "VH_Steel")
    box(m, (x0 - 0.065, top + 0.055, z0 - 0.06), (x0 + 0.03, top + 0.062, z1 + 0.06), "VH_Steel")
    # her side: a shelf with boxed stock (medkits, folded webbing) under the top
    box(m, (x0 + 0.12, BASE + 0.42, z0 + 0.08), (x1 - 0.01, BASE + 0.445, z1 - 0.08), "VH_Steel")
    zz = z1 - 0.15
    k = 0
    while zz > z0 + 0.25:
        rr = drng("fs_under", k)
        w = rr.uniform(0.22, 0.32)
        mat = ("FS_MedRed", "FS_Canvas", "FS_MedOlive", "FS_Canvas")[k % 4]
        box(sup, (x0 + 0.2, BASE + 0.445, zz - w), (x0 + 0.2 + rr.uniform(0.3, 0.42), BASE + 0.445 + rr.uniform(0.1, 0.2), zz), mat)
        zz -= w + rr.uniform(0.04, 0.1)
        k += 1
    # glazed case: felt base, steel corner posts, glass, nano cells in a row of foam cradles
    ty = top + 0.055
    cz0, cz1, ch = CASE["z0"], CASE["z1"], CASE["h"]
    cx0, cx1 = x0 - 0.02, x1 - 0.02
    box(sup, (cx0 + 0.02, ty, cz0 + 0.02), (cx1 - 0.02, ty + 0.04, cz1 - 0.02), "FS_Felt")
    for (px, pz) in ((cx0, cz0), (cx0, cz1), (cx1, cz0), (cx1, cz1)):
        box(m, (px - 0.012, ty, pz - 0.012), (px + 0.012, ty + ch, pz + 0.012), "VH_Steel")
    box(m, (cx0 - 0.012, ty + ch - 0.015, cz0 - 0.012), (cx1 + 0.012, ty + ch, cz1 + 0.012), "VH_Steel")
    box(gl, (cx0, ty + 0.04, cz0), (cx1, ty + ch - 0.015, cz1), "FS_CaseGlass", skip=("bottom",))
    for i in range(6):
        zc = lerp(cz0 + 0.1, cz1 - 0.1, i / 5)
        nano_cell(s, (lerp(cx0, cx1, 0.42), ty + 0.04 + 0.026, zc), axis="x", length=0.13)
    for i in range(2):
        surge_pack(s, (lerp(cx0, cx1, 0.8), ty + 0.04, lerp(cz0 + 0.22, cz1 - 0.22, i)))


def nano_cell(s, c, axis="y", length=0.12, r=0.024):
    """A nanite recharge cartridge: knurled steel caps, a glowing cyan window and an amber band."""
    sup = s.isup
    x, y, z = c
    ax = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}[axis]
    a = (x - ax[0] * length / 2, y - ax[1] * length / 2, z - ax[2] * length / 2)
    def at(t):
        return (a[0] + ax[0] * length * t, a[1] + ax[1] * length * t, a[2] + ax[2] * length * t)
    seg = 12 if s.lod == 0 else 8
    sup.cyl(at(0.0), at(0.18), r * 1.06, "VH_Steel", seg)
    sup.cyl(at(0.18), at(0.74), r * 0.92, "FS_NanoGlow", seg)
    sup.cyl(at(0.74), at(0.82), r, "FS_Amber", seg)
    sup.cyl(at(0.82), at(1.0), r * 1.06, "VH_Steel", seg)
    if s.lod == 0:
        sup.cyl(at(1.0), at(1.06), r * 0.3, "VH_Steel", 6)


def surge_pack(s, base):
    """Twin cartridges clamped in a scorched bracket with a finned regulator between them."""
    sup = s.isup
    x, y, z = base
    box(sup, (x - 0.05, y, z - 0.09), (x + 0.05, y + 0.02, z + 0.09), "VH_Dark")
    for dz in (-0.05, 0.05):
        nano_cell(s, (x, y + 0.02 + 0.07, z + dz), axis="y", length=0.14, r=0.026)
    box(sup, (x - 0.03, y + 0.04, z - 0.018), (x + 0.03, y + 0.13, z + 0.018), "VH_Steel")
    if s.lod == 0:
        for k in range(4):
            yy = y + 0.05 + k * 0.02
            box(sup, (x - 0.036, yy, z - 0.022), (x + 0.036, yy + 0.006, z + 0.022), "VH_Steel")
    box(sup, (x - 0.052, y + 0.11, z - 0.092), (x - 0.046, y + 0.13, z + 0.092), "FS_Amber")


def medkit(s, lo, w=0.26, h=0.15, dpt=0.11, mat="FS_MedRed", face="-x"):
    """A hard medical case standing on a shelf, its lid facing out (white cross on the face, steel latches, a handle)."""
    sup = s.isup
    x, y, z = lo
    box(sup, (x, y, z), (x + dpt, y + h, z + w), mat)
    fx = x - 0.004 if face == "-x" else x + dpt + 0.004
    fa, fb = sorted((fx, x if face == "-x" else x + dpt))
    zc, yc = z + w / 2, y + h / 2
    cw = min(w, h) * 0.18
    ca = min(w, h) * 0.5
    box(sup, (fa, yc - cw / 2, zc - ca / 2), (fb, yc + cw / 2, zc + ca / 2), "FS_MedWhite")
    box(sup, (fa, yc - ca / 2, zc - cw / 2), (fb, yc + ca / 2, zc + cw / 2), "FS_MedWhite")
    if s.lod == 0:
        for zz in (z + 0.03, z + w - 0.05):
            box(sup, (fa - 0.004, y + h - 0.045, zz), (fb, y + h - 0.02, zz + 0.02), "VH_Steel")
        box(sup, (x + dpt * 0.3, y + h, zc - 0.05), (x + dpt * 0.7, y + h + 0.025, zc + 0.05), "VH_Dark")


def cabinet(s):
    """Wall cabinet on the north wall behind the counter: steel carcass, two glass doors, three shelves of medkits,
    trauma kits, nano cells and surge packs; an enamel red-cross plaque over it."""
    m, gl, sup = s.imetal, s.iglass, s.isup
    c = CABINET
    x0, x1, z0, z1, y0, y1 = c["x0"], c["x1"], c["z0"], c["z1"], c["y0"], c["y1"]
    t = 0.02
    box(m, (x0 + 0.02, y0, z0), (x1, y0 + t, z1), "VH_PaintedSteel")                    # bottom
    box(m, (x0 + 0.02, y1 - t, z0), (x1, y1, z1), "VH_PaintedSteel")                    # top
    box(m, (x0 + 0.02, y0, z0), (x1, y1, z0 + t), "VH_PaintedSteel")                    # ends
    box(m, (x0 + 0.02, y0, z1 - t), (x1, y1, z1), "VH_PaintedSteel")
    box(m, (x1 - 0.015, y0, z0), (x1, y1, z1), "VH_Dark")                               # back
    zm = (z0 + z1) / 2
    box(m, (x0 + 0.02, y0, zm - 0.01), (x1, y1, zm + 0.01), "VH_PaintedSteel")          # centre divider
    shelves = [y0 + t, y0 + 0.45, y0 + 0.88]
    for yy in shelves[1:]:
        box(m, (x0 + 0.03, yy - 0.015, z0 + t), (x1 - 0.015, yy, z1 - t), "VH_Steel")
    # doors: steel frames round glass, hinged at the ends, handles near the middle
    for (za, zb) in ((z0, zm), (zm, z1)):
        box(m, (x0, y0, za), (x0 + 0.025, y1, za + 0.035), "VH_PaintedSteel")
        box(m, (x0, y0, zb - 0.035), (x0 + 0.025, y1, zb), "VH_PaintedSteel")
        box(m, (x0, y0, za), (x0 + 0.025, y0 + 0.04, zb), "VH_PaintedSteel")
        box(m, (x0, y1 - 0.04, za), (x0 + 0.025, y1, zb), "VH_PaintedSteel")
        box(gl, (x0 + 0.008, y0 + 0.04, za + 0.035), (x0 + 0.014, y1 - 0.04, zb - 0.035), "FS_CaseGlass")
        hz = zb - 0.06 if za == z0 else za + 0.06
        box(m, (x0 - 0.03, (y0 + y1) / 2 - 0.09, hz - 0.01), (x0, (y0 + y1) / 2 + 0.09, hz + 0.01), "VH_Steel")
    # stock: bottom shelf medkits and trauma kits, middle nano cells in racks, top surge packs and boxed cells
    xs = x0 + 0.06
    k = 0
    for (za, zb) in ((z0 + t + 0.02, zm - 0.03), (zm + 0.03, z1 - t - 0.02)):
        z = za
        while True:
            trauma = k % 3 == 2
            w = 0.3 if trauma else 0.26
            if z + w > zb:
                break
            medkit(s, (xs, shelves[0], z), w=w, h=0.17 if trauma else 0.15, dpt=0.24, mat="FS_MedOlive" if trauma else "FS_MedRed")
            z += w + 0.03
            k += 1
    for side, (za, zb) in enumerate(((z0 + 0.05, zm - 0.04), (zm + 0.04, z1 - 0.05))):
        for row in range(2):
            xr = x0 + 0.1 + row * 0.11
            n = 7
            for i in range(n):
                nano_cell(s, (xr, shelves[1] + 0.065, lerp(za + 0.04, zb - 0.04, i / (n - 1))), axis="y", length=0.12)
        box(sup, (x0 + 0.05, shelves[1], za), (x1 - 0.03, shelves[1] + 0.01, zb), "VH_Dark")
    for i, zc in enumerate((z0 + 0.15, z0 + 0.38, zm + 0.18, zm + 0.42, z1 - 0.2)):
        if i % 2 == 0:
            surge_pack(s, (x0 + 0.16, shelves[2], zc))
        else:
            box(sup, (x0 + 0.07, shelves[2], zc - 0.1), (x0 + 0.26, shelves[2] + 0.12, zc + 0.1), "FS_Canvas")
    # plaque over the cabinet: white enamel disc with a red cross
    pz, py = zm, y1 + 0.22
    s.imetal.cyl((XI - 0.012, py, pz), (XI - 0.03, py, pz), 0.16, "FS_MedWhite", 24 if s.lod == 0 else 12)
    box(sup, (XI - 0.036, py - 0.03, pz - 0.1), (XI - 0.03, py + 0.03, pz + 0.1), "FS_MedRed")
    box(sup, (XI - 0.036, py - 0.1, pz - 0.03), (XI - 0.03, py + 0.1, pz + 0.03), "FS_MedRed")


def pack_wall(s):
    """Steel uprights on the rear wall with two hook rails (packs hang from them in Unity) and a slatted shelf."""
    m, w = s.imetal, s.iwood
    p = PACKWALL
    z = p["z"]
    ups = [p["x0"] + i * (p["x1"] - p["x0"]) / 4 for i in range(5)]
    for x in ups:
        box(m, (x - 0.025, BASE + 0.05, z), (x + 0.025, 2.75, z + 0.04), "VH_PaintedSteel")
        if s.lod == 0:
            yy = BASE + 0.2
            while yy < 2.7:
                box(m, (x - 0.008, yy, z + 0.039), (x + 0.008, yy + 0.03, z + 0.042), "VH_Dark")
                yy += 0.07
            for yy in (0.62, 2.62):
                m.sphere((x, yy, z + 0.042), 0.009, "VH_Steel", 6, hemi_axis=(0, 0, 1))
    hooks = []
    for name, ry, xs in (("top", p["rail_top"], [lerp(p["x0"], p["x1"], (i + 0.5) / 4) for i in range(4)]),
                         ("low", p["rail_low"], [lerp(p["x0"], p["x1"], i / 4) for i in (0.5, 1.5, 2.5, 3.5)])):
        box(m, (p["x0"] - 0.05, ry - 0.025, z + 0.04), (p["x1"] + 0.05, ry + 0.025, z + 0.07), "VH_Steel")
        for i, x in enumerate(xs):
            if name == "low" and i % 2 == 1:
                continue          # the low rail's hooks stagger under the gaps between the top row's packs
            m.tube([(x, ry, z + 0.07), (x, ry, z + 0.2), (x, ry + 0.06, z + 0.24)], 0.009, "VH_Steel", 6)
            hooks.append({"name": f"{name}_{i}", "pos": [round(x, 3), round(ry, 3), round(z + 0.2, 3)], "facing": [0, 0, 1]})
    # slatted timber shelf on brackets
    sy = p["shelf"]
    for x in ups[1:-1]:
        box(m, (x - 0.02, sy - 0.18, z + 0.04), (x + 0.02, sy, z + 0.4), "VH_PaintedSteel")
    for k in range(4):
        rr = drng("fs_slat", k)
        bid = w.new_block(off=(rr.uniform(0, 8), rr.uniform(0, 8)), tint=(0.5, 0.5, 0.5))
        za = z + 0.06 + k * 0.088
        box(w, (p["x0"] + 0.4, sy, za), (p["x1"] - 0.4, sy + 0.03, za + 0.075), "SS_Timber", bid)
    # folded stock on the shelf: canvas bundles and webbing rolls
    x = p["x0"] + 0.5
    k = 0
    while x < p["x1"] - 0.7:
        rr = drng("fs_stock", k)
        ww = rr.uniform(0.28, 0.4)
        if k % 3 == 2:
            s.isup.cyl((x, sy + 0.1, z + 0.22), (x + ww, sy + 0.1, z + 0.22), 0.07, "FS_Webbing", 12 if s.lod == 0 else 8)
        else:
            box(s.isup, (x, sy + 0.03, z + 0.08), (x + ww, sy + 0.03 + rr.uniform(0.1, 0.16), z + 0.36), "FS_Canvas")
        x += ww + rr.uniform(0.05, 0.12)
        k += 1
    s.rec.setdefault("_hooks", []).extend(hooks)


def _screen(s, i, z_left, y_bottom, w, h, tilt, x_face, copy_key):
    """One field slate leaning back on a tier: rugged bumper frame (metal) and its screen (cover i of the atlas). The
    screen's UVs come from Part.build's box projection; its block offset and scale put the face exactly on cover i."""
    m, sc = s.imetal, s.iscreen
    ct, st = math.cos(math.radians(tilt)), math.sin(math.radians(tilt))
    # the slate face plane leans back towards the wall (-x) by `tilt`
    def P(zz, yy, d):
        lift = yy - y_bottom
        return (x_face - lift * st / ct * 1.0 + d, yy, zz)
    zr = z_left - w        # viewer faces -x; the screen's left edge is at the larger z
    yt = y_bottom + h * ct
    pad = 0.014
    # bumper frame (a slab slightly larger than the screen, 1.4 cm thick)
    corners = []
    for (zz, yy) in ((zr - pad, y_bottom - pad), (z_left + pad, y_bottom - pad), (z_left + pad, yt + pad), (zr - pad, yt + pad)):
        corners.append((zz, yy))
    c = [P(zz, yy, -0.016) for (zz, yy) in corners] + [P(zz, yy, -0.002) for (zz, yy) in corners]
    # hexa expects bottom face 4 then top face 4 (any consistent box ordering works with Part.hexa's winding)
    m.hexa([c[0], c[1], c[2], c[3], c[4], c[5], c[6], c[7]], "VH_Dark")
    # screen face, 1 mm proud of the bumper: own block whose box projection lands on cover i
    s_ = 0.25 / w                                   # u span of one cover / screen width
    ou = i * 0.25 + z_left * s_                     # u = -z * s + ou  (face normal +x)
    ov = COVER_V[0] - y_bottom * s_                 # v = y * s + ov
    bid = sc.new_block(off=(ou, ov), scale=s_, tint=(1, 1, 1))
    q = [P(zr, y_bottom, 0.0), P(z_left, y_bottom, 0.0), P(z_left, yt, 0.0), P(zr, yt, 0.0)]
    q2 = [P(zr, y_bottom, -0.001), P(z_left, y_bottom, -0.001), P(z_left, yt, -0.001), P(zr, yt, -0.001)]
    sc.hexa([q2[0], q2[1], q2[2], q2[3], q[0], q[1], q[2], q[3]], "FS_Screens", bid, skip=())


def magazine_shelf(s):
    """The digital magazine shelf on the south wall by the bay: a steel frame with a base cabinet, three leaning tiers of
    field slates (each screen shows one of the four covers) and a FIELD READS lightbox on top."""
    m, sc = s.imetal, s.iscreen
    sh = SHELF
    x, z0, z1 = sh["x"], sh["z0"], sh["z1"]
    depth = 0.42
    xf = x + depth
    # frame: two side cheeks, base cabinet, back panel
    for zz in (z0, z1 - 0.03):
        box(m, (x, BASE, zz), (xf, 2.2, zz + 0.03), "VH_PaintedSteel")
    box(m, (x, BASE, z0), (x + 0.02, 2.2, z1), "VH_Dark")
    box(m, (x, BASE, z0 + 0.03), (xf - 0.02, BASE + 0.62, z1 - 0.03), "WS_PaintTeal")
    box(m, (xf - 0.03, BASE + 0.62, z0), (xf, BASE + 0.66, z1), "VH_Steel")
    if s.lod == 0:
        for zz in (lerp(z0, z1, 0.25), lerp(z0, z1, 0.75)):
            box(m, (xf - 0.022, BASE + 0.45, zz - 0.06), (xf - 0.012, BASE + 0.48, zz + 0.06), "VH_Steel")
    # tiers: a steel ledge with a lip; slates lean back against a rail
    w, h, tilt = 0.16, 0.24 / math.cos(math.radians(sh["tilt"])), sh["tilt"]
    order = [(0, 1, 2, 3, 0), (1, 2, 3, 0, 1), (2, 3, 0, 1, 2)]
    for ti, ty in enumerate(sh["tiers"]):
        ledge_x = xf - 0.06 - ti * 0.08
        box(m, (x + 0.02, ty - 0.02, z0 + 0.03), (ledge_x, ty, z1 - 0.03), "VH_Steel")
        box(m, (ledge_x - 0.012, ty, z0 + 0.03), (ledge_x, ty + 0.03, z1 - 0.03), "VH_Steel")
        box(m, (x + 0.02, ty + 0.2, z0 + 0.03), (x + 0.05, ty + 0.22, z1 - 0.03), "VH_Steel")
        n = 5
        span = (z1 - 0.03) - (z0 + 0.03)
        gap = (span - n * w) / (n + 1)
        for k in range(n):
            zl = (z1 - 0.03) - gap - k * (w + gap)
            _screen(s, order[ti][k], zl, ty + 0.002, w, h, tilt, ledge_x - 0.02, (ti, k))
    # lightbox: a steel box with the FIELD READS band on its face (UVs from the atlas band row)
    ly0, ly1 = 2.22, 2.4
    box(m, (x, ly0 - 0.02, z0), (x + 0.16, ly1 + 0.02, z1), "VH_PaintedSteel")
    W = z1 - z0 - 0.06
    s_ = 1.0 / W
    bid = sc.new_block(off=(0.0 + (z1 - 0.03) * s_, BAND_V[0] - ly0 * s_), scale=s_, tint=(1, 1, 1))
    box(sc, (x + 0.16, ly0, z0 + 0.03), (x + 0.162, ly0 + W * (BAND_V[1] - BAND_V[0]), z1 - 0.03), "FS_Screens", bid)


def pack_stand(s):
    """A free-standing timber A-frame stand in the room with hooks on both faces (packs hang from it in Unity)."""
    w, m = s.iwood, s.imetal
    cx, cz = STAND["x"], STAND["z"]
    half = 0.65
    hooks = []
    for side in (-1, 1):
        for zz in (cz - half, cz + half):
            w.cyl((cx + side * 0.32, BASE, zz), (cx + side * 0.04, 2.0, zz), 0.035, "SS_Timber", 8)
        w.cyl((cx + side * 0.3, BASE + 0.25, cz - half), (cx + side * 0.3, BASE + 0.25, cz + half), 0.025, "SS_Timber", 8)
        for k, zz in enumerate((cz - 0.32, cz + 0.32)):
            hx = cx + side * 0.13
            m.tube([(hx, 1.72, zz), (hx + side * 0.12, 1.72, zz), (hx + side * 0.16, 1.78, zz)], 0.009, "VH_Steel", 6)
            hooks.append({"name": f"stand_{'e' if side > 0 else 'w'}{k}", "pos": [round(hx + side * 0.12, 3), 1.72, round(zz, 3)],
                          "facing": [side, 0, 0]})
    w.cyl((cx, 2.0, cz - half - 0.06), (cx, 2.0, cz + half + 0.06), 0.04, "SS_Timber", 10)
    for zz in (cz - half, cz + half):
        box(m, (cx - 0.06, 1.93, zz - 0.02), (cx + 0.06, 2.06, zz + 0.02), "VH_Steel")
    s.rec.setdefault("_hooks", []).extend(hooks)


def services(s):
    m = s.imetal
    zr = ZR + 0.06
    xe = XI - 0.06
    yc = 3.85
    m.tube([(-XI + 0.1, yc, zr), (xe, yc, zr)], 0.024, "VH_Steel", clamps=0.7)
    m.tube([(xe, yc, zr), (xe, yc, ZF - 0.25)], 0.024, "VH_Steel", clamps=0.7)
    m.tube([(2.75, yc, zr), (2.75, 2.3, zr)], 0.024, "VH_Steel", clamps=0.6)
    box(m, (2.4, 1.35, ZR), (3.1, 2.3, ZR + 0.16), "VH_PaintedSteel")
    box(m, (2.43, 1.38, ZR + 0.16), (3.07, 2.27, ZR + 0.175), "WS_PaintOchre")
    box(m, (2.99, 1.75, ZR + 0.175), (3.03, 1.92, ZR + 0.2), "VH_Steel")
    m.tube([(xe, yc, -1.35), (xe, 1.55, -1.35)], 0.02, "VH_Steel", clamps=0.6)
    box(m, (XI - 0.11, 1.35, -1.48), (XI, 1.55, -1.22), "VH_PaintedSteel")
    # the shelf's feed: a conduit down the south wall to the lightbox
    m.tube([(-XI + 0.06, yc, zr), (-XI + 0.06, yc, -2.0), (-XI + 0.06, 2.42, -2.0)], 0.018, "VH_Steel", clamps=0.6)


def lamps(s):
    m, g = s.imetal, s.iglow
    for name, (x, y, z) in LAMPS:
        m.cyl((x, CEIL - 0.2, z), (x, y + 0.16, z), 0.005, "VH_Rubber", 6)
        m.cyl((x, CEIL - 0.21, z), (x, CEIL - 0.19, z), 0.045, "VH_Steel", 10)
        m.cyl((x, y + 0.16, z), (x, y + 0.08, z), 0.03, "VH_Steel", 10)
        seg = 18 if s.lod == 0 else 10
        m.cyl((x, y + 0.1, z), (x, y - 0.06, z), 0.06, "WS_PaintTeal", seg, cap=False, r2=0.24)
        inner = m.cyl((x, y + 0.095, z), (x, y - 0.055, z), 0.055, "SS_Enamel", seg, cap=False, r2=0.232)
        bmesh.ops.reverse_faces(m.bm, faces=inner)
        g.sphere((x, y - 0.0, z), 0.05, "SS_BulbWarm", 10 if s.lod == 0 else 6)


# ---------------------------------------------------------------------------------------------------------- colliders
def colliders(s):
    c = s.rec["colliders"]
    g = s.gable
    top = g["eave"] + 0.2
    X, Z0, Z1 = HW + 0.09, -D - 0.09, 0.09

    def add(name, lo, hi):
        c.append({"name": name, "center": [round((a + b) / 2, 4) for a, b in zip(lo, hi)],
                  "size": [round(b - a, 4) for a, b in zip(lo, hi)]})
    add("COL_WallWest", (-X, BASE, Z0), (-XI, CEIL, Z1))
    add("COL_WallEast", (XI, BASE, Z0), (X, CEIL, Z1))
    add("COL_WallRear", (-XI, BASE, Z0), (XI, CEIL, ZR))
    add("COL_FrontPier_bay_south", (-XI, BASE, ZF), (BAY[0], CEIL, Z1))
    add("COL_FrontPier_bay_door", (BAY[1], BASE, ZF), (DOOR_F[0], CEIL, Z1))
    add("COL_FrontPier_door_north", (DOOR_F[1], BASE, ZF), (XI, CEIL, Z1))
    add("COL_OverBay", (BAY[0], BAY[2], ZF), (BAY[1], CEIL, Z1))
    add("COL_ShutterBox", (BAY[0], BAY[2] - 0.44, -0.31), (BAY[1], BAY[2], -0.05))
    add("COL_OverDoor_1.75", (DOOR_F[0], DOOR_F[2], ZF), (DOOR_F[1], CEIL, Z1))
    add("COL_Door_1.75", (DOOR_F[0], BASE, ZF), (DOOR_F[1], DOOR_F[2], -0.34))
    add("COL_Upper", (-X, CEIL, Z0), (X, top, Z1))
    add("COL_Roof", (-HW, g["eave"], -D), (HW, g["ridge"], 0.0))
    add("COL_Floor", (-XI, BASE - 0.12, ZR), (XI, BASE, -0.34))
    k = COUNTER
    add("COL_Counter", (k["x0"] - 0.085, BASE, k["z0"] - 0.06), (k["x1"] + 0.05, k["top"] + 0.062 + CASE["h"], k["z1"] + 0.06))
    add("COL_Cabinet", (CABINET["x0"] - 0.03, CABINET["y0"], CABINET["z0"]), (XI, CABINET["y1"], CABINET["z1"]))
    add("COL_PackWall", (PACKWALL["x0"] - 0.05, BASE, ZR), (PACKWALL["x1"] + 0.05, 2.75, ZR + 0.42))
    add("COL_MagazineShelf", (SHELF["x"], BASE, SHELF["z0"]), (SHELF["x"] + 0.42, 2.42, SHELF["z1"]))
    add("COL_PackStand", (STAND["x"] - 0.38, BASE, STAND["z"] - 0.72), (STAND["x"] + 0.38, 2.06, STAND["z"] + 0.72))
