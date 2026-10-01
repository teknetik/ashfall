#!/usr/bin/env python3
"""Wall-foot sand layout (1 October 2026): plain Python. Writes layout.json for Editor/WallFootDriftsPass.cs and
review/layout-map.png (with --plot).

Inputs: faces.json (faces.py), probe.json (probe_faces.py: where each wall foot really is), kit.json (author_drift_kit.py:
visible footprints), and the scene audit (StreetDressingAudit.DumpBatch: colliders, renderers, markers).

Rules (art-direction review item 6 and the pass brief):
* Wind. The Ward's prevailing wind blows from the west-south-west towards +X/+Z (the windborne dust systems move at
  x 1.3-2.6, z 0.35-1.0 m/s). Faces looking into the wind (outward normal against it) carry the heaviest, most continuous
  banks; faces in its lee carry moderate banks; faces along it lighter runs broken by bare stretches.
* Inside corners always collect a bank (porch/step junctions, hill stair cheeks, Vanguard Hall piers). Step risers get
  small banks at their ends only; the walked middle of every step stays clean. Posts get a collar with a lee tail.
* The narrow alleys between paired shops get a thin sand floor (wind funnels through them).
* Kept clear: doors, bays, rear doors and air conditioners (faces.py), every prop, collider and chunk-drawn object at the
  foot (scene audit; 8 cm margin), walker/mechanic/droid routes (sand toe >= 0.45 m from the line), NPC and landmark
  points (1.0 m), the Lattice/Ring interaction areas, the stair approaches and the Vanguard Hall step approach.
  The perimeter walls (own sand) and the West Gate arches (own sand) are not touched.
* Decals (URP projectors, drawn to 40 m): a sand-dust band on the ground along each banked stretch (the feathered
  transition from the drift toe to the paving), a dust/contact-grime skirt on walls taller than a riser, a collar and
  lee tail under each post, sheets under the alley sand.

Run: python3 layout.py [--plot] [--audit path]
"""
import json, math, random, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
AUDIT = ROOT / "unity/evidence/wall-foot-drifts/20261001/audit.json"
if "--audit" in sys.argv:
    AUDIT = Path(sys.argv[sys.argv.index("--audit") + 1])
A = json.loads(AUDIT.read_text())
FJ = json.loads((HERE / "faces.json").read_text())
PR = json.loads((HERE / "probe.json").read_text())
KIT = json.loads((HERE / "kit.json").read_text())["pieces"]

WIND = (0.95, 0.31)                       # direction the wind travels (towards +X, a little +Z)
wl = math.hypot(*WIND)
WIND = (WIND[0] / wl, WIND[1] / wl)
rng = random.Random(20261001)
R = lambda a, b: rng.uniform(a, b)

# ------------------------------------------------------------------ obstacles from the scene audit
BUILDING_ROOTS = ("Ward shops (hall district)/", "Ward shops (north avenue)/", "Vanguard Hall/", "Ward hill/", "Ward perimeter walls/",
                  "City Render Chunks/", "Paving", "COL_Ground", "Desert Landscape/", "Basin mountains/", "Player/", "Colonists/",
                  "Windborne dust/", "City Atmosphere/", "Ward wall-foot drifts/", "Ward west gate arches/", "Sky", "Sun")
SKIP_COLLIDERS = ("AuthoredWorld/COL_BLD_", "AuthoredWorld/COL_ENV_", "AuthoredWorld/COL_Ground", "Ward oasis tree/")
SOFT = ("Vegetation", "joint growth", "Joint growth", "weeds", "Weeds", "grass", "Grass")
chunk_mats = set()
for r in A["renderers"]:
    p = r["path"]
    if p.startswith("City Render Chunks/Generated material chunks/Chunk_"):
        parts = p.split("/")[-1].split("_")
        chunk_mats.add("_".join(parts[2:-2]))

OBST = []          # (x0, x1, z0, z1, y0, y1, path)
for r in A["renderers"]:
    p = r["path"]
    if not r["active"] or p.startswith(BUILDING_ROOTS) or p.startswith(SKIP_COLLIDERS) or p.split("/")[-1].startswith("COL_"):
        continue
    if not r["enabled"] and not any(m in chunk_mats for m in (r["mats"] or []) if m):
        continue                               # hidden (collider proxy) rather than drawn by the render chunks
    (x, y, z), (sx, sy, sz) = r["center"], r["size"]
    if sx > 6 or sz > 6 or sx * sz < 1e-4 or sy < 0.06 or y + sy / 2 < 0.05 or abs(x) > 47 or abs(z) > 44:
        continue                               # buildings, ground-flush paving and decal quads are not obstacles
    if any(k in p for k in SOFT):
        continue                               # dry grass and weeds: sand banks round them
    OBST.append((x - sx / 2, x + sx / 2, z - sz / 2, z + sz / 2, y - sy / 2, y + sy / 2, p))
