#!/usr/bin/env python3
"""Warden training range layout (1 Oct 2026): plain Python, no Blender. Writes layout.json for Blender
(author_range.py reads the kit dimensions and the revetment/cable paths) and Unity (Editor/TrainingRangePass.cs), and
review/layout-map.png.

Carl: "the training robot section could use work." The range beyond the West Gate (three steel knockdown plates,
a firing bench and the range control) is where recruits learn to shoot before they meet the machines on the service
road. It becomes a working Warden range:
  * a firing point of three timber bays (dividers, benches with sandbag rests, lane boards, painted line) at the
    tutorial's firing line; a range officer's table and a range-orders board;
  * the plates' backstop: the natural mound behind them is built up into an earth berm with a timber revetment and a
    sandbag cap, scarred where the plates' misses land, lane numbers painted on it, red flags on the crest;
  * lane 4, the machine lane: a start frame, a tyre run and two cover barricades for movement drills, a training drone
    on a tether gantry and a stripped worker droid on a steel frame with painted hit zones;
  * a robot service apron behind a blast wall: a shade shelter over drone docks with parked training drones, a repair
    bench, welding cart, compressor, generator and cables;
  * night lighting on the Ward light clock (range floods, work lamp, red "range live" lamp).
The bay floor is cleared of loose scatter rocks (retired, inactive), the old firing bench/sandbags and the flag that
stood in front of the line are retired. Plates, reset station, landmarks, Wardens, locker, board and encounters are
never moved.

Coordinates: Unity world metres. The range frame: origin F = the checkpoint_firingline landmark (-66.2, 7.6), fwd =
down range (yaw -63, WNW), lat = to the right (NNE). yaw_rel 0 faces down range. Ground heights come from the survey
(TrainingRangePass survey: Berms ground raycast grid, 0.5 m).
Run: uv run --with numpy --with matplotlib python layout.py [--plot]
"""
import json, math, random, sys
from pathlib import Path
import numpy as np
from ground import S, ground, top, F, YAW, FWD, RIGHT, W, L
from glb_bounds import bounds

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ASSETS = ROOT / "unity/AthenHill/Assets/AthenHill"
rng = random.Random(20261001)
j = lambda a: rng.uniform(-a, a)

# ------------------------------------------------------------------ gameplay anchors (never moved)
PLATES = {1: (-78.0, 11.0), 2: (-80.5, 15.5), 3: (-77.5, 20.0)}
PLATE_AIM_H = 1.03             # Health.aimOffset
EYE = 1.66                     # player eye / review camera height above ground at the firing line
BAYS = {1: 0.0, 2: 1.6, 3: 3.2}   # bay centres (lat); bay 1 is the landmark F (the tutorial's firing position)

# ------------------------------------------------------------------ kit: authored pieces (Blender reads these dims)
# size = footprint/height (x width, y height, z depth) in the prefab's local frame (front +Z); collider = box colliders on
KIT = {
    "TR_BayDivider": {"size": [0.14, 1.72, 0.9], "collider": True, "note": "timber frame + plywood screen between bays, posts at z -0.6/+0.6"},
    "TR_ShootingBench": {"size": [1.3, 1.16, 0.56], "collider": True, "note": "timber bench, top 0.95, sandbag rest, charge-cell case"},
    "TR_LaneBoard": {"size": [0.32, 1.13, 0.1], "collider": True, "note": "number board 1-4 (UV-selected), hangs on a divider post"},
    "TR_LaneGate": {"size": [3.7, 2.35, 0.3], "collider": True, "note": "machine lane start frame: two posts, cross beam, MACHINE LANE 4 board"},
    "TR_CoverBarricade": {"size": [1.7, 1.3, 0.6], "collider": True, "note": "timber plank cover wall on posts with a sandbag foot and rear braces"},
    "TR_TetherGantry": {"size": [3.0, 3.5, 0.5], "collider": True, "note": "steel gantry, cable trolley; the drone hangs at y 1.95"},
    "TR_DroidFrame": {"size": [1.98, 2.45, 1.8], "collider": True, "note": "goal-post frame: base plate, two uprights, beam, chains to a worker droid shell"},
    "TR_DroneDock": {"size": [1.0, 0.9, 1.0], "collider": True, "note": "steel stand, landing plate with cyan charge ring, status box"},
    "TR_RepairBench": {"size": [2.1, 1.75, 0.9], "top": 0.9, "collider": True, "note": "heavy timber bench on a steel frame, shelf, tool board"},
    "TR_RangeTable": {"size": [1.6, 0.8, 0.72], "collider": True, "note": "range officer's trestle table"},
    "TR_RulesBoard": {"size": [1.5, 2.2, 0.25], "collider": True, "note": "RANGE ORDERS board on two timber posts with a drip cap"},
    "TR_FloodPole": {"size": [0.9, 5.6, 0.5], "collider": True, "note": "timber pole, cross arm, two flood lamps (LIGHT_ empties), junction box"},
    "TR_BlastWall": {"size": [5.2, 1.25, 0.7], "collider": True, "note": "timber crib wall filled with sand, sandbag cap"},
    "TR_ServiceShelter": {"size": [4.4, 2.75, 3.6], "collider": True, "note": "four steel poles, cloth-simulated shade cloth"},
    "TR_TimberStack": {"size": [2.5, 0.55, 0.8], "collider": True, "note": "spare sleepers stacked on bearers"},
    "TR_SpentCells": {"size": [1.4, 0.03, 1.0], "collider": False, "note": "spent nano cells and a few brass cases on the ground"},
    "TR_RangeLamp": {"size": [0.3, 0.3, 0.3], "collider": False, "note": "red range-live beacon lamp (clamps to a flag pole)"},
    "TR_Lantern": {"size": [0.15, 0.33, 0.15], "collider": False, "note": "field lantern"},
    "TR_DistanceMarker": {"size": [0.4, 1.15, 0.12], "collider": True, "note": "distance post with a 5/10/15/20 M plate (UV-selected)"},
}
for k, v in KIT.items():
    v["prefab"] = f"Assets/AthenHill/Prefabs/TrainingRange/{k}.prefab"

