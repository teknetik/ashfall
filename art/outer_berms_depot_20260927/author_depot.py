"""Outer Berms machine depot — authored structures (27 Sep 2026), Blender 5.2 headless.

Run:  blender -b --python-exit-code 1 -P author_depot.py [-- AssetName ...]

Reuses the West Gate kit (art/west_gate_20260926/author_west_gate.py): coordinates are Unity metres (X east, Y up,
Z north) converted by U(); UVs are box-projected in metres; materials are named WG_* (existing West Gate URP
materials) or DP_* (built by Editor/OuterBermsDepotPass from textures written by make_depot_textures.py).
COL_* objects are box-collider proxies; LIGHT_* / FX_* empties mark practical lights and effects.

Site-specific pieces (hall, conveyor, plinth, cables) are authored in world coordinates relative to an anchor
(the prefab origin) so they sit on the sculpted ground; depot-ground-grid.json (exported by the Unity pass after the
ground sculpt) supplies the ground heights. Reusable pieces (cradles, walls) use their own base-centre origin.
"""
import bpy, bmesh, json, math, random, sys
from pathlib import Path
from mathutils import Vector, Matrix, noise

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "west_gate_20260926"))
import author_west_gate as wg
from author_west_gate import U, box, cyl, tube, ibeam, join, empty, mesh_obj, box_uv, place_bm, reset, sag, decimate_copy

OUT = HERE.parents[1] / "unity/AthenHill/Assets/AthenHill/Art/OuterBermsDepot/Structures"
OUT.mkdir(parents=True, exist_ok=True)
wg.OUT = OUT
REPORT = wg.REPORT

# ---------------------------------------------------------------- ground (world) and anchors
_grid = json.loads((HERE / "depot-ground-grid.json").read_text())
_G = {(round(x * 2), round(z * 2)): y for x, y, z in _grid}


def gy(x, z):
    """Walkable ground height at world (x, z), bilinear on the 0.5 m grid."""
    fx, fz = x * 2, z * 2; ix, iz = math.floor(fx), math.floor(fz); tx, tz = fx - ix, fz - iz
    def h(i, j): return _G.get((i, j), _G.get((max(min(i, -120), -208), max(min(j, -28), -108)), 0.0))
    return (h(ix, iz) * (1 - tx) + h(ix + 1, iz) * tx) * (1 - tz) + (h(ix, iz + 1) * (1 - tx) + h(ix + 1, iz + 1) * tx) * tz


HALL = Vector((-79.75, 0.12, -48.0))       # hall floor centre (prefab origin)
CONV = Vector((-88.4, 0.0, -46.0))         # conveyor anchor (world x/z of the hall entry, y = 0)


def export(name, note=""):
    """Triangulate (so the glTF exporter can write tangents for the normal-mapped URP materials), then export."""
    for ob in list(bpy.context.scene.objects):
        if ob.type != "MESH" or ob.name.startswith("COL_"): continue
        for o in bpy.context.selected_objects: o.select_set(False)
        bpy.context.view_layer.objects.active = ob; ob.select_set(True)
        m = ob.modifiers.new("tri", "TRIANGULATE"); bpy.ops.object.modifier_apply(modifier="tri")
    wg.export(name, note)


def rnd_seed(s):
    random.seed(s)


