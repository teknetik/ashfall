"""Re-export the optimized meshes through Blender's official FBX exporter (binary 7.4).

blender -b --factory-startup --python reexport_blender.py -- truck|tree

Why: Unity 6000.6's FBX SDK rejected ("File is corrupted") all seven files written by the
custom element-tree writer (fbxlib.write_surgery). Those files are kept, renamed, under
rejected_customwriter/. Their geometry payload was verified (raw vertices, polygons,
normals, UVs, colours), so it is read back here with the low-level parser and rebuilt
as Blender meshes with an identity object transform (mesh coordinates = the FBX raw
coordinates, exactly as the source files were authored), then exported with the
settings that reproduce the sources' declared conventions:

  source GlobalSettings: UpAxis Y(+1), FrontAxis Z(+1), CoordAxis X(+1), UnitScaleFactor 1.0,
  OriginalUnitScaleFactor 1.0; every mesh Model: Lcl Rotation (-90, 0, 0), Lcl Scaling 100.
  => axis_forward='-Z', axis_up='Y', apply_unit_scale=True (metric scene, scale_length 1 =>
  factor 100), apply_scale_options='FBX_SCALE_NONE' (factor goes on the root node scale,
  UnitScaleFactor stays 1.0), global_scale=1.0, bake_space_transform=False,
  use_space_transform=True. (This is Blender's default export; the Meshy truck source
  was written by "Blender (stable FBX IO) 4.4.0" with the same result.)

Per-corner normals are stored as Blender free custom normals ("custom_normal" corner
attribute) and read back before export; material slot names, the UV set name "UVMap"
and the tree's "Col" corner colours (exported LINEAR = raw values) are preserved.
Tangents are not written (the installer sets CalculateMikk).
"""
import json
import os
import sys
import time

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import fbxlib  # noqa: E402

ROOT = "/home/teknetik/code/ao2/art/optimization_20260929"
REJECTED = f"{ROOT}/rejected_customwriter"
FILES = {
    "truck": ["KaraveenTruck_LOD0_exact", "KaraveenTruck_LOD1", "KaraveenTruck_LOD2",
              "KaraveenTruck_ShadowNear", "KaraveenTruck_ShadowProxy"],
    "tree": ["WardTree_ShadowProxy", "WardTree_LOD2"],
}
EXPORT = dict(
    use_selection=True, use_visible=False, use_active_collection=False, collection="",
    global_scale=1.0, apply_unit_scale=True, apply_scale_options="FBX_SCALE_NONE",
    use_space_transform=True, bake_space_transform=False,
    object_types={"MESH"}, use_mesh_modifiers=False, mesh_smooth_type="OFF",
    use_subsurf=False, use_mesh_edges=False, use_tspace=False, use_triangles=False,
    use_custom_props=False, add_leaf_bones=False, bake_anim=False,
    path_mode="AUTO", embed_textures=False, batch_mode="OFF",
    axis_forward="-Z", axis_up="Y", colors_type="LINEAR", prioritize_active_color=False,
)


def log(m):
    print(time.strftime("%H:%M:%S"), m, flush=True)


def read_file(path):
    root, version = fbxlib.load(path)
    geoms = {o.props[0]: o for o in fbxlib.objects(root, b"Geometry")}
    models = {o.props[0]: o for o in fbxlib.objects(root, b"Model")}
    mats = {o.props[0]: fbxlib.obj_name(o) for o in fbxlib.objects(root, b"Material")}
    kids = {}
    for c in fbxlib.child(root, b"Connections").elems:
        if c.props[0] == b"OO":
            kids.setdefault(c.props[2], []).append(c.props[1])
    out = []
    for uid, m in models.items():
        name = fbxlib.obj_name(m)
        geom = next(geoms[k] for k in kids.get(uid, []) if k in geoms)
        mat_names = [mats[k] for k in kids.get(uid, []) if k in mats]
        g = fbxlib.read_geometry(geom)
        rec = {"model": name, "mesh": fbxlib.obj_name(geom), "materials": mat_names,
               "cp": g["cp"], "corner_cp": g["corner_cp"], "poly_size": g["poly_size"],
               "normals": fbxlib.corner_attribute(g, "LayerElementNormal", "Normals", "NormalsIndex", 3),
               "uv": fbxlib.corner_attribute(g, "LayerElementUV", "UV", "UVIndex", 2),
               "uv_name": g["layers"]["LayerElementUV"][0]["children"].get("Name", "UVMap")}
        if "LayerElementColor" in g["layers"]:
            rec["color"] = fbxlib.corner_attribute(g, "LayerElementColor", "Colors", "ColorIndex", 4)
            rec["color_name"] = g["layers"]["LayerElementColor"][0]["children"].get("Name", "Col")
        out.append(rec)
    return out


def repeated_vertex_faces(corners, sizes):
    poly = np.repeat(np.arange(len(sizes)), sizes).astype(np.int64)
    key = poly * (1 << 32) + corners.astype(np.int64)
    key.sort()
    dup = key[1:] == key[:-1]
    return int(len(np.unique(key[1:][dup] >> 32)))


