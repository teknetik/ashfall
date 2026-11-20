"""Native real-input check of the combat feel package (art/showcase_20261119/combat_feel/README.md, test plan 2-7).

Continues a fixture save (primer done, field rifle + scrap pistol, basic armour, Rifle 20) and, with real F / 1 / 2 / RMB
and the bridge only for teleports, camera aim and reads:
  range: pistol shots knock the three plates down -> hit/kill markers, ticks and camera impulses;
  droids: a worker pack at the caravan (berms_caravan): body hits (white), optic hits (weak point, brass, critical flash),
          kills (red, marker.kills follows kills), the FX light cap never exceeded, captures with markers on screen;
  shake: pistol shot angle small, damage taken larger, suppressed with Reduced Motion;
  low vitality: below 35 % the edge appears, a medkit (hotbar 3) clears it;
  bolts: the relay-knoll gunners fire bolts (captures while they shoot).
  ATHEN_EXE=<player> python unity/tools/check_showcase_combat_feel.py [OUT]
"""
import math, time
import showcase_qa as S
from showcase_qa import qa, ok, note, cap

SAVE = S.kit_save(S.OUT / 'save')


def aim_point(p, passes=3):
    for _ in range(passes):
        c = S.snap()['camera']['position']
        dx, dz = p[0] - c[0], p[2] - c[2]
        h = math.hypot(dx, dz)
        qa.yaw(math.degrees(math.atan2(dx, dz)))
        qa.pitch(max(-60, min(60, math.degrees(math.atan2(c[1] - p[1], max(h, .1))))))
        time.sleep(.12)


def draw(slot, weapon):
    for _ in range(4):
        c = S.snap()['combat']
        if c['Armed'] and c.get('weaponId') == weapon:
            return True
        qa.tap(slot, settle=.7)
    c = S.snap()['combat']
    return c['Armed'] and c.get('weaponId') == weapon


def fire_capture(name, secs=.25):
    """Capture while the fire key is held (markers last 0.14-0.38 s)."""
    qa.focus(); qa.key('f', True)
    try:
        time.sleep(secs)
        qa.cmd('capture', name=name, settle=0)
        time.sleep(.6)
    finally:
        qa.key('f', False)
    S.report['captures'].append(str(qa.RUN / (name + '.png')))


def grant(item, n):
    try:
        qa.cmd('dev.item.grant', itemId=item, quantity=n)
    except RuntimeError as e:
        note('grant refused', str(e))


def live(names=None, within=None, centre=None):
    out = []
    for e in S.snap()['combat']['enemies']:
        if not e['alive'] or (names and e['displayName'] not in names):
            continue
        if within and S.dist(e['position'], centre) > within:
            continue
        out.append(e)
    return out


