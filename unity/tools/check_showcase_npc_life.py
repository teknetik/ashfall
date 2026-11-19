"""Native real-input check of the NPC life package (art/showcase_20261119/npc_life/README.md, test plan 1-10).

Continues a fixture save (primer done, pistol + rifle, no bark flags yet) and walks up to colonists with real W:
greeting with caption and voice from Vex (once-per-save acknowledgement first), hour-specific greetings at 23:00 and
08:00, no repeat inside the cooldown, Esc during a bark, captions off, an idle remark from Mira, a Weapon line near Torr,
a walker's Passing line and glance, Mira's ack_primer flag, and Tamsin's and Ossa's voiced dialogue nodes (the clip
playing on the NPC's voice source must be the node's take). Captures every caption. Nobody listens: "voiced" means the
take was bound and its AudioSource reported playing.
  ATHEN_EXE=<player> python unity/tools/check_showcase_npc_life.py [OUT]
"""
import math, time
import showcase_qa as S
from showcase_qa import qa, ok, note, cap

SAVE = S.kit_save(S.OUT / 'save', flags=[])
VEX, MIRA, TORR, TAMSIN = (41.7, -1.5), (8.0, 15.8), (9.0, -12.0), (20.45, -11.7)


def last():
    return (S.barks().get('last') or {})


def wait_bark(pred, timeout=8):
    t = time.monotonic() + timeout
    while time.monotonic() < t:
        b = S.barks()
        if pred(b):
            return b
        time.sleep(.1)
    return None


def walk_up(target, start, stop_at=3.0, timeout=25):
    """Real W from `start` toward `target` until within stop_at metres."""
    tx, tz = target
    sx, sz = start
    d = math.hypot(sx - tx, sz - tz)
    qa.walk_to(tx + (sx - tx) * stop_at / d, tz + (sz - tz) * stop_at / d, tol=.7, timeout=timeout)


def back_off(npc, dist, timeout=12):
    """Face the NPC and walk backwards (real S) until `dist` metres away: the way the player arrived stays clear."""
    t_end = time.monotonic() + timeout
    while time.monotonic() < t_end:
        p = qa.pos()
        if math.hypot(p[0] - npc[0], p[2] - npc[1]) >= dist:
            return True
        qa.face(*npc); qa.hold('s', .5)
    return False


def caption_visible():
    e = qa.el(qa.ui(), 'bark-caption')
    return bool(e and e['visible']), e


def voice_playing(prefix):
    return [s for s in S.sources(playing=True) if (s['clip'] or '').startswith(prefix)]


def talk_node_voice(npc_prefix):
    """The node id and the voice clip playing for the open dialogue."""
    s = S.snap()
    node = s['interaction']['node']
    time.sleep(.4)
    clips = [x['clip'] for x in S.sources(playing=True) if (x['clip'] or '').startswith(npc_prefix)]
    return node, clips


