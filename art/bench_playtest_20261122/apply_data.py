#!/usr/bin/env python3
"""22 Nov 2026 playtest fixes: the data half (idempotent; no Unity needed).

  * Bench input map: A / E (or D) step sideways, V turns the vise, G / Home resets the view, Q / Shift+Q rotate.
  * Primer: clearing the depot sends the player back to Ossa, who then sends them to Brann.
  * Field order "Steady Hands": a WARDEN OSSA marker while the salvage is waiting to be shown to her.
  * The crack step's instruction.
  * The punch is struck in the side-on shot, where the blow can be seen.
  * The drill's crank and the servo's rotor spin about their bones' +Y (they tumbled about +Z).

    python3 art/bench_playtest_20261122/apply_data.py [--check]
"""
import hashlib
import json
import re
import sys
import uuid
from pathlib import Path

R = Path(__file__).resolve().parents[2]
A = R / 'unity/AthenHill/Assets/AthenHill'
CHECK = '--check' in sys.argv
changed = []

RADIO_START = "Clean work. Bring that salvage back to me at the post and we''ll see what it''s good for. "
CRACK_LINE = 'Drag the vise round (or hold V and move the mouse) until the crack faces you, or click the crack'
CRACK_OLD = 'Hold left on the vise and circle the mouse to turn the frame round until you see the crack'


def write(path, old, new):
    if old != new:
        changed.append(str(path.relative_to(R)))
        if not CHECK:
            path.write_text(new, encoding='utf-8')


def replace(path, old, new, done=None):
    text = path.read_text(encoding='utf-8')
    if (done or new) in text:
        return
    if text.count(old) != 1:
        raise SystemExit(f'{path}: expected one {old[:70]!r}')
    write(path, text, text.replace(old, new))


def controls():
    path = A / 'Data/Controls.inputactions'
    text = path.read_text(encoding='utf-8')
    data = json.loads(text)
    before = json.dumps(data)
    bench = next(m for m in data['maps'] if m['name'] == 'Bench')
    actions, bindings = bench['actions'], bench['bindings']
    uid = lambda name: str(uuid.uuid5(uuid.NAMESPACE_URL, 'ward-bench-20261122/' + name))

    def action(name, kind, control):
        if any(a['name'] == name for a in actions):
            return False
        new = dict(actions[0], name=name, type=kind, id=uid(name), expectedControlType=control,
                   processors='', interactions='', initialStateCheck=kind == 'Value')
        actions.append(new)
        return True

    def bind(act, path_, name='', composite=False, part=False):
        bindings.append(dict(bindings[0], name=name, id=uid(f'{act}/{name}/{path_}'), path=path_, interactions='',
                             processors='', action=act, isComposite=composite, isPartOfComposite=part))

    if action('Shimmy', 'Value', 'Axis'):
        bind('Shimmy', '1DAxis', 'Sideways', composite=True)
        bind('Shimmy', '<Keyboard>/a', 'negative', part=True)
        bind('Shimmy', '<Keyboard>/e', 'positive', part=True)
        bind('Shimmy', '<Keyboard>/d', 'positive', part=True)
    if action('Swivel', 'Button', 'Button'):
        bind('Swivel', '<Keyboard>/v')
    if action('ResetView', 'Button', 'Button'):
        bind('ResetView', '<Keyboard>/g')
        bind('ResetView', '<Keyboard>/home')
    taken = {('Navigate', '<Keyboard>/a'), ('Navigate', '<Keyboard>/d'), ('Rotate', '<Keyboard>/e')}
    bench['bindings'] = [b for b in bindings if (b.get('action'), b.get('path')) not in taken]
    if json.dumps(data) != before:
        write(path, text, json.dumps(data, indent=4, ensure_ascii=False) + ('\n' if text.endswith('\n') else ''))


