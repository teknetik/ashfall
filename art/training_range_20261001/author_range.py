"""Warden training range authored pieces (1 Oct 2026), Blender 5.2 headless.

Run:  $O/blender.sh author_range.py [-- TR_Name ...]
Reads layout.json (kit dimensions, the revetment toe path, cable paths) and the survey ground (ground.py).
Coordinates are written in Unity metres (X east, Y up, Z north; props face +Z) through the West Gate helpers
(art/west_gate_20260926/author_west_gate.py: U(), box/cyl/tube/quad, sandbags, export), so the glTF/glTFast axis
mapping, metre UVs and COL_/LIGHT_ conventions are the same as the West Gate kit. Timber members get UVs with the grain
along their length. Every asset writes Art/TrainingRange/Structures/<Name>.glb (LOD0, LOD1 where it pays) and a record
in authored-assets.json. Path-based pieces (revetment, cables) are authored in world space relative to their first
point, which the Unity pass uses as the prefab position.
"""
import bpy, bmesh, json, math, random, sys
from pathlib import Path
from mathutils import Vector, Matrix, noise

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "west_gate_20260926"))
sys.path.insert(0, str(HERE))
import author_west_gate as wg  # noqa: E402
import ground as GR  # noqa: E402

OUT = HERE.parents[1] / "unity/AthenHill/Assets/AthenHill/Art/TrainingRange/Structures"
OUT.mkdir(parents=True, exist_ok=True)
wg.OUT = OUT
LAYOUT = json.loads((HERE / "layout.json").read_text())
KIT = LAYOUT["kit"]
U, box, cyl, tube, quad, empty, join, mat = wg.U, wg.box, wg.cyl, wg.tube, wg.quad, wg.empty, wg.join, wg.mat


def rnd(seed):
    return random.Random(seed)


# ---------------------------------------------------------------- timber with the grain along the member
def tbox(name, center, size, material="TR_Timber", rot=(0, 0, 0), bevel=0.006, seed=None, uv_scale=1.0):
    """Box in Unity metres; UVs in metres in the box's own frame with v along its longest axis (the grain)."""
    r = random.Random(seed if seed is not None else hash((name, center)) & 0xffff)
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    uvl = bm.loops.layers.uv.new("UVMap")
    long_ax = max(range(3), key=lambda i: size[i])
    off = (r.random() * 5, r.random() * 5)
    bm.normal_update()
    for f in bm.faces:
        n = f.normal; ax = max(range(3), key=lambda i: abs(n[i]))
        plane = [i for i in range(3) if i != ax]
        va = long_ax if long_ax in plane else max(plane, key=lambda i: size[i])
        ua = [i for i in plane if i != va][0]
        for lp in f.loops:
            co = lp.vert.co
            lp[uvl].uv = (co[ua] * uv_scale + off[0], co[va] * uv_scale + off[1])
    R = wg.urot(*rot); c = Vector(center)
    for v in bm.verts:
        v.co = R @ v.co + c
    wg.to_blender(bm)
    ob = wg.mesh_obj(name, bm, material)
    wg.finish(ob, bevel, 1, uv=False)
    return ob


def beam(name, a, b, w, h, material="TR_Timber", up=(0, 1, 0), bevel=0.005, seed=None):
    """Rectangular member between Unity points a -> b (width w across, depth h along 'up')."""
    a, b = Vector(a), Vector(b); d = b - a; L = d.length; dn = d.normalized()
    upv = Vector(up)
    if abs(dn.dot(upv.normalized())) > .95:
        upv = Vector((1, 0, 0))
    side = dn.cross(upv).normalized(); upv = side.cross(dn).normalized()
    # rotation matrix columns: local X = side (w), local Y = up (h), local Z = along (L)
    M = Matrix((side, upv, dn)).transposed()
    # build directly instead of via Euler (avoid convention mistakes)
    r = random.Random(seed if seed is not None else hash((name, tuple(a))) & 0xffff)
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    uvl = bm.loops.layers.uv.new("UVMap"); off = (r.random() * 5, r.random() * 5)
    bm.normal_update()
    for f in bm.faces:
        n = f.normal; ax = max(range(3), key=lambda i: abs(n[i]))
        for lp in f.loops:
            co = lp.vert.co
            if ax == 2:
                u, v = co.x * w, co.y * h
            else:
                u, v = (co.y * h if ax == 0 else co.x * w), co.z * L
            lp[uvl].uv = (u + off[0], v + off[1])
    for v in bm.verts:
        v.co = M @ Vector((v.co.x * w, v.co.y * h, v.co.z * L)) + (a + b) / 2
    wg.to_blender(bm)
    ob = wg.mesh_obj(name, bm, material)
    wg.finish(ob, bevel, 1, uv=False)
    return ob


def col(name, center, size, rot=(0, 0, 0)):
    return box("COL_" + name, center, size, "WG_Collider", 0, rot=rot)


def bag(name, pos, yaw=0.0, seed=1, scale=1.0, tilt=(0.0, 0.0)):
    """One sandbag (the West Gate bag mesh) at a Unity position, yaw in degrees (bag length along local x)."""
    bm = wg.bag_bm(seed)
    bmesh.ops.scale(bm, vec=(scale, scale, scale), verts=bm.verts)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(tilt[0], 3, "X") @ Matrix.Rotation(tilt[1], 3, "Y"))
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(-yaw) + math.pi, 3, "Z"))
    bmesh.ops.translate(bm, vec=U(*pos), verts=bm.verts)
    ob = wg.mesh_obj(name, bm, "WG_Hessian"); wg.box_uv(ob)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def finish_asset(name, parts, lod1=0.4, note="", cols=()):
    """Join visual parts into <name>_LOD0 (+ a decimated LOD1) and export with the COL_ boxes and empties."""
    vis = [p for p in parts if p and p.type == "MESH" and not p.name.startswith("COL_")]
    ob = join(name, vis)
    if lod1:
        wg.with_lod(ob, (lod1,))
    else:
        ob.name = ob.data.name = name + "_LOD0"
    wg.export(name, note)


