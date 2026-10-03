#!/usr/bin/env python3
"""Warden kit crafting chain (3 Oct 2026). Idempotent text patches on the serialized Unity data:

Carl, playtest 3 Oct: "why after shooting the tutorial robots did I get a load of armour. that should be a crafting
mission and not so easy to get ... collect, craft slowly, craft it to armour. should take scavenging most of the outer
berms to get it."

- CityCatalog: three new salvage materials (strap_webbing, padded_liner, rivet_stock; sell-only, loot-only: no parts
  price); the four Field armour pieces (helmet, arm guards, gloves, leg armour) are no longer traded (Mira sold them).
- WardCrafting: the materials in Berms loot tables, four Armour schematics at Brann's bench (each revealed by its
  order), alloy plate also revealed by the first kit order, the Armour group label.
- WardFieldOrders: four Warden Kit orders straight after Steady Hands (the helm reports to Brann first).
- npc_ossa / npc_brann: kit dialogue.
- UI: icon rules in CityHUD.uss and 192 px icons in UI/Art (from icons/, made by icons/gen_icons.sh + fit_icons.sh).
- Scene: the Outer Berms BermsTutorial component's serialized kitItems/kitNotice emptied (the primer no longer grants
  the kit). Skip with --skip-scene while another job owns the scene.

Run order: after art/tutorial_set_20261002, art/rifle_armour_20261002 and art/next_level_20261002/*/apply_data.py.
Usage: apply_data.py [--root ASSETS_ATHENHILL_DIR] [--skip-scene]
The default root is the live project; files are backed up once to backup/ before the first live change.
Plain scalars carry no ': ' (Unity's YAML reader is stricter than pyyaml); q() quotes when needed."""
import argparse, hashlib, re, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVE = Path('/home/teknetik/code/ao2/unity/AthenHill/Assets/AthenHill')
ap = argparse.ArgumentParser()
ap.add_argument('--root', type=Path, default=LIVE)
ap.add_argument('--skip-scene', action='store_true')
args = ap.parse_args()
A = args.root.resolve()
live = A == LIVE
log = []


def backup(rel):
    if not live: return
    src, dst = A / rel, HERE / 'backup' / rel
    if src.exists() and not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src, dst)


def patch(rel, fn):
    p = A / rel; s = p.read_text(); n = fn(s)
    if n != s: backup(rel); p.write_text(n); log.append(f'patched {rel}')
    else: log.append(f'unchanged {rel}')


def block(s, start_marker, end_regex=r'\n  (?:- id: |[A-Za-z])'):
    """The YAML list item starting at start_marker up to the next item (or key) at the same indent."""
    i = s.index(start_marker); m = re.compile(end_regex).search(s, i + len(start_marker))
    j = m.start() + 1 if m else len(s)
    return s[i:j]


def q(v):
    """A YAML scalar Unity reads back: single-quoted when it holds ': ', ' #' or starts with an indicator."""
    if v == '': return ''
    if ': ' in v or ' #' in v or v[0] in '\'"!&*[]{}|>%@,?:-#`' or v.endswith(':'):
        return "'" + v.replace("'", "''") + "'"
    return v


KIT = ['field_helmet', 'field_armguards', 'field_gloves', 'field_leggings']

# ---- CityCatalog --------------------------------------------------------------------------------------------------
MATERIALS = [
    # id, name, description, sellPrice, maxStack, icon, weightKg
    ('strap_webbing', 'Strap Webbing', 'Worn canvas and nylon webbing cut from caravan loads, buckles still threaded. Wardens stitch armour straps from it.', 2, 30, 'webbing-icon', 0.15),
    ('padded_liner', 'Padded Liner', 'A quilted liner salvaged from wrecked truck and drone seats. Pads a helmet or a plate where it meets the body.', 3, 20, 'liner-icon', 0.3),
    ('rivet_stock', 'Rivet Stock', 'A tin of steel rivets and washers pried from droid frames. Every Warden plate is riveted to its straps.', 2, 30, 'rivets-icon', 0.2),
]


def material_yaml(id_, name, desc, sell, stack, icon, kg):
    return (f'  - id: {id_}\n    name: {name}\n    description: {q(desc)}\n    buyPrice: 0\n    sellPrice: {sell}\n'
            f'    startingQuantity: 0\n    tags:\n    - salvage\n    - material\n    - material:armour\n    - tier:1\n'
            f'    maxStack: {stack}\n    excludeFromTrade: 0\n    rarity: 0\n    sellOnly: 1\n    icon: {icon}\n    partsPrice: 0\n    weightKg: {kg}\n')


