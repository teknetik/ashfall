# fx_m3.py: the Milestone 3 fixtures (model-bench, 21 Nov 2026): salvage tray, scrap bin, solvent jar, bench tester
# with its probes and lamp, nanite press with its lever, vents and gauge, mould rack with the pistol-tang mould and its
# charge, cure lamp on its arm, schematic sheet on the card board, holster, and the pose marks for the places the step
# table had no mark for. Ids are the ones data/steps.json and bench/make_greybox.py use (fixtures/PARTS.md, M3 rulings).
# Every builder works in the fixture's own frame (metres, Z up, -Y toward the player) and places the nodes on the
# bench from layout.json, as fx_parts.py does.
import math, json, os
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree
import mbk
from mbk import G, MT, CT, AP, RG, MM, X, Y, Z, O, T, R4, R3, put, W, Wd, bench_pose, join, box, turned, ring_prof, extrude_x, extrude_y, extrude_z
from fx_parts import reg, sub, sweep_closed, rrect_path, densify, BOARD

FAM = 'fixtures'
PROG = mbk.PROG
PROBE = json.load(open(os.path.join(PROG, 'fixtures', 'layout', 'm3_probe.json')))
NOTES = {}          # numbers other parts of the build and the check read (press heights, mould frame, ...)


# ====================================================================== helpers
def bake_xf(objs):
    for o in objs:
        if o is None:
            continue
        o.data.transform(o.matrix_world); o.matrix_world = Matrix.Identity(4)
    return objs


def xf(o, M):
    o.data.transform(Matrix(M)); o.data.update()
    return o


def capped_sweep(name, path, normals, prof, mat):
    """sweep_closed with its first and last rings filled: a closed solid when the profile runs from one face to another."""
    o = sweep_closed(name, path, normals, prof, mat)
    n = len(path); k = len(prof)
    bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
    for col in (0, k - 1):
        try:
            bm.faces.new([bm.verts[i * k + col] for i in range(n)])
        except ValueError:
            pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(o.data); bm.free()
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def mats_by(o, fn):
    """Give each face the material index fn(face centre, normal) returns."""
    for p in o.data.polygons:
        p.material_index = fn(p.center, p.normal)
    o.data.update()
    return o


def with_mats(o, mats):
    o.data.materials.clear()
    for m in mats:
        o.data.materials.append(m)
    return o


def smooth01(v):
    v = max(0.0, min(1.0, v))
    return v * v * (3 - 2 * v)


def rect_ring(cx, cy, hx, hy, r, z, n=6):
    pts = []
    for qx, qy, a0 in ((hx - r, hy - r, 0), (-hx + r, hy - r, 90), (-hx + r, -hy + r, 180), (hx - r, -hy + r, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + qx + r * math.cos(a), cy + qy + r * math.sin(a), z))
    return pts


def custom_rig(F, short, parent_obj, bones, rides, params, root=None):
    """A rig the kit does not make: several bones moved together by one clip per parameter.
    bones: [(name, head, tail, parent, ref)] in WORLD coordinates; rides: {object: bone};
    params: [(param, [bones], pose_fn(arm, v), loc_bones, scale_bones, note, extra dict)]."""
    arm = mbk.new_armature('%s_%s_rig' % (F.name, short), bones)
    for o, bn in rides.items():
        mbk.bone_parent(o, arm, bn)
        if 'sh' in o:
            d = json.loads(o['sh']); d['rides'] = bn; o['sh'] = json.dumps(d)
    bpy.context.view_layer.update()
    mw = arm.matrix_world.copy()
    arm.parent = parent_obj; arm.matrix_parent_inverse = parent_obj.matrix_world.inverted(); arm.matrix_world = mw
    keep = {}
    for (p, bl, fn, lb, sb, note, extra) in params:
        keep[p + '_param'] = list(bl)

    def bake():
        for (p, bl, fn, lb, sb, note, extra) in params:
            mbk.bake_pose_action(arm, p + '_param', list(bl), lambda v, fn=fn: fn(arm, v), keys=25, loc=list(lb), scale=list(sb))
    F.custom_arms.append((arm, bake, keep))
    joints = []
    for (p, bl, fn, lb, sb, note, extra) in params:
        e = {'id': '%s.%s' % (F.name, p), 'node': arm.name, 'bone': None, 'bones': list(bl), 'action': p + '_param', 'type': 'custom',
             'min': 0.0, 'max': 1.0, 'unit': 'ratio', 'continuous': False, 'rest': 0.0, 'parent_bone': root or bones[0][0], 'requires': {},
             'parts': sorted({json.loads(o['sh'])['id'] for o, bn in rides.items() if bn in bl and 'sh' in o}), 'note': note}
        e.update(extra or {})
        F.extra_params.append(e)
        joints.append({'param': p, 'type': e['type'], 'min': 0, 'max': 1, 'unit': 'ratio', 'continuous': False, 'bones': list(bl)})
    arm['anymachine'] = json.dumps({'joints': joints})
    return arm


def qy(angle):
    """Rotation about a bone's own +Y (its joint axis)."""
    return Quaternion((0, 1, 0), angle)


def set_bone(arm, name, rot=None, loc=None, scale=None):
    pb = arm.pose.bones[name]; pb.rotation_mode = 'QUATERNION'
    if rot is not None:
        pb.rotation_quaternion = rot
    if loc is not None:
        pb.location = loc
    if scale is not None:
        pb.scale = scale


def load_mesh(fam, objname, newname):
    """A copy of another family's mesh (from its exported .blend), its materials dropped."""
    path = os.path.join(PROG, fam, 'export', fam + '.blend')
    before = set(bpy.data.materials)
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.meshes = [objname]
    me = dst.meshes[0]
    me.name = newname
    me.materials.clear()
    for m in set(bpy.data.materials) - before:
        if m.users == 0:
            bpy.data.materials.remove(m)
    o = bpy.data.objects.new(newname, me)
    bpy.context.scene.collection.objects.link(o)
    return o


def world_of(fam, objname):
    d = PROBE['grip_core'] if objname == 'grip_core' else None
    if d is None:
        for k, v in PROBE.get('materials', {}).items():
            if v['node'] == objname:
                d = v
    return Matrix(d['matrix_world'])


# ====================================================================== salvage tray
def build_tray(F, M):
    Wf, Hf, Rf, t = 0.272, 0.172, 0.016, 0.0009
    pts, nrm = rrect_path(Wf, Hf, Rf, 6)
    cx_, cz_, rb = 0.0128, 0.0266, 0.0021
    prof = [(0.0, 0.0), (0.0013, 0.0030), (0.0108, 0.0246)]
    for a in (-100, -55, -10, 35, 80, 125, 170):
        prof.append((cx_ + rb * math.cos(math.radians(a)), cz_ + rb * math.sin(math.radians(a))))
    prof += [(0.0101, 0.0252), (0.0009, 0.0034), (-t, t)]
    tray = capped_sweep('tray', pts, nrm, prof, M['tray_enamel'])
    from mathutils import noise as _nz
    G.displace(tray, lambda co: co + _nz.noise_vector(co * 18 + Vector((21.3, 9.9, 5.1))) * 0.0006 * smooth01((co.z - 0.0015) / 0.006))
    # a dent in the front left wall and a kink in the rim at the back right
    def dents(co):
        for (dx, dy, dz, r, d) in ((-0.10, -0.095, 0.016, 0.022, 0.0028), (0.11, 0.098, 0.026, 0.016, 0.0018)):
            q = Vector((dx, dy, dz)); k = max(0.0, 1 - (co - q).length / r)
            if k > 0:
                c = Vector((co.x, co.y, 0)); c = c.normalized() if c.length > 1e-6 else Vector((0, 0, 0))
                co = co - c * d * k * k
        return co
    G.displace(tray, dents)
    G.shade(tray, 40)
    put(tray, bench_pose('fixtures_tray'))
    reg(tray, 'tray', 'Salvage tray', 'steel', 'medium', steps=['s0.salvage', 's4.charge'])
    fz = t + 0.0001
    # the servo stands on its feet in the right half (its node origin is the middle of its base)
    mbk.seat(tray, 'servo', M_local=T((0.0565, 0.004, fz)) @ R4('Z', 8), pose=True, accepts=['servo.case_body'])
    # the two alloy sheets lie stacked in the left half (sheet A at the mark; sheet B on it, the bench's #b variant);
    # a sheet's node origin is the middle of the whole 120 x 90 sheet on its underside
    mbk.seat(tray, 'alloy', M_local=T((-0.069, 0.014, fz)) @ R4('Z', -4), pose=True, accepts=['materials.sheet_a', 'materials.sheet_b'])
    # the nanite vial on its side at the front left, mouth to the left (its origin is the middle of its base)
    mbk.seat(tray, 'vial', M_local=T((-0.012, -0.064, fz + 0.0121)) @ R4('Y', -90), pose=True, accepts=['materials.vial'])
    F.set_of[tray.name] = 'd'
    return tray


# ====================================================================== scrap bin
def build_bin(F, M):
    prof = [(0.0, 0.0), (0.0, 0.086), (0.0012, 0.094), (0.0040, 0.0995), (0.0100, 0.1004), (0.0135, 0.0996), (0.0160, 0.0993), (0.1300, 0.0993),
            (0.1345, 0.1004), (0.1378, 0.1030), (0.1392, 0.1050), (0.1382, 0.1062), (0.1362, 0.1052), (0.1350, 0.1024), (0.1335, 0.0982),
            (0.0160, 0.0980), (0.0128, 0.0962), (0.0122, 0.0900), (0.0134, 0.0860), (0.0122, 0.0820), (0.0122, 0.0560), (0.0136, 0.0530),
            (0.0122, 0.0500), (0.0122, 0.0)]
    b = turned('bin', prof, 48, M['bin_paint'], axis=Z)
    with_mats(b, [M['bin_paint'], M['bin_rust']])

    def inside(c, n):
        r = math.hypot(c.x, c.y)
        radial = Vector((c.x, c.y, 0)).normalized() if r > 1e-6 else Vector((0, 0, 0))
        if c.z > 0.0115 and r < 0.0992 and (n.dot(radial) < -0.2 or n.z > 0.5):
            return 1
        return 0
    mats_by(b, inside)
    # beaten about: dents in the wall, out of round, the rim hammered unevenly
    from mathutils import noise
    def bash(co):
        r = math.hypot(co.x, co.y)
        if r < 0.05:
            return co
        a = math.atan2(co.y, co.x)
        h = max(0.0, (co.z - 0.015) / 0.125)
        d = noise.noise(Vector((math.cos(a) * 3.0, math.sin(a) * 3.0, co.z * 14))) * 0.0028 * (0.4 + h)
        d += 0.0016 * math.cos(2 * a + 0.6) * h
        for (a0, z0, rr, dd) in ((0.9, 0.09, 0.03, 0.0045), (-2.4, 0.05, 0.025, 0.0035), (2.6, 0.125, 0.02, 0.003)):
            da = math.atan2(math.sin(a - a0), math.cos(a - a0)) * 0.1
            k = max(0.0, 1 - math.hypot(da, co.z - z0) / rr)
            d -= dd * k * k
        s = (r + d) / r
        return Vector((co.x * s, co.y * s, co.z))
    G.displace(b, bash)
    G.shade(b, 40)
    put(b, bench_pose('fixtures_bin'))
    reg(b, 'bin', 'Scrap bin', 'steel', 'medium', steps=['s2.board', 's2.gears', 's6.slide'])
    # where scrap is set down: in the opening just under the rim, so it is seen going in from the wide shot (bench, 21 Nov)
    mbk.mark(b, 'seat_scrap', (0, 0, 0.110), Z)
    F.set_of[b.name] = 'd'
    return b


# ====================================================================== solvent jar
JAR = dict(r=0.062, h=0.112, wall=0.003, mouth=0.0525, fluid=0.052)      # lowered 21 Nov: the gimbal's bath and the quench show over it