# ---------------------------------------------------------------- sheet metal
def sheet_bm(L, Hh, keep=None, bend=None, pitch=.28, depth=.035, vres=.3):
    """Box-profile corrugated sheet: local X = length (0..L), Y = height (0..Hh), corrugation along +Z.
    keep(u, v) -> bool drops cells (torn edges, holes); bend(u, v) -> z offset (dents, sag, curl)."""
    prof = [(0, 0), (.36, 0), (.45, 1), (.86, 1), (.95, 0)]      # fractions of the pitch
    xs = []; zs = []; x = 0.0
    while x < L - 1e-6:
        for (fa, da) in prof[1:]:
            pass
        for k in range(len(prof)):
            px = x + prof[k][0] * pitch
            if px > L: break
            if not xs or px > xs[-1] + 1e-6:
                xs.append(px); zs.append(prof[k][1] * depth)
        x += pitch
    if xs[-1] < L: xs.append(L); zs.append(zs[-1])
    nv = max(2, int(math.ceil(Hh / vres)) + 1)
    ys = [Hh * j / (nv - 1) for j in range(nv)]
    bm = bmesh.new(); vid = {}
    def V(i, j):
        if (i, j) not in vid:
            u, v = xs[i], ys[j]
            z = zs[i] + (bend(u, v) if bend else 0.0)
            vid[(i, j)] = bm.verts.new((u, v, z))
        return vid[(i, j)]
    for i in range(len(xs) - 1):
        for j in range(nv - 1):
            cu, cv = (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2
            if keep and not keep(cu, cv):
                continue
            bm.faces.new([V(i, j), V(i + 1, j), V(i + 1, j + 1), V(i, j + 1)])
    return bm


def sheet(name, origin, X, Y, Z, L, Hh, material, keep=None, bend=None, thick=.004, **kw):
    X, Y, Z = (tuple(Vector(a).normalized()) for a in (X, Y, Z))
    bm = sheet_bm(L, Hh, keep, bend, **kw)
    place_bm(bm, origin, X, Y, Z)
    ob = mesh_obj(name, bm, material)
    if thick > 0:
        m = ob.modifiers.new("t", "SOLIDIFY"); m.thickness = thick; m.offset = 0
        bpy.context.view_layer.objects.active = ob; bpy.ops.object.modifier_apply(modifier="t")
    box_uv(ob)
    for p in ob.data.polygons: p.use_smooth = False
    return ob


def torn(edge_v, amp=.35, freq=1.7, seed=0, side="top"):
    """keep() for a torn edge at height edge_v (+ noise) — keeps cells below (top) or above (bottom) the tear."""
    def k(u, v):
        e = edge_v + amp * noise.noise(Vector((u * freq + seed * 3.1, seed * 1.7, 0))) + amp * .4 * noise.noise(Vector((u * freq * 4.3, seed, 1)))
        return v < e if side == "top" else v > e
    return k


def holes(centres):
    def k(u, v):
        for (cu, cv, r) in centres:
            if (u - cu) ** 2 + ((v - cv) * 1.3) ** 2 < r * r * (1 + .35 * noise.noise(Vector((u * 5, v * 5, cu)))):
                return False
        return True
    return k


def both(*ks):
    return lambda u, v: all(k(u, v) for k in ks if k)


def dents(amp=.02, freq=1.3, seed=0):
    return lambda u, v: amp * noise.noise(Vector((u * freq + seed, v * freq, seed * .7)))


# ---------------------------------------------------------------- the ruined processing hall
def hall():
    """Portal-frame processing hall, 3 bays x 5.5 m (X), 7 m span (Z), eaves 5.4 m, ridge 6.6 m.
    Origin: floor centre at world (-79.75, 0.12, -48). Frame A (x -8.25) and B (-2.75) stand; frame C (2.75)
    has lost its north column so its north rafter lies from the ridge to the ground; frame D (8.25, east gable)
    is sheared off. The west bay keeps part of its roof and cladding; drifted sand buries the west/south bases."""
    reset(); rnd_seed(27)
    H, R, Zc = 5.4, 6.6, 3.5
    FX = [-8.25, -2.75, 2.75, 8.25]
    def G(x, z):  # ground height in local coords
        return gy(x + HALL.x, z + HALL.z) - HALL.y
    main, detail, fallen = [], [], []
    ST, PAINT = "DP_FramePaint", "DP_FramePaint"
    # --- footings, base plates, columns
    for i, x in enumerate(FX):
        for s in (1, -1):
            z = s * Zc
            main.append(box("Footing", (x, -.1, z), (.9, .6, .9), "DP_Concrete", .03))
            detail.append(box("Base plate", (x, .215, z), (.46, .03, .56), "WG_RustSteel", .004))
            for bx in (-.17, .17):
                for bz in (-.21, .21):
                    detail.append(cyl("Anchor bolt", (x + bx, .2, z + bz), (x + bx, .29, z + bz), .016, "WG_RustSteel", 6))
            top = H
            if i == 2 and s == 1:
                top = 2.3                      # frame C north column: buckled stub
            if i == 3:
                top = 3.1 if s == 1 else 2.05  # east gable sheared
            main.append(ibeam("Column", (x, .23, z), (x, top, z), .36, .2, .012, .018, PAINT, up=(0, 0, 1)))
            if top < H:  # torn cap: a skewed plate at the break
                detail.append(box("Torn web", (x, top - .02, z), (.21, .05, .37), "WG_RustSteel", .004, rot=(8 * s, 0, 14)))
    # --- rafters, haunches, knee braces, apex (frames A, B standing; C south half only)
    for i, x in enumerate(FX[:3]):
        for s in (1, -1):
            if i == 2 and s == 1:
                continue
            a = (x, H - .15, s * Zc); b = (x, R - .15, 0)
            main.append(ibeam("Rafter", a, b, .34, .18, .01, .016, PAINT))
            detail.append(box("Haunch plate", (x, H - .12, s * (Zc - .08)), (.02, .55, .45), PAINT, .004))
            main.append(ibeam("Knee brace", (x, H - 1.45, s * (Zc - .12)), (x, H + .2, s * (Zc - 1.25)), .12, .1, .008, .01, PAINT))
        detail.append(box("Apex plate", (x, R - .12, 0), (.03, .5, .5), PAINT, .004))
    # frame C north rafter: eave end dropped onto the ground north of the hall, still hinged at the apex
    xc = FX[2]; gz = 4.7; gyc = G(xc + .55, gz) + .18
    main.append(ibeam("Fallen rafter", (xc + .1, R - .35, .25), (xc + .55, gyc, gz), .34, .18, .01, .016, PAINT, up=(0.3, 1, 0)))
    main.append(ibeam("Knee brace (hanging)", (xc + .5, gyc + .9, gz - 1.0), (xc + .9, G(xc + .9, gz + .6) + .1, gz + .6), .12, .1, .008, .01, PAINT, up=(1, 0, 0)))
    # the buckled upper column lying beside its stub
    main.append(ibeam("Buckled column", (xc - .2, 2.2, Zc + .15), (xc - 1.6, G(xc - 3.2, Zc + 2.4) + .2, Zc + 2.5), .36, .2, .012, .018, PAINT, up=(0, 1, .3)))
    # east gable rafters on the ground
    xd = FX[3]
    fallen.append(ibeam("Fallen gable rafter", (xd + .9, G(xd + .9, -2.6) + .2, -2.6), (xd + 1.6, G(xd + 1.6, 1.0) + .19, 1.0), .34, .18, .01, .016, PAINT, up=(0, 1, 0)))
    fallen.append(ibeam("Leaning gable rafter", (xd + .15, 2.0, -Zc + .1), (xd + 2.3, G(xd + 2.3, -.8) + .18, -.8), .34, .18, .01, .016, PAINT, up=(0, 1, 0)))
    # --- eave beams (north line broken after B), ridge tie, purlins
    for s in (1, -1):
        for k in range(3):
            if s == 1 and k == 1:   # B->C north eave beam broken, hanging from B to the ground near C
                main.append(ibeam("Eave beam (hanging)", (FX[1] + .15, H - .3, Zc), (FX[2] - .4, G(FX[2] - .4, Zc + .9) + .12, Zc + .9), .25, .13, .008, .012, PAINT, up=(0, 0, 1)))
                continue
            if k == 2:
                continue
            main.append(ibeam("Eave beam", (FX[k] + .12, H - .3, s * Zc), (FX[k + 1] - .12, H - .3, s * Zc), .25, .13, .008, .012, PAINT))
    for k in range(2):
        main.append(ibeam("Ridge tie", (FX[k] + .05, R - .05, 0), (FX[k + 1] - .05, R - .05, 0), .2, .1, .006, .01, PAINT))
    L = math.hypot(Zc, R - H)
    fracs = [.12, .38, .64, .9]
    def slope_pt(s, f, lift):
        z = s * Zc * (1 - f); y = (H - .15) + (R - H) * f
        n = Vector((0, Zc, s * (R - H))).normalized()          # outward normal of this slope (s=+1 north)
        return Vector((0, y, z)) + n * lift, n
    purlin_sets = {(1, 0): fracs, (-1, 0): fracs, (-1, 1): fracs, (1, 1): [.64, .9]}
    for (s, k), fl in purlin_sets.items():
        for f in fl:
            p, n = slope_pt(s, f, .27)
            a = (FX[k] + .1, p.y, p.z); b = (FX[k + 1] - .1, p.y, p.z)
            if (s, k) == (-1, 1) and f == .38:   # one purlin dropped at its C end, dangling
                b = (FX[k + 1] - 1.2, 1.4, p.z * .8)
            main.append(ibeam("Purlin", a, b, .2, .07, .005, .008, "WG_RustSteel", up=tuple(n)))
    # bay C-D: two purlins lying on the ground
    for j, (x0, z0, x1, z1) in enumerate([(3.4, -1.6, 8.6, -2.3), (4.2, 1.2, 7.8, 2.6)]):
        fallen.append(ibeam("Fallen purlin", (x0, G(x0, z0) + .1, z0), (x1, G(x1, z1) + .1, z1), .2, .07, .005, .008, "WG_RustSteel", up=(0, 1, 0)))
    # --- roof sheets
    def roof(s, k, keep, bend, name="Roof sheet"):
        p0, n = slope_pt(s, 0, .4)
        Y = (Vector((0, R - H, -s * Zc))).normalized()
        o = (FX[k] - .05, p0.y - .02, p0.z)
        return sheet(name, o, (1, 0, 0), tuple(Y), tuple(n), 5.6, L + .1, "DP_RoofSheet", keep, bend)
    main.append(roof(-1, 0, both(torn(L * .78, .45, 1.3, 1), holes([(1.6, 1.4, .35), (4.3, .7, .25)])), dents(.025, 1.1, 1)))
    main.append(roof(1, 0, both(torn(L * .42, .55, 1.1, 2), holes([(3.2, .6, .3)])), lambda u, v: dents(.03, 1.2, 2)(u, v) - .5 * max(0, v - L * .25) ** 2 * (u / 5.6) ** 1.5))
    # bay B-C south slope: a strip near the ridge, its lower edge curled down
    p0, n = slope_pt(-1, .55, .4); Y = Vector((0, R - H, Zc)).normalized()
    main.append(sheet("Roof sheet (torn)", (FX[1] + .2, p0.y, p0.z), (1, 0, 0), tuple(Y), tuple(n), 3.2, L * .45, "DP_RoofSheet",
                      torn(L * .3, .3, 1.8, 3, side="bottom"), lambda u, v: dents(.02, 1.5, 3)(u, v) - .6 * max(0, L * .18 - v) ** 1.5))
    # a single sheet hanging from the B-C south purlin, swinging down into the bay
    p1, _ = slope_pt(-1, .38, .45)
    main.append(sheet("Hanging roof sheet", (FX[1] + 1.4, p1.y, p1.z), (1, 0, 0), (0, -1, .28), (0, .28, 1), 1.1, 2.6, "DP_RoofSheet",
                      torn(2.3, .25, 2.5, 4), dents(.04, 1.8, 4)))
    # --- girts and cladding (south wall bays A-B, B-C; west gable lower half)
    gz_s = -Zc - .26
    for k in range(2):
        for y in (1.25, 2.65, 4.05):
            main.append(ibeam("Girt", (FX[k] + .1, y, gz_s + .08), (FX[k + 1] - .1, y, gz_s + .08), .15, .06, .005, .007, "WG_RustSteel", up=(0, 0, 1)))
    wall_o = lambda k: (FX[k] - .02, .15, -Zc - .36)
    main.append(sheet("South cladding A-B", wall_o(0), (1, 0, 0), (0, 1, 0), (0, 0, -1), 5.55, 5.1, "DP_WallSheet",
                      both(holes([(2.2, 1.0, .45), (4.6, 3.6, .3)]), lambda u, v: not (3.3 < u < 4.15 and v > 1.8)), dents(.03, .9, 5)))
    main.append(sheet("South cladding B-C", wall_o(1), (1, 0, 0), (0, 1, 0), (0, 0, -1), 5.55, 5.1, "DP_WallSheet",
                      torn(2.6, .7, .9, 6), dents(.04, .8, 6)))
    # peeled sheet hanging off the B-C wall
    main.append(sheet("Peeled wall sheet", (FX[1] + 3.3, 2.5, -Zc - .4), (.55, -.35, -.35), (0, 1, 0), (-.5, 0, -.8), 1.4, 2.3, "DP_WallSheet",
                      torn(2.0, .3, 2.2, 7), dents(.05, 1.6, 7)))
    for y in (1.25, 2.65):
        main.append(ibeam("Gable girt", (FX[0] - .26, y, -Zc + .1), (FX[0] - .26, y, Zc - .1), .15, .06, .005, .007, "WG_RustSteel", up=(1, 0, 0)))
    main.append(sheet("West gable cladding", (FX[0] - .36, .15, -Zc - .05), (0, 0, 1), (0, 1, 0), (-1, 0, 0), 7.1, 3.4, "DP_WallSheet",
                      both(torn(2.9, .5, 1.2, 8), lambda u, v: not (4.6 < u < 6.0 and v < 2.3)), dents(.03, 1.1, 8)))
    # --- bracing: X rods in the south wall and roof of bay A-B
    for (a, b) in [((FX[0] + .2, .5, -Zc - .2), (FX[1] - .2, H - .5, -Zc - .2)), ((FX[0] + .2, H - .5, -Zc - .2), (FX[1] - .2, .5, -Zc - .2))]:
        detail.append(cyl("Brace rod", a, b, .014, "WG_RustSteel", 6))
    for s in (1, -1):
        pa, _ = slope_pt(s, .1, .2); pb, _ = slope_pt(s, .9, .2)
        detail.append(cyl("Roof brace", (FX[0] + .2, pa.y, pa.z), (FX[1] - .2, pb.y, pb.z), .012, "WG_RustSteel", 6))
    # snapped roof brace in bay B-C hanging down
    pa, _ = slope_pt(-1, .15, .2)
    detail.append(tube("Snapped brace", [(FX[1] + .2, pa.y, pa.z), (FX[1] + 1.2, pa.y - .9, pa.z + .6), (FX[1] + 1.5, pa.y - 2.4, pa.z + .9)], .012, "WG_RustSteel", 5))
    # --- lamp brackets and a dead hanging lamp (the lamp model is a Poly Haven prop placed in Unity)
    empty("MOUNT_hanging_lamp", (FX[1] - 2.0, H - .1, -.9))
    empty("LIGHT_hall_spark", (FX[1] + 1.8, H - .4, -1.2))
    # --- collision proxies (Unity BoxColliders)
    for i, x in enumerate(FX):
        for s in (1, -1):
            top = 2.3 if (i == 2 and s == 1) else (3.1 if s == 1 else 2.05) if i == 3 else H
            box("COL_Column", (x, top / 2, s * Zc), (.3, top, .45), "WG_Collider", 0)
    for k in range(2):
        box("COL_South wall", ((FX[k] + FX[k + 1]) / 2, 2.6, -Zc - .3), (5.5, 5.2, .25), "WG_Collider", 0)
    box("COL_West gable", (FX[0] - .3, 1.6, 0), (.25, 3.2, 7.1), "WG_Collider", 0)
    box("COL_Fallen rafter", (xc + .35, 1.4, 3.3), (.5, 2.8, 2.4), "WG_Collider", 0)
    box("COL_Buckled column", (xc - 1.0, .6, Zc + 1.3), (1.8, 1.0, 1.2), "WG_Collider", 0, rot=(0, 40, 0))
    # --- assemble LODs
    m0 = join("DP_Hall_LOD0", main + fallen)
    d0 = join("DP_HallDetail_LOD0", detail)
    decimate_copy(m0, .45, "DP_Hall_LOD1")
    export("DP_Hall", "ruined portal-frame processing hall, 16.5 x 7 m, west bay roofed, frame C collapsed, east gable sheared")


# ---------------------------------------------------------------- shattered drone bays (inside the hall, south wall)
def drone_rack():
    """Rail of four drone docking arms along the inside of the south wall (local = hall coordinates).
    Arms 1 and 3 intact (clamp ring, contact head), arm 2 snapped and hanging, arm 4 gone (its ring on the floor)."""
    reset(); rnd_seed(4)
    H = 3.35; zr = -3.05
    parts = []; detail = []
    parts.append(ibeam("Dock rail", (-8.05, H, zr), (2.5, H, zr), .3, .16, .01, .014, "DP_FramePaint", up=(0, 1, 0)))
    for x in (-8.1, -2.75):
        parts.append(box("Rail bracket", (x + .1, H - .05, zr - .2), (.2, .45, .5), "DP_FramePaint", .01))
    for i, x in enumerate((-6.6, -4.2, -1.3, 1.3)):
        if i == 3:
            ring_at = Vector((x + .6, gy(x + .6 + HALL.x, -1.9 + HALL.z) - HALL.y + .06, -1.9)); tilt = (7, 0, 4)
        else:
            parts.append(box("Arm carriage", (x, H - .25, zr), (.42, .22, .42), "WG_OlivePaint", .015))
            if i == 1:  # snapped: arm swings down and out
                a = (x, H - .35, zr); b = (x + .7, 1.4, zr + .55)
                parts.append(cyl("Arm (snapped)", a, b, .065, "DP_FramePaint", 10))
                detail.append(tube("Torn hose", [(x, H - .35, zr + .08), (x + .3, 2.0, zr + .3), (x + .45, 1.1, zr + .5), (x + .5, .6, zr + .4)], .02, "WG_Rubber", 6))
                ring_at = Vector(b) + Vector((.05, -.2, .1)); tilt = (35, 25, 60)
            else:
                parts.append(cyl("Arm", (x, H - .35, zr), (x, 2.05, zr + .45), .065, "DP_FramePaint", 10))
                parts.append(cyl("Arm piston", (x + .09, H - .45, zr + .02), (x + .09, 2.3, zr + .36), .025, "WG_RustSteel", 8))
                ring_at = Vector((x, 1.75, zr + .55)); tilt = (0, 0, 0)
                # contact head with a faint cyan status lamp (only arm 1 still powered)
                parts.append(cyl("Contact head", (x, 2.05, zr + .45), (x, 1.9, zr + .5), .09, "WG_InteriorDark", 12))
                detail.append(cyl("Status lamp", (x + .07, 2.0, zr + .52), (x + .07, 2.0, zr + .56), .018, "DP_CyanCell" if i == 0 else "WG_InteriorDark", 8))
        # clamp ring (torus); claws only on the intact arms
        bpy.ops.mesh.primitive_torus_add(major_radius=.52, minor_radius=.045, major_segments=24, minor_segments=6)
        ring = bpy.context.active_object; ring.name = "Clamp ring"
        ring.data.materials.clear(); ring.data.materials.append(wg.mat("DP_FramePaint"))
        R = Matrix.Rotation(math.radians(tilt[0]), 4, "X") @ Matrix.Rotation(math.radians(tilt[1]), 4, "Y") @ Matrix.Rotation(math.radians(tilt[2]), 4, "Z")
        ring.data.transform(R); ring.location = U(*ring_at)
        for o in bpy.context.selected_objects: o.select_set(False)
        bpy.context.view_layer.objects.active = ring; ring.select_set(True)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True); box_uv(ring)
        for p in ring.data.polygons: p.use_smooth = True
        parts.append(ring)
        if i in (0, 2):
            for c in range(3):
                ang = c * 2.094 + .3
                o = ring_at + Vector((math.cos(ang) * .52, 0, math.sin(ang) * .52))
                tip = ring_at + Vector((math.cos(ang) * .36, .3, math.sin(ang) * .36))
                detail.append(cyl("Claw", tuple(o), tuple(tip), .03, "WG_RustSteel", 6))
    # cable loom along the rail
    detail.append(tube("Rail loom", [(-8.0, H + .2, zr + .05), (-4.0, H + .05, zr + .08), (0, H + .15, zr + .06), (2.4, H + .1, zr + .05)], .04, "WG_Rubber", 8))
    detail.append(tube("Loom drop", [(2.4, H + .1, zr + .05), (2.7, 2.2, zr + .2), (2.9, .9, zr + .5), (3.1, gy(3.1 + HALL.x, zr + .9 + HALL.z) - HALL.y + .05, zr + .9)], .04, "WG_Rubber", 8))
    box("COL_Fallen ring", (1.9, .2, -1.9), (1.2, .4, 1.2), "WG_Collider", 0)
    a = join("DP_DroneRack_LOD0", parts); b = join("DP_DroneRackDetail_LOD0", detail)
    decimate_copy(a, .4, "DP_DroneRack_LOD1")
    export("DP_DroneRack", "shattered drone docking rail inside the hall's south wall (hall origin)")


