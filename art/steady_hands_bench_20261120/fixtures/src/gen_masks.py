#!/usr/bin/env python3
"""Mask images for the fixture materials, drawn with ImageMagick (no Blender needed, seconds):
  gen/rule_marks.png      900 x 26 mm at 16 px/mm. R: engraved millimetre marks and centimetre numerals,
                          G: the lead-length notch (120 mm from zero), B: the two screw seats.
  gen/rubber_wear.png     900 x 550 mm at 4 px/mm. R: knife cuts, G: soldering burns, B: stains and rings.
  gen/partsmat.png        440 x 200 mm at 8 px/mm. R: painted outlines (PLACEHOLDER shapes until the pistol and servo
                          families export; then gen_outlines.py replaces this file), G: wear that rubs the paint away.
  gen/hazard.png          the insulated pad's border.
Usage: python3 gen_masks.py [rule] [wear] [partsmat]   (default all). Layout numbers come from here: the build reads
gen/masks.json for the same sizes."""
import os, sys, json, math, random, subprocess

H = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(H, 'gen'); os.makedirs(OUT, exist_ok=True)
FONT = '/usr/share/fonts/liberation/LiberationSans-Bold.ttf'
FONTN = '/usr/share/fonts/liberation/LiberationSansNarrow-Bold.ttf'
if not os.path.exists(FONTN):
    FONTN = FONT
INFO = {}


def magick(size, bg, mvg, out, post=()):
    f = os.path.join(OUT, '_draw.mvg')
    open(f, 'w').write('\n'.join(mvg))
    r = subprocess.run(['magick', '-size', '%dx%d' % size, 'xc:' + bg, '-draw', '@' + f, *post, '-depth', '8', out], capture_output=True, text=True)
    if r.returncode:
        print(r.stderr[:800]); sys.exit(1)
    os.remove(f)
    print('wrote', out)