def body():
    S.launch(save=SAVE)
    S.start()
    S.time_set(13)
    b = S.barks()
    ok(b and b.get('speakers', 0) >= 11, 'bark director present with 11 speakers', {k: b.get(k) for k in ('speakers', 'captions', 'captionBound')} if b else None)
    S.report['roster'] = b.get('roster') if b else None

    # ---- 1. Vex: walk up from 11 m (first bark of the save may be the acknowledgement)
    qa.goto('west_gate'); qa.view('follow'); time.sleep(.6)
    qa.walk_to(31.5, -1.5, tol=1.0, timeout=20)
    qa.cmd('barkReset'); time.sleep(.3)
    n0 = S.barks()['count']
    walk_up(VEX, (31.5, -1.5), 3.2)
    bk = wait_bark(lambda b: b['count'] > n0, 6)
    lb = (bk or {}).get('last') or {}
    ok(bk and lb.get('speakerId') == 'npc_vex' and lb.get('trigger') in ('Greeting', 'Acknowledge'), 'Vex barks on the walk-up (greeting or once-only acknowledgement)', lb)
    ok(lb.get('voiced'), 'Vex bark is voiced (take bound)', lb.get('line'))
    vis, e = caption_visible()
    ok(vis and (S.barks().get('caption') or '').strip(), 'caption shown low centre while Vex speaks', {'caption': S.barks().get('caption'), 'bounds': e and e['bounds']})
    cap('bark-vex-caption')
    guards = [g for g in S.snap()['guards'] if 'vex' in (g['name'] or '').lower()]
    note('Vex look-at / clip while barking', guards)
    first = lb
    # the ordinary greeting after an acknowledgement
    if lb.get('trigger') == 'Acknowledge':
        time.sleep(8)
        qa.walk_to(31.5, -1.5, tol=1.0, timeout=20); qa.cmd('barkReset'); time.sleep(.3)
        n0 = S.barks()['count']
        walk_up(VEX, (31.5, -1.5), 3.2)
        bk = wait_bark(lambda b: b['count'] > n0, 6)
        lb = (bk or {}).get('last') or {}
        ok(lb.get('trigger') == 'Greeting', 'after the acknowledgement Vex greets normally', lb)

    # cooldown: step out beyond 8.5 m and back within 150 s -> nothing
    time.sleep(8)
    t_vex = last().get('time') if last().get('speakerId') == 'npc_vex' else -1
    qa.walk_to(31.5, -1.5, tol=1.0, timeout=20)
    walk_up(VEX, (31.5, -1.5), 3.2)
    vex_again = None
    for _ in range(30):   # the walkers share Vex's lane: only a new line from Vex counts
        l = last()
        if l.get('speakerId') == 'npc_vex' and (l.get('time') or 0) > (t_vex or 0) + .01:
            vex_again = l
        time.sleep(.1)
    ok(vex_again is None, 'no second greeting from Vex inside the 150 s cooldown', {'last': last(), 'vexAgain': vex_again})

    # ---- 5. hour-specific greetings
    for hour, want in ((23, 'night'), (8, 'morning')):
        S.time_set(hour)
        qa.walk_to(31.5, -1.5, tol=1.0, timeout=20)
        time.sleep(8)
        qa.cmd('barkReset'); time.sleep(.3)
        n0 = S.barks()['count']
        walk_up(VEX, (31.5, -1.5), 3.2)
        bk = wait_bark(lambda b: b['count'] > n0, 6)
        lb = (bk or {}).get('last') or {}
        ok(want in (lb.get('line') or ''), f'{hour:02d}:00 greeting from Vex is the {want} line', lb)
        cap(f'bark-vex-{want}')
    S.time_set(13)

    # ---- 3. Esc during a bark hides the caption; captions off
    got = None
    for attempt in range(3):   # a passing walker can hold the one-bark-at-a-time slot and the 7 s gap
        qa.walk_to(31.5, -1.5, tol=1.0, timeout=20); time.sleep(9)
        qa.cmd('barkReset'); time.sleep(.3)
        n0 = S.barks()['count']
        walk_up(VEX, (31.5, -1.5), 3.2)
        got = wait_bark(lambda b: b['count'] > n0 and b.get('caption'), 8)
        if got:
            break
    if got:
        qa.tap('Escape', settle=.4)
        vis, _ = caption_visible()
        ok(qa.state() == 'Paused' and not vis, 'Esc during a bark: paused and the caption is hidden', {'state': qa.state(), 'paused': S.snap()['audio']['paused']})
        qa.tap('Escape', settle=.6)
    else:
        ok(False, 'bark for the Esc test')
    qa.cmd('barkCaptions', on=False)
    qa.walk_to(31.5, -1.5, tol=1.0, timeout=20); time.sleep(8)
    qa.cmd('barkReset'); time.sleep(.3)
    n0 = S.barks()['count']
    walk_up(VEX, (31.5, -1.5), 3.2)
    bk = wait_bark(lambda b: b['count'] > n0, 6)
    vis, _ = caption_visible()
    ok(bk and bk['last']['voiced'] and not vis and not bk.get('caption'), 'captions off: a voiced bark plays with no caption', (bk or {}).get('last'))
    qa.cmd('barkCaptions', on=True)

    # ---- 8. walker Daro passing on his lane (glance)
    qa.walk_to(38.0, -3.5, tol=.8, timeout=20)
    qa.cmd('barkReset')
    bk = wait_bark(lambda b: (b.get('last') or {}).get('trigger') == 'Passing', 100)
    ok(bk, 'a walker speaks a Passing line as he passes', (bk or {}).get('last'))
    if bk:
        cap('bark-walker-passing')
        g = [x for x in S.snap()['guards'] if 'walker' in (x['name'] or '').lower()]
        note('walker look-at state while passing', g)
        ok(any(x['Focused'] for x in g), 'walker glances at the player (ActorLookAt focused)', g)

    # ---- 9. Mira: acknowledgement once (primer), flag saved
    qa.goto('basic_general'); qa.view('follow'); time.sleep(.5)
    back_off(MIRA, 10.0)
    time.sleep(8); qa.cmd('barkReset'); time.sleep(.3)
    n0 = S.barks()['count']
    p = qa.pos(); walk_up(MIRA, (p[0], p[2]), 3.0)
    bk = wait_bark(lambda b: b['count'] > n0, 6)
    lb = (bk or {}).get('last') or {}
    ok(lb.get('speakerId') == 'npc_mira', 'Mira barks on the walk-up', lb)
    flags = S.snap()['interaction']['flags']
    if lb.get('line') == 'ack_primer':
        ok('bark.npc_mira.ack_primer' in flags, 'ack_primer recorded as a story flag', [f for f in flags if f.startswith('bark.')])
    else:
        note('Mira did not use ack_primer first (line %s); flags %s' % (lb.get('line'), [f for f in flags if f.startswith('bark.')]))
    cap('bark-mira')

    # ---- 4. idle remark while lingering near Mira (up to 160 s)
    t0 = time.monotonic()
    bk = wait_bark(lambda b: (b.get('last') or {}).get('trigger') == 'Idle', 160)
    ok(bk, 'an idle remark while lingering near a colonist (within 160 s)', {'seconds': round(time.monotonic() - t0), 'last': (bk or {}).get('last')})
    if bk:
        cap('bark-idle')

    # ---- 7. weapon reaction near Torr (press 2 inside the walls)
    qa.goto('mission_slab'); time.sleep(1.0)
    back_off(TORR, 4.0)
    # arriving next to Torr starts his greeting: let it and the 7 s gap pass before drawing (one bark at a time)
    S.wait_for(lambda: not S.barks().get('active') and S.barks().get('globalReadyIn', 1) == 0, 20)
    time.sleep(.5)
    n0 = S.barks()['count']
    qa.tap('2', settle=.2)
    bk = wait_bark(lambda b: b['count'] > n0 and (b.get('last') or {}).get('trigger') == 'Weapon', 3)
    note('notice after 2 inside the walls', S.snap()['session']['notice'])
    ok(bk, 'a Weapon line answers 2 inside the walls (within 3 s)', (bk or {}).get('last') or S.barks().get('last'))
    if bk:
        cap('bark-weapon')

    # ---- 10. Tamsin's voiced dialogue nodes
    time.sleep(8)
    qa.goto('field_supply_counter'); qa.view('follow'); time.sleep(1.0)
    qa.face(*TAMSIN); time.sleep(.3)
    ok('Tamsin' in (S.snap()['interaction']['prompt'] or ''), 'Tamsin prompt at the Field Supply counter', S.snap()['interaction']['prompt'])
    qa.tap('e', settle=1.0)
    seen = {}
    for choice_label in (None, 'Which pack should I carry?', 'Medkits and nano cells?', 'Tell me about the magazines.'):
        if choice_label:
            labels = S.snap()['interaction']['choices'] or []
            if choice_label not in labels:
                note('choice missing', {'want': choice_label, 'have': labels}); break
            qa.activate('choice%d' % labels.index(choice_label)); time.sleep(.8)
        node, clips = talk_node_voice('npc_tamsin')
        seen[node] = clips
    S.report['tamsin'] = seen
    for node in ('greeting', 'first_visit', 'packs', 'supplies', 'magazines'):
        if node in seen:
            ok(any(node in c for c in seen[node]), f'Tamsin {node}: her take for that node plays', seen[node])
    ok(len(seen) >= 4, 'four Tamsin nodes visited', list(seen))
    sup = qa.el(qa.ui(), 'dialogue-text') or {}
    qa.tap('Escape', settle=.8)

    # ---- 10. Ossa's range and locker takes
    qa.goto('checkpoint_ossa'); time.sleep(1.0)
    ok('Ossa' in (S.snap()['interaction']['prompt'] or ''), 'Ossa prompt at the checkpoint', S.snap()['interaction']['prompt'])
    qa.tap('e', settle=1.0)
    oss = {}
    node, clips = talk_node_voice('npc_ossa')
    oss[node] = clips
    for want in ('Remind me of the controls.', 'Where is the locker?', 'Tell me about the machines.', 'How do I use the range?', 'Where was the locker?'):
        labels = S.snap()['interaction']['choices'] or []
        if want in labels:
            qa.activate('choice%d' % labels.index(want)); time.sleep(.8)
            node, clips = talk_node_voice('npc_ossa')
            oss[node] = clips
    S.report['ossa'] = oss
    for node in ('range', 'locker', 'long_arm'):
        if node in oss:
            ok(any(node in c for c in oss[node]), f'Ossa {node}: her take for that node plays', oss[node])
    ok('range' in oss and 'locker' in oss, 'Ossa range and locker nodes reached', list(oss))
    cap('ossa-dialogue')
    qa.tap('Escape', settle=.6)
    S.report['final'] = S.barks()
    note('NOT VERIFIED BY EAR: voices, levels, the 7 s gap and lip/talk-clip timing need a listening/watching pass')


S.run(body)
