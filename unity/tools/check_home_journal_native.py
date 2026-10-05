"""Native real-input check of the 5 Oct 2026 controls, hotbar, journal and container home (art/ward_home_20261005).

Continues a prepared v3 save (primer complete, Ossa's first field order running, 120 credits, salvage, a medkit and a
trauma kit; pistol in the secondary slot), then with real keyboard and mouse input:

  1. cursor: in play the cursor is locked and hidden; Tab frees it and Esc locks it again; Left Alt frees it (mouse look
     itself, with a real relative mouse: check_mouse_look_native.py).
  2. hotbar: 2 shows the scrap pistol; in the field pack, dragging the trauma kit tile onto HOTBAR strip cell 0 assigns
     it, and selecting the medkit and pressing 7 assigns it to 7; back in play, hotbar 0 uses the trauma kit on a wound.
  3. journal: J opens it; the missions are listed (primer complete, field order 1 and A Roof in Ward active); selecting
     the home mission and pressing T tracks it; Field Notes shows its title and the compass carries the tracked marker.
  4. lease: Linn on the hill offers the housing roll; the lease takes 40 credits and records home_leased.
  5. home: the door swings open as the player arrives; walking in holds the camera in first person; E at the locker opens
     the stash window; Store all salvage moves the salvage; Take 1 brings one back; E at the bunk opens the rest window;
     Sleep until morning sets 06:30 and restores vitality.
  6. LMB fire: in the Outer Berms, 2 draws the pistol and the left mouse button fires it.
  7. save: quit and Continue: the colonist wakes at the bunk; the locker, the hotbar and the tracked mission are kept.
Captures the review cameras cam_home_* at 13:00 and 20:30 and first-person views inside.

  uv run --offline --with python-xlib --with pillow python unity/tools/check_home_journal_native.py OUT
"""
import json, math, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'unity/evidence/gameplay-v2/20260930-reqa2'))
import qa  # noqa: E402

out = Path(sys.argv[1]).resolve(); out.mkdir(parents=True, exist_ok=True)
save = out / 'save'; save.mkdir(exist_ok=True)
SALVAGE = [('scrap_alloy', 4), ('copper_filament', 3), ('droid_servo_damaged', 2), ('scrap_coil', 2)]
(save / 'ward-save.json').write_text(json.dumps({
    'version': 3, 'savedUtc': '2026-10-05T04:00:00Z', 'build': 'qa', 'credits': 120, 'purchases': 0, 'sales': 0,
    'items': [{'itemId': i, 'quantity': q} for i, q in SALVAGE] + [{'itemId': 'medkit', 'quantity': 1}, {'itemId': 'trauma_kit', 'quantity': 1},
                                                                     {'itemId': 'field_toolkit', 'quantity': 1}],
    'crafting': {'known': [], 'crafted': [], 'crafts': 0, 'fitted': []},
    'bermsStep': 'Complete', 'hasPistol': True, 'orders': {'index': 0, 'id': 'order_steady_hands', 'testFired': [], 'reported': []},
    'city': {'visitedHill': True, 'boughtFlask': True, 'soldScrap': True, 'linked': True,
             'spoken': ['npc_linn', 'npc_mira', 'npc_torr', 'npc_vex'], 'selectedDestination': '', 'flags': []},
    'character': {'version': 2, 'level': 2, 'experience': 0, 'attributePoints': 0, 'skillPoints': 0,
                  'equipped': [{'slot': 'storage', 'itemId': 'field_backpack'}, {'slot': 'armour_chest', 'itemId': 'field_vest'},
                               {'slot': 'armour_feet', 'itemId': 'field_boots'}, {'slot': 'secondary', 'itemId': 'scrap_pistol'}],
                  'modifications': []},
}, indent=1))

checks = []; report = {'checks': checks}


def ok(cond, what, detail=None):
    checks.append({'check': what, 'passed': bool(cond), 'detail': detail})
    print(('PASS ' if cond else 'FAIL ') + what + ('' if detail is None else ' :: ' + json.dumps(detail, default=str)[:300]), flush=True)
    return cond


def snap():
    return qa.snap()


def home():
    return snap().get('home') or {}


def journal():
    return snap().get('journal') or {}


def hotbar():
    return {e['slot']: e for e in (snap().get('hotbar') or [])}


def cursor():
    return snap().get('cursor') or {}


def centre(layout, name):
    e = qa.el(layout, name)
    if not e or not e.get('visible'):
        raise AssertionError(f'{name} is not visible')
    x, y, w, h = e['bounds']
    return x + w / 2, y + h / 2


def move(x, y):
    from Xlib import X
    from Xlib.ext import xtest
    d = qa._display()
    o = d.screen().root.translate_coords(qa.window(), 0, 0)
    xtest.fake_input(d, X.MotionNotify, x=o.x + int(x), y=o.y + int(y))
    d.sync(); time.sleep(.12)