def city(s):
    add = ''.join(material_yaml(*m) for m in MATERIALS if f'  - id: {m[0]}\n' not in s)
    if add:
        anchor = block(s, '  - id: micro_capacitor\n')
        s = s.replace(anchor, anchor + add, 1)
    for id_ in KIT:   # built at Brann's bench through the Warden Kit orders, never bought (Mira stocked them)
        b = block(s, f'  - id: {id_}\n')
        n = re.sub(r'^    excludeFromTrade: \d$', '    excludeFromTrade: 1', b, count=1, flags=re.M)
        n = re.sub(r'^    buyPrice: \d+$', '    buyPrice: 0', n, count=1, flags=re.M)
        s = s.replace(b, n, 1)
    return s


# ---- WardCrafting -------------------------------------------------------------------------------------------------
# table: [(item, min, max, chance, pityAfter)]; appended at the end of each table
LOOT = {
    'loot_berms_outer':        [('strap_webbing', 1, 2, 0.5, 2)],    # the ten outer-site heaps
    'loot_caravan_strongbox':  [('strap_webbing', 1, 2, 1, 0)],      # the caravan's cargo straps
    'loot_wreck_carcass':      [('padded_liner', 1, 1, 0.45, 2)],    # four truck wrecks
    'loot_drone_wreck':        [('padded_liner', 1, 1, 0.35, 3)],    # five drone wrecks
    'loot_berms_outpost':      [('padded_liner', 1, 2, 0.5, 2)],     # two outpost lockers
    'loot_feral_worker_droid': [('rivet_stock', 1, 2, 0.35, 3)],
    'loot_feral_gunner':       [('rivet_stock', 1, 2, 0.5, 2)],
    'loot_feral_lancer':       [('rivet_stock', 1, 2, 0.45, 2)],
    'loot_scrap_heap':         [('rivet_stock', 1, 1, 0.35, 3)],
}


def entry_yaml(item, lo, hi, chance, pity):
    return (f'    - itemId: {item}\n      minQuantity: {lo}\n      maxQuantity: {hi}\n      chance: {chance}\n'
            f'      pityAfter: {pity}\n      guaranteeUntilCollected: 0\n')


# recipe id, name, output, order, inputs [(id, qty)], hint
RECIPES = [
    ('recipe_field_helmet', 'Field Helmet', 'field_helmet', 'order_kit_helmet',
     [('alloy_plate', 2), ('padded_liner', 1), ('strap_webbing', 2), ('rivet_stock', 2)],
     "Ossa's Warden Kit orders. Webbing from the Berms heaps, liner from the wrecks, rivets from the droids."),
    ('recipe_field_armguards', 'Field Arm Guards', 'field_armguards', 'order_kit_arms',
     [('alloy_plate', 2), ('strap_webbing', 2), ('rivet_stock', 2)],
     "Ossa's Warden Kit orders. Webbing from the Berms heaps, rivets from the droids."),
    ('recipe_field_gloves', 'Field Gloves', 'field_gloves', 'order_kit_hands',
     [('strap_webbing', 2), ('padded_liner', 1), ('rivet_stock', 1), ('copper_filament', 2)],
     "Ossa's Warden Kit orders. Webbing from the Berms heaps, liner from the wrecks, rivets from the droids."),
    ('recipe_field_leggings', 'Field Leg Armour', 'field_leggings', 'order_kit_legs',
     [('alloy_plate', 3), ('padded_liner', 2), ('strap_webbing', 3), ('rivet_stock', 3)],
     "Ossa's Warden Kit orders. The far wrecks and outpost lockers still hold liner."),
]
ARMOUR_GROUP = 5   # RecipeGroup.Armour, appended to the enum (3 Oct 2026)


def recipe_yaml(id_, name, out, order, inputs, hint):
    ins = ''.join(f'    - kind: item\n      id: {i}\n      quantity: {n}\n' for i, n in inputs)
    return (f'  - id: {id_}\n    name: {name}\n    stationId: station_field_fabricator\n    requiresWeaponId: \n'
            f'    outputItemId: {out}\n    outputWeaponId: \n    outputSlots: []\n    inputs:\n{ins}'
            f'    outputQuantity: 1\n    knownByDefault: 0\n    unlocks:\n    - type: orderStart\n      id: {order}\n'
            f'    requirements: []\n    requiredTools: []\n    requiredSchematics: []\n    group: {ARMOUR_GROUP}\n'
            f'    lockedHint: {q(hint)}\n')


