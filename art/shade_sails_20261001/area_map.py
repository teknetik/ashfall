#!/usr/bin/env python3
"""Top-down review maps of the shade-sail areas from the fresh scene audit (StreetDressingAudit): active colliders
(grey: walkable-height obstacles, light grey: low), renderer footprints (pink outline: ground objects; blue: overhead
objects whose bottom is above 2.2 m, e.g. bunting, cables, canopies, lamp heads), walker/mechanic/droid routes (green),
NPC/landmark points, lamps (yellow: renderers under the lamp roots), and, if sail-layout.json exists, the sails (corner
polygons), poles and anchors. Run: uv run --with matplotlib python area_map.py [area ...]"""
import json, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, Circle

HERE = Path(__file__).resolve().parent
EV = HERE.parents[1] / "unity/evidence/shade-sails/20261001"
A = json.loads((EV / "audit-before.json").read_text())
L = json.loads((HERE / "sail-layout.json").read_text()) if (HERE / "sail-layout.json").exists() else None
AREAS = {"courtyard": (-4, 22, -26, 2), "market": (-50, -22, -20, 16), "apron": (24, 50, -14, 22), "lattice": (-14, 16, -46, -22),
         "all": (-60, 60, -46, 46)}
LAMP_ROOTS = ("Ward night life", "Ward utility lamps", "Ward west gate arches")


def draw(name, ext):
    fig, ax = plt.subplots(figsize=(16, 16 * (ext[3] - ext[2]) / (ext[1] - ext[0])))
    fig.subplots_adjust(0.04, 0.04, 0.99, 0.97)
    for c in A["colliders"]:
        (x, y, z), (sx, sy, sz) = c["center"], c["size"]
        if sx > 70 or sz > 70 or y + sy / 2 < 0.05: continue
        if not (ext[0] - 10 <= x <= ext[1] + 10 and ext[2] - 10 <= z <= ext[3] + 10): continue
        col = "#888" if y + sy / 2 > 0.7 else "#ccc"
        ax.add_patch(Rectangle((x - sx / 2, z - sz / 2), sx, sz, fc=col, ec="#555", lw=0.4, alpha=0.55))
    for r in A["renderers"]:
        if not r["active"] or "LOD1" in r["path"] or "LOD2" in r["path"] or "LOD3" in r["path"]: continue
        (x, y, z), (sx, sy, sz) = r["center"], r["size"]
        if sx > 30 or sz > 30: continue
        if not (ext[0] - 3 <= x <= ext[1] + 3 and ext[2] - 3 <= z <= ext[3] + 3): continue
        bottom, top = y - sy / 2, y + sy / 2
        lamp = r["path"].split("/")[0] in LAMP_ROOTS
        if lamp:
            ax.add_patch(Rectangle((x - sx / 2, z - sz / 2), sx, sz, fc="#fc0", ec="#a80", lw=0.6, alpha=0.7))
        elif bottom > 2.2 and bottom < 12:
            ax.add_patch(Rectangle((x - sx / 2, z - sz / 2), sx, sz, fc="none", ec="#06c", lw=0.6, alpha=0.8))
            if sx * sz > 0.5 and (ext[1] - ext[0]) < 40:
                ax.text(x, z, f"{r['path'].split('/')[-1][:16]} {bottom:.1f}-{top:.1f}", fontsize=5, color="#06c")
        elif bottom < 4.5:
            ax.add_patch(Rectangle((x - sx / 2, z - sz / 2), sx, sz, fc="none", ec="#b58", lw=0.3, alpha=0.5))
    by = {}
    for m in A["markers"]:
        p = m["path"].split("/")
        if len(p) == 2 and (p[0].endswith(" route") or p[0] == "Mining droid route"):
            by.setdefault(p[0], []).append((m["pos"][0], m["pos"][2]))
        elif len(p) == 2 and p[0] in ("Colonists", "Landmarks"):
            ax.plot(m["pos"][0], m["pos"][2], "g^", ms=7); ax.text(m["pos"][0] + .2, m["pos"][2] + .2, p[1][:16], fontsize=7, color="g")
        elif len(p) == 1 and p[0] in ("Lattice interaction", "Ring interaction"):
            ax.add_patch(Circle((m["pos"][0], m["pos"][2]), 3.0, fc="none", ec="g", lw=1))
    for rn, pts in by.items():
        xs = [q[0] for q in pts] + [pts[0][0]]; zs = [q[1] for q in pts] + [pts[0][1]]
        ax.plot(xs, zs, "-", color="#2a7", lw=2, alpha=0.7)
    if L:
        for s in L["sails"]:
            cs = [(c[0], c[2]) for c in s["corners"]]
            ax.add_patch(Polygon(cs, closed=True, fc=s.get("previewColour", "#d84"), alpha=0.35, ec="#a40", lw=1.2))
            ax.text(sum(c[0] for c in cs) / len(cs), sum(c[1] for c in cs) / len(cs), s["name"], fontsize=8, color="#720", ha="center")
            for p in s.get("poles", []):
                ax.plot(p["base"][0], p["base"][2], "ko", ms=6)
                for g in p.get("guys", []):
                    ax.plot([p["top"][0], g[0]], [p["top"][2], g[2]], "k-", lw=0.6); ax.plot(g[0], g[2], "ks", ms=4)
            for a in s.get("wallAnchors", []):
                ax.plot(a["pos"][0], a["pos"][2], "mD", ms=6)
    ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3]); ax.set_aspect("equal"); ax.grid(True, lw=0.3)
    step = 1 if (ext[1] - ext[0]) <= 40 else 5
    ax.set_xticks(range(int(ext[0]), int(ext[1]) + 1, step)); ax.set_yticks(range(int(ext[2]), int(ext[3]) + 1, step))
    ax.tick_params(labelsize=6); ax.set_title(name)
    out = HERE / f"review/map-{name}.png"; out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=70); plt.close(fig); print(out)


for n in (sys.argv[1:] or ["courtyard", "market", "apron", "lattice"]):
    draw(n, AREAS[n])
