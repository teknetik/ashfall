#!/usr/bin/env python3
"""Ward street dressing layout (30 Sep 2026): plain Python, no Blender. Writes layout.json for
Unity (Editor/StreetDressingInstall.cs) and review/layout-map.png.

Carl: "I want the area to have a lived in look but not be too messy. I dont want a clean clinical ward. eventually we
will introduce more NPC to make it look busy". So the dressing is organised as vignettes that explain what people do
there, set against walls, on porch ends, in the rear service lanes and on yard edges:
  shop frontages (stock by the door, planters, a stool or bench), refuse points (communal bin and tied sacks), water
  points, a workshop yard (generator, fuel, tarp-covered stock), a salvage skip, a market rest spot, hill benches, and
  a little windblown litter where it collects (wall feet, corners, near bins), never across the walking lines.
Kept clear: the avenue lanes round the hill (props stay on porches or against walls), every door and shutter bay (front,
rear, side), the stair approaches, walker/mechanic/droid routes (1 m), NPC stand points, the Lattice and Ring interaction
areas. Seats carry "NPC sit point" markers in their prefabs for the later crowd pass.

Coordinates: Unity world metres (x east, z north, y up); yaw is Unity's (0 faces +Z, 90 faces +X); props face +Z.
Surface heights come from the saved colliders (street 0, porch decks 0.5, steps 0.25), read from the scene audit.
Run: uv run --with matplotlib python layout.py   (needs unity/evidence/street-dressing/20260930/audit.json)
"""
import json, math, random, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
AUDIT = ROOT / "unity/evidence/street-dressing/20260930/audit.json"
PROPS = ROOT / "unity/AthenHill/Assets/AthenHill/Art/StreetDressing/Props"
SHOPS = ROOT / "unity/AthenHill/Assets/AthenHill/Art/WardShops/Models"

SIZE = {}
for f in ("ph-props.json", "meshy-props.json", "authored-props.json"):
    for k, v in json.loads((PROPS / f).read_text()).items():
        SIZE[k] = v["size"]            # Unity axes: x width, y height, z depth (front along +Z)

A = json.loads(AUDIT.read_text())

# ------------------------------------------------------------------ what is retired (their colliders are ignored here)
RETIRE_PREFIXES = ["Post-war salvage/trash scatter", "Post-war salvage/crate scatter", "Post-war salvage/crate original",
                   "Post-war salvage/scrap scatter", "Post-war salvage/generator scatter",
                   "AuthoredWorld/AAA Environment Dressing/Street cargo crate", "AuthoredWorld/AAA Environment Dressing/Street bollard",
                   "AuthoredWorld/AAA Environment Dressing/Plaza bench"]
# retrofit collider proxies left visible as grey slabs (renderer off, collision kept)
HIDE_RENDERERS = ["Ward district retrofit/Shop retrofits/COL_air_water_n_bin", "Ward district retrofit/Shop retrofits/COL_field_supply_n_bin",
                  "Ward district retrofit/Shop retrofits/COL_repairs_s_bin", "Ward district retrofit/Shop retrofits/COL_tool_exchange_s_bin"]

COLS = []
for c in A["colliders"]:
    if any(c["path"].startswith(p) for p in RETIRE_PREFIXES):
        continue
    (x, y, z), (sx, sy, sz) = c["center"], c["size"]
    if sx > 60 or sz > 60:
        continue
    COLS.append((c["path"], x - sx / 2, x + sx / 2, z - sz / 2, z + sz / 2, y - sy / 2, y + sy / 2))


def surface_y(x, z):
    """Top of the highest walkable collider under (x, z): street 0, steps 0.25, porch decks 0.5."""
    best = 0.0
    for (_, x0, x1, z0, z1, y0, y1) in COLS:
        if x0 <= x <= x1 and z0 <= z <= z1 and y1 <= 0.62 and y1 > best:
            best = y1
    return round(best, 3)


