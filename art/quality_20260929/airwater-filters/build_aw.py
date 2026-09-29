"""Air + Water three-filter mounts and fittings - authoring (29 Sep 2026, task t_bd3d9fe3).

    sh bl.sh --python build_aw.py

Opens airwater-review-base.blend (the 9 Sep surface-pass `air_water` objects re-expressed in A-space; never saved over), builds five
modules in A-space (building-local metres, +X screen-right from the avenue, +Y up, +Z towards the avenue, Y = 0 porch top) and saves
airwater-filters-source-v1.blend.  Geometry only; PBR maps come from make_aw_textures.py, label rectangles from textures/layout.json.

Modules
  AW_FilterMount_1/2/3  per vessel: two bolted hoop straps with rubber liners and masonry-anchored ears, U-cradle under the bottom
                        collar with gussets and anchored wall plates, curved FILTER n service plate, differentiated outlet, inlet coupling
                        (union / gasketed flange / reducer + vent), boss, mineral crust, drips and runs.
  AW_FilterHeader       new DN50 header with three tees, two hangers, blanked end, flanged isolation ball valve (red lever), pressure
                        gauge with red limit flag, ISOLATE plate, 45 degree set to the riser line, mineral at every joint.
  AW_FeedRiser          union, elbow, riser with a gasketed flange joint, roof turns.  Existing clamps / stand-offs / masonry anchors kept.
Superseded rev 04 / 9 Sep objects are only flagged (aw_retired) in the review scene.
"""
import bpy, bmesh, math, json, sys
from pathlib import Path
from mathutils import Vector, Matrix

OUT = Path('/home/teknetik/code/ao2/art/quality_20260929/airwater-filters')
sys.path.insert(0, str(OUT))
import aw_lib as L
from aw_lib import Part, material

bpy.ops.wm.open_mainfile(filepath=str(OUT / 'airwater-review-base.blend'))
scene = bpy.data.scenes[0]
bpy.context.window.scene = scene
new_col = bpy.data.collections.new('AW filter fittings (new)')
scene.collection.children.link(new_col)

LAYOUT = json.loads((OUT / 'textures/layout.json').read_text())['labels']
M = material
M('Paint', 'AW_PaintSlate', .5)
M('Steel', 'AW_BareSteel', .5)
M('Bronze', 'AW_Bronze', .5)
M('ValveRed', 'AW_ValveRed', .4)
M('Rubber', 'AW_Rubber', .3)
M('Mineral', 'AW_Mineral', .3)
M('Labels', 'AW_Labels', None, unique_uv=True, note='Unique 4096x512 at 6000 px/m; rectangles in textures/layout.json (FILTER 1/2/3, ISOLATE)')
M('Dial', 'AW_Dial', None, unique_uv=True, note='Unique 1024x1024; face circle radius 0.494 of the texture, centre (0.5, 0.5); mapped 1:1 onto a 0.0365 m radius face')

PI = math.pi
ZW = 2.73                       # front plaster plane (recessed spalls sit at 2.687, see wall-recess-samples.json)
VESSEL_R, VESSEL_CZ = .25, 2.93
VESSELS = [.9, 1.7, 2.5]
HY = 2.12                       # header axis height
HZ = 2.93                       # header axis depth (over the vessel axes)
RZ, RX = 3.03, 3.18             # existing riser axis (z, x), from the retained clamps / anchors
RECESS = json.loads((OUT / 'wall-recess-samples.json').read_text())['samples']
WARN = []


def wall_z(x, y):
    """Wall depth at (x, y): 2.687 inside a sampled spall, 2.73 elsewhere."""
    for sx, sy, sz in RECESS:
        if abs(sx - x) < .03 and abs(sy - y) < .03:
            return 2.687
    return ZW


def check_wall(name, x0, x1, y0, y1):
    bad = [(round(x, 2), round(y, 2)) for x in (x0, (x0 + x1) / 2, x1) for y in (y0, (y0 + y1) / 2, y1) if wall_z(x, y) < ZW]
    if bad:
        WARN.append(f'{name} touches a spall at {bad}')


# ------------------------------------------------------------------ small builders
def hex_nut(p, pos, axis, af, h, mat='Bronze'):
    r = af / math.sqrt(3)
    p.lathe([(r * .9, 0), (r, .12 * h), (r, .88 * h), (r * .9, h)], mat, .5, pos=pos, axis=axis, segs=6)


def disc(p, pos, axis, r, h, mat, segs=28, tile=.5, prof=None):
    p.lathe(prof or [(r, 0), (r, h)], mat, tile, pos=pos, axis=axis, segs=segs)


def ring(p, pos, axis, ri, ro, h, mat, segs=32, tile=.5):
    p.lathe([(ri, 0), (ro, 0), (ro, h), (ri, h), (ri, 0)], mat, tile, pos=pos, axis=axis, segs=segs, caps=(False, False))


def anchor(p, x, y, z, af=.017, axis=(0, 0, 1)):
    """Sleeve anchor head: washer + hex head, `z` = seating face."""
    ax = Vector(axis)
    disc(p, Vector((x, y, z)), axis, .0185, .003, 'Steel', segs=18)
    hex_nut(p, Vector((x, y, z)) + ax * .003, axis, af, .0075, 'Steel')


def bolt_head(p, pos, axis, af, h, washer=True):
    ax = Vector(axis)
    if washer:
        disc(p, pos, axis, af * .95, .0025, 'Steel', segs=14)
        pos = Vector(pos) + ax * .0025
    hex_nut(p, pos, axis, af, h, 'Steel')


def round_dome(p, pos, axis, r=.0036):
    p.lathe([(r, 0), (r, .0008), (r * .75, .0018), (r * .4, .0025), (0, .0028)], 'Steel', .5, pos=pos, axis=axis, segs=10)


