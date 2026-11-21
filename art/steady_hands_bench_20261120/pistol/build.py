# Scrap pistol, rebuilt as real parts to the outline of the in-game pistol (ScrapPistol.glb as a measuring skin).
# Parts breakdown, frames and fixed numbers: PARTS.md. Run:
#   SH/blender.sh pistol/build.py -- --nobake [--review --only six,close] [--nomods]
#   SH/run.sh mp-bake SH/blender.sh pistol/build.py -- --size 2048 --spp 24 ; SH/wait.sh mp-bake
#   --out DIR: write everything to DIR instead of export/ (a staging build: export/ stays as published)
# Surfaces (20 Nov, model-pistol-surface): the materials, the wrap, the guard's section and the atlas come from px.py.
# Writes export/pistol.glb (metres, the pistol's origin and axes), pistol.blend, parts.json, stats.json, outline.json
# (the fixed numbers against the skin) and, after a bake, export/pistol_hand.glb (merged nodes in ScrapPistol units).
import sys, os, math, json, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'kit')); sys.path.insert(0, HERE)
from family import Family, G, MT, CT, RG, BK
import am_parts as AP
import measure as ME
import pframe as PF
import pgeom as PG
from pgeom import P, GP, xz, us, uy, ycyl, MM, X, Y, Z, U_, S_, G0
import px as PX
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix

F = Family('pistol', __file__, budget=45000)
M = F.mats
ARGS = F.argv
if '--out' in ARGS:
    F.out = os.path.abspath(ARGS[ARGS.index('--out') + 1]); os.makedirs(F.out, exist_ok=True)
BY, BZ = PG.BORE_Y, PG.BORE_Z
YC0 = 0.15
# ---------------------------------------------------------------------- surfaces (px.py)
# Old finished steel carried for years; each part its own steel. Fields are where hand and holster rub (pistol mm).
FRAME_RUB = [((86, 0, 43), (11, 15, 7)), ((63, 0, 73), (13, 19, 9)), ((-22, 0, 78), (16, 15, 6)), ((8, 12, 27), (17, 4, 11)), ((8, -12, 27), (17, 4, 11)),
             ((42, -14, 52), (17, 6, 10)), ((2, 0, -18), (27, 9, 6)), ((-55, 0, 32), (8, 17, 15)), ((40, 0, 84), (7, 9, 5)), ((-60, 0, 74), (34, 17, 5)),
             ((-24, 12, -8), (9, 5, 9)), ((-24, -12, -8), (9, 5, 9))]
M['recv'] = PX.steel('recv', fields=FRAME_RUB, rust=1.35, stain=0.7)        # no convex term: the inside test misreads a joined, unioned frame (a hard-edged pale zone)
M['recv_plate'] = PX.steel('recv_plate', finish=(0.40, 0.32, 0.27), finish_metal=0.7, finish_rough=0.58, patina=(0.33, 0.31, 0.30), patina_amt=0.6,
                           worn=(0.61, 0.56, 0.51), dir1=(0.12, 0, 1), dir2=(1, 0, 0.3), mach=(0.05, 0, 1), mach_amt=0.45, rust=1.0, stain=0.8, thin=0.03,
                           edge_gain=0.6, dings=0.3)
M['barrel'] = PX.steel('barrel', origin=P(-94.0, BY, BZ), finish=(0.205, 0.21, 0.225), finish_metal=0.95, finish_rough=0.42, thin=0.04, patina=(0.25, 0.22, 0.21), patina_amt=0.4,
                       worn=(0.52, 0.51, 0.50), worn_rough=0.32, dir1=(0.03, 1, 0.25), dir2=(1, 0.15, 0.1), mach=(0, 1, 0.02), mach_amt=0.4,
                       fields=[((-128, BY, BZ), (10, 24, 24)), ((-113, BY, 85), (8, 5, 5)), ((-96, BY, BZ), (4, 24, 24))], field_gain=0.4,
                       edge_gain=0.7, rust=0.9, pits=0.7, oil=0.16)
M['dust'] = PX.steel('dust', origin=P(-58.15, 0.3, 32), finish=(0.305, 0.32, 0.295), finish_metal=0.75, finish_rough=0.60, patina=(0.36, 0.315, 0.26),
                     worn=(0.58, 0.57, 0.55), fields=[((-112, 0.3, 35.5), (9, 10, 10)), ((-80, -10, 33), (26, 3, 9))], field_gain=0.4, dir1=(1, 0, 0.02),
                     rust=1.1, pits=1.2)
M['housing_st'] = PX.steel('housing_st', origin=GP(-16, 20), finish=(0.30, 0.305, 0.32), worn=(0.60, 0.585, 0.565), worn_rough=0.34, dir1=tuple(S_), dir2=(0.2, 1, 0.1),
                           fields=[(tuple(GP(-29, sv) / MM), (8, 15, 17)) for sv in (-32, -6, 20)] + [(tuple(GP(0, -50) / MM), (34, 20, 5))], field_gain=0.5,
                           rust=1.1, pits=1.3, oil=0.18)
M['steel'] = PX.steel('screw_steel', finish=(0.225, 0.228, 0.245), finish_rough=0.46, patina=(0.31, 0.27, 0.25), worn=(0.53, 0.52, 0.50), edge_gain=0.7, thin=0.06, rust=1.2, stain=0.8,
                      pits=0.5, dings=0.0, scratch=0.6, edge_w=0.0005, wide_w=0.0012, cav_w=0.0028)
M['zinc'] = PX.steel('bolt_zinc', finish=(0.51, 0.51, 0.49), finish_metal=0.9, finish_rough=0.58, patina=(0.45, 0.42, 0.37), worn=(0.65, 0.64, 0.62), bare=(0.82, 0.81, 0.78),
                     edge_gain=0.5, rust=1.3, stain=0.9, pits=0.8, dings=0.0, scratch=0.5, edge_w=0.0005, wide_w=0.0012, cav_w=0.0028)
M['steel_dark'] = PX.steel('steel_case', finish=(0.205, 0.20, 0.205), finish_rough=0.44, patina=(0.31, 0.27, 0.29), patina_amt=0.6, worn=(0.54, 0.53, 0.51), worn_rough=0.32,
                           fields=[((4, 0.15, 2), (7, 5, 14)), ((66, 0.15, 76), (6, 6, 4)), ((30, 16, 46), (8, 5, 5))], field_gain=0.5, edge_gain=0.65, dir1=(0.3, 0, 1),
                           rust=0.8, pits=0.6, dings=0.1)
M['steel_bright'] = PX.bright_steel('steel_pin')
M['steel_rusty'] = PX.rusty_steel('steel_rusted')
M['brass'] = PX.brass('brass_old', base=(0.53, 0.39, 0.20), tarn=0.85, tarn_lo=0.30)          # 21 Nov: tarnished, not clean yellow
M['brass_dull'] = PX.brass('brass_plate', base=(0.42, 0.31, 0.165), rough=0.56, green=0.5, spots=0.9, dir1=(0.2, 0, 1), tarn=0.9, tarn_lo=0.26,
                       fields=[((40, 14, 36), (12, 4, 12)), ((40, -14, 36), (12, 4, 12))])
M['copper'] = PX.copper('copper_old')
M['wire_cu'] = PX.copper('copper_wire', green=0.9, dark=0.6)
M['wood_l'] = PX.wood('wood_scale_l', origin=GP(0, 5, -3.6), cracks=[((-2.1, 60), (-3.7, 40)), ((-3.7, 40), (-5.4, 24.5))], holes=[PG.HOLES['A'], PG.HOLES['B']], side=-1)
M['wood_r'] = PX.wood('wood_scale_r', origin=GP(0, 5, 3.6), cracks=[((-22.5, -52), (-22.0, -44)), ((-22.0, -44), (-20.2, -29.5))], holes=[PG.HOLES['A'], PG.HOLES['B']], side=1)
M['wood_scale'] = M['wood_l']
M['leather_tan'] = PX.leather('leather_tan', origin=GP(0, -10))
M['leather'] = PX.leather('leather_dark', origin=GP(0, -10), base=(0.24, 0.14, 0.088), dark=(0.10, 0.06, 0.04), rough=0.60, thread=(0.42, 0.37, 0.28), raw=(0.46, 0.33, 0.22))
M['tape_khaki'] = PX.cloth('tape_khaki', origin=GP(0, -10), length=0.44)
M['tape'] = PX.cloth('tape_black', origin=GP(0, -10), base=(0.135, 0.13, 0.122), dark=(0.06, 0.055, 0.05), pale=(0.40, 0.38, 0.35), rough=0.78, length=0.50, gum=0.5)
M['butt'] = PX.paint_chipped('butt_orange', GP(-16, 20), MT.WARDEN_ORANGE, MT.BARE_ALLOY, under_rough=getattr(MT, 'BARE_ALLOY_ROUGH', 0.6))      # the kit's constants (SEAM.md section 8)
M['plastic_cream'] = PX.plastic('plastic_old')
M['wire_red'] = PX.sleeve('lead_sleeve')
M['ceramic'] = PX.ceramic('ceramic_old')
M['glass_dark'] = PX.emitter_glass('emitter_glass')
M['fluid'] = PX.fluid('fluid', P(-61.0, BY, 66.6), (BY, 66.6))
M['glass_cell'] = PX.cell_glass('glass_cell_dirty', P(-61.0, BY, 66.6), (BY, 66.6))      # baked with its alpha (px.bake_alpha)
# emission strength 1: glTFast does not read KHR_materials_emissive_strength, so the factor is all that reaches Unity
M['lamp'] = MT.passthrough('lamp_pistol', (0.2, 0.75, 0.9), alpha=1.0, rough=0.12, emit=(0.10, 0.80, 1.0), emit_strength=1.0)
if 'kitmat' in PX.DIAG:
    _dm = MT.make('diag', (0.5, 0.5, 0.5), 0.0, 0.5)
    for _k in list(M):
        if M[_k].get('px'):
            M[_k] = _dm
    M['glass_cell'] = MT.passthrough('glass_cell', (0.55, 0.82, 0.86), alpha=0.16, rough=0.05)
