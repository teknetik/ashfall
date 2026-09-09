"""Reproduce capture proposals from the frozen audit, without touching Unity.

The old seven-shop proposals are retained as provenance, not assumed safe. Side
views use front-corner obliques because narrow gaps can put a broadside camera
inside the adjacent shop. Native obstruction/review remains mandatory.
"""
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIT = HERE.parent / "audit"
ROOT = HERE.parents[4]


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bounds(rows):
    lo = [min(r["center"][a] - r["size"][a] / 2 for r in rows) for a in range(3)]
    hi = [max(r["center"][a] + r["size"][a] / 2 for r in rows) for a in range(3)]
    return [(lo[a] + hi[a]) / 2 for a in range(3)], [hi[a] - lo[a] for a in range(3)]


def main():
    audit = read(AUDIT / "current-scene-audit.json")
    briefs = read(AUDIT / "building-repair-briefs.json")
    old = {x["path"]: x for x in read(AUDIT / "capture-requests.json")}
    instances = [r for r in audit["instances"] if r["active"] and r["sourceVisible"] and not r["generated"]]
    mesh = {m["id"]: m for m in audit["meshes"]}
    buildings, assigned = [], set()
    for brief in sorted(briefs, key=lambda x: x["name"]):
        path = brief["path"]
        main_rows = [r for r in instances if r["path"] == path or r["path"].startswith(path + "/")]
        assert main_rows, path
        center, size = bounds(main_rows)
        x, cy, z = center
        sx, sy, sz = size
        ground = cy - sy / 2
        identifier = re.sub(r"[^a-z0-9]+", "_", brief["name"].lower()).strip("_")
        is_shop = "BLD_shop_" in path or brief["name"] == "Finery"
        front = [-1 if x > 0 else 1, 0, 0] if is_shop else [0, 0, 1]
        right = [front[2], 0, -front[0]]
        depth = sx / 2 if front[0] else sz / 2
        width = sz / 2 if front[0] else sx / 2

        def point(f, side, y):
            return [x + front[0] * f + right[0] * side, y, z + front[2] * f + right[2] * side]

        # Keep the front camera at player height. A whole-roof overview is separate.
        views = [
            ("front", point(depth + max(6, sy * .9), 0, ground + 1.8), point(0, 0, ground + sy * .45), 65),
            ("door", point(depth + 1.7, 0, ground + 1.6), point(depth - .12, 0, ground + 1.5), 68),
            ("side_left", point(depth + 1.8, -width - 1.8, ground + 1.8), point(0, -width + .15, ground + min(3.2, sy * .5)), 68),
            ("side_right", point(depth + 1.8, width + 1.8, ground + 1.8), point(0, width - .15, ground + min(3.2, sy * .5)), 68),
            ("back", point(-depth - max(4, sy * .5), 0, ground + 1.8), point(-depth + .12, 0, ground + sy * .4), 68),
            ("roof", point(depth + 4, -width - 3, ground + sy + max(4, width)), point(0, 0, ground + sy - .4), 60),
        ]
        roots = [path.rsplit("/", 1)[0]] if path.endswith("/Meshy visual") else [path]
        match = re.search(r"BLD_shop_[we]_\d\d", path)
        shop_id = match.group() if match else "BLD_shop_w_01" if brief["name"] == "Finery" else None
        context_prefixes = ["AuthoredWorld/" + shop_id + "_", "Post-war salvage/" + shop_id + " repaired/"] if shop_id else []
        if brief["name"] == "Basic General":
            context_prefixes += ["AuthoredWorld/BLD_general_"]
        if brief["name"] == "Vanguard Hall":
            context_prefixes += ["AuthoredWorld/BLD_hall_"]
        context = [r for r in instances if any(r["path"].startswith(p + "/") or r["path"] == p for p in roots)
                   or any(r["path"].startswith(p) for p in context_prefixes)]
        for r in context:
            assigned.add(r["path"])
        buildings.append({"id": identifier, "name": brief["name"], "category": "primary building", "primaryPath": path,
                          "center": center, "size": size, "frontNormal": front,
                          "sourceInstances": [dict(r, meshRecord=mesh[r["meshId"]]) for r in context],
                          "previousProposal": old.get(path), "reviewStatus": "not captured by this tooling; not reviewed",
                          "views": [{"name": "cam_audit_" + identifier + "_" + kind, "kind": kind, "position": p,
                                     "target": target, "fov": fov, "status": "proposed; requires native framing and occlusion review"}
                                    for kind, p, target, fov in views]})
    unassigned = [r for r in instances if r["path"] not in assigned and
                  ("/BLD_" in r["path"] or "gate" in r["meshPath"].lower())]
    plan = {"schema": 1, "basis": "frozen saved scene audit", "capturedUtc": audit["capturedUtc"],
            "snapshotSha256": digest(AUDIT / "current-scene-audit.json"), "fingerprint": audit["fingerprint"],
            "scope": "All 10 active primary buildings, every placement separately; gates/boundary architecture listed outside this set.",
            "captureContract": {"width": 1920, "height": 1080, "renderScale": 1, "actorCount": 9,
                                "imagesAreVisualAcceptance": False, "sideCoverage": "Two pedestrian corner obliques; inspect hidden regions separately if occluded."},
            "buildings": buildings, "architectureOutsidePrimaryBuildingSet": unassigned}
    (HERE / "building-capture-plan.json").write_text(json.dumps(plan, indent=2) + "\n")

    props = []
    for i in range(3):
        prefix = f"PROP_hill_market_{i:02d}"
        rows = [r for r in instances if r["path"].startswith("AuthoredWorld/" + prefix + "_")]
        cols = [c for c in audit["colliders"] if c["path"].startswith("AuthoredWorld/COL_" + prefix + "_")]
        c, s = bounds(rows)
        body = next(r for r in rows if r["path"].endswith("_body"))
        props.append({"slot": prefix, "bodyCenter": body["center"], "combinedCenter": c, "combinedSize": s,
                      "baseY": 1.5, "frontNormal": [0, 0, 1], "interactions": [],
                      "functionAssignment": "Unassigned: existing code provides no save/reclaim interaction.",
                      "instances": [dict(r, meshRecord=mesh[r["meshId"]]) for r in rows], "colliders": cols})
    code = ROOT / "unity/AthenHill/Assets/AthenHill/Scripts/GameSession.cs"
    platform = {"basis": "frozen scene inventory; current GameSession code checked separately", "capturedUtc": audit["capturedUtc"],
                "snapshotSha256": digest(AUDIT / "current-scene-audit.json"), "slots": props,
                "missionTerminalsExcluded": [r for r in instances if r["path"].startswith("Mission Terminal Upgrade/")],
                "latticeExcluded": [r for r in instances if r["path"].startswith("AuthoredWorld/PROP_lattice_terminal_")],
                "interactionCode": {"path": str(code.relative_to(ROOT)), "sha256": digest(code),
                                    "evidence": "GameSession.Prompt / Interact target nearest NPC, Lattice or Ring only; hillPoint tracks visitation, not a terminal verb."}}
    (HERE / "tree-platform-targets.json").write_text(json.dumps(platform, indent=2) + "\n")
    print(json.dumps({"buildings": len(buildings), "cameras": sum(len(b["views"]) for b in buildings),
                      "architectureInstancesOutsidePrimarySet": len(unassigned), "treePlatformProps": len(props)}))


if __name__ == "__main__":
    main()