# reused kit prefabs and their footprints (street dressing, West Gate, this pass's Poly Haven props)
SD = {}
for f in ("ph-props.json", "meshy-props.json", "authored-props.json"):
    for k, v in json.loads((ASSETS / "Art/StreetDressing/Props" / f).read_text()).items():
        SD["sd:" + k] = {"size": v["size"], "prefab": f"Assets/AthenHill/Prefabs/StreetDressing/SD_{k}.prefab", "collider": True}
WG = {}
for name, sub in [("WG_RangeFlag", "Structures"), ("WG_SandbagPile", "Structures"), ("PH_Clipboard", "Props"), ("PH_RadioSet", "Props"),
                  ("PH_Binoculars", "Props"), ("PH_AmmoBox", "Props"), ("PH_PowerBox", "Props"), ("PH_MilitaryCrateA", "Props"), ("PH_MilitaryCrateB", "Props")]:
    mn, mx = bounds(ASSETS / f"Art/WestGate/{sub}/{name}.glb", lambda n: not n.startswith("COL_") and "_LOD1" not in n and "_LOD2" not in n)
    WG["wg:" + name] = {"size": [round(mx[i] - mn[i], 3) for i in range(3)], "prefab": f"Assets/AthenHill/Prefabs/WestGate/{name}.prefab", "collider": True}
WG["wg:WG_RangeFlag"]["size"] = [0.5, 4.7, 0.5]        # the flag cloth overhangs; the footing is what stands on the ground
TRP = {   # this pass's Poly Haven props (prepare_ph_props.py); sizes from the source dimensions (mm)
    "trp:bench_vice": [0.2, 0.27, 0.4], "trp:megaphone": [0.3, 0.23, 0.37], "trp:multimeter": [0.22, 0.2, 0.28],
    "trp:compressor": [0.6, 1.18, 1.68], "trp:welding_cart": [0.84, 1.56, 0.65], "trp:work_lamp": [1.16, 0.75, 0.31],
    "trp:spade": [0.17, 1.1, 0.05], "trp:sledgehammer": [0.21, 1.0, 0.09],
}
TRP = {k: {"size": v, "prefab": f"Assets/AthenHill/Prefabs/TrainingRange/TRP_{k[4:]}.prefab", "collider": k in ("trp:compressor", "trp:welding_cart")} for k, v in TRP.items()}
ROBOT = {"robot:drone": {"size": [1.0, 0.5, 1.0], "prefab": "Assets/AthenHill/Prefabs/TrainingRange/TR_TrainingDrone.prefab", "collider": False},
         "robot:worker": {"size": [1.0, 2.0, 0.7], "prefab": "Assets/AthenHill/Prefabs/TrainingRange/TR_WorkerDroidShell.prefab", "collider": True}}
CATALOG = {**{"tr:" + k: v for k, v in KIT.items()}, **SD, **WG, **TRP, **ROBOT}

# ------------------------------------------------------------------ placements
PL = []


def corners(x, z, yaw, size, pad=0.0):
    a = math.radians(yaw); sx, sz = size[0] / 2 + pad, size[2] / 2 + pad
    out = []
    for u, v in ((-sx, -sz), (sx, -sz), (sx, sz), (-sx, sz)):
        out.append((x + u * math.cos(a) + v * math.sin(a), z - u * math.sin(a) + v * math.cos(a)))
    return out


def P(group, prop, fwd, lat, yaw_rel=0.0, y="ground-min", on=None, pitch=0.0, roll=0.0, dy=0.0, collider=None, name=None, note="", world=None, extra=None):
    """Place a catalogue prop at frame (fwd, lat) or world (x, z); y: 'ground' (at origin), 'ground-min'/'ground-max' over the
    footprint, a float, or on top of placement `on`. Uniform scale only (1)."""
    if prop not in CATALOG:
        raise SystemExit("unknown prop " + prop)
    x, z = world if world else W(fwd, lat)
    yaw = YAW + yaw_rel
    size = CATALOG[prop]["size"]
    if on is not None:
        b = PL[on]
        yy = b["pos"][1] + CATALOG[b["prop"]].get("top", CATALOG[b["prop"]]["size"][1]) - 0.004
    elif isinstance(y, (int, float)):
        yy = float(y)
    else:
        hs = [ground(px, pz) for px, pz in corners(x, z, yaw, size)] + [ground(x, z)]
        yy = ground(x, z) if y == "ground" else (min(hs) - 0.02 if y == "ground-min" else max(hs))
    yy += dy
    PL.append({"group": group, "prop": prop, "prefab": CATALOG[prop]["prefab"], "name": name or prop.split(":")[1],
               "ymode": ("on" if on is not None else (y if isinstance(y, str) else "fixed")), "dy": dy, "size": CATALOG[prop]["size"],
               "pos": [round(x, 3), round(yy, 3), round(z, 3)], "euler": [pitch, round(yaw, 2), roll], "scale": 1.0,
               "collider": CATALOG[prop]["collider"] if collider is None else collider, "on": on, "note": note, "extra": extra or {}})
    return len(PL) - 1


# ---- firing point: three bays at the tutorial firing line ---------------------------------------------------------
g = "Firing point"
for k, lat in enumerate([0.8, 2.4]):
    P(g, "tr:TR_BayDivider", 0.1, lat, name=f"Bay divider {k + 1}")
for n, lat in BAYS.items():
    b = P(g, "tr:TR_ShootingBench", 1.2, lat, j(1.5), name=f"Bay {n} bench")
    # lane board on the rear post of the bay's left divider, facing up range (the firer and anyone walking up)
    P(g, "tr:TR_LaneBoard", -0.45, lat + 0.62, 180, y="ground-min", name=f"Lane board {n}", extra={"number": n})
    P(g, "tr:TR_SpentCells", 0.1 + j(.1), lat + j(.15), rng.uniform(0, 360), y="ground", name=f"Spent cells bay {n}", extra={"variant": n})
