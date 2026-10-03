#!/usr/bin/env python3
"""Ward life pass layout (3 Oct 2026): plain Python. Writes layout.json for Unity (Editor/WardLifePass.cs).

Three spots, each a scene root "Ward life: <spot>":
  West Gate bastions  WL_GateBastionS/N at the round-two roots (same position/yaw), retiring
                      "Ward building: West Gate bastions" (deactivated, kept for rollback).
  Lattice court       the court behind Vanguard Hall where the old Lattice Jack stood becomes the Wardens' water ration
                      point (WL_WaterPoint) with the queue's cans and carts from the street dressing kit, damp and
                      trodden decals.
  Node 07 goods dock  the empty paving east of the Meshy ring in front of Quantum Tube Node 07: inbound/outbound bays
                      with goods canisters, a platform scale, the tally desk and dock board, painted bay marks.

Validation (prints problems, exits 1 if any): every placed footprint (model colliders from the authored json, kit
props from the street dressing sizes) against the saved scene colliders of the survey
(unity/evidence/ward-life/20261003/survey/survey.json), walker/mechanic routes (1 m), NPC/landmark/interaction markers,
the hall loop and Lattice/ring approach corridors from unity/tools, the Node 07 door lane and each other.
Run: python3 layout.py
"""
import json, math, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SURVEY = ROOT / "unity/evidence/ward-life/20261003/survey/survey.json"
PROPS = ROOT / "unity/AthenHill/Assets/AthenHill/Art/StreetDressing/Props"
MODELS = ROOT / "unity/AthenHill/Assets/AthenHill/Art/WardLife/Models"
SD = "Assets/AthenHill/Prefabs/StreetDressing/SD_"
WLP = "Assets/AthenHill/Prefabs/WardLife/"

SIZE = {}
for f in ("ph-props.json", "meshy-props.json", "authored-props.json"):
    for k, v in json.loads((PROPS / f).read_text()).items():
        SIZE[k] = v["size"]

A = json.loads(SURVEY.read_text())

# ------------------------------------------------------------------ models (built by WardLifePass build)
MODEL_KEYS = {
    "bastion_s": ("WL_GateBastionS", 3, [22, 60, 400]),
    "bastion_n": ("WL_GateBastionN", 3, [22, 60, 400]),
    "waterpoint": ("WL_WaterPoint", 2, [26, 90]),
    "canister_pallet": ("WL_CanisterPallet", 2, [14, 55]),
    "canister_stand": ("WL_CanisterStand", 2, [14, 55]),
    "pallet": ("WL_Pallet", 2, [10, 45]),
    "floor_scale": ("WL_FloorScale", 2, [12, 50]),
    "dock_board": ("WL_DockBoard", 2, [16, 60]),
    "tally_desk": ("WL_TallyDesk", 2, [12, 50]),
}
MCOL = {}
for key, (model, _, _) in MODEL_KEYS.items():
    p = MODELS / f"{key}.json"
    if p.exists():
        MCOL[model] = json.loads(p.read_text()).get("colliders", [])

SPOTS = {}
CUR = None


def spot(name, retire=()):
    global CUR
    SPOTS[name] = {"root": "Ward life: " + name, "instances": [], "decals": [], "retire": list(retire)}
    CUR = SPOTS[name]


def M(model, x, z, yaw=0.0, name=None, y=0.0):
    CUR["instances"].append({"kind": "model", "prefab": WLP + model + ".prefab", "model": model, "name": name or model,
                             "pos": [round(x, 3), round(y, 3), round(z, 3)], "yaw": yaw})


def K(prop, x, z, yaw=0.0, name=None, y=0.0, note=""):
    if prop not in SIZE:
        raise SystemExit("unknown kit prop " + prop)
    CUR["instances"].append({"kind": "kit", "prefab": SD + prop + ".prefab", "prop": prop, "name": name or prop,
                             "pos": [round(x, 3), round(y, 3), round(z, 3)], "yaw": yaw, "note": note})


