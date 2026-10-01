"""Blender (headless) street-level review of the roof kit in place: the rebuilt shops, the booth, Vanguard Hall and the hill
(their LOD1 GLBs at their saved world transforms) with layout.json's pieces and service lines, rendered from the
cam_rt_* street cameras (1.6 m eye height) - composition and skyline only; lighting and materials are judged in Unity.
Run: $O/blender.sh review_street.py -- [cam,cam,...] [before]      ("before" leaves the roof kit out)
Out: review/street_<cam>[_before].png"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector, Euler

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from review_cams import CAMS
A = ROOT / "unity/AthenHill/Assets/AthenHill/Art"
MODELS = A / "Rooftops/Models"
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
cams = args[0].split(",") if args and args[0] else list(CAMS)
before = len(args) > 1 and args[1] == "before"
layout = json.loads((HERE / "layout.json").read_text())
lines = json.loads((MODELS / "lines.json").read_text())

COL = {"VH_Ashlar": (0.62, 0.48, 0.34), "VH_AshlarRough": (0.55, 0.43, 0.31), "VH_Mortar": (0.5, 0.42, 0.33), "VH_Roof": (0.35, 0.33, 0.3),
       "VH_Steel": (0.5, 0.5, 0.48), "VH_PaintedSteel": (0.33, 0.37, 0.31), "VH_Dark": (0.07, 0.07, 0.07), "VH_Rubber": (0.03, 0.03, 0.03),
       "VH_DoorSteel": (0.3, 0.3, 0.3), "WS_PaintTeal": (0.15, 0.3, 0.31), "WS_PaintOlive": (0.3, 0.32, 0.18), "WS_PaintRed": (0.5, 0.1, 0.07),
       "WS_PaintYellow": (0.75, 0.58, 0.1), "WS_ClothMadder": (0.5, 0.17, 0.12), "SD_Sack": (0.55, 0.43, 0.28), "SD_Rope": (0.7, 0.6, 0.45),
       "RT_Ceramic": (0.85, 0.83, 0.78), "RT_SolarCell": (0.04, 0.06, 0.14), "RT_DewNet": (0.78, 0.8, 0.78), "WS_Corrugated": (0.42, 0.35, 0.3),
       "WS_ContainerRust": (0.45, 0.24, 0.15), "VH_Sand": (0.7, 0.58, 0.42), "VH_PodiumSlab": (0.6, 0.5, 0.38), "WS_Canvas": (0.5, 0.25, 0.17)}


def U(p):
    return Vector((-p[0], -p[2], p[1]))


def place(glb, pos, yaw, name):
    before_ = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(glb))
    roots = [o for o in set(bpy.data.objects) - before_ if o.parent is None]
    for o in roots:
        o.location = U(pos)
        o.rotation_mode = "XYZ"
        o.rotation_euler = Euler((0, 0, math.radians(-yaw)))
        o.name = name
    return roots


bpy.ops.wm.read_factory_settings(use_empty=True)
SHOPS = {"RelayWorks": ((-18.1, 0, -18), 90), "AirWater": ((-18.1, 0, -9), 90), "ToolExchange": ((-18.1, 0, 9), 90),
         "Salvage": ((-18.1, 0, 18), 90), "Finery": ((18.1, 0, -18), -90), "FieldSupply": ((18.1, 0, -9), -90),
         "Repairs": ((18.1, 0, 9), -90), "ThreadHide": ((18.1, 0, 18), -90)}
for k, (p, y) in SHOPS.items():
    place(A / f"WardShops/Models/{k}_LOD1.glb", p, y, k)
place(A / "WardShops/Booth/BasicGeneral_LOD1.glb", (8, 0, 15.1), 0, "BasicGeneral")
place(A / "VanguardHall/Models/VanguardHall_LOD1.glb", (-10, 0, -26.55), 0, "VanguardHall")
place(A / "WardHill/Models/WardHill_LOD1.glb", (0, 0, 0), 0, "WardHill")
if not before:
    for g in layout["groups"]:
        for it in g["items"]:
            if it["sd"]:
                pid = it["id"]
                glb = A / f"StreetDressing/Props/{pid}/{pid}_LOD1.glb"
            else:
                glb = MODELS / f"RT_{it['id']}_LOD0.glb"
            place(glb, it["world"], it["worldYaw"], it["id"])
    for k, e in lines.items():
        place(MODELS / f"RT_{k}_LOD0.glb", e["origin"], 0, k)

for m in bpy.data.materials:
    base = m.name.split(".")[0]
    col = COL.get(base)
    if col is None:
        if base.startswith(("WS_Cloth", "WS_Hide")):
            col = (0.5, 0.3, 0.2)
        elif base.startswith("SD_"):
            continue
        else:
            col = (0.45, 0.43, 0.4)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF") or m.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
    for inp in ("Base Color", "Metallic", "Roughness", "Alpha"):
        for l in list(b.inputs[inp].links):
            m.node_tree.links.remove(l)
    b.inputs["Base Color"].default_value = (*col, 1)
    b.inputs["Roughness"].default_value = 0.65
    b.inputs["Metallic"].default_value = 0.0
    b.inputs["Alpha"].default_value = 0.5 if base == "RT_DewNet" else 1.0
    out = next((n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL"), None)
    if out:
        m.node_tree.links.new(b.outputs[0], out.inputs[0])

sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 16
sc.render.resolution_x = 1600; sc.render.resolution_y = 900
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.68, 0.85, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.6
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(sun); sun.data.energy = 3.0
sun.rotation_euler = (math.radians(35), 0, math.radians(140))
bpy.ops.mesh.primitive_plane_add(size=140, location=(0, 0, -0.01))
g = bpy.context.active_object; gm = bpy.data.materials.new("ground"); gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.62, 0.52, 0.4, 1); g.data.materials.append(gm)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
for name in cams:
    c = CAMS[name]
    cam.location = U(c["pos"])
    tgt = U(c["target"])
    cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.sensor_fit = "VERTICAL"
    cam.data.angle_y = math.radians(c.get("fov", 60))
    sc.render.filepath = str(HERE / f"review/street_{name}{'_before' if before else ''}.png")
    bpy.ops.render.render(write_still=True)
