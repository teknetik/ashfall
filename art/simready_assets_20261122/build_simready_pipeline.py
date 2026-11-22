"""Local Blender 5.2 pipeline for NVIDIA SimReady Central assets -> Ashfall (Ward / Athen Hill).

Runs inside Blender 5.2 LTS headless:
    env -i HOME=$HOME PATH=/usr/bin:/bin /Applications/Blender.app/Contents/MacOS/Blender \
        -b --factory-startup --python-exit-code 1 -P build_simready_pipeline.py [-- asset_id ...]

For each downloaded asset in raw/<id>/:
1. Inspects the root USD stage with pxr.Usd to extract SimReady_Metadata (mass, category,
   qcode, rigid_body_count, author, asset_license, joints) and Physics / Grasp prims.
2. Imports the visual USD stage via bpy.ops.wm.usd_import(import_guide=False, import_proxy=False,
   import_render=True, import_visible_only=True, apply_unit_conversion_scale=True).
3. Cleans and normalises all meshes into metric ground-centred coordinates (footprint centre at X=0, Y=0,
   base at Z=0).
4. Exports two ready-to-cherry-pick representations into assets/<id>/:
   - <id>_parts.glb: preserves every separable sub-mesh node (<id>_<part_name>) so Claude / Codex can
     pull multi-part tools, clamps, vises, latches, and components directly into the Crafting Studio
     (`art/crafting_studio_20261121`) or animate hinged lids/jaws.
   - <id>_LOD0.glb, <id>_LOD1.glb, <id>_LOD2.glb: joined static prop meshes with collapse-decimated LODs
     and embedded PBR textures (glTF baseColor, normal, and packed ORM with occlusionTexture hooked up)
     plus standalone URP Lit textures (<mat>_BaseMap.png, <mat>_Normal.png, <mat>_Mask.png) in
     assets/<id>/textures/ ready for Unity URP Lit or glTFast.
5. Writes per-asset assets/<id>/meta.json and master catalog.json + CATALOG.md so Claude can easily
   query what each asset is, its exact dimensions, triangle counts, separable parts, and where in Ward /
   Outer Berms / Crafting Studio it can be used.
"""
import json, math, os, re, shutil, sys
from pathlib import Path
import numpy as np
import bpy
import bmesh
from mathutils import Vector, Matrix
from pxr import Usd, UsdGeom, UsdPhysics

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from catalog_defs import ASSETS

RAW = HERE / "raw"
OUT = HERE / "assets"

LOD0_MAX_TRIS = 30000
LOD_RATIOS = (0.25, 0.08)
LOD_MINS = (400, 120)


def clean_name(s):
    s = re.sub(r"[^a-zA-Z0-9_]+", "_", s).strip("_").lower()
    return s or "part"


def count_tris(me):
    return sum(max(0, len(p.vertices) - 2) for p in me.polygons)


def find_root_usd(adir, bom_items):
    usd_files = [
        i["relative_path"]
        for i in bom_items
        if i["relative_path"].endswith((".usd", ".usda", ".usdc"))
        and "/payloads/" not in i["relative_path"]
        and "/forgecad/" not in i["relative_path"]
        and "/runnables/" not in i["relative_path"]
        and "/layers/" not in i["relative_path"]
    ]
    if not usd_files:
        usd_files = [i["relative_path"] for i in bom_items if i["relative_path"].endswith((".usd", ".usda", ".usdc"))]
    usd_files.sort(key=lambda p: (len(Path(p).parts), len(p)))
    return adir / usd_files[0]


