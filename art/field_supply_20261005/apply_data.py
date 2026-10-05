#!/usr/bin/env python3
"""Field Supply data patch (5 October 2026). Idempotent: re-run after other branches (Codex) change the catalogs.

Writes, by text patch so unrelated serialized data is untouched:
  Data/CityCatalog.asset            new items (packs, pack upgrades, trauma kit, nano recharges, magazines),
                                    field_supply tags on Medkit and Field Backpack, the consumables list
  Resources/CharacterCatalog.asset  storage-slot equipment for the new packs (+ an upgrade socket on the Field
                                    Backpack) and the pack-upgrade modifications
  Data/Crafting/WardCrafting.asset  magazine-taught recipes (groups Gear and ArmourMod) and their group labels
  Data/npc_mira.asset               Basic General leaves field_supply_only stock to Field Supply
  Data/npc_tamsin.asset (+ .meta)   Tamsin, Field Supply's keeper: dialogue and counter profile

Usage: python3 art/field_supply_20261005/apply_data.py [--check]
--check validates the patched files with PyYAML and reports, without writing.
"""
import os, re, sys, uuid

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
A = os.path.join(ROOT, "unity/AthenHill/Assets/AthenHill")
CHECK = "--check" in sys.argv

# --------------------------------------------------------------------------------------------- YAML emission
PLAIN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_: .,'()/+%&!?-]*$")


def s(v):
    """A Unity-style scalar: plain when safe, otherwise double-quoted with \\x / \\u escapes."""
    if v is None or v == "":
        return ""
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, float):
        return str(int(v)) if v == int(v) else repr(v)
    if isinstance(v, int):
        return str(v)
    v = str(v)
    if PLAIN.match(v) and ": " not in v and " #" not in v and not v.endswith((" ", ":")) and not v.startswith(("-", "?", "!", "&", "*", "'", '"', "%", "@", "`")):
        return v
    out = []
    for ch in v:
        o = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif o < 0x20:
            out.append("\\x%02X" % o)
        elif o < 0x7F:
            out.append(ch)
        elif o <= 0xFF:
            out.append("\\x%02X" % o)
        else:
            out.append("\\u%04X" % o)
    return '"' + "".join(out) + '"'


def kv(ind, k, v):
    val = s(v)
    return f"{ind}{k}: {val}" if val != "" else f"{ind}{k}: "


def str_list(ind, k, values):
    if not values:
        return [f"{ind}{k}: []"]
    return [f"{ind}{k}:"] + [f"{ind}- {s(x)}" for x in values]


def obj_list(ind, k, rows, emit):
    if not rows:
        return [f"{ind}{k}: []"]
    lines = [f"{ind}{k}:"]
    for r in rows:
        body = emit(r)
        lines.append(f"{ind}- {body[0]}")
        lines += [f"{ind}  {b}" for b in body[1:]]
    return lines


MID = "·"

# --------------------------------------------------------------------------------------------- content
PACK_TAGS = ["storage", "storage:backpack", "backpack", "field_supply", "field_supply_only"]
MOD_TAGS = ["pack_mod", "field_supply", "field_supply_only"]

