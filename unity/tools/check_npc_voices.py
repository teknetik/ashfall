"""Real-key native check for NPC dialogue clip playback and stop/advance behavior."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evidence/npc-voices/20261002/native'


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name in ('snapshot.json', 'command.json', 'ack.json', 'qa-error.json'):
        (OUT / name).unlink(missing_ok=True)
    player = None
    report = {'complete': False, 'checks': []}
    try:
        player = subprocess.Popen([str(ROOT / 'AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64'),
            '-force-glcore', '-screen-fullscreen', '0', '-screen-width', '1280', '-screen-height', '720',
            '-logFile', str(OUT / 'Player.log'), '--athen-qa', str(OUT)],
            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        os.environ.update(ATHEN_NATIVE_DIR=str(OUT), ATHEN_NATIVE_PID=str(player.pid))
        from Xlib import X
        from desktop_input import focus_window, key
        from native_client import Client
        deadline = time.monotonic() + 90
        while not (OUT / 'snapshot.json').exists():
            if player.poll() is not None: raise RuntimeError('Native player exited during startup')
            if time.monotonic() > deadline: raise TimeoutError('No native QA snapshot')
            await asyncio.sleep(.2)
        display, window = focus_window()

        async def tap(name):
            window.set_input_focus(X.RevertToParent, X.CurrentTime)
            display.sync()
            key(display, name, True)
            try: await asyncio.sleep(.09)
            finally: key(display, name, False)
            await asyncio.sleep(.28)

        async with Client() as client:
            async def snapshot(): return await client.snapshot()
            current = await snapshot()
            if current['session']['state'] == 'MainMenu':
                await asyncio.sleep(2)
                for _ in range(30):
                    if (await snapshot())['session']['focused'] in ('start-game', 'continue-game'):
                        break
                    await tap('Tab')
                else: raise RuntimeError('Start/Continue button did not accept keyboard focus')
                await tap('Return')
            elif current['session']['state'] == 'Paused':
                await tap('Escape')
            state = await snapshot()
            assert state['session']['state'] == 'Play', (state['session']['state'], state['session']['focused'])
            for landmark, actor, first in (
                ('basic_general', 'npc_mira', 'greeting'),
                ('mission_slab', 'npc_torr', 'greeting'),
                ('west_gate', 'npc_vex', 'greeting'),
                ('oa_hill', 'npc_linn', 'greeting')):
                await client.command({'action': 'goto', 'landmark': landmark})
                await tap('e')
                await asyncio.sleep(.45)
                state = await snapshot()
                assert state['session']['state'] == 'Dialogue' and state['interaction']['node'] == first, state['interaction']
                expected = f'{actor}-{first}'
                sources = [s for s in state['audio']['sources'] if s['clip'] == expected]
                assert len(sources) == 1 and sources[0]['playing'] and sources[0]['group'] == 'SFX', (expected, sources)
                report['checks'].append({'actor': actor, 'node': first, 'clip': expected,
                    'playing': sources[0]['playing'], 'group': sources[0]['group'], 'volume': sources[0]['volume']})
                if actor in ('npc_mira', 'npc_torr'):
                    for _ in range(20):
                        if (await snapshot())['session']['focused'] == 'choice0': break
                        await tap('Tab')
                    else: raise RuntimeError(actor + ' dialogue choice not keyboard focusable')
                    await tap('Return')
                    await asyncio.sleep(.4)
                    state = await snapshot()
                    if actor == 'npc_torr':
                        assert state['interaction']['node'] == 'slab'
                        assert any(s['clip'] == 'npc_torr-slab' and s['playing'] for s in state['audio']['sources'])
                        report['checks'].append({'actor': actor, 'node': 'slab', 'clip': 'npc_torr-slab', 'playing': True})
                    else:
                        assert state['session']['state'] == 'Shop'
                        assert not any(s['clip'] == expected and s['playing'] for s in state['audio']['sources'])
                        report['checks'].append({'actor': actor, 'node': 'shop', 'voiceStopped': True})
                await tap('Escape')
                state = await snapshot()
                assert state['session']['state'] == 'Play'
                assert not any(s['clip'] and s['clip'].startswith(actor + '-') and s['playing'] for s in state['audio']['sources'])
            await client.command({'action': 'quit'})
        player.wait(timeout=20)
        log = (OUT / 'Player.log').read_text()
        assert 'NullReferenceException' not in log and 'error CS' not in log
        report['complete'] = True
        print('PASS: four NPCs speak; node change replaces a clip; Escape stops speech', flush=True)
    except Exception as error:
        report['error'] = str(error)
        raise
    finally:
        if player and player.poll() is None:
            player.terminate()
            try: player.wait(timeout=10)
            except subprocess.TimeoutExpired: player.kill()
        (OUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    asyncio.run(main())
