"""Real-input close review of the correctly identified Field Supply and Finery.

Dedicated September 9 reference-street check; the historical shared
check_weathering_proximity.py and its earlier evidence remain untouched.
Field Supply is w_02, centered at Z=-9; Finery is w_01, centered at Z=-18.
Targets are grounded in the retained exact building source and threshold export,
with current saved diagnostic-camera positions providing an independent check.
"""
import asyncio
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'unity/tools'))
from Xlib import X
from Xlib.ext import xtest
from PIL import Image
from native_client import Client
from desktop_input import focus, key

OUT = Path(os.environ['ATHEN_NATIVE_DIR'])
SOURCE = ROOT / 'art/building_weathering_20260909/unity-source.json'
PORCHES = ROOT / 'art/reference_street_20260909/threshold-source.json'


def source_targets():
    rows = json.loads(SOURCE.read_text())
    threshold = json.loads(PORCHES.read_text())
    source = {r['path']: r for r in rows}
    porches = {r['path']: r for r in threshold}
    targets = [
        dict(family='field', label='Field Supply', centerZ=-9.,
             sourcePath='Ward shop architecture/field_supply/Workshop shutter/field_supply Rolled shutter slat 0',
             porchPath='AuthoredWorld/BLD_shop_w_02_porch',
             close=[16.35, .5, -9.], plantView=[15.95, .5, -12.0],
             plantTarget=[17.62, .70, -12.52]),
        dict(family='finery', label='Finery', centerZ=-18.,
             sourcePath='Phase 1 Finery frontage/Door/Door threshold cap',
             porchPath='AuthoredWorld/BLD_shop_w_01_porch',
             close=[15.7, .5, -18.], plantView=[15.6, .5, -20.7],
             plantTarget=[16.48, .70, -21.4]),
    ]
    for target in targets:
        row = source[target['sourcePath']]
        porch = porches[target['porchPath']]
        lo = [min(p[k] for p in porch['positions']) for k in range(3)]
        hi = [max(p[k] for p in porch['positions']) for k in range(3)]
        target['sourceBounds'] = row['bounds']
        target['porchBounds'] = dict(min=lo, max=hi)
        assert row['bounds']['min'][2] < target['centerZ'] < row['bounds']['max'][2]
        for point in [target['close'], target['plantView']]:
            assert lo[0] < point[0] < hi[0] and lo[2] < point[2] < hi[2]
            assert abs(point[1] - hi[1]) < .0001
    return targets