ITEMS = [
    # packs (storage slot)
    dict(id="canvas_rucksack", name="Stitched Canvas Rucksack", buy=36, sell=12, tags=PACK_TAGS, stack=1, rarity=0, icon="rucksack-icon", kg=1.9,
         desc="Heavy Karaveen canvas over a sewn-in frame sheet, with two side pockets and a pouch loop. Low tech and easy to patch: a real step up from the issue backpack."),
    dict(id="frame_pack", name="Karaveen Frame Pack", buy=64, sell=21, tags=PACK_TAGS, stack=1, rarity=0, icon="frame-pack-icon", kg=2.6,
         desc="A welded tube frame and padded hip belt put the load on your hips, the way caravan porters have carried it for generations. You carry more, not just pack more."),
    dict(id="porter_carrier", name="Porter's Load Carrier", buy=110, sell=36, tags=PACK_TAGS, stack=1, rarity=1, icon="load-carrier-icon", kg=3.1,
         desc="Mid-tier: a fab-alloy frame with load-lifter straps, a quick-release harness and pouch rails. Made in Ward for the Tube-node porters."),
    dict(id="courier_cargo_rig", name="Courier Cargo Rig", buy=160, sell=53, tags=PACK_TAGS, stack=1, rarity=1, icon="cargo-rig-icon", kg=3.4,
         desc="Mid-tier: a nanoweave shell over a compact servo spine that takes part of the load off your back. The best pack Field Supply sells."),
    # pack upgrades (fabricated at Brann's bench; Tamsin buys them back)
    dict(id="pack_side_pouches", name="Side Pouch Pair", buy=0, sell=4, tags=MOD_TAGS, stack=4, rarity=0, icon="side-pouches-icon", kg=0.35,
         desc="Two stitched webbing pouches that clip into a pack's pouch socket. More room for small parts."),
    dict(id="pack_hip_belt", name="Padded Hip Belt", buy=0, sell=5, tags=MOD_TAGS, stack=4, rarity=0, icon="hip-belt-icon", kg=0.4,
         desc="A quilted belt that bolts to a pack frame and moves the weight onto your hips."),
    dict(id="pack_nanoweave_pouch", name="Nanoweave Expansion Pouch", buy=0, sell=9, tags=MOD_TAGS, stack=4, rarity=1, icon="nanoweave-pouch-icon", kg=0.3,
         desc="A nanite-bonded pouch that folds flat when empty and swells to take a full load."),
    dict(id="pack_servo_lifter", name="Servo Load Lifter", buy=0, sell=12, tags=MOD_TAGS, stack=4, rarity=1, icon="servo-lifter-icon", kg=0.9,
         desc="A pair of salvaged droid servos on the frame's shoulder straps, taking part of the pack's weight as you move."),
    # med and nano
    dict(id="trauma_kit", name="Trauma Kit", buy=20, sell=7, tags=["consumable", "field_supply", "field_supply_only"], stack=10, rarity=1, icon="trauma-kit-icon", kg=1.2,
         desc="Haemostatic foam, a nanite suture gun and a pressure dressing. Closes what a medkit can't. Use with 2."),
    dict(id="nano_cell", name="Nano Recharge Cell", buy=6, sell=2, tags=["consumable", "nano", "field_supply", "field_supply_only"], stack=20, rarity=0, icon="nano-cell-icon", kg=0.25,
         desc="A sealed tier-one nanite cartridge. Refills your weapon's charge and overclocks the regulator for 15 seconds, so the charge keeps refilling while you fire. Use with 9."),
    dict(id="nano_surge_pack", name="Nano Surge Pack", buy=14, sell=5, tags=["consumable", "nano", "field_supply", "field_supply_only"], stack=10, rarity=1, icon="nano-surge-icon", kg=0.45,
         desc="Twin cartridges and a hot-running regulator shunt. Refills the charge and doubles its refill rate for 40 seconds, firing or not. Use with 9."),
    # digital magazines (never carried: GameSession.BuyMagazine)
    dict(id="mag_packcraft_12", name=f"Packcraft Quarterly {MID} Issue 12", buy=18, sell=0, tags=["magazine", "field_supply", "field_supply_only"], stack=1, rarity=0, icon="magazine-packcraft-icon", kg=0,
         desc="The fab co-op's quarterly for people who sew their own gear. This issue: a canvas rucksack from caravan webbing, clip-in side pouches and a padded hip belt."),
    dict(id="mag_karaveen_freight_3", name=f"Karaveen Freight Notes {MID} Vol. 3", buy=26, sell=0, tags=["magazine", "field_supply", "field_supply_only"], stack=1, rarity=0, icon="magazine-freight-icon", kg=0,
         desc="Patterns traded between caravan outfitters for generations, finally in print. The frame pack and the porter's load carrier, with load charts."),
    dict(id="mag_nanoweave_monthly", name=f"Nanoweave Monthly {MID} Load Tech", buy=40, sell=0, tags=["magazine", "field_supply", "field_supply_only"], stack=1, rarity=1, icon="magazine-nanoweave-icon", kg=0,
         desc="Ward's fab engineers on smart fabrics and assisted carry. Expansion pouches, a servo load lifter and the full courier cargo rig."),
    dict(id="mag_ward_armourer", name=f"Ward Armourer's Digest {MID} Liners & Plates", buy=22, sell=0, tags=["magazine", "field_supply", "field_supply_only"], stack=1, rarity=0, icon="magazine-armourer-icon", kg=0,
         desc="A Warden armourer's notes on the upgrades that keep plate carriers alive: impact and thermal liners and a replaceable ablative chest plate."),
]
ADD_TAGS = {"medkit": ["field_supply"], "field_backpack": ["field_supply"]}

