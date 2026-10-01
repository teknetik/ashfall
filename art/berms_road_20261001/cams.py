#!/usr/bin/env python3
"""Player-height review cameras for the Berms road ground pass -> review_cameras.json (eye = Berms ground + 1.7 m
unless a fixed height is given; targets on the ground + dy). Ground heights from survey.json (0.5 m grid, bilinear)."""
import json, math
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
s = json.loads((HERE / "survey.json").read_text())
g = np.array(s["grid"], np.float64)
xs = np.unique(g[:, 0]); zs = np.unique(g[:, 1])
G = np.full((len(zs), len(xs)), np.nan); G[np.searchsorted(zs, g[:, 1]), np.searchsorted(xs, g[:, 0])] = g[:, 2]


def ground(x, z):
    fx = np.interp(x, xs, np.arange(len(xs))); fz = np.interp(z, zs, np.arange(len(zs)))
    i0, j0 = int(min(fx, len(xs) - 2)), int(min(fz, len(zs) - 2)); tx, tz = fx - i0, fz - j0
    return float(G[j0, i0] * (1 - tx) * (1 - tz) + G[j0, i0 + 1] * tx * (1 - tz) + G[j0 + 1, i0] * (1 - tx) * tz + G[j0 + 1, i0 + 1] * tx * tz)


# name, eye xz, eye height above ground, target xz, target height above ground, fov, what it judges
VIEWS = [
    ("cam_br_road_bend", (-73.0, -0.6), 1.7, (-84.0, -14.0), 0.0, 60, "road leaving the outpost, the bend, edge stones, wheel paths"),
    ("cam_br_road_south", (-84.4, -13.5), 1.7, (-83.3, -30.0), 0.0, 60, "first-contact stretch towards the depot: crown, shoulders, verge"),
    ("cam_br_road_close", (-84.9, -21.5), 1.6, (-84.6, -17.6), 0.0, 55, "close road surface: ruts, loose gravel crown, windrow, stones"),
    ("cam_br_depot_approach", (-84.0, -24.5), 1.7, (-80.5, -37.0), 0.4, 60, "depot approach and yard apron"),
    ("cam_br_west_slope", (-85.5, -8.5), 1.7, (-100.0, -4.0), 1.0, 60, "west slope: V2 rock/scree on the Berms ground and the toe into the basin"),
    ("cam_br_road_back", (-82.6, -29.5), 1.7, (-77.0, -2.0), 0.0, 60, "looking back to the gate: road, verges, slope on the left"),
    ("cam_br_edge_stones", (-82.7, -14.0), 1.7, (-81.5, -22.0), 0.1, 55, "close run of edge stones and the east windrow: sinking, scale, grounding"),
    ("cam_br_cairn", (-86.1, -28.5), 1.7, (-88.87, -26.7), 0.35, 55, "the depot-bend cairn and the west shoulder"),
]
out = []
for name, (ex, ez), eh, (tx, tz), th, fov, what in VIEWS:
    ey = ground(ex, ez) + eh; ty = ground(tx, tz) + th
    out.append({"name": name, "pos": [ex, round(ey, 3), ez], "target": [tx, round(ty, 3), tz], "fov": fov, "judges": what})
(HERE / "review_cameras.json").write_text(json.dumps(out, indent=1))
for o in out: print(o["name"], o["pos"], o["target"])
