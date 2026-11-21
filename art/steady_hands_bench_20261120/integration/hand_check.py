#!/usr/bin/env python3
"""Steady Hands bench, integration, Part 2: the numbers check before the rebuilt pistol goes into the hand.

pistol_hand.glb (model-pistol) against ScrapPistol.glb (the fused Meshy pistol in the hand today), both in ScrapPistol's
own glTF units with identity nodes, so the game puts both under the same instance (scale 0.136736). Measured at the
game's scale, in the pistol metric frame P of FACTS.md / grip/INTERFACE.md (mm; x along the barrel, muzzle -x; y the
player's right; z up). Tolerance: 1 mm (the orchestrator's limit for Part 2).

  muzzle   the bore mouth (centre of the muzzle ring, circle fit, and the mouth's x) and the stock `Muzzle` point the
           flash leaves from today (front of the lower dust cover, 29 mm under the bore)
  grip     the grip frame: section centres along the raked grip axis (rays from the axis to the surface front, back,
           left, right), the fitted axis line and its rake; the two hand anchor points of the first-person view model
  rail     the dust-cover rail the cell mods clamp to: both side faces on a grid (rays from outside)
  mods     the five other mods of PistolMods.glb: every vertex of a mod lying on the Meshy pistol's surface (within
           0.5 mm) is a mount point; its distance to the rebuilt pistol is the error there. Also how deep any of the
           mod's vertices go into the rebuilt pistol (as model-pistol's outline check counts it)

Bare pistol = all five nodes of pistol_hand.glb (the grip mods other than Stabilised are fitted over the stock grip).
Informational, not part of the pass: the real grip (grip.core, its screws and seams; materials plates and bent strap at
the core's seat marks; servo case screws at theirs) in place of ScrapPistol_grip_stock, at the hand points.

numpy only; no Unity, no Blender.  Usage: hand_check.py [--hand GLB] [--json OUT] [--tol MM]
"""
import json, math, os, struct, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
A = os.path.join(ROOT, 'unity/AthenHill/Assets/AthenHill/Art')
OLD = os.path.join(A, 'OuterBerms/ScrapPistol.glb')
HAND = os.path.join(A, 'Bench/Pistol/pistol_hand.glb')
MODS = os.path.join(A, 'Weapons/PistolMods/PistolMods.glb')
GRIP = os.path.join(A, 'Bench/Grip/grip.glb')
MATS = os.path.join(A, 'Bench/Materials/materials.glb')
SERVO = os.path.join(A, 'Bench/Servo/servo.glb')
OUT = os.path.join(ROOT, 'unity/evidence/steady_hands/20261120/integration/hand_numbers.json')
S = 0.136736            # the ScrapPistol instance's scale in the scene (FACTS.md); glTF unit -> metres
HOLDER_T = np.array([0.00067, 0.00012, 0.08376])   # ScrapPistol's local position in its holder (pistol_frame.json)

args = sys.argv[1:]
def opt(name, default):
    return args[args.index(name) + 1] if name in args else default
HAND = opt('--hand', HAND); OUT = opt('--json', OUT); TOL = float(opt('--tol', '1.0'))

from glbgeom import read_glb, accessor, trs, Model, Surface, closest_on_tris

def to_mm(p_gltf):
    """ScrapPistol glTF units (muzzle -X, up +Y, right -Z) -> P frame mm (muzzle -x, right +y, up +z)."""
    p = np.asarray(p_gltf, float)
    return np.stack([p[..., 0], -p[..., 2], p[..., 1]], -1) * S * 1000

def metres_to_hand_units(t):
    """A family GLB in P metres (glTF axes) -> ScrapPistol glTF units: divide by the scale."""
    return t / S

def circle_fit(pts):
    """Least-squares circle through 2-D points (Kasa): centre, radius, rms."""
    x, y = pts[:, 0], pts[:, 1]
    M = np.stack([x, y, np.ones_like(x)], 1); r = x * x + y * y
    sol, *_ = np.linalg.lstsq(M, r, rcond=None); cx, cy = sol[0] / 2, sol[1] / 2; rad = math.sqrt(sol[2] + cx * cx + cy * cy)
    rms = float(np.sqrt(np.mean((np.hypot(x - cx, y - cy) - rad) ** 2)))
    return np.array([cx, cy]), rad, rms