CONSUMABLES = [
    dict(itemId="medkit", restoreHealth=40, restoreNano=0, overclockSeconds=0, overclockRegen=0),
    dict(itemId="trauma_kit", restoreHealth=90, restoreNano=0, overclockSeconds=0, overclockRegen=0),
    dict(itemId="nano_cell", restoreHealth=0, restoreNano=100, overclockSeconds=15, overclockRegen=0.5),
    dict(itemId="nano_surge_pack", restoreHealth=0, restoreNano=100, overclockSeconds=40, overclockRegen=1),
]

POUCH = dict(id="pouch", label="Pouch", type="pack_pouch")
POUCH2 = dict(id="pouch_2", label="Second pouch", type="pack_pouch")
FRAME = dict(id="frame", label="Frame mount", type="pack_frame")


def mods(storage, slots, carry):
    m = [dict(stat="storageCapacity", flat=storage, percent=0), dict(stat="packSlots", flat=slots, percent=0)]
    if carry:
        m.append(dict(stat="carryCapacity", flat=carry, percent=0))
    return m


EQUIPMENT = [
    dict(itemId="canvas_rucksack", tier=1, weight=1.9, sockets=[POUCH], requirements=[], modifiers=mods(32, 20, 2)),
    dict(itemId="frame_pack", tier=1, weight=2.6, sockets=[POUCH, FRAME], requirements=[], modifiers=mods(38, 22, 6)),
    dict(itemId="porter_carrier", tier=2, weight=3.1, sockets=[POUCH, POUCH2, FRAME], requirements=[], modifiers=mods(48, 26, 10)),
    dict(itemId="courier_cargo_rig", tier=2, weight=3.4, sockets=[POUCH, POUCH2, FRAME], requirements=[dict(stat="engineering", minimum=35)], modifiers=mods(58, 30, 14)),
]
BACKPACK_SOCKETS = [POUCH]  # the starting Field Backpack gains one pouch socket

MODIFICATIONS = [
    dict(itemId="pack_side_pouches", socketTypes=["pack_pouch"], modifiers=[dict(stat="packSlots", flat=4, percent=0), dict(stat="storageCapacity", flat=3, percent=0)]),
    dict(itemId="pack_hip_belt", socketTypes=["pack_frame"], modifiers=[dict(stat="carryCapacity", flat=4, percent=0)]),
    dict(itemId="pack_nanoweave_pouch", socketTypes=["pack_pouch"], modifiers=[dict(stat="packSlots", flat=6, percent=0), dict(stat="storageCapacity", flat=6, percent=0)]),
    dict(itemId="pack_servo_lifter", socketTypes=["pack_frame"], modifiers=[dict(stat="carryCapacity", flat=9, percent=0)]),
]

GEAR, ARMOUR_MOD = 6, 7


def I(id, n):
    return dict(kind="item", id=id, quantity=n)


def T(id, n):
    return dict(kind="tag", id=id, quantity=n)


def recipe(id, name, out, inputs, mag, group, seconds, hint, requirements=()):
    return dict(id=id, name=name, out=out, inputs=inputs, mag=mag, group=group, seconds=seconds, hint=hint, requirements=list(requirements))


