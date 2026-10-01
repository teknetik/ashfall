"""Blender (headless) review renders of the West Gate arch fittings in place: the GLB of one arch (Art/WestGateArches/
Models/WGA_Gate<K>.glb, chosen LOD) inside the real Meshy arch geometry (gate_world.obj from extract_gate_mesh.py,
shifted to the arch's local frame), a paving plane, a 1.8 m figure for scale, low afternoon sun from the city side.
Flat plausible colours per material family (shape, construction, fit, scale and floaters are judged here; real
materials are judged in Unity). Writes review/<run>/<K>_<view>_lod<n>.png.

Run: $O/blender.sh review_gate.py -- <run> [A|B] [--lod n] [--views front,close3q,...] [--samples 24] [--res 960]
"""
import bpy, bmesh, math, sys
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SRC = REPO / "unity/AthenHill/Assets/AthenHill/Art/WestGateArches/Models"
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
RUN = args[0] if args else "r1"
KEY = args[1] if len(args) > 1 and not args[1].startswith("--") else "A"


def opt(k, d):
    return args[args.index(k) + 1] if k in args else d


LOD = int(opt("--lod", "0"))
SAMPLES = int(opt("--samples", "24"))
RES = int(opt("--res", "960"))
ZC = {"A": 0.0, "B": 12.0}[KEY]
OUT = HERE / "review" / RUN
OUT.mkdir(parents=True, exist_ok=True)

# Unity local (x depth, y up, z along) -> Blender
def U(x, y, z):
    return Vector((-x, -z, y))


VIEWS = {
    # name: (eye, target, lens mm)
    "spawn": ((-5.0, 1.65, 0.3), (0.6, 2.6, 0.0), 22),
    "front": ((-7.5, 1.65, -1.2), (0.6, 2.6, 0.0), 26),
    "close3q": ((-2.4, 1.65, -1.8), (0.62, 1.4, 0.4), 22),
    "wicket": ((-1.0, 1.45, -0.9), (0.62, 1.15, -1.36), 24),
    "head": ((-2.6, 1.65, 0.9), (0.66, 5.4, 0.0), 18),
    "guard": ((-2.6, 1.05, -3.6), (-1.15, 0.45, -2.35), 26),
    "hinge": ((-0.6, 1.6, 1.0), (0.6, 2.3, 2.35), 22),
    "far": ((-30.0, 1.65, -6.0), (0.6, 3.0, 0.0), 50),
    "mid": ((-14.0, 1.65, -3.0), (0.6, 3.0, 0.0), 35),
    "back": ((5.5, 2.4, 2.8), (0.8, 2.6, 0.0), 22),
    "top": ((-2.5, 9.5, -3.0), (0.3, 1.0, 0.0), 22),
}
VIEW_LIST = opt("--views", "spawn,front,close3q,wicket,head,guard,hinge").split(",")

PAL = {"TR_Timber": (.40, .34, .26), "TR_TimberDark": (.22, .17, .12), "TR_TimberFresh": (.58, .44, .28),
       "WG_RustSteel": (.30, .18, .11), "WG_PlateSteel": (.33, .33, .32), "WG_Rubber": (.035, .035, .035),
       "VH_Dark": (.05, .05, .05), "VH_Steel": (.35, .36, .37), "VH_LampLens": (1.0, .85, .6), "VH_Ashlar": (.60, .47, .33),
       "WG_Collider": (1, 0, 1)}


def setup_materials():
    for m in bpy.data.materials:
        m.use_nodes = True
        b = m.node_tree.nodes.get("Principled BSDF") or m.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        for l in list(b.inputs["Base Color"].links):
            m.node_tree.links.remove(l)
        n = m.name.split(".")[0]
        c = PAL.get(n, (.5, .5, .5))
        b.inputs["Base Color"].default_value = (*c, 1)
        b.inputs["Roughness"].default_value = .55 if "Steel" in n else .8
        b.inputs["Metallic"].default_value = .6 if n in ("WG_PlateSteel", "VH_Steel") else 0.0
        if "Lens" in n:
            b.inputs["Emission Color"].default_value = (*c, 1)
            b.inputs["Emission Strength"].default_value = 3


def flat_mat(name, c, rough=.85):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*c, 1)
    b.inputs["Roughness"].default_value = rough
    return m


def load_arch():
    vs, fs = [], []
    for line in open(HERE / "gate_world.obj"):
        if line.startswith("v "):
            x, y, z = map(float, line.split()[1:4])
            vs.append(U(x - 48.0, y, z - ZC))
        elif line.startswith("f "):
            fs.append([int(t) - 1 for t in line.split()[1:4]])
    me = bpy.data.meshes.new("MeshyArch")
    me.from_pydata(vs, [], fs)
    me.update()
    for p in me.polygons:
        p.use_smooth = False
    ob = bpy.data.objects.new("MeshyArch", me)
    bpy.context.scene.collection.objects.link(ob)
    me.materials.append(flat_mat("Arch", (.58, .45, .31)))
    # paving
    bpy.ops.mesh.primitive_plane_add(size=1)
    g = bpy.context.active_object
    g.scale = (40, 40, 1)
    g.location = U(-6, -0.001, 0)
    g.data.materials.append(flat_mat("Paving", (.55, .45, .33)))
    # 1.8 m figure at the apron
    bpy.ops.mesh.primitive_cylinder_add(radius=.22, depth=1.8, location=U(-1.8, .9, 1.4))
    bpy.context.active_object.data.materials.append(flat_mat("Figure", (.2, .3, .45)))


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(SRC / f"WGA_Gate{KEY}.glb"))
    tris = 0
    for o in list(bpy.data.objects):
        if o.type != "MESH":
            continue
        n = o.name.split(".")[0]
        keep = (not n.startswith("COL_")) and n.endswith(f"_LOD{LOD}")
        o.hide_render = not keep
        if keep:
            tris += sum(len(p.vertices) - 2 for p in o.data.polygons)
    setup_materials()
    load_arch()
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = RES, RES * 9 // 16
    sc.view_settings.view_transform = "AgX"
    w = bpy.data.worlds.new("W")
    sc.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (.55, .62, .75, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = .9
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
    sun.data.energy = 4.0
    sun.data.angle = math.radians(1.5)
    sc.collection.objects.link(sun)
    # afternoon sun from the city side (west, -x) and a little south, 28 deg up: low enough to reach into the tunnel
    d = U(-math.cos(math.radians(28)) * .85, math.sin(math.radians(28)), -.45).normalized()
    sun.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    for v in VIEW_LIST:
        eye, tgt, lens = VIEWS[v]
        cam.location = U(*eye)
        cam.rotation_euler = (U(*tgt) - U(*eye)).to_track_quat("-Z", "Y").to_euler()
        cam.data.lens = lens
        cam.data.clip_start = .05
        sc.render.filepath = str(OUT / f"{KEY}_{v}_lod{LOD}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", v, tris, flush=True)


main()