def fillet_path(pts, r, only=None, n=7):
    """Polyline with circular fillets of radius r at the vertices in `only` (all interior vertices if None)."""
    out = [Vector(pts[0])]
    for i in range(1, len(pts) - 1):
        a, b, c = Vector(pts[i - 1]), Vector(pts[i]), Vector(pts[i + 1])
        if only is not None and i not in only:
            out.append(b); continue
        u = (a - b).normalized(); v = (c - b).normalized()
        ang = math.acos(max(-1, min(1, u.dot(v))))
        if PI - ang < math.radians(3):
            out.append(b); continue
        rr = r(i) if callable(r) else r
        t = min(rr / math.tan(ang / 2), (a - b).length * .5, (c - b).length * .5)
        rr = t * math.tan(ang / 2)
        p1 = b + u * t; p2 = b + v * t
        cen = b + (u + v).normalized() * (rr / math.sin(ang / 2))
        v1 = (p1 - cen).normalized(); v2 = (p2 - cen).normalized()
        th = math.acos(max(-1, min(1, v1.dot(v2))))
        for k in range(n + 1):
            s = k / n
            d = (v1 * math.sin((1 - s) * th) + v2 * math.sin(s * th)) / math.sin(th)
            out.append(cen + d * rr)
    out.append(Vector(pts[-1]))
    return out


def crust(p, pos, axis, r, h, seed, mat='Mineral', amp=.25, th=1.0):
    """Hard-water crust at a joint: lumpy lathe, thickest in the middle.  On horizontal joints it is weighted to the underside (water runs down
    and dries there); the upper half sinks inside the fitting so nothing reads as a floating fin."""
    ph = seed * 1.7
    ax = Vector(axis).normalized()
    ref = Vector((0, 0, 1)) if abs(ax.z) < .9 else Vector((1, 0, 0))
    e1 = ax.cross(ref).normalized(); e2 = ax.cross(e1).normalized()
    horiz = abs(ax.y) < .5
    sink = (r - .004) / (r + .011)

    def wp(a, hh):
        lump = 1 + amp * math.sin(3 * a + ph + hh * 70) * math.cos(2 * a - ph * .7 - hh * 55)
        if not horiz:
            return lump
        dy = math.cos(a) * e1.y + math.sin(a) * e2.y          # +1 top, -1 underside
        w = min(1.0, max(0.0, (dy + .1) / .5))                # 0 below the horizon .. 1 on top
        return lump * (1 - w * (1 - sink))
    p.lathe([(r + .0008, 0), (r + .006 * th, .12 * h), (r + .011 * th, .45 * h), (r + .009 * th, .75 * h), (r + .0008, h)], mat, .3, pos=pos, axis=axis, segs=26, warp=wp)


def stalactite(p, pos, length, r, seed=1.0):
    ph = seed
    p.lathe([(0, -length), (r * .28, -length * .72), (r * .62, -length * .38), (r, 0)], 'Mineral', .3, pos=pos, axis=(0, 1, 0), segs=10,
            warp=lambda a, hh: 1 + .2 * math.sin(2 * a + ph))


def lump(p, pos, r, seed=1.0, squash=.45):
    """Mineral bead / splash crust (flattened lumpy dome) on a surface facing +Z."""
    ph = seed
    p.lathe([(r, 0), (r * 1.02, r * squash * .35), (r * .75, r * squash * .8), (r * .3, r * squash), (0, r * squash * 1.02)], 'Mineral', .3, pos=pos,
            axis=(0, 0, 1), segs=14, warp=lambda a, hh: 1 + .25 * math.sin(3 * a + ph) * math.cos(a * 2 - ph))


def cyl_pt(cx, cz, R, phi, y):
    return Vector((cx + R * math.cos(phi), y, cz + R * math.sin(phi)))


def wall_plate(p, x, y, w, h, anchors, af=.017, mat='Paint', name='plate'):
    """Vertical steel plate on the wall with anchor heads at `anchors` [(dx, dy)]."""
    check_wall(name, x - w / 2, x + w / 2, y - h / 2, y + h / 2)
    if any(wall_z(xx, yy) < ZW for xx in (x - w / 2, x, x + w / 2) for yy in (y - h / 2, y, y + h / 2)):
        # plate straddles a plaster spall (43 mm deep): bed it on a steel packer that fills the hollow so the anchors bite
        p.box((x, y, (2.687 + ZW) / 2), (w - .016, h - .016, ZW - 2.687), 'Steel', .5, bevel=.0015, seg=1)
    p.box((x, y, ZW + .0028), (w, h, .0056), mat, .5, bevel=.0018, seg=2)
    for dx, dy in anchors:
        anchor(p, x + dx, y + dy, ZW + .0056, af)


