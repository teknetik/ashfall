"""Walk-in Salvage shop (1 October 2026): the loading bay stands open and the ground floor is a working salvage shop.

Carl (1 Oct 2026): "make the salvage shop walkable. i want it part of the tutorial mission ... the salvage shop should be
open to trade and have the equipment in there and an npc to trade with".

Used by art/north_avenue_20260930/author_north_shops.py salvage(): prepare(s) right after the shop is created (porch
sand kept out of the open bay, walk-in colliders), add(s) after everything else (the interior is built last, as a
deferred builder, so the exterior's random layout is identical to the 30 Sep shop).

Shop-local Unity metres (origin = facade centre at paving level, +Z out to the avenue, X along the facade, Y up; the
root sits at world (-18.1, 0, 18), yaw 90, so local +X is world south and local -Z is world west). The shell is a 6 cm
facing at the facade plane; the inner skin stands IN = 0.42 m inside every outer face (the reveals are 0.35-0.4 deep),
lined at the openings so no wall void shows.

Ground floor (clear 6.76 x 6.06 m, 3.95 m to the deck): rough-stone dado and coursed ashlar on the inner skin (the
Ward masonry kit, vertex AO from the whole building), a flagged floor with a checker plate where heavy salvage is
worked, two steel beams on bearing plates (one the yellow monorail of a chain hoist) carrying timber joists and a
board deck, a trade counter of salvaged sheet panels on a steel frame with a timber top, conduit runs, a breaker panel
and three enamel pendant lamps. The workbench, racks, stock, the dealer and lights are placed in Unity
(Editor/SalvageShopPass.cs) from the record written here (rec["interior"]).

Separate parts (so Unity can give the interior its own ambient and shadow settings): InteriorMasonry, InteriorFloor
(Masonry Lit), InteriorMetal, InteriorTimber, InteriorDeck (the deck and counter top: UVs turned so the grain runs
along the boards), InteriorGlow (bulbs).
"""
import math
import bmesh
from mathutils import Vector
import ward_masonry as WM
from ward_masonry import Part, Frame, stone_tint, ashlar_block, fill_wall, eroded_bevel, lerp, drng, MORTAR_FRONT
from author_ward_shops import BASE, HW, D

IN = 0.42
XI = HW - IN                 # 3.38: inner faces of the side walls
ZF = -IN                     # -0.42: inner face of the front wall
ZR = -D + IN                 # -6.48: inner face of the rear wall
CEIL = 4.45                  # underside of the board deck
COURSES = [0.5, 1.05, 1.47, 1.89, 2.31, 2.73, 3.15, 3.57, 3.99, CEIL]
BEAMS_X = (-1.0, 2.0)        # steel beams along z (the east one is the hoist monorail)
BAY = (-3.0, 0.3, 3.57)      # loading bay x0, x1, top (the shutter's opening)
BAY_REVEAL = 0.07            # the shutter's stone reveal width each side
DOOR_F = (1.475, 2.425, 3.57)   # front personnel door (closed) x0, x1, top
DOOR_R = (0.525, 1.475, 3.15)   # rear door (closed) x0, x1, top
COUNTER = dict(x0=1.05, x1=1.75, z0=-3.8, z1=-1.2, top=BASE + 1.0)     # worktop 1.0 m above the floor
HOOK = (BEAMS_X[1], 2.75, -5.1)
LAMPS = [("Pendant over the counter", (1.42, 3.3, -2.5)), ("Pendant over the floor", (-1.75, 3.4, -2.55)),
         ("Pendant over the workbench", (-1.3, 3.55, -4.85))]     # clear of the 2.1 m bench gantry, over the worktop front


