#!/usr/bin/env python3
"""Layout plan drawing: layout.json drawn over the top view of the existing bench (bench_top_under_head.png, 750 px/m).
Usage: python3 draw_plan.py   -> layout_plan.png"""
import json, math, subprocess, os
H = os.path.dirname(os.path.abspath(__file__))
L = json.load(open(H + '/layout.json'))
S, CX, CY = 750.0, 900.0, 500.0
FONT = '/usr/share/fonts/liberation/LiberationSans-Regular.ttf'
FONTB = '/usr/share/fonts/liberation/LiberationSans-Bold.ttf'


def P(x, y):
    return CX + x * S, CY - y * S


cmd = ['magick', H + '/bench_top_under_head.png', '-modulate', '135,60', '-background', 'white', '-gravity', 'northwest',
       '-extent', '2500x1180']
d = []
# obstacles
for o in L['bench']['obstacles']:
    if o['id'].startswith('print_head'):
        x0, y0 = P(o['x'][0], o['y'][1]); x1, y1 = P(o['x'][1], o['y'][0])
        d.append(f"fill none stroke '#ffcc00' stroke-width 2 stroke-dasharray 10 8 rectangle {x0:.0f},{y0:.0f} {x1:.0f},{y1:.0f} stroke-dasharray none")
        continue
    x0, y0 = P(o['x'][0], o['y'][1]); x1, y1 = P(o['x'][1], o['y'][0])
    d.append(f"fill 'rgba(255,60,40,0.35)' stroke '#ff3020' stroke-width 2 rectangle {x0:.0f},{y0:.0f} {x1:.0f},{y1:.0f}")
# reach arcs from the front edge centre (0.62 m and 0.80 m)
ex, ey = P(0, -0.583)
for r, c in ((0.62, '#40e060'), (0.80, '#e0e040')):
    d.append(f"fill none stroke '{c}' stroke-width 1.5 stroke-dasharray 4 6 ellipse {ex:.0f},{ey:.0f} {r*S:.0f},{r*S:.0f} 180,360 stroke-dasharray none")
legend = []
n = 0
for k, it in L['items'].items():
    n += 1
    tool = k.startswith('tools_')
    col = '#30d0ff' if not tool else '#ffa030'
    x, y = it['pos'][0], it['pos'][1]
    ox, oy = it.get('off', [0, 0])
    w, dp = it['size'][0], it['size'][1]
    cx, cy = P(x + ox, y + oy)
    if it.get('round'):
        d.append(f"fill 'rgba(255,255,255,0.10)' stroke '{col}' stroke-width 2.5 circle {cx:.0f},{cy:.0f} {cx + w/2*S:.0f},{cy:.0f}")
    else:
        d.append(f"fill 'rgba(255,255,255,0.10)' stroke '{col}' stroke-width 2.5 rectangle {cx - w/2*S:.0f},{cy - dp/2*S:.0f} {cx + w/2*S:.0f},{cy + dp/2*S:.0f}")
    d.append(f"fill '{col}' stroke none font '{FONTB}' font-size 20 text {cx - 8:.0f},{cy + 7:.0f} '{n}'")
    legend.append((n, col, f"{k}  {it['label']}  ({x:+.2f}, {y:+.2f})"))
# axes and player
d.append(f"fill none stroke white stroke-width 2 line {CX:.0f},{CY:.0f} {CX + 75:.0f},{CY:.0f} line {CX:.0f},{CY:.0f} {CX:.0f},{CY - 75:.0f}")
d.append(f"fill white stroke none font '{FONT}' font-size 16 text {CX + 80:.0f},{CY + 5:.0f} '+X 0.1 m' text {CX - 14:.0f},{CY - 82:.0f} '+Y'")
d.append(f"fill black stroke none font '{FONTB}' font-size 22 text 640,985 'PLAYER STANDS HERE (front edge y -0.583; bench camera 0.50 m out, 40 deg down)'")
d.append(f"fill black font '{FONT}' font-size 15 text 20,1010 'red: fused parts of the existing bench (screen, pendant, hanging loop).  yellow dashes: print head overhead (0.58 m up).  green / yellow arcs: 0.62 m and 0.80 m from the front edge centre.'")
d.append(f"fill black font '{FONTB}' font-size 24 text 1820,40 'Steady Hands bench: layout plan'")
d.append(f"fill black font '{FONT}' font-size 15 text 1820,64 'bench frame, metres; 750 px per metre; model-bench 20 Nov 2026'")
d.append(f"fill '#0090c0' font '{FONTB}' font-size 16 text 1820,92 'blue: fixtures family' fill '#d07000' text 2020,92 'orange: tools family'")
yy = 122
for n, col, t in legend:
    c2 = '#0090c0' if col == '#30d0ff' else '#d07000'
    t = t.replace("'", '')
    d.append(f"fill '{c2}' stroke none font '{FONTB}' font-size 14 text 1820,{yy} '{n}' fill black font '{FONT}' font-size 13 text 1848,{yy} '{t[:92]}'")
    yy += 30
cmd += ['-draw', ' '.join(d), H + '/layout_plan.png']
r = subprocess.run(cmd, capture_output=True, text=True)
if r.returncode:
    print(r.stderr[:600]); raise SystemExit(1)
print('wrote', H + '/layout_plan.png')
