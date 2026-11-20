"""Native first-person frames of the rifle and pistol view models (art/rifle_hands_20261120/README.md).

Continues the showcase kit save (primer done, field rifle primary on 1, scrap pistol on 2) twice: once with bare hands
(field gloves and arm guards unequipped) and once wearing them. At the rifle review stand, looking down range at 13:00
with the HUD hidden, in first person (camera boom 0), each weapon is captured:
  hip, ADS (hold RMB), mid-burst (hold F), walking (hold W), sprinting (hold W + Shift_L), lowered (during the draw).
Frames are 1920x1080 PNGs named <weapon>_<state>_<bare|armour>.png in the run folders, listed in report.json with the
QA read-out at the moment of capture (combat.rifleHands when the build has it).
  ATHEN_EXE=<player> ATHEN_OUT=<folder> python unity/tools/capture_rifle_hands_native.py [OUT]
Run through the native wrapper (lock, memory cap, QA display), like the check_showcase_*.py checks.
"""
import json, time
import showcase_qa as S
from showcase_qa import qa, ok, note

STATES = ['hip', 'ads', 'burst', 'walk', 'sprint', 'lowered']


def save_for(armour):
    folder = S.kit_save(S.OUT / ('save-armour' if armour else 'save-bare'))
    if not armour:
        p = folder / 'ward-save.json'
        s = json.loads(p.read_text())
        eq = s['character']['equipped']
        s['character']['equipped'] = [e for e in eq if e['slot'] not in ('armour_arms', 'armour_hands')]
        s['items'] += [{'itemId': 'field_gloves', 'quantity': 1}, {'itemId': 'field_armguards', 'quantity': 1}]
        p.write_text(json.dumps(s, indent=1))
    return folder


def armed(slot, weapon):
    for _ in range(4):
        c = S.snap()['combat']
        if c['Armed'] and c.get('weaponId') == weapon:
            return True
        qa.tap(slot, settle=.8)
    c = S.snap()['combat']
    return c['Armed'] and c.get('weaponId') == weapon


def holster():
    for _ in range(3):
        c = S.snap()['combat']
        if not c['Armed']:
            return
        qa.tap('1' if c.get('weaponId') == 'weapon_field_rifle' else '2', settle=.8)


def grab(name, during=None, after=.0, hold=.6):
    """Capture (optionally while keys/buttons are held). during: list of ('key', name) / ('button', n)."""
    during = during or []
    qa.focus()
    for kind, v in during:
        (qa.key if kind == 'key' else qa.button)(v, True)
    try:
        time.sleep(hold)
        s = S.snap()
        qa.cmd('capture', name=name, settle=0)
        time.sleep(after or .5)
    finally:
        for kind, v in reversed(during):
            (qa.key if kind == 'key' else qa.button)(v, False)
    S.report['captures'].append({'png': str(qa.RUN / (name + '.png')), 'combat': {k: s['combat'].get(k) for k in
        ('weaponId', 'Armed', 'Aiming', 'rifleViewModelVisible', 'viewModelVisible', 'viewModelAim', 'wornArmour', 'rifleHands')},
        'camera': {k: s['camera'].get(k) for k in ('firstPerson', 'yaw', 'pitch')}, 'speed': s['player'].get('speed')})
    S.save_report()


def stand():
    qa.goto('rifle_stand'); qa.view('follow'); time.sleep(.5)
    qa.cmd('cameraBoom', boom=0.0); qa.yaw(270); qa.pitch(2); time.sleep(.6)


def weapon_set(tag, slot, weapon, suffix):
    stand()
    if not ok(armed(slot, weapon), f'{tag} drawn ({suffix})', S.snap()['combat'].get('weaponId')):
        return
    time.sleep(.6)
    ok(S.snap()['camera'].get('firstPerson'), f'{tag}: first person ({suffix})')
    grab(f'{tag}_hip_{suffix}')
    grab(f'{tag}_ads_{suffix}', during=[('button', 3)], hold=.8)
    grab(f'{tag}_burst_{suffix}', during=[('key', 'f')], hold=.35)
    stand(); armed(slot, weapon); time.sleep(.5)
    grab(f'{tag}_walk_{suffix}', during=[('key', 'w')], hold=.9)
    stand(); armed(slot, weapon); time.sleep(.5)
    grab(f'{tag}_sprint_{suffix}', during=[('key', 'Shift_L'), ('key', 'w')], hold=.9)
    stand(); holster(); time.sleep(.6)
    # lowered: the draw slide (the view model rises over drawSeconds 0.28-0.35 s); captured shortly after the key
    qa.focus(); qa.tap(slot, secs=.05, settle=0); time.sleep(.09)
    s = S.snap(); qa.cmd('capture', name=f'{tag}_lowered_{suffix}', settle=0); time.sleep(.6)
    S.report['captures'].append({'png': str(qa.RUN / f'{tag}_lowered_{suffix}.png'), 'combat': {k: s['combat'].get(k) for k in ('weaponId', 'Armed', 'rifleHands')}})
    holster(); time.sleep(.4)


def one_run(armour):
    suffix = 'armour' if armour else 'bare'
    S.launch(run='run-' + suffix, save=save_for(armour))
    S.start()
    S.time_set(13)
    # reviewHud only works while a dialogue is open; outside one the player logs an InvalidOperationException, which
    # failed this script's no-exceptions check on p2-b1 and p2-b3 (20 Nov 2026). Frames keep the HUD.
    worn = S.snap()['combat'].get('wornArmour') or []
    ok(('field_gloves' in worn and 'field_armguards' in worn) == armour, f'gloves and arm guards {"worn" if armour else "not worn"}', worn)
    weapon_set('rifle', '1', 'weapon_field_rifle', suffix)
    weapon_set('pistol', '2', 'weapon_scrap_pistol', suffix)
    rh = [c for c in S.report['captures'] if isinstance(c, dict) and (c.get('combat') or {}).get('rifleHands')]
    if rh:
        note('rifleHands read-outs', [(c['png'].rsplit('/', 1)[-1], c['combat']['rifleHands']) for c in rh if suffix in c['png']])
    S.stop()


def body():
    one_run(False)
    one_run(True)
    pngs = [c['png'] if isinstance(c, dict) else c for c in S.report['captures']]
    sizes = {}
    for p in pngs:
        try:
            sizes[p.rsplit('/', 1)[-1]] = S.png_stats(p)['size']
        except Exception as e:  # noqa: BLE001
            sizes[p.rsplit('/', 1)[-1]] = 'missing: ' + str(e)[:80]
    ok(len(pngs) == 24 and all(v == (1920, 1080) for v in sizes.values()), '24 first-person frames at 1920x1080', sizes)


S.run(body)
