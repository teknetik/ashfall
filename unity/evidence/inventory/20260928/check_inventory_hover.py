"""Native inventory hover acceptance: hover preview must temporarily override selection.

Writes evidence under unity/evidence/inventory/20260928/native by default.
Requires a Development player with NativeQa enabled.

This script specifically exercises a 2-item inventory (scrap_coil + water_flask)
so the overview can switch on pointer hover.
"""

import asyncio
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

from Xlib import X
from Xlib.ext import xtest

ROOT = pathlib.Path(__file__).resolve().parents[4]  # repo root
TOOLS = ROOT / 'unity' / 'tools'
sys.path.insert(0, str(TOOLS))

from native_client import Client
from desktop_input import focus, focus_window, key, click

BUILD = ROOT / 'unity' / 'AthenHill' / 'Builds' / 'LinuxDevelopment' / 'AthenHill.x86_64'
OUT = pathlib.Path(
    os.environ.get(
        'ATHEN_INVENTORY_EVIDENCE',
        ROOT / 'unity' / 'evidence' / 'inventory' / '20260928' / 'native',
    )
)


def snapshot():
    return json.loads((OUT / 'snapshot.json').read_text())


def move(d, x, y):
    xtest.fake_input(d, X.MotionNotify, x=x, y=y)
    d.sync()


