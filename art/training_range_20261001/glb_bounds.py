"""Axis-aligned bounds of a GLB (all POSITION accessors with node transforms ignored except translation/scale/rotation via
simple matrix walk). Returns Unity-space (x, y, z) min/max: glTF is +Y up, +Z forward; glTFast maps glTF (x,y,z) -> Unity (-x,y,z)."""
import json, struct, math
from pathlib import Path
import numpy as np


def _mat(node):
    if "matrix" in node:
        return np.array(node["matrix"], float).reshape(4, 4).T
    t = np.array(node.get("translation", [0, 0, 0]), float)
    r = node.get("rotation", [0, 0, 0, 1]); s = np.array(node.get("scale", [1, 1, 1]), float)
    x, y, z, w = r
    R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                  [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                  [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    M = np.eye(4); M[:3, :3] = R * s; M[:3, 3] = t
    return M


def bounds(path, name_filter=None):
    b = Path(path).read_bytes()
    jl = struct.unpack("<I", b[12:16])[0]
    g = json.loads(b[20:20 + jl])
    lo = np.full(3, np.inf); hi = np.full(3, -np.inf)
    def walk(i, M):
        nonlocal lo, hi
        n = g["nodes"][i]; M = M @ _mat(n)
        if "mesh" in n and (name_filter is None or name_filter(n.get("name", ""))):
            for p in g["meshes"][n["mesh"]]["primitives"]:
                a = g["accessors"][p["attributes"]["POSITION"]]
                mn, mx = np.array(a["min"]), np.array(a["max"])
                for c in range(8):
                    v = np.array([mx[0] if c & 1 else mn[0], mx[1] if c & 2 else mn[1], mx[2] if c & 4 else mn[2], 1.0])
                    w = (M @ v)[:3]; lo = np.minimum(lo, w); hi = np.maximum(hi, w)
        for k in n.get("children", []):
            walk(k, M)
    for s in g["scenes"][g.get("scene", 0)]["nodes"]:
        walk(s, np.eye(4))
    # glTF -> Unity: x mirrored
    return [-hi[0], lo[1], lo[2]], [-lo[0], hi[1], hi[2]]


if __name__ == "__main__":
    import sys
    for p in sys.argv[1:]:
        mn, mx = bounds(p, lambda n: not n.startswith("COL_") and "_LOD1" not in n and "_LOD2" not in n)
        print(Path(p).stem, [round(v, 3) for v in mn], [round(v, 3) for v in mx], "size", [round(mx[i] - mn[i], 3) for i in range(3)])
