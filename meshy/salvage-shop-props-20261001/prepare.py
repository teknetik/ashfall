"""Salvage shop props for Unity, Blender 5.2 headless (1 October 2026).
Run through the capped wrapper:  ~/.local/state/ward-programme/blender.sh prepare.py -- [SS_id ...]
then:                            uv run --with pillow --with numpy python textures.py

Per prop (source = the accepted Meshy attempt's textured.glb, task ids in its record.json):
  * join the delivered meshes; drop loose parts the spec names (separate floor objects Meshy added beside the bench,
    slivers under 50 vertices); turn the front to Blender -Y (= Unity +Z through glTF/glTFast); scale uniformly to the
    spec dimension (no axis is stretched); base on the floor at the footprint centre;
  * LOD0 = the delivered topology and normals (transform only);
  * LOD1 = a copy welded at the UV seams, collapse-decimated to the spec ratio, custom normals cleared and smooth-shaded
    by angle (judged against LOD0 in `review.py lods`);
  * the embedded 2k maps written out byte-for-byte: base colour and normal into the Unity folder, metal-rough into
    <src>/maps/ (textures.py turns it into the URP Lit mask and draws the workbench screen);
  * colliders, the workbench's screen panel, print head, use and light points measured on the fitted mesh and written in
    Unity axes (x = -bx, y = bz, z = -by) to Props/salvage-shop-props.json for Editor/SalvageShopProps.cs.
GLBs are written by Blender's own glTF exporter without images (the Unity materials reference the extracted maps, which
the TextureImporter compresses and streams).
"""
import bpy, bmesh, json, math, sys
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "unity/AthenHill/Assets/AthenHill/Art/SalvageShop/Props"
MANIFEST = OUT / "salvage-shop-props.json"

# src: Meshy attempt folder; yaw: degrees about up bringing the front to -Y; fit: (Unity axis, metres) for the uniform
# scale; drop: "outside_main" removes loose parts whose centre lies outside the largest part's footprint, plus slivers;
# lod1: decimation ratio; metal_scale: multiplies the metallic map (textures.py); smooth_angle: LOD1 shading.
PROPS = {
    # attempt 2 (workbench_b) re-textured at 4k (workbench_b4k, same mesh): the bench with its rear frame, gantry print
    # head and screen; Meshy added a wheeled case and a crate on the floor either side, removed here so the footprint is
    # the bench alone
    "SS_Workbench": dict(src="workbench_b4k", yaw=0.0, fit=("x", 2.2), drop="outside_main", lod1=0.3, metal_scale=1.0,
                         smooth_angle=40),
    # the shelving bay came back 1.0 : 1.8 (a standard bay); fitted by its height, so it is 1.23 m wide, not 2.0
    "SS_PartsRack": dict(src="parts_rack", yaw=0.0, fit=("y", 2.2), drop="slivers", lod1=0.3, metal_scale=1.0,
                         smooth_angle=40),
    "SS_PartsRackHeavy": dict(src="parts_rack_heavy", yaw=0.0, fit=("y", 1.4), drop="slivers", lod1=0.3, metal_scale=1.0,
                              smooth_angle=40),
}


def U(v):
    """Blender point -> Unity local point (glTF export +Y up, glTFast negates X)."""
    return [round(float(-v[0]), 4), round(float(v[2]), 4), round(float(-v[1]), 4)]


