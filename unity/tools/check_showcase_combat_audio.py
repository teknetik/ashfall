"""Native check of the combat audio package (art/showcase_20261119/combat_audio/README.md, listening test 1-9 as far as a
machine can follow it). Nobody listens here: it asserts which set a shot used, that droid voice lines are played through
their sources (FeralDroid.VoicesPlayed / LastVoiceClip), that the Sentinel's roll loop runs near it and stops far away,
that bolt fly-bys/impacts play, and the mixer groups. Loudness and character need a human with headphones.
  ATHEN_EXE=<player> python unity/tools/check_showcase_combat_audio.py [OUT]
"""
import math, time
import showcase_qa as S
from showcase_qa import qa, ok, note, cap

SAVE = S.kit_save(S.OUT / 'save', extra_items=[('medkit', 6)])


def aim_point(p, passes=2):
    for _ in range(passes):
        c = S.snap()['camera']['position']
        dx, dz = p[0] - c[0], p[2] - c[2]
        qa.yaw(math.degrees(math.atan2(dx, dz)))
        qa.pitch(max(-60, min(60, math.degrees(math.atan2(c[1] - p[1], max(math.hypot(dx, dz), .1))))))
        time.sleep(.12)


def draw(slot, weapon):
    for _ in range(4):
        c = S.snap()['combat']
        if c['Armed'] and c.get('weaponId') == weapon:
            return True
        qa.tap(slot, settle=.7)
    return S.snap()['combat'].get('weaponId') == weapon and S.snap()['combat']['Armed']


def droid_audio(part):
    return [d for d in S.feel().get('droidAudio', []) if part.lower() in d['droid'].lower()]


def site(landmark, part, prefix, seconds=45, kill=True):
    """Visit a site, alert its droids with rifle fire, record voice lines, try for a kill (death line)."""
    try:
        qa.cmd('dev.item.grant', itemId='medkit', quantity=2)
        for w in ('weapon_scrap_pistol', 'weapon_field_rifle'): qa.cmd('dev.weapon.condition', weaponId=w, full=True)  # Phase 3: start each site at full condition
    except RuntimeError as e:
        note('grant refused', str(e))
    qa.goto(landmark); qa.view('follow'); time.sleep(2.0)
    draw('1', 'weapon_field_rifle')
    seen = droid_audio(part)
    res = {'landmark': landmark, 'droids': len(seen), 'start': seen}
    if not seen:
        ok(False, f'{part}: droids present at {landmark}', [d['droid'] for d in S.feel().get('droidAudio', [])])
        return res
    clips = set()
    deaths0 = sum(1 for e in S.snap()['combat']['enemies'] if part.lower() in e['displayName'].lower() and not e['alive'])
    t_end = time.monotonic() + seconds
    while time.monotonic() < t_end:
        if S.snap()['combat']['health'] < 70:
            qa.tap('3', settle=.6)
        p = S.snap()['player']['position']
        targets = [e for e in S.snap()['combat']['enemies'] if e['alive'] and part.lower() in e['displayName'].lower() and S.dist(e['position'], p) < 70]
        for d in droid_audio(part):
            if d['last']:
                clips.add(d['last'])
        if not targets:
            break
        e = min(targets, key=lambda e: S.dist(e['position'], p))
        aim_point([e['position'][0], e['position'][1] + 1.0, e['position'][2]], passes=1)
        qa.hold('f', .5)
        deaths = sum(1 for x in S.snap()['combat']['enemies'] if part.lower() in x['displayName'].lower() and not x['alive'])
        if deaths > deaths0 and not kill:
            break
        if deaths > deaths0 and kill and any('death' in c for c in clips):
            break
    time.sleep(1.0)
    for d in droid_audio(part):
        if d['last']:
            clips.add(d['last'])
    end = droid_audio(part)
    res.update(end=end, clips=sorted(clips))
    played = sum(d['played'] for d in end)
    ok(played > 0 and any(c.startswith(prefix) for c in clips), f'{part}: own voice lines played ({prefix}*)', {'played': played, 'dropped': sum(d['dropped'] for d in end), 'clips': sorted(clips)})
    return res


