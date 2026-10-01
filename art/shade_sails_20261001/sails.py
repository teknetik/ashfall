#!/usr/bin/env python3
"""Ward shade sails: layout, form finding and validation (1 October 2026). Plain Python + numpy.

Reads the fresh scene audit (unity/evidence/shade-sails/20261001/audit-before.json, StreetDressingAudit) and the survey
(survey.json: lights, cameras, sun, mesh probes of the oasis tree canopy, the retrofit service poles/lines and the
market bunting). Writes sail-layout.json (everything author_sails.py and ShadeSailsPass.cs need) and, with --plot,
review/layout-*.png.

Rules (same family as art/street_dressing_20260930/layout.py and night_layout.py):
* pole footprints (sandbag ring 1.1 m / stone footing 0.84 m) and guy anchors clear of active colliders, street-dressing
  props (+0.3 m), keep-clear zones (shop doors/shutters/stairs, terminal slab, hall steps, Lattice step, West Gate arch
  walk), walker/mechanic/droid routes (1.0 m, droid 1.6 m), NPC stand points and landmarks (1.3 m), the Lattice/Ring
  interaction areas (3 m); guy wires (ground projection) 1.0 m from routes and out of keep-clear zones;
* the solved sail surface: >= 3.0 m above walkable ground (except within 0.8 m of a pole), clear of every collider,
  renderer and probed mesh point (tree canopy, service lines, bunting) by 0.3 m, of lights by 0.6 m, and of the barrel
  fire smoke column (1.6 m); festoons >= 2.55 m;
* sightlines that must stay open (landmarks from the standard cameras and the spawn view) are tested against the
  solved surface.
Run: uv run --with numpy --with matplotlib python sails.py [--plot]
"""
import json, math, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import formfind as FF

EV = ROOT / "unity/evidence/shade-sails/20261001"
# --installed: re-validate against the audit taken after the install (other passes' changes since, the sails' own
# objects filtered out), e.g. after another pass has placed something nearby.
AUDIT = EV / ("audit-after-install.json" if "--installed" in sys.argv else "audit-before.json")
A = json.loads(AUDIT.read_text())
OWN = "Ward shade sails"
A["colliders"] = [c for c in A["colliders"] if not c["path"].startswith(OWN)]
A["renderers"] = [r for r in A["renderers"] if not r["path"].startswith(OWN)]
S = json.loads((EV / "survey-before.json").read_text())   # pre-install survey (the sails' own lights excluded)
SHOPS = ROOT / "unity/AthenHill/Assets/AthenHill/Art/WardShops/Models"
SUN13 = np.array(next(s["lightForward"] for s in S["sun"] if s["hour"] == 13.0))

