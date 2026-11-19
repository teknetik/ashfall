"""Native check of the weather package (art/showcase_20261119/weather/README.md, native test plan).

1. New game: calm, grace, no front allowed before the primer.
2. Continue (primer done): starts calm in grace; each state forced instantly (calm, breezy, gusting, buildup, peak,
   clearing) at 13:00 and 20:30 from cam_hill (city), cam_gate (gate) and cam_bx_relay_knoll (Berms): dev-state values
   asserted (fog, visibility, sand) and captured; a contact sheet per hour.
3. Reduced Motion at the peak: no blowing sand. Esc pause freezes the schedule.
4. One whole front on normal timings (dev.weather.set front): build-up, peak, clearing and back, with Ossa's two radio
   lines (one at build-up, one at clearing).
  ATHEN_EXE=<player> python unity/tools/check_showcase_weather.py [OUT]
"""
import time
import showcase_qa as S
from showcase_qa import qa, ok, note, cap

STATES = ['calm', 'breezy', 'gusting', 'buildup', 'peak', 'clearing']
CAMS = ['cam_hill', 'cam_gate', 'cam_bx_relay_knoll']


def weather():
    return S.dev()['weather']


def sheet(hour_tag, names):
    from PIL import Image, ImageDraw
    tiles = []
    for st in STATES:
        row = []
        for c in CAMS:
            p = qa.RUN / f'weather-{hour_tag}-{st}-{c}.png'
            row.append(p if p.exists() else None)
        tiles.append(row)
    w, h = 480, 270
    out = Image.new('RGB', (w * len(CAMS), h * len(STATES)), (20, 20, 20))
    d = ImageDraw.Draw(out)
    for r, row in enumerate(tiles):
        for c, p in enumerate(row):
            if p:
                with Image.open(p) as im:
                    out.paste(im.convert('RGB').resize((w, h)), (c * w, r * h))
            d.text((c * w + 8, r * h + 6), f'{STATES[r]} {CAMS[c]} {hour_tag}', fill=(255, 255, 0))
    path = S.OUT / f'weather-sheet-{hour_tag}.jpg'
    out.save(path, quality=88)
    S.report['captures'].append(str(path))


