"""Real-input check of the 2 Oct 2026 rifle / armour / first-contact / pistol-carry work on the native development player.

  ATHEN_RIFLE_EVIDENCE=<dir> [ATHEN_EXE=<player>] DISPLAY=:0 uv run --offline --with python-xlib --with pillow python unity/tools/check_rifle_quest.py

Phase A, new game: the Outer Berms primer with real input (locker, draw, plates, the service-road pair of drones, the
depot nest), checking the first contact spawns beside the gate again and the HUD marker names it. Captures the drawn
pistol at the carry (the 45-degree complaint).
Phase B, Continue on a fixture save at Ossa's "Long Arm" order with the receiver and parts carried: Brann's report line,
fabricating the Field Rifle at his bench, equipping it (inventory drag), drawing it with 8 at the range (held-fire burst,
aim, switch to the pistol and back), then the "Plate Carrier" order: the caravan scavengers, the strongbox, equipping the
carrier and seeing it on the colonist. Fails on any runtime exception in Player.log.

Requires the combined inventory/rifle build: RifleArmourInstall scene bindings and QA landmarks, the re-applied
rifle/plate-carrier catalog and order data, and NativeQa dev.state character diagnostics. Run under the shared Unity
job lock with other Unity/player jobs stopped. Phase B deliberately loads a version-2 save to exercise migration;
its equipped backpack and trained rifle/engineering skills provide room and meet the rifle's requirements.
"""
import json, math, os, shutil, subprocess, sys, time, traceback, uuid
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'unity/evidence/gameplay-v2/20260930-reqa2'))
import qa  # noqa: E402
from check_inventory_redesign import launch as launch_capped_player  # noqa: E402
if os.environ.get('ATHEN_EXE'): qa.EXE = Path(os.environ['ATHEN_EXE'])
OUT = Path(os.environ.get('ATHEN_RIFLE_EVIDENCE', ROOT / 'unity/evidence/rifle-armour/20261002/native-check')).resolve()
OUT.mkdir(parents=True, exist_ok=True)
report = {'passed': False, 'checks': [], 'failures': [], 'captures': [], 'phases': {}, 'players': {}}
_owned_player = None


def launch_player(phase, save):
    """Use the inventory harness's exact-PID launcher and own only this phase's unique scope."""
    global _owned_player
    if _owned_player is not None: raise RuntimeError('A rifle QA player is already owned')
    out = OUT / ('run-' + phase)
    out.mkdir()  # A fresh evidence path also prevents accidentally continuing a previous phase-A save.
    unit = 'ashfall-rifle-qa-' + phase + '-' + uuid.uuid4().hex[:10]
    record = {'unit': unit + '.scope', 'run': str(out / 'run'), 'saveDir': str(save)}
    report['players'][phase] = record
    # Register ownership before launch so its scope is still cleaned up if startup raises.
    _owned_player = {'unit': unit, 'proc': None, 'record': record}
    proc = launch_capped_player(out, save.resolve(), qa.EXE.resolve(), unit)
    _owned_player['proc'] = proc
    record['pid'] = qa.pid()


def stop_player():
    global _owned_player
    owned = _owned_player
    if owned is None: return
    record, unit, proc = owned['record'], owned['unit'] + '.scope', owned['proc']
    try:
        try: record['stop'] = qa.stop(timeout=8)
        except Exception as e: record['stopError'] = str(e)
        try:
            stopped = subprocess.run(['systemctl', '--user', 'stop', unit], capture_output=True, text=True, timeout=15)
            record['scopeStop'] = {'exitCode': stopped.returncode, 'message': stopped.stderr.strip()}
        except Exception as e:
            record['scopeStopError'] = str(e)
            # This unique scope contains only our phase's player; never stop another player or Unity job.
            try: subprocess.run(['systemctl', '--user', 'kill', '--kill-whom=all', unit], capture_output=True, timeout=5)
            except Exception as kill_error: record['scopeKillError'] = str(kill_error)
        if proc is not None:
            try: record['launcherExitCode'] = proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.terminate()
                try: record['launcherExitCode'] = proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill(); record['launcherExitCode'] = proc.wait(timeout=5)
    finally:
        _owned_player = None


