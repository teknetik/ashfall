#!/usr/bin/env python3
"""Outer Berms ground variety (20 Nov 2026): the story layout and its check.

Writes
  features.json      earthworks (old Warden berm lines and redoubts), craters, sandstone ledges, dunes, tracks
                     (Warden trails, the Karaveen trail, old haul-droid treads, Post sentinel wheel loops)
  placements.json    prefab instances (wreck fields, battle debris, caravan litter, talus, wash and shade scrub)
                     plus the chunk list the installer builds from the GLB (filled in by meshes.py)
  layout-check.json  every rejected or trimmed item and the clearances that decided it, plus the final minimum
                     distances of each kept object to spawns, salvage, landmarks, sites, routes, colliders and the edge

All gameplay positions come from survey.json (the saved scene, BermsVarietyPass20261120 survey), so nothing here can
move a site, spawn, loot node, landmark or collider: objects that would crowd one are trimmed or dropped. Story:
lore.md has the Wardens' "hard-fought stands at the outer berms" and the Outer Berms "littered with the half-buried
ruins of ... the outer reaches of a vast industrial complex: collapsed processing halls, rusted conveyor spines,
shattered drone bays". No new history is invented: the lines, craters and wrecks are unnamed remains of those stands.
Run: uv run --with numpy --with scipy python layout.py
"""
import json, math
from pathlib import Path
import numpy as np
from scipy import ndimage
from bv_common import Field, HERE, sites, routes, survey, poly_dist, seg_dist, OLD

F = Field()
SV = survey()
RNG = np.random.default_rng(20261120)
WIND = np.array([1.0, 0.38]); WIND /= np.linalg.norm(WIND)          # wind blows toward ENE (from the WSW)
CREST_YAW = math.degrees(math.atan2(-WIND[1], WIND[0]))            # not used directly; dunes use WIND below

# ----------------------------------------------------------------------------------------------- gameplay data
SITES = sites()
ROUTES = routes()
MK = SV['markers']
SPAWNS = [(m['pos'][0], m['pos'][2]) for m in MK if m['kind'] == 'spawn']
NODES = [(m['pos'][0], m['pos'][2]) for m in MK if m['kind'] in ('salvage', 'interactable', 'loot', 'waystation', 'respawn', 'target')]
LANDMARKS = [(m['pos'][0], m['pos'][2]) for m in MK if m['kind'] in ('landmark', 'misc')]
COLS = []
for c in SV['colliders']:
    if c['trigger'] or c['path'].startswith('Outer Berms/Berms expanse/Boundary'): continue
    x0, _, z0 = c['min']; x1, _, z1 = c['max']
    if (x1 - x0) > 120 or (z1 - z0) > 120: continue          # ground-sized colliders (old Berms ground etc.)
    COLS.append((x0, z0, x1, z1, c['path']))
COL_ARR = np.array([c[:4] for c in COLS]) if COLS else np.zeros((0, 4))


def d_rect(x, z):
    if not len(COL_ARR): return 1e9
    dx = np.maximum(np.maximum(COL_ARR[:, 0] - x, 0), x - COL_ARR[:, 2])
    dz = np.maximum(np.maximum(COL_ARR[:, 1] - z, 0), z - COL_ARR[:, 3])
    return float(np.hypot(dx, dz).min())


def d_pts(x, z, pts):
    if not pts: return 1e9
    a = np.asarray(pts); return float(np.hypot(a[:, 0] - x, a[:, 1] - z).min())


def d_sites(x, z):
    return min(math.hypot(x - s['centre'][0], z - s['centre'][1]) - (4 if s['waystation'] else 0) for s in SITES)


def d_routes(x, z, extra=()):
    d = min(poly_dist(x, z, r) for r in ROUTES)
    for t in extra: d = min(d, poly_dist(x, z, t))
    return d


def d_old(x, z):
    x0, x1, z0, z1 = OLD
    return math.hypot(max(x0 - x, 0, x - x1), max(z0 - z, 0, z - z1))


def d_edge(x, z):
    return float(F.sample(F.d_in, x, z)) if F.sample(F.playable.astype(float), x, z) > 0.5 else -1.0


def slope_deg(x, z, r=2.0):
    h = [F.ground(x + dx, z + dz) for dx, dz in ((r, 0), (-r, 0), (0, r), (0, -r))]
    return math.degrees(math.atan(math.hypot(h[0] - h[1], h[2] - h[3]) / (2 * r)))


def rock_at(x, z):
    return float(F.sample(F.rocks, x, z))


# clearance classes (metres): spawns, nodes (loot/salvage/interactables), landmarks, site centres, routes/tracks,
# existing colliders, playable edge (inside distance), old Berms ground footprint
CLEAR = {
    'ledge':   dict(spawn=25, node=10, landmark=8, site=30, route=6, col=3, edge=8, old=14),
    'berm':    dict(spawn=15, node=8, landmark=6, site=24, route=5, col=3, edge=7, old=14),
    'dune':    dict(spawn=12, node=8, landmark=6, site=22, route=5, col=3, edge=6, old=14),
    'rim':     dict(spawn=8, node=6, landmark=4, site=16, route=2.5, col=2, edge=6, old=14),
    'wreck':   dict(spawn=20, node=8, landmark=6, site=26, route=5, col=3, edge=8, old=14),
    'boulder': dict(spawn=14, node=5, landmark=4, site=22, route=3.5, col=2, edge=5, old=12),
    'small':   dict(spawn=5, node=3, landmark=3, site=18, route=1.5, col=1, edge=4, old=10),
}


