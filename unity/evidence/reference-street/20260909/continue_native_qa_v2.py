"""Continue the retained native run after correcting one test waypoint.

The original attempt and all evidence remain immutable. This harness runs only
the corrected proximity check, separately profiled city-loop checks, and the
unchanged wrapper's lighting review. It never builds/launches a game, changes
game assets, reruns traversal timing, or reclassifies the failed first attempt.
Root must invoke it against the already launched native player after finishing
independent captures. Set ATHEN_NATIVE_DIR; PID defaults to that folder's pid.
"""
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path('/home/teknetik/code/ao2')
FOLDER = Path(__file__).resolve().parent
WRAPPER = ROOT / 'art/reference_street_20260909/verify_reference_street.py'
spec = importlib.util.spec_from_file_location('frozen_reference_qa', WRAPPER)
qa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qa)


async def main():
    out = Path(os.environ['ATHEN_NATIVE_DIR']).resolve()
    os.environ.setdefault('ATHEN_NATIVE_PID', (out / 'pid').read_text().strip())
    os.environ['ATHEN_EVIDENCE'] = str(out)
    from native_client import Client
    c = Client()
    report_path = out / 'reference-qa-continuation-v2.json'
    assert not report_path.exists(), 'Preserve the prior continuation; use another version for a new attempt.'
    initial = qa.read(out / 'reference-qa-run.json')
    assert initial is not None and not initial.get('complete'), 'Expected the preserved incomplete first attempt.'
    assert any(s['step'] == 'traversal' and s.get('complete') for s in initial['steps']), 'Existing completed traversal is required.'
    for name in ['city-loop.json', 'reference-lighting.json', 'interaction-frames.json', 'interaction-performance.json']:
        assert not (out / name).exists(), 'Preserve pre-existing evidence: ' + name
    retained = ['reference-qa-run.json', 'reference-proximity.json', 'reference-first-person.mp4',
                'qa-check_reference_proximity.log', 'traversal-frames.json', 'traversal-performance.json',
                'warmup-route.json', 'measured-route.json']
    retained += [p.name for p in out.glob('first-person-*.png')]
    retained_before = {name: qa.sha(out / name) for name in retained}
    original_identity = qa.read(out / 'reference-identity-before.json')
    current_identity = qa.identity()
    report = dict(startedUtc=qa.utc(), complete=False, scope=__doc__,
                  initialAttempt={'file': 'reference-qa-run.json', 'sha256': retained_before['reference-qa-run.json'],
                                  'complete': initial.get('complete'), 'error': initial.get('error')},
                  correction={'previousView': [15.6, .5, -20.7], 'newView': [15.6, .5, -15.6],
                              'newTarget': [16.48, .7, -14.4],
                              'reason': 'Previous test waypoint intersects existing crate scatter 61; no gameplay geometry was changed.'},
                  testScript=str(FOLDER / 'check_reference_proximity_v2.py'),
                  testSha256=qa.sha(FOLDER / 'check_reference_proximity_v2.py'),
                  wrapperSha256=qa.sha(WRAPPER), sourceIdentityMatchesMeasuredRun=original_identity == current_identity,
                  retainedEvidenceBefore=retained_before, steps=[])
    qa.write(report_path, report)
    assert report['sourceIdentityMatchesMeasuredRun'], 'Source/build identity changed after the retained traversal; inspect before continuing.'
    try:
        for name in ['proximity-v2', 'city-loop', 'lighting']:
            step = {'step': name, 'startedUtc': qa.utc(), 'complete': False, 'commands': []}
            report['steps'].append(step)
            qa.write(report_path, report)
            print('Starting native QA continuation: ' + name, flush=True)
            if name == 'proximity-v2':
                result = await qa.subprocess_check(out, FOLDER / 'check_reference_proximity_v2.py')
                step['commands'].append(result)
                assert result['returncode'] == 0, 'Corrected proximity subprocess failed; evidence retained.'
                assert qa.read(out / 'reference-proximity-v2.json').get('complete'), 'Corrected proximity report is incomplete.'
            elif name == 'city-loop':
                session = qa.read(out / 'snapshot.json')['session']
                assert not session.get('boughtFlask') and not session.get('soldScrap'), 'Atomic trade check needs the untouched starting inventory.'
                step['authoringProcesses'] = qa.authoring_processes()
                assert not step['authoringProcesses'], 'Close authoring processes before profiling interactions.'
                await c.command({'action': 'profileStart'})
                try:
                    result = await qa.subprocess_check(out, 'city_loop_check.py')
                    step['commands'].append(result)
                finally:
                    await c.command({'action': 'profileStop'})
                    frames = qa.read(out / 'profile.json')
                    qa.write(out / 'interaction-frames.json', frames)
                    qa.write(out / 'interaction-performance.json',
                             {'complete': bool(step['commands']) and step['commands'][-1]['returncode'] == 0,
                              'scope': 'Separate city-loop interaction profile; retained walking measurement is untouched.',
                              'allFrames': qa.summarize(frames)})
                assert result['returncode'] == 0, 'City-loop subprocess failed; evidence retained.'
            else:
                await qa.lighting(out)
            step.update(complete=True, finishedUtc=qa.utc())
            qa.write(report_path, report)
        report['complete'] = True
    except Exception as error:
        report['error'] = repr(error)
        raise
    finally:
        report['finishedUtc'] = qa.utc()
        report['retainedEvidenceAfter'] = {name: qa.sha(out / name) for name in retained}
        report['initialEvidenceUnchanged'] = report['retainedEvidenceBefore'] == report['retainedEvidenceAfter']
        report['identityAfterContinuation'] = qa.identity()
        report['sourceIdentityStillMatchesMeasuredRun'] = original_identity == report['identityAfterContinuation']
        qa.write(report_path, report)
        summary = dict(utc=qa.utc(), attempts=[report['initialAttempt'],
                       {'file': report_path.name, 'sha256': qa.sha(report_path),
                        'complete': report.get('complete'), 'error': report.get('error')}],
                       walking=qa.summarize(qa.read(out / 'traversal-frames.json')),
                       proximityV2=qa.read(out / 'reference-proximity-v2.json'),
                       cityLoop=qa.read(out / 'city-loop.json'),
                       modalInteractions=qa.summarize(qa.read(out / 'interaction-frames.json')),
                       lighting=qa.read(out / 'reference-lighting.json'),
                       initialEvidenceUnchanged=report['initialEvidenceUnchanged'],
                       sourceIdentityStillMatchesMeasuredRun=report['sourceIdentityStillMatchesMeasuredRun'],
                       visualAcceptance=None,
                       note='The initial failed test is retained. Walking timing is reused only with unchanged source/build identity; no new walking measurement was run.')
        qa.write(out / 'reference-verification-continuation-v2.json', summary)
    assert report['initialEvidenceUnchanged'] and report['sourceIdentityStillMatchesMeasuredRun'], 'Evidence or game/source identity changed.'
    print('QA continuation complete; initial failed attempt and walking timing preserved.', flush=True)


if __name__ == '__main__':
    asyncio.run(main())