def _parts(s):
    n, lod = s.name, s.lod
    s.imas = Part(f"{n}_InteriorMasonry_LOD{lod}", wear=True)
    s.ifloor = Part(f"{n}_InteriorFloor_LOD{lod}", wear=True)
    s.imetal = Part(f"{n}_InteriorMetal_LOD{lod}", wear=False)
    s.iwood = Part(f"{n}_InteriorTimber_LOD{lod}", wear=False)
    s.ideck = Part(f"{n}_InteriorDeck_LOD{lod}", wear=False)
    s.iglow = Part(f"{n}_InteriorGlow_LOD{lod}", wear=False)
    s.extra_parts = [
        (s.imas, dict(drips=None, ground_y=BASE, splash=0.3, scars=None)),
        (s.ifloor, dict(drips=None, ground_y=BASE, splash=0.0, scars=None, macro=0.14)),
        (s.imetal, dict(ao=False)),
        (s.iwood, dict(ao=False)),
        (s.ideck, dict(ao=False)),
        (s.iglow, dict(ao=False)),
    ]


def prepare(s):
    """Before the porch is built: keep the facade sand out of the open bay; walk-in colliders."""
    _parts(s)
    orig_drift = s.drift

    def drift(a, b, z0, key, **k):
        # the porch lays sand along the facade foot; the bay is swept daily, so the run stops at its reveal
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
    """Deck boards and the counter top run along z: turn their UVs so the timber grain follows the boards."""
    if "_InteriorDeck_" not in part.name:
        return
    uv = ob.data.uv_layers["UVMap"]
    for d in uv.data:
        u, v = d.uv
        d.uv = (v, -u)


