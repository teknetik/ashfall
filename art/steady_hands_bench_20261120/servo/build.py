# servo/build.py: the Damaged Servo (item droid_servo_damaged) and everything inside it. See PARTS.md.
#
# Parts, in the order they are built (each is one node, `servo_<id>`):
#   case_body       lower half can, both end bells, boss, foot, seam flanges and screw bosses, deck, shaft pedestal,
#                   gear post, idler post and pinion, board shelves, clip hinge pins, grommet, three torn outside leads
#   case_lid        upper half shell, flanges, four lugs, ribs, riveted data plate (scorched rear +Y corner)
#   clip_1..3       spring strap clips on hinge pins under the body flange (rig clip_1..3)
#   screw_case_a..d four brass M3 x 10 cross screws (d is chewed)
#   output_shaft    shaft, outside pinion, inner pinion
#   stator, stator_winding   flat laminated ring round the gimbal well, two wound sectors
#   gear_low, gear_mid, gear_top, circlip      crown gear, large spur, small spur on the gear post
#   board, trim_resistor, lead_plug            burnt control board with its pot, the resistor, the plug and lead ends
#   lead_coil_a, lead_coil_b, lead_sense       the three leads, cut at their bands
#   screw_trunnion_a, _b                       the two screws that hold the gimbal's lugs to the stator
#   gimbal_cradle, gimbal_coil, gimbal_ring, gimbal_race, gimbal_rotor, gimbal_retainer, gimbal_grit_1..3  (gimbal.py)
#
# Where this leaves the sheets: the outside follows sheets/servo_turn.png (round can); the inside takes the exploded
# sheet's flat deck and flat stator. The gear stack is small, large, small and not a pyramid, because a pyramid
# cannot lift past fixed mesh partners. The lid screws sit on seam-flange lugs (that is the 70 mm width), not on the
# lid's curved top. The outside leads are red, blue and yellow as on the bench look target.
#
# Run: SH/blender.sh servo/build.py -- --nobake        then  SH/blender.sh servo/check.py
import sys, os, math, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'kit'))
sys.path.insert(0, HERE)
from family import Family, G, MT, CT, RG
import am_parts as AP
import bpy
from mathutils import Vector, Matrix
import sv
from sv import P, MM, X, Y, Z
import gimbal as GM

FAM = 'servo'
F = Family(FAM, __file__, budget=45000)
if '--out' in F.argv:        # a surface trial (`-- --nobake --out export_wip`): export/ keeps the checked, published build
    F.out = os.path.join(HERE, F.argv[F.argv.index('--out') + 1]); os.makedirs(F.out, exist_ok=True)
M = F.mats

# ------------------------------------------------------------------ dimensions (mm)
ZA = 29.0                    # can axis height
RO, RI = 26.0, 24.0          # can outside and inside radius
X0, X1 = -22.5, 38.5         # inner faces of the end bells
SEAM, LIDGAP = 31.0, 0.05
FL_TOP = 33.45               # top of the lid flange
DECK = 16.0
GX, GY, GZ = 17.0, 0.0, 30.4 # gimbal datum D: centre of the cradle flange's outer face (grip/INTERFACE.md)
PX, PY = -5.6, 0.0           # gear post
LUGS = [(-16.5, 1), (32.5, 1), (32.5, -1), (-16.5, -1)]        # case screws a, b, c, d
CLIPS = [(-2.0, 1), (19.0, 1), (8.0, -1)]
GD = dict(GM.DIM)
MD = Matrix.Translation(P(GX, GY, GZ)) @ Matrix.Rotation(math.pi, 4, 'Z')      # D in the servo: +X_D to the rear, +Y_D to -Y, leads leave on the -Y side
STAT_Z0, STAT_Z1 = GZ - 10.0, GZ - 4.0          # stator core
BLOCK_TOP = GZ - GD['flange_t'] - 0.05

# ------------------------------------------------------------------ materials
DIRT = ((0.16, 0.12, 0.09), 0.85, 0.75)
DUST = (0.52, 0.44, 0.33)
# Warden orange and the bare alloy under it are the programme's shared colours: the kit's constants (linear albedo,
# SEAM.md section 8), never typed here. Every tone of the paint and of the bare metal is one of them times a factor.
def tone(lin, k):
    """A shared linear albedo times a factor (one number or one per channel) -> the sRGB triple the kit takes."""
    k = k if isinstance(k, (tuple, list)) else (k, k, k)
    return MT.from_linear(tuple(min(1.0, x * f) for x, f in zip(lin, k)))


ORANGE = MT.from_linear(MT.WARDEN_ORANGE)
BARE = (MT.from_linear(MT.BARE_ALLOY), MT.BARE_ALLOY_ROUGH, 1.0)          # old and oxidised: a dull dark grey-brown
OXIDE = (tone(MT.BARE_ALLOY, 0.55), 0.72, 0.6)                             # darker blooms on the bare metal
FRESH = (tone(MT.BARE_ALLOY, 1.6), 0.44, 1.0)                              # a scratch from the salvage: still brighter than the old bare metal
OIL = (tone(MT.WARDEN_ORANGE, (0.66, 0.60, 0.58)), 0.46)                   # where hands held it: darker, a little glossier
SOAK = (tone(MT.WARDEN_ORANGE, (0.46, 0.40, 0.36)), 0.52)                  # an old spill that soaked in
CHALK = (tone(MT.WARDEN_ORANGE, (1.08, 1.24, 1.38)), 0.70)                 # chalked and faded where it faced the sun (lighter, a little duller)
RUB = (tone(MT.WARDEN_ORANGE, (0.74, 0.64, 0.58)), 0.44)                   # paint rubbed thin and burnished, not cut through
PRIMER = ((0.30, 0.13, 0.06), 0.8)                                         # the rim round a flake, as on the alloy plates (materials/mtl.py)
# edge=None: no even worn line on every edge (it read as an outline); edges lose their paint through add_flakes' edge_gain, in runs
PAINT = dict(metal=0.0, rough=0.58, var=0.11, rough_var=0.07, edge=None, dirt=DIRT, rust=((0.33, 0.15, 0.06), 0.08),
             bumps=[('noise', 700, 0.3), ('stipple', 2600, 0.14)], tone2=(OIL[0], 42, 0.5, 0.74, 0.36), grime=0.45)     # tone2: handling stains
LID_O = P(8, 0, SEAM)


def fld(c, r, o=(0, 0, 0)):
    """A wear field: centre and radii in millimetres (world), moved into the object space of a part whose origin is o."""
    return (P(*c) - Vector(o), (r[0] * MM, r[1] * MM, r[2] * MM))


def flds(rows, o=(0, 0, 0)):
    return [fld(c, r, o) for c, r in rows]


# Where the paint is worn through (the last surface pass, 20 Nov 21:00): only where the thing was handled, clamped,
# stood and dragged. Nothing in the middle of a panel: the lid's shoulder field of the first repaint is gone.
WEAR = {
    'sv_paint': flds((
        ((-15.5, -28.5, 1.6), (7, 6.5, 4)), ((27.5, -28.5, 1.6), (8, 7, 4)), ((-15.5, 28.5, 1.6), (5, 5, 3.5)), ((27.5, 28.5, 1.6), (4.5, 4.5, 3.5)),     # the foot's corners
        ((-17, -4, 2.4), (3, 12, 3)),                                                         # the foot's front edge
        ((6, 23, 3.2), (6.5, 7.5, 2.2)), ((6, -23, 3.2), (6.5, 7.5, 2.2)),                    # round the bolt slots, under the washers
        ((-2, 31, 27.8), (5.5, 3, 3.5)), ((19, 31, 27.8), (5.5, 3, 3.5)), ((8, -31, 27.8), (5.5, 3, 3.5)),         # the clip seats
        ((-16.5, 34.5, 26), (4.5, 3, 5.5)), ((32.5, -34.5, 26), (4.5, 3, 5.5)), ((32.5, 34.5, 27), (3.5, 2.5, 4)), ((-16.5, -34.5, 27), (4, 2.5, 4.5)),   # the screw bosses
        ((20, -31, 28.6), (12, 2.5, 2.5)),                                                    # a length of flange edge on the side it lay on
        ((-9, -19, 9), (3.2, 3, 4.5)), ((21, -19, 9), (3.2, 3, 4.5)))),                       # the saddle ribs' ends on that side
    'sv_lidpaint': flds((
        ((-12, 3, 55.0), (2.0, 10, 3.0)), ((8, -5, 54.8), (2.0, 12, 3.4)), ((28, -2, 55.0), (2.0, 8, 3.0)),        # the rib crests over the crown
        ((-2, 30.2, 33.0), (6, 3.2, 2.4)), ((19, 30.2, 33.0), (6, 3.2, 2.4)), ((8, -30.2, 33.0), (6, 3.2, 2.4)),   # the flange under the clips
        ((22, -31, 32.4), (11, 2.4, 2.2)), ((-9, -31, 32.4), (6, 2.2, 2.2)), ((8, 31, 32.4), (7, 2.2, 2.2)),       # lengths of flange edge
        ((-16.5, 30.5, 33.4), (5.2, 5.2, 2.4)), ((32.5, 30.5, 33.4), (4.8, 4.8, 2.4)), ((32.5, -30.5, 33.4), (4.8, 4.8, 2.4)),
        ((-16.5, -30.5, 33.4), (5.2, 5.2, 2.4))), LID_O),                                     # the four lugs, round the screws
}
# the side it lay on and was dragged along: the -Y flank of the body, below the seam
DRAG = {'sv_paint': flds((((8, -22.0, 15.0), (33, 6.5, 10)),)),
        'sv_lidpaint': flds((((8, 0, 55.0), (32, 12, 5)),), LID_O)}                           # the crown: rubbed, not dragged bare