BY, BZ = PG.BORE_Y, PG.BORE_Z
CZ = 66.6                        # axis of the charge cell (its top is the skin's 73.7)
FLOOR = CZ - 8.2                 # floor of the cell bay
PAWL_X = -28.3                   # pivot of the latch pawl
YC = YC0                         # centre plane of the skin's receiver
rnd = random.Random(11)
parts = {}


def paint(o, mat):
    o.data.materials.clear(); o.data.materials.append(mat)
    for p in o.data.polygons:
        p.material_index = 0
    return o


def side_screw(name, x, z, side, head='pan', drive='slot', d=3.0, mat=None, y=None, turn=None, hd=None):
    """A screw or bolt head on a side face (side -1 = left). Heads only: the shank is 2.5 mm into the part."""
    yy = y if y is not None else YC + side * 11.7
    return AP.screw(name, d * MM, 2.5 * MM, head=head, drive=drive, mat=mat or M['steel'], thread=False, point=False,
                    head_d=(hd or d * 1.9) * MM, at=P(x, yy, z), axis=Y * side, turn=rnd.uniform(0, 3.1) if turn is None else turn)


# ====================================================================== frame and receiver (one part)
def build_frame(blanks):
    st = M['recv']
    # side outline from the skin's silhouette (work/skin_mask_side.npy): fairing ahead of the guard, the guard opening,
    # the ledge the scales butt against (their top edge + 0.15), the rear face and the beavertail
    low = [(-49, 51), (-51.5, 46), (-53.5, 42.2), (-58, 42), (-58, 21.5), (-56, 20), (-52, 17.5), (-48, 15.5), (-44, 14), (-40, 14), (-36, 11.5),
           (-32, 7), (-28, -3), (-24, -10.5), (-21.5, -14.0), (-20.5, -10.5), (-22, -5), (-22.3, 6), (-21, 13), (-17.5, 17.5), (-12, 19.5),
           (-8, 20.3), (-2, 19.8), (6, 19.3), (15, 18.6), (18.5, 16.5), (22, 12), (25, 5), (26.8, -1.5), (28, -6.6), (32, -4.6), (36, -4.1),
           (38.45, -5.35), (41.0, 8.2), (44.98, 18.62), (62.0, 22.1), (72.58, 29.0), (78.15, 18.35), (80.2, 17.3), (79.7, 21), (79.2, 30),
           (78.3, 37.2), (80, 38.6), (84, 40), (88, 41.2), (90.5, 43.6), (88, 45.5), (84, 46.5), (80, 48.3), (78.5, 50.5), (77, 53), (72, 54),
           (69, 54), (66, 51)]
    body = xz('frame_low', low, YC - 11.7, YC + 11.7, st)
    G.bevel(body, 1.15 * MM, 3, 30, weighted=False)        # the flanks' edges are broken for real (was a 0.45 chamfer: it read as cut plate)

    def hexsec(x, top, ht, hm, zhi, zlo=55.5, bot=50.3, hb=12.0):
        return [P(x, YC - hb, bot), P(x, YC + hb, bot), P(x, YC + hm, zlo), P(x, YC + hm, zhi), P(x, YC + ht, top), P(x, YC - ht, top),
                P(x, YC - hm, zhi), P(x, YC - hm, zlo)]
    rear = G.loft('up_rear', [hexsec(-25.5, 77.8, 9.2, 15.35, 68), hexsec(50, 77.8, 9.2, 15.35, 68), hexsec(56, 73.2, 9.6, 15.35, 66.5),
                              hexsec(62, 73.2, 9.6, 15.35, 66.5), hexsec(66.6, 71.0, 8.0, 13.6, 64.0)], st, smooth=False)
    G.bevel(rear, 0.6 * MM, 2, 30, weighted=False)
    tray = [(-12, 50.0), (12, 50.0), (15.35, 55.5), (15.35, 59.6), (12.4, 61.8), (9.8, 61.8), (9.0, FLOOR), (-9.0, FLOOR), (-9.8, 61.8), (-12.4, 61.8),
            (-15.35, 59.6), (-15.35, 55.5)]
    bay = G.prism('up_bay', [((a + YC) * MM, b * MM) for a, b in tray], 73.2 * MM, P(-92.5, 0, 0), Y, Z, X, st, w0=0.0)
    tang = uy('tang', PG.TANG_T, PG.TANG_END, 60.0, st)
    G.boolean(tang, [us('_th', [(-30, PG.T_TOP), (-13.0, PG.T_TOP), (-13.0, 62), (-30, 62)], -10, 10)])      # the T-head stops at T_TOP
    # the bay's front contact block and the two cheeks either side of the latch
    blocks = [G.box('fblock', P(-91.2, BY, (FLOOR + 73.5) / 2 - 0.5), (2.6 * MM, 19.2 * MM, (73.5 - FLOOR + 1) * MM), None, st)]
    for sy in (-1, 1):
        blocks.append(G.box('cheek', P(-29.2, BY + sy * 8.5, (FLOOR + 74.0) / 2 - 0.5), (8.4 * MM, 7.6 * MM, (74.0 - FLOOR + 1) * MM), None, st))
    G.boolean(body, [rear, bay, tang] + blocks, 'UNION')
    G.boolean(body, [G.box('_pawlnotch', P(-22.6, BY, 70.5), (7.0 * MM, 8.8 * MM, 24 * MM))])            # room for the pawl to swing back
    # the broken end of the tang, the crack, the holes, the trigger slot
    jag = us('_jag', [(-21, -3), (7, -3), (7, 2.0), (2.5, 3.6), (-1.5, 2.3), (-6, 4.0), (-10, 2.5), (-13.5, 3.2), (-21, 2.1)], -10, 10)
    crack = us('_crack', [(5.6, 17.2), (1.0, 14.8), (-2.5, 15.4), (-6.0, 12.6), (-6.0, 12.3), (-2.5, 15.0), (1.0, 14.4), (5.6, 16.8)], -6, 6)
    cuts = [jag, crack]
    for k in ('A', 'B'):
        cuts.append(ycyl('_h', PG.HOLES[k][0], PG.HOLES[k][1], 2.15, -8, 8))
    cuts.append(ycyl('_pin', PG.PIN[0], PG.PIN[1], 1.6, -9, 9))
    cuts.append(G.cyl('_spr', GP(-19.4, 22.0), GP(-13.5, 22.0), 2.35 * MM, 14))                 # blind hole for the housing spring
    cuts.append(G.box('_trigslot', P(10.9, YC, 22.3), (14.2 * MM, 6.2 * MM, 10.6 * MM)))
    G.boolean(body, cuts)
    G.bevel(body, 0.45 * MM, 1, 33)
    # 21 Nov: a bevel fills a concave edge. The two concave corners of the ledge, where the grip core seats, had gained up to
    # 0.34 mm of fillet from the 1.15 mm flank bevel (grip.core then overlapped the frame): cut them back to the sharp
    # outline, 0.02 mm outside it so no cutter face lies in a face of the frame
    sa = sum(low[i][0] * low[(i + 1) % len(low)][1] - low[(i + 1) % len(low)][0] * low[i][1] for i in range(len(low)))
    def outn(p, q):
        d = Vector((q[0] - p[0], q[1] - p[1])).normalized()
        return Vector((d.y, -d.x)) if sa > 0 else Vector((-d.y, d.x))
    corners = []
    for c in ((44.98, 18.62), (72.58, 29.0)):
        i = low.index(c); a_, b_ = low[i - 1], low[i + 1]
        C = Vector(c); ua = (Vector(a_) - C).normalized(); ub = (Vector(b_) - C).normalized()
        na, nb = outn(a_, c), outn(c, b_)
        k = 0.02
        poly = [C + (na + nb).normalized() * k * 1.5, C + ub * 3.0 + nb * k, C + ub * 3.0 + nb * 2.5, C + (na + nb).normalized() * 3.0,
                C + ua * 3.0 + na * 2.5, C + ua * 3.0 + na * k]
        corners.append(xz('_corner', [(p.x, p.y) for p in poly], -14, 14))
    G.boolean(body, corners)
    # the scales butt against the frame: cut the frame to their real shape with 0.15 mm of air
    G.boolean(body, [PG.inflate(G.duplicate(b, '_infl'), 0.15) for b in blanks])
    paint(body, st)
    bits = [body]
    # trigger guard: a flat strap from the fairing round to the back of the opening
    gpts = [(-21.5, -14.0), (-16, -16.8), (-10, -18.2), (-4, -18.6), (2, -18.5), (8, -17.6), (14, -15.6), (20, -12.4), (25, -8.4), (28.2, -6.4)]
    gp = G.chaikin([P(a, YC, b) for a, b in gpts], 2, closed=False)
    cen = P(2, YC, 6)
    # a forged strap: rounded section, crowned outside, widening into the frame at both roots (same outer line as before)
    gp = G.resample(gp, 40)
    guard = PX.forged_strap('guard', gp, 8.4 * MM, 4.0 * MM, lambda p, t: p - cen, st, r=1.5 * MM, seg=3,
                            flare=lambda t: 1.0 + 0.55 * abs(2 * t - 1) ** 3)
    G.shade(guard, 40)
    bits.append(guard)
    # rear sight with its notch, the hammer, the latch's pivot lugs and pin, the front cell clip
    rs = G.box('rsight', P(40.5, YC, 81.25), (7 * MM, 10 * MM, 7.5 * MM), None, st)
    G.boolean(rs, [G.box('_n', P(40.5, YC, 83.9), (9 * MM, 2.6 * MM, 3.4 * MM))])
    G.bevel(rs, 0.3 * MM, 1, 30)
    bits += [rs, G.box('rsbase', P(40.5, YC, 78.3), (10.5 * MM, 14 * MM, 1.4 * MM), None, st)]
    ham = xz('hammer', [(60.5, 71.5), (62.5, 76.2), (65, 77.2), (69.5, 76.3), (70.2, 71), (68.5, 68.8), (64, 69.0)], YC - 3.6, YC + 3.6, M['steel_dark'])
    G.bevel(ham, 0.5 * MM, 1, 30)
    bits.append(ham)
    for sy in (-1, 1):
        for i in range(9):
            bits.append(G.box('rib', P(19.5 + 3.4 * i, YC + sy * 15.75, 63.2), (1.7 * MM, 0.9 * MM, 8.4 * MM), None, st))
        bits.append(G.box('lug', P(PAWL_X, BY + sy * 3.6, CZ - 5.9), (3.6 * MM, 1.5 * MM, 4.6 * MM), None, st))
    bits.append(G.pin('latchpin', P(PAWL_X, BY - 4.6, CZ - 5.5), P(PAWL_X, BY + 4.6, CZ - 5.5), 1.0 * MM, 10, M['steel_bright']))
    bits.append(saddle('clip_front', -84.0, M['brass']))
    # fasteners that stay: mismatched on purpose
    for sd in (-1, 1):       # a cover plate bolted on each side of the receiver, its four screws not all alike
        y0, y1 = (YC + 15.3, YC + 16.2) if sd > 0 else (YC - 16.2, YC - 15.3)
        cp = xz('cover', PG.fillet([(-17, 59.6), (14.5, 59.6), (14.5, 67.6), (-17, 67.6)], 1.2, 2), y0, y1, M['recv_plate'])
        G.bevel(cp, 0.25 * MM, 1, 30)
        bits.append(cp)
        for i, (cx, cz) in enumerate(((-14.4, 61.9), (11.9, 61.9), (11.9, 65.3), (-14.4, 65.3))):
            hx = (i == 2 and sd > 0) or (i == 0 and sd < 0)
            bits.append(side_screw('cs', cx, cz, sd, head='hex' if hx else 'pan', drive='none' if hx else 'slot', d=2.2 if not hx else 2.6, y=YC + sd * 16.2,
                                   mat=M['zinc'] if hx else None))
    for tx in (-8, 27):
        bits.append(AP.screw('ts', 3.0 * MM, 2.5 * MM, head='pan', drive='slot', mat=M['steel'], thread=False, point=False, at=P(tx, YC, 77.8), axis=Z,
                             turn=rnd.uniform(0, 3)))
    bits += [side_screw('fs', 60, 61, s, y=YC + s * 15.35, d=3.6) for s in (-1, 1)]
    bits += [side_screw('fs', -27, 24.4, s) for s in (-1, 1)]
    bits += [side_screw('fs', 32, 4.4, s, d=2.6) for s in (-1, 1)]
    bits += [side_screw('fb', -46, 34, 1, head='hex', drive='none', d=3.2, mat=M['zinc'])]
    for i in range(3):          # three vent ribs on the right of the fairing (the left face is the mod rail and stays flat)
        vr = G.box('vent', P(-40.5 + 3.6 * i, YC + 12.0, 24.5), (1.8 * MM, 1.0 * MM, 8.5 * MM), None, st)
        bits.append(vr)
    bits += [side_screw('fs', -66, 55.6, 1, y=YC + 15.35, d=2.6), side_screw('fs', -66, 55.6, -1, y=YC - 15.35, d=2.6, head='cheese')]
    # brass side plate with its axle cap (right side; the left one is the bus terminal plate)
    bits += brass_plate(1, cap=True)
    # bezel of the status lamp on the rear face
    bits.append(AP.tube('bezel', 7.6 * MM, 5.0 * MM, 1.6 * MM, M['brass'], 16, at=P(66.55, YC, 60.5), axis=X))
    # 21 Nov (orchestrator's ruling on integration's 08:28 numbers check): the frozen grip_gyro_braced mod clips its status
    # repeater onto the frame's left rear at P (60, -14.2, 24..25.5), where the Meshy skin stands 2.6 mm proud of the flank.
    # A welded clip seat brings the surface back to the skin there (flat face at y -14.15; skin -14.6 .. -14.0)
    pad = xz('clip_seat', PG.fillet([(56.5, 23.3), (63.2, 23.9), (63.2, 27.8), (56.5, 27.8)], 1.0, 2), -14.15, YC - 11.7 + 0.15, st)
    G.bevel(pad, 0.35 * MM, 2, 30)
    bits.append(pad)
    o = G.join('frame', bits)
    G.shade(o, 38, weighted=True)
    CT.part(o, 'pistol', 'frame', 'Frame and receiver', kind='part', material='steel', mass='heavy', item='scrap_pistol', loose=True,
            steps=['s0.pistol', 's1.clamp', 's1.inspect', 's2.swap', 's6.slide'], note='root of the pistol; the tang stub with its crack is part of it')
    CT.mark(o, 'crack', GP(0.5, 14.8, -3.6), -Y)
    CT.mark(o, 'tang_end', GP(-4, 2.6, 0), -S_)
    return o


