"""Ward hydroponics (1 Oct 2026): working-yard props, called by author_hydroponics.py (Blender 5.2).

Each prop is authored in Unity coordinates at the origin (front +Z, base on y = 0, footprint centred) as LOD Geos and
exported to Assets/AthenHill/Art/Hydroponics/Props/<id>/<id>_LOD<i>.glb, recorded in hy-manifest.json (size, LOD
triangles, collider boxes, NPC sit points, notes, shadow LODs).

  * authored: potting bench, compost bays, shade frame with drying herbs, IBC nutrient tote, nursery table, pallet, soil
    and herbs for the retrofit planters, a hose run on the ground;
  * produce fills: what sits inside the street kit's scanned yellow stacking crate (Prefabs/StreetDressing/SD_crate_yellow,
    inner 0.45 x 0.35 m, floor 8 mm) and flat wicker basket (SD_basket_flat) -- HydroponicsPass nests the scan and the
    fill in one prefab, so harvest crates use real crate geometry instead of coloured boxes;
  * Poly Haven scans (hose reel on a timber post, trowel, spade, boots, work hat, nutrient jugs, storage trolley, step
    ladder) merged, normalised and decimated the same way as the street-dressing kit.
"""
import math, random, json
from pathlib import Path
import numpy as np
import bpy
from mathutils import Vector, Matrix
from hykit import Geo, box, quad, tube, cylinder, icosphere, leaf, cross_card, lettuce, chard, basil, seedling_patch, cell_uv, norm, rot_y, ATLAS

A = None     # the author module (materials, to_blender, export_glb, MANIFEST)
nrng = np.random.default_rng(1001)

# street kit containers the fills sit in (measured from the Poly Haven scans: art/street_dressing_20260930/polyhaven)
CRATE = dict(floor=.012, hx=.218, hz=.168, rim=.254)        # plastic_crate_02 (SD_crate_yellow)
BASKET = dict(floor=.01, hx=.16, hz=.12, rim=.117)          # wicker_basket_01 (SD_basket_flat)


def pot(g, c, r=.06, h=.1, filled=True):
    """Black nursery pot (tapered, open) with soil."""
    c = np.asarray(c, float)
    tube(g, [c, c + [0, h, 0]], r * .78, "HY_BlackPlastic", sides=8, r_end=r)
    if filled:
        quad(g, [c + [-r * .9, h - .012, -r * .9], c + [-r * .9, h - .012, r * .9], c + [r * .9, h - .012, r * .9], c + [r * .9, h - .012, -r * .9]], "HY_Soil",
             uv=[(0, 0), (0, .12), (.12, .12), (.12, 0)], normals=[(0, 1, 0)] * 4)


def mound(g, c, sx, sz, h, matname, res=14, rng=None, uvm=1.0, lumps=6):
    """A heap (soil, compost) as a displaced grid with a few lumps; smooth normals from the height field."""
    rng = rng or np.random.default_rng(5)
    c = np.asarray(c, float)
    bumps = [(rng.uniform(-.7, .7), rng.uniform(-.7, .7), rng.uniform(.18, .4), rng.uniform(-.12, .18)) for _ in range(lumps)]

    def height(u, v):
        d = min(1, math.sqrt(u * u + v * v))
        y = math.cos(d * math.pi / 2) ** 1.1
        for bu, bv, br, ba in bumps:
            y += ba * math.exp(-((u - bu) ** 2 + (v - bv) ** 2) / (br * br)) * (1 - d ** 4)
        return max(0.0, y) * h

    V, UV, F, N = [], [], [], []
    e = 1.0 / res
    for j in range(res + 1):
        for i in range(res + 1):
            u, v = i / res * 2 - 1, j / res * 2 - 1
            y = height(u, v)
            p = c + [u * sx / 2, y, v * sz / 2]
            V.append(p); UV.append(((u + 1) * sx / 2 / uvm, (v + 1) * sz / 2 / uvm))
            dx = (height(u + e, v) - height(u - e, v)) / (2 * e * sx / 2)
            dz = (height(u, v + e) - height(u, v - e)) / (2 * e * sz / 2)
            N.append(norm([-dx, 1, -dz]))
    for j in range(res):
        for i in range(res):
            a = j * (res + 1) + i; b = a + res + 1
            F.append((a, b, b + 1, a + 1))
    g.add(V, F, UV, matname, N)
    return height


def plank(g, c, s, yaw=0.0):
    box(g, c, s, "HY_Wood", uvm=1.4, yaw=yaw)


def seed_tray_prop(g, cx, cz, y, lod, micro=False):
    L, W, H = .54, .28, .05
    box(g, (cx, y + H / 2, cz), (L, H, W), "HY_BlackPlastic", top=False)
    u0, v0, u1, v1 = cell_uv("microgreens" if micro else "rockwool")
    top = y + H - .008
    quad(g, [(cx - L / 2, top, cz + W / 2), (cx + L / 2, top, cz + W / 2), (cx + L / 2, top, cz - W / 2), (cx - L / 2, top, cz - W / 2)],
         "HY_Crop", uv=[(u0, v0), (u1, v0), (u1, v1), (u0, v1)], normals=[(0, 1, 0)] * 4)
    if lod == 0 and not micro:
        seedling_patch(g, "HY_Crop", cx - L / 2 + .01, cx + L / 2 - .01, cz - W / 2 + .01, cz + W / 2 - .01, top, .054, nrng)
    if micro and lod == 0:
        h2 = top + .025
        quad(g, [(cx - L / 2 + .01, h2, cz + W / 2 - .01), (cx + L / 2 - .01, h2, cz + W / 2 - .01), (cx + L / 2 - .01, h2, cz - W / 2 + .01),
                 (cx - L / 2 + .01, h2, cz - W / 2 + .01)], "HY_Crop", uv=[(u0, v1), (u1, v1), (u1, v0), (u0, v0)], normals=[(0, 1, 0)] * 4)