# ---------------------------------------------------------------- conveyor spine
def conveyor():
    """Truss conveyor gallery from the hall's west gable (world -88.4, 5.0, -46) up the escarpment to a feed
    hopper at (-99.6, 9.3, -33.4). Section 2 snapped at trestle 1 and lies from the ground up to trestle 2;
    the belt hangs from the broken end. Origin: world (x, 0, z) of the hall entry."""
    reset(); rnd_seed(9)
    P0 = Vector((-88.4, 5.0, -46.0)); P3 = Vector((-99.6, 9.3, -33.4))
    def L(p): return (p[0] - CONV.x, p[1] - CONV.y, p[2] - CONV.z)
    def at(t): return P0.lerp(P3, t)
    T = [.30, .63]
    main, detail = [], []
    W, Hh = 1.3, 1.1
    def gallery(a, b, broken_a=False, name="Gallery"):
        a, b = Vector(a), Vector(b); d = (b - a); n = d.length; dn = d.normalized()
        side = dn.cross(Vector((0, 1, 0))).normalized(); up = side.cross(dn).normalized()
        parts, dets = [], []
        for sx in (-1, 1):
            for sy in (0, 1):
                o = side * sx * W / 2 + up * sy * Hh
                parts.append(ibeam(name + " chord", L(a + o), L(b + o), .1, .08, .006, .008, "DP_FramePaint", up=tuple(up)))
        k = max(2, int(n / 1.6))
        for i in range(k + 1):
            p = a + d * (i / k)
            for sx in (-1, 1):
                dets.append(box(name + " post", L(p + side * sx * W / 2 + up * Hh / 2), (.07, Hh, .07), "DP_FramePaint", .004,
                                rot=(0, math.degrees(math.atan2(dn.x, dn.z)), 0)))
            if i < k:
                q = a + d * ((i + 1) / k)
                for sx in (-1, 1):
                    dets.append(cyl(name + " diagonal", L(p + side * sx * W / 2), L(q + side * sx * W / 2 + up * Hh), .02, "WG_RustSteel", 5))
            # idler rollers (troughed: centre + two wings)
            c = p + up * .35
            dets.append(cyl("Idler", L(c - side * .22), L(c + side * .22), .05, "WG_RustSteel", 8))
            for sx in (-1, 1):
                dets.append(cyl("Idler wing", L(c + side * sx * .22), L(c + side * sx * .45 + up * .17), .05, "WG_RustSteel", 8))
        # belt: troughed strip
        bm = bmesh.new(); rows = []
        prof = [(-.47, .2), (-.24, .03), (.24, .03), (.47, .2)]
        for i in range(k * 2 + 1):
            p = a + d * (i / (k * 2)) + up * .41
            rows.append([bm.verts.new(U(*L(p + side * px + up * py))) for px, py in prof])
        for i in range(len(rows) - 1):
            for j in range(3):
                bm.faces.new([rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j]])
        belt = mesh_obj(name + " belt", bm, "DP_Belt")
        mm = belt.modifiers.new("t", "SOLIDIFY"); mm.thickness = .012
        bpy.context.view_layer.objects.active = belt; bpy.ops.object.modifier_apply(modifier="t"); box_uv(belt)
        parts.append(belt)
        # walkway plate along one side + handrail posts
        wp = a + side * (W / 2 + .35)
        parts.append(ibeam(name + " walkway", L(wp), L(wp + d), .05, .6, .004, .004, "WG_PlateSteel", up=tuple(up)))
        for i in range(0, k + 1, 1):
            p = a + d * (i / k) + side * (W / 2 + .62)
            dets.append(cyl("Handrail post", L(p), L(p + up * 1.0), .02, "WG_RustSteel", 6))
        dets.append(cyl("Handrail", L(a + side * (W / 2 + .62) + up * 1.0), L(b + side * (W / 2 + .62) + up * 1.0), .02, "WG_RustSteel", 6))
        # hood panels over the belt (half of them gone)
        for i in range(k):
            if random.random() < .45: continue
            p = a + d * ((i + .5) / k) + up * (Hh - .05)
            parts.append(box("Hood panel", L(p), (W - .1, .03, n / k - .08), "DP_RoofSheet", .004,
                             rot=(-math.degrees(math.asin(max(-1, min(1, dn.y)))), math.degrees(math.atan2(dn.x, dn.z)), random.uniform(-6, 6))))
        return parts, dets
    t1 = at(T[0]); t2 = at(T[1])
    for seg in [(P0, t1 + (P0 - t1).normalized() * .3)]:
        p, dd = gallery(*seg, name="Gallery 1"); main += p; detail += dd
    # section 2: snapped at trestle 1, its low end on the ground
    g2 = Vector((t1.x - 1.0, gy(t1.x - 1.0, t1.z + 1.2) + .25, t1.z + 1.2))
    p, dd = gallery(g2, t2, name="Gallery 2"); main += p; detail += dd
    p, dd = gallery(t2, P3, name="Gallery 3"); main += p; detail += dd
    # belt hanging from the broken end of section 1
    e = t1 + (P0 - t1).normalized() * .3 + Vector((0, .41, 0))
    detail.append(tube("Hanging belt", [L(e), L(e + Vector((-.3, -1.6, .5))), L(g2 + Vector((.3, .6, -.2)))], .05, "DP_Belt", 6))
    # trestle bents (A-frames with bracing) at t1 (holds section 1's broken end) and t2
    for tp, top in ((t1, t1), (t2, t2)):
        g = gy(tp.x, tp.z)
        for sx in (-1, 1):
            side = Vector((12.6, 0, 11.2)).normalized() * sx   # across the gallery (perpendicular in plan)
            foot = tp + side * 1.25; foot.y = gy(foot.x, foot.z) - .2
            head = tp + side * .7; head.y = top.y - .05
            main.append(ibeam("Trestle leg", L(foot), L(head), .22, .16, .008, .012, "DP_FramePaint", up=(0, 0, 1)))
            main.append(box("Trestle footing", L((foot.x, foot.y - .05, foot.z)), (.8, .6, .8), "DP_Concrete", .03))
        a = tp + Vector((12.6, 0, 11.2)).normalized() * -1.0; b = tp + Vector((12.6, 0, 11.2)).normalized() * 1.0
        for y in (g + 1.0, (g + top.y) / 2 + .2):
            detail.append(cyl("Trestle brace", L((a.x, y, a.z)), L((b.x, y, b.z)), .04, "WG_RustSteel", 8))
        main.append(ibeam("Trestle cap", L((a.x, top.y - .05, a.z)), L((b.x, top.y - .05, b.z)), .2, .15, .008, .012, "DP_FramePaint"))
    # hall-end support: bracket off the west gable column line
    main.append(box("Gable bracket", L(P0 + Vector((.35, -.15, 0))), (.6, .3, 1.5), "DP_FramePaint", .01))
    # head: feed hopper tower on the slope
    hx, hz = P3.x - .2, P3.z + .3; hg = gy(hx, hz)
    for dx in (-.9, .9):
        for dz in (-.9, .9):
            main.append(ibeam("Hopper leg", L((hx + dx, hg - .2, hz + dz)), L((hx + dx * .8, P3.y + .2, hz + dz * .8)), .18, .14, .008, .012, "DP_FramePaint", up=(0, 0, 1)))
    bm = bmesh.new()
    top_r, bot_r, y0, y1 = 1.1, .35, P3.y + .2, P3.y + 2.0
    vs = []
    for (r, y) in ((bot_r, y0 - .6), (top_r, y0 + .5), (top_r, y1)):
        vs.append([bm.verts.new(U(*L((hx + math.cos(a) * r * 1.0 * (1 if abs(math.cos(a)) > .5 else 1), y, hz + math.sin(a) * r)))) for a in [math.pi / 4 + k * math.pi / 2 for k in range(4)]])
    for i in range(2):
        for j in range(4):
            bm.faces.new([vs[i][j], vs[i][(j + 1) % 4], vs[i + 1][(j + 1) % 4], vs[i + 1][j]])
    hop = mesh_obj("Feed hopper", bm, "DP_RoofSheet")
    mm = hop.modifiers.new("t", "SOLIDIFY"); mm.thickness = .01
    bpy.context.view_layer.objects.active = hop; bpy.ops.object.modifier_apply(modifier="t"); box_uv(hop); main.append(hop)
    detail.append(box("Head pulley housing", L(P3 + Vector((0, .6, 0))), (1.5, .8, 1.0), "WG_OlivePaint", .02, rot=(0, 48, 0)))
    detail.append(cyl("Head pulley", L(P3 + Vector((-.5, .6, -.45))), L(P3 + Vector((.5, .6, .45))), .3, "WG_RustSteel", 14))
    # colliders: fallen section on the slope and trestle legs
    box("COL_Fallen gallery", L((g2 + t2) / 2), (1.8, 1.4, (t2 - g2).length), "WG_Collider", 0,
        rot=(-math.degrees(math.atan2(t2.y - g2.y, math.hypot(t2.x - g2.x, t2.z - g2.z))), math.degrees(math.atan2(t2.x - g2.x, t2.z - g2.z)), 0))
    for tp in (t1, t2):
        box("COL_Trestle", L((tp.x, gy(tp.x, tp.z) + 1.5, tp.z)), (3.0, 3.0, .6), "WG_Collider", 0, rot=(0, math.degrees(math.atan2(12.6, 11.2)) + 90, 0))
    m0 = join("DP_Conveyor_LOD0", main); d0 = join("DP_ConveyorDetail_LOD0", detail)
    decimate_copy(m0, .45, "DP_Conveyor_LOD1")
    export("DP_Conveyor", "truss conveyor spine from the hall up the escarpment; middle section snapped")


