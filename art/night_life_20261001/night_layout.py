#!/usr/bin/env python3
"""Ward night life layout (1 Oct 2026): street-lamp posts, wall brackets, terminal fills and ambient-effect anchors.
Plain Python. Reads the fresh scene audit (unity/evidence/night-life/20261001/audit-before.json, StreetDressingAudit) and
writes night-layout.json for Unity (Editor/NightLifePass.cs) plus review/layout-map.png.

Validation (same rules as art/street_dressing_20260930/layout.py): a post's footprint (0.7 m square incl. the head
overhang projected to the ground) must not touch an active collider, a shop door/shutter/stair/terminal keep-clear zone,
a walker/mechanic/droid route (1.0 m margin, 1.6 m for the droid), an NPC stand point or landmark (1.3 m) or the
Lattice/Ring interaction areas (3 m), or a street-dressing prop (0.3 m). Wall brackets are snapped to the real wall
surface in Unity (ray against the LOD0 mesh) and only need their foot-of-wall point clear of routes.
Run: uv run --with matplotlib python night_layout.py [--candidates]
"""
import json, math, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
AUDIT = ROOT / "unity/evidence/night-life/20261001/audit-before.json"
SHOPS = ROOT / "unity/AthenHill/Assets/AthenHill/Art/WardShops/Models"
A = json.loads(AUDIT.read_text())

# ------------------------------------------------------------------ obstacles
COLS = []
for c in A["colliders"]:
    (x, y, z), (sx, sy, sz) = c["center"], c["size"]
    if (sx > 70 and sz > 70) or y + sy / 2 < 0.04:      # ground plates and the paving (long walls stay)
        continue
    COLS.append((c["path"], x - sx / 2, x + sx / 2, z - sz / 2, z + sz / 2, y - sy / 2, y + sy / 2))

PROPS = []   # street dressing props (LOD0 renderer footprints)
for r in A["renderers"]:
    p = r["path"]
    if p.startswith("Ward street dressing/") and r["active"] and p.endswith("/LOD0"):
        (x, y, z), (sx, sy, sz) = r["center"], r["size"]
        PROPS.append((p.split("/")[2], x - sx / 2, x + sx / 2, z - sz / 2, z + sz / 2))


def shop_openings():
    """Front, rear and side openings of the rebuilt shops (copied from the street-dressing layout, 30 Sep)."""
    shops = {"relay_works": (-18.1, -18, 90), "air_water": (-18.1, -9, 90), "tool_exchange": (-18.1, 9, 90), "salvage": (-18.1, 18, 90),
             "finery": (18.1, -18, -90), "field_supply": (18.1, -9, -90), "repairs": (18.1, 9, -90), "thread_hide": (18.1, 18, -90)}
    rects = []
    for s, (rx, rz, yaw) in shops.items():
        f = SHOPS / f"{s}.json"
        if not f.exists():
            continue
        d = json.loads(f.read_text())
        sgn = 1 if yaw == 90 else -1
        for r in d.get("recesses", []):
            u0, u1 = r["u"]
            if r["face"] in ("front", "rear"):
                za, zb = sorted([rz - sgn * u0, rz - sgn * u1])
                face_x = rx + sgn * 0.09 if r["face"] == "front" else rx - sgn * 6.95
                out = sgn if r["face"] == "front" else -sgn
                xa, xb = sorted([face_x, face_x + out * 1.3])
                rects.append((f"{s} {r['face']} opening", xa, xb, za - 0.3, zb + 0.3))
            elif r["face"] in ("left", "right"):
                side = -1 if r["face"] == "left" else 1
                fz = rz + (side * 3.89 if yaw == -90 else -side * 3.89)
                xa, xb = sorted([rx - sgn * u0, rx - sgn * u1])
                out = -1 if fz < rz else 1
                za, zb = sorted([fz, fz + out * 1.3])
                rects.append((f"{s} {r['face']} door", xa - 0.3, xb + 0.3, za, zb))
    rects.append(("basic general counter", 5.4, 10.6, 12.2, 14.0))
    rects += [("hill stair -Z", -2.6, 2.6, -13.2, -7.0), ("hill stair +Z", -2.6, 2.6, 7.0, 13.2), ("hill stair +X", 7.0, 13.2, -2.6, 2.6)]
    rects += [("terminal slab", 4.6, 11.4, -13.4, -10.6), ("hall steps", -16.5, -3.6, -23.6, -21.2)]
    # the District gate arches (spawn) and the walk through them
    rects += [("gate arches walk", 41.0, 46.0, -4.6, 16.6)]
    return rects


