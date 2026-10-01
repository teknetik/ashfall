"""Blender (headless) review renders of the courtyard tree beds (Cycles CPU, flat colours x vertex tint/AO).
Source check only; the game's materials and lighting are judged in Unity.
Run: env -i HOME=$HOME PATH=/usr/bin:/bin blender -b --factory-startup -P review_tree_beds.py -- Birch4b [views...]"""
import bpy, math, sys
from pathlib import Path
from mathutils import Vector
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MODELS = ROOT / "unity/AthenHill/Assets/AthenHill/Art/CourtyardTrees/Models"
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["Birch4b"]
key, views = args[0], args[1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(MODELS / f"TreeBed_{key}_LOD0.glb"))
bpy.ops.import_scene.gltf(filepath=str(MODELS / f"TreeBedPlants_{key}_LOD0.glb"))
COL = {"VH_Ashlar": (0.62, 0.5, 0.36), "VH_AshlarRough": (0.55, 0.45, 0.33), "VH_Mortar": (0.42, 0.37, 0.3), "VH_PodiumSlab": (0.6, 0.52, 0.4),
       "VH_Sand": (0.72, 0.6, 0.44), "VH_Steel": (0.25, 0.22, 0.2), "VH_Dark": (0.03, 0.03, 0.03), "VH_Bronze": (0.4, 0.28, 0.15),
       "VH_LampLens": (0.9, 0.85, 0.7), "WH_RingLitter": (0.3, 0.18, 0.1), "RootBark": (0.28, 0.22, 0.17)}
for m in bpy.data.materials:
    nm = m.name.split(".")[0]
    vertex = nm in COL and nm not in ("VH_Steel", "VH_Dark", "VH_Bronze", "VH_LampLens")
    base = COL.get(nm, (0.25, 0.32, 0.14))
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.85
    if vertex:
        attr = nt.nodes.new("ShaderNodeVertexColor"); attr.layer_name = "Color"
        mul = nt.nodes.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs[0].default_value = 1.0
        mul.inputs[6].default_value = (*base, 1)
        sc = nt.nodes.new("ShaderNodeVectorMath"); sc.operation = "SCALE"; sc.inputs[3].default_value = 4.6
        nt.links.new(attr.outputs["Color"], sc.inputs[0])
        ao = nt.nodes.new("ShaderNodeMix"); ao.data_type = "RGBA"; ao.blend_type = "MULTIPLY"; ao.inputs[0].default_value = 1.0
        nt.links.new(sc.outputs[0], mul.inputs[7])
        nt.links.new(mul.outputs[2], ao.inputs[6])
        nt.links.new(attr.outputs["Alpha"], ao.inputs[7])
        nt.links.new(ao.outputs[2], bsdf.inputs["Base Color"])
    else:
        bsdf.inputs["Base Color"].default_value = (*base, 1)
        if nm in ("VH_Steel", "VH_Bronze"):
            bsdf.inputs["Metallic"].default_value = 0.8
    nt.links.new(bsdf.outputs[0], out.inputs[0])
sc_ = bpy.context.scene
sc_.render.engine = "CYCLES"; sc_.cycles.device = "CPU"; sc_.cycles.samples = 48
sc_.render.resolution_x = 1280; sc_.render.resolution_y = 720
w = bpy.data.worlds.new("w"); sc_.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.62, 0.72, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.7
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc_.collection.objects.link(sun); sun.data.energy = 4.0; sun.data.angle = 0.02
def U(p): return Vector((-p[0], -p[2], p[1]))
d = Vector((0.55, -0.64, 0.53)); sun.rotation_euler = U(d).to_track_quat("-Z", "Y").to_euler()
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, -0.002))
g = bpy.context.active_object; gm = bpy.data.materials.new("ground"); gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.5, 0.42, 0.32, 1); g.data.materials.append(gm)
# stand-ins: the birch trunk (0.35 m at the base) and a 1.8 m person
bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=0.36, radius2=0.2, depth=4.0, location=(0, 0, 1.6))
tm = bpy.data.materials.new("trunk"); tm.use_nodes = True; tm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.75, 0.73, 0.68, 1)
bpy.context.active_object.data.materials.append(tm)
bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.22, depth=1.8, location=U((2.6, 0.9, -0.6)))
pm = bpy.data.materials.new("person"); pm.use_nodes = True; pm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.2, 0.35, 0.6, 1)
bpy.context.active_object.data.materials.append(pm)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc_.collection.objects.link(cam); sc_.camera = cam
VIEWS = {
    "overview": ((-4.2, 2.6, 3.4), (0, 0.3, 0), 50),
    "eye": ((4.4, 1.62, -2.2), (0, 0.35, 0), 55),
    "seat": ((-2.1, 0.75, -2.0), (0.6, 0.4, 0.4), 60),
    "heave": ((-2.4, 1.3, 2.0), (-1.4, 0.45, 0.55), 45),
    "inside": ((1.4, 1.5, 1.3), (-0.4, 0.3, -0.4), 60),
    "top": ((0.01, 7.5, 0.0), (0, 0, 0), 45),
}
for name, (pos, tgt, fov) in VIEWS.items():
    if views and name not in views: continue
    cam.location = U(pos); cam.data.angle = math.radians(fov)
    cam.rotation_euler = (U(tgt) - U(pos)).to_track_quat("-Z", "Y").to_euler()
    sc_.render.filepath = str(HERE / f"review/{key}_{name}.png")
    bpy.ops.render.render(write_still=True)