def check(x, z, cls, radius=0.0, tracks=()):
    """Returns (ok, worst) where worst names the first failed clearance (centre distance minus the object radius)."""
    c = CLEAR[cls]
    tests = (('edge', d_edge(x, z) - radius), ('old', d_old(x, z) - radius), ('site', d_sites(x, z) - radius),
             ('spawn', d_pts(x, z, SPAWNS) - radius), ('node', d_pts(x, z, NODES) - radius),
             ('landmark', d_pts(x, z, LANDMARKS) - radius), ('route', d_routes(x, z, tracks) - radius),
             ('col', d_rect(x, z) - radius))
    for k, v in tests:
        if v < c[k]: return False, f'{k} {v:.1f} < {c[k]}'
    return True, None


REPORT = dict(rejected=[], trimmed=[], kept={})


def settle(name, x, z, cls, radius, tracks=(), extra=lambda x, z: None, rmax=30):
    """First position at or near (x, z) (rings of 3 m out to rmax) that passes the class clearances and `extra`
    (returns a reason string when it fails). Reports nudges; returns None when nothing fits."""
    def fails(xx, zz):
        ok, why = check(xx, zz, cls, radius, tracks)
        return why if not ok else extra(xx, zz)
    why0 = fails(x, z)
    if not why0: return x, z
    for r in np.arange(3, rmax + 0.1, 3):
        for a in np.linspace(0, 2 * math.pi, max(8, int(r * 1.5)), endpoint=False):
            xx, zz = x + r * math.cos(a), z + r * math.sin(a)
            if not fails(xx, zz):
                REPORT['trimmed'].append(dict(what=name, nudged=[round(xx, 1), round(zz, 1)], by=round(float(r), 1), because=why0))
                return xx, zz
    REPORT['rejected'].append(dict(what=name, at=[x, z], because=why0))
    return None


def spline(pts, step=1.0, closed=False):
    """Catmull-Rom through pts, resampled every ~step metres."""
    P = np.asarray(pts, float)
    if closed: P = np.vstack([P[-1], P, P[0], P[1]])
    else: P = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        n = max(2, int(np.linalg.norm(p2 - p1) / step))
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-2])
    return np.array(out)


# ----------------------------------------------------------------------------------------------- tracks (paint)
WASHES = json.loads((F and (HERE.parent / 'berms_expanse_20261002/footprint.json')).read_text())['washes']
if isinstance(WASHES, str):
    import ast; WASHES = ast.literal_eval(WASHES)

TRACKS = [dict(name=f'Warden trail {i + 1}', kind='warden', pts=r, width=2.4) for i, r in enumerate(ROUTES)]
TRACKS += [
    # Karaveen trail: from the gate side, past the caravan ambush (the wreck sits on it), north of the mesa, out NW
    dict(name='Karaveen trail', kind='caravan', width=7.0,
         pts=[[-106, 30], [-140, 40], [-182, 55], [-214, 62], [-250, 78], [-296, 98], [-336, 122], [-372, 158],
              [-420, 176], [-470, 182], [-512, 172]]),
    # old haul-droid treads from the depot side toward the scrapyard and the Tube pylon (the industrial reach)
    dict(name='Haul tread', kind='haul', width=3.2,
         pts=[[-106, -44], [-140, -92], [-196, -114], [-252, -126], [-318, -128], [-372, -120], [-410, -108]]),
    dict(name='Haul tread north', kind='haul', width=3.2,
         pts=[[-300, -40], [-286, 10], [-282, 40]]),
]
# Post sentinel wheel loops round the post relay (wheeled droids patrol there)
for k, (r, ph) in enumerate(((15.0, 0.0), (21.0, 1.3))):
    loop = [[-432 + r * math.cos(a + ph) * (1 + 0.15 * math.sin(3 * a)), 22 + r * math.sin(a + ph) * 0.85] for a in np.linspace(0, 2 * math.pi, 14)]
    TRACKS.append(dict(name=f'Sentinel loop {k + 1}', kind='wheel', width=0.35, pts=loop))
TRACK_LINES = [t['pts'] for t in TRACKS if t['kind'] in ('caravan', 'haul')]

# ----------------------------------------------------------------------------------------------- earthworks
LINES = [
    dict(name='Line one', h=1.6, w=9.0, pts=[[-150, -120], [-160, -100], [-168, -60], [-172, -20], [-176, 10], [-180, 40], [-183, 70], [-182, 95], [-190, 118]]),
    dict(name='Line three', h=1.5, w=8.5, pts=[[-305, -74], [-300, -45], [-296, -15]]),
    dict(name='Line four', h=1.4, w=8.0, pts=[[-432, 112], [-426, 145], [-419, 178]]),
    dict(name='Line five', h=1.6, w=8.5, pts=[[-262, -24], [-258, 6], [-250, 30]]),
    dict(name='Line six', h=1.5, w=8.0, pts=[[-474, 36], [-466, 66], [-458, 98]]),
    dict(name='Line seven', h=1.5, w=8.0, pts=[[-350, -150], [-346, -122], [-338, -96]]),
    dict(name='Line two', h=1.4, w=8.0, pts=[[-392, -150], [-398, -110], [-402, -70], [-400, -40], [-396, -10], [-392, 20], [-390, 50], [-386, 80]]),
    dict(name='North redoubt', h=1.5, w=7.0, arc=dict(c=[-300, 176], r=14, a0=70, a1=290)),
    dict(name='South redoubt', h=1.4, w=7.0, arc=dict(c=[-205, -120], r=12, a0=70, a1=290)),
    dict(name='West redoubt', h=1.3, w=6.5, arc=dict(c=[-525, 40], r=11, a0=110, a1=330)),
]