# ------------------------------------------------------------------ vessel: straps
def strap(p, cx, y, lug_side, seed, R=.2557, w=.040, ears=(1, 1)):
    """Hoop strap round the vessel from wall to wall, flat ears on the plaster, rubber liner, tension lug with a through bolt."""
    cz = VESSEL_CZ
    a0 = math.asin(-(cz - ZW) / R)                # right wall crossing (about -51.5 deg)
    a1 = PI - a0
    N = 44
    arc = [cyl_pt(cx, cz, R, a0 + (a1 - a0) * i / N, y) for i in range(N + 1)]
    zc = ZW + .0024
    er = Vector((cx + R * math.cos(a0) + .078, y, zc)); el = Vector((cx + R * math.cos(a1) - .078, y, zc))
    pts = [er] + arc + [el]
    pts = fillet_path(pts, .022, only={1, len(pts) - 2}, n=6)
    sec = [(-w / 2, -.0024), (w / 2, -.0024), (w / 2, .0024), (-w / 2, .0024)]
    p.sweep(pts, sec, lambda P: Vector((P.x - cx, 0, P.z - cz)), 'Paint', .5)
    # rubber liner (wider than the strap so its edges read)
    lin = [cyl_pt(cx, cz, .2517, a0 + .02 + (a1 - a0 - .04) * i / 34, y) for i in range(35)]
    p.sweep(lin, [(-w / 2 - .007, -.0015), (w / 2 + .007, -.0015), (w / 2 + .007, .0015), (-w / 2 - .007, .0015)],
            lambda P: Vector((P.x - cx, 0, P.z - cz)), 'Rubber', .3)
    # ear anchors
    for sgn, on in ((1, ears[0]), (-1, ears[1])):
        if on:
            anchor(p, cx + sgn * .208, y, ZW + .0048)
    # tension lug: two blocks either side of a gap, bolt through both
    phi = math.radians(52) if lug_side > 0 else math.radians(128)      # front-right / front-left: visible from the avenue, clear of the label (71..109 deg)
    tng = Vector((-math.sin(phi), 0, math.cos(phi)))
    rad = Vector((math.cos(phi), 0, math.sin(phi)))
    rc = cyl_pt(cx, cz, R + .0024 + .0075, phi, y)
    for s in (-1, 1):
        p.box(rc + tng * (s * .0165), (.024, w + .008, .015), 'Paint', .5, bevel=.0022, seg=2, rot=(0, -(phi + PI / 2), 0))
    bolt_pos = rc - tng * .036
    p.lathe([(.0038, 0), (.0038, .075)], 'Steel', .5, pos=bolt_pos, axis=tuple(tng), segs=8)
    bolt_head(p, bolt_pos, tuple(tng), .016, .008)
    hex_nut(p, rc + tng * .0295, tuple(tng), .015, .009, 'Steel')
    hex_nut(p, rc + tng * .0395, tuple(tng), .015, .009, 'Steel')
    check_wall('strap ears', cx - .25, cx + .25, y - w / 2, y + w / 2)


# ------------------------------------------------------------------ vessel: cradle
def cradle(p, cx, seed, skew=0.0):
    cz = VESSEL_CZ
    y0, y1 = .4785, .4865
    prof = [(cx + .19, ZW), (cx + .30, ZW), (cx + .30, cz)]
    prof += [(cx + .30 * math.cos(a), cz + .30 * math.sin(a)) for a in [PI * i / 22 for i in range(1, 22)]]
    prof += [(cx - .30, cz), (cx - .30, ZW), (cx - .19, ZW), (cx - .19, cz)]
    prof += [(cx + .19 * math.cos(a), cz + .19 * math.sin(a)) for a in [PI - PI * i / 22 for i in range(1, 22)]]
    # (x, z) polygon in the axis-'y' prism convention; reject the duplicated seam vertex if any
    seen, clean = set(), []
    for q in prof:
        k = (round(q[0], 5), round(q[1], 5))
        if k not in seen:
            seen.add(k); clean.append(q)
    p.prism(clean, 'y', y0, y1, 'Paint', .5)
    for s in (-1, 1):
        xp = cx + s * .245
        yc = .4245 + (skew if s > 0 else 0)
        wall_plate(p, xp, yc, .11, .124, [(-.03, .033), (.03, .033), (-.03, -.033), (.03, -.033)], name=f'cradle plate {cx} {s}')
        # gusset triangle under the arm, on the wall
        p.prism([(ZW + .005, yc - .13), (cz - .03, y0 - .0005), (ZW + .005, y0 - .0005)], 'x', xp - .0045, xp + .0045, 'Paint', .5) if False else None
        gz = [(ZW + .0056, .27), (cz - .04, y0 - .0004), (ZW + .0056, y0 - .0004)]
        p.prism([(z, y) for z, y in gz], 'x', xp - .0045, xp + .0045, 'Paint', .5)
        # a bolt through each arm at the saddle
        bolt_head(p, Vector((xp, y1 + .0005, cz - .02)), (0, 1, 0), .014, .006)


# ------------------------------------------------------------------ vessel: service plate
def curved_plate(p, cx, cz, R, yc, w, h, t, rect, mat_rim='Steel', nu=16):
    bm = p.bm

    def P(s, y, rad):
        a = PI / 2 - s / R
        return bm.verts.new((cx + rad * math.cos(a), y, cz + rad * math.sin(a)))
    ss = [-w / 2 + w * i / nu for i in range(nu + 1)]
    fb = [P(s, yc - h / 2, R + t) for s in ss]; ft = [P(s, yc + h / 2, R + t) for s in ss]
    bb = [P(s, yc - h / 2, R) for s in ss]; bt = [P(s, yc + h / 2, R) for s in ss]
    front, rest = [], []
    for i in range(nu):
        front.append(bm.faces.new((fb[i], fb[i + 1], ft[i + 1], ft[i])))
        rest.append(bm.faces.new((bb[i + 1], bb[i], bt[i], bt[i + 1])))
        rest.append(bm.faces.new((fb[i], bb[i], bb[i + 1], fb[i + 1])))
        rest.append(bm.faces.new((ft[i], ft[i + 1], bt[i + 1], bt[i])))
    rest.append(bm.faces.new((fb[0], ft[0], bt[0], bb[0])))
    rest.append(bm.faces.new((fb[nu], bb[nu], bt[nu], ft[nu])))
    allf = front + rest
    p._new()
    bmesh.ops.recalc_face_normals(bm, faces=allf)
    u0, v0, u1, v1 = rect
    ins = .004
    for i, f in enumerate(front):
        for lp in f.loops:
            co = lp.vert.co
            a = math.atan2(co.z - cz, co.x - cx)
            s = (PI / 2 - a) * R
            u = (s + w / 2) / w
            v = (co.y - (yc - h / 2)) / h
            lp[p.uv].uv = (u0 + (u1 - u0) * (ins + (1 - 2 * ins) * u), v0 + (v1 - v0) * (ins + (1 - 2 * ins) * v))
    p.uv_box(rest, mat_rim, .5)
    p._tag(front, 'Labels')
    p._tag(rest, mat_rim)
    for sx in (-1, 1):
        for sy in (-1, 1):
            s = sx * (w / 2 - .0075)
            pos = cyl_pt(cx, cz, R + t, PI / 2 - s / R, yc + sy * (h / 2 - .0075))
            round_dome(p, pos, (math.cos(PI / 2 - s / R), 0, math.sin(PI / 2 - s / R)))