for c in A["colliders"]:
    p = c["path"]
    if p.startswith(BUILDING_ROOTS) or p.startswith(SKIP_COLLIDERS):
        continue
    (x, y, z), (sx, sy, sz) = c["center"], c["size"]
    if sx > 6 or sz > 6 or sy < 0.06 or abs(x) > 47 or abs(z) > 44:
        continue
    yaw = math.radians(c.get("yaw") or 0.0)
    ex = abs(sx * math.cos(yaw)) + abs(sz * math.sin(yaw))
    ez = abs(sx * math.sin(yaw)) + abs(sz * math.cos(yaw))
    OBST.append((x - ex / 2, x + ex / 2, z - ez / 2, z + ez / 2, y - sy / 2, y + sy / 2, p))

# walkable surfaces (street 0, steps 0.25, porch decks and the hall podium 0.5) from the saved colliders
WALK = []
for c in A["colliders"]:
    (x, y, z), (sx, sy, sz) = c["center"], c["size"]
    top = y + sy / 2
    if 0.1 < top <= 0.62 and sx < 30 and sz < 30 and (c["path"].startswith(("AuthoredWorld/COL_BLD_", "AuthoredWorld/COL_ENV_", "Vanguard Hall/"))):
        WALK.append((x - sx / 2, x + sx / 2, z - sz / 2, z + sz / 2, top))


def surface_y(x, z):
    best = 0.0
    for (x0, x1, z0, z1, top) in WALK:
        if x0 <= x <= x1 and z0 <= z <= z1 and top > best:
            best = top
    return round(best, 3)


# routes, NPC/landmark points, keep-clear rectangles
ROUTES, POINTS = {}, []
for m in A["markers"]:
    parts = m["path"].split("/")
    if len(parts) == 2 and (parts[0].endswith(" route") or parts[0] == "Mining droid route"):
        ROUTES.setdefault(parts[0], []).append((m["pos"][0], m["pos"][2]))
    elif len(parts) == 2 and parts[0] in ("Colonists", "Landmarks"):
        POINTS.append((parts[1], m["pos"][0], m["pos"][2], 1.0))
    elif len(parts) == 1 and parts[0] in ("Lattice interaction", "Ring interaction"):
        POINTS.append((parts[0], m["pos"][0], m["pos"][2], 3.0))
SEGS = []
for name, pts in ROUTES.items():
    for i in range(len(pts)):
        SEGS.append((name, pts[i], pts[(i + 1) % len(pts)]))
CLEAR = [("hill stair -Z approach", -2.0, 2.0, -13.2, -10.6), ("hill stair +Z approach", -2.0, 2.0, 10.6, 13.2),
         ("hill stair +X approach", 10.6, 13.2, -2.0, 2.0), ("hall step approach", -13.25, -6.75, -23.6, -21.2),
         ("terminal slab", 4.6, 11.4, -13.4, -10.6), ("basic general counter", 5.4, 10.6, 12.2, 14.0),
         ("west gate arches", 45.0, 60.0, -6.0, 18.0)]


def seg_dist(px, pz, a, b):
    ax, az = a; bx, bz = b
    dx, dz = bx - ax, bz - az
    t = max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / (dx * dx + dz * dz + 1e-9)))
    return math.hypot(px - ax - dx * t, pz - az - dz * t)


def blocked(x, z, y, r=0.0, ignore_routes=False):
    """Why (x, z) at surface y cannot carry sand (None when free). r = extra radius."""
    for (x0, x1, z0, z1, y0, y1, p) in OBST:
        if x0 - 0.08 - r <= x <= x1 + 0.08 + r and z0 - 0.08 - r <= z <= z1 + 0.08 + r and y1 > y + 0.03 and y0 < y + 0.35:
            return "obstacle " + p
    if not ignore_routes:
        for (name, a, b) in SEGS:
            if seg_dist(x, z, a, b) < 0.45 + r:
                return "route " + name
    for (name, px, pz, rad) in POINTS:
        if math.hypot(x - px, z - pz) < rad + r:
            return "point " + name
    for (name, x0, x1, z0, z1) in CLEAR:
        if x0 - r <= x <= x1 + r and z0 - r <= z <= z1 + r:
            return "keep-clear " + name
    return None


# ------------------------------------------------------------------ faces: real foot line from the probe
def exposure(n):
    d = n[0] * WIND[0] + n[1] * WIND[1]
    return max(0.0, -d), max(0.0, d), 1.0 - abs(d)        # windward, lee, along