# the range officer's table beside the line (right end, flat ground), stool and stores
g = "Range officer"
t = P(g, "tr:TR_RangeTable", 2.35, 5.45, j(2), name="Range officer's table")
P(g, "wg:PH_Clipboard", 2.25, 5.05, 10, on=t, name="Range log", collider=False)
P(g, "wg:PH_RadioSet", 2.45, 6.0, -15, on=t, name="Range radio", collider=False)
P(g, "trp:megaphone", 2.4, 5.45, 40, on=t, name="Megaphone", collider=False)
P(g, "wg:PH_Binoculars", 2.2, 4.8, -30, on=t, name="Binoculars", collider=False)
P(g, "tr:TR_Lantern", 2.5, 5.85, 0, on=t, name="Range officer's lantern")
# 3 Oct (Carl: "too many props in the way ... make sure it's easy to walk to the tables"): stool, crates and can moved to
# the table's down-range side so its up-range side is open from the line
P(g, "sd:stool_folding", 3.1, 5.3, 190, name="Range officer's stool")
c = P(g, "sd:ammo_crate_a", 2.4, 7.15, 88 + j(2), name="Nano cell crate")
P(g, "sd:ammo_crate_b", 2.37, 7.18, 92 + j(2), on=c, name="Nano cell crate (open)")
P(g, "sd:jerrycan_green", 3.15, 4.6, 20, name="Water can")
# distance posts down the left edge of the range (outside every line of fire), plates facing the firing line
for k, fw in enumerate((5.0, 10.0, 15.0)):
    P("Distance posts", "tr:TR_DistanceMarker", fw, -4.6 - 0.1 * k, 180 + j(3), name=f"Distance post {int(fw)} m", extra={"number": k + 1})
# spent-cell bin at the left end of the line (range order 6), recruits' waiting bench behind the bays
P("Firing point", "sd:bin_galv_rust", -1.0, 6.6, 90 + j(4), name="Spent cell bin")   # 3 Oct: out of the walk behind the line
P("Firing point", "sd:bench_painted", -3.3, 3.2, 0, name="Waiting bench")
P("Firing point", "sd:jerrycan_green", -3.3, 4.15, 20, name="Water can (waiting bench)")
# range orders board facing the approach from the gate, behind the line on the left
P("Range orders", "tr:TR_RulesBoard", -2.4, 5.6, 0, y="ground-min", name="Range orders board", note="faces the path from the gate")   # 3 Oct: off the approach
PL[-1]["euler"][1] = 160.0
# red flag + range-live lamp at the right end of the firing point, second flag on the backstop crest (placed with the berm)
fl = P("Range flags", "wg:WG_RangeFlag", -0.3, 6.9, 90, y="ground-min", name="Range flag (firing point)")
P("Range flags", "tr:TR_RangeLamp", -0.3, 6.9, 0, y=PL[fl]["pos"][1] + 3.55, name="Range live lamp (firing point)")
# flood pole behind bay 1's left end, lighting the plates and the bay floor
P("Night lighting", "tr:TR_FloodPole", 1.5, -3.6, 0, name="Range flood pole")   # 3 Oct: out of the approach

# ---- lane 4: the machine lane -----------------------------------------------------------------------------------
g = "Machine lane"
P(g, "tr:TR_LaneGate", 3.0, 8.7, 0, name="Machine lane start frame", extra={"number": 4})
for i in range(4):
    for row, lat in enumerate((8.4, 8.98)):
        yr = rng.uniform(-20, 20)
        cf, cl = 4.0 + i * 0.6 + (0.3 if row else 0) + j(.03), lat + j(.03)
        # pivot = centre - 0.3 m along the tyre's yaw (frame: yaw_rel 0 = down range = +fwd)
        a = math.radians(yr)
        P(g, "sd:tyre", cf - 0.3 * math.cos(a), cl - 0.3 * math.sin(a), yr, y="ground-max", pitch=90, dy=0.083,
          collider=False, name="Drill tyre")
P(g, "tr:TR_CoverBarricade", 7.4, 7.75, j(4), name="Cover barricade A")
P(g, "tr:TR_CoverBarricade", 10.1, 9.7, j(4), name="Cover barricade B")
P(g, "tr:TR_TetherGantry", 12.7, 8.8, 0, name="Drone tether gantry")
gt = PL[-1]
P(g, "robot:drone", 12.7, 8.8, 180 + 25, y=gt["pos"][1] + 1.62, name="Training drone (tethered)", extra={"tethered": True})
PL[-1].update(ymode="rel", relTo=len(PL) - 2, dy=1.68)
fr = P(g, "tr:TR_DroidFrame", 16.4, 8.7, 180, name="Worker droid target frame")
P(g, "robot:worker", 16.4, 8.7, 180, y=PL[fr]["pos"][1] + 0.05, name="Worker droid shell (target)", extra={"painted": True})
PL[-1].update(ymode="rel", relTo=fr, dy=0.05)
P(g, "sd:sack_tied_b", 15.1, 7.3, 30, name="Sand sack")
# blast wall between lane 4 and the service apron
P("Service apron", "tr:TR_BlastWall", 10.4, 11.05, 90, name="Blast wall")

# ---- the robot service apron --------------------------------------------------------------------------------------
g = "Service apron"
APRON = {"fwd": [8.9, 14.1], "lat": [11.7, 15.7]}
P(g, "tr:TR_ServiceShelter", 11.5, 13.9, 90, y="ground-min", name="Service shelter")
for k, (fw, la, has) in enumerate([(9.9, 15.0, True), (11.15, 15.0, True), (12.4, 15.0, False)]):
    d = P(g, "tr:TR_DroneDock", fw, la, -90, name=f"Drone dock {k + 1}")
    if has:
        P(g, "robot:drone", fw, la, -90 + j(10), y=PL[d]["pos"][1] + 0.87, name=f"Training drone (docked {k + 1})")
        PL[-1].update(ymode="rel", relTo=d, dy=0.87)
