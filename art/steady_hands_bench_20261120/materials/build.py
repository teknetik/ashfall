# materials/build.py: the worked materials of the Steady Hands bench (family `materials`). See PARTS.md and README.md.
#
#   Scrap Alloy sheets A and B and everything cut from them (plate, margin, plugs, strap flat and bent, offcuts,
#   scribed line, swarf); the gimbal's leads in their bench states, the trim resistor, the heat-shrink sleeves and the
#   damper loop (as soldered, and tucked) in the gimbal cradle's frame D; the nanite vial; the bobbin and its copper.
#   The raw core, its flash and sprue and the poured charge wait for grip/export/grip.glb (listed under `pending`).
#
# Frames (SEAM.md section 9, grip/interface.json): a plate's node frame is the grip frame G projected on its inner
# face (+Y = S, +Z out of the grip; +X = -U on the left plate, +U on the right); the strap's node frame is G. The
# node's transform lays the piece in its sheet. Everything that hangs on the gimbal is modelled in D with an identity
# node transform (parent servo.gimbal_cradle); there the bench is at z = -20 mm. Loose things stand on z = 0.
#
#   SH/blender.sh materials/build.py -- --nobake      then  SH/blender.sh materials/check.py
import sys, os, math, json
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ('pistol', 'servo', '.', 'kit'):          # the kit first: servo/ and pistol/ have their own check.py, review.py, measure.py
    sys.path.insert(0, os.path.normpath(os.path.join(HERE, '..', p)) if p != '.' else HERE)
from family import Family, G, MT, CT, RG
import am_parts as AP
import bpy, bmesh
from mathutils import Vector, Matrix
import sv
import mtl
from mtl import MM, enc
import pgeom as PG          # only fillet() and offset_poly(): the same corner easing the grip core's recess is cut with

FAM = 'materials'
F = Family(FAM, __file__, budget=15700)          # 15k plus core_flash and core_sprue (SEAM.md section 10)
M = F.mats
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
ifc = json.load(open(os.path.join(HERE, '..', 'grip', 'interface.json')))
NOTES = F.notes


def V(x, y, z=0.0):
    return Vector((x * MM, y * MM, z * MM))


def rdp(P, tol):
    """Drop points of a polyline that lie within tol (metres) of the line through their neighbours."""
    P = [Vector(p) for p in P]
    if len(P) < 3:
        return P
    a, b = P[0], P[-1]
    ab = b - a
    best, idx = 0.0, 0
    for i in range(1, len(P) - 1):
        d = ((P[i] - a).cross(ab)).length / ab.length if ab.length > 1e-12 else (P[i] - a).length
        if d > best:
            best, idx = d, i
    if best <= tol:
        return [a, b]
    return rdp(P[:idx + 1], tol)[:-1] + rdp(P[idx:], tol)


def remat(o, mat, test):
    me = o.data
    names = [m.name for m in me.materials]
    if mat.name not in names:
        me.materials.append(mat); names.append(mat.name)
    i = names.index(mat.name)
    R = o.matrix_world.to_3x3()
    for p in me.polygons:
        if test(o.matrix_world @ p.center, R @ p.normal):
            p.material_index = i
    return o


# ====================================================================== materials
DIRT = ((0.16, 0.12, 0.09), 0.85, 0.75)
DUSTY = ((0.42, 0.35, 0.27), 0.9, 0.5)
M['al_old'] = MT.make('al_old', enc(tuple(x * 0.85 for x in mtl.BARE_LIN)), 1.0, 0.6, var=0.08, dirt=((0.16, 0.12, 0.09), 0.85, 0.5), bumps=[('noise', 900, 0.4)], bevel_r=0.0002)
M['al_cut'] = MT.make('al_cut', mtl.FRESH, 1.0, 0.32, var=0.05, bumps=[('lathe', 'Z', 2600, 0.5), ('noise', 2200, 0.25)], bevel_r=0.0)
M['al_filed'] = MT.make('al_filed', mtl.FRESH, 1.0, 0.30, var=0.04, bumps=[('brushed', (22, 22, 1), 0.35)], bevel_r=0.0)
M['al_scribe'] = MT.make('al_scribe', enc((0.72, 0.71, 0.69)), 1.0, 0.25, var=0.03, bevel_r=0.0)
M['al_swarf'] = MT.make('al_swarf', enc((0.66, 0.65, 0.63)), 1.0, 0.26, var=0.05, bumps=[('noise', 2600, 0.3)], bevel_r=0.0)
# wires and the resistor: the servo's own colours (servo/build.py), so a lead does not change colour when the unit is on the bench
M['wire_red'] = MT.make('wire_red', (0.36, 0.055, 0.04), 0.0, 0.6, var=0.14, dirt=((0.42, 0.35, 0.27), 0.9, 0.6), grime=0.6, bumps=[('noise', 900, 0.25)])
for nm, col in (('wire_bone', (0.56, 0.50, 0.38)), ('band_pale', (0.80, 0.76, 0.64)), ('band_yellow', (0.80, 0.62, 0.06)), ('res_body', (0.62, 0.50, 0.33)),
                ('res_red', (0.55, 0.06, 0.04)), ('res_dark', (0.06, 0.04, 0.03)), ('res_gold', (0.70, 0.55, 0.22))):
    M[nm] = MT.make(nm, col, 0.0, 0.5, var=0.1, dirt=((0.42, 0.35, 0.27), 0.9, 0.5))
M['shrink'] = MT.make('shrink', (0.032, 0.032, 0.035), 0.0, 0.62, var=0.1, edge=((0.10, 0.10, 0.10), 0.0, 0.5, 0.4), dirt=DUSTY, bumps=[('noise', 1600, 0.2)])
# strands: tinned bright in the GLB, bare twisted copper in the as-found set (wipe 'tin')
M['strand'] = MT.make('strand', (0.76, 0.76, 0.74), 1.0, 0.2, var=0.05, bumps=[('lathe', 'Y', 5200, 0.6), ('noise', 2400, 0.3)], bevel_r=0.0)
mtl.dirty_layer(M['strand'], (0.85, 0.47, 0.30), 0.34, 1.0)
M['res_leg'] = MT.make('res_leg', (0.76, 0.76, 0.74), 1.0, 0.2, var=0.05, bumps=[('noise', 1800, 0.3)], bevel_r=0.0)
mtl.dirty_layer(M['res_leg'], (0.46, 0.44, 0.40), 0.5, 1.0)
M['copper_enamel'] = MT.make('copper_enamel', (0.56, 0.25, 0.13), 1.0, 0.36, var=0.14, edge=((0.86, 0.52, 0.34), 1.0, 0.22, 0.7), edge_width=0.0003,
                             dirt=((0.10, 0.06, 0.04), 0.8, 1.0), grime=0.3, bevel_r=0.0002)
M['wound'] = MT.make('wound', (0.74, 0.40, 0.21), 1.0, 0.30, var=0.12, dirt=((0.10, 0.06, 0.04), 0.8, 0.5), grime=0.25, bevel_r=0.0,
                     bumps=[('lathe', 'Z', 2300, 1.3), ('noise', 900, 0.2)], tone2=((0.50, 0.24, 0.13), 240, 0.45, 0.7, 0.5))
M['flange'] = MT.make('flange', (0.36, 0.35, 0.33), 1.0, 0.5, var=0.1, edge=((0.62, 0.60, 0.57), 1.0, 0.3, 0.9), dirt=DIRT, rust=((0.38, 0.19, 0.08), 0.5, 0.9, 30),
                      bumps=[('stipple', 2000, 0.35), ('noise', 500, 0.3)], grime=0.5)
M['iron_wire'] = MT.make('iron_wire', (0.20, 0.17, 0.15), 0.9, 0.58, var=0.12, rust=((0.36, 0.18, 0.08), 0.9), bumps=[('noise', 1500, 0.4)], bevel_r=0.0)
M['stopper'] = MT.make('stopper', (0.075, 0.068, 0.062), 0.0, 0.78, var=0.14, edge=((0.17, 0.16, 0.15), 0.0, 0.7, 0.7), dirt=DUSTY, bumps=[('stipple', 1500, 0.4), ('noise', 500, 0.3)], grime=0.6)
M['etch'] = MT.make('etch', (0.78, 0.80, 0.79), 0.0, 0.9, var=0.1, bumps=[('noise', 3000, 0.4)], bevel_r=0.0)
# nanite residue: a dull grey-silver fluid, darker where it has settled, with a faint cool glint (no light)
M['nanite'] = MT.make('nanite', enc((0.17, 0.175, 0.19)), 0.85, 0.40, var=0.1, bumps=[('noise', 2600, 0.5)], bevel_r=0.0, tone2=(enc((0.10, 0.105, 0.12)), 70, 0.45, 0.75, 0.5))
M['vial_glass'] = MT.passthrough('vial_glass', (0.82, 0.88, 0.85), alpha=0.13, rough=0.05)          # clearer than the library's glass: the residue has to read grey through it
_b = MT.NB(M['nanite']); _P = sv._obj(M['nanite'])
_z = mtl._sep(M['nanite'], _P)[2]
sv._layer(M['nanite'], _b.math('SUBTRACT', 1.0, _b.ramp(_z, 0.001, 0.013)), enc((0.07, 0.072, 0.08)), 0.6, 0.6)                 # the settled bottom third
sv._layer(M['nanite'], _b.ramp(_b.noise(_P, 5200.0, 2, 0.5), 0.70, 0.74), enc((0.78, 0.84, 0.93)), 0.16, 1.0)                 # the glint

