#!/usr/bin/env python3
"""Rifle and armour quest data (2 Oct 2026). Idempotent text patches on the serialized Unity data assets:
CityCatalog (items), Resources/CharacterCatalog (equipment), WardCrafting (recipe, loot), WardFieldOrders (orders),
npc_ossa and npc_brann (dialogue). Run from the repo root after Codex's inventory work has landed; safe to re-run."""
import re, sys
from pathlib import Path
A = Path('/home/teknetik/code/ao2/unity/AthenHill/Assets/AthenHill')
log = []
def patch(path, fn):
    p = A / path; s = p.read_text(); n = fn(s)
    if n != s: p.write_text(n); log.append(f'patched {path}')
    else: log.append(f'unchanged {path}')
def block(s, start_marker, end_regex=r'\n  - id: '):
    """The YAML list block starting at start_marker up to the next list item at the same indent."""
    i = s.index(start_marker); m = re.compile(end_regex).search(s, i + len(start_marker))
    j = m.start() + 1 if m else len(s)   # keep the trailing newline so appended blocks start on their own line
    return s[i:j]

# ---- CityCatalog: items -------------------------------------------------------------------------------------------
def city(s):
    if 'id: rifle_receiver' not in s:
        core = block(s, '  - id: foreman_control_core')
        rec = core.replace('foreman_control_core', 'rifle_receiver').replace('Foreman Control Core', 'Warden Rifle Receiver')
        rec = re.sub(r'description: .*', "description: The bolted receiver of a Warden-pattern field rifle, stripped from a feral gunner droid's rack. Brann's workbench can build a rifle around it.", rec, 1)
        rec = rec.replace('    - component:control\n', '    - component:receiver\n').replace('icon: control-core-icon', 'icon: receiver-icon').replace('weightKg: 0.75', 'weightKg: 1.6')
        s = s.replace(core, core + rec, 1)
    if 'id: warden_plate_carrier' not in s:
        vest = block(s, '  - id: field_vest')
        pc = vest.replace('field_vest', 'warden_plate_carrier').replace('Field Vest', 'Warden Plate Carrier')
        pc = re.sub(r'description: .*', 'description: A Warden-issue plate carrier recovered from the ambushed caravan, with hard plates front and back under sand-tan canvas, magazine pouches and a grab handle. Wear it in the chest slot.', pc, 1)
        pc = re.sub(r'rarity: \d', 'rarity: 1', pc, count=1).replace('weightKg: 3.2', 'weightKg: 5.5').replace('icon: pack-icon', 'icon: carrier-icon')
        s = s.replace(vest, vest + pc, 1)
    # the rifle is built in the Long Arm order, not issued at the start
    fr = block(s, '  - id: field_rifle')
    s = s.replace(fr, fr.replace('startingQuantity: 1', 'startingQuantity: 0'), 1)
    return s
patch('Data/CityCatalog.asset', city)

# ---- CharacterCatalog: equipment ----------------------------------------------------------------------------------
def character(s):
    if 'itemId: warden_plate_carrier' not in s:
        vest = block(s, '  - itemId: field_vest', r'\n  - itemId: ')
        pc = vest.replace('field_vest', 'warden_plate_carrier').replace('tier: 0', 'tier: 1', 1).replace('weight: 3.2', 'weight: 5.5')
        pc = pc.replace('      flat: 12\n', '      flat: 24\n', 1).replace('      flat: 0.08\n', '      flat: 0.12\n', 1)
        pc = pc.replace('comfortableStrength: 8', 'comfortableStrength: 10').replace('comfortableEndurance: 8', 'comfortableEndurance: 10')
        s = s.replace(vest, vest + pc, 1)
    return s
patch('Resources/CharacterCatalog.asset', character)