def flat_plate(p, x, y, z, w, h, rect, name):
    u0, v0, u1, v1 = rect
    ins = .004
    fn = lambda co, n: (u0 + (u1 - u0) * (ins + (1 - 2 * ins) * min(1, max(0, (co.x - (x - w / 2)) / w))),
                        v0 + (v1 - v0) * (ins + (1 - 2 * ins) * min(1, max(0, (co.y - (y - h / 2)) / h))))
    check_wall(name, x - w / 2, x + w / 2, y - h / 2, y + h / 2)
    p.box((x, y, z + .002), (w, h, .004), 'Steel', .5, bevel=.0012, seg=1, over=[(2, 1, 'Labels', None, fn)])
    for sx in (-1, 1):
        anchor(p, x + sx * (w / 2 - .011), y, z + .004, af=.011)


# ------------------------------------------------------------------ vessel: mineral run
def vessel_run(p, cx, phi, y0, y1, w0, w1, seed):
    cz = VESSEL_CZ
    N = 26
    pts = []
    for i in range(N + 1):
        t = i / N
        y = y0 + (y1 - y0) * t
        ph = phi + .035 * math.sin(t * 7.0 + seed) + .02 * math.sin(t * 17 + seed * 2)
        pts.append(cyl_pt(cx, cz, .2512, ph, y))
    sec = [(-.5, -.0013), (.5, -.0013), (.5, .0013), (-.5, .0013)]
    # width varies with the path: taper toward the bottom, blobs at the start
    p.sweep(pts, sec, lambda P: Vector((P.x - cx, 0, P.z - cz)), 'Mineral', .3, scale_fn=lambda t: 2.4 * (w0 + (w1 - w0) * t) * (1 + .35 * math.sin(t * 19 + seed)) * (1 - t ** 3 * .75))


