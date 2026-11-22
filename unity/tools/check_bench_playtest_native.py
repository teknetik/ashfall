#!/usr/bin/env python3
"""Carl's Steady Hands playtest of 22 Nov 2026, each note repeated in the built player with real X input.

  A  the depot cleared with real fire: Ossa's radio line, her marker, her talk, then Brann's marker
  B  a copy of Carl's own save: his half-finished job resumes (the real save is only read)
  C  a fresh job: the cell dropped beside the pad, a part over the mat, A / E, the camera pushed as far as it goes,
     V and G, the crack by circling, the mallet on the punch and on the bent pin, the vise opened the wrong way,
     the vise wound far too tight

  ~/.local/state/ward-programme/steady-hands-20261120/native_check.sh playtest22 unity/tools/check_bench_playtest_native.py \
      ATHEN_EXE=<build>/AthenHill.x86_64 ATHEN_OUT=<folder>
"""
import json
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_steady_hands_bench as B  # noqa: E402
import showcase_qa as S  # noqa: E402
from showcase_qa import cap, note, ok, qa  # noqa: E402


def texts():
    return [e['text'] for e in qa.ui()['elements'] if e.get('visible') and e.get('text')]


def depot_save(folder):
    B.real_save(folder)
    path = folder / 'ward-save.json'
    s = json.loads(path.read_text())
    s['bermsStep'] = 'Depot'
    s['crafting']['known'] = []
    s['orders'] = {'index': -1, 'id': '', 'testFired': [], 'reported': []}
    path.write_text(json.dumps(s, indent=1))


def marker(words, towards):
    for _ in range(8):
        qa.face(*towards)
        qa.pitch(6)
        time.sleep(.6)
        found = [t for t in texts() if words in t and len(t) < 90]
        if found:
            return found
    return []


def hand_off():
    save = S.OUT / 'save-a'
    depot_save(save)
    S.launch(run='a', save=save)
    S.start()
    S.time_set(13)
    qa.view('follow')
    qa.tap('2', settle=.6)
    qa.goto('depot_approach')
    time.sleep(.5)
    qa.fight(until=lambda s: s['combat']['step'] == 'Complete', seconds=240, center=(-80.6, -36.2), leash=16, regroup='depot_approach')
    if not ok(qa.snap()['combat']['step'] == 'Complete', 'A: depot cleared with real fire'):
        return
    time.sleep(1.2)
    seen = texts()
    line = next((t for t in seen if t.startswith('Clean work')), '')
    ok('back to me at the post' in line, 'A: the radio sends the player back to Ossa', line)
    ok('Brann' not in line, 'A: the radio does not send the player to Brann', line)
    cap('a1-radio')
    ok(qa.craft().get('orderStage') == 'Identify', 'A: the order waits for Ossa', qa.craft().get('orderStage'))
    ok('Ossa' in (qa.craft().get('objective') or ''), 'A: Field Notes name Ossa', qa.craft().get('objective'))
    qa.goto('checkpoint_ossa')
    time.sleep(.6)
    ossa = qa.pos()
    qa.goto('checkpoint_approach')
    time.sleep(.6)
    ok(marker('WARDEN OSSA', (ossa[0], ossa[2])), 'A: the marker points at Warden Ossa')
    cap('a2-marker')
    qa.goto('checkpoint_ossa')
    time.sleep(.8)
    qa.tap('e', settle=1.0)
    i = S.snap()['interaction']
    ok(i.get('node') == 'servo', 'A: Ossa talks about the salvage', i.get('node'))
    qa.activate('choice0')
    time.sleep(.9)
    i = S.snap()['interaction']
    said = next((t for t in texts() if 'Brann at Salvage' in t), '')
    ok(i.get('node') == 'servo_look' and said, 'A: then she sends the player to Brann', said)
    cap('a3-ossa')
    qa.tap('Escape', settle=.8)
    ok(qa.craft().get('orderStage') == 'Report', 'A: the next step is Brann', qa.craft().get('orderStage'))
    ok('Brann' in (qa.craft().get('objective') or ''), 'A: Field Notes name Brann', qa.craft().get('objective'))
    S.stop()


def carls_save():
    save = S.carl_save_copy(S.OUT / 'save-b')
    S.launch(run='b', save=save)
    S.start()
    qa.goto('salvage_bench')
    time.sleep(.7)
    qa.tap('e', settle=1.5)
    S.wait_for(lambda: B.asm().get('open'), 10, what='bench open')
    a = B.settled(8)
    ok(a.get('open') and a.get('next'), "B: Carl's job resumes on this build", {'stage': a.get('stage'), 'next': a.get('next')})
    cap('b-resumed', layout=False)
    S.stop()


def reach(action_id):
    for _ in range(90):
        a = B.settled()
        now = a.get('next')
        if now == action_id:
            return B.action(a, now)
        act = B.action(a, now)
        if not act:
            break
        B.free_hand(act)
        if not B.take_tool(act):
            break
        if not B.VERBS[act['verb']](B.action(B.settled(), now) or act):
            note('could not do ' + now)
            break
    ok(False, 'C: reached ' + action_id, B.asm().get('next'))
    return None


def current(action_id):
    a = B.settled()
    return a, B.action(a, action_id)


def drop_beside(action_id, dx, dy, what):
    act = reach(action_id)
    if not act:
        return
    B.free_hand(act)
    if not ok(B.carry(act), 'C: picked up for ' + what):
        return
    a, now = current(action_id)
    if now:
        x, y = B.px(now['at'], a)
        B.glide((x + dx * 1.6, y + dy * 1.6), (x + dx, y + dy))
        time.sleep(.5)
        qa.button(1, False)
        time.sleep(.5)
    ok(B.done(action_id), 'C: ' + what)
    cap('c-' + action_id.replace(':', '_'), layout=False)


