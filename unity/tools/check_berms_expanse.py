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
from native_client import Client
from settings_test_input import focus, key, window
from Xlib import X
from Xlib.ext import xtest

ROOT = Path(__file__).resolve().parents[1]
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

        def summarise(name):
            rows = json.loads((OUT / 'profile.json').read_text()); shutil.copyfile(OUT / 'profile.json', OUT / f'profile-{name}.json')
            dts = sorted(r['dt'] * 1000 for r in rows if r['dt'] > 0)
            if not dts: return {}
            q = lambda f: round(dts[min(len(dts) - 1, int(f * len(dts)))], 2)
            gpu = [r['gpuMs'] for r in rows if r.get('gpuMs', -1) > 0]; tris = [r['tris'] for r in rows if r.get('tris', -1) > 0]
            out = dict(frames=len(dts), seconds=round(sum(dts) / 1000, 1), avg_fps=round(1000 * len(dts) / sum(dts), 1), p50=q(.5), p95=q(.95), p99=q(.99), max=round(dts[-1], 2),
                       hitches_over_33ms=sum(1 for d in dts if d > 33.3), gpu_ms_p50=round(sorted(gpu)[len(gpu) // 2], 2) if gpu else None,
                       tris_p50=sorted(tris)[len(tris) // 2] if tris else None)
            report.setdefault('profiles', {})[name] = out; return out

        async def walk_profile(name, landmark, yaw, seconds):
            await cmd(action='goto', landmark=landmark); await cmd(action='view', camera='follow'); await cmd(action='cameraYaw', yaw=yaw)
            await tap('w', 2.0); await asyncio.sleep(1)                       # warm the route
            await cmd(action='goto', landmark=landmark); await cmd(action='cameraYaw', yaw=yaw); await asyncio.sleep(1.5)
            await cmd(action='profileStart'); await tap('w', seconds); await asyncio.sleep(.3); await cmd(action='profileStop'); await asyncio.sleep(.5)
            return summarise(name)

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
            # 0. frame time across the bowl before the pistol (no site activates without it): two real-W walks
            report['samples']['walk_east_bowl'] = await walk_profile('walk-east-bowl', 'berms_first_contact', -80, 10)
            report['samples']['walk_mid_bowl'] = await walk_profile('walk-mid-bowl', 'berms_waystation', -95, 10)
            report['checks'].append('Profiled real-input walks across the bowl: ' + ', '.join(f"{k} {v.get('avg_fps')} fps (p99 {v.get('p99')} ms)" for k, v in report['profiles'].items()))
            # 1. pistol (real E, real 7)
            await cmd(action='goto', landmark='checkpoint_approach'); await asyncio.sleep(1)   # the primer starts at the gate and enables the locker
            await cmd(action='goto', landmark='checkpoint_locker'); await asyncio.sleep(.5)
            assert 'ARMS LOCKER' in snap()['interaction']['prompt'], snap()['interaction']
            await tap('e'); assert snap()['combat']['hasPistol']
            await tap('7'); assert snap()['combat']['Armed']
            report['checks'].append('Pistol taken and drawn with real E / 7')
            # 2. waystation
            await cmd(action='goto', landmark='berms_waystation'); await asyncio.sleep(1)
            for _ in range(4):                                # walk in with real input (the landmark is the approach, 18 m out)
                if 'waystation:berms_mid' in snap()['interaction']['flags']: break
                await face([-266, 52]); await tap('w', 1.6); await asyncio.sleep(.4)
            report['samples']['waystation_walk'] = snap()['player']['position']
            await face([-266, 52]); await capture('waystation')
            assert 'waystation:berms_mid' in snap()['interaction']['flags'], snap()['interaction']['flags']
            report['checks'].append('Warden waystation found and recorded')
            # 3. caravan ambush pack activates and engages
            await cmd(action='goto', landmark='berms_caravan'); await face([-205, 74]); h0 = snap()['combat']['health']
            for _ in range(40):
                await asyncio.sleep(.25)
                workers = near('Feral worker droid', 40)
                if workers and any(w['state'] not in ('Idle', 'Returning') for w in workers): break
            workers = near('Feral worker droid', 40)
            report['samples']['caravan'] = workers
            assert len(workers) >= 2 and any(w['state'] not in ('Idle', 'Returning') for w in workers), workers
            await asyncio.sleep(2.5); await capture('caravan-fight')
            report['checks'].append(f'Caravan ambush pack activated by proximity and engaged ({len(workers)} workers)')
            # 4. relay knoll gunners
            await cmd(action='goto', landmark='berms_relay_knoll'); await face([-330, 8]); h0 = snap()['combat']['health']; t0 = time.time()
            downs_before_relay = snap()['combat']['downs']
            shot = False
            for _ in range(80):
                await asyncio.sleep(.25)
                g = near('Feral gunner droid', 40, origin=[-330, 0, 8])
                if any(x['bolts'] > 0 for x in g): shot = True; break
            await cmd(action='profileStart'); await asyncio.sleep(6); await cmd(action='profileStop'); await asyncio.sleep(.5)
            fight = summarise('relay-fight'); report['samples']['relay_fight_profile'] = fight
            await capture('relay-fight')
            g = near('Feral gunner droid', 40, origin=[-330, 0, 8]); report['samples']['gunners'] = g   # (the player may be down by now)
            assert g, 'no gunner droids at the relay knoll'
            assert shot, g
            for _ in range(40):
                if snap()['combat']['health'] < h0 or snap()['combat']['downs'] > 0: break
                await asyncio.sleep(.25)
            assert snap()['combat']['health'] < h0 or snap()['combat']['downs'] > 0, 'gunner bolts never hurt the player'
            report['checks'].append(f'Relay knoll gunners aimed and fired ({sum(x["bolts"] for x in g)} bolts) and hurt the player in {time.time() - t0:.1f} s')
            # 5. knocked down -> waystation
            downs0 = downs_before_relay
            for _ in range(240):
                if snap()['combat']['downs'] > downs0: break
                await asyncio.sleep(.25)
            assert snap()['combat']['downs'] > downs0, 'never knocked down'
            await asyncio.sleep(1); pos = snap()['player']['position']
            report['samples']['respawn'] = pos
            assert math.dist([pos[0], pos[2]], [-266, 52]) < 20, pos
            await capture('respawned-at-waystation')
            report['checks'].append('Knocked down at the relay knoll; the Wardens bring the player to the waystation')
            # 6. lancers at the Tube pylon
            await cmd(action='goto', landmark='berms_tube_pylon'); await face([-424, -96])
            shot = False
            for _ in range(100):
                await asyncio.sleep(.25)
                l = near('Feral lancer drone', 70)
                if any(x['bolts'] > 0 for x in l): shot = True; break
            await capture('pylon-fight')
            l = near('Feral lancer drone', 70); report['samples']['lancers'] = l
            assert l and shot, l
            report['checks'].append(f'Tube pylon lancers fired ({sum(x["bolts"] for x in l)} bolts)')
            await cmd(action='memorySnapshot')
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
