# Stabilised Pistol Grip: what is new when the grip exists (SEAM.md section 9): the fused core, the two brass grip
# screws, the nanite seams, and the marks and paths on the core. Built in the pistol's metric frame P, so grip.glb
# placed on pistol.glb is the fitted grip. Interface: INTERFACE.md / interface.json.
#
# NOT in this family (they seat on the core's pose marks): the gimbal damper unit and the four plate screws (servo
# family), the side plates, the strap, the damper loop and the leads (materials family). The plates and the strap are
# built here from interface.json only as STAND-INS, registered under their materials ids: they are in grip.blend for
# the sweeps and the review renders, and are not exported and not in parts.json.
#
#   SH/blender.sh grip/build.py -- --nobake [--review --only six,close,exploded] [--warm]
#   SH/run.sh mp-gbake SH/blender.sh grip/build.py -- --size 2048 --spp 24 ; SH/wait.sh mp-gbake
import sys, os, math, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'kit'))
from family import Family, G, MT, CT, RG, BK
import am_parts as AP
import pgeom as PG                       # frozen copy of pistol/pgeom.py (the interface's numbers)
from pgeom import P, GP, DP, xz, us, uy, ycyl, MM, X, Y, Z, U_, S_, G0
import numpy as np
import bpy, bmesh
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

F = Family('grip', __file__, budget=25000)
M = F.mats
DIRT = ((0.16, 0.12, 0.09), 0.85, 0.75)
# fused nanite alloy: a sintered skin a little darker and cooler than the shared bare alloy (linear about 0.26),
# granular, with a brown heat tint in patches; bright where the flash was knocked off and along worn edges.
# (MT.make takes sRGB: the first pass's (0.42, 0.43, 0.46) was linear 0.15, a graphite black under the calibrated rig.)
RAW = ('film', (0.47, 0.46, 0.44), 0.86, 1.5, 200)         # the as-found set: fresh from the mould, a dull grey skin under release powder
M['fused'] = MT.make('fused', (0.55, 0.555, 0.575), 1.0, 0.50, var=0.10, edge=((0.88, 0.87, 0.84), 1.0, 0.24, 1.0), dirt=((0.16, 0.13, 0.11), 0.85, 0.7),
                     bumps=[('stipple', 3000, 0.42), ('noise', 260, 0.38), ('noise', 38, 0.10)], grime=0.34,
                     tone2=((0.47, 0.41, 0.36), 42, 0.50, 0.78, 0.42), edge_width=0.0011, rough_var=0.14, wipe=RAW)
# the same alloy where a tool has been (linear about 0.57): pocket bore, counterbore, drilled holes. As found it is cast skin.
M['fused_cut'] = MT.make('fused_cut', (0.79, 0.785, 0.77), 1.0, 0.32, var=0.05, edge=((0.92, 0.91, 0.89), 1.0, 0.18, 0.8), dirt=((0.16, 0.13, 0.11), 0.85, 0.55),
                         bumps=[('lathe', 'Y', 1500, 0.22), ('noise', 500, 0.12)], grime=0.3, edge_width=0.0006, wipe=RAW)
# the parting line: filed bright where the flash was knocked off; as found, the dark witness line the flash stands on
M['fused_filed'] = MT.make('fused_filed', (0.83, 0.825, 0.81), 1.0, 0.36, var=0.06, edge=((0.93, 0.92, 0.90), 1.0, 0.2, 0.6), dirt=((0.16, 0.13, 0.11), 0.85, 0.4),
                           bumps=[('noise', 1100, 0.3), ('noise', 240, 0.22)], grime=0.2, edge_width=0.0005,
                           wipe=('film', (0.34, 0.33, 0.32), 0.9, 1.6, 200))
M['plate_bare'] = MT.make('plate_bare', MT.from_linear(MT.BARE_ALLOY), 1.0, MT.BARE_ALLOY_ROUGH, var=0.05, edge=((0.80, 0.79, 0.76), 1.0, 0.25, 0.8), dirt=DIRT,
                          bumps=[('brushed', (1, 1, 12), 0.18)], grime=0.25)
M['seam'] = MT.make('seam', (0.83, 0.84, 0.87), 1.0, 0.22, var=0.06, bumps=[('noise', 1500, 0.4), ('noise', 300, 0.25)], bevel_r=0.0,
                    wipe=('all', (0.42, 0.43, 0.45), 0.80, 1.0))
PL_OUT, PL_IN = 19.55, 17.55             # plate faces (|Y|)
SEAT = 17.5                              # the core's flat side faces: the plates' seat, and z = 0 of the unit's datum D
RC = 2.0                                 # the core's corner radius
OUT = PG.outline()
D0 = DP(0, 0, 0)
ifc = json.load(open(os.path.join(HERE, 'interface.json')))
SERVO_SCREWS = ['servo.screw_case_a', 'servo.screw_case_b', 'servo.screw_case_c', 'servo.screw_case_d']
UNIT = ['servo.gimbal_cradle']
PLATE_L, PLATE_R, STRAP = 'materials.sheet_a_plate', 'materials.sheet_b_plate', 'materials.strap_bent'