rb = P(g, "tr:TR_RepairBench", 9.8, 12.55, 90, name="Repair bench")
P(g, "trp:bench_vice", 9.05, 12.75, 90, on=rb, name="Bench vice", collider=False)
P(g, "trp:multimeter", 10.1, 12.6, 110, on=rb, name="Multimeter", collider=False)
P(g, "sd:toolbox", 10.6, 12.5, 85, on=rb, name="Toolbox", collider=False)
P(g, "sd:rag", 9.6, 12.8, 30, on=rb, name="Rag", collider=False)
P(g, "trp:welding_cart", 8.6, 14.6, 180 + 20, name="Welding cart")
P(g, "trp:compressor", 13.6, 12.8, 0, name="Compressor")
P(g, "sd:field_generator", 13.95, 14.75, 90, name="Dock generator")
P(g, "sd:jerrycan_red", 14.45, 13.75, 10, name="Fuel can")
P(g, "sd:tool_cart", 11.65, 12.5, 90, name="Tool trolley")
P(g, "trp:work_lamp", 11.5, 13.9, 0, y="ground", dy=1.86, collider=False, name="Shelter work lamp")

# ---- the backstop -------------------------------------------------------------------------------------------------
# revetment toe path (fwd, lat): in front of the natural mound behind plates 1-2, built out across plate 3 and lane 4
# 1 Oct: toe kept on the range floor (ground about -1.1), in front of the natural mound behind plates 1-2 (the 30 Sep
# line climbed 0.9 m up the mound, so the wall top stepped); the earth bank (Unity) buries the mound behind the wall
REVET = [(17.0, -8.0), (16.4, -6.0), (16.3, -4.0), (16.9, -2.0), (17.6, 0.0), (18.25, 1.6), (18.8, 3.2), (19.35, 6.0), (19.6, 9.0), (19.4, 11.4), (19.0, 13.2)]
BERM = {"toe": REVET, "wallHeight": 1.92, "crestRise": 3.15, "crestFrom": 2.4, "crestTo": 3.6, "backTo": 8.8,
        "taperLat": [-10.5, -7.0, 13.2, 16.2], "noise": 0.12, "step": 0.33}
g = "Backstop"
fl2 = P("Range flags", "wg:WG_RangeFlag", 19.5, -3.6, 90, y="ground", dy=3.1, name="Range flag (backstop crest)", note="y set on the berm crest in Unity")
PL[fl2]["ymode"] = "berm"
P(g, "tr:TR_TimberStack", 14.9, -6.4, 8, name="Spare sleepers")
P(g, "trp:spade", 15.95, -4.95, 0, y="ground", pitch=-14, name="Spade (against the wall)", collider=False)
P(g, "sd:handcart", 14.0, -7.4, 15, name="Sand cart")
P(g, "trp:sledgehammer", 17.5, 11.9, 0, y="ground", pitch=-16, collider=False, name="Sledgehammer")
P(g, "sd:sack_tied_a", 17.2, 12.6, 40, name="Sand sack")
P(g, "sd:sack_tied_c", 17.35, 13.2, -20, name="Sand sack")

# ------------------------------------------------------------------ what is retired (inactive, never deleted)
RETIRE = ["Outer Berms/West Gate outpost/Outpost/Firing bench", "Outer Berms/West Gate outpost/Outpost/Firing point sandbags (front)",
          "Outer Berms/West Gate outpost/Outpost/Firing point sandbags (side)", "Outer Berms/West Gate outpost/Outpost/Sandbag pile (range)",
          "Outer Berms/West Gate outpost/Outpost/Range flag"]
RETIRE_TEXT = [f"Outer Berms/Warden range/Range plate {n}/Target number" for n in PLATES]     # floating unlit TextMesh numbers
# loose scatter, shrubs and a boulder on the cleared bay floor and under the new pieces (frame polygon)
BAY_POLY = [(1.0, -6.5), (1.0, 4.4), (2.6, 6.6), (2.6, 16.2), (22.0, 16.5), (22.0, -9.5), (14.0, -9.5)]


def in_poly(pt, poly):
    x, y = pt; ins = False
    for i in range(len(poly)):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % len(poly)]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1:
            ins = not ins
    return ins


def _seg_dist(p, a, b):
    ax, ay = a; bx, by = b; px, py = p
    t = max(0.0, min(1.0, ((px - ax) * (bx - ax) + (py - ay) * (by - ay)) / ((bx - ax) ** 2 + (by - ay) ** 2)))
    return math.hypot(px - ax - t * (bx - ax), py - ay - t * (by - ay))


# Same-named siblings (e.g. 20 objects called "scatter rocka") cannot be told apart by path, so each retired object is
# recorded as parent path + name + footprint centre; Unity retires the sibling whose renderers centre within 0.4 m.
retire_scatter = {}
for r in S["renderers"]:
    p = r["path"]
    if not (r["active"] and r["enabled"]):
        continue
    parts = p.split("/")
    if len(parts) < 4:
        continue
    if not (p.startswith("Outer Berms/West Gate outpost/Scatter/") or p.startswith("Outer Berms/West Gate outpost/Terrain dressing/")
            or p.startswith("Outer Berms/Warden post/West Gate checkpoint/Checkpoint foliage/")):
        continue
    if "_LOD0" not in p and "LOD" in p:
        continue
    cx, cz = (r["min"][0] + r["max"][0]) / 2, (r["min"][2] + r["max"][2]) / 2
    fw, la = L(cx, cz)
    if in_poly((fw, la), BAY_POLY) or (-1.2 < fw < 1.2 and -1.5 < la < 7.5):
        # loose small stones stay where nothing is built and no shot passes (a raked range, not a bulldozed one)
        if "stones" in parts[3]:
            near_fire = any(_seg_dist((fw, la), (0.0, 0.0), L(*PLATES[n])) < 1.6 for n in PLATES)
            in_yard = 2.0 < fw < 18.5 and 6.3 < la < 17.0
            if not (near_fire or in_yard or fw < 1.5):
                continue
        key = ("/".join(parts[:3]), parts[3], round(cx, 2), round(cz, 2))
        retire_scatter[key] = {"parent": key[0], "name": key[1], "centre": [key[2], key[3]], "frame": [round(fw, 2), round(la, 2)]}
