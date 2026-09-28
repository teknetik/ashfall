"""Real-input machine-depot check against the native Linux development player (27 Sep 2026 depot/robot pass).

DISPLAY=:0 ATHEN_DEPOT_EVIDENCE=<dir> uv run --offline --with python-xlib python unity/tools/check_depot.py
Close the Unity Editor first (VRAM). Plays the Outer Berms tutorial with real keyboard input (locker E, draw 7,
three plates with F), puts down the service-road drone, which arms the depot nest, captures the nest and the
depot review cameras in the native build, then fights the nest with real F presses (the QA bridge only turns the
follow camera toward the nearest droid, as a player would with the mouse). Records droid states seen (wind-up
telegraphs), player knock-downs, frame-time profiles for the fight and a warmed depot walk, night views, and fails
on any runtime exception in Player.log.
"""
import asyncio, json, math, os, subprocess, shutil, base64, sys, time
from pathlib import Path
from native_client import Client
from settings_test_input import focus, key, window
from Xlib import X
from Xlib.ext import xtest

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('ATHEN_DEPOT_EVIDENCE', ROOT / 'evidence/outer-berms-depot/20260927/native-depot')); OUT.mkdir(parents=True, exist_ok=True)


def summarize(samples):
    dts = sorted(s['dt'] * 1000 for s in samples)
    if not dts: return None
    n = len(dts); dur = sum(dts) / 1000
    pct = lambda q: round(dts[min(n - 1, int(q * n))], 2)
    return {'frames': n, 'duration_seconds': round(dur, 2), 'average_fps': round(n / dur, 1), 'p50_ms': pct(.5), 'p95_ms': pct(.95),
            'p99_ms': pct(.99), 'max_ms': round(dts[-1], 2), 'hitches_over_50ms': sum(d > 50 for d in dts), 'hitches_over_100ms': sum(d > 100 for d in dts),
            'cpu_mean_ms': round(sum(s.get('cpuMs', 0) for s in samples) / n, 2), 'setpass_mean': round(sum(s.get('setPass', 0) for s in samples) / n, 1),
            'submitted_triangles_mean': int(sum(s.get('tris', 0) for s in samples) / n)}