def build_jar(F, M):
    r, h, w, rm = JAR['r'], JAR['h'], JAR['wall'], JAR['mouth']
    outer = [(0.0, 0.0), (0.0, r - 0.012), (0.0015, r - 0.004), (0.006, r), (h - 0.028, r), (h - 0.016, r - 0.004), (h - 0.010, rm + 0.0035),
             (h - 0.004, rm + 0.0035), (h - 0.003, rm + 0.0055), (h, rm + 0.0045), (h, rm + 0.0005)]
    inner = [(h - 0.003, rm), (h - 0.010, rm), (h - 0.016, r - w - 0.004), (h - 0.028, r - w), (0.008, r - w), (0.005, r - w - 0.006), (0.005, 0.0)]
    glass = turned('jar_glass', outer + inner, 32, M['glass'], axis=Z)
    G.shade(glass, 50)
    fl = JAR['fluid']
    fluid = turned('jar_fluid', [(0.0051, 0.0), (0.0051, r - w - 0.0062), (0.0082, r - w - 0.0002), (fl - 0.0012, r - w - 0.0002), (fl, r - w - 0.0015),
                                (fl - 0.0004, r - w - 0.008), (fl - 0.0004, 0.0)], 32, M['solvent'], axis=Z)
    G.shade(fluid, 50)
    # the lid, flipped open on its wire bail behind the jar: glass disc with an orange seal
    lid = turned('lid', [(0.0, 0.0), (0.0, rm + 0.0045), (0.003, rm + 0.0045), (0.006, rm - 0.004), (0.010, 0.0)], 32, M['glass'], axis=Z)
    seal = ring_prof('seal', [(-0.0012, rm - 0.0005), (-0.0012, rm + 0.0040), (0.0, rm + 0.0045), (0.0, rm - 0.0005)], 32, M['seal_rubber'], axis=Z)
    # hinge axis along X behind the mouth; the lid stands open 105 degrees back
    hy, hz = rm + 0.0095, h + 0.0035
    Hg = T((0, hy, hz)) @ R4('X', -105) @ T((0, -hy, -hz))
    for o in (lid, seal):
        xf(o, Hg @ T((0, 0, h + 0.0013)))
    wire = M['clip_wire']
    pcs = [glass, fluid, lid, seal]
    # neck ring with two ears at the back, the lid frame loop and the lever
    pcs.append(G.ring('neck_ring', (0, 0, h - 0.0085), Z, rm + 0.0047, 0.0011, 40, 6, wire))
    for sx in (-1, 1):
        pcs.append(AP.wire('ear', [(sx * 0.016, rm + 0.004, h - 0.0085), (sx * 0.017, hy, h - 0.006), (sx * 0.017, hy, hz)], 0.0022, wire, segs=6))
    zl = h + 0.0013 + 0.0105
    lw = AP.wire('lidwire', [(-0.017, hy, hz), (-0.020, rm * 0.4, zl), (-0.012, -rm * 0.55, zl), (0.0, -rm * 0.65, zl), (0.012, -rm * 0.55, zl),
                             (0.020, rm * 0.4, zl), (0.017, hy, hz)], 0.0022, wire, segs=6)
    xf(lw, Hg)
    pcs.append(lw)
    lever = AP.wire('lever', [(-0.017, hy, hz), (-0.022, hy + 0.006, hz - 0.012), (-0.022, hy + 0.010, hz - 0.040), (0.022, hy + 0.010, hz - 0.040),
                              (0.022, hy + 0.006, hz - 0.012), (0.017, hy, hz)], 0.0024, wire, segs=6)
    pcs.append(lever)
    bake_xf(pcs)
    jar = join('jar', pcs)
    put(jar, bench_pose('fixtures_jar'))
    reg(jar, 'jar', 'Solvent jar', 'glass', 'medium', steps=['s3.bath', 's4.open'])
    # where a part is set down to be swirled: on the floor of the jar, under the solvent
    # where a part is set down to be swirled: its underside 12 mm under the solvent's surface, so most of it shows (bench)
    mbk.mark(jar, 'seat_swirl', (0, 0, fl - 0.012), Z)
    mbk.mark(jar, 'fluid_top', (0, 0, fl), Z)
    F.set_of[jar.name] = 'd'
    return jar


# ====================================================================== bench tester
TS = dict(yf=-0.042, yb=0.034, h=0.108, ytop=-0.014, zb=0.006, w=0.160)
PZ0 = 0.0115                      # the probes' back end (just above the plugs of their leads)


def tester_face(u, v, out=0.0):
    """A point on the sloped front face: u across (X), v up the slope from its foot, out along the outward normal."""
    yf, zb, ytop, h = TS['yf'], TS['zb'], TS['ytop'], TS['h']
    d = Vector((0, ytop - yf, h - zb)); L = d.length; d.normalize()
    n = Vector((0, -d.z, d.y))
    return Vector((u, yf, zb)) + d * v + n * out, d, n


def build_tester(F, M):
    yf, yb, h, ytop, zb, w = TS['yf'], TS['yb'], TS['h'], TS['ytop'], TS['zb'], TS['w']
    prof = [(yf, 0.0), (yb, 0.0), (yb, h), (ytop, h), (yf, zb)]
    body = extrude_x('tbody', prof, -w / 2, w / 2, M['tester_paint'])
    # the front panel is let in: a shallow tray round its edge
    p0, d, n = tester_face(0, 0.004)
    rec = G.prism('_rec', G.rounded_rect(w - 0.016, (Vector((0, ytop - yf, h - zb)).length - 0.012), 0.004), 0.004, p0 + d * ((Vector((0, ytop - yf, h - zb)).length - 0.012) / 2) + n * 0.0008,
                  X, d, n, None, w0=-0.0018)
    body = G.boolean(body, [rec])
    G.bevel(body, 0.0022, 2, angle=35)
    pcs = [body]
    feet = []
    for sx in (-1, 1):
        for sy in (yf + 0.012, yb - 0.010):
            feet.append(G.cyl('foot', (sx * 0.065, sy, -0.0001), (sx * 0.065, sy, 0.0035), 0.006, 12, M['bakelite'], chamfer=0.0008))
    bake_xf(feet)
    # amber lamp: brass bezel (the lens is its own part)
    lp, d, n = tester_face(-0.050, 0.078)
    bez = turned('bez', [(0.0, 0.0115), (0.0018, 0.0122), (0.0035, 0.0108), (0.0036, 0.0088), (0.0028, 0.0084), (0.0028, 0.0)], 24, M['brass'], axis=n, origin=lp - n * 0.0005)
    lens = turned('lens', [(0.0, 0.0084), (0.0030, 0.0082), (0.0055, 0.0068), (0.0075, 0.0040), (0.0083, 0.0)], 20, M['tester_lens'], axis=n, origin=lp + n * 0.0026)
    # buzzer grille: a punched disc over a black cloth
    gp, d, n = tester_face(0.0, 0.074)
    cloth = G.cyl('cloth', gp - n * 0.0004, gp + n * 0.0003, 0.0215, 28, M['bakelite'])
    holes = [(0.0, 0.0, 0.0016)]
    for ring_r, k in ((0.0068, 6), (0.0134, 12)):
        for i in range(k):
            a = 2 * math.pi * i / k + (0.26 if k == 12 else 0.0)
            holes.append((ring_r * math.cos(a), ring_r * math.sin(a), 0.0016 if ring_r < 0.019 else 0.0013))
    grille = G.plate('grille', G.circle(0.0225, 32), 0.0011, gp + n * 0.0008, X, d, n, holes=holes, mat=M['tester_paint'], w0=-0.00055, hole_segs=8)
    # toggle switch: hex nut on a threaded bush and a bat lever, thrown down (off)
    sp, d, n = tester_face(0.050, 0.078)
    nut = AP.nut('tnut', 0.0062, 0.0105, 0.0026, M['brass'], at=tuple(sp), axis=tuple(n))
    bush = G.cyl('bush', sp, sp + n * 0.0068, 0.0031, 14, M['needle'])
    bat = G.cyl('bat', sp + n * 0.0060, sp + n * 0.0060 + (n - d * 0.45).normalized() * 0.016, 0.0016, 10, M['needle'], r1=0.0021, chamfer=0.0006)
    # binding posts, red and black collars, brass caps
    posts = []
    for u, col in ((-0.024, M['wire_red']), (0.024, M['wire_black'])):
        pp, d, n = tester_face(u, 0.030)
        posts.append(AP.nut('pn', 0.006, 0.011, 0.003, M['brass'], at=tuple(pp), axis=tuple(n)))
        posts.append(turned('pcol', [(0.0025, 0.0062), (0.0090, 0.0062), (0.0095, 0.0050), (0.0095, 0.0)], 16, col, axis=n, origin=pp))
        posts.append(AP.knurled_band('pcap', 0.0105, 0.0055, 18, mat=M['brass'], at=tuple(pp + n * 0.0095), axis=tuple(n)))
        posts.append(turned('ptop', [(0.0, 0.0052), (0.0012, 0.0050), (0.0016, 0.0)], 16, M['brass'], axis=n, origin=pp + n * 0.0150))
        NOTES.setdefault('tester_posts', []).append(tuple(pp + n * 0.004))
    # corner screws on the panel
    scr = []
    L = Vector((0, ytop - yf, h - zb)).length
    for u in (-0.068, 0.068):
        for v in (0.008, L - 0.008):
            sp2, d, n = tester_face(u, v)
            scr.append(AP.screw('cs', 0.003, 0.004, head='pan', drive='slot', head_d=0.0056, head_h=0.0016, mat=M['bolt'], thread=False, segs=10,
                                at=tuple(sp2 + n * 0.0002), axis=tuple(n), turn=math.radians(30 * u / 0.068 + 60 * v)))
    # carrying handle on the top: a strap of steel bent over two lugs
    hpath = [(-0.050, 0.010, h), (-0.046, 0.010, h + 0.014), (-0.030, 0.010, h + 0.022), (0.030, 0.010, h + 0.022), (0.046, 0.010, h + 0.014), (0.050, 0.010, h)]
    handle = G.tube_path('handle', [Vector(p) for p in G.chaikin(hpath, 2, closed=False)], 0.0032, 10, M['bakelite'])
    lugs = [box('lug', (sx * 0.050 - 0.006, 0.004, h - 0.0005), (sx * 0.050 + 0.006, 0.016, h + 0.004), M['tester_paint'], bevel=0.0008) for sx in (-1, 1)]
    # side clips on the right for the probes, and the leads from the posts to the clipped probes
    xs = w / 2
    PX, PY = (xs + 0.0068, -0.008), (xs + 0.0068, 0.008)
    NOTES['probe_xy'] = (PX, PY)
    clips = []
    for zc in (0.040, 0.082):
        for (px, py) in (PX, PY):
            # the kit's clip holds its rod along its local Y with the mouth along `axis`: mouth out of the box, rod vertical
            c = AP.clip('pclip', 0.007, 0.0006, 0.0052, M['needle'], at=(px - 0.0058, py, zc), axis=(1, 0, 0), ref=(0, 1, 0))
            clips.append(c)
        clips.append(box('cplate', (xs - 0.0003, -0.016, zc - 0.0045), (xs + 0.0016, 0.016, zc + 0.0045), M['needle'], bevel=0.0003))
    leads = []
    for i, ((px, py), col) in enumerate(((PX, M['wire_red']), (PY, M['wire_black']))):
        a = Vector(NOTES['tester_posts'][i])
        end = Vector((px, py, PZ0 - 0.0080))
        mid1 = a + Vector((0.020 + 0.010 * i, -0.030 - 0.008 * i, -0.010))
        mid2 = Vector((xs + 0.040 + 0.006 * i, -0.050 + 0.010 * i, 0.003))
        mid3 = Vector((xs + 0.028, py - 0.010, 0.004))
        pts = G.bezier(a, mid1, mid2, mid3, 10) + G.bezier(mid3, mid3 + Vector((-0.010, 0.006, 0.0)), end - Vector((0.004, 0, 0.004)), end, 6)[1:]
        pts = [Vector(p) if i_ == 0 else Vector((p.x, p.y, max(p.z, 0.0021))) for i_, p in enumerate(pts)]
        leads.append(G.tube_path('lead', pts, 0.0019, 8, col))
        leads.append(turned('plug', [(0.0, 0.0), (0.0, 0.0028), (0.0055, 0.0030), (0.0078, 0.0022), (0.0078, 0.0)], 12, M['brass'], axis=Z, origin=end))
    bake_xf([bez, cloth, grille, nut, bush, bat] + posts + scr + [handle] + lugs + clips + leads)
    t = join('tester', pcs + feet + [bez, cloth, grille, nut, bush, bat] + posts + scr + [handle] + lugs + clips + leads)
    G.shade(t, 35)
    Mw = bench_pose('fixtures_tester')
    put(t, Mw)
    reg(t, 'tester', 'Bench tester', 'steel', 'medium', steps=['s3.test'])
    # the lamp lens: its own node (the bench drives its emission)
    lens.name = 'tester_lamp'
    put(lens, Mw)
    sub(lens, 'tester_lamp', 'Tester lamp', 'tester', 'glass', 'tiny')
    # the probes: one tool, two probes side by side in the clips, tips up; a brass bridge holds them 16 mm apart
    pr = build_probes(M, PX, PY)
    put(pr, Mw)
    CT.tool(pr, FAM, 'tester_probes', 'Tester probes', verbs=['Point'], tags=['tool:probe'], parent='tester', material='copper', mass='light',
            loose=False, steps=['s3.test'], note='both probes as one tool; the tip is the red probe\'s needle; the leads stay on the box (the probes plug in)')
    CT.tip(pr, W(t, (PX[0], PX[1], NOTES['probe_tip_z'])), Wd(t, (0, 0, 1)))
    CT.grab(pr, W(t, (PX[0], 0.0, 0.062)))
    G.set_origin(pr, W(t, (PX[0], 0.0, PZ0)))
    mbk.clear_local(pr, (0, 0, 0.060))
    mbk.mark(t, 'probe_rest', (PX[0], 0.0, PZ0), Z)
    for o in (t, lens, pr):
        F.set_of[o.name] = 'd'
    F.uv_weights[pr.name] = 1.4
    return t