# ------------------------------------------------------------------ keep-clear zones
def shop_openings():
    """Front, rear and side openings of the rebuilt shops as world rectangles (1.3 m deep, 0.3 m margin)."""
    shops = {"relay_works": (-18.1, -18, 90), "air_water": (-18.1, -9, 90), "tool_exchange": (-18.1, 9, 90), "salvage": (-18.1, 18, 90),
             "finery": (18.1, -18, -90), "field_supply": (18.1, -9, -90), "repairs": (18.1, 9, -90), "thread_hide": (18.1, 18, -90)}
    rects = []
    for s, (rx, rz, yaw) in shops.items():
        d = json.loads((SHOPS / f"{s}.json").read_text())
        sgn = 1 if yaw == 90 else -1          # front faces +x for the west row, -x for the east row
        for r in d.get("recesses", []):
            u0, u1 = r["u"]
            if r["face"] in ("front", "rear"):
                # local x -> world z (west row: z = rz - u; east row: z = rz + u)
                za, zb = sorted([rz - sgn * u0, rz - sgn * u1])
                face_x = rx + sgn * 0.09 if r["face"] == "front" else rx - sgn * 6.95
                out = sgn if r["face"] == "front" else -sgn
                xa, xb = sorted([face_x, face_x + out * 1.3])
                rects.append((f"{s} {r['face']} opening", xa, xb, za - 0.3, zb + 0.3))
            elif r["face"] in ("left", "right"):
                # side faces: u runs along the depth (local z), the face is at local x = -+3.89
                side = -1 if r["face"] == "left" else 1
                fz = rz + (side * 3.89 if yaw == -90 else -side * 3.89)
                xa, xb = sorted([rx - sgn * u0, rx - sgn * u1])
                out = -1 if fz < rz else 1
                za, zb = sorted([fz, fz + out * 1.3])
                rects.append((f"{s} {r['face']} door", xa - 0.3, xb + 0.3, za, zb))
    # the rebuilt Basic General booth: the counter front (customers) and Mira's side access
    rects.append(("basic general counter", 5.4, 10.6, 12.2, 14.0))
    # hill stair approaches (stairs on -Z "north", +Z "south" and +X "west"), 2.5 m beyond the bottom nosing
    rects += [("hill stair -Z", -2.6, 2.6, -13.2, -7.0), ("hill stair +Z", -2.6, 2.6, 7.0, 13.2), ("hill stair +X", 7.0, 13.2, -2.6, 2.6)]
    # mission terminals' standing area and the Vanguard Hall steps
    rects += [("terminal slab", 4.6, 11.4, -13.4, -10.6), ("hall steps", -16.5, -3.6, -23.6, -21.2)]
    return rects


CLEAR = shop_openings()
ROUTES = []
POINTS = []
for m in A["markers"]:
    p = m["path"]
    parts = p.split("/")
    if len(parts) == 2 and (parts[0].endswith(" route") or parts[0] == "Mining droid route"):
        ROUTES.append((parts[0], m["pos"][0], m["pos"][2]))
    elif len(parts) == 2 and parts[0] == "Colonists":
        POINTS.append((parts[1], m["pos"][0], m["pos"][2], 1.3))
    elif len(parts) == 2 and parts[0] == "Landmarks":
        POINTS.append((parts[1], m["pos"][0], m["pos"][2], 1.2))
    elif len(parts) == 1 and parts[0] in ("Lattice interaction", "Ring interaction"):
        POINTS.append((parts[0], m["pos"][0], m["pos"][2], 3.0))
SEGS = []
by = {}
for name, x, z in ROUTES:
    by.setdefault(name, []).append((x, z))
for name, pts in by.items():
    for i in range(len(pts)):
        SEGS.append((name, pts[i], pts[(i + 1) % len(pts)], 1.0 if "droid" not in name.lower() else 1.6))

# ------------------------------------------------------------------ placements
PL = []


def P(vig, prop, x, z, yaw=0.0, y=None, on=None, pitch=0.0, roll=0.0, scale=1.0, note=""):
    """Place prop at (x, z) with its base on the surface (or on top of placement `on`). Scale is uniform only."""
    if prop not in SIZE:
        raise SystemExit(f"unknown prop {prop}")
    if on is not None:
        base = PL[on]
        y = base["pos"][1] + SIZE[base["prop"]][1] * base["scale"] - 0.004
    elif y is None:
        y = surface_y(x, z)
    PL.append({"vignette": vig, "prop": prop, "pos": [round(x, 3), round(y, 3), round(z, 3)], "euler": [pitch, yaw, roll],
               "scale": scale, "on": on, "note": note})
    return len(PL) - 1


def dims(p):
    return [v * p["scale"] for v in SIZE[p["prop"]]]


WX, EX = -18.01, 18.01          # shop front faces (west row faces +x, east row faces -x)


