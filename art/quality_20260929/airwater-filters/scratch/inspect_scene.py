"""Inspect the saved Unity scene/prefab for the Air + Water filter bank (read-only).

Maps prefab GameObjects named 'air_water Filter*|Roof to filter|Feed*|Pipe clamp|Rainwater' to their renderers, then
reports scene-instance overrides (enabled state, materials, mesh) and any colliders under the bank.
"""
import re, json, sys
from pathlib import Path

ROOT = Path('/home/teknetik/code/ao2/unity/AthenHill/Assets/AthenHill')
PREFAB = ROOT / 'Art/Quality/StoreArchitecture/Revision04/air_water/air_water.prefab'
SCENE = ROOT / 'Scenes/AthenHill.unity'
KEY = re.compile(r'air_water (Filter|Roof to filter|Feed |Pipe clamp|Rainwater|Twin vessel|Vessel feed)')

txt = PREFAB.read_text()
docs = re.split(r'^--- ', txt, flags=re.M)
go = {}      # gameobject fileID -> name
comps = {}   # gameobject fileID -> [component fileIDs]
kind = {}
for d in docs:
    m = re.match(r'!u!(\d+) &(\d+)', d)
    if not m:
        continue
    cls, fid = m.group(1), m.group(2)
    kind[fid] = cls
    if cls == '1':
        nm = re.search(r'm_Name: (.*)', d).group(1).strip()
        go[fid] = nm
        comps[fid] = re.findall(r'component: \{fileID: (\d+)\}', d)
bank = {fid: n for fid, n in go.items() if KEY.search(n)}
rend = {}
for fid, n in bank.items():
    for c in comps[fid]:
        if kind.get(c) == '23':
            rend[c] = n
colliders = [n for fid, n in go.items() if any(kind.get(c) in ('64', '65', '135', '136', '136', '143') for c in comps[fid])]
print('prefab GameObjects total', len(go), 'bank objects', len(bank), 'bank renderers', len(rend))
print('prefab colliders (all building):', len(colliders), colliders[:12])

s = SCENE.read_text()
guid = re.search(r'guid: (\w+)', (PREFAB.parent / 'air_water.prefab.meta').read_text()).group(1)
# locate the scene PrefabInstance block(s) that source this prefab
blocks = re.split(r'^--- ', s, flags=re.M)
inst = [b for b in blocks if b.startswith('!u!1001') and guid in b]
print('scene prefab instances of air_water:', len(inst))
b = inst[0]
mods = re.findall(r'- target: \{fileID: (\d+), guid: %s, type: 3\}\n\s+propertyPath: ([^\n]+)\n\s+value: ([^\n]*)\n\s+objectReference: (\{[^\n]*\})' % guid, b)
print('override entries', len(mods))
hits = {}
for fid, path, val, ref in mods:
    if fid in rend:
        hits.setdefault(rend[fid], []).append((path, val, ref))
print('bank renderers with overrides:', len(hits))
for n, v in sorted(hits.items()):
    print(' ', n, v)
# disabled renderers overall (names)
dis = [rend[f] for f, p, v, r in mods if f in rend and p == 'm_Enabled' and v.strip() == '0']
print('bank renderers disabled in scene:', dis)
loc = {}
for fid, path, val, ref in mods:
    if fid == '5826893501811737497' and path.startswith('m_Local'):
        loc[path] = val
print('building root transform overrides', loc)
# any scene-level objects (not part of prefab) named like bank fittings / colliders near Air+Water
extra = re.findall(r'm_Name: ((?:air_water|Air Water|AirWater)[^\n]*)', s)
print('scene-level names mentioning air_water (non-prefab):', sorted(set(extra))[:40])