# where a hand closes round it
HELD = {'sv_paint': flds((((8, 22, 17), (22, 8, 10)), ((0, -22, 19), (24, 8, 9)))),
        'sv_lidpaint': flds((((2, 15, 49), (22, 12, 9)), ((14, -15, 48), (20, 11, 9))), LID_O)}
BURNT = ((0.20, 0.10, 0.06), 0.8)             # paint darkened by heat
SOOT = ((0.035, 0.03, 0.027), 0.95)
for nm in ('sv_paint', 'sv_lidpaint'):
    lid = nm == 'sv_lidpaint'
    oo = LID_O if lid else Vector((0, 0, 0))
    M[nm] = m = MT.make(nm, ORANGE, **PAINT)
    # the paint itself is not one flat colour: chalked where it faced up, oil where it was held, one old soaked spill
    sv.add_chalk(m, CHALK[0], CHALK[1], amount=0.20)
    sv.add_stains(m, OIL[0], OIL[1], scale=30.0, lo=0.47, hi=0.66, amount=0.62, seed=(0.31, 0.07, 0.19), fields=HELD[nm], gain=0.18)
    sv.add_stains(m, SOAK[0], SOAK[1], scale=17.0, lo=0.64, hi=0.74, amount=0.55, detail=5, seed=(0.11, 0.53, 0.29))
    if lid:      # the stencilled serial, on the lid's -Y shoulder between two ribs
        ta = math.radians(113)
        sv.add_stencil(m, os.path.join(HERE, 'src', 'stencil_8372.png'), P(18, RO * math.cos(ta), ZA + RO * math.sin(ta)) - LID_O,
                       (1, 0, 0), (0, math.sin(ta), -math.cos(ta)), 0.0150, 0.0040, (0.80, 0.76, 0.66))
    # rub marks along the axis: paint burnished thin in broad bands, most on the dragged side and the crown
    sv.add_rubs(m, RUB[0], RUB[1], 0.0, scale=(22.0, 300.0, 300.0), lo=0.60, hi=0.72, fields=DRAG[nm], gain=0.10, group=(22.0, 0.40, 0.56), amount=0.5, depth=-0.1)
    # flakes with the plates' coast and primer rim, at the handled places and along outside edges only
    sv.add_flakes(m, WEAR[nm], BARE[0], BARE[1], BARE[2], gain=0.245, plateau=0.45, mix=(0.40, 0.42, 0.18), rim=PRIMER, edge_gain=0.15, pits=0.3,
                  stain=OXIDE)
    if not lid:  # the dragged side: the flakes drawn out along the axis, a wide primer haze round them
        sv.add_flakes(m, DRAG[nm], BARE[0], BARE[1], BARE[2], scale=74.0, gain=0.28, plateau=0.5, mix=(0.45, 0.38, 0.17), rim=PRIMER, rim_w=2.6,
                      stretch=(0.2, 1.0, 1.0), seed=(0.4, 0.0, 0.2),
                      pits=0.3, stain=OXIDE)
    # scratches along the axis, through to the metal: old dull ones, and a few still bright from the salvage
    sv.add_rubs(m, BARE[0], BARE[1], BARE[2], scale=(30.0, 480.0, 480.0), lo=0.695, hi=0.705, fields=DRAG[nm], gain=0.07, group=(30.0, 0.40, 0.55), depth=-0.5)
    sv.add_rubs(m, FRESH[0], FRESH[1], FRESH[2], scale=(55.0, 650.0, 650.0), lo=0.705, hi=0.715, group=(18.0, 0.46, 0.58), depth=-0.5)
    # grime: a tide mark towards the foot and against the end bells, the recesses, runs down the flanks
    if lid:
        sv.add_grime(m, DIRT[0], 0.86, 0.0 * MM, 6.0 * MM, amount=0.30, cav=0.55, ends=((X0 - 8) * MM, (X1 - 8) * MM, 8 * MM, 0.30))
    else:
        sv.add_grime(m, DIRT[0], 0.86, 3.0 * MM, 15.0 * MM, amount=0.85, cav=0.6, ends=(X0 * MM, X1 * MM, 8 * MM, 0.32), tide=(3.0 * MM, 1.8 * MM, 0.7))
    sv.add_streaks(m, (0.20, 0.14, 0.09), 0.85, axis='Z', scale=(300.0, 300.0, 26.0), lo=0.56, hi=0.8, amount=0.45)
    # the scorch at the rear +Y corner: paint darkened and blistered in a wide soft field, soot thickening to black
    sv.add_patch(m, P(32, 16, 47) - oo, 0.034, BURNT[0], BURNT[1], 0.0, noise_scale=150, soft=0.45, bump=2.6, inner=0.12, amount=0.9)
    sv.add_patch(m, P(34, 17, 47) - oo, 0.024, SOOT[0], SOOT[1], 0.0, noise_scale=210, soft=0.5, inner=0.05)
    sv.add_dust(m, DUST, veil=0.035, cav=1.9, up=1.5)
M['sv_bell'] = MT.make('sv_bell', (0.27, 0.26, 0.25), 0.85, 0.62, var=0.2, edge=((0.66, 0.64, 0.60), 1.0, 0.3, 1.0), edge_width=0.0022, dirt=DIRT,
                       rust=((0.34, 0.17, 0.08), 0.6), bumps=[('stipple', 1800, 0.55), ('noise', 320, 0.6), ('noise', 90, 0.5)], grime=0.7,
                       tone2=((0.37, 0.34, 0.31), 240, 0.42, 0.6, 0.6))
sv.add_cavity(M['sv_bell'], (0.33, 0.16, 0.07), 0.9)          # brown rust in the recesses and round the bolt heads
sv.add_patch(M['sv_bell'], P(42, 14, 46), 0.020, SOOT[0], SOOT[1], 0.0, noise_scale=210, soft=0.5, inner=0.05, amount=0.85)
sv.add_dust(M['sv_bell'], DUST, cav=1.9, veil=0.04, up=1.5)
# the torn leads outside the case: old, dull, dusty
for nm, col in (('xwire_red', (0.30, 0.075, 0.055)), ('xwire_blue', (0.085, 0.12, 0.24)), ('xwire_yellow', (0.47, 0.38, 0.13))):
    M[nm] = MT.make(nm, col, 0.0, 0.8, var=0.16, dirt=(DUST, 0.95, 1.0), grime=0.9, bumps=[('noise', 900, 0.35)], tone2=((0.44, 0.37, 0.28), 260, 0.42, 0.62, 0.55))
    sv.add_dust(M[nm], DUST, veil=0.3, cav=1.6, up=1.3)
M['sv_cast'] = MT.make('sv_cast', (0.40, 0.395, 0.38), 1.0, 0.58, var=0.09, edge=((0.70, 0.69, 0.66), 1.0, 0.26, 0.9), dirt=((0.20, 0.16, 0.11), 0.9, 1.0),
                       bumps=[('stipple', 2400, 0.3), ('noise', 500, 0.25)], grime=0.85, tone2=((0.50, 0.42, 0.31), 55, 0.5, 0.7, 0.45))
sv.add_patch(M['sv_cast'], P(36, 12, 34), 0.026, (0.035, 0.03, 0.027), 0.95, 0.0, noise_scale=200, soft=0.7)       # soot from the burnt board
M['sv_spring'] = MT.make('sv_spring', (0.24, 0.24, 0.25), 1.0, 0.42, edge=((0.62, 0.61, 0.6), 1.0, 0.24, 1.0), dirt=DIRT,
                         rust=((0.36, 0.18, 0.08), 0.3), bumps=[('noise', 1100, 0.18)])
sv.add_dust(M['sv_spring'], DUST, veil=0.03, cav=1.6, up=1.4)
M['sv_brass'] = MT.make('sv_brass', (0.74, 0.58, 0.33), 1.0, 0.36, var=0.08, edge=((0.93, 0.80, 0.55), 1.0, 0.2, 0.8),
                        dirt=((0.20, 0.15, 0.08), 0.7, 0.8))
sv.add_dust(M['sv_brass'], DUST, cav=2.0, veil=0.1, up=1.5)
M['sv_plate'] = MT.make('sv_plate', (0.50, 0.42, 0.27), 1.0, 0.44, var=0.12, edge=((0.86, 0.76, 0.52), 1.0, 0.25, 0.9), dirt=DIRT,
                        bumps=[('lathe', 'Y', 1500, 0.9), ('brushed', (14, 1, 1), 0.25)], tone2=((0.16, 0.13, 0.09), 900, 0.5, 0.6, 0.5))
sv.add_dust(M['sv_plate'], DUST, veil=0.06, cav=1.6, up=1.5)
M['pcb'] = MT.make('pcb', (0.075, 0.105, 0.065), 0.0, 0.46, var=0.06, edge=((0.46, 0.38, 0.22), 0.0, 0.6, 0.6), dirt=DIRT,
                   bumps=[('brushed', (22, 1, 1), 0.5), ('noise', 1800, 0.2)], tone2=((0.13, 0.17, 0.09), 1700, 0.52, 0.6, 0.55), grime=0.5)
M['char'] = MT.make('char', (0.028, 0.024, 0.022), 0.0, 0.92, var=0.2, bumps=[('noise', 500, 1.2), ('stipple', 1400, 0.6)])
M['phenolic'] = MT.make('phenolic', (0.34, 0.20, 0.11), 0.0, 0.45, var=0.1, edge=((0.5, 0.36, 0.22), 0.0, 0.6, 0.6), dirt=DIRT)
M['copper_enamel'] = MT.make('copper_enamel', (0.56, 0.25, 0.13), 1.0, 0.36, var=0.14, edge=((0.86, 0.52, 0.34), 1.0, 0.22, 0.7), edge_width=0.0003,
                             dirt=((0.10, 0.06, 0.04), 0.8, 1.0), grime=0.3, bevel_r=0.0002)
