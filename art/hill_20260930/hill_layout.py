"""Shared layout for the hill and hero-tree pass (30 September 2026): plain Python, no Blender imports.

Unity metres local to the hill root, which sits at world (0, 0, 0): X east, Y up, Z north (the "west" stair in the
scene's legacy names is on +X). The saved colliders stay authoritative for walking: COL_ENV_hill_plinth (14 x 1.4 x 14),
COL_ENV_hill_surface (top 1.5) and the eighteen COL_ENV_hill_stair_* boxes (6 risers of 0.25 m, 0.6 m treads, 4 m wide)
on the -Z ("north"), +Z ("south") and +X ("west") sides. Nothing authored here may change those heights.
"""
import math

HT = 1.50            # hilltop paving level (top of COL_ENV_hill_surface)
E = 7.00             # retaining-wall face plane (|x| or |z|)
BLOCK = 0.062        # kit block face offset in front of a frame plane
WALL_COURSES = [-0.08, 0.40, 0.85, 1.30]     # rough foot course, two dressed courses; coping 1.30 -> 1.52
COPE_BOT, COPE_TOP, COPE_IN, COPE_OUT = 1.30, 1.52, 0.42, 0.075   # retaining-wall coping (inner width, overhang)
BAND = E - COPE_IN   # 6.58: inner edge of the coping band on the hilltop

STAIR_HW = 2.00      # stair half width (colliders x or z +-2)
CHEEK = 0.42         # stair cheek wall thickness (outside the stair width)
CHEEK_OUT = STAIR_HW + CHEEK
RISE, RUN, NSTEP = 0.25, 0.60, 6
STAIR_LEN = RUN * NSTEP      # 3.6 m from the plinth face to the bottom nosing
CHEEK_HEAD = -0.40   # the cheek's capstone reaches back over the hilltop band to meet the landing
CHEEK_ABOVE = 0.32   # cheek coping top above the nosing line
CHEEK_COPE = 0.16    # raking coping thickness

# sides: (name, outward normal, has stair). The "west" stair of the legacy scene names is on +X.
SIDES = [("north", (0.0, -1.0), True), ("south", (0.0, 1.0), True), ("west", (1.0, 0.0), True), ("east", (-1.0, 0.0), False)]

RING_C = (0.0, 0.0)  # tree ring centre (trunk centroid at ground is (0, -0.35), root flare radius <= 1.8 at y 1.2-1.5)
RO, RI = 3.30, 2.85  # ring outer / inner stone faces
RING_BOT, RING_TOP = HT - 0.04, 1.86          # dressed course (outer face)
RING_CAP = (1.86, 1.99)                        # coping; top 0.49 m above the paving (a seat)
RING_CAP_OVER = 0.05
SOIL_EDGE, SOIL_MID = 1.745, 1.845             # soil inside the ring at the wall and near the trunk
APRON = 3.95         # paved apron round the ring
KERB = 0.10          # bed kerb width
KERB_TOP = HT + 0.03
PATH_HW = 1.50       # paths to the three stairs (+X, +Z, -Z)
LANDING_D = 0.95     # landing depth at each stair head, full stair width
BED_Y = HT - 0.035   # bed soil level

# terminals (existing COL_PROP_hill_market_0x_* collider positions); they now face the tree
TERMINALS = [("Platform terminal 00 SAVE", (5.0, -4.0)), ("Platform terminal 01 RECLAIM", (-5.0, -4.0)),
             ("Platform terminal 02 RECLAIM", (-5.0, 1.0))]
PAD_W, PAD_D, PAD_TOP = 1.55, 1.25, HT + 0.11  # stone pad under each terminal (terminal faces the tree)
LINN = (2.50, 4.70)          # Linn's standing point (npc_linn root)
BOARD = (-5.40, -5.30, 3.5, 0.7)   # community board footprint centre + size (x, z, w, d)
UPLIGHT_ANGLES = [40.0, 128.0, 252.0]  # degrees from +X towards +Z, set in the ring coping
HEAVE_ANGLE = 146.0          # the coping stone a root has lifted (repaired with iron cramps)


def ang(p):
    return math.degrees(math.atan2(p[1] - RING_C[1], p[0] - RING_C[0])) % 360.0


def face_yaw_to_tree(p):
    """Unity yaw (degrees) that turns a +Z-facing object at p to face the ring centre."""
    dx, dz = RING_C[0] - p[0], RING_C[1] - p[1]
    return math.degrees(math.atan2(dx, dz))


