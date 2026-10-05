"""The player's home (5 October 2026): variant P of the converted 20 ft container home on Ward's south wall.

Carl (5 Oct 2026, ~02:40): "we need a place to store our loot" -> rent one of the container homes: "a locker and shelf
rack as the stash, a bunk as a rest and save point, a lease you get from Linn or the Wardens". Design and work split:
art/ward_home_20261005/PROGRESS.md.

Used by art/ward_buildings_20261003/author_buildings.py wall_home(lod, "P") (key `homep`): the exterior is variant A
(rust container, stone pads, step, planter, madder awning, roof solar, drum, AC, laundry, porch light, impact scar)
with these differences, all made here or guarded by `variant == "P"` so A/B/C are unchanged:
  * shell(): the container is built with a real cut-in door opening (welded box-section frame, steel threshold, kick
    plate, frame-side hinge knuckles) and a real glazed window (the 3 Oct box frames were solid slabs);
  * the door leaf is its own object, WallHomeP_DoorLeaf_LOD<n>, whose origin is the hinge axis at the leaf's foot
    (HINGE): rotate it about local +Y; closed yaw 0, open yaw -100 (outward, over the step);
  * the awning's street edge is 0.15 m higher (the opening leaf clears it) and a lower stone step is added (ground ->
    0.15 -> 0.30 -> floor 0.50: every rise within the player's 0.3 m step offset);
  * no solid COL_Container: walls with a door gap, roof, floor and furniture colliders instead.
build(s) adds the fitted interior and wraps s.finish so the interior parts and the leaf are exported with the exterior.

Building-local Unity metres: root = container centre at ground, X along the container (west -X, east +X), +Z = street,
Y up. Interior (lining faces): x -2.913..2.953, z -1.103..1.103, floor 0.50 (boards on the 0.48 steel plate), ceiling
2.763: 5.87 x 2.21 m, 2.26 m clear. Bunk at the west end along the back wall, stash locker on the back wall facing the
door, slotted-angle rack beside it, fold-down table under the window, services and life details round the walls.
"""
import math
import sys

import bmesh
from mathutils import Matrix, Vector

import ward_masonry as WM
from ward_masonry import Part, Frame, lerp, drng, lettering, tri_count, U, nz

_AB = sys.modules.get("author_buildings") or sys.modules["__main__"]

# ------------------------------------------------------------------ dimensions (building-local metres)
Y0 = 0.32                      # container bottom (on the stone pads)
PLATE = 0.48                   # top of the steel floor plate
FY = 0.50                      # top of the floor boards: the walkable interior floor
X0, X1, Z0, Z1 = -3.03, 3.03, -1.22, 1.22          # container outer
SB, SF, SW, SE = -1.15, 1.15, -2.96, 3.00          # shell inner faces (corrugation troughs, end doors)
BD, PT = 0.035, 0.012          # batten depth, lining sheet thickness
LB, LF, LW, LE = SB + BD + PT, SF - BD - PT, SW + BD + PT, SE - BD - PT   # lining faces -1.103 1.103 -2.913 2.953
ROOF = 2.81                    # underside of the roof plate
LC = ROOF - BD - PT            # 2.763: ceiling lining face
PX, PZ = 2.87, 1.06            # inner faces of the corner posts (|x|, |z|)
DOOR = (0.90, 1.85, 2.44)      # clear opening x0, x1, head (threshold top 0.502)
DOOR_FRAME = (0.84, 1.91, 2.50)
WIN = (-1.90, -0.70, 1.43, 2.21)          # glass x0, x1, y0, y1
WIN_FRAME = (-1.96, -0.64, 1.37, 2.27)
HINGE = (0.86, 0.51, 1.277)    # door hinge axis at the leaf's foot
LEAF = dict(x0=0.875, x1=1.885, y0=0.51, y1=2.46, z0=1.223, z1=1.268)
OPEN_YAW = -176.0              # Unity yaw (deg) of the leaf object when open: swings outward (+X -> +Z -> -X) and parks
#                                flat against the container face west of the door, 6-14 cm off the corrugation (5 Oct:
#                                at -100 it stood across the only approach, the lane west of Nanofab 2's pier)
BED = dict(x0=-2.86, x1=-0.92, z0=-1.05, z1=-0.24, rail=FY + 0.34, head=FY + 0.84, foot=FY + 0.56)
MATT = dict(x0=-2.818, x1=-0.962, z0=-1.043, z1=-0.247, y0=BED["rail"] - 0.035, y1=BED["rail"] + 0.105)   # inside the posts
LOCKER = dict(x0=0.65, x1=1.55, z0=LB, z1=-0.60, y0=FY, y1=FY + 1.9)
RACK = dict(x0=1.66, x1=2.86, z0=LB, z1=-0.65, levels=(0.56, 1.14, 1.64, 2.12), top=2.30)
TABLE = dict(x0=-1.88, x1=-0.76, z0=0.69, z1=LF, top=FY + 0.72)
STOOL = (-1.25, 0.86)
SIDE_CRATE = dict(x0=-2.89, x1=-2.49, z0=-0.20, z1=0.20, h=0.46)
TRAY = dict(x0=-1.75, x1=1.25, z=0.0, y=LC - 0.03)       # ceiling cable tray (top of the rim)
BULB = (0.0, 2.56, 0.0)
JBOX = (-0.40, 1.85)            # junction box on the front wall (x, y): behind the exterior one
SHELF_Y = 2.0                   # shelf over the bunk


# ------------------------------------------------------------------ small helpers
def B(part, lo, hi, mat, bid=0, skip=()):
    return part.box(tuple(lo), tuple(hi), mat, bid, skip)


def orient(f, hint):
    f.normal_update()
    if f.normal.dot(Vector(hint)) < 0:
        f.normal_flip()


def poly(part, pts, mat, hint):
    """One flat n-gon (a decal-like patch made of geometry), normal towards hint."""
    vs = [part.bm.verts.new(Vector(p)) for p in pts]
    f = part.bm.faces.new(vs)
    f.material_index = part.mi(mat)
    orient(f, hint)
    return f


def blob(F, uc, yc, ru, rv, key, n=9, jag=0.4):
    """Irregular outline round (uc, yc) on frame F's plane (returns (u, y) pairs)."""
    rr = drng("blob", key)
    out = []
    for i in range(n):
        a = 2 * math.pi * i / n + rr.uniform(-0.2, 0.2)
        r = 1 - jag * rr.random()
        out.append((uc + math.cos(a) * ru * r, yc + math.sin(a) * rv * r))
    return out


def patch(part, F, uc, yc, d, ru, rv, mat, key, n=9, jag=0.4):
    """Paint chip / rust bloom / scuff on frame F at depth d (a few tenths of a mm proud of the surface)."""
    return poly(part, [F.P(u, y, d) for u, y in blob(F, uc, yc, ru, rv, key, n, jag)], mat, F.n)


def hpatch(part, xc, y, zc, rx, rz, mat, key, n=9, jag=0.4, up=1):
    """Horizontal patch (floor scuff, rust on a shelf), facing +Y (up=1) or -Y."""
    rr = drng("hpatch", key)
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n + rr.uniform(-0.2, 0.2)
        r = 1 - jag * rr.random()
        pts.append((xc + math.cos(a) * rx * r, y, zc + math.sin(a) * rz * r))
    return poly(part, pts, mat, (0, up, 0))


def screw(part, F, u, y, d, r=0.0055):
    F.box(part, u - r, u + r, y - r, y + r, d, d + 0.0016, "VH_Steel", skip=("s0",))


def loft(part, rings, mat, cap0=True, cap1=True):
    """Closed loft through rings (lists of Vectors, same length, same winding)."""
    bm = part.bm
    vr = [[bm.verts.new(Vector(p)) for p in ring] for ring in rings]
    n = len(rings[0])
    fs = []
    for a, b in zip(vr, vr[1:]):
        for i in range(n):
            j = (i + 1) % n
            fs.append(bm.faces.new([a[i], a[j], b[j], b[i]]))
    if cap0:
        fs.append(bm.faces.new(vr[0][::-1]))
    if cap1:
        fs.append(bm.faces.new(vr[-1]))
    mi = part.mi(mat)
    for f in fs:
        f.material_index = mi
    bmesh.ops.recalc_face_normals(bm, faces=fs)
    return fs


def ring(c, r1, r2, n, ax="y", rot=0.0, wob=None):
    """Ellipse ring round c in the plane normal to axis ax (radii r1, r2); wob(i, a) -> radius factor."""
    c = Vector(c)
    out = []
    for i in range(n):
        a = rot + 2 * math.pi * i / n
        k = wob(i, a) if wob else 1.0
        ca, sa = math.cos(a) * r1 * k, math.sin(a) * r2 * k
        if ax == "y":
            out.append(c + Vector((ca, 0, sa)))
        elif ax == "x":
            out.append(c + Vector((0, sa, ca)))
        else:
            out.append(c + Vector((ca, sa, 0)))
    return out


