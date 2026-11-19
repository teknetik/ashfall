"""Native real-input check of the world map (art/showcase_20261119/world_map/README.md, test plan 1-9), run on a COPY of
Carl's real save (~/.config/unity3d/Free Column/Athen Hill/ward-save.json is only read), which also proves an old save
still continues on this build.
  ATHEN_EXE=<player> python unity/tools/check_showcase_world_map.py [OUT]
"""
import json, math, time
import showcase_qa as S
from showcase_qa import qa, ok, note, cap

SAVE = S.carl_save_copy(S.OUT / 'save')
ORIG = json.loads(S.CARL_SAVE.read_text())


def m():
    return S.mapstate()


def site_ids(st):
    return sorted(x for x in st['discovered'] if x.startswith('site:'))


def move(x, y):
    from Xlib import X
    from Xlib.ext import xtest
    d = qa._display()
    o = d.screen().root.translate_coords(qa.window(), 0, 0)
    xtest.fake_input(d, X.MotionNotify, x=o.x + int(x), y=o.y + int(y))
    d.sync(); time.sleep(.08)


def wheel(n, up=True):
    from Xlib import X
    from Xlib.ext import xtest
    d = qa._display()
    for _ in range(n):
        b = 4 if up else 5
        xtest.fake_input(d, X.ButtonPress, b); xtest.fake_input(d, X.ButtonRelease, b); d.sync(); time.sleep(.06)


