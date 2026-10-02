"""Zoomed hillshade of the playable floor with slope shading (design aid)."""
import json, sys
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
HF, OUT = sys.argv[1], sys.argv[2]
x0, x1, z0, z1 = [float(v) for v in (sys.argv[3].split(',') if len(sys.argv) > 3 else '-215,-50,-95,85'.split(','))]
d = np.load(HF); H = d['H']
OXg, OZg = (float(d['grid'][2]), float(d['grid'][3])) if 'grid' in d else (-512.0, -512.0)
i0, i1, j0, j1 = int(x0-OXg), int(x1-OXg), int(z0-OZg), int(z1-OZg)
sub = H[j0:j1, i0:i1].astype(float)
gz, gx = np.gradient(sub)
L = np.array([-0.45, 0.6, -0.65]); L /= np.linalg.norm(L)
n = np.dstack([-gx, np.ones_like(sub), -gz]); n /= np.linalg.norm(n, axis=2, keepdims=True)
hs = np.clip((n * L).sum(2), 0, 1)
slope = np.degrees(np.arctan(np.hypot(gx, gz)))
rgb = np.dstack([hs]*3) * np.array([0.92, 0.8, 0.66])
rgb[slope > 30] = rgb[slope > 30] * 0.6 + np.array([0.5, 0.1, 0.1]) * 0.4
fig, ax = plt.subplots(figsize=(14, 15))
ax.imshow(rgb, origin='lower', extent=(x0, x1, z0, z1))
cs = ax.contour(np.arange(x0, x1), np.arange(z0, z1), sub, levels=list(range(-2, 14, 1)), colors='k', linewidths=.3, alpha=.5)
FP = json.load(open('footprint.json'))
poly = np.array(FP['playable'] + [FP['playable'][0]]); ax.plot(poly[:, 0], poly[:, 1], '-', color='orange', lw=1.5)
ax.add_patch(plt.Rectangle((-104, -54), 44, 102, fc='none', ec='yellow', lw=1, ls='--'))
s = json.load(open('survey.json'))
for m in s['markers']:
    p = m['pos']; col = {'spawn': 'red', 'salvage': 'orange', 'landmark': 'cyan', 'npc': 'lime', 'target': 'magenta'}.get(m['kind'], 'white')
    ax.plot(p[0], p[2], 'o', ms=3, color=col)
for extra in sys.argv[4:]:
    pts = json.load(open(extra))
    for p in pts: ax.plot(p['x'], p['z'], p.get('m', 's'), ms=p.get('ms', 6), color=p.get('c', 'blue')); ax.text(p['x']+1, p['z']+1, p.get('label', ''), fontsize=7, color=p.get('c', 'blue'))
ax.set_xticks(np.arange(x0, x1+1, 10)); ax.set_yticks(np.arange(z0, z1+1, 10)); ax.grid(alpha=.25); ax.tick_params(labelsize=7)
fig.savefig(OUT, dpi=72, bbox_inches='tight')