CLEAR = shop_openings()
ROUTES, POINTS = {}, []
for m in A["markers"]:
    parts = m["path"].split("/")
    if len(parts) == 2 and (parts[0].endswith(" route") or parts[0] == "Mining droid route"):
        ROUTES.setdefault(parts[0], []).append((m["pos"][0], m["pos"][2]))
    elif len(parts) == 2 and parts[0] in ("Colonists", "Landmarks"):
        POINTS.append((parts[1], m["pos"][0], m["pos"][2], 1.3))
    elif len(parts) == 1 and parts[0] in ("Lattice interaction", "Ring interaction"):
        POINTS.append((parts[0], m["pos"][0], m["pos"][2], 3.0))
SEGS = []
for name, pts in ROUTES.items():
    for i in range(len(pts)):
        SEGS.append((name, pts[i], pts[(i + 1) % len(pts)], 1.6 if "droid" in name.lower() else 1.0))


def seg_dist(px, pz, a, b):
    ax, az = a; bx, bz = b
    dx, dz = bx - ax, bz - az
    t = max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / (dx * dx + dz * dz + 1e-9)))
    return math.hypot(px - ax - dx * t, pz - az - dz * t)


def problems(x, z, half=0.35, kind="post"):
    out = []
    x0, x1, z0, z1 = x - half, x + half, z - half, z + half
    if kind == "post":
        for (name, cx0, cx1, cz0, cz1, cy0, cy1) in COLS:
            if cx1 < x0 or cx0 > x1 or cz1 < z0 or cz0 > z1:
                continue
            if cy1 < 0.05 or cy0 > 4.6:
                continue
            out.append("collider " + name)
        for (name, px0, px1, pz0, pz1) in PROPS:
            if not (px1 + 0.3 < x0 or px0 - 0.3 > x1 or pz1 + 0.3 < z0 or pz0 - 0.3 > z1):
                out.append("prop " + name)
    for (name, rx0, rx1, rz0, rz1) in CLEAR:
        if not (rx1 < x0 or rx0 > x1 or rz1 < z0 or rz0 > z1):
            out.append("keep-clear " + name)
    for (name, a, b, margin) in SEGS:
        if seg_dist(x, z, a, b) < margin + half:
            out.append("route " + name)
    for (name, px, pz, rad) in POINTS:
        if math.hypot(x - px, z - pz) < rad + half:
            out.append("point " + name)
    return out


def nearest_wall(x, z, min_top=2.0):
    """Distance from (x, z) to the nearest tall collider (a wall, building or plinth) and its name."""
    best = (1e9, None)
    for (name, cx0, cx1, cz0, cz1, cy0, cy1) in COLS:
        if cy1 < min_top:
            continue
        dx = max(cx0 - x, 0, x - cx1); dz = max(cz0 - z, 0, z - cz1)
        d = math.hypot(dx, dz)
        if d < best[0]:
            best = (d, name)
    return best


def surface_y(x, z):
    best = 0.0
    for (_, x0, x1, z0, z1, y0, y1) in COLS:
        if x0 <= x <= x1 and z0 <= z <= z1 and y1 <= 0.62 and y1 > best:
            best = y1
    return round(best, 3)


# ------------------------------------------------------------------ fixtures
# yaw: Unity yaw of the fixture's +Z (the lamp head / bracket arm points along +Z). Posts carry a downward spot;
# brackets a spot tilted 25 deg out from the wall. "aim" (brackets) is the horizontal direction INTO the wall used to snap.
FIX = []