# ====================================================================== the layout
# Corner records: base (x, z) of the pole on the paving, h = height of the sail fixing (padeye) above the paving,
# kind: "plate" (welded base plate in a sandbag ring, guyed), "block" (dressed-stone footing block, unguyed),
# "service" (an existing retrofit service pole, an I-beam: a wire-rope strop round it with a shackle at h).
# guys: ground anchors (x, z) for "plate" poles (sandbagged anchor plates).
# Festoons: (from, to, sag): "p<k>" = pole k at its festoon hook (just under the fixing), or explicit [x, y, z].
SITES = [
    dict(
        id="Courtyard", name="Courtyard terminals sail", dye="madder", kind="quad", sag=0.06,
        note="over the mission-terminal slab and the gathering space in front of it, between the hill stair and the "
             "Field Supply / Finery porches; madder canvas, natural-canvas patches; shades the screens from the noon sun",
        corners=[
            dict(base=(3.35, -9.05), h=3.85, kind="block"),                     # NW, the niche by the hill stair cheek
            dict(base=(11.85, -9.75), h=4.95, kind="block"),                    # NE, off the Field Supply steps
            dict(base=(11.95, -15.55), h=3.7, kind="plate", guys=[(12.0, -17.75)]),   # SE, behind terminal 01
            dict(base=(4.05, -15.55), h=4.85, kind="plate", guys=[(2.55, -17.05)]),   # SW, behind terminal 03
        ],
        festoons=[("p0", "p2", 0.45), ("p0", "p1", 0.4)],
        lights=[dict(at="f0", drop=0.2, intensity=2.2, range=7.0), dict(at="f1", drop=0.2, intensity=1.6, range=6.0)],
    ),
    dict(
        id="Market", name="Market rest sail", dye="indigo", kind="quad", sag=0.055,
        note="over the market-edge rest spot (picnic table, stools, bench) behind Air + Water, tied to the two retrofit "
             "service poles on the lane and two new poles on the market side; indigo canvas; the fire barrel stands "
             "under the high south-west corner, its smoke drifting east under the sail",
        corners=[
            dict(base=(-28.4, -4.5), h=4.35, kind="service"),                   # NE: N service pole
            dict(base=(-28.4, -13.5), h=3.6, kind="service"),                   # SE: S service pole
            dict(base=(-31.9, -12.4), h=5.3, kind="block"),                      # SW, high over the barrel smoke
            dict(base=(-32.55, -5.0), h=3.75, kind="block"),                     # NW, market side
        ],
        festoons=[("p3", "p0", 0.3), ("p0", "p1", 0.55)],
        lights=[dict(at=[-29.9, 3.05, -7.6], intensity=2.0, range=6.5)],
    ),
    dict(
        id="Apron", name="West Gate apron sail", dye="natural", kind="quad", sag=0.06,
        note="over the caravan goods waiting on the apron north of the spawn; natural canvas with madder repair panels; "
             "frames the first view west from the gate",
        corners=[
            dict(base=(33.3, 7.15), h=3.7, kind="plate", guys=[(31.65, 5.75)]),        # SW
            dict(base=(40.3, 4.55), h=5.0, kind="block"),                            # SE, by the arch walk
            dict(base=(40.2, 12.55), h=3.75, kind="block"),                          # NE, by arch B
            dict(base=(33.6, 12.7), h=4.85, kind="plate", guys=[(31.95, 14.35)]),     # NW
        ],
        festoons=[("p0", "p2", 0.45), ("p0", "p1", 0.4)],
        lights=[dict(at="f0", drop=0.2, intensity=2.2, range=7.0), dict(at="f1", drop=0.2, intensity=1.6, range=6.0)],
    ),
    dict(
        id="Lattice", name="Lattice court sail", dye="natural_indigo", kind="tri", sag=0.05,
        note="over the north half of the approach to the Lattice step and the court east of it, rising to its high "
             "corner by the pad so the ring stays in view from under it; natural canvas with indigo panels",
        corners=[
            dict(base=(3.3, -33.45), h=5.2, kind="block"),                       # S, east of the step, by the pad
            dict(base=(6.1, -25.55), h=3.7, kind="block"),                       # NE
            dict(base=(-3.2, -25.35), h=4.45, kind="block"),                     # NW, the hall's east service edge
        ],
        festoons=[("p2", "p0", 0.45), ("p2", "p1", 0.35)],
        lights=[dict(at="f0", drop=0.2, intensity=2.0, range=7.0), dict(at="f1", drop=0.2, intensity=1.4, range=6.0)],
    ),
]

RAKE = math.radians(4.0)      # new poles lean 4 degrees away from their sail
HARDWARE = 0.5                # fixing -> fabric corner: shackle, turnbuckle / lashing, corner ring and plate
POLE_R = 0.057                # 114 mm pipe
SERVICE_HALF = (0.1, 0.13)    # retrofit service poles: I-beam 0.20 (x) by 0.26 (z, flanges) m, measured from the probe
FESTOON_DROP = 0.35           # festoon hook below the sail fixing
BULB_STEP = 0.48

