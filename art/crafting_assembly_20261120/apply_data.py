#!/usr/bin/env python3
"""Crafting rework data patch (20 Nov 2026). Phase 1: Ossa identifies the Damaged Servo. Phase 2: skills, tools and Brann's toolkit. Phase 3: weapon condition, field repair, bench overhaul. Idempotent, exact-match: each edit
is skipped when already applied and fails loudly when its anchor text is missing (then the asset changed under us).

  python3 art/crafting_assembly_20261120/apply_data.py          # apply
  python3 art/crafting_assembly_20261120/apply_data.py --check  # report only, exit 1 if anything is unapplied

Run generate_voices.py first so the voice clips' .meta GUIDs exist (a missing clip leaves the node captioned only).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
A = ROOT / "unity/AthenHill/Assets/AthenHill"
CHECK = "--check" in sys.argv
pending = []


def voice(npc, node):
    meta = A / f"Audio/ElevenLabs/NpcVoices/{npc}-{node}.wav.meta"
    if not meta.exists():
        print(f"  (no voice clip for {npc}-{node}: captioned only)")
        return "{fileID: 0}"
    guid = [l.split(":")[1].strip() for l in meta.read_text().splitlines() if l.startswith("guid:")][0]
    return "{fileID: 8300000, guid: %s, type: 3}" % guid


def patch(path, old, new, label, applied=None):
    """applied: optional marker text; when the file already holds it the edit counts as done (for anchors a later phase touched)."""
    text = path.read_text()
    if new in text or (applied and applied in text):
        print(f"ok      {label}")
        return
    if text.count(old) != 1:
        raise SystemExit(f"anchor for '{label}' found {text.count(old)}x in {path.name}; not patching")
    pending.append(label)
    print(f"{'WOULD  ' if CHECK else 'applied'} {label}")
    if not CHECK:
        path.write_text(text.replace(old, new, 1))


# ---- recipe: taught by identification, not by picking the servo up ------------------------------------------------------
patch(A / "Data/Crafting/WardCrafting.asset",
      """    - kind: tag
      id: nanite:tier1
      quantity: 5
    outputQuantity: 1
    knownByDefault: 0
    unlocks:
    - type: acquireItem
      id: droid_servo_damaged
    requirements: []
    requiredTools: []
    requiredSchematics: []
    group: 1
    lockedHint: Salvage a worker-droid servo at the machine depot to learn this.
    craftSeconds: 8""",
      """    - kind: tag
      id: nanite:tier1
      quantity: 5
    outputQuantity: 1
    knownByDefault: 0
    unlocks:
    - type: identify
      id: npc_ossa:servo_look
    requirements: []
    requiredTools: []
    requiredSchematics: []
    group: 1
    lockedHint: Show a salvaged worker-droid servo to Warden Ossa to learn this.
    craftSeconds: 8""", "recipe_grip_stabilised_pistol: identify unlock", applied="      id: npc_ossa:servo_look\n")

# ---- item: who identifies it ---------------------------------------------------------------------------------------------
patch(A / "Data/CityCatalog.asset",
      "    description: A salvaged worker-droid servo, still fit for a field repair.\n",
      "    description: A salvaged worker-droid servo, still fit for a field repair. Show it to Ossa at the West Gate post; she can tell you what it could become.\n",
      "droid_servo_damaged: description")
patch(A / "Data/CityCatalog.asset",
      """    icon: servo-icon
    partsPrice: 10
    weightKg: 1.4
""",
      """    icon: servo-icon
    partsPrice: 10
    weightKg: 1.4
    identifyBy: npc_ossa
