"""Field Supply's Meshy packs for Unity, Blender 5.2 headless (5 October 2026).

Sources: meshy/field-supply-20261005/props/<id>/model.glb (Meshy Image to 3D from each item's icon art, 2k PBR,
16-20k triangles). Fronts already face Unity +Z (inspect/, inspect_packs.py), so no yaw. Per pack: scale uniformly to its
real height, put the origin at the HANG POINT (top of the back, centred: the wall and stand hooks), then three LODs by
collapse decimation with the source's split normals carried over (the turret/bench recipe,
art/turret_bench_20261004/prepare_meshy.py, whose helpers are reused here verbatim). Maps are written out byte for byte
plus the URP mask (R metallic, G occlusion, A smoothness).

Run:  blender.sh art/field_supply_20261005/packs/prepare_packs.py
Out:  unity/AthenHill/Assets/AthenHill/Art/FieldSupply/Packs/<id>/<id>_LOD0..2.glb, source_*.png|jpg, <id>_Mask.png, packs.json
"""
import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector, Matrix

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SRC = ROOT / "meshy/field-supply-20261005/props"
OUT = ROOT / "unity/AthenHill/Assets/AthenHill/Art/FieldSupply/Packs"
# id: (real height m, item id, LOD ratios of the source)
PACKS = {
    "pack_field": (0.52, "field_backpack", (0.6, 0.2, 0.06)),
    "pack_rucksack": (0.62, "canvas_rucksack", (0.6, 0.2, 0.06)),
    "pack_frame": (0.78, "frame_pack", (0.6, 0.2, 0.06)),
    "pack_carrier": (0.70, "porter_carrier", (0.6, 0.2, 0.06)),
    "pack_rig": (0.62, "courier_cargo_rig", (0.6, 0.2, 0.06)),
}


def tris(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


def save_maps(dst, pid, metal):
    out = {}
    for m in bpy.data.materials:
        if not m.use_nodes:
            continue
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if not bsdf:
            continue

        def src_image(sock):
            stack = [l.from_node for l in bsdf.inputs[sock].links]
            while stack:
                n = stack.pop()
                if n.type == "TEX_IMAGE" and n.image:
                    return n.image
                for inp in n.inputs:
                    stack += [l.from_node for l in inp.links]
            return None
        for key, sock in (("BaseColor", "Base Color"), ("MetalRough", "Metallic"), ("Normal", "Normal")):
            img = src_image(sock)
            if img and img.packed_file:
                data = img.packed_file.data
                ext = ".png" if data[:4] == b"\x89PNG" else ".jpg"
                path = dst / f"source_{key}{ext}"
                path.write_bytes(data)
                out[key] = {"file": path.name, "size": list(img.size)}
                if key == "MetalRough":
                    make_mask(img, dst / f"{pid}_Mask.png", metal)
                    out["Mask"] = {"file": f"{pid}_Mask.png", "size": list(img.size)}
    return out


def make_mask(img, path, metal=1.0):
    w, h = img.size
    px = list(img.pixels[:])          # linear floats RGBA (metal-rough maps are non-colour data)
    for i in range(0, len(px), 4):
        g, b = px[i + 1], px[i + 2]
        px[i], px[i + 1], px[i + 2], px[i + 3] = b * metal, 1.0, 0.0, 1.0 - g
    m = bpy.data.images.new("mask", w, h, alpha=True, float_buffer=False)
    m.colorspace_settings.name = "Non-Color"
    m.pixels[:] = px
    m.filepath_raw = str(path); m.file_format = "PNG"; m.save()


def export(ob, path):
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True, export_yup=True,
                              export_image_format="NONE", export_tangents=True, export_normals=True, export_apply=True,
                              export_materials="EXPORT", export_vertex_color="NONE", export_extras=False)


def main():
    report = {}
    for pid, (height, item, ratios) in PACKS.items():
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(SRC / pid / "model.glb"))
        meshes = [o for o in bpy.data.objects if o.type == "MESH"]
        for o in meshes:
            if o.parent:
                mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
        for o in bpy.context.selected_objects:
            o.select_set(False)
        for o in meshes:
            o.select_set(True)
        bpy.context.view_layer.objects.active = meshes[0]
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        if len(meshes) > 1:
            bpy.ops.object.join()
        ob = bpy.context.view_layer.objects.active
        for o in list(bpy.data.objects):
            if o != ob:
                bpy.data.objects.remove(o, do_unlink=True)
        welded = ob.data.copy()
        bm = bmesh.new(); bm.from_mesh(welded)
        v0 = len(bm.verts)
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
        v1 = len(bm.verts)
        bm.to_mesh(welded); bm.free()
        vs = [v.co for v in ob.data.vertices]
        mn = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
        mx = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
        s = height / (mx.z - mn.z)
        # hang point: centre x, the back (Blender +Y = Unity -Z), the top
        hx, hy, hz = (mn.x + mx.x) / 2, mx.y, mx.z
        for me in (ob.data, welded):
            me.transform(Matrix.Scale(s, 4) @ Matrix.Translation((-hx, -hy, -hz)))
            me.update()
        vs = [v.co for v in ob.data.vertices]
        mn = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
        mx = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
        ubounds = {"min": [round(-mx.x, 3), round(mn.z, 3), round(-mx.y, 3)], "max": [round(-mn.x, 3), round(mx.z, 3), round(-mn.y, 3)]}
        ob.data.materials[0].name = f"FS_{pid}"
        dst = OUT / pid
        dst.mkdir(parents=True, exist_ok=True)
        maps = save_maps(dst, pid, 1.0)
        src_tris = tris(ob.data)
        lods = []
        for i, r in enumerate(ratios):
            c = bpy.data.objects.new(f"FS_{pid}_LOD{i}", (ob.data if i == 0 else welded).copy())
            bpy.context.scene.collection.objects.link(c)
            for o in bpy.context.selected_objects:
                o.select_set(False)
            c.select_set(True); bpy.context.view_layer.objects.active = c
            d = c.modifiers.new("d", "DECIMATE"); d.ratio = r; d.use_collapse_triangulate = True
            bpy.ops.object.modifier_apply(modifier="d")
            t = c.modifiers.new("n", "DATA_TRANSFER"); t.object = ob; t.use_loop_data = True
            t.data_types_loops = {"CUSTOM_NORMAL"}; t.loop_mapping = "POLYINTERP_NEAREST"
            bpy.ops.object.modifier_apply(modifier="n")
            lods.append(c)
        counts = []
        for i, o in enumerate(lods):
            export(o, dst / f"{pid}_LOD{i}.glb")
            counts.append(tris(o.data))
        report[pid] = {"item": item, "source": f"meshy/field-supply-20261005/props/{pid}/model.glb", "source_triangles": src_tris,
                       "height_m": height, "scale": round(s, 5), "origin": "hang point (top of the back, centred)",
                       "welded_vertices": [v0, v1], "unity_bounds": ubounds, "lods": counts, "lod_ratios": list(ratios), "maps": maps}
        print(pid, ubounds, counts, flush=True)
    (OUT / "packs.json").write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