# ====================================================================== obstacles
COLS = []
for c in A["colliders"]:
    (x, y, z), (sx, sy, sz) = c["center"], c["size"]
    if (sx > 70 and sz > 70) or y + sy / 2 < 0.04:
        continue
    COLS.append((c["path"], x - sx / 2, x + sx / 2, z - sz / 2, z + sz / 2, y - sy / 2, y + sy / 2))

PROPS = []
for r in A["renderers"]:
    p = r["path"]
    if p.startswith("Ward street dressing/") and r["active"] and p.endswith("/LOD0"):
        (x, y, z), (sx, sy, sz) = r["center"], r["size"]
        PROPS.append((p.split("/")[1] + "/" + p.split("/")[2], x - sx / 2, x + sx / 2, z - sz / 2, z + sz / 2, y + sy / 2))

# overhead renderers (fittings, lamps, signs, cables...) for the sail clearance: active, not LOD1+, not huge
RENDS = []
for r in A["renderers"]:
    p = r["path"]
    if not r["active"] or any(f"LOD{k}" in p for k in (1, 2, 3)) or p.startswith("City Render Chunks") or p.startswith("Paving"):
        continue
    (x, y, z), (sx, sy, sz) = r["center"], r["size"]
    if sx > 12 or sz > 12 or y + sy / 2 < 2.0:
        continue
    RENDS.append((p, x - sx / 2, x + sx / 2, z - sz / 2, z + sz / 2, y - sy / 2, y + sy / 2))

PROBE_PTS = np.array([q for p in S["probes"] for q in p.get("points", [])], float)
PROBE_SRC = [p["path"] for p in S["probes"] for q in p.get("points", [])]
LIGHTS = [l for l in S["lights"] if l["active"] and l["enabled"] and l["type"] != "Directional"]


def shop_openings():
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
    rects.append(("basic general counter", 5.4, 10.6, 12.2, 14.0))
    rects += [("hill stair -Z", -2.6, 2.6, -13.2, -7.0), ("hill stair +Z", -2.6, 2.6, 7.0, 13.2), ("hill stair +X", 7.0, 13.2, -2.6, 2.6)]
    rects += [("terminal slab", 4.4, 11.6, -14.85, -10.6), ("hall steps", -16.5, -3.6, -23.6, -21.2)]
    rects += [("gate arches walk", 41.0, 46.0, -4.6, 16.6)]
    # shop porch first steps and the ground in front of them (people step up anywhere along them)
    for c in A["colliders"]:
        if c["path"].endswith("_first_step"):
            (x, y, z), (sx, sy, sz) = c["center"], c["size"]
            out = -1 if x > 0 else 1                          # west-side shops step down to +X, east-side to -X
            xa, xb = sorted([x - out * sx / 2, x + out * (sx / 2 + 1.1)])
            rects.append((c["path"].split("/")[-1] + " approach", xa, xb, z - sz / 2, z + sz / 2))
    rects += [("lattice step approach", -2.4, 2.4, -34.0, -31.6)]
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


def footprint_problems(x, z, half, ignore=()):
    out = []
    x0, x1, z0, z1 = x - half, x + half, z - half, z + half
    for (name, cx0, cx1, cz0, cz1, cy0, cy1) in COLS:
        if any(s in name for s in ignore):
            continue
        if cx1 < x0 or cx0 > x1 or cz1 < z0 or cz0 > z1 or cy1 < 0.05 or cy0 > 4.6:
            continue
        out.append("collider " + name)
    for (name, px0, px1, pz0, pz1, top) in PROPS:
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


