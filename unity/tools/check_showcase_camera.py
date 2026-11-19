"""Native real-input check of the showcase camera package (art/showcase_20261119/showcase_camera/README.md, test plan 2-11)
plus the interface package's lower-third layout (art/showcase_20261119/interface/README.md, steps 1, 3, 4).

Conversation camera: every talking colonist (Mira, Torr, Vex, Linn, Brann in Salvage, Tamsin in Field Supply, Wardens Ossa
and Rell): E engages the shoulder framing (or the eye-line fallback), no camera overlaps, the dialogue is the lower third,
a capture; Esc restores yaw/pitch/boom/position exactly. First person: depth of field only, centred dialogue. Reduced
Motion: cut. Switch off: no framing. Photo mode: open/freeze/fly/limits/rows/capture (two PNGs: size, upright, not black,
opaque)/exit with P and Esc/refusals/F8; inside the container home and out through its door.
  ATHEN_EXE=<player> python unity/tools/check_showcase_camera.py [OUT]
"""
import math, time
from pathlib import Path
import showcase_qa as S
from showcase_qa import qa, ok, note, cap

SAVE = S.kit_save(S.OUT / 'save', flags=['home_asked', 'home_leased'])
NPCS = [  # name, landmark, npc x/z, approach offset
    ('Mira', 'basic_general', (8.0, 15.8)),
    ('Torr', 'mission_slab', (9.0, -12.0)),
    ('Vex', 'west_gate', (41.7, -1.5)),
    ('Linn', 'oa_hill', (2.5, 4.7)),
    ('Brann', 'salvage_counter', (-15.8, 15.45)),
    ('Tamsin', 'field_supply_counter', (20.45, -11.7)),
    ('Ossa', 'checkpoint_ossa', None),
    ('Rell', 'checkpoint_rell', None),
]


def cam():
    s = S.snap(); c = s['camera']; p = s['player']['position']
    # the camera relative to the colonist: the capsule may settle by a millimetre or two while the dialogue is open
    return dict(yaw=c['yaw'], pitch=c['pitch'], boom=c['boom'], position=[c['position'][i] - p[i] for i in range(3)], world=c['position'], player=p, firstPerson=c['firstPerson'])


def same(a, b, tol=.001):
    return (abs((a['yaw'] - b['yaw'] + 180) % 360 - 180) < .01 and abs(a['pitch'] - b['pitch']) < .01 and abs(a['boom'] - b['boom']) < .001
            and max(abs(x - y) for x, y in zip(a['position'], b['position'])) <= tol)


def open_dialogue(name, landmark, xz, press=True):
    qa.goto(landmark); qa.view('follow'); time.sleep(.9)
    if xz:
        qa.face(*xz); time.sleep(.3)
    prompt = S.snap()['interaction']['prompt'] or ''
    if name not in prompt and xz:
        p = qa.pos()
        d = math.hypot(xz[0] - p[0], xz[1] - p[2])
        if d > 2.2:
            try:
                qa.walk_to(xz[0] + (p[0] - xz[0]) * 1.8 / d, xz[1] + (p[2] - xz[1]) * 1.8 / d, tol=.5, timeout=10)
            except TimeoutError:
                pass
            qa.face(*xz); time.sleep(.3)
        prompt = S.snap()['interaction']['prompt'] or ''
    if name not in prompt:
        return False, prompt
    if not press:
        return True, prompt
    qa.tap('e', settle=.05)
    return qa.state() == 'Dialogue' or bool(S.wait_for(lambda: qa.state() == 'Dialogue', 3)), prompt


def back_off(npc, dist, timeout=10):
    t_end = time.monotonic() + timeout
    while time.monotonic() < t_end:
        p = qa.pos()
        if math.hypot(p[0] - npc[0], p[2] - npc[1]) >= dist:
            return True
        qa.face(*npc); qa.hold('s', .4)
    return False


