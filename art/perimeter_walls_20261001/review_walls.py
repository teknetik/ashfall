"""Blender (headless) review renders of the perimeter wall kit: a run of modules laid out as in the game, Cycles CPU, flat
colours x vertex tint / sky occlusion, runoff (UV1.x) and rust (UV2.x) shown as darkening. Source check only; the game's
materials and lighting are judged in Unity.

Run: blender -b --factory-startup -P review_walls.py -- <KIND> <run name> [--lod 0] [--views a,b] [--mods id,id,...]
"""
import bpy, math, sys, json
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MODELS = ROOT / "unity/AthenHill/Assets/AthenHill/Art/PerimeterWalls/Models"
sys.path.insert(0, str(HERE))
import pw_layout as PL

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["NS", "run"]
kind, runname = argv[0], argv[1]
lod = int(argv[argv.index("--lod") + 1]) if "--lod" in argv else 0
views = argv[argv.index("--views") + 1].split(",") if "--views" in argv else []
T = PL.KINDS[kind]["T"]
RUNS = {
    "NS": ["PW_NS_fill_4p00_se", "PW_NS_intact_a_7p00", "PW_NS_merlons_7p00", "PW_NS_impact_7p00", "PW_NS_collapse_7p00",
           "PW_NS_repair_7p00", "PW_NS_collapse_n_7p00", "PW_NS_intact_c_7p00", "PW_NS_fill_4p00_ee"],
    "EX": ["PW_EX_fill_1p20_se", "PW_EX_intact_a_5p00", "PW_EX_merlons_5p00", "PW_EX_intact_b_5p00", "PW_EX_repair_5p00",
           "PW_EX_impact_5p00", "PW_EX_siege_4p10", "PW_EX_gate_1p60_sn", "PW_EX_siege_5p40_sn", "PW_EX_fill_2p90_sn_ee"],
    "BW": ["PW_BW_fill_4p40_sn", "PW_BW_intact_a_5p00", "PW_BW_coping_5p00", "PW_BW_impact_5p00", "PW_BW_breach_5p00",
           "PW_BW_collapse_5p00", "PW_BW_repair_5p00", "PW_BW_intact_b_5p00", "PW_BW_intact_c_5p00", "PW_BW_fill_1p50"],
}
mods = argv[argv.index("--mods") + 1].split(",") if "--mods" in argv else RUNS[kind]


def U(p):
    return Vector((-p[0], -p[2], p[1]))


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(MODELS / f"PW_{kind}_LOD{lod}.glb"))
objs = {o.name: o for o in bpy.data.objects if o.type == "MESH"}
specs = PL.modules()
# lay the run out along Unity +X (city face +Z) from x = 0
x = 0.0
keep = set()
starts = {}
for m in mods:
    L = specs[m]["length"]
    starts[m] = x
    for name, o in objs.items():
        if name.startswith(m + "_") and "_Col" not in name:
            o2 = o.copy()
            o2.data = o.data
            o2.location = U((x, 0, 0))
            bpy.context.scene.collection.objects.link(o2)
            keep.add(o2.name)
    x += L
for o in list(bpy.data.objects):
    if o.type == "MESH" and o.name not in keep:
        bpy.data.objects.remove(o, do_unlink=True)
run_len = x
COL = {"VH_Ashlar": (0.62, 0.5, 0.36), "VH_AshlarRough": (0.55, 0.45, 0.33), "VH_Mortar": (0.42, 0.37, 0.3), "VH_PodiumSlab": (0.6, 0.52, 0.4),
       "VH_Sand": (0.72, 0.6, 0.44), "VH_Steel": (0.25, 0.22, 0.2), "VH_PaintedSteel": (0.2, 0.26, 0.24), "VH_Dark": (0.03, 0.03, 0.03),
       "PW_Hesco": (0.5, 0.45, 0.33), "SD_Sack": (0.55, 0.42, 0.26), "SD_ScrapSheet": (0.32, 0.36, 0.28)}
