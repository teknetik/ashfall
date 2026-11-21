# FROZEN COPY of pistol/pgeom.py as it stood at the pistol hand-over (20 Nov 2026, 18:00), kept here so the grip family builds
# from files its own agent owns. The numbers are the interface (grip/INTERFACE.md); do not let the two drift: if the
# pistol geometry changes, the interface changes first.
# Shared geometry of the scrap pistol's grip region, used by pistol/build.py and grip/build.py so that the old scales,
# the new side plates, the wrap and the new core all come from the same numbers (grip/INTERFACE.md).
# Frames: P = pistol metric frame (metres; muzzle -X, up +Z, right +Y). G = grip frame: origin G0, +S up the grip
# axis, +U toward the front strap. Helper inputs are millimetres.
import math
import numpy as np
from mathutils import Vector
import geo as G

MM = 0.001
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
G0 = Vector((0.080, 0.0, -0.030))
S_ = Vector((-0.42038, 0.0, 0.90736))
U_ = Vector((-0.90736, 0.0, -0.42038))
BORE_Y, BORE_Z = 0.75, 58.85            # bore axis (mm), from the skin; mouth at X = -130.1
MOUTH_X = -130.1

# the old scale = the template of the new side plates (grip/interface.json plate.outline_G_us), (U, S) in mm
OUTLINE = [(27.4, 39.7), (28.2, 27.0), (26.5, 10.0), (26.0, -10.0), (25.0, -30.0), (24.2, -41.0), (21.5, -44.6), (-22.5, -50.8),
           (-26.6, -47.5), (-27.8, -30.0), (-27.8, -6.0), (-26.0, 8.0), (-23.0, 21.0), (-24.2, 32.0), (-12.5, 32.0), (-12.5, 42.0),
           (-20.0, 42.0), (-18.5, 44.5), (-18.0, 56.5), (-5.5, 54.7), (11.4, 58.7), (19.4, 50.9)]
HOLES = {'A': (-4.0, 40.0), 'B': (-4.0, 8.0), 'C': (22.0, -2.0), 'D': (-22.0, -44.0)}
PIN = (-16.0, 37.0)                     # housing pin, along Y
BITE = (-24.2, -12.5, 32.0, 42.0)       # u0, u1, s0, s1: the bite of the scales and plates round the pin's ear
TANG_END = 2.0                          # S of the broken end of the tang stub
# T-section of the tang in (U, Y): web and dovetailed head
TANG_T = [(5.0, -3.4), (5.0, 3.4), (-13.0, 3.4), (-16.0, 6.0), (-19.0, 6.0), (-19.0, -6.0), (-16.0, -6.0), (-13.0, -3.4)]
# the matching slot (housing, and the new core): 0.15 clear all round
T_SLOT = [(-19.25, -6.15), (-16.05, -6.15), (-13.0, -3.55), (-10.5, -3.55), (-10.5, 3.55), (-13.0, 3.55), (-16.05, 6.15), (-19.25, 6.15)]
T_TOP = 40.0                            # the T-head ends here; above it only the web runs up into the frame


def P(x, y, z):
    return Vector((x, y, z)) * MM


def GP(u, s, y=0.0):
    return G0 + U_ * (u * MM) + S_ * (s * MM) + Y * (y * MM)


def to_us(p):
    """P point (metres) -> (u, s, y) in mm."""
    d = Vector(p) - G0
    return d.dot(U_) / MM, d.dot(S_) / MM, d.y / MM


def xz(name, poly, y0, y1, mat=None):
    """Prism of an (X, Z) outline in mm between two Y values in mm."""
    return G.prism(name, [(a * MM, b * MM) for a, b in poly], (y1 - y0) * MM, (0, y0 * MM, 0), X, Z, Y, mat, w0=0.0)


def us(name, poly, y0, y1, mat=None):
    """Prism of a (U, S) outline in mm between two Y values in mm."""
    return G.prism(name, [(a * MM, b * MM) for a, b in poly], (y1 - y0) * MM, G0 + Y * (y0 * MM), U_, S_, Y, mat, w0=0.0)


def uy(name, poly, s0, s1, mat=None):
    """Prism of a (U, Y) outline in mm along the grip axis between two S values in mm."""
    return G.prism(name, [(a * MM, b * MM) for a, b in poly], (s1 - s0) * MM, G0 + S_ * (s0 * MM), U_, Y, S_, mat, w0=0.0)


def ycyl(name, u, s, r, y0, y1, segs=16, mat=None):
    """Cylinder along Y at grip position (u, s), mm."""
    return G.cyl(name, GP(u, s, y0), GP(u, s, y1), r * MM, segs, mat)


