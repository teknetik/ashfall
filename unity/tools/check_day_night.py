"""Native time-control/input checks and matched dawn/noon/dusk/night evidence.

Attach with ATHEN_NATIVE_PID and ATHEN_NATIVE_DIR to an opted-in development player.
The player remains open, clock reset to its authored default, for further route QA.
This records visual evidence; it does not assign art acceptance scores.
"""
import asyncio
import json
import math
import os
import pathlib
import time
from native_client import Client
from desktop_input import focus, key, click
from Xlib import X
from Xlib.ext import xtest

OUT = pathlib.Path(os.environ['ATHEN_NATIVE_DIR'])
VIEWS = os.environ.get('ATHEN_TIME_VIEWS', 'cam_avenue,cam_terminal,cam_p1_finery_front,cam_p1_vex_face,cam_p1_tree_roots').split(',')


def timing(frames):
    values = sorted(f['dt'] * 1000 for f in frames)
    if not values:
        raise AssertionError('No timing frames recorded')
    def pct(p): return values[min(len(values) - 1, int((len(values) - 1) * p))]
    def counter(name):
        valid = [f[name] for f in frames if f.get(name, -1) > 0]
        return {'mean': sum(valid) / len(valid), 'maximum': max(valid)} if valid else 'unavailable'
    return dict(frames=len(values), seconds=sum(values) / 1000, averageFps=1000 * len(values) / sum(values),
                p50Ms=pct(.5), p95Ms=pct(.95), p99Ms=pct(.99), maxMs=max(values),
                hitchesOver33ms=sum(v > 33.33 for v in values),
                cpuFrameMs=counter('cpuMs'), gpuFrameMs=counter('gpuMs'), mainThreadMs=counter('mainMs'), renderThreadMs=counter('renderMs'),
                draws=counter('draws'), batches=counter('batches'), setPass=counter('setPass'), submittedTriangles=counter('tris'),
                meets60fpsAndP99=1000 * len(values) / sum(values) >= 60 and pct(.99) <= 16.67)