def cells(name, seed, area=(1.4, 1.0), count=46):
    """Spent nano cells (steel, cyan band) and a few brass cases lying on the ground."""
    r = rnd(seed); objs = []
    for i in range(count):
        x = r.gauss(0, area[0] / 4); z = r.gauss(0, area[1] / 4)
        yaw = r.uniform(0, 180)
        brass = r.random() < .25
        L = .022 if brass else .05; rad = .0055 if brass else .008
        a = (x - math.cos(math.radians(yaw)) * L / 2, rad, z + math.sin(math.radians(yaw)) * L / 2)
        b = (x + math.cos(math.radians(yaw)) * L / 2, rad, z - math.sin(math.radians(yaw)) * L / 2)
        objs.append(cyl("Cell", a, b, rad, "TR_Brass" if brass else "TR_CellSteel", 6))
        if not brass:
            m = ((a[0] + b[0]) / 2, rad, (a[2] + b[2]) / 2)
            e = ((a[0] + 3 * b[0]) / 4, rad, (a[2] + 3 * b[2]) / 4)
            objs.append(cyl("Cell band", m, e, rad * 1.04, "TR_CellBand", 6))
    return objs


# ================================================================ firing point
def bay_divider():
    wg.reset(); s = KIT["TR_BayDivider"]["size"]; H = s[1]; D = s[2]
    P = []
    for z in (-D / 2 + .05, D / 2 - .05):
        P.append(tbox("Divider post", (0, (H - .15) / 2, z), (.095, H + .15, .095), seed=int(z * 100) + 7))
    P.append(tbox("Top rail", (0, H - .03, 0), (.07, .06, D), seed=11))
    P.append(tbox("Mid rail", (0, .78, 0), (.06, .07, D - .1), seed=12))
    P.append(tbox("Kick board", (0, .12, 0), (.05, .22, D - .1), "TR_TimberDark", seed=13))
    P.append(box("Screen", (.045, .95, 0), (.018, 1.24, D - .12), "WG_Plywood", .003))
    P.append(box("Screen back", (-.045, .95, 0), (.018, 1.24, D - .12), "WG_Plywood", .003))
    for y in (.4, 1.45):
        for z in (-D / 2 + .05, D / 2 - .05):
            P.append(cyl("Screw", (.056, y, z), (.062, y, z), .008, "WG_RustSteel", 6))
    # scuffed hazard tape along the forward edge (the line end)
    P.append(box("Edge tape", (0, 1.62, D / 2 - .01), (.1, .1, .025), "WG_Hazard", .002))
    # two sandbags weighting the down-range foot, ear defenders hung on a hook at the rear post
    P.append(bag("Foot bag", (.0, .0, D / 2 - .05), 90, seed=7, scale=.9))
    P.append(bag("Foot bag", (.02, .1, D / 2 - .1), 84, seed=9, scale=.8, tilt=(.04, 0)))
    zr = -D / 2 + .05
    P.append(cyl("Hook", (.05, 1.5, zr), (.11, 1.53, zr), .007, "WG_RustSteel", 6))
    for sx in (-1, 1):
        P.append(cyl("Ear cup", (.13 + .0, 1.38, zr + sx * .075), (.13 + .0, 1.38, zr + sx * .03), .042, "WG_OlivePaint", 14))
        P.append(cyl("Ear cushion", (.13, 1.38, zr + sx * .03), (.13, 1.38, zr + sx * .018), .036, "WG_Rubber", 14))
    P.append(tube("Headband", [(.13, 1.38, zr - .075), (.12, 1.5, zr - .07), (.11, 1.535, zr), (.12, 1.5, zr + .07), (.13, 1.38, zr + .075)], .008, "WG_Rubber", 6))
    col("Divider", (0, H / 2, 0), (.14, H, D))
    finish_asset("TR_BayDivider", P, lod1=0, note="bay divider: posts, rails, plywood screens, kick board")


def shooting_bench():
    wg.reset(); s = KIT["TR_ShootingBench"]["size"]; W_, D = s[0], s[2]; top = .95
    P = []
    for x in (-W_ / 2 + .07, W_ / 2 - .07):
        for z in (-D / 2 + .06, D / 2 - .06):
            P.append(tbox("Leg", (x, (top - .05) / 2 - .08, z), (.08, top - .05 + .16, .08), seed=int(x * 50 + z * 90)))
        P.append(tbox("End rail", (x, .32, 0), (.06, .08, D - .1), seed=int(x * 70)))
    for z in (-D / 2 + .08, D / 2 - .08):
        P.append(tbox("Long rail", (0, .32, z), (W_ - .12, .08, .05), seed=int(z * 99)))
        P.append(tbox("Top bearer", (0, top - .08, z), (W_, .07, .06), seed=int(z * 77)))
    for i, z in enumerate((-.18, 0, .18)):
        P.append(tbox("Top plank", (0, top - .02, z * (D / .56)), (W_ + .04, .045, .17 * (D / .56)), seed=40 + i))
    P.append(tbox("Front apron", (0, top - .13, D / 2 + .012), (W_, .14, .025), seed=51))
    # sandbag rest (two bags) and a charge-cell case
    P.append(bag("Rest bag", (.05, top + .005, .05), 0, seed=2, scale=.92))
    P.append(bag("Rest bag", (.05, top + .092, .08), 6, seed=4, scale=.8, tilt=(.05, 0)))
    P.append(box("Cell case", (-.45, top + .085, -.05), (.34, .16, .22), "WG_OlivePaint", .012))
    P.append(box("Cell case lid", (-.45, top + .17, -.05), (.345, .025, .225), "WG_OlivePaint", .006))
    P.append(box("Cell case latch", (-.45, top + .14, .062), (.05, .04, .012), "WG_RustSteel", .002))
    cs = cells("Bench cells", 5, (.4, .25), 7)
    for o in cs:
        o.location += U(.42, top + .003, -.08) - U(0, 0, 0)
    P.extend(cs)
    col("Bench", (0, top / 2, 0), (W_, top, D))
    finish_asset("TR_ShootingBench", P, lod1=.45, note="timber shooting bench with sandbag rest and charge-cell case")


