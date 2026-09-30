"""Write the rebaked truck LODs (new UV0 + baked-map normals) as FBX via source-tree surgery.

Inputs: cache/truck_<LOD>_geometry.npz (truck_lods.py) and cache/truck_<LOD>_baked_uv.npz
(truck_bake.py). Blender drops coincident duplicate faces when it builds the bake mesh;
collapsed thin sheets produce opposite-winding twins, which are restored here with the
same UVs and flipped normals so both faces of thin parts still render with back-face
culling. Same-winding duplicates are dropped (they would z-fight).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import fbxlib  # noqa: E402
import meshtools as mt  # noqa: E402

REPO = "/home/teknetik/code/ao2"
SRC = f"{REPO}/unity/AthenHill/Assets/MeshyImports/Mudrunner Convoy_20260910_162611/Meshy_AI_Mudrunner_Convoy_0910152501_texture.fbx"
OUT = f"{REPO}/art/optimization_20260929/truck"
CACHE = f"{REPO}/art/optimization_20260929/cache"
LODS = ["LOD1", "LOD2"]


def canonical(t):
    """Rotate each triangle so its smallest index comes first (keeps winding)."""
    r = np.argmin(t, axis=1)
    idx = (np.arange(3)[None, :] + r[:, None]) % 3
    return np.take_along_axis(t, idx, axis=1), idx


def main():
    root, version = fbxlib.load(SRC)
    geom = fbxlib.objects(root, b"Geometry")[0]
    report_path = f"{OUT}/truck-lod-report.json"
    import json
    report = json.load(open(report_path))
    for name in LODS:
        g = np.load(f"{CACHE}/truck_{name}_geometry.npz")
        b = np.load(f"{CACHE}/truck_{name}_baked_uv.npz")
        pos = g["positions"]
        orig = g["tris"].astype(np.int64)
        bt = b["tris"].astype(np.int64)
        buv = b["corner_uv"].reshape(-1, 3, 2)
        bn = b["corner_normals"].reshape(-1, 3, 3)
        # canonicalise Blender triangles (rotation keeps winding), permute corner data alike
        cbt, rot = canonical(bt)
        buv = np.take_along_axis(buv, rot[:, :, None], axis=1)
        bn = np.take_along_axis(bn, rot[:, :, None], axis=1)
        key_b = {tuple(t): i for i, t in enumerate(cbt.tolist())}
        corig, _ = canonical(orig)
        restored_t, restored_uv, restored_n = [], [], []
        seen = set(key_b)
        same_dropped = 0
        for t in corig.tolist():
            tt = tuple(t)
            if tt in seen:
                continue
            rev = (t[0], t[2], t[1])
            if rev in key_b:
                i = key_b[rev]
                restored_t.append(tt)
                # corner order (a, c, b) of the kept face -> (a, b, c) of the twin
                restored_uv.append(buv[i][[0, 2, 1]])
                restored_n.append(-bn[i][[0, 2, 1]])
                seen.add(tt)
            else:
                same_dropped += 1
        tris = cbt
        uv = buv
        nrm = bn
        if restored_t:
            tris = np.concatenate([tris, np.array(restored_t, np.int64)])
            uv = np.concatenate([uv, np.array(restored_uv)])
            nrm = np.concatenate([nrm, np.array(restored_n)])
        # compact vertices
        used, inv = np.unique(tris.ravel(), return_inverse=True)
        corner_cp = inv.ravel()
        label = f"KaraveenTruck_{name}"
        gw = fbxlib.build_geometry_elem(geom, label, pos[used], corner_cp, np.full(len(tris), 3),
                                        normals=nrm.reshape(-1, 3), uv=uv.reshape(-1, 2))
        path = f"{OUT}/{label}.fbx"
        fbxlib.write_surgery(root, version, path, {geom.props[0]: gw}, model_renames={"Mesh_0": label})
        rep = report.setdefault(name, {})
        rep.update({"fbx": path, "trianglesWritten": int(len(tris)),
                    "blenderDroppedDuplicates": int(len(orig) - len(bt)),
                    "restoredOppositeTwins": len(restored_t), "droppedSameWindingDuplicates": same_dropped,
                    "uvIslandsNote": "new UV0: Smart UV Project (66 deg) on a Laplacian-smoothed copy + concave packing",
                    "normals": "smooth with sharp edges > 60 deg on the voxel-remeshed LOD; transferred tangent-space normal map is relative to these (Unity: import normals, CalculateMikk tangents)"})
        mt.log(f"{name}: wrote {path} {len(tris)} tris (restored {len(restored_t)}, dropped {same_dropped})")
    mt.dump_json(report_path, report)


if __name__ == "__main__":
    main()