def fruit(g, c, r, ripe, lod, rng):
    """A tomato: slightly flattened sphere, atlas colour by ripeness (0 red .. 3 green)."""
    icosphere(g, c, r, "HY_Crop", cell_uv(f"fruit_{ripe}"), sub=1 if lod == 0 else (0 if lod == 1 else -1), squash=rng.uniform(.8, .9))


def bunch(g, tie, lod, rng, cell=None, yaw=0.0, lying=False, length=.26):
    """A tied bunch of herbs. Hanging: stems fan downwards from the tie in a narrow cone, leaves drooping along them.
    Lying (in a basket or crate): the same bunch laid along `yaw`, leaves resting outwards."""
    tie = np.asarray(tie, float)
    cell = cell or ("mint_leaf" if rng.random() < .5 else "basil_leaf")
    stems = (9 if lod == 0 else 5) if not lying else (7 if lod == 0 else 4)
    axis = np.array([0, -1., 0]) if not lying else rot_y(yaw) @ np.array([0, 0, 1.])
    side = np.cross(axis, [0, 0, 1.] if not lying else [0, 1., 0]); side = norm(side if np.linalg.norm(side) > 1e-6 else [1, 0, 0])
    up = np.cross(side, axis)
    for s in range(stems):
        a = s * 2.4 + rng.uniform(-.3, .3)
        spread = (side * math.cos(a) + up * math.sin(a)) * (rng.uniform(.18, .32) if not lying else rng.uniform(.06, .14))
        d = norm(axis + spread)
        L = length * rng.uniform(.8, 1.08)
        end = tie + d * L
        if lying:
            end[1] = max(end[1], tie[1] - .01)
        if lod == 0:
            tube(g, [tie, end], .0022, "HY_Crop", sides=3, uv_rect=cell_uv("stem"), uv_len=0)
        nl = 4 if lod == 0 else 2
        for k in range(nl):
            t = .3 + .7 * k / max(1, nl - 1)
            p = tie + (end - tie) * t
            az = math.atan2(d[0] + spread[0] * 2, d[2] + spread[2] * 2) + (k % 2 - .5) * 1.4
            el = math.radians(-60 + rng.uniform(-15, 15)) if not lying else math.radians(rng.uniform(-5, 15))
            leaf(g, "HY_Crop", p, az, el, rng.uniform(.05, .075) * (1.1 - .25 * t) * (1 if not lying else .8), cell, droop=-.15 if not lying else .1, cup=.18,
                 nu=1, nv=1 if lod else 2, centre=p - axis * .05, dome=.3)
    # twine wrap at the tie
    tube(g, [tie - axis * .005, tie + axis * .03], .011, "HY_Twine", sides=6)


# ------------------------------------------------------------------ authored props
def potting_bench(lod):
    g = Geo()
    W, D, Ht = 1.6, .62, .88
    for x in (-W / 2 + .05, W / 2 - .05):
        for z in (-D / 2 + .05, D / 2 - .05):
            h = Ht + (.35 if z < 0 else 0)
            plank(g, (x, h / 2, z), (.07, h, .07))
    for i in range(6):
        plank(g, (0, Ht - .017, -D / 2 + .052 + i * .103), (W, .034, .096))
    plank(g, (0, Ht + .19, -D / 2 + .01), (W - .1, .3, .02))
    for x in (-W / 2 + .03, W / 2 - .03):
        plank(g, (x, Ht + .07, 0), (.02, .14, D - .1))
    for i in range(3):
        plank(g, (0, .25, -D / 2 + .1 + i * .21), (W - .12, .025, .19))
    plank(g, (0, .12, -D / 2 + .05), (W - .12, .08, .025)); plank(g, (0, .12, D / 2 - .05), (W - .12, .08, .025))
    # potting mix heap at the left end, a seed tray being filled, pots with young plants, a tool rail on the back board
    mound(g, (-.5, Ht, -.02), .5, .42, .1, "HY_Soil", res=10 if lod == 0 else 4, uvm=.5, lumps=4)
    seed_tray_prop(g, .12, -.12, Ht, lod)
    for i, (x, z) in enumerate([(.5, .1), (.64, .1), (.5, -.06), (.64, -.08), (.33, .17)]):
        pot(g, (x, Ht, z))
        if i < 4 and lod < 2:
            lettuce(g, "HY_Crop", ["butter", "lollo", "cos", "butter"][i], .11, nrng, lod=max(1, lod), at=(x, Ht + .09, z), yaw=i)
    for j in range(4):
        pot(g, (-.2 + .03 * j, Ht + j * .03, .18), filled=False)
    if lod == 0:
        for k, x in enumerate((-.55, -.4)):
            for j in range(5):
                pot(g, (x, .265 + j * .025, -.05), filled=False)
        for k in range(3):   # empty seed trays stacked on the shelf
            box(g, (.42, .275 + k * .024, .02), (.54, .022, .28), "HY_BlackPlastic", yaw=.05 * (k - 1))
        # tool rail with three hanging hand forks
        box(g, (.2, Ht + .28, -D / 2 + .035), (.9, .03, .02), "HY_Wood")
        for x in (-.1, .1, .35):
            tube(g, [(x, Ht + .28, -D / 2 + .05), (x, Ht + .1, -D / 2 + .055)], .007, "HY_Wood", sides=5)
            for k in range(3):
                tube(g, [(x - .02 + k * .02, Ht + .1, -D / 2 + .055), (x - .02 + k * .02, Ht + .04, -D / 2 + .065)], .0025, "HY_Steel", sides=3)
    return g


