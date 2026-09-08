"""Exercise the saved Linux atmosphere with real input and the development QA bridge."""
import asyncio
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / 'evidence/atmosphere/20260908/native'
OUT.mkdir(parents=True, exist_ok=True)


async def main():
    display = subprocess.check_output(['xrandr', '--current'], text=True)
    active = next((line.split()[0] for line in display.splitlines() if '*' in line), None)
    mode = active or 'x'.join(re.search(r'current (\d+) x (\d+)', display).groups())
    process = None
    report = {'complete': False, 'views': []}
    for name in ['snapshot.json', 'command.json', 'ack.json', 'qa-error.json']:
        (OUT / name).unlink(missing_ok=True)
    try:
        if mode != '1920x1080':
            subprocess.run(['xrandr', '--output', 'DP-0', '--mode', '1920x1080'], check=True)
        process = subprocess.Popen([str(ROOT / 'AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64'),
            '-force-glcore', '-screen-fullscreen', '1', '-screen-width', '1920', '-screen-height', '1080',
            '-logFile', str(OUT / 'Player.log'), '--athen-qa', str(OUT)],
            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        os.environ.update(ATHEN_NATIVE_DIR=str(OUT), ATHEN_NATIVE_PID=str(process.pid), ATHEN_EVIDENCE=str(OUT))
        from native_client import Client
        from desktop_input import focus, key
        deadline = time.monotonic() + 60
        while not (OUT / 'snapshot.json').exists():
            if process.poll() is not None: raise RuntimeError('Player exited during startup')
            if time.monotonic() > deadline: raise TimeoutError('No native snapshot')
            await asyncio.sleep(.2)
        d = focus()

        def snapshot(): return json.loads((OUT / 'snapshot.json').read_text())

        async def tap(name):
            key(d, name, True)
            try: await asyncio.sleep(.08)
            finally: key(d, name, False)
            await asyncio.sleep(.2)

        async def activate(name):
            for _ in range(30):
                if snapshot()['session']['focused'] == name:
                    await tap('Return')
                    return
                await tap('Tab')
            raise RuntimeError('Could not focus ' + name)

        await asyncio.sleep(3)
        if snapshot()['session']['state'] == 'Paused': await tap('Escape')
        s = snapshot()
        assert (s['width'], s['height']) == (1920, 1080)
        assert s['atmosphere'] and s['atmosphere']['dustPlaying']
        assert 0 < s['atmosphere']['dustParticles'] <= 64
        t0 = s['atmosphere']['windTime']
        await asyncio.sleep(.5)
        assert snapshot()['atmosphere']['windTime'] > t0
        report['animatedAtmosphere'] = True

        async with Client() as client:
            for name in ['cam_hill', 'cam_avenue', 'cam_gate', 'cam_grid', 'cam_whompah', 'cam_hero']:
                await client.command({'action': 'view', 'camera': name})
                await asyncio.sleep(.8)
                s = snapshot()
                report['views'].append({'camera': name, 'fps': s['fps'], 'triangles': s['triangles']})
                await client.command({'action': 'capture', 'name': name})
            await client.command({'action': 'view', 'camera': 'follow'})
            await client.command({'action': 'profileStart'})
            route = await asyncio.create_subprocess_exec(sys.executable, str(ROOT / 'tools/walk_route.py'))
            assert await route.wait() == 0, 'Keyboard traversal failed'
            await client.command({'action': 'profileStop'})
            await client.command({'action': 'capture', 'name': 'route-lattice'})
            loop = await asyncio.create_subprocess_exec(sys.executable, str(ROOT / 'tools/city_loop_check.py'))
            assert await loop.wait() == 0, 'City loop failed'
            # The city loop leaves Reduced Motion enabled and returns to normal gameplay.
            s = snapshot()
            assert s['session']['reducedMotion'] and s['session']['state'] == 'Play'
            assert s['atmosphere']['dustParticles'] == 0 and not s['atmosphere']['dustPlaying']
            t0 = s['atmosphere']['windTime']
            await asyncio.sleep(.6)
            assert snapshot()['atmosphere']['windTime'] == t0, 'Reduced Motion did not freeze the wind clock'
            report['reducedMotion'] = True
            await tap('Escape')
            await activate('reduced-motion')
            await tap('Escape')
            await asyncio.sleep(.8)
            s = snapshot()
            assert not s['session']['reducedMotion'] and s['atmosphere']['dustPlaying']
            assert s['atmosphere']['windTime'] > t0
            report['motionResumes'] = True
            await client.command({'action': 'goto', 'landmark': 'oa_hill'})
            await client.command({'action': 'capture', 'name': 'grass-close'})
            await client.command({'action': 'quit'})
        await asyncio.to_thread(process.wait, timeout=15)
        samples = json.loads((OUT / 'profile.json').read_text())
        walking = [s for s in samples if s['speed'] > 1 and s['state'] == 'Play']
        times = sorted(s['dt'] * 1000 for s in walking)
        report.update(environment=json.loads((OUT / 'environment.json').read_text()),
            walkingFrames=len(walking), averageWalkingFPS=1000 / statistics.mean(times),
            walkingFrameMs={'mean': statistics.mean(times), 'p95': times[int(len(times) * .95)],
                'p99': times[int(len(times) * .99)], 'max': max(times)},
            maxWalkingTriangles=max(s['tris'] for s in walking))
        log = (OUT / 'Player.log').read_text()
        assert not any(x in log for x in ['Exception:', 'NullReferenceException', 'Shader error', 'is not supported on this GPU'])
        assert report['maxWalkingTriangles'] <= 250000, 'Walking triangle budget exceeded'
        assert report['walkingFrameMs']['p99'] < 1000 / 58, 'Walking performance below 58 FPS'
        report['complete'] = True
        print(json.dumps(report, indent=2), flush=True)
    finally:
        if process and process.poll() is None:
            process.terminate(); process.wait(timeout=10)
        if mode != '1920x1080':
            subprocess.run(['xrandr', '--output', 'DP-0', '--mode', mode], check=True)
        (OUT / 'report.json').write_text(json.dumps(report, indent=2))


asyncio.run(main())
