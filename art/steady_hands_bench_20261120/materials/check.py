# materials/check.py: the kit's machine checks (contract, sequence sweep, GLB re-import) and the family's own:
#   interface   plates and bent strap against grip/interface.json in their node frames (outline, holes, frame, seats)
#   unit        every part that hangs on the gimbal against the servo's unit (no overlap), in the cradle frame D
#   leads       lengths against the servo's as-cut leads and the interface's loop
#   rest        loose things stand on z = 0, nothing in D is under the bench (z = -20 mm)
#   grip        when grip/export exists: the plates and strap seated at the core's pose marks
# Run: SH/blender.sh materials/check.py        -> export/check.json, exit 1 on failure
import sys, os, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ('pistol', 'servo', 'kit'):          # the kit first: servo/ and pistol/ have their own check.py
    sys.path.insert(0, os.path.normpath(os.path.join(HERE, '..', p)))
import bpy
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
import importlib.util
_spec = importlib.util.spec_from_file_location('kit_check', os.path.normpath(os.path.join(HERE, '..', 'kit', 'check.py')))
check = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(check)      # not this file, not another family's
import contract as CT
import geo as G
import pgeom as PG

MM = 0.001
rc = 0
try:
    check.main(HERE)
except SystemExit as e:
    rc = int(e.code or 0)
path = os.path.join(HERE, 'export', 'check.json')
res = json.load(open(path))
ifc = json.load(open(os.path.join(HERE, '..', 'grip', 'interface.json')))
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'export', 'materials.blend'))
P = CT.parts('materials')
ob = lambda n: P['materials.' + n]
out = {}


def local_mm(o):
    return np.array([tuple(v.co) for v in o.data.vertices]) / MM


def world_mm(o):
    mw = o.matrix_world
    return np.array([tuple(mw @ v.co) for v in o.data.vertices]) / MM


def near_poly(pts, poly):
    """Largest distance from 2D points to a closed polygon's boundary."""
    worst = 0.0
    n = len(poly)
    A = np.array(poly); B = np.roll(A, -1, 0)
    for p in pts:
        d = B - A
        t = np.clip(((p - A) * d).sum(1) / np.maximum((d * d).sum(1), 1e-18), 0, 1)
        worst = max(worst, float(np.min(np.linalg.norm(A + d * t[:, None] - p, axis=1))))
    return worst


