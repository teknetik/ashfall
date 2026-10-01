#!/usr/bin/env python3
"""West Gate arches layout (1 Oct 2026): plain Python. Writes layout.json for Unity (Editor/WestGateArchesPass.cs)
and validates every footprint against a fresh scene audit (StreetDressingAudit.DumpBatch):

  * the gate fittings' colliders (the leaves' sealing box, the guard stones) vs the saved colliders (only the Meshy
    arch itself and the rampart's own boxes may touch them), the player spawn capsule, NPC stand points, walker/mechanic
    routes, landmarks and interaction points
  * the ground decals vs NPC points (they never block anything; recorded for completeness)
  * the cart passage left between the guard stones

Coordinates: Unity world metres (X east, Y up, Z north). The two arches sit in the +X rampart at x 46.3-49.7, centred
z 0 (arch A, the spawn arch) and z 12 (arch B). Gate prefabs are authored in a local frame with the origin at
(48, 0, zc) and world axes (author_gate_arches.py).

Run: uv run --with matplotlib python layout.py [audit.json]   (default unity/evidence/west-gate-arches/20261001/audit-before.json)
"""
import json, math, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
AUDIT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "unity/evidence/west-gate-arches/20261001/audit-before.json"
REC = json.loads((HERE / "gate-arches.json").read_text())
D = REC["dims"]
JZ = D["JZ"]

GATES = [dict(key="A", pos=[48.0, 0.0, 0.0], name="West gate arch A (spawn, wicket)"),
         dict(key="B", pos=[48.0, 0.0, 12.0], name="West gate arch B")]

# ------------------------------------------------------------------ decals (local to the gate origin)
# kind -> material: ruts/jamb = this pass's textures; sand/grime = the West Gate kit's; scuffs = the weathering atlas
DECALS = []


def decal(kind, pos, size, fwd, up=None, opacity=1.0, fade=(60, 85), note="", gate=None, uv=None):
    DECALS.append(dict(kind=kind, pos=[round(v, 3) for v in pos], size=[round(v, 3) for v in size], fwd=fwd,
                       up=up, opacity=opacity, angleFade=list(fade), note=note, gate=gate, uv=uv))


x_th = D["threshold"][0]                  # threshold plate starts here (local x)
L_RUT = 6.6
for key in ("all",):
    # cart ruts on the paving from the apron to the threshold (v = 1 at the threshold), projected down
    decal("ruts", [x_th - L_RUT / 2, 0.0, 0.0], [2.4, L_RUT, 0.5], fwd=[1, 0, 0], opacity=0.95,
          note="two worn wheel tracks, 1.45 m gauge, fading out on the apron")
    # boot and cart scuffs in the passage in front of the leaves (weathering atlas, scuff quadrant)
    decal("scuffs", [-0.35, 0.0, 0.0], [4.2, 1.6, 0.5], fwd=[1, 0, 0], opacity=0.75, note="scuffs in the passage")
    # wind-blown sand caught against the leaf foot on the threshold plate
    decal("sand", [0.42, 0.02, 0.0], [4.8, 0.55, 0.4], fwd=[1, 0, 0], opacity=0.8, note="sand against the leaves")
    # grime skirt on the lower leaves (vertical projector towards +x; dark edge at the foot)
    decal("grime", [0.45, 0.45, 0.0], [4.9, 0.9, 0.8], fwd=[1, 0, 0], up=[0, -1, 0], opacity=0.7, fade=(50, 75),
          note="dirt splash on the lower leaves")
    # hub and load scrapes on both jambs at the tunnel mouth
    for s in (1, -1):
        decal("jamb", [-0.35, 0.72, s * (JZ - 0.28)], [1.2, 0.75, 0.6], fwd=[0, 0, s], opacity=0.85, fade=(50, 75),
              note="hub scrapes on the jamb")

# projector boxes (depth = size z, centred on pos) must reach both the frame face (x 0.605) and the boards (x 0.705)
# painted stencils (atlas WGA_DecalStencil: top half KEEP CLEAR, bottom half "1" | "2"; uv = [scale u, scale v, bias u, bias v])
# KEEP CLEAR across both leaves' upper panels (painted after assembly: it runs over rails, braces and straps);
# the gate number on the transom, left of the lamp
decal("stencil", [0.55, 3.40, 0.0], [3.6, 0.45, 0.5], fwd=[1, 0, 0], up=[0, 1, 0], opacity=0.85, fade=(50, 75),
      note="KEEP CLEAR stencil", uv=[1.0, 0.5, 0.0, 0.5])
decal("stencil", [0.35, 4.72, 0.95], [1.1, 0.275, 0.4], fwd=[1, 0, 0], up=[0, 1, 0], opacity=0.9, fade=(50, 75),
      note="gate number 1", gate="A", uv=[0.5, 0.5, 0.0, 0.0])
