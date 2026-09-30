"""Re-import each new FBX and its SOURCE FBX into fresh Blender scenes with identical
import settings and compare them in world space.

blender -b --factory-startup --python validate_reimport.py -- truck|tree

Per new object: matrix_world vs the matching source object, world bounds vs the source
part, nearest-source-vertex distance for a seeded sample of vertices (exact for meshes
whose vertices are a subset of the source: truck LOD0_exact, tree trunk/branch casters,
LOD2 trunk), and normal agreement on exactly coincident vertices. Distances are also
given in scene millimetres (Unity scene scale). Writes <kind>/reimport-validation.json.
"""
import json
import os
import sys
import time

import bpy
import numpy as np
from mathutils.kdtree import KDTree

ROOT = "/home/teknetik/code/ao2/art/optimization_20260929"
REPO = "/home/teknetik/code/ao2"
SOURCES = {
    "truck": f"{REPO}/unity/AthenHill/Assets/MeshyImports/Mudrunner Convoy_20260910_162611/Meshy_AI_Mudrunner_Convoy_0910152501_texture.fbx",
    "tree": f"{REPO}/unity/AthenHill/Assets/AthenHill/Art/HeroTree/WardTree_LOD0.fbx",
}
FILES = {
    "truck": ["KaraveenTruck_LOD0_exact", "KaraveenTruck_LOD1", "KaraveenTruck_LOD2",
              "KaraveenTruck_ShadowNear", "KaraveenTruck_ShadowProxy"],
    "tree": ["WardTree_ShadowProxy", "WardTree_LOD2"],
}
# raw FBX geometry units -> Unity scene metres (importer scale x FBX cm x scene instance scale)
RAW_TO_SCENE = {"truck": 6.1975354 * 0.65, "tree": 1.0 * 0.88}
IMPORT = dict(use_custom_normals=True, use_image_search=False, global_scale=1.0, bake_space_transform=False,
              use_manual_orientation=False, axis_forward="-Z", axis_up="Y", ignore_leaf_bones=False,
              automatic_bone_orientation=False, use_anim=False)
SAMPLE = 40000


def log(m):
    print(time.strftime("%H:%M:%S"), m, flush=True)


def part_of(name):
    for p in ("leaves", "branches", "trunk"):
        if name.endswith(p):
            return p
    return "mesh"


def import_file(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path, **IMPORT)
    out = {}
    for ob in bpy.context.scene.objects:
        if ob.type != "MESH":
            continue
        me = ob.data
        v = np.zeros(len(me.vertices) * 3, np.float64)
        me.vertices.foreach_get("co", v)
        v = v.reshape(-1, 3)
        M = np.array(ob.matrix_world)
        w = v @ M[:3, :3].T + M[:3, 3]
        cn = np.zeros(len(me.loops) * 3, np.float32)
        me.corner_normals.foreach_get("vector", cn)
        lv = np.zeros(len(me.loops), np.int32)
        me.loops.foreach_get("vertex_index", lv)
        vn = np.zeros((len(me.vertices), 3))
        np.add.at(vn, lv, cn.reshape(-1, 3))
        N = np.linalg.inv(M[:3, :3]).T
        vn = vn @ N.T
        vn /= np.maximum(np.linalg.norm(vn, axis=1), 1e-20)[:, None]
        out[part_of(ob.name)] = {"name": ob.name, "matrix": M, "world": w, "normals": vn,
                                 "polygons": len(me.polygons), "vertices": len(me.vertices),
                                 "materials": [s.material.name if s.material else None for s in ob.material_slots],
                                 "uv": [u.name for u in me.uv_layers]}
    return out


def main():
    kind = sys.argv[sys.argv.index("--") + 1]
    log(f"import source {SOURCES[kind]}")
    src = import_file(SOURCES[kind])
    trees = {}
    for part, d in src.items():
        kd = KDTree(len(d["world"]))
        for i, p in enumerate(d["world"]):
            kd.insert(p, i)
        kd.balance()
        trees[part] = kd
        log(f"source {part}: {d['vertices']} verts, KD ready")
    report = {"importSettings": IMPORT, "source": SOURCES[kind],
              "sourceObjects": {p: {"name": d["name"], "matrixWorld": d["matrix"].tolist(),
                                    "worldMin": d["world"].min(0).tolist(), "worldMax": d["world"].max(0).tolist()}
                                for p, d in src.items()},
              "files": {}}
    rng = np.random.default_rng(29)
    for name in FILES[kind]:
        path = f"{ROOT}/{kind}/{name}.fbx"
        new = import_file(path)
        frec = {}
        for part, d in new.items():
            s = src[part]
            size = float((s["world"].max(0) - s["world"].min(0)).max())
            # world units per scene metre: Blender imports FBX cm with UnitScaleFactor 1 -> 0.01 m per unit
            idx = rng.choice(len(d["world"]), min(SAMPLE, len(d["world"])), replace=False)
            dist = np.empty(len(idx))
            nearest = np.empty(len(idx), np.int64)
            for j, i in enumerate(idx):
                _, k, dd = trees[part].find(d["world"][i])
                dist[j] = dd
                nearest[j] = k
            exact = dist < 1e-6 * size
            dots = (d["normals"][idx] * s["normals"][nearest]).sum(1)
            # object matrix scale = world units per raw FBX unit; raw -> Unity scene metres is known
            mm = RAW_TO_SCENE[kind] * 1000.0 / float(np.linalg.norm(s["matrix"][:3, 0]))
            bmin, bmax = d["world"].min(0), d["world"].max(0)
            smin, smax = s["world"].min(0), s["world"].max(0)
            rec = {
                "object": d["name"], "vertices": d["vertices"], "polygons": d["polygons"],
                "materials": d["materials"], "uvLayers": d["uv"],
                "matrixWorldMaxAbsDiffVsSource": float(np.abs(d["matrix"] - s["matrix"]).max()),
                "worldMin": bmin.tolist(), "worldMax": bmax.tolist(),
                "boundsDeltaFractionOfSourceSize": float(max(np.abs(bmin - smin).max(), np.abs(bmax - smax).max()) / size),
                "nearestSourceVertex": {"fractionOfSourceSize": {"median": float(np.median(dist) / size),
                                                                 "p95": float(np.percentile(dist, 95) / size),
                                                                 "max": float(dist.max() / size)},
                                        "sceneMm": {"median": float(np.median(dist) * mm),
                                                    "p95": float(np.percentile(dist, 95) * mm),
                                                    "max": float(dist.max() * mm)},
                                        "exactMatchFraction": float(exact.mean())},
                "normalsOnExactMatches": ({"count": int(exact.sum()), "meanDot": float(dots[exact].mean()),
                                           "p1Dot": float(np.percentile(dots[exact], 1)),
                                           "fractionDotAbove0.99": float((dots[exact] > 0.99).mean())}
                                          if exact.any() else None),
            }
            frec[part] = rec
            log(f"{name}/{part}: {rec}")
        report["files"][f"{name}.fbx"] = frec
        with open(f"{ROOT}/{kind}/reimport-validation.json", "w") as fh:
            json.dump(report, fh, indent=1)
    log("done")


main()
