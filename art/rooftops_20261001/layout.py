#!/usr/bin/env python3
"""Ward rooftops layout (1 Oct 2026): plain Python, no Blender. Writes layout.json for author_cables.py (Blender) and
Unity (Editor/RooftopsPass.cs), review/layout-map.png and review/layout-report.json.

Next-wins item 8: "Place 1-2 per building so they break the skyline *as seen from the avenue* ... Add 3-4 sagging
service cables between rooftop masts across the cross streets." Each roof gets one or two pieces that say what the
building does for Ward and that rise above its cornice where the avenue can see them:
  Relay Works   HF whip on the front corner (comms), a gooseneck cowl
  Air + Water   dew/condensate net across the front of the roof (beside its tank), service-line mast, caged ladder
  Tool Exchange two PV panels tilted to the avenue (the nanofab's power), service-line mast
  Salvage       a roof terrace: shade canvas on a pipe frame, two seats and a crate, guard rail on the front parapet
  Finery        a tall galvanised water tank forward on the roof, guard rail along the front, a cowl; caged ladder
  Field Supply  two turbine ventilators on the ridge and a ridge-saddle service-line mast
  Repairs       a comms dish on the container workshop, service-line mast
  Thread + Hide a horizontal tank (dye and wash water) on a stand behind the drying lines, a cowl, a front rail
Service lines: two conductors across each cross street (Air + Water <-> Tool Exchange, Field Supply <-> Repairs), a
short line across each narrow alley on wall hooks, and four conduit drops from the masts down the side walls into
junction boxes (cleated to the stone, routed round the cornice and string course).

Coordinates: placements are in each shop's frame (roofs.py: origin = facade centre at paving level, +Z to the avenue)
and converted to world metres (x east, z north, y up; Unity yaw, props face +Z). Cables are world-space polylines.
Validation (review/layout-report.json; exits non-zero on problems): deck footprints inside the parapets, clear of the
existing roof furniture (hatches, air conditioners, masts and guys, tanks, shed, container, drying lines) and of each
other; 1.8 m from the night-life smoke columns (Repairs forge flue, Salvage stovepipe), cables included; wall pieces
clear of windows, doors, lamps, downpipes and boxes; ladder feet and conduit ends clear of the saved colliders,
walker/mechanic/droid routes, NPC/landmark points and door approaches. A skyline check reports, for each piece, how
much of it rises above the rooflines from points along the avenue at 1.6 m eye height.

Run: uv run --with matplotlib python layout.py   (needs unity/evidence/rooftops/20261001/audit-before.json, else the
     latest night-life audit)
"""
import json, math, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from roofs import SHOPS, to_world, HW, D, PARAPET_IN, gable_y, SMOKE_CLEAR

KIT = json.loads((ROOT / "unity/AthenHill/Assets/AthenHill/Art/Rooftops/Models/kit.json").read_text())
SD_SIZES = {}
for f in ("ph-props.json", "meshy-props.json", "authored-props.json"):
    p = ROOT / "unity/AthenHill/Assets/AthenHill/Art/StreetDressing/Props" / f
    if p.exists():
        for k, v in json.loads(p.read_text()).items():
            SD_SIZES[k] = v["size"]
AUDIT_PATH = ROOT / "unity/evidence/rooftops/20261001/audit-before.json"
if not AUDIT_PATH.exists():
    AUDIT_PATH = ROOT / "unity/evidence/night-life/20261001/audit-before.json"
AUDIT = json.loads(AUDIT_PATH.read_text())


def Ry(yaw, v):
    a = math.radians(yaw)
    x, y, z = v
    return (x * math.cos(a) + z * math.sin(a), y, -x * math.sin(a) + z * math.cos(a))


def add(a, b):
    return [a[0] + b[0], a[1] + b[1], a[2] + b[2]]


# ====================================================================== placements (shop frame)
GROUPS = {}          # shop key -> list of items
WALL = {}            # wall pieces: shop key -> list


def item(shop, oid, pos, yaw=0.0, note="", on=None, sd=False):
    it = {"id": oid, "pos": [round(v, 4) for v in pos], "yaw": yaw, "note": note, "sd": sd, "on": on}
    GROUPS.setdefault(shop, []).append(it)
    return it


def deck(shop):
    return SHOPS[shop]["deck"]


def coping(shop):
    return SHOPS[shop]["coping"]


INNER_COPING_Z = 0.092 + 0.02 - 0.46      # inner edge of the coping above the front parapet (-0.348)