def drop_repeated_vertex_faces(rec):
    """Remove zero-area faces that reference the same vertex twice (invalid polygons)."""
    sizes = np.asarray(rec["poly_size"], np.int64)
    corners = np.asarray(rec["corner_cp"], np.int64)
    poly = np.repeat(np.arange(len(sizes)), sizes)
    key = poly * (1 << 32) + corners
    order = np.sort(key)
    bad = np.unique(order[1:][order[1:] == order[:-1]] >> 32)
    if len(bad) == 0:
        return 0
    keep_poly = np.ones(len(sizes), bool)
    keep_poly[bad] = False
    keep_corner = keep_poly[poly]
    for k in ("corner_cp", "normals", "uv", "color"):
        if k in rec:
            rec[k] = np.asarray(rec[k])[keep_corner]
    rec["poly_size"] = sizes[keep_poly]
    return int(len(bad))


def build(rec, materials):
    dropped = drop_repeated_vertex_faces(rec)
    cp = np.ascontiguousarray(rec["cp"], np.float32)
    corners = np.ascontiguousarray(rec["corner_cp"], np.int32)
    sizes = np.asarray(rec["poly_size"], np.int32)
    starts = np.concatenate([[0], np.cumsum(sizes)[:-1]]).astype(np.int32)
    me = bpy.data.meshes.new(rec["mesh"])
    me.vertices.add(len(cp))
    me.vertices.foreach_set("co", cp.ravel())
    me.loops.add(len(corners))
    me.loops.foreach_set("vertex_index", corners)
    me.polygons.add(len(sizes))
    me.polygons.foreach_set("loop_start", starts)
    me.update(calc_edges=True)
    uvl = me.uv_layers.new(name=rec["uv_name"])
    uvl.data.foreach_set("uv", np.ascontiguousarray(rec["uv"], np.float32).ravel())
    n = np.asarray(rec["normals"], np.float64)
    n /= np.maximum(np.linalg.norm(n, axis=1), 1e-20)[:, None]
    attr = me.attributes.new("custom_normal", "FLOAT_VECTOR", "CORNER")
    attr.data.foreach_set("vector", n.astype(np.float32).ravel())
    if "color" in rec:
        col = me.color_attributes.new(rec["color_name"], "FLOAT_COLOR", "CORNER")
        col.data.foreach_set("color", np.ascontiguousarray(rec["color"], np.float32).ravel())
    for mname in rec["materials"]:
        if mname not in materials:
            materials[mname] = bpy.data.materials.new(mname)
            assert materials[mname].name == mname, f"material name changed: {materials[mname].name}"
        me.materials.append(materials[mname])
    ob = bpy.data.objects.new(rec["model"], me)
    bpy.context.scene.collection.objects.link(ob)
    assert ob.name == rec["model"] and me.name == rec["mesh"], (ob.name, me.name)
    # read-back checks
    cn = np.zeros(len(corners) * 3, np.float32)
    me.corner_normals.foreach_get("vector", cn)
    dev = np.degrees(np.arccos(np.clip((cn.reshape(-1, 3) * n).sum(1), -1, 1)))
    uv_back = np.zeros(len(corners) * 2, np.float32)
    me.uv_layers[rec["uv_name"]].data.foreach_get("uv", uv_back)
    stats = {"object": ob.name, "mesh": me.name, "vertices": len(me.vertices), "polygons": len(me.polygons),
             "triangles": int((sizes - 2).sum()), "materials": [m.name for m in me.materials],
             "uvLayers": [u.name for u in me.uv_layers], "colorAttributes": [c.name for c in me.color_attributes],
             "normalReadbackMaxDeg": float(dev.max()), "normalReadbackP99Deg": float(np.percentile(dev, 99)),
             "uvReadbackMaxAbs": float(np.abs(uv_back - np.asarray(rec["uv"], np.float32).ravel()).max()),
             "droppedRepeatedVertexFaces": dropped,
             "facesWithRepeatedVertexAfter": repeated_vertex_faces(corners, sizes)}
    return ob, stats


def main():
    kind = sys.argv[sys.argv.index("--") + 1]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    assert scene.unit_settings.system == "METRIC" and abs(scene.unit_settings.scale_length - 1.0) < 1e-9
    materials = {}
    report = {"exporter": "bpy.ops.export_scene.fbx (Blender %s)" % bpy.app.version_string,
              "settings": {k: (sorted(v) if isinstance(v, set) else v) for k, v in EXPORT.items()},
              "sceneUnits": {"system": scene.unit_settings.system, "scale_length": scene.unit_settings.scale_length},
              "files": {}}
    for name in FILES[kind]:
        src = f"{REJECTED}/{kind}/{name}.fbx.rejected"
        recs = read_file(src)
        objs, stats = [], []
        for rec in recs:
            ob, st = build(rec, materials)
            objs.append(ob)
            stats.append(st)
            log(f"{name}: built {st}")
        for o in bpy.context.scene.objects:
            o.select_set(o in objs)
        bpy.context.view_layer.objects.active = objs[0]
        out = f"{ROOT}/{kind}/{name}.fbx"
        t0 = time.time()
        result = bpy.ops.export_scene.fbx(filepath=out, check_existing=False, **EXPORT)
        log(f"{name}: export {result} {time.time()-t0:.1f}s -> {os.path.getsize(out)/1e6:.1f} MB")
        report["files"][os.path.basename(out)] = {"rebuiltFrom": os.path.relpath(src, ROOT), "objects": stats,
                                                   "bytes": os.path.getsize(out)}
        for o in objs:
            me = o.data
            bpy.data.objects.remove(o)
            bpy.data.meshes.remove(me)
        with open(f"{ROOT}/{kind}/reexport-{kind}.json", "w") as fh:
            json.dump(report, fh, indent=1)
    log("done")


main()
