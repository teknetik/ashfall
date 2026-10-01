"""Wall-foot faces of the Ward's avenue-ring buildings (1 October 2026): plain Python, no Blender imports.

Shared by probe_faces.py (Blender: measures where each face really is at its foot, against the shipped building
models) and layout.py (places the drift kit and decals). Coordinates are Unity world metres (X east, Y up, Z north).

A face is a straight wall foot: endpoints a -> b on the ground plane, outward normal n, the surface it stands on (y),
the wall height above that surface (for the dust skirt), its kind and spans to keep clear (u along a -> b, metres).
Inside corners are listed separately: the corner point, the two wall directions running away from it, and y.

Sources of the geometry: the shop sites in Editor/WardShopsPass.cs and the shop records
(Art/WardShops/Models/<shop>.json: recesses = doors/bays, mounts = rear air conditioners), the hall-district author
constants (porch 3.6 m deep, deck 0.5, step 0.8 x 4.2 at 0.25, body half-width 3.88 at the foot, rear at -6.98),
the booth constants (author_basic_general.py), Vanguard Hall's saved colliders, and hill_layout.py (plinth face 7.0,
stairs 4 m wide with 0.42 m cheeks out to 10.6 m).
"""
import json, math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SHOPS = ROOT / "unity/AthenHill/Assets/AthenHill/Art/WardShops/Models"

# shop sites: key -> (model, root x, root z, yaw). West row (yaw 90) fronts face +X, east row (yaw -90) face -X.
SITES = {"relay_works": ("RelayWorks", -18.1, -18.0, 90), "air_water": ("AirWater", -18.1, -9.0, 90),
         "tool_exchange": ("ToolExchange", -18.1, 9.0, 90), "salvage": ("Salvage", -18.1, 18.0, 90),
         "finery": ("Finery", 18.1, -18.0, -90), "field_supply": ("FieldSupply", 18.1, -9.0, -90),
         "repairs": ("Repairs", 18.1, 9.0, -90), "thread_hide": ("ThreadHide", 18.1, 18.0, -90)}
BOOTH = ("BasicGeneral", 8.0, 15.1, 0)
HALL = ("VanguardHall", -10.0, -26.55, 0)
HILL = ("WardHill", 0.0, 0.0, 0)

PORCH, STEP_D, STEP_HW, BODY_HW, REAR = 3.6, 0.8, 2.1, 3.88, -6.98


def rot(yaw, x, z):
    """Unity yaw rotation of a local (x, z) offset (yaw 90 turns local +Z to world +X)."""
    a = math.radians(yaw)
    return (x * math.cos(a) + z * math.sin(a), -x * math.sin(a) + z * math.cos(a))


def to_world(site, x, z):
    _, rx, rz, yaw = site
    dx, dz = rot(yaw, x, z)
    return (rx + dx, rz + dz)


def face(fid, building, a, b, n, y, kind, height, exclude=(), tags=()):
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    return {"id": fid, "building": building, "a": [round(a[0], 3), round(a[1], 3)], "b": [round(b[0], 3), round(b[1], 3)],
            "n": [round(n[0], 4), round(n[1], 4)], "y": y, "kind": kind, "height": height, "length": round(L, 3),
            "exclude": [list(e) for e in exclude], "tags": list(tags)}


def corner(cid, building, p, d1, d2, y, size="L"):
    return {"id": cid, "building": building, "p": [round(p[0], 3), round(p[1], 3)], "d1": [round(d1[0], 4), round(d1[1], 4)],
            "d2": [round(d2[0], 4), round(d2[1], 4)], "y": y, "size": size}


def local_face(site, key, fid, la, lb, ln, y, kind, height, exclude=(), tags=()):
    a, b = to_world(site, *la), to_world(site, *lb)
    n = rot(site[3], *ln)
    return face(f"{key}/{fid}", key, a, b, n, y, kind, height, exclude, tags)


def local_corner(site, key, cid, lp, ld1, ld2, y, size="L"):
    return corner(f"{key}/{cid}", key, to_world(site, *lp), rot(site[3], *ld1), rot(site[3], *ld2), y, size)