def D(mat, x, z, sx, sz, yaw=0.0, opacity=1.0, uv=None, y=0.0, name=None):
    CUR["decals"].append({"mat": mat, "pos": [x, y, z], "size": [sx, sz], "yaw": yaw, "opacity": opacity, "uv": uv,
                          "name": name or mat})


# atlas cells of WL_DecalMarks (cols 0-1 x rows 0-3 from the top, each 0.5 x 0.25 of the texture)
def cell(c, r):
    return [0.5, 0.25, c * 0.5, (3 - r) * 0.25]


LINE = [0.48, 0.11, 0.51, 0.32]        # the solid worn line in cell (1, 2)

# ================================================================== 1. West Gate bastions
spot("West Gate bastions", retire=["Ward building: West Gate bastions"])
M("WL_GateBastionS", 44.0, -10.75, 270, "Gate bastion south (post 1)")
M("WL_GateBastionN", 44.0, 22.5, 270, "Gate bastion north (post 2)")
# sand blown against the street faces, a scatter of spilled fill where feet kick it, grime where the gun crews stand
D("WG_DecalSandSpill", 44.55, -12.6, 2.6, 1.6, 90, 0.9)
D("WG_DecalSandSpill", 44.6, -9.6, 2.0, 1.2, 90, 0.7)
D("WG_DecalGrime", 43.6, -9.6, 1.8, 1.6, 0, 0.6)
D("WG_DecalSandSpill", 44.6, 21.0, 2.4, 1.4, 90, 0.8)
D("WG_DecalSandSpill", 44.55, 24.0, 2.0, 1.4, 90, 0.75)
D("WG_DecalGrime", 43.6, 21.2, 1.8, 1.6, 0, 0.6)

# ================================================================== 2. Lattice court: water ration point
spot("Lattice court water ration")
M("WL_WaterPoint", 1.9, -34.5, 0, "Water ration point")
v = "queue: cans left in line"
for i, (prop, yaw) in enumerate((("jerrycan_green", 84), ("jerrycan_red", 97), ("churn", 0), ("jerrycan_green", 79),
                                 ("jerrycan_green", 101), ("bucket_wood", 0), ("jerrycan_red", 88))):
    K(prop, 4.55 + (0.05 if i % 2 else -0.04), -27.75 + i * 0.42, yaw, f"Queue {i + 1} · {prop}")
K("handcart", 7.55, -27.35, 196, "Handcart for the household drums")
K("drum_blue", 8.6, -28.35, 30, "Household water drum")
K("drum_blue", 9.15, -27.75, 75, "Household water drum")
K("jerrycan_green", 3.75, -28.3, 12, "Filled can by the trough")
K("bucket_wood", 0.85, -28.15, 40, "Bucket at the first tap")
K("tub_wood", -0.25, -28.85, 0, "Washing tub at the trough end")
K("stool_wood", 5.0, -29.72, 15, "Warden's stool")
K("bench_painted", -1.4, -27.0, 90, "Bench for the waiting elders")
K("drum_blue", 0.1, -40.95, 20, "Spare ration drum")
K("drum_steel_blue", -0.6, -40.45, 60, "Spare ration drum")
D("WL_DecalDamp", 1.9, -28.25, 4.4, 1.7, 0, 0.95, name="Damp paving at the taps")
D("WL_DecalDamp", 1.9, -39.9, 1.4, 0.9, 0, 0.8, name="Damp round the tank valve")
SCUFF = [0.49, 0.49, 0.005, 0.005]     # weathering atlas quadrants (street dressing): scuffs, grime
GRIME = [0.49, 0.49, 0.505, 0.505]
D("Sand grime scuffs and runoff", 5.0, -29.1, 1.8, 1.4, 0, 0.6, GRIME, name="Grime round the tally desk")
D("WG_DecalGrime", 8.3, -27.8, 2.4, 1.8, 20, 0.55, name="Cart grime")