def layout_check(tag):
    lay = qa.ui()
    m = qa.el(lay, 'modal') or {}
    h = S.hud()
    return dict(layout=h.get('dialogueLayout'), shade=h.get('shadeDimmed'), held=h.get('modalHeld'), hidden=h.get('hidden'), modal=m.get('bounds'),
                title=(qa.el(lay, 'modal-title') or {}).get('text'))


def body():
    S.launch(save=SAVE)
    S.start()
    S.time_set(13)
    s = S.show()
    ok(s['conversation']['installed'] and s['photo']['installed'], 'conversation camera and photo mode installed', s)
    ok(not s['cinematic'], 'outside dialogue the camera is not under cinematic control')
    S.report['npcs'] = {}

    # ---- conversation camera on every talking colonist
    for name, landmark, xz in NPCS:
        hour = 20.5 if name in ('Brann',) else 13
        S.time_set(hour)
        ready, prompt = open_dialogue(name, landmark, xz, press=False)
        if ready and name == 'Mira':
            # a real walk-up: the basic_general landmark stands the colonist almost inside Mira's counter
            back_off(xz, 3.0); t_w = time.monotonic() + 4
            while time.monotonic() < t_w and 'Mira' not in (S.snap()['interaction']['prompt'] or ''):
                qa.face(*xz); qa.hold('w', .15)
            prompt = S.snap()['interaction']['prompt'] or ''
            note('Mira walk-up distance', round(S.dist(qa.pos(), (xz[0], 0, xz[1])), 2))
            ready = 'Mira' in prompt
        if not ready:
            ok(False, f'{name}: talk prompt reached', prompt); continue
        time.sleep(1.5)
        settle0 = cam(); time.sleep(.5)
        before = cam()
        drift = max(abs(x - y) for x, y in zip(settle0['position'], before['position']))
        if drift > .0005:
            note(f'{name}: follow camera still settling before E', round(drift, 4))
        qa.tap('e', settle=.05)
        opened = bool(S.wait_for(lambda: qa.state() == 'Dialogue', 3))
        if not opened:
            ok(False, f'{name}: dialogue opens with E', prompt); continue
        # open_dialogue may have stepped closer: take the pose recorded just before E from the snapshot history
        t_open = time.monotonic()
        w = S.wait_for(lambda: S.show()['conversation']['weight'] >= .999, 3)
        c = S.show()['conversation']
        lay = layout_check(name)
        time.sleep(.7)   # adaptive fades take 0.6 s
        lay = layout_check(name)
        snapc = S.snap()['camera']
        rec = dict(conversation=c, layout=lay, overlaps=snapc['overlaps'], blend=round(time.monotonic() - t_open, 2))
        S.report['npcs'][name] = rec
        ok(c['active'] and (c['framing'] or c['eyeLine']) and c['weight'] >= .999, f'{name}: conversation camera engaged and framing', {k: c[k] for k in ('active', 'framing', 'eyeLine', 'weight', 'side', 'subject')})
        ok(not snapc['overlaps'], f'{name}: camera clear of geometry', snapc['overlaps'])
        ok(lay['layout'] == 'lowerThird' and not lay['shade'], f'{name}: dialogue is the lower third, no shade', lay)
        ok(all(p in (lay['hidden'] or []) for p in ('identity', 'fieldNotes', 'compass', 'log', 'keyHints', 'hotbar')), f'{name}: every HUD panel gives way to the lower third', lay['hidden'])
        if lay['modal']:
            x, y, wdt, hgt = lay['modal']
            ok(y + hgt > 960 and y > 600, f'{name}: panel sits in the lower part of the frame', lay['modal'])
        cap(f'conversation-{name.lower()}-{"2030" if hour > 20 else "1300"}')
        qa.tap('Escape', settle=.05)
        S.wait_for(lambda: S.show()['conversation']['weight'] <= 0 and not S.show()['cinematic'], 3)
        time.sleep(.3)
        after = cam()
        rec['restore'] = dict(before=before, after=after)
        if S.snap()['player']['position'] and qa.state() == 'Play':
            ok(same(before, after), f'{name}: camera restored exactly after Esc', rec['restore'])
        h = S.hud()
        ok(not h.get('hidden'), f'{name}: HUD panels back after the dialogue (Full mode)', h.get('hidden'))
    S.time_set(13)

    # ---- odd-angle walk-ups to Vex: from his east side and from his south side
    for tag, spot in (('east', (43.5, -1.3)), ('south', (41.6, -3.3))):
        qa.goto('west_gate'); qa.view('follow'); time.sleep(.6)
        try:
            qa.walk_to(*spot, tol=.5, timeout=12)
        except TimeoutError:
            note(f'walk to the {tag} side stopped', qa.pos())
        qa.face(41.7, -1.5); time.sleep(.5)
        note(f'Vex {tag} approach: player at', qa.pos())
        if 'Vex' in (S.snap()['interaction']['prompt'] or ''):
            qa.tap('e', settle=1.2)
            c = S.show()['conversation']
            ok(c['active'] and (c['framing'] or c['eyeLine']), f'Vex from the {tag} side, camera off-axis: framing engages', c)
            cap(f'conversation-vex-{tag}-approach')
            qa.tap('Escape', settle=.8)
        else:
            note(f'no Vex prompt from the {tag} side', S.snap()['interaction']['prompt'])

    # ---- first person: depth of field only, centred dialogue (Vex)
    qa.goto('west_gate'); qa.view('follow'); time.sleep(.6); qa.face(41.7, -1.5)
    d = qa.focus()
    from Xlib import X
    from Xlib.ext import xtest
    for _ in range(12):
        xtest.fake_input(d, X.ButtonPress, 4); xtest.fake_input(d, X.ButtonRelease, 4); d.sync(); time.sleep(.06)
    time.sleep(.6)
    fp = S.snap()['camera']['firstPerson']
    ok(fp, 'wheel reaches first person')
    if fp:
        before = cam()
        qa.face(41.7, -1.5); time.sleep(.3); before = cam()
        opened, prompt = open_dialogue('Vex', 'west_gate', (41.7, -1.5))
        time.sleep(1.0)
        c = S.show()['conversation']; lay = layout_check('vex-fp')
        ok(opened and c['active'] and not c['framing'], 'first person: conversation active (depth of field) without framing', c)
        ok(lay['layout'] == 'centred' and lay['shade'], 'first person: centred dialogue with shade', lay)
        cap('conversation-vex-first-person')
        qa.tap('Escape', settle=.8)
    for _ in range(12):
        xtest.fake_input(d, X.ButtonPress, 5); xtest.fake_input(d, X.ButtonRelease, 5); d.sync(); time.sleep(.06)
    time.sleep(.6)

    # ---- switch off: no framing, centred
    qa.cmd('conversationCamera', enabled=False)
    opened, _ = open_dialogue('Mira', 'basic_general', (8.0, 15.8))
    time.sleep(1.0)
    c = S.show()['conversation']; lay = layout_check('mira-off')
    ok(opened and not c['framing'] and c['weight'] == 0, 'conversation camera off: no framing', c)
    ok(lay['layout'] == 'centred', 'conversation camera off: centred dialogue', lay)
    qa.tap('Escape', settle=.6)
    qa.cmd('conversationCamera', enabled=True)

    # ---- Reduced Motion: the framing cuts in
    qa.tap('Escape', settle=.5); qa.activate('reduced-motion'); qa.tap('Escape', settle=.6)
    opened, _ = open_dialogue('Mira', 'basic_general', (8.0, 15.8))
    time.sleep(.15)
    c = S.show()['conversation']
    ok(opened and c['weight'] >= .999, 'Reduced Motion: framing cuts in (weight 1 within 0.15 s)', c)
    qa.tap('Escape', settle=.15)
    ok(S.show()['conversation']['weight'] == 0, 'Reduced Motion: framing cuts out', S.show()['conversation'])
    qa.tap('Escape', settle=.5); qa.activate('reduced-motion'); qa.tap('Escape', settle=.6)

    # ---- photo mode
    qa.goto('hill_tree'); qa.view('follow'); time.sleep(1.0); qa.yaw(200); qa.pitch(8); time.sleep(.4)
    hour0 = S.dev()['clock']['hour']
    before = cam()
    qa.tap('p', settle=.6)
    ph = S.show()['photo']
    ok(ph['active'] and S.show()['timeScale'] == 0 and ph['panelShown'], 'P opens photo mode: frozen, panel shown', ph)
    ok(S.snap()['cursor']['lockState'] == 'Locked', 'photo mode keeps the cursor locked', S.snap()['cursor'])
    cap('photo-mode-panel')
    p0 = S.snap()['camera']['position']
    qa.hold('w', 1.5)
    p1 = S.snap()['camera']['position']
    ok(S.dist(p0, p1) > .5, 'photo mode: W flies the camera', {'from': p0, 'to': p1})
    qa.hold(['Shift_L', 'w'], 6)
    head = S.snap()['player']['position']
    p2 = S.snap()['camera']['position']
    d15 = math.dist(p2, [head[0], head[1] + 1.6, head[2]])
    ok(d15 <= 15.5, 'photo mode: camera held within 15 m of the colonist', round(d15, 2))
    qa.hold(['Shift_L', 'c'], 5)
    p3 = S.snap()['camera']['position']
    ok(p3[1] > -.2, 'photo mode: cannot fly under the paving', p3)
    qa.tap('r', settle=.4)   # reset view
    # rows: Down through all rows, Right on field of view
    c0 = S.show()['photo']
    rows = []
    for _ in range(11):
        rows.append(S.show()['photo']['selected']); qa.tap('Down', settle=.12)
    note('photo rows in order', rows)
    S.report['photoRows'] = rows
    # field of view row: back to the top
    for _ in range(11):
        if S.show()['photo']['selected'] in ('FieldOfView', 'Fov'):
            break
        qa.tap('Up', settle=.1)
    fov0 = S.show()['photo']['fieldOfView']
    qa.tap('Right', settle=.2); qa.tap('Right', settle=.2)
    ok(S.show()['photo']['fieldOfView'] != fov0, 'photo mode: Right changes the selected row (field of view)', (fov0, S.show()['photo']['fieldOfView']))
    # exposure and time of day rows change the picture
    for target, keyn in (('Exposure', 'Right'), ('TimeOfDay', 'Right')):
        for _ in range(11):
            if S.show()['photo']['selected'] == target:
                break
            qa.tap('Down', settle=.1)
        v0 = S.show()['photo']['exposure' if target == 'Exposure' else 'hour']
        for _ in range(4):
            qa.tap(keyn, settle=.12)
        v1 = S.show()['photo']['exposure' if target == 'Exposure' else 'hour']
        ok(v1 != v0, f'photo mode: {target} row changes its value', (v0, v1))
    cap('photo-mode-adjusted')
    # capture with F12
    home = qa.RUN / 'home/Pictures/Ashfall'
    qa.tap('F12', settle=.2)
    S.wait_for(lambda: S.show()['photo']['lastSupersampled'] and Path(S.show()['photo']['lastSupersampled']).exists(), 25)
    time.sleep(1.5)
    ph = S.show()['photo']
    files = sorted(home.glob('*.png')) if home.exists() else []
    S.report['photoFiles'] = [str(f) for f in files]
    ok(len(files) >= 2 and ph['lastCapture'] and ph['lastSupersampled'], 'F12 writes the 1x and the supersampled PNG', {'files': [f.name for f in files], 'status': ph['status'], 'error': ph['lastError']})
    for f in files[:2]:
        st = S.png_stats(f)
        S.report.setdefault('photoStats', {})[f.name] = st
        big = '_2x' in f.name
        want = (3840, 2160) if big else (1920, 1080)
        ok(tuple(st['size']) == want, f'{f.name}: size {want[0]}x{want[1]}', st['size'])
        ok(st['alphaMin'] >= 250, f'{f.name}: opaque', st)
        ok(st['mean'] > 20 and st['stddev'] > 8, f'{f.name}: not black or flat', st)
        ok(st['top'] >= st['bottom'] * .6, f'{f.name}: upright (sky brighter than or near the ground)', st)
    # exit with P: restore
    qa.tap('p', settle=.8)
    after = cam()
    ok(not S.show()['photo']['active'] and S.show()['timeScale'] == 1 and qa.state() == 'Play', 'P closes photo mode: time scale 1, Play', S.show())
    ok(abs(S.dev()['clock']['hour'] - hour0) < .05, 'clock hour restored after photo mode', (hour0, S.dev()['clock']['hour']))
    ok(same(before, after, tol=.01), 'follow camera pose restored after photo mode', dict(before=before, after=after))
    ok(S.snap()['cursor']['lockState'] == 'Locked', 'cursor locked again after photo mode', S.snap()['cursor'])
    # exit with Esc: not the pause menu
    qa.tap('p', settle=.5); qa.tap('Escape', settle=.8)
    ok(not S.show()['photo']['active'] and qa.state() == 'Play', 'Esc closes photo mode without opening the pause menu', qa.state())
    # refusals
    for what, open_keys, close_keys in (('pack', ['Tab'], ['Tab']), ('journal', ['j'], ['j']), ('pause', ['Escape'], ['Escape'])):
        for k in open_keys:
            qa.tap(k, settle=.6)
        st = qa.state()
        qa.tap('p', settle=.5)
        ok(not S.show()['photo']['active'], f'P refused while the {what} is open ({st})', S.show()['photo']['active'])
        for k in close_keys:
            qa.tap(k, settle=.6)
        if qa.state() != 'Play':
            qa.tap('Escape', settle=.6)
    opened, _ = open_dialogue('Mira', 'basic_general', (8.0, 15.8))
    qa.tap('p', settle=.5)
    ok(opened and not S.show()['photo']['active'], 'P refused in dialogue', S.show()['photo']['active'])
    qa.tap('Escape', settle=.8)
    # F8 developer time menu closes photo mode
    qa.tap('p', settle=.5)
    qa.tap('F8', settle=.6)
    ok(not S.show()['photo']['active'], 'F8 (developer time menu) closes photo mode', {'photo': S.show()['photo']['active'], 'state': qa.state(), 'timeScale': S.show()['timeScale']})
    qa.tap('F8', settle=.6)
    if qa.state() != 'Play':
        qa.tap('Escape', settle=.6)

    # ---- container home: photo mode inside, out through the door, first person held again
    qa.goto('home_inside'); qa.view('follow'); time.sleep(1.2)
    fp_in = S.snap()['camera']['firstPerson']
    note('first person inside the home', fp_in)
    qa.face(28.88, -38.0); time.sleep(.3)
    qa.tap('p', settle=.6)
    ok(S.show()['photo']['active'], 'photo mode opens inside the container home')
    if fp_in:
        ok(S.show()['photo']['playerVisible'] is False, 'opened from first person, the colonist starts hidden (camera is inside the head)', S.show()['photo'])
    cap('photo-mode-home-inside')
    p0 = S.snap()['camera']['position']
    qa.hold('w', 6)
    p1 = S.snap()['camera']['position']
    note('photo camera through the home door', {'from': p0, 'to': p1})
    ok(p1[2] > -38.6, 'photo camera flies out through the home door', p1)
    cap('photo-mode-home-door')
    qa.tap('p', settle=.8)
    ok(S.snap()['camera']['firstPerson'] == fp_in, 'first person held again inside the home after photo mode', S.snap()['camera']['firstPerson'])


S.run(body)
