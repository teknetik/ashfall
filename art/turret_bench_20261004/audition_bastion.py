"""Blender audition: the re-authored bastion (no pintle gun) with the Meshy turret on its deck, a 1.8 m scale marker.
Unity bastion-local (x, y, z) -> Blender (-x, -z, y); Unity yaw t -> Blender Z rotation -t."""
import bpy, math, mathutils, sys
from pathlib import Path
R = Path(__file__).resolve().parents[2]
M = R / "unity/AthenHill/Assets/AthenHill/Art/WardLife/Models"; T = R / "unity/AthenHill/Assets/AthenHill/Art/TurretBench/sentinel_turret"
SRC = R / "meshy/turret-bench-20261004/source/Meshy_AI_Sentinel_Turret_1004174027_texture.glb"
out = Path(__file__).resolve().parent / "review"
opts = [tuple(map(float, a.split(","))) for a in sys.argv[sys.argv.index("--") + 1:]]   # x,z,yaw (south post, S=+1)
for k, (ux, uz, yaw) in enumerate(opts):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(M / "WL_GateBastionS_LOD0.glb"))
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(SRC)); src = [o for o in bpy.data.objects if o not in before][0]; mat = src.data.materials[0]
    bpy.data.objects.remove(src)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(T / "sentinel_turret_LOD0.glb"))
    tur = [o for o in bpy.data.objects if o not in before and o.type == "MESH"][0]
    tur.data.materials.clear(); tur.data.materials.append(mat)
    tur.rotation_mode = "XYZ"           # glTF import leaves objects in quaternion mode
    tur.location = (-ux, -uz, 0.37); tur.rotation_euler = (0, 0, math.radians(-yaw))
    bpy.ops.mesh.primitive_cylinder_add(radius=0.2, depth=1.8, location=(-0.0, -1.6, 0.9))   # scale marker on the street side
    sc = bpy.context.scene; sc.render.resolution_x, sc.render.resolution_y = 900, 650
    sc.render.engine = "BLENDER_EEVEE"
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.6, 0.65, 0.75, 1)
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sun.data.energy = 4; sun.rotation_euler = (math.radians(50), 0, math.radians(200)); sc.collection.objects.link(sun)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam; cam.data.lens = 30
    for v, loc in enumerate([(-1.0, -6.5, 2.2), (-5.5, -4.0, 3.2)]):
        cam.location = loc
        tgt = mathutils.Vector((-1.4, -0.3, 1.1))
        cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = str(out / f"bastion_turret_opt{k}_v{v}.png"); bpy.ops.render.render(write_still=True)