# ---------------------------------------------------------------- charging cradles (the power source)
def cradle(broken=False):
    """Drone charging cradle: octagonal footing, finned housing with three cyan power-cell windows, a contact
    crown with three clamp arms that cup a hovering drone. ~2.1 m tall. Origin: base centre on its plinth.
    The broken variant: a housing panel torn open (exposed glowing core), one arm snapped off, leaning."""
    name = "DP_CradleBroken" if broken else "DP_Cradle"
    reset(); rnd_seed(31 if broken else 30)
    parts, detail, glow = [], [], []
    def octo(nm, y0, y1, r0, r1, material, sides=8):
        bm = bmesh.new(); rings = []
        for (y, r) in ((y0, r0), (y1, r1)):
            rings.append([bm.verts.new(U(math.cos(a) * r, y, math.sin(a) * r)) for a in [math.pi / sides + k * 2 * math.pi / sides for k in range(sides)]])
        for j in range(sides):
            bm.faces.new([rings[0][j], rings[0][(j + 1) % sides], rings[1][(j + 1) % sides], rings[1][j]])
        bm.faces.new(rings[1]); bm.faces.new(rings[0][::-1])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        ob = mesh_obj(nm, bm, material); wg.finish(ob, .012, 1); return ob
    parts.append(octo("Footing", 0, .16, .72, .68, "WG_RustSteel"))
    parts.append(octo("Skirt", .16, .42, .6, .56, "WG_Hazard"))
    parts.append(octo("Housing", .42, 1.38, .46, .43, "WG_BonePaint"))
    parts.append(octo("Shoulder", 1.38, 1.52, .5, .36, "WG_BonePaint"))
    # cooling fins
    for k in range(8):
        a = k * math.pi / 4
        if broken and k in (1, 2): continue
        detail.append(box("Fin", (math.cos(a) * .47, .9, math.sin(a) * .47), (.1, .85, .03), "WG_RustSteel", .004, rot=(0, -math.degrees(a), 0)))
    # three cell windows (emissive) with bars
    for k in range(3):
        a = math.pi / 8 + k * 2 * math.pi / 3
        if broken and k == 0:
            continue
        c = Vector((math.cos(a) * .452, .9, math.sin(a) * .452))
        glow.append(box("Power cell window", tuple(c), (.02, .62, .16), "DP_CyanCell", .002, rot=(0, -math.degrees(a), 0)))
        for dy in (-.2, 0, .2):
            detail.append(box("Window bar", tuple(c + Vector((math.cos(a) * .015, dy, math.sin(a) * .015))), (.02, .025, .19), "WG_RustSteel", .002, rot=(0, -math.degrees(a), 0)))
    if broken:
        # torn-open panel: dark cavity with the glowing core rod visible, the panel bent out
        a = math.pi / 8
        glow.append(cyl("Exposed core", (0, .5, 0), (0, 1.3, 0), .13, "DP_CyanCell", 12))
        parts.append(box("Torn panel", (math.cos(a) * .72, .45, math.sin(a) * .72), (.03, .7, .36), "WG_BonePaint", .006, rot=(20, -math.degrees(a), 64)))
        detail.append(box("Cavity", (math.cos(a) * .36, .9, math.sin(a) * .36), (.12, .8, .34), "WG_InteriorDark", .004, rot=(0, -math.degrees(a), 0)))
        empty("FX_arc", (math.cos(a) * .42, 1.05, math.sin(a) * .42))
    # contact crown and clamp arms
    parts.append(cyl("Crown post", (0, 1.52, 0), (0, 1.78, 0), .14, "WG_RustSteel", 12))
    parts.append(cyl("Contact plate", (0, 1.78, 0), (0, 1.84, 0), .3, "WG_InteriorDark", 16))
    glow.append(cyl("Contact ring", (0, 1.84, 0), (0, 1.855, 0), .22, "DP_CyanCell", 16))
    for k in range(3):
        a = k * 2 * math.pi / 3 + .5
        if broken and k == 2:
            # snapped arm lies at the foot of the cradle
            b0 = Vector((math.cos(a) * 1.0, .06, math.sin(a) * 1.0))
            parts.append(cyl("Snapped arm", tuple(b0), tuple(b0 + Vector((-.5, .08, .45))), .05, "DP_FramePaint", 8))
            detail.append(cyl("Snapped claw", tuple(b0 + Vector((-.5, .08, .45))), tuple(b0 + Vector((-.62, .04, .7))), .035, "WG_RustSteel", 6))
            continue
        base = Vector((math.cos(a) * .3, 1.6, math.sin(a) * .3))
        elbow = Vector((math.cos(a) * .62, 2.0, math.sin(a) * .62))
        tip = Vector((math.cos(a) * .52, 2.28, math.sin(a) * .52))
        parts.append(cyl("Arm", tuple(base), tuple(elbow), .05, "DP_FramePaint", 8))
        parts.append(cyl("Arm upper", tuple(elbow), tuple(tip), .04, "DP_FramePaint", 8))
        detail.append(cyl("Arm piston", tuple(base + Vector((0, -.05, 0))), tuple((base + elbow) / 2 + Vector((0, .05, 0))), .02, "WG_RustSteel", 6))
        detail.append(box("Claw pad", tuple(tip), (.1, .05, .14), "WG_Rubber", .01, rot=(0, -math.degrees(a), 30)))
    # cable glands at the base
    for k in range(3):
        a = k * 2 * math.pi / 3 + 1.1
        detail.append(cyl("Cable gland", (math.cos(a) * .5, .12, math.sin(a) * .5), (math.cos(a) * .66, .1, math.sin(a) * .66), .06, "WG_RustSteel", 10))
    # data plate + hazard sticker positions
    detail.append(box("Data plate", (0, 1.1, -.44), (.18, .12, .01), "WG_PlateSteel", .002))
    empty("LIGHT_cell", (0, 1.05, 0))
    box("COL_Cradle", (0, .95, 0), (1.1, 1.9, 1.1), "WG_Collider", 0)
    objs = parts + detail + glow
    lod0 = join(name + "_LOD0", objs)
    decimate_copy(lod0, .35, name + "_LOD1")
    if broken:
        for ob in bpy.context.scene.objects:
            if ob.type == "MESH" and not ob.name.startswith("COL_"):
                ob.data.transform(Matrix.Rotation(math.radians(-7), 4, "Y"))   # lean (Blender Y = Unity -Z axis)
    export(name, "drone charging cradle (power cell), broken variant" if broken else "drone charging cradle (power cell)")


