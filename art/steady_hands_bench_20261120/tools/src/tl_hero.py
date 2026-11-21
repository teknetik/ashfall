# tl_hero.py: model-tools' rebuild of model-bench's slice tools (21 Nov 2026): pliers, cutters, screwdriver, bit block,
# punch, mallet. Each returns the same dict as its tl_parts.build_* did, with the same working points (the tip, the bit
# socket, the pivot at the origin, y_tip), so tl_parts.finish_* place them, and the roll's seat marks, the rigs and
# every helper empty land where they were. What changes is the form and the materials (tl_mats2).
import math
import bpy
from mathutils import Vector, Matrix
import mbk
from mbk import G, MT, CT, AP, MM, X, Y, Z, O, T, R4, join, turned, ring_prof, box
import tl_kit as K
import tl_mats2 as T2
import tl_new as TN
import tl_parts as TL
import tl_mats
from tl_kit import settle, sup, loft_path, baked

HEX_AF = 6.35 * MM


# ====================================================================== combination pliers (black cloth tape)
def build_pliers(F, M):
    th, st = 0.0095, 0.0012
    teeth = TL.serrate((-0.0001, 0.0500), (-0.0001, 0.0300), 0.0011, 0.00055)
    jaw = teeth + [(-0.0026, 0.0272), (-0.0040, 0.0214), (-0.0026, 0.0156), (-0.0006, 0.0128), (-0.0001, 0.0104), (-0.0118, 0.0100),
                   (-0.0110, 0.0210), (-0.0092, 0.0330), (-0.0068, 0.0440), (-0.0046, 0.0495), (-0.0024, 0.0503)]
    hp = [(0.0050, -0.0060), (0.0090, -0.0140), (0.0135, -0.0300), (0.0180, -0.0520), (0.0212, -0.0760), (0.0222, -0.0960), (0.0214, -0.1080),
          (0.0205, -0.1130)]
    hw = lambda f: 0.0112 - 0.0026 * f + 0.0008 * math.sin(math.pi * f)
    ht = lambda f: th * (0.98 - 0.18 * f)
    sm = T2.forged('t_pliers_steel', oxide=0.55)
    jm = T2.forged('t_pliers_jaw', base=(0.50, 0.505, 0.515), oxide=0.3, edge=1.0)
    tl_mats.stamp_triangle(jm, -0.0066, 0.0185)
    ta = T2.cloth_tape('t_pliers_tape_a', (0.0135, -0.030, th / 2 + st), (0.105, -0.994, 0), 0.0, 0.090)
    tb = T2.cloth_tape('t_pliers_tape_b', (-0.0135, -0.030, th / 2 + st), (-0.105, -0.994, 0), 0.0, 0.090)
    a, b = TN.scissor_pair('pliers', jaw, lambda x, y: th / 2 * (1.0 - 0.32 * max(0.0, (y - 0.0125) / 0.0375)), hp, hw, ht, th, 0.0128, sm, jm,
                           rivet_d=0.0090, sleeve=(-0.030, st, ta, tb))
    return dict(root=a, b=b, y_tip=0.050, y_butt=-0.116, thick=th + 2 * st, width=0.054, z0=st)


# ====================================================================== diagonal cutters (red dip worn through)
def build_cutters(F, M):
    th, st = 0.009, 0.0016
    jaw = [(-0.00006, 0.0345), (-0.00006, 0.0100), (-0.0112, 0.0100), (-0.0108, 0.0140), (-0.0092, 0.0225), (-0.0062, 0.0300), (-0.0030, 0.0340),
           (-0.0012, 0.0350)]
    hp = [(0.0045, -0.0060), (0.0085, -0.0130), (0.0128, -0.0280), (0.0168, -0.0480), (0.0186, -0.0700), (0.0182, -0.0900), (0.0170, -0.1000),
          (0.0160, -0.1030)]
    hw = lambda f: 0.0102 - 0.0022 * f
    ht = lambda f: th * (0.96 - 0.16 * f)
    sm = T2.forged('t_cut_steel', oxide=0.5)
    bm = T2.bright('t_cut_blade', base=(0.60, 0.605, 0.61), rough=0.3)
    ra, rb = T2.red_dip('t_cut_dip_a'), T2.red_dip('t_cut_dip_b')
    a, b = TN.scissor_pair('cutters', jaw, lambda x, y: th / 2 * (0.10 + 0.90 * min(1.0, abs(x) / 0.0112)), hp, hw, ht, th, 0.0114, sm, bm,
                           rivet_d=0.0078, sleeve=(-0.024, st, ra, rb))
    return dict(root=a, b=b, y_tip=0.0345, y_butt=-0.1055, thick=th + 2 * st, width=0.048, z0=st)


