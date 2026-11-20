"""Light budget pass (20 Nov 2026): native measurements on a built development player.

Run through the phase 2 wrapper (lock, memory cap, private display :5):
  P2/native_check.sh NAME art/light_budget_20261120/tools/lb_native.py ATHEN_EXE=<player> LB_MODE=<mode> [ATHEN_OUT=<dir>] ...

LB_MODE
  views   one launch per budget state (LB_STATES, default "0,1": off then on, by ATHEN_LIGHT_BUDGET at launch) with the
          night-readability diagnostic on (ATHEN_NIGHT_DIAG=1): each camera in LB_CAMS at each hour in LB_HOURS (default
          20.5): light-budget.json snapshot (lights enabled in view, lamps wanted in view), capture <cam>-hHH.HH.png, and
          night-diag.json for measure.py (faces, ground). Extra launch env: LB_TUNE=<file> -> ATHEN_LB_TUNE.
  walk    one launch; the scripted 20:30 night walk (spawn apron, avenue, Basic General, courtyard, hall district,
          market and West Gate, the range, the three interiors, the waystation, with 360-degree turns) LB_ROUNDS times
          per state, alternating off/on through light-budget-cmd.json; per segment a frame-time profile and the light
          counts sampled at 4 Hz; a capture at every waypoint.
  ab      frame time, alternating fresh launches: budget off / on of ATHEN_EXE (and LB_BASE_EXE, the phase 1 build, when
          set), LB_ROUNDS rounds, LB_CAMS at 20:30 (8 s uncapped, warmed 3 s), plus the first walk segment.
"""
import json, math, os, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'unity/tools'))
import showcase_qa as S  # noqa: E402
from showcase_qa import qa, ok, note  # noqa: E402
from lookbook import summarize  # noqa: E402

MODE = os.environ.get('LB_MODE', 'views')
CAMS = [c for c in os.environ.get('LB_CAMS', 'cam_night_spawn_apron,cam_night_avenue_west,cam_avenue,cam_hill').split(',') if c]
HOURS = [float(h) for h in os.environ.get('LB_HOURS', '20.5').split(',')]
STATES = [s for s in os.environ.get('LB_STATES', '0,1').split(',') if s]
ROUNDS = int(os.environ.get('LB_ROUNDS', '1'))


def lb():
    try:
        return qa.read('light-budget.json')
    except Exception:  # noqa: BLE001
        return {}


def lb_cmd(**kw):
    kw['id'] = os.urandom(6).hex()
    p = qa.RUN / 'light-budget-cmd.json'
    tmp = qa.RUN / 'light-budget-cmd.tmp'
    tmp.write_text(json.dumps(kw)); tmp.rename(p)
    for _ in range(100):
        if lb().get('lastCommand') == kw['id']:
            return lb()
        time.sleep(.05)
    raise TimeoutError('light budget command not taken: %s' % kw)


def launch(tag, budget, extra_env=None):
    os.environ['ATHEN_LIGHT_BUDGET'] = budget
    for k, v in (extra_env or {}).items():
        os.environ[k] = v
    S.launch(run=tag, save=S.kit_save(S.OUT / ('save-' + tag)))
    S.start()
    try:
        qa.cmd('dev.weather.set', state='breezy', instant=True)
    except Exception as e:  # noqa: BLE001 - older build
        note('weather pin failed', str(e))


