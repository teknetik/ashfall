# fx_parts.py: the fixtures, part by part (slice set first). Every builder makes its pieces in the fixture's own
# frame (metres, Z up, -Y toward the player), joins them into nodes, places the nodes on the bench from layout.json and
# registers them with the kit's contract. See ../PARTS.md for the breakdown this follows.
import math, json, os
import bpy, bmesh
from mathutils import Vector, Matrix
import mbk
from mbk import G, MT, CT, AP, MM, X, Y, Z, O, T, R4, R3, put, W, Wd, bench_pose, join, box, turned, ring_prof, extrude_x, extrude_y, extrude_z
import fx_mats

FAM = 'fixtures'


def reg(o, pid, label, material, mass='medium', kind='fixture', parent=None, note=None, **kw):
    kw.setdefault('loose', True)
    return CT.part(o, FAM, pid, label, kind=kind, parent=parent, material=material, mass=mass, note=note, **kw)


def sub(o, pid, label, parent, material, mass='light', note=None):
    return CT.part(o, FAM, pid, label, kind='part', parent=parent, material=material, mass=mass, loose=True,
                   note=note or 'fixed sub-part of %s.%s, never separated on the bench' % (FAM, parent))


# ====================================================================== work surface
WS = dict(hx=0.45, hy=0.275, t=0.008, sw=0.026, st=0.002)


def build_worksurface(F, M):
    hx, hy, t, sw, st = WS['hx'], WS['hy'], WS['t'], WS['sw'], WS['st']
    c = 0.012
    outline = [(-hx + c, -hy), (hx - c, -hy), (hx, -hy + c), (hx, hy - c), (hx - c, hy), (-hx + c, hy), (-hx, hy - c), (-hx, -hy + c)]
    slab = G.prism('slab', outline, t, O, X, Y, Z, M['ws_rubber'], w0=0.0)
    G.bevel(slab, 0.0012, 2)
    pieces = [slab]
    z0, z1 = t, t + st
    e = M['ws_edging']

    def strip(name, poly, mat):
        o = G.prism(name, poly, st, (0, 0, z0), X, Y, Z, mat, w0=0.0)
        G.bevel(o, 0.0005, 1)
        return o
    yf = -hy + sw           # back edge of the rule
    # side strips butt against the rule at the front and mitre into the back strip
    pieces.append(strip('strip_l', [(-hx + c * 0.0, yf), (-hx + sw, yf), (-hx + sw, hy - sw), (-hx + c, hy), (-hx, hy - c)], e))
    pieces.append(strip('strip_r', [(hx - sw, yf), (hx, yf), (hx, hy - c), (hx - c, hy), (hx - sw, hy - sw)], e))
    pieces.append(strip('strip_b0', [(-hx + c, hy), (-hx + sw, hy - sw), (0, hy - sw), (0, hy)], e))
    pieces.append(strip('strip_b1', [(0, hy), (0, hy - sw), (hx - sw, hy - sw), (hx - c, hy)], e))
    # the bench rule: two halves so each gets its own strip of the atlas (the joint at x = 0 is under a screw)
    r = M['ws_rule']
    pieces.append(strip('rule0', [(-hx + c, -hy), (0, -hy), (0, yf), (-hx, yf), (-hx, -hy + c)], r))
    pieces.append(strip('rule1', [(0, -hy), (hx - c, -hy), (hx, -hy + c), (hx, yf), (0, yf)], r))
    # rivets on the edging, every 90 mm or so; three countersunk slotted screws hold the rule
    rv = []
    WS['rivets'] = []; WS['screws'] = []
    for i in range(6):
        y = yf + 0.035 + i * (2 * hy - sw - 0.07) / 5
        for sx in (-1, 1):
            rv.append(AP.rivet('rv', 6.2 * MM, 1.7 * MM, M['bolt'], segs=8, at=(sx * (hx - sw / 2), y, z1)))
            WS['rivets'].append((sx * (hx - sw / 2), y))
    for i in range(10):
        x = -hx + 0.06 + i * (2 * hx - 0.12) / 9
        rv.append(AP.rivet('rv', 6.2 * MM, 1.7 * MM, M['bolt'], segs=8, at=(x, hy - sw / 2, z1)))
        WS['rivets'].append((x, hy - sw / 2))
    info = fx_mats.MASKS['rule']
    for k, sx in enumerate(info['screws_mm']):
        s = AP.screw('rs', 3.4 * MM, 5 * MM, head='csk', drive='slot', head_d=6.6 * MM, head_h=1.7 * MM, mat=M['bolt'], thread=False, segs=10,
                     at=(-hx + sx * MM, yf - info['screw_y_from_far_edge_mm'] * MM, z1 + 0.00005), turn=math.radians((35, 100, -20)[k]))
        rv.append(s)
        WS['screws'].append((-hx + sx * MM, yf - info['screw_y_from_far_edge_mm'] * MM))
    for o in rv:      # bake their placement into the mesh before the join
        o.data.transform(o.matrix_world); o.matrix_world = Matrix.Identity(4)
    ws = join('worksurface', pieces + rv)
    # nothing that faces down is ever seen (the slab's underside, the strips where they lie on the slab), and in a
    # top-projected atlas those faces would land on the texels of the faces above them
    bm = bmesh.new(); bm.from_mesh(ws.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z < -0.5], context='FACES')
    bm.to_mesh(ws.data); bm.free()
    put(ws, bench_pose('fixtures_worksurface'))
    reg(ws, 'worksurface', 'Work surface and bench rule', 'rubber', 'heavy', steps=['s0.pistol', 's3.trim'])
    xz = -hx + info['zero_mm'] * MM
    mbk.mark(ws, 'lead_zero', (xz, yf, z1), Z)
    mbk.mark(ws, 'lead_length', (xz + info['lead_mm'] * MM, yf, z1), Z)
    mbk.zone(ws, 'rule', (0, -hy + sw / 2, z1), (hx, sw / 2, 0.002))
    F.set_of[ws.name] = 'a'
    return ws