def build_probes(M, PX, PY):
    pcs = []
    z0 = PZ0
    for (px, py), col in ((PX, M['wire_red']), (PY, M['wire_black'])):
        o = Vector((px, py, 0))
        pcs.append(turned('sock', [(z0, 0.0), (z0, 0.0026), (z0 + 0.006, 0.0029), (z0 + 0.008, 0.0035), (z0 + 0.008, 0.0)], 12, M['brass'], axis=Z, origin=o))
        pcs.append(AP.spring('relief', 0.020, 0.0062, 0.0008, 7, col, per_turn=8, wire_segs=5, at=(px, py, z0 + 0.008)))
        # turned wooden handle 4.5 mm in radius between the clips, swelling a little at the top for the fingers
        pcs.append(turned('hdl', [(z0 + 0.026, 0.0), (z0 + 0.026, 0.0035), (z0 + 0.028, 0.0044), (z0 + 0.086, 0.0044), (z0 + 0.092, 0.0050),
                                  (z0 + 0.100, 0.0046), (z0 + 0.104, 0.0034), (z0 + 0.104, 0.0)], 14, M['probe_wood'], axis=Z, origin=o))
        pcs.append(G.ring('band', (px, py, z0 + 0.0815), Z, 0.0045, 0.0007, 14, 5, col))
        pcs.append(turned('fer', [(z0 + 0.103, 0.0), (z0 + 0.103, 0.0030), (z0 + 0.112, 0.0026), (z0 + 0.118, 0.0012), (z0 + 0.118, 0.0)], 12, M['brass'], axis=Z, origin=o))
        pcs.append(turned('ndl', [(z0 + 0.117, 0.0), (z0 + 0.117, 0.0008), (z0 + 0.138, 0.0007), (z0 + 0.142, 0.0)], 8, M['needle'], axis=Z, origin=o))
    NOTES['probe_tip_z'] = z0 + 0.142
    # the bridge: a bent brass strip soldered round both handles above the clips
    for zb_ in (z0 + 0.097,):
        pcs.append(box('bridge', (PX[0] - 0.0014, PX[1] + 0.004, zb_ - 0.003), (PX[0] + 0.0014, PY[1] - 0.004, zb_ + 0.003), M['brass'], bevel=0.0004))
    bake_xf(pcs)
    return join('tester_probes', pcs)


# ====================================================================== mould dies (shared by the rack and the press)
DIE = dict(hx=0.060, hy=0.073, H=0.034, tongue=0.003)


_CORE = {}


def grip_core_live():
    """grip.core as it is in grip/export/grip.blend now (its node matrix and world bounds in P): read once per build,
    so a republished grip moves the cavity and the seat mark with it."""
    if not _CORE:
        path = os.path.join(PROG, 'grip', 'export', 'grip.blend')
        kinds = (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.armatures, bpy.data.actions, bpy.data.node_groups)
        before = [set(k) for k in kinds]
        with bpy.data.libraries.load(path, link=False) as (src, dst):
            dst.objects = list(src.objects)            # the whole family, so the core's parents place it
        coll = bpy.data.collections.new('_grip_tmp'); bpy.context.scene.collection.children.link(coll)
        for x in dst.objects:
            if x is not None:
                coll.objects.link(x)
        bpy.context.view_layer.update()
        o = next(x for x in dst.objects if x is not None and x.name.startswith('grip_core') and x.type == 'MESH' and '__' not in x.name)
        mw = o.matrix_world.copy()
        dg = bpy.context.evaluated_depsgraph_get()
        me_eval = bpy.data.meshes.new_from_object(o.evaluated_get(dg))      # with its modifiers, as the check sees it
        _CORE['mods'] = [m.type for m in o.modifiers]
        pts = [mw @ v.co for v in me_eval.vertices]
        _CORE['matrix'] = mw
        _CORE['min'] = [min(p[i] for p in pts) for i in range(3)]
        _CORE['max'] = [max(p[i] for p in pts) for i in range(3)]
        _CORE['mesh'] = me_eval
        for x in dst.objects:
            if x is not None:
                bpy.data.objects.remove(x, do_unlink=True)
        bpy.data.collections.remove(coll)
        for blk, b0 in zip(kinds, before):          # only what the load brought in
            for d in list(blk):
                if d not in b0 and d.users == 0 and d is not _CORE['mesh']:
                    blk.remove(d)
        print('[fx_m3] grip.core modifiers', _CORE['mods'], 'verts', len(me_eval.vertices), 'from grip.blend: origin', [round(x, 5) for x in mw.translation], 'bounds', [round(x, 5) for x in _CORE['min']], [round(x, 5) for x in _CORE['max']])
    return _CORE


def core_in_die():
    """Matrix taking the pistol/grip frame P into a die's frame: core lying on its +Y side (P +Y up), P X -> -X,
    P Z -> +Y, the parting plane P Y = 0 on the die's top face, the core's outline centred."""
    g = grip_core_live()
    cx = (g['min'][0] + g['max'][0]) / 2
    cz = (g['min'][2] + g['max'][2]) / 2
    A = Matrix(((-1, 0, 0, cx), (0, 0, 1, -cz), (0, 1, 0, DIE['H']), (0, 0, 0, 1)))
    return A


def grow(o, offset, name):
    """Move every vertex `offset` along its normal, toward the outside of its own shell (ray parity decides which way
    is out: the core's normals do not all face out). Negative offset shrinks."""
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    tree = BVHTree.FromBMesh(bm)
    d_ = Vector((0.31, 0.27, 0.91)).normalized()

    def inside(q):
        cnt, org = 0, q.copy()
        for _ in range(64):
            hit = tree.ray_cast(org, d_)
            if hit[0] is None:
                break
            cnt += 1; org = hit[0] + d_ * 1e-6
        return cnt % 2 == 1
    flips, moves = 0, []
    for v in bm.verts:
        n = v.normal.copy()
        if n.length < 1e-9:
            moves.append(Vector()); continue
        if inside(v.co + n * offset) != (offset < 0):
            n = -n; flips += 1
        moves.append(n * offset)
    for v, d in zip(bm.verts, moves):
        v.co += d
    bm.to_mesh(o.data); bm.free()
    G.clean(o, 1e-6, recalc=True)
    print('[fx_m3] %s grown %.2f mm, %d vertex normals turned' % (name, offset * 1000, flips))
    return o


def core_cutter(name, offset=0.0009, ratio=1.0, target=None):
    """The grip core in the die frame, each of its shells grown by the flash clearance: a LIST of cutters to subtract
    one after another (its shells intersect each other, and one cutter made of intersecting shells cuts like an
    exclusive or). The first is the main body."""
    g = grip_core_live()
    o = bpy.data.objects.new(name, g['mesh'].copy())
    bpy.context.scene.collection.objects.link(o)
    o.data.materials.clear()
    o.data.transform(core_in_die() @ g['matrix'])
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bm.to_mesh(o.data); bm.free()
    shells = shell_split(o)
    shells.sort(key=lambda q: -G._volume(q))
    out = []
    for k, q in enumerate(shells):
        q.name = '%s_%d' % (name, k)
        if ratio < 1.0 and k == 0:
            md = q.modifiers.new('dec', 'DECIMATE'); md.ratio = ratio; md.use_collapse_triangulate = True
            G.apply_mods(q)
        if offset:
            grow(q, offset, q.name)
        out.append(q)
    return out


def shell_split(o):
    """Loose parts of a mesh object as separate objects (the original is reused for the first)."""
    bm = bmesh.new(); bm.from_mesh(o.data)
    bm.verts.ensure_lookup_table()
    seen, groups = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, grp = [v], []
        seen.add(v.index)
        while stack:
            x = stack.pop(); grp.append(x.index)
            for e in x.link_edges:
                w = e.other_vert(x)
                if w.index not in seen:
                    seen.add(w.index); stack.append(w)
        groups.append(set(grp))
    bm.free()
    if len(groups) < 2:
        return [o]
    out = []
    for k, gset in enumerate(groups):
        bm = bmesh.new(); bm.from_mesh(o.data)
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in gset], context='VERTS')
        me = bpy.data.meshes.new('%s_s%d' % (o.name, k)); bm.to_mesh(me); bm.free()
        q = bpy.data.objects.new(me.name, me); bpy.context.scene.collection.objects.link(q)
        q.matrix_world = o.matrix_world.copy()
        out.append(q)
    bpy.data.objects.remove(o)
    print('[fx_m3] core cutter: %d shells, volumes %s' % (len(out), [round(G._volume(q) * 1e6, 2) for q in out]))
    return out


def sprue_point():
    s = PROBE['materials']['materials.core_sprue']['helpers']['materials_core_sprue__mark_snap']
    S = core_in_die() @ Matrix(s)
    p = S.translation.copy(); d = S.to_3x3() @ Vector((0, 0, 1))
    d.z = 0.0; d.normalize()
    return p, d


def die_block(name, mat, z0, z1, cavity=True, offset=0.0009, ratio=1.0, target=5000):
    hx, hy = DIE['hx'], DIE['hy']
    blk = box(name, (-hx, -hy, z0), (hx, hy, z1), mat)
    G.bevel(blk, 0.0012, 1)
    if cavity:
        cuts = core_cutter('_core_cut', offset, ratio, target)
        blk = G.boolean(blk, cuts)
        sp, sd = sprue_point()
        a = sp - sd * 0.006; b = sp + sd * 0.060
        ch = G.cyl('_sprue', (a.x, a.y, DIE['H']), (b.x, b.y, DIE['H']), 0.0036, 14)
        blk = G.boolean(blk, [ch])
    return blk


def die_keys(o, pattern, z_bottom=0.0):
    """Key the underside of a lower die: a tongue (cross or bar) and two dowel holes. pattern = (tongues, holes)."""
    tongues, holes = pattern
    add = []
    for (x0, y0, x1, y1) in tongues:
        add.append(box('_tg', (x0, y0, z_bottom - DIE['tongue']), (x1, y1, z_bottom + 0.0004), None))
    if add:
        o = G.boolean(o, add, 'UNION')
    cuts = [G.cyl('_dw', (hx_, hy_, z_bottom - 0.004), (hx_, hy_, z_bottom + 0.011), 0.0043, 14) for (hx_, hy_) in holes]
    if cuts:
        o = G.boolean(o, cuts)
    return o


KEY_TANG = ([(-0.045, -0.0063, 0.045, 0.0063), (-0.0063, -0.065, 0.0063, 0.065)], [(0.040, -0.050), (-0.040, 0.050)])
KEY_B = ([(-0.0063, -0.065, 0.0063, 0.065)], [(0.030, 0.030), (-0.030, -0.030)])
KEY_C = ([(-0.045, 0.024, 0.045, 0.036)], [(0.0, -0.050), (0.0, 0.050)])