SHELF = "Field Supply's magazine shelf: "
RECIPES = [
    recipe("recipe_canvas_rucksack", "Stitched Canvas Rucksack", "canvas_rucksack", [I("strap_webbing", 4), I("padded_liner", 2), I("rivet_stock", 2)],
           "mag_packcraft_12", GEAR, 12, SHELF + f"Packcraft Quarterly {MID} Issue 12."),
    recipe("recipe_pack_side_pouches", "Side Pouch Pair", "pack_side_pouches", [I("strap_webbing", 2), I("rivet_stock", 1)],
           "mag_packcraft_12", GEAR, 6, SHELF + f"Packcraft Quarterly {MID} Issue 12."),
    recipe("recipe_pack_hip_belt", "Padded Hip Belt", "pack_hip_belt", [I("strap_webbing", 2), I("padded_liner", 1), I("rivet_stock", 1)],
           "mag_packcraft_12", GEAR, 6, SHELF + f"Packcraft Quarterly {MID} Issue 12."),
    recipe("recipe_frame_pack", "Karaveen Frame Pack", "frame_pack", [I("alloy_plate", 2), I("strap_webbing", 4), I("padded_liner", 2), I("rivet_stock", 3)],
           "mag_karaveen_freight_3", GEAR, 16, SHELF + f"Karaveen Freight Notes {MID} Vol. 3.", [dict(stat="fabrication", minimum=10)]),
    recipe("recipe_porter_carrier", "Porter's Load Carrier", "porter_carrier", [I("alloy_plate", 3), I("strap_webbing", 5), I("padded_liner", 2), I("rivet_stock", 4), I("droid_servo_damaged", 1)],
           "mag_karaveen_freight_3", GEAR, 20, SHELF + f"Karaveen Freight Notes {MID} Vol. 3.", [dict(stat="fabrication", minimum=15)]),
    recipe("recipe_pack_nanoweave_pouch", "Nanoweave Expansion Pouch", "pack_nanoweave_pouch", [I("strap_webbing", 2), T("nanite:tier1", 6), I("copper_filament", 2)],
           "mag_nanoweave_monthly", GEAR, 10, SHELF + f"Nanoweave Monthly {MID} Load Tech.", [dict(stat="nanotechnology", minimum=10)]),
    recipe("recipe_pack_servo_lifter", "Servo Load Lifter", "pack_servo_lifter", [I("droid_servo_damaged", 2), I("wound_coil", 1), T("component:capacitor", 1), I("alloy_plate", 1)],
           "mag_nanoweave_monthly", GEAR, 14, SHELF + f"Nanoweave Monthly {MID} Load Tech.", [dict(stat="engineering", minimum=30)]),
    recipe("recipe_courier_cargo_rig", "Courier Cargo Rig", "courier_cargo_rig", [I("alloy_plate", 3), I("strap_webbing", 4), T("nanite:tier1", 8), I("wound_coil", 2), T("component:capacitor", 2), I("droid_servo_damaged", 2)],
           "mag_nanoweave_monthly", GEAR, 25, SHELF + f"Nanoweave Monthly {MID} Load Tech.", [dict(stat="fabrication", minimum=20), dict(stat="nanotechnology", minimum=10)]),
    recipe("recipe_armour_impact_liner", "Impact Liner", "armour_impact_liner", [I("padded_liner", 2), I("strap_webbing", 1), T("nanite:tier1", 2)],
           "mag_ward_armourer", ARMOUR_MOD, 8, SHELF + f"Ward Armourer's Digest {MID} Liners & Plates."),
    recipe("recipe_armour_thermal_liner", "Thermal Liner", "armour_thermal_liner", [I("padded_liner", 2), I("copper_filament", 2), T("nanite:tier1", 2)],
           "mag_ward_armourer", ARMOUR_MOD, 8, SHELF + f"Ward Armourer's Digest {MID} Liners & Plates."),
    recipe("recipe_armour_extra_plate", "Ablative Chest Plate", "armour_extra_plate", [I("alloy_plate", 2), I("rivet_stock", 2)],
           "mag_ward_armourer", ARMOUR_MOD, 10, SHELF + f"Ward Armourer's Digest {MID} Liners & Plates."),
]
GROUP_LABELS = [("Gear", "Packs and pack upgrades"), ("ArmourMod", "Armour upgrades")]


