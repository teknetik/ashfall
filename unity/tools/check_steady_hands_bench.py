#!/usr/bin/env python3
"""Steady Hands bench: plays the slice (stages 0, 1, 6, 7) at Brann's workbench with real input and saves a capture per step.

Mouse mode (default) points, presses, circles and drags with the real pointer at the screen positions the game reports in
snapshot.json -> assembly (AssemblyQa). Keyboard mode (BENCH_MODE=keys) never moves the pointer: Tab moves the focus ring,
Space picks up / uses / holds, Q and E turn the held part, A and D steer.
Stages 2 to 5 are granted by dev.assembly.grant (the slice gives the finished grip complete), as in the Edit Mode bot,
unless BENCH_FULL=1, which plays them by hand too (about 200 actions).

  ~/.local/state/ward-programme/steady-hands-20261120/native_check.sh bench_slice unity/tools/check_steady_hands_bench.py ATHEN_EXE=<build>/AthenHill.x86_64
  ... BENCH_MODE=keys     keyboard only
  ... BENCH_REAL=1        as a player: a save after the primer (pistol equipped as sidearm, toolkit and inputs in the pack,
                          schematic known), Continue, E at Brann's workbench, Build by hand in the Fabricator
  ... BENCH_STOP=s1       stop after that stage (quick look)
  ... BENCH_FULL=1        stages 2 to 5 by hand as well
  ... BENCH_TURN_SIGN=-1  circle the other way (for the 18:05 build, whose turn was mirrored on the screen)
  ... BENCH_SOFT=1        an action that fails by hand is completed for the run (it still counts as failed) so the rest is played
  ... BENCH_TUTOR=1       also assert Brann's guided first job (tutor agent, 21 Nov): his line for the first step of each of
                          stages 0 to 4 played, and his how-line the first time each kind of action comes up (stages 0 to 6);
                          the run waits up to 25 s for each (the tutor never talks over a quick hand, so it is given time)

Every run starts by holding each camera shot in turn (dev.assembly.shot) and saving a frame of it: shot-<name>.png.
Traces too long for report.json go to files beside it (trace-*.json).

Output: unity/evidence/steady_hands/20261120/bench/native-<mode>/ (report.json, one PNG per step, run folder).

Changed 21 Nov (real art, slice 3): the pistol lies on the work mat turned half round from the art's pose (cell and latch to
the front), the gimbal's leads lie towards the player, s2.pry:clip_3 uses the `over` shot and s6.plug:plug a new side shot
`vise_r` (the shots list now has 13, with `vise_l` and `vise_r`). Each step's line records the shot the game had for it.
On the real pistol the trigger lead cannot be reached by its wire at s1.lead (it lies under the housing and the pin); the
script never makes that mistake, so nothing here depends on it.
"""
import json, math, os, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODE = os.environ.get('BENCH_MODE', 'mouse')
KEYS = MODE == 'keys'
os.environ.setdefault('ATHEN_OUT', str(ROOT / 'unity/evidence/steady_hands/20261120/bench' / ('native-' + MODE)))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import showcase_qa as S  # noqa: E402
from showcase_qa import qa, ok, note, cap  # noqa: E402

GRANT = [] if os.environ.get('BENCH_FULL') == '1' else ['s2', 's3', 's4', 's5']
TURN_SIGN = int(os.environ.get('BENCH_TURN_SIGN', '1'))
SOFT = os.environ.get('BENCH_SOFT') == '1'
TUTOR = os.environ.get('BENCH_TUTOR') == '1'
heard = set()   # every voice line id seen in a snapshot (the snapshot keeps the last 8)
taught = set()
failed_soft = []
shots = 0


def trace(name, data):
    """A long payload goes to its own file in the output folder (note() cuts what it is given)."""
    import json
    path = os.path.join(os.environ['ATHEN_OUT'], 'trace-%s.json' % name.replace(':', '_').replace('/', '_'))
    with open(path, 'w') as fh:
        json.dump(data, fh, indent=1, default=str)
    return path


