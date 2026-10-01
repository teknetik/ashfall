"""Top-down footprint map of the city from the street-dressing audit (renderer bounds), for planning review cameras."""
import json, sys
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
d = json.load(open('unity/evidence/street-dressing/20260930/audit.json'))
fig, ax = plt.subplots(figsize=(16, 12))
for r in d['renderers']:
    c, s = r.get('center'), r.get('size')
    if not c or not r['active'] or r['path'].startswith(('Paving', 'City Render Chunks', 'Desert', 'Outer Berms')): continue
    if s[0] * s[2] > 4000 or c[1] - s[1] / 2 > 3: continue
    if s[1] < 0.4 and s[0] * s[2] > 30: col = 'tab:orange'
    elif s[1] > 2.5: col = 'tab:blue'
    else: col = 'tab:green'
    ax.add_patch(Rectangle((c[0] - s[0] / 2, c[2] - s[2] / 2), s[0], s[2], fill=False, lw=.3, ec=col))
for c in d['colliders']:
    pass
for x in range(-60, 61, 4): ax.axvline(x, color='0.85', lw=.3, zorder=0)
for z in range(-44, 45, 4): ax.axhline(z, color='0.85', lw=.3, zorder=0)
ax.add_patch(Rectangle((-60, -45), 120, 90, fill=False, ec='k', lw=1))
ax.set_xlim(-62, 62); ax.set_ylim(-47, 47); ax.set_aspect('equal'); ax.set_xticks(range(-60, 61, 8)); ax.set_yticks(range(-44, 45, 8)); ax.grid(False)
ax.set_xlabel('X east (m)'); ax.set_ylabel('Z north (m)')
fig.savefig(sys.argv[1], dpi=110, bbox_inches='tight')