def arc_pts(a):
    c, r = a['c'], a['r']
    return [[c[0] + r * math.cos(math.radians(t)), c[1] + r * math.sin(math.radians(t))] for t in np.arange(a['a0'], a['a1'] + 1, 10)]


def wash_dist(x, z):
    return min(poly_dist(x, z, w['pts']) - w['width'] * 0.75 for w in WASHES)


earthworks = []
for L in LINES:
    pts = arc_pts(L['arc']) if 'arc' in L else L['pts']
    P = spline(pts, 1.0)
    rad = L['w'] * 0.5
    ok = []
    for x, z in P:
        good, why = check(x, z, 'berm', rad, tracks=TRACK_LINES)
        if good and wash_dist(x, z) < 0: good, why = False, 'wash'
        if good and rock_at(x, z) > 0.5: good, why = False, 'outcrop rock'
        ok.append((good, why))
    # deliberate breaches: old gaps worn through the line every 30-70 m
    s = 0.0; nxt = RNG.uniform(35, 80)
    for i in range(1, len(P)):
        s += float(np.linalg.norm(P[i] - P[i - 1]))
        if s > nxt:
            w = int(RNG.uniform(3, 6))
            for k in range(i, min(len(P), i + w)): ok[k] = (False, 'breach')
            nxt = s + w + RNG.uniform(40, 90)
    segs = []; cur = []
    for (good, why), p in zip(ok, P):
        if good: cur.append([round(float(p[0]), 2), round(float(p[1]), 2)])
        else:
            if len(cur) >= 10: segs.append(cur)
            elif cur: REPORT['trimmed'].append(dict(what=L['name'] + ' short piece', at=cur[0], len=len(cur)))
            cur = []
    if len(cur) >= 10: segs.append(cur)
    reasons = {}
    for g, why in ok:
        if not g: reasons[why.split(' ')[0]] = reasons.get(why.split(' ')[0], 0) + 1
    REPORT['trimmed'].append(dict(what=L['name'], metres_cut=reasons))
    earthworks.append(dict(name=L['name'], h=L['h'] + 0.25, w=L['w'] + 1.0, segments=segs))

# ----------------------------------------------------------------------------------------------- ledges
LEDGES = [  # name, x, z, length, width, height, yaw (deg, long axis from +X toward +Z), tilt (deg), kind
    ('Ledge north court', -250, 100, 18, 8, 2.2, 20, 0, 'ledge'),
    ('Ledge relay south', -355, -55, 16, 7, 1.8, -30, 0, 'ledge'),
    ('Ledge post north', -455, 75, 20, 8, 2.6, 60, 0, 'ledge'),
    ('Ledge scrapyard south', -330, -140, 14, 7, 2.0, 10, 0, 'ledge'),
    ('Ledge west edge', -522, 72, 18, 9, 3.0, 80, 0, 'ledge'),
    ('Slab cache north', -228, -120, 12, 6, 1.6, -50, 9, 'slab'),
    ('Slab waystation west', -305, 66, 10, 6, 1.4, 35, 11, 'slab'),
    ('Ledge fans', -468, -70, 14, 6, 2.2, 30, 0, 'ledge'),
    ('Ledge reaper north', -192, 150, 14, 6, 1.8, -15, 0, 'ledge'),
    ('Tor north strip', -352, 172, 10, 8, 3.0, 40, 0, 'tor'),
    ('Slab butte west', -276, -46, 11, 6, 1.5, 100, 10, 'slab'),
    ('Ledge depot south', -132, -108, 12, 6, 1.8, 15, 0, 'ledge'),
    ('Ledge southwest', -538, -92, 16, 8, 2.8, -20, 0, 'ledge'),
    ('Tor northgate', -142, 112, 8, 6, 2.6, 0, 0, 'tor'),
    ('Slab pylon east', -372, -82, 10, 5, 1.4, -70, 8, 'slab'),
]
def outline(x, z, L, W, yaw, kind):
    """Noise-warped rounded outline (star-shaped about the centre): lobes and bays, no straight box sides."""
    n = 96; th = np.linspace(0, 2 * math.pi, n, endpoint=False)
    ph = RNG.uniform(0, 6.28, 5)
    rr = 1 + 0.12 * np.sin(2 * th + ph[0]) + 0.09 * np.sin(3 * th + ph[1]) + 0.06 * np.sin(5 * th + ph[2]) + 0.04 * np.sin(9 * th + ph[3]) + 0.025 * np.sin(17 * th + ph[4])
    sq = {'ledge': 2.6, 'slab': 2.8, 'tor': 2.1, 'block': 2.4}[kind]
    ex = (np.abs(np.cos(th)) ** sq + np.abs(np.sin(th)) ** sq) ** (-1 / sq)
    lx = np.cos(th) * ex * rr * L * 0.5; lz = np.sin(th) * ex * rr * W * 0.5
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    return [[round(x + a * cy - b * sy, 2), round(z + a * sy + b * cy, 2)] for a, b in zip(lx, lz)]