def post(name, pocket, x, z, yaw, intensity=6.0, rng=15.0, shadows=False, note=""):
    FIX.append(dict(kind="post", name=name, pocket=pocket, pos=[x, surface_y(x, z), z], yaw=yaw, intensity=intensity,
                    range=rng, shadows=shadows, note=note))


def bracket(name, pocket, x, y, z, into_yaw, intensity=4.0, rng=10.0, shadows=False, note=""):
    """x, z: a point about 1 m in front of the wall; into_yaw: direction from that point into the wall face."""
    FIX.append(dict(kind="bracket", name=name, pocket=pocket, pos=[x, y, z], yaw=(into_yaw + 180) % 360, intoYaw=into_yaw,
                    intensity=intensity, range=rng, shadows=shadows, note=note))


def candidates(cx, cz, radius, step=0.5, want_wall=(0.6, 2.6)):
    out = []
    n = int(radius / step)
    for i in range(-n, n + 1):
        for k in range(-n, n + 1):
            x, z = cx + i * step, cz + k * step
            if math.hypot(x - cx, z - cz) > radius:
                continue
            if problems(x, z):
                continue
            d, w = nearest_wall(x, z)
            if not (want_wall[0] <= d <= want_wall[1]):
                continue
            out.append((round(math.hypot(x - cx, z - cz), 2), x, z, round(d, 2), w))
    return sorted(out)[:12]


POCKETS = {
    "courtyard_terminals": (8.0, -16.5, 7.0),
    "courtyard_west": (2.0, -18.0, 6.0),
    "lattice_court_w": (-3.0, -37.0, 4.0),
    "lattice_court_e": (6.0, -37.0, 4.0),
    "hill_benches": (-8.0, 0.0, 5.0),
    "hall_corner": (-2.0, -30.0, 4.0),
    "apron_south": (41.0, -11.0, 6.0),
    "apron_north": (41.0, 13.0, 6.0),
    "south_collapse": (10.5, -40.0, 5.0),
    "south_lane_west": (-20.0, -40.5, 5.0),
    "north_collapse": (-45.5, 40.5, 5.0),
    "north_foot": (12.0, 40.5, 6.0),
    "east_foot_south": (43.5, -26.0, 6.0),
    "east_foot_north": (43.5, 30.0, 6.0),
}

if "--candidates" in sys.argv:
    for k, (cx, cz, r) in POCKETS.items():
        print(f"== {k} ({cx}, {cz})")
        for c in candidates(cx, cz, r):
            print("   ", c)
    sys.exit(0)

# ---- the chosen layout -------------------------------------------------------------------------------------------------
exec((HERE / "night_layout_fixtures.py").read_text())

# ------------------------------------------------------------------ check and write
bad = 0
for f in FIX:
    x, _, z = f["pos"]
    if f["kind"] == "post":
        pr = problems(x, z)
        d, w = nearest_wall(x, z)
        f["nearestWall"] = [round(d, 2), w]
    else:
        # the foot of the wall under the bracket: 0.6 m out from the face along the aim
        pr = [p for p in problems(x, z, half=0.2, kind="bracket")]
    f["problems"] = pr
    if pr:
        bad += 1
    print(f"{f['kind']:7s} {f['name']:34s} {f['pocket']:20s} ({x:6.2f}, {z:6.2f}) yaw {f['yaw']:5.1f} {'OK' if not pr else pr}")
EFFECTS = globals().get("EFFECTS", [])
TERMINAL_FILLS = globals().get("TERMINAL_FILLS", [])
out = dict(date="2026-10-01", audit=str(AUDIT.relative_to(ROOT)), fixtures=FIX, effects=EFFECTS, terminalFills=TERMINAL_FILLS)
(HERE / "night-layout.json").write_text(json.dumps(out, indent=1))
print(f"{len(FIX)} fixtures ({sum(f['kind']=='post' for f in FIX)} posts, {sum(f['kind']=='bracket' for f in FIX)} brackets), {bad} with problems -> night-layout.json")
sys.exit(1 if bad else 0)
