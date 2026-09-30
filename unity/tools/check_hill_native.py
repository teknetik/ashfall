"""Real-input native check of the rebuilt hill, tree ring, terminals and Vanguard Hall floodlights (30 Sep 2026).

  uv run --offline --with python-xlib --with pillow python unity/tools/check_hill_native.py OUT [--exe PATH]

Launches the development player (lookbook.launch), starts play and walks with real X11 W presses (camera yaw set through
the development bridge each step): West Gate -> the +X ("west") stair -> landing -> round the apron -> Linn (E, choice,
Escape) -> down and up the south stair -> terminal 02 and 01 stepping stones -> down the north stair. Expected blocks:
the tree ring (from the apron towards the trunk), a stair cheek wall (sideways off the north flight) and terminal 00's
body. Heights are checked on each stair and on the hilltop. A frame-timing profile covers the walk (12:00). First-person
stills at 12:00, 17:00 and 20:30: ring and uplights, a terminal, the beds, the hall facade and floodlights.
Writes hill-native.json and PNGs into OUT; raises on a failed check.
"""
import argparse, asyncio, json, math, os, sys, time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
from lookbook import launch, start_play, Run, summarize, ROOT  # noqa: E402

RING_R = 3.35 + 0.35   # ring collider outer radius + player capsule radius


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out', type=Path)
    ap.add_argument('--exe', type=Path, default=ROOT / 'unity/AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64')
    a = ap.parse_args()
    out = a.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    player = launch(out, a.exe); run = Run(out)
    rec = dict(utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), exe=str(a.exe), legs={}, blocks={}, stops={}, stills=[], checks=[])
    from desktop_input import focus, key
    try:
        await start_play(run, player)
        d = focus()

        def snap():
            for _ in range(20):
                try: return run.read('snapshot.json')
                except (json.JSONDecodeError, FileNotFoundError): time.sleep(.05)
            raise RuntimeError('snapshot unreadable')

        async def tap(name, seconds=.1, settle=.35):
            key(d, name, True)
            try: await asyncio.sleep(seconds)
            finally: key(d, name, False)
            await asyncio.sleep(settle)

        async def walk_to(name, target, tol=.3, limit=70, expect_block=False):
            started = time.monotonic(); last = 999; stalls = 0; ys = []
            while True:
                p = snap()['player']['position']; ys.append(p[1]); dx = target[0] - p[0]; dz = target[2] - p[2]; dist = math.hypot(dx, dz)
                if dist < tol:
                    r = dict(reached=True, position=p, minY=min(ys), maxY=max(ys), seconds=round(time.monotonic() - started, 1))
                    r['heightOk'] = abs(p[1] - target[1]) < (.28 if 'stair' in name else .15)   # the capsule can straddle a riser
                    if expect_block: raise RuntimeError('NOT BLOCKED on the way to %s: reached %s' % (name, p))
                    if not r['heightOk']: raise RuntimeError('height at %s: %s (expected %.2f)' % (name, p, target[1]))
                    rec['legs'][name] = r; print(name, r, flush=True); return r
                if time.monotonic() - started > limit: raise RuntimeError('timeout walking to %s %s at %s' % (name, target, p))
                stalls = stalls + 1 if abs(last - dist) < .01 else 0
                if stalls >= 6:
                    if expect_block:
                        r = dict(blocked=True, position=p, remaining=round(dist, 3)); rec['blocks'][name] = r; print(name, r, flush=True); return r
                    raise RuntimeError('BLOCKED before %s %s at %s' % (name, target, p))
                last = dist
                await run.command({'action': 'cameraYaw', 'yaw': math.degrees(math.atan2(dx, dz))}); await asyncio.sleep(.06)
                key(d, 'w', True)
                try: await asyncio.sleep(min(1.6, max(.025, (dist - .1) / 3.4)))
                finally: key(d, 'w', False)
                await asyncio.sleep(.08)

        async def route(legs):
            for name, target in legs:
                await walk_to(name, target)

        async def focus_and_press(name):
            for _ in range(40):
                if snap()['session']['focused'] == name: await tap('Return'); return
                await tap('Tab', settle=.2)
            raise RuntimeError('could not keyboard-focus ' + name)

        async def still(name, yaw, pitch, hours=(12, 17, 20.5), boom=0):
            await run.command({'action': 'cameraBoom', 'boom': boom}); await run.command({'action': 'cameraYaw', 'yaw': yaw})
            await run.command({'action': 'cameraPitch', 'pitch': pitch})
            for h in hours:
                await run.command({'action': 'timeSet', 'hour': h}); await run.command({'action': 'timePause', 'paused': True})
                await asyncio.sleep(2.2)
                n = 'fp_%s-h%05.2f' % (name, h)
                rec['stills'].append(await run.capture(n))
            await run.command({'action': 'timeSet', 'hour': 12}); await run.command({'action': 'cameraBoom', 'boom': 4})
            await run.command({'action': 'cameraPitch', 'pitch': 12}); await asyncio.sleep(.8)

        await run.command({'action': 'timeSet', 'hour': 12}); await run.command({'action': 'timePause', 'paused': True})
        await run.command({'action': 'view', 'camera': 'follow'}); await run.command({'action': 'cameraBoom', 'boom': 4})
        await run.command({'action': 'reset'}); await asyncio.sleep(1)
        rec['start'] = snap()['player']['position']

        # ---- walk in from the gate and up the +X stair (profiled)
        await run.command({'action': 'profileStart'})
        await route([('avenue', (14, 0, 0.3)), ('west_stair_foot', (11.2, 0, 0.3)), ('west_stair_mid', (9.1, .75, 0.3)),
                     ('west_landing', (6.3, 1.5, 0.3)), ('apron_east', (4.25, 1.5, 0.6)), ('apron_ne', (2.97, 1.5, 2.97)),
                     ('apron_south', (0.7, 1.5, 4.2)), ('linn_stone', (2.35, 1.5, 3.95))])
        await run.command({'action': 'profileStop'}); await asyncio.sleep(.3)
        rec['walkProfile'] = summarize(run.read('profile.json'))
        # ---- Linn
        s = snap(); prompt = s.get('interaction', {}).get('prompt', '')
        assert 'Talk to Linn' in prompt, 'Linn prompt: %r' % prompt
        await tap('e'); s = snap(); assert s['session']['state'] == 'Dialogue', s['session']
        before = s['player']['position']; await tap('w', .4); moved = math.dist(before, snap()['player']['position'])
        assert moved < .04, 'modal movement leak %.3f' % moved
        await focus_and_press('choice0'); await tap('Escape')
        if snap()['session']['state'] != 'Play': await tap('Escape')
        assert snap()['session']['state'] == 'Play'
        rec['stops']['linn'] = dict(prompt=prompt, modalMoveM=round(moved, 4), visitedHill=snap()['session'].get('visitedHill'))
        # ---- ring blocks the player (apron -> trunk)
        await route([('apron_south_2', (0.0, 1.5, 4.25))])
        r = await walk_to('into_ring_from_south', (0.0, 1.5, 0.5), expect_block=True)
        rad = math.hypot(r['position'][0], r['position'][2])
        rec['checks'].append(dict(check='ring blocks at the wall', radius=round(rad, 3), expected=RING_R, ok=abs(rad - RING_R) < .25 and abs(r['position'][1] - 1.5) < .1))
        # ---- south stair down and up
        await route([('south_path', (0.3, 1.5, 5.9)), ('south_stair_mid', (0.3, .75, 9.1)), ('south_stair_foot', (0.3, 0, 11.3)),
                     ('south_stair_up_mid', (-0.3, 1.0, 8.5)), ('south_landing', (-0.3, 1.5, 6.3))])
        # ---- terminal 02 (-5, 1) and its stepping stones, terminal 01 (-5, -4)
        await route([('apron_sw', (-2.97, 1.5, 2.97)), ('apron_t02', (-4.12, 1.5, 0.82)), ('t02_front', (-4.2, 1.5, 0.84))])
        await still('terminal02', math.degrees(math.atan2(-0.8, 0.16)), 4, hours=(12, 20.5))
        await route([('apron_west', (-4.2, 1.5, -0.6)), ('apron_t01', (-3.3, 1.5, -2.62)), ('t01_stones', (-3.9, 1.5, -3.1))])
        r = await walk_to('into_terminal01', (-5.0, 1.6, -4.0), expect_block=True)
        rec['checks'].append(dict(check='terminal 01 body blocks', position=r['position'], ok=math.dist((r['position'][0], r['position'][2]), (-5.0, -4.0)) > .7))
        # ---- north stair: cheek wall blocks a sideways step, then down
        await route([('apron_nw', (-2.97, 1.5, -2.97)), ('apron_north', (-0.3, 1.5, -4.25)), ('north_path', (0.3, 1.5, -5.9)),
                     ('north_stair_mid', (1.4, .75, -9.1))])
        r = await walk_to('off_north_stair_side', (3.6, 0.0, -9.1), expect_block=True)
        rec['checks'].append(dict(check='north stair cheek blocks', x=r['position'][0], ok=r['position'][0] < 1.8))
        await route([('north_stair_foot', (0.3, 0, -11.3))])
        # ---- ring still from the south, beds, hall facade and floodlights
        await route([('north_stair_back_up', (0.3, 1.0, -8.5)), ('north_landing_2', (0.3, 1.5, -6.2)), ('apron_ne_2', (2.97, 1.5, -2.97)),
                     ('apron_e_2', (4.25, 1.5, 0.3)), ('apron_se_2', (2.97, 1.5, 2.97)), ('ring_view_point', (1.0, 1.5, 5.6))])
        await still('ring_south', math.degrees(math.atan2(-1.0, -5.6)), 6)
        await still('uplit_crown', math.degrees(math.atan2(-1.0, -5.6)), -32, hours=(20.5,))
        await route([('bed_view_point', (-1.0, 1.5, 5.9))])
        await still('beds_west', math.degrees(math.atan2(-4.0, -3.5)), 14, hours=(12, 17))
        await route([('south_path_2', (0.3, 1.5, 6.2)), ('apron_s_3', (0.3, 1.5, 4.25)), ('apron_w_3', (-4.25, 1.5, 0.0)), ('apron_n_3', (0.0, 1.5, -4.25)),
                     ('north_path_3', (0.3, 1.5, -6.2)), ('north_stair_foot_2', (0.3, 0, -11.3)), ('plaza_hall', (-7.0, 0, -15.5)),
                     ('hall_view_point', (-10.0, 0, -17.0))])
        await still('hall_floodlights', 180.0, -14, hours=(12, 17, 20.5))
        await route([('hall_terrace_front', (-7.4, 0.25, -23.6))])
        await still('floodlight_close', math.degrees(math.atan2(-5.8, -1.6)), 10, hours=(12, 20.5))
        rec['final'] = snap()['session'].get('objective')
        rec['ok'] = all(c['ok'] for c in rec['checks'])
        await run.command({'action': 'quit'}, timeout=5)
    finally:
        try: player.wait(timeout=10)
        except Exception:
            try: os.killpg(player.pid, 15)
            except Exception: pass
        try:
            d = focus()
            for k in ['w', 'a', 's', 'd', 'e', 'Return', 'Escape', 'Tab', 'Shift_L']: key(d, k, False)
        except Exception: pass
        (out / 'hill-native.json').write_text(json.dumps(rec, indent=1))
    print(json.dumps(dict(ok=rec.get('ok'), checks=rec['checks'], blocks=rec['blocks'], walk=rec.get('walkProfile')), indent=1))
    if not rec.get('ok'): raise SystemExit('HILL CHECK FAILED')
    print('HILL CHECK PASS')


if __name__ == '__main__':
    asyncio.run(main())
