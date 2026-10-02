"""Plot the basin heightfield around the Outer Berms with the survey's markers (design aid)."""
import json, sys
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
HF = sys.argv[1] if len(sys.argv) > 1 else '../basin_mountains_20261001/work/heightfield.npz'
OUT = sys.argv[2] if len(sys.argv) > 2 else 'work/area.png'
d = np.load(HF); H = d['H']; N = H.shape[0]
OXg, OZg = (float(d['grid'][2]), float(d['grid'][3])) if 'grid' in d else (-512.0, -512.0)
x0, x1, z0, z1 = [float(v) for v in (sys.argv[3].split(',') if len(sys.argv) > 3 and ',' in sys.argv[3] else '-300,-40,-190,180'.split(','))]
i0, i1, j0, j1 = int(x0-OXg), int(x1-OXg), int(z0-OZg), int(z1-OZg)
sub = H[j0:j1, i0:i1]
gy, gx = np.gradient(sub)
hs = np.clip((-gx*0.5 + -gy*0.62 + 0.6) / np.sqrt(gx**2+gy**2+1), 0, 1)
fig, ax = plt.subplots(figsize=(13, 13*(z1-z0)/(x1-x0)))
ax.imshow(hs, cmap='gray', origin='lower', extent=(x0, x1, z0, z1), alpha=1)
cs = ax.contour(np.arange(x0, x1), np.arange(z0, z1), sub, levels=[0, 2, 4, 6, 8, 10, 15, 20, 30, 40, 50], cmap='viridis', linewidths=.7)
ax.clabel(cs, fontsize=6)
s = json.load(open('survey.json'))
for m in s['markers']:
    p = m['pos']; k = m['kind']
    col = {'spawn': 'red', 'salvage': 'orange', 'landmark': 'cyan', 'npc': 'lime', 'target': 'magenta', 'interactable': 'yellow'}.get(k, 'white')
    ax.plot(p[0], p[2], 'o', ms=3, color=col)
for c in s['colliders']:
    if 'Boundary' in c['path']:
        mn, mx = c['min'], c['max']; ax.add_patch(plt.Rectangle((mn[0], mn[2]), mx[0]-mn[0], mx[2]-mn[2], fc='none', ec='red', lw=1))
ax.add_patch(plt.Rectangle((-104, -54), 44, 102, fc='none', ec='yellow', lw=1, ls='--'))
FP=json.load(open('footprint.json'))
import numpy as _np
poly=_np.array(FP['playable']+[FP['playable'][0]]);ax.plot(poly[:,0],poly[:,1],'-',color='orange',lw=2)
for extra in [e for e in sys.argv[4:] if e.count(',')==3]:
    a, b, c_, d_ = map(float, extra.split(',')); ax.add_patch(plt.Rectangle((a, c_), b-a, d_-c_, fc='none', ec='orange', lw=1.5))
ax.set_xlim(x0, x1); ax.set_ylim(z0, z1); ax.grid(alpha=.3); st = 20 if (x1-x0) < 400 else 50; ax.set_xticks(np.arange(x0, x1+1, st)); ax.set_yticks(np.arange(z0, z1+1, st))
fig.savefig(OUT, dpi=80, bbox_inches='tight')
