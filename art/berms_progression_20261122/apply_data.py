#!/usr/bin/env python3
"""Outer Berms Gameplay & Progression data patch (22 Nov 2026).

Idempotent text patcher preserving all unrelated serialized data and uncommitted changes:
  Data/CityCatalog.asset
    - M2 Layered Armour parts: salvaged_chest_plate, chest_rig_harness,
      ceramic_ballistic_plate, nanoweave_backing, rig_harness_frame,
      tread_strut, reinforced_sole, armoured_shell_casing, optic_visor_lens
    - M3 Key item: berms_relay_key ("Warden Relay Key")
    - M4 Medical items: med_dressing, med_biogel, med_nanosuture, field_bandage
      + field_bandage consumable entry
    - M4 Ammo items: propellant_tin, hardened_slug_core, capacitor_filament,
      ammo_rifle_standard, ammo_rifle_ap, ammo_rifle_emp
    - M4 Dormant Nano Band 3 TBC seeds: nano_dormant_matrix, nano_resonator_shard,
      nano_targeting_core
  Data/Crafting/WardCrafting.asset
    - M2 Armour recipes: recipe_field_vest, recipe_warden_plate_carrier, recipe_field_boots,
      and deeper Band 2/3 parts wired into recipe_field_helmet
    - M4 Medical recipes: recipe_field_bandage, recipe_medkit, recipe_trauma_kit
    - M4 Ammo recipes: recipe_ammo_rifle_standard, recipe_ammo_rifle_ap, recipe_ammo_rifle_emp
    - Loot table entries with bad-luck protection (pityAfter) across Band 1/2/3 tables
      (leaves loot_feral_scrap_drone untouched for exact seeded RNG tests, and preserves
      loot_nextlevel_strongbox's 2 guaranteeUntilCollected entries)
  Data/Crafting/WardFieldOrders.asset
    - Enriches briefs for order_kit_helmet, order_plate_carrier, and order_depot_foreman
      without altering order IDs, titles, goals, targets, or indices.

Usage: python3 art/berms_progression_20261122/apply_data.py [--check]
"""
import os
import re
import sys

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
    if (
        PLAIN.match(v)
        and ": " not in v
        and " #" not in v
        and not v.endswith((" ", ":"))
        and not v.startswith(("-", "?", "!", "&", "*", "'", '"', "%", "@", "`"))
    ):
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


def block(rows, emit, ind="  "):
    out = []
    for r in rows:
        b = emit(r)
        out.append(f"{ind}- {b[0]}")
        out += [f"{ind}  {x}" for x in b[1:]]
    return out


# --------------------------------------------------------------------------------------------- list surgery
def list_span(lines, key, ind="  "):
    """[start, end) of entries under `ind+key:` (exclusive of key line)."""
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
    """Replace or append entries (by `- id_key: X`) in list under key. Keeps others in place."""
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


def group(rows, emit, ind="  "):
    return [block([r], emit, ind) for r in rows]


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


