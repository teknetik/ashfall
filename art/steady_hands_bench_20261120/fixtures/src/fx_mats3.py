# fx_mats3.py: authoring materials of the Milestone 3 fixtures (press, moulds, tray, bin, jar, tester, cure lamp,
# schematic, holster). Kit mats.make plus layers from mbk.Tap, object-space coordinates in metres.
# Albedo judged at the calibrated exposure (white card 0.9 scene-linear), like fx_mats.py.
import os
import bpy
from mbk import MT, Tap, MM
from fx_mats import DIRT, DUST, OIL, IRON, voronoi_dimples, PRESS_YELLOW_LINEAR

GEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gen')
RUST = (0.36, 0.19, 0.10)


def cast(name, base, rust_amt=0.3, edge_amt=1.0, rough=0.5):
    return MT.make(name, base, 0.0, rough, var=0.10, edge=(IRON, 1.0, 0.44, edge_amt), dirt=DIRT, rust=(RUST, rust_amt),
                   bumps=[('stipple', 520, 0.55), ('noise', 240, 0.8), ('noise', 1100, 0.25)], edge_width=0.0014, grime=0.45,
                   tone2=((base[0] * 0.55, base[1] * 0.55, base[2] * 0.55), 28, 0.5, 0.74, 0.55), bump_dist=0.0002)


def chips(t, amount=1.0, scale=38):
    """Paint knocked off in sharp-edged flakes: bare iron inside, a rust-brown lip."""
    n = t.b.math('ADD', t.noise(scale, 5, 0.62), t.b.math('MULTIPLY', t.noise(scale * 4.5, 4, 0.6), 0.22))
    lip = t.b.ramp(n, 0.672 - 0.03 * amount, 0.685 - 0.03 * amount)
    core = t.b.ramp(n, 0.689 - 0.03 * amount, 0.699 - 0.03 * amount)
    t.layer(lip, col=(0.27, 0.14, 0.075), rough=0.85, metal=0.0, height=-0.6)
    t.layer(core, col=(0.50, 0.48, 0.455), rough=0.42, metal=1.0, height=-0.4)
    return core


