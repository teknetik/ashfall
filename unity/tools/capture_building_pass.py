"""Matched native building-pass stills. Diagnostic cameras do not qualify traversal."""
import argparse, asyncio, hashlib, json, os, time
from pathlib import Path
from PIL import Image
from native_client import Client
from desktop_input import focus

ROOT = Path(__file__).resolve().parents[2]

async def capture(args):
    out = args.native.resolve()
    os.environ.update(ATHEN_NATIVE_DIR=str(out), ATHEN_NATIVE_PID=(out / 'pid').read_text().strip())
    report_path = out / args.report
    previous = json.loads(report_path.read_text()) if report_path.exists() else None
    if previous is not None and (not args.resume or previous.get('complete')):
        raise RuntimeError('Keep earlier evidence; launch a new folder.')
    focus(); client = Client()
    await client.command({'action': 'resize', 'width': 1920, 'height': 1080})
    await asyncio.sleep(1.3)
    await client.command({'action': 'timeReset'})
    await client.command({'action': 'timePause', 'paused': True})
    await client.command({'action': 'timeState'})
    await client.command({'action': 'settingsSnapshot'})
    def read(name): return json.loads((out / name).read_text())
    report = {'purpose': __doc__, 'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'settings': read('settings.json'), 'time': read('time-state.json'),
              'environment': read('environment.json'), 'captures': [], 'complete': False}
    if previous is not None:
        report['captures'] = previous['captures']
        report['resumedUtc'] = report['utc']
        report['utc'] = previous['utc']
        report['interruptions'] = previous.get('interruptions', [])
    assert report['settings']['renderScale'] == 1
    assert report['environment']['actorCount'] == 9
    plan = json.loads((ROOT / 'unity/evidence/quality/20260908/building-captures/building-capture-plan.json').read_text())
    buildings = plan['buildings']
    views = [v['name'] for b in buildings if args.building is None or b['id'] == args.building for v in b['views']]
    if args.building is None:
        views = ['cam_hill', 'cam_avenue', 'cam_gate', 'cam_grid', 'cam_whompah', 'cam_hero', 'cam_terminal'] + views
    if args.extra:
        views += json.loads(args.extra.read_text())
    try:
        for name in views:
            if any(v['camera'] == name for v in report['captures']): continue
            focus()
            await client.command({'action': 'view', 'camera': name})
            await asyncio.sleep(.8)
            snapshot = read('snapshot.json')
            assert [snapshot['width'], snapshot['height']] == [1920, 1080]
            assert snapshot['session']['state'] == 'Play', 'Modal UI obscures this diagnostic view; resume Play before capturing.'
            await client.command({'action': 'capture', 'name': name})
            path = out / (name + '.png')
            for _ in range(70):
                try:
                    with Image.open(path) as im:
                        im.load(); assert im.size == (1920, 1080)
                    break
                except (FileNotFoundError, OSError): await asyncio.sleep(.1)
            else: raise TimeoutError(name)
            report['captures'].append({'camera': name, 'path': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'snapshot': snapshot})
            report_path.write_text(json.dumps(report, indent=2))
            print(name, flush=True)
        report['complete'] = True
    except Exception as error:
        report.setdefault('interruptions', []).append({'utc': time.time(), 'error': str(error)})
        raise
    finally:
        report_path.write_text(json.dumps(report, indent=2))
        await client.command({'action': 'view', 'camera': 'follow'})
        await client.command({'action': 'timeReset'})

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('native', type=Path)
    parser.add_argument('--building')
    parser.add_argument('--extra', type=Path)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--report', default='building-pass-captures.json')
    asyncio.run(capture(parser.parse_args()))