def inspect_usd_stage(usd_path):
    stage = Usd.Stage.Open(str(usd_path))
    root_layer = stage.GetRootLayer()
    cld = dict(root_layer.customLayerData or {})
    sr = dict(cld.get("SimReady_Metadata") or {})

    def pick(key, default=None):
        v = sr.get(key)
        if v is None:
            v = cld.get(key, default)
        if hasattr(v, "__iter__") and not isinstance(v, (str, dict, list)):
            return [round(float(x), 5) for x in v]
        return v

    joints = []
    grasps = []
    rigid_bodies = []
    for prim in stage.Traverse():
        tname = prim.GetTypeName()
        if "Joint" in tname:
            joints.append({"name": prim.GetName(), "path": str(prim.GetPath()), "type": tname})
        if prim.HasAPI(UsdPhysics.RigidBodyAPI):
            rigid_bodies.append(str(prim.GetPath()))
        if prim.GetName().startswith("grasp_") and prim.GetTypeName() == "Xform":
            loc = prim.GetAttribute("intersection_location")
            obj = prim.GetAttribute("intersection_object")
            if loc and loc.Get() is not None:
                grasps.append({
                    "name": prim.GetName(),
                    "target_object": str(obj.Get()) if obj and obj.Get() else None,
                    "location": [round(float(x), 4) for x in loc.Get()],
                })

    return {
        "usd_file": usd_path.name,
        "meters_per_unit": float(UsdGeom.GetStageMetersPerUnit(stage)),
        "up_axis": str(UsdGeom.GetStageUpAxis(stage)),
        "author": str(pick("author", "unknown")),
        "simready_category": str(pick("category", pick("asset_type", "prop"))),
        "simready_license": str(pick("asset_license", "CC-BY-4.0")),
        "wikidata_qcode": str(pick("qcode", "")) or None,
        "mass_kg": round(float(pick("mass", 0.0) or 0.0), 4) if pick("mass") is not None else None,
        "rigid_body_count": int(pick("rigid_body_count", len(rigid_bodies)) or len(rigid_bodies)),
        "joints": joints,
        "grasp_points": grasps[:8],
    }


def trace_socket_image(sock):
    stack = [l.from_node for l in sock.links]
    visited = set()
    while stack:
        n = stack.pop()
        if n in visited:
            continue
        visited.add(n)
        if n.type == "TEX_IMAGE" and n.image:
            return n.image, n
        for inp in n.inputs:
            stack.extend(l.from_node for l in inp.links)
    return None, None


def get_pixels_2d(img, target_w, target_h):
    if img.size[0] == 0 or img.size[1] == 0:
        return None
    if img.size[0] != target_w or img.size[1] != target_h:
        cp = img.copy()
        cp.scale(target_w, target_h)
        arr = np.empty(target_w * target_h * cp.channels, dtype=np.float32)
        cp.pixels.foreach_get(arr)
        arr = arr.reshape((target_h, target_w, cp.channels))
        bpy.data.images.remove(cp)
        return arr
    arr = np.empty(target_w * target_h * img.channels, dtype=np.float32)
    img.pixels.foreach_get(arr)
    return arr.reshape((target_h, target_w, img.channels))


def save_float_image(name, filepath, arr_rgba, colorspace="Non-Color"):
    h, w, c = arr_rgba.shape
    if c == 3:
        alpha = np.ones((h, w, 1), dtype=np.float32)
        arr_rgba = np.concatenate([arr_rgba, alpha], axis=-1)
    img = bpy.data.images.new(name=name, width=w, height=h, alpha=(c == 4), float_buffer=False)
    img.colorspace_settings.name = colorspace
    img.pixels.foreach_set(np.clip(arr_rgba, 0.0, 1.0).ravel())
    img.filepath_raw = str(filepath)
    img.file_format = "PNG"
    img.save()
    return img