def rule():
    PX = 16; L, Wd = 900, 26
    ZERO, LAST, LEAD = 10, 880, 120          # mm from the left end: zero mark, last mark; lead length from zero
    W, Hh = L * PX, Wd * PX
    d = ["fill '#ff0000' stroke none"]
    for mm in range(0, LAST - ZERO + 1):
        x = (ZERO + mm) * PX
        ln, wd = (8.0, 0.30) if mm % 10 == 0 else ((5.5, 0.24) if mm % 5 == 0 else (3.2, 0.20))
        d.append('rectangle %.1f,0 %.1f,%.1f' % (x - wd * PX / 2, x + wd * PX / 2, ln * PX))
    d.append("font '%s' font-size %d text-anchor middle" % (FONT, int(4.4 * PX)))
    for cm in range(0, (LAST - ZERO) // 10 + 1):
        x = (ZERO + cm * 10) * PX
        d.append("text %.1f,%.1f '%d'" % (x, 13.4 * PX, cm))
    # lead-length notch: a file-cut V at the far edge and a short filled bar under it (green channel)
    xl = (ZERO + LEAD) * PX
    d.append("fill '#00ff00'")
    d.append('polygon %.1f,0 %.1f,0 %.1f,%.1f' % (xl - 1.3 * PX, xl + 1.3 * PX, xl, 4.2 * PX))
    d.append('rectangle %.1f,%.1f %.1f,%.1f' % (xl - 0.5 * PX, 15.0 * PX, xl + 0.5 * PX, 22.5 * PX))
    # a second, older scratched mark at zero so the pair reads as "from here to here"
    x0 = ZERO * PX
    d.append('rectangle %.1f,%.1f %.1f,%.1f' % (x0 - 0.3 * PX, 15.0 * PX, x0 + 0.3 * PX, 22.5 * PX))
    d.append("fill '#0000ff'")
    for sx in (40, 450, 860):
        d.append('circle %.1f,%.1f %.1f,%.1f' % (sx * PX, 20.0 * PX, sx * PX + 3.4 * PX, 20.0 * PX))
    magick((W, Hh), 'black', d, os.path.join(OUT, 'rule_marks.png'))
    INFO['rule'] = {'px_per_mm': PX, 'length_mm': L, 'width_mm': Wd, 'zero_mm': ZERO, 'last_mm': LAST, 'lead_mm': LEAD,
                    'screws_mm': [40, 450, 860], 'screw_y_from_far_edge_mm': 20.0,
                    'note': 'image top = the far edge of the rule (toward the work), left = the bench left end'}


def wear():
    PX = 4; Wm, Hm = 900, 550
    W, Hh = Wm * PX, Hm * PX
    rnd = random.Random(20261120)
    d = []
    # R: knife cuts. Clusters where work happens: in front of the work mat and round the vise; a few long strays.
    d.append("fill none stroke '#ff0000' stroke-linecap round")
    clusters = [(480, 95, 150, 55, 70), (140, 250, 70, 110, 45), (760, 150, 60, 90, 30), (450, 500, 300, 30, 26), (300, 420, 80, 50, 18)]
    for cx, cy, sx, sy, n in clusters:
        ang0 = rnd.uniform(0, math.pi)
        for _ in range(n):
            x = rnd.gauss(cx, sx); y = rnd.gauss(cy, sy)
            a = ang0 + rnd.gauss(0, 0.5) if rnd.random() < 0.7 else rnd.uniform(0, math.pi)
            ln = abs(rnd.gauss(26, 22)) + 6
            wd = rnd.choice((0.8, 1.0, 1.0, 1.3, 1.8))
            op = rnd.uniform(0.35, 1.0)
            x1, y1 = x + math.cos(a) * ln / 2, y + math.sin(a) * ln / 2
            x0, y0 = x - math.cos(a) * ln / 2, y - math.sin(a) * ln / 2
            # a slight curve: two segments
            mx, my = (x0 + x1) / 2 + rnd.gauss(0, ln * 0.03), (y0 + y1) / 2 + rnd.gauss(0, ln * 0.03)
            d.append("stroke-opacity %.2f stroke-width %.1f path 'M %.1f,%.1f Q %.1f,%.1f %.1f,%.1f'" %
                     (op, wd, x0 * PX, (Hm - y0) * PX, mx * PX, (Hm - my) * PX, x1 * PX, (Hm - y1) * PX))
    for _ in range(14):
        x = rnd.uniform(60, 840); y = rnd.uniform(40, 500); a = rnd.uniform(0, math.pi); ln = rnd.uniform(90, 260)
        d.append("stroke-opacity %.2f stroke-width 1.0 line %.1f,%.1f %.1f,%.1f" %
                 (rnd.uniform(0.25, 0.6), (x - math.cos(a) * ln / 2) * PX, (Hm - y + math.sin(a) * ln / 2) * PX,
                  (x + math.cos(a) * ln / 2) * PX, (Hm - y - math.sin(a) * ln / 2) * PX))
    # G: soldering burns, right of centre behind the work mat, and a few strays
    d.append("stroke none stroke-opacity 1")
    burns = []
    for _ in range(26):
        x = rnd.gauss(690, 55); y = rnd.gauss(430, 45); r = abs(rnd.gauss(2.2, 1.2)) + 0.8
        burns.append((x, y, r))
    for _ in range(8):
        burns.append((rnd.uniform(80, 820), rnd.uniform(60, 500), abs(rnd.gauss(1.6, 0.8)) + 0.7))
    for x, y, r in burns:
        d.append("fill '#00ff00' fill-opacity %.2f circle %.1f,%.1f %.1f,%.1f" % (rnd.uniform(0.6, 1.0), x * PX, (Hm - y) * PX, (x + r) * PX, (Hm - y) * PX))
    # a dragged burn (the iron laid down)
    d.append("fill none stroke '#00ff00' stroke-opacity 0.9 stroke-width %.1f stroke-linecap round line %.1f,%.1f %.1f,%.1f" %
             (3.2 * PX, 742 * PX, (Hm - 468) * PX, 771 * PX, (Hm - 480) * PX))
    # B: stains. A ring where a jar stood, a spill, blotches.
    d.append("stroke none")
    for cx, cy, r, w, op in ((120, 470, 46, 5, 0.8), (128, 462, 46, 3, 0.45), (800, 300, 31, 3.5, 0.6)):
        d.append("fill none stroke '#0000ff' stroke-opacity %.2f stroke-width %.1f circle %.1f,%.1f %.1f,%.1f" %
                 (op, w * PX, cx * PX, (Hm - cy) * PX, (cx + r) * PX, (Hm - cy) * PX))
    d.append("stroke none")
    for _ in range(40):
        x = rnd.uniform(30, 870); y = rnd.uniform(30, 520); r = abs(rnd.gauss(14, 12)) + 4
        d.append("fill '#0000ff' fill-opacity %.2f ellipse %.1f,%.1f %.1f,%.1f 0,360" %
                 (rnd.uniform(0.08, 0.35), x * PX, (Hm - y) * PX, r * PX, r * rnd.uniform(0.5, 1.0) * PX))
    for x, y, rx, ry, op in ((330, 250, 70, 45, 0.5), (300, 262, 40, 60, 0.35), (600, 80, 90, 30, 0.3)):
        d.append("fill '#0000ff' fill-opacity %.2f ellipse %.1f,%.1f %.1f,%.1f 0,360" % (op, x * PX, (Hm - y) * PX, rx * PX, ry * PX))
    out = os.path.join(OUT, 'rubber_wear.png')
    magick((W, Hh), 'black', d, out)
    # soften the stains and the burns a little, keep the cuts sharp
    r = subprocess.run(['magick', out, '-channel', 'B', '-blur', '0x%d' % (5 * PX), '-channel', 'G', '-blur', '0x1.2', '+channel', '-depth', '8', out],
                       capture_output=True, text=True)
    if r.returncode:
        print(r.stderr[:600]); sys.exit(1)
    INFO['wear'] = {'px_per_mm': PX, 'size_mm': [Wm, Hm], 'note': 'image covers the whole slab; left-bottom = the slab corner at the bench left, player side'}


def rrect(x0, y0, x1, y1, r, PX, Hm):
    return 'roundrectangle %.1f,%.1f %.1f,%.1f %.1f,%.1f' % (x0 * PX, (Hm - y1) * PX, x1 * PX, (Hm - y0) * PX, r * PX, r * PX)


def partsmat():
    """PLACEHOLDER outlines. Positions (mm, from the mat's left-front corner) are also written to masks.json as the
    seat marks, so the build and the picture agree."""
    PX = 8; Wm, Hm = 440, 200
    d = ["fill none stroke '#ff0000' stroke-width %.1f stroke-linejoin round" % (1.1 * PX)]
    seats = {}
    def C(x, y):
        return x * PX, (Hm - y) * PX

    def circ(name, x, y, r, inner=None):
        d.append('circle %.1f,%.1f %.1f,%.1f' % (*C(x, y), (x + r) * PX, (Hm - y) * PX))
        if inner:
            d.append('circle %.1f,%.1f %.1f,%.1f' % (*C(x, y), (x + inner) * PX, (Hm - y) * PX))
        seats[name] = [x, y, 0]

    def rect(name, x, y, w, h, r=3, yaw=0):
        d.append(rrect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, r, PX, Hm))
        seats[name] = [x, y, yaw]

    def blob(name, x, y, pts):
        s = ' '.join('%.1f,%.1f' % C(x + px, y + py) for px, py in pts)
        d.append('polygon ' + s)
        seats[name] = [x, y, 0]
    # pistol, left third: two grip scales, the backstrap housing, tape and wrap (one box), spring, pin, 2 screws
    scale = [(-21, -46), (17, -48), (22, -20), (20, 20), (12, 46), (-14, 48), (-22, 22), (-19, -18)]
    blob('pistol.scale_l', 34, 132, scale); blob('pistol.scale_r', 88, 132, [(-px, py) for px, py in scale])
    blob('pistol.housing', 140, 136, [(-14, -44), (12, -44), (16, -30), (16, 40), (4, 46), (-14, 40)])
    rect('pistol.wrap', 60, 40, 96, 40, 6)
    rect('pistol.spring', 150, 62, 9, 44, 4)
    rect('pistol.pin', 168, 62, 5, 40, 2)
    circ('pistol.screw_grip_a', 150, 24, 4.2); circ('pistol.screw_grip_b', 166, 24, 4.2)
    # servo, right two thirds: case top, board, three gears, circlip, gimbal, rotor, four case screws, two trunnion screws
    rect('servo.case_top', 236, 140, 86, 62, 8)
    rect('servo.board', 232, 54, 58, 40, 3)
    circ('servo.gear_a', 312, 150, 17, 4); circ('servo.gear_b', 348, 152, 12, 3.5); circ('servo.gear_c', 376, 152, 9, 3)
    circ('servo.circlip', 404, 152, 6, 3.6)
    circ('servo.gimbal', 316, 86, 26, 19)
    circ('servo.rotor', 372, 84, 15, 4)
    for i, x in enumerate((296, 314, 332, 350)):
        circ('servo.screw_case_%d' % (i + 1), x, 30, 3.6)
    circ('servo.screw_trunnion_a', 380, 30, 3.2); circ('servo.screw_trunnion_b', 396, 30, 3.2)
    rect('servo.resistor', 414, 86, 22, 8, 3)
    rect('servo.bobbin', 414, 116, 24, 20, 3)
    # divider and a border
    d.append("stroke-width %.1f" % (0.8 * PX))
    d.append('line %.1f,%.1f %.1f,%.1f' % (*C(186, 12), *C(186, 188)))
    d.append(rrect(5, 5, Wm - 5, Hm - 5, 6, PX, Hm))
    out = os.path.join(OUT, 'partsmat.png')
    # G: wear, heavier in the middle of each outline where a part is put down again and again (blurred copies) + scuffs
    rnd = random.Random(7)
    g = ["stroke none"]
    for name, (x, y, _) in seats.items():
        g.append("fill '#00ff00' fill-opacity %.2f circle %.1f,%.1f %.1f,%.1f" % (rnd.uniform(0.35, 0.8), *C(x, y), (x + rnd.uniform(9, 20)) * PX, (Hm - y) * PX))
    for _ in range(60):
        x = rnd.uniform(0, Wm); y = rnd.uniform(0, Hm); a = rnd.uniform(-0.5, 0.5); ln = rnd.uniform(10, 70)
        g.append("fill none stroke '#00ff00' stroke-opacity %.2f stroke-width %.1f line %.1f,%.1f %.1f,%.1f" %
                 (rnd.uniform(0.2, 0.7), rnd.uniform(1.5, 5) * PX, *C(x, y), *C(x + math.cos(a) * ln, y + math.sin(a) * ln)))
    magick((Wm * PX, Hm * PX), 'black', d, out)
    tmp = os.path.join(OUT, '_wear.png')
    magick((Wm * PX, Hm * PX), 'black', g, tmp, post=('-blur', '0x%d' % (2 * PX)))
    r = subprocess.run(['magick', out, tmp, '-compose', 'Plus', '-composite', '-depth', '8', out], capture_output=True, text=True)
    if r.returncode:
        print(r.stderr[:600]); sys.exit(1)
    os.remove(tmp)
    INFO['partsmat'] = {'px_per_mm': PX, 'size_mm': [Wm, Hm], 'placeholder': True,
                        'seats_mm_from_left_front': seats}


def hazard():
    PX = 8; Wm, Hm = 130, 104
    d = ["fill '#ffffff' stroke none"]
    # diagonal stripes in a 13 mm border; R = stripe, G = border band
    step = 14
    for i in range(-20, 30):
        x = i * step
        d.append('polygon %.1f,%.1f %.1f,%.1f %.1f,%.1f %.1f,%.1f' % (x * PX, Hm * PX, (x + step / 2) * PX, Hm * PX, (x + step / 2 + Hm) * PX, 0, (x + Hm) * PX, 0))
    out = os.path.join(OUT, 'hazard.png')
    magick((Wm * PX, Hm * PX), 'black', d, out)
    INFO['hazard'] = {'px_per_mm': PX, 'size_mm': [Wm, Hm]}


which = set(sys.argv[1:]) or {'rule', 'wear', 'partsmat', 'hazard'}
old = {}
mj = os.path.join(OUT, 'masks.json')
if os.path.exists(mj):
    old = json.load(open(mj))
for k, fn in (('rule', rule), ('wear', wear), ('partsmat', partsmat), ('hazard', hazard)):
    if k in which:
        fn()
old.update(INFO)
json.dump(old, open(mj, 'w'), indent=1)
