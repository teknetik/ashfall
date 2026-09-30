# Cell attachments: mounted on the left side (-Y) of the pistol's dust-cover rail, in front of the trigger guard.
# Rail left face: y ~ -10.0 mm for x in [-0.095, -0.058], y ~ -11.7 mm for x in [-0.057, -0.03]; rail z 0.021..0.042.
import math
from mathutils import Vector, Matrix
import pm_geo as G

MM = 0.001
X = Vector((1, 0, 0)); Y = Vector((0, 1, 0)); Z = Vector((0, 0, 1))
PORT = Vector((-0.0272, -0.0117, 0.0262))  # grommet on the frame's left face, just ahead of the trigger guard


def bezier(p0, p1, p2, p3, n):
    pts = []
    for i in range(n + 1):
        t = i / n
        a = (1 - t) ** 3; b = 3 * (1 - t) ** 2 * t; c = 3 * (1 - t) * t * t; d = t ** 3
        pts.append(p0 * a + p1 * b + p2 * c + p3 * d)
    return pts


def grommet(M):
    return G.lathe('grommet', [(G_mm([(-0.2, 2.1), (-0.2, 3.2), (0.6, 3.7), (1.3, 3.5), (1.5, 2.8), (1.5, 2.1)]), True)], 16,
                   PORT, -Y, Z, M['polymer'])


def G_mm(loop):
    return [(s * MM, r * MM) for s, r in loop]


def p_clamp(name, xc, yc, zc, R, M, width=6.5, thick=0.6, stem=11.0, rail_y=-11.7):
    """P-clamp strap around a cylinder (axis X at (yc, zc), band centre-line radius R mm) whose two-layer stem runs up
    the rail face (inner layer against the rail at rail_y mm)."""
    y_in = rail_y - thick / 2  # inner layer centre (mm)
    y_out = y_in - thick
    # circle joins: outer layer where the circle's y equals y_out
    ycm, zcm = yc * 1000, zc * 1000
    phi0 = math.degrees(math.acos(max(-1, min(1, (y_out - ycm) / R))))
    pts = []
    for z in (zcm + stem, zcm + stem * 0.6, zcm + (R * math.sin(math.radians(phi0))) + 1.2):
        pts.append((y_out, z))
    n = 44
    for i in range(n + 1):
        ph = math.radians(phi0 + (360 - phi0) * i / n)
        pts.append((ycm + (R + 0.0) * math.cos(ph) * (1 if i < n else 1), zcm + R * math.sin(ph)))
    # last point is (ycm+R, zcm); make it land on the inner layer
    pts[-1] = (y_in, zcm)
    for z in (zcm + 1.5, zcm + stem * 0.6, zcm + stem):
        pts.append((y_in, z))
    P = [Vector((xc, y * MM, z * MM)) for y, z in pts]
    band = G.band_path(name, P, width * MM, thick * MM, lambda p, t: X.cross(t), M['steel'], closed=False, offset=-thick / 2 * MM)
    return band


def capacitor_body(M, x_rear, length, yc, zc, r):
    O = Vector((x_rear, yc, zc))
    ax = -X
    L = length
    body = G.lathe('cap_body', [(G_mm([(0.6, 0), (0.6, r - 0.6), (1.0, r), (4.0, r), (4.6, r - 0.6), (5.4, r - 0.6), (6.0, r),
                                       (L - 0.8, r), (L - 0.2, r - 0.4), (L, r - 1.1), (L - 0.3, r - 1.4), (L - 0.6, r - 1.4), (L - 0.6, 0)]), False)],
                   28, O, ax, Z, M['sleeve_teal'])
    top = G.lathe('cap_top', [(G_mm([(L - 0.7, 0), (L - 0.7, r - 1.35), (L - 0.25, r - 1.35), (L - 0.25, 0)]), False)], 28, O, ax, Z, M['alloy'])
    cuts = []
    for a in (35, -35):
        R = Matrix.Rotation(math.radians(a), 3, X)
        cuts.append(G.box('kvent', O + ax * (L - 0.25) * MM, (0.9 * MM, 0.55 * MM, 11 * MM), R @ Matrix((Y, X, Z)).transposed()))
    G.boolean(top, cuts)
    seal = G.lathe('cap_seal', [(G_mm([(-0.9, 0), (-0.9, r - 2.4), (-0.5, r - 1.3), (0.2, r - 0.7), (0.8, r - 0.6), (0.8, 0)]), False)],
                   24, O, ax, Z, M['polymer'])
    return [body, top, seal]