def paint(o, mat):
    o.data.materials.clear(); o.data.materials.append(mat)
    for p in o.data.polygons:
        p.material_index = 0
    return o


def frame(origin, x, y, z):
    Mx = Matrix((Vector(x), Vector(y), Vector(z))).transposed().to_4x4()
    Mx.translation = Vector(origin)
    assert Mx.to_3x3().determinant() > 0.99, 'left-handed frame'
    return Mx


def out_normals(poly):
    """Outward unit normals (2D) of a closed polygon's vertices."""
    n = len(poly)
    area = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n))
    sg = 1.0 if area > 0 else -1.0
    out = []
    for i in range(n):
        t = Vector(poly[(i + 1) % n]) - Vector(poly[i - 1])
        out.append((Vector((t.y, -t.x)) * sg).normalized())
    return out


# ====================================================================== strap stand-in (the core is cut round it)
def strap_path():
    """The strap's inner face in (U, S): 2.0 under the grip's surface, down the back, round the heel, along the base and
    up over the toe. It goes on from below (+S), so the back leg and the toe lip are both parallel to the grip axis."""
    return [tuple(p) for p in ifc['strap']['inner_face_path_G_us']]


def build_strap():
    pts = [GP(u, s, 0) for u, s in strap_path()]
    cen = GP(0, -20, 0)
    o = G.band_path('strap', G.chaikin(pts, 2, closed=False), 17.0 * MM, 2.0 * MM, lambda p, t: p - cen, M['plate_bare'], closed=False, offset=-0.05 * MM)
    G.bevel(o, 0.3 * MM, 1, 30)
    me = o.data
    paint(o, M['plate_bare'])
    me.materials.append(M['paint_orange'])
    for p in me.polygons:          # old Warden orange on the face that looks outward
        c = Vector(p.center)
        if p.normal.dot(c - cen) > 0.5 * (c - cen).length and abs(p.normal.y) < 0.5:
            p.material_index = 1
    G.shade(o, 40)
    return o


# ====================================================================== core
PARTING = []          # (point, normal) along the parting line on the finished core, filled by build_core


