"""Native real-input check of the gate names pass (art/gate_names_20261119/README.md): the +X spawn arches are the East
Gate in what the player reads, and "West Gate" stays the -X Berms portal.

1. Menu with a save made before the Berms primer: the Continue summary reads "Arrived at East Gate".
2. In play: the pause panel's button reads "Return to East Gate" and its controls list "R · Return to East Gate"; no
   pause text says West Gate (capture pause-panel). The journal's Ward notes say "R returns to East Gate." (capture).
3. Real R after walking away puts the player back at the spawn arches (x about 43), i.e. the gate the text names.
4. The world map lists "East Gate" (+X) and "West Gate" (-X) and the "You are" line names the East Gate at the spawn.
  ATHEN_EXE=<player> python unity/tools/check_showcase_gate_names.py [OUT]
"""
import json, time
import showcase_qa as S
from showcase_qa import qa, ok, note, cap


def texts(layout):
    return [e.get('text') or '' for e in layout['elements'] if e.get('visible', True)]


def body():
    # ---- 1. menu summary for a save before the primer
    menu_save = S.kit_save(S.OUT / 'save-arrival')
    d = json.loads((menu_save / 'ward-save.json').read_text())
    d['bermsStep'] = 'Approach'; d['orders'] = {'index': -1, 'id': '', 'testFired': [], 'reported': []}
    (menu_save / 'ward-save.json').write_text(json.dumps(d, indent=1))
    S.launch(run='run-menu', save=menu_save)
    qa.wait_menu()
    time.sleep(1.0)
    lay = qa.ui()
    summary = (qa.el(lay, 'continue-summary') or {}).get('text', '')
    ok(summary.startswith('Arrived at East Gate'), 'Continue summary before the primer names the East Gate', summary)
    cap('menu-continue-summary')
    S.stop()

    # ---- 2. pause panel and journal notes
    S.launch(save=S.kit_save(S.OUT / 'save'))
    S.start()
    S.time_set(13)
    p0 = qa.pos()
    ok(abs(p0[0] - 43) < 2.5 and abs(p0[-1]) < 3, 'the game starts at the +X spawn arches', p0)
    qa.tap('Escape', settle=.6)
    ok(qa.state() == 'Paused', 'Escape pauses', qa.state())
    lay = qa.ui()
    reset = (qa.el(lay, 'reset') or {}).get('text', '')
    ok(reset == 'Return to East Gate', 'pause button reads "Return to East Gate"', reset)
    all_text = texts(lay)
    ok(any('R · Return to East Gate' in t for t in all_text), 'pause controls list reads "R · Return to East Gate"',
       [t for t in all_text if 'Return to' in t][:3])
    ok(not any('West Gate' in t for t in all_text), 'no pause-panel text says West Gate', [t for t in all_text if 'West Gate' in t][:3])
    cap('pause-panel')
    qa.tap('Escape', settle=.6)
    qa.wait(lambda: qa.state() == 'Play', 5, what='Play')

    qa.tap('j', settle=.8)
    try:
        qa.activate('journal-tab-notes', max_tabs=30)
    except AssertionError as e:
        note('could not focus the Ward notes tab with Tab', str(e))
    time.sleep(.5)
    lay = qa.ui()
    notes = (qa.el(lay, 'journal-notes-text') or {}).get('text', '')
    ok('R returns to East Gate.' in notes and 'West Gate' not in notes, 'Ward notes say "R returns to East Gate."', notes[-120:])
    cap('journal-ward-notes')
    for _ in range(3):
        if qa.state() == 'Play':
            break
        qa.tap('Escape', settle=.5)

    # ---- 3. R returns to the arches the text names
    qa.release_all()
    qa.hold(['a'], 1.6)
    time.sleep(.4)
    p1 = qa.pos()
    note('walked away from the spawn', p1)
    qa.tap('r', settle=.8)
    p2 = qa.pos()
    ok(S.dist(p2, [43, 0, 0]) < 1.0 and S.dist(p1, [43, 0, 0]) > 1.5, 'real R returns the player to the East Gate spawn (+X)', {'away': p1, 'after_r': p2})

    # ---- 4. world map labels
    qa.tap('m', settle=1.0)
    lay = qa.ui()
    east = qa.el(lay, 'map-label-city:barred_gates') or {}
    west = qa.el(lay, 'map-label-berms:west_gate') or {}
    all_text = texts(lay)
    ok(east.get('text') == 'East Gate', 'map label at the +X arches reads East Gate', east.get('text'))
    note('West Gate label on the city view (may be decluttered off-screen)', west.get('text'))
    ok(any(t.startswith('Ward · ') and 'East Gate' in t for t in all_text), '"You are" names the East Gate at the spawn',
       [t for t in all_text if t.startswith('Ward · ')][:2])
    if east.get('bounds') and west.get('bounds'):
        ok(east['bounds'][0] > west['bounds'][0], 'East Gate label is east (right) of the West Gate label on the north-up map', {'east': east['bounds'], 'west': west['bounds']})
    cap('map-east-gate')
    qa.tap('m', settle=.6)
    S.time_set(20.5)
    qa.tap('Escape', settle=.6)
    cap('pause-panel-night')
    qa.tap('Escape', settle=.6)


S.run(body)
