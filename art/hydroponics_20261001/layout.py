#!/usr/bin/env python3
"""Ward hydroponics yard layout (1 Oct 2026): plain Python, no Blender. Writes layout.json for Unity
(Editor/HydroponicsPass.cs) and review/layout-map.png (--plot).

Carl: "green houses look bare" -- and for the street props, "lived in, not too messy". The greenhouses are the working
heart of Ward's food supply (lore.md), so the ground around them shows the work: harvest waiting by the door, a potting
bench, seedlings hardening off under shade cloth with herbs drying on a line, a rest bench for the growers, nutrient totes
and a dosing trolley by the pump, compost behind the bays, herbs in the planters between them. Everything stands against
a skin, a wall or under the shade frame; the approaches and the alleys stay open.

Coordinates: Unity world metres (x east, z north, y up); yaw is Unity's (0 faces +Z, 90 faces +X); props face +Z.
Props: "HY_<id>" = Prefabs/Hydroponics (this pass: Blender-authored kit, Poly Haven scans, crate/basket composites that
nest the street kit's scanned yellow crate or wicker basket with a produce fill), "SD_<id>" = Prefabs/StreetDressing.
Run: uv run --with matplotlib python layout.py [--plot]   (needs unity/evidence/hydroponics/20261001/audit-before.json)
"""
import json, math, random, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
AUDIT = ROOT / "unity/evidence/hydroponics/20261001/audit-before.json"
SD_PROPS = ROOT / "unity/AthenHill/Assets/AthenHill/Art/StreetDressing/Props"
HY = ROOT / "unity/AthenHill/Assets/AthenHill/Art/Hydroponics/hy-manifest.json"
rng = random.Random(20261001)

SIZE = {}
for f in ("ph-props.json", "meshy-props.json", "authored-props.json"):
    for k, v in json.loads((SD_PROPS / f).read_text()).items():
        SIZE["SD_" + k] = v["size"]
MAN = json.loads(HY.read_text())
for k, v in MAN["props"].items():
    if not k.startswith("fill_"):
        SIZE["HY_" + k] = v["size"]
COMPOSITES = {   # composite prefab -> (street kit container, fill)
    **{f"HY_crate_{k}": ("SD_crate_yellow", f"fill_crate_{k}") for k in ("lettuce", "cos", "tomato", "beans", "chard", "onion")},
    **{f"HY_basket_{k}": ("SD_basket_flat", f"fill_basket_{k}") for k in ("tomato", "herbs", "beans")},
    **{f"HY_pot_{k}": ("SD_pot_clay", f"fill_pot_{k}") for k in ("basil", "mint", "chard")},
}
for k, (c, f) in COMPOSITES.items():
    SIZE[k] = SIZE[c]

A = json.loads(AUDIT.read_text())
COLS = []
for c in A["colliders"]:
    (x, y, z), (sx, sy, sz) = c["center"], c["size"]
    if sx > 60 or sz > 60:
        continue
    if c["path"].startswith("Ward hydroponics"):   # this pass's own colliders (a re-audit after install)
        continue
    COLS.append((c["path"], x - sx / 2, x + sx / 2, z - sz / 2, z + sz / 2, y - sy / 2, y + sy / 2))

# keep-clear rectangles: doors and thresholds (x0, x1, z0, z1)
CLEAR = [
    ("quonset A east door", -26.3, -25.0, 35.6, 37.8),
    ("quonset B east door", -26.3, -25.0, 27.2, 29.4),
    ("quonset B west door", -42.9, -41.7, 27.2, 29.4),
    ("home 2 door (west end)", -31.6, -30.0, 39.8, 41.6),
    ("home 3 door and the gap between the homes", -24.6, -23.0, 39.8, 41.6),
]
# walking lines kept open (polyline, half width)
WALKS = [
    ("east yard approach to A's door", [(-17.0, 33.0), (-24.0, 33.0), (-24.0, 36.7)], .4),
    ("east yard to the home fronts", [(-17.2, 31.0), (-17.2, 38.9), (-30.0, 38.95)], .5),
    ("south lane", [(-27.0, 23.2), (-44.0, 23.2)], .6),
    ("gap alley (north of the planters)", [(-26.4, 33.05), (-40.9, 33.05)], .3),
    ("gap alley (south of the planters)", [(-26.4, 31.85), (-40.9, 31.85)], .25),
    ("north alley", [(-31.0, 40.35), (-45.0, 40.35)], .35),
]