def terminal(M, base, lug_dir):
    """Brass screw post on the capacitor's rear face with nut, ring lug and crimp barrel (lug_dir: unit vector in the face plane)."""
    parts = [G.lathe('post', [(G_mm([(0, 0), (0, 1.25), (3.4, 1.25), (3.8, 0.9), (3.8, 0)]), False)], 12, base, X, Z, M['brass'])]
    parts.append(G.lathe('lug', [(G_mm([(0.3, 1.4), (0.3, 2.7), (0.8, 2.7), (0.8, 1.4)]), True)], 16, base, X, Z, M['copper']))
    rc = 2.1 / math.cos(math.radians(30))
    parts.append(G.lathe('nut', [(G_mm([(0.8, 1.3), (0.8, rc * 0.9), (1.0, rc), (1.9, rc), (2.1, rc * 0.9), (2.1, 1.3)]), True)], 6, base, X, Z,
                         M['brass'], phase=math.radians(30)))
    d = Vector(lug_dir).normalized()
    b0 = base + X * 0.55 * MM + d * 2.4 * MM
    parts.append(G.lathe('barrel', [(G_mm([(0, 0), (0, 1.15), (3.6, 1.15), (4.0, 0.95), (4.0, 0)]), False)], 10, b0, d, X, M['copper']))
    return parts, b0 + d * 4.0 * MM, d


def build_capacitor(M):
    """Mk I: a salvaged can capacitor held to the rail by two P-clamps (the front one packed out with washers),
    wired back into the frame through a grommet."""
    parts = []
    yc, zc, r = -0.0213, 0.0262, 8.4
    x_rear, L = -0.0452, 56.0
    parts += capacitor_body(M, x_rear, L, yc, zc, r)
    ends = []
    for dz, dy in ((3.4, 0.0), (-3.4, 0.0)):
        base = Vector((x_rear + 0.9 * MM, yc + dy * MM, zc + dz * MM))
        tp, end, d = terminal(M, base, (0, 1, 0))
        parts += tp
        ends.append((end, d))
    for xc, rail in ((-0.0872, -10.0), (-0.0548, -11.7)):
        parts.append(G.lathe('liner', [(G_mm([(-3.6, r - 0.2), (-3.6, 9.0), (3.6, 9.0), (3.6, r - 0.2)]), True)], 24,
                             Vector((xc, yc, zc)), X, Z, M['rubber']))
        parts.append(p_clamp('pclamp', xc, yc, zc, 9.3, M, rail_y=-11.7))
        sy = -11.7 - 1.2  # outer face of the stem
        hc = Vector((xc, sy * MM, zc + 7.6 * MM))
        head = G.lathe('pan_head', [(G_mm([(0, 0), (0, 2.5), (0.7, 2.4), (1.3, 1.9), (1.6, 1.0), (1.65, 0)]), False)], 16, hc, -Y, X, M['steel_dark'])
        G.boolean(head, [G.box('slot', hc - Y * 1.6 * MM, (0.6 * MM, 6 * MM, 1.6 * MM), Matrix((X, Z, Y)).transposed())])
        parts.append(head)
        if rail > -11.0:  # packing washers between the stem and the narrower front rail
            for k in range(2):
                y0 = (-11.7 + 0.02) + k * 0.84  # from the stem inward
                parts.append(G.lathe('washer', [(G_mm([(0, 1.7), (0, 3.3), (0.8, 3.3), (0.8, 1.7)]), True)], 16,
                                     Vector((xc, y0 * MM, zc + 7.6 * MM)), Y, X, M['steel' if k else 'brass']))
    # wires: from the crimp barrels into the grommet
    for k, ((e, d), col) in enumerate(zip(ends, ('wire_orange', 'polymer'))):
        tgt = PORT + Z * (1.0 if k == 0 else -1.0) * MM + Y * 0.8 * MM
        pts = bezier(e, e + d * 2.5 * MM + X * 3.0 * MM, tgt - Y * 6 * MM - X * 2 * MM, tgt, 16)
        parts.append(G.tube_path('wire', pts, 0.95 * MM, 8, M[col]))
    parts.append(grommet(M))
    obj = G.join('cell_salvaged_capacitor', parts)
    G.sharp_by_angle(obj, 35)
    return obj, None