# ------------------------------------------------------------------ vessel module
def build_vessel(i, cx, cfg):
    p = Part(f'AW_FilterMount_{i}', seed=100 + i)
    cz = VESSEL_CZ
    for k, (y, lug) in enumerate(zip(cfg['strap_y'], cfg['lug'])):
        strap(p, cx, y, lug, seed=i * 3 + k, ears=cfg['ears'][k])
    cradle(p, cx, i, cfg.get('skew', 0))
    # label plate: 0.17 x 0.06 m on the vessel front
    curved_plate(p, cx, cz, VESSEL_R, cfg['label_y'], .17, .06, .0055, LAYOUT[f'FILTER {i}']['uv'])
    # --- outlet
    o = cfg['outlet']
    ob = Vector((cx, .501, cz))
    if o == 'hose':
        p.tube([ob, (cx, .432, cz)], .0205, 'Bronze', .5, sides=12)
        hex_nut(p, (cx, .432, cz), (0, -1, 0), .052, .026, 'Bronze')            # union nut up to y .406
        ring(p, (cx, .406, cz), (0, -1, 0), .0, .0275, .008, 'Bronze', segs=18)
        hex_nut(p, (cx, .398, cz), (0, -1, 0), .052, .026, 'Bronze')
        pts = fillet_path([(cx, .372, cz), (cx, .335, cz), (cx, .335, cz + .17)], .045, n=8)
        p.tube(pts, .0205, 'Bronze', .5, sides=12)
        # hose tail + rubber hose + worm-drive clamp
        p.lathe([(.0205, 0), (.0225, .002), (.0225, .008), (.0165, .010), (.0165, .022), (.0225, .024), (.0225, .030)], 'Bronze', .5, pos=(cx, .335, cz + .105), axis=(0, 0, 1), segs=16)
        hp = fillet_path([(cx, .335, cz + .118), (cx, .335, cz + .225 - .0), (cx, .225, cz + .225)], .05, n=8)
        p.tube([Vector(q) for q in hp][:], .0195, 'Rubber', .3, sides=14)
        ring(p, (cx, .335, cz + .128), (0, 0, 1), .0190, .0225, .012, 'Steel', segs=18)
        p.box((cx, .335 + .0245, cz + .134), (.014, .011, .012), 'Steel', .5, bevel=.0015, seg=1)
        # trickle of scale at the hose lip and a stalactite under the union
        crust(p, (cx, .420, cz), (0, -1, 0), .0275, .030, 1 + i, amp=.3)
        stalactite(p, (cx + .012, .385, cz + .028), .05, .006, 1.0 + i)
        stalactite(p, (cx - .01, .385, cz + .03), .028, .0045, 2.0 + i)
    elif o == 'cap':
        p.tube([ob, (cx, .432, cz)], .0205, 'Bronze', .5, sides=12)
        hex_nut(p, (cx, .432, cz), (0, -1, 0), .052, .026, 'Bronze')
        ring(p, (cx, .406, cz), (0, -1, 0), .0, .0275, .008, 'Bronze', segs=18)
        hex_nut(p, (cx, .398, cz), (0, -1, 0), .052, .026, 'Bronze')
        pts = fillet_path([(cx, .372, cz), (cx, .335, cz), (cx, .335, cz + .12)], .045, n=8)
        p.tube(pts, .0205, 'Bronze', .5, sides=12)
        ring(p, (cx, .335, cz + .0975), (0, 0, 1), .0205, .0268, .0075, 'Bronze', segs=18)
        ring(p, (cx, .335, cz + .1050), (0, 0, 1), .0195, .0262, .0025, 'Rubber', segs=18, tile=.3)
        hex_nut(p, (cx, .335, cz + .1075), (0, 0, 1), .05, .030, 'Bronze')          # threaded blanking cap
        disc(p, (cx, .335, cz + .1375), (0, 0, 1), .018, .004, 'Steel', segs=16)
        crust(p, (cx, .335, cz + .0975), (0, 0, 1), .0268, .010, 6 + i, amp=.35)
        crust(p, (cx, .420, cz), (0, -1, 0), .0275, .030, 8 + i, amp=.25)
        stalactite(p, (cx, .323, cz + .12), .04, .0055, 3.0 + i)
    else:      # 'bend': 45 degree offset dropping to the right, flanged end with gasket
        p.tube([ob, (cx, .440, cz)], .0205, 'Bronze', .5, sides=12)
        hex_nut(p, (cx, .440, cz), (0, -1, 0), .052, .026, 'Bronze')
        ring(p, (cx, .414, cz), (0, -1, 0), .0, .0275, .008, 'Bronze', segs=18)
        hex_nut(p, (cx, .406, cz), (0, -1, 0), .052, .026, 'Bronze')
        pts = fillet_path([(cx, .380, cz), (cx, .30, cz), (cx + .13, .17, cz)], .06, n=10)
        p.tube(pts, .0205, 'Bronze', .5, sides=12)
        d = Vector((.13, -.13, 0)).normalized()
        e0 = Vector((cx + .13, .17, cz)) - d * .012
        ring(p, e0 - d * .0, tuple(d), .0, .043, .010, 'Bronze', segs=20)
        ring(p, e0 + d * .010, tuple(d), .0195, .0405, .003, 'Rubber', segs=20, tile=.3)
        for a in range(4):
            aa = a * PI / 2 + PI / 4
            n1 = d.cross(Vector((0, 0, 1))).normalized()
            pos = e0 + d * .001 + n1 * (.032 * math.cos(aa)) + Vector((0, 0, 1)) * (.032 * math.sin(aa)) - d * 0.0
            bolt_head(p, pos - d * .004, tuple(-d), .012, .006, washer=False)
        crust(p, (cx, .424, cz), (0, -1, 0), .0275, .030, 12 + i, amp=.3)
        stalactite(p, (cx + .13, .147, cz), .04, .008, 4.0 + i)
    # --- inlet coupling stack on the vessel top (y 1.98 .. 2.075)
    p.box((cx, 1.985, cz), (.001, .001, .001), 'Bronze', .5, bevel=0, seg=1) if False else None
    disc(p, (cx, 1.980, cz), (0, 1, 0), .050, .010, 'Bronze', segs=28)              # boss flange on the cap
    for a in range(4):
        aa = a * PI / 2 + PI / 4
        bolt_head(p, (cx + .036 * math.cos(aa), 1.990, cz + .036 * math.sin(aa)), (0, 1, 0), .013, .006, washer=False)
    top = cfg['inlet']
    if top == 'union':
        p.tube([(cx, 1.996, cz), (cx, 2.010, cz)], .0205, 'Bronze', .5, sides=12)
        hex_nut(p, (cx, 2.004, cz), (0, 1, 0), .052, .028, 'Bronze')
        ring(p, (cx, 2.032, cz), (0, 1, 0), .0, .0275, .008, 'Bronze', segs=20)
        ring(p, (cx, 2.039, cz), (0, 1, 0), .0, .0255, .0025, 'Rubber', segs=20, tile=.3)
        hex_nut(p, (cx, 2.0415, cz), (0, 1, 0), .052, .028, 'Bronze')
        p.tube([(cx, 2.069, cz), (cx, 2.078, cz)], .0215, 'Bronze', .5, sides=12)
        crust(p, (cx, 2.000, cz), (0, 1, 0), .0345, .036, 20 + i, amp=.3)
        stalactite(p, (cx + .02, 2.002, cz + .03), .04, .0055, 5.0 + i)
        stalactite(p, (cx - .025, 2.002, cz + .02), .026, .0045, 6.0 + i)
    elif top == 'flange':
        disc(p, (cx, 1.990, cz), (0, 1, 0), .0525, .012, 'Bronze', segs=28)
        ring(p, (cx, 2.002, cz), (0, 1, 0), .0195, .0505, .003, 'Rubber', segs=28, tile=.3)
        disc(p, (cx, 2.005, cz), (0, 1, 0), .0525, .012, 'Bronze', segs=28)
        for a in range(4):
            aa = a * PI / 2
            bolt_head(p, (cx + .039 * math.cos(aa), 2.017, cz + .039 * math.sin(aa)), (0, 1, 0), .013, .0065)
        p.lathe([(.0525, 0), (.0525, .001), (.038, .012), (.026, .026), (.0215, .034), (.0215, .038)], 'Bronze', .5, pos=(cx, 2.017 + .006 + .003, cz), axis=(0, 1, 0), segs=24)
        crust(p, (cx, 1.996, cz), (0, 1, 0), .0525, .012, 30 + i, amp=.2, th=.3)
        stalactite(p, (cx - .02, 1.992, cz + .046), .045, .0065, 7.0 + i)
        stalactite(p, (cx + .03, 1.992, cz + .037), .028, .0045, 8.0 + i)
    else:      # 'reducer': union + reducing bush, side vent stub with hex cap
        p.tube([(cx, 1.996, cz), (cx, 2.008, cz)], .0205, 'Bronze', .5, sides=12)
        hex_nut(p, (cx, 2.002, cz), (0, 1, 0), .052, .026, 'Bronze')
        ring(p, (cx, 2.028, cz), (0, 1, 0), .0, .0275, .008, 'Bronze', segs=20)
        hex_nut(p, (cx, 2.036, cz), (0, 1, 0), .046, .020, 'Bronze')
        p.lathe([(.024, 0), (.0215, .012), (.0215, .020)], 'Bronze', .5, pos=(cx, 2.056, cz), axis=(0, 1, 0), segs=16)
        p.tube([(cx, 2.046, cz + .0), (cx, 2.046, cz + .058)], .0085, 'Bronze', .5, sides=8)
        hex_nut(p, (cx, 2.046, cz + .052), (0, 0, 1), .019, .012, 'Bronze')
        crust(p, (cx, 2.036, cz), (0, 1, 0), .0290, .022, 40 + i, amp=.3)
        stalactite(p, (cx, 2.043, cz + .062), .03, .0045, 9.0 + i)
        stalactite(p, (cx + .022, 2.002, cz + .026), .036, .0055, 10.0 + i)
    # --- mineral runs on the vessel skin below the top cap
    for (phi, y0, y1, w0, w1, sd) in cfg['runs']:
        vessel_run(p, cx, phi, y0, y1, w0, w1, sd)
    # --- crust on the strap ear anchors is left clean; drip splash beneath the outlet on the porch is NOT modelled (ground is not ours)
    return p.finalise(new_col, origin=(cx, .5, cz))


