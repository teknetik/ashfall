"""Capture one native visual iteration; no build, launch, full route or FPS verdict.

Root owns the only native Client and launches a fresh evidence folder separately.
Run --plan without live apps/input; see native-iteration-driver.md for host usage.
"""
import argparse
import asyncio
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / 'unity/AthenHill'
SCENE = PROJECT / 'Assets/AthenHill/Scenes/AthenHill.unity'
FIXED_CAMERAS = [
    'cam_reference_street', 'cam_courtyard_facade', 'cam_courtyard_ground',
    'cam_audit_field_supply_front', 'cam_audit_field_supply_door',
    'cam_audit_finery_front', 'cam_audit_finery_door',
    'cam_hill', 'cam_avenue', 'cam_gate', 'cam_grid', 'cam_whompah',
    'cam_hero', 'cam_terminal',
]
# These physical route points retain the successful V3 tread-center correction.
# Field Supply is w_02 (Z=-9); Finery is w_01 (Z=-18). Authoring must preserve
# collision/layout, or revise this dated driver deliberately against new evidence.
FACADES = [('field', -9., 16.35), ('finery', -18., 15.7)]


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def identity():
    """Hash the whole development player, including packed texture/mesh payloads."""
    files = [SCENE, Path(__file__), PROJECT / 'ProjectSettings/ProjectVersion.txt',
             PROJECT / 'Packages/manifest.json', PROJECT / 'Packages/packages-lock.json',
             PROJECT / 'ProjectSettings/QualitySettings.asset']
    files += [ROOT / 'unity/tools/native_memory.py']
    files += [PROJECT / 'Assets/AthenHill/Scripts' / name for name in
              ['NativeQa.cs', 'NativeAssetReview.cs', 'NativeVisualReview.cs', 'AthenDebugBridge.cs', 'FollowCamera.cs',
               'CityTimeReflections.cs', 'CityTimeOfDay.cs']]
    build = PROJECT / 'Builds/LinuxDevelopment'
    assert (build / 'AthenHill.x86_64').is_file(), 'Development build is absent.'
    files += [path for path in build.rglob('*') if path.is_file()]
    return {str(path.relative_to(ROOT)): sha(path) for path in sorted(set(files))}


def camera_sources(names):
    """Keep lens and complete parent transform records for matched-view audits."""
    parts = re.split(r'^--- !u!(\d+) &(-?\d+)\s*\n', SCENE.read_text(), flags=re.M)
    docs = {int(parts[i + 1]): (int(parts[i]), parts[i + 2]) for i in range(1, len(parts), 3)}
    objects, transforms, cameras = {}, {}, {}
    for fid, (kind, body) in docs.items():
        if kind == 1:
            match = re.search(r'^  m_Name: (.*)$', body, re.M)
            if match:
                objects[match[1]] = fid
        elif kind in {4, 20}:
            go = re.search(r'^  m_GameObject: \{fileID: (-?\d+)\}', body, re.M)
            if go:
                (transforms if kind == 4 else cameras)[int(go[1])] = (fid, body)
    result = {}
    for name in names:
        go = objects.get(name)
        assert go in cameras and go in transforms, 'Saved camera is absent: ' + name
        chain, current = [], transforms[go][0]
        while current:
            body = docs[current][1]
            chain.append({'fileID': current, 'record': body})
            match = re.search(r'^  m_Father: \{fileID: (-?\d+)\}', body, re.M)
            current = int(match[1]) if match else 0
        result[name] = {'cameraFileID': cameras[go][0], 'cameraRecord': cameras[go][1],
                        'transformChain': chain}
    return result


def errors(out):
    path = out / 'Player.log'
    lines = path.read_text(errors='replace').splitlines() if path.exists() else []
    pattern = re.compile(r'(?:\b\w*Exception\b|\bAssertion failed\b|\bShader error\b|'
                         r'\bCrash!!!\b|\bSegmentation fault\b|^Error:)', re.I)
    return {'playerLog': path.name, 'exists': path.exists(), 'sha256': sha(path) if path.exists() else None,
            'matchingLines': [{'line': i + 1, 'text': line} for i, line in enumerate(lines) if pattern.search(line)],
            'qaError': read(out / 'qa-error.json') if (out / 'qa-error.json').exists() else None,
            'scope': 'Pattern scan plus native command errors; visual review and full log inspection remain required.'}