# ====================================================================== screwdriver with its bits and the bit block
def build_screwdriver(F, M):
    y0 = -0.095
    og = (0, y0, 0)
    wd = T2.wood('t_sd_wood', base=(0.33, 0.20, 0.11), dark=(0.11, 0.06, 0.035), rough=0.36, polish=0.7)
    T2.rings(wd, 1, [y0 + 0.0120, y0 + 0.0150, y0 + 0.0590, y0 + 0.0625], width=0.0008)
    br = T2.brass('t_sd_brass')
    sh = T2.bright('t_sd_shaft', base=(0.62, 0.625, 0.63), rough=0.28)
    kn = T2.nickel('t_sd_collar', base=(0.56, 0.565, 0.57))
    T2.knurl_band(kn, (0, y0 + 0.171, 0), (0, 1, 0), y0 + 0.1725 - (y0 + 0.171), y0 + 0.1855 - (y0 + 0.171), n=36, pitch=0.0008)
    hp = [(0, 0), (0.0010, 0.0060), (0.0035, 0.0105), (0.0090, 0.0130), (0.0180, 0.0140), (0.0300, 0.0142), (0.0420, 0.0138), (0.0520, 0.0128),
          (0.0575, 0.0121), (0.0590, 0.0114), (0.0605, 0.0121), (0.0640, 0.0118), (0.0655, 0.0111), (0.0670, 0.0117), (0.0780, 0.0104), (0.0880, 0.0096),
          (0.0965, 0.0093), (0.0970, 0)]
    handle = turned('h', hp, 32, wd, axis=Y, origin=og)
    fer = turned('f', [(0.0955, 0), (0.0955, 0.0096), (0.0965, 0.0101), (0.0995, 0.0101), (0.1001, 0.0097), (0.1065, 0.0097), (0.1072, 0.0092),
                       (0.1095, 0.0080), (0.1095, 0)], 32, br, axis=Y, origin=og)
    shaft = turned('s', [(0.108, 0), (0.108, 0.0031), (0.1675, 0.0031), (0.1690, 0.0048), (0.1893, 0.0048), (0.1900, 0.0042), (0.1900, 0)],
                   24, sh, axis=Y, origin=og)
    rc = (HEX_AF + 0.15 * MM) / 2 / math.cos(math.radians(30))
    shaft = G.boolean(shaft, [G.prism('_hx', G.circle(rc, 6), 0.0132, (0, y0 + 0.190 - 0.013, 0), Z, X, Y, w0=0.0)])
    collar = AP.knurled_band('collar', 0.0124, 0.016, n=36, depth=0.00035, mat=kn, at=(0, y0 + 0.171, 0), axis=Y, ref=Z, d_in=0.0099)
    TL.bake_place([collar])
    slot = TL.make_bit('bit_slot', 'slot', {'t_shaft': T2.forged('t_bit_sh', base=(0.36, 0.37, 0.385), oxide=0.25), 't_steel_bright': T2.bright('t_bit_tip')})
    slot.data.transform(T((0, y0 + 0.1775, 0)))
    pcs = [handle, fer, shaft, collar, slot]
    Mr = settle(pcs, about=-0.03)
    K.frame_mats([handle, fer, shaft, collar], Mr)
    sd = join('screwdriver', [handle, fer, shaft])
    G.shade(sd, 38)
    return dict(root=sd, collar=collar, slot=slot, Mr=Mr, tip=Mr @ Vector((0, y0 + 0.2225, 0)), axis=(Mr.to_3x3() @ Y).normalized(),
                sock=Mr @ Vector((0, y0 + 0.1775, 0)), grab=Mr @ Vector((0, y0 + 0.045, 0)), y_tip=y0 + 0.2225, y_butt=y0, thick=0.029, width=0.029)