def xdepth(prop, yaw, scale=1.0):
    """Extent along world x of a prop turned by `yaw` (its footprint's projection)."""
    sx, _, sz = [v * scale for v in SIZE[prop]]
    a = math.radians(yaw)
    return abs(sx * math.cos(a)) + abs(sz * math.sin(a))


def west(prop, yaw, scale=1.0):  # x of a prop centre standing against a west-row front (faces +x)
    return WX + xdepth(prop, yaw, scale) / 2 + 0.04


def east(prop, yaw, scale=1.0):
    return EX - xdepth(prop, yaw, scale) / 2 - 0.04


rng = random.Random(20260930)
j = lambda a: rng.uniform(-a, a)          # small hand-placed jitter

# ---- shop frontages (porch decks, y 0.5) -----------------------------------------------------------------------------
v = "Relay Works frontage: parts stock"
c = P(v, "crate_long", west("crate_long", 90), -21.25, 90 + j(1))
P(v, "tote_blue", west("crate_long", 90), -21.4, 93, on=c)
y1 = P(v, "crate_yellow", -16.95, -21.5, 88 + j(3))
P(v, "carton", -16.95, -21.48, 178 + j(4), on=y1)
P("Relay Works frontage: door pot", "pot_clay_planted", west("pot_clay_planted", 0, 1.7), -14.6, j(30), scale=1.7)

v = "Air + Water frontage: water point"
P(v, "water_point", west("water_point", 90), -12.22, 90)
P(v, "bucket_wood", -16.72, -12.3, j(40))
P(v, "churn", -17.25, -12.7, j(40))
P(v, "drum_blue", -16.95, -7.4, j(30), note="stored water beside the filter bank")
P(v, "churn", -16.55, -6.55, j(40))

v = "Tool Exchange frontage: trolley"
t = P(v, "tool_cart", west("tool_cart", 90), 5.82, 90)
P(v, "toolbox", west("tool_cart", 90), 5.72, 93, on=t)
P(v, "gas_bottle", -16.62, 5.45, j(40))
P("Tool Exchange frontage: display stool", "stool_metal", -15.35, 11.9, 100)

v = "Salvage frontage: wheels"
P(v, "tyre", west("tyre", 90), 14.58, 90)
P(v, "rim_a", west("tyre", 90) + 0.17, 14.6, 88)
P(v, "jerrycan_red", -16.85, 14.45, 75)

v = "Finery frontage: door planters and bench"
P(v, "pot_clay_planted_grass", east("pot_clay_planted_grass", 0, 1.5), -19.45, j(40), scale=1.5)
P(v, "pot_clay_planted", east("pot_clay_planted", 0, 1.7), -16.6, j(40), scale=1.7)
P(v, "bench_painted", east("bench_painted", -90), -21.1, -90)

v = "Field Supply frontage: stock"
c = P(v, "crate_wood_deep", east("crate_wood_deep", -90), -12.25, -90 + j(1))
P(v, "carton", east("crate_wood_deep", -90), -12.4, -84, on=c)
y1 = P(v, "crate_yellow", 16.95, -12.45, -86 + j(3))
P(v, "crate_yellow", 16.95, -12.43, -94, on=y1)
P(v, "jerrycan_green", east("jerrycan_green", -90), -5.8, -90)
P(v, "jerrycan_green", east("jerrycan_green", -82), -5.38, -82)

v = "Repairs frontage: tea break"
tb = P(v, "crate_wood", east("crate_wood", 90), 12.44, 90)
P(v, "pot_enamel", east("crate_wood", 90), 12.5, 30, on=tb)
P(v, "stool_wood", 16.85, 12.35, -115)
P(v, "churn", 16.2, 12.62, j(40))
P("Repairs frontage: broom", "broom", EX - 0.36, 5.4, -90, pitch=-12, note="leaning on the pier beside the bay")

v = "Thread + Hide frontage: sewing stool"
P(v, "stool_painted", 17.15, 21.2, -110)
P(v, "basket_flat", east("basket_flat", -90), 21.5, -90)
P(v, "basket_lidded", 16.55, 21.6, -60)
P(v, "pot_clay_planted", east("pot_clay_planted", 0, 1.7), 17.95, j(40), scale=1.7)

