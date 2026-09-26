"""Native diagnostic asset-camera movies after capture_native_iteration.py.

Root is the only Client/input operator. This script records real native pixels;
camera motion uses the explicitly enabled development QA bridge. It does not
qualify player traversal, frame-time performance or AAA visual acceptance.
"""
import argparse
import asyncio
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time

import capture_native_iteration as base

DEFAULT_PASSES = [
    {'camera': 'cam_ground_crate', 'target': [15.65, 1.08, -20.7], 'offset': [0, .2, -1.1]},
    {'camera': 'cam_ground_trash', 'target': [15.4, .64, -21.3], 'offset': [0, -.1, 1.2]},
    {'camera': 'cam_ground_scrap', 'target': [35, .6, -7], 'offset': [0, -.25, -1.2]},
    {'camera': 'cam_ground_scrap_back', 'target': [35, .6, -7], 'offset': [0, -.15, 1.1]},
    {'camera': 'cam_canopy_top', 'target': [14.6, 3.6, -18.5], 'offset': [0, 0, 1.3]},
    {'camera': 'cam_canopy_under', 'target': [14.6, 3.6, -18.5], 'offset': [0, 0, 1.1]},
]
HOURS = [12, 16]


def plan(args):
    passes = base.read(args.plan_file) if args.plan_file else DEFAULT_PASSES
    assert isinstance(passes, list) and len(passes) == 6, 'Provide the six ground/canopy passes.'
    assert {p['camera'] for p in passes} == {p['camera'] for p in DEFAULT_PASSES}
    for item in passes:
        for key in ['target', 'offset']:
            assert len(item[key]) == 3 and all(math.isfinite(v) for v in item[key]), item
        assert 0 < math.sqrt(sum(v*v for v in item['offset'])) <= 4, 'Require nonzero camera travel of at most 4 m.'
    present = set(re.findall(r'^  m_Name: (.*)$', base.SCENE.read_text(), flags=re.M))
    missing = [p['camera'] for p in passes if p['camera'] not in present]
    sources = base.camera_sources([p['camera'] for p in passes if p['camera'] in present])
    return passes, sources, missing