def primer():
    path = A / 'Scenes/AthenHill.unity'
    old = ("Clean work. Take that salvage to Brann at Salvage, on the north avenue inside the walls. "
           "His bench can turn a worker servo into a steadier grip for that pistol. ")
    replace(path, "  lineComplete: '" + old, "  lineComplete: '" + RADIO_START)

    text = path.read_text(encoding='utf-8')
    if not re.search(r'  - key: ossa\n    label: WARDEN OSSA\n', text):
        warden = re.search(r'\n  briefingWarden: \{fileID: (\d+)\}', text).group(1)
        anchor = re.search(r'\n  - key: caravan\n    label: CARAVAN STRONGBOX\n    point: \{fileID: \d+\}\n', text)
        target = f'  - key: ossa\n    label: WARDEN OSSA\n    point: {{fileID: {warden}}}\n'
        write(path, text, text[:anchor.end()] + target + text[anchor.end():])

    replace(A / 'Data/Crafting/WardFieldOrders.asset',
            'She knows what salvage can become.\n    identifyGuidance: \n',
            'She knows what salvage can become.\n    identifyGuidance: ossa\n')


def instruction():
    replace(R / 'art/steady_hands_bench_20261120/audio/tutor/instructions.json', CRACK_OLD, CRACK_LINE)
    replace(A / 'Audio/ElevenLabs/Bench/Tutor/BenchTutorLines.asset', CRACK_OLD, CRACK_LINE)
    replace(R / 'art/steady_hands_bench_20261120/audio/tutor/build_instructions.py', CRACK_OLD, CRACK_LINE)
    replace(R / 'art/steady_hands_bench_20261120/audio/tutor/README.md', CRACK_OLD, CRACK_LINE)


def strike_shots():
    src = R / 'art/steady_hands_bench_20261120/data/steps.json'
    lines = src.read_text(encoding='utf-8').split('\n')
    step = None
    for i, line in enumerate(lines):
        found = re.search(r'\{"id": "([^"]+)"', line)
        if found:
            step = found.group(1)
        key = re.search(r'\{"key": "([^"]+)"', line)
        if not key or (step, key.group(1)) not in (('s1.pin', 'taps'), ('s6.pin', 'taps'), ('s6.pin.r', 'flush')):
            continue
        if '"shot": "vise_l"' in line:
            continue
        if '"shot": "work"' in line:
            lines[i] = line.replace('"shot": "work"', '"shot": "vise_l"')
        else:
            lines[i] = line.replace('"audio": "asm.tap"', '"shot": "vise_l", "audio": "asm.tap"', 1)
    text = '\n'.join(lines)
    write(src, src.read_text(encoding='utf-8'), text)

    asset = A / 'Data/Assembly/assembly_grip_stabilised_pistol.asset'
    old = asset.read_text(encoding='utf-8')
    out, step, key = [], None, None
    for line in old.split('\n'):
        if found := re.match(r'      - id: (\S+)$', line):
            step = found.group(1)
        if found := re.match(r'        - key: (\S+)$', line):
            key = found.group(1)
        if line.startswith('          shot:') and (step, key) in (('s1.pin', 'taps'), ('s6.pin', 'taps'), ('s6.pin.r', 'flush')):
            line = '          shot: vise_l'
        if line.startswith('  sourceHash: '):
            line = '  sourceHash: ' + hashlib.sha1(text.encode('utf-8')).hexdigest()
        out.append(line)
    write(asset, old, '\n'.join(out))


def spin_axes():
    path = A / 'Data/Assembly/SteadyHandsBench.prefab'
    old = path.read_text(encoding='utf-8')
    docs = old.split('\n--- !u!')
    for i, doc in enumerate(docs):
        if re.search(r'\n  id: (tools\.drill_crank|servo\.rotor)\n', doc) and '\n  continuous: 1\n' in doc:
            docs[i] = doc.replace('spinAxis: {x: 0, y: 0, z: 1}', 'spinAxis: {x: 0, y: 1, z: 0}')
    write(path, old, '\n--- !u!'.join(docs))


controls()
strike_shots()
spin_axes()
primer()
instruction()
print(('would change ' if CHECK else 'changed ') + (', '.join(changed) if changed else 'nothing'))