# ====================================================================== interface numbers
PLATE = ifc['plate']
OUT_US = [tuple(p) for p in PLATE['outline_G_us']]
HOLES = {k: (v['u'], v['s'], v['d'] / 2.0) for k, v in PLATE['holes_G'].items()}
T = float(PLATE['thickness'])
RAD = float(PLATE['corner_radius'])
STRAP = ifc['strap']
SW_, ST_ = float(STRAP['width']), float(STRAP['thickness'])
SL = float(STRAP['developed_length'])
SPATH = [tuple(p) for p in STRAP['inner_face_path_G_us']]
FIL = PG.fillet(OUT_US, RAD)                      # (u, s), the eased outline: exactly what the grip core's recess follows
NOTES['colours'] = {'warden_orange_linear': list(mtl.ORANGE_LIN), 'bare_alloy_linear': list(mtl.BARE_LIN),
                    'from': 'kit/mats.py constants' if mtl.KIT_READY else "the orchestrator's ruling of 19:25 (the kit's constants were interim; no KIT RIG FIXED line yet)"}
NOTES['interface'] = {'plate_points': len(OUT_US), 'plate_thickness': T, 'strap_developed_length': SL, 'strap_path_points': len(SPATH),
                      'pgeom_outline_equals_interface': [tuple(p) for p in PG.OUTLINE] == OUT_US}

# ====================================================================== the two sheets
SWD, SHT = 120.0, 90.0                # sheet, plan (PARTS.md)
X0, Y0 = 56.0, 54.5                   # where the grip-frame origin G lies in the sheet's plan: x = X0 + s, y = Y0 + u
MARGIN = 0.6
Y_MID, X_SPLIT = Y0, 62.0             # where the snips ran out to the edges
BOLT_R = 2.6
BOLTS = [(8.5, 81.5), (111.5, 25.0)]


def tear(p0, p1, ph, nicks):
    """A torn edge from p0 to p1 (plan, mm): a slow wave, a faster ripple and a few sharp nicks, into the sheet."""
    a, b = Vector(p0), Vector(p1)
    d = (b - a).normalized()
    inw = Vector((-d.y, d.x)) if Vector((-d.y, d.x)).dot(Vector((60, 45)) - a) > 0 else Vector((d.y, -d.x))
    n = 15
    out = [tuple(a)]
    for i in range(1, n):
        t = (i + 0.38 * math.sin(i * 2.1 + ph)) / n
        off = 0.9 + 1.0 * math.sin(2.3 * math.pi * t + ph) + 0.45 * math.sin(7.1 * math.pi * t + 2 * ph) + (1.5 if i in nicks else 0.0)
        out.append(tuple(a.lerp(b, t) + inw * max(0.0, off)))
    return out + [tuple(b)]


SHEET = {
    'a': {'O': Vector((0.200, -0.045, 0.0)), 'paint_up': True, 'tear': tear((120, 72), (104, 90), 0.4, (4, 10))},
    'b': {'O': Vector((0.350, -0.045, 0.0)), 'paint_up': False, 'tear': tear((120, 68), (109, 90), 2.2, (6, 11))},
}


def plan(u, s):
    return (X0 + s, Y0 + u)


PP = [plan(u, s) for u, s in FIL]                                  # the plate (= the scribed line) in the sheet's plan
MOUT = PG.offset_poly(PP, MARGIN)                                  # where the snips cut
CORNERS = [plan(u, s) for u, s in OUT_US]
lo_x, hi_x = min(p[0] for p in MOUT), max(p[0] for p in MOUT)
lo_y, hi_y = min(p[1] for p in MOUT), max(p[1] for p in MOUT)
assert lo_x > 3.0 and hi_x < SWD - 3.0 and lo_y > SW_ + 6.0 and hi_y < SHT - 5.0, 'the plate does not fit the sheet: %s' % [lo_x, hi_x, lo_y, hi_y]
assert SL < SWD - 1.0, 'the strap is longer than the sheet'
for (bx, by) in BOLTS:
    assert mtl.dist_to_poly((bx, by), MOUT) > BOLT_R + 1.5, 'an old bolt hole is too near the plate'

# strap geometry in G (mm): the smoothed inner-face path, outward normals, the neutral axis
CEN = Vector((0.0, -20.0))
_sp = [Vector(p) for p in G.chaikin([Vector((u, s, 0)) for u, s in SPATH], 2, closed=False)]
_sp = [Vector((p.x, p.y)) for p in rdp(_sp, 0.03)]


def strap_frames(path):
    """[(inner point, tangent, outward normal)] for a 2D inner-face path."""
    out = []
    n = len(path)
    for i, p in enumerate(path):
        t = (path[min(i + 1, n - 1)] - path[max(i - 1, 0)]).normalized()
        nn = Vector((t.y, -t.x))
        if nn.dot(p - CEN) < 0:
            nn = -nn
        out.append((p, t, nn))
    return out


SFR = strap_frames(_sp)
_neutral = [p + nn * (ST_ / 2) for p, t, nn in SFR]
SD = [0.0]
for a_, b_ in zip(_neutral, _neutral[1:]):
    SD.append(SD[-1] + (b_ - a_).length)
NOTES['strap'] = {'neutral_axis_mm': round(SD[-1], 2), 'inner_face_mm': round(sum((b_ - a_).length for a_, b_ in zip(_sp, _sp[1:])), 2), 'stations': len(_sp)}
assert abs(SD[-1] - SL) < 1.0, 'the strap path develops to %.2f, the interface says %.2f' % (SD[-1], SL)
SDK = SL / SD[-1]                    # stations are spread over exactly the interface's developed length
# the two bends: turning-weighted centres along the developed length
_turn = [0.0] + [math.degrees(SFR[i][1].angle(SFR[i + 1][1])) for i in range(len(SFR) - 1)]
_half = next(i for i, d in enumerate(SD) if d > SD[-1] * 0.58)
BEND = []
for rng in (range(0, _half), range(_half, len(SD))):
    w = sum(_turn[i] for i in rng)
    BEND.append((sum(_turn[i] * (SD[i] + SD[i - 1]) / 2 for i in rng if i > 0) / max(w, 1e-9) * SDK, w))
NOTES['strap']['bends'] = [{'at_mm': round(a_, 2), 'deg': round(w, 1)} for a_, w in BEND]
TOE_START = next(i for i in range(_half, len(SD)) if _turn[i] > 1.0) - 1


def strap_mesh(name, frames, stations, origin_m, mat, chamfer=0.25):
    """The strap as a sweep in G (metres, x = U, y = S, z = P Y). Returns (object, rest coordinates of its vertices
    in the uncut sheet whose layout origin is origin_m, paint up)."""
    c = chamfer
    h = SW_ / 2
    sec = [(0.0, -h + c), (0.0, h - c), (c, h), (ST_ - c, h), (ST_, h - c), (ST_, -h + c), (ST_ - c, -h), (c, -h)]       # (t out of the inner face, w across)
    verts, rest, faces = [], [], []
    ns = len(sec)
    for (p, t, nn), d in zip(frames, stations):
        for (tt, w) in sec:
            q = p + nn * tt
            verts.append(Vector((q.x * MM, q.y * MM, w * MM)))
            rest.append(origin_m + V(d, h + w, tt))
    for i in range(len(frames) - 1):
        for k in range(ns):
            k2 = (k + 1) % ns
            faces.append((i * ns + k, i * ns + k2, (i + 1) * ns + k2, (i + 1) * ns + k))
    faces.append(tuple(range(ns))[::-1])
    faces.append(tuple(range((len(frames) - 1) * ns, len(frames) * ns)))
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    o = bpy.data.objects.new(name, me); G.link(o)
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    if mat:
        me.materials.append(mat)
    return o, rest


PLATE_MESH = {}