decal("stencil", [0.35, 4.72, 0.95], [1.1, 0.275, 0.4], fwd=[1, 0, 0], up=[0, 1, 0], opacity=0.9, fade=(50, 75),
      note="gate number 2", gate="B", uv=[0.5, 0.5, 0.5, 0.0])

LIGHT = dict(type="spot", color=[1.0, 0.78, 0.52], intensity=3.0, range=7.5, angle=125, inner=60, shadows=False,
             note="caged bulkhead on the transom (one per arch), on the Ward lighting clock (practical + night only)")

# ------------------------------------------------------------------ review cameras (player eye 1.65 m)
CAMS = [
    dict(name="cam_wga_spawn", pos=[43.0, 1.65, 0.6], target=[48.6, 2.6, 0.0], fov=60,
         note="what the player sees on turning round at the spawn"),
    dict(name="cam_wga_front", pos=[37.5, 1.65, 6.0], target=[48.0, 3.4, 6.0], fov=60, note="both arches from the apron"),
    dict(name="cam_wga_close", pos=[45.6, 1.65, -1.8], target=[48.62, 1.4, 0.4], fov=60, note="arch A leaves, three-quarter"),
    dict(name="cam_wga_wicket", pos=[47.0, 1.5, -0.9], target=[48.62, 1.15, -1.36], fov=60, note="wicket door, arm's length"),
    dict(name="cam_wga_head", pos=[45.4, 1.65, 12.9], target=[48.66, 5.4, 12.0], fov=60,
         note="arch B: transom, head grille, repair plate"),
    dict(name="cam_wga_threshold", pos=[45.2, 1.65, 9.6], target=[48.3, 0.1, 12.4], fov=60,
         note="arch B: threshold plate, ruts, guard stone"),
]


# ------------------------------------------------------------------ validation
def world_box(g, c, size):
    gx, gy, gz = g["pos"]
    return (gx + c[0] - size[0] / 2, gx + c[0] + size[0] / 2, gy + c[1] - size[1] / 2, gy + c[1] + size[1] / 2,
            gz + c[2] - size[2] / 2, gz + c[2] + size[2] / 2)


def gate_colliders(g):
    gu = D["guard"]
    out = [("leaves", world_box(g, (0.66, 3.45, 0.0), (0.52, 6.9, 2 * JZ + 0.02)))]
    for s, n in ((1, "N"), (-1, "S")):
        x0, x1 = gu["x"]
        out.append(("guard" + n, world_box(g, ((x0 + x1) / 2, 0.36, s * (gu["z_in"] + gu["z_out"]) / 2), (x1 - x0, 0.72, gu["z_out"] - gu["z_in"]))))
    return out


def seg_dist(px, pz, a, b):
    ax, az = a
    bx, bz = b
    dx, dz = bx - ax, bz - az
    t = max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / (dx * dx + dz * dz + 1e-9)))
    return math.hypot(px - ax - dx * t, pz - az - dz * t)


def box_dist(b, px, pz):
    dx = max(b[0] - px, 0, px - b[1])
    dz = max(b[4] - pz, 0, pz - b[5])
    return math.hypot(dx, dz)