# --- Relay Works: comms
item("relay_works", "Whip", (-2.5, deck("relay_works"), -1.45), 0, "HF whip on the front corner, guyed stub mast")
item("relay_works", "VentCowl", (0.4, deck("relay_works"), -1.0), 200, "gooseneck cowl near the front parapet")
# --- Air + Water: water from the air
item("air_water", "DewNet", (1.3, deck("air_water"), -1.5), 180, "dew/condensate net across the front, drum to the -X side")
item("air_water", "CableMast", (-2.5, deck("air_water"), -2.4), 90, "service-line mast, west cross street (north side of Air + Water)")
# --- Tool Exchange: power for the fabricator
item("tool_exchange", "SolarFrame", (1.25, deck("tool_exchange"), -1.5), 0, "two PV panels tilted to the avenue")
item("tool_exchange", "CableMast", (2.45, deck("tool_exchange"), -3.4), -90, "service-line mast, west cross street (south side of Tool Exchange)")
# --- Salvage: a roof terrace for the scavengers
item("salvage", "ShadeFrame", (1.65, deck("salvage"), -1.8), 0, "shade canvas over a lookout seat")
item("salvage", "stool_folding", (1.15, deck("salvage"), -1.4), 25, "seat under the shade", sd=True)
item("salvage", "stool_wood", (2.35, deck("salvage"), -1.6), -40, "seat under the shade", sd=True)
item("salvage", "crate_wood_deep", (1.75, deck("salvage"), -2.4), 8, "crate used as a table", sd=True)
item("salvage", "Rail320", (1.65, coping("salvage"), INNER_COPING_Z), 0, "guard rail along the terrace's front parapet", on="coping")
# --- Finery: water store and a terrace rail
item("finery", "TankTall", (1.5, deck("finery"), -2.7), 0, "galvanised water tank on a stand, forward on the roof")
item("finery", "Rail660", (0.0, coping("finery"), INNER_COPING_Z), 0, "guard rail along the front parapet", on="coping")
item("finery", "VentCowl", (-2.4, deck("finery"), -1.3), 160, "gooseneck cowl")
# --- Field Supply: ventilate the store, carry the line
FS_RIDGE = 8.26
item("field_supply", "TurbineVentRidge", (0.0, FS_RIDGE, -1.5), 0, "turbine ventilator on the ridge")
item("field_supply", "TurbineVentRidge", (0.0, FS_RIDGE, -5.2), 0, "turbine ventilator on the ridge")
item("field_supply", "CableMastRidge", (0.0, FS_RIDGE, -3.4), 0, "ridge-saddle service-line mast, east cross street")
# --- Repairs: radios mended here
CONTAINER_TOP = 6.74 + 0.22 + 1.9 - 0.02
item("repairs", "Dish", (0.35, CONTAINER_TOP, -2.35), 0, "comms dish on the container workshop roof", on="container")
item("repairs", "CableMast", (-2.55, deck("repairs"), -4.4), 90, "service-line mast, east cross street (south side of Repairs)")
# --- Thread + Hide: dye water
item("thread_hide", "TankLow", (-1.2, deck("thread_hide"), -4.9), 90, "horizontal dye/wash water tank behind the drying lines")
item("thread_hide", "VentCowl", (2.6, deck("thread_hide"), -1.0), 140, "gooseneck cowl")
item("thread_hide", "Rail660", (0.0, coping("thread_hide"), INNER_COPING_Z), 0, "guard rail along the drying terrace's front parapet", on="coping")

# --- wall pieces: (shop, id, face, u = local z along the wall, y, note); face left = local x -3.8, right = +3.8
FACE_X = {"left": -HW, "right": HW}
WALL_YAW = {"left": -90.0, "right": 90.0}          # prefab +Z out of the wall
STONE = 0.062                                      # wall block faces stand 6.2 cm proud of the frame plane


def wall(shop, oid, face, z, y, note, off=STONE):
    x = FACE_X[face] + (off if face == "right" else -off)
    it = {"id": oid, "pos": [round(x, 4), round(y, 4), round(z, 4)], "yaw": WALL_YAW[face], "note": note, "sd": False,
          "on": "wall", "face": face}
    GROUPS.setdefault(shop, []).append(it)
    return it


LADDERS = [wall("air_water", "Ladder876", "left", -6.0, 0.0, "caged service ladder up the cross-street wall", off=0.0),
           wall("finery", "Ladder919", "left", -5.9, 0.0, "caged service ladder up the south wall", off=0.0)]
BOXES = {
    "air_water": wall("air_water", "JunctionBox", "left", -2.4, 2.85, "junction box at the foot of the service drop"),
    "tool_exchange": wall("tool_exchange", "JunctionBox", "right", -4.3, 2.85, "junction box at the foot of the service drop"),
    "field_supply": wall("field_supply", "JunctionBox", "right", -4.2, 2.85, "junction box at the foot of the service drop"),
    "repairs": wall("repairs", "JunctionBox", "left", -6.35, 2.8, "junction box at the foot of the service drop"),
}
HOOKS = {
    ("relay_works", 0): wall("relay_works", "WallHook", "left", -1.2, 7.2, "alley line hook"),
    ("relay_works", 1): wall("relay_works", "WallHook", "left", -2.0, 7.0, "alley line hook"),
    ("air_water", 0): wall("air_water", "WallHook", "right", -1.0, 7.25, "alley line hook"),
    ("air_water", 1): wall("air_water", "WallHook", "right", -1.9, 6.95, "alley line hook"),
    ("repairs", 0): wall("repairs", "WallHook", "right", -1.4, 6.0, "alley line hook"),
    ("repairs", 1): wall("repairs", "WallHook", "right", -2.0, 5.85, "alley line hook"),
    ("thread_hide", 0): wall("thread_hide", "WallHook", "left", -1.5, 6.6, "alley line hook"),
    ("thread_hide", 1): wall("thread_hide", "WallHook", "left", -2.05, 6.35, "alley line hook"),
}


