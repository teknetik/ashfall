"""Verify the Meshy gate in the native player, including real movement and interaction."""
import asyncio
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path('/home/teknetik/code/ao2/unity')
sys.path.insert(0, str(ROOT / 'tools'))
OUT = Path(os.environ.get('ATHEN_RING_EVIDENCE', ROOT / 'evidence/ring-gate/20260908/native'))
OUT.mkdir(parents=True, exist_ok=True)


async def main():
    display = subprocess.check_output(['xrandr', '--current'], text=True)
    mode = next(line.split()[0] for line in display.splitlines() if '*' in line)
    process = None
    report = {'complete': False, 'views': [], 'gateChecks': []}
    try:
        if mode != '1920x1080':
            subprocess.run(['xrandr', '--output', 'DP-0', '--mode', '1920x1080'], check=True)
        for name in ('snapshot.json', 'environment.json', 'ack.json', 'command.json', 'qa-error.json'):
            (OUT / name).unlink(missing_ok=True)
        process = subprocess.Popen([os.environ.get('ATHEN_GROUNDING_PLAYER', str(ROOT / 'AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64')),
            '-force-glcore', '-screen-fullscreen', '1', '-screen-width', '1920', '-screen-height', '1080',
            '-logFile', str(OUT / 'Player.log'), '--athen-qa', str(OUT)],
            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        os.environ.update(ATHEN_NATIVE_DIR=str(OUT), ATHEN_NATIVE_PID=str(process.pid), ATHEN_EVIDENCE=str(OUT))
        from native_client import Client
        from desktop_input import focus, key
        deadline = time.monotonic() + 60
        while not (OUT / 'snapshot.json').exists():
            if process.poll() is not None:
                raise RuntimeError('Player exited during startup')
            if time.monotonic() > deadline:
                raise TimeoutError('No native snapshot')
            await asyncio.sleep(.2)
        d = focus()
        await asyncio.sleep(3)

        def snapshot():
            return json.loads((OUT / 'snapshot.json').read_text())

        async def tap(name, seconds=.08):
            key(d, name, True)
            try:
                await asyncio.sleep(seconds)
            finally:
                key(d, name, False)
            await asyncio.sleep(.2)

        report['environment'] = json.loads((OUT / 'environment.json').read_text())
        assert report['environment']['actorCount'] == 9  # Includes the installed yard mechanic.
        assert (snapshot()['width'], snapshot()['height']) == (1920, 1080)
        async with Client() as client:
            if snapshot()['session']['state'] == 'Paused':
                await tap('Escape')
            for camera in ['cam_ring_front', 'cam_hill', 'cam_avenue', 'cam_gate']:
                await client.command({'action': 'view', 'camera': camera})
                await asyncio.sleep(2)
                await client.command({'action': 'profileStart'})
                await asyncio.sleep(3)
                await client.command({'action': 'profileStop'})
                frames = json.loads((OUT / 'profile.json').read_text())
                (OUT / (camera + '-profile.json')).write_text(json.dumps(frames))
                fps = len(frames) / sum(f['dt'] for f in frames)
                result = {'camera': camera, 'averageFps': fps, 'frames': len(frames),
                          'p99FrameMs': sorted(f['dt'] * 1000 for f in frames)[int(len(frames) * .99)],
                          'maxDraws': max(f['draws'] for f in frames), 'maxTriangles': max(f['tris'] for f in frames)}
                report['views'].append(result)
                assert fps >= 58, result
                await client.command({'action': 'capture', 'name': camera})
                await asyncio.sleep(.3)
                print(result, flush=True)

            for camera in ['cam_grounding_stairs', 'cam_grounding_bench', 'cam_grounding_hill_bench', 'cam_grounding_shop_side', 'cam_grounding_shop_back', 'cam_grounding_general_back', 'cam_grounding_hall_back', 'cam_grid']:
                await client.command({'action': 'view', 'camera': camera})
                await asyncio.sleep(.5)
                await client.command({'action': 'capture', 'name': camera})
            await client.command({'action': 'view', 'camera': 'follow'})
            await client.command({'action': 'goto', 'landmark': 'ring_gate'})
            await client.command({'action': 'cameraYaw', 'yaw': 0})
            await asyncio.sleep(1)
            s = snapshot()
            assert s['player']['grounded'], s['player']
            assert 'offline' in s['session']['notice'], s['session']
            assert any(a['name'] == 'Ring hum' and a['playing'] for a in s['audio']['sources']), s['audio']
            report['gateChecks'].append({'check': 'arrival', 'snapshot': s})
            before = s['audio']['UnavailableCount']
            await tap('e')
            s = snapshot()
            assert s['audio']['UnavailableCount'] > before
            assert 'offline' in s['session']['notice']
            await client.command({'action': 'capture', 'name': 'ring-interaction'})

            # Walk from the gate to the court and back. Record actual displacement,
            # ground contact and camera overlap rather than only trusting a teleport.
            start = snapshot()['player']['position']
            await tap('s', 2)
            outside = snapshot()
            assert outside['player']['grounded']
            assert math.dist(start, outside['player']['position']) > 3, outside['player']
            await tap('w', 2)
            returned = snapshot()
            assert returned['player']['grounded']
            assert returned['player']['position'][2] > outside['player']['position'][2] + 2
            assert math.dist(start, returned['player']['position']) < .45, 'Could not walk back up the platform steps: ' + str(returned['player'])
            assert not returned['camera']['overlaps'], returned['camera']
            report['gateChecks'].append({'check': 'walk-out-and-back', 'start': start, 'outside': outside, 'returned': returned})
            await client.command({'action': 'capture', 'name': 'ring-approach'})

            check = await asyncio.create_subprocess_exec(sys.executable, '/home/teknetik/code/ao2/unity/evidence/grounding/20260908/interaction-check.py')
            assert await check.wait() == 0, 'Native city loop failed'
            await client.command({'action': 'quit'})
        await asyncio.to_thread(process.wait, timeout=15)
        log = (OUT / 'Player.log').read_text()
        assert 'Exception:' not in log and 'NullReferenceException' not in log
        report['complete'] = True
        print('PASS: ring gate rendering, movement, offline interaction, audio and dialogues, trading and lattice travel', flush=True)
    except Exception as error:
        report['error'] = str(error)
        raise
    finally:
        if process and process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
        if mode != '1920x1080':
            subprocess.run(['xrandr', '--output', 'DP-0', '--mode', mode], check=True)
        (OUT / 'report.json').write_text(json.dumps(report, indent=2))


asyncio.run(main())
