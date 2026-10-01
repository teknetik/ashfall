"""Measure the real wall feet (Blender 5.2 headless, 1 October 2026).

Run:  $O/blender.sh probe_faces.py          (after `python3 faces.py`; $O = /home/teknetik/.local/state/ward-programme)

Loads the shipped building models (the eight shops, the Basic General booth, Vanguard Hall and the Ward hill, LOD0) at
their scene transforms, builds a BVH in Unity world metres and, every 5 cm along each face in faces.json, casts rays
towards the wall at 3, 8, 16 and 30 cm above the face's surface. The offset recorded is how far the real surface stands
proud (+) or sits back (-) of the nominal face line; null where nothing is hit within 0.6 m behind it (a door or bay).
Also records the surface height 15 cm in front of the face (deck faces: the porch slabs and podium are in the models).
Writes probe.json. The shops' existing LOD0 sand wedges and glass are left out of the BVH.
"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import faces as FA

ART = ROOT / "unity/AthenHill/Assets/AthenHill/Art"
MODELS = [(ART / f"WardShops/Models/{m}_LOD0.glb", (m, rx, rz, yaw)) for (m, rx, rz, yaw) in FA.SITES.values()]
MODELS += [(ART / "WardShops/Booth/BasicGeneral_LOD0.glb", FA.BOOTH), (ART / "VanguardHall/Models/VanguardHall_LOD0.glb", FA.HALL),
           (ART / "WardHill/Models/WardHill_LOD0.glb", FA.HILL)]
SKIP = ("_Sand_", "_Glass_", "Glass", "Plants", "Litter", "Soil")
HEIGHTS = [0.03, 0.08, 0.16, 0.30]
OUT_D = 0.6


def load_world_tris():
    verts, polys = [], []
    for path, site in MODELS:
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=str(path))
        new = [o for o in set(bpy.data.objects) - before if o.type == "MESH"]
        _, rx, rz, yaw = site
        a = math.radians(yaw)
        ca, sa = math.cos(a), math.sin(a)
        n_obj = 0
        for o in new:
            if any(s in o.name for s in SKIP):
                continue
            n_obj += 1
            M = o.matrix_world
            base = len(verts)
            for v in o.data.vertices:
                b = M @ v.co
                ux, uy, uz = -b.x, b.z, -b.y                       # Blender -> Unity local (glTFast mapping)
                verts.append(Vector((rx + ux * ca + uz * sa, uy, rz - ux * sa + uz * ca)))
            for p in o.data.polygons:
                polys.append([base + i for i in p.vertices])
        print(path.name, "objects", n_obj, "verts so far", len(verts))
        for o in set(bpy.data.objects) - before:
            bpy.data.objects.remove(o, do_unlink=True)
    return BVHTree.FromPolygons(verts, polys, all_triangles=False)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    data = json.loads((HERE / "faces.json").read_text())
    bvh = load_world_tris()
    out = {"heights": HEIGHTS, "faces": {}}
    for f in data["faces"]:
        a, b, n = Vector((f["a"][0], 0, f["a"][1])), Vector((f["b"][0], 0, f["b"][1])), Vector((f["n"][0], 0, f["n"][1]))
        L = f["length"]
        steps = max(1, int(round(L / 0.05)))
        rows = []
        for i in range(steps + 1):
            u = L * i / steps
            p = a.lerp(b, i / steps)
            row = [round(u, 3)]
            for h in HEIGHTS:
                o = p + n * OUT_D + Vector((0, f["y"] + h, 0))
                hit, _, _, d = bvh.ray_cast(o, -n, OUT_D + 0.6)
                row.append(None if hit is None else round(OUT_D - d, 4))
            # surface in front of the face
            o = p + n * 0.15 + Vector((0, f["y"] + 1.2, 0))
            hit, _, _, d = bvh.ray_cast(o, Vector((0, -1, 0)), 1.5)
            row.append(None if hit is None else round(f["y"] + 1.2 - d, 4))
            rows.append(row)
        out["faces"][f["id"]] = rows
    # inside corners: offset of each wall line near the corner (0.15-0.35 m out along the other wall)
    out["corners"] = {}
    for c in data["corners"]:
        p0 = Vector((c["p"][0], 0, c["p"][1]))
        d1, d2 = Vector((c["d1"][0], 0, c["d1"][1])), Vector((c["d2"][0], 0, c["d2"][1]))
        res = {}
        for name, along, nrm in (("a", d1, d2), ("b", d2, d1)):      # wall A runs along d1 (normal d2), B along d2
            offs = []
            for t in (0.15, 0.25, 0.35):
                for h in (0.03, 0.08):
                    o = p0 + along * t + nrm * OUT_D + Vector((0, c["y"] + h, 0))
                    hit, _, _, d = bvh.ray_cast(o, -nrm, OUT_D + 0.6)
                    if hit is not None:
                        offs.append(round(OUT_D - d, 4))
            res[name] = offs
        out["corners"][c["id"]] = res
    (HERE / "probe.json").write_text(json.dumps(out))
    print("probed", len(out["faces"]), "faces")


main()
