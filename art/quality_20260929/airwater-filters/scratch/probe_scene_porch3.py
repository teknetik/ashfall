"""Read-only: saved-scene porch / first-step objects (names BLD_shop_w_NN_porch|first_step, no suffix), local position + parent, and colliders on them."""
import re
s = open('/home/teknetik/code/ao2/unity/AthenHill/Assets/AthenHill/Scenes/AthenHill.unity').read()
docs = re.split(r'^--- ', s, flags=re.M)
names, comps, kind, tf = {}, {}, {}, {}
for d in docs:
    m = re.match(r'!u!(\d+) &(\d+)', d)
    if not m:
        continue
    c, f = m.groups()
    kind[f] = c
    if c == '1':
        mm = re.search(r'm_Name: (.*)', d)
        names[f] = mm.group(1).strip() if mm else ''
        comps[f] = re.findall(r'component: \{fileID: (\d+)\}', d)
    elif c == '4':
        gm = re.search(r'm_GameObject: \{fileID: (\d+)\}', d)
        pm = re.search(r'm_LocalPosition: \{x: ([-\d.e]+), y: ([-\d.e]+), z: ([-\d.e]+)\}', d)
        sm = re.search(r'm_LocalScale: \{x: ([-\d.e]+), y: ([-\d.e]+), z: ([-\d.e]+)\}', d)
        fm = re.search(r'm_Father: \{fileID: (\d+)\}', d)
        if gm and pm:
            tf[gm.group(1)] = (tuple(float(x) for x in pm.groups()), tuple(float(x) for x in sm.groups()) if sm else None, fm.group(1) if fm else '0')
tf_to_go = {}
for d in docs:
    m = re.match(r'!u!4 &(\d+)', d)
    if m:
        gm = re.search(r'm_GameObject: \{fileID: (\d+)\}', d)
        if gm:
            tf_to_go[m.group(1)] = gm.group(1)
for g, nm in names.items():
    if re.fullmatch(r'BLD_shop_w_\d+_(porch|first_step)|Ward shop.*|.*[Pp]orch(?! settled)(?!.*chip)(?!.*mortar).*', nm) and g in tf and 'chip' not in nm and 'mortar' not in nm:
        p, sc, par = tf[g]
        cols = [kind.get(c) for c in comps[g] if kind.get(c) in ('65', '64', '135', '136')]
        print(nm, p, sc, 'parent', names.get(tf_to_go.get(par, ''), par), 'colliders', cols)
