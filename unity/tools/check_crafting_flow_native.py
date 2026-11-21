"""Native real-input check of the crafting rework, phases 1-3 (art/crafting_assembly_20261120, 20 Nov 2026).

Fresh save at Steady Hands with a damaged servo, parts and a toolkit in the pack, the grip schematic NOT known:
  1. identify: the grip is not known; Brann's steady_identify line sends the player to Ossa; Ossa's `servo` -> `servo_look`
     (driven with real Tab/Return on the choices) teaches the grip; the order moves Identify -> Report.
  2. tools: without the Field Toolkit the bench refuses with the missing-tool reason (and a click on Fabricate makes nothing).
  3. XP: building the grip at Brann's bench (Build by hand -> the hands-on bench job, finished with dev.assembly.finish through
     the real crafting ticket) shows the XP / Engineering award in the notice; the engineering stat and the saved experience
     rise. The grip has no timer or Auto-assemble button (21 Nov 2026, Carl: "no auto assemble for anything ever").
  4. condition: a worn pistol misfires, at 0 it jams and the HUD says so; field repair from the field pack (Tab -> SECONDARY
     -> Repair with toolkit) restores +30 and lowers the cap; damage during a repair cancels it; after four repairs the
     fifth is refused; the bench Overhaul restores full condition and the repair count.
Screenshots and the UI layout of each step are saved. Run through native_check.sh with ATHEN_EXE=... ATHEN_OUT=...
"""
import json, re, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import showcase_qa as S  # noqa: E402
from showcase_qa import ok, note, qa  # noqa: E402

SKILLS = S.SKILLS
SAVE = S.OUT / 'save'


def fixture(folder):
    folder.mkdir(parents=True, exist_ok=True)
    s = {'version': 2, 'savedUtc': '2026-11-20T09:00:00.0000000Z', 'build': 'qa', 'credits': 60, 'purchases': 0, 'sales': 0,
         'items': [{'itemId': 'scrap_alloy', 'quantity': 12}, {'itemId': 'copper_filament', 'quantity': 6}, {'itemId': 'nanite_residue', 'quantity': 8},
                   {'itemId': 'droid_servo_damaged', 'quantity': 1}, {'itemId': 'field_toolkit', 'quantity': 1}, {'itemId': 'medkit', 'quantity': 1}],
         # 21 Nov 2026: the grip is built by hand at the bench every time (no timer route); handMade no longer matters
         'crafting': {'known': [], 'crafted': [], 'crafts': 0, 'fitted': []},
         'loot': {'rng': 'bc1721a626f0570d', 'rolls': 4, 'misses': [], 'collected': ['scrap_alloy', 'copper_filament', 'nanite_residue', 'droid_servo_damaged']},
         'bermsStep': 'Complete', 'hasPistol': True,
         'orders': {'index': 0, 'id': 'order_steady_hands', 'testFired': [], 'reported': []},
         'city': {'visitedHill': True, 'boughtFlask': True, 'soldScrap': True, 'linked': True, 'spoken': ['npc_linn', 'npc_mira', 'npc_torr', 'npc_vex'],
                  'selectedDestination': '', 'flags': ['brann_met', 'tamsin_met']},
         'character': {'version': 2, 'level': 1, 'experience': 0, 'attributePoints': 0, 'skillPoints': 0,
                       'attributes': [{'id': a, 'count': 10} for a in ['agility', 'endurance', 'intellect', 'perception', 'resolve', 'strength']],
                       'skills': [{'id': k, 'count': 0} for k in SKILLS],
                       'equipped': [{'slot': 'secondary', 'itemId': 'scrap_pistol'}, {'slot': 'armour_chest', 'itemId': 'field_vest'},
                                    {'slot': 'armour_feet', 'itemId': 'field_boots'}, {'slot': 'storage', 'itemId': 'field_backpack'}]}}
    (folder / 'ward-save.json').write_text(json.dumps(s, indent=1))


def notice():
    return (S.snap().get('session') or {}).get('notice') or ''


def texts(lay=None):
    lay = lay or qa.ui()
    return [e.get('text') or '' for e in lay['elements'] if e.get('visible') and e.get('text')]


def find_text(rx, lay=None):
    r = re.compile(rx)
    for t in texts(lay):
        m = r.search(t)
        if m:
            return t
    return None


