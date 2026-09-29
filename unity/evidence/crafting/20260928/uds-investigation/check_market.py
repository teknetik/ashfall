"""Capture rebuilt native market cameras; real Enter starts the game."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'tools'))
from native_client import Client
from settings_test_input import focus, window, key
from Xlib import X

OUT = Path(__file__).parent / 'native-market'
OUT.mkdir(exist_ok=True)

async def main():
    env = dict(os.environ, XDG_CONFIG_HOME=str(OUT / 'config'))
    report = {'passed': False, 'captures': []}
    with (OUT / 'launcher.log').open('wb') as log:
        p = subprocess.Popen([str(ROOT / 'AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64'), '-force-glcore', '-screen-fullscreen', '0', '-screen-width', '1920', '-screen-height', '1080', '-logFile', str(OUT / 'Player.log'), '--athen-qa', str(OUT), '--athen-qa-background'], env=env, stdout=log, stderr=subprocess.STDOUT)
        os.environ.update(ATHEN_NATIVE_DIR=str(OUT), ATHEN_NATIVE_PID=str(p.pid))
        def snap():
            return json.loads((OUT / 'snapshot.json').read_text())
        try:
            for _ in range(1800):
                if p.poll() is not None:
                    raise RuntimeError(f'Player exited: {p.returncode}')
                if (OUT / 'snapshot.json').exists() and snap()['session']['state'] == 'MainMenu':
                    break
                await asyncio.sleep(.1)
            else:
                raise TimeoutError('Main menu unavailable')
            d = focus()
            window(d).set_input_focus(X.RevertToParent, X.CurrentTime)
            d.sync()
            key(d, 'Return', True)
            await asyncio.sleep(.1)
            key(d, 'Return', False)
            for _ in range(100):
                if snap()['session']['state'] == 'Play':
                    break
                await asyncio.sleep(.1)
            assert snap()['session']['state'] == 'Play'
            async with Client() as c:
                await c.command({'action': 'timePause', 'paused': True})
                await c.command({'action': 'timeSet', 'hour': 16})
                for camera in ['cam_market', 'cam_market_produce', 'cam_market_cookfire', 'cam_market_lane', 'cam_checkpoint_locker']:
                    await c.command({'action': 'view', 'camera': camera})
                    await asyncio.sleep(3)
                    await c.command({'action': 'capture', 'name': camera})
                    for _ in range(100):
                        if (OUT / (camera + '.png')).exists():
                            break
                        await asyncio.sleep(.1)
                    assert (OUT / (camera + '.png')).exists()
                    report['captures'].append(camera + '.png')
                report['snapshot'] = snap()
                await c.command({'action': 'quit'})
            p.wait(timeout=20)
            report['passed'] = True
        finally:
            if p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    p.kill()
                    p.wait()
            text = (OUT / 'Player.log').read_text(errors='replace')
            report['runtime_errors'] = [l for l in text.splitlines() if 'Exception:' in l or 'NullReference' in l or 'UDSFilesystem failed' in l]
            (OUT / 'report.json').write_text(json.dumps(report, indent=2))

asyncio.run(main())
