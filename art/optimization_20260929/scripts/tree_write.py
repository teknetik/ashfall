"""Write the final tree FBX files: v2 simplified-card leaves + wood from tree_proxies.py.

WardTree_ShadowProxy.fbx = Shadow_leaves_v2 (25% of cards, ~9 tris/card, k 1.81) +
                           shadow branches (144k position-welded collapse) + shadow trunk (14k)
WardTree_LOD2.fbx        = LOD2_leaves_v2 (50% of cards, ~6 tris/card, k 1.46) +
                           Blender-decimated branches (78.6k) + seam-preserving trunk (15k)
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import meshtools as mt  # noqa: E402
from tree_proxies import write_tree, CACHE, OUT  # noqa: E402

KEYS = ("cp", "corner_cp", "poly_size", "normals", "uv", "color")


def parts_from(npz_path, leaves_path):
    d = np.load(npz_path)
    parts = {p: {k: d[f"{p}_{k}"] for k in KEYS} for p in ("branches", "trunk")}
    lv = np.load(leaves_path)
    parts["leaves"] = {k: lv[k] for k in KEYS}
    return {p: parts[p] for p in ("leaves", "branches", "trunk")}


def main():
    report_path = f"{OUT}/tree-lod-report.json"
    report = json.load(open(report_path))
    for name, prefix, wood, leaves in (
            ("ShadowProxy", "WardTree_Shadow", f"{CACHE}/tree_ShadowProxy.npz", f"{CACHE}/tree_Shadow_leaves_v2.npz"),
            ("LOD2", "WardTree_LOD2", f"{CACHE}/tree_LOD2.npz", f"{CACHE}/tree_LOD2_leaves_v2.npz")):
        parts = parts_from(wood, leaves)
        tri = {p: int((v["poly_size"] - 2).sum()) for p, v in parts.items()}
        tri["total"] = sum(tri.values())
        report[f"{name}_triangles"] = tri
        write_tree(f"{OUT}/WardTree_{name}.fbx", prefix, parts)
        mt.log(f"{name}: {tri}")
    report["final"] = {"ShadowProxy": "leaves v2 (shadowLeavesV2) + shadow_branches + shadow_trunk",
                       "LOD2": "leaves v2 (lod2LeavesV2) + LOD2_branches (Blender) + LOD2_trunk",
                       "supersededLeafSets": ["shadowLeaves_f0.15 / f0.2 whole-card sets", "lod2Leaves whole-card set (v1)"]}
    mt.dump_json(report_path, report)


if __name__ == "__main__":
    main()
