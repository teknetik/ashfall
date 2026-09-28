"""t_6c931016: native captures for requests #1-#6 at the DEFAULT start hour (no timeSet), against the dev build.
Real input: Return (menu), E (Ossa, locker), 7 (draw), mouse wheel (first person), RMB (ADS), LMB (fire), W/Shift (run).
ATHEN_DUSK_EVIDENCE=<dir> uv run --offline --with python-xlib python capture_requests.py"""
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
    res = {'checks': [], 'notes': []}
    rec = []

    def focused():
        d = focus(); w = window(d); w.set_input_focus(X.RevertToParent, X.CurrentTime); d.sync(); return d

    def button(n, down):
        d = focused(); xtest.fake_input(d, X.ButtonPress if down else X.ButtonRelease, n); d.sync()

    async def tap(name, s=.12, settle=.35):
        d = focused(); key(d, name, True); await asyncio.sleep(s); key(d, name, False); await asyncio.sleep(settle)

    def start(name):
        wid = window(focus()).id
        rec.append(subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'x11grab', '-framerate', '30', '-window_id', str(wid), '-i', os.environ['DISPLAY'],
                                     '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '22', '-pix_fmt', 'yuv420p', str(OUT / (name + '.mp4'))],
                                    stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))

    def stop():
        while rec:
            r = rec.pop()
            try: r.communicate(b'q', timeout=15)
            except subprocess.TimeoutExpired: r.kill()

    snap = lambda: json.loads((OUT / 'snapshot.json').read_text())
    try:
        async with Client() as c:
            async def cmd(**kw): await c.command(kw); await asyncio.sleep(.35)

            async def capture(name):
                await cmd(action='capture', name=name); await cmd(action='uiSnapshot'); shutil.copyfile(OUT / 'snapshot.json', OUT / (name + '-state.json'))

            for _ in range(1800):
                try: focus(); break
                except RuntimeError: await asyncio.sleep(.05)
            subprocess.run(['hyprctl', '-i', '0', 'dispatch', f'hl.dsp.window.float({{action="set",window="pid:{p.pid}"}})'], capture_output=True)
            for _ in range(1800):
                if (OUT / 'snapshot.json').exists() and snap()['session']['state'] == 'MainMenu': break
                await asyncio.sleep(.1)
            await asyncio.sleep(2)
            for _ in range(6):
                await tap('Return', .12, 1.5)
                if snap()['session']['state'] != 'MainMenu': break
            d0 = focused()
            for k in ['d', 'a', 'w', 's', 'Shift_L', 'e', 'f', 'space']: key(d0, k, False)
            for _ in range(1800):
                if snap()['session']['state'] == 'Play': break
                await asyncio.sleep(.1)
            await cmd(action='resize', width=1920, height=1080); await asyncio.sleep(3)
            await cmd(action='timeState'); await asyncio.sleep(.3)
            if (OUT / 'time-state.json').exists():
                res['time_at_start'] = json.loads((OUT / 'time-state.json').read_text())
            await cmd(action='view', camera='follow')
            await capture('01-spawn-default-hour')
            for cam in ['cam_avenue', 'cam_hill', 'cam_gate']:
                await cmd(action='view', camera=cam); await asyncio.sleep(.8); await capture('05-dusk-' + cam)
            for cam in ['cam_market', 'cam_market_lane', 'cam_berms_gate', 'cam_westgate_mouth', 'cam_berms_road', 'cam_berms_depot', 'cam_westgate_range']:
                try:
                    await cmd(action='view', camera=cam); await asyncio.sleep(.8); await capture('34-' + cam)
                except Exception as e: res['notes'].append(cam + ' ' + repr(e))
            await cmd(action='view', camera='follow')
            for lm, name in [('checkpoint_ossa', 'ossa'), ('checkpoint_rell', 'rell')]:
                await cmd(action='goto', landmark=lm); await asyncio.sleep(.5)
                await capture('02-warden-' + name)
            await cmd(action='view', camera='cam_berms_post'); await asyncio.sleep(.6); await capture('02-wardens-post')
            await cmd(action='view', camera='follow')
            await cmd(action='goto', landmark='checkpoint_firingline'); await cmd(action='cameraYaw', yaw=180); await asyncio.sleep(.5)
            start('01-run-dusk')
            d = focused(); key(d, 'Shift_L', True); key(d, 'w', True); await asyncio.sleep(4.0); key(d, 'w', False); key(d, 'Shift_L', False)
            await asyncio.sleep(.6); stop()
            await cmd(action='goto', landmark='checkpoint_ossa'); await tap('e', .12, .6); await tap('Escape', .1, .4)
            await cmd(action='goto', landmark='checkpoint_locker'); await tap('e', .12, 1.0)
            res['hasPistol'] = snap()['combat']['hasPistol']
            await tap('7', .1, 1.2); res['armed'] = snap()['combat']['Armed']
            await cmd(action='goto', landmark='checkpoint_firingline'); await cmd(action='view', camera='follow'); await cmd(action='cameraYaw', yaw=0)
            for _ in range(12): button(4, True); button(4, False); await asyncio.sleep(.08)
            await asyncio.sleep(.8); await cmd(action='cameraPitch', pitch=4); await cmd(action='cameraYaw', yaw=0)
            res['camera'] = snap()['camera']
            start('06-fp-pistol-dusk')
            await capture('06-fp-hip-dusk')
            button(3, True); await asyncio.sleep(.7); await capture('06-fp-ads-dusk')
            for _ in range(3): button(1, True); await asyncio.sleep(.06); button(1, False); await asyncio.sleep(.45)
            button(3, False); await asyncio.sleep(.5)
            await cmd(action='cameraYaw', yaw=180); await asyncio.sleep(.5); await capture('06-fp-hip-dusk-sunbehind')
            button(3, True); await asyncio.sleep(.7); await capture('06-fp-ads-dusk-sunbehind'); button(3, False)
            d = focused(); key(d, 'w', True); await asyncio.sleep(1.5); key(d, 'w', False); await asyncio.sleep(.4)
            await capture('06-fp-after-walk'); stop()
            res['combat'] = snap()['combat']
            res['checks'].append('default-hour captures, wardens, run video, FP hip/ADS/fire video')
    except Exception as e:
        res['notes'].append(repr(e))
    finally:
        stop(); p.terminate()
        try: p.wait(15)
        except subprocess.TimeoutExpired: p.kill()
    log = (OUT / 'Player.log').read_text(errors='replace') if (OUT / 'Player.log').exists() else ''
    res['exceptions'] = [l for l in log.splitlines() if 'Exception' in l][:20]
    (OUT / 'report.json').write_text(json.dumps(res, indent=1, default=str)); print(json.dumps(res, default=str)[:3000])

asyncio.run(main())
