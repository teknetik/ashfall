#!/usr/bin/env python3
"""Carl, 22 Nov 2026: "the main player should not start with any armour, it should be crafted or bought".

Idempotent. Drops every armour_* entry from CharacterCatalog.initialEquipment (the backpack is storage and stays) and
the "Issued to new arrivals" claim on the Field Vest. Saved games keep what they already own: only a new game changes.
"""
import re
from pathlib import Path

A = Path(__file__).resolve().parents[3] / 'unity/AthenHill/Assets/AthenHill'
c = A / 'Resources/CharacterCatalog.asset'
s = c.read_text()
m = re.search(r'(?m)^  initialEquipment:\n((?:  - slot: .*\n    itemId: .*\n)*)', s)
assert m, 'initialEquipment not found'
rows = re.findall(r'  - slot: .*\n    itemId: .*\n', m.group(1))
keep = [r for r in rows if not r.startswith('  - slot: armour_')]
t = s[:m.start(1)] + ''.join(keep) + s[m.end(1):]
if t != s:
    c.write_text(t)

i = A / 'Data/CityCatalog.asset'
s = i.read_text()
t = s.replace(' and a scrap shoulder pad. Issued to new arrivals.', ' and a scrap shoulder pad.')
if t != s:
    i.write_text(t)
print('initial equipment now:', [r.split('itemId: ')[1].strip() for r in keep])
