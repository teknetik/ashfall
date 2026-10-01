#!/usr/bin/env python3
"""Query the audit: q.py x0 x1 z0 z1 [c|r|all] [minbottom] — colliders and active renderers whose footprint touches the box."""
import json, sys
from pathlib import Path
A = json.loads((Path(__file__).resolve().parents[2] / "unity/evidence/shade-sails/20261001/audit-before.json").read_text())
x0, x1, z0, z1 = map(float, sys.argv[1:5]); what = sys.argv[5] if len(sys.argv) > 5 else "all"; mb = float(sys.argv[6]) if len(sys.argv) > 6 else -9
def hit(c, s): return not (c[0] + s[0] / 2 < x0 or c[0] - s[0] / 2 > x1 or c[2] + s[2] / 2 < z0 or c[2] - s[2] / 2 > z1)
if what in ("c", "all"):
    for c in A["colliders"]:
        if c["size"][0] > 70 or c["size"][2] > 70: continue
        if hit(c["center"], c["size"]) and c["center"][1] - c["size"][1] / 2 >= mb:
            (x, y, z), (sx, sy, sz) = c["center"], c["size"]
            print(f"C {c['path'][:80]:80s} x {x-sx/2:6.2f}..{x+sx/2:6.2f} z {z-sz/2:6.2f}..{z+sz/2:6.2f} y {y-sy/2:5.2f}..{y+sy/2:5.2f} yaw {c.get('yaw',0):.0f}")
if what in ("r", "all"):
    for r in A["renderers"]:
        if not r["active"]: continue
        if any(f"LOD{k}" in r["path"] for k in (1, 2, 3)): continue
        if r["size"][0] > 40 or r["size"][2] > 40: continue
        if hit(r["center"], r["size"]) and r["center"][1] - r["size"][1] / 2 >= mb:
            (x, y, z), (sx, sy, sz) = r["center"], r["size"]
            print(f"R {r['path'][:80]:80s} x {x-sx/2:6.2f}..{x+sx/2:6.2f} z {z-sz/2:6.2f}..{z+sz/2:6.2f} y {y-sy/2:5.2f}..{y+sy/2:5.2f} {r['tris']}")