M['gim_alloy'] = MT.make('gim_alloy', (0.52, 0.51, 0.49), 1.0, 0.38, var=0.06, edge=((0.78, 0.77, 0.74), 1.0, 0.2, 0.9), dirt=DIRT,
                         bumps=[('lathe', 'Z', 1100, 0.05), ('noise', 1200, 0.15)])
sv.add_tarnish(M['gim_alloy'], (0.20, 0.175, 0.14), 0.9, amount=0.9, base=0.22, cav=1.1, patch=0.35, scale=260.0)
M['gim_steel'] = MT.make('gim_steel', (0.58, 0.57, 0.55), 1.0, 0.26, var=0.04, edge=((0.8, 0.8, 0.78), 1.0, 0.15, 0.6), dirt=DIRT,
                         bumps=[('lathe', 'Z', 1200, 0.1)])
sv.add_tarnish(M['gim_steel'], (0.30, 0.135, 0.06), 0.93, amount=1.0, base=0.12, cav=1.0, patch=1.1, scale=300.0, pit=0.5, bump=1.2)
M['gim_brass'] = MT.make('gim_brass', (0.78, 0.61, 0.36), 1.0, 0.3, var=0.06, edge=((0.93, 0.80, 0.55), 1.0, 0.2, 0.8),
                         dirt=((0.20, 0.15, 0.08), 0.7, 0.6), bumps=[('lathe', 'Z', 1000, 0.12)])
M['magnet'] = MT.make('magnet', (0.10, 0.10, 0.105), 0.6, 0.5, var=0.06, edge=((0.4, 0.4, 0.4), 1.0, 0.3, 0.6), dirt=DIRT)
M['grit'] = MT.make('grit', (0.30, 0.24, 0.17), 0.0, 0.95, var=0.2, bumps=[('noise', 900, 1.0)])
M['lam'] = MT.make('lam', (0.27, 0.265, 0.26), 0.9, 0.46, var=0.06, edge=((0.6, 0.59, 0.57), 1.0, 0.26, 0.9), dirt=DIRT,
                   rust=((0.36, 0.18, 0.08), 0.25), bumps=[('lathe', 'Z', 2600, 0.55)])
M['wire_red'] = MT.make('wire_red', (0.36, 0.055, 0.04), 0.0, 0.6, var=0.14, dirt=((0.42, 0.35, 0.27), 0.9, 0.6), grime=0.6, bumps=[('noise', 900, 0.25)])
for nm, col in (('wire_bone', (0.56, 0.50, 0.38)), ('wire_blue', (0.07, 0.15, 0.40)), ('wire_yellow', (0.72, 0.55, 0.08)),
                ('band_pale', (0.80, 0.76, 0.64)), ('band_yellow', (0.80, 0.62, 0.06)), ('res_body', (0.62, 0.50, 0.33)),
                ('res_red', (0.55, 0.06, 0.04)), ('res_dark', (0.06, 0.04, 0.03)), ('res_gold', (0.70, 0.55, 0.22))):
    M[nm] = MT.make(nm, col, 0.0, 0.5, var=0.1, dirt=((0.42, 0.35, 0.27), 0.9, 0.5))
# the lid's scorched rear +Y corner, and the board's charred end (patches in object space; the origins are set below)
BOARD_O = P(8, 0, 43.2)
M['pcb_trace'] = MT.make('pcb_trace', (0.20, 0.27, 0.13), 0.0, 0.4, var=0.08, dirt=DIRT)
for nm in ('pcb', 'pcb_trace'):
    sv.add_patch(M[nm], P(35, 7, 44.5) - BOARD_O, 0.021, (0.03, 0.026, 0.022), 0.93, 0.0, noise_scale=300, soft=0.5, bump=2.5 if nm == 'pcb' else 0.0)


def remat(o, mat, test):
    """Give the faces that pass test(world centre, world normal) another material."""
    me = o.data
    for k, m in enumerate(me.materials):        # a boolean union can leave an empty slot behind
        if m is None:
            me.materials[k] = mat
    names = [m.name for m in me.materials]
    if mat.name not in names:
        me.materials.append(mat); names.append(mat.name)
    i = names.index(mat.name)
    R = o.matrix_world.to_3x3()
    for p in me.polygons:
        if test(o.matrix_world @ p.center, R @ p.normal):
            p.material_index = i
    return o


def axis_r(c):
    return math.hypot(c.y, c.z - ZA * MM) / MM


# ====================================================================== case: the can, split at the seam
def can_tube(name, x0, x1, mat, n_st=19):
    L = x1 - x0
    prof = [(0.0, RI), (L, RI)] + [(L * (1 - i / (n_st - 1)), RO) for i in range(n_st)]
    o = G.lathe(name, [([(a * MM, b * MM) for a, b in prof], True)], 64, P(x0, 0, ZA), X, (0, 0, -1), mat)
    remat(o, M['sv_cast'], lambda c, n: axis_r(c) < RI + 0.4)
    return o


def surf(x, deg, r=RO):
    a = math.radians(deg)
    return P(x, r * math.cos(a), ZA + r * math.sin(a))


body_can = can_tube('body_can', X0, X1, M['sv_paint'])
G.boolean(body_can, [sv.box('_c', (-100, -100, SEAM), (100, 100, 200))])
sv.dent(body_can, [(surf(-6, -35), 9.0, 1.5), (surf(23, 207), 7.5, 1.1), (surf(2, -150), 5.0, 0.7)], P(0, 0, ZA), X, RO - 0.4)
lid_can = can_tube('lid_can', X0 + 0.15, X1 - 0.15, M['sv_lidpaint'])
G.boolean(lid_can, [sv.box('_c', (-100, -100, -100), (100, 100, SEAM + LIDGAP))])
LID_DENTS = [(surf(-9, 62), 10.0, 1.6), (surf(26, 118), 6.0, 0.8)]
sv.dent(lid_can, LID_DENTS, P(0, 0, ZA), X, RO - 0.4)

body_parts = [body_can]
lid_parts = [lid_can]

# end bells (cast steel), boss, seal, bolts
bf = [(0, 4.25), (0, 11.6), (0.7, 12.2), (0.7, 21.6), (0, 22.2), (0, 25.3), (1.0, 26.4), (5.8, 26.4), (6.2, 26.0), (7.0, 26.0), (7.0, 4.25)]
body_parts.append(G.lathe('bell_front', [([(a * MM, b * MM) for a, b in bf], True)], 56, P(-29.5, 0, ZA), X, Z, M['sv_bell']))
bo = [(0, 4.25), (0, 7.6), (0.6, 8.6), (3.2, 8.6), (3.6, 10.2), (5.4, 10.2), (6.0, 11.4), (6.0, 4.25)]
body_parts.append(G.lathe('boss', [([(a * MM, b * MM) for a, b in bo], True)], 40, P(-35.5, 0, ZA), X, Z, M['sv_bell']))
body_parts.append(sv.annulus('seal', P(-35.9, 0, ZA), X, 4.12, 5.7, 0.0, 0.45, 28, M['rubber'], chamfer=0.1))
br = [(0, 0), (0, 26.0), (0.8, 26.0), (1.2, 26.4), (5.0, 26.4), (6.0, 25.3), (6.0, 22.2), (5.3, 21.6), (5.3, 12.2), (6.0, 11.6), (6.0, 6.8),
      (6.5, 6.3), (8.2, 6.0), (8.2, 0)]
body_parts.append(G.lathe('bell_rear', [([(a * MM, b * MM) for a, b in br], False)], 56, P(X1, 0, ZA), X, Z, M['sv_bell']))
body_parts.append(sv.annulus('grommet', P(46.7, 0, ZA), X, 2.7, 5.2, 0.0, 0.8, 24, M['rubber'], chamfer=0.25))
for k in range(4):
    a = math.radians(45 + 90 * k)
    y, z = 17.0 * math.cos(a), ZA + 17.0 * math.sin(a)
    body_parts.append(AP.screw('bolt_f', 3 * MM, 1.5 * MM, head='hex', drive='none', head_d=5.4 * MM, head_h=1.7 * MM, mat=M['steel_dark'],
                               thread=False, point=False, at=P(-29.5 + 0.7, y, z), axis=-X, turn=0.3 * k))
    body_parts.append(AP.screw('bolt_r', 3 * MM, 1.5 * MM, head='hex', drive='none', head_d=5.4 * MM, head_h=1.7 * MM, mat=M['steel_dark'],
                               thread=False, point=False, at=P(X1 + 5.3, y, z), axis=X, turn=0.5 * k))

# seam flanges and the four screw bosses (body) and lugs (lid)
for s in (1, -1):
    bar = sv.box('flange_b', (X0, s * 25.3, 28.2), (X1, s * 31.0, SEAM), M['sv_paint'])
    lbar = sv.box('flange_l', (X0 + 0.15, s * 25.3, SEAM + LIDGAP), (X1 - 0.15, s * 31.0, FL_TOP), M['sv_lidpaint'])
    G.bevel(bar, 0.35 * MM, 1, 40); G.bevel(lbar, 0.35 * MM, 1, 40)
    mine = [xl for (xl, sl) in LUGS if sl == s]
    for xl in mine:        # one closed solid per flange: lugs and gussets are united before the holes are cut
        G.boolean(bar, [sv.vcyl('lug_b', xl, s * 30.5, 21.0, SEAM, 4.5, 20, M['sv_paint'], chamfer=0.5),
                        sv.box('gus_b', (xl - 1.4, s * 24.2, 21.5), (xl + 1.4, s * 28.6, 28.0), M['sv_paint'])], op='UNION')
        G.boolean(lbar, [sv.vcyl('lug_l', xl, s * 30.5, SEAM + LIDGAP, FL_TOP, 4.5, 20, M['sv_lidpaint'])], op='UNION')
    for xl in mine:
        G.boolean(bar, [AP.hole_cutter(3.2 * MM, 9.8 * MM, P(xl, s * 30.5, SEAM), Z, segs=14)])
        G.boolean(lbar, [G.cyl('_h', P(xl, s * 30.5, SEAM - 1), P(xl, s * 30.5, FL_TOP + 1), 1.7 * MM, 14)])
    body_parts.append(bar); lid_parts.append(lbar)

