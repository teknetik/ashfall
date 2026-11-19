"""Cost bisection for the showcase build (19 Nov 2026): cam_hill and cam_avenue at 13:00, 8 s each (warmed 3 s), with
every root on, then with today's scene additions switched off one at a time through the bridge's setActive (weather root,
bark director host is not a root so it is not toggled). Run on the build under test and on batch-showcase1 (before the
night pass) for comparison. Indicative: private QA display, desktop shares the GPU.
  ATHEN_EXE=<player> python unity/tools/check_showcase_perf_bisect.py [OUT]
"""
import json, time
import showcase_qa as S
from showcase_qa import qa, ok, note
from lookbook import summarize

PREFIXES = ['Ward weather', 'Night readability']


def profile(name):
    time.sleep(3)
    qa.cmd('profileStart'); time.sleep(8); qa.cmd('profileStop'); time.sleep(.4)
    s = summarize(qa.read('profile.json'))
    S.report.setdefault('profiles', {})[name] = s
    d, tr, g = s.get('draws') or {}, s.get('tris') or {}, s.get('gpuMs') or {}
    print('PROFILE %-40s %6.1f fps  p50 %5.2f  p95 %5.2f  p99 %5.2f ms  draws %s  tris %s  gpu %s' % (name, s['averageFps'], s['p50Ms'], s['p95Ms'], s['p99Ms'], d.get('mean'), tr.get('mean'), g.get('mean')), flush=True)


def body():
    S.launch(save=S.kit_save(S.OUT / 'save'))
    S.start()
    qa.cmd('dev.weather.set', state='breezy', instant=True)
    S.time_set(13)
    for cam in ('cam_hill', 'cam_avenue'):
        qa.view(cam)
        profile(f'{cam}-all')
        for p in PREFIXES:
            qa.cmd('setActive', prefix=p, active=False); time.sleep(.3)
            changed = qa.read('set-active.json')['changed']
            profile(f'{cam}-without-{p.replace(" ", "_")}-{changed}')
            qa.cmd('setActive', prefix=p, active=True)
        profile(f'{cam}-all-again')
    ok(True, 'bisection profiled')


S.run(body)