def core_ring(s, n=4):
    """Section of the core at level s: a flat-sided slab with rounded corners, back and front on the old grip's line."""
    ub = PG.back_new(s); uf = float(np.interp(s, PG._ST_N, PG._UF_N))
    pts = []
    for cu, cy, a0 in ((uf - RC, SEAT - RC, 0), (ub + RC, SEAT - RC, 90), (ub + RC, -(SEAT - RC), 180), (uf - RC, -(SEAT - RC), 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90.0 * k / n)
            pts.append(GP(cu + RC * math.cos(a), s, cy + RC * math.sin(a)))
    return pts


def build_core(strap):
    al = M['fused']
    region = [(31, 37.2), (27.4, 39.55), (19.4, 50.9), (11.4, 58.7), (-5.5, 54.7), (-18.0, 56.5), (-18.5, 44.5), (-20.0, 42.0), (-40, 41.85),
              (-40, -52), (-30.5, -53.2), (-24.0, -55.2), (28.6, -47.9), (31, -47.5)]
    core = G.loft('core', [core_ring(-58.0 + 5.0 * i) for i in range(25)], al)
    G.boolean(core, [us('_r', region, -30, 30)], 'INTERSECT')
    F.log('core blank', G.solid_check(core))
    G.bevel(core, 0.6 * MM, 1, 30)
    F.log('core bevelled', G.solid_check(core))
    paint(core, al)
    blank = BVHTree.FromObject(core, bpy.context.evaluated_depsgraph_get())        # the outer skin before anything is cut into it

    def cut(cs):
        G.boolean(core, cs if isinstance(cs, list) else [cs])
    # the T-slot for the tang, open at the top, with room in front for the bus strip and a bay for the socket block
    slot = [(6.75, -2.7), (6.75, 2.7), (5.2, 2.7), (5.2, 3.55), (-13.0, 3.55), (-16.05, 6.15), (-19.25, 6.15), (-19.25, -6.15), (-16.05, -6.15),
            (-13.0, -3.55), (5.2, -3.55), (5.2, -2.7)]
    cuts = [uy('_slot', slot, -6.4, 64)]
    # where the frame runs on between the plates' top edges, a hair of relief
    top = [(27.4, 39.55), (19.4, 50.9), (11.4, 58.7), (-5.5, 54.7), (-18.0, 56.5)]
    band = [(u, s + 1.0) for u, s in top] + [(u, s - 0.45) for u, s in reversed(top)]
    cuts.append(us('_band', band, -3.8, 3.8))
    # the window in the back for the plug, and the open channel the trigger lead lies in above it
    cuts.append(us('_win', [(-40, -6.2), (-13.3, -6.2), (-13.3, 1.0), (-40, 1.0)], -3.75, 3.75))
    ch = [(-40, 43)] + [(PG.back_new(s) + 3.3, s) for s in (43, 39, 36, 30, 21, 9, 3, 0.5)] + [(-40, 0.5)]
    cuts.append(us('_lead', ch, 2.5, 5.5))
    # 21 Nov (bench: s6.plug:route could not be seen): the channel's mouth is opened out to 5.6 wide and 1.2 deep, so the
    # lead in it shows from behind and from 45 degrees either side, not only from straight behind
    ch2 = [(-40, 42.6)] + [(PG.back_new(s) + 1.2, s) for s in (42.6, 39, 36, 30, 21, 9, 3, 0.9)] + [(-40, 0.9)]
    cuts.append(us('_leadmouth', ch2, 1.2, 6.8))
    # the strap's bed: an open channel 17.3 wide whose floor is 0.15 under the strap's inner face. It is cut right out
    # through the surface, because along the base and round the heel and toe the strap's outer face is 0.4 to 1.1 mm
    # inside the old grip's outline: a bed the strap's own shape would leave a skin over it and it could not slide on.
    sp = G.chaikin([GP(u, s, 0) for u, s in strap_path()], 2, closed=False)
    sp = [sp[0] + (sp[0] - sp[1]).normalized() * 0.15 * MM] + sp + [sp[-1] + (sp[-1] - sp[-2]).normalized() * 0.15 * MM]
    cen = GP(0, -20, 0)
    cuts.append(G.band_path('_bed', sp, 17.3 * MM, 8.2 * MM, lambda p, t: p - cen, None, closed=False, offset=-0.2 * MM))
    # cast-in lightening pockets with a rib between them, under the right plate; ejector witness marks
    for poly, depth in (([(-19.0, -37.6), (-3.0, -35.4), (-3.0, -13.0), (-19.0, -13.0)], 6.0),
                        ([(0.0, -35.0), (16.2, -32.8), (17.4, -13.0), (0.0, -13.0)], 6.0),
                        ([(2.5, 13.0), (18.6, 13.0), (20.0, 30.5), (12.0, 33.5), (2.5, 33.5)], 4.0)):
        cuts.append(us('_lp', PG.fillet(poly, 2.2, 3), SEAT - depth, 30))
    for u, s, sd in ((-22.0, 12.0, 1), (21.0, -24.0, 1), (9.0, 46.0, 1), (19.5, 30.0, -1), (-21.0, -12.0, -1), (6.0, 47.0, -1)):
        cuts.append(ycyl('_ej', u, s, 2.4, sd * (SEAT - 0.22), sd * 30, 16))
    # finger serrations cast into the front strap: V grooves 1.5 wide and 0.9 deep, every 4 mm, on the flat of the face
    for i in range(15):
        s0 = -25.0 + 4.0 * i
        f = float(np.interp(s0, PG._ST_N, PG._UF_N))
        cuts.append(us('_ser', [(f + 1.0, s0 - 1.6), (f - 0.9, s0), (f + 1.0, s0 + 1.6)], -14.6, 14.6))
    cut(cuts)
    for p in core.data.polygons:
        p.material_index = 0
    # ---- what a tool made after the mould (bright): pocket, loop channel, holes
    core.data.materials.append(M['fused_cut'])
    n0 = len(core.data.polygons)
    pk = ifc['pocket_as_modelled_in_grip_core']
    cuts = [G.cyl('_cb', DP(0, 0, 5), DP(0, 0, -pk['counterbore']['depth']), pk['counterbore']['d'] / 2 * MM, 48),
            G.cyl('_bore', DP(0, 0, 5), DP(0, 0, -pk['bore']['depth']), pk['bore']['d'] / 2 * MM, 48)]
    kw = pk['keyway']
    cuts.append(G.box('_key', DP(0, -(kw['r_out'] + 11.0) / 2, -pk['bore']['depth'] / 2 + 2.5), ((kw['r_out'] - 11.0) * MM, kw['width'] * MM, (pk['bore']['depth'] + 4.9) * MM),
                      Matrix((U_, S_, -Y)).transposed()))
    # the damper loop's channel and the resistor bay, in the left face in front of the pocket
    lp = ifc['loop']
    zc = -lp['channel']['depth'] / 2 + 0.6
    path = [DP(lp['path_xy'][0][0] * 0.75, lp['path_xy'][0][1] * 0.75, zc)] + [DP(x, y, zc) for x, y in lp['path_xy']] + \
           [DP(lp['path_xy'][-1][0] * 0.75, lp['path_xy'][-1][1] * 0.75, zc)]
    cuts.append(G.band_path('_loop', G.chaikin(path, 1, closed=False), (lp['channel']['depth'] + 1.2) * MM, lp['channel']['width'] * MM,
                            lambda p, t: t.cross(Y), None, closed=False, offset=-lp['channel']['width'] / 2 * MM))
    rb = lp['resistor_bay']
    cuts.append(G.box('_bay', DP(0, lp['resistor']['centre_xy'][1], -rb['depth'] / 2 + 0.6), (rb['len'] * MM, rb['width'] * MM, (rb['depth'] + 1.2) * MM),
                      Matrix((S_, U_, -Y)).transposed()))
    # holes: the housing pin, the two grip screws (blind in the right wall), the four plate screws
    cuts.append(ycyl('_pin', PG.PIN[0], PG.PIN[1], 1.6, -30, 30))
    # 21 Nov (bench: s6.pin.r:flush, the pin's end sat 2.5 mm down a 3.2 mm hole): a 45 degree countersink on each face,
    # inside the plates' bite, so the pin's end shows from the side at up to 45 degrees
    for sd in (-1, 1):
        cuts.append(G.cyl('_pincs', GP(PG.PIN[0], PG.PIN[1], sd * 14.9), GP(PG.PIN[0], PG.PIN[1], sd * (SEAT + 0.3)), 1.5 * MM, 20, None,
                          r1=(1.5 + SEAT + 0.3 - 14.9) * MM))
    for k in 'AB':
        cuts.append(ycyl('_g', PG.HOLES[k][0], PG.HOLES[k][1], 2.15, -30, 14.6))
    ps = ifc['plate_screws']
    for k in 'CD':
        cuts.append(ycyl('_pl', PG.HOLES[k][0], PG.HOLES[k][1], 1.6, -SEAT - 1, -SEAT + 8.7))
        cuts.append(ycyl('_pr', PG.HOLES[k][0], PG.HOLES[k][1], 1.6, SEAT - 8.7, SEAT + 1))
    cut(cuts)
    # the mould parts on the grip's mid-plane (Y = 0): a band 1.6 mm wide round the outside there is its own surface
    HW = 0.8 * MM
    bm = bmesh.new(); bm.from_mesh(core.data)
    for yy in (-HW, HW):
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, yy, 0), plane_no=(0, 1, 0), dist=1e-7,
                               clear_inner=False, clear_outer=False)
    bm.normal_update(); bm.faces.ensure_lookup_table(); bm.faces.index_update()
    tree = BVHTree.FromBMesh(bm)
    band = set()
    for f in bm.faces:
        c = f.calc_center_median()
        if abs(c.y) < HW and abs(f.normal.y) < 0.5 and tree.ray_cast(c + f.normal * 2e-5, f.normal, 0.08)[0] is None:
            band.add(f.index)          # it looks out of the part, not across a slot or a hole
    # ... and the line itself, for the flash (materials.core_flash) and whoever files it: front strap, toe, base, heel, back
    cen = GP(0, 0, 0)
    for k in range(52):
        ph = math.radians(40.0 - 275.0 * k / 51)
        org = GP(120 * math.cos(ph), 120 * math.sin(ph), 0)
        dr = (cen - org).normalized()
        h0 = blank.ray_cast(org, dr, 0.3); h1 = tree.ray_cast(org, dr, 0.3)
        if h0[0] is None or h1[0] is None or h1[3] - h0[3] > 5 * MM:
            continue                   # through the plug window or a hole: not on the outside
        PARTING.append((h1[0].copy(), h1[1].copy()))
    bm.to_mesh(core.data); bm.free()
    core.data.update()
    # faces a tool made after the mould (bright): inside the pocket and the keyway, and the walls of the drilled holes
    me = core.data
    me.materials.clear(); me.materials.append(al); me.materials.append(M['fused_cut']); me.materials.append(M['fused_filed'])
    rcb = pk['counterbore']['d'] / 2 + 0.05
    for p in me.polygons:
        p.material_index = 0
        c = Vector(p.center)
        u, s, y = PG.to_us(c)
        dv = c - D0
        dx, dy, dz = dv.dot(S_) / MM, dv.dot(U_) / MM, dv.dot(-Y) / MM          # in D, mm
        if math.hypot(dx, dy) < rcb and -pk['bore']['depth'] - 0.2 < dz < -0.05:
            p.material_index = 1
        if abs(p.normal.y) < 0.5:
            for hu, hs, r in [PG.HOLES[k] + (2.15 if k in 'AB' else 1.6,) for k in 'ABCD'] + [PG.PIN + (1.6,)]:
                if math.hypot(u - hu, s - hs) < r + 0.06:
                    p.material_index = 1
        if p.index in band and p.material_index == 0:
            p.material_index = 2
    from collections import Counter
    F.log('core faces per slot', dict(Counter(p.material_index for p in me.polygons)), 'slots', [m.name if m else None for m in me.materials])
    bits = [core]
    # locating pegs for the plates at A and B (hollow on the left, where the grip screws go through)
    for k in 'AB':
        u, s = PG.HOLES[k]
        bits.append(AP.tube('peg', 5.9 * MM, 4.3 * MM, 1.8 * MM, al, 16, at=GP(u, s, -SEAT + 0.05), axis=-Y))
        bits.append(G.cyl('pegr', GP(u, s, SEAT - 0.05), GP(u, s, SEAT + 1.8), 2.95 * MM, 16, al, chamfer=0.3 * MM))
    # two spring clips in the loop channel
    for cx, cy in lp['clips_xy']:
        bits.append(AP.clip('clip', 2.4 * MM, 0.35 * MM, 0.9 * MM, M['steel_bright'], legs=0.5 * MM, at=DP(cx, cy, -lp['channel']['depth'] + 0.05), axis=-Y, ref=S_))
    o = G.join('core', bits)
    G.shade(o, 40, weighted=True)
    CT.part(o, 'grip', 'core', 'Grip core', kind='part', parent='pistol.frame', item='grip_stabilised_pistol', material='alloy', mass='medium', symmetry=1,
            tol_mm=4, tol_deg=12, held_by=['pistol.housing_pin', 'screw_a', 'screw_b'], steps=['s4.press', 's4.open', 's4.flash', 's4.pressfit', 's5.loop', 's6.slide'],
            origin=GP(-4, 20), touches=['pistol.cell_bus', 'pistol.lead', 'pistol.lead_plug', 'pistol.housing_pin'],
            note='fused alloy spine: flat seat faces for the two plates, T-slot for the tang, pocket for the damper unit, loop channel with two '
                 'clips, lead channel and plug window in the back, strap bed, pegs at A and B, lightening pockets under the right plate. It is the '
                 'pressed core from the moment the mould opens (SEAM.md section 10): the as-found texture set is the core fresh from the mould, '
                 'and materials.core_flash and core_sprue stand on it along path parting')
    CT.clear(o, offset=-S_ * 75 * MM)
    return o