# ---- Basic General ---------------------------------------------------------------------------------------------------
v = "Basic General: stock by the east cheek"
c = P(v, "crate_long", 11.2, 16.2, 90 + j(2))
P(v, "tote_blue", 11.2, 16.0, 88, on=c)
P(v, "sack_tied_c", 11.25, 17.35, j(30), note="grain sack waiting to go in")
P(v, "hand_truck", 11.35, 14.85, 90 + j(4))
v = "Basic General: refuse point"
P(v, "refuse_bin", 4.52, 16.6, -90)
P(v, "sack_tied_a", 4.42, 17.75, j(40))
P(v, "sack_tied_b", 4.9, 18.25, j(40))
P(v, "card_flat_a", 3.7, 15.55, 0)
P(v, "paper_ball", 3.95, 17.1, 0)

# ---- hill-foot benches (seats for the crowd pass) and the old plaza bench spot ------------------------------------------
v = "Hill foot benches"
P(v, "bench_painted", -7.37, -2.6, -90)
P(v, "bench_painted", -7.37, 2.8, -90)
P("Plaza bench (replaces the cube bench)", "bench_painted", 11.5, 5.7, 180)

# ---- rear service lanes ----------------------------------------------------------------------------------------------
v = "Salvage yard: scrap skip"
P(v, "scrap_skip", -27.25, 20.95, 90)
P(v, "tyre", -26.3, 22.55, 20)
P(v, "rim_b", -26.45, 22.95, 35)
P(v, "hand_truck", -25.9, 20.3, -90)
P(v, "tin_a", -26.9, 19.6, 0)

v = "Tool Exchange yard: stock"
c = P(v, "crate_wood_deep", -26.15, 11.6, 90 + j(3))
y1 = P(v, "crate_yellow", -26.95, 12.4, 12 + j(4))
P(v, "crate_red", -26.95, 12.4, 8, on=y1)
P(v, "drum_steel_blue", -26.2, 10.15, j(40))
P(v, "drum_steel_blue", -26.9, 9.85, j(40))

v = "Air + Water yard: water drums"
P(v, "drum_blue", -26.0, -11.25, j(40))
P(v, "drum_blue", -26.55, -11.75, j(40))
P(v, "drum_blue", -25.95, -11.9, j(40))
P(v, "bucket_wood", -26.7, -10.9, j(40))

v = "Relay Works yard: deliveries"
c = P(v, "carton", -25.95, -15.4, 90 + j(4))
P(v, "carton", -25.95, -15.38, 95, on=c)
P(v, "tote_blue", -26.1, -16.15, 90)
P(v, "card_flat_b", -26.6, -14.6, 0)

v = "Repairs yard: forge gas and rack"
P(v, "rack", 25.92, 12.25, 90)
P(v, "gas_bottle", 25.55, 8.55, j(40))
P(v, "gas_bottle", 25.95, 8.1, j(40))
P(v, "field_generator", 26.35, 14.65, 0)
P(v, "oil_tin", 25.7, 7.5, j(40))

v = "Field Supply yard: sacks and crates"
c = P(v, "ammo_crate_a", 25.95, -13.6, 90 + j(2))
P(v, "ammo_crate_a", 25.95, -13.55, 92, on=c)
P(v, "sack_tied_c", 26.55, -12.35, j(40))
P(v, "sack_tied_b", 26.05, -8.9, j(40))

v = "Finery yard: refuse point"
P(v, "bin_galv", 25.75, -21.3, 90)
P(v, "bin_galv_rust", 25.8, -20.3, 75)
P(v, "sack_tied_a", 26.45, -20.8, j(40))
P(v, "paper_d", 26.3, -19.4, 0)

# ---- east yard (by the mechanic) and the West Gate approach ------------------------------------------------------------
v = "East yard: generator and fuel"
P(v, "field_generator", 30.3, -14.9, 5)
P(v, "jerrycan_red", 31.3, -15.4, 12)
P(v, "jerrycan_red", 31.6, -15.05, -18)
P(v, "toolbox", 29.35, -15.65, 30)
P(v, "tarp_stack", 30.95, -11.9, 15)
P(v, "drum_red", 29.3, -12.95, j(40))
P(v, "drum_red", 29.3, -12.35, j(40))
P(v, "handcart", 31.8, -9.55, 100)

