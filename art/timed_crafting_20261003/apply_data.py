#!/usr/bin/env python3
"""Timed crafting at Brann's workbench (3 Oct 2026): bench seconds per schematic in WardCrafting.asset.

Carl, playtest 3 Oct: armour "should be a crafting mission ... collect, craft slowly, craft it to armour".
CraftRecipe.craftSeconds (0 = instant) is written after each recipe's lockedHint line; an existing value is replaced,
so the script is idempotent and re-runnable after other patches rewrite the asset.

Run order: after art/armour_mission_20261003/apply_data.py (and everything that runs before it). Afterwards in Unity:
AthenHill.Editor.CraftingDataExporter.Export (refreshes Data/Crafting/Export/ward-crafting.v1.json).
Usage: apply_data.py [--root ASSETS_ATHENHILL_DIR] [--check]
--check only reports what would change (exit 1 when something differs). The live asset is backed up once to backup/."""
import argparse, re, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVE = Path('/home/teknetik/code/ao2/unity/AthenHill/Assets/AthenHill')
REL = 'Data/Crafting/WardCrafting.asset'

# Seconds at the bench. Refined components 4-6 s, weapon mods 8-12 s, armour 15-25 s (helmet/gloves shortest,
# leggings longest), the field rifle 20 s.
SECONDS = {
    'recipe_wound_coil': 4,
    'recipe_charge_cell_core': 5,
    'recipe_alloy_plate': 6,
    'recipe_grip_stabilised_pistol': 8,
    'recipe_cell_salvaged_capacitor': 9,
    'recipe_barrel_bored_alloy': 10,
    'recipe_grip_gyro_braced': 11,
    'recipe_barrel_lattice_focused': 12,
    'recipe_cell_overclocked': 12,
    'recipe_rifle_precision_barrel': 12,
    'recipe_field_rifle': 20,
    'recipe_field_helmet': 15,
    'recipe_field_gloves': 16,
    'recipe_field_armguards': 20,
    'recipe_field_leggings': 25,
}

ap = argparse.ArgumentParser()
ap.add_argument('--root', type=Path, default=LIVE)
ap.add_argument('--check', action='store_true')
args = ap.parse_args()
path = args.root.resolve() / REL
text = path.read_text()

start = text.index('\n  recipes:\n')
m = re.compile(r'\n  [A-Za-z]').search(text, start + len('\n  recipes:\n'))
end = m.start() if m else len(text)
section = text[start:end]
items = re.split(r'(?=\n  - id: )', section)
seen, out, changes = set(), [], []
for item in items:
    mid = re.match(r'\n  - id: (\S+)', item)
    if not mid:
        out.append(item); continue
    rid = mid.group(1); seen.add(rid)
    want = SECONDS.get(rid, 0)
    line = f'\n    craftSeconds: {want}'
    if re.search(r'\n    craftSeconds: [^\n]*', item):
        new = re.sub(r'\n    craftSeconds: [^\n]*', line, item, count=1)
    else:
        hint = re.search(r'\n    lockedHint:[^\n]*', item)
        if not hint: sys.exit(f'{rid}: no lockedHint line to anchor craftSeconds')
        new = item[:hint.end()] + line + item[hint.end():]
    if new != item: changes.append(f'{rid} -> {want} s')
    out.append(new)
missing = sorted(set(SECONDS) - seen)
if missing: sys.exit('recipes not found in the asset: ' + ', '.join(missing))
result = text[:start] + ''.join(out) + text[end:]

try:
    import yaml
    body = result.split('\n', 3)[3] if result.startswith('%YAML') else result
    doc = yaml.safe_load(re.sub(r'^--- !u!\d+ &\d+.*$', '', body, flags=re.M))
    recs = doc['MonoBehaviour']['recipes']
    assert all(r['craftSeconds'] == SECONDS.get(r['id'], 0) for r in recs), 'craftSeconds mismatch after patch'
except ImportError:
    pass

for c in changes: print(c)
if args.check:
    print('up to date' if not changes else f'{len(changes)} change(s) pending'); sys.exit(1 if changes else 0)
if result != text:
    if args.root.resolve() == LIVE:
        dst = HERE / 'backup' / REL
        if not dst.exists(): dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(path, dst)
    path.write_text(result); print(f'patched {REL} ({len(changes)} recipes)')
else:
    print(f'unchanged {REL}')