def process_materials(aid, out_tex_dir, max_dim_m):
    """Standardize every material on the active objects for both glTF 2.0 (ORM + AO) and Unity URP Lit (MaskMap)."""
    out_tex_dir.mkdir(parents=True, exist_ok=True)
    max_res = 2048 if max_dim_m >= 0.75 else 1024
    mat_records = {}

    used_mats = []
    for o in bpy.data.objects:
        if o.type == "MESH":
            for m in o.data.materials:
                if m and m not in used_mats:
                    used_mats.append(m)

    ao_group = bpy.data.node_groups.get("glTF Material Output")
    if not ao_group:
        ao_group = bpy.data.node_groups.new("glTF Material Output", "ShaderNodeTree")
        ao_group.interface.new_socket("Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")

    for m in used_mats:
        m_clean = f"SR_{aid}_{clean_name(m.name)}"
        m.name = m_clean
        nt = m.node_tree
        if not nt:
            continue
        bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if not bsdf:
            continue

        base_img, _ = trace_socket_image(bsdf.inputs["Base Color"])
        metal_img, _ = trace_socket_image(bsdf.inputs["Metallic"])
        rough_img, _ = trace_socket_image(bsdf.inputs["Roughness"])
        norm_img, _ = trace_socket_image(bsdf.inputs["Normal"])

        # Determine working resolution
        imgs = [x for x in (base_img, metal_img, rough_img, norm_img) if x is not None and x.size[0] > 0]
        if imgs:
            w = min(max_res, max(x.size[0] for x in imgs))
            h = min(max_res, max(x.size[1] for x in imgs))
        else:
            w = h = 0

        rec = {
            "material_name": m_clean,
            "base_color_factor": [round(float(x), 4) for x in bsdf.inputs["Base Color"].default_value[:4]],
            "metallic_factor": round(float(bsdf.inputs["Metallic"].default_value), 4),
            "roughness_factor": round(float(bsdf.inputs["Roughness"].default_value), 4),
            "textures": {},
        }

        # 1. BaseMap
        if base_img and w > 0:
            base_arr = get_pixels_2d(base_img, w, h)
            base_path = out_tex_dir / f"{m_clean}_BaseMap.png"
            new_base = save_float_image(f"{m_clean}_BaseMap", base_path, base_arr, "sRGB")
            rec["textures"]["base_map"] = f"textures/{base_path.name}"
            rec["textures"]["resolution"] = [w, h]
        else:
            new_base = None

        # 2. Normal
        if norm_img and w > 0:
            norm_arr = get_pixels_2d(norm_img, w, h)
            norm_path = out_tex_dir / f"{m_clean}_Normal.png"
            new_norm = save_float_image(f"{m_clean}_Normal", norm_path, norm_arr, "Non-Color")
            rec["textures"]["normal_map"] = f"textures/{norm_path.name}"
        else:
            new_norm = None

        # 3. ORM (glTF: R=AO, G=Roughness, B=Metallic) & Unity URP Mask (R=Metallic, G=AO, B=0, A=1-Roughness)
        if (metal_img or rough_img) and w > 0:
            if metal_img and rough_img and metal_img == rough_img:
                # Packed ORM map (R=AO, G=Roughness, B=Metallic)
                orm_src = get_pixels_2d(metal_img, w, h)
                ao_ch = orm_src[..., 0]
                rough_ch = orm_src[..., 1]
                metal_ch = orm_src[..., 2]
            else:
                ao_ch = np.ones((h, w), dtype=np.float32)
                if rough_img:
                    r_arr = get_pixels_2d(rough_img, w, h)
                    rough_ch = r_arr[..., 1] if (r_arr.shape[-1] >= 3 and "orm" in rough_img.name.lower()) else r_arr[..., 0]
                else:
                    rough_ch = np.full((h, w), float(bsdf.inputs["Roughness"].default_value), dtype=np.float32)
                if metal_img:
                    m_arr = get_pixels_2d(metal_img, w, h)
                    metal_ch = m_arr[..., 2] if (m_arr.shape[-1] >= 3 and "orm" in metal_img.name.lower()) else m_arr[..., 0]
                else:
                    metal_ch = np.full((h, w), float(bsdf.inputs["Metallic"].default_value), dtype=np.float32)

            orm_rgba = np.stack([ao_ch, rough_ch, metal_ch, np.ones_like(ao_ch)], axis=-1)
            orm_path = out_tex_dir / f"{m_clean}_ORM.png"
            new_orm = save_float_image(f"{m_clean}_ORM", orm_path, orm_rgba, "Non-Color")

            urp_mask = np.stack([metal_ch, ao_ch, np.zeros_like(ao_ch), 1.0 - rough_ch], axis=-1)
            mask_path = out_tex_dir / f"{m_clean}_Mask.png"
            mask_img = save_float_image(f"{m_clean}_Mask", mask_path, urp_mask, "Non-Color")
            bpy.data.images.remove(mask_img)

            rec["textures"]["gltf_orm_map"] = f"textures/{orm_path.name}"
            rec["textures"]["unity_urp_mask_map"] = f"textures/{mask_path.name}"
        else:
            new_orm = None

        # Rebuild clean glTF-compliant node tree for this material
        for n in list(nt.nodes):
            if n not in (bsdf,) and n.type != "OUTPUT_MATERIAL":
                nt.nodes.remove(n)

        if new_base:
            tn = nt.nodes.new("ShaderNodeTexImage")
            tn.image = new_base
            nt.links.new(tn.outputs["Color"], bsdf.inputs["Base Color"])
            bsdf.inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1.0)

        if new_orm:
            tn = nt.nodes.new("ShaderNodeTexImage")
            tn.image = new_orm
            sep = nt.nodes.new("ShaderNodeSeparateColor")
            nt.links.new(tn.outputs["Color"], sep.inputs["Color"])
            nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
            nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
            gn = nt.nodes.new("ShaderNodeGroup")
            gn.node_tree = ao_group
            nt.links.new(sep.outputs["Red"], gn.inputs["Occlusion"])
            bsdf.inputs["Roughness"].default_value = 1.0
            bsdf.inputs["Metallic"].default_value = 1.0

        if new_norm:
            tn = nt.nodes.new("ShaderNodeTexImage")
            tn.image = new_norm
            nm = nt.nodes.new("ShaderNodeNormalMap")
            nt.links.new(tn.outputs["Color"], nm.inputs["Color"])
            nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])

        mat_records[m_clean] = rec

    return mat_records


