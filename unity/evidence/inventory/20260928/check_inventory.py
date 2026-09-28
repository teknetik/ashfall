"""Native inventory acceptance: Tab toggle, compact grid, overview hover/focus, inspection subwindow.

Writes evidence under unity/evidence/inventory/20260928/native by default.
Requires a Development player with NativeQa enabled.
"""

import asyncio
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[4]  # repo root
TOOLS = ROOT / 'unity' / 'tools'
sys.path.insert(0, str(TOOLS))

from native_client import Client
from desktop_input import focus, key, click

BUILD = ROOT / 'unity' / 'AthenHill' / 'Builds' / 'LinuxDevelopment' / 'AthenHill.x86_64'
OUT = pathlib.Path(os.environ.get('ATHEN_INVENTORY_EVIDENCE', ROOT / 'unity' / 'evidence' / 'inventory' / '20260928' / 'native'))


def snapshot():
    return json.loads((OUT / 'snapshot.json').read_text())


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
    for name in ('snapshot.json', 'ack.json', 'command.json', 'qa-error.json', 'ui-layout.json', 'Player.log', 'launcher.log'):
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
                '-screen-fullscreen', '0',
                '-screen-width', '1920',
                '-screen-height', '1080',
                '-logFile', str(OUT / 'Player.log'),
                '--athen-qa', str(OUT),
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

            async def capture(name):
                await cmd(action='uiSnapshot')
                shutil.copyfile(OUT / 'ui-layout.json', OUT / f'{name}-ui.json')
                await cmd(action='capture', name=name)
                await asyncio.sleep(0.45)

            async def tap(k, t=0.08):
                d = focus()
                key(d, k, True)
                try:
                    await asyncio.sleep(t)
                finally:
                    key(d, k, False)
                await asyncio.sleep(0.2)

            async def shift_click(bounds):
                x, y, w, h = bounds
                d = focus()
                key(d, 'Shift_L', True)
                try:
                    click(d, int(x + w / 2), int(y + h / 2))
                finally:
                    key(d, 'Shift_L', False)
                await asyncio.sleep(0.25)

            async def expect_state(state, timeout=10):
                deadline = time.monotonic() + timeout
                while time.monotonic() < deadline:
                    if snapshot()['session']['state'] == state:
                        return
                    await asyncio.sleep(0.2)
                raise AssertionError(f'Expected state {state} but saw {snapshot()["session"]["state"]}')

            async def layout():
                await cmd(action='uiSnapshot')
                return json.loads((OUT / 'ui-layout.json').read_text())

            async def bounds_for(name):
                l = await layout()
                for e in l['elements']:
                    if e.get('name') == name:
                        return e['bounds']
                raise KeyError(f'No UI element named {name}')

            async def activate(name):
                # Focus by cycling Tab. Safe in most modals; do not call from Inventory.
                for _ in range(60):
                    if snapshot()['session'].get('focused') == name:
                        await tap('Return')
                        return
                    await tap('Tab')
                raise AssertionError('Could not focus ' + name)

            # Start game (MainMenu should have start-game focused by default).
            await asyncio.sleep(1.5)
            if snapshot()['session']['state'] == 'Paused':
                await tap('Escape')
            if snapshot()['session']['state'] != 'Play':
                await tap('Return')
                await expect_state('Play')

            await cmd(action='view', camera='cam_avenue')
            await capture('play-avenue')

            # Tab opens inventory from play.
            await tap('Tab')
            await expect_state('Inventory')
            await capture('inventory-initial')

            # Open details via Enter.
            await tap('Return')
            await asyncio.sleep(0.2)
            await capture('inventory-details-enter')

            # Esc closes details first, then inventory.
            await tap('Escape')
            await asyncio.sleep(0.2)
            await capture('inventory-after-esc-details-closed')
            assert snapshot()['session']['state'] == 'Inventory'
            await tap('Escape')
            await expect_state('Play')

            # Tab opens, Tab closes inventory.
            await tap('Tab')
            await expect_state('Inventory')
            await capture('inventory-before-tab-close')
            await tap('Tab')
            await expect_state('Play')

            # Buy a flask, sell scrap to test live quantities + empty state.
            await cmd(action='goto', landmark='basic_general')
            await asyncio.sleep(0.4)
            await tap('e')
            await expect_state('Dialogue')
            await activate('choice0')
            await expect_state('Shop')
            await capture('shop-open')

            # While in shop, Tab must not open inventory.
            await tap('Tab')
            await expect_state('Shop')

            # Buy water flask, then sell scrap coil.
            await activate('buy0')
            await asyncio.sleep(0.25)
            await activate('sell2')
            await asyncio.sleep(0.25)
            await capture('shop-after-trades')
            await tap('Escape')
            await expect_state('Play')

            # Inventory should now be empty (flask 1, scrap 0) OR show flask only depending on starting inventory.
            await tap('Tab')
            await expect_state('Inventory')
            await capture('inventory-after-trades')

            # Shift+click opens details.
            tile_bounds = await bounds_for('inv-water_flask')
            await shift_click(tile_bounds)
            await asyncio.sleep(0.2)
            await capture('inventory-details-shift-click')

            # Small viewport smoke check.
            await cmd(action='resize', width=1280, height=720)
            await asyncio.sleep(1.0)
            await capture('play-1280x720')
            await tap('Tab')
            await expect_state('Inventory')
            await capture('inventory-1280x720')
            await tap('Escape')
            await expect_state('Play')

            await cmd(action='quit')
            await asyncio.sleep(0.8)

        # Summarise evidence.
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