# ---------------------------------------------------------------- state
def asm():
    a = S.snap().get('assembly') or {}
    v = a.get('voice') or {}
    heard.update(x for x in (v.get('spoken') or []) if x)
    if v.get('line'): heard.add(v['line'])
    return a


# ---------------------------------------------------------------- BENCH_TUTOR=1 (tutor agent, 21 Nov 2026)
def tutor_id(step):
    import re
    return 'tutor_' + re.sub(r'[^a-z0-9]+', '_', step.lower()).strip('_')


def teach_key(act):
    v, m = act.get('verb'), act.get('mode') or ''
    if v == 'Point': return 'point_aim' if m == 'aim' else 'point'
    if v == 'Window': return 'window_strike' if m == 'strike' else 'window_hold' if m == 'hold' else None
    return {'Seat': 'seat', 'Turn': 'turn', 'Path': 'path', 'Wipe': 'wipe', 'Flick': 'flick'}.get(v)


def tutor_wait(line_id, what, timeout=25):
    end = time.time() + timeout
    while line_id not in heard and time.time() < end:
        asm(); time.sleep(.25)
    return ok(line_id in heard, "Brann's guidance: " + what, {'line': line_id, 'heard': sorted(x for x in heard if x.startswith('tutor_'))[-12:]})


def settled(timeout=6):
    """The bench snapshot once the camera has stopped blending (positions are only right then)."""
    end = time.time() + timeout
    a = asm()
    while time.time() < end and (a.get('camera') or {}).get('blending'):
        time.sleep(.1); a = asm()
    time.sleep(.12)
    return asm()


def action(a, act_id):
    return next((x for x in a.get('actions') or [] if x['id'] == act_id), None)


def done(act_id):
    a = asm()
    if not a.get('open'):
        return True
    step, key = act_id.split(':')
    st = next((s for s in a['steps'] if s['id'] == step), None)
    return st is None or st['state'] == 'Done' or action(a, act_id) is None


def px(at, a=None):
    """Snapshot screen point (bottom-left origin) -> window pixels (top-left origin)."""
    h = (a or S.snap()).get('height') or S.snap()['height']
    return at[0], h - at[1]


# ---------------------------------------------------------------- real input
def move(p):
    from Xlib import X
    from Xlib.ext import xtest
    d = qa.focus(center=False); w = qa.window(); o = d.screen().root.translate_coords(w, 0, 0)
    xtest.fake_input(d, X.MotionNotify, x=o.x + int(round(p[0])), y=o.y + int(round(p[1]))); d.sync()


def glide(a, b, seconds=.35, steps=14):
    for i in range(1, steps + 1):
        t = i / steps; move((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)); time.sleep(seconds / steps)


def click(p, hold=.06):
    move(p); time.sleep(.08); qa.button(1, True); time.sleep(hold); qa.button(1, False); time.sleep(.15)


def wheel(notches):
    for _ in range(abs(int(notches))):
        b = 4 if notches > 0 else 5
        qa.button(b, True); qa.button(b, False); time.sleep(.07)


def key_tap(name, secs=.07):
    qa.key(name, True); time.sleep(secs); qa.key(name, False); time.sleep(.12)


def focus_on(target_id, max_tabs=60):
    for _ in range(max_tabs):
        f = (asm().get('focus') or {}).get('id')
        if f == target_id:
            return True
        key_tap('Tab')
    return (asm().get('focus') or {}).get('id') == target_id


def held():
    return asm().get('held') or {}


def shot(name):
    global shots
    shots += 1
    cap('%02d-%s' % (shots, name.replace(':', '_').replace('.', '_')), layout=False)


# ---------------------------------------------------------------- hands
def free_hand(act):
    h = held()
    if h.get('part') and h['part'] != act['part']:
        key_tap('x')
    h = held()
    if h.get('tool') and not act['tool'] and not (act['verb'] == 'Seat' and act['part'] == h['tool']):
        key_tap('x')


