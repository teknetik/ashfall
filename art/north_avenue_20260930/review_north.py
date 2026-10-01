"""Source review renders for the north avenue buildings (Blender 5.2, Cycles on the CPU; not the game's render).

Run:  blender -b --python-exit-code 1 -P review_north.py -- <Model> [<Model> ...]    (Model = Salvage, Repairs, ThreadHide,
      BasicGeneral). Imports Art/WardShops/Models/<Model>_LOD0.glb (or the booth's folder), gives every material a
      preview shader (vertex colour x a base tint for the masonry, flat tints for metal, glass and cloth), adds a 1.8 m
      scale marker in front and renders review/<Model>_<view>.png.
Views are defined in Unity shop-local metres (facade faces +Z); U() converts to Blender.
"""
import bpy, math, sys
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MODELS = ROOT / "unity/AthenHill/Assets/AthenHill/Art/WardShops/Models"
OUT = HERE / "review"
OUT.mkdir(exist_ok=True)

TINTS = {
    "VH_Ashlar": (0.78, 0.6, 0.42), "VH_AshlarRough": (0.72, 0.56, 0.4), "VH_Mortar": (0.5, 0.42, 0.34),
    "VH_PodiumSlab": (0.74, 0.6, 0.45), "VH_Roof": (0.4, 0.37, 0.34), "VH_Sand": (0.8, 0.66, 0.48),
    "VH_DoorSteel": (0.2, 0.21, 0.22), "VH_Steel": (0.3, 0.3, 0.3), "VH_PaintedSteel": (0.22, 0.24, 0.25),
    "VH_Bronze": (0.45, 0.3, 0.15), "VH_Brass": (0.6, 0.45, 0.2), "VH_Dark": (0.05, 0.05, 0.05), "VH_Rubber": (0.04, 0.04, 0.04),
    "WS_Glass": (0.08, 0.1, 0.12), "WS_ClearGlass": (0.6, 0.7, 0.72), "WS_Shutter": (0.34, 0.36, 0.36), "WS_Corrugated": (0.46, 0.38, 0.33),
    "WS_PaintTeal": (0.2, 0.34, 0.35), "WS_PaintRed": (0.42, 0.17, 0.12), "WS_PaintOlive": (0.3, 0.32, 0.2),
    "WS_PaintOchre": (0.55, 0.38, 0.14), "WS_PaintYellow": (0.62, 0.48, 0.1), "WS_ContainerRust": (0.42, 0.2, 0.12),
    "WS_Canvas": (0.54, 0.27, 0.18), "WS_ClothIndigo": (0.12, 0.16, 0.32), "WS_ClothOchre": (0.62, 0.42, 0.16),
    "WS_ClothMadder": (0.5, 0.14, 0.1), "WS_ClothBone": (0.75, 0.7, 0.6), "WS_Hide": (0.42, 0.28, 0.17),
    "WS_PanelDark": (0.2, 0.2, 0.22), "WS_Deck": (0.3, 0.3, 0.3), "WS_LedWarm": (1.0, 0.7, 0.4), "WS_LedCyan": (0.3, 0.9, 1.0),
}
MASONRY = {"VH_Ashlar", "VH_AshlarRough", "VH_Mortar", "VH_PodiumSlab"}
EMIT = {"WS_LedWarm", "WS_LedCyan"}


def U(p):
    return Vector((-p[0], -p[2], p[1]))


def preview_material(name):
    base = name.split(".")[0]
    m = bpy.data.materials.new("prev_" + base)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tint = TINTS.get(base, (0.5, 0.0, 0.5))
    bsdf.inputs["Base Color"].default_value = (*tint, 1)
    bsdf.inputs["Roughness"].default_value = 0.08 if "Glass" in base else 0.75
    if base in ("VH_Steel", "VH_Bronze", "VH_Brass"):
        bsdf.inputs["Metallic"].default_value = 0.8
    if base in MASONRY:
        va = nt.nodes.new("ShaderNodeVertexColor")
        va.layer_name = ""          # the mesh's active colour attribute (glTF COLOR_0)
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs["Factor"].default_value = 1.0
        mul.inputs[6].default_value = (*[c * 2 for c in tint], 1)
        nt.links.new(va.outputs["Color"], mul.inputs[7])
        # vertex alpha = sky occlusion
        mul2 = nt.nodes.new("ShaderNodeMix")
        mul2.data_type = "RGBA"
        mul2.blend_type = "MULTIPLY"
        mul2.inputs["Factor"].default_value = 1.0
        nt.links.new(mul.outputs[2], mul2.inputs[6])
        comb = nt.nodes.new("ShaderNodeCombineColor")
        nt.links.new(va.outputs["Alpha"], comb.inputs[0])
        nt.links.new(va.outputs["Alpha"], comb.inputs[1])
        nt.links.new(va.outputs["Alpha"], comb.inputs[2])
        nt.links.new(comb.outputs[0], mul2.inputs[7])
        nt.links.new(mul2.outputs[2], bsdf.inputs["Base Color"])
    if base in EMIT:
        bsdf.inputs["Emission Color"].default_value = (*tint, 1)
        bsdf.inputs["Emission Strength"].default_value = 4.0
    if base == "WS_ClearGlass":
        bsdf.inputs["Alpha"].default_value = 0.12
    return m