def foot_offsets(f):
    """Per probe sample: (u, offset) with the most protruding surface in the bottom 8 cm; None where open."""
    rows = PR["faces"][f["id"]]
    out = []
    side_fallback = f["kind"] == "wall"          # shop sides/rear: the old porch slab (render chunks) stands at -5 mm
    for row in rows:
        u, h03, h08 = row[0], row[1], row[2]
        vals = [v for v in (h03, h08) if v is not None]
        if vals:
            out.append((u, max(vals)))
        elif side_fallback:
            out.append((u, -0.005))
        else:
            out.append((u, None))
    return out


def usable_spans(f):
    """Split a face into spans (u0, u1, offset) that can carry sand: open, unobstructed, offset continuous."""
    L = f["length"]
    a, b, n = f["a"], f["b"], f["n"]
    t = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
    offs = foot_offsets(f)
    ok = []
    for (u, off) in offs:
        why = None
        if off is None or off < -0.2 or off > 0.25:
            why = "open"
        elif any(e0 <= u <= e1 for (e0, e1) in f["exclude"]):
            why = "exclude"
        else:
            # the sand strip at this u: check 0.12, 0.35 and 0.55 m out from the real face
            for d in (0.12, 0.35, 0.55):
                px = a[0] + t[0] * u + n[0] * (off + d)
                pz = a[1] + t[1] * u + n[1] * (off + d)
                why = blocked(px, pz, f["y"])
                if why:
                    break
        ok.append((u, off, why))
    spans, cur = [], None
    for (u, off, why) in ok:
        if why is None and (cur is None or abs(off - cur["offs"][-1]) < 0.03):
            if cur is None:
                cur = {"u0": u, "offs": []}
            cur["u1"] = u
            cur["offs"].append(off)
        else:
            if cur is not None:
                spans.append(cur)
            cur = {"u0": u, "u1": u, "offs": [off]} if why is None else None
    if cur is not None:
        spans.append(cur)
    out = []
    for s in spans:
        if s["u1"] - s["u0"] >= 0.3:
            out.append((s["u0"], s["u1"], max(s["offs"])))
    return out, t, [w for (_, _, w) in ok if w]


# ------------------------------------------------------------------ placement
PL, DECALS, REJECT = [], [], []
def samples(p):
    """Points of the visible sand outside the wall (local z > 4 cm; corners also local x > 4 cm), shrunk 10 %."""
    fp = KIT[p["piece"]]["footprint"]
    s = p["scale"]
    a = math.radians(p["yaw"])
    x0, x1, z0, z1 = fp
    if p["piece"].startswith(("Run", "Corner")):
        z0 = max(z0, 0.04)
    if p["piece"].startswith("Corner"):
        x0 = max(x0, 0.04)
    xs = [x0 + (x1 - x0) * k for k in (0.05, 0.5, 0.95)]
    zs = [z0 + (z1 - z0) * k for k in (0.05, 0.5, 0.95)]
    if p["piece"].startswith("Corner"):
        # the bank is a quarter cone: keep to the filled part near the corner and along the walls
        pts = [(xx, zz) for xx in xs for zz in zs if math.hypot(xx, zz) < 0.85 * max(x1, z1) or min(xx, zz) < 0.2]
    else:
        pts = [(xx, zz) for xx in xs for zz in zs]
    out = []
    for (lx, lz) in pts:
        lx, lz = lx * s, lz * s
        out.append((p["pos"][0] + lx * math.cos(a) + lz * math.sin(a), p["pos"][2] - lx * math.sin(a) + lz * math.cos(a)))
    return out




def check(p):
    """First reason the placed piece is not acceptable (None when it is): the surface under the visible sand must be the
    piece's own level; no obstacle, route (0.35 m), NPC/landmark point or keep-clear area under it."""
    for (sx, sz) in samples(p):
        if abs(surface_y(sx, sz) - p["pos"][1]) > 0.03:
            return f"surface {surface_y(sx, sz)} under the sand at ({sx:.2f}, {sz:.2f})"
        for (x0, x1, z0, z1, y0, y1, path) in OBST:
            if p["piece"] == "Post" and x0 <= p["pos"][0] <= x1 and z0 <= p["pos"][2] <= z1:
                continue
            if x0 - 0.02 <= sx <= x1 + 0.02 and z0 - 0.02 <= sz <= z1 + 0.02 and y1 > p["pos"][1] + 0.03 and y0 < p["pos"][1] + 0.3:
                return "obstacle " + path
        for (name, a, b) in SEGS:
            if seg_dist(sx, sz, a, b) < 0.35:
                return "route " + name
        for (name, px, pz, rad) in POINTS:
            if math.hypot(sx - px, sz - pz) < rad * 0.8:
                return "point " + name
        for (name, x0, x1, z0, z1) in CLEAR:
            if x0 <= sx <= x1 and z0 <= sz <= z1:
                return "keep-clear " + name
    return None