def ok(cond, what, detail=None):
    (report['checks'] if cond else report['failures']).append(what if detail is None else {'check': what, 'detail': detail})
    print(('PASS ' if cond else 'FAIL ') + what, '' if detail is None else json.dumps(detail, default=str)[:300], flush=True)
    return cond


def cap(name):
    report['captures'].append(qa.capture(name, layout=False)); return name


def inter(): return qa.snap()['interaction']


def weapon():
    return qa.snap()['combat'].get('weaponId')


def panel_bounds(layout):
    return (qa.el(layout, 'hud') or {}).get('bounds', [0, 0, layout['width'], layout['height']])


def pixels(point, layout):
    """UI Toolkit bounds use reference-panel units, while XTEST uses client pixels."""
    x, y, w, h = panel_bounds(layout)
    return (point[0] - x) * layout['width'] / w, (point[1] - y) * layout['height'] / h


def inside(point, bounds, inset=3):
    x, y = point; bx, by, w, h = bounds
    return bx + inset <= x <= bx + w - inset and by + inset <= y <= by + h - inset


def centre(layout, name):
    e = qa.el(layout, name)
    if not e or not e['visible'] or not e.get('enabled', True): raise AssertionError(name + ' is not available')
    x, y, w, h = e['bounds']; point = (x + w / 2, y + h / 2)
    if not inside(point, panel_bounds(layout)): raise AssertionError(name + ' is outside the visible panel')
    return pixels(point, layout)


def move(x, y):
    from Xlib import X
    from Xlib.ext import xtest
    d = qa._display(); o = d.screen().root.translate_coords(qa.window(), 0, 0)
    xtest.fake_input(d, X.MotionNotify, x=o.x + int(x), y=o.y + int(y)); d.sync(); time.sleep(.12)


def drag(start, end):
    qa.focus(center=False); move(*start); qa.button(1, True)
    try:
        time.sleep(.2); move(start[0] + 12, start[1])
        for step in range(1, 13): move(start[0] + (end[0] - start[0]) * step / 12, start[1] + (end[1] - start[1]) * step / 12)
    finally: qa.button(1, False)
    time.sleep(.5)


def scroll_into_view(name, scroll_name, tries=12):
    for _ in range(tries):
        layout = qa.ui(); e = qa.el(layout, name); sv = qa.el(layout, scroll_name)
        if not e or not e['visible']: raise AssertionError(name + ' is not visible')
        if not sv or not sv['visible']: raise AssertionError(scroll_name + ' is not visible')
        x, y, w, h = e['bounds']; sx, sy, sw, sh = sv['bounds']; point = (x + w / 2, y + h / 2)
        if inside(point, sv['bounds'], 16) and inside(point, panel_bounds(layout)): return layout
        # Anatomy slots are fixed beside the independently scrolling details, never in the inspector's scroll area.
        if scroll_name == 'armour-body-map': raise AssertionError(name + ' is clipped on the fixed armour map')
        qa.focus(center=False); move(*pixels((sx + sw / 2, sy + sh / 2), layout)); b = 5 if point[1] > sy + sh - 16 else 4
        qa.button(b, True); qa.button(b, False); time.sleep(.25)
    raise AssertionError(name + ' did not become reachable in ' + scroll_name)


def equipped(slot):
    qa.cmd('dev.state')
    character = qa.dev().get('character')
    if not character or not character.get('available'): raise AssertionError('Build lacks character equipment diagnostics')
    return character['equipped'].get(slot)


