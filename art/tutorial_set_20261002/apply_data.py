#!/usr/bin/env python3
"""Tutorial set data (2 Oct 2026), idempotent: re-run after other branches (Codex inventory work) touch the catalogs.
- CityCatalog: Field set descriptions match the salvaged scrap-metal models; field_boots no longer starts in the pack
  (it starts worn).
- CharacterCatalog: initialEquipment is no longer touched (22 Nov 2026: a new colonist starts with no armour).
The primer no longer grants the helmet, arm guards, gloves and leg armour (3 Oct 2026): they are built through the Warden
Kit orders, see art/armour_mission_20261003/apply_data.py (run after this script).
Plain scalars only, no ': ' inside values (Unity's YAML reader rejects them; see memory unity-editor-pitfalls)."""
import re, sys
from pathlib import Path
A = Path('/home/teknetik/code/ao2/unity/AthenHill/Assets/AthenHill')
CITY = A / 'Data/CityCatalog.asset'; CHAR = A / 'Resources/CharacterCatalog.asset'
DESC = {
    'field_vest': 'A canvas plate carrier with a riveted steel plate cut from a machine panel, front and back, and a scrap shoulder pad.',
    'field_boots': 'Worn work boots with welded steel toe caps and a riveted ankle plate strapped over the instep.',
    'field_helmet': 'An open-face cap beaten from a salvaged machine housing, with a riveted brow band, ear cups and a padded liner.',
    'field_armguards': 'Curved bracers cut from pipe and panel steel, buckled over the forearm and clear of the elbow for tool and weapon work.',
    'field_gloves': 'Fingerless leather work gloves with a wrist strap. Good grip on a weapon or a wrench.',
    'field_leggings': 'A riveted knee cap and a shin plate with a faded hazard stripe, strapped over the suit with buckled leather.',
}
def entry_span(text, item):
    m = re.search(r'^  - id: ' + re.escape(item) + r'\n', text, re.M)
    if not m: sys.exit(f'missing {item}')
    n = re.search(r'^  - id: ', text[m.end():], re.M)
    return m.start(), m.end() + (n.start() if n else len(text) - m.end())
t = CITY.read_text(); changes = []
for item, d in DESC.items():
    assert ': ' not in d and '#' not in d
    a, b = entry_span(t, item); block = t[a:b]
    nb = re.sub(r'^    description: .*$', '    description: ' + d, block, count=1, flags=re.M)
    if item == 'field_boots': nb = re.sub(r'^    startingQuantity: \d+$', '    startingQuantity: 0', nb, count=1, flags=re.M)
    if nb != block: t = t[:a] + nb + t[b:]; changes.append(item)
CITY.write_text(t)
c = CHAR.read_text()
# 22 Nov 2026: no starting armour (Carl), so this patch no longer equips field_boots on a new colonist
# (art/npc_rebuild_20261122/data/no_starting_armour.py).
try:
    import yaml  # sanity parse (Unity tags stripped)
    for f in (CITY, CHAR):
        yaml.safe_load(re.sub(r'^%TAG.*$|!u!\d+ &\d+', '', f.read_text(), flags=re.M).replace('--- ', '---\n'))
except ImportError: pass
print('changed:', changes or 'nothing (already applied)')
