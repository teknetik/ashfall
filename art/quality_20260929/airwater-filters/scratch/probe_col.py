import re
s = open('/home/teknetik/code/ao2/unity/AthenHill/Assets/AthenHill/Scenes/AthenHill.unity').read()
docs = re.split(r'^--- ', s, flags=re.M)
names, gtf, tfd, comps = {}, {}, {}, {}
box = []
def num(m): return tuple(float(x) for x in m.groups())
for d in docs:
    m = re.match(r'!u!(\d+) &(\d+)', d)
    if not m: continue
    c, f = m.groups()
    if c == '1':
        mm = re.search(r'm_Name: (.*)', d); names[f] = mm.group(1).strip() if mm else ''
    elif c == '4':
        gm = re.search(r'm_GameObject: \{fileID: (\d+)\}', d)
        if not gm: continue
        p = num(re.search(r'm_LocalPosition: \{x: ([-\d.e]+), y: ([-\d.e]+), z: ([-\d.e]+)\}', d))
        q = re.search(r'm_LocalRotation: \{x: ([-\d.e]+), y: ([-\d.e]+), z: ([-\d.e]+), w: ([-\d.e]+)\}', d)
        sc = num(re.search(r'm_LocalScale: \{x: ([-\d.e]+), y: ([-\d.e]+), z: ([-\d.e]+)\}', d))
        fa = re.search(r'm_Father: \{fileID: (\d+)\}', d).group(1)
        tfd[f] = (gm.group(1), p, tuple(map(float, q.groups())), sc, fa); gtf[gm.group(1)] = f
    elif c == '65':
        gm = re.search(r'm_GameObject: \{fileID: (\d+)\}', d)
        ce = num(re.search(r'm_Center: \{x: ([-\d.e]+), y: ([-\d.e]+), z: ([-\d.e]+)\}', d))
        sz = num(re.search(r'm_Size: \{x: ([-\d.e]+), y: ([-\d.e]+), z: ([-\d.e]+)\}', d))
        box.append((gm.group(1), ce, sz))
import math
def world(tf):
    # returns (pos, yaw-only rotation, scale) composed root-down
    chain = []
    cur = tf
    while cur in tfd:
        chain.append(cur); cur = tfd[cur][4]
    pos = (0.0, 0.0, 0.0); yaw = 0.0
    for t in reversed(chain):
        g, p, q, sc, fa = tfd[t]
        # local pos scaled (assume 1) rotated by parent yaw
        c, s_ = math.cos(yaw), math.sin(yaw)
        pos = (pos[0] + c * p[0] + s_ * p[2], pos[1] + p[1], pos[2] - s_ * p[0] + c * p[2])
        yaw += 2 * math.atan2(q[1], q[3])
    return pos, yaw
for g, ce, sz in box:
    if g not in gtf: continue
    pos, yaw = world(gtf[g])
    c, s_ = math.cos(yaw), math.sin(yaw)
    wx = pos[0] + c * ce[0] + s_ * ce[2]; wz = pos[2] - s_ * ce[0] + c * ce[2]
    if -19.6 < wx < -16.0 and -13 < wz < -4:
        print(f"{names.get(g,'?')[:44]:44s} pos=({wx:7.2f},{pos[1]+ce[1]:6.2f},{wz:7.2f}) yaw={math.degrees(yaw):6.1f} size={tuple(round(v,2) for v in sz)}")