def sweep_closed(name, path, normals, prof, mat=None):
    """Sweep an open profile [(out, up)] round a closed path (points with outward normals in XY)."""
    n = len(path); k = len(prof)
    verts, faces = [], []
    for p, nn in zip(path, normals):
        for (a, b) in prof:
            verts.append(Vector((p[0] + nn[0] * a, p[1] + nn[1] * a, b)))
    for i in range(n):
        j = (i + 1) % n
        for q in range(k - 1):
            faces.append((i * k + q, j * k + q, j * k + q + 1, i * k + q + 1))
    o = G.mesh_obj(name, verts, faces, mat, recalc=True)
    return o


def rrect_path(w, h, r, seg=6):
    """Rounded rectangle as (points, outward normals)."""
    pts, nrm = [], []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for k in range(seg + 1):
            a = math.radians(a0 + 90 * k / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a))); nrm.append((math.cos(a), math.sin(a)))
    return pts, nrm


def densify(pts, nrm, step):
    P, N = [], []
    n = len(pts)
    for i in range(n):
        a = Vector(pts[i]); b = Vector(pts[(i + 1) % n]); na = Vector(nrm[i]); nb = Vector(nrm[(i + 1) % n])
        m = max(1, int(round((b - a).length / step)))
        for k in range(m):
            f = k / m
            P.append(tuple(a.lerp(b, f))); N.append(tuple(na.lerp(nb, f).normalized()))
    return P, N


def build_workmat(F, M):
    w, h, t, r = 0.36, 0.26, 0.006, 0.018
    felt = G.prism('felt', G.rounded_rect(w - 0.004, h - 0.004, r - 0.002, 6), t, O, X, Y, Z, M['felt'], w0=0.0)
    G.bevel(felt, 0.0012, 2)
    pts, nrm = rrect_path(w, h, r, 6)
    # leather binding folded over the edge: 9 mm on top, rounded over, down the side
    prof = [(-0.0095, t - 0.0002), (-0.0092, t + 0.0009), (-0.0015, t + 0.0012), (0.0002, t + 0.0006), (0.0010, t - 0.0012), (0.0010, 0.0)]
    bind = sweep_closed('bind', pts, nrm, prof, M['binding'])
    for p in bind.data.polygons:
        p.use_smooth = True
    # saddle stitches along the binding, 4.5 mm apart: tiny raised tents of waxed thread
    sp, sn = densify(*rrect_path(w - 0.012, h - 0.012, r - 0.006, 6), 0.0045)
    verts, faces = [], []
    zt = t + 0.00105
    for i in range(len(sp)):
        a = Vector((*sp[i], zt)); b = Vector((*sp[(i + 1) % len(sp)], zt))
        d = (b - a); L = d.length
        if L < 1e-6:
            continue
        d.normalize(); s = Vector((-d.y, d.x, 0)) * 0.00045
        a2 = a + d * L * 0.14; b2 = a + d * L * 0.86; mid = (a2 + b2) / 2 + Vector((0, 0, 0.00045))
        k = len(verts)
        verts += [a2 - s, a2 + s, mid - s * 1.15, mid + s * 1.15, b2 - s, b2 + s]
        faces += [(k, k + 1, k + 3, k + 2), (k + 2, k + 3, k + 5, k + 4)]
    st = G.mesh_obj('stitch', verts, faces, M['thread'], recalc=False)
    bm = bmesh.new(); bm.from_mesh(st.data)
    for f in bm.faces:
        if f.normal.z < 0:
            f.normal_flip()
    bm.to_mesh(st.data); bm.free()
    mat = join('workmat', [felt, bind, st])
    bm = bmesh.new(); bm.from_mesh(mat.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z < -0.5], context='FACES')
    bm.to_mesh(mat.data); bm.free()
    put(mat, bench_pose('fixtures_workmat'))
    reg(mat, 'workmat', 'Work mat', 'canvas', 'light', steps=['s0.pistol', 's6.cell'])
    # the pistol lies on its left side, muzzle toward the player's left; the grip sub-assembly a little to the right
    # full poses (the resting node takes the mark's transform). The pistol lies on its right side, muzzle to the
    # player's left, grip toward the player, as in the look target: pistol X -> X, up -> +Y, right -> down. Its widest
    # point on that side (the wrap) is 25.17 mm from the mid-plane (pistol/export/stats.json).
    lay = R4('X', -90)
    # turned 180 degrees about the mat's normal on 21 Nov (bench): the receiver's top, the cell and its latch face the player
    mbk.seat(mat, 'pistol', M_local=T((0.0, 0.0, t + 0.02517)) @ R4('Z', 180) @ lay, pose=True, accepts=['pistol.frame'])
    # the grip is in the pistol's frame too (grip/INTERFACE.md); its middle, P (0.080, 0, -0.030), lies at (0.07, -0.01)
    mbk.seat(mat, 'grip', M_local=T((0.07 - 0.080, -0.01 + 0.030, t + 0.0196)) @ lay, pose=True, accepts=[])
    mbk.seat(mat, 'small', p=(-0.11, -0.07, t), yaw=0)
    mbk.zone(mat, 'work', (0, 0, t + 0.02), (w / 2 - 0.012, h / 2 - 0.012, 0.02))
    F.set_of[mat.name] = 'a'
    return mat


def build_partsmat(F, M):
    w, h, t = 0.44, 0.20, 0.003
    pm = G.prism('pm', G.rounded_rect(w, h, 0.006, 4), t, O, X, Y, Z, M['pm_rubber'], w0=0.0)
    G.bevel(pm, 0.0007, 1)
    bm = bmesh.new(); bm.from_mesh(pm.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z < -0.99], context='FACES')
    bm.to_mesh(pm.data); bm.free()
    pm.name = 'partsmat'
    put(pm, bench_pose('fixtures_partsmat'))
    info = fx_mats.MASKS['partsmat']
    reg(pm, 'partsmat', 'Parts mat', 'rubber', 'light', steps=['s1.scales', 's2.gears'],
        note='PLACEHOLDER outlines and seats until the pistol and servo families export' if info.get('placeholder') else None)
    for sid, (x, y, yaw) in info['seats_mm_from_left_front'].items():
        mbk.seat(pm, sid.replace('.', '_'), p=(x * MM - w / 2, y * MM - h / 2, t), yaw=yaw)
    F.set_of[pm.name] = 'a'
    return pm