ledges = []
for name, x, z, L, W, h, yaw, tilt, kind in LEDGES:
    def ledge_extra(xx, zz, L=L):
        if slope_deg(xx, zz, 4) > 12: return 'slope'
        if wash_dist(xx, zz) < L * 0.5: return 'wash'
        if any(math.hypot(xx - o['x'], zz - o['z']) < (L + o['length']) * 0.5 + 10 for o in ledges): return 'ledge'
    at = settle(name, x, z, 'ledge', L * 0.5, TRACK_LINES, ledge_extra, rmax=36)
    if not at: continue
    x, z = at
    ledges.append(dict(name=name, x=round(x, 2), z=round(z, 2), length=L, width=W, h=h, yaw=yaw, tilt=tilt, kind=kind,
                       seed=int(RNG.integers(1 << 30)), outline=outline(x, z, L, W, yaw, kind)))
    # fallen blocks: one or two pieces broken off the long ledges, lying a few metres out
    if kind in ('ledge', 'slab') and L >= 12:
        for b in range(int(RNG.integers(1, 3))):
            a = math.radians(yaw) + RNG.choice([0, math.pi]) + RNG.normal(0, 0.5)
            dist = L * 0.5 + RNG.uniform(2.5, 5.0)
            bx, bz = x + dist * math.cos(a), z + dist * math.sin(a)
            bl, bw, bh = RNG.uniform(2.6, 4.5), RNG.uniform(1.8, 3.0), RNG.uniform(0.8, min(1.6, h * 0.7))
            ok, why = check(bx, bz, 'ledge', bl * 0.5, TRACK_LINES)
            if not ok or slope_deg(bx, bz, 2) > 14 or any(math.hypot(bx - o['x'], bz - o['z']) < (bl + o['length']) * 0.45 for o in ledges if o['name'] != name):
                REPORT['rejected'].append(dict(what=name + ' fallen block', at=[round(bx, 1), round(bz, 1)], because=why or 'overlap/slope')); continue
            byaw = float(RNG.uniform(0, 180))
            ledges.append(dict(name=f'{name} block {b + 1}', x=round(bx, 2), z=round(bz, 2), length=round(bl, 2), width=round(bw, 2), h=round(bh, 2),
                               yaw=round(byaw, 1), tilt=round(float(RNG.uniform(6, 18)), 1), kind='block', seed=int(RNG.integers(1 << 30)),
                               outline=outline(bx, bz, bl, bw, byaw, 'block')))

# ----------------------------------------------------------------------------------------------- dunes
DUNES = [('Dune field NW 1', -492, 162, 34, 13, 2.0), ('Dune field NW 2', -527, 112, 28, 12, 1.6),
         ('Dune field N', -455, 176, 28, 11, 1.7), ('Mesa lee dune', -338, 132, 26, 12, 1.5),
         ('Butte lee dune', -200, -4, 24, 11, 1.3), ('West edge dune', -548, 10, 24, 10, 1.5),
         ('Knoll lee dune', -292, 24, 20, 10, 1.1), ('Ridge lee dune', -318, -190, 26, 10, 1.4)]
dunes = []
crest = np.array([-WIND[1], WIND[0]])
for name, x, z, L, W, h in DUNES:
    def dune_extra(xx, zz, L=L):
        # the whole crest must clear routes and sites, not just the centre
        for t in (-0.5, 0.5):
            p = np.array([xx, zz]) + crest * t * L
            ok, why = check(p[0], p[1], 'dune', W * 0.4, TRACK_LINES)
            if not ok: return 'crest ' + why
        if any(math.hypot(xx - l['x'], zz - l['z']) < l['length'] * 0.5 + L * 0.5 + 4 for l in ledges): return 'ledge'
    at = settle(name, x, z, 'dune', W * 0.5, TRACK_LINES, dune_extra, rmax=36)
    if not at: continue
    x, z = at
    # crest polyline across the wind with a gentle barchan bow (horns downwind)
    pts = []
    for t in np.linspace(-0.5, 0.5, 9):
        p = np.array([x, z]) + crest * t * L + WIND * (t * t * 4.0) * (L * 0.18)
        pts.append([round(float(p[0]), 2), round(float(p[1]), 2)])
    dunes.append(dict(name=name, h=h, w=W, pts=pts, seed=int(RNG.integers(1 << 30))))

# ----------------------------------------------------------------------------------------------- craters
craters = []
ZONES = [  # (x0, x1, z0, z1, count) fields in front (west) of the lines and round the redoubts
    (-245, -186, -110, 130, 16), (-470, -408, -150, 80, 14), (-330, -270, 150, 195, 5), (-240, -195, -150, -120, 4),
    (-300, -240, -70, -30, 5), (-560, -520, 10, 70, 4)]
