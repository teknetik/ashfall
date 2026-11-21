# The grip_gyro_braced mod's mount points (vertices within 0.5 mm of the Meshy ScrapPistol skin) and, for each, the
# nearest part of a pistol.glb (P metres) and its signed gap. numpy only, uses integration/glbgeom.py (read only).
# Usage: python3 gyro_points.py PISTOL_GLB OUT_JSON
import sys, os, json, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); B = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(B, 'integration'))
from glbgeom import Model, Surface
A = os.path.abspath(os.path.join(B, '..', '..', 'unity/AthenHill/Assets/AthenHill/Art'))
S = 0.136736
def to_mm(p):
    p = np.asarray(p, float); return np.stack([p[..., 0], -p[..., 2], p[..., 1]], -1) * S * 1000
old = Model(os.path.join(A, 'OuterBerms/ScrapPistol.glb')); mods = Model(os.path.join(A, 'Weapons/PistolMods/PistolMods.glb'))
OS = Surface(to_mm(np.concatenate([old.tris(n) for n in old.mesh_nodes()])))
node = [n for n in mods.mesh_nodes() if 'gyro' in n][0]
v = to_mm(mods.tris(node).reshape(-1, 3)); v = np.unique(np.round(v, 4), axis=0)
mount = [p for p in v if OS.closest(p)[0] <= 0.5]
new = Model(sys.argv[1]); parts = {}
for nm in new.mesh_nodes():
    if nm.startswith('pistol_') and not nm.startswith('pistol_card'):
        t = new.tris(nm); parts[nm] = Surface(np.stack([t[..., 0], -t[..., 2], t[..., 1]], -1) * 1000)
rows = []
for p in mount:
    best = min(((s.closest(p)[0], k) for k, s in parts.items()))
    d = best[0]; ins = parts[best[1]].inside(p)
    rows.append({'p': [round(float(x), 2) for x in p], 'part': best[1], 'gap': round(-d if ins else d, 2), 'skin_n': [round(float(x), 3) for x in OS.n[OS.closest(p)[3]]]})
rows.sort(key=lambda r: -r['gap'])
json.dump(rows, open(sys.argv[2], 'w'), indent=0)
print(len(mount), 'mount points; over 1 mm:', sum(r['gap'] > 1 for r in rows))
for r in rows[:24]: print(r)