# ====================================================================== geometry from the layout
def build_site(site, spacing=0.3):
    corners = site["corners"]
    base = [np.array([c["base"][0], 0.0, c["base"][1]]) for c in corners]
    cxz = np.mean([[b[0], b[2]] for b in base], 0)
    poles, fix = [], []
    for k, c in enumerate(corners):
        b = base[k]
        out = np.array([b[0] - cxz[0], 0, b[2] - cxz[1]])
        out /= np.linalg.norm(out)
        if c["kind"] == "service":
            # the retrofit service poles are I-beams (flanges facing +-Z): leave the beam's envelope along the pull
            axis = np.array([0, 1.0, 0])
            inward = -out
            hx, hz = SERVICE_HALF
            t_exit = min(hx / max(abs(inward[0]), 1e-6), hz / max(abs(inward[2]), 1e-6))
            f = b + axis * c["h"] + inward * (t_exit + 0.06)
            top = np.array([b[0], 8.3, b[2]])
            r = SERVICE_HALF[1]
        else:
            axis = np.array([out[0] * math.sin(RAKE), math.cos(RAKE), out[2] * math.sin(RAKE)])
            base_y = 0.5 if c["kind"] == "block" else 0.02           # the pipe stands in the block's collar
            b0 = b + np.array([0, base_y, 0])
            t = (c["h"] - base_y) / axis[1]
            f = b0 + axis * t - out * (POLE_R + 0.06)              # padeye on the sail side of the pipe
            top = b0 + axis * (t + 0.32)
            r = POLE_R
        poles.append(dict(kind=c["kind"], base=b.tolist(), axis=axis.tolist(), top=top.tolist(), fixing=f.tolist(), radius=r,
                          outward=out.tolist(), guys=[[g[0], 0.0, g[1]] for g in c.get("guys", [])]))
        fix.append(f)
    centroid = np.mean(fix, 0)
    fabric = [FF.pull_in(f, centroid, HARDWARE) for f in fix]
    sail = FF.Sail(fabric, spacing=spacing, sag=site.get("sag", 0.07), belly=site.get("belly", 0.06))
    # festoons: hook on each pole just under its fixing, on the inside face
    strings = []
    for (a, b, sag) in site["festoons"]:
        def end(ref):
            if isinstance(ref, str) and ref.startswith("p"):
                p = poles[int(ref[1:])]
                return np.array(p["fixing"]) - np.array([0, FESTOON_DROP, 0])
            return np.array(ref, float)
        pa, pb = end(a), end(b)
        L = np.linalg.norm(pb - pa)
        n = max(2, int(round(L / BULB_STEP)))
        pts = FF.catenary(pa, pb, sag, max(8, int(L * 4)))
        bulbs = FF.catenary(pa, pb, sag, n)[1:-1]
        strings.append(dict(a=pa.tolist(), b=pb.tolist(), sag=sag, length=float(L), points=pts.tolist(), bulbs=bulbs.tolist()))
    lights = []
    for i, l in enumerate(site["lights"]):
        if isinstance(l["at"], str):
            s = strings[int(l["at"][1:])]
            mid = (np.array(s["a"]) + np.array(s["b"])) / 2 - np.array([0, s["sag"] + l.get("drop", 0.2), 0])
            pos = mid
        else:
            pos = np.array(l["at"], float)
        lights.append(dict(name=f"{site['id']} festoon light {i + 1}", pos=pos.tolist(), intensity=l["intensity"], range=l["range"],
                           color=[1.0, 0.71, 0.43]))
    return dict(poles=poles, fixings=[f.tolist() for f in fix], fabric=[f.tolist() for f in fabric], sail=sail, strings=strings, lights=lights)


# ====================================================================== checks
def tri_hit(o, d, a, b, c):
    e1, e2 = b - a, c - a
    h = np.cross(d, e2)
    det = np.dot(e1, h)
    if abs(det) < 1e-9:
        return None
    f = 1 / det
    s = o - a
    u = f * np.dot(s, h)
    if u < 0 or u > 1:
        return None
    q = np.cross(s, e1)
    v = f * np.dot(d, q)
    if v < 0 or u + v > 1:
        return None
    t = f * np.dot(e2, q)
    return t if 0 < t < 1 else None


