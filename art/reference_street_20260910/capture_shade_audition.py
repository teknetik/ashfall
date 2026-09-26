"""Matched native stills for the bounded afternoon environment audition.

Run after the sole native review runner finishes. Root owns all native input.
This records actual native pixels and clock/probe/memory state; it is not a
performance qualification or a real-input traversal substitute.
"""
import asyncio
import json
import os
from pathlib import Path
import sys
import time

import capture_native_iteration as base

CAMERAS = ['cam_reference_street', 'cam_audit_finery_front', 'cam_canopy_top',
           'cam_canopy_under', 'cam_ground_crate', 'cam_ground_trash', 'cam_ground_scrap']
HOURS = [16, 17.5, 18.25, 0, 12]


async def run(folder):
    from PIL import Image
    sys.path.insert(0, str(base.ROOT / 'unity/tools'))
    from native_client import Client
    from desktop_input import focus
    from native_memory import snapshot as memory_snapshot

    out = Path(folder).resolve(); report_path = out / 'shade-audition-report.json'
    assert not report_path.exists(), 'Preserve previous shade evidence.'
    assert base.read(out/'review-runner-status.json')['complete']
    pid = int((out/'pid').read_text())
    assert Path(os.readlink(Path('/proc')/str(pid)/'exe')).name == 'AthenHill.x86_64'
    os.environ.update(ATHEN_NATIVE_DIR=str(out), ATHEN_NATIVE_PID=str(pid), ATHEN_EVIDENCE=str(out))
    before = base.identity()
    assert before == base.read(out/'asset-passes-identity-after.json'), 'Native source/build changed.'
    client = Client(); d = focus(); d.close()
    report = {'complete': False, 'startedUtc': base.utc(), 'pid': pid, 'scope': __doc__,
              'driverSha256': base.sha(Path(__file__)), 'cameraSources': base.camera_sources(CAMERAS),
              'hours': HOURS, 'views': [], 'reflectionWaits': [], 'performanceQualified': False}
    base.write(report_path, report)

    async def command(payload):
        await client.command(payload)
        assert not (out/'qa-error.json').exists(), base.errors(out)['qaError']

    async def time_state():
        await command({'action': 'timeState'})
        return base.read(out/'time-state.json')

    try:
        await command({'action': 'view', 'camera': 'cam_canopy_under'})
        await command({'action': 'timePause', 'paused': True})
        # The preceding driver's cleanup may have just reset noon. Let any
        # outstanding previous-hour captures finish before measuring new ones.
        await asyncio.sleep(9)
        report['memoryBefore'] = await memory_snapshot(client, out)
        for hour in HOURS:
            await command({'action': 'view', 'camera': 'cam_canopy_under'})
            initial = await time_state(); reflection = initial['reflections']
            assert reflection and reflection['failed'] == 0 and not reflection['pending'], initial
            count = reflection['completed']; expected = len(reflection['probes'])
            assert abs(initial['hour']-hour) > .3, 'Need a distinct diagnostic hour.'
            await command({'action': 'timeSet', 'hour': hour})
            started = time.monotonic(); quiet = None; observations = []
            while time.monotonic()-started < 35:
                state = await time_state(); reflections = state['reflections']
                observations.append({'seconds': time.monotonic()-started, 'state': state})
                assert abs(state['hour']-hour) < .01 and state['paused'] and reflections['failed'] == 0
                if reflections['completed'] >= count+expected and not reflections['pending']:
                    quiet = quiet or time.monotonic()
                    if time.monotonic()-quiet >= 1.2:
                        for probe in reflections['probes']:
                            assert probe['mode'] == 'Realtime' and probe['texturePresent'] and probe['realtimeTextureCreated']
                            assert probe['textureWidth'] == probe['resolution']
                        break
                else:
                    quiet = None
                await asyncio.sleep(.35)
            else:
                raise TimeoutError('Both actual probe captures did not settle at '+str(hour))
            report['reflectionWaits'].append({'hour': hour, 'completionBefore': count, 'expectedNewCaptures': expected,
                                              'settled': True, 'observations': observations})
            for camera in CAMERAS:
                await command({'action': 'view', 'camera': camera})
                await asyncio.sleep(.65)
                name = 'shade-'+camera+'-hour-'+str(hour).replace('.', '_'); image_path = out/(name+'.png')
                assert not image_path.exists()
                await command({'action': 'capture', 'name': name})
                for _ in range(80):
                    try:
                        with Image.open(image_path) as image:
                            image.load(); assert image.size == (1920, 1080)
                        break
                    except (OSError, ValueError):
                        await asyncio.sleep(.15)
                else:
                    raise TimeoutError('Native still was not written: '+name)
                report['views'].append({'hour': hour, 'camera': camera, 'file': image_path.name,
                                        'sha256': base.sha(image_path), 'timeState': await time_state()})
                base.write(report_path, report)
        report['memoryAfter'] = await memory_snapshot(client, out)
        report['complete'] = True
    except Exception as error:
        report['error'] = repr(error)
        raise
    finally:
        for payload in [{'action': 'view', 'camera': 'follow'}, {'action': 'timeReset'}]:
            try:
                await client.command(payload)
            except Exception as error:
                report.setdefault('cleanupErrors', []).append(repr(error))
        after = base.identity()
        report['identityChangedPaths'] = [p for p in sorted(set(before)|set(after)) if before.get(p) != after.get(p)]
        report['runtimeErrors'] = base.errors(out)
        report['complete'] = bool(report['complete'] and not report['identityChangedPaths'] and
                                  not report['runtimeErrors']['matchingLines'] and not report['runtimeErrors']['qaError'] and
                                  report['runtimeErrors']['exists'] and not report.get('cleanupErrors'))
        report['finishedUtc'] = base.utc(); base.write(report_path, report)
    assert report['complete'], 'Inspect retained shade-audition-report.json.'
    print('Captured matched native shade/dusk/night views; critic and full qualification remain.', flush=True)


if __name__ == '__main__':
    asyncio.run(run(sys.argv[1]))