def body():
    S.launch(save=SAVE)
    S.start()
    S.time_set(13)
    S.report['sites'] = {}
    groups = {}
    for s in S.sources():
        groups.setdefault(s['group'], []).append(s['name'])
    note('audio source groups at start', {k: len(v) for k, v in groups.items()})

    # ---- 1-2. pistol keeps the legacy arrays, rifle uses its own set
    qa.goto('checkpoint_firingline'); qa.view('follow'); time.sleep(.8)
    qa.yaw(270); qa.pitch(3)
    ok(draw('2', 'weapon_scrap_pistol'), 'pistol drawn (2)')
    n0 = S.snap()['combat']['ShotsFired']
    qa.tap('f', .08, settle=.4)
    f = S.feel()
    ok(S.snap()['combat']['ShotsFired'] > n0 and f.get('lastShotSoundSet') is None, 'pistol shot plays the legacy pistol arrays (no set)', f.get('lastShotSoundSet'))
    playing = [s['name'] for s in S.sources(playing=True)]
    note('sources playing right after a pistol shot', playing[:20])
    ok(draw('1', 'weapon_field_rifle'), 'rifle drawn (1)')
    n0 = S.snap()['combat']['ShotsFired']
    qa.tap('f', .08, settle=.4)
    ok(S.feel().get('lastShotSoundSet') == 'weapon_field_rifle', 'rifle single shot uses the weapon_field_rifle set', S.feel().get('lastShotSoundSet'))
    time.sleep(1.0)
    n1 = S.snap()['combat']['ShotsFired']
    qa.hold('f', 2.4)
    n2 = S.snap()['combat']['ShotsFired']
    ok(n2 - n1 >= 8, 'rifle burst (hold F 2.4 s) fires a burst on the rifle set', {'shots': n2 - n1, 'set': S.feel().get('lastShotSoundSet')})
    qa.hold('f', 6)   # run the charge dry: empty click
    note('nano after a long burst', S.snap()['combat']['Nano'])

    # ---- 5. Sentinel: roll loop near, voices, roll stops far away
    r = site('nextlevel_post_relay', 'sentinel', 'sentinel-', seconds=50)
    S.report['sites']['sentinel'] = r
    roll_seen = any(d['rollPlaying'] for d in (r.get('start') or []) + (r.get('end') or []))
    ok(roll_seen, 'sentinel: roll loop plays near a Sentinel', [(d['roll'], d['rollPlaying']) for d in r.get('end') or []])
    qa.goto('west_gate'); time.sleep(4)
    far = droid_audio('sentinel')
    ok(not any(d['rollPlaying'] for d in far), 'sentinel: roll loop stops far away (city)', [(d['roll'], d['rollPlaying']) for d in far])

    # ---- 6-7. Reaper, gunners (bolt fly-bys), lancers
    S.report['sites']['reaper'] = site('nextlevel_reaper_den', 'reaper', 'reaper-', seconds=50)
    b0 = (S.feel()['boltFlybys'], S.feel()['boltImpacts'])
    S.report['sites']['gunner'] = site('berms_relay_knoll', 'gunner', 'gunner-', seconds=45)
    S.report['sites']['lancer'] = site('berms_tube_pylon', 'lancer', 'lancer-', seconds=45)
    b1 = (S.feel()['boltFlybys'], S.feel()['boltImpacts'])
    ok(b1[0] > b0[0] or b1[1] > b0[1], 'bolts: fly-by / impact sounds played during the gunner and lancer fights', {'before': b0, 'after': b1})

    # ---- mixer groups of the droid voices (SFX since the sfxall step)
    groups = {}
    for s in S.sources():
        groups.setdefault(s['group'], set()).add(s['name'])
    S.report['groups'] = {k: sorted(v)[:40] for k, v in groups.items()}
    note('mixer groups in use at the end', {k: len(v) for k, v in groups.items()})
    ui_group = [n for n in groups.get('UI', set()) if 'oice' in n or 'roll' in n.lower()]
    ok(not ui_group, 'no droid voice/roll source left on the UI group', ui_group[:10])
    S.report['final'] = S.feel()
    note('NOT VERIFIED BY EAR: loudness, timbre, the tail build-up in a burst and the mix need a listening test (README "Listening test")')


S.run(body)
