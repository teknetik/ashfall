"""Smoke-test the rebuilt native player using the existing QA bridge and real keys."""
import asyncio
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evidence' / 'ward-guard' / datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
OUT.mkdir(parents=True)

async def main():
    display = subprocess.check_output(['xrandr', '--current'], text=True)
    mode = next(line.split()[0] for line in display.splitlines() if '*' in line)
    process = None
    report = {'complete': False, 'output': str(OUT), 'views': [], 'motion': []}
    try:
        subprocess.run(['xrandr', '--output', 'DP-0', '--mode', '1920x1080'], check=True)
        process = subprocess.Popen([str(ROOT / 'AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64'),
            '-force-glcore', '-screen-fullscreen', '1', '-screen-width', '1920', '-screen-height', '1080',
            '-logFile', str(OUT / 'Player.log'), '--athen-qa', str(OUT)], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        os.environ.update(ATHEN_NATIVE_DIR=str(OUT), ATHEN_NATIVE_PID=str(process.pid), ATHEN_EVIDENCE=str(OUT))
        from native_client import Client
        from desktop_input import focus, key
        deadline = time.monotonic() + 60
        while not (OUT / 'snapshot.json').exists():
            if process.poll() is not None: raise RuntimeError('Player exited during startup')
            if time.monotonic() > deadline: raise TimeoutError('No native snapshot')
            await asyncio.sleep(.2)
        d = focus()
        await asyncio.sleep(3)
        def snapshot(): return json.loads((OUT / 'snapshot.json').read_text())
        report['environment'] = json.loads((OUT / 'environment.json').read_text())
        assert report['environment']['actorCount'] == 8
        assert (snapshot()['width'], snapshot()['height']) == (1920, 1080)
        async with Client() as client:
            await client.command({'action': 'capture', 'name': 'guard-at-gate'})
            await client.command({'action': 'cameraYaw', 'yaw': -90})
            try:
                for name in ['walk', 'run', 'idle']:
                    key(d, 'w', name != 'idle'); key(d, 'Shift_L', name == 'run')
                    await asyncio.sleep(.8)
                    sample = snapshot(); report['motion'].append({'name': name, 'player': sample['player']})
                    assert sample['player']['grounded']
                    if name != 'idle': assert sample['player']['speed'] >= 3.3
                    print(name, sample['player'], flush=True)
            finally:
                key(d, 'w', False); key(d, 'Shift_L', False)
            assert report['motion'][1]['player']['speed'] > report['motion'][0]['player']['speed']
            for camera in ['cam_gate', 'cam_avenue', 'cam_hill', 'cam_grid', 'cam_whompah', 'cam_hero']:
                await client.command({'action': 'view', 'camera': camera}); await asyncio.sleep(1.5)
                sample = snapshot(); report['views'].append({'camera': camera, 'fps': sample['fps'], 'draws': sample['draws'], 'triangles': sample['triangles']})
                await client.command({'action': 'capture', 'name': camera}); await asyncio.sleep(.2)
                print(report['views'][-1], flush=True)
            await client.command({'action': 'view', 'camera': 'follow'})
            check = await asyncio.create_subprocess_exec(sys.executable, str(ROOT / 'tools/city_loop_check.py'))
            assert await check.wait() == 0, 'Native city loop failed'
            await client.command({'action': 'quit'})
        await asyncio.to_thread(process.wait, timeout=15)
        log = (OUT / 'Player.log').read_text()
        assert 'Exception:' not in log and 'NullReferenceException' not in log
        report['complete'] = True
        print('PASS: native import, motion, six cameras and full city loop', flush=True)
    except Exception as error:
        report['error'] = str(error)
        raise
    finally:
        if process and process.poll() is None:
            process.terminate(); process.wait(timeout=10)
        subprocess.run(['xrandr', '--output', 'DP-0', '--mode', mode], check=True)
        (OUT / 'report.json').write_text(json.dumps(report, indent=2))
        print('Native evidence:', OUT, flush=True)

asyncio.run(main())