def tris(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


def select_only(ob):
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


def components(me):
    """Connected parts of the welded mesh: per-vertex part id (vertices at the same position are one vertex)."""
    co = np.empty(len(me.vertices) * 3, np.float64); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    key = np.round(co / 1e-5).astype(np.int64)
    _, weld = np.unique(key, axis=0, return_inverse=True)
    weld = weld.ravel()
    parent = np.arange(weld.max() + 1)

    def find(a):
        root = a
        while parent[root] != root:
            root = parent[root]
        while parent[a] != root:
            parent[a], a = root, parent[a]
        return root
    ev = np.empty(len(me.edges) * 2, np.int64); me.edges.foreach_get("vertices", ev); ev = weld[ev.reshape(-1, 2)]
    for a, b in ev:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    roots = np.array([find(i) for i in range(len(parent))])
    return roots[weld], co


def drop_parts(ob, mode):
    me = ob.data
    part, co = components(me)
    ids, counts = np.unique(part, return_counts=True)
    main = ids[np.argmax(counts)]
    mmin, mmax = co[part == main].min(0), co[part == main].max(0)
    drop = set()
    report = []
    for i, n in zip(ids, counts):
        if i == main:
            continue
        pmin, pmax = co[part == i].min(0), co[part == i].max(0)
        c = (pmin + pmax) / 2
        outside = mode == "outside_main" and not (mmin[0] <= c[0] <= mmax[0] and mmin[1] <= c[1] <= mmax[1])
        sliver = n < 50
        if outside or sliver:
            drop.add(int(i))
            report.append({"vertices": int(n), "min": [round(float(x), 3) for x in pmin], "max": [round(float(x), 3) for x in pmax],
                           "why": "outside the bench footprint" if outside else "sliver under 50 vertices"})
    if drop:
        bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
        kill = [f for f in bm.faces if int(part[f.verts[0].index]) in drop]
        bmesh.ops.delete(bm, geom=kill, context="FACES")
        loose = [v for v in bm.verts if not v.link_faces]
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
        bm.to_mesh(me); bm.free(); me.update()
    return report


def save_maps(dst_unity, dst_src, uid):
    out = {}
    m = next(m for m in bpy.data.materials if m.use_nodes and any(n.type == "BSDF_PRINCIPLED" for n in m.node_tree.nodes))
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")

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
        if not img or not img.packed_file:
            raise RuntimeError(f"{uid}: no packed {key} map")
        data = img.packed_file.data
        ext = ".png" if data[:4] == b"\x89PNG" else ".jpg"
        (dst_src / f"source_{key}{ext}").write_bytes(data)
        if key != "MetalRough":
            (dst_unity / f"{uid}_{key}{ext}").write_bytes(data)
            out[key] = f"{uid}_{key}{ext}"
        else:
            out["MetalRoughSource"] = f"meshy/salvage-shop-props-20261001/{dst_src.parent.name}/maps/source_{key}{ext}"
        out[key + "_size"] = list(img.size)
    out["Mask"] = f"{uid}_Mask.png"
    return out


def export(ob, path):
    select_only(ob)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True, export_yup=True,
                              export_image_format="NONE", export_tangents=True, export_normals=True, export_apply=True,
                              export_materials="EXPORT", export_vertex_color="NONE", export_extras=False)


def box(lo, hi, name):
    c = (np.asarray(lo) + np.asarray(hi)) / 2; s = np.asarray(hi) - np.asarray(lo)
    return {"name": name, "center": U(c), "size": [round(float(s[0]), 4), round(float(s[2]), 4), round(float(s[1]), 4)]}