# ====================================================================== world transforms and anchors
def world_of(shop, it):
    p, yaw = to_world(shop, it["pos"], it["yaw"])
    return p, yaw


def anchor(shop, it, name):
    p, yaw = world_of(shop, it)
    a = KIT[it["id"]]["anchors"][name]
    return [round(v, 4) for v in add(p, Ry(yaw, a))]


def find(shop, oid):
    return next(i for i in GROUPS[shop] if i["id"] == oid)


# ====================================================================== cables
CABLES = []


def span(name, group, a, b, sag, r, note):
    CABLES.append({"name": name, "group": group, "kind": "span", "a": a, "b": b, "sag": sag, "radius": r, "note": note})


def conduit(name, group, pts, r, note, clips=0.75):
    CABLES.append({"name": name, "group": group, "kind": "conduit", "points": [[round(v, 4) for v in p] for p in pts],
                   "radius": r, "clips": clips, "note": note})


AW_M, TE_M = find("air_water", "CableMast"), find("tool_exchange", "CableMast")
FS_M, RP_M = find("field_supply", "CableMastRidge"), find("repairs", "CableMast")
for w, sag, r in (("wirea", 0.55, 0.013), ("wirec", 0.62, 0.011)):
    span(f"West cross street {w[-1]}", "Service lines (west cross street)", anchor("air_water", AW_M, w), anchor("tool_exchange", TE_M, "wirec" if w == "wirea" else "wirea"),
         sag, r, "Air + Water mast to Tool Exchange mast")
    span(f"East cross street {w[-1]}", "Service lines (east cross street)", anchor("field_supply", FS_M, w), anchor("repairs", RP_M, "wirec" if w == "wirea" else "wirea"),
         sag + 0.05, r, "Field Supply ridge mast to Repairs mast")
for k in (0, 1):
    span(f"West alley line {k + 1}", "Service lines (west alley)", anchor("relay_works", HOOKS[("relay_works", k)], "wire"),
         anchor("air_water", HOOKS[("air_water", k)], "wire"), 0.05 + 0.03 * k, 0.01, "Relay Works to Air + Water, across the alley")
    span(f"East alley line {k + 1}", "Service lines (east alley)", anchor("repairs", HOOKS[("repairs", k)], "wire"),
         anchor("thread_hide", HOOKS[("thread_hide", k)], "wire"), 0.04 + 0.04 * k, 0.01, "Repairs to Thread + Hide, across the alley")


def wall_route(shop, face, z, top_y, box_top_y, wall_top, string=(4.83, 5.08), cornice_h=0.45):
    """Conduit down a side wall in shop-local coordinates: off the coping, round the cornice (0.43 m) and the string
    course (0.15 m), cleated to the stone (0.07 m out) down to the junction box's top gland."""
    sx = 1 if face == "right" else -1
    X = lambda off: sx * (HW + off)
    pts = [(X(0.25), top_y, z), (X(0.5), top_y - 0.12, z), (X(0.5), wall_top - 0.08, z), (X(0.1), wall_top - 0.32, z)]
    if string and string[0] < wall_top - 0.5 and string[0] > box_top_y:
        pts += [(X(0.1), string[1] + 0.22, z), (X(0.21), string[1] + 0.06, z), (X(0.21), string[0] - 0.06, z), (X(0.1), string[0] - 0.22, z)]
    pts += [(X(0.1), box_top_y + 0.18, z), (X(0.1), box_top_y, z)]
    return pts


def L(shop, p):
    return to_world(shop, p)[0]


def box_top(shop):
    return anchor(shop, BOXES[shop], "top")


def box_bottom(shop):
    return anchor(shop, BOXES[shop], "bottom")


def mast_box(shop, m):
    return anchor(shop, m, "box")


def drop_from_deck_mast(shop, m, face, z, wall_top):
    """Mast box -> down the pipe -> along the deck -> up the parapet's inner face -> over the coping -> down the wall."""
    d, c = deck(shop), coping(shop)
    sx = 1 if face == "right" else -1
    mb = mast_box(shop, m)
    mloc = m["pos"]
    bx = box_top(shop)
    down = add(mb, (0, -(mb[1] - d - 0.05), 0))
    from roofs import to_local
    ml = to_local(shop, down)
    loc = [(ml[0], d + 0.05, z), (sx * (HW - PARAPET_IN - 0.06), d + 0.05, z), (sx * (HW - PARAPET_IN - 0.06), c - 0.05, z),
           (sx * (HW - 0.2), c + 0.05, z)]
    wall_pts = wall_route(shop, face, z, c + 0.05, bx[1], wall_top)
    return [mb, down] + [L(shop, p) for p in loc] + [L(shop, p) for p in wall_pts]


