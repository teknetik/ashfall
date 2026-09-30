# Barrel attachments (metric pistol frame). Bore axis from pistol_frame ray casts: y=0.00075, z=0.05885; the slide
# nose face is at x=-0.1205 and the pistol's muzzle ring (r~12.9 mm) protrudes to x=-0.1301.
import math
from mathutils import Vector, Matrix
import pm_geo as G

MM = 0.001
AX_O = Vector((-0.1205, 0.00075, 0.05885))
AX = Vector((-1, 0, 0))
UP = Vector((0, 0, 1))


def P(s, r=0.0, th=0.0):
    """point at s mm forward of the nose face, radius r mm, angle th (deg, 0=up, 90=right)"""
    t = math.radians(th)
    return AX_O + AX * s * MM + (UP * math.cos(t) + Vector((0, 1, 0)) * math.sin(t)) * r * MM


def radial_frame(th):
    t = math.radians(th)
    rad = UP * math.cos(t) + Vector((0, 1, 0)) * math.sin(t)
    tan = AX.cross(rad)
    return rad, tan


def mm(loop):
    return [(s * MM, r * MM) for s, r in loop]


def slot_cutter(s, th, length, width, r0=10.0, depth=8.0, name='cut'):
    rad, tan = radial_frame(th)
    return G.prism(name, G.stadium(length * MM, width * MM, 6), depth * MM, P(s), AX, tan, rad, w0=r0 * MM)


def hex_head(name, origin, axis, ref, af, h, mat, slot=True, washer=0.0):
    """Hex bolt head: across-flats af mm, height h mm, along axis from origin."""
    rc = af / 2 / math.cos(math.radians(30))
    loop = [(0, 0), (0, rc * 0.92), (0.25, rc), (h - 0.35, rc), (h, rc * 0.85), (h, 0)]
    o = G.lathe(name, [(mm(loop), False)], 6, origin, axis, ref, mat, phase=math.radians(30))
    parts = [o]
    if washer:
        parts.append(G.lathe(name + '_w', [(mm([(-washer, 0), (-washer, rc * 1.25), (0, rc * 1.25), (0, 0)]), False)], 20, origin, axis, ref, mat))
    return parts


def build_bored_alloy(M):
    """Mk I: bored alloy sleeve (collar, slotted cooling section, ported crown) hose-clamped over the muzzle ring."""
    outer = [(0.5, 13.5), (0.5, 14.5), (1.2, 15.8), (13.6, 15.8), (14.2, 15.5), (15.8, 14.2), (40.0, 14.2), (40.5, 13.2),
             (41.9, 13.2), (42.4, 14.8), (54.0, 14.8), (55.0, 13.8), (55.0, 7.2), (54.3, 6.0), (53.8, 4.8), (52.0, 4.8),
             (52.0, 11.0), (44.0, 11.0), (44.0, 4.8), (10.0, 4.8), (10.0, 13.5)]
    cav = [(11.5, 7.6), (23.9, 7.6), (24.2, 10.0), (25.3, 10.0), (25.6, 7.6), (31.4, 7.6), (31.7, 10.0), (32.8, 10.0),
           (33.1, 7.6), (39.0, 7.6), (39.0, 12.4), (11.5, 12.4)]
    sleeve = G.lathe('bored_sleeve', [(mm(outer), True), (mm(cav), True)], 28, AX_O, AX, UP, M['alloy_heat'])
    cuts = []
    for th in (-58, 0, 58):
        for s in (20.6, 28.3, 36.0):
            cuts.append(slot_cutter(s, th, 6.4, 2.8, 11.0, 6.0))
    for th in (90, 270):  # crown side ports into the brake chamber
        cuts.append(slot_cutter(48.0, th, 6.6, 4.2, 9.0, 9.0))
    for th in (45, 135, 225, 315):  # collar relief slits
        rad, tan = radial_frame(th)
        cuts.append(G.prism('slit', [(-0.2 * MM, -0.55 * MM), (7.5 * MM, -0.55 * MM), (7.5 * MM, 0.55 * MM), (-0.2 * MM, 0.55 * MM)],
                            5 * MM, P(0.0), AX, tan, rad, w0=12.5 * MM))
    G.boolean(sleeve, cuts)
    parts = [sleeve]
    parts.append(G.lathe('paint_band', [(mm([(42.3, 14.78), (42.3, 14.92), (44.6, 14.92), (44.6, 14.78)]), True)], 28, AX_O, AX, UP, M['paint_orange']))
    # worm-drive hose clamp over the collar
    clamp_th = 62.0
    parts.append(G.lathe('clamp_band', [(mm([(2.6, 15.82), (2.6, 16.38), (9.8, 16.38), (9.8, 15.82)]), True)], 40, AX_O, AX, UP, M['stainless']))
    parts.append(G.lathe('clamp_tail', [(mm([(2.8, 16.4), (2.8, 16.92), (9.6, 16.92), (9.6, 16.4)]), True)], 6, AX_O, AX, UP,
                         M['stainless'], arc=(math.radians(clamp_th + 6), math.radians(clamp_th + 30))))
    rad, tan = radial_frame(clamp_th)
    house = G.prism('clamp_house', G.rounded_rect(8.6 * MM, 7.2 * MM, 1.3 * MM, 2), 4.2 * MM, P(6.2, 16.38 + 2.05, clamp_th), AX, tan, rad)
    G.bevel(house, 0.3 * MM, 1, 30)
    house.data.materials.clear(); house.data.materials.append(M['stainless_plain'])
    parts.append(house)
    sc_o = P(6.2, 16.38 + 2.2, clamp_th) - tan * 3.6 * MM
    hh = hex_head('clamp_screw', sc_o, -tan, rad, 5.6, 2.8, M['stainless_plain'])
    G.boolean(hh[0], [G.box('slotcut', sc_o - tan * 2.8 * MM, (0.7 * MM, 7 * MM, 1.6 * MM), Matrix((rad, AX, -tan)).transposed())])
    parts += hh
    thread = [(0, 0), (0, 1.8)]
    for k in range(3):
        thread += [(0.45 + k * 0.9, 2.15), (0.9 + k * 0.9, 1.8)]
    thread += [(3.0, 1.5), (3.0, 0)]
    parts.append(G.lathe('clamp_thread', [(mm(thread), False)], 10, sc_o + tan * 7.2 * MM, tan, rad, M['stainless_plain']))
    obj = G.join('barrel_bored_alloy', parts)
    G.sharp_by_angle(obj, 35)
    muzzle = P(55.0)
    return obj, muzzle