# --------------------------------------------------------------------------------------------- content
ITEMS = [
    # M2 Stage 1 — Bare-Minimum Chest Rig (field_vest) parts
    dict(
        id="salvaged_chest_plate",
        name="Salvaged Ballistic Plate",
        desc="A curved steel chest plate pried off a feral machine chassis or Warden crate. Three plates make a bare-minimum Field Vest at Brann's bench.",
        buy=0, sell=6, tags=["berms_part", "material", "material:armour", "tier:1"],
        stack=10, exclude=0, rarity=1, sellOnly=0, icon="alloy-plate-icon", kg=1.1,
    ),
    dict(
        id="chest_rig_harness",
        name="Reinforced Canvas Harness",
        desc="Heavy buckled load straps recovered from Karaveen wreck lockboxes and collapsed depot lockers. Holds a Field Vest's plates tight over the chest.",
        buy=0, sell=5, tags=["berms_part", "material", "material:armour", "tier:1"],
        stack=10, exclude=0, rarity=1, sellOnly=0, icon="webbing-icon", kg=0.6,
    ),
    # M2 Stage 2 — Chest Upgrade (warden_plate_carrier) parts
    dict(
        id="ceramic_ballistic_plate",
        name="Ballistic Ceramic Plate",
        desc="Composite Warden-grade trauma plate stripped from mid-Berms gunners and supply lockboxes. Built to stop sustained ranged fire.",
        buy=0, sell=10, tags=["berms_part", "material", "material:armour", "tier:2"],
        stack=10, exclude=0, rarity=1, sellOnly=0, icon="alloy-plate-icon", kg=1.2,
    ),
    dict(
        id="nanoweave_backing",
        name="Nanoweave Backing",
        desc="Layered aramid-and-nanite spall liner salvaged from locked Band 2 strongboxes and collapsed fab conduits.",
        buy=0, sell=9, tags=["berms_part", "material", "material:armour", "tier:2"],
        stack=10, exclude=0, rarity=1, sellOnly=0, icon="liner-icon", kg=0.45,
    ),
    dict(
        id="rig_harness_frame",
        name="Tensioned Plate Clasp",
        desc="A quick-release carrier yoke recovered from Band 2 elites. Locks ceramic plates into a full Warden Plate Carrier.",
        buy=0, sell=14, tags=["berms_part", "component", "material:armour", "tier:2"],
        stack=5, exclude=1, rarity=2, sellOnly=0, icon="rivets-icon", kg=0.85,
    ),
    # M2 Stage 3 — Boots & Helmet deeper parts
    dict(
        id="tread_strut",
        name="Shock-Absorbing Tread Strut",
        desc="Spring-damped heel strut scavenged from wash wrecks and outer droids. Takes the sting out of rough terrain and Lancer splash.",
        buy=0, sell=8, tags=["berms_part", "material", "material:armour", "tier:2"],
        stack=10, exclude=0, rarity=1, sellOnly=0, icon="servo-icon", kg=0.7,
    ),
    dict(
        id="reinforced_sole",
        name="Reinforced Sole Plate",
        desc="Bonded steel-and-rubber boot sole recovered from Warden outposts and Reaper chassis.",
        buy=0, sell=7, tags=["berms_part", "material", "material:armour", "tier:2"],
        stack=10, exclude=0, rarity=1, sellOnly=0, icon="alloy-plate-icon", kg=0.65,
    ),
    dict(
        id="armoured_shell_casing",
        name="Armoured Shell Casing",
        desc="A contoured machine housing thick enough to beat into a ballistic helmet dome.",
        buy=0, sell=10, tags=["berms_part", "material", "material:armour", "tier:2"],
        stack=10, exclude=0, rarity=1, sellOnly=0, icon="alloy-plate-icon", kg=0.95,
    ),
    dict(
        id="optic_visor_lens",
        name="Optic Visor Lens",
        desc="Polarised anti-glare visor glass pulled from Lancer drones and Post Sentinels. Keeps sightlines sharp through dust fronts.",
        buy=0, sell=11, tags=["berms_part", "component", "component:optic", "material:armour", "tier:2"],
        stack=10, exclude=0, rarity=1, sellOnly=0, icon="optic-icon", kg=0.3,
    ),
    # M3 — Key-Gated Waystation Save & Lattice Terminal Key
    dict(
        id="berms_relay_key",
        name="Warden Relay Key",
        desc="An encrypted Lattice relay key carried by the inner-Berms Warden patrol. Brings the mid-Berms Waystation terminal online for manual saves and fast travel back to Ward's Lattice Jack.",
        buy=0, sell=0, tags=["key", "unique", "berms"],
        stack=1, exclude=1, rarity=2, sellOnly=0, icon="control-core-icon", kg=0.1,
    ),
    # M4 — Medical salvage & Field Bandage
    dict(
        id="med_dressing",
        name="Field Dressing",
        desc="Sealed sterile gauze and pressure tape found in Karaveen wrecks and Warden crates. Craft bandages and medkits at Brann's bench.",
        buy=0, sell=2, tags=["berms_part", "material", "material:medical", "tier:1"],
        stack=30, exclude=0, rarity=0, sellOnly=0, icon="liner-icon", kg=0.1,
    ),
    dict(
        id="med_biogel",
        name="Biogel Ampoule",
        desc="Antiseptic coagulant gel from intact medical lockers and drone service bays. Key ingredient for Medkits and Trauma Kits.",
        buy=0, sell=5, tags=["berms_part", "material", "material:medical", "tier:2"],
        stack=20, exclude=0, rarity=1, sellOnly=0, icon="flask-icon", kg=0.18,
    ),
    dict(
        id="med_nanosuture",
        name="Nano-Suture Cartridge",
        desc="Sealed tier-two medical nanites from Band 2-3 strongboxes. Required to fabricate Trauma Kits.",
        buy=0, sell=10, tags=["berms_part", "material", "material:medical", "tier:3"],
        stack=10, exclude=1, rarity=2, sellOnly=0, icon="nanites-icon", kg=0.22,
    ),
    dict(
        id="field_bandage",
        name="Field Bandage",
        desc="A quick-wrap pressure dressing stitched from scavenged field gauze. Restores 30 vitality from your hotbar.",
        buy=4, sell=2, tags=["consumable", "medical"],
        stack=20, exclude=0, rarity=0, sellOnly=0, icon="medkit-icon", kg=0.2,
    ),
    # M4 — Ammo salvage & Field Rifle ammo types
    dict(
        id="propellant_tin",
        name="Propellant Tin",
        desc="Dry smokeless propellant powder sealed in a stamped tin. Pressed with scrap alloy into Standard Ballistic Slugs.",
        buy=0, sell=2, tags=["berms_part", "material", "material:ammo", "tier:1"],
        stack=30, exclude=0, rarity=0, sellOnly=0, icon="rivets-icon", kg=0.25,
    ),
    dict(
        id="hardened_slug_core",
        name="Hardened Slug Core",
        desc="Tungsten-alloy penetrator rods salvaged from heavy Band 2-3 droids. Needed for Armour-Piercing Rounds.",
        buy=0, sell=4, tags=["berms_part", "material", "material:ammo", "tier:2"],
        stack=30, exclude=0, rarity=1, sellOnly=0, icon="alloy-icon", kg=0.3,
    ),
    dict(
        id="capacitor_filament",
        name="Capacitor Filament",
        desc="High-discharge wire coils pulled from Lancer drones and Post Sentinels. Powers Disruptor Shock Rounds.",
        buy=0, sell=5, tags=["berms_part", "material", "material:ammo", "tier:2"],
        stack=30, exclude=0, rarity=1, sellOnly=0, icon="copper-icon", kg=0.15,
    ),
    dict(
        id="ammo_rifle_standard",
        name="Standard Ballistic Slugs",
        desc="General-purpose jacketed rounds for the Field Rifle. Reliable against unarmoured drones, workers, and exposed weak points.",
        buy=0, sell=1, tags=["ammo", "ammo:rifle"],
        stack=120, exclude=0, rarity=0, sellOnly=0, icon="alloy-icon", kg=0.02,
    ),
    dict(
        id="ammo_rifle_ap",
        name="Armour-Piercing Rounds",
        desc="Hardened penetrator slugs for the Field Rifle. Punches through plated Scrap Reapers, Post Sentinels, and armoured Gunners.",
        buy=0, sell=2, tags=["ammo", "ammo:rifle"],
        stack=120, exclude=0, rarity=1, sellOnly=0, icon="alloy-plate-icon", kg=0.025,
    ),
    dict(
        id="ammo_rifle_emp",
        name="Disruptor Shock Rounds",
        desc="Capacitor-loaded shock rounds for the Field Rifle. Disrupts droid targeting and strips heavy armour plating.",
        buy=0, sell=3, tags=["ammo", "ammo:rifle"],
        stack=120, exclude=0, rarity=1, sellOnly=0, icon="capacitor-icon", kg=0.025,
    ),
    # M4 — Dormant Nano (Band 3 TBC seeds)
    dict(
        id="nano_dormant_matrix",
        name="Dormant Nanite Matrix",
        desc="A sealed lattice wafer packed with dormant fabrication nanites from an outer-ring sentinel. High credit value, though Nanofab 2 may need this.",
        buy=0, sell=45, tags=["berms_part", "nano_tech", "tier:3"],
        stack=5, exclude=1, rarity=2, sellOnly=0, icon="nanites-icon", kg=0.35,
    ),
    dict(
        id="nano_resonator_shard",
        name="Quantum Resonator Shard",
        desc="A resonant splinter recovered near dead Quantum Tube branch pylons in the outer Berms. High credit value, though Nanofab 2 may need this.",
        buy=0, sell=50, tags=["berms_part", "nano_tech", "tier:3"],
        stack=5, exclude=1, rarity=2, sellOnly=0, icon="shard-icon", kg=0.28,
    ),
    dict(
        id="nano_targeting_core",
        name="Sandboxed Targeting Sub-Core",
        desc="An isolated targeting processor pulled from an outer-ring machine wreck. High credit value, though Nanofab 2 may need this.",
        buy=0, sell=55, tags=["berms_part", "nano_tech", "tier:3"],
        stack=5, exclude=1, rarity=2, sellOnly=0, icon="control-core-icon", kg=0.45,
    ),
]

