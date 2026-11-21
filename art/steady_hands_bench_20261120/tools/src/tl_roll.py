# tl_roll.py: the Field Toolkit roll. Waxed canvas with nine stitched pockets, a fold-over flap and a leather strap,
# as ONE skinned mesh on its own armature (cloth cannot be rigid parts). Bind pose: unrolled flat, flap open, strap
# laid out. Two clips: 'roll_unroll_param' (0 = rolled bundle at the left end, 0.8 = flat, 1 = flap folded open) and
# 'roll_strap_param' (0 = buckled round the bundle, 1 = lying beside the roll).
# Roll frame: centre of the unrolled canvas on the bench, X right, Y away from the player, Z up.
import math, json
import bpy, bmesh
from mathutils import Vector, Matrix, Quaternion, noise
import mbk
from mbk import G, MT, CT, AP, MM, X, Y, Z, O, T, R4, put, W, Wd, bench_pose, join, Tap

FAM = 'tools'
L, H, TH = 0.56, 0.30, 0.0016
XL = -L / 2
NSEG = 80        # 80 segment bones (40 until 21 Nov): 7 mm steps, so the rolled end is a smooth spiral
SEG = L / NSEG
FLAP = 0.110
PTOP = -0.045                 # pocket mouth (y); -0.015 until 21 Nov 17:40, lowered so every tool stands proud of its pocket
MOUTH = {'bitblock': -0.100}  # a shallower pocket for the short bit block, so the cross bit shows
R0, PITCH = 0.014, 0.0085      # spiral: inner radius and radial pitch per turn
STRAP_Y, STRAP_L, STRAP_N = -0.02, 0.30, 15
# pocket: key, centre x, width, bulge at the mouth, bulge at the bottom, how far the flap must lift over it (deg)
POCKETS = [('screwdriver', -0.228, 0.056, 0.0225, 0.0085, 25.0), ('bitblock', -0.176, 0.040, 0.019, 0.019, 5.0), ('pliers', -0.119, 0.066, 0.0125, 0.0125, 7.0),
           ('cutters', -0.052, 0.060, 0.012, 0.012, 6.0), ('strippers', 0.010, 0.056, 0.0102, 0.0110, 6.0), ('wirebrush', 0.067, 0.050, 0.0222, 0.0222, 13.0),
           ('pick', 0.112, 0.032, 0.0114, 0.0050, 6.0), ('punch', 0.148, 0.032, 0.0125, 0.008, 5.0), ('scribe', 0.184, 0.032, 0.0134, 0.0056, 7.0)]
TIP_Y = -0.135                # where a tool's working end sits in its pocket


def bounds_of_pockets():
    xs = [POCKETS[0][1] - POCKETS[0][2] / 2]
    for a, b in zip(POCKETS, POCKETS[1:]):
        xs.append(((a[1] + a[2] / 2) + (b[1] - b[2] / 2)) / 2)
    xs.append(POCKETS[-1][1] + POCKETS[-1][2] / 2)
    return xs


def wob(x, y, amp=0.0006, seed=0.0):
    return amp * noise.noise(Vector((x * 14.0 + seed, y * 14.0, seed * 0.37)))


def crease(x, y, amp=0.0011, seed=0.0):
    """Creases of a canvas that has been rolled up for years: ridges running along the roll's axis (Y), a few across."""
    n1 = noise.noise(Vector((x * 38.0 + seed, y * 4.0, seed * 0.7)))
    n2 = noise.noise(Vector((x * 6.0, y * 30.0 + seed, 1.3 + seed)))
    r = (1.0 - min(1.0, abs(n1) * 2.0)) ** 4 + 0.55 * (1.0 - min(1.0, abs(n2) * 2.4)) ** 5
    return amp * 3.4 * r


def sag(x, y, amp=0.0030):
    """Soft lift and sag: an old canvas never lies flat; it rises in broad waves between where it touches."""
    n = noise.noise(Vector((x * 7.0 + 3.1, y * 9.0, 0.4)))
    return amp * max(0.0, n) ** 1.3