def crystal_mesh(name, s0, s1, rmax, mat, seed=3, sides=6):
    import random
    rnd = random.Random(seed)
    verts, faces = [], []
    rings = [(s0, 0.0), (s0 + (s1 - s0) * 0.18, rmax * 0.92), (s0 + (s1 - s0) * 0.3, rmax), (s0 + (s1 - s0) * 0.62, rmax * 0.86),
             (s0 + (s1 - s0) * 0.78, rmax * 0.55), (s1, 0.0)]
    idx = []
    for i, (s, r) in enumerate(rings):
        if r == 0:
            verts.append(P(s + rnd.uniform(-0.3, 0.3), rnd.uniform(0, 0.4), rnd.uniform(0, 360)))
            idx.append([len(verts) - 1] * sides)
            continue
        row = []
        for k in range(sides):
            th = 360.0 * k / sides + i * 9 + rnd.uniform(-8, 8)
            verts.append(P(s + rnd.uniform(-0.6, 0.6), r * rnd.uniform(0.86, 1.08), th))
            row.append(len(verts) - 1)
        idx.append(row)
    for i in range(len(rings) - 1):
        a, b = idx[i], idx[i + 1]
        for k in range(sides):
            k2 = (k + 1) % sides
            q = [a[k], a[k2], b[k2], b[k]]
            u = []
            for v in q:
                if v not in u:
                    u.append(v)
            if len(u) == 4:
                faces.append((u[0], u[1], u[2])); faces.append((u[0], u[2], u[3]))
            elif len(u) == 3:
                faces.append(tuple(u))
    o = G.mesh_obj(name, verts, faces, mat, smooth=False)
    G.clean(o)
    for p in o.data.polygons:
        p.use_smooth = False
    return o