conduit("Air + Water service drop", "Service drop (Air + Water)", drop_from_deck_mast("air_water", AW_M, "left", -2.4, 7.6), 0.018,
        "mast to the junction box on the cross-street wall")
conduit("Tool Exchange service drop", "Service drop (Tool Exchange)", drop_from_deck_mast("tool_exchange", TE_M, "right", -4.3, 5.92), 0.018,
        "mast to the junction box on the cross-street wall")
conduit("Repairs service drop", "Service drop (Repairs)", drop_from_deck_mast("repairs", RP_M, "left", -6.35, 6.34), 0.018,
        "mast to the junction box on the cross-street wall")
# Field Supply: from the ridge mast's box down the north slope (0.06 m above the sheets) and the eave to the wall
fs_mb = mast_box("field_supply", FS_M)
fs_pts = [fs_mb, add(fs_mb, (0, -0.55, 0))]
zf = -4.2
for x in (0.25, 1.2, 2.2, 3.2, 4.15):
    fs_pts.append(L("field_supply", (x, gable_y("field_supply", x) + 0.07, -3.6 + (zf + 3.6) * x / 4.15)))
eave_y = gable_y("field_supply", 4.25)
fs_pts += [L("field_supply", (4.32, eave_y - 0.12, zf)), L("field_supply", (4.32, 4.7, zf)), L("field_supply", (3.8 + 0.1, 4.45, zf)),
           L("field_supply", (3.8 + 0.1, box_top("field_supply")[1] + 0.18, zf)), box_top("field_supply")]
conduit("Field Supply service drop", "Service drop (Field Supply)", fs_pts, 0.018, "ridge mast down the north slope and wall to the junction box")
# feeds from the boxes down into the ground (cleated)
for shop in BOXES:
    bb = box_bottom(shop)
    conduit(f"{SHOPS[shop]['name']} ground feed", f"Service drop ({SHOPS[shop]['name']})", [bb, add(bb, (0, -(bb[1] - 0.04), 0))], 0.02, "junction box to the ground")


# ====================================================================== validation
PROBLEMS, NOTES = [], []
DX = (-HW + PARAPET_IN, HW - PARAPET_IN)
DZ = (-D + PARAPET_IN, -PARAPET_IN)


def footprint(it):
    """Shop-local AABB (x0, x1, z0, z1, y0, y1) of an item from the kit bounds rotated by its yaw."""
    if it["sd"]:
        s = SD_SIZES[it["id"]]
        lo, hi = [-s[0] / 2, 0, -s[2] / 2], [s[0] / 2, s[1], s[2] / 2]
    else:
        lo, hi = KIT[it["id"]]["min"], KIT[it["id"]]["max"]
    xs, zs = [], []
    for x in (lo[0], hi[0]):
        for z in (lo[2], hi[2]):
            r = Ry(it["yaw"], (x, 0, z))
            xs.append(r[0] + it["pos"][0]); zs.append(r[2] + it["pos"][2])
    return min(xs), max(xs), min(zs), max(zs), it["pos"][1] + lo[1], it["pos"][1] + hi[1]


def overlap(a, b, m=0.0):
    return a[0] < b[1] - m and b[0] < a[1] - m and a[2] < b[3] - m and b[2] < a[3] - m


