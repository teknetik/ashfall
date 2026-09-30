"""Prepare Carl's two Meshy props for Unity, Blender 5.2 headless (30 September 2026).

Sources (supplied by Carl, copied unchanged to meshy_source/): terminal_source.glb ("Reclaim & Save Point" kiosk,
506,432 triangles, 2k base colour / metal-rough / normal) and floodlight_source.glb (tripod floodlight with cable and
power box, 515,818 triangles, same maps). Meshy exports are normalised to about +-0.95 units and split at UV seams.

Per prop: weld the UV-island seams (loops keep their UVs), put the base on y = 0 and scale uniformly to real size
(terminal 1.85 m tall, floodlight 1.0 m), then write three LODs by collapse decimation (the source stays untouched):
  terminal   LOD0 ~46k, LOD1 ~15k, LOD2 ~4k triangles (first pass 111k/28k/7k cost ~1 ms on the hill walk)
  floodlight LOD0 ~36k, LOD1 ~10k, LOD2 ~3k triangles
The floodlight head is turned up 15 degrees about its yoke pivot so it can floodlight the Vanguard Hall facade from the
podium (a larger turn drives the lamp's tail into the tripod). The embedded maps are written out byte-for-byte.

Run:  blender -b --python-exit-code 1 -P prepare_meshy_props.py
Outputs: unity/AthenHill/Assets/AthenHill/Art/HillProps/{Terminal,Floodlight}/ (LOD glbs, source maps, props.json).
"""
import bpy, bmesh, json, math, sys
from pathlib import Path
from mathutils import Vector, Matrix

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "unity/AthenHill/Assets/AthenHill/Art/HillProps"

PROPS = {
    "Terminal": dict(src="terminal_source.glb", height=1.85, lods=[0.09, 0.03, 0.008], mat="HP_Terminal"),
    "Floodlight": dict(src="floodlight_source.glb", height=1.0, lods=[0.07, 0.02, 0.006], mat="HP_Floodlight",
                       # yoke pivot (source units, Blender axes) and the head re-aim
                       pivot=(-0.33, 0.0, 0.43), head_lens=(-0.70, 0.64), head_rear=(0.34, 0.20), head_r=0.355, raise_deg=15.0),
}