def compost_bays(lod):
    g = Geo()
    Wb, D, H = 1.1, 1.0, .92
    n = 3; W = n * Wb
    rng = np.random.default_rng(7)
    xs = [-W / 2 + i * Wb for i in range(n + 1)]
    for x in xs:   # dividers: posts and slatted boards
        for z in (-D / 2, D / 2):
            plank(g, (x, H / 2 + .03, z), (.08, H + .06, .08))
        for k in range(5 if lod == 0 else 3):
            plank(g, (x, .1 + k * (.18 if lod == 0 else .3), 0), (.03, .13, D - .08))
    for k in range(5 if lod == 0 else 3):   # back wall
        plank(g, (0, .1 + k * (.18 if lod == 0 else .3), -D / 2), (W, .13, .03))
    fronts = [3, 0, 1]
    for b in range(n):
        cx = xs[b] + Wb / 2
        for k in range(fronts[b]):
            plank(g, (cx, .08 + k * .15, D / 2 + .02), (Wb - .09, .13, .03))
    # contents: fresh trimmings, mature compost, a half-turned mix
    res = 14 if lod == 0 else 6
    h0 = mound(g, (xs[0] + Wb / 2, 0, -.02), Wb - .1, D - .12, .6, "HY_Compost", res=res, rng=rng)
    mound(g, (xs[1] + Wb / 2, 0, .02), Wb - .12, D - .1, .5, "HY_Soil", res=res, rng=rng, uvm=.6)
    mound(g, (xs[2] + Wb / 2, 0, -.1), Wb - .1, D - .3, .35, "HY_Compost", res=res, rng=rng)
    if lod < 2:   # trimmings on the fresh heap: outer lettuce leaves, chard, spent tomato leaves
        for i in range(34 if lod == 0 else 12):
            u, v = rng.uniform(-.85, .85), rng.uniform(-.85, .85)
            p = (xs[0] + Wb / 2 + u * (Wb - .1) / 2, h0(u, v) + .004, v * (D - .12) / 2 - .02)
            cell = ["cos_a", "chard_red", "tomato_leaf_a", "butter_b", "oak_red", "butter_a"][i % 6]
            leaf(g, "HY_Crop", p, rng.uniform(0, 6.28), math.radians(rng.uniform(-6, 10)), rng.uniform(.12, .22), cell, droop=.12, cup=.05,
                 nu=1, nv=1 if lod else 2, centre=np.asarray(p) + [0, -.2, 0])
    if lod == 0:   # garden fork leaning on the middle divider
        b0 = np.array([xs[2] - .05, 0, D / 2 + .08]); t0 = b0 + [.06, 1.05, -.22]
        tube(g, [b0 + [0, .3, 0], t0], .014, "HY_Wood", sides=6)
        tube(g, [t0, t0 + [.07, .05, 0], t0 + [-.07, .05, 0], t0], .01, "HY_Steel", sides=4)
        for k in range(4):
            tube(g, [b0 + [-.045 + k * .03, .3, 0], b0 + [-.045 + k * .03, .02, .02]], .005, "HY_Steel", sides=3)
        tube(g, [b0 + [-.05, .3, 0], b0 + [.05, .3, 0]], .008, "HY_Steel", sides=4)
    return g


SHADE = dict(W=3.6, D=3.0, H=2.4)


def shade_frame(lod):
    """Galvanised frame with knitted shade cloth over the nursery tables; herbs drying on a line under the back edge."""
    g = Geo()
    W, D, H = SHADE["W"], SHADE["D"], SHADE["H"]
    rng = np.random.default_rng(31)
    corners = [(-W / 2, -D / 2), (W / 2, -D / 2), (W / 2, D / 2), (-W / 2, D / 2)]
    for x, z in corners:
        tube(g, [(x, 0, z), (x, H, z)], .03, "HY_Galv", sides=8 if lod == 0 else 5)
        box(g, (x, .01, z), (.16, .02, .16), "HY_Galv")
        if lod == 0:   # knee braces
            for dx, dz in ((-np.sign(x) * .45, 0), (0, -np.sign(z) * .45)):
                tube(g, [(x, H - .5, z), (x + dx, H - .03, z + dz)], .015, "HY_Galv", sides=5)
    for i in range(4):
        (x0, z0), (x1, z1) = corners[i], corners[(i + 1) % 4]
        tube(g, [(x0, H - .03, z0), (x1, H - .03, z1)], .022, "HY_Galv", sides=6 if lod == 0 else 4)
    tube(g, [(0, H - .03, -D / 2), (0, H - .03, D / 2)], .02, "HY_Galv", sides=5)
    # cloth: a gently sagging knitted sheet tied over the rails, a valance on the sunny (front) edge
    nu, nv = (14, 12) if lod == 0 else (5, 4)
    V, UV, F, N = [], [], [], []
    for j in range(nv + 1):
        for i in range(nu + 1):
            u, v = i / nu, j / nv
            x = -W / 2 - .04 + u * (W + .08); z = -D / 2 - .04 + v * (D + .08)
            sag = .1 * math.sin(u * math.pi) * math.sin(v * math.pi) * (1 - .7 * math.exp(-(x / .1) ** 2))
            V.append((x, H + .02 - sag, z)); UV.append((u * (W + .08) / .5, v * (D + .08) / .5)); N.append((0, 1, 0))
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i; b = a + nu + 1
            F.append((a, b, b + 1, a + 1))
    g.add(V, F, UV, "HY_ShadeCloth", N)
    V, UV, F, N = [], [], [], []
    for j in range(3):
        for i in range(nu + 1):
            u = i / nu; x = -W / 2 - .04 + u * (W + .08)
            y = H + .02 - j * .16 - (.025 * math.sin(u * math.pi * 7) if j else 0)
            V.append((x, y, D / 2 + .05 + j * .004)); UV.append((u * (W + .08) / .5, j * .16 / .5)); N.append((0, 0, 1))
    for j in range(2):
        for i in range(nu):
            a = j * (nu + 1) + i; b = a + nu + 1
            F.append((a, a + 1, b + 1, b))
    g.add(V, F, UV, "HY_ShadeCloth", N)
    # drying herbs: a line under the back rail with tied bunches
    ly = H - .3; lz = -D / 2 + .25
    tube(g, [(-W / 2, H - .05, lz), (-W / 2 + .35, ly, lz), (W / 2 - .35, ly, lz), (W / 2, H - .05, lz)], .004, "HY_Twine", sides=3)
    nb = 11 if lod == 0 else 6
    for k in range(nb):
        x = -W / 2 + .5 + k * ((W - 1.0) / (nb - 1))
        bunch(g, (x + rng.uniform(-.04, .04), ly - .01, lz), lod, rng, cell=["basil_leaf", "mint_leaf", "oak_green"][k % 3], length=rng.uniform(.22, .3))
    return g