ITEMS_REPORT = []
for shop, items in GROUPS.items():
    s = SHOPS[shop]
    obst = [o for o in s["obstacles"] if "x" in o]
    deck_items = [i for i in items if i["on"] is None]
    for it in items:
        fp = footprint(it)
        if it["on"] is None and s.get("deck") is not None:
            if fp[0] < DX[0] - 1e-3 or fp[1] > DX[1] + 1e-3 or fp[2] < DZ[0] - 1e-3 or fp[3] > DZ[1] + 1e-3:
                PROBLEMS.append(f"{shop} {it['id']}: footprint {[round(v, 2) for v in fp[:4]]} outside the deck {DX} {DZ}")
            for o in obst:
                ob = (o["x"][0], o["x"][1], o["z"][0], o["z"][1])
                if overlap(fp, ob, 0.02) and it["id"] not in ("Rail320", "Rail660"):
                    PROBLEMS.append(f"{shop} {it['id']}: overlaps {o['note']}")
            for o in s["obstacles"]:
                if "guy" in o:
                    (gx0, _, gz0), (gx1, _, gz1) = o["guy"]
                    for t in [k / 10 for k in range(11)]:
                        gx, gz = gx0 + (gx1 - gx0) * t, gz0 + (gz1 - gz0) * t
                        gy = o["guy"][0][1] + (o["guy"][1][1] - o["guy"][0][1]) * t
                        if fp[0] - 0.05 < gx < fp[1] + 0.05 and fp[2] - 0.05 < gz < fp[3] + 0.05 and gy < fp[5] + 0.05:
                            PROBLEMS.append(f"{shop} {it['id']}: crosses a mast guy wire at ({gx:.2f}, {gy:.2f}, {gz:.2f})")
                            break
        for (sx_, sz_, sy_, note) in s.get("smoke", []):
            if fp[5] > sy_ - 1.5:
                dx = max(fp[0] - sx_, 0, sx_ - fp[1]); dz = max(fp[2] - sz_, 0, sz_ - fp[3])
                if math.hypot(dx, dz) < SMOKE_CLEAR:
                    PROBLEMS.append(f"{shop} {it['id']}: {math.hypot(dx, dz):.2f} m from {note}")
    for a_i in range(len(items)):
        for b_i in range(a_i + 1, len(items)):
            A_, B_ = items[a_i], items[b_i]
            if A_["on"] == "wall" or B_["on"] == "wall":
                continue
            if A_["sd"] or B_["sd"]:
                continue
            fa, fb = footprint(A_), footprint(B_)
            if overlap(fa, fb, 0.02) and fa[4] < fb[5] and fb[4] < fa[5]:
                PROBLEMS.append(f"{shop}: {A_['id']} overlaps {B_['id']}")

# SD props under the shade: inside the shade frame, clear of each other (circles)
sal = GROUPS["salvage"]
seats = [i for i in sal if i["sd"]]
for a_i in range(len(seats)):
    for b_i in range(a_i + 1, len(seats)):
        A_, B_ = seats[a_i], seats[b_i]
        ra = max(SD_SIZES[A_["id"]][0], SD_SIZES[A_["id"]][2]) / 2
        rb = max(SD_SIZES[B_["id"]][0], SD_SIZES[B_["id"]][2]) / 2
        d_ = math.hypot(A_["pos"][0] - B_["pos"][0], A_["pos"][2] - B_["pos"][2])
        if d_ < (ra + rb) * 0.85:
            PROBLEMS.append(f"salvage seats: {A_['id']} and {B_['id']} too close ({d_:.2f} m)")

# --- side-wall features (u = local z; from the shop author scripts): windows/doors (u0, u1, y0, y1), point fittings
FACE_FEATURES = {
    ("relay_works", "left"): [(-3.9, -3.0, 5.5, 7.18, "upper window"), (-5.4, -5.0, 1.2, 1.9, "power box")],
    ("air_water", "left"): [(-5.2, -4.3, 5.5, 7.18, "upper window"), (-1.35, -1.05, 0.0, 7.7, "downpipe")],
    ("air_water", "right"): [(-3.3, -2.4, 5.5, 7.18, "upper window"), (-5.65, -5.15, 1.2, 1.9, "power box")],
    ("tool_exchange", "right"): [(-3.5, -2.6, 1.89, 3.15, "window"), (-5.75, -5.45, 0.0, 6.0, "downpipe")],
    ("field_supply", "right"): [(-3.1, -2.2, 1.89, 3.15, "window"), (-5.75, -5.25, 1.2, 1.9, "power box")],
    ("finery", "left"): [(-3.4, -2.4, 5.5, 7.18, "upper window"), (-1.15, -0.85, 0.0, 8.1, "downpipe")],
    ("repairs", "left"): [(-3.2, -2.3, 1.89, 3.15, "window"), (-4.5, -3.6, 5.5, 6.34, "upper window"), (-2.3, -1.4, 5.5, 6.34, "upper window"),
                          (-5.82, -4.88, 0.0, 3.2, "side door"), (-5.55, -5.15, 3.5, 4.1, "side door lamp"), (-3.0, -2.5, 3.9, 4.45, "power box"),
                          (-2.2, -1.3, 1.5, 8.4, "forge flue")],
    ("repairs", "right"): [(-3.1, -2.2, 1.89, 3.15, "window"), (-1.55, -1.05, 3.95, 4.45, "security light"), (-5.75, -5.45, 0.0, 6.4, "downpipe")],
    ("thread_hide", "left"): [(-3.3, -2.4, 5.5, 7.18, "upper window"), (-5.3, -4.4, 1.89, 3.15, "window"), (-1.15, -0.85, 0.0, 7.7, "downpipe")],
}
# right-face features are listed with u = local z (already converted: z = -u)
for shop, items in GROUPS.items():
    for it in items:
        if it["on"] != "wall":
            continue
        face = it["face"]
        size = KIT[it["id"]]["size"]
        lo, hi = KIT[it["id"]]["min"], KIT[it["id"]]["max"]
        z0, z1 = it["pos"][2] + lo[0], it["pos"][2] + hi[0]
        y0, y1 = it["pos"][1] + lo[1], it["pos"][1] + hi[1]
        if it["id"].startswith("Ladder"):
            y1 = coping(shop)
        for (u0, u1, fy0, fy1, what) in FACE_FEATURES.get((shop, face), []):
            if z0 < u1 + 0.12 and u0 - 0.12 < z1 and y0 < fy1 + 0.1 and fy0 - 0.1 < y1:
                PROBLEMS.append(f"{shop} {face} wall {it['id']} at z {it['pos'][2]}: overlaps the {what}")