for x0, x1, z0, z1, n in ZONES:
    tries = 0; k = 0
    while k < n and tries < n * 80:
        tries += 1
        x, z = RNG.uniform(x0, x1), RNG.uniform(z0, z1)
        r = float(np.clip(1.4 + RNG.pareto(2.2) * 2.0, 1.4, 6.5))
        good, why = check(x, z, 'rim', r * 1.5, tracks=TRACK_LINES)
        if not good or slope_deg(x, z, r) > 8 or wash_dist(x, z) < r: continue
        if any(math.hypot(x - c['x'], z - c['z']) < (r + c['r']) * 1.6 for c in craters): continue
        if any(math.hypot(x - l['x'], z - l['z']) < l['length'] * 0.6 + r * 2 for l in ledges): continue
        craters.append(dict(x=round(x, 2), z=round(z, 2), r=round(r, 2), glass=bool(RNG.random() < 0.3),
                            rim=r >= 2.4, seed=int(RNG.integers(1 << 30))))
        k += 1

# ----------------------------------------------------------------------------------------------- prefab placements
P = []
FOOT = []          # (x, z, r) footprints of relief objects so prefabs avoid them
for l in ledges: FOOT.append((l['x'], l['z'], l['length'] * 0.55))
for d in dunes:
    for p in d['pts']: FOOT.append((p[0], p[1], d['w'] * 0.45))
for e in earthworks:
    for s in e['segments']:
        for p in s[::3]: FOOT.append((p[0], p[1], e['w'] * 0.5))
for c in craters:
    if c['rim']: FOOT.append((c['x'], c['z'], c['r'] * 1.5))


def on_relief(x, z, pad=0.0):
    return any(math.hypot(x - a, z - b) < r + pad for a, b, r in FOOT)


def add(group, cluster, prefab, x, z, cls, yaw=None, scale=1.0, sink=0.0, pitch=0.0, roll=0.0, shadows=False,
        collider='keep', cull=0.012, radius=0.5, allow_relief=False, tracks=True, own=None):
    good, why = check(x, z, cls, radius, tracks=TRACK_LINES if tracks else ())
    if good and not allow_relief and on_relief(x, z, radius): good, why = False, 'on relief'
    if good and any(math.hypot(x - p['x'], z - p['z']) < radius + p['_r'] for p in P if not (own and p['cluster'] == own)): good, why = False, 'overlap'
    if not good:
        REPORT['rejected'].append(dict(what=f'{group}/{cluster}/{prefab}', at=[round(x, 1), round(z, 1)], because=why)); return False
    P.append(dict(group=group, cluster=cluster, prefab=prefab, x=round(float(x), 2), z=round(float(z), 2),
                  yaw=round(float(RNG.uniform(0, 360) if yaw is None else yaw), 1), pitch=round(float(pitch), 1),
                  roll=round(float(roll), 1), scale=round(float(scale), 2), sink=round(float(sink), 2), shadows=shadows,
                  collider=collider, cull=cull, _r=radius))
    return True


def around(cx, cz, rmin, rmax):
    a = RNG.uniform(0, 2 * math.pi); r = RNG.uniform(rmin, rmax)
    return cx + r * math.cos(a), cz + r * math.sin(a)


BOULDERS = ['WestGate/PH_BoulderA', 'WestGate/PH_BoulderB', 'WestGate/PH_BoulderC', 'OuterBermsDepot/PHD_BoulderD', 'OuterBermsDepot/PHD_BoulderE']
SCRUB = ['WestGate/PH_RooibosA', 'WestGate/PH_RooibosB', 'WestGate/PH_RooibosC', 'WestGate/PH_SearsiaSmall']
DEAD = ['WestGate/PH_DryBranchA', 'WestGate/PH_DryBranchB']

# talus and shade scrub round each ledge: boulders on the downslope/wind side, scrub in the north (shaded) lee
for l in ledges:
    if l['kind'] == 'block': continue
    n = 8 if l['kind'] != 'tor' else 10
    k = 0; tries = 0
    while k < n and tries < 60:
        tries += 1
        x, z = around(l['x'], l['z'], l['length'] * 0.45, l['length'] * 0.5 + 5)
        s = RNG.uniform(0.5, 1.5)
        if add('Clusters', 'Talus · ' + l['name'], BOULDERS[RNG.integers(len(BOULDERS))], x, z, 'boulder', scale=s,
               sink=0.12 * s, shadows=s > 1.1, collider='keep' if s > 1.0 else 'off', radius=1.1 * s, allow_relief=True):
            k += 1
    for _ in range(3):
        x, z = l['x'] + RNG.uniform(-0.4, 0.4) * l['length'], l['z'] + l['width'] * 0.5 + RNG.uniform(1.5, 4.5)
        add('Clusters', 'Shade scrub · ' + l['name'], SCRUB[RNG.integers(len(SCRUB))], x, z, 'small', scale=RNG.uniform(0.8, 1.3), collider='off', radius=0.8)

