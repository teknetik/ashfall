# tl_mats2.py: model-tools materials (21 Nov 2026), for the new tools and the rebuild. Different steels, not one grey:
# forged black-oxide steel, bright ground steel, blued steel, nickel plate, cast iron, file steel; turned dark wood
# with scribed rings, pale beech, cork, cloth tape, red dip. Every factory returns a NEW material (tools are tilted to
# their rest one by one and their materials are framed to the modelling axes with tl_kit.frame_mat).
import math
from mbk import MT, Tap, MM

DIRT = ((0.115, 0.105, 0.095), 0.85, 0.75)
GRIME = ((0.11, 0.09, 0.07), 0.8, 0.9)
OIL = ((0.07, 0.055, 0.04), 0.4, 0.8)
DUST = ((0.46, 0.39, 0.30), 0.9, 0.5)


def _oxide(m, amount=0.55, col=(0.135, 0.125, 0.118), scale=40, pit=0.45):
    """Dark brown-black oxide in broad patches and fine pitting (not orange: orange rust only in the deepest pits)."""
    t = Tap(m)
    ox = t.b.ramp(t.b.math('ADD', t.noise(scale, 5, 0.7), t.b.math('MULTIPLY', t.noise(scale * 7, 3, 0.6), 0.25)), 0.55, 0.74)
    t.layer(t.b.math('MULTIPLY', ox, amount), col=col, rough=0.72, metal=0.45)
    if pit:
        p = t.b.ramp(t.noise(900, 2, 0.5), 0.70, 0.78)
        t.height(p, -1.4)
        t.layer(t.b.math('MULTIPLY', p, pit), col=(0.20, 0.12, 0.075), rough=0.86, metal=0.2)
    return m


def forged(name, base=(0.42, 0.43, 0.445), rough=0.46, oxide=0.55, rust=0.22, edge=0.9):
    """Forged tool steel kept oiled: dark grey with brown-black oxide in patches, pitted, bright where it works."""
    m = MT.make(name, base, 1.0, rough, var=0.10, edge=((0.76, 0.765, 0.77), 1.0, 0.22, edge), edge_width=0.0010, dirt=DIRT,
                rust=((0.36, 0.20, 0.11), rust, 0.9, 30), bumps=[('noise', 850, 0.28), ('noise', 220, 0.45), ('stipple', 1800, 0.18)], grime=0.45,
                tone2=((0.29, 0.295, 0.305), 60, 0.5, 0.72, 0.45))
    return _oxide(m, oxide) if oxide else m


def bright(name, base=(0.68, 0.685, 0.69), rough=0.24, along=1):
    """Ground and polished by use: jaws, tips, bits, the cut faces."""
    st = [1, 1, 1]; st[along] = 30
    return MT.make(name, base, 1.0, rough, var=0.06, edge=((0.86, 0.85, 0.83), 1.0, 0.14, 0.8), dirt=OIL,
                   bumps=[('noise', 900, 0.2), ('brushed', tuple(st), 0.22)], grime=0.35, tone2=((0.42, 0.42, 0.425), 60, 0.52, 0.72, 0.4))


def blued(name, base=(0.17, 0.185, 0.22), rough=0.34):
    m = MT.make(name, base, 1.0, rough, var=0.07, edge=((0.66, 0.64, 0.60), 1.0, 0.22, 1.0), edge_width=0.0009, dirt=DIRT,
                rust=((0.34, 0.19, 0.10), 0.18, 0.9, 30), bumps=[('noise', 1100, 0.18)], grime=0.4,
                tone2=((0.13, 0.14, 0.16), 50, 0.55, 0.75, 0.35))
    return m


