"""Top-down map around the two courtyard birches: active colliders, renderer footprints (low), routes, NPC points,
lights (from the audit-before + survey), tree crowns and proposed review cameras (cams.json if present).
Run: uv run --with matplotlib python map_trees.py out.png xmin xmax zmin zmax"""
import json, sys, math
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle

HERE = Path(__file__).resolve().parent
EV = HERE.parents[1] / "unity/evidence/birch-canopy/20261001"
A = json.loads((EV / "audit-before.json").read_text())
CAMS = json.loads((HERE / "cams.json").read_text()) if (HERE / "cams.json").exists() else []
out = sys.argv[1]; ext = list(map(float, sys.argv[2:6]))
fig, ax = plt.subplots(figsize=(14, 14 * (ext[3] - ext[2]) / (ext[1] - ext[0])))
for c in A["colliders"]:
    (x, y, z), (sx, sy, sz) = c["center"], c["size"]
    if sx > 70 or sz > 70 or y + sy / 2 < 0.05: continue
    if not (ext[0] - 10 <= x <= ext[1] + 10 and ext[2] - 10 <= z <= ext[3] + 10): continue
    col = "#888" if y + sy / 2 > 0.7 else "#ccc"
    ax.add_patch(Rectangle((x - sx / 2, z - sz / 2), sx, sz, fc=col, ec="#555", lw=0.3, alpha=0.6))
by = {}
for m in A["markers"]:
    p = m["path"].split("/")
    if len(p) == 2 and (p[0].endswith(" route") or p[0] == "Mining droid route"):
        by.setdefault(p[0], []).append((m["pos"][0], m["pos"][2]))
    elif len(p) == 2 and p[0] in ("Colonists", "Landmarks"):
        if ext[0] <= m["pos"][0] <= ext[1] and ext[2] <= m["pos"][2] <= ext[3]:
            ax.plot(m["pos"][0], m["pos"][2], "g^", ms=6); ax.text(m["pos"][0], m["pos"][2], p[1][:16], fontsize=6, color="g")
    if p[-1].startswith("cam_") and ext[0] <= m["pos"][0] <= ext[1] and ext[2] <= m["pos"][2] <= ext[3]:
        ax.plot(m["pos"][0], m["pos"][2], "bx", ms=4); ax.text(m["pos"][0], m["pos"][2], p[-1], fontsize=5, color="b")
for name, pts in by.items():
    xs = [q[0] for q in pts] + [pts[0][0]]; zs = [q[1] for q in pts] + [pts[0][1]]
    ax.plot(xs, zs, "-", color="#3a8", lw=1.2, alpha=0.7)
for r in A["renderers"]:
    if not (r["active"] and r["enabled"]): continue
    if r["path"].startswith("birch") and "lod0" in r["path"]:
        (x, y, z), (sx, sy, sz) = r["center"], r["size"]
        ax.add_patch(Circle((x, z), max(sx, sz) / 2, fc="#ec4", alpha=0.25)); ax.text(x, z, r["path"].split("/")[0], fontsize=9)
for cam in CAMS:
    (x, y, z), (tx, ty, tz) = cam["pos"], cam["target"]
    ax.plot(x, z, "ro", ms=5); ax.annotate("", (x + (tx - x) * .4, z + (tz - z) * .4), (x, z), arrowprops=dict(arrowstyle="->", color="r"))
    ax.text(x, z - .6, cam["name"], fontsize=7, color="r")
ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3]); ax.set_aspect("equal"); ax.grid(alpha=.3)
fig.savefig(out, dpi=90)