def body():
    # ---- 1. new game
    S.launch(run='run-new')
    S.start()
    w = weather()
    ok(w['available'] and w['state'] == 'calm' and w['grace'] and not w['frontAllowed'], 'new game: calm, in grace, no front before the primer',
       {k: w.get(k) for k in ('state', 'grace', 'frontAllowed', 'remaining')})
    S.report['newGame'] = w
    S.stop()

    # ---- 2. continue, forced states
    S.launch(save=S.kit_save(S.OUT / 'save'))
    S.start()
    w = weather()
    ok(w['state'] == 'calm' and w['grace'], 'Continue starts calm in the grace period', {k: w.get(k) for k in ('state', 'grace', 'frontAllowed')})
    values = {}
    for hour, tag in ((13, '1300'), (20.5, '2030')):
        S.time_set(hour)
        for st in STATES:
            qa.cmd('dev.weather.set', state=st, instant=True)
            time.sleep(2.0)
            w = weather()
            values[(tag, st)] = {k: w.get(k) for k in ('state', 'held', 'windStrength', 'visibility', 'haze', 'sand', 'sunDim', 'warmth', 'fogStart', 'fogEnd', 'sandParticles', 'audio')}
            for c in CAMS:
                qa.view(c); time.sleep(.8)
                cap(f'weather-{tag}-{st}-{c}', layout=False)
            qa.view('follow')
        sheet(tag, STATES)
    S.report['values'] = {f'{k[0]}-{k[1]}': v for k, v in values.items()}
    v = {st: values[('1300', st)] for st in STATES}
    ok(all(v[st]['state'] == st and v[st]['held'] for st in STATES), 'each state forced and held', {st: (v[st]['state'], v[st]['held']) for st in STATES})
    ok(v['gusting']['windStrength'] > v['breezy']['windStrength'] > v['calm']['windStrength'] * .99, 'wind strength calm <= breezy < gusting',
       {st: v[st]['windStrength'] for st in ('calm', 'breezy', 'gusting')})
    ok(v['peak']['fogEnd'] < v['buildup']['fogEnd'] < v['breezy']['fogEnd'], 'fog closes in: peak < build-up < breezy', {st: (v[st]['fogStart'], v[st]['fogEnd']) for st in STATES})
    ok(.35 <= v['peak']['visibility'] <= .55, 'front peak visibility about 0.45', v['peak']['visibility'])
    ok(v['peak']['sand'] > .5 and v['calm']['sand'] == 0, 'blowing sand only in the front', {st: v[st]['sand'] for st in STATES})
    note('weather values at 13:00', v)
    # sand particles around the follow camera at the peak (Berms, player height)
    qa.goto('berms_caravan'); qa.view('follow')
    qa.cmd('dev.weather.set', state='peak', instant=True); time.sleep(3)
    w = weather()
    ok(w['sandParticles'] > 0 and w['sandPlaying'], 'peak: blowing sand particles stream around the player', {k: w[k] for k in ('sandParticles', 'sandPlaying')})
    S.time_set(13)
    cap('weather-peak-follow-berms')
    qa.goto('west_gate'); qa.view('follow'); qa.yaw(270); time.sleep(2)
    cap('weather-peak-follow-gate')
    # audio layers (cannot be heard here)
    note('weather audio at the peak', w.get('audio'))

    # ---- 3. Reduced Motion and pause
    qa.tap('Escape', settle=.5); qa.activate('reduced-motion'); qa.tap('Escape', settle=.6)
    time.sleep(4)
    w = weather()
    ok(w['reducedMotion'] and w['sandParticles'] == 0, 'Reduced Motion: no blowing sand at the peak', {k: w[k] for k in ('reducedMotion', 'sandParticles', 'windStrength', 'gust')})
    qa.tap('Escape', settle=.5); qa.activate('reduced-motion'); qa.tap('Escape', settle=.6)
    qa.cmd('dev.weather.reset', instant=True); time.sleep(1)
    qa.cmd('dev.weather.set', state='front'); time.sleep(2)
    r0 = weather()['remaining']
    qa.tap('Escape', settle=.3); time.sleep(3)
    r1 = weather()['remaining']
    qa.tap('Escape', settle=.5)
    ok(abs(r1 - r0) < .3, 'Esc pause freezes the weather schedule', {'before': r0, 'paused': r1})

    # ---- 4. one whole front with its radio lines
    qa.goto('checkpoint_approach'); qa.view('follow'); qa.yaw(270)
    S.time_set(13, pause=False)
    radio = []
    phases = []
    t_end = time.monotonic() + 480
    peak_cap = False
    while time.monotonic() < t_end:
        s = S.snap()
        r = (s['session'].get('radioSpeaker'), s['session'].get('radio'))
        if r[1] and (not radio or radio[-1][1] != r[1]):
            radio.append(r)
        st = s['weather']['state']
        if not phases or phases[-1][0] != st:
            phases.append((st, round(time.monotonic() - (t_end - 480))))
        if st == 'peak' and not peak_cap:
            time.sleep(15); cap('weather-front-peak-follow'); peak_cap = True
        if len(phases) >= 4 and st not in ('buildup', 'peak', 'clearing'):
            break
        time.sleep(1.0)
    S.report['front'] = {'phases': phases, 'radio': radio}
    note('front phases (state, seconds)', phases)
    note('radio during the front', radio)
    names = [p[0] for p in phases]
    ok(names[:3] == ['buildup', 'peak', 'clearing'] and len(names) >= 4, 'a whole front runs build-up -> peak -> clearing -> back', phases)
    ossa = [r for r in radio if r[0] and 'Ossa' in r[0]]
    ok(len(ossa) >= 2, 'radio: Ossa warns at build-up and calls the all-clear', radio)


S.run(body)