def nickel(name, base=(0.62, 0.62, 0.615), rough=0.30):
    """Nickel plate worn through to brassy undercoat at edges and to dark steel in patches."""
    m = MT.make(name, base, 1.0, rough, var=0.07, edge=((0.62, 0.50, 0.33), 1.0, 0.3, 0.8), edge_width=0.0008, dirt=DIRT,
                rust=((0.30, 0.20, 0.12), 0.15, 0.9, 30), bumps=[('noise', 1200, 0.14)], grime=0.5,
                tone2=((0.40, 0.40, 0.40), 70, 0.55, 0.76, 0.5))
    return m


def cast_iron(name, base=(0.27, 0.275, 0.285), rough=0.62, rust=0.3):
    m = MT.make(name, base, 0.9, rough, var=0.09, edge=((0.62, 0.60, 0.57), 1.0, 0.3, 1.0), edge_width=0.0012, dirt=DIRT,
                rust=((0.34, 0.19, 0.10), rust, 0.9, 25), bumps=[('stipple', 2200, 0.35), ('noise', 500, 0.3)], grime=0.6,
                tone2=((0.19, 0.19, 0.195), 30, 0.5, 0.72, 0.5))
    return _oxide(m, 0.45, (0.14, 0.125, 0.11), 30, 0.35)


def file_steel(name, base=(0.36, 0.365, 0.375), rough=0.55):
    return MT.make(name, base, 1.0, rough, var=0.07, edge=((0.70, 0.69, 0.66), 1.0, 0.3, 0.6), dirt=GRIME,
                   rust=((0.34, 0.20, 0.11), 0.2, 0.9, 30), grime=0.7, tone2=((0.26, 0.265, 0.27), 50, 0.5, 0.75, 0.5))


def file_teeth(m, axes=(1, 0), pitch=0.00075, angle1=65.0, angle2=-45.0, lo=None, hi=None, along=1, strength=1.6):
    """Double-cut teeth on a file's faces: two families of sharp ridges, the overcut finer. Masked to lo..hi along
    `along` (the blade) when given. Filings and grime in the cuts."""
    t = Tap(m)
    x, y, z = t.xyz()
    c = [x, y, z]
    u, v = c[axes[0]], c[axes[1]]

    def ridge(ang, p):
        ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        s = t.b.math('ADD', t.b.math('MULTIPLY', u, ca / p), t.b.math('MULTIPLY', v, sa / p))
        f = t.b.math('FRACT', s)
        return t.b.math('MULTIPLY', t.b.ramp(f, 0.0, 0.8), t.b.math('SUBTRACT', 1.0, t.b.ramp(f, 0.86, 1.0)))
    r1 = ridge(angle1, pitch); r2 = ridge(angle2, pitch * 1.25)
    h = t.b.math('MINIMUM', r1, t.b.math('ADD', r2, 0.25))
    if lo is not None:
        h = t.b.math('MULTIPLY', h, t.band(along, lo, hi, 0.0008))
    t.height(h, strength)
    t.layer(t.b.math('MULTIPLY', t.b.math('SUBTRACT', 1.0, h), 0.5), col=(0.12, 0.11, 0.10), rough=0.8)
    return m


def wood(name, base=(0.36, 0.22, 0.12), dark=(0.13, 0.075, 0.04), axis=1, rough=0.40, polish=0.6, grain=0.65):
    st = [9, 9, 9]; st[axis] = 0.55
    m = MT.make(name, base, 0.0, rough, var=0.13, edge=((base[0] * 1.45, base[1] * 1.4, base[2] * 1.35), 0.0, 0.55, 0.7), edge_width=0.0013,
                dirt=((0.08, 0.06, 0.04), 0.6, 0.85), bumps=[('grain', tuple(st), 75, 0.55, dark, grain), ('noise', 420, 0.2)],
                tone2=((dark[0] * 0.8, dark[1] * 0.8, dark[2] * 0.8), 24, 0.45, 0.7, polish), grime=0.6)
    return m