def body():
    S.launch(save=SAVE)
    S.start()
    S.time_set(13)
    S.report['weather'] = S.snap().get('weather')
    f = S.feel()
    ok(f.get('available') and f.get('shake') is not None and f.get('marker') is not None, 'combat feel state present (marker, shake)', {k: f.get(k) for k in ('marker', 'shake', 'fxLightCap')})

    # ---- 1. range plates with the pistol (real 2 and F)
    qa.goto('checkpoint_firingline'); qa.view('follow'); time.sleep(.8)
    qa.cmd('dev.range.raise'); time.sleep(.5)
    for w in ('weapon_scrap_pistol', 'weapon_field_rifle'): qa.cmd('dev.weapon.condition', weaponId=w, full=True)  # Phase 3: condition wears per shot; start every run at full condition
    ok(draw('2', 'weapon_scrap_pistol'), 'pistol drawn with 2 at the range')
    f0 = S.feel()
    for i in range(1, 4):
        qa.view(f'cam_checkpoint_plate{i}'); time.sleep(.3)
        qa.tap('f', .1, settle=.5)
    f1 = S.feel()
    m0, m1 = f0['marker'], f1['marker']
    ok(m1['hits'] + m1['kills'] > m0['hits'] + m0['kills'], 'range: plate shots show hit/kill markers', {'before': m0, 'after': m1})
    ok(m1['ticks'] > m0['ticks'], 'range: marker ticks played', {'before': m0['ticks'], 'after': m1['ticks']})
    ok(f1['shake']['impulses'] > f0['shake']['impulses'], 'range: shots add camera impulses', {'before': f0['shake'], 'after': f1['shake']})
    note('range shake after pistol shots (review cameras)', f1['shake'])
    qa.view('follow')

    # ---- 2. shake values from the follow camera: pistol shot vs damage taken
    qa.goto('checkpoint_firingline'); time.sleep(.6)
    qa.yaw(270); qa.pitch(5); time.sleep(.3)
    qa.tap('f', .1, settle=.15)
    a_shot = S.feel()['shake']
    time.sleep(1.5)
    qa.cmd('damage', amount=25.0); time.sleep(.12)
    a_hurt = S.feel()['shake']
    ok(a_shot['peakAngle'] < .6, 'shake: a pistol shot gives a slight shake (peakAngle under 0.6 deg)', a_shot)
    ok(a_hurt['impulses'] > a_shot['impulses'] and a_hurt['peakAngle'] > a_shot['peakAngle'], 'shake: damage taken adds a stronger impulse', {'shot': a_shot, 'hurt': a_hurt})
    note('shake after damage (lastAngle/peak in degrees)', a_hurt)

    # ---- 3. low vitality and medkit
    for _ in range(6):   # armour soaks part of each hit: step down until under 30 %
        d = S.dev()['combat']
        if d['health'] < d['maxHealth'] * .3:
            break
        qa.cmd('damage', amount=float(max(5, d['health'] - d['maxHealth'] * .22))); time.sleep(.4)
    time.sleep(1.2)
    lv = S.feel()['marker']['lowVitality']
    ok(lv > 0, 'low vitality: edge shows below 35 %', {'health': S.dev()['combat']['health'], 'lowVitality': lv})
    cap('low-vitality-edge')
    hp0 = S.snap()['combat']['health']
    qa.tap('3', settle=1.5)
    hp1 = S.snap()['combat']['health']
    time.sleep(1.0)
    ok(hp1 > hp0, 'medkit on hotbar 3 heals', {'before': hp0, 'after': hp1})
    if S.dev()['combat']['health'] / S.dev()['combat']['maxHealth'] > .35:
        ok(S.feel()['marker']['lowVitality'] == 0, 'low vitality: edge clears after healing', S.feel()['marker'])
    else:
        qa.tap('3', settle=1.5)
        note('one medkit did not lift vitality over 35 %', S.dev()['combat']['health'])

    # ---- 4. Reduced Motion suppresses shake (pause menu, real input)
    qa.tap('Escape', settle=.5)
    ok(qa.state() == 'Paused', 'Esc opens the pause menu')
    qa.activate('reduced-motion')
    qa.tap('Escape', settle=.6)
    ok(S.snap()['session']['reducedMotion'], 'Reduced Motion on from the pause menu')
    qa.yaw(270); qa.pitch(5)
    qa.tap('f', .1, settle=.15)
    s_rm = S.feel()['shake']
    ok(s_rm['suppressed'] and s_rm['lastAngle'] == 0, 'shake: suppressed under Reduced Motion', s_rm)
    qa.tap('Escape', settle=.5); qa.activate('reduced-motion'); qa.tap('Escape', settle=.6)
    ok(not S.snap()['session']['reducedMotion'], 'Reduced Motion back off')

    # ---- 5. worker packs: body hits, optic hits, kills, FX light cap
    # The rifle (precision barrel, Rifle 20) has the tighter cone; optic shots are only taken while the droid stands still
    # (idle, winding up, striking, staggered), so the snapshot's weak-point centre is where the optic really is.
    shots = []
    light_max = 0
    f_start = S.feel()
    captured_kill = False
    for landmark in ('berms_caravan', 'berms_scrapyard', 'berms_scrapper_camp'):
        grant('medkit', 3)
        qa.goto(landmark); qa.view('follow'); time.sleep(1.5)
        draw('1', 'weapon_field_rifle')
        p = S.snap()['player']['position']
        ws = [e for e in live() if 'orker' in e['displayName'] and S.dist(e['position'], p) < 60]
        note(f'workers near {landmark}', [(e['state'], [round(v, 1) for v in e['position']]) for e in ws])
        if not ws:
            continue
        names = {ws[0]['displayName']}
        t_end = time.monotonic() + 120
        qa.button(3, True)
        try:
            while time.monotonic() < t_end:
                fz = S.feel(); light_max = max(light_max, fz['fxLights'])
                if S.snap()['combat']['health'] < 60:
                    qa.button(3, False); qa.tap('3', settle=.8); qa.button(3, True)
                p = S.snap()['player']['position']
                near = sorted(live(names, 60, p), key=lambda e: S.dist(e['position'], p))
                if not near:
                    break
                e = near[0]
                dd = S.dist(e['position'], p)
                zone = next((z for z in fz['weakPointZones'] if S.dist(z['centre'], e['position']) < 1.6), None)
                still = e['state'] in ('Idle', 'Alert', 'Windup', 'Recover', 'Stagger')
                weak_now = len([s for s in shots if s['weak']])
                want_optic = zone and still and (weak_now < 3)
                want_body = len([s for s in shots if s['aimed'] == 'body']) < 3
                if not want_optic and not want_body and weak_now >= 3:
                    want_body = True
                if not want_optic and not want_body:
                    time.sleep(.15); continue
                tgt = zone['centre'] if want_optic else [e['position'][0], e['position'][1] + .95, e['position'][2]]
                aim_point(tgt, passes=2)
                before = S.feel()
                if not captured_kill and e['health'] < 30:
                    fire_capture('rifle-kill-marker', .15); captured_kill = True
                else:
                    qa.tap('f', .05, settle=.12)
                after = S.feel()
                if after['hits'] > before['hits']:
                    lh = after['lastHit'] or {}
                    shots.append(dict(aimed='optic' if want_optic else 'body', state=e['state'], weak=lh.get('weakPoint'), zone=lh.get('zone'), dealt=round(lh.get('dealt') or 0, 1),
                                      killed=lh.get('killed'), dist=round(dd, 1), cone=round(after.get('lastCone') or 0, 2), marker=after['marker']['shown'],
                                      criticals=after['marker']['criticals']))
                    if lh.get('weakPoint') and not lh.get('killed') and len([s for s in shots if s['weak'] and not s['killed']]) == 1:
                        cap('weak-point-hit-marker', layout=False)
        finally:
            qa.button(3, False)
        if len([s for s in shots if s['weak'] and not s['killed']]) >= 2:
            break
    f_end = S.feel()
    S.report['shots'] = shots
    note('worker shots', shots)
    weak = [s for s in shots if s['weak']]
    optic_tries = [s for s in shots if s['aimed'] == 'optic']
    bodyhits = [s for s in shots if not s['weak'] and not s['killed'] and s['aimed'] == 'body']
    ok(weak, 'weak point: an aimed optic shot registers as a weak-point hit (zone optic)', {'weak': weak[:4], 'opticTries': len(optic_tries)})
    ok(f_end['weakPointHits'] > f_start['weakPointHits'] and f_end['criticalHits'] > f_start['criticalHits'], 'weak point: weakPointHits and criticalHits rise',
       {k: (f_start[k], f_end[k]) for k in ('weakPointHits', 'criticalHits', 'criticalFlashes', 'criticalStaggers')})
    ok(f_end['criticalFlashes'] > f_start['criticalFlashes'], 'weak point: critical flash at the optic', (f_start['criticalFlashes'], f_end['criticalFlashes']))
    wd = [s['dealt'] for s in weak if not s['killed']]
    bd = [s['dealt'] for s in bodyhits]
    if wd and bd:
        ratio = (sum(wd) / len(wd)) / (sum(bd) / len(bd))
        ok(1.3 <= ratio <= 1.7, 'weak point: optic damage about 1.5x a body hit (rifle vs worker)', {'optic': wd, 'body': bd, 'ratio': round(ratio, 2)})
    else:
        note('no non-lethal optic hit to compare damage', {'optic': wd, 'body': bd})
    if wd:
        ok(f_end['marker']['criticals'] > f_start['marker']['criticals'], 'critical (brass) marker shown for a non-lethal weak-point hit', (f_start['marker'], f_end['marker']))
    dk = f_end['kills'] - f_start['kills']
    dm = f_end['marker']['kills'] - f_start['marker']['kills']
    ok(dk > 0 and dm == dk, 'kill markers follow kills (marker.kills delta == kills delta)', {'kills': dk, 'markerKills': dm})
    ok(light_max <= f_end['fxLightCap'], 'FX light cap never exceeded during the fights', {'max': light_max, 'cap': f_end['fxLightCap']})

    # ---- 6. gunner bolts at the relay knoll
    grant('medkit', 3)
    qa.goto('relay_knoll_approach'); qa.view('follow'); time.sleep(1.0)
    qa.goto('berms_relay_knoll'); time.sleep(.5)
    draw('1', 'weapon_field_rifle')
    g0 = sum(e.get('bolts', 0) for e in S.snap()['combat']['enemies'])
    t_end = time.monotonic() + 40
    bolt_caps = 0
    while time.monotonic() < t_end and bolt_caps < 4:
        gun = [e for e in live() if 'unner' in e['displayName']]
        if not gun:
            break
        p = S.snap()['player']['position']
        g = min(gun, key=lambda e: S.dist(e['position'], p))
        aim_point([g['position'][0], g['position'][1] + 1.2, g['position'][2]], passes=1)
        if S.snap()['combat']['health'] < 60:
            qa.tap('3', settle=.6)
        bolts = sum(e.get('bolts', 0) for e in S.snap()['combat']['enemies'])
        if bolts > g0 + bolt_caps:
            cap('gunner-bolt-%d' % bolt_caps, layout=False); bolt_caps += 1
        time.sleep(.3)
    g1 = sum(e.get('bolts', 0) for e in S.snap()['combat']['enemies'])
    ok(g1 > g0, 'relay-knoll gunners fire bolts at the player', {'before': g0, 'after': g1, 'captures': bolt_caps})
    S.report['final_feel'] = S.feel()


S.run(body)