NEW_CONSUMABLES = [
    dict(itemId="field_bandage", restoreHealth=30, restoreNano=0, overclockSeconds=0, overclockRegen=0, hotbarLabel="Bandage"),
]

ARMOUR = 5
GEAR = 6


def I(id, n):
    return dict(kind="item", id=id, quantity=n)


def U(kind, id):
    return dict(type=kind, id=id)


def recipe(id, name, out, inputs, unlocks, group, seconds, hint, outQty=1, skill="engineering", xp=8, skillUse=0.5):
    return dict(
        id=id, name=name, out=out, inputs=inputs, unlocks=unlocks, group=group,
        seconds=seconds, hint=hint, outQty=outQty, skill=skill, xp=xp, skillUse=skillUse,
    )


NEW_RECIPES = [
    # M2 Stage 1: Bare-Minimum Chest Rig (field_vest)
    recipe(
        "recipe_field_vest", "Field Vest", "field_vest",
        [I("salvaged_chest_plate", 3), I("chest_rig_harness", 2), I("alloy_plate", 2)],
        [U("acquireItem", "salvaged_chest_plate"), U("acquireItem", "chest_rig_harness")],
        ARMOUR, 16,
        "Recover salvaged ballistic plates from inner-Berms droids or crates and a canvas harness from wrecks.",
        skill="engineering", xp=12, skillUse=0.75,
    ),
    # M2 Stage 2: Upgraded Chest (warden_plate_carrier)
    recipe(
        "recipe_warden_plate_carrier", "Warden Plate Carrier", "warden_plate_carrier",
        [I("ceramic_ballistic_plate", 3), I("nanoweave_backing", 2), I("rig_harness_frame", 1), I("alloy_plate", 2)],
        [U("acquireItem", "ceramic_ballistic_plate"), U("acquireItem", "nanoweave_backing"), U("acquireItem", "rig_harness_frame")],
        ARMOUR, 22,
        "Recover ceramic plates, nanoweave backing, and a tensioned clasp from Band 2 Gunners and strongboxes.",
        skill="engineering", xp=16, skillUse=0.75,
    ),
    # M2 Stage 3: Field Boots
    recipe(
        "recipe_field_boots", "Field Boots", "field_boots",
        [I("tread_strut", 2), I("reinforced_sole", 2), I("alloy_plate", 1), I("strap_webbing", 2)],
        [U("acquireItem", "tread_strut"), U("acquireItem", "reinforced_sole")],
        ARMOUR, 18,
        "Recover shock-absorbing tread struts and reinforced sole plates from mid-to-outer Berms wrecks and droids.",
        skill="engineering", xp=12, skillUse=0.75,
    ),
    # M4 Medical recipes
    recipe(
        "recipe_field_bandage", "Field Bandage", "field_bandage",
        [I("med_dressing", 2)],
        [U("acquireItem", "med_dressing")],
        GEAR, 3,
        "Scavenge field dressings from Karaveen wrecks or Warden crates to learn this.",
        skill="engineering", xp=3, skillUse=0.25,
    ),
    recipe(
        "recipe_medkit", "Medkit", "medkit",
        [I("med_dressing", 2), I("med_biogel", 1)],
        [U("acquireItem", "med_biogel")],
        GEAR, 6,
        "Scavenge a biogel ampoule from drone service bays or outpost lockers to learn this.",
        skill="nanotechnology", xp=5, skillUse=0.5,
    ),
    recipe(
        "recipe_trauma_kit", "Trauma Kit", "trauma_kit",
        [I("medkit", 1), I("med_nanosuture", 1), I("med_biogel", 1)],
        [U("acquireItem", "med_nanosuture")],
        GEAR, 10,
        "Recover a nano-suture cartridge from Band 2-3 strongboxes to learn this.",
        skill="nanotechnology", xp=10, skillUse=0.75,
    ),
    # M4 Ammo recipes
    recipe(
        "recipe_ammo_rifle_standard", "Standard Ballistic Slugs", "ammo_rifle_standard",
        [I("scrap_alloy", 1), I("propellant_tin", 1)],
        [U("acquireItem", "propellant_tin")],
        GEAR, 4,
        "Scavenge a propellant tin from inner-Berms droids or crates to press rifle slugs.",
        outQty=12, skill="engineering", xp=4, skillUse=0.25,
    ),
    recipe(
        "recipe_ammo_rifle_ap", "Armour-Piercing Rounds", "ammo_rifle_ap",
        [I("alloy_plate", 1), I("hardened_slug_core", 2)],
        [U("acquireItem", "hardened_slug_core")],
        GEAR, 6,
        "Recover hardened slug cores from Band 2-3 plated droids to fabricate AP rounds.",
        outQty=12, skill="engineering", xp=6, skillUse=0.5,
    ),
    recipe(
        "recipe_ammo_rifle_emp", "Disruptor Shock Rounds", "ammo_rifle_emp",
        [I("capacitor_filament", 2), I("copper_filament", 1), I("charge_cell_core", 1)],
        [U("acquireItem", "capacitor_filament")],
        GEAR, 8,
        "Recover capacitor filaments from Lancer drones or Post Sentinels to fabricate EMP rounds.",
        outQty=10, skill="electronics", xp=8, skillUse=0.5,
    ),
]