def take_tool(act):
    if not act['tool'] or act['tool'] == '*':
        return True
    if not act.get('toolInHand'):
        if held().get('part'):
            key_tap('x')
        a = settled(); act = action(a, act['id']) or act
        if not act.get('toolAt'):
            return ok(False, 'tool is on the bench: ' + act['tool'])
        if KEYS:
            tool_id = next((p['id'] for p in a['parts'] if p['id'].startswith('tools.') and act['tool'].split(':')[-1] in p['id']), act['tool'])
            focus_on(tool_id); key_tap('space')
        else:
            click(px(act['toolAt'], a))
        time.sleep(.3)
    for _ in range(3):
        a = asm(); now = action(a, act['id'])
        if not act['toolMode'] or (now and now.get('toolModeNow') == act['toolMode']):
            break
        key_tap('r')
    now = action(asm(), act['id'])
    return ok(bool(now and now.get('toolInHand')), 'took ' + act['tool'] + ' for ' + act['id'], (asm().get('held')))


def carry(act, hold=False):
    """Pick the action's part up. Mouse: a click leaves it in the hand; hold=True keeps the button down."""
    if held().get('part') == act['part']:
        return True
    a = settled(); now = action(a, act['id']) or act
    if not now.get('partAt'):
        return False
    p = px(now['partAt'], a)
    if KEYS:
        focus_on(act['part']); qa.key('space', True); time.sleep(.07)
        if not hold:
            qa.key('space', False)
        time.sleep(.7)
    else:
        move(p); time.sleep(.1); qa.button(1, True); time.sleep(.07)
        if not hold:
            qa.button(1, False)
        # off its parent: pull away from where it was taken
        # (21 Nov: up to 360 px; 174 px was too short for the trigger lead's plug, which needs 35 mm of drag at the vise)
        for i in range(1, 61):
            if not held().get('leaving'):
                break
            move((p[0], p[1] - 6 * i)); time.sleep(.05)
    # the snapshot lags the press: give the hand up to 2.5 s to report the part before judging
    end = time.time() + 2.5
    while time.time() < end and held().get('part') != act['part'] and not done(act['id']):
        if held().get('part'):
            break   # it took something else: the caller decides
        time.sleep(.1)
    return held().get('part') == act['part'] or done(act['id'])


def took_another(act):
    """The hand came away with a different part that has work of its own (two things lying at one spot): the game's next
    action follows the hand, so that is what is played now."""
    h = held()
    return bool(h.get('part') and h['part'] != act['part'] and h.get('action'))


def seat(act):
    part_is_tool = act['part'].startswith('tools.') and act['part'] != 'tools.roll'
    if part_is_tool:
        if held().get('tool') != act['part'] and held().get('part') != act['part']:
            a = settled(); now = action(a, act['id']) or act
            if KEYS:
                focus_on(act['part']); key_tap('space')
            else:
                click(px(now['partAt'], a))
        a = settled(); now = action(a, act['id']) or act
        if KEYS:
            focus_on(act['target']); key_tap('space')
        else:
            click(px(now['at'], a))
    elif not carry(act, hold=act.get('keepHold', False) or act['id'] == 's1.housing:slide'):
        if took_another(act):
            if not KEYS:
                qa.button(1, False)
            return 'redirected'
        return False
    if act['mode'] == 'keyed' and held().get('flipped'):
        key_tap('r')   # the plug came to the hand the wrong way up
    if act['mode'] == 'inspect':
        for _ in range(40):
            if done(act['id']):
                break
            if KEYS:
                qa.key('e', True); time.sleep(.25); qa.key('e', False)
            else:
                wheel(1)
        return done(act['id'])
    parent = act['part'].rsplit('.', 1)[0]
    direction, last, since, pull = 1, 1e9, 0, 0
    end = time.time() + 25
    while time.time() < end and not done(act['id']):
        a = asm(); now = action(a, act['id'])
        if not now:
            break
        if KEYS:
            want = act['target'] if act['target'] not in ('seat', 'start', 'clear') else None
            f = (a.get('focus') or {}).get('id')
            if want and f != want:
                focus_on(want)
            elif not want and f in (None, act['part']):
                key_tap('Tab')
        elif (a.get('held') or {}).get('leaving'):
            # still coming off its parent: keep pulling away from where it was taken, never back towards it
            pull += 12; at = px(now['at'], a); move((at[0], at[1] - 120 - pull))
        else:
            move(px(now['at'], a))
        err = (a.get('held') or {}).get('yawError') or 0
        if err > 7:
            since += 1
            if since % 3 == 0:
                if err > last + .5:
                    direction = -direction
                last = err
                if KEYS:
                    k = 'e' if direction > 0 else 'q'; qa.key(k, True); time.sleep(.08 if err < 25 else .2); qa.key(k, False)
                else:
                    wheel(direction)
        time.sleep(.12)
    if not KEYS:
        qa.button(1, False)
    else:
        qa.key('space', False)
    return done(act['id'])


