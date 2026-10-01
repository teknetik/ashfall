"""Layout check for the perimeter walls (1 October 2026): every module's footprint (piers, buttresses, pilasters, rubble
cones, fallen blocks, field repairs, sand at the feet; recorded by author_perimeter_walls.py in
perimeter-walls-<kind>.json) placed as in layout.json, against the scene audit (StreetDressingAudit.DumpBatch: renderers,
colliders, route and landmark markers). Reports every overlap with something that is not a wall, ground or render chunk.

    python3 pw_validate.py <audit.json> [out.json]
"""
import json, math, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MODELS = ROOT / "unity/AthenHill/Assets/AthenHill/Art/PerimeterWalls/Models"
IGNORE = re.compile(r"^(City Render Chunks|Ward perimeter walls|Perimeter wall review cameras|AuthoredWorld/(BLD_|COL_BLD_|ENV_mesa|"
                    r"ENV_sandstone_mesa|ENV_ground|ENV_paving|AAA Environment Dressing/Wall shadow proxy)|Outer Berms/Berms ground|"
                    r"Outer Berms/Boundary colliders|Colonists|Player)")
# small things at the wall foot that rubble or sand may touch without harm (weeds, wear decals)
SOFT = re.compile(r"(weed|growth|scrub|grass|Dusty joint|Leak corner|decal|Sand deposit|stain)", re.I)


def boxes_for(pl, fp):
    th = math.radians(pl["yaw"])
    N = (math.sin(th), math.cos(th))
    A = (N[1], -N[0])
    px, _, pz = pl["pos"]
    out = []
    for b in fp:
        xs, zs = [], []
        for x in b["x"]:
            for z in b["z"]:
                xs.append(px + A[0] * x + N[0] * z)
                zs.append(pz + A[1] * x + N[1] * z)
        out.append(dict(kind=b["kind"], lo=(min(xs), b["y"][0], min(zs)), hi=(max(xs), b["y"][1], max(zs))))
    return out


def overlap(alo, ahi, blo, bhi, pad=0.0):
    return all(alo[i] - pad < bhi[i] and blo[i] - pad < ahi[i] for i in range(3))


def main():
    audit = json.load(open(sys.argv[1]))
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    layout = json.load(open(HERE / "layout.json"))
    fps = {}
    for k in ("NS", "EX", "BW"):
        rec = json.load(open(MODELS / f"perimeter-walls-{k}.json"))
        for mid, m in rec["modules"].items():
            fps[mid] = m.get("footprint", [])
    things = []
    for r in audit["renderers"]:
        if not r["active"] or IGNORE.match(r["path"]) or max(r["size"]) > 60:
            continue
        c, s = r["center"], r["size"]
        things.append(("renderer", r["path"], tuple(c[i] - s[i] / 2 for i in range(3)), tuple(c[i] + s[i] / 2 for i in range(3))))
    for c in audit["colliders"]:
        if IGNORE.match(c["path"]) or max(c["size"]) > 60:
            continue
        cc, s = c["center"], c["size"]
        things.append(("collider", c["path"], tuple(cc[i] - s[i] / 2 for i in range(3)), tuple(cc[i] + s[i] / 2 for i in range(3))))
    for m in audit["markers"]:
        if IGNORE.match(m["path"]):
            continue
        p = m["pos"]
        things.append(("marker", m["path"], (p[0] - 0.4, p[1], p[2] - 0.4), (p[0] + 0.4, p[1] + 1.8, p[2] + 0.4)))
    problems = []
    for pl in layout["placements"]:
        for b in boxes_for(pl, fps.get(pl["module"], [])):
            for kind, path, lo, hi in things:
                if not overlap(b["lo"], b["hi"], lo, hi):
                    continue
                soft = bool(SOFT.search(path)) or b["kind"] == "sand"
                problems.append(dict(wall=pl["wall"], slot=pl["slot"], module=pl["module"], part=b["kind"], what=kind, path=path,
                                     severity="minor" if soft else ("blocking" if kind in ("collider", "marker") else "visual"),
                                     box=[[round(v, 2) for v in b["lo"]], [round(v, 2) for v in b["hi"]]]))
    # one line per (module slot, part, object)
    seen = set()
    rows = []
    for p in problems:
        key = (p["wall"], p["slot"], p["part"], p["path"])
        if key in seen:
            continue
        seen.add(key)
        rows.append(p)
    rows.sort(key=lambda p: ({"blocking": 0, "visual": 1, "minor": 2}[p["severity"]], p["wall"], p["slot"]))
    for p in rows:
        print(f'{p["severity"]:8s} {p["wall"]:20s} {p["slot"]:2d} {p["part"]:9s} {p["what"]:8s} {p["path"][:95]}')
    summary = {s: sum(1 for p in rows if p["severity"] == s) for s in ("blocking", "visual", "minor")}
    print(summary)
    if out_path:
        out_path.write_text(json.dumps(dict(summary=summary, overlaps=rows), indent=1))


if __name__ == "__main__":
    main()
