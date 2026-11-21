# fx_mats.py: authoring materials of the fixtures family (kit mats.make plus layers from mbk.Tap).
# Look target: ../../concept/bench_overview_fal.jpg. All coordinates are the object's own frame, metres.
import os, json, math
import bpy
from mbk import MT, Tap, MM

GEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gen')
MASKS = json.load(open(os.path.join(GEN, 'masks.json')))
# Albedo was re-tuned on 20 Nov 19:40 at a calibrated exposure (white card 0.9 scene-linear, SEAM.md section 8): the
# first set had been judged under a rig 1.6 EV too bright and was one to two stops too dark.
DIRT = ((0.20, 0.155, 0.115), 0.85, 0.75)
DUST = ((0.50, 0.41, 0.31), 0.9, 0.55)
OIL = ((0.07, 0.055, 0.04), 0.35, 0.8)
IRON = (0.54, 0.52, 0.49)
# shared colours, linear albedo (SEAM.md section 8): other families take these from here
VISE_GREEN_LINEAR = (0.020, 0.036, 0.018)
PRESS_YELLOW_LINEAR = (0.36, 0.21, 0.040)        # planned for fixtures.press (Milestone 3)


def voronoi_dimples(t, scale, lo=0.0, hi=0.45):
    v = t.b.n('ShaderNodeTexVoronoi', feature='F1')
    v.inputs['Scale'].default_value = scale
    t.b.l(t.P, v.inputs['Vector'])
    return t.b.ramp(v.outputs['Distance'], lo, hi)