def uv_mats(F):
    """Hand layout of set 'a' (the mats). Everything is projected from above; vertical faces take the texels beside
    them. Rectangles in pixels of a 2048 atlas (scaled for other sizes)."""
    hx, hy, sw = WS['hx'], WS['hy'], WS['sw']

    def lay(objs, size):
        k = size / 2048.0
        by = {o.name: o for o in objs}
        ws, wm, pm = by['fixtures_worksurface'], by['fixtures_workmat'], by['fixtures_partsmat']

        def mat_is(o, names):
            idx = {i for i, m in enumerate(o.data.materials) if m and m.name in names}
            return lambda p, me: p.material_index in idx

        def within(o, names, x0, x1, y0, y1):
            base = mat_is(o, names)
            return lambda p, me: base(p, me) and x0 - 1e-4 <= p.center.x <= x1 + 1e-4 and y0 - 1e-4 <= p.center.y <= y1 + 1e-4

        def R(x0, y0, x1, y1):
            return (x0 * k, y0 * k, x1 * k, y1 * k)
        steel = {'ws_edging'}
        yf = -hy + sw
        is_bolt = mat_is(ws, {'bolt'})

        def near(cx, cy, r):
            return lambda p, me: is_bolt(p, me) and abs(p.center.x - cx) < r and abs(p.center.y - cy) < r
        # rivets and screws each on a shared swatch (they are all alike), so the strip under them keeps its own texels
        rects = [(ws, near(cx, cy, 0.0045), R(1740, 1910, 1790, 1960), (0, 1), (cx - 0.0036, cx + 0.0036, cy - 0.0036, cy + 0.0036)) for cx, cy in WS['rivets']]
        rects += [(ws, near(cx, cy, 0.0045), R(1800, 1910, 1850, 1960), (0, 1), (cx - 0.0036, cx + 0.0036, cy - 0.0036, cy + 0.0036)) for cx, cy in WS['screws']]
        rects += [
            # rubber top: 900 x 550 mm at 1.79 px/mm
            (ws, mat_is(ws, {'ws_rubber'}), R(2, 2, 1612, 986), (0, 1), (-hx, hx, -hy, hy)),
            # the rule in two halves at 4.4 px/mm (its screws ride along)
            (ws, within(ws, {'ws_rule'}, -hx, 0.0, -hy, yf), R(2, 1670, 1982, 1784), (0, 1), (-hx, 0.0, -hy, yf)),
            (ws, within(ws, {'ws_rule'}, 0.0, hx, -hy, yf), R(2, 1788, 1982, 1902), (0, 1), (0.0, hx, -hy, yf)),
            # edging at 1.9 px/mm: the two ends stand beside the rubber, the back lies in two halves
            (ws, within(ws, steel, -hx, -hx + sw, yf, hy), R(1620, 2, 1670, 986), (0, 1), (-hx, -hx + sw, yf, hy)),
            (ws, within(ws, steel, hx - sw, hx, yf, hy), R(1676, 2, 1726, 986), (0, 1), (hx - sw, hx, yf, hy)),
            (ws, within(ws, steel, -hx, 0.0, hy - sw, hy), R(944, 1496, 1799, 1546), (0, 1), (-hx, 0.0, hy - sw, hy)),
            (ws, within(ws, steel, 0.0, hx, hy - sw, hy), R(944, 1550, 1799, 1600), (0, 1), (0.0, hx, hy - sw, hy)),
            # work mat 360 x 260 at 2.6 px/mm; its thread on a small swatch
            (wm, mat_is(wm, {'thread'}), R(1990, 1910, 2040, 1960), (0, 1), (-0.18, 0.18, -0.13, 0.13)),
            (wm, lambda p, me: True, R(2, 990, 938, 1666), (0, 1), (-0.18, 0.18, -0.13, 0.13)),
            # parts mat 440 x 200 at 2.5 px/mm
            (pm, lambda p, me: True, R(944, 990, 2044, 1490), (0, 1), (-0.22, 0.22, -0.10, 0.10)),
        ]
        return mbk.uv_rects(objs, size, rects, R(1620, 2, 2046, 986))
    return lay