# ------------------------------------------------------------------ header module
def header_hanger(p, x, style):
    """Wall plate + stand-off arm + strap ring round the header, two ears with a through bolt."""
    wall_plate(p, x, HY, .07, .10, [(0, .034), (0, -.034)], name=f'header hanger {x}')
    p.box((x, HY, (ZW + .0056 + HZ - .034) / 2), (.030, .024, HZ - .034 - ZW - .0056), 'Paint', .5, bevel=.0025, seg=2)
    ring(p, (x - .011, HY, HZ), (1, 0, 0), .0300, .0330, .022, 'Rubber', segs=26, tile=.3) if style == 'liner' else None
    ring(p, (x - .011, HY, HZ), (1, 0, 0), .0330, .0372, .022, 'Steel', segs=26)
    # ears on the front of the ring, bolt across them
    for s in (-1, 1):
        p.box((x + s * .0075 + 0.0, HY, HZ + .0395), (.008, .030, .026), 'Steel', .5, bevel=.0012, seg=1)
    p.lathe([(.0036, 0), (.0036, .046)], 'Steel', .5, pos=(x - .023, HY, HZ + .0395), axis=(1, 0, 0), segs=8)
    bolt_head(p, (x - .023, HY, HZ + .0395), (1, 0, 0), .014, .006)
    hex_nut(p, (x + .0115, HY, HZ + .0395), (1, 0, 0), .014, .0065, 'Steel')