async def main():
    report = {'passed': False, 'checks': [], 'droid_states_seen': {}, 'knockdowns': 0}
    env = dict(os.environ, XDG_CONFIG_HOME=str(OUT / 'config'))
    video = json.loads((ROOT / 'evidence/courtyard/20260908/after-native/settings.json').read_text())['video']
    for vendor, product in [('unknown', 'unknown'), ('Free Column', 'Athen Hill')]:
        prefs = OUT / 'config/unity3d' / vendor / product; prefs.mkdir(parents=True, exist_ok=True)
        encoded = base64.b64encode(json.dumps(video).encode()).decode()
        (prefs / 'prefs').write_text('<unity_prefs version_major="1" version_minor="1"><pref name="AthenHill.Settings.v1.QA.Video" type="string">' + encoded + '</pref></unity_prefs>')
    p = subprocess.Popen([str(ROOT / 'AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64'), '-force-glcore', '-screen-fullscreen', '0', '-screen-width', '1920', '-screen-height', '1080',
                          '-logFile', str(OUT / 'Player.log'), '--athen-qa', str(OUT), '--athen-qa-background'], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    (OUT / 'pid').write_text(str(p.pid))
    os.environ.update(ATHEN_NATIVE_DIR=str(OUT), ATHEN_NATIVE_PID=str(p.pid))
    recording = None

    def focused():
        d = focus(); w = window(d); w.set_input_focus(X.RevertToParent, X.CurrentTime); g = w.get_geometry(); xy = d.screen().root.translate_coords(w, 0, 0)
        xtest.fake_input(d, X.MotionNotify, x=xy.x + g.width // 2, y=xy.y + g.height // 2); d.sync(); return d

    def snap(): return json.loads((OUT / 'snapshot.json').read_text())

    async def tap(name, seconds=.12, settle=.35):
        d = focused(); key(d, name, True); await asyncio.sleep(seconds); key(d, name, False); await asyncio.sleep(settle)

    async with Client() as c:
        async def cmd(**kw): await c.command(kw); await asyncio.sleep(.35)

        async def capture(name):
            await cmd(action='capture', name=name); await cmd(action='uiSnapshot')
            shutil.copyfile(OUT / 'snapshot.json', OUT / (name + '-state.json'))

        def enemies(s=None):
            s = s or snap(); return [e for e in (s['combat'] or {}).get('enemies', []) if e['alive']]

        async def arm():
            if not snap()['combat']['Armed']: await tap('7')
            assert snap()['combat']['Armed'], snap()['combat']

        async def fight(label, timeout, want_step=None, rally='depot_approach', capture_windup=True):
            """Face the nearest live droid and fire with real F presses once it is inside hip-fire reach (the follow
            camera looks 17 degrees down, so hip shots connect inside ~6 m). Walk toward droids that have not noticed
            the player. After a knock-down the player respawns at the checkpoint unarmed: goto the rally landmark
            (QA shortcut for the walk back) and draw again."""
            t0 = time.time(); shots = 0; windup_captured = False; last = None
            while time.time() - t0 < timeout:
                s = snap(); live = enemies(s)
                if want_step and s['combat']['step'] == want_step: break
                if not live and not want_step: break
                for e in live: report['droid_states_seen'][e['state']] = report['droid_states_seen'].get(e['state'], 0) + 1
                px, _, pz = s['player']['position']
                if last and math.hypot(px - last[0], pz - last[1]) > 12:
                    report['knockdowns'] += 1; await cmd(action='goto', landmark=rally); await arm(); last = None; continue
                last = (px, pz)
                if not s['combat']['Armed']: await arm()
                if not live: await asyncio.sleep(.3); continue
                e = min(live, key=lambda e: math.hypot(e['position'][0] - px, e['position'][2] - pz))
                dx, dz = e['position'][0] - px, e['position'][2] - pz; dist = math.hypot(dx, dz)
                await c.command({'action': 'cameraYaw', 'yaw': math.degrees(math.atan2(dx, dz)) % 360}); await asyncio.sleep(.05)
                # (no capture while profiling: ScreenCapture encodes the PNG on the main thread, a ~150 ms hitch)
                if capture_windup and not windup_captured and any(x['state'] == 'Windup' and math.hypot(x['position'][0] - px, x['position'][2] - pz) < 5 for x in live):
                    await c.command({'action': 'capture', 'name': label + '-windup-telegraph'}); windup_captured = True
                if dist <= 6.5: await tap('f', .06, .2); shots += 1
                elif e['state'] in ('Idle', 'Returning') and dist > 10: await tap('w', .4, .05)
                else: await asyncio.sleep(.1)
            return shots, time.time() - t0

        try:
            for _ in range(1800):
                try: focus(); break
                except RuntimeError: await asyncio.sleep(.05)
            if shutil.which('hyprctl'):
                subprocess.run(['hyprctl', '-i', '0', 'dispatch', f'hl.dsp.window.float({{action="set",window="pid:{p.pid}"}})'], capture_output=True)
            for _ in range(1800):
                if (OUT / 'snapshot.json').exists() and snap()['session']['state'] == 'MainMenu': break
                await asyncio.sleep(.1)
            assert snap()['session']['state'] == 'MainMenu', 'Main menu never ready'
            await tap('Return')
            d0 = focused()
            for k in ['d', 'Right', 'a', 'Left', 'w', 's', 'Up', 'Down', 'Shift_L', 'Shift_R', 'Control_L', 'e', 'f', 'space']: key(d0, k, False)
            for _ in range(1800):
                if snap()['session']['state'] == 'Play': break
                await asyncio.sleep(.1)
            assert snap()['session']['state'] == 'Play'
            await cmd(action='resize', width=1920, height=1080); await asyncio.sleep(2)
            await cmd(action='timeSet', hour=12); await cmd(action='timePause', paused=True)
            # tutorial prerequisites with real input
            await cmd(action='goto', landmark='checkpoint_approach'); await cmd(action='view', camera='follow'); await cmd(action='cameraYaw', yaw=270); await tap('w', 1.3)
            await cmd(action='goto', landmark='checkpoint_locker'); await tap('e'); assert snap()['combat']['hasPistol'], snap()['combat']
            await tap('7'); assert snap()['combat']['Armed']
            await cmd(action='goto', landmark='checkpoint_firingline')
            for i in range(1, 4): await cmd(action='view', camera=f'cam_checkpoint_plate{i}'); await tap('f', .65)
            assert snap()['combat']['step'] == 'FirstContact', snap()['combat']
            report['checks'].append('Tutorial prerequisites with real input (locker, draw, three plates)')
            # first contact: the service-road drone
            await cmd(action='goto', landmark='checkpoint_road'); await cmd(action='view', camera='follow')
            shots, secs = await fight('first-contact', 90, want_step='Depot', rally='checkpoint_road')
            assert snap()['combat']['step'] == 'Depot', snap()['combat']
            report['checks'].append(f'Service-road drone put down with real F input ({shots} shots, {secs:.0f} s); depot nest armed')
            # nest spawned: inspect it from the service road, out of aggro range (15-16 m), before engaging
            await cmd(action='goto', landmark='checkpoint_road'); await asyncio.sleep(.5)
            s = snap(); nest = enemies(s); report['nest_spawn'] = [{k: e[k] for k in ('displayName', 'state', 'health', 'position')} for e in nest]
            assert len(nest) == 3, nest
            assert sum(e['displayName'] == 'Feral worker droid' for e in nest) == 2 and sum(e['displayName'] == 'Feral scrap drone' for e in nest) == 1, nest
            report['checks'].append('Depot nest spawns two worker droids and one scrap drone at the moved spawn points')
            for cam in ['cam_depot_fight', 'cam_depot_approach', 'cam_depot_yard', 'cam_depot_cradles', 'cam_depot_hall', 'cam_depot_west', 'cam_depot_conveyor', 'cam_depot_aerial']:
                await cmd(action='view', camera=cam); await asyncio.sleep(.6); await capture('day-' + cam)
            await cmd(action='view', camera='follow')
            if shutil.which('ffmpeg'):
                wid = window(focus()).id
                recording = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'x11grab', '-framerate', '20', '-window_id', str(wid), '-i', os.environ['DISPLAY'], '-c:v', 'libx264',
                                              '-preset', 'ultrafast', '-crf', '23', '-pix_fmt', 'yuv420p', str(OUT / 'depot-fight.mp4')], stdin=subprocess.PIPE, stderr=(OUT / 'video.log').open('wb'), stdout=subprocess.DEVNULL)
            await cmd(action='goto', landmark='depot_approach'); await cmd(action='view', camera='follow'); await cmd(action='cameraYaw', yaw=180); await arm()
            await cmd(action='profileStart')
            shots, secs = await fight('depot', 150, capture_windup=False)
            await cmd(action='profileStop'); shutil.copyfile(OUT / 'profile.json', OUT / 'depot-fight-profile.json')
            await capture('depot-after-fight')
            s = snap(); left = enemies(s)
            report['fight'] = {'shots': shots, 'seconds': round(secs, 1), 'remaining': len(left), 'step': s['combat']['step'], 'player_health': s['combat']['health']}
            assert not left, left
            report['checks'].append(f'Depot nest cleared with real F input ({shots} shots, {secs:.0f} s, {report["knockdowns"]} knock-downs); tutorial step {s["combat"]["step"]}')
            assert 'Windup' in report['droid_states_seen'], report['droid_states_seen']
            report['checks'].append('Droids telegraphed strikes (Windup state observed during the fight)')
            if recording and recording.poll() is None: recording.communicate(b'q', timeout=10)
            await cmd(action='view', camera='cam_depot_yard'); await asyncio.sleep(1); await capture('depot-wrecks')
            # warmed depot walk for frame times (corpses sunk after 14 s)
            await asyncio.sleep(12)
            await cmd(action='view', camera='follow')
            for lm in ['depot_approach', 'depot_yard', 'depot_hall']:
                await cmd(action='goto', landmark=lm)
                for yaw in [180, 270, 0, 90]: await cmd(action='cameraYaw', yaw=yaw); await tap('w', .9, .1)
            await cmd(action='goto', landmark='depot_approach'); await asyncio.sleep(2); await cmd(action='profileStart')
            for lm in ['depot_approach', 'depot_yard', 'depot_hall']:
                await cmd(action='goto', landmark=lm)
                for yaw in [180, 270, 0, 90]: await cmd(action='cameraYaw', yaw=yaw); await tap('w', 1.2, .2)
            await cmd(action='profileStop'); shutil.copyfile(OUT / 'profile.json', OUT / 'depot-route-profile.json')
            report['checks'].append('Warmed depot walk profiled')
            # night
            await cmd(action='timeSet', hour=21); await asyncio.sleep(1)
            for cam in ['cam_depot_yard', 'cam_depot_cradles', 'cam_depot_approach']:
                await cmd(action='view', camera=cam); await asyncio.sleep(.8); await capture('night-' + cam)
            await cmd(action='timeSet', hour=12)
            await cmd(action='settingsSnapshot'); await cmd(action='memorySnapshot')
            errors = [l for l in (OUT / 'Player.log').read_text().splitlines() if 'Exception:' in l or 'NullReference' in l]
            assert not errors, errors
            report['checks'].append('No runtime exceptions in Player.log')
            report['profiles'] = {n: summarize(json.loads((OUT / f'{n}-profile.json').read_text())) for n in ('depot-fight', 'depot-route')}
            report['passed'] = True
        except Exception as e:
            report['error'] = repr(e); raise
        finally:
            if recording and recording.poll() is None: recording.communicate(b'q', timeout=10)
            (OUT / 'report.json').write_text(json.dumps(report, indent=2))
            try: await cmd(action='quit')
            except Exception: pass
            try: p.wait(timeout=5)
            except subprocess.TimeoutExpired: p.terminate()

asyncio.run(main())