def drag(start, end):
    qa.focus(center=False); move(*start); qa.button(1, True)
    try:
        time.sleep(.2); move(start[0] + 12, start[1])
        for step in range(1, 13):
            move(start[0] + (end[0] - start[0]) * step / 12, start[1] + (end[1] - start[1]) * step / 12)
    finally:
        qa.button(1, False)
    time.sleep(.5)


def goto(landmark):
    qa.goto(landmark); time.sleep(.6)
    return qa.pos()


def recentre():
    """Re-activate the window after using the mouse in a window. qa.focus() moves the XTEST pointer only while the game's
    cursor is free (a move while it is locked arrives as one large mouse delta under Hyprland's pointer lock)."""
    qa.focus(center=True); time.sleep(.3)


qa.launch(out / 'run', save_dir=save)
try:
    qa.wait_menu(); qa.focus(); qa.tap('Return')
    qa.wait(lambda: qa.state() == 'Play', 40, what='Play after Continue')
    qa.release_all()
    qa.cmd('timeSet', hour=13); qa.cmd('timePause', paused=True)

    # ---- 1. mouse look
    qa.focus(); time.sleep(.5)
    c = cursor(); ok(c.get('lockState') == 'Locked' and not c.get('visible'), 'in play the cursor is locked and hidden', c)
    # (mouse look with a real relative mouse: unity/tools/check_mouse_look_native.py)
    qa.tap('Tab', settle=.6); c = cursor()
    ok(qa.state() == 'Inventory' and c.get('lockState') == 'None' and c.get('visible'), 'opening the field pack frees the cursor', c)
    qa.capture('pack-with-hotbar-strip')

    # ---- 2. hotbar: drag the trauma kit to 0, press 7 on the medkit
    lay = qa.ui()
    ok(qa.el(lay, 'pack-hotbar') is not None and all(qa.el(lay, f'packbar-slot{i}') for i in range(1, 11)), 'the field pack shows the HOTBAR strip with ten cells')
    drag(centre(lay, 'inv-trauma_kit'), centre(lay, 'packbar-slot10'))
    ok(hotbar().get(10, {}).get('item') == 'trauma_kit', 'dragging the trauma kit onto strip cell 0 puts it on hotbar 0', hotbar().get(10))
    lay = qa.ui(); qa.click_at(*centre(lay, 'inv-medkit')); time.sleep(.3)
    qa.tap('7', settle=.5)
    hb = hotbar(); ok(hb.get(7, {}).get('item') == 'medkit' and hb.get(3, {}).get('item') is None, 'selecting the medkit and pressing 7 moves it to hotbar 7', {k: v.get('item') for k, v in hb.items()})
    drag(centre(qa.ui(), 'inv-scrap_alloy'), centre(qa.ui(), 'packbar-slot5'))
    ok(hotbar().get(5, {}).get('item') is None, 'salvage dropped on the strip is refused', {'notice': snap()['session']['notice']})
    qa.capture('pack-hotbar-assigned')
    qa.tap('Escape', settle=.6); recentre(); c = cursor()
    ok(qa.state() == 'Play' and c.get('lockState') == 'Locked', 'closing the pack locks the cursor again', c)
    lay = qa.ui()
    s2 = qa.el(lay, 'slot2'); s10 = qa.el(lay, 'slot10')
    ok(s2 and 'empty-slot' not in s2['classes'] and s10 and 'empty-slot' not in s10['classes'], 'the HUD hotbar shows the pistol on 2 and the trauma kit on 0', {'slot2': s2 and s2['classes'], 'slot10': s10 and s10['classes']})
    qa.key('Alt_L', True); time.sleep(.4); c = cursor(); qa.key('Alt_L', False); time.sleep(.4); recentre()
    ok(c.get('lockState') == 'None' and c.get('freed'), 'holding Left Alt frees the cursor in play', c)
    h0 = snap()['combat']['health']; qa.cmd('damage', amount=45); time.sleep(.3); h1 = snap()['combat']['health']
    qa.tap('0', settle=.6); h2 = snap()['combat']['health']
    ok(h1 < h0 - 20 and h2 >= h0 - .5 and (qa.qty('trauma_kit') or 0) == 0, 'hotbar 0 uses the trauma kit on a wound (healed to full)', {'before': h0, 'wounded': h1, 'healed': h2, 'notice': snap()['session']['notice']})
    qa.capture('hud-hotbar', layout=False)

    # ---- 3. journal
    qa.tap('j', settle=.7)
    ok(qa.state() == 'Journal', 'J opens the journal')
    j = journal(); ids = {m['id']: m for m in j.get('missions', [])}
    ok(ids.get('primer', {}).get('status') == 'Complete' and ids.get('order:order_steady_hands', {}).get('status') == 'Active' and ids.get('home', {}).get('status') == 'Active',
       'the journal lists the primer (complete), field order 1 and A Roof in Ward (active)', {k: v['status'] for k, v in ids.items()})
    ok(j.get('tracked') == 'order:order_steady_hands', 'the running field order is tracked by default', j.get('tracked'))
    qa.capture('journal-order')
    lay = qa.ui(); qa.click_at(*centre(lay, 'journal-mission-home')); time.sleep(.4)
    qa.capture('journal-home')
    qa.tap('t', settle=.6)
    ok(journal().get('tracked') == 'home', 'T tracks the selected mission', journal().get('tracked'))
    qa.tap('j', settle=.6); recentre(); ok(qa.state() == 'Play', 'J closes the journal')
    lay = qa.ui(); title = qa.el(lay, 'objective-title')
    ok(title and 'ROOF' in (title.get('text') or ''), 'Field Notes shows the tracked mission', title and title.get('text'))
    tracked_marker = [e for e in lay['elements'] if e.get('name') == 'compass-tracked' and e.get('visible')]
    ok(bool(tracked_marker) and journal().get('trackedTarget'), 'the compass carries the tracked marker (pointing at Linn before the lease)', {'target': journal().get('trackedTarget'), 'label': journal().get('trackedLabel')})
    qa.capture('compass-tracked', layout=False)

    # ---- 4. lease from Linn
    goto('oa_hill'); qa.tap('e', settle=.8)
    ok(qa.state() == 'Dialogue' and qa.snap()['interaction']['npc'] == 'Linn', 'Linn on the hill')
    choices = qa.snap()['interaction']['choices'] or []
    ok(any('stay' in c for c in choices), 'Linn offers the housing roll after the primer', choices)
    qa.activate('choice%d' % next(i for i, c in enumerate(choices) if 'stay' in c)); time.sleep(.5)
    qa.capture('linn-housing')
    c0 = snap()['session']['credits']
    choices = qa.snap()['interaction']['choices'] or []
    qa.activate('choice%d' % next(i for i, c in enumerate(choices) if 'lease' in c)); time.sleep(.6)
    ok(home().get('leased') and snap()['session']['credits'] == c0 - 40, 'the lease takes 40 credits and the home is leased', {'credits': snap()['session']['credits'], 'home': home()})
    qa.tap('Escape', settle=.6); recentre()
    ok(journal().get('trackedLabel') == 'HOME LOCKER', 'the tracked marker moves to the home locker', journal().get('trackedLabel'))

    # ---- 5. the home
    goto('home_door'); time.sleep(1.0)
    ok(home().get('doorOpen', 0) > .9 and not home().get('doorLocked'), 'the door swings open as the tenant arrives', home())
    qa.view('follow'); qa.capture('home-door-open', layout=False)
    goto('home_inside'); inside = qa.pos(); goto('home_door'); time.sleep(.6)
    recentre(); qa.pitch(12); qa.face(inside[0], inside[2]); time.sleep(.3)
    qa.walk_to(inside[0], inside[2], tol=.5)
    h = home(); ok(qa.dist_xz(qa.pos(), inside) < .7 and h.get('insideZone') and h.get('confined') and snap()['camera']['firstPerson'], 'walked in through the door; the camera holds first person inside', {'pos': qa.pos(), 'home': h, 'camera': snap()['camera']})
    qa.capture('home-inside-fp', layout=False)
    goto('home_locker'); qa.tap('e', settle=.8)
    ok(qa.state() == 'Stash', 'E at the locker opens the stash window')
    qa.capture('stash-open')
    lay = qa.ui(); qa.click_at(*centre(lay, 'stash-store-salvage')); time.sleep(.6)
    st = {s['item']: s['quantity'] for s in (home().get('stash') or [])}
    ok(all(st.get(i) == q for i, q in SALVAGE) and (qa.qty('field_toolkit') or 0) == 1 and (qa.qty('medkit') or 0) == 1,
       'Store all salvage moves the salvage and keeps the toolkit and medkit in the pack', {'stash': st, 'notice': snap()['session']['notice']})
    lay = qa.ui(); qa.click_at(*centre(lay, 'stash-locker-scrap_alloy')); time.sleep(.3)
    lay = qa.ui(); qa.click_at(*centre(lay, 'stash-take-one')); time.sleep(.5)
    st = {s['item']: s['quantity'] for s in (home().get('stash') or [])}
    ok(st.get('scrap_alloy') == 3 and (qa.qty('scrap_alloy') or 0) == 1, 'Take 1 brings one scrap alloy back to the pack', {'stash': st})
    qa.capture('stash-moved')
    qa.tap('Escape', settle=.6); recentre()
    ok(home().get('stored') and journal().get('tracked') != 'home', 'storing salvage completes A Roof in Ward and tracking moves on', {'home': home(), 'tracked': journal().get('tracked')})
    qa.cmd('damage', amount=30); time.sleep(.3)
    goto('home_bunk'); qa.tap('e', settle=.8)
    ok(qa.state() == 'Rest', 'E at the bunk opens the rest window')
    qa.capture('rest-open')
    lay = qa.ui(); qa.click_at(*centre(lay, 'rest-morning')); time.sleep(1.0); recentre()
    qa.cmd('timeState'); hour = qa.read('time-state.json').get('hour')
    cb = snap()['combat']
    ok(qa.state() == 'Play' and home().get('rested') and cb['health'] >= 99 and (hour is None or abs(hour - 6.5) < .2), 'sleeping until morning restores vitality, sets 06:30 and records the rest', {'health': cb['health'], 'hour': hour, 'home': home()})
    qa.capture('woke-at-bunk', layout=False)
    report['wake'] = qa.pos()

    # ---- 6. LMB fire in the Berms
    goto('checkpoint_range_reset'); qa.view('follow'); time.sleep(.5)
    qa.tap('2', settle=.6); cb = snap()['combat']
    ok(cb['Armed'] and cb.get('weaponId') == 'weapon_scrap_pistol', '2 draws the scrap pistol in the Berms', {'armed': cb['Armed'], 'weapon': cb.get('weaponId')})
    shots = cb['ShotsFired']; qa.focus(); qa.button(1, True); time.sleep(.08); qa.button(1, False); time.sleep(.5)
    ok(snap()['combat']['ShotsFired'] == shots + 1, 'the left mouse button fires without aiming', {'before': shots, 'after': snap()['combat']['ShotsFired']})
    qa.tap('2', settle=.5)

    # ---- review views (13:00 and 20:30)
    cams = ['cam_home_street', 'cam_home_door', 'cam_home_inside_bunk', 'cam_home_inside_locker', 'cam_home_locker', 'cam_home_bunk']
    for cam in cams:
        try:
            qa.view(cam); time.sleep(.5); qa.capture(cam + '-h13', layout=False)
        except Exception as e:  # noqa: BLE001
            ok(False, 'review camera ' + cam, str(e))
    qa.cmd('timeSet', hour=20.5); time.sleep(1.5)
    for cam in cams[:4]:
        try:
            qa.view(cam); time.sleep(.5); qa.capture(cam + '-h20.5', layout=False)
        except Exception:  # noqa: BLE001
            pass
    qa.view('follow')
    report['errors'] = qa.log_errors()
    ok(not report['errors'], 'no exceptions in Player.log', report['errors'][:3])
