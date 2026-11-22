"""Native real-input check of Linn's voice (art/linn_voice_20261120, 20 Nov 2026).

Continues a fixture save past Ossa's primer (200 credits, no home lease) and, with real input at Linn on the hill:
  1. E opens her dialogue; the clip on her dialogue voice source is npc_linn-greeting and it plays longer than the old
     Amelia take (so the new take is in the build).
  2. "What's under the tree?" -> npc_linn-hill plays (same length test).
  3. "Let me ask you something else." -> again (the returning greeting), then "Is there anywhere in Ward I could stay?" -> npc_linn-housing; after 2 s
     "Not yet. I'll come back." closes early: state back to Play, her voice stops, no Linn clip left playing.
  4. Again to housing, and it plays to its end (time reaches length - 0.6 s) with the node still `housing`.
  5. "I'll take the lease (40 credits)." -> npc_linn-housing_leased plays; 40 credits taken.
  6. Closed, standing by her: one of her bark takes (npc_linn-<line>) plays with its caption.
Expected lengths come from art/linn_voice_20261120/installed.json (the mastered WAVs), old lengths from previous/.
Nobody listens: "plays" means the take is bound and its AudioSource reports playing; the voice itself needs an ear.
  ATHEN_EXE=<player> ATHEN_OUT=<dir> python unity/tools/check_linn_voice_native.py
"""
import json, time, wave
import showcase_qa as S
from showcase_qa import qa, ok, note, cap

ART = S.ROOT / 'art/linn_voice_20261120'
INSTALLED = json.loads((ART / 'installed.json').read_text())
NEW = {k: v['after']['seconds'] for k, v in INSTALLED['lines'].items()}
OLD = {}
for p in (ART / 'previous').glob('npc_linn-*.wav'):
    with wave.open(str(p)) as w:
        OLD[p.stem.split('-', 1)[1]] = w.getnframes() / w.getframerate()
S.report['voice'] = {'name': INSTALLED.get('voice_name'), 'id': INSTALLED.get('voice_id'), 'newSeconds': NEW, 'oldSeconds': OLD}
SAVE = S.kit_save(S.OUT / 'save', flags=[])


def linn_dialogue_sources():
    return [s for s in S.sources() if s['name'] == 'Dialogue voice' and (s['clip'] or '').startswith('npc_linn-')]


def follow(clip, seconds, until_end=False):
    """Poll Linn's dialogue voice: the furthest playback time seen on `clip`, and whether it stopped by itself."""
    t_end = time.monotonic() + (seconds + 2.5 if until_end else min(seconds, 4.0) + 1.0)
    best, nodes = 0.0, set()
    while time.monotonic() < t_end:
        s = S.snap()
        nodes.add(s['interaction']['node'])
        src = [x for x in s['audio']['sources'] if x['name'] == 'Dialogue voice' and x['clip'] == clip]
        if src and src[0]['playing']:
            best = max(best, src[0]['time'])
        elif until_end and best > 0:
            break
        time.sleep(.15)
    return round(best, 2), nodes


def choose(label):
    labels = S.snap()['interaction']['choices'] or []
    if not ok(label in labels, f'choice "{label}" offered', labels):
        raise RuntimeError('missing choice ' + label)
    qa.activate('choice%d' % labels.index(label)); time.sleep(.5)


def node_take(node, full=False):
    clip = 'npc_linn-' + node
    playing = [s['clip'] for s in linn_dialogue_sources() if s['playing']]
    ok(S.snap()['interaction']['node'] == node and playing == [clip], f'{node}: node open and {clip} is the clip playing', playing)
    longer = node in OLD and NEW[node] > OLD[node] + .5
    best, nodes = follow(clip, NEW[node], until_end=full or longer)
    if longer:
        ok(best > OLD[node] + .2, f'{node}: playback passes the old take\'s length (new take in the build)',
           {'seen': best, 'old': round(OLD[node], 2), 'new': NEW[node]})
    if full:
        ok(best >= NEW[node] - .6 and nodes == {node}, f'{node}: plays to its end ({NEW[node]} s) without being cut off',
           {'seen': best, 'nodes': sorted(n for n in nodes if n)})
    return best


def body():
    S.launch(save=SAVE)
    S.start()
    S.time_set(13)
    qa.goto('oa_hill'); qa.view('follow'); time.sleep(1.0)
    ok('Linn' in (S.snap()['interaction']['prompt'] or ''), 'Linn prompt on the hill', S.snap()['interaction']['prompt'])

    # 1-2 greeting and hill
    qa.tap('e', settle=.6)
    ok(qa.state() == 'Dialogue' and S.snap()['interaction']['npc'] == 'Linn', 'E opens Linn\'s dialogue')
    node_take('greeting')
    cap('linn-greeting')
    choose("What's under the tree?")
    node_take('hill')

    # 3 housing, left early
    choose('Let me ask you something else.')
    choose('Is there anywhere in Ward I could stay?')
    playing = [s['clip'] for s in linn_dialogue_sources() if s['playing']]
    ok(S.snap()['interaction']['node'] == 'housing' and playing == ['npc_linn-housing'], 'housing: npc_linn-housing plays', playing)
    time.sleep(2.0)
    choose('Not yet. I\'ll come back.')
    time.sleep(.6)
    left = [s['clip'] for s in linn_dialogue_sources() if s['playing']]
    ok(qa.state() == 'Play' and not left, 'leaving during the housing take: back in play and her voice stops', {'state': qa.state(), 'playing': left})
    qa.release_all(); time.sleep(.5)

    # 4 housing to its end
    qa.tap('e', settle=.6)
    ok(qa.state() == 'Dialogue', 'Linn\'s dialogue opens again after leaving early')
    choose('Is there anywhere in Ward I could stay?')
    node_take('housing', full=True)
    cap('linn-housing')

    # 5 lease
    c0 = S.snap()['session']['credits']
    choose('I\'ll take the lease (40 credits).')
    ok(S.snap()['session']['credits'] == c0 - 40 and (S.snap().get('home') or {}).get('leased'), 'the lease takes 40 credits', {'credits': S.snap()['session']['credits']})
    node_take('housing_leased', full=True)
    choose('Thank you, Linn.')
    time.sleep(.6)
    ok(qa.state() == 'Play' and not [s for s in linn_dialogue_sources() if s['playing']], 'dialogue closed, no Linn dialogue take left playing', qa.state())

    # 6 a bark with its caption, standing by her
    time.sleep(8)  # the global gap between barks after a conversation
    qa.cmd('barkReset'); time.sleep(.3)
    t_end, got = time.monotonic() + 170, None
    while time.monotonic() < t_end and not got:
        b = S.barks()
        last = b.get('last') or {}
        if b.get('active') == 'npc_linn' and last.get('speakerId') == 'npc_linn':
            clips = [s['clip'] for s in S.sources(playing=True) if (s['clip'] or '').startswith('npc_linn-')]
            got = {'last': last, 'caption': b.get('caption'), 'clips': clips}
        time.sleep(.15)
    ok(got and got['last'].get('voiced') and ('npc_linn-' + (got['last'].get('line') or '')) in got['clips'],
       'one of Linn\'s bark takes plays near her', got)
    vis = qa.el(qa.ui(), 'bark-caption')
    ok(got and vis and vis['visible'] and (got['caption'] or '').strip() == (got['last'].get('text') or '').strip(),
       'the bark caption shows her line', {'caption': got and got['caption'], 'visible': vis and vis['visible']})
    cap('linn-bark')
    note('NOT VERIFIED BY EAR: the voice, its age and roughness, pronunciation of Karaveen and Berms, levels and lip timing')


S.run(body)