def setup(model):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    path = MODELS / f"{model}_LOD0.glb"
    if not path.exists():
        path = ROOT / f"unity/AthenHill/Assets/AthenHill/Art/WardShops/Booth/{model}_LOD0.glb"
    bpy.ops.import_scene.gltf(filepath=str(path))
    cache = {}
    for ob in bpy.context.scene.objects:
        if ob.type != "MESH":
            continue
        for i, slot in enumerate(ob.material_slots):
            n = slot.material.name if slot.material else "none"
            if n not in cache:
                cache[n] = preview_material(n)
            slot.material = cache[n]
    # ground and paving
    bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, 0))
    g = bpy.context.active_object
    gm = bpy.data.materials.new("ground")
    gm.use_nodes = True
    gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.55, 0.45, 0.33, 1)
    g.data.materials.append(gm)
    # 1.8 m scale marker on the porch
    bpy.ops.mesh.primitive_cylinder_add(radius=0.2, depth=1.8, location=U((2.9, 0.5 + 0.9, 2.6)))
    mk = bpy.context.active_object
    mm = bpy.data.materials.new("marker")
    mm.use_nodes = True
    mm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.9, 0.9, 0.95, 1)
    mk.data.materials.append(mm)
    # sun + sky
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    bpy.context.scene.collection.objects.link(sun)
    sun.data.energy = 4.0
    sun.data.angle = math.radians(1.5)
    sun.rotation_euler = (math.radians(52), 0, math.radians(215))
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.62, 0.72, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.9
    bpy.context.scene.world = world
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 24
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = 1280, 800
    sc.view_settings.view_transform = "AgX"
    return sc


def shoot(sc, name, eye, target, lens=28):
    cam = bpy.data.objects.get("cam") or bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    if cam.name not in sc.collection.objects:
        sc.collection.objects.link(cam)
    cam.data.lens = lens
    e, t = U(eye), U(target)
    cam.location = e
    cam.rotation_euler = (t - e).to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam
    sc.render.filepath = str(OUT / f"{name}.png")
    bpy.ops.render.render(write_still=True)
    print("wrote", sc.render.filepath, flush=True)


VIEWS = {
    "front": ((0.0, 1.7, 13.5), (0.0, 4.2, 0.0), 26),
    "three_q_left": ((-8.5, 1.7, 9.5), (0.0, 3.8, -1.0), 26),
    "three_q_right": ((8.5, 1.7, 9.5), (0.0, 3.8, -1.0), 26),
    "porch": ((1.2, 1.65, 4.6), (-0.6, 2.4, 0.0), 22),
    "upper": ((0.5, 1.7, 5.5), (0.0, 6.2, 0.0), 30),
    "side_left": ((-11.5, 2.5, -3.0), (0.0, 3.5, -3.4), 24),
    "rear": ((3.5, 2.2, -16.5), (0.0, 3.5, -3.4), 24),
    # Basic General booth (root at world (8, 0, 15.1))
    "bg_front": ((0.0, 1.65, 9.0), (0.0, 2.0, 0.0), 26),
    "bg_three_q": ((-5.5, 1.65, 6.5), (0.0, 2.0, 0.0), 24),
    "bg_porch": ((0.9, 1.65, 3.2), (-0.4, 1.9, -1.0), 20),
    "bg_under": ((0.0, 1.5, 2.0), (0.0, 3.2, 0.2), 16),
    "bg_rear": ((-4.0, 1.8, -7.5), (0.0, 1.8, -1.5), 24),
    "bg_side": ((7.5, 1.7, 1.0), (0.0, 1.8, 0.0), 24),
}


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    views = [a[6:] for a in args if a.startswith("views=")]
    models = [a for a in args if not a.startswith("views=")]
    names = views[0].split(",") if views else list(VIEWS)
    for model in models:
        sc = setup(model)
        for v in names:
            eye, tgt, lens = VIEWS[v]
            shoot(sc, f"{model}_{v}", eye, tgt, lens)


main()