KIT_LEN = {"Run_L": 1.6, "Run_M": 1.1, "Run_S": 0.7, "Run_Low": 1.5}


if "--check" in sys.argv:
    # validate the installed layout (layout.json as installed) against a fresh scene audit, without re-placing anything
    inst = json.loads((HERE / "layout.json").read_text())
    bad = [(i, p, check(p)) for i, p in enumerate(inst["pieces"])]
    bad = [(i, p, w) for (i, p, w) in bad if w]
    for (i, p, w) in bad:
        print(f"#{i:3d} {p['piece']:9s} {p['source'][:36]:36s} {p['pos']} {w}")
    rep = {"audit": str(AUDIT), "pieces": len(inst["pieces"]), "problems": [{"index": i, "piece": p["piece"], "source": p["source"],
           "why": w} for (i, p, w) in bad]}
    out = HERE / "review" / "validate-installed.json"
    out.write_text(json.dumps(rep, indent=1))
    print(f"checked {len(inst['pieces'])} installed pieces against {AUDIT.name}: {len(bad)} problems -> {out}")
    sys.exit(0)


def place(piece, x, y, z, yaw, scale, src, note=""):
    """Place a piece, shrinking it (uniformly) up to 40 % to fit; returns False when it cannot be placed."""
    why = None
    for k in (1.0, 0.85, 0.72, 0.6):
        p = {"piece": piece, "pos": [round(x, 3), round(y, 3), round(z, 3)], "yaw": round(yaw, 2), "scale": round(scale * k, 3),
             "source": src, "note": note}
        why = check(p)
        if why is None:
            PL.append(p)
            return True
    REJECT.append({"piece": piece, "source": src, "pos": [round(x, 2), round(y, 2), round(z, 2)], "why": why})
    return False


def yaw_of(nx, nz):
    return math.degrees(math.atan2(nx, nz))


def runs_on_span(f, u0, u1, off, t):
    n = f["n"]
    w, l, al = exposure(n)
    kind = f["kind"]
    y = f["y"]
    yaw = yaw_of(*n)
    base = lambda u: (f["a"][0] + t[0] * u + n[0] * off, f["a"][1] + t[1] * u + n[1] * off)
    if kind in ("step", "tread"):
        # small banks against a riser: one at each end of the span (the walked middle is excluded already)
        Lp = 0.7 * 0.75
        if u1 - u0 >= 0.35:
            for (uc, s) in ((u0 + min(0.32, (u1 - u0) / 2), R(0.62, 0.8)),) if u1 - u0 < 1.0 else ((u0 + 0.3, R(0.62, 0.8)), (u1 - 0.3, R(0.62, 0.8))):
                x, z = base(uc)
                place("Run_S", x, y, z, yaw, s, f["id"], kind)
        return
    dens = 0.62 + 0.38 * w + 0.15 * l
    smul = 0.85 + 0.4 * w + 0.1 * l
    if kind == "deck":
        dens *= 0.7
        smul *= 0.8
    if kind == "porch":
        smul *= 0.95
    u = u0 + R(0.0, 0.25)
    while u < u1 - 0.25:
        room = u1 - u + 0.08
        if rng.random() < dens:
            if room >= 1.45 and (w > 0.4 or rng.random() < 0.35):
                piece, s = "Run_L", R(0.9, 1.15) * smul
            elif room >= 1.0:
                piece, s = "Run_M", R(0.85, 1.15) * smul
            else:
                piece, s = "Run_S", R(0.8, 1.1) * smul
            Lp = KIT_LEN[piece] * s * 0.92
            if Lp > room:
                s *= room / Lp
                Lp = room
            if Lp < 0.35:
                break
            x, z = base(u + Lp / 2)
            place(piece, x, y, z, yaw, s, f["id"])
            gap = R(0.0, 0.35) if w > 0.4 else R(0.2, 0.9)
            u += Lp + gap
        else:
            # a bare or dusted stretch: a low broken band, or nothing
            if room >= 1.1 and rng.random() < 0.55:
                s = R(0.75, 1.05)
                Lp = KIT_LEN["Run_Low"] * s * 0.9
                if Lp <= room:
                    x, z = base(u + Lp / 2)
                    place("Run_Low", x, y, z, yaw, s, f["id"], "dust")
                    u += Lp + R(0.1, 0.4)
                    continue
            u += R(0.4, 1.0)


SEG_MAX, SEG_FADE = 4.5, 0.45       # decal segments (non-tiling textures with soft ends) overlap by their fade length


