"""Blender (headless) review of the roof kit: every object's LOD (default 0) in a labelled line-up with a 1.8 m figure,
plausible flat colours per material (shape, scale, orientation and grounding check; materials are judged in Unity).
Run: $O/blender.sh review_kit.py -- [lod] [id,id,...] [view: front|back|top]
Out: review/kit_lod<lod>[_<view>].png"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MODELS = ROOT / "unity/AthenHill/Assets/AthenHill/Art/Rooftops/Models"
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
lod = int(args[0]) if args else 0
only = args[1].split(",") if len(args) > 1 and args[1] else None
view = args[2] if len(args) > 2 else "front"
kit = json.loads((MODELS / "kit.json").read_text())

COL = {"VH_Steel": (0.55, 0.55, 0.53), "VH_PaintedSteel": (0.36, 0.40, 0.33), "VH_Dark": (0.08, 0.08, 0.08),
       "VH_Rubber": (0.03, 0.03, 0.03), "WS_PaintTeal": (0.17, 0.33, 0.34), "WS_PaintOlive": (0.33, 0.35, 0.2),
       "WS_PaintRed": (0.55, 0.12, 0.08), "WS_PaintYellow": (0.8, 0.62, 0.12), "WS_ClothMadder": (0.55, 0.2, 0.14),
       "SD_Sack": (0.6, 0.47, 0.3), "SD_Rope": (0.75, 0.66, 0.48), "RT_Ceramic": (0.85, 0.83, 0.78),
       "RT_SolarCell": (0.05, 0.08, 0.18), "RT_DewNet": (0.8, 0.82, 0.8)}

bpy.ops.wm.read_factory_settings(use_empty=True)
ids = [k for k in kit if (only is None or k in only)]
# tall pieces at the back row
tall = [k for k in ids if kit[k]["size"][1] > 3.2]
low = [k for k in ids if k not in tall]
rows = [low[:8], low[8:], tall]
rows = [r for r in rows if r]
placed = []
y = 0.0
for r_i, row in enumerate(rows):
    x = 0.0
    depth = max(kit[k]["size"][2] for k in row)
    for k in row:
        w = max(kit[k]["size"][0], 0.8)
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=str(MODELS / f"RT_{k}_LOD{lod}.glb"))
        for o in set(bpy.data.objects) - before:
            if o.parent is None:
                o.location = (x + w / 2, y, 0)          # Blender: x = -unity x (glTF mirror); fine for a review
        t = bpy.data.curves.new(k, "FONT"); t.body = k; t.size = 0.22; t.align_x = "CENTER"
        to = bpy.data.objects.new(k + "_label", t); bpy.context.scene.collection.objects.link(to)
        to.location = (x + w / 2, y + depth / 2 + 0.35, 0.002)
        placed.append((k, x + w / 2, y))
        x += w + 0.7
    y += depth + 1.4
xmax = max(p[1] for p in placed) + 1.5
for m in bpy.data.materials:
    base = m.name.split(".")[0]
    col = COL.get(base, (1.0, 0.0, 1.0))
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF") or m.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
    for inp in ("Base Color", "Metallic", "Roughness", "Alpha"):
        for l in list(b.inputs[inp].links):
            m.node_tree.links.remove(l)
    b.inputs["Base Color"].default_value = (*col, 1)
    b.inputs["Roughness"].default_value = 0.6
    b.inputs["Metallic"].default_value = 0.0
    b.inputs["Alpha"].default_value = 0.55 if base == "RT_DewNet" else 1.0
    out = next((n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL"), None)
    if out:
        m.node_tree.links.new(b.outputs[0], out.inputs[0])
lm = bpy.data.materials.new("label"); lm.use_nodes = True
lm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.02, 0.02, 0.02, 1)
for o in bpy.data.objects:
    if o.name.endswith("_label"):
        o.data.materials.append(lm)
bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.2, depth=1.8, location=(-0.8, 0, 0.9))
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 20
sc.render.resolution_x = 1920; sc.render.resolution_y = 1080
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.45, 0.55, 0.7, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.35
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(sun); sun.data.energy = 2.6
sun.rotation_euler = (math.radians(48), 0, math.radians(35))
bpy.ops.mesh.primitive_plane_add(size=120, location=(xmax / 2, y / 2, 0))
g = bpy.context.active_object; gm = bpy.data.materials.new("ground"); gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.55, 0.5, 0.42, 1); g.data.materials.append(gm)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 28
cx, cy = xmax / 2, y / 2
span = max(xmax, y)
if view == "front":       # glTF front (+Z unity) is -Y blender
    cam.location = (cx - 0.15 * span, cy - 0.75 * span - 2.0, 1.6 + 0.12 * span)
elif view == "back":
    cam.location = (cx + 2.0, y * 1.9 + 6.5, 3.6)
else:
    cam.location = (cx, cy - 4.0, 16.0)
aim_z = float(args[3]) if len(args) > 3 else 1.2
cam.rotation_euler = (Vector((cx, cy, aim_z)) - cam.location).to_track_quat("-Z", "Y").to_euler()
sc.render.filepath = str(HERE / f"review/kit_lod{lod}_{view}{('_' + '-'.join(only)) if only else ''}.png")
bpy.ops.render.render(write_still=True)