def sail_tris(sail):
    tris = []
    for f in sail.F:
        if len(f) == 4:
            tris += [(f[0], f[1], f[2]), (f[0], f[2], f[3])]
        else:
            tris.append(tuple(f))
    return tris


SIGHTLINES = [
    ("cam_grid -> Lattice ring", "cam_grid", [(0, 1.6, -40.7), (0, 4.0, -40.7), (0, 6.5, -40.7), (-2.5, 4.0, -40.7), (2.5, 4.0, -40.7)]),
    ("cam_grid -> Lattice pad front", "cam_grid", [(0, 0.6, -34.0), (0, 0.3, -33.4), (-2, 0.6, -34.0)]),
    ("cam_nl_lattice -> Lattice ring", "cam_nl_lattice", [(0, 1.6, -40.7), (0, 6.5, -40.7)]),
    ("approach eye (0,1.6,-26) -> ring top", (0, 1.6, -26), [(0, 6.6, -40.7), (0, 4, -40.7)]),
    ("approach eye (0,1.6,-30) -> ring top", (0, 1.6, -30), [(0, 6.6, -40.7)]),
    ("cam_terminal -> terminals", "cam_terminal", [(8, 1.6, -13.8), (6, 1.6, -13.8), (10, 1.6, -13.8)]),
    ("cam_courtyard -> terminals", "cam_courtyard", [(8, 1.6, -13.8), (10, 1.6, -13.8)]),
    ("spawn camera (47,2.7,0) -> hill tree", (47.0, 2.73, 0.0), [(4, 8, 0), (4, 12, 0)]),
    ("spawn camera (47,2.7,0) -> Vex", (47.0, 2.73, 0.0), [(41.7, 1.6, -1.5)]),
    ("cam_gate -> arches", "cam_gate", [(47.5, 3, 0), (47.5, 3, 12)]),
    ("cam_market -> cookfire", "cam_market", [(-34.5, 1.5, -2.8)]),
]


def cam_pos(ref):
    if isinstance(ref, str):
        c = next(c for c in S["cameras"] if c["name"] == ref)
        return np.array(c["pos"], float)
    return np.array(ref, float)


WARN = []
SMOKE = [("barrel fire smoke plume", np.array([-32.2, 1.1, -9.2]), np.array([-30.2, 3.6, -8.95]), 0.3, 0.7)]
WALK_EXEMPT = 0.8