def build_bitblock(F, M):
    wd = T2.wood('t_bb_wood', base=(0.50, 0.37, 0.22), dark=(0.28, 0.18, 0.10), rough=0.55, polish=0.4)
    blk = box('blk', (-0.015, 0.0, 0.0), (0.015, 0.024, 0.016), wd, bevel=0.0016, segs=3)
    rc = (HEX_AF + 0.2 * MM) / 2 / math.cos(math.radians(30))
    blk = G.boolean(blk, [G.prism('_h', G.circle(rc, 6), 0.0135, (sx * 0.0075, -0.0005, 0.008), Z, X, Y, w0=0.0) for sx in (-1, 1)])
    cross = TL.make_bit('bit_cross', 'cross', {'t_shaft': T2.forged('t_bit_sh2', base=(0.36, 0.37, 0.385), oxide=0.25), 't_steel_bright': T2.bright('t_bit_tip2')})
    G.shade(blk, 35)
    return dict(root=blk, cross=cross, y_tip=0.024, y_butt=-0.033, thick=0.017, width=0.030)


# ====================================================================== pin punch (blued, knurled band, mushroomed head)
def build_punch(F, M):
    y0 = -0.060
    og = (0, y0, 0)
    bm = T2.blued('t_punch_body')
    T2.knurl_band(bm, (0, y0, 0), (0, 1, 0), 0.010, 0.052, n=40, pitch=0.0008, strength=1.2)
    hm = T2.forged('t_punch_head', base=(0.40, 0.405, 0.41), oxide=0.4, edge=1.0)
    nm = T2.bright('t_punch_pin', base=(0.64, 0.645, 0.65), rough=0.26)
    yh = y0 - 0.020          # the head end 20 mm longer than model-bench's (21 Nov): it shows above the pocket mouth; the tip is where it was
    head = turned('ph', [(0, 0), (0.0001, 0.0030), (0.0006, 0.0046), (0.0014, 0.0058), (0.0024, 0.0061), (0.0034, 0.0057), (0.0040, 0.0049),
                         (0.0060, 0.0041), (0.0125, 0.0040), (0.0125, 0)], 20, hm, axis=Y, origin=(0, yh, 0))
    rc = 0.004 / math.cos(math.radians(22.5))
    body = G.prism('pb', G.circle(rc, 8, phase=math.radians(22.5)), 0.0935, (0, yh + 0.012, 0), Z, X, Y, bm, w0=0.0)
    G.bevel(body, 0.0004, 1)
    nose = turned('pn', [(0.0850, 0), (0.0850, 0.0040), (0.0865, 0.0040), (0.0945, 0.0019), (0.0952, 0.0015), (0.1196, 0.0015), (0.1200, 0.0012), (0.1200, 0)],
                  14, nm, axis=Y, origin=og)
    pcs = [head, body, nose]
    Mr = settle(pcs)
    K.frame_mats(pcs, Mr)
    p = join('punch', pcs)
    G.shade(p, 35)
    return dict(root=p, Mr=Mr, tip=Mr @ Vector((0, y0 + 0.120, 0)), axis=(Mr.to_3x3() @ Y).normalized(), strike=Mr @ Vector((0, yh, 0)),
                grab=Mr @ Vector((0, y0 + 0.04, 0)), y_tip=y0 + 0.120, y_butt=yh, thick=0.0122, width=0.0122)