def turn(act):
    a = settled(); now = action(a, act['id']) or act
    c = px(now['partAt'] or now['at'], a)
    if KEYS:
        focus_on(act['part'] if act['mode'] != 'reveal' else act['part'])
        qa.key('space', True)
        end = time.time() + 40
        need = abs(act['turns']) + act['lo'] + min(.12, (act['hi'] - act['lo']) * .4)
        while time.time() < end and not done(act['id']):
            v = asm().get('verb') or {}
            if act['mode'] == 'stop' and (action(asm(), act['id']) or {}).get('partial', 0) >= need:
                break
            time.sleep(.05)
        qa.key('space', False); time.sleep(.5)
        return done(act['id'])
    move(c); time.sleep(.12); qa.button(1, True); time.sleep(.08)
    if act['mode'] == 'reveal':
        # one long drag to the right: the vise turns with it until the mark faces the camera, then swings back by itself
        x = c[0]; end = time.time() + 30
        while time.time() < end and not done(act['id']):
            if x < c[0] + 900:
                x += 6; move((x, c[1]))
            time.sleep(.03)
        qa.button(1, False)
        return done(act['id'])
    sign = (-1 if act['turns'] < 0 else 1) * TURN_SIGN
    need = abs(act['turns']) + (act['lo'] + min(.12, (act['hi'] - act['lo']) * .4) if act['mode'] == 'stop' else 0)
    ang, radius, end = 0.0, 46, time.time() + 60
    samples, n, t0 = [], 0, time.time()
    while time.time() < end and not done(act['id']):
        a = asm(); now = action(a, act['id'])
        if act['mode'] == 'stop' and now and now.get('partial', 0) >= need:
            time.sleep(.6); break
        n += 1
        if n % 10 == 1 and len(samples) < 40:
            samples.append({'t': round(time.time() - t0, 2), 'partial': (now or {}).get('partial'), 'verb': a.get('verb'), 'held': {k: (a.get('held') or {}).get(k) for k in ('part', 'tool', 'action')}})
        # clockwise on screen (y down) is positive
        ang += sign * math.radians(14)
        move((c[0] + radius * math.cos(ang), c[1] + radius * math.sin(ang))); time.sleep(.02)
    qa.button(1, False); time.sleep(.3)
    if not done(act['id']):
        trace('turn-' + act['id'], {'centre': c, 'act': act, 'samples': samples, 'final': asm()})
    return done(act['id'])


def window(act):
    mid = (act['lo'] + act['hi']) / 2
    if act['mode'] == 'wait':
        # nothing to do but leave it alone
        if held().get('part'):
            key_tap('x')
        end = time.time() + (act.get('seconds') or 10) + 6
        while time.time() < end and not done(act['id']):
            time.sleep(.25)
        return done(act['id'])
    if act['mode'] == 'sustain':
        a = settled(); now = action(a, act['id']) or act; p = px(now['at'], a); down = False
        if KEYS:
            focus_on(act['part'])
        else:
            move(p); time.sleep(.1)
        end = time.time() + (act.get('seconds') or 6) + 40
        while time.time() < end and not done(act['id']):
            v = (asm().get('verb') or {}).get('value') or 0
            want = v < mid
            if want != down:
                (qa.key('space', want) if KEYS else qa.button(1, want)); down = want
            time.sleep(.03)
        if down:
            (qa.key('space', False) if KEYS else qa.button(1, False))
        return done(act['id'])
    for _ in range(act['count'] + 4):
        if done(act['id']):
            break
        a = settled(); now = action(a, act['id']) or act
        p = px(now['at'], a)
        if KEYS:
            focus_on(act['target'] if act['target'].startswith('tools.') else act['part']); qa.key('space', True)
        else:
            move(p); time.sleep(.1); qa.button(1, True)
        end = time.time() + 6
        while time.time() < end:
            v = (asm().get('verb') or {}).get('value') or 0
            if v >= mid:
                break
            time.sleep(.02)
        if KEYS:
            qa.key('space', False)
        else:
            qa.button(1, False)
        time.sleep(.35)
    return done(act['id'])