def library(M):
    # ------------------------------------------------------------------ work surface
    HX, HY = 0.45, 0.275
    m = MT.make('ws_rubber', (0.17, 0.166, 0.160), 0.0, 0.78, var=0.10, edge=((0.28, 0.27, 0.26), 0.0, 0.72, 0.5),
                dirt=((0.38, 0.32, 0.24), 0.9, 0.3), bumps=[('stipple', 1100, 0.22), ('noise', 260, 0.35)], grime=0.15,
                tone2=((0.25, 0.235, 0.215), 9, 0.50, 0.76, 0.40), edge_width=0.001)
    t = Tap(m)
    wear = t.image(os.path.join(GEN, 'rubber_wear.png'), (-HX, -HY), (2 * HX, 2 * HY))
    cuts, burns, stains = t.chan(wear, 0), t.chan(wear, 1), t.chan(wear, 2)
    # stains: where solvent stood the rubber is paler and drier; the big blotch under the vise is oil, dark and glossy
    oilm = t.b.math('MULTIPLY', stains, t.b.math('SUBTRACT', 1.0, t.b.ramp(t.xyz()[0], -0.20, -0.05)), clamp=True)
    solm = t.b.math('MULTIPLY', stains, t.b.ramp(t.xyz()[0], -0.20, -0.05), clamp=True)
    t.layer(t.b.math('MULTIPLY', solm, 0.6), col=(0.31, 0.295, 0.265), rough=0.92)
    t.layer(t.b.math('MULTIPLY', oilm, 0.9), col=(0.09, 0.083, 0.075), rough=0.42)
    # polished track where hands and work slide: in front of the work mat
    pol = t.b.math('MULTIPLY', t.b.math('MULTIPLY', t.band(1, -0.26, -0.03, 0.05), t.band(0, -0.28, 0.33, 0.08)), t.b.ramp(t.noise(14, 4), 0.35, 0.7))
    t.layer(t.b.math('MULTIPLY', pol, 0.55), col=(0.13, 0.127, 0.122), rough=0.50)
    # knife cuts: a groove with pale dusty lips
    t.height(cuts, -3.0)
    t.layer(t.b.math('MULTIPLY', cuts, 0.8), col=(0.40, 0.375, 0.335), rough=0.93)
    # burns: a crater, grey ash colour, raised glossy rim from the blurred edge
    core = t.b.ramp(burns, 0.55, 0.9); rim = t.b.math('MULTIPLY', t.b.ramp(burns, 0.08, 0.5), t.b.math('SUBTRACT', 1.0, core))
    t.height(core, -4.0); t.height(rim, 2.2)
    t.layer(core, col=(0.26, 0.235, 0.20), rough=0.95)
    t.layer(t.b.math('MULTIPLY', rim, 0.9), col=(0.075, 0.075, 0.075), rough=0.3)
    # fine scuffs both ways across the whole sheet: paler and drier than the rubber
    sc1 = t.b.ramp(t.noise(300, 3, 0.6, stretch=(1, 30, 1)), 0.66, 0.72)
    sc2 = t.b.ramp(t.noise(240, 3, 0.6, stretch=(26, 1, 1)), 0.68, 0.74)
    t.layer(t.b.math('MULTIPLY', t.b.math('MAXIMUM', sc1, sc2), 0.45), col=(0.36, 0.34, 0.31), rough=0.92)
    # Ward's dust: settled toward the edges and the back, wiped off the middle where the work is
    inner = t.b.math('MULTIPLY', t.band(0, -0.34, 0.36, 0.10), t.band(1, -0.24, 0.17, 0.08))
    dustm = t.b.math('MULTIPLY', t.b.math('SUBTRACT', 1.0, t.b.math('MULTIPLY', inner, 0.8)), t.b.ramp(t.noise(7, 5, 0.65), 0.36, 0.72), clamp=True)
    t.layer(t.b.math('MULTIPLY', dustm, 0.42), col=(0.47, 0.40, 0.31), rough=0.96)
    M['ws_rubber'] = m

    M['ws_edging'] = MT.make('ws_edging', (0.44, 0.43, 0.41), 1.0, 0.46, var=0.08, edge=((0.76, 0.74, 0.71), 1.0, 0.26, 1.0),
                             dirt=DIRT, rust=((0.33, 0.17, 0.08), 0.32), bumps=[('brushed', (1, 1, 1), 0.2), ('noise', 700, 0.3)],
                             edge_width=0.0009, tone2=((0.30, 0.285, 0.265), 30, 0.5, 0.75, 0.5))

    m = MT.make('ws_rule', (0.60, 0.59, 0.57), 1.0, 0.36, var=0.06, edge=((0.82, 0.81, 0.79), 1.0, 0.2, 1.0), dirt=DIRT,
                rust=((0.30, 0.16, 0.08), 0.15), bumps=[('brushed', (30, 1, 1), 0.25)], edge_width=0.0006,
                tone2=((0.44, 0.43, 0.41), 40, 0.45, 0.7, 0.6))
    t = Tap(m)
    R = MASKS['rule']
    img = t.image(os.path.join(GEN, 'rule_marks.png'), (-HX, -HY), (R['length_mm'] * MM, R['width_mm'] * MM))
    marks, notch = t.chan(img, 0), t.chan(img, 1)
    # engraved marks filled with black: worn out of the fill here and there
    keep = t.b.math('SUBTRACT', 1.0, t.b.math('MULTIPLY', t.b.ramp(t.noise(55, 3), 0.55, 0.8), 0.7))
    t.height(marks, -2.2)
    t.layer(t.b.math('MULTIPLY', marks, keep), col=(0.015, 0.015, 0.016), rough=0.7, metal=0.0)
    t.height(notch, -3.0)
    t.layer(notch, col=(0.80, 0.30, 0.07), rough=0.6, metal=0.0)
    M['ws_rule'] = m

    # ------------------------------------------------------------------ work mat (felt, leather binding)
    m = MT.make('felt', (0.30, 0.30, 0.28), 0.0, 0.96, var=0.10, bumps=[('noise', 2300, 0.9), ('noise', 600, 0.6)],
                dirt=((0.25, 0.21, 0.16), 0.95, 0.4), tone2=((0.25, 0.24, 0.22), 25, 0.45, 0.7, 0.5), bevel_r=0.0, bump_dist=0.00035)
    t = Tap(m)
    x, y, z = t.xyz()
    rr = t.b.math('SQRT', t.b.math('ADD', t.b.math('MULTIPLY', t.b.math('MULTIPLY', x, x), 0.55), t.b.math('MULTIPLY', y, y)))
    mid = t.b.math('SUBTRACT', 1.0, t.b.ramp(t.b.math('ADD', rr, t.b.math('MULTIPLY', t.b.math('SUBTRACT', t.noise(18, 4), 0.5), 0.06)), 0.03, 0.125))
    t.layer(t.b.math('MULTIPLY', mid, 0.75), col=(0.16, 0.152, 0.145), rough=0.8)        # pressed flat and dark with oil
    fib = t.b.ramp(t.noise(900, 3, 0.6, stretch=(1, 14, 1)), 0.55, 0.8)                   # stray pale fibres
    t.layer(t.b.math('MULTIPLY', fib, 0.35), col=(0.5, 0.49, 0.46))
    M['felt'] = m
    M['binding'] = MT.make('binding', (0.34, 0.19, 0.105), 0.0, 0.6, var=0.14, edge=((0.56, 0.38, 0.24), 0.0, 0.8, 0.9), edge_width=0.001,
                           dirt=((0.12, 0.08, 0.055), 0.5, 0.6), bumps=[('pores', 1400, 0.5)], tone2=((0.17, 0.095, 0.055), 20, 0.45, 0.7, 0.7))
    M['thread'] = MT.make('thread', (0.62, 0.55, 0.42), 0.0, 0.85, var=0.1, dirt=((0.2, 0.15, 0.1), 0.9, 0.5), bevel_r=0.0)

    # ------------------------------------------------------------------ parts mat
    PW, PH = 0.44, 0.20
    m = MT.make('pm_rubber', (0.20, 0.193, 0.183), 0.0, 0.74, var=0.08, edge=((0.30, 0.29, 0.275), 0.0, 0.7, 0.5), dirt=DUST,
                bumps=[('noise', 500, 0.3)], grime=0.2, tone2=((0.27, 0.255, 0.235), 12, 0.5, 0.75, 0.4), edge_width=0.0008)
    t = Tap(m)
    t.weave(scale=1800.0, strength=0.22, tone=0.05)
    img = t.image(os.path.join(GEN, 'partsmat.png'), (-PW / 2, -PH / 2), (PW, PH))
    line, rub = t.chan(img, 0), t.chan(img, 1)
    worn = t.b.math('MULTIPLY', t.b.math('SUBTRACT', 1.0, t.b.math('MULTIPLY', rub, 0.85)),
                    t.b.ramp(t.b.math('ADD', t.noise(160, 5, 0.7), t.b.math('MULTIPLY', t.noise(900, 3), 0.4)), 0.42, 0.62), clamp=True)
    paint = t.b.math('MULTIPLY', line, worn, clamp=True)
    t.height(paint, 0.7)
    t.layer(paint, col=(0.70, 0.60, 0.27), rough=0.62)
    t.layer(t.b.math('MULTIPLY', rub, 0.5), col=(0.13, 0.126, 0.12), rough=0.5)      # where parts are put down: polished
    M['pm_rubber'] = m

    # ------------------------------------------------------------------ vise
    def cast(name, base, rust_amt=0.3, edge_amt=1.0):
        return MT.make(name, base, 0.0, 0.48, var=0.10, edge=(IRON, 1.0, 0.44, edge_amt), dirt=DIRT, rust=((0.36, 0.19, 0.10), rust_amt),
                       bumps=[('stipple', 520, 0.55), ('noise', 240, 0.8), ('noise', 1100, 0.25)], edge_width=0.0014, grime=0.45,
                       tone2=((base[0] * 0.55, base[1] * 0.55, base[2] * 0.55), 28, 0.5, 0.74, 0.55), bump_dist=0.0002)
    GREEN = MT.from_linear(VISE_GREEN_LINEAR)        # sRGB (0.152, 0.209, 0.143)

    def chips(t, amount=1.0):
        # paint knocked off in sharp-edged flakes: bare iron inside, a rust-brown lip, heavier low down and on corners
        n = t.b.math('ADD', t.noise(38, 5, 0.62), t.b.math('MULTIPLY', t.noise(170, 4, 0.6), 0.22))
        lip = t.b.ramp(n, 0.672 - 0.03 * amount, 0.685 - 0.03 * amount)
        core = t.b.ramp(n, 0.689 - 0.03 * amount, 0.699 - 0.03 * amount)
        t.layer(lip, col=(0.27, 0.14, 0.075), rough=0.85, metal=0.0, height=-0.6)
        t.layer(core, col=(0.50, 0.48, 0.455), rough=0.42, metal=1.0, height=-0.4)
        return core
    m = cast('vise_green', GREEN)
    t = Tap(m)
    chips(t)
    # the anvil: paint long gone from its top, bare iron pocked by hammer and punch
    x, y, z = t.xyz()
    anv = t.b.math('MULTIPLY', t.b.math('MULTIPLY', t.facing(2, 0.7, 0.95), t.b.ramp(z, 0.1175, 0.1185)),
                   t.b.math('MULTIPLY', t.b.ramp(y, 0.024, 0.028), t.b.math('SUBTRACT', 1.0, t.b.ramp(z, 0.125, 0.127))))
    t.layer(anv, col=(0.56, 0.545, 0.52), rough=0.34, metal=1.0)
    dim = t.b.math('SUBTRACT', 1.0, voronoi_dimples(t, 420, 0.0, 0.35))
    t.height(t.b.math('MULTIPLY', t.b.math('MULTIPLY', anv, dim), t.b.ramp(t.noise(60, 3), 0.4, 0.6)), -2.5)
    M['vise_green'] = m
    m = cast('vise_green_slide', GREEN, 0.22)
    t = Tap(m)
    chips(t, 1.3)
    # black oily grime round the screw boss, and the jaw top polished by hands and work
    x, y, z = t.xyz()
    th, al, rr = t.cyl((0, 0, 0.084), (0, 1, 0))
    oil = t.b.math('MULTIPLY', t.b.math('SUBTRACT', 1.0, t.b.ramp(rr, 0.017, 0.034)), t.b.ramp(t.noise(60, 4), 0.3, 0.7))
    t.layer(t.b.math('MULTIPLY', oil, 0.8), col=(0.075, 0.065, 0.055), rough=0.3, metal=0.0)
    M['vise_green_slide'] = m
    M['vise_bar'] = MT.make('vise_bar', (0.62, 0.61, 0.59), 1.0, 0.27, var=0.05, edge=((0.84, 0.83, 0.81), 1.0, 0.16, 0.8), dirt=OIL,
                            bumps=[('brushed', (1, 40, 1), 0.3), ('noise', 900, 0.15)], grime=0.5,
                            tone2=((0.30, 0.255, 0.20), 35, 0.52, 0.72, 0.55))
    M['vise_screw'] = MT.make('vise_screw', (0.56, 0.55, 0.52), 1.0, 0.30, var=0.06, edge=((0.84, 0.83, 0.80), 1.0, 0.16, 1.0), dirt=OIL,
                              bumps=[('noise', 900, 0.2)], grime=0.7, ao_dist=0.004)
    M['vise_plate'] = MT.make('vise_plate', (0.50, 0.49, 0.47), 1.0, 0.36, var=0.06, edge=((0.80, 0.79, 0.76), 1.0, 0.2, 1.0), dirt=DIRT,
                              bumps=[('noise', 900, 0.25)])
    M['pad_copper_old'] = MT.make('pad_copper_old', (0.64, 0.39, 0.26), 1.0, 0.42, var=0.12, edge=((0.90, 0.58, 0.40), 1.0, 0.24, 0.9),
                                  dirt=((0.15, 0.11, 0.08), 0.8, 0.8), bumps=[('noise', 500, 0.5)], tone2=((0.30, 0.44, 0.37), 60, 0.55, 0.72, 0.6))
    M['pad_copper_new'] = MT.make('pad_copper_new', (0.80, 0.47, 0.31), 1.0, 0.30, var=0.08, edge=((0.95, 0.64, 0.46), 1.0, 0.2, 0.7),
                                  dirt=((0.14, 0.09, 0.06), 0.7, 0.5), bumps=[('noise', 500, 0.35)])
    M['pad_leather_old'] = MT.make('pad_leather_old', (0.27, 0.155, 0.095), 0.0, 0.5, var=0.16, edge=((0.50, 0.34, 0.22), 0.0, 0.8, 0.9), edge_width=0.001,
                                   dirt=((0.075, 0.055, 0.04), 0.4, 0.8), bumps=[('pores', 1300, 0.5), ('noise', 180, 0.8)],
                                   tone2=((0.085, 0.065, 0.055), 45, 0.42, 0.66, 0.8))
    M['pad_leather_new'] = MT.make('pad_leather_new', (0.44, 0.27, 0.15), 0.0, 0.66, var=0.10, edge=((0.52, 0.36, 0.22), 0.0, 0.8, 0.6), edge_width=0.001,
                                   dirt=((0.12, 0.08, 0.05), 0.6, 0.4), bumps=[('pores', 1300, 0.5)])
    M['bolt'] = MT.make('bolt', (0.44, 0.43, 0.41), 1.0, 0.5, var=0.1, edge=((0.74, 0.72, 0.69), 1.0, 0.28, 1.0), dirt=DIRT,
                        rust=((0.38, 0.20, 0.10), 0.45), bumps=[('noise', 800, 0.35)])

    # ------------------------------------------------------------------ dish, cradle, pad, board
    m = MT.make('dish_steel', (0.68, 0.675, 0.66), 1.0, 0.30, var=0.05, edge=((0.86, 0.86, 0.84), 1.0, 0.16, 0.6), dirt=DIRT,
                bumps=[('lathe', 'Z', 900, 0.10), ('noise', 700, 0.2)], grime=0.3, tone2=((0.46, 0.45, 0.43), 50, 0.5, 0.72, 0.5))
    t = Tap(m)
    # scratched grey floor where screws are dropped and stirred
    x, y, z = t.xyz()
    rr = t.b.math('SQRT', t.b.math('ADD', t.b.math('MULTIPLY', x, x), t.b.math('MULTIPLY', y, y)))
    floor = t.b.math('MULTIPLY', t.b.math('SUBTRACT', 1.0, t.b.ramp(rr, 0.03, 0.04)), t.facing(2, 0.5, 0.9))
    scr = t.b.ramp(t.noise(420, 4, 0.7, stretch=(1, 9, 1)), 0.5, 0.72)
    t.layer(t.b.math('MULTIPLY', floor, t.b.math('ADD', 0.35, t.b.math('MULTIPLY', scr, 0.5))), col=(0.52, 0.515, 0.50), rough=0.46)
    M['dish_steel'] = m
    M['dish_rubber'] = MT.make('dish_rubber', (0.16, 0.156, 0.15), 0.0, 0.7, var=0.1, edge=((0.27, 0.26, 0.25), 0.0, 0.7, 0.6), dirt=DUST,
                               bumps=[('stipple', 1500, 0.3)])

    def wood(name, base, dark, grain_axis, amount=0.55, rough=0.5):
        st = [8, 8, 8]; st[grain_axis] = 0.7
        return MT.make(name, base, 0.0, rough, var=0.12, edge=((base[0] * 1.5, base[1] * 1.5, base[2] * 1.5), 0.0, 0.7, 0.8), edge_width=0.0012,
                       dirt=((0.10, 0.07, 0.05), 0.6, 0.7), bumps=[('grain', tuple(st), 60, 0.6, dark, amount), ('noise', 500, 0.2)],
                       tone2=((dark[0] * 0.8, dark[1] * 0.8, dark[2] * 0.8), 18, 0.5, 0.72, 0.5))
    m = wood('wood_cradle', (0.36, 0.21, 0.115), (0.15, 0.085, 0.048), 0)
    t = Tap(m)
    dent = t.b.math('SUBTRACT', 1.0, voronoi_dimples(t, 70, 0.0, 0.16))        # knocks and old tool marks
    t.height(dent, -3.0)
    t.layer(t.b.math('MULTIPLY', dent, 0.8), col=(0.09, 0.06, 0.04), rough=0.75)
    stain = t.b.ramp(t.noise(22, 4, 0.6), 0.52, 0.7)
    t.layer(t.b.math('MULTIPLY', stain, 0.7), col=(0.07, 0.052, 0.04), rough=0.35)       # oil soaked in
    M['wood_cradle'] = m
    M['forged'] = MT.make('forged', (0.40, 0.385, 0.365), 1.0, 0.46, var=0.12, edge=((0.76, 0.74, 0.71), 1.0, 0.26, 1.0), dirt=DIRT,
                          rust=((0.36, 0.19, 0.10), 0.35), bumps=[('noise', 300, 0.9), ('noise', 900, 0.3)], edge_width=0.0011,
                          tone2=((0.27, 0.25, 0.23), 40, 0.5, 0.72, 0.6))
    M['leather'] = MT.make('leather_fx', (0.36, 0.205, 0.12), 0.0, 0.6, var=0.14, edge=((0.56, 0.38, 0.24), 0.0, 0.8, 0.9), edge_width=0.001,
                           dirt=((0.11, 0.075, 0.055), 0.5, 0.7), bumps=[('pores', 1300, 0.5)], tone2=((0.16, 0.095, 0.06), 30, 0.45, 0.7, 0.7))
    M['brass_screw'] = MT.make('brass_screw', (0.72, 0.57, 0.32), 1.0, 0.4, var=0.1, edge=((0.9, 0.76, 0.5), 1.0, 0.22, 1.0),
                               dirt=((0.16, 0.12, 0.07), 0.7, 0.9))

    m = MT.make('tile', (0.74, 0.72, 0.66), 0.0, 0.22, var=0.04, edge=((0.55, 0.50, 0.42), 0.0, 0.8, 0.7), dirt=((0.3, 0.25, 0.18), 0.8, 0.6),
                bumps=[('noise', 300, 0.12)], edge_width=0.0012, grime=0.5)
    t = Tap(m)
    TX, TY = 0.065, 0.052
    x, y, z = t.xyz()
    ax = t.b.math('ABSOLUTE', x); ay = t.b.math('ABSOLUTE', y)
    border = t.b.math('MAXIMUM', t.b.ramp(ax, TX - 0.0135, TX - 0.0125), t.b.ramp(ay, TY - 0.0135, TY - 0.0125))
    border = t.b.math('MULTIPLY', border, t.facing(2, 0.6, 0.9))
    chip = t.b.ramp(t.b.math('ADD', t.noise(120, 5, 0.7), t.b.math('MULTIPLY', t.noise(700, 3), 0.3)), 0.47, 0.62)   # paint that is left
    stripe = t.stripes((0, 1), 0.014, 0.5, 45.0)
    t.layer(t.b.math('MULTIPLY', border, chip), col=(0.66, 0.52, 0.13), rough=0.55)
    t.layer(t.b.math('MULTIPLY', t.b.math('MULTIPLY', border, chip), stripe), col=(0.03, 0.03, 0.03), rough=0.55)
    crz = t.b.n('ShaderNodeTexVoronoi', feature='DISTANCE_TO_EDGE'); crz.inputs['Scale'].default_value = 130
    t.b.l(t.P, crz.inputs['Vector'])
    crack = t.b.math('SUBTRACT', 1.0, t.b.ramp(crz.outputs['Distance'], 0.0, 0.012))                               # crazing in the glaze
    t.layer(t.b.math('MULTIPLY', crack, 0.5), col=(0.30, 0.26, 0.2), rough=0.6)
    M['tile'] = m
    M['pad_rubber'] = MT.make('pad_rubber', (0.40, 0.15, 0.105), 0.0, 0.72, var=0.12, edge=((0.55, 0.26, 0.19), 0.0, 0.7, 0.7), dirt=DUST,
                              bumps=[('stipple', 1300, 0.3), ('noise', 300, 0.3)], grime=0.45, tone2=((0.19, 0.075, 0.055), 40, 0.5, 0.72, 0.6),
                              edge_width=0.001)

    m = MT.make('hardboard', (0.42, 0.30, 0.19), 0.0, 0.66, var=0.08, edge=((0.58, 0.44, 0.30), 0.0, 0.85, 0.8), edge_width=0.0012,
                dirt=((0.17, 0.125, 0.085), 0.8, 0.5), bumps=[('noise', 1800, 0.35), ('noise', 300, 0.2)],
                tone2=((0.27, 0.185, 0.115), 9, 0.46, 0.7, 0.55))
    t = Tap(m)
    pin = t.b.math('SUBTRACT', 1.0, voronoi_dimples(t, 55, 0.0, 0.035))           # old pin holes
    t.height(pin, -3.0)
    t.layer(pin, col=(0.10, 0.07, 0.05), rough=0.9)
    M['hardboard'] = m
    M['frame_steel'] = MT.make('frame_steel', (0.42, 0.41, 0.395), 1.0, 0.5, var=0.1, edge=((0.74, 0.72, 0.69), 1.0, 0.28, 1.0), dirt=DIRT,
                               rust=((0.38, 0.20, 0.10), 0.35), bumps=[('noise', 700, 0.3)], edge_width=0.0009)
    M['clip_black'] = MT.make('clip_black', (0.12, 0.12, 0.125), 0.6, 0.42, var=0.08, edge=((0.62, 0.61, 0.58), 1.0, 0.24, 1.0), dirt=DUST,
                              bumps=[('noise', 900, 0.2)], edge_width=0.0007)
    M['clip_wire'] = MT.make('clip_wire', (0.62, 0.61, 0.59), 1.0, 0.25, var=0.05, dirt=DIRT, bevel_r=0.0)
    return M
