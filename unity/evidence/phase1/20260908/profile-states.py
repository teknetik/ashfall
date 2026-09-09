"""Supplement the moving-route sample with real-input shop/travel/UI timings."""
import asyncio
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'unity/tools'))
from native_client import Client
from check_weathering import stats
from desktop_input import focus, key

OUT = pathlib.Path(os.environ['ATHEN_NATIVE_DIR'])

async def main():
    client = Client()
    report = {'complete': False, 'kind': 'supplemental real-input city states'}
    try:
        display = focus()
        await client.command({'action': 'reset'})
        await client.command({'action': 'settingsSnapshot'})
        report['settings'] = json.loads((OUT / 'settings.json').read_text())
        report['environment'] = json.loads((OUT / 'environment.json').read_text())
        assert report['settings']['renderScale'] == 1
        assert report['settings']['vSync'] == 0
        assert report['settings']['frameLimit'] == -1
        assert report['environment']['actorCount'] == 9
        viewport = json.loads((OUT / 'snapshot.json').read_text())
        report['measuredViewport'] = [viewport['width'], viewport['height']]
        assert report['measuredViewport'] == [1920, 1080]
        await asyncio.sleep(10)
        # Warm the actual UI states and capture them before the timed sample.
        child = await asyncio.create_subprocess_exec(sys.executable, str(ROOT / 'unity/tools/city_loop_check.py'))
        assert await child.wait() == 0
        async def tap(name, seconds=.08):
            key(display, name, True)
            try:
                await asyncio.sleep(seconds)
            finally:
                key(display, name, False)
            await asyncio.sleep(.2)
        def snapshot():
            return json.loads((OUT / 'snapshot.json').read_text())
        async def click(name):
            for _ in range(30):
                if snapshot()['session']['focused'] == name:
                    await tap('Return')
                    return
                await tap('Tab')
            raise RuntimeError('Could not focus ' + name)
        async def goto(name):
            await client.command({'action': 'goto', 'landmark': name})
            await asyncio.sleep(.3)
        await client.command({'action': 'profileStart'})
        await goto('mission_slab')
        await client.command({'action': 'cameraYaw', 'yaw': 180})
        await tap('a', .4)
        await tap('d', .4)
        await asyncio.sleep(4)
        await goto('basic_general')
        await tap('e')
        assert snapshot()['session']['state'] == 'Dialogue'
        await click('choice0')
        assert snapshot()['session']['state'] == 'Shop'
        await asyncio.sleep(5)
        await tap('Escape')
        await goto('lattice_jack')
        await tap('e')
        assert snapshot()['session']['state'] == 'Grid'
        await asyncio.sleep(2)
        await click('node0')
        await asyncio.sleep(4)
        await tap('Escape')
        await tap('5')
        await asyncio.sleep(1)
        await tap('Escape')
        await tap('6')
        await asyncio.sleep(1)
        await tap('Escape')
        await tap('Escape')
        await asyncio.sleep(2)
        await tap('Escape')
        await client.command({'action': 'profileStop'})
        frames = json.loads((OUT / 'profile.json').read_text())
        report['timing'] = stats(frames)
        report['stateTiming'] = {state: stats([f for f in frames if f['state'] == state]) for state in sorted(set(f['state'] for f in frames))}
        assert {'Shop', 'Grid', 'Play'} <= set(report['stateTiming'])
        report['warmup'] = 'Ten seconds plus the full real-input city loop before timing; screenshots are outside the sample.'
        report['complete'] = True
    finally:
        (OUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        await client.command({'action': 'quit'})
    print(json.dumps(report, indent=2))

asyncio.run(main())