finally:
    print('stop:', qa.stop())

saved = json.loads((save / 'ward-save.json').read_text())
report['saved'] = {k: saved.get(k) for k in ('version', 'hotbar', 'stash', 'journal')}
ok(saved.get('version') == 4 and {'slot': 10, 'itemId': 'trauma_kit'} in (saved.get('hotbar') or []) and any(s['itemId'] == 'copper_filament' for s in saved.get('stash') or []),
   'the save (v4) keeps the hotbar and the locker', report['saved'])

# ---- 7. Continue wakes at the bunk with everything kept
qa.launch(out / 'run2', save_dir=save)
try:
    qa.wait_menu(); qa.focus(); qa.tap('Return')
    qa.wait(lambda: qa.state() == 'Play', 40, what='Play after the second Continue')
    time.sleep(1.0)
    p = qa.pos()
    ok(report.get('wake') and qa.dist_xz(p, report['wake']) < 1.0 and 'container home' in (snap()['session']['notice'] or ''), 'Continue wakes the colonist at the bunk', {'pos': p, 'wake': report.get('wake'), 'notice': snap()['session']['notice']})
    st = {s['item']: s['quantity'] for s in (home().get('stash') or [])}
    ok(st.get('copper_filament') == 3 and hotbar().get(10, {}).get('item') == 'trauma_kit', 'the locker and the hotbar survive the restart', {'stash': st, 'hotbar': {k: v.get('item') for k, v in hotbar().items()}})
    qa.capture('continue-at-home', layout=False)
    report['errors2'] = qa.log_errors()
    ok(not report['errors2'], 'no exceptions in Player.log after Continue', report['errors2'][:3])
finally:
    print('stop:', qa.stop())

report['passed'] = all(c['passed'] for c in checks)
(out / 'report.json').write_text(json.dumps(report, indent=1, default=str))
print('PASSED' if report['passed'] else 'FAILED', sum(c['passed'] for c in checks), '/', len(checks))
sys.exit(0 if report['passed'] else 1)