def point(act):
    if act['mode'] == 'aim':
        if not carry(act):
            return False
        a = settled(); now = action(a, act['id']) or act
        p = px(now['at'], a)
        if KEYS:
            focus_on(act['target'])
        else:
            glide(px(now['partAt'] or now['at'], a), p)
        S.wait_for(lambda: held().get('aiming'), 5, what='aiming')
        time.sleep(.6); shot(act['id'] + '-aim')
        # the pistol is held up to the card: in the picture, in its lower third (builds from slice 3 on)
        snap = S.snap(); h = held(); at = h.get('partAt'); height = snap.get('height') or 1080; width = snap.get('width') or 1920
        if at:
            x, y = px(at, snap)
            ok(0 <= x <= width and height * 2 / 3 <= y <= height * 1.05, '%s: the pistol is in the lower third of the picture while it is aimed' % act['id'],
               {'pistol': [round(x), round(y)], 'window': [width, height], 'shot': (asm().get('camera') or {}).get('shot')})
        for _ in range(act['count'] + 3):
            if done(act['id']):
                break
            if KEYS:
                key_tap('space')
            else:
                click(p)
            time.sleep(.5)
        return done(act['id'])
    for m in (act['marks'] or [{'id': act['target'], 'at': act['at'], 'shown': True}]):
        if done(act['id']):
            break
        a = settled(); now = action(a, act['id']) or act
        live = next((x for x in now.get('marks') or [] if x['id'] == m['id']), None) or {'at': now['at'], 'shown': True}
        if not live.get('shown'):
            continue
        if KEYS:
            focus_on(m['id']); key_tap('space')
        else:
            click(px(live['at'], a))
        time.sleep(.3)
    return done(act['id'])


def flick(act):
    if not carry(act):
        return False
    if KEYS:
        qa.key('space', True); time.sleep(1.2); qa.key('space', False); time.sleep(.3)
        return done(act['id'])
    a = asm(); w, h = a.get('width') or S.snap()['width'], S.snap()['height']
    c = (w / 2, h * .55); end = time.time() + 12; i = 0
    while time.time() < end and not done(act['id']):
        move((c[0] + (160 if i % 2 == 0 else -160), c[1])); i += 1; time.sleep(.09)
    return done(act['id'])


def path(act):
    a = settled(); now = action(a, act['id']) or act
    pts = [px(p, a) for p in (now.get('path') or [])]
    if len(pts) < 2:
        return False
    if KEYS:
        focus_on(act['target']); qa.key('space', True); end = time.time() + 40; steer = None
        while time.time() < end and not done(act['id']):
            v = (asm().get('verb') or {}).get('value') or 0
            if v > .5:
                k = 'a' if steer != 'a' else 'd'
                if steer: qa.key(steer, False)
                steer = k; qa.key(k, True)
            elif v < .25 and steer:
                qa.key(steer, False); steer = None
            time.sleep(.1)
        if steer: qa.key(steer, False)
        qa.key('space', False)
        return done(act['id'])
    # a tear or a slip off the line ends the stroke and costs quality; a player goes again from where it stopped, slower
    for attempt, pace in enumerate((.45, .8, 1.2)):
        a = settled(); now = action(a, act['id'])
        if now is None:
            return True
        pts = [px(p, a) for p in (now.get('path') or [])] or pts
        faults = a.get('faults') or 0
        move(pts[0]); time.sleep(.12); qa.button(1, True); time.sleep(.08)
        for i in range(1, len(pts)):
            glide(pts[i - 1], pts[i], seconds=pace, steps=int(40 * pace))
            if done(act['id']):
                break
        time.sleep(.3); qa.button(1, False); time.sleep(.2)
        if done(act['id']):
            if attempt:
                note('%s: done on stroke %d (pace %.2f s a segment)' % (act['id'], attempt + 1, pace))
            return True
        note('%s: stroke %d did not finish it (faults %d -> %d, carried %s)' % (act['id'], attempt + 1, faults, asm().get('faults') or 0, (action(asm(), act['id']) or {}).get('carried')))
    return done(act['id'])


