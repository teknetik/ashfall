"""Native real-input check of the interface package (art/showcase_20261119/interface/README.md, steps 2, 3, 6-10) and the
Settings rows of the combat feel, NPC life and showcase camera packages. The lower-third geometry per colonist is
asserted in check_showcase_camera.py.

Settings: Controls shows Camera shake (100 %), Hit markers and ticks, Conversation camera, Interface (Full); Sound shows
Bark captions. Real Tab/Return turn captions off, the camera off and Interface to Adaptive; they persist over a restart
(same private config) and Reset controls restores camera on / Full. Adaptive: quiet panels fade after ~6.6 s, Left Alt
wakes them, a prompt wakes the key hints; Reduced Motion cuts (no intermediate opacity); photo mode with the Interface row;
top-centre depth never above 2.
  ATHEN_EXE=<player> python unity/tools/check_showcase_interface.py [OUT]
"""
import time
import showcase_qa as S
from showcase_qa import qa, ok, note, cap

SAVE = S.kit_save(S.OUT / 'save')
PANELS = ['identity', 'fieldNotes', 'log', 'keyHints']


def settings_open(tab):
    qa.tap('Escape', settle=.5)
    qa.activate('settings-button')
    qa.activate(tab)
    time.sleep(.4)
    return qa.ui()


def settings_close():
    for _ in range(3):
        if qa.state() == 'Play':
            return
        qa.tap('Escape', settle=.5)


def toggle(name):
    qa.focus_ui(name, max_tabs=80)
    qa.tap('Return', settle=.4)