def r2(x, n=2):
    if isinstance(x, (list, tuple, np.ndarray)): return [r2(v, n) for v in x]
    return None if x is None else round(float(x), n)

# ------------------------------------------------------------------ load
t0 = time.time()
old = Model(OLD); hand = Model(HAND); mods = Model(MODS)
old_tris = to_mm(np.concatenate([old.tris(n) for n in old.mesh_nodes()]))
hand_nodes = hand.mesh_nodes()
hand_tris = to_mm(np.concatenate([hand.tris(n) for n in hand_nodes]))
OLD_S = Surface(old_tris); NEW_S = Surface(hand_tris)
report = {'generated': time.strftime('%Y-%m-%d %H:%M'), 'tool': 'art/steady_hands_bench_20261120/integration/hand_check.py',
          'old': os.path.relpath(OLD, ROOT), 'new': os.path.relpath(HAND, ROOT), 'mods': os.path.relpath(MODS, ROOT),
          'newSize': os.path.getsize(HAND), 'newMtime': time.strftime('%Y-%m-%d %H:%M', time.localtime(os.path.getmtime(HAND))),
          'scale': S, 'toleranceMm': TOL, 'frame': 'P, mm: x along the barrel (muzzle -x), y the player\'s right, z up; origin = ScrapPistol.glb origin',
          'triangles': {'old': len(old_tris), 'new': len(hand_tris), 'newNodes': {n: len(hand.local_tris(n)) for n in hand_nodes}}}
fails = []

# ------------------------------------------------------------------ muzzle
def mouth(tris):
    v = tris.reshape(-1, 3); axis_guess = np.array([0.75, 58.85])   # FACTS bore axis (y, z) in P mm
    near = v[np.hypot(v[:, 1] - axis_guess[0], v[:, 2] - axis_guess[1]) < 16]
    x0 = near[:, 0].min(); front = near[near[:, 0] < x0 + 0.6]
    rr = np.hypot(front[:, 1] - axis_guess[0], front[:, 2] - axis_guess[1])
    ring = front[rr > rr.max() - 2.5]        # the outer edge of the muzzle ring's front face
    c, rad, rms = circle_fit(ring[:, 1:3])
    return {'mouthX': x0, 'axisY': c[0], 'axisZ': c[1], 'ringRadius': rad, 'fitRms': rms, 'points': len(ring)}
mo, mn = mouth(old_tris), mouth(hand_tris)
facts = {'mouthX': -0.95143 * S * 1000, 'axisY': 0.00548 * S * 1000, 'axisZ': 0.43038 * S * 1000}
d_axis = math.hypot(mn['axisY'] - mo['axisY'], mn['axisZ'] - mo['axisZ']); d_x = mn['mouthX'] - mo['mouthX']
# the stock Muzzle transform (glTF units, PistolModsInstall / art README): where the flash leaves today
stock = to_mm(np.array([-0.95166, 0.21771, -0.00088]))
so, sn = OLD_S.closest(stock), NEW_S.closest(stock)
def front_x(surf, y, z):
    t = surf.ray(np.array([-400.0, y, z]), np.array([1.0, 0, 0])); return None if t is None else -400 + t
fx_o, fx_n = front_x(OLD_S, stock[1], stock[2]), front_x(NEW_S, stock[1], stock[2])
report['muzzle'] = {
    'boreMouth': {'old': {k: r2(v, 3) for k, v in mo.items()}, 'new': {k: r2(v, 3) for k, v in mn.items()}, 'facts': {k: r2(v, 3) for k, v in facts.items()},
                  'axisErrorMm': r2(d_axis, 3), 'mouthXErrorMm': r2(d_x, 3), 'newVsFactsAxisMm': r2(math.hypot(mn['axisY'] - facts['axisY'], mn['axisZ'] - facts['axisZ']), 3),
                  'newVsFactsMouthXMm': r2(mn['mouthX'] - facts['mouthX'], 3)},
    'stockMuzzlePoint': {'pointMm': r2(stock, 2), 'toOldSurfaceMm': r2(so[0], 2), 'toNewSurfaceMm': r2(sn[0], 2),
                         'frontFaceXAtThatHeight': {'old': r2(fx_o, 2), 'new': r2(fx_n, 2), 'errorMm': r2(None if fx_o is None or fx_n is None else fx_n - fx_o, 2)},
                         'note': 'unsigned distance to the closest surface point'},
}
# the stock Muzzle transform floats ahead of the lower dust cover in both models (not on a surface), so only the bore is judged
report['muzzle']['stockMuzzlePoint']['judged'] = False
report['muzzle']['judgedOn'] = 'the bore mouth: axis (circle fit on the muzzle ring) and the mouth x. The stock Muzzle transform is a scene object that stays where it is; it is not on either surface, so the front face behind it is reported, not judged'
muzzle_ok = d_axis <= TOL and abs(d_x) <= TOL
report['muzzle']['pass'] = muzzle_ok
if not muzzle_ok: fails.append(f"muzzle: bore axis {d_axis:.2f} mm, mouth x {d_x:+.2f} mm")