def saddle(name, x, mat, width=4.0, t=0.7):
    """Open-topped spring clip for a cell cap (d 14.2): a U whose mouth is wider than the cap, lips flared."""
    r = 7.25 + t / 2
    pts = []
    for k in range(13):
        a = math.radians(180 + 180 * k / 12)
        pts.append(P(x, BY + r * math.cos(a), CZ + r * math.sin(a)))
    lipl = [P(x, BY - r - 1.3, CZ + 4.3), P(x, BY - r, CZ + 2.2)]
    lipr = [P(x, BY + r, CZ + 2.2), P(x, BY + r + 1.3, CZ + 4.3)]
    pts = lipl + pts + lipr
    ax = P(x, BY, CZ)
    o = G.band_path(name, pts, width * MM, t * MM, lambda p, tg: p - ax, mat, closed=False, offset=-t * MM / 2)
    foot = G.box(name + '_foot', P(x, BY, FLOOR + 0.35), (width * MM, 5 * MM, 0.9 * MM), None, mat)
    o = G.join(name, [o, foot])
    G.shade(o, 40)
    return o


def brass_plate(side, cap):
    poly = [(25, 25.5), (29, 21.4), (51, 21.4), (55, 27), (55, 50.2), (25, 50.2)]
    y0, y1 = (YC + 11.75, YC + 13.9) if side > 0 else (YC - 13.9, YC - 11.75)
    pl = xz('bplate', poly, y0, y1, M['brass_dull'])
    G.bevel(pl, 0.35 * MM, 1, 30)
    out = [pl, AP.screw('bp_hex', 3.6 * MM, 2 * MM, head='hex', drive='none', mat=M['steel'], thread=False, point=False,
                        at=P(31, YC + side * 13.9, 26.5), axis=Y * side, turn=0.4),
           side_screw('bp_s', 50.5, 45.5, side, y=YC + side * 13.9, d=2.2, mat=M['brass'])]
    yb0, yb1 = (YC + 13.9, YC + 19.2) if side > 0 else (YC - 19.2, YC - 13.9)
    bar = xz('lever', PG.fillet([(25.5, 43.2), (35.5, 43.8), (36.5, 46.2), (35.5, 48.6), (25.5, 49.2)], 1.0, 2), yb0, yb1, M['steel_dark'] if cap else M['brass'])
    G.bevel(bar, 0.5 * MM, 1, 30)
    out.append(bar)
    if cap:
        prof = [(0, 0), (0, 5.6), (5.2, 5.6), (7.2, 4.9), (8.3, 3.4), (8.6, 0)]
        out.append(G.lathe('axlecap', [([(a * MM, b * MM) for a, b in prof], False)], 20, P(39, YC + side * 13.9, 39.5), Y * side, Z, M['brass']))
    return out