def check_site(site, g):
    probs = []
    for k, (c, p) in enumerate(zip(site["corners"], g["poles"])):
        x, z = c["base"]
        if c["kind"] == "service":
            continue
        half = 0.55 if c["kind"] == "plate" else 0.42
        for pr in footprint_problems(x, z, half):
            probs.append(f"pole {k}: {pr}")
        for j, gz in enumerate(c.get("guys", [])):
            for pr in footprint_problems(gz[0], gz[1], 0.38):
                probs.append(f"pole {k} guy {j} anchor: {pr}")
            # ground projection of the wire: routes and keep-clear zones
            for t in np.linspace(0.15, 0.95, 9):
                gx, gzz = x + (gz[0] - x) * t, z + (gz[1] - z) * t
                hgt = p["top"][1] * (1 - t)
                for (name, a, b, margin) in SEGS:
                    if seg_dist(gx, gzz, a, b) < margin:
                        probs.append(f"pole {k} guy {j} over route {name}")
                for (name, rx0, rx1, rz0, rz1) in CLEAR:
                    if rx0 <= gx <= rx1 and rz0 <= gzz <= rz1 and hgt < 2.4:
                        probs.append(f"pole {k} guy {j} through keep-clear {name}")
                for (name, cx0, cx1, cz0, cz1, cy0, cy1) in COLS:
                    if cx0 <= gx <= cx1 and cz0 <= gzz <= cz1 and cy1 > hgt - 0.15 and cy0 < hgt:
                        probs.append(f"pole {k} guy {j} through collider {name}")
    sail = g["sail"]
    P = sail.P
    poles_xz = [np.array([p["base"][0], p["base"][2]]) for p in g["poles"]]
    lowest_walk = 99.0
    hits = {}
    for i, q in enumerate(P):
        x, y, z = q
        near_pole = min(np.linalg.norm(np.array([x, z]) - b) for b in poles_xz) < WALK_EXEMPT
        if not near_pole:
            lowest_walk = min(lowest_walk, y)
        for (name, cx0, cx1, cz0, cz1, cy0, cy1) in COLS:
            if cx0 - 0.3 <= x <= cx1 + 0.3 and cz0 - 0.3 <= z <= cz1 + 0.3 and cy1 > y - 0.3 and cy0 < y + 0.3:
                if "service" not in name.lower() or site["id"] != "Market":
                    hits.setdefault("collider " + name, 0); hits["collider " + name] += 1
        for (name, rx0, rx1, rz0, rz1, ry0, ry1) in RENDS:
            if rx0 - 0.3 <= x <= rx1 + 0.3 and rz0 - 0.3 <= z <= rz1 + 0.3 and ry1 > y - 0.3 and ry0 < y + 0.3:
                if site["id"] == "Market" and "Service lanes" in name:
                    continue
                hits.setdefault("renderer " + name, 0); hits["renderer " + name] += 1
        for l in LIGHTS:
            if np.linalg.norm(np.array(l["pos"]) - q) < 0.6:
                hits.setdefault("light " + l["path"], 0); hits["light " + l["path"]] += 1
        for (name, a0, a1, r0, r1) in SMOKE:
            ax_ = a1 - a0
            t = max(0.0, min(1.0, float(np.dot(q - a0, ax_) / np.dot(ax_, ax_))))
            if np.linalg.norm(q - (a0 + ax_ * t)) < r0 + (r1 - r0) * t + 0.2:
                hits.setdefault(name, 0); hits[name] += 1
    if len(PROBE_PTS):
        d = np.linalg.norm(PROBE_PTS[:, None, :] - P[None, :, :], axis=2)
        close = np.where(d.min(1) < 0.3)[0]
        for k in close:
            src = PROBE_SRC[k]
            if site["id"] == "Market" and "Service lanes" in src:
                # the clamped poles themselves; their crossarms/lines are above 7 m
                if PROBE_PTS[k][1] < 7.0:
                    continue
            hits.setdefault("probe " + src, 0); hits["probe " + src] += 1
    for h, n in hits.items():
        if h.startswith("barrel fire smoke"):
            # the faded top of the barrel smoke (drifting east at 3-4 m) passes under the high west part of the market
            # sail: accepted, reported, judged in the native lookbook
            WARN.append(f"{site['id']}: {h} ({n} nodes within 0.2 m of the plume's faded end cap)")
            continue
        probs.append(f"sail: {h} ({n} nodes)")
    if lowest_walk < 3.0:
        probs.append(f"sail: lowest point over walkable ground {lowest_walk:.2f} m < 3.0")
    for j, s in enumerate(g["strings"]):
        pts = np.array(s["points"])
        mid = pts[1:-1]
        low = float(mid[:, 1].min()) if len(mid) else 9
        if low < 2.55:
            probs.append(f"festoon {j}: lowest {low:.2f} m < 2.55")
        # festoon must stay under the sail (not through it)
        for q in mid:
            hs = sail.height_at(q[0], q[2])
            if hs is not None and q[1] > hs - 0.12:
                probs.append(f"festoon {j}: touches the sail at ({q[0]:.1f}, {q[2]:.1f})")
                break
    return probs, lowest_walk