# ------------------------------------------------------------------ grip frame
C0 = np.array([80.0, 0.0, -30.0]); AX = np.array([-0.4633, 0.0, 1.0]); AX /= np.linalg.norm(AX)   # mods_grip.py GRIP_C0 / GRIP_AX (metric)
FRONT = np.array([-AX[2], 0.0, AX[0]]); FRONT = FRONT if FRONT[0] < 0 else -FRONT                  # toward the muzzle side (front strap)
LEFT = np.array([0.0, -1.0, 0.0])
def section(tris, s, reach=40.0):
    """Where the plane across the grip axis at s cuts the surface: extents along FRONT and y of the cut within `reach`
    of the axis (so the trigger guard and the frame above stay out). The section's box centre is the grip's centre."""
    o = C0 + AX * s; d = (tris - o) @ AX                       # (n, 3) signed distances of the corners to the plane
    pts = []
    for i, j in ((0, 1), (1, 2), (2, 0)):
        m = (d[:, i] * d[:, j]) < 0; t = d[m, i] / (d[m, i] - d[m, j])
        pts.append(tris[m, i] + (tris[m, j] - tris[m, i]) * t[:, None])
    p = np.concatenate(pts) - o; u = p @ FRONT; y = p[:, 1]
    k = (np.abs(u) < reach) & (np.abs(y) < reach)
    if k.sum() < 8: return None
    return {'front': float(u[k].max()), 'back': float(-u[k].min()), 'left': float(-y[k].min()), 'right': float(y[k].max()),
            'centre': [float((u[k].max() + u[k].min()) / 2), float((y[k].max() + y[k].min()) / 2)]}
rows = []; cen_o = []; cen_n = []
for s in np.arange(-45, 2.5, 2.5):
    row = {'sMm': float(s)}
    for tris, key, acc in ((old_tris, 'old', cen_o), (hand_tris, 'new', cen_n)):
        sec = section(tris, s)
        if sec: acc.append((s, sec['centre'][0], sec['centre'][1])); row[key] = {k: r2(v, 2) for k, v in sec.items()}
    if 'old' in row and 'new' in row:
        row['centreErrorMm'] = r2(math.hypot(row['new']['centre'][0] - row['old']['centre'][0], row['new']['centre'][1] - row['old']['centre'][1]), 2)
    rows.append(row)
def axis_fit(c):
    c = np.array(c); A_ = np.stack([c[:, 0], np.ones(len(c))], 1)
    ku, bu = np.linalg.lstsq(A_, c[:, 1], rcond=None)[0]; ky, by = np.linalg.lstsq(A_, c[:, 2], rcond=None)[0]
    return ku, bu, ky, by