RETIRE_SCATTER = sorted(retire_scatter.values(), key=lambda q: (q["parent"], q["name"], q["centre"]))

# ------------------------------------------------------------------ decals (URP decal projectors; textures by make_textures.py)
DECALS = []


def D(kind, fwd, lat, w, l, yaw_rel=0.0, opacity=0.8, world=None, proj="down", depth=0.6, y=None):
    x, z = world if world else W(fwd, lat)
    DECALS.append({"kind": kind, "pos": [round(x, 3), round(ground(x, z) if y is None else y, 3), round(z, 3)], "size": [w, l, depth],
                   "yaw": round(YAW + yaw_rel, 2), "opacity": opacity, "proj": proj})


# decal frame: size[0] runs 90 deg clockwise of the yaw (the painted-line texture runs along it), size[1] along the yaw
D("TR_DecalFiringLine", 1.68, 1.6, 5.4, 0.22, 0, 0.85)                                # painted line across the three bays
for n, lat in BAYS.items():
    D("TR_DecalTrodden", 0.0, lat, 1.5, 1.4, j(10), 0.55)                             # scuffed standing spots
for n, (x, z) in PLATES.items():                                                    # paint overspray round each plate foot
    D("TR_DecalOverspray", 0, 0, 1.9, 1.9, rng.uniform(0, 360), 0.8, world=(x, z))
    fw, la = L(x, z)
    D("TR_DecalTrodden", fw - 1.3, la, 1.2, 2.2, 0, 0.45)                            # path worn walking forward to repaint
D("TR_DecalLaneLine", 5.6, 6.8, 5.0, 0.12, 90, 0.75)                                 # machine lane boundaries (worn paint)
D("TR_DecalLaneLine", 5.6, 10.6, 5.0, 0.12, 90, 0.7)
D("WG_DecalTyreTracks", 8.6, -6.5, 0.9, 9.0, 0, 0.45)                                # sand cart run up the left side to the backstop
D("WG_DecalSandSpill", 14.4, -7.0, 1.6, 1.4, 25, 0.6)                                # spilled fill where the cart is loaded
D("TR_DecalTrodden", 5.0, 8.5, 2.2, 3.2, 0, 0.5)
D("TR_DecalOil", 12.2, 13.8, 2.4, 2.0, 30, 0.65)                                     # service apron stains
D("TR_DecalOil", 16.4, 8.7, 1.6, 1.5, 80, 0.5)
# impact scars on the revetment face behind each target (projected horizontally onto the wall, facing up range)
SCARS = []           # (lane number, lat where the line from the firing position F through plate n meets the wall)
for n, (x, z) in PLATES.items():
    fw, la = L(x, z)
    lat = la
    for _ in range(6):
        toe_f = float(np.interp(lat, [q[1] for q in REVET], [q[0] for q in REVET]))
        lat = la * toe_f / fw
    SCARS.append((n, round(lat, 3)))
SCARS.append((4, 10.4))

# ------------------------------------------------------------------ lights (Ward light clock: practical + night only)
LIGHTS = []
fp = [p for p in PL if p["name"] == "Range flood pole"][0]
LIGHTS.append({"name": "Range flood (plates)", "type": "Spot", "pos": [fp["pos"][0], fp["pos"][1] + 5.25, fp["pos"][2]],
               "target": [PLATES[2][0] + 1.5, ground(*PLATES[2]) + 0.6, PLATES[2][1] - 1.5], "color": [0.95, 0.93, 0.86],
               "intensity": 70.0, "range": 34.0, "angle": 56.0, "shadows": False})
tx, tz = W(12.0, 8.8)
LIGHTS.append({"name": "Range flood (machine lane)", "type": "Spot", "pos": [fp["pos"][0], fp["pos"][1] + 5.25, fp["pos"][2]],
               "target": [tx, ground(tx, tz) + 0.5, tz], "color": [0.95, 0.93, 0.86], "intensity": 45.0, "range": 28.0, "angle": 42.0, "shadows": False})
lamp = [p for p in PL if p["name"] == "Shelter work lamp"][0]
LIGHTS.append({"name": "Service shelter work lamp", "type": "Spot", "pos": [lamp["pos"][0], lamp["pos"][1] + 0.05, lamp["pos"][2]],
               "target": [lamp["pos"][0], lamp["pos"][1] - 2.5, lamp["pos"][2]], "color": [1.0, 0.84, 0.64], "intensity": 7.0, "range": 8.0,
               "angle": 120.0, "shadows": False})
rl = [p for p in PL if p["name"] == "Range live lamp (firing point)"][0]
LIGHTS.append({"name": "Range live lamp", "type": "Point", "pos": [rl["pos"][0], rl["pos"][1] + 0.12, rl["pos"][2]], "target": None,
               "color": [1.0, 0.16, 0.08], "intensity": 1.6, "range": 4.0, "angle": 0, "shadows": False})
tb = [p for p in PL if p["name"] == "Range officer's table"][0]
ln = [p for p in PL if p["name"] == "Range officer's lantern"][0]
LIGHTS.append({"name": "Range officer's lamp", "type": "Point", "pos": [ln["pos"][0], ln["pos"][1] + 0.16, ln["pos"][2]], "target": None,
               "color": [1.0, 0.82, 0.6], "intensity": 1.4, "range": 3.5, "angle": 0, "shadows": False})

# ------------------------------------------------------------------ review cameras (player height; lookbook names)
CAMS = []


def CAM(name, fwd, lat, look_fwd, look_lat, h=1.62, look_h=0.9, fov=60, world=None, look_world=None):
    x, z = world if world else W(fwd, lat)
    tx, tz = look_world if look_world else W(look_fwd, look_lat)
    CAMS.append({"name": name, "pos": [round(x, 3), round(ground(x, z) + h, 3), round(z, 3)], "target": [round(tx, 3), round(ground(tx, tz) + look_h, 3), round(tz, 3)], "fov": fov})