def lift_slots(o, mat=None):
    """Two milled grip slots in the die's sides, so it can be lifted with the fingers."""
    hx, hy, H = DIE['hx'], DIE['hy'], DIE['H']
    cuts = [box('_ls', (sx * hx - 0.006, -0.025, H * 0.38), (sx * hx + 0.006, 0.025, H * 0.62)) for sx in (-1, 1)]
    return G.boolean(o, cuts)


def build_mould_tang(F, M):
    H = DIE['H']
    die = die_block('mould_tang', M['mould_steel_tang'], 0.0, H, ratio=1.0, offset=0.0)   # the core's own shells, cut one by one
    die = die_keys(die, KEY_TANG)
    die = lift_slots(die)
    # stamped mark on the front: a little raised tang shape boss is enough at 0.3 m (a ridge in the material is not)
    G.shade(die, 35)
    return die


def build_charge(M):
    """The heap of alloy offcuts in grey nanite paste, in the lower die's cavity (die frame)."""
    H = DIE['H']
    cores = core_cutter('_paste_core', offset=-0.00005, ratio=0.4)
    core = cores[0]
    for q in cores[1:]:
        bpy.data.objects.remove(q)
    slab = box('charge_paste', (-0.07, -0.08, 0.0), (0.07, 0.08, H - 0.0045), M['nanite_paste'])
    paste = G.boolean(slab, [core], 'INTERSECT')
    with_mats(paste, [M['nanite_paste']])
    pcs = [paste]
    for (nm, c, yaw, tilt, z) in (('materials_sheet_a_offcut_1', (0.0262, -0.0150), 90.0, 3.0, H - 0.0056),
                                  ('materials_sheet_a_offcut_2', (0.0258, 0.0170), 92.5, -2.5, H - 0.0040)):
        o = load_mesh('materials', nm, '_' + nm)
        loc = Vector(PROBE['materials']['materials.' + nm.split('materials_')[1]]['local_min']) + Vector(PROBE['materials']['materials.' + nm.split('materials_')[1]]['local_max'])
        xf(o, T((c[0], c[1], z)) @ R4('Z', yaw) @ R4('X', tilt) @ T(-loc / 2))
        with_mats(o, [M['paint_orange']])
        pcs.append(o)
    ch = join('mould_charge', pcs)
    G.shade(ch, 35)
    return ch


