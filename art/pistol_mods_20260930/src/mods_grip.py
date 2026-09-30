# Grip attachments. The FP hands (PlayerFPHands_v5) cup the grip on both sides and under the front of the base, so
# hardware goes where the free-space maps showed room: the backstrap centre strip (|y| < ~10 mm, clear of the web
# below z ~ -0.024), the heel, and under the rear of the base plate (y > -0.012).
import math
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
import pm_geo as G

MM = 0.001
X = Vector((1, 0, 0)); Y = Vector((0, 1, 0)); Z = Vector((0, 0, 1))
N_BS = Vector((0.898, 0, 0.439)).normalized()     # backstrap outward normal (XZ)
N_BASE = Vector((0.287, 0, -0.958)).normalized()  # base plate outward normal
T_BASE = Vector((0.958, 0, 0.287)).normalized()   # base long axis, pointing back
GRIP_C0 = Vector((0.080, 0, -0.030)); GRIP_AX = Vector((-0.4633, 0, 1.0)).normalized()


def _bvh(objs):
    bm = bmesh.new()
    for o in objs:
        t = bmesh.new(); t.from_mesh(o.data); t.transform(o.matrix_world)
        me = bpy.data.meshes.new('_t'); t.to_mesh(me); t.free(); bm.from_mesh(me); bpy.data.meshes.remove(me)
    tree = BVHTree.FromBMesh(bm); bm.free()
    return tree


def pistol_bvh():
    return _bvh([bpy.data.objects['ScrapPistol']])


def hands_bvh():
    hs = [o for o in bpy.data.objects if o.name.startswith('PlayerFPHands')]
    return _bvh(hs) if hs else None


def x_bs(z):
    return 0.1155 - 0.41 * (z + 0.03)


def base_z(x):
    return -0.0834 + 0.3 * (x - 0.08)


def guide(z_top, z_heel=-0.060, n_bs=11, n_heel=7, base_xs=(0.1165, 0.1125, 0.1085)):
    """(origin, direction) ray samples that walk down the backstrap, round the heel and forward under the base."""
    PB = pistol_bvh()
    g = []
    for z in np.linspace(z_top, z_heel, n_bs):
        p = Vector((x_bs(z), 0, z))
        g.append((p + N_BS * 0.03, -N_BS))
    # pivot so the first heel ray hits where the backstrap samples ended
    last = PB.ray_cast(g[-1][0], g[-1][1], 0.1)[0]
    K = last - N_BS * 0.010
    a1 = math.atan2(N_BS.z, N_BS.x); a2 = math.atan2(N_BASE.z, N_BASE.x)
    for a in np.linspace(a1, a2, n_heel)[1:]:
        n = Vector((math.cos(a), 0, math.sin(a)))
        g.append((K + n * 0.03, -n))
    for x in base_xs:
        p = Vector((x, 0, base_z(x)))
        g.append((p + N_BASE * 0.03, -N_BASE))
    return g


def conform_strip(name, samples, half_w, n_u, inner_off, thick, mat, swell=None, edge_frac=0.55, hand_clear=None):
    """Plate that hugs the pistol surface along ray samples. swell(i, u) adds outer thickness (m)."""
    PB = pistol_bvh()
    nv = len(samples)
    us = np.linspace(-half_w, half_w, n_u)
    inner, outer = [], []
    prev = None
    for i, (o, d) in enumerate(samples):
        row_i, row_o = [], []
        for j, u in enumerate(us):
            oo = o + Y * u
            h = PB.ray_cast(oo, d, 0.2)[0]
            if h is None:
                h = prev[j] if prev else oo + d * 0.03
            e = abs(u) / half_w
            t = thick * (edge_frac + (1 - edge_frac) * (1 - e ** 6)) if n_u > 2 else thick
            if swell:
                t += swell(i, u)
            row_i.append(h - d * inner_off)
            row_o.append(h - d * (inner_off + t))
        prev = [h for h in row_i]
        inner.append(row_i); outer.append(row_o)
    verts = []
    for i in range(nv):
        verts += inner[i]
    for i in range(nv):
        verts += outer[i]
    off = nv * n_u
    idx = lambda i, j, s=0: s * off + i * n_u + j
    faces = []
    for i in range(nv - 1):
        for j in range(n_u - 1):
            faces.append((idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)))
            faces.append((idx(i, j, 1), idx(i, j + 1, 1), idx(i + 1, j + 1, 1), idx(i + 1, j, 1)))
    for i in range(nv - 1):  # side walls
        faces.append((idx(i, 0), idx(i, 0, 1), idx(i + 1, 0, 1), idx(i + 1, 0)))
        faces.append((idx(i, n_u - 1), idx(i + 1, n_u - 1), idx(i + 1, n_u - 1, 1), idx(i, n_u - 1, 1)))
    for i in (0, nv - 1):  # end caps
        for j in range(n_u - 1):
            faces.append((idx(i, j), idx(i, j + 1), idx(i, j + 1, 1), idx(i, j, 1)))
    o = G.mesh_obj(name, verts, faces, mat)
    return o, inner, outer