def _wall_frames():
    return {
        # name: (frame, u0, u1, holes); frames face into the room, block faces land on the inner skin plane
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
    hoist(s)
    counter(s)
    services(s)
    lamps(s)
    s.rec["interior"] = {
        "note": "walk-in ground floor (art/salvage_shop_20261001/salvage_interior.py); shop-local metres",
        "bounds": [[-XI, BASE, ZR], [XI, CEIL, ZF]],
        "bay": {"x": [BAY[0], BAY[1]], "top": BAY[2], "z": [ZF, 0.0]},
        "counter": {"x": [COUNTER["x0"], COUNTER["x1"]], "z": [COUNTER["z0"], COUNTER["z1"]], "top": COUNTER["top"]},
        "beams_x": list(BEAMS_X), "ceiling": CEIL, "hook": list(HOOK),
        "lamps": [{"name": n, "pos": list(p)} for n, p in LAMPS],
        "doors_closed": {"front": [DOOR_F[0], DOOR_F[1]], "rear": [DOOR_R[0], DOOR_R[1]]},
    }


def walls(s):
    for face, (F, u0, u1, holes) in _wall_frames().items():
        if s.lod > 0:
            # LOD1: plain courses (one slab per free span), same stone material
            for ci, (y0, y1) in enumerate(zip(COURSES, COURSES[1:])):
                for (a, b) in WM.course_intervals(u0, u1, holes, y0, y1):
                    F.box(s.imas, a, b, y0, y1, 0.02, 0.062, "VH_AshlarRough" if ci == 0 else "VH_Ashlar",
                          s.imas.new_block(tint=stone_tint()), skip=("s0",))
            continue
        for ci, (y0, y1) in enumerate(zip(COURSES, COURSES[1:])):
            rough = ci == 0
            fill_wall(s.imas, F, u0, u1, [y0, y1], holes, mat="VH_AshlarRough" if rough else "VH_Ashlar",
                      key=("in", face), course_offset=ci, lmin=0.5, lmax=1.15, depth=0.062)


def linings(s):
    """Close the wall void at the openings: stone jambs and lintels from the inner skin to the outer reveals."""
    zi = ZF - 0.005
    # loading bay: stone jambs between the inner skin and the shutter reveal stones, a riveted steel lintel channel
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
    # closed doors: thin stone linings to the jamb stones, stone lintels
    for (x0, x1, top), (za, zb), lz in (((DOOR_F[0], DOOR_F[1], DOOR_F[2]), (ZF - 0.005, -0.385), (ZF - 0.04, -0.38)),
                                        ((DOOR_R[0], DOOR_R[1], DOOR_R[2]), (-6.515, ZR + 0.005), (-6.52, ZR + 0.04))):
        for (a, b) in ((x0 - 0.1, x0), (x1, x1 + 0.1)):
            ys = [c for c in COURSES if c < top] + [top]
            for (y0, y1) in zip(ys, ys[1:]):
                stone(s, s.imas, (a + 0.003, y0 + 0.004, min(za, zb)), (b - 0.003, y1 - 0.004, max(za, zb)), bevel=0.008)
        stone(s, s.imas, (x0 - 0.14 + 0.004, top + 0.004, min(lz)), (x1 + 0.14 - 0.004, top + 0.42 - 0.004, max(lz)), bevel=0.014)
        # threshold slab
        stone(s, s.ifloor, (x0, BASE - 0.1, min(za, zb)), (x1, BASE + 0.012, max(za, zb)), "VH_PodiumSlab", bevel=0.006, rough=True)


FX = XI + 0.06              # the flags run on under the inner skin (no slit at the wall foot)
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
    # under the bay, out to the shutter's threshold slab
    x = BAY[0] + BAY_REVEAL
    while x < BAY[1] - BAY_REVEAL - 1e-3:
        x1 = min(BAY[1] - BAY_REVEAL, x + L.uniform(0.8, 1.2))
        bid = f.new_block(tint=stone_tint("rough"), erode=0.012)
        vs, made = box(f, (x + 0.004, BASE - 0.1, FZ1 + 0.004), (x1 - 0.004, BASE, -0.344), "VH_PodiumSlab", bid, skip=("bottom",))
        eroded_bevel(f, list(made["top"].edges), 0.01, 2, seg_len=0.2)
        x = x1
    # checker plate where heavy salvage is dropped and dragged to the bench, and a drain in front of the bay
    m = s.imetal
    box(m, (-2.55, BASE - 0.002, -5.55), (-0.05, BASE + 0.012, -4.55), "VH_Steel")
    rr = drng("checker")
    for i in range(46):
        x, zz = rr.uniform(-2.5, -0.1), rr.uniform(-5.5, -4.6)
        a = rr.choice((0.785, -0.785))
        dx, dz = 0.03 * math.cos(a), 0.03 * math.sin(a)
        m.cyl((x - dx, BASE + 0.012, zz - dz), (x + dx, BASE + 0.012, zz + dz), 0.005, "VH_Steel", 4)
    box(m, (-1.75, BASE - 0.004, -1.05), (-0.85, BASE + 0.004, -0.8), "VH_Dark")
    for k in range(10):
        x = lerp(-1.72, -0.88, k / 9)
        box(m, (x - 0.012, BASE - 0.004, -1.04), (x + 0.012, BASE + 0.006, -0.81), "VH_Steel")


def ceiling(s):
    m, w, d = s.imetal, s.iwood, s.ideck
    # steel beams along z, bearing plates on the front and rear walls
    for bx, mat in zip(BEAMS_X, ("VH_PaintedSteel", "WS_PaintYellow")):
        z0, z1 = ZR - 0.12, ZF + 0.12
        box(m, (bx - 0.08, CEIL - 0.018, z0), (bx + 0.08, CEIL, z1), mat)
        box(m, (bx - 0.08, CEIL - 0.3, z0), (bx + 0.08, CEIL - 0.282, z1), mat)
        box(m, (bx - 0.006, CEIL - 0.282, z0), (bx + 0.006, CEIL - 0.018, z1), mat)
        for zz, sgn in ((ZR, 1), (ZF, -1)):
            # padstone in the wall face and a steel bearing plate under the beam end
            za, zb = sorted((zz, zz + sgn * 0.06))
            pad_bottom = 4.0 if zz == ZF else CEIL - 0.62        # the front-wall ends bear over the bay and door lintels
            stone(s, s.imas, (bx - 0.22, pad_bottom, za), (bx + 0.22, CEIL - 0.322, zb), bevel=0.01)
            za, zb = sorted((zz, zz + sgn * 0.24))
            box(m, (bx - 0.12, CEIL - 0.322, za), (bx + 0.12, CEIL - 0.3, zb), "VH_Steel")
            # web stiffeners near the bearings
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
    # timber joists along x between walls and beams; ends sit in steel hangers on the beams
    spans = [(-XI, BEAMS_X[0] - 0.08), (BEAMS_X[0] + 0.08, BEAMS_X[1] - 0.08), (BEAMS_X[1] + 0.08, XI)]
    if s.lod == 0:
        z = ZF - 0.32
        k = 0
        while z > ZR + 0.15:
            for (a, b) in spans:
                rr = drng("joist", k, round(a, 2))
                bid = w.new_block(off=(rr.uniform(0, 8), rr.uniform(0, 8)), tint=(0.5, 0.5, 0.5))
                vs, made = box(w, (a, CEIL - 0.2 - rr.uniform(0.0, 0.006), z - 0.038), (b, CEIL, z + 0.038), "SS_Timber", bid)
                w.bevel_edges([e for e in made["bottom"].edges], 0.006, 1)
                # steel shoes where the joist meets a beam
                if a > -XI + 0.01:
                    box(m, (a, CEIL - 0.205, z - 0.042), (a + 0.05, CEIL - 0.02, z + 0.042), "VH_Steel")
                if b < XI - 0.01:
                    box(m, (b - 0.05, CEIL - 0.205, z - 0.042), (b, CEIL - 0.02, z + 0.042), "VH_Steel")
            z -= 0.55
            k += 1
    # board deck (planks along z; the post-build UV turn runs the grain along them)
    if s.lod == 0:
        x = -XI
        k = 0
        while x < XI - 1e-3:
            rr = drng("board", k)
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


def hoist(s):
    """Chain hoist on a trolley under the yellow beam, hook loaded at HOOK (the stripped droid hangs from it in Unity)."""
    m = s.imetal
    bx, hy, hz = HOOK
    y = CEIL - 0.3
    box(m, (bx - 0.1, y - 0.12, hz - 0.12), (bx + 0.1, y - 0.005, hz + 0.12), "VH_Steel")
    for sx in (-1, 1):
        for dz in (-0.07, 0.07):
            m.cyl((bx + sx * 0.02, y + 0.02, hz + dz), (bx + sx * 0.06, y + 0.02, hz + dz), 0.03, "VH_Steel", 10)
    top, bot = y - 0.16, y - 0.52
    m.cyl((bx, top, hz), (bx, bot, hz), 0.1, "WS_PaintYellow", 14)
    m.cyl((bx - 0.11, (top + bot) / 2, hz), (bx + 0.11, (top + bot) / 2, hz), 0.13, "VH_Steel", 16)

    def chain(x, z, ya, yb, r=0.011):
        if s.lod > 0:
            m.cyl((x, ya, z), (x, yb, z), r * 1.3, "VH_Steel", 6)
            return
        k, yy = 0, ya
        while yy > yb:
            l = 0.045
            if k % 2 == 0:
                box(m, (x - 0.004, yy - l, z - 0.016), (x + 0.004, yy, z + 0.016), "VH_Steel")
            else:
                box(m, (x - 0.016, yy - l, z - 0.004), (x + 0.016, yy, z + 0.004), "VH_Steel")
            yy -= l * 0.82
            k += 1
    chain(bx, hz, bot, hy + 0.2)
    chain(bx + 0.13, hz + 0.02, (top + bot) / 2, 1.55, 0.008)
    chain(bx + 0.16, hz - 0.03, (top + bot) / 2, 1.55, 0.008)
    box(m, (bx - 0.05, hy + 0.04, hz - 0.035), (bx + 0.05, hy + 0.2, hz + 0.035), "WS_PaintYellow")
    m.tube([(bx, hy + 0.04, hz), (bx, hy - 0.08, hz), (bx + 0.04, hy - 0.17, hz), (bx + 0.1, hy - 0.15, hz),
            (bx + 0.11, hy - 0.07, hz)], 0.018, "VH_Steel", 8)


def counter(s):
    """Trade counter: a steel frame clad in salvaged sheet panels (each a different old paint), timber top with a worn
    steel nosing on the customer side, recessed kick, a shelf on the dealer's side."""
    m, d = s.imetal, s.ideck
    c = COUNTER
    x0, x1, z0, z1, top = c["x0"], c["x1"], c["z0"], c["z1"], c["top"]
    box(m, (x0 + 0.06, BASE, z0 + 0.06), (x1 - 0.02, BASE + 0.1, z1 - 0.06), "VH_Dark")               # kick
    box(m, (x0 + 0.02, BASE + 0.1, z0 + 0.02), (x1 - 0.02, top - 0.04, z1 - 0.02), "VH_Dark", skip=("top",))
    # frame: corner posts, mid posts on the customer face, top and bottom rails
    posts_z = [z0, lerp(z0, z1, 0.25), lerp(z0, z1, 0.5), lerp(z0, z1, 0.75), z1]
    for i, pz in enumerate(posts_z):
        for px in (x0, x1) if i in (0, len(posts_z) - 1) else (x0,):
            box(m, (px - 0.02, BASE + 0.08, pz - 0.022), (px + 0.025, top - 0.04, pz + 0.022), "VH_Steel")
    for yy in (BASE + 0.1, top - 0.08):
        box(m, (x0 - 0.02, yy, z0), (x0 + 0.02, yy + 0.04, z1), "VH_Steel")
    # customer-face panels: four bays of salvaged sheet, slightly proud, each riveted round its edge
    mats = ("WS_PaintOlive", "WS_CladTeal", "WS_ContainerRust", "WS_PaintOlive")
    for i, (a, b) in enumerate(zip(posts_z, posts_z[1:])):
        rr = drng("cpanel", i)
        box(m, (x0 - 0.012 - rr.uniform(0, 0.004), BASE + 0.14, a + 0.03), (x0 + 0.004, top - 0.085, b - 0.03), mats[i])
        if s.lod == 0:
            for yy in (BASE + 0.17, top - 0.11):
                zz = a + 0.07
                while zz < b - 0.05:
                    m.sphere((x0 - 0.014, yy, zz), 0.006, "VH_Steel", 6, hemi_axis=(-1, 0, 0))
                    zz += 0.16
    # end panels (the south end faces the bay as you walk in)
    for zz, sgn in ((z1, 1), (z0, -1)):
        box(m, (x0 + 0.03, BASE + 0.14, min(zz, zz + 0.012 * sgn)), (x1 - 0.03, top - 0.085, max(zz, zz + 0.012 * sgn)), "WS_PaintOlive")
    # top: timber slab, steel nosing on the customer edge, a cut-out hatch strip at the north end
    box(d, (x0 - 0.07, top, z0 - 0.06), (x1 + 0.05, top + 0.055, z1 + 0.06), "SS_Timber")
    box(m, (x0 - 0.085, top - 0.012, z0 - 0.06), (x0 - 0.065, top + 0.062, z1 + 0.06), "VH_Steel")
    box(m, (x0 - 0.065, top + 0.055, z0 - 0.06), (x0 + 0.03, top + 0.062, z1 + 0.06), "VH_Steel")
    # dealer's side: open shelf under the top
    box(m, (x0 + 0.12, BASE + 0.42, z0 + 0.08), (x1 - 0.01, BASE + 0.445, z1 - 0.08), "VH_Steel")


def services(s):
    m = s.imetal
    zr = ZR + 0.06
    xe = XI - 0.06
    yc = 3.85
    # main run along the rear wall, a drop to the bench and to the breaker panel; a run along the east wall with a drop
    # behind the counter
    m.tube([(-XI + 0.1, yc, zr), (xe, yc, zr)], 0.024, "VH_Steel", clamps=0.7)
    m.tube([(xe, yc, zr - 0.0), (xe, yc, ZF - 0.25)], 0.024, "VH_Steel", clamps=0.7)
    m.tube([(-1.3, yc, zr), (-1.3, 2.45, zr)], 0.022, "VH_Steel", clamps=0.6)
    box(m, (-1.45, 2.15, ZR), (-1.15, 2.45, ZR + 0.12), "VH_PaintedSteel")
    m.tube([(2.6, yc, zr), (2.6, 2.3, zr)], 0.024, "VH_Steel", clamps=0.6)
    box(m, (2.25, 1.35, ZR), (2.95, 2.3, ZR + 0.16), "VH_PaintedSteel")                      # breaker panel
    box(m, (2.28, 1.38, ZR + 0.16), (2.92, 2.27, ZR + 0.175), "WS_PaintOchre")              # its door
    box(m, (2.84, 1.75, ZR + 0.175), (2.88, 1.92, ZR + 0.2), "VH_Steel")                    # latch
    m.tube([(xe, yc, -2.75), (xe, 1.6, -2.75)], 0.02, "VH_Steel", clamps=0.6)
    box(m, (XI - 0.11, 1.4, -2.88), (XI, 1.6, -2.62), "VH_PaintedSteel")                     # switch box
    # cable down from the beam to the hoist pendant control
    m.cyl((HOOK[0] + 0.15, CEIL - 0.6, HOOK[2]), (HOOK[0] + 0.15, 1.55, HOOK[2]), 0.006, "VH_Rubber", 6)
    box(m, (HOOK[0] + 0.1, 1.3, HOOK[2] - 0.04), (HOOK[0] + 0.2, 1.55, HOOK[2] + 0.04), "WS_PaintYellow")


def lamps(s):
    """Enamel pendant shades on cords from the joists, warm bulbs (InteriorGlow; the lights are added in Unity)."""
    m, g = s.imetal, s.iglow
    for name, (x, y, z) in LAMPS:
        m.cyl((x, CEIL - 0.2, z), (x, y + 0.16, z), 0.005, "VH_Rubber", 6)
        m.cyl((x, CEIL - 0.21, z), (x, CEIL - 0.19, z), 0.045, "VH_Steel", 10)          # rose
        m.cyl((x, y + 0.16, z), (x, y + 0.08, z), 0.03, "VH_Steel", 10)                  # lampholder
        seg = 18 if s.lod == 0 else 10
        # dome shade: a flared cone, enamel outside, white inside (two shells so both read)
        m.cyl((x, y + 0.1, z), (x, y - 0.06, z), 0.06, "WS_PaintOlive", seg, cap=False, r2=0.24)
        inner = m.cyl((x, y + 0.095, z), (x, y - 0.055, z), 0.055, "SS_Enamel", seg, cap=False, r2=0.232)
        bmesh.ops.reverse_faces(m.bm, faces=inner)          # seen from below: the white inside of the shade
        g.sphere((x, y - 0.0, z), 0.05, "SS_BulbWarm", 10 if s.lod == 0 else 6)


# ---------------------------------------------------------------------------------------------------------- colliders
def colliders(s):
    c = s.rec["colliders"]
    top = s.top_y
    X, Z0, Z1 = HW + 0.09, -D - 0.09, 0.09

    def add(name, lo, hi):
        c.append({"name": name, "center": [round((a + b) / 2, 4) for a, b in zip(lo, hi)],
                  "size": [round(b - a, 4) for a, b in zip(lo, hi)]})
    add("COL_WallWest", (-X, BASE, Z0), (-XI, CEIL, Z1))
    add("COL_WallEast", (XI, BASE, Z0), (X, CEIL, Z1))
    add("COL_WallRear", (-XI, BASE, Z0), (XI, CEIL, ZR))
    add("COL_FrontPier_bay_north", (-XI, BASE, ZF), (BAY[0], CEIL, Z1))
    add("COL_FrontPier_bay_south", (BAY[1], BASE, ZF), (DOOR_F[0], CEIL, Z1))
    add("COL_FrontPier_door_south", (DOOR_F[1], BASE, ZF), (XI, CEIL, Z1))
    add("COL_OverBay", (BAY[0], BAY[2], ZF), (BAY[1], CEIL, Z1))
    add("COL_ShutterBox", (BAY[0], BAY[2] - 0.44, -0.31), (BAY[1], BAY[2], -0.05))
    add("COL_OverDoor_1.48", (DOOR_F[0], DOOR_F[2], ZF), (DOOR_F[1], CEIL, Z1))
    add("COL_Door_1.48", (DOOR_F[0], BASE, ZF), (DOOR_F[1], DOOR_F[2], -0.34))
    add("COL_Upper", (-X, CEIL, Z0), (X, top, Z1))
    add("COL_Floor", (-XI, BASE - 0.12, ZR), (XI, BASE, -0.34))
    k = COUNTER
    add("COL_Counter", (k["x0"] - 0.085, BASE, k["z0"] - 0.06), (k["x1"] + 0.05, k["top"] + 0.062, k["z1"] + 0.06))