def bead(x, y, y_hi, w=0.006, h=0.0008):
    """The bound edge: a raised bead of folded-over binding round the outline."""
    d = min(x - XL, -XL - x, y + H / 2, y_hi - y)
    if d >= w:
        return 0.0
    k = 1.0 - d / w
    return h * min(1.0, k * 2.2) * (1.0 - max(0.0, k - 0.85) * 4.0)


def bdef(x, y):
    """Crease and sag of the base, faded out under the pocket strip (tools lie there) and kept full above it."""
    # flat where the seated tools lie: the pocket strip and, above it, the tools' handles up to y 0.075
    xa, xb = POCKETS[0][1] - POCKETS[0][2] / 2 - 0.006, POCKETS[-1][1] + POCKETS[-1][2] / 2 + 0.006
    kx = min(1.0, max(0.0, (xa - x) / 0.015, (x - xb) / 0.015))
    ky = max(0.0, min(1.0, (y - 0.075) / 0.025))
    k = max(kx, ky)
    k = 0.10 + 0.90 * k * k * (3 - 2 * k)
    return (crease(x, y) + sag(x, y)) * k


def grid_solid(name, xs, ys, ztop, zbot, mat):
    """Thin sheet: a top and an under surface over the grid xs x ys, closed round the rim."""
    nx, ny = len(xs), len(ys)
    verts, faces = [], []
    for j, y in enumerate(ys):
        for i, x in enumerate(xs):
            verts.append((x, y, ztop(x, y, i, j)))
    for j, y in enumerate(ys):
        for i, x in enumerate(xs):
            verts.append((x, y, zbot(x, y, i, j)))
    n = nx * ny
    for j in range(ny - 1):
        for i in range(nx - 1):
            a = j * nx + i
            faces.append((a, a + 1, a + nx + 1, a + nx))
            faces.append((n + a, n + a + nx, n + a + nx + 1, n + a + 1))
    for i in range(nx - 1):
        faces.append((i + 1, i, n + i, n + i + 1))
        a = (ny - 1) * nx + i
        faces.append((a, a + 1, n + a + 1, n + a))
    for j in range(ny - 1):
        a = j * nx
        faces.append((a, a + nx, n + a + nx, n + a))
        b = j * nx + nx - 1
        faces.append((b + nx, b, n + b, n + b + nx))
    o = G.mesh_obj(name, verts, faces, mat, recalc=True)
    return o


ARCH = ((0.0, 0.0), (0.09, 0.62), (0.24, 0.96), (0.5, 1.0), (0.76, 0.96), (0.91, 0.62), (1.0, 0.0))


def arch(f):
    """A pocket's cross-section, 0 at its seams and 1 over the tool: a smooth curve through the ARCH points that never
    dips under the straight lines between them (the tools were fitted under those lines)."""
    P = ARCH
    for i in range(len(P) - 1):
        if P[i][0] <= f <= P[i + 1][0]:
            break
    (f0, a0), (f1, a1) = P[i], P[i + 1]

    def slope(j):
        lo, hi = max(0, j - 1), min(len(P) - 1, j + 1)
        return (P[hi][1] - P[lo][1]) / (P[hi][0] - P[lo][0])
    h = f1 - f0; t = (f - f0) / h
    m0, m1 = slope(i) * h, slope(i + 1) * h
    v = (2 * t ** 3 - 3 * t ** 2 + 1) * a0 + (t ** 3 - 2 * t ** 2 + t) * m0 + (-2 * t ** 3 + 3 * t ** 2) * a1 + (t ** 3 - t ** 2) * m1
    return max(v, a0 + (a1 - a0) * t, 0.0)


