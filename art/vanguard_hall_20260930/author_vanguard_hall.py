"""Vanguard Hall rebuild: authored civic hall, Blender 5.2 headless (30 September 2026).

Accepted target: concept/vanguard-hall-concept-a.png ("yes this!", Carl, 30 Sep 2026).

Run:  blender -b --python-exit-code 1 -P author_vanguard_hall.py

Coordinates are written in Unity metres, local to the hall root: X east, Y up, Z north (the facade faces +Z,
towards the plaza). Origin = front wall face centre at paving level; the root is installed at world
(-10, 0, -26.55). U() converts to Blender; the glTF export (+Y up) and glTFast import map Blender (x, y, z)
back to Unity (-x, z, -y). Text and the banner are built directly in Blender space so they read correctly.

Construction: individually modelled ashlar blocks (bevelled, occasional chipped arrises, per-block tint and
occlusion in vertex colour for the Athen Hill/Masonry Lit shader) on a recessed mortar backing, battered corner
piers, a deep portal with riveted steel doors, barred upper windows, a supported entablature and cornice,
parapet and attic, steel repairs, conduit, drainage, a rooftop comms mast and a woven banner.
UVs are metre box projections (1 UV unit = 1 m, per-block random offset); Unity tiling = 1 / texture size.

Outputs (unity/AthenHill/Assets/AthenHill/Art/VanguardHall/Models):
  VanguardHall_LOD0.glb, VanguardHall_LOD1.glb, vanguard-hall.json (colliders, mounts, report)
and art/vanguard_hall_20260930/vanguard-hall-source.blend (LOD0 + LOD1 collections).
"""
import bpy, bmesh, json, math, random, sys
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.noise import noise as pnoise

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "art/ward_masonry_kit"))
import ward_masonry as WM
from ward_masonry import (Part, Frame, stone_tint, ashlar_block, course_intervals, fill_wall, sweep, triangulate, material,
                          eroded_bevel, split_edge, block_wear, finalize_parts, AOBaker, DripSet, U, lerp, smoothstep, drng,
                          ScarSet, scatter_impacts)
OUT = ROOT / "unity/AthenHill/Assets/AthenHill/Art/VanguardHall/Models"
FONT = HERE / "fonts/NotoSerifDisplay-Bold.ttf"
OUT.mkdir(parents=True, exist_ok=True)

LOD = 0          # set per build pass
LAYOUT = None    # layout RNG (identical sequence in every LOD)






# ================================================================ dimensions (Unity local metres)
BASE = 0.5                     # podium top
WX = 5.0                       # side wall faces at x = +-5.0
ZF, ZB = 0.0, -8.5             # front / rear wall faces
PIER_W0, PIER_W1 = 2.1, 1.5    # pier width at base / top (square)
PIER_PROJ0, PIER_PROJ1 = 0.8, 0.5
PIER_TOP = 10.4
ENT_X, ENT_ZF, ENT_ZB = 5.5, 0.5, -9.0      # entablature rectangle
POD_X, POD_ZF, POD_ZB = 5.94, 2.25, -9.5    # podium

GROUND = [1.10, 1.58, 2.01, 2.49, 2.92, 3.40, 3.83, 4.31, 4.74, 5.22, 5.65, 6.10]
UPPER = [6.35 + 0.45 * i for i in range(10)]          # 6.35 .. 10.40
COURSES = [BASE] + GROUND + UPPER                     # plinth course 0.5-1.1, string band 6.1-6.35


def pier_t(y):
    return max(0.0, min(1.0, (y - BASE) / (PIER_TOP - BASE)))


def pier_proj(y):
    return lerp(PIER_PROJ0, PIER_PROJ1, pier_t(y))


def pier_w(y):
    return lerp(PIER_W0, PIER_W1, pier_t(y))


def pier_inner_x(y):
    """|x| of the front/rear pier face that meets the facade (the facade runs between +-this)."""
    return WX + pier_proj(y) - pier_w(y)


def pier_side_front(y):
    """z of the front pier's back face on the side walls (side wall runs from here towards the rear)."""
    return ZF + pier_proj(y) - pier_w(y)


def pier_side_rear(y):
    return ZB - pier_proj(y) + pier_w(y)


# geometry helpers live in the shared Ward masonry kit (art/ward_masonry_kit/ward_masonry.py)