def build_header():
    p = Part('AW_FilterHeader', seed=200)
    # main header run from the blanked end to the valve inlet flange
    xL, xV0 = .60, 2.63
    p.tube([(xL, HY, HZ), (xV0, HY, HZ)], .030, 'Bronze', .5, sides=18)
    # blanked left end: reducing cap + hex plug, crust below
    p.lathe([(.0385, 0), (.0385, .012), (.0345, .024), (.026, .031), (.0, .034)], 'Bronze', .5, pos=(xL - .0, HY, HZ), axis=(-1, 0, 0), segs=22)
    hex_nut(p, (xL - .034, HY, HZ), (-1, 0, 0), .028, .014, 'Bronze')
    crust(p, (xL - .002, HY - .03, HZ), (0, 1, 0), .0, .0, 0) if False else None
    stalactite(p, (xL - .012, HY - .0345, HZ + .012), .038, .0055, 11.0)
    # tees
    for k, cx in enumerate(VESSELS):
        p.lathe([(.0385, -.058), (.0385, .058)], 'Bronze', .5, pos=(cx - .0, HY, HZ), axis=(1, 0, 0), segs=22) if False else None
        p.lathe([(.0385, 0), (.0385, .112)], 'Bronze', .5, pos=(cx - .056, HY, HZ), axis=(1, 0, 0), segs=22)
        p.lathe([(.0295, 0), (.0295, .006), (.0225, .010), (.0225, .046)], 'Bronze', .5, pos=(cx, HY - .0365, HZ), axis=(0, -1, 0), segs=20)
        ring(p, (cx, HY - .0345, HZ), (0, -1, 0), .0, .0305, .0035, 'Bronze', segs=20)
    # crust bands on the tee sleeves' lower edge (different on each), drips
    crust(p, (.9 - .056, HY, HZ), (1, 0, 0), .0385, .018, 51, amp=.3)
    crust(p, (1.7 + .038, HY, HZ), (1, 0, 0), .0385, .018, 52, amp=.35)
    crust(p, (2.5 - .056, HY, HZ), (1, 0, 0), .0385, .014, 53, amp=.3)
    stalactite(p, (.9 - .048, HY - .040, HZ + .014), .034, .0048, 12.0)
    stalactite(p, (1.7 + .046, HY - .040, HZ + .020), .050, .0058, 13.0)
    stalactite(p, (2.5 - .05, HY - .040, HZ - .012), .028, .0045, 14.0)
    # hangers: left overhang and between vessels 2 and 3
    header_hanger(p, .745, 'liner')
    header_hanger(p, 2.10, 'bare')
    # ---------------- flanged isolation ball valve (open: lever along the pipe)
    xv = 2.76
    for fx, gasket_side in ((xV0, 1), (2.877, -1)):
        disc(p, (fx, HY, HZ), (1, 0, 0), .055, .013, 'Bronze', segs=28)
    ring(p, (2.643, HY, HZ), (1, 0, 0), .0195, .0505, .004, 'Rubber', segs=28, tile=.3)
    ring(p, (2.873, HY, HZ), (1, 0, 0), .0195, .0505, .004, 'Rubber', segs=28, tile=.3)
    disc(p, (2.647, HY, HZ), (1, 0, 0), .055, .013, 'Bronze', segs=28)
    disc(p, (2.860, HY, HZ), (1, 0, 0), .055, .013, 'Bronze', segs=28)
    for fx, sd in ((2.6265, 1), (2.8765, 1)):
        pass
    for a in range(4):
        aa = a * PI / 2 + PI / 4
        yy = HY + .041 * math.cos(aa); zz = HZ + .041 * math.sin(aa)
        # through-bolt: head one side, nut the other, both flanges
        p.lathe([(.0037, 0), (.0037, .262)], 'Steel', .5, pos=(2.617, yy, zz), axis=(1, 0, 0), segs=8)
        bolt_head(p, (2.606, yy, zz), (1, 0, 0), .014, .008, washer=False)
        hex_nut(p, (2.885, yy, zz), (1, 0, 0), .014, .008, 'Steel')
    p.lathe([(.030, 0), (.043, .018), (.050, .046), (.052, .090), (.050, .134), (.043, .162), (.030, .18)], 'Bronze', .5, pos=(2.673, HY, HZ), axis=(1, 0, 0), segs=28)
    # body seam ring + cast lug and stop
    ring(p, (2.755, HY, HZ), (1, 0, 0), .050, .0545, .010, 'Bronze', segs=28)
    # stem, gland, lever (stem axis +Z, lever lies along -X when open)
    p.lathe([(.0175, 0), (.0175, .020), (.0105, .022), (.0105, .062)], 'Bronze', .5, pos=(xv, HY, HZ + .046), axis=(0, 0, 1), segs=14)
    hex_nut(p, (xv, HY, HZ + .066), (0, 0, 1), .028, .010, 'Bronze')
    p.box((xv - .062, HY, HZ + .094), (.150, .022, .006), 'ValveRed', .4, bevel=.0018, seg=2)
    p.lathe([(.0125, 0), (.0125, .012)], 'ValveRed', .4, pos=(xv, HY, HZ + .086), axis=(0, 0, 1), segs=16)
    p.lathe([(.0115, 0), (.0115, .052)], 'Rubber', .3, pos=(xv - .136, HY, HZ + .094), axis=(1, 0, 0), segs=14, warp=lambda a, hh: 1)
    hex_nut(p, (xv, HY, HZ + .100), (0, 0, 1), .017, .009, 'Steel')
    p.box((xv - .026, HY + .036, HZ + .052), (.008, .020, .012), 'Steel', .5, bevel=.0015, seg=1)          # stop lug on the body
    crust(p, (2.6535, HY, HZ), (1, 0, 0), .0545, .008, 60, amp=.2, th=.3)
    crust(p, (2.860, HY, HZ), (1, 0, 0), .0545, .008, 61, amp=.2, th=.3)
    stalactite(p, (2.66, HY - .054, HZ + .02), .050, .0065, 15.0)
    stalactite(p, (2.895, HY - .054, HZ + .016), .036, .005, 16.0)
    # ---------------- pipe from the valve outlet flange, gauge tee, 45 degree set to the riser line
    pts = [(2.890, HY, HZ), (2.985, HY, HZ), (3.085, HY, RZ), (3.090, HY, RZ)]
    pts = fillet_path([Vector(q) for q in [(2.890, HY, HZ), (2.985, HY, HZ), (3.085, HY, RZ), (3.13, HY, RZ)]], .060, n=8)
    pts = [q for q in pts if q.x <= 3.0915] + [Vector((3.0900, HY, RZ))]
    p.tube(pts, .030, 'Bronze', .5, sides=18)
    # gauge: bottom stub from the pipe crown, small hex cock, case with bezel, dial (unique map), needle, limit flag
    gx, gy = 2.945, 2.262
    p.lathe([(.0165, 0), (.0165, .006), (.0105, .009), (.0105, .052)], 'Bronze', .5, pos=(gx, HY + .0285, HZ), axis=(0, 1, 0), segs=14)
    hex_nut(p, (gx, HY + .0400, HZ), (0, 1, 0), .022, .014, 'Bronze')
    p.lathe([(.0425, 0), (.0425, .028), (.0385, .030)], 'Steel', .5, pos=(gx, gy, HZ - .020), axis=(0, 0, 1), segs=36)
    ring(p, (gx, gy, HZ + .008), (0, 0, 1), .0368, .0442, .011, 'Bronze', segs=36)
    # dial disc
    bm = p.bm
    rd = .0368; S = rd / .494
    cen = bm.verts.new((gx, gy, HZ + .0135)); rim = [bm.verts.new((gx + rd * math.cos(a), gy + rd * math.sin(a), HZ + .0135)) for a in [2 * PI * k / 48 for k in range(48)]]
    fs = [bm.faces.new((cen, rim[k], rim[(k + 1) % 48])) for k in range(48)]
    p._new()
    for f in fs:
        if f.normal.z < 0:
            f.normal_flip()
        for lp in f.loops:
            lp[p.uv].uv = (.5 + (lp.vert.co.x - gx) / S, .5 + (lp.vert.co.y - gy) / S)
    p._tag(fs, 'Dial')
    # needle at 2.6 bar (-18 deg from 12 o'clock), fixed limit flag at 4.5 bar (67.5 deg) on the bezel
    ang = math.radians(-135 + 45 * 2.6)
    nd = Vector((math.sin(ang), math.cos(ang), 0))
    p.box(Vector((gx, gy, HZ + .0155)) + nd * .0135 - nd * .0, (.0026, .033, .0016), 'Rubber', .3, bevel=.0004, seg=1, rot=(0, 0, -ang)) if False else None
    tw = Vector((math.cos(ang), -math.sin(ang), 0))
    nc = Vector((gx, gy, HZ + .0155)) + nd * .0125
    p.box(nc, (.0028, .0335, .0016), 'Rubber', .3, bevel=.0004, seg=1, rot=(0, 0, -ang))
    disc(p, (gx, gy, HZ + .0155), (0, 0, 1), .0042, .0028, 'Steel', segs=14)
    fa = math.radians(-135 + 45 * 4.5)
    fd = Vector((math.sin(fa), math.cos(fa), 0))
    p.box(Vector((gx, gy, HZ + .0195)) + fd * .0395, (.0085, .0105, .0075), 'ValveRed', .4, bevel=.0012, seg=1, rot=(0, 0, -fa))
    crust(p, (gx, HY + .0365, HZ), (0, 1, 0), .0105, .014, 62, amp=.2)
    # ---------------- ISOLATE plate on the wall under the valve
    flat_plate(p, 2.84, 1.905, ZW, .09, .06, LAYOUT['ISOLATE']['uv'], 'ISOLATE plate')
    return p.finalise(new_col, origin=(1.7, HY, HZ))