# wash scrub: clumps on the wash banks every 14-26 m, dead wood caught in the bed
for w in WASHES:
    S = spline(w['pts'], 1.0); s = 0.0; nxt = RNG.uniform(5, 15)
    for i in range(1, len(S)):
        s += float(np.linalg.norm(S[i] - S[i - 1]))
        if s < nxt: continue
        nxt = s + RNG.uniform(14, 26)
        t = S[i] - S[i - 1]; t /= np.linalg.norm(t); nrm = np.array([-t[1], t[0]])
        side = RNG.choice([-1, 1])
        base = S[i] + nrm * side * w['width'] * RNG.uniform(0.45, 0.7)
        for k in range(int(RNG.integers(2, 5))):
            p = base + RNG.normal(0, 1.6, 2)
            add('Clusters', 'Wash scrub · ' + w['name'], SCRUB[RNG.integers(len(SCRUB))], p[0], p[1], 'small', scale=RNG.uniform(0.7, 1.35), collider='off', radius=0.7)
        if RNG.random() < 0.35:
            p = S[i] + nrm * RNG.normal(0, 1.5)
            add('Clusters', 'Wash scrub · ' + w['name'], DEAD[RNG.integers(2)], p[0], p[1], 'small', scale=RNG.uniform(0.9, 1.3), collider='off', radius=0.7)

# boulder fields below the mountain foot (rockfall), each 9-14 boulders falling off with distance
for name, cx, cz in (('Rockfall west', -553, -55), ('Rockfall northwest', -470, 168), ('Rockfall south', -300, -203),
                     ('Rockfall southeast', -128, -100), ('Rockfall south fans', -470, -168)):
    at = settle('rockfall ' + name, cx, cz, 'boulder', 14, TRACK_LINES, lambda xx, zz: 'edge' if d_edge(xx, zz) < 16 else None, rmax=45)
    if not at: continue
    cx, cz = at
    n = int(RNG.integers(9, 15)); k = 0; tries = 0
    while k < n and tries < 150:
        tries += 1
        x, z = around(cx, cz, 0, 22)
        s = RNG.uniform(0.8, 2.2) * (1.15 - math.hypot(x - cx, z - cz) / 40)
        if add('Clusters', name, BOULDERS[RNG.integers(len(BOULDERS))], x, z, 'boulder', scale=s, sink=0.15 * s,
               shadows=s > 1.1, collider='keep' if s > 1.0 else 'off', radius=1.3 * s):
            k += 1

# battle remains along the lines: dead workers and drone wrecks in front (west), spent cells and sandbags behind
DROIDS_DEAD = ['OuterBermsDepot/DP_DeadWorker', 'TrainingRange/TR_WorkerDroidShell', 'OuterBermsDepot/DP_CrashedDrone']
for e in earthworks:
    for seg in e['segments']:
        S = np.array(seg)
        for i in range(0, len(S), 14):
            if i + 1 >= len(S): break
            t = S[min(i + 1, len(S) - 1)] - S[i]; t /= max(np.linalg.norm(t), 1e-6); nrm = np.array([-t[1], t[0]])
            west = nrm if nrm[0] < 0 else -nrm
            r = RNG.random()
            if r < 0.45:
                p = S[i] + west * RNG.uniform(7, 26) + t * RNG.normal(0, 3)
                pf = DROIDS_DEAD[RNG.integers(3)]
                add('Wreckage', 'Battle remains · ' + e['name'], pf, p[0], p[1], 'wreck' if 'Dead' in pf or 'Shell' in pf else 'small',
                    sink=RNG.uniform(0.15, 0.45), pitch=RNG.uniform(-12, 12), roll=RNG.uniform(-25, 25), shadows=True,
                    collider='keep', cull=0.02, radius=1.4)
            if r > 0.55:
                p = S[i] - west * RNG.uniform(4.5, 7) + t * RNG.normal(0, 2)
                add('Wreckage', 'Line remains · ' + e['name'], ['TrainingRange/TR_SpentCells_1', 'TrainingRange/TR_SpentCells_2', 'TrainingRange/TR_SpentCells_3'][RNG.integers(3)],
                    p[0], p[1], 'small', collider='off', radius=1.0, cull=0.03)
            if RNG.random() < 0.3:   # a sandbag remnant slumped on the crest
                add('Wreckage', 'Line remains · ' + e['name'], ['WestGate/WG_SandbagPile', 'WestGate/WG_SandbagWall2mLow'][RNG.integers(2)],
                    S[i][0], S[i][1], 'small', yaw=math.degrees(math.atan2(t[1], -t[0])) if False else None, sink=0.18,
                    pitch=RNG.uniform(-6, 6), roll=RNG.uniform(-8, 8), collider='off', radius=1.0, allow_relief=True, cull=0.02)

# craters: a scorched wreck in a few of the big ones
for c in craters:
    if c['r'] > 3.5 and RNG.random() < 0.4:
        add('Wreckage', 'Crater wrecks', DROIDS_DEAD[RNG.integers(3)], c['x'] + RNG.normal(0, 0.5), c['z'] + RNG.normal(0, 0.5), 'small',
            sink=0.35, pitch=RNG.uniform(-20, 20), roll=RNG.uniform(-30, 30), shadows=True, collider='keep', radius=1.0, allow_relief=True, cull=0.02)