def build_moulds(F, M):
    """The mould rack beside the press with three keyed lower dies; the tang mould on top, its charge in it."""
    H = DIE['H']
    p = 0.0                           # rails: angle iron, horizontal flange inward
    RX, RY, RH = 0.071, 0.080, 0.168
    st = M['frame_steel']
    pcs = [box('rbase', (-RX, -RY, 0.0), (RX, RY, 0.004), st, bevel=0.0008)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            x0, y0 = sx * RX, sy * RY
            pcs.append(box('post_a', (min(x0, x0 - sx * 0.016), min(y0, y0 - sy * 0.002), 0.004), (max(x0, x0 - sx * 0.016), max(y0, y0 - sy * 0.002), RH), st, bevel=0.0004))
            pcs.append(box('post_b', (min(x0, x0 - sx * 0.002), min(y0, y0 - sy * 0.016), 0.004), (max(x0, x0 - sx * 0.002), max(y0, y0 - sy * 0.016), RH), st, bevel=0.0004))
    levels = [0.056, 0.112]
    for z in levels:
        for sx in (-1, 1):
            pcs.append(box('rail_h', (min(sx * 0.050, sx * (RX - 0.002)), -RY + 0.002, z - 0.003), (max(sx * 0.050, sx * (RX - 0.002)), RY - 0.002, z), st, bevel=0.0004))
            pcs.append(box('rail_v', (min(sx * (RX - 0.002), sx * RX), -RY + 0.002, z - 0.003), (max(sx * (RX - 0.002), sx * RX), RY - 0.002, z + 0.010), st, bevel=0.0004))
    # a stop bar at the back of each level so the dies do not slide out behind
    for z in [0.004] + levels:
        pcs.append(box('stop', (-0.050, RY - 0.006, z), (0.050, RY - 0.002, z + 0.008), st, bevel=0.0004))
    for o in pcs:
        pass
    rack = join('mouldrack', pcs)
    G.shade(rack, 35)
    Mr = bench_pose('fixtures_mouldrack')
    put(rack, Mr)
    reg(rack, 'mouldrack', 'Mould rack', 'steel', 'medium', steps=['s4.mould'])
    F.set_of[rack.name] = 'd'
    # dies: c at the bottom, b in the middle, the tang mould on top (open above: lift it straight out)
    dz = {'mould_c': 0.004 + DIE['tongue'] + 0.0001, 'mould_b': levels[0] + DIE['tongue'] + 0.0001, 'mould_tang': levels[1] + DIE['tongue'] + 0.0001}
    mb = die_block('mould_b', M['mould_steel'], 0.0, H, cavity=False)
    mb = G.boolean(mb, [box('_cb', (-0.040, -0.050, H - 0.012), (0.012, 0.050, H + 0.01)), box('_cb2', (0.0115, -0.050, H - 0.012), (0.040, -0.025, H + 0.01)),
                        G.cyl('_cbs', (-0.020, -0.050, H), (-0.020, -0.080, H), 0.0035, 12)])
    mb = die_keys(mb, KEY_B); mb = lift_slots(mb)
    mc = die_block('mould_c', M['mould_steel'], 0.0, H, cavity=False)
    mc = G.boolean(mc, [G.cyl('_cc', (0, 0.005, H - 0.016), (0, 0.005, H + 0.01), 0.030, 40), G.cyl('_cs', (0, -0.020, H), (0, -0.080, H), 0.0035, 12)])
    mc = G.boolean(mc, [G.cyl('_cp', (0, 0.005, H - 0.0165), (0, 0.005, H - 0.002), 0.010, 24)], 'UNION')
    mc = die_keys(mc, KEY_C); mc = lift_slots(mc)
    tang = build_mould_tang(F, M)
    charge = build_charge(M)
    for o in (mb, mc):
        G.shade(o, 35)
    for o, k in ((mc, 'mould_c'), (mb, 'mould_b'), (tang, 'mould_tang')):
        put(o, Mr @ T((0, 0, dz[k])))
    put(charge, Mr @ T((0, 0, dz['mould_tang'])))
    sub(mb, 'mould_b', 'Mould (bracket)', 'mouldrack', 'steel', 'medium')
    sub(mc, 'mould_c', 'Mould (bush)', 'mouldrack', 'steel', 'medium')
    reg(tang, 'mould_tang', 'Pistol-tang mould', 'steel', 'medium', kind='part', parent='mouldrack', loose=False, steps=['s4.mould', 's4.charge', 's4.press', 's4.open'],
        note='the lower die; the top die rides the press platen. Keyed: a cross tongue and two dowel holes on its underside fit only the press bed')
    mbk.clear_local(tang, (0, 0, 0.045))
    mbk.grab(tang, (0, -DIE['hy'] + 0.004, H - 0.004))
    mbk.zone(tang, 'cavity', (0, -0.003, H - 0.0105), (0.047, 0.058, 0.0105))
    CT.wipe(tang, 'cavity', zone='cavity', label='Nanite dust and scale from the last pour (s4.mould brushes it out)')
    # the grip core lying in the cavity when the mould opens (the grip family's node takes this pose)
    CT.pose_mark(tang, 'seat_core', tang.matrix_world @ core_in_die() @ grip_core_live()['matrix'], accepts=['grip.core'])
    # alloy sheet A (what is left of it with its two offcuts) laid on the open mould over the cavity, along it
    CT.pose_mark(tang, 'seat_charge', tang.matrix_world @ T((0.0, 0.0, H + 0.0001)) @ R4('Z', 90), accepts=['materials.sheet_a'])
    sp, sd = sprue_point()
    mbk.mark(tang, 'port', (sp.x + sd.x * 0.030, -DIE['hy'], H), -Y)
    reg(charge, 'mould_charge', 'Charge', 'alloy', 'tiny', kind='consumable', parent='mould_tang', steps=['s4.charge', 's4.press', 's4.open'],
        note='alloy offcuts in grey nanite paste; hidden at the start, shown after s4.charge, gone when the mould opens')
    NOTES['absent'] = NOTES.get('absent', []) + ['mould_charge']
    for o in (mb, mc, tang, charge):
        F.set_of[o.name] = 'd'
    F.uv_weights.update({tang.name: 1.4, charge.name: 1.3})
    NOTES['die_z'] = dz
    return rack


# ====================================================================== nanite press
PR = dict(bx=0.115, by=0.150, bh=0.024, yb=-0.045, bed=0.012, cx=0.042, cy0=0.072, cy1=0.140, hz0=0.240, hz1=0.370, hy0=-0.080,
          ram=0.015, rp=0.057, sz=0.310, sy=0.0065, stroke=0.110, lever_deg=110.0, lever_len=0.235)
# 21 Nov: the head 40 mm higher and a 110 mm stroke, so the open platen no longer hides the cavity, the charge and the pour
# from the press shot (bench)


def press_paint():
    """Where the press's painted marks are, in its own frame (the same numbers build_press uses): the green band beside
    the sight tube (x0, x1, z0, z1, face y) and the hopper's level line height."""
    P_ = PR
    hz0 = P_['hz0']
    tx, tz0, tz1 = -0.022, hz0 + 0.022, hz0 + 0.102
    trav = (tz1 - tz0 - 0.016) - 0.011
    base = tz0 + 0.008 + 0.005
    zpart = P_['bh'] + P_['bed'] + DIE['H']
    return dict(band=(tx - 0.008, tx + 0.008, base + 0.55 * trav, base + 0.80 * trav, P_['hy0']), line=zpart + 0.052 - 0.009, parting=DIE['H'])


def build_press(F, M):
    P_ = PR
    H = DIE['H']
    zbed = P_['bh'] + P_['bed']                      # top of the bed: the die sits here
    zpart = zbed + H                                 # parting plane
    yb = P_['yb']
    NOTES['press'] = dict(zbed=zbed, zpart=zpart)
    Y_ = M['press_yellow']; S_ = M['press_steel']; D_ = M['press_dark']
    # ---------------- base plate with hazard stripes, four hold-down bolts
    base = extrude_z('pbase', G.rounded_rect(2 * P_['bx'], 2 * P_['by'], 0.020, 5), 0.0, P_['bh'], Y_)
    G.bevel(base, 0.003, 2)
    pcs = [base]
    bolts = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            at = (sx * (P_['bx'] - 0.018), sy * (P_['by'] - 0.018), P_['bh'])
            bolts.append(AP.washer('bw', 0.0105, 0.021, 0.0018, M['bolt'], segs=14, at=at))
            bolts.append(AP.screw('bb', 0.010, 0.008, head='hex', drive='none', head_d=0.017, head_h=0.0065, mat=M['bolt'], thread=False,
                                  at=(at[0], at[1], at[2] + 0.0018), turn=math.radians(13 * (sx + 3 * sy)), point=False))
    # ---------------- column and head: one casting (side profile extruded across), the ram bore through the head
    cy0, cy1, hz0, hz1, hy0 = P_['cy0'], P_['cy1'], P_['hz0'], P_['hz1'], P_['hy0']
    prof = [(cy1 + 0.010, P_['bh'] - 0.0005), (cy1 + 0.006, hz1 - 0.020), (cy1 - 0.010, hz1), (hy0 + 0.012, hz1), (hy0, hz1 - 0.012), (hy0, hz0 + 0.010),
            (hy0 + 0.010, hz0), (cy0 - 0.040, hz0), (cy0 - 0.006, hz0 - 0.030), (cy0, hz0 - 0.060), (cy0, P_['bh'] + 0.020), (cy0 - 0.014, P_['bh'] - 0.0005)]
    col = extrude_x('pcol', prof, -P_['cx'], P_['cx'], Y_)
    # narrower toward the front of the head (a casting is not a box)
    G.displace(col, lambda co: Vector((co.x * (1.0 - 0.6 * max(0.0, (cy0 - co.y)) * (1 if co.z > hz0 - 0.03 else 0)), co.y, co.z)))
    bore = box('_bore', (-P_['ram'] - 0.0006, yb - P_['ram'] - 0.0006, hz0 - 0.01), (P_['ram'] + 0.0006, yb + P_['ram'] + 0.0006, hz1 + 0.01))
    rack_slot = box('_rack', (-P_['ram'] + 0.0012, yb + P_['ram'] - 0.002, hz0 - 0.012), (P_['ram'] - 0.0012, yb + P_['ram'] + 0.0042, hz1 + 0.012))
    # vents: five slots across the head's front face; the glowing inserts are their own node
    vz = [hz0 + 0.030 + 0.016 * i for i in range(5)]
    slots = [box('_vs', (-0.004, hy0 - 0.005, z - 0.0026), (0.030, hy0 + 0.006, z + 0.0026)) for z in vz]
    shaft = G.cyl('_shaft', (-P_['cx'] - 0.01, P_['sy'], P_['sz']), (P_['cx'] + 0.01, P_['sy'], P_['sz']), 0.0102, 24)
    col = G.boolean(col, [bore, rack_slot] + slots + [shaft])
    G.bevel(col, 0.0035, 2, angle=35)
    pcs.append(col)
    # bosses round the shaft on both sides, and a gib plate with two screws on the head's front
    for sx in (-1, 1):
        pcs.append(ring_prof('boss', [(0.0, 0.0105), (0.0, 0.026), (0.006, 0.024), (0.0065, 0.0105)], 28, Y_, axis=Vector((sx, 0, 0)),
                             origin=(sx * (P_['cx'] - 0.0012), P_['sy'], P_['sz'])))
    gib = []
    for z in (hz0 + 0.004, hz1 - 0.004):
        pass
    # ---------------- bed: machined plate with a cross slot and two dowels
    bed = box('pbed', (-0.075, yb - 0.088, P_['bh'] - 0.0004), (0.075, yb + 0.088, zbed), S_)
    G.bevel(bed, 0.0009, 1)
    slot_c = [box('_sx', (-0.0453, yb - 0.0066, zbed - 0.004), (0.0453, yb + 0.0066, zbed + 0.01)),
              box('_sy', (-0.0066, yb - 0.0653, zbed - 0.004), (0.0066, yb + 0.0653, zbed + 0.01))]
    bed = G.boolean(bed, slot_c)
    pcs.append(bed)
    for (hx_, hy_) in KEY_TANG[1]:
        pcs.append(G.cyl('dowel', (hx_, yb + hy_, zbed - 0.002), (hx_, yb + hy_, zbed + 0.009), 0.0040, 14, S_, chamfer=0.0008))
    for sx in (-1, 1):
        for sy in (-1, 1):
            pcs.append(AP.screw('bs', 0.006, 0.006, head='socket', drive='hex', head_d=0.0095, head_h=0.006, mat=D_, thread=False, segs=12,
                                at=(sx * 0.066, yb + sy * 0.079, zbed), turn=math.radians(20 * sx + 50 * sy), point=False))
    # ---------------- sight tube with the pressure slug, on the left of the vents; the green band is painted behind it
    tx, tyf = -0.022, hy0 - 0.0045
    tz0, tz1 = hz0 + 0.022, hz0 + 0.102
    NOTES['gauge'] = dict(x=tx, y=tyf, z0=tz0 + 0.008, z1=tz1 - 0.008)
    trav = (tz1 - tz0 - 0.016) - 0.011
    blo, bhi = tz0 + 0.008 + 0.005 + 0.55 * trav, tz0 + 0.008 + 0.005 + 0.80 * trav
    NOTES['press_paint'] = dict(band=(tx - 0.008, tx + 0.008, blo, bhi, hy0), line=None)
    tube = ring_prof('tube', [(tz0 + 0.008, 0.0037), (tz0 + 0.008, 0.0042), (tz1 - 0.008, 0.0042), (tz1 - 0.008, 0.0037)], 16, M['glass'], axis=Z, origin=(tx, tyf, 0))
    fit = []
    for (z0_, z1_, up) in ((tz0, tz0 + 0.009, False), (tz1 - 0.009, tz1, True)):
        fit.append(AP.nut('tf', 0.009, 0.010, z1_ - z0_, M['brass'], at=(tx, tyf, z0_), axis=(0, 0, 1)))
        fit.append(box('tfb', (tx - 0.004, tyf, (z0_ + z1_) / 2 - 0.003), (tx + 0.004, hy0 + 0.0008, (z0_ + z1_) / 2 + 0.003), M['brass'], bevel=0.0005))
    cap = turned('tcap', [(tz1, 0.0), (tz1, 0.0045), (tz1 + 0.004, 0.0040), (tz1 + 0.006, 0.0), ], 14, M['brass'], axis=Z, origin=(tx, tyf, 0))
    slug = turned('slug', [(0.0, 0.0), (0.0, 0.0034), (0.0095, 0.0034), (0.0100, 0.0), ], 14, M['brass'], axis=Z, origin=(tx, tyf, tz0 + 0.0085))
    # ---------------- lock: a swing-over latch on the head's left side (static)
    lx = -0.0390                                    # the head's left face there (the casting narrows forward)
    lk = [G.cyl('lkp', (lx + 0.002, yb + 0.010, hz1 - 0.030), (lx - 0.008, yb + 0.010, hz1 - 0.030), 0.006, 16, D_, chamfer=0.001),
          extrude_x('lka', [(yb + 0.004, hz1 - 0.036), (yb + 0.016, hz1 - 0.036), (yb + 0.020, hz1 - 0.060), (yb + 0.004, hz1 - 0.074), (yb - 0.004, hz1 - 0.070),
                            (yb + 0.006, hz1 - 0.062), (yb + 0.006, hz1 - 0.030)], lx - 0.0065, lx - 0.0015, D_, bevel=0.0006),
          G.cyl('lkk', (lx - 0.004, yb - 0.001, hz1 - 0.070), (lx - 0.018, yb - 0.001, hz1 - 0.070), 0.0045, 14, M['bakelite'], chamfer=0.001)]
    # ---------------- hopper: a cup on a bracket at the front left of the bed, its spout to the mould's port
    sp, sd = sprue_point()
    port = Vector((sp.x + sd.x * 0.030, yb - DIE['hy'], zpart))
    cupc = Vector((port.x - 0.006, port.y - 0.034, zpart + 0.052))
    NOTES['hopper'] = cupc
    cup = ring_prof('cup', [(-0.024, 0.0055), (-0.022, 0.0090), (0.000, 0.0215), (0.0015, 0.0230), (0.0020, 0.0216), (0.0006, 0.0200), (-0.021, 0.0072), (-0.022, 0.0047)],
                    28, M['hopper_steel'], axis=Z, origin=cupc)
    spout_pts = [cupc + Vector((0, 0, -0.022)), cupc + Vector((0, 0, -0.034)), Vector((port.x, port.y - 0.012, zpart - 0.0035)), Vector((port.x, port.y - 0.0009, zpart - 0.0036))]
    spout = G.tube_path('spout', G.bezier(*spout_pts, n=10), 0.0024, 10, M['hopper_steel'])
    line_z = cupc.z - 0.009
    NOTES['press_paint']['line'] = line_z - cupc.z
    brk = [box('hbr', (cupc.x - 0.006, yb - 0.088 - 0.003, P_['bh'] - 0.0004), (cupc.x + 0.006, yb - 0.088, cupc.z - 0.016), M['hopper_steel'], bevel=0.0005),
           box('hbr2', (cupc.x - 0.006, cupc.y + 0.004, cupc.z - 0.020), (cupc.x + 0.006, yb - 0.088 - 0.0005, cupc.z - 0.016), M['hopper_steel'], bevel=0.0005),
           G.ring('hring', cupc + Vector((0, 0, -0.012)), Z, 0.013, 0.0012, 24, 6, M['hopper_steel'])]
    # stamped plate on the base: a riveted maker's plate
    plate = box('mplate', (-0.035, -P_['by'] - 0.0012, 0.006), (0.035, -P_['by'] + 0.0002, 0.019), M['brass'], bevel=0.0003)
    bake_xf(pcs + bolts + [tube, cap] + fit + lk + [cup, spout] + brk + [plate])
    body = join('press', pcs + bolts + fit + lk + [cup, spout] + brk + [plate, cap])
    with_mats(body, list(body.data.materials))
    G.shade(body, 35)
    Mw = bench_pose('fixtures_press')
    put(body, Mw)
    reg(body, 'press', 'Nanite press', 'steel', 'heavy', steps=['s4.mould', 's4.charge', 's4.press', 's4.open'])
    tube.name = 'press_gauge'
    put(tube, Mw)
    sub(tube, 'press_gauge', 'Press sight tube', 'press', 'glass', 'tiny')
    # ---------------- vents: the glowing inserts behind the slots (the bench drives their emission)
    vents = [box('vi', (-0.0025, hy0 + 0.0040, z - 0.0021), (0.0285, hy0 + 0.0052, z + 0.0021), M['vent_glow']) for z in vz]
    bake_xf(vents)
    vent = join('press_vents', vents)
    put(vent, Mw)
    sub(vent, 'press_vents', 'Press vents', 'press', 'glass', 'tiny')
    # ---------------- lever: shaft, hub, an outside gear and the bar with a wooden knob (rides the lever bone)
    sx_ = P_['cx'] + 0.0062
    hub = [G.cyl('shaft', (-P_['cx'] - 0.004, P_['sy'], P_['sz']), (sx_ + 0.030, P_['sy'], P_['sz']), 0.0099, 20, S_, chamfer=0.0008)]
    # the outside gear (the pinion's twin on the shaft): teeth as geometry
    nt_ = 18; rr, rt = 0.026, 0.0315
    gpts = []
    for i in range(nt_):
        a0 = 2 * math.pi * i / nt_
        for (da, r_) in ((0.0, rr), (0.06, rt), (0.22, rt), (0.28, rr)):
            gpts.append((r_ * math.cos(a0 + da), r_ * math.sin(a0 + da)))
    gear = G.prism('gear', gpts, 0.008, (sx_ + 0.0005, P_['sy'], P_['sz']), Y, Z, X, D_, w0=0.0)
    gear = G.boolean(gear, [G.cyl('_gh', (sx_ - 0.01, P_['sy'], P_['sz']), (sx_ + 0.02, P_['sy'], P_['sz']), 0.0100, 20)])
    hubr = turned('hub', [(0.0, 0.0100), (0.0, 0.0175), (0.003, 0.0185), (0.014, 0.0185), (0.016, 0.0165), (0.016, 0.0100)], 24, D_, axis=X, origin=(sx_ + 0.0090, P_['sy'], P_['sz']))
    # bar: 10 degrees forward of vertical at rest
    a = math.radians(10)
    dvec = Vector((0, -math.sin(a), math.cos(a)))
    hc = Vector((sx_ + 0.017, P_['sy'], P_['sz']))
    L = P_['lever_len']
    bar = G.cyl('bar', hc + dvec * 0.012, hc + dvec * (L - 0.050), 0.0070, 16, S_, chamfer=0.001)
    knob = turned('knob', [(0.0, 0.0), (0.0, 0.0085), (0.004, 0.0110), (0.030, 0.0125), (0.048, 0.0110), (0.054, 0.0060), (0.055, 0.0)], 18, M['probe_wood'],
                  axis=dvec, origin=hc + dvec * (L - 0.054))
    ferr = turned('kfer', [(0.0, 0.0), (0.0, 0.0090), (0.006, 0.0092), (0.006, 0.0)], 18, M['brass'], axis=dvec, origin=hc + dvec * (L - 0.058))
    bake_xf(hub + [gear, hubr, bar, knob, ferr])
    lever = join('press_lever', hub + [gear, hubr, bar, knob, ferr])
    G.shade(lever, 35)
    put(lever, Mw)
    sub(lever, 'press_lever', 'Press lever', 'press', 'steel', 'heavy')
    mbk.grab(lever, tuple(hc + dvec * (L - 0.025)))
    NOTES['lever_tip'] = tuple(hc + dvec * L)
    # ---------------- ram, rack, platen and top die (ride the ram bone), at the top of the stroke as found
    st = P_['stroke']
    zt0 = zpart + 0.00015                         # top die's face when closed (the seated mould stands 0.1 mm proud of the bed)
    ram_lo = zt0 + H + 0.014                      # top of the platen when closed
    ramb = box('ram', (-P_['ram'], yb - P_['ram'], ram_lo - 0.002), (P_['ram'], yb + P_['ram'], ram_lo + 0.232), S_, bevel=0.0008)
    teeth = []
    pitch = 0.0057
    n_t = int(0.200 / pitch)
    for i in range(n_t):
        z = ram_lo + 0.020 + i * pitch
        teeth.append(extrude_x('tooth', [(yb + P_['ram'] - 0.0003, z), (yb + P_['ram'] + 0.0032, z + 0.0012), (yb + P_['ram'] + 0.0032, z + 0.0024),
                                          (yb + P_['ram'] - 0.0003, z + 0.0040)], -P_['ram'] + 0.002, P_['ram'] - 0.002, D_))
    platen = box('platen', (-0.064, yb - 0.078, zt0 + H), (0.064, yb + 0.078, ram_lo), S_, bevel=0.0012)
    topdie = die_block('topdie', M['mould_steel'], DIE['H'], 2 * DIE['H'] - 0.0004, ratio=0.35)
    xf(topdie, T((0, yb, zt0 - DIE['H'])))
    # four cap screws holding the top die to the platen
    caps = [AP.screw('pc', 0.006, 0.006, head='socket', drive='hex', head_d=0.0095, head_h=0.006, mat=D_, thread=False, segs=12,
                     at=(sx * 0.054, yb + sy * 0.068, ram_lo), turn=math.radians(35 * sx + 20 * sy), point=False) for sx in (-1, 1) for sy in (-1, 1)]
    bake_xf([ramb] + teeth + [platen] + caps)
    ram = join('press_ram', [ramb] + teeth + [platen, topdie] + caps)
    with_mats(ram, list(ram.data.materials))
    xf(ram, T((0, 0, st)))                         # as found: the press open, platen at the top of its stroke
    G.shade(ram, 35)
    put(ram, Mw)
    sub(ram, 'press_ram', 'Press ram and top die', 'press', 'steel', 'heavy')
    # ---------------- the slug in the sight tube (kit rig: param pressure)
    slug.name = 'press_slug'
    put(slug, Mw)
    sub(slug, 'press_slug', 'Pressure slug', 'press', 'copper', 'tiny')
    # ---------------- rigs
    shaft_c = Mw @ Vector((0, P_['sy'], P_['sz']))
    ram_o = Mw @ Vector((0, yb, ram_lo + st))
    bones = [('press_lever_root', Mw @ Vector((0, 0, 0)), Mw @ Vector((0, 0.01, 0)), None, Z),
             ('press_lever', shaft_c, shaft_c + Wd(body, (1, 0, 0)) * 0.02, 'press_lever_root', Z),
             ('press_ram', ram_o, ram_o + Wd(body, (0, 0, 1)) * 0.02, 'press_lever_root', Y)]
    ang = math.radians(P_['lever_deg'])

    def pose_lever(arm, v):
        set_bone(arm, 'press_lever', rot=qy(ang * v))
        set_bone(arm, 'press_ram', rot=Quaternion(), loc=(0, -st * v, 0))
        bpy.context.view_layer.update()
    custom_rig(F, 'press_lever', body, bones, {lever: 'press_lever', ram: 'press_ram'},
               [('press_lever', ['press_lever', 'press_ram'], pose_lever, ['press_ram'], [],
                 '0 = open, lever 10 degrees forward of vertical, platen at the top of its %d mm stroke (as found); 1 = lever turned %d degrees '
                 'forward and down, the top die closed on the mould. The ram rides the lever through the rack and pinion (one clip moves both).'
                 % (st * 1000, P_['lever_deg']), {'stroke_mm': st * 1000, 'lever_deg': P_['lever_deg']})], root='press_lever_root')
    R = F.new_rig('press', body)
    R.slide('press_pressure', Mw @ Vector((tx, tyf, tz0 + 0.0085)), Wd(body, (0, 0, 1)), 0.0, trav, [slug])
    F.end_rig(R)
    F.param_notes['fixtures.press_pressure'] = {'band': [0.55, 0.80], 'note': 'the brass slug in the sight tube: 0 = no pressure (as found), 1 = top; '
                                                'the painted green band runs from 0.55 to 0.80, the s4.press sustain window. Not driven by the step table yet'}
    # ---------------- marks
    CT.pose_mark(body, 'seat_mould', Mw @ T((0, yb, zbed + 0.0001)), accepts=['fixtures.mould_tang'])
    CT.pose_mark(body, 'clear_mould', Mw @ T((0, yb - 0.010, zbed + 0.040)), accepts=['fixtures.mould_tang'])
    # the vial held over the hopper, tipped 115 degrees, its mouth over the cup
    dv = Vector((math.sin(math.radians(115)), 0, math.cos(math.radians(115))))
    mouth = cupc + Vector((0, 0, 0.034))
    CT.pose_mark(body, 'seat_pour', Mw @ T(mouth - dv * 0.062) @ R4('Y', 115), accepts=['materials.vial'])
    mbk.mark(body, 'hopper_line', (cupc.x, cupc.y + 0.019, line_z), -Y)
    gz = NOTES['gauge']
    mbk.mark(body, 'band_lo', (tx, hy0, blo), -Y)
    mbk.mark(body, 'band_hi', (tx, hy0, bhi), -Y)
    mbk.zone(body, 'vents', (0.013, hy0, vz[2]), (0.018, 0.003, 0.036))
    for o in (body, tube, vent, lever, ram, slug):
        F.set_of[o.name] = 'd'
    F.uv_weights.update({body.name: 1.1, lever.name: 1.2, ram.name: 1.1})
    return body


# ====================================================================== cure lamp
LP = dict(zs=0.068, L1=0.240, L2=0.240, hood=0.075, wrist_off=0.030)


def lamp_fk(psi, a1, a2, a3):
    """Joint positions in the lamp's own frame for yaw psi and the three hinge angles (radians, in the arm plane)."""
    u = Vector((math.cos(psi), math.sin(psi), 0)); z = Vector((0, 0, 1))
    S = Vector((0, 0, LP['zs']))
    d1 = u * math.cos(a1) + z * math.sin(a1)
    E = S + d1 * LP['L1']
    d2 = u * math.cos(a1 + a2) + z * math.sin(a1 + a2)
    Wr = E + d2 * LP['L2']
    d3 = u * math.cos(a1 + a2 + a3) + z * math.sin(a1 + a2 + a3)
    return S, E, Wr, d1, d2, d3, u


def lamp_ik(psi, r, zw):
    """Hinge angles that put the wrist at horizontal distance r and height zw, elbow up, the hood pointing down."""
    L1, L2 = LP['L1'], LP['L2']
    dz = zw - LP['zs']
    d = min(math.hypot(r, dz), L1 + L2 - 1e-4)
    c = (d * d - L1 * L1 - L2 * L2) / (2 * L1 * L2)
    q2 = -math.acos(max(-1.0, min(1.0, c)))
    q1 = math.atan2(dz, r) - math.atan2(L2 * math.sin(q2), L1 + L2 * math.cos(q2))
    q3 = -math.pi / 2 - q1 - q2
    return q1, q2, q3


def lamp_path(v):
    """(yaw, r, wrist height) along the swing: parked (0) to over the grip on the work mat (1)."""
    s = smooth01(v)
    psi = LP['psi0'] + (LP['psi1'] - LP['psi0']) * s
    r = LP['r0'] + (LP['r1'] - LP['r0']) * s
    zw = LP['z0'] + (LP['z1'] - LP['z0']) * s + 0.06 * math.sin(math.pi * s)
    return psi, r, zw


def build_lamp(F, M):
    P = M['lamp_paint']
    base_w = bench_pose('fixtures_lamp')
    # the target: the grip lying on the work mat at fixtures.workmat/seat_grip, emitter 100 mm over its top
    tgt_w = bench_pose('fixtures_workmat') @ Vector((-0.010, 0.020, 0.0))
    tgt = base_w.inverted() @ tgt_w
    LP['psi1'] = math.atan2(tgt.y, tgt.x)
    LP['r1'] = math.hypot(tgt.x, tgt.y)
    LP['z1'] = 0.0336 + 0.0193 + 0.100 + LP['hood'] + LP['wrist_off']
    LP['psi0'], LP['r0'], LP['z0'] = math.radians(-55), 0.22, 0.40
    a0 = lamp_ik(LP['psi0'], LP['r0'], LP['z0'])
    S, E, Wr, d1, d2, d3, u = lamp_fk(LP['psi0'], *a0)
    h = u.cross(Vector((0, 0, 1)))                # hinge axis: positive turns raise
    # base: a heavy turned casting with a felt ring underneath
    base = turned('lbase', [(0.0, 0.0), (0.0, 0.055), (0.0035, 0.0555), (0.006, 0.052), (0.014, 0.044), (0.020, 0.030), (0.024, 0.022), (0.026, 0.020),
                            (0.030, 0.019), (0.030, 0.0)], 36, P, axis=Z)
    G.shade(base, 40)
    # turret (yaw): post and clevis with a wing nut on the shoulder axis
    tur = [turned('tpost', [(0.0302, 0.0), (0.0302, 0.0120), (0.0330, 0.0125), (0.0530, 0.0095), (0.0555, 0.0090), (0.0555, 0.0)], 20, P, axis=Z)]
    for sg in (-1, 1):
        c = S + h * sg * 0.0085
        tur.append(G.cyl('cheek', c - h * sg * 0.0015 + Vector((0, 0, -0.012)), c + h * sg * 0.0015 + Vector((0, 0, -0.012)), 0.0085, 18, P))
        tur.append(G.cyl('cheek2', c - h * sg * 0.0015, c + h * sg * 0.0015, 0.0085, 18, P))
    wn = wing_nut(M, S + h * 0.0105, h)
    tur += wn
    bake_xf(tur)
    turret = join('lamp_turret', tur)
    # arm 1 and arm 2: steel tubes with flattened knuckle ends, a cable clipped along
    def arm_seg(name, a, b, dirv, nxt_hinge, side):
        # side: the arm's knuckles and tube stand to one side of the arm plane, the next arm's to the other
        o_ = h * side * 0.0040
        pcs = [G.cyl(name + '_t', a + dirv * 0.0092 + o_, b - dirv * 0.0092 + o_, 0.0045, 16, P)]
        for p_ in (a, b):
            pcs.append(G.cyl(name + '_k', p_ + h * side * 0.0008, p_ + h * side * 0.0068, 0.0095, 18, P, chamfer=0.0008))
        # the cable: a little off the tube, two clips
        off = h.cross(dirv).normalized() * -0.0085
        cp = [a + dirv * 0.012 + off * 0.8, a + dirv * 0.06 + off, b - dirv * 0.06 + off, b - dirv * 0.012 + off * 0.8]
        pcs.append(G.tube_path(name + '_c', G.bezier(*cp, n=8), 0.0023, 8, M['wire_black']))
        if nxt_hinge:
            pcs += wing_nut(M, b - h * side * 0.0075, -h * side)
        return pcs
    a1p = arm_seg('a1', S, E, d1, True, -1)
    a2p = arm_seg('a2', E, Wr, d2, True, 1)
    bake_xf(a1p + a2p)
    arm1 = join('lamp_arm1', a1p)
    arm2 = join('lamp_arm2', a2p)
    # head: knuckle tab, hood with a ribbed collar, emitter in its mouth (pointing along d3, down when parked)
    hp = Wr + d3 * LP['wrist_off']
    hood_axis = d3
    hpcs = [G.cyl('hk', Wr - h * 0.0068, Wr - h * 0.0008, 0.0090, 18, P, chamfer=0.0008),
            G.cyl('htab', Wr - h * 0.0038, hp + d3 * 0.006 - h * 0.0038, 0.0035, 12, P)]
    hood = turned('hood', [(0.0, 0.0), (0.0, 0.016), (0.004, 0.019), (0.016, 0.021), (0.022, 0.028), (0.050, 0.041), (0.074, 0.045), (0.075, 0.0465),
                           (0.0755, 0.0445), (0.074, 0.0435), (0.050, 0.0390), (0.024, 0.0265), (0.024, 0.0)], 32, P, axis=hood_axis, origin=hp)
    G.shade(hood, 45)
    rib = [G.ring('rib', hp + hood_axis * (0.006 + 0.0045 * k), hood_axis, 0.0195, 0.0011, 28, 5, P) for k in range(3)]
    emit = turned('emit', [(0.0, 0.0), (0.0, 0.0395), (0.0015, 0.0390), (0.004, 0.030), (0.0045, 0.0)], 32, M['lamp_emitter'], axis=-hood_axis, origin=hp + hood_axis * 0.0690)
    bake_xf(hpcs + [hood] + rib + [emit])
    head = join('lamp_head', hpcs + [hood] + rib + [emit])
    G.shade(head, 40)
    for o in (base, turret, arm1, arm2, head):
        put(o, base_w)
    reg(base, 'lamp', 'Cure lamp', 'steel', 'medium', steps=['s5.cure'])
    sub(turret, 'lamp_turret', 'Cure lamp turret', 'lamp', 'steel')
    sub(arm1, 'lamp_arm1', 'Cure lamp arm', 'lamp', 'steel')
    sub(arm2, 'lamp_arm2', 'Cure lamp arm', 'lamp', 'steel')
    CT.part(head, FAM, 'lamp_head', 'Cure lamp head', kind='fixture', parent='lamp', material='steel', mass='light', loose=True, steps=['s5.cure'],
            note='the whole swinging head; its emitter is the only face on the emissive material (M_fixtures_b_emissive): light that, not the hood')
    mbk.grab(head, tuple(hp + hood_axis * 0.030 + h * 0.02))
    # rig: yaw, shoulder, elbow, wrist, one clip
    Bw = lambda p_: base_w @ p_
    Dw = lambda d_: (base_w.to_3x3() @ d_).normalized()
    Zw = Dw(Vector((0, 0, 1)))
    bones = [('lamp_root', Bw(Vector((0, 0, 0.004))), Bw(Vector((0, 0.01, 0.004))), None, Zw),
             ('lamp_yaw', Bw(Vector((0, 0, 0.030))), Bw(Vector((0, 0, 0.030))) + Zw * 0.012, 'lamp_root', Dw(u)),
             ('lamp_shoulder', Bw(S), Bw(S) + Dw(h) * 0.012, 'lamp_yaw', Zw),
             ('lamp_elbow', Bw(E), Bw(E) + Dw(h) * 0.012, 'lamp_shoulder', Zw),
             ('lamp_wrist', Bw(Wr), Bw(Wr) + Dw(h) * 0.012, 'lamp_elbow', Zw)]

    def pose_arm(arm, v):
        psi, r, zw = lamp_path(v)
        q = lamp_ik(psi, r, zw)
        set_bone(arm, 'lamp_yaw', rot=qy(psi - LP['psi0']))
        set_bone(arm, 'lamp_shoulder', rot=qy(q[0] - a0[0]))
        set_bone(arm, 'lamp_elbow', rot=qy(q[1] - a0[1]))
        set_bone(arm, 'lamp_wrist', rot=qy(q[2] - a0[2]))
        bpy.context.view_layer.update()
    custom_rig(F, 'lamp', base, bones, {turret: 'lamp_yaw', arm1: 'lamp_shoulder', arm2: 'lamp_elbow', head: 'lamp_wrist'},
               [('lamp_arm', ['lamp_yaw', 'lamp_shoulder', 'lamp_elbow', 'lamp_wrist'], pose_arm, [], [],
                 '0 = parked: arm folded up beside its base, head hanging (as found); 1 = swung over the grip on the work mat '
                 '(fixtures.workmat/seat_grip), the emitter 100 mm above it, facing down. Yaw, shoulder, elbow and wrist move together on one clip.',
                 {'reaches': 'fixtures.workmat/seat_grip'})], root='lamp_root')
    for o in (base, turret, arm1, arm2, head):
        F.set_of[o.name] = 'd'
    return base


def wing_nut(M, at, axis):
    ax = Vector(axis).normalized()
    pcs = [AP.nut('wn', 0.0045, 0.008, 0.004, M['needle'], at=tuple(at), axis=tuple(ax))]
    ref = Vector((0, 0, 1)) if abs(ax.z) < 0.9 else Vector((1, 0, 0))
    e1 = (ref - ax * ax.dot(ref)).normalized()
    for sg in (-1, 1):
        c = Vector(at) + ax * 0.002 + e1 * sg * 0.0075
        pcs.append(G.cyl('wing', c - ax * 0.0006, c + ax * 0.0006, 0.0055, 12, M['needle']))
    return pcs


# ====================================================================== schematic sheet on the card board
SC = dict(w=0.250, h=0.300, nx=12, ny=14)


def sheet_curl(x, y):
    return 0.0032 * (max(0.0, -y) / SC['h']) ** 2 + 0.0012 * max(0.0, (x - 0.07) / 0.055) ** 2 * max(0.0, -y - 0.22) / 0.08


def region_centre(i):
    col, row = i % 2, i // 2
    return (-0.060 + 0.120 * col, -0.068 - 0.064 * row)


def build_schematic(F, M):
    w, h = SC['w'], SC['h']
    # node frame = the board's seat mark: X across the board, Y up it, Z out of it; the sheet's top edge at y = +0.004
    p_ = 0.0015
    L = R4('X', -BOARD['lean'])
    Mm = bench_pose('fixtures_board') @ L @ T((0.160, -p_ - 0.0004, BOARD['z0'] + BOARD['h'] - 0.012)) @ R4('X', 90)
    nx, ny = SC['nx'], SC['ny']
    verts, faces = [], []
    for j in range(ny + 1):
        for i in range(nx + 1):
            x = -w / 2 + w * i / nx; y = 0.004 - (h + 0.004) * j / ny
            verts.append((x, y, 0.0003 + sheet_curl(x, y)))
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    paper = G.mesh_obj('paper', verts, faces, M['paper'], recalc=False)
    bm = bmesh.new(); bm.from_mesh(paper.data)
    for f in bm.faces:
        if f.normal.z < 0:
            f.normal_flip()
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.0003)
    bm.normal_update()
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z < -0.5], context='FACES')
    bm.to_mesh(paper.data); bm.free()
    # the clip on the top edge, hung on a nail; the clip lamp on a gooseneck from the board's top frame
    clip = paper_clip(M, 0.034)
    lamp = clip_lamp(M)
    bake_xf([clip] + lamp)
    sch = join('schematic', [paper, clip] + lamp)
    G.shade(sch, 35)
    put(sch, Mm)
    CT.part(sch, FAM, 'schematic', 'Schematic', kind='fixture', parent='board', material='paper', mass='light', loose=True, steps=[],
            note='hand-drawn exploded view of the grip in eight regions (stages 0 to 7); params schematic_s0..s7 put a wax-pencil ring round a region '
                 '(0.5, the stage in hand) and a tick in it (1, done)')
    for i in range(8):
        cx, cy = region_centre(i)
        mbk.zone(sch, 'region_%d' % i, (cx, cy, 0.0005 + sheet_curl(cx, cy)), (0.057, 0.029, 0.002))
    # ring and tick per region: one skinned mesh, one bone each, scaled from nothing by the region's clip
    marks, bones = [], [('schematic_root', Mm @ Vector((0, 0, 0)), Mm @ Vector((0, 0.01, 0)), None, None)]
    pen = M['wax_pencil']
    for i in range(8):
        cx, cy = region_centre(i)
        rc = (cx - 0.044, cy + 0.017); tc = (cx + 0.036, cy - 0.015)
        pts = []
        for k in range(16):
            a = math.radians(100 + k * 24.6)
            rr_ = 0.0105 * (1 + 0.06 * math.sin(3 * a + i) + 0.03 * k / 15)
            pts.append(Vector((rc[0] + rr_ * math.cos(a) * 1.25, rc[1] + rr_ * math.sin(a), 0.0)))
        ring_ = G.band_path('ring', pts, 0.0016, 0.0002, lambda p, tg: Vector((0, 0, 1)), pen, closed=False)
        tk = [Vector((tc[0] - 0.007, tc[1] + 0.004, 0)), Vector((tc[0] - 0.002, tc[1] - 0.003, 0)), Vector((tc[0] + 0.001, tc[1] - 0.0045, 0)),
              Vector((tc[0] + 0.006, tc[1] + 0.003, 0)), Vector((tc[0] + 0.012, tc[1] + 0.012, 0))]
        tick = G.band_path('tick', G.chaikin(tk, 1, closed=False), 0.0019, 0.0002, lambda p, tg: Vector((0, 0, 1)), pen, closed=False)
        for o, nm, c in ((ring_, 'schematic_s%d_ring' % i, rc), (tick, 'schematic_s%d_tick' % i, tc)):
            G.displace(o, lambda co: Vector((co.x, co.y, co.z + 0.00085 + sheet_curl(co.x, co.y))))
            g = o.vertex_groups.new(name=nm); g.add(list(range(len(o.data.vertices))), 1.0, 'REPLACE')
            o.data.transform(Mm)
            cz = 0.0009 + sheet_curl(*c)
            bones.append((nm, Mm @ Vector((c[0], c[1], cz)), Mm @ Vector((c[0], c[1], cz + 0.004)), 'schematic_root', None))
            marks.append(o)
    mk = join('schematic_marks', marks)
    CT.part(mk, FAM, 'schematic_marks', 'Schematic ticks', kind='fixture', parent='schematic', material='paper', mass='tiny', loose=True,
            note='skinned on fixtures_schematic_rig; the bind pose shows every ring and tick, each clip at 0 shrinks its own to nothing')
    arm = mbk.new_armature('fixtures_schematic_rig', bones)
    mk.parent = arm
    mod = mk.modifiers.new('Armature', 'ARMATURE'); mod.object = arm
    bpy.context.view_layer.update()
    mw = arm.matrix_world.copy()
    arm.parent = sch; arm.matrix_parent_inverse = sch.matrix_world.inverted(); arm.matrix_world = mw
    keep = {}
    for i in range(8):
        keep['schematic_s%d_param' % i] = ['schematic_s%d_ring' % i, 'schematic_s%d_tick' % i]

    def bake():
        for i in range(8):
            rn, tn = keep['schematic_s%d_param' % i]

            def pose(v, rn=rn, tn=tn):
                sr = max(0.001, smooth01((v - 0.25) / 0.2)); stk = max(0.001, smooth01((v - 0.75) / 0.2))
                set_bone(arm, rn, rot=Quaternion(), scale=(sr, sr, sr))
                set_bone(arm, tn, rot=Quaternion(), scale=(stk, stk, stk))
                bpy.context.view_layer.update()
            mbk.bake_pose_action(arm, 'schematic_s%d_param' % i, [rn, tn], pose, keys=21, scale=[rn, tn])
    F.custom_arms.append((arm, bake, keep))
    joints = []
    for i in range(8):
        F.extra_params.append({'id': 'fixtures.schematic_s%d' % i, 'node': arm.name, 'bone': None, 'bones': keep['schematic_s%d_param' % i],
                               'action': 'schematic_s%d_param' % i, 'type': 'skinned', 'min': 0.0, 'max': 1.0, 'unit': 'ratio', 'continuous': False,
                               'parent_bone': 'schematic_root', 'requires': {}, 'parts': ['fixtures.schematic_marks'], 'rest': 0.0, 'bind_pose_value': 1.0,
                               'region': 'fixtures_schematic__zone_region_%d' % i,
                               'note': 'stage s%d: 0 = nothing drawn (as found), 0.5 = a wax-pencil ring round the region (the stage in hand), 1 = ring and tick (done). '
                                       'The skin\'s bind pose is 1.' % i})
        joints.append({'param': 'schematic_s%d' % i, 'type': 'skinned', 'min': 0, 'max': 1, 'unit': 'ratio', 'continuous': False})
    arm['anymachine'] = json.dumps({'joints': joints})
    for o in (sch, mk):
        F.set_of[o.name] = 'c'
    return sch