def ibc_tote(lod, hose=True):
    g = Geo()
    L, Wd, H = 1.2, 1.0, 1.16
    box(g, (0, .07, 0), (L, .14, Wd), "HY_BlackPlastic")
    for z in (-Wd / 2 + .03, Wd / 2 - .03):
        box(g, (0, .145, z), (L, .03, .05), "HY_Galv")
    box(g, (0, .15 + .47, 0), (L - .06, .94, Wd - .06), "HY_IBC", uvm=1.2)
    cylinder(g, (0, 1.1, -.1), .15, .04, "HY_IBC", sides=12)
    cylinder(g, (.3, 1.1, .2), .03, .05, "HY_BlackPlastic", sides=6)
    sides = 5 if lod == 0 else 3
    r = .009
    nx, nz = (6, 5) if lod == 0 else (3, 3)
    for i in range(nx + 1):
        x = -L / 2 + i * L / nx
        for z in (-Wd / 2, Wd / 2):
            tube(g, [(x, .15, z), (x, H, z)], r, "HY_Galv", sides=sides)
        tube(g, [(x, H, -Wd / 2), (x, H, Wd / 2)], r, "HY_Galv", sides=sides)
    for i in range(nz + 1):
        z = -Wd / 2 + i * Wd / nz
        for x in (-L / 2, L / 2):
            tube(g, [(x, .15, z), (x, H, z)], r, "HY_Galv", sides=sides)
    for y in ([.16, .5, .83, H] if lod == 0 else [.16, H]):
        tube(g, [(-L / 2, y, -Wd / 2), (L / 2, y, -Wd / 2), (L / 2, y, Wd / 2), (-L / 2, y, Wd / 2), (-L / 2, y, -Wd / 2)], r * 1.3, "HY_Galv", sides=sides)
    cylinder(g, (0, .24, Wd / 2 + .04), .05, .09, "HY_BlackPlastic", sides=8, axis="z")
    box(g, (0, .31, Wd / 2 + .06), (.16, .03, .03), "HY_Steel")
    if hose:
        tube(g, [(0, .24, Wd / 2 + .08), (0, .22, Wd / 2 + .22), (.05, .03, Wd / 2 + .4), (.25, .025, Wd / 2 + .9), (.2, .025, Wd / 2 + 1.4)],
             .02, "HY_Hose", sides=6 if lod == 0 else 4)
    if lod == 0:   # level line: the concentrate shows through the bottle as a darker band
        box(g, (0, .15 + .3, Wd / 2 - .028), (L - .08, .6, .002), "HY_Water")
    return g