# ------------------------------------------------------------------ riser module
def build_riser():
    p = Part('AW_FeedRiser', seed=300)
    r = .040
    path = [(3.125, HY, RZ), (RX, HY, RZ), (RX, 7.08, RZ), (1.70, 7.08, RZ), (1.70, 7.08, .80)]
    pts = fillet_path([Vector(q) for q in path], lambda i: {1: .05, 2: .12, 3: .12}[i], n=10)
    p.tube(pts, r, 'Bronze', .5, sides=16)
    # union at the header joint: nut, collar, gasket, nut
    hex_nut(p, (3.089, HY, RZ), (1, 0, 0), .058, .014, 'Bronze')
    ring(p, (3.103, HY, RZ), (1, 0, 0), .0, .0315, .006, 'Bronze', segs=22)
    ring(p, (3.109, HY, RZ), (1, 0, 0), .0, .0300, .0025, 'Rubber', segs=22, tile=.3)
    hex_nut(p, (3.1115, HY, RZ), (1, 0, 0), .058, .014, 'Bronze')
    crust(p, (3.089, HY, RZ), (1, 0, 0), .034, .030, 70, amp=.3)
    stalactite(p, (3.10, HY - .0385, RZ + .010), .040, .005, 17.0)
    # gasketed flange joint on the vertical run (y 2.95) with four bolts
    for k, (yy, r0, r1, mat) in enumerate([(2.940, .0, .066, 'Bronze'), (2.9525, .0, .0605, 'Rubber'), (2.955, .0, .066, 'Bronze')]):
        h = .0125 if mat == 'Bronze' else .0025
        ring(p, (RX, yy, RZ), (0, 1, 0), .038, r1, h, mat, segs=30, tile=.3 if mat == 'Rubber' else .5)
    for a in range(4):
        aa = a * PI / 2 + PI / 4
        bx, bz = RX + .052 * math.cos(aa), RZ + .052 * math.sin(aa)
        p.lathe([(.0037, 0), (.0037, .040)], 'Steel', .5, pos=(bx, 2.933, bz), axis=(0, 1, 0), segs=8)
        bolt_head(p, (bx, 2.9675, bz), (0, 1, 0), .014, .008)
        hex_nut(p, (bx, 2.9265, bz), (0, 1, 0), .014, .008, 'Steel')
    crust(p, (RX, 2.905, RZ), (0, 1, 0), .040, .036, 71, amp=.35)
    stalactite(p, (RX - .05, 2.941, RZ + .02), .050, .0065, 18.0)
    stalactite(p, (RX + .04, 2.941, RZ + .036), .030, .005, 19.0)
    # end flange onto the existing roof feed (ends at z 0.80)
    ring(p, (1.70, 7.08, .80), (0, 0, 1), .0, .0, .0, 'Bronze') if False else None
    disc(p, (1.70, 7.08, .80 + .0), (0, 0, -1), .070, .012, 'Bronze', segs=28)
    ring(p, (1.70, 7.08, .80 + .012), (0, 0, 1), .0, .0, .0, 'Rubber') if False else None
    return p.finalise(new_col, origin=(RX, HY, RZ))


# ------------------------------------------------------------------ build
CFG = {
    1: dict(strap_y=(.78, 1.50), lug=(1, -1), ears=((1, 1), (1, 1)), label_y=1.14, outlet='hose', inlet='union',
            runs=[(PI / 2 - .35, 1.965, 1.72, .010, .006, 1.0), (PI / 2 + .55, 1.965, 1.80, .008, .004, 2.0)]),
    2: dict(strap_y=(.83, 1.56), lug=(-1, 1), ears=((1, 1), (1, 1)), label_y=1.20, outlet='cap', inlet='flange', skew=.03,
            runs=[(PI / 2 + .10, 1.965, 1.70, .012, .006, 3.0)]),
    3: dict(strap_y=(.80, 1.53), lug=(1, 1), ears=((1, 1), (1, 1)), label_y=1.17, outlet='bend', inlet='reducer',
            runs=[(PI / 2 - .62, 1.965, 1.75, .010, .005, 4.0), (PI / 2 + .30, 1.965, 1.82, .007, .004, 5.0)]),
}
made = []
for i, cx in enumerate(VESSELS, start=1):
    made.append(build_vessel(i, cx, CFG[i]))
made.append(build_header())
made.append(build_riser())

# flag what the new modules supersede in the review scene
SUPERSEDED = ['air_water Filter manifold', 'air_water Filter manifold inlet 0.9', 'air_water Filter manifold inlet 1.7', 'air_water Filter manifold inlet 2.5',
              'air_water Filter wall mount 0.9', 'air_water Filter wall mount 1.7', 'air_water Filter wall mount 2.5', 'air_water Roof to filter downfeed']
for n in SUPERSEDED:
    bpy.data.objects[n]['aw_retired'] = True
txt = bpy.data.texts.new('aw_retired_objects.txt'); txt.write('\n'.join(SUPERSEDED))

stats = {o.name: L.stats(o) for o in made}
tot = sum(s['tris'] for s in stats.values())
raw = {'parts': {}, 'materials': L.RECORDS, 'warnings': WARN}
for o in made:
    raw['parts'][o.name] = dict(stats[o.name], pivotAuthoring=list(o['pivotAuthoring']), materialSlots=[m.get('ward_slot') for m in o.data.materials])
raw['totalTris'] = tot
(OUT / 'build-stats-raw.json').write_text(json.dumps(raw, indent=2))
for o in made:
    print(o.name, stats[o.name]['tris'], 'tris', stats[o.name]['sizeA'])
print('TOTAL', tot, 'WARN', WARN)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'airwater-filters-source-v1.blend'), compress=True)
print('BUILD_SAVED')