async def run(args, names):
    # Importing this module or --plan never opens X11 or sends native commands.
    sys.path.insert(0, str(ROOT / 'unity/tools'))
    from native_client import Client
    from desktop_input import focus, key
    from native_memory import snapshot as memory_snapshot
    from Xlib import X
    from Xlib.ext import xtest
    from PIL import Image

    out = args.native.resolve()
    assert out.is_dir() and (out / 'pid').is_file(), 'Launch into a fresh folder first.'
    report_path = out / 'iteration-review.json'
    assert not report_path.exists(), 'Preserve previous evidence; launch a new iteration folder.'
    pid = int((out / 'pid').read_text().strip())
    assert Path(os.readlink(Path('/proc') / str(pid) / 'exe')).name == 'AthenHill.x86_64', 'PID is not the native player.'
    os.environ.update(ATHEN_NATIVE_DIR=str(out), ATHEN_NATIVE_PID=str(pid), ATHEN_EVIDENCE=str(out))
    report = {'complete': False, 'startedUtc': utc(), 'pid': pid, 'scope': __doc__,
              'cameras': names, 'cameraSources': camera_sources(names), 'captures': [], 'checkpoints': [],
              'performanceQualified': False, 'artAccepted': None, 'fullQualificationRequired': True}
    write(report_path, report)
    before = identity()
    write(out / 'iteration-identity-before.json', before)
    c, d, video = Client(), None, None

    def snap():
        return read(out / 'snapshot.json')

    async def command(payload):
        try:
            await c.command(payload)
        except Exception:
            if (out / 'qa-error.json').exists():
                raise RuntimeError(read(out / 'qa-error.json'))
            raise
        assert not (out / 'qa-error.json').exists(), 'Native bridge error: ' + str(errors(out)['qaError'])

    async def tap(name, duration):
        key(d, name, True)
        try:
            await asyncio.sleep(duration)
        finally:
            key(d, name, False)

    async def walk(label, target):
        started, previous, stalls = time.monotonic(), None, 0
        while True:
            state = snap()
            assert state['session']['state'] == 'Play', state['session']['state']
            p = state['player']['position']
            dx, dz = target[0] - p[0], target[2] - p[2]
            distance = math.hypot(dx, dz)
            if distance < .08:
                break
            stalls = stalls + 1 if previous is not None and abs(previous - distance) < .01 else 0
            assert time.monotonic() - started < 25 and stalls < 5, (label, p, distance)
            previous = distance
            await command({'action': 'cameraYaw', 'yaw': math.degrees(math.atan2(dx, dz))})
            await tap('w', min(1.5, max(.03, (distance - .08) / 3.4)))
            await asyncio.sleep(.18)
        await asyncio.sleep(.5)
        state = snap()
        assert state['player']['grounded'] and abs(state['player']['position'][1] - target[1]) < .15, state['player']
        report['checkpoints'].append({'name': label, 'target': target, 'snapshot': state})
        write(report_path, report)

    async def drag(dx, dy):
        xtest.fake_input(d, X.MotionNotify, x=cx, y=cy)
        d.sync()
        await asyncio.sleep(.1)
        xtest.fake_input(d, X.ButtonPress, 1)
        d.sync()
        await asyncio.sleep(.1)
        try:
            for step in range(1, 21):
                xtest.fake_input(d, X.MotionNotify, x=cx + round(dx * step / 20), y=cy + round(dy * step / 20))
                d.sync()
                await asyncio.sleep(.025)
        finally:
            xtest.fake_input(d, X.ButtonRelease, 1)
            d.sync()
        await asyncio.sleep(.2)

    async def pitch(degrees):
        await drag(0, round((degrees - snap()['camera']['pitch']) / .13))
        assert abs(snap()['camera']['pitch'] - degrees) < 2, 'Real mouse pitch did not reach target.'

    async def capture(name, camera=None, first_person=False):
        path = out / (name + '.png')
        assert not path.exists(), 'Preserve earlier capture: ' + name
        state = snap()
        assert [state['width'], state['height']] == [1920, 1080] and state['session']['state'] == 'Play'
        if first_person:
            assert state['camera']['firstPerson'] and not state['camera']['overlaps'], state['camera']
        await command({'action': 'capture', 'name': name})
        for _ in range(80):
            try:
                with Image.open(path) as image:
                    image.load()
                    assert image.size == (1920, 1080), image.size
                break
            except (FileNotFoundError, OSError):
                await asyncio.sleep(.1)
        else:
            raise TimeoutError(name)
        report['captures'].append({'path': path.name, 'sha256': sha(path), 'camera': camera,
                                   'firstPerson': first_person, 'snapshot': state})
        write(report_path, report)
        print('Captured ' + name, flush=True)

    try:
        d = focus()
        if snap()['session']['state'] == 'Paused':
            await tap('Escape', .1)
        assert snap()['session']['state'] == 'Play', 'Start with ordinary Play, without a modal.'
        await command({'action': 'resize', 'width': 1920, 'height': 1080})
        await asyncio.sleep(1.3)
        await command({'action': 'timeReset'})
        await command({'action': 'timePause', 'paused': True})
        await command({'action': 'timeState'})
        await command({'action': 'settingsSnapshot'})
        await command({'action': 'actorSnapshot'})
        report.update(settings=read(out / 'settings.json'), lighting=read(out / 'time-state.json'),
                      environment=read(out / 'environment.json'), actors=read(out / 'actors.json'))
        settings = report['settings']
        assert settings['renderScale'] == 1 and settings['video']['renderPercent'] == 100
        assert settings['video']['windowMode'] == 0 and settings['msaa'] == 4
        assert settings['textureLimit'] == 0 and settings['postProcessing'] is True
        assert report['environment']['actorCount'] == 9
        assert 'OpenGL' in report['environment']['api'], report['environment']['api']
        report['memoryBeforeViews'] = await memory_snapshot(c, out)
        for name in names:
            await command({'action': 'view', 'camera': name})
            await asyncio.sleep(.8)
            await capture(name, camera=name)

        await command({'action': 'view', 'camera': 'follow'})
        await command({'action': 'reset'})
        await walk('west lane setup', [12, 0, 0])
        await walk('Field Supply avenue setup', [12, 0, -9])
        d = focus()
        desktop = d.screen().root
        window = None
        for wid in desktop.get_full_property(d.intern_atom('_NET_CLIENT_LIST'), X.AnyPropertyType).value:
            candidate = d.create_resource_object('window', wid)
            prop = candidate.get_full_property(d.intern_atom('_NET_WM_PID'), X.AnyPropertyType)
            if prop is not None and int(prop.value[0]) == pid:
                window = candidate
                break
        assert window is not None, 'Native player window is absent.'
        origin, geometry = desktop.translate_coords(window, 0, 0), window.get_geometry()
        assert (geometry.width, geometry.height) == (1920, 1080)
        report['nativeWindow'] = {'x': origin.x, 'y': origin.y, 'width': geometry.width, 'height': geometry.height}
        cx, cy = origin.x + 960, origin.y + 540
        xtest.fake_input(d, X.MotionNotify, x=cx, y=cy)
        d.sync()
        for _ in range(10):
            xtest.fake_input(d, X.ButtonPress, 4)
            xtest.fake_input(d, X.ButtonRelease, 4)
            d.sync()
            await asyncio.sleep(.08)
        await asyncio.sleep(.4)
        assert snap()['camera']['firstPerson'], 'Real wheel zoom did not enter first person.'
        await pitch(0)
        movie = out / 'iteration-first-person.mp4'
        assert not movie.exists(), 'Preserve the previous movie.'
        video_started = time.monotonic()
        video_log = (out / 'iteration-video.log').open('wb')
        video = await asyncio.create_subprocess_exec(
            'ffmpeg', '-nostats', '-hide_banner', '-loglevel', 'warning', '-n',
            '-f', 'x11grab', '-framerate', '30', '-video_size', '1920x1080',
            '-i', os.environ.get('DISPLAY', ':0') + f'+{origin.x},{origin.y}',
            '-t', '180', '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '22',
            '-pix_fmt', 'yuv420p', str(movie), stdin=asyncio.subprocess.PIPE,
            stdout=video_log, stderr=video_log)
        try:
            for family, z, close_x in FACADES:
                await pitch(0)
                await walk(family + ' avenue', [12, 0, z])
                for label, point in [('first tread', [14.05, .25, z]), ('porch arris', [15., .5, z]),
                                     ('centered close view', [close_x, .5, z])]:
                    await walk(family + ' ' + label, point)
                await command({'action': 'cameraYaw', 'yaw': 90})
                await capture('iteration-first-person-' + family, first_person=True)
                before_look = snap()['camera']['yaw']
                await drag(-95, -25)
                assert abs(snap()['camera']['yaw'] - before_look) > 5, 'Real horizontal look did not respond.'
                await drag(95, 25)
                await pitch(52)
                await capture('iteration-first-person-' + family + '-threshold', first_person=True)
                await pitch(0)
                for label, point in [('porch return', [15., .5, z]), ('tread return', [14.05, .25, z]),
                                     ('avenue departure', [12., 0, z])]:
                    await walk(family + ' ' + label, point)
        finally:
            if video.returncode is None:
                await video.communicate(b'q')
            video_log.close()
            report['video'] = {'path': movie.name, 'exit': video.returncode,
                               'elapsedSeconds': time.monotonic() - video_started, 'sha256': sha(movie) if movie.exists() else None}
            assert video.returncode == 0, 'Native walkthrough encoder failed.'
            probe = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                                    'format=duration:stream=codec_type,width,height,avg_frame_rate',
                                    '-of', 'json', str(movie)], capture_output=True, text=True, check=True)
            report['video']['probe'] = json.loads(probe.stdout)
            streams = report['video']['probe']['streams']
            assert any(stream.get('codec_type') == 'video' and stream.get('width') == 1920
                       and stream.get('height') == 1080 for stream in streams), 'Movie dimensions are invalid.'
            duration = float(report['video']['probe']['format']['duration'])
            assert abs(duration - report['video']['elapsedSeconds']) < 3, 'Movie ended early or lost a substantial recording interval.'
        report['memoryAfterViewsAndLocalWalk'] = await memory_snapshot(c, out)
        report['complete'] = True
    except Exception as error:
        report['error'] = repr(error)
        raise
    finally:
        if d is not None:
            for name in ['w', 'a', 's', 'd', 'Escape']:
                key(d, name, False)
            xtest.fake_input(d, X.ButtonRelease, 1)
            d.sync()
        for payload in [{'action': 'view', 'camera': 'follow'}, {'action': 'timeReset'}]:
            try:
                await c.command(payload)
            except Exception as error:
                report.setdefault('cleanupErrors', []).append(repr(error))
        after = identity()
        write(out / 'iteration-identity-after.json', after)
        report['identityChangedPaths'] = [name for name in sorted(set(before) | set(after)) if before.get(name) != after.get(name)]
        report['runtimeErrors'] = errors(out)
        report['complete'] = bool(report['complete'] and not report['identityChangedPaths']
                                  and not report['runtimeErrors']['matchingLines'] and not report['runtimeErrors']['qaError']
                                  and report['runtimeErrors']['exists'] and not report.get('cleanupErrors'))
        report['finishedUtc'] = utc()
        write(report_path, report)
    assert report['complete'], 'Iteration capture incomplete; inspect retained iteration-review.json.'
    print('Captured native iteration; independent art review and full qualification remain outstanding.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('native', type=Path, nargs='?', help='Fresh launch_phase1_qa evidence folder.')
    parser.add_argument('--prop-cameras', nargs=3, metavar=('CRATE', 'TRASH', 'SCRAP'))
    parser.add_argument('--plan', action='store_true', help='Validate saved cameras and print plan without live apps/input.')
    args = parser.parse_args()
    names = list(dict.fromkeys(FIXED_CAMERAS + (args.prop_cameras or [])))
    if args.plan:
        print(json.dumps({'cameras': list(camera_sources(names)), 'propCamerasPending': not bool(args.prop_cameras),
                          'firstPersonFacades': FACADES, 'performanceQualified': False}, indent=2))
    else:
        assert args.native is not None and args.prop_cameras, 'Provide native folder and three saved prop cameras.'
        assert len(set(args.prop_cameras)) == 3, 'Provide three distinct prop cameras.'
        asyncio.run(run(args, names))