def lead_route():
    """The line the trigger lead is fed along in the new grip (path grip.core/lead): out of the frame under the
    beavertail, down the back of the core along the MOUTH of the lead channel (21 Nov: the bench camera looks at the
    grip from 35 degrees toward the butt; on the channel's floor the points were hidden), and into the plug window,
    ending at its mouth. The lead itself lies deeper, in the channel."""
    pts = [GP(-21.4, 46.5, 3.5)]
    for s in (39, 36, 30, 21, 9, 3.5):
        pts.append(GP(PG.back_new(s) + 0.3, s, 3.5))
    pts += [GP(PG.back_new(0.2) + 0.3, 0.2, 2.0), GP(PG.back_new(-2.5) + 0.3, -2.5, 0.8), GP(PG.back_new(-4.0) + 0.3, -4.0, 0.0)]
    return pts


SEAM_IDX = 17          # the plate outline's first 17 corners: down the front, along the base, up the back, round the bite.
#                        Above that the plate's edge is the core's own top edge (the frame sits on it): nothing to trace.


def seam_line(sd, off, ylift, n=None):
    """The seam of one plate: the plate's edge where it meets the core's seat face, as 3D points and outward normals."""
    full = PG.offset_poly(OUT, off)
    nrm = out_normals(OUT)
    per = len(OUT) // len(PG.OUTLINE)                          # filleted corners: 4 points each
    i0, i1 = per - 1, per * (SEAM_IDX - 1) + 1                 # from the end of the first corner to the start of the last
    pts = [GP(u, s, sd * (SEAT + ylift)) for u, s in full[i0:i1]]
    nn = [((U_ * a.x + S_ * a.y) * 0.6 + Y * sd * 0.8).normalized() for a in nrm[i0:i1]]
    return pts, nn


