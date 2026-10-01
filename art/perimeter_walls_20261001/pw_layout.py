"""Ward perimeter walls: wall lines, module specs and the placement plan (1 October 2026). Pure Python (no Blender).

Shared by author_perimeter_walls.py (builds each unique module once, three LODs) and the Unity pass
(Editor/PerimeterWallsPass.cs reads layout.json). Run it on its own to write layout.json:
    python3 pw_layout.py

Module convention (Unity metres): a module runs along local +X from x = 0 to its length L; its city ("inner") face is
the +Z face at z = +T/2, the outer face at z = -T/2; y = 0 is the city paving. A placement yaw of theta maps local +Z to
the wall's inward normal N = (sin theta, 0, cos theta) and local +X to A = (N.z, 0, -N.x).

The saved wall colliders are kept unchanged (COL_BLD_boundary_wall*, COL_BLD_west_wall*, COL_BLD_berms_gate_wall_*,
COL_BLD_boundary_side): visual breaches stay blocked. Old visuals are retired (inactive), not deleted.
"""
import json, math
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ---------------------------------------------------------------- wall kinds
# NS: north/south curtain walls (5 m body, crenellated parapet, 1 m thick, piers every 7 m on both faces)
# EX: the +X rampart (legacy "west wall", 7.4 m, 3 m thick, stepped buttresses on the city face, wall walk, outer merlons)
# BW: the low Outer Berms walls on -X and the strip wall east of the gate (3 m, 2 m thick, saddleback coping)
KINDS = {
    "NS": dict(T=1.0, H=5.0, bay=7.0),
    "EX": dict(T=3.0, H=7.4, bay=5.0),
    "BW": dict(T=2.0, H=3.0, bay=5.0),
}

# variants (see author_perimeter_walls.py for what each builds):
#   intact a/b/c   weathered, chipped, runoff, light old scarring
#   repair         paler replacement stones in a patch, bolted steel plate over a crack, repointing
#   merlons        (NS/EX) parapet partly broken: a merlon gone, one sheared, fallen stones at the foot
#   coping         (BW) coping stones displaced / missing, one fallen
#   impact         heavy old battle damage: shell craters with the rubble core exposed, scars, soot
#   siege          (EX) impact + broken merlons + plates (the gate flanks)
#   collapse       upper wall fallen in a stepped break, rubble cones, field-repaired (sandbags / sheet screen)
#   breach         (BW) wall down to the footing over ~3 m, closed with HESCO, sandbags and welded sheet
#   fill           plain end/corner piece of a given length


def mod_id(kind, variant, L, start="pier", end="none"):
    s = f"PW_{kind}_{variant}_{L:.2f}".replace(".", "p")
    if start != "pier":
        s += "_s" + start[0]
    if end != "none":
        s += "_e" + end[0]
    return s


class Wall:
    def __init__(self, name, kind, p0, n, slots):
        """p0: world (x, z) of the module-chain start on the wall centreline; n: inward normal (x, z) unit;
        slots: list of (length, variant, start, end)."""
        self.name, self.kind, self.p0, self.n, self.slots = name, kind, p0, n, slots

    @property
    def yaw(self):
        return math.degrees(math.atan2(self.n[0], self.n[1])) % 360

    @property
    def along(self):
        return (self.n[1], -self.n[0])

    def placements(self):
        out = []
        s = 0.0
        ax, az = self.along
        for i, (L, variant, start, end) in enumerate(self.slots):
            x = self.p0[0] + ax * s
            z = self.p0[1] + az * s
            out.append(dict(wall=self.name, slot=i, module=mod_id(self.kind, variant, L, start, end), kind=self.kind,
                            variant=variant, length=L, start=start, end=end, pos=[round(x, 4), 0.0, round(z, 4)],
                            yaw=round(self.yaw, 3), span=[round(s, 3), round(s + L, 3)]))
            s += L
        return out


