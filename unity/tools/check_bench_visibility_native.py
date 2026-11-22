#!/usr/bin/env python3
"""Carl's second Steady Hands playtest of 22 Nov 2026, each note in the built player with real X input.

  A  a copy of his save as it was when he reported (on the servo's screws): the bit says how to change it, and the
     on-screen button, R and the middle button each change it
  B  a fresh job: the salvage beside the open roll, a sheet put down on the roll, the tray and the work mat, both sheets in
     the tray, then the punch and the ringed pin, set with one click

Run it against any build (the one before the fix fails it):

  ~/.local/state/ward-programme/steady-hands-20261120/native_check.sh bench-vis unity/tools/check_bench_visibility_native.py \
      ATHEN_EXE=<build>/AthenHill.x86_64 ATHEN_OUT=<folder>
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_steady_hands_bench as B  # noqa: E402
import showcase_qa as S  # noqa: E402
from showcase_qa import cap, note, ok, qa  # noqa: E402

SAVE = S.ROOT if hasattr(S, 'ROOT') else Path(__file__).resolve().parents[2]
SAVE = SAVE / 'unity/evidence/bench_visibility/20261122/save-at-report/ward-save.json'


def element(name):
    for e in qa.ui()['elements']:
        if e.get('name') == name and e.get('visible'):
            return e


def panel_px(e):
    ui = qa.ui()
    x, y, w, h = e['bounds']
    s = S.snap()
    return (x + w / 2) * s['width'] / ui['width'], (y + h / 2) * s['height'] / ui['height']


def mode():
    return (B.held() or {}).get('toolMode')


def bit():
    folder = S.OUT / 'save-a'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'ward-save.json').write_bytes(SAVE.read_bytes())
    S.launch(run='a', save=folder)
    S.start()
    qa.goto('salvage_bench')
    time.sleep(.7)
    qa.tap('e', settle=1.5)
    S.wait_for(lambda: B.asm().get('open'), 10, what='bench open')
    a = B.settled(8)
    if not ok(a.get('next') == 's2.screws:a_turn', "A: Carl's job resumes on the servo's screws", a.get('next')):
        return
    act = B.action(a, a['next'])
    B.click(B.px(act['toolAt'], a))
    time.sleep(1.4)
    a = B.settled()
    ok(mode() == 'slot', 'A: the screwdriver comes up with the slotted bit', mode())
    line = a.get('actionLine') or ''
    ok('press R' in line and 'cross' in line, 'A: the line says how to change the bit', line)
    e = element('assembly-bit-do')
    ok(e and 'CROSS' in (e.get('text') or ''), 'A: the bit button is on screen', e and e.get('text'))
    cap('a1-wrong-bit', layout=False)
    if e:
        B.click(panel_px(e))
        time.sleep(.5)
        ok(mode() == 'cross', 'A: clicking the button fits the cross bit', mode())
        ok((B.held() or {}).get('tool') == 'tools.screwdriver', 'A: the screwdriver stays in the hand', B.held())
        cap('a2-fitted', layout=False)
        time.sleep(2.2)
        ok(not element('assembly-bit-do'), 'A: the button goes once the bit is right')
    was = mode()
    qa.button(2, True); time.sleep(.07); qa.button(2, False); time.sleep(.6)
    ok(mode() != was, 'A: the middle button changes it', [was, mode()])
    was = mode()
    B.key_tap('r'); time.sleep(.6)
    ok(mode() != was, 'A: R changes it', [was, mode()])
    if mode() != 'cross':
        B.key_tap('r'); time.sleep(.6)
    a = B.settled()
    act = B.action(a, a['next'])
    ok(B.turn(act), "A: the servo's first screw comes out", (a.get('actionLine'), mode()))
    cap('a3-screw', layout=False)


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
    ok(False, 'B: reached ' + action_id, B.asm().get('next'))


def part(a, part_id):
    return next((p for p in a.get('parts') or [] if p['id'] == part_id), {})


def put_down(shot, over, dy, name):
    """Sheet A picked up and clicked down over another thing, as a player tidying the bench does."""
    qa.cmd('dev.assembly.shot', shot='wide'); time.sleep(1)
    a = B.settled()
    p = part(a, 'materials.sheet_a')
    B.click(B.px(p['at'], a))
    time.sleep(.5)
    sheet = (B.held() or {}).get('part') or ''   # the two lie in a pile on the build before the fix: either will do
    if not ok(sheet.startswith('materials.sheet_'), 'B: picked a sheet up for ' + name, B.held()):
        return
    to = B.px(part(a, over)['at'], a) if isinstance(over, str) else over
    to = (to[0], to[1] + dy)
    B.glide(B.px(p['at'], a), to)
    time.sleep(.5)
    B.click(to)
    time.sleep(.7)
    a = B.settled()
    ok(part(a, sheet).get('place') == 'loose', 'B: the sheet is put down on ' + name, part(a, sheet))
    cap('b-putdown-' + name.replace(' ', '-'), layout=False)
    qa.cmd('dev.assembly.shot', shot=shot); time.sleep(1.2)
    cap('b-putdown-' + name.replace(' ', '-') + '-close', layout=False)


def open_fresh(run):
    S.launch(run=run)
    S.start(continue_game=False)
    qa.goto('bench_steady_hands')
    time.sleep(1)
    qa.cmd('dev.assembly.open', force=True, fresh=True)
    S.wait_for(lambda: B.asm().get('open'), 10, what='bench open')


def scrap():
    open_fresh('b')
    if not reach('s0.salvage:servo'):
        return
    qa.cmd('dev.assembly.shot', shot='wide'); time.sleep(1.2)
    cap('b1-open-roll', layout=False)
    put_down('roll', 'tools.punch', -120, 'the roll')
    put_down('roll', 'tools.punch', 40, 'the pockets')
    put_down('work', (960, 470), 0, 'the work mat')


def tray_and_pin():
    open_fresh('c')
    if not reach('s0.card_before:pulses'):
        return
    a = B.settled()
    for i, seat in (('materials.sheet_a', 'fixtures.tray/seat_alloy'), ('materials.sheet_b', 'fixtures.tray/seat_alloy#b')):
        ok(part(a, i).get('place') == seat, 'B: ' + i + ' is in the tray', part(a, i))
    qa.cmd('dev.assembly.shot', shot='tray'); time.sleep(1.4)
    cap('b2-tray', layout=False)
    qa.cmd('dev.assembly.shot', shot='auto')
    act = reach('s1.pin:punch')
    if not act:
        return
    B.free_hand(act)
    time.sleep(1.4)
    cap('b3-take-punch', layout=False)
    e = element('assembly-target-label')
    ok(e and 'PUNCH' in (e.get('text') or ''), 'B: the punch is ringed in the roll', e and e.get('text'))
    a = B.settled(); act = B.action(a, 's1.pin:punch')
    B.click(B.px(act['partAt'], a))
    time.sleep(1.6)
    a = B.settled()
    ok((B.held() or {}).get('tool') == 'tools.punch', 'B: the punch is in the hand', B.held())
    line = a.get('actionLine') or ''
    ok('back first' not in line, 'B: the line does not say to put the punch back', line)
    ok((a.get('camera') or {}).get('shot') == 'pin', "B: the camera goes to the pin", (a.get('camera') or {}).get('shot'))
    e = element('assembly-target-label')
    ok(e and 'PIN' in (e.get('text') or ''), 'B: the pin is ringed', e and e.get('text'))
    cap('b4-ringed-pin', layout=False)
    act = B.action(a, 's1.pin:punch')
    B.click(B.px(act['at'], a))
    time.sleep(.9)
    ok(B.done('s1.pin:punch'), 'B: one click on the pin stands the punch on it', B.held())
    time.sleep(1.2)
    cap('b5-take-mallet', layout=False)
    act = B.action(B.settled(), 's1.pin:taps')
    if act and B.take_tool(act):
        time.sleep(1.4)
        cap('b6-strike-here', layout=False)
    act = reach('s1.pin:pull')
    if act:
        B.free_hand(act)
        if B.take_tool(act):
            time.sleep(1.4)
            cap('b7-pull-pin', layout=False)
            ok(B.seat(B.action(B.settled(), 's1.pin:pull') or act), 'B: the pin is pulled with the pliers')


def body():
    for check in (bit, scrap, tray_and_pin):
        try:
            check()
        except Exception as e:  # noqa: BLE001
            ok(False, check.__name__ + ' ran without error', repr(e))
            cap('error-' + check.__name__, layout=False)
        if check is not tray_and_pin:
            S.stop()


S.run(body)
