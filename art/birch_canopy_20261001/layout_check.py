"""Placement check for the birch canopy pass (1 Oct 2026). The pass adds no geometry, colliders or props: it swaps the
two birches' meshes for baked copies with identical vertex positions (wind sway <= 0.11 m, crown only, above 3.5 m) and
re-aims the four existing bed uplights in place. What it does place are five disabled review cameras; this checks that
each camera position (player eye height) is clear of every active collider (0.25 m pad), outside the bed rings, and
not on a walker/mechanic/droid route line (0.4 m). Reads the fresh audit (audit-before.json). Exit 1 on a problem."""
import json, math, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
A = json.loads((HERE.parents[1] / "unity/evidence/birch-canopy/20261001/audit-before.json").read_text())
TREES = {"birch 4b": (-16.3392773, -1.85), "birch 3": (-19.6, 25.55)}
CAMS = [("cam_bc_4b_crown", "birch 4b", (6.34, 1.62, 13.85)), ("cam_bc_4b_under", "birch 4b", (2.6, 1.62, 1.4)),
        ("cam_bc_4b_bed", "birch 4b", (3.74, 1.62, 1.25)), ("cam_bc_3_crown", "birch 3", (11.1, 1.62, -4.55)),
        ("cam_bc_3_bed", "birch 3", (3.4, 1.62, 2.05))]
routes = {}
for m in A["markers"]:
    p = m["path"].split("/")
    if len(p) == 2 and (p[0].endswith(" route") or p[0] == "Mining droid route"):
        routes.setdefault(p[0], []).append((m["pos"][0], m["pos"][2]))
def seg_dist(px, pz, a, b):
    (ax, az), (bx, bz) = a, b; dx, dz = bx - ax, bz - az; L = dx * dx + dz * dz
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (pz - az) * dz) / L))
    return math.hypot(px - ax - t * dx, pz - az - t * dz)
problems = []
for name, tree, off in CAMS:
    tx, tz = TREES[tree]; x, y, z = tx + off[0], off[1], tz + off[2]
    for c in A["colliders"]:
        (cx, cy, cz), (sx, sy, sz) = c["center"], c["size"]
        if sx > 70 or sz > 70: continue
        if abs(x - cx) < sx / 2 + .25 and abs(z - cz) < sz / 2 + .25 and abs(y - cy) < sy / 2 + .25:
            problems.append(f"{name} inside {c['path']}")
    for t, (bx, bz) in TREES.items():
        if math.hypot(x - bx, z - bz) < 2.0: problems.append(f"{name} within 2 m of {t}'s trunk/bed")
    for rn, pts in routes.items():
        d = min(seg_dist(x, z, pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts)))
        if d < .4: problems.append(f"{name} on {rn} ({d:.2f} m)")
    print(f"{name}: ({x:.2f}, {y:.2f}, {z:.2f})")
print("problems:", len(problems)); [print(" ", p) for p in problems]
sys.exit(1 if problems else 0)
