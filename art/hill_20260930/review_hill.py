"""Blender (headless) review renders of the authored hill LOD0 (Cycles CPU, simple materials x vertex tint/AO)."""
import bpy, math, sys
from pathlib import Path
from mathutils import Vector
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
lod = int(sys.argv[sys.argv.index("--") + 1]) if "--" in sys.argv else 0
views = sys.argv[sys.argv.index("--") + 2:] if "--" in sys.argv and len(sys.argv) > sys.argv.index("--") + 2 else None
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT / f"unity/AthenHill/Assets/AthenHill/Art/WardHill/Models/WardHill_LOD{lod}.glb"))
COL = {"VH_Ashlar": (0.62, 0.5, 0.36), "VH_AshlarRough": (0.55, 0.45, 0.33), "VH_Mortar": (0.42, 0.37, 0.3), "VH_PodiumSlab": (0.6, 0.52, 0.4),
       "VH_Sand": (0.72, 0.6, 0.44), "VH_Steel": (0.25, 0.22, 0.2), "VH_Dark": (0.03, 0.03, 0.03), "VH_Bronze": (0.4, 0.28, 0.15),
       "VH_LampLens": (0.9, 0.85, 0.7), "WH_BedSoil": (0.23, 0.15, 0.09), "WH_RingLitter": (0.3, 0.18, 0.1), "RootBark": (0.28, 0.22, 0.17)}
for m in bpy.data.materials:
    base = COL.get(m.name.split(".")[0], (0.8, 0.0, 0.8))
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.85
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
    nt.links.new(bsdf.outputs[0], out.inputs[0])
sc_ = bpy.context.scene
sc_.render.engine = "CYCLES"; sc_.cycles.device = "CPU"; sc_.cycles.samples = 40
sc_.render.resolution_x = 1280; sc_.render.resolution_y = 720
w = bpy.data.worlds.new("w"); sc_.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.62, 0.72, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.7
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc_.collection.objects.link(sun); sun.data.energy = 4.0; sun.data.angle = 0.02
def U(p): return Vector((-p[0], -p[2], p[1]))
# sun from the south-west-ish, 40 deg up (Unity direction the light travels)
d = Vector((0.55, -0.64, 0.53)); sun.rotation_euler = U(d).to_track_quat("-Z", "Y").to_euler()
# ground plane at plaza level
bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, -0.005))
g = bpy.context.active_object; gm = bpy.data.materials.new("ground"); gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.5, 0.42, 0.32, 1); g.data.materials.append(gm)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc_.collection.objects.link(cam); sc_.camera = cam
VIEWS = {
    "overview": ((-15, 13, 16), (0, 0.6, 0), 45),
    "ring": ((-5.6, 3.3, 5.2), (0, 1.8, 0), 55),
    "ring_heave": ((-4.7, 2.9, 4.6), (-2.5, 1.9, 1.7), 45),
    "ring_inner": ((0.6, 3.6, 4.6), (-0.8, 1.7, -0.6), 55),
    "stair_north": ((3.5, 1.7, -14.5), (0, 0.9, -8.5), 50),
    "stair_west": ((14.5, 1.7, 3.8), (8.5, 0.8, 0), 50),
    "corner": ((-11.5, 1.7, -11.0), (-7, 0.8, -7), 50),
    "stair_head": ((0.9, 3.1, -3.5), (0, 1.5, -7.5), 55),
    "terminal_pad": ((1.5, 3.2, -1.5), (5, 1.5, -4), 55),
    "top": ((0.01, 26, 0.0), (0, 0, 0), 45),
}
for name, (pos, tgt, fov) in VIEWS.items():
    if views and name not in views: continue
    cam.location = U(pos); cam.data.angle = math.radians(fov)
    cam.rotation_euler = (U(tgt) - U(pos)).to_track_quat("-Z", "Y").to_euler()
    sc_.render.filepath = str(HERE / f"review/hill_lod{lod}_{name}.png")
    bpy.ops.render.render(write_still=True)
