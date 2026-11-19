"""Before/after frame time for the showcase programme (19 Nov 2026).

Alternating fresh player runs of two builds (base, showcase, showcase, base, base, showcase ...), each with 8 s of
uncapped frame timing (warmed 3 s) at cam_hill, cam_avenue and cam_gate at 13:00 and 20:30. 1920x1080, High preset with
TAA (qa.launch's video settings), private QA display, the desktop shares the GPU: read differences against the spread of
the runs of one build, not as absolute numbers. Only bridge commands both builds know are used; the showcase build is
pinned to its default weather ("breezy") so a dust front cannot roll in mid-measurement.

  ATHEN_BASE_EXE=<before player> ATHEN_EXE=<after player> python unity/tools/check_showcase_ab.py [OUT]
  AB_ROUNDS (default 3) = runs per build.
"""
import json, os, time
from pathlib import Path
import showcase_qa as S
from showcase_qa import qa, ok, note
from lookbook import summarize

BUILDS = {'base': Path(os.environ['ATHEN_BASE_EXE']), 'showcase': Path(qa.EXE)}
CAMS = ['cam_hill', 'cam_avenue', 'cam_gate']
ROUNDS = int(os.environ.get('AB_ROUNDS', '3'))
SECONDS = 8


def profile(build, name):
    time.sleep(3)
    qa.cmd('profileStart'); time.sleep(SECONDS); qa.cmd('profileStop'); time.sleep(.4)
    s = summarize(qa.read('profile.json'))
    S.report.setdefault('profiles', {}).setdefault(name, {}).setdefault(build, []).append(s)
    tris, sp = (s.get('tris') or {}).get('mean'), (s.get('setPass') or {}).get('mean')
    print('PROFILE %-9s %-18s %6.1f fps  p50 %5.2f  p95 %5.2f  p99 %5.2f  max %6.2f ms  tris %s  setPass %s' % (
        build, name, s['averageFps'], s['p50Ms'], s['p95Ms'], s['p99Ms'], s['maxMs'], tris, sp), flush=True)


def one(build, r):
    qa.EXE = BUILDS[build]
    S.launch(run=f'{build}{r}', save=S.kit_save(S.OUT / f'save-{build}{r}'))
    S.start()
    if build == 'showcase':
        qa.cmd('dev.weather.set', state='breezy', instant=True)
    for hour, tag in ((13, '1300'), (20.5, '2030')):
        S.time_set(hour)
        for c in CAMS:
            qa.view(c); profile(build, f'{c}-{tag}')
    S.report.setdefault('environment', qa.read('environment.json'))
    S.stop()


def mean(xs):
    return sum(xs) / len(xs)


def body():
    S.report['builds'] = {k: {'exe': str(v), 'mtime': time.ctime(v.stat().st_mtime)} for k, v in BUILDS.items()}
    for r in range(1, ROUNDS + 1):
        for build in (('base', 'showcase') if r % 2 else ('showcase', 'base')):
            one(build, r)
    table = {}
    for view, per in S.report['profiles'].items():
        row = {}
        for build, runs in per.items():
            row[build] = {'fps': round(mean([x['averageFps'] for x in runs]), 1), 'p50Ms': round(mean([x['p50Ms'] for x in runs]), 2),
                          'p95Ms': round(mean([x['p95Ms'] for x in runs]), 2), 'p99Ms': round(mean([x['p99Ms'] for x in runs]), 2),
                          'fpsRuns': [round(x['averageFps'], 1) for x in runs], 'p50Runs': [round(x['p50Ms'], 2) for x in runs],
                          'tris': round(mean([(x.get('tris') or {}).get('mean') or 0 for x in runs])),
                          'setPass': round(mean([(x.get('setPass') or {}).get('mean') or 0 for x in runs]))}
        if 'base' in row and 'showcase' in row:
            row['p50DeltaMs'] = round(row['showcase']['p50Ms'] - row['base']['p50Ms'], 2)
            row['baseSpreadMs'] = round(max(row['base']['p50Runs']) - min(row['base']['p50Runs']), 2)
            row['showcaseSpreadMs'] = round(max(row['showcase']['p50Runs']) - min(row['showcase']['p50Runs']), 2)
        table[view] = row
        print('AB %-18s base %5.1f fps p50 %5.2f %s | showcase %5.1f fps p50 %5.2f %s | delta %+5.2f ms' % (
            view, row['base']['fps'], row['base']['p50Ms'], row['base']['p50Runs'], row['showcase']['fps'], row['showcase']['p50Ms'],
            row['showcase']['p50Runs'], row.get('p50DeltaMs', 0)), flush=True)
    S.report['table'] = table
    (S.OUT / 'ab-table.json').write_text(json.dumps(table, indent=1))
    ok(all(len(per.get('base', [])) == ROUNDS and len(per.get('showcase', [])) == ROUNDS for per in S.report['profiles'].values()),
       'every view profiled in every run of both builds')


S.run(body)
