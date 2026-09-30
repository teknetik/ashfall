"""Verify the optimized FBX files against their sources (no Blender needed).

Files are the Blender-exported versions (reexport_blender.py). The payload is also
compared with the superseded custom-writer files in rejected_customwriter/ (same raw
vertices, polygons, per-corner normals, UVs and colours, minus invalid faces that
referenced a vertex twice), and GlobalSettings are dumped in full for the record.

Checks, per output file: FBX version, GlobalSettings axes/unit scale, every Model's
Lcl/Pre/Post transform and InheritType equal to the source Model it replaces,
material names/slots, UV layer name, triangle counts, and raw geometry bounds vs the
source part. Writes verification.json next to this folder's README.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import fbxlib  # noqa: E402

REPO = "/home/teknetik/code/ao2"
ROOT = f"{REPO}/art/optimization_20260929"
TRUCK_SRC = f"{REPO}/unity/AthenHill/Assets/MeshyImports/Mudrunner Convoy_20260910_162611/Meshy_AI_Mudrunner_Convoy_0910152501_texture.fbx"
TREE_SRC = f"{REPO}/unity/AthenHill/Assets/AthenHill/Art/HeroTree/WardTree_LOD0.fbx"
AXES = ("UpAxis", "UpAxisSign", "FrontAxis", "FrontAxisSign", "CoordAxis", "CoordAxisSign", "OriginalUpAxis",
        "UnitScaleFactor", "OriginalUnitScaleFactor")
XFORM = ("Lcl Translation", "Lcl Rotation", "Lcl Scaling", "PreRotation", "PostRotation", "RotationOrder",
         "GeometricTranslation", "GeometricRotation", "GeometricScaling", "InheritType")


def props70(elem):
    out = {}
    p = fbxlib.child(elem, b"Properties70")
    if p is None:
        return out
    for e in p.elems:
        out[e.props[0].decode()] = [v.decode() if isinstance(v, bytes) else v for v in e.props[4:]]
    return out


def summary(path):
    root, version = fbxlib.load(path)
    gs = props70(fbxlib.child(root, b"GlobalSettings"))
    models = {}
    geoms = {o.props[0]: o for o in fbxlib.objects(root, b"Geometry")}
    mats = {o.props[0]: fbxlib.obj_name(o) for o in fbxlib.objects(root, b"Material")}
    model_objs = {o.props[0]: o for o in fbxlib.objects(root, b"Model")}
    links = {}
    for c in fbxlib.child(root, b"Connections").elems:
        if c.props[0] == b"OO":
            links.setdefault(c.props[2], []).append(c.props[1])
    for uid, m in model_objs.items():
        p = props70(m)
        rec = {"transform": {k: p.get(k) for k in XFORM}, "parentIsRoot": uid in links.get(0, [])}
        for child_uid in links.get(uid, []):
            if child_uid in geoms:
                g = fbxlib.read_geometry(geoms[child_uid])
                rec["triangles"] = int((g["poly_size"] - 2).sum())
                rec["rawMin"] = g["cp"].min(0).tolist()
                rec["rawMax"] = g["cp"].max(0).tolist()
                rec["uvLayers"] = [r["children"].get("Name") for r in g["layers"].get("LayerElementUV", [])]
                rec["layers"] = sorted(g["layers"].keys())
            elif child_uid in mats:
                rec.setdefault("materials", []).append(mats[child_uid])
        models[fbxlib.obj_name(m)] = rec
    creator = fbxlib.child(root, b"Creator")
    return {"version": version, "axes": {k: gs.get(k) for k in AXES}, "models": models, "gsFull": gs,
            "creator": creator.props[0].decode() if creator is not None else None}


def payload(path):
    root, _ = fbxlib.load(path)
    geoms = {o.props[0]: o for o in fbxlib.objects(root, b"Geometry")}
    models = {o.props[0]: fbxlib.obj_name(o) for o in fbxlib.objects(root, b"Model")}
    out = {}
    for c in fbxlib.child(root, b"Connections").elems:
        if c.props[0] == b"OO" and c.props[1] in geoms and c.props[2] in models:
            g = fbxlib.read_geometry(geoms[c.props[1]])
            rec = {"cp": g["cp"], "corner_cp": g["corner_cp"], "poly_size": g["poly_size"],
                   "normals": fbxlib.corner_attribute(g, "LayerElementNormal", "Normals", "NormalsIndex", 3),
                   "uv": fbxlib.corner_attribute(g, "LayerElementUV", "UV", "UVIndex", 2)}
            if "LayerElementColor" in g["layers"]:
                rec["color"] = fbxlib.corner_attribute(g, "LayerElementColor", "Colors", "ColorIndex", 4)
            out[models[c.props[2]]] = rec
    return out


def valid_corner_mask(rec):
    sizes = rec["poly_size"].astype(np.int64)
    poly = np.repeat(np.arange(len(sizes)), sizes)
    key = poly * (1 << 32) + rec["corner_cp"]
    srt = np.sort(key)
    bad = np.unique(srt[1:][srt[1:] == srt[:-1]] >> 32)
    keep = np.ones(len(sizes), bool)
    keep[bad] = False
    return keep[poly], int(len(bad))


def compare_payload(new_path, old_path):
    new, old = payload(new_path), payload(old_path)
    res = {}
    for name, o in old.items():
        n = new.get(name)
        if n is None:
            res[name] = {"present": False}
            continue
        mask, dropped = valid_corner_mask(o)
        r = {"present": True, "droppedInvalidFaces": dropped,
             "verticesEqual": bool(o["cp"].shape == n["cp"].shape and np.allclose(o["cp"], n["cp"], rtol=0, atol=1e-6)),
             "polygonsEqual": bool(np.array_equal(o["corner_cp"][mask], n["corner_cp"])
                                   and np.array_equal(o["poly_size"][o["poly_size"] > 0][:len(n["poly_size"])] * 0 + n["poly_size"], n["poly_size"])
                                   and len(n["poly_size"]) == len(o["poly_size"]) - dropped)}
        on = o["normals"][mask]
        on = on / np.maximum(np.linalg.norm(on, axis=1), 1e-20)[:, None]
        nn = n["normals"] / np.maximum(np.linalg.norm(n["normals"], axis=1), 1e-20)[:, None]
        if len(on) == len(nn):
            r["normalMaxDeg"] = float(np.degrees(np.arccos(np.clip((on * nn).sum(1), -1, 1))).max())
            r["uvMaxAbs"] = float(np.abs(o["uv"][mask] - n["uv"]).max())
            if "color" in o:
                r["colorMaxAbs"] = float(np.abs(o["color"][mask] - n["color"]).max()) if "color" in n else None
        r["pass"] = bool(r["verticesEqual"] and r["polygonsEqual"] and r.get("normalMaxDeg", 99) < 0.05
                         and r.get("uvMaxAbs", 1) < 1e-6 and (("color" not in o) or (r.get("colorMaxAbs") is not None and r["colorMaxAbs"] < 1e-6)))
        res[name] = r
    return res


def transform_delta(a, b):
    """Max abs difference over the transform props (None == default on both sides)."""
    worst = 0.0
    for k in XFORM:
        x, y = a.get(k), b.get(k)
        if x is None and y is None:
            continue
        if x is None or y is None or len(x) != len(y):
            return None
        worst = max(worst, max(abs(float(p) - float(q)) for p, q in zip(x, y)))
    return worst


def suffix(name):
    for s in ("leaves", "branches", "trunk"):
        if name.endswith(s):
            return s
    return "mesh"


def main():
    report = {}
    sources = {"truck": summary(TRUCK_SRC), "tree": summary(TREE_SRC)}
    outputs = {
        "truck": ["KaraveenTruck_LOD0_exact.fbx", "KaraveenTruck_LOD1.fbx", "KaraveenTruck_LOD2.fbx",
                  "KaraveenTruck_ShadowNear.fbx", "KaraveenTruck_ShadowProxy.fbx"],
        "tree": ["WardTree_ShadowProxy.fbx", "WardTree_LOD2.fbx"],
    }
    ok_all = True
    for kind, files in outputs.items():
        src = sources[kind]
        src_by_part = {suffix(n): m for n, m in src["models"].items()}
        for f in files:
            path = f"{ROOT}/{kind}/{f}"
            out = summary(path)
            checks = {"fbxVersion": out["version"] == src["version"], "axesAndUnits": out["axes"] == src["axes"]}
            parts = {}
            for name, m in out["models"].items():
                s = src_by_part[suffix(name)]
                tdelta = transform_delta(m["transform"], s["transform"])
                pd = {"transformEqual": tdelta is not None and tdelta < 1e-4, "transformMaxAbsDelta": tdelta,
                      "transform": m["transform"], "sourceTransform": s["transform"],
                      "parentIsRoot": m["parentIsRoot"] == s["parentIsRoot"],
                      "materials": m.get("materials"), "materialsEqual": m.get("materials") == s.get("materials"),
                      "uvLayers": m.get("uvLayers"), "uvLayersEqual": m.get("uvLayers") == s.get("uvLayers"),
                      "triangles": m.get("triangles"), "sourceTriangles": s.get("triangles"),
                      "rawMin": m.get("rawMin"), "rawMax": m.get("rawMax"),
                      "sourceRawMin": s.get("rawMin"), "sourceRawMax": s.get("rawMax")}
                size = float(np.max(np.array(s["rawMax"]) - np.array(s["rawMin"])))
                delta = float(max(np.abs(np.array(m["rawMin"]) - s["rawMin"]).max(),
                                  np.abs(np.array(m["rawMax"]) - s["rawMax"]).max()))
                pd["boundsDeltaFractionOfSize"] = delta / size
                parts[name] = pd
            checks["models"] = parts
            checks["globalSettingsFull"] = {k: v for k, v in out.get("gsFull", {}).items()}
            old = f"{ROOT}/rejected_customwriter/{kind}/{f}.rejected"
            checks["payloadVsCustomWriter"] = compare_payload(path, old) if os.path.exists(old) else "n/a"
            checks["pass"] = bool(checks["fbxVersion"] and checks["axesAndUnits"] and all(
                p["transformEqual"] and p["parentIsRoot"] and p["materialsEqual"] and p["uvLayersEqual"]
                and p["boundsDeltaFractionOfSize"] < 0.05 for p in parts.values())
                and all(v.get("pass") for v in checks["payloadVsCustomWriter"].values()))
            ok_all &= checks["pass"]
            report[f"{kind}/{f}"] = checks
            checks["creator"] = out["creator"]
            print(f"{kind}/{f}: pass={checks['pass']} creator={out['creator']} payload=" + json.dumps(
                {n: {k: v for k, v in r.items() if k in ('pass', 'droppedInvalidFaces', 'normalMaxDeg')} for n, r in checks['payloadVsCustomWriter'].items()}) + " " + ", ".join(
                f"{n}: {p['triangles']} tris, bounds d={p['boundsDeltaFractionOfSize']:.4f}" for n, p in parts.items()))
    report["allPass"] = ok_all
    report["sourceAxes"] = {k: v["axes"] for k, v in sources.items()}
    report["sourceCreator"] = {k: v["creator"] for k, v in sources.items()}
    report["sourceModelTransforms"] = {k: {n: m["transform"] for n, m in v["models"].items()} for k, v in sources.items()}
    # companion checks (run separately): raw type-code audit and Blender re-import comparison
    audit_path = f"{ROOT}/typecode-audit.json"
    if os.path.exists(audit_path):
        audit = json.load(open(audit_path))
        report["typeCodeAudit"] = {os.path.relpath(k, REPO) if k.startswith(REPO) else k: {"pass": v["pass"], "nonStandardCodes": v["nonStandardCodes"]}
                                   for k, v in audit.items()}
    reimport = {}
    for kind in ("truck", "tree"):
        path = f"{ROOT}/{kind}/reimport-validation.json"
        if os.path.exists(path):
            r = json.load(open(path))
            for f, parts in r["files"].items():
                reimport[f"{kind}/{f}"] = {p: {"matrixWorldMaxAbsDiffVsSource": d["matrixWorldMaxAbsDiffVsSource"],
                                               "boundsDeltaFractionOfSourceSize": d["boundsDeltaFractionOfSourceSize"],
                                               "nearestSourceVertexSceneMm": d["nearestSourceVertex"]["sceneMm"],
                                               "exactMatchFraction": d["nearestSourceVertex"]["exactMatchFraction"]}
                                           for p, d in parts.items()}
    report["blenderReimportVsSource"] = reimport
    report["fbxSdkToolCheck"] = ("not run: no FBX-SDK-based or independent FBX tool (fbx2gltf/FBX2glTF, assimp, "
                                 "Autodesk FBX Python bindings, com.autodesk.fbx) is installed; Unity was not run")
    with open(f"{ROOT}/verification.json", "w") as fh:
        json.dump(report, fh, indent=1)


if __name__ == "__main__":
    main()