def build_roll(F, M):
    canvas = M['roll_canvas']
    xs = [XL + i * SEG for i in range(NSEG + 1)]
    ys = [-H / 2 + k * H / 16 for k in range(17)]
    base = grid_solid('base', xs, ys, lambda x, y, i, j: TH + max(0.0, wob(x, y) + 0.0003) + bdef(x, y) + bead(x, y, 1.0, h=0.0012),
                      lambda x, y, i, j: max(0.0, wob(x, y)) + bdef(x, y), canvas)
    # ---- pocket panel: one arch per pocket, seams between them, flat along the bottom seam, open at the mouth
    bx = bounds_of_pockets()
    pxs, prof = [], []          # x positions and (pocket index, arch factor 0..1)
    for k, (key, cx, w, hm, hb, lift) in enumerate(POCKETS):
        x0, x1 = bx[k], bx[k + 1]
        ww = x1 - x0
        for f in (0.0, 0.04, 0.09, 0.16, 0.24, 0.36, 0.5, 0.64, 0.76, 0.84, 0.91, 0.96):
            pxs.append(x0 + ww * f); prof.append((k, arch(f)))
    pxs.append(bx[-1]); prof.append((len(POCKETS) - 1, 0.0))
    pys = [-H / 2 + 0.002, -H / 2 + 0.0075, -H / 2 + 0.016, -H / 2 + 0.030, -H / 2 + 0.045, -H / 2 + 0.058, -H / 2 + 0.070, -H / 2 + 0.082,
           PTOP - 0.010, PTOP - 0.004, PTOP]
    rise = [0.0, 0.58, 0.85, 0.88, 0.90, 0.93, 0.96, 0.99, 1.0, 1.0, 1.0]

    def ptop(x, y, i, j):
        k, a = prof[i]
        hm, hb = POCKETS[k][3], POCKETS[k][4]
        f = (y - pys[2]) / (PTOP - pys[2])
        h = (hb + (hm - hb) * max(0.0, min(1.0, f))) * rise[j]
        tool = 1.0 + 0.18 * math.sin(math.pi * max(0.0, min(1.0, f))) - 0.10 * max(0.0, 1.0 - f * 3.0)
        across = 0.0011 * a * max(0.0, math.sin(y * 210.0 + k * 1.7)) ** 6
        return TH + 0.0007 + bdef(x, y) + a * h * tool + across + (0.0003 if j == len(pys) - 1 else 0.0) + crease(x, y, 0.0005, 5.0) * a + (0.0009 if j >= len(pys) - 2 else 0.0)

    def pbot(x, y, i, j):
        return max(TH + 0.0002 + bdef(x, y), ptop(x, y, i, j) - 0.0013)
    pocket = grid_solid('pocket', pxs, pys, ptop, pbot, canvas)
    # a pocket with its own mouth (MOUTH): its columns are drawn down toward the bottom seam
    for v in pocket.data.vertices:
        k = max(i for i in range(len(POCKETS)) if bx[i] <= v.co.x + 1e-7) if v.co.x >= bx[0] - 1e-7 else 0
        k = min(k, len(POCKETS) - 1)
        m = MOUTH.get(POCKETS[k][0])
        if m is not None:
            v.co.y = -H / 2 + (v.co.y + H / 2) * (m + H / 2) / (PTOP + H / 2)
    pocket.data.update()
    # ---- flap: two panels beyond the top edge (it lies open in the bind pose), hinged along the edge
    fys = [H / 2 + FLAP * k / 8 for k in range(9)]
    flap = grid_solid('flap', xs, fys, lambda x, y, i, j: TH + max(0.0, wob(x, y, 0.0005, 3.0) + 0.0002) + crease(x, y, 0.0009, 9.0) + sag(x, y, 0.0016) + bead(x, y, H / 2 + FLAP, h=0.0012),
                      lambda x, y, i, j: max(0.0, wob(x, y, 0.0005, 3.0)) + crease(x, y, 0.0009, 9.0) + sag(x, y, 0.0016), canvas)
    # ---- a patch sewn over the worn right-hand corner
    pxp = [0.198 + 0.072 * k / 6 for k in range(7)]; pyp = [-0.147 + 0.060 * k / 5 for k in range(6)]
    pat = grid_solid('patch', pxp, pyp, lambda x, y, i, j: TH + 0.0026 + sag(x, y) + crease(x, y, 0.0005, 3.0) + (0.0005 if 0 < i < 6 and 0 < j < 5 else 0.0),
                     lambda x, y, i, j: TH + 0.0014 + sag(x, y) + crease(x, y, 0.0005, 3.0), canvas)
    # ---- strap: leather, 25 x 2.4 mm, from under the left edge out to the left; a steel roller buckle at its root
    sxs = [XL + 0.024 - k * (STRAP_L + 0.024) / 32 for k in range(33)]
    sxs = sxs[::-1]

    def taper(x):
        d = x - (XL - STRAP_L)
        return 0.0125 if d > 0.02 else 0.0125 * (0.35 + 0.65 * d / 0.02)
    strap_pts = []
    sv, sf = [], []
    for i, x in enumerate(sxs):
        hw = taper(x)
        for (dy, dz) in ((-hw, 0.0), (hw, 0.0), (hw, 0.0034), (-hw, 0.0034)):
            sv.append((x, STRAP_Y + dy, dz - (0.0 if x < XL else 0.0)))
    for i in range(len(sxs) - 1):
        a, b = 4 * i, 4 * (i + 1)
        for q in range(4):
            sf.append((a + q, b + q, b + (q + 1) % 4, a + (q + 1) % 4))
    sf.append((0, 1, 2, 3)); sf.append((4 * (len(sxs) - 1) + 3, 4 * (len(sxs) - 1) + 2, 4 * (len(sxs) - 1) + 1, 4 * (len(sxs) - 1)))
    strap = G.mesh_obj('strap', sv, sf, M['roll_leather'], recalc=True)
    bk = M['roll_buckle']
    bxc = XL - 0.012
    frame = [(bxc - 0.013, STRAP_Y - 0.0195, 0.0040), (bxc + 0.013, STRAP_Y - 0.0195, 0.0040), (bxc + 0.013, STRAP_Y + 0.0195, 0.0040), (bxc - 0.013, STRAP_Y + 0.0195, 0.0040)]
    ring = G.tube_path('bk', G.chaikin(frame, 2, True), 0.0021, 8, bk, closed=True)
    roller = G.cyl('bkr', (bxc - 0.013, STRAP_Y - 0.0155, 0.0040), (bxc - 0.013, STRAP_Y + 0.0155, 0.0040), 0.0030, 10, bk)
    prong = G.cyl('bkp', (bxc + 0.013, STRAP_Y, 0.0046), (bxc - 0.0150, STRAP_Y, 0.0062), 0.0013, 6, bk)
    keeper = G.band_path('keep', [(XL + 0.018, STRAP_Y, 0.0026), (XL + 0.004, STRAP_Y, 0.0030), (bxc + 0.0115, STRAP_Y, 0.0052), (bxc + 0.0105, STRAP_Y, 0.0012),
                                  (XL + 0.004, STRAP_Y, 0.0002)], 0.016, 0.0016, lambda p, tg: (0, 0, 1), M['roll_leather'], closed=False)
    rv = AP.rivet('rvt', 5.5 * MM, 1.5 * MM, bk, segs=8, at=(XL + 0.012, STRAP_Y, TH + 0.0003))
    rv.data.transform(rv.matrix_world); rv.matrix_world = Matrix.Identity(4)
    fixed = join('fixed', [ring, roller, prong, keeper, rv])

    # ---- vertex groups (before the join, so each piece is weighted its own way)
    def seg_w(o, kind):
        vg = {}
        for v in o.data.vertices:
            u = (v.co.x - XL) / SEG - 0.5
            i0 = math.floor(u); f = u - i0
            pairs = [(min(NSEG - 1, max(0, i0)), 1.0 - f), (min(NSEG - 1, max(0, i0 + 1)), f)]
            for i, wgt in pairs:
                if wgt <= 1e-4:
                    continue
                if kind == 'flap':
                    nm = 'roll_flapb_%02d' % i if v.co.y > H / 2 + FLAP * 0.5 + 1e-5 else ('roll_flapa_%02d' % i if v.co.y > H / 2 + 1e-5 else 'roll_seg_%02d' % i)
                else:
                    nm = 'roll_seg_%02d' % i
                g = o.vertex_groups.get(nm) or o.vertex_groups.new(name=nm)
                g.add([v.index], wgt, 'ADD')
    for o in (base, pocket, pat):
        seg_w(o, 'seg')
    seg_w(flap, 'flap')
    for v in strap.data.vertices:
        d = XL - v.co.x                     # distance out along the strap
        if d <= 0:
            nm = [('roll_seg_00', 1.0)]
        else:
            u = d / (STRAP_L / STRAP_N) - 0.5
            i0 = math.floor(u); f = u - i0
            nm = [('roll_strap_%02d' % min(STRAP_N - 1, max(0, i0)), 1.0 - f), ('roll_strap_%02d' % min(STRAP_N - 1, max(0, i0 + 1)), f)]
            if i0 < 0:
                nm = [('roll_strap_00', 1.0)]
        for n_, wgt in nm:
            if wgt > 1e-4:
                g = strap.vertex_groups.get(n_) or strap.vertex_groups.new(name=n_)
                g.add([v.index], wgt, 'ADD')
    g = fixed.vertex_groups.new(name='roll_seg_00')
    g.add([v.index for v in fixed.data.vertices], 1.0, 'ADD')
    roll = join('roll', [base, pocket, flap, pat, strap, fixed])
    G.shade(roll, 50)

    # ---- stitching and hems in the canvas material
    m = canvas
    t = Tap(m)
    x, y, z = t.xyz()
    dash = t.b.ramp(t.b.math('SINE', t.b.math('MULTIPLY', y, 2 * math.pi / 0.0042)), -0.25, 0.1)
    dashx = t.b.ramp(t.b.math('SINE', t.b.math('MULTIPLY', x, 2 * math.pi / 0.0042)), -0.25, 0.1)
    inpocket = t.band(1, -H / 2 + 0.003, PTOP - 0.001, 0.0006)
    seams = None
    for xb in bx:
        bnd = t.band(0, xb - 0.00045, xb + 0.00045, 0.00025)
        seams = bnd if seams is None else t.b.math('MAXIMUM', seams, bnd)
    seam = t.b.math('MULTIPLY', t.b.math('MULTIPLY', seams, inpocket), dash)
    hems = None
    for ax_, lo_, hi_, d_ in ((1, -H / 2 + 0.0045, -H / 2 + 0.0054, dashx), (1, H / 2 - 0.0054, H / 2 - 0.0045, dashx), (1, PTOP - 0.0052, PTOP - 0.0043, dashx),
                              (1, H / 2 + FLAP - 0.0054, H / 2 + FLAP - 0.0045, dashx), (0, XL + 0.0045, XL + 0.0054, dash), (0, -XL - 0.0054, -XL - 0.0045, dash)):
        bnd = t.b.math('MULTIPLY', t.band(ax_, lo_, hi_, 0.00025), d_)
        hems = bnd if hems is None else t.b.math('MAXIMUM', hems, bnd)
    st = t.b.math('MAXIMUM', seam, hems, clamp=True)
    t.layer(st, col=(0.70, 0.63, 0.47), rough=0.85, height=1.6)
    # the patch is a newer, paler cloth; the roll is darkest where the bundle's outside takes the dirt (the far left)
    pm = t.b.math('MULTIPLY', t.band(0, 0.1985, 0.2695, 0.0004), t.b.math('MULTIPLY', t.band(1, -0.1465, -0.0875, 0.0004), t.b.ramp(z, TH + 0.0010, TH + 0.0014)))
    t.layer(t.b.math('MULTIPLY', pm, 0.95), col=(0.46, 0.44, 0.34), rough=0.82)
    pe = t.b.math('SUBTRACT', pm, t.b.math('MULTIPLY', t.band(0, 0.2025, 0.2655, 0.0003), t.band(1, -0.1425, -0.0915, 0.0003)))
    zz = t.b.ramp(t.b.math('SINE', t.b.math('MULTIPLY', t.b.math('ADD', x, y), 2 * math.pi / 0.0030)), -0.2, 0.3)
    t.layer(t.b.math('MULTIPLY', t.b.math('MAXIMUM', pe, 0.0), zz), col=(0.10, 0.09, 0.07), rough=0.85, height=1.5)
    worn = t.b.math('MULTIPLY', t.b.math('SUBTRACT', 1.0, t.b.ramp(x, XL + 0.02, XL + 0.14)), t.b.ramp(t.noise(30, 4), 0.3, 0.7))
    t.layer(t.b.math('MULTIPLY', worn, 0.55), col=(0.17, 0.13, 0.09), rough=0.6)
    grip = t.b.math('MAXIMUM', t.b.math('MULTIPLY', t.band(1, PTOP - 0.022, PTOP + 0.012, 0.006), 0.8),
                    t.b.ramp(x, -XL - 0.06, -XL - 0.005))
    gm = t.b.math('MULTIPLY', grip, t.b.ramp(t.noise(45, 5, 0.65), 0.35, 0.7))
    t.layer(t.b.math('MULTIPLY', gm, 0.75), col=(0.10, 0.085, 0.06), rough=0.42)
    # the binding round the outline: a darker, more worn cloth tape
    inner = t.b.math('MULTIPLY', t.band(0, XL + 0.0055, -XL - 0.0055, 0.0004), t.band(1, -H / 2 + 0.0055, H / 2 + FLAP - 0.0055, 0.0004))
    t.layer(t.b.math('MULTIPLY', t.b.math('SUBTRACT', 1.0, inner), 0.92), col=(0.13, 0.115, 0.08), rough=0.62)
    bw = t.b.math('MULTIPLY', t.b.math('SUBTRACT', 1.0, inner), t.b.ramp(t.noise(60, 4, 0.6), 0.55, 0.75))
    t.layer(t.b.math('MULTIPLY', bw, 0.7), col=(0.30, 0.27, 0.19), rough=0.8)       # binding rubbed through to the weave
    # creases polished and darkened by handling
    cr = t.b.ramp(t.noise(38, 3, 0.6, stretch=(1.0, 0.11, 1.0)), 0.47, 0.53)
    t.layer(t.b.math('MULTIPLY', t.b.math('SUBTRACT', 1.0, t.b.math('ABSOLUTE', t.b.math('SUBTRACT', t.b.math('MULTIPLY', cr, 2.0), 1.0))), 0.10), col=(0.24, 0.22, 0.15), rough=0.55)
    # the strap's punched holes
    lt = Tap(M['roll_leather'])
    lx, ly, lz = lt.xyz()
    holes = None
    for k in range(5):
        hx = XL - 0.200 - 0.019 * k
        d = lt.b.math('SQRT', lt.b.math('ADD', lt.b.math('MULTIPLY', lt.b.math('SUBTRACT', lx, hx), lt.b.math('SUBTRACT', lx, hx)),
                                       lt.b.math('MULTIPLY', lt.b.math('SUBTRACT', ly, STRAP_Y), lt.b.math('SUBTRACT', ly, STRAP_Y))))
        hm = lt.b.math('SUBTRACT', 1.0, lt.b.ramp(d, 0.0016, 0.0020))
        holes = hm if holes is None else lt.b.math('MAXIMUM', holes, hm)
    lt.height(holes, -6.0)
    lt.layer(holes, col=(0.02, 0.015, 0.012), rough=0.9)

    # ---- armature
    bones = [('roll_root', (0, 0, 0), (0, 0.02, 0), None, Z)]
    for i in range(NSEG):
        xc = XL + (i + 0.5) * SEG
        bones.append(('roll_seg_%02d' % i, (xc, 0, 0), (xc, 0.02, 0), 'roll_root', Z))
        bones.append(('roll_flapa_%02d' % i, (xc, H / 2, TH), (xc + 0.012, H / 2, TH), 'roll_seg_%02d' % i, Z))
        bones.append(('roll_flapb_%02d' % i, (xc, H / 2 + FLAP * 0.5, TH), (xc + 0.012, H / 2 + FLAP * 0.5, TH), 'roll_flapa_%02d' % i, Z))
    ds = STRAP_L / STRAP_N
    for k in range(STRAP_N):
        bones.append(('roll_strap_%02d' % k, (XL - k * ds, STRAP_Y, 0), (XL - (k + 1) * ds, STRAP_Y, 0), 'roll_strap_%02d' % (k - 1) if k else 'roll_root', Z))
    arm = mbk.new_armature('tools_roll_rig', bones)
    Mw = bench_pose('tools_roll')
    roll.parent = arm                       # the skin rides the armature object: its own matrix stays the identity
    put(arm, Mw)
    CT.part(roll, FAM, 'roll', 'Field Toolkit roll', kind='part', material='canvas', mass='medium', item='field_toolkit', loose=True, steps=['s0.roll', 's7.leave'],
            note='skinned mesh on tools_roll_rig; bind pose is unrolled with the flap open')
    mod = roll.modifiers.new('Armature', 'ARMATURE'); mod.object = arm

    # ---- poses
    lifts = [4.0] * NSEG
    for (key, cx, w, hm, hb, lift) in POCKETS:
        for i in range(NSEG):
            xc = XL + (i + 0.5) * SEG
            if abs(xc - cx) <= w / 2 + SEG * 0.5:
                lifts[i] = max(lifts[i], lift)
    sm = lifts[:]
    for i in range(NSEG):
        sm[i] = max(lifts[i], 0.5 * (lifts[max(0, i - 1)] + lifts[min(NSEG - 1, i + 1)]))
    lifts = sm

    def rad(q):
        return math.sqrt(R0 * R0 + PITCH * max(0.0, q) / math.pi)

    def seg_pose(i, tt):
        """(location, angle about Y) of segment bone i at unroll value tt, in the armature's frame relative to rest."""
        u = L * min(1.0, tt / 0.8)
        s = (i + 0.5) * SEG
        if s <= u:
            return Vector((0, 0, 0)), 0.0
        q = L - s
        Rr = rad(L - u)
        th_out = 2 * math.pi / PITCH * (Rr - R0)
        th = 2 * math.pi / PITCH * (rad(q) - R0)
        phi = -math.pi / 2 + (th_out - th)
        c = Vector((XL + u, 0, Rr))
        p = c + Vector((math.cos(phi), 0, math.sin(phi))) * rad(q)
        psi = phi + math.pi / 2
        rest = Vector((XL + s, 0, 0))
        return p - rest, -psi

    def flap_pose(i, tt):
        k = 1.0 if tt <= 0.8 else max(0.0, 1.0 - (tt - 0.8) / 0.2)
        k = k * k * (3 - 2 * k)
        a = math.radians(lifts[i])
        h1 = FLAP * 0.5 * math.sin(a)
        tgt = 0.013
        b = a - math.asin(max(-0.9, min(0.9, (tgt - h1) / (FLAP * 0.5))))
        return (math.pi - a) * k, b * k

    def strap_pose(k, tt):
        kap = (1.0 / (rad(L) + 0.0014)) * max(0.0, 1.0 - tt / 0.6) ** 1.2
        a = kap * ds
        yaw = 0.0
        if k == 0:
            w = max(0.0, min(1.0, (tt - 0.6) / 0.4)); w = w * w * (3 - 2 * w)
            yaw = -math.pi / 2 * w
        return a, yaw

    def set_pose(unroll=None, strap=None):
        pb = arm.pose.bones
        if unroll is not None:
            for i in range(NSEG):
                loc, ang = seg_pose(i, unroll)
                b = pb['roll_seg_%02d' % i]; b.rotation_mode = 'QUATERNION'
                b.location = loc; b.rotation_quaternion = Quaternion((0, 1, 0), ang)
                fa, fb = flap_pose(i, unroll)
                for nm, an in (('roll_flapa_%02d' % i, fa), ('roll_flapb_%02d' % i, fb)):
                    b = pb[nm]; b.rotation_mode = 'QUATERNION'; b.rotation_quaternion = Quaternion((0, 1, 0), an)
        if strap is not None:
            for k in range(STRAP_N):
                a, yaw = strap_pose(k, strap)
                b = pb['roll_strap_%02d' % k]; b.rotation_mode = 'QUATERNION'
                b.rotation_quaternion = Quaternion((0, 0, 1), yaw) @ Quaternion((1, 0, 0), a)
        bpy.context.view_layer.update()

    def bake():
        seg_names = ['roll_seg_%02d' % i for i in range(NSEG)] + ['roll_flapa_%02d' % i for i in range(NSEG)] + ['roll_flapb_%02d' % i for i in range(NSEG)]
        strap_names = ['roll_strap_%02d' % k for k in range(STRAP_N)]
        mbk.bake_pose_action(arm, 'roll_unroll_param', seg_names, lambda v: set_pose(unroll=v), keys=25, loc=['roll_seg_%02d' % i for i in range(NSEG)])
        mbk.bake_pose_action(arm, 'roll_strap_param', strap_names, lambda v: set_pose(strap=v), keys=25)
    keep = {'roll_unroll_param': ['roll_seg_%02d' % i for i in range(NSEG)] + ['roll_flapa_%02d' % i for i in range(NSEG)] + ['roll_flapb_%02d' % i for i in range(NSEG)],
            'roll_strap_param': ['roll_strap_%02d' % k for k in range(STRAP_N)]}
    F.custom_arms.append((arm, bake, keep))
    for pid, act, note in (('roll_unroll', 'roll_unroll_param', '0 = rolled bundle at the left end of its footprint (as found), 0.8 = flat, 1 = flap folded open. The bind pose of the skin is 1: sample the clip at 0 for the as-found bundle.'),
                           ('roll_strap', 'roll_strap_param', '0 = buckled round the bundle (as found), 0.6 = laid out straight to the left (this is the bind pose of the skin), 1 = swung to lie beside the roll, pointing away from the player. Undo the strap before unrolling.')):
        F.extra_params.append({'id': 'tools.' + pid, 'node': arm.name, 'bone': None, 'bones': keep[act][0].rsplit('_', 1)[0] + '_*', 'action': act, 'type': 'skinned',
                               'min': 0.0, 'max': 1.0, 'unit': 'ratio', 'continuous': False, 'parent_bone': 'roll_root', 'requires': {}, 'parts': ['tools.roll'],
                               'rest': 0.0, 'bind_pose_value': 1.0 if pid == 'roll_unroll' else 0.6, 'note': note})
    arm['anymachine'] = json.dumps({'joints': [{'param': 'roll_unroll', 'type': 'skinned', 'min': 0, 'max': 1, 'unit': 'ratio', 'continuous': False},
                                               {'param': 'roll_strap', 'type': 'skinned', 'min': 0, 'max': 1, 'unit': 'ratio', 'continuous': False}]})
    mbk.grab(roll, (XL + 0.02, 0, rad(L)))
    F.set_of[roll.name] = 'a'
    F.uv_weights[roll.name] = 0.8
    return dict(root=roll, arm=arm, set_pose=set_pose, rad=rad)


def pocket_of(key):
    return next(p for p in POCKETS if p[0] == key)


def seat_matrix(key, y_tip, z=None):
    """Roll-frame pose of a tool in its pocket: working end toward the player (-Y), tip at TIP_Y."""
    p = pocket_of(key)
    return T((p[1], TIP_Y + y_tip, TH + 0.0012 if z is None else z)) @ R4('Z', 180)


def add_seat(F, roll_d, key, Mseat):
    """'tools_roll__mark_seat_<key>' on the segment bone under the pocket, so a tool parented to it rolls up with the roll."""
    roll, arm = roll_d['root'], roll_d['arm']
    e = mbk.seat(roll, key, M_local=Mseat, pose=True, accepts=['tools.' + key])
    i = min(NSEG - 1, max(0, int((pocket_of(key)[1] - XL) / SEG)))

    def fix(e=e, i=i):
        bpy.context.view_layer.update()
        mw = e.matrix_world.copy()
        e.parent = arm; e.parent_type = 'BONE'; e.parent_bone = 'roll_seg_%02d' % i
        bpy.context.view_layer.update()
        e.matrix_world = mw
    F.post_hierarchy.append(fix)
    return e