def filter_visual_meshes():
    meshes = []
    for o in list(bpy.data.objects):
        if o.type != "MESH":
            continue
        nl = o.name.lower()
        if any(w in nl for w in ("collision", "collider", "physx", "proxy", "guide", "grasp_identifier")):
            continue
        if len(o.data.polygons) == 0:
            continue
        meshes.append(o)
    return meshes


def export_glb(objects, filepath):
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    filepath.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(filepath),
        export_format="GLB",
        use_selection=True,
        export_yup=True,
        export_tangents=True,
        export_normals=True,
        export_apply=True,
        export_materials="EXPORT",
        export_image_format="AUTO",
    )


def decimate_object(ob, ratio, min_tris, new_name):
    me = ob.data.copy()
    c = bpy.data.objects.new(new_name, me)
    bpy.context.scene.collection.objects.link(c)
    t0 = count_tris(me)
    r = max(ratio, min(1.0, min_tris / max(1, t0)))
    if r < 0.995:
        for o in bpy.context.selected_objects:
            o.select_set(False)
        c.select_set(True)
        bpy.context.view_layer.objects.active = c
        mod = c.modifiers.new("dec", "DECIMATE")
        mod.ratio = r
        mod.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier="dec")
    c.data.name = new_name
    return c


def process_one_asset(entry):
    aid = entry["id"]
    adir = RAW / aid
    bom_path = adir / ".metadata/com.nvidia.simready.packaging.bom.json"
    pkg_path = adir / "com.nvidia.simready.packaging.json"
    if not bom_path.exists():
        raise FileNotFoundError(f"Missing BOM for {aid}: run fetch_simready.py first")

    bom = json.loads(bom_path.read_text())
    pkg = json.loads(pkg_path.read_text()) if pkg_path.exists() else {}
    root_usd = find_root_usd(adir, bom.get("items", []))
    usd_info = inspect_usd_stage(root_usd)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.usd_import(
        filepath=str(root_usd),
        import_cameras=False,
        import_curves=False,
        import_lights=False,
        import_materials=True,
        import_meshes=True,
        import_volumes=False,
        import_shapes=False,
        import_skeletons=False,
        import_guide=False,
        import_proxy=False,
        import_render=True,
        import_visible_only=True,
        support_scene_instancing=False,
        apply_unit_conversion_scale=True,
    )

    meshes = filter_visual_meshes()
    if not meshes:
        raise RuntimeError(f"No visual meshes found in {root_usd}")

    # Unparent and bake world transforms on each part mesh
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for o in meshes:
        if o.data.users > 1:
            o.data = o.data.copy()
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mw
        if o.data.shape_keys:
            o.shape_key_clear()
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # Remove non-mesh empties/lights
    for o in list(bpy.data.objects):
        if o not in meshes:
            bpy.data.objects.remove(o, do_unlink=True)

    # Compute overall bounding box in Blender Z-up metres
    all_verts = [v.co for o in meshes for v in o.data.vertices]
    mn = Vector((min(v.x for v in all_verts), min(v.y for v in all_verts), min(v.z for v in all_verts)))
    mx = Vector((max(v.x for v in all_verts), max(v.y for v in all_verts), max(v.z for v in all_verts)))
    shift = Vector((-(mn.x + mx.x) / 2.0, -(mn.y + mx.y) / 2.0, -mn.z))

    # Shift all part meshes so the assembly footprint centre is at (0,0,0) and base rests on Z=0
    for o in meshes:
        o.data.transform(Matrix.Translation(shift))
        o.data.update()

    # Dimensions in Unity axes (X width, Y height = Blender Z, Z depth = Blender Y)
    size_unity_m = [round(float(mx.x - mn.x), 4), round(float(mx.z - mn.z), 4), round(float(mx.y - mn.y), 4)]
    max_dim_m = max(size_unity_m)

    out_dir = OUT / aid
    out_dir.mkdir(parents=True, exist_ok=True)

    # Copy thumbnail if available
    thumbs = [
        adir / i["relative_path"]
        for i in bom.get("items", [])
        if "/.thumbs/" in i["relative_path"] and (adir / i["relative_path"]).exists()
    ]
    thumb_rel = None
    if thumbs:
        thumbs.sort(key=lambda p: (0 if p.name.endswith("_thumbnail.png") else 1, -p.stat().st_size))
        shutil.copyfile(thumbs[0], out_dir / "thumbnail.png")
        thumb_rel = f"assets/{aid}/thumbnail.png"

    # Process materials once (shared by parts and joined LODs)
    mat_records = process_materials(aid, out_dir / "textures", max_dim_m)

    # Record separable parts & normalize part names
    used_names = set()
    parts_meta = []
    source_total_tris = 0
    for o in sorted(meshes, key=lambda x: x.name):
        base_pname = clean_name(o.name)
        if base_pname.startswith(clean_name(aid) + "_"):
            pname = base_pname
        else:
            pname = f"{clean_name(aid)}_{base_pname}"
        idx = 2
        orig_pname = pname
        while pname in used_names:
            pname = f"{orig_pname}_{idx}"
            idx += 1
        used_names.add(pname)
        o.name = pname
        o.data.name = pname

        p_verts = [v.co for v in o.data.vertices]
        if p_verts:
            p_mn = Vector((min(v.x for v in p_verts), min(v.y for v in p_verts), min(v.z for v in p_verts)))
            p_mx = Vector((max(v.x for v in p_verts), max(v.y for v in p_verts), max(v.z for v in p_verts)))
            p_size_mm = [
                round(float(p_mx.x - p_mn.x) * 1000.0, 1),
                round(float(p_mx.z - p_mn.z) * 1000.0, 1),
                round(float(p_mx.y - p_mn.y) * 1000.0, 1),
            ]
        else:
            p_size_mm = [0.0, 0.0, 0.0]

        ptris = count_tris(o.data)
        source_total_tris += ptris
        parts_meta.append({
            "node": pname,
            "triangles": ptris,
            "vertices": len(o.data.vertices),
            "size_mm": p_size_mm,
            "materials": [m.name for m in o.data.materials if m],
        })

    # If the total triangle count across parts is huge (> 60,000), mildly decimate ultra-dense parts in _parts.glb
    if source_total_tris > 60000:
        scale_factor = 45000.0 / source_total_tris
        for o, pm in zip(sorted(meshes, key=lambda x: x.name), parts_meta):
            if pm["triangles"] > 4000:
                r = max(0.15, min(1.0, scale_factor))
                for sel in bpy.context.selected_objects:
                    sel.select_set(False)
                o.select_set(True)
                bpy.context.view_layer.objects.active = o
                mod = o.modifiers.new("dec_part", "DECIMATE")
                mod.ratio = r
                mod.use_collapse_triangulate = True
                bpy.ops.object.modifier_apply(modifier="dec_part")
                pm["triangles"] = count_tris(o.data)
                pm["vertices"] = len(o.data.vertices)

    parts_glb = out_dir / f"{aid}_parts.glb"
    export_glb(meshes, parts_glb)
    parts_total_tris = sum(p["triangles"] for p in parts_meta)

    # Join into a single static prop mesh for LOD0..2
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    joined.name = f"SR_{aid}_LOD0"
    joined.data.name = f"SR_{aid}_LOD0"

    # Weld UV-seam double vertices lightly if safe, and cap LOD0 at LOD0_MAX_TRIS
    t_joined = count_tris(joined.data)
    if t_joined > LOD0_MAX_TRIS:
        for o in bpy.context.selected_objects:
            o.select_set(False)
        joined.select_set(True)
        bpy.context.view_layer.objects.active = joined
        mod = joined.modifiers.new("dec0", "DECIMATE")
        mod.ratio = LOD0_MAX_TRIS / float(t_joined)
        mod.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier="dec0")

    lod0_tris = count_tris(joined.data)
    lod1_obj = decimate_object(joined, LOD_RATIOS[0], LOD_MINS[0], f"SR_{aid}_LOD1")
    lod2_obj = decimate_object(joined, LOD_RATIOS[1], LOD_MINS[1], f"SR_{aid}_LOD2")

    lod_objs = [joined, lod1_obj, lod2_obj]
    lod_tris = []
    lod_files = {}
    for i, lo in enumerate(lod_objs):
        lp = out_dir / f"{aid}_LOD{i}.glb"
        export_glb([lo], lp)
        lod_tris.append(count_tris(lo.data))
        lod_files[f"LOD{i}"] = f"assets/{aid}/{lp.name}"

    meta = {
        "id": aid,
        "title": entry["title"],
        "category": entry["category"],
        "subcategory": entry["subcategory"],
        "description": entry["description"],
        "lore_fit": entry["lore_fit"],
        "where_to_use": entry["where_to_use"],
        "recommended_usage": entry["recommended_usage"],
        "tags": entry["tags"],
        "provenance": {
            "source_repo": "https://github.com/NVIDIA-Omniverse/simready-central",
            "dataset": entry["dataset"],
            "package_id": pkg.get("package_id"),
            "license": pkg.get("license") or usd_info["simready_license"],
            "author": usd_info["author"],
            "source_url": f"{entry['url']}/com.nvidia.simready.packaging.json",
            "wikidata_qcode": usd_info["wikidata_qcode"],
        },
        "physical_properties": {
            "dimensions_m": {
                "width_x": size_unity_m[0],
                "height_y": size_unity_m[1],
                "depth_z": size_unity_m[2],
            },
            "dimensions_mm": [round(x * 1000.0, 1) for x in size_unity_m],
            "mass_kg": usd_info["mass_kg"],
            "simready_category": usd_info["simready_category"],
            "rigid_body_count": usd_info["rigid_body_count"],
            "usd_joints": usd_info["joints"],
            "grasp_points": usd_info["grasp_points"],
        },
        "geometry": {
            "source_triangles": source_total_tris,
            "parts_glb_triangles": parts_total_tris,
            "lod_triangles": {
                "LOD0": lod_tris[0],
                "LOD1": lod_tris[1],
                "LOD2": lod_tris[2],
            },
            "part_count": len(parts_meta),
            "is_multi_part": len(parts_meta) > 1,
            "parts": parts_meta,
        },
        "materials": list(mat_records.values()),
        "files": {
            "LOD0_glb": lod_files["LOD0"],
            "LOD1_glb": lod_files["LOD1"],
            "LOD2_glb": lod_files["LOD2"],
            "parts_glb": f"assets/{aid}/{parts_glb.name}",
            "textures_dir": f"assets/{aid}/textures",
            "thumbnail": thumb_rel,
            "meta_json": f"assets/{aid}/meta.json",
        },
    }

    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    print(
        f"BUILT {aid:40} size={size_unity_m} parts={len(parts_meta):2} "
        f"LODs={lod_tris} mats={len(mat_records)}",
        flush=True,
    )
    return meta