# ---------------------------------------------------------------------- interface: plates
pl = ifc['plate']
fil = PG.fillet([tuple(p) for p in pl['outline_G_us']], pl['corner_radius'])
T = pl['thickness']
blk = {'ok': True, 'plates': {}}
for key, sx, side in (('sheet_a_plate', -1.0, 'left'), ('sheet_b_plate', 1.0, 'right')):
    o = ob(key)
    v = local_mm(o)
    poly = [(sx * u, s) for u, s in fil]
    wall = v[(v[:, 2] > 0.25) & (v[:, 2] < T - 0.25)]
    holes = {}
    used = np.zeros(len(wall), bool)
    for hk, h in pl['holes_G'].items():
        c = np.array([sx * h['u'], h['s']])
        r = np.linalg.norm(wall[:, :2] - c, axis=1)
        m = r < h['d'] / 2 + 0.2
        used |= m
        if not m.any():
            holes[hk] = {'points': 0, 'r_min': 0.0, 'r_max': 0.0, 'want_r': h['d'] / 2, 'centre_error': 99.0,
                         'diag': {'wall_points': int(len(wall)), 'nearest': round(float(r.min()), 3) if len(r) else None,
                                  'z_levels': sorted(set(round(float(z_), 3) for z_ in v[:, 2]))[:12]}}
            continue
        holes[hk] = {'points': int(m.sum()), 'r_min': round(float(r[m].min()), 4), 'r_max': round(float(r[m].max()), 4), 'want_r': h['d'] / 2,
                     'centre_error': round(float(np.linalg.norm(wall[m, :2].mean(0) - c)), 4)}
    edge = wall[~used]
    dev_out = near_poly(edge[:, :2], poly)                       # mesh edge -> eased interface outline
    ptree = BVHTree.FromPolygons([vx.co.copy() for vx in o.data.vertices], [tuple(pg.vertices) for pg in o.data.polygons])
    dev_in = 0.0                                                 # every point of the eased interface outline lies on the plate's edge
    for q in poly:
        nn = ptree.find_nearest(Vector((q[0] * MM, q[1] * MM, T / 2 * MM)), 0.01)
        dev_in = max(dev_in, nn[3] / MM if nn[0] is not None else 10.0)
    R = o.matrix_world.to_3x3()
    fr = pl['node_frames'][side + ' (materials.%s)' % key]
    # the node frame seats the plate in P: check the screw holes against the interface's seats
    MP = Matrix((fr['X_in_P'], fr['Y_in_P'], fr['Z_in_P'])).transposed().to_4x4(); MP.translation = Vector(fr['origin_P_m'])
    seats = {}
    for hk in 'CD':
        h = pl['holes_G'][hk]
        got = MP @ Vector((sx * h['u'] * MM, h['s'] * MM, T * MM))
        want = Vector(ifc['plate_screws']['seats_P_m']['%s_%s' % (side, hk)])
        seats[hk] = round((got - want).length / MM, 4)
    row = {'outline_dev_mm': round(max(dev_out, dev_in), 4), 'holes': holes, 'z_mm': [round(float(v[:, 2].min()), 4), round(float(v[:, 2].max()), 4)],
           'frame_det': round(R.determinant(), 6), 'scale': [round(x, 6) for x in o.matrix_world.to_scale()], 'screw_seats_error_mm': seats,
           'frame_in_P_det': round(MP.to_3x3().determinant(), 6)}
    row['ok'] = (row['outline_dev_mm'] < 0.2 and abs(row['frame_det'] - 1) < 1e-4 and abs(row['z_mm'][0]) < 1e-3 and abs(row['z_mm'][1] - T) < 1e-3 and
                 all(abs(h['r_max'] - h['want_r']) < 0.02 and h['centre_error'] < 0.05 for h in holes.values()) and max(seats.values()) < 0.2 and
                 abs(row['frame_in_P_det'] - 1) < 1e-3)
    blk['plates'][key] = row
    blk['ok'] = blk['ok'] and row['ok']
# plates lie in their sheets with the paint where it should be
for key, up in (('sheet_a_plate', 1.0), ('sheet_b_plate', -1.0)):
    z = (ob(key).matrix_world.to_3x3() @ Vector((0, 0, 1))).z
    blk['plates'][key]['paint_faces'] = 'up' if z > 0 else 'down'
    blk['ok'] = blk['ok'] and abs(z - up) < 1e-4
# strap
st = ifc['strap']
sm = [Vector((p.x, p.y)) for p in G.chaikin([Vector((u, s, 0)) for u, s in st['inner_face_path_G_us']], 2, closed=False)]
o = ob('strap_bent')
v = local_mm(o)
samples = []
for a_, b_ in zip(sm, sm[1:]):
    samples += [a_.lerp(b_, t) for t in (0.0, 0.5)]
dev = 0.0
stree = BVHTree.FromPolygons([vx.co.copy() for vx in o.data.vertices], [tuple(pg.vertices) for pg in o.data.polygons])
for q in samples:
    nn = stree.find_nearest(Vector((q.x * MM, q.y * MM, 0.0)), 0.01)
    dev = max(dev, (nn[3] / MM) if nn[0] is not None else 10.0)
notes = json.load(open(os.path.join(HERE, 'export', 'stats.json')))['notes']
row = {'inner_face_dev_mm': round(dev, 3), 'width_z_mm': [round(float(v[:, 2].min()), 3), round(float(v[:, 2].max()), 3)],
       'neutral_axis_mm': notes['strap']['neutral_axis_mm'], 'interface_developed_mm': st['developed_length'], 'bends': notes['strap']['bends']}
flat = local_mm(ob('sheet_a_strap'))
u0, s0 = st['inner_face_path_G_us'][0]
row['flat_in_G_mm'] = {'u': [round(float(flat[:, 0].min()), 3), round(float(flat[:, 0].max()), 3)], 's': [round(float(flat[:, 1].min()), 3), round(float(flat[:, 1].max()), 3)],
                       'z': [round(float(flat[:, 2].min()), 3), round(float(flat[:, 2].max()), 3)]}
