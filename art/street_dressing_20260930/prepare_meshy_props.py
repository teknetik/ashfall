"""Ward street dressing: the four Meshy hero props for Unity, Blender 5.2 headless (30 September 2026).

Sources: meshy/street-dressing-20260930/<id>/textured.glb (Meshy text-to-3D preview -> refine, 2k PBR; task ids and
credits in each record.json). Per prop: join and weld the UV-island seams, turn the front to Unity +Z, put the base on the
ground at the footprint centre and scale uniformly to its real size (no axis is stretched), then write three LODs by
collapse decimation; the embedded maps are written out byte-for-byte (prepare_textures.py derives the URP mask maps).

Run:  env -i HOME=$HOME PATH=/usr/bin:/bin blender -b --factory-startup --python-exit-code 1 -P prepare_meshy_props.py
Out:  unity/AthenHill/Assets/AthenHill/Art/StreetDressing/Props/<id>/<id>_LOD0..2.glb, source_*.jpg|png, meshy-props.json
"""
import bpy, bmesh, json, math, sys
from pathlib import Path
from mathutils import Vector, Matrix

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SRC = ROOT / "meshy/street-dressing-20260930"
OUT = ROOT / "unity/AthenHill/Assets/AthenHill/Art/StreetDressing/Props"

# id: fit (axis, metres) for the uniform scale, yaw fix (degrees about up), LOD ratios after LOD0
PROPS = {
    "field_generator": dict(fit=("x", 1.25), yaw=0, lods=(0.18, 0.05)),
    "water_point": dict(fit=("y", 1.65), yaw=0, lods=(0.18, 0.05)),
    "handcart": dict(fit=("x", 1.7), yaw=0, lods=(0.18, 0.05)),
    "refuse_bin": dict(fit=("y", 1.25), yaw=0, lods=(0.18, 0.05)),
}


def tris(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


def save_maps(dst):
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
    return out


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
        bpy.ops.import_scene.gltf(filepath=str(SRC / pid / "textured.glb"))
        meshes = [o for o in bpy.data.objects if o.type == "MESH"]
        for o in bpy.context.selected_objects:
            o.select_set(False)
        for o in meshes:
            o.select_set(True)
            if o.parent:
                mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
        bpy.context.view_layer.objects.active = meshes[0]
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        if len(meshes) > 1:
            bpy.ops.object.join()
        ob = bpy.context.view_layer.objects.active
        for o in list(bpy.data.objects):
            if o != ob:
                bpy.data.objects.remove(o, do_unlink=True)
        bm = bmesh.new(); bm.from_mesh(ob.data)
        v0 = len(bm.verts)
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
        v1 = len(bm.verts)
        bm.to_mesh(ob.data); bm.free()
        if spec["yaw"]:
            ob.data.transform(Matrix.Rotation(math.radians(spec["yaw"]), 4, "Z"))
        vs = [v.co for v in ob.data.vertices]
        mn = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
        mx = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
        ext = {"x": mx.x - mn.x, "y": mx.z - mn.z, "z": mx.y - mn.y}      # Unity axes
        axis, metres = spec["fit"]
        s = metres / ext[axis]
        ob.data.transform(Matrix.Scale(s, 4) @ Matrix.Translation((-(mn.x + mx.x) / 2, -(mn.y + mx.y) / 2, -mn.z)))
        ob.data.update()
        size = [round(ext["x"] * s, 4), round(ext["y"] * s, 4), round(ext["z"] * s, 4)]
        mat = ob.data.materials[0]
        mat.name = f"SD_{pid}"
        dst = OUT / pid
        dst.mkdir(parents=True, exist_ok=True)
        maps = save_maps(dst)
        lods = [ob]
        for i, r in enumerate(spec["lods"]):
            c = bpy.data.objects.new(f"SD_{pid}_LOD{i + 1}", ob.data.copy())
            bpy.context.scene.collection.objects.link(c)
            for o in bpy.context.selected_objects:
                o.select_set(False)
            c.select_set(True); bpy.context.view_layer.objects.active = c
            d = c.modifiers.new("d", "DECIMATE"); d.ratio = r; d.use_collapse_triangulate = True
            bpy.ops.object.modifier_apply(modifier="d")
            lods.append(c)
        counts = []
        for i, o in enumerate(lods):
            o.name = f"SD_{pid}_LOD{i}"
            export(o, dst / f"{pid}_LOD{i}.glb")
            counts.append(tris(o.data))
        rec = json.loads((SRC / pid / "record.json").read_text())
        report[pid] = {"source": f"meshy/street-dressing-20260930/{pid}/textured.glb", "preview_task": rec.get("preview_task"),
                       "refine_task": rec.get("refine_task"), "credits": rec.get("credits"), "scale": round(s, 5),
                       "welded_vertices": [v0, v1], "size": size, "lods": counts, "maps": maps,
                       "materials": {f"SD_{pid}": {"meshy": pid}}}
        print(pid, size, counts, maps, flush=True)
    (OUT / "meshy-props.json").write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