def wipe(act):
    a = settled(); now = action(a, act['id']) or act
    z = [px(c, a) for c in (now.get('zone') or [])]
    if len(z) != 4:
        return False
    def at(u, v):
        top = (z[0][0] + (z[1][0] - z[0][0]) * u, z[0][1] + (z[1][1] - z[0][1]) * u); bot = (z[3][0] + (z[2][0] - z[3][0]) * u, z[3][1] + (z[2][1] - z[3][1]) * u)
        return top[0] + (bot[0] - top[0]) * v, top[1] + (bot[1] - top[1]) * v
    if KEYS:
        focus_on(act['target']); qa.key('space', True); end = time.time() + 40
        while time.time() < end and not done(act['id']):
            time.sleep(.1)
        qa.key('space', False)
        return done(act['id'])
    move(at(.05, .05)); time.sleep(.12); qa.button(1, True); time.sleep(.08)
    for sweep in range(3):
        for row in range(9):
            v = (row + (.5 if sweep % 2 else 0)) / 8
            a0, a1 = (at(.02, v), at(.98, v)) if row % 2 == 0 else (at(.98, v), at(.02, v))
            glide(a0, a1, seconds=.25, steps=10)
            if done(act['id']):
                break
        if done(act['id']):
            break
    qa.button(1, False); time.sleep(.3)
    return done(act['id'])


VERBS = {'Seat': seat, 'Turn': turn, 'Window': window, 'Point': point, 'Flick': flick, 'Path': path, 'Wipe': wipe}


def play():
    stop = os.environ.get('BENCH_STOP')
    seen_stage = None
    for _ in range(420):
        a = settled()
        if not a.get('open'):
            return True
        stage = (a.get('stage') or {}).get('id')
        if stage != seen_stage:
            ok(True, 'stage ' + str(stage) + ': ' + str((a.get('stage') or {}).get('label')), {'voice': (a.get('voice') or {}).get('spoken'), 'shot': (a.get('camera') or {}).get('shot')})
            shot('stage-' + str(stage)); seen_stage = stage
            nxt = a.get('next')
            if TUTOR and stage in ('s0', 's1', 's2', 's3', 's4') and stage not in GRANT and nxt:
                tutor_wait(tutor_id(nxt.split(':')[0]), 'the first step of stage %s is spoken (%s)' % (stage, nxt))
            if stop and stage and stage > stop:
                return True
        if stage in GRANT:
            qa.cmd('dev.assembly.grant', stages=GRANT, precision=.9); time.sleep(.8)
            ok((asm().get('stage') or {}).get('id') == 's6', 'stages 2 to 5 granted: the finished grip is on the mat', asm().get('stage'))
            continue
        act_id = a.get('next')
        act = action(a, act_id) if act_id else None
        if not act:
            return ok(False, 'something is open to do', {'stage': stage, 'next': act_id})
        k = teach_key(act)
        # an optional step (the shake before) is taught only when the player takes it up, so it is not waited for here
        if TUTOR and k and k not in taught and stage not in ('s7',) and not act.get('optional'):
            taught.add(k)
            tutor_wait('tutor_' + k + '_verb', 'how to %s is spoken the first time it comes up (%s)' % (k, act_id))
        free_hand(act)
        if not take_tool(act):
            return False
        t0 = time.time()
        good = VERBS[act['verb']](action(settled(), act_id) or act)
        if good == 'redirected':
            note('%s: the hand took %s, which lay on top and has its own place to go; playing that first' % (act_id, held().get('part')), held())
            continue
        ok(good, '%s %s (%s) by %s' % (act_id, act['verb'], act['mode'] or '-', MODE), {'seconds': round(time.time() - t0, 1), 'held': held(), 'verb': asm().get('verb'), 'refusals': asm().get('refusals'), 'shot': (asm().get('camera') or {}).get('shot')})
        shot(act_id)
        if not good:
            trace('failed-' + act_id, {'act': act, 'assembly': asm()})
            if not SOFT:
                return False
            # BENCH_SOFT=1: the failure stands, but the action is completed for the run so that the rest of the job is played
            if qa.button: qa.button(1, False)
            for k in ('space', 'a', 'd', 'q', 'e'):
                qa.key(k, False)
            key_tap('x'); time.sleep(.2)
            step, key = act_id.split(':')
            qa.cmd('dev.assembly.complete', step=step, key=key, precision=.9); time.sleep(.6)
            failed_soft.append(act_id)
            if not done(act_id):
                return ok(False, '%s could not be completed for the run either' % act_id, asm().get('next'))
            note('%s: completed for the run (BENCH_SOFT); %d so far' % (act_id, len(failed_soft)))
    return ok(False, 'the job finished within the action limit')