def segments(u0, u1):
    """Split [u0-0.1, u1+0.1] into overlapping decal segments no longer than SEG_MAX."""
    a, b = u0 - 0.1, u1 + 0.1
    n = max(1, math.ceil((b - a - SEG_FADE) / (SEG_MAX - SEG_FADE)))
    L = (b - a + (n - 1) * SEG_FADE) / n
    return [(a + k * (L - SEG_FADE), a + k * (L - SEG_FADE) + L) for k in range(n)]


def flip_uv():
    return [1, 1, 0, 0] if rng.random() < 0.5 else [-1, 1, 1, 0]


def decal_band(f, u0, u1, off, t, banks):
    n = f["n"]
    w, l, al = exposure(n)
    y = f["y"]
    width = (0.75 + 0.35 * w + 0.1 * l) * (0.8 if f["kind"] == "deck" else 1.0)
    for (a, b) in segments(u0, u1):
        um = (a + b) / 2
        cx = f["a"][0] + t[0] * um + n[0] * (off + width / 2)
        cz = f["a"][1] + t[1] * um + n[1] * (off + width / 2)
        DECALS.append({"kind": "band", "pos": [round(cx, 3), y, round(cz, 3)], "fwd": [n[0], 0, n[1]],
                       "size": [round(b - a, 3), round(width, 3), 0.5], "uv": flip_uv(),
                       "opacity": round(min(1.0, 0.65 + 0.3 * w + 0.1 * l + (0.1 if banks else 0)), 2), "source": f["id"]})


def skirt_spans(f):
    offs = foot_offsets(f)
    out, cur = [], None
    for (u, off) in offs:
        ok = off is not None and -0.2 <= off <= 0.25 and not any(e0 <= u <= e1 for (e0, e1) in f["exclude"])
        if ok and (cur is None or abs(off - cur[2]) < 0.06):
            cur = [u, u, off] if cur is None else [cur[0], u, max(cur[2], off)]
        else:
            if cur and cur[1] - cur[0] >= 0.6:
                out.append(tuple(cur))
            cur = [u, u, off] if ok else None
    if cur and cur[1] - cur[0] >= 0.6:
        out.append(tuple(cur))
    return out


def decal_skirt(f, u0, u1, off, t):
    n = f["n"]
    w, l, al = exposure(n)
    y = f["y"]
    H = 0.5 + 0.2 * w
    for (a, b) in segments(u0 + 0.1, u1 - 0.1):
        um = (a + b) / 2
        cx = f["a"][0] + t[0] * um + n[0] * off
        cz = f["a"][1] + t[1] * um + n[1] * off
        DECALS.append({"kind": "skirt", "pos": [round(cx, 3), round(y + H / 2 - 0.02, 3), round(cz, 3)], "fwd": [-n[0], 0, -n[1]],
                       "up": [0, 1, 0], "size": [round(b - a, 3), round(H, 3), 0.36], "uv": flip_uv(),
                       "opacity": round(0.7 + 0.3 * w, 2), "source": f["id"]})