# foot with two bolt slots, saddle ribs up to the can
foot = G.plate('foot', G.rounded_rect(46 * MM, 60 * MM, 4 * MM), 3.2 * MM, P(6, 0, 0), X, Y, Z,
               slots=[(0, 23 * MM, 10 * MM, 4.6 * MM, math.pi / 2), (0, -23 * MM, 10 * MM, 4.6 * MM, math.pi / 2)], mat=M['sv_paint'], w0=0.0, bevel_w=0.5 * MM)
body_parts.append(foot)
for xr in (-9.0, 21.0):
    rib = sv.box('rib', (xr - 2.2, -19, 3.0), (xr + 2.2, 19, 12.2), M['sv_paint'])
    G.bevel(rib, 0.6 * MM, 1, 40)
    G.boolean(rib, [G.cyl('_rc', P(-40, 0, ZA), P(40, 0, ZA), (RI + 1.0) * MM, 48)])       # the saddle stays outside the can
    body_parts.append(rib)
web = sv.box('web', (-9, -6, 3.0), (21, 6, 5.5), M['sv_paint'])
G.boolean(web, [G.cyl('_rc', P(-40, 0, ZA), P(40, 0, ZA), (RI + 1.0) * MM, 48)])
body_parts.append(web)

# inside the body: deck with the gimbal well, shaft pedestal, gear post, idler, board shelves
deck = sv.box('deck', (X0, -20.3, 14.0), (X1, 20.3, DECK), M['sv_cast'])
G.boolean(deck, [sv.vcyl('_w', GX, GY, 10, 20, GD['body_r'] + 0.4, 40), sv.box('_k', (GX - 2.5, GY, 10), (GX + 2.5, GY + GD['key_r'] + 0.5, 20))])
body_parts.append(deck)
ped = sv.box('pedestal', (-16.8, -5.0, DECK), (-13.8, 5.0, 33.2), M['sv_cast'])
G.boolean(ped, [G.cyl('_pb', P(-18, 0, ZA), P(-12, 0, ZA), 3.15 * MM, 20)])
G.bevel(ped, 0.5 * MM, 1, 40)
body_parts.append(ped)
gp = [(DECK, 0), (DECK, 3.2), (17.5, 3.2), (18.0, 2.2), (33.25, 2.2), (33.25, 1.5), (41.55, 1.5), (41.55, 1.2), (42.15, 1.2), (42.15, 1.5),
      (42.5, 1.5), (42.8, 1.2), (42.8, 0)]
body_parts.append(G.lathe('gear_post', [([(a * MM, b * MM) for a, b in gp], False)], 16, P(PX, PY, 0), Z, X, M['steel_bright']))
ID_D = 8.4 + 2.4 + 0.06
IDX, IDY = PX + ID_D * math.cos(math.radians(135)), PY + ID_D * math.sin(math.radians(135))
body_parts.append(sv.vcyl('idler_post', IDX, IDY, DECK, 38.6, 1.2, 12, M['steel_bright'], chamfer=0.2))
body_parts.append(sv.vcyl('idler_foot', IDX, IDY, DECK, 17.6, 2.4, 12, M['sv_cast'], chamfer=0.3))
idler, _, ID_RT = sv.spur('idler', 8, 0.6, P(IDX, IDY, 35.35), X, Y, Z, 2.9, 1.15, M['steel'], phase=math.radians(315 + 22.5))
body_parts.append(idler)
for (xa, xb, ya, yb, px_, py_) in ((X0, -19.2, -10.0, -3.0, -20.5, -6.5), (36.3, X1, -9.0, 1.0, 37.7, -4.0)):
    sh = sv.box('shelf', (xa, ya, 40.7), (xb, yb, 43.15), M['sv_cast'])
    G.bevel(sh, 0.4 * MM, 1, 40)
    body_parts += [sh, sv.vcyl('shelf_pin', px_, py_, 43.1, 45.3, 0.8, 10, M['steel_bright'], chamfer=0.2)]

# clip hinges under the body flange: two tabs and a pin for each clip
for (xc, s) in CLIPS:
    for dx in (-4.05, 4.05):
        body_parts.append(sv.box('clip_tab', (xc + dx - 0.45, s * 28.9, 25.5), (xc + dx + 0.45, s * 31.0, 28.25), M['sv_paint']))
    body_parts.append(G.pin('clip_pin', P(xc - 4.7, s * 30.2, 26.8), P(xc + 4.7, s * 30.2, 26.8), 0.6 * MM, 10, M['steel_bright']))

# three torn outside leads through the grommet (red, blue, yellow), frayed copper at the ends
for k, (mat, pts) in enumerate((
        ('xwire_red', [(46.0, -1.3, 29.7), (50.5, -1.9, 29.6), (55.0, -4.2, 27.4), (59.0, -7.4, 23.2), (61.0, -9.6, 18.6)]),
        ('xwire_blue', [(46.0, 1.4, 29.4), (50.5, 2.0, 29.0), (55.5, 3.6, 26.2), (59.5, 5.0, 21.4), (61.5, 5.6, 16.0)]),
        ('xwire_yellow', [(46.0, 0.1, 27.6), (50.0, 0.2, 26.8), (54.0, -0.6, 23.6), (56.6, -1.6, 18.8), (57.6, -2.4, 13.6)]))):
    pp = [P(*q) for q in pts]
    body_parts.append(sv.tube('xlead', pp, 2.1 * MM, M[mat], segs=8, smooth=2, n=12))
    d = (pp[-1] - pp[-2]).normalized()
    body_parts.append(sv.tube('xcore', [pp[-1] - d * (0.5 * MM), pp[-1] + d * (2.6 * MM)], 1.0 * MM, M['copper'], segs=6, smooth=0))
    side = d.cross(X).normalized()
    for j, (a, b) in enumerate(((0.9, 0.5), (-0.7, 0.8), (0.1, -0.9))):
        e = pp[-1] + d * (2.4 * MM)
        body_parts.append(sv.tube('xstrand', [e, e + d * (1.4 * MM) + side * (a * 0.5 * MM) + d.cross(side) * (b * 0.5 * MM),
                                               e + d * (3.0 * MM) + side * (a * 1.4 * MM) + d.cross(side) * (b * 1.4 * MM)], 0.32 * MM, M['copper'], segs=4, smooth=0))

case_body = G.join('case_body', body_parts)
G.shade(case_body, 38)
CT.part(case_body, FAM, 'case_body', 'Servo case body', kind='part', material='alloy', mass='medium', loose=True, item='droid_servo_damaged',
        steps=['s0.salvage', 's2.swap', 's2.dust'], origin=(0, 0, 0))

# lid: ribs, data plate with rivets
for xr in (-12.0, 8.0, 28.0):
    rib = G.lathe('lid_rib', [([(a * MM, b * MM) for a, b in ((-1.7, RO - 0.2), (1.7, RO - 0.2), (1.0, RO + 0.32), (-1.0, RO + 0.32))], True)], 40,
                  P(xr, 0, ZA), X, (0, 0, -1), M['sv_lidpaint'], arc=(math.radians(180 - 62), math.radians(180 + 62)))
    G.fill_holes(rib)
    sv.dent(rib, LID_DENTS, P(0, 0, ZA), X, 1.0)
    lid_parts.append(rib)
PL_A = math.asin(4.6 / RO)
sec = [(-(RO + 0.04) * MM * math.sin(a), (RO + 0.04) * MM * math.cos(a)) for a in [PL_A * (2 * k / 6 - 1) for k in range(7)]] + \
      [(-(RO + 0.30) * MM * math.sin(a), (RO + 0.30) * MM * math.cos(a)) for a in [PL_A * (1 - 2 * k / 6) for k in range(7)]]
dp = G.prism('data_plate', sec, 15 * MM, P(-9.0, 0, ZA), Y, Z, X, M['sv_plate'], w0=0.0)
lid_parts.append(dp)
for sx in (-1, 1):
    for sy in (-1, 1):
        yy = sy * 3.3
        zz = ZA + math.sqrt((RO + 0.30) ** 2 - yy ** 2)
        lid_parts.append(AP.rivet('plate_rivet', 1.1 * MM, mat=M['sv_brass'], segs=8, at=P(-1.5 + sx * 6.2, yy, zz), axis=Vector((0, yy, RO)).normalized()))
case_lid = G.join('case_lid', lid_parts)
G.shade(case_lid, 38)
CT.part(case_lid, FAM, 'case_lid', 'Servo case lid', parent='case_body', material='plastic', mass='light',
        held_by=['screw_case_a', 'screw_case_b', 'screw_case_c', 'screw_case_d', 'clip_1', 'clip_2', 'clip_3'], steps=['s2.dust', 's2.pry'],
        origin=LID_O, touches=['board'])