CAM("cam_range_line", -2.4, 1.4, 16.0, 1.0, look_h=0.8)                  # behind the firing point, looking down range
CAM("cam_range_bays", 3.4, -3.6, 0.2, 2.0, look_h=0.75)                  # the bays from in front-left
CAM("cam_range_backstop", 11.0, 0.8, 18.8, 0.4, look_h=1.2)              # walking up to the plates: backstop, plate 2
CAM("cam_range_plates", 9.5, -4.2, 16.5, 2.5, look_h=0.9, fov=62)        # plates 1-3 against the backstop
CAM("cam_range_machine_lane", 2.2, 7.4, 16.0, 8.8, look_h=1.2)           # machine lane from its start frame
CAM("cam_range_droid", 13.4, 7.3, 16.5, 8.7, look_h=1.3, fov=55)         # the droid target and the tethered drone
CAM("cam_range_apron", 8.0, 16.5, 11.6, 13.4, look_h=0.9)                # robot service apron under its shelter
CAM("cam_range_overview", 0, 0, 0, 0, world=(-58.5, 17.5), look_world=(-73.5, 15.0), h=5.5, look_h=0.0, fov=62)
CAMS[-1]["pos"][1] = 4.6                                                  # from the wall-walk height over the gate's north side
# after-only close-ups (nothing stood here before): the machine lane from behind its start frame, a firing bay from down range
CAM("cam_range_lane_start", 1.3, 8.2, 16.0, 8.6, look_h=1.0)   # clear of the searsia shrub at (0.7, 10.1)
CAM("cam_range_bench", 3.0, 2.9, 1.0, 1.4, h=1.45, look_h=0.8, fov=55)

# ------------------------------------------------------------------ validation (oriented boxes)
class OBB:
    def __init__(self, cx, cz, hx, hz, yaw, y0, y1, name=""):
        self.c = (cx, cz); self.h = (hx, hz); self.y0, self.y1 = y0, y1; self.name = name
        a = math.radians(yaw)
        self.ax = (math.cos(a), -math.sin(a)); self.az = (math.sin(a), math.cos(a))

    def local(self, x, z):
        dx, dz = x - self.c[0], z - self.c[1]
        return dx * self.ax[0] + dz * self.ax[1], dx * self.az[0] + dz * self.az[1]

    def corners(self):
        return [(self.c[0] + u * self.h[0] * self.ax[0] + v * self.h[1] * self.az[0], self.c[1] + u * self.h[0] * self.ax[1] + v * self.h[1] * self.az[1])
                for u, v in ((-1, -1), (1, -1), (1, 1), (-1, 1))]

    def overlaps(self, o, pad=0.0):
        if self.y1 <= o.y0 + 0.02 or o.y1 <= self.y0 + 0.02:
            return False
        for axis in (self.ax, self.az, o.ax, o.az):
            p1 = [q[0] * axis[0] + q[1] * axis[1] for q in self.corners()]
            p2 = [q[0] * axis[0] + q[1] * axis[1] for q in o.corners()]
            if max(p1) + pad < min(p2) or max(p2) + pad < min(p1):
                return False
        return True

    def seg(self, p, q, pad=0.0):
        """3D segment (x, y, z) vs this box."""
        lp = self.local(p[0], p[2]); lq = self.local(q[0], q[2])
        P = (lp[0], p[1], lp[1]); Q = (lq[0], q[1], lq[1])
        box = (-self.h[0] - pad, self.h[0] + pad, self.y0 - pad, self.y1 + pad, -self.h[1] - pad, self.h[1] + pad)
        t0, t1 = 0.0, 1.0
        for a in range(3):
            d = Q[a] - P[a]; lo, hi = box[2 * a], box[2 * a + 1]
            if abs(d) < 1e-9:
                if P[a] < lo or P[a] > hi:
                    return False
            else:
                ta, tb = (lo - P[a]) / d, (hi - P[a]) / d
                t0, t1 = max(t0, min(ta, tb)), min(t1, max(ta, tb))
                if t0 > t1:
                    return False
        return True

    def dist(self, x, z):
        u, v = self.local(x, z)
        du = max(abs(u) - self.h[0], 0); dv = max(abs(v) - self.h[1], 0)
        return math.hypot(du, dv)


COLS = []
retired_prefixes = RETIRE
for c in S["colliders"]:
    if c["path"].startswith("Outer Berms/Warden training range/"):
        continue   # 3 Oct: a survey taken after install sees the range's own props; they are what this layout places
    if c["trigger"] or any(c["path"].startswith(p) for p in retired_prefixes):
        continue
    ccx, ccz = (c["min"][0] + c["max"][0]) / 2, (c["min"][2] + c["max"][2]) / 2
    if any(c["path"].startswith(q["parent"] + "/" + q["name"]) and abs(ccx - q["centre"][0]) < 1.0 and abs(ccz - q["centre"][1]) < 1.0 for q in RETIRE_SCATTER):
        continue
    if c["path"].startswith("Outer Berms/Warden range/"):
        continue           # plates are checked separately (fall zones)
    (x0, y0, z0), (x1, y1, z1) = c["min"], c["max"]
    if x1 - x0 > 30 or z1 - z0 > 30:
        continue
    o = c.get("obb")
    if o and abs(o["pitch"]) < 1 and abs(o["roll"]) < 1:
        COLS.append(OBB(o["center"][0], o["center"][2], o["size"][0] / 2, o["size"][2] / 2, o["yaw"], y0, y1, c["path"]))
    else:
        COLS.append(OBB((x0 + x1) / 2, (z0 + z1) / 2, (x1 - x0) / 2, (z1 - z0) / 2, 0, y0, y1, c["path"]))
POINTS = []
for m in S["markers"]:
    if m["kind"] in ("landmark", "npc", "interactable", "spawn"):
        rad = {"landmark": 0.5, "npc": 1.0, "interactable": 0.6, "spawn": 3.0}[m["kind"]]
        POINTS.append((m["path"].split("/")[-1], m["pos"][0], m["pos"][2], rad))