def equip(item, slot, tab):
    """Open the pack (Tab), drag inv-<item> onto equipment-<slot>, close. Returns the equipped state from the dev snapshot."""
    qa.tap('Tab', settle=.8); qa.wait(lambda: qa.state() == 'Inventory', 6, what='inventory')
    before = qa.qty(item)
    if not before or before < 1: raise AssertionError(item + ' is not carried before the equipment drag')
    qa.click_at(*centre(qa.ui(), tab))
    qa.wait(lambda: 'active-tab' in (qa.el(qa.ui(), tab) or {}).get('classes', []), 5, what=tab)
    target_viewport = 'armour-body-map' if slot.startswith('armour_') else 'character-scroll'
    scroll_into_view('equipment-' + slot, target_viewport)
    layout = scroll_into_view('inv-' + item, 'inventory-scroll')
    # Read both endpoints from the same settled layout after scrolling; pack and loadout rebuild independently.
    for name, viewport_name in [('inv-' + item, 'inventory-scroll'), ('equipment-' + slot, target_viewport)]:
        e, viewport = qa.el(layout, name), qa.el(layout, viewport_name)
        if not e or not viewport: raise AssertionError(name + ' is missing before the drag')
        x, y, w, h = e['bounds']
        if not inside((x + w / 2, y + h / 2), viewport['bounds']): raise AssertionError(name + ' is clipped before the drag')
    source, target = centre(layout, 'inv-' + item), centre(layout, 'equipment-' + slot)
    (OUT / f'equip-{item}-layout.json').write_text(json.dumps(layout, indent=1))
    drag(source, target)
    result = (qa.el(qa.ui(), 'equipment-result') or {}).get('text')
    qa.wait(lambda: equipped(slot) == item, 5, what=item + ' equipped by real drag; UI result=' + str(result))
    installed = equipped(slot)
    qa.tap('Escape', settle=.6); qa.wait(lambda: qa.state() == 'Play', 6, what='pack closed')
    return {'tab': tab, 'result': result, 'before': before, 'left': qa.qty(item), 'slot': slot, 'equipped': installed}


LONG_ARM = 5   # 3 Oct 2026: Long Arm's order index after the four Warden Kit orders (was 1)


def fixture_save(folder):
    """A version-2 save at the Long Arm order: primer done, Steady Hands done, receiver and parts carried, skills trained."""
    folder.mkdir(parents=True, exist_ok=True)
    skills = ['armourcraft', 'armourHandling', 'awareness', 'blades', 'blunt', 'chemistry', 'dodging', 'electronics', 'energyWeapons', 'engineering', 'pistol', 'rifle']
    s = {'version': 2, 'savedUtc': '2026-10-02T12:00:00.0000000Z', 'build': '0.1.0', 'credits': 60, 'purchases': 0, 'sales': 0,
         'items': [{'itemId': 'rifle_receiver', 'quantity': 1}, {'itemId': 'scrap_alloy', 'quantity': 12}, {'itemId': 'copper_filament', 'quantity': 6},
                   {'itemId': 'nanite_residue', 'quantity': 8}, {'itemId': 'field_toolkit', 'quantity': 1}, {'itemId': 'droid_servo_damaged', 'quantity': 1},
                   {'itemId': 'water_flask', 'quantity': 1}, {'itemId': 'medkit', 'quantity': 1}],
         'crafting': {'known': ['recipe_charge_cell_core', 'recipe_field_rifle', 'recipe_rifle_precision_barrel', 'recipe_grip_stabilised_pistol'],
                      'crafted': [{'id': 'recipe_grip_stabilised_pistol', 'count': 1}], 'crafts': 1,
                      'fitted': [{'slot': 'grip', 'itemId': 'grip_stabilised_pistol'}],
                      'weapons': [{'weaponId': 'weapon_scrap_pistol', 'fitted': [{'slot': 'grip', 'itemId': 'grip_stabilised_pistol'}]}]},
         'loot': {'rng': 'bc1721a626f0570d', 'rolls': 8, 'misses': [], 'collected': ['scrap_alloy', 'copper_filament', 'nanite_residue', 'droid_servo_damaged', 'rifle_receiver']},
         'bermsStep': 'Complete', 'hasPistol': True,
         'orders': {'index': 5, 'id': 'order_long_arm', 'testFired': ['order_steady_hands'], 'reported': ['order_steady_hands', 'order_kit_helmet']},   # 3 Oct 2026: Long Arm follows the four Warden Kit orders
         'city': {'visitedHill': True, 'boughtFlask': False, 'soldScrap': False, 'linked': False, 'spoken': [], 'selectedDestination': '', 'flags': ['brann_met']},
         'character': {'version': 1, 'level': 1, 'experience': 0, 'attributePoints': 4, 'skillPoints': 12,
                       'attributes': [{'id': a, 'count': 10} for a in ['agility', 'endurance', 'intellect', 'perception', 'resolve', 'strength']],
                       'skills': [{'id': k, 'count': 20 if k in ('rifle', 'engineering') else 0} for k in skills],
                       'equipped': [{'slot': 'armour_chest', 'itemId': 'field_vest'}, {'slot': 'secondary', 'itemId': 'scrap_pistol'}, {'slot': 'storage', 'itemId': 'field_backpack'}]}}
    (folder / 'ward-save.json').write_text(json.dumps(s, indent=1))
    return folder