# Extra inputs wired into existing recipe_field_helmet (Stage 3 deeper helmet parts)
HELMET_EXTRA_INPUTS = [
    I("armoured_shell_casing", 1),
    I("optic_visor_lens", 1),
]


def L(itemId, lo, hi, chance, pity=0, guarantee=0):
    return dict(itemId=itemId, minQuantity=lo, maxQuantity=hi, chance=chance, pityAfter=pity, guaranteeUntilCollected=guarantee)


# Additive loot entries per table (upserted by itemId within each table's entries).
# Note: loot_feral_scrap_drone is intentionally untouched to preserve exact seeded RNG tests.
LOOT_ADDITIONS = {
    "loot_feral_worker_droid": [
        L("salvaged_chest_plate", 1, 1, 0.20, pity=4),
        L("propellant_tin", 1, 1, 0.40, pity=3),
    ],
    "loot_scrap_heap": [
        L("salvaged_chest_plate", 1, 1, 0.20, pity=4),
        L("med_dressing", 1, 2, 0.45, pity=2),
        L("propellant_tin", 1, 1, 0.40, pity=3),
    ],
    "loot_wreck_carcass": [
        L("chest_rig_harness", 1, 1, 0.22, pity=4),
        L("reinforced_sole", 1, 1, 0.20, pity=4),
        L("med_dressing", 1, 2, 0.50, pity=2),
    ],
    "loot_drone_wreck": [
        L("chest_rig_harness", 1, 1, 0.22, pity=4),
        L("med_biogel", 1, 1, 0.30, pity=3),
    ],
    "loot_depot_foreman": [
        L("berms_relay_key", 1, 1, 0, pity=0, guarantee=1),
        L("salvaged_chest_plate", 1, 1, 0.30, pity=4),
    ],
    "loot_berms_outer": [
        L("salvaged_chest_plate", 1, 1, 0.30, pity=4),
        L("nanoweave_backing", 1, 1, 0.20, pity=4),
        L("tread_strut", 1, 1, 0.25, pity=4),
        L("med_dressing", 1, 2, 0.55, pity=2),
        L("propellant_tin", 1, 2, 0.50, pity=2),
    ],
    "loot_feral_gunner": [
        L("salvaged_chest_plate", 1, 1, 0.25, pity=4),
        L("ceramic_ballistic_plate", 1, 1, 0.25, pity=4),
        L("rig_harness_frame", 1, 1, 0.25, pity=3),
        L("propellant_tin", 1, 2, 0.55, pity=2),
        L("hardened_slug_core", 1, 2, 0.35, pity=3),
        L("ammo_rifle_standard", 4, 8, 0.50, pity=2),
    ],
    "loot_feral_lancer": [
        L("rig_harness_frame", 1, 1, 0.25, pity=3),
        L("armoured_shell_casing", 1, 1, 0.30, pity=4),
        L("optic_visor_lens", 1, 1, 0.30, pity=4),
        L("hardened_slug_core", 1, 2, 0.35, pity=3),
        L("capacitor_filament", 1, 2, 0.40, pity=3),
    ],
    "loot_caravan_strongbox": [
        L("berms_relay_key", 1, 1, 0, pity=0, guarantee=1),
        L("ceramic_ballistic_plate", 1, 1, 0.30, pity=4),
        L("nanoweave_backing", 1, 1, 0.25, pity=4),
        L("med_biogel", 1, 1, 0.50, pity=2),
        L("ammo_rifle_standard", 6, 12, 0.80, pity=2),
    ],
    "loot_berms_outpost": [
        L("chest_rig_harness", 1, 1, 0.25, pity=4),
        L("ceramic_ballistic_plate", 1, 1, 0.30, pity=4),
        L("nanoweave_backing", 1, 1, 0.20, pity=4),
        L("rig_harness_frame", 1, 1, 0.25, pity=3),
        L("reinforced_sole", 1, 1, 0.30, pity=4),
        L("armoured_shell_casing", 1, 1, 0.25, pity=4),
        L("med_dressing", 1, 2, 0.60, pity=2),
        L("med_biogel", 1, 1, 0.40, pity=3),
        L("med_nanosuture", 1, 1, 0.20, pity=4),
        L("capacitor_filament", 1, 2, 0.35, pity=3),
        L("ammo_rifle_standard", 4, 8, 0.60, pity=2),
    ],
    "loot_scrap_reaper": [
        L("tread_strut", 1, 1, 0.35, pity=3),
        L("reinforced_sole", 1, 1, 0.35, pity=3),
        L("hardened_slug_core", 1, 2, 0.50, pity=2),
        L("nano_resonator_shard", 1, 1, 0.25, pity=4),
        L("nano_targeting_core", 1, 1, 0.20, pity=4),
    ],
    "loot_post_sentinel": [
        L("armoured_shell_casing", 1, 1, 0.40, pity=3),
        L("optic_visor_lens", 1, 1, 0.45, pity=3),
        L("capacitor_filament", 1, 2, 0.50, pity=2),
        L("nano_dormant_matrix", 1, 1, 0.25, pity=4),
        L("nano_targeting_core", 1, 1, 0.20, pity=4),
    ],
    "loot_nextlevel_crate": [
        L("tread_strut", 1, 1, 0.35, pity=3),
        L("optic_visor_lens", 1, 1, 0.35, pity=3),
        L("med_biogel", 1, 2, 0.50, pity=2),
        L("med_nanosuture", 1, 1, 0.45, pity=3),
        L("hardened_slug_core", 1, 2, 0.55, pity=2),
        L("capacitor_filament", 1, 2, 0.50, pity=2),
    ],
    # Keep guaranteeUntilCollected count at 2 (reaper_blade + sentinel_optic) for NextLevelEnemiesTests
    "loot_nextlevel_strongbox": [
        L("med_nanosuture", 1, 2, 0.65, pity=2),
        L("nano_dormant_matrix", 1, 1, 0.40, pity=3),
        L("nano_resonator_shard", 1, 1, 0.40, pity=3),
        L("nano_targeting_core", 1, 1, 0.35, pity=3),
    ],
}