def ns_wall(name, p0, n, bays):
    """Bays of 7 m between piers from -56 to 56, 4 m end pieces to the corners (+-60)."""
    slots = [(4.0, "fill", "end", "none")]
    slots += [(7.0, v, "pier", "none") for v in bays]
    slots += [(4.0, "fill", "pier", "end")]
    return Wall(name, "NS", p0, n, slots)


WALLS = [
    # south wall: city to +Z, runs west -> east from the -X corner
    ns_wall("South wall", (-60.0, -44.5), (0.0, 1.0),
            # -56   -49     -42        -35     -28       -21      -14 lane  -7       0 lattice  7        14        21       28        35      42(+X) 49(strip)
            ["intact_a", "intact_b", "merlons", "intact_c", "repair", "intact_a", "impact", "repair", "intact_b", "collapse", "merlons", "intact_c",
             "repair", "intact_a", "intact_b", "merlons"]),
    # north wall: city to -Z, runs east -> west from the strip corner
    ns_wall("North wall", (60.0, 44.5), (0.0, -1.0),
            # 56     49(+X)     42        35         28       21        14         7          0         -7        -14        -21       -28      -35       -42      -49
            ["intact_c", "intact_a", "intact_b", "merlons", "intact_c", "repair", "intact_a", "intact_b", "impact", "intact_c", "merlons", "repair",
             "intact_a", "intact_b", "collapse_n", "intact_c"]),
    # +X rampart, south of the District gate: city to -X, runs south -> north from inside the south wall. Buttresses keep
    # the old rhythm (z = -43.7 + 5k) so the notices, pipes and fittings mounted between them stay clear.
    # The run ends 1.15 m inside the District gate arch pier (arches x 46.3-49.7, z -5.75..5.75 and 6.25..17.75).
    Wall("East rampart south", "EX", (48.0, -44.9), (-1.0, 0.0),
         [(1.2, "fill", "end", "none")] + [(5.0, v, "pier", "none") for v in
                                           ["intact_a", "intact_b", "merlons", "repair", "intact_a", "impact", "intact_b"]]
         + [(4.1, "siege", "pier", "none")]),
    # +X rampart, north of the gate: starts 1.15 m inside the arch pier (no buttress), buttresses at z = 22, 27, 32, 37
    # (as before; none at 42, where Watchtower 3 stands against the face)
    Wall("East rampart north", "EX", (48.0, 16.6), (-1.0, 0.0),
         [(5.4, "siege", "none", "none")] + [(5.0, v, "pier", "none") for v in ["repair", "merlons", "intact_a", "intact_b"]]
         + [(2.9, "fill", "none", "end")]),
    # between the two gate arches: only the 0.5 m slot between the arch piers shows (z 5.75..6.25)
    Wall("Gate infill", "EX", (48.0, 5.2), (-1.0, 0.0), [(1.6, "gate", "none", "none")]),
    # -X Outer Berms wall, north of the West Gate portal: city to +X, runs north -> south from the north wall
    Wall("Berms wall north", "BW", (-59.0, 44.0), (1.0, 0.0),
         [(4.4, "fill", "none", "none")] + [(5.0, v, "pier", "none") for v in
                                            ["intact_a", "coping", "intact_b", "repair", "impact", "intact_c", "intact_a"]]),
    # -X Outer Berms wall, south of the portal: the old siege breach (story beat): worst next to the gate, the collapse
    # and breach clear of the perimeter dwelling at z -27..-21 and the wreck plinth at z -8.5..-5.5
    Wall("Berms wall south", "BW", (-59.0, -2.5), (1.0, 0.0),
         [(5.0, "impact", "none", "none")] + [(5.0, v, "pier", "none") for v in
                                              ["collapse", "breach", "impact", "intact_b", "coping", "intact_c", "repair"]]
         + [(1.5, "fill", "pier", "none")]),
    # strip wall east of the gate (x 58..60), seen through the arches: city (strip) to -X, runs south -> north
    Wall("Strip wall", "BW", (59.0, -44.0), (-1.0, 0.0),
         [(3.0, "fill", "none", "none")] + [(5.0, v, "pier", "none") for v in
                                            ["intact_a", "intact_b", "intact_c", "coping", "intact_a", "intact_b", "intact_c", "repair",
                                             "intact_a", "impact", "coping", "intact_b", "intact_c", "intact_a", "repair", "intact_b", "intact_c"]]),
]

