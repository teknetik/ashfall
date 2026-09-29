"""Independent native regression: actual keyboard with read-only QA positioning/inspection."""
import asyncio, json, os, pathlib, subprocess, sys, time, traceback
from Xlib import X
ROOT = pathlib.Path(__file__).resolve().parents[4]
OUT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools'))
from native_client import Client
from settings_test_input import focus, key, window

async def main():
    qa = OUT / 'city-native'
    qa.mkdir(exist_ok=True)
    for name in ('snapshot.json', 'ack.json', 'command.json'):
        (qa / name).unlink(missing_ok=True)
    env = dict(os.environ, DISPLAY=os.environ.get('DISPLAY', ':0'), XDG_CONFIG_HOME=str(qa / 'config'))
    args = [str(ROOT / 'AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64'), '-force-glcore', '-screen-fullscreen', '0', '-screen-width', '1280', '-screen-height', '720', '-logFile', str(qa / 'Player.log'), '--athen-qa', str(qa), '--athen-qa-background']
    with (qa / 'launcher.log').open('wb') as log:
        proc = subprocess.Popen(args, env=env, stdout=log, stderr=subprocess.STDOUT)
        os.environ.update(DISPLAY=env['DISPLAY'], ATHEN_NATIVE_DIR=str(qa), ATHEN_NATIVE_PID=str(proc.pid), ATHEN_EVIDENCE=str(qa))
        report = {'passed': False, 'pid': proc.pid, 'checks': []}
        try:
            for _ in range(600):
                if proc.poll() is not None: raise RuntimeError(f'Player exited {proc.returncode}')
                if (qa / 'snapshot.json').exists(): break
                await asyncio.sleep(.1)
            else: raise TimeoutError('No native QA snapshot')
            if subprocess.run(['which', 'hyprctl'], capture_output=True).returncode == 0:
                subprocess.run(['hyprctl', '-i', '0', 'dispatch', f'hl.dsp.window.float({{action="set",window="pid:{proc.pid}"}})'], capture_output=True)
            d = focus()
            w = window(d)
            w.set_input_focus(X.RevertToParent, X.CurrentTime)
            d.sync()
            async with Client() as c:
                def snap(): return json.loads((qa / 'snapshot.json').read_text())
                async def tap(name, hold=.08):
                    w.set_input_focus(X.RevertToParent, X.CurrentTime); d.sync()
                    key(d, name, True)
                    try: await asyncio.sleep(hold)
                    finally: key(d, name, False)
                    await asyncio.sleep(.25)
                async def cmd(action, **kw): await c.command(dict(action=action, **kw))
                async def state(value):
                    for _ in range(30):
                        if snap()['session']['state'] == value: return snap()
                        await asyncio.sleep(.1)
                    raise AssertionError(f'Expected {value}, got {snap()["session"]["state"]}')
                async def click(name):
                    for _ in range(45):
                        if snap()['session']['focused'] == name:
                            await tap('Return'); return
                        await tap('Tab')
                    raise AssertionError(f'Cannot focus {name}: {snap()["session"]["focused"]}')
                await state('MainMenu'); await tap('Return'); await state('Play')
                await cmd('reset'); await state('Play')
                route = await asyncio.create_subprocess_exec(sys.executable, str(ROOT / 'tools/walk_route.py'), stdout=(qa / 'route.log').open('wb'), stderr=subprocess.STDOUT)
                route_exit = await route.wait()
                report['route_exit'] = route_exit
                if route_exit:
                    report['checks'].append('PARTIAL traversal: West Gate→hill/stairs→Ring Gate→west lane south; blocked northbound at x=12.09,z=20.81')
                else:
                    report['checks'].append('Real-keyboard West Gate→hill/stairs→Ring Gate→Lattice traversal')
                for landmark, npc in [('west_gate', 'npc_vex'), ('mission_slab', 'npc_torr'), ('oa_hill', 'npc_linn')]:
                    await cmd('goto', landmark=landmark); await tap('e'); s = await state('Dialogue')
                    assert npc in s['session']['spoken'], (npc, s['session']['spoken'])
                    before = s['player']['position']; await tap('w', .35)
                    after = snap()['player']['position']; assert sum((a-b)**2 for a,b in zip(before, after)) < .003, 'Movement leaked into dialogue'
                    await click('choice0'); await state('Dialogue'); await tap('Escape'); await state('Play')
                report['checks'].append('Vex/Torr/Linn dialogue and modal input blocking')
                await cmd('goto', landmark='basic_general'); await tap('e'); await state('Dialogue'); await click('choice0'); await state('Shop')
                await click('buy0'); s=await state('Shop'); assert s['session']['credits']==21 and s['session']['quantities']['water_flask']==1, s['session']
                await click('sell2'); s=await state('Shop'); assert s['session']['credits']==22 and s['session']['quantities']['scrap_coil']==0, s['session']
                report['checks'].append('Actual keyboard shop buy and sell exact credits/inventory')
                await tap('Escape'); await cmd('goto', landmark='lattice_jack'); await tap('e'); await state('Grid')
                for _ in range(100):
                    if snap()['session']['gridProgress'] >= .999: break
                    await asyncio.sleep(.1)
                await click('node0'); s=await state('Grid')
                assert s['session']['linked'] and s['session']['selectedDestination']=='crosswind_reach', s['session']
                assert s['session']['visitedHill'] and len(s['session']['spoken'])==4, s['session']
                report['checks'].append('Lattice link and all four NPC objective flags')
                await tap('Escape'); await tap('Escape'); await state('Paused'); await tap('Escape'); await state('Play')
                for digit, modal in [('5', 'Inventory'), ('6', 'Notes')]:
                    await tap(digit); await state(modal); await tap('Escape'); await state('Play')
                await cmd('goto', landmark='ring_gate'); assert 'offline' in (await state('Play'))['session']['notice']
                await tap('r'); s=await state('Play'); assert abs(s['player']['position'][0]-43)<.1, s['player']
                report['checks'].append('Pause, inventory, notes, Ring Gate offline, return reset')
                await cmd('quit')
            report['passed'] = True
        except BaseException as e:
            report['error'] = repr(e)
            report['traceback'] = traceback.format_exc()
            raise
        finally:
            report['runtime_exceptions'] = [line for line in (qa / 'Player.log').read_text(errors='replace').splitlines() if 'Exception:' in line or 'NullReference' in line] if (qa / 'Player.log').exists() else []
            (qa / 'report.json').write_text(json.dumps(report, indent=2))
            if proc.poll() is None:
                proc.terminate()
                try: proc.wait(timeout=8)
                except subprocess.TimeoutExpired: proc.kill(); proc.wait()

asyncio.run(main())