async def run(args, passes, sources):
    # Offline --plan never imports X11 or sends a command.
    sys.path.insert(0, str(base.ROOT / 'unity/tools'))
    from native_client import Client
    from desktop_input import focus
    from Xlib import X
    from PIL import Image

    out = args.native.resolve()
    path = out/'asset-passes-report.json'
    assert not path.exists(), 'Preserve the previous supplement; use a fresh native iteration folder.'
    assert base.read(out/'iteration-review.json')['complete'], 'Complete the base native iteration first.'
    pid = int((out/'pid').read_text().strip())
    assert Path(os.readlink(Path('/proc')/str(pid)/'exe')).name == 'AthenHill.x86_64', 'Native PID is absent or changed.'
    os.environ.update(ATHEN_NATIVE_DIR=str(out), ATHEN_NATIVE_PID=str(pid), ATHEN_EVIDENCE=str(out))
    before = base.identity()
    assert before == base.read(out/'iteration-identity-after.json'), 'The build/source identity differs from the base capture.'
    base.write(out/'asset-passes-identity-before.json', before)
    report = {'complete': False, 'startedUtc': base.utc(), 'pid': pid, 'scope': __doc__,
              'hours': HOURS, 'requestedSeconds': args.seconds, 'plan': passes, 'cameraSources': sources,
              'driverSha256': base.sha(Path(__file__)), 'planFile': str(args.plan_file) if args.plan_file else None,
              'planFileSha256': base.sha(args.plan_file) if args.plan_file else None,
              'passes': [], 'reflectionWaits': [], 'performanceQualified': False, 'traversalQualified': False, 'artAccepted': None,
              'overlapCheck': 'NativeAssetReview samples a 0.08 m sphere every active pass frame; ordinary snapshot also records the separate 0.20 m camera overlap query.'}
    base.write(path, report)
    client = Client()

    def snap():
        return base.read(out/'snapshot.json')

    def save():
        base.write(path, report)

    async def command(payload):
        try:
            await client.command(payload)
        except Exception:
            if (out/'qa-error.json').exists():
                raise RuntimeError(base.read(out/'qa-error.json'))
            raise
        assert not (out/'qa-error.json').exists(), base.errors(out)['qaError']

    async def clock_state():
        await command({'action': 'timeState'})
        return base.read(out/'time-state.json')

    async def settle_reflections(hour, require_new_capture, initial_completed):
        """Observe actual pending/completion state, including sequential captures."""
        started, quiet_since, observations = time.monotonic(), None, []
        wait_report = {'hour': hour, 'startedUtc': base.utc(), 'settled': False, 'observations': observations,
                       'newCaptureRequired': require_new_capture, 'completionCounterBefore': initial_completed,
                       'scope': 'Observed completed counter, no pending capture for at least 1.2 s and zero failures. Diagnostics do not expose per-probe captured hour; exact probe state/intensity is retained for review.'}
        report['reflectionWaits'].append(wait_report); save()
        while time.monotonic()-started < 35:
            state = await clock_state()
            observations.append({'elapsedSeconds': time.monotonic()-started, 'state': state}); save()
            assert abs(state['hour']-hour) < .01 and state['paused'] is True, state
            reflection = state['reflections']
            assert reflection is not None and reflection['failed'] == 0, state
            capture_ready = not require_new_capture or reflection['completed'] > initial_completed
            if not reflection['pending'] and capture_ready:
                quiet_since = quiet_since or time.monotonic()
                if time.monotonic()-quiet_since >= 1.2:
                    # An unnamed RenderTexture can be valid: check its actual
                    # allocation and dimensions, not the display-name string.
                    if require_new_capture:
                        assert state['realtimeReflectionsEnabled'] is True, state
                    for probe in reflection['probes']:
                        assert probe['texturePresent'] and probe['textureWidth'] > 0, probe
                        if probe['mode'] == 'Realtime':
                            assert probe['realtimeTextureCreated'] and probe['textureWidth'] == probe['resolution'], probe
                    wait_report.update(settled=True, final=state, finishedUtc=base.utc()); save()
                    return wait_report
            else:
                quiet_since = None
            await asyncio.sleep(.35)
        raise TimeoutError('Reflections did not reach the required observed state: ' + json.dumps(observations[-1]))

    async def state(label):
        await command({'action': 'reviewAssetState'})
        return {'label': label, 'utc': base.utc(), 'motion': base.read(out/'asset-review-state.json'),
                'snapshot': snap()}

    async def still(name):
        image_path = out/(name+'.png')
        assert not image_path.exists(), 'Preserve previous asset still.'
        await command({'action': 'capture', 'name': name})
        for _ in range(80):
            try:
                with Image.open(image_path) as image:
                    image.load()
                    assert image.size == (1920, 1080)
                return {'path': image_path.name, 'sha256': base.sha(image_path)}
            except (FileNotFoundError, OSError):
                await asyncio.sleep(.1)
        raise TimeoutError(name)

    try:
        focus()
        assert snap()['session']['state'] == 'Play', 'Use ordinary Play with HUD visible and no modal.'
        await command({'action': 'resize', 'width': 1920, 'height': 1080})
        await asyncio.sleep(1.3)
        await command({'action': 'settingsSnapshot'})
        settings = base.read(out/'settings.json')
        assert settings['renderScale'] == 1 and settings['video']['renderPercent'] == 100
        assert settings['video']['windowMode'] == 0 and [snap()['width'], snap()['height']] == [1920, 1080]
        assert settings['msaa'] == 4 and settings['textureLimit'] == 0
        report.update(settings=settings, environment=base.read(out/'environment.json'))
        assert report['environment']['actorCount'] == 9 and 'OpenGL' in report['environment']['api']
        await command({'action': 'timeReset'})
        initial = await clock_state()
        assert abs(initial['defaultHour']-12) < .01, 'This plan requires authored noon at hour 12.'
        for hour in HOURS:
            # Move to a relevant local reflection region before changing its time.
            await command({'action': 'view', 'camera': passes[0]['camera']})
            before_time = await clock_state()
            await command({'action': 'timePause', 'paused': True})
            await command({'action': 'timeSet', 'hour': hour})
            changed_hour = abs(before_time['hour']-hour) >= .3
            hour_settling = await settle_reflections(hour, changed_hour, before_time['reflections']['completed'])
            for item in passes:
                name = 'asset-pass-'+item['camera']+'-hour-'+str(hour)
                print('Recording '+name, flush=True)
                entry = {'name': name, 'camera': item['camera'], 'hour': hour, 'request': dict(item, seconds=args.seconds),
                         'startedUtc': base.utc(), 'complete': False, 'states': [], 'hourTransition': hour_settling}
                report['passes'].append(entry); save()
                d = focus()
                await command({'action': 'view', 'camera': item['camera']})
                entry['reflectionSettling'] = await settle_reflections(hour, False, hour_settling['final']['reflections']['completed'])
                entry['startStill'] = await still(name+'-start')
                assert snap()['session']['state'] == 'Play'
                desktop, window = d.screen().root, None
                for wid in desktop.get_full_property(d.intern_atom('_NET_CLIENT_LIST'), X.AnyPropertyType).value:
                    candidate = d.create_resource_object('window', wid)
                    prop = candidate.get_full_property(d.intern_atom('_NET_WM_PID'), X.AnyPropertyType)
                    if prop is not None and int(prop.value[0]) == pid:
                        window = candidate; break
                assert window is not None, 'Native window is absent.'
                origin, geometry = desktop.translate_coords(window, 0, 0), window.get_geometry()
                assert (geometry.width, geometry.height) == (1920, 1080)
                entry['nativeWindow'] = {'x': origin.x, 'y': origin.y, 'width': geometry.width, 'height': geometry.height}
                movie, movie_log = out/(name+'.mp4'), out/(name+'-ffmpeg.log')
                assert not movie.exists() and not movie_log.exists(), 'Preserve previous asset movie.'
                record_started = time.monotonic()
                with movie_log.open('wb') as log:
                    video = await asyncio.create_subprocess_exec(
                        'ffmpeg', '-nostats', '-hide_banner', '-loglevel', 'warning', '-n',
                        '-f', 'x11grab', '-framerate', '30', '-video_size', '1920x1080',
                        '-i', os.environ.get('DISPLAY', ':0')+f'+{origin.x},{origin.y}',
                        '-t', str(args.seconds+12), '-c:v', 'libx264', '-preset', 'ultrafast',
                        '-crf', '20', '-pix_fmt', 'yuv420p', str(movie),
                        stdin=asyncio.subprocess.PIPE, stdout=log, stderr=log)
                    try:
                        await asyncio.sleep(.5)
                        assert video.returncode is None, 'Recorder exited before camera motion.'
                        started = time.monotonic()
                        await command(dict(action='reviewAssetPass', **item, seconds=args.seconds))
                        entry['states'].append(await state('start')); save()
                        await asyncio.sleep(max(0, args.seconds*.5-(time.monotonic()-started)))
                        entry['states'].append(await state('middle')); save()
                        await asyncio.sleep(max(0, args.seconds+.15-(time.monotonic()-started)))
                        entry['states'].append(await state('end'))
                        while entry['states'][-1]['motion']['active'] and time.monotonic()-started < args.seconds+4:
                            await asyncio.sleep(.2)
                            entry['states'].append(await state('end-wait'))
                        entry['motionElapsedSeconds'] = time.monotonic()-started
                        await asyncio.sleep(.25)
                    finally:
                        # The video remains a real, uninterrupted screen recording.
                        # Stills are captured outside it to avoid screenshot stalls.
                        if video.returncode is None:
                            await video.communicate(b'q')
                        entry['video'] = {'path': movie.name, 'exit': video.returncode,
                                          'elapsedSeconds': time.monotonic()-record_started,
                                          'sha256': base.sha(movie) if movie.exists() else None}
                        save()
                assert video.returncode == 0, 'Asset movie recorder failed.'
                final, middle, first = entry['states'][-1], entry['states'][1], entry['states'][0]
                motion = final['motion']
                assert all(s['snapshot']['session']['state'] == 'Play' and
                           [s['snapshot']['width'], s['snapshot']['height']] == [1920, 1080] for s in entry['states'])
                assert motion['sourceCamera'] == item['camera'] and motion['sampledFrames'] > middle['motion']['sampledFrames'] > first['motion']['sampledFrames'] > 0
                assert first['motion']['active'] and middle['motion']['active'] and motion['active'] is False
                assert motion['overlappingFrames'] == 0, 'Diagnostic camera overlapped collision during its pass.'
                assert math.dist(final['snapshot']['camera']['position'], motion['end']) < .025, 'Camera did not reach the requested endpoint.'
                assert math.dist(final['snapshot']['player']['position'], first['snapshot']['player']['position']) < .01, 'Player moved during diagnostic pass.'
                assert entry['motionElapsedSeconds'] >= args.seconds-.1
                probe = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                    'format=duration:stream=codec_type,width,height,avg_frame_rate', '-of', 'json', str(movie)],
                    capture_output=True, text=True, check=True)
                entry['video']['probe'] = json.loads(probe.stdout)
                actual_duration = float(entry['video']['probe']['format']['duration'])
                assert actual_duration >= args.seconds and abs(actual_duration-entry['video']['elapsedSeconds']) < 2
                assert any(s.get('codec_type') == 'video' and s.get('width') == 1920 and s.get('height') == 1080
                           for s in entry['video']['probe']['streams'])
                entry['endStill'] = await still(name+'-end')
                entry['finalTimeState'] = await clock_state()
                assert not entry['finalTimeState']['reflections']['pending'] and entry['finalTimeState']['reflections']['failed'] == 0
                entry.update(complete=True, completedFromStateAndEndpoint=True, finishedUtc=base.utc()); save()
                print('Completed '+name+' with '+str(motion['sampledFrames'])+' native camera samples and zero overlap frames.', flush=True)
        report['complete'] = len(report['passes']) == 12 and all(p['complete'] for p in report['passes'])
    except Exception as error:
        report['error'] = repr(error)
        raise
    finally:
        # NativeQa's view operation explicitly cancels NativeAssetReview before
        # returning to follow. Resetting the clock alone would not stop motion.
        for payload in [{'action': 'view', 'camera': 'follow'}, {'action': 'timeReset'}]:
            try:
                await client.command(payload)
            except Exception as error:
                report.setdefault('cleanupErrors', []).append(repr(error))
        try:
            await client.command({'action': 'reviewAssetState'})
            report['cleanupMotionState'] = base.read(out/'asset-review-state.json')
            assert report['cleanupMotionState']['active'] is False
        except Exception as error:
            report.setdefault('cleanupErrors', []).append(repr(error))
        after = base.identity()
        base.write(out/'asset-passes-identity-after.json', after)
        report['identityChangedPaths'] = [p for p in sorted(set(before)|set(after)) if before.get(p) != after.get(p)]
        report['runtimeErrors'] = base.errors(out)
        report['driverSha256After'] = base.sha(Path(__file__))
        report['planFileSha256After'] = base.sha(args.plan_file) if args.plan_file else None
        report['complete'] = bool(report['complete'] and not report['identityChangedPaths'] and not report.get('cleanupErrors')
            and report['runtimeErrors']['exists'] and not report['runtimeErrors']['matchingLines'] and not report['runtimeErrors']['qaError']
            and report['driverSha256'] == report['driverSha256After'] and report['planFileSha256'] == report['planFileSha256After'])
        report['finishedUtc'] = base.utc(); save()
    assert report['complete'], 'Asset supplement incomplete; inspect retained report and failed evidence.'
    print('Recorded 12 diagnostic asset passes. Native traversal, performance and independent art acceptance remain separate.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('native', type=Path, nargs='?')
    parser.add_argument('--seconds', type=float, default=7)
    parser.add_argument('--plan-file', type=Path, help='Root-reviewed JSON list with the same six cameras and safe target/offset vectors.')
    parser.add_argument('--plan', action='store_true', help='Print plan and missing saved cameras without live apps/input.')
    args = parser.parse_args()
    assert 6 <= args.seconds <= 8
    passes, sources, missing = plan(args)
    if args.plan:
        print(json.dumps({'passes': passes, 'hours': HOURS, 'seconds': args.seconds,
                          'savedCameras': list(sources), 'missingCameras': missing,
                          'requiresRootCollisionPathReview': True}, indent=2))
    else:
        assert args.native is not None and not missing, 'Provide native folder and create missing saved cameras: '+str(missing)
        asyncio.run(run(args, passes, sources))