def measure_bench(ob):
    me = ob.data
    part, co = components(me)
    mn, mx = co.min(0), co.max(0)
    bm = bmesh.new(); bm.from_mesh(me); bvh = BVHTree.FromBMesh(bm); bm.free()
    res = {}
    # worktop height: median of downward hits over the worktop's front half, below 1.2 m (the frame overhangs higher)
    hs = []
    for x in np.linspace(mn[0] * 0.85, mx[0] * 0.85, 11):
        for y in np.linspace(mn[1] + 0.05, (mn[1] + mx[1]) / 2 - 0.1, 5):
            hit = bvh.ray_cast(Vector((float(x), float(y), 1.2)), Vector((0, 0, -1)))
            if hit[0] is not None:
                hs.append(hit[0].z)
    top = float(np.median(hs))
    # front edge of the worktop: rays from the front 2 cm under the top
    fr = []
    for x in np.linspace(mn[0] * 0.8, mx[0] * 0.8, 9):
        hit = bvh.ray_cast(Vector((float(x), float(mn[1]) - 1.0, top - 0.02)), Vector((0, 1, 0)))
        if hit[0] is not None:
            fr.append(hit[0].y)
    front = float(np.median(fr))
    below = co[co[:, 2] <= top + 0.005]
    res["worktop_top"] = round(top, 4)
    res["worktop_front_unity_z"] = round(-front, 4)
    # back edge of the worktop: the furthest-back downward hit at worktop height (the frame stands behind it)
    wback = front
    for x in np.linspace(mn[0] * 0.9, mx[0] * 0.9, 15):
        for y in np.linspace(front, float(mx[1]), 60):
            hit = bvh.ray_cast(Vector((float(x), float(y), top + 0.04)), Vector((0, 0, -1)))
            if hit[0] is not None and abs(hit[0].z - top) < 0.015:
                wback = max(wback, float(y))
    res["worktop_back_unity_z"] = round(-wback, 4)
    res["worktop_depth"] = round(wback - front, 4)
    back = float(below[:, 1].max())
    cols = [box([below[:, 0].min(), below[:, 1].min(), 0.0], [below[:, 0].max(), back, top], "COL bench body")]
    above = co[co[:, 2] > top + 0.12]
    rear = above[above[:, 1] > wback - 0.08]
    if len(rear):
        cols.append(box([rear[:, 0].min(), rear[:, 1].min(), top], [rear[:, 0].max(), rear[:, 1].max(), rear[:, 2].max()], "COL rear frame"))
    res["colliders"] = cols
    cx = (below[:, 0].min() + below[:, 0].max()) / 2
    wc = (front + wback) / 2
    res["worktop_centre"] = U((cx, wc, top))
    # where the player stands: 0.8 m in front of the worktop centre, but at least 0.5 m clear of the front edge (the
    # player's CharacterController is 0.35 m in radius)
    uy = min(wc - 0.8, front - 0.5)
    res["use_point"] = U((cx, uy, 0.0))
    res["use_point_clear_of_front_edge"] = round(front - uy, 4)
    # screen panel: the thin flat part standing on the worktop (Meshy made the face a separate plate)
    best = None
    for i in np.unique(part):
        p = co[part == i]
        pmn, pmx = p.min(0), p.max(0)
        ext = pmx - pmn
        if pmn[2] > top - 0.02 and ext[1] < 0.06 and ext[0] > 0.25 and ext[2] > 0.1 and (best is None or ext[0] > best[1][0]):
            best = (p, ext)
    if best is not None:
        p = best[0]
        # the plate has a front and a back face: fit the plane to the front half of its vertices
        c0 = p.mean(0)
        n0 = np.linalg.svd(p - c0)[2][2]
        if n0[1] > 0:
            n0 = -n0
        d0 = (p - c0) @ n0
        f = p[d0 > (d0.min() + d0.max()) / 2]
        c = f.mean(0)
        n = np.linalg.svd(f - c)[2][2]
        if n[1] > 0:
            n = -n                                     # towards the front (-Y)
        ax = np.array([1.0, 0, 0]); ax -= n * ax.dot(n); ax /= np.linalg.norm(ax)
        ay = np.cross(n, ax)
        if ay[2] < 0:
            ay = -ay
        lx, ly, ln = (f - c) @ ax, (f - c) @ ay, (f - c) @ n
        w, h = float(lx.max() - lx.min()), float(ly.max() - ly.min())
        centre = c + ax * (lx.max() + lx.min()) / 2 + ay * (ly.max() + ly.min()) / 2 + n * (float(ln.max()) + 0.002)
        res["screen"] = {"center": U(centre), "normal": U(n), "up": U(ay), "panel_size": [round(w, 4), round(h, 4)],
                         "front_face_deviation": round(float(ln.max() - ln.min()), 4), "plate_thickness": round(float(d0.max() - d0.min()), 4),
                         "vertices": int(len(p))}
    # print head: the lowest hanging block of the overhead unit above the worktop's middle (ray from below)
    heads = []
    for x in np.linspace(mn[0] * 0.5, mx[0] * 0.5, 21):
        for y in np.linspace(front + 0.05, back, 9):
            hit = bvh.ray_cast(Vector((float(x), float(y), top + 0.45)), Vector((0, 0, 1)))
            if hit[0] is not None and hit[0].z < top + 1.0:
                heads.append((hit[0].z, float(x), float(y)))
    if heads:
        heads.sort()
        z0 = heads[0][0]
        near = np.array([h for h in heads if h[0] < z0 + 0.04])
        hx, hy = float(near[:, 1].mean()), float(near[:, 2].mean())
        # the block's front face and top: rays from the front and down its body
        hit = bvh.ray_cast(Vector((hx, float(mn[1]) - 1.0, z0 + 0.08)), Vector((0, 1, 0)))
        hfront = float(hit[0].y) if hit[0] is not None else hy - 0.06
        res["print_head"] = {"bottom": U((hx, hy, z0)), "front_face": U((hx, hfront, z0 + 0.08))}
        # light point: at the print head, 6 cm in front of its body and 12 cm up from its tip (clear of the geometry)
        res["light_point"] = U((hx, hfront - 0.06, z0 + 0.12))
    return res


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ids = [a for a in args if not a.startswith("--")] or [k for k, v in PROPS.items() if (HERE / v["src"] / "textured.glb").exists()]
    man = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    for uid in ids:
        spec = PROPS[uid]
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(HERE / spec["src"] / "textured.glb"))
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
        me = ob.data
        tri_src = tris(me)
        dropped = drop_parts(ob, spec["drop"]) if spec.get("drop") else []
        if spec["yaw"]:
            me.transform(Matrix.Rotation(math.radians(spec["yaw"]), 4, "Z"))
        co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
        mn, mx = co.min(0), co.max(0)
        axis, metres = spec["fit"]
        ext = {"x": mx[0] - mn[0], "y": mx[2] - mn[2], "z": mx[1] - mn[1]}
        s = metres / float(ext[axis])
        me.transform(Matrix.Scale(s, 4) @ Matrix.Translation((-(mn[0] + mx[0]) / 2, -(mn[1] + mx[1]) / 2, -mn[2])))
        me.update()
        ob.name = me.name = f"{uid}_LOD0"
        me.materials[0].name = uid
        dst = OUT / uid; dst.mkdir(parents=True, exist_ok=True)
        src_maps = HERE / spec["src"] / "maps"; src_maps.mkdir(exist_ok=True)
        maps = save_maps(dst, src_maps, uid)
        info = measure_bench(ob) if uid == "SS_Workbench" else {}
        co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
        mn, mx = co.min(0), co.max(0)
        if uid != "SS_Workbench":
            info["colliders"] = [box([mn[0] + 0.02, mn[1] + 0.02, 0.0], [mx[0] - 0.02, mx[1] - 0.02, mx[2]], "COL rack")]
        # LOD1: weld UV seams, collapse-decimate, plain smooth-by-angle normals
        lod1 = bpy.data.objects.new(f"{uid}_LOD1", me.copy()); lod1.data.name = f"{uid}_LOD1"
        bpy.context.scene.collection.objects.link(lod1)
        bm = bmesh.new(); bm.from_mesh(lod1.data)
        v0 = len(bm.verts)
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4)
        v1 = len(bm.verts)
        bm.to_mesh(lod1.data); bm.free()
        select_only(lod1)
        try:
            bpy.ops.mesh.customdata_custom_splitnormals_clear()
        except RuntimeError:
            pass
        d = lod1.modifiers.new("d", "DECIMATE"); d.ratio = spec["lod1"]; d.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier="d")
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(spec["smooth_angle"]))
        export(ob, dst / f"{uid}_LOD0.glb")
        export(lod1, dst / f"{uid}_LOD1.glb")
        rec = json.loads((HERE / spec["src"] / "record.json").read_text())
        size = [round(float(mx[0] - mn[0]), 4), round(float(mx[2] - mn[2]), 4), round(float(mx[1] - mn[1]), 4)]
        man[uid] = {"source": f"meshy/salvage-shop-props-20261001/{spec['src']}/textured.glb",
                    "preview_task": rec.get("preview_task"), "refine_task": rec.get("refine_task"), "credits": rec.get("credits"),
                    "source_triangles": tri_src, "dropped_parts": dropped, "yaw": spec["yaw"], "fit": list(spec["fit"]),
                    "scale": round(s, 6), "size": size, "target_size": rec.get("target_size_m"),
                    "lod_triangles": [tris(ob.data), tris(lod1.data)], "lod1_ratio": spec["lod1"], "lod1_welded_vertices": [v0, v1],
                    "maps": maps, "metal_scale": spec["metal_scale"], **info}
        print(uid, json.dumps(man[uid]), flush=True)
        MANIFEST.write_text(json.dumps(man, indent=1))


if __name__ == "__main__":
    main()