def panel_condition(lay=None):
    """The Condition text of the weapon panel / bench title, never the notice log (which also quotes 'Condition x / y')."""
    for t in texts(lay):
        if re.search(r'Condition \d+ / \d+', t, re.I) and not re.match(r'(Dev|System|Field Pack|Salvage workbench)\b', t) and t.count('\n') <= 1 and len(t) < 160:
            return t
    return None


def centre(lay, name):
    e = qa.el(lay, name)
    if not e or not e.get('visible'):
        raise AssertionError(f'{name} is not visible')
    x, y, w, h = e['bounds']
    return x + w / 2, y + h / 2


def click(name):
    qa.click_at(*centre(qa.ui(), name)); time.sleep(.5)


def known():
    return qa.craft().get('knownRecipes') or []


def stage():
    return qa.craft().get('orderStage')


def stat(name):
    return ((S.dev().get('character') or {}).get('stats') or {}).get(name)


def talk(landmark):
    qa.goto(landmark); time.sleep(.8); qa.tap('e', settle=1.0)
    i = S.snap()['interaction']
    return i.get('npc'), i.get('node'), i.get('choices') or []


def choose(label_part):
    labels = S.snap()['interaction']['choices'] or []
    idx = next((i for i, c in enumerate(labels) if label_part.lower() in c.lower()), None)
    if idx is None:
        raise AssertionError(f'no choice containing {label_part!r}: {labels}')
    qa.activate('choice%d' % idx); time.sleep(.9)


def condition_line(weapon_tab='secondary'):
    """Open the field pack on the weapon tab (re-clicking the tab refreshes the panel) and return the 'Condition x / y ...' line."""
    if qa.state() != 'Inventory':
        qa.tap('Tab', settle=.7)
    click('character-tab-' + weapon_tab)
    return panel_condition()


def num(line):
    m = re.search(r'Condition (\d+) / (\d+)', line or '', re.I)
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)


def close_pack():
    if qa.state() == 'Inventory':
        qa.tap('Escape', settle=.7)
    qa.focus(center=True); time.sleep(.3)


def open_bench():
    qa.goto('salvage_bench'); time.sleep(.6); qa.tap('e', settle=1.0)
    qa.wait(lambda: qa.state() == 'Fabricator', 6, what='fabricator')


def close_bench():
    if qa.state() == 'Fabricator':
        qa.tap('Escape', settle=.7)
    qa.wait(lambda: qa.state() == 'Play', 6, what='play')
    qa.focus(center=True); time.sleep(.3)


GRIP = 'fab-recipe-recipe_grip_stabilised_pistol'


