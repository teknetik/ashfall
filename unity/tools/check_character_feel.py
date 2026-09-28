"""Real-input character-feel check against a native Linux development player (27 Sep 2026 character-feel pass).

DISPLAY=:0 ATHEN_FEEL_EVIDENCE=<dir> [ATHEN_FEEL_BUILD=<player>] uv run --offline --with python-xlib python unity/tools/check_character_feel.py
Close the Unity Editor first (VRAM). Records video with desktop audio (x11grab + PulseAudio monitor) of:
  1. Wardens Ossa and Rell idling from ~6 m (outside their look-at radius) and then up close, and the four city
     colonists (Torr, Mira, Linn, Vex) idling;
  2. a walk and run over city paving -> West Gate threshold/apron -> Berms sand/gravel -> depot yard apron, with a
     jump landing, polling the surface the footstep system reports;
  3. the pistol: locker, draw (7), third-person aim (hold RMB) and fire, hip fire (F), first person (mouse-wheel zoom
     to the eye), aim-down-sights and fire, first-person walk, and a close wall at the Warden post container;
  4. walking back inside the walls (pistol must holster; view model hidden).
Fails on runtime exceptions in Player.log. Works against older builds too (missing snapshot fields are reported, not
asserted), so the same script records the "before" baseline. Loudness of each audio segment is measured (EBU R128).
"""
import asyncio, json, math, os, subprocess, shutil, base64, time
from pathlib import Path
from native_client import Client
from settings_test_input import focus, key, window
from Xlib import X
from Xlib.ext import xtest

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('ATHEN_FEEL_EVIDENCE', ROOT / 'evidence/character-feel/20260927/native-after')).resolve(); OUT.mkdir(parents=True, exist_ok=True)
BUILD = Path(os.environ.get('ATHEN_FEEL_BUILD', ROOT / 'AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64'))
GUARDS = {'Warden Ossa': (-69.4, -1.6, -3.3, 'checkpoint_ossa'), 'Warden Rell': (-61.6, -0.4, -1.3, 'checkpoint_rell')}
COLONISTS = {'Torr': (9.0, 0.3, -12.0, 'mission_slab'), 'Mira': (8.0, .5, 15.8, 'basic_general'), 'Linn': (2.5, 1.5, 4.7, 'oa_hill'), 'Vex': (41.7, 0, -1.5, 'west_gate')}


def monitor_source():
    sink = subprocess.run(['pactl', 'get-default-sink'], capture_output=True, text=True).stdout.strip()
    return sink + '.monitor'


def lufs(path):
    out = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(path), '-vn', '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
    summary = out[out.rfind('Summary:'):]
    val = lambda key: float(summary.split(key)[1].split()[0]) if key in summary else None
    return {'integrated_lufs': val('I:'), 'loudness_range_lu': val('LRA:'), 'true_peak_dbfs': val('Peak:')}