# ====================================================================== vise
def square_thread(name, r_core, r_crest, pitch, y0, y1, segs=16, mat=None, land=0.5):
    """Square-thread ridge as real geometry on the Y axis from y0 to y1: three quads a step."""
    turns = (y1 - y0 - pitch) / pitch
    n = int(round(turns * segs))
    w = pitch * land
    verts, faces = [], []
    for k in range(n + 1):
        th = 2 * math.pi * k / segs
        y = y0 + pitch * k / segs
        f = min(1.0, k / (segs * 0.5), (n - k) / (segs * 0.5))
        rc = r_core + (r_crest - r_core) * max(0.0, f)
        c, s = math.cos(th), math.sin(th)
        rr = r_core * 0.985
        verts += [(rr * s, y, rr * c), (rc * s, y + w * 0.08, rc * c), (rc * s, y + w * 0.92, rc * c), (rr * s, y + w, rr * c)]
    for k in range(n):
        a, b = 4 * k, 4 * (k + 1)
        for q in range(3):
            faces.append((a + q, b + q, b + q + 1, a + q + 1))
    o = G.mesh_obj(name, verts, faces, mat, recalc=False)
    p = o.data.polygons[len(o.data.polygons) // 2 + 1]
    if Vector((p.center.x, 0, p.center.z)).dot(p.normal) < 0:
        bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.reverse_faces(bm, faces=bm.faces); bm.to_mesh(o.data); bm.free()
    for q in o.data.polygons:
        q.use_smooth = False
    return o


VZ = dict(zs=0.084, zb0=0.044, zb1=0.066, top=0.133, jz0=0.113, jz1=0.135, open=0.090, yend=0.118, ybar=0.140)


def build_vise(F, M):
    zs = VZ['zs']
    gp = 0.00006                      # half the gap left between the pads when closed
    PT = 0.0032                       # pad thickness (copper + leather)
    yj = PT + gp                      # fixed jaw plate face
    yb = yj + 0.008                   # fixed casting face
    g, gs = M['vise_green'], M['vise_green_slide']
    # ---------------- body
    prof = [(yb, 0.030), (yb, 0.131), (yb + 0.0145, 0.131), (yb + 0.0145, 0.119), (0.090, 0.119), (0.094, 0.111), (0.094, 0.058), (0.086, 0.030)]
    body = extrude_x('body', prof, -0.035, 0.035, g)
    # a casting, not a block: narrower toward the anvil end (a linear taper keeps every face flat), a gusset each side
    G.displace(body, lambda co: Vector((co.x * (1.0 - 1.93 * (co.y - yb)), co.y, co.z)))
    head = box('head', (-0.040, yb, 0.100), (0.040, yb + 0.0145, 0.131), g)
    body = G.boolean(body, [head], 'UNION')
    for sx in (-1, 1):
        gus = extrude_y('gus', [(sx * 0.024, 0.029), (sx * 0.049, 0.029), (sx * 0.049, 0.034), (sx * 0.030, 0.088), (sx * 0.024, 0.088)], 0.040, 0.052, g)
        body = G.boolean(body, [gus], 'UNION')
    cut = [box('_bar', (-0.0133, -0.01, VZ['zb0'] - 0.0003), (0.0133, 0.2, VZ['zb1'] + 0.0003)),
           G.cyl('_nut', (0, yb - 0.01, zs), (0, 0.2, zs), 0.0087, 20)]       # the nut is bored through: the screw's end shows at the back
    body = G.boolean(body, cut)
    G.bevel(body, 0.0022, 2, angle=32)
    # swivel: neck, upper flange, lower ring, base plate
    cy = 0.052
    flange = turned('flange', [(0.006, 0), (0.006, 0.059), (0.0155, 0.059), (0.0158, 0.0578), (0.0158, 0)], 28, g, axis=Z, origin=(0, cy, 0))
    neck = turned('neck', [(0.0160, 0), (0.0160, 0.0568), (0.0175, 0.057), (0.0175, 0.0585 - 0.004), (0.020, 0.052), (0.028, 0.050), (0.031, 0.047), (0.031, 0)],
                  28, g, axis=Z, origin=(0, cy, 0))
    plate = extrude_z('plate', G.rounded_rect(0.150, 0.130, 0.014, 5), 0.0, 0.006, g)
    plate.data.transform(T((0, cy, 0)))
    G.bevel(plate, 0.0012, 1)
    body = join('vise_body', [body, neck])
    base = join('vise_base', [plate, flange])
    # ---------------- bolts (their own node: steel, not paint)
    bolts = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            p = (sx * 0.060, cy + sy * 0.050, 0.006)
            bolts.append(AP.washer('w', 8.6 * MM, 17 * MM, 1.5 * MM, M['bolt'], segs=14, at=p))
            bolts.append(AP.screw('b', 8 * MM, 6 * MM, head='hex', drive='none', head_d=15 * MM, head_h=5.3 * MM, mat=M['bolt'], thread=False,
                                  at=(p[0], p[1], p[2] + 1.5 * MM), turn=math.radians(17 * (sx + 2 * sy)), point=False))
    # swivel lock: a stud with a short lever on the left of the flange
    bolts.append(G.cyl('lk', (-0.064, cy, 0.0150), (-0.064, cy, 0.0300), 0.0045, 12, M['bolt'], chamfer=0.0008))
    bolts.append(G.cyl('lkh', (-0.064, cy, 0.0260), (-0.088, cy - 0.012, 0.0320), 0.0034, 10, M['bolt'], chamfer=0.0006))
    bolts.append(G.cyl('lkb', (-0.088, cy - 0.012, 0.0320), (-0.0905, cy - 0.01325, 0.0326), 0.0055, 10, M['bolt'], chamfer=0.0015))
    for o in bolts:
        o.data.transform(o.matrix_world); o.matrix_world = Matrix.Identity(4)
    bolts = join('vise_bolts', bolts)
    # ---------------- slide: the moving jaw casting and its guide bar
    ym = -yj - 0.008                  # moving casting face
    sp = [(ym, 0.131), (ym - 0.0145, 0.131), (ym - 0.030, 0.118), (ym - 0.0375, 0.098), (ym - 0.0375, 0.046), (ym - 0.033, 0.040),
          (ym - 0.0075, 0.040), (ym - 0.0075, 0.094), (ym, 0.099)]
    slide = extrude_x('slide', sp, -0.035, 0.035, gs)
    yfront = ym - 0.0375
    G.displace(slide, lambda co: Vector((co.x * (1.0 - 7.4 * max(0.0, ym - co.y)), co.y, co.z)))     # narrower toward the handle
    shead = box('shead', (-0.040, ym - 0.0145, 0.100), (0.040, ym, 0.131), gs)
    slide = G.boolean(slide, [shead], 'UNION')
    boss = G.cyl('boss', (0, yfront - 0.006, zs), (0, yfront + 0.004, zs), 0.0165, 24, gs, chamfer=0.0015)
    slide = G.boolean(slide, [boss], 'UNION')
    slide = G.boolean(slide, [G.cyl('_sh', (0, yfront - 0.02, zs), (0, ym + 0.02, zs), 0.0074, 20)])
    G.bevel(slide, 0.0022, 2, angle=32)
    bar = box('bar', (-0.013, ym - 0.031, VZ['zb0']), (0.013, VZ['ybar'], VZ['zb1']), M['vise_bar'], bevel=0.0008)
    slide = join('vise_slide', [slide, bar])
    # ---------------- screw: collar, hub with a cross hole, tommy bar, plain shank, square thread
    S = M['vise_screw']
    ycol = yfront - 0.006
    core = turned('core', [(0, 0), (0, 0.0030), (0.0006, 0.0034), (0.0006, 0.0098), (0.0016, 0.0113), (0.0050, 0.0113), (0.0056, 0.0107), (0.0160, 0.0107),
                           (0.0166, 0.0113), (0.0205, 0.0113), (0.0213, 0.0105), (0.0220, 0.0138), (0.0252, 0.0138), (0.026, 0.013),
                           (0.026, 0.0069), (0.026 + (ym - 0.0075 - ycol), 0.0069), (0.026 + (ym - 0.0075 - ycol) + 0.001, 0.0060),
                           (VZ['yend'] - (ycol - 0.026) - 0.0015, 0.0060), (VZ['yend'] - (ycol - 0.026), 0.0045), (VZ['yend'] - (ycol - 0.026), 0)],
                  20, S, axis=Y, origin=(0, ycol - 0.026, zs))
    yhub = ycol - 0.026 + 0.0108
    core = G.boolean(core, [G.cyl('_x', (-0.02, yhub, zs), (0.02, yhub, zs), 0.0046, 14)])
    thr = square_thread('thr', 0.0060, 0.0080, 0.005, ym - 0.0060, VZ['yend'] - 0.0015, 16, S)
    thr.data.transform(T((0, 0, zs)))
    tb = G.cyl('tb', (-0.050, yhub, zs), (0.074, yhub, zs), 0.00425, 12, S)
    b0 = turned('b0', [(0, 0), (0.001, 0.0045), (0.004, 0.0074), (0.008, 0.0082), (0.012, 0.0074), (0.015, 0.0045), (0.016, 0)], 14, S, axis=X, origin=(-0.062, yhub, zs))
    b1 = turned('b1', [(0, 0), (0.001, 0.0045), (0.004, 0.0074), (0.008, 0.0082), (0.012, 0.0074), (0.015, 0.0045), (0.016, 0)], 14, S, axis=X, origin=(0.070, yhub, zs))
    screw = join('vise_screw', [core, thr, tb, b0, b1])
    G.shade(screw, 35)
    # ---------------- jaw plates and soft pads
    def plate_(name, y0, y1):
        return box(name, (-0.040, y0, VZ['jz0']), (0.040, y1, VZ['jz1']), M['vise_plate'], bevel=0.0006)

    def pad(name, face_y, sgn, cu, le):
        """Copper sheet hooked over the plate with a leather face; sgn = +1 for the fixed jaw (body at +Y)."""
        zt = VZ['jz1']
        y0 = face_y + sgn * 0.0020; y1 = face_y + sgn * PT          # copper leg behind the leather
        ybk = face_y + sgn * (PT + 0.008 + 0.0004)                   # over the back of the plate
        pr = [(y0, 0.1085), (y0, zt + 0.0013), (ybk + sgn * 0.0012, zt + 0.0013), (ybk + sgn * 0.0012, zt - 0.0035), (ybk, zt - 0.0035),
              (ybk, zt + 0.0001), (y1, zt + 0.0001), (y1, 0.1085)]
        if sgn < 0:
            pr = pr[::-1]
        c = extrude_x(name + '_cu', pr, -0.042, 0.042, cu, bevel=0.0003)
        l = box(name + '_le', (-0.041, min(face_y, y0), 0.1095), (0.041, max(face_y, y0), zt + 0.0006), le, bevel=0.0005, segs=2)
        return join(name, [c, l])
    plate_f = plate_('vise_plate_f', yj, yb)
    plate_m = plate_('vise_plate_m', ym, -yj)
    pad_f = pad('vise_pad_f', gp, 1, M['pad_copper_old'], M['pad_leather_old'])
    pad_m = pad('vise_pad_m', -gp, -1, M['pad_copper_new'], M['pad_leather_new'])
    OPEN = VZ['open']
    for o in (slide, screw, plate_m, pad_m):       # built closed, stood open: parameter 0 is the as-found pose
        o.data.transform(T((0, -OPEN, 0)))
    Mw = bench_pose('fixtures_vise')
    for o in (body, base, bolts, slide, screw, plate_f, plate_m, pad_f, pad_m):
        put(o, Mw)
    reg(base, 'vise_base', 'Vise base', 'steel', 'heavy', steps=['s1.clamp'], note='bolted through the mat; the vise body swivels on it (param vise_swivel)')
    reg(body, 'vise', 'Bench vise', 'steel', 'heavy', parent='vise_base', steps=['s1.clamp', 's2.swap', 's3.cut', 's3.strap', 's4.pressfit', 's6.cell'],
        note='the swivelling body: node origin on the vertical swivel axis through the base centre')
    body_id = 'vise'
    sub(bolts, 'vise_bolts', 'Vise base bolts', 'vise_base', 'steel')
    sub(plate_f, 'vise_plate_f', 'Fixed jaw plate', body_id, 'steel')
    sub(pad_f, 'vise_pad_f', 'Fixed soft pad', body_id, 'copper')
    sub(slide, 'vise_slide', 'Sliding jaw', body_id, 'steel', 'heavy')
    sub(plate_m, 'vise_plate_m', 'Moving jaw plate', body_id, 'steel')
    sub(pad_m, 'vise_pad_m', 'Moving soft pad', body_id, 'copper')
    sub(screw, 'vise_screw', 'Vise screw and handle', body_id, 'steel')
    G.set_origin(screw, W(body, (0, yhub - OPEN, zs)))
    G.set_origin(slide, W(body, (0, -OPEN, zs)))
    # ---------------- rig: jaw 0 = open 70 mm (as found), 1 = pads touching; the screw is a continuous turn on the slide
    R = F.new_rig('vise', body)
    R.slide('vise_jaw', W(body, (0, -OPEN, zs)), Wd(body, (0, 1, 0)), 0.0, OPEN, [slide, plate_m, pad_m])
    R.continuous('vise_handle', W(body, (0, yhub - OPEN, zs)), Wd(body, (0, 1, 0)), [screw], parent='vise_jaw')
    F.end_rig(R)
    F.param_notes['fixtures.vise_handle'] = {'pitch_mm': 5.0, 'hand': 'right', 'turns_for': {'fixtures.vise_jaw': OPEN / 0.005},
                                             'note': 'positive turns about the bone +Y close the vise: turns = %g x vise_jaw' % (OPEN / 0.005)}
    F.param_notes['fixtures.vise_jaw'] = {'opening_mm': [OPEN * 1000, 0.0],
                                          'note': '0 = open %g mm (as found), 1 = soft pads touching; gap = %g x (1 - value) mm' % (OPEN * 1000, OPEN * 1000)}
    # the pistol frame in the jaws: upside down (the grip up, so the housing slides off upward), its left side and the
    # screw heads toward the player, muzzle to the right. Clamped by the top of the receiver round P x = -0.03, where it
    # is 35.6 mm across (fixtures/layout/pistol_profile.json): the fixed pad bears on its right side.
    # the pistol upside down, held by the flat sides of the receiver top behind the cell bay: the whole grip stands over
    # the jaws (27 mm above the pad tops), left side and screw heads toward the player, muzzle to the player's right.
    # Until 20:50 on 20 Nov the frame sat 60 mm further left and the grip hung off the left of the vise, cut by the
    # bench camera's frame (fixtures/src/vise_pose_probe.py gives the numbers for any pose).
    mbk.seat(body, 'work', M_local=T((0.030, -0.0180, 0.1907)) @ R4('Y', 180), pose=True, accepts=['pistol.frame'])
    # the servo upright across its 70 mm width, 18 mm down in the jaws (21 Nov: was 30 mm, which put the case seam and its
    # three clips, 23 mm up the case, behind the pads; now the pry marks stand 5 mm above the pad tops)
    mbk.seat(body, 'servo', M_local=T((-0.0145, -0.0350, VZ['jz1'] - 0.018)), pose=True, accepts=['servo.case_body'])
    mbk.seat(body, 'flat', p=(0, 0, VZ['jz1'] - 0.011), yaw=0)
    mbk.mark(body, 'anvil', (0, 0.058, 0.119), Z)
    mbk.mark(slide, 'handle', (0.078, yhub - OPEN, zs), X)
    mbk.mark(body, 'jaw_top', (0, 0, VZ['jz1']), Z)
    # the body's node origin onto the swivel axis (the jaw rig hanging on it is put back where it was), and the swivel
    axis_w = W(body, (0, cy, 0))
    kids = [(c, c.matrix_world.copy()) for c in body.children]
    G.set_origin(body, axis_w)
    for c, m_ in kids:
        c.matrix_world = m_
    bpy.context.view_layer.update()
    R2 = F.new_rig('vise_swivel', base)
    R2.continuous('vise_swivel', axis_w, Wd(base, (0, 0, 1)), [body])
    F.end_rig(R2)
    F.param_notes['fixtures.vise_swivel'] = {'note': 'the vise body (and all on it) turns about the vertical axis through the base centre; '
                                             'positive = anticlockwise seen from above; code-driven, no clip; rest 0'}
    for o in (body, base, bolts, slide, screw, plate_f, plate_m, pad_f, pad_m):
        F.set_of[o.name] = 'b'
    F.uv_weights.update({pad_f.name: 1.5, pad_m.name: 1.5, plate_f.name: 1.2, plate_m.name: 1.2, screw.name: 1.1})
    return body


# ====================================================================== dish
def build_dish(F, M):
    mm = MM
    prof = [(5.0, 0), (5.0, 35), (6.2, 40.5), (9.5, 46.2), (16, 50.6), (24, 53.0), (26.6, 53.5), (27.8, 54.2), (28.6, 53.6), (28.7, 52.6), (27.9, 51.9),
            (26.4, 52.0), (24, 51.6), (16.4, 49.2), (10.4, 45.0), (7.4, 39.6), (6.3, 34.5), (6.2, 0)]
    bowl = turned('bowl', [(a * mm, b * mm) for a, b in prof], 40, M['dish_steel'], axis=Z)
    base = turned('base', [(0, 0), (0, 42 * mm), (1 * mm, 43 * mm), (5.3 * mm, 43 * mm), (5.3 * mm, 0)], 26, M['dish_rubber'], axis=Z)
    d = join('dish', [bowl, base])
    G.shade(d, 50)
    put(d, bench_pose('fixtures_dish'))
    reg(d, 'dish', 'Magnetic dish', 'steel', 'light', steps=['s1.screw_a', 's2.screws'])
    zf = 6.2 * mm
    mbk.seat(d, 'fasteners', p=(0, 0, zf))
    k = 0
    for r, n, ph in ((0.022, 8, 0.2), (0.009, 4, 0.6)):
        for i in range(n):
            a = ph + 2 * math.pi * i / n
            mbk.mark(d, 'slot_%02d' % k, (r * math.cos(a), r * math.sin(a), zf), Z); k += 1
    F.set_of[d.name] = 'b'
    F.uv_weights[d.name] = 1.3
    return d


# ====================================================================== cradle
def build_cradle(F, M):
    base = box('base', (-0.090, -0.045, 0.0), (0.090, 0.045, 0.018), M['wood_cradle'], bevel=0.003, segs=2)
    pcs = [base]
    # two saddles 124 mm apart for the stripped frame, placed on its real underside (rays cast in
    # src/probe_pistol.py, layout/pistol_profile.json): the front one under the flat of the dust cover (P x -0.091 to
    # -0.062, z 0.024), the rear one on the 5 mm flat between the trigger guard and the cell bus where it runs down
    # the tang (P x 0.045 to 0.050, z 0.0187), with a 4 mm pad. The rear saddle is 5.3 mm lower so
    # the frame lies level. Wide and shallow (50 mm flat, 8 mm lips): the frame is up to 40 mm across above them and
    # carries the cell bus 22.5 mm out on its left.
    for x, zs, padw in ((-0.062, 77.6, 0.013), (0.062, 72.3, 0.004)):
        out = [(-30, 18), (30, 18), (30, 23.5), (10, 26), (9, zs - 16), (29, zs - 7), (33, zs + 8), (27.5, zs + 8), (25, zs), (-25, zs),
               (-27.5, zs + 8), (-33, zs + 8), (-29, zs - 7), (-9, zs - 16), (-10, 26), (-30, 23.5)]
        fork = extrude_x('fork', [(a * MM, b * MM) for a, b in out], x - 0.003, x + 0.003, M['forged'], bevel=0.0009)
        pcs.append(fork)
        sad = [(-26.9, zs + 7.6), (-25.0, zs + 1.6), (-23.2, zs + 0.2), (23.2, zs + 0.2), (25.0, zs + 1.6), (26.9, zs + 7.6)]
        pts = [Vector((x, a * MM, b * MM)) for a, b in sad]
        ctr = Vector((x, 0, (zs + 40) * MM))
        pad = G.band_path('pad', pts, padw, 0.0030, lambda p, tg, c=ctr: (c - p), M['leather'], closed=False, offset=-0.0002)
        G.shade(pad, 50)
        pcs.append(pad)
        for sy in (-1, 1):
            s = AP.screw('s', 4 * MM, 8 * MM, head='dome', drive='slot', head_d=7.6 * MM, head_h=2.4 * MM, mat=M['brass_screw'], thread=False, segs=10,
                         at=(x, sy * 0.021, 0.0236), turn=math.radians(40 * (1 if x > 0 else -1) + 70 * sy))
            s.data.transform(s.matrix_world); s.matrix_world = Matrix.Identity(4)
            pcs.append(s)
    c = join('cradle', pcs)
    put(c, bench_pose('fixtures_cradle'))
    reg(c, 'cradle', 'Cradle stand', 'wood', 'medium', steps=['s2.swap'])
    # the stripped frame upright, muzzle to the player's left, level on the two leather pads
    mbk.seat(c, 'frame', M_local=T((0.062 - 0.0475, 0.0, 0.0776 + 0.0031 - 0.0240)), pose=True, accepts=['pistol.frame'])
    mbk.mark(c, 'saddle_l', (-0.062, 0, 0.0807), Z)
    mbk.mark(c, 'saddle_r', (0.062, 0, 0.0754), Z)
    F.set_of[c.name] = 'b'
    return c


# ====================================================================== insulated pad
def build_pad(F, M):
    tile = box('tile', (-0.065, -0.052, 0.0), (0.065, 0.052, 0.008), M['tile'], bevel=0.0012, segs=2)
    # a chipped corner
    chip = box('_chip', (0.050, -0.070, 0.002), (0.090, -0.040, 0.02))
    chip.data.transform(T((0.012, -0.004, 0)) @ R4('Z', 38) @ R4('X', 25))
    tile = G.boolean(tile, [chip])
    hw, hd, z0, th = 0.052, 0.039, 0.008, 0.0125
    n = 13
    prof = [(-hw, z0), (hw, z0), (hw, z0 + th - 0.002), (hw - 0.002, z0 + th)]
    step = (2 * hw - 0.008) / n
    for i in range(n):
        x1 = hw - 0.004 - i * step
        prof += [(x1, z0 + th), (x1 - step * 0.22, z0 + th + 0.0016), (x1 - step * 0.5, z0 + th + 0.0016), (x1 - step * 0.72, z0 + th)]
    prof += [(-hw + 0.002, z0 + th), (-hw, z0 + th - 0.002)]
    slab = extrude_y('slab', prof, -hd, hd, M['pad_rubber'], bevel=0.0005)
    G.shade(slab, 25)
    p = join('pad', [tile, slab])
    put(p, bench_pose('fixtures_pad'))
    reg(p, 'pad', 'Insulated pad', 'ceramic', 'medium', steps=['s0.cell', 's6.cell'])
    # the charge cell (59 long, 14.2 across, its node origin at its middle, its axis along its own X) lies along the
    # ribs in the groove between the two middle ones, 6.6 mm above their crests
    xv = (hw - 0.004 - 6 * step) - 0.86 * step
    mbk.seat(p, 'cell', M_local=T((xv, 0, z0 + th + 0.0016 + 0.00658)) @ R4('Z', 90), pose=True, accepts=['pistol.cell'])
    F.set_of[p.name] = 'b'
    F.uv_weights[p.name] = 1.2
    return p


# ====================================================================== card board
def bulldog(name, M, width=0.040):
    """Bulldog clip gripping an edge 6.5 mm thick whose top is at z = 0, front face at y = 0. Body, two wire handles."""
    t = 0.0007
    w = 0.0100                     # outside of the rear lip; the sheet is 0.7 thick, so the jaws open 9.2 mm
    pr = [(-0.0006, -0.016), (-0.0030, -0.0165), (-0.0034, -0.0155), (-0.0012, -0.014), (-0.0052, 0.004), (w / 2 - 0.0003, 0.0115),
          (w + 0.0046, 0.004), (w + 0.0006, -0.014), (w + 0.0028, -0.0155), (w + 0.0024, -0.0165), (w, -0.016)]
    inner = [(-0.0006 + t, -0.0152), (-0.0045 + t * 1.2, 0.0036), (w / 2 - 0.0003, 0.0105), (w + 0.0039 - t * 1.2, 0.0036), (w - t, -0.0152)]
    body = extrude_x(name + '_b', pr + inner[::-1], -width / 2, width / 2, M['clip_black'])
    G.shade(body, 30)
    wire = M['clip_wire']; r = 0.0009
    hw = width / 2 - 0.004
    # front handle folded down over the card, back handle standing up
    f = [(-hw, -0.0036, 0.0026), (-hw, -0.0052, -0.004), (-hw * 0.72, -0.0044, -0.026), (-hw * 0.3, -0.0040, -0.033), (hw * 0.3, -0.0040, -0.033),
         (hw * 0.72, -0.0044, -0.026), (hw, -0.0052, -0.004), (hw, -0.0036, 0.0026)]
    b = [(-hw, w + 0.0029, 0.0026), (-hw, w + 0.0054, 0.008), (-hw * 0.72, w + 0.0074, 0.030), (-hw * 0.3, w + 0.0079, 0.037), (hw * 0.3, w + 0.0079, 0.037),
         (hw * 0.72, w + 0.0074, 0.030), (hw, w + 0.0054, 0.008), (hw, w + 0.0029, 0.0026)]
    wf = AP.wire(name + '_wf', f, 2 * r, wire, segs=6, smooth=1)
    wb = AP.wire(name + '_wb', b, 2 * r, wire, segs=6, smooth=1)
    return join(name, [body, wf, wb])


BOARD = dict(w=0.60, h=0.34, z0=0.022, lean=10.0, t=0.005)


def build_board(F, M):
    w, h, z0, t = BOARD['w'], BOARD['h'], BOARD['z0'], BOARD['t']
    L = R4('X', -BOARD['lean'])        # leans back: the top goes toward +Y
    panel = box('panel', (-w / 2, 0, z0), (w / 2, t, z0 + h), M['hardboard'], bevel=0.0008)
    fr = M['frame_steel']; a = 0.012; p = 0.0015
    bars = [box('ft', (-w / 2 - p, -p, z0 + h - a + p), (w / 2 + p, t + p, z0 + h + p), fr, bevel=0.0005),
            box('fb', (-w / 2 - p, -p, z0 - p), (w / 2 + p, t + p, z0 + a - p), fr, bevel=0.0005),
            box('fl', (-w / 2 - p, -p, z0 + a - p), (-w / 2 + a - p, t + p, z0 + h - a + p), fr, bevel=0.0005),
            box('frr', (w / 2 - a + p, -p, z0 + a - p), (w / 2 + p, t + p, z0 + h - a + p), fr, bevel=0.0005)]
    rv = []
    for sx in (-1, 1):
        for sz in (0, 1):
            rv.append(AP.rivet('r', 4.6 * MM, 1.3 * MM, M['bolt'], segs=8, at=(sx * (w / 2 - a / 2 + p / 2), -p, z0 + a / 2 + sz * (h - a)), axis=-Y))
    for x in (-0.140, 0.140):      # clear of the two cards
        for sz in (0, 1):
            rv.append(AP.rivet('r', 4.6 * MM, 1.3 * MM, M['bolt'], segs=8, at=(x, -p, z0 + a / 2 - p / 2 + sz * (h - a + p)), axis=-Y))
    for o in rv:
        o.data.transform(o.matrix_world); o.matrix_world = Matrix.Identity(4)
    brd = join('board', [panel] + bars + rv)
    brd.data.transform(L)
    # feet and strut are built where they stand (after the lean)
    top = L @ Vector((0, t, z0 + h))
    pcs = [brd]
    for sx in (-1, 1):
        x = sx * 0.235
        pcs.append(box('foot', (x - 0.0125, -0.045, 0.0), (x + 0.0125, 0.105, 0.003), fr, bevel=0.0006))
        up0 = L @ Vector((x, t + p, z0 - p)); up1 = L @ Vector((x, t + p, z0 + 0.10))
        pcs.append(G.cyl('post', (x, up0.y + 0.004, 0.002), (x, up1.y + 0.004, up1.z), 0.004, 8, fr))
        pcs.append(G.cyl('stay', (x, 0.100, 0.003), (x, up1.y + 0.006, up1.z - 0.004), 0.003, 8, fr))
    pcs.append(G.cyl('strut', (0, top.y + 0.002, top.z - 0.03), (0, 0.118, 0.003), 0.0032, 8, fr))
    pcs.append(box('strutfoot', (-0.02, 0.105, 0.0), (0.02, 0.130, 0.003), fr, bevel=0.0006))
    board = join('board', pcs)
    put(board, bench_pose('fixtures_board'))
    reg(board, 'board', 'Card board', 'wood', 'medium', steps=['s0.card_before', 's7.card_after'])
    # two bulldog clips on the top edge at the left; each its own node (static)
    cards = {}
    for nm, x in (('clip_a', -0.218), ('clip_b', -0.062)):
        c = bulldog('board_' + nm, M)
        c.data.transform(L @ T((x, -0.0027, z0 + h + p)))
        put(c, bench_pose('fixtures_board'))
        sub(c, 'board_' + nm, 'Card clip', 'board', 'steel', 'tiny')
        F.set_of[c.name] = 'b'
        cards[nm] = x
    # card seats, full poses: a test card (pistol.card_a, _b: 148 x 105, origin at the middle of its back, mark `clip`
    # 44 mm up its Y) hangs with its clip mark in the clip's jaws 8 mm below the board's top edge; card X across the
    # board, Y up it, Z out of it
    for sid, nm, acc in (('card_before', 'clip_a', 'pistol.card_a'), ('card_after', 'clip_b', 'pistol.card_b')):
        Ml = L @ T((cards[nm], -p - 0.0004, z0 + h - 0.008)) @ R4('X', 90) @ T((0, -0.044, 0))
        mbk.seat(board, sid, M_local=Ml, pose=True, accepts=[acc])
    # where the schematic sheet hangs (Milestone 3): the top middle of a sheet 250 x 300, same axes as a card
    mbk.seat(board, 'schematic', M_local=L @ T((0.160, -p - 0.0004, z0 + h - 0.012)) @ R4('X', 90), pose=True, accepts=[])
    F.set_of[board.name] = 'b'
    F.uv_weights[board.name] = 0.55
    return board
