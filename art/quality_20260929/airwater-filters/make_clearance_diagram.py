"""Front-door clearance diagram (plan + elevation) for the Air + Water filter fittings, task t_bd3d9fe3.

    env -i HOME=$HOME PATH=/usr/bin:/bin /usr/bin/python3 make_clearance_diagram.py
Inputs: measurements.json (from measure_aw.py).  Output: renders/clearance-diagram.png (pycairo).  A-space metres.
"""
import json, math
from pathlib import Path
import cairo

OUT = Path('/home/teknetik/code/ao2/art/quality_20260929/airwater-filters')
m = json.loads((OUT / 'measurements.json').read_text())
gap = m['clearances']
W, H = 1700, 1560
S = 175.0                                    # px per metre (both views)
surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
c = cairo.Context(surf)
c.set_source_rgb(1, 1, 1); c.paint()
c.select_font_face('Liberation Sans', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)


def rgb(h):
    h = h.lstrip('#')
    if len(h) == 3:
        h = ''.join(ch * 2 for ch in h)
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def text(x, y, s, size=13, col='#222'):
    c.set_font_size(size); c.set_source_rgb(*rgb(col)); c.move_to(x, y); c.show_text(s); c.new_path()


class View:
    def __init__(self, x0, ybase, xmin, ymin, up):
        self.x0, self.yb, self.xmin, self.ymin, self.up = x0, ybase, xmin, ymin, up      # up: +v goes up the page

    def p(self, x, v):
        return self.x0 + (x - self.xmin) * S, self.yb - (v - self.ymin) * S if self.up else self.yb + (v - self.ymin) * S

    def rect(self, x, v, w, h, fc=None, ec='#000', lw=1, dash=None):
        (X, Y), (X2, Y2) = self.p(x, v), self.p(x + w, v + h)
        c.rectangle(min(X, X2), min(Y, Y2), abs(X2 - X), abs(Y2 - Y))
        if fc:
            c.set_source_rgb(*rgb(fc)); c.fill_preserve()
        c.set_source_rgb(*rgb(ec)); c.set_line_width(lw); c.set_dash(dash or []); c.stroke(); c.set_dash([])

    def circ(self, x, v, r, fc=None, ec='#000', lw=1):
        X, Y = self.p(x, v); c.arc(X, Y, r * S, 0, 2 * math.pi)
        if fc:
            c.set_source_rgb(*rgb(fc)); c.fill_preserve()
        c.set_source_rgb(*rgb(ec)); c.set_line_width(lw); c.stroke()

    def line(self, x0, v0, x1, v1, col='#b33', lw=1.2, dash=None):
        a, b = self.p(x0, v0), self.p(x1, v1); c.move_to(*a); c.line_to(*b); c.set_source_rgb(*rgb(col)); c.set_line_width(lw); c.set_dash(dash or []); c.stroke(); c.set_dash([])

    def label(self, x, v, s, size=13, col='#222'):
        X, Y = self.p(x, v); text(X, Y, s, size, col)


# ------------------------------------------------ plan: x across, z toward the avenue is DOWN the page
text(20, 28, 'PLAN (from above) - A-space metres: +X screen-right from the avenue, +Z toward the avenue (down the page)', 17, '#000')
P = View(40, 60, -3.7, 2.3, up=False)
P.rect(-3.62, 2.45, 7.24, .28, '#c9c3b4'); P.label(.6, 2.62, 'front wall (collider face z 2.70, plaster z 2.73)', 12)
P.rect(-2.45, 2.48, 2.30, .54, '#9aa090')
P.rect(-2.29, 2.50, 1.98, .64, None, '#555', 1, [5, 4])
P.rect(-2.13, 3.14, 1.66, 1.0, '#dfe9d8', '#3a7', 1.2, [3, 3])
P.label(-2.4, 3.30, 'DOOR (service entry): reveal x -2.45..-0.15, threshold to z 3.14', 13)
P.label(-2.4, 3.48, 'door approach zone 1.66 x 1.0 m - no new geometry', 13, '#264')
P.label(-2.4, 3.66, f"nearest new geometry x = {gap['newGeometryLeftMostX']} m: {gap['gapDoorRevealRightToNewLeftMost_m']} m from the reveal, {gap['gapDoorLeafRightToNewLeftMost_m']} m from the leaf", 13, '#264')
for cx in (.9, 1.7, 2.5):
    P.circ(cx, 2.93, .25, '#8b9a94'); P.circ(cx, 2.93, .2557, None, '#4a5a54', 2)