CT.clear(case_lid, offset=P(0, 0, 48))
CT.zone(case_lid, 'dust', P(8, 0, 44), P(32, 31, 13))
CT.wipe(case_lid, 'dust', zone='dust', label='Caked Berms dust')
CT.zone(case_body, 'dust_l', P(8, -30, 18), P(32, 7, 16))
CT.zone(case_body, 'dust_r', P(8, 30, 18), P(32, 7, 16))
CT.zone(case_body, 'dust_front', P(-34, 0, 29), P(13, 28, 28))
CT.zone(case_body, 'dust_rear', P(42, 0, 29), P(6, 28, 28))
CT.wipe(case_body, 'dust', zone='dust_l', label='Caked Berms dust')
F.notes['dust_also_on'] = 'clips and case screws share the as-found set; they are wiped with the lid and body zones'

# ====================================================================== clips
clips = []
for i, (xc, s) in enumerate(CLIPS):
    def yz(y, z):
        return P(xc, s * y, z)
    # a formed spring-steel latch: a bow in the upright, a flat that bears on the lid flange, a rolled finger lip
    strap = G.band_path('clip_strap', [yz(31.25, 26.4), yz(31.68, 27.3), yz(31.8, 28.4), yz(32.2, 29.6), yz(32.4, 30.8), yz(32.25, 32.0), yz(31.85, 33.0),
                                       yz(31.5, 33.7), yz(30.9, 33.95), yz(27.9, 33.95), yz(27.45, 34.1), yz(27.15, 34.5), yz(27.2, 34.95), yz(27.5, 35.2), yz(27.9, 35.15)],
                        7.0 * MM, 0.7 * MM, lambda p, t: Vector((0, s * t.z, -s * t.y)), M['sv_spring'], closed=False, offset=-0.35 * MM)
    tail = G.band_path('clip_tail', [yz(30.75, 25.85), yz(31.35, 24.5), yz(32.25, 22.9)], 7.0 * MM, 0.7 * MM, lambda p, t: Vector((0, s, 0)),
                       M['sv_spring'], closed=False, offset=-0.35 * MM)
    knuckle = sv.annulus('clip_knuckle', P(xc - 3.5, s * 30.2, 26.8), X, 0.7, 1.4, 0.0, 7.0, 12, M['sv_spring'])
    c = G.join('clip', [strap, tail, knuckle])
    G.shade(c, 40)
    CT.part(c, FAM, 'clip_%d' % (i + 1), 'Case spring clip %d' % (i + 1), parent='case_body', material='steel', mass='tiny', loose=True,
            steps=['s2.pry'], origin=P(xc, s * 30.2, 26.8), touches=['case_lid'])
    CT.grab(c, P(xc, s * 31.9, 23.6))
    CT.wipe(c, 'dust', zone=None, label='Dust')
    CT.mark(case_body, 'pry_%d' % (i + 1), P(xc, s * 32.3, 23.2), (0, s, -0.3))
    clips.append(c)

# ====================================================================== case screws (brass M3 x 10, cross; d is chewed)
case_screws = []
for k, (xl, s) in zip('abcd', LUGS):
    scr = AP.screw('scr', 3 * MM, 10 * MM, head='pan', drive='cross', head_d=5.6 * MM, head_h=2.2 * MM, mat=M['sv_brass'],
                   at=P(xl, s * 30.5, FL_TOP + 0.05), axis=Z, turn=0.4 + 0.7 * ord(k))
    if k == 'd':        # chewed: the recess is reamed out to a ragged crater
        G.transform_obj(scr, Matrix.Identity(4))
        crater = G.lathe('_cr', [([(0.3 * MM, 0), (0.3 * MM, 1.5 * MM), (-0.9 * MM, 0.5 * MM), (-1.0 * MM, 0)], False)], 7, Vector((0, 0, 2.2 * MM)), Z, X)
        crater.matrix_world = scr.matrix_world
        G.boolean(scr, [crater])
        G.shade(scr, 38)
    CT.fastener(scr, FAM, 'screw_case_' + k, 'Case screw ' + k.upper() + (' (chewed head)' if k == 'd' else ''), bit='pliers' if k == 'd' else 'cross',
                turns=10, holds=['case_lid'], into='case_body', shank_d=3 * MM, parent='case_body', material='steel',
                steps=(['s2.stripped'] if k == 'd' else ['s2.screws']) + ['s5.start', 's5.torque'])
    CT.clear_along(scr, 14 * MM)
    CT.wipe(scr, 'dust', zone=None, label='Dust in the recess')
    case_screws.append(scr)

# ====================================================================== output shaft with its two pinions
sp = [(1.3, 0), (1.3, 3.0), (8.8, 3.0), (8.8, 5.2), (9.8, 5.2), (9.8, 4.0), (25.0, 4.0), (25.0, 3.0), (37.1, 3.0), (37.3, 2.7), (37.3, 0)]
shaft = G.lathe('shaft', [([(a * MM, b * MM) for a, b in sp], False)], 20, P(-47.5, 0, ZA), X, Z, M['steel_bright'])
pin_out, _, PO_RT = sv.spur('pinion_out', 14, 1.0, P(-46.2, 0, ZA), Y, Z, X, 7.5, 2.9, M['steel'], chew={2: 0.72, 3: 0.5, 4: 0.8, 9: 0.75, 10: 0.6})
pin_in, _, PI_RT = sv.spur('pinion_in', 12, 0.6, P(PX - 7.2, 0, ZA), Y, Z, X, 2.4, 1.0, M['steel'], phase=math.radians(90))
washer = AP.washer('shaft_washer', 3.0 * MM, 7.4 * MM, 0.4 * MM, M['steel_dark'], segs=14, at=P(-46.2, 0, ZA), axis=-X)
endscr = AP.screw('shaft_screw', 2.5 * MM, 1.0 * MM, head='pan', drive='slot', head_d=4.6 * MM, head_h=0.9 * MM, mat=M['steel_dark'], thread=False,
                  point=False, at=P(-46.6, 0, ZA), axis=-X, turn=0.6)
output_shaft = G.join('output_shaft', [shaft, pin_out, pin_in, washer, endscr])
G.shade(output_shaft, 38)
CT.part(output_shaft, FAM, 'output_shaft', 'Output shaft and pinion', parent='case_body', material='steel', mass='light', loose=True,
        origin=P(-47.5, 0, ZA), touches=['gear_low', 'case_lid'])

# ====================================================================== stator and its winding
core = sv.annulus('stator_core', P(GX, GY, 0), Z, 15.5, 18.3, STAT_Z0, STAT_Z1, 48, M['lam'], chamfer=0.25)
SCREW_W = [math.degrees(math.atan2(-math.sin(math.radians(a)), -math.cos(math.radians(a)))) for a in GD['screw_deg']]      # world angles of the two screws
holes = []
for deg in SCREW_W:
    a = math.radians(deg)
    blk = G.lathe('stator_block', [([(DECK * MM + 0.05 * MM, 13.4 * MM), (BLOCK_TOP * MM, 13.4 * MM), (BLOCK_TOP * MM, 18.9 * MM), (DECK * MM + 0.05 * MM, 18.9 * MM)], True)],
                  6, P(GX, GY, 0), Z, X, M['sv_cast'], arc=(a - 0.2, a + 0.2))
    G.fill_holes(blk)
    G.boolean(core, [blk], op='UNION')          # one closed solid, so the screw holes have one wall
    holes.append(P(GX + GD['screw_at'] * math.cos(a), GY + GD['screw_at'] * math.sin(a), BLOCK_TOP))
for c in holes:
    G.boolean(core, [AP.hole_cutter(2.7 * MM, 8.6 * MM, c, Z, segs=12)])
remat(core, M['sv_cast'], lambda c, n: (c.z > (STAT_Z1 + 0.1) * MM or c.z < (STAT_Z0 - 0.1) * MM or math.hypot(c.x - GX * MM, c.y - GY * MM) > 18.4 * MM or math.hypot(c.x - GX * MM, c.y - GY * MM) < 15.4 * MM))
stator = G.join('stator', [core])
G.shade(stator, 38)
CT.part(stator, FAM, 'stator', 'Stator', parent='case_body', material='steel', mass='light', loose=True, steps=['s2.winding'], origin=P(GX, GY, DECK))
w = []
gapa = math.radians(17)
a0_, a1_ = sorted(round(x, 6) % 360.0 for x in SCREW_W)
for (d0, d1) in ((a0_, a1_), (a1_, a0_ + 360.0)):
    w.append(sv.torus_wrap('wind', P(GX, GY, (STAT_Z0 + STAT_Z1) / 2), 16.9, 1.4 + 0.75, 3.0 + 0.75, math.radians(d0) + gapa, math.radians(d1) - gapa, 30, 0.28, M['copper_enamel'], corner=0.9, sec=2))
winding = G.join('stator_winding', w)
CT.part(winding, FAM, 'stator_winding', 'Stator winding (copper)', parent='stator', material='copper', mass='light', loose=True, flex=True,
        steps=['s2.winding'], origin=P(GX, GY, DECK))
CT.mark(winding, 'end', P(GX + 16.9 * math.cos(math.radians(SCREW_W[0] + 19)), GY + 16.9 * math.sin(math.radians(SCREW_W[0] + 19)), STAT_Z1 + 0.8), Z)

# ====================================================================== gears on the post, and the circlip
gear_low = sv.crown('gear_low', 20, P(PX, PY, 0), 4.8, 7.2, 7.2, 33.3, 1.8, 0.5, 1.6, M['brass'], phase=math.pi + math.pi / 20, chew={6: 0.5, 7: 0.3, 13: 0.6})
CT.part(gear_low, FAM, 'gear_low', 'Crown gear (low)', parent='case_body', material='steel', mass='tiny', symmetry=0, held_by=['gear_mid'],
        steps=['s2.gears'], origin=P(PX, PY, 33.3), touches=['output_shaft'])