PL = []


def P(vig, prop, x, z, yaw=0.0, y=0.0, on=None, scale=1.0, note="", within=None):
    """Place prop at (x, z), base at y (or on top of placement `on`, or at y inside placement `within`, e.g. a cart bed).
    Uniform scale only."""
    if prop not in SIZE:
        raise SystemExit(f"unknown prop {prop}")
    if within is not None:
        on = within
    elif on is not None:
        base = PL[on]
        y = base["pos"][1] + SIZE[base["prop"]][1] * base["scale"] - .006
    PL.append({"vignette": vig, "prop": prop, "pos": [round(x, 3), round(y, 3), round(z, 3)], "euler": [0.0, yaw, 0.0],
               "scale": scale, "on": on, "note": note})
    return len(PL) - 1


def j(a=8):
    return rng.uniform(-a, a)


# ---- east yard: nursery under the shade frame ---------------------------------------------------------------------------
v = "Hydroponics yard: nursery under shade"
P(v, "HY_shade_frame", -21.6, 35.2, 0)
P(v, "HY_nursery_table", -21.6, 34.45, 0 + j(1))
P(v, "HY_nursery_table", -21.65, 36.0, 180 + j(1))
P(v, "SD_stool_wood", -23.0, 35.25, 90 + j(), note="sit point: someone pricking out seedlings")
P(v, "SD_watering_can", -20.15, 33.75, 200 + j())
P(v, "HY_crate_lettuce", -20.25, 35.25, 90 + j(4), note="young plants waiting to go in")
# rest bench on the shade edge, facing the tables
v = "Hydroponics yard: growers' rest bench"
P(v, "SD_bench_painted", -18.85, 35.2, -90)
P(v, "SD_churn", -18.8, 34.25, j(30))
P(v, "HY_basket_tomato", -18.75, 36.15, -80)

# ---- east yard: harvest waiting by A's door ---------------------------------------------------------------------------------
v = "Hydroponics yard: harvest by the A door"
pal = P(v, "HY_pallet", -25.25, 34.3, 90)
fills = [["SD_crate_yellow"] * 4, ["HY_crate_lettuce", "HY_crate_tomato", "HY_crate_cos", "HY_crate_chard"], ["HY_crate_beans", "HY_crate_onion"]]
for layer, kinds in enumerate(fills):
    for i, kind in enumerate(kinds):
        dx = -.205 if i % 2 == 0 else .205
        dz = -.258 if i < 2 else .258
        if layer == 2:
            dz = -.258
        y = .133 + layer * .247
        P(v, kind, -25.25 + dx, 34.3 + dz, 90 + j(2.5), y=y)
P(v, "SD_hand_truck", -25.35, 33.25, 200)
P(v, "HY_crate_beans", -25.7, 35.22, 90 + j(4))

v = "Hydroponics yard: herbs by the A door"
P(v, "HY_pot_basil", -25.95, 38.08, j(40))
P(v, "HY_pot_mint", -25.62, 38.12, j(40))
P(v, "HY_pot_chard", -25.3, 38.05, j(40))

v = "Hydroponics yard: cart loaded for the market"
cart = P(v, "SD_handcart", -21.4, 31.95, 0, note="bed floor 0.53 m, bed centre 0.16 m towards -x")
P(v, "HY_crate_tomato", -21.82, 31.95, j(3), y=.53, within=cart)
P(v, "HY_crate_lettuce", -21.30, 31.95, j(3), y=.53, within=cart)

# ---- B's east end: potting bench ------------------------------------------------------------------------------------------------
v = "Hydroponics yard: potting bench"
bench = P(v, "HY_potting_bench", -25.88, 26.12, 90)
P(v, "HY_trowel", -25.95, 26.45, 60, y=.88)
P(v, "SD_stool_wood", -25.05, 26.0, j(), note="sit point at the potting bench")
P(v, "SD_bucket_wood", -25.25, 25.35, j(40))
P(v, "HY_crate_lettuce", -25.85, 30.9, 90 + j(3))
P(v, "HY_basket_herbs", -25.85, 30.9, 90 + j(6), y=.254 - .004)

