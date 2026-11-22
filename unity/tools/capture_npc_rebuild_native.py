"""Native check and review frames for art/npc_rebuild_20261122 (22 Nov 2026).

  A. A NEW game: no armour worn, none carried, none drawn on the body; the colonist from behind and in front; Linn's new
     greeting and one lore node by real input; Mira sells Field Boots and the starting credits buy them.
  B. A QA save in the Berms-ready state: face, body and conversation cameras of every rebuilt colonist at 13:00 and 20:30.

  ATHEN_EXE=<player> ATHEN_OUT=<folder> python unity/tools/capture_npc_rebuild_native.py
"""
import time
import showcase_qa as S
from showcase_qa import qa, ok, note, cap

ARMOUR = ['field_vest', 'field_boots', 'field_helmet', 'field_armguards', 'field_gloves', 'field_leggings', 'warden_plate_carrier']
CAMERAS = ['cam_npcs_%s_%s' % (n, v) for n in ('linn', 'ossa', 'mira', 'torr', 'vex', 'rell') for v in ('face', 'body')]
CAMERAS += ['cam_npcs_ossa_holster', 'cam_npcs_rell_back']
CAMERAS += ['cam_arms_' + n for n in ('linn', 'brann', 'ossa', 'ossa_2', 'mira', 'torr', 'vex', 'rell', 'rell_2', 'tamsin')]
CAMERAS += ['cam_arms_talk_' + n for n in ('linn', 'brann', 'ossa', 'ossa_2', 'mira', 'torr', 'vex', 'rell', 'rell_2', 'tamsin')]


def click(name):
    layout = qa.ui(); e = qa.el(layout, name)
    if not e or not e.get('visible'):
        return False
    p = (qa.el(layout, 'hud') or {}).get('bounds', [0, 0, layout['width'], layout['height']]); b = e['bounds']
    qa.click_at((b[0] + b[2] / 2 - p[0]) * layout['width'] / p[2], (b[1] + b[3] / 2 - p[1]) * layout['height'] / p[3])
    time.sleep(.5)
    return True


def new_game():
    empty = S.OUT / 'empty-save'; empty.mkdir(parents=True, exist_ok=True)
    for f in empty.glob('*'): f.unlink()
    S.launch(run='new', save=empty)
    S.start()
    S.time_set(13.0); time.sleep(1.0)
    worn = (S.snap().get('combat') or {}).get('wornArmour') or []
    ok(not worn, 'new game: no armour model is drawn on the colonist', worn)
    carried = {i: qa.qty(i) for i in ARMOUR}
    ok(not any(carried.values()), 'new game: no armour in the pack', carried)
    qa.view('follow'); cap('new-game-follow')
    qa.tap('Tab', settle=1.0)
    if click('character-tab-armour'):
        cap('new-game-armour-page')
    qa.tap('Tab', settle=.6)

    qa.goto('oa_hill'); qa.view('follow'); time.sleep(1.2)
    qa.tap('e', settle=1.2)
    ok(qa.state() == 'Dialogue' and S.snap()['interaction']['node'] == 'greeting', "Linn opens on her greeting", S.snap()['interaction'])
    time.sleep(1.0); cap('linn-greeting')
    qa.activate('choice0'); time.sleep(1.5)
    ok(S.snap()['interaction']['node'] == 'hill', 'first choice leads into the lore', S.snap()['interaction']['node'])
    cap('linn-hill')
    qa.activate('choice0'); time.sleep(1.5)
    ok(S.snap()['interaction']['node'] == 'fall', 'on to the Fall', S.snap()['interaction']['node'])
    cap('linn-fall')
    qa.tap('Escape', settle=.8)
    qa.tap('e', settle=1.0)
    ok(S.snap()['interaction']['node'] == 'again', 'she greets a returning player differently', S.snap()['interaction']['node'])
    qa.tap('Escape', settle=.8)

    qa.goto('basic_general'); time.sleep(1.0)
    qa.tap('e', settle=1.0); qa.activate('choice0'); time.sleep(1.0)
    click('merchant-tab-buy'); click('merchant-filter-equipment')
    before = S.snap()['session']['credits']
    found = click('merchant-item-field_boots')
    ok(found, 'Mira stocks Field Boots')
    if found:
        cap('mira-sells-boots')
        click('merchant-trade')
        ok(qa.qty('field_boots') == 1 and S.snap()['session']['credits'] == before - 20, 'Field Boots bought from the starting credits',
           {'before': before, 'after': S.snap()['session']['credits']})
    S.finish_errors = [e for e in S.errors() if 'Exception' in e['text']]
    ok(not S.finish_errors, 'new game: no runtime exceptions', S.finish_errors[:3])
    S.stop()


def portraits():
    S.launch(run='portraits', save=S.kit_save(S.OUT / 'kit-save'))
    S.start()
    for hour, tag in ((13.0, '1300'), (20.5, '2030')):
        S.time_set(hour); time.sleep(1.0)
        for c in CAMERAS:
            try:
                qa.view(c); time.sleep(.5)
                qa.cmd('capture', name=f'{c}-{tag}', settle=0); time.sleep(.4)
                S.report['captures'].append(str(qa.RUN / f'{c}-{tag}.png'))
            except Exception as e:  # noqa: BLE001
                note('camera failed ' + c, str(e))
    qa.view('follow')


def body():
    new_game()
    portraits()


S.run(body)