# ---- WardCrafting: recipe inputs, gunner loot, caravan strongbox table --------------------------------------------
def crafting(s):
    r = block(s, '  - id: recipe_field_rifle')
    if 'id: rifle_receiver' not in r:
        n = r.replace("""    inputs:
    - kind: item
      id: scrap_alloy
      quantity: 8
    - kind: item
      id: copper_filament
      quantity: 4
    - kind: tag
      id: nanite:tier1
      quantity: 6
""", """    inputs:
    - kind: item
      id: rifle_receiver
      quantity: 1
    - kind: item
      id: scrap_alloy
      quantity: 6
    - kind: item
      id: copper_filament
      quantity: 3
    - kind: tag
      id: nanite:tier1
      quantity: 4
""")
        n = n.replace("""    - stat: engineering
      minimum: 45
""", """    - stat: engineering
      minimum: 20
""", 1)
        n = re.sub(r'lockedHint: .*', "lockedHint: Ossa's Long Arm order. A Warden rifle receiver from the relay-knoll gunners, then Brann's bench.", n, 1)
        assert n != r, 'recipe inputs not found'
        s = s.replace(r, n, 1)
    g = block(s, '  - id: loot_feral_gunner')
    if 'rifle_receiver' not in g:
        n = g.replace('    entries:\n', """    entries:
    - itemId: rifle_receiver
      minQuantity: 1
      maxQuantity: 1
      chance: 0.35
      pityAfter: 2
      guaranteeUntilCollected: 1
""", 1)
        s = s.replace(g, n, 1)
    if 'id: loot_caravan_strongbox' not in s:
        outer = block(s, '  - id: loot_berms_outer')
        strong = """  - id: loot_caravan_strongbox
    entries:
    - itemId: warden_plate_carrier
      minQuantity: 1
      maxQuantity: 1
      chance: 1
      pityAfter: 0
      guaranteeUntilCollected: 1
    - itemId: scrap_alloy
      minQuantity: 2
      maxQuantity: 3
      chance: 1
      pityAfter: 0
      guaranteeUntilCollected: 0
    - itemId: copper_filament
      minQuantity: 1
      maxQuantity: 2
      chance: 1
      pityAfter: 0
      guaranteeUntilCollected: 0
    - itemId: micro_capacitor
      minQuantity: 1
      maxQuantity: 1
      chance: 0.6
      pityAfter: 2
      guaranteeUntilCollected: 0
"""
        s = s.replace(outer, outer + strong, 1)
    return s
patch('Data/Crafting/WardCrafting.asset', crafting)

# ---- WardFieldOrders: two orders after Steady Hands --------------------------------------------------------------
ORDERS = """  - id: order_long_arm
    title: Long Arm
    goal: 3
    targetItemId: field_rifle
    targetGroup: 0
    requireTestFire: 0
    activateEncounter: relay_knoll
    guidance: relay_knoll
    reportTo: npc_brann
    reportBrief: Take the receiver to Brann at Salvage, on the north avenue inside the walls. His workbench can build the {item} around it.
    reportGuidance: dealer
    brief: Feral gunner droids on the relay knoll, west along the Warden trail past the waystation, carry Warden-pattern rifle receivers on their racks. Put one down and bring the receiver, with alloy and filament, to Brann.
    startLine: Your pistol's steadier. Now a long arm. The gunner droids nesting on the relay knoll, west past the waystation, strip rifles off dead Wardens; the receivers are still on their racks. Put one down, take the receiver to Brann, and train your rifle hand in the pack before you carry it.
    completeLine: A Warden rifle, built in Ward. Train Rifle in your pack to carry it, equip it in your loadout, and press 8 out here to draw it. Hold fire; it runs bursts on the same charge.
    urgentStart: 0
    engageLine: Gunner has a line on you. Its laser walks before it fires. Move off the line, then put rounds in the optic.
    speaker: Warden Ossa
    rewardCredits: 20
    rewardItems: []
    rewardRecipes: []
  - id: order_plate_carrier
    title: Plate Carrier
    goal: 1
    targetItemId: warden_plate_carrier
    targetGroup: 0
    requireTestFire: 0
    activateEncounter: caravan
    guidance: caravan
    reportTo: 
    reportBrief: 
    reportGuidance: 
    brief: A Warden plate carrier went down with the caravan ambushed north of the trail, past the northgate drones. Clear the scavengers and take it from the caravan strongbox, then wear it in your chest slot.
    startLine: One more before the Foreman. A caravan went down north of the trail, past the northgate drones; scavenger droids are still picking it. A Warden plate carrier is in the strongbox. Bring it back and wear it. The Berms hit harder further out.
    completeLine: Plate carrier recovered. Put it on in your loadout, chest slot. It will take a gunner bolt that would have put you down.
    urgentStart: 0
    engageLine: 
    speaker: Warden Ossa
    rewardCredits: 20
    rewardItems: []
    rewardRecipes: []
"""
def orders(s):
    if 'id: order_long_arm' in s: return s
    first = block(s, '  - id: order_steady_hands')
    return s.replace(first, first + ORDERS, 1)