# conduit wall runs vs features (sample points within 0.3 m of the wall plane)
for c in CABLES:
    if c["kind"] != "conduit":
        continue
    shop = next((s for s in SHOPS if SHOPS[s]["name"] in c["name"]), None)
    if not shop:
        continue
    from roofs import to_local
    for p in c["points"]:
        lp = to_local(shop, p)
        for face, fx in FACE_X.items():
            if abs(abs(lp[0]) - HW) < 0.3 and (lp[0] > 0) == (face == "right"):
                for (u0, u1, fy0, fy1, what) in FACE_FEATURES.get((shop, face), []):
                    if u0 - 0.1 < lp[2] < u1 + 0.1 and fy0 - 0.1 < lp[1] < fy1 + 0.1:
                        PROBLEMS.append(f"{c['name']}: passes the {what} at y {lp[1]:.2f}")

# --- spans: smoke clearance, roof clearance, sag sanity
SMOKES = []
for shop, s in SHOPS.items():
    for (sx_, sz_, sy_, note) in s.get("smoke", []):
        SMOKES.append((to_world(shop, (sx_, sy_, sz_))[0], note))
BODIES = []
for shop, s in SHOPS.items():
    top = s["coping"] if s["coping"] else s["gable"]["ridge"] + 0.2
    lo = to_world(shop, (-HW - 0.1, 0, -D - 0.1))[0]; hi = to_world(shop, (HW + 0.1, 0, 0.1))[0]
    BODIES.append((shop, min(lo[0], hi[0]), max(lo[0], hi[0]), min(lo[2], hi[2]), max(lo[2], hi[2]), top))


def span_pts(c, n=32):
    a, b, s = c["a"], c["b"], c["sag"]
    return [[a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t - 4 * s * t * (1 - t), a[2] + (b[2] - a[2]) * t] for t in [k / n for k in range(n + 1)]]


for c in CABLES:
    pts = span_pts(c) if c["kind"] == "span" else c["points"]
    for p in pts:
        for (sp, note) in SMOKES:
            if p[1] > sp[1] - 1.0 and math.hypot(p[0] - sp[0], p[2] - sp[2]) < SMOKE_CLEAR:
                PROBLEMS.append(f"{c['name']}: {math.hypot(p[0] - sp[0], p[2] - sp[2]):.2f} m from {note}")
                break
    if c["kind"] == "span":
        L_ = math.dist(c["a"], c["b"])
        if not (0.02 * L_ <= c["sag"] <= 0.06 * L_ + 0.12):
            NOTES.append(f"{c['name']}: sag {c['sag']} m on a {L_:.1f} m span")
        for p in span_pts(c)[3:-3]:
            for (shop, x0, x1, z0, z1, top) in BODIES:
                if x0 < p[0] < x1 and z0 < p[2] < z1:
                    roof = top
                    if shop == "field_supply":
                        from roofs import to_local
                        lx = to_local(shop, p)[0]
                        roof = gable_y(shop, lx)
                    if p[1] < roof + 0.35:
                        PROBLEMS.append(f"{c['name']}: only {p[1] - roof:.2f} m above {SHOPS[shop]['name']}")
                        break

# --- ground: ladder feet and conduit ends vs colliders, routes, NPC points, door approaches
SHOP_COLLIDER_ROOTS = {s: [f"Ward shops (hall district)/{SHOPS[s]['name']}/", f"Ward shops (north avenue)/{SHOPS[s]['name']}/"] for s in SHOPS}
COLS = []
for c in AUDIT["colliders"]:
    (x, y, z), (sx, sy, sz) = c["center"], c["size"]
    if sx > 60 or sz > 60 or y - sy / 2 > 2.4:
        continue
    COLS.append((c["path"], x - sx / 2, x + sx / 2, z - sz / 2, z + sz / 2, y - sy / 2, y + sy / 2))
ROUTES, POINTS = {}, []
for m in AUDIT["markers"]:
    parts = m["path"].split("/")
    if len(parts) == 2 and (parts[0].endswith(" route") or parts[0] == "Mining droid route"):
        ROUTES.setdefault(parts[0], []).append((m["pos"][0], m["pos"][2]))
    elif len(parts) == 2 and parts[0] in ("Colonists", "Landmarks"):
        POINTS.append((parts[1], m["pos"][0], m["pos"][2], 1.3))