# ---------------------------------------------------------------- power plinth
def plinth():
    """Cracked concrete plinth carrying the three cradles, with steel edge angles, a cable trench on its south
    side and grating covers. Origin: top-surface centre; 7.6 x 2.6 m, 0.75 m deep (buried to suit the ground)."""
    reset(); rnd_seed(12)
    parts, detail = [], []
    Lx, Lz, D = 7.6, 2.6, .75
    parts.append(box("Plinth", (0, -D / 2, 0), (Lx, D, Lz), "DP_Concrete", .04))
    for s in (1, -1):
        detail.append(box("Edge angle", (0, -.03, s * (Lz / 2 + .005)), (Lx - .1, .06, .02), "WG_RustSteel", .003))
    # cable trench (south side) with two grating covers missing
    parts.append(box("Trench lip", (0, .02, -Lz / 2 + .32), (Lx - .5, .06, .08), "WG_RustSteel", .004))
    for i in range(6):
        if i in (2, 4): continue
        detail.append(box("Trench cover", (-3.1 + i * 1.24, .015, -Lz / 2 + .17), (1.18, .03, .26), "WG_PlateSteel", .004))
    # anchor bolts for the cradles
    for x in (-2.6, 0, 2.6):
        for k in range(6):
            a = k * math.pi / 3
            detail.append(cyl("Anchor bolt", (x + math.cos(a) * .6, 0, math.sin(a) * .6), (x + math.cos(a) * .6, .07, math.sin(a) * .6), .02, "WG_RustSteel", 6))
    # broken corner (NE) chunk lying beside it
    detail.append(box("Spalled chunk", (Lx / 2 + .45, -.35, Lz / 2 - .2), (.5, .3, .6), "DP_Concrete", .05, rot=(12, 30, 18)))
    box("COL_Plinth", (0, -D / 2, 0), (Lx, D, Lz), "WG_Collider", 0)
    lod0 = join("DP_Plinth_LOD0", parts + detail)
    decimate_copy(lod0, .4, "DP_Plinth_LOD1")
    export("DP_Plinth", "concrete power plinth with cable trench")