v = "West Gate approach: caravan goods waiting"
P(v, "handcart", 38.9, 7.3, -20)
c = P(v, "crate_wood_deep", 37.6, 8.5, 10)
P(v, "sack_tied_c", 37.55, 8.5, 20, on=c)
P(v, "crate_long", 36.9, 9.55, 5)

# ---- market edge rest spot ----------------------------------------------------------------------------------------------
v = "Market edge: rest spot"
P(v, "picnic_table", -29.9, -7.5, 90)
P(v, "stool_folding", -31.9, -6.3, 60)
P(v, "pot_enamel", -29.3, -7.2, 20, y=0.746)
P(v, "fire_barrel", -32.2, -9.2, j(40))
P(v, "paper_c", -31.6, -9.9, 0)

# ---- hydroponics door: planters and a watering can ----------------------------------------------------------------------
v = "Hydroponics door: planters"
P(v, "planter_long_planted", -26.0, 27.9, 90)
P(v, "planter_short_planted", -26.0, 29.75, 90)
P(v, "watering_can", -25.55, 28.95, 150)

# ---- south: Vanguard Hall refuse point -----------------------------------------------------------------------------------
v = "Vanguard Hall: refuse point"
P(v, "refuse_bin", -3.3, -28.5, 90)
P(v, "sack_tied_a", -3.2, -27.25, j(40))
P(v, "sack_tied_b", -3.05, -29.85, j(40))
P(v, "card_flat_b", -2.4, -27.9, 0)


# ---- second layer: more everyday use at the frontages, the hill stair feet cared for --------------------------------------
P("Air + Water frontage: water point", "tub_wood", -16.95, -5.62, j(40), note="washing tub by the filter bank")
v = "Tool Exchange frontage: display stool"
c = P(v, "crate_red", west("crate_red", 90), 12.45, 90)
P(v, "oil_tin", west("crate_red", 90), 12.4, 20, on=c)
P("Field Supply frontage: stock", "sack_tied_c", 16.25, -12.3, j(40), note="grain")
P("Field Supply frontage: stock", "sack_tied_c", 16.3, -11.75, j(40), note="grain")
v = "Repairs frontage: cart under repair"
P(v, "handcart", 15.5, 7.2, 3)
P(v, "toolbox", 15.25, 5.75, 25)
P(v, "rim_b", 16.3, 6.4, -70, note="a wheel off the cart")
P("Thread + Hide frontage: sewing stool", "pot_clay_planted_grass", east("pot_clay_planted_grass", 0, 1.5), 14.6, j(40), scale=1.5)
P("Basic General: stock by the east cheek", "stool_folding", 11.55, 12.9, -130, note="someone waits for Mira")
v = "Hill stair feet: planted pots"
for (px, pz, grass) in [(-3.1, -10.3, False), (3.15, -10.3, True), (-3.15, 10.3, True), (3.1, 10.3, False),
                        (10.3, -3.1, False), (10.3, 3.15, True)]:
    pid = "pot_clay_planted_grass" if grass else "pot_clay_planted"
    P(v, pid, px, pz, rng.uniform(0, 360), scale=1.6 if not grass else 1.45)

# ---- loose litter where wind and feet leave it (wall feet, corners, lanes) ------------------------------------------------
v = "Windblown litter"
for pid, x, z in [("paper_a", -14.6, -4.45), ("tin_b", -25.4, -2.8), ("paper_b", -25.45, 3.2), ("rag", -26.2, -4.2),
                  ("paper_d", 25.4, 3.3), ("tin_a", 25.35, -4.6), ("paper_c", -7.4, -6.3), ("paper_ball", -7.35, 6.3),
                  ("paper_a", 7.35, 6.5), ("tin_b", 13.9, -13.9), ("paper_b", -13.85, 13.95), ("card_flat_a", -25.6, -20.4),
                  ("paper_c", 25.5, 16.3), ("tin_a", 34.0, 6.2), ("paper_d", -29.2, 19.4), ("paper_ball", 29.4, -8.9),
                  ("rag", 36.6, 5.7),
                  # porch-step corners, where the wind drops what it carries
                  ("paper_b", -14.2, -15.65), ("tin_a", 14.25, -6.7), ("paper_ball", -14.25, 11.35), ("paper_d", 14.2, 20.45),
                  ("paper_ball", -14.2, 20.5), ("paper_a", 14.2, -20.45), ("tin_b", -14.25, -6.65), ("paper_c", 11.6, 6.4),
                  ("paper_ball", -6.9, -7.6), ("tin_a", 7.6, 7.6)]:
    P(v, pid, x, z, rng.uniform(0, 360))


