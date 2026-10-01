"""Ward rooftops: service cables and conduit drops from layout.json, Blender 5.2 headless (1 October 2026).

Spans hang between the masts' pin insulators (or wall hooks) as parabolic catenaries with the sag set in layout.py;
conduits are galvanised tube runs from each mast's junction box across the roof deck, over the coping, round the
cornice and string course and down the side wall into a junction box, cleated every ~0.75 m, then down to the ground.
One GLB per layout group, origin at the group's centre (so each group gets its own LODGroup bounds in Unity).

Run:  $O/blender.sh author_cables.py
Out:  unity/AthenHill/Assets/AthenHill/Art/Rooftops/Models/RT_Lines_<slug>_LOD0/1.glb, Models/lines.json
"""
import bpy, json, math, re, sys
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import author_roof_kit as K
import ward_masonry as WM
from ward_masonry import Part, export, tri_count, finalize_parts

LAYOUT = json.loads((HERE / "layout.json").read_text())


def slug(s):
    return re.sub(r"[^A-Za-z0-9]+", "", s.title())


def span_points(a, b, sag, n):
    return [Vector((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t - 4 * sag * t * (1 - t), a[2] + (b[2] - a[2]) * t))
            for t in [k / n for k in range(n + 1)]]


def build_group(name, cables, lod):
    K.LOD = lod
    WM.set_state(lod, __import__("random").Random(1), "rt_lines")
    WM.reset_materials()
    pts_all = []
    for c in cables:
        pts_all += [c["a"], c["b"]] if c["kind"] == "span" else c["points"]
    o = Vector((round(sum(p[0] for p in pts_all) / len(pts_all), 2), 0.0, round(sum(p[2] for p in pts_all) / len(pts_all), 2)))
    line = Part(f"RT_Lines_{slug(name)}_Cable_LOD{lod}", wear=False)
    metal = Part(f"RT_Lines_{slug(name)}_Metal_LOD{lod}", wear=False)
    for c in cables:
        if c["kind"] == "span":
            L = (Vector(c["b"]) - Vector(c["a"])).length
            n = max(6, int(L * (2.2 if lod == 0 else 1.0)))
            pts = [p - o for p in span_points(c["a"], c["b"], c["sag"], n)]
            K.sweep_tube(line, pts, c["radius"], "VH_Rubber", 6, cap=True, min_sides=4)
            if lod == 0:     # binding at each insulator
                for end, nxt in ((pts[0], pts[1]), (pts[-1], pts[-2])):
                    d = (nxt - end).normalized()
                    line.cyl(tuple(end + d * 0.02), tuple(end + d * 0.09), c["radius"] * 1.6, "VH_Rubber", 6)
        else:
            pts = [Vector(p) - o for p in c["points"]]
            # drop consecutive duplicates
            clean = [pts[0]]
            for p in pts[1:]:
                if (p - clean[-1]).length > 1e-3:
                    clean.append(p)
            K.sweep_tube(metal, clean, c["radius"], "VH_Steel", 8, cap=True, min_sides=4)
            if lod == 0 and c.get("clips"):
                for a, b in zip(clean, clean[1:]):
                    seg = b - a
                    k = int(seg.length / c["clips"])
                    for i in range(1, k + 1):
                        p = a + seg * (i / (k + 1))
                        d = seg.normalized()
                        metal.cyl(tuple(p - d * 0.02), tuple(p + d * 0.02), c["radius"] * 1.7, "VH_Steel", 8)
    coll = bpy.data.collections.new(f"RT_Lines_{slug(name)}_LOD{lod}")
    bpy.context.scene.collection.children.link(coll)
    parts = [p for p in (line, metal) if len(p.bm.faces)]
    finalize_parts(parts)
    objs = [p.build(coll, ao=None, macro=0.0, splash=0.0) for p in parts]
    return objs, [o.x, o.y, o.z]


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    groups = {}
    for c in LAYOUT["cables"]:
        groups.setdefault(c["group"], []).append(c)
    rec = {}
    for name, cables in groups.items():
        entry = {"group": name, "cables": [c["name"] for c in cables], "lods": {}}
        for lod in (0, 1):
            objs, origin = build_group(name, cables, lod)
            export(objs, K.OUT / f"RT_Lines_{slug(name)}_LOD{lod}.glb")
            entry["lods"][f"LOD{lod}"] = tri_count(objs)
            entry["origin"] = origin
            print(f"RT_Lines_{slug(name)} LOD{lod}: {tri_count(objs)} triangles", flush=True)
        entry["id"] = f"Lines_{slug(name)}"
        rec[f"Lines_{slug(name)}"] = entry
    (K.OUT / "lines.json").write_text(json.dumps(rec, indent=1))


if __name__ == "__main__":
    main()