def body():
    S.launch(save=SAVE)
    S.start()
    s = S.snap()
    ok(s['session']['state'] == 'Play' and s['session']['credits'] == ORIG['credits'], "Carl's save (copy) continues on this build", {'credits': (s['session']['credits'], ORIG['credits']), 'version': ORIG['version']})
    S.report['carlSave'] = {'version': ORIG['version'], 'orders': ORIG.get('orders'), 'flags': ORIG.get('city', {}).get('flags'), 'journal': ORIG.get('journal')}
    S.time_set(13)
    st = m()
    ok(st.get('installed'), 'world map installed', st.get('survey'))
    note('discovered on load', st['discovered'])
    ok(site_ids(st) == ['site:machine_depot'], 'old save loads with only the machine depot among the Berms sites', site_ids(st))
    note('survey', st['survey'])

    # ---- 1-2. M opens and closes, Esc closes to Play
    qa.tap('m', settle=.8)
    st = m(); s = S.snap()
    ok(s['session']['state'] == 'Map' and st['open'], 'M opens the map', s['session']['state'])
    ok(s['cursor']['lockState'] != 'Locked' and s['cursor']['visible'], 'map frees the cursor', s['cursor'])
    ok(s['session']['focused'] == 'map-viewport', 'the sheet has keyboard focus', s['session']['focused'])
    title = (qa.el(qa.ui(), 'modal-title') or {}).get('text')
    ok(title and 'map' in title.lower(), 'title reads World map', title)
    shown = [p['name'] for p in st['places'] if p['shown']]
    S.report['shownPlaces'] = shown
    cap('map-open-city')
    lay = qa.ui()
    jack, dock, tbtn = (qa.el(lay, 'map-label-city:lattice_jack') or {}), (qa.el(lay, 'map-label-city:goods_dock') or {}), (qa.el(lay, 'map-centre-tracked') or {})
    note('labels at the opening scale', {'jack': jack.get('visible'), 'dock': dock.get('visible'), 'jackBounds': jack.get('bounds'), 'dockBounds': dock.get('bounds')})
    if jack.get('visible') and dock.get('visible'):
        jb, db = jack['bounds'], dock['bounds']
        overl = jb[0] < db[0] + db[2] and db[0] < jb[0] + jb[2] and jb[1] < db[1] + db[3] and db[1] < jb[1] + jb[3]
        ok(not overl, 'Lattice Jack and Node 07 goods dock labels do not overlap', {'jack': jb, 'dock': db})
    else:
        ok(jack.get('visible'), 'declutter keeps the Lattice Jack label over the goods dock', {'jack': jack.get('visible'), 'dock': dock.get('visible')})
    if not m()['tracked']['shown']:
        ok(not tbtn.get('visible'), 'no "Show on the sheet" offer when the tracked mission has no map target', tbtn.get('visible'))
    qa.tap('m', settle=.8)
    ok(qa.state() == 'Play' and S.snap()['cursor']['lockState'] == 'Locked', 'M closes the map, cursor locked', S.snap()['cursor'])
    qa.tap('m', settle=.8); qa.tap('Escape', settle=.8)
    ok(qa.state() == 'Play', 'Esc closes the map to Play (not Paused)', qa.state())

    # ---- 3. drag, wheel, keys
    qa.tap('m', settle=.8)
    lay = qa.ui()
    vp = qa.el(lay, 'map-viewport'); modal0 = (qa.el(lay, 'modal') or {}).get('bounds')
    v0 = m()['view']
    hudb = (qa.el(lay, 'hud') or {}).get('bounds') or [0, 0, 1920, 1080]
    sc = S.snap()['width'] / hudb[2]
    cx, cy = (vp['bounds'][0] + vp['bounds'][2] / 2) * sc, (vp['bounds'][1] + vp['bounds'][3] / 2) * sc
    qa.focus(center=False); move(cx, cy); qa.button(1, True)
    for i in range(1, 11):
        move(cx + 20 * i, cy + 8 * i)
    qa.button(1, False); time.sleep(.4)
    v1 = m()['view']; modal1 = (qa.el(qa.ui(), 'modal') or {}).get('bounds')
    ok(v1['centre'] != v0['centre'], 'drag pans the sheet', {'before': v0['centre'], 'after': v1['centre']})
    ok(modal1 == modal0, 'drag does not move the window', {'before': modal0, 'after': modal1})
    move(cx, cy); wheel(4, True); time.sleep(.3)
    v2 = m()['view']
    ok(v2['scale'] > v1['scale'], 'wheel up zooms in', (v1['scale'], v2['scale']))
    qa.hold('Right', 1.0); v3 = m()['view']
    ok(v3['centre'] != v2['centre'], 'arrow keys pan', (v2['centre'], v3['centre']))
    qa.tap('f', settle=.4); vf = m()['view']
    qa.tap('c', settle=.4); vc = m()['view']
    p = S.snap()['player']['position']
    ok(vf['scale'] < v2['scale'], 'F shows the whole sheet', (v2['scale'], vf['scale']))
    ok(math.hypot(vc['centre'][0] - p[0], vc['centre'][1] - p[2]) < 5, 'C centres on the player', {'centre': vc['centre'], 'player': [p[0], p[2]]})
    tr = m()['tracked']
    S.report['tracked'] = tr
    if tr['shown']:
        qa.tap('t', settle=.4); vt = m()['view']
        ok(math.hypot(vt['centre'][0] - tr['world'][0], vt['centre'][1] - tr['world'][1]) < 5, 'T centres on the tracked target', {'centre': vt['centre'], 'tracked': tr})
    else:
        note('no tracked marker in this save', tr)
    cap('map-zoomed')
    qa.tap('Escape', settle=.8)

    # ---- 4. discovery of a Berms site, autosave
    before = set(m()['discovered'])
    qa.goto('berms_relay_knoll'); qa.view('follow'); time.sleep(2.5)
    new = sorted(set(m()['discovered']) - before)
    notice = S.snap()['session']['notice']
    ok(any('relay' in x for x in new), 'walking into the relay knoll discovers its site', {'new': new, 'notice': notice})
    ok('map' in (notice or '').lower(), 'discovery notice mentions the map', notice)
    cap('map-discovery-notice')
    time.sleep(2)
    saved = json.loads((SAVE / 'ward-save.json').read_text())
    ok(any('relay' in x for x in (saved.get('map') or {}).get('discovered', [])), 'autosave writes the discovery into the save', (saved.get('map') or {}).get('discovered'))

    # ---- 5. waystation and respawn ring
    qa.goto('berms_waystation'); qa.view('follow'); time.sleep(1)
    try:
        qa.walk_to(-266, 52, tol=3, timeout=15)
    except TimeoutError:
        pass
    time.sleep(1.5)
    st = m()
    ok('waystation:berms_mid' in st['discovered'], 'walking into the waystation camp records it', [x for x in st['discovered'] if 'way' in x])
    ok(st['respawn'] == 'waystation:berms_mid', 'respawn point is the found waystation when it is nearer', st['respawn'])
    qa.tap('m', settle=.8); cap('map-waystation'); qa.tap('m', settle=.6)

    # ---- 6. tracked marker never on a live droid
    tr = m()['tracked']
    enemies = [e['position'] for e in S.snap()['combat']['enemies'] if e['alive']]
    if tr['shown'] and tr['world']:
        close = [e for e in enemies if math.hypot(e[0] - tr['world'][0], e[2] - tr['world'][1]) < .5]
        ok(not close, 'tracked marker is not a live droid position', {'tracked': tr, 'closeDroids': close})
        note('tracked marker', tr)

    # ---- 7. knock-down position
    p_before = S.snap()['player']['position']
    downs0 = S.snap()['combat']['downs']
    qa.cmd('damage', amount=5000.0); time.sleep(4)
    st = m()
    ok(S.snap()['combat']['downs'] > downs0 and st['lastDowned'] and math.hypot(st['lastDowned'][0] - p_before[0], st['lastDowned'][1] - p_before[2]) < 3,
       'knock-down recorded where the player went down', {'lastDowned': st['lastDowned'], 'before': p_before, 'after': S.snap()['player']['position']})
    qa.tap('m', settle=.8); cap('map-knockdown'); qa.tap('m', settle=.6)

    # ---- 8. QA commands
    qa.cmd('mapOpen', open=True); ok(qa.state() == 'Map', 'mapOpen {open:true}')
    qa.cmd('mapOpen', open=False); ok(qa.state() == 'Play', 'mapOpen {open:false}')
    qa.cmd('mapDiscover', site='site:mesa_roost') if any(p['id'] == 'site:mesa_roost' for p in m()['places']) else note('no site:mesa_roost id', [p['id'] for p in m()['places'] if p['id'].startswith('site:')])
    try:
        qa.cmd('mapDiscover', site='site:nowhere'); ok(False, 'unknown site id refused')
    except RuntimeError as e:
        ok('Unknown map place' in str(e), 'unknown site id refused', str(e))
    S.report['places'] = m()['places']

    # ---- 9. survey picture at 13:00 and 20:30 (baked: should not change)
    for hour, tag in ((13, '1300'), (20.5, '2030')):
        S.time_set(hour)
        qa.tap('m', settle=.8); qa.tap('f', settle=.4)
        cap(f'map-whole-sheet-{tag}')
        qa.tap('m', settle=.6)
    S.report['survey'] = m()['survey']

    # ---- save and Continue keeps the discoveries
    disc = sorted(m()['discovered'])
    S.stop()
    S.launch(run='run-continue', save=SAVE)
    S.start()
    disc2 = sorted(m()['discovered'])
    ok(set(disc) <= set(disc2), 'quit and Continue keep the discoveries', {'before': disc, 'after': disc2})
    note('Carl original save untouched (mtime)', time.ctime(S.CARL_SAVE.stat().st_mtime))

    # ---- new game: the primer's depot is not discovered by walking out of the gate (native QA fix, 19 Nov 2026)
    S.stop()
    S.launch(run='run-newgame')
    S.start()
    for lm in ('checkpoint_approach', 'checkpoint_road', 'checkpoint_firingline', 'checkpoint_locker'):
        qa.goto(lm); time.sleep(2.0)
    st = m()
    ok('site:machine_depot' not in st['discovered'], 'new game: walking out of the gate does not discover the machine depot before the primer reaches it',
       {'discovered': st['discovered'], 'step': S.snap()['combat'].get('step'), 'notice': S.snap()['session']['notice']})


S.run(body)