def nursery_table(lod):
    g = Geo()
    L, D, H = 2.4, .8, .78
    for x in (-L / 2 + .12, L / 2 - .12):
        for z in (-1, 1):
            tube(g, [(x, 0, z * .36), (x, H - .03, z * .2)], .018, "HY_Galv", sides=6 if lod == 0 else 4)
        tube(g, [(x, H - .03, -.36), (x, H - .03, .36)], .02, "HY_Galv", sides=5)
        tube(g, [(x, .3, -.3), (x, .3, .3)], .012, "HY_Galv", sides=4)
    for i in range(7):
        plank(g, (0, H + .01, -D / 2 + .06 + i * .113), (L, .025, .1))
    for i, (x, z, micro) in enumerate([(-.87, -.18, False), (-.87, .15, False), (-.3, -.18, False), (-.3, .15, True), (.27, -.18, False)]):
        seed_tray_prop(g, x, z, H + .022, lod, micro=micro)
    for i in range(8):
        x = .63 + (i % 4) * .15; z = -.2 + (i // 4) * .2
        pot(g, (x, H + .022, z), r=.055, h=.09)
        if lod < 2:
            kind = ["butter", "lollo", "cos", "rocket"][i % 4]
            lettuce(g, "HY_Crop", kind, .13, nrng, lod=max(1, lod), at=(x, H + .1, z), yaw=i)
    pot(g, (.3, H + .022, .2), r=.05, h=.08)
    if lod < 2:
        basil(g, "HY_Crop", .16, nrng, lod=max(1, lod), at=(.3, H + .09, .2))
    if lod == 0:   # spare trays stacked on the ground under the table
        for k in range(4):
            box(g, (-.6, .011 + k * .022, .05), (.54, .022, .28), "HY_BlackPlastic", yaw=.04 * k)
    return g


def pallet(lod):
    g = Geo()
    for x in (-.55, 0, .55):
        plank(g, (x, .05, 0), (.1, .1, .8))
    for i in range(7 if lod == 0 else 4):
        plank(g, (0, .122, -.35 + i * (.7 / (6 if lod == 0 else 3))), (1.2, .022, .1))
    for z in (-.35, 0, .35):
        plank(g, (0, .011, z), (1.2, .022, .1))
    return g


def gap_planter_herbs(lod):
    """Soil and herbs for the retrofit's three planter boxes between the bays (inner 0.94 x 0.25 m, soil at 0.385 m)."""
    g = Geo()
    y = .385
    quad(g, [(-.47, y, -.125), (-.47, y, .125), (.47, y, .125), (.47, y, -.125)], "HY_Soil", uv=[(0, 0), (0, .25), (.94, .25), (.94, 0)],
         normals=[(0, 1, 0)] * 4)
    rng = np.random.default_rng(3)
    plan = ["basil", "chard", "mint", "basil", "chard_y", "mint", "basil", "chard"]
    for i, k in enumerate(plan):
        x = -.41 + i * (.82 / (len(plan) - 1)); z = rng.uniform(-.05, .05)
        l = lod if lod < 2 else 1
        if k == "basil": basil(g, "HY_Crop", .26, nrng, lod=l, at=(x, y, z), yaw=i)
        elif k == "mint": basil(g, "HY_Crop", .22, nrng, lod=l, at=(x, y, z), yaw=i, cell="mint_leaf")
        else: chard(g, "HY_Crop", .38, nrng, lod=l, at=(x, y, z), yaw=i, yellow=k == "chard_y")
    return g


def hose_ground(lod):
    g = Geo()
    pts = []
    for i in range(3 * 14 + 1):
        a = i / 14 * 2 * math.pi
        r = .32 - i * .002
        pts.append((r * math.cos(a), .018 + i * .0006, r * math.sin(a)))
    pts += [(.2, .02, .3), (.1, .02, .7), (-.1, .02, 1.0)]
    tube(g, pts, .016, "HY_Hose", sides=6 if lod == 0 else 4)
    return g


# ------------------------------------------------------------------ produce fills (local frame of the street kit container)
def lie(g, at, cell, length, yaw, lod, rng, stalk=False):
    """A harvested head or bunch lying on its side: a few long leaves laid along yaw from a stem end."""
    at = np.asarray(at, float)
    base = at - rot_y(yaw) @ np.array([0, 0, length / 2])
    n = 6 if lod == 0 else 3
    u0, v0, u1, v1 = cell_uv(cell)
    rib = (u0 + .49 * (u1 - u0), v0 + .05 * (v1 - v0), u0 + .51 * (u1 - u0), v0 + .3 * (v1 - v0))
    for k in range(n):
        az = yaw + rng.uniform(-.35, .35)
        p = base + np.array([rng.uniform(-.02, .02), k * .006, rng.uniform(-.02, .02)])
        if stalk:
            d = rot_y(az) @ np.array([0, 0, 1.])
            if lod == 0:
                tube(g, [p, p + d * length * .3 + [0, .01, 0]], .007, "HY_Crop", sides=3, uv_rect=rib, uv_len=0)
            p = p + d * length * .28
        leaf(g, "HY_Crop", p, az, math.radians(rng.uniform(4, 16)), length * rng.uniform(.75, 1.0), cell, droop=.15, cup=.25,
             nu=2 if lod == 0 else 1, nv=2 if lod == 0 else 1, centre=p + [0, -.1, 0], dome=.4)


def fill(kind, holder):
    H = CRATE if holder == "crate" else BASKET

    def f(lod):
        g = Geo()
        rng = np.random.default_rng(sum(map(ord, kind + holder)))
        fy, hx, hz = H["floor"], H["hx"], H["hz"]
        if kind == "lettuce":
            heads = [(-.1, -.075), (.1, -.075), (-.1, .078), (.1, .078)]
            for i, (dx, dz) in enumerate(heads):
                lettuce(g, "HY_Crop", "butter" if i % 2 == 0 else "lollo", .19, nrng, lod=lod, at=(dx, fy + .1, dz), yaw=i * 1.7)
            if lod < 2:
                lettuce(g, "HY_Crop", "butter", .17, nrng, lod=max(1, lod), at=(0, fy + .15, 0), yaw=.4)
        elif kind == "cos":
            for i in range(6 if lod < 2 else 3):
                dz = -.12 + (i % 3) * .12
                y = fy + .05 + (i // 3) * .06
                lie(g, (0, y, dz * .9), "cos_a" if i % 2 else "cos_b", .3, math.pi / 2 if i % 2 else -math.pi / 2, lod, rng)
        elif kind == "tomato":
            layers = ([1, 2] if holder == "crate" else [0, 1]) if lod == 0 else ([2] if holder == "crate" else [1]) if lod == 1 else []
            r0 = .03
            top_layer = 2 if holder == "crate" else 1
            for layer in layers:
                y = fy + r0 * .85 + layer * r0 * 1.55 + (.06 if holder == "crate" else 0)
                nx, nz = int(2 * hx / (2 * r0)), int(2 * hz / (2 * r0))
                for i in range(nx):
                    for j in range(nz):
                        x = -hx + r0 + i * (2 * hx - 2 * r0) / max(1, nx - 1) + (layer % 2) * r0 * .5
                        z = -hz + r0 + j * (2 * hz - 2 * r0) / max(1, nz - 1) + (layer % 2) * r0 * .5
                        if abs(x) > hx - r0 * .6 or abs(z) > hz - r0 * .6: continue
                        if layer == top_layer and rng.random() < .12: continue
                        fruit(g, (x + rng.uniform(-.005, .005), y + rng.uniform(-.004, .006), z + rng.uniform(-.005, .005)),
                              rng.uniform(.026, .032), 0 if rng.random() < .8 else 1, lod, rng)
            if lod >= 1 or holder == "crate":   # the hidden lower layers as a red bed under the visible top
                u0, v0, u1, v1 = cell_uv("fruit_0")
                yb = fy + r0 * .85 + (top_layer - (1 if lod == 1 else 0)) * r0 * 1.55 + (.06 if holder == "crate" else 0)
                if lod == 0: yb = fy + r0 * .85 + r0 * 1.55 + .06 - r0 * .6
                quad(g, [(-hx, yb, hz), (hx, yb, hz), (hx, yb, -hz), (-hx, yb, -hz)], "HY_Crop",
                     uv=[(u0 + .2 * (u1 - u0), v0 + .2 * (v1 - v0)), (u1 - .2 * (u1 - u0), v0 + .2 * (v1 - v0)), (u1 - .2 * (u1 - u0), v1 - .2 * (v1 - v0)),
                         (u0 + .2 * (u1 - u0), v1 - .2 * (v1 - v0))], normals=[(0, 1, 0)] * 4)
        elif kind == "beans":
            u0, v0, u1, v1 = cell_uv("pod")
            n = 170 if lod == 0 else 60 if lod == 1 else 20
            top = .2 if holder == "crate" else .09
            for i in range(n):
                t = (i / n) ** .6
                a = rng.uniform(0, math.pi); d = np.array([math.cos(a), rng.uniform(-.15, .15), math.sin(a)]) * .08
                p = np.array([rng.uniform(-hx + abs(d[0]) + .01, hx - abs(d[0]) - .01), fy + .01 + t * (top - fy),
                              rng.uniform(-hz + abs(d[2]) + .01, hz - abs(d[2]) - .01)])
                s = np.array([-math.sin(a), 0, math.cos(a)]) * .009
                quad(g, [p - d - s, p + d - s, p + d + s, p - d + s], "HY_Crop",
                     uv=[(u0 + (u1 - u0) * .35, v0), (u0 + (u1 - u0) * .35, v1), (u0 + (u1 - u0) * .65, v1), (u0 + (u1 - u0) * .65, v0)],
                     normals=[norm([rng.uniform(-.3, .3), 1, rng.uniform(-.3, .3)])] * 4)
        elif kind == "chard":
            for i in range(5 if lod < 2 else 3):
                dz = -.12 + i * .06
                lie(g, (0, fy + .06 + (i % 2) * .03, dz), "chard_red" if i % 2 else "chard_yellow", .27, math.pi / 2 if i % 2 else -math.pi / 2, lod, rng, stalk=True)
        elif kind == "herbs":
            for i in range(4 if lod < 2 else 2):
                p = (-hx + .04, fy + .02 + (i % 2) * .015, -hz + .05 + i * (2 * hz - .1) / 3)
                bunch(g, p, lod, rng, cell=["basil_leaf", "mint_leaf"][i % 2], yaw=math.pi / 2 + rng.uniform(-.1, .1), lying=True, length=.24)
        return g
    return f


def pot_fill(kind):
    """Soil and one herb plant for the street kit's terracotta pot (SD_pot_clay: rim 0.27 m, soil at 0.195 m)."""
    def f(lod):
        g = Geo()
        y, r = .195, .104
        pts = [(r * math.cos(a), y, r * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 13)[:-1]]
        g.add(pts, [tuple(range(12))[::-1]], [(.5 + .5 * math.cos(a) * .2, .5 + .5 * math.sin(a) * .2) for a in np.linspace(0, 2 * math.pi, 13)[:-1]],
              "HY_Soil", [(0, 1, 0)] * 12)
        l = min(lod, 1)
        if kind == "basil": basil(g, "HY_Crop", .32, nrng, lod=l, at=(0, y, 0), yaw=.3)
        elif kind == "mint": basil(g, "HY_Crop", .27, nrng, lod=l, at=(0, y, 0), yaw=1.1, cell="mint_leaf")
        else: chard(g, "HY_Crop", .4, nrng, lod=l, at=(0, y, 0), yaw=.7, yellow=False)
        return g
    return f


AUTHORED = {
    #  id: (builder, collider, notes, sit points [(x, y, z)])
    "potting_bench": (potting_bench, True, "potting bench: potting-mix heap, seed tray, potted young lettuces, stacked pots, hand forks", []),
    "compost_bays": (compost_bays, True, "three slatted compost bays: fresh trimmings, mature compost, half-turned mix; a fork", []),
    "shade_frame": (shade_frame, False, "galvanised shade frame 3.6 x 3.0 m, knitted shade cloth, drying herb bunches", []),
    "ibc_tote": (ibc_tote, True, "IBC nutrient tote in its cage with a hose to the ground", []),
    "nursery_table": (nursery_table, True, "trestle table of seedling trays and potted plants hardening off", []),
    "pallet": (pallet, False, "wooden pallet", []),
    "gap_planter_herbs": (gap_planter_herbs, False, "soil and herbs for the retrofit planters between the bays", []),
    "hose_ground": (hose_ground, False, "garden hose coiled on the ground with a loose run", []),
    "fill_crate_lettuce": (fill("lettuce", "crate"), False, "butterhead and red lollo heads in a stacking crate", []),
    "fill_crate_cos": (fill("cos", "crate"), False, "cos lettuces laid in a stacking crate", []),
    "fill_crate_tomato": (fill("tomato", "crate"), False, "ripe tomatoes in a stacking crate", []),
    "fill_crate_beans": (fill("beans", "crate"), False, "runner beans in a stacking crate", []),
    "fill_crate_chard": (fill("chard", "crate"), False, "rainbow chard bunches in a stacking crate", []),
    "fill_basket_tomato": (fill("tomato", "basket"), False, "tomatoes in a flat wicker basket", []),
    "fill_basket_herbs": (fill("herbs", "basket"), False, "tied basil and mint bunches in a flat wicker basket", []),
    "fill_basket_beans": (fill("beans", "basket"), False, "runner beans in a flat wicker basket", []),
    "fill_pot_basil": (pot_fill("basil"), False, "basil in a terracotta pot", []),
    "fill_pot_mint": (pot_fill("mint"), False, "mint in a terracotta pot", []),
    "fill_pot_chard": (pot_fill("chard"), False, "chard in a terracotta pot", []),
}
SHADOWS_LOD = {"shade_frame": 1, "compost_bays": 1, "ibc_tote": 1, "potting_bench": 1, "nursery_table": 1}


def geo_size(g):
    V = np.asarray(g.v)
    mn, mx = V.min(0), V.max(0)
    return [round(float(mx[0] - mn[0]), 3), round(float(mx[1] - mn[1]), 3), round(float(mx[2] - mn[2]), 3)], mn, mx


def build_authored(pid):
    fn, col, notes, sits = AUTHORED[pid]
    lods = [fn(i) for i in range(3)]
    size, mn, mx = geo_size(lods[0])
    for i, g in enumerate(lods):
        o = A.to_blender(g, f"HY_{pid}_LOD{i}")
        A.export_glb([o], A.OUT_PROPS / pid / f"{pid}_LOD{i}.glb")
    cols = []
    if pid == "shade_frame":
        W, D = SHADE["W"], SHADE["D"]
        cols = [dict(center=[x, 1.2, z], size=[.12, 2.4, .12]) for x in (-W / 2, W / 2) for z in (-D / 2, D / 2)]
    elif pid == "ibc_tote":   # the hose on the ground is not solid
        cols = [dict(center=[0, .58, 0], size=[1.2, 1.16, 1.0])]
    elif col:
        c = (mn + mx) / 2
        cols = [dict(center=[round(float(c[0]), 3), round(float((mx[1]) / 2), 3), round(float(c[2]), 3)],
                     size=[round(float(mx[0] - mn[0]) * .95, 3), round(float(mx[1]), 3), round(float(mx[2] - mn[2]) * .95, 3)])]
    A.MANIFEST["props"][pid] = dict(kind="authored", notes=notes, size=size, lods=[len(g) for g in lods], colliders=cols, sitPoints=sits,
                                   footprint=[round(float(mn[0]), 3), round(float(mx[0]), 3), round(float(mn[2]), 3), round(float(mx[2]), 3)],
                                   shadowLods=(SHADOWS_LOD.get(pid, 0) + 1) if not pid.startswith("fill_") else 1,
                                   glb=[f"Props/{pid}/{pid}_LOD{i}.glb" for i in range(3)])
    print("prop", pid, size, [len(g) for g in lods], flush=True)


# ------------------------------------------------------------------ Poly Haven scans (merge, normalise, decimate)
PH_PROPS = {
    # id: (model, yaw about Blender Z to face Unity +Z, notes, lod ratios, object filter)
    "hose_reel": ("garden_hose_wall_mounted_01", 0, "wall hose reel with a green hose, bolted to a timber post", (.35, .12), None),
    "trowel": ("trowel_01", 0, "hand trowel", (.3, .1), None),
    "spade": ("rusted_spade_01", 0, "old spade", (.3, .1), None),
    "boots": ("rubber_boots", 0, "pair of muddy rubber boots", (.2, .06), "dirt"),
    "work_hat": ("fishermans_hat", 0, "wide-brimmed work hat", (.3, .1), None),
    "nutrient_jug": ("plastic_bottle_gallon", 0, "4 l jug of nutrient concentrate", (.25, .08), None),
    "dosing_trolley": ("industrial_storage_cart", 0, "steel trolley for the nutrient dosing kit", (.3, .1), None),
    "step_ladder": ("wooden_ladder", 0, "wooden step ladder", (.3, .1), None),
}


def tris(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


def import_merged(model, filt=None):
    before = set(bpy.data.objects)
    g = next((A.PH / "models" / model).glob("*.gltf"))
    bpy.ops.import_scene.gltf(filepath=str(g))
    new = [o for o in bpy.data.objects if o not in before]
    new_names = [o.name for o in new]
    meshes = [o for o in new if o.type == "MESH"]
    if filt:
        sel = [o for o in meshes if filt in o.name.lower()]
        meshes = sel or meshes
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
        if o.data.users > 1: o.data = o.data.copy()
        if o.parent:
            mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if len(meshes) > 1: bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    for n in new_names:
        o = bpy.data.objects.get(n)
        if o is not None and o != ob: bpy.data.objects.remove(o, do_unlink=True)
    return ob


def normalise(ob, yaw=0):
    if yaw: ob.data.transform(Matrix.Rotation(math.radians(yaw), 4, "Z"))
    vs = [v.co for v in ob.data.vertices]
    mn = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs))); mx = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
    ob.data.transform(Matrix.Translation((-(mn.x + mx.x) / 2, -(mn.y + mx.y) / 2, -mn.z)))
    ob.data.update()
    return [round(mx.x - mn.x, 4), round(mx.z - mn.z, 4), round(mx.y - mn.y, 4)]