def crafting(s):
    for table, rows in LOOT.items():
        t = block(s, f'  - id: {table}\n')
        add = ''.join(entry_yaml(*r) for r in rows if f'    - itemId: {r[0]}\n' not in t)
        if add: s = s.replace(t, t + add, 1)
    add = ''.join(recipe_yaml(*r) for r in RECIPES if f'  - id: {r[0]}\n' not in s)
    if add: s = s.replace('\n  lootTables:\n', '\n' + add.rstrip('\n') + '\n  lootTables:\n', 1)
    plate = block(s, '  - id: recipe_alloy_plate\n')
    n = plate
    if 'id: order_kit_helmet\n' not in n:
        n = n.replace('    unlocks:\n', '    unlocks:\n    - type: orderStart\n      id: order_kit_helmet\n', 1)
    n = n.replace('lockedHint: Ossa issues this schematic with her Bore It True order.',
                  'lockedHint: Ossa issues this schematic with her Warden Kit and Bore It True orders.')
    s = s.replace(plate, n, 1)
    if '  - id: Armour\n' not in s:
        s = s.replace('    label: Weapon mods\n  statLabels:\n', '    label: Weapon mods\n  - id: Armour\n    label: Armour\n  statLabels:\n', 1)
        assert '  - id: Armour\n' in s, 'groupLabels anchor not found'
    return s


# ---- WardFieldOrders ----------------------------------------------------------------------------------------------
ORDERS = [
    dict(id='order_kit_helmet', title='Warden Kit: Helm', target='field_helmet', credits=10,
         reportTo='npc_brann', reportGuidance='dealer',
         reportBrief="Take what you've scavenged to Brann at Salvage, on the north avenue inside the walls. His bench rolls the plate and rivets it into the {item}.",
         brief="Wardens build their own kit. Scavenge the Outer Berms for strap webbing (scrap heaps), padded liner (wrecks) and rivet stock (droids), roll alloy plate at Brann's bench from scrap alloy and nanites, then build the {item}.",
         start="That grip will do. Now cover yourself. Wardens don't hand out kit; we build it. Webbing turns up in the scrap heaps, liner in the wrecks, rivets on the droids. Brann's bench rolls alloy into plate. A helm first. Show Brann what you find.",
         complete="That's a Warden helm, built in Ward. Wear it in your loadout, head slot. Ugly, but it turns a drone's dart."),
    dict(id='order_kit_arms', title='Warden Kit: Bracers', target='field_armguards', credits=10,
         brief="More webbing and rivets from across the Berms, two alloy plates from Brann's bench, then build the {item}.",
         start="A helm won't stop a clamp to the forearm. Bracers next. More plate, webbing and rivets. The heaps further out haven't been picked over.",
         complete="Bracers built. Strap them on and keep your forearms up when a worker swings."),
    dict(id='order_kit_hands', title='Warden Kit: Gloves', target='field_gloves', credits=10,
         brief="Webbing, a padded liner, rivets and copper filament to wire-stitch the palms. Build the {item} at Brann's bench.",
         start="Gloves now. Webbing, a liner and rivets, and copper filament to stitch the palms. Your grip on that pistol will thank you.",
         complete="Gloves built. Wear them in your loadout; a sure grip is half a steady shot."),
    dict(id='order_kit_legs', title='Warden Kit: Leg Plates', target='field_leggings', credits=20,
         brief="The heaviest piece. Three alloy plates, two padded liners, webbing and rivets. Search the far wrecks, outpost lockers and heaps, then build the {item} at Brann's bench.",
         start="Last piece, and the heaviest. Leg plates. Three plates and two liners. The far wrecks and the outpost lockers still have liner in them. Finish the set and you'll walk the Berms like a Warden.",
         complete="A full Warden kit, built with your own hands. Wear it all. Now you look like you belong out here."),
]