def paper_clip(M, width):
    """A small bulldog clip gripping the paper's top edge (frame: X along the edge, Y up, Z out of the board), hung on a nail."""
    prof = [(-0.0016, -0.016), (-0.0016, 0.004), (-0.0005, 0.0100), (0.0030, 0.0115), (0.0062, 0.0080), (0.0013, -0.0160),
            (0.0005, -0.0155), (0.0050, 0.0075), (0.0028, 0.0102), (-0.0004, 0.0090), (-0.0009, 0.0040), (-0.0009, -0.0155)]
    poly = [(z_, y_) for (z_, y_) in prof]
    body = G.prism('pclip', [(p[1], p[0]) for p in poly], width, (-width / 2, 0, 0), Y, Z, X, M['clip_black'], w0=0.0)
    G.shade(body, 30)
    hw = width / 2 - 0.004; r = 0.0008
    f = [(-hw, 0.0040, 0.0058), (-hw, -0.004, 0.0090), (-hw * 0.6, -0.022, 0.0110), (hw * 0.6, -0.022, 0.0110), (hw, -0.004, 0.0090), (hw, 0.0040, 0.0058)]
    b = [(-hw, 0.0040, -0.0010), (-hw, 0.012, -0.0018), (-hw * 0.5, 0.026, -0.0016), (hw * 0.5, 0.026, -0.0016), (hw, 0.012, -0.0018), (hw, 0.0040, -0.0010)]
    nail = G.cyl('nail', (0, 0.024, -0.0020), (0, 0.024, 0.0030), 0.0016, 10, M['bolt'], chamfer=0.0004)
    return join('pclip', [body, AP.wire('wf', f, 2 * r, M['clip_wire'], segs=6, smooth=1), AP.wire('wb', b, 2 * r, M['clip_wire'], segs=6, smooth=1), nail])


