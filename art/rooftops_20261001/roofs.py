"""Ward rooftops (1 Oct 2026): roof data of the rebuilt shops, read from their source records. Plain Python (no Blender).

Every shop is authored in its own frame (art/hall_district_20260930/author_ward_shops.py and
art/north_avenue_20260930/author_north_shops.py): origin = facade centre at paving level, +Z towards the avenue,
footprint x -3.8..3.8, z -6.9..0. The west row is rotated yaw +90 (local +Z = world +X), the east row yaw -90.
Placements in layout.json are given in this shop frame and converted with to_world().

Roof deck heights, copings and existing roof furniture below are taken from those scripts (shop.top(), roof_y,
roof_hatch_and_ac, mast, water_tank, roof_shed, container, drying_lines, flue) and checked against the shop records
(Art/WardShops/Models/<shop>.json: "top", mounts) and the scene audit (roof air conditioners at their world positions).
"""
import json, math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SHOP_MODELS = ROOT / "unity/AthenHill/Assets/AthenHill/Art/WardShops/Models"

HW, D = 3.8, 6.9
PARAPET_IN = 0.46          # coping overhangs the inner parapet face by 0.46 m (cop profile -0.46..0.08)


def box(x0, x1, z0, z1, y1, note):
    return {"x": [x0, x1], "z": [z0, z1], "top": y1, "note": note}


def hatch(x, z, r):
    """roof_hatch_and_ac: 0.9 m hatch at (x, z) and the Poly Haven aircon at (x + 1.4, z - 0.6)."""
    return [box(x - 0.5, x + 0.5, z - 0.5, z + 0.5, r + 0.4, "roof hatch"),
            box(x + 1.4 - 0.45, x + 1.4 + 0.45, z - 0.6 - 0.25, z - 0.6 + 0.25, r + 0.95, "roof air conditioner")]


def mast(x, z, r, h=3.4):
    """mast(): pipe + crossbars + dish, guy wires to (x+-1.6, z+1.4) and (x, z-1.8) (anchors 0.16 m plates)."""
    out = [box(x - 0.45, x + 0.45, z - 0.35, z + 0.65, r + h + 1.2, "shop comms mast and dish")]
    for dx, dz in ((1.6, 1.4), (-1.6, 1.4), (0.0, -1.8)):
        out.append({"guy": [[x, r + h * 0.8, z], [x + dx, r + 0.05, z + dz]], "note": "mast guy wire"})
    return out


# key: root (world x, z), yaw, deck (roof_y), coping top, existing obstacles (local), notes
SHOPS = {
    "relay_works": dict(name="Relay Works", root=(-18.1, -18.0), yaw=90, deck=8.0, coping=8.76,
                        obstacles=hatch(-1.8, -4.8, 8.0) + mast(1.9, -3.4, 8.0)),
    "air_water": dict(name="Air + Water", root=(-18.1, -9.0), yaw=90, deck=8.0, coping=8.76,
                      obstacles=hatch(1.6, -5.4, 8.0) + [box(-2.3, -0.5, -4.8, -3.0, 8.0 + 0.78 + 1.5 + 0.83, "roof water tank (teal)"),
                                                          box(-0.55, 0.0, -4.0, -2.6, 8.4, "tank outlet pipe")]),
    "tool_exchange": dict(name="Tool Exchange", root=(-18.1, 9.0), yaw=90, deck=6.32, coping=7.01,
                          obstacles=hatch(1.2, -4.6, 6.32) + mast(-2.2, -2.8, 6.32, h=2.0)),
    "salvage": dict(name="Salvage", root=(-18.1, 18.0), yaw=90, deck=8.0, coping=8.73,
                    obstacles=hatch(1.7, -5.0, 8.0) + [box(-3.2, -0.5, -3.55, -0.85, 10.2, "corrugated roof shed")],
                    smoke=[(-2.65, -2.2, 11.24, "Salvage stovepipe smoke (Ward night life)")]),
    "finery": dict(name="Finery", root=(18.1, -18.0), yaw=-90, deck=8.42, coping=9.19,
                   obstacles=hatch(-1.6, -4.9, 8.42)),
    "field_supply": dict(name="Field Supply", root=(18.1, -9.0), yaw=-90, deck=None, coping=None,
                         gable=dict(eave=5.24, ridge=8.16, over=0.45, slope_deg=math.degrees(math.atan2(8.1 - 5.24, 3.8))),
                         obstacles=[box(-0.2, 0.2, -7.4, 0.5, 8.3, "ridge cap")]),
    "repairs": dict(name="Repairs", root=(18.1, 9.0), yaw=-90, deck=6.74, coping=7.43,
                    obstacles=hatch(1.2, -5.0, 6.74) + [box(-2.4, 1.6, -3.45, -1.25, 8.86, "rooftop container workshop")],
                    smoke=[(-4.08, -1.75, 8.65, "Repairs forge flue smoke (Ward night life)")]),
    "thread_hide": dict(name="Thread + Hide", root=(18.1, 18.0), yaw=-90, deck=8.0, coping=8.76,
                        obstacles=hatch(1.9, -5.6, 8.0) + [box(-2.75, 1.75, -2.25, -1.15, 10.05, "drying lines and cloth")]),
}

# world-space smoke columns from the Ward night life pass (art/night_life_20261001/night-layout.json): keep 1.8 m clear
SMOKE_CLEAR = 1.8


def to_world(key, p, yaw=0.0):
    """Shop-local (x, y, z) -> world (x, y, z); local yaw (deg) -> world yaw."""
    s = SHOPS[key]
    rx, rz = s["root"]
    a = math.radians(s["yaw"])
    x, y, z = p
    wx = rx + x * math.cos(a) + z * math.sin(a)
    wz = rz - x * math.sin(a) + z * math.cos(a)
    return [round(wx, 4), round(y, 4), round(wz, 4)], (yaw + s["yaw"]) % 360


def to_local(key, w):
    s = SHOPS[key]
    rx, rz = s["root"]
    a = math.radians(s["yaw"])
    dx, dz = w[0] - rx, w[2] - rz
    return [dx * math.cos(a) - dz * math.sin(a), w[1], dx * math.sin(a) + dz * math.cos(a)]


def deck_bounds():
    """Usable deck inside the parapet copings (local)."""
    return (-HW + PARAPET_IN, HW - PARAPET_IN), (-D + PARAPET_IN, -PARAPET_IN)


def gable_y(key, x):
    """Top of the corrugated roof at local x (Field Supply)."""
    g = SHOPS[key]["gable"]
    t = math.tan(math.radians(g["slope_deg"]))
    return g["ridge"] + 0.072 - abs(x) * t


def faces(key):
    """Facade openings, lamps and fittings of a shop (local), for keeping wall drops and ladders clear."""
    rec = json.loads((SHOP_MODELS / f"{key}.json").read_text())
    return rec


if __name__ == "__main__":
    for k, s in SHOPS.items():
        print(k, s["name"], s["root"], s["yaw"], s["deck"], s["coping"], len(s["obstacles"]))
    print(to_world("air_water", (3.0, 8.0, -6.0)), "expect (-24.1, 8, -12.0)")
    print(to_world("finery", (-0.2, 8.42, -5.5)), "expect (23.6, 8.42, -18.2)")