def lane_board(n):
    wg.reset()
    P = []
    # 1 Oct review: below eye height (a 1.9 m post put the boards in the shooter's view down range)
    P.append(tbox("Board post", (0, .45, -.05), (.07, 1.15, .07), seed=n))
    P.append(tbox("Board", (0, .98, 0), (.32, .32, .03), "TR_TimberDark", seed=10 + n))
    u0 = (n - 1) * .25
    P.append(quad("Lane number", (0, .98, .0155), .28, .28, "TR_LaneNumbers", facing=(0, 0, 1), uv_rect=(u0, 0, u0 + .25, 1)))
    for x in (-.11, .11):
        P.append(cyl("Bolt", (x, .98, .015), (x, .98, .022), .008, "WG_RustSteel", 6))
    col("Post", (0, .56, -.05), (.08, 1.12, .08))
    finish_asset(f"TR_LaneBoard_{n}", P, lod1=0, note=f"lane {n} number board on a post")


def distance_marker(n):
    """Distance post: a 1.15 m timber stake with a bone-painted steel plate (TR_DistanceNumbers atlas cell n)."""
    wg.reset()
    P = [tbox("Marker post", (0, .42, -.03), (.08, 1.4, .08), seed=70 + n)]
    P.append(box("Marker plate", (0, .98, .02), (.38, .26, .008), "WG_RustSteel", .002))
    u0 = (n - 1) * .25
    P.append(quad("Marker number", (0, .98, .0245), .37, .245, "TR_DistanceNumbers", facing=(0, 0, 1), uv_rect=(u0, 0, u0 + .25, 1)))
    for x in (-.15, .15):
        P.append(cyl("Bolt", (x, .98, .024), (x, .98, .03), .008, "WG_RustSteel", 6))
    P.append(box("Post cap", (0, 1.125, -.03), (.09, .02, .09), "WG_RustSteel", .002))
    col("Post", (0, .55, 0), (.4, 1.1, .1))
    finish_asset(f"TR_DistanceMarker_{n}", P, lod1=0, note=f"distance post, plate {(5, 10, 15, 20)[n - 1]} M")


def rules_board():
    wg.reset()
    P = []
    for x in (-.68, .68):
        P.append(tbox("Board post", (x, .95, -.04), (.09, 2.3, .09), seed=int(x * 10) + 3))
    P.append(box("Board backing", (0, 1.52, 0), (1.46, 1.0, .03), "WG_Plywood", .004))
    P.append(quad("Orders", (0, 1.52, .0165), 1.4, .95, "TR_RangeOrders", facing=(0, 0, 1)))
    for y in (1.0, 2.04):
        P.append(tbox("Board frame", (0, y, .01), (1.52, .05, .05), "TR_TimberDark", seed=int(y * 10)))
    P.append(box("Drip cap", (0, 2.12, .08), (1.66, .025, .32), "WG_OlivePaint", .004, rot=(12, 0, 0)))
    for x, y in ((-.66, 1.95), (.66, 1.95), (-.66, 1.08), (.66, 1.08)):
        P.append(cyl("Bolt", (x, y, .018), (x, y, .026), .01, "WG_RustSteel", 6))
    col("Board", (0, 1.1, 0), (1.5, 2.2, .14))
    finish_asset("TR_RulesBoard", P, lod1=0, note="RANGE ORDERS board on timber posts")


def range_table():
    wg.reset(); s = KIT["TR_RangeTable"]["size"]; W_, D = s[0], s[2]; top = .78
    P = []
    P.append(box("Table top", (0, top - .015, 0), (W_, .03, D), "WG_Plywood", .004))
    for z in (-D / 2 + .02, D / 2 - .02):
        P.append(tbox("Top rim", (0, top - .05, z), (W_ - .04, .06, .03), seed=int(z * 50) + 5))
    for x in (-W_ / 2 + .18, W_ / 2 - .18):
        for sgn in (-1, 1):
            P.append(beam("Trestle leg", (x, 0, sgn * .28), (x, top - .06, sgn * .08), .035, .035, "WG_RustSteel", bevel=.003))
        P.append(beam("Trestle bar", (x, top - .07, -.3), (x, top - .07, .3), .035, .035, "WG_RustSteel", bevel=.003))
        P.append(beam("Trestle brace", (x, .25, -.22), (x, .25, .22), .02, .02, "WG_RustSteel", bevel=.002))
    col("Table", (0, top / 2, 0), (W_, top, D))
    finish_asset("TR_RangeTable", P, lod1=0, note="range officer's trestle table")


def lantern():
    """Field lantern for the range officer's table: steel base and cap, glass chimney round a glowing mantle, wire
    guard, bail handle (the officer's lamp light sits on it)."""
    wg.reset()
    P = [cyl("Lantern base", (0, 0, 0), (0, .07, 0), .075, "WG_OlivePaint", 18),
         cyl("Lantern base rim", (0, .068, 0), (0, .078, 0), .07, "WG_RustSteel", 18),
         cyl("Lantern glass", (0, .078, 0), (0, .2, 0), .052, "TR_LanternGlass", 18),
         cyl("Lantern mantle", (0, .1, 0), (0, .17, 0), .018, "TR_LampGlow", 10),
         cyl("Lantern cap", (0, .2, 0), (0, .225, 0), .066, "WG_OlivePaint", 18),
         cyl("Lantern vent", (0, .225, 0), (0, .25, 0), .03, "WG_RustSteel", 12)]
    for i in range(4):
        a = i * math.pi / 2 + .4
        P.append(cyl("Guard wire", (math.cos(a) * .062, .078, math.sin(a) * .062), (math.cos(a) * .062, .2, math.sin(a) * .062), .003, "WG_RustSteel", 5))
    P.append(tube("Bail", [(-.068, .21, 0), (-.05, .3, 0), (0, .33, 0), (.05, .3, 0), (.068, .21, 0)], .004, "WG_RustSteel", 5))
    P.append(cyl("Fuel knob", (.07, .04, 0), (.09, .04, 0), .012, "WG_RustSteel", 8))
    empty("LIGHT_lantern", (0, .14, 0))
    finish_asset("TR_Lantern", P, lod1=0, note="field lantern (range officer's table)")


def range_lamp():
    wg.reset()
    P = [cyl("Lamp base", (0, 0, .07), (0, .06, .07), .06, "WG_RustSteel", 12),
         cyl("Lamp lens", (0, .06, .07), (0, .2, .07), .05, "TR_RedLens", 14),
         cyl("Lamp cap", (0, .2, .07), (0, .23, .07), .055, "WG_RustSteel", 12),
         box("Clamp", (0, .03, .02), (.08, .06, .07), "WG_RustSteel", .004),
         tube("Lamp cable", [(0, .01, .0), (0, -.5, -.01), (.0, -1.6, -.02)], .006, "WG_Rubber", 5)]
    empty("LIGHT_lamp", (0, .13, .07))
    finish_asset("TR_RangeLamp", P, lod1=0, note="red range-live lamp clamped to a flag pole")


