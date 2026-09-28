"""Verify startup/menu/settings/movement with real input in the Linux player."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import shutil
import time

from PIL import Image, ImageStat
from native_client import Client
from settings_test_input import focus, key, click, window

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('ATHEN_MENU_EVIDENCE', ROOT / 'evidence/startup-menu/20260926/native'))
OUT.mkdir(parents=True, exist_ok=True)


async def main():
    report = {'passed': False, 'checks': []}
    config = OUT / 'config'
    config.mkdir(exist_ok=True)
    player = os.environ.get('ATHEN_MENU_PLAYER', str(ROOT / 'AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64'))
    for name in ('snapshot.json', 'command.json', 'ack.json'):
        (OUT / name).unlink(missing_ok=True)
    process = subprocess.Popen([player, '-force-glcore', '-screen-fullscreen', '0',
        '-screen-width', '1920', '-screen-height', '1080', '-logFile', str(OUT / 'Player.log'),
        '--athen-qa', str(OUT), '--athen-qa-background'], env=dict(os.environ, XDG_CONFIG_HOME=str(config)),
        stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    os.environ.update(ATHEN_NATIVE_DIR=str(OUT), ATHEN_NATIVE_PID=str(process.pid))
    def focus_player(resize=False):
        d = focus()
        if shutil.which('hyprctl'):
            selector = f'pid:{process.pid}'
            if resize:
                subprocess.run(['hyprctl', '-i', '0', 'dispatch', 'hl.dsp.window.float({action="set",window="' + selector + '"})'], check=True, capture_output=True)
                # Hyprland dispatch sizes are logical; use its recorded monitor scale.
                clients = json.loads(subprocess.check_output(['hyprctl', '-i', '0', 'clients', '-j']))
                own = next(w for w in clients if w['pid'] == process.pid)
                monitors = json.loads(subprocess.check_output(['hyprctl', '-i', '0', 'monitors', '-j']))
                scale = next(m['scale'] for m in monitors if m['id'] == own['monitor'])
                expression = f'hl.dsp.window.resize({{x={round(1920/scale)},y={round(1080/scale)},window="{selector}"}})'
                subprocess.run(['hyprctl', '-i', '0', 'dispatch', expression], check=True, capture_output=True)
            subprocess.run(['hyprctl', '-i', '0', 'dispatch', 'hl.dsp.focus({window="' + selector + '"})'], check=True, capture_output=True)
        w = window(d)
        g = w.get_geometry()
        origin = d.screen().root.translate_coords(w, 0, 0)
        from Xlib import X
        from Xlib.ext import xtest
        xtest.fake_input(d, X.MotionNotify, x=origin.x + g.width // 2, y=origin.y + g.height // 2)
        w.set_input_focus(X.RevertToParent, X.CurrentTime)
        d.sync()
        time.sleep(.1)
        return d
    def snap():
        return json.loads((OUT / 'snapshot.json').read_text())
    try:
        # Size the test window before Unity renders its first scene frame. Forcing
        # compositor sizing after GL initialization produced blank surfaces here.
        for _ in range(300):
            try:
                d = focus_player(resize=True)
                break
            except (RuntimeError, StopIteration):
                await asyncio.sleep(.03)
        else:
            raise TimeoutError('Native test window did not open')
        for _ in range(300):
            if (OUT / 'snapshot.json').exists() and snap()['session']['state'] == 'MainMenu':
                break
            assert process.poll() is None, 'Player exited at startup'
            try:
                focus_player()
            except RuntimeError:
                pass
            await asyncio.sleep(.2)
        else:
            raise TimeoutError('Startup menu did not open')
        d = focus_player()
        await asyncio.sleep(1)
        async def settle(frames=2):
            frame = snap()['frame']
            deadline = time.monotonic() + 10
            while snap()['frame'] < frame + frames:
                if time.monotonic() > deadline:
                    raise TimeoutError('Native player stopped producing frames')
                await asyncio.sleep(.1)
        async def tap(name, duration=.08):
            focus_player()
            key(d, name, True)
            try:
                await asyncio.sleep(duration)
            finally:
                key(d, name, False)
            await settle()
        async with Client() as client:
            async def layout():
                await client.command({'action': 'uiSnapshot'})
                return json.loads((OUT / 'ui-layout.json').read_text())
            async def capture(name):
                focus_player()
                await settle(4)
                data = await layout()
                (OUT / (name + '-layout.json')).write_text(json.dumps(data, indent=2))
                await client.command({'action': 'capture', 'name': name})
                await asyncio.sleep(.4)
                assert sum(ImageStat.Stat(Image.open(OUT / (name + '.png'))).stddev[:3]) > 15, 'Blank native capture: ' + name
            async def activate(name):
                for _ in range(35):
                    if snap()['session']['focused'] == name:
                        await tap('Return')
                        return
                    await tap('Tab')
                raise AssertionError('Cannot focus ' + name)
            async def click_control(name):
                data = await layout()
                e = next(e for e in data['elements'] if e['name'] == name)
                assert e['visible'] and e['enabled'], e
                # Panel coordinates scale with the authored 1920x1080 reference.
                screen = next(e for e in data['elements'] if e['name'] == 'startup-screen')
                sx, sy = data['width'] / screen['bounds'][2], data['height'] / screen['bounds'][3]
                x, y, width, height = e['bounds']
                native = window(d)
                origin = d.screen().root.translate_coords(native, 0, 0)
                click(d, round(origin.x + (x + width / 2) * sx), round(origin.y + (y + height / 2) * sy))
                await settle()
            await asyncio.sleep(1)
            assert snap()['session']['focused'] == 'start-game', snap()
            await capture('startup-1920x1080')
            assert not next(e for e in (await layout())['elements'] if e['name'] == 'hud')['visible']
            before = snap()['player']['position']
            await tap('w', .6)
            await tap('space')
            await tap('Escape')
            assert snap()['session']['state'] == 'MainMenu'
            assert snap()['player']['position'] == before
            report['checks'].append('Menu blocks movement, jump and Escape bypass; HUD hidden; Start Game focused')
            await click_control('startup-settings')
            assert snap()['session']['state'] == 'Settings'
            await capture('startup-settings-sound')
            await client.command({'action': 'settingsSnapshot'})
            settings = json.loads((OUT / 'settings.json').read_text())
            assert settings['timeScale'] == 0
            assert not snap()['audio']['paused']
            reduced = snap()['session']['reducedMotion']
            await activate('settings-reduced-motion')
            assert snap()['session']['reducedMotion'] != reduced
            await activate('video-tab')
            await capture('startup-settings-video')
            await activate('graphics-preset')
            await tap('Home')
            await tap('Return')
            await activate('apply-video')
            await client.command({'action': 'settingsSnapshot'})
            assert json.loads((OUT / 'settings.json').read_text())['previewing']
            await tap('Escape')
            assert snap()['session']['state'] == 'Settings'
            await client.command({'action': 'settingsSnapshot'})
            assert not json.loads((OUT / 'settings.json').read_text())['previewing']
            await tap('Escape')
            assert snap()['session']['state'] == 'MainMenu'
            assert snap()['session']['focused'] == 'start-game'
            report['checks'].append('Mouse opens Settings; sound/video/accessibility work; preview reverts before Escape returns to menu')
            await click_control('startup-settings')
            await activate('video-tab')
            data = await layout()
            field = next(e for e in data['elements'] if e['name'] == 'resolution')
            index = field['choices'].index('1280 × 720')
            await activate('resolution')
            await tap('Home')
            for _ in range(index):
                await tap('Down')
            await tap('Return')
            await activate('apply-video')
            await asyncio.sleep(1)
            d = focus_player()
            await activate('keep-video')
            await tap('Escape')
            assert snap()['session']['state'] == 'MainMenu'
            assert (snap()['width'], snap()['height']) == (1280, 720), snap()
            await capture('startup-1280x720')
            report['checks'].append('Menu remains readable at 1280x720 after confirmed display change')
            await tap('Return')
            assert snap()['session']['state'] == 'Play'
            await capture('started-game')
            data = await layout()
            assert next(e for e in data['elements'] if e['name'] == 'hud')['visible']
            assert not next(e for e in data['elements'] if e['name'] == 'startup-screen')['visible']
            before = snap()['player']['position']
            await tap('w', .8)
            after = snap()['player']['position']
            assert sum((a-b)**2 for a,b in zip(before,after)) > .2
            await tap('Escape')
            assert snap()['session']['state'] == 'Paused'
            await activate('settings-button')
            await tap('Escape')
            assert snap()['session']['state'] == 'Paused'
            await tap('Escape')
            assert snap()['session']['state'] == 'Play'
            report['checks'].append('Keyboard starts game; HUD appears; movement works; in-game Settings returns to Pause')
        log = (OUT / 'Player.log').read_text()
        assert 'Exception:' not in log and 'NullReferenceException' not in log
        report['passed'] = True
        print(json.dumps(report, indent=2), flush=True)
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
        (OUT / 'report.json').write_text(json.dumps(report, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