""", "droid_servo_damaged: identifyBy")

# ---- field order: Identify stage between Gather and Report ----------------------------------------------------------------
orders = A / "Data/Crafting/WardFieldOrders.asset"
patch(orders,
      "    brief: Salvage a worker-droid servo at the machine depot, then take it to Brann at Salvage for a steadier pistol grip.\n",
      "    brief: Salvage a worker-droid servo at the machine depot, show it to Warden Ossa, then take it to Brann at Salvage for a steadier pistol grip.\n",
      "order_steady_hands: brief")
patch(orders,
      "    reportBrief: Take the servo to Brann at Salvage, on the north avenue inside the walls. His workbench can make the {item}.\n    reportGuidance: dealer\n    brief: Salvage a worker-droid servo",
      "    identifyBrief: Show the servo to Warden Ossa at the West Gate post. She knows what salvage can become.\n    identifyGuidance: \n    reportBrief: Take the servo to Brann at Salvage, on the north avenue inside the walls. His workbench can make the {item}.\n    reportGuidance: dealer\n    brief: Salvage a worker-droid servo",
      "order_steady_hands: identifyBrief")


def scalar(t):
    """Plain YAML scalar unless it holds ': ' or ' #' (then single-quoted, as Unity writes it)."""
    return "'" + t.replace("'", "''") + "'" if ": " in t or " #" in t else t


def node(npc, nid, title, text, choices):
    out = [f"  - id: {nid}", f"    title: {title}", f"    text: {scalar(text)}", f"    voice: {voice(npc, nid)}", "    choices:"]
    for cid, label, nxt, action in choices:
        out += [f"    - id: {cid}", f"      label: {label}", f"      next: {nxt}", f"      action: {action}", "      requires: ", "      setFlag: "]
    return "\n".join(out) + "\n"


# ---- Ossa: the servo conversation (the second node teaches the schematic: recipe unlock npc_ossa:servo_look) ----------------
ossa = A / "Data/npc_ossa.asset"
patch(ossa, "  entries:\n  - node: warden_kit\n    requires: order:order_kit_helmet\n",
      "  entries:\n  - node: servo\n    requires: carry:droid_servo_damaged, !recipe:recipe_grip_stabilised_pistol\n  - node: warden_kit\n    requires: order:order_kit_helmet\n",
      "npc_ossa: servo entry")
ossa_nodes = (
    node("npc_ossa", "servo", "Salvage",
         "Hold it up. Worker servo. Anything you pull off the machines, you can sell, or you can build it into guns and armour. That's how it works around here: we salvage what we can. Let me look closer.",
         [("look", "Go on.", "servo_look", ""), ("later", "Another time.", "", "close")])
    + node("npc_ossa", "servo_look", "Salvage",
           "Hm. The gimbal is still true. Wired into a pistol grip, that should take the kick out of your scrap pistol. Brann at Salvage has the bench, on the north avenue. Take him alloy and nanites too.",
           [("brann", "I'll find Brann.", "", "close"), ("else", "Anything else, Ossa?", "greeting", "")]))
patch(ossa, "  nodes:\n  - id: warden_kit\n", "  nodes:\n" + ossa_nodes + "  - id: warden_kit\n", "npc_ossa: servo nodes")

# ---- Brann: while the servo is carried but unidentified ------------------------------------------------------------------------
brann = A / "Data/npc_brann.asset"
patch(brann, "  - node: report_early\n    requires: order:order_steady_hands, !reported\n",
      "  - node: steady_identify\n    requires: order:order_steady_hands, stage:Identify\n  - node: report_early\n    requires: order:order_steady_hands, !reported\n",
      "npc_brann: steady_identify entry")
brann_node = node("npc_brann", "steady_identify", "Steady Hands",
                  "That's a worker servo. Good. Before I touch it, show it to Ossa. She reads salvage better than I do, and she'll tell you what it's good for. Then come back with alloy and nanites.",
                  [("shop", "Show me what you trade.", "", "shop"), ("close", "I'll go and see her.", "", "close")])
patch(brann, "  - id: steady_gather\n", brann_node + "  - id: steady_gather\n", "npc_brann: steady_identify node")

# ---- voice audit roster -------------------------------------------------------------------------------------------------------
audit = A / "Editor/NpcVoiceAudit.cs"
patch(audit, '{"npc_brann", 19}, {"npc_ossa", 7}, {"npc_rell", 2},',
      '{"npc_brann", 20}, {"npc_ossa", 9}, {"npc_rell", 2},   // 20 Nov 2026: Ossa identifies the servo (art/crafting_assembly_20261120)', "NpcVoiceAudit counts", applied='{"npc_brann", 21}')


# =====================================================================================================================
# Phase 2 (20 Nov 2026): skills, tools and Brann's Field Toolkit
# =====================================================================================================================
import re

CRAFT = A / "Data/Crafting/WardCrafting.asset"

# ---- carried tool: the Field Toolkit is a screwdriver (tag), still matched by its item id by the rifle recipes -----------
patch(A / "Data/CityCatalog.asset",
      """    tags:
    - tool
    - fabrication
    maxStack: 1
    excludeFromTrade: 1""",
      """    tags:
    - tool
    - fabrication
    - tool:screwdriver
    maxStack: 1
    excludeFromTrade: 1""", "field_toolkit: tag tool:screwdriver")

# ---- per-recipe skill, XP and use gain (exercised skill, character XP on completion, first-craft skill use) ---------------
# id: (skill, craftXp, skillUse). XP: 100 a level. Use gain halves with every repeat of the same schematic and is capped per
# craft by the catalog (useGainCap); spent skill points (+5 a point, 10 a level) stay the main route.
SKILLS = {
    "recipe_field_rifle": ("engineering", 25, 1.5),
    "recipe_rifle_precision_barrel": ("engineering", 15, 1),
    "recipe_wound_coil": ("electronics", 3, 0.5),
    "recipe_charge_cell_core": ("electronics", 4, 0.5),
    "recipe_alloy_plate": ("engineering", 3, 0.5),
    "recipe_grip_stabilised_pistol": ("engineering", 12, 1),
    "recipe_cell_salvaged_capacitor": ("electronics", 10, 1),
    "recipe_barrel_bored_alloy": ("engineering", 10, 1),
    "recipe_grip_gyro_braced": ("robotics", 14, 1),
    "recipe_barrel_lattice_focused": ("nanotechnology", 14, 1),
    "recipe_cell_overclocked": ("electronics", 14, 1),
    "recipe_field_helmet": ("engineering", 10, 0.75),
    "recipe_field_armguards": ("engineering", 12, 0.75),
    "recipe_field_gloves": ("engineering", 10, 0.75),
    "recipe_field_leggings": ("engineering", 14, 0.75),
    "recipe_canvas_rucksack": ("engineering", 6, 0.5),
    "recipe_pack_side_pouches": ("engineering", 3, 0.5),
    "recipe_pack_hip_belt": ("engineering", 3, 0.5),
    "recipe_frame_pack": ("engineering", 8, 0.5),
    "recipe_porter_carrier": ("engineering", 10, 0.5),
    "recipe_pack_nanoweave_pouch": ("nanotechnology", 7, 0.5),
    "recipe_pack_servo_lifter": ("robotics", 8, 0.5),
    "recipe_courier_cargo_rig": ("nanotechnology", 12, 0.75),
    "recipe_armour_impact_liner": ("engineering", 6, 0.5),
    "recipe_armour_thermal_liner": ("nanotechnology", 6, 0.5),
    "recipe_armour_extra_plate": ("engineering", 8, 0.5),
}


def recipe_block(text, rid):
    m = re.search(r"\n  - id: %s\n" % re.escape(rid), text)
    if not m:
        raise SystemExit(f"recipe {rid} not found")
    start = m.start() + 1
    n = re.search(r"\n  (?:- id: |[A-Za-z])", text[m.end():])
    end = m.end() + n.start() + 1 if n else len(text)
    return start, end


def patch_recipe(rid, edits, label):
    """edits: list of (old, new) exact replacements applied inside that recipe's block."""
    text = CRAFT.read_text()
    s, e = recipe_block(text, rid)
    block = new = text[s:e]
    for old, repl in edits:
        if repl in new:
            continue
        if new.count(old) != 1:
            raise SystemExit(f"anchor for '{label}' found {new.count(old)}x in {rid}; not patching")
        new = new.replace(old, repl, 1)
    if new == block:
        print(f"ok      {label}")
        return
    pending.append(label)
    print(f"{'WOULD  ' if CHECK else 'applied'} {label}")
    if not CHECK:
        CRAFT.write_text(text[:s] + new + text[e:])