# ---- south lane: nutrient store along B's skin ----------------------------------------------------------------------------------
v = "Hydroponics south lane: nutrient totes"
tote = P(v, "HY_ibc_tote", -40.05, 24.45, 90, note="hose runs east along the skin")
P(v, "HY_ibc_tote", -41.45, 24.45, -90, note="hose runs west to the pump yard")
for k, (x, z) in enumerate([(-40.25, 24.2), (-39.95, 24.55)]):   # concentrate jugs on the tote's top
    P(v, "HY_nutrient_jug", x, z, j(60), on=tote)
v = "Hydroponics south lane: skin repair"
P(v, "HY_step_ladder", -36.2, 24.6, 0 + j(3), note="under B's tarp patch")
P(v, "SD_crate_yellow", -34.3, 24.82, j(4))
P(v, "SD_crate_yellow", -34.3, 24.82, j(6), on=len(PL) - 1)
P(v, "SD_crate_yellow", -34.3, 24.82, j(6), on=len(PL) - 1)
P(v, "SD_drum_blue", -33.45, 24.8, j(30))

# ---- west: dosing trolley by the pump, the B west door ----------------------------------------------------------------------------
v = "Hydroponics pump yard: dosing"
P(v, "HY_dosing_trolley", -44.45, 33.72, 90)
P(v, "HY_nutrient_jug", -45.4, 32.75, j(40))
P(v, "HY_nutrient_jug", -45.25, 32.6, j(40))
P(v, "HY_hose_ground", -40.7, 32.25, 75)
v = "Hydroponics west door: boots and reel"
P(v, "HY_hose_reel", -42.6, 25.6, 0)
P(v, "SD_stool_wood", -42.45, 26.55, j(20))
P(v, "HY_work_hat", -42.45, 26.55, j(90), y=.44)
P(v, "HY_boots", -42.05, 26.95, 80 + j())

# ---- between the bays: herbs in the retrofit planters ---------------------------------------------------------------------------
v = "Hydroponics gap: herb planters"
for x in (-29.0, -34.0, -39.0):
    P(v, "HY_gap_planter_herbs", x, 32.5, 0 if x != -34.0 else 180)
P(v, "SD_watering_can", -31.6, 32.45, 90 + j())

# ---- north alley: compost behind A ---------------------------------------------------------------------------------------------------
v = "Hydroponics north alley: compost"
P(v, "HY_compost_bays", -41.6, 41.47, 180)
P(v, "SD_bucket_wood", -39.45, 41.25, j(40))
P(v, "HY_spade", -39.0, 41.95, 0, note="leaning on the wall? stands upright at the bay end")

# ------------------------------------------------------------------ validation
ROUND = ("SD_drum", "SD_bucket", "SD_churn", "HY_nutrient_jug", "SD_watering_can")


def dims(p):
    return [v * p["scale"] for v in SIZE[p["prop"]]]


def footprint(p):
    """World corners of the prop's footprint (authored props: their recorded local bounds, else the centred size)."""
    sx, sy, sz = dims(p)
    x, y, z = p["pos"]
    yaw = math.radians(p["euler"][1])
    rec = MAN["props"].get(p["prop"][3:], {}) if p["prop"].startswith("HY_") else {}
    if "footprint" in rec:
        fx0, fx1, fz0, fz1 = [v * p["scale"] for v in rec["footprint"]]
    else:
        fx0, fx1, fz0, fz1 = -sx / 2, sx / 2, -sz / 2, sz / 2
    pts = []
    for lx, lz in ((fx0, fz0), (fx1, fz0), (fx1, fz1), (fx0, fz1)):
        pts.append((x + lx * math.cos(yaw) + lz * math.sin(yaw), z - lx * math.sin(yaw) + lz * math.cos(yaw)))
    return pts