def fillet(poly, r=2.0, n=3):
    """Ease the corners of a polygon to about radius r (mm)."""
    out = []
    N = len(poly)
    for i in range(N):
        a = Vector(poly[i - 1]); b = Vector(poly[i]); c = Vector(poly[(i + 1) % N])
        e0 = (a - b); e1 = (c - b)
        d = min(r, e0.length * 0.45, e1.length * 0.45)
        p0 = b + e0.normalized() * d; p1 = b + e1.normalized() * d
        for k in range(n + 1):
            t = k / n
            q = p0 * (1 - t) ** 2 + b * 2 * t * (1 - t) + p1 * t ** 2
            out.append((q.x, q.y))
    return out


def outline(r=2.0):
    return fillet(OUTLINE, r)


# ---------------------------------------------------------------------- the grip's outer surface (wood and steel)
# From the skin's side silhouette (work/skin_mask_side.npy), less about 0.9 mm for the leather that lies on it.
_ST = [-58, -52, -45, -40, -36, -25, -15, -3, 9, 21, 30, 36, 39, 42.6, 62]
_UB = [-29.3, -29.6, -29.6, -29.7, -29.7, -29.8, -29.8, -29.6, -27.4, -26.3, -25.8, -24.4, -21.7, -19.0, -19.0]   # back strap
_UF = [29.3, 29.4, 29.4, 28.3, 28.3, 28.3, 28.4, 28.8, 28.8, 28.9, 29.0, 29.0, 29.0, 29.0, 29.0]                  # front strap
_BW = [18.0, 18.6, 19.2, 19.3, 19.4, 19.5, 19.4, 19.2, 19.0, 18.7, 18.5, 18.3, 18.2, 18.1, 16.5]                  # half width
NEXP = 3.0


def section(s):
    """(u_back, u_front, half_width) of the grip at level s (mm)."""
    return float(np.interp(s, _ST, _UB)), float(np.interp(s, _ST, _UF)), float(np.interp(s, _ST, _BW))


def surf(theta, s, offset=0.0):
    """Point on the grip surface (P, metres) and its outward normal in the section plane. theta = 0 is the front strap,
    90 degrees the right side, 180 the back strap. offset in mm, outward."""
    ub, uf, b = section(s)
    uc = (ub + uf) / 2; a = (uf - ub) / 2
    c, sn = math.cos(theta), math.sin(theta)
    e = 2.0 / NEXP
    u = uc + a * math.copysign(abs(c) ** e, c)
    y = b * math.copysign(abs(sn) ** e, sn)
    # normal of the superellipse |x/a|^n + |y/b|^n = 1
    nx = math.copysign(abs((u - uc) / a) ** (NEXP - 1), c) / a
    ny = math.copysign(abs(y / b) ** (NEXP - 1), sn) / b
    ln = math.hypot(nx, ny) or 1.0
    nx, ny = nx / ln, ny / ln
    n = (U_ * nx + Y * ny).normalized()
    return GP(u + nx * offset, s, y + ny * offset), n


def ring(s, n=44, offset=0.0, tilt=None):
    """Closed ring of n points round the grip at level s. tilt = (amplitude mm, phase rad): a diagonal loop."""
    out = []
    for k in range(n):
        th = 2 * math.pi * k / n
        ss = s + (tilt[0] * math.cos(th - tilt[1]) if tilt else 0.0)
        out.append(surf(th, ss, offset)[0])
    return out


def solid(name, s0=-58.0, s1=62.0, step=6.0, n=44, mat=None, offset=0.0):
    """The whole grip surface as a closed solid (lofted rings)."""
    k = max(2, int(round((s1 - s0) / step)))
    rings = [ring(s0 + (s1 - s0) * i / k, n, offset) for i in range(k + 1)]
    return G.loft(name, rings, mat)


def band(name, s, width, thick, n=48, mat=None, tilt=None, lift=0.1, wobble=0.0, seed=1, th0=0.0, th1=None, turns=None, pitch=0.0, peel=0.0):
    """A strap round the grip: `width` along the axis, `thick` outward, lying `lift` above the surface. tilt as ring().
    turns + pitch: a helical winding instead of a closed loop (tape), `turns` round, advancing `pitch` mm a turn;
    peel: the last few steps of a winding lift off the surface by up to this many mm (a loose end).
    Returns the object and the centreline points on its outer face (for a peel path)."""
    import random
    rnd = random.Random(seed)
    closed = turns is None
    m = n if closed else int(round(n * turns)) + 1
    verts, faces, centre = [], [], []
    for k in range(m):
        th = 2 * math.pi * k / n + th0
        sc = s + (tilt[0] * math.cos(th - tilt[1]) if tilt else 0.0) + (pitch * k / n if not closed else 0.0)
        w0 = -width / 2 + (rnd.uniform(-wobble, wobble) if wobble else 0.0)
        w1 = width / 2 + (rnd.uniform(-wobble, wobble) if wobble else 0.0)
        lf = lift
        if peel and not closed and k > m - 7:
            lf = lift + peel * ((k - (m - 7)) / 6.0) ** 2
            w0 *= 1.0 - 0.25 * (k - (m - 7)) / 6.0
        a, _ = surf(th, sc + w0, lf)
        b, _ = surf(th, sc + w1, lf)
        c, _ = surf(th, sc + w1, lf + thick)
        d, _ = surf(th, sc + w0, lf + thick)
        verts += [a, b, c, d]
        centre.append((surf(th, sc, lift + thick)[0], surf(th, sc, 0.0)[1]))
    rng = m if closed else m - 1
    for i in range(rng):
        j = (i + 1) % m
        for q in range(4):
            q2 = (q + 1) % 4
            faces.append((i * 4 + q, i * 4 + q2, j * 4 + q2, j * 4 + q))
    if not closed:
        faces.append((0, 1, 2, 3)); faces.append(tuple((m - 1) * 4 + q for q in (3, 2, 1, 0)))
    o = G.mesh_obj(name, verts, faces, mat, recalc=True)
    return o, centre