# --------------------------------------------------------------------------------------------- emitters
def emit_item(d):
    return [kv("", "id", d["id"]), kv("", "name", d["name"]), kv("", "description", d["desc"]), f"buyPrice: {d['buy']}",
            f"sellPrice: {d['sell']}", "startingQuantity: 0", *str_list("", "tags", d["tags"]), f"maxStack: {d['stack']}",
            "excludeFromTrade: 0", f"rarity: {d['rarity']}", "sellOnly: 0", kv("", "icon", d["icon"]), "partsPrice: 0", f"weightKg: {s(float(d['kg']))}"]


def emit_modifier(m):
    return [f"stat: {m['stat']}", f"flat: {s(m['flat'])}", f"percent: {s(m['percent'])}"]


def emit_req(r):
    return [f"stat: {r['stat']}", f"minimum: {s(r['minimum'])}"]


def emit_socket(k):
    return [f"id: {k['id']}", kv("", "label", k["label"]), f"type: {k['type']}"]


def emit_equipment(e):
    return [f"itemId: {e['itemId']}", *str_list("", "slots", ["storage"]), f"tier: {e['tier']}", "upgradeLevel: 0", f"weight: {s(float(e['weight']))}",
            *obj_list("", "modificationSockets", e["sockets"], emit_socket), *obj_list("", "requirements", e["requirements"], emit_req),
            "operatingRequirements: []", *obj_list("", "modifiers", e["modifiers"], emit_modifier), "installationFacility: ", "upgradeToItemId: ",
            "upgradeIngredients: []", "upgradeCredits: 0", "comfortableStrength: 0", "comfortableEndurance: 0", "movementPenalty: 0", "staminaPenalty: 0"]


def emit_modification(m):
    return [f"itemId: {m['itemId']}", "slots:", "- storage", *str_list("", "socketTypes", m["socketTypes"]), "requirements: []",
            "operatingRequirements: []", *obj_list("", "modifiers", m["modifiers"], emit_modifier)]


def emit_recipe(r):
    return [f"id: {r['id']}", kv("", "name", r["name"]), "stationId: station_field_fabricator", "requiresWeaponId: ", f"outputItemId: {r['out']}",
            "outputWeaponId: ", "outputSlots: []", *obj_list("", "inputs", r["inputs"], lambda i: [f"kind: {i['kind']}", f"id: {i['id']}", f"quantity: {i['quantity']}"]),
            "outputQuantity: 1", "knownByDefault: 0", *obj_list("", "unlocks", [dict(type="magazine", id=r["mag"])], lambda u: [f"type: {u['type']}", f"id: {u['id']}"]),
            *obj_list("", "requirements", r["requirements"], emit_req), "requiredTools: []", "requiredSchematics: []", f"group: {r['group']}",
            kv("", "lockedHint", r["hint"]), f"craftSeconds: {r['seconds']}"]


def emit_consumable(c):
    return [f"itemId: {c['itemId']}", f"restoreHealth: {s(c['restoreHealth'])}", f"restoreNano: {s(c['restoreNano'])}",
            f"overclockSeconds: {s(c['overclockSeconds'])}", f"overclockRegen: {s(c['overclockRegen'])}"]


def block(rows, emit, ind="  "):
    out = []
    for r in rows:
        b = emit(r)
        out.append(f"{ind}- {b[0]}")
        out += [f"{ind}  {x}" for x in b[1:]]
    return out


# --------------------------------------------------------------------------------------------- list surgery
def list_span(lines, key, ind="  "):
    """[start, end) of the entries under `ind+key:` (exclusive of the key line); start=end when empty or `[]`."""
    for i, l in enumerate(lines):
        if l == f"{ind}{key}:" or l == f"{ind}{key}: []":
            if l.endswith("[]"):
                lines[i] = f"{ind}{key}:"
                return i + 1, i + 1
            j = i + 1
            while j < len(lines) and (lines[j].startswith(ind + "- ") or lines[j].startswith(ind + "  ")):
                j += 1
            return i + 1, j
    raise KeyError(key)