def seg_dist(p, a, b):
    ax, az = a; bx, bz = b; px, pz = p
    L2 = (bx - ax) ** 2 + (bz - az) ** 2
    t = 0 if L2 == 0 else max(0, min(1, ((px - ax) * (bx - ax) + (pz - az) * (bz - az)) / L2))
    return math.hypot(px - (ax + t * (bx - ax)), pz - (az + t * (bz - az)))


GROUND = []
for shop, items in GROUPS.items():
    for it in items:
        if it["id"].startswith("Ladder"):
            col = KIT[it["id"]]["collider"]
            p, yaw = world_of(shop, it)
            cs = []
            for dx in (-col["size"][0] / 2, col["size"][0] / 2):
                for dz in (col["center"][2] - col["size"][2] / 2, col["center"][2] + col["size"][2] / 2):
                    r = Ry(yaw, (dx, 0, dz)); cs.append((p[0] + r[0], p[2] + r[2]))
            GROUND.append((f"{shop} {it['id']}", min(c_[0] for c_ in cs), max(c_[0] for c_ in cs), min(c_[1] for c_ in cs), max(c_[1] for c_ in cs), shop))
for c in CABLES:
    if c["kind"] == "conduit" and "ground feed" in c["name"]:
        p = c["points"][-1]
        shop = next(s for s in SHOPS if SHOPS[s]["name"] in c["name"])
        GROUND.append((c["name"], p[0] - 0.06, p[0] + 0.06, p[2] - 0.06, p[2] + 0.06, shop))
for (name, x0, x1, z0, z1, shop) in GROUND:
    for (path, cx0, cx1, cz0, cz1, cy0, cy1) in COLS:
        if any(path.startswith(r) for r in SHOP_COLLIDER_ROOTS[shop]) or cy1 < 0.05:
            continue
        if path.startswith("Ward district retrofit/Shop retrofits/COL_") and path.endswith("_bin"):
            continue        # renderer retired by the street-dressing pass: invisible proxies along the side walls
        if x0 < cx1 and cx0 < x1 and z0 < cz1 and cz0 < z1:
            PROBLEMS.append(f"{name}: overlaps collider {path}")
    c_ = ((x0 + x1) / 2, (z0 + z1) / 2)
    for rname, pts in ROUTES.items():
        for i in range(len(pts)):
            d_ = seg_dist(c_, pts[i], pts[(i + 1) % len(pts)])
            lim = (1.6 if "droid" in rname.lower() else 1.0) + max(x1 - x0, z1 - z0) / 2
            if d_ < lim:
                PROBLEMS.append(f"{name}: {d_:.2f} m from {rname}")
    for (pname, px, pz, r) in POINTS:
        if math.hypot(c_[0] - px, c_[1] - pz) < r + max(x1 - x0, z1 - z0) / 2:
            PROBLEMS.append(f"{name}: on {pname}")


# ====================================================================== skyline check
VIEW = [(x, 1.6, z) for x in (-13.5, -11.0, 11.0, 13.5) for z in range(-26, 27, 4)] + [(-12.4, 1.62, 1.1), (12.0, 1.6, 0.0), (-3.5, 1.65, -12.0)]
OCC = []
for shop, s in SHOPS.items():
    top = s["coping"] if s["coping"] else s["gable"]["eave"]
    lo = to_world(shop, (-HW - 0.1, 0, -D - 0.1))[0]; hi = to_world(shop, (HW + 0.1, 0, 0.12))[0]
    OCC.append((min(lo[0], hi[0]), max(lo[0], hi[0]), 0.0, top, min(lo[2], hi[2]), max(lo[2], hi[2])))
    if s.get("gable"):  # ridge as a thin wall under the ridge line
        lo = to_world(shop, (-0.8, 0, -D - 0.5))[0]; hi = to_world(shop, (0.8, 0, 0.5))[0]
        OCC.append((min(lo[0], hi[0]), max(lo[0], hi[0]), 0.0, s["gable"]["ridge"] - 0.4, min(lo[2], hi[2]), max(lo[2], hi[2])))
OCC.append((-15.5, -4.5, 0.0, 13.0, -36.5, -26.0))              # Vanguard Hall (approx.)


def blocked(p, q, skip=None):
    d = [q[i] - p[i] for i in range(3)]
    for k, (x0, x1, y0, y1, z0, z1) in enumerate(OCC):
        if k == skip:
            continue
        t0, t1 = 0.0, 0.999
        ok = True
        for (o, dd, lo, hi) in ((p[0], d[0], x0, x1), (p[1], d[1], y0, y1), (p[2], d[2], z0, z1)):
            if abs(dd) < 1e-9:
                if o < lo or o > hi:
                    ok = False; break
            else:
                a, b = (lo - o) / dd, (hi - o) / dd
                if a > b:
                    a, b = b, a
                t0, t1 = max(t0, a), min(t1, b)
                if t0 > t1:
                    ok = False; break
        if ok:
            return True
    return False