def rings(m, axis_i, positions, width=0.0007, depth=-1.6, col=(0.07, 0.045, 0.03)):
    """Scribed rings round a turned handle at `positions` along the object axis axis_i."""
    t = Tap(m)
    mask = None
    for p in positions:
        b = t.band(axis_i, p - width / 2, p + width / 2, 0.00015)
        mask = b if mask is None else t.b.math('MAXIMUM', mask, b)
    t.height(mask, depth)
    t.layer(t.b.math('MULTIPLY', mask, 0.8), col=col, rough=0.7)
    return m


def knurl_band(m, origin, axis, lo, hi, n=40, pitch=0.0009, strength=1.4):
    """Diamond knurl in a band lo..hi along an axis, grime packed into the grooves."""
    t = Tap(m)
    kn = t.knurl(origin, axis, n=n, pitch=pitch, strength=strength, lo=lo, hi=hi)
    th, al, rr = t.cyl(origin, axis)
    band = t.b.math('MULTIPLY', t.b.ramp(al, lo - 0.0002, lo + 0.0002), t.b.math('SUBTRACT', 1.0, t.b.ramp(al, hi - 0.0002, hi + 0.0002)))
    groove = t.b.math('MULTIPLY', t.b.math('SUBTRACT', 1.0, t.b.ramp(kn, 0.05, 0.4)), band)
    t.layer(t.b.math('MULTIPLY', groove, 0.7), col=(0.10, 0.09, 0.08), rough=0.8, metal=0.3)
    return m


def cloth_tape(name, origin, axis, lo, hi, pitch=0.0068, base=(0.085, 0.082, 0.078)):
    """Black cloth friction tape wound round a handle: a ridge at each turn, worn grey where the palm and fingers sit,
    oil-shiny in places, frayed at the ends."""
    m = MT.make(name, base, 0.0, 0.82, var=0.12, edge=((0.30, 0.29, 0.27), 0.0, 0.9, 0.9), edge_width=0.0009,
                dirt=((0.20, 0.17, 0.13), 0.9, 0.6), bumps=[('noise', 1600, 0.4)], grime=0.6,
                tone2=((0.20, 0.19, 0.17), 30, 0.5, 0.72, 0.6), bump_dist=0.00025)
    t = Tap(m)
    t.wrap(origin, axis, pitch, lo, hi, col_seam=(0.03, 0.03, 0.03), strength=1.6)
    t.weave(scale=1 / 0.00085, strength=0.35, axes=(0, 1), tone=0.05)
    th_, al_, rr_ = t.cyl(origin, axis)
    worn = t.b.math('MULTIPLY', t.b.ramp(al_, lo + (hi - lo) * 0.15, lo + (hi - lo) * 0.55), t.b.ramp(t.noise(55, 4), 0.45, 0.75))
    t.layer(t.b.math('MULTIPLY', worn, 0.55), col=(0.26, 0.245, 0.22), rough=0.9)
    shine = t.b.ramp(t.noise(30, 3), 0.55, 0.7)
    t.layer(t.b.math('MULTIPLY', shine, 0.5), rough=0.45)
    return m


def red_dip(name):
    m = MT.make(name, (0.50, 0.085, 0.065), 0.0, 0.52, var=0.12, edge=((0.52, 0.50, 0.48), 1.0, 0.36, 1.0), edge_width=0.0016,
                dirt=((0.15, 0.075, 0.06), 0.7, 0.8), bumps=[('noise', 500, 0.4), ('noise', 160, 0.6)], grime=0.6,
                tone2=((0.25, 0.05, 0.045), 35, 0.42, 0.66, 0.85))
    t = Tap(m)
    n = t.noise(70, 5, 0.65)
    t.layer(t.b.ramp(n, 0.64, 0.66), col=(0.50, 0.48, 0.455), rough=0.4, metal=1.0, height=-2.0)
    return m


