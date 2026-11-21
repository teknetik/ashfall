# tl_mats.py: authoring materials of the tools family (kit mats.make plus layers from mbk.Tap).
# Look target: ../../concept/bench_overview_fal.jpg: steel dark with oxide and worn bright where it works, handles
# re-taped in pale cloth gone grey-brown with oil, wood dark and polished by hands.
import math
from mbk import MT, Tap, MM

# Albedo was re-tuned on 20 Nov 19:40 at a calibrated exposure (white card 0.9 scene-linear, SEAM.md section 8): the
# first set had been judged under a rig 1.6 EV too bright and was one to two stops too dark.
DIRT = ((0.20, 0.155, 0.115), 0.85, 0.75)
DUST = ((0.50, 0.41, 0.31), 0.9, 0.55)
OIL = ((0.07, 0.055, 0.04), 0.4, 0.8)


def stamp_triangle(m, x0, y0, r=0.0017, zmin=0.004):
    """The player's mark: a small punched triangle on an up-facing face at (x0, y0) in the object's frame."""
    t = Tap(m)
    x, y, z = t.xyz()
    px = t.b.math('ABSOLUTE', t.b.math('SUBTRACT', x, x0)); py = t.b.math('SUBTRACT', y, y0)
    d = t.b.math('MAXIMUM', t.b.math('ADD', t.b.math('MULTIPLY', px, 0.866), t.b.math('MULTIPLY', py, 0.5)), t.b.math('MULTIPLY', py, -1.0))
    inside = t.b.math('SUBTRACT', 1.0, t.b.ramp(d, r * 0.5 - 0.00012, r * 0.5 + 0.00012))
    line = t.b.math('MULTIPLY', inside, t.b.ramp(d, r * 0.5 - 0.00055, r * 0.5 - 0.0003))
    mask = t.b.math('MULTIPLY', line, t.b.math('MULTIPLY', t.facing(2, 0.7, 0.95), t.b.ramp(z, zmin - 0.0002, zmin)))
    t.height(mask, -3.0)
    t.layer(mask, col=(0.11, 0.10, 0.095), rough=0.6)
    return m


def tool_steel(name, base=(0.47, 0.445, 0.415), rough=0.44, rust=0.42, bright=1.0, brushed=None, oxide=0.6):
    """Old tool steel kept oiled, not polished: brown oxide in patches, fine pitting, bright on edges and where it
    works, a little rust in the hollows."""
    bumps = [('noise', 900, 0.3), ('noise', 260, 0.5)]
    if brushed:
        bumps.append(('brushed', brushed, 0.25))
    m = MT.make(name, base, 1.0, rough, var=0.10, edge=((0.80, 0.78, 0.75), 1.0, 0.26, bright * 0.75), dirt=DIRT,
                rust=((0.40, 0.22, 0.12), rust), bumps=bumps, edge_width=0.0009, grime=0.5,
                tone2=((0.33, 0.29, 0.25), 45, 0.5, 0.72, 0.6))
    if oxide:
        t = Tap(m)
        ox = t.b.ramp(t.b.math('ADD', t.noise(46, 5, 0.7), t.b.math('MULTIPLY', t.noise(320, 3, 0.6), 0.22)), 0.57, 0.75)
        t.layer(t.b.math('MULTIPLY', ox, oxide), col=(0.31, 0.18, 0.105), rough=0.78, metal=0.3)
        pit = t.b.ramp(t.noise(850, 2, 0.5), 0.71, 0.79)
        t.height(pit, -1.2)
        t.layer(t.b.math('MULTIPLY', pit, 0.55), col=(0.15, 0.10, 0.07), rough=0.85)
    return m


def wood(name, base, dark, axis=1, amount=0.6, rough=0.42, polish=0.7):
    st = [9, 9, 9]; st[axis] = 0.6
    m = MT.make(name, base, 0.0, rough, var=0.12, edge=((base[0] * 1.5, base[1] * 1.45, base[2] * 1.4), 0.0, 0.6, 0.7), edge_width=0.0012,
                dirt=((0.09, 0.065, 0.045), 0.55, 0.8), bumps=[('grain', tuple(st), 70, 0.5, dark, amount), ('noise', 400, 0.2)],
                tone2=((dark[0] * 0.7, dark[1] * 0.7, dark[2] * 0.7), 22, 0.45, 0.7, polish), grime=0.5)
    return m