def rivet(name, pos, normal, mat, r=1.7, h=1.05, segs=12):
    loop = [(0, 0), (0, r), (0.35 * h, r * 0.93), (0.7 * h, r * 0.72), (0.92 * h, r * 0.42), (h, 0)]
    ref = Z if abs(Vector(normal).dot(Z)) < 0.9 else X
    return G.lathe(name, [([(s * MM, rr * MM) for s, rr in loop], False)], segs, pos - Vector(normal) * 0.25 * MM, normal, ref, mat)


def grip_sleeve(M, hb):
    """Rubberised wrap: an inner-tube style band round the lower grip, from under the existing lower leather strap
    (which stays proud over its top edge) down to the base pad. It rides a smoothed envelope of the grip relief and is
    pulled in wherever the FP hands come within 0.3 mm (never below 0.15 mm above the real surface)."""
    PB = pistol_bvh()
    nth, nv = 44, 10
    ths = [2 * math.pi * k / nth for k in range(nth)]
    R = np.full((nv, nth), np.nan)
    zs = np.zeros((nv, nth))
    for k, th in enumerate(ths):
        d = Vector((math.cos(th), math.sin(th), 0))
        ztop = -0.0420 + 0.0160 * math.cos(th)
        zbot = -0.0685 + 0.0075 * math.cos(th)
        for i in range(nv):
            z = ztop + (zbot - ztop) * i / (nv - 1)
            c = Vector((0.080 - 0.4633 * (z + 0.03), 0, z))
            h = PB.ray_cast(c + d * 0.06, -d, 0.1)[0]
            if h:
                R[i, k] = (h - c).length
            zs[i, k] = z
    for k in range(nth):
        col = R[:, k]; good = ~np.isnan(col)
        R[:, k] = np.interp(np.arange(nv), np.where(good)[0], col[good])
    Rb = R.copy()
    Rb[0] = Rb[2]; Rb[1] = Rb[2]  # the top rows run under the leather strap: ignore the strap's height
    env = np.array([[Rb[max(0, i - 1):i + 2, [(k - 1) % nth, k, (k + 1) % nth]].max() for k in range(nth)] for i in range(nv)])
    for _ in range(2):
        env = (np.roll(env, 1, 1) + 2 * env + np.roll(env, -1, 1)) / 4
        env[1:-1] = (env[:-2] + 2 * env[1:-1] + env[2:]) / 4
    env = np.maximum(env, Rb)
    T = 0.0011
    verts_o, verts_i = [], []
    thin = 0
    for i in range(nv):
        for k, th in enumerate(ths):
            d = Vector((math.cos(th), math.sin(th), 0))
            z = zs[i, k]
            c = Vector((0.080 - 0.4633 * (z + 0.03), 0, z))
            r = env[i, k] + T
            floor = R[i, k] + 0.00015 if i > 1 else env[i, k] + 0.0002
            if hb:
                for _ in range(3):
                    p = c + d * r
                    nn = hb.find_nearest(p, 0.01)
                    if nn[0] is None:
                        break
                    inside = (p - nn[0]).dot(nn[1]) < 0
                    dist = -nn[3] if inside else nn[3]
                    if dist >= 0.0003:
                        break
                    r = max(floor, r - (0.0003 - dist) - 0.00005)
                if r < env[i, k] + T - 1e-5:
                    thin += 1
            verts_o.append(c + d * r)
            verts_i.append(c + d * (min(R[i, k], env[i, k]) - 0.0004))
    n = nv * nth
    verts = verts_o + verts_i
    faces = []
    for i in range(nv - 1):
        for k in range(nth):
            k2 = (k + 1) % nth
            faces.append((i * nth + k, i * nth + k2, (i + 1) * nth + k2, (i + 1) * nth + k))
    for i, flip in ((0, False), (nv - 1, True)):  # rims down into the grip
        for k in range(nth):
            k2 = (k + 1) % nth
            f = (i * nth + k, n + i * nth + k, n + i * nth + k2, i * nth + k2)
            faces.append(f[::-1] if flip else f)
    o = G.mesh_obj('grip_sleeve', verts, faces, M['rubber_wrap'], recalc=False)
    me = o.data
    p0 = me.polygons[0]
    cc = Vector(p0.center)
    axp = Vector((0.080 - 0.4633 * (cc.z + 0.03), 0, cc.z))
    if p0.normal.dot(cc - axp) < 0:
        bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.reverse_faces(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    return o, thin


def build_stabilised(M):
    """Mk I: rubberised wrap on the grip panels + an orange-painted riveted backstrap brace with a palm swell that
    wraps round the heel onto the base."""
    hb = hands_bvh()
    parts = []
    sleeve, thin = grip_sleeve(M, hb)
    parts.append(sleeve)
    g = guide(-0.0265, n_bs=12, n_heel=6, base_xs=(0.1175, 0.1135))
    nv = len(g)

    def swell(i, u):
        zc = -0.043
        z = g[i][0].z - 0.03 * N_BS.z if i < 12 else -0.07
        a = math.exp(-((z - zc) / 0.010) ** 2) if i < 12 else 0.0
        return 0.0026 * a * max(0.0, 1 - (u / 0.0085) ** 2) ** 0.6

    brace, inner, outer = conform_strip('brace', g, 0.0085, 9, 0.0019, 0.0022, M['paint_orange'], swell=swell)
    parts.append(brace)
    # rivets on the outer face (top pair, lower pair) and a screw on the base tab
    def at(i, j):
        p_o = outer[i][j]; p_i = inner[i][j]
        return p_o, (p_o - p_i).normalized()
    for (i, j) in ((1, 2), (1, 6), (10, 2), (10, 6)):
        p, n = at(i, j)
        parts.append(rivet('rivet', p, n, M['brass']))
    p, n = at(nv - 1, 4)
    p = (outer[nv - 1][4] + outer[nv - 2][4]) / 2; n = (outer[nv - 1][4] - inner[nv - 1][4]).normalized()
    parts.append(rivet('tabrivet', p, n, M['brass'], r=1.9, h=0.9))
    obj = G.join('grip_stabilised_pistol', parts)
    G.sharp_by_angle(obj, 40)
    return obj, {'sleeve_thinned_verts': thin}


def build_gyro(M):
    """Mk II: gyro-stabiliser drum machined from a feral droid's actuator (bone-white droid paint, gunmetal flange
    and caps), cradled under the base plate by a saddle, braced up the backstrap by an alloy bar; cyan status ring
    on the rear cap faces the shooter."""
    parts = []
    C = Vector((0.1065, 0.0, -0.0901))
    t = T_BASE; up = -N_BASE
    mm = lambda L: [(s * MM, r * MM) for s, r in L]
    shell = [(-21.0, 0), (-21.0, 8.0), (-20.4, 9.2), (-18.8, 9.4), (-18.8, 12.6), (-18.2, 13.3), (-14.9, 13.3), (-14.4, 12.6),
             (-14.4, 11.2), (5.5, 11.2), (5.9, 10.5), (6.9, 10.5), (7.3, 11.2), (8.3, 11.2), (8.7, 10.5), (9.7, 10.5), (10.1, 11.2),
             (13.4, 11.2), (13.9, 10.6), (16.6, 10.6), (17.1, 10.0), (20.0, 10.0), (20.6, 9.3), (20.6, 7.3), (20.1, 7.3), (20.1, 5.3),
             (20.6, 5.3), (20.6, 3.2), (21.5, 2.7), (21.5, 0)]
    cav = [(-12.5, 3.0), (4.5, 3.0), (4.5, 10.3), (-12.5, 10.3)]
    body = G.lathe('gyro_body', [(mm(shell), False), (mm(cav), True)], 28, C, t, up, M['paint_bone'])
    cuts = []
    for side in (1, -1):
        cuts.append(G.prism('win', G.stadium(15.0 * MM, 5.2 * MM, 6), 8 * MM, C + t * -4.0 * MM, t, up, Y * side, w0=7.0 * MM))
    G.boolean(body, cuts)
    parts.append(body)
    # machined gunmetal flange ring + caps as separate material parts overlaying the painted drum
    parts.append(G.lathe('gyro_flange', [(mm([(-18.85, 9.35), (-18.85, 12.65), (-18.2, 13.35), (-14.85, 13.35), (-14.35, 12.65), (-14.35, 9.35)]), True)],
                         28, C, t, up, M['steel_dark']))
    parts.append(G.lathe('gyro_rearcap', [(mm([(16.55, 7.0), (16.55, 10.65), (17.1, 10.05), (20.05, 10.05), (20.65, 9.35), (20.65, 7.0)]), True)],
                         28, C, t, up, M['steel_dark']))
    parts.append(G.lathe('gyro_led', [(mm([(19.9, 5.45), (19.9, 7.15), (20.35, 7.15), (20.35, 5.45)]), True)], 28, C, t, up, M['led']))
    # flywheel visible through the windows
    parts.append(G.lathe('flywheel', [(mm([(-9.5, 3.0), (-9.5, 9.9), (-2.5, 9.9), (-2.5, 3.0)]), True)], 28, C, t, up, M['brass']))
    # flange bolts (heads toward the shooter)
    for k in range(6):
        a = math.radians(30 + 60 * k)
        rad = up * math.cos(a) + Y * math.sin(a)
        pos = C + t * (-14.35 * MM) + rad * 12.0 * MM
        parts += hex_head_local('fbolt', pos, t, rad, 2.6, 1.3, M['steel'])
    # saddle cradle: flat top on the base plane, bottom following the drum
    a0 = math.degrees(math.asin(8.5 / 10.9))
    prof = [(-8.5, 14.0), (8.5, 14.0)]
    for k in range(13):
        a = math.radians(a0 - 2 * a0 * k / 12)
        prof.append((10.9 * math.sin(a), 10.9 * math.cos(a)))
    saddle = G.prism('saddle', [(y * MM, n * MM) for y, n in prof], 18.0 * MM, C + t * -3.0 * MM, Y, up, t)
    saddle.data.materials.clear(); saddle.data.materials.append(M['steel_dark'])
    parts.append(saddle)
    for tt in (-8.5, 2.5):
        for side in (1, -1):
            c = C + t * tt * MM + up * 11.2 * MM + Y * side * 8.5 * MM
            h = G.lathe('sbolt', [(mm([(0, 0), (0, 1.9), (1.6, 1.9), (1.9, 1.6), (1.9, 0)]), False)], 12, c, Y * side, t, M['steel'])
            G.boolean(h, [G.prism('hs', G.circle(0.95 * MM, 6), 1.4 * MM, c + Y * side * 1.9 * MM, t, up, -Y * side, w0=-0.1 * MM)])
            parts.append(h)
    # alloy brace bar up the backstrap with lightening slots, top screw and heel screw
    g = guide(-0.0290, n_bs=10, n_heel=6, base_xs=(0.1165, 0.1128))
    bar, inner, outer = conform_strip('brace_bar', g, 0.0062, 5, 0.0004, 0.0024, M['alloy_grip'])
    cuts = []
    for i in (3, 6):
        o_, d_ = g[i]
        hit = (inner[i][2] + inner[i + 1][2]) / 2
        tang = (inner[i + 1][2] - inner[i][2]).normalized()
        cuts.append(G.prism('lh', G.stadium(6.0 * MM, 3.2 * MM, 5), 10 * MM, hit, tang, Y, -d_, w0=-4 * MM))
    G.boolean(bar, cuts)
    parts.append(bar)
    for i in (0, len(g) - 1):
        p = (outer[i][2] + outer[min(i + 1, len(g) - 1)][2]) / 2 if i == 0 else (outer[i][2] + outer[i - 1][2]) / 2
        n = (outer[i][2] - inner[i][2]).normalized()
        parts.append(G.lathe('bscrew', [(mm([(0, 0), (0, 2.2), (0.5, 2.1), (0.8, 1.6), (0.85, 0)]), False)], 12, p - n * 0.2 * MM, n,
                             Y, M['steel']))
    # cable from the rear cap to a connector on the bar at the heel
    hi = 11
    conn_p = (outer[hi][2] + outer[hi][3]) / 2
    conn_n = (outer[hi][2] - inner[hi][2]).normalized()
    conn = G.box('conn', conn_p + conn_n * 1.4 * MM + Y * -4.8 * MM, (4.5 * MM, 3.4 * MM, 2.8 * MM),
                 Matrix(((outer[hi + 1][2] - outer[hi - 1][2]).normalized(), Y, conn_n)).transposed(), M['polymer'])
    parts.append(conn)
    import mods_cell as MC
    a = math.radians(-65)
    start = C + t * 15.0 * MM + (up * math.cos(a) + Y * math.sin(a)) * 10.4 * MM
    sdir = (up * math.cos(a) + Y * math.sin(a))
    end = conn_p + conn_n * 1.4 * MM + Y * -6.6 * MM
    pts = MC.bezier(start, start + sdir * 3 * MM + t * 2 * MM, end - Y * 3.5 * MM - conn_n * 1 * MM, end, 14)
    parts.append(G.tube_path('gcable', pts, 1.05 * MM, 8, M['polymer']))
    parts.append(G.lathe('gland', [(mm([(-0.6, 0), (-0.6, 1.9), (1.4, 1.9), (1.8, 1.5), (1.8, 0)]), False)], 6, start - sdir * 0.6 * MM, sdir, t,
                         M['brass'], phase=math.radians(30)))
    # droid-panel orange band on the drum (salvage paint), between the flange and the cooling grooves
    parts.append(G.lathe('gyro_band', [(mm([(-11.6, 11.18), (-11.6, 11.32), (-7.4, 11.32), (-7.4, 11.18)]), True)], 28, C, t, up, M['paint_orange']))
    # gyro status repeater clipped to the frame's left rear, above the support thumb (the drum itself sits below the
    # bottom edge of the in-game hip view; this is the part the player sees in first person)
    pc = Vector((0.0560, -0.0153, 0.0215))
    pod = G.prism('pod', G.rounded_rect(12.5 * MM, 8.0 * MM, 2.0 * MM, 3), 6.2 * MM, pc + Y * 1.5 * MM, X, Z, -Y, w0=0)
    G.bevel(pod, 0.4 * MM, 1, 30)
    pod.data.materials.clear(); pod.data.materials.append(M['anodized'])
    parts.append(pod)
    face = pc - Y * 4.7 * MM                       # outer (left) face
    rear = Vector((pc.x + 6.25 * MM, -0.0176, pc.z))  # rear face, looking back at the shooter
    parts.append(G.lathe('pod_bezel', [(mm([(0, 1.35), (0, 2.1), (0.45, 1.95), (0.5, 1.35)]), True)], 16, rear, X, Z, M['brass']))
    parts.append(G.lathe('pod_led', [(mm([(-0.2, 0), (-0.2, 1.4), (0.35, 1.35), (0.75, 0.95), (0.95, 0)]), False)], 16, rear, X, Z, M['led']))
    c = face + X * -3.4 * MM
    parts.append(G.lathe('pod_screw', [(mm([(0, 0), (0, 1.1), (0.4, 1.0), (0.6, 0.65), (0.65, 0)]), False)], 10, c, -Y, X, M['steel']))
    for dz in (-2.0, 0.0, 2.0):  # raised ribs on the outer face
        parts.append(G.box('pod_rib', face + X * 1.6 * MM + Z * dz * MM - Y * 0.1 * MM, (5.0 * MM, 0.5 * MM, 0.4 * MM), None, M['steel_dark']))
    obj = G.join('grip_gyro_braced', parts)
    G.sharp_by_angle(obj, 35)
    return obj, None


def hex_head_local(name, origin, axis, ref, af, h, mat):
    rc = af / 2 / math.cos(math.radians(30))
    loop = [(0, 0), (0, rc * 0.92), (0.2, rc), (h - 0.25, rc), (h, rc * 0.8), (h, 0)]
    return [G.lathe(name, [([(s * MM, r * MM) for s, r in loop], False)], 6, origin, axis, ref, mat, phase=math.radians(30))]