MASONRY = ("VH_Ashlar", "VH_AshlarRough", "VH_Mortar", "VH_PodiumSlab")
for m in bpy.data.materials:
    nm = m.name.split(".")[0]
    base = COL.get(nm, (0.35, 0.4, 0.2))
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.85
    if nm in MASONRY:
        attr = nt.nodes.new("ShaderNodeVertexColor"); attr.layer_name = "Color"
        mul = nt.nodes.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs[0].default_value = 1.0
        mul.inputs[6].default_value = (*base, 1)
        sc = nt.nodes.new("ShaderNodeVectorMath"); sc.operation = "SCALE"; sc.inputs[3].default_value = 2.0
        nt.links.new(attr.outputs["Color"], sc.inputs[0])
        nt.links.new(sc.outputs[0], mul.inputs[7])
        ao = nt.nodes.new("ShaderNodeMix"); ao.data_type = "RGBA"; ao.blend_type = "MULTIPLY"; ao.inputs[0].default_value = 1.0
        nt.links.new(mul.outputs[2], ao.inputs[6])
        nt.links.new(attr.outputs["Alpha"], ao.inputs[7])
        # runoff (UV1.x) and rust (UV2.x) as darkening / warm stain
        uvw = nt.nodes.new("ShaderNodeUVMap"); uvw.uv_map = "Wear"
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(uvw.outputs[0], sep.inputs[0])
        run = nt.nodes.new("ShaderNodeMix"); run.data_type = "RGBA"; run.blend_type = "MULTIPLY"
        nt.links.new(sep.outputs[0], run.inputs[0])
        nt.links.new(ao.outputs[2], run.inputs[6])
        run.inputs[7].default_value = (0.5, 0.46, 0.4, 1)
        uvr = nt.nodes.new("ShaderNodeUVMap"); uvr.uv_map = "Rust"
        sep2 = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(uvr.outputs[0], sep2.inputs[0])
        rust = nt.nodes.new("ShaderNodeMix"); rust.data_type = "RGBA"; rust.blend_type = "MULTIPLY"
        nt.links.new(sep2.outputs[0], rust.inputs[0])
        nt.links.new(run.outputs[2], rust.inputs[6])
        rust.inputs[7].default_value = (0.62, 0.38, 0.24, 1)
        # battle damage (UV2.y): darker speckle
        dmg = nt.nodes.new("ShaderNodeMix"); dmg.data_type = "RGBA"; dmg.blend_type = "MULTIPLY"
        nt.links.new(sep2.outputs[1], dmg.inputs[0])
        nt.links.new(rust.outputs[2], dmg.inputs[6])
        dmg.inputs[7].default_value = (0.72, 0.68, 0.64, 1)
        nt.links.new(dmg.outputs[2], bsdf.inputs["Base Color"])
    else:
        bsdf.inputs["Base Color"].default_value = (*base, 1)
        if nm in ("VH_Steel",):
            bsdf.inputs["Metallic"].default_value = 0.8
    nt.links.new(bsdf.outputs[0], out.inputs[0])
sc_ = bpy.context.scene
sc_.render.engine = "CYCLES"; sc_.cycles.device = "CPU"; sc_.cycles.samples = 40
sc_.render.resolution_x = 1280; sc_.render.resolution_y = 720
w = bpy.data.worlds.new("w"); sc_.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.62, 0.72, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.8
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc_.collection.objects.link(sun); sun.data.energy = 4.0; sun.data.angle = 0.02
d = Vector((0.45, -0.7, 0.55))    # sun from the city side, high
sun.rotation_euler = U(d).to_track_quat("-Z", "Y").to_euler()
bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, -0.003))
g = bpy.context.active_object; gm = bpy.data.materials.new("ground"); gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.5, 0.42, 0.32, 1); g.data.materials.append(gm)
# 1.8 m person for scale
bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.22, depth=1.8, location=U((starts[mods[1]] + 1.0, 0.9, T / 2 + 1.2)))
pm = bpy.data.materials.new("person"); pm.use_nodes = True; pm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.2, 0.35, 0.6, 1)
bpy.context.active_object.data.materials.append(pm)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc_.collection.objects.link(cam); sc_.camera = cam
H = PL.KINDS[kind]["H"]
VIEWS = {"wide": ((run_len * 0.5, H * 0.9, T / 2 + run_len * 0.42), (run_len * 0.5, H * 0.45, 0), 55),
         "outer": ((run_len * 0.45, 1.65, -T / 2 - 12), (run_len * 0.45, H * 0.4, 0), 60)}
for m in mods:
    x0 = starts[m]; L = specs[m]["length"]
    VIEWS["eye_" + m] = ((x0 + L * 0.5 + 2.5, 1.65, T / 2 + 5.5), (x0 + L * 0.5, H * 0.45, T / 2), 60)
    VIEWS["top_" + m] = ((x0 + L * 0.5 + 3, H + 5, T / 2 + 7), (x0 + L * 0.5, H * 0.7, 0), 55)
    VIEWS["out_" + m] = ((x0 + L * 0.5 - 2.0, 1.65, -T / 2 - 5.5), (x0 + L * 0.5, H * 0.45, -T / 2), 60)
outdir = HERE / "review" / f"{runname}"
outdir.mkdir(parents=True, exist_ok=True)
for name, (pos, tgt, fov) in VIEWS.items():
    if views and not any(name == v or (v.endswith("*") and name.startswith(v[:-1])) for v in views):
        continue
    cam.location = U(pos); cam.data.angle = math.radians(fov)
    cam.rotation_euler = (U(tgt) - U(pos)).to_track_quat("-Z", "Y").to_euler()
    sc_.render.filepath = str(outdir / f"{kind}_L{lod}_{name}.png")
    bpy.ops.render.render(write_still=True)
    print("rendered", name, flush=True)