def build_overclocked(M):
    """Mk II: finned, machined nanite cell with twin glowing cores behind windows, glowing top vents between the
    fins, a lattice-shard window on the rear boss, bolted through to the rail."""
    parts = []
    x0, x1 = -0.1015, -0.0435          # body length along X
    yi, yo = -0.0128, -0.0290          # inner / outer face
    z0, z1 = 0.0175, 0.0405
    yc, zc = (yi + yo) / 2, (z0 + z1) / 2
    body = G.prism('oc_body', G.rounded_rect((yo - yi) * -1, z1 - z0, 2.2 * MM, 3), x1 - x0, Vector((x0, yc, zc)), Y, Z, X, w0=0)
    cuts = []
    # twin core windows on the outer face
    for zz in (zc - 5.2 * MM, zc + 5.2 * MM):
        cuts.append(G.prism('win', G.stadium(42 * MM, 5.0 * MM, 6), 5.0 * MM, Vector(((x0 + x1) / 2 - 1.5 * MM, yo, zz)), X, Z, Y, w0=-1.0 * MM))
    # vent channels on the top face (between the fins)
    for yy in (-0.01725, -0.02095, -0.02465):
        cuts.append(G.prism('vent', G.stadium(34 * MM, 2.0 * MM, 4), 4.0 * MM, Vector(((x0 + x1) / 2 + 2 * MM, yy, z1)), X, Y, -Z, w0=-1.0 * MM))
    # counterbores for the through-bolts
    for xb in (-0.0935, -0.0505):
        cuts.append(G.prism('cb', G.circle(2.9 * MM, 16), 3.2 * MM, Vector((xb, yo, zc)), X, Z, Y, w0=-1.0 * MM))
    G.boolean(body, cuts)
    body.data.materials.clear(); body.data.materials.append(M['anodized'])
    parts.append(body)
    # glowing cores and vent floors (emissive)
    for zz in (zc - 5.2 * MM, zc + 5.2 * MM):
        parts.append(G.lathe('core', [(G_mm([(0, 0), (0, 2.3), (43, 2.3), (43, 0)]), False)], 12, Vector((x0 + 6.0 * MM, yo + 2.7 * MM, zz)), X, Z, M['core_fluid']))
        for xb in (-0.0795, -0.0655):  # retaining bars across the windows
            parts.append(G.box('bar', Vector((xb, yo + 0.35 * MM, zz)), (1.6 * MM, 6.4 * MM, 0.9 * MM), Matrix((X, Z, Y)).transposed(), M['steel']))
    for yy in (-0.01725, -0.02095, -0.02465):
        parts.append(G.box('vfloor', Vector(((x0 + x1) / 2 + 2 * MM, yy, z1 - 2.6 * MM)), (35 * MM, 2.4 * MM, 0.6 * MM), None, M['vent_glow']))
    # heat-sink fins on top
    for yy in (-0.0154, -0.0191, -0.0228, -0.0265):
        fin = G.prism('fin', [(-26 * MM, 0), (26 * MM, 0), (24.5 * MM, 3.8 * MM), (-24.5 * MM, 3.8 * MM)], 1.1 * MM,
                      Vector(((x0 + x1) / 2 + 2 * MM, yy, z1 - 0.3 * MM)), X, Z, Y)
        fin.data.materials.clear(); fin.data.materials.append(M['anodized'])
        G.bevel(fin, 0.25 * MM, 1, 30, weighted=True)
        parts.append(fin)
    # Warden-orange front plate with four screws
    fp = G.prism('oc_front', G.rounded_rect((yo - yi) * -1 + 1.0 * MM, z1 - z0 + 1.0 * MM, 2.6 * MM, 3), 2.6 * MM, Vector((x0, yc, zc)), Y, Z, -X, w0=-0.2 * MM)
    fp.data.materials.clear(); fp.data.materials.append(M['paint_orange'])
    G.bevel(fp, 0.35 * MM, 2, 30)
    parts.append(fp)
    for dy, dz in ((-5.6, -8.4), (5.6, -8.4), (-5.6, 8.4), (5.6, 8.4)):
        c = Vector((x0 - 2.4 * MM, yc + dy * MM, zc + dz * MM))
        h = G.lathe('fscrew', [(G_mm([(0, 0), (0, 1.3), (0.5, 1.2), (0.8, 0.8), (0.9, 0)]), False)], 10, c, -X, Z, M['steel'])
        parts.append(h)
    # rear boss with the lattice shard window + cable gland
    rb = Vector((x1, yc + 1.5 * MM, zc + 3.0 * MM))
    boss = G.lathe('oc_boss', [(G_mm([(0, 5.6), (0, 6.2), (0.4, 6.6), (2.4, 6.6), (2.8, 6.1), (2.8, 3.6), (2.2, 3.4), (1.2, 3.4)]), True)], 20, rb, X, Z, M['steel_dark'])
    parts.append(boss)
    shard = crystal_local('oc_shard', rb + X * 0.4 * MM, X, Z, 1.2, 4.2, 3.2, M['crystal'])
    parts.append(shard)
    gl = Vector((x1, yc - 3.5 * MM, zc - 5.5 * MM))
    parts.append(G.lathe('gland', [(G_mm([(0, 0), (0, 2.8), (1.6, 2.8), (2.0, 2.2), (3.6, 2.0), (3.6, 1.5), (3.6, 0)]), False)], 6, gl, X, Z, M['brass'], phase=math.radians(30)))
    e = gl + X * 3.6 * MM
    tgt = PORT + Y * 0.8 * MM
    pts = bezier(e, e + X * 6 * MM, tgt - Y * 7 * MM - X * 1.5 * MM, tgt, 18)
    parts.append(G.tube_path('cable', pts, 1.45 * MM, 10, M['polymer']))
    parts.append(grommet(M))
    # through-bolts (socket heads in the counterbores) and the front spacer
    for xb in (-0.0935, -0.0505):
        c = Vector((xb, yo + 2.2 * MM, zc))
        h = G.lathe('sbolt', [(G_mm([(0, 0), (0, 2.3), (1.9, 2.3), (2.2, 2.0), (2.2, 0)]), False)], 16, c, -Y, Z, M['steel'])
        G.boolean(h, [G.prism('hs', G.circle(1.2 * MM, 6), 1.6 * MM, c - Y * 2.2 * MM, X, Z, Y, w0=-0.1 * MM)])
        parts.append(h)
    parts.append(G.lathe('spacer', [(G_mm([(0, 2.0), (0, 3.4), (2.9, 3.4), (2.9, 2.0)]), True)], 16, Vector((-0.0935, -0.0099, zc)), -Y, Z, M['brass']))
    obj = G.join('cell_overclocked', parts)
    G.sharp_by_angle(obj, 35)
    return obj, None


