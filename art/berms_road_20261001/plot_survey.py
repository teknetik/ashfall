#!/usr/bin/env python3
"""Plan view of the Berms ground from survey.json: height (hillshade), slope classes, the road polyline, markers,
colliders, existing rock/scatter renderers and decals -> review/survey-map.png (and --slope review/slope-map.png)."""
import json, sys, math
from pathlib import Path
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
s = json.loads((HERE / "survey.json").read_text())
wg = json.loads((HERE.parent / "west_gate_20260926/layout.json").read_text())
v = np.array(s["ground"]["vertices"], np.float32)
xs = np.unique(v[:, 0]); zs = np.unique(v[:, 2])
H = np.full((len(zs), len(xs)), np.nan, np.float32); NY = np.full_like(H, np.nan)
ix = np.searchsorted(xs, v[:, 0]); iz = np.searchsorted(zs, v[:, 2])
H[iz, ix] = v[:, 1]; NY[iz, ix] = v[:, 7]
print("grid", H.shape, "height", np.nanmin(H), np.nanmax(H))
slope = 1 - NY
print("slope 1-ny: >0.03", (slope > .03).mean().round(3), ">0.06", (slope > .06).mean().round(3), ">0.1", (slope > .1).mean().round(3), ">0.2", (slope > .2).mean().round(3))
fig, ax = plt.subplots(figsize=(10, 20))
ext = [xs[0], xs[-1], zs[0], zs[-1]]
gy, gx = np.gradient(H)
shade = np.clip(.6 + (-gx * .7 + gy * .7) * .5, 0, 1)
ax.imshow(H, origin="lower", extent=ext, cmap="terrain", alpha=.9)
ax.imshow(shade, origin="lower", extent=ext, cmap="gray", alpha=.35)
cs = ax.contour(xs, zs, H, levels=np.arange(-2, 12, .5), colors="k", linewidths=.3)
if "--slope" in sys.argv:
    ax.contourf(xs, zs, slope, levels=[.06, .1, .2, 1], colors=["#ffd70080", "#ff8c0090", "#ff000090"])
road = np.array(wg["anchors"]["road"])
ax.plot(road[:, 0], road[:, 1], "w-", lw=2)
for r in s["renderers"]:
    if not r["active"] or not r["enabled"]: continue
    p = r["path"]
    if "Berms ground" in p: continue
    mn, mx = r["min"], r["max"]
    if mx[0] - mn[0] > 30 or mx[2] - mn[2] > 30: continue
    small = (mx[0] - mn[0]) < 1.2 and (mx[2] - mn[2]) < 1.2
    col = "#55555580" if small else "#0000ff40"
    ax.add_patch(plt.Rectangle((mn[0], mn[2]), mx[0] - mn[0], mx[2] - mn[2], fc=col, ec="none"))
for c in s["colliders"]:
    if c["trigger"]: continue
    mn, mx = c["min"], c["max"]
    if mx[0] - mn[0] > 40: continue
    ax.add_patch(plt.Rectangle((mn[0], mn[2]), mx[0] - mn[0], mx[2] - mn[2], fc="none", ec="r", lw=.5))
for d in s["decals"]:
    ax.plot(d["pos"][0], d["pos"][2], "c+", ms=4)
colors = {"landmark": "m", "interactable": "y", "spawn": "r", "encounter": "r", "npc": "b", "target": "k", "misc": "y", "route": "g"}
for m in s["markers"]:
    ax.plot(m["pos"][0], m["pos"][2], "o", color=colors.get(m["kind"], "k"), ms=4)
    if m["kind"] in ("landmark", "encounter"): ax.text(m["pos"][0] + .4, m["pos"][2], m["path"].split("/")[-1], fontsize=6)
for c in s["cameras"]:
    if c["name"].startswith(("cam_berms", "cam_bm", "cam_depot_approach", "cam_westgate_mouth")):
        p, f = c["pos"], c["fwd"]; ax.arrow(p[0], p[2], f[0] * 3, f[2] * 3, color="k", head_width=.6); ax.text(p[0], p[2] - 1, c["name"], fontsize=5)
ax.set_xlim(-106, -56); ax.set_ylim(-56, 50); ax.set_aspect("equal"); ax.grid(alpha=.3)
out = HERE / "review" / ("slope-map.png" if "--slope" in sys.argv else "survey-map.png")
fig.savefig(out, dpi=90, bbox_inches="tight"); print(out)