def tape(name, origin, axis, lo, hi, pitch=0.007, base=(0.60, 0.55, 0.46)):
    """Cloth tape wound round a handle, pale, grey-brown where the palm sits, frayed at the ends."""
    m = MT.make(name, base, 0.0, 0.86, var=0.14, edge=((0.74, 0.70, 0.62), 0.0, 0.9, 0.5), edge_width=0.0008,
                dirt=((0.20, 0.16, 0.12), 0.8, 0.9), bumps=[('noise', 1500, 0.5)], grime=0.9,
                tone2=((0.30, 0.25, 0.19), 26, 0.36, 0.62, 0.9), bump_dist=0.00025)
    t = Tap(m)
    t.wrap(origin, axis, pitch, lo, hi, strength=1.3)
    th_, al_, rr_ = t.cyl(origin, axis)
    palm = t.b.math('MULTIPLY', t.b.ramp(al_, lo + (hi - lo) * 0.25, lo + (hi - lo) * 0.6), t.b.ramp(t.noise(40, 4), 0.25, 0.7))
    t.layer(t.b.math('MULTIPLY', palm, 0.6), col=(0.17, 0.14, 0.11), rough=0.6)        # black with oil where the palm closes
    t.weave(scale=1 / 0.0011, strength=0.25, axes=(0, 1), tone=0.06)
    return m