# ---------------------------------------------------------------- broken concrete walls
def wall(name, length, height, broken_left=False, broken_right=False, notch=None, seed=1, thick=.32):
    """Cast concrete wall panel: jagged top, broken ends with exposed bent rebar. Local X = length centred,
    origin at the base centre; the wall extends 0.4 m below grade."""
    reset(); rnd_seed(seed)
    n = 40
    top = []
    for i in range(n + 1):
        u = i / n; x = -length / 2 + u * length
        h = height + .06 * noise.noise(Vector((x * 1.7, seed, 0)))
        if notch:
            c, w, d = notch
            h -= d * max(0, 1 - abs(x - c) / w) ** 1.2 * (1 + .3 * noise.noise(Vector((x * 4, seed, 2))))
        if broken_left and x < -length / 2 + .8: h -= (1 - (x + length / 2) / .8) * height * .45 * (1 + .4 * noise.noise(Vector((x * 5, seed, 3))))
        if broken_right and x > length / 2 - .8: h -= (1 - (length / 2 - x) / .8) * height * .55 * (1 + .4 * noise.noise(Vector((x * 5, seed, 4))))
        top.append((x, max(.25, h)))
    bm = bmesh.new()
    front, back = [], []
    for (x, h) in top:
        for zs, lst in ((-thick / 2, front), (thick / 2, back)):
            lst.append((bm.verts.new(U(x, -.4, zs)), bm.verts.new(U(x, h, zs + .012 * noise.noise(Vector((x * 3, h, zs)))))))
    for i in range(n):
        f0, f1 = front[i], front[i + 1]; b0, b1 = back[i], back[i + 1]
        bm.faces.new([f0[0], f1[0], f1[1], f0[1]])
        bm.faces.new([b0[1], b1[1], b1[0], b0[0]])
        bm.faces.new([f0[1], f1[1], b1[1], b0[1]])
        bm.faces.new([f0[0], b0[0], b1[0], f1[0]])
    bm.faces.new([front[0][0], front[0][1], back[0][1], back[0][0]])
    bm.faces.new([front[-1][0], back[-1][0], back[-1][1], front[-1][1]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = mesh_obj(name + "_LOD0", bm, "DP_Concrete")
    # chipped surface: displace along normals a little, then bevel the cast edges
    sub = ob.modifiers.new("sub", "SUBSURF"); sub.levels = 1; sub.subdivision_type = "SIMPLE"
    bpy.context.view_layer.objects.active = ob; bpy.ops.object.modifier_apply(modifier="sub")
    for v in ob.data.vertices:
        v.co += v.normal * .018 * noise.noise(v.co * 2.3 + Vector((seed, 0, 0)))
    wg.finish(ob, .02, 1, uv=True, smooth_angle=30)
    parts = [ob]
    # rebar sticking out of the broken ends and the notch
    ends = []
    if broken_left: ends.append((-length / 2 + .15, -1))
    if broken_right: ends.append((length / 2 - .15, 1))
    for (x, s) in ends:
        for zs in (-.09, .09):
            for y in (height * .25, height * .48):
                a = Vector((x, y, zs)); b = a + Vector((s * random.uniform(.35, .7), random.uniform(-.05, .25), random.uniform(-.1, .1)))
                c = b + Vector((s * random.uniform(.1, .3), random.uniform(-.35, -.1), random.uniform(-.15, .15)))
                parts.append(tube("Rebar", [tuple(a), tuple(b), tuple(c)], .008, "WG_RustSteel", 5))
    if notch:
        c, w, d = notch
        for k in range(3):
            x = c - w * .4 + k * w * .4
            parts.append(tube("Rebar", [(x, height - d * .8, -.09), (x + random.uniform(-.15, .15), height - d * .2, -.12), (x + random.uniform(-.3, .3), height - d * .05 + .1, -.2)], .008, "WG_RustSteel", 5))
    box("COL_Wall", (0, height / 2 - .2, 0), (length, height + .4, thick + .04), "WG_Collider", 0)
    lod0 = join(name + "_LOD0", parts)
    decimate_copy(lod0, .3, name + "_LOD1")
    export(name, f"broken cast-concrete wall {length} x {height} m")


def walls():
    wall("DP_WallA", 3.0, 1.55, notch=(.4, .8, .7), seed=3)
    wall("DP_WallB", 2.4, 1.2, broken_right=True, seed=5)
    wall("DP_WallC", 3.2, 1.8, broken_left=True, notch=(.9, .6, .5), seed=7)
    wall("DP_WallD", 1.8, .95, broken_left=True, broken_right=True, seed=9)


# ---------------------------------------------------------------- cable runs (world, anchored at the hall origin)
def cables():
    """Power cables snaking from each cradle down the plinth edge and across the yard to the hall power cabinet;
    a heavy feeder up hall column B north to the eave. Anchor: HALL. Uses the sculpted ground heights."""
    reset(); rnd_seed(44)
    objs = []
    cab = Vector((-81.3, 0, -44.1))                 # power cabinet (Poly Haven power box) at the hall's north line
    plinth_c = Vector((-80.4, .5, -39.4)); top = .5
    def ground_path(pts, r, lift=.0):
        out = []
        for i in range(len(pts) - 1):
            a, b = Vector(pts[i]), Vector(pts[i + 1]); n = max(2, int((b - a).length / .35))
            for k in range(n):
                p = a.lerp(b, k / n)
                wob = Vector((noise.noise(p * .8) * .18, 0, noise.noise(p * .8 + Vector((5, 0, 5))) * .18))
                q = p + wob
                y = max(q.y, gy(q.x, q.z) + r * .8 + lift) if q.y < 0 else q.y
                out.append((q.x - HALL.x, y - HALL.y, q.z - HALL.z))
        e = Vector(pts[-1]); out.append((e.x - HALL.x, max(e.y, gy(e.x, e.z) + r) - HALL.y if e.y < 0 else e.y - HALL.y, e.z - HALL.z))
        return out
    for k, x in enumerate((-83.0, -80.4, -77.8)):
        gl = Vector((x + .3, top - .45, plinth_c.z - .5))
        pts = [(x + .45, top + .1, plinth_c.z - .45), (x + .5, top + .02, plinth_c.z - 1.25), (x + .5, -1, plinth_c.z - 1.45),
               (x + .3 - k * .2, -1, -42.2), (cab.x + .6 * (k - 1), -1, cab.z + .9), (cab.x + .25 * (k - 1), -1, cab.z + .3)]
        objs.append(tube("Cradle feed", ground_path(pts, .045), .045, "WG_Rubber", 8))
    # loose spare cable coil and a run toward the conveyor trestle
    objs.append(tube("Conveyor feed", ground_path([(cab.x - .5, .3, cab.z), (-84.5, -1, -44.8), (-87.0, -1, -45.5), (-87.75, -1, -44.8), (-87.75, 2.4, -44.78), (-87.8, 4.6, -44.78), (-88.3, 4.9, -45.6)], .05), .05, "WG_Rubber", 8))
    objs.append(tube("Loose cable", ground_path([(-76.4, -1, -41.2), (-75.6, -1, -40.0), (-74.9, -1, -40.6), (-74.2, -1, -39.4), (-73.6, -1, -38.9)], .03), .03, "WG_Rubber", 6))
    lod0 = join("DP_Cables_LOD0", objs)
    decimate_copy(lod0, .35, "DP_Cables_LOD1")
    export("DP_Cables", "cable runs from the cradles to the hall power cabinet and the conveyor (hall origin)")


# ---------------------------------------------------------------- signs
def sign_hall():
    """Enamel-plate hall sign hanging from the eave beam by two chains (one hanger bent, so it hangs askew).
    Origin: the hanging point on the beam; plate 2.4 x 0.6 m faces +Z (north)."""
    reset()
    parts = []
    parts.append(box("Sign frame", (0, -.62, 0), (2.5, .68, .05), "WG_RustSteel", .01))
    parts.append(wg.quad("Sign face", (0, -.62, .028), 2.4, .6, "DP_SignHall", facing=(0, 0, 1)))
    for x, y0 in ((-1.1, -.28), (1.1, -.28)):
        parts.append(cyl("Hanger chain", (x * .98, 0, 0), (x, y0 + (.14 if x > 0 else -.14), 0), .012, "WG_RustSteel", 5))
    lod0 = join("DP_SignHallPlate_LOD0", parts)
    lod0.data.transform(Matrix.Rotation(math.radians(6), 4, "Y"))    # hangs askew (Blender Y = Unity -Z axis)
    export("DP_SignHallPlate", "PROCESSING HALL 3 plate on chains")


def sign_voltage():
    """Hazard plate on a steel post. Origin: post foot; plate faces +Z."""
    reset()
    parts = [cyl("Post", (0, -.3, 0), (0, 1.7, 0), .04, "WG_RustSteel", 10),
             box("Plate back", (0, 1.35, -.01), (.62, .47, .02), "WG_RustSteel", .004),
             wg.quad("Plate face", (0, 1.35, .002), .6, .45, "DP_SignVoltage", facing=(0, 0, 1))]
    for y in (1.2, 1.5):
        parts.append(box("Clamp", (0, y, -.04), (.12, .04, .06), "WG_RustSteel", .003))
    box("COL_Post", (0, .7, 0), (.12, 1.8, .12), "WG_Collider", 0)
    join("DP_SignVoltagePost_LOD0", parts)
    export("DP_SignVoltagePost", "HIGH VOLTAGE plate on a post")


ASSETS = {"DP_Hall": hall, "DP_DroneRack": drone_rack, "DP_Conveyor": conveyor, "DP_Cradle": lambda: cradle(False),
          "DP_CradleBroken": lambda: cradle(True), "DP_Plinth": plinth, "DP_Walls": walls, "DP_Cables": cables, "DP_SignHallPlate": sign_hall, "DP_SignVoltagePost": sign_voltage}

if __name__ == "__main__":
    only = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for k, fn in ASSETS.items():
        if only and k not in only:
            continue
        fn()
    rp = HERE / "authored-assets.json"
    old = json.loads(rp.read_text()) if rp.exists() else {}
    old.update(REPORT); rp.write_text(json.dumps(old, indent=1))