def marks_and_paths(o):
    """Where other families' parts go (SEAM.md sections 2, 7, 9): pose marks in pairs, seat and clear."""
    lp = ifc['loop']
    Md = frame(D0, S_, U_, -Y)
    CT.pose_mark(o, 'seat_gimbal', Md, UNIT)
    CT.pose_mark(o, 'clear_gimbal', Matrix.Translation(-Y * 40 * MM) @ Md, UNIT)
    Ml = frame(GP(0, 0, -PL_IN), -U_, S_, -Y)
    Mr = frame(GP(0, 0, PL_IN), U_, S_, Y)
    CT.pose_mark(o, 'seat_plate_l', Ml, [PLATE_L])
    CT.pose_mark(o, 'clear_plate_l', Matrix.Translation(-Y * 30 * MM) @ Ml, [PLATE_L])
    CT.pose_mark(o, 'seat_plate_r', Mr, [PLATE_R])
    CT.pose_mark(o, 'clear_plate_r', Matrix.Translation(Y * 30 * MM) @ Mr, [PLATE_R])
    Ms = frame(G0, U_, S_, Y)
    CT.pose_mark(o, 'seat_strap', Ms, [STRAP])
    CT.pose_mark(o, 'clear_strap', Matrix.Translation(-S_ * 65 * MM) @ Ms, [STRAP])
    for sd, side in ((-1, 'l'), (1, 'r')):
        for k in 'CD':
            u, s = PG.HOLES[k]
            Mk = CT._zframe(GP(u, s, sd * PL_OUT), Y * sd, S_)
            CT.pose_mark(o, 'seat_plate_screw_%s%s' % (side, k.lower()), Mk, SERVO_SCREWS)
            CT.pose_mark(o, 'clear_plate_screw_%s%s' % (side, k.lower()), Matrix.Translation(Y * sd * 16 * MM) @ Mk, SERVO_SCREWS)
    CT.path(o, 'loop', [DP(x, y, lp['z']) for x, y in lp['path_xy']], [-Y for _ in lp['path_xy']])
    CT.path(o, 'lead', G.resample(G.chaikin(lead_route(), 2, False), 14), [(-U_) for _ in range(14)])
    for sd, nm in ((-1, 'seam_l'), (1, 'seam_r')):
        pts, nn = seam_line(sd, 0.25, 0.3)
        rs = G.resample(pts, 40)
        CT.path(o, nm, rs, [nn[min(range(len(pts)), key=lambda i: (pts[i] - Vector(r)).length)] for r in rs])
    # 21 Nov (bench: the shoulder is under the cradle once it is pressed in): where the cradle's key lug cracks, seen from
    # outside: on the flange's outer face over the lug (D: -Y_D, r 13), facing out of the pocket
    CT.mark(o, 'mend', DP(0, -13.0, 0.05), -Y)
    CT.mark(o, 'pocket_shoulder', DP(0, 0, -ifc['pocket_as_modelled_in_grip_core']['bore']['depth']), -Y)
    # the parting line (the flash stands on it, the file follows it): at most 40 of the points found on the surface
    pp = PARTING if len(PARTING) <= 40 else [PARTING[round(i * (len(PARTING) - 1) / 39)] for i in range(40)]
    CT.path(o, 'parting', [p for p, n in pp], [n for p, n in pp])
    # the as-found state and what takes it off (SEAM.md section 10): three boxes, each wiped across its thin side
    R = Matrix((U_, S_, Y)).transposed()
    CT.zone(o, 'skin', GP(-0.35, 1.75, 0), (32.5 * MM, 59.5 * MM, 21.5 * MM), R)
    CT.zone(o, 'flash', GP(-0.35, 1.75, 0), (32.5 * MM, 59.5 * MM, 2.5 * MM), R)
    CT.zone(o, 'pocket', GP(0, -26, -SEAT + 10.0), (16.5 * MM, 16.5 * MM, 11.0 * MM), R)
    CT.wipe(o, 'skin', zone='skin', label='Release powder on the dull cast skin (as-found set = fresh from the mould)')
    CT.wipe(o, 'flash', zone='flash', label='Parting line: filed bright where the flash was (s4.flash)')
    CT.wipe(o, 'pocket', zone='pocket', label='Bearing pocket: eased bright with the round file (s4.flash)')