def flood_pole():
    wg.reset()
    P = [cyl("Pole", (0, -.6, 0), (0, 5.6, 0), .11, "TR_TimberDark", 12)]
    P.append(tbox("Cross arm", (0, 5.25, .1), (1.0, .1, .1), seed=5))
    for x, yaw in ((-.4, -8), (.4, 30)):
        R = wg.urot(20, yaw, 0)
        c = Vector((x, 5.12, .2))
        P.append(box("Flood housing", tuple(c), (.36, .26, .16), "WG_RustSteel", .012, rot=(20, yaw, 0)))
        lens = c + R @ Vector((0, 0, .085))
        P.append(box("Flood lens", tuple(lens), (.31, .21, .015), "WG_LampLens", 0, rot=(20, yaw, 0)))
        P.append(box("Flood yoke", (x, 5.2, .12), (.04, .12, .06), "WG_RustSteel", .003))
        empty("LIGHT_flood", tuple(lens + R @ Vector((0, 0, .05))), (20, yaw, 0))
    P.append(box("Junction box", (0, 1.35, .14), (.26, .34, .14), "WG_OlivePaint", .01))
    P.append(tube("Pole cable", [(0, 1.5, .13), (.02, 3.5, .12), (.0, 5.1, .12), (.2, 5.18, .16)], .012, "WG_Rubber", 6))
    P.append(tube("Feed cable", [(0, 1.2, .13), (.05, .3, .14), (.3, .02, .5), (.8, .02, 1.6)], .012, "WG_Rubber", 6))
    for i in range(6):
        P.append(cyl("Climb step", (-.11, 2.2 + i * .45, 0), (-.25, 2.2 + i * .45, 0), .012, "WG_RustSteel", 6))
    col("Pole", (0, 2.8, 0), (.24, 5.6, .24))
    finish_asset("TR_FloodPole", P, lod1=0, note="timber flood pole: two lamps on a cross arm, junction box")


