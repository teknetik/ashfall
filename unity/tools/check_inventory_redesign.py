"""Native Ashfall inventory / loadout / merchant regression, 2 Oct 2026.

Run only when no other Unity or player job is active:
  uv run --offline --with python-xlib --with pillow python unity/tools/check_inventory_redesign.py OUT [--save SEED_DIR] [--exe DEVELOPMENT_PLAYER]

Creates an isolated version-3 QA save, then uses Continue and real XTEST input for
all gameplay/UI verbs. The bridge only reads state, positions the player at the
existing Basic General landmark, changes review time/resolution and captures.
Uses a named, memory-capped systemd scope and always stops the whole scope.
--prepare-only validates/writes the save without launching anything.
--profile-seconds 6 optionally samples closed/open UI frames; default omits profiling.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'unity/evidence/gameplay-v2/20260930-reqa2'))
import qa  # noqa: E402

SEED = ROOT / 'unity/evidence/combined/20261001/final/walk-final-1/save/ward-save.json'
CARRIED = {
    'water_flask': 2, 'medkit': 2, 'scrap_coil': 3, 'scrap_alloy': 3,
    'droid_servo_damaged': 2, 'copper_filament': 3, 'micro_capacitor': 2,
    'optic_lens_cracked': 1, 'actuator_intact': 1, 'alloy_plate': 2,
    'wound_coil': 1, 'charge_cell_core': 1, 'field_toolkit': 1,
    'grip_stabilised_pistol': 1, 'barrel_bored_alloy': 1,
    'cell_salvaged_capacitor': 1, 'rifle_precision_barrel': 1,
    'aug_cognition': 1, 'aug_sighting': 1, 'aug_reflex': 1,
    'armour_extra_plate': 1, 'armour_impact_liner': 1,
    'armour_leg_motor': 1, 'armour_grip_damper': 1,
}
EQUIPPED = {
    'primary': 'field_rifle', 'secondary': 'scrap_pistol',
    'storage': 'field_backpack', 'armour_chest': 'field_vest',
    'armour_legs': 'field_leggings', 'armour_feet': 'field_boots',
    'armour_head': 'field_helmet', 'armour_hands': 'field_gloves',
    'implant_head': 'targeting_implant_mk1',
}


def prepare_save(out, source):
    """Author test inputs on disk; never grant or equip through runtime commands."""
    source = source.resolve()
    if source.is_dir():
        source /= 'ward-save.json'
    if not source.is_file():
        raise FileNotFoundError(f'QA seed missing: {source}; pass --save SAVE_DIR or SAVE_JSON')
    original = source.read_bytes()
    data = json.loads(original)
    folder = out / 'save'
    folder.mkdir()
    (out / 'seed-source.json').write_text(json.dumps({'path': str(source), 'sha256': hashlib.sha256(original).hexdigest()}, indent=2))
    data.update(version=3, credits=1000, purchases=0, sales=0, bermsStep='Complete', hasPistol=True)
    data['items'] = [{'itemId': item, 'quantity': count} for item, count in CARRIED.items()]
    character = data.setdefault('character', {})
    character.update(version=2, level=1, experience=0, attributePoints=4, skillPoints=20,
                     equipped=[{'slot': slot, 'itemId': item} for slot, item in EQUIPPED.items()], modifications=[])
    attributes = {row['id']: row['count'] for row in character.get('attributes', [])}
    attributes.update(strength=20, endurance=12, intellect=12, agility=10, perception=10, resolve=10)
    character['attributes'] = [{'id': key, 'count': value} for key, value in attributes.items()]
    skills = {row['id']: row['count'] for row in character.get('skills', [])}
    skills.update(rifle=20, pistol=20, engineering=20)
    character['skills'] = [{'id': key, 'count': value} for key, value in skills.items()]
    data.setdefault('crafting', {}).update(fitted=[], weapons=[{'weaponId': 'weapon_field_rifle', 'fitted': []}, {'weaponId': 'weapon_scrap_pistol', 'fitted': []}])
    data['orders'] = {'index': -1, 'testFired': []}
    data['city'] = {'visitedHill': False, 'boughtFlask': False, 'soldScrap': False, 'linked': False, 'spoken': [], 'selectedDestination': '', 'flags': []}
    (folder / 'ward-save.json').write_text(json.dumps(data, indent=2))
    # Retain the exact starting fixture after the player starts autosaving.
    (out / 'initial-ward-save.json').write_text(json.dumps(data, indent=2))
    return folder


def launch(out, save, exe, unit):
    run = out / 'run'
    run.mkdir()
    qa.use(run)
    qa.EXE = exe
    settings = json.loads((ROOT / 'unity/evidence/courtyard/20260908/after-native/settings.json').read_text())['video']
    settings['antiAliasing'] = 32
    encoded = base64.b64encode(json.dumps(settings).encode()).decode()
    for vendor, product in [('unknown', 'unknown'), ('Free Column', 'Athen Hill')]:
        folder = run / 'config/unity3d' / vendor / product
        folder.mkdir(parents=True)
        (folder / 'prefs').write_text('<?xml version="1.0" encoding="utf-8"?><unity_prefs version_major="1" version_minor="1"><pref name="AthenHill.Settings.v1.QA.Video" type="string">' + encoded + '</pref></unity_prefs>')
    args = [str(exe), '-force-glcore', '-screen-width', '1920', '-screen-height', '1080', '-screen-fullscreen', '0', '-logFile', str(run / 'Player.log'), '--athen-qa', str(run), '--athen-qa-background', '--athen-save-dir', str(save)]
    # $1 is a local output filename; no shell interpolation of user strings.
    command = ['systemd-run', '--user', '--scope', '--expand-environment=no', '--unit=' + unit, '-q', '-p', 'MemoryMax=12G', '-p', 'MemoryHigh=10G', '-p', 'MemorySwapMax=512M', 'bash', '-c', 'printf "%s\\n" "$$" > "$1"; shift; exec "$@"', 'ashfall-inventory-qa', str(run / 'pid')] + args
    log = (run / 'scope.log').open('w')
    proc = subprocess.Popen(command, env=dict(os.environ, XDG_CONFIG_HOME=str(run / 'config')), stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    log.close()
    qa.wait(lambda: (run / 'pid').is_file() or proc.poll() is not None, timeout=20, what='player pid in named scope')
    if not (run / 'pid').is_file():
        raise RuntimeError('Scope did not launch the player: ' + (run / 'scope.log').read_text()[-2000:])
    (run / 'launch.json').write_text(json.dumps({'unit': unit + '.scope', 'args': args, 'pid': qa.pid(), 'video': settings, 'sourceRevision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(), 'exe': str(exe), 'exeMtime': exe.stat().st_mtime}, indent=2))
    return proc


def centre(bounds):
    return bounds[0] + bounds[2] / 2, bounds[1] + bounds[3] / 2


def panel_bounds(layout):
    # UI Toolkit reports reference-panel coordinates (1920x1080 even in a 1280x720 window).
    return (qa.el(layout, 'hud') or {}).get('bounds', [0, 0, layout['width'], layout['height']])


def pixels(point, layout):
    panel = panel_bounds(layout)
    return ((point[0] - panel[0]) * layout['width'] / panel[2],
            (point[1] - panel[1]) * layout['height'] / panel[3])


def point_inside(point, bounds, inset=3):
    x, y = point
    return bounds[0] + inset <= x <= bounds[0] + bounds[2] - inset and bounds[1] + inset <= y <= bounds[1] + bounds[3] - inset


def move(x, y):
    from Xlib import X
    from Xlib.ext import xtest
    display = qa.focus(center=False)
    origin = display.screen().root.translate_coords(qa.window(), 0, 0)
    xtest.fake_input(display, X.MotionNotify, x=origin.x + int(x), y=origin.y + int(y))
    display.sync()
    time.sleep(.07)


def wheel(name, direction, ticks=3):
    layout = qa.ui()
    element = qa.el(layout, name)
    if not element or not element['visible']:
        raise AssertionError(f'Scroll target {name} is not visible')
    move(*pixels(centre(element['bounds']), layout))
    for _ in range(ticks):
        qa.button(5 if direction > 0 else 4, True)
        qa.button(5 if direction > 0 else 4, False)
        time.sleep(.045)
    time.sleep(.18)


def click(name, scroll=None, timeout=12):
    deadline = time.monotonic() + timeout
    while True:
        layout = qa.ui()
        element = qa.el(layout, name)
        if not element or not element['visible']:
            raise AssertionError(f'Element {name} absent/hidden in {qa.state()}; focused={qa.focused()}')
        if not element['enabled']:
            raise AssertionError(f'Element {name} disabled: {element}; equipment-result={text("equipment-result", layout)}')
        point = centre(element['bounds'])
        viewport = qa.el(layout, scroll)['bounds'] if scroll else panel_bounds(layout)
        if point_inside(point, viewport) and point_inside(point, panel_bounds(layout)):
            qa.click_at(*pixels(point, layout))
            return element
        if not scroll or time.monotonic() >= deadline:
            raise AssertionError(f'Element {name} not reachable: bounds={element["bounds"]}, viewport={viewport}')
        wheel(scroll, 1 if point[1] > viewport[1] + viewport[3] else -1, 2)


def text(name, layout=None):
    return (qa.el(layout or qa.ui(), name) or {}).get('text')


def set_text(name, value):
    click(name)
    qa.key('Control_L', True)
    try:
        # Let Unity observe the modifier and chord on separate input frames.
        # Zero-duration XTEST chords can arrive after their modifier is released.
        time.sleep(.12)
        qa.tap('a', secs=.12, settle=.12)
    finally:
        qa.key('Control_L', False)
    time.sleep(.12)
    qa.tap('BackSpace', settle=.12)
    for char in value:
        qa.tap(char, secs=.03, settle=.06)
    time.sleep(.35)


def drag_preview():
    layout = qa.ui()
    box = qa.el(layout, 'preview-view')['bounds']
    x, y = pixels(centre(box), layout)
    width = min(120, box[2] * layout['width'] / panel_bounds(layout)[2] * .5)
    move(x - width / 2, y)
    qa.button(1, True)
    try:
        for step in range(1, 9):
            move(x - width / 2 + width * step / 8, y)
    finally:
        qa.button(1, False)
    move(qa.snap()['width'] - 25, 30)
    time.sleep(.4)


def drag_equipment(source_name, target_name, source_scroll, target_scroll):
    """Drag visible controls with held real input, crossing the 7px capture threshold."""
    layout = qa.ui()
    points = []
    for name, viewport_name in [(source_name, source_scroll), (target_name, target_scroll)]:
        element = qa.el(layout, name)
        viewport = qa.el(layout, viewport_name)
        if not element or not element['visible'] or not element['enabled'] or not viewport:
            raise AssertionError(f'Drag endpoint {name} is unavailable in {viewport_name}')
        point = centre(element['bounds'])
        if not point_inside(point, viewport['bounds']) or not point_inside(point, panel_bounds(layout)):
            raise AssertionError(f'Drag endpoint {name} is clipped: {element["bounds"]}; viewport={viewport["bounds"]}')
        points.append(pixels(point, layout))
    start, end = points
    move(*start)
    qa.button(1, True)
    try:
        # One slow sweep gives PointerDown time to arrive before real movement;
        # release only at the target, never using a bridge equip/unequip verb.
        time.sleep(.12)
        for step in range(1, 17):
            move(start[0] + (end[0] - start[0]) * step / 16,
                 start[1] + (end[1] - start[1]) * step / 16)
        time.sleep(.12)
    finally:
        qa.button(1, False)
    move(qa.snap()['width'] - 25, 30)
    time.sleep(.4)
    return {'source': source_name, 'target': target_name, 'startPixels': start, 'endPixels': end}


def dev():
    qa.cmd('dev.state')
    return qa.dev()


def character():
    value = dev().get('character')
    if not value or not value.get('available'):
        raise AssertionError('Build lacks read-only dev-state character diagnostics required by this QA script')
    return value


def installed(slot, index):
    return next((row['itemId'] for row in character()['modifications'] if row['slot'] == slot and row['socketIndex'] == index), None)


def stat(name):
    return character()['stats'][name]


def visible_ids(prefix, layout=None):
    return [e['name'] for e in (layout or qa.ui())['elements'] if e['visible'] and (e.get('name') or '').startswith(prefix)]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('out', type=Path)
    parser.add_argument('--save', type=Path, default=SEED)
    parser.add_argument('--exe', type=Path, default=qa.EXE)
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--profile-seconds', type=float, default=0)
    parser.add_argument('--city-loop', action='store_true', help='Walk the existing city dialogue, trade and Lattice regression before stopping this player')
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    save = prepare_save(out, args.save)
    if args.prepare_only:
        print(json.dumps({'prepared': str(save), 'carriedStacks': len(CARRIED), 'equipment': EQUIPPED, 'launched': False}, indent=2))
        return 0
    exe = args.exe.resolve()
    if not exe.is_file():
        raise FileNotFoundError(f'Development player not found: {exe}')
    report = {'complete': False, 'seed': str(args.save.resolve()), 'checks': [], 'captures': [], 'errors': []}
    unit = 'ashfall-inventory-qa-' + uuid.uuid4().hex[:10]
    launched = False

    def persist():
        (out / 'report.json').write_text(json.dumps(report, indent=2, default=str))

    def expect(label, condition, evidence=None):
        report['checks'].append({'label': label, 'pass': bool(condition), 'evidence': evidence})
        persist()
        if not condition:
            raise AssertionError(f'{label}: {evidence}')
        print('PASS ' + label, flush=True)

    def capture(name):
        report['captures'].append(qa.capture(name))
        persist()

    try:
        launched = True
        launch(out, save, exe, unit)
        qa.wait_menu()
        qa.focus()
        qa.tap('Return', settle=1)
        qa.wait(lambda: qa.state() == 'Play', 30, what='Play after real Continue')
        qa.cmd('resize', width=1920, height=1080)
        qa.cmd('timeSet', hour=17.0)
        qa.cmd('timePause', paused=True)
        qa.PARK = (1895, 30)
        time.sleep(1)
        report['environment'] = qa.read('environment.json')
        qa.cmd('settingsSnapshot')
        report['settings'] = qa.read('settings.json')
        video = report['settings']['video']
        expect('Native High settings are applied at full render scale', video['preset'] == 2 and video['antiAliasing'] == 32 and abs(report['settings']['renderScale'] - 1) < .001 and qa.snap()['width'] == 1920 and qa.snap()['height'] == 1080, report['settings'])
        baseline = character()
        expect('Version-3 fixture loads both weapons and inventory', baseline['equipped'].get('primary') == 'field_rifle' and baseline['equipped'].get('secondary') == 'scrap_pistol' and qa.snap()['session']['credits'] == 1000, baseline)
        expect('Fixture restores all pack stacks, equipped hosts and empty module sockets', baseline['equipped'] == EQUIPPED and baseline['modifications'] == [] and baseline['packSlotsUsed'] == len(CARRIED) and baseline['packSlotCapacity'] == 40 and all(qa.qty(item) == quantity for item, quantity in CARRIED.items()), baseline)
        expect('Fixture fits both physical and pack capacity limits', baseline['carryWeight'] <= baseline['carryCapacity'] and baseline['packWeight'] <= baseline['storageCapacity'], baseline)
        if args.profile_seconds:
            report['closedFrames'] = qa.profile_for(args.profile_seconds, 'frames-closed')
        qa.tap('Tab', settle=.8)
        qa.wait(lambda: qa.state() == 'Inventory', 5, what='Tab opens inventory')
        expect('Tab opens inventory', qa.state() == 'Inventory')
        click('inv-scrap_coil', 'inventory-scroll')
        layout = qa.ui()
        pack = qa.el(layout, 'pack-col')['bounds']
        detail = qa.el(layout, 'inventory-details')['bounds']
        expect('One click opens adjacent details', text('details-title', layout) == 'Scrap Coil' and detail[0] >= pack[0] + pack[2] - 3, {'pack': pack, 'details': detail, 'title': text('details-title', layout)})
        expect('Capacity displays real stack and weight limits', '/' in text('pack-slot-capacity', layout) and 'kg' in text('pack-weight-capacity', layout), [text('pack-slot-capacity', layout), text('pack-weight-capacity', layout)])
        capture('01-pack-details-1080')
        previous = qa.focused()
        qa.tap('Right', settle=.3)
        expect('Arrow navigation continues with details open', (qa.focused() or '').startswith('inv-') and qa.focused() != previous, {'before': previous, 'after': qa.focused()})
        qa.tap('Return', settle=.25)
        expect('Enter keeps the selected item in the adjacent inspector', qa.state() == 'Inventory' and bool(text('details-title')))
        qa.tap('Escape', settle=.4)
        expect('One Escape closes inventory after Enter inspection', qa.state() == 'Play', {'state': qa.state()})
        qa.tap('Tab', settle=.6)
        qa.wait(lambda: qa.state() == 'Inventory', 5, what='reopen inventory after keyboard inspection')
        set_text('pack-search', 'alloy')
        filtered = visible_ids('inv-')
        expect('Search narrows carried items', bool(filtered) and all('alloy' in name for name in filtered), filtered)
        set_text('pack-search', '')
        expect('Clearing search restores grid', len(visible_ids('inv-')) >= len(CARRIED), visible_ids('inv-'))
        if args.profile_seconds:
            report['openFrames'] = qa.profile_for(args.profile_seconds, 'frames-open')

        click('character-tab-implants')
        click('equipment-implant_head', 'character-scroll')
        layout = qa.ui()
        sockets = visible_ids('modification-socket-', layout)
        preview = dev()['preview']
        expect('Implants use the body map with exactly three sockets and no 3D camera', len(sockets) == 3 and (qa.el(layout, 'implant-body-map') or {}).get('visible') and not (qa.el(layout, 'preview-col') or {}).get('visible') and not preview['active'], {'sockets': sockets, 'preview': preview})
        click('modification-socket-0', 'equipment-inspector-scroll')
        expect('Clicking an implant socket opens its nested panel', bool((qa.el(qa.ui(), 'augmentation-details') or {}).get('visible')))
        intellect, mass, quantity = stat('intellect'), character()['carryWeight'], qa.qty('aug_cognition')
        click('install-augmentation-aug_cognition', 'equipment-inspector-scroll')
        qa.wait(lambda: installed('implant_head', 0) == 'aug_cognition', what='augmentation model commit')
        expect('Installing augmentation transfers one item and applies stat without changing total mass', qa.qty('aug_cognition') == quantity - 1 and abs(stat('intellect') - intellect - 1) < .001 and abs(character()['carryWeight'] - mass) < .001, character())
        layout = qa.ui()
        map_bounds = qa.el(layout, 'implant-body-map')['bounds']
        viewport = qa.el(layout, 'character-scroll')['bounds']
        expect('Full X-ray stays visible while the augmentation inspector scrolls',
               map_bounds[1] >= viewport[1] - 1 and map_bounds[1] + map_bounds[3] <= viewport[1] + viewport[3] + 1,
               {'map': map_bounds, 'viewport': viewport})
        capture('02-implants-augmentation-1080')
        click('remove-augmentation', 'equipment-inspector-scroll')
        qa.wait(lambda: installed('implant_head', 0) is None, what='augmentation removal')
        expect('Removing augmentation returns item and restores stat', qa.qty('aug_cognition') == quantity and abs(stat('intellect') - intellect) < .001, character())

        click('character-tab-armour')
        click('equipment-armour_legs', 'character-scroll')
        click('modification-socket-0', 'equipment-inspector-scroll')
        speed, quantity = stat('movementSpeed'), qa.qty('armour_leg_motor')
        click('install-augmentation-armour_leg_motor', 'equipment-inspector-scroll')
        qa.wait(lambda: installed('armour_legs', 0) == 'armour_leg_motor', what='leg motor commit')
        expect('Armour motor applies actual movement stat and character preview stays active', stat('movementSpeed') > speed and qa.qty('armour_leg_motor') == quantity - 1 and dev()['preview']['active'] and not dev()['preview']['showingWeapon'], {'beforeSpeed': speed, 'afterSpeed': stat('movementSpeed'), 'preview': dev()['preview']})
        capture('03-armour-motor-1080')
        click('remove-augmentation', 'equipment-inspector-scroll')
        qa.wait(lambda: installed('armour_legs', 0) is None, what='leg motor removal')
        expect('Motor removal restores movement and inventory', abs(stat('movementSpeed') - speed) < .001 and qa.qty('armour_leg_motor') == quantity, character())

        # Round-trip an armour host with no modules: a click-only implementation
        # cannot pass these model assertions, and the final fixture is unchanged.
        click('equipment-armour_head', 'character-scroll')
        drag_before = character()
        pack_before = {item: count for item, count in qa.snap()['session']['quantities'].items() if count}
        helmet_before = qa.qty('field_helmet') or 0
        helmet_mass = 1.2  # Authored Field Helmet weight in both current catalogs.
        expect('Armour drag fixture has an equipped helmet and room to return it',
               drag_before['equipped'].get('armour_head') == 'field_helmet'
               and helmet_before == 0
               and drag_before['packSlotsUsed'] < drag_before['packSlotCapacity']
               and drag_before['packWeight'] + helmet_mass <= drag_before['storageCapacity'], drag_before)
        drag_out = drag_equipment('equipment-armour_head', 'inv-water_flask', 'character-scroll', 'inventory-scroll')
        qa.wait(lambda: character()['equipped'].get('armour_head') != 'field_helmet'
                and (qa.qty('field_helmet') or 0) == helmet_before + 1, what='real armour drag returns helmet to pack')
        drag_removed = character()
        expected_pack = dict(pack_before, field_helmet=helmet_before + 1)
        expect('Real armour drag unequips one helmet without losing mass or other pack items',
               not drag_removed['equipped'].get('armour_head')
               and drag_removed['packSlotsUsed'] == drag_before['packSlotsUsed'] + 1
               and abs(drag_removed['packWeight'] - drag_before['packWeight'] - helmet_mass) < .001
               and abs(drag_removed['carryWeight'] - drag_before['carryWeight']) < .001
               and drag_removed['stats']['armour'] < drag_before['stats']['armour']
               and {item: count for item, count in qa.snap()['session']['quantities'].items() if count} == expected_pack,
               {'drag': drag_out, 'before': drag_before, 'after': drag_removed})
        # The returned item occupies the next pack cell. Select it and the empty
        # host first so both endpoints are scrolled into view before pressing.
        click('inv-field_helmet', 'inventory-scroll')
        click('equipment-armour_head', 'character-scroll')
        drag_back = drag_equipment('inv-field_helmet', 'equipment-armour_head', 'inventory-scroll', 'character-scroll')
        qa.wait(lambda: character()['equipped'].get('armour_head') == 'field_helmet'
                and (qa.qty('field_helmet') or 0) == helmet_before, what='real armour drag re-equips helmet')
        drag_restored = character()
        expect('Dragging helmet back restores equipment, stats, quantities and carry weights',
               drag_restored['equipped'] == drag_before['equipped']
               and drag_restored['modifications'] == drag_before['modifications']
               and drag_restored['packSlotsUsed'] == drag_before['packSlotsUsed']
               and abs(drag_restored['packWeight'] - drag_before['packWeight']) < .001
               and abs(drag_restored['carryWeight'] - drag_before['carryWeight']) < .001
               and all(abs(drag_restored['stats'][key] - value) < .001 for key, value in drag_before['stats'].items())
               and {item: count for item, count in qa.snap()['session']['quantities'].items() if count} == pack_before,
               {'drag': drag_back, 'before': drag_before, 'after': drag_restored})

        for index, tab, item in [(4, 'primary', 'Field Rifle'), (5, 'secondary', 'Scrap Pistol')]:
            click('character-tab-' + tab)
            layout = qa.ui()
            preview = dev()['preview']
            expect(tab.title() + ' has a 2D weapon image, attachment slots and live 3D weapon', (qa.el(layout, 'weapon-picture') or {}).get('visible') and len(visible_ids('socket-', layout)) > 0 and preview['active'] and preview['showingWeapon'] and text('preview-name', layout) == item, {'preview': preview, 'name': text('preview-name', layout), 'sockets': visible_ids('socket-', layout)})
            capture(f'{index:02d}-{tab}-overview-1080')
            old_yaw = preview['yaw']
            drag_preview()
            expect(tab.title() + ' preview rotates from real pointer drag', abs(dev()['preview']['yaw'] - old_yaw) > 5, {'before': old_yaw, 'after': dev()['preview']['yaw']})
            capture(f'{index:02d}-{tab}-rotated-1080')
        qa.tap('Tab', settle=.5)
        expect('Closing inventory stops preview camera', qa.state() == 'Play' and not dev()['preview']['active'], {'state': qa.state(), 'preview': dev()['preview']})

        qa.goto('basic_general')
        qa.tap('e', settle=.4)
        qa.wait(lambda: qa.state() == 'Dialogue', 5, what='real E opens Mira dialogue')
        for _ in range(2):
            if qa.state() == 'Shop':
                break
            qa.activate('choice0', max_tabs=30)
        qa.wait(lambda: qa.state() == 'Shop', 5, what='dialogue opens Basic General')
        layout = qa.ui()
        offers = visible_ids('merchant-item-', layout)
        browser, details = qa.el(layout, 'merchant-browser')['bounds'], qa.el(layout, 'merchant-detail')['bounds']
        expect('Merchant has expanded scrollable stock left and detailed inspector right', len(offers) >= 20 and details[0] >= browser[0] + browser[2] - 3, {'offers': len(offers), 'browser': browser, 'details': details})
        first = qa.el(layout, offers[0])['bounds']
        wheel('merchant-scroll', 1, 7)
        after = qa.el(qa.ui(), offers[0])['bounds']
        expect('Merchant list responds to real wheel scrolling', after[1] < first[1] - 10, {'before': first, 'after': after})
        click('merchant-filter-mods')
        click('merchant-item-armour_leg_motor', 'merchant-scroll')
        capture('06-merchant-details-1080')
        click('merchant-filter-supplies')
        click('merchant-item-water_flask', 'merchant-scroll')
        before = qa.snap()['session']
        click('merchant-trade')
        qa.wait(lambda: qa.qty('water_flask') == before['quantities']['water_flask'] + 1, what='flask purchase commit')
        after_buy = qa.snap()['session']
        trade_state = dev()['session']
        expect('Flask purchase preserves the city objective and trade counter', after_buy['boughtFlask'] and trade_state['purchases'] == 1 and trade_state['sales'] == 0, trade_state)
        expect('Flask purchase is atomic', after_buy['credits'] == before['credits'] - 4 and after_buy['quantities']['water_flask'] == before['quantities']['water_flask'] + 1, {'before': before['credits'], 'after': after_buy['credits']})
        click('merchant-tab-sell')
        click('merchant-filter-all')
        click('merchant-item-scrap_coil', 'merchant-scroll')
        before = qa.snap()['session']
        click('merchant-trade')
        qa.wait(lambda: qa.qty('scrap_coil') == before['quantities']['scrap_coil'] - 1, what='scrap sale commit')
        after_sell = qa.snap()['session']
        trade_state = dev()['session']
        expect('Scrap sale preserves the city objective and trade counter', after_sell['soldScrap'] and after_sell['boughtFlask'] and trade_state['purchases'] == 1 and trade_state['sales'] == 1, trade_state)
        expect('Scrap sale is atomic', after_sell['credits'] == before['credits'] + 1 and after_sell['quantities']['scrap_coil'] == before['quantities']['scrap_coil'] - 1, {'before': before['credits'], 'after': after_sell['credits']})
        qa.cmd('resize', width=1280, height=720)
        qa.PARK = (1255, 25)
        time.sleep(1.5)
        capture('07-merchant-1280x720')
        qa.tap('Escape', settle=.4)
        qa.wait(lambda: qa.state() == 'Play', what='close merchant')
        qa.tap('Tab', settle=.6)
        click('character-tab-implants')
        click('equipment-implant_head', 'character-scroll')
        click('modification-socket-1', 'equipment-inspector-scroll')
        layout = qa.ui()
        capture('08-implants-1280x720')
        expect('Narrow implants retain reachable nested controls and hide 3D pane', (qa.el(layout, 'augmentation-details') or {}).get('visible') and not (qa.el(layout, 'preview-col') or {}).get('visible'), {'modal': qa.el(layout, 'modal')['bounds'], 'details': qa.el(layout, 'augmentation-details')['bounds']})
        qa.tap('Tab', settle=.4)
        qa.wait(lambda: qa.state() == 'Play', what='close narrow inventory')
        qa.cmd('resize', width=1920, height=1080)
        if args.city_loop:
            with (out / 'city-loop-console.log').open('w') as log:
                route = subprocess.run(['bash', str(ROOT / 'unity/tools/run_native.sh'), str(out / 'run'), 'check_hall_district_city_loop.py'], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=480)
            route_file = out / 'run/city-loop.json'
            report['cityLoop'] = json.loads(route_file.read_text()) if route_file.exists() else {'exitCode': route.returncode}
            expect('Walked city loop preserves dialogue, atomic trading, porch access and Lattice travel', route.returncode == 0 and report['cityLoop'].get('complete'), report['cityLoop'].get('final', report['cityLoop']))
        report['errors'] = qa.log_errors()
        expect('No runtime errors in player log', not report['errors'], report['errors'])
        report['complete'] = True
    except Exception as error:
        report['failure'] = str(error)
        report['traceback'] = traceback.format_exc()
        print(report['traceback'], file=sys.stderr)
        if launched:
            try:
                report['lastSnapshot'] = qa.snap()
                report['lastDevState'] = qa.dev()
                capture('failure-state')
            except Exception as capture_error:
                report['failureCaptureError'] = str(capture_error)
    finally:
        if launched:
            try:
                report['stop'] = qa.stop(timeout=8)
            except Exception as error:
                report['stopError'] = str(error)
            finally:
                try:
                    stopped = subprocess.run(['systemctl', '--user', 'stop', unit + '.scope'], capture_output=True, text=True, timeout=15)
                    report['scopeStop'] = {'exitCode': stopped.returncode, 'message': stopped.stderr.strip()}
                except Exception as stop_error:
                    report['scopeStopError'] = str(stop_error)
        persist()
    print(json.dumps({'complete': report['complete'], 'checks': len(report['checks']), 'report': str(out / 'report.json'), 'failure': report.get('failure')}, indent=2))
    return 0 if report['complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