def phase_a():
    """New game: the primer with real input; the moved first contact and the pistol carry."""
    r = {}
    save = OUT / 'save-a'
    save.mkdir()  # Explicit empty QA save; the user's save and any prior run are never loaded.
    try:
        launch_player('a', save)
        qa.wait_menu(); qa.focus(); qa.tap('Return'); qa.wait(lambda: qa.state() == 'Play', 40, what='new game'); qa.release_all()
        qa.cmd('resize', width=1920, height=1080); time.sleep(1.5)
        qa.cmd('timeSet', hour=13); qa.cmd('timePause', paused=True)
        # locker, draw, plates (as qa.primer does, then stop before first contact to inspect it)
        qa.goto('checkpoint_approach'); qa.view('follow'); qa.yaw(270); time.sleep(.3); qa.hold('w', 1.3); time.sleep(.4)
        qa.goto('checkpoint_locker'); time.sleep(.4); qa.tap('e', settle=.4)
        ok(qa.snap()['combat']['hasPistol'], 'A: pistol taken from the locker with real E')
        qa.tap('7', settle=.6); ok(qa.snap()['combat']['Armed'], 'A: pistol drawn with 7')
        # the carry: drawn, not aiming, standing (the 45-degree complaint)
        qa.goto('rifle_stand'); qa.view('follow'); qa.cmd('cameraBoom', boom=2.4); qa.yaw(110); qa.pitch(8); time.sleep(1.2); cap('a-pistol-carry-side')
        qa.yaw(160); time.sleep(.8); cap('a-pistol-carry-34'); qa.view('cam_rifle_side'); time.sleep(.6); cap('a-pistol-carry-cam_rifle_side'); qa.view('follow')
        # 3 Oct 2026: first-person pistol view model on the MPFB arms (hip and aim)
        qa.yaw(110); qa.pitch(2); qa.cmd('cameraBoom', boom=0.0); time.sleep(.9); s = qa.snap(); cap('a-pistol-first-person')
        ok(s['combat'].get('viewModelVisible', False), 'A: the pistol view model shows in first person', s['combat'].get('viewModelVisible'))
        qa.button(3, True); time.sleep(.9); cap('a-pistol-first-person-aim'); qa.button(3, False); time.sleep(.3)
        qa.cmd('cameraBoom', boom=2.4); time.sleep(.4)
        qa.goto('checkpoint_firingline'); qa.view('follow'); time.sleep(.3)
        for i, (x, z) in enumerate([(-78, 11), (-80.5, 15.5), (-77.5, 20)]):
            for off in [-2.5, -3.5, -1.5, -4.5]:
                if qa.snap()['combat']['targets'] > i: break
                p = qa.pos(); qa.yaw(math.degrees(math.atan2(x - p[0], z - p[2])) + off); qa.pitch(2.5); time.sleep(.15)
                qa.focus(); qa.button(3, True); time.sleep(.4); qa.button(1, True); time.sleep(.07); qa.button(1, False); time.sleep(.3); qa.button(3, False); time.sleep(.25)
        s = qa.snap(); ok(s['combat']['targets'] == 3 and s['combat']['step'] == 'FirstContact', 'A: three plates down, primer at FirstContact', {'targets': s['combat']['targets'], 'step': s['combat']['step']})
        # first contact: the pair spawns on the service road beside the gate, within 35 m of the gate marker
        time.sleep(.5); s = qa.snap(); live = [e for e in s['combat']['enemies'] if e['alive']]
        gate = (-57.0, 1.0); dists = [round(math.hypot(e['position'][0] - gate[0], e['position'][2] - gate[1]), 1) for e in live]
        r['firstContactSpawn'] = [(e['displayName'], e['state'], [round(v, 1) for v in e['position']]) for e in live]
        ok(len(live) == 2 and all(e['displayName'] == 'Feral scrap drone' for e in live) and max(dists) < 40, 'A: first contact is two scrap drones within 40 m of the gate', {'enemies': r['firstContactSpawn'], 'gateDistances': dists})
        qa.goto('checkpoint_road'); qa.view('follow'); time.sleep(.5)
        p = qa.pos(); e = min(live, key=lambda e: math.hypot(e['position'][0] - p[0], e['position'][2] - p[2])); qa.face(e['position'][0], e['position'][2]); time.sleep(.5)
        lay = qa.ui(); marker = [x['text'] for x in lay['elements'] if x['visible'] and x.get('text') and 'SCRAP DRONE' in x['text']]
        ok(bool(marker), 'A: the HUD guidance marker names the scrap drone', marker[:2]); cap('a-first-contact-marker')
        d1 = []
        r['firstContact'] = qa.fight(until=lambda s: s['combat']['step'] == 'Depot', seconds=150, deaths=d1)
        ok(qa.snap()['combat']['step'] == 'Depot', 'A: the service-road pair put down with real F; depot nest armed', r['firstContact'])
        qa.face(-80.6, -36.2); time.sleep(.6)   # the marker only shows while its target is in view
        marker = []
        for _ in range(8):   # the marker refreshes with the HUD; poll briefly
            lay = qa.ui(); marker = [x['text'] for x in lay['elements'] if x['visible'] and x.get('text') and 'MACHINE DEPOT' in x['text']]
            if marker: break
            qa.face(-80.6, -36.2); time.sleep(.5)
        ok(bool(marker), 'A: the HUD marker now points at the machine depot', marker[:2])
        qa.goto('depot_approach'); qa.view('follow'); time.sleep(.4)
        d2 = []
        r['depot'] = qa.fight(until=lambda s: s['combat']['step'] == 'Complete', seconds=300, deaths=d2, center=(-80.6, -36.2), leash=16, regroup='depot_approach')
        ok(qa.snap()['combat']['step'] == 'Complete', 'A: depot nest cleared, primer complete', {'shots': r['depot'].get('shots'), 'seconds': r['depot'].get('seconds'), 'kills': len(d2)})
        r['errors'] = qa.log_errors(); ok(not r['errors'], 'A: no runtime exceptions in Player.log', r['errors'][:3])
    finally:
        stop_player()
    report['phases']['a'] = r


