#!/usr/bin/env python3
"""Edge stones and cairns along the Berms road, checkpoint to depot (1 Oct 2026) -> edge_stones.json, layout-check.json,
review/edge-stones-map.png.   uv run --with numpy --with matplotlib python art/berms_road_20261001/edge_stones.py

The Wardens marked the track with fist-to-head-sized stones laid just outside the graded shoulders: irregular spacing,
runs broken where vehicles pulled off or tyres kicked stones out of line (more scattered on the outside of bends), half
sunk in the drift. Two small cairns stand off the outside of the two bends as markers. Pieces are the West Gate pass's Poly
Haven namaqualand rocks (PH_RockA-D, CC0, LOD0 5k / LOD1 1.25k tris; their pivot is the ground-contact centre), uniform
scale only. Edge stones have no collider (like the West Gate scatter); cairn rocks share one box collider per cairn.

Validation (written to layout-check.json, the install refuses placements that fail):
  * every piece stays outside the road's graded width (|offset| >= half width + 0.2 m) and off the pull-off spurs;
  * >= 0.5 m from any non-trigger collider other than the Berms ground (props, structures, walls);
  * >= 2.2 m from gameplay markers (interactables, landmarks, NPCs, droid spawns, encounter roots);
  * >= 0.35 m from the existing scatter rocks/stones (no interpenetration), cairns >= 1.5 m from other renderers' bounds;
  * cairn colliders >= 3 m from markers and outside every route/spur line.
"""
import json, math, random
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
road = json.loads((HERE / "road.json").read_text())
s = json.loads((HERE / "survey.json").read_text())
C = np.array(road["centreline"]); S = np.array(road["along"]); HW = np.array(road["half_width"])
T = np.gradient(C, axis=0); T /= np.linalg.norm(T, axis=1)[:, None]
Nrm = np.stack([T[:, 1], -T[:, 0]], 1)                 # right-hand normal (matches make_splat side sign)
ang = np.unwrap(np.arctan2(T[:, 1], T[:, 0])); curv = np.gradient(ang, S)
rnd = random.Random(1001)
# rock kinds: (prefab, footprint radius at scale 1 (m), height at scale 1 (m))  [from polyhaven-conversion.json]
KINDS = {"PH_RockA": (.115, .15), "PH_RockB": (.11, .08), "PH_RockC": (.105, .09), "PH_RockD": (.1, .12)}

g = np.array(s["grid"], np.float64)
gxs = np.unique(g[:, 0]); gzs = np.unique(g[:, 1])
GY = np.full((len(gzs), len(gxs)), np.nan); GY[np.searchsorted(gzs, g[:, 1]), np.searchsorted(gxs, g[:, 0])] = g[:, 2]


def at(sv):
    i = np.interp(sv, S, np.arange(len(S)))
    i0 = int(min(i, len(S) - 2)); t = i - i0
    c = C[i0] * (1 - t) + C[i0 + 1] * t; n = Nrm[i0] * (1 - t) + Nrm[i0 + 1] * t; n /= np.linalg.norm(n)
    return c, n, float(np.interp(sv, S, HW)), float(np.interp(sv, S, curv))


markers = [m for m in s["markers"] if m["kind"] in ("interactable", "landmark", "npc", "spawn", "encounter", "misc", "target")]
cols = [c for c in s["colliders"] if not c["trigger"] and (c["max"][0] - c["min"][0]) < 40 and (c["max"][2] - c["min"][2]) < 40]
scatter = [r for r in s["renderers"] if r["active"] and r["enabled"] and ("PH_Rock" in r["path"] or "PH_Stones" in r["path"]) and r["path"].endswith("_LOD0")]
others = [r for r in s["renderers"] if r["active"] and r["enabled"] and "Berms ground" not in r["path"] and r not in scatter
          and (r["max"][0] - r["min"][0]) < 30 and (r["max"][2] - r["min"][2]) < 30]
spurs = road["spurs"]


def seg_d(p, a, b):
    a, b, p = np.array(a), np.array(b), np.array(p); d = b - a
    t = np.clip(np.dot(p - a, d) / np.dot(d, d), 0, 1); return float(np.linalg.norm(p - (a + t * d)))


def box_d(p, mn, mx):
    dx = max(mn[0] - p[0], 0, p[0] - mx[0]); dz = max(mn[2] - p[1], 0, p[1] - mx[2]); return math.hypot(dx, dz)


def road_offset(p):
    d = np.linalg.norm(C - p, axis=1); i = int(np.argmin(d))
    return float(np.dot(p - C[i], Nrm[i])), float(S[i]), float(HW[i])