def shop_faces(key):
    site = SITES[key]
    rec = json.loads((SHOPS / f"{key}.json").read_text())
    F, C = [], []
    rx = {"front": [], "rear": [], "left": [], "right": []}
    for r in rec.get("recesses", []):
        rx[r["face"]].append(tuple(sorted(r["u"])))
    # air conditioners on stands behind the rear wall (local x)
    ac = [m["pos"][0] for m in rec.get("mounts", []) if "air conditioner" in m["name"].lower() and m["pos"][2] < -6.5]
    hw, P, S = BODY_HW, PORCH, STEP_HW
    # --- street level (y 0)
    F.append(local_face(site, key, "porch_front_l", (-hw, P), (-S, P), (0, 1), 0.0, "porch", 0.5))
    F.append(local_face(site, key, "porch_front_r", (S, P), (hw, P), (0, 1), 0.0, "porch", 0.5))
    F.append(local_face(site, key, "step_front", (-S, P + STEP_D), (S, P + STEP_D), (0, 1), 0.0, "step", 0.25,
                        exclude=[(0.62, 2 * S - 0.62)], tags=["walk"]))
    F.append(local_face(site, key, "step_end_l", (-S, P + STEP_D), (-S, P), (-1, 0), 0.0, "step", 0.25))
    F.append(local_face(site, key, "step_end_r", (S, P), (S, P + STEP_D), (1, 0), 0.0, "step", 0.25))
    C.append(local_corner(site, key, "step_corner_l", (-S, P), (-1, 0), (0, 1), 0.0, "S"))
    C.append(local_corner(site, key, "step_corner_r", (S, P), (1, 0), (0, 1), 0.0, "S"))
    # side faces: u runs from a to b; local "left" (-x) runs front -> rear, "right" (+x) rear -> front
    def side_ex(face_name, a_z, b_z):
        out = []
        for (u0, u1) in rx[face_name]:          # recess u spans along local z (depth axis)
            za, zb = sorted((u0, u1))
            ua, ub = sorted((abs(za - a_z), abs(zb - a_z)))
            out.append((ua - 0.3, ub + 0.3))
        return out
    F.append(local_face(site, key, "side_l", (-hw, P), (-hw, REAR), (-1, 0), 0.0, "wall", 4.0, exclude=side_ex("left", P, REAR)))
    F.append(local_face(site, key, "side_r", (hw, REAR), (hw, P), (1, 0), 0.0, "wall", 4.0, exclude=side_ex("right", REAR, P)))
    # rear: a = local +x end, b = local -x end; u = hw - x
    rex = [(hw - u1 - 0.35, hw - u0 + 0.35) for (u0, u1) in rx["rear"]] + [(hw - x - 0.7, hw - x + 0.7) for x in ac]
    F.append(local_face(site, key, "rear", (hw, REAR), (-hw, REAR), (0, -1), 0.0, "wall", 4.0, exclude=rex))
    # --- porch deck (y 0.5): the facade foot, doors and bays kept clear
    fex = [(u0 + hw - 0.3, u1 + hw + 0.3) for (u0, u1) in rx["front"]]
    F.append(local_face(site, key, "facade", (-hw, 0.0), (hw, 0.0), (0, 1), 0.5, "deck", 3.5, exclude=fex))
    # tread pockets against the porch riser at the step ends (y 0.25)
    F.append(local_face(site, key, "tread_l", (-S, P), (-S + 0.62, P), (0, 1), 0.25, "tread", 0.25))
    F.append(local_face(site, key, "tread_r", (S - 0.62, P), (S, P), (0, 1), 0.25, "tread", 0.25))
    return F, C


def booth_faces():
    key, site = "basic_general", BOOTH
    F, C = [], []
    PX, PZ0, PZ1, SX, SZ1 = 2.83, -1.83, 2.30, 1.6, 3.10
    F.append(local_face(site, key, "porch_front_l", (-PX, PZ1), (-SX, PZ1), (0, 1), 0.0, "porch", 0.5))
    F.append(local_face(site, key, "porch_front_r", (SX, PZ1), (PX, PZ1), (0, 1), 0.0, "porch", 0.5))
    F.append(local_face(site, key, "step_front", (-SX, SZ1), (SX, SZ1), (0, 1), 0.0, "step", 0.25,
                        exclude=[(0.55, 2 * SX - 0.55)], tags=["walk"]))
    C.append(local_corner(site, key, "step_corner_l", (-SX, PZ1), (-1, 0), (0, 1), 0.0, "S"))
    C.append(local_corner(site, key, "step_corner_r", (SX, PZ1), (1, 0), (0, 1), 0.0, "S"))
    F.append(local_face(site, key, "side_l", (-PX, PZ1), (-PX, PZ0), (-1, 0), 0.0, "porch", 0.5))
    F.append(local_face(site, key, "side_r", (PX, PZ0), (PX, PZ1), (1, 0), 0.0, "porch", 0.5))
    F.append(local_face(site, key, "rear", (PX, PZ0), (-PX, PZ0), (0, -1), 0.0, "porch", 0.5))
    return F, C


