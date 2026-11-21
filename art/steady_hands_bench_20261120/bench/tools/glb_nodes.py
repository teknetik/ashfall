#!/usr/bin/env python3
"""Print world positions (glTF Y-up space, and Unity's x-flipped view) of nodes in a family GLB whose names match.
Usage: glb_nodes.py FAMILY_GLB PATTERN [PATTERN ...]   (substring match). No Blender, no Unity."""
import json, struct, sys

def load(p):
    f = open(p, 'rb'); f.read(12); n, = struct.unpack('<I', f.read(4)); f.read(4); return json.loads(f.read(n))

def qrot(q, v):
    x, y, z, w = q; vx, vy, vz = v
    tx = 2*(y*vz-z*vy); ty = 2*(z*vx-x*vz); tz = 2*(x*vy-y*vx)
    return (vx+w*tx+(y*tz-z*ty), vy+w*ty+(z*tx-x*tz), vz+w*tz+(x*ty-y*tx))

def qmul(a, b):
    ax, ay, az, aw = a; bx, by, bz, bw = b
    return (aw*bx+ax*bw+ay*bz-az*by, aw*by-ax*bz+ay*bw+az*bx, aw*bz+ax*by-ay*bx+az*bw, aw*bw-ax*bx-ay*by-az*bz)

G = load(sys.argv[1]); par = {}
for i, x in enumerate(G['nodes']):
    for c in x.get('children', []): par[c] = i

def world(i, p=(0, 0, 0)):
    while i is not None:
        x = G['nodes'][i]; s = x.get('scale', [1, 1, 1]); p = (p[0]*s[0], p[1]*s[1], p[2]*s[2])
        p = qrot(x.get('rotation', [0, 0, 0, 1]), p); t = x.get('translation', [0, 0, 0]); p = (p[0]+t[0], p[1]+t[1], p[2]+t[2])
        i = par.get(i)
    return p

def wrot(i):
    q = (0, 0, 0, 1)
    while i is not None:
        q = qmul(G['nodes'][i].get('rotation', [0, 0, 0, 1]), q); i = par.get(i)
    return q

for i, x in enumerate(G['nodes']):
    n = x.get('name', '')
    if any(pt in n for pt in sys.argv[2:]):
        w = world(i); q = wrot(i); ax = qrot(q, (0, 0, 1))
        print('%-46s world(gltf) %s  unity %s  parent %s  +Z(gltf) %s' % (n, [round(v, 4) for v in w], [round(-w[0], 4), round(w[1], 4), round(w[2], 4)],
              G['nodes'][par[i]].get('name') if i in par else '-', [round(v, 3) for v in ax]))