# ground outside the -X wall falls away (Outer Berms terrain grid, art/west_gate_20260926/berms-ground-grid.json):
# about -0.07 m at 1 m out, -0.35 at 2 m, -0.66 at 3 m, -0.97 at 4 m
def berms_ground(d):
    return -0.31 * max(0.0, d - 0.78)


def modules():
    """Unique module specs {id: spec}."""
    specs = {}
    for w in WALLS:
        for p in w.placements():
            m = p["module"]
            if m not in specs:
                specs[m] = dict(id=m, kind=p["kind"], variant=p["variant"], length=p["length"], start=p["start"], end=p["end"],
                                uses=0, walls=[])
            specs[m]["uses"] += 1
            if w.name not in specs[m]["walls"]:
                specs[m]["walls"].append(w.name)
    # BW modules on the Berms side get the falling outer ground
    for s in specs.values():
        s["outer_slope"] = s["kind"] == "BW" and any(n.startswith("Berms") for n in s["walls"])
    return specs


def layout():
    pl = [p for w in WALLS for p in w.placements()]
    total = {}
    for w in WALLS:
        total[w.name] = round(sum(s[0] for s in w.slots), 3)
    return dict(source="art/perimeter_walls_20261001/pw_layout.py", date="2026-10-01", placements=pl, wallLengths=total,
                totalLength=round(sum(total.values()), 2), modules=modules(),
                retire=RETIRE, retirePrefixes=RETIRE_PREFIXES, keptColliders=KEPT_COLLIDERS)


# old wall visuals (render-chunk sources under AuthoredWorld): retired (inactive), colliders kept
RETIRE = [
    "AuthoredWorld/BLD_boundary_wall", "AuthoredWorld/BLD_boundary_wall.001",
    "AuthoredWorld/BLD_boundary_coping", "AuthoredWorld/BLD_boundary_coping.001",
    "AuthoredWorld/BLD_boundary_side",
    "AuthoredWorld/BLD_west_wall", "AuthoredWorld/BLD_west_wall.001", "AuthoredWorld/BLD_west_wall.002",
    "AuthoredWorld/BLD_west_wall_coping", "AuthoredWorld/BLD_west_wall_coping.001", "AuthoredWorld/BLD_west_wall_coping.002",
    "AuthoredWorld/BLD_berms_gate_wall_north", "AuthoredWorld/BLD_berms_gate_wall_south",
]
RETIRE_PREFIXES = [
    "AuthoredWorld/BLD_boundary_pier", "AuthoredWorld/BLD_boundary_recess",
    "AuthoredWorld/BLD_wall_buttress", "AuthoredWorld/BLD_wall_inset", "AuthoredWorld/BLD_wall_signal",
    "AuthoredWorld/AAA Environment Dressing/Wall shadow proxy",
]
KEPT_COLLIDERS = [
    "AuthoredWorld/COL_BLD_boundary_wall", "AuthoredWorld/COL_BLD_boundary_wall.001", "AuthoredWorld/COL_BLD_boundary_side",
    "AuthoredWorld/COL_BLD_west_wall", "AuthoredWorld/COL_BLD_west_wall.001", "AuthoredWorld/COL_BLD_west_wall.002",
    "AuthoredWorld/COL_BLD_berms_gate_wall_north", "AuthoredWorld/COL_BLD_berms_gate_wall_south",
]

if __name__ == "__main__":
    L = layout()
    (HERE / "layout.json").write_text(json.dumps(L, indent=1))
    print(len(L["placements"]), "placements,", len(L["modules"]), "unique modules,", L["totalLength"], "m of wall")
    for w, l in L["wallLengths"].items():
        print(f"  {w}: {l} m")
    for m, s in sorted(L["modules"].items()):
        print(f"  {m:40s} x{s['uses']:2d}  {', '.join(s['walls'])}")
