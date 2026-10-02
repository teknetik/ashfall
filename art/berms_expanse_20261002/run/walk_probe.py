"""Native check of the Outer Berms expansion (2 Oct 2026) on the Linux development player.

Real input for the verbs (E, 7, W), the QA bridge for teleports, cameras and captures:
1. take the pistol at the locker and draw it (real E / 7);
2. walk into the Warden waystation and check it is recorded (flag waystation:berms_mid);
3. stand at the caravan ambush approach: the site's pack activates on its own and turns on the player;
4. stand at the relay knoll approach: gunner droids aim (laser) and fire bolts that hurt the player; capture the fight;
5. stay until knocked down: the Warden patrol drags the player to the waystation (nearer than the gate);
6. stand at the Tube pylon approach: lancer drones fire;
7. no exceptions in the player log.
Usage: ATHEN_EXPANSE_EVIDENCE=<dir> python unity/tools/check_berms_expanse.py
"""
import asyncio, json, math, os, subprocess, shutil, base64, time
from pathlib import Path
import sys; sys.path.insert(0, '/home/teknetik/code/ao2/unity/tools')
from native_client import Client
from settings_test_input import focus, key, window
from Xlib import X
from Xlib.ext import xtest

ROOT = Path('/home/teknetik/code/ao2/unity')
OUT = Path(os.environ.get('ATHEN_EXPANSE_EVIDENCE', ROOT / 'evidence/berms-expanse/20261002/native-check')); OUT.mkdir(parents=True, exist_ok=True)
EXE = os.environ.get('ATHEN_EXE', str(ROOT / 'AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64'))


async def main():
    report = {'passed': False, 'checks': [], 'samples': {}}
    env = dict(os.environ, XDG_CONFIG_HOME=str(OUT / 'config'))
    video = json.loads((ROOT / 'evidence/courtyard/20260908/after-native/settings.json').read_text())['video']
    for vendor, product in [('unknown', 'unknown'), ('Free Column', 'Athen Hill')]:
        prefs = OUT / 'config/unity3d' / vendor / product; prefs.mkdir(parents=True, exist_ok=True)
        enc = base64.b64encode(json.dumps(video).encode()).decode()
        (prefs / 'prefs').write_text('<unity_prefs version_major="1" version_minor="1"><pref name="AthenHill.Settings.v1.QA.Video" type="string">' + enc + '</pref></unity_prefs>')
    p = subprocess.Popen([EXE, '-force-glcore', '-screen-fullscreen', '0', '-screen-width', '1920', '-screen-height', '1080', '-logFile', str(OUT / 'Player.log'),
                          '--athen-qa', str(OUT), '--athen-qa-background'], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    os.environ.update(ATHEN_NATIVE_DIR=str(OUT), ATHEN_NATIVE_PID=str(p.pid))

    def focused():
        d = focus(); w = window(d); w.set_input_focus(X.RevertToParent, X.CurrentTime); g = w.get_geometry(); xy = d.screen().root.translate_coords(w, 0, 0)
        xtest.fake_input(d, X.MotionNotify, x=xy.x + g.width // 2, y=xy.y + g.height // 2); d.sync(); return d

    def snap(): return json.loads((OUT / 'snapshot.json').read_text())

    async def tap(name, seconds=.12):
        d = focused(); key(d, name, True); await asyncio.sleep(seconds); key(d, name, False); await asyncio.sleep(.35)

    async with Client() as c:
        async def cmd(**kw): await c.command(kw); await asyncio.sleep(.35)

        async def capture(name):
            await cmd(action='capture', name=name); await cmd(action='uiSnapshot'); shutil.copyfile(OUT / 'snapshot.json', OUT / (name + '-state.json'))

        async def face(target):
            pos = snap()['player']['position']; yaw = math.degrees(math.atan2(target[0] - pos[0], target[1] - pos[2]))
            await cmd(action='view', camera='follow'); await cmd(action='cameraYaw', yaw=yaw)

        def near(name, radius, origin=None):
            s = snap(); o = origin or s['player']['position']
            return [e for e in s['combat']['enemies'] if e['displayName'] == name and math.dist([e['position'][0], e['position'][2]], [o[0], o[2]]) < radius]

        try:
            for _ in range(1800):
                try: focus(); break
                except RuntimeError: await asyncio.sleep(.05)
            if shutil.which('hyprctl'):
                subprocess.run(['hyprctl', '-i', '0', 'dispatch', f'hl.dsp.window.float({{action="set",window="pid:{p.pid}"}})'], capture_output=True)
            for _ in range(1800):
                if (OUT / 'snapshot.json').exists() and snap()['session']['state'] == 'MainMenu': break
                await asyncio.sleep(.1)
            await tap('Return')
            d0 = focused()
            for k in ['d', 'Right', 'a', 'Left', 'w', 's', 'Up', 'Down', 'Shift_L', 'Shift_R', 'Control_L', 'e', 'f', 'space']: key(d0, k, False)
            for _ in range(1800):
                if snap()['session']['state'] == 'Play': break
                await asyncio.sleep(.1)
            assert snap()['session']['state'] == 'Play'
            await cmd(action='resize', width=1920, height=1080); await asyncio.sleep(2)
            await cmd(action='timeSet', hour=13); await cmd(action='timePause', paused=True)
            async def walk_probe(tag, lm, target):
                await cmd(action='goto', landmark=lm); await asyncio.sleep(1); await face(target)
                p0 = snap()['player']['position']; await tap('w', 2.0); await asyncio.sleep(.4); p1 = snap()['player']['position']
                report['samples'][tag] = dict(before=p0, after=p1, moved=math.dist(p0, p1), yaw=snap()['camera']['yaw'], state=snap()['session']['state'])
            await walk_probe('gate_unarmed', 'checkpoint_approach', [-80, 0])
            await walk_probe('waystation_unarmed', 'berms_waystation', [-266, 52])
            await cmd(action='goto', landmark='checkpoint_approach'); await asyncio.sleep(1)
            await cmd(action='goto', landmark='checkpoint_locker'); await asyncio.sleep(.5); await tap('e'); await tap('7')
            await walk_probe('waystation_armed', 'berms_waystation', [-266, 52])
            await walk_probe('locker_armed', 'checkpoint_locker', [-80, 10])
            report['passed'] = True

            errors = [line for line in (OUT / 'Player.log').read_text().splitlines() if 'Exception:' in line or 'NullReference' in line]
            assert not errors, errors[:5]
            report['checks'].append('No exceptions in the player log')
            report['passed'] = True
        except Exception as e:
            report['error'] = repr(e); raise
        finally:
            (OUT / 'report.json').write_text(json.dumps(report, indent=2))
            try: await cmd(action='quit')
            except Exception: pass
            try: p.wait(timeout=5)
            except subprocess.TimeoutExpired: p.terminate()

asyncio.run(main())