# ================================================================== 3. Node 07 goods dock
spot("Node 07 goods dock")
# east node (9, 40.75): door lane x 7.9..10.1, z 36..40.6 kept clear; scale at the lane mouth
M("WL_FloorScale", 9.0, 35.0, 0, "Platform scale")
M("WL_CanisterPallet", 6.45, 36.65, 2, "Bay 1 · canisters (inbound)")
M("WL_CanisterStand", 6.4, 35.25, -4, "Bay 1 · canisters standing")
M("WL_CanisterPallet", 11.75, 38.6, 91, "Bay 2 · canisters (inbound)")
K("crate_wood_deep", 12.55, 37.25, 88, "Bay 2 · crate")
K("crate_long", 12.55, 37.25, 92, "Bay 2 · crate on crate", y=0.46)
M("WL_Pallet", 11.6, 34.45, 0, "Bay 3 · outbound pallet")
K("carton", 11.3, 34.25, 3, "Bay 3 · carton", y=0.144)
K("carton", 11.75, 34.3, -4, "Bay 3 · carton", y=0.144)
K("carton", 11.5, 34.7, 92, "Bay 3 · carton", y=0.144)
K("carton", 11.45, 34.3, 1, "Bay 3 · carton on carton", y=0.484)
K("tote_blue", 12.65, 34.05, 88, "Bay 3 · tote")
K("sack_tied_c", 12.75, 35.25, 30, "Bay 3 · grain sack")
K("hand_truck", 13.55, 33.4, 205, "Porter's hand truck")
K("handcart", 9.7, 32.1, 160, "Porters' handcart waiting")
M("WL_TallyDesk", 12.3, 31.95, 0, "Tally desk")
K("stool_folding", 13.75, 31.2, -140, "Porters' stool")
K("crate_wood", 13.9, 32.25, 10, "Porters' crate seat")
K("pot_enamel", 13.9, 32.25, 30, "Tea on the crate", y=0.35)
M("WL_DockBoard", 14.15, 36.2, -90, "Dock board")
# west node (-9, 40.75): outbound goods waiting under a tarp, a hand truck
K("tarp_stack", -9.7, 37.55, 4, "Outbound stock under tarp")
K("hand_truck", -7.75, 38.15, 200, "Hand truck")
K("carton", -11.25, 38.25, 7, "Carton")
K("carton", -11.3, 38.3, -3, "Carton on carton", y=0.34)
# painted marks: bay outlines, numbers, weigh, keep clear; trolley tracks out of the doors; grime where goods stand
def bay(x0, x1, z0, z1, label, lx, lz):
    D("WL_DecalMarks", (x0 + x1) / 2, z0, x1 - x0, 0.1, 0, 0.85, LINE)
    D("WL_DecalMarks", (x0 + x1) / 2, z1, x1 - x0, 0.1, 0, 0.85, LINE)
    D("WL_DecalMarks", x0, (z0 + z1) / 2, z1 - z0, 0.1, 90, 0.85, LINE)
    D("WL_DecalMarks", x1, (z0 + z1) / 2, z1 - z0, 0.1, 90, 0.85, LINE)
    D("WL_DecalMarks", lx, lz, 1.5, 0.375, 0, 0.9, label)
bay(5.4, 7.55, 34.4, 37.45, cell(0, 0), 6.45, 33.95)
bay(10.45, 13.3, 36.4, 39.6, cell(1, 0), 11.85, 35.95)
bay(10.45, 13.3, 33.3, 35.9, cell(0, 1), 11.85, 32.85)
D("WL_DecalMarks", 9.0, 33.95, 1.3, 0.33, 0, 0.9, cell(1, 1), name="WEIGH")
D("WL_DecalMarks", 9.0, 39.85, 2.0, 0.5, 0, 0.85, cell(0, 2), name="KEEP CLEAR")
D("WL_DecalMarks", -9.0, 39.85, 1.6, 0.4, 0, 0.8, cell(0, 3), name="GOODS")
D("WG_DecalTyreTracks", 9.0, 37.9, 1.4, 4.8, 0, 0.6, name="Trolley tracks from the node door")
D("WG_DecalTyreTracks", -9.0, 38.6, 1.3, 3.4, 0, 0.5, name="Trolley tracks, west node")
D("WG_DecalGrime", 11.85, 38.0, 3.0, 3.2, 0, 0.45, name="Grime under bay 2")
D("WG_DecalGrime", 6.45, 35.9, 2.4, 3.0, 0, 0.45, name="Grime under bay 1")