def check(p, r, kind):
    """Returns a list of problems for a piece of footprint radius r at p (x, z)."""
    probs = []
    off, sv, hw = road_offset(p)
    if abs(off) - r < hw + .2 and 0 < sv < S[-1]: probs.append(f"inside road ({abs(off):.2f} < {hw + .2:.2f})")
    for sp in spurs:
        if min(seg_d(p, a, b) for a, b in zip(sp[:-1], sp[1:])) < 1.3 + r: probs.append("on pull-off spur")
    for c in cols:
        if box_d(p, c["min"], c["max"]) < .5 + r: probs.append("near collider " + c["path"][-60:])
    lim = 3.0 if kind == "cairn" else 2.2
    for m in markers:
        if math.hypot(p[0] - m["pos"][0], p[1] - m["pos"][2]) < lim: probs.append("near marker " + m["path"][-50:])
    for q in scatter:
        if box_d(p, q["min"], q["max"]) < .35 + r * .5: probs.append("touches scatter " + q["path"].split("/")[-2][-30:])
    if kind == "cairn":
        for q in others:
            if box_d(p, q["min"], q["max"]) < 1.5: probs.append("cairn near " + q["path"][-50:])
    return probs


pieces, rejected = [], []
S_START, S_END = 14.0, 54.0
for sgn in (-1, 1):
    sv = S_START + rnd.uniform(0, 1.2)
    run_left = rnd.randint(5, 12)
    while sv < S_END:
        c, n, hw, k = at(sv)
        outside_of_bend = (k * sgn) > 0.02             # right side (+n) is the outside of a left turn (k > 0, CCW seen from above)
        step = rnd.uniform(.9, 1.9) * (1.25 if outside_of_bend else 1.0)
        run_left -= 1
        if run_left <= 0:                                # a gap: kicked out, buried or never laid
            sv += rnd.uniform(1.5, 4.0); run_left = rnd.randint(4, 12); continue
        kind = rnd.choice(list(KINDS)); fr, fh = KINDS[kind]
        scale = round(rnd.uniform(1.7, 2.6), 2)
        jitter = rnd.uniform(-.12, .18) + (rnd.uniform(.1, .7) if outside_of_bend and rnd.random() < .35 else 0)
        offset = hw + .45 + fr * scale + jitter
        along_j = rnd.uniform(-.15, .15)
        p = c + n * offset * sgn + np.array([n[1], -n[0]]) * along_j
        piece = {"prefab": kind, "x": round(float(p[0]), 3), "z": round(float(p[1]), 3), "yaw": round(rnd.uniform(0, 360), 1),
                 "tilt": [round(rnd.uniform(-7, 7), 1), round(rnd.uniform(-7, 7), 1)], "scale": scale,
                 "sink": round(rnd.uniform(.28, .45), 2), "group": "Edge stones", "side": "right" if sgn > 0 else "left",
                 "along": round(sv, 2), "r": round(fr * scale, 3), "h": round(fh * scale, 3)}
        probs = check(p, piece["r"], "stone")
        (rejected if probs else pieces).append(dict(piece, problems=probs) if probs else piece)
        sv += step