def library(M):
    M['t_steel'] = tool_steel('t_steel')
    M['t_steel_pliers'] = stamp_triangle(tool_steel('t_steel_pliers'), -0.0066, 0.0185)
    M['t_steel_cutters'] = stamp_triangle(tool_steel('t_steel_cutters'), 0.0, -0.0005, r=0.0014)
    M['t_steel_bright'] = MT.make('t_steel_bright', (0.68, 0.67, 0.65), 1.0, 0.26, var=0.06, edge=((0.86, 0.85, 0.83), 1.0, 0.14, 0.8), dirt=OIL,
                                  bumps=[('noise', 900, 0.2), ('brushed', (1, 30, 1), 0.2)], grime=0.4,
                                  tone2=((0.40, 0.37, 0.33), 60, 0.52, 0.72, 0.5))
    M['t_shaft'] = MT.make('t_shaft', (0.55, 0.535, 0.51), 1.0, 0.34, var=0.08, edge=((0.82, 0.81, 0.78), 1.0, 0.18, 1.0), dirt=DIRT,
                           rust=((0.40, 0.22, 0.12), 0.3), bumps=[('lathe', 'Y', 1400, 0.12), ('noise', 700, 0.2)],
                           tone2=((0.38, 0.35, 0.31), 50, 0.5, 0.72, 0.5))
    M['t_brass'] = MT.make('t_brass', (0.70, 0.55, 0.30), 1.0, 0.38, var=0.10, edge=((0.92, 0.78, 0.52), 1.0, 0.2, 1.0),
                           dirt=((0.18, 0.13, 0.08), 0.7, 0.9), bumps=[('lathe', 'Y', 1200, 0.15)], tone2=((0.42, 0.31, 0.17), 40, 0.5, 0.72, 0.6))
    M['t_wood'] = wood('t_wood', (0.37, 0.215, 0.115), (0.14, 0.08, 0.045))
    M['t_wood_pale'] = wood('t_wood_pale', (0.56, 0.41, 0.24), (0.30, 0.19, 0.10), amount=0.5, rough=0.5)
    m = MT.make('t_rubber_red', (0.47, 0.075, 0.058), 0.0, 0.5, var=0.12, edge=((0.52, 0.50, 0.48), 1.0, 0.36, 1.0), edge_width=0.0016,
                dirt=((0.15, 0.075, 0.06), 0.7, 0.8), bumps=[('noise', 500, 0.4), ('noise', 160, 0.6)], grime=0.6,
                tone2=((0.23, 0.045, 0.042), 35, 0.42, 0.66, 0.85))
    t = Tap(m)
    # the dip is worn through to the steel at the handle ends and cracked off in flakes
    x, y, z = t.xyz()
    n = t.b.math('ADD', t.noise(70, 5, 0.65), t.b.math('MULTIPLY', t.b.ramp(y, -0.088, -0.104), 0.22))
    bare = t.b.ramp(n, 0.63, 0.65)
    t.layer(bare, col=(0.50, 0.48, 0.455), rough=0.4, metal=1.0, height=-2.0)
    M['t_rubber_red'] = m
    M['t_rawhide'] = MT.make('t_rawhide', (0.66, 0.58, 0.43), 0.0, 0.8, var=0.12, edge=((0.78, 0.72, 0.58), 0.0, 0.9, 0.7), edge_width=0.001,
                             dirt=((0.26, 0.20, 0.14), 0.85, 0.9), bumps=[('lathe', 'X', 700, 0.6), ('noise', 500, 0.4)], grime=0.7,
                             tone2=((0.40, 0.33, 0.23), 40, 0.4, 0.66, 0.8))
    M['t_brass_face'] = MT.make('t_brass_face', (0.71, 0.56, 0.31), 1.0, 0.42, var=0.10, edge=((0.93, 0.80, 0.54), 1.0, 0.22, 1.0),
                                dirt=((0.18, 0.13, 0.08), 0.7, 0.8), bumps=[('noise', 300, 0.9), ('noise', 900, 0.3)],
                                tone2=((0.45, 0.34, 0.19), 50, 0.45, 0.68, 0.7))
    M['t_black_rubber'] = MT.make('t_black_rubber', (0.16, 0.157, 0.153), 0.0, 0.62, var=0.1, edge=((0.27, 0.26, 0.25), 0.0, 0.7, 0.6), dirt=DUST,
                                  bumps=[('noise', 900, 0.2)], grime=0.5)
    M['t_bakelite'] = MT.make('t_bakelite', (0.135, 0.105, 0.088), 0.0, 0.36, var=0.1, edge=((0.27, 0.20, 0.15), 0.0, 0.5, 0.7), dirt=DUST,
                              bumps=[('noise', 700, 0.2)])
    M['t_oil'] = MT.make('t_oil', (0.30, 0.17, 0.035), 0.0, 0.08, var=0.05, bevel_r=0.0)
    M['glass_amber'] = MT.passthrough('glass_amber', (0.34, 0.13, 0.025), alpha=0.72, rough=0.06)
    M['glass_clear'] = MT.passthrough('glass_clear', (0.80, 0.86, 0.84), alpha=0.25, rough=0.06)
    # ---- the roll
    m = MT.make('roll_canvas', (0.33, 0.305, 0.195), 0.0, 0.58, var=0.10, edge=((0.46, 0.43, 0.31), 0.0, 0.78, 0.7), edge_width=0.0014,
                dirt=((0.09, 0.08, 0.05), 0.55, 0.95), bumps=[('noise', 300, 0.4)], grime=0.8,
                tone2=((0.24, 0.22, 0.14), 5, 0.45, 0.72, 0.40), bump_dist=0.00035, ao_dist=0.012)
    t = Tap(m)
    wax = t.b.ramp(t.b.math('ADD', t.noise(14, 5, 0.65), t.b.math('MULTIPLY', t.noise(90, 3, 0.6), 0.3)), 0.58, 0.72)
    t.layer(t.b.math('MULTIPLY', wax, 0.35), col=(0.29, 0.27, 0.17), rough=0.38)       # fresh wax: darker and shiny in patches
    t.weave(scale=1 / 0.0012, strength=0.75, axes=(0, 1), tone=0.07)
    M['roll_canvas'] = m
    M['roll_leather'] = MT.make('roll_leather', (0.27, 0.15, 0.085), 0.0, 0.55, var=0.14, edge=((0.54, 0.37, 0.24), 0.0, 0.8, 0.9), edge_width=0.001,
                                dirt=((0.10, 0.07, 0.05), 0.5, 0.7), bumps=[('pores', 1300, 0.5), ('noise', 200, 0.5)],
                                tone2=((0.14, 0.08, 0.05), 30, 0.45, 0.7, 0.7))
    M['roll_buckle'] = tool_steel('roll_buckle', (0.42, 0.42, 0.42), rough=0.4, rust=0.5, oxide=0.3)
    M['roll_thread'] = MT.make('roll_thread', (0.60, 0.53, 0.38), 0.0, 0.85, var=0.1, dirt=((0.2, 0.15, 0.1), 0.9, 0.5), bevel_r=0.0)
    return M
