"""Blender (headless) review of the training-range kit (Art/TrainingRange/Structures/*.glb): one Cycles render per piece
from a front-left three-quarter view at about player eye height (LOD0 only; COL_ proxies hidden), with a 1.8 m figure for
scale and plausible flat colours per material family (shape, construction, scale, grounding and floaters are judged
here; real materials are judged in Unity). Writes review/kit/<name>.png; sheet.py stitches them.
Run: $O/blender.sh review_kit.py -- [name-prefix,...] [--lod 1] [--back]"""
import bpy, math, sys
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SRC = HERE.parents[1] / "unity/AthenHill/Assets/AthenHill/Art/TrainingRange/Structures"
OUT = HERE / "review/kit"; OUT.mkdir(parents=True, exist_ok=True)
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
lod = int(args[args.index("--lod") + 1]) if "--lod" in args else 0
back = "--back" in args
filt = [a for a in args if not a.startswith("--") and not a.isdigit()]
filt = filt[0].split(",") if filt else [""]

PAL = {"Timber": (.42, .29, .17), "TimberDark": (.26, .19, .12), "TimberFresh": (.62, .47, .30), "Plywood": (.55, .44, .30),
       "RustSteel": (.30, .18, .11), "PlateSteel": (.36, .36, .35), "OlivePaint": (.25, .27, .17), "Hessian": (.55, .47, .33),
       "Hazard": (.75, .6, .1), "Concrete": (.5, .49, .46), "Rubber": (.04, .04, .04), "CyanGlow": (.2, .9, .95), "LampLens": (.95, .9, .7),
       "ShadeCloth": (.45, .38, .28), "SandFill": (.62, .52, .38), "Brass": (.7, .55, .2), "CellSteel": (.45, .47, .5), "CellBand": (.2, .7, .75),
       "RedLens": (.8, .08, .05), "RedLead": (.7, .05, .05), "LaneNumbers": (.9, .9, .85), "LaneNumbersPaint": (.9, .9, .85),
       "RangeOrders": (.85, .82, .7), "LaneSign": (.85, .8, .6), "Collider": (1, 0, 1)}


def colour(name):
    n = name.split(".")[0].replace("TR_", "").replace("WG_", "")
    return PAL.get(n, (.5, .5, .5))


def render(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    obs = [o for o in bpy.data.objects if o.type == "MESH"]
    for o in obs:
        hide = o.name.startswith("COL_") or ("_LOD" in o.name and not o.name.split(".")[0].endswith(f"_LOD{lod}"))
        if lod == 0 and "_LOD" not in o.name and not o.name.startswith("COL_"):
            hide = False
        o.hide_render = hide
    vis = [o for o in obs if not o.hide_render]
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in vis)
    for m in bpy.data.materials:
        m.use_nodes = True
        b = m.node_tree.nodes.get("Principled BSDF") or m.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        for l in list(b.inputs["Base Color"].links):
            m.node_tree.links.remove(l)
        c = colour(m.name)
        b.inputs["Base Color"].default_value = (*c, 1)
        b.inputs["Roughness"].default_value = .75
        if "Glow" in m.name or "Lens" in m.name:
            b.inputs["Emission Color"].default_value = (*c, 1); b.inputs["Emission Strength"].default_value = 2
    lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
    for o in vis:
        for v in o.bound_box:
            w = o.matrix_world @ Vector(v)
            lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    size = hi - lo; c = (lo + hi) / 2
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 20
    sc.view_settings.view_transform = "Standard"
    sc.render.resolution_x = 960; sc.render.resolution_y = 720
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (.72, .74, .78, 1); w.node_tree.nodes["Background"].inputs[1].default_value = .9
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(sun); sun.data.energy = 3.2
    sun.rotation_euler = (math.radians(48), 0, math.radians(-35))
    gz = lo.z
    bpy.ops.mesh.primitive_plane_add(size=200, location=(c.x, c.y, gz - .002))
    g = bpy.context.active_object; gm = bpy.data.materials.new("ground"); gm.use_nodes = True
    gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (.55, .48, .38, 1); g.data.materials.append(gm)
    # 1.8 m figure beside the piece (Blender -Y is Unity +Z front; Unity +X is Blender -X)
    fx = lo.x - .6
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=.18, depth=1.8, location=(fx, c.y, gz + .9))
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.lens = 35
    ext = max(size.x, size.y, size.z * 1.3, 1.9)
    # front = Unity +Z = Blender -Y; front-left of the piece (Unity -X = Blender +X)
    sy = 1 if back else -1
    d = ext * 1.45 + .8
    eye = min(max(1.62, size.z * .7), 4)
    cam.location = (c.x + (-.55 if back else .55) * d, c.y + sy * .85 * d, gz + eye)
    cam.rotation_euler = (Vector((c.x - (.35 if not back else -.35), c.y, gz + size.z * .42)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    name = path.stem + (f"_lod{lod}" if lod else "") + ("_back" if back else "")
    sc.render.filepath = str(OUT / f"{name}.png")
    bpy.ops.render.render(write_still=True)
    print("REVIEW", name, "tris", tris, "size", [round(v, 2) for v in size], flush=True)


for p in sorted(SRC.glob("*.glb")):
    if any(p.stem.startswith(f) for f in filt):
        render(p)