async def main():
    assert not (OUT / 'reference-proximity.json').exists(), 'Preserve earlier proximity evidence.'
    c = Client()
    d = focus()
    targets = source_targets()
    report = dict(complete=False, scope=__doc__, checkpoints=[], views=[], targets=targets,
                  sourceSha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                  thresholdSourceSha256=hashlib.sha256(PORCHES.read_bytes()).hexdigest(),
                  video='reference-first-person.mp4')

    def snap():
        return json.loads((OUT / 'snapshot.json').read_text())

    async def tap(name, duration):
        key(d, name, True)
        try:
            await asyncio.sleep(duration)
        finally:
            key(d, name, False)

    async def walk(name, target):
        start = time.monotonic()
        while True:
            p = snap()['player']['position']
            dx, dz = target[0] - p[0], target[2] - p[2]
            distance = math.hypot(dx, dz)
            if distance < .17:
                break
            assert time.monotonic() - start < 35, (name, p)
            await c.command({'action': 'cameraYaw', 'yaw': math.degrees(math.atan2(dx, dz))})
            await tap('w', min(1.5, max(.03, (distance - .08) / 3.4)))
            await asyncio.sleep(.18)
        state = snap()
        assert state['player']['grounded'] and abs(state['player']['position'][1] - target[1]) < .15, state['player']
        report['checkpoints'].append(dict(name=name, intendedPosition=target, snapshot=state))
        print('PASS ' + name, flush=True)

    root = d.screen().root
    window = None
    for wid in root.get_full_property(d.intern_atom('_NET_CLIENT_LIST'), X.AnyPropertyType).value:
        w = d.create_resource_object('window', wid)
        pid = w.get_full_property(d.intern_atom('_NET_WM_PID'), X.AnyPropertyType)
        if pid is not None and int(pid.value[0]) == int(os.environ['ATHEN_NATIVE_PID']):
            window = w
            break
    assert window is not None, 'Native window is absent.'
    origin = root.translate_coords(window, 0, 0)
    geometry = window.get_geometry()
    assert (geometry.width, geometry.height) == (1920, 1080)
    cx, cy = origin.x + geometry.width // 2, origin.y + geometry.height // 2

    async def drag(dx, dy):
        xtest.fake_input(d, X.MotionNotify, x=cx, y=cy)
        d.sync()
        await asyncio.sleep(.12)
        xtest.fake_input(d, X.ButtonPress, 1)
        d.sync()
        await asyncio.sleep(.12)
        try:
            for i in range(1, 21):
                xtest.fake_input(d, X.MotionNotify, x=cx + round(dx * i / 20), y=cy + round(dy * i / 20))
                d.sync()
                await asyncio.sleep(.04)
        finally:
            xtest.fake_input(d, X.ButtonRelease, 1)
            d.sync()
        await asyncio.sleep(.3)

    async def pitch_to(degrees):
        await drag(0, round((degrees - snap()['camera']['pitch']) / .13))

    async def capture(name, description):
        state = snap()
        assert state['camera']['firstPerson'] and not state['camera']['overlaps'], state['camera']
        image_path = OUT / (name + '.png')
        assert not image_path.exists(), 'Preserve earlier close-up.'
        await c.command({'action': 'capture', 'name': name})
        for attempt in range(70):
            try:
                with Image.open(image_path) as image:
                    image.load()
                    dimensions = list(image.size)
                break
            except (FileNotFoundError, OSError):
                await asyncio.sleep(.1)
        else:
            raise TimeoutError(name)
        assert dimensions == [1920, 1080]
        report['views'].append(dict(path=image_path.name, description=description, snapshot=state,
                                   sha256=hashlib.sha256(image_path.read_bytes()).hexdigest()))

    video = None
    try:
        if snap()['session']['state'] == 'Paused':
            await tap('Escape', .1)
        await c.command({'action': 'view', 'camera': 'follow'})
        await c.command({'action': 'reset'})
        await c.command({'action': 'timeReset'})
        await c.command({'action': 'timePause', 'paused': True})
        await walk('west lane', [12, 0, 0])
        movie = OUT / report['video']
        assert not movie.exists(), 'Preserve earlier movie.'
        video = await asyncio.create_subprocess_exec(
            'ffmpeg', '-hide_banner', '-loglevel', 'error', '-f', 'x11grab', '-framerate', '30',
            '-video_size', '1920x1080', '-i', os.environ.get('DISPLAY', ':0') + f'+{origin.x},{origin.y}',
            '-t', '210', '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '22', '-pix_fmt', 'yuv420p',
            str(movie), stdin=asyncio.subprocess.PIPE)
        for target in targets:
            label, family, z = target['label'], target['family'], target['centerZ']
            await walk(label + ' avenue approach', [12, 0, z])
            await walk(label + ' first tread', [14.15, .25, z])
            await walk(label + ' porch arris', [15.0, .5, z])
            await walk(label + ' centered close view', target['close'])
            await c.command({'action': 'cameraYaw', 'yaw': 90})
            xtest.fake_input(d, X.MotionNotify, x=cx, y=cy)
            d.sync()
            for i in range(10):
                xtest.fake_input(d, X.ButtonPress, 4)
                xtest.fake_input(d, X.ButtonRelease, 4)
                d.sync()
                await asyncio.sleep(.08)
            await asyncio.sleep(.4)
            assert snap()['camera']['firstPerson'], snap()['camera']
            await pitch_to(0)
            await capture('first-person-' + family, label + ' centered on its actual shutter or door.')
            before = snap()
            await drag(-95, -25)
            after = snap()
            assert abs(after['camera']['yaw'] - before['camera']['yaw']) > 5, 'Real mouse-look did not respond.'
            assert after['camera']['firstPerson'] and not after['camera']['overlaps'], after['camera']
            await drag(95, 25)
            await pitch_to(52)
            await capture('first-person-' + family + '-threshold', label + ' near porch surface, joints and retained walking top.')
            await walk(label + ' joint-growth review', target['plantView'])
            p = snap()['camera']['position']
            aim = target['plantTarget']
            dx, dz = aim[0] - p[0], aim[2] - p[2]
            await c.command({'action': 'cameraYaw', 'yaw': math.degrees(math.atan2(dx, dz))})
            await pitch_to(math.degrees(math.atan2(p[1] - aim[1], math.hypot(dx, dz))))
            await capture('first-person-' + family + '-joint-growth', label + ' localized vegetation and facade/porch edge.')
            await walk(label + ' porch return', target['close'])
            await walk(label + ' first tread return', [14.15, .25, z])
            await walk(label + ' avenue departure', [12, 0, z])
        report['complete'] = True
    except Exception as error:
        report['error'] = repr(error)
        raise
    finally:
        key(d, 'w', False)
        if video:
            await video.communicate(b'q')
            report['videoExit'] = video.returncode
            if video.returncode != 0:
                report['complete'] = False
        (OUT / 'reference-proximity.json').write_text(json.dumps(report, indent=2))
        await c.command({'action': 'timeReset'})
    assert report['complete'] and report.get('videoExit') == 0, 'Incomplete proximity/movie check.'
    print('PASS: centered Field Supply/Finery views, both treads and porches, joint plants, real zoom/look and camera clearance.', flush=True)


if __name__ == '__main__':
    asyncio.run(main())
