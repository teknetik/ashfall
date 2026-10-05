"""Native real-input check of the walk-in Field Supply (5 Oct 2026).

Continues a prepared save (pistol carried, primer complete, 200 credits), then with real keyboard input: walks from the
porch through the open loading bay to Tamsin's counter, talks to her (first-visit opening, the magazine branch), opens
her counter (Field Supply stock only: packs, med kits, nano recharges; no flask, no parts), buys nano recharge cells, a
medkit and a canvas rucksack, downloads a digital magazine from the MAGAZINES shelf (credits only, schematics learned,
nothing carried), sells the rucksack back, then uses the medkit on hotbar 3 (refused at full health, heals a measured
wound) and a nano recharge on hotbar 4 (refills and overclocks; 5 Oct 2026: the default hotbar), and checks that Brann's bench lists the magazine's
schematics. Captures the review cameras at 13:00 and 20:30 and first-person views.

  uv run --offline --with python-xlib --with pillow python unity/tools/check_field_supply_native.py OUT
"""
import json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'unity/evidence/gameplay-v2/20260930-reqa2'))
import qa  # noqa: E402

out = Path(sys.argv[1]).resolve(); out.mkdir(parents=True, exist_ok=True)
save = out / 'save'; save.mkdir(exist_ok=True)
(save / 'ward-save.json').write_text(json.dumps({
    'version': 3, 'savedUtc': '2026-10-05T01:00:00Z', 'build': 'qa', 'credits': 200, 'purchases': 0, 'sales': 0,
    'items': [{'itemId': 'scrap_alloy', 'quantity': 2}, {'itemId': 'field_toolkit', 'quantity': 1}],
    'crafting': {'known': [], 'crafted': [], 'crafts': 0, 'fitted': []},
    'bermsStep': 'Complete', 'hasPistol': True, 'orders': {'index': 1, 'id': 'order_kit_helmet', 'testFired': [], 'reported': ['order_steady_hands']},
    'city': {'visitedHill': True, 'boughtFlask': True, 'soldScrap': True, 'linked': True,
             'spoken': ['npc_linn', 'npc_mira', 'npc_torr', 'npc_vex'], 'selectedDestination': '', 'flags': ['brann_met']},
    # a starting character: issue backpack, vest and boots worn, pistol in the secondary slot (without the backpack the
    # 5 kg base storage cannot take a 1.9 kg rucksack, which the counter correctly refuses)
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


def inter():
    return qa.snap()['interaction']


def credits():
    return qa.snap()['session']['credits']


def rows():
    return [e['name'] for e in qa.ui()['elements'] if e.get('visible') and e.get('enabled') and (e.get('name') or '').startswith('merchant-item-')]


def merchant_select(item_id):
    """Real keyboard: only the selected stock row is a Tab stop; arrows move between rows (native_client.select_merchant_item)."""
    rs = rows(); target = 'merchant-item-' + item_id
    assert target in rs, ('stock row absent', target, rs)
    for _ in range(40):
        f = qa.snap()['session']['focused']
        if f in rs: break
        qa.tap('Tab', settle=.15)
    else: raise AssertionError('could not keyboard-focus the merchant stock')
    for _ in range(abs(rs.index(target) - rs.index(f))): qa.tap('Down' if rs.index(target) > rs.index(f) else 'Up', settle=.15)
    assert qa.snap()['session']['focused'] == target, ('arrows focused', qa.snap()['session']['focused'], target)
    qa.tap('Return', settle=.3)


# shop root (18.1, 0, -9), yaw -90: world = (18.1 - local z, y, -9 + local x)
def W(x, z):
    return [18.1 - z, 0.5, -9 + x]


PORCH, INSIDE, COUNTER = W(-0.6, 2.2), W(-0.6, -0.9), W(0.45, -2.7)


def goto(landmark, at):
    qa.goto(landmark)
    qa.wait(lambda: qa.dist_xz(qa.pos(), at) < .35, 5, what='teleport to ' + landmark)
    time.sleep(.3)


qa.launch(out / 'run', save_dir=save)
try:
    qa.wait_menu(); qa.focus(); qa.tap('Return')
    qa.wait(lambda: qa.state() == 'Play', 40, what='Play after Continue')
    qa.release_all()
    qa.cmd('timeSet', hour=13); qa.cmd('timePause', paused=True)

    # porch -> open bay -> counter, on foot
    goto('field_supply', PORCH); qa.view('follow')
    qa.face(INSIDE[0], INSIDE[2]); time.sleep(.5)
    qa.capture('porch-bay', layout=False)
    ok('Tamsin' not in (inter()['prompt'] or ''), 'no talk prompt from the street', inter()['prompt'])
    qa.walk_to(INSIDE[0], INSIDE[2], tol=.5)
    qa.capture('walk-in', layout=False)
    qa.walk_to(COUNTER[0], COUNTER[2], tol=.45)
    ok(qa.dist_xz(qa.pos(), COUNTER) < .6, 'walked from the porch through the bay to the counter', {'pos': qa.pos(), 'counter': COUNTER})
    ok('Talk to Tamsin' in (inter()['prompt'] or ''), 'Tamsin offers the E prompt at the counter', inter()['prompt'])

    # dialogue: first visit -> the magazine branch -> her counter
    qa.tap('e'); qa.wait(lambda: qa.state() == 'Dialogue', 5, what='dialogue')
    i = inter(); ok(i['npc'] == 'Tamsin' and i['node'] == 'first_visit', 'Tamsin opens with her first-visit line', i)
    qa.capture('tamsin-first-visit')
    qa.activate('choice1'); time.sleep(.5); i = inter()
    ok(i['node'] == 'magazines', '"What\'s on the magazine shelf?" explains the digital magazines', i)
    qa.activate('choice0'); time.sleep(.6)
    ok(qa.state() == 'Shop' and inter()['shop'] == 'Field Supply', '"Show me the shelf." opens the Field Supply counter', inter())
    ok('tamsin_met' in (inter().get('flags') or []), 'the first visit is remembered (story flag)', inter().get('flags'))

    # buy list: field gear only
    qa.activate('merchant-tab-buy'); time.sleep(.3)
    names = set(rows())
    want = {'merchant-item-' + x for x in ('canvas_rucksack', 'frame_pack', 'porter_carrier', 'courier_cargo_rig', 'field_backpack', 'medkit', 'trauma_kit', 'nano_cell', 'nano_surge_pack')}
    ok(want <= names and not names & {'merchant-item-water_flask', 'merchant-item-scrap_alloy', 'merchant-item-mag_packcraft_12'},
       'Field Supply sells packs, med kits and nano recharges (no flask, no parts, no magazines in the list)', sorted(names))
    qa.capture('shop-buy')
    c0 = credits()
    merchant_select('nano_cell'); qa.activate('merchant-trade'); qa.activate('merchant-trade')
    ok((qa.qty('nano_cell') or 0) == 2 and credits() == c0 - 12, 'bought two nano recharge cells (6 cr each)', {'cells': qa.qty('nano_cell'), 'credits': credits()})
    merchant_select('medkit'); qa.activate('merchant-trade')
    ok((qa.qty('medkit') or 0) == 1, 'bought a medkit', {'medkit': qa.qty('medkit'), 'credits': credits()})
    merchant_select('canvas_rucksack'); qa.activate('merchant-trade')
    ok((qa.qty('canvas_rucksack') or 0) == 1, 'bought a stitched canvas rucksack', {'rucksack': qa.qty('canvas_rucksack'), 'credits': credits()})
    qa.capture('shop-rucksack')

    # magazine shelf
    qa.activate('merchant-tab-magazines'); time.sleep(.4)
    mags = rows()
    ok(len(mags) == 4 and all(m.startswith('merchant-item-mag_') for m in mags), 'the MAGAZINES tab lists the four digital magazines', mags)
    qa.capture('shop-magazines')
    c1 = credits()
    merchant_select('mag_packcraft_12'); qa.capture('shop-magazine-detail'); qa.activate('merchant-trade'); time.sleep(.4)
    known = qa.craft().get('knownRecipes') or []
    ok(credits() == c1 - 18 and {'recipe_canvas_rucksack', 'recipe_pack_side_pouches', 'recipe_pack_hip_belt'} <= set(known),
       'downloading Packcraft Quarterly (18 cr) teaches its three schematics', {'credits': credits(), 'known': known, 'notice': qa.snap()['session']['notice']})
    ok((qa.qty('mag_packcraft_12') or 0) == 0, 'the magazine is downloaded, not carried')
    btn = qa.el(qa.ui(), 'merchant-trade')
    ok(btn and not btn.get('enabled', True) and credits() == c1 - 18, 'the owned magazine cannot be downloaded twice', btn and {'text': btn.get('text'), 'enabled': btn.get('enabled')})
    qa.capture('shop-magazine-owned')

    # sell the rucksack back
    qa.activate('merchant-tab-sell'); time.sleep(.3)
    c2 = credits(); merchant_select('canvas_rucksack'); qa.activate('merchant-trade')
    ok((qa.qty('canvas_rucksack') or 0) == 0 and credits() == c2 + 12, 'Tamsin buys the rucksack back (12 cr)', {'credits': credits()})
    qa.tap('Escape', settle=.6); ok(qa.state() == 'Play', 'Esc closes the counter')

    # hotbar 3 (medkit) and 4 (nano recharge): the default assignments since 5 Oct 2026
    qa.focus()
    h0 = qa.snap()['combat']['health']
    qa.tap('3', settle=.5)
    ok((qa.qty('medkit') or 0) == 1 and 'not hurt' in (qa.snap()['session']['notice'] or ''), 'hotbar 3 at full health uses nothing', {'notice': qa.snap()['session']['notice']})
    qa.cmd('damage', amount=50); time.sleep(.3)
    h1 = qa.snap()['combat']['health']
    qa.tap('3', settle=.5); h2 = qa.snap()['combat']['health']
    ok(h1 < h0 and h2 > h1 + 30 and (qa.qty('medkit') or 0) == 0, 'hotbar 3 uses the medkit on a wound', {'before': h0, 'wounded': h1, 'healed': h2, 'notice': qa.snap()['session']['notice']})
    time.sleep(1.2)
    qa.tap('4', settle=.5); cb = qa.snap()['combat']
    ok((qa.qty('nano_cell') or 0) == 1 and cb.get('nanoOverclocked'), 'hotbar 4 uses a nano recharge and overclocks the regulator', {'cells': qa.qty('nano_cell'), 'nano': cb.get('Nano'), 'overclocked': cb.get('nanoOverclocked'), 'notice': qa.snap()['session']['notice']})
    lay = qa.ui(); s9 = qa.el(lay, 'slot4')
    ok(s9 and s9.get('enabled', True) and 'empty-slot' not in s9['classes'], 'hotbar slot 4 shows the nano recharge', s9 and {'classes': s9['classes'], 'tooltip': s9.get('tooltip')})
    qa.capture('hotbar-nano')

    # Brann's bench lists the downloaded schematics
    qa.goto('salvage_bench'); time.sleep(.6)
    qa.tap('e', settle=.8); ok(qa.state() == 'Fabricator', 'E at Brann\'s bench opens the fabricator')
    lay = qa.ui(); fab = {e.get('name') for e in lay['elements'] if (e.get('name') or '').startswith('fab-recipe-')}
    ok('fab-recipe-recipe_canvas_rucksack' in fab and 'fab-recipe-recipe_courier_cargo_rig' in fab, 'the bench lists the magazine schematics (known and locked)', sorted(fab)[:40])
    qa.capture('bench-packs')
    qa.tap('Escape', settle=.5)

    # views: review cameras at 13:00 and 20:30, first person at the counter
    for cam in ['cam_fs_street', 'cam_fs_bay', 'cam_fs_counter', 'cam_fs_tamsin', 'cam_fs_packwall', 'cam_fs_shelf', 'cam_fs_cabinet', 'cam_fs_inside_out']:
        qa.view(cam); time.sleep(.5); qa.capture(cam + '-h13', layout=False)
    qa.view('follow'); goto('field_supply_counter', COUNTER)
    qa.cmd('cameraBoom', boom=0.0); qa.face(COUNTER[0], COUNTER[2] + 3.0); qa.pitch(4); time.sleep(1)
    qa.capture('fp-counter-h13', layout=False)
    goto('field_supply_shelf', W(-2.3, -1.95)); qa.face(18.1 + 1.95, -9 - 3.38); qa.pitch(8); time.sleep(1)
    qa.capture('fp-shelf-h13', layout=False)
    qa.cmd('cameraBoom', boom=3.0)
    qa.cmd('timeSet', hour=20.5); time.sleep(1.5)
    for cam in ['cam_fs_street', 'cam_fs_bay', 'cam_fs_counter', 'cam_fs_shelf']:
        qa.view(cam); time.sleep(.5); qa.capture(cam + '-h20.5', layout=False)
    tag = [e for e in qa.ui()['elements'] if (e.get('text') or '').startswith('Tamsin') and e.get('visible')]
    qa.view('cam_nf_field_supply'); time.sleep(.5); qa.capture('street-night', layout=False)
    qa.view('follow')
    report['errors'] = qa.log_errors()
    ok(not report['errors'], 'no exceptions in Player.log', report['errors'][:3])
finally:
    print('stop:', qa.stop())
saved = json.loads((save / 'ward-save.json').read_text())
report['savedKnown'] = (saved.get('crafting') or {}).get('known')
ok({'recipe_canvas_rucksack', 'recipe_pack_hip_belt'} <= set(report['savedKnown'] or []), 'the save keeps the downloaded schematics', report['savedKnown'])
report['passed'] = all(c['passed'] for c in checks)
(out / 'report.json').write_text(json.dumps(report, indent=1, default=str))
print('PASSED' if report['passed'] else 'FAILED', sum(c['passed'] for c in checks), '/', len(checks))
sys.exit(0 if report['passed'] else 1)