async def main():
    c = Client(); d = focus(); root = d.screen().root
    report = {'complete': False, 'inputChecks': [], 'states': [], 'timings': {}}
    origin = None
    for wid in root.get_full_property(d.intern_atom('_NET_CLIENT_LIST'), X.AnyPropertyType).value:
        w = d.create_resource_object('window', wid)
        pid = w.get_full_property(d.intern_atom('_NET_WM_PID'), X.AnyPropertyType)
        if pid is not None and int(pid.value[0]) == int(os.environ['ATHEN_NATIVE_PID']):
            origin = root.translate_coords(w, 0, 0); break
    assert origin is not None, 'Native player window missing'
    def snap(): return json.loads((OUT / 'snapshot.json').read_text())
    async def state():
        await c.command({'action': 'timeState'})
        return json.loads((OUT / 'time-state.json').read_text())
    async def tap(name, duration=.10):
        key(d, name, True)
        try: await asyncio.sleep(duration)
        finally: key(d, name, False)
        await asyncio.sleep(.2)
    async def button(name):
        await c.command({'action': 'uiSnapshot'})
        ui = json.loads((OUT / 'ui-layout.json').read_text())
        item = next(e for e in ui['elements'] if e['name'] == name and e['visible'] and e['enabled'])
        x, y, width, height = item['bounds']
        # This project uses a 1920×1080 reference panel; scale via the actual panel bounds.
        viewport = next(e for e in ui['elements'] if e['name'] == 'developer-time-overlay' and e['visible']) if name.startswith('developer-time') else None
        sx = ui['width'] / viewport['bounds'][2] if viewport else 1
        sy = ui['height'] / viewport['bounds'][3] if viewport else 1
        click(d, int(origin.x + (x + width / 2) * sx), int(origin.y + (y + height / 2) * sy))
        await asyncio.sleep(.25)
    async def keyboard_button(name):
        for _ in range(40):
            if snap()['session']['focused'] == name:
                await tap('Return'); return
            await tap('Tab', .04)
        raise AssertionError('Keyboard focus did not reach ' + name)
    async def reflection_ready():
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            s = await state()
            if s['reflections']['failed']:
                raise AssertionError('Reflection update failed: ' + str(s['reflections']))
            if not s['reflections']['pending'] and s['reflections']['status'] in ('Reflections current', 'Authored reflections'):
                await asyncio.sleep(.5); return await state()
            await asyncio.sleep(.4)
        raise AssertionError('Reflections did not settle')
    try:
        if snap()['session']['state'] == 'Paused': await tap('Escape')
        await c.command({'action': 'view', 'camera': 'follow'}); await c.command({'action': 'reset'})
        await c.command({'action': 'timeReset'})
        initial = await state()
        assert initial['paused'] and abs(initial['hour'] - initial['defaultHour']) < .001
        await tap('F8'); opened = await state()
        assert opened['menuOpen'] and snap()['session']['state'] == 'Paused'
        before = snap(); await tap('w', .5); await tap('space')
        xtest.fake_input(d, X.ButtonPress, 4); xtest.fake_input(d, X.ButtonRelease, 4); d.sync(); await asyncio.sleep(.3)
        after = snap()
        assert math.dist(before['player']['position'], after['player']['position']) < .01, 'Developer menu movement leak'
        assert abs(before['camera']['distance'] - after['camera']['distance']) < .001, 'Developer menu zoom leak'
        await c.command({'action': 'capture', 'name': 'time-menu-1080p'})
        await keyboard_button('developer-time-dusk')
        assert abs((await state())['hour'] - 17.5) < .001
        await tap('Escape'); assert snap()['session']['state'] == 'Play' and not (await state())['menuOpen']
        report['inputChecks'].append('F8 open, movement/jump/wheel blocked, keyboard preset, Esc closes without reopening pause')
        await tap('Escape'); await tap('F8'); await tap('F8')
        assert snap()['session']['state'] == 'Paused', 'Opening from pause did not preserve pause'
        await tap('Escape'); report['inputChecks'].append('Opening and closing from an existing pause preserves that state')

        await c.command({'action': 'settingsSnapshot'})
        report['environment'] = json.loads((OUT / 'environment.json').read_text())
        report['settings'] = json.loads((OUT / 'settings.json').read_text())
        assert report['environment']['actorCount'] == 9
        assert report['settings']['renderScale'] == 1 and snap()['width'] == 1920 and snap()['height'] == 1080
        await c.command({'action': 'goto', 'landmark': 'mission_slab'})
        for preset in ('dawn', 'noon', 'dusk', 'night'):
            await c.command({'action': 'view', 'camera': 'cam_terminal'})
            await tap('F8'); await button('developer-time-' + preset); await tap('F8')
            s = await reflection_ready(); report['states'].append(dict(preset=preset, state=s))
            assert s['circuits'] and sum(circuit['activeLights'] for circuit in s['circuits']) > 0, 'No practical fixture lights are installed in the active review area'
            if preset == 'night':
                assert s['sunVisibility'] == 0 and s['skySunVisibility'] == 0
                assert s['lampStrength'] > .99
                assert all(p['mode'] == 'Realtime' for p in s['reflections']['probes']), 'Daytime baked probe remained'
            for view in VIEWS:
                await c.command({'action': 'view', 'camera': view}); await asyncio.sleep(.6)
                await c.command({'action': 'capture', 'name': preset + '-' + view}); await asyncio.sleep(.3)
            await c.command({'action': 'view', 'camera': 'cam_avenue'})
            await c.command({'action': 'profileStart'}); await asyncio.sleep(8); await c.command({'action': 'profileStop'})
            frames = json.loads((OUT / 'profile.json').read_text())
            (OUT / (preset + '-profile.json')).write_text(json.dumps(frames))
            report['timings'][preset] = timing(frames)

        # Reduced-motion setting is exercised through the real pause interface.
        await tap('Escape'); await keyboard_button('reduced-motion')
        assert snap()['session']['reducedMotion']
        await tap('F8'); await button('developer-time-speed60'); await button('developer-time-play')
        first = await state(); await asyncio.sleep(2); second = await state()
        travelled = (second['hour'] - first['hour']) % 24
        assert second['ReducedMotionSpeedLimited'] and 0 < travelled < .05, 'Reduced motion did not cap timelapse'
        await tap('F8'); assert snap()['session']['state'] == 'Paused'
        await keyboard_button('reduced-motion'); await tap('Escape')
        assert not snap()['session']['reducedMotion']
        report['inputChecks'].append('Reduced motion caps 60× to ordinary clock speed; pause/menu teardown remains correct')
        await c.command({'action': 'timePause', 'paused': False})
        await c.command({'action': 'timeSpeed', 'speed': 60})
        await c.command({'action': 'timeSet', 'hour': 17})
        await c.command({'action': 'profileStart'}); await asyncio.sleep(15); await c.command({'action': 'profileStop'})
        frames = json.loads((OUT / 'profile.json').read_text())
        (OUT / 'accelerated-transition-profile.json').write_text(json.dumps(frames))
        report['timings']['acceleratedTransitions'] = timing(frames)
        report['complete'] = True
    except Exception as error:
        report['error'] = str(error); raise
    finally:
        for name in ('w', 'space', 'F8', 'Escape'): key(d, name, False)
        try:
            if (await state())['menuOpen']: await tap('F8')
            await c.command({'action': 'timeReset'})
            if snap()['session']['state'] == 'Paused': await tap('Escape')
        finally:
            (OUT / 'day-night-report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__': asyncio.run(main())