fo, fn = axis_fit(cen_o), axis_fit(cen_n)
common = [r['sMm'] for r in rows if 'centreErrorMm' in r]
grip_err = max(r['centreErrorMm'] for r in rows if 'centreErrorMm' in r)
line_err = max(math.hypot((fn[0] - fo[0]) * s + fn[1] - fo[1], (fn[2] - fo[2]) * s + fn[3] - fo[3]) for s in common)
report['grip'] = {
    'axis': {'c0Mm': C0.tolist(), 'direction': r2(AX, 4), 'source': 'art/pistol_mods_20260930/src/mods_grip.py GRIP_C0, GRIP_AX; s is along it (mm), the hand holds about s -45 .. 0'},
    'sections': rows,
    'fittedAxis': {'old': {'uAt0': r2(fo[1], 2), 'yAt0': r2(fo[3], 2), 'uPerMm': r2(fo[0], 4), 'yPerMm': r2(fo[2], 4)},
                   'new': {'uAt0': r2(fn[1], 2), 'yAt0': r2(fn[3], 2), 'uPerMm': r2(fn[0], 4), 'yPerMm': r2(fn[2], 4)},
                   'tiltBetweenDeg': r2(math.degrees(math.atan(math.hypot(fn[0] - fo[0], fn[2] - fo[2]))), 3),
                   'largestLineOffsetMm': r2(line_err, 2)},
    'largestSectionCentreErrorMm': grip_err,
}
# the hand anchors of the first-person view model (holder frame, metres) -> P mm
def holder_to_mm(h):
    h = np.array(h); return np.array([-(h[2] - HOLDER_T[2]), h[0] - HOLDER_T[0], h[1] - HOLDER_T[1]]) * 1000
hands = {'Shooting grip': [0.0448, -0.0828, -0.0295], 'Support grip': [-0.0139, -0.1009, -0.0181]}
hp = {}
for name, h in hands.items():
    p = holder_to_mm(h); a, b = OLD_S.closest(p), NEW_S.closest(p)
    hp[name] = {'pointMm': r2(p, 2), 'toOldSurfaceMm': r2(a[0], 2), 'toNewSurfaceMm': r2(b[0], 2), 'errorMm': r2(b[0] - a[0], 2)}
report['grip']['handAnchors'] = hp
hand_err = max(abs(v['errorMm']) for v in hp.values())
grip_ok = line_err <= TOL and hand_err <= TOL
report['grip']['pass'] = grip_ok
report['grip']['judgedOn'] = 'the grip frame = the line fitted through the section centres over s -45 .. 0 (where the hand holds): its offset from the old line anywhere on that length, and the two hand anchors\' distance to the surface; single sections are listed (a wrap of tape moves one side, not the frame)'
if not grip_ok: fails.append(f"grip frame: fitted axis off by up to {line_err:.2f} mm, hand anchors {hand_err:.2f} mm")

# ------------------------------------------------------------------ rail
rail = []
for x in range(-95, -25, 5):
    for z in (21, 25, 30, 34, 38, 42):
        row = {'xMm': x, 'zMm': z}
        for side, sgn in (('left', -1), ('right', 1)):
            o = np.array([x, sgn * 80.0, z]); d = np.array([0, -sgn, 0.0])
            to, tn = OLD_S.ray(o, d), NEW_S.ray(o, d)
            fo_, fn_ = (None if to is None else sgn * (80 - to)), (None if tn is None else sgn * (80 - tn))
            row[side] = {'old': r2(fo_, 2), 'new': r2(fn_, 2), 'errorMm': r2(None if fo_ is None or fn_ is None else fn_ - fo_, 2)}
        rail.append(row)
face = lambda r: 28 <= r['zMm'] <= 40 and -90 <= r['xMm'] <= -35
left_err = [abs(r['left']['errorMm']) for r in rail if r['left']['errorMm'] is not None and face(r)]
right_err = [abs(r['right']['errorMm']) for r in rail if r['right']['errorMm'] is not None and face(r)]
edge_err = [abs(r['left']['errorMm']) for r in rail if r['left']['errorMm'] is not None and not face(r)]
rail_ok = bool(left_err) and max(left_err) <= TOL
summ = lambda e: {'n': len(e), 'maxErrorMm': r2(max(e) if e else None, 2), 'meanErrorMm': r2(float(np.mean(e)) if e else None, 2), 'over': sum(x > TOL for x in e)}
report['rail'] = {'region': 'FACTS.md: dust-cover rail, x -95..-30 mm, z 21..42 mm, sampled every 5 mm in x; face y from rays at each (x, z)', 'samples': rail,
                  'leftFace': summ(left_err), 'rightFace': summ(right_err), 'leftEdgesAndEnds': summ(edge_err),
                  'judgedOn': 'the left face proper (z 28..40, x -90..-35: the cell mods clamp on the left of the rail); its edges and ends (chamfers, a notch in the Meshy skin) and the right face are listed. Where the clamps actually bear is judged again under mods', 'pass': rail_ok}