def tri_count(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def weld(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    before = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    after = len(bm.verts)
    bm.to_mesh(ob.data)
    bm.free()
    return before, after


def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def raise_head(ob, spec):
    """Turn the lamp head up about the yoke pivot axis (Blender Y). The turn angle is a continuous weight of each
    vertex's distance from the head axis (full inside the head, fading to zero across the yoke arms and cable), so
    coincident seam vertices move together and nothing tears; the arms bend at most a couple of centimetres beside
    the pivot, where the motion is smallest. Returns the number of vertices that moved."""
    px, _, pz = spec["pivot"]
    lx, lz = spec["head_lens"]
    rx, rz = spec["head_rear"]
    ax = Vector((rx - lx, 0, rz - lz))
    length = ax.length
    ax.normalize()
    lens = Vector((lx, 0, lz))
    r0, r1 = spec["head_r"], spec["head_r"] + 0.075
    moved = 0
    me = ob.data
    for v in me.vertices:
        p = v.co
        t = (Vector((p.x, 0, p.z)) - lens).dot(ax)
        foot = lens + ax * t
        radial = math.sqrt((p.x - foot.x) ** 2 + (p.z - foot.z) ** 2 + p.y ** 2)
        w = (1 - smoothstep(r0, r1, radial)) * smoothstep(-0.16, -0.04, t) * (1 - smoothstep(length + 0.06, length + 0.18, t))
        if w <= 0:
            continue
        phi = math.radians(spec["raise_deg"]) * w
        c, s = math.cos(phi), math.sin(phi)
        dx, dz = p.x - px, p.z - pz
        p.x = px + dx * c + dz * s
        p.z = pz - dx * s + dz * c
        moved += 1
    me.update()
    return moved


def save_maps(dst):
    names = {}
    for img in bpy.data.images:
        if not img.packed_file:
            continue
        data = img.packed_file.data
        ext = ".png" if data[:4] == b"\x89PNG" else ".jpg"
        names[img.name] = img
    # map by material slot usage
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


def main():
    report = {"source": "art/hill_20260930/prepare_meshy_props.py", "date": "2026-09-30", "props": {}}
    for name, spec in PROPS.items():
        bpy.ops.wm.read_factory_settings(use_empty=True)
        src = HERE / "meshy_source" / spec["src"]
        bpy.ops.import_scene.gltf(filepath=str(src))
        ob = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]
        bpy.context.view_layer.objects.active = ob
        ob.select_set(True)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        rec = {"source_triangles": tri_count(ob), "source_file": spec["src"]}
        if "pivot" in spec:
            rec["head_vertices_moved"] = raise_head(ob, spec)
            rec["head_raise_deg"] = spec["raise_deg"]
        rec["weld_vertices"] = weld(ob)
        # base on z = 0 (Blender up), centred on the footprint, uniform scale to the real height
        vs = [v.co for v in ob.data.vertices]
        mn = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
        mx = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
        k = spec["height"] / (mx.z - mn.z)
        ctr = Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))
        ob.data.transform(Matrix.Scale(k, 4) @ Matrix.Translation(-ctr))
        ob.data.update()
        rec["uniform_scale"] = k
        rec["size_m_blender_xyz"] = [(mx.x - mn.x) * k, (mx.y - mn.y) * k, (mx.z - mn.z) * k]
        if "pivot" in spec:
            # where the lamp's lens centre and beam axis end up (Unity metres, local to the prop root)
            px, _, pz = spec["pivot"]
            phi = math.radians(spec["raise_deg"])
            def rot(x, z):
                x, z = x - px, z - pz
                return px + x * math.cos(phi) + z * math.sin(phi), pz - x * math.sin(phi) + z * math.cos(phi)
            lxz = rot(*spec["head_lens"])
            rxz = rot(*spec["head_rear"])
            lens = (Vector((lxz[0], 0, lxz[1])) - ctr) * k
            rear = (Vector((rxz[0], 0, rxz[1])) - ctr) * k
            d = (lens - rear).normalized()
            # Blender (x, y, z) -> Unity (-x, z, -y)
            rec["lens_unity"] = [-lens.x, lens.z, -lens.y]
            rec["beam_dir_unity"] = [-d.x, d.z, -d.y]
            rec["beam_elevation_deg"] = math.degrees(math.asin(d.z))
        dst = OUT / name
        dst.mkdir(parents=True, exist_ok=True)
        rec["maps"] = save_maps(dst)
        mat = bpy.data.materials.new(spec["mat"])
        ob.data.materials.clear()
        ob.data.materials.append(mat)
        for p in ob.data.polygons:
            p.use_smooth = True
        rec["lods"] = {}
        base_me = ob.data.copy()
        for li, ratio in enumerate(spec["lods"]):
            lo = bpy.data.objects.new(f"{name}_LOD{li}", base_me.copy())
            bpy.context.scene.collection.objects.link(lo)
            for o in bpy.context.selected_objects:
                o.select_set(False)
            lo.select_set(True)
            bpy.context.view_layer.objects.active = lo
            dec = lo.modifiers.new("dec", "DECIMATE")
            dec.decimate_type = "COLLAPSE"
            dec.ratio = ratio
            dec.use_collapse_triangulate = True
            bpy.ops.object.modifier_apply(modifier="dec")
            lo.data.set_sharp_from_angle(angle=math.radians(50))
            wn = lo.modifiers.new("wn", "WEIGHTED_NORMAL")
            wn.keep_sharp = True
            bpy.ops.object.modifier_apply(modifier="wn")
            bpy.ops.export_scene.gltf(filepath=str(dst / f"{name}_LOD{li}.glb"), export_format="GLB", use_selection=True,
                                      export_yup=True, export_image_format="NONE", export_tangents=True, export_normals=True,
                                      export_apply=True, export_materials="EXPORT", export_vertex_color="NONE")
            rec["lods"][f"LOD{li}"] = tri_count(lo)
            print(name, f"LOD{li}", tri_count(lo), flush=True)
        report["props"][name] = rec
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE / f"meshy_source/{name.lower()}-prepared.blend"))
    (OUT / "props.json").write_text(json.dumps(report, indent=1))


main()
