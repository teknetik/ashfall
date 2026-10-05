#!/usr/bin/env python3
"""Ward home pass (5 Oct 2026): serialized data for the new controls, hotbar, journal and home. Idempotent text patches
(each replacement checks for the new text first), so it can be re-run after other passes (or Codex) rewrite these assets.

  CityCatalog       Ward notes text (mouse look, Tab, J); hotbar labels for the four consumables.
  npc_ossa          the locker and range lines name 2 (sidearm) instead of 7; their old voice takes say "7", so the voice
                    reference is cleared on those two nodes (clip GUIDs kept below to restore once re-voiced).
  WardFieldOrders   the Long Arm completion line names 1 (primary) instead of 8.
  AthenHill.unity   the Berms primer's serialized radio lines (draw with 2; left mouse fires).
  npc_linn          the housing roll: "Is there anywhere in Ward I could stay?" → lease the container home.

Unity's YAML reader is stricter than pyyaml (memory: a blank line between list items or a plain scalar containing ": "
loads the asset EMPTY): replacements keep line structure, and every patched asset is re-parsed with pyyaml at the end.
"""
import pathlib, re, sys
R = pathlib.Path(__file__).resolve().parents[2]
A = R / "unity/AthenHill/Assets/AthenHill"
OSSA_VOICES = {"locker": "09c46f3a39264a9b84f50cdfa577b3d7", "range": "45342f2c12824efd9a835c1df7a000f5"}
changed = []


def patch(path, pairs):
    p = A / path
    s = p.read_text()
    before = s
    for old, new in pairs:
        if new in s:
            continue
        if old not in s:
            sys.exit(f"{path}: neither the old nor the new text was found:\n  {old[:120]}")
        s = s.replace(old, new, 1)
    if s != before:
        p.write_text(s)
        changed.append(path)
    return s


# ---- CityCatalog: notes and hotbar labels
cat = A / "Data/CityCatalog.asset"
patch("Data/CityCatalog.asset", [(
    "WASD or arrows move; Shift runs; left-drag turns the camera. The mouse wheel zooms into first person. E interacts.",
    "WASD or arrows move; Shift runs; the mouse turns the camera (hold Left Alt for a pointer). The mouse wheel zooms into first person. E interacts. Tab opens the field pack and J the journal.")])
s = cat.read_text()
labels = {"medkit": "Medkit", "trauma_kit": "Trauma", "nano_cell": "Nano", "nano_surge_pack": "Surge"}
block = re.search(r"\n  consumables:\n(.*?)\n  consumableCooldown:", s, re.S)
if not block:
    sys.exit("CityCatalog: consumables block not found")
body = block.group(1)
entries = re.split(r"(?=  - itemId: )", body)
out = []
for e in entries:
    if not e.strip():
        out.append(e)
        continue
    iid = re.match(r"  - itemId: (\S+)", e).group(1)
    if iid in labels and "hotbarLabel:" not in e:
        e = e.rstrip("\n") + f"\n    hotbarLabel: {labels[iid]}\n"
    out.append(e)
nbody = "".join(out).rstrip("\n")
if nbody != body.rstrip("\n"):
    s = s[:block.start(1)] + nbody + s[block.end(1):]
    cat.write_text(s)
    changed.append("Data/CityCatalog.asset (hotbar labels)")

# ---- Ossa: keys in two dialogue nodes, voices cleared there
s = patch("Data/npc_ossa.asset", [
    ("Walk up to it and press E. Press 7 to draw the pistol outside the walls;", "Walk up to it and press E. Press 2 to draw the pistol outside the walls;"),
    ("Draw with 7. Hold right mouse to aim, then left click to fire; F fires from the hip.", "Draw with 2. Left mouse fires, and so does F; hold right mouse to steady your aim.")])
p = A / "Data/npc_ossa.asset"
s2 = s
for node, guid in OSSA_VOICES.items():
    s2 = s2.replace("    voice: {fileID: 8300000, guid: %s, type: 3}" % guid, "    voice: {fileID: 0}")
if s2 != s:
    p.write_text(s2)
    changed.append("Data/npc_ossa.asset (voices)")

# ---- Long Arm completion line
patch("Data/Crafting/WardFieldOrders.asset", [
    ("equip it in your loadout, and press 8 out here to draw it.", "equip it in your loadout, and press 1 out here to draw it.")])

# ---- Scene: the primer's serialized radio lines
patch("Scenes/AthenHill.unity", [
    ("  lineDraw: It runs on nano charge, not rounds. Press 7 to draw it.", "  lineDraw: It runs on nano charge, not rounds. Press 2 to draw it."),
    ("Hold right mouse to aim, then left click to fire; F fires from the hip. Knock down all three.", "Left mouse fires, and so does F; hold right mouse to steady your aim. Knock down all three.")])

# ---- Linn: the housing roll (lease the container home on the south wall)
LINN_CHOICE = """    - id: housing
      label: Is there anywhere in Ward I could stay?
      next: housing
      action:
      requires: primer, !flag:home_leased
      setFlag: home_asked
"""
LINN_NODES = """  - id: housing
    title: The housing roll
    text: There is a rust-red container against the south wall, behind the Nanofab yard. The family who fitted it out went with a Karaveen caravan last season. Bunk, a steel locker, shelves, a window that shuts. Forty credits takes the lease off the roll and the key is yours. Keep the locker for your salvage; the Berms will fill your pack faster than you think.
    voice: {fileID: 0}
    choices:
    - id: lease
      label: I'll take the lease (40 credits).
      next: housing_leased
      action: lease_home
      requires:
      setFlag:
    - id: later
      label: Not yet. I'll come back.
      next:
      action: close
      requires:
      setFlag:
  - id: housing_leased
    title: The housing roll
    text: Then it is yours. The door knows you now. Rest on the bunk when the Berms wear you down, and come back up the hill when you need someone to talk to.
    voice: {fileID: 0}
    choices:
    - id: leave
      label: Thank you, Linn.
      next:
      action: close
      requires:
      setFlag:
"""
p = A / "Data/npc_linn.asset"
s = p.read_text()
before = s
if "id: housing\n" not in s:
    anchor = "    - id: tree\n      label: Why does everyone meet here?\n      next: hill\n      action: \n"
    if anchor not in s:
        sys.exit("npc_linn: greeting choices not found")
    s = s.replace(anchor, anchor + LINN_CHOICE, 1)
    s = s.rstrip("\n") + "\n" + LINN_NODES
# (5 Oct 03:50) asking about the housing roll records home_asked for the journal
s = s.replace("      requires: primer, !flag:home_leased\n      setFlag:\n", "      requires: primer, !flag:home_leased\n      setFlag: home_asked\n")
if s != before:
    p.write_text(s)
    changed.append("Data/npc_linn.asset")

# ---- validate every touched asset with pyyaml (Unity tags stripped)
try:
    import yaml
except ImportError:
    yaml = None
if yaml:
    for rel in ["Data/CityCatalog.asset", "Data/npc_ossa.asset", "Data/npc_linn.asset", "Data/Crafting/WardFieldOrders.asset"]:
        txt = re.sub(r"^--- !u!.*$", "---", (A / rel).read_text(), flags=re.M)
        txt = re.sub(r"^%TAG.*$", "", txt, flags=re.M)
        for doc in yaml.safe_load_all(txt):
            pass
print("changed:", changed or "nothing (already applied)")