def order_yaml(o):
    return (f"  - id: {o['id']}\n    title: {q(o['title'])}\n    goal: 3\n    targetItemId: {o['target']}\n    targetGroup: 0\n"
            f"    requireTestFire: 0\n    activateEncounter: \n    guidance: \n    reportTo: {o.get('reportTo', '')}\n"
            f"    reportBrief: {q(o.get('reportBrief', ''))}\n    reportGuidance: {o.get('reportGuidance', '')}\n"
            f"    brief: {q(o['brief'])}\n    startLine: {q(o['start'])}\n    completeLine: {q(o['complete'])}\n"
            f"    urgentStart: 0\n    engageLine: \n    speaker: Warden Ossa\n    rewardCredits: {o['credits']}\n"
            f"    rewardItems: []\n    rewardRecipes: []\n")


def orders(s):
    for o in ORDERS: assert 'fabricator' not in (o['brief'] + o['start'] + o['complete']).lower()
    add = ''.join(order_yaml(o) for o in ORDERS if f"  - id: {o['id']}\n" not in s)
    if add:
        first = block(s, '  - id: order_steady_hands\n')
        s = s.replace(first, first + add, 1)
    # the rifle now follows the kit, not the grip
    return s.replace("startLine: Your pistol's steadier. Now a long arm.", "startLine: You're kitted out and your pistol's steadier. Now a long arm.", 1)


# ---- Dialogue -----------------------------------------------------------------------------------------------------
def node_yaml(id_, title, text, choices):
    c = ''.join(f'    - id: {cid}\n      label: {q(label)}\n      next: {nxt}\n      action: {act}\n      requires: {req}\n      setFlag: \n'
                for cid, label, nxt, act, req in choices)
    return f'  - id: {id_}\n    title: {q(title)}\n    text: {q(text)}\n    voice: {{fileID: 0}}\n    choices:\n{c}'


def ossa(s):
    if '  - id: warden_kit\n' in s: return s
    entries = ''.join(f'  - node: warden_kit\n    requires: order:{o["id"]}\n' for o in ORDERS)
    s = s.replace('\n  entries:\n', '\n  entries:\n' + entries, 1)
    node = node_yaml('warden_kit', 'Warden kit',
                     "Nobody issues Warden kit; you build it. Webbing turns up in the scrap heaps all over the Berms, padded liner in the wrecked trucks and drones, rivets on the droids you put down. Brann's bench rolls scrap alloy and nanites into plate and rivets the rest together. Helm, bracers, gloves, then leg plates.",
                     [('range', 'Remind me of the controls.', 'range', '', ''), ('leave', 'On my way.', '', 'close', '')])
    return s.replace('\n  nodes:\n', '\n  nodes:\n' + node, 1)


KIT_ORDERS = [o['id'] for o in ORDERS]


def brann(s):
    if '  - id: kit_report\n' in s: return s
    entries = ('  - node: kit_report\n    requires: order:order_kit_helmet, !reported, stage:Report\n'
               '  - node: kit_brief\n    requires: order:order_kit_helmet, !reported\n'
               + ''.join(f'  - node: kit_gather\n    requires: order:{o}, stage:Gather\n' for o in KIT_ORDERS)
               + ''.join(f'  - node: kit_bench\n    requires: order:{o}, stage:Fabricate\n' for o in KIT_ORDERS))
    assert '  - node: orders\n' in s
    s = s.replace('  - node: orders\n', entries + '  - node: orders\n', 1)
    bench = ('bench', 'Use the bench.', '', 'fabricator', 'pistol')
    nodes = (node_yaml('kit_report', 'Warden kit',
                       "Ossa's got you building Warden kit? Good. Let's see the haul. Webbing, liner, rivets. The bench presses scrap alloy into plate, three measures and two of nanites a plate, and rivets the rest into a helm. Same again for bracers, gloves and leg plates. Nobody sells this; you earn every strap.",
                       [bench, ('shop', 'Trade first.', '', 'shop', ''), ('close', 'Later.', '', 'close', '')])
             + node_yaml('kit_brief', 'Warden kit',
                         "Ossa radioed. You're building Warden kit. I can't sell you that, but I can help you make it. Strap webbing from the scrap heaps, padded liner from the wrecks, rivet stock off the droids. The bench rolls plate from scrap alloy and nanites, three and two a plate. Helm first. Two plates, a liner, two webbing, two rivets.",
                         [bench, ('shop', 'Show me what you trade.', '', 'shop', ''), ('close', "I'll find them.", '', 'close', '')])
             + node_yaml('kit_gather', 'Warden kit',
                         "Still short? Webbing turns up in the scrap heaps all over the Berms, liner in the wrecked trucks and drones, rivets on the droids. Scrap alloy and nanites I can sell you for plate. The rest you scavenge.",
                         [('shop', 'Show me what you trade.', '', 'shop', ''), bench, ('close', 'Later, Brann.', '', 'close', '')])
             + node_yaml('kit_bench', 'Warden kit',
                         "That's enough for the next piece. Use the bench at the back. Roll any plate you need, then build it, and wear it in your loadout.",
                         [bench, ('shop', 'Show me what you trade.', '', 'shop', ''), ('close', 'Later, Brann.', '', 'close', '')]))
    return s.replace('\n  nodes:\n', '\n  nodes:\n' + nodes, 1)


