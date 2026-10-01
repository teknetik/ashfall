"""Ward hydroponics review renders (Blender, Cycles CPU): the authored interior inside a stand-in quonset skin (ribs,
translucent polycarbonate, end panels with the door) plus a 1.8 m figure, from player-height viewpoints outside and a
few inside views for inspection. Writes review/<view>.png.

Run: $O/blender.sh review_hydroponics.py [-- views=a,b lod=0 samples=24]
"""
import sys, math
from pathlib import Path
import bpy, bmesh
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ARGS = dict(a.split("=") for a in (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []) if "=" in a)
LOD = int(ARGS.get("lod", 0))
bpy.ops.wm.open_mainfile(filepath=str(HERE / "hydroponics-source.blend"))
sc = bpy.context.scene
for o in list(bpy.data.objects):
    keep = (o.name.endswith(f"_LOD{LOD}") and (o.name.startswith("HY_Crops") or o.name.startswith("HY_Fitout"))) or \
           (o.name.startswith("HY_") and not o.name.startswith(("HY_Crops", "HY_Fitout")) and False)
    o.hide_render = not keep
    if keep:
        o.hide_render = False


def U(x, y, z):
    return Vector((-x, -z, y))


def flat(name, rgb, rough=.5, metal=0., alpha=1., emit=None):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = 2
    return m


steel = flat("rv_steel", (.34, .33, .31), .42, .9)
poly = flat("rv_poly", (.78, .82, .74), .35, 0, .42)
panel = flat("rv_panel", (.12, .12, .13), .6)
ground = flat("rv_ground", (.55, .45, .33), .9)
tarp = flat("rv_tarp", (.3, .32, .2), .9)


def mesh_obj(name, bm, m):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o); me.materials.append(m)
    for p in me.polygons: p.use_smooth = True
    return o


def quonset(zc, L=15., W=6.2, H=4.2, holes=True):
    prof = lambda t: (-W / 2 * math.cos(t * math.pi), H * math.sin(t * math.pi) ** .85)
    n = int(L / 1.5)
    bm = bmesh.new()
    for i in range(n + 1):
        x = -41.5 + L * i / n
        ring = []
        for k in range(17):
            y, h = prof(k / 16)
            ring.append(U(x, h, zc + y))
        for a, b in zip(ring[:-1], ring[1:]):
            d = (b - a); c = (a + b) / 2
            bmesh.ops.create_cube(bm, size=1, matrix=__import__("mathutils").Matrix.LocRotScale(c, d.to_track_quat("Z", "Y"), Vector((.07, .07, d.length))))
    mesh_obj(f"rib{zc}", bm, steel)
    bm = bmesh.new()
    V = [[bm.verts.new(U(-41.5 + L * i / n, prof(j / 12)[1] * 1.012, zc + prof(j / 12)[0] * 1.012)) for i in range(n + 1)] for j in range(13)]
    import random
    r = random.Random(3)
    for j in range(12):
        for i in range(n):
            if holes and r.random() < .05: continue
            bm.faces.new((V[j][i], V[j][i + 1], V[j + 1][i + 1], V[j + 1][i]))
    mesh_obj(f"skin{zc}", bm, poly)
    for x in (-41.5, -26.5):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1, matrix=__import__("mathutils").Matrix.LocRotScale(U(x, H * .35, zc), None, Vector((.04, W * .82, H * .7))))
        mesh_obj(f"end{x}{zc}", bm, poly)
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1, matrix=__import__("mathutils").Matrix.LocRotScale(U(x + (.03 if x > -30 else -.03), 1.1, zc), None, Vector((.06, 1.8, 2.2))))
        mesh_obj(f"door{x}{zc}", bm, panel)
    # retrofit trays (graphite)
    for dz in (-1.6, 1.6):
        for y in (.7, 1.45):
            bm = bmesh.new()
            bmesh.ops.create_cube(bm, size=1, matrix=__import__("mathutils").Matrix.LocRotScale(U(-34, y, zc + dz), None, Vector((13.8, 1.1, .12))))
            mesh_obj(f"tray{zc}{dz}{y}", bm, panel)


if ARGS.get("shell", "1") == "1":
    for zc in (36.7, 28.3):
        quonset(zc)
bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=60); mesh_obj("ground", bm, ground).location = U(-34, 0, 30)
# 1.8 m figure at the B east door
bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=.22, radius2=.18, depth=1.8)
fig = mesh_obj("figure", bm, flat("rv_fig", (.6, .15, .1), .6)); fig.location = U(-24.8, .9, 29.4)

world = bpy.data.worlds.new("w"); sc.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (.55, .62, .75, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = .9
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(sun)
sun.data.energy = 4.0; sun.rotation_euler = (math.radians(40), math.radians(10), math.radians(200))
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = int(ARGS.get("samples", 24))
sc.render.resolution_x, sc.render.resolution_y = 1600, 900
sc.view_settings.view_transform = "AgX"

VIEWS = {
    # name: (eye (Unity x, y, z), target, lens mm)
    "lane_b_south": ((-31.0, 1.62, 21.8), (-35.5, 1.1, 27.0), 28),
    "east_doors": ((-21.6, 1.62, 31.8), (-29.5, 1.3, 30.0), 26),
    "gap_west": ((-25.5, 1.62, 32.4), (-36, 1.2, 32.5), 30),
    "close_b_side": ((-33.0, 1.55, 23.9), (-34.2, 1.0, 26.8), 30),
    "aisle_b": ((-27.2, 1.55, 28.3), (-36, 1.0, 28.3), 26),
    "rack_close": ((-30.5, 1.3, 28.9), (-31.5, .9, 26.8), 30),
    "vines_inside": ((-30.8, 1.4, 27.6), (-32.5, 1.3, 25.6), 26),
    "overview": ((-18.0, 9.0, 18.0), (-34, 1.0, 32.0), 30),
}
sel = ARGS.get("views", ",".join(VIEWS)).split(",")
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
out = HERE / "review"; out.mkdir(exist_ok=True)
for name in sel:
    eye, tgt, lens = VIEWS[name]
    cam.location = U(*eye); cam.data.lens = lens; cam.data.clip_start = .05
    d = U(*tgt) - U(*eye)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = str(out / f"{name}_lod{LOD}.png")
    bpy.ops.render.render(write_still=True)
    print("rendered", name, flush=True)
