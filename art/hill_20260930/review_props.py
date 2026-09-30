"""Blender review of the prepared Meshy prop LODs with their base colour map (Cycles CPU)."""
import bpy, math
from pathlib import Path
from mathutils import Vector
HERE = Path(__file__).resolve().parent
P = HERE.parents[1] / "unity/AthenHill/Assets/AthenHill/Art/HillProps"
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 32
sc.render.resolution_x = 1600; sc.render.resolution_y = 900
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.6, 0.63, 0.68, 1)
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(sun); sun.data.energy = 3.5
sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
x = 0.0
for name, spacing in (("Terminal", 1.4), ("Floodlight", 1.3)):
    img = bpy.data.images.load(str(P / name / "source_BaseColor.jpg"))
    nimg = bpy.data.images.load(str(P / name / "source_Normal.jpg")); nimg.colorspace_settings.name = "Non-Color"
    m = bpy.data.materials.new(name + "_rev"); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = img; nt.links.new(t.outputs[0], b.inputs["Base Color"])
    tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = nimg
    nm = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(tn.outputs[0], nm.inputs[1]); nt.links.new(nm.outputs[0], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = 0.6
    for li in range(3):
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=str(P / name / f"{name}_LOD{li}.glb"))
        for o in set(bpy.data.objects) - before:
            if o.type == "MESH":
                o.location.x += x
                o.data.materials.clear(); o.data.materials.append(m)
        x += spacing
    x += 0.4
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
for name, loc, tgt, fov in (("front", (3.9, -7.5, 1.6), (3.9, 0, 0.6), 60), ("back", (3.9, 7.5, 1.9), (3.9, 0, 0.6), 60),
                            ("close_terminal", (0.0, -1.7, 1.45), (0.0, 0, 1.2), 45), ("close_flood", (3.6, -1.5, 1.0), (4.6, 0, 0.55), 45),
                            ("close_flood_side", (4.6, -2.0, 0.55), (4.6, 0, 0.55), 40)):
    cam.location = loc; cam.data.angle = math.radians(fov)
    cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = str(HERE / f"review/props_{name}.png")
    bpy.ops.render.render(write_still=True)