# ====================================================================== screws, seams
def build_screws():
    out = []
    gs = ifc['grip_screws']
    for nm, k, label in (('screw_a', 'A', 'Upper grip screw (brass)'), ('screw_b', 'B', 'Lower grip screw (brass)')):
        u, s = PG.HOLES[k]
        o = AP.screw(nm, 3.8 * MM, gs['length_under_head'] * MM, head='pan', drive='cross', head_d=gs['head_d'] * MM, head_h=gs['head_h'] * MM, mat=M['brass'],
                     thread_len=11 * MM, pitch=0.9 * MM, at=GP(u, s, -PL_OUT - 0.02), axis=-Y, ref=S_, turn=0.3 if k == 'A' else 1.1)
        CT.fastener(o, 'grip', nm, label, bit='cross', turns=7, holds=[PLATE_L, 'core'], into='pistol.frame', shank_d=3.8 * MM, parent='core',
                    material='steel', steps=['s6.screws'], touches=['pistol.frame', PLATE_L],
                    note='M4 x 34 pan head, cross drive, from Brann\'s jar: through the left plate and the hollow peg, the tang, into the right wall')
        CT.clear_along(o, 42 * MM)
        out.append(o)
    return out


def build_seams():
    out = []
    for sd, nm in ((-1, 'seam_l'), (1, 'seam_r')):
        pts, nn = seam_line(sd, 0.2, 0.3)
        # five lengths end to end, not one tube: unwrapped whole, the 250 mm bead is one strip across the atlas and its
        # length alone set the scale of every other island (the core fell to 56.6 px/cm)
        k = (len(pts) - 1) // 5
        runs = [pts[i * k: (i + 1) * k + 1] if i < 4 else pts[i * k:] for i in range(5)]
        o = G.join(nm, [G.tube_path(nm, r, 0.45 * MM, 5, M['seam'], closed=False, twist_ref=Y) for r in runs])
        G.shade(o, 60)
        CT.part(o, 'grip', nm, 'Nanite seam, %s plate' % ('left' if sd < 0 else 'right'), parent='core', material='alloy', mass='tiny', flex=True,
                steps=['s5.seam', 's5.cure'], origin=GP(0, 0, sd * SEAT), touches=[PLATE_L if sd < 0 else PLATE_R],
                note='a bead, not a part to carry: shown as the seam is traced along path grip.core/%s (front edge, base, back edge and the bite; '
                     'the plate\'s top edge is the core\'s own edge). The as-found texture set is the uncured grey paste, the clean set the cured bead' % nm)
        CT.clear(o, offset=Y * sd * 10 * MM)
        CT.zone(o, 'seam', GP(0, 0, sd * (SEAT + 0.3)), (60 * MM, 60 * MM, 2 * MM), Matrix((U_, S_, Y)).transposed())      # x = U, y = S, thin along Y
        CT.wipe(o, 'seam', zone='seam', label='Uncured nanite paste')
        out.append(o)
    return out