# ================================================================ the building
def build(lod):
    global LOD, LAYOUT
    LOD = lod
    LAYOUT = random.Random(20260930)
    WM.set_state(lod, LAYOUT, "vh")
    WM.WEAR["ground_y"] = BASE
    WM.reset_materials()
    coll = bpy.data.collections.new(f"LOD{lod}")
    bpy.context.scene.collection.children.link(coll)
    rec = {"colliders": [], "mounts": [], "notes": []}

    mas = Part(f"VH_Masonry_LOD{lod}")      # walls, piers, frieze, parapet (Masonry Lit)
    trim = Part(f"VH_Trim_LOD{lod}")        # sweeps: plinth course, string course, cornice, coping, sills, lintels
    pod = Part(f"VH_Podium_LOD{lod}")       # podium, steps, slabs
    metal = Part(f"VH_Metal_LOD{lod}", wear=False)      # doors, frames, bars, brackets, plates, conduit
    glass = Part(f"VH_Glass_LOD{lod}", wear=False)      # window glazing (interior-mapped in Unity)
    roof = Part(f"VH_Roof_LOD{lod}", wear=False)        # roof deck, hatch, vents, mast
    sand = Part(f"VH_Sand_LOD{lod}", wear=False)        # sheltered sand drifts (LOD0 only)
    # runoff / rust sources on the vertical faces (Masonry Lit UV1/UV2); base runoff grows towards the parapet
    drips = DripSet(base=0.22, base_top=11.2, ground_y=BASE)

    # ------------------------------------------------ frames
    FRONT = Frame((0, 0, ZF), (1, 0, 0), (0, 0, 1))
    REAR = Frame((0, 0, ZB), (-1, 0, 0), (0, 0, -1))
    EAST = Frame((WX, 0, 0), (0, 0, -1), (1, 0, 0))    # u runs towards the rear (z = -u)
    WEST = Frame((-WX, 0, 0), (0, 0, 1), (-1, 0, 0))   # u = z

    # ------------------------------------------------ openings (course aligned)
    PORTAL_HW = 1.45
    ARCH_HW = 2.05
    front_holes = [(-ARCH_HW, ARCH_HW, BASE, 4.31), (-2.35, 2.35, 4.31, 5.22)]
    gwin = [(-3.45, -2.85), (2.85, 3.45)]
    for a, b in gwin:
        front_holes += [(a, b, 2.01, 3.40), (a - 0.15, b + 0.15, 3.40, 3.83)]
    uwin = [(-3.4, -2.4), (-1.8, -0.8), (0.8, 1.8), (2.4, 3.4)]
    for a, b in uwin:
        front_holes += [(a, b, 6.80, 9.50), (a - 0.15, b + 0.15, 9.50, 9.95)]

    side_u = [(2.6, 3.5), (5.0, 5.9)]           # side window spans (u = distance behind the front wall)
    side_holes = []
    for a, b in side_u:
        side_holes += [(a, b, 6.80, 9.50), (a - 0.15, b + 0.15, 9.50, 9.95)]
        c = (a + b) / 2
        side_holes += [(c - 0.35, c + 0.35, 2.01, 3.40), (c - 0.5, c + 0.5, 3.40, 3.83)]

    # rear: u axis is -x (u = -x); door at x 1.2..2.3 -> u -2.3..-1.2 ; windows at x +-1.5
    rear_door = (-2.3, -1.2)
    rear_holes = [(rear_door[0], rear_door[1], BASE, 2.92), (rear_door[0] - 0.15, rear_door[1] + 0.15, 2.92, 3.40)]
    rear_win_open = (-2.0, -1.0)     # x = 1.0..2.0 (east) open window
    rear_win_infill = (1.0, 2.0)     # x = -2.0..-1.0 (west) bricked-up window
    for a, b in (rear_win_open, rear_win_infill):
        rear_holes += [(a, b, 6.80, 9.50), (a - 0.15, b + 0.15, 9.50, 9.95)]

    # ------------------------------------------------ walls
    def front_limit(y0, y1):
        x = pier_inner_x(y1) + 0.06
        return (-x, x)

    def side_limit(y0, y1):
        return (-pier_side_front(y1) - 0.06, -pier_side_rear(y1) + 0.06)

    def wall_ao(p, n):
        a = lerp(0.72, 1.0, smoothstep(BASE, 1.9, p.y))
        if p.y < PIER_TOP:
            a *= 1.0 - 0.22 * smoothstep(8.8, PIER_TOP, p.y)
        return a

    fill_wall(mas, FRONT, 0, 0, COURSES[1:13], front_holes, ulimit=front_limit, key="front")
    fill_wall(mas, FRONT, 0, 0, COURSES[13:], front_holes, ulimit=front_limit, key="front_up")
    fill_wall(mas, REAR, 0, 0, COURSES[1:13], rear_holes, ulimit=front_limit, key="rear")
    fill_wall(mas, REAR, 0, 0, COURSES[13:], rear_holes, ulimit=front_limit, key="rear_up")
    fill_wall(mas, EAST, 0, 0, COURSES[1:13], side_holes, ulimit=side_limit, key="east")
    fill_wall(mas, EAST, 0, 0, COURSES[13:], side_holes, ulimit=side_limit, key="east_up")
    fill_wall(mas, WEST, 0, 0, COURSES[1:13], [(-b, -a, y0, y1) for a, b, y0, y1 in side_holes],
              ulimit=lambda y0, y1: (lambda l: (-l[1], -l[0]))(side_limit(y0, y1)), key="west")
    fill_wall(mas, WEST, 0, 0, COURSES[13:], [(-b, -a, y0, y1) for a, b, y0, y1 in side_holes],
              ulimit=lambda y0, y1: (lambda l: (-l[1], -l[0]))(side_limit(y0, y1)), key="west_up")

    # string band 6.10-6.35: plain wall behind the projecting string course (hidden mostly)
    for F, lim in ((FRONT, front_limit), (REAR, front_limit)):
        a, b = lim(6.1, 6.35)
        F.box(mas, a, b, 6.1, 6.35, 0.0, 0.05, "VH_Mortar", skip=("s0", "bottom", "top"))
    for F, sgn in ((EAST, 1), (WEST, -1)):
        a, b = side_limit(6.1, 6.35)
        if sgn < 0:
            a, b = -b, -a
        F.box(mas, a, b, 6.1, 6.35, 0.0, 0.05, "VH_Mortar", skip=("s0", "bottom", "top"))

    # rear bricked-up window: rough infill recessed 4 cm, smaller rubble courses
    a, b = rear_win_infill
    ys = [6.80 + i * (2.70 / 8) for i in range(9)]
    for ci, (y0, y1) in enumerate(zip(ys, ys[1:])):
        u = a
        while u < b - 1e-3:
            ln = LAYOUT.uniform(0.28, 0.48)
            if b - (u + ln) < 0.15:
                ln = b - u
            ashlar_block(mas, REAR, u + 0.006, u + ln - 0.006, y0 + 0.006, y1 - 0.006, mat="VH_AshlarRough",
                         depth=0.02, back=-0.01, bevel=(0.012, 0.025), key=("infill", ci, round(u, 3)),
                         tint=tuple(c * 0.93 for c in stone_tint("rough")), chip=0.3, face_jitter=0.008)
            u += ln
    REAR.box(mas, a, b, 6.80, 9.50, -0.02, 0.005, "VH_Mortar", skip=("s0", "bottom", "top"))

    # ------------------------------------------------ piers (battered, 4 corners)
    pier_courses = COURSES[:]  # 0.5 .. 10.4
    for cx in (-1, 1):
        for cz in (1, -1):          # +1 front piers, -1 rear piers
            for ci, (y0, y1) in enumerate(zip(pier_courses, pier_courses[1:])):
                def ring(y, grow=0.0):
                    w, pr = pier_w(y), pier_proj(y)
                    xo = WX + pr + grow
                    xi = xo - w - 2 * grow
                    if cz > 0:
                        zo = ZF + pr + grow
                        zi = zo - w - 2 * grow
                    else:
                        zo = ZB - pr - grow
                        zi = zo + w + 2 * grow
                    return (xi * cx, xo * cx, zi, zo)
                grow = 0.07 if ci == 0 else 0.0
                j = 0.0045
                ra, rb = ring(y0, grow), ring(y1, grow if ci > 0 else 0.0)
                # split the ring into a 2x2 of blocks, split position alternating by course
                s = 0.42 if ci % 2 == 0 else 0.58
                xs0 = [ra[0], lerp(ra[0], ra[1], s), ra[1]]
                xs1 = [rb[0], lerp(rb[0], rb[1], s), rb[1]]
                s2 = 0.58 if ci % 2 == 0 else 0.42
                zs0 = [ra[2], lerp(ra[2], ra[3], s2), ra[3]]
                zs1 = [rb[2], lerp(rb[2], rb[3], s2), rb[3]]
                for ix in range(2):
                    for iz in range(2):
                        def c4(xs, zs, y):
                            x0, x1 = sorted((xs[ix], xs[ix + 1]))
                            z0, z1 = sorted((zs[iz], zs[iz + 1]))
                            return [(x0 + j, y, z0 + j), (x1 - j, y, z0 + j), (x1 - j, y, z1 - j), (x0 + j, y, z1 - j)]
                        bot = c4(xs0, zs0, y0 + j)
                        top = c4(xs1, zs1, y1 - j)
                        mat = "VH_AshlarRough" if ci == 0 else "VH_Ashlar"
                        bid = mas.new_block(tint=stone_tint("rough" if ci == 0 else "ashlar"),
                                            erode=(0.006 + 0.01 * block_wear(y0)) * (1.4 if ci == 0 else 1.0))
                        rr = drng("pier", cx, cz, ci, ix, iz)
                        if LOD == 0 and rr.random() < 0.18:
                            k = rr.randrange(4)
                            top[k] = tuple(Vector(top[k]) + Vector((rr.uniform(-.03, .03), -rr.uniform(.01, .035), rr.uniform(-.03, .03))))
                        vs, made = mas.hexa(bot + top, mat, bid)
                        # bevel all edges except those buried in neighbours: bevel only the outer vertical arris +
                        # the top/bottom outer edges
                        outer = [e for e in {e for f in made.values() for e in f.edges}
                                 if all(abs(v.co.x) > WX - 0.02 or (cz > 0 and v.co.z > ZF - 0.02) or (cz < 0 and v.co.z < ZB + 0.02)
                                        for v in e.verts)]
                        eroded_bevel(mas, outer, LAYOUT.uniform(0.012, 0.024) + (0.04 if ci == 0 else 0), 2,
                                     seg_len=0.15 if y0 < 3.2 else 0.32)
                # mortar core (visible in the joints)
                core_a, core_b = ring(y0, grow - 0.045), ring(y1, (grow if ci > 0 else 0.0) - 0.045)
                x0a, x1a = sorted(core_a[:2]); z0a, z1a = sorted(core_a[2:])
                x0b, x1b = sorted(core_b[:2]); z0b, z1b = sorted(core_b[2:])
                mas.hexa([(x0a, y0, z0a), (x1a, y0, z0a), (x1a, y0, z1a), (x0a, y0, z1a),
                          (x0b, y1, z0b), (x1b, y1, z0b), (x1b, y1, z1b), (x0b, y1, z1b)], "VH_Mortar",
                         skip=("bottom", "top"))

    # ------------------------------------------------ entablature: corner capitals + frieze + soffit
    ent_courses = [PIER_TOP, 10.8, 11.2]
    for cx in (-1, 1):
        for cz in (1, -1):
            xo = ENT_X * cx
            xi = (ENT_X - PIER_W1 - 0.1) * cx
            zo = ENT_ZF if cz > 0 else ENT_ZB
            zi = zo - (PIER_W1 + 0.1) * cz
            x0, x1 = sorted((xi, xo)); z0, z1 = sorted((zi, zo))
            for ci, (y0, y1) in enumerate(zip(ent_courses, ent_courses[1:])):
                bid = mas.new_block(tint=stone_tint())
                vs, made = mas.box((x0 + .005, y0 + .005, z0 + .005), (x1 - .005, y1 - .005, z1 - .005), "VH_Ashlar", bid)
                mas.bevel_edges(list({e for f in made.values() for e in f.edges}), LAYOUT.uniform(0.012, 0.022), 2)
    # frieze runs between capitals on each face; full-depth blocks (their undersides form the soffit)
    EF = Frame((0, 0, ENT_ZF), (1, 0, 0), (0, 0, 1))
    ER = Frame((0, 0, ENT_ZB), (-1, 0, 0), (0, 0, -1))
    EE = Frame((ENT_X, 0, 0), (0, 0, -1), (1, 0, 0))
    EW = Frame((-ENT_X, 0, 0), (0, 0, 1), (-1, 0, 0))
    span_x = ENT_X - PIER_W1 - 0.1
    for F, (ua, ub), soffit_depth in ((EF, (-span_x, span_x), ENT_ZF - ZF), (ER, (-span_x, span_x), ZB - ENT_ZB),
                                      (EE, (-ENT_ZF + PIER_W1 + 0.1, -ENT_ZB - PIER_W1 - 0.1), ENT_X - WX),
                                      (EW, (ENT_ZB + PIER_W1 + 0.1, ENT_ZF - PIER_W1 - 0.1), ENT_X - WX)):
        for ci, (y0, y1) in enumerate(zip(ent_courses, ent_courses[1:])):
            u = ua
            while u < ub - 1e-3:
                ln = LAYOUT.uniform(0.9, 1.5)
                if ci % 2 and u == ua:
                    ln *= 0.55
                if ub - (u + ln) < 0.45:
                    ln = ub - u
                bid = mas.new_block(tint=stone_tint(), ao=0.92 if ci == 0 else 1.0)
                back = -soffit_depth - 0.05
                c = [F.P(u + .005, y0 + .005, back), F.P(u + ln - .005, y0 + .005, back), F.P(u + ln - .005, y0 + .005, 0.0), F.P(u + .005, y0 + .005, 0.0),
                     F.P(u + .005, y1 - .005, back), F.P(u + ln - .005, y1 - .005, back), F.P(u + ln - .005, y1 - .005, 0.0), F.P(u + .005, y1 - .005, 0.0)]
                vs, made = mas.hexa(c, "VH_Ashlar", bid, skip=("s0",) + (() if ci == 0 else ("bottom",)) + ("top",))
                edges = list(made["s2"].edges) + (list(made["bottom"].edges) if ci == 0 else [])
                mas.bevel_edges(edges, LAYOUT.uniform(0.012, 0.022), 2)
                u += ln
            F.box(mas, ua, ub, y0, y1, -0.03, -0.012, "VH_Mortar", skip=("s0", "top", "bottom"))

    # ------------------------------------------------ sweeps (plinth course, string courses, cornice, copings)

    PX = ENT_X
    rect = [(-PX, ENT_ZF), (PX, ENT_ZF), (PX, ENT_ZB), (-PX, ENT_ZB)]
    # Unity: from (-X, front) to (+X, front) travelling east along the front; right-hand of travel = +Z? (see nrm)
    cornice = [(-0.02, 11.2), (0.06, 11.2), (0.06, 11.27), (0.10, 11.30), (0.17, 11.36), (0.25, 11.43), (0.33, 11.52),
               (0.38, 11.58), (0.42, 11.60), (0.42, 11.63), (0.50, 11.63), (0.50, 11.80), (-0.10, 11.80)]
    sweep(trim, rect, True, cornice, "VH_Ashlar", seg=1.4, key="cornice")

    # plinth course along each wall (open paths between piers / openings), profile with chamfered top
    plinth = [(-0.06, BASE), (0.14, BASE), (0.14, 0.96), (0.05, 1.10), (-0.06, 1.10)]
    xin = pier_inner_x(0.8) + 0.02
    sweep(trim, [(-xin, 0.0), (-ARCH_HW, 0.0)], False, plinth, "VH_AshlarRough", seg=1.1, key="plinth_f0")
    sweep(trim, [(ARCH_HW, 0.0), (xin, 0.0)], False, plinth, "VH_AshlarRough", seg=1.1, key="plinth_f1")
    sweep(trim, [(xin, ZB), (2.3, ZB)], False, plinth, "VH_AshlarRough", seg=1.1, key="plinth_r0")
    sweep(trim, [(1.2, ZB), (-xin, ZB)], False, plinth, "VH_AshlarRough", seg=1.1, key="plinth_r1")
    zf_, zr_ = pier_side_front(0.8) - 0.02, pier_side_rear(0.8) + 0.02
    sweep(trim, [(WX, zf_), (WX, zr_)], False, plinth, "VH_AshlarRough", seg=1.1, key="plinth_e")
    sweep(trim, [(-WX, zr_), (-WX, zf_)], False, plinth, "VH_AshlarRough", seg=1.1, key="plinth_w")

    # string course 6.10-6.35 between piers
    string = [(-0.05, 6.10), (0.07, 6.10), (0.07, 6.14), (0.12, 6.19), (0.12, 6.35), (-0.05, 6.35)]
    xs = pier_inner_x(6.2) + 0.02
    sweep(trim, [(-xs, 0.0), (xs, 0.0)], False, string, "VH_Ashlar", seg=1.3, key="string_f")
    sweep(trim, [(xs, ZB), (-xs, ZB)], False, string, "VH_Ashlar", seg=1.3, key="string_r")
    zf_, zr_ = pier_side_front(6.2) - 0.02, pier_side_rear(6.2) + 0.02
    sweep(trim, [(WX, zf_), (WX, zr_)], False, string, "VH_Ashlar", seg=1.3, key="string_e")
    sweep(trim, [(-WX, zr_), (-WX, zf_)], False, string, "VH_Ashlar", seg=1.3, key="string_w")

    # ------------------------------------------------ parapet, corner caps, attic, copings
    PPX, PZF, PZB = 5.4, 0.4, -8.9
    par_courses = [11.8, 12.25, 12.7]
    cap_w = PIER_W1
    # corner caps over the piers (raised)
    for cx in (-1, 1):
        for cz in (1, -1):
            x0, x1 = sorted((cx * (PPX - cap_w + 0.05), cx * (PPX + 0.02)))
            zo = PZF + 0.02 if cz > 0 else PZB - 0.02
            z0, z1 = sorted((zo, zo - cz * (cap_w - 0.05)))
            for ci, (y0, y1) in enumerate(((11.8, 12.4), (12.4, 12.95))):
                bid = mas.new_block(tint=stone_tint())
                vs, made = mas.box((x0 + .005, y0 + .005, z0 + .005), (x1 - .005, y1 - .005, z1 - .005), "VH_Ashlar", bid)
                mas.bevel_edges(list({e for f in made.values() for e in f.edges}), LAYOUT.uniform(0.012, 0.02), 2)
            # cap stone
            bid = mas.new_block(tint=stone_tint())
            vs, made = mas.box((x0 - .06, 12.95, z0 - .06), (x1 + .06, 13.12, z1 + .06), "VH_Ashlar", bid)
            mas.bevel_edges(list({e for f in made.values() for e in f.edges}), 0.02, 2)
    # parapet walls between caps (outer face ashlar, inner face plain)
    span = PPX - cap_w + 0.05
    PF = Frame((0, 0, PZF), (1, 0, 0), (0, 0, 1))
    PR = Frame((0, 0, PZB), (-1, 0, 0), (0, 0, -1))
    PE = Frame((PPX, 0, 0), (0, 0, -1), (1, 0, 0))
    PW = Frame((-PPX, 0, 0), (0, 0, 1), (-1, 0, 0))
    attic_hw = 2.4
    fill_wall(mas, PF, -span, span, par_courses, [(-attic_hw, attic_hw, 11.8, 13.6)], key="par_f", lmin=0.8, lmax=1.4)
    fill_wall(mas, PR, -span, span, par_courses, [], key="par_r", lmin=0.8, lmax=1.4)
    zspan = (-(PZF - cap_w + 0.05), -(PZB + cap_w - 0.05))
    fill_wall(mas, PE, zspan[0], zspan[1], par_courses, [], key="par_e", lmin=0.8, lmax=1.4)
    fill_wall(mas, PW, -zspan[1], -zspan[0], par_courses, [], key="par_w", lmin=0.8, lmax=1.4)
    # inner faces (roof side) as plain mortar-rendered walls
    for F, (ua, ub) in ((PF, (-span, span)), (PR, (-span, span)), (PE, zspan), (PW, (-zspan[1], -zspan[0]))):
        F.box(mas, ua, ub, 11.8, 12.7, -0.45, 0.04, "VH_Mortar", skip=("s2",))
    # attic on the front parapet
    attic_courses = [11.8, 12.25, 12.7, 13.1, 13.5]
    fill_wall(mas, PF, -attic_hw, attic_hw, attic_courses, [], key="attic", lmin=0.9, lmax=1.5)
    PF.box(mas, -attic_hw, attic_hw, 11.8, 13.5, -0.7, 0.04, "VH_Mortar", skip=("s2",))
    for F in (Frame((attic_hw, 0, PZF), (0, 0, -1), (1, 0, 0)), Frame((-attic_hw, 0, PZF), (0, 0, 1), (-1, 0, 0))):
        F.box(mas, -0.7 if F.u.z > 0 else 0.0, 0.0 if F.u.z > 0 else 0.7, 12.7, 13.5, -0.02, 0.05, "VH_Ashlar",
              bid=mas.new_block(tint=stone_tint()))
    # copings
    cop = [(-0.62, 12.70), (0.06, 12.70), (0.06, 12.78), (0.02, 12.85), (-0.58, 12.85), (-0.62, 12.78)]
    sweep(trim, [(-span, PZF), (-attic_hw - 0.02, PZF)], False, cop, "VH_Ashlar", seg=1.2, key="cop_f0")
    sweep(trim, [(attic_hw + 0.02, PZF), (span, PZF)], False, cop, "VH_Ashlar", seg=1.2, key="cop_f1")
    sweep(trim, [(span, PZB), (-span, PZB)], False, cop, "VH_Ashlar", seg=1.2, key="cop_r")
    sweep(trim, [(PPX, PZF - cap_w + 0.05), (PPX, PZB + cap_w - 0.05)], False, cop, "VH_Ashlar", seg=1.2, key="cop_e")
    sweep(trim, [(-PPX, PZB + cap_w - 0.05), (-PPX, PZF - cap_w + 0.05)], False, cop, "VH_Ashlar", seg=1.2, key="cop_w")
    acop = [(-0.78, 13.50), (0.08, 13.50), (0.08, 13.58), (0.03, 13.66), (-0.73, 13.66), (-0.78, 13.58)]
    sweep(trim, [(-attic_hw - 0.06, PZF), (attic_hw + 0.06, PZF)], False, acop, "VH_Ashlar", seg=1.25, key="cop_attic")

    # ------------------------------------------------ roof deck
    roof.box((-PPX + 0.4, 11.78, PZB + 0.4), (PPX - 0.4, 11.86, PZF - 0.45), "VH_Roof")
    # ------------------------------------------------ portal: architrave jambs, flat-arch lintel, reveals, hood
    jamb_y = [BASE, 1.10, 2.01, 2.92, 3.83, 4.31]
    for side in (-1, 1):
        for ci, (y0, y1) in enumerate(zip(jamb_y, jamb_y[1:])):
            wide = ci % 2 == 0
            u0, u1 = (PORTAL_HW, ARCH_HW + (0.12 if wide else 0.0))
            x0, x1 = sorted((side * u0, side * u1))
            # jamb stone: face projects 0.12, return lines the reveal to the door plane
            bid = trim.new_block(tint=stone_tint())
            vs, made = trim.box((x0 + .004, y0 + .005, -0.95), (x1 - .004, y1 - .005, 0.12 + (0.02 if wide else 0)), "VH_Ashlar", bid,
                                skip=("s0",))
            trim.bevel_edges([e for e in {e for f in made.values() for e in f.edges} if max(v.co.z for v in e.verts) > -0.9],
                             LAYOUT.uniform(0.014, 0.024), 2)
    # flat arch: 5 voussoirs + key, courses 4.31..5.22
    vx = [-2.35, -1.5, -0.8, -0.28, 0.28, 0.8, 1.5, 2.35]
    for i, (a, b) in enumerate(zip(vx, vx[1:])):
        key_stone = (i == 3)
        ta, tb = (a * 0.93, b * 0.93)   # slight splay at the soffit
        y0, y1 = 4.31, (5.30 if key_stone else 5.22)
        d = 0.19 if key_stone else 0.14
        bid = trim.new_block(tint=stone_tint())
        c = [(ta + .005, y0, -0.95), (tb - .005, y0, -0.95), (tb - .005, y0, d), (ta + .005, y0, d),
             (a + .005, y1, -0.95), (b - .005, y1, -0.95), (b - .005, y1, d), (a + .005, y1, d)]
        # only the soffit portion inside the opening is visible from below; stones outside the opening sit on jambs
        vs, made = trim.hexa(c, "VH_Ashlar", bid, skip=("s0",))
        trim.bevel_edges([e for e in {e for f in made.values() for e in f.edges} if max(v.co.z for v in e.verts) > -0.9],
                         LAYOUT.uniform(0.012, 0.02), 2)
    hood = [(-0.03, 5.22), (0.20, 5.22), (0.26, 5.27), (0.26, 5.34), (0.21, 5.40), (-0.03, 5.40)]
    sweep(trim, [(-2.55, 0.0), (2.55, 0.0)], False, hood, "VH_Ashlar", seg=1.3, key="hood")
    # portal floor slabs and threshold
    for i, (a, b) in enumerate(zip([-PORTAL_HW, -0.5, 0.5], [-0.5, 0.5, PORTAL_HW])):
        bid = pod.new_block(tint=stone_tint("rough"))
        vs, made = pod.box((a + .004, BASE - 0.12, -0.92), (b - .004, BASE, 0.0 - .004), "VH_PodiumSlab", bid, skip=("bottom",))
        pod.bevel_edges(list(made["top"].edges), 0.008, 2)

    # ------------------------------------------------ doors (steel, riveted, strap hinges, bronze studs)
    DZ = -0.9
    # frame
    for x0, x1, y0, y1 in ((-PORTAL_HW, -PORTAL_HW + 0.12, BASE, 4.31), (PORTAL_HW - 0.12, PORTAL_HW, BASE, 4.31),
                           (-PORTAL_HW, PORTAL_HW, 4.19, 4.31), (-PORTAL_HW, PORTAL_HW, 3.72, 3.84)):
        vs, made = metal.box((x0, y0, DZ - 0.05), (x1, y1, DZ + 0.12), "VH_Steel")
        metal.bevel_edges(list({e for f in made.values() for e in f.edges}), 0.006, 1)
    # transom grille over a dark back plate
    metal.box((-PORTAL_HW + 0.12, 3.84, DZ - 0.06), (PORTAL_HW - 0.12, 4.19, DZ - 0.03), "VH_Dark")
    nb = 13
    for i in range(nb):
        x = lerp(-PORTAL_HW + 0.2, PORTAL_HW - 0.2, i / (nb - 1))
        metal.cyl((x, 3.84, DZ + 0.03), (x, 4.19, DZ + 0.03), 0.014, "VH_Steel", 8)
    metal.box((-PORTAL_HW + 0.12, 3.99, DZ + 0.01), (PORTAL_HW - 0.12, 4.03, DZ + 0.05), "VH_Steel")
    # leaves
    leaf_y0, leaf_y1 = BASE + 0.03, 3.72
    for side in (-1, 1):
        xa, xb = sorted((side * 0.004, side * (PORTAL_HW - 0.12)))
        vs, made = metal.box((xa, leaf_y0, DZ - 0.02), (xb, leaf_y1, DZ + 0.06), "VH_DoorSteel")
        metal.bevel_edges(list({e for f in made.values() for e in f.edges}), 0.008, 1)
        # stiles and rails (raised frame strips) defining three panels
        rails = [leaf_y0, leaf_y0 + 0.42, 1.55, 2.62, leaf_y1 - 0.18, leaf_y1]
        strips = [(xa, xa + 0.11), (xb - 0.11, xb)]
        for (u0, u1) in strips:
            vs, made = metal.box((u0, leaf_y0, DZ + 0.06), (u1, leaf_y1, DZ + 0.085), "VH_DoorSteel")
            metal.bevel_edges(list(made["s2"].edges) if "s2" in made else [], 0.006, 1)
        for (r0, r1) in ((rails[0], rails[0] + 0.1), (rails[2] - 0.05, rails[2] + 0.05), (rails[3] - 0.05, rails[3] + 0.05),
                         (rails[4] - 0.02, rails[5])):
            metal.box((xa + 0.11, r0, DZ + 0.06), (xb - 0.11, r1, DZ + 0.085), "VH_DoorSteel")
        # kick plate (bronze)
        metal.box((xa + 0.13, leaf_y0 + 0.12, DZ + 0.06), (xb - 0.13, leaf_y0 + 0.40, DZ + 0.072), "VH_Bronze")
        # rivets along strips and bronze studs in panels (LOD0)
        if LOD == 0:
            for (u0, u1) in strips:
                uc = (u0 + u1) / 2
                y = leaf_y0 + 0.08
                while y < leaf_y1 - 0.05:
                    metal.sphere((uc, y, DZ + 0.085), 0.012, "VH_Steel", 6, hemi_axis=(0, 0, 1))
                    y += 0.16
            for (p0, p1) in ((rails[0] + 0.1, rails[2] - 0.05), (rails[2] + 0.05, rails[3] - 0.05), (rails[3] + 0.05, rails[4] - 0.02)):
                for iy in range(3):
                    for ix in range(3):
                        x = lerp(xa + 0.28, xb - 0.28, ix / 2)
                        y = lerp(p0 + 0.18, p1 - 0.18, iy / 2)
                        metal.sphere((x, y, DZ + 0.06), 0.028, "VH_Bronze", 8, hemi_axis=(0, 0, 1))
        # strap hinges on the outer edge
        hx_out = xb if side > 0 else xa
        for hy in (leaf_y0 + 0.55, 2.1, leaf_y1 - 0.5):
            h0, h1 = sorted((hx_out, hx_out - side * 0.85))
            metal.box((h0, hy - 0.05, DZ + 0.085), (h1, hy + 0.05, DZ + 0.1), "VH_Steel")
            metal.cyl((hx_out, hy - 0.09, DZ + 0.1), (hx_out, hy + 0.09, DZ + 0.1), 0.028, "VH_Steel", 10)
            if LOD == 0:
                for k in range(4):
                    metal.sphere((hx_out - side * (0.15 + k * 0.2), hy, DZ + 0.1), 0.014, "VH_Steel", 6, hemi_axis=(0, 0, 1))
        # bronze pull handle near the meeting edge
        hx = side * 0.22
        metal.cyl((hx, 1.25, DZ + 0.17), (hx, 1.95, DZ + 0.17), 0.022, "VH_Bronze", 10)
        for hy in (1.3, 1.9):
            metal.cyl((hx, hy, DZ + 0.085), (hx, hy, DZ + 0.18), 0.018, "VH_Bronze", 8)
    # meeting-edge cover strip
    metal.box((-0.05, leaf_y0, DZ + 0.085), (0.05, leaf_y1, DZ + 0.105), "VH_Steel")
    # threshold plate
    metal.box((-PORTAL_HW, BASE - 0.005, DZ - 0.02), (PORTAL_HW, BASE + 0.012, DZ + 0.35), "VH_Bronze")

    # ------------------------------------------------ drip helpers (frame -> world-local Drip)
    def fdrip(F, ua, ub, top, length, strength, kind="grime", plane_off=0.0, soft=0.12):
        n = F.n
        a, b = F.P(ua, 0, plane_off), F.P(ub, 0, plane_off)
        if abs(n.z) > 0.5:
            drips.add((0, 0, n.z), a.z, a.x, b.x, top, length, strength, kind, soft)
        else:
            drips.add((n.x, 0, 0), a.x, a.z, b.z, top, length, strength, kind, soft)

    def drips_sill(F, ua, ub, top, length):
        fdrip(F, ua - 0.1, ub + 0.1, top, length, 0.55)
        for u in (ua - 0.05, ub + 0.05):
            fdrip(F, u - 0.12, u + 0.12, top, length * 1.25, 0.95, soft=0.1)

    # ------------------------------------------------ windows (reveals, sills, lintels, frames, glass, bars)
    def window(F, ua, ub, y0, y1, depth, bars=True, ground=False, key="win"):
        # reveal lining stones (jambs + soffit), sill stone, lintel stone
        for (u0, u1) in ((ua - 0.001, ua + 0.06), (ub - 0.06, ub + 0.001)):
            j_y = [y0] + [c for c in COURSES if y0 < c < y1] + [y1]
            for ci, (a, b) in enumerate(zip(j_y, j_y[1:])):
                bid = trim.new_block(tint=stone_tint(), ao=0.8)
                F.box(trim, u0, u1, a + .004, b - .004, -depth, 0.03, "VH_Ashlar", bid, skip=("bottom", "top"))
        bid = trim.new_block(tint=stone_tint(), ao=0.72)
        F.box(trim, ua, ub, y1 - 0.06, y1, -depth, 0.03, "VH_Ashlar", bid, skip=("top",))
        # sill (projecting, weathered top)
        bid = trim.new_block(tint=stone_tint())
        vs, made = F.box(trim, ua - 0.1, ub + 0.1, y0 - 0.16, y0, -depth, 0.11, "VH_Ashlar", bid)
        eroded_bevel(trim, list(made["top"].edges) + [e for e in made["s2"].edges if e not in made["top"].edges], 0.015, 2)
        # sill ends shed water down the wall (strongest at the ends, lighter under the middle)
        drips_sill(F, ua, ub, y0 - 0.16, 2.6 if not ground else 1.25)
        # lintel stone in the course above
        bid = trim.new_block(tint=stone_tint())
        ly1 = y1 + (0.45 if not ground else 0.43)
        vs, made = F.box(trim, ua - 0.15 + .005, ub + 0.15 - .005, y1 + .005, ly1 - .005, 0.0, 0.075, "VH_Ashlar", bid,
                         skip=("s0",))
        eroded_bevel(trim, list(made["s2"].edges), 0.02, 2, seg_len=0.2)
        # steel frame and glazing at the back of the reveal
        fd = -depth + 0.02
        t = 0.05
        for (u0, u1, a, b) in ((ua, ua + t, y0, y1), (ub - t, ub, y0, y1), (ua, ub, y0, y0 + t), (ua, ub, y1 - t, y1)):
            F.box(metal, u0, u1, a, b, fd - 0.04, fd + 0.03, "VH_Steel")
        um = (ua + ub) / 2
        F.box(metal, um - 0.018, um + 0.018, y0, y1, fd - 0.03, fd + 0.02, "VH_Steel")
        rows = 4 if not ground else 2
        for k in range(1, rows):
            yy = lerp(y0, y1, k / rows)
            F.box(metal, ua, ub, yy - 0.016, yy + 0.016, fd - 0.03, fd + 0.02, "VH_Steel")
        F.box(glass, ua + t * 0.5, ub - t * 0.5, y0 + t * 0.5, y1 - t * 0.5, fd - 0.02, fd - 0.01, "VH_Glass",
              skip=("s0", "s1", "s3", "top", "bottom"))
        if bars:
            nbar = max(3, int((ub - ua) / 0.15))
            bd = -0.12
            for k in range(nbar):
                u = lerp(ua + 0.08, ub - 0.08, k / (nbar - 1))
                a3, b3 = F.P(u, y0 - 0.02, bd), F.P(u, y1 + 0.02, bd)
                metal.cyl(a3, b3, 0.015, "VH_Steel", 8)
            for yy in (lerp(y0, y1, 0.2), lerp(y0, y1, 0.8)):
                F.box(metal, ua - 0.02, ub + 0.02, yy - 0.025, yy + 0.025, bd - 0.012, bd + 0.014, "VH_Steel")
        # sand on the sill
        if LOD == 0:
            rr = drng(key, round(ua, 2), round(y0, 2))
            F.box(sand, ua + rr.uniform(0.0, 0.1), ub - rr.uniform(0.0, 0.1), y0, y0 + rr.uniform(0.008, 0.02), -depth + 0.05, 0.02,
                  "VH_Sand", skip=("bottom",))

    for a, b in gwin:
        window(FRONT, a, b, 2.01, 3.40, 0.32, ground=True, key="fg")
    for a, b in uwin:
        window(FRONT, a, b, 6.80, 9.50, 0.36, key="fu")
    for a, b in side_u:
        c = (a + b) / 2
        for F, sgn in ((EAST, 1), (WEST, -1)):
            ua, ub = (a, b) if sgn > 0 else (-b, -a)
            window(F, ua, ub, 6.80, 9.50, 0.36, key="su%d" % sgn)
            cc = (ua + ub) / 2
            window(F, cc - 0.35, cc + 0.35, 2.01, 3.40, 0.32, ground=True, key="sg%d" % sgn)
    window(REAR, *rear_win_open, 6.80, 9.50, 0.36, key="ru")
    # bricked-up window keeps its sill and lintel
    a, b = rear_win_infill
    bid = trim.new_block(tint=stone_tint())
    REAR.box(trim, a - 0.1, b + 0.1, 6.64, 6.80, -0.05, 0.11, "VH_Ashlar", bid)
    bid = trim.new_block(tint=stone_tint())
    REAR.box(trim, a - 0.15, b + 0.15, 9.505, 9.945, 0.0, 0.075, "VH_Ashlar", bid, skip=("s0",))

    # ------------------------------------------------ pilasters (front upper storey, sides) with capitals
    def pilaster(F, ua, ub, proj=0.12, key="pil"):
        ys = UPPER
        for ci, (y0, y1) in enumerate(zip(ys, ys[1:])):
            if y1 > 10.11:
                y1 = 10.1
            if y0 >= y1:
                continue
            ashlar_block(mas, F, ua + 0.005, ub - 0.005, y0 + 0.005, y1 - 0.005, depth=proj + 0.06, back=0.03,
                         key=(key, ci), bevel=(0.012, 0.02))
        # capital: two stepped mouldings
        bid = trim.new_block(tint=stone_tint())
        vs, made = F.box(trim, ua - 0.06, ub + 0.06, 10.1, 10.24, 0.0, proj + 0.14, "VH_Ashlar", bid, skip=("s0",))
        trim.bevel_edges(list(made["s2"].edges) + list(made["bottom"].edges), 0.015, 2)
        bid = trim.new_block(tint=stone_tint())
        vs, made = F.box(trim, ua - 0.1, ub + 0.1, 10.24, 10.4, 0.0, proj + 0.22, "VH_Ashlar", bid, skip=("s0",))
        trim.bevel_edges(list(made["s2"].edges) + list(made["bottom"].edges), 0.015, 2)

    for a, b in ((-0.6, 0.6), (-2.4, -1.8), (1.8, 2.4)):
        pilaster(FRONT, a, b, key=("pf", a))
    for F in (EAST,):
        pilaster(F, 4.0, 4.5, key="pe")
    pilaster(WEST, -4.5, -4.0, key="pw")

    # ------------------------------------------------ steel brackets under the entablature soffit
    def bracket(F, u, key="br"):
        top = PIER_TOP
        depth = 0.5          # frieze projection over every wall face
        start = 0.065        # on the block faces
        plate = 0.018
        # vertical wall plate, horizontal top plate, diagonal gusset
        F.box(metal, u - 0.09, u + 0.09, top - 0.75, top - 0.02, start, start + 0.02, "VH_Steel")
        F.box(metal, u - 0.09, u + 0.09, top - 0.035, top - 0.005, start, depth - 0.02, "VH_Steel")
        g = [F.P(u - plate / 2, top - 0.72, start + 0.02), F.P(u + plate / 2, top - 0.72, start + 0.02),
             F.P(u + plate / 2, top - 0.035, start + 0.02), F.P(u - plate / 2, top - 0.035, start + 0.02),
             F.P(u - plate / 2, top - 0.72, start + 0.05), F.P(u + plate / 2, top - 0.72, start + 0.05),
             F.P(u + plate / 2, top - 0.035, depth - 0.05), F.P(u - plate / 2, top - 0.035, depth - 0.05)]
        # reorder into bottom/top rings for hexa: use as a wedge-like hexahedron
        metal.hexa([g[0], g[1], g[5], g[4], g[3], g[2], g[6], g[7]], "VH_Steel")
        if LOD == 0:
            for yy in (top - 0.62, top - 0.4, top - 0.18):
                metal.cyl(F.P(u - 0.05, yy, start + 0.02), F.P(u - 0.05, yy, start + 0.045), 0.016, "VH_Steel", 6)
                metal.cyl(F.P(u + 0.05, yy, start + 0.02), F.P(u + 0.05, yy, start + 0.045), 0.016, "VH_Steel", 6)

    for u in (-3.66, 3.66):
        bracket(FRONT, u)
    for u in (1.75, 6.6):
        bracket(EAST, u)
        bracket(WEST, -u)
    for u in (-2.6, 0.0, 2.6):
        bracket(REAR, u)

    # ------------------------------------------------ iron corbels on the frieze, under the cornice
    def corbel(F, u, key="cb"):
        y0, y1, D = 10.47, 11.24, 0.34
        prof = [(0.0, y0), (0.07, y0), (D, y1 - 0.07), (D, y1), (0.0, y1)]
        for side in (-1, 1):
            ux = u + side * 0.075
            verts = [F.P(ux - 0.009, y, d) for d, y in prof] + [F.P(ux + 0.009, y, d) for d, y in prof]
            m = len(prof)
            faces = [[i, (i + 1) % m, m + (i + 1) % m, m + i] for i in range(m)] + [list(range(m))[::-1], [m + i for i in range(m)]]
            metal.closed_solid(verts, faces, "VH_Steel")
        # sloped front strap and top bearing plate
        a0, a1 = (0.07, y0), (D, y1 - 0.07)
        strap = [F.P(u - 0.085, a0[1], a0[0]), F.P(u + 0.085, a0[1], a0[0]), F.P(u + 0.085, a1[1], a1[0]), F.P(u - 0.085, a1[1], a1[0])]
        n_out = (F.n * 0.012)
        up = Vector((0, 0.012, 0))
        off = n_out - up * (0.07 / 0.77)
        metal.hexa([strap[0], strap[1], strap[1] + off, strap[0] + off, strap[3], strap[2], strap[2] + off, strap[3] + off], "VH_Steel")
        F.box(metal, u - 0.1, u + 0.1, y1 - 0.018, y1, 0.0, D + 0.02, "VH_Steel")
        F.box(metal, u - 0.11, u + 0.11, y0 - 0.02, y0 + 0.16, 0.0, 0.014, "VH_Steel")
        if LOD == 0:
            for yy in (y0 + 0.05, y0 + 0.12):
                for du in (-0.08, 0.08):
                    metal.sphere(F.P(u + du, yy, 0.014), 0.016, "VH_Steel", 6, hemi_axis=tuple(F.n))

    for u in (-3.35, -2.1, -0.45, 0.45, 2.1, 3.35):
        corbel(EF, u)
    for u in (1.9, 4.25, 6.6):
        corbel(EE, u)
        corbel(EW, -u)
    for u in (-3.0, -1.0, 1.0, 3.0):
        corbel(ER, u)

    # ------------------------------------------------ nameplate (bronze plate; letters added in Blender space)
    npx, npy0, npy1 = 2.05, 5.46, 5.96
    vs, made = metal.box((-npx, npy0, 0.05), (npx, npy1, 0.085), "VH_PlateBronze")
    metal.bevel_edges(list(made["s2"].edges) if "s2" in made else list({e for f in made.values() for e in f.edges}), 0.012, 2)
    for (x0, x1, y0, y1) in ((-npx, npx, npy0, npy0 + 0.035), (-npx, npx, npy1 - 0.035, npy1),
                             (-npx, -npx + 0.035, npy0, npy1), (npx - 0.035, npx, npy0, npy1)):
        metal.box((x0, y0, 0.085), (x1, y1, 0.097), "VH_Brass")
    for x in (-npx + 0.08, npx - 0.08):
        for y in (npy0 + 0.1, npy1 - 0.1):
            metal.sphere((x, y, 0.097), 0.018, "VH_Brass", 8, hemi_axis=(0, 0, 1))
    rec["nameplate"] = {"centre": [0, (npy0 + npy1) / 2, 0.097], "size": [2 * npx, npy1 - npy0]}

    # ------------------------------------------------ steel repairs: pier base wraps and a strapped pier
    def pier_wrap(cx, cz):
        y0, y1 = BASE + 0.62, 1.95
        def face_pts(y):
            w, pr = pier_w(y), pier_proj(y)
            xo = (WX + pr + 0.012) * cx
            zo = (ZF + pr + 0.012) if cz > 0 else (ZB - pr - 0.012)
            return xo, zo
        xo0, zo0 = face_pts(y0)
        xo1, zo1 = face_pts(y1)
        L = 0.85
        t = 0.012
        # plate on the front (z) face along x, and on the side (x) face along z
        metal.hexa([(xo0, y0, zo0), (xo0 - cx * L, y0, zo0), (xo0 - cx * L, y0, zo0 + t * cz), (xo0, y0, zo0 + t * cz),
                    (xo1, y1, zo1), (xo1 - cx * L, y1, zo1), (xo1 - cx * L, y1, zo1 + t * cz), (xo1, y1, zo1 + t * cz)], "VH_Steel")
        metal.hexa([(xo0, y0, zo0), (xo0, y0, zo0 - cz * L), (xo0 + cx * t, y0, zo0 - cz * L), (xo0 + cx * t, y0, zo0),
                    (xo1, y1, zo1), (xo1, y1, zo1 - cz * L), (xo1 + cx * t, y1, zo1 - cz * L), (xo1 + cx * t, y1, zo1)], "VH_Steel")
        # corner angle
        metal.box((min(xo0, xo0 + cx * 0.04), y0 - 0.02, min(zo0, zo0 + cz * 0.04)), (max(xo0, xo0 + cx * 0.04), y1 + 0.02, max(zo0, zo0 + cz * 0.04)), "VH_Steel")
        if LOD == 0:
            for k in range(5):
                for yy in (y0 + 0.07, y1 - 0.07):
                    s = 0.1 + k * 0.17
                    metal.sphere((xo0 - cx * s, yy, zo0 + t * cz), 0.013, "VH_Steel", 6, hemi_axis=(0, 0, cz))
                    metal.sphere((xo0 + cx * t, yy, zo0 - cz * s), 0.013, "VH_Steel", 6, hemi_axis=(cx, 0, 0))

    for cx in (-1, 1):
        pier_wrap(cx, 1)
    pier_wrap(-1, -1)
    # strap band around the front-west pier at 7.2 m
    yb = 7.2
    w, pr = pier_w(yb), pier_proj(yb)
    xo, xi = -(WX + pr + 0.01), -(WX + pr - w - 0.01)
    zo, zi = ZF + pr + 0.01, ZF + pr - w
    for (a, b) in (((xo, zo), (xi, zo)), ((xo, zo), (xo, zi)), ((xi, zo), (xi, 0.0))):
        (x0, z0), (x1, z1) = a, b
        metal.box((min(x0, x1) - 0.01, yb - 0.07, min(z0, z1) - 0.01), (max(x0, x1) + 0.01, yb + 0.07, max(z0, z1) + 0.01), "VH_Steel")
    if LOD == 0:
        for k in range(4):
            metal.cyl((lerp(xo, xi, 0.15 + 0.23 * k), yb, zo + 0.005), (lerp(xo, xi, 0.15 + 0.23 * k), yb, zo + 0.03), 0.02, "VH_Steel", 6)

    # rear repair plate over spalled stone (x -3.1..-1.1, y 1.4..3.3) with rivets
    metal.box((-3.1, 1.45, ZB - 0.075), (-1.15, 3.3, ZB - 0.062), "VH_Steel")
    metal.box((-2.2, 2.2, ZB - 0.09), (-1.2, 3.1, ZB - 0.074), "VH_Steel")
    if LOD == 0:
        for x in [lerp(-3.02, -1.23, k / 9) for k in range(10)]:
            for y in (1.52, 3.23):
                metal.sphere((x, y, ZB - 0.075), 0.014, "VH_Steel", 6, hemi_axis=(0, 0, -1))
        for y in [lerp(1.6, 3.15, k / 6) for k in range(7)]:
            for x in (-3.03, -1.22):
                metal.sphere((x, y, ZB - 0.075), 0.014, "VH_Steel", 6, hemi_axis=(0, 0, -1))

    # ------------------------------------------------ rear service door (painted steel) + canopy
    rx0, rx1 = 1.2, 2.3
    for x0, x1, y0, y1 in ((rx0, rx0 + 0.08, BASE, 2.92), (rx1 - 0.08, rx1, BASE, 2.92), (rx0, rx1, 2.84, 2.92)):
        REAR.box(metal, -x1, -x0, y0, y1, -0.34, -0.2, "VH_Steel")
    for x0, x1 in ((rx0 - 0.001, rx0 + 0.06), (rx1 - 0.06, rx1 + 0.001)):
        bid = trim.new_block(tint=stone_tint(), ao=0.8)
        REAR.box(trim, -x1, -x0, BASE, 2.92, -0.34, 0.03, "VH_Ashlar", bid, skip=("bottom", "top"))
    bid = trim.new_block(tint=stone_tint(), ao=0.7)
    REAR.box(trim, -rx1, -rx0, 2.86, 2.92, -0.34, 0.03, "VH_Ashlar", bid, skip=("top",))
    bid = trim.new_block(tint=stone_tint())
    vs, made = REAR.box(trim, -rx1 - 0.15, -rx0 + 0.15, 2.925, 3.395, 0.0, 0.075, "VH_Ashlar", bid, skip=("s0",))
    trim.bevel_edges(list(made["s2"].edges), 0.02, 2)
    REAR.box(metal, -rx1 + 0.08, -rx0 - 0.08, BASE + 0.02, 2.84, -0.3, -0.25, "VH_PaintedSteel")
    for yy in (0.95, 1.7, 2.45):
        REAR.box(metal, -rx1 + 0.12, -rx0 - 0.12, yy - 0.03, yy + 0.03, -0.25, -0.235, "VH_PaintedSteel")
    REAR.box(metal, -rx0 - 0.2, -rx0 - 0.14, 1.35, 1.5, -0.25, -0.18, "VH_Steel")   # lever handle block
    metal.cyl(REAR.P(-rx0 - 0.17, 1.42, -0.18), REAR.P(-rx0 - 0.4, 1.42, -0.16), 0.014, "VH_Steel", 8)
    # canopy: steel sheet on two brackets
    cy = 3.55
    REAR.box(metal, -rx1 - 0.35, -rx0 + 0.35, cy, cy + 0.03, 0.0, 0.85, "VH_PaintedSteel")
    for x in (-rx1 - 0.25, -rx0 + 0.25):
        REAR.box(metal, x - 0.012, x + 0.012, cy - 0.6, cy, 0.02, 0.05, "VH_Steel")
        c = [REAR.P(x - 0.008, cy - 0.55, 0.03), REAR.P(x + 0.008, cy - 0.55, 0.03), REAR.P(x + 0.008, cy - 0.55, 0.06), REAR.P(x - 0.008, cy - 0.55, 0.06),
             REAR.P(x - 0.008, cy - 0.005, 0.03), REAR.P(x + 0.008, cy - 0.005, 0.03), REAR.P(x + 0.008, cy - 0.005, 0.8), REAR.P(x - 0.008, cy - 0.005, 0.8)]
        metal.hexa(c, "VH_Steel")

    # ------------------------------------------------ conduit, junction boxes, downpipe, scuppers
    # west of the portal: junction box feeding the west lamp; east lamp fed from above
    jb = (-2.45, 1.45)
    metal.box((jb[0] - 0.16, jb[1] - 0.22, 0.05), (jb[0] + 0.16, jb[1] + 0.22, 0.2), "VH_PaintedSteel")
    metal.box((jb[0] - 0.17, jb[1] + 0.2, 0.04), (jb[0] + 0.17, jb[1] + 0.24, 0.21), "VH_PaintedSteel")
    metal.tube([(jb[0], jb[1] + 0.22, 0.12), (jb[0], 3.05, 0.12)], 0.024, "VH_Steel", clamps=0.6)
    metal.tube([(jb[0], jb[1] - 0.22, 0.12), (jb[0], BASE + 0.02, 0.12)], 0.024, "VH_Steel")
    metal.tube([(2.45, 3.05, 0.12), (2.45, 5.1, 0.12), (3.3, 5.1, 0.12), (3.3, 6.02, 0.12)], 0.022, "VH_Steel", clamps=0.7)
    # west side downpipe from a scupper near the front pier
    dz = -1.55
    metal.tube([(-6.12, 11.36, dz), (-6.12, 10.2, dz), (-5.15, 9.6, dz), (-5.15, 1.05, dz), (-5.42, 0.62, dz)], 0.07,
               "VH_Steel", sides=12, clamps=1.4)
    metal.box((-6.3, 11.36, dz - 0.17), (-5.94, 11.86, dz + 0.17), "VH_Steel")        # hopper head
    for (x0, x1, y0, y1, z0, z1) in ((-6.2, -5.3, 11.86, 11.88, dz - 0.09, dz + 0.09), (-6.2, -5.3, 11.86, 11.95, dz - 0.09, dz - 0.08),
                                     (-6.2, -5.3, 11.86, 11.95, dz + 0.08, dz + 0.09)):
        metal.box((x0, y0, z0), (x1, y1, z1), "VH_Steel")
    # scuppers through the parapet (front, east, rear) - dark stains added as decals in Unity
    scuppers = [((-3.2, PZF), (0, 1)), ((3.2, PZF), (0, 1)), ((PPX, -3.0), (1, 0)), ((PPX, -6.4), (1, 0)),
                ((-PPX, -5.6), (-1, 0)), ((-2.6, PZB), (0, -1)), ((2.8, PZB), (0, -1))]
    rec["scuppers"] = []
    for (x, z), (nx, nz) in scuppers:
        L = 0.75
        a = Vector((x, 11.9, z))
        n = Vector((nx, 0, nz))
        s = Vector((nz, 0, -nx))
        base = a - n * 0.1
        tip = a + n * L
        # U channel: bottom + two cheeks
        for off, h, w in ((0.0, 0.012, 0.09), (0.085, 0.09, 0.008), (-0.085, 0.09, 0.008)):
            c0 = base + s * off
            c1 = tip + s * off
            lo = [c0 - s * w, c1 - s * w, c1 + s * w, c0 + s * w]
            corners = [Vector((p.x, 11.9 - 0.02, p.z)) for p in lo] + [Vector((p.x, 11.9 - 0.02 + h, p.z)) for p in lo]
            metal.hexa(corners, "VH_Steel")
        rec["scuppers"].append({"tip": [tip.x, 11.88, tip.z], "normal": [nx, 0, nz]})

    # ------------------------------------------------ podium, slabs, steps
    pod_courses = [0.0, 0.25, BASE]
    PFr = Frame((0, 0, POD_ZF), (1, 0, 0), (0, 0, 1))
    PRr = Frame((0, 0, POD_ZB), (-1, 0, 0), (0, 0, -1))
    PEr = Frame((POD_X, 0, 0), (0, 0, -1), (1, 0, 0))
    PWr = Frame((-POD_X, 0, 0), (0, 0, 1), (-1, 0, 0))
    for F, ua, ub, key in ((PFr, -POD_X - 0.06, POD_X + 0.06, "pf"), (PRr, -POD_X - 0.06, POD_X + 0.06, "pr"), (PEr, -POD_ZF, -POD_ZB, "pe"), (PWr, POD_ZB, POD_ZF, "pw")):
        fill_wall(pod, F, ua, ub, pod_courses, [], mat="VH_AshlarRough", lmin=0.7, lmax=1.3, key=key, mortar=True)
    # coping ring (edge stones) and paving slabs on top
    ring_w = 0.42
    def slab(x0, z0, x1, z1, key):
        bid = pod.new_block(tint=stone_tint("rough"))
        vs, made = pod.box((x0 + 0.005, BASE - 0.1, z0 + 0.005), (x1 - 0.005, BASE, z1 - 0.005), "VH_PodiumSlab", bid, skip=("bottom",))
        rr = drng("slab", key)
        pod.bevel_edges(list(made["top"].edges), rr.uniform(0.006, 0.014), 2)
    # edge ring: front and rear runs along x, sides along z
    x = -POD_X
    while x < POD_X - 1e-3:
        ln = min(LAYOUT.uniform(0.8, 1.2), POD_X - x)
        if POD_X - (x + ln) < 0.4:
            ln = POD_X - x
        slab(x, POD_ZF - ring_w, x + ln, POD_ZF + 0.085, ("rf", round(x, 2)))
        slab(x, POD_ZB - 0.085, x + ln, POD_ZB + ring_w, ("rr", round(x, 2)))
        x += ln
    z = POD_ZB + ring_w
    while z < POD_ZF - ring_w - 1e-3:
        ln = min(LAYOUT.uniform(0.8, 1.2), POD_ZF - ring_w - z)
        if POD_ZF - ring_w - (z + ln) < 0.4:
            ln = POD_ZF - ring_w - z
        slab(POD_X - ring_w, z, POD_X + 0.04, z + ln, ("re", round(z, 2)))
        slab(-POD_X - 0.04, z, -POD_X + ring_w, z + ln, ("rw", round(z, 2)))
        z += ln
    # inner paving: terrace in front of the facade and strips along the sides and rear (outside the walls)
    def pave(x0, x1, z0, z1, key, sx=0.9, sz=0.75):
        zz = z0
        row = 0
        while zz < z1 - 1e-3:
            h = min(sz, z1 - zz)
            xx = x0 + (-(sx / 2) if row % 2 else 0)
            while xx < x1 - 1e-3:
                a, b = max(xx, x0), min(xx + sx, x1)
                if b - a > 0.08:
                    slab(a, zz, b, zz + h, (key, row, round(xx, 2)))
                xx += sx
            zz += h
            row += 1
    pave(-POD_X + ring_w, POD_X - ring_w, ZF, POD_ZF - ring_w, "terrace")
    pave(-POD_X + ring_w, POD_X - ring_w, POD_ZB + ring_w, ZB, "rearstrip")
    pave(WX, POD_X - ring_w, ZB, ZF, "eaststrip", sx=0.55, sz=0.9)
    pave(-POD_X + ring_w, -WX, ZB, ZF, "weststrip", sx=0.55, sz=0.9)
    # front step (same footprint and height as the original step) and a rear service step
    for (x0, x1, z0, z1, key) in ((-3.25, 3.25, POD_ZF, POD_ZF + 0.8, "fstep"), (1.0, 2.5, POD_ZB - 0.8, POD_ZB, "rstep")):
        x = x0
        while x < x1 - 1e-3:
            ln = min(LAYOUT.uniform(1.0, 1.6), x1 - x)
            if x1 - (x + ln) < 0.5:
                ln = x1 - x
            bid = pod.new_block(tint=stone_tint("rough"))
            vs, made = pod.box((x + 0.004, 0.0, z0 + 0.004), (x + ln - 0.004, 0.25, z1 - 0.004), "VH_PodiumSlab", bid, skip=("bottom",))
            pod.bevel_edges(list(made["top"].edges), 0.018, 2)
            x += ln
    rec["colliders"] += [
        {"name": "COL_Podium", "center": [0, 0.21, (POD_ZF + POD_ZB) / 2], "size": [2 * POD_X, 0.58, POD_ZF - POD_ZB]},
        {"name": "COL_FrontStep", "center": [0, 0.125, POD_ZF + 0.4], "size": [6.5, 0.25, 0.8]},
        {"name": "COL_RearStep", "center": [1.75, 0.125, POD_ZB - 0.4], "size": [1.5, 0.25, 0.8]},
        {"name": "COL_Body", "center": [0, (BASE + 12.85) / 2, (-0.9 + ZB) / 2], "size": [2 * WX, 12.85 - BASE, -0.9 - ZB]},
        {"name": "COL_FrontWest", "center": [-(PORTAL_HW + WX) / 2, (BASE + 12.85) / 2, -0.45], "size": [WX - PORTAL_HW, 12.85 - BASE, 0.9]},
        {"name": "COL_FrontEast", "center": [(PORTAL_HW + WX) / 2, (BASE + 12.85) / 2, -0.45], "size": [WX - PORTAL_HW, 12.85 - BASE, 0.9]},
        {"name": "COL_OverPortal", "center": [0, (4.31 + 12.85) / 2, -0.45], "size": [2 * PORTAL_HW, 12.85 - 4.31, 0.9]},
        {"name": "COL_Entablature", "center": [0, (PIER_TOP + 12.85) / 2, (ENT_ZF + ENT_ZB) / 2], "size": [2 * ENT_X, 12.85 - PIER_TOP, ENT_ZF - ENT_ZB]},
    ]
    for cx in (-1, 1):
        for cz in (1, -1):
            xo = WX + PIER_PROJ0
            xc = cx * (xo - PIER_W0 / 2)
            zo = (ZF + PIER_PROJ0) if cz > 0 else (ZB - PIER_PROJ0)
            zc = zo - cz * PIER_W0 / 2
            rec["colliders"].append({"name": f"COL_Pier_{'E' if cx > 0 else 'W'}{'F' if cz > 0 else 'R'}",
                                     "center": [xc, (BASE + PIER_TOP) / 2, zc], "size": [PIER_W0 - 0.1, PIER_TOP - BASE, PIER_W0 - 0.1]})

    # ------------------------------------------------ roof furniture and comms mast
    roof.box((-3.6, 11.86, -6.9), (-2.6, 12.28, -5.9), "VH_PaintedSteel")          # hatch housing
    roof.box((-3.65, 12.28, -6.95), (-2.55, 12.33, -5.85), "VH_Steel")
    for (x, z) in ((3.4, -6.8), (3.9, -2.3)):
        roof.cyl((x, 11.86, z), (x, 12.75, z), 0.14, "VH_Steel", 12)
        roof.cyl((x, 12.8, z), (x, 12.95, z), 0.24, "VH_Steel", 12, r2=0.05)
        roof.cyl((x, 12.75, z), (x, 12.8, z), 0.03, "VH_Steel", 6)
    mx, mz = 0.9, -3.4
    roof.box((mx - 0.35, 11.86, mz - 0.25), (mx + 0.35, 12.8, mz + 0.25), "VH_PaintedSteel")   # equipment cabinet
    roof.box((mx - 0.37, 12.8, mz - 0.27), (mx + 0.37, 12.84, mz + 0.27), "VH_Steel")
    roof.cyl((mx, 11.86, mz - 0.55), (mx, 17.4, mz - 0.55), 0.085, "VH_Steel", 12)
    roof.cyl((mx, 17.4, mz - 0.55), (mx, 19.1, mz - 0.55), 0.05, "VH_Steel", 10)
    roof.box((mx - 0.2, 11.86, mz - 0.75), (mx + 0.2, 11.95, mz - 0.35), "VH_Steel")
    roof.cyl((mx - 1.15, 17.6, mz - 0.55), (mx + 1.15, 17.6, mz - 0.55), 0.035, "VH_Steel", 8)
    for x in (-1.05, -0.45, 0.45, 1.05):
        roof.cyl((mx + x, 17.55, mz - 0.55), (mx + x, 18.5 + (0.2 if abs(x) < 1 else 0.0), mz - 0.55), 0.011, "VH_Steel", 6)
    # guy wires
    for (gx, gz) in ((-4.2, -1.2), (4.2, -1.8), (0.4, -7.6)):
        roof.cyl((mx, 16.2, mz - 0.55), (gx, 11.9, gz), 0.006, "VH_Steel", 5, cap=False)
        roof.box((gx - 0.08, 11.86, gz - 0.08), (gx + 0.08, 11.95, gz + 0.08), "VH_Steel")
    # dish on an arm, pointing north-west and slightly up
    dc = Vector((mx - 0.5, 15.9, mz - 0.25))
    roof.cyl((mx, 15.9, mz - 0.55), tuple(dc), 0.03, "VH_Steel", 6)
    aim = Vector((-0.55, 0.18, 0.8)).normalized()
    ring = 16 if LOD == 0 else 10
    R0 = 0.46
    ref = Vector((0, 1, 0))
    s1 = aim.cross(ref).normalized()
    s2 = aim.cross(s1).normalized()
    verts = [tuple(dc - aim * 0.02)]
    for k in range(1, 4):
        r = R0 * k / 3
        depth = 0.16 * (k / 3) ** 2
        for i in range(ring):
            t = 2 * math.pi * i / ring
            verts.append(tuple(dc + aim * depth + (s1 * math.cos(t) + s2 * math.sin(t)) * r))
    faces = [[0, 1 + (i + 1) % ring, 1 + i] for i in range(ring)]
    for k in range(2):
        for i in range(ring):
            a0 = 1 + k * ring + i
            a1 = 1 + k * ring + (i + 1) % ring
            faces.append([a0, a1, a1 + ring, a0 + ring])
    vs = [roof.bm.verts.new(Vector(p)) for p in verts]
    fs = []
    idx = roof.mi("VH_PaintedSteel")
    for f in faces:
        ff = roof.bm.faces.new([vs[i] for i in f])
        ff.material_index = idx
        fs.append(ff)
    bmesh.ops.recalc_face_normals(roof.bm, faces=fs)
    roof.cyl(tuple(dc + aim * 0.16 + s1 * 0.42), tuple(dc + aim * 0.5), 0.01, "VH_Steel", 5)
    roof.cyl(tuple(dc + aim * 0.16 - s1 * 0.42), tuple(dc + aim * 0.5), 0.01, "VH_Steel", 5)
    roof.sphere(tuple(dc + aim * 0.5), 0.035, "VH_Steel", 8)
    # aircraft warning beacon
    roof.sphere((mx, 19.16, mz - 0.55), 0.07, "VH_BeaconRed", 10)
    rec["beacon"] = [mx, 19.16, mz - 0.55]
    # cable down the mast to the cabinet
    roof.tube([(mx + 0.09, 17.3, mz - 0.55), (mx + 0.09, 12.85, mz - 0.55), (mx + 0.09, 12.8, mz - 0.3)], 0.012, "VH_Rubber", sides=6)

    # ------------------------------------------------ sheltered sand drifts on the podium (LOD0)
    if LOD == 0:
        def drift(a, b, width, height, key, n=14):
            """Wedge of sand along a wall base from a to b (x, z), heaped against the wall on the 'inner' side."""
            rr = drng("drift", key)
            a, b = Vector((a[0], 0, a[1])), Vector((b[0], 0, b[1]))
            d = b - a
            L = d.length
            out = Vector((-d.z, 0, d.x)).normalized()   # same side as sweep() outward: away from the wall
            pts_wall, pts_top, pts_toe = [], [], []
            for i in range(n + 1):
                t = i / n
                env = math.sin(math.pi * t) ** 0.6
                h = height * env * (0.7 + 0.6 * pnoise(Vector((t * 5 + rr.random(), 0.3, 0.0))) ** 2)
                w = width * env * (0.8 + 0.4 * rr.random())
                p = a + d * t
                pts_wall.append(Vector((p.x, BASE + max(h, 0.002), p.z)) + out * 0.0)
                pts_top.append(Vector((p.x, BASE + max(h, 0.002) * 0.45, p.z)) + out * (w * 0.4))
                pts_toe.append(Vector((p.x, BASE + 0.001, p.z)) + out * max(w, 0.02))
            rows = [pts_wall, pts_top, pts_toe]
            vs = [[sand.bm.verts.new(p) for p in r] for r in rows]
            idx = sand.mi("VH_Sand")
            fs = []
            for r in range(2):
                for i in range(n):
                    f = sand.bm.faces.new([vs[r][i], vs[r][i + 1], vs[r + 1][i + 1], vs[r + 1][i]])
                    f.material_index = idx
                    fs.append(f)
            for f in fs:
                f.normal_update()
                if f.normal.y < 0:
                    f.normal_flip()
        xi = pier_inner_x(0.6)
        drift((-xi, 0.02), (-ARCH_HW - 0.1, 0.02), 0.32, 0.07, "fw")
        drift((ARCH_HW + 0.1, 0.02), (xi, 0.02), 0.28, 0.06, "fe")
        drift((-PORTAL_HW + 0.05, -0.8), (PORTAL_HW - 0.05, -0.8), 0.18, 0.03, "portal")
        drift((WX + 0.02, pier_side_front(0.6)), (WX + 0.02, pier_side_rear(0.6)), 0.3, 0.08, "east")
        drift((-WX - 0.02, pier_side_front(0.6)), (-WX - 0.02, pier_side_rear(0.6)), 0.34, 0.09, "west")
        drift((xi, ZB - 0.02), (-xi, ZB - 0.02), 0.3, 0.07, "rear")

    # ------------------------------------------------ terrace uplights (floodlight the nameplate and banner at night)
    rec["lights"] = []
    for side in (-1, 1):
        x, z = side * 2.75, 1.75
        metal.box((x - 0.2, BASE, z - 0.16), (x + 0.2, BASE + 0.06, z + 0.16), "VH_Steel")          # base plate
        for dx in (-0.13, 0.13):
            metal.box((x + dx - 0.012, BASE + 0.06, z - 0.03), (x + dx + 0.012, BASE + 0.3, z + 0.03), "VH_Steel")
        target = Vector((side * 0.4, 7.4, 0.2))
        head = Vector((x, BASE + 0.26, z))
        aim = (target - head).normalized()
        ref = Vector((1, 0, 0))
        s1 = aim.cross(ref).normalized(); s2 = aim.cross(s1).normalized()
        c0, c1 = head - aim * 0.12, head + aim * 0.06
        def ring(c, r1, r2):
            return [c + s1 * r1 * sx + s2 * r2 * sy for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        metal.hexa(ring(c0, 0.14, 0.1) + ring(c1, 0.15, 0.11), "VH_PaintedSteel")
        metal.hexa(ring(c1, 0.12, 0.085) + ring(c1 + aim * 0.012, 0.12, 0.085), "VH_LampLens")
        metal.cyl(tuple(Vector((x - 0.13, BASE + 0.26, z))), tuple(Vector((x + 0.13, BASE + 0.26, z))), 0.018, "VH_Steel", 8)
        rec["lights"].append({"name": "Facade uplight " + ("west" if side < 0 else "east"), "type": "Spot",
                              "pos": list(head + aim * 0.1), "target": list(target), "intensity": 16.0, "range": 13.0,
                              "angle": 42.0, "inner": 18.0, "color": [1.0, 0.86, 0.68]})
    # cable from the uplights into the portal junction
    metal.tube([(-2.75, BASE + 0.012, 1.55), (-2.45, BASE + 0.012, 0.2)], 0.012, "VH_Rubber", sides=6)
    metal.tube([(2.75, BASE + 0.012, 1.55), (2.45, BASE + 0.012, 0.2)], 0.012, "VH_Rubber", sides=6)

    # ------------------------------------------------ mounts (placed in Unity)
    rec["mounts"] += [
        {"name": "Portal lamp west", "prefab": "PH_WallLamp", "pos": [-2.45, 3.25, 0.13], "yaw": 0},
        {"name": "Portal lamp east", "prefab": "PH_WallLamp", "pos": [2.45, 3.25, 0.13], "yaw": 0},
        {"name": "Rear door lamp", "prefab": "PH_WallLamp", "pos": [1.75, 3.1, ZB - 0.13], "yaw": 180},
        {"name": "Portal recess lamp", "prefab": "PH_WallLamp", "pos": [-PORTAL_HW + 0.075, 3.05, -0.5], "yaw": 90},
        {"name": "East security light", "prefab": "PH_SecurityLight", "pos": [WX + 0.05, 5.7, -6.2], "yaw": 90},
        {"name": "East security camera", "prefab": "PH_SecurityCamera", "pos": [WX + 0.05, 5.5, -1.7], "yaw": 60},
        {"name": "Rear air conditioner", "prefab": "PH_AirconRusted", "pos": [-0.35, BASE, ZB - 0.55], "yaw": 180},
        {"name": "Roof air conditioner", "prefab": "PH_AirconRusted", "pos": [-2.2, 11.86, -3.3], "yaw": 180},
        {"name": "East power box", "prefab": "PH_PowerBox", "pos": [WX + 0.08, BASE + 0.9, -4.9], "yaw": 90},
    ]

    # ------------------------------------------------ build objects
    def mas_ao(p, n):
        a = wall_ao(p, n)
        if n.y < -0.5:
            a *= 0.8
        # inside the portal recess
        if abs(p.x) < 2.0 and p.z < 0.05 and p.y < 5.3:
            a *= lerp(1.0, 0.6, smoothstep(0.05, -0.9, p.z))
        return a

    def trim_ao(p, n):
        a = 1.0
        if abs(p.x) < 2.2 and p.z < 0.0 and p.y < 5.3:
            a *= lerp(1.0, 0.55, smoothstep(0.0, -0.9, p.z))
        if n.y < -0.5:
            a *= 0.78
        if p.y < 1.2:
            a *= 0.85
        return a

    def pod_ao(p, n):
        # darker close to the walls (sheltered), lighter at the open edges
        dx = max(0.0, WX - abs(p.x)) if -8.5 < p.z < 0 else 0
        dwall = min(abs(abs(p.x) - WX) if ZB < p.z < ZF else 9, abs(p.z - ZF) if abs(p.x) < WX else 9, abs(p.z - ZB) if abs(p.x) < WX else 9)
        return lerp(0.72, 1.0, smoothstep(0.0, 1.4, dwall))

    # drip edges of the whole shell: entablature, walls under the soffit, string course, parapet coping
    for F in (FRONT, REAR):
        fdrip(F, -ENT_X, ENT_X, 11.2, 1.6, 0.8, plane_off=ENT_ZF - ZF if F is FRONT else ZB - ENT_ZB)
        fdrip(F, -WX - 0.9, WX + 0.9, PIER_TOP - 0.02, 6.0, 0.95, soft=0.3)
        fdrip(F, -WX, WX, 6.1, 3.0, 0.75, soft=0.3)
        fdrip(F, -PPX, PPX, 12.7, 0.95, 0.75, plane_off=PZF if F is FRONT else ZB - PZB)
    for F in (EAST, WEST):
        fdrip(F, -12, 12, 11.2, 1.6, 0.8, plane_off=ENT_X - WX)
        fdrip(F, -12, 12, PIER_TOP - 0.02, 6.0, 0.95, soft=0.3)
        fdrip(F, -12, 12, 6.1, 3.0, 0.75, soft=0.3)
        fdrip(F, -12, 12, 12.7, 0.95, 0.75, plane_off=PPX - WX)
    # rust under the iron corbels (frieze) and the steel brackets (walls)
    for F, us in ((EF, (-3.35, -2.1, -0.45, 0.45, 2.1, 3.35)), (EE, (1.9, 4.25, 6.6)), (EW, (-1.9, -4.25, -6.6)),
                  (ER, (-3.0, -1.0, 1.0, 3.0))):
        for u in us:
            fdrip(F, u - 0.1, u + 0.1, 10.47, 0.75, 1.0, "rust", soft=0.07)
    for F, us in ((FRONT, (-3.66, 3.66)), (EAST, (1.75, 6.6)), (WEST, (-1.75, -6.6)), (REAR, (-2.6, 0.0, 2.6))):
        for u in us:
            fdrip(F, u - 0.1, u + 0.1, PIER_TOP - 0.75, 2.4, 0.95, "rust", soft=0.08)
    # scupper spouts: dark runoff and rust down the parapet, frieze and wall below each spout
    for sc in rec["scuppers"]:
        tx, tz = sc["tip"][0], sc["tip"][2]
        nx_, nz_ = sc["normal"][0], sc["normal"][2]
        if abs(nz_) > 0.5:
            for plane, top, L in ((PZF if nz_ > 0 else PZB, 11.9, 0.9), (ENT_ZF if nz_ > 0 else ENT_ZB, 11.2, 1.2), (ZF if nz_ > 0 else ZB, 10.4, 5.5)):
                drips.add((0, 0, nz_), plane, tx - 0.2, tx + 0.2, top, L, 1.0, "grime", 0.15)
                drips.add((0, 0, nz_), plane, tx - 0.12, tx + 0.12, top, L * 0.8, 0.7, "rust", 0.1)
        else:
            for plane, top, L in ((PPX * nx_, 11.9, 0.9), (ENT_X * nx_, 11.2, 1.2), (WX * nx_, 10.4, 5.5)):
                drips.add((nx_, 0, 0), plane, tz - 0.2, tz + 0.2, top, L, 1.0, "grime", 0.15)
                drips.add((nx_, 0, 0), plane, tz - 0.12, tz + 0.12, top, L * 0.8, 0.7, "rust", 0.1)
    # bronze nameplate, lamps, rear canopy, repair plate
    fdrip(FRONT, -npx, npx, npy0, 1.4, 0.7, soft=0.15)
    fdrip(FRONT, -npx + 0.3, npx - 0.3, npy0, 1.0, 0.35, "rust", soft=0.2)
    for x in (-2.45, 2.45):
        fdrip(FRONT, x - 0.09, x + 0.09, 3.1, 1.3, 0.8, "rust", soft=0.07)
    fdrip(REAR, -rx1 - 0.35, -rx0 + 0.35, 3.5, 0.8, 0.6, "rust", soft=0.1)
    fdrip(REAR, 1.15, 3.1, 1.45, 0.9, 0.8, "rust", soft=0.1)

    # old battle damage: scattered impact clusters, heavier by the portal and the front-west pier (the side that faced
    # the West Gate), soot above the rear window that burned before it was walled in and one east upper window
    scars = ScarSet(base=0.12)
    srng = random.Random(1918)
    scatter_impacts(scars, [(FRONT, -5.5, 5.5), (WEST, -8.5, 0.0), (EAST, 0.0, 8.5), (REAR, -5.5, 5.5)], 8, srng, BASE + 0.4, 8.0)
    scars.impact(tuple(FRONT.P(-4.7, 2.3, 0.1)), 1.9, 1.0)
    scars.impact(tuple(FRONT.P(-2.2, 1.4, 0.1)), 1.1, 0.9)
    scars.impact(tuple(WEST.P(-1.4, 3.2, 0.1)), 1.6, 1.0)
    scars.impact(tuple(FRONT.P(2.6, 5.0, 0.1)), 1.2, 0.8)
    scars.plume((0, 0, -1), ZB, -2.15, -0.85, 9.5, 2.6, 0.85)
    scars.plume((1, 0, 0), WX, -3.6, -2.5, 9.5, 2.2, 0.6)
    parts = [mas, trim, pod, metal, glass, roof] + ([sand] if LOD == 0 else [])
    finalize_parts(parts)
    ao = AOBaker(parts, ground_y=0.0, samples=24 if LOD == 0 else 12)
    objs = [
        mas.build(coll, ao=ao, drips=drips, ground_y=BASE, scars=scars),
        trim.build(coll, ao=ao, drips=drips, ground_y=BASE, scars=scars),
        pod.build(coll, ao=ao, drips=drips, ground_y=0.0, splash=0.25, scars=scars),
        metal.build(coll),
        glass.build(coll, flat=True),
        roof.build(coll),
    ]
    rec.setdefault("notes", []).append(f"LOD{lod}: vertex AO {ao.rays} rays")
    if LOD == 0:
        objs.append(sand.build(coll))
    else:
        sand.bm.free()

    # nameplate lettering (Blender space; reads left-to-right from the plaza)
    cu = bpy.data.curves.new(f"VH_Lettering_LOD{lod}", "FONT")
    cu.body = "VANGUARD HALL"
    cu.font = bpy.data.fonts.load(str(FONT), check_existing=True)
    cu.size = 0.40
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.extrude = 0.009
    cu.bevel_depth = 0.0025 if lod == 0 else 0.0
    cu.bevel_resolution = 1
    cu.space_character = 1.12
    cu.resolution_u = 6 if lod == 0 else 3
    txt = bpy.data.objects.new(f"VH_Lettering_LOD{lod}", cu)
    coll.objects.link(txt)
    txt.rotation_euler = (math.radians(90), 0, 0)
    c = rec["nameplate"]["centre"]
    txt.location = U((c[0], c[1] - 0.005, 0.085 + 0.0085))
    bpy.context.view_layer.update()
    for o in bpy.context.selected_objects:
        o.select_set(False)
    txt.select_set(True)
    bpy.context.view_layer.objects.active = txt
    bpy.ops.object.convert(target="MESH")
    txt = bpy.context.view_layer.objects.active
    # fit width to the plate
    xs_ = [(txt.matrix_world @ v.co).x for v in txt.data.vertices]
    width = max(xs_) - min(xs_)
    target = rec["nameplate"]["size"][0] - 0.36
    if width > target:
        txt.scale = (target / width, 1, target / width)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    txt.data.materials.clear()
    txt.data.materials.append(material("VH_Brass"))
    me = txt.data
    uvl = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uvl.data[li].uv = (co.x * 1.0, co.z * 1.0)
    colattr = me.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
    for d in colattr.data:
        d.color = (0.5, 0.5, 0.5, 1.0)
    for p in me.polygons:
        p.use_smooth = False
    triangulate(txt)
    objs.append(txt)
    rec.setdefault("lettering_width", {})[f"LOD{lod}"] = width

    # banner (Blender space): hangs from a rod in front of the central pilaster
    bw, by0, by1, bz = 1.1, 6.55, 9.94, 0.235
    nx_, ny_ = (14, 44) if lod == 0 else (6, 16)
    bm = bmesh.new()
    uvb = bm.loops.layers.uv.new("UVMap")
    colb = bm.loops.layers.color.new("Col")
    grid = []
    for j in range(ny_ + 1):
        row = []
        v = j / ny_
        for i in range(nx_ + 1):
            u = i / nx_
            bx = (u - 0.5) * bw
            bzv = lerp(by0, by1, v)
            hang = 1 - v
            fold = 0.022 * math.sin(u * math.pi * 6 + 0.7) * (0.35 + 0.65 * hang) + 0.012 * math.sin(u * math.pi * 11 + 2.1) * hang
            billow = 0.05 * hang ** 1.6 + 0.008 * math.sin(v * 9)
            row.append(bm.verts.new((bx * (1 - 0.03 * hang), -(bz + fold + billow), bzv)))
        grid.append(row)
    for j in range(ny_):
        for i in range(nx_):
            f = bm.faces.new([grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]])
            for l, (ii, jj) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                l[uvb].uv = (ii / nx_, jj / ny_)
                l[colb] = (0.5, 0.5, 0.5, 1.0)
    bm.normal_update()
    for f in bm.faces:
        if f.normal.y > 0:
            f.normal_flip()
    me = bpy.data.meshes.new(f"VH_Banner_LOD{lod}")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(material("VH_Banner"))
    ban = bpy.data.objects.new(f"VH_Banner_LOD{lod}", me)
    coll.objects.link(ban)
    for p in me.polygons:
        p.use_smooth = True
    objs.append(ban)
    # banner rod + brackets (Unity space via a small part)
    rod = Part(f"VH_BannerRod_LOD{lod}")
    rod.cyl((-0.66, 9.98, bz), (0.66, 9.98, bz), 0.018, "VH_Steel", 8)
    for x in (-0.62, 0.62):
        rod.box((x - 0.012, 9.9, 0.12), (x + 0.012, 10.02, bz + 0.02), "VH_Steel")
    for x in (-0.68, 0.68):
        rod.sphere((x, 9.98, bz), 0.03, "VH_Steel", 8)
    objs.append(rod.build(coll))

    tri = 0
    for o in objs:
        tri += sum(len(p.vertices) - 2 for p in o.data.polygons)
    rec["triangles"] = tri
    rec["objects"] = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs}
    return coll, objs, rec


def export(objs, path):
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True, export_yup=True,
                              export_image_format="NONE", export_tangents=True, export_normals=True, export_apply=True,
                              export_vertex_color="ACTIVE", export_extras=False, export_materials="EXPORT")


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    report = {"source": "art/vanguard_hall_20260930/author_vanguard_hall.py", "date": "2026-09-30",
              "units": "Unity metres local to the hall root; root at world (-10, 0, -26.55)", "lods": {}}
    for lod in (0, 1):
        coll, objs, rec = build(lod)
        export(objs, OUT / f"VanguardHall_LOD{lod}.glb")
        report["lods"][f"LOD{lod}"] = {"triangles": rec["triangles"], "objects": rec["objects"]}
        if lod == 0:
            report.update({k: v for k, v in rec.items() if k not in ("triangles", "objects")})
        print(f"LOD{lod}: {rec['triangles']} triangles", rec["objects"], flush=True)
    (OUT / "vanguard-hall.json").write_text(json.dumps(report, indent=1))
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "vanguard-hall-source.blend"))


main()