def brass(name, base=(0.72, 0.57, 0.33), rough=0.38, axis='Y'):
    return MT.make(name, base, 1.0, rough, var=0.10, edge=((0.92, 0.79, 0.53), 1.0, 0.2, 1.0),
                   dirt=((0.18, 0.13, 0.08), 0.7, 0.9), bumps=[('lathe', axis, 1200, 0.15)], tone2=((0.40, 0.33, 0.20), 40, 0.5, 0.72, 0.55))


def copper_tip(name):
    """Copper bit, heat-coloured toward the barrel, the end tinned bright with solder."""
    m = MT.make(name, (0.78, 0.45, 0.29), 1.0, 0.36, var=0.12, edge=((0.95, 0.66, 0.48), 1.0, 0.2, 0.6),
                dirt=((0.12, 0.08, 0.06), 0.7, 0.9), bumps=[('noise', 1500, 0.2)], tone2=((0.30, 0.18, 0.15), 35, 0.45, 0.7, 0.75))
    return m


def cork(name):
    return MT.make(name, (0.58, 0.44, 0.30), 0.0, 0.84, var=0.16, edge=((0.68, 0.56, 0.42), 0.0, 0.9, 0.5), edge_width=0.001,
                   dirt=((0.20, 0.14, 0.09), 0.9, 0.9), bumps=[('pores', 900, 0.6), ('stipple', 2600, 0.4)], grime=0.9,
                   tone2=((0.36, 0.26, 0.17), 30, 0.45, 0.7, 0.7))


def cloth_lead(name):
    return MT.make(name, (0.32, 0.22, 0.13), 0.0, 0.85, var=0.14, dirt=((0.12, 0.09, 0.06), 0.9, 0.8), bumps=[('weave', 3800, 0.6)],
                   grime=0.8, tone2=((0.18, 0.12, 0.07), 40, 0.45, 0.7, 0.6))


def brass_wire(name):
    return MT.make(name, (0.66, 0.52, 0.30), 1.0, 0.36, var=0.14, dirt=((0.20, 0.15, 0.09), 0.7, 0.7), bumps=[('brushed', (30, 1, 30), 0.6)],
                   grime=0.6, tone2=((0.40, 0.30, 0.17), 80, 0.5, 0.72, 0.6), bevel_r=0.0)


def ceramic(name):
    return MT.make(name, (0.80, 0.78, 0.72), 0.0, 0.30, var=0.05, edge=((0.86, 0.85, 0.82), 0.0, 0.3, 0.5), dirt=((0.30, 0.27, 0.22), 0.7, 0.8),
                   bumps=[('noise', 1500, 0.1)], grime=0.6)


def paste(name):
    """Nanite paste behind the applicator's sight window: dark grey and glossy, a faint cyan crawl (the only cyan)."""
    return MT.make(name, (0.21, 0.215, 0.22), 0.5, 0.2, var=0.14, bumps=[('noise', 600, 0.3)], emit=((0.06, 0.40, 0.52), 0.22, 'crystal'),
                   bevel_r=0.0)


def alloy_barrel(name):
    return MT.make(name, (0.56, 0.555, 0.54), 1.0, 0.36, var=0.06, edge=((0.80, 0.79, 0.76), 1.0, 0.2, 0.9), dirt=DIRT,
                   bumps=[('lathe', 'Y', 900, 0.12), ('noise', 1300, 0.12)], grime=0.5, tone2=((0.40, 0.38, 0.35), 50, 0.55, 0.75, 0.45))


def plastic_dark(name, base=(0.11, 0.105, 0.10)):
    return MT.make(name, base, 0.0, 0.48, var=0.08, edge=((0.30, 0.29, 0.28), 0.0, 0.45, 0.6), dirt=DUST, bumps=[('noise', 1400, 0.15)], grime=0.6)


def solder(name):
    return MT.make(name, (0.70, 0.70, 0.68), 1.0, 0.28, var=0.06, dirt=((0.25, 0.23, 0.2), 0.6, 0.5), bumps=[('noise', 1100, 0.2)])