# ====================================================================== barrel, dust cover
def build_barrel():
    st = M['barrel']
    prof = [(36.1, 0), (36.1, 18.9), (30.4, 18.9), (29.8, 17.3), (10.4, 17.3), (9.6, 16.5), (9.6, 12.0), (8.8, 12.0), (8.2, 12.5), (0.8, 12.5),
            (0, 11.7), (0, 7.6), (0.6, 7.0), (33.5, 7.0), (33.5, 0)]
    mouth = P(PG.MOUTH_X, BY, BZ)
    b = G.lathe('barrel', [([(a * MM, r * MM) for a, r in prof], False)], 32, mouth, X, Z, st)
    bits = [b]
    for k in range(6):
        a = math.radians(30 + 60 * k)
        rad = Y * math.cos(a) + Z * math.sin(a)
        tan = X.cross(rad)
        rib = G.box('rib', mouth + X * 20.0 * MM + rad * 18.0 * MM, (18.4 * MM, 5.0 * MM, 2.3 * MM), Matrix((X, tan, rad)).transposed(), st)
        G.bevel(rib, 0.5 * MM, 1, 30)
        bits.append(rib)
    fs = xz('fsight', [(-117.5, 77.0), (-108.5, 77.0), (-109.4, 80.2), (-110.0, 85.0), (-115.6, 85.0), (-116.8, 80.2)], BY - 1.2, BY + 1.2, st)
    bits += [fs, G.box('fsbase', P(-113.0, BY, 77.6), (10.0 * MM, 6.4 * MM, 2.4 * MM), None, st)]
    bits.append(G.cyl('emitter', mouth + X * 32.6 * MM, mouth + X * 33.6 * MM, 6.95 * MM, 20, M['glass_dark']))
    bits.append(AP.tube('focus', 9.0 * MM, 6.0 * MM, 1.2 * MM, M['copper'], 20, at=mouth + X * 31.6 * MM, axis=-X))
    bits.append(AP.screw('pinch', 3.4 * MM, 2 * MM, head='hex', drive='none', mat=M['steel'], thread=False, point=False,
                         at=mouth + X * 33.2 * MM - Y * 18.9 * MM, axis=-Y, turn=0.2))
    o = G.join('barrel', bits)
    G.shade(o, 36)
    CT.part(o, 'pistol', 'barrel', 'Barrel assembly', parent='frame', material='steel', mass='medium', fixed=True,
            origin=P(-94.0, BY, BZ), note='muzzle ring, ribbed collar, flange, front sight, emitter cup; the barrel mods sleeve over the muzzle ring')
    CT.mark(o, 'bore_mouth', mouth, -X)
    return o


def build_dust_cover():
    st = M['dust']
    yc = 0.3
    # left face from the skin (Y -9.96 at Z 30, -9.4 at Z 38): the cell mods sit on it
    sec = [(-9.3, 40.5), (10.7, 40.5), (10.7, 30), (6.8, 24.0), (-6.8, 24.0), (-10.05, 30)]
    body = G.prism('dc', [(a * MM, b * MM) for a, b in sec], 42.85 * MM, P(-101, 0, 0), Y, Z, X, st, w0=0.0)
    G.boolean(body, [xz('_c', [(-102, 23), (-102, 31.2), (-90.5, 23)], -20, 20)])
    nose = G.cyl('nose', P(-114, yc, 35.5), P(-99, yc, 35.5), 5.0 * MM, 20, st, chamfer=1.0 * MM)
    G.boolean(body, [nose], 'UNION')
    G.bevel(body, 0.45 * MM, 1, 30)
    paint(body, st)
    bits = [body]
    bits.append(AP.screw('ns', 4.0 * MM, 2 * MM, head='cheese', drive='slot', mat=M['steel'], thread=False, point=False, head_d=6.4 * MM, head_h=1.2 * MM,
                         at=P(-113.9, yc, 35.5), axis=-X, turn=0.5))
    bits += [side_screw('ds', -94, 35, 1, y=10.7, d=2.6), side_screw('ds', -66, 35, 1, y=10.7, head='hex', drive='none', d=3.0, mat=M['zinc'])]
    o = G.join('dust_cover', bits)
    G.shade(o, 38, weighted=True)
    CT.part(o, 'pistol', 'dust_cover', 'Dust cover with rail', parent='frame', material='steel', mass='medium', fixed=True, origin=P(-58.15, yc, 32),
            note='its left face is the front of the rail the cell mods sit on (held to the skin within 0.1 mm): nothing stands proud of it')
    return o


# ====================================================================== trigger, lead, plug, bus
def build_trigger():
    poly = [(5.2, 24.6), (5.4, 19.5), (4.6, 10), (3.2, 3), (1.6, -3), (0.0, -7.2), (-0.6, -9.2), (0.6, -10.4), (3.0, -10.4), (5.8, -8.4),
            (9.2, -4.4), (12.6, 2.5), (15.2, 10), (16.4, 17), (16.6, 24.6)]
    o = xz('trigger', [(v.x, v.y) for v in G.chaikin([(a, b, 0) for a, b in poly], 1)], YC - 2.6, YC + 2.6, M['steel_dark'])
    hole = G.cyl('_tp', P(10.5, -6, 22.3), P(10.5, 6, 22.3), 1.25 * MM, 12)
    G.boolean(o, [hole])
    G.bevel(o, 0.5 * MM, 2, 30)
    G.shade(o, 40)
    CT.part(o, 'pistol', 'trigger', 'Trigger', parent='frame', material='steel', mass='tiny', fixed=True, origin=P(10.5, YC, 22.3))
    return o


def lead_route():
    return [GP(-21.4, 46.5, 4.0), GP(-21.2, 41, 4.0), GP(-21.0, 34, 4.0), GP(-21.4, 28, 4.0), GP(-22.0, 18, 4.0), GP(-23.3, 9, 4.0), GP(-23.6, 3, 3.6),
            GP(-23.2, -1.0, 2.0), GP(-22.2, -2.6, 0.6), GP(-21.2, -2.8, 0.0)]


def build_lead():
    pts = lead_route()
    o = PX.tube('lead', G.resample(G.chaikin(pts, 2, False), 22), 1.1 * MM, 8, M['wire_red'], sid=1)       # as AP.lead's sleeve, with strip UVs
    gl = AP.tube('gland', 3.8 * MM, 2.3 * MM, 2.2 * MM, M['brass'], 12, at=pts[0], axis=(pts[1] - pts[0]))
    o = G.join('lead', [o, gl])
    G.shade(o, 50)
    CT.part(o, 'pistol', 'lead', 'Trigger lead', parent='frame', material='rubber', mass='tiny', fixed=True, flex=True, origin=pts[0],
            steps=['s1.lead', 's6.plug'], note='fixed in the frame at its top end; the free end carries pistol.lead_plug. Its as-found route is path route')
    rp = G.resample(G.chaikin(pts, 2, False), 12)
    CT.path(o, 'route', rp, [(-U_) for _ in rp])
    return o


def build_plug():
    cr = M['plastic_cream']
    body = us('plug', [(-21.4, -5.0), (-13.2, -5.0), (-13.2, -0.6), (-21.4, -0.6)], -2.6, 2.6, cr)
    tab = us('ptab', [(-20.6, -0.6), (-15.0, -0.6), (-15.6, 0.5), (-20.6, 0.2)], -1.3, 1.3, cr)
    key = us('pkey', [(-17.5, -4.6), (-13.2, -4.6), (-13.2, -3.2), (-17.5, -3.2)], -3.3, -2.6, cr)
    G.boolean(body, [tab, key], 'UNION')
    G.bevel(body, 0.3 * MM, 1, 30)
    paint(body, cr)
    bits = [body]
    for yy in (-1.2, 1.2):
        bits.append(G.pin('ppin', GP(-13.25, -2.8, yy), GP(-9.6, -2.8, yy), 0.45 * MM, 8, M['brass']))
    o = G.join('lead_plug', bits)
    G.shade(o, 40)
    CT.part(o, 'pistol', 'lead_plug', 'Keyed plug of the trigger lead', parent='cell_bus', material='plastic', mass='tiny', symmetry=1, tol_mm=3, tol_deg=15,
            steps=['s1.lead', 's6.plug'], origin=GP(-13.2, -2.8), touches=['lead', 'housing'])
    CT.clear(o, offset=-U_ * 14 * MM)
    CT.grab(o, GP(-18.5, -2.8))
    return o