# wreck fields from the industrial complex's outer reach
def field(name, cx, cz, items, radius=12):
    def fext(xx, zz):
        if on_relief(xx, zz, radius * 0.6): return 'on relief'
        if any(math.hypot(xx - p['x'], zz - p['z']) < radius * 0.6 + p['_r'] for p in P): return 'overlap'
    at = settle('field ' + name, cx, cz, 'wreck', radius, TRACK_LINES, fext, rmax=40)
    if not at: return
    cx, cz = at
    n0 = len(P)
    for pf, dx, dz, yaw, sink, pitch, roll, scale, cls in items:
        add('Wreckage', name, pf, cx + dx, cz + dz, cls, yaw=yaw, scale=scale, sink=sink, pitch=pitch, roll=roll,
            shadows=True, collider='box' if cls == 'wreck' else 'keep', cull=0.012, radius=1.4 if cls == 'wreck' else 0.6,
            own=name)


field('Drone bay wreck', -345, 152, [
    ('OuterBermsDepot/DP_DroneRack', 0, 0, 25, 0.7, 4, -7, 1.0, 'wreck'),
    ('OuterBermsDepot/DP_CradleBroken', 7, 5, 70, 0.5, 12, 18, 1.0, 'wreck'),
    ('OuterBermsDepot/DP_CradleBroken', -8, -4, 200, 0.9, -15, 30, 1.0, 'wreck'),
    ('OuterBermsDepot/DP_CrashedDrone', 4, -7, 110, 0.15, 6, 12, 1.0, 'small'),
    ('OuterBermsDepot/DP_CrashedDrone', -3, 8, 300, 0.2, -10, -20, 1.0, 'small'),
    ('OuterBermsDepot/DP_CrashedDrone', 11, -2, 40, 0.25, 0, 35, 1.0, 'small'),
    ('OuterBermsDepot/MX_ScrapHeapB', -10, 6, 150, 0.35, 0, 0, 1.0, 'wreck'),
])
field('Processing hall ruin', -432, -148, [
    ('OuterBermsDepot/DP_WallA', 0, 0, 10, 0.4, 0, 4, 1.0, 'wreck'),
    ('OuterBermsDepot/DP_WallC', 3.6, 0.6, 10, 0.8, 0, -6, 1.0, 'wreck'),
    ('OuterBermsDepot/DP_WallB', 8.5, 1.2, 12, 0.3, 0, 18, 1.0, 'wreck'),
    ('OuterBermsDepot/DP_WallD', -1.5, 11.5, 100, 0.5, 0, -10, 1.0, 'wreck'),
    ('OuterBermsDepot/DP_WallA', 2.0, 13.5, 190, 0.9, 0, 25, 1.0, 'wreck'),
    ('OuterBermsDepot/DP_WallB', 12, 9, 280, 0.6, 0, 70, 1.0, 'wreck'),
    ('OuterBermsDepot/DP_Plinth', 5, 6, 10, 0.55, 0, 0, 1.0, 'wreck'),
])
field('Conveyor spine', -535, -12, [
    ('OuterBermsDepot/DP_Conveyor', 0, 0, 82, 3.2, 3, -6, 1.0, 'wreck'),
    ('OuterBermsDepot/DP_Conveyor', 2, -17, 76, 4.2, -5, 9, 1.0, 'wreck'),
])
field('Yard fence line', -225, 112, [
    ('OuterBermsDepot/PHD_FencePost', 0, 0, 0, 0.6, 8, 4, 1.0, 'small'),
    ('OuterBermsDepot/PHD_FencePanel', 0.6, 1.2, 80, 0.7, 4, 22, 1.0, 'small'),
    ('OuterBermsDepot/PHD_FencePost', 1.2, 2.4, 0, 0.9, -12, 10, 1.0, 'small'),
    ('OuterBermsDepot/PHD_FencePost', 2.4, 4.8, 0, 1.0, 20, -6, 1.0, 'small'),
    ('OuterBermsDepot/PHD_FencePanel', 3.0, 6.0, 80, 1.1, -30, 60, 1.0, 'small'),
    ('OuterBermsDepot/PHD_FencePost', 3.6, 7.2, 0, 0.7, 4, 14, 1.0, 'small'),
])
field('Toppled crane', -385, 168, [('OuterBermsDepot/PHD_Crane', 0, 0, 160, 0.8, 0, 84, 1.0, 'wreck')])

# Karaveen litter along the trail: lost tyres, rims, sacks and broken crates, thicker where the trail climbs
LITTER = ['WestGate/PH_OldTyre', 'StreetDressing/SD_tyre', 'StreetDressing/SD_rim_a', 'OuterBermsDepot/PHD_WheelRimA',
          'StreetDressing/SD_sack_tied_a', 'StreetDressing/SD_sack_tied_b', 'StreetDressing/SD_crate_wood',
          'WestGate/PH_Jerrycan', 'StreetDressing/SD_jerrycan_red', 'WestGate/PH_WoodenMilitaryCrate']
car = [t for t in TRACKS if t['kind'] == 'caravan'][0]
S = spline(car['pts'], 1.0); s = 0.0; nxt = 12
for i in range(1, len(S)):
    s += float(np.linalg.norm(S[i] - S[i - 1]))
    if s < nxt: continue
    nxt = s + RNG.uniform(16, 34)
    t = S[i] - S[i - 1]; t /= np.linalg.norm(t); nrm = np.array([-t[1], t[0]])
    for k in range(int(RNG.integers(1, 4))):
        p = S[i] + nrm * RNG.choice([-1, 1]) * RNG.uniform(4.2, 8) + t * RNG.normal(0, 2)
        pf = LITTER[RNG.integers(len(LITTER))]
        flat = 'tyre' in pf.lower() or 'rim' in pf.lower()
        add('Clusters', 'Karaveen trail litter', pf, p[0], p[1], 'small', sink=0.06 if not flat else 0.02,
            pitch=RNG.uniform(70, 90) if flat else RNG.uniform(-8, 8), roll=RNG.uniform(-10, 10), collider='off', radius=0.6, tracks=False, cull=0.03)