def inflate(o, d_mm):
    """Push every vertex out along its normal (a cutter that leaves d_mm of clearance round a part)."""
    me = o.data
    me.update()
    for v in me.vertices:
        v.co = v.co + v.normal * (d_mm * MM)
    me.update()
    return o


# ---------------------------------------------------------------------- the new grip's outer surface (bare alloy)
# The skin's silhouette itself (no leather on the new grip), flatter sides (the plates lie on them).
_ST_N = [-58, -52, -45, -36, -25, -15, -3, 9, 21, 30, 36, 39, 42.6, 62]
_UB_N = [-30.1, -30.4, -30.4, -30.5, -30.6, -30.6, -30.4, -28.2, -27.1, -26.6, -25.2, -22.5, -19.8, -19.8]
_UF_N = [29.6, 29.8, 29.8, 29.8, 29.8, 29.8, 29.8, 29.9, 29.9, 29.9, 29.9, 29.9, 29.9, 29.9]
_BW_N = [18.9, 19.3, 19.55, 19.55, 19.55, 19.55, 19.55, 19.55, 19.55, 19.55, 19.55, 19.4, 19.2, 17.8]
NEXP_N = 6.0


def surf_new(theta, s, offset=0.0):
    ub = float(np.interp(s, _ST_N, _UB_N)); uf = float(np.interp(s, _ST_N, _UF_N)); b = float(np.interp(s, _ST_N, _BW_N))
    uc = (ub + uf) / 2; a = (uf - ub) / 2
    c, sn = math.cos(theta), math.sin(theta)
    e = 2.0 / NEXP_N
    u = uc + a * math.copysign(abs(c) ** e, c)
    y = b * math.copysign(abs(sn) ** e, sn)
    nx = math.copysign(abs((u - uc) / a) ** (NEXP_N - 1), c) / a
    ny = math.copysign(abs(y / b) ** (NEXP_N - 1), sn) / b
    ln = math.hypot(nx, ny) or 1.0
    nx, ny = nx / ln, ny / ln
    return GP(u + nx * offset, s, y + ny * offset), (U_ * nx + Y * ny).normalized()


def solid_new(name, s0=-58.0, s1=62.0, step=5.0, n=56, mat=None):
    k = max(2, int(round((s1 - s0) / step)))
    rings = []
    for i in range(k + 1):
        s = s0 + (s1 - s0) * i / k
        rings.append([surf_new(2 * math.pi * j / n, s)[0] for j in range(n)])
    return G.loft(name, rings, mat)


def back_new(s):
    return float(np.interp(s, _ST_N, _UB_N))


def offset_poly(poly, d):
    """Offset a closed 2D polygon outward by d (mm): mitred, for small d."""
    n = len(poly)
    area = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n))
    sg = 1.0 if area > 0 else -1.0
    out = []
    for i in range(n):
        p0 = Vector(poly[i - 1]); p1 = Vector(poly[i]); p2 = Vector(poly[(i + 1) % n])
        e0 = (p1 - p0); e1 = (p2 - p1)
        if e0.length < 1e-9 or e1.length < 1e-9:
            out.append((p1.x, p1.y)); continue
        n0 = Vector((e0.y, -e0.x)).normalized() * sg
        n1 = Vector((e1.y, -e1.x)).normalized() * sg
        b = (n0 + n1)
        if b.length < 1e-9:
            out.append((p1.x + n0.x * d, p1.y + n0.y * d)); continue
        b.normalize()
        k = d / max(0.35, b.dot(n0))
        out.append((p1.x + b.x * k, p1.y + b.y * k))
    return out


# datum of the gimbal damper unit (grip/INTERFACE.md): origin, and D coordinates (mm) -> P
D0_US = (0.0, -26.0, -17.5)


def DP(x, y, z=0.0):
    """Point given in the unit's datum frame D (mm): +X_D = +S, +Y_D = +U, +Z_D = P -Y."""
    return GP(D0_US[0] + y, D0_US[1] + x, D0_US[2] - z)