same = (ob('strap_bent').matrix_world - ob('sheet_a_strap').matrix_world)
row['same_node_frame_as_flat'] = max(abs(x) for r_ in same for x in r_) < 1e-6
row['ok'] = (dev < 0.05 and abs(row['width_z_mm'][0] + st['width'] / 2) < 1e-3 and abs(row['width_z_mm'][1] - st['width'] / 2) < 1e-3 and
             abs(row['neutral_axis_mm'] - st['developed_length']) < 1.0 and row['same_node_frame_as_flat'] and
             abs(flat[:, 0].max() - u0) < 0.01 and abs(flat[:, 0].min() - (u0 - st['thickness'])) < 0.01 and abs(flat[:, 1].max() - s0) < 0.01 and
             abs((flat[:, 1].max() - flat[:, 1].min()) - st['developed_length']) < 0.05)
blk['strap'] = row
blk['ok'] = blk['ok'] and row['ok']
out['interface'] = blk

# ---------------------------------------------------------------------- cover: no hole in a plate, no gap in an uncut sheet
def inside(pt, poly):
    x, y = pt; c = False
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]; x1, y1 = poly[(i + 1) % n]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            c = not c
    return c


cb = {'ok': True}
for key, sx in (('sheet_a_plate', -1.0), ('sheet_b_plate', 1.0)):
    o = ob(key)
    tree = BVHTree.FromPolygons([vx.co.copy() for vx in o.data.vertices], [tuple(pg.vertices) for pg in o.data.polygons])
    poly = [(sx * u, s) for u, s in fil]
    n = miss = 0
    for x in np.arange(-30.0, 30.01, 0.5):
        for y in np.arange(-52.0, 60.01, 0.5):
            if not inside((x, y), poly) or near_poly(np.array([[x, y]]), poly) < 0.6:
                continue
            if any(math.hypot(x - sx * h['u'], y - h['s']) < h['d'] / 2 + 0.6 for h in pl['holes_G'].values()):
                continue
            n += 1
            for oz, dz, want in ((T + 1.0, -1.0, T), (-1.0, 1.0, 0.0)):
                hit = tree.ray_cast(Vector((x * MM, y * MM, oz * MM)), Vector((0, 0, dz)))
                if hit[0] is None or abs(hit[0].z / MM - want) > 0.01:
                    miss += 1
    bnd, nm = G.solid_check(o)
    cb[key] = {'rays': 2 * n, 'missed': miss, 'boundary_edges': bnd, 'non_manifold_edges': nm}
    cb['ok'] = cb['ok'] and miss == 0 and bnd == 0 and nm == 0
for k in 'ab':
    objs = [o for fid, o in P.items() if fid.startswith('materials.sheet_%s' % k) and not fid.endswith('scribe')]
    vs, ts = [], []
    for o in objs:
        base = len(vs)
        vs += [o.matrix_world @ vx.co for vx in o.data.vertices]
        ts += [tuple(base + i for i in pg.vertices) for pg in o.data.polygons]
    tree = BVHTree.FromPolygons(vs, ts)
    corner = notes['frames']['sheet_plan']['sheet_%s_corner_m' % k]
    n = miss = 0
    worst = []
    for x in np.arange(1.0, 119.01, 0.5):
        for y in np.arange(1.0, 89.01, 0.5):
            if x + y > 172.0 or math.hypot(x - 8.5, y - 81.5) < 3.4 or math.hypot(x - 111.5, y - 25.0) < 3.4 or (x > 117.5 and y < 4.0):
                continue            # the torn corner, the two old bolt holes, the clipped corner
            n += 1
            for oz, dz, want in ((3.0, -1.0, T), (-1.0, 1.0, 0.0)):
                bad = 0
                for jx, jy in ((0.0, 0.0), (0.013, 0.007), (-0.011, 0.009), (0.006, -0.012)):          # a ray can slip along a seam between two pieces: try beside it
                    hit = tree.ray_cast(Vector((corner[0] + (x + jx) * MM, corner[1] + (y + jy) * MM, corner[2] + oz * MM)), Vector((0, 0, dz)))
                    if hit[0] is None or abs((hit[0].z - corner[2]) / MM - want) > 0.01:
                        bad += 1
                    else:
                        break
                if bad == 4:
                    miss += 1
                    if len(worst) < 6:
                        worst.append([round(float(x), 1), round(float(y), 1), 'top' if dz < 0 else 'bottom'])
    cb['sheet_' + k] = {'rays': 2 * n, 'missed': miss, 'first_misses_plan_mm': worst}
    cb['ok'] = cb['ok'] and miss == 0