# ------------------------------------------------------------------ validation
ROUND = ("drum", "bin_galv", "gas_bottle", "churn", "bucket", "tub", "pot_clay", "sack", "fire_barrel", "pot_enamel", "oil_tin")
is_round = lambda prop: prop.startswith(ROUND)


def footprint(p):
    sx, sy, sz = dims(p)
    x, y, z = p["pos"]
    yaw = math.radians(p["euler"][1]) if not is_round(p["prop"]) else 0.0
    pitch = abs(p["euler"][0])
    sz_eff = sz + sy * math.sin(math.radians(pitch))       # a leaning prop sweeps further out
    pts = []
    for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        lx, lz = a * sx / 2, b * sz_eff / 2
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


problems = []
for i, p in enumerate(PL):
    pts = footprint(p)
    x0, x1, z0, z1 = aabb(pts, 0.03)
    sx, sy, sz = dims(p)
    y = p["pos"][1]
    top = y + sy
    litter = sy < 0.13
    # the surface must be level under the footprint (no hanging off a porch edge or step)
    if p["on"] is None and p["pos"][1] != 0.746:
        ys = {surface_y(qx, qz) for qx, qz in pts + [(p["pos"][0], p["pos"][2])]}
        if max(ys) - min(ys) > 0.02:
            problems.append((i, "uneven surface " + str(sorted(ys))))
    for (name, cx0, cx1, cz0, cz1, cy0, cy1) in COLS:
        if cx1 < x0 or cx0 > x1 or cz1 < z0 or cz0 > z1:
            continue
        if cy1 <= y + 0.03 or cy0 >= top:
            continue
        problems.append((i, "collider " + name))
    for (name, rx0, rx1, rz0, rz1) in CLEAR:
        if not (rx1 < x0 or rx0 > x1 or rz1 < z0 or rz0 > z1):
            problems.append((i, "keep-clear " + name))
    r = max(sx, sz) / 2
    for (name, a, b, margin) in SEGS:
        if seg_dist(p["pos"][0], p["pos"][2], a, b) < margin + r * 0.7:
            problems.append((i, "route " + name))
    for (name, px, pz, rad) in POINTS:
        if math.hypot(p["pos"][0] - px, p["pos"][2] - pz) < rad + r * 0.7:
            problems.append((i, "point " + name))
    for k, q in enumerate(PL):
        if k >= i or q["on"] == i or p["on"] == k or (p["on"] is not None and p["on"] == q["on"]):
            continue
        qx0, qx1, qz0, qz1 = aabb(footprint(q), 0.03)
        if qx1 < x0 or qx0 > x1 or qz1 < z0 or qz0 > z1:
            continue
        if is_round(p["prop"]) and is_round(q["prop"]):
            rp = min(dims(p)[0], dims(p)[2]) / 2
            rq = min(dims(q)[0], dims(q)[2]) / 2
            if math.hypot(p["pos"][0] - q["pos"][0], p["pos"][2] - q["pos"][2]) >= (rp + rq) * 0.97:
                continue
        # stacked items share a footprint by design; others must not intersect in height either
        qy, qtop = q["pos"][1], q["pos"][1] + dims(q)[1]
        if qtop <= y + 0.01 or qy >= top - 0.01:
            continue
        problems.append((i, f"overlaps #{k} {q['prop']}"))

for i, why in problems:
    p = PL[i]
    print(f"#{i:3d} {p['prop']:22s} {p['vignette'][:40]:40s} {p['pos']} {why}")
print(f"{len(PL)} placements, {len({p['vignette'] for p in PL})} vignettes, {len(problems)} problems")

# ------------------------------------------------------------------ ground decals (the district's weathering atlas)
# one decal per tight cluster of props (single linkage, 0.8 m gaps), so no decal bridges a doorway between two groups;
# lone pots, litter and the stair-foot pots get none. Footprint scuffs where people stand (refuse points, rest spots).
SCUFF = ("refuse point", "rest spot", "benches", "tea break", "sewing stool", "display stool", "water point", "waits")
DECALS = []
groups = {}
for idx, p in enumerate(PL):
    groups.setdefault(p["vignette"], []).append(idx)