# ---- UI icons -----------------------------------------------------------------------------------------------------
ICONS = {'webbing-icon': 'strap_webbing', 'liner-icon': 'padded_liner', 'rivets-icon': 'rivet_stock'}


def uss(s):
    rules = ''.join(f'.{cls} {{ background-image: url("Art/{cls[:-5]}.png"); }}\n' for cls in ICONS if f'.{cls} ' not in s)
    if not rules: return s
    anchor = '.carrier-icon { background-image: url("Art/carrier.png"); }\n'
    return s.replace(anchor, anchor + rules, 1) if anchor in s else s + '\n' + rules


def icons():
    meta_src = (A / 'UI/Art/receiver.png.meta').read_text()
    for cls, item in ICONS.items():
        src = HERE / 'icons' / f'{item}.192.png'; rel = f'UI/Art/{cls[:-5]}.png'; dst = A / rel
        if not src.exists(): log.append(f'MISSING icon {src.name} (run icons/gen_icons.sh and icons/fit_icons.sh)'); continue
        if not dst.exists() or dst.read_bytes() != src.read_bytes():
            backup(rel); shutil.copyfile(src, dst); log.append(f'installed {rel}')
        else: log.append(f'unchanged {rel}')
        meta = A / (rel + '.meta')
        if not meta.exists():   # same importer settings as the other 192 px item icons, stable GUID per file
            guid = hashlib.md5(('ashfall-armour-mission/' + rel).encode()).hexdigest()
            meta.write_text(re.sub(r'^guid: [0-9a-f]{32}$', f'guid: {guid}', meta_src, count=1, flags=re.M)); log.append(f'created {rel}.meta')


# ---- Scene: the primer no longer grants the kit -------------------------------------------------------------------
def scene(s):
    i = s.index('m_EditorClassIdentifier: AthenHill.Runtime::AthenHill.BermsTutorial\n')
    j = s.find('\n--- !u!', i); j = len(s) if j < 0 else j
    part = s[i:j]
    n = re.sub(r"  kitItems:(?: \[\])?\n(?:  - .*\n)*  kitNotice:.*\n", '  kitItems: []\n  kitNotice: \n', part, count=1)
    assert '  kitItems: []\n  kitNotice: \n' in n, 'BermsTutorial kitItems/kitNotice not found'
    return s[:i] + n + s[j:]


patch('Data/CityCatalog.asset', city)
patch('Data/Crafting/WardCrafting.asset', crafting)
patch('Data/Crafting/WardFieldOrders.asset', orders)
patch('Data/npc_ossa.asset', ossa)
patch('Data/npc_brann.asset', brann)
patch('UI/CityHUD.uss', uss)
icons()
if args.skip_scene: log.append('skipped Scenes/AthenHill.unity (--skip-scene)')
else:
    p = A / 'Scenes/AthenHill.unity'; b = p.read_bytes(); s = b.decode('utf-8')
    n = scene(s)
    if n != s: backup('Scenes/AthenHill.unity'); p.write_bytes(n.encode('utf-8')); log.append('patched Scenes/AthenHill.unity')
    else: log.append('unchanged Scenes/AthenHill.unity')

try:   # sanity parse (Unity tags stripped)
    import yaml
    for rel in ('Data/CityCatalog.asset', 'Data/Crafting/WardCrafting.asset', 'Data/Crafting/WardFieldOrders.asset', 'Data/npc_ossa.asset', 'Data/npc_brann.asset'):
        yaml.safe_load(re.sub(r'^%TAG.*$|!u!\d+ &\d+', '', (A / rel).read_text(), flags=re.M).replace('--- ', '---\n'))
    log.append('yaml ok')
except ImportError: log.append('pyyaml not installed; YAML not parsed')
print('\n'.join(log))