def aabb(pts, shrink=0.0):
    xs = [q[0] for q in pts]; zs = [q[1] for q in pts]
    return min(xs) + shrink, max(xs) - shrink, min(zs) + shrink, max(zs) - shrink


def seg_dist(px, pz, a, b):
    ax, az = a; bx, bz = b
    dx, dz = bx - ax, bz - az
    t = max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / (dx * dx + dz * dz + 1e-9)))
    return math.hypot(px - ax - dx * t, pz - az - dz * t)


def rect_seg_dist(r, a, b):
    """Distance from segment a-b to an axis-aligned rectangle (0 if they intersect), sampled."""
    x0, x1, z0, z1 = r
    best = 1e9
    for t in [i / 40 for i in range(41)]:
        px, pz = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        dx = max(x0 - px, 0, px - x1); dz = max(z0 - pz, 0, pz - z1)
        best = min(best, math.hypot(dx, dz))
    return best


# exceptions: hoses lie across thresholds by design (their footprint includes the coil run); the planter fills sit in the
# retrofit planters; the trowel and hat rest on the bench and stool; the IBC hose runs along the skin.
SOFT = {"HY_hose_ground", "HY_gap_planter_herbs", "HY_trowel", "HY_work_hat", "HY_basket_herbs", "HY_nutrient_jug@top"}
CANOPY = {"HY_shade_frame"}     # only its four posts are solid; things stand under it
for i, p in enumerate(PL):
    if p["prop"] in CANOPY:
        for (px, pz) in footprint(p):
            cx = p["pos"][0] + (px - p["pos"][0]) * .97; cz = p["pos"][2] + (pz - p["pos"][2]) * .97
            COLS.append((f"shade frame post #{i}", cx - .08, cx + .08, cz - .08, cz + .08, 0, 2.4))
IGNORE_COLS = ("Ward street dressing/Hydroponics door",)
problems = []
for i, p in enumerate(PL):
    pts = footprint(p)
    x0, x1, z0, z1 = aabb(pts, .03)
    sx, sy, sz = dims(p)
    y = p["pos"][1]; top = y + sy
    if p["prop"] == "HY_ibc_tote":   # the hose run is not part of the solid footprint
        pts = footprint(dict(p, prop="HY_pallet")) if False else pts
    for (name, cx0, cx1, cz0, cz1, cy0, cy1) in COLS:
        if p["prop"] in SOFT or p["prop"] in CANOPY:
            break
        if cx1 < x0 or cx0 > x1 or cz1 < z0 or cz0 > z1:
            continue
        if cy1 <= y + .03 or cy0 >= top:
            continue
        if any(name.startswith(s) for s in IGNORE_COLS):
            continue
        problems.append((i, "collider " + name))
    for (name, rx0, rx1, rz0, rz1) in CLEAR:
        if p["prop"] in SOFT: continue
        if not (rx1 < x0 or rx0 > x1 or rz1 < z0 or rz0 > z1):
            problems.append((i, "keep-clear " + name))
    for (name, line, half) in WALKS:
        if p["prop"] in SOFT or p["prop"] in CANOPY: continue
        for a, b in zip(line[:-1], line[1:]):
            if rect_seg_dist((x0, x1, z0, z1), a, b) < half:
                problems.append((i, "walk " + name)); break
    for k, q in enumerate(PL):
        if k >= i or q["on"] == i or p["on"] == k or (p["on"] is not None and p["on"] == q["on"]):
            continue
        if p["prop"] in SOFT or q["prop"] in SOFT or p["prop"] in CANOPY or q["prop"] in CANOPY:
            continue
        qx0, qx1, qz0, qz1 = aabb(footprint(q), .03)
        if qx1 < x0 or qx0 > x1 or qz1 < z0 or qz0 > z1:
            continue
        qy, qtop = q["pos"][1], q["pos"][1] + dims(q)[1]
        if qtop <= y + .01 or qy >= top - .01:
            continue
        problems.append((i, f"overlaps #{k} {q['prop']}"))

for i, why in problems:
    p = PL[i]
    print(f"#{i:3d} {p['prop']:22s} {p['vignette'][:42]:42s} {p['pos']} {why}")
