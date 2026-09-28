"""Blender 5.2: fit the depot's Meshy props (meshy/outer-berms-depot-20260927) for Unity.
Uniform scale to the briefed size, origin at the ground-contact centre (sunk slightly so the flat underside beds in),
LOD0 = source geometry, LOD1/LOD2 decimated; exported without images (URP Lit materials are built in Unity from the
maps written by pack_meshy_textures.py). Source GLBs and 4k maps stay untouched.
Run: blender -b --python-exit-code 1 -P prep_meshy_props.py"""
import bpy, json
from pathlib import Path
from mathutils import Matrix
HERE = Path(__file__).resolve().parent
SRC = HERE.parents[1] / "meshy/outer-berms-depot-20260927"
OUT = HERE.parents[1] / "unity/AthenHill/Assets/AthenHill/Art/OuterBermsDepot/Meshy"
OUT.mkdir(parents=True, exist_ok=True)
# name: (source folder, target longest horizontal size m, sink m, lod ratios)
JOBS = {"MX_ScrapHeapA": ("scrap-heap-a", 3.6, .06, [.3, .08]), "MX_ScrapHeapB": ("scrap-heap-b", 3.0, .03, [.3, .08])}
REPORT = {}
for name, (folder, size, sink, ratios) in JOBS.items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(SRC / folder / "model.glb"))
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    for o in bpy.context.selected_objects: o.select_set(False)
    for o in meshes: o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if len(meshes) > 1: bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    for o in list(bpy.context.scene.objects):
        if o != ob: bpy.data.objects.remove(o, do_unlink=True)
    xs = [v.co.x for v in ob.data.vertices]; ys = [v.co.y for v in ob.data.vertices]; zs = [v.co.z for v in ob.data.vertices]
    src_dims = (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
    s = size / max(src_dims[0], src_dims[1])
    ob.data.transform(Matrix.Translation((-(max(xs) + min(xs)) / 2, -(max(ys) + min(ys)) / 2, -min(zs))))
    ob.data.transform(Matrix.Scale(s, 4))
    ob.data.transform(Matrix.Translation((0, 0, -sink)))
    for m in ob.data.materials: m.name = name
    for p in ob.data.polygons: p.use_smooth = True
    ob.name = ob.data.name = name + "_LOD0"
    lods = [ob]
    for i, r in enumerate(ratios, 1):
        c = ob.copy(); c.data = ob.data.copy(); bpy.context.scene.collection.objects.link(c)
        d = c.modifiers.new("d", "DECIMATE"); d.ratio = r
        bpy.context.view_layer.objects.active = c; bpy.ops.object.modifier_apply(modifier="d")
        c.name = c.data.name = f"{name}_LOD{i}"; lods.append(c)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(filepath=str(OUT / f"{name}.glb"), export_format="GLB", use_selection=True, export_yup=True,
                              export_image_format="NONE", export_tangents=True, export_materials="EXPORT", export_apply=True)
    REPORT[name] = {"source": folder, "source_dims_m": [round(d, 3) for d in src_dims], "scale": round(s, 4),
                    "dims_m": [round(d * s, 3) for d in src_dims], "lod_tris": [sum(len(p.vertices) - 2 for p in o.data.polygons) for o in lods]}
    print("prepared", name, REPORT[name], flush=True)
(HERE / "meshy-props.json").write_text(json.dumps(REPORT, indent=1))
