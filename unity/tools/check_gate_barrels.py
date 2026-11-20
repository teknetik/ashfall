"""Native real-input check of the gate barrels pass (art/gate_barrels_20261120/README.md, 20 Nov 2026).

Carl: "Barrels on the floor by the waste gate, the broken ones on the floor need to be able to be walked over or need to
go". The broken Poly Haven barrel sets (staves, hoops, lids, a barrel half) lie at the Karaveen caravan overflow inside
the West Gate (-X, by the market) and beside the Rations stall; their colliders now hold only the whole barrels.

For every walk line of the pass (landmarks gb_<line>_a / gb_<line>_b) the player is put at one end, turned to the other
and walked across with real W input, both ways. Each crossing must reach the far end in about the time a free walk
takes (3.4 m/s, 35 % + 0.6 s slack for input and turning), with no height jump over 0.3 m (no popping up onto
anything) and no sudden pull-in of the follow camera. The forward crossing stops half-way for a follow-view capture
(the colonist standing among the staves). Then a frame at every cam_gb_* review camera at 13:00 and 20:30.
  ATHEN_EXE=<player> ATHEN_OUT=<folder> python unity/tools/check_gate_barrels.py
"""
import math, os, time
from pathlib import Path
os.environ.setdefault('ATHEN_OUT', str(Path(__file__).resolve().parents[2] / 'unity/evidence/showcase_phase2/20261120/gate_barrels/native'))
import showcase_qa as S
from showcase_qa import qa, ok, note, cap

S.NAME = 'gate_barrels'
S.report['name'] = 'gate_barrels'

LINES = [  # name, (x0, z0), (x1, z1): the same table as GateBarrelsPass20261120.Lines
    ('caravan_staves_ew', (-48.4, 6.6), (-42.6, 6.6)),
    ('caravan_staves_ns', (-46.6, 9.2), (-46.6, 6.15)),
    ('caravan_between', (-45.5, 3.4), (-45.5, 8.8)),
    ('rations_staves_ns', (-37.0, -14.6), (-37.0, -16.6)),
    ('rations_staves_ew', (-39.4, -16.2), (-36.1, -16.2)),
]
CAMERAS = ['cam_gb_caravan_east', 'cam_gb_caravan_north', 'cam_gb_rations_west', 'cam_gb_rations_north']
WALK = 3.4


def walk_line(name, a, b, capture_mid=None):
    """a, b: (x, z). Hold real W from the player's position towards b until within 0.25 m of b (progress along a->b) or timeout.
    Returns held seconds, reached flag, max rise, largest single-sample rise, camera distance trace."""
    dx, dz = b[0] - a[0], b[1] - a[1]
    dist = math.hypot(dx, dz); ux, uz = dx / dist, dz / dist
    qa.face(*b)
    time.sleep(.45)
    p0 = qa.pos()
    y0 = p0[1]
    held, captured = 0.0, False
    ys, cams, prog = [y0], [], 0.0
    limit = dist / WALK * 1.35 + 0.6
    qa.focus()
    qa.key('w', True)
    t = time.monotonic()
    try:
        while held + (time.monotonic() - t) < limit + 2.0:
            s = qa.snap()
            p = s['player']['position']
            prog = (p[0] - a[0]) * ux + (p[2] - a[1]) * uz
            ys.append(p[1])
            cams.append((s.get('camera') or {}).get('distance'))
            if capture_mid and not captured and prog >= dist / 2:
                qa.key('w', False)
                held += time.monotonic() - t
                time.sleep(.35)
                cap(capture_mid)
                captured = True
                qa.focus()
                qa.key('w', True)
                t = time.monotonic()
                continue
            if prog >= dist - .25:
                break
            time.sleep(.04)
    finally:
        qa.key('w', False)
    held += time.monotonic() - t
    rise = max(ys) - y0
    step = max((y1 - y0_) for y0_, y1 in zip(ys, ys[1:])) if len(ys) > 1 else 0
    cams = [c for c in cams if c is not None]
    cam_step = max((abs(c1 - c0) for c0, c1 in zip(cams, cams[1:])), default=0)
    return dict(line=name, dist=round(dist, 2), held=round(held, 2), limit=round(limit, 2), reached=prog >= dist - .25, progress=round(prog, 2),
                rise=round(rise, 3), maxStep=round(step, 3), camDistMin=round(min(cams), 2) if cams else None,
                camDistMax=round(max(cams), 2) if cams else None, camMaxStep=round(cam_step, 3), end=qa.pos())


def body():
    S.launch(save=S.kit_save(S.OUT / 'save'))
    S.start()
    S.time_set(13)
    for name, a, b in LINES:
        for rev in (False, True):
            src, dst = (b, a) if rev else (a, b)
            qa.release_all()
            qa.goto('gb_%s_%s' % (name, 'b' if rev else 'a'))
            time.sleep(.5)
            start = qa.pos()
            ok(S.dist(start, [src[0], 0, src[1]]) < .6, 'player placed at the %s end of %s' % ('far' if rev else 'near', name), start)
            r = walk_line(name, (start[0], start[2]), dst, capture_mid=None if rev else 'mid-%s' % name)
            label = '%s%s' % (name, ' (reverse)' if rev else '')
            ok(r['reached'], '%s: real W walks across to the far end' % label, r)
            ok(r['held'] <= r['limit'], '%s: crossing takes about a free walk (%.2f s <= %.2f s)' % (label, r['held'], r['limit']), r)
            ok(r['rise'] <= .30 and r['maxStep'] <= .25, '%s: no pop upwards (rise %.2f m, largest step %.2f m)' % (label, r['rise'], r['maxStep']), r)
            if r['camMaxStep'] is not None:
                ok(r['camMaxStep'] <= .8, '%s: follow camera distance has no sudden pull-in (largest change %.2f m between samples)' % (label, r['camMaxStep']), r)
    qa.release_all()
    for hour in (13, 20.5):
        S.time_set(hour)
        time.sleep(.8)
        for c in CAMERAS:
            qa.view(c)
            time.sleep(.5)
            got = cap('%s-h%05.2f' % (c, hour))
            ok(got is not None, 'capture at %s %05.2f' % (c, hour), got)
    qa.view('follow')


S.run(body)