# ------------------------------------------------------------------ views
def views():
    S.report['views'] = {}
    env = {'ATHEN_NIGHT_DIAG': '1'}
    if os.environ.get('LB_TUNE'):
        env['ATHEN_LB_TUNE'] = str(Path(os.environ['LB_TUNE']).resolve())
    for st in STATES:
        tag = 'views-' + ('on' if st == '1' else 'off')
        launch(tag, st, env)
        rows = {}
        for h in HOURS:
            S.time_set(h)
            for c in CAMS:
                qa.view(c); time.sleep(2.0)
                b = lb()
                name = '%s-h%05.2f' % (c, h)
                S.cap(name, layout=False)
                time.sleep(1.0)  # night diag writes after 0.9 s settled
                rows[name] = {'inView': b.get('inView'), 'wantedInView': b.get('wantedInView'), 'budget': b.get('budget'), 'circuit': b.get('circuit')}
                print('VIEW %-4s %-34s inView %3s wanted %3s %s' % (st, name, b.get('inView'), b.get('wantedInView'), json.dumps(b.get('budget'))[:160]), flush=True)
        qa.view('follow')
        S.report['views'][tag] = rows
        S.report.setdefault('tune', {})[tag] = lb().get('tune')
        S.stop()
    on, off = S.report['views'].get('views-on', {}), S.report['views'].get('views-off', {})
    if on:
        worst = max((r['inView'] or 0) for r in on.values())
        ok(worst <= 30, 'budget on: at most 30 local lights enabled in view at every review camera', {k: v['inView'] for k, v in on.items()})
    if off:
        note('budget off: lights in view', {k: v['inView'] for k, v in off.items()})


# ------------------------------------------------------------------ walk
ROUTE = [
    ('spawn-avenue', 'west_gate', [(34, 0), (24, 1), (16, 6), (8, 19.6)], [1, 3]),
    ('courtyard-hall', 'field_supply', [(10, -10), (5, -19), (-4, -22), (-10, -19)], [0, 3]),
    ('market-westgate', 'shop_row_e', [(-14, 3), (-27, -4), (-32, -12), (-45, 5), (-56, 1)], [1, 4]),
    ('range', 'checkpoint_approach', [(-62, 3), (-66.5, 4.5), (-71.5, -2.5)], [1]),
    ('salvage', 'salvage_shop', [(-18.5, 18.6), (-20.4, 18.0)], [1]),
    ('fieldsupply', 'field_supply', [(18.5, -9.4), (20.5, -9.0)], [1]),
    ('home', 'home_inside', [], [None]),
    ('waystation', 'berms_waystation', [], [None]),
]


def sweep(samples, tag):
    """A 360-degree turn in 16 steps (about 0.12 s each), sampling the counts at every step."""
    for k in range(16):
        qa.yaw(k * 22.5); time.sleep(.12)
        b = lb(); samples.append({'t': time.time(), 'tag': tag + '-turn', 'inView': b.get('inView'), 'wanted': b.get('wantedInView')})


def segment(state, rnd, name, start, points, turns):
    samples = []
    qa.goto(start); qa.view('follow'); qa.pitch(6); time.sleep(1.2)
    lb_cmd(reset=True)
    qa.cmd('profileStart')
    t0 = time.time()
    for i, (x, z) in enumerate(points):
        try:
            p0 = qa.pos(); d = math.hypot(x - p0[0], z - p0[2])
            deadline = time.time() + 20
            while time.time() < deadline:
                p = qa.pos(); d = math.hypot(x - p[0], z - p[2])
                if d <= .9:
                    break
                qa.face(x, z)
                qa.hold(['Shift_L', 'w'] if d > 4 else 'w', min(.5, max(.12, d / 6)))
                b = lb(); samples.append({'t': time.time(), 'tag': name, 'pos': [round(v, 1) for v in p], 'inView': b.get('inView'), 'wanted': b.get('wantedInView')})
        except Exception as e:  # noqa: BLE001
            note('walk %s point %d failed' % (name, i), str(e))
        if i in turns:
            sweep(samples, name)
        if rnd == 1:
            S.cap('walk-%s-%s-%d' % (state, name, i), layout=False)
    if not points and None in turns:
        sweep(samples, name)
        if rnd == 1:
            S.cap('walk-%s-%s-0' % (state, name), layout=False)
    qa.cmd('profileStop'); time.sleep(.4)
    prof = summarize(qa.read('profile.json'))
    b = lb_cmd(dump=True)
    run = b.get('running') or {}
    S.report.setdefault('walk', []).append({'state': state, 'round': rnd, 'segment': name, 'seconds': round(time.time() - t0, 1), 'profile': prof, 'running': run,
                                            'samples': samples, 'lamps': b.get('lamps')})
    print('WALK %-3s r%d %-16s %5.1f fps p50 %5.2f p95 %5.2f | inView max %s mean %s over30 %s/%s | wanted max %s | cuts %s promo %s demo %s' % (
        state, rnd, name, prof['averageFps'], prof['p50Ms'], prof['p95Ms'], run.get('maxInView'), run.get('meanInView'), run.get('framesOver30'), run.get('frames'),
        run.get('maxWantedInView'), run.get('hardCuts'), run.get('promotions'), run.get('demotions')), flush=True)