# ====================================================================== stand-ins for the materials family's plates and strap
def build_standins(strap):
    out = []
    for sd, pid, label in ((-1, PLATE_L, 'Left side plate (stand-in)'), (1, PLATE_R, 'Right side plate (stand-in)')):
        y0, y1 = (-PL_OUT, -PL_IN) if sd < 0 else (PL_IN, PL_OUT)
        o = us('plate', OUT, y0, y1, M['plate_bare'])
        cuts = []
        for k, (u, s) in PG.HOLES.items():
            cuts.append(ycyl('_h', u, s, ifc['plate']['holes_G'][k]['d'] / 2, -30, 30))
        G.boolean(o, cuts)
        G.bevel(o, 0.3 * MM, 1, 30)
        paint(o, M['plate_bare'])
        o.data.materials.append(M['paint_orange'])
        for p in o.data.polygons:
            if p.normal.y * sd > 0.9:
                p.material_index = 1
        G.shade(o, 40)
        fam, short = pid.split('.')
        CT.part(o, fam, short, label, parent='grip.core', material='alloy', mass='light', fixed=True,
                note='STAND-IN built from grip/interface.json for the sweeps and renders; the real part is in the materials family')
        G.set_frame(o, bpy.data.objects['grip_core__mark_seat_plate_%s' % ('l' if sd < 0 else 'r')].matrix_world)
        out.append(o)
    fam, short = STRAP.split('.')
    CT.part(strap, fam, short, 'Reinforcement strap (stand-in)', parent='grip.core', material='alloy', mass='light', fixed=True,
            note='STAND-IN built from grip/interface.json for the sweeps and renders; the real part is in the materials family')
    G.set_frame(strap, bpy.data.objects['grip_core__mark_seat_strap'].matrix_world)
    out.append(strap)
    return out


# ====================================================================== build
strap = build_strap()
core = build_core(strap)
marks_and_paths(core)
screws = build_screws()
seams = build_seams()
standins = build_standins(strap)
for o in list(bpy.data.objects):
    if o.type == 'MESH' and 'sh' not in o:
        F.log('removing stray object', o.name)
        bpy.data.objects.remove(o, do_unlink=True)
for o in [core] + screws + seams + standins:
    sc = G.solid_check(o)
    F.log('solid', o.name, G.tris(o), sc)
F.log('built', {o.name: G.tris(o) for o in F.parts().values()})