def build_lattice_focused(M):
    """Mk II: machined collar, octagonal focusing shroud with coil windows, prong cage with a lattice shard
    seated behind a salvaged optic."""
    parts = []
    collar = G.lathe('lf_collar', [(mm([(0.5, 13.5), (0.5, 15.4), (1.3, 16.4), (6.6, 16.4), (7.1, 15.8), (8.7, 15.8), (9.2, 16.4),
                                       (14.4, 16.4), (15.0, 15.8), (15.0, 5.5), (10.0, 5.5), (10.0, 13.5)]), True)],
                     28, AX_O, AX, UP, M['steel_dark'])
    for th in (60, 180, 300):
        rad, tan = radial_frame(th)
        c = P(11.8, 15.9, th)
        head = G.lathe('lf_screw', [(mm([(0, 0), (0, 2.35), (1.7, 2.35), (2.1, 2.0), (2.1, 0)]), False)], 16, c, rad, AX, M['steel'])
        sock = G.prism('sock', G.circle(1.25 * MM, 6), 1.6 * MM, c + rad * 2.1 * MM, AX, tan, -rad, w0=-0.1 * MM)
        G.boolean(head, [sock])
        parts.append(head)
    parts.append(collar)
    # octagonal shroud (flat on top)
    shroud = G.lathe('lf_shroud', [(mm([(15.0, 15.0), (15.8, 16.1), (79.2, 16.1), (80.0, 15.3), (80.0, 11.0), (15.0, 11.0)]), True)],
                     8, AX_O, AX, UP, M['anodized'], phase=math.radians(22.5))
    cuts = [slot_cutter(47.0, 90, 44.0, 6.6, 9.0, 9.0), slot_cutter(47.0, 270, 44.0, 6.6, 9.0, 9.0)]
    for s in (29.0, 37.0, 45.0, 53.0, 61.0):
        rad, tan = radial_frame(0)
        cuts.append(G.prism('port', G.circle(1.5 * MM, 12), 8 * MM, P(s), AX, tan, rad, w0=10 * MM))
    G.bevel(shroud, 0.5 * MM, 2, 30, weighted=False)
    G.boolean(shroud, cuts)
    parts.append(shroud)
    # core: steel spine + copper focusing coils + glowing lattice filament
    parts.append(G.lathe('lf_spine', [(mm([(15.0, 0), (15.0, 3.6), (80.0, 3.6), (80.0, 0)]), False)], 12, AX_O, AX, UP, M['steel_dark']))
    for s in (28.0, 36.0, 44.0, 52.0, 60.0, 68.0):
        coil = G.lathe('lf_coil', [(mm([(s - 1.5, 4.8), (s - 1.5, 8.4), (s + 1.5, 8.4), (s + 1.5, 4.8)]), True)],
                       16, AX_O, AX, UP, M['copper'])
        parts.append(coil)
    fil = crystal_mesh('lf_filament', 19.0, 76.0, 5.6, M['core_fluid'], seed=11, sides=6)
    parts.append(fil)
    # front ring
    ring = G.lathe('lf_front', [(mm([(80.0, 9.0), (80.0, 15.6), (80.6, 16.3), (83.4, 16.3), (84.0, 15.6), (84.0, 9.0)]), True)],
                   28, AX_O, AX, UP, M['anodized'])
    parts.append(ring)
    # prong cage (3 claws)
    for th in (60, 180, 300):
        rad, tan = radial_frame(th)
        pts = [P(s, r, th) for s, r in ((82.0, 13.6), (86.0, 13.8), (90.0, 13.0), (93.5, 11.6), (96.4, 10.3), (98.6, 9.6))]
        claw = G.band_path('lf_claw', pts, 3.4 * MM, 2.2 * MM, lambda p, t, th=th: radial_frame(th)[0], M['steel'], closed=False)
        G.bevel(claw, 0.35 * MM, 1, 30)
        parts.append(claw)
    parts.append(crystal_mesh('lf_crystal', 83.0, 99.0, 6.4, M['crystal'], seed=5))
    # salvaged optic: knurled brass bezel with a glowing lens
    bez = G.lathe('lf_bezel', [(mm([(98.6, 7.2), (98.6, 10.6), (99.1, 11.1), (102.6, 11.1), (103.1, 10.6), (103.1, 8.4), (102.4, 7.6), (100.6, 7.2)]), True)],
                  32, AX_O, AX, UP, M['brass_knurl'])
    parts.append(bez)
    lens = G.lathe('lf_lens', [(mm([(99.6, 0), (99.6, 7.6), (101.2, 7.6), (102.1, 5.0), (102.5, 0)]), False)], 24, AX_O, AX, UP, M['lens_glow'])
    parts.append(lens)
    obj = G.join('barrel_lattice_focused', parts)
    G.sharp_by_angle(obj, 35)
    muzzle = P(102.5)
    return obj, muzzle