P.rect(.552, 2.90, 2.98, .16, '#d78a4e', '#000', .6)
P.rect(3.10, 2.985, .17, .09, '#d78a4e', '#000', .6)
P.line(-3.7, 3.30, 4.6, 3.30, '#b33', 1.2, [6, 4]); P.label(3.0, 3.26, 'porch walk zone z 3.30', 12, '#b33')
P.label(.6, 3.50, 'new work: front-most z 3.23 (strap / cradle ears), 10 mm beyond the retained collar (3.22)', 13, '#a33')

# ------------------------------------------------ elevation
text(20, 620, 'ELEVATION (from the avenue) - y above the porch top', 17, '#000')
E = View(40, 1480, -3.7, 0.0, up=True)
E.rect(-3.62, 0, 7.24, 3.6, '#eee9dd')
E.rect(-2.13, .04, 1.66, 2.23, '#a9b5b0'); E.label(-1.6, 1.0, 'DOOR leaves', 14)
E.rect(-2.45, 0, 2.30, 2.30, None, '#444', 2.5); E.label(-2.4, 2.4, 'masonry surround', 12)
for i, cx in enumerate((.9, 1.7, 2.5), start=1):
    E.rect(cx - .25, .5, .5, 1.48, '#8b9a94')
    for y in {1: (.78, 1.50), 2: (.83, 1.56), 3: (.80, 1.53)}[i]:
        E.rect(cx - .2557, y - .02, .5114, .04, '#556666', '#000', .6)
    E.rect(cx - .30, .4785, .6, .01, '#000', '#000', .5)
    ly = {1: 1.14, 2: 1.20, 3: 1.17}[i]
    E.rect(cx - .085, ly - .03, .17, .06, '#20304a', '#fff', .6); E.label(cx - .068, ly - .013, f'FILTER {i}', 8, '#fff')
E.rect(.552, 2.09, 2.60, .06, '#d78a4e', '#000', .6)
E.rect(3.14, 2.09, .08, 1.5, '#d78a4e', '#000', .6); E.label(3.3, 3.45, 'riser continues to roof (y 7.08)', 12)
E.rect(2.607, 2.06, .286, .12, '#cc6666', '#000', .8); E.label(2.30, 2.40, 'isolation valve (lever y 2.12)', 12)
E.circ(2.945, 2.262, .0365, '#f3e9c8', '#000', 1); E.label(2.99, 2.34, 'gauge', 12)
E.rect(2.795, 1.875, .09, .06, '#20304a', '#fff', .6); E.label(2.60, 1.75, 'ISOLATE plate', 12)
E.rect(4.75, 0, .45, 1.8, '#dddddd'); E.label(4.55, 1.92, '1.8 m marker', 12)
E.line(-3.7, 1.6, 5.3, 1.6, '#3377aa', 1, [5, 4]); E.label(-3.6, 1.66, 'eye 1.6 m', 12, '#37a')
E.line(-3.7, 2.2, 5.3, 2.2, '#b33', 1, [2, 3]); E.label(-3.6, 2.26, 'standing overhead reach ~2.2 m', 12, '#b33')
text(20, H - 20, f"New work is source geometry only (not a Unity collision test).  Retained vessel silhouettes and placement are unchanged; nothing is added left of x = 0.55 (rev 04 manifold start).", 13, '#222')
surf.write_to_png(str(OUT / 'renders' / 'clearance-diagram.png'))
print('DIAGRAM_OK')
