#!/usr/bin/env python3
"""Planning / review plot of the bowl: hillshade, sites, routes, survey markers, and (if present) features.json and the
region masks. -> work/plan.png (or the path given). Run: uv run --with numpy --with scipy --with matplotlib python plot_plan.py"""
import json, sys
import numpy as np
from bv_common import Field, HERE, sites, routes, survey, RX0, RZ0, RSIZE
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt

F = Field()
out = sys.argv[1] if len(sys.argv) > 1 else str(HERE / 'work/plan.png')
xa, xb, za, zb = RX0, RX0 + RSIZE, RZ0, RZ0 + RSIZE
ja, jb = int(za - F.oz), int(zb - F.oz); ia, ib = int(xa - F.ox), int(xb - F.ox)
H = F.H[ja:jb, ia:ib]; gz, gx = np.gradient(H)
shade = np.clip(0.6 - 0.45 * gx - 0.65 * gz, 0, 1)
fig, ax = plt.subplots(figsize=(16, 16))
mask_png = HERE / 'work/regions_preview.png'
if mask_png.exists() and '--masks' in sys.argv:
    img = plt.imread(mask_png)
    ax.imshow(shade, cmap='gray', origin='lower', extent=(xa, xb, za, zb))
    ax.imshow(img, origin='lower', extent=(xa, xb, za, zb), alpha=0.55)
else:
    ax.imshow(shade, cmap='gray', origin='lower', extent=(xa, xb, za, zb))
pl = F.playable[ja:jb, ia:ib]
ax.contour(np.arange(xa, xb), np.arange(za, zb), pl.astype(float), [0.5], colors='k', linewidths=1)
for r in routes():
    a = np.array(r); ax.plot(a[:, 0], a[:, 1], 'c--', lw=1)
for s in sites():
    ax.add_patch(plt.Circle(s['centre'], 22 if s['waystation'] else 18, fill=False, color='r'))
    ax.text(s['centre'][0], s['centre'][1] + 20, s['name'], color='r', fontsize=8, ha='center')
sv = survey()
if sv:
    col = dict(spawn='m', salvage='y', interactable='orange', landmark='b', encounter='r', loot='y')
    for m in sv['markers']:
        if m['kind'] in col: ax.plot(m['pos'][0], m['pos'][2], '.', color=col[m['kind']], ms=4)
    for c in sv['colliders']:
        if c['trigger'] or c['path'].startswith('Outer Berms/Berms expanse/Boundary'): continue
        x0, _, z0 = c['min']; x1, _, z1 = c['max']
        if (x1 - x0) * (z1 - z0) > 3000: continue
        ax.add_patch(plt.Rectangle((x0, z0), x1 - x0, z1 - z0, fill=False, color='brown', lw=0.4))
fp = HERE / 'features.json'
if fp.exists():
    f = json.loads(fp.read_text())
    for e in f.get('earthworks', []):
        for seg in e['segments']:
            a = np.array(seg); ax.plot(a[:, 0], a[:, 1], '-', color='saddlebrown', lw=3)
    for c in f.get('craters', []): ax.add_patch(plt.Circle((c['x'], c['z']), c['r'], fill=False, color='k', lw=1))
    for o in f.get('outcrops', []):
        a = np.array(o['outline'] + [o['outline'][0]]); ax.plot(a[:, 0], a[:, 1], '-', color='darkred', lw=1.2)
    for t in f.get('tracks', []):
        a = np.array(t['pts']); ax.plot(a[:, 0], a[:, 1], ':', color={'warden': 'blue', 'caravan': 'navy', 'droid': 'purple', 'haul': 'purple'}.get(t['kind'], 'b'), lw=1.5)
    pp = HERE / 'placements.json'
    if pp.exists():
        for p in json.loads(pp.read_text())['prefabs']:
            ax.plot(p['x'], p['z'], 'x' if p['group'] == 'Wreckage' else '.', color='lime' if p['group'] == 'Wreckage' else 'darkgreen', ms=3)
for cam in json.loads((HERE / 'review_cameras.json').read_text())['cameras']:
    ax.annotate('', xy=(cam['target'][0], cam['target'][2]), xytext=(cam['pos'][0], cam['pos'][2]), arrowprops=dict(arrowstyle='->', color='gold', lw=0.8))
    ax.text(cam['pos'][0], cam['pos'][2], cam['name'][7:], color='gold', fontsize=6)
ax.set_xlim(xa, xb); ax.set_ylim(za, zb); ax.set_aspect('equal'); ax.grid(alpha=0.25)
fig.savefig(out, dpi=60, bbox_inches='tight')
print(out)