def walk():
    launch('walk', '1')
    S.time_set(20.5)
    order = []
    for r in range(1, ROUNDS + 1):
        order += [('off', r), ('on', r)] if r % 2 else [('on', r), ('off', r)]
    for state, r in order:
        lb_cmd(enabled=(state == 'on'), reset=True); time.sleep(.5)
        for name, start, points, turns in ROUTE:
            segment(state, r, name, start, points, turns)
    S.report.setdefault('environment', qa.read('environment.json'))
    S.stop()
    on = [w for w in S.report['walk'] if w['state'] == 'on']
    worst = max((w['running'].get('maxInView') or 0) for w in on) if on else None
    ok(on and worst <= 30, 'walk, budget on: lights enabled in view never above 30', {w['segment'] + '-r%d' % w['round']: w['running'].get('maxInView') for w in on})


# ------------------------------------------------------------------ ab
def ab():
    base = os.environ.get('LB_BASE_EXE')
    exe = qa.EXE
    variants = [('off', exe, '0'), ('on', exe, '1')] + ([('phase1', Path(base), '1')] if base else [])
    for r in range(1, ROUNDS + 1):
        seq = variants if r % 2 else list(reversed(variants))
        for name, path, st in seq:
            qa.EXE = Path(path)
            launch('ab-%s-%d' % (name, r), st)
            S.time_set(20.5)
            for c in CAMS:
                qa.view(c); time.sleep(3)
                qa.cmd('profileStart'); time.sleep(8); qa.cmd('profileStop'); time.sleep(.4)
                s = summarize(qa.read('profile.json')); b = lb()
                S.report.setdefault('ab', {}).setdefault(c, {}).setdefault(name, []).append({'profile': s, 'inView': b.get('inView')})
                print('AB %-7s r%d %-26s %6.1f fps p50 %5.2f p95 %5.2f inView %s' % (name, r, c, s['averageFps'], s['p50Ms'], s['p95Ms'], b.get('inView')), flush=True)
            qa.view('follow')
            S.stop()
    table = {}
    for c, per in S.report['ab'].items():
        row = {}
        for name, runs in per.items():
            p50 = [x['profile']['p50Ms'] for x in runs]; fps = [x['profile']['averageFps'] for x in runs]
            row[name] = {'p50Ms': round(sum(p50) / len(p50), 2), 'p50Runs': [round(x, 2) for x in p50], 'fps': round(sum(fps) / len(fps), 1),
                         'spreadMs': round(max(p50) - min(p50), 2), 'inView': [x['inView'] for x in runs]}
        table[c] = row
        print('ABT %-26s %s' % (c, ' | '.join('%s %.1f fps p50 %.2f (%s)' % (k, v['fps'], v['p50Ms'], v['p50Runs']) for k, v in row.items())), flush=True)
    S.report['abTable'] = table
    (S.OUT / 'ab-table.json').write_text(json.dumps(table, indent=1))
    ok(all(len(v) == ROUNDS for per in S.report['ab'].values() for v in per.values()), 'every camera profiled in every run')


S.run({'views': views, 'walk': walk, 'ab': ab}[MODE])