def probed_y(f):
    """The real surface in front of a raised face (porch decks and step treads sit ~4 mm under their nominal level)."""
    if f["y"] <= 0.0:
        return 0.0
    g = sorted(r[5] for r in PR["faces"][f["id"]] if r[5] is not None and abs(r[5] - f["y"]) < 0.02)
    return round(g[len(g) // 2], 4) if g else f["y"]


face_report = {}
for f in FJ["faces"]:
    f["y"] = probed_y(f)
    spans, t, whys = usable_spans(f)
    before = len(PL)
    for (u0, u1, off) in spans:
        runs_on_span(f, u0, u1, off, t)
    banked = len(PL) > before
    # one sand band per run of spans (gaps under 0.6 m that are not doors are bridged)
    merged = []
    for (u0, u1, off) in spans:
        if merged and u0 - merged[-1][1] < 0.6 and not any(e0 < u0 and e1 > merged[-1][1] for (e0, e1) in f["exclude"]):
            merged[-1] = (merged[-1][0], u1, max(merged[-1][2], off))
        else:
            merged.append((u0, u1, off))
    for (u0, u1, off) in merged:
        if f["kind"] in ("step", "tread") or u1 - u0 < 0.5:
            continue
        decal_band(f, u0, u1, off, t, banked)
    # dust skirt on walls taller than a riser: the whole face less its doors and openings
    if f["height"] >= 1.0:
        for (u0, u1, off) in skirt_spans(f):
            decal_skirt(f, u0, u1, off, t)
    face_report[f["id"]] = {"spans": [[round(a, 2), round(b, 2), round(o, 3)] for (a, b, o) in spans], "pieces": len(PL) - before,
                            "blockedBy": sorted({w.split(" ")[0] + " " + w.split(" ", 1)[1].split("/")[0] for w in whys if " " in w})[:8]}

# inside corners
DECK_Y = {f["building"]: f["y"] for f in FJ["faces"] if f["kind"] == "deck"}
for c in FJ["corners"]:
    if c["y"] > 0.0:
        c["y"] = DECK_Y.get(c["building"], c["y"])
    pr = PR["corners"].get(c["id"], {})
    offA = max(pr.get("a") or [0.0]); offB = max(pr.get("b") or [0.0])
    d1, d2 = c["d1"], c["d2"]
    px = c["p"][0] + d2[0] * offA + d1[0] * offB
    pz = c["p"][1] + d2[1] * offA + d1[1] * offB
    # local X along d1 and Z along d2 when that is a proper rotation, else swapped
    if abs(d1[0] - d2[1]) < 1e-3 and abs(d1[1] + d2[0]) < 1e-3:
        zdir = d2
    else:
        zdir = d1
    big = c["size"] == "L"
    piece = "Corner_L" if big else "Corner_S"
    s = R(0.85, 1.15) if big else R(0.9, 1.2)
    reach = (1.0 if big else 0.6) * s
    # the quadrant probe: centre of the bank must be free
    qx, qz = px + (d1[0] + d2[0]) * 0.3 * reach, pz + (d1[1] + d2[1]) * 0.3 * reach
    why = blocked(qx, qz, c["y"])
    if why:
        REJECT.append({"corner": c["id"], "why": why})
        continue
    if not place(piece, px, c["y"], pz, yaw_of(*zdir), s, c["id"], "corner"):
        continue
    reach = (1.0 if big else 0.6) * PL[-1]["scale"]
    # a sand fan decal under the corner (the band decal of each wall runs into it as well)
    DECALS.append({"kind": "sheet", "pos": [round(px + (d1[0] + d2[0]) * 0.45 * reach, 3), c["y"], round(pz + (d1[1] + d2[1]) * 0.45 * reach, 3)],
                   "fwd": [round((d1[0] + d2[0]) / math.sqrt(2), 4), 0, round((d1[1] + d2[1]) / math.sqrt(2), 4)],
                   "size": [round(1.5 * reach, 3), round(1.5 * reach, 3), 0.5], "uv": None, "opacity": 0.7, "source": c["id"]})

# posts: collar with the lee tail downwind
for p in FJ["posts"]:
    x, z = p["p"]
    why = None
    for d in ((0.0, 0.55), (0.0, -0.45), (0.45, 0.0), (-0.45, 0.0)):
        # sample round the footing (relative to the wind frame), ignoring the post's own collider/renderers
        wx, wz = WIND
        sx = x + wx * d[1] + wz * d[0] * 1.0
        sz = z + wz * d[1] - wx * d[0] * 1.0
        for (x0, x1, z0, z1, y0, y1, path) in OBST:
            if x0 <= x <= x1 and z0 <= z <= z1:
                continue                       # the post itself
            if x0 - 0.05 <= sx <= x1 + 0.05 and z0 - 0.05 <= sz <= z1 + 0.05 and y1 > 0.03 and y0 < 0.35:
                why = "obstacle " + path
                break
        if why:
            break
    if not why:
        for (name, a, b) in SEGS:
            if seg_dist(x, z, a, b) < 1.7:
                why = "route " + name
    if why:
        REJECT.append({"post": p["id"], "why": why})
        continue
    s = max(0.9, min(1.25, p["half"] / 0.26)) * R(0.94, 1.06)
    if not place("Post", x, p["y"], z, yaw_of(*WIND), s, p["id"], "post"):
        continue
    s = PL[-1]["scale"]
    DECALS.append({"kind": "post", "pos": [round(x + WIND[0] * 0.4 * s, 3), p["y"], round(z + WIND[1] * 0.4 * s, 3)],
                   "fwd": [WIND[0], 0, WIND[1]], "size": [round(1.4 * s, 3), round(2.0 * s, 3), 0.5], "uv": None, "opacity": 0.75,
                   "source": p["id"]})

# alleys between paired shops: thin sand floors along the funnel
for (x0, x1, zc) in [(-24.9, -14.6, -13.5), (-24.9, -14.6, 13.5), (14.6, 24.9, -13.5), (14.6, 24.9, 13.5)]:
    x = x0 + R(0.4, 0.9)
    while x < x1 - 0.8:
        s = R(0.8, 1.0)
        cx = x + 0.7 * s
        cz = zc + R(-0.06, 0.06)
        if not blocked(cx, cz, 0.0, ignore_routes=False):
            place("Sheet", cx, 0.0, cz, R(-5, 5) + (180 if rng.random() < 0.5 else 0), s, f"alley {zc:+.1f} {x0:+.1f}", "alley")
        x += 1.4 * s + R(0.3, 1.2)
    for k in range(3):
        cx = x0 + (x1 - x0) * (k + 0.5) / 3 + R(-0.3, 0.3)
        DECALS.append({"kind": "sheet", "pos": [round(cx, 3), 0.0, zc], "fwd": [0, 0, 1], "size": [round((x1 - x0) / 3 + 0.8, 3), 1.25, 0.5],
                       "uv": flip_uv(), "opacity": 0.8, "source": f"alley {zc:+.1f} {x0:+.1f}"})

# ------------------------------------------------------------------ validation of the final placements
def footprint(p):
    fp = KIT[p["piece"]]["footprint"]
    s = p["scale"]
    a = math.radians(p["yaw"])
    pts = []
    for (lx, lz) in ((fp[0], fp[2]), (fp[1], fp[2]), (fp[1], fp[3]), (fp[0], fp[3])):
        lx, lz = lx * s, lz * s
        pts.append((p["pos"][0] + lx * math.cos(a) + lz * math.sin(a), p["pos"][2] - lx * math.sin(a) + lz * math.cos(a)))
    return pts


problems = []
for i, p in enumerate(PL):
    for (sx, sz) in samples(p):
        if abs(surface_y(sx, sz) - p["pos"][1]) > 0.03:
            problems.append((i, f"surface {surface_y(sx, sz)} under the sand at ({sx:.2f}, {sz:.2f})"))
            break
        for (x0, x1, z0, z1, y0, y1, path) in OBST:
            if p["piece"] == "Post" and x0 <= p["pos"][0] <= x1 and z0 <= p["pos"][2] <= z1:
                continue
            if x0 - 0.02 <= sx <= x1 + 0.02 and z0 - 0.02 <= sz <= z1 + 0.02 and y1 > p["pos"][1] + 0.03 and y0 < p["pos"][1] + 0.3:
                problems.append((i, "obstacle " + path))
                break
        for (name, a, b) in SEGS:
            if seg_dist(sx, sz, a, b) < 0.35:
                problems.append((i, "route " + name))
                break
        for (name, px, pz, rad) in POINTS:
            if math.hypot(sx - px, sz - pz) < rad * 0.8:
                problems.append((i, "point " + name))
                break
        for (name, x0, x1, z0, z1) in CLEAR:
            if x0 <= sx <= x1 and z0 <= sz <= z1:
                problems.append((i, "keep-clear " + name))
                break
problems = sorted(set(problems))
for i, why in problems:
    print(f"#{i:3d} {PL[i]['piece']:9s} {PL[i]['source'][:36]:36s} {PL[i]['pos']} {why}")

counts = {}
for p in PL:
    counts[p["piece"]] = counts.get(p["piece"], 0) + 1
dcounts = {}
for d in DECALS:
    dcounts[d["kind"]] = dcounts.get(d["kind"], 0) + 1
tris = {lod: sum(KIT[p["piece"]]["lods"][lod] for p in PL) for lod in ("LOD0", "LOD1", "LOD2")}
print(f"{len(PL)} pieces {counts}; {len(DECALS)} decals {dcounts}; rejected {len(REJECT)}; problems {len(problems)}; tris {tris}")

CAMERAS = [
    {"name": "cam_wfd_field_step", "pos": [12.1, 1.62, -6.2], "target": [14.6, 0.15, -8.6], "fov": 55,
     "what": "Field Supply porch front and step corner (windward east-row front), banks and dust band"},
    {"name": "cam_wfd_finery_deck", "pos": [15.4, 2.1, -14.9], "target": [17.9, 0.55, -19.6], "fov": 55,
     "what": "Finery porch deck (windward east-row front): sand at the pier feet, the door and its planters kept clear"},
    {"name": "cam_wfd_alley", "pos": [13.4, 1.62, -12.4], "target": [21.0, 0.1, -13.6], "fov": 50,
     "what": "the Finery / Field Supply alley: sand floor and banks on both walls, side skirts"},
    {"name": "cam_wfd_cross_street", "pos": [-13.4, 1.62, 3.2], "target": [-20.5, 0.15, 5.0], "fov": 55,
     "what": "west cross street along the Tool Exchange side wall (porch riser and old slab foot)"},
    {"name": "cam_wfd_hill_cheek", "pos": [-4.6, 1.62, -12.6], "target": [-2.6, 0.2, -8.2], "fov": 55,
     "what": "hill north stair: cheek corner bank, plinth foot run, stair kept clean"},
    {"name": "cam_wfd_hall_podium", "pos": [-18.6, 1.62, -23.1], "target": [-15.7, 0.2, -27.6], "fov": 55,
     "what": "Vanguard Hall podium west face (windward) and the deck pier corners above"},
    {"name": "cam_wfd_rear_lane", "pos": [-27.4, 1.62, -1.6], "target": [-25.2, 0.15, -8.0], "fov": 55,
     "what": "west service lane: windward rear walls of the west row, a pole collar"},
    {"name": "cam_wfd_lamp", "pos": [10.0, 1.62, -22.8], "target": [12.2, 0.1, -25.2], "fov": 50,
     "what": "avenue utility lamp footing: collar and lee tail"},
]

out = {"source": "art/wall_foot_drifts_20261001/layout.py", "date": "2026-10-01", "wind": list(WIND), "pieces": PL, "decals": DECALS,
       "cameras": CAMERAS, "rejected": REJECT, "faces": face_report, "counts": counts, "decalCounts": dcounts, "triangles": tris,
       "problems": [{"index": i, "why": w} for (i, w) in problems]}
(HERE / "layout.json").write_text(json.dumps(out, indent=1))

if "--plot" in sys.argv:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Polygon
    fig, ax = plt.subplots(figsize=(30, 24), dpi=70)
    for c in A["colliders"]:
        (x, y, z), (sx, sy, sz) = c["center"], c["size"]
        if sx > 30 or sz > 30 or y + sy / 2 < 0.05 or abs(x) > 47 or abs(z) > 44:
            continue
        ax.add_patch(Rectangle((x - sx / 2, z - sz / 2), sx, sz, fc="#bbb" if y + sy / 2 > 0.62 else "#e6dcc0", ec="#777", lw=.3, alpha=.5))
    for (x0, x1, z0, z1, y0, y1, p) in OBST:
        if y1 > 0.03 and y0 < 0.9:
            ax.add_patch(Rectangle((x0, z0), x1 - x0, z1 - z0, fc="none", ec="#c08", lw=.3))
    for (name, x0, x1, z0, z1) in CLEAR:
        ax.add_patch(Rectangle((x0, z0), x1 - x0, z1 - z0, fc="none", ec="green", lw=1, ls="--"))
    for (name, a, b) in SEGS:
        ax.plot([a[0], b[0]], [a[1], b[1]], color="dodgerblue", lw=2)
    for (name, px, pz, rad) in POINTS:
        ax.plot(px, pz, "b*")
    for f in FJ["faces"]:
        ax.plot([f["a"][0], f["b"][0]], [f["a"][1], f["b"][1]], color="k", lw=.6)
    for d in DECALS:
        fx, fz = d["fwd"][0], d["fwd"][2]
        if d["kind"] == "skirt":
            tx, tz = -fz, fx
            L = d["size"][0]
            ax.plot([d["pos"][0] - tx * L / 2, d["pos"][0] + tx * L / 2], [d["pos"][2] - tz * L / 2, d["pos"][2] + tz * L / 2], color="#6b4", lw=2.5, alpha=.6)
            continue
        L, Wd = d["size"][0], d["size"][1]
        tx, tz = fz, -fx
        c0 = (d["pos"][0], d["pos"][2])
        pts = [(c0[0] + tx * u * L / 2 + fx * v * Wd / 2, c0[1] + tz * u * L / 2 + fz * v * Wd / 2) for (u, v) in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        ax.add_patch(Polygon(pts, closed=True, fc="#f3d58a", ec="none", alpha=.35))
    bad = {i for i, _ in problems}
    col = {"Run_L": "#b5651d", "Run_M": "#d2873c", "Run_S": "#e8a85c", "Run_Low": "#f0c890", "Corner_L": "#8b4513", "Corner_S": "#a0522d",
           "Post": "#704214", "Sheet": "#e0b878"}
    for i, p in enumerate(PL):
        ax.add_patch(Polygon(footprint(p), closed=True, fc="red" if i in bad else col[p["piece"]], ec="k", lw=.3, alpha=.9))
    for cam in CAMERAS:
        ax.annotate("", xy=(cam["target"][0], cam["target"][2]), xytext=(cam["pos"][0], cam["pos"][2]), arrowprops=dict(arrowstyle="->", color="purple"), annotation_clip=True)
        ax.text(cam["pos"][0], cam["pos"][2], cam["name"][8:], fontsize=8, color="purple", clip_on=True)
    ax.set_aspect("equal"); ax.grid(True, lw=.3)
    (HERE / "review").mkdir(exist_ok=True)
    zooms = {"all": (-34, 46, -42, 34), "east": (11, 28, -24, -3), "west": (-28, -11, 3, 24), "hill": (-12, 12, -13, 12),
             "hall": (-18, -2, -38, -20)}
    for zn, (x0, x1, z0, z1) in zooms.items():
        ax.set_xlim(x0, x1); ax.set_ylim(z0, z1)
        fig.savefig(HERE / f"review/layout-map{'' if zn == 'all' else '-' + zn}.png", bbox_inches="tight")
    print("plot written")