# ================================================================== review cameras (player height 1.65 m)
CAMERAS = [
    ("cam_wl_gate_south_wide", (39.4, 1.65, -6.6), (45.0, 1.0, -11.5), 55),
    ("cam_wl_gate_south_blast", (41.9, 1.65, -11.2), (44.95, 0.8, -13.1), 55),
    ("cam_wl_gate_north_wide", (39.8, 1.65, 17.2), (45.0, 1.0, 22.6), 55),
    ("cam_wl_gate_north_burst", (41.9, 1.65, 21.2), (44.95, 0.6, 23.2), 55),
    ("cam_wl_court_north", (1.2, 1.65, -22.6), (2.2, 1.0, -32.0), 55),
    ("cam_wl_court_taps", (4.3, 1.65, -26.2), (1.6, 0.75, -29.0), 55),
    ("cam_wl_court_desk", (7.4, 1.65, -26.9), (5.0, 1.0, -29.4), 55),
    ("cam_wl_court_tank", (-1.6, 1.65, -35.6), (1.9, 1.4, -41.2), 55),
    ("cam_wl_dock_plaza", (2.6, 1.65, 27.4), (10.0, 0.8, 37.0), 55),
    ("cam_wl_dock_bays", (14.6, 1.65, 30.6), (9.5, 0.6, 37.5), 55),
    ("cam_wl_dock_scale", (6.6, 1.65, 31.9), (9.0, 0.5, 35.6), 55),
    ("cam_wl_dock_west", (-4.6, 1.65, 32.6), (-9.5, 0.7, 38.4), 55),
]

# ================================================================== validation
def rect_of_kit(it):
    sx, sy, sz = SIZE[it["prop"]]
    a = math.radians(it["yaw"])
    hx = abs(sx * math.cos(a)) / 2 + abs(sz * math.sin(a)) / 2
    hz = abs(sx * math.sin(a)) / 2 + abs(sz * math.cos(a)) / 2
    x, y, z = it["pos"]
    return (x - hx, x + hx, z - hz, z + hz, y, y + sy)


def rects_of_model(it):
    out = []
    a = math.radians(it["yaw"])
    ca, sa = math.cos(a), math.sin(a)
    x, _, z = it["pos"]
    for c in MCOL.get(it["model"], []):
        cx, cy, cz = c["center"]; sx, sy, sz = c["size"]
        # Unity yaw: local (lx, lz) -> world (x + lx*cos + lz*sin, z - lx*sin + lz*cos)
        wx, wz = x + cx * ca + cz * sa, z - cx * sa + cz * ca
        hx = abs(sx * ca) / 2 + abs(sz * sa) / 2
        hz = abs(sx * sa) / 2 + abs(sz * ca) / 2
        out.append((wx - hx, wx + hx, wz - hz, wz + hz, cy - sy / 2, cy + sy / 2, c["name"]))
    return out


def overlap(a, b, m=0.0):
    return a[0] < b[1] + m and b[0] < a[1] + m and a[2] < b[3] + m and b[2] < a[3] + m


def seg_dist(px, pz, a, b):
    ax, az = a; bx, bz = b
    dx, dz = bx - ax, bz - az
    t = max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / (dx * dx + dz * dz + 1e-9)))
    return math.hypot(px - ax - dx * t, pz - az - dz * t)


def rect_seg_dist(r, a, b):
    best = 9e9
    for k in range(21):
        t = k / 20
        px, pz = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        dx = max(r[0] - px, 0, px - r[1]); dz = max(r[2] - pz, 0, pz - r[3])
        best = min(best, math.hypot(dx, dz))
    return best


IGNORE = ("Ward building: West Gate bastions", "Ward life:", "Player", "Colonists/", "Ward wall-foot drifts")
scene_cols = []
for c in A["colliders"]:
    if c["trigger"] or any(c["path"].startswith(p) for p in IGNORE) or "camera only" in c["path"]:
        continue
    (x, y, z), (sx, sy, sz) = c["center"], c["size"]
    if y + sy / 2 < 0.03:
        continue
    scene_cols.append((x - sx / 2, x + sx / 2, z - sz / 2, z + sz / 2, y - sy / 2, y + sy / 2, c["path"]))