def decimated(ob, ratio, name, min_tris=200):
    me = ob.data.copy(); c = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(c)
    bpy.ops.object.select_all(action="DESELECT"); c.select_set(True); bpy.context.view_layer.objects.active = c
    d = c.modifiers.new("d", "DECIMATE"); d.ratio = max(ratio, min(1, min_tris / max(1, tris(me)))); d.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier="d"); c.data.name = c.name
    return c


def add_post(ob):
    """Timber post behind a wall-mounted fitting (Blender +Y is Unity -Z, the back of a front-facing scan); the reel is
    lifted to working height and the post stands on the ground."""
    vs = [v.co for v in ob.data.vertices]
    back = max(v.y for v in vs)
    zc = (min(v.z for v in vs) + max(v.z for v in vs)) / 2
    ob.data.transform(Matrix.Translation((0, 0, .95 - zc)))
    post = Geo()
    box(post, (0, .65, -(back + .035)), (.075, 1.3, .075), "HY_Wood", uvm=1.2, top=True)
    po = A.to_blender(post, "post_tmp")
    bpy.ops.object.select_all(action="DESELECT"); ob.select_set(True); po.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.object.join()
    return ob


def build_ph(pid):
    model, yaw, notes, ratios, filt = PH_PROPS[pid]
    ob = import_merged(model, filt)
    ob.name = f"HY_{pid}_LOD0"; ob.data.name = ob.name
    normalise(ob, yaw)
    if pid == "hose_reel":
        add_post(ob); normalise(ob)
    vs = [v.co for v in ob.data.vertices]
    size = [round(max(v.x for v in vs) - min(v.x for v in vs), 4), round(max(v.z for v in vs) - min(v.z for v in vs), 4),
            round(max(v.y for v in vs) - min(v.y for v in vs), 4)]
    lods = [ob] + [decimated(ob, r, f"HY_{pid}_LOD{i + 1}") for i, r in enumerate(ratios)]
    for i, o in enumerate(lods):
        A.export_glb([o], A.OUT_PROPS / pid / f"{pid}_LOD{i}.glb")
    mats = sorted({m.name for m in ob.data.materials if m})
    cols = []
    if pid in ("dosing_trolley",):
        cols = [dict(center=[0, size[1] / 2, 0], size=[size[0] * .95, size[1], size[2] * .95])]
    A.MANIFEST["props"][pid] = dict(kind="polyhaven", model=model, notes=notes, size=size, lods=[tris(o.data) for o in lods], colliders=cols,
                                   sitPoints=[], materials=mats, shadowLods=1, glb=[f"Props/{pid}/{pid}_LOD{i}.glb" for i in range(3)])
    for o in lods: o.hide_render = True; o.hide_set(True)
    print("ph prop", pid, size, A.MANIFEST["props"][pid]["lods"], mats, flush=True)


