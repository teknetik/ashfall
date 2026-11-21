# servo/gimbal.py: the gimbal damper unit (cradle, damping coil, gimbal ring, race, rotor, retaining ring, grit),
# to grip/INTERFACE.md section 1.
#
# Everything is built in the unit's datum frame D: origin at the centre of the flange's OUTER face, +Z out of the
# pocket, pitch trunnions on the X axis, roll pivots on the Y axis. The cradle is a deep cup: flange d 30 x 2 with its
# outer face at z = 0, press-fit body d 26 down to z = -20 (the shoulder), a key lug at -Y, two lead notches at +/-50
# degrees from +Y. Ring, race, rotor, retaining ring and coil stay inside r 11.0 and z -19.0 .. -0.3 at every value of
# every parameter (measured by check.py). Nothing stands above the flange face: the grip's left plate closes over it.
#
# build(M, MD, p) returns the objects placed with the 4x4 frame MD (D in world) and the points the caller needs in
# world space. Dimensions (millimetres) come from DIM, overridden by p.
import math
import bpy
from mathutils import Vector, Matrix
import sv
from sv import G, MM, X, Y, Z
import am_parts as AP

DIM = {
    'flange_r': 15.0, 'flange_t': 2.0, 'body_r': 13.0, 'depth': 20.0,
    'cup_r': 11.4, 'floor': 1.0,
    'key_w': 4.0, 'key_r': 14.5,
    'notch_deg': (40.0, 140.0), 'notch_w': 3.0, 'notch_r_in': 11.0, 'notch_depth': 2.7,     # angles from +X toward +Y
    'sense_deg': 90.0, 'sense_w': 1.7, 'sense_depth': 1.9,
    'screw_deg': (0.0, 180.0), 'screw_at': 15.6, 'scallop_r': 1.45,
    'pivot_z': -4.9,
    'ring_in': 8.9, 'ring_out': 10.5, 'ring_h': 3.0,
    'race_in': 6.6, 'race_out': 8.3, 'race_h': 4.0, 'lip_r': 5.9, 'lip_t': 0.7,
    'rotor_r': 6.3, 'rotor_t': 2.4, 'bob_r': 3.8, 'bob_z0': -17.4, 'bob_z1': -12.6, 'stem_r': 1.3, 'spindle_r': 1.1, 'spindle_top': -0.6,
    'coil_in': 7.8, 'coil_out': 10.75, 'coil_z1': -14.2,
    'swing_deg': 12.0,
    'env_r': 11.0, 'env_z': (-19.0, -0.3),
}
O = Vector((0, 0, 0))


def pol(r, deg, z=0.0):
    a = math.radians(deg)
    return Vector((r * MM * math.cos(a), r * MM * math.sin(a), z * MM))


def radial(deg):
    a = math.radians(deg)
    return Vector((math.cos(a), math.sin(a), 0)), Vector((-math.sin(a), math.cos(a), 0))


def slot(deg, r0, r1, width, z0, z1):
    rad, tan = radial(deg)
    poly = [(r0 * MM, -width / 2 * MM), (r1 * MM, -width / 2 * MM), (r1 * MM, width / 2 * MM), (r0 * MM, width / 2 * MM)]
    return G.prism('_slot', poly, (z1 - z0) * MM, Vector((0, 0, z0 * MM)), rad, tan, Z, w0=0.0)


