"""Re-author container home variants into a scratch folder (never into Unity's Assets) and compare them with the committed
records, so the player-home variant P can be shown not to change WallHomeA/B/C (5 October 2026).

Run:  ~/.local/state/ward-programme/blender.sh art/ward_home_20261005/verify_variants.py -- <tag> homea [homeb homec]
Writes art/ward_home_20261005/scratch/<tag>/<Model>_LOD{0,1,2}.glb + <key>.json and prints a comparison of each json and
of every object's triangle count and vertex-position checksum with the committed Assets/.../WardBuildings/Models files.
"""
import bpy, json, hashlib, struct, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "art/ward_buildings_20261003"))
import author_buildings as AB                       # noqa: E402
from ward_masonry import export, tri_count         # noqa: E402

COMMITTED = ROOT / "unity/AthenHill/Assets/AthenHill/Art/WardBuildings/Models"


def glb_digest(path):
    """Per-mesh (name, triangle count, sha1 of the sorted POSITION values rounded to 0.1 mm) from a GLB, without
    importing it. Sorted because the kit's bevels iterate Python sets of BMEdges, so vertex order (not geometry) varies
    from run to run (the unmodified 3 Oct script reproduces the committed rubble with a different vertex order)."""
    data = path.read_bytes()
    jlen = struct.unpack_from("<I", data, 12)[0]
    gj = json.loads(data[20:20 + jlen])
    bin_off = 20 + jlen + 8
    out = {}
    for mesh in gj["meshes"]:
        tris, pts = 0, []
        for prim in mesh["primitives"]:
            acc = gj["accessors"][prim["indices"]]
            tris += acc["count"] // 3
            pa = gj["accessors"][prim["attributes"]["POSITION"]]
            bv = gj["bufferViews"][pa["bufferView"]]
            start = bin_off + bv.get("byteOffset", 0) + pa.get("byteOffset", 0)
            vals = struct.unpack_from(f"<{pa['count'] * 3}f", data, start)
            pts += [tuple(round(v * 1e4) for v in vals[i:i + 3]) for i in range(0, len(vals), 3)]
        out[mesh["name"]] = (tris, hashlib.sha1(repr(sorted(pts)).encode()).hexdigest()[:12])
    return out


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    tag, keys = args[0], args[1:]
    out = HERE / "scratch" / tag
    out.mkdir(parents=True, exist_ok=True)
    AB.OUT = out
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for key in keys:
        fn, fn2 = AB.BUILDINGS[key]
        report = {"source": "art/ward_buildings_20261003/author_buildings.py", "date": "2026-10-03", "building": key,
                  "units": "Unity metres local to the building root (street-face centre at ground level, +Z = street side)", "lods": {}}
        model = None
        for lod in (0, 1):
            b = fn(lod)
            objs = b.finish()
            export(objs, out / f"{b.name}_LOD{lod}.glb")
            report["lods"][f"LOD{lod}"] = {"triangles": b.rec["triangles"], "objects": b.rec["objects"]}
            if lod == 0:
                report.update({k: v for k, v in b.rec.items() if k not in ("triangles", "objects")})
                model = b.name
        objs = fn2()
        export(objs, out / f"{model}_LOD2.glb")
        report["lods"]["LOD2"] = {"triangles": tri_count(objs)}
        (out / f"{key}.json").write_text(json.dumps(report, indent=1))
        ref = COMMITTED / f"{key}.json"
        if ref.exists():
            same = json.loads(ref.read_text()) == json.loads((out / f"{key}.json").read_text())
            print(f"VERIFY {key}.json identical to committed: {same}", flush=True)
            for lod in (0, 1, 2):
                a, b_ = COMMITTED / f"{model}_LOD{lod}.glb", out / f"{model}_LOD{lod}.glb"
                da, db = glb_digest(a), glb_digest(b_)
                print(f"VERIFY {model}_LOD{lod}: meshes identical (tris + positions): {da == db}", flush=True)
                if da != db:
                    for n in sorted(set(da) | set(db)):
                        if da.get(n) != db.get(n):
                            print(f"   {n}: committed {da.get(n)}  scratch {db.get(n)}", flush=True)
        else:
            print(f"VERIFY {key}: no committed record (new variant)", flush=True)


main()