def write_master_catalog():
    records = []
    for entry in ASSETS:
        mpath = OUT / entry["id"] / "meta.json"
        if mpath.exists():
            records.append(json.loads(mpath.read_text()))

    by_cat = {}
    for r in records:
        by_cat.setdefault(r["category"], []).append(r["id"])

    catalog = {
        "schema_version": "1.0",
        "generated_by": "art/simready_assets_20261122/build_simready_pipeline.py",
        "blender_version": bpy.app.version_string,
        "source_repository": "https://github.com/NVIDIA-Omniverse/simready-central",
        "asset_count": len(records),
        "categories": {k: len(v) for k, v in by_cat.items()},
        "coordinate_convention": "Metric (metres), Unity Y-up in exported GLBs, footprint centred at (0,0,0) with base at Y=0.",
        "how_to_cherry_pick": {
            "static_prop_with_lods": "Import `files.LOD0_glb`, `files.LOD1_glb`, `files.LOD2_glb` (embedded glTF PBR + AO, or bind URP Lit materials to `files.textures_dir/*_{BaseMap,Normal,Mask}.png`).",
            "crafting_studio_or_articulated": "Check `geometry.is_multi_part` and `geometry.parts`: import `files.parts_glb` where each sub-component is its own named mesh node (`<id>_<part>`).",
        },
        "assets": records,
    }
    (HERE / "catalog.json").write_text(json.dumps(catalog, indent=2))

    # Also write a human- and agent-scannable CATALOG.md table
    lines = [
        "# SimReady Central Asset Library for Ashfall (Ward / Athen Hill)",
        "",
        f"**{len(records)} curated, metric, PBR-baked 3D assets** pulled from [NVIDIA-Omniverse/simready-central](https://github.com/NVIDIA-Omniverse/simready-central) and processed through the local Blender {bpy.app.version_string} pipeline.",
        "",
        "## Quick Start for Claude / Agents",
        "",
        "- **Master machine-readable index:** [`catalog.json`](catalog.json) (all 72 assets with full semantic tags, placement recommendations, dimensions, triangle counts, and separable part nodes).",
        "- **Per-asset folder:** `assets/<id>/` contains:",
        "  - `<id>_LOD0.glb`, `<id>_LOD1.glb`, `<id>_LOD2.glb` — joined static prop meshes with embedded glTF 2.0 PBR textures (`baseColorTexture`, `normalTexture`, `metallicRoughnessTexture`, `occlusionTexture`), grounded at `(0, 0, 0)` in metres.",
        "  - `<id>_parts.glb` — multi-node GLB preserving all separable sub-parts (`<id>_<part>`) for **Crafting Studio** assembly jobs (`art/crafting_studio_20261121`), hinged toolbox lids, spinning grinder discs, movable vise jaws, or removable respirator filters.",
        "  - `textures/` — standalone PNG maps including pre-packed **Unity URP Lit Mask maps** (`*_Mask.png`: `R = Metallic`, `G = Occlusion`, `B = 0`, `A = Smoothness = 1 - Roughness`) alongside `*_BaseMap.png`, `*_Normal.png`, and `*_ORM.png`.",
        "  - `meta.json` — single-asset metadata card.",
        "  - `thumbnail.png` — preview render from the SimReady package.",
        "- **Contact sheets:** `review/sheet_*.png` (Blender Cycles ortho grids with a 1.8 m human scale reference).",
        "",
        "## Asset Summary Table",
        "",
        "| ID | Title | Category | Size (W×H×D m) | Parts | LOD0 / 1 / 2 Tris | Where to Use in Ward / Berms |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in records:
        d = r["physical_properties"]["dimensions_m"]
        lt = r["geometry"]["lod_triangles"]
        where = "; ".join(r["where_to_use"][:2])
        lines.append(
            f"| `{r['id']}` | {r['title']} | `{r['category']}` | "
            f"{d['width_x']:.2f}×{d['height_y']:.2f}×{d['depth_z']:.2f} | "
            f"{r['geometry']['part_count']} | {lt['LOD0']:,} / {lt['LOD1']:,} / {lt['LOD2']:,} | {where} |"
        )
    lines.append("")
    (HERE / "CATALOG.md").write_text("\n".join(lines))
    print(f"Wrote catalog.json and CATALOG.md ({len(records)} assets).", flush=True)


def main():
    only = set(sys.argv[sys.argv.index("--") + 1 :]) if "--" in sys.argv else None
    targets = [a for a in ASSETS if not only or a["id"] in only]
    for entry in targets:
        process_one_asset(entry)
    write_master_catalog()


if __name__ == "__main__":
    main()