def sheet(part, P, mat, t, hint):
    """Cloth sheet with thickness t from a grid of points P[i][j] (Unity coords). hint(p) gives the 'outside' direction
    used to orient the top layer. Builds top and bottom layers and stitches the border."""
    bm = part.bm
    ni, nj = len(P), len(P[0])

    def nrm(i, j):
        a = P[min(i + 1, ni - 1)][j] - P[max(i - 1, 0)][j]
        b = P[i][min(j + 1, nj - 1)] - P[i][max(j - 1, 0)]
        n = a.cross(b)
        if n.length < 1e-9:
            n = Vector(hint(P[i][j]))
        n.normalize()
        if n.dot(Vector(hint(P[i][j]))) < 0:
            n = -n
        return n
    N = [[nrm(i, j) for j in range(nj)] for i in range(ni)]
    top = [[bm.verts.new(P[i][j] + N[i][j] * t / 2) for j in range(nj)] for i in range(ni)]
    bot = [[bm.verts.new(P[i][j] - N[i][j] * t / 2) for j in range(nj)] for i in range(ni)]
    mi = part.mi(mat)
    fs = []
    for i in range(ni - 1):
        for j in range(nj - 1):
            f = bm.faces.new([top[i][j], top[i + 1][j], top[i + 1][j + 1], top[i][j + 1]])
            c = (P[i][j] + P[i + 1][j + 1]) / 2
            orient(f, N[i][j])
            g = bm.faces.new([bot[i][j], bot[i][j + 1], bot[i + 1][j + 1], bot[i + 1][j]])
            orient(g, -N[i][j])
            fs += [f, g]
    border = [(i, 0) for i in range(ni)] + [(ni - 1, j) for j in range(1, nj)] + [(i, nj - 1) for i in range(ni - 2, -1, -1)] + \
             [(0, j) for j in range(nj - 2, 0, -1)]
    for k in range(len(border)):
        (i0, j0), (i1, j1) = border[k], border[(k + 1) % len(border)]
        f = bm.faces.new([top[i0][j0], top[i1][j1], bot[i1][j1], bot[i0][j0]])
        mid = (P[i0][j0] + P[i1][j1]) / 2
        cen = P[ni // 2][nj // 2]
        orient(f, mid - cen)
        fs.append(f)
    for f in fs:
        f.material_index = mi
    return fs


def grid_surface(part, pt, nu, nv, mat, hint, back=None):
    """Lumpy surface patch pt(a, b) for a, b in [0, 1] (insulation batts). back(a, b) -> point closes it as a slab."""
    bm = part.bm
    G = [[bm.verts.new(pt(i / nu, j / nv)) for j in range(nv + 1)] for i in range(nu + 1)]
    mi = part.mi(mat)
    fs = []
    for i in range(nu):
        for j in range(nv):
            f = bm.faces.new([G[i][j], G[i + 1][j], G[i + 1][j + 1], G[i][j + 1]])
            orient(f, hint)
            fs.append(f)
    if back is not None:
        edge = [(i, 0) for i in range(nu + 1)] + [(nu, j) for j in range(1, nv + 1)] + [(i, nv) for i in range(nu - 1, -1, -1)] + \
               [(0, j) for j in range(nv - 1, 0, -1)]
        bk = {k: bm.verts.new(back(k[0] / nu, k[1] / nv)) for k in edge}
        cen = pt(0.5, 0.5)
        for k in range(len(edge)):
            a, b = edge[k], edge[(k + 1) % len(edge)]
            f = bm.faces.new([G[a[0]][a[1]], G[b[0]][b[1]], bk[b], bk[a]])
            orient(f, (G[a[0]][a[1]].co + G[b[0]][b[1]].co) / 2 - cen)
            fs.append(f)
    for f in fs:
        f.material_index = mi
    return fs


# ------------------------------------------------------------------ frames for the lining (n into the room)
WALLS = {
    "back": Frame((0, 0, SB), (1, 0, 0), (0, 0, 1)),        # u = x
    "front": Frame((0, 0, SF), (-1, 0, 0), (0, 0, -1)),     # u = -x
    "west": Frame((SW, 0, 0), (0, 0, -1), (1, 0, 0)),       # u = -z
    "east": Frame((SE, 0, 0), (0, 0, 1), (-1, 0, 0)),       # u = z
}
# openings in wall frame coordinates (u0, u1, y0, y1)
HOLES = {"front": [(-DOOR_FRAME[1], -DOOR_FRAME[0], FY - 0.05, DOOR_FRAME[2]),
                   (-WIN_FRAME[1], -WIN_FRAME[0], WIN_FRAME[2], WIN_FRAME[3])]}
# lining sheets per wall: (u0, u1, [(y0, y1, material or None for a missing sheet), ...])
LINING = {
    "back": [(-PX, -1.67, [(FY, LC, "WG_Plywood")]),
             (-1.67, -0.47, [(FY, 1.55, "WG_Plywood"), (1.55, LC, "WS_PanelDark")]),
             (-0.47, 0.73, [(FY, 1.58, "WG_Plywood"), (1.58, LC, None)]),
             (0.73, 1.93, [(FY, LC, "WG_Plywood")]),
             (1.93, PX, [(FY, 1.3, "WG_Plywood"), (1.3, LC, "WG_Plywood")])],
    "front": [(-PX, -1.91, [(FY, LC, "WG_Plywood")]),
              (-1.91, -0.84, [(FY, LC, "WG_Plywood")]),
              (-0.84, 0.64, [(FY, 1.2, "WG_PlateSteel"), (1.2, LC, "WG_Plywood")]),
              (0.64, 1.96, [(FY, LC, "WG_Plywood")]),
              (1.96, PX, [(FY, LC, "WG_Plywood")])],
    "west": [(-PZ, 0.0, [(FY, 1.3, "WG_Plywood"), (1.3, LC, "WS_PanelDark")]),
             (0.0, PZ, [(FY, LC, "WG_Plywood")])],
    "east": [(-PZ, 0.0, [(FY, LC, "WG_Plywood")]),
             (0.0, PZ, [(FY, 1.1, None), (1.1, LC, "WG_Plywood")])],
}
CEILING = [(LW, -1.7, "WG_Plywood"), (-1.7, -0.5, "WG_Plywood"), (-0.5, 0.7, "WG_Plywood"), (0.7, 1.9, "WG_Plywood"),
           (1.9, LE, None)]


# ====================================================================== exterior shell with real openings
def shell(s, mat, lod):
    """container_box() of author_buildings for the player's home: the same 20 ft container, but the front door and the
    window are real openings in the corrugation (welded box-section frames running back to the lining, glass, bars),
    with a steel threshold, a kick plate on the sill rail and the frame halves of the door hinges."""
    corr = _AB.corrugated_wall
    m, hd = s.metal, s.hard
    y0, H = Y0, 2.59
    x0, x1, z0, z1 = X0, X1, Z0, Z1
    cz = 0.0
    Ff = Frame((0, 0, z1), (1, 0, 0), (0, 0, 1))
    Fb = Frame((0, 0, z0), (-1, 0, 0), (0, 0, -1))
    Fr = Frame((x1, 0, 0), (0, 0, -1), (1, 0, 0))
    Fl = Frame((x0, 0, 0), (0, 0, 1), (-1, 0, 0))
    yb, yt = y0 + 0.16, y0 + H - 0.1
    fx0, fx1, ftop = DOOR_FRAME
    wx0, wx1, wy0, wy1 = WIN_FRAME
    corr(m, Ff, x0 + 0.1, wx0, yb, yt, -0.04, mat, lod=lod)
    corr(m, Ff, wx0, wx1, yb, wy0, -0.04, mat, lod=lod)
    corr(m, Ff, wx0, wx1, wy1, yt, -0.04, mat, lod=lod)
    corr(m, Ff, wx1, fx0, yb, yt, -0.04, mat, lod=lod)
    corr(m, Ff, fx1, x1 - 0.1, yb, yt, -0.04, mat, lod=lod)
    corr(m, Ff, fx0, fx1, ftop - 0.03, yt, -0.04, mat, lod=lod)
    corr(m, Fb, -x1 + 0.1, -x0 - 0.1, yb, yt, -0.04, mat, lod=lod)
    corr(m, Fl, z0 + 0.1, z1 - 0.1, yb, yt, -0.04, mat, lod=lod)
    for (a, b) in ((-z1 + 0.08, -cz - 0.01), (-cz + 0.01, -z0 - 0.08)):      # cargo doors at the east end (closed)
        Fr.box(m, a, b, yb, yt, -0.03, 0.01, mat)
        for k in range(1, 4):
            uu = lerp(a, b, k / 4)
            Fr.box(m, uu - 0.03, uu + 0.03, yb + 0.05, yt - 0.05, 0.01, 0.035, mat)
        for uu in (lerp(a, b, 0.3), lerp(a, b, 0.7)):
            m.cyl(tuple(Fr.P(uu, yb + 0.1, 0.06)), tuple(Fr.P(uu, yt - 0.1, 0.06)), 0.018, "VH_Steel", 6)
    m.box((x0 + 0.05, y0 + 0.02, z0 + 0.05), (x1 - 0.05, y0 + 0.16, z1 - 0.05), "WB_BlackSteel")
    m.box((x0 + 0.04, yt, z0 + 0.04), (x1 - 0.04, y0 + H - 0.02, z1 - 0.04), mat)
    for (xx, zz) in ((x0, z0), (x1, z0), (x1, z1), (x0, z1)):
        sx, sz = (1 if xx < 0 else -1), (1 if zz < cz else -1)
        m.box((min(xx, xx + sx * 0.16), y0, min(zz, zz + sz * 0.16)), (max(xx, xx + sx * 0.16), y0 + H, max(zz, zz + sz * 0.16)), mat)
        for yy in (y0, y0 + H - 0.12):
            m.box((min(xx, xx + sx * 0.18), yy, min(zz, zz + sz * 0.18)), (max(xx, xx + sx * 0.18), yy + 0.12, max(zz, zz + sz * 0.18)), "WG_RustSteel")
    for zz in (z0, z1):
        m.box((x0 + 0.1, y0, min(zz, zz + (0.12 if zz < cz else -0.12))), (x1 - 0.1, y0 + 0.17, max(zz, zz + (0.12 if zz < cz else -0.12))), mat)
        m.box((x0 + 0.1, y0 + H - 0.12, min(zz, zz + (0.1 if zz < cz else -0.1))), (x1 - 0.1, y0 + H, max(zz, zz + (0.1 if zz < cz else -0.1))), mat)
    # ---- door: welded box-section frame from the lining (z 1.095) to the container's rail plane (z 1.22)
    dz0, dz1 = 1.095, 1.22
    B(m, (fx0, PLATE - 0.01, dz0), (DOOR[0], ftop, dz1), "WB_BlackSteel")
    B(m, (DOOR[1], PLATE - 0.01, dz0), (fx1, ftop, dz1), "WB_BlackSteel")
    B(m, (DOOR[0], DOOR[2], dz0), (DOOR[1], ftop, dz1), "WB_BlackSteel")
    # door stops (the overlay leaf closes against the frame face; a 15 mm stop strip inside it keeps the draught out)
    for (a, b) in ((DOOR[0], DOOR[0] + 0.015), (DOOR[1] - 0.015, DOOR[1])):
        B(m, (a, FY + 0.01, 1.19), (b, DOOR[2], dz1), "WB_BlackSteel")
    B(m, (DOOR[0], DOOR[2] - 0.015, 1.19), (DOOR[1], DOOR[2], dz1), "WB_BlackSteel")
    # threshold: worn tread plate over the sill rail, nosing out over the step; kick plate on the rail face below it
    B(m, (fx0, 0.47, 1.06), (fx1, 0.502, 1.31), "WS_Deck")
    B(m, (fx0 - 0.04, 0.34, z1), (fx1 + 0.04, 0.462, z1 + 0.006), "VH_Steel")
    if lod == 0:
        for xx in (fx0 - 0.01, (fx0 + fx1) / 2, fx1 + 0.01):
            for yy in (0.36, 0.44):
                hd.sphere((xx, yy, z1 + 0.006), 0.009, "VH_Steel", 6, hemi_axis=(0, 0, 1))
        # tread worn bright down the middle where boots land
        hpatch(m, (DOOR[0] + DOOR[1]) / 2, 0.5024, 1.17, 0.36, 0.08, "VH_Steel", "thr", n=11, jag=0.25)
    # frame halves of the three barrel hinges (knuckles above and below the leaf's), welded to the jamb face
    hx, hz = HINGE[0], HINGE[2]
    for hy in hinge_heights():
        for (a, b) in ((hy - 0.075, hy - 0.037), (hy + 0.037, hy + 0.075)):
            m.cyl((hx, a, hz), (hx, b, hz), 0.014, "VH_Steel", 10)
        B(m, (fx0 + 0.002, hy - 0.075, dz1), (hx + 0.006, hy + 0.075, hz - 0.004), "VH_Steel")
    # ---- window: real opening, box-section frame (as A's, proud of the corrugation, carrying shutter and hood)
    wd0, wd1 = 1.095, z1 + 0.06
    B(m, (wx0, wy0, wd0), (WIN[0], wy1, wd1), "WB_BlackSteel")
    B(m, (WIN[1], wy0, wd0), (wx1, wy1, wd1), "WB_BlackSteel")
    B(m, (WIN[0], wy0, wd0), (WIN[1], WIN[2], wd1), "WB_BlackSteel")
    B(m, (WIN[0], WIN[3], wd0), (WIN[1], wy1, wd1), "WB_BlackSteel")
    B(s.glass, (WIN[0], WIN[2], 1.187), (WIN[1], WIN[3], 1.193), "WS_ClearGlass")
    for side in (1.18, 1.20):          # glazing beads either side of the pane
        za, zb = (side - 0.007, side) if side < 1.19 else (side, side + 0.007)
        B(m, (WIN[0], WIN[2], za), (WIN[1], WIN[2] + 0.018, zb), "WB_BlackSteel")
        B(m, (WIN[0], WIN[3] - 0.018, za), (WIN[1], WIN[3], zb), "WB_BlackSteel")
        B(m, (WIN[0], WIN[2], za), (WIN[0] + 0.018, WIN[3], zb), "WB_BlackSteel")
        B(m, (WIN[1] - 0.018, WIN[2], za), (WIN[1], WIN[3], zb), "WB_BlackSteel")
    wu0, wu1 = WIN[0], WIN[1]
    for k in range(1, 6):
        uu = lerp(wu0, wu1, k / 6)
        m.cyl(tuple(Ff.P(uu, y0 + 1.08, 0.03)), tuple(Ff.P(uu, y0 + 1.92, 0.03)), 0.011, "VH_Steel", 6)
    Ff.box(m, wu0 - 0.68, wu0 - 0.08, y0 + 1.05, y0 + 1.95, 0.06, 0.09, "WS_PaintOlive")
    if lod == 0:
        for k in range(8):
            yy = y0 + 1.1 + k * 0.105
            Ff.box(m, wu0 - 0.64, wu0 - 0.12, yy, yy + 0.05, 0.09, 0.105, "WS_PaintOlive")
    Ff.box(m, wu0 - 0.15, wu1 + 0.15, y0 + 2.0, y0 + 2.04, 0.0, 0.32, "WB_BlackSteel")
    s.rec.setdefault("containers", []).append({"tag": "lower", "centre": [0.0, y0, 0.0]})


def hinge_heights():
    return (0.75, 1.30, 2.25)       # clear of the stiffeners (0.82, 1.47, 2.12)


# ====================================================================== door leaf (own object, origin at the hinge)
def door_leaf(s, lp):
    """Overlay steel door: teal-painted plate on a channel frame, three stiffeners (A's), lever handles both sides with a
    keyhole, barrel-hinge knuckles and straps; paint worn round the handle, rust and boot scuffs along the foot."""
    L, lod = LEAF, s.lod
    x0, x1, y0, y1, z0, z1 = L["x0"], L["x1"], L["y0"], L["y1"], L["z0"], L["z1"]
    B(lp, (x0, y0, z0), (x1, y1, z1), "WB_TankTeal")
    Fo = Frame((0, 0, z1), (1, 0, 0), (0, 0, 1))
    Fi = Frame((0, 0, z0), (-1, 0, 0), (0, 0, -1))
    for yy in (0.82, 1.47, 2.12):                         # stiffeners (A's heights)
        B(lp, (x0 + 0.06, yy - 0.025, z1), (x1 - 0.06, yy + 0.025, z1 + 0.018), "WB_BlackSteel")
    hx, hz = HINGE[0], HINGE[2]
    for hy in hinge_heights():
        lp.cyl((hx, hy - 0.035, hz), (hx, hy + 0.035, hz), 0.014, "VH_Steel", 10)
        B(lp, (hx, hy - 0.03, z1), (x0 + 0.17, hy + 0.03, z1 + 0.006), "VH_Steel")
    # outside lever handle on a rose, keyhole below; inside lever
    hxr = x1 - 0.105
    B(lp, (hxr - 0.025, 1.27, z1), (hxr + 0.025, 1.43, z1 + 0.006), "VH_Steel")
    lp.cyl((hxr, 1.38, z1 + 0.006), (hxr, 1.38, z1 + 0.05), 0.009, "VH_Steel", 8)
    B(lp, (hxr - 0.125, 1.369, z1 + 0.036), (hxr + 0.012, 1.391, z1 + 0.056), "VH_Steel")
    B(lp, (hxr - 0.006, 1.295, z1 + 0.006), (hxr + 0.006, 1.315, z1 + 0.007), "VH_Dark")
    B(lp, (hxr - 0.025, 1.27, z0 - 0.006), (hxr + 0.025, 1.43, z0), "VH_Steel")
    lp.cyl((hxr, 1.38, z0 - 0.006), (hxr, 1.38, z0 - 0.05), 0.009, "VH_Steel", 8)
    B(lp, (hxr - 0.125, 1.369, z0 - 0.056), (hxr + 0.012, 1.391, z0 - 0.036), "VH_Steel")
    if lod > 0:
        return
    # rim: welded flat bar round the outer face
    for (a, b, c, d) in ((x0, x1, y0, y0 + 0.035), (x0, x1, y1 - 0.035, y1), (x0, x0 + 0.035, y0, y1), (x1 - 0.035, x1, y0, y1)):
        B(lp, (a, c, z1), (b, d, z1 + 0.004), "WB_TankTeal")
    for yy in (0.82, 1.47, 2.12):
        x = x0 + 0.1
        while x < x1 - 0.08:
            for dy in (-0.015, 0.015):
                lp.sphere((x, yy + dy, z1 + 0.018), 0.006, "VH_Steel", 6, hemi_axis=(0, 0, 1))
            x += 0.18
    # wear: bare steel round the handle and along the pull edge, rust and boot scuffs at the foot, drip rust under ribs
    patch(lp, Fo, hxr - 0.02, 1.36, 0.0045, 0.075, 0.11, "VH_Steel", "leaf_h", n=11)
    patch(lp, Fo, x1 - 0.05, 1.6, 0.0045, 0.03, 0.22, "VH_Steel", "leaf_e", n=9, jag=0.5)
    patch(lp, Fi, -(hxr - 0.02), 1.36, 0.0005, 0.07, 0.1, "VH_Steel", "leaf_hi", n=11)
    rr = drng("leaf_foot")
    # rust creeping up from the foot: a continuous band with a ragged top edge
    n = 28
    us = [lerp(x0 + 0.036, x1 - 0.036, i / n) for i in range(n + 1)]
    tops = [y0 + 0.036 + 0.02 + 0.05 * (0.5 + 0.5 * nz((u, 0, 0), 9, 2.0)) + rr.uniform(0, 0.02) for u in us]
    for i in range(n):
        poly(lp, [Fo.P(us[i], y0 + 0.036, 0.0045), Fo.P(us[i + 1], y0 + 0.036, 0.0045), Fo.P(us[i + 1], tops[i + 1], 0.0045),
                  Fo.P(us[i], tops[i], 0.0045)], "WG_RustSteel", Fo.n)
    for k in range(5):
        patch(lp, Fo, rr.uniform(x0 + 0.25, x1 - 0.25), rr.uniform(y0 + 0.12, y0 + 0.4), 0.0045, rr.uniform(0.03, 0.07),
              rr.uniform(0.006, 0.014), "VH_Steel", ("kick", k), n=7, jag=0.3)
    for yy in (0.82, 1.47):
        for k in range(3):
            uc = rr.uniform(x0 + 0.15, x1 - 0.15)
            poly(lp, [Fo.P(uc - 0.012, yy - 0.026, 0.0045), Fo.P(uc + 0.012, yy - 0.026, 0.0045),
                      Fo.P(uc + 0.004, yy - 0.026 - rr.uniform(0.12, 0.3), 0.0045)], "WG_RustSteel", Fo.n)


# ====================================================================== lining (walls)
def lining(s):
    part, lod = s.ilin, s.lod
    for wall, sheets in LINING.items():
        F = WALLS[wall]
        holes = HOLES.get(wall, [])
        for si, (u0, u1, rows) in enumerate(sheets):
            for ri, (y0, y1, mat) in enumerate(rows):
                key = (wall, si, ri)
                rr = drng("lin", key)
                if mat is None:
                    missing_bay(s, F, u0, u1, y0, y1, key)
                    continue
                g = 0.0025 if lod == 0 else 0.0
                for ya, yb_ in _bands(y0, y1, holes):
                    for (a, b) in WM.course_intervals(u0, u1, holes, ya, yb_):
                        d1 = BD + PT + rr.uniform(-0.0015, 0.0015)
                        F.box(part, a + g, b - g, ya + g, yb_ - g, BD, d1, mat, skip=("s0",))
                if lod == 0 and mat != "WG_PlateSteel":
                    rows_y = [y0 + 0.05, (y0 + y1) / 2, y1 - 0.05] if y1 - y0 > 0.9 else [y0 + 0.04, y1 - 0.04]
                    cols = [u0 + 0.03, (u0 + u1) / 2, u1 - 0.03]
                    for yy in rows_y:
                        for uu in cols:
                            if not any(h[0] - 0.02 < uu < h[1] + 0.02 and h[2] - 0.02 < yy < h[3] + 0.02 for h in holes):
                                screw(s.ihard, F, uu + rr.uniform(-0.01, 0.01), yy + rr.uniform(-0.01, 0.01), BD + PT)
                if mat == "WG_PlateSteel" and lod == 0:
                    # riveted steel patch: rivet rows round the edge, a weld seam where it was cut to fit
                    u = u0 + 0.04
                    while u < u1 - 0.03:
                        for yy in (y0 + 0.04, y1 - 0.04):
                            s.ihard.sphere(tuple(F.P(u, yy, BD + PT + 0.001)), 0.008, "VH_Steel", 6, hemi_axis=tuple(F.n))
                        u += 0.12
                    for k in range(3):
                        patch(part, F, rr.uniform(u0 + 0.2, u1 - 0.2), rr.uniform(y0 + 0.15, y1 - 0.15), BD + PT + 0.0004,
                              rr.uniform(0.05, 0.12), rr.uniform(0.04, 0.09), "WG_RustSteel", ("plate", k))
        # skirting along the foot of the wall (not across the door)
        if wall in ("back", "front"):
            spans = [(-PX, PX)] if wall == "back" else [(-PX, -DOOR_FRAME[1]), (-DOOR_FRAME[0], PX)]
        else:
            spans = [(-PZ, PZ)]
        for (a, b) in spans:
            F.box(part, a, b, FY, FY + 0.075, BD + PT, BD + PT + 0.016, "SS_Timber", skip=("s0", "bottom"))
    # corner trims where the lining meets the posts and the ceiling meets the walls are left as plain butt joints
    # (as a home conversion would be); the post noses show in the four corners.


def _bands(y0, y1, holes):
    cuts = sorted({y0, y1} | {h[2] for h in holes if y0 < h[2] < y1} | {h[3] for h in holes if y0 < h[3] < y1})
    return list(zip(cuts, cuts[1:]))


def missing_bay(s, F, u0, u1, y0, y1, key):
    """A lining sheet torn off: the battens show, mineral-wool batts between them (one sagging, one partly pulled
    away) and the container's corrugation behind."""
    part, lod = s.ilin, s.lod
    rr = drng("bay", key)
    bw = 0.045
    # battens: verticals at the bay edges, a horizontal one across the middle
    for (a, b) in ((u0, u0 + bw), (u1 - bw, u1)):
        F.box(part, a, b, y0 - 0.02, y1, 0.0, BD, "SS_Timber", skip=("s0",))
    # the back bay's middle batten carries the peg rail (packed out flush with the lining)
    ym = 2.065 if wall_is(F, "back") else ((y0 + y1) / 2 if y1 - y0 > 0.8 else None)
    if ym:
        F.box(part, u0 + bw, u1 - bw, ym - 0.022, ym + 0.022, 0.0, BD + (PT if wall_is(F, "back") else 0.0), "SS_Timber", skip=("s0",))
    # torn sheet edge left on the battens (a jagged strip of ply still screwed on)
    poly(part, [F.P(u0, y0, BD + PT), F.P(u1, y0, BD + PT), F.P(u1, y0 + rr.uniform(0.02, 0.06), BD + PT),
                F.P(lerp(u0, u1, 0.6), y0 + rr.uniform(0.05, 0.1), BD + PT), F.P(lerp(u0, u1, 0.25), y0 + rr.uniform(0.01, 0.04), BD + PT),
                F.P(u0, y0 + rr.uniform(0.03, 0.08), BD + PT)], "WG_Plywood", F.n)
    nu, nv = (10, 8) if lod == 0 else (2, 2)
    a0, a1 = u0 + bw, u1 - bw
    if wall_is(F, "east"):            # kicked through low down: the batt is half gone, the end door shows
        b0, b1 = y0 + 0.02, (ym or y1) - 0.022
        top = lerp(b0, b1, 0.55)
        grid_surface(part, lambda a, b: _batt(F, lerp(a0, a1, a), lerp(top, b1, b), rr, 0.6), nu, nv // 2, "HP_Insulation", F.n,
                     back=lambda a, b: F.P(lerp(a0, a1, a), lerp(top, b1, b), 0.002))
        # torn tufts hanging at the edge of the remaining batt
        for k in range(5 if lod == 0 else 0):
            uc = lerp(a0 + 0.05, a1 - 0.05, k / 4)
            c = F.P(uc, top - 0.02, BD * 0.6)
            part.sphere(tuple(c), 0.03, "HP_Insulation", 6)
        return
    # back wall upper bay: the lower batt is in place; the upper one has sagged out of its bay and hangs forward
    if ym:
        grid_surface(part, lambda a, b: _batt(F, lerp(a0, a1, a), lerp(y0 + 0.005, ym - 0.022, b), rr, 0.0), nu, nv // 2, "HP_Insulation",
                     F.n, back=lambda a, b: F.P(lerp(a0, a1, a), lerp(y0 + 0.005, ym - 0.022, b), 0.002))
        top0, top1 = ym + 0.022, y1 - 0.02
        sag = 0.22

        def hang(a, b):
            u = lerp(a0, a1, a)
            y = lerp(top0, top1 - sag, b)
            p = _batt(F, u, y, rr, 0.0)
            # peeled forward at the top
            return p + F.n * (0.06 * max(0.0, b - 0.6) / 0.4) ** 1.3
        grid_surface(part, hang, nu, nv // 2, "HP_Insulation", F.n,
                     back=lambda a, b: F.P(lerp(a0, a1, a), lerp(top0, top1 - sag, b), 0.002))


def wall_is(F, name):
    return F is WALLS[name]


def _batt(F, u, y, rr, seed):
    """Point on a mineral-wool batt face: bulges a little proud of the battens, lumpy, fibrous."""
    p = F.P(u, y, 0.0)
    n1 = nz(p, 9.0, 3.3 + seed) * 0.5 + 0.5
    n2 = nz(p, 31.0, 7.1 + seed)
    return F.P(u, y, BD - 0.008 + 0.022 * n1 + 0.005 * n2)


# ====================================================================== ceiling
def ceiling(s):
    part, lod = s.ilin, s.lod
    rr0 = drng("ceil")
    for i, (a, b, mat) in enumerate(CEILING):
        if mat is None:
            # missing panel above the rack: battens across, batts between them sagging, roof plate where one fell
            for xx in (a, a + 0.5, b - 0.045):
                B(part, (xx, LC + PT, LB), (xx + 0.045, ROOF, LF), "SS_Timber", skip=("top",))
            nu, nv = (8, 10) if lod == 0 else (2, 2)
            for (c0, c1) in ((a + 0.045, a + 0.5), (a + 0.545, b - 0.045)):
                zs = (LB + 0.01, LF - 0.01) if c0 < a + 0.1 else (LB + 0.01, 0.35)
                def pt(u, v, c0=c0, c1=c1, zs=zs):
                    x, z = lerp(c0, c1, u), lerp(zs[0], zs[1], v)
                    p = Vector((x, ROOF, z))
                    sag = 0.05 * math.sin(math.pi * u) * math.sin(math.pi * v)
                    return Vector((x, ROOF - BD + 0.004 - 0.012 * (nz(p, 9, 2.0) * 0.5 + 0.5) - sag, z))
                grid_surface(part, pt, nu, nv, "HP_Insulation", (0, -1, 0),
                             back=lambda u, v, c0=c0, c1=c1, zs=zs: Vector((lerp(c0, c1, u), ROOF - 0.002, lerp(zs[0], zs[1], v))))
            continue
        g = 0.0025 if lod == 0 else 0.0
        B(part, (a + g, LC + rr0.uniform(-0.0012, 0.0), LB), (b - g, LC + PT, LF), mat, skip=("top",))
        if lod == 0:
            for xx in (a + 0.03, b - 0.03):
                for zz in (LB + 0.05, -0.55, 0.0, 0.55, LF - 0.05):
                    s.ihard.box((xx - 0.0055, LC - 0.0016, zz - 0.0055), (xx + 0.0055, LC, zz + 0.0055), "VH_Steel", skip=("top",))


# ====================================================================== floor
def floor(s):
    f, lod = s.ifloor, s.lod
    if lod > 0:
        B(f, (LW, PLATE, LB), (LE, FY, LF), "SS_Boards", skip=("bottom",))
    else:
        rr = drng("floor")
        z = LB
        k = 0
        while z < LF - 1e-3:
            w = rr.uniform(0.17, 0.26)
            z1 = min(LF, z + w)
            if LF - z1 < 0.1:
                z1 = LF
            # each board run in two or three lengths with staggered butt joints
            cuts = sorted(rr.uniform(-1.8, 1.8) for _ in range(rr.choice((1, 2))))
            xs = [LW] + cuts + [LE]
            for xa, xb in zip(xs, xs[1:]):
                mat = "SS_Boards"
                if k == 3 and xa < -1.0 < xb:       # one length replaced with fresh timber beside the bunk
                    mat = "SS_Timber"
                bid = f.new_block(off=(rr.uniform(0, 8), rr.uniform(0, 8)), tint=(0.5, 0.5, 0.5))
                vs, made = B(f, (xa + 0.002, PLATE, z + 0.002), (xb - 0.002, FY - rr.uniform(0.0, 0.0012), z1 - 0.002), mat, bid,
                             skip=("bottom",))
                f.bevel_edges(list(made["top"].edges), 0.002, 1)
            # screw heads in rows over the cross members
            x = LW + 0.15
            while x < LE - 0.1:
                for zz in (z + (z1 - z) * 0.3, z + (z1 - z) * 0.7):
                    poly(s.ihard, [(x - 0.005, FY + 0.0004, zz - 0.005), (x + 0.005, FY + 0.0004, zz - 0.005),
                                   (x + 0.005, FY + 0.0004, zz + 0.005), (x - 0.005, FY + 0.0004, zz + 0.005)], "VH_Dark", (0, 1, 0))
                x += 0.305
            z = z1
            k += 1
        # steel plate screwed over a worn-through spot where the player stands at the locker
        B(f, (0.84, FY, -0.52), (1.38, FY + 0.004, -0.2), "WG_PlateSteel", skip=("bottom",))
        for xx in (0.86, 1.11, 1.36):
            for zz in (-0.5, -0.22):
                s.ihard.sphere((xx, FY + 0.004, zz), 0.007, "VH_Steel", 6, hemi_axis=(0, 1, 0))
        hpatch(f, 1.1, FY + 0.0045, -0.36, 0.2, 0.1, "VH_Steel", "plate_worn", jag=0.3)
    # rubber mat inside the door
    B(f, (0.98, FY, 0.52), (1.78, FY + 0.012, 1.02), "WG_Rubber", skip=("bottom",))
    if lod == 0:
        for k in range(9):
            zc = lerp(0.56, 0.98, k / 8)
            B(f, (1.01, FY + 0.012, zc - 0.008), (1.75, FY + 0.016, zc + 0.008), "WG_Rubber", skip=("bottom",))
    rug(s)


def rug(s):
    """Woven striped rug in the middle of the floor (Ward cloths: madder, bone, indigo, ochre), fringed ends."""
    f, lod = s.ifloor, s.lod
    x0, x1, z0, z1 = -0.88, 0.58, -0.2, 0.62
    t = 0.008
    if lod > 0:
        B(f, (x0, FY, z0), (x1, FY + t, z1), "WS_ClothMadder", skip=("bottom",))
        return
    seq = ["WS_ClothIndigo", "WS_ClothBone", "WS_ClothMadder", "WS_ClothMadder", "WS_ClothOchre", "WS_ClothMadder", "WS_ClothBone",
           "WS_ClothIndigo", "WS_ClothMadder", "WS_ClothMadder", "WS_ClothBone", "WS_ClothMadder", "WS_ClothOchre", "WS_ClothMadder",
           "WS_ClothMadder", "WS_ClothBone", "WS_ClothIndigo"]
    widths = [0.05, 0.03, 0.12, 0.1, 0.04, 0.12, 0.03, 0.06, 0.12, 0.12, 0.03, 0.12, 0.04, 0.1, 0.12, 0.03, 0.05]
    k = sum(widths)
    widths = [w * (x1 - x0) / k for w in widths]
    x = x0
    for w, mat in zip(widths, seq):
        B(f, (x, FY, z0 + 0.05), (x + w, FY + t, z1 - 0.05), mat, skip=("bottom",))
        x += w
    for (za, zb) in ((z0, z0 + 0.05), (z1 - 0.05, z1)):         # side borders
        B(f, (x0, FY, za), (x1, FY + t * 0.9, zb), "WS_ClothIndigo", skip=("bottom",))
    for xe, sg in ((x0, -1), (x1, 1)):                          # fringes
        z = z0 + 0.02
        while z < z1 - 0.01:
            B(f, (min(xe, xe + sg * 0.045), FY, z - 0.003), (max(xe, xe + sg * 0.045), FY + 0.003, z + 0.003), "WS_ClothBone",
              skip=("bottom",))
            z += 0.028


# ====================================================================== bunk
def bunk(s):
    m, c, lod = s.imetal, s.icloth, s.lod
    b = BED
    x0, x1, z0, z1, rt = b["x0"], b["x1"], b["z0"], b["z1"], b["rail"]
    t = 0.04
    mat = "WB_BlackSteel"
    for (xx, top) in ((x0, b["head"]), (x1 - t, b["foot"])):
        for zz in (z0, z1 - t):
            B(m, (xx, FY + 0.012, zz), (xx + t, top, zz + t), mat)
            B(m, (xx - 0.005, FY, zz - 0.005), (xx + t + 0.005, FY + 0.012, zz + t + 0.005), "VH_Rubber")   # feet
    # side and end rails: 40 x 40 angle (vertical flange outside, horizontal flange carrying the straps)
    for zz, sg in ((z0, 1), (z1 - 0.005, -1)):
        B(m, (x0 + t, rt - t, zz), (x1 - t, rt, zz + 0.005), mat)
        za, zb = sorted((zz + (0.005 if sg > 0 else 0.0), zz + sg * 0.04 + (0.005 if sg < 0 else 0.0)))
        B(m, (x0 + t, rt - t, za), (x1 - t, rt - t + 0.005, zb), mat)
    for xx in (x0, x1 - 0.005):
        B(m, (xx, rt - t, z0 + t), (xx + 0.005, rt, z1 - t), mat)
    # straps under the mattress
    nstr = 9 if lod == 0 else 4
    for k in range(nstr):
        xx = lerp(x0 + 0.12, x1 - 0.12, k / (nstr - 1))
        B(m, (xx - 0.02, rt - t, z0 + 0.005), (xx + 0.02, rt - t + 0.004, z1 - 0.005), "VH_Steel")
    # head end: two rails and three bars; foot end: one rail
    hz0, hz1 = z0 + t / 2, z1 - t / 2
    for yy in (b["head"] - 0.03, rt + 0.24):
        m.cyl((x0 + t / 2, yy, hz0), (x0 + t / 2, yy, hz1), 0.016, mat, 10)
    for k in range(1, 4):
        zz = lerp(hz0, hz1, k / 4)
        m.cyl((x0 + t / 2, rt + 0.24, zz), (x0 + t / 2, b["head"] - 0.03, zz), 0.01, mat, 8)
    m.cyl((x1 - t / 2, b["foot"] - 0.03, hz0), (x1 - t / 2, b["foot"] - 0.03, hz1), 0.016, mat, 10)
    if lod == 0:
        # worn paint on the top rails where hands grab them
        for (xx, yy, zz, ax) in ((x0 + t / 2, b["head"] - 0.03, z1 - 0.15, "z"), (x1 - t / 2, b["foot"] - 0.03, z1 - 0.12, "z")):
            m.cyl((xx, yy, zz - 0.08), (xx, yy, zz + 0.08), 0.0165, "VH_Steel", 10)
    # mattress: canvas ticking, rounded, sagging a little in the middle
    M = MATT
    vs, made = B(c, (M["x0"], M["y0"], M["z0"]), (M["x1"], M["y1"], M["z1"]), "FS_Canvas")
    c.bevel_edges(list({e for f in made.values() for e in f.edges}), 0.035, 3)
    if lod == 0:
        # piping seam round the top edge
        for zz in (M["z0"] - 0.003, M["z1"] + 0.003):
            c.cyl((M["x0"] + 0.04, M["y1"] - 0.035, zz), (M["x1"] - 0.04, M["y1"] - 0.035, zz), 0.006, "WS_ClothBone", 6)
    pillow(s)
    blanket(s)
    # folded indigo blanket on the foot of the bed
    fb_lo, fb_hi = (-1.42, M["y1"] + 0.045, -0.98), (-1.0, M["y1"] + 0.125, -0.42)
    vs, made = B(c, fb_lo, fb_hi, "WS_ClothIndigo")
    c.bevel_edges(list({e for f in made.values() for e in f.edges}), 0.025, 2)
    if lod == 0:
        for k in range(1, 3):
            yy = lerp(fb_lo[1], fb_hi[1], k / 3)
            c.cyl((fb_lo[0] - 0.004, yy, fb_lo[2] + 0.03), (fb_lo[0] - 0.004, yy, fb_hi[2] - 0.03), 0.004, "WS_ClothIndigo", 5)
    # under the bunk: a canvas duffel at the head end; a pair of boots set down by its side
    duffel(s, (-2.45, FY, -0.66))
    boots(s, (0.5, FY, 0.93))          # left by the door, between the battery and the mat
    # shelf over the bunk: a board on two steel brackets, books, a radio, tins, a jar
    sy = SHELF_Y
    w = s.iprops
    B(w, (-2.84, sy, LB), (-1.82, sy + 0.025, LB + 0.21), "SS_Timber")
    for xx in (-2.66, -2.0):
        B(m, (xx - 0.012, sy - 0.17, LB), (xx + 0.012, sy, LB + 0.006), "WB_BlackSteel")
        B(m, (xx - 0.012, sy - 0.006, LB), (xx + 0.012, sy, LB + 0.18), "WB_BlackSteel")
        m.cyl((xx, sy - 0.15, LB + 0.006), (xx, sy - 0.006, LB + 0.16), 0.006, "WB_BlackSteel", 6)
    if lod > 0:            # LOD1: one block of books, the radio case
        B(w, (-2.8, sy + 0.025, LB + 0.02), (-2.64, sy + 0.24, LB + 0.18), "WS_ClothMadder")
        B(w, (-2.45, sy + 0.025, LB + 0.03), (-2.25, sy + 0.145, LB + 0.13), "VH_Dark")
        reading_lamp(s)
        return
    rr = drng("books")
    x = -2.8
    for k, cm in enumerate(("WS_ClothMadder", "FS_Canvas", "WS_ClothIndigo", "WS_Hide")):
        bw, bh, bd = rr.uniform(0.03, 0.05), rr.uniform(0.19, 0.24), rr.uniform(0.14, 0.17)
        lean = 0.0 if k < 3 else 0.35
        if lean:
            c0 = Vector((x + 0.02, sy + 0.025, LB + 0.02))
            ax = Vector((math.sin(lean), math.cos(lean), 0))
            pts = []
            for yy in (0, bh):
                for (dx, dz) in ((0, 0), (bw, 0), (bw, bd), (0, bd)):
                    pts.append(c0 + ax * yy + Vector((math.cos(lean) * dx, -math.sin(lean) * dx, dz)))
            w.hexa(pts, cm)
        else:
            B(w, (x, sy + 0.025, LB + 0.02), (x + bw, sy + 0.025 + bh, LB + 0.02 + bd), cm)
            if lod == 0:
                B(w, (x + 0.003, sy + 0.03, LB + 0.02 + bd), (x + bw - 0.003, sy + 0.02 + bh, LB + 0.022 + bd), "WB_PaintBone")
        x += bw + 0.004
    # little radio: dark case, steel dial and grille, a whip aerial
    rx0 = -2.45
    B(w, (rx0, sy + 0.025, LB + 0.03), (rx0 + 0.2, sy + 0.145, LB + 0.13), "VH_Dark")
    if lod == 0:
        w.cyl((rx0 + 0.15, sy + 0.085, LB + 0.13), (rx0 + 0.15, sy + 0.085, LB + 0.138), 0.022, "VH_Steel", 12)
        for k in range(5):
            B(w, (rx0 + 0.02, sy + 0.05 + k * 0.016, LB + 0.13), (rx0 + 0.11, sy + 0.058 + k * 0.016, LB + 0.134), "VH_Steel")
        w.cyl((rx0 + 0.18, sy + 0.145, LB + 0.05), (rx0 + 0.24, sy + 0.42, LB + 0.06), 0.003, "VH_Steel", 5)
    for (xx, r, h, mat) in ((-2.12, 0.04, 0.1, "WS_PaintRed"), (-1.98, 0.035, 0.07, "VH_Steel")):
        w.cyl((xx, sy + 0.025, LB + 0.1), (xx, sy + 0.025 + h, LB + 0.1), r, mat, 12)
    # reading lamp clipped to the head rail, its cord down the post and along the wall to a socket past the foot
    reading_lamp(s)


def duffel(s, base):
    c, lod = s.icloth, s.lod
    x, y, z = base
    n = 14 if lod == 0 else 8
    rings_ = []
    for k, (dx, r) in enumerate(((-0.3, 0.06), (-0.27, 0.11), (-0.15, 0.13), (0.15, 0.13), (0.27, 0.11), (0.3, 0.06))):
        rr = [Vector((x + dx, y + 0.12 + math.sin(a) * r * 0.85, z + math.cos(a) * r)) for a in [2 * math.pi * i / n for i in range(n)]]
        for p in rr:
            p.y = max(p.y, y + 0.002)               # sits flat on the floor
        rings_.append(rr)
    loft(c, rings_, "FS_Canvas")
    if lod == 0:
        for dx in (-0.12, 0.12):
            loop_tube(c, [Vector((x + dx, y + 0.12 + math.sin(a) * 0.135 * 0.85, z + math.cos(a) * 0.135)) for a in
                          [2 * math.pi * i / 12 for i in range(12)]], 0.008, "FS_Webbing", 4)
        c.tube([(x - 0.12, y + 0.235, z), (x - 0.05, y + 0.27, z + 0.02), (x + 0.05, y + 0.27, z + 0.02), (x + 0.12, y + 0.235, z)], 0.01,
               "FS_Webbing", 5)


def boots(s, base):
    """A pair of worn leather boots, one standing, one tipped against it."""
    c, lod = s.icloth, s.lod
    x, y, z = base
    n = 10 if lod == 0 else 6
    for k, (dx, dz, tip) in enumerate(((0.0, 0.0, 0.0), (0.13, -0.06, -0.35))):
        bx, bz = x + dx, z + dz
        ca, sa = math.cos(tip), math.sin(tip)
        def P(px, py, pz):          # boot-local (x along the foot, toe +x), tipped about the foot axis
            return Vector((bx + px, y + py * ca + 0.0, bz + pz + py * sa))
        sole = [P(-0.13, 0.0, -0.045), P(0.15, 0.0, -0.045), P(0.15, 0.0, 0.045), P(-0.13, 0.0, 0.045),
                P(-0.13, 0.025, -0.045), P(0.15, 0.025, -0.045), P(0.15, 0.025, 0.045), P(-0.13, 0.025, 0.045)]
        c.hexa(sole, "VH_Rubber")
        rings_ = []
        for (px, py, ry, rz) in ((-0.12, 0.08, 0.05, 0.045), (0.0, 0.07, 0.055, 0.045), (0.1, 0.05, 0.035, 0.04), (0.15, 0.035, 0.02, 0.035)):
            rings_.append([P(px, py + math.sin(a) * ry, math.cos(a) * rz) for a in [2 * math.pi * i / n for i in range(n)]])
        loft(c, rings_, "WS_Hide")
        shaft = [[P(-0.09 + math.cos(a) * 0.05, h, math.sin(a) * 0.045) for a in [2 * math.pi * i / n for i in range(n)]]
                 for h in (0.05, 0.2, 0.26)]
        loft(c, shaft, "WS_Hide")


def pillow(s):
    c, lod = s.icloth, s.lod
    M = MATT
    cx, cz = M["x0"] + 0.24, (M["z0"] + M["z1"]) / 2
    cy = M["y1"] + 0.055
    seg = 16 if lod == 0 else 8
    fs = c.sphere((0, 0, 0), 1.0, "WS_ClothBone", seg)
    vs = {v for f in fs for v in f.verts}
    for v in vs:
        p = v.co.copy()
        # superellipse-ish: square up the footprint, flatten, dent the middle
        sx = math.copysign(abs(p.x) ** 0.55, p.x)
        sz = math.copysign(abs(p.z) ** 0.55, p.z)
        ry = p.y * (1 - 0.25 * (sx * sx + sz * sz))
        dent = -0.025 * math.exp(-((sx + 0.1) ** 2 + sz ** 2) * 3.0) if p.y > 0 else 0.0
        q = Vector((cx + sx * 0.17, cy + ry * 0.065 + dent, cz + sz * 0.29))
        q.y += 0.006 * nz(q, 18, 4.2)
        v.co = q


def blanket(s):
    """Madder wool blanket thrown back off the head of the bunk: rumpled over the mattress, hanging down the open side
    (not the wall side) and over the foot, the top edge turned back on itself."""
    c, lod = s.icloth, s.lod
    M = MATT
    top = M["y1"] + 0.006
    xa, xb = -2.26, M["x1"] - 0.012
    hang_f, hang_x = 0.3, 0.0
    za, zb = M["z0"] - 0.01, M["z1"]
    ni, nj = (34, 24) if lod == 0 else (8, 6)
    Lx = (xb - xa) + hang_x
    Lz = (zb - za) + hang_f
    r = 0.03
    rr = drng("blanket")
    ph = [rr.uniform(0, 6.28) for _ in range(4)]

    def place(fx, fz):
        # along x: on the top until the foot edge, then over the edge and down
        ox, oz = fx - (xb - xa), fz - (zb - za)
        x, y, z = xa + min(fx, xb - xa), top, za + min(fz, zb - za)
        dy = 0.0
        if ox > 0:
            a = min(ox / r, math.pi / 2)
            x = xb + r * math.sin(a) + max(0.0, ox - r * math.pi / 2) * 0.12
            dy += r * (1 - math.cos(a)) + max(0.0, ox - r * math.pi / 2)
        if oz > 0:
            a = min(oz / r, math.pi / 2)
            z = zb + r * math.sin(a) + max(0.0, oz - r * math.pi / 2) * 0.1
            dy += r * (1 - math.cos(a)) + max(0.0, oz - r * math.pi / 2)
        p = Vector((x, top - dy, z))
        on_top = ox <= 0 and oz <= 0
        # rumples: broad folds running diagonally, finer noise; the hanging parts get vertical folds
        if on_top:
            rum = 0.022 * math.sin(fx * 7.0 + fz * 4.0 + ph[0]) * math.sin(fz * 3.0 + ph[1]) + 0.012 * nz(p, 6, 1.3) + 0.004 * nz(p, 19, 2.2)
            p.y += 0.012 + max(-0.006, rum)          # never below the mattress top (it showed through in review p2)
            p.y += 0.035 * math.exp(-((fx - 0.25) ** 2) / 0.01) * (0.6 + 0.4 * math.sin(fz * 9))    # ridge of the turned-back fold
        else:
            k = 0.008 * (1 + math.sin(fx * 23 + ph[2]))        # folds only ever bulge outwards, clear of the side rail
            if oz > 0:
                p.z += k + 0.003 * (1 + nz(p, 11, 5.0))
            if ox > 0:
                p.x += (0.016 * math.sin(fz * 21 + ph[3])) + 0.006 * nz(p, 11, 6.0)
        return p
    P = [[place(Lx * i / (ni - 1), Lz * j / (nj - 1)) for j in range(nj)] for i in range(ni)]
    sheet(c, P, "WS_ClothMadder", 0.008, lambda p: (0, 1, 0) if p.y > top - 0.02 else ((0.4, 0, 1) if p.z > zb else (1, 0, 0.3)))
    # turned-back top edge: a strip lying on the blanket, rolled at the head end
    if lod == 0:
        n2i, n2j = 10, 20
        Q = []
        for i in range(n2i):
            fx = 0.24 * i / (n2i - 1)
            row = []
            for j in range(n2j):
                fz = (zb - za + 0.18) * j / (n2j - 1)
                base = place(0.26 - fx, min(fz, Lz))
                q = base + Vector((0, 0.016 + 0.01 * math.sin(math.pi * fx / 0.24), 0))
                row.append(q)
            Q.append(row)
        sheet(c, Q, "WS_ClothMadder", 0.007, lambda p: (0, 1, 0) if p.y > top - 0.02 else (0, 0.3, 1))


def reading_lamp(s):
    m, g, lod = s.imetal, s.iglow, s.lod
    b = BED
    cx, cy, cz = b["x0"] + 0.02, b["head"] - 0.03, b["z1"] - 0.06
    # clamp round the head rail
    B(m, (cx - 0.03, cy - 0.035, cz - 0.025), (cx + 0.03, cy + 0.03, cz + 0.025), "VH_Dark")
    if lod == 0:
        m.cyl((cx, cy - 0.035, cz), (cx, cy - 0.07, cz), 0.006, "VH_Steel", 6)
        m.cyl((cx - 0.02, cy - 0.07, cz), (cx + 0.02, cy - 0.07, cz), 0.005, "VH_Steel", 6)
    neck = [(cx, cy + 0.03, cz), (cx, cy + 0.17, cz), (cx + 0.05, cy + 0.28, cz - 0.05), (cx + 0.15, cy + 0.31, cz - 0.15),
            (cx + 0.24, cy + 0.27, cz - 0.22)]
    m.tube(neck, 0.007, "VH_Dark", 6)
    head = Vector(neck[-1])
    aim = (Vector((MATT["x0"] + 0.3, MATT["y1"] + 0.02, (MATT["z0"] + MATT["z1"]) / 2 - 0.05)) - head).normalized()
    mouth = head + aim * 0.13
    m.cyl(tuple(head), tuple(mouth), 0.032, "WS_PaintYellow", 14 if lod == 0 else 8, r2=0.062)
    m.cyl(tuple(head - aim * 0.025), tuple(head), 0.02, "VH_Dark", 10)
    bulb = head + aim * 0.06
    g.sphere(tuple(bulb), 0.022, "SS_BulbWarm", 10 if lod == 0 else 6)
    s.rec["_reading_lamp"] = (bulb, aim)
    if lod == 0:
        # cord: down the head post, along the back wall behind the bunk, to a socket past its foot
        sx = BED["x1"] + 0.12
        s.iprops.tube([(cx, cy - 0.04, b["z1"] + 0.008), (cx + 0.005, FY + 0.05, b["z1"] + 0.008), (cx + 0.09, FY + 0.015, LB + 0.03),
                       (sx, FY + 0.015, LB + 0.03), (sx, FY + 0.2, LB + 0.012)], 0.004, "VH_Rubber", 5)


# ====================================================================== stash locker
def locker(s):
    m, hd, lod = s.imetal, s.ihard, s.lod
    L = LOCKER
    x0, x1, z0, z1, y0, y1 = L["x0"], L["x1"], L["z0"], L["z1"], L["y0"], L["y1"]
    paint = "WG_OlivePaint"
    B(m, (x0 + 0.03, y0, z0), (x1 - 0.03, y0 + 0.07, z1 - 0.03), "VH_Dark")          # recessed plinth
    yb = y0 + 0.07
    B(m, (x0, yb, z0), (x0 + 0.012, y1, z1), paint)                                  # sides, top, back
    B(m, (x1 - 0.012, yb, z0), (x1, y1, z1), paint)
    B(m, (x0, y1 - 0.012, z0), (x1, y1, z1), paint)
    B(m, (x0, yb, z0), (x1, yb + 0.03, z1), paint)
    B(m, (x0 + 0.012, y1 - 0.06, z1 - 0.02), (x1 - 0.012, y1 - 0.012, z1), paint)    # head rail
    # two doors (closed), 15 mm proud of the carcass front
    gap = 0.003
    xm = (x0 + x1) / 2
    dz0, dz1 = z1, z1 + 0.018
    dy0, dy1 = yb + 0.035, y1 - 0.065
    doors = [(x0 + 0.012, xm - gap), (xm + gap, x1 - 0.012)]
    Fd = Frame((0, 0, dz1), (1, 0, 0), (0, 0, 1))
    for i, (a, b) in enumerate(doors):
        B(m, (a, dy0, dz0), (b, dy1, dz1), paint)
        if lod == 0:
            # pressed return lip round the door
            for (aa, bb, cc, dd) in ((a, b, dy0, dy0 + 0.02), (a, b, dy1 - 0.02, dy1), (a, a + 0.02, dy0, dy1), (b - 0.02, b, dy0, dy1)):
                B(m, (aa, cc, dz1), (bb, dd, dz1 + 0.003), paint)
            # louvres top and bottom
            for vy in (dy1 - 0.27, dy0 + 0.1):
                for k in range(6):
                    yy = vy + k * 0.022
                    B(m, (a + 0.1, yy, dz1 - 0.004), (b - 0.1, yy + 0.008, dz1 + 0.0005), "VH_Dark")
                    m.hexa([Vector((a + 0.1, yy + 0.008, dz1)), Vector((b - 0.1, yy + 0.008, dz1)), Vector((b - 0.1, yy + 0.008, dz1 + 0.006)),
                            Vector((a + 0.1, yy + 0.008, dz1 + 0.006)), Vector((a + 0.1, yy + 0.018, dz1)), Vector((b - 0.1, yy + 0.018, dz1)),
                            Vector((b - 0.1, yy + 0.011, dz1 + 0.003)), Vector((a + 0.1, yy + 0.011, dz1 + 0.003))], paint)
            # card holder (empty on the right, a bone card on the left)
            cy_ = dy1 - 0.08
            B(m, ((a + b) / 2 - 0.05, cy_ - 0.025, dz1 + 0.003), ((a + b) / 2 + 0.05, cy_ + 0.025, dz1 + 0.006), "VH_Steel")
            B(m, ((a + b) / 2 - 0.042, cy_ - 0.018, dz1 + 0.006), ((a + b) / 2 + 0.042, cy_ + 0.018, dz1 + 0.0065),
              "WB_PaintBone" if i == 0 else "VH_Dark")
            # hinges on the outer edges
            for hy in (dy0 + 0.15, dy1 - 0.15):
                hx = a - 0.002 if i == 0 else b + 0.002
                m.cyl((hx, hy - 0.04, dz1 - 0.004), (hx, hy + 0.04, dz1 - 0.004), 0.006, "VH_Steel", 8)
    # handle housing and lever on the right door, padlock hasp across the meeting edge
    hx = xm + 0.06
    hy = (dy0 + dy1) / 2 + 0.05
    B(m, (hx - 0.022, hy - 0.08, dz1 - 0.003), (hx + 0.022, hy + 0.08, dz1 + 0.002), "VH_Dark")
    B(m, (hx - 0.012, hy - 0.07, dz1), (hx + 0.012, hy + 0.04, dz1 + 0.022), "VH_Steel")
    B(m, (xm - 0.04, hy + 0.1, dz1), (xm + 0.035, hy + 0.13, dz1 + 0.006), "VH_Steel")        # hasp plate (right door)
    B(m, (xm - 0.055, hy + 0.098, dz1), (xm - 0.035, hy + 0.132, dz1 + 0.025), "VH_Steel")     # staple (left door)
    pl = (xm - 0.045, hy + 0.06, dz1 + 0.03)
    B(m, (pl[0] - 0.022, pl[1] - 0.05, pl[2] - 0.009), (pl[0] + 0.022, pl[1], pl[2] + 0.009), "VH_Brass")   # padlock
    m.tube([(pl[0] - 0.012, pl[1], pl[2]), (pl[0] - 0.012, pl[1] + 0.03, pl[2]), (pl[0], pl[1] + 0.045, pl[2]),
            (pl[0] + 0.012, pl[1] + 0.03, pl[2]), (pl[0] + 0.012, pl[1], pl[2])], 0.004, "VH_Steel", 6)
    if lod == 0:
        hd.box((pl[0] - 0.003, pl[1] - 0.04, pl[2] + 0.009), (pl[0] + 0.003, pl[1] - 0.025, pl[2] + 0.0095), "VH_Dark")
        # wear: bare steel round the handle and padlock, chips along door edges at hand height, rust at the plinth
        patch(m, Fd, hx + 0.004, hy - 0.02, 0.0035, 0.04, 0.085, "VH_Steel", "lk_h", n=13, jag=0.25)
        patch(m, Fd, xm - 0.045, hy + 0.115, 0.0035, 0.028, 0.03, "VH_Steel", "lk_p", n=11, jag=0.25)
        rr = drng("locker_wear")
        for k in range(14):
            side = rr.choice((0, 1))
            a, b = doors[side]
            u = rr.choice((a + 0.012, b - 0.012))
            y = rr.uniform(dy0 + 0.1, dy1 - 0.1)
            patch(m, Fd, u, y, 0.0035, rr.uniform(0.006, 0.018), rr.uniform(0.008, 0.03), "VH_Steel", ("lkc", k), n=7)
        for k in range(6):
            patch(m, Fd, rr.uniform(x0 + 0.05, x1 - 0.05), dy0 + rr.uniform(0.01, 0.05), 0.0035, rr.uniform(0.03, 0.07),
                  rr.uniform(0.01, 0.03), "WG_RustSteel", ("lkr", k))
        Fh = Frame((0, 0, z1), (1, 0, 0), (0, 0, 1))
        for k in range(4):           # head rail knocked about
            patch(m, Fh, rr.uniform(x0 + 0.05, x1 - 0.05), y1 - 0.035, 0.0005, 0.03, 0.01, "VH_Steel", ("lkt", k), n=6)
    # stencilled home number (painted, like the door's)
    ob, w = lettering("S2", _AB.STENCIL_FONT, 0.13, ((doors[0][0] + doors[0][1]) / 2, dy1 - 0.42, dz1 + 0.0012), 0.002, 0.3,
                      "WB_StencilPaint", s.coll, f"{s.name}_LockerStencil_LOD{lod}", lod=1, facing=(0, 0, 1))
    s.istencils.append(ob)
    # rolled sleeping mat on top
    c = s.icloth
    c.cyl((x0 + 0.12, y1 + 0.07, z0 + 0.25), (x1 - 0.12, y1 + 0.07, z0 + 0.25), 0.07, "FS_Canvas", 14 if lod == 0 else 8)
    for xx in (x0 + 0.25, x1 - 0.25):
        c.cyl((xx - 0.02, y1 + 0.07, z0 + 0.25), (xx + 0.02, y1 + 0.07, z0 + 0.25), 0.073, "FS_Webbing", 14 if lod == 0 else 8)


# ====================================================================== slotted-angle rack
def rack(s):
    m, w, hd, lod = s.imetal, s.iprops, s.ihard, s.lod
    R = RACK
    x0, x1, z0, z1 = R["x0"], R["x1"], R["z0"], R["z1"]
    a = 0.04                     # angle size
    t = 0.0035
    st = "VH_Steel"
    posts = [(x0, z1, 1, -1), (x1, z1, -1, -1), (x0, z0, 1, 1), (x1, z0, -1, 1)]   # (x, z, dir into rack x, dir into rack z)
    for (px, pz, sx, sz) in posts:
        xa, xb = sorted((px, px + sx * a))
        za, zb = sorted((pz, pz + sz * a))
        # L-section: one flange in the x-y plane (faces the room / wall), one in the z-y plane
        fz0, fz1 = sorted((pz, pz + sz * t))
        fx0, fx1 = sorted((px, px + sx * t))
        B(m, (xa, FY, fz0), (xb, R["top"], fz1), st)
        B(m, (fx0, FY, za), (fx1, R["top"], zb), st)
        if lod == 0:
            B(m, (xa - 0.01, FY, za - 0.01), (xb + 0.01, FY + 0.004, zb + 0.01), st)       # foot plate
            # slots up both flanges (dark quads a hair proud)
            y = FY + 0.05
            while y < R["top"] - 0.04:
                xc = (xa + xb) / 2
                if sz < 0:          # front posts: slots on the face towards the room
                    zf = fz1 + 0.0003
                    poly(hd, [(xc - 0.006, y, zf), (xc + 0.006, y, zf), (xc + 0.006, y + 0.028, zf), (xc - 0.006, y + 0.028, zf)], "VH_Dark",
                         (0, 0, 1))
                zc = (za + zb) / 2
                xf = (fx0 if sx > 0 else fx1) - 0.0003 * sx      # outer face of the end flange
                poly(hd, [(xf, y, zc - 0.006), (xf, y, zc + 0.006), (xf, y + 0.028, zc + 0.006), (xf, y + 0.028, zc - 0.006)], "VH_Dark",
                     (-sx, 0, 0))
                y += 0.05
            hpatch(m, (xa + xb) / 2, FY + 0.0045, (za + zb) / 2, 0.03, 0.03, "WG_RustSteel", ("rackfoot", px, pz))
    for lv in R["levels"]:
        # front and back angle beams, side angles, a ply shelf
        for (zz, sg) in ((z1, -1), (z0, 1)):
            za, zb = sorted((zz, zz + sg * t))
            B(m, (x0 + t, lv - a, za), (x1 - t, lv, zb), st)
            za, zb = sorted((zz, zz + sg * a))
            B(m, (x0 + t, lv - t, za), (x1 - t, lv, zb), st)
        for (xx, sg) in ((x0, 1), (x1, -1)):
            xa, xb = sorted((xx + sg * t, xx + sg * a))
            B(m, (xa, lv - t, z0 + a), (xb, lv, z1 - a), st)
        B(w, (x0 + 0.01, lv, z0 + 0.008), (x1 - 0.01, lv + 0.018, z1 - 0.008), "WG_Plywood")
        if lod == 0:
            for (xx, zz) in ((x0 + 0.02, z1 + 0.002), (x1 - 0.02, z1 + 0.002)):
                hd.cyl((xx, lv - 0.02, zz), (xx, lv - 0.02, zz + 0.008), 0.007, "VH_Steel", 6)
    # cross bracing on the back of the lower bays and the two ends
    if lod == 0:
        for (ya, yb_) in ((R["levels"][0], R["levels"][1] - a), (R["levels"][1], R["levels"][2] - a)):
            for (p, q) in (((x0 + a, ya, z0 + 0.004), (x1 - a, yb_, z0 + 0.004)), ((x0 + a, yb_, z0 + 0.004), (x1 - a, ya, z0 + 0.004))):
                s_ = Vector(q) - Vector(p)
                n = Vector((0, 0, 1))
                side = s_.cross(n).normalized() * 0.012
                m.hexa([Vector(p) - side, Vector(p) + side, Vector(p) + side + Vector((0, 0, 0.003)), Vector(p) - side + Vector((0, 0, 0.003)),
                        Vector(q) - side, Vector(q) + side, Vector(q) + side + Vector((0, 0, 0.003)), Vector(q) - side + Vector((0, 0, 0.003))], st)
    # dressing modelled here: small parts bins, coils of cable and copper, scrap in the salvage crate (mounts carry the
    # scanned crates, toolbox, jerrycan and tins: see record())
    lv2 = R["levels"][2] + 0.018
    for k in range(3):
        bx = 2.29 + k * 0.17
        mat = ("WS_PaintYellow", "WB_PaintBone", "WS_PaintRed")[k]
        B(w, (bx, lv2, z1 - 0.3), (bx + 0.15, lv2 + 0.005, z1 - 0.02), mat)
        B(w, (bx, lv2, z1 - 0.3), (bx + 0.006, lv2 + 0.13, z1 - 0.02), mat)
        B(w, (bx + 0.144, lv2, z1 - 0.3), (bx + 0.15, lv2 + 0.13, z1 - 0.02), mat)
        B(w, (bx, lv2, z1 - 0.3), (bx + 0.15, lv2 + 0.13, z1 - 0.294), mat)
        # sloped open front lip
        m_ = [Vector((bx, lv2, z1 - 0.02)), Vector((bx + 0.15, lv2, z1 - 0.02)), Vector((bx + 0.15, lv2, z1 - 0.014)), Vector((bx, lv2, z1 - 0.014)),
              Vector((bx, lv2 + 0.07, z1 - 0.02)), Vector((bx + 0.15, lv2 + 0.07, z1 - 0.02)), Vector((bx + 0.15, lv2 + 0.07, z1 - 0.014)),
              Vector((bx, lv2 + 0.07, z1 - 0.014))]
        w.hexa(m_, mat)
        if lod == 0:   # contents: screws/bolts as a lumpy fill
            fs = w.sphere((bx + 0.075, lv2 + 0.06, z1 - 0.16), 1.0, ("VH_Steel", "VH_Brass", "VH_Steel")[k], 8, hemi_axis=(0, 1, 0))
            for v in {v for f in fs for v in f.verts}:
                p = v.co - Vector((bx + 0.075, lv2 + 0.06, z1 - 0.16))
                v.co = Vector((bx + 0.075 + p.x * 0.068, lv2 + 0.06 + p.y * 0.03 + 0.006 * nz(v.co, 60, k), z1 - 0.16 + p.z * 0.13))
    top = R["levels"][3] + 0.018
    torus(w, (2.5, top + 0.022, z1 - 0.21), 0.11, 0.02, "VH_Rubber", 22 if lod == 0 else 10)
    torus(w, (2.5, top + 0.062, z1 - 0.21), 0.1, 0.019, "VH_Rubber", 22 if lod == 0 else 10)
    torus(w, (2.73, top + 0.022, z1 - 0.24), 0.07, 0.022, "VH_Bronze", 22 if lod == 0 else 10)
    lv1 = R["levels"][1] + 0.018
    # scrap parts on the second shelf: a small motor, a geared hub, pipe offcuts
    w.cyl((2.14, lv1 + 0.06, z1 - 0.26), (2.27, lv1 + 0.06, z1 - 0.26), 0.06, "WB_BlackSteel", 14 if lod == 0 else 8)
    B(w, (2.155, lv1, z1 - 0.32), (2.255, lv1 + 0.012, z1 - 0.2), "WB_BlackSteel")
    w.cyl((2.27, lv1 + 0.06, z1 - 0.26), (2.31, lv1 + 0.06, z1 - 0.26), 0.012, "VH_Steel", 8)
    if lod == 0:
        gear(w, (2.2, lv1 + 0.006, z1 - 0.09), 0.06, 0.012, 14, "VH_Steel")


def torus(part, c, R_, r, mat, n=20, m_=8):
    c = Vector(c)
    rings = []
    for i in range(n):
        a = 2 * math.pi * i / n
        ctr = c + Vector((math.cos(a) * R_, 0, math.sin(a) * R_))
        out = Vector((math.cos(a), 0, math.sin(a)))
        rings.append([ctr + out * math.cos(b) * r + Vector((0, math.sin(b) * r, 0)) for b in [2 * math.pi * j / m_ for j in range(m_)]])
    bm = part.bm
    V = [[bm.verts.new(p) for p in rg] for rg in rings]
    mi = part.mi(mat)
    fs = []
    for i in range(n):
        a, b = V[i], V[(i + 1) % n]
        for j in range(m_):
            k = (j + 1) % m_
            fs.append(bm.faces.new([a[j], b[j], b[k], a[k]]))
    for f in fs:
        f.material_index = mi
    bmesh.ops.recalc_face_normals(bm, faces=fs)


def loop_tube(part, pts, r, mat, m_=6):
    """Sweep a circle of radius r round a closed polyline (rope coils, rings) without the joint spheres Part.tube adds."""
    pts = [Vector(p) for p in pts]
    n = len(pts)
    bm = part.bm
    rings_ = []
    for i in range(n):
        tng = (pts[(i + 1) % n] - pts[i - 1]).normalized()
        ref = Vector((0, 1, 0)) if abs(tng.y) < 0.9 else Vector((1, 0, 0))
        a_ = tng.cross(ref).normalized()
        b_ = tng.cross(a_).normalized()
        rings_.append([bm.verts.new(pts[i] + (a_ * math.cos(2 * math.pi * k / m_) + b_ * math.sin(2 * math.pi * k / m_)) * r)
                       for k in range(m_)])
    mi = part.mi(mat)
    fs = []
    for i in range(n):
        a, b = rings_[i], rings_[(i + 1) % n]
        for k in range(m_):
            fs.append(bm.faces.new([a[k], a[(k + 1) % m_], b[(k + 1) % m_], b[k]]))
    for f in fs:
        f.material_index = mi
    bmesh.ops.recalc_face_normals(bm, faces=fs)


def gear(part, c, r, h, teeth, mat):
    x, y, z = c
    part.cyl((x, y, z), (x, y + h, z), r * 0.86, mat, teeth * 2)
    for k in range(teeth):
        a = 2 * math.pi * k / teeth
        d = Vector((math.cos(a), 0, math.sin(a)))
        s_ = Vector((-d.z, 0, d.x)) * 0.008
        p0, p1 = Vector(c) + d * r * 0.84, Vector(c) + d * r
        part.hexa([p0 - s_, p1 - s_ * 0.6, p1 + s_ * 0.6, p0 + s_,
                   p0 - s_ + Vector((0, h, 0)), p1 - s_ * 0.6 + Vector((0, h, 0)), p1 + s_ * 0.6 + Vector((0, h, 0)), p0 + s_ + Vector((0, h, 0))], mat)
    part.cyl((x, y + h, z), (x, y + h + 0.004, z), r * 0.3, "VH_Dark", 10)


# ====================================================================== fold-down table, stool, kitchen things
def table(s):
    m, w, lod = s.imetal, s.iprops, s.lod
    T = TABLE
    x0, x1, z0, z1, top = T["x0"], T["x1"], T["z0"], T["z1"], T["top"]
    B(w, (x0 + 0.02, top - 0.07, z1 - 0.025), (x1 - 0.02, top - 0.03, z1), "SS_Timber")       # wall cleat
    B(w, (x0, top - 0.03, z0), (x1, top, z1 - 0.003), "SS_Timber")                            # top
    B(m, (x0 - 0.003, top - 0.032, z0 - 0.004), (x1 + 0.003, top + 0.002, z0), "VH_Steel")      # steel edge band
    for xx in (x0 + 0.08, x1 - 0.08):
        # folding bracket: wall leg, arm under the top, diagonal
        B(m, (xx - 0.012, top - 0.42, z1 - 0.012), (xx + 0.012, top - 0.03, z1), "WB_BlackSteel")
        B(m, (xx - 0.012, top - 0.055, z0 + 0.06), (xx + 0.012, top - 0.03, z1 - 0.012), "WB_BlackSteel")
        p, q = Vector((xx, top - 0.39, z1 - 0.012)), Vector((xx, top - 0.05, z0 + 0.09))
        d = (q - p).normalized()
        sd = Vector((0.012, 0, 0))
        nd = d.cross(Vector((1, 0, 0))).normalized() * 0.006
        m.hexa([p - sd - nd, p + sd - nd, p + sd + nd, p - sd + nd, q - sd - nd, q + sd - nd, q + sd + nd, q - sd + nd], "WB_BlackSteel")
    if lod == 0:
        for xx in (x0 + 0.25, x1 - 0.25):      # butt hinges at the back edge
            B(m, (xx - 0.04, top - 0.002, z1 - 0.03), (xx + 0.04, top + 0.001, z1 - 0.003), "VH_Steel")
        # ring stains and knife marks on the top
        hpatch(w, -1.4, top + 0.0004, 0.84, 0.045, 0.045, "VH_Dark", "mugring", jag=0.15)
        hpatch(w, -1.62, top + 0.0004, 0.95, 0.06, 0.05, "VH_Dark", "jugring", jag=0.15)
    ty = top
    # hot plate and kettle
    hp = (-1.05, 0.9)
    B(w, (hp[0] - 0.13, ty, hp[1] - 0.1), (hp[0] + 0.13, ty + 0.05, hp[1] + 0.1), "VH_Dark")
    w.cyl((hp[0], ty + 0.05, hp[1]), (hp[0], ty + 0.056, hp[1]), 0.085, "VH_Steel", 20 if lod == 0 else 10)
    w.cyl((hp[0] + 0.09, ty + 0.025, hp[1] - 0.1), (hp[0] + 0.09, ty + 0.025, hp[1] - 0.112), 0.012, "WB_PaintBone", 10)
    kettle(s, (hp[0], ty + 0.056, hp[1]))
    if lod > 0:
        w.cyl((-1.62, ty, 0.95), (-1.62, ty + 0.26, 0.95), 0.07, "VH_Steel", 8)
        stool(s)
        sill(s)
        return
    # enamel mug with a dark rim
    mx, mz = -1.4, 0.84
    w.cyl((mx, ty, mz), (mx, ty + 0.085, mz), 0.04, "SS_Enamel", 16 if lod == 0 else 8)
    w.cyl((mx, ty + 0.08, mz), (mx, ty + 0.0865, mz), 0.0405, "VH_Dark", 16 if lod == 0 else 8)
    w.cyl((mx, ty + 0.07, mz), (mx, ty + 0.0868, mz), 0.035, "WS_Hide", 16 if lod == 0 else 8)     # tea
    w.tube([(mx + 0.04, ty + 0.065, mz), (mx + 0.065, ty + 0.06, mz), (mx + 0.065, ty + 0.03, mz), (mx + 0.04, ty + 0.025, mz)], 0.006,
           "SS_Enamel", 6)
    # galvanised water jug
    jx, jz = -1.62, 0.95
    rings = []
    for (yy, r) in ((0.0, 0.07), (0.01, 0.075), (0.16, 0.075), (0.21, 0.05), (0.25, 0.042), (0.262, 0.046)):
        rings.append(ring((jx, ty + yy, jz), r, r, 16 if lod == 0 else 8))
    loft(w, rings, "VH_Steel")
    w.tube([(jx + 0.072, ty + 0.2, jz), (jx + 0.12, ty + 0.19, jz), (jx + 0.12, ty + 0.06, jz), (jx + 0.074, ty + 0.05, jz)], 0.008, "VH_Steel", 6)
    w.cyl((jx - 0.04, ty + 0.255, jz), (jx - 0.08, ty + 0.27, jz), 0.012, "VH_Steel", 6)
    # food tin and a spoon
    w.cyl((-1.25, ty, 1.0), (-1.25, ty + 0.1, 1.0), 0.038, "WS_PaintRed", 12 if lod == 0 else 8)
    if lod == 0:
        w.cyl((-1.25, ty + 0.1, 1.0), (-1.25, ty + 0.104, 1.0), 0.036, "VH_Steel", 12)
        B(w, (-1.3, ty, 0.775), (-1.16, ty + 0.004, 0.79), "VH_Steel")
    # cord from the hot plate along the back of the table to the socket strip
    if lod == 0:
        s.iprops.tube([(hp[0] + 0.1, ty + 0.02, hp[1] + 0.08), (-0.85, ty + 0.004, LF - 0.02), (-0.72, ty + 0.03, LF - 0.02),
                       (-0.585, 1.3, LF - 0.03)], 0.004, "VH_Rubber", 5)
    stool(s)
    # inside window sill with a tin of succulents, a curtain pushed to one side
    sill(s)


def kettle(s, base):
    w, lod = s.iprops, s.lod
    x, y, z = base
    n = 18 if lod == 0 else 8
    rings = [ring((x, y, z), 0.07, 0.07, n), ring((x, y + 0.01, z), 0.078, 0.078, n), ring((x, y + 0.09, z), 0.074, 0.074, n),
             ring((x, y + 0.13, z), 0.055, 0.055, n), ring((x, y + 0.14, z), 0.045, 0.045, n)]
    loft(w, rings, "SS_Enamel")
    w.cyl((x, y + 0.14, z), (x, y + 0.146, z), 0.047, "VH_Dark", n)
    w.sphere((x, y + 0.146, z), 0.02, "VH_Dark", 8, hemi_axis=(0, 1, 0))
    w.cyl((x + 0.06, y + 0.04, z), (x + 0.13, y + 0.11, z), 0.014, "SS_Enamel", 8, r2=0.008)
    w.tube([(x - 0.045, y + 0.14, z), (x - 0.03, y + 0.2, z), (x + 0.03, y + 0.2, z), (x + 0.045, y + 0.14, z)], 0.005, "VH_Dark", 6)
    if lod == 0:
        F = Frame((x, 0, z), (0, 0, -1), (-1, 0, 0))
        poly(w, [(x - 0.0782, y + 0.02, z - 0.01), (x - 0.0782, y + 0.02, z + 0.025), (x - 0.0782, y + 0.04, z + 0.02),
                 (x - 0.0782, y + 0.035, z - 0.005)], "VH_Dark", (-1, 0, 0))      # chipped enamel


def stool(s):
    w, m, lod = s.iprops, s.imetal, s.lod
    cx, cz = STOOL
    sy = FY + 0.45
    w.cyl((cx, sy - 0.03, cz), (cx, sy, cz), 0.15, "SS_Timber", 18 if lod == 0 else 10)
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.3
        top = (cx + math.cos(a) * 0.09, sy - 0.03, cz + math.sin(a) * 0.09)
        foot = (cx + math.cos(a) * 0.15, FY, cz + math.sin(a) * 0.15)
        m.cyl(top, foot, 0.012, "VH_Steel", 8)
    if lod == 0:
        loop_tube(m, [(cx + math.cos(a) * 0.132, FY + 0.16, cz + math.sin(a) * 0.132) for a in [2 * math.pi * k / 12 for k in range(12)]],
                  0.006, "VH_Steel", 6)


def sill(s):
    w, c, m, lod = s.iprops, s.icloth, s.imetal, s.lod
    wx0, wx1, wy0, wy1 = WIN_FRAME
    B(w, (wx0 - 0.02, wy0 - 0.02, 1.0), (wx1 + 0.02, wy0, 1.095), "SS_Timber")
    tx, tz = -0.95, 1.05
    w.cyl((tx, wy0, tz), (tx, wy0 + 0.075, tz), 0.04, "VH_Steel", 12 if lod == 0 else 8)
    if lod == 0:
        rr = drng("succ")
        for k in range(7):
            a = 2 * math.pi * k / 7 + rr.uniform(-0.2, 0.2)
            el = rr.uniform(0.6, 1.2)
            d = Vector((math.cos(a) * math.cos(el), math.sin(el), math.sin(a) * math.cos(el)))
            base = Vector((tx, wy0 + 0.07, tz))
            fs = w.sphere((0, 0, 0), 1.0, "HP_Succulent", 8)
            for v in {v for f in fs for v in f.verts}:
                p = v.co.copy()
                q = d * (0.035 + p.z * 0.035) + Vector((p.x * 0.012, p.y * 0.009, 0))
                v.co = base + q
    # curtain wire and a bone cloth curtain bunched at the west side of the window
    m.cyl((wx0 - 0.03, 2.31, 1.075), (wx1 + 0.03, 2.31, 1.075), 0.003, "VH_Steel", 5)
    for xx in (wx0 - 0.03, wx1 + 0.03):
        m.cyl((xx, 2.31, 1.075), (xx, 2.31, LF), 0.005, "VH_Steel", 6)
    ni, nj = (26, 16) if lod == 0 else (6, 4)
    xa, xb, ya, yb = wx0 + 0.01, wx0 + 0.36, 1.42, 2.3

    def cp(i, j):
        u, v = i / (ni - 1), j / (nj - 1)
        x = lerp(xa, xb, u)
        y = lerp(yb, ya, v)
        amp = 0.024 * (1 - 0.3 * v)
        z = 1.055 + amp * math.sin(u * math.pi * 9) + 0.004 * nz((x, y, 0), 13, 1.0)
        x += 0.03 * v * u          # spreads a little towards the hem
        return Vector((x, y, z))
    P = [[cp(i, j) for j in range(nj)] for i in range(ni)]
    sheet(c, P, "WS_ClothBone", 0.004, lambda p: (0, 0, -1))
    for k in range(5 if lod == 0 else 0):
        m.cyl((xa + k * 0.07, 2.31, 1.075), (xa + k * 0.07, 2.295, 1.06), 0.006, "VH_Steel", 6)


# ====================================================================== services: power, light, air, fire
def services(s):
    m, g, w, hd, lod = s.imetal, s.iglow, s.iprops, s.ihard, s.lod
    # cable tray down the ceiling with cables in it; the light hangs from it
    T = TRAY
    ty = T["y"]
    B(m, (T["x0"], ty - 0.044, T["z"] - 0.05), (T["x1"], ty - 0.04, T["z"] + 0.05), "VH_Steel")
    for zz in (T["z"] - 0.05, T["z"] + 0.046):
        B(m, (T["x0"], ty - 0.044, zz), (T["x1"], ty, zz + 0.004), "VH_Steel")
    x = T["x0"] + 0.1
    while x < T["x1"]:
        m.cyl((x, LC, T["z"]), (x, ty - 0.044, T["z"]), 0.004, "VH_Steel", 6)              # drop rod
        B(m, (x - 0.01, ty - 0.05, T["z"] - 0.06), (x + 0.01, ty - 0.044, T["z"] + 0.06), "VH_Steel")
        x += 0.75
    if lod == 0:
        for k, (dz, r) in enumerate(((-0.025, 0.008), (0.0, 0.006), (0.024, 0.009))):
            m.cyl((T["x0"] - 0.02, ty - 0.034, T["z"] + dz), (T["x1"] + 0.02, ty - 0.034, T["z"] + dz), r, "VH_Rubber", 6)
        # one cable sags out of the tray between two hangers
        s.iprops.tube([(-0.9, ty - 0.03, T["z"] + 0.05), (-0.75, ty - 0.1, T["z"] + 0.08), (-0.45, ty - 0.12, T["z"] + 0.08),
                       (-0.3, ty - 0.03, T["z"] + 0.05)], 0.006, "VH_Rubber", 6)
    # caged bulb under the tray
    bx, by, bz = BULB
    m.cyl((bx, ty - 0.044, bz), (bx, by + 0.065, bz), 0.004, "VH_Rubber", 6)
    m.cyl((bx, by + 0.065, bz), (bx, by + 0.03, bz), 0.018, "VH_Dark", 10)
    g.sphere((bx, by, bz), 0.03, "SS_BulbWarm", 12 if lod == 0 else 6)
    cage_r = 0.055
    for k in range(6 if lod == 0 else 3):
        a = 2 * math.pi * k / 6
        p0 = (bx + math.cos(a) * 0.02, by + 0.035, bz + math.sin(a) * 0.02)
        p1 = (bx + math.cos(a) * cage_r, by, bz + math.sin(a) * cage_r)
        p2 = (bx + math.cos(a) * 0.015, by - 0.06, bz + math.sin(a) * 0.015)
        m.tube([p0, p1, p2], 0.0022, "VH_Steel", 4)
    if lod == 0:
        loop_tube(m, [(bx + math.cos(2 * math.pi * k / 12) * cage_r, by, bz + math.sin(2 * math.pi * k / 12) * cage_r) for k in range(12)], 0.0025,
                  "VH_Steel", 4)
    # junction box behind the exterior one, conduit up and across the ceiling to the tray
    jx, jy = JBOX
    B(m, (jx - 0.09, jy - 0.09, LF - 0.075), (jx + 0.09, jy + 0.09, LF), "WG_BonePaint")
    B(m, (jx - 0.095, jy - 0.095, LF - 0.08), (jx + 0.095, jy + 0.095, LF - 0.072), "WG_BonePaint")
    m.tube([(jx, jy + 0.095, LF - 0.035), (jx, LC - 0.02, LF - 0.035), (jx, LC - 0.02, T["z"] + 0.06)], 0.011, "VH_Steel", 8, clamps=0.5)
    if lod == 0:
        for (dx, dy) in ((-0.075, -0.075), (0.075, -0.075), (-0.075, 0.075), (0.075, 0.075)):
            hd.cyl((jx + dx, jy + dy, LF - 0.08), (jx + dx, jy + dy, LF - 0.083), 0.006, "VH_Steel", 6)
    # charge controller with a small cyan readout and a status LED; battery on the floor; socket strip by the table
    cx, cy = -0.12, 1.62
    B(m, (cx - 0.08, cy - 0.055, LF - 0.045), (cx + 0.08, cy + 0.055, LF), "WS_PanelDark")
    B(g, (cx - 0.05, cy + 0.005, LF - 0.0465), (cx + 0.02, cy + 0.035, LF - 0.045), "WB_ScreenCyan")
    led = (cx + 0.05, cy + 0.02, LF - 0.047)
    g.sphere(led, 0.005, "WB_LedCyan", 8 if lod == 0 else 6)
    s.rec["_status_led"] = led
    bx0, bx1, bz0 = -0.62, -0.22, 0.86
    B(w, (bx0, FY, bz0), (bx1, FY + 0.22, LF - 0.02), "WG_OlivePaint")
    B(w, (bx0 + 0.02, FY + 0.22, bz0 + 0.02), (bx1 - 0.02, FY + 0.235, LF - 0.04), "VH_Dark")
    for (xx, mat) in ((bx0 + 0.07, "WS_PaintRed"), (bx1 - 0.07, "VH_Dark")):
        w.cyl((xx, FY + 0.235, (bz0 + LF) / 2), (xx, FY + 0.26, (bz0 + LF) / 2), 0.012, mat, 8)
    if lod == 0:
        for (xx, yoff) in ((bx0 + 0.07, 0.0), (bx1 - 0.07, 0.01)):
            w.tube([(xx, FY + 0.26, (bz0 + LF) / 2), (xx, FY + 0.32, (bz0 + LF) / 2 + 0.04), (cx - 0.04 + yoff, cy - 0.15, LF - 0.025),
                    (cx - 0.04 + yoff, cy - 0.055, LF - 0.025)], 0.005, "VH_Rubber", 5)
        w.tube([(cx + 0.04, cy + 0.055, LF - 0.025), (cx + 0.04, jy - 0.03, LF - 0.025), (jx + 0.09, jy - 0.03, LF - 0.03)], 0.005, "VH_Rubber", 5)
        patch(m, Frame((0, 0, LF - 0.075 + 0.0), (1, 0, 0), (0, 0, -1)), jx, jy, -0.0005, 0.04, 0.03, "WG_RustSteel", "jbrust")
    B(w, (-0.6, 1.278, LF - 0.035), (-0.3, 1.322, LF), "WG_BonePaint")
    if lod == 0:
        for k in range(4):
            B(w, (-0.57 + k * 0.07, 1.29, LF - 0.0355), (-0.53 + k * 0.07, 1.31, LF - 0.035), "VH_Dark")
        w.tube([(-0.3, 1.3, LF - 0.02), (-0.2, 1.35, LF - 0.02), (-0.2, cy - 0.055, LF - 0.02)], 0.004, "VH_Rubber", 5)
    # socket by the bunk foot (reading lamp), cable up to the tray
    sx = BED["x1"] + 0.12
    B(w, (sx - 0.045, FY + 0.18, LB), (sx + 0.045, FY + 0.27, LB + 0.035), "WG_BonePaint")
    if lod == 0:
        w.tube([(sx, FY + 0.27, LB + 0.015), (sx, LC - 0.02, LB + 0.015), (sx, LC - 0.02, T["z"] - 0.06)], 0.005, "VH_Rubber", 5)
    # AC indoor grille on the back wall (the unit hangs outside between the container and the curtain wall)
    ax0, ax1, ay0, ay1 = -1.62, -1.18, 2.42, 2.64
    B(m, (ax0, ay0, LB), (ax1, ay1, LB + 0.05), "WG_BonePaint")
    if lod == 0:
        for k in range(7):
            yy = lerp(ay0 + 0.03, ay1 - 0.03, k / 6)
            B(m, (ax0 + 0.03, yy - 0.006, LB + 0.05), (ax1 - 0.03, yy + 0.006, LB + 0.053), "VH_Dark")
        for k in range(3):
            patch(m, Frame((0, 0, LB + 0.05), (1, 0, 0), (0, 0, 1)), lerp(ax0 + 0.05, ax1 - 0.05, k / 2), ay0 + 0.02, 0.0006, 0.02, 0.05,
                  "WG_RustSteel", ("acdrip", k), n=6)
    # fire extinguisher on a wall bracket east of the door
    ex, ez = 2.14, LF - 0.075
    B(m, (ex - 0.03, FY + 0.28, LF - 0.012), (ex + 0.03, FY + 0.62, LF), "VH_Steel")
    for yy in (FY + 0.33, FY + 0.55):
        m.cyl((ex, yy, ez), (ex, yy + 0.02, ez), 0.068, "VH_Steel", 14 if lod == 0 else 8)
    _AB.cyl_uv(m, (ex, FY + 0.15, ez), (ex, FY + 0.6, ez), 0.065, "WB_CylRed", 16 if lod == 0 else 8)
    m.sphere((ex, FY + 0.6, ez), 0.065, "WB_CylRed", 12 if lod == 0 else 6, hemi_axis=(0, 1, 0))
    B(m, (ex - 0.02, FY + 0.65, ez - 0.02), (ex + 0.02, FY + 0.7, ez + 0.02), "VH_Dark")
    B(m, (ex - 0.02, FY + 0.7, ez - 0.012), (ex + 0.1, FY + 0.715, ez + 0.012), "VH_Steel")
    m.cyl((ex, FY + 0.69, ez + 0.02), (ex, FY + 0.69, ez + 0.035), 0.016, "WB_PaintBone", 10)
    m.tube([(ex - 0.02, FY + 0.67, ez), (ex - 0.09, FY + 0.6, ez - 0.02), (ex - 0.09, FY + 0.3, ez - 0.02)], 0.009, "VH_Rubber", 6)
    _AB.cyl_uv(m, (ex, FY + 0.38, ez), (ex, FY + 0.46, ez), 0.0655, "WB_CylBone", 16 if lod == 0 else 8)


# ====================================================================== life: clothes, mirror, photo, calendar, crate
def life(s):
    w, c, m, lod = s.iprops, s.icloth, s.imetal, s.lod
    # peg rail on the back wall between the bunk and the locker
    py = 2.065
    B(w, (-0.78, py - 0.045, LB), (0.24, py + 0.045, LB + 0.022), "SS_Timber")
    pegs = [-0.52, -0.18, 0.12]
    for px in pegs:
        m.cyl((px, py, LB + 0.022), (px, py + 0.03, LB + 0.09), 0.009, "VH_Steel", 8)
        m.sphere((px, py + 0.03, LB + 0.09), 0.012, "VH_Brass", 8)
    coat(s, (pegs[0], py + 0.02, LB + 0.07))
    scarf(s, (pegs[1], py + 0.02, LB + 0.07))
    hat(s, (pegs[2], py + 0.02, LB + 0.07))
    # calendar on the back wall by the locker (texture HP_Calendar), held by a nail
    cx0, cx1, cy0, cy1 = 0.2, 0.5, 1.08, 1.5
    calendar_quad(w, cx0, cx1, cy0, cy1, LB + 0.002)
    w.sphere(((cx0 + cx1) / 2, cy1 - 0.015, LB + 0.004), 0.005, "VH_Steel", 6)
    # mirror shard glued to the front wall west of the window, three bent tabs; a photo tucked under its corner
    Ff = WALLS["front"]
    mu, my = 2.45, 1.92            # u = -x
    rr = drng("mirror")
    outline = [(mu - 0.11, my - 0.15), (mu + 0.09, my - 0.17), (mu + 0.13, my + 0.02), (mu + 0.04, my + 0.16), (mu - 0.12, my + 0.12)]
    d = BD + PT
    base = [Ff.P(u, y, d + 0.001) for u, y in outline]
    face = [Ff.P(u, y, d + 0.005) for u, y in outline]
    bm = w.bm
    vb = [bm.verts.new(p) for p in base]
    vf = [bm.verts.new(p) for p in face]
    f = bm.faces.new(vf)
    f.material_index = w.mi("HP_Mirror")
    orient(f, Ff.n)
    for i in range(len(vb)):
        j = (i + 1) % len(vb)
        e = bm.faces.new([vb[i], vb[j], vf[j], vf[i]])
        e.material_index = w.mi("VH_Dark")
        orient(e, (face[i] + face[j]) / 2 - sum(face, Vector()) / len(face))
    for (u, y) in ((mu - 0.1, my + 0.1), (mu + 0.11, my + 0.0), (mu - 0.02, my - 0.16)):
        Ff.box(m, u - 0.012, u + 0.012, y - 0.012, y + 0.012, d, d + 0.0075, "VH_Steel", skip=("s0",))
    photo_quad(w, Ff, mu + 0.12, my - 0.12, 0.09, 0.13, -0.18, d + 0.0025)
    # side crate at the head of the bunk: a slatted timber crate on end, a book, a bottle and a candle in a tin on it
    side_crate(s)
    # coil of rope on a hook on the east wall above the crates
    Fe = WALLS["east"]
    m.cyl(tuple(Fe.P(0.62, 1.85, d)), tuple(Fe.P(0.62, 1.88, d + 0.07)), 0.008, "VH_Steel", 6)
    for k in range(3 if lod == 0 else 1):
        nseg = 20 if lod == 0 else 10
        loop = [Fe.P(0.62 + 0.01 * k + math.cos(a) * 0.13, 1.66 - 0.01 * k + math.sin(a) * 0.19, d + 0.05 + 0.012 * k)
                for a in [2 * math.pi * i / nseg for i in range(nseg)]]
        loop_tube(w, loop, 0.011 if lod == 0 else 0.02, "WL_HessianOld" if k != 1 else "WG_Hessian", 6 if lod == 0 else 4)
    # sand blown in across the threshold
    s.mound((1.375, FY + 0.019, 1.05), 0.42, 0.11, 0.0065)
    s.mound((1.2, FY + 0.019, 0.97), 0.16, 0.06, 0.004)


def calendar_quad(part, x0, x1, y0, y1, z):
    """Calendar sheet facing +Z with exact UVs (0..1) for HP_Calendar; a slight curl at the bottom."""
    bm = part.bm
    nv = 4
    rows = []
    for j in range(nv + 1):
        t = j / nv
        y = lerp(y0, y1, t)
        zc = z + (0.012 * (1 - t) ** 3)
        rows.append((bm.verts.new((x0, y, zc)), bm.verts.new((x1, y, zc)), t))
    mi = part.mi("HP_Calendar")
    for (a0, a1, t0), (b0, b1, t1) in zip(rows, rows[1:]):
        f = bm.faces.new([a0, a1, b1, b0])
        f.material_index = mi
        orient(f, (0, 0, 1))


def photo_quad(part, F, uc, yc, wdt, hgt, rot, d):
    """Small photo on frame F, rotated rot radians, for HP_Photo (exact UVs set after build)."""
    pts = []
    for (du, dy) in ((-wdt / 2, -hgt / 2), (wdt / 2, -hgt / 2), (wdt / 2, hgt / 2), (-wdt / 2, hgt / 2)):
        u = uc + du * math.cos(rot) - dy * math.sin(rot)
        y = yc + du * math.sin(rot) + dy * math.cos(rot)
        pts.append(F.P(u, y, d))
    poly(part, pts, "HP_Photo", F.n)


def coat(s, hook):
    """Long canvas duster hanging from a peg by its loop: lofted cross-sections from the collar to the hem, folds that
    deepen towards the hem, the sleeves hanging at the sides."""
    c, lod = s.icloth, s.lod
    hx, hy, hz = hook
    zb = LB + 0.004
    n = 20 if lod == 0 else 8
    secs = [(hy - 0.02, 0.05, 0.02), (hy - 0.08, 0.12, 0.045), (hy - 0.2, 0.22, 0.075), (hy - 0.32, 0.25, 0.08),
            (hy - 0.6, 0.25, 0.07), (hy - 0.85, 0.27, 0.065), (hy - 1.0, 0.29, 0.06)]
    rings_ = []
    for k, (y, hw, hd) in enumerate(secs):
        fold = 0.0 if k < 3 else 0.18 * (k - 2) / (len(secs) - 3)
        zc = zb + hd + 0.003
        rings_.append(ring((hx, y, zc), hw, hd, n, ax="y",
                           wob=lambda i, a, fold=fold, k=k: 1 + fold * math.sin(a * 5 + k * 0.7) * (0.6 + 0.4 * math.cos(a))))
    # flatten the wall side so it lies against the lining
    for rg in rings_:
        for p in rg:
            p.z = max(p.z, zb)
    loft(c, rings_, "WS_Hide")
    for sg in (-1, 1):
        sl = [ring((hx + sg * 0.21, hy - 0.22, zb + 0.07), 0.05, 0.045, 10 if lod == 0 else 6),
              ring((hx + sg * 0.24, hy - 0.5, zb + 0.075), 0.055, 0.045, 10 if lod == 0 else 6),
              ring((hx + sg * 0.24, hy - 0.78, zb + 0.075), 0.06, 0.045, 10 if lod == 0 else 6)]
        loft(c, sl, "WS_Hide")
    c.cyl((hx, hy - 0.02, zb + 0.02), (hx, hy + 0.01, LB + 0.075), 0.006, "WS_Hide", 6)       # hanging loop


def scarf(s, hook):
    c, lod = s.icloth, s.lod
    hx, hy, hz = hook
    zb = LB + 0.04
    for (dx, L_, ph, dz) in ((-0.03, 0.42, 0.0, 0.0), (0.035, 0.62, 1.3, 0.012)):
        ni, nj = (18, 4) if lod == 0 else (4, 2)
        P = []
        for i in range(ni):
            t = i / (ni - 1)
            row = []
            for j in range(nj):
                u = j / (nj - 1)
                tw = 0.6 * math.sin(t * 2.6 + ph)          # a loose twist down the tail
                x = hx + dx + (u - 0.5) * 0.095 * math.cos(tw) + 0.015 * math.sin(t * 3 + ph)
                y = hy - 0.01 - t * L_
                z = zb + 0.012 + dz + 0.02 * t + (u - 0.5) * 0.095 * math.sin(tw) * 0.5
                row.append(Vector((x, y, z)))
            P.append(row)
        sheet(c, P, "WS_ClothIndigo", 0.005, lambda p: (0, 0, 1))
        if lod == 0:                                       # fringe at the end of each tail
            yb_ = hy - 0.01 - L_
            for k in range(7):
                fx_ = P[-1][0].x + (P[-1][-1].x - P[-1][0].x) * k / 6
                c.cyl((fx_, yb_ + 0.002, P[-1][0].z), (fx_ + 0.003, yb_ - 0.04, P[-1][0].z + 0.004), 0.0025, "WS_ClothBone", 4)
    c.cyl((hx - 0.06, hy - 0.01, zb + 0.016), (hx + 0.06, hy - 0.01, zb + 0.016), 0.02, "WS_ClothIndigo", 8)


def hat(s, hook):
    """Wide-brimmed leather hat hung by its crown on the peg, brim against the wall."""
    c, lod = s.icloth, s.lod
    hx, hy, hz = hook
    n = 24 if lod == 0 else 10
    cz = LB + 0.03
    cy = hy - 0.1
    brim = []
    for (r, dz) in ((0.2, 0.0), (0.2, 0.008), (0.1, 0.012), (0.1, 0.0)):
        brim.append([Vector((hx + math.cos(a) * r, cy + math.sin(a) * r * 0.95, cz + dz + 0.012 * math.sin(a * 2)))
                     for a in [2 * math.pi * i / n for i in range(n)]])
    bm = c.bm
    V = [[bm.verts.new(p) for p in rg] for rg in brim]
    mi = c.mi("FS_Felt")
    fs = []
    for a, b in zip(V, V[1:] + V[:1]):
        for i in range(n):
            j = (i + 1) % n
            fs.append(bm.faces.new([a[i], a[j], b[j], b[i]]))
    for f in fs:
        f.material_index = mi
    bmesh.ops.recalc_face_normals(bm, faces=fs)
    crown = [ring((hx, cy, cz + 0.01), 0.095, 0.085, n, ax="z"), ring((hx, cy, cz + 0.09), 0.09, 0.08, n, ax="z"),
             ring((hx, cy, cz + 0.11), 0.06, 0.05, n, ax="z")]
    loft(c, crown, "FS_Felt")
    c.cyl((hx, cy, cz + 0.012), (hx, cy, cz + 0.04), 0.1, "WS_ClothMadder", n)        # band


def side_crate(s):
    w, lod = s.iprops, s.lod
    S = SIDE_CRATE
    x0, x1, z0, z1, h = S["x0"], S["x1"], S["z0"], S["z1"], S["h"]
    y0, y1 = FY, FY + h
    # corner posts and slats
    for (xx, zz) in ((x0, z0), (x1 - 0.035, z0), (x0, z1 - 0.035), (x1 - 0.035, z1 - 0.035)):
        B(w, (xx, y0, zz), (xx + 0.035, y1, zz + 0.035), "SS_Timber")
    nsl = 4
    for k in range(nsl):
        ya = lerp(y0 + 0.01, y1 - 0.02, k / nsl)
        yb = ya + (y1 - y0 - 0.03) / nsl - 0.02
        B(w, (x0 + 0.035, ya, z1 - 0.02), (x1 - 0.035, yb, z1), "SS_Timber")      # front (faces +z)
        B(w, (x1 - 0.02, ya, z0 + 0.035), (x1, yb, z1 - 0.035), "SS_Timber")      # bed-side face
        B(w, (x0 + 0.035, ya, z0), (x1 - 0.035, yb, z0 + 0.02), "SS_Timber")
    B(w, (x0 + 0.02, y0 + 0.01, z0 + 0.02), (x1 - 0.02, y1 - 0.05, z1 - 0.02), "VH_Dark")      # shadowed inside
    B(w, (x0 - 0.005, y1, z0 - 0.005), (x1 + 0.005, y1 + 0.02, z1 + 0.005), "SS_Timber")       # lid
    ty = y1 + 0.02
    B(w, (x0 + 0.05, ty, z0 + 0.06), (x0 + 0.21, ty + 0.035, z0 + 0.3), "WS_ClothIndigo")    # book
    B(w, (x0 + 0.055, ty + 0.002, z0 + 0.065), (x0 + 0.205, ty + 0.033, z0 + 0.297), "WB_PaintBone") if lod == 0 else None
    w.cyl((x1 - 0.1, ty, z1 - 0.1), (x1 - 0.1, ty + 0.2, z1 - 0.1), 0.035, "VH_Steel", 12 if lod == 0 else 8)   # bottle
    w.cyl((x1 - 0.1, ty + 0.2, z1 - 0.1), (x1 - 0.1, ty + 0.23, z1 - 0.1), 0.015, "VH_Dark", 8)
    w.cyl((x1 - 0.1, ty, z0 + 0.12), (x1 - 0.1, ty + 0.05, z0 + 0.12), 0.04, "VH_Steel", 12 if lod == 0 else 8)  # candle tin
    w.cyl((x1 - 0.1, ty + 0.01, z0 + 0.12), (x1 - 0.1, ty + 0.07, z0 + 0.12), 0.022, "WB_PaintBone", 10 if lod == 0 else 6)


# ====================================================================== record: colliders, anchors, lights, mounts
def record(s):
    rec = s.rec
    cols = [c_ for c_ in rec["colliders"] if c_["name"] != "COL_Container"]

    def box(name, lo, hi, **extra):
        cen = [round((a + b) / 2, 4) for a, b in zip(lo, hi)]
        size = [round(b - a, 4) for a, b in zip(lo, hi)]
        d = {"name": name, "center": cen, "size": size}
        d.update(extra)
        return d
    fx0, fx1, ftop = DOOR_FRAME
    cols += [
        box("COL_Floor", (-3.1, 0.0, -1.3), (3.1, FY, 1.3)),
        box("COL_Roof", (-3.1, LC, -1.3), (3.1, 2.92, 1.3)),
        box("COL_WallBack", (-3.1, 0.0, -1.3), (3.1, 2.92, LB)),
        box("COL_WallWest", (-3.1, 0.0, LB), (LW, 2.92, LF)),
        box("COL_WallEast", (LE, 0.0, LB), (3.1, 2.92, LF)),
        box("COL_WallFrontWest", (-3.1, 0.0, LF), (DOOR[0], 2.92, 1.3)),
        box("COL_WallFrontEast", (DOOR[1], 0.0, LF), (3.1, 2.92, 1.3)),
        box("COL_DoorHead", (DOOR[0], DOOR[2], LF), (DOOR[1], 2.92, 1.22)),
        box("COL_Bunk", (BED["x0"] - 0.03, FY, LB), (BED["x1"] + 0.02, MATT["y1"] + 0.03, BED["z1"] + 0.03)),
        box("COL_BunkHead", (BED["x0"] - 0.03, FY, LB), (BED["x0"] + 0.06, BED["head"], BED["z1"] + 0.03)),
        box("COL_Locker", (LOCKER["x0"] - 0.01, FY, LB), (LOCKER["x1"] + 0.01, LOCKER["y1"] + 0.15, LOCKER["z1"] + 0.03)),
        box("COL_Rack", (RACK["x0"] - 0.02, FY, LB), (RACK["x1"] + 0.02, RACK["top"], RACK["z1"] + 0.03)),
        box("COL_Table", (TABLE["x0"] - 0.01, FY, TABLE["z0"] - 0.01), (TABLE["x1"] + 0.01, TABLE["top"] + 0.03, LF)),
        box("COL_Stool", (STOOL[0] - 0.16, FY, STOOL[1] - 0.16), (STOOL[0] + 0.16, FY + 0.45, STOOL[1] + 0.16)),
        box("COL_SideCrate", (SIDE_CRATE["x0"], FY, SIDE_CRATE["z0"]), (SIDE_CRATE["x1"], FY + SIDE_CRATE["h"] + 0.02, SIDE_CRATE["z1"])),
        box("COL_Battery", (-0.62, FY, 0.86), (-0.22, FY + 0.26, LF)),
        box("COL_CrateStack", (2.3, FY, 0.24), (2.9, FY + 0.6, 1.08)),
        box("COL_StepLow", (0.73, 0.0, 1.92), (2.03, 0.15, 2.32)),
    ]
    lx = LEAF
    leaf_c = box("COL_DoorLeaf", (lx["x0"], lx["y0"], lx["z0"]), (lx["x1"], lx["y1"], lx["z1"] + 0.02))
    leaf_c["closed"] = True
    leaf_c["local_center"] = [round(leaf_c["center"][0] - HINGE[0], 4), round(leaf_c["center"][1] - HINGE[1], 4),
                              round(leaf_c["center"][2] - HINGE[2], 4)]
    leaf_c["note"] = "child of the leaf: local_center is relative to the hinge (the leaf object's origin)"
    cols.append(leaf_c)
    rec["colliders"] = cols
    bulb, aim = rec.pop("_reading_lamp")
    led = rec.pop("_status_led")
    tgt = bulb + aim * 1.0
    rec["lights"] += [
        {"name": "Home ceiling light", "type": "point", "pos": list(BULB), "color": [1.0, 0.76, 0.5], "intensity": 2.0, "range": 5.0,
         "clock": False, "interior": True, "shadows": "soft"},
        {"name": "Home reading lamp", "type": "spot", "pos": [round(v, 4) for v in bulb], "target": [round(v, 4) for v in tgt],
         "color": [1.0, 0.72, 0.42], "intensity": 1.3, "range": 2.6, "angle": 75.0, "inner": 40.0, "clock": False, "interior": True},
        {"name": "Home status LED", "type": "point", "pos": [round(v, 4) for v in led], "color": [0.3, 0.85, 1.0], "intensity": 0.12,
         "range": 0.7, "clock": False, "interior": True, "shadows": "none"},
    ]
    SD = _AB.SD
    # A's wooden bucket stood in the opening leaf's arc (0.84 m from the hinge, 0.55 tall vs the leaf's 0.51 foot)
    for m_ in rec["mounts"]:
        if m_["name"] == "Bucket":
            m_["pos"] = [-0.15, 0.0, 2.2]
    R = RACK
    lv = [l + 0.018 for l in R["levels"]]
    zr = R["z1"] - 0.225          # footprint centre of items on the rack (rack depth 0.45)
    rec["mounts"] += [
        {"name": "Rack: wooden box", "path": SD + "SD_crate_wood.prefab", "pos": [2.12, lv[0], zr], "yaw": 0, "interior": True},
        {"name": "Rack: jerrycan", "path": SD + "SD_jerrycan_green.prefab", "pos": [2.69, lv[0], zr], "yaw": 90, "interior": True},
        {"name": "Rack: toolbox", "path": SD + "SD_toolbox.prefab", "pos": [1.9, lv[1], zr + 0.04], "yaw": 0, "interior": True},
        {"name": "Rack: red crate", "path": SD + "SD_crate_red.prefab", "pos": [2.58, lv[1], zr + 0.05], "yaw": 0, "interior": True},
        {"name": "Rack: salvage crate", "path": SD + "SD_crate_yellow.prefab", "pos": [1.97, lv[2], zr], "yaw": 0, "interior": True},
        {"name": "Rack: carton", "path": SD + "SD_carton.prefab", "pos": [1.95, lv[3], zr], "yaw": 90, "interior": True},
        {"name": "Rack: oil tin", "path": SD + "SD_oil_tin.prefab", "pos": [2.27, lv[3], zr + 0.1], "yaw": 15, "interior": True},
        {"name": "Spillover: ammo crate", "path": SD + "SD_ammo_crate_a.prefab", "pos": [2.58, FY, 0.64], "yaw": 90, "interior": True},
        {"name": "Spillover: red crate", "path": SD + "SD_crate_red.prefab", "pos": [2.58, FY + 0.301, 0.6], "yaw": 85, "interior": True},
        {"name": "Under the bunk: crate", "path": SD + "SD_crate_yellow.prefab", "pos": [-1.55, FY, -0.68], "yaw": 4, "interior": True},
    ]
    xin = (DOOR[0] + DOOR[1]) / 2
    floor_c = [round((LW + LE) / 2, 4), round((FY + LC) / 2, 4), 0.0]
    rec["anchors"] = {
        "door_hinge": {"pos": list(HINGE), "axis": [0, 1, 0], "closedYaw": 0.0, "openYaw": OPEN_YAW, "swing": "outward",
                       "leaf": f"{s.name}_DoorLeaf_LOD0 (and _LOD1)", "radius": 1.03,
                       "note": "leaf object origin = hinge axis at the leaf's foot; the free edge swings out over the step (half-disc "
                               "of radius 1.03 in front of the door, leaf foot at 0.51 above the steps and planter) and parks flat "
                               "against the face west of the door (x -0.16..0.86, 6-14 cm off the corrugation); |openYaw| < 180 so "
                               "LerpAngle takes the outward way"},
        "locker_use": {"pos": [round((LOCKER["x0"] + LOCKER["x1"]) / 2, 4), FY + 1.0, -0.3], "yaw": 180.0, "floor_y": FY,
                       "note": "1.0 m above the interior floor, 0.3 m in front of the doors; yaw faces the locker (-Z)"},
        "bunk_use": {"pos": [-1.85, FY + 1.0, 0.05], "yaw": 180.0, "floor_y": FY, "note": "beside the bunk, facing it"},
        "wake_point": {"pos": [-1.7, FY, 0.2], "yaw": 90.0, "note": "floor point beside the bunk; yaw faces the room and door (+X)"},
        "interior_bounds": {"center": [floor_c[0], floor_c[1], 0.0], "size": [round(LE - LW, 4), round(LC - FY, 4), round(LF - LB, 4)],
                            "note": "the air volume inside the lining (camera zone / interior lighting volume)"},
        "door_centre": {"pos": [xin, 0.502, 1.16], "yaw": 180.0, "note": "floor point at the middle of the doorway (on the threshold plate)"},
        "door_inside": {"pos": [xin, FY, 0.62], "yaw": 180.0},
        "door_outside": {"pos": [xin, 0.30, 1.62], "yaw": 0.0, "note": "on the upper step, inside the leaf's swing; clear of it at z > 2.33"},
        "door_clear_outside": {"pos": [xin, 0.15, 2.4], "yaw": 0.0, "note": "lower step edge, outside the leaf's swing"},
    }
    rec["interior"] = {
        "note": "player home (art/ward_home_20261005/home_interior.py); building-local metres",
        "floor_y": FY, "ceiling_y": LC, "lining": {"x": [LW, LE], "z": [LB, LF]},
        "door": {"clear": [DOOR[0], DOOR[1]], "head": DOOR[2], "threshold_y": 0.502, "frame": [fx0, fx1, ftop]},
        "window": {"glass": list(WIN), "frame": list(WIN_FRAME), "material": "WS_ClearGlass (both faces)"},
        "bunk": {"x": [BED["x0"], BED["x1"]], "z": [BED["z0"], BED["z1"]], "mattress_top": MATT["y1"]},
        "locker": {"x": [LOCKER["x0"], LOCKER["x1"]], "z": [LOCKER["z0"], LOCKER["z1"]], "y": [LOCKER["y0"], LOCKER["y1"]]},
        "rack": {"x": [RACK["x0"], RACK["x1"]], "z": [RACK["z0"], RACK["z1"]], "levels": list(RACK["levels"]), "top": RACK["top"]},
        "table": {"x": [TABLE["x0"], TABLE["x1"]], "z": [TABLE["z0"], TABLE["z1"]], "top": TABLE["top"]},
        "walk_path": "door -> locker: x 0.9..1.85 from z 1.1 to -0.55 (1.7 m deep); door -> bunk side: z -0.21..0.67 between "
                     "the blanket's hang and the stool/table (0.88-0.92 m), nothing below 2.50 m overhead",
        "parts": "Interior parts are separate objects so Unity can put them on the interior light layer: InteriorLining, "
                 "InteriorFloor, InteriorMetal, InteriorCloth, InteriorProps, InteriorHardware (no shadows), InteriorGlow (bulbs, LED, "
                 "readout); LockerStencil; DoorLeaf (moving).",
    }
    rec["decal_hints"] = [
        {"name": "scuffs inside the door", "material": "WL_DecalMarks", "pos": [1.375, FY, 0.4], "size": [0.9, 0.6], "normal": [0, 1, 0]},
        {"name": "scuffs at the locker", "material": "WL_DecalMarks", "pos": [1.1, FY, -0.15], "size": [0.9, 0.5], "normal": [0, 1, 0]},
        {"name": "grime round the door handle (inside)", "material": "WG_DecalGrime", "pos": [1.78, 1.38, LF - 0.06], "size": [0.3, 0.4],
         "normal": [0, 0, -1]},
        {"name": "damp stain under the AC grille", "material": "WL_DecalDamp", "pos": [-1.4, 2.1, LB], "size": [0.5, 0.7], "normal": [0, 0, 1]},
        {"name": "dust on the threshold", "material": "WG_DecalSandSpill", "pos": [1.375, FY, 1.0], "size": [1.0, 0.4], "normal": [0, 1, 0]},
    ]


# ====================================================================== entry point (called at the end of wall_home)
def build(s):
    lod = s.lod
    n = s.name
    s.ilin = Part(f"{n}_InteriorLining_LOD{lod}", wear=False)
    s.ifloor = Part(f"{n}_InteriorFloor_LOD{lod}", wear=False)
    s.imetal = Part(f"{n}_InteriorMetal_LOD{lod}", wear=False)
    s.icloth = Part(f"{n}_InteriorCloth_LOD{lod}", wear=False)
    s.iprops = Part(f"{n}_InteriorProps_LOD{lod}", wear=False)
    s.ihard = Part(f"{n}_InteriorHardware_LOD{lod}", wear=False)
    s.iglow = Part(f"{n}_InteriorGlow_LOD{lod}", wear=False)
    s.ileaf = Part(f"{n}_DoorLeaf_LOD{lod}", wear=False)
    s.istencils = []
    # the lower step (uses the layout RNG, so it comes after every exterior piece)
    s.block((1.38, 0.075, 2.12), (1.3, 0.15, 0.4), (0.0, 0.0, 0.0), mat="VH_Ashlar")
    door_leaf(s, s.ileaf)
    lining(s)
    ceiling(s)
    floor(s)
    bunk(s)
    locker(s)
    rack(s)
    table(s)
    services(s)
    life(s)
    record(s)
    parts = [s.ilin, s.ifloor, s.imetal, s.icloth, s.iprops, s.ihard, s.iglow]
    orig = s.finish

    def finish():
        objs = orig()
        new = []
        for p_ in parts:
            if len(p_.bm.faces):
                ob = p_.build(s.coll)
                exact_uvs(ob)
                grain_uvs(ob)
                new.append(ob)
        leaf_ob = s.ileaf.build(s.coll)
        st, _ = lettering("S2", _AB.STENCIL_FONT, 0.22, ((LEAF["x0"] + LEAF["x1"]) / 2, 1.8, LEAF["z1"] + 0.0012), 0.002, 0.42,
                          "WB_StencilPaint", s.coll, f"{n}_DoorStencil_LOD{lod}", lod=1, facing=(0, 0, 1))
        _join(leaf_ob, st)
        h = U(HINGE)
        leaf_ob.data.transform(Matrix.Translation(-h))
        leaf_ob.location = h
        new.append(leaf_ob)
        objs = objs + new + s.istencils
        s.rec["triangles"] = tri_count(objs)
        s.rec["objects"] = {o.name: sum(len(pl.vertices) - 2 for pl in o.data.polygons) for o in objs}
        return objs
    s.finish = finish


def _join(target, other):
    import bpy
    for o in bpy.context.selected_objects:
        o.select_set(False)
    other.select_set(True)
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.join()


def grain_uvs(ob):
    """The timber maps (SS_Boards = TR_Timber, SS_Timber = TR_TimberDark) run their grain along V. Part.build's box
    projection puts U along the floor boards, table top, rails and slats, so the grain crossed every board and the floor
    read as small tiles in Unity (5 Oct captures). Turn each timber face's UVs so V runs along its longer side."""
    me = ob.data
    idx = {i for i, m in enumerate(me.materials) if m and m.name.split(".")[0] in ("SS_Boards", "SS_Timber")}
    if not idx:
        return
    uv = me.uv_layers["UVMap"]
    for poly in me.polygons:
        if poly.material_index not in idx:
            continue
        us = [uv.data[i].uv[0] for i in poly.loop_indices]
        vs = [uv.data[i].uv[1] for i in poly.loop_indices]
        if max(us) - min(us) > max(vs) - min(vs):
            for i in poly.loop_indices:
                u, v = uv.data[i].uv
                uv.data[i].uv = (v, -u)


def exact_uvs(ob):
    """Photo and calendar: map UVMap to the full 0..1 image over each face's extent (Part.build's box projection
    would tile it in metres)."""
    me = ob.data
    names = [m.name.split(".")[0] if m else "" for m in me.materials]
    if not any(nm in ("HP_Photo", "HP_Calendar") for nm in names):
        return
    uv = me.uv_layers["UVMap"]
    for nm in ("HP_Photo", "HP_Calendar"):
        if nm not in names:
            continue
        idx = [i for i, x in enumerate(names) if x == nm]
        polys = [p for p in me.polygons if p.material_index in idx]
        if not polys:
            continue
        # Blender coords: Unity (x, y, z) -> (-x, -z, y). Photo/calendar planes face Unity +/-Z or -Z: use Blender x (= -Unity x) and z (= Unity y)
        # group polygons into connected quads by proximity of their centres (each photo/calendar is a small island)
        islands = []
        for p in polys:
            c = p.center
            for isl in islands:
                if (isl[0] - c).length < 0.5:
                    isl[1].append(p)
                    break
            else:
                islands.append([c.copy(), [p]])
        for _, ps in islands:
            vs = [me.vertices[i].co for p in ps for i in p.vertices]
            n = ps[0].normal
            # in-plane axes: horizontal = up x n, vertical = Blender +Z projected
            up = Vector((0, 0, 1))
            hz = up.cross(n).normalized()
            vt = n.cross(hz).normalized()
            us = [v.dot(hz) for v in vs]
            ws = [v.dot(vt) for v in vs]
            u0, u1, w0, w1 = min(us), max(us), min(ws), max(ws)
            for p in ps:
                for li in p.loop_indices:
                    co = me.vertices[me.loops[li].vertex_index].co
                    uv.data[li].uv = ((co.dot(hz) - u0) / max(1e-6, u1 - u0), (co.dot(vt) - w0) / max(1e-6, w1 - w0))