def entries(lines, start, end, ind="  "):
    """Split [start,end) into entries: list of (s, e, first_line)."""
    out, cur = [], None
    for i in range(start, end):
        if lines[i].startswith(ind + "- "):
            if cur is not None:
                out.append((cur, i))
            cur = i
    if cur is not None:
        out.append((cur, end))
    return out


def upsert(lines, key, new_blocks, id_key, ind="  "):
    """Replace or append entries (by `- id_key: X`) in the list under key. Keeps others in place."""
    start, end = list_span(lines, key, ind)
    ids = {}
    for b in new_blocks:
        m = re.match(rf"{re.escape(ind)}- {id_key}: (\S+)", b[0])
        ids[m.group(1).strip('"')] = b
    kept, seen = [], set()
    for (a, b) in entries(lines, start, end, ind):
        m = re.match(rf"{re.escape(ind)}- {id_key}: (\S+)", lines[a])
        k = m.group(1).strip('"') if m else None
        if k in ids:
            kept += ids[k]
            seen.add(k)
        else:
            kept += lines[a:b]
    for k, b in ids.items():
        if k not in seen:
            kept += b
    lines[start:end] = kept


def group(rows, emit, id_key, ind="  "):
    out = []
    for r in rows:
        out.append(block([r], emit, ind))
    return out


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read().split("\n")


def write(path, lines):
    text = "\n".join(lines)
    if CHECK:
        return text
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return text


# --------------------------------------------------------------------------------------------- patches
def patch_city():
    p = os.path.join(A, "Data/CityCatalog.asset")
    L = read(p)
    upsert(L, "items", group(ITEMS, emit_item, "id"), "id")
    # field_supply tags on existing stock (Medkit, Field Backpack)
    start, end = list_span(L, "items")
    for (a, b) in reversed(entries(L, start, end)):  # bottom-up: insertions do not shift entries still to visit
        m = re.match(r"  - id: (\S+)", L[a])
        if not m or m.group(1) not in ADD_TAGS:
            continue
        ti = next(i for i in range(a, b) if L[i].startswith("    tags:"))
        if L[ti] == "    tags: []":
            L[ti] = "    tags:"
        tj = ti + 1
        while L[tj].startswith("    - "):
            tj += 1
        have = {L[i][6:] for i in range(ti + 1, tj)}
        for tag in ADD_TAGS[m.group(1)]:
            if tag not in have:
                L.insert(tj, f"    - {tag}")
                tj += 1
                b += 1
    # consumables + cooldown, between items and destinations
    for key in ("consumables", "consumableCooldown"):
        for i, l in enumerate(L):
            if l.startswith(f"  {key}:"):
                if key == "consumables":
                    st, en = list_span(L, key)
                    del L[i:en]
                else:
                    del L[i]
                break
    _, end = list_span(L, "items")
    L[end:end] = ["  consumables:"] + block(CONSUMABLES, emit_consumable) + ["  consumableCooldown: 1"]
    return p, write(p, L)


def patch_character():
    p = os.path.join(A, "Resources/CharacterCatalog.asset")
    L = read(p)
    upsert(L, "equipment", group(EQUIPMENT, emit_equipment, "itemId"), "itemId")
    upsert(L, "modifications", group(MODIFICATIONS, emit_modification, "itemId"), "itemId")
    # Field Backpack: one pouch socket (inserted after its weight, the serialized field order)
    start, end = list_span(L, "equipment")
    for (a, b) in entries(L, start, end):
        if L[a] != "  - itemId: field_backpack":
            continue
        ms = [i for i in range(a, b) if L[i].startswith("    modificationSockets:")]
        if ms:
            i = ms[0]
            j = i + 1
            if not L[i].endswith("[]"):
                while L[j].startswith("    - ") or L[j].startswith("      "):
                    j += 1
            del L[i:j]
        w = next(i for i in range(a, b) if L[i].startswith("    weight:"))
        L[w + 1:w + 1] = ["    " + x for x in obj_list("", "modificationSockets", BACKPACK_SOCKETS, emit_socket)]
        break
    return p, write(p, L)


