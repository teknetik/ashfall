"""SOFTWARE-ADAPTED controls check; run only through run_adapted.py.

This is not a pass of unity/tools/controls_check.py. Input is real XTest on the
private display. QA commands only reset, inspect, capture and record physics.
Frame barriers replace wall-clock input timing. Sparse rendered jump samples
are replaced by separately identified fixed-step evidence, with original bounds.
"""
import asyncio
import hashlib
import json
import math
from pathlib import Path
import time

from Xlib import X
from Xlib.ext import xtest
from software_input import OUT, REPORT, Client, focus, key, snapshot, wait_frames, until
from software_input import tap as frame_tap


async def main():
    d = focus()
    REPORT.mkdir(exist_ok=True)
    destination = REPORT / 'controls-check.json'
    if destination.exists():
        raise RuntimeError('Refusing to overwrite earlier adapted controls evidence.')
    original = Path(__file__).resolve().parents[3] / 'unity/tools/controls_check.py'
    report = {
        'complete': False,
        'purpose': 'SOFTWARE-ADAPTED functional evidence only',
        'originalTestPassed': False,
        'originalScript': str(original),
        'originalSha256': hashlib.sha256(original.read_bytes()).hexdigest(),
        'checks': [],
        'notTested': [
            'Original 8 ms Space tap delivery',
            'Original second Space press 170 ms into a rendered jump / no double jump',
            'Original rendered jump peak samples and 60 FPS responsiveness',
            'GPU performance or temporal visual acceptance',
        ],
    }
    trace_active = False

    def record(name, **values):
        report['checks'].append(dict(name=name, **values))
        print('PASS (software-adapted):', name, flush=True)

    def motion(x, y):
        desktop = d.screen().root.get_geometry()
        xtest.fake_input(d, X.MotionNotify, x=round(x * desktop.width / 1920),
                         y=round(y * desktop.height / 1080))
        d.sync()

    def button(number, down):
        xtest.fake_input(d, X.ButtonPress if down else X.ButtonRelease, number)
        d.sync()

    async def tap(name, frames=2, settle=2):
        return await frame_tap(d, name, frames=frames, settle=settle)

    async def drag(number=1, start=(900, 450), delta=(180, -80)):
        motion(*start)
        await wait_frames(2)
        button(number, True)
        try:
            # GameInput intentionally ignores delta on the Orbit press frame.
            await wait_frames(2)
            for i in range(1, 7):
                motion(int(start[0] + delta[0] * i / 6),
                       int(start[1] + delta[1] * i / 6))
                await wait_frames(1)
        finally:
            button(number, False)
        await wait_frames(2)

    async def wheel(up, count, position=(1000, 400), stop_at_bound=False):
        motion(*position)
        await wait_frames(2)
        for _ in range(count):
            button(4 if up else 5, True)
            button(4 if up else 5, False)
            current = await wait_frames(2)
            # Large counts in the original only establish the clamped endpoint.
            # Stop at that same endpoint, after one additional saturation event.
            bound = 0 if up else 10
            if stop_at_bound and abs(current['camera']['boom'] - bound) < .01:
                button(4 if up else 5, True)
                button(4 if up else 5, False)
                await wait_frames(2)
                break

    def same_camera(a, b):
        return all(abs(a[k] - b[k]) < .05 for k in ('yaw', 'pitch', 'boom'))

    async def baseline():
        return (await wait_frames(2))['camera']

    async def jump_trace(client, name, held_frames, lower_peak):
        nonlocal trace_active
        await until(lambda s: s['player']['grounded'])
        baseline_y = snapshot()['player']['position'][1]
        path = REPORT / (name + '-motion.json')
        if path.exists():
            raise RuntimeError('Refusing to overwrite fixed-step jump evidence.')
        await client.command({'action': 'motionStart'})
        trace_active = True
        started = time.monotonic()
        key(d, 'space', True)
        try:
            await wait_frames(held_frames)
            if held_frames == 1:
                key(d, 'space', False)
                await wait_frames(8)
            await until(lambda s: s['player']['grounded'])
            await wait_frames(4)
            # For the held test, stop recording before release so its complete
            # grounded tail is evidence from while the physical key is held.
            await client.command({'action': 'motionStop'})
            trace_active = False
        finally:
            key(d, 'space', False)
        await wait_frames(2)
        # Copy immediately: NativeQa uses one motion.json for every recording.
        source = OUT / 'motion.json'
        raw = source.read_bytes()
        with path.open('xb') as stream:
            stream.write(raw)
        rows = json.loads(raw)
        assert rows, 'No fixed-step samples recorded'
        jumps = [r for r in rows if r['JumpStarted']]
        assert len(jumps) == 1, ('Expected exactly one accepted jump', jumps)
        peak = max(r['position'][1] for r in rows) - baseline_y
        assert lower_peak < peak < 1.5, peak
        assert rows[-1]['Grounded'] and snapshot()['player']['grounded']
        assert abs(snapshot()['player']['position'][1] - baseline_y) < .05
        late = [r for r in rows if r['time'] - jumps[0]['time'] > 1]
        assert late, 'Insufficient fixed-time coverage after landing'
        assert all(r['Grounded'] for r in late), 'Space repeated a jump'
        record(name, evidence='Fixed-step physics trace; not rendered peak sampling',
               lowerPeakExclusive=lower_peak, upperPeakExclusive=1.5, peak=peak,
               acceptedJumps=len(jumps), fixedStepSamples=len(rows),
               fixedTimeSpan=rows[-1]['time'] - rows[0]['time'],
               initialHeldRenderFrames=held_frames, heldUntilTraceStop=held_frames > 1,
               wallSeconds=time.monotonic()-started,
               trace=str(path), sha256=hashlib.sha256(raw).hexdigest())

    try:
        await wait_frames(2)
        if snapshot()['session']['state'] == 'Paused':
            await tap('Escape')
        assert (snapshot()['width'], snapshot()['height']) == (1920, 1080)
        async with Client() as client:
            await client.command({'action': 'reset'})
            await wheel(True, 30, stop_at_bound=True)
            await wheel(False, 6)
            before = await baseline()
            motion(650, 400)
            await wait_frames(2)
            assert same_camera(before, snapshot()['camera']), 'Unheld mouse moved the camera'
            before = await baseline()
            await drag(3)
            assert same_camera(before, snapshot()['camera']), 'Right mouse still controls look'
            before = await baseline()
            await drag()
            turned = snapshot()['camera']
            assert turned['yaw'] - before['yaw'] > 15 and before['pitch'] - turned['pitch'] > 5, turned
            motion(600, 300)
            await wait_frames(2)
            assert same_camera(turned, snapshot()['camera']), 'Look continued after release'
            record('Left-drag look; unheld and right mouse do not rotate', before=before, after=turned)

            await client.command({'action': 'uiSnapshot'})
            layout_raw = (OUT / 'ui-layout.json').read_bytes()
            with (REPORT / 'controls-hud-layout.json').open('xb') as stream:
                stream.write(layout_raw)
            layout = json.loads(layout_raw)
            elements = {e['name']: e for e in layout['elements'] if e['name']}
            slot = elements['slot1']
            assert slot['visible'] and slot['enabled'], slot
            x, y, width, height = slot['bounds']
            root_width = elements['hud']['bounds'][2]
            assert root_width > 0 and width > 0 and height > 0
            panel_scale = layout['width'] / root_width
            hud_point = ((x + width / 2) * panel_scale, (y + height / 2) * panel_scale)
            assert 0 <= hud_point[0] < 1920 and 0 <= hud_point[1] < 1080, hud_point
            report['hudTarget'] = dict(name='slot1', bounds=slot['bounds'], point=hud_point, panelScale=panel_scale)
            before = await baseline()
            await drag(start=hud_point, delta=(180, -130))
            assert same_camera(before, snapshot()['camera']), 'Dragging from a HUD button rotated the camera'
            before = await baseline()
            await wheel(True, 2, hud_point)
            assert same_camera(before, snapshot()['camera']), 'Wheel over HUD zoomed the camera'
            motion(*hud_point)
            await wait_frames(2)
            button(1, True)
            try:
                await wait_frames(2)
            finally:
                button(1, False)
            await wait_frames(2)
            assert 'Water Flask' in snapshot()['session']['notice'], 'HUD click was swallowed'
            record('HUD clicks work and HUD drags/wheel leave the camera alone')

            await client.command({'action': 'reset'})
            await wheel(True, 1)
            assert abs(snapshot()['camera']['boom'] - 3.5) < .05, snapshot()['camera']
            await wheel(True, 6)
            first = snapshot()
            assert first['camera']['firstPerson'] and first['camera']['playerHidden']
            assert first['camera']['distance'] < .01
            assert abs(first['camera']['position'][1] - first['player']['position'][1] - 1.65) < .03
            await client.command({'action': 'capture', 'name': 'adapted-first-person'})
            first = snapshot()
            await drag(delta=(-140, 45))
            assert abs(snapshot()['camera']['yaw'] - first['camera']['yaw']) > 10
            before = snapshot()['player']['position']
            key(d, 'w', True)
            try:
                await until(lambda s: math.dist(before, s['player']['position']) > 1)
            finally:
                key(d, 'w', False)
            await wait_frames(2)
            moving = snapshot()
            assert math.dist(before, moving['player']['position']) > 1
            assert math.dist(moving['camera']['position'], [moving['player']['position'][0], moving['player']['position'][1]+1.65, moving['player']['position'][2]]) < .05
            record('Wheel reaches clear eye-level first person with look and movement', camera=first['camera'])
            await wheel(False, 1)
            assert not snapshot()['camera']['firstPerson'] and not snapshot()['camera']['playerHidden']
            await wheel(False, 30, stop_at_bound=True)
            assert abs(snapshot()['camera']['boom'] - 10) < .01
            await wheel(True, 8)
            await client.command({'action': 'reset'})
            await client.command({'action': 'capture', 'name': 'adapted-third-person'})
            record('Wheel returns to third person, restores the model and respects maximum zoom')

            await jump_trace(client, 'Held Space physics jump and landing without repetition', 8, .95)
            await jump_trace(client, 'Frame-delivered Space pulse physics jump and landing', 1, .9)

            for opener, state in [('Escape', 'Paused'), ('e', 'Dialogue'), ('5', 'Inventory')]:
                await tap(opener)
                assert snapshot()['session']['state'] == state, snapshot()['session']
                before = snapshot()
                await drag(start=(200, 350), delta=(150, 70))
                await wheel(True, 3, (200, 350))
                await tap('space')
                assert same_camera(before['camera'], snapshot()['camera']), state + ' leaked camera input'
                assert math.dist(before['player']['position'], snapshot()['player']['position']) < .04, state + ' leaked jump input'
                await tap('Escape')
                await wait_frames(2)
                assert snapshot()['player']['grounded'], 'Space pressed in a panel leaked into gameplay'
                record(state + ' blocks look, zoom and jumping without queuing a jump on close')

            for landmark in ['west_gate', 'shop_row_w', 'shop_row_e', 'hill_tree']:
                await client.command({'action': 'goto', 'landmark': landmark})
                for yaw in [0, 90, 180, 270]:
                    await client.command({'action': 'cameraYaw', 'yaw': yaw})
                    await wait_frames(2)
                    assert not snapshot()['camera']['overlaps'], (landmark, yaw, snapshot()['camera'])
            record('Third-person camera collision: 16 landmark/orientation checks')
            await client.command({'action': 'reset'})
            await client.command({'action': 'capture', 'name': 'adapted-controls-verified'})
        report['complete'] = True
    except BaseException as error:
        report['error'] = str(error)
        raise
    finally:
        for name in ['space', 'w', 'Shift_L']:
            key(d, name, False)
        for number in (1, 3, 4, 5):
            button(number, False)
        if trace_active:
            try:
                async with Client() as client:
                    await client.command({'action': 'motionStop'})
                raw = (OUT / 'motion.json').read_bytes()
                with (REPORT / 'interrupted-controls-motion.json').open('xb') as stream:
                    stream.write(raw)
            except BaseException as error:
                report['traceCleanupError'] = str(error)
        with destination.open('x') as stream:
            json.dump(report, stream, indent=2)


if __name__ == '__main__':
    asyncio.run(main())