def fmt(x):
    return ("%g" % x)


for rid, (skill, xp, use) in SKILLS.items():
    text = CRAFT.read_text()
    s, e = recipe_block(text, rid)
    secs = re.search(r"\n    craftSeconds: (\S+)\n", text[s:e])
    if not secs:
        raise SystemExit(f"{rid}: no craftSeconds line")
    old = f"\n    craftSeconds: {secs.group(1)}\n"
    patch_recipe(rid, [(old, old + f"    skill: {skill}\n    craftXp: {xp}\n    skillUse: {fmt(use)}\n")], f"{rid}: skill {skill}, {xp} XP, use {fmt(use)}")

# ---- the grip needs a screwdriver (carried, tag) ---------------------------------------------------------------------------
patch_recipe("recipe_grip_stabilised_pistol", [("    requiredTools: []\n", "    requiredTools:\n    - tool:screwdriver\n")],
             "recipe_grip_stabilised_pistol: requires tool:screwdriver")

# ---- the workbench's fixed tools (belong to the station; carried tools cannot do these jobs) -------------------------------
patch(CRAFT,
      "  stations:\n  - id: station_field_fabricator\n    name: Salvage workbench\n  recipes:\n",
      "  stations:\n  - id: station_field_fabricator\n    name: Salvage workbench\n    tools:\n    - tool:vise\n    - tool:grinder\n    - tool:solder\n    - tool:nanite_press\n    - tool:welder\n  recipes:\n",
      "station_field_fabricator: fixed tools")

# ---- Brann's Field Toolkit gift, skill use settings, tool labels ----------------------------------------------------------------
patch(CRAFT, "  slotLabels:\n  - id: grip\n",
      "  nodeGifts:\n  - topic: npc_brann:toolkit\n    itemId: field_toolkit\n    flag: brann_toolkit\n    quantity: 1\n  useGainCap: 1.5\n  useRepeatFactor: 0.5\n  slotLabels:\n  - id: grip\n",
      "catalog: nodeGifts and skill-use settings", applied="  nodeGifts:\n  - topic: npc_brann:toolkit\n")
