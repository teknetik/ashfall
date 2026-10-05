import bpy, math
from pathlib import Path
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[3]
P = ROOT / "meshy/field-supply-20261005/props"
OUT = Path(__file__).resolve().parent / "inspect"; OUT.mkdir(exist_ok=True)
for name in ("pack_field", "pack_rucksack", "pack_frame", "pack_carrier", "pack_rig"):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(P / name / "model.glb"))
    ms = [o for o in bpy.data.objects if o.type == "MESH"]
    pts = [o.matrix_world @ Vector(c) for o in ms for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))); hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    print("INSPECT", name, "size", [round(v, 3) for v in hi - lo], "tris", sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in ms), "mats", [m.name for o in ms for m in o.data.materials])
    c = (lo + hi) / 2; r = (hi - lo).length
    sc = bpy.context.scene; sc.render.engine = "BLENDER_WORKBENCH"; sc.render.resolution_x = sc.render.resolution_y = 360
    sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "TEXTURE"
    for tag, d in (("front_negY", Vector((0, -1, 0.15))), ("side_posX", Vector((1, 0, 0.15)))):
        cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
        cam.location = c + d.normalized() * r * 1.6
        cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = str(OUT / f"{name}_{tag}.png"); bpy.ops.render.render(write_still=True)
