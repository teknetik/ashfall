"""Real-input native check of the north avenue rebuild: Salvage, Repairs, Thread + Hide, Basic General (30 Sep 2026).

  uv run --offline --with python-xlib --with pillow python unity/tools/check_north_avenue_native.py OUT [--exe PATH]

Launches the development player (lookbook.launch), starts play and walks with real X11 W presses (camera yaw set through
the development bridge each step; E, Tab, Return, Escape are real key events). The whole city loop is kept: Vex at the
gate, Torr, Linn on the hill, Mira at the rebuilt Basic General (between its new stone piers) with a flask purchase and a
scrap sale, the rebuilt hall-district porches, and Lattice travel. New legs: onto each north avenue porch and into each new
door recess (Thread + Hide display and door, Repairs bay and door, Salvage shutter and door), across the cross street
past Repairs' south side and down the avenue. A frame-timing profile covers the north avenue legs (12:00). First-person
stills at 12:00, 17:00 and 20:30 (Basic General approach and counter, Thread + Hide balcony, Repairs from the cross street,
Salvage, the avenue from its north end). Writes north-native.json and PNGs into OUT; raises on a failed check or a stall.
"""
import argparse, asyncio, json, math, os, sys, time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
from lookbook import launch, start_play, Run, summarize, ROOT  # noqa: E402

ROUTES = {
    'torr': [('avenue_west_stair', (12, 0, 0)), ('avenue_mid_south', (12.6, 0, -6.5)), ('torr_approach', (10.6, 0, -10.6))],
    'linn': [('avenue_west_stair_2', (12, 0, 0)), ('hill_tree', (4, 1.5, 0)), ('linn_approach', (3.6, 1.5, 3.2))],
    'mira': [('hill_southwest', (4, 1.5, 4)), ('south_stair_top', (0, 1.5, 4)), ('south_stair_bottom', (0, 0, 12)),
             ('general_clear_lane', (0, 0, 21)), ('general_front_lane', (8, 0, 21)), ('general_approach', (8, 0, 19)),
             ('general_porch', (8, .5, 16.8))],
    # the kept salvage props (generator scatter 48 at (12, 20), crate scatter 49 at (13.65, 21.3)) are passed on their south side
    'east_north': [('general_back_off', (8, 0, 20.5)), ('lane_east_south', (11.0, 0, 18.6)), ('thread_step', (13.1, 0, 18.0)),
                   ('thread_porch', (15.2, .5, 18.0)), ('thread_display', (16.9, .5, 16.4)), ('thread_door_recess', (18.2, .5, 19.25)),
                   ('thread_off', (12.9, 0, 19.3)), ('east_lane_mid', (12.6, 0, 13.0)), ('repairs_step', (13.1, 0, 9.0)),
                   ('repairs_porch', (15.2, .5, 9.0)), ('repairs_bay', (17.3, .5, 7.6)), ('repairs_door_recess', (18.2, .5, 10.95)),
                   ('repairs_off', (12.9, 0, 10.9)), ('cross_south', (12.6, 0, 4.0))],
    'back_north': [('east_lane_back', (12.6, 0, 13.0)), ('thread_view_point', (12.4, 0, 18.3))],
    'to_west': [('lane_east_south_2', (11.0, 0, 18.6)), ('general_front_lane_2', (8, 0, 20.8)), ('avenue_north_end', (0, 0, 22))],
    'west_north': [('lane_west_north', (-6, 0, 20.5)), ('salvage_lane', (-12.6, 0, 20.8)), ('salvage_step', (-13.1, 0, 18.0)),
                   ('salvage_porch', (-15.2, .5, 18.0)), ('salvage_shutter', (-17.3, .5, 19.35)), ('salvage_door_recess', (-18.2, .5, 16.05)),
                   ('salvage_off', (-12.8, 0, 16.0)), ('salvage_view', (-11.5, 0, 17.0))],
    'west_row': [('east_row_lane', (-12.8, 0, 13.5)), ('tool_exchange_step', (-13.1, 0, 9.5)), ('tool_exchange_display', (-16.9, .5, 10.4)),
                 ('tool_exchange_door_recess', (-18.2, .5, 7.45)), ('tool_exchange_off', (-12.8, 0, 7.5)),
                 ('east_lane_south', (-12.8, 0, -4.5)), ('air_water_step', (-13.1, 0, -9.0)),
                 ('air_water_door_recess', (-18.2, .5, -10.35)), ('air_water_off', (-12.8, 0, -10.35)),
                 ('relay_step', (-13.1, 0, -18.0)), ('relay_porch_shutter', (-16.9, .5, -17.3)), ('relay_off', (-12.8, 0, -20.0))],
    'lattice': [('plaza_west', (-6, 0, -22)), ('hall_front_step', (-10, .25, -23.9)), ('hall_terrace', (-10, .5, -25.3)),
                # 3 Oct 2026: one Lattice Jack, the Meshy ring in the north court (the old Jack behind the hall is retired)
                ('hall_back_off', (-12.8, 0, -20.0)), ('east_lane_north', (-12.8, 0, 13.5)), ('lane_west_2', (-6, 0, 20.5)),
                ('ring_clear_lane', (0, 0, 21)), ('ring_plaza', (0, 0, 28)), ('lattice_ring_step', (0, .25, 32.8))],
}