for shop, items in GROUPS.items():
    for it in items:
        if it["on"] == "wall" or it["sd"]:
            continue
        p, _ = world_of(shop, it)
        fp = footprint(it)
        h = fp[5] - (SHOPS[shop]["coping"] or SHOPS[shop]["gable"]["ridge"])
        best, views = 0.0, 0
        for v in VIEW:
            vis = 0.0
            for k in range(12):
                y = fp[5] - k * 0.15
                if y < fp[4]:
                    break
                if not blocked(v, (p[0], y, p[2])):
                    vis = fp[5] - y + 0.15
                else:
                    break
            if vis >= 0.3:
                views += 1
            best = max(best, vis)
        ITEMS_REPORT.append({"shop": shop, "id": it["id"], "world": p, "top": round(fp[5], 2), "above_roofline": round(h, 2),
                             "max_visible_m": round(min(best, fp[5] - fp[4]), 2), "street_views_showing_0.3m": views, "of": len(VIEW)})


# ====================================================================== output
def out_items(shop):
    s = SHOPS[shop]
    res = []
    for it in GROUPS[shop]:
        w, wyaw = world_of(shop, it)
        res.append({"id": it["id"], "sd": it["sd"], "local": it["pos"], "localYaw": it["yaw"], "world": w, "worldYaw": round(wyaw, 3),
                    "note": it["note"], "on": it["on"]})
    return res


layout = {
    "date": "2026-10-01", "source": "art/rooftops_20261001/layout.py", "audit": str(AUDIT_PATH.relative_to(ROOT)),
    "groups": [{"name": f"{SHOPS[s]['name']} roof", "shop": s, "root": [SHOPS[s]["root"][0], 0.0, SHOPS[s]["root"][1]],
                "yaw": SHOPS[s]["yaw"], "items": out_items(s)} for s in SHOPS if s in GROUPS],
    "cables": CABLES,
}
(HERE / "layout.json").write_text(json.dumps(layout, indent=1))
report = {"problems": PROBLEMS, "notes": NOTES, "skyline": ITEMS_REPORT,
          "counts": {"items": sum(len(v) for v in GROUPS.values()), "spans": sum(1 for c in CABLES if c["kind"] == "span"),
                     "conduits": sum(1 for c in CABLES if c["kind"] == "conduit")}}
(HERE / "review").mkdir(exist_ok=True)
(HERE / "review/layout-report.json").write_text(json.dumps(report, indent=1))
for s in ITEMS_REPORT:
    print(f"  {s['shop']:14s} {s['id']:18s} top {s['top']:6.2f}  +{s['above_roofline']:5.2f} over roof  visible {s['max_visible_m']:4.2f} m, {s['street_views_showing_0.3m']:2d}/{s['of']} views")
print(json.dumps(report["counts"]))
for n in NOTES:
    print("note:", n)
for p in PROBLEMS:
    print("PROBLEM:", p)
print(f"{len(PROBLEMS)} problems")

if "--plot" in sys.argv:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(14, 12))
    for (shop, x0, x1, z0, z1, top) in BODIES:
        ax.add_patch(plt.Rectangle((x0, z0), x1 - x0, z1 - z0, fc="#d8cbb4", ec="#8a7a60"))
        ax.text((x0 + x1) / 2, (z0 + z1) / 2, SHOPS[shop]["name"], ha="center", va="center", fontsize=8, color="#5a4a30")
    for shop, items in GROUPS.items():
        for it in items:
            fp = footprint(it)
            corners = [to_world(shop, (x, 0, z))[0] for x, z in ((fp[0], fp[2]), (fp[1], fp[2]), (fp[1], fp[3]), (fp[0], fp[3]))]
            xs = [c_[0] for c_ in corners] + [corners[0][0]]; zs = [c_[2] for c_ in corners] + [corners[0][2]]
            ax.plot(xs, zs, color="#1f5f8b" if not it["sd"] else "#8b5a1f", lw=1)
            w = world_of(shop, it)[0]
            ax.text(w[0], w[2], it["id"], fontsize=6, color="#103050")
    for c in CABLES:
        pts = span_pts(c) if c["kind"] == "span" else c["points"]
        ax.plot([p[0] for p in pts], [p[2] for p in pts], color="#202020" if c["kind"] == "span" else "#a03020", lw=0.8)
    for (sp, note) in SMOKES:
        ax.add_patch(plt.Circle((sp[0], sp[2]), SMOKE_CLEAR, fc="none", ec="#c03030", ls="--"))
    for rname, pts in ROUTES.items():
        ax.plot([p[0] for p in pts + pts[:1]], [p[1] for p in pts + pts[:1]], color="#30a030", lw=0.6, alpha=0.6)
    ax.set_aspect("equal"); ax.set_xlim(-30, 30); ax.set_ylim(-30, 30); ax.grid(alpha=0.3)
    ax.set_title("Ward rooftops layout (world x/z; red dashed = smoke clearance, black = spans, red = conduits)")
    fig.savefig(HERE / "review/layout-map.png", dpi=110, bbox_inches="tight")

sys.exit(1 if PROBLEMS else 0)