def build_bus():
    cu, br = M['copper'], M['brass_dull']
    bits = [saddle('clip_rear', -38.0, M['brass'])]
    # copper rod from the rear clip over the bay rim, down the left side and back to the terminal plate
    yl = YC - 15.35 - 1.5
    rod = [P(-38, BY - 8.4, CZ + 3.0), P(-38, BY - 11.5, CZ - 0.4), P(-38, yl + 0.4, 62.0), P(-37, yl, 58.5), P(-33, yl, 57.4), P(-10, yl, 57.4), P(12, yl, 57.4),
           P(22, yl + 0.3, 55.0), P(28, YC - 15.3, 49.5), P(33.5, YC - 15.2, 44.5), P(37.5, YC - 15.2, 41.5)]
    bits.append(PX.tube('busrod', G.chaikin(rod, 2, False), 1.2 * MM, 8, cu, sid=2))       # as AP.wire, with strip UVs
    for xx in (-22, 4):
        bits.append(AP.tube('standoff', 5.2 * MM, 2.0 * MM, 1.6 * MM, M['ceramic'], 12, at=P(xx, YC - 15.35, 57.4), axis=-Y))
    bits += brass_plate(-1, cap=False)
    bits.append(G.cyl('tpost', P(39, YC - 13.9, 39.5), P(39, YC - 16.3, 39.5), 3.4 * MM, 14, M['brass']))
    bits.append(AP.knurled_band('tnut', 11.4 * MM, 4.6 * MM, n=22, mat=M['brass'], at=P(39, YC - 16.3, 39.5), axis=-Y))
    bits.append(G.lathe('tdome', [([(0, 0), (0, 3.0 * MM), (0.9 * MM, 2.6 * MM), (1.5 * MM, 1.4 * MM), (1.7 * MM, 0)], False)], 12,
                        P(39, YC - 20.9, 39.5), -Y, Z, M['brass']))
    # strip down the front edge of the tang to the socket under its broken end
    strip = us('busstrip', [(5.15, 57.5), (6.4, 57.5), (6.4, 0.3), (-12.6, 0.3), (-12.6, 1.4), (5.15, 1.4)], -2.4, 2.4, cu)
    bits.append(strip)
    block = us('socket', [(-13.0, -5.9), (-3.0, -5.9), (-3.0, 0.3), (-13.0, 0.3)], -3.4, 3.4, M['plastic_cream'])
    cuts = [G.cyl('_sp', GP(-14, -2.8, yy), GP(-9.0, -2.8, yy), 0.62 * MM, 8) for yy in (-1.2, 1.2)]
    G.boolean(block, cuts)
    G.bevel(block, 0.3 * MM, 1, 30)
    paint(block, M['plastic_cream'])
    bits.append(block)
    o = G.join('cell_bus', bits)
    G.shade(o, 40)
    CT.part(o, 'pistol', 'cell_bus', 'Cell bus', parent='frame', material='copper', mass='light', fixed=True, origin=P(39, YC - 13.9, 39.5),
            note='rear cell clip, copper rod with two stand-offs, brass terminal plate and nut, strip down the tang, keyed socket at its lower end')
    CT.mark(o, 'socket', GP(-13.0, -2.8), -U_)
    return o


# ====================================================================== cell, latch, lamp
def build_cell():
    ax = lambda x: P(x, BY, CZ)
    br = M['brass']
    bits = []
    for x0, x1 in ((-88.0, -80.0), (-42.0, -34.0)):
        prof = [(0, 0), (0, 6.4), (0.5, 7.1), (2.2, 7.1), (2.6, 6.75), (5.4, 6.75), (5.8, 7.1), (7.5, 7.1), (8.0, 6.4), (8.0, 0)]
        bits.append(G.lathe('cap', [([(a * MM, r * MM) for a, r in prof], False)], 24, ax(x0), X, Z, br))
    bits.append(G.lathe('dome', [([(0, 0), (0, 2.6 * MM), (0.8 * MM, 2.2 * MM), (1.3 * MM, 1.2 * MM), (1.5 * MM, 0)], False)], 12, ax(-88.0), -X, Z, M['copper']))
    bits.append(G.cyl('stud', ax(-34.1), ax(-30.4), 1.3 * MM, 10, M['steel_bright'], chamfer=0.25 * MM))
    fluid = G.cyl('fluid', ax(-79.2), ax(-42.8), 5.2 * MM, 20, M['fluid'])
    glass = AP.tube('glass', 12.6 * MM, 11.2 * MM, 38.4 * MM, M['glass_cell'], 24, at=ax(-80.2), axis=X, chamfer=0.0)
    bits += [fluid, glass]
    o = G.join('cell', bits)
    G.shade(o, 40)
    CT.part(o, 'pistol', 'cell', 'Charge cell', parent='frame', material='glass', mass='light', symmetry=1, tol_mm=4, tol_deg=20,
            held_by=['cell_latch'], steps=['s0.cell', 's6.cell'], origin=ax(-61.0), touches=['cell_bus'],
            note='glass tube, two brass caps, retaining stud on the rear cap, glowing fluid; lifts straight up out of two saddle clips')
    CT.clear(o, offset=Z * 40 * MM)
    CT.mark(o, 'stud', ax(-32.2) + Z * 1.3 * MM, Z)
    return o


def build_latch():
    # the pawl in its own frame: x from the pivot, z from the pivot (the pivot is 5.5 under the cell axis)
    rel = [(1.9, -1.7), (2.1, 2.4), (1.4, 9.4), (1.4, 15.0), (1.3, 17.3), (-2.9, 16.9), (-2.3, 14.8), (-1.0, 14.0), (-0.9, 9.0), (-3.3, 8.6),
           (-3.3, 6.95), (-1.6, 6.95), (-1.6, 2.4), (-1.9, -1.7)]
    px, pz = PAWL_X, CZ - 5.5
    o = xz('latch', [(px + a, pz + b) for a, b in rel], BY - 2.5, BY + 2.5, M['brass'])
    G.boolean(o, [G.cyl('_lp', P(px, BY - 5, pz), P(px, BY + 5, pz), 1.15 * MM, 12)])
    pad = G.box('pad', P(px - 0.8, BY, pz + 17.3), (4.6 * MM, 7.4 * MM, 1.0 * MM), Matrix.Rotation(math.radians(-5), 3, 'Y'), M['brass'])
    G.boolean(o, [pad], 'UNION')
    G.bevel(o, 0.3 * MM, 1, 30)
    paint(o, M['brass'])
    G.shade(o, 40)
    CT.part(o, 'pistol', 'cell_latch', 'Cell latch', parent='frame', material='steel', mass='tiny', fixed=True, origin=P(px, BY, pz),
            steps=['s0.cell', 's6.cell'], note='upright pawl; thumb the pad back 22 degrees and the beak clears the cell stud')
    CT.grab(o, P(px - 0.8, BY, pz + 17.4))
    return o


def build_lamp():
    o = G.lathe('lamp', [([(0, 0), (0, 2.45 * MM), (0.9 * MM, 2.3 * MM), (1.7 * MM, 1.5 * MM), (2.0 * MM, 0)], False)], 14, P(66.65, YC, 60.5), X, Z, M['lamp'])
    CT.part(o, 'pistol', 'status_lamp', 'Status lamp', parent='frame', material='glass', mass='tiny', fixed=True, origin=P(66.65, YC, 60.5),
            steps=['s0.cell', 's6.cell'], note='own emissive material (lamp_pistol): off with the cell out, amber then cyan when it goes back')
    return o


# ====================================================================== the old grip
def scale_blank(gs, side):
    """One wooden scale: the grip solid cut to the plate outline, from the tang face outward, with its rebate for the
    housing's flanges and its four holes."""
    y0, y1 = (-30, -3.6) if side < 0 else (3.6, 30)
    o = G.duplicate(gs, 'scale')
    G.boolean(o, [us('_o', PG.outline(), y0, y1)], 'INTERSECT')
    G.bevel(o, 0.8 * MM, 2, 30)
    ry = (-9.4, -3.5) if side < 0 else (3.5, 9.4)
    cuts = [us('_reb', [(-32, -8), (-12.9, -8), (-12.9, 42.3), (-32, 42.3)], ry[0], ry[1])]
    for k, (u, s) in PG.HOLES.items():
        cuts.append(ycyl('_h', u, s, 3.05 if k in 'AB' else 1.65, -30, 30))
    for k in 'AB':
        u, s = PG.HOLES[k]
        cuts.append(ycyl('_cb', u, s, 4.6, -30, -14.0) if side < 0 else ycyl('_cb', u, s, 4.6, 14.0, 30))
    G.boolean(o, cuts)
    return o


def build_scales(L, R):
    wd = M['wood_l']
    crack = us('_crk', [(-2.3, 60), (-3.8, 40), (-5.6, 24.5), (-5.2, 24.5), (-3.5, 37), (-1.9, 60)], -30, 0)
    chip = us('_chip', [(17.5, -47), (27, -47), (27, -37.5)], -30, 0)
    G.boolean(L, [crack, chip])
    paint(L, wd); G.shade(L, 42, weighted=True)
    CT.part(L, 'pistol', 'scale_l', 'Left grip scale', parent='frame', material='wood', mass='light', symmetry=1, tol_mm=5, tol_deg=20,
            held_by=['screw_grip_a', 'screw_grip_b', 'wrap'], steps=['s1.scales', 's3.scribe', 's3.punch'], origin=GP(0, 5, -3.6),
            touches=['housing'], note='cracked through hole A, chipped at the toe; its outline and four holes are the template for the side plates')
    CT.clear(L, offset=-Y * 45 * MM)
    crack = us('_crk', [(-22.8, -52), (-22.2, -44), (-20.4, -29.5), (-20.0, -29.5), (-21.8, -44), (-22.2, -52)], 0, 30)
    G.boolean(R, [crack])
    wd = M['wood_r']
    paint(R, wd)
    bits = [R]
    for k in 'AB':
        u, s = PG.HOLES[k]
        bits.append(AP.tube('nut', 6.0 * MM, 4.1 * MM, 10.0 * MM, M['brass'], 14, at=GP(u, s, 4.0), axis=Y))
        fl = AP.tube('nutfl', 8.8 * MM, 4.1 * MM, 1.5 * MM, M['brass'], 16, at=GP(u, s, 14.0), axis=Y)
        G.boolean(fl, [G.box('_sl', GP(u, s, 15.3), (10 * MM, 0.9 * MM, 1.2 * MM), Matrix((U_, Y.cross(U_), Y)).transposed())])
        bits.append(fl)
    R = G.join('scale_r', bits)
    G.shade(R, 42, weighted=True)
    CT.part(R, 'pistol', 'scale_r', 'Right grip scale', parent='frame', material='wood', mass='light', symmetry=1, tol_mm=5, tol_deg=20,
            held_by=['screw_grip_a', 'screw_grip_b', 'wrap'], steps=['s1.scales'], origin=GP(0, 5, 3.6), touches=['housing'],
            note='carries the two brass nuts the grip screws thread into; cracked through hole D')
    CT.clear(R, offset=Y * 45 * MM)
    return L, R