gear_mid, _, GM_RT = sv.spur('gear_mid', 28, 0.6, P(PX, PY, 35.3), X, Y, Z, 3.0, 1.6, M['steel_dark'], phase=math.radians(135),
                             chew={5: 0.6, 6: 0.34, 7: 0.2, 8: 0.16, 9: 0.24, 10: 0.5, 19: 0.72}, holes=[(5.0, 1.5, 5)], hub=(3.0, 0.22))
CT.part(gear_mid, FAM, 'gear_mid', 'Reduction gear (stripped teeth)', parent='case_body', material='steel', mass='tiny', symmetry=0,
        held_by=['gear_top'], steps=['s2.gears'], origin=P(PX, PY, 35.3), touches=['gear_low'])
gear_top, _, GT_RT = sv.spur('gear_top', 12, 0.6, P(PX, PY, 38.6), X, Y, Z, 2.8, 1.6, M['brass'], phase=math.radians(90), chew={3: 0.5, 4: 0.36, 8: 0.7})
CT.part(gear_top, FAM, 'gear_top', 'Feedback gear (top)', parent='case_body', material='steel', mass='tiny', symmetry=0, held_by=['circlip'],
        steps=['s2.gears'], origin=P(PX, PY, 38.6), touches=['gear_mid', 'board'])
for g in (gear_low, gear_mid, gear_top):
    CT.clear(g, offset=P(0, 0, 36))
circlip = AP.circlip('circlip', 2.4 * MM, 1.25 * MM, 0.5 * MM, mat=M['steel_blued'], segs=18, at=P(PX, PY, 41.6), axis=Z, ref=-X)
CT.part(circlip, FAM, 'circlip', 'Gear post circlip', parent='case_body', material='steel', mass='tiny', flex=True, steps=['s2.circlip'],
        touches=['gear_top'], note='sprung open with pliers: not a rigid removal')
CT.clear(circlip, offset=P(0, 0, 14))

# ====================================================================== control board, pot, trim resistor
outline = [(-22, -11), (-20, -13), (36.5, -13), (38, -11.5), (38, 3.0), (36.6, 4.2), (35.9, 6.1), (34.3, 6.9), (33.6, 8.8), (32.0, 9.6),
           (31.3, 11.6), (29.8, 13.0), (-20, 13), (-22, 11)]
pcb = G.plate('pcb', [(x * MM, y * MM) for x, y in outline], 1.6 * MM, P(0, 0, 43.2), X, Y, Z,
              holes=[(-20.5 * MM, -6.5 * MM, 0.95 * MM), (37.7 * MM, -4.0 * MM, 1.0 * MM)], mat=M['pcb'], w0=0.0, hole_segs=10)
bp = [pcb]
BT = 44.8
bp.append(sv.box('hdr_base', (-18.2, -9.6, BT), (-15.8, -2.4, BT + 1.2), M['polymer']))
HDR_Y = (-8.5, -6.0, -3.5)
for y in HDR_Y:
    bp.append(sv.box('hdr_pin', (-17.3, y - 0.3, BT), (-16.7, y + 0.3, BT + 3.4), M['brass']))
chip = sv.box('chip', (-0.5, -6.0, BT + 0.25), (4.5, -2.0, BT + 1.75), M['polymer'])
G.bevel(chip, 0.2 * MM, 1, 40)
bp.append(chip)
for sy in (-1, 1):
    bp.append(sv.box('chip_legs', (0.0, -4.0 + sy * 2.0 - 0.45, BT), (4.0, -4.0 + sy * 2.0 + 0.45, BT + 0.55), M['solder']))
bp.append(sv.vcyl('cap_a', -9.0, 6.5, BT, BT + 4.6, 2.1, 14, M['alloy'], chamfer=0.3))
bp.append(sv.vcyl('cap_a_base', -9.0, 6.5, BT, BT + 0.6, 2.2, 14, M['polymer']))
capb = sv.vcyl('cap_b', 22.0, -6.0, BT, BT + 4.0, 2.6, 14, M['char'], chamfer=0.3)
G.displace(capb, lambda c: Vector((c.x + (0.5 * MM if c.z > (BT + 3) * MM else 0), c.y, c.z + (0.5 * MM if (c.z > (BT + 3.5) * MM and c.x > 22 * MM) else 0))))
bp.append(capb)
tr = sv.box('transistor', (25.0, 1.0, BT + 0.2), (31.5, 7.0, BT + 2.1), M['char'])
G.bevel(tr, 0.3 * MM, 1, 40)
bp.append(tr)
bp.append(sv.box('heatsink', (24.0, 0.2, BT), (32.0, 7.6, BT + 0.25), M['alloy']))
for (x, y, sx, sy) in ((-12, -1, 2.0, 1.2), (-6, -9, 1.2, 2.0), (6, -9.5, 2.0, 1.2), (12, -8, 1.2, 2.0), (17, 0.5, 2.0, 1.2), (-3, 9, 1.2, 2.0),
                       (16, 9.5, 2.0, 1.2), (-14, 9, 2.0, 1.2)):
    bp.append(sv.box('smd', (x - sx / 2, y - sy / 2, BT), (x + sx / 2, y + sy / 2, BT + 0.8), M['polymer'] if (x + y) % 2 else M['res_body']))
# more of a board: a second chip, a row of test pads, diodes, traces as thin lands, a crystal can
chip2 = sv.box('chip2', (12.0, -10.5, BT + 0.2), (17.0, -6.5, BT + 1.4), M['polymer'])
G.bevel(chip2, 0.2 * MM, 1, 40)
bp.append(chip2)
for sy in (-1, 1):
    bp.append(sv.box('chip2_legs', (12.4, -8.5 + sy * 2.0 - 0.4, BT), (16.6, -8.5 + sy * 2.0 + 0.4, BT + 0.5), M['solder']))
bp.append(sv.box('crystal', (-2.5, 4.5, BT), (2.5, 7.3, BT + 1.6), M['alloy']))
for k in range(6):
    bp.append(sv.vcyl('testpad', -13.0 + 2.0 * k, -11.3, BT - 0.02, BT + 0.12, 0.6, 8, M['solder']))
for (x, y, ln, ang) in ((-4, -1.5, 9, 0), (8, 0.8, 12, 0), (5, -7.5, 6, 90), (-10, 2, 7, 90), (19, 5, 8, 0), (20, -2.5, 9, 0), (-15, -1, 5, 90), (9, 9.5, 10, 0), (-6, 10.5, 12, 0)):
    dx, dy = (ln / 2, 0.22) if ang == 0 else (0.22, ln / 2)
    bp.append(sv.box('trace', (x - dx, y - dy, BT - 0.02), (x + dx, y + dy, BT + 0.05), M['pcb_trace']))
for (x, y) in ((7.0, -3.2), (9.2, -3.2), (-12.5, 5.5), (18.5, 9.0), (21.0, 9.0), (-17.0, 6.0)):
    bp.append(G.cyl('diode', P(x, y - 1.3, BT + 0.55), P(x, y + 1.3, BT + 0.55), 0.55 * MM, 8, M['res_dark'], chamfer=0.1 * MM))
# charred crust near the bite
for (x, y, r) in ((33.0, 4.0, 2.6), (30.5, 9.0, 2.2), (35.5, -1.0, 1.9), (27.5, 10.5, 1.5), (34.5, -6.5, 1.4), (29.0, 5.5, 1.3)):
    bl = G.lathe('crust', [([(0, 0), (0, r * MM), (0.5 * r * MM, 0.8 * r * MM), (0.8 * r * MM, 0.4 * r * MM), (0.9 * r * MM, 0)], False)], 7, P(x, y, BT - 0.05), Z, X, M['char'], phase=x)
    G.displace(bl, lambda c, x0=x * MM, z0=(BT - 0.05) * MM: Vector((x0 + (c.x - x0) * (1 + 0.25 * math.sin(c.y * 2100)), c.y, z0 + (c.z - z0) * (1 + 0.3 * math.sin(c.x * 1700)))))
    bp.append(bl)
# trim resistor's pads and the stubs of its legs
RX0, RX1, RY, RZ = 4.8, 15.2, 5.0, BT + 1.9
for x in (RX0, RX1):
    bp.append(AP.solder_blob('pad', 2.0 * MM, 0.55 * MM, M['solder'], at=P(x, RY, BT), axis=Z))
    bp.append(sv.vcyl('leg_stub', x, RY, BT + 0.3, BT + 0.7, 0.3, 6, M['solder']))
# feedback pot and its pinion under the board, meshing the top gear
POT_D = 3.6 + 3.6 + 0.06
POTX, POTY = PX, PY + POT_D
bp.append(sv.vcyl('pot_body', POTX, POTY, 42.2, 43.2, 3.0, 16, M['polymer'], chamfer=0.2))
bp.append(sv.vcyl('pot_spindle', POTX, POTY, 38.7, 42.25, 0.8, 8, M['steel_bright']))
potg, _, _ = sv.spur('pot_pinion', 12, 0.6, P(POTX, POTY, 38.7), X, Y, Z, 2.6, 0.75, M['brass'], phase=math.radians(270 + 15))
bp.append(potg)
board = G.join('board', bp)
G.shade(board, 38)
CT.part(board, FAM, 'board', 'Burnt control board', parent='case_body', material='plastic', mass='light', held_by=['case_lid'],
        steps=['s2.board'], origin=BOARD_O, touches=['gear_top'])
CT.clear(board, offset=P(0, 0, 32))
CT.mark(board, 'snip_r1', P(RX0, RY, BT + 0.7), Z)
CT.mark(board, 'snip_r2', P(RX1, RY, BT + 0.7), Z)

