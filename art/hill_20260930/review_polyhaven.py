"""Blender (headless): render a quick Cycles CPU view of each downloaded Poly Haven model and list its objects."""
import bpy, sys, math, mathutils, json
from pathlib import Path
HERE = Path(__file__).resolve().parent
ids = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sorted(p.name for p in (HERE / "polyhaven/models").iterdir())
report = {}
for aid in ids:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    g = next((HERE / "polyhaven/models" / aid).glob("*.gltf"))
    bpy.ops.import_scene.gltf(filepath=str(g))
    objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    mn = mathutils.Vector((1e9,) * 3); mx = -mn
    rows = []
    for o in objs:
        ws = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
        omn = mathutils.Vector(map(min, *ws)) if False else mathutils.Vector([min(w[i] for w in ws) for i in range(3)])
        omx = mathutils.Vector([max(w[i] for w in ws) for i in range(3)])
        mn = mathutils.Vector(map(min, mn, omn)); mx = mathutils.Vector(map(max, mx, omx))
        rows.append(dict(name=o.name, tris=sum(len(p.vertices) - 2 for p in o.data.polygons), size=[round(v, 3) for v in (omx - omn)],
                         centre=[round(v, 3) for v in (omx + omn) / 2], mats=[m.name for m in o.data.materials if m]))
    report[aid] = rows
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 16
    sc.render.resolution_x = 800; sc.render.resolution_y = 500
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.6, 0.62, 0.66, 1)
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(sun)
    sun.data.energy = 4; sun.rotation_euler = (math.radians(45), 0, math.radians(30))
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
    ctr = (mn + mx) / 2; size = (mx - mn).length
    cam.location = ctr + mathutils.Vector((size * 0.1, -size * 0.95, size * 0.45))
    cam.rotation_euler = (ctr - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = str(HERE / "review/polyhaven" / f"{aid}.png")
    bpy.ops.render.render(write_still=True)
(HERE / "review/polyhaven/objects.json").write_text(json.dumps(report, indent=1))
