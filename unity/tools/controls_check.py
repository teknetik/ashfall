"""Real X11 mouse/keyboard regression checks against an opted-in native QA player.

Set ATHEN_NATIVE_DIR and ATHEN_NATIVE_PID, as for walk_route.py.
The fullscreen player must render at 1920x1080; desktop scaling is accounted for.
No input is injected through the QA bridge.
"""
import asyncio
import json
import math
import os
from pathlib import Path
import time

from Xlib import X
from Xlib.ext import xtest
from desktop_input import focus, key
from native_client import Client

OUT = Path(os.environ['ATHEN_NATIVE_DIR'])


async def main():
    d = focus()
    report = {'complete': False, 'checks': []}

    def snap():
        return json.loads((OUT / 'snapshot.json').read_text())

    def record(name, **values):
        report['checks'].append(dict(name=name, **values))
        print('PASS:', name, flush=True)

    def motion(x, y):
        desktop = d.screen().root.get_geometry()
        xtest.fake_input(d, X.MotionNotify, x=round(x * desktop.width / 1920), y=round(y * desktop.height / 1080))
        d.sync()

    def button(number, down):
        xtest.fake_input(d, X.ButtonPress if down else X.ButtonRelease, number)
        d.sync()

    async def tap(name, duration=.05):
        key(d, name, True)
        try:
            await asyncio.sleep(duration)
        finally:
            key(d, name, False)
        await asyncio.sleep(.2)

    async def drag(number=1, start=(900, 450), delta=(180, -80)):
        motion(*start)
        await asyncio.sleep(.15)
        button(number, True)
        try:
            await asyncio.sleep(.08)
            for i in range(1, 7):
                motion(int(start[0] + delta[0] * i / 6), int(start[1] + delta[1] * i / 6))
                await asyncio.sleep(.035)
        finally:
            button(number, False)
        await asyncio.sleep(.25)

    async def wheel(up, count, position=(1000, 400)):
        motion(*position)
        await asyncio.sleep(.12)
        for _ in range(count):
            button(4 if up else 5, True)
            button(4 if up else 5, False)
            await asyncio.sleep(.045)
        await asyncio.sleep(.5)

    def same_camera(a, b):
        return all(abs(a[k] - b[k]) < .05 for k in ('yaw', 'pitch', 'boom'))

    async def sample_jump(duration, second_press=False):
        samples = []
        start = time.monotonic()
        pressed_again = False
        while time.monotonic() - start < duration:
            elapsed = time.monotonic() - start
            if second_press and not pressed_again and elapsed > .17:
                await tap('space', .02)
                pressed_again = True
            samples.append({'time': elapsed, 'player': snap()['player']})
            await asyncio.sleep(.035)
        return samples

    try:
        await asyncio.sleep(.5)
        if snap()['session']['state'] == 'Paused':
            await tap('Escape')
        assert (snap()['width'], snap()['height']) == (1920, 1080)
        async with Client() as client:
            await client.command({'action': 'reset'})
            await wheel(True, 30)
            await wheel(False, 6)
            await asyncio.sleep(.3)
            baseline = snap()['camera']
            motion(650, 400)
            await asyncio.sleep(.3)
            assert same_camera(baseline, snap()['camera']), 'Unheld mouse moved the camera'
            await drag(3)
            assert same_camera(baseline, snap()['camera']), 'Right mouse still controls look'
            await drag()
            turned = snap()['camera']
            assert turned['yaw'] - baseline['yaw'] > 15 and baseline['pitch'] - turned['pitch'] > 5, turned
            motion(600, 300)
            await asyncio.sleep(.3)
            assert same_camera(turned, snap()['camera']), 'Look continued after release'
            record('Left-drag look; unheld and right mouse do not rotate', before=baseline, after=turned)

            # Slot 1 is a real HUD button at this verified 1080p layout.
            await drag(start=(840, 960), delta=(180, -130))
            assert same_camera(turned, snap()['camera']), 'Dragging from a HUD button rotated the camera'
            await wheel(True, 2, (840, 960))
            assert same_camera(turned, snap()['camera']), 'Wheel over HUD zoomed the camera'
            motion(840, 960)
            button(1, True)
            await asyncio.sleep(.07)
            button(1, False)
            await asyncio.sleep(.3)
            assert 'Water Flask' in snap()['session']['notice'], 'HUD click was swallowed'
            record('HUD clicks work and HUD drags/wheel leave the camera alone')

            await client.command({'action': 'reset'})
            await wheel(True, 1)
            assert abs(snap()['camera']['boom'] - 3.5) < .05, snap()['camera']
            await wheel(True, 6)
            first = snap()
            assert first['camera']['firstPerson'] and first['camera']['playerHidden']
            assert first['camera']['distance'] < .01
            assert abs(first['camera']['position'][1] - first['player']['position'][1] - 1.65) < .03
            await client.command({'action': 'capture', 'name': 'first-person'})
            await drag(delta=(-140, 45))
            assert abs(snap()['camera']['yaw'] - first['camera']['yaw']) > 10
            before = snap()['player']['position']
            await tap('w', .4)
            moving = snap()
            assert math.dist(before, moving['player']['position']) > 1
            assert math.dist(moving['camera']['position'], [moving['player']['position'][0], moving['player']['position'][1]+1.65, moving['player']['position'][2]]) < .05
            record('Wheel reaches clear eye-level first person with look and movement', camera=first['camera'])
            await wheel(False, 1)
            assert not snap()['camera']['firstPerson'] and not snap()['camera']['playerHidden']
            await wheel(False, 30)
            assert abs(snap()['camera']['boom'] - 10) < .01
            await wheel(True, 8)
            await client.command({'action': 'reset'})
            await client.command({'action': 'capture', 'name': 'third-person'})
            record('Wheel returns to third person, restores the model and respects maximum zoom')

            baseline_y = snap()['player']['position'][1]
            key(d, 'space', True)
            try:
                held = await sample_jump(1.4)
            finally:
                key(d, 'space', False)
            peak = max(s['player']['position'][1] for s in held) - baseline_y
            assert .95 < peak < 1.5, peak
            assert all(s['player']['grounded'] for s in held if s['time'] > 1), 'Holding Space repeated the jump'
            assert abs(snap()['player']['position'][1] - baseline_y) < .05
            record('Space jumps and lands; holding it does not auto-repeat', peak=peak, samples=held)

            # A short tap must survive until a physics update, with no midair extra jump.
            key(d, 'space', True)
            await asyncio.sleep(.008)
            key(d, 'space', False)
            tapped = await sample_jump(1.1, second_press=True)
            peak = max(s['player']['position'][1] for s in tapped) - baseline_y
            assert .9 < peak < 1.5, peak
            assert snap()['player']['grounded'] and abs(snap()['player']['position'][1] - baseline_y) < .05
            record('Short Space tap works and a second midair press cannot double-jump', peak=peak, samples=tapped)

            for opener, state in [('Escape', 'Paused'), ('e', 'Dialogue'), ('5', 'Inventory')]:
                await tap(opener)
                assert snap()['session']['state'] == state, snap()['session']
                before = snap()
                await drag(start=(200, 350), delta=(150, 70))
                await wheel(True, 3, (200, 350))
                await tap('space')
                assert same_camera(before['camera'], snap()['camera']), state + ' leaked camera input'
                assert math.dist(before['player']['position'], snap()['player']['position']) < .04, state + ' leaked jump input'
                await tap('Escape')
                await asyncio.sleep(.35)
                assert snap()['player']['grounded'], 'Space pressed in a panel leaked into gameplay'
                record(state + ' blocks look, zoom and jumping without queuing a jump on close')

            for landmark in ['west_gate', 'shop_row_w', 'shop_row_e', 'hill_tree']:
                await client.command({'action': 'goto', 'landmark': landmark})
                for yaw in [0, 90, 180, 270]:
                    await client.command({'action': 'cameraYaw', 'yaw': yaw})
                    await asyncio.sleep(.3)
                    assert not snap()['camera']['overlaps'], (landmark, yaw, snap()['camera'])
            record('Third-person camera collision: 16 landmark/orientation checks')
            await client.command({'action': 'reset'})
            await client.command({'action': 'capture', 'name': 'controls-verified'})
        report['complete'] = True
    except Exception as error:
        report['error'] = str(error)
        raise
    finally:
        for name in ['space', 'w', 'Shift_L']:
            key(d, name, False)
        button(1, False)
        button(3, False)
        (OUT / 'controls-check.json').write_text(json.dumps(report, indent=2))


asyncio.run(main())
