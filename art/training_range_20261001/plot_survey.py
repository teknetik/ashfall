"""Plan map of the survey (ground height, colliders, active renderers, gameplay markers) -> review/survey-map.png."""
import json, sys
from pathlib import Path
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
HERE = Path(__file__).resolve().parent
d = json.loads((HERE / "survey.json").read_text())
x0, x1, z0, z1 = d["window"]; st = d["gridStep"]
g = np.array([[p[0], p[1], p[2] if p[2] is not None else np.nan] for p in d["grid"]], float)
nx = int(round((x1 - x0) / st)) + 1; nz = int(round((z1 - z0) / st)) + 1
H = g[:, 2].reshape(nz, nx)
win = [float(a) for a in sys.argv[1:5]] if len(sys.argv) > 4 else [x0, x1, z0, z1]
fig, ax = plt.subplots(figsize=(22, 22), dpi=70)
im = ax.imshow(H, origin="lower", extent=[x0 - st / 2, x1 + st / 2, z0 - st / 2, z1 + st / 2], cmap="terrain", vmin=-2, vmax=6)
cs = ax.contour(np.linspace(x0, x1, nx), np.linspace(z0, z1, nz), H, levels=np.arange(-2, 12, .25), colors="k", linewidths=.3)
ax.clabel(cs, cs.levels[::4], fontsize=7)
for r in d["renderers"]:
    if not (r["active"] and r["enabled"]): continue
    (a, _, b), (c, _, e) = r["min"], r["max"]
    if c - a > 25 or e - b > 25: continue
    ax.add_patch(Rectangle((a, b), c - a, e - b, fc="none", ec="#666", lw=.3))
for c in d["colliders"]:
    (a, _, b), (cc, _, e) = c["min"], c["max"]
    if cc - a > 40 or e - b > 40: continue
    ax.add_patch(Rectangle((a, b), cc - a, e - b, fc="#f004" if not c["trigger"] else "none", ec="r", lw=.8))
    ax.text(a, b, c["path"].split("/")[-1][:18], fontsize=5, color="r")
for m in d["markers"]:
    x, _, z = m["pos"]
    ax.plot(x, z, "o", ms=6, color={"npc": "b", "interactable": "m", "target": "k", "landmark": "g", "spawn": "orange"}.get(m["kind"], "c"))
    ax.text(x + .2, z + .2, m["path"].split("/")[-1][:24], fontsize=7)
for c in d["cameras"]:
    x, _, z = c["pos"]; fx, _, fz = c["fwd"]
    ax.arrow(x, z, fx * 2, fz * 2, color="navy", width=.05); ax.text(x, z - .5, c["name"], fontsize=6, color="navy")
ax.set_xlim(win[0], win[1]); ax.set_ylim(win[2], win[3]); ax.set_aspect("equal"); ax.grid(True, lw=.3)
ax.set_xticks(np.arange(int(win[0]), int(win[1]) + 1, 2)); ax.set_yticks(np.arange(int(win[2]), int(win[3]) + 1, 2))
plt.colorbar(im, fraction=.03)
out = HERE / "review" / (sys.argv[5] if len(sys.argv) > 5 else "survey-map.png")
fig.savefig(out, bbox_inches="tight"); print(out)
