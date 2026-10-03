#!/usr/bin/env python3
"""Next-level combat data (2 Oct 2026). Idempotent text patches on Data/Crafting/WardCrafting.asset: weapon ranges,
spreads and base accuracy, the pistol barrel mods' range/spread effects, and stat labels for Accuracy and Spread.
Run from anywhere; safe to re-run (also after Codex's inventory work lands)."""
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
def set_stat(blk, section, stat, value):
    """Set one stat inside the weapon's `stats:` (or minStats/maxStats) mapping."""
    i = blk.index(f'    {section}:\n'); j = blk.find('\n    ', i + len(section) + 6)
    # the mapping runs until the next 4-space key
    m = re.compile(r'\n    [a-zA-Z]').search(blk, i + len(section) + 6)
    j = m.start() if m else len(blk)
    sec = blk[i:j]
    new = re.sub(rf'(\n      {stat}: )[^\n]*', rf'\g<1>{value}', sec, count=1)
    assert new != sec or f'\n      {stat}: {value}\n' in sec + '\n', (section, stat)
    return blk[:i] + new + blk[j:]
def set_effect(blk, stat, op, value):
    """Set or add one effect on a modifier block."""
    pat = re.compile(rf'    - stat: {stat}\n      op: {op}\n      value: [^\n]*')
    if pat.search(blk): return pat.sub(f'    - stat: {stat}\n      op: {op}\n      value: {value}', blk, count=1)
    i = blk.index('    effects:\n') + len('    effects:\n')
    return blk[:i] + f'    - stat: {stat}\n      op: {op}\n      value: {value}\n' + blk[i:]

def crafting(s):
    # --- weapons: pistol 30 m / 4 deg / accuracy 0, rifle 95 m / 1.8 deg / accuracy 20 (WeaponBallistics falloff: full
    # damage to 60 % of the range, 35 % at the range). The character's accuracy stat and the weapon skill add to accuracy.
    w = block(s, '  - id: weapon_scrap_pistol')
    n = set_stat(w, 'stats', 'range', 30); n = set_stat(n, 'stats', 'spread', 4); n = set_stat(n, 'stats', 'accuracy', 0)
    s = s.replace(w, n, 1)
    w = block(s, '  - id: weapon_field_rifle')
    n = set_stat(w, 'stats', 'range', 95); n = set_stat(n, 'stats', 'spread', 1.8); n = set_stat(n, 'stats', 'accuracy', 20)
    s = s.replace(w, n, 1)
    # --- pistol barrels: range adds scaled to the 30 m pistol, and a spread tightening so the mod is still meaningful
    m = block(s, '  - id: mod_barrel_bored_alloy')
    n = set_effect(m, 'range', 'add', 6); n = set_effect(n, 'spread', 'percent', -10); s = s.replace(m, n, 1)
    m = block(s, '  - id: mod_barrel_lattice_focused')
    n = set_effect(m, 'range', 'add', 12); n = set_effect(n, 'spread', 'percent', -20); s = s.replace(m, n, 1)
    # --- stat labels: the Fabricator table and pack tooltips show every labelled WeaponStats field
    if '\n  - stat: accuracy\n' not in s:
        labels = block(s, '  statLabels:\n', r'\n  [a-zA-Z]')
        add = ('  - stat: accuracy\n    label: Accuracy\n    format: 0\n    unit: \n    lowerIsBetter: 0\n'
               '  - stat: spread\n    label: Spread\n    format: 0.0\n    unit: "\\xB0"\n    lowerIsBetter: 1\n')
        s = s.replace(labels, labels.rstrip('\n') + '\n' + add, 1)
    return s
patch('Data/Crafting/WardCrafting.asset', crafting)
print('\n'.join(log))