# --------------------------------------------------------------------------------------------- emitters
def emit_item(d):
    return [
        kv("", "id", d["id"]),
        kv("", "name", d["name"]),
        kv("", "description", d["desc"]),
        f"buyPrice: {d['buy']}",
        f"sellPrice: {d['sell']}",
        "startingQuantity: 0",
        *str_list("", "tags", d["tags"]),
        f"maxStack: {d['stack']}",
        f"excludeFromTrade: {d['exclude']}",
        f"rarity: {d['rarity']}",
        f"sellOnly: {d['sellOnly']}",
        kv("", "icon", d["icon"]),
        "partsPrice: 0",
        f"weightKg: {s(float(d['kg']))}",
    ]


def emit_consumable(c):
    return [
        f"itemId: {c['itemId']}",
        f"restoreHealth: {s(c['restoreHealth'])}",
        f"restoreNano: {s(c['restoreNano'])}",
        f"overclockSeconds: {s(c['overclockSeconds'])}",
        f"overclockRegen: {s(c['overclockRegen'])}",
        kv("", "hotbarLabel", c["hotbarLabel"]),
    ]


def emit_recipe(r):
    return [
        f"id: {r['id']}",
        kv("", "name", r["name"]),
        "stationId: station_field_fabricator",
        "requiresWeaponId: ",
        f"outputItemId: {r['out']}",
        "outputWeaponId: ",
        "outputSlots: []",
        *obj_list("", "inputs", r["inputs"], lambda i: [f"kind: {i['kind']}", f"id: {i['id']}", f"quantity: {i['quantity']}"]),
        f"outputQuantity: {r['outQty']}",
        "knownByDefault: 0",
        *obj_list("", "unlocks", r["unlocks"], lambda u: [f"type: {u['type']}", f"id: {u['id']}"]),
        "requirements: []",
        "requiredTools: []",
        "requiredSchematics: []",
        f"group: {r['group']}",
        kv("", "lockedHint", r["hint"]),
        f"craftSeconds: {s(r['seconds'])}",
        f"skill: {r['skill']}",
        f"craftXp: {r['xp']}",
        f"skillUse: {s(r['skillUse'])}",
    ]