patch('Data/Crafting/WardFieldOrders.asset', orders)

# ---- Dialogue -----------------------------------------------------------------------------------------------------
def ossa(s):
    if 'id: long_arm' in s: return s
    entries = """  entries:
  - node: plate_carrier
    requires: order:order_plate_carrier
  - node: long_arm
    requires: order:order_long_arm
"""
    if '\n  entries:' in s:
        s = s.replace('\n  entries:\n', '\n' + entries, 1) if '\n  entries:\n' in s else s.replace('\n  entries: []\n', '\n' + entries, 1)
    else:
        s = s.replace('\n  nodes:\n', '\n' + entries + '  nodes:\n', 1)
    nodes = """  - id: long_arm
    title: Long arm
    text: The relay knoll is west along the trail, past the waystation; two gunner droids nest on it with a worker. Their lasers walk before they fire, so move off the line and shoot the optic. The receiver is on the gunner's rack. Brann builds the rest. Train Rifle in your pack, equip it in your loadout, and 8 draws it out here.
    choices:
    - id: range
      label: Remind me of the controls.
      next: range
      action: 
      requires: 
      setFlag: 
    - id: leave
      label: On my way.
      next: 
      action: close
      requires: 
      setFlag: 
  - id: plate_carrier
    title: Plate carrier
    text: The caravan is north of the trail, past the northgate drones; the scavengers picking it are workers with a drone. The strongbox is by the lead truck. Wear the carrier in your chest slot; it is heavier than your vest, so mind your carry weight.
    choices:
    - id: range
      label: Remind me of the controls.
      next: range
      action: 
      requires: 
      setFlag: 
    - id: leave
      label: Understood.
      next: 
      action: close
      requires: 
      setFlag: 
"""
    return s.replace('\n  nodes:\n', '\n  nodes:\n' + nodes, 1)
patch('Data/npc_ossa.asset', ossa)

def brann(s):
    if 'id: long_report' in s: return s
    entries = """  - node: long_report
    requires: order:order_long_arm, !reported, stage:Report
  - node: long_gather
    requires: order:order_long_arm, stage:Gather
  - node: long_bench
    requires: order:order_long_arm, stage:Fabricate
"""
    s = s.replace('  - node: orders\n', entries + '  - node: orders\n', 1)
    nodes = """  - id: long_report
    title: Rifle receiver
    text: A Warden receiver, off a gunner's rack. Bolt's still true. Give me alloy for the barrel and stock, filament for the charge path and nanite for the cell seat, and the bench will build the rest of it around this. Train your rifle hand before you carry it; it kicks harder than the pistol.
    choices:
    - id: bench
      label: Let's build it.
      next: 
      action: close
      requires: 
      setFlag: 
  - id: long_gather
    title: Long arm
    text: Ossa wants you on a long arm? Bring me a Warden receiver off the relay-knoll gunners, six alloy, three filament and four nanite grade. I can build a field rifle around it.
    choices:
    - id: leave
      label: I'll get them.
      next: 
      action: close
      requires: 
      setFlag: 
  - id: long_bench
    title: Long arm
    text: Receiver, alloy, filament, nanite. It's all here. Use the workbench behind me and fabricate the Field Rifle.
    choices:
    - id: leave
      label: Will do.
      next: 
      action: close
      requires: 
      setFlag: 
"""
    return s.replace('\n  nodes:\n', '\n  nodes:\n' + nodes, 1)
patch('Data/npc_brann.asset', brann)
print('\n'.join(log))