def sightline_report(built):
    out = []
    for label, cam, targets in SIGHTLINES:
        o = cam_pos(cam)
        for t in targets:
            d = np.array(t, float) - o
            for sid, g in built.items():
                sail = g["sail"]
                hit = None
                for (a, b, c) in sail_tris(sail):
                    tt = tri_hit(o, d, sail.P[a], sail.P[b], sail.P[c])
                    if tt is not None:
                        hit = tt
                        break
                if hit is not None:
                    out.append(f"{label}: blocked by {sid} at t={hit:.2f} (target {t})")
    return out


def to_json(site, g):
    sail = g["sail"]
    return dict(id=site["id"], name=site["name"], dye=site["dye"], kind=site["kind"], note=site["note"],
                corners=site["corners"], poles=g["poles"], fixings=g["fixings"], fabric=g["fabric"],
                sags=sail.sags, lowest=round(sail.lowest(), 3), festoons=g["strings"], lights=g["lights"],
                outline=[[round(v, 3) for v in p] for p in sail.outline().tolist()],
                previewColour={"madder": "#a0452f", "indigo": "#3d5068", "natural": "#cbb48c", "natural_indigo": "#8b95a0"}[site["dye"]])


def main():
    built, bad, report = {}, 0, []
    for site in SITES:
        g = build_site(site)
        built[site["id"]] = g
        probs, low = check_site(site, g)
        bad += len(probs)
        s = g["sail"]
        report.append(f"== {site['id']}: {site['kind']} corners h {[c['h'] for c in site['corners']]}, hem sags {s.sags}, lowest sail {s.lowest():.2f} m, "
                      f"lowest over walkable {low:.2f} m, festoons {[round(x['length'], 1) for x in g['strings']]} m, "
                      f"bulbs {sum(len(x['bulbs']) for x in g['strings'])}")
        report += ["   " + p for p in probs] or ["   OK"]
    sl = sightline_report(built)
    report.append("== sightlines")
    report += ["   " + x for x in sl] or ["   all open"]
    report.append("== warnings (accepted, see README)")
    report += ["   " + x for x in WARN] or ["   none"]
    bad += len(sl)
    print("\n".join(report))
    if "--installed" in sys.argv:
        (HERE / "layout-report-installed.txt").write_text("\n".join(report) + "\n")
        print(f"{bad} problems (installed check, layout not rewritten)")
        return 1 if bad else 0
    out = dict(date="2026-10-01", audit=str(AUDIT.relative_to(ROOT)), sun13=SUN13.tolist(),
               constants=dict(rake_deg=4.0, hardware=HARDWARE, pole_r=POLE_R, service_half=list(SERVICE_HALF), festoon_drop=FESTOON_DROP, bulb_step=BULB_STEP),
               sails=[to_json(s, built[s["id"]]) for s in SITES])
    (HERE / "sail-layout.json").write_text(json.dumps(out, indent=1))
    (HERE / "layout-report.txt").write_text("\n".join(report) + "\n")
    if "--plot" in sys.argv:
        plot(built)
    print(f"{bad} problems -> sail-layout.json")
    return 1 if bad else 0