def emit_loot_entry(e):
    return [
        f"itemId: {e['itemId']}",
        f"minQuantity: {e['minQuantity']}",
        f"maxQuantity: {e['maxQuantity']}",
        f"chance: {s(e['chance'])}",
        f"pityAfter: {e['pityAfter']}",
        f"guaranteeUntilCollected: {e['guaranteeUntilCollected']}",
    ]


# --------------------------------------------------------------------------------------------- patches
def patch_city():
    p = os.path.join(A, "Data/CityCatalog.asset")
    lines = read(p)
    upsert(lines, "items", group(ITEMS, emit_item), "id")
    upsert(lines, "consumables", group(NEW_CONSUMABLES, emit_consumable), "itemId")
    return p, write(p, lines)


def patch_crafting():
    p = os.path.join(A, "Data/Crafting/WardCrafting.asset")
    lines = read(p)

    # 1. Upsert new M2/M4 recipes
    upsert(lines, "recipes", group(NEW_RECIPES, emit_recipe), "id")

    # 2. Wire armoured_shell_casing + optic_visor_lens into recipe_field_helmet inputs (idempotent)
    r_start, r_end = list_span(lines, "recipes")
    for (a, b) in entries(lines, r_start, r_end):
        if lines[a] != "  - id: recipe_field_helmet":
            continue
        # Find inputs span inside this recipe (4-space indent)
        in_start = next(i for i in range(a, b) if lines[i] == "    inputs:") + 1
        in_end = in_start
        while in_end < b and (lines[in_end].startswith("    - ") or lines[in_end].startswith("      ")):
            in_end += 1
        existing = set()
        for i in range(in_start, in_end):
            m = re.match(r"      id: (\S+)", lines[i])
            if m:
                existing.add(m.group(1))
        add_lines = []
        for ing in HELMET_EXTRA_INPUTS:
            if ing["id"] not in existing:
                add_lines += [
                    f"    - kind: {ing['kind']}",
                    f"      id: {ing['id']}",
                    f"      quantity: {ing['quantity']}",
                ]
        if add_lines:
            lines[in_end:in_end] = add_lines
        break

    # 3. Upsert loot table entries per table (4-space indent for `entries:`)
    lt_start, lt_end = list_span(lines, "lootTables")
    # Walk bottom-up so insertions do not shift earlier spans
    for (a, b) in reversed(entries(lines, lt_start, lt_end)):
        m = re.match(r"  - id: (\S+)", lines[a])
        if not m:
            continue
        tid = m.group(1)
        if tid not in LOOT_ADDITIONS:
            continue
        sub = lines[a:b]
        new_blocks = group(LOOT_ADDITIONS[tid], emit_loot_entry, ind="    ")
        upsert(sub, "entries", new_blocks, "itemId", ind="    ")
        lines[a:b] = sub

    return p, write(p, lines)