def on_path(x, z, margin=0.0):
    """Paving (paths, landings, apron) incl. an optional margin (kerb width)."""
    r = math.hypot(x - RING_C[0], z - RING_C[1])
    if r < APRON + margin:
        return True
    hw = PATH_HW + margin
    if abs(z) <= hw and x > 0:            # +X path (to the "west" stair)
        return True
    if abs(x) <= hw:                      # +Z and -Z paths
        return True
    lw = STAIR_HW + margin
    if abs(x) <= lw and abs(z) >= BAND - LANDING_D - margin:
        return True
    if abs(z) <= lw and x >= BAND - LANDING_D - margin:
        return True
    return False


def in_bed(x, z, margin=0.0):
    """True inside a planted bed (kerbs excluded when margin = KERB)."""
    if abs(x) > BAND - margin or abs(z) > BAND - margin:
        return False
    return not on_path(x, z, margin)


def pad_corners(p, w=PAD_W, d=PAD_D):
    yaw = math.radians(face_yaw_to_tree(p))
    fx, fz = math.sin(yaw), math.cos(yaw)        # facing
    rx, rz = fz, -fx                             # right
    out = []
    for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        out.append((p[0] + rx * a * w / 2 + fx * b * d / 2, p[1] + rz * a * w / 2 + fz * b * d / 2))
    return out


def exclusions():
    """Circles (x, z, r) where the plant scatter must stay clear (terminals, pads, stepping stones, Linn, board)."""
    ex = []
    for _, p in TERMINALS:
        ex.append((p[0], p[1], 1.05))
        # stepping stones to the apron
        r = math.hypot(*p)
        ux, uz = -p[0] / r, -p[1] / r
        s = 0.95
        while r - s > APRON + 0.15:
            ex.append((p[0] + ux * s, p[1] + uz * s, 0.42))
            s += 0.62
    ex.append((LINN[0], LINN[1], 0.75))
    bx, bz, bw, bd = BOARD
    for k in range(5):
        ex.append((bx - bw / 2 + bw * k / 4, bz, 0.55))
    return ex


def stepping_stones(p):
    """Centres of the stepping stones from a terminal pad to the apron kerb."""
    r = math.hypot(*p)
    ux, uz = -p[0] / r, -p[1] / r
    out = []
    s = PAD_D / 2 + 0.42
    while r - s > APRON + KERB + 0.3:
        out.append((p[0] + ux * s, p[1] + uz * s))
        s += 0.62
    return out


# ------------------------------------------------------------------ deterministic ground heights (shared with the scatter)
def _hash(ix, iz, seed):
    h = (ix * 374761393 + iz * 668265263 + seed * 2147483647) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0


def vnoise(x, z, f, seed=0):
    """Smooth value noise in [-1, 1] at frequency f (per metre)."""
    x, z = x * f, z * f
    ix, iz = math.floor(x), math.floor(z)
    fx, fz = x - ix, z - iz
    sx, sz = fx * fx * (3 - 2 * fx), fz * fz * (3 - 2 * fz)
    a, b = _hash(ix, iz, seed), _hash(ix + 1, iz, seed)
    c, d = _hash(ix, iz + 1, seed), _hash(ix + 1, iz + 1, seed)
    return (a + (b - a) * sx + (c - a) * sz + (a - b - c + d) * sx * sz) * 2 - 1


TRUNK_C = (0.0, -0.35)


def bed_y(x, z):
    """Planted-bed soil: 3.5 cm below the paving, a few cm of relief, slightly mounded away from the kerbs."""
    edge = min(BAND - abs(x), BAND - abs(z), math.hypot(x, z) - APRON, abs(abs(x) - PATH_HW) if abs(z) > APRON else 9,
               abs(abs(z) - PATH_HW) if x > APRON else 9)
    mound = 0.022 * min(1.0, max(0.0, (edge - 0.15) / 1.2))
    return BED_Y - 0.01 + mound + 0.012 * vnoise(x, z, 1.7, 3) + 0.006 * vnoise(x, z, 5.3, 4)


def ring_soil_y(x, z):
    """Leaf-litter soil inside the ring: 12 cm below the coping at the wall, rising to the root flare."""
    r = math.hypot(x - RING_C[0], z - RING_C[1])
    rt = math.hypot(x - TRUNK_C[0], z - TRUNK_C[1])
    t = max(0.0, min(1.0, (RI - r) / (RI - 1.0)))
    base = SOIL_EDGE + (SOIL_MID - SOIL_EDGE) * (t * t * (3 - 2 * t))
    flare = 0.06 * max(0.0, 1.0 - (rt - 0.75) / 0.6) if rt > 0.75 else 0.06
    return base + flare + 0.014 * vnoise(x, z, 1.9, 7) + 0.006 * vnoise(x, z, 6.1, 8)