rb = [(0, 0), (0, 0.85), (0.5, 1.2), (5.7, 1.2), (6.2, 0.85), (6.2, 0)]
res = [G.lathe('res_body', [([(a * MM, b * MM) for a, b in rb], False)], 14, P(6.9, RY, RZ), X, Z, M['res_body'])]
for (x, mat) in ((8.2, 'res_dark'), (9.5, 'res_red'), (10.8, 'res_red'), (12.3, 'res_gold')):
    res.append(sv.annulus('res_band', P(x - 0.35, RY, RZ), X, 1.19, 1.27, 0.0, 0.7, 14, M[mat]))
for (xe, xp, sgn) in ((6.9, RX0, -1), (13.1, RX1, 1)):
    res.append(sv.tube('res_leg', [P(xe - sgn * 0.2, RY, RZ), P(xe + sgn * 1.2, RY, RZ), P(xp - sgn * 0.25, RY, RZ - 0.15), P(xp, RY, RZ - 0.7), P(xp, RY, BT + 0.75)],
                       0.6 * MM, M['solder'], segs=6, smooth=1))
resistor = G.join('trim_resistor', res)
G.shade(resistor, 40)
CT.part(resistor, FAM, 'trim_resistor', 'Trim resistor', parent='board', material='ceramic', mass='tiny', symmetry=2, steps=['s2.board', 's3.tin', 's3.loop'],
        origin=P(10, RY, RZ))
CT.clear(resistor, offset=P(0, 0, 12))

# ====================================================================== the gimbal unit (gimbal.py, grip/INTERFACE.md)
C = P(GX, GY, GZ)
g = GM.build(M, MD, GD)
cradle = g['cradle']
UP = 26.0          # how far the unit is lifted to clear the servo
CT.part(cradle, FAM, 'gimbal_cradle', 'Gimbal cradle', parent='case_body', material='alloy', mass='light', symmetry=1,
        held_by=['screw_trunnion_a', 'screw_trunnion_b'], steps=['s2.trunnion', 's3.bath', 's3.oil', 's4.flash', 's4.pressfit'], origin=C,
        touches=['stator', 'stator_winding'])
CT.clear(cradle, offset=P(0, 0, UP + 22))
CT.part(g['coil'], FAM, 'gimbal_coil', 'Damping coil', parent='gimbal_cradle', material='copper', mass='tiny', loose=True, steps=['s3.test'], origin=C)
CT.part(g['ring'], FAM, 'gimbal_ring', 'Gimbal ring', parent='gimbal_cradle', material='steel', mass='tiny', loose=True, steps=['s3.brush', 's3.oil'], origin=g['pivot'])
CT.part(g['race'], FAM, 'gimbal_race', 'Bearing race', parent='gimbal_cradle', material='steel', mass='tiny', loose=True, steps=['s3.brush', 's3.pick'], origin=g['pivot'])
CT.part(g['rotor'], FAM, 'gimbal_rotor', 'Rotor (the swinging mass)', parent='gimbal_cradle', material='steel', mass='light', symmetry=0,
        held_by=['gimbal_retainer'], steps=['s3.spin', 's5.rotor', 's5.damp'], origin=g['rotor_seat'], touches=['gimbal_coil', 'gimbal_race'])
CT.clear(g['rotor'], offset=g['axes']['z'] * (30 * MM))
CT.part(g['retainer'], FAM, 'gimbal_retainer', 'Rotor retaining ring', parent='gimbal_cradle', material='steel', mass='tiny', flex=True, steps=['s5.rotor'],
        origin=g['retainer_seat'], touches=['gimbal_rotor', 'gimbal_race'], note='sprung in with pliers: not a rigid removal')
CT.clear(g['retainer'], offset=g['axes']['z'] * (12 * MM))
for k, gr in enumerate(g['grit']):
    CT.part(gr, FAM, 'gimbal_grit_%d' % (k + 1), 'Grit in detent %d' % (k + 1), parent='gimbal_cradle', kind='consumable', material='ceramic', mass='tiny',
            loose=True, steps=['s3.pick'], origin=g['detents'][k])
    CT.mark(g['race'], 'detent_%d' % (k + 1), g['detents'][k], Z)
for k, e in zip('ab', g['trunnions']):
    CT.mark(cradle, 'oil_' + k, e, Z)
    CT.zone(cradle, 'trunnion_' + k, e, P(2.4, 2.6, 3.2))
for k, nn in zip('ab', g['notch']):
    CT.mark(cradle, 'probe_' + k, nn['in'] + Z * (1.0 * MM), Z)
CT.zone(g['race'], 'race', g['pivot'] + Z * (0.4 * MM), P(10.8, 10.8, 3.4))
CT.wipe(g['race'], 'corrosion', zone='race', label='Corrosion on the race')
CT.wipe(g['ring'], 'corrosion', zone=None, label='Corrosion on the ring and trunnions')
CT.wipe(cradle, 'corrosion', zone='trunnion_a', label='Corrosion at the trunnions')

# the two trunnion screws: M2.5 x 10, a wide cheese head over the flange rim beside each trunnion, shank in a scallop
# of the rim, threaded into the stator's blocks
tscrews = []
for k, c in zip('ab', g['screws']):
    scr = AP.screw('tscr', 2.5 * MM, 10 * MM, head='cheese', drive='cross', head_d=6.0 * MM, head_h=1.5 * MM, mat=M['steel_blued'],
                   at=c + Z * (0.05 * MM), axis=Z, turn=0.9 if k == 'a' else 0.2)
    CT.fastener(scr, FAM, 'screw_trunnion_' + k, 'Trunnion screw ' + k.upper(), bit='cross', turns=8, holds=['gimbal_cradle'], into='stator',
                shank_d=2.5 * MM, parent='case_body', material='steel', steps=['s2.trunnion'])
    CT.clear_along(scr, 14 * MM)
    tscrews.append(scr)

# ====================================================================== the three leads, their plug, cut at the bands
NA, NB = sorted(g['notch'], key=lambda n: n['rim'].x)          # the notch nearer the front takes lead a
SN = g['sense']
WIRES = {
    'a': ('wire_red', 'band_pale', 1.6, [NA['in'], NA['rim'], NA['rim'] + NA['dir'] * (4.4 * MM) + Z * (0.05 * MM), P(0.0, -17.8, 28.9), P(-3.5, -20.4, 29.2), P(-6.5, -20.4, 31.0),
                                         P(-8.6, -19.4, 35.0), P(-10.2, -17.4, 40.0), P(-11.4, -15.8, 43.2), P(-12.0, -14.0, 45.8), P(-12.6, -10.6, 47.4), P(-13.6, HDR_Y[0], 47.7), P(-14.7, HDR_Y[0], 47.7)]),
    'b': ('wire_red', 'band_pale', 1.6, [NB['in'], NB['rim'], NB['rim'] + NB['dir'] * (3.6 * MM) + Z * (0.2 * MM), P(30.8, -16.4, 29.8), P(27.0, -19.6, 30.8), P(18.0, -21.0, 31.1), P(6.0, -21.2, 31.2),
                                         P(-2.0, -20.8, 31.6), P(-5.6, -19.8, 35.6), P(-8.4, -17.6, 40.8), P(-9.6, -16.0, 43.6), P(-10.4, -13.8, 46.2), P(-11.6, -9.0, 47.7), P(-13.2, HDR_Y[1], 47.7), P(-14.7, HDR_Y[1], 47.7)]),
    's': ('wire_bone', 'band_yellow', 1.2, [SN['in'], SN['rim'], SN['rim'] + SN['dir'] * (1.0 * MM), P(16.2, -18.8, 30.9), P(12.0, -20.6, 33.0), P(4.0, -20.9, 33.4), P(-1.5, -20.4, 33.8),
                                            P(-4.4, -19.4, 37.2), P(-6.4, -17.6, 41.2), P(-7.6, -16.2, 43.8), P(-8.6, -13.6, 46.4), P(-10.4, -7.0, 47.8), P(-12.6, HDR_Y[2], 47.7), P(-14.7, HDR_Y[2], 47.7)]),
}
LEAD_D = 1.6 * MM
plug_parts = []
band_pts = []
lead_objs = {}
lead_len = {}
for k, (wm, bm, dia, pts) in WIRES.items():
    sm = G.resample(G.chaikin(pts, 2, False), 60)
    L = [0.0]
    for a_, b_ in zip(sm, sm[1:]):
        L.append(L[-1] + (b_ - a_).length)
    # the cut: the last point of the run that is still outside the board's edge on the way up
    icut = max(i for i, p in enumerate(sm) if p.y < -14.9 * MM and p.z < 44.6 * MM)
    dcut = L[icut]
    long_pts = sv.cut_path(sm, 0.0, dcut)
    stub_pts = sv.cut_path(sm, dcut + 0.14 * MM, L[-1])        # the kerf of the snip
    band_pts.append(long_pts[-1])
    lead = G.tube_path('lead', long_pts, dia * MM / 2, 8, M[wm])
    bandp = sv.cut_path(sm, dcut - 4.4 * MM, dcut - 2.2 * MM)
    band = G.tube_path('band', bandp, dia * MM / 2 + 0.16 * MM, 8, M[bm])
    blob = AP.solder_blob('lead_solder', 1.7 * MM, 0.7 * MM, M['solder'], at=sm[0] + Z * (0.45 * MM), axis=Z) if k != 's' else None
    lo = G.join('lead_' + k, [lead, band] + ([blob] if blob else []))
    G.shade(lo, 50)
    lead_objs[k] = lo
    lead_len[k] = round(dcut / MM, 2)
    stub = G.tube_path('stub', stub_pts, dia * MM / 2, 8, M[wm])
    plug_parts.append(stub)