def real_save(folder):
    """BENCH_REAL=1 (21 Nov): a save as a player has it after the primer and the identify talk: the scrap pistol equipped as
    the sidearm, the Field Toolkit, the damaged servo, alloy and nanites in the pack, the grip schematic known, the order at
    Steady Hands. The same shape as check_crafting_flow_native.py's fixture."""
    folder.mkdir(parents=True, exist_ok=True)
    s = {'version': 2, 'savedUtc': '2026-11-21T09:00:00.0000000Z', 'build': 'qa', 'credits': 60, 'purchases': 0, 'sales': 0,
         'items': [{'itemId': 'scrap_alloy', 'quantity': 4}, {'itemId': 'nanite_residue', 'quantity': 6},
                   {'itemId': 'droid_servo_damaged', 'quantity': 1}, {'itemId': 'field_toolkit', 'quantity': 1}, {'itemId': 'medkit', 'quantity': 1}],
         'crafting': {'known': ['recipe_grip_stabilised_pistol'], 'crafted': [], 'crafts': 0, 'fitted': []},
         'loot': {'rng': 'bc1721a626f0570d', 'rolls': 4, 'misses': [], 'collected': ['scrap_alloy', 'nanite_residue', 'droid_servo_damaged']},
         'bermsStep': 'Complete', 'hasPistol': True,
         'orders': {'index': 0, 'id': 'order_steady_hands', 'testFired': [], 'reported': []},
         'city': {'visitedHill': True, 'boughtFlask': True, 'soldScrap': True, 'linked': True, 'spoken': ['npc_linn', 'npc_mira', 'npc_torr', 'npc_vex'],
                  'selectedDestination': '', 'flags': ['brann_met', 'tamsin_met']},
         'character': {'version': 2, 'level': 1, 'experience': 0, 'attributePoints': 0, 'skillPoints': 0,
                       'attributes': [{'id': x, 'count': 10} for x in ['agility', 'endurance', 'intellect', 'perception', 'resolve', 'strength']],
                       'skills': [{'id': k, 'count': 0} for k in S.SKILLS],
                       'equipped': [{'slot': 'secondary', 'itemId': 'scrap_pistol'}, {'slot': 'armour_chest', 'itemId': 'field_vest'},
                                    {'slot': 'armour_feet', 'itemId': 'field_boots'}, {'slot': 'storage', 'itemId': 'field_backpack'}]}}
    (folder / 'ward-save.json').write_text(json.dumps(s, indent=1))


