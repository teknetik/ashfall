#!/usr/bin/env python3
"""Steady Hands bench, integration: what the lamps put on a white card (albedo 0.8) lying on the bench, by URP's
own formulas (no picture, no ambient, no shadows, no reflections). Linear RGB out of the lit shader, before the
game's grade. Bench-local metres. Usage: light_numbers.py [look.json]"""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
look = json.load(open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'look.json')))
lin = lambda c: [((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c]
def sub(a, b): return [a[i] - b[i] for i in range(3)]
def norm(a): l = math.sqrt(sum(x * x for x in a)); return [x / l for x in a], l
def light(P, pos, color, I, rng, aim=None, spot=None, inner=None, n=(0, 1, 0)):
    L, d = norm(sub(pos, P)); ndl = max(0.0, sum(L[i] * n[i] for i in range(3)))
    att = 1 / (d * d) * max(0.0, 1 - (d * d / (rng * rng)) ** 2) ** 2
    if spot:
        ax, _ = norm(sub(aim, pos)); cosd = -sum(L[i] * ax[i] for i in range(3))
        co, ci = math.cos(math.radians(spot / 2)), math.cos(math.radians(inner / 2))
        att *= max(0.0, min(1.0, (cosd - co) / (ci - co))) ** 2
    return [0.8 * c * I * att * ndl for c in lin(color)]
k = look['key']; s = look['session']
warm = [1, .76, .5]
# the Salvage shop's lamps in the bench's frame (shop-local minus the workbench's place (-1.3, 0.5, -5.875))
room = [('pendant over the workbench', [0, 2.98, 1.025], warm, 2.5, 5.5, 120, 66), ('pendant over the floor', [-0.45, 2.83, 3.325], warm, 2.2, 7, 140, 77),
        ('pendant over the counter', [2.6, 2.78, 3.125], warm, 2.2, 7, 140, 77)]
points = {'work mat, middle': [-0.03, .872, .195], 'work surface, front edge': [0, .872, .55], 'vise jaws (top)': [.325, 1.0, .33], 'pistol in the vise (grip)': [.42, 1.09, .35],
          'dish': [-.36, .872, .455], 'pad': [-.36, .872, .125], 'parts mat': [-.03, .872, .44], 'tray (right rear)': [-.66, .872, .18], 'press (right rear)': [-.56, .872, -.2],
          'tester (left)': [.52, .872, .05], 'card board (left rear)': [.95, 1.07, -.29], 'pistol as found (left front)': [.72, .88, .44], 'servo as found (far left)': [1.0, .89, .37], 'tool roll as found': [.76, .9, .06]}
print(f"{'white card at':32s} {'work lamp':>20s} {'shop lamps now':>20s} {'shop lamps at the bench':>24s} {'screen glow at the bench':>24s}   total at the bench (R G B)")
for name, P in points.items():
    key = light(P, k['pos'], k['color'], k['intensity'], k['range'], k['aim'], k['spot'], k['inner'])
    shop = [0, 0, 0]
    for _, pos, col, I, rng, sp, inn in room:
        c = light(P, pos, col, I, rng, [pos[0], 0, pos[2]], sp, inn); shop = [shop[i] + c[i] for i in range(3)]
    b = light(P, [1.5, 2.4, 2.475], [1, .82, .62], .45, 6.5); shop = [shop[i] + b[i] for i in range(3)]
    glow = light(P, [0, 1.208, .344], [.35, .85, 1], .45, 2.2)
    dim = [x * s['roomDim'] for x in shop]; g = [x * s.get('glowDim', s['screenDim']) for x in glow]
    tot = [key[i] + dim[i] + g[i] for i in range(3)]
    f = lambda c: ' '.join(f'{x:5.2f}' for x in c)
    print(f"{name:32s} {f(key):>20s} {f([shop[i] + glow[i] for i in range(3)]):>20s} {f(dim):>24s} {f(g):>24s}   {f(tot)}")