# ================================================================ machine lane
def lane_gate():
    wg.reset(); s = KIT["TR_LaneGate"]["size"]; hw = s[0] / 2 - .1
    P = []
    for x in (-hw, hw):
        P.append(tbox("Gate post", (x, (2.35 - .5) / 2, 0), (.15, 2.35 + .5, .15), seed=int(x * 10) + 20))
        for k in range(4):
            P.append(bag("Post bag", (x + (k % 2 - .5) * .42, .0 + (k // 2) * .13, (k % 2) * .2 - .1), 90 * (k % 2) + 10 * k, seed=k + 3))
    P.append(tbox("Cross beam", (0, 2.25, 0), (2 * hw + .3, .14, .12), seed=33))
    for x in (-.55, .55):
        P.append(tube("Sign chain", [(x, 2.18, .05), (x, 1.95, .05)], .008, "WG_RustSteel", 5))
    P.append(box("Sign board", (0, 1.72, .05), (1.3, .46, .03), "WG_Plywood", .004))
    P.append(quad("Sign face", (0, 1.72, .033), 1.26, .42, "TR_LaneSign", facing=(0, 0, -1)))
    P.append(quad("Sign face back", (0, 1.72, .067), 1.26, .42, "TR_LaneSign", facing=(0, 0, 1)))
    for x in (-hw, hw):
        col("Post" + ("L" if x < 0 else "R"), (x, 1.1, 0), (.16, 2.3, .16))
    finish_asset("TR_LaneGate", P, lod1=.5, note="machine lane start frame with LANE 4 board")


def cover_barricade():
    wg.reset(); s = KIT["TR_CoverBarricade"]["size"]; W_ = s[0]; H = 1.25
    r = rnd(71); P = []
    for x in (-W_ / 2 + .08, 0, W_ / 2 - .08):
        P.append(tbox("Barricade post", (x, (H - .4) / 2, -.02), (.12, H + .4, .12), seed=int(x * 10) + 60))
        # rear brace to a ground stake
        P.append(beam("Rear brace", (x, H * .75, -.08), (x, .0, -.62), .07, .05, seed=int(x * 10) + 61))
    for i in range(6):
        y = .12 + i * .205
        if i == 4:           # one plank shot through and missing its right end
            P.append(tbox("Plank (broken)", (-.18, y, .08), (W_ - .45, .19, .045), seed=80 + i, rot=(0, 0, r.uniform(-1, 1))))
            P.append(tbox("Splinter", (.46, y + .04, .085), (.18, .06, .03), seed=90, rot=(0, 0, 18)))
            continue
        P.append(tbox("Plank", (r.uniform(-.03, .03), y, .08), (W_ + r.uniform(0, .08), .19, .045), seed=80 + i, rot=(0, 0, r.uniform(-.8, .8))))
    for k in range(4):
        P.append(bag("Foot bag", (-.6 + k * .4, .0, .3), r.uniform(-8, 8), seed=k + 11))
    P.append(bag("Foot bag", (-.35, .12, .31), 4, seed=5))
    col("Barricade", (0, H / 2, .02), (W_, H, .3))
    finish_asset("TR_CoverBarricade", P, lod1=.45, note="timber cover barricade with sandbag foot and rear braces")


def tether_gantry():
    wg.reset(); P = []
    hx = 1.3
    for x in (-hx, hx):
        P.append(box("Gantry post", (x, 1.7, 0), (.12, 3.4, .12), "WG_OlivePaint", .008))
        P.append(box("Post hazard band", (x, .6, 0), (.125, .6, .125), "WG_Hazard", .006))
        P.append(box("Base plate", (x, .015, 0), (.35, .03, .35), "WG_RustSteel", .004))
        P.append(box("Footing", (x, -.25, 0), (.45, .5, .45), "WG_Concrete", .02))
        for dz in (-1, 1):
            P.append(beam("Knee brace", (x, .02, dz * .45), (x, 1.1, dz * .04), .05, .05, "WG_RustSteel", bevel=.003))
    P.append(wg.ibeam("Gantry beam", (-hx - .15, 3.36, 0), (hx + .15, 3.36, 0), .16, .1, .012, .014, "WG_OlivePaint"))
    for x in (-hx, hx):
        P.append(beam("Beam knee", (x, 2.7, 0), (x * .6, 3.28, 0), .06, .06, "WG_RustSteel", bevel=.003))
    P.append(box("Cable trolley", (.0, 3.2, 0), (.24, .12, .16), "WG_RustSteel", .01))
    P.append(cyl("Tether cable", (0, 3.14, 0), (0, 2.16, 0), .006, "WG_Rubber", 6))
    P.append(cyl("Tether hook", (0, 2.2, 0), (0, 2.12, 0), .02, "WG_RustSteel", 8))
    P.append(box("Winch", (-hx, 1.25, .12), (.24, .3, .18), "WG_OlivePaint", .01))
    P.append(tube("Winch line", [(-hx + .05, 1.4, .12), (-hx + .05, 3.2, .05), (0, 3.25, .0)], .005, "WG_Rubber", 5))
    for x in (-hx, hx):
        col("Post" + ("L" if x < 0 else "R"), (x, 1.7, 0), (.14, 3.4, .14))
    finish_asset("TR_TetherGantry", P, lod1=.5, note="steel tether gantry for a training drone")


def droid_frame():
    """Goal-post target frame straddling a stripped worker droid (its combat-stance stride is 1.5 m deep): a steel base
    plate weighted with sandbags, two braced olive uprights, an I-beam overhead and chains down to the shoulders."""
    wg.reset(); P = []
    P.append(box("Base plate", (0, .025, 0), (1.9, .05, 1.8), "WG_PlateSteel", .008))
    for x in (-.88, .88):
        P.append(box("Upright", (x, 1.22, 0), (.1, 2.4, .1), "WG_OlivePaint", .008))
        P.append(box("Upright foot", (x, .06, 0), (.26, .025, .26), "WG_RustSteel", .004))
        for dz in (-1, 1):
            P.append(beam("Upright brace", (x, .07, dz * .78), (x, 1.05, dz * .05), .06, .06, "WG_RustSteel", bevel=.003))
        P.append(box("Hazard band", (x, .55, 0), (.105, .45, .105), "WG_Hazard", .004))
    P.append(wg.ibeam("Frame beam", (-.98, 2.4, 0), (.98, 2.4, 0), .14, .09, .01, .012, "WG_OlivePaint"))
    for x in (-.24, .24):
        P.append(tube("Chain", [(x, 2.33, 0), (x * 1.1, 1.8, .03), (x * 1.25, 1.36, .06)], .013, "WG_RustSteel", 6))
        P.append(cyl("Shackle", (x * 1.25, 1.38, .06), (x * 1.25, 1.31, .06), .025, "WG_RustSteel", 8))
    for k, (x, z) in enumerate(((-.75, .7), (.72, .72), (-.74, -.7), (.75, -.66))):
        P.append(bag("Weight bag", (x, .05, z), 90 + k * 25, seed=k + 21))
    col("UprightL", (-.88, 1.2, 0), (.12, 2.4, .12)); col("UprightR", (.88, 1.2, 0), (.12, 2.4, .12))
    col("Plate", (0, .025, 0), (1.9, .05, 1.8))
    finish_asset("TR_DroidFrame", P, lod1=.5, note="goal-post frame holding a stripped worker droid as a target")


# ================================================================ service apron
def drone_dock():
    wg.reset(); P = []
    for x in (-.4, .4):
        for z in (-.4, .4):
            P.append(box("Dock leg", (x, .4, z), (.06, .8, .06), "WG_OlivePaint", .006))
            P.append(box("Leg foot", (x, .01, z), (.16, .02, .16), "WG_RustSteel", .003))
    for z in (-.4, .4):
        P.append(box("Top rail", (0, .8, z), (.86, .06, .06), "WG_OlivePaint", .006))
        P.append(box("Low rail", (0, .25, z), (.8, .04, .04), "WG_RustSteel", .004))
    for x in (-.4, .4):
        P.append(box("Top rail", (x, .8, 0), (.06, .06, .86), "WG_OlivePaint", .006))
    P.append(cyl("Landing plate", (0, .83, 0), (0, .86, 0), .45, "WG_PlateSteel", 28))
    # cyan charge ring: thin annulus of segments
    for i in range(16):
        a0 = i * math.tau / 16; a1 = (i + 1) * math.tau / 16; am = (a0 + a1) / 2
        P.append(box("Charge ring", (math.cos(am) * .36, .865, math.sin(am) * .36), (.045, .012, .36 * (a1 - a0) + .01), "TR_ChargeGlow", 0, rot=(0, -math.degrees(am), 0)))
    for i in range(3):
        a = i * math.tau / 3 + .5
        P.append(cyl("Locating pin", (math.cos(a) * .28, .86, math.sin(a) * .28), (math.cos(a) * .28, .92, math.sin(a) * .28), .018, "WG_RustSteel", 8))
    P.append(box("Status box", (.0, .6, -.45), (.24, .22, .1), "WG_OlivePaint", .01))
    P.append(cyl("Status lamp", (.07, .64, -.5), (.07, .64, -.515), .018, "TR_ChargeGlow", 10))
    P.append(tube("Dock conduit", [(0, .5, -.47), (0, .1, -.5), (0, .02, -.7)], .016, "WG_Rubber", 6))
    col("Dock", (0, .44, 0), (.9, .88, .9))
    finish_asset("TR_DroneDock", P, lod1=.5, note="drone dock: steel stand, landing plate, cyan charge ring, status box")


def repair_bench():
    wg.reset(); s = KIT["TR_RepairBench"]["size"]; W_, D = s[0], s[2]; top = .9
    r = rnd(33); P = []
    for x in (-W_ / 2 + .06, W_ / 2 - .06):
        for z in (-D / 2 + .06, D / 2 - .06):
            P.append(box("Bench leg", (x, (top - .08) / 2, z), (.06, top - .08, .06), "WG_OlivePaint", .005))
        P.append(box("Leg rail", (x, .22, 0), (.05, .05, D - .1), "WG_RustSteel", .004))
    for i in range(4):
        P.append(tbox("Bench top", (0, top - .035, -D / 2 + .11 + i * .225), (W_, .07, .22), "TR_TimberDark", seed=100 + i))
    P.append(box("Shelf", (0, .26, 0), (W_ - .12, .025, D - .12), "WG_Plywood", .003))
    # tool board on the back edge
    for x in (-W_ / 2 + .1, W_ / 2 - .1):
        P.append(tbox("Board post", (x, 1.3, -D / 2 + .04), (.06, .85, .05), seed=int(x * 10) + 110))
    P.append(box("Tool board", (0, 1.34, -D / 2 + .035), (W_ - .1, .72, .02), "WG_OlivePaint", .003))
    for k in range(7):
        x = -.85 + k * .28 + r.uniform(-.03, .03)
        L = r.uniform(.16, .3)
        P.append(box("Hung tool", (x, 1.42 - L / 2, -D / 2 + .06), (.03, L, .012), "WG_RustSteel", .002, rot=(0, 0, r.uniform(-6, 6))))
        P.append(cyl("Peg", (x, 1.44, -D / 2 + .045), (x, 1.44, -D / 2 + .075), .006, "WG_RustSteel", 5))
    # parts on the shelf: a coiled cable, plates, a case
    bpy.ops.mesh.primitive_torus_add(major_radius=.16, minor_radius=.025, major_segments=20, minor_segments=6)
    t = bpy.context.active_object; t.name = "Cable coil"; t.location = U(-.55, .3, .05); t.data.materials.append(mat("WG_Rubber"))
    wg.finish(t, 0, uv=True); P.append(t)
    P.append(box("Spare plate", (.2, .29, .1), (.5, .02, .35), "WG_PlateSteel", .003, rot=(0, 12, 0)))
    P.append(box("Spare plate", (.25, .31, .08), (.4, .02, .3), "WG_RustSteel", .003, rot=(0, -8, 0)))
    P.append(box("Parts case", (.72, .36, 0), (.36, .18, .3), "WG_OlivePaint", .01))
    # on top: a stripped drone optic, a wired cell pack, loose screws
    P.append(cyl("Optic housing", (-.1, top, .15), (-.1, top + .12, .15), .09, "WG_RustSteel", 16))
    P.append(cyl("Optic lens", (-.1, top + .12, .15), (-.1, top + .13, .15), .07, "WG_LampLens", 16))
    P.append(box("Cell pack", (.35, top + .05, .18), (.26, .1, .14), "WG_OlivePaint", .008))
    P.append(tube("Test leads", [(.35, top + .1, .12), (.15, top + .04, .05), (-.02, top + .01, .12)], .005, "TR_RedLead", 5))
    col("Bench", (0, top / 2, 0), (W_, top, D))
    finish_asset("TR_RepairBench", P, lod1=.45, note="repair bench: timber top, steel frame, tool board, parts")


def blast_wall():
    wg.reset(); s = KIT["TR_BlastWall"]["size"]; L = s[0]; H = 1.05; T = .55
    r = rnd(55); P = []
    n = 5
    for i in range(n):
        x = -L / 2 + .06 + i * (L - .12) / (n - 1)
        for z in (-T / 2, T / 2):
            P.append(tbox("Crib post", (x, (H - .3) / 2, z), (.12, H + .3, .12), seed=i * 3 + int(z * 10) + 200))
    for z in (-T / 2 - .07, T / 2 + .07):
        for k in range(5):
            y = .1 + k * .205
            P.append(tbox("Crib plank", (r.uniform(-.04, .04), y, z), (L + r.uniform(-.05, .05), .19, .04), "TR_TimberDark" if k % 3 == 0 else "TR_Timber", seed=210 + k + int(z * 10)))
    for i in range(int(L / .46)):
        P.append(bag("Cap bag", (-L / 2 + .25 + i * .46, H + .02, r.uniform(-.03, .03)), 0 + r.uniform(-6, 6), seed=i + 31))
    col("Wall", (0, (H + .2) / 2, 0), (L, H + .2, T + .2))
    finish_asset("TR_BlastWall", P, lod1=.4, note="timber crib blast wall filled with sand, sandbag cap")


def service_shelter():
    wg.reset(); s = KIT["TR_ServiceShelter"]["size"]; W_, D = s[0] - .2, s[2] - .2
    Hf, Hb = 2.75, 2.5
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=32, y_subdivisions=26, size=1)
    cloth = bpy.context.active_object; cloth.name = "Shade cloth"
    cloth.scale = (W_, D, 1); bpy.ops.object.transform_apply(scale=True)
    for v in cloth.data.vertices:
        uz = -v.co.y                    # Unity z (-D/2..D/2)
        v.co.z = Hb + (uz + D / 2) / D * (Hf - Hb)
    vg = cloth.vertex_groups.new(name="pin")
    pins = [v.index for v in cloth.data.vertices if (abs(abs(v.co.x) - W_ / 2) < .02 and abs(abs(v.co.y) - D / 2) < .02) or
            (abs(abs(v.co.y) - D / 2) < .02 and abs(v.co.x) < .05) or (abs(abs(v.co.x) - W_ / 2) < .02 and abs(v.co.y) < .05)]
    vg.add(pins, 1.0, "REPLACE")
    m = cloth.modifiers.new("Cloth", "CLOTH"); st = m.settings
    st.vertex_group_mass = "pin"; st.quality = 8; st.mass = .25; st.tension_stiffness = 14; st.compression_stiffness = 14; st.shear_stiffness = 6; st.bending_stiffness = .3
    bpy.context.scene.frame_start = 1; bpy.context.scene.frame_end = 40; m.point_cache.frame_end = 40
    for f in range(1, 41):
        bpy.context.scene.frame_set(f)
    bpy.context.view_layer.objects.active = cloth
    bpy.ops.object.modifier_apply(modifier="Cloth")
    cloth.data.materials.append(mat("WG_ShadeCloth"))
    sol = cloth.modifiers.new("sol", "SOLIDIFY"); sol.thickness = .006
    bpy.ops.object.modifier_apply(modifier="sol")
    wg.box_uv(cloth, scale=1.0)
    for p in cloth.data.polygons:
        p.use_smooth = True
    P = [cloth]
    for x in (-W_ / 2, W_ / 2):
        for z, h in ((-D / 2, Hb), (D / 2, Hf)):
            P.append(cyl("Shelter pole", (x, -.3, z), (x, h + .03, z), .04, "WG_RustSteel", 10))
            P.append(box("Pole foot", (x, .02, z), (.26, .04, .26), "WG_RustSteel", .004))
            sx = 1 if x > 0 else -1; sz = 1 if z > 0 else -1
            P.append(tube("Guy line", [(x, h - .05, z), (x + sx * .6, 0, z + sz * .9)], .004, "WG_Rubber", 4))
            P.append(cyl("Guy peg", (x + sx * .6, -.2, z + sz * .9), (x + sx * .6, .06, z + sz * .9), .012, "WG_RustSteel", 6))
    for z, h in ((-D / 2, Hb), (D / 2, Hf)):
        P.append(cyl("Edge batten", (-W_ / 2, h, z), (W_ / 2, h, z), .022, "WG_RustSteel", 8))
    P.append(tube("Lamp cable", [(-W_ / 2, Hf - .05, D / 2), (-W_ / 4, Hf - .15, D / 4), (0, (Hf + Hb) / 2 - .12, 0)], .008, "WG_Rubber", 5))
    for x in (-W_ / 2, W_ / 2):
        for z, h in ((-D / 2, Hb), (D / 2, Hf)):
            col("Pole" + str(int(x * 10)) + str(int(z * 10)), (x, h / 2, z), (.1, h, .1))
    finish_asset("TR_ServiceShelter", P, lod1=.4, note="free-standing shade shelter over the drone docks")


def timber_stack():
    wg.reset(); r = rnd(91); P = []
    for x in (-.8, .8):
        P.append(tbox("Bearer", (x, .05, 0), (.12, .1, .8), "TR_TimberDark", seed=int(x * 10) + 300))
    for k, (y, n) in enumerate(((.17, 3), (.31, 2))):
        for i in range(n):
            z = (i - (n - 1) / 2) * .25 + r.uniform(-.02, .02)
            P.append(tbox("Spare sleeper", (r.uniform(-.06, .06), y, z), (2.4, .13, .22), "TR_TimberDark" if (i + k) % 2 else "TR_Timber", seed=310 + k * 5 + i, rot=(0, r.uniform(-2, 2), 0)))
    P.append(box("Strap", (.3, .2, 0), (.03, .34, .82), "WG_Rubber", .003))
    col("Stack", (0, .2, 0), (2.4, .4, .75))
    finish_asset("TR_TimberStack", P, lod1=0, note="spare revetment sleepers")


def spent_cells():
    for v in (1, 2, 3):
        wg.reset()
        finish_asset(f"TR_SpentCells_{v}", cells("Spent cells", 400 + v), lod1=0, note="spent nano cells and brass cases on the ground")


# ================================================================ backstop revetment (path, world space)
def revetment():
    wg.reset()
    toe = [Vector(p) for p in LAYOUT["revetment"]["toe"]]           # Unity world (x, y ground, z)
    origin = toe[0].copy()
    H = LAYOUT["berm"]["wallHeight"]; r = rnd(20261001)
    # resample the toe polyline at ~1.5 m post spacing
    segs = [(toe[i], toe[i + 1]) for i in range(len(toe) - 1)]
    total = sum((b - a).length for a, b in segs)
    npost = max(2, int(round(total / 1.5)) + 1)
    def at(s):
        acc = 0
        for a, b in segs:
            L = (b - a).length
            if s <= acc + L + 1e-6:
                t = (s - acc) / L; p = a.lerp(b, t); d = (b - a).normalized(); return p, d
            acc += L
        return segs[-1][1], (segs[-1][1] - segs[-1][0]).normalized()
    posts = []; post_ground = []
    for i in range(npost):
        p, d = at(total * i / (npost - 1))
        # p.y is the smoothed wall base level from layout.json (the wall top runs level bay to bay); posts are buried
        # to the local ground, whichever is lower
        g = min(GR.ground(p.x + dx, p.z + dz) for dx, dz in ((0, 0), (.2, 0), (-.2, 0), (0, .2), (0, -.2)))
        posts.append((Vector((p.x, p.y, p.z)), d))
        post_ground.append(g)
    P = []
    def rel(v):
        return (v.x - origin.x, v.y - origin.y, v.z - origin.z)
    face_side = lambda d: Vector((-d.z, 0, d.x))     # left of the path direction = toward the firing line? checked below
    # the wall faces the firing line: pick the side whose normal points toward F
    Fp = Vector((GR.F[0], 0, GR.F[1]))
    mid, dmid = at(total / 2)
    nrm = face_side(dmid)
    if nrm.dot(Fp - Vector((mid.x, 0, mid.z))) < 0:
        face_side = lambda d: Vector((d.z, 0, -d.x))
    # posts (in front) and sleepers (behind the posts, against the earth)
    for i, (p, d) in enumerate(posts):
        n = face_side(d)
        top = p.y + H + .06 + r.uniform(-.03, .03)
        base = min(p.y, post_ground[i]) - .55
        c = p + n * .02
        P.append(tbox("Revetment post", rel(Vector((c.x, (top + base) / 2, c.z))), (.2, top - base, .2), "TR_TimberDark", seed=500 + i,
                      rot=(0, math.degrees(math.atan2(d.x, d.z)), 0)))
        P.append(box("Post cap", rel(Vector((c.x, top + .01, c.z))), (.22, .02, .22), "WG_RustSteel", .003, rot=(0, math.degrees(math.atan2(d.x, d.z)), 0)))
    scar_lats = LAYOUT["revetment"]["scarLats"]
    scar_pts = []
    for n_, lat in scar_lats:
        # the toe point closest to this lateral offset
        best = min(range(200), key=lambda k: abs(GR.L(*[(at(total * k / 199)[0].x), (at(total * k / 199)[0].z)])[1] - lat))
        scar_pts.append((n_, total * best / 199))
    for i in range(npost - 1):
        (p0, d0), (p1, d1) = posts[i], posts[i + 1]
        d = (p1 - p0); d.y = 0; d = d.normalized(); n = face_side(d)
        base = min(p0.y, p1.y, post_ground[i], post_ground[i + 1]) - .12
        s_mid = total * (i + .5) / (npost - 1)
        near_scar = min((abs(s_mid - s) for _, s in scar_pts), default=99)
        k = 0; y = base
        while y < p0.y + H - .02:
            h = .215 + r.uniform(-.01, .01)
            a = p0 - n * .15 + d * .02; b = p1 - n * .15 - d * .02
            mat_ = "TR_TimberFresh" if (i % 5 == 3 and k in (3, 4)) else ("TR_Timber" if r.random() < .45 else "TR_TimberDark")
            sag = r.uniform(-.0015, .0015)
            if near_scar < 1.0 and k in (3, 4, 5) and r.random() < .7:
                # shot-up sleeper: two shorter pieces with a ragged gap showing the sand behind
                cut = r.uniform(.35, .65); gap = r.uniform(.08, .16)
                for (u0, u1) in ((0, cut - gap / 2), (cut + gap / 2, 1)):
                    A = a.lerp(b, u0); B = a.lerp(b, u1)
                    P.append(beam("Sleeper (shot)", rel(Vector((A.x, y + h / 2 + sag, A.z))), rel(Vector((B.x, y + h / 2 + sag, B.z))), .14, h - .004, mat_, bevel=.008, seed=600 + i * 20 + k))
                G = a.lerp(b, cut)
                P.append(box("Sand in gap", rel(Vector((G.x - n.x * .1, y + h / 2, G.z - n.z * .1))), (gap + .1, h, .1), "TR_SandFill", .02))
            else:
                P.append(beam("Sleeper", rel(Vector((a.x, y + h / 2 + sag, a.z))), rel(Vector((b.x, y + h / 2 + sag, b.z))), .14, h - .004, mat_, bevel=.008, seed=600 + i * 20 + k))
            y += h; k += 1
    # sandbag cap on the earth just behind the wall top: two courses along the path
    capH = H
    for c_ in range(2):
        s = .25 + (.23 if c_ else 0)
        while s < total - .2:
            p, d = at(s); n = face_side(d)
            g = min(posts, key=lambda q: (q[0] - p).length)[0].y
            q = p - n * (.32 + c_ * .06)
            P.append(bag("Cap bag", rel(Vector((q.x, g + capH - .02 + c_ * .115, q.z))), math.degrees(math.atan2(d.z, d.x)) + r.uniform(-5, 5), seed=int(s * 10) % 6 + c_))
            s += .46
    # painted lane numbers on the sleepers behind each target (paint over the timber)
    spacing = total / (npost - 1)
    for n_, s in scar_pts:
        s = (math.floor(s / spacing) + .5) * spacing           # centre of the bay, clear of the posts
        p, d = at(s); n = face_side(d)
        g = min(posts, key=lambda q: (q[0] - p).length)[0].y
        c = p - n * .074 + Vector((0, g - p.y, 0))               # on the sleeper face (sleepers: d .08-.22 behind the toe)
        u0 = (n_ - 1) * .25
        yaw_face = Vector((n.x, 0, n.z))
        q = quad("Painted lane number", rel(Vector((c.x, g + 1.5, c.z))), .66, .66, "TR_LaneNumbersPaint", facing=tuple(yaw_face), uv_rect=(u0, 0, u0 + .25, 1))
        P.append(q)
    # collision: one strip along the path (Unity makes a MeshCollider from COL_Revetment)
    bm = bmesh.new()
    vs = []
    for (p, d) in posts:
        n = face_side(d)
        for off, y in ((n * .12, p.y - .3), (n * .12, p.y + H + .1), (-n * .5, p.y + H + .1), (-n * .5, p.y - .3)):
            v = p + off; vs.append(bm.verts.new(U(*rel(Vector((v.x, y, v.z))))))
    for i in range(len(posts) - 1):
        for k in range(4):
            a0, a1 = vs[i * 4 + k], vs[i * 4 + (k + 1) % 4]
            b0, b1 = vs[(i + 1) * 4 + k], vs[(i + 1) * 4 + (k + 1) % 4]
            bm.faces.new((a0, a1, b1, b0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    wg.mesh_obj("COL_Revetment", bm, "WG_Collider")
    finish_asset("TR_Revetment", P, lod1=.35, note=f"backstop revetment: {npost} posts, sleepers, sandbag cap, lane numbers; origin = first toe point {tuple(round(v, 3) for v in origin)}")
    wg.REPORT["TR_Revetment"]["origin"] = [origin.x, origin.y, origin.z]
    wg.REPORT["TR_Revetment"]["scars"] = [[n_, s] for n_, s in scar_pts]


def cables():
    wg.reset(); P = []
    origin = Vector(LAYOUT["cables"][0]["pts"][0])
    for c in LAYOUT["cables"]:
        pts = [Vector(p) - origin for p in c["pts"]]
        P.append(tube(c["name"], [tuple(p) for p in pts], .014, "WG_Rubber", 6))
    finish_asset("TR_Cables", P, lod1=0, note="power cables from the dock generator; origin = first cable point")
    wg.REPORT["TR_Cables"]["origin"] = [origin.x, origin.y, origin.z]


ASSETS = {"TR_BayDivider": bay_divider, "TR_ShootingBench": shooting_bench, "TR_LaneBoard": lambda: [lane_board(n) for n in (1, 2, 3)],
          "TR_RulesBoard": rules_board, "TR_DistanceMarker": lambda: [distance_marker(n) for n in (1, 2, 3)], "TR_RangeTable": range_table, "TR_RangeLamp": range_lamp, "TR_Lantern": lantern, "TR_FloodPole": flood_pole,
          "TR_LaneGate": lane_gate, "TR_CoverBarricade": cover_barricade, "TR_TetherGantry": tether_gantry, "TR_DroidFrame": droid_frame,
          "TR_DroneDock": drone_dock, "TR_RepairBench": repair_bench, "TR_BlastWall": blast_wall, "TR_ServiceShelter": service_shelter,
          "TR_TimberStack": timber_stack, "TR_SpentCells": spent_cells, "TR_Revetment": revetment, "TR_Cables": cables}

if __name__ == "__main__":
    random.seed(20261001)
    only = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for k, fn in ASSETS.items():
        if only and k not in only:
            continue
        fn()
    rp = HERE / "authored-assets.json"
    old = json.loads(rp.read_text()) if rp.exists() else {}
    old.update(wg.REPORT); rp.write_text(json.dumps(old, indent=1))