# cairns off the outside of the bends and at the depot turn-in
# candidate stations (along, preferred) -- the first valid spot near each is used; outside of the bend when curved
CAIRN_S = [(20.5, (19.0, 22.5, 18.0, 24.0)), (44.0, (42.0, 46.0, 40.0, 48.0))]
cairns = []
for s0, alts in CAIRN_S:
    best = None
    for sv in (s0,) + alts:
        c, n, hw, k = at(sv)
        sgn = 1 if k > 0 else -1                          # outside of the bend
        for extra in (1.6, 2.0, 2.4, 2.8, 3.2):
            p = c + n * (hw + extra + .45) * sgn
            if not check(p, .4, "cairn"): best = (sv, p); break
        if best: break
    if best: s0, p = best
    probs = check(p, .4, "cairn")
    base = []
    yaw0 = rnd.uniform(0, 360)
    # three base rocks round the centre, two on them, one capstone (positions relative to the cairn centre; y from
    # the ground at install: tiers stack on the previous tier's top with ~35 % overlap)
    for i in range(3):
        a = math.radians(yaw0 + i * 120 + rnd.uniform(-15, 15)); kind = rnd.choice(["PH_RockA", "PH_RockD"])
        base.append({"prefab": kind, "dx": round(.17 * math.cos(a), 3), "dz": round(.17 * math.sin(a), 3), "tier": 0,
                     "yaw": round(rnd.uniform(0, 360), 1), "scale": round(rnd.uniform(2.3, 2.7), 2), "tilt": [round(rnd.uniform(-10, 10), 1), round(rnd.uniform(-10, 10), 1)]})
    for i in range(2):
        a = math.radians(yaw0 + 60 + i * 180 + rnd.uniform(-20, 20)); kind = rnd.choice(["PH_RockB", "PH_RockC", "PH_RockA"])
        base.append({"prefab": kind, "dx": round(.07 * math.cos(a), 3), "dz": round(.07 * math.sin(a), 3), "tier": 1,
                     "yaw": round(rnd.uniform(0, 360), 1), "scale": round(rnd.uniform(2.0, 2.4), 2), "tilt": [round(rnd.uniform(-12, 12), 1), round(rnd.uniform(-12, 12), 1)]})
    base.append({"prefab": rnd.choice(["PH_RockB", "PH_RockC"]), "dx": 0.0, "dz": 0.0, "tier": 2, "yaw": round(rnd.uniform(0, 360), 1),
                 "scale": round(rnd.uniform(1.6, 1.9), 2), "tilt": [round(rnd.uniform(-8, 8), 1), round(rnd.uniform(-8, 8), 1)]})
    cairns.append({"name": f"Cairn {len(cairns) + 1}", "x": round(float(p[0]), 3), "z": round(float(p[1]), 3), "along": round(float(s0), 2),
                   "rocks": base, "collider": {"size": [.85, .75, .85]}, "problems": probs})

ok = not any(c["problems"] for c in cairns)
out = {"what": "Berms road edge stones (no colliders) and cairns (one box collider each), checkpoint to depot. y is resolved at "
               "install from the Berms ground collider: lowest ground under the footprint minus sink x height.",
       "stretch_along_m": [S_START, S_END], "stones": pieces, "cairns": [{k: v for k, v in c.items() if k != "problems"} for c in cairns]}
(HERE / "edge_stones.json").write_text(json.dumps(out, indent=1))
report = {"stones": len(pieces), "rejected_candidates": len(rejected), "rejection_reasons": {},
          "cairns": len(cairns), "cairn_problems": [c["problems"] for c in cairns], "ok": ok,
          "tris_lod0_all": len(pieces) * 5000 + sum(len(c["rocks"]) for c in cairns) * 5000,
          "tris_lod1_all": len(pieces) * 1250 + sum(len(c["rocks"]) for c in cairns) * 1250}
for r_ in rejected:
    for p_ in r_["problems"]:
        key = p_.split(" (")[0] if p_.startswith("inside") else p_
        report["rejection_reasons"][key] = report["rejection_reasons"].get(key, 0) + 1
(HERE / "layout-check.json").write_text(json.dumps(report, indent=1))
print(json.dumps({k: v for k, v in report.items() if k != "rejection_reasons"}, indent=1))
print("rejections:", report["rejection_reasons"])

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(9, 12))
ax.plot(C[:, 0], C[:, 1], "k-", lw=.8)
for sgn in (-1, 1):
    e = C + Nrm * (HW[:, None] * sgn); ax.plot(e[:, 0], e[:, 1], "k:", lw=.6)
for c in cols:
    ax.add_patch(plt.Rectangle((c["min"][0], c["min"][2]), c["max"][0] - c["min"][0], c["max"][2] - c["min"][2], fc="none", ec="r", lw=.4))
for q in scatter:
    ax.add_patch(plt.Rectangle((q["min"][0], q["min"][2]), q["max"][0] - q["min"][0], q["max"][2] - q["min"][2], fc="#88888880", ec="none"))
for m in markers: ax.plot(m["pos"][0], m["pos"][2], "m.", ms=5)
for sp in spurs: ax.plot([a for a, b in sp], [b for a, b in sp], "c-", lw=2)
for p_ in pieces: ax.add_patch(plt.Circle((p_["x"], p_["z"]), p_["r"], fc="#b07030", ec="k", lw=.3))
for p_ in rejected: ax.plot(p_["x"], p_["z"], "rx", ms=3)
for c in cairns: ax.add_patch(plt.Circle((c["x"], c["z"]), .45, fc="#603010", ec="k")); ax.text(c["x"] + .5, c["z"], c["name"], fontsize=7)
ax.set_xlim(-92, -70); ax.set_ylim(-40, 2); ax.set_aspect("equal"); ax.grid(alpha=.3)
(HERE / "review").mkdir(exist_ok=True); fig.savefig(HERE / "review/edge-stones-map.png", dpi=90, bbox_inches="tight")