def build_sheet(k):
    cfg = SHEET[k]
    O = cfg['O']; up = cfg['paint_up']
    pre = 'sheet_' + k
    rect = (O.x, O.y, O.x + SWD * MM, O.y + SHT * MM)
    holes_m = [(O.x + bx * MM, O.y + by * MM, BOLT_R * MM) for bx, by in BOLTS]
    W = lambda x, y, z=0.0: O + V(x, y, z)
    zp = T if up else 0.0                                         # the painted face's height
    if k == 'a':
        st = (os.path.join(HERE, 'src', 'stencil_7c.png'), W(38.0, 33.0, zp), X, Y, 0.046, 0.023)
    else:           # read from below: the text runs along -X there
        st = (os.path.join(HERE, 'src', 'stencil_04b.png'), W(70.0, 58.0, zp), -X, Y, 0.050, 0.025)
    punch = [W(X0 + s, Y0 + u, T) for (u, s, r) in HOLES.values()] if up else None
    paint = M['al_paint_' + k] = mtl.alloy_paint('al_paint_' + k, rect, holes_m, st, lo=0.522 if k == 'a' else 0.528)
    bare = M['al_bare_' + k] = mtl.alloy_bare('al_bare_' + k, rect, holes_m)
    plugpaint = paint
    if punch:
        plugpaint = M['al_plug_' + k] = mtl.alloy_paint('al_plug_' + k, rect, holes_m, st, lo=0.522, punch=punch)
    top, bot = (paint, bare) if up else (bare, paint)
    outline = [(0, 0), (SL + 0.6, 0), (SWD, 1.2 + (SWD - SL - 0.6))] + cfg['tear'] + [(0, SHT)]
    made = {}

    def classify(c, n):
        if n.z > 0.9:
            return 'top'
        if n.z < -0.9:
            return 'bot'
        p = ((c.x - O.x) / MM, (c.y - O.y) / MM)
        if mtl.dist_to_poly(p, outline) < 0.03 or any(math.hypot(p[0] - bx, p[1] - by) < BOLT_R + 0.05 for bx, by in BOLTS):
            return 'old'
        return 'cut'
    FM = {'top': top, 'bot': bot, 'old': M['al_old'], 'cut': M['al_cut']}

    # the whole sheet, then its pieces as the snips leave them
    whole = mtl.slab('_sheet', outline, 0, T, O)
    G.boolean(whole, [G.cyl('_bolt', W(bx, by, -1), W(bx, by, T + 1), BOLT_R * MM, 14) for bx, by in BOLTS])
    regions = {'rem': [(-1, SW_), (SL, SW_), (SL, -1), (SWD + 1, -1), (SWD + 1, Y_MID), (-1, Y_MID)],
               'offcut_1': [(-1, Y_MID), (X_SPLIT, Y_MID), (X_SPLIT, SHT + 1), (-1, SHT + 1)],
               'offcut_2': [(X_SPLIT, Y_MID), (SWD + 1, Y_MID), (SWD + 1, SHT + 1), (X_SPLIT, SHT + 1)],
               'strap': [(-1, -1), (SL, -1), (SL, SW_), (-1, SW_)]}
    for rk, poly in regions.items():
        o = G.duplicate(whole, '_' + rk)
        G.boolean(o, [mtl.slab('_reg', poly, -1, T + 1, O)], op='INTERSECT')
        if rk != 'strap':
            G.boolean(o, [mtl.slab('_plate', MOUT, -1, T + 1, O)])
        mtl.tri_safe(o)
        mtl.paint_faces(o, classify, FM)
        G.shade(o, 40)
        made[rk] = o
    bpy.data.objects.remove(whole, do_unlink=True)

    # the plate, in its own node frame (SEAM.md section 9)
    sx = -1.0 if k == 'a' else 1.0                                  # left plate: +X = -U
    loc = [(sx * u * MM, s * MM) for u, s in FIL]
    plate = G.prism('_pl', loc, T * MM, (0, 0, 0), X, Y, Z, None, w0=0.0)
    G.boolean(plate, [G.cyl('_h', Vector((sx * u * MM, s * MM, -1 * MM)), Vector((sx * u * MM, s * MM, (T + 1) * MM)), r * MM, 16) for (u, s, r) in HOLES.values()])
    G.bevel(plate, 0.3 * MM, 1, 60, clamp=False)       # rims only (the plan outline keeps every eased corner). Clamped, the bevel shrank to nothing round the whole outline: one edge between two eased corners is 0.3 mm long
    mtl.tri_safe(plate)
    if k == 'a':
        PLATE_MESH['left'] = plate.data.copy()
    else:           # the right plate is the left one mirrored, vertex for vertex (its own boolean left a sliver hole)
        old = plate.data
        plate.data = PLATE_MESH['left'].copy()
        bpy.data.meshes.remove(old)
        G.mirror(plate, 0, 0.0)
    if up:
        plate.matrix_world = Matrix.Translation(W(X0, Y0, 0)) @ Matrix(((0, 1, 0), (-1, 0, 0), (0, 0, 1))).to_4x4()
    else:
        plate.matrix_world = Matrix.Translation(W(X0, Y0, T)) @ Matrix(((0, 1, 0), (1, 0, 0), (0, 0, -1))).to_4x4()
    bpy.context.view_layer.update()
    mtl.paint_faces(plate, lambda c, n: 'top' if n.z > 0.9 else ('bot' if n.z < -0.9 else 'side'), {'top': top, 'bot': bot, 'side': M['al_filed']})
    G.shade(plate, 40)
    made['plate'] = plate

    # the plate's flat faces end at these edges (after the bevel): the margin and the plugs are built on them
    mw = plate.matrix_world

    def edges_at(world_top):
        zl, upl = (T * MM, True) if (world_top == up) else (0.0, False)
        return [(mw @ a_, mw @ b_) for a_, b_ in mtl.plane_edges(plate, zl, upl)]

    def ring(z):
        pts = [W(x, y, z) for x, y in MOUT]
        return [(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]
    centres = [W(X0 + s, Y0 + u, 0) for (u, s, r) in HOLES.values()]
    radii = [r for (u, s, r) in HOLES.values()]

    def hole_of(e):
        m_ = (e[0] + e[1]) / 2
        for i, (c, r) in enumerate(zip(centres, radii)):
            if (m_ - c).to_2d().length < (r + 0.8) * MM:
                return i
        return -1
    Et, Eb = edges_at(True), edges_at(False)
    mg = [mtl.fill_edges('_mt', ring(T) + [e for e in Et if hole_of(e) < 0], top),
          mtl.fill_edges('_mb', ring(0) + [e for e in Eb if hole_of(e) < 0], bot, flip=True),
          mtl.wall('_mw', [(O.x + x * MM, O.y + y * MM) for x, y in MOUT], O.z, O.z + T * MM, M['al_cut'])]
    margin = G.join('_margin', mg)
    G.clean(margin, 1e-7)
    G.shade(margin, 40)
    made['margin'] = margin
    made['plugs'] = []
    for i in range(4):
        et, eb = [e for e in Et if hole_of(e) == i], [e for e in Eb if hole_of(e) == i]
        assert len(et) >= 8 and len(eb) >= 8, 'plate %s: hole %d has no rim on a face (%d, %d edges)' % (k, i, len(et), len(eb))
        pg = G.join('_plug', [mtl.fill_edges('_pt', et, plugpaint if up else top), mtl.fill_edges('_pb', eb, bot, flip=True)])
        G.shade(pg, 40)
        made['plugs'].append(pg)

    # ------------------------------------------------------------------ contract
    sheet = made['rem']
    CT.part(sheet, FAM, pre, 'Scrap Alloy sheet %s (what is left after cutting)' % k.upper(), kind='part', material='alloy', mass='light', loose=True,
            item='scrap_alloy', steps=['s0.salvage', 's3.scribe', 's3.cut', 's4.charge'], origin=W(SWD / 2, SHT / 2, 0),
            note='paint side %s; its children lie in it as the uncut sheet' % ('up' if up else 'down'))
    CT.part(plate, FAM, pre + '_plate', '%s side plate, cut and finished' % ('Left' if k == 'a' else 'Right'), parent=pre, material='alloy', mass='light', loose=True,
            steps=['s3.cut', 's3.file', 's3.punch', 's3.drill', 's5.plates', 's5.torque', 's5.seam'],
            note='node frame = grip/interface.json plate.node_frames (%s): seat it at grip.core/seat_plate_%s' % (('left', 'l') if k == 'a' else ('right', 'r')))
    CT.grab(plate, W(X0 + 4, Y0, T / 2))
    for i, hk in enumerate('ABCD'):
        u, s, r = HOLES[hk]
        CT.mark(plate, 'punch_%d' % (i + 1), W(X0 + s, Y0 + u, T), Z)
        pg = made['plugs'][i]
        CT.part(pg, FAM, pre + '_plug_%d' % (i + 1), 'Metal in hole %s' % hk, parent=pre + '_plate', kind='consumable', material='alloy', mass='tiny', loose=True,
                steps=['s3.punch', 's3.drill'], origin=W(X0 + s, Y0 + u, 0), note='hidden when drilled')
        if up:
            CT.wipe(pg, 'punch', zone=None, label='Centre-punch dimple (clean set = punched, as-found set = unmarked)')
    CT.part(margin, FAM, pre + '_margin', 'Sliver left outside the line', parent=pre + '_plate', kind='consumable', material='alloy', mass='tiny', loose=True,
            steps=['s3.cut', 's3.file'], origin=W(X0, Y0, 0), note='hidden when filed; open on the inside (the plate fills it)')
    for i in (1, 2):
        oc = made['offcut_%d' % i]
        bb = [oc.matrix_world @ Vector(c) for c in oc.bound_box]
        cen = sum(bb, Vector()) / 8
        CT.part(oc, FAM, pre + '_offcut_%d' % i, 'Alloy offcut %d' % i, parent=pre, material='alloy', mass='tiny', loose=True, steps=['s3.cut', 's4.charge'],
                origin=Vector((cen.x, cen.y, O.z)))
    # the strap: node frame G, laid so that its back leg is the strip's first 36 mm
    u0, s0 = _sp[0].x, _sp[0].y
    if up:
        R = Matrix(((0, -1, 0), (0, 0, 1), (-1, 0, 0)))             # columns: G X -> -z, G Y -> -x, G Z -> +y
        anchor = W(0, SW_ / 2, 0)
    else:
        R = Matrix(((0, -1, 0), (0, 0, -1), (1, 0, 0)))             # paint down: G X -> +z, G Y -> -x, G Z -> -y
        anchor = W(0, SW_ / 2, T)
    MS = Matrix.Translation(anchor - R @ V(u0, s0, 0)) @ R.to_4x4()
    strap = made['strap']
    G.set_frame(strap, MS)
    CT.part(strap, FAM, pre + '_strap', 'Strap strip, flat' + ('' if up else ' (the spare)'), parent=pre, material='alloy', mass='light', loose=True,
            steps=['s3.cut', 's3.strap'], note='node frame = the grip frame G (interface strap.node_frame): the strip coincides with the bent strap along its back leg')
    CT.grab(strap, W(SL / 2, SW_ / 2, T / 2))
    for i, (at, deg) in enumerate(BEND):
        CT.mark(strap, 'bend_%d' % (i + 1), W(at, SW_ / 2, zp), Z if up else -Z)
    out = {'sheet': sheet, 'plate': plate, 'margin': margin, 'strap': strap, 'MS': MS, 'W': W, 'paint': paint, 'bare': bare, 'O': O,
           'rest_objs': [sheet, plate, margin, strap, made['offcut_1'], made['offcut_2']] + made['plugs']}
    return out


SA = build_sheet('a')
SB = build_sheet('b')

# the bent strap (sheet A's strip after the vise), and the strip after the first bend only
OA = SA['O']
flat_st = [d * SDK for d in SD]
bent, rest = strap_mesh('_bent', SFR, flat_st, OA, None)
# after the first (heel) bend: the base and the toe lip still in one line
_tk = (SFR[TOE_START][0] - SFR[TOE_START - 1][0]).normalized()
_nk = Vector((_tk.y, -_tk.x))
if _nk.dot(SFR[TOE_START][2]) < 0:
    _nk = -_nk
f1 = list(SFR[:TOE_START]) + [(SFR[TOE_START][0], _tk, _nk)]
for i in range(TOE_START + 1, len(SFR)):
    f1.append((f1[-1][0] + _tk * (SFR[i][0] - SFR[i - 1][0]).length, _tk, _nk))
bent1, rest1 = strap_mesh('_bent1', f1, flat_st, OA, None)
for o, rr, pid, label, note in ((bent, rest, 'strap_bent', 'Reinforcement strap, bent', 'node frame = the grip frame G: seat it at grip.core/seat_strap'),
                                (bent1, rest1, 'strap_bent_1', 'Strap after the first bend', 'extra state, not in PARTS.md: the heel bend done, the toe lip still flat')):
    o.matrix_world = SA['MS']
    bpy.context.view_layer.update()
    mtl.set_rest(o, rr)
    me = o.data
    me.materials.clear()
    for m in (SA['bare'], SA['paint'], M['al_filed'], M['al_cut'], M['al_old']):
        me.materials.append(m)
    frs = SFR if o is bent else f1
    for p in me.polygons:        # in G: the painted face looks away from the grip; one long edge and one end are the sheet's own
        c = Vector((p.center.x / MM, p.center.y / MM)); n2 = Vector((p.normal.x, p.normal.y))
        if abs(p.normal.z) > 0.9:
            p.material_index = 3 if p.normal.z > 0 else 4
        elif abs(p.normal.z) > 0.3:
            p.material_index = 2
        elif len(p.vertices) == 8:
            p.material_index = 4 if (c - frs[0][0]).length < (c - frs[-1][0]).length else 3
        else:
            fr = min(frs, key=lambda f_: (f_[0] + f_[2] * (ST_ / 2) - c).length)
            p.material_index = 1 if n2.dot(fr[2]) > 0 else 0
    G.shade(o, 40)
    CT.part(o, FAM, pid, label, parent='sheet_a', material='alloy', mass='light', loose=True, steps=['s3.strap', 's5.strap'], note=note)
    vs = [o.matrix_world @ v.co for v in o.data.vertices]
    CT.grab(o, sum(vs, Vector()) / len(vs))

# the scribed line: a bright 0.3 mm strip on the paint of sheet A, along the plate's outline
W = SA['W']
si, so = PG.offset_poly(PP, -0.15), PG.offset_poly(PP, 0.15)
n = len(PP)
verts = [W(x, y, T + 0.02) for x, y in si] + [W(x, y, T + 0.02) for x, y in so]
faces = [(i, n + i, n + (i + 1) % n, (i + 1) % n) for i in range(n)]
scribe = G.mesh_obj('_scribe', verts, faces, M['al_scribe'], recalc=False)
if scribe.data.polygons[0].normal.z < 0:
    bm = bmesh.new(); bm.from_mesh(scribe.data); bmesh.ops.reverse_faces(bm, faces=bm.faces); bm.to_mesh(scribe.data); bm.free()
CT.part(scribe, FAM, 'sheet_a_scribe', 'Scribed line', parent='sheet_a', kind='consumable', material='alloy', mass='tiny', loose=True, steps=['s3.scribe', 's3.file'],
        origin=W(SWD / 2, SHT / 2, 0), note='reveal it along path scribe; it lies 0.02 mm above the paint')


def ring_path(corners, extra):
    """The corners of a closed outline plus the midpoints of its longest edges, closed (first point repeated)."""
    n = len(corners)
    lens = sorted(range(n), key=lambda i: -(Vector(corners[(i + 1) % n]) - Vector(corners[i])).length)[:extra]
    out = []
    for i in range(n):
        out.append(corners[i])
        if i in lens:
            out.append(tuple((Vector(corners[i]) + Vector(corners[(i + 1) % n])) / 2))
    return out + [corners[0]]


CT.path(SA['sheet'], 'scribe', [W(x, y, T) for x, y in ring_path(CORNERS, 17)], [Z] * 40)
CT.path(SA['sheet'], 'cut', [W(x, y, T) for x, y in ring_path(PG.offset_poly(CORNERS, MARGIN), 17)], [Z] * 40)
CT.path(SA['sheet'], 'cut_strap', [W(SL * i / 7.0, SW_, T) for i in range(8)] + [W(SL, SW_ / 2, T), W(SL, 0, T)], [Z] * 10)

# swarf: five drill curls
import random
rnd = random.Random(7)
swarf = []
for i in range(5):
    r0 = rnd.uniform(1.3, 1.9); turns = rnd.uniform(1.6, 2.6); ang = rnd.uniform(0, math.pi)
    c = Vector((0.500 + 0.012 * (i % 3) + rnd.uniform(-0.002, 0.002), -0.008 + 0.014 * (i // 3) + rnd.uniform(-0.003, 0.003), 0.0))
    ax = Vector((math.cos(ang), math.sin(ang), rnd.uniform(-0.12, 0.12))).normalized()
    start = c + Vector((0, 0, r0 * MM)) - ax * (turns * 0.7 * MM)
    pts = G.helix(start, ax, Z, r0 * MM, 1.4 * MM, turns, per_turn=9, phase=rnd.uniform(0, 6.28), r1=r0 * 0.62 * MM)
    nrm = []
    for p in pts:
        a_ = start + ax * (p - start).dot(ax)
        nrm.append((p - a_).normalized())
    o = mtl.ribbon('_swarf', pts, nrm, rnd.uniform(0.9, 1.3) * MM, M['al_swarf'])
    zmin = min((o.matrix_world @ v.co).z for v in o.data.vertices)
    o.data.transform(Matrix.Translation((0, 0, -zmin)))
    G.shade(o, 60)
    CT.part(o, FAM, 'swarf_%d' % (i + 1), 'Drill swarf %d' % (i + 1), kind='consumable', material='alloy', mass='tiny', loose=True, steps=['s3.drill'], origin=c)
    swarf.append(o)

# ====================================================================== leads, resistor, sleeves, loop (frame D)
UNIT = ifc['unit']; LOOP = ifc['loop']
servo_notes = json.load(open(os.path.join(HERE, '..', 'servo', 'export', 'stats.json')))['notes']
AS_CUT = servo_notes['lead_length_as_cut_mm']                     # the servo's leads as snipped at their bands
GD = servo_notes['gimbal']
BENCH_Z = -GD['depth']                                            # the cradle stands on its bottom face
LEAD_D, CORE_D = LOOP['lead']['d_sleeve'], LOOP['lead']['d_core']
STRIP, TRIM = 8.0, 27.0                                           # stripped length; trimmed length from the tab (19 insulated + 8 bare)
BAND = (4.4, 2.2)                                                 # the marker band, back from the as-cut end (servo/build.py)
NA, NB = GD['notch_deg']


def pol(r, deg, z):
    a = math.radians(deg)
    return (r * math.cos(a), r * math.sin(a), z)


def lead_curve(ctrl, step=0.5):
    P = G.chaikin([V(*c) for c in ctrl], 3, False)
    n = max(8, int(mtl.arc_lengths(P)[-1] / (step * MM)))
    return G.resample(P, n + 1)


def piece(P, d0, d1, tol=0.02):
    return rdp(sv.cut_path(P, d0 * MM, d1 * MM), tol * MM)


_d = Vector((-0.25, 0.80, -0.55)).normalized()
_q3 = Vector((15.6, 20.0, -5.8))
A_CTRL = [pol(GD['body_r'] - 1.7, NA, -1.7), pol(GD['flange_r'], NA, -1.7), pol(18.5, NA, -1.8), (16.0, 16.6, -3.4)] + \
         [tuple(_q3 + _d * (3.5 * i)) for i in range(5)] + \
         [(9.8, 37.0, -17.4), (7.2, 42.0, -18.85), (5.6, 47.0, BENCH_Z + 1.0), (5.0, 53.0, BENCH_Z + 1.0), (5.0, 85.0, BENCH_Z + 1.0)]       # lying on its marker band
S_CTRL = [(0, 13.0, -1.0), (0, 15.0, -1.0), (0, 18.5, -1.05), (0.5, 22.5, -3.0), (1.0, 27.5, -7.5), (1.0, 32.5, -12.5), (0.6, 37.5, -16.8),
          (0.2, 42.0, -18.9), (0, 47.0, BENCH_Z + 0.8), (0, 70.0, BENCH_Z + 0.8)]
CURVE = {'a': lead_curve(A_CTRL), 'b': lead_curve([(-x, y, z) for x, y, z in A_CTRL]), 's': lead_curve(S_CTRL)}
# the stripped length must be straight, or the slug cannot slide off
for k in 'ab':
    sl = sv.cut_path(CURVE[k], (TRIM - STRIP) * MM, (TRIM + 0.5) * MM)
    dev = max(((p - sl[0]).cross((sl[-1] - sl[0]).normalized())).length for p in sl)
    assert dev < 0.02 * MM, 'lead %s is not straight where it is stripped (%.3f mm)' % (k, dev / MM)
NOTES['leads'] = {'as_cut_mm': AS_CUT, 'trim_at_mm': TRIM, 'strip_mm': STRIP, 'bench_z_mm': BENCH_Z}
RL = LEAD_D / 2 * MM
leads = {}
for k in 'ab':
    P = CURVE[k]
    tab = P[0]
    ins = G.tube_path('_ins', piece(P, 0, TRIM - STRIP, 0.03), RL, 8, M['wire_red'])
    blob = AP.solder_blob('_blob', 1.7 * MM, 0.7 * MM, M['solder'], segs=8, at=tab + Z * (0.45 * MM), axis=Z)
    lead = G.join('_lead', [ins, blob])
    G.shade(lead, 50)
    CT.part(lead, FAM, 'lead_' + k, 'Coil lead %s on the bench' % k.upper(), parent='servo.gimbal_cradle', material='rubber', mass='tiny', loose=True, flex=True,
            steps=['s3.trim', 's3.strip', 's3.tin', 's3.loop'], note='in the cradle frame D, identity transform; replaces servo.lead_coil_%s once the unit is out' % k)
    pt, tg = mtl.point_at(P, TRIM * MM)
    CT.mark(lead, 'trim', pt, Z)
    CT.grab(lead, mtl.point_at(P, 12 * MM)[0])
    # strands under the slug
    sp = piece(P, TRIM - STRIP - 0.2, TRIM)
    strands = [mtl.var_tube('_st', sp, CORE_D / 2 * MM, 6, M['strand'])]
    e, t = mtl.point_at(P, TRIM * MM)
    side = t.cross(Z).normalized(); upv = t.cross(side)
    for (a_, b_) in ((0.8, 0.4), (-0.6, 0.7), (0.1, -0.9)):          # the ends of the strands part a little
        strands.append(mtl.var_tube('_tip', [e - t * (0.9 * MM), e + t * (0.25 * MM) + (side * a_ + upv * b_) * (0.22 * MM)], 0.16 * MM, 4, M['strand']))
    stn = G.join('_strands', strands)
    G.shade(stn, 60)
    CT.part(stn, FAM, 'lead_%s_strands' % k, 'Bare strands of lead %s' % k.upper(), parent='lead_' + k, material='copper', mass='tiny', loose=True, flex=True,
            steps=['s3.strip', 's3.tin', 's3.loop'])
    mid, _t = mtl.point_at(P, (TRIM - STRIP / 2) * MM)
    CT.zone(stn, 'tin', mid, (STRIP / 2 * MM + 0.0005, 0.0012, 0.0012), rot=Matrix((t, side, upv)).transposed())
    CT.wipe(stn, 'tin', zone='tin', label='Tinning (clean set = tinned bright, as-found set = bare copper)')
    # the slug of insulation: slides off along the lead
    slug = mtl.hollow_tube('_slug', piece(P, TRIM - STRIP, TRIM), RL, CORE_D / 2 * MM + 0.05 * MM, 8, M['wire_red'])
    G.shade(slug, 50)
    CT.part(slug, FAM, 'lead_%s_slug' % k, 'Stripped insulation of lead %s' % k.upper(), parent='lead_' + k, kind='consumable', material='rubber', mass='tiny',
            symmetry=0, steps=['s3.strip'])
    CT.clear(slug, offset=t * (14 * MM))
    # the offcut beyond the trim mark, with the marker band and the copper showing at both cut ends
    L = AS_CUT[k]
    oc = [G.tube_path('_oc', piece(P, TRIM, L, 0.04), RL, 7, M['wire_red']),
          G.tube_path('_band', piece(P, L - BAND[0], L - BAND[1]), RL + 0.16 * MM, 8, M['band_pale'])]
    for dd, sgn in ((TRIM, -1), (L, 1)):
        q, tq = mtl.point_at(P, dd * MM)
        oc.append(G.cyl('_cu', q - tq * sgn * (0.02 * MM), q + tq * sgn * (0.07 * MM), CORE_D / 2 * MM, 6, M['copper']))
    off = G.join('_off', oc)
    G.shade(off, 50)
    CT.part(off, FAM, 'lead_%s_offcut' % k, 'Trimmed end of lead %s' % k.upper(), parent='lead_' + k, kind='consumable', material='rubber', mass='tiny', loose=True,
            flex=True, steps=['s3.trim'])
    CT.grab(off, mtl.point_at(P, (TRIM + L) / 2 * MM)[0])
    # the heat-shrink sleeve, slid back on the lead before the joint is made (it hangs on the lead)
    sl = [p - Z * (0.75 * MM) for p in piece(P, 8.5, 16.5, 0.05)]
    slv = mtl.hollow_tube('_slv', sl, 1.8 * MM, 1.55 * MM, 8, M['shrink'])
    G.shade(slv, 50)
    CT.part(slv, FAM, 'sleeve_' + k, 'Heat-shrink sleeve %s (not yet shrunk)' % k.upper(), parent='lead_' + k, material='plastic', mass='tiny', loose=True,
            steps=['s3.loop'])
    CT.grab(slv, mtl.point_at(P, 12.5 * MM)[0])
    leads[k] = {'lead': lead, 'strands': stn, 'slug': slug, 'offcut': off, 'sleeve': slv, 'len': mtl.arc_lengths(P)[-1] / MM}
# the sense lead, whole: it is cut off flush
P = CURVE['s']
L = AS_CUT['s']
sp = [G.tube_path('_sn', piece(P, 0, L, 0.04), 0.6 * MM, 6, M['wire_bone']), G.tube_path('_sband', piece(P, L - BAND[0], L - BAND[1], 0.04), 0.76 * MM, 6, M['band_yellow'])]
q, tq = mtl.point_at(P, L * MM)
sp.append(G.cyl('_cu', q - tq * (0.02 * MM), q + tq * (0.07 * MM), 0.3 * MM, 6, M['copper']))
sense = G.join('_sense', sp)
G.shade(sense, 50)
CT.part(sense, FAM, 'lead_sense', 'Sense lead on the bench', parent='servo.gimbal_cradle', kind='consumable', material='rubber', mass='tiny', loose=True, flex=True,
        steps=['s3.trim'], note='in the cradle frame D; replaces servo.lead_sense once the unit is out; cut off flush at mark flush')
CT.mark(sense, 'flush', V(*pol(GD['flange_r'], 90.0, -1.0)), Y)
CT.grab(sense, mtl.point_at(P, 18 * MM)[0])


def resistor(name, centre, axis, leg_a, leg_b, legs=True, segs=10):
    """The trim resistor (interface loop.resistor): body with four bands on `axis` about `centre` (metres), leg stubs."""
    hl = LOOP['resistor']['body_len'] / 2; rr = LOOP['resistor']['body_d'] / 2
    ax = Vector(axis).normalized()
    ref = Z if abs(ax.z) < 0.9 else X
    cuts = [-hl, -hl + 0.42, -2.25, -1.55, -1.1, -0.4, 0.05, 0.75, 1.6, 2.3, hl - 0.42, hl]
    prof = [(cuts[0], 0.0), (cuts[0], rr * 0.7)] + [(s, rr) for s in cuts[1:-1]] + [(cuts[-1], rr * 0.7), (cuts[-1], 0.0)]
    body = G.lathe(name, [([(s * MM, r * MM) for s, r in prof], False)], segs, Vector(centre), ax, ref, M['res_body'])
    for (s0, s1, mat) in ((-2.25, -1.55, 'res_dark'), (-1.1, -0.4, 'res_red'), (0.05, 0.75, 'res_red'), (1.6, 2.3, 'res_gold')):
        remat(body, M[mat], lambda c, n, s0=s0, s1=s1: s0 * MM < (c - Vector(centre)).dot(ax) < s1 * MM and abs(n.dot(ax)) < 0.5)
    out = [body]
    if legs:
        rl = LOOP['resistor']['leg_d'] / 2 * MM
        for sgn, pts in ((-1, leg_a), (1, leg_b)):
            out.append(mtl.var_tube(name + '_leg', [Vector(centre) + ax * (sgn * (hl - 0.1) * MM)] + [Vector(p) for p in pts], rl, 6, M['res_leg']))
    o = G.join(name, out)
    G.shade(o, 45)
    return o


# as snipped from the board, lying on the bench: short bent legs
RC = Vector((0.560, 0.0, 0.0012))
res = resistor('_res', RC, X, [RC - X * 0.0048 - Z * 0.0002, RC - X * 0.0058 - Z * 0.0009], [RC + X * 0.0050 + Y * 0.0002, RC + X * 0.0060 - Z * 0.0009 + Y * 0.0006])
CT.part(res, FAM, 'resistor', 'Trim resistor, snipped from the board', material='ceramic', mass='tiny', loose=True, steps=['s2.board', 's3.tin', 's3.loop'],
        origin=Vector((RC.x, RC.y, 0.0)), note='the same resistor as servo.trim_resistor once it is off the board')
CT.zone(res, 'tin', RC, (0.0068, 0.0016, 0.0016))
CT.wipe(res, 'tin', zone='tin', label='Tinning on the legs (clean set = tinned, as-found set = dull); the body is the same in both sets')

# the damper loop on the interface's line (D, z = -1.7), and the same loop as it stands off the unit once soldered
LZ = LOOP['z']
_lp = [tuple(p) for p in LOOP['path_xy']]
LCTRL = [pol(GD['body_r'] - 1.7, NA, LZ)] + [(x, y, LZ) for x, y in _lp[1:-1]] + [pol(GD['body_r'] - 1.7, NB, LZ)]
LC = G.resample(G.chaikin([V(*c) for c in LCTRL], 2, False), 240)
LLEN = mtl.arc_lengths(LC)[-1] / MM
NOTES['loop'] = {'centre_line_mm': round(LLEN, 2), 'interface_between_notches_mm': LOOP['length_between_notches'],
                 'mid_point_mm': [round(c / MM, 3) for c in mtl.point_at(LC, LLEN / 2 * MM)[0]]}
SLV = LOOP['shrink_sleeves']; RSV = SLV['d'] / 2
HALF = LLEN / 2
Q_IN, Q_OUT = abs(SLV['centres_xy'][0][0]) - SLV['len'] / 2, abs(SLV['centres_xy'][0][0]) + SLV['len'] / 2            # 2.5 .. 9.5 from the middle
SPROF = [(Q_IN, RSV), (Q_IN + 0.8, RSV), (Q_IN + 1.25, 1.12), (Q_IN + 1.9, 0.95), (Q_IN + 2.7, 1.12), (Q_IN + 4.1, 1.18), (Q_IN + 5.3, 1.04), (Q_IN + 6.0, 0.98),
         (Q_OUT - 0.55, 1.07), (Q_OUT, 1.07)]
HINGE_Y, DROOP = 10.4, math.radians(22.0)


def stand_off(p):
    """Where a point of the tucked loop is once the loop stands free of the unit: everything past the flange rim
    hangs 22 degrees down (a gradual bend over the first 4 mm)."""
    p = Vector(p)
    y = p.y / MM
    if y <= HINGE_Y - 0.6:
        return p
    f = min(1.0, max(0.0, (y - (HINGE_Y - 0.6)) / 4.2)); f = f * f * (3 - 2 * f)
    a = -DROOP * f
    dy, dz = (y - HINGE_Y) * MM, p.z - LZ * MM
    return Vector((p.x, HINGE_Y * MM + dy * math.cos(a) - dz * math.sin(a), LZ * MM + dy * math.sin(a) + dz * math.cos(a)))


STAND = Matrix.Translation((0, HINGE_Y * MM, LZ * MM)) @ Matrix.Rotation(-DROOP, 4, 'X') @ Matrix.Translation((0, -HINGE_Y * MM, -LZ * MM))


def loop_parts(tag, tf, segs=8):
    """(lead a, lead b, sleeve a, sleeve b, resistor) on the loop's line, each point passed through tf."""
    out = {}
    for k, sgn in (('a', 1), ('b', -1)):
        d0, d1 = (0.0, HALF - Q_OUT + 0.5) if k == 'a' else (HALF + Q_OUT - 0.5, LLEN)
        pts = rdp([tf(p) for p in sv.cut_path(LC, d0 * MM, d1 * MM)], 0.04 * MM)
        tab = pts[0] if k == 'a' else pts[-1]
        ld = G.join('_ll', [G.tube_path('_ll', pts, RL, segs, M['wire_red']),
                            AP.solder_blob('_blob', 1.7 * MM, 0.7 * MM, M['solder'], segs=8, at=tab + Z * (0.45 * MM), axis=Z)])
        G.shade(ld, 50)
        out['lead_' + k] = ld
        qs = [q for q, r in SPROF]
        sp_ = [tf(mtl.point_at(LC, (HALF - q if k == 'a' else HALF + q) * MM)[0]) for q in qs]
        sv_ = mtl.var_tube('_ls', sp_, [r * MM for q, r in SPROF], segs, M['shrink'])
        G.shade(sv_, 50)
        out['sleeve_' + k] = sv_
    c, t = mtl.point_at(LC, HALF * MM)
    r_ = resistor('_lr', c, -t, [], [], legs=False, segs=segs)
    if tf is not None and tag == 'bench':
        G.transform_obj(r_, STAND)
    out['resistor'] = r_
    return out


LB = loop_parts('bench', stand_off)
for key, label in (('lead_a', 'Loop: coil lead A'), ('lead_b', 'Loop: coil lead B'), ('resistor', 'Loop: trim resistor'), ('sleeve_a', 'Loop: shrunk sleeve A'),
                   ('sleeve_b', 'Loop: shrunk sleeve B')):
    o = LB[key]
    CT.part(o, FAM, 'loop_' + key, label + ' (as soldered on the bench)', parent='servo.gimbal_cradle', material='rubber' if 'lead' in key else ('ceramic' if key == 'resistor' else 'plastic'),
            mass='tiny', loose=True, flex=True, steps=['s3.loop', 's3.test', 's5.loop'], note='in the cradle frame D, identity transform')
mid_b = stand_off(mtl.point_at(LC, HALF * MM)[0])
for kk, sgn in (('a', -1), ('b', 1)):          # where the tester's probes go: the resistor's two ends
    q = stand_off(mtl.point_at(LC, (HALF + sgn * (LOOP['resistor']['body_len'] / 2 + 0.1)) * MM)[0])
    CT.mark(LB['resistor'], 'probe_' + kk, q + Z * (1.3 * MM), Z)
CT.grab(LB['resistor'], mid_b)
LT = loop_parts('tucked', lambda p: Vector(p), segs=6)
tucked = G.join('_tucked', [LT[k] for k in ('lead_a', 'lead_b', 'sleeve_a', 'sleeve_b', 'resistor')])
CT.part(tucked, FAM, 'loop_tucked', 'Damper loop, tucked in the core channel', parent='servo.gimbal_cradle', material='rubber', mass='tiny', loose=True, flex=True,
        steps=['s5.loop', 's5.damp'], note='in the cradle frame D on the interface line (z = %.1f): one node' % LZ)
CT.path(tucked, 'tuck', [V(x, y, LZ) for x, y in _lp], [Z] * len(_lp))
CT.grab(tucked, mtl.point_at(LC, HALF * MM)[0])

# ====================================================================== nanite vial
VC = Vector((0.620, 0.0, 0.0))
gl = [(0.0, 0.0), (0.0, 10.4), (0.9, 11.7), (2.2, 12.0), (44.0, 12.0), (47.6, 11.1), (50.6, 8.7), (52.2, 7.6), (58.6, 7.6), (59.5, 8.7), (60.6, 9.1), (61.6, 8.8), (62.0, 8.0),
      (62.0, 6.7), (60.4, 6.4), (52.4, 6.4), (48.4, 9.4), (44.0, 10.8), (2.6, 10.8), (1.4, 0.0)]
glass = G.lathe('_glass', [([(a * MM, b * MM) for a, b in gl], False)], 20, VC, Z, X, M['vial_glass'])
# a twist of iron wire round the neck, with its pigtail (it stays on the vial; the bail over the stopper comes off)
ring = G.tube_path('_nw', G.helix(VC + Z * (56.9 * MM), Z, X, 8.05 * MM, 0.85 * MM, 2.0, per_turn=12, phase=1.2), 0.4 * MM, 5, M['iron_wire'])
tail = []
for ph in (0.0, math.pi):
    tp = []
    for i in range(7):
        s = i / 6.0
        base = VC + Vector((0.0, 8.3 * MM + s * 5.0 * MM, (57.6 - 5.5 * s * s) * MM))
        tp.append(base + Vector((math.cos(ph + s * 9.0), 0, math.sin(ph + s * 9.0))) * (0.42 * MM))
    tail.append(G.tube_path('_tw', tp, 0.36 * MM, 4, M['iron_wire']))
vial = G.join('_vial', [glass, ring] + tail)
G.shade(vial, 40)
CT.part(vial, FAM, 'vial', 'Nanite vial', kind='part', material='glass', mass='light', loose=True, item='nanite_residue', steps=['s0.salvage', 's4.charge'], origin=VC,
        note='glass is its own unbaked material; the wire round the neck is baked. materials_vial__tip: the lip, +Z out of the mouth')
CT.tip(vial, VC + Z * (62.0 * MM), Z)
CT.mark(vial, 'level', VC + V(12.0, 0, 31.6), X)
fluid = G.lathe('_fluid', [([(a * MM, b * MM) for a, b in ((1.5, 0.0), (1.5, 10.0), (2.6, 10.7), (29.2, 10.7), (28.5, 10.0), (28.25, 7.5), (28.2, 0.0))], False)], 20, VC, Z, X, M['nanite'])
G.shade(fluid, 50)
CT.part(fluid, FAM, 'vial_fluid', 'Nanite residue in the vial', parent='vial', kind='consumable', material='glass', mass='tiny', loose=True, steps=['s4.charge'],
        origin=VC + Z * (1.5 * MM), note='origin on the inside of the bottom: lower its top to let the level fall')
st = [G.lathe('_stop', [([(a * MM, b * MM) for a, b in ((53.2, 0.0), (53.2, 5.5), (54.0, 6.2), (60.2, 6.3), (62.05, 6.3), (62.05, 8.3), (62.7, 9.0), (65.2, 9.0), (66.1, 8.2), (66.1, 0.0))], False)],
              14, VC, Z, X, M['stopper'])]
bail = [(9.75, 0, 58.4), (9.75, 0, 61.0), (9.75, 0, 64.6), (9.3, 0, 66.2), (7.6, 0, 66.75), (0, 0, 66.6), (-7.6, 0, 66.75), (-9.3, 0, 66.2), (-9.75, 0, 64.6), (-9.75, 0, 61.0), (-9.75, 0, 58.4)]
st.append(G.tube_path('_bail', rdp(G.chaikin([VC + V(*p) for p in bail], 2, False), 0.04 * MM), 0.4 * MM, 5, M['iron_wire']))
stopper = G.join('_stopper', st)
G.shade(stopper, 45)
CT.part(stopper, FAM, 'vial_stopper', 'Vial stopper and its wire bail', parent='vial', material='rubber', mass='tiny', symmetry=2, steps=['s4.charge'],
        origin=VC + Z * (62.05 * MM))
CT.clear(stopper, offset=Z * (20 * MM))
ln = G.lathe('_line', [([(31.35 * MM, 12.04 * MM), (31.85 * MM, 12.04 * MM)], False)], 22, VC, Z, X, M['etch'], arc=(math.radians(-150), math.radians(150)))
bm = bmesh.new(); bm.from_mesh(ln.data)
if sum(f.normal.dot(f.calc_center_median() - VC) for f in bm.faces) < 0:
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(ln.data)
bm.free()
CT.part(ln, FAM, 'vial_line', 'Scratched level line', parent='vial', kind='part', material='glass', mass='tiny', loose=True, fixed=True, steps=['s4.charge'],
        origin=VC + Z * (31.6 * MM))

# ====================================================================== bobbin and its copper
BC = Vector((0.690, 0.0, 0.0))
fl = []
for z0, flip in ((0.0, False), (28.8, True)):
    pr = [(0.0, 3.0), (0.0, 16.3), (0.35, 17.0), (0.95, 17.0), (1.4, 16.5), (1.2, 16.0), (1.2, 3.0)]
    pr = [((1.2 - a) if flip else a, b) for a, b in pr]
    f_ = G.lathe('_fl', [([((z0 + a) * MM, b * MM) for a, b in pr], True)], 20, BC, Z, X, M['flange'])
    G.boolean(f_, [G.box('_slot', BC + V(14.6, 0, z0 + 0.6), (6.0 * MM, 1.2 * MM, 6 * MM)),
                   G.cyl('_drv', BC + V(-10.5, 2.0, z0 - 2), BC + V(-10.5, 2.0, z0 + 3.5), 1.3 * MM, 10)])
    for kk, m_ in enumerate(f_.data.materials):
        if m_ is None:
            f_.data.materials[kk] = M['flange']
    fl.append(f_)
core = sv.annulus('_core', BC, Z, 3.0, 7.0, 1.2, 28.8, 16, M['wood'])
bobbin = G.join('_bobbin', fl + [core])
G.shade(bobbin, 40)
CT.part(bobbin, FAM, 'bobbin', 'Wire bobbin', kind='part', material='steel', mass='light', loose=True, item='copper_filament', steps=['s2.winding'], origin=BC,
        note='stands on a flange; with materials.bobbin_wire shown it is the Copper Filament')
wp = [(1.32, 7.08), (1.32, 14.9), (3.2, 15.5), (9.0, 15.75), (15.0, 15.6), (21.0, 15.8), (26.8, 15.5), (28.68, 14.9), (28.68, 7.08)]       # the turns are in the normal map
wire = G.lathe('_wire', [([(a * MM, b * MM) for a, b in wp], True)], 20, BC, Z, X, M['wound'])
G.shade(wire, 60)
CT.part(wire, FAM, 'bobbin_wire', 'Wound stator copper', parent='bobbin', kind='consumable', material='copper', mass='light', loose=True, steps=['s2.winding'],
        origin=BC + Z * (1.32 * MM), note='its own node so that it can grow as the crank turns')

# ====================================================================== flash and sprue of the pressed core (frame of grip.core)
# SEAM.md section 10: the pressed core is grip.core itself; what makes it raw is the fin along the parting line and
# the sprue stub. The parting plane is the core's middle plane, P Y = 0 (the grip family names none). The fin follows
# the core's outline in that plane, read from grip/export/grip.blend; where the tang slot opens there is no fin.
from mathutils.bvhtree import BVHTree
M['fused_raw'] = MT.make('fused_raw', (0.42, 0.425, 0.43), 1.0, 0.46, var=0.1, bumps=[('stipple', 2600, 0.3), ('noise', 420, 0.35)], bevel_r=0.0,
                         tone2=((0.33, 0.29, 0.42), 55, 0.42, 0.75, 0.55), dirt=((0.12, 0.11, 0.10), 0.8, 0.4), grime=0.3)
GBLEND = os.path.join(HERE, '..', 'grip', 'export', 'grip.blend')
FLASH = []
if os.path.exists(GBLEND):
    with bpy.data.libraries.load(GBLEND, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n == 'grip_core']
    gcore = dst.objects[0]
    bpy.context.scene.collection.objects.link(gcore)
    bpy.context.view_layer.update()
    MCORE = gcore.matrix_world.copy()
    cv = [MCORE @ v.co for v in gcore.data.vertices]
    ctree = BVHTree.FromPolygons(cv, [tuple(p.vertices) for p in gcore.data.polygons])

    def outline_at(y):
        bm = bmesh.new(); bm.from_mesh(gcore.data); bm.transform(MCORE)
        r = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, y, 0), plane_no=(0, 1, 0))
        ed = [e for e in r['geom_cut'] if isinstance(e, bmesh.types.BMEdge)]
        nb = {}
        for e in ed:
            a_, b_ = e.verts
            nb.setdefault(a_.index, []).append(b_.index); nb.setdefault(b_.index, []).append(a_.index)
        co = {v.index: Vector((v.co.x, v.co.z)) for e in ed for v in e.verts}
        bm.free()
        loops, seen = [], set()
        for st_ in nb:
            if st_ in seen:
                continue
            lp = [st_]; seen.add(st_); prev = None; cur = st_
            while True:
                nx = [q for q in nb[cur] if q != prev and (q not in seen or (q == st_ and len(lp) > 2))]
                if not nx or nx[0] == st_:
                    break
                prev, cur = cur, nx[0]
                lp.append(cur); seen.add(cur)
            loops.append([co[i] for i in lp])
        area = lambda lp: abs(sum(lp[i].x * lp[(i + 1) % len(lp)].y - lp[(i + 1) % len(lp)].x * lp[i].y for i in range(len(lp)))) / 2
        return max(loops, key=area)
    OUTL = outline_at(0.008)                    # beside the tang slot the section is whole; in the strap bed's width the outline is the same as on the middle plane
    cen2 = sum(OUTL, Vector((0, 0))) / len(OUTL)
    NF = 120
    ring_ = G.resample([Vector((p.x, 0.0, p.y)) for p in OUTL] + [Vector((OUTL[0].x, 0.0, OUTL[0].y))], NF + 1)[:-1]
    rnd2 = random.Random(11)
    nrm, hgt, onm = [], [], []
    for i, p in enumerate(ring_):
        t = (ring_[(i + 1) % NF] - ring_[i - 1]).normalized()
        n_ = Vector((t.z, 0.0, -t.x))
        if n_.dot(p - Vector((cen2.x, 0.0, cen2.y))) < 0:
            n_ = -n_
        nrm.append(n_)
        hgt.append((0.5 + 2.4 * abs(math.sin(i * 0.37 + 1.3) * math.sin(i * 0.11 + 0.4)) + rnd2.uniform(0.0, 0.9)) * (0.25 if rnd2.random() < 0.12 else 1.0))
        hit = ctree.ray_cast(p - n_ * 0.004, n_, 0.012)             # the surface on the middle plane itself (the back is rounded across Y)
        onm.append(hit[0] is not None)                               # no metal across the tang slot's mouth
        if hit[0] is not None:
            ring_[i] = hit[0].copy()
    runs, cur = [], []
    for i in range(NF):
        if onm[i] and onm[(i + 1) % NF]:
            cur.append(i)
        elif cur:
            runs.append(cur); cur = []
    if cur:
        runs.append(cur)
    total = sum(len(r_) for r_ in runs)
    pieces, acc, cur = [], 0, []
    for r_ in runs:          # two or three pieces of about equal length, never split inside a 6-segment stretch
        for j in range(0, len(r_), 6):
            cur.append(r_[j:j + 6]); acc += len(r_[j:j + 6])
            if acc >= total / 3.0 and len(pieces) < 2:
                pieces.append(cur); cur = []; acc = 0
    if cur:
        pieces.append(cur)
    sprue_i = min(range(NF), key=lambda i: (ring_[i] - Vector(PG.GP(0.0, -70.0, 0.0))).length)          # the middle of the base, where the mould fills
    for k, chunks in enumerate(pieces):
        verts, faces = [], []
        for ch in chunks:
            idx = ch + [(ch[-1] + 1) % NF]
            b0 = len(verts)
            for j, i in enumerate(idx):
                p, n_ = ring_[i], nrm[i]
                h = hgt[i] * (0.15 if j in (0, len(idx) - 1) else 1.0)
                verts += [p - n_ * (0.15 * MM) - Y * (0.25 * MM), p - n_ * (0.15 * MM) + Y * (0.25 * MM), p + n_ * (h * MM)]
            for j in range(len(idx) - 1):
                a_, b_ = b0 + 3 * j, b0 + 3 * j + 3
                faces += [(a_, a_ + 2, b_ + 2, b_), (a_ + 2, a_ + 1, b_ + 1, b_ + 2)]
            faces += [(b0, b0 + 1, b0 + 2), (b0 + 3 * (len(idx) - 1), b0 + 3 * (len(idx) - 1) + 2, b0 + 3 * (len(idx) - 1) + 1)]
        fo = G.mesh_obj('_flash', verts, faces, M['fused_raw'], recalc=False)
        bm = bmesh.new(); bm.from_mesh(fo.data)          # an open wedge: make each side face look away from the middle plane
        for f_ in bm.faces:
            f_.normal_update()
            cy = f_.calc_center_median().y
            if abs(cy) > 1e-6 and f_.normal.y * cy < 0:
                f_.normal_flip()
        bm.to_mesh(fo.data); bm.free()
        G.shade(fo, 50)
        G.set_frame(fo, MCORE)
        pid = 'core_flash' if k == 0 else 'core_flash_%d' % (k + 1)
        CT.part(fo, FAM, pid, 'Flash on the pressed core, piece %d' % (k + 1), parent='grip.core', kind='consumable', material='alloy', mass='tiny', loose=True, flex=True,
                steps=['s4.open', 's4.flash'], note='in the frame of grip.core, identity transform; filed off along path file (on core_flash); parting plane P Y = 0')
        vs = [fo.matrix_world @ v.co for v in fo.data.vertices]
        CT.grab(fo, sum(vs, Vector()) / len(vs))
        FLASH.append(fo)
    on_i = [i for i in range(NF) if onm[i]]
    fp = [ring_[i] for i in on_i[::max(1, len(on_i) // 38)]][:40]
    CT.path(FLASH[0], 'file', fp, [nrm[i] for i in on_i[::max(1, len(on_i) // 38)]][:40])
    # the sprue: a stub on the parting line under the base, necked where it snaps
    sp_, sn_ = ring_[sprue_i], nrm[sprue_i]
    sprue = G.lathe('_sprue', [([(a * MM, b * MM) for a, b in ((-0.3, 0.0), (-0.3, 2.2), (0.35, 1.7), (1.3, 3.0), (5.6, 3.4), (7.0, 3.1), (7.6, 2.0), (7.3, 0.0))], False)], 10,
                    sp_, sn_, Y, M['fused_raw'])
    G.displace(sprue, lambda c: c + Y * (0.0005 * math.sin((c - sp_).dot(sn_) * 2600.0) if (c - sp_).dot(sn_) > 0.006 else 0.0))        # a broken, uneven end
    G.shade(sprue, 45)
    G.set_frame(sprue, MCORE)
    CT.part(sprue, FAM, 'core_sprue', 'Sprue stub on the pressed core', parent='grip.core', kind='consumable', material='alloy', mass='tiny', symmetry=0,
            steps=['s4.open', 's4.flash'], note='in the frame of grip.core, identity transform; snaps off at mark snap')
    CT.clear(sprue, offset=sn_ * (18 * MM))
    CT.mark(sprue, 'snap', sp_ + sn_ * (0.35 * MM), sn_)
    FLASH.append(sprue)
    bpy.data.objects.remove(gcore, do_unlink=True)
    NOTES['core'] = {'parting_plane': 'P Y = 0 (the middle plane of grip.core)', 'outline_read_at_y_mm': 8.0, 'grip_blend_generated': json.load(open(os.path.join(HERE, '..', 'grip', 'export', 'parts.json')))['generated'],
                     'flash_pieces': len(pieces), 'flash_segments': total, 'of': NF, 'sprue_at_P_mm': [round(c / MM, 2) for c in sp_]}

# ====================================================================== rest coordinates, absent parts, sequence
for S in (SA, SB):
    for o in S['rest_objs']:
        mtl.set_rest(o)
mtl.set_rest(scribe)
for o in list(CT.parts(FAM).values()):          # every part that carries a 'rest' material must have the attribute
    if any(m and m.get('rest') for m in o.data.materials) and not o.get('has_rest'):
        raise RuntimeError('%s has a rest-space material but no sh_rest attribute' % o.name)

ABSENT = [json.loads(o['sh'])['id'] for o in FLASH] + ['strap_bent', 'strap_bent_1', 'sheet_a_scribe'] + ['swarf_%d' % i for i in range(1, 6)] + ['bobbin_wire', 'resistor', 'lead_sense', 'loop_tucked'] + \
         ['loop_' + k for k in ('lead_a', 'lead_b', 'resistor', 'sleeve_a', 'sleeve_b')]
for k in 'ab':
    ABSENT += ['lead_' + k, 'lead_%s_strands' % k, 'lead_%s_slug' % k, 'lead_%s_offcut' % k, 'sleeve_' + k]
CT.absent(ABSENT)
seq = []
for k in 'ab':          # the unit comes out with its leads; the insulation is then pulled off the stripped length
    seq += [{'op': 'insert', 'part': 'lead_' + k, 'step': 's2.trunnion'}, {'op': 'insert', 'part': 'lead_%s_strands' % k, 'step': 's2.trunnion'},
            {'op': 'insert', 'part': 'lead_%s_slug' % k, 'step': 's2.trunnion'}, {'op': 'remove', 'part': 'lead_%s_slug' % k, 'step': 's3.strip'}]
seq += [{'op': 'remove', 'part': 'vial_stopper', 'step': 's4.charge'}, {'op': 'insert', 'part': 'vial_stopper', 'step': 's4.charge'}]
CT.sequence(seq)

F.uv_weights = {'materials_sheet_a_plate': 1.9, 'materials_sheet_b_plate': 1.9, 'materials_strap_bent': 1.9, 'materials_strap_bent_1': 0.6,
                'materials_sheet_a_strap': 0.9, 'materials_sheet_b_strap': 0.8, 'materials_sheet_a': 0.9, 'materials_sheet_b': 0.9,
                'materials_sheet_a_offcut_1': 0.9, 'materials_sheet_a_offcut_2': 0.9, 'materials_sheet_b_offcut_1': 0.9, 'materials_sheet_b_offcut_2': 0.9,
                'materials_sheet_a_margin': 0.9, 'materials_sheet_b_margin': 0.9, 'materials_bobbin_wire': 0.8, 'materials_loop_tucked': 1.2}
for k in 'ab':
    for s in ('lead_%s', 'lead_%s_strands', 'lead_%s_slug', 'lead_%s_offcut', 'loop_lead_%s', 'loop_sleeve_%s', 'sleeve_%s'):
        F.uv_weights['materials_' + s % k] = 1.3
for i in range(1, 5):
    F.uv_weights['materials_sheet_a_plug_%d' % i] = 1.9
    F.uv_weights['materials_sheet_b_plug_%d' % i] = 1.9

NOTES['frames'] = {
    'plates': 'node frame = grip/interface.json plate.node_frames (origin G on the inner face, +Y = S, +Z out of the grip, +X = -U left / +U right); the node transform lays the plate in its sheet',
    'strap': 'sheet_a_strap, sheet_b_strap, strap_bent and strap_bent_1 share the grip frame G as node frame; the flat strip coincides with the bent strap along the back leg',
    'cradle': 'lead_*, sleeve_*, loop_* are in the datum D of servo.gimbal_cradle with identity transforms; the bench there is at z = %.1f mm' % BENCH_Z,
    'loose': 'sheets, swarf, resistor, vial and bobbin lie in a row along X on z = 0',
    'sheet_plan': {'G_at_mm': [X0, Y0], 'rule': 'x = %.1f + S, y = %.1f + U from the sheet corner' % (X0, Y0), 'sheet_a_corner_m': list(SA['O']), 'sheet_b_corner_m': list(SB['O'])}}
PENDING = [] if FLASH else [{'id': 'materials.core_flash', 'waits_for': 'grip/export/grip.blend'}, {'id': 'materials.core_sprue', 'waits_for': 'grip/export/grip.blend'}]
DROPPED = ['materials.core_raw (SEAM.md section 10: the pressed core is grip.core)', 'materials.charge (SEAM.md section 10: fixtures.mould_charge)']
F.finish(extra={'pending': PENDING, 'dropped': DROPPED, 'notes': {'wipes': 'one as-found set for the family (SEAM.md section 7): tinning on strands and resistor legs, punch dimples on sheet A plugs',
                                              'absent_at_start_also': 'the bench leads and the loose resistor are absent at the start: they appear when the unit is lifted out and the resistor is snipped off'}})