patch(CRAFT, "  - id: component:optic\n    label: Any optic lens\n  groupLabels:\n",
      "  - id: component:optic\n    label: Any optic lens\n  - id: tool:screwdriver\n    label: Screwdriver\n  - id: tool:vise\n    label: Bench vise\n"
      "  - id: tool:grinder\n    label: Bench grinder\n  - id: tool:solder\n    label: Soldering station\n  - id: tool:nanite_press\n    label: Nanite press\n"
      "  - id: tool:welder\n    label: Bench welder\n  groupLabels:\n", "catalog: tool labels")

# ---- Brann hands over the toolkit (voiced, once) -----------------------------------------------------------------------------------
brann = A / "Data/npc_brann.asset"
patch(brann, "  - node: report_ready\n    requires: order:order_steady_hands, !reported, stage:Report\n",
      "  - node: toolkit\n    requires: '!flag:brann_toolkit, !carry:field_toolkit'\n  - node: report_ready\n    requires: order:order_steady_hands, !reported, stage:Report\n",
      "npc_brann: toolkit entry")
toolkit_node = (
    node("npc_brann", "toolkit", "Salvage",
         "No toolkit on you? Then you're not touching my bench. Here, take this one: a screwdriver, a few gauges, the basics. Every salvager starts with one. Don't leave it lying about.",
         [("report", "I've brought the servo.", "report_ready", ""), ("shop", "Show me what you trade.", "", "shop"),
          ("thanks", "Thanks, Brann.", "greeting", "")]))
# the first choice only shows while Steady Hands waits for the report, so it carries a condition
toolkit_node = toolkit_node.replace("      next: report_ready\n      action: \n      requires: \n", "      next: report_ready\n      action: \n      requires: order:order_steady_hands, !reported, stage:Report\n")
patch(brann, "  - id: steady_identify\n", toolkit_node + "  - id: steady_identify\n", "npc_brann: toolkit node")
patch(audit, '{"npc_brann", 20}, {"npc_ossa", 9}', '{"npc_brann", 21}, {"npc_ossa", 9}', "NpcVoiceAudit counts: Brann 21")

# ---- Phase 3: weapon condition, field repair and the placeholder bench overhaul ----------------------------------------------
# Durability stat = full condition. Pistol 100 (it was 0: no wear); the rifle already has 100. Wear per shot: pistol 0.15 (about 660
# shots to a jam, misfires from about 330 on), rifle 0.2 (its hold-to-fire bursts: about 500 shots to a jam).
patch(CRAFT, "      durability: 0\n      armourPenetration: 0\n    minStats:", "      durability: 100\n      armourPenetration: 0\n    minStats:",
      "weapon_scrap_pistol: base durability 100")
patch(CRAFT, "    - grip\n    - barrel\n    - cell\n  - id: weapon_field_rifle\n", "    - grip\n    - barrel\n    - cell\n    wearPerShot: 0.15\n  - id: weapon_field_rifle\n",
      "weapon_scrap_pistol: wearPerShot 0.15")
patch(CRAFT, "    - barrel\n    - cell\n  modifiers:\n", "    - barrel\n    - cell\n    wearPerShot: 0.2\n  modifiers:\n",
      "weapon_field_rifle: wearPerShot 0.2")
patch(CRAFT, "  useGainCap: 1.5\n  useRepeatFactor: 0.5\n",
      "  useGainCap: 1.5\n  useRepeatFactor: 0.5\n"
      "  condition:\n    spreadBelow: 50\n    spreadMaxScale: 2\n    misfireBelow: 30\n    misfireMaxChance: 0.35\n"
      "    repairAmounts:\n    - 30\n    - 20\n    - 12\n    - 6\n"
      "    capLossPerRepair: 8\n    brokenBelow: 70\n    repairSeconds: 4\n    repairTool: tool:screwdriver\n"
      "    overhaulStationId: station_field_fabricator\n    overhaulInputs:\n"
      "    - kind: item\n      id: scrap_alloy\n      quantity: 3\n"
      "    - kind: tag\n      id: nanite:tier1\n      quantity: 4\n",
      "catalog: weapon condition rules")
patch(A / "Data/CityCatalog.asset", "    description: Reusable gauges and hand tools for fitting and fabrication work.\n",
      "    description: Reusable gauges and hand tools for fitting, fabrication and field repairs. Open a weapon in your field pack to repair it.\n",
      "field_toolkit: description")


sys.exit(1 if CHECK and pending else 0)
