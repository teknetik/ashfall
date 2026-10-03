"""Blender review renders of Ward life models (Cycles CPU, preview materials: the Unity textures on UV0, flat colours
for kit materials). Run: blender.sh review_render.py -- <model> <out_prefix> [cam spec ...]
cam spec: "name:px,py,pz:tx,ty,tz:lens" in Unity coordinates local to the model root (y up, +z street)."""
import bpy, sys, math
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MOD = ROOT / "unity/AthenHill/Assets/AthenHill/Art/WardLife/Models"
TEX = ROOT / "unity/AthenHill/Assets/AthenHill/Art/WardLife/Textures"
a = sys.argv[sys.argv.index("--") + 1:]
model, prefix, cams = a[0], a[1], a[2:]
lod = 0
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(MOD / f"{model}_LOD{lod}.glb"))

FLAT = {"WG_Hessian": (0.42, 0.34, 0.24), "WL_HessianOld": (0.33, 0.28, 0.21), "WL_HessianPale": (0.55, 0.47, 0.35),
        "VH_Sand": (0.62, 0.5, 0.36), "VH_AshlarRough": (0.6, 0.48, 0.36), "VH_Steel": (0.4, 0.4, 0.4), "WB_BlackSteel": (0.06, 0.06, 0.06),
        "WG_OlivePaint": (0.2, 0.22, 0.13), "WS_PaintOlive": (0.2, 0.22, 0.13), "WG_PlateSteel": (0.3, 0.29, 0.28), "WS_PaintYellow": (0.7, 0.55, 0.1),
        "WS_Deck": (0.25, 0.25, 0.25), "TR_Timber": (0.4, 0.3, 0.2), "TR_TimberDark": (0.25, 0.18, 0.12)}


def tex(name, cs="sRGB"):
    p = TEX / name
    if not p.exists():
        return None
    im = bpy.data.images.load(str(p), check_existing=True)
    im.colorspace_settings.name = cs
    return im


for m in bpy.data.materials:
    n = m.name.split(".")[0]
    nt = m.node_tree
    if nt is None:
        continue
    bsdf = next((x for x in nt.nodes if x.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        continue
    for l in list(bsdf.inputs["Base Color"].links):
        nt.links.remove(l)
    base = {"WL_GabionFill": ("WL_GabionFill_BaseMap.png", 1 / 1.5), "WL_GabionFillWired": ("WL_GabionFillWired_BaseMap.png", 1 / 1.5),
            "WL_GabionWire": ("WL_GabionWire_BaseMap.png", 1.0), "WL_GabionWireFresh": ("WL_GabionWireFresh_BaseMap.png", 1.0)}.get(n)
    if base:
        uv = nt.nodes.new("ShaderNodeUVMap"); uv.uv_map = "UVMap"
        mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (base[1], base[1], 1)
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = tex(base[0])
        nt.links.new(uv.outputs[0], mp.inputs[0]); nt.links.new(mp.outputs[0], t.inputs[0])
        nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
        if "Wire" in n and "Fill" not in n:
            nt.links.new(t.outputs["Alpha"], bsdf.inputs["Alpha"])
            bsdf.inputs["Metallic"].default_value = 0.6
        bsdf.inputs["Roughness"].default_value = 0.8
    else:
        c = FLAT.get(n, (0.5, 0.5, 0.5))
        bsdf.inputs["Base Color"].default_value = (*c, 1)
        bsdf.inputs["Roughness"].default_value = 0.75

sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = 48
sc.render.resolution_x, sc.render.resolution_y = 1280, 720
sc.view_settings.view_transform = "AgX"
w = bpy.data.worlds.new("w"); sc.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.65, 0.8, 1)
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
sun.data.energy = 4.0
sun.rotation_euler = (math.radians(50), 0, math.radians(35))
sc.collection.objects.link(sun)
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
g = bpy.context.active_object
gm = bpy.data.materials.new("ground"); g.data.materials.append(gm)
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.5, 0.42, 0.33, 1)
# 1.8 m scale figure
bpy.ops.mesh.primitive_cylinder_add(radius=0.2, depth=1.8, location=(-6, 4.0, 0.9))


def U(p):   # Unity (x, y, z) -> Blender
    return Vector((-p[0], -p[2], p[1]))


for spec in cams:
    nm, p, t, lens = spec.split(":")
    p = [float(v) for v in p.split(",")]; t = [float(v) for v in t.split(",")]
    cd = bpy.data.cameras.new(nm); cd.lens = float(lens)
    cam = bpy.data.objects.new(nm, cd); sc.collection.objects.link(cam)
    cam.location = U(p)
    d = U(t) - U(p)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam
    sc.render.filepath = f"{prefix}_{nm}.png"
    bpy.ops.render.render(write_still=True)
    print("rendered", nm, flush=True)
