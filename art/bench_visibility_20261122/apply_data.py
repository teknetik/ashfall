#!/usr/bin/env python3
"""22 Nov 2026, second playtest round: the data half (idempotent; no Unity needed).

  * layout.json: sheet B lies on top of sheet A in the tray, staggered; the sheets and the vial start clear of the open
    roll (`at`, in the bench surface's frame); a close shot of the housing pin.
  * steps.json: the punch is set in that shot.
  * instructions: the punch line, and the new shot's name. The lines are edited in place: build_instructions.py is
    not re-run, because its output differs from the saved file for three s2.pry steps that carry their own `line`.

    python3 art/bench_visibility_20261122/apply_data.py [--check]

Then unity/install.sh takes them into the assets.
"""
import json
import re
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[2] / 'art/steady_hands_bench_20261120'
CHECK = '--check' in sys.argv
changed = []
PUNCH = 'Click the punch in the tool roll, then click the ringed pin at the back of the bare grip frame'
SHOT = 'the housing pin, close'
AT = {'sheet_a': [0.385, -0.0079, -0.055], 'sheet_b': [0.25, -0.0079, -0.058], 'vial': [0.33, 0.0057, -0.125]}


def write(path, old, new):
    if old != new:
        if path.suffix == '.json':
            json.loads(new)
        changed.append(path.name)
        if not CHECK:
            path.write_text(new, encoding='utf-8')


def sub(text, old, new, what):
    if new in text:
        return text
    if text.count(old) != 1:
        raise SystemExit(f'{what}: expected one {old[:70]!r}')
    return text.replace(old, new)


def block(text, ident):
    start = text.index(f'   "id": "{ident}",')
    return start, text.index('\n  }', start)


path = R / 'data/layout.json'
old = text = path.read_text()
a, b = block(text, 'fixtures.tray/seat_alloy#b')
body = re.sub(r'"pos": \[[^]]*\]', '"pos": [\n    -0.105,\n    0.0152,\n    -0.05\n   ]', text[a:b], count=1)
text = text[:a] + body + text[b:]
for name, at in AT.items():
    a, b = block(text, f'place.entry.{name}')
    body = text[a:b]
    if '"at":' not in body:
        body += ',\n   "at": [\n    ' + ',\n    '.join(map(str, at)) + '\n   ]'
    text = text[:a] + body + text[b:]
if not any(s['id'] == 'pin' for s in json.loads(text)['shots']):
    m = re.search(r'\n "shots": \[\n', text)
    shot = {'id': 'pin', 'fov': 40, 'pos': [0.25, 1.2317, 0.67], 'look': [0.36, 1.0497, 0.41]}
    # last in the list, so the shots keep their order
    end = text.index('\n ]', m.end())
    text = text[:end] + ',\n' + '\n'.join('  ' + line for line in json.dumps(shot, indent=1).split('\n')) + text[end:]
write(path, old, text)

path = R / 'data/steps.json'
old = text = path.read_text()
text = sub(text, '"target": "pistol.housing_pin/punch", "weight": 0.25', '"target": "pistol.housing_pin/punch", "shot": "pin", "weight": 0.25', 'steps')
write(path, old, text)

path = R / 'audio/tutor/instructions.json'
old = text = path.read_text()
text = sub(text, 'Drag the punch to the housing pin and let go (the wheel turns it to fit)', PUNCH, 'instructions')
text = sub(text, '"roll": "the tool roll"', f'"roll": "the tool roll",\n  "pin": "{SHOT}"', 'instructions') if f'"pin": "{SHOT}"' not in text else text
write(path, old, text)

path = R / 'audio/tutor/build_instructions.py'
old = text = path.read_text()
if PUNCH not in text:
    text = sub(text, "    's1.inspect:find':", f"    's1.pin:punch': '{PUNCH}',\n    's1.inspect:find':", 'generator')
if SHOT not in text:
    text = sub(text, "'roll': 'the tool roll',\n}", f"'roll': 'the tool roll',\n    'pin': '{SHOT}',\n}}", 'generator')
write(path, old, text)

print(('would change: ' if CHECK else 'changed: ') + (', '.join(changed) or 'nothing'))
raise SystemExit(1 if CHECK and changed else 0)