routes = {}
markers = []
for m_ in A["markers"]:
    parts = m_["path"].split("/")
    if parts[0].endswith(" route"):
        routes.setdefault(parts[0], []).append((m_["pos"][0], m_["pos"][2]))
    else:
        markers.append((m_["path"], m_["pos"][0], m_["pos"][2]))
segs = [(n, p[i], p[(i + 1) % len(p)]) for n, p in routes.items() for i in range(len(p))]
# QA walking corridors (unity/tools): hall loop and ring approach; the old Lattice Jack walk is retired with the Jack
QA = [("lattice", [(-6, -22), (-10, -23.9), (-10, -25.3), (-4, -23), (-12.8, -20)]),
      ("ring", [(-6, 20.5), (0, 21), (0, 28), (0, 32.8)]),
      ("vanguard east side", [(-3.1, -25.0), (-3.1, -32.6), (-3.1, -23.2)]),
      ("gate spawn out", [(43, 0), (38, 0), (30, 0)])]
CLEAR = [("Node 07 east door lane", 7.9, 10.1, 36.0, 40.6), ("Node 07 west door lane", -10.1, -7.9, 39.0, 40.6),
         ("ring and approach", -4.4, 4.4, 30.5, 39.0), ("gate passage", 44.0, 49.0, -3.0, 15.0)]

problems = []
placed = []
for sname, sp in SPOTS.items():
    for it in sp["instances"]:
        rs = [rect_of_kit(it) + (it["name"],)] if it["kind"] == "kit" else rects_of_model(it)
        if it["kind"] == "model" and it["model"].startswith("WL_GateBastion"):
            continue        # same footprint as round two (checked in Unity verify against markers/routes)
        for r in rs:
            for c in scene_cols:
                if overlap(r, c, -0.02) and r[4] < c[5] - 0.02 and c[4] < r[5]:
                    problems.append(f"{it['name']} / {r[6]} hits {c[6]}")
            for (n, a, b) in segs:
                if rect_seg_dist(r, a, b) < 1.0:
                    problems.append(f"{it['name']} within 1 m of route {n}")
            for (n, px, pz) in markers:
                if max(r[0] - px, 0, px - r[1]) ** 2 + max(r[2] - pz, 0, pz - r[3]) ** 2 < 1.0:
                    problems.append(f"{it['name']} within 1 m of marker {n}")
            for (n, pts) in QA:
                for a, b in zip(pts, pts[1:]):
                    if rect_seg_dist(r, a, b) < 0.9:
                        problems.append(f"{it['name']} within 0.9 m of QA walk {n}")
            for (n, x0, x1, z0, z1) in CLEAR:
                if overlap(r, (x0, x1, z0, z1)):
                    problems.append(f"{it['name']} in {n}")
            for (on, o) in placed:
                if on != it["name"] and overlap(r, o, -0.03) and r[4] < o[5] - 0.02 and o[4] < r[5] - 0.02 and abs(r[4] - o[5]) > 0.03:
                    problems.append(f"{it['name']} overlaps {on}")
        for r in rs:
            placed.append((it["name"], r))

out = {"_doc": __doc__, "date": "2026-10-03",
       "models": [{"key": k, "model": m, "lods": n, "lodDistances": d} for k, (m, n, d) in MODEL_KEYS.items()],
       "spots": list(SPOTS.values()),
       "cameraRoot": "Ward life review cameras",
       "cameras": [{"name": n, "pos": list(p), "target": list(t), "fov": f} for (n, p, t, f) in CAMERAS]}
(HERE / "layout.json").write_text(json.dumps(out, indent=1))
print(f"{sum(len(s['instances']) for s in SPOTS.values())} instances, {sum(len(s['decals']) for s in SPOTS.values())} decals, "
      f"{len(CAMERAS)} cameras; {len(set(problems))} problems")
for p in sorted(set(problems)):
    print("  -", p)
sys.exit(1 if problems else 0)
