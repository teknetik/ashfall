"""Blender (5.2) batch conversion of Poly Haven CC0 glTF props into Unity-ready GLBs.

Run:  blender -b --python-exit-code 1 -P convert_polyhaven.py
Each output GLB holds <Name>_LOD0..n meshes (Unity LODGroup is built from the suffix),
origin at the ground contact centre, no embedded images. Materials keep the prefix PH_
and are rebuilt in Unity as URP Lit from the textures written next to the props by
pack_polyhaven_textures.py. Source files stay untouched under polyhaven/models.
"""
import bpy, bmesh, json, math, sys
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SRC = HERE / "polyhaven/models"
OUT = HERE.parents[1] / "unity/AthenHill/Assets/AthenHill/Art/WestGate/Props"
REPORT = {}

# out name: (asset id, [source objects to join, or '*' for all], LOD0 tri target or None, [LOD ratios after LOD0])
JOBS = {
    "PH_JerseyBarrierA": ("concrete_road_barrier", "*", 9000, [.3, .08]),
    "PH_JerseyBarrierB": ("concrete_road_barrier_02", "*", 8000, [.3, .08]),
    "PH_MilitaryCrateA": ("old_military_crate", ["old_military_crate_a", "old_military_crate_lid_a", "old_military_crate_loop_a", "old_military_crate_latch_a", "old_military_crate_cloth_a"], None, [.3]),
    "PH_MilitaryCrateB": ("old_military_crate", ["old_military_crate_b", "old_military_crate_lid_b", "old_military_crate_loop_b", "old_military_crate_latch_b", "old_military_crate_cloth_b"], None, [.3]),
    "PH_WoodenMilitaryCrate": ("wooden_military_crate", "*", 12000, [.25]),
    "PH_AmmoBox": ("ammo_box", "*", None, [.3]),
    "PH_Jerrycan": ("metal_jerrycan_green", "*", 6000, [.25]),
    "PH_BarrelBlue": ("barrel_03", "*", None, [.4]),
    "PH_BarrelRed": ("Barrel_01", "*", None, [.4]),
    "PH_Searchlight": ("portable_searchlight", "*", 9000, [.25]),
    "PH_SecurityLight": ("security_light", "*", None, [.35]),
    "PH_WallLamp": ("industrial_wall_lamp", "*", None, [.35]),
    "PH_Generator": ("portable_generator", "*", 14000, [.25]),
    "PH_AirconRusted": ("exterior_aircon_unit", ["exterior_aircon_unit_rusted"], None, [.3]),
    "PH_PowerBox": ("power_box_01", "*", 9000, [.25]),
    "PH_UtilityBox": ("utility_box_02", "*", None, [.3]),
    "PH_RadioSet": ("vintage_radio_transceiver", "*", 16000, [.25]),
    "PH_MonoblocChair": ("plastic_monobloc_chair_01", "*", None, [.35]),
    "PH_TrashCanRust": ("metal_trash_can", ["metal_trash_can_rust", "metal_trash_can_rust_lid", "metal_trash_can_rust_handle_left", "metal_trash_can_rust_handle_right"], None, [.3]),
    "PH_OldTyre": ("old_tyre", "*", None, [.4]),
    "PH_BoulderA": ("namaqualand_boulder_02", "*", 14000, [.25, .07]),
    "PH_BoulderB": ("namaqualand_boulder_03", "*", 14000, [.25, .07]),
    "PH_BoulderC": ("namaqualand_boulder_04", "*", 14000, [.25, .07]),
    "PH_RockA": ("namaqualand_rocks_01", ["namaqualand_rocks_02_a"], 5000, [.25]),
    "PH_RockB": ("namaqualand_rocks_01", ["namaqualand_rocks_02_b"], 5000, [.25]),
    "PH_RockC": ("namaqualand_rocks_01", ["namaqualand_rocks_02_c"], 5000, [.25]),
    "PH_RockD": ("namaqualand_rocks_01", ["namaqualand_rocks_02_d"], 5000, [.25]),
    "PH_StonesA": ("namaqualand_stones_01", ["namaqualand_stones_01_a"], 3000, [.3]),
    "PH_StonesB": ("namaqualand_stones_01", ["namaqualand_stones_01_c"], 3000, [.3]),
    "PH_StonesC": ("namaqualand_stones_01", ["namaqualand_stones_01_e"], 3000, [.3]),
    "PH_RooibosA": ("wild_rooibos_bush", ["wild_rooibos_bush_a"], None, [.4]),
    "PH_RooibosB": ("wild_rooibos_bush", ["wild_rooibos_bush_b"], None, [.4]),
    "PH_RooibosC": ("wild_rooibos_bush", ["wild_rooibos_bush_c"], None, [.45]),
    "PH_SearsiaSmall": ("searsia_burchellii", ["searsia_burchellii_small_LOD0"], 16000, [.3]),
    "PH_DideltaSmall": ("didelta_spinosa", ["didelta_spinosa_small_LOD0"], 14000, [.3]),
    "PH_DryBranchA": ("dry_branches_medium_01", ["dry_branches_medium_01_a"], None, [.3]),
    "PH_DryBranchB": ("dry_branches_medium_01", ["dry_branches_medium_01_b"], None, [.3]),
    "PH_ToolCart": ("tool_cart", "*", 12000, [.25]),
    "PH_MetalRack": ("worn_metal_rack", "*", None, [.35]),
    "PH_Binoculars": ("binoculars", "*", 4000, []),
    "PH_Clipboard": ("clipboard", "*", 2500, []),
    "PH_PropaneTank": ("propane_tank", "*", None, [.35]),
    "PH_SecurityCamera": ("security_camera_01", "*", 6000, [.3]),
    "PH_HandTruck": ("hand_truck", "*", 8000, [.3]),
}