def item_obb(p):
    size = CATALOG[p["prop"]]["size"]
    y0 = p["pos"][1]
    if p["euler"][0] == 90:        # laid flat (tyres): height is the prop's depth
        return OBB(p["pos"][0], p["pos"][2], size[0] / 2, size[1] / 2, p["euler"][1], y0 - size[1] / 2, y0 + size[2], p["name"])
    return OBB(p["pos"][0], p["pos"][2], size[0] / 2, size[2] / 2, p["euler"][1], y0, y0 + size[1], p["name"])


problems = []
shooters = [("cam F", W(-0.22, 0.0), 1.76)] + [(f"bay {n}", W(0.0, lat), EYE) for n, lat in BAYS.items()] + \
           [(f"bay {n} step left", W(0.0, lat - 0.45), EYE) for n, lat in BAYS.items()] + [(f"bay {n} step right", W(0.0, lat + 0.45), EYE) for n, lat in BAYS.items()]
OB = [item_obb(p) for p in PL]
for i, p in enumerate(PL):
    x, y, z = p["pos"]; size = CATALOG[p["prop"]]["size"]
    bx = OB[i]
    fw, la = L(x, z)
    if p["collider"]:
        for c in COLS:
            if bx.overlaps(c):
                problems.append((i, "collider " + c.name))
        for sname, (sx, sz), eye in shooters:
            for n, (px, pz) in PLATES.items():
                a = (sx, ground(sx, sz) + eye, sz); b = (px, ground(px, pz) + PLATE_AIM_H, pz)
                if bx.seg(a, b, 0.05):
                    problems.append((i, f"line of fire {sname} -> plate {n}"))
        for (name, px, pz, rad) in POINTS:
            if bx.dist(px, pz) < rad:
                problems.append((i, f"keep-clear {name} ({bx.dist(px, pz):.2f} m)"))
    for n, (px, pz) in PLATES.items():
        pf, pl_ = L(px, pz)
        if -0.9 < fw - pf < 1.6 and abs(la - pl_) < 0.9:
            problems.append((i, f"plate {n} fall zone"))
    for k, q in enumerate(PL):
        if k >= i or q["on"] == i or p["on"] == k or (p["on"] is not None and p["on"] == q["on"]) or not (p["collider"] and q["collider"]):
            continue
        if {p["prop"], q["prop"]} == {"robot:worker", "tr:TR_DroidFrame"} or "tr:TR_ServiceShelter" in (p["prop"], q["prop"]):
            continue       # the shell stands in its frame; the shelter's poles stand at its corners
        if bx.overlaps(OB[k], -0.02):
            problems.append((i, f"overlaps #{k} {q['name']}"))
# the revetment must stand well behind each plate (its fall and the misses)
for n, (px, pz) in PLATES.items():
    pf, pl_ = L(px, pz)
    toe_f = np.interp(pl_, [q[1] for q in REVET], [q[0] for q in REVET])
    if toe_f - pf < 1.2:
        problems.append((-1, f"revetment only {toe_f - pf:.2f} m behind plate {n}"))
# nothing stands inside the revetment line (the wall and the earth bank behind it)
for i, p in enumerate(PL):
    if p["group"] == "Range flags" and "crest" in p["name"]:
        continue
    for cx, cz in OB[i].corners():
        fw, la = L(cx, cz)
        if fw > float(np.interp(la, [q[1] for q in REVET], [q[0] for q in REVET])) - 0.04 and REVET[0][1] - 1 < la < REVET[-1][1] + 1:
            problems.append((i, "inside the revetment / berm")); break
# walking route: gate apron -> just behind the firing line stays open (0.45 m either side of the line)
route = [(-60.5, 2.0), (-63.5, 5.0), W(-0.7, 0.0)]
for i, p in enumerate(PL):
    if not p["collider"]:
        continue
    for (a, b) in zip(route, route[1:]):
        if any(OB[i].dist(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t) < 0.45 for t in np.linspace(0, 1, 40)):
            problems.append((i, "blocks the gate-to-firing-line walk"))
            break
# 3 Oct: and along behind the line to every bay and up to the range officer's table (0.45 m clearance)
for route in ([W(-1.1, 0.0), W(-1.1, 1.6), W(-1.1, 3.2), W(-1.1, 5.0), W(1.3, 5.45)],):
    for i, p in enumerate(PL):
        if not p["collider"] or p["prop"] == "tr:TR_RangeTable":
            continue
        for (a, b) in zip(route, route[1:]):
            if any(OB[i].dist(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t) < 0.45 for t in np.linspace(0, 1, 40)):
                problems.append((i, "blocks the walk behind the line / to the officer's table"))
                break

for i, why in problems:
    name = PL[i]["name"] if i >= 0 else "backstop"
    print(f"#{i:3d} {name:38s} {why}")
print(f"{len(PL)} placements, {len(RETIRE_SCATTER)} scatter objects retired, {len(DECALS)} decals, {len(LIGHTS)} lights, "
      f"{len(CAMS)} cameras, {len(problems)} problems")

# ------------------------------------------------------------------ revetment + cables for Blender (world points + ground)
# wall base level along the toe: ground sampled every 0.25 m, smoothed over about 3 m, so the wall top runs level
# bay to bay instead of stepping with every bump (posts are still buried to the local ground in Blender)
def _toe_base():
    pts = [np.array(W(*q)) for q in REVET]
    seg = [np.linalg.norm(b - a) for a, b in zip(pts, pts[1:])]
    s_pts = np.concatenate([[0], np.cumsum(seg)])
    ss = np.arange(0, s_pts[-1] + 1e-6, 0.25)
    xs = np.interp(ss, s_pts, [p[0] for p in pts]); zs = np.interp(ss, s_pts, [p[1] for p in pts])
    g = np.array([min(ground(x + dx, z + dz) for dx, dz in ((0, 0), (.25, 0), (-.25, 0), (0, .25), (0, -.25))) for x, z in zip(xs, zs)])
    k = 12
    gs = np.array([g[max(0, i - k):i + k + 1].mean() for i in range(len(g))])
    return np.interp(s_pts, ss, gs)


