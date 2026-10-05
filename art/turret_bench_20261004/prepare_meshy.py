"""Carl's Meshy turret and bench for Unity, Blender 5.2 headless (4 October 2026).

Sources (supplied by Carl, Meshy web exports, 2k PBR): meshy/turret-bench-20261004/source/
  Meshy_AI_Sentinel_Turret_1004174027_texture.glb   370,290 triangles
  Meshy_AI_Cybernetic_Bench_1004174020_texture.glb  301,280 triangles
Per model: keep the UV-island seams split for LOD0 (welded for LOD1+, see below), turn the front to Unity +Z, put the base on the ground at the footprint centre,
scale uniformly (no axis stretched), then write three LODs by collapse decimation from the full source (the source
files stay untouched). The embedded maps are written out byte-for-byte; make_masks() derives the URP Lit mask
(R metallic = glTF B x metal scale, G occlusion 1, A smoothness = 1 - glTF G). The bench is ~99 % full metal on a dark
albedo, which reads black against the city's small sky probe (as the street kit's galvanised bins did): metal x 0.5.

* Bench: seat top measured at 0.733 of the 1.095 Meshy height; scaled so the seat is 0.45 m (the street kit's NPC sit
  points), giving 1.17 x 0.44 x 0.67 m, the footprint of the Poly Haven bench it replaces. Backrest already at -Z.
* Turret: scale 1 (1.49 m tall, 0.83 m square base); the barrel axis is 1.085 m above the feet, so on the bastion's
  0.37 m gun deck it sits at the old pintle gun's height. Barrel turned from Unity +X to +Z (front).

Run:  env -i HOME=$HOME PATH=/usr/bin:/bin blender -b --factory-startup --python-exit-code 1 -P prepare_meshy.py
Out:  unity/AthenHill/Assets/AthenHill/Art/TurretBench/<id>/<id>_LOD0..2.glb, source_*.png|jpg, <id>_Mask.png, props.json
"""
import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector, Matrix

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SRC = ROOT / "meshy/turret-bench-20261004/source"
OUT = ROOT / "unity/AthenHill/Assets/AthenHill/Art/TurretBench"

# yaw about Blender Z (degrees) to bring the front to Blender -Y (= Unity +Z); scale; LOD ratios of the source
PROPS = {
    "sentinel_turret": dict(file="Meshy_AI_Sentinel_Turret_1004174027_texture.glb", yaw=90, scale=1.0,
                            centre="feet", lods=(0.08, 0.02, 0.006), metal=1.0),
    "cyber_bench": dict(file="Meshy_AI_Cybernetic_Bench_1004174020_texture.glb", yaw=0, scale=0.45 / 0.733,
                        centre="bounds", lods=(0.15, 0.03, 0.007), metal=0.5),
}


# Meshy splits the mesh at UV-island seams. For the light LOD0 reduction they stay split (welding let the collapse drag
# UVs across islands: a smeared dark notch on the bench back); the heavy LOD1/LOD2 reductions collapse cleaner welded
# (split borders then keep too many vertices and tear). Normals always come from the full source.


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
    for pid, spec in PROPS.items():
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(SRC / spec["file"]))
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
        if spec["yaw"]:
            for me in (ob.data, welded):
                me.transform(Matrix.Rotation(math.radians(spec["yaw"]), 4, "Z"))
        vs = [v.co for v in ob.data.vertices]
        zmin = min(v.z for v in vs)
        if spec["centre"] == "feet":      # footprint of the base plate, not the barrel/pod overhang
            feet = [v for v in vs if v.z < zmin + 0.03]
            src = feet
        else:
            src = vs
        cx = (min(v.x for v in src) + max(v.x for v in src)) / 2
        cy = (min(v.y for v in src) + max(v.y for v in src)) / 2
        s = spec["scale"]
        for me in (ob.data, welded):
            me.transform(Matrix.Scale(s, 4) @ Matrix.Translation((-cx, -cy, -zmin)))
            me.update()
        vs = [v.co for v in ob.data.vertices]
        mn = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
        mx = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
        # Unity bounds: x = -Blender x, y = Blender z, z = -Blender y
        ubounds = {"min": [round(-mx.x, 3), round(mn.z, 3), round(-mx.y, 3)], "max": [round(-mn.x, 3), round(mx.z, 3), round(-mn.y, 3)]}
        mat = ob.data.materials[0]
        mat.name = f"TB_{pid}"
        dst = OUT / pid
        dst.mkdir(parents=True, exist_ok=True)
        maps = save_maps(dst, pid, spec["metal"])
        src_tris = tris(ob.data)
        lods = []
        for i, r in enumerate(spec["lods"]):
            c = bpy.data.objects.new(f"TB_{pid}_LOD{i}", (ob.data if i == 0 else welded).copy())
            bpy.context.scene.collection.objects.link(c)
            for o in bpy.context.selected_objects:
                o.select_set(False)
            c.select_set(True); bpy.context.view_layer.objects.active = c
            d = c.modifiers.new("d", "DECIMATE"); d.ratio = r; d.use_collapse_triangulate = True
            bpy.ops.object.modifier_apply(modifier="d")
            # collapse leaves interpolated normals that no longer match the source the normal map was baked against
            # (dark facets on flat panels): carry the source's split normals over
            t = c.modifiers.new("n", "DATA_TRANSFER"); t.object = ob; t.use_loop_data = True
            t.data_types_loops = {"CUSTOM_NORMAL"}; t.loop_mapping = "POLYINTERP_NEAREST"
            bpy.ops.object.modifier_apply(modifier="n")
            lods.append(c)
        counts = []
        for i, o in enumerate(lods):
            export(o, dst / f"{pid}_LOD{i}.glb")
            counts.append(tris(o.data))
        report[pid] = {"source": f"meshy/turret-bench-20261004/source/{spec['file']}", "source_triangles": src_tris,
                       "yaw": spec["yaw"], "metal_scale": spec["metal"], "scale": round(s, 5), "welded_vertices": [v0, v1], "unity_bounds": ubounds,
                       "lods": counts, "lod_ratios": list(spec["lods"]), "maps": maps}
        print(pid, ubounds, counts, flush=True)
    (OUT / "props.json").write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