def tris(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def decimate(obj, ratio):
    m = obj.modifiers.new("dec", "DECIMATE"); m.ratio = max(min(ratio, 1), .002); m.use_collapse_triangulate = True
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=m.name)


def run(out, asset, parts, lod0, ratios):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    gltf = next((SRC / asset).glob("*.gltf"))
    bpy.ops.import_scene.gltf(filepath=str(gltf))
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    keep = meshes if parts == "*" else [o for o in meshes if o.name in parts or o.name.rsplit(".", 1)[0] in parts]
    if not keep:
        raise RuntimeError(f"{out}: no objects matched {parts}; have {[o.name for o in meshes]}")
    for o in meshes:
        if o not in keep:
            bpy.data.objects.remove(o, do_unlink=True)
    # bake parent transforms, join
    bpy.ops.object.select_all(action="DESELECT")
    for o in keep:
        o.select_set(True)
    bpy.context.view_layer.objects.active = keep[0]
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if len(keep) > 1:
        bpy.ops.object.join()
    base = bpy.context.view_layer.objects.active
    for o in list(bpy.context.scene.objects):
        if o != base:
            bpy.data.objects.remove(o, do_unlink=True)
    # origin at ground contact centre (Blender Z up)
    ws = [base.matrix_world @ v.co for v in base.data.vertices]
    minz = min(v.z for v in ws); cx = (min(v.x for v in ws) + max(v.x for v in ws)) / 2; cy = (min(v.y for v in ws) + max(v.y for v in ws)) / 2
    base.data.transform(__import__("mathutils").Matrix.Translation((-cx, -cy, -minz)))
    base.location = (0, 0, 0)
    for m in base.data.materials:
        if m and not m.name.startswith("PH_"):
            m.name = "PH_" + m.name
    src_tris = tris(base)
    if lod0 and src_tris > lod0 * 1.15:
        decimate(base, lod0 / src_tris)
    base.name = base.data.name = out + "_LOD0"
    lods = [base]
    for i, r in enumerate(ratios, 1):
        c = base.copy(); c.data = base.data.copy(); bpy.context.scene.collection.objects.link(c)
        decimate(c, r); c.name = c.data.name = f"{out}_LOD{i}"; lods.append(c)
    for o in lods:
        for p in o.data.polygons:
            p.use_smooth = True
    dims = [round(d, 3) for d in base.dimensions]
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(filepath=str(OUT / f"{out}.glb"), export_format="GLB", use_selection=True,
                              export_yup=True, export_image_format="NONE", export_tangents=True,
                              export_materials="EXPORT", export_apply=True)
    REPORT[out] = {"asset": asset, "parts": parts, "source_tris": src_tris, "lod_tris": [tris(o) for o in lods],
                   "dimensions_blender_xyz_m": dims, "materials": sorted({m.name for o in lods for m in o.data.materials if m})}
    print("converted", out, REPORT[out]["lod_tris"], dims, flush=True)


only = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
for out, (asset, parts, lod0, ratios) in JOBS.items():
    if only and out not in only:
        continue
    run(out, asset, parts, lod0, ratios)
rp = HERE / "polyhaven-conversion.json"
old = json.loads(rp.read_text()) if rp.exists() else {}
old.update(REPORT)
rp.write_text(json.dumps(old, indent=1))