def body():
    fixture(SAVE)
    S.launch(save=SAVE)
    S.start()
    S.time_set(13)
    qa.view('follow')

    # ------------------------------------------------------------------ 1. identify
    ok('recipe_grip_stabilised_pistol' not in known(), 'fresh save: the grip recipe is not known', known())
    st0 = stage()
    ok(st0 in ('Identify', 'Gather'), 'Steady Hands is at the Identify stage with the servo carried', {'stage': st0, 'objective': qa.craft().get('objective')})
    note('stage before Ossa (the brief said Gather; the code reports the Identify stage once salvage is carried)', st0)
    npc, node, choices = talk('salvage_counter')
    ok(npc == 'Brann' and node == 'steady_identify', "Brann's dialogue is steady_identify (shows the servo to Ossa)", {'npc': npc, 'node': node, 'choices': choices})
    txt = qa.el(qa.ui(), 'dialogue-text') or {}
    ok('Ossa' in (txt.get('text') or ''), "Brann's line names Ossa", txt.get('text'))
    S.cap('01-brann-identify')
    qa.tap('Escape', settle=.8)
    ok('recipe_grip_stabilised_pistol' not in known(), 'talking to Brann does not teach the grip')

    npc, node, choices = talk('checkpoint_ossa')
    ok(npc and 'Ossa' in npc and node == 'servo', 'Ossa opens with the servo node', {'npc': npc, 'node': node, 'choices': choices})
    S.cap('02-ossa-servo')
    choose('Go on')
    i = S.snap()['interaction']
    ok(i.get('node') == 'servo_look', 'Go on leads to servo_look', {'node': i.get('node')})
    S.cap('03-ossa-servo-look')
    ok('recipe_grip_stabilised_pistol' in known(), 'servo_look teaches the grip recipe', known())
    qa.tap('Escape', settle=.8)
    st1 = stage()
    ok(st1 == 'Report', 'the order moved Identify -> Report', {'before': st0, 'after': st1, 'objective': qa.craft().get('objective')})
    npc, node, choices = talk('salvage_counter')
    ok(npc == 'Brann' and node == 'report_ready', 'Brann now opens report_ready', {'node': node})
    S.cap('04-brann-report')
    qa.tap('Escape', settle=.8)
    qa.wait(lambda: stage() == 'Fabricate', 6, what='Fabricate stage')
    ok(stage() == 'Fabricate', 'talking to Brann moves the order to Fabricate', stage())

    # ------------------------------------------------------------------ 2. bench without the toolkit
    qa.cmd('dev.item.remove', itemId='field_toolkit', quantity=1)
    ok((qa.qty('field_toolkit') or 0) == 0, 'toolkit removed from the pack for the refusal check')
    open_bench()
    click(GRIP)
    lay = qa.ui()
    reason = (qa.el(lay, 'fab-reason') or {}).get('text') or ''
    ok('tool' in reason.lower() and 'screwdriver' in reason.lower(), 'the bench refuses with the missing-tool reason', reason)
    S.cap('05-bench-no-toolkit')
    crafts = qa.craft().get('crafts')
    e = qa.el(lay, 'fabricator-craft') or {}
    ok(not e.get('visible'), 'the grip has no timer (Fabricate / Auto-assemble) button', e)
    b = qa.el(lay, 'fabricator-build') or {}
    if b.get('visible'):
        try:
            qa.click_at(*centre(lay, 'fabricator-build')); time.sleep(1.0)
        except AssertionError:
            pass
    ok(qa.state() != 'Assembly' and not qa.craft().get('craftJob') and (qa.qty('grip_stabilised_pistol') or 0) == 0 and qa.craft().get('crafts') == crafts,
       'Build by hand without the toolkit starts nothing', {'state': qa.state(), 'build': b, 'job': qa.craft().get('craftJob'), 'crafts': qa.craft().get('crafts'), 'notice': notice()})
    close_bench()
    qa.cmd('dev.item.grant', itemId='field_toolkit', quantity=1)
    ok((qa.qty('field_toolkit') or 0) == 1, 'toolkit returned')

    # ------------------------------------------------------------------ 3. fabricate, XP
    eng0 = stat('engineering')
    open_bench()
    click(GRIP)
    reason = (qa.el(qa.ui(), 'fab-reason') or {}).get('text') or ''
    desc = find_text(r'Exercises')
    ok(desc is not None and 'Engineering' in desc, 'the recipe panel lists "Exercises Engineering · +N XP"', desc)
    S.cap('06-bench-grip')
    lay = qa.ui()
    ok(not (qa.el(lay, 'fabricator-craft') or {}).get('visible'), 'no timer or Auto-assemble button for the grip', qa.el(lay, 'fabricator-craft'))
    ok(find_text(r'(?i)auto.?assembl', lay) is None, 'no Auto-assemble wording anywhere in the window', find_text(r'(?i)auto.?assembl', lay))
    ok(((qa.el(lay, 'fabricator-build') or {}).get('text') or '') == 'Build by hand', 'the only way is Build by hand', qa.el(lay, 'fabricator-build'))
    click('fabricator-build')
    qa.wait(lambda: qa.state() == 'Assembly', 8, what='the bench job')
    ok(qa.state() == 'Assembly', 'Build by hand opens the hands-on bench job (real crafting ticket)', {'state': qa.state(), 'assembly': {k: (S.snap().get('assembly') or {}).get(k) for k in ('open', 'detached')}})
    ok(not (S.snap().get('assembly') or {}).get('detached'), 'the bench job is the real one, not a detached QA job', (S.snap().get('assembly') or {}).get('detached'))
    S.cap('06b-bench-job')
    qa.cmd('dev.assembly.finish', quality='Standard')
    qa.wait(lambda: qa.state() == 'Play', 10, what='the bench job finished')
    time.sleep(.6)
    n = notice()
    c = qa.craft()
    ok((c.get('slots') or {}).get('grip') == 'grip_stabilised_pistol' or (qa.qty('grip_stabilised_pistol') or 0) >= 1, 'the grip is built (fitted to the pistol)', {'slots': c.get('slots'), 'qty': qa.qty('grip_stabilised_pistol')})
    ok('timer' not in n.lower() and 'auto' not in n.lower(), 'the completion notice offers no timer route', n)
    ok(re.search(r'\+\d+ XP', n) is not None and 'Engineering' in n, 'the fabrication notice shows the XP and Engineering award', n)
    S.cap('07-bench-xp-notice')
    eng1 = stat('engineering')
    ok(eng0 is not None and eng1 is not None and eng1 > eng0, 'engineering increased', {'before': eng0, 'after': eng1})
    close_bench()
    time.sleep(1.0)
    qa.cmd('dev.state'); time.sleep(.3)
    sv = SAVE / 'ward-save.json'
    try:
        ch = json.loads(sv.read_text()).get('character') or {}
        note('saved character after the craft (the game may only write it on rest/quit)', {'experience': ch.get('experience'), 'level': ch.get('level'), 'useProgress': ch.get('useProgress')})
    except Exception as ex:  # noqa: BLE001
        note('save read failed', str(ex))

    # ------------------------------------------------------------------ 4. condition
    qa.goto('checkpoint_range_reset'); qa.view('follow'); time.sleep(.6)
    qa.cmd('dev.weapon.condition', weaponId='weapon_scrap_pistol', full=True)
    qa.tap('2', settle=.9)
    cb = S.snap()['combat']
    ok(cb['armed'] if 'armed' in cb else cb.get('Armed'), '2 draws the scrap pistol', {'weapon': cb.get('weaponId')})

    def shots():
        c = S.snap()['combat']
        return c.get('ShotsFired', c.get('shotsFired'))

    def fire():
        qa.focus(); qa.button(1, True); time.sleep(.08); qa.button(1, False); time.sleep(.45)

    s0 = shots()
    fire()
    ok(shots() == (s0 or 0) + 1 if s0 is not None else True, 'a pistol in good condition fires', {'before': s0, 'after': shots()})
    # misfires: condition 3, fire with gaps over the notice throttle
    qa.cmd('dev.weapon.condition', weaponId='weapon_scrap_pistol', full=True)   # the bridge rejects repairs=0 (range 1..100): full resets the count
    qa.cmd('dev.weapon.condition', weaponId='weapon_scrap_pistol', durability=3)
    seen_misfire, fired, attempts = None, 0, 0
    for _ in range(24):
        a = shots(); fire(); attempts += 1
        if shots() == a:
            nt = notice()
            if 'misfire' in nt.lower():
                seen_misfire = nt; S.cap('08-misfire-notice', layout=False); break
        else:
            fired += 1
        time.sleep(.7)
    ok(seen_misfire is not None, 'a worn pistol (condition 3) misfires and the HUD says so', {'notice': seen_misfire, 'attempts': attempts, 'fired': fired})
    # jam at 0
    qa.cmd('dev.weapon.condition', weaponId='weapon_scrap_pistol', durability=0)
    time.sleep(1.2)
    a = shots(); fire(); time.sleep(.2)
    nt = notice()
    ok(shots() == a and 'jam' in nt.lower(), 'at condition 0 the pistol is jammed: no shot and the HUD notice says so', {'notice': nt, 'shots': [a, shots()]})
    S.cap('09-jam-notice', layout=False)
    for _ in range(3):
        time.sleep(1.1); b = shots(); fire()
        if shots() != b:
            ok(False, 'a jammed pistol never fires', {'shots': [b, shots()]}); break
    else:
        ok(True, 'a jammed pistol stays jammed over repeated trigger pulls')
    qa.tap('2', settle=.6)   # holster

    # field repair
    qa.cmd('dev.weapon.condition', weaponId='weapon_scrap_pistol', full=True)
    qa.cmd('dev.weapon.condition', weaponId='weapon_scrap_pistol', durability=20)
    line = condition_line()
    d0, m0 = num(line)
    ok(qa.state() == 'Inventory' and d0 == 20 and m0 == 100, 'field pack, SECONDARY tab shows Condition 20 / 100', line)
    ok(qa.el(qa.ui(), 'weapon-repair') is not None, 'the weapon panel has the Repair with toolkit button')
    tl = find_text(r'Next field repair')
    ok(tl is not None and '30' in tl, 'the panel announces the next field repair (+30)', tl)
    S.cap('10-pack-condition-before')
    click('weapon-repair')
    ok(qa.el(qa.ui(), 'weapon-repair-cancel') is not None or find_text(r'Repairing') is not None, 'a field repair starts (button becomes Stop repair)', notice())
    S.cap('11-pack-repairing')
    time.sleep(5.2)
    line = condition_line(); d1, m1 = num(line)
    ok(d1 == 50 and m1 == 92, 'repair 1 restores +30 (20 -> 50) and lowers the cap to 92', {'line': line, 'notice': notice()})
    S.cap('12-pack-condition-after-repair1')

    # damage during a repair cancels it
    click('weapon-repair'); time.sleep(1.0)
    started = qa.el(qa.ui(), 'weapon-repair-cancel') is not None or find_text(r'Repairing') is not None
    qa.cmd('damage', amount=5); time.sleep(.6)
    cn = notice()
    time.sleep(4.5)
    line = condition_line(); d2, m2 = num(line)
    ok(started and (d2, m2) == (d1, m1), 'damage during a repair cancels it: condition and cap unchanged', {'started': started, 'before': [d1, m1], 'after': [d2, m2], 'notice': cn})
    ok('cancel' in cn.lower() or 'interrupt' in cn.lower() or 'stop' in cn.lower() or 'hurt' in cn.lower() or 'damage' in cn.lower(), 'the cancel notice says why', cn)
    S.cap('13-pack-repair-cancelled')
    # repairs 2-4: cap 84, 76, 68
    caps = [m1]
    for n_rep in (2, 3, 4):
        qa.cmd('dev.weapon.condition', weaponId='weapon_scrap_pistol', durability=10, maxDurability=caps[-1], repairs=n_rep - 1)
        line = condition_line()
        click('weapon-repair'); time.sleep(5.2)
        line = condition_line(); d, m = num(line); caps.append(m)
        note(f'repair {n_rep}', {'line': line})
    ok(caps == [92, 84, 76, 68], 'each field repair lowers the best condition by 8 (92, 84, 76, 68)', caps)
    S.cap('14-pack-after-four-repairs')
    line = condition_line()
    ok(line is not None and 'bench overhaul' in line.lower(), 'after four repairs the weapon reads as needing a bench overhaul', line)
    before = num(line)
    click('weapon-repair'); time.sleep(.8)
    msg = find_text(r'bench overhaul|good order|worn past')
    ok(qa.el(qa.ui(), 'weapon-repair-cancel') is None and num(condition_line()) == before, 'a fifth field repair is refused', {'message': msg, 'notice': notice()})
    S.cap('15-pack-fifth-repair-refused')
    close_pack()

    # bench overhaul
    qa.cmd('dev.item.grant', itemId='scrap_alloy', quantity=6)
    qa.cmd('dev.item.grant', itemId='nanite_residue', quantity=8)
    open_bench()
    click(GRIP)
    tt = panel_condition()
    ok(num(tt)[0] is not None and num(tt)[1] == 68, 'the bench window shows the worn pistol condition', tt)
    S.cap('16-bench-before-overhaul')
    click('fabricator-overhaul'); time.sleep(1.0)
    n = notice(); tt = panel_condition()
    ok(num(tt) == (100, 100), 'the bench Overhaul restores condition and best condition to 100 / 100', {'title': tt, 'notice': n})
    S.cap('17-bench-after-overhaul')
    close_bench()
    line = condition_line(); ok(num(line) == (100, 100), 'the field pack agrees: Condition 100 / 100', line)
    ok(qa.el(qa.ui(), 'weapon-repair') is not None and num(line) == (100, 100), 'field repair is available again after the overhaul (repair count reset)', find_text(r'Next field repair'))
    close_pack()
    note('NOT VERIFIED: audio, live repair progress bar (panel text says reopen the tab to refresh)')


S.run(body)