def build_grip_screws():
    out = []
    for nm, k, mat, label, steps, turn in (('screw_grip_a', 'A', M['steel'], 'Upper grip screw', ['s1.screw_a'], 0.5),
                                           ('screw_grip_b', 'B', M['steel_rusty'], 'Lower grip screw (rusted)', ['s1.screw_b'], 2.0)):
        u, s = PG.HOLES[k]
        o = AP.screw(nm, 3.8 * MM, 27.5 * MM, head='cheese', drive='slot', head_d=8.4 * MM, head_h=2.6 * MM, mat=mat, thread_len=11 * MM, pitch=0.9 * MM,
                     at=GP(u, s, -14.0), axis=-Y, ref=S_, turn=turn)
        CT.fastener(o, 'pistol', nm, label, bit='slot', turns=6, holds=['scale_l', 'scale_r'], shank_d=3.8 * MM, parent='frame',
                    material='steel', steps=steps, touches=['frame', 'wrap'])
        CT.clear_along(o, 34 * MM)
        if k == 'B':
            CT.mark(o, 'oil', GP(u, s, -16.6), -Y)
        out.append(o)
    return out


def build_housing(gs):
    st = M['housing_st']
    # everything behind and under the scales, the pin's ears (corners cut back for the scales' eased bite) and the
    # zone of the flanges, as one outline: one intersection with the grip solid, then only cuts
    region = [(31, -44.5), (24.6, -44.5), (21.5, -44.85), (-22.5, -51.05), (-26.8, -47.75), (-27.95, -30), (-27.95, -6), (-27.4, 2.6),
              (-13.2, 2.6), (-13.2, 32.15), (-14.2, 32.15), (-12.65, 33.7), (-12.65, 40.3), (-14.2, 41.85), (-40, 41.85), (-40, -52),
              (-30.5, -53.2), (-24.0, -55.2), (28.6, -47.9), (31, -47.5)]
    back = G.duplicate(gs, 'housing')
    G.boolean(back, [us('_r', region, -30, 30)], 'INTERSECT')
    G.bevel(back, 0.45 * MM, 1, 30)
    # the flanges are only 18 wide: take the rest of their zone away
    fz = [(-27.4, 2.3), (-12.9, 2.3), (-12.9, 32.45), (-24.5, 32.45), (-23.6, 21), (-26.15, 8)]      # no face of it lies in a face of the housing
    tslot = uy('_ts', PG.T_SLOT, -4, 62)
    chan = us('_ch', [(-19.2, -12), (-27.6, -12), (-27.8, -3), (-25.6, 9), (-24.2, 21), (-23.6, 30), (-22.3, 36.5), (-19.2, 36.5)], -6.15, 6.15)
    groove = us('_lg', [(-19.2, 34), (-32, 34), (-32, 43), (-19.2, 43)], 2.7, 5.3)       # the lead lies in an open groove at the top
    pinh = ycyl('_ph', PG.PIN[0], PG.PIN[1], 1.6, -30, 30)
    win = us('_win', [(-40, -6.2), (-19, -6.2), (-19, 1.0), (-40, 1.0)], -3.75, 3.75)     # the plug is seen, and pulled, through the back
    G.boolean(back, [us('_fz', fz, 9.0, 30), us('_fz', fz, -30, -9.0), tslot, chan, groove, pinh, win])
    paint(back, st)
    me = back.data
    me.materials.append(M['butt'])
    for p in me.polygons:      # the butt plate keeps its old orange paint
        if (Vector(p.center) - G0).dot(S_) < -46.9 * MM:
            p.material_index = 1
    G.shade(back, 40, weighted=True)
    CT.part(back, 'pistol', 'housing', 'Backstrap housing', parent='frame', material='steel', mass='medium', symmetry=1, tol_mm=5, tol_deg=15,
            held_by=['housing_pin'], steps=['s1.housing'], origin=GP(-16, 20), touches=['scale_l', 'scale_r', 'housing_spring', 'lead', 'wrap'],
            note='backstrap, pin ears, heel and orange butt plate in one piece; rides the T-rail of the tang and slides off downward')
    CT.clear(back, offset=-S_ * 70 * MM)
    return back


def build_pin_spring():
    pin = G.pin('housing_pin', GP(PG.PIN[0], PG.PIN[1], -15.0), GP(PG.PIN[0], PG.PIN[1], 15.0), 1.5 * MM, 12, M['steel_bright'])
    G.set_frame(pin, AP.frame_matrix(GP(PG.PIN[0], PG.PIN[1], 15.0), Y, S_))
    CT.fastener(pin, 'pistol', 'housing_pin', 'Housing pin', bit='pin', turns=0, holds=['housing'], into='frame', shank_d=3.0 * MM, parent='frame',
                material='steel', steps=['s1.pin', 's6.pin'], touches=['housing'])
    CT.clear_along(pin, 48 * MM)
    CT.mark(pin, 'punch', GP(PG.PIN[0], PG.PIN[1], -15.0), -Y)
    sp = AP.spring('housing_spring', 10.3 * MM, 4.2 * MM, 0.55 * MM, 6, M['steel_bright'], per_turn=12, wire_segs=5, at=GP(-13.6, 22.0), axis=-U_, ref=S_)
    CT.part(sp, 'pistol', 'housing_spring', 'Housing spring', parent='frame', material='steel', mass='tiny', symmetry=0, tol_mm=4, tol_deg=30,
            held_by=['housing'], steps=['s1.housing'], flex=True, touches=['housing'], note='sits in a blind hole in the back of the T-rail; it jumps when the housing slides off')
    CT.clear_along(sp, 22 * MM)
    return pin, sp


