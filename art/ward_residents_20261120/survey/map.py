"""Top-down SVG/PNG of the saved city's colliders, walkers, NPCs and sit points from the residents survey (read-only).
Usage: map.py NAME x0 x1 z0 z1 [routes.json]   -> NAME.png (via ImageMagick). +x right, +z up."""
import json, subprocess, sys
d = json.load(open('/home/teknetik/code/ao2/unity/evidence/showcase_phase2/20261120/residents/survey.json'))
name, x0, x1, z0, z1 = sys.argv[1], *map(float, sys.argv[2:6])
extra = json.load(open(sys.argv[6])) if len(sys.argv) > 6 else {}
S = 30.0
W, H = (x1 - x0) * S, (z1 - z0) * S
X = lambda x: (x - x0) * S
Y = lambda z: (z1 - z) * S
o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}"><rect width="100%" height="100%" fill="white"/>']
for x in range(int(x0), int(x1) + 1):
    o.append(f'<line x1="{X(x)}" y1="0" x2="{X(x)}" y2="{H}" stroke="#ddd" stroke-width="{2 if x % 5 == 0 else .5}"/>')
    if x % 2 == 0: o.append(f'<text x="{X(x)+1}" y="10" font-size="9" fill="#888">{x}</text>')
for z in range(int(z0), int(z1) + 1):
    o.append(f'<line x1="0" y1="{Y(z)}" x2="{W}" y2="{Y(z)}" stroke="#ddd" stroke-width="{2 if z % 5 == 0 else .5}"/>')
    if z % 2 == 0: o.append(f'<text x="1" y="{Y(z)-1}" font-size="9" fill="#888">{z}</text>')
for c in d['colliders']:
    mn, mx = c['min'], c['max']
    if mx[0] < x0 or mn[0] > x1 or mx[2] < z0 or mn[2] > z1: continue
    o.append(f'<rect x="{X(mn[0])}" y="{Y(mx[2])}" width="{(mx[0]-mn[0])*S}" height="{(mx[2]-mn[2])*S}" fill="#a08060" fill-opacity=".35" stroke="black" stroke-width=".6"><title>{c["p"]}</title></rect>')
def poly(pts, col, label, closed=True):
    pp = pts + ([pts[0]] if closed else [])
    o.append(f'<polyline points="{" ".join(f"{X(p[0])},{Y(p[1])}" for p in pp)}" fill="none" stroke="{col}" stroke-width="3"/>')
    for p in pts: o.append(f'<circle cx="{X(p[0])}" cy="{Y(p[1])}" r="4" fill="{col}"/>')
    o.append(f'<text x="{X(pts[0][0])+4}" y="{Y(pts[0][1])-4}" font-size="12" fill="{col}">{label}</text>')
for w in d['walkers']:
    if w['active']: poly([[q[0], q[2]] for q in w['waypoints']], 'blue', w['path'].split('/')[-1])
for n in d['npcs']:
    o.append(f'<circle cx="{X(n["pos"][0])}" cy="{Y(n["pos"][2])}" r="7" fill="red"/><text x="{X(n["pos"][0])+8}" y="{Y(n["pos"][2])}" font-size="12" fill="red">{n["id"]}</text>')
for n in d['named']:
    if 'sit point' in n['path']: o.append(f'<circle cx="{X(n["pos"][0])}" cy="{Y(n["pos"][2])}" r="4" fill="green"/>')
for k, v in extra.items():
    poly(v['pts'], v.get('col', 'magenta'), k, v.get('closed', True))
    for s in v.get('stops', []): o.append(f'<rect x="{X(s[0])-6}" y="{Y(s[1])-6}" width="12" height="12" fill="orange"/>')
o.append('</svg>')
open(name + '.svg', 'w').write('\n'.join(o))
subprocess.run(['magick', name + '.svg', name + '.png'], check=True)