def body():
    S.launch(save=SAVE)
    S.start()
    S.time_set(13)
    depth_max = [0]

    def sample():
        h = S.hud(); depth_max[0] = max(depth_max[0], (h.get('topCentre') or {}).get('depth', 0)); return h

    # ---- Settings rows
    lay = settings_open('controls-tab')
    rows = {n: qa.el(lay, n) for n in ('camera-shake', 'hit-markers', 'conversation-camera', 'interface-mode', 'camera-shake-value')}
    ok(all(rows[n] and rows[n]['visible'] for n in ('camera-shake', 'hit-markers', 'conversation-camera', 'interface-mode')), 'Controls tab shows Camera shake, Hit markers, Conversation camera, Interface',
       {n: bool(r and r['visible']) for n, r in rows.items()})
    ok((rows['camera-shake-value'] or {}).get('text', '').startswith('100'), 'Camera shake defaults to 100 %', (rows['camera-shake-value'] or {}).get('text'))
    ok((rows['interface-mode'] or {}).get('value') == 'Full', 'Interface defaults to Full', (rows['interface-mode'] or {}).get('value'))
    cap('settings-controls')
    h = S.hud()
    ok(h['conversationCameraSetting'] and h['interfaceMode'] == 'full', 'defaults: conversation camera on, Full', h)
    toggle('conversation-camera')
    ok(S.hud()['conversationCameraSetting'] is False and S.hud()['conversationCamera'] is False, 'Return on Conversation camera turns it off', S.hud())
    qa.focus_ui('interface-mode', max_tabs=80); qa.tap('Return', settle=.4); qa.tap('Home', settle=.2); qa.tap('Down', settle=.2); qa.tap('Return', settle=.5)  # as check_settings_options.choose()
    ok(S.hud()['interfaceMode'] == 'adaptive', 'Interface set to Adaptive with real keys', S.hud()['interfaceMode'])
    qa.activate('sound-tab'); time.sleep(.3)
    lay = qa.ui()
    ok((qa.el(lay, 'bark-captions') or {}).get('visible'), 'Sound tab shows Bark captions')
    toggle('bark-captions')
    ok(S.hud()['barkCaptions'] is False, 'Return on Bark captions turns them off', S.hud())
    cap('settings-sound')
    settings_close()

    # ---- persistence across a restart (same private config)
    S.stop()
    qa.launch(qa.RUN, save_dir=S.OUT / 'save')
    S.start()
    h = S.hud()
    ok(h['conversationCameraSetting'] is False and h['interfaceMode'] == 'adaptive' and h['barkCaptions'] is False, 'settings kept after a restart', h)
    lay = settings_open('controls-tab')
    qa.activate('reset-controls'); time.sleep(.4)
    h = S.hud()
    ok(h['conversationCameraSetting'] is True and h['interfaceMode'] == 'full', 'Reset controls restores camera on and Full', h)
    qa.activate('sound-tab'); toggle('bark-captions')
    settings_close()
    ok(S.hud()['barkCaptions'] is True, 'captions back on')

    # ---- Adaptive
    S.time_set(13)
    qa.goto('hill_tree'); qa.view('follow'); time.sleep(.5)
    qa.cmd('interfaceMode', mode='adaptive')
    time.sleep(8.0)
    h = sample()
    ok(all(p in h['hidden'] for p in PANELS) and 'hotbar' not in h['hidden'], 'Adaptive: quiet panels fade after ~6.6 s (hotbar stays)', h['hidden'])
    cap('adaptive-quiet')
    qa.focus(); qa.key('Alt_L', True)
    time.sleep(.35)
    h = sample()
    qa.key('Alt_L', False)
    ok(not h['hidden'], 'Adaptive: Left Alt brings everything back within 0.35 s', h['hidden'])
    time.sleep(7.5)
    ok(all(p in sample()['hidden'] for p in PANELS), 'Adaptive: hidden again after release', S.hud()['hidden'])
    # a prompt wakes the key hints
    qa.goto('basic_general'); time.sleep(.2); qa.face(8.0, 15.8); time.sleep(.6)
    h = sample()
    ok(S.snap()['interaction']['prompt'] and 'keyHints' not in h['hidden'], 'Adaptive: key hints return while a prompt is offered', {'prompt': S.snap()['interaction']['prompt'], 'hidden': h['hidden']})
    # pack open: everything visible behind it
    qa.tap('Tab', settle=.8)
    h = sample()
    ok(not h['hidden'], 'Adaptive: all panels visible behind an open window', h['hidden'])
    qa.tap('Tab', settle=.6)
    if qa.state() != 'Play':
        qa.tap('Escape', settle=.5)
    # Reduced Motion: cuts, no intermediate opacity
    qa.tap('Escape', settle=.5); qa.activate('reduced-motion'); qa.tap('Escape', settle=.6)
    qa.goto('hill_tree'); time.sleep(.3)
    vals = []
    t_end = time.monotonic() + 9
    while time.monotonic() < t_end:
        vals.append(S.hud()['opacity']); time.sleep(.1)
    mids = [v for o in vals for k, v in o.items() if .02 < v < .98]
    ok(not mids, 'Reduced Motion: opacity jumps 0 <-> 1', {'intermediate': mids[:10], 'samples': len(vals)})
    qa.tap('Escape', settle=.5); qa.activate('reduced-motion'); qa.tap('Escape', settle=.6)
    # photo mode with the Interface row on
    time.sleep(8)
    qa.tap('p', settle=.6)
    for _ in range(12):
        if S.show()['photo']['selected'] == 'Hud':
            break
        qa.tap('Down', settle=.12)
    qa.tap('Return', settle=.5)
    ph = S.show()['photo']
    ok(ph['active'] and ph['hudVisible'], 'photo mode: Interface row shows the HUD', ph)
    cap('photo-mode-hud-shown')
    qa.tap('p', settle=.8)
    ok(not S.show()['photo']['active'] and qa.state() == 'Play', 'photo mode closed cleanly from Adaptive')
    qa.cmd('interfaceMode', mode='full'); time.sleep(.5)
    ok(not S.hud()['hidden'], 'Full mode: every panel shown', S.hud()['hidden'])
    ok(depth_max[0] <= 2, 'top centre never stacks more than radio + notice', depth_max[0])
    note('NOT TESTED: Ctrl-drag of a moved window against the lower third (step 5); needs a hand on the mouse')


S.run(body)