def main():
    A = json.loads(AUDIT.read_text())
    problems, notes = [], []
    # neighbours we expect to touch: the Meshy arch (MeshCollider), the rampart's own boxes
    EXPECT = ("District rebuild/District gate", "AuthoredWorld/COL_BLD_west_wall", "Ward west gate arches")
    cols = []
    for c in A["colliders"]:
        if c["path"] == "Player":
            continue
        cx, cy, cz = c["center"]
        sx, sy, sz = c["size"]
        cols.append((c["path"], cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, cz - sz / 2, cz + sz / 2, c["type"]))
    routes, points = {}, []
    for m in A["markers"]:
        parts = m["path"].split("/")
        if len(parts) == 2 and parts[0].endswith(" route"):
            routes.setdefault(parts[0], []).append((m["pos"][0], m["pos"][2]))
        elif len(parts) == 2 and parts[0] in ("Colonists", "Landmarks"):
            points.append((m["path"], m["pos"][0], m["pos"][2], 1.0))
        elif m["path"] in ("Player", "npc_yard_mechanic"):
            points.append((m["path"], m["pos"][0], m["pos"][2], 0.9))
    segs = [(n, p[i], p[(i + 1) % len(p)]) for n, p in routes.items() for i in range(len(p))]
    checked = 0
    for g in GATES:
        for name, b in gate_colliders(g):
            checked += 1
            for (cn, x0, x1, y0, y1, z0, z1, typ) in cols:
                if x1 < b[0] or x0 > b[1] or z1 < b[4] or z0 > b[5] or y1 < b[2] + 0.02 or y0 > b[3]:   # resting on the ground is fine
                    continue
                if any(cn.startswith(e) for e in EXPECT):
                    notes.append(f"{g['key']}/{name}: touches {cn} ({typ}) as expected")
                    continue
                problems.append(f"{g['key']}/{name}: overlaps collider {cn} ({typ})")
            for pn, px, pz, rad in points:
                d = box_dist(b, px, pz)
                if d < rad:
                    problems.append(f"{g['key']}/{name}: {d:.2f} m from point {pn} (< {rad})")
            for rn, a, c in segs:
                d = min(seg_dist(x, z, a, c) for x, z in ((b[0], b[4]), (b[0], b[5]), (b[1], b[4]), (b[1], b[5]), ((b[0] + b[1]) / 2, (b[4] + b[5]) / 2)))
                if d < 1.0:
                    problems.append(f"{g['key']}/{name}: {d:.2f} m from route {rn}")
        gu = D["guard"]
        notes.append(f"{g['key']}: cart passage between the guard stones {2 * gu['z_in']:.2f} m (tunnel {2 * JZ:.2f} m)")
    # spawn: player capsule (r 0.35) at its saved position
    sp = next((m["pos"] for m in A["markers"] if m["path"] == "Player"), [43, 0, 0])
    for g in GATES:
        for name, b in gate_colliders(g):
            d = box_dist(b, sp[0], sp[2])
            notes.append(f"spawn to {g['key']}/{name}: {d:.2f} m")
            if d < 1.5:
                problems.append(f"{g['key']}/{name}: {d:.2f} m from the spawn")
    out = dict(source="art/west_gate_arches_20261001/layout.py", date="2026-10-01", audit=str(AUDIT.relative_to(ROOT)),
               gates=GATES, decals=DECALS, light=LIGHT, cameras=CAMS,
               validation=dict(checked=checked, problems=problems, notes=notes))
    (HERE / "layout.json").write_text(json.dumps(out, indent=1))
    for n in notes:
        print("  ", n)
    for p in problems:
        print("PROBLEM", p)
    print(f"{checked} collider footprints checked, {len(DECALS)} decals per both arches, {len(CAMS)} review cameras, {len(problems)} problems")
    try:
        plot(A, cols, points, segs)
    except ImportError:
        pass


def plot(A, cols, points, segs):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, ax = plt.subplots(figsize=(10, 10))
    for (cn, x0, x1, y0, y1, z0, z1, typ) in cols:
        if x1 < 34 or x0 > 52 or z1 < -10 or z0 > 22:
            continue
        ax.add_patch(Rectangle((x0, z0), x1 - x0, z1 - z0, fc="none", ec="#888", lw=.6))
    for g in GATES:
        for name, b in gate_colliders(g):
            ax.add_patch(Rectangle((b[0], b[4]), b[1] - b[0], b[5] - b[4], fc="#c84", ec="#842", alpha=.6))
        for d in DECALS:
            if d["up"] is None and d["fwd"] == [1, 0, 0]:
                w, l = d["size"][0], d["size"][1]
                x, z = g["pos"][0] + d["pos"][0], g["pos"][2] + d["pos"][2]
                ax.add_patch(Rectangle((x - l / 2, z - w / 2), l, w, fc="#46a", alpha=.12, ec="#46a", lw=.4))
    for pn, px, pz, rad in points:
        if 34 < px < 52 and -10 < pz < 22:
            ax.plot(px, pz, "g^")
            ax.text(px + .2, pz + .2, pn.split("/")[-1], fontsize=7, color="g")
    for rn, a, c in segs:
        if 30 < a[0] < 52:
            ax.plot([a[0], c[0]], [a[1], c[1]], "-", color="#3a8", lw=1)
    for c in CAMS:
        ax.plot(c["pos"][0], c["pos"][2], "bs", ms=4)
        ax.annotate("", xy=(c["target"][0], c["target"][2]), xytext=(c["pos"][0], c["pos"][2]), arrowprops=dict(arrowstyle="->", color="b", lw=.6))
        ax.text(c["pos"][0], c["pos"][2] - .5, c["name"].replace("cam_wga_", ""), fontsize=7, color="b")
    ax.set_xlim(34, 52)
    ax.set_ylim(-10, 22)
    ax.set_aspect("equal")
    ax.grid(True, lw=.3)
    ax.set_title("West Gate arches: colliders (orange), saved colliders (grey), decals (blue), cameras, routes, NPCs")
    (HERE / "review").mkdir(exist_ok=True)
    fig.savefig(HERE / "review/layout-map.png", dpi=90)


if __name__ == "__main__":
    main()