def crystal_local(name, base, axis, ref, r0, length, rmax, mat, seed=7, sides=6):
    import random
    rnd = random.Random(seed)
    a, e1, e2 = G.frame(axis, ref)
    rings = [(0.0, rmax * 0.8), (length * 0.45, rmax), (length * 0.8, rmax * 0.55), (length, 0.0)]
    verts, faces, idx = [], [], []
    for i, (s, r) in enumerate(rings):
        if r == 0:
            verts.append(base + a * s * MM); idx.append([len(verts) - 1] * sides); continue
        row = []
        for k in range(sides):
            th = 2 * math.pi * k / sides + i * 0.2 + rnd.uniform(-0.12, 0.12)
            rr = r * rnd.uniform(0.85, 1.1)
            verts.append(base + a * (s + rnd.uniform(-0.2, 0.2)) * MM + (e1 * math.cos(th) + e2 * math.sin(th)) * rr * MM)
            row.append(len(verts) - 1)
        idx.append(row)
    faces.append(tuple(idx[0][::-1]))
    for i in range(len(rings) - 1):
        a_, b_ = idx[i], idx[i + 1]
        for k in range(sides):
            k2 = (k + 1) % sides
            q = []
            for v in (a_[k], a_[k2], b_[k2], b_[k]):
                if v not in q:
                    q.append(v)
            if len(q) == 4:
                faces.append((q[0], q[1], q[2])); faces.append((q[0], q[2], q[3]))
            else:
                faces.append(tuple(q))
    o = G.mesh_obj(name, verts, faces, mat, smooth=False)
    for p in o.data.polygons:
        p.use_smooth = False
    return o