def camera():
    return B.asm().get('camera') or {}


def view_checks():
    qa.focus(center=False)
    qa.key('a', True); time.sleep(.6); qa.key('a', False); time.sleep(.6)
    left = camera().get('side', 0)
    ok(left < -.2, 'C: A steps left along the bench', left)
    cap('c-step-left', layout=False)
    qa.key('e', True); time.sleep(1.2); qa.key('e', False); time.sleep(.6)
    right = camera().get('side', 0)
    ok(right > .15, 'C: E steps right along the bench', right)
    cap('c-step-right', layout=False)

    middle = (960, 540)
    for dx, dy in ((700, 350), (-700, -350)):
        B.move(middle); time.sleep(.1)
        qa.button(3, True); time.sleep(.35)
        B.glide(middle, (middle[0] + dx, middle[1] + dy))
        qa.button(3, False); time.sleep(.2)
        B.wheel(8); time.sleep(1.2)
        a = B.asm()
        act = B.action(a, a.get('next')) or {}
        at = act.get('toolAt') if act.get('tool') and not act.get('toolInHand') and act.get('toolAt') else act.get('at')
        x, y = B.px(at)
        snap = S.snap()
        ok(0 <= x <= snap.get('width', 1920) and 0 <= y <= snap.get('height', 1080), 'C: the work stays in the picture with the view pushed to its limit', [x, y])
        cap('c-view-pushed-%d' % (dx > 0), layout=False)

    before = camera().get('viseYaw', 0)
    B.move(middle); time.sleep(.2)
    qa.key('v', True); time.sleep(.15)
    B.glide(middle, (middle[0] + 220, middle[1]))
    qa.key('v', False); time.sleep(.4)
    turned = camera().get('viseYaw', 0)
    ok(abs(turned - before) > 25, 'C: V and the mouse turn the vise', [before, turned])
    cap('c-vise-turned', layout=False)
    B.key_tap('g')
    time.sleep(1.6)
    c = camera()
    ok(abs(c.get('viseYaw', 9)) < 1 and abs(c.get('side', 9)) < .03 and c.get('zoom', 9) < .03, 'C: G squares up the view and the vise', c)


def circle(action_id, way, turns, what, picture=None):
    act = reach(action_id)
    if not act:
        return
    B.free_hand(act)
    a, now = current(action_id)
    cx, cy = B.px(now.get('partAt') or now['at'], a)
    B.move((cx, cy)); time.sleep(.15)
    qa.button(1, True); time.sleep(.08)
    for n in range(int(turns * 26)):
        angle = way * n * 2 * math.pi / 26
        B.move((cx + 55 * math.cos(angle), cy + 55 * math.sin(angle)))
        time.sleep(.025)
        if n % 6 == 5:
            if picture and n == 5:
                cap(picture, layout=False)
            if B.done(action_id):
                break
    qa.button(1, False)
    time.sleep(.4)
    ok(B.done(action_id), 'C: ' + what)


def strike(action_id, release_at, picture):
    a, now = current(action_id)
    if not now:
        return
    B.move(B.px(now['at'], a)); time.sleep(.15)
    qa.button(1, True)
    end = time.time() + 4
    pictured = False
    while time.time() < end:
        v = (B.asm().get('verb') or {}).get('value') or 0
        if not pictured and v >= .2:
            cap(picture, layout=False); pictured = True
        if v >= release_at:
            break
        time.sleep(.02)
    qa.button(1, False)
    time.sleep(.5)
    cap(picture + '-landed', layout=False)


def bench():
    S.launch(run='c')
    S.start(continue_game=False)
    qa.goto('bench_steady_hands')
    time.sleep(1)
    qa.cmd('dev.assembly.open', force=True, fresh=True)
    S.wait_for(lambda: B.asm().get('open'), 10, what='bench open')
    drop_beside('s0.cell:cell', 95, 25, 'the cell drops in from beside the pad')
    if not reach('s1.bind:snip_a'):
        return
    view_checks()
    drop_beside('s1.scales:left', 120, -20, 'a scale drops into place from over the mat')
    act = reach('s1.pin:taps')
    if act:
        B.free_hand(act)
        B.take_tool(act)
        for n in range(3):
            if B.done('s1.pin:taps'):
                break
            strike('s1.pin:taps', .92, 'c-mallet-on-punch-%d' % n)   # too hard, to bend the pin
        ok(B.done('s1.pin:taps'), 'C: the mallet drives the pin out along the punch')
    act = reach('s1.pin.r:straighten')
    if act:
        B.free_hand(act)
        B.take_tool(act)
        for n in range(2):
            if B.done('s1.pin.r:straighten'):
                break
            strike('s1.pin.r:straighten', .5, 'c-mallet-on-anvil-%d' % n)
        ok(B.done('s1.pin.r:straighten'), 'C: the bent pin is straightened on the anvil')
    circle('s1.inspect:find', 1, 2, 'circling the vise finds the crack and the job moves on', 'c-crack')
    S.wait_for(lambda: not camera().get('squaring'), 4, what='vise square')
    cap('c-crack-found', layout=False)
    circle('s2.swap:open', 1, 6, 'the vise opens though circled clockwise')
    circle('s2.swap:snug', 1, 7, 'winding the vise far too tight still finishes the step')


def body():
    for part in (hand_off, carls_save, bench):
        try:
            part()
        except Exception as e:  # noqa: BLE001
            ok(False, part.__name__ + ' ran without error', repr(e))
            cap('error-' + part.__name__, layout=False)
        if part is not bench:
            S.stop()


S.run(body)