if not rail_ok: fails.append(f"rail: left face off by up to {max(left_err) if left_err else 'n/a'} mm")

# ------------------------------------------------------------------ the five other mods
mod_rows = {}; mods_ok = True; node_of = []
for n in hand_nodes: node_of += [n] * len(hand.local_tris(n))
for name in ['barrel_bored_alloy', 'barrel_lattice_focused', 'cell_salvaged_capacitor', 'cell_overclocked', 'grip_gyro_braced']:
    v = np.unique(np.round(to_mm(mods.verts(name)), 4), axis=0)
    co = [OLD_S.closest(p) for p in v]; cn = [NEW_S.closest(p) for p in v]
    ao = np.array([c[0] for c in co]); an = np.array([c[0] for c in cn])
    mount = np.where(ao <= 0.5)[0]
    # signs by ray parity where it matters: the mount points, and anything the face normal calls in the metal
    so_ = {i: (-ao[i] if OLD_S.inside(v[i]) else ao[i]) for i in mount}
    sn_ = {i: (-an[i] if NEW_S.inside(v[i]) else an[i]) for i in mount}
    disp = np.array([sn_[i] - so_[i] for i in mount]); lower = np.array([abs(an[i] - ao[i]) for i in mount])
    slide = np.array([np.linalg.norm(cn[i][1] - co[i][1]) for i in mount])
    over = np.abs(disp) > TOL; certain = lower > TOL
    deep_new = [i for i in range(len(v)) if cn[i][2] < -0.3 and NEW_S.inside(v[i])]
    deep_old = [i for i in range(len(v)) if co[i][2] < -0.3 and OLD_S.inside(v[i])]
    order = np.argsort(-np.abs(disp))[:6]
    row = {'vertices': int(len(v)), 'mountPoints': int(len(mount)),
           'surfaceMovedAtMountMm': {'max': r2(np.abs(disp).max() if len(disp) else None, 2), 'p95': r2(np.percentile(np.abs(disp), 95) if len(disp) else None, 2),
                                     'mean': r2(np.abs(disp).mean() if len(disp) else None, 2), 'overTolerance': int(over.sum()),
                                     'overToleranceWhateverTheSign': int(certain.sum()), 'nowAGapOver': int((disp > TOL).sum()), 'nowInTheMetalOver': int((disp < -TOL).sum())},
           'gapOrDepthOnTheNewPistolMm': {'max': r2(max(abs(sn_[i]) for i in mount) if len(mount) else None, 2)},
           'mountPointSlideMm': {'max': r2(slide.max() if len(slide) else None, 2), 'p95': r2(np.percentile(slide, 95) if len(slide) else None, 2)},
           'worstMountPoints': [{'pointMm': r2(v[mount[k]], 1), 'oldMm': r2(so_[mount[k]], 2), 'newMm': r2(sn_[mount[k]], 2), 'movedMm': r2(disp[k], 2), 'newNode': node_of[cn[mount[k]][3]]} for k in order],
           'intoNewPistol': {'deeperThan0.3mm': len(deep_new), 'deepestMm': r2(max([an[i] for i in deep_new], default=0), 2)},
           'intoOldPistol': {'deeperThan0.3mm': len(deep_old), 'deepestMm': r2(max([ao[i] for i in deep_old], default=0), 2)}}
    if over.any():
        bad = v[mount[over]]; row['overToleranceBoxMm'] = {'min': r2(bad.min(0), 1), 'max': r2(bad.max(0), 1)}
        nodes_at = {}
        for k in np.where(over)[0]: n = node_of[cn[mount[k]][3]]; nodes_at[n] = nodes_at.get(n, 0) + 1
        row['overToleranceOnNode'] = nodes_at
    row['pass'] = bool(not over.any())
    mods_ok &= row['pass']; mod_rows[name] = row
    if not row['pass']: fails.append(f"{name}: at {int(over.sum())} of {len(mount)} mount points the pistol's surface moved more than {TOL} mm (worst {np.abs(disp).max():.2f} mm; {int(certain.sum())} of them over {TOL} mm whatever the sign)")
report['mods'] = {'mountPointRule': 'a mod vertex within 0.5 mm of the Meshy pistol\'s surface is a mount point. Judged: how far the pistol\'s surface moved there, new signed distance minus old (+ the mod now stands off, - it now sits in the metal), signs by ray parity; the sign-free lower bound |new| - |old| is counted too. Also listed: how far the closest surface point slid, and how deep any vertex of the mod goes into either pistol',
                  'perMod': mod_rows, 'pass': mods_ok}

