"""Blender (headless) review of the street-dressing kit: every prop's LOD (default 0) in a labelled grid with a 1.8 m
figure, flat colours per material (geometry, orientation, grounding and scale check; materials are judged in Unity).
Run: env -i HOME=$HOME PATH=/usr/bin:/bin blender -b --factory-startup -P review_kit.py -- [lod] [prefix-filter]"""
import bpy, json, math, sys, zlib
from pathlib import Path
from mathutils import Vector
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PROPS = ROOT / "unity/AthenHill/Assets/AthenHill/Art/StreetDressing/Props"
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
lod = int(args[0]) if args else 0
filt = args[1] if len(args) > 1 else ""
bpy.ops.wm.read_factory_settings(use_empty=True)
pref = tuple(filt.split(",")) if filt else ("",)
ids = sorted(p.name for p in PROPS.iterdir() if p.is_dir() and p.name.startswith(pref) and (p / f"{p.name}_LOD{lod}.glb").exists())
cols = 8 if len(ids) > 12 else 5
sp = 1.7 if len(ids) > 12 else 2.2
for i, pid in enumerate(ids):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(PROPS / pid / f"{pid}_LOD{lod}.glb"))
    x, y = (i % cols) * sp, -(i // cols) * sp * 1.25
    for o in set(bpy.data.objects) - before:
        if o.parent is None:
            o.location = (x, y, 0)
    t = bpy.data.curves.new(pid, "FONT"); t.body = pid; t.size = 0.14; t.align_x = "CENTER"
    to = bpy.data.objects.new(pid + "_label", t); bpy.context.scene.collection.objects.link(to)
    to.location = (x, y - 0.75, 0.002)
for m in bpy.data.materials:
    h = zlib.crc32(m.name.split(".")[0].encode())
    col = (0.25 + (h & 255) / 400, 0.25 + ((h >> 8) & 255) / 400, 0.25 + ((h >> 16) & 255) / 400, 1)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF") or m.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
    for l in list(b.inputs["Base Color"].links):
        m.node_tree.links.remove(l)
    b.inputs["Base Color"].default_value = col
    for k in ("Metallic", "Roughness", "Alpha"):
        for l in list(b.inputs[k].links):
            m.node_tree.links.remove(l)
    b.inputs["Roughness"].default_value = 0.7
    b.inputs["Metallic"].default_value = 0.0
    b.inputs["Alpha"].default_value = 1.0
    out = next((n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL"), None)
    if out:
        m.node_tree.links.new(b.outputs[0], out.inputs[0])
lm = bpy.data.materials.new("label"); lm.use_nodes = True
lm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.05, 0.05, 0.05, 1)
for o in bpy.data.objects:
    if o.name.endswith("_label"):
        o.data.materials.append(lm)
# a 1.8 m figure at the start
bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.2, depth=1.8, location=(-1.2, 0, 0.9))
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 24
rows = (len(ids) + cols - 1) // cols
sc.render.resolution_x = 1920; sc.render.resolution_y = 1080 if rows <= 5 else 1400
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.7, 0.72, 0.75, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.8
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(sun); sun.data.energy = 3.5
sun.rotation_euler = (math.radians(50), 0, math.radians(30))
bpy.ops.mesh.primitive_plane_add(size=80, location=(5, -5, 0))
g = bpy.context.active_object; gm = bpy.data.materials.new("ground"); gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.55, 0.5, 0.42, 1); g.data.materials.append(gm)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cx = (cols - 1) * sp / 2
cy = -(rows - 1) * sp * 1.25 / 2
cam.data.type = "ORTHO"; cam.data.ortho_scale = max(cols * sp + 1.5, rows * sp * 1.25 * 1920 / sc.render.resolution_y * 0.62)
cam.location = (cx, cy - 9.0, 7.5)
cam.rotation_euler = (Vector((cx, cy, 0.3)) - cam.location).to_track_quat("-Z", "Y").to_euler()
sc.render.filepath = str(HERE / f"review/kit_lod{lod}{('_' + filt.replace(',', '-')) if filt else ''}.png")
bpy.ops.render.render(write_still=True)