def patch_crafting():
    p = os.path.join(A, "Data/Crafting/WardCrafting.asset")
    L = read(p)
    upsert(L, "recipes", group(RECIPES, emit_recipe, "id"), "id")
    upsert(L, "groupLabels", [[f"  - id: {g}", f"    label: {s(l)}"] for g, l in GROUP_LABELS], "id")
    return p, write(p, L)


def patch_mira():
    p = os.path.join(A, "Data/npc_mira.asset")
    L = read(p)
    i = L.index("  shop:")
    j = i + 1
    while j < len(L) and L[j].startswith("    "):
        j += 1
    # drop our keys (and their list items) before writing them again
    clean, skip = [], False
    for l in L[i + 1:j]:
        if re.match(r"    (stockTags|excludeTags|magazines):", l):
            skip = l.endswith(":")
            continue
        if skip and l.startswith("    - "):
            continue
        skip = False
        clean.append(l)
    clean += ["    stockTags: []", "    excludeTags:", "    - field_supply_only", "    magazines: 0"]
    L[i + 1:j] = clean
    return p, write(p, L)


TAMSIN_GUID_FILE = os.path.join(A, "Data/npc_tamsin.asset.meta")


def choice(id, label, action="", next="", requires="", flag=""):
    return dict(id=id, label=label, action=action, next=next, requires=requires, flag=flag)


TAMSIN = dict(
    id="npc_tamsin", name="Tamsin", role="Field Supply",
    entries=[dict(node="first_visit", requires="!flag:tamsin_met")],
    nodes=[
        dict(id="first_visit", title="Field Supply",
             text="Mind the step. Tamsin, Field Supply. Twenty years outfitting Karaveen caravans before my knees voted to stay in Ward. Packs on the wall, medkits and nano cells under the counter, and the magazine shelf by the window. Fabricators swear by it.",
             choices=[choice("shop", "Show me the stock.", "shop", flag="tamsin_met"), choice("magazines", "What's on the magazine shelf?", next="magazines", flag="tamsin_met"),
                      choice("close", "Another time.", "close", flag="tamsin_met")]),
        dict(id="greeting", title="Field Supply",
             text="Back again. New issues on the shelf, fresh cells under the counter. What are we carrying today?",
             choices=[choice("shop", "Let me see the stock.", "shop"), choice("packs", "Which pack should I carry?", next="packs"), choice("supplies", "Medkits and nano cells?", next="supplies")]),
        dict(id="magazines", title="The magazine shelf",
             text="Digital issues from the fab co-op and the Karaveen freight houses. Download one to your slate and Brann's bench in Salvage can make what's inside. Rucksacks, frame packs, pouches, hip belts, even armour liners. Cheaper than buying, if you can scavenge the webbing.",
             choices=[choice("shop", "Show me the shelf.", "shop"), choice("packs", "And the packs?", next="packs"), choice("close", "Later.", "close")]),
        dict(id="packs", title="Packs",
             text="Weight's the real limit, not room. A frame pack puts the load on your hips, so you carry more, not just stuff more in. The low tech ones you can patch yourself. The mid-tier rigs want fab alloy and servos. Every pack has sockets for pouches, and the frames take a belt or a lifter.",
             choices=[choice("shop", "Show me the packs.", "shop"), choice("supplies", "Medkits and nano cells?", next="supplies"), choice("close", "Thanks, Tamsin.", "close")]),
        dict(id="supplies", title="Med and nano",
             text="Medkits patch you up mid-fight, press 2. The trauma kit closes worse. A nano cell refills your weapon and overclocks the regulator, so the charge keeps coming back while you fire, press 9. The surge pack runs hotter and longer.",
             choices=[choice("shop", "I'll take some.", "shop"), choice("magazines", "Tell me about the magazines.", next="magazines"), choice("close", "Good to know.", "close")]),
    ],
    shop=dict(title="Field Supply", subtitle=f"Tamsin {MID} Packs, med and nano, magazines", supplies=1, parts=0, salvage=0,
              stockTags=["field_supply"], excludeTags=[], magazines=1),
)


