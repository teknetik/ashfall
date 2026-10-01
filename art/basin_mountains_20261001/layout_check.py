"""Layout check for the basin (render-only, no colliders): the new surface against the playable space and every scene
marker/camera. Inputs: work/heightfield.npz, the 1 Oct scene audit and cameras.json. Output: layout-check.json."""
import gzip, json, math
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
EV = Path('/home/teknetik/code/ao2/unity/evidence/basin-mountains/20261001')
hf = np.load(HERE / 'work/heightfield.npz'); H = hf['H'].astype(float); OLD = hf['old'].astype(float); T = hf['t'].astype(float)
N, ORG = 1025, -512.0
BERMS = (-104.0, -60.0, -54.0, 48.0)
def at(A, x, z):
    fx, fz = x - ORG, z - ORG; i, j = int(fx), int(fz); u, v = fx - i, fz - j
    return A[j, i] * (1 - u) * (1 - v) + A[j, i + 1] * u * (1 - v) + A[j + 1, i] * (1 - u) * v + A[j + 1, i + 1] * u * v
def inside_berms(x, z, m=0.0):
    return BERMS[0] - m <= x <= BERMS[1] + m and BERMS[2] - m <= z <= BERMS[3] + m
def in_city(x, z): return abs(x) <= 62 and abs(z) <= 48
ax = ORG + np.arange(N); X, Z = np.meshgrid(ax, ax)
x0, x1, z0, z1 = BERMS
dxo = np.maximum(np.maximum(x0 - X, X - x1), 0); dzo = np.maximum(np.maximum(z0 - Z, Z - z1), 0); outside = np.hypot(dxo, dzo)
rec = {}
band = (outside <= 0.75) & np.isfinite(OLD)
rec['berms_footprint_plus_0.75m_max_abs_dev_from_old_m'] = float(np.abs(H[band] - OLD[band]).max())
ring = (T >= 0) & (T <= 3) & (outside > 7)
rec['city_rim_0_3m_height_range_m'] = [float(H[ring].min()), float(H[ring].max())]
ring2 = (T >= 0) & (T <= 15) & (outside > 7)
rec['city_rim_0_15m_max_height_m'] = float(H[ring2].max())
rec['city_rim_0_15m_old_max_height_m'] = float(np.nanmax(np.where(ring2, OLD, np.nan)))
a = json.loads(gzip.open(EV / 'audit-before.json.gz').read())
issues = []
for m in a['markers']:
    x, y, z = m['pos']
    if in_city(x, z) or inside_berms(x, z): continue
    h = at(H, x, z)
    issues.append(dict(kind='marker', path=m['path'], pos=m['pos'], terrain=round(h, 2), buried=bool(y < h)))
cams = json.loads((EV / 'cameras.json').read_text())['cameras']
for c in cams:
    x, y, z = c['pos']
    if in_city(x, z) or inside_berms(x, z): continue
    h = at(H, x, z)
    issues.append(dict(kind='camera', path=c['name'], pos=c['pos'], terrain=round(h, 2), buried=bool(y < h + 0.3)))
rec['outside_markers_and_cameras'] = issues
rec['buried'] = [i for i in issues if i['buried']]
rec['colliders'] = 'none (render-only, as before); the playable floor outside the walls is the Outer Berms ground collider, untouched'
(HERE / 'layout-check.json').write_text(json.dumps(rec, indent=1))
print(json.dumps({k: v for k, v in rec.items() if k != 'outside_markers_and_cameras'}, indent=1)); print(len(issues), 'outside items')