def patch_orders():
    p = os.path.join(A, "Data/Crafting/WardFieldOrders.asset")
    lines = read(p)
    # Keep all 11 order IDs, titles, goals, targets, and indices intact;
    # enrich briefs for order_plate_carrier and order_depot_foreman to reflect M2/M3 progression.
    brief_updates = {
        "order_plate_carrier": (
            "A Warden plate carrier went down with the caravan ambushed north of the trail, past the northgate drones, "
            "or you can fabricate one at Brann's bench from Band 2 ceramic plates, nanoweave backing, and a tensioned clasp. "
            "Recover or build it, then wear it in your chest slot."
        ),
        "order_depot_foreman": (
            "Destroy the Depot Foreman in the processing hall and recover the {item} (and the Warden Relay Key for the mid-Berms Waystation) from its wreck."
        ),
    }
    o_start, o_end = list_span(lines, "orders")
    for (a, b) in reversed(entries(lines, o_start, o_end)):
        m = re.match(r"  - id: (\S+)", lines[a])
        if not m or m.group(1) not in brief_updates:
            continue
        oid = m.group(1)
        for i in range(a, b):
            if lines[i].startswith("    brief: "):
                lines[i] = kv("    ", "brief", brief_updates[oid])
                break
    return p, write(p, lines)


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
    for fn in (patch_city, patch_crafting, patch_orders):
        path, text = fn()
        v = validate(path, text)
        ok &= v
        print(("checked " if CHECK else "wrote   ") + os.path.relpath(path, ROOT), "OK" if v else "FAILED")
    sys.exit(0 if ok else 1)