# ====================================================================== mallet (Brann's): steel barrel, brass and rawhide faces, taped hickory handle
def build_mallet(F, M):
    y0 = -0.140
    wd = T2.wood('t_mallet_wood', base=(0.46, 0.31, 0.17), dark=(0.20, 0.12, 0.06), rough=0.5, polish=0.5)
    tp = T2.cloth_tape('t_mallet_tape', (0, y0, 0), (0, 1, 0), 0.012, 0.108, pitch=0.0080)
    st = T2.forged('t_mallet_steel', base=(0.40, 0.405, 0.415), oxide=0.6)
    bf = T2.brass('t_mallet_brass', base=(0.70, 0.56, 0.32), rough=0.45, axis='X')
    rh = MT.make('t_mallet_hide', (0.62, 0.55, 0.42), 0.0, 0.8, var=0.12, edge=((0.74, 0.68, 0.56), 0.0, 0.9, 0.7), edge_width=0.001,
                 dirt=((0.22, 0.18, 0.13), 0.85, 0.9), bumps=[('lathe', 'X', 700, 0.6), ('noise', 500, 0.4)], grime=0.7,
                 tone2=((0.36, 0.30, 0.22), 40, 0.4, 0.66, 0.8))
    hp = [(0, 0), (0.0015, 0.0098), (0.006, 0.0132), (0.016, 0.0140), (0.040, 0.0136), (0.075, 0.0126), (0.104, 0.0114), (0.118, 0.0106), (0.160, 0.0100),
          (0.200, 0.0097), (0.238, 0.0101), (0.277, 0.0101), (0.2785, 0.0093), (0.2785, 0)]
    grip = turned('mg', [(a_, r_ * 0.94 + 0.0006) for (a_, r_) in hp if a_ <= 0.1085] + [(0.1085, 0.0110), (0.1085, 0)], 32, tp, axis=Y, origin=(0, y0, 0))
    hd = turned('mh', [(0.1075, 0), (0.1075, 0.0108)] + [p for p in hp if p[0] >= 0.112], 28, wd, axis=Y, origin=(0, y0, 0))
    for o in (grip, hd):
        o.data.transform(Matrix.Diagonal((1.0, 1.0, 0.84, 1.0)))
    yc = y0 + 0.258
    c = (0, yc, 0)
    brass = turned('mb', [(-0.0400, 0), (-0.0400, 0.0160), (-0.0392, 0.0182), (-0.0378, 0.0190), (-0.0262, 0.0189), (-0.0255, 0.0180), (-0.0255, 0)],
                   40, bf, axis=X, origin=c)
    barrel = turned('ms', [(-0.0258, 0), (-0.0258, 0.0176), (-0.0245, 0.0176), (-0.0240, 0.0192), (-0.0190, 0.0192), (-0.0185, 0.0176), (0.0135, 0.0176),
                           (0.0140, 0.0192), (0.0190, 0.0192), (0.0195, 0.0176), (0.0208, 0.0176), (0.0208, 0)], 40, st, axis=X, origin=c)
    hide = turned('mr', [(0.0205, 0), (0.0205, 0.0182), (0.0215, 0.0188), (0.0340, 0.0192), (0.0380, 0.0196), (0.0396, 0.0186), (0.0400, 0.0165), (0.0400, 0)],
                  40, rh, axis=X, origin=c)
    wedge = box('mw', (-0.0050, yc + 0.0176, -0.0012), (0.0050, yc + 0.0212, 0.0012), st, bevel=0.0003)
    pcs = [grip, hd, brass, barrel, hide, wedge]
    Mr = settle(pcs, about=yc - 0.06)
    K.frame_mats(pcs, Mr)
    m = join('mallet', pcs)
    G.shade(m, 40)
    return dict(root=m, Mr=Mr, tip=Mr @ Vector((-0.040, yc, 0)), soft=Mr @ Vector((0.040, yc, 0)), grab=Mr @ Vector((0, y0 + 0.06, 0)))