def library3(M, press=None):
    """press: dict of numbers from the press builder (sight tube, band, hopper line) for the painted marks."""
    press = press or {}
    # ------------------------------------------------------------------ press: worn industrial yellow casting
    YEL = MT.from_linear(PRESS_YELLOW_LINEAR)
    m = cast('press_yellow', YEL, 0.28, rough=0.55)
    t = Tap(m)
    chips(t, 0.35, 52)
    x, y, z = t.xyz()
    # black and yellow hazard stripes round the sides of the base plate
    side = t.b.math('SUBTRACT', 1.0, t.facing(2, 0.5, 0.8))
    base = t.b.math('MULTIPLY', t.band(2, 0.003, 0.021, 0.0004), side)
    f = t.b.math('FRACT', t.b.math('DIVIDE', t.b.math('ADD', t.b.math('ADD', x, y), z), 0.030))
    blk = t.b.math('SUBTRACT', 1.0, t.b.ramp(f, 0.48, 0.52))
    keep = t.b.ramp(t.b.math('ADD', t.noise(70, 5, 0.7), t.b.math('MULTIPLY', t.noise(400, 3), 0.3)), 0.40, 0.55)
    t.layer(t.b.math('MULTIPLY', t.b.math('MULTIPLY', base, blk), keep), col=(0.035, 0.034, 0.032), rough=0.6)
    # the green band painted beside the sight tube (the pressure to hold)
    if 'band' in press:
        bx0, bx1, bz0, bz1, by = press['band']
        bm = t.b.math('MULTIPLY', t.b.math('MULTIPLY', t.band(0, bx0, bx1, 0.0003), t.band(2, bz0, bz1, 0.0003)), t.facing(1, 0.6, 0.9, -1.0))
        bm = t.b.math('MULTIPLY', bm, t.b.math('SUBTRACT', 1.0, t.b.math('MULTIPLY', t.b.ramp(t.noise(180, 4), 0.62, 0.7), 0.8)))
        t.layer(bm, col=(0.13, 0.40, 0.16), rough=0.55, metal=0.0)
    # hands: the yellow is worn through round the lever boss and the lock
    M['press_yellow'] = m
    M['press_steel'] = MT.make('press_steel', (0.58, 0.57, 0.55), 1.0, 0.28, var=0.05, edge=((0.82, 0.81, 0.79), 1.0, 0.16, 0.8), dirt=OIL,
                               bumps=[('brushed', (1, 1, 30), 0.25), ('noise', 900, 0.15)], grime=0.55,
                               tone2=((0.30, 0.255, 0.20), 35, 0.52, 0.72, 0.5))
    M['press_dark'] = MT.make('press_dark', (0.26, 0.255, 0.245), 1.0, 0.36, var=0.08, edge=((0.70, 0.69, 0.66), 1.0, 0.2, 1.0), dirt=OIL,
                              bumps=[('noise', 700, 0.3)], grime=0.6)
    M['vent_glow'] = MT.make('vent_glow', (0.35, 0.80, 0.90), 0.0, 0.2, var=0.04, emit=((0.10, 0.85, 1.0), 6.0, 'all'))
    m = MT.make('hopper_steel', (0.50, 0.495, 0.48), 1.0, 0.36, var=0.07, edge=((0.80, 0.79, 0.76), 1.0, 0.2, 1.0), dirt=DIRT,
                bumps=[('lathe', 'Z', 700, 0.12), ('noise', 600, 0.2)], grime=0.6)
    if 'line' in press:
        t = Tap(m)
        zl = press['line']
        ln = t.b.math('MULTIPLY', t.band(2, zl - 0.0011, zl + 0.0011, 0.0002), t.b.ramp(t.noise(300, 3), 0.25, 0.4))
        t.layer(ln, col=(0.82, 0.78, 0.66), rough=0.7, metal=0.0)
    M['hopper_steel'] = m
    # ------------------------------------------------------------------ moulds: tool steel, the cavity polished
    m = MT.make('mould_steel', (0.43, 0.425, 0.41), 1.0, 0.40, var=0.07, edge=((0.78, 0.77, 0.74), 1.0, 0.22, 1.0), dirt=DIRT,
                rust=(RUST, 0.18, 0.8, 30), bumps=[('noise', 600, 0.35), ('brushed', (30, 1, 1), 0.15)], grime=0.55,
                tone2=((0.27, 0.25, 0.23), 25, 0.5, 0.72, 0.5))
    t = Tap(m)
    # heat tint round the cavity (straw to blue) and grey nanite residue in its corners
    x, y, z = t.xyz()
    top = t.b.math('MULTIPLY', t.facing(2, 0.6, 0.9), t.b.ramp(z, press.get('parting', 0.034) - 0.001, press.get('parting', 0.034) - 0.0002))
    tint = t.b.math('MULTIPLY', t.b.math('MULTIPLY', top, t.b.ramp(t.noise(25, 3), 0.45, 0.65)), 0.55)
    t.layer(t.b.math('MULTIPLY', tint, 0.45), col=(0.50, 0.45, 0.38))
    M['mould_steel'] = m
    M['mould_steel_tang'] = MT.make('mould_steel_tang', (0.43, 0.425, 0.41), 1.0, 0.40, var=0.07, edge=((0.78, 0.77, 0.74), 1.0, 0.22, 1.0), dirt=DIRT,
                                    rust=(RUST, 0.15, 0.8, 30), bumps=[('noise', 600, 0.35), ('brushed', (30, 1, 1), 0.15)], grime=0.55,
                                    tone2=((0.27, 0.25, 0.23), 25, 0.5, 0.72, 0.5),
                                    wipe=('dust', (0.30, 0.30, 0.31), 0.95, 0.95, 80))      # grey nanite dust and scale from the last pour
    M['nanite_paste'] = MT.make('nanite_paste', (0.21, 0.215, 0.22), 0.55, 0.30, var=0.12, dirt=((0.08, 0.085, 0.09), 0.5, 0.6),
                                bumps=[('noise', 260, 0.9), ('noise', 1400, 0.4)], tone2=((0.32, 0.34, 0.35), 40, 0.5, 0.7, 0.4), bevel_r=0.0)
    # ------------------------------------------------------------------ tray, bin
    m = MT.make('tray_enamel', (0.43, 0.48, 0.43), 0.0, 0.45, var=0.08, edge=((0.30, 0.29, 0.27), 1.0, 0.5, 1.0), edge_width=0.0012,
                dirt=DIRT, rust=(RUST, 0.25, 0.8, 30), bumps=[('noise', 300, 0.3)], grime=0.5,
                flake=((0.28, 0.27, 0.255), 1.0, 0.55, 0.12, 60), tone2=((0.33, 0.37, 0.33), 14, 0.48, 0.72, 0.5))
    M['tray_enamel'] = m
    M['bin_paint'] = MT.make('bin_paint', (0.27, 0.34, 0.36), 0.0, 0.62, var=0.1, edge=((0.32, 0.30, 0.28), 1.0, 0.5, 1.0), dirt=DIRT,
                             rust=(RUST, 0.45, 0.6, 25), bumps=[('noise', 200, 0.5), ('noise', 900, 0.2)], grime=0.5,
                             flake=((0.30, 0.20, 0.12), 0.4, 0.8, 0.40, 22), tone2=((0.40, 0.44, 0.43), 10, 0.45, 0.7, 0.5))
    M['bin_rust'] = MT.make('bin_rust', (0.25, 0.16, 0.10), 0.3, 0.8, var=0.15, dirt=((0.08, 0.06, 0.045), 0.9, 0.8), rust=(RUST, 0.5),
                            bumps=[('noise', 300, 0.8), ('stipple', 900, 0.4)], grime=0.8, tone2=((0.15, 0.11, 0.08), 20, 0.45, 0.7, 0.6))
    # ------------------------------------------------------------------ jar
    M['solvent'] = MT.make('solvent', (0.47, 0.49, 0.46), 0.0, 0.08, var=0.08, bumps=[('noise', 60, 0.05)], tone2=((0.36, 0.38, 0.35), 8, 0.4, 0.7, 0.6), bevel_r=0.0)
    M['seal_rubber'] = MT.make('seal_rubber', (0.62, 0.27, 0.12), 0.0, 0.62, var=0.1, dirt=DIRT, bumps=[('noise', 800, 0.3)])
    # ------------------------------------------------------------------ tester
    m = MT.make('tester_paint', (0.30, 0.31, 0.29), 0.2, 0.55, var=0.08, edge=((0.55, 0.53, 0.50), 1.0, 0.35, 1.0), dirt=DIRT,
                rust=(RUST, 0.25, 0.8, 30), bumps=[('stipple', 700, 0.6), ('noise', 250, 0.4)], grime=0.5, edge_width=0.0012,
                tone2=((0.22, 0.23, 0.21), 18, 0.45, 0.7, 0.5))
    t = Tap(m)
    chips(t, 0.25, 60)
    M['tester_paint'] = m
    M['bakelite'] = MT.make('bakelite', (0.05, 0.045, 0.04), 0.0, 0.35, var=0.06, edge=((0.16, 0.13, 0.10), 0.0, 0.5, 0.6), dirt=DUST, bumps=[('noise', 900, 0.2)])
    M['tester_lens'] = MT.make('tester_lens', (0.80, 0.42, 0.10), 0.0, 0.12, var=0.05, emit=((1.0, 0.55, 0.12), 6.0, 'all'))
    M['probe_wood'] = MT.make('probe_wood', (0.40, 0.235, 0.125), 0.0, 0.5, var=0.12, edge=((0.55, 0.36, 0.22), 0.0, 0.6, 0.8),
                              dirt=((0.10, 0.07, 0.05), 0.6, 0.7), bumps=[('grain', (8, 8, 0.7), 60, 0.6, (0.17, 0.09, 0.05), 0.55)],
                              tone2=((0.18, 0.10, 0.06), 20, 0.5, 0.7, 0.6))
    M['brass'] = MT.make('brass_fx', (0.70, 0.55, 0.30), 1.0, 0.36, var=0.1, edge=((0.90, 0.76, 0.50), 1.0, 0.2, 1.0),
                         dirt=((0.14, 0.11, 0.07), 0.7, 0.9), tone2=((0.30, 0.34, 0.24), 40, 0.55, 0.72, 0.5))
    M['needle'] = MT.make('needle', (0.70, 0.69, 0.67), 1.0, 0.22, var=0.04, dirt=DIRT, bevel_r=0.0)
    # ------------------------------------------------------------------ cure lamp
    m = MT.make('lamp_paint', (0.20, 0.205, 0.20), 0.35, 0.45, var=0.08, edge=((0.60, 0.59, 0.56), 1.0, 0.3, 1.0), dirt=DIRT,
                rust=(RUST, 0.2, 0.8, 30), bumps=[('stipple', 600, 0.7), ('noise', 300, 0.3)], grime=0.5, edge_width=0.0012,
                tone2=((0.13, 0.13, 0.13), 20, 0.45, 0.7, 0.5))
    t = Tap(m)
    chips(t, 0.25, 55)
    M['lamp_paint'] = m
    M['lamp_emitter'] = MT.make('lamp_emitter', (0.62, 0.66, 0.95), 0.0, 0.15, var=0.04, emit=((0.42, 0.55, 1.0), 6.0, 'all'))
    # ------------------------------------------------------------------ schematic: paper with the drawing, wax pencil
    m = MT.make('paper', (0.80, 0.765, 0.67), 0.0, 0.85, var=0.06, edge=((0.62, 0.56, 0.44), 0.0, 0.9, 0.7), edge_width=0.0012,
                dirt=((0.42, 0.36, 0.26), 0.9, 0.4), bumps=[('noise', 1500, 0.15)], tone2=((0.70, 0.63, 0.50), 9, 0.46, 0.72, 0.55), bevel_r=0.0)
    img = os.path.join(GEN, 'schematic.png')
    if os.path.exists(img):
        t = Tap(m)
        im = t.image(img, (-0.125, -0.300), (0.250, 0.300), axes=(0, 1))
        ink = t.b.math('SUBTRACT', 1.0, t.chan(im, 0))
        t.layer(t.b.math('MULTIPLY', ink, t.facing(2, 0.5, 0.8)), col=(0.10, 0.10, 0.12), rough=0.75)
    M['paper'] = m
    M['wax_pencil'] = MT.make('wax_pencil', (0.55, 0.10, 0.07), 0.0, 0.6, var=0.1, bumps=[('noise', 2000, 0.4)], bevel_r=0.0)
    # ------------------------------------------------------------------ holster
    M['holster_leather'] = MT.make('holster_leather', (0.26, 0.145, 0.08), 0.0, 0.55, var=0.15, edge=((0.48, 0.31, 0.19), 0.0, 0.75, 1.0),
                                   edge_width=0.0015, dirt=((0.08, 0.055, 0.04), 0.5, 0.8), bumps=[('pores', 1300, 0.5), ('noise', 120, 0.8)],
                                   tone2=((0.13, 0.075, 0.045), 22, 0.42, 0.68, 0.8))
    return M