def gap(a, b):
    ax0, ax1, az0, az1 = aabb(footprint(PL[a]))
    bx0, bx1, bz0, bz1 = aabb(footprint(PL[b]))
    return max(bx0 - ax1, ax0 - bx1, bz0 - az1, az0 - bz1, 0.0)


for vname, ids in groups.items():
    if vname == "Windblown litter" or vname.startswith("Hill stair feet") or vname.startswith("Plaza bench"):
        continue
    ids = [i for i in ids if dims(PL[i])[1] > 0.13]            # litter does not make grime
    clusters = []
    for i in ids:
        hit = [c for c in clusters if any(gap(i, k) < 0.8 for k in c)]
        merged = [i] + [k for c in hit for k in c]
        clusters = [c for c in clusters if c not in hit] + [merged]
    scuffed = False
    for c in sorted(clusters, key=len, reverse=True):
        big = any(max(dims(PL[i])) >= 0.9 for i in c)
        if len(c) < 2 and not big:
            continue
        pts = [q for i in c for q in footprint(PL[i])]
        x0, x1, z0, z1 = aabb(pts)
        cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
        w, l = x1 - x0 + 0.7, z1 - z0 + 0.7
        y = min(PL[i]["pos"][1] for i in c if PL[i]["on"] is None)
        DECALS.append({"vignette": vname, "kind": "grime", "pos": [round(cx, 3), y, round(cz, 3)], "size": [round(w, 2), round(l, 2)],
                       "yaw": round(rng.uniform(-8, 8), 1), "opacity": 0.4})
        if not scuffed and any(k in vname for k in SCUFF):
            scuffed = True
            DECALS.append({"vignette": vname, "kind": "scuffs", "pos": [round(cx + rng.uniform(-.3, .3), 3), y, round(cz + rng.uniform(-.3, .3), 3)],
                           "size": [round(max(w, 1.6) * .8, 2), round(max(l, 1.6) * .8, 2)], "yaw": round(rng.uniform(0, 360), 1), "opacity": 0.32})
print(len(DECALS), "decals")

out = {"source": "art/street_dressing_20260930/layout.py", "date": "2026-09-30", "decals": DECALS,
       "retirePrefixes": RETIRE_PREFIXES, "hideRenderers": HIDE_RENDERERS,
       "placements": [{k: v for k, v in p.items() if k != "on"} | {"stackedOn": p["on"]} for p in PL]}
(HERE / "layout.json").write_text(json.dumps(out, indent=1))

if "--plot" in sys.argv:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Polygon
    fig, ax = plt.subplots(figsize=(26, 20), dpi=80)
    for (name, x0, x1, z0, z1, y0, y1) in COLS:
        if x1 - x0 > 30 or z1 - z0 > 30 or y1 < 0.05:
            continue
        ax.add_patch(Rectangle((x0, z0), x1 - x0, z1 - z0, fc="#999" if y1 > 0.62 else "#e6dcc0", ec="#555", lw=.3, alpha=.6))
    for (name, x0, x1, z0, z1) in CLEAR:
        ax.add_patch(Rectangle((x0, z0), x1 - x0, z1 - z0, fc="none", ec="green", lw=1, ls="--"))
    for (name, a, b, m) in SEGS:
        ax.plot([a[0], b[0]], [a[1], b[1]], color="dodgerblue", lw=2)
    for (name, px, pz, rad) in POINTS:
        ax.plot(px, pz, "b*")
    vigs = sorted({p["vignette"] for p in PL})
    cmap = plt.get_cmap("tab20")
    bad = {i for i, _ in problems}
    for i, p in enumerate(PL):
        col = "red" if i in bad else cmap(vigs.index(p["vignette"]) % 20)
        ax.add_patch(Polygon(footprint(p), closed=True, fc=col, ec="k", lw=.4, alpha=.85))
    for vname in vigs:
        ps = [p for p in PL if p["vignette"] == vname]
        cx = sum(p["pos"][0] for p in ps) / len(ps); cz = sum(p["pos"][2] for p in ps) / len(ps)
        if vname != "Windblown litter":
            ax.text(cx, cz + 1.0, vname.split(":")[0], fontsize=7)
    ax.set_xlim(-50, 46); ax.set_ylim(-40, 40); ax.set_aspect("equal"); ax.grid(True, lw=.3)
    fig.savefig(HERE / "review/layout-map.png", bbox_inches="tight")