def build(M, MD, p=None):
    d = dict(DIM); d.update(p or {})
    out = {'dim': d}
    D, FT, BR, FR, CR = d['depth'], d['flange_t'], d['body_r'], d['flange_r'], d['cup_r']
    PZ = d['pivot_z']
    Pv = Vector((0, 0, PZ * MM))

    # ---------------- cradle: a turned cup, flange at the mouth, key lug, lead notches, screw scallops, pivot bushes
    prof = [(-D, 0.0), (-D, BR - 0.6), (-D + 0.6, BR), (-FT, BR), (-FT, FR - 0.25), (-FT + 0.25, FR), (-0.25, FR), (0.0, FR - 0.25),
            (0.0, CR + 0.3), (-0.3, CR), (-D + d['floor'], CR), (-D + d['floor'], 0.0)]
    cup = G.lathe('cradle_cup', [([(a * MM, b * MM) for a, b in prof], True)], 56, O, Z, X, M['gim_alloy'])
    key = sv.box('cradle_key', (-d['key_w'] / 2, -d['key_r'], -D + 0.5), (d['key_w'] / 2, -BR + 0.6, -FT), M['gim_alloy'])
    keyfoot = G.prism('cradle_keyfoot', [(-d['key_w'] / 2 * MM, 0), (d['key_w'] / 2 * MM, 0), (d['key_w'] / 2 * MM, 0.5 * MM), (-d['key_w'] / 2 * MM, 0.5 * MM)],
                      (d['key_r'] - BR + 0.6 - 0.5) * MM, Vector((0, (-BR + 0.6) * MM, -D * MM)), X, Z, -Y, M['gim_alloy'], w0=0.0)
    G.boolean(cup, [key, keyfoot], op='UNION')
    cut = []
    for deg in (20.0, 160.0, 200.0, 340.0):         # slots of the grub screws
        gp = pol((FR + CR) / 2 + 0.2, deg)
        cut.append(G.cyl('_gs', gp - Z * (1.45 * MM), gp + Z * (0.5 * MM), 1.0 * MM, 10))
    for deg in d['notch_deg']:
        cut.append(slot(deg, d['notch_r_in'], FR + 2, d['notch_w'], -d['notch_depth'], 1.0))
    cut.append(slot(d['sense_deg'], CR - 0.2, FR + 2, d['sense_w'], -d['sense_depth'], 1.0))
    for deg in d['screw_deg']:
        c = pol(d['screw_at'], deg)
        cut.append(G.cyl('_scallop', c - Z * (FT + 1) * MM, c + Z * (1 * MM), d['scallop_r'] * MM, 14))
    G.boolean(cup, cut)
    for k, m in enumerate(cup.data.materials):
        if m is None:
            cup.data.materials[k] = M['gim_alloy']
    parts = [cup]
    for sgn in (1, -1):          # the two trunnions: steel studs in brass bushes in the cup wall, pointing in
        parts.append(sv.annulus('cradle_bush', Vector((sgn * (CR - 0.36) * MM, 0, PZ * MM)), X * sgn, 0.6, 1.35, 0.0, 0.5, 12, M['gim_brass']))
        parts.append(G.pin('cradle_trunnion', Vector((sgn * (CR + 0.2) * MM, 0, PZ * MM)), Vector((sgn * (d['ring_out'] - 0.75) * MM, 0, PZ * MM)), 0.6 * MM, 10, M['gim_steel']))
    # the pickup: a small black plug at the inner end of the sense notch
    rad, tan = radial(d['sense_deg'])
    parts.append(G.cyl('cradle_pickup', rad * ((CR + 0.05) * MM) + Z * (-1.0 * MM), rad * ((CR + 1.6) * MM) + Z * (-1.0 * MM), 0.78 * MM, 10, M['polymer'], chamfer=0.12 * MM))
    tail_tops = []
    for deg in d['notch_deg']:       # the coil's two tails, fixed up the cup wall to the lead notches
        rad, tan = radial(deg)
        rr = CR - 0.26
        pts = [rad * ((d['coil_out'] - 0.3) * MM) + Z * (d['coil_z1'] * MM), rad * ((d['coil_out'] - 0.1) * MM) + Z * ((d['coil_z1'] + 0.9) * MM),
               rad * (rr * MM) + Z * ((d['coil_z1'] + 2.2) * MM), rad * (rr * MM) + Z * (-3.2 * MM), rad * ((CR + 0.1) * MM) + Z * (-2.1 * MM)]
        parts.append(sv.tube('coil_tail', pts, 0.45 * MM, M['copper_enamel'], segs=5, smooth=1))
        tail_tops.append(pts[-1])
    for deg in (20.0, 160.0, 200.0, 340.0):          # four small slotted grub screws sunk in the flange face
        gp = pol((FR + CR) / 2 + 0.2, deg)
        grub = G.cyl('cradle_grub', gp - Z * (1.4 * MM), gp - Z * (0.15 * MM), 0.9 * MM, 10, M['steel_blued'], chamfer=0.1 * MM)
        rad, tan = radial(deg + 35.0)
        G.boolean(grub, [G.prism('_gsl', [(-1.2 * MM, -0.17 * MM), (1.2 * MM, -0.17 * MM), (1.2 * MM, 0.17 * MM), (-1.2 * MM, 0.17 * MM)], 1.0 * MM,
                                 gp - Z * (0.55 * MM), rad, tan, Z, w0=0.0)])
        for k, m in enumerate(grub.data.materials):
            if m is None:
                grub.data.materials[k] = M['steel_blued']
        parts.append(grub)
    cradle = G.join('gimbal_cradle', parts)
    G.shade(cradle, 38)
    out['cradle'] = cradle

    # ---------------- damping coil on the cup floor, its two tails up the wall to the lead notches
    z0 = -D + d['floor'] + 0.18
    coil = sv.ridged_ring('gimbal_coil', O, Z, d['coil_in'], d['coil_out'], z0, d['coil_z1'], 0.85, 0.16, 32, M['copper_enamel'])
    out['coil'] = coil

    # ---------------- gimbal ring, turning on the cradle's two trunnion studs (pitch about X)
    ring = sv.annulus('gimbal_ring', Pv, Z, d['ring_in'], d['ring_out'], -d['ring_h'] / 2, d['ring_h'] / 2, 48, M['gim_steel'], chamfer=0.3)
    G.boolean(ring, [G.cyl('_rh', Pv + X * (sgn * (d['ring_out'] - 0.9) * MM), Pv + X * (sgn * (d['ring_out'] + 0.5) * MM), 0.7 * MM, 10) for sgn in (1, -1)])
    for k, m in enumerate(ring.data.materials):
        if m is None:
            ring.data.materials[k] = M['gim_steel']
    rp = [ring]
    for sgn in (1, -1):
        rp.append(sv.annulus('ring_collar', Pv + X * (sgn * (d['ring_out'] - 0.1) * MM), X * sgn, 0.7, 1.05, 0.0, 0.45, 10, M['gim_steel']))
        rp.append(G.cyl('ring_boss', Pv + Y * (sgn * (d['ring_out'] - 0.1) * MM), Pv + Y * (sgn * (d['ring_out'] + 0.3) * MM), 0.8 * MM, 10, M['gim_steel'], chamfer=0.1 * MM))
    ring = G.join('gimbal_ring', rp)
    G.shade(ring, 38)
    out['ring'] = ring

    # ---------------- race on two pivots in the ring (roll about Y), a lip for the rotor, three detents on the top land
    rz0, rz1 = PZ - d['race_h'] / 2, PZ + d['race_h'] / 2
    race = sv.annulus('gimbal_race', O, Z, d['race_in'], d['race_out'], rz0, rz1, 44, M['gim_steel'], chamfer=0.25)
    det = []
    cut = []
    rm = (d['race_in'] + d['race_out']) / 2
    for deg in (35.0, 155.0, 275.0):
        rad, tan = radial(deg)
        cpt = rad * (rm * MM) + Z * (rz1 * MM)
        det.append(cpt)
        cut.append(G.cyl('_det', cpt - rad * (1.3 * MM) + Z * (0.12 * MM), cpt + rad * (1.3 * MM) + Z * (0.12 * MM), 0.6 * MM, 8))
    G.boolean(race, cut)
    for k, m in enumerate(race.data.materials):
        if m is None:
            race.data.materials[k] = M['gim_steel']
    lip = sv.annulus('race_lip', O, Z, d['lip_r'], d['race_in'] + 0.05, rz0, rz0 + d['lip_t'], 44, M['gim_steel'], chamfer=0.12)
    rc = [race, lip]
    for sgn in (1, -1):
        rc.append(G.pin('race_pivot', Pv + Y * (sgn * (d['race_out'] - 0.2) * MM), Pv + Y * (sgn * (d['ring_in'] - 0.06) * MM), 0.6 * MM, 10, M['gim_steel']))
    race = G.join('gimbal_race', rc)
    G.shade(race, 38)
    out['race'] = race
    grit = []
    for k, cpt in enumerate(det):
        grit.append(G.lathe('gimbal_grit_%d' % (k + 1), [([(-0.42 * MM, 0), (-0.3 * MM, 0.42 * MM), (0.05 * MM, 0.5 * MM), (0.3 * MM, 0.3 * MM), (0.4 * MM, 0)], False)],
                            6, cpt - Z * (0.1 * MM), Z, X, M['grit'], phase=0.4 * k))
    out['grit'] = grit

    # ---------------- rotor: brass flywheel on a steel spindle, and the bob that swings inside the coil
    zs = rz0 + d['lip_t'] + 0.05
    zt = zs + d['rotor_t']
    R = d['rotor_r']
    top = d['spindle_top']
    disc_prof = [(zs, 1.9), (zs, R - 0.25), (zs + 0.25, R), (zt - 0.3, R), (zt, R - 0.3), (zt, R - 1.4), (zt - 0.5, R - 1.8), (zt - 0.5, 3.0), (zt + 0.45, 2.7), (zt + 0.45, 1.9)]
    disc = G.lathe('rotor_disc', [([(a * MM, b * MM) for a, b in disc_prof], True)], 44, O, Z, X, M['gim_brass'])
    G.boolean(disc, [G.cyl('_bal', Vector((math.cos(a) * 4.5 * MM, math.sin(a) * 4.5 * MM, (zt - 1.0) * MM)),
                           Vector((math.cos(a) * 4.5 * MM, math.sin(a) * 4.5 * MM, (zt + 1.0) * MM)), 0.55 * MM, 8) for a in (0.5, 2.7, 4.6)])
    for k, m in enumerate(disc.data.materials):
        if m is None:
            disc.data.materials[k] = M['gim_brass']
    sp_prof = [(d['bob_z1'] - 0.2, 0.0), (d['bob_z1'] - 0.2, d['stem_r']), (zs + 0.4, d['stem_r']), (zs + 0.4, 1.85), (zt + 0.45, 1.85),
               (zt + 0.45, d['spindle_r']), (top - 0.25, d['spindle_r']), (top, d['spindle_r'] - 0.25), (top, 0.0)]
    spindle = G.lathe('rotor_spindle', [([(a * MM, b * MM) for a, b in sp_prof], False)], 16, O, Z, X, M['steel_bright'])
    b0, b1, br = d['bob_z0'], d['bob_z1'], d['bob_r']
    bob = G.lathe('rotor_bob', [([(a * MM, b * MM) for a, b in ((b0, 0.0), (b0, br - 0.5), (b0 + 0.5, br), (b1 - 0.5, br), (b1, br - 0.5), (b1, 0.0))], False)],
                  28, O, Z, X, M['magnet'])
    band = sv.annulus('rotor_band', O, Z, br - 0.05, br + 0.1, b0 + 1.4, b0 + 2.4, 28, M['gim_brass'])
    rotor = G.join('gimbal_rotor', [disc, spindle, bob, band])
    G.shade(rotor, 38)
    out['rotor'] = rotor

    # ---------------- retaining ring: an internal snap ring in the race's bore above the flywheel
    g = math.radians(24)
    rprof = [((zt + 0.1) * MM, (R - 0.8) * MM), ((zt + 0.1) * MM, (d['race_in'] - 0.05) * MM), ((zt + 0.6) * MM, (d['race_in'] - 0.05) * MM), ((zt + 0.6) * MM, (R - 0.8) * MM)]
    ret = G.lathe('gimbal_retainer', [(rprof, True)], 30, O, Z, X, M['steel_blued'], arc=(g, 2 * math.pi - g))
    G.fill_holes(ret)
    eyes = []
    for sgn in (1, -1):
        a = sgn * (g + 0.17)
        ec = Vector((math.cos(a) * (R - 1.2) * MM, math.sin(a) * (R - 1.2) * MM, (zt + 0.1) * MM))
        eye = G.prism('ret_eye', G.circle(0.8 * MM, 8), 0.5 * MM, ec, X, Y, Z, M['steel_blued'], w0=0.0)
        G.boolean(eye, [G.prism('_re', G.circle(0.33 * MM, 6), 2 * MM, ec, X, Y, Z, w0=-0.5 * MM)])
        eyes.append(eye)
    ret = G.join('gimbal_retainer', [ret] + eyes)
    G.shade(ret, 35)
    out['retainer'] = ret

    # ---------------- place everything with the datum frame, and hand back the points in world space
    MD = Matrix(MD)
    for o in [cradle, coil, ring, race, rotor, ret] + grit:
        o.matrix_world = MD
    bpy.context.view_layer.update()
    R3 = MD.to_3x3()
    W = lambda v: MD @ Vector(v)
    out['pivot'] = W(Pv)
    out['detents'] = [W(c) for c in det]
    out['rotor_seat'] = W((0, 0, zs * MM))
    out['retainer_seat'] = W((0, 0, (zt + 0.1) * MM))
    out['trunnions'] = [W((sgn * (CR - 0.45) * MM, 0, PZ * MM)) for sgn in (1, -1)]
    out['screws'] = [W(pol(d['screw_at'], deg)) for deg in d['screw_deg']]
    out['notch'] = [{'in': W(pol(CR - 0.1, deg, -1.7)), 'rim': W(pol(FR, deg, -1.7)), 'dir': R3 @ radial(deg)[0], 'tail': W(t)} for deg, t in zip(d['notch_deg'], tail_tops)]
    out['sense'] = {'in': W(pol(CR + 1.6, d['sense_deg'], -1.0)), 'rim': W(pol(FR, d['sense_deg'], -1.0)), 'dir': R3 @ radial(d['sense_deg'])[0]}
    out['axes'] = {'x': R3 @ X, 'y': R3 @ Y, 'z': R3 @ Z}
    out['zs'] = zs; out['zt'] = zt
    return out