def _smooth(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def wire_track(seed, s_c, th_t):
    """(theta mod 2 pi, s) of the binding wire's centre line, the same numbers build_wires() draws"""
    rr = random.Random(seed)
    sw = lambda th: s_c + 2.6 * math.cos((th - th_t) / 2) + 0.8 * math.sin(th * 2 + seed)
    out = []
    for k in range(72):
        th = th_t + 4 * math.pi * k / 72
        out.append((th % (2 * math.pi), sw(th) + rr.uniform(-0.25, 0.25)))
    return out


def back_pad(mat, s_mid=-13.8, y_half=7.5, top=2.45, lift=0.08):
    """21 Nov (ruling on integration's 08:28 numbers check): a folded leather pad on the backstrap between the two turns of
    binding wire A, where the frozen grip_gyro_braced mod's brace bar lands its top end (P x 115, z -29) and the Meshy skin
    stands 2.7 to 3.1 mm proud of the housing. It lies between the turns at every angle (0.4 mm clear of the wire)."""
    tr = wire_track(2, -14.5, math.radians(215))
    b = PG.section(s_mid)[2]
    dth = math.asin(min(1.0, (y_half / b) ** 1.5))
    nth, ns = 13, 7
    cols = []
    for i in range(nth):
        th = math.pi - dth + 2 * dth * i / (nth - 1)
        near = [s for t, s in tr if abs((t - th + math.pi) % (2 * math.pi) - math.pi) < 0.12]
        hi = min([s for s in near if s > s_mid] + [s_mid + 3.0]) - 0.6 - 0.4
        lo = max([s for s in near if s < s_mid] + [s_mid - 3.0]) + 0.6 + 0.4
        cols.append((th, lo, hi))
    verts, faces = [], []
    def vid(k, i, j):
        return (k * nth + i) * ns + j
    for k, off in ((0, None), (1, lift)):
        for i, (th, lo, hi) in enumerate(cols):
            for j in range(ns):
                sj = lo + (hi - lo) * j / (ns - 1)
                if off is None:
                    e = min(i, nth - 1 - i, j, ns - 1 - j)
                    o_ = lift + (top - lift) * (0.45 + 0.55 * _smooth(0, 1.5, e))
                else:
                    o_ = off
                verts.append(tuple(PG.surf(th, sj, o_)[0]))
    for i in range(nth - 1):
        for j in range(ns - 1):
            faces.append((vid(0, i, j), vid(0, i + 1, j), vid(0, i + 1, j + 1), vid(0, i, j + 1)))
            faces.append((vid(1, i, j), vid(1, i, j + 1), vid(1, i + 1, j + 1), vid(1, i + 1, j)))
    for i in range(nth - 1):           # the two long edges
        faces.append((vid(1, i, 0), vid(1, i + 1, 0), vid(0, i + 1, 0), vid(0, i, 0)))
        faces.append((vid(0, i, ns - 1), vid(0, i + 1, ns - 1), vid(1, i + 1, ns - 1), vid(1, i, ns - 1)))
    for j in range(ns - 1):            # the two ends
        faces.append((vid(0, 0, j), vid(0, 0, j + 1), vid(1, 0, j + 1), vid(1, 0, j)))
        faces.append((vid(1, nth - 1, j), vid(1, nth - 1, j + 1), vid(0, nth - 1, j + 1), vid(0, nth - 1, j)))
    me = bpy.data.meshes.new('back_pad'); me.from_pydata(verts, [], faces); me.update()
    o = bpy.data.objects.new('back_pad', me); bpy.context.scene.collection.objects.link(o)
    me.materials.append(mat)
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    G.shade(o, 45)
    return o


def gyro_heel(objs, push=1.2):
    """21 Nov (same ruling): the brace bar's lower end bears on the heel of the backstrap, where the Meshy skin stands 1.0 to
    1.6 mm behind the housing (P x 125..130, z -56..-68). Every part there is shifted back by up to `push` mm along +x with
    smooth ramps (grip level s -41 -> -44; x 67 -> 78 mm, behind the front strap and ahead of the housing). One smooth field for
    all parts, with no ramp across a face where two parts meet: neighbours move together. Helper empties are not moved."""
    n = 0
    SHADE = {'pistol_housing': (40, True), 'pistol_scale_l': (42, True), 'pistol_scale_r': (42, True)}
    for o in objs:
        if o.type != 'MESH':
            continue
        Mw = o.matrix_world; Mi = Mw.inverted(); R3 = Mw.to_3x3().transposed()
        if o.name in SHADE:
            # cut the faces in the ramps into slices first, so that a big face follows the field as its neighbour does
            # (the housing and the scales meet across the ramp: linear faces against a smooth field crossed by 0.1 mm)
            bm = bmesh.new(); bm.from_mesh(o.data)
            wv = lambda v: Mw @ v.co
            planes = [(G0 + S_ * (sv * MM), S_) for sv in [-39.77 - 0.5 * k for k in range(10)]] + \
                     [(Vector((xv * MM, 0, 0)), X) for xv in [67.13 + 1.5 * k for k in range(8)]]
            for co, nrm in planes:
                geom = [f for f in bm.faces if any(((wv(v) - G0).dot(S_) / MM) < -38.5 for v in f.verts)]
                if not geom:
                    continue
                gset = set(geom) | {e for f in geom for e in f.edges} | {v for f in geom for v in f.verts}
                bmesh.ops.bisect_plane(bm, geom=list(gset), dist=1e-7, plane_co=Mi @ co, plane_no=R3 @ nrm)
            bmesh.ops.dissolve_degenerate(bm, dist=2e-6, edges=bm.edges)
            bm.to_mesh(o.data); bm.free()
        for v in o.data.vertices:
            p = Mw @ v.co
            s = (p - G0).dot(S_) / MM
            w = _smooth(-40.0, -44.5, s) * _smooth(67.0, 78.0, p.x / MM)       # the ramp only crosses the scales and wrap (dense): the housing moves as one
            if w > 0:
                v.co = Mi @ (p + X * (push * MM * w)); n += 1
        o.data.update()
        if o.name in SHADE:
            G.shade(o, *SHADE[o.name])
    return n


def build_wrap():
    lt, tp = M['leather_tan'], M['tape']
    bits = []
    # the centre lines of the peel path are those of the first build (pgeom.band): the path must not move
    _o, c3 = PG.band('_c3', -38.2, 12.0, 1.6, 48, None, tilt=(1.8, 3.6), wobble=0.4, seed=7)
    bpy.data.objects.remove(_o, do_unlink=True)
    _o, ct2 = PG.band('_ct2', -30.5, 9.5, 0.55, 40, None, turns=2.6, pitch=5.6, wobble=0.3, seed=13, th0=4.0, peel=4.0)
    bpy.data.objects.remove(_o, do_unlink=True)
    # wound by hand: straps that wander, change width and lap over their own start; tape whose turns ride on each other
    s1 = PX.band('strap1', 9.0, 13.0, 1.6, 48, lt, tilt=(3.5, 0.6), seed=3, th0=2.5, lap=17.0, wander=0.7, wvar=1.1, sid=1)
    s2 = PX.band('strap2', -7.5, 13.5, 1.6, 48, M['leather'], tilt=(4.0, 2.4), seed=5, th0=4.1, lap=22.0, wander=0.8, wvar=1.2, sid=2)
    # strap3 1.4 thick, not 1.6 (21 Nov): where tape2 laps it the pair stood 0.7 mm proud of the Meshy skin, 1.07 mm into the gyro mod's bar
    s3 = PX.band('strap3', -38.2, 12.0, 1.4, 48, lt, tilt=(1.8, 3.6), seed=7, th0=1.2, lap=14.0, wander=0.6, wvar=1.0, sid=3)
    t1 = PX.band('tape1', 17.0, 9.0, 0.55, 40, M['tape_khaki'], turns=2.3, pitch=5.2, seed=9, th0=2.0, peel=3.2, wander=0.5, wvar=0.7, tvar=0.0, ride=3.8, cut=2.4, sid=4)
    t2 = PX.band('tape2', -30.5, 9.5, 0.55, 40, tp, turns=2.6, pitch=5.6, seed=13, th0=4.0, peel=4.0, wander=0.5, wvar=0.7, tvar=0.0, ride=3.9, cut=2.4, sid=5)
    bits += [t1, t2, s1, s2, s3]
    # two studs a side: their posts press into holes C and D of the scales
    for k in 'CD':
        u, s = PG.HOLES[k]
        for side in (-1, 1):
            ub, uf, b = PG.section(s)
            uc = (ub + uf) / 2; a = (uf - ub) / 2
            yy = b * (1 - abs((u - uc) / a) ** PG.NEXP) ** (1 / PG.NEXP)
            top = yy + 1.75
            bits.append(G.cyl('post', GP(u, s, side * (yy - 5.0)), GP(u, s, side * top), 1.45 * MM, 10, M['brass']))
            prof = [(0, 0), (0, 3.6), (1.6, 3.5), (3.4, 2.7), (4.6, 1.5), (5.0, 0)]
            bits.append(G.lathe('stud', [([(q * MM, r * MM) for q, r in prof], False)], 14, GP(u, s, side * top), Y * side, S_, M['brass']))
    # the strap's own snap rivets at the widest part of the grip (the skin has them: they set the overall width)
    for side in (-1, 1):
        b = PG.section(-7.5)[2]
        prof = [(0, 0), (0, 3.6), (1.6, 3.5), (3.0, 2.7), (3.8, 1.5), (4.2, 0)]
        bits.append(G.lathe('snap', [([(q * MM, r * MM) for q, r in prof], False)], 14, GP(-2.0, -7.5 - 4.0 * math.cos(math.pi / 2 * side - 2.4), side * (b + 1.7)),
                            Y * side, S_, M['steel']))
    bits.append(back_pad(M['leather']))
    o = G.join('wrap', bits)
    G.shade(o, 45)
    CT.part(o, 'pistol', 'wrap', 'Leather strips and tape', parent='frame', material='canvas', mass='light', flex=True, steps=['s1.tape'],
            held_by=['bind_wire_a', 'bind_wire_b'], origin=GP(0, -10), touches=['scale_l', 'scale_r', 'housing'],
            note='three leather straps, two bands of cloth tape and four studs whose posts sit in holes C and D; peeled along path peel')
    CT.clear(o, offset=-U_ * 30 * MM - S_ * 30 * MM)
    pts = [p for p, n in ct2] + [p for p, n in c3[::-1]]
    nrm = [n for p, n in ct2] + [n for p, n in c3[::-1]]
    idx = [int(round(i * (len(pts) - 1) / 35)) for i in range(36)]
    CT.path(o, 'peel', [pts[i] for i in idx], [nrm[i] for i in idx])
    return o


def build_wires():
    out = []
    for nm, s, th_t, seed in (('bind_wire_a', -14.5, math.radians(215), 2), ('bind_wire_b', -34.0, math.radians(210), 4)):     # b twisted on the left too (bench, 21 Nov: the right faces away from the bench camera)
        rr = random.Random(seed)
        loop = []
        n = 72                     # two turns round the grip, crossing once at the back
        sw = lambda th: s + 2.6 * math.cos((th - th_t) / 2) + 0.8 * math.sin(th * 2 + seed)
        for k in range(n):
            th = th_t + 4 * math.pi * k / n
            loop.append(PG.surf(th, sw(th) + rr.uniform(-0.25, 0.25), 2.5 + 0.7 * math.sin((th - th_t) / 2) ** 2)[0])
        w = PX.tube(nm, loop, 0.6 * MM, 6, M['wire_cu'], closed=True, sid=1)
        base, nrm = PG.surf(th_t, sw(th_t), 2.5)
        tang = (PG.surf(th_t + 0.05, sw(th_t), 2.5)[0] - PG.surf(th_t - 0.05, sw(th_t), 2.5)[0]).normalized()
        ax = (nrm * 0.75 + tang * 0.45 - S_ * 0.35).normalized()
        bits = [w]
        for ph in (0.0, math.pi):
            h = G.helix(base, ax, tang, 0.62 * MM, 2.4 * MM, 3.2, 10, phase=ph)
            bits.append(PX.tube('tw', h, 0.6 * MM, 6, M['wire_cu'], sid=2 if ph == 0.0 else 3))
        o = G.join(nm, bits)
        G.shade(o, 60)
        CT.part(o, 'pistol', nm, 'Binding wire twist', parent='frame', material='copper', mass='tiny', flex=True, steps=['s1.bind'], origin=base,
                touches=['wrap', 'scale_l', 'scale_r', 'housing'], note='one turn of copper wire round the grip, twisted shut; snip at mark snip')
        CT.clear(o, offset=nrm * 30 * MM)
        CT.mark(o, 'snip', base + ax * 1.2 * MM, nrm)
        out.append(o)
    return out


def build_cards():
    out = []
    for nm, x, z in (('card_a', -45, -112.0), ('card_b', 85, -114.0)):
        o = G.prism(nm, [(a * MM, b * MM) for a, b in PG.fillet([(-74, -52.5), (74, -52.5), (74, 52.5), (-74, 52.5)], 4, 3)], 0.4 * MM, (0, 0, 0), X, Y, Z, M['paper'], w0=0.0)
        G.boolean(o, [G.cyl('_ch', (0, 0.044, -0.01), (0, 0.044, 0.01), 2.6 * MM, 12)])
        paint(o, M['paper'])
        o.matrix_world = Matrix.Translation(P(x, 0, z))
        CT.part(o, 'pistol', nm, 'Test card', kind='consumable', material='paper', mass='tiny', loose=True, steps=['s0.card_before', 's7.card_after'],
                note='blank card, 148 x 105; the game places the hole decals. Mark centre is the aim point, mark clip the hole for the board clip')
        CT.mark(o, 'centre', P(x, 0, z + 0.4), Z)
        CT.mark(o, 'clip', P(x, 44, z + 0.4), Z)
        out.append(o)
    return out


# ====================================================================== build
gs = PG.solid('grip_solid', mat=M['wood_scale'])
blank_l, blank_r = scale_blank(gs, -1), scale_blank(gs, 1)
frame = build_frame([blank_l, blank_r]); F.log('frame', G.tris(frame))
barrel = build_barrel()
dust = build_dust_cover()
trigger = build_trigger()
lead = build_lead()
bus = build_bus()
plug = build_plug()
cell = build_cell()
latch = build_latch()
lamp = build_lamp()
scale_l, scale_r = build_scales(blank_l, blank_r)
screws = build_grip_screws()
housing = build_housing(gs)
pin, spring = build_pin_spring()
wrap = build_wrap()
wires = build_wires()
cards = build_cards()
bpy.data.objects.remove(gs, do_unlink=True)
for o in list(bpy.data.objects):          # leftovers of failed booleans or helpers
    if o.type == 'MESH' and 'sh' not in o:
        F.log('removing stray object', o.name)
        bpy.data.objects.remove(o, do_unlink=True)
F.log('gyro heel: vertices moved', gyro_heel([o for o in F.parts().values() if o not in cards]))
F.log('built', {o.name: G.tris(o) for o in F.parts().values()})

R = F.rig = RG.Rig('pistol', parent=frame)
R.hinge('cell_latch', P(PAWL_X, BY, CZ - 5.5), Y, 0, 22, [latch])
R.slide('cell_seat', P(-61.0, BY, CZ), Z, 0, 16 * MM, [cell], requires={'cell_latch': 1.0})
R.hinge('trigger', P(10.5, YC, 22.3), -Y, 0, 12, [trigger])
R.finish()

CT.sequence([
    {'op': 'remove', 'part': 'cell', 'step': 's0.cell', 'params': {'cell_latch': 1.0}},
    {'op': 'remove', 'part': 'bind_wire_a', 'step': 's1.bind', 'group': 'bind'},
    {'op': 'remove', 'part': 'bind_wire_b', 'step': 's1.bind', 'group': 'bind'},
    {'op': 'remove', 'part': 'wrap', 'step': 's1.tape'},
    {'op': 'remove', 'part': 'screw_grip_a', 'step': 's1.screw_a', 'group': 'screws'},
    {'op': 'remove', 'part': 'screw_grip_b', 'step': 's1.screw_b', 'group': 'screws'},
    {'op': 'remove', 'part': 'scale_l', 'step': 's1.scales', 'group': 'scales'},
    {'op': 'remove', 'part': 'scale_r', 'step': 's1.scales', 'group': 'scales'},
    {'op': 'remove', 'part': 'lead_plug', 'step': 's1.lead'},
    {'op': 'remove', 'part': 'housing_pin', 'step': 's1.pin'},
    {'op': 'remove', 'part': 'housing', 'step': 's1.housing'},
    {'op': 'remove', 'part': 'housing_spring', 'step': 's1.housing'},
    {'op': 'insert', 'part': 'cell', 'step': 's6.cell', 'params': {'cell_latch': 1.0}},
])
F.uv_weights = {'pistol_frame': 1.0, 'pistol_card_a': 0.35, 'pistol_card_b': 0.35, 'pistol_wrap': 0.9}
F.uv_align = '--noalign' not in ARGS          # the grip lies at 25 degrees: its islands are turned square before packing
F.review_hero = ('pistol_cell', 'pistol_scale_l')
F.review_objs = [o for o in F.parts().values() if o not in cards]
# the exploded view: every part at its __clear pose, the ones that stay on pulled apart by hand
mm = lambda x, y, z: Vector((x, y, z)) * MM
F.explode = {'f': 1.0, 'extra': {
    'pistol_barrel': mm(-38, 0, 0), 'pistol_dust_cover': mm(-26, 0, -14), 'pistol_trigger': mm(0, 0, -24), 'pistol_cell_bus': mm(0, -30, 6),
    'pistol_cell_latch': mm(8, 0, 22), 'pistol_status_lamp': mm(16, 0, 0), 'pistol_lead': mm(26, 0, 6), 'pistol_lead_plug': mm(22, 0, -4),
    'pistol_screw_grip_a': mm(0, -42, 0), 'pistol_screw_grip_b': mm(0, -42, 0), 'pistol_housing_pin': mm(0, 22, 0),
    'pistol_housing_spring': mm(14, 0, 8), 'pistol_wrap': mm(44, 0, -34), 'pistol_bind_wire_a': mm(30, 0, -52), 'pistol_bind_wire_b': mm(34, 0, -60),
    'pistol_cell': mm(0, 0, -8)}}

# ====================================================================== the fixed numbers, against the skin
import outline_check
if not ({'fast', 'noout'} & PX.DIAG):
    outline_check.run(F, cards, nomods='--nomods' in ARGS)

if 'nopatch' not in PX.DIAG:
    PX.install(F)      # the kit's unwrap, bake and assign_runtime with the pistol's additions (px.py); the kit is not edited
pj, st = F.finish(export=not ({'fast', 'noexp'} & PX.DIAG), extra={'frame': 'P: metres, muzzle -X, up +Z, right +Y in Blender (glTF: muzzle -X, up +Y, right -Z); origin = ScrapPistol.glb origin',
                         'in_hand': 'pistol_hand.glb: merged nodes in ScrapPistol.glb units (x 1 / 0.13674), written after a bake'})

# ====================================================================== the in-hand copy (only after a bake)
if not F.nobake:
    PP = F.parts()
    g = lambda *ids: [PP['pistol.' + i] for i in ids]
    # the in-hand copy keeps a 2048 set made from the same bake
    tex_now = {}
    for mn in ('M_pistol', 'M_pistol_emissive', 'glass_cell'):
        m_ = bpy.data.materials.get(mn)
        for n_ in (m_.node_tree.nodes if m_ else []):
            if n_.type == 'TEX_IMAGE' and n_.image:
                for k_ in ('color', 'normal', 'orm', 'emit'):
                    if n_.image.name == 'pistol_' + k_:
                        tex_now[k_] = n_.image
    small = PX.hand_textures(tex_now, F.out, 'pistol', 2048)
    swapped = []
    if small:
        for m_ in bpy.data.materials:
            if m_.use_nodes:
                for n_ in m_.node_tree.nodes:
                    if n_.type == 'TEX_IMAGE' and n_.image:
                        for k_, im_ in tex_now.items():
                            if n_.image == im_:
                                swapped.append((n_, im_)); n_.image = small[k_]
    hand = BK.export_merged(os.path.join(F.out, 'pistol_hand.glb'), {
        'ScrapPistol': g('frame', 'barrel', 'dust_cover', 'cell_bus', 'cell_latch', 'housing_pin'),
        'ScrapPistol_cell': g('cell'),
        'ScrapPistol_trigger': g('trigger'),
        'ScrapPistol_lamp': g('status_lamp'),
        'ScrapPistol_grip_stock': g('scale_l', 'scale_r', 'screw_grip_a', 'screw_grip_b', 'housing', 'wrap', 'bind_wire_a', 'bind_wire_b', 'lead', 'lead_plug'),
    }, 1.0 / PF.S)
    for n_, im_ in swapped:
        n_.image = im_
    sp = os.path.join(F.out, 'stats.json')
    sj = json.load(open(sp))
    sj['in_hand_textures'] = {'size': 2048 if small else F.size, 'files': ['tex/pistol_hand_%s.png' % k_ for k_ in small] if small else 'the family atlas'}
    sj['in_hand'] = {'glb': 'pistol_hand.glb', 'bytes': os.path.getsize(os.path.join(F.out, 'pistol_hand.glb')), 'units': 'ScrapPistol.glb units (metres / 0.13674), its origin and axes',
                     'nodes': hand, 'note': 'ScrapPistol_grip_stock is hidden when grip_stabilised_pistol is fitted; ScrapPistol_trigger pivots about pistol.trigger; '
                                            'the housing spring is left out (it cannot be seen)'}
    json.dump(sj, open(sp, 'w'), indent=1)
    F.log('in-hand copy', hand)

if 'clearM' in PX.DIAG:
    import gc
    M.clear(); F.mats = {}
    gc.collect()
    print('[diag] cleared the material references', flush=True)