BENCH = ['grip', 'servo', 'materials']        # what is on the bench while the grip is put together (the pistol is in the vise)
CT.absent(['core', 'screw_a', 'screw_b', 'seam_l', 'seam_r'])
CT.sequence([
    {'op': 'insert', 'part': 'core', 'step': 'check.bare_core'},               # the bare core up the tang (a fit check, not a bench step)
    {'op': 'insert', 'part': 'servo.gimbal_cradle', 'step': 's4.pressfit', 'unit': True, 'among': BENCH,
     'seat': 'grip_core__mark_seat_gimbal', 'clear': 'grip_core__mark_clear_gimbal'},
    {'op': 'insert', 'part': STRAP, 'step': 's5.strap', 'among': BENCH, 'seat': 'grip_core__mark_seat_strap', 'clear': 'grip_core__mark_clear_strap'},
    {'op': 'insert', 'part': PLATE_L, 'step': 's5.plates', 'group': 'plates', 'among': BENCH,
     'seat': 'grip_core__mark_seat_plate_l', 'clear': 'grip_core__mark_clear_plate_l', 'expect': UNIT},
    {'op': 'insert', 'part': PLATE_R, 'step': 's5.plates', 'group': 'plates', 'among': BENCH,
     'seat': 'grip_core__mark_seat_plate_r', 'clear': 'grip_core__mark_clear_plate_r'},
] + [
    {'op': 'insert', 'part': sid, 'step': 's5.torque', 'group': 'pscrews', 'among': BENCH, 'expect': [PLATE_L, PLATE_R, 'grip.core'],
     'seat': 'grip_core__mark_seat_plate_screw_' + hole, 'clear': 'grip_core__mark_clear_plate_screw_' + hole}
    for sid, hole in zip(SERVO_SCREWS, ('lc', 'ld', 'rc', 'rd'))
] + [
    {'op': 'insert', 'part': 'seam_l', 'step': 's5.seam', 'group': 'seams'},
    {'op': 'insert', 'part': 'seam_r', 'step': 's5.seam', 'group': 'seams'},
    {'op': 'remove', 'part': 'core', 'step': 'check.assembled_off'},           # the assembled grip, off the tang and on again
    {'op': 'insert', 'part': 'core', 'step': 's6.slide', 'unit': True},
    {'op': 'insert', 'part': 'pistol.lead_plug', 'step': 's6.plug'},
    {'op': 'insert', 'part': 'pistol.housing_pin', 'step': 's6.pin'},
    {'op': 'insert', 'part': 'screw_a', 'step': 's6.screws', 'group': 'gscrews'},
    {'op': 'insert', 'part': 'screw_b', 'step': 's6.screws', 'group': 'gscrews'},
])
F.uv_weights = {'grip_core': 1.0, 'grip_screw_a': 1.3, 'grip_screw_b': 1.3, 'grip_seam_l': 1.3, 'grip_seam_r': 1.3}
F.uv_align = True        # the two side faces lie at 25 degrees in their projection: turned square they pack far better
F.review_hero = ('grip_core',)
F.review_objs = list(F.parts().values()) + standins
EXF = 0.9          # the core stays where it is in the exploded view (its own clear pose is 75 mm down the tang)
F.explode = {'f': EXF, 'extra': {'grip_core': list(S_ * 0.075 * EXF), 'grip_screw_a': [0, -0.03, 0], 'grip_screw_b': [0, -0.03, 0],
                                 'materials_sheet_a_plate': [0, -0.035, 0], 'materials_sheet_b_plate': [0, 0.035, 0],
                                 'materials_strap_bent': list(-S_ * 0.05)}}
pj, st = F.finish(extra={
    'frame': 'P: the pistol metric frame (metres); place this family root on the pistol family root and the grip is fitted',
    'seats_on_pistol': 'grip_core rest pose = seated on pistol.frame (same frame as pistol.glb); grip_core__clear = slid 75 mm down off the tang; '
                       'the trigger lead is tucked along path grip.core/lead (grip_core__path_lead_00..13)',
    'interface': 'INTERFACE.md / interface.json',
    'foreign_parts': {
        'about': 'parts of other families that seat on grip.core: place the part\'s node on the seat mark (world transform), approach from the clear mark',
        'servo.gimbal_cradle (with what rides on it)': ['grip_core__mark_seat_gimbal', 'grip_core__mark_clear_gimbal'],
        PLATE_L: ['grip_core__mark_seat_plate_l', 'grip_core__mark_clear_plate_l'],
        PLATE_R: ['grip_core__mark_seat_plate_r', 'grip_core__mark_clear_plate_r'],
        STRAP: ['grip_core__mark_seat_strap', 'grip_core__mark_clear_strap'],
        'servo.screw_case_a..d (any screw in any hole)': ['grip_core__mark_seat_plate_screw_lc', '..._ld', '..._rc', '..._rd', 'grip_core__mark_clear_plate_screw_*'],
        'materials.loop_tucked': 'path grip.core/loop (the channel centre line, datum D at z -1.7)'},
    'in_hand': 'none from this family (SEAM.md section 9): integration builds grip_stabilised_pistol from the seated bench parts',
    'as_found': 'grip.core is the pressed core from the moment the mould opens (SEAM.md section 10). Its as-found set (tex/grip__dirty_*) is the '
                'core fresh from the mould: dull grey skin under release powder, pocket and holes as cast, a dark witness line on the parting plane. '
                'Three wipes on the core: skin (the whole core), flash (the slab round the parting plane, Y = 0) and pocket. The zones overlap: a '
                'texel should show the clean set only when EVERY zone that holds it has been wiped, so the pocket and the parting line stay as '
                'cast until s4.flash even if the skin is cleaned first. The seams\' as-found state is the uncured paste. The two spring clips in '
                'the loop channel are part of the core mesh and are there in both sets'})