def yaw_to(frm, to):
    return math.degrees(math.atan2(to[0] - frm[0], to[2] - frm[2]))


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out', type=Path)
    ap.add_argument('--exe', type=Path, default=ROOT / 'unity/AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64')
    ap.add_argument('--no-stills', action='store_true')
    a = ap.parse_args()
    out = a.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    player = launch(out, a.exe); run = Run(out)
    rec = dict(utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), exe=str(a.exe), legs={}, stops={}, stills=[], checks=[])
    from desktop_input import focus, key
    t0 = time.time()
    try:
        await start_play(run, player)
        d = focus()

        def snap():
            for _ in range(20):
                try: return run.read('snapshot.json')
                except (json.JSONDecodeError, FileNotFoundError): time.sleep(.05)
            raise RuntimeError('snapshot unreadable')

        def note(label):
            s = snap(); print(json.dumps(dict(label=label, t=round(time.time() - t0, 1), state=s['session']['state'], player=s['player']['position'],
                                               credits=s['session'].get('credits'))), flush=True)
            return s

        async def tap(name, seconds=.1, settle=.35):
            key(d, name, True)
            try: await asyncio.sleep(seconds)
            finally: key(d, name, False)
            await asyncio.sleep(settle)

        async def walk_to(name, target, tol=.3, limit=70):
            started = time.monotonic(); last = 999; stalls = 0; ys = []
            while True:
                p = snap()['player']['position']; ys.append(p[1]); dx = target[0] - p[0]; dz = target[2] - p[2]; dist = math.hypot(dx, dz)
                if dist < tol:
                    r = dict(reached=True, position=p, minY=min(ys), maxY=max(ys), seconds=round(time.monotonic() - started, 1))
                    r['heightOk'] = abs(p[1] - target[1]) < (.28 if 'stair' in name else .15)
                    if not r['heightOk']: raise RuntimeError('height at %s: %s (expected %.2f)' % (name, p, target[1]))
                    rec['legs'][name] = r; print(name, r, flush=True); return r
                if time.monotonic() - started > limit: raise RuntimeError('timeout walking to %s %s at %s' % (name, target, p))
                stalls = stalls + 1 if abs(last - dist) < .01 else 0
                if stalls >= 6: raise RuntimeError('BLOCKED before %s %s at %s' % (name, target, p))
                last = dist
                await run.command({'action': 'cameraYaw', 'yaw': math.degrees(math.atan2(dx, dz))}); await asyncio.sleep(.06)
                key(d, 'w', True)
                try: await asyncio.sleep(min(1.6, max(.025, (dist - .1) / 3.4)))
                finally: key(d, 'w', False)
                await asyncio.sleep(.08)

        async def route(k):
            for name, target in ROUTES[k]:
                await walk_to(name, target)

        async def focus_and_press(name):
            for _ in range(40):
                if snap()['session']['focused'] == name: await tap('Return'); return
                await tap('Tab', settle=.2)
            raise RuntimeError('could not keyboard-focus ' + name)

        async def still(name, yaw, pitch, hours=(12, 17, 20.5), boom=0):
            if a.no_stills: return
            await run.command({'action': 'cameraBoom', 'boom': boom}); await run.command({'action': 'cameraYaw', 'yaw': yaw})
            await run.command({'action': 'cameraPitch', 'pitch': pitch})
            for h in hours:
                await run.command({'action': 'timeSet', 'hour': h}); await run.command({'action': 'timePause', 'paused': True})
                await asyncio.sleep(2.2)
                rec['stills'].append(await run.capture('fp_%s-h%05.2f' % (name, h)))
            await run.command({'action': 'timeSet', 'hour': 12}); await run.command({'action': 'cameraBoom', 'boom': 4})
            await run.command({'action': 'cameraPitch', 'pitch': 12}); await asyncio.sleep(.8)

        async def talk(npc, who):
            s = note('before ' + npc); prompt = s.get('interaction', {}).get('prompt', '')
            assert ('Talk to ' + who) in prompt, 'prompt for %s: %r' % (who, prompt)
            await tap('e'); s = note('E ' + npc); assert s['session']['state'] == 'Dialogue', s['session']
            before = s['player']['position']; await tap('w', .4); moved = math.dist(before, snap()['player']['position'])
            assert moved < .04, 'modal movement leak %.3f' % moved
            await focus_and_press('choice0'); s = note('choice0 ' + npc)
            return dict(prompt=prompt, afterChoice=s['session']['state'], modalMoveM=round(moved, 4)), s

        async def close_modal():
            await tap('Escape'); await asyncio.sleep(.3)
            if snap()['session']['state'] != 'Play': await tap('Escape')
            assert snap()['session']['state'] == 'Play', snap()['session']

        await run.command({'action': 'timeSet', 'hour': 12}); await run.command({'action': 'timePause', 'paused': True})
        await run.command({'action': 'view', 'camera': 'follow'}); await run.command({'action': 'cameraBoom', 'boom': 4})
        await run.command({'action': 'reset'}); await asyncio.sleep(1)
        s0 = note('start'); rec['start'] = dict(credits=s0['session']['credits'], quantities=s0['session']['quantities'])

        rec['stops']['vex'], s = await talk('npc_vex', 'Vex'); await close_modal()
        await route('torr'); rec['stops']['torr'], s = await talk('npc_torr', 'Torr'); await close_modal()
        await route('linn'); rec['stops']['linn'], s = await talk('npc_linn', 'Linn'); await close_modal()
        # ---- Basic General: approach between the new piers, trade with Mira
        await route('mira')
        stop, s = await talk('npc_mira', 'Mira')
        assert s['session']['state'] == 'Shop', 'Mira choice0 should open the shop: %s' % s['session']['state']
        before = dict(credits=s['session']['credits'], q=dict(s['session']['quantities']))
        await run.capture('shop_open')
        await focus_and_press('buy0'); s = note('buy0')
        after_buy = dict(credits=s['session']['credits'], q=dict(s['session']['quantities']))
        assert after_buy['q'].get('water_flask', 0) == before['q'].get('water_flask', 0) + 1, (before, after_buy)
        assert after_buy['credits'] < before['credits'], (before, after_buy)
        await focus_and_press('sell2'); s = note('sell2')
        after_sell = dict(credits=s['session']['credits'], q=dict(s['session']['quantities']))
        assert after_sell['q'].get('scrap_coil', 0) == after_buy['q'].get('scrap_coil', 0) - 1, (after_buy, after_sell)
        assert after_sell['credits'] > after_buy['credits'], (after_buy, after_sell)
        stop.update(before=before, afterBuy=after_buy, afterSell=after_sell)
        rec['stops']['mira'] = stop
        await close_modal()
        await still('bg_counter', 180.0, -4)
        await walk_to('bg_view_point', (8, 0, 21.2))
        await still('bg_approach', 180.0, 5)
        # ---- north avenue legs (profiled at 12:00)
        await run.command({'action': 'profileStart'})
        await route('east_north')
        await run.command({'action': 'profileStop'}); await asyncio.sleep(.3)
        rec['walkProfile'] = summarize(run.read('profile.json'))
        await still('repairs_south', yaw_to((12.6, 0, 4.0), (18.1, 0, 8.0)), -8)
        await route('back_north')
        await still('thread_balcony', 90.0, -20)
        await route('to_west')
        await still('avenue_north_end', 180.0, 4)
        await route('west_north')
        await still('salvage_front', -90.0, -14)
        # ---- the rest of the loop: hall-district west row, Lattice
        await route('west_row')
        await route('lattice')
        s = note('at lattice'); lat_prompt = s.get('interaction', {}).get('prompt', '')
        await tap('e'); s = note('E lattice'); assert s['session']['state'] == 'Grid', s['session']
        for _ in range(120):
            if snap()['session'].get('gridProgress', 0) >= .999: break
            await asyncio.sleep(.1)
        assert snap()['session']['gridProgress'] >= .999, 'lattice never became ready'
        await focus_and_press('node0'); s = note('node0')
        assert s['session']['linked'], s['session']
        rec['stops']['lattice'] = dict(prompt=lat_prompt, selectedDestination=s['session'].get('selectedDestination'), linked=s['session']['linked'])
        await close_modal()
        s = note('end')
        rec['final'] = dict(state=s['session']['state'], spoken=s['session']['spoken'], boughtFlask=s['session'].get('boughtFlask'),
                            soldScrap=s['session'].get('soldScrap'), linked=s['session'].get('linked'), visitedHill=s['session'].get('visitedHill'),
                            objective=s['session'].get('objective'), credits=s['session']['credits'], quantities=s['session']['quantities'])
        rec['checks'].append(dict(check='four conversations', ok=set(['npc_vex', 'npc_torr', 'npc_linn', 'npc_mira']) <= set(s['session']['spoken'])))
        rec['checks'].append(dict(check='every leg reached at the right height', ok=all(l.get('heightOk') for l in rec['legs'].values()), legs=len(rec['legs'])))
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
        (out / 'north-native.json').write_text(json.dumps(rec, indent=1))
    print(json.dumps(dict(ok=rec.get('ok'), checks=rec['checks'], walk=rec.get('walkProfile')), indent=1))
    if not rec.get('ok'): raise SystemExit('NORTH AVENUE CHECK FAILED')
    print('NORTH AVENUE CHECK PASS')


if __name__ == '__main__':
    asyncio.run(main())
