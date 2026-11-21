#!/usr/bin/env python3
"""Greybox stand-ins and the bench layout for the Steady Hands bench (bench agent, 20 Nov 2026; Milestone 2: real ids).

Writes, deterministically:
  unity/AthenHill/Assets/AthenHill/Data/Assembly/Greybox/<family>.parts.json   (CONTRACT.md parts.json + a "grey" block)
  art/steady_hands_bench_20261120/data/layout.json                              (places, homes, lamps, shots)

SEAM.md: the art's names are the names. Every id here (parts, marks, paths, zones, params) is the id the real family
uses (`<family>/export/parts.json`, or its PARTS.md where it has not exported). Ids the art does not have yet are listed
by `--report` against the exported files. A place whose id is `<part>/<mark>` is bound to that mark of the real family
(the numbers here are then only the greybox fallback); an id starting `place.` has no mark in the art.

Bench space is the SS_Workbench prefab's own: metres, +Y up, +Z towards the player, origin at the floor under the bench
centre. The player stands at +Z looking at -Z, so the player's RIGHT is -X. Positions follow model-bench's plan
(fixtures/PARTS.md; its X is the player's right: bench x = -X, z = -Y, y = Z + 0.8637).
Part poses are in their parent part's space (family space for top-level parts; greybox families sit at the bench origin).

  python3 make_greybox.py [--check] [--report]
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.normpath(os.path.join(HERE, ".."))
REPO = os.path.normpath(os.path.join(ART, "..", ".."))
OUT = os.path.join(REPO, "unity/AthenHill/Assets/AthenHill/Data/Assembly/Greybox")
LAYOUT = os.path.join(ART, "data", "layout.json")

WT = 0.8637           # worktop
Y0 = WT + 0.008       # top of the rubber work surface
FLAT = [-90, 0, 0]    # lays a thing that is thin along its Z flat, its top towards the far side

families, params, places, home, lamps, shots = {}, {}, [], {}, [], []
layout_params, parents, cards, tips, grabs = {}, {}, [], {}, {}


def box(cx, cy, cz, sx, sy, sz):
    return {"box": [cx, cy, cz, sx, sy, sz]}


def cyl(cx, cy, cz, r, length, axis="z"):
    return {"cyl": [cx, cy, cz, r, length, axis]}


def part(pid, label, shapes, pos=(0, 0, 0), rot=(0, 0, 0), kind="part", parent=None, material="steel", mass="light",
         clear=None, held_by=(), symmetry=1, tol_mm=8, tol_deg=25, item=None, **grey):
    family, name = pid.split(".", 1)
    node = family + "_" + name
    p = {"id": pid, "node": node, "label": label, "kind": kind, "parent": parent, "item": item, "material": material,
         "mass": mass, "held_by": list(held_by), "seat": {"symmetry": symmetry, "tol_mm": tol_mm, "tol_deg": tol_deg}}
    g = {"pos": list(pos), "rot": list(rot), "shapes": shapes}
    # a wipe over the whole part (SEAM.md section 10): as found until an action's effect "~part/wipe" reveals it
    if "wipes" in grey:
        p["wipes"] = [{"id": w, "zone": None} for w in grey.pop("wipes")]
    if clear is not None:
        p["seat"]["clear"] = node + "__clear"
        g["clear"] = list(clear)
    g.update(grey)
    p["grey"] = g
    families.setdefault(family, []).append(p)
    return p


def fastener(p, bit, turns, holds=()):
    p["kind"] = "fastener"
    p["fastener"] = {"bit": bit, "turns": turns, "holds": list(holds)}
    return p


def tool(pid, label, shapes, length, tags, pos=(0, 0, 0), rot=(0, 0, 0), parent=None, clear=None, tip=None, grab=None, material="steel", mass="light", **grey):
    p = part(pid, label, shapes, pos=pos, rot=rot, kind="tool", parent=parent, material=material, mass=mass, symmetry=0, clear=clear,
             tip=tip if tip else [0, 0, length / 2, 0, 0, 1], grab=grab if grab else [0, 0, -length / 4], **grey)
    p["tool"] = {"verbs": [], "tip": p["node"] + "__tip", "tags": list(tags)}
    return p


def place(pid, on, pos, rot=(0, 0, 0), accepts=(), material="rubber", approach=(0, 0.035, 0), radius=0.03, tol_mm=0, tol_deg=0, symmetry=-1,
          held_by="", hold_above=0.5, rest_of="", mark=None, real=None, turn=None):
    """A place. `<part>/<mark>` ids bind to that mark in the real family; `#variant` gives a second pose at the same mark.
    `rest_of` puts the place at that part's own rest pose (its pocket, or where it lies as built), whatever the family's source."""
    # `mark` names a mark of the art other than the id's own (the art has seat_servo on the vise; the table's place is seat_work#servo).
    # `real` is for a place with no mark: where it is once the toolkit is the art's, and that a real part is set down on it.
    mark = mark if mark is not None else (pid.split("#")[0] if "/" in pid else "")
    places.append({"id": pid, "mark": mark, "rest_of": rest_of, "on": on, "pos": list(pos), "rot": list(rot), "accepts": list(accepts), "material": material,
                   "approach": list(approach), "radius": radius, "tol_mm": tol_mm, "tol_deg": tol_deg, "symmetry": symmetry, "held_by": held_by,
                   "hold_above": hold_above, **({"real": real} if real else {}), **({"turn": turn} if turn else {})})


def param(pid, target=None, move=(0, 0, 0), turn=(0, 0, 0), as_found=0, **grey):
    family = pid.split(".")[0]
    g = {"target": target, "move": list(move), "turn": list(turn), "as_found": as_found}
    g.update(grey)
    params.setdefault(family, []).append({"id": pid, "node": family + "_rig", "action": pid.split(".")[-1] + "_param", "type": "slide", "min": 0, "max": 1,
                                          "unit": "", "continuous": False, "grey": g})


# ====================================================================================================== fixtures
part("fixtures.worksurface", "Work surface", [box(0, -0.004, 0, 0.90, 0.008, 0.55)], pos=(0, Y0, 0.303), kind="fixture", material="rubber", color=[.11, .12, .12],
     marks={"lead_zero": [0.10, 0, 0.26, 0, 1, 0, 0.006], "lead_length": [0.02, 0, 0.26, 0, 1, 0, 0.006]})
part("fixtures.workmat", "Work mat", [box(0, -0.003, 0, 0.36, 0.006, 0.26)], pos=(-0.03, Y0 + 0.006, 0.195), kind="fixture", material="canvas", color=[.07, .07, .07])
part("fixtures.partsmat", "Parts mat", [box(0, -0.0015, 0, 0.44, 0.003, 0.20)], pos=(-0.03, Y0 + 0.003, 0.44), kind="fixture", material="rubber", color=[.20, .22, .20])
part("fixtures.vise", "Bench vise", [box(0, 0.02, 0, 0.15, 0.04, 0.26), box(0, 0.09, -0.065, 0.12, 0.09, 0.03), cyl(0, 0.07, 0.05, 0.010, 0.16, "z")],
     pos=(0.325, Y0, 0.33), kind="fixture", mass="heavy", color=[.23, .27, .30])
part("fixtures.vise_slide", "Vise jaw", [box(0, 0, 0, 0.12, 0.09, 0.03)], pos=(0, 0.09, 0.055), kind="fixture", parent="fixtures.vise", color=[.26, .30, .33])
part("fixtures.vise_screw", "Vise handle", [cyl(0, 0, 0, 0.006, 0.13, "x"), cyl(0, 0, -0.012, 0.012, 0.024, "z")], pos=(0, 0.07, 0.152), kind="fixture",
     parent="fixtures.vise", mass="heavy", clear=(0, 0, 0.03), symmetry=0, color=[.62, .60, .55])
param("fixtures.vise_jaw", target="fixtures.vise_slide", move=(0, 0, -0.090))   # gap = 90 x (1 - value) mm, as the real one
part("fixtures.cradle", "Cradle stand", [box(0, 0.01, 0, 0.18, 0.02, 0.09), box(-0.02, 0.0775, 0, 0.012, 0.115, 0.06), box(0.075, 0.0775, 0, 0.012, 0.115, 0.06)],
     pos=(-0.335, Y0, 0.30), kind="fixture", material="wood", color=[.38, .27, .17])
part("fixtures.dish", "Magnetic dish", [cyl(0, 0.008, 0, 0.054, 0.016, "y")], pos=(-0.36, Y0, 0.455), kind="fixture", color=[.55, .56, .57])
part("fixtures.pad", "Insulated pad", [box(0, 0.012, 0, 0.13, 0.024, 0.104)], pos=(-0.36, Y0, 0.125), kind="fixture", material="ceramic", color=[.62, .30, .10])
part("fixtures.board", "Card board", [box(0, 0.18, -0.01, 0.60, 0.36, 0.02), box(0, 0.01, 0.03, 0.60, 0.02, 0.13)], pos=(0.76, WT, -0.29), kind="fixture", material="wood", color=[.40, .30, .20])
part("fixtures.schematic", "Schematic", [box(0, 0, 0, 0.26, 0.20, 0.004)], pos=(-0.13, 0.22, 0.004), kind="fixture", parent="fixtures.board", material="paper", color=[.72, .68, .56])
for i in range(8):
    part("fixtures.schematic_r%d" % i, "Schematic region %d" % i, [box(0, 0, 0, 0.054, 0.080, 0.002)], pos=(-0.093 + 0.062 * (i % 4), 0.045 - 0.09 * (i // 4), 0.003),
         kind="fixture", parent="fixtures.schematic", material="paper", color=[.50, .47, .38], emissive=True)
    param("fixtures.schematic_s%d" % i, glow="fixtures.schematic_r%d" % i, glow_color=[.9, .75, .35])
part("fixtures.tray", "Salvage tray", [box(0, 0.004, 0, 0.30, 0.008, 0.20), box(0, 0.018, -0.096, 0.30, 0.03, 0.008), box(0, 0.018, 0.096, 0.30, 0.03, 0.008)],
     pos=(-0.64, WT, 0.06), kind="fixture", color=[.36, .40, .36])
part("fixtures.bin", "Scrap bin", [cyl(0, 0.07, 0, 0.10, 0.14, "y")], pos=(0.95, WT, -0.07), kind="fixture", color=[.25, .20, .16])
part("fixtures.jar", "Solvent jar", [cyl(0, 0.06, 0, 0.045, 0.12, "y")], pos=(0.76, WT, -0.03), kind="fixture", material="glass", color=[.45, .58, .60])
part("fixtures.tester", "Bench tester", [box(0, 0.055, 0, 0.16, 0.11, 0.075)], pos=(0.58, WT, -0.035), kind="fixture", color=[.30, .33, .30])
tool("fixtures.tester_probes", "Tester probes", [cyl(0, 0, 0.02, 0.003, 0.09, "z"), cyl(0.012, 0, 0.02, 0.003, 0.09, "z")], 0.13, ["tool:probe"], pos=(0, 0.118, 0.01), rot=(0, 180, 0),
     parent="fixtures.tester", clear=(0, 0.03, 0), material="copper")
part("fixtures.tester_lamp", "Tester lamp", [cyl(0, 0, 0, 0.012, 0.01, "z")], pos=(0.05, 0.08, 0.04), kind="fixture", parent="fixtures.tester", material="glass", color=[.10, .08, .03], emissive=True)
lamps.append({"part": "fixtures.tester_lamp", "color": [2.0, 1.3, 0.3], "as_found": 0})
part("fixtures.press", "Nanite press", [box(0, 0.03, 0, 0.26, 0.06, 0.22), box(0, 0.24, -0.08, 0.10, 0.36, 0.06), box(0, 0.40, -0.01, 0.12, 0.05, 0.16)], pos=(-0.56, WT, -0.22),
     kind="fixture", mass="heavy", color=[.72, .58, .12])
part("fixtures.press_lever", "Press lever", [cyl(0, 0.10, 0, 0.012, 0.22, "y")], pos=(-0.09, 0.30, 0.02), kind="fixture", parent="fixtures.press", mass="heavy", clear=(0.03, 0, 0), symmetry=0, color=[.20, .20, .20])
param("fixtures.press_lever", target="fixtures.press_lever", turn=(70, 0, 0))
part("fixtures.press_vents", "Press vents", [box(0, 0, 0, 0.08, 0.02, 0.004)], pos=(0, 0.032, 0.112), kind="fixture", parent="fixtures.press", color=[.06, .10, .10], emissive=True)
lamps.append({"part": "fixtures.press_vents", "color": [0.2, 1.6, 1.7], "as_found": 0})
part("fixtures.mouldrack", "Mould rack", [box(0, 0.075, 0, 0.11, 0.15, 0.13)], pos=(-0.80, WT, -0.19), kind="fixture", color=[.30, .30, .28])
part("fixtures.mould_tang", "Pistol-tang mould", [box(0, 0.015, 0, 0.13, 0.03, 0.07)], pos=(0, 0.165, 0), parent="fixtures.mouldrack", mass="medium", clear=(0, 0.05, 0), tol_mm=14,
     color=[.42, .42, .40], grab=[0, 0.015, 0], zones={"cavity": [0, 0.031, 0, 0.11, 0.004, 0.05]})
# the charge as poured (SEAM.md section 10: a sub-part of the mould, hidden until the nanites are poured over the offcuts)
part("fixtures.mould_charge", "Charge", [box(0, 0, 0, 0.10, 0.008, 0.044), box(0.012, 0.005, 0.004, 0.05, 0.004, 0.02)], pos=(0, 0.034, 0), kind="consumable", parent="fixtures.mould_tang",
     material="alloy", mass="tiny", color=[.46, .47, .48])
home["fixtures.mould_charge"] = "gone"
part("fixtures.lamp", "Cure lamp", [cyl(0, 0.01, 0, 0.055, 0.02, "y"), cyl(0, 0.13, 0, 0.008, 0.24, "y")], pos=(-0.30, WT, -0.03), kind="fixture", color=[.25, .25, .27])
part("fixtures.lamp_head", "Cure lamp head", [cyl(0.10, 0, 0, 0.008, 0.20, "x"), cyl(0.20, -0.02, 0, 0.045, 0.04, "y")], pos=(0, 0.25, 0), rot=(0, 46.3, 0), kind="fixture", parent="fixtures.lamp", clear=(0, 0.03, 0),
     symmetry=0, color=[.30, .30, .34], emissive=True)
param("fixtures.lamp_arm", target="fixtures.lamp_head", turn=(0, -80, 0))
lamps.append({"part": "fixtures.lamp_head", "color": [0.5, 1.0, 1.9], "as_found": 0})
# (at the front edge by the vise: the right end of the bench is the toolkit's once it is the art's)
part("fixtures.holster", "Holster hook", [box(0, 0.02, 0, 0.05, 0.04, 0.12)], pos=(0.22, WT, 0.565), kind="fixture", color=[.30, .22, .15])

# places on the fixtures (ids are the real marks)
# (21 Nov 14:10 model-bench turned this pose mark so the cell faces the front; the bench's own `turn: 180` is dropped)
place("fixtures.workmat/seat_pistol", "fixtures.workmat", (0.05, 0.0185, 0.0), FLAT, ["pistol.frame"], tol_mm=18, tol_deg=30, radius=0.07)
place("fixtures.workmat/seat_grip", "fixtures.workmat", (-0.105, 0.0135, -0.115), FLAT, ["grip.core"], tol_mm=16, tol_deg=30, radius=0.05)
place("fixtures.workmat/seat_grip#over", "fixtures.workmat", (-0.105, 0.0135, -0.015), (90, 0, 0), ["grip.core"], tol_mm=16, tol_deg=30, radius=0.05)
# (turned half round so the gimbal's leads, which leave it towards -Z of its frame, lie towards the player: stage 3 trims, strips and tins them;
#  tipped 30 degrees so they rise off the mat: they leave the cradle sloping down, and the strip pulled off them went into the mat)
place("fixtures.workmat/seat_small", "fixtures.workmat", (-0.11, 0.025, 0.07), (30, 180, 0), ["servo.gimbal_cradle"], tol_mm=18, symmetry=0, radius=0.04)
place("fixtures.vise/seat_work", "fixtures.vise", (0.05, 0.147, -0.032), (0, 0, 180), ["pistol.frame"], material="steel", approach=(0, 0.07, 0), tol_mm=16, tol_deg=30,
      radius=0.06, held_by="fixtures.vise_jaw", hold_above=0.50)
# The servo's seam clips are on opposite faces (model-bench 17:45: clip_3 and the dusty side on -Y, clips 1 and 2 on +Y), and the vise
# clamps across those faces: it is clamped as the art's seat_servo holds it for the dust and clip 3, then turned round in the vise
# (`#servo_turned`, the same mark turned half round) for clips 1 and 2. One way only each, so the turn is the player's.
place("fixtures.vise/seat_work#servo", "fixtures.vise", (0, 0.115, -0.015), (0, 0, 0), ["servo.case_body"], material="steel", approach=(0, 0.07, 0), tol_mm=16, symmetry=1, tol_deg=30,
      radius=0.06, held_by="fixtures.vise_jaw", hold_above=0.15, mark="fixtures.vise/seat_servo")
place("fixtures.vise/seat_work#servo_turned", "fixtures.vise", (0, 0.115, -0.015), (0, 180, 0), ["servo.case_body"], material="steel", approach=(0, 0.07, 0), tol_mm=16, symmetry=1, tol_deg=30,
      radius=0.06, held_by="fixtures.vise_jaw", hold_above=0.15, mark="fixtures.vise/seat_servo", turn=180)
place("fixtures.vise/seat_work#plate", "fixtures.vise", (0, 0.156, -0.0461), (90, 0, 0), ["materials.sheet_a_plate"], material="steel", approach=(0, 0.07, 0), tol_mm=16, symmetry=2,
      radius=0.05, held_by="fixtures.vise_jaw", hold_above=0.85)
place("fixtures.vise/seat_work#sheets", "fixtures.vise", (0, 0.16, -0.0461), (-90, 180, 0), ["materials.sheet_a"], material="steel", approach=(0, 0.07, 0), tol_mm=16, symmetry=2,
      radius=0.06, held_by="fixtures.vise_jaw", hold_above=0.85)
place("fixtures.vise/anvil", "fixtures.vise", (0, 0.137, -0.068), (0, 90, 0), ["pistol.housing_pin"], material="steel", tol_mm=16, symmetry=0, radius=0.025)
place("fixtures.vise/seat_work#strap", "fixtures.vise", (0, 0.16, -0.0487), (90, 0, 0), ["materials.sheet_a_strap", "materials.sheet_b_strap", "materials.strap_bent_1", "materials.strap_bent"], material="steel", approach=(0, 0.07, 0),
      tol_mm=16, symmetry=2, radius=0.05, held_by="fixtures.vise_jaw", hold_above=0.85)
place("fixtures.vise/seat_work#core", "fixtures.vise", (-0.045, 0.19, -0.032), (-90, 0, 0), ["grip.core"], material="steel", approach=(0, 0.07, 0), tol_mm=16, radius=0.05,
      held_by="fixtures.vise_jaw", hold_above=0.55)
# (muzzle to the left, out over the end of the bench: the other way round it stands between the eye and the work mat)
place("fixtures.cradle/seat_frame", "fixtures.cradle", (0.07, 0.125, 0), (0, 180, 0), ["pistol.frame"], material="wood", radius=0.06, tol_mm=16)
place("fixtures.pad/seat_cell", "fixtures.pad", (0, 0.036, 0), FLAT, ["pistol.cell"], material="ceramic", radius=0.05, tol_mm=18)
for i in range(12):
    place("fixtures.dish/slot_%02d" % i, "fixtures.dish", (-0.03 + 0.02 * (i % 4), 0.018, -0.02 + 0.02 * (i // 4)), FLAT, ["*"], material="steel", radius=0.05, tol_mm=40, symmetry=0)
place("fixtures.partsmat/seat_pistol_wrap", "fixtures.partsmat", (-0.17, 0.027, 0.055), (-90, 0, 90), ["pistol.wrap"], tol_mm=20, symmetry=0)
mat = {"seat_pistol_scale_l": (-0.17, -0.045, ["pistol.scale_l"], (-90, 0, 90), 2), "seat_pistol_scale_r": (-0.12, -0.045, ["pistol.scale_r"], (-90, 0, 90), 2),
       "seat_pistol_housing": (-0.07, -0.045, ["pistol.housing"], (-90, 0, 90), 2), "seat_servo_case_top": (0.03, -0.045, ["servo.case_lid"], (0, 0, 0), 2),
       "seat_servo_rotor": (0.11, -0.045, ["servo.gimbal_rotor"], (0, 0, 0), 0), "seat_servo_circlip": (0.15, -0.045, ["servo.circlip"], (0, 0, 0), 0),
       "seat_servo_bobbin": (0.195, -0.045, ["materials.bobbin"], (0, 0, 0), 0),
       "seat_pistol_pin": (-0.10, 0.05, ["pistol.housing_pin"], (0, 90, 0), 0), "seat_pistol_spring": (-0.06, 0.05, ["pistol.housing_spring"], (0, 0, 90), 0),
       "seat_servo_board": (0.02, 0.055, ["servo.board"], (0, 0, 0), 0), "seat_servo_resistor": (0.09, 0.05, ["materials.resistor"], (0, 0, 0), 0)}
for name, (x, z, acc, rot, sym) in mat.items():
    place("fixtures.partsmat/" + name, "fixtures.partsmat", (x, 0.008, z), rot, acc, tol_mm=14, symmetry=sym)
place("fixtures.board/seat_card_before", "fixtures.board", (0.13, 0.20, 0.004), (0, 0, 0), ["pistol.card_a"], material="wood", radius=0.07)
place("fixtures.board/seat_card_after", "fixtures.board", (0.245, 0.20, 0.004), (0, 0, 0), ["pistol.card_b"], material="wood", radius=0.07)
place("fixtures.tray/seat_servo", "fixtures.tray", (0.08, 0.036, 0.0), (0, 12, 0), ["servo.case_body"], material="steel", tol_mm=25, symmetry=2, radius=0.05)
# (sheet A lies on sheet B in the tray: it is the one the job takes first)
place("fixtures.tray/seat_alloy", "fixtures.tray", (-0.07, 0.013, -0.03), (0, -8, 0), ["materials.sheet_a"], material="steel", tol_mm=25, symmetry=2, radius=0.05)
place("fixtures.tray/seat_alloy#b", "fixtures.tray", (-0.075, 0.010, -0.02), (0, 6, 0), ["materials.sheet_b"], material="steel", tol_mm=25, symmetry=2, radius=0.05)
place("fixtures.tray/seat_vial", "fixtures.tray", (-0.09, 0.021, 0.06), (0, 0, 90), ["materials.vial"], material="steel", tol_mm=25, symmetry=0)
place("fixtures.bin/seat_scrap", "fixtures.bin", (0, 0.15, 0), (0, 0, 0), ["*"], material="steel", radius=0.09, tol_mm=70, tol_deg=180, symmetry=0)
place("fixtures.jar/seat_swirl", "fixtures.jar", (0, 0.13, 0), (0, 0, 0), ["servo.gimbal_cradle"], material="glass", radius=0.05, tol_mm=30, symmetry=0)
place("fixtures.jar/seat_swirl#core", "fixtures.jar", (0.045, 0.19, 0), (0, 0, 0), ["grip.core"], material="glass", radius=0.05, tol_mm=30, tol_deg=60, symmetry=0)
place("fixtures.press/seat_mould", "fixtures.press", (0, 0.06, 0.02), (0, 0, 0), ["fixtures.mould_tang"], material="steel", tol_mm=14, tol_deg=15, radius=0.05)
# places the art has no mark for (README: "Places with no mark")
# (probe of 21:30 on the real families: the art's toolkit unrolls over x 0.78..1.09, z 0.23..0.53 with its mallet and oil bottle at
# x -0.64..-0.48 on the left, where the stand-in tools that fill it also lie; so with it the servo stands in the gap right of the
# vise and the rest moves up to the vise's side of the toolkit. `rest_on`: a real part is set down there, not put by its origin.)
place("place.entry.pistol", "", (0.72, WT + 0.0185, 0.47), FLAT, ["pistol.frame"], radius=0.07, real={"pos": [0.67, WT + 0.0185, 0.47], "rest_on": True, "surface": WT}, mark="fixtures.worksurface/entry_pistol")
place("place.entry.roll", "", (0.76, WT, 0.33), (0, 90, 0), ["tools.roll"], radius=0.06, real={"pos": [0.95, WT, 0.38], "rot": [0, 0, 0], "rest_on": True, "surface": WT})
# once unrolled the roll stays where it lies (its own mechanism holds it there: nobody carries off an open roll of tools)
place("place.roll", "", (0, 0, 0), accepts=["tools.roll"], material="rubber", radius=0.08, tol_mm=40, tol_deg=40, rest_of="tools.roll", held_by="tools.roll_unroll", hold_above=0.5)
place("place.entry.servo", "", (1.00, WT, 0.36), (0, 90, 0), ["servo.case_body"], radius=0.05, real={"pos": [0.52, WT, 0.20], "rest_on": True, "surface": WT}, mark="fixtures.worksurface/entry_servo")
place("place.entry.sheet_a", "", (0.56, WT + 0.0045, 0.50), (0, 0, 0), ["materials.sheet_a"], radius=0.05, real={"pos": [0.50, WT + 0.0045, 0.50], "rest_on": True, "surface": WT + 0.0025}, mark="fixtures.worksurface/entry_sheet_a")
place("place.entry.sheet_b", "", (0.565, WT + 0.0015, 0.495), (0, 9, 0), ["materials.sheet_b"], radius=0.05, real={"pos": [0.505, WT + 0.0015, 0.495], "rest_on": True, "surface": WT}, mark="fixtures.worksurface/entry_sheet_b")
place("place.entry.vial", "", (0.50, WT + 0.012, 0.42), (0, 0, 90), ["materials.vial"], radius=0.03, real={"pos": [0.47, WT + 0.012, 0.40], "rest_on": True, "surface": WT}, mark="fixtures.worksurface/entry_vial")
place("place.bench.stray", "", (0.10, Y0 + 0.012, 0.50), (0, 35, 0), ["materials.vial", "pistol.housing_spring", "servo.circlip", "servo.gimbal_retainer"], radius=0.03, symmetry=0, tol_mm=20,
      real={"when": "fixtures", "pos": [0.33, Y0 + 0.012, 0.545]}, mark="fixtures.worksurface/seat_stray")   # (the art's parts mat has the wrap where the stand-ins' stray place is)
place("place.holster", "fixtures.holster", (0, 0.062, 0), FLAT, ["pistol.frame"], material="wood", tol_mm=25, tol_deg=40, radius=0.07, mark="fixtures.holster/seat_pistol")
place("place.mat.retainer", "fixtures.partsmat", (0.13, 0.004, 0.05), (0, 0, 0), ["servo.gimbal_retainer"], radius=0.02, symmetry=0, tol_mm=16,
      real={"when": "fixtures", "pos": [-0.212, 0.003, 0.045], "rest_on": True}, mark="fixtures.partsmat/seat_retainer")

# ====================================================================================================== tools
part("tools.roll", "Field Toolkit", [cyl(0, 0.04, 0, 0.04, 0.30, "z")], pos=(-0.78, WT, 0.36), material="canvas", mass="medium", item="field_toolkit",
     clear=(0, 0, 0.05), symmetry=2, tol_mm=30, tol_deg=30, color=[.42, .37, .26], grab=[0, 0.04, 0])
part("tools.roll_flat", "Toolkit roll, open", [box(0, 0.003, 0, 0.56, 0.006, 0.30)], kind="fixture", parent="tools.roll", material="canvas", color=[.45, .40, .28], helper=True)
part("tools.roll_tie", "Toolkit strap", [box(0, 0.082, 0, 0.02, 0.004, 0.10)], kind="fixture", parent="tools.roll", material="canvas", color=[.25, .20, .14], helper=True)
param("tools.roll_strap", show_low=["tools.roll_tie"])
home["tools.roll"] = "place.entry.roll"
kit = [
    ("tools.screwdriver", "Screwdriver", [cyl(0, 0, 0.02, 0.004, 0.11, "z"), cyl(0, 0, -0.06, 0.011, 0.07, "z")], 0.19, ["tool:screwdriver"], "wood"),
    ("tools.pliers", "Pliers", [box(0, 0, 0.04, 0.012, 0.008, 0.07), box(0, 0, -0.04, 0.026, 0.010, 0.09)], 0.16, ["tool:pliers"], "steel"),
    ("tools.cutters", "Wire cutters", [box(0, 0, 0.045, 0.014, 0.008, 0.05), box(0, 0, -0.03, 0.028, 0.010, 0.09)], 0.14, ["tool:cutters"], "steel"),
    ("tools.strippers", "Wire strippers", [box(0, 0, 0.04, 0.016, 0.006, 0.06), box(0, 0, -0.035, 0.03, 0.008, 0.09)], 0.15, ["tool:strippers"], "steel"),
    ("tools.wirebrush", "Wire brush", [box(0, 0, 0.055, 0.02, 0.014, 0.06), box(0, 0, -0.03, 0.014, 0.010, 0.11)], 0.17, ["tool:brush"], "wood"),
    ("tools.pick", "Pick", [cyl(0, 0, 0.02, 0.0025, 0.10, "z"), cyl(0, 0, -0.05, 0.007, 0.05, "z")], 0.14, ["tool:pick"], "steel"),
    ("tools.punch", "Pin punch", [cyl(0, 0, 0, 0.005, 0.11, "z")], 0.11, ["tool:punch"], "steel"),
    ("tools.scribe", "Scribe", [cyl(0, 0, 0, 0.003, 0.13, "z")], 0.13, ["tool:scribe"], "steel"),
]
shown = ["tools.roll_flat"]
for i, (pid, label, shapes, length, tags, material) in enumerate(kit):
    tool(pid, label, shapes, length, tags, pos=(0.22 - 0.055 * i, 0.016, 0.02), rot=(0, 180, 0), parent="tools.roll", clear=(0, 0.015, 0.095), material=material)
    place("tools.roll/seat_" + pid.split(".")[1], "tools.roll", (0, 0, 0), accepts=[pid], material="canvas", radius=0.025, rest_of=pid)
    shown.append(pid)
part("tools.bitblock", "Bit block", [box(0, 0.006, 0, 0.03, 0.012, 0.02)], pos=(-0.235, 0.008, 0.06), parent="tools.roll", material="wood", mass="tiny", kind="fixture", color=[.36, .26, .16])
shown.append("tools.bitblock")
for pid, label, parent, pos, colour in (("tools.bit_slot", "Slotted bit", "tools.screwdriver", (0, 0, 0.085), [.80, .80, .78]), ("tools.bit_cross", "Cross bit", "tools.bitblock", (0, 0.022, 0), [.85, .70, .30])):
    b = part(pid, label, [cyl(0, 0, 0, 0.003, 0.022, "z")], pos=pos, rot=(0, 0, 0) if parent == "tools.screwdriver" else (-90, 0, 0), kind="tool", parent=parent, mass="tiny",
             clear=(0, 0, 0.02) if parent == "tools.screwdriver" else (0, 0.02, 0), symmetry=6, color=colour)
    b["tool"] = {"verbs": [], "tags": ["bit:" + pid.split("_")[1]]}
param("tools.roll_unroll", show_high=["tools.roll_flat"], mesh_low=["tools.roll"])
# what is in the roll is hidden while it is rolled, whatever the roll is made of (the real roll's tools do not ride its bones)
layout_params["tools.roll_unroll"] = {"as_found": 0, "switch_at": 0.5, "show_high": [t for t in shown if t != "tools.roll_flat"]}
bench_tools = [
    ("tools.mallet", "Mallet", [box(0, 0, 0.10, 0.08, 0.04, 0.04), cyl(0, 0, -0.03, 0.009, 0.22, "z")], 0.28, ["tool:mallet"], (0.56, 0.02, 0.14), "wood", dict(tip=[0, -0.021, 0.10, 0, -1, 0], grab=[0, 0, -0.07], mass="medium")),
    ("tools.file_flat", "Flat file", [box(0, 0, 0.03, 0.02, 0.004, 0.16), cyl(0, 0, -0.09, 0.011, 0.08, "z")], 0.26, ["tool:file"], (0.64, 0.012, 0.14), "steel", {}),
    ("tools.file_round", "Round file", [cyl(0, 0, 0.03, 0.004, 0.16, "z"), cyl(0, 0, -0.09, 0.011, 0.08, "z")], 0.26, ["tool:file_round"], (0.69, 0.012, 0.14), "steel", {}),
    ("tools.snips", "Tin snips", [box(0, 0, 0.06, 0.03, 0.01, 0.08), box(0, 0, -0.05, 0.05, 0.012, 0.14)], 0.24, ["tool:snips"], (0.76, 0.012, 0.14), "steel", {}),
    ("tools.drill", "Hand drill", [cyl(0, 0, 0.06, 0.003, 0.08, "z"), box(0, 0, -0.03, 0.04, 0.05, 0.12)], 0.22, ["tool:drill"], (0.84, 0.03, 0.14), "steel", dict(mass="medium")),
    ("tools.iron", "Soldering iron", [cyl(0, 0, 0.05, 0.004, 0.07, "z"), cyl(0, 0, -0.04, 0.010, 0.11, "z")], 0.20, ["tool:solder"], (0.92, 0.02, 0.14), "wood", {}),
    ("tools.applicator", "Nanite applicator", [cyl(0, 0, 0, 0.006, 0.14, "z")], 0.14, ["tool:applicator"], (0.99, 0.012, 0.14), "plastic", {}),
]
for pid, label, shapes, length, tags, pos, material, extra in bench_tools:
    tool(pid, label, shapes, length, tags, pos=(pos[0], WT + pos[1], pos[2]), rot=(0, 180, 0), material=material, **extra)
    place("place.rest." + pid.split(".")[1], "", (0, 0, 0), accepts=[pid], material="wood", radius=0.03, rest_of=pid)
    home[pid] = "place.rest." + pid.split(".")[1]
part("tools.oil_bottle", "Oil bottle", [cyl(0, 0.031, 0, 0.016, 0.062, "y")], pos=(0.33, Y0, 0.10), kind="fixture", material="glass", color=[.55, .35, .10])
tool("tools.oil_dropper", "Oil dropper", [cyl(0, 0, 0.01, 0.004, 0.06, "z"), cyl(0, 0, -0.03, 0.010, 0.03, "z")], 0.10, ["tool:oil"], pos=(0, 0.075, 0), rot=(90, 0, 0), parent="tools.oil_bottle",
     clear=(0, 0.04, 0), material="glass")
place("tools.oil_bottle/seat_dropper", "tools.oil_bottle", (0, 0, 0), accepts=["tools.oil_dropper"], material="glass", radius=0.02, rest_of="tools.oil_dropper")
part("tools.thirdhand", "Third hand", [box(0, 0.01, 0, 0.07, 0.02, 0.05), cyl(0, 0.05, 0, 0.003, 0.08, "y")], pos=(0.10, Y0 + 0.006, 0.07), kind="fixture", color=[.30, .30, .32])
# the art's pose mark between the clips (model-tools, 21 Nov: in front of the post, not over it)
place("place.thirdhand", "tools.thirdhand", (0, 0.095, 0), (0, 0, 0), ["materials.resistor"], material="steel", tol_mm=16, symmetry=0, radius=0.03, mark="tools.thirdhand/seat_resistor")

# ====================================================================================================== pistol
# Greybox pistol space: +X muzzle, +Y up, Z across; the origin is at the top of the grip (the real family has its own frame:
# places that take the pistol have pose marks or their rot is re-measured at integration).
part("pistol.frame", "Scrap pistol", [box(0.05, 0.035, 0, 0.20, 0.05, 0.036), box(-0.045, -0.0475, 0, 0.030, 0.115, 0.016), box(0.0, -0.022, 0, 0.05, 0.012, 0.012)],
     mass="medium", item="scrap_pistol", tol_mm=16, tol_deg=30, grab=[0.115, 0.03, 0], tip=[0.21, 0.045, 0, 1, 0, 0],
     marks={"crack": [-0.0605, -0.06, 0, -1, 0, 0, 0.012], "tang_end": [-0.045, -0.105, 0, 0, -1, 0, 0.008]}, color=[.30, .31, .33])
home["pistol.frame"] = "place.entry.pistol"
part("pistol.barrel", "Barrel", [cyl(0, 0, 0, 0.012, 0.08, "x")], pos=(0.17, 0.045, 0), kind="fixture", parent="pistol.frame", color=[.22, .23, .25])
part("pistol.cell_bus", "Cell bus", [box(0, 0, 0, 0.05, 0.004, 0.006)], pos=(0.03, 0.012, 0.021), kind="fixture", parent="pistol.frame", material="copper", color=[.66, .42, .22])
part("pistol.cell", "Charge cell", [box(0, 0, 0, 0.055, 0.028, 0.022)], pos=(0.07, 0.03, 0.029), parent="pistol.frame", material="glass", clear=(0, 0, 0.06),
     held_by=["pistol.cell_latch"], tol_mm=12, tol_deg=30, color=[.25, .55, .58])
part("pistol.cell_latch", "Cell latch", [box(0, 0, 0, 0.012, 0.008, 0.022)], pos=(0.035, 0.052, 0.029), kind="fixture", parent="pistol.frame", clear=(0, 0.02, 0), symmetry=0, color=[.70, .55, .20])
param("pistol.cell_latch", target="pistol.cell_latch", move=(0, 0.008, 0))
part("pistol.status_lamp", "Status lamp", [box(0, 0, 0, 0.012, 0.005, 0.012)], pos=(-0.01, 0.0625, 0), kind="fixture", parent="pistol.frame", material="glass", color=[.05, .12, .13], emissive=True)
lamps.append({"part": "pistol.status_lamp", "color": [0.1, 1.6, 1.7], "as_found": 1})
for side, z in (("l", 1), ("r", -1)):
    part("pistol.scale_" + side, ("Left" if side == "l" else "Right") + " grip scale", [box(0, 0, 0, 0.036, 0.10, 0.009)], pos=(-0.045, -0.05, 0.0125 * z), parent="pistol.frame",
         material="wood", clear=(0, 0, 0.045 * z), held_by=["pistol.screw_grip_a", "pistol.screw_grip_b", "pistol.wrap"], symmetry=2, tol_mm=12, color=[.34, .22, .13])
for name, y, label in (("a", -0.022, "Upper grip screw"), ("b", -0.078, "Lower grip screw")):
    fastener(part("pistol.screw_grip_" + name, label, [cyl(0, 0, 0, 0.0045, 0.012, "z")], pos=(-0.045, y, 0.0190), parent="pistol.frame", mass="tiny", clear=(0, 0, 0.022),
                  symmetry=0, tol_mm=8, grab=[0, 0, 0.006], marks={"oil": [0, 0, 0.0065, 0, 0, 1, 0.007]} if name == "b" else {},
                  color=[.55, .40, .22] if name == "b" else [.60, .60, .58]), "slot", 6, ["pistol.scale_l", "pistol.scale_r"])
part("pistol.wrap", "Leather and tape wrap", [box(0, 0, 0, 0.050, 0.088, 0.052)], pos=(-0.045, -0.05, 0), parent="pistol.frame", material="canvas", clear=(0, 0, 0.06),
     held_by=["pistol.bind_wire_a", "pistol.bind_wire_b"], color=[.28, .20, .14], paths={"peel": [[-0.022 + (0.004 if i % 2 else -0.004), 0.040 - 0.0088 * i, 0.0265] for i in range(10)]})
for n, y in (("a", -0.03), ("b", -0.07)):
    part("pistol.bind_wire_" + n, "Binding wire", [box(0, 0, 0, 0.054, 0.004, 0.056)], pos=(-0.045, y, 0), parent="pistol.frame", material="copper", mass="tiny", clear=(0, 0, 0.05),
         marks={"snip": [0.012, 0, 0.0285, 0, 0, 1, 0.009]}, color=[.60, .42, .22])
part("pistol.lead", "Trigger lead", [box(0, -0.01, 0, 0.004, 0.03, 0.004)], pos=(0.012, 0.004, 0.022), kind="fixture", parent="pistol.frame", material="rubber", mass="tiny", color=[.10, .10, .10],
     paths={"route": [[-0.07 + 0.0, -0.004 - 0.0085 * i, -0.006] for i in range(12)]})
part("pistol.lead_plug", "Trigger lead plug", [box(0, 0, 0, 0.012, 0.008, 0.008)], pos=(-0.01, -0.006, 0.006), parent="pistol.cell_bus", material="plastic", mass="tiny",
     clear=(0, -0.03, 0.012), tol_mm=8, tol_deg=20, color=[.70, .68, .30])
part("pistol.housing", "Backstrap housing", [box(0, 0, 0, 0.012, 0.115, 0.030)], pos=(-0.066, -0.0475, 0), parent="pistol.frame", clear=(0, -0.13, 0),
     held_by=["pistol.housing_pin"], symmetry=2, tol_mm=12, color=[.20, .21, .23])
part("pistol.housing_spring", "Housing spring", [cyl(0, 0, 0, 0.004, 0.03, "y")], pos=(-0.058, -0.08, 0), parent="pistol.frame", mass="tiny", clear=(0, -0.05, 0), held_by=["pistol.housing"],
     symmetry=0, tol_mm=14, color=[.75, .75, .72])
fastener(part("pistol.housing_pin", "Housing pin", [cyl(0, 0, 0, 0.003, 0.04, "z")], pos=(-0.066, -0.005, 0), parent="pistol.frame", mass="tiny", clear=(0, 0, -0.045), symmetry=0, tol_mm=8,
              color=[.72, .72, .70], marks={"punch": [0, 0, 0.075, 0, 0, 1, 0.02]}), "pin", 0, ["pistol.housing"])
place("pistol.housing_pin/punch", "pistol.housing_pin", (0, 0, 0.075), (0, 180, 0), ["tools.punch"], material="steel", approach=(0, 0, 0.03), tol_mm=14, symmetry=0, radius=0.02)
for name, seat in (("a", "fixtures.board/seat_card_before"), ("b", "fixtures.board/seat_card_after")):
    part("pistol.card_" + name, "Test card", [box(0, 0, 0, 0.105, 0.148, 0.0012)], kind="consumable", material="paper", mass="tiny", symmetry=0, color=[.86, .84, .76],
         marks={"centre": [0, 0, 0.001, 0, 0, 1, 0.05]})
    home["pistol.card_" + name] = seat
    cards.append("pistol.card_" + name)

# ====================================================================================================== grip (ids as grip/export/parts.json of 19:27)
# In the pistol's frame, as the real family is: the core's rest pose is its seat on the tang, its clear pose 75 mm down off it.
# The family is the core, its two screws and the two nanite seams. The plates and the strap are the materials family's cut pieces
# (materials.sheet_a_plate, sheet_b_plate, strap_bent) and the gimbal is the servo's: they seat on the core's own seat marks.
# Stand-in left is +Z. The pocket and the loop channel are on the left face; the lead channel is down the back.
GX, GY = -0.045, -0.05   # centre of the grip in the pistol's frame
RECT = lambda z: [[GX + 0.02 * c, GY + 0.05 * d, z] for c, d in ((-1, 1), (1, 1), (1, -1), (-1, -1), (-1, 1))]
part("grip.core", "Stabilised Pistol Grip", [box(GX, GY, 0, 0.034, 0.11, 0.022), box(GX + 0.012, GY - 0.045, 0, 0.014, 0.02, 0.0224)], parent="pistol.frame", material="alloy",
     item="grip_stabilised_pistol", clear=(0, -0.075, 0), held_by=["pistol.housing_pin", "grip.screw_a", "grip.screw_b"], tol_mm=10, tol_deg=12, grab=[GX, GY, 0], color=[.50, .51, .48],
     paths={"lead": [[GX - 0.0175, 0.0 - 0.0085 * i, 0.004] for i in range(12)],
            "loop": [[GX + 0.009 - 0.0022 * abs(i - 3.5), GY + 0.004 + 0.006 * i, 0.0112] for i in range(8)],
            "seam_l": RECT(0.0136), "seam_r": RECT(-0.0136)},
     marks={"pocket_shoulder": [GX, GY - 0.026, 0.0112, 0, 0, 1, 0.012], "mend": [GX + 0.012, GY - 0.026, 0.0112, 0, 0, 1, 0.012]}, wipes=["skin", "flash", "pocket"])
home["grip.core"] = "gone"
parents["grip.core"] = "pistol.frame"
place("grip.core/seat_gimbal", "grip.core", (GX, GY - 0.026, 0.011), (90, 0, 0), ["servo.gimbal_cradle"], material="alloy", tol_mm=12, tol_deg=25, symmetry=1, radius=0.03, approach=(0, 0, 0.04))
# a cut plate lies flat with +Y its upper face and its length along X; on the core its length runs up the grip and that face looks outward (left plate) or inward (right)
place("grip.core/seat_plate_l", "grip.core", (GX, GY, 0.0123), (-180, -90, -90), ["materials.sheet_a_plate"], material="alloy", tol_mm=12, tol_deg=20, symmetry=1, radius=0.03, approach=(0, 0, 0.04))
place("grip.core/seat_plate_r", "grip.core", (GX, GY, -0.0123), (-180, -90, -90), ["materials.sheet_b_plate"], material="alloy", tol_mm=12, tol_deg=20, symmetry=1, radius=0.03, approach=(0, 0, -0.04))
place("grip.core/seat_strap", "grip.core", (GX - 0.019, GY, 0), (0, 0, 90), ["materials.strap_bent"], material="alloy", tol_mm=12, tol_deg=20, symmetry=1, radius=0.02, approach=(0, -0.11, 0))
for side, z, screws in (("l", 1, "ab"), ("r", -1, "cd")):
    for hole, (x, y), screw in (("c", (0.012, 0.03), screws[0]), ("d", (-0.012, -0.035), screws[1])):
        place("grip.core/seat_plate_screw_%s%s" % (side, hole), "grip.core", (GX + x, GY + y, 0.0136 * z), (90 * z, 0, 0), ["servo.screw_case_" + screw], material="alloy",
              tol_mm=10, symmetry=0, radius=0.012, approach=(0, 0, 0.025 * z))
    part("grip.seam_" + side, ("Left" if z > 0 else "Right") + " nanite seam", [box(0, 0, 0, 0.042, 0.102, 0.0008)], pos=(GX, GY, 0.0139 * z), parent="grip.core", material="plastic", mass="tiny",
         color=[.62, .64, .66], wipes=["seam"])
    home["grip.seam_" + side] = "gone"
for name, y in (("a", -0.022), ("b", -0.078)):
    fastener(part("grip.screw_" + name, "New grip screw", [cyl(0, 0, 0, 0.0045, 0.012, "z")], pos=(-0.045, y, 0.0215), parent="grip.core", mass="tiny", clear=(0, 0, 0.022),
                  symmetry=0, tol_mm=9, grab=[0, 0, 0.006], color=[.72, .58, .25]), "cross", 7, ["materials.sheet_a_plate", "grip.core"])
    home["grip.screw_" + name] = "fixtures.dish/slot_1%d" % (0 if name == "a" else 1)

# ====================================================================================================== servo (real ids, simple shapes)
# Servo space: X long (95), Y up (55), Z across (70); origin at the centre of the base. The case is an open box so what is inside shows.
W, H, D = 0.095, 0.055, 0.07
part("servo.case_body", "Damaged Servo", [box(0, 0.003, 0, W, 0.006, D), box(0, 0.024, -D / 2 + 0.003, W, 0.042, 0.006), box(0, 0.024, D / 2 - 0.003, W, 0.042, 0.006),
                                         box(-W / 2 + 0.003, 0.024, 0, 0.006, 0.042, D), box(W / 2 - 0.003, 0.024, 0, 0.006, 0.042, D)],
     material="alloy", mass="medium", item="droid_servo_damaged", symmetry=2, tol_mm=18, color=[.42, .36, .26], grab=[0, 0.03, 0],
     marks={"pry_%d" % (i + 1): [-0.03 + 0.03 * i, 0.044, D / 2 + 0.001, 0, 0, 1, 0.008] for i in range(3)}, zones={"dust_l": [0, 0.032, D / 2 + 0.001, 0.09, 0.004, 0.03], "dust_r": [0, 0.032, -D / 2 - 0.001, 0.09, 0.004, 0.03]}, zone_rot={"dust_l": [90, 0, 0], "dust_r": [-90, 0, 0]})
home["servo.case_body"] = "place.entry.servo"
part("servo.case_lid", "Servo case lid", [box(0, 0, 0, W, 0.008, D)], pos=(0, 0.049, 0), parent="servo.case_body", material="plastic", clear=(0, 0.05, 0), symmetry=2, tol_mm=14,
     held_by=["servo.screw_case_a", "servo.screw_case_b", "servo.screw_case_c", "servo.screw_case_d", "servo.clip_1", "servo.clip_2", "servo.clip_3"], color=[.36, .33, .26],
     zones={"dust": [0, 0.005, 0, 0.085, 0.004, 0.06]})
for i, (name, x, z) in enumerate((("a", -1, -1), ("b", 1, -1), ("c", -1, 1), ("d", 1, 1))):
    fastener(part("servo.screw_case_" + name, "Case screw", [cyl(0, 0, 0, 0.004, 0.012, "y")], pos=(x * 0.038, 0.055, z * 0.026), parent="servo.case_body", mass="tiny", clear=(0, 0.02, 0),
                  symmetry=0, tol_mm=8, grab=[0, 0.006, 0], color=[.50, .32, .20] if name == "d" else [.72, .58, .25], wipes=["dust"]), "pliers" if name == "d" else "cross", 10, ["servo.case_lid"])
for i in range(3):
    part("servo.clip_%d" % (i + 1), "Case clip", [box(0, 0, 0, 0.012, 0.014, 0.003)], pos=(-0.03 + 0.03 * i, 0.044, D / 2 + 0.0015), kind="fixture", parent="servo.case_body", mass="tiny",
         clear=(0, 0, 0.01), symmetry=0, color=[.60, .60, .58], wipes=["dust"])
    param("servo.clip_%d" % (i + 1), target="servo.clip_%d" % (i + 1), move=(0, 0, 0.004), turn=(-25, 0, 0))
part("servo.board", "Burnt control board", [box(0, 0, 0, 0.05, 0.003, 0.05)], pos=(-0.018, 0.040, 0), parent="servo.case_body", material="plastic", clear=(0, 0.06, 0), held_by=["servo.case_lid"],
     symmetry=0, tol_mm=14, color=[.12, .20, .12], marks={"snip_r1": [0.012, 0.004, 0.018, 0, 1, 0, 0.006], "snip_r2": [0.022, 0.004, 0.018, 0, 1, 0, 0.006]})
part("servo.lead_plug", "Board plug", [box(0, 0, 0, 0.010, 0.006, 0.008)], pos=(-0.018, 0.005, -0.018), parent="servo.board", material="plastic", mass="tiny", clear=(0, 0.02, 0), tol_mm=8, color=[.80, .78, .60])
part("servo.trim_resistor", "Trim resistor", [cyl(0, 0, 0, 0.0025, 0.010, "x")], pos=(0.017, 0.005, 0.018), parent="servo.board", material="ceramic", mass="tiny", clear=(0, 0.02, 0), symmetry=2,
     tol_mm=12, color=[.20, .45, .60])
part("servo.circlip", "Circlip", [cyl(0, 0, 0, 0.007, 0.0015, "y")], pos=(-0.030, 0.036, 0.018), parent="servo.case_body", mass="tiny", clear=(0, 0.02, 0), symmetry=0, tol_mm=12,
     color=[.75, .75, .72])
for i, (name, held) in enumerate((("low", "servo.gear_mid"), ("mid", "servo.gear_top"), ("top", "servo.circlip"))):
    part("servo.gear_" + name, name.capitalize() + " gear", [cyl(0, 0, 0, 0.011 - 0.002 * i, 0.005, "y")], pos=(-0.030, 0.014 + 0.007 * i, 0.018), parent="servo.case_body", mass="tiny",
         clear=(0, 0.04, 0), symmetry=0, tol_mm=14, held_by=[held], color=[.50, .46, .36])
for name, z in (("a", -1), ("b", 1)):
    fastener(part("servo.screw_trunnion_" + name, "Trunnion screw", [cyl(0, 0, 0, 0.0035, 0.010, "y")], pos=(0.005, 0.030, 0.012 + z * 0.014), parent="servo.case_body", mass="tiny", clear=(0, 0.02, 0),
                  symmetry=0, tol_mm=8, grab=[0, 0.005, 0], color=[.72, .58, .25]), "cross", 8, ["servo.gimbal_cradle"])
part("servo.gimbal_cradle", "Gimbal", [box(0, 0, 0, 0.034, 0.006, 0.034), cyl(0, 0.010, 0, 0.014, 0.004, "y")], pos=(0.005, 0.012, 0.012), parent="servo.case_body", material="alloy", clear=(0, 0.06, 0),
     held_by=["servo.screw_trunnion_a", "servo.screw_trunnion_b"], symmetry=2, tol_mm=12, color=[.58, .58, .54], grab=[0, 0.006, 0],
     marks={"oil_a": [0, 0.008, -0.014, 0, 1, 0, 0.005], "oil_b": [0, 0.008, 0.014, 0, 1, 0, 0.005], "probe_a": [-0.014, 0.006, 0, 0, 1, 0, 0.005], "probe_b": [0.014, 0.006, 0, 0, 1, 0, 0.005]},
     zones={"trunnion_a": [0, 0.004, -0.012, 0.03, 0.003, 0.012], "trunnion_b": [0, 0.004, 0.012, 0.03, 0.003, 0.012]})
part("servo.gimbal_ring", "Gimbal ring", [cyl(0, 0, 0, 0.0165, 0.002, "y")], pos=(0, 0.0125, 0), kind="fixture", parent="servo.gimbal_cradle", mass="tiny", color=[.44, .36, .28],
     wipes=["corrosion"])
part("servo.gimbal_race", "Bearing race", [cyl(0, 0, 0, 0.012, 0.003, "y")], pos=(0, 0.014, 0), kind="fixture", parent="servo.gimbal_cradle", mass="tiny", color=[.40, .30, .22],
     marks={"detent_%d" % (i + 1): [0.010 * [1, -.5, -.5][i], 0.002, 0.010 * [0, .87, -.87][i], 0, 1, 0, 0.004] for i in range(3)}, zones={"race": [0, 0.002, 0, 0.026, 0.003, 0.026]})
for i in range(3):
    part("servo.gimbal_grit_%d" % (i + 1), "Grit", [box(0, 0, 0, 0.003, 0.002, 0.003)], pos=(0.010 * [1, -.5, -.5][i], 0.017, 0.010 * [0, .87, -.87][i]), kind="consumable",
         parent="servo.gimbal_cradle", material="ceramic", mass="tiny", color=[.30, .22, .12])
part("servo.gimbal_rotor", "Rotor", [cyl(0, 0, 0, 0.009, 0.012, "y")], pos=(0, 0.024, 0), parent="servo.gimbal_cradle", clear=(0, 0.03, 0), held_by=["servo.gimbal_retainer"], symmetry=0, tol_mm=12,
     color=[.66, .66, .62])
part("servo.gimbal_retainer", "Retaining ring", [cyl(0, 0, 0, 0.010, 0.0015, "y")], pos=(0, 0.031, 0), parent="servo.gimbal_cradle", mass="tiny", clear=(0, 0.02, 0), symmetry=0, tol_mm=12,
     color=[.78, .78, .75])
for name, z in (("coil_a", -0.008), ("coil_b", 0.0), ("sense", 0.008)):
    part("servo.lead_" + name, "Lead", [box(-0.015, 0, 0, 0.03, 0.002, 0.002)], pos=(-0.017, 0.004, z), kind="fixture", parent="servo.gimbal_cradle", material="rubber", mass="tiny",
         color=[.55, .15, .12] if name != "sense" else [.15, .15, .50], marks={"snip": [-0.027, 0.001, 0, 0, 1, 0, 0.005]})
part("servo.stator", "Stator", [cyl(0, 0, 0, 0.014, 0.016, "y")], pos=(0.030, 0.014, -0.016), kind="fixture", parent="servo.case_body", color=[.30, .30, .30])
part("servo.stator_winding", "Stator winding", [cyl(0, 0, 0, 0.016, 0.010, "y")], pos=(0, 0, 0), kind="fixture", parent="servo.stator", material="copper", color=[.70, .42, .20],
     marks={"end": [0.016, 0, 0, 1, 0, 0, 0.006]})

# ====================================================================================================== materials (ids from materials/PARTS.md and SEAM.md section 10)
# What makes the core raw when the mould opens (in the core's frame, absent until then): the fin along the parting line, filed off
# along its path, and the sprue stub, knocked off at its mark.
part("materials.core_flash", "Flash", [box(GX - 0.0185, GY + 0.004, 0, 0.003, 0.088, 0.0012), box(GX + 0.0185, GY + 0.02, 0, 0.003, 0.04, 0.0012)], parent="grip.core", kind="consumable",
     material="alloy", mass="tiny", color=[.66, .67, .64], paths={"file": [[GX - 0.020, GY + 0.044 - 0.0126 * i, 0] for i in range(8)]})
home["materials.core_flash"] = "gone"
part("materials.core_sprue", "Sprue", [cyl(GX - 0.004, GY - 0.062, 0, 0.004, 0.014, "y")], parent="grip.core", kind="consumable", material="alloy", mass="tiny", color=[.60, .61, .58],
     grab=[GX - 0.004, GY - 0.062, 0], marks={"snap": [GX - 0.004, GY - 0.064, 0.004, 0, 0, 1, 0.008]})
home["materials.core_sprue"] = "gone"
# The two sheets lie flat, +Y the upper face, 120 x 90. What is cut out of a sheet is a child of it until it is cut.
for s, colour in (("a", [.62, .40, .18]), ("b", [.58, .56, .50])):
    outline = [[0.05 * c, 0.002, 0.02 * d - 0.006] for c, d in ((-1, -1), (1, -1), (1, 1), (-1, 1), (-1, -1))]
    part("materials.sheet_" + s, "Scrap Alloy", [box(0, 0, 0, 0.12, 0.0025, 0.09)], material="alloy", item="scrap_alloy", symmetry=2, tol_mm=18, color=colour, grab=[0, 0, 0],
         paths={"scribe": outline, "cut": [[p[0] * 1.03, p[1], (p[2] + 0.006) * 1.08 - 0.006] for p in outline], "cut_strap": [[-0.055 + 0.0122 * i, 0.002, 0.031] for i in range(10)]} if s == "a" else {})
    home["materials.sheet_" + s] = "place.entry.sheet_" + s
    part("materials.sheet_%s_plate" % s, ("Left" if s == "a" else "Right") + " plate, as cut", [box(0, 0, 0, 0.10, 0.0026, 0.04)], pos=(0, 0.0001, -0.006), parent="materials.sheet_" + s, material="alloy",
         clear=(0, 0.03, 0), symmetry=1, tol_mm=14, color=[c * 1.12 for c in colour], grab=[0, 0, 0],
         marks={"punch_%d" % (i + 1): [0.035 * [-1, 1, -1, 1][i], 0.0016, 0.012 * [-1, -1, 1, 1][i], 0, 1, 0, 0.005] for i in range(4)})
    part("materials.sheet_%s_margin" % s, "Margin outside the line", [box(0, 0, 0, 0.104, 0.0024, 0.044)], kind="consumable", parent="materials.sheet_%s_plate" % s, material="alloy", mass="tiny",
         color=[c * .8 for c in colour])
    for i in range(4):
        part("materials.sheet_%s_plug_%d" % (s, i + 1), "Hole", [cyl(0, 0, 0, 0.003, 0.004, "y")], pos=(0.035 * [-1, 1, -1, 1][i], 0.0008, 0.012 * [-1, -1, 1, 1][i]), kind="consumable",
             parent="materials.sheet_%s_plate" % s, material="alloy", mass="tiny", clear=(0, 0.01, 0), symmetry=0, color=[.22, .22, .22], grab=[0, 0.002, 0],
             **({"wipes": ["punch"]} if s == "a" else {}))
    part("materials.sheet_%s_strap" % s, "Strap strip", [box(0, 0, 0, 0.10, 0.0026, 0.012)], pos=(0, 0.0001, 0.038), parent="materials.sheet_" + s, material="alloy", clear=(0, 0.03, 0), symmetry=2,
         tol_mm=14, color=[.80, .45, .12], grab=[0, 0, 0], marks={"bend_1": [-0.02, 0.002, 0, 0, 1, 0, 0.006], "bend_2": [0.02, 0.002, 0, 0, 1, 0, 0.006]})
    for i in range(2):
        part("materials.sheet_%s_offcut_%d" % (s, i + 1), "Alloy offcut", [box(0, 0, 0, 0.006, 0.0026, 0.05)], pos=(0.056 * (1 if i else -1), 0.0001, -0.006), kind="fixture", parent="materials.sheet_" + s,
             material="alloy", mass="tiny", color=[c * .9 for c in colour])
# the strap after one bend and after both: second states of the flat strip, at its own origin (absent until bent)
part("materials.strap_bent_1", "Strap, bent once", [box(-0.008, 0, 0, 0.084, 0.0026, 0.012), box(0.034, -0.008, 0, 0.0026, 0.018, 0.012)], pos=(0, 0.0001, 0.038),
     parent="materials.sheet_a", material="alloy", symmetry=2, tol_mm=14, color=[.83, .45, .11], grab=[0, 0, 0])
home["materials.strap_bent_1"] = "gone"
part("materials.strap_bent", "Reinforcement strap", [box(0, 0, 0, 0.10, 0.0026, 0.017), box(-0.05, 0.016, 0, 0.0026, 0.034, 0.017)], pos=(0, 0.0001, 0.038),
     parent="materials.sheet_a", material="alloy", symmetry=1, tol_mm=12, tol_deg=20, color=[.85, .45, .10], grab=[0, 0, 0])
home["materials.strap_bent"] = "gone"
part("materials.sheet_a_scribe", "Scribed line", [box(0, 0, 0, 0.101, 0.0006, 0.041)], pos=(0, 0.0016, -0.006), kind="consumable", parent="materials.sheet_a", material="alloy", color=[.95, .95, .90])
home["materials.sheet_a_scribe"] = "gone"
place("place.sheet.template", "materials.sheet_a", (0.0, 0.006, -0.006), (-90, 0, 90), ["pistol.scale_l"], material="alloy", tol_mm=16, symmetry=2, radius=0.04)
place("place.sheet.stack", "materials.sheet_a", (0.0, -0.0026, 0.0), (0, 0, 0), ["materials.sheet_b"], material="alloy", tol_mm=18, symmetry=2, radius=0.05, approach=(0, 0, 0.05))
place("place.plate.stack", "materials.sheet_a_plate", (0.0, -0.0027, 0.0), (0, 0, 0), ["materials.sheet_b_plate"], material="alloy", tol_mm=18, symmetry=2, radius=0.04)
place("place.plate.template", "materials.sheet_a_plate", (0.0, 0.006, 0.0), (-90, 0, 90), ["pistol.scale_l"], material="alloy", tol_mm=16, symmetry=2, radius=0.04, approach=(0, 0.035, 0))
# (not bound to fixtures.workmat/seat_sheet: that mark is where seat_small is, and the gimbal lies there through stage 3)
place("place.mat.sheet", "fixtures.workmat", (0.085, 0.0039, 0.045), (0, 0, 0), ["materials.sheet_a"], tol_mm=20, symmetry=2, radius=0.06, real={"when": "fixtures", "pos": [-0.085, 0.0075, 0.045], "rest_on": True})
place("place.mat.plate_l", "fixtures.workmat", (0.085, 0.0041, -0.095), (0, 0, 0), ["materials.sheet_a_plate"], tol_mm=18, symmetry=2, radius=0.04, real={"when": "fixtures", "pos": [-0.085, 0.0075, -0.095], "rest_on": True}, mark="fixtures.workmat/seat_plate_l")
place("place.mat.plate_r", "fixtures.workmat", (0.085, 0.0015, -0.045), (0, 0, 0), ["materials.sheet_b_plate"], tol_mm=18, symmetry=2, radius=0.04, real={"when": "fixtures", "pos": [-0.085, 0.0075, -0.045], "rest_on": True}, mark="fixtures.workmat/seat_plate_r")
# (not bound to fixtures.workmat/seat_strap: the strap's node frame is the grip frame G, so on that pose mark the strap went into the mat)
place("place.mat.strap", "fixtures.workmat", (0.135, 0.003, 0.0), (0, 90, 0), ["materials.sheet_a_strap", "materials.sheet_b_strap", "materials.strap_bent"], tol_mm=16, symmetry=2, radius=0.03, real={"when": "fixtures", "pos": [-0.135, 0.0075, 0.0], "rest_on": True})
place("place.mat.spare", "fixtures.workmat", (0.168, 0.003, 0.0), (0, 90, 0), ["materials.sheet_b_strap"], tol_mm=16, symmetry=2, radius=0.02, real={"when": "fixtures", "pos": [-0.168, 0.0075, 0.0], "rest_on": True}, mark="fixtures.workmat/seat_spare")

# What hangs on the gimbal is in the cradle's own frame (parent servo.gimbal_cradle at identity), absent until the gimbal is on the bench.
on_gimbal = []
def lead_part(pid, label, shapes, **kw):
    kw.setdefault("material", "rubber"); kw.setdefault("mass", "tiny"); kw.setdefault("kind", "fixture")
    part(pid, label, shapes, parent="servo.gimbal_cradle", **kw)
    home[pid] = "gone"; parents[pid] = "servo.gimbal_cradle"; on_gimbal.append(pid)
def on_lead(pid, label, shapes, lead, **kw):
    kw.setdefault("material", "rubber"); kw.setdefault("mass", "tiny"); kw.setdefault("kind", "consumable")
    part(pid, label, shapes, parent=lead, **kw); home[pid] = "gone"
for s, z in (("a", -0.008), ("b", 0.0)):
    lead = "materials.lead_" + s
    lead_part(lead, "Coil lead", [box(-0.019, 0, 0, 0.038, 0.002, 0.002)], pos=(-0.017, -0.001, z), kind="part", color=[.55, .15, .12], marks={"trim": [-0.046, 0.001, 0, 0, 1, 0, 0.005]})
    on_lead(lead + "_offcut", "Lead offcut", [box(-0.010, 0, 0, 0.020, 0.002, 0.002)], lead, pos=(-0.046, 0, 0), color=[.45, .12, .10])
    on_lead(lead + "_strands", "Bare strands", [box(-0.004, 0, 0, 0.008, 0.0012, 0.0012)], lead, pos=(-0.038, 0, 0), kind="part", material="copper", color=[.80, .50, .25], wipes=["tin"])
    on_lead(lead + "_slug", "Insulation", [box(-0.004, 0, 0, 0.008, 0.0026, 0.0026)], lead, pos=(-0.038, 0, 0), clear=(-0.014, 0, 0), symmetry=0, tol_mm=10, color=[.70, .20, .15], grab=[-0.004, 0, 0])
    on_lead("materials.sleeve_" + s, "Sleeve", [cyl(0, 0, 0, 0.0018, 0.008, "x")], lead, pos=(-0.013, 0, 0), kind="part", color=[.08, .08, .08])
lead_part("materials.lead_sense", "Sense lead", [box(-0.025, 0, 0, 0.05, 0.002, 0.002)], pos=(-0.017, -0.001, 0.008), kind="consumable", color=[.15, .15, .50], marks={"flush": [-0.002, 0.001, 0, 0, 1, 0, 0.005]})
lead_part("materials.loop_lead_a", "Loop lead", [box(-0.012, 0, 0, 0.024, 0.002, 0.002), box(-0.024, 0, 0.012, 0.002, 0.002, 0.026)], pos=(-0.017, -0.001, -0.008), kind="part", color=[.55, .15, .12])
lead_part("materials.loop_lead_b", "Loop lead", [box(-0.012, 0, 0, 0.024, 0.002, 0.002)], pos=(-0.017, -0.001, 0.016), kind="part", color=[.55, .15, .12])
lead_part("materials.loop_resistor", "Damper loop resistor", [cyl(0, 0, 0, 0.0025, 0.010, "z")], pos=(-0.041, -0.001, 0.004), kind="part", material="ceramic", color=[.20, .45, .60],
          marks={"probe_a": [0, 0.003, -0.007, 0, 1, 0, 0.005], "probe_b": [0, 0.003, 0.007, 0, 1, 0, 0.005]})
for s, z in (("a", -0.004), ("b", 0.012)):
    lead_part("materials.loop_sleeve_" + s, "Shrunk sleeve", [cyl(0, 0, 0, 0.0016, 0.007, "z")], pos=(-0.041, -0.001, z), kind="part", color=[.08, .08, .08])
lead_part("materials.loop_tucked", "Damper loop, tucked", [box(-0.006, 0.0, 0.026, 0.026, 0.002, 0.002), box(-0.019, 0.0, 0.019, 0.002, 0.002, 0.016), box(0.007, 0.0, 0.019, 0.002, 0.002, 0.016), cyl(-0.006, 0, 0.026, 0.0025, 0.008, "x")],
          pos=(0, 0.004, 0), kind="part", material="copper", color=[.60, .25, .20], paths={"tuck": [[-0.019 + 0.0052 * i, 0.001, 0.026] for i in range(6)]})
part("materials.resistor", "Trim resistor", [cyl(0, 0, 0, 0.0025, 0.010, "x"), box(0, 0, 0, 0.03, 0.0008, 0.0008)], material="ceramic", mass="tiny", symmetry=0, tol_mm=14, color=[.20, .45, .60],
     grab=[0, 0, 0], wipes=["tin"])
home["materials.resistor"] = "gone"
part("materials.vial", "Nanite vial", [cyl(0, 0, 0, 0.012, 0.062, "y")], material="glass", mass="tiny", item="nanite_residue", symmetry=0, tol_mm=25, color=[.55, .57, .60],
     tip=[0, 0.031, 0, 0, 1, 0], grab=[0, 0, 0], marks={"level": [0.012, 0.012, 0, 1, 0, 0, 0.005]})
home["materials.vial"] = "place.entry.vial"
part("materials.vial_fluid", "Nanites", [cyl(0, -0.008, 0, 0.010, 0.040, "y")], kind="consumable", parent="materials.vial", material="plastic", mass="tiny", color=[.42, .44, .46])
part("materials.vial_stopper", "Stopper", [cyl(0, 0, 0, 0.009, 0.012, "y")], pos=(0, 0.035, 0), parent="materials.vial", material="rubber", mass="tiny", clear=(0, 0.02, 0), symmetry=0, tol_mm=10,
     color=[.18, .12, .10], grab=[0, 0.003, 0])
part("materials.vial_line", "Level line", [cyl(0, 0.012, 0, 0.0122, 0.001, "y")], kind="fixture", parent="materials.vial", material="glass", mass="tiny", color=[.9, .9, .9])
part("materials.bobbin", "Bobbin", [cyl(0, 0.015, 0, 0.007, 0.03, "y"), cyl(0, 0.001, 0, 0.017, 0.002, "y"), cyl(0, 0.029, 0, 0.017, 0.002, "y")], material="wood", mass="tiny", symmetry=0, tol_mm=16,
     color=[.45, .32, .18], clear=(0, 0.03, 0), grab=[0, 0.015, 0], item="copper_filament")
home["materials.bobbin"] = "fixtures.partsmat/seat_servo_bobbin"
part("materials.bobbin_wire", "Wound copper", [cyl(0, 0.015, 0, 0.013, 0.024, "y")], kind="consumable", parent="materials.bobbin", material="copper", color=[.75, .45, .20])
home["materials.bobbin_wire"] = "gone"
place("place.servo.bobbin", "servo.case_body", (0.030, 0.045, -0.016), (0, 0, 0), ["materials.bobbin"], material="alloy", tol_mm=18, symmetry=0, radius=0.03)
place("place.mould.charge", "fixtures.mould_tang", (0, 0.034, 0), (0, 0, 0), ["materials.sheet_a"], material="steel", tol_mm=30, tol_deg=45, symmetry=2, radius=0.05, mark="fixtures.mould_tang/seat_charge")
place("place.mould.core", "fixtures.mould_tang", (-GY, 0.046, GX), (-90, 0, 90), ["grip.core"], material="steel", tol_mm=20, symmetry=0, radius=0.04, mark="fixtures.mould_tang/seat_core")
place("place.press.pour", "fixtures.press", (0.05, 0.16, 0.03), (0, 0, 105), ["materials.vial"], material="steel", tol_mm=30, tol_deg=60, symmetry=0, radius=0.05, approach=(0.03, 0.03, 0), mark="fixtures.press/seat_pour")

# ====================================================================================================== shots (cam_bench_*)
# A shot is what it frames (part, mark or place ids; "reach" is the whole worktop the hand can use), with a pitch, a yaw from
# the player's side and a lens: the installer stands the camera where that fits a 16:9 picture. pos and look are only the
# fallback for a bench that has none of the things named (a family whose art has not arrived).
# A part whose art has no __tip of its own: the node its tip stands at, and which way is out and up in the part's own space (Unity
# axes; the pistol family's frame has the muzzle along +X and the top along +Y once imported). The stand-in has its own tip.
tips["pistol.frame"] = {"node": "pistol_barrel__mark_bore_mouth", "dir": [1, 0, 0], "up": [0, 1, 0]}
# Where the hand takes a real part that has no __grab of its own, in the part's own space: the vise screw is turned at its front end,
# which is its origin (its middle is inside the jaw; the art's `handle` mark on the jaw is 8 cm off the screw, at the end of the bar).
grabs["fixtures.vise_screw"] = {"local": [0, 0, 0]}
# The old bench's print head hangs over the middle of the worktop (measured on workbench_b4k: x +-0.30, y 1.47..2.01, z -0.20..0.16).
# `avoid` keeps it to the top tenth of the widest shot: the eye stays in front of it and looks down more steeply.
HEAD = [0.0, 1.74, -0.02, 0.60, 0.54, 0.36]
shots += [
    {"id": "wide", "frames": ["reach"], "pitch": 50, "fov": 55, "anchor": "bottom", "margin": 0.02, "avoid": {"box": HEAD, "max_top": 0.10, "max_pitch": 76},
     "headroom": 0.10, "pos": [0.0, 1.99, 1.08], "look": [0.0, 0.88, 0.22]},
    {"id": "work", "frames": ["fixtures.worksurface"], "pitch": 52, "fov": 50, "anchor": "bottom", "headroom": 0.16, "margin": 0.03, "pos": [0.0, 1.62, 1.05], "look": [0.0, 0.88, 0.28]},
    # (headroom 0.2, 21 Nov: the grip clamped above the jaws swings round on the swivel and reached Brann's caption band at 0.13)
    {"id": "vise", "frames": ["fixtures.vise", "fixtures.vise_screw"], "pitch": 40, "fov": 42, "headroom": 0.2, "margin": 0.12, "pos": [0.30, 1.46, 0.95], "look": [0.34, 1.03, 0.33]},
    # down into what the vise holds (the open servo, the top edge of a clamped sheet): the same place seen from above the front jaw
    {"id": "over", "frames": ["fixtures.vise", "fixtures.vise_screw"], "pitch": 66, "fov": 42, "headroom": 0.10, "margin": 0.12, "pos": [0.32, 1.62, 0.62], "look": [0.33, 1.0, 0.33]},
    # the vise from the player's left and from the right (21 Nov): for work on a side of what the vise holds that faces away from
    # the front (the grip's rear channel, the far wire twist, the servo's seam clips)
    {"id": "vise_l", "frames": ["fixtures.vise", "fixtures.vise_screw"], "pitch": 32, "yaw": -55, "fov": 42, "headroom": 0.13, "margin": 0.12, "pos": [0.9, 1.4, 0.7], "look": [0.34, 1.03, 0.33]},
    {"id": "vise_r", "frames": ["fixtures.vise", "fixtures.vise_screw"], "pitch": 32, "yaw": 55, "fov": 42, "headroom": 0.13, "margin": 0.12, "pos": [-0.2, 1.4, 0.7], "look": [0.34, 1.03, 0.33]},
    {"id": "mat", "frames": ["fixtures.workmat", "fixtures.pad"], "pitch": 56, "fov": 46, "headroom": 0.05, "margin": 0.08, "pos": [-0.03, 1.50, 0.82], "look": [-0.03, 0.89, 0.22]},
    {"id": "parts", "frames": ["fixtures.partsmat", "fixtures.dish"], "pitch": 58, "fov": 46, "headroom": 0.04, "margin": 0.1, "pos": [-0.03, 1.46, 1.02], "look": [-0.03, 0.88, 0.43]},
    {"id": "card", "frames": ["fixtures.board"], "pitch": 14, "fov": 38, "margin": 0.12, "min": 0.9, "pos": [0.50, 1.42, 0.62], "look": [0.95, 1.07, -0.29]},
    {"id": "tray", "frames": ["fixtures.tray"], "pitch": 52, "fov": 46, "headroom": 0.08, "margin": 0.25, "pos": [-0.60, 1.45, 0.78], "look": [-0.66, 0.90, 0.18]},
    {"id": "press", "frames": ["fixtures.press", "fixtures.press_lever", "fixtures.mouldrack", "fixtures.tray"], "pitch": 36, "fov": 44, "headroom": 0.14, "margin": 0.08, "pos": [-0.40, 1.52, 0.72], "look": [-0.56, 1.02, -0.20]},
    # (21 Nov) low under the press ram into the mould on the bed: laying the charge in, lifting the core out
    {"id": "press_low", "frames": ["fixtures.press", "fixtures.mould_tang"], "pitch": 16, "yaw": -18, "fov": 40, "headroom": 0.05, "margin": 0.12, "pos": [-0.5, 1.15, 0.6], "look": [-0.56, 1.0, -0.2]},
    # (21 Nov) the press from the player's left, low: into the cavity past the ram (laying the charge in)
    {"id": "press_side", "frames": ["fixtures.press", "fixtures.mould_tang"], "pitch": 26, "yaw": -34, "fov": 40, "headroom": 0.05, "margin": 0.12, "pos": [0.2, 1.4, 0.9], "look": [-0.56, 1.0, -0.2]},
    # (21 Nov) over the open toolkit: where the hand goes for a tool in the roll that the work shot does not show
    {"id": "roll", "frames": ["tools.screwdriver", "tools.pliers", "tools.cutters", "tools.punch", "tools.strippers", "tools.wirebrush", "tools.pick", "tools.scribe"], "pitch": 62, "fov": 40, "headroom": 0.03, "margin": 0.1, "pos": [0.95, 1.45, 0.75], "look": [0.95, 0.88, 0.38]},
    {"id": "tester", "frames": ["fixtures.tester", "fixtures.jar"], "pitch": 42, "fov": 44, "headroom": 0.05, "margin": 0.2, "pos": [0.48, 1.42, 0.70], "look": [0.52, 0.93, 0.05]},
    {"id": "room", "frames": ["reach"], "pitch": 26, "yaw": -32, "fov": 55, "margin": 0.2, "pos": [1.55, 1.60, 2.30], "look": [0.0, 1.0, 0.0]},
]

layout = {
    "note": "Bench space: metres, +Y up, +Z towards the player (the player's right is -X), origin at the floor under the bench centre (the SS_Workbench prefab's own space). "
            "Generated by bench/make_greybox.py. A place with a `mark` takes its position (and, for a pose mark, its rotation) from that mark of the real family; "
            "pos and rot are the greybox fallback, in the owner part's space. `real` gives where a real family's GLB root goes.",
    "surface": {"pos": [0, Y0, 0.0], "reach": [1.08, 0.58]},
    "families": {name: {"pos": [0, 0, 0], "rot": [0, 0, 0], "scale": 1, "real": {"pos": [0, WT, 0] if name in ("fixtures", "tools") else [0, 0, 0], "rot": [0, 0, 0], "scale": 1}} for name in
                 ("fixtures", "tools", "pistol", "grip", "servo", "materials")},
    "home": home, "places": places, "lamps": lamps, "params": layout_params, "parents": parents, "cards": cards, "tips": tips, "grabs": grabs, "shots": shots,
}


def dump(path, data, check):
    text = json.dumps(data, indent=1) + "\n"
    if check:
        ok = os.path.exists(path) and open(path).read() == text
        print(("same   " if ok else "DIFFERS ") + os.path.relpath(path, REPO))
        return ok
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)
    print("wrote " + os.path.relpath(path, REPO))
    return True


def report():
    """What the greybox has that the exported families do not (and the other way), by id."""
    for name in sorted(families):
        path = os.path.join(ART, name, "export", "parts.json")
        if not os.path.exists(path):
            print("%-10s not exported: %d stand-in parts" % (name, len(families[name])))
            continue
        real = json.load(open(path))
        rp = {p["id"]: p for p in real["parts"]}
        gp = {p["id"]: p for p in families[name]}
        def marks(p, grey):
            if grey:
                g = p["grey"]
                return {m for m in g.get("marks", {})} | {m for m in g.get("paths", {})} | {m for m in g.get("zones", {})}
            return {m["id"] for m in p.get("marks") or []} | {m["id"] for m in p.get("paths") or []} | {m["id"] for m in p.get("zones") or []}
        print("%-10s exported %d parts; greybox %d" % (name, len(rp), len(gp)))
        print("   greybox only :", sorted(set(gp) - set(rp)))
        print("   real only    :", sorted(set(rp) - set(gp)))
        for pid in sorted(set(gp) & set(rp)):
            extra = marks(gp[pid], True) - marks(rp[pid], False)
            if extra:
                print("   %s: marks only in the greybox: %s" % (pid, sorted(extra)))
        real_marks = {p["id"] + "/" + m["id"] for p in real["parts"] for m in p.get("marks") or []}
        for pl in places:
            if pl["mark"] and pl["mark"].split("/")[0].split(".")[0] == name and pl["mark"] not in real_marks:
                print("   place with no such mark in the art:", pl["id"])
        rparams = {q["id"] for q in real.get("params", [])}
        gparams = {q["id"] for q in params.get(name, [])}
        print("   params greybox only:", sorted(gparams - rparams), "| real only:", sorted(rparams - gparams))


def main():
    check = "--check" in sys.argv
    ids = [p["id"] for fam in families.values() for p in fam]
    assert len(ids) == len(set(ids)), "duplicate part ids: " + str(sorted(i for i in ids if ids.count(i) > 1))
    pids = [p["id"] for p in places]
    assert len(pids) == len(set(pids)), "duplicate place ids"
    for pl in places:
        assert pl["on"] == "" or pl["on"] in ids, "place on unknown part: " + pl["id"]
        for a in pl["accepts"]:
            assert a == "*" or a in ids, pl["id"] + " accepts unknown part " + a
    for pid, where in home.items():
        assert pid in ids and (where == "gone" or where in pids), "bad home: " + pid + " -> " + where
    for fam in families.values():
        for p in fam:
            assert not p["parent"] or p["parent"] in ids, p["id"] + " has unknown parent " + str(p["parent"])
    if "--report" in sys.argv:
        report()
        return
    ok = True
    for old in glob.glob(os.path.join(OUT, "*.parts.json")):
        if os.path.basename(old).split(".")[0] not in families and not check:
            os.remove(old)
    for name, plist in families.items():
        data = {"family": name, "glb": None, "greybox": True, "blender": None, "generated": "2026-11-20", "parts": plist, "params": params.get(name, [])}
        ok &= dump(os.path.join(OUT, name + ".parts.json"), data, check)
    ok &= dump(LAYOUT, layout, check)
    print("%d parts, %d params, %d places (%d bound to marks), %d lamps, %d shots" % (len(ids), sum(len(v) for v in params.values()), len(places), sum(1 for p in places if p["mark"]), len(lamps), len(shots)))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