async def main():
    report = {'build': str(BUILD), 'passed': False, 'checks': [], 'notes': [], 'segments': {}, 'surfaces_seen': {}}
    env = dict(os.environ, XDG_CONFIG_HOME=str(OUT / 'config'))
    video = json.loads((ROOT / 'evidence/courtyard/20260908/after-native/settings.json').read_text())['video']
    for vendor, product in [('unknown', 'unknown'), ('Free Column', 'Athen Hill')]:
        prefs = OUT / 'config/unity3d' / vendor / product; prefs.mkdir(parents=True, exist_ok=True)
        encoded = base64.b64encode(json.dumps(video).encode()).decode()
        (prefs / 'prefs').write_text('<unity_prefs version_major="1" version_minor="1"><pref name="AthenHill.Settings.v1.QA.Video" type="string">' + encoded + '</pref></unity_prefs>')
    p = subprocess.Popen([str(BUILD), '-force-glcore', '-screen-fullscreen', '0', '-screen-width', '1920', '-screen-height', '1080',
                          '-logFile', str(OUT / 'Player.log'), '--athen-qa', str(OUT), '--athen-qa-background'], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    (OUT / 'pid').write_text(str(p.pid))
    os.environ.update(ATHEN_NATIVE_DIR=str(OUT), ATHEN_NATIVE_PID=str(p.pid))
    rec = None

    warped = []

    def focused():
        # Centre the pointer once only: a warp while aiming is read as mouse look and drags the camera.
        d = focus(); w = window(d); w.set_input_focus(X.RevertToParent, X.CurrentTime)
        if not warped:
            g = w.get_geometry(); xy = d.screen().root.translate_coords(w, 0, 0)
            xtest.fake_input(d, X.MotionNotify, x=xy.x + g.width // 2, y=xy.y + g.height // 2); warped.append(1)
        d.sync(); return d

    def snap(): return json.loads((OUT / 'snapshot.json').read_text())

    async def tap(name, seconds=.12, settle=.35):
        d = focused(); key(d, name, True); await asyncio.sleep(seconds); key(d, name, False); await asyncio.sleep(settle)

    def button(n, down):
        d = focused(); xtest.fake_input(d, X.ButtonPress if down else X.ButtonRelease, n); d.sync()

    async def click(n, settle=.3):
        button(n, True); await asyncio.sleep(.06); button(n, False); await asyncio.sleep(settle)

    def start(name):
        nonlocal rec
        wid = window(focus()).id
        rec = (name, subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'x11grab', '-framerate', '30', '-window_id', str(wid), '-i', os.environ['DISPLAY'],
                                       '-f', 'pulse', '-i', monitor_source(), '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '22', '-pix_fmt', 'yuv420p',
                                       '-c:a', 'aac', '-b:a', '192k', str(OUT / (name + '.mp4'))], stdin=subprocess.PIPE, stderr=(OUT / (name + '-ffmpeg.log')).open('wb'), stdout=subprocess.DEVNULL))

    def stop():
        nonlocal rec
        if not rec: return
        name, proc = rec; rec = None
        if proc.poll() is None:
            try: proc.communicate(b'q', timeout=15)
            except subprocess.TimeoutExpired: proc.kill()
        report['segments'][name] = lufs(OUT / (name + '.mp4'))

    async with Client() as c:
        async def cmd(**kw): await c.command(kw); await asyncio.sleep(.3)

        async def capture(name):
            await cmd(action='capture', name=name); await cmd(action='uiSnapshot'); shutil.copyfile(OUT / 'snapshot.json', OUT / (name + '-state.json'))

        async def try_cmd(**kw):
            try: await cmd(**kw); return True
            except TimeoutError: report['notes'].append('build does not support ' + kw['action']); return False

        def yaw_to(x, z):
            px, _, pz = snap()['player']['position']; return math.degrees(math.atan2(x - px, z - pz)) % 360

        async def walk_poll(keys, seconds, label):
            d = focused()
            for k in keys: key(d, k, True)
            t0 = time.time()
            while time.time() - t0 < seconds:
                await asyncio.sleep(.25)
                s = snap(); f = s.get('footsteps')
                if f:
                    report['surfaces_seen'].setdefault(label, {}); report['surfaces_seen'][label][f['under']] = report['surfaces_seen'][label].get(f['under'], 0) + 1
            for k in reversed(keys): key(d, k, False)
            await asyncio.sleep(.3)

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
            await asyncio.sleep(2)
            for _ in range(6):
                await tap('Return', .12, 1.5)
                if snap()['session']['state'] != 'MainMenu': break
            d0 = focused()
            for k in ['d', 'Right', 'a', 'Left', 'w', 's', 'Up', 'Down', 'Shift_L', 'Shift_R', 'Control_L', 'e', 'f', 'space']: key(d0, k, False)
            for b in (1, 3): xtest.fake_input(d0, X.ButtonRelease, b)
            d0.sync()
            for _ in range(1800):
                if snap()['session']['state'] == 'Play': break
                await asyncio.sleep(.1)
            assert snap()['session']['state'] == 'Play'
            await cmd(action='resize', width=1920, height=1080); await asyncio.sleep(2)
            await cmd(action='timeSet', hour=12); await cmd(action='timePause', paused=True)
            await cmd(action='view', camera='follow')

            # 1. Wardens and colonists
            start('guards')
            for name, (gx, gy, gz, lm) in list(GUARDS.items()) + list(COLONISTS.items()):
                await cmd(action='goto', landmark=lm); await asyncio.sleep(.4)
                await cmd(action='cameraYaw', yaw=yaw_to(gx, gz)); await try_cmd(action='cameraPitch', pitch=8)
                await tap('s', 1.3, .6)                       # back away to ~5 m (outside the 4 m look-at radius)
                await asyncio.sleep(1)
                await cmd(action='cameraYaw', yaw=yaw_to(gx, gz)); await asyncio.sleep(.5)
                await capture('guard-' + name.split()[-1].lower() + '-far')
                await asyncio.sleep(12 if name in GUARDS else 5)
                if name in GUARDS:
                    await tap('w', 1.0, .5)                   # step in: the Warden should turn its head to you
                    await cmd(action='cameraYaw', yaw=(yaw_to(gx, gz) + 32) % 360); await asyncio.sleep(3)
                    await capture('guard-' + name.split()[-1].lower() + '-near')
                    s = snap(); report.setdefault('guard_states', {})[name] = s.get('guards')
                    await asyncio.sleep(5)
            stop()
            report['checks'].append('Recorded Wardens (far ~12 s + near ~8 s each) and colonists (~5 s each)')
            await try_cmd(action='cameraPitch', pitch=17)

            # 2. surface walk/run with audio
            start('surfaces')
            await cmd(action='goto', landmark='east_wreck'); await cmd(action='cameraYaw', yaw=270); await asyncio.sleep(1.5)
            await walk_poll(['w'], 3.5, 'city paving to gate')
            await walk_poll(['w'], 3.0, 'gate threshold and apron to berms')
            await walk_poll(['w'], 3.0, 'berms walk')
            await walk_poll(['Shift_L', 'w'], 3.0, 'berms run')
            await tap('space', .1, 1.2)
            await cmd(action='goto', landmark='checkpoint_road'); await cmd(action='cameraYaw', yaw=200); await asyncio.sleep(.8)
            await walk_poll(['w'], 3.0, 'service road')
            await cmd(action='goto', landmark='depot_approach'); await cmd(action='cameraYaw', yaw=190); await asyncio.sleep(.8)
            await walk_poll(['w'], 3.0, 'depot approach to yard apron')
            await walk_poll(['Shift_L', 'w'], 2.0, 'depot yard run')
            await asyncio.sleep(.8)
            stop()
            s = snap(); f = s.get('footsteps')
            if f:
                report['footsteps'] = f
                seen = {k for v in report['surfaces_seen'].values() for k in v}
                report['checks'].append(f'Footsteps: {f["StepCount"]} steps, {f["LandCount"]} landings; surfaces under the player: {sorted(seen)}')
                assert f['StepCount'] >= 20, f
                assert {'Stone', 'Concrete', 'Sand'} <= seen, seen
            else:
                report['notes'].append('No footstep system in this build (baseline).')

            # 3. pistol
            await cmd(action='goto', landmark='checkpoint_locker'); await tap('e')
            s = snap(); assert s['combat']['hasPistol'], s['combat']
            await cmd(action='goto', landmark='checkpoint_firingline'); await cmd(action='cameraYaw', yaw=0); await try_cmd(action='cameraPitch', pitch=10); await asyncio.sleep(.5)
            start('pistol-third-person')
            await tap('7', .1, .12); await capture('tp-draw'); await asyncio.sleep(1)
            assert snap()['combat']['Armed']
            await capture('tp-armed-idle')
            button(3, True); await asyncio.sleep(.6)
            report['tp_pitch_after_aim_press'] = snap()['camera'].get('pitch')
            await try_cmd(action='cameraPitch', pitch=10); await cmd(action='cameraYaw', yaw=0); await asyncio.sleep(.3); await capture('tp-aim')
            s = snap(); report['tp_aim_state'] = s['combat']
            for _ in range(4): await click(1, .45)
            await asyncio.sleep(.4); button(3, False); await asyncio.sleep(.8)
            await try_cmd(action='cameraPitch', pitch=10); await cmd(action='cameraYaw', yaw=20)
            for _ in range(3): await tap('f', .06, .5)
            await capture('tp-after-hipfire')
            await asyncio.sleep(1.2)
            for _ in range(8): await tap('f', .05, .25)          # rapid fire at ~fireInterval
            await asyncio.sleep(1.5)
            stop()
            report['checks'].append('Third-person draw, aim (RMB), aimed fire (LMB) x4, hip fire x3, rapid fire x8')
            # first person by the mouse wheel (real input)
            for _ in range(9): await click(4, .08)
            await try_cmd(action='cameraPitch', pitch=4); await cmd(action='cameraYaw', yaw=0)
            await asyncio.sleep(.8)
            s = snap(); report['fp_camera'] = s['camera']
            assert s['camera']['firstPerson'], s['camera']
            start('pistol-first-person')
            await capture('fp-hip')
            vm = s['combat'].get('viewModelVisible')
            if vm is None: report['notes'].append('No first-person view model in this build (baseline).')
            else: assert vm, s['combat']
            button(3, True); await asyncio.sleep(.6); await try_cmd(action='cameraPitch', pitch=4); await cmd(action='cameraYaw', yaw=0); await asyncio.sleep(.3); await capture('fp-ads')
            for _ in range(4): await click(1, .45)
            button(3, False); await asyncio.sleep(.6)
            for _ in range(3): await tap('f', .06, .45)
            await walk_poll(['w'], 1.5, 'fp walk (armed)')
            await capture('fp-after-walk')
            await asyncio.sleep(1)
            stop()
            s = snap(); report['fp_combat'] = s['combat']
            if vm is not None:
                assert s['combat']['viewModelFlashes'] >= 5, s['combat']
                report['checks'].append(f'First person: view model visible, ADS and fire; {s["combat"]["viewModelFlashes"]} view-model flashes')
            # close wall at the Warden post container (the view model must not clip)
            await cmd(action='goto', landmark='checkpoint_locker'); await asyncio.sleep(.5)
            for yaw in (0, 90, 180, 270):
                await cmd(action='cameraYaw', yaw=yaw); await tap('w', .8, .4); await capture(f'fp-wall-{yaw}')
            # 4. back inside the walls: holster
            for _ in range(9): await click(5, .08)
            await cmd(action='goto', landmark='checkpoint_approach'); await asyncio.sleep(1.5)
            s = snap()
            assert not s['combat']['Armed'], s['combat']
            if s['combat'].get('viewModelVisible') is not None: assert not s['combat']['viewModelVisible'], s['combat']
            report['checks'].append('Pistol holstered inside the walls; view model hidden')
            await cmd(action='settingsSnapshot')
            errors = [l for l in (OUT / 'Player.log').read_text().splitlines() if ('Exception:' in l or 'NullReference' in l)
                      and not ('Unknown QA operation' in l and any(n.startswith('build does not support') for n in report['notes']))]
            assert not errors, errors[:5]
            report['checks'].append('No runtime exceptions in Player.log')
            report['passed'] = True
        except Exception as e:
            report['error'] = repr(e); raise
        finally:
            for b in (1, 3):
                try: button(b, False)
                except Exception: pass
            stop()
            (OUT / 'report.json').write_text(json.dumps(report, indent=2))
            try: await cmd(action='quit')
            except Exception: pass
            try: p.wait(timeout=5)
            except subprocess.TimeoutExpired: p.terminate()

asyncio.run(main())
