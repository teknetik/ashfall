"""Frame-time profile of the showcase build (19 Nov 2026): two fresh player runs, each with 8 s of uncapped frame timing
(warmed 3 s) at cam_hill, cam_avenue, cam_gate and cam_bx_relay_knoll at 13:00 and 20:30, then at the same city/gate
views and the Berms follow view during a forced dust-front peak, and in an open conversation (depth of field) with Vex
and Tamsin. 1920x1080, High preset with TAA (qa.launch's video settings), private QA display: indicative numbers.
  ATHEN_EXE=<player> python unity/tools/check_showcase_perf.py [OUT]
"""
import json, time
import showcase_qa as S
from showcase_qa import qa, ok, note
from lookbook import summarize

CAMS = ['cam_hill', 'cam_avenue', 'cam_gate', 'cam_bx_relay_knoll']
SECONDS = 8


def profile(name):
    time.sleep(3)
    qa.cmd('profileStart'); time.sleep(SECONDS); qa.cmd('profileStop'); time.sleep(.4)
    s = summarize(qa.read('profile.json'))
    S.report.setdefault('profiles', {}).setdefault(name, []).append(s)
    print('PROFILE %-34s %6.1f fps  p50 %5.2f  p95 %5.2f  p99 %5.2f  max %6.2f ms' % (name, s['averageFps'], s['p50Ms'], s['p95Ms'], s['p99Ms'], s['maxMs']), flush=True)
    return s


def body():
    for r in (1, 2):
        S.launch(run=f'run{r}', save=S.kit_save(S.OUT / f'save{r}'))
        S.start()
        qa.cmd('dev.weather.set', state='breezy', instant=True)
        for hour, tag in ((13, '1300'), (20.5, '2030')):
            S.time_set(hour)
            for c in CAMS:
                qa.view(c); profile(f'{c}-{tag}')
        S.time_set(13)
        qa.cmd('dev.weather.set', state='peak', instant=True); time.sleep(2)
        for c in ('cam_hill', 'cam_gate'):
            qa.view(c); profile(f'{c}-1300-peak')
        qa.goto('berms_caravan'); qa.view('follow'); qa.yaw(250); qa.pitch(8)
        profile('berms-follow-1300-peak')
        qa.cmd('dev.weather.set', state='breezy', instant=True); time.sleep(2)
        profile('berms-follow-1300-breezy')
        # open conversations (conversation camera + bokeh depth of field)
        for name, lm, xz in (('Vex', 'west_gate', (41.7, -1.5)), ('Tamsin', 'field_supply_counter', (20.45, -11.7))):
            qa.goto(lm); qa.view('follow'); time.sleep(1); qa.face(*xz); time.sleep(.5)
            profile(f'follow-{name.lower()}-before-dialogue')
            if name in (S.snap()['interaction']['prompt'] or ''):
                qa.tap('e', settle=1.2)
                c = S.show()['conversation']
                note(f'{name} conversation state while profiling', c)
                profile(f'conversation-{name.lower()}-dof')
                qa.tap('Escape', settle=.8)
            else:
                note(f'no prompt for {name}', S.snap()['interaction']['prompt'])
        S.report.setdefault('environment', qa.read('environment.json'))
        S.stop()
    # averages over the two runs
    table = {}
    for k, v in S.report['profiles'].items():
        table[k] = {m: round(sum(x[m] for x in v) / len(v), 2) for m in ('averageFps', 'p50Ms', 'p95Ms', 'p99Ms', 'maxMs')}
        table[k]['runs'] = [round(x['averageFps'], 1) for x in v]
    S.report['table'] = table
    (S.OUT / 'perf-table.json').write_text(json.dumps(table, indent=1))
    ok(all(len(v) == 2 for v in S.report['profiles'].values()), 'every view profiled in both runs')


S.run(body)