out['cover'] = cb

# ---------------------------------------------------------------------- the unit: nothing of ours passes through it
servo_blend = os.path.join(HERE, '..', 'servo', 'export', 'servo.blend')
ublk = {'ok': True, 'pairs': {}, 'min_clearance_mm': {}}
if os.path.exists(servo_blend):
    with bpy.data.libraries.load(servo_blend, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n.startswith('servo_gimbal_') or n.startswith('servo_lead_coil') or n in ('servo_case_body', 'servo_rig')]
    for o in dst.objects:
        if o is not None:
            bpy.context.scene.collection.objects.link(o)
    bpy.context.view_layer.update()
    cr = bpy.data.objects['servo_gimbal_cradle']
    Dinv = cr.matrix_world.inverted()
    unit = [o for o in dst.objects if o is not None and o.type == 'MESH' and o.name.startswith('servo_gimbal_')]
    dg = bpy.context.evaluated_depsgraph_get()

    tris_of = {}
    verts_of = {}
    gd_ = json.load(open(os.path.join(HERE, '..', 'servo', 'export', 'stats.json')))['notes']['gimbal']
    TABS = [Vector(((gd_['body_r'] - 1.7) * MM * math.cos(math.radians(a_)), (gd_['body_r'] - 1.7) * MM * math.sin(math.radians(a_)), -0.0017)) for a_ in gd_['notch_deg']]

    def tree(o, M, shrink=0.0):
        me = o.evaluated_get(dg).to_mesh()
        me.calc_loop_triangles()
        vs = [M @ (v.co - v.normal * shrink) for v in me.vertices]
        ts = [tuple(t.vertices) for t in me.loop_triangles]
        tris_of[o.name] = ts
        verts_of[o.name] = vs
        return BVHTree.FromPolygons(vs, ts, all_triangles=True), vs
    utrees = {o.name: tree(o, Dinv @ o.evaluated_get(dg).matrix_world)[0] for o in unit}
    mine = [o for fid, o in P.items() if json.loads(o['sh']).get('parent') in ('servo.gimbal_cradle', 'materials.lead_a', 'materials.lead_b')]
    for o in mine:
        t, vs = tree(o, o.matrix_world, 0.00003)
        cl = 1.0
        me_ = o.data
        for un, ut in utrees.items():
            n = 0
            for (iu, im) in ut.overlap(t):          # the joint at the terminal tab (coil tail, solder blob) is meant to touch: not counted
                c_ = sum((me_.vertices[i_].co for i_ in tris_of[o.name][im]), Vector()) / 3
                cu = sum((verts_of[un][i_] for i_ in tris_of[un][iu]), Vector()) / 3          # a long triangle of ours can have its middle far from where it touches
                if min(min((c_ - tb).length, (cu - tb).length) for tb in TABS) > 0.0022:
                    n += 1
            if n:
                ublk['pairs']['%s x %s' % (o.name, un)] = n
            for p in vs[::3]:
                nn = ut.find_nearest(p, 0.004)
                if nn[0] is not None:
                    cl = min(cl, nn[3])
        if cl < 1:
            ublk['min_clearance_mm'][o.name] = round(cl / MM, 3)
    # the solder blob at the tab is meant to sit on the cradle: overlaps of the lead nodes with the cradle are that blob only if they are at the tab
    ublk['ok'] = not [k for k in ublk['pairs']]
    # the tab: our leads start where the servo's do
    tabs = {}
    for k in 'ab':
        so = bpy.data.objects.get('servo_lead_coil_' + k)
        if so:
            sv_ = [Dinv @ (so.matrix_world @ v.co) for v in so.data.vertices]
            mine_v = [v.co for v in ob('lead_' + k).data.vertices]
            # distance between the two solder blobs' tops
            a_ = max(sv_, key=lambda p: p.z if (Vector((p.x, p.y)).length < 0.0125) else -9); b_ = max(mine_v, key=lambda p: p.z if (Vector((p.x, p.y)).length < 0.0125) else -9)
            tabs[k] = round((a_ - b_).length / MM, 3)
    ublk['tab_offset_from_servo_lead_mm'] = tabs
    ublk['ok'] = ublk['ok'] and all(v_ < 0.3 for v_ in tabs.values())
