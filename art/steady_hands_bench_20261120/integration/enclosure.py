#!/usr/bin/env python3
"""Steady Hands bench, integration: which parts of a family cannot be seen while it is assembled as found.

A part is ENCLOSED when no ray leaves it: from up to 48 points on it, in 40 directions spread over the sphere, every ray
meets an opaque surface of another part of the family (glass does not block). The parts a ray meets last on its way out
are the part's SHELLS (a case body, its lid, the screws in the lid): while every shell and the part sit where they sat as
found, the part is hidden and needs no draw. BenchLook checks that at run time by pose, not by the bench's place names.

Usage: enclosure.py [family ...] [--json OUT]       (default: servo pistol; writes integration/enclosure.json)
numpy only. The families' GLBs are read from Assets/AthenHill/Art/Bench/<Family>/ in their as-found pose."""
import json, os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from glbgeom import Model
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
ART = os.path.join(ROOT, 'unity/AthenHill/Assets/AthenHill/Art/Bench')
args = [a for a in sys.argv[1:]]
OUT = args[args.index('--json') + 1] if '--json' in args else os.path.join(HERE, 'enclosure.json')
fams = [a for a in args if not a.startswith('--') and a != OUT] or ['servo', 'pistol']

def sphere(n=40):
    i = np.arange(n) + .5; phi = np.arccos(1 - 2 * i / n); th = np.pi * (1 + 5 ** .5) * i
    return np.stack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)], 1)
DIRS = sphere(40)

def cast(T, owner, o, d):
    """All hits of a ray against triangles T (n,3,3): (t, owner index) sorted by t."""
    v0 = T[:, 0]; e1 = T[:, 1] - v0; e2 = T[:, 2] - v0
    pv = np.cross(d, e2); det = np.einsum('ij,ij->i', e1, pv); ok = np.abs(det) > 1e-14
    inv = np.where(ok, 1 / np.where(ok, det, 1), 0); tv = o - v0
    u = np.einsum('ij,ij->i', tv, pv) * inv; qv = np.cross(tv, e1); v = (qv @ d) * inv; t = np.einsum('ij,ij->i', e2, qv) * inv
    h = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1e-7)
    return t[h], owner[h]

report = {'generated': time.strftime('%Y-%m-%d %H:%M'), 'tool': 'art/steady_hands_bench_20261120/integration/enclosure.py', 'rays': '48 points x 40 directions per part', 'families': {}}
t0 = time.time()
for fam in fams:
    cap = fam[0].upper() + fam[1:]
    glb = os.path.join(ART, cap, fam + '.glb'); parts = json.load(open(os.path.join(ART, cap, fam + '.parts.json')))['parts']
    m = Model(glb); ids = [p['id'] for p in parts]; node = {p['id']: p['node'] for p in parts}
    tri = {}; opaque = {}
    for pid in ids:
        if node[pid] not in m.byname or 'mesh' not in m.js['nodes'][m.byname[node[pid]]]: continue
        tri[pid] = m.tris(node[pid]); opaque[pid] = m.tris(node[pid], opaque_only=True)
    rows = {}
    for x in tri:
        others = [p for p in opaque if p != x and len(opaque[p])]
        T = np.concatenate([opaque[p] for p in others]); owner = np.concatenate([np.full(len(opaque[p]), k) for k, p in enumerate(others)])
        v = np.unique(tri[x].reshape(-1, 3), axis=0)
        rng = np.random.default_rng(7); pts = v[rng.choice(len(v), min(48, len(v)), replace=False)]
        centre = tri[x].reshape(-1, 3).mean(0)
        pts = pts + (centre - pts) * 1e-3          # a hair inside the part, so its own surface is not in the way (it is left out anyway)
        shells = set(); escaped = 0; rays = 0
        for o in pts:
            for d in DIRS:
                rays += 1; t, k = cast(T, owner, o, d)
                if len(t) == 0: escaped += 1; break
                shells.add(others[int(k[np.argmax(t)])])
            if escaped: break
        rows[x] = {'enclosed': not escaped, 'shells': sorted(shells) if not escaped else [], 'raysCast': rays}
    report['families'][fam] = rows
    print(fam, 'enclosed:', [p for p, r in rows.items() if r['enclosed']])
report['seconds'] = round(time.time() - t0, 1)
json.dump(report, open(OUT, 'w'), indent=1)
print('->', os.path.relpath(OUT, ROOT), report['seconds'], 's')