def open_by_hand():
    """As a player: walk up to Brann's workbench, E. With the grip's order open the bench goes straight to the job; otherwise
    the Fabricator opens, the grip is chosen and Build by hand pressed."""
    qa.goto('salvage_bench'); time.sleep(.6); qa.tap('e', settle=1.2)
    S.wait_for(lambda: qa.state() in ('Fabricator', 'Assembly'), 6, what='fabricator or bench')
    if qa.state() == 'Fabricator':
        lay = qa.ui(); cap('00-fabricator', layout=True)
        for name in ('fab-recipe-recipe_grip_stabilised_pistol', 'fabricator-build'):
            e = qa.el(lay, name) or {}
            ok(bool(e.get('visible')), 'the Fabricator shows ' + name, e)
            if not e.get('visible'):
                return
            x, y, w, h = e['bounds']; qa.click_at(x + w / 2, y + h / 2); time.sleep(1.0); lay = qa.ui()
    note('opened the bench through ' + ('Build by hand' if qa.state() == 'Assembly' else 'nothing (state %s)' % qa.state()), {'notice': (S.snap().get('session') or {}).get('notice')})


def body():
    real = os.environ.get('BENCH_REAL') == '1'
    if real:
        real_save(S.OUT / 'save'); S.launch(run='run', save=S.OUT / 'save'); S.start()
    else:
        S.launch(run='run'); S.start(continue_game=False)
    qa.goto('bench_steady_hands'); time.sleep(1.0)
    cap('00-at-the-bench', layout=False)
    if real:
        open_by_hand()
    else:
        qa.cmd('dev.assembly.open', force=True, fresh=True)
    ok(S.wait_for(lambda: qa.state() == 'Assembly' and asm().get('open'), 8, what='bench open') is not None, 'the bench opens (state Assembly)', {'state': qa.state(), 'assembly': {k: asm().get(k) for k in ('open', 'detached', 'lastNotice')}})
    a = settled(10)
    c = S.snap().get('cursor') or {}
    ok(c.get('lockState') == 'None' and c.get('visible'), 'the cursor is free and visible at the bench', c)
    ok((a.get('camera') or {}).get('active'), 'the bench camera has the view', a.get('camera'))
    ok((a.get('camera') or {}).get('shot') in ('work', 'wide'), "the bench is entered on 'work', or on 'wide' when the pistol to pick up lies outside it (21 Nov: it does, at the right end)", (a.get('camera') or {}).get('shot'))
    ok(len(a.get('actions') or []) > 0, 'there is work open', [x['id'] for x in a.get('actions') or []])
    lay = qa.ui()
    shade = qa.el(lay, 'shade'); modal = qa.el(lay, 'modal')
    ok(not (shade or {}).get('visible') and not (modal or {}).get('visible'), 'no shade and no window over the bench', {'shade': (shade or {}).get('visible'), 'modal': (modal or {}).get('visible')})
    ok(bool((a.get('hud') or {}).get('legend')), 'the key legend shows on first use', a.get('hud'))
    # one frame of every shot, each run (the shot is held until released)
    names = (a.get('camera') or {}).get('shots') or []
    for name in names:
        r = qa.cmd('dev.assembly.shot', shot=name); time.sleep(.6)
        cap('shot-' + name, layout=False)
    qa.cmd('dev.assembly.shot', shot='auto'); time.sleep(.6)
    ok(len(names) >= 6 and (asm().get('camera') or {}).get('pinned') in (None, ''), 'every shot was held for a frame and let go again', {'shots': names, 'camera': asm().get('camera')})
    if KEYS:
        qa.PARK = (40, 40); qa.focus()
    finished = play()
    a = asm()
    if os.environ.get('BENCH_STOP'):
        note('stopped early as asked', a.get('stage'))
        return
    S.wait_for(lambda: qa.state() == 'Play', 8, what='back in play')
    a = asm()
    ok(finished and not a.get('open') and a.get('lastResult'), 'the job is finished and the bench has closed', a.get('lastResult') or a.get('lastNotice'))
    if SOFT:
        ok(not failed_soft, 'no action had to be completed for the run', failed_soft)
    ok(qa.state() == 'Play', 'the player has control back', qa.state())
    c = S.snap().get('cursor') or {}
    ok(c.get('lockState') == 'Locked', 'the cursor is locked for play again', c)
    cap('99-after', layout=False)
    report = S.report; report['mode'] = MODE; report['captures_count'] = shots


S.run(body)