else:
    ublk.update(ok=False, error='no servo/export/servo.blend')
out['unit'] = ublk

# ---------------------------------------------------------------------- leads and loop
lb = {'ok': True}
sn = json.load(open(os.path.join(HERE, '..', 'servo', 'export', 'stats.json')))['notes']['lead_length_as_cut_mm']
lb['servo_as_cut_mm'] = sn
lb['built_for_mm'] = notes['leads']['as_cut_mm']
lb['ok'] = all(abs(sn[k] - notes['leads']['as_cut_mm'][k]) < 2.0 for k in 'abs')
lp = ifc['loop']
lb['loop_centre_line_mm'] = notes['loop']['centre_line_mm']
lb['loop_interface_mm'] = lp['length_between_notches']
lb['loop_mid_mm'] = notes['loop']['mid_point_mm']
lb['ok'] = lb['ok'] and abs(notes['loop']['centre_line_mm'] - lp['length_between_notches']) < 2.5 and abs(notes['loop']['mid_point_mm'][0]) < 0.05 and \
    abs(notes['loop']['mid_point_mm'][1] - lp['resistor']['centre_xy'][1]) < 0.05
tk = world_mm(ob('loop_tucked'))
lb['tucked_z_mm'] = [round(float(tk[:, 2].min()), 3), round(float(tk[:, 2].max()), 3)]
lb['ok'] = lb['ok'] and tk[:, 2].max() < 0.05 and tk[:, 2].min() > -lp['channel']['depth']        # under the plate's inner face (z = +0.05), above the channel floor
# the tucked loop stays inside the channel: every vertex within half the channel (or bay) width of the interface line
line = [np.array(p) for p in lp['path_xy']]
worst = near_poly(tk[(tk[:, 1] > 9.0), :2], line + line[::-1][1:-1])
lb['tucked_off_line_mm'] = round(worst, 3)
lb['ok'] = lb['ok'] and worst < lp['resistor_bay']['width'] / 2
out['leads'] = lb

# ---------------------------------------------------------------------- rest
rb = {'ok': True, 'min_z_mm': {}}
bench_d = notes['leads']['bench_z_mm']
for fid, o in P.items():
    d = json.loads(o['sh'])
    w = world_mm(o)
    zmin = float(w[:, 2].min())
    top = fid
    while json.loads(P[top]['sh']).get('parent') in P:
        top = json.loads(P[top]['sh'])['parent']
    if json.loads(P[top]['sh']).get('parent') == 'servo.gimbal_cradle':
        if zmin < bench_d - 0.02:
            rb['ok'] = False; rb['min_z_mm'][fid] = round(zmin, 3)
    elif fid in ('materials.strap_bent', 'materials.strap_bent_1') or json.loads(P[top]['sh']).get('parent') == 'grip.core':
        continue            # these share the flat strip's frame: their legs hang below it until the bench lays them down
    elif zmin < -0.02:
        rb['ok'] = False; rb['min_z_mm'][fid] = round(zmin, 3)
for n_ in ('sheet_a', 'sheet_b', 'vial', 'bobbin', 'resistor'):
    rb['min_z_mm']['materials.' + n_] = round(float(world_mm(ob(n_))[:, 2].min()), 3)
    rb['ok'] = rb['ok'] and abs(rb['min_z_mm']['materials.' + n_]) < 0.05
out['rest'] = rb

# ---------------------------------------------------------------------- flash and sprue sit on the core's middle plane
fb = {'ok': True}
fl_ = [o for fid, o in P.items() if fid.startswith('materials.core_')]
if fl_ and os.path.exists(gblend_ := os.path.join(HERE, '..', 'grip', 'export', 'grip.blend')):
    with bpy.data.libraries.load(gblend_, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n == 'grip_core']
    gc_ = dst.objects[0]
    bpy.context.scene.collection.objects.link(gc_); bpy.context.view_layer.update()
    ct_ = BVHTree.FromPolygons([gc_.matrix_world @ vx.co for vx in gc_.data.vertices], [tuple(pg.vertices) for pg in gc_.data.polygons])
    for o in fl_:
        w = [o.matrix_world @ vx.co for vx in o.data.vertices]
        far = max((ct_.find_nearest(p_, 0.05)[3] or 0.05) for p_ in w) / MM
        root = min((ct_.find_nearest(p_, 0.05)[3] or 0.05) for p_ in w) / MM
        d_ = o.matrix_world - gc_.matrix_world
        row = {'farthest_from_core_mm': round(far, 2), 'nearest_mm': round(root, 3), 'max_abs_y_mm': round(max(abs(p_.y) for p_ in w) / MM, 2),
               'node_frame_is_the_cores': max(abs(x) for r_ in d_ for x in r_) < 1e-6}
        lim = 9.0 if 'sprue' in o.name else 4.5
        row['ok'] = far < lim and root < 0.3 and row['max_abs_y_mm'] < (4.0 if 'sprue' in o.name else 0.3) and row['node_frame_is_the_cores']
        fb[o.name] = row
        fb['ok'] = fb['ok'] and row['ok']
    bpy.data.objects.remove(gc_, do_unlink=True)