def patch_tamsin():
    p = os.path.join(A, "Data/npc_tamsin.asset")
    if os.path.exists(TAMSIN_GUID_FILE):
        guid = re.search(r"guid: ([0-9a-f]{32})", open(TAMSIN_GUID_FILE).read()).group(1)
    else:
        guid = uuid.uuid4().hex
        if not CHECK:
            with open(TAMSIN_GUID_FILE, "w", newline="\n") as f:
                f.write(f"fileFormatVersion: 2\nguid: {guid}\nNativeFormatImporter:\n  externalObjects: {{}}\n  mainObjectFileID: 11400000\n"
                        "  userData: \n  assetBundleName: \n  assetBundleVariant: \n")
    # keep voice clip references the voice pass may have added (by node id)
    voices = {}
    if os.path.exists(p):
        cur = None
        for l in open(p, encoding="utf-8").read().split("\n"):
            m = re.match(r"  - id: (\S+)", l)
            if m:
                cur = m.group(1)
            m = re.match(r"    voice: (\{.*\})", l)
            if m and cur and "guid" in m.group(1):
                voices[cur] = m.group(1)
    t = TAMSIN
    L = ["%YAML 1.1", "%TAG !u! tag:unity3d.com,2011:", "--- !u!114 &11400000", "MonoBehaviour:", "  m_ObjectHideFlags: 0",
         "  m_CorrespondingSourceObject: {fileID: 0}", "  m_PrefabInstance: {fileID: 0}", "  m_PrefabAsset: {fileID: 0}", "  m_GameObject: {fileID: 0}",
         "  m_Enabled: 1", "  m_EditorHideFlags: 0", "  m_Script: {fileID: 11500000, guid: 5a584a25f7a2f6c23a420ed9d0c79f73, type: 3}",
         "  m_Name: npc_tamsin", "  m_EditorClassIdentifier: AthenHill.Runtime::AthenHill.NpcDefinition",
         f"  id: {t['id']}", f"  displayName: {t['name']}", kv("  ", "role", t["role"])]
    L += obj_list("  ", "entries", t["entries"], lambda e: [f"node: {e['node']}", kv("", "requires", e["requires"])])
    def emit_node(n):
        out = [f"id: {n['id']}", kv("", "title", n["title"]), kv("", "text", n["text"]), f"voice: {voices.get(n['id'], '{fileID: 0}')}"]
        out += obj_list("", "choices", n["choices"], lambda c: [f"id: {c['id']}", kv("", "label", c["label"]), kv("", "next", c["next"]), kv("", "action", c["action"]),
                                                               kv("", "requires", c["requires"]), kv("", "setFlag", c["flag"])])
        return out
    L += obj_list("  ", "nodes", t["nodes"], emit_node)
    sh = t["shop"]
    L += ["  shop:", kv("    ", "title", sh["title"]), kv("    ", "subtitle", sh["subtitle"]), f"    supplies: {sh['supplies']}", f"    parts: {sh['parts']}",
          f"    salvage: {sh['salvage']}", *["    " + x for x in str_list("", "stockTags", sh["stockTags"])],
          *["    " + x for x in str_list("", "excludeTags", sh["excludeTags"])], f"    magazines: {sh['magazines']}", ""]
    return p, write(p, L)


# --------------------------------------------------------------------------------------------- validation
def validate(path, text):
    try:
        import yaml
    except ImportError:
        print("  (PyYAML missing: structural check skipped)")
        return True
    body = re.sub(r"^--- !u!\d+ &\d+.*$", "---", text, flags=re.M)
    body = "\n".join(l for l in body.split("\n") if not l.startswith("%"))
    try:
        d = yaml.safe_load(body)
    except Exception as e:
        print("  YAML ERROR", path, e)
        return False
    bad = re.findall(r"\n\s*\n\s*- ", text)
    if bad:
        print("  blank line inside a list:", path)
        return False
    return d is not None


if __name__ == "__main__":
    ok = True
    for fn in (patch_city, patch_character, patch_crafting, patch_mira, patch_tamsin):
        path, text = fn()
        v = validate(path, text)
        ok &= v
        print(("checked " if CHECK else "wrote   ") + os.path.relpath(path, ROOT), "OK" if v else "FAILED")
    sys.exit(0 if ok else 1)