def hall_faces():
    """Vanguard Hall: the podium (x -15.94..-4.06, z -36.05..-24.3, top 0.5) at street level, its front and rear steps,
    and on the deck the body walls between the corner piers (piers 2 m square at x -14.75/-5.25, z -26.8/-34.8)."""
    key = "vanguard_hall"
    F, C = [], []
    x0, x1, z0, z1 = -15.94, -4.06, -36.05, -24.3
    fs0, fs1 = -13.25, -6.75           # front step x span (z -24.3 .. -23.5)
    rs0, rs1 = -9.0, -7.5              # rear step x span (z -36.85 .. -36.05)
    F.append(face(f"{key}/podium_w", key, (x0, z1), (x0, z0), (-1, 0), 0.0, "porch", 0.5))
    F.append(face(f"{key}/podium_e", key, (x1, z0), (x1, z1), (1, 0), 0.0, "porch", 0.5))
    F.append(face(f"{key}/podium_n_w", key, (x0, z1), (fs0, z1), (0, 1), 0.0, "porch", 0.5))
    F.append(face(f"{key}/podium_n_e", key, (fs1, z1), (x1, z1), (0, 1), 0.0, "porch", 0.5))
    F.append(face(f"{key}/podium_s_e", key, (x1, z0), (rs1, z0), (0, -1), 0.0, "porch", 0.5))
    F.append(face(f"{key}/podium_s_w", key, (rs0, z0), (x0, z0), (0, -1), 0.0, "porch", 0.5))
    F.append(face(f"{key}/front_step", key, (fs0, -23.5), (fs1, -23.5), (0, 1), 0.0, "step", 0.25,
                  exclude=[(0.7, (fs1 - fs0) - 0.7)], tags=["walk"]))
    C.append(corner(f"{key}/step_corner_w", key, (fs0, z1), (-1, 0), (0, 1), 0.0, "S"))
    C.append(corner(f"{key}/step_corner_e", key, (fs1, z1), (1, 0), (0, 1), 0.0, "S"))
    # deck: body walls between the piers (pier faces at x -13.75 / -6.25 and z -27.8 / -33.8)
    F.append(face(f"{key}/deck_front_w", key, (-13.75, -26.55), (-11.45, -26.55), (0, 1), 0.5, "deck", 6.0, exclude=[(1.75, 2.4)]))
    F.append(face(f"{key}/deck_front_e", key, (-8.55, -26.55), (-6.25, -26.55), (0, 1), 0.5, "deck", 6.0, exclude=[(-0.1, 0.55)]))
    F.append(face(f"{key}/deck_west", key, (-15.0, -27.8), (-15.0, -33.8), (-1, 0), 0.5, "deck", 6.0))
    F.append(face(f"{key}/deck_east", key, (-5.0, -33.8), (-5.0, -27.8), (1, 0), 0.5, "deck", 6.0))
    F.append(face(f"{key}/deck_rear", key, (-6.25, -35.05), (-13.75, -35.05), (0, -1), 0.5, "deck", 6.0))
    for (cid, p, d1, d2) in [("pier_wf_front", (-13.75, -26.55), (1, 0), (0, 1)), ("pier_ef_front", (-6.25, -26.55), (-1, 0), (0, 1)),
                             ("pier_wf_side", (-15.0, -27.8), (0, -1), (-1, 0)), ("pier_wr_side", (-15.0, -33.8), (0, 1), (-1, 0)),
                             ("pier_ef_side", (-5.0, -27.8), (0, -1), (1, 0)), ("pier_er_side", (-5.0, -33.8), (0, 1), (1, 0)),
                             ("pier_wr_rear", (-13.75, -35.05), (1, 0), (0, -1)), ("pier_er_rear", (-6.25, -35.05), (-1, 0), (0, -1))]:
        C.append(corner(f"{key}/{cid}", key, p, d1, d2, 0.5, "S"))      # the deck is only 0.87 m wide beside the body
    return F, C