def clip_lamp(M):
    """A small clip-on lamp on a gooseneck from the board's top frame at the right, its shade over the sheet."""
    k = M['lamp_paint']
    top = 0.0135
    base = Vector((0.105, top + 0.0022, -0.0036))
    clamp = [box('cl', (0.095, top - 0.010, -0.0002), (0.115, top + 0.0022, 0.0018), k, bevel=0.0005),
             box('cl2', (0.095, top + 0.0002, -0.0110), (0.115, top + 0.0022, 0.0018), k, bevel=0.0005),
             box('cl3', (0.095, top - 0.008, -0.0110), (0.115, top + 0.0022, -0.0090), k, bevel=0.0005)]
    gn = [base, base + Vector((-0.005, 0.040, 0.010)), Vector((0.070, 0.085, 0.060)), Vector((0.040, 0.060, 0.095))]
    pts = G.bezier(*gn, n=18)
    neck = G.tube_path('neck', pts, 0.0032, 10, M['needle'])
    rings = [G.ring('gr', pts[i], (pts[i + 1] - pts[i - 1]).normalized(), 0.0033, 0.0006, 10, 4, M['needle']) for i in range(2, len(pts) - 2, 2)]
    tip = pts[-1]; d = (Vector((0.0, -0.11, 0.0)) - tip).normalized()
    shade = turned('cls', [(0.0, 0.0), (0.0, 0.0070), (0.006, 0.0090), (0.030, 0.0145), (0.040, 0.0160), (0.0405, 0.0150), (0.030, 0.0135), (0.006, 0.0080),
                           (0.006, 0.0)], 20, k, axis=d, origin=tip)
    bulb = turned('clb', [(0.030, 0.0), (0.030, 0.0080), (0.036, 0.0075), (0.039, 0.0)], 14, M['tester_lens'] if False else M['needle'], axis=d, origin=tip)
    return clamp + [neck, shade, bulb] + rings