else:
    fb['note'] = 'no flash or sprue in this build'
out['flash'] = fb

# ---------------------------------------------------------------------- the grip's marks, when it has exported
gb = {'ok': True}
gj = os.path.join(HERE, '..', 'grip', 'export', 'parts.json')
gblend = os.path.join(HERE, '..', 'grip', 'export', 'grip.blend')
if os.path.exists(gj) and os.path.exists(gblend):
    with bpy.data.libraries.load(gblend, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n.startswith('grip_core__mark_seat_') or n == 'grip_core']
    for o in dst.objects:
        if o is not None:
            bpy.context.scene.collection.objects.link(o)
    bpy.context.view_layer.update()
    marks = {o.name.split('__mark_', 1)[1]: o.matrix_world.copy() for o in dst.objects if o is not None and '__mark_' in o.name}
    gb['marks'] = sorted(marks)
    for key, sx, side, mk in (('sheet_a_plate', -1.0, 'left', 'seat_plate_l'), ('sheet_b_plate', 1.0, 'right', 'seat_plate_r')):
        if mk not in marks:
            gb.setdefault('missing', []).append(mk); continue
        errs = {}
        for hk in 'CD':
            h = pl['holes_G'][hk]
            got = marks[mk] @ Vector((sx * h['u'] * MM, h['s'] * MM, T * MM))
            errs[hk] = round((got - Vector(ifc['plate_screws']['seats_P_m']['%s_%s' % (side, hk)])).length / MM, 4)
        gb[mk] = {'screw_hole_error_mm': errs, 'det': round(marks[mk].to_3x3().determinant(), 5)}
        gb['ok'] = gb['ok'] and max(errs.values()) < 0.2 and abs(marks[mk].to_3x3().determinant() - 1) < 1e-3
    if 'seat_strap' in marks:
        fr = st['node_frame']
        MG = Matrix((fr['X_in_P'], fr['Y_in_P'], fr['Z_in_P'])).transposed().to_4x4(); MG.translation = Vector(fr['origin_P_m'])
        d_ = marks['seat_strap'] - MG
        gb['seat_strap_vs_G'] = round(max(abs(x) for r_ in d_ for x in r_), 6)
        gb['ok'] = gb['ok'] and gb['seat_strap_vs_G'] < 2e-4
else:
    gb['note'] = 'grip/export has no parts.json and grip.blend yet: checked against interface.json only'
gck = os.path.join(HERE, '..', 'grip', 'export', 'check.json')
gb['grip_own_check_ok'] = bool(json.load(open(gck)).get('ok')) if os.path.exists(gck) else None
gb['advisory'] = True              # another family's marks: reported for both sides to read, not held against this family's export
out['grip'] = gb

res['materials'] = out
ok2 = all(b.get('ok', True) or b.get('advisory') for b in out.values())
res['ok'] = bool(res.get('ok')) and ok2
json.dump(res, open(path, 'w'), indent=1, default=lambda v_: bool(v_) if isinstance(v_, np.bool_) else float(v_))
print('MATERIALS CHECK', 'PASS' if ok2 else 'FAIL', json.dumps({k: bool(b.get('ok', True)) for k, b in out.items()}))
if not ok2:
    for k, b in out.items():
        if not b.get('ok', True):
            print('  ', k, '(advisory)' if b.get('advisory') else '', json.dumps(b, default=str)[:1500])
sys.exit(0 if (rc == 0 and ok2) else 1)