async def wait_for_snapshot(proc, timeout=60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if (OUT / 'snapshot.json').exists():
            return
        if proc.poll() is not None:
            raise RuntimeError('Player exited early')
        await asyncio.sleep(0.2)
    raise TimeoutError('No native snapshot created')


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name in (
        'snapshot.json',
        'ack.json',
        'command.json',
        'qa-error.json',
        'ui-layout.json',
        'Player.log',
        'launcher.log',
        'report.json',
    ):
        (OUT / name).unlink(missing_ok=True)

    config = OUT / 'config'
    config.mkdir(parents=True, exist_ok=True)

    if not BUILD.exists():
        raise FileNotFoundError(f'Development build not found: {BUILD}')

    env = dict(os.environ, XDG_CONFIG_HOME=str(config))

    with open(OUT / 'launcher.log', 'w') as launcher:
        proc = subprocess.Popen(
            [
                str(BUILD),
                '-force-glcore',
                '-screen-fullscreen',
                '0',
                '-screen-width',
                '1920',
                '-screen-height',
                '1080',
                '-logFile',
                str(OUT / 'Player.log'),
                '--athen-qa',
                str(OUT),
            ],
            env=env,
            stdout=launcher,
            stderr=subprocess.STDOUT,
        )

    os.environ.update(ATHEN_NATIVE_DIR=str(OUT), ATHEN_NATIVE_PID=str(proc.pid), ATHEN_EVIDENCE=str(OUT))
    (OUT / 'pid').write_text(str(proc.pid))

    try:
        await wait_for_snapshot(proc)

        async with Client() as c:
            async def cmd(**j):
                await c.command(j)

            async def layout():
                await cmd(action='uiSnapshot')
                return json.loads((OUT / 'ui-layout.json').read_text())

            def _ui_scale(l):
                try:
                    panel = next(e for e in l['elements'] if e.get('name') == 'CityPanel')
                    bw = float(panel['bounds'][2])
                    bh = float(panel['bounds'][3])
                    if bw > 0 and bh > 0:
                        return (float(l['width']) / bw, float(l['height']) / bh)
                except Exception:
                    pass
                return (1.0, 1.0)

            async def _root_point(bounds, l=None):
                # NativeQa layout JSON may represent numbers as strings.
                x, y, w, h = (float(v) for v in bounds)
                if l is None:
                    l = await layout()
                sx, sy = _ui_scale(l)
                d, win = focus_window()
                root = d.screen().root
                tc = root.translate_coords(win, 0, 0)
                wx, wy = tc.x, tc.y
                return d, int(wx + (x + w / 2) * sx), int(wy + (y + h / 2) * sy), wx, wy

            async def bounds_for(name):
                l = await layout()
                for e in l['elements']:
                    if e.get('name') == name:
                        return e['bounds']
                raise KeyError(f'No UI element named {name}')

            async def expect_state(state, timeout=10):
                deadline = time.monotonic() + timeout
                while time.monotonic() < deadline:
                    if snapshot()['session']['state'] == state:
                        return
                    await asyncio.sleep(0.2)
                raise AssertionError(
                    f'Expected state {state} but saw {snapshot()["session"]["state"]}'
                )

            async def tap(k, t=0.08):
                d = focus()
                key(d, k, True)
                try:
                    await asyncio.sleep(t)
                finally:
                    key(d, k, False)
                await asyncio.sleep(0.2)

            async def click_bounds(bounds):
                d, rx, ry, _, _ = await _root_point(bounds)
                click(d, rx, ry)
                await asyncio.sleep(0.25)

            async def capture(name):
                await cmd(action='uiSnapshot')
                shutil.copyfile(OUT / 'ui-layout.json', OUT / f'{name}-ui.json')
                await cmd(action='capture', name=name)
                await asyncio.sleep(0.45)

            async def activate(name):
                # Focus by cycling Tab. Safe in most modals; do not call from Inventory.
                for _ in range(60):
                    if snapshot()['session'].get('focused') == name:
                        await tap('Return')
                        return
                    await tap('Tab')
                raise AssertionError('Could not focus ' + name)

            # Start game. In some WMs the window focus/activation can lag the first
            # simulated keypress; retry a few times rather than failing instantly.
            await asyncio.sleep(1.5)
            if snapshot()['session']['state'] == 'Paused':
                await tap('Escape')
            if snapshot()['session']['state'] != 'Play':
                deadline = time.monotonic() + 25
                while time.monotonic() < deadline and snapshot()['session']['state'] != 'Play':
                    if snapshot()['session']['state'] == 'MainMenu':
                        try:
                            await activate('start-game')
                        except Exception:
                            await click_bounds(await bounds_for('start-game'))
                    else:
                        await tap('Return')
                    await asyncio.sleep(0.8)
                await expect_state('Play', timeout=2)

            # Acquire 2 items: buy water_flask but keep scrap_coil.
            await cmd(action='goto', landmark='basic_general')
            await asyncio.sleep(0.4)
            await tap('e')
            if snapshot()['session']['state'] != 'Shop':
                await expect_state('Dialogue')
                await click_bounds(await bounds_for('choice0'))
                await expect_state('Shop')

            await capture('shop-before-hover-test')
            # Use a direct click instead of keyboard focus-cycling; window-manager focus
            # reporting can drift and cause Enter to activate a different button.
            await click_bounds(await bounds_for('buy0'))
            await asyncio.sleep(0.3)
            await capture('shop-after-buy-0')
            await tap('Escape')
            await expect_state('Play')

            q = snapshot()['session'].get('quantities') or {}
            carried = [k for k, v in q.items() if v and int(v) > 0]
            if 'scrap_coil' not in carried or len(carried) < 2:
                raise AssertionError(
                    'Expected at least 2 carried items including scrap_coil '
                    f'but saw quantities={q}'
                )

            # Open inventory with both items.
            await tap('Tab')
            await expect_state('Inventory')
            await capture('inventory-two-items-initial')

            # Hover preview should temporarily override selection.
            # Use the captured layout snapshot to avoid transient NaN bounds while UI settles.
            initial_layout = json.loads((OUT / 'inventory-two-items-initial-ui.json').read_text())
            scrap_bounds = next(
                e['bounds'] for e in initial_layout['elements'] if e.get('name') == 'inv-scrap_coil'
            )
            d, hx, hy, wx, wy = await _root_point(scrap_bounds, initial_layout)
            move(d, hx, hy)
            await asyncio.sleep(0.35)
            await capture('inventory-two-items-hover-scrap')

            # Move pointer away; overview should return to the selected/focused item.
            move(d, int(wx + 10), int(wy + 10))
            await asyncio.sleep(0.35)
            await capture('inventory-two-items-hover-exit')

            await cmd(action='quit')
            await asyncio.sleep(0.8)

        report = {
            'complete': True,
            'screenshots': sorted(p.name for p in OUT.glob('*.png')),
            'finalState': snapshot()['session']['state'],
            'credits': snapshot()['session'].get('credits'),
            'quantities': snapshot()['session'].get('quantities'),
        }
        (OUT / 'report.json').write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))

    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == '__main__':
    asyncio.run(main())