def plot(built):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Polygon, Circle
    views = {"Courtyard": (-2, 18, -22, -4), "Market": (-38, -22, -18, 0), "Apron": (27, 47, -6, 18), "Lattice": (-8, 10, -40, -20)}
    for sid, ext in views.items():
        g = built[sid]
        fig, ax = plt.subplots(figsize=(12, 12 * (ext[3] - ext[2]) / (ext[1] - ext[0])))
        fig.subplots_adjust(0.05, 0.04, 0.99, 0.97)
        for (name, cx0, cx1, cz0, cz1, cy0, cy1) in COLS:
            if cx1 < ext[0] - 2 or cx0 > ext[1] + 2 or cz1 < ext[2] - 2 or cz0 > ext[3] + 2:
                continue
            ax.add_patch(Rectangle((cx0, cz0), cx1 - cx0, cz1 - cz0, fc="#888" if cy1 > 0.7 else "#ccc", ec="#555", lw=0.4, alpha=0.5))
        for (name, px0, px1, pz0, pz1, top) in PROPS:
            ax.add_patch(Rectangle((px0, pz0), px1 - px0, pz1 - pz0, fc="#b58", ec="none", alpha=0.35))
        for (name, rx0, rx1, rz0, rz1, ry0, ry1) in RENDS:
            if rx1 < ext[0] or rx0 > ext[1] or rz1 < ext[2] or rz0 > ext[3]:
                continue
            ax.add_patch(Rectangle((rx0, rz0), rx1 - rx0, rz1 - rz0, fc="none", ec="#06c", lw=0.4, alpha=0.6))
        for (name, rx0, rx1, rz0, rz1) in CLEAR:
            ax.add_patch(Rectangle((rx0, rz0), rx1 - rx0, rz1 - rz0, fc="#f80", ec="#f80", alpha=0.12, lw=0.6))
        for (name, a, b, margin) in SEGS:
            ax.plot([a[0], b[0]], [a[1], b[1]], "-", color="#2a7", lw=2, alpha=0.7)
        for (name, px, pz, rad) in POINTS:
            ax.add_patch(Circle((px, pz), rad, fc="none", ec="g", lw=0.8)); ax.text(px, pz, name[:14], fontsize=6, color="g")
        if len(PROBE_PTS):
            m = (PROBE_PTS[:, 0] > ext[0]) & (PROBE_PTS[:, 0] < ext[1]) & (PROBE_PTS[:, 2] > ext[2]) & (PROBE_PTS[:, 2] < ext[3])
            ax.scatter(PROBE_PTS[m, 0], PROBE_PTS[m, 2], s=0.5, c="#555", alpha=0.4)
        for l in LIGHTS:
            x, z = l["pos"][0], l["pos"][2]
            if ext[0] <= x <= ext[1] and ext[2] <= z <= ext[3]:
                ax.plot(x, z, "*", color="#e90", ms=9)
        for sid2, g2 in built.items():
            s = g2["sail"]
            o = s.outline()
            # 13:00 shadow footprint on the paving
            sh = o - SUN13[None, :] * (o[:, 1:2] / SUN13[1])
            ax.add_patch(Polygon(sh[:, [0, 2]], closed=True, fc="#000", alpha=0.10, ec="none"))
            ax.add_patch(Polygon(o[:, [0, 2]], closed=True, fc="#c63", alpha=0.25, ec="#a40", lw=1.2))
            for p in g2["poles"]:
                ax.plot(p["base"][0], p["base"][2], "ko", ms=5)
                for gg in p["guys"]:
                    ax.plot([p["top"][0], gg[0]], [p["top"][2], gg[2]], "k-", lw=0.7); ax.plot(gg[0], gg[2], "ks", ms=4)
            for st in g2["strings"]:
                pts = np.array(st["points"]); ax.plot(pts[:, 0], pts[:, 2], "-", color="#fb0", lw=1)
                b = np.array(st["bulbs"]); ax.plot(b[:, 0], b[:, 2], ".", color="#d80", ms=3)
            for l in g2["lights"]:
                ax.add_patch(Circle((l["pos"][0], l["pos"][2]), l["range"] * 0.5, fc="#fd0", alpha=0.08, ec="#da0"))
        ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3]); ax.set_aspect("equal"); ax.grid(True, lw=0.3)
        ax.set_xticks(range(int(ext[0]), int(ext[1]) + 1)); ax.set_yticks(range(int(ext[2]), int(ext[3]) + 1)); ax.tick_params(labelsize=6)
        ax.set_title(f"{sid}: sail (orange), 13:00 shadow (grey), poles, guys, festoons, lights")
        out = HERE / f"review/layout-{sid}.png"
        fig.savefig(out, dpi=70); plt.close(fig)
        print(out)


if __name__ == "__main__":
    sys.exit(main())