print(f"{len(PL)} placements, {len({p['vignette'] for p in PL})} vignettes, {len(problems)} problems")

# ------------------------------------------------------------------ ground decals (the district's weathering atlas)
DECALS = []
for vname, kind, (cx, cz), (w, l), yaw, op in [
    ("Hydroponics yard: nursery under shade", "grime", (-21.6, 35.2), (3.4, 2.8), 2, .35),
    ("Hydroponics yard: nursery under shade", "scuffs", (-21.7, 35.25), (2.6, 1.2), 0, .3),
    ("Hydroponics yard: harvest by the A door", "grime", (-25.0, 34.4), (1.8, 2.0), -4, .4),
    ("Hydroponics yard: harvest by the A door", "scuffs", (-24.6, 36.4), (1.6, 2.2), 90, .3),
    ("Hydroponics yard: potting bench", "grime", (-25.6, 26.1), (1.4, 2.2), 3, .45),
    ("Hydroponics yard: potting bench", "scuffs", (-25.0, 26.4), (1.5, 1.5), 30, .3),
    ("Hydroponics south lane: nutrient totes", "grime", (-40.0, 24.4), (3.6, 1.6), 0, .4),
    ("Hydroponics pump yard: dosing", "grime", (-44.0, 33.5), (2.6, 2.4), 6, .4),
    ("Hydroponics north alley: compost", "grime", (-41.6, 41.2), (4.0, 1.8), 0, .45),
    ("Hydroponics west door: boots and reel", "scuffs", (-42.3, 26.6), (1.4, 1.6), 15, .3),
]:
    DECALS.append({"vignette": vname, "kind": kind, "pos": [cx, 0.0, cz], "size": [w, l], "yaw": yaw, "opacity": op})

# night glow inside the bays (on the city light circuit, night only, no shadows)
LIGHTS = [{"name": f"Grow glow {q} {i}", "pos": [x, 2.55, zc], "color": [1.0, .45, .82], "intensity": 2.2, "range": 7.0}
          for q, zc in (("A", 36.7), ("B", 28.3)) for i, x in enumerate((-37.4, -30.6))]

out = {"source": "art/hydroponics_20261001/layout.py", "date": "2026-10-01", "composites": {k: list(v) for k, v in COMPOSITES.items()},
       "placements": [{k: v for k, v in p.items() if k != "on"} | {"stackedOn": p["on"]} for p in PL],
       "decals": DECALS, "lights": LIGHTS}
(HERE / "layout.json").write_text(json.dumps(out, indent=1))

if "--plot" in sys.argv:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Polygon
    fig, ax = plt.subplots(figsize=(22, 16), dpi=80)
    for (name, x0, x1, z0, z1, y0, y1) in COLS:
        if -50 < x0 < -14 and 18 < z0 < 46:
            ax.add_patch(Rectangle((x0, z0), x1 - x0, z1 - z0, fill=True, fc=(1, 0, 0, .12), ec="r", lw=.8))
            ax.text((x0 + x1) / 2, (z0 + z1) / 2, name.split("/")[-1][:16], fontsize=6, ha="center")
    for (name, x0, x1, z0, z1) in CLEAR:
        ax.add_patch(Rectangle((x0, z0), x1 - x0, z1 - z0, fill=True, fc=(0, .6, 0, .15), ec="g", lw=.8, ls="--"))
    for (name, line, half) in WALKS:
        ax.plot([p[0] for p in line], [p[1] for p in line], "g-", lw=half * 20, alpha=.15)
    bad = {i for i, _ in problems}
    for i, p in enumerate(PL):
        ax.add_patch(Polygon(footprint(p), closed=True, fill=True, fc=(0, 0, 1, .25) if i not in bad else (1, .5, 0, .6), ec="b", lw=.8))
        ax.text(p["pos"][0], p["pos"][2], p["prop"][3:16], fontsize=5, ha="center")
    ax.set_xlim(-50, -15); ax.set_ylim(20, 45); ax.set_aspect("equal"); ax.grid(True, lw=.3)
    (HERE / "review").mkdir(exist_ok=True)
    plt.savefig(HERE / "review" / "layout-map.png", bbox_inches="tight")
    print("plot written")
