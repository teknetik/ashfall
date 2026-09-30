"""Stage A/B for the Ward oasis tree: extract LOD0 parts and analyse leaf cards.

Source (read-only): unity/AthenHill/Assets/AthenHill/Art/HeroTree/WardTree_LOD0.fbx
Writes cache/tree_<part>.npz (per-corner arrays) and cache/tree_cards.npz.
"""
import os
import sys

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

sys.path.insert(0, os.path.dirname(__file__))
import fbxlib  # noqa: E402
import meshtools as mt  # noqa: E402

REPO = "/home/teknetik/code/ao2"
SRC = f"{REPO}/unity/AthenHill/Assets/AthenHill/Art/HeroTree/WardTree_LOD0.fbx"
CACHE = f"{REPO}/art/optimization_20260929/cache"
PARTS = {"WardTree_LOD0_leaves": "leaves", "WardTree_LOD0_branches": "branches", "WardTree_LOD0_trunk": "trunk"}


def main():
    mt.log("parse")
    root, version = fbxlib.load(SRC)
    geoms = {o.props[0]: o for o in fbxlib.objects(root, b"Geometry")}
    models = {o.props[0]: fbxlib.obj_name(o) for o in fbxlib.objects(root, b"Model")}
    conns = fbxlib.child(root, b"Connections")
    geom_of_model = {}
    for c in conns.elems:
        if c.props[0] == b"OO" and c.props[1] in geoms and c.props[2] in models:
            geom_of_model[models[c.props[2]]] = c.props[1]
    summary = {}
    for model, part in PARTS.items():
        g = fbxlib.read_geometry(geoms[geom_of_model[model]])
        normals = fbxlib.corner_attribute(g, "LayerElementNormal", "Normals", "NormalsIndex", 3)
        uv = fbxlib.corner_attribute(g, "LayerElementUV", "UV", "UVIndex", 2)
        color = fbxlib.corner_attribute(g, "LayerElementColor", "Colors", "ColorIndex", 4)
        tri_corners, poly_of_tri = fbxlib.triangulate(g["poly_start"], g["poly_size"])
        np.savez(f"{CACHE}/tree_{part}.npz", cp=g["cp"], corner_cp=g["corner_cp"], poly_start=g["poly_start"],
                 poly_size=g["poly_size"], normals=normals.astype(np.float32), uv=uv.astype(np.float32),
                 color=color.astype(np.float32), tri_corners=tri_corners, poly_of_tri=poly_of_tri,
                 geometry_uid=geoms[geom_of_model[model]].props[0])
        summary[part] = {"model": model, "controlPoints": int(len(g["cp"])), "polygons": int(len(g["poly_size"])),
                         "triangles": int(len(tri_corners)), "polySizes": np.bincount(g["poly_size"]).tolist()}
        mt.log(f"{part}: {summary[part]}")
    del root

    mt.log("leaf cards")
    d = np.load(f"{CACHE}/tree_leaves.npz")
    cp, corner_cp = d["cp"], d["corner_cp"]
    ps, psz = d["poly_start"], d["poly_size"]
    nxt = np.arange(len(corner_cp)) + 1
    ends = ps + psz - 1
    nxt[ends] = ps
    a, b = corner_cp, corner_cp[nxt]
    g = coo_matrix((np.ones(len(a), np.int8), (a, b)), shape=(len(cp), len(cp)))
    ncomp, label = connected_components(g, directed=False)
    tri = d["tri_corners"]
    tri_cp = corner_cp[tri]
    p0, p1, p2 = cp[tri_cp[:, 0]], cp[tri_cp[:, 1]], cp[tri_cp[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(p1 - p0, p2 - p0), axis=1)
    centroid_tri = (p0 + p1 + p2) / 3
    card_of_tri = label[tri_cp[:, 0]]
    card_area = np.bincount(card_of_tri, weights=area, minlength=ncomp)
    card_tris = np.bincount(card_of_tri, minlength=ncomp)
    cen = np.stack([np.bincount(card_of_tri, weights=area * centroid_tri[:, i], minlength=ncomp)
                    for i in range(3)], 1) / np.maximum(card_area, 1e-30)[:, None]
    # card extent (max vertex distance from centroid)
    dist = np.linalg.norm(cp - cen[label], axis=1)
    radius = np.zeros(ncomp)
    np.maximum.at(radius, label, dist)
    card_of_poly = label[corner_cp[ps]]
    np.savez(f"{CACHE}/tree_cards.npz", label=label, card_of_tri=card_of_tri, card_of_poly=card_of_poly,
             card_area=card_area, card_tris=card_tris, centroid=cen, radius=radius, tri_area=area)
    summary["leafCards"] = {"cards": int(ncomp), "trisPerCard": np.percentile(card_tris, [5, 50, 95]).tolist(),
                            "cardAreaM2": np.percentile(card_area, [5, 50, 95]).tolist(),
                            "cardRadiusM": np.percentile(radius, [5, 50, 95]).tolist(),
                            "totalLeafAreaM2": float(area.sum())}
    mt.log(f"cards: {summary['leafCards']}")
    mt.dump_json(f"{REPO}/art/optimization_20260929/tree/tree-source-summary.json", summary)


if __name__ == "__main__":
    os.makedirs(f"{REPO}/art/optimization_20260929/tree", exist_ok=True)
    main()