for k, nm, lab in (('a', 'lead_coil_a', 'Coil lead A'), ('b', 'lead_coil_b', 'Coil lead B'), ('s', 'lead_sense', 'Sense lead')):
    CT.part(lead_objs[k], FAM, nm, lab, parent='gimbal_cradle', material='rubber', mass='tiny', loose=True, flex=True,
            steps=['s2.leads', 's3.trim'] + ([] if k == 's' else ['s3.strip', 's3.tin', 's3.loop']), origin=C)
    CT.mark(lead_objs[k], 'snip', band_pts['abs'.index(k)], Z)
F.notes['lead_length_as_cut_mm'] = lead_len
plug_body = sv.box('plug_body', (-19.3, -10.2, BT + 1.3), (-14.7, -0.6, BT + 4.2), M['polymer'])
G.boolean(plug_body, [sv.box('_pr', (-17.9, -9.5, BT), (-16.1, -1.0, BT + 3.7))])
G.bevel(plug_body, 0.3 * MM, 1, 40)
plug_parts.append(plug_body)
lead_plug = G.join('lead_plug', plug_parts)
G.shade(lead_plug, 45)
BAND_C = sum(band_pts, Vector()) / 3
CT.part(lead_plug, FAM, 'lead_plug', 'Lead plug and burnt lead ends', parent='board', material='plastic', mass='tiny', steps=['s2.board', 's2.leads'],
        origin=BAND_C, touches=['lead_coil_a', 'lead_coil_b', 'lead_sense'])
CT.clear(lead_plug, rot=Matrix.Rotation(math.radians(100), 3, 'X'), offset=P(-0.5, 1.4, 2.0))

# ====================================================================== rigs: the clips on the body, the gimbal on its cradle
R1 = RG.Rig(FAM, parent=case_body)
for i, ((xc, s), c) in enumerate(zip(CLIPS, clips)):
    R1.hinge('clip_%d' % (i + 1), P(xc, s * 30.2, 26.8), X * -s, 0, 40, [c])
R1.finish()
J1 = json.loads(bpy.context.scene['sh_joints'])
SW = GD['swing_deg']
R2 = RG.Rig(FAM, parent=cradle, name='servo_gimbal_rig')
R2.hinge('gimbal_pitch', g['pivot'], g['axes']['x'], -SW, SW, [], requires={'gimbal_roll': 0.5})
R2.hinge('gimbal_roll', g['pivot'], g['axes']['y'], -SW, SW, [], parent='gimbal_pitch', requires={'gimbal_pitch': 0.5})
R2.continuous('rotor', g['pivot'], g['axes']['z'], [], parent='gimbal_roll')
R2.finish()
# The kit parents parts while a parameter is 0, which makes 0 the modelled pose. A gimbal swings both ways from
# level, so here the rig is set level (0.5) first and the parts are put on their bones by hand: 0.5 is the modelled
# and as-found pose, 0 and 1 are the two stops, and the GLB's rest pose is level.
RG.set_params(R2.arm, {'gimbal_pitch': 0.5, 'gimbal_roll': 0.5})
RIDE = {'gimbal_pitch': [g['ring']], 'gimbal_roll': [g['race'], g['retainer']] + g['grit'], 'rotor': [g['rotor']]}
for j in R2.joints:
    j['parts'] = [o.name for o in RIDE[j['param']]]
    for o in RIDE[j['param']]:
        bpy.context.view_layer.update()
        mw = o.matrix_world.copy()
        o.parent = R2.arm; o.parent_type = 'BONE'; o.parent_bone = j['bone']
        bpy.context.view_layer.update()
        o.matrix_world = mw
        dd = json.loads(o['sh']); dd['rides'] = j['param']; o['sh'] = json.dumps(dd)
prm = json.loads(bpy.context.scene['sh_params'])
for pr in prm:
    if pr['node'] == R2.name:
        pr['parts'] = [json.loads(o['sh'])['id'] for o in RIDE[pr['bone']]]
        if not pr['continuous']:
            pr['rest'] = 0.5
bpy.context.scene['sh_params'] = json.dumps(prm)
J2 = R2.joints
sc = bpy.context.scene
sc['sv_rigs'] = json.dumps({R1.name: J1, R2.name: J2})
sc['sh_rig'] = R1.name; sc['sh_joints'] = json.dumps(J1)                 # the kit's single-rig checks see the clips


class Rigs:
    """Two armatures behind the one-rig interface Family.finish() expects."""
    def __init__(self, rigs):
        self.rigs = rigs; self.arm = rigs[0].arm
        self.joints = [j for r in rigs for j in r.joints]

    def bake_actions(self):
        for r in self.rigs:
            bpy.context.scene['sh_joints'] = json.dumps(r.joints)
            r.bake_actions()
        bpy.context.scene['sh_joints'] = json.dumps(self.rigs[0].joints)


F.rig = Rigs([R1, R2])
_eo = F.export_objects
F.export_objects = lambda: (_eo()[0], _eo()[1], [R1.arm, R2.arm])

# ====================================================================== the order things come out (DESIGN.md stage 2)
OPEN = {'clip_1': 1.0, 'clip_2': 1.0, 'clip_3': 1.0}
seq = [{'op': 'remove', 'part': 'screw_case_' + k, 'step': 's2.stripped' if k == 'd' else 's2.screws', 'group': 'case_screws'} for k in 'abcd']
seq += [{'op': 'remove', 'part': 'case_lid', 'step': 's2.pry', 'params': OPEN},
        {'op': 'remove', 'part': 'lead_plug', 'step': 's2.board'},
        {'op': 'remove', 'part': 'trim_resistor', 'step': 's2.board'},
        {'op': 'remove', 'part': 'board', 'step': 's2.board'},
        {'op': 'remove', 'part': 'circlip', 'step': 's2.circlip'},
        {'op': 'remove', 'part': 'gear_top', 'step': 's2.gears'},
        {'op': 'remove', 'part': 'gear_mid', 'step': 's2.gears'},
        {'op': 'remove', 'part': 'gear_low', 'step': 's2.gears'},
        {'op': 'remove', 'part': 'gimbal_retainer', 'step': 's5.rotor'},
        {'op': 'remove', 'part': 'gimbal_rotor', 'step': 's5.rotor'},
        {'op': 'insert', 'part': 'gimbal_rotor', 'step': 's5.rotor'},
        {'op': 'insert', 'part': 'gimbal_retainer', 'step': 's5.rotor'},
        {'op': 'remove', 'part': 'screw_trunnion_a', 'step': 's2.trunnion', 'group': 'trunnion'},
        {'op': 'remove', 'part': 'screw_trunnion_b', 'step': 's2.trunnion', 'group': 'trunnion'},
        {'op': 'remove', 'part': 'gimbal_cradle', 'step': 's2.trunnion'}]
CT.sequence(seq)

# texel budget: the gimbal is the hero, the body's hidden inside matters least
F.uv_weights = {'servo_gimbal_cradle': 1.5, 'servo_gimbal_ring': 1.6, 'servo_gimbal_race': 1.6, 'servo_gimbal_rotor': 1.6, 'servo_gimbal_coil': 1.3,
                'servo_gimbal_retainer': 1.6, 'servo_board': 1.25, 'servo_trim_resistor': 1.6, 'servo_case_body': 0.85, 'servo_stator_winding': 0.8}

# ====================================================================== fixed numbers
bpy.context.view_layer.update()
lo = Vector((1e9, 1e9, 1e9)); hi = -lo
for o in list(CT.parts(FAM).values()):
    if o is case_body:
        vs = [o.matrix_world @ v.co for v in o.data.vertices if (o.matrix_world @ v.co).x < 47.52 * MM]     # without the torn outside leads
    else:
        vs = [o.matrix_world @ v.co for v in o.data.vertices]
    for v in vs:
        lo = Vector((min(lo.x, v.x), min(lo.y, v.y), min(lo.z, v.z))); hi = Vector((max(hi.x, v.x), max(hi.y, v.y), max(hi.z, v.z)))
size = [(hi[i] - lo[i]) / MM for i in range(3)]
for o in list(CT.parts(FAM).values()):
    zs = [(o.matrix_world @ v.co) / MM for v in o.data.vertices]
    bb = [round(min(q[i] for q in zs), 2) for i in range(3)] + [round(max(q[i] for q in zs), 2) for i in range(3)]
    if bb[2] < -0.05 or bb[5] > 55.5 or bb[1] < -35.1 or bb[4] > 35.1 or bb[0] < -47.6:
        F.log('OUT OF ENVELOPE', o.name, bb)
F.notes['size_mm_without_outside_leads'] = [round(x, 2) for x in size]
F.notes['gimbal'] = {k: GD[k] for k in ('body_r', 'depth', 'flange_r', 'flange_t', 'key_w', 'key_r', 'notch_deg', 'notch_w', 'pivot_z', 'spindle_top', 'swing_deg', 'env_r', 'env_z')}
F.notes['gimbal_datum_in_servo_m'] = [list(r) for r in MD]
F.log('size without outside leads (mm)', [round(x, 2) for x in size], 'target 95 x 70 x 55')
for got, want in zip(size, (95.0, 70.0, 55.0)):
    assert abs(got - want) < 0.5, 'servo size %s is off the fixed 95 x 70 x 55' % [round(x, 2) for x in size]
F.finish(extra={'param_rest': {'servo.gimbal_pitch': 0.5, 'servo.gimbal_roll': 0.5},
                'rigs': {R1.name: 'servo_case_body', R2.name: 'servo_gimbal_cradle'}})