def build_onion_fill():
    """Onions in a stacking crate: the Poly Haven onion scan decimated and scattered in two layers."""
    src = import_merged("yellow_onion")
    normalise(src)
    vs = [v.co for v in src.data.vertices]
    d = max(max(v.x for v in vs) - min(v.x for v in vs), max(v.y for v in vs) - min(v.y for v in vs))
    rng = random.Random(77)
    lods = []
    for lod, (ratio, layers) in enumerate([(.016, 2), (.007, 1), (.003, 1)]):
        dec = decimated(src, ratio, f"onion_dec{lod}", min_tris=24)
        parts = []
        for layer in range(layers):
            y = CRATE["floor"] + .07 + (layer if layers == 2 else 1) * d * .8
            nx, nz = 6, 5
            for i in range(nx):
                for j in range(nz):
                    x = -CRATE["hx"] + d / 2 + i * (2 * CRATE["hx"] - d) / (nx - 1) + rng.uniform(-.008, .008) + (layer % 2) * d * .3
                    z = -CRATE["hz"] + d / 2 + j * (2 * CRATE["hz"] - d) / (nz - 1) + rng.uniform(-.008, .008)
                    if abs(x) > CRATE["hx"] - d * .4: continue
                    c = bpy.data.objects.new("onion", dec.data.copy()); bpy.context.scene.collection.objects.link(c)
                    s = rng.uniform(.85, 1.1)
                    c.matrix_world = Matrix.Translation((-x, -z, y)) @ Matrix.Rotation(rng.uniform(0, 6.28), 4, "Z") @ \
                        Matrix.Rotation(rng.uniform(-.5, .5), 4, "X") @ Matrix.Scale(s, 4)
                    parts.append(c)
        bpy.ops.object.select_all(action="DESELECT")
        for p in parts: p.select_set(True)
        bpy.context.view_layer.objects.active = parts[0]
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        bpy.ops.object.join()
        ob = bpy.context.view_layer.objects.active; ob.name = f"HY_fill_crate_onion_LOD{lod}"
        lods.append(ob)
        bpy.data.objects.remove(dec, do_unlink=True)
    bpy.data.objects.remove(src, do_unlink=True)
    for i, o in enumerate(lods):
        A.export_glb([o], A.OUT_PROPS / "fill_crate_onion" / f"fill_crate_onion_LOD{i}.glb")
    A.MANIFEST["props"]["fill_crate_onion"] = dict(kind="polyhaven", model="yellow_onion", notes="onions in a stacking crate",
                                                   size=[.44, .2, .34], lods=[tris(o.data) for o in lods], colliders=[], sitPoints=[],
                                                   materials=sorted({m.name for m in lods[0].data.materials if m}), shadowLods=1,
                                                   glb=[f"Props/fill_crate_onion/fill_crate_onion_LOD{i}.glb" for i in range(3)])
    for o in lods: o.hide_render = True; o.hide_set(True)
    print("fill onion", A.MANIFEST["props"]["fill_crate_onion"]["lods"], flush=True)


def build_all(author, only=None):
    global A
    A = author
    for pid in AUTHORED:
        if not only or pid in only: build_authored(pid)
    for pid in PH_PROPS:
        if not only or pid in only: build_ph(pid)
    if not only or "fill_crate_onion" in only:
        build_onion_fill()
