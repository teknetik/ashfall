"""t_6c931016: native capture of the default start time (request #5) at spawn and at the Berms range, without timeSet.
Also first-person hip and ADS at dusk with the pistol (request #6). Dev build, real input for the zoom and RMB.
DISPLAY=:0 ATHEN_DUSK_EVIDENCE=<dir> uv run --offline --with python-xlib python unity/tools/../../<this file>"""
import asyncio, json, os, subprocess, shutil, base64, sys
from pathlib import Path
sys.path.insert(0, '/home/teknetik/code/.snap/ao2-t_6c931016/unity/tools')
from native_client import Client
from settings_test_input import focus, key, window
from Xlib import X
from Xlib.ext import xtest

ROOT = Path('/home/teknetik/code/.snap/ao2-t_6c931016/unity')
OUT = Path(os.environ['ATHEN_DUSK_EVIDENCE']); OUT.mkdir(parents=True, exist_ok=True)
BUILD = ROOT / 'AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64'


async def main():
    env = dict(os.environ, XDG_CONFIG_HOME=str(OUT / 'config'))
    video = json.loads((ROOT / 'evidence/courtyard/20260908/after-native/settings.json').read_text())['video']
    for vendor, product in [('unknown', 'unknown'), ('Free Column', 'Athen Hill')]:
        prefs = OUT / 'config/unity3d' / vendor / product; prefs.mkdir(parents=True, exist_ok=True)
        enc = base64.b64encode(json.dumps(video).encode()).decode()
        (prefs / 'prefs').write_text('<unity_prefs version_major="1" version_minor="1"><pref name="AthenHill.Settings.v1.QA.Video" type="string">' + enc + '</pref></unity_prefs>')
    p = subprocess.Popen([str(BUILD), '-force-glcore', '-screen-fullscreen', '0', '-screen-width', '1920', '-screen-height', '1080',
                          '-logFile', str(OUT / 'Player.log'), '--athen-qa', str(OUT), '--athen-qa-background'], env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    os.environ.update(ATHEN_NATIVE_DIR=str(OUT), ATHEN_NATIVE_PID=str(p.pid))
    res = {'notes': []}

    def focused():
        d = focus(); w = window(d); w.set_input_focus(X.RevertToParent, X.CurrentTime); d.sync(); return d

    def button(n, down):
        d = focused(); xtest.fake_input(d, X.ButtonPress if down else X.ButtonRelease, n); d.sync()

    async def tap(name, s=.12, settle=.35):
        d = focused(); key(d, name, True); await asyncio.sleep(s); key(d, name, False); await asyncio.sleep(settle)

    try:
        async with Client() as c:
            async def cmd(**kw): await c.command(kw); await asyncio.sleep(.3)

            async def capture(name):
                await cmd(action='capture', name=name); await cmd(action='uiSnapshot'); shutil.copyfile(OUT / 'snapshot.json', OUT / (name + '-state.json'))

            for _ in range(1800):
                try: focus(); break
                except RuntimeError: await asyncio.sleep(.05)
            subprocess.run(['hyprctl', '-i', '0', 'dispatch', f'hl.dsp.window.float({{action="set",window="pid:{p.pid}"}})'], capture_output=True)
            snap = lambda: json.loads((OUT / 'snapshot.json').read_text())
            for _ in range(1800):
                if (OUT / 'snapshot.json').exists() and snap()['session']['state'] == 'MainMenu': break
                await asyncio.sleep(.1)
            await asyncio.sleep(2)
            for _ in range(6):
                await tap('Return', .12, 1.5)
                if snap()['session']['state'] != 'MainMenu': break
            for _ in range(1800):
                if snap()['session']['state'] == 'Play': break
                await asyncio.sleep(.1)
            await cmd(action='resize', width=1920, height=1080); await asyncio.sleep(4)
            await cmd(action='view', camera='follow')
            res['clock_state'] = {k: v for k, v in snap().items() if 'time' in k.lower() or 'hour' in k.lower() or 'clock' in k.lower()}
            await capture('start-default')
            await cmd(action='goto', landmark='checkpoint_locker'); await tap('e', .12, 1.0)
            res['hasPistol'] = json.loads((OUT / 'snapshot.json').read_text()).get('combat', {}).get('hasPistol')
            await cmd(action='goto', landmark='checkpoint_firingline'); await cmd(action='cameraYaw', yaw=0); await asyncio.sleep(1.0)
            await capture('range-default-tp')
            await tap('7', .1, 1.2)
            for _ in range(14):
                button(4, True); button(4, False); await asyncio.sleep(.08)
            await asyncio.sleep(.8); await cmd(action='cameraPitch', pitch=4); await cmd(action='cameraYaw', yaw=0)
            res['camera'] = json.loads((OUT / 'snapshot.json').read_text()).get('camera')
            await capture('fp-hip-dusk')
            button(3, True); await asyncio.sleep(.7); await capture('fp-ads-dusk'); button(3, False)
            await cmd(action='cameraYaw', yaw=180); await asyncio.sleep(.4)
            await capture('fp-hip-dusk-sunbehind')
            button(3, True); await asyncio.sleep(.7); await capture('fp-ads-dusk-sunbehind'); button(3, False)
    except Exception as e:
        res['notes'].append(repr(e))
    finally:
        p.terminate()
        try: p.wait(15)
        except subprocess.TimeoutExpired: p.kill()
    log = (OUT / 'Player.log').read_text(errors='replace') if (OUT / 'Player.log').exists() else ''
    res['exceptions'] = [l for l in log.splitlines() if 'Exception' in l][:20]
    (OUT / 'report.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res))

asyncio.run(main())