def phase_b():
    """Continue on the fixture: Long Arm, the rifle in hand, then the plate carrier."""
    r = {}
    save = fixture_save(OUT / 'save')
    try:
        launch_player('b', save)
        qa.wait_menu(); qa.focus(); qa.tap('Return'); qa.wait(lambda: qa.state() == 'Play', 40, what='Play after Continue'); qa.release_all()
        qa.cmd('resize', width=1920, height=1080); time.sleep(1.5)
        qa.cmd('timeSet', hour=13); qa.cmd('timePause', paused=True)
        c = qa.craft(); r['start'] = {k: c.get(k) for k in ('fieldOrder', 'orderStage', 'objective')}
        ok(c.get('fieldOrder') == LONG_ARM and c.get('orderStage') == 'Report', 'B: continued at Long Arm, waiting for the report to Brann', r['start'])
        ok(qa.qty('field_rifle') in (None, 0), 'B: no test-issue rifle in the pack', qa.qty('field_rifle'))
        # Brann: report line, then the bench
        qa.goto('salvage_counter'); qa.view('follow'); time.sleep(.5)
        ok('Talk to Brann' in (inter()['prompt'] or ''), 'B: Brann offers the E prompt at the counter', inter()['prompt'])
        qa.tap('e'); qa.wait(lambda: qa.state() == 'Dialogue', 5, what='dialogue'); i = inter()
        ok(i['npc'] == 'Brann' and i['node'] == 'long_report', 'B: Brann opens with the rifle receiver line', {'npc': i['npc'], 'node': i['node']}); cap('b-brann-receiver')
        ok(qa.craft().get('orderStage') == 'Fabricate', 'B: talking to Brann moves Long Arm to fabrication', qa.craft().get('objective'))
        qa.tap('Return', settle=.6); qa.wait(lambda: qa.state() == 'Play', 5, what='dialogue closed')
        qa.goto('salvage_bench'); time.sleep(.5); qa.tap('e', settle=.8)
        ok(qa.state() == 'Fabricator', 'B: E at the workbench opens the fabricator', qa.state())
        lay = qa.ui(); focused = qa.snap()['session'].get('focused')
        if focused != 'fab-recipe-recipe_field_rifle':
            e = qa.el(lay, 'fab-recipe-recipe_field_rifle')
            if e and e['visible']: qa.click_at(*centre(lay, 'fab-recipe-recipe_field_rifle')); time.sleep(.4)
        cap('b-bench-rifle')
        e = qa.el(qa.ui(), 'fabricator-craft'); qa.click_at(*centre(qa.ui(), 'fabricator-craft')) if e and e['visible'] else qa.tap('Return', settle=.8)
        time.sleep(.8); c = qa.craft()
        ok((qa.qty('field_rifle') or 0) >= 1, 'B: the Field Rifle is fabricated at the bench', {'crafts': c.get('crafts'), 'rifle': qa.qty('field_rifle'), 'reason': (qa.el(qa.ui(), 'fab-reason') or {}).get('text')})
        qa.tap('Escape', settle=.6); qa.wait(lambda: qa.state() == 'Play', 6, what='fabricator closed')
        qa.wait(lambda: qa.craft().get('fieldOrder') == LONG_ARM + 1, 6, what='Long Arm order completion')
        c = qa.craft(); ok(c.get('fieldOrder') == LONG_ARM + 1, 'B: Long Arm complete, Plate Carrier is the current order', {k: c.get(k) for k in ('fieldOrder', 'orderStage', 'objective')})
        # equip the rifle (primary) and draw it at the range
        r['equipRifle'] = equip('field_rifle', 'primary', 'character-tab-primary')
        ok(r['equipRifle']['equipped'] == 'field_rifle' and (r['equipRifle']['left'] or 0) == r['equipRifle']['before'] - 1, 'B: the rifle is equipped in the primary slot by drag', r['equipRifle'])
        qa.goto('rifle_stand'); qa.view('follow'); time.sleep(.5); qa.yaw(270)
        qa.tap('8', settle=.8); s = qa.snap(); w = weapon()
        ok(s['combat']['Armed'] and w == 'weapon_field_rifle' and s['combat'].get('rifleShown') and not s['combat'].get('pistolShown'), 'B: 8 draws the field rifle (rifle model shown, pistol hidden)', {'armed': s['combat']['Armed'], 'weapon': w, 'rifleShown': s['combat'].get('rifleShown'), 'notice': s['session']['notice']})
        ok('rifle' in (s['session']['notice'] or '').lower(), 'B: draw notice names the rifle', s['session']['notice'])
        lay = qa.ui(); slot8 = qa.el(lay, 'slot8'); ok(slot8 and slot8.get('enabled', True) and not any('empty-slot' == c for c in slot8['classes']), 'B: hotbar slot 8 shows the rifle', slot8 and {'classes': slot8['classes'], 'tooltip': slot8.get('tooltip')})
        time.sleep(1.0)
        for cam, name in [('cam_rifle_carry', 'b-rifle-carry-quarter'), ('cam_rifle_side', 'b-rifle-carry-side')]: qa.view(cam); time.sleep(.6); cap(name)
        qa.view('follow'); qa.cmd('cameraBoom', boom=2.4); qa.yaw(110); qa.pitch(6); time.sleep(.8); cap('b-rifle-carry-follow')
        # held fire: a burst
        shots0 = qa.snap()['combat']['ShotsFired']; qa.focus(); qa.yaw(270); qa.pitch(0); time.sleep(.3)
        qa.key('f', True); time.sleep(.75); qa.key('f', False); time.sleep(.3)
        shots = qa.snap()['combat']['ShotsFired'] - shots0
        ok(shots >= 3, 'B: holding F fires a burst from the rifle', {'shots': shots})
        # aim: raised two-hand hold
        qa.yaw(90); time.sleep(.4); qa.button(3, True); time.sleep(.9); cap('b-rifle-aim-follow'); qa.view('cam_rifle_aim'); time.sleep(.5); cap('b-rifle-aim-cam'); qa.view('cam_rifle_side'); time.sleep(.4); cap('b-rifle-aim-side'); qa.button(3, False); qa.view('follow'); time.sleep(.5)
        # switch: 7 holsters the rifle and draws the pistol; 8 switches back
        qa.tap('7', settle=.7); s = qa.snap(); w = weapon(); ok(s['combat']['Armed'] and w == 'weapon_scrap_pistol', 'B: 7 switches to the pistol while armed', {'armed': s['combat']['Armed'], 'weapon': w})
        qa.tap('8', settle=.7); s = qa.snap(); w = weapon(); ok(s['combat']['Armed'] and w == 'weapon_field_rifle', 'B: 8 switches back to the rifle', {'weapon': w})
        qa.tap('8', settle=.6); ok(not qa.snap()['combat']['Armed'], 'B: 8 again holsters the rifle')
        # first person: no rifle view model, no pistol view model either
        qa.tap('8', settle=.6); qa.cmd('cameraBoom', boom=0.0); time.sleep(.8); s = qa.snap(); ok(not s['combat'].get('viewModelVisible', False), 'B: the pistol view model stays hidden with the rifle drawn in first person', s['combat'].get('viewModelVisible')); cap('b-rifle-first-person')
        # 3 Oct 2026: the field rifle has its own first-person view model (arms + rifle); hip view above, aim view here
        ok(s['combat'].get('rifleViewModelVisible', False), 'B: the rifle view model shows with the rifle drawn in first person', s['combat'].get('rifleViewModelVisible'))
        qa.button(3, True); time.sleep(1.0); s = qa.snap(); cap('b-rifle-first-person-aim')
        ok(s['combat'].get('rifleViewModelVisible', False), 'B: the rifle view model stays up while aiming in first person', s['combat'].get('rifleViewModelVisible'))
        qa.button(3, False); time.sleep(.4)
        qa.cmd('cameraBoom', boom=2.4); qa.tap('8', settle=.5)
        # plate carrier: the caravan scavengers and the strongbox
        qa.goto('caravan_approach'); qa.view('follow'); time.sleep(.6); qa.face(-205, 74); time.sleep(.4)
        qa.tap('8', settle=.6)
        d3 = []
        r['caravanFight'] = qa.fight(until=lambda s: not any(e['alive'] and math.hypot(e['position'][0] + 205, e['position'][2] - 74) < 45 for e in s['combat']['enemies']), seconds=240, deaths=d3, center=(-205, 74), leash=30, regroup='caravan_approach', engage=14.0)
        ok(len(d3) >= 3, 'B: caravan scavengers cleared with the rifle', {'kills': len(d3), 'shots': r['caravanFight'].get('shots')})
        qa.goto('caravan_strongbox'); time.sleep(.5)
        box = (-208.3, 75.8); got = None
        for a in [0, .9, -.9, 1.8, -1.8, 2.7]:
            try: qa.walk_to(box[0] + math.sin(a) * 1.3, box[1] + math.cos(a) * 1.3, tol=.5, timeout=12)
            except TimeoutError: pass
            pr = inter()['prompt'] or ''
            if pr.startswith('E · '): break
        r['strongboxPrompt'] = inter()['prompt']
        ok((inter()['prompt'] or '').startswith('E · '), 'B: the caravan strongbox offers its search prompt', inter()['prompt'])
        q0 = qa.snap()['session']['quantities']; qa.tap('e', settle=.3); cap('b-strongbox-search')
        qa.wait(lambda: (qa.qty('warden_plate_carrier') or 0) >= 1, 8, what='plate carrier from the strongbox')
        ok((qa.qty('warden_plate_carrier') or 0) >= 1, 'B: the Warden plate carrier comes out of the strongbox', {'got': {k: v - q0.get(k, 0) for k, v in qa.snap()['session']['quantities'].items() if v != q0.get(k, 0)}})
        qa.wait(lambda: qa.craft().get('fieldOrder') == LONG_ARM + 2, 6, what='Plate Carrier order completion')   # the order evaluates on the next frame after the pickup
        c = qa.craft(); ok(c.get('fieldOrder') == LONG_ARM + 2, 'B: Plate Carrier complete, the Depot Foreman order is next', {k: c.get(k) for k in ('fieldOrder', 'orderStage')})
        r['equipVest'] = equip('warden_plate_carrier', 'armour_chest', 'character-tab-armour')
        ok(r['equipVest']['equipped'] == 'warden_plate_carrier' and (r['equipVest']['left'] or 0) == r['equipVest']['before'] - 1, 'B: the plate carrier is equipped in the chest slot by drag', r['equipVest'])
        qa.goto('rifle_stand'); qa.view('follow'); time.sleep(.6)
        for cam, name in [('cam_vest_front', 'b-vest-front'), ('cam_vest_quarter', 'b-vest-quarter')]: qa.view(cam); time.sleep(.6); cap(name)
        qa.view('follow'); qa.cmd('cameraBoom', boom=2.2); qa.yaw(90); qa.pitch(6); time.sleep(.8); cap('b-vest-follow')
        ok('warden_plate_carrier' in (qa.snap()['combat'].get('wornArmour') or []), 'B: the plate carrier model is shown on the colonist', qa.snap()['combat'].get('wornArmour'))
        # the save records both pieces
        qa.cmd('timePause', paused=False); time.sleep(1.0)
        qa.tap('Escape', settle=.8)  # pause menu saves
        qa.tap('Escape', settle=.5)
        saved = json.loads((save / 'ward-save.json').read_text()); eq = {x['slot']: x['itemId'] for x in saved['character']['equipped']}
        ok(eq.get('primary') == 'field_rifle' and eq.get('armour_chest') == 'warden_plate_carrier', 'B: the save records the rifle and the plate carrier equipped', eq)
        r['errors'] = qa.log_errors(); ok(not r['errors'], 'B: no runtime exceptions in Player.log', r['errors'][:3])
    finally:
        stop_player()
    report['phases']['b'] = r


try:
    try: phase_a()
    except Exception as e: report['failures'].append({'phase': 'A', 'error': repr(e), 'trace': traceback.format_exc()[-1500:]}); print('phase A error', e, flush=True)
    try: phase_b()
    except Exception as e: report['failures'].append({'phase': 'B', 'error': repr(e), 'trace': traceback.format_exc()[-1500:]}); print('phase B error', e, flush=True)
finally:
    report['passed'] = not report['failures']
    (OUT / 'report.json').write_text(json.dumps(report, indent=1, default=str))
    print(('RIFLE QUEST PASS' if report['passed'] else 'RIFLE QUEST FAIL') + f" ({len(report['checks'])} checks, {len(report['failures'])} failures)")
