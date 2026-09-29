import re
s = open('/home/teknetik/code/ao2/unity/AthenHill/Assets/AthenHill/Scenes/AthenHill.unity').read()
docs = re.split(r'^--- ', s, flags=re.M)
names, tf, tf_go, go_tf = {}, {}, {}, {}
for d in docs:
    m = re.match(r'!u!(\d+) &(\d+)', d)
    if not m: continue
    c, f = m.groups()
    if c == '1':
        mm = re.search(r'm_Name: (.*)', d); names[f] = mm.group(1).strip() if mm else ''
    elif c == '4':
        gm = re.search(r'm_GameObject: \{fileID: (\d+)\}', d)
        if not gm: continue
        g = gm.group(1)
        p = re.search(r'm_LocalPosition: \{x: ([-\d.e]+), y: ([-\d.e]+), z: ([-\d.e]+)\}', d)
        sc = re.search(r'm_LocalScale: \{x: ([-\d.e]+), y: ([-\d.e]+), z: ([-\d.e]+)\}', d)
        fa = re.search(r'm_Father: \{fileID: (\d+)\}', d).group(1)
        tf[f] = (g, tuple(map(float, p.groups())), tuple(map(float, sc.groups())), fa); go_tf[g] = f
for f, (g, p, sc, fa) in tf.items():
    n = names.get(g, '')
    if re.search(r'BLD_shop_w_0\d_(porch|first_step) recessed joint mortar', n):
        chain = []; cur = f
        while cur in tf and cur != '0':
            gg, pp, ss, ff = tf[cur]; chain.append((names.get(gg, '?')[:30], pp, ss)); cur = ff
        print(n, chain[:4])
