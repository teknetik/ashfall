"""Top-down review map of the city for the night-life layout: active colliders (grey), route segments, NPC/landmark
points, existing lights (from survey.json: yellow = practical night lamps, orange = others), proposed lamps from
night-layout.json if present. Run: uv run --with matplotlib python map_scene.py [out.png] [xmin xmax zmin zmax]"""
import json, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle

HERE = Path(__file__).resolve().parent
EV = HERE.parents[1] / "unity/evidence/night-life/20261001"
A = json.loads((EV / "audit-before.json").read_text())
S = json.loads((EV / "survey.json").read_text()) if (EV / "survey.json").exists() else None
L = json.loads((HERE / "night-layout.json").read_text()) if (HERE / "night-layout.json").exists() else None
out = sys.argv[1] if len(sys.argv) > 1 else str(HERE / "review/map.png")
ext = list(map(float, sys.argv[2:6])) if len(sys.argv) > 5 else [-60, 60, -50, 50]
fig, ax = plt.subplots(figsize=(24, 24 * (ext[3] - ext[2]) / (ext[1] - ext[0])))
fig.subplots_adjust(0.03, 0.03, 0.99, 0.99)
for c in A["colliders"]:
    (x, y, z), (sx, sy, sz) = c["center"], c["size"]
    if sx > 70 or sz > 70 or y + sy / 2 < 0.05: continue
    col = "#999" if y + sy / 2 > 0.7 else "#ccc"
    ax.add_patch(Rectangle((x - sx / 2, z - sz / 2), sx, sz, fc=col, ec="#666", lw=0.3, alpha=0.6))
by = {}
for m in A["markers"]:
    p = m["path"].split("/")
    if len(p) == 2 and (p[0].endswith(" route") or p[0] == "Mining droid route"):
        by.setdefault(p[0], []).append((m["pos"][0], m["pos"][2]))
    elif len(p) == 2 and p[0] in ("Colonists", "Landmarks"):
        if ext[0] <= m["pos"][0] <= ext[1] and ext[2] <= m["pos"][2] <= ext[3]:
            ax.plot(m["pos"][0], m["pos"][2], "g^", ms=6); ax.text(m["pos"][0], m["pos"][2], p[1][:14], fontsize=6, color="g")
for name, pts in by.items():
    xs = [q[0] for q in pts] + [pts[0][0]]; zs = [q[1] for q in pts] + [pts[0][1]]
    ax.plot(xs, zs, "-", color="#3a8", lw=1.2, alpha=0.7)
# renderer footprints (LOD0 / unsplit, active, not huge) for context
for r in A["renderers"]:
    if not (r["active"] and r["enabled"]) or "LOD1" in r["path"] or "LOD2" in r["path"]: continue
    (x, y, z), (sx, sy, sz) = r["center"], r["size"]
    if sx > 30 or sz > 30 or y - sy / 2 > 4.5: continue
    if not (ext[0] - 5 <= x <= ext[1] + 5 and ext[2] - 5 <= z <= ext[3] + 5): continue
    ax.add_patch(Rectangle((x - sx / 2, z - sz / 2), sx, sz, fc="none", ec="#b58", lw=0.25, alpha=0.5))
if S:
    for l in S["lights"]:
        if not l["active"] or not l["enabled"]: continue
        x, z = l["pos"][0], l["pos"][2]
        if not (ext[0] <= x <= ext[1] and ext[2] <= z <= ext[3]): continue
        c = "#f5c400" if l["nightOnly"] else ("#f08000" if l["practical"] else "#c0c")
        ax.add_patch(Circle((x, z), min(l["range"], 12) * 0.5, fc=c, alpha=0.06, ec=c, lw=0.3))
        ax.plot(x, z, "o", color=c, ms=3)
        if (ext[1] - ext[0]) < 70: ax.text(x, z + .3, l["path"].split("/")[-1][:18] + f" r{l['range']:.0f} i{l['intensity']:.1f}", fontsize=5, color="#a60")
if L:
    for f in L.get("fixtures", []):
        x, z = f["pos"][0], f["pos"][2]
        ax.add_patch(Circle((x, z), f.get("range", 10) * 0.5, fc="#08f", alpha=0.08, ec="#08f", lw=0.6))
        if not (ext[0] <= x <= ext[1] and ext[2] <= z <= ext[3]): continue
        ax.plot(x, z, "s", color="#04c", ms=6); ax.text(x + .4, z + .4, f["name"][:22], fontsize=7, color="#04c")
for (name, x, z) in [("Finery court", 8, -16), ("Lattice court", 0, -36.5), ("hill-foot benches", -7.4, 0), ("hall corner", -3, -28.4),
                     ("spawn apron", 40, 0), ("south collapse", 10.5, -43), ("north collapse", -45.5, 43)]:
    if ext[0] <= x <= ext[1] and ext[2] <= z <= ext[3]:
        ax.plot(x, z, "rx", ms=10); ax.text(x, z - 1.2, name, color="r", fontsize=8)
ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3]); ax.set_aspect("equal"); ax.grid(True, lw=0.3)
ax.set_xticks(range(int(ext[0]), int(ext[1]) + 1, 5)); ax.set_yticks(range(int(ext[2]), int(ext[3]) + 1, 5))
ax.tick_params(labelsize=6)
fig.savefig(out, dpi=60); print(out)
