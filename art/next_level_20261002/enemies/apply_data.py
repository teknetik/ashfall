#!/usr/bin/env python3
"""Next-level enemies data (2 Oct 2026). Idempotent text patches on the serialized Unity assets that Codex's inventory
work overwrites (BRIEF): CityCatalog (three loot items), UI/CityHUD.uss (their icon rules), WardFieldOrders (Ossa's
free-play objective mentions the far caches). Loot tables and the droid prefabs are written by the Editor method
AthenHill.Editor.NextLevelEnemiesInstall (C#), which checks these items exist first.
Run from anywhere after Codex lands; safe to re-run: python3 apply_data.py"""
import re, sys
from pathlib import Path
A = Path('/home/teknetik/code/ao2/unity/AthenHill/Assets/AthenHill')
log = []


def patch(path, fn):
    p = A / path; s = p.read_text(); n = fn(s)
    if n != s: p.write_text(n); log.append(f'patched {path}')
    else: log.append(f'unchanged {path}')


def block(s, start_marker, end_regex=r'\n  - id: '):
    i = s.index(start_marker); m = re.compile(end_regex).search(s, i + len(start_marker))
    j = m.start() + 1 if m else len(s)
    return s[i:j]


RETIRED = ['ironclad_plate']   # the 'Ironclad Warden' model is Brann; nothing drops this plate any more
ITEMS = [
    # Rare parts are trade-excluded by the catalog rules (ShopSellTests: Rare => excludeFromTrade), so they are crafting
    # rewards rather than credits; the sell price is recorded for a future parts counter.
    ('reaper_blade', 'Reaper Blade', 'A serrated scrap-steel claw blade from a Scrap Reaper, hydraulic knuckle still attached. Weaponsmiths will want the edge.',
     18, ['component', 'component:blade', 'tier:3', 'nextlevel'], 'reaper-blade-icon', 1.8),
    ('sentinel_optic', 'Sentinel Optic', 'The brass-ringed targeting optic of a Post sentinel, amber lens intact. A rifle sight could be built around it.',
     20, ['component', 'component:optic_targeting', 'tier:3', 'nextlevel'], 'sentinel-optic-icon', 0.6),
]


def item_yaml(id_, name, desc, sell, tags, icon, kg):
    t = ''.join(f'    - {x}\n' for x in tags)
    return (f'  - id: {id_}\n    name: {name}\n    description: {desc}\n    buyPrice: 0\n    sellPrice: {sell}\n    startingQuantity: 0\n    tags:\n{t}'
            f'    maxStack: 5\n    excludeFromTrade: 1\n    rarity: 2\n    sellOnly: 1\n    icon: {icon}\n    partsPrice: 0\n    weightKg: {kg}\n')


# ---- CityCatalog: three rare parts dropped only by the next-level droids and crates ---------------------------------
def city(s):
    # replace our blocks if present (so a definition change re-applies), then append after lattice_shard
    for id_ in [it[0] for it in ITEMS] + RETIRED:
        if f'  - id: {id_}\n' in s: s = s.replace(block(s, f'  - id: {id_}\n'), '', 1)
    anchor = block(s, '  - id: lattice_shard')
    return s.replace(anchor, anchor + ''.join(item_yaml(*it) for it in ITEMS), 1)
patch('Data/CityCatalog.asset', city)


# ---- CityHUD.uss: icon rules (the PNGs live in UI/Art; 192 x 192 like the salvage icons) ----------------------------
def uss(s):
    for id_ in RETIRED: s = re.sub(r'^\.' + id_.replace('_', '-') + r'-icon \{[^\n]*\n', '', s, flags=re.M)
    rules = ''.join(f'.{it[5]} {{ background-image: url("Art/{it[5][:-5]}.png"); }}\n' for it in ITEMS if f'.{it[5]} ' not in s)
    if not rules: return s
    anchor = '.carrier-icon { background-image: url("Art/carrier.png"); }\n'
    return s.replace(anchor, anchor + rules, 1) if anchor in s else s + '\n' + rules
patch('UI/CityHUD.uss', uss)


# ---- WardFieldOrders: Ossa's free-play objective points at the far caches -------------------------------------------
NOTE = ' Past the fans and the washes, Post sentinels and Scrap Reapers hold the far caches: take the field rifle and a full set of plate, and when they fall easily you are ready for the next region.'
def orders(s):
    m = re.search(r"^  freePlayObjective: '(.*)'$", s, re.M)
    if not m: return s
    line = m.group(1)
    if 'Post sentinels' in line: line = re.sub(r' Past the fans and the washes.*?next region\.', '', line)
    return s[:m.start(1)] + line + NOTE + s[m.end(1):]
patch('Data/Crafting/WardFieldOrders.asset', orders)


# ---- WardCrafting: the precision barrel's armour penetration 4 -> 8 (shared edit, nl1 fix round: the outer droids' flat armour
# must be a rifle-with-mod problem, not a rifle problem; the starter pistol has no penetration at all) ----------------------
def crafting(s):
    b = block(s, '  - id: mod_rifle_precision_barrel')
    n = re.sub(r"(- stat: armourPenetration\n\s+op: add\n\s+value: )4\n", r"\g<1>8\n", b, count=1)
    return s.replace(b, n, 1) if n != b else s
patch('Data/Crafting/WardCrafting.asset', crafting)

# ---- validate the YAML the way the Editor would (pyyaml, plus Unity's stricter rules) --------------------------------
try:
    import yaml
    for path in ('Data/CityCatalog.asset', 'Data/Crafting/WardFieldOrders.asset'):
        t = (A / path).read_text()
        yaml.safe_load(t.replace('%TAG !u! tag:unity3d.com,2011:\n', '').replace('!u!114 &11400000', '').replace('--- \n', '--- \n'))
        assert '\n\n' not in t.split('MonoBehaviour:', 1)[1], path + ': blank line inside the asset body'
    log.append('yaml ok')
except ImportError: log.append('pyyaml not available: yaml not validated (run with: uv run --offline --with pyyaml python apply_data.py)')
print('\n'.join(log))
