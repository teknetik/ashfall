"""Top-down plans of the perimeter strips (from a StreetDressingAudit json) for planning cameras and story beats.
uv run --with matplotlib python plan_map.py <audit.json> <out_prefix>"""
import json, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

a = json.load(open(sys.argv[1]))
prefix = sys.argv[2]
STRIPS = {"north": (-64, 64, 28, 50), "south": (-64, 64, -50, -28), "east": (30, 64, -50, 50), "west": (-66, -34, -50, 50)}
COLS = {"Ward district retrofit": "#2980b9", "Ward street dressing": "#27ae60", "Outer Berms": "#8e44ad",
        "Karaveen": "#d35400", "Meshy Ring Gate": "#16a085", "District rebuild": "#c0392b", "Vanguard Hall": "#7f8c8d"}


def colour(p):
    if "wall" in p.lower() or "boundary" in p.lower():
        return "#c0392b"
    for k, v in COLS.items():
        if p.startswith(k):
            return v
    return "#bbbbbb"


for name, (x0, x1, z0, z1) in STRIPS.items():
    w = 24 if (x1 - x0) > 60 else 10
    fig, ax = plt.subplots(figsize=(w, w * (z1 - z0) / (x1 - x0)))
    labels = {}
    for r in a["renderers"]:
        if not r["active"] or r["path"].startswith("City Render Chunks") or r["path"].startswith("COL_"):
            continue
        cx, cy, cz = r["center"]; sx, sy, sz = r["size"]
        if cx + sx / 2 < x0 or cx - sx / 2 > x1 or cz + sz / 2 < z0 or cz - sz / 2 > z1:
            continue
        if sy < 0.3 and sx * sz > 20:
            continue
        if sx > 150 or sz > 150:
            continue
        p = r["path"]
        ax.add_patch(Rectangle((cx - sx / 2, cz - sz / 2), sx, sz, fill=False, lw=0.4, ec=colour(p), alpha=0.8))
        key = "/".join(p.split("/")[:2])
        labels.setdefault(key, []).append((cx, cz, cy + sy / 2))
    for c in a["colliders"]:
        cx, cy, cz = c["center"]; sx, sy, sz = c["size"]
        if sx > 60 and sz > 60:
            continue
        if cx + sx / 2 < x0 or cx - sx / 2 > x1 or cz + sz / 2 < z0 or cz - sz / 2 > z1:
            continue
        ax.add_patch(Rectangle((cx - sx / 2, cz - sz / 2), sx, sz, fill=True, lw=0.2, ec="k", fc="#f39c12", alpha=0.18))
    for key, pts in labels.items():
        if key.startswith("AuthoredWorld/") and not any(s in key for s in ("wall", "boundary", "berms")):
            continue
        x = sum(p[0] for p in pts) / len(pts); z = sum(p[1] for p in pts) / len(pts); top = max(p[2] for p in pts)
        ax.text(x, z, f"{key.split('/')[-1][:28]} ({top:.1f})", fontsize=6, color=colour(key))
    for m in a["markers"]:
        x, y, z = m["pos"]
        if x0 < x < x1 and z0 < z < z1:
            ax.plot(x, z, "k.", ms=2)
    ax.set_xlim(x0, x1); ax.set_ylim(z0, z1); ax.set_aspect("equal")
    ax.set_xticks(range(int(x0), int(x1) + 1, 2)); ax.set_yticks(range(int(z0), int(z1) + 1, 2))
    ax.tick_params(labelsize=6)
    ax.grid(lw=0.2)
    ax.set_title(f"{name} strip (x east, z north); red = walls, blue = retrofit, green = street dressing")
    fig.savefig(f"{prefix}_{name}.png", dpi=100, bbox_inches="tight")
    plt.close(fig)