# ====================================================================== holster on the bench's front edge
HOL = dict(x=-0.600, mouth=-0.0135)


def pistol_in_holster():
    """Pistol frame P in the holster (fixture frame: origin on the worktop's front edge): muzzle down, its top toward
    the bench, the grip pointing out at the player. P X -> +Z, P Y -> +X, P Z -> +Y."""
    R = Matrix(((0, 1, 0, 0.0), (0, 0, 1, -0.122), (1, 0, 0, -0.068), (0, 0, 0, 1)))
    return R


def build_holster(F, M):
    R = pistol_in_holster()
    # a smooth pouch round the front of the pistol (P X from the muzzle to just behind the trigger guard's front):
    # an envelope of the pistol's sections (fixtures/layout/m3_probe.json bins) at four stations, lofted
    stations = [(-0.137, -0.021, 0.021, 0.022, 0.088), (-0.100, -0.021, 0.021, 0.020, 0.088), (-0.030, -0.021, 0.021, -0.024, 0.088),
                (-0.018, -0.021, 0.021, -0.026, 0.088)]
    bins = PROBE['pistol']['bins_x']
    for (x, y0_, y1_, z0_, z1_) in stations:          # the envelope must hold the pistol there (it does by the bins on 21 Nov)
        for b in bins:
            if abs(b[0] - x) < 0.006:
                assert b[1][1] >= y0_ - 0.001 and b[2][1] <= y1_ + 0.001 and b[2][2] <= z1_ + 0.001, ('holster envelope', x, b)
    secs_in, secs_out = [], []
    xs = [-0.137 + (-0.018 + 0.137) * k / 11 for k in range(12)]

    def env(x):
        for (a, b) in zip(stations, stations[1:]):
            if a[0] <= x <= b[0]:
                f = (x - a[0]) / (b[0] - a[0])
                return [a[i] + (b[i] - a[i]) * f for i in range(1, 5)]
        return list(stations[-1][1:])
    for x in xs:
        ymin, ymax, zmin, zmax = env(x)
        g = 0.0030
        for (lst, t) in ((secs_in, 0.0), (secs_out, 0.0032)):
            cy = (ymin + ymax) / 2; cz = (zmin + zmax) / 2
            hy = (ymax - ymin) / 2 + g + t; hz = (zmax - zmin) / 2 + g + t
            lst.append([R @ Vector((x, q[0], q[1])) for q in rect_ring(cy, cz, hy, hz, 0.008 + t, 0.0, 4)])
    secs_out[0] = [p_ + (R.to_3x3() @ Vector((-0.003, 0, 0))) for p_ in secs_out[0]]      # the toe: the outer skin closes below the inner
    # mouth flare: the outer and inner top rings meet in a rolled lip; the toe closes both
    nr = len(secs_out[-1])
    secs = secs_out + [[p + (p - sum(secs_out[-1], Vector()) / nr) * 0.04 + Vector((0, 0, 0.0035)) for p in secs_out[-1]]] + secs_in[::-1]
    shell = G.loft('holster_shell', secs, M['holster_leather'], caps=(True, True))
    G.shade(shell, 45)
    # belt loop at the back (bench side) over the hook, and a thumb strap with a snap
    loop_pts = [Vector((0.0, -0.0300, -0.100)), Vector((0.0, -0.0290, -0.060)), Vector((0.0, -0.0275, -0.040)), Vector((0.0, -0.0220, -0.0335)),
                Vector((0.0, -0.0150, -0.0355)), Vector((0.0, -0.0120, -0.045)), Vector((0.0, -0.0150, -0.060)), Vector((0.0, -0.0270, -0.100))]
    inplane = lambda p, tg: Vector((1, 0, 0)).cross(tg).normalized() if tg.length > 1e-9 else Vector((0, 1, 0))
    loops = []
    for dx in (0.0, 0.030):
        loops.append(G.band_path('loop', [p + Vector((dx, 0, 0)) for p in G.chaikin(loop_pts, 2, closed=False)], 0.020, 0.0026, inplane,
                                 M['holster_leather'], closed=False))
    # the hook: a steel strap screwed to the worktop, bent down over the edge and out into a J
    hk = [Vector((0.0, 0.019, 0.0015)), Vector((0.0, 0.002, 0.0015)), Vector((0.0, -0.0015, -0.002)), Vector((0.0, -0.0015, -0.048)),
          Vector((0.0, -0.005, -0.056)), Vector((0.0, -0.013, -0.056)), Vector((0.0, -0.0175, -0.044))]
    hook = G.band_path('hook', G.chaikin(hk, 2, closed=False), 0.016, 0.003, inplane, M['forged'], closed=False)
    hook2 = G.band_path('hook2', [p + Vector((0.030, 0, 0)) for p in G.chaikin(hk, 2, closed=False)], 0.016, 0.003, inplane, M['forged'], closed=False)
    screws = [AP.screw('hs', 0.004, 0.006, head='dome', drive='cross', head_d=0.008, head_h=0.0024, mat=M['bolt'], thread=False, segs=10,
                       at=(dx, y_, 0.003), turn=math.radians(20 + 40 * k)) for k, (dx, y_) in enumerate(((0.0, 0.011), (0.030, 0.011)))]
    bake_xf(screws)
    for o in loops + [hook, hook2] + screws:
        xf(o, T((-0.015, 0, 0)))
    hol = join('holster', [shell] + loops + [hook, hook2] + screws)
    G.shade(hol, 40)
    Mw = bench_pose('fixtures_holster')
    put(hol, Mw)
    reg(hol, 'holster', 'Holster hook', 'canvas', 'light', steps=['s7.leave'],
        note='a leather holster hanging from a hook on the worktop\'s front edge, left of the work surface')
    CT.pose_mark(hol, 'seat_pistol', Mw @ R, accepts=['pistol.frame'])
    F.set_of[hol.name] = 'd'
    return hol


# ====================================================================== places that had no mark (bench/README.md)
UV_D = {'fixtures_mouldrack': 0.5, 'fixtures_mould_b': 0.5, 'fixtures_mould_c': 0.5, 'fixtures_holster': 0.6, 'fixtures_bin': 0.7,
        'fixtures_tray': 0.8, 'fixtures_jar': 0.8, 'fixtures_lamp': 0.8, 'fixtures_lamp_turret': 0.8, 'fixtures_lamp_arm1': 0.8, 'fixtures_lamp_arm2': 0.8,
        'fixtures_tester_probes': 1.6, 'fixtures_tester_lamp': 1.2, 'fixtures_mould_tang': 1.5, 'fixtures_mould_charge': 1.4, 'fixtures_press_lever': 1.3}


def add_places(F):
    for k, v in UV_D.items():
        F.uv_weights[k] = v
    P = CT.parts(FAM)
    wm = P.get('fixtures.workmat'); pm = P.get('fixtures.partsmat'); ws = P.get('fixtures.worksurface')
    t = 0.006 + 0.0001
    if wm is not None:
        # stage 3 to 5 stock on the felt: the grip core lies at seat_grip (right of the middle), so the sheet and the
        # plates lie to its left, the straps along the right and front edges
        # right of the middle, where the grip core lies only from s4 on: clear of seat_small (the gimbal, s2.trunnion to s4.pressfit)
        mbk.seat(wm, 'sheet', p=(0.050, -0.030, t), yaw=0, pose=True, accepts=['materials.sheet_a'])
        mbk.seat(wm, 'plate_l', p=(-0.135, 0.058, t), yaw=0, pose=True, accepts=['materials.sheet_a_plate'])
        mbk.seat(wm, 'plate_r', p=(-0.070, 0.058, t), yaw=0, pose=True, accepts=['materials.sheet_b_plate'])
        # a flat strap: its node frame has the 17 mm width along Z and lies 28.4 to 30.4 mm out along -X: turned flat
        mbk.seat(wm, 'strap', M_local=T((0.143, 0.066, t - 0.0284)) @ R4('Y', 90), pose=True, accepts=['materials.sheet_a_strap', 'materials.sheet_b_strap'])
        mbk.seat(wm, 'spare', M_local=T((-0.0125, -0.110, t - 0.0284)) @ R4('Z', 90) @ R4('Y', 90), pose=True, accepts=['materials.sheet_b_strap'])
    if pm is not None:
        mbk.seat(pm, 'retainer', p=(0.195, -0.060, 0.003), yaw=0)
    if ws is not None:
        # where things lie when the bench is taken (the bench's numbers, as pose marks on the work surface's node)
        o = Vector((0, -0.303, 0))
        lay = R4('X', -90)
        for sid, p, M_, acc in (('entry_pistol', (-0.67, -0.47, 0.02517), lay, ['pistol.frame']), ('entry_servo', (-0.52, -0.20, 0.0001), Matrix.Identity(4), ['servo.case_body']),
                                ('entry_sheet_a', (-0.58, -0.50, 0.0001), Matrix.Identity(4), ['materials.sheet_a']),
                                ('entry_sheet_b', (-0.585, -0.495, 0.0022), R4('Z', -9), ['materials.sheet_b']),
                                ('entry_vial', (-0.55, -0.40, 0.0137), R4('X', -90), ['materials.vial']),
                                ('entry_roll', (-0.95, -0.38, 0.0), Matrix.Identity(4), ['tools.roll'])):
            CT.pose_mark(ws, sid, T(Vector(p)) @ M_, accepts=acc)
        mbk.mark(ws, 'seat_stray', (-0.33, -0.545 + 0.303, 0.010), Z)