# lone dead shrubs and stones in the hardpan and pan margins (sparse, purposeful: they mark the dry ground)
for name, cx, cz in (('Pan margin scrub', -300, -20), ('Pan margin scrub', -250, 30), ('Pan margin scrub', -430, -40), ('Pan margin scrub', -520, -120)):
    for _ in range(4):
        x, z = around(cx, cz, 4, 22)
        add('Clusters', name, DEAD[RNG.integers(2)] if RNG.random() < 0.5 else SCRUB[RNG.integers(len(SCRUB))], x, z, 'small', scale=RNG.uniform(0.7, 1.2), collider='off', radius=0.7)

# keep the review cameras' lens and first 10 m of view clear of kit pieces (fix round 2: scrub sat on cam_bv_bx_scrapyard)
_cams = json.loads((HERE / 'review_cameras.json').read_text())['cameras'] if (HERE / 'review_cameras.json').exists() else []
def _blocks_cam(p):
    for c in _cams:
        P0 = np.array([c['pos'][0], c['pos'][2]], float); D = np.array([c['target'][0], c['target'][2]], float) - P0; D /= np.linalg.norm(D)
        if math.hypot(p['x'] - P0[0], p['z'] - P0[1]) < 3.5: return c['name']
        for s_ in np.arange(1, 11, 1.0):
            q = P0 + D * s_
            if math.hypot(p['x'] - q[0], p['z'] - q[1]) < 1.0 + 1.3 * p['scale']: return c['name']
    return None
_kept = []
for p in P:
    cn = _blocks_cam(p)
    if cn: REPORT['rejected'].append(dict(what=f"{p['group']}/{p['cluster']}/{p['prefab']}", at=[p['x'], p['z']], because='camera ' + cn))
    else: _kept.append(p)
P = _kept
for p in P: p.pop('_r')

# ----------------------------------------------------------------------------------------------- write
feat = dict(version=1, wind=WIND.round(3).tolist(), note='Unity world metres. Generated by layout.py; see README.md.',
            earthworks=earthworks, ledges=ledges, dunes=dunes, craters=craters, tracks=TRACKS, washes=WASHES)
# keep the outline key name used by plot_plan.py
feat['outcrops'] = [dict(name=l['name'], outline=l['outline']) for l in ledges]
(HERE / 'features.json').write_text(json.dumps(feat, indent=0) + '\n')
pl_path = HERE / 'placements.json'
old = json.loads(pl_path.read_text()) if pl_path.exists() else {}
(pl_path).write_text(json.dumps(dict(version=1, chunks=old.get('chunks', []), prefabs=P), indent=0) + '\n')

# final clearances of everything kept
def summary(items, cls):
    out = []
    for name, x, z, rad in items:
        out.append(dict(what=name, spawn=round(d_pts(x, z, SPAWNS) - rad, 1), node=round(d_pts(x, z, NODES) - rad, 1),
                        site=round(d_sites(x, z) - rad, 1), route=round(d_routes(x, z) - rad, 1), col=round(d_rect(x, z) - rad, 1),
                        edge=round(d_edge(x, z) - rad, 1)))
    return out


REPORT['kept'] = dict(
    earthwork_segments=sum(len(e['segments']) for e in earthworks), earthwork_metres=sum(len(s) for e in earthworks for s in e['segments']),
    ledges=len(ledges), dunes=len(dunes), craters=len(craters), crater_rims=sum(c['rim'] for c in craters),
    tracks=len(TRACKS), prefabs=len(P), prefab_groups={g: sum(1 for p in P if p['group'] == g) for g in ('Wreckage', 'Clusters')})
REPORT['clearance'] = dict(classes=CLEAR,
                           ledges=summary([(l['name'], l['x'], l['z'], l['length'] * 0.5) for l in ledges], 'ledge'),
                           wrecks=summary([(p['cluster'] + '/' + p['prefab'], p['x'], p['z'], 0) for p in P if p['group'] == 'Wreckage'], 'wreck'))
REPORT['problems'] = []   # anything kept that breaks its class (none by construction; re-checked here)
for l in ledges:
    ok, why = check(l['x'], l['z'], 'ledge', l['length'] * 0.5)
    if not ok: REPORT['problems'].append(dict(what=l['name'], why=why))
(HERE / 'layout-check.json').write_text(json.dumps(REPORT, indent=1) + '\n')
print(json.dumps(REPORT['kept'], indent=1))
print('rejected', len(REPORT['rejected']), 'problems', len(REPORT['problems']))
from collections import Counter
print(Counter(r['because'].split(' ')[0] for r in REPORT['rejected']))
for r in REPORT['rejected']:
    if not r['what'].startswith(('Clusters', 'Wreckage/Battle', 'Wreckage/Line', 'Wreckage/Crater')): print(r)
for t in REPORT['trimmed']: print(t)