# ------------------------------------------------------------------ informational: the real grip in place of the stock grip
try:
    g = Model(GRIP); mt = Model(MATS); sv = Model(SERVO)
    parts = []
    for n in ['grip_core', 'grip_screw_a', 'grip_screw_b', 'grip_seam_l', 'grip_seam_r']: parts.append(g.tris(n))
    seat = lambda mark: g.world[g.byname[mark]]
    parts.append(mt.tris('materials_sheet_a_plate', seat('grip_core__mark_seat_plate_l')))
    parts.append(mt.tris('materials_sheet_b_plate', seat('grip_core__mark_seat_plate_r')))
    parts.append(mt.tris('materials_strap_bent', seat('grip_core__mark_seat_strap')))
    for scr, mark in (('a', 'lc'), ('b', 'ld'), ('c', 'rc'), ('d', 'rd')):
        mk = 'grip_core__mark_seat_plate_screw_' + mark
        if mk in g.byname: parts.append(sv.tris('servo_screw_case_' + scr, seat(mk)))
    real = to_mm(metres_to_hand_units(np.concatenate(parts)))
    bare = to_mm(np.concatenate([hand.tris(n) for n in hand_nodes if n != 'ScrapPistol_grip_stock']))
    RG = Surface(np.concatenate([bare, real]))
    stab = to_mm(mods.tris('grip_stabilised_pistol')); OS = Surface(np.concatenate([old_tris, stab]))
    info = {}
    for name, h in hands.items():
        p = holder_to_mm(h); a, b = OS.closest(p), RG.closest(p)
        info[name] = {'toOldPistolWithStabilisedModMm': r2(a[0], 2), 'toRebuiltPistolWithRealGripMm': r2(b[0], 2), 'differenceMm': r2(b[0] - a[0], 2)}
    rows = []
    for s in range(-50, 25, 10):
        o = C0 + AX * s; row = {'sMm': s}
        for surf, key in ((OS, 'oldWithStabilisedMod'), (RG, 'realGrip')):
            row[key] = {}
            for nm, d in (('front', FRONT), ('back', -FRONT), ('left', LEFT), ('right', -LEFT)):
                t = surf.ray(o + d * 60, -d); row[key][nm] = r2(None if t is None else 60 - t, 1)
        rows.append(row)
    report['realGripInformational'] = {'handAnchors': info, 'sections': rows,
        'note': 'not part of the pass: the hand today holds the Meshy grip (bare) or the Meshy grip with the Stabilised wrap; this is how far the real grip (core, plates, bent strap, screws, seams at their seat marks) differs at the same places. A large difference means the hand pose, solved against the old shapes, will not touch the new grip.'}
except Exception as e:
    report['realGripInformational'] = {'error': repr(e)}

report['pass'] = not fails; report['fails'] = fails; report['seconds'] = round(time.time() - t0, 1)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(report, open(OUT, 'w'), indent=1, default=lambda o: o.item() if hasattr(o, 'item') else str(o))
print(json.dumps({'pass': report['pass'], 'fails': fails,
                  'muzzle': {k: report['muzzle']['boreMouth'][k] for k in ('axisErrorMm', 'mouthXErrorMm')},
                  'grip': {'lineOffsetMm': report['grip']['fittedAxis']['largestLineOffsetMm'], 'tiltDeg': report['grip']['fittedAxis']['tiltBetweenDeg'], 'sectionMaxMm': grip_err, 'handAnchors': {k: v['errorMm'] for k, v in hp.items()}},
                  'rail': {k: report['rail'][k] for k in ('leftFace', 'rightFace', 'leftEdgesAndEnds')},
                  'mods': {k: {'mount': v['mountPoints'], 'moved': v['surfaceMovedAtMountMm'], 'deepNew': v['intoNewPistol'], 'deepOld': v['intoOldPistol']} for k, v in mod_rows.items()},
                  'realGrip': report['realGripInformational'].get('handAnchors', report['realGripInformational']),
                  'out': os.path.relpath(OUT, ROOT), 'seconds': report['seconds']}, indent=1))