rev_world = []
for (fw, la), gy in zip(REVET, _toe_base()):
    x, z = W(fw, la)
    rev_world.append([round(x, 3), round(float(gy), 3), round(z, 3)])
# earth bank toe for Unity (Editor/TrainingRangePass builds the berm mesh on the real ground): the revetment toe extended
# past both wall ends, where the bank comes down to the ground as a plain earth wing (wall flag 0)
def _ext(p, q, d):
    vx, vz = p[0] - q[0], p[1] - q[1]; n = math.hypot(vx, vz)
    return (p[0] + vx / n * d, p[1] + vz / n * d)


earth = [(_ext(REVET[0], REVET[1], 3.6), 0), (_ext(REVET[0], REVET[1], 1.8), 0)] + [(q, 1) for q in REVET] + \
        [(_ext(REVET[-1], REVET[-2], 1.6), 0), (_ext(REVET[-1], REVET[-2], 3.2), 0)]
EARTH = []
for (fw, la), wall in earth:
    x, z = W(fw, la)
    EARTH.append({"pos": [round(x, 3), round(ground(x, z), 3), round(z, 3)], "wall": wall})
# per-post ground along the toe at 0.05 m resolution for the Blender wall (minimum within the post footprint)
def cable(points):
    out = []
    for fw, la in points:
        x, z = W(fw, la)
        out.append([round(x, 3), round(ground(x, z) + 0.03, 3), round(z, 3)])
    return out


gen = [p for p in PL if p["name"] == "Dock generator"][0]
gf, gl = L(gen["pos"][0], gen["pos"][2])
CABLES = [
    {"name": "Dock feed 1", "pts": cable([(gf - 0.3, gl + 0.2), (12.4, 15.3), (11.55, 15.35), (11.55, 15.25)])},
    {"name": "Dock feed 2", "pts": cable([(gf - 0.2, gl + 0.35), (11.2, 15.45), (10.3, 15.4), (10.3, 15.3)])},
    {"name": "Bench feed", "pts": cable([(gf - 0.5, gl - 0.1), (12.3, 13.1), (10.4, 12.75), (9.9, 12.9)])},
    {"name": "Gantry feed", "pts": cable([(9.3, 11.2), (10.5, 10.4), (12.4, 10.35), (12.7, 10.2)])},
]
out = {"source": "art/training_range_20261001/layout.py", "date": "2026-10-01",
       "frame": {"origin": list(F), "yaw": YAW, "fwd": list(FWD), "right": list(RIGHT)},
       "plates": {str(k): list(v) for k, v in PLATES.items()}, "bays": BAYS, "kit": KIT,
       "placements": [{k: v for k, v in p.items() if k not in ("on",)} | {"stackedOn": p["on"]} for p in PL],
       "retire": RETIRE, "retireText": RETIRE_TEXT, "retireScatter": RETIRE_SCATTER,
       "berm": BERM | {"toeWorld": rev_world, "earthToe": EARTH}, "revetment": {"toe": rev_world, "scarLats": SCARS},
       "apron": APRON, "decals": DECALS, "lights": LIGHTS, "cameras": CAMS, "cables": CABLES,
       "flagOnCrest": fl2, "problems": [f"#{i} {why}" for i, why in problems]}
(HERE / "layout.json").write_text(json.dumps(out, indent=1))

if "--plot" in sys.argv:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as Poly
    from ground import _g, X0, X1, Z0, Z1, ST, NX, NZ
    fig, ax = plt.subplots(figsize=(20, 20), dpi=70)
    ax.imshow(_g, origin="lower", extent=[X0, X1, Z0, Z1], cmap="terrain", vmin=-2, vmax=4, alpha=.6)
    ax.contour(np.linspace(X0, X1, NX), np.linspace(Z0, Z1, NZ), _g, levels=np.arange(-2, 6, .25), colors="k", linewidths=.25)
    for c in COLS:
        ax.add_patch(Poly(c.corners(), fc="#f003", ec="r", lw=.6))
    for p, ob in zip(PL, OB):
        cs = ob.corners()
        ax.add_patch(Poly(cs, fc="#0af5" if p["collider"] else "#fa05", ec="k", lw=.5))
        ax.text(p["pos"][0], p["pos"][2], p["name"][:22], fontsize=5)
    ax.plot([q[0] for q in rev_world], [q[2] for q in rev_world], "-", color="saddlebrown", lw=3)
    for n, (x, z) in PLATES.items():
        ax.plot(x, z, "ks", ms=8)
        for sname, (sx, sz), eye in shooters:
            ax.plot([sx, x], [sz, z], "-", color="#c00", lw=.4)
    for (name, px, pz, rad) in POINTS:
        ax.add_patch(plt.Circle((px, pz), rad, fc="none", ec="g")); ax.text(px, pz, name, fontsize=6, color="g")
    for d in DECALS:
        ax.add_patch(Poly(corners(d["pos"][0], d["pos"][2], d["yaw"], d["size"]), fc="none", ec="purple", lw=.5, ls="--"))
    for c in CAMS:
        ax.annotate("", xy=(c["target"][0], c["target"][2]), xytext=(c["pos"][0], c["pos"][2]), arrowprops=dict(arrowstyle="->", color="navy"))
        ax.text(c["pos"][0], c["pos"][2], c["name"], fontsize=6, color="navy")
    for c in CABLES:
        ax.plot([q[0] for q in c["pts"]], [q[2] for q in c["pts"]], "-", color="k", lw=1)
    poly = [W(*q) for q in BAY_POLY]
    ax.add_patch(Poly(poly, fc="none", ec="orange", lw=1, ls=":"))
    ax.set_xlim(-90, -57); ax.set_ylim(-2, 32); ax.set_aspect("equal"); ax.grid(True, lw=.3)
    fig.savefig(HERE / "review/layout-map.png", bbox_inches="tight")
    print("review/layout-map.png")