def hill_faces():
    """The hill plinth's four retaining walls (face 7.0) at street level with the three stairs and their cheeks."""
    key = "ward_hill"
    F, C = [], []
    E, CO, SL = 7.0, 2.42, 10.6
    # (side, outward normal, has stair). -Z "north", +Z "south", +X "west" stair; -X face has none.
    for side, (nx, nz), stair in [("north", (0, -1), True), ("south", (0, 1), True), ("west", (1, 0), True), ("east", (-1, 0), False)]:
        tx, tz = nz, -nx                       # along the face (right-hand of the outward normal, seen from above)
        cx, cz = nx * E, nz * E
        p = lambda u: (cx + tx * u, cz + tz * u)
        if stair:
            F.append(face(f"{key}/{side}_a", key, p(-E), p(-CO), (nx, nz), 0.0, "plinth", 1.4))
            F.append(face(f"{key}/{side}_b", key, p(CO), p(E), (nx, nz), 0.0, "plinth", 1.4))
            # cheek outer faces (from the plinth to the bottom of the stair) and the corners they make with the plinth
            for sgn in (-1, 1):
                tdir = (tx * sgn, tz * sgn)
                c0 = (cx + tx * sgn * CO, cz + tz * sgn * CO)
                c1 = (c0[0] + nx * (SL - E), c0[1] + nz * (SL - E))
                a, b = (c0, c1) if sgn > 0 else (c1, c0)
                F.append(face(f"{key}/{side}_cheek_{'p' if sgn > 0 else 'm'}", key, a, b, tdir, 0.0, "cheek", 1.0))
                C.append(corner(f"{key}/{side}_cheek_corner_{'p' if sgn > 0 else 'm'}", key, c0, tdir, (nx, nz), 0.0, "L"))
        else:
            F.append(face(f"{key}/{side}", key, p(-E), p(E), (nx, nz), 0.0, "plinth", 1.4))
    return F, C


def posts():
    """Post footings: (id, x, z, footing half-size, y). Avenue utility lamps, night-life lamp posts, service-lane poles."""
    P = [("lamp_avenue_00", 35.0, -5.0, 0.26), ("lamp_avenue_01", 35.0, 5.0, 0.26), ("lamp_avenue_02", 12.0, -25.0, 0.3),
         ("lamp_avenue_03", -12.0, 25.0, 0.3), ("lamp_avenue_04", -32.0, 5.0, 0.27),
         ("lamp_terminals", 8.0, -16.8, 0.23), ("lamp_hall_corner", -2.5, -31.2, 0.23), ("lamp_lattice", 5.1, -39.4, 0.23),
         ("lamp_hill_benches", -8.0, 0.2, 0.23), ("lamp_apron_south", 44.0, -14.0, 0.23), ("lamp_apron_north", 44.6, 18.5, 0.23)]
    for sx in (1, -1):
        for z in (4.5, 13.5, 22.5, -4.5, -13.5, -22.5):
            x = 28.4 * sx
            if sx == 1 and z == -22.5:
                x = 27.4
            zz = 23.75 if (sx == -1 and z == 22.5) else (-22.25 if (sx == -1 and z == -22.5) else z)
            P.append((f"pole_{'e' if sx > 0 else 'w'}_{zz:+.2f}", x, zz, 0.35))
    return [{"id": f"post/{i}", "p": [x, z], "half": h, "y": 0.0} for (i, x, z, h) in P]


def all_faces():
    F, C = [], []
    for k in SITES:
        f, c = shop_faces(k)
        F += f; C += c
    for fn in (booth_faces, hall_faces, hill_faces):
        f, c = fn()
        F += f; C += c
    return F, C, posts()


if __name__ == "__main__":
    F, C, P = all_faces()
    (HERE / "faces.json").write_text(json.dumps({"faces": F, "corners": C, "posts": P}, indent=1))
    print(len(F), "faces,", len(C), "corners,", len(P), "posts")
