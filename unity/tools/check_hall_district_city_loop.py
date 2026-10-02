"""Real-input city loop over the rebuilt hall district (merchant update: 2 Oct 2026).

  unity/tools/run_native.sh <native-dir> check_hall_district_city_loop.py

Attaches only to the existing QA player identified by <native-dir>/pid; never launches or stops a player.

Carl asked for the rest of the loop to be re-checked after the Vanguard Hall rebuild (only Vex had been): Mira, Torr and
Linn, trading at Basic General and Lattice travel. Everything here is walked with real X11 W presses (camera yaw set
through the development bridge each step); E, Tab, Return and Escape are real key events. Bridge commands only read state or set
view/camera/reset/time/resolution/capture. Per stop: prompt, E -> Dialogue, movement blocked while modal, first choice, Escape.
Basic General: E -> Dialogue -> choice0 -> Shop; use merchant tabs/filters, arrow-select a water flask and a scrap coil,
then Tab to the explicit trade action. Exact credit and inventory deltas are asserted. The route also steps onto the rebuilt Field Supply, Air + Water, Relay Works and Tool Exchange
porches and into two door recesses (collision/access check). Lattice: E -> Grid, wait for the link, node0 -> linked.
Writes city-loop.json (+ captures) into the native dir; raises on any failed check or a stall (6 steps without progress).
"""
import asyncio, json, math, os, time
from pathlib import Path
from native_client import Client, select_merchant_item
from desktop_input import focus, focus_window, key
from Xlib import X

OUT = Path(os.environ['ATHEN_NATIVE_DIR'])


def snap():
    for _ in range(20):
        try: return json.loads((OUT / 'snapshot.json').read_text())
        except (json.JSONDecodeError, FileNotFoundError): time.sleep(.05)
    raise RuntimeError('snapshot unreadable')


ROUTES = {
    'torr': [('avenue_west_stair', (12, 0, 0)), ('avenue_mid_south', (12.6, 0, -6.5)), ('torr_approach', (10.6, 0, -10.6))],
    'field_supply_porch': [('field_supply_step', (13.1, 0, -9.0)), ('field_supply_porch', (15.2, .5, -9.0)),
                           ('field_supply_door_recess', (17.9, .5, -11.2)), ('field_supply_back_out', (13.0, 0, -11.2))],
    'linn': [('avenue_west_stair_2', (12, 0, 0)), ('hill_tree', (4, 1.5, 0)), ('linn_approach', (3.6, 1.5, 3.2))],
    'mira': [('hill_southwest', (4, 1.5, 4)), ('south_stair_top', (0, 1.5, 4)), ('south_stair_bottom', (0, 0, 12)),
             ('general_clear_lane', (0, 0, 21)), ('general_front_lane', (8, 0, 21)), ('general_approach', (8, 0, 19)),
             ('general_porch', (8, .5, 16.8))],
    'west_row': [('general_back_off', (8, 0, 20.5)), ('lane_west', (-6, 0, 20.5)), ('east_row_lane', (-12.8, 0, 13.5)),
                 ('tool_exchange_step', (-13.1, 0, 9.5)), ('tool_exchange_display', (-16.9, .5, 10.4)),
                 ('tool_exchange_door_recess', (-18.2, .5, 7.45)), ('tool_exchange_off', (-12.8, 0, 7.5)),
                 ('east_lane_south', (-12.8, 0, -4.5)), ('air_water_step', (-13.1, 0, -9.0)),
                 ('air_water_door_recess', (-18.2, .5, -10.35)), ('air_water_off', (-12.8, 0, -10.35)),
                 ('relay_step', (-13.1, 0, -18.0)), ('relay_porch_shutter', (-16.9, .5, -17.3)), ('relay_off', (-12.8, 0, -20.0))],
    'lattice': [('plaza_west', (-6, 0, -22)), ('hall_front_step', (-10, .25, -23.9)), ('hall_terrace', (-10, .5, -25.3)),
                ('plaza_back', (-4, 0, -23)), ('lattice_step', (0, .25, -33.6)), ('lattice_pad', (0, .5, -36.0))],
}


async def main():
    d = focus(); c = Client(); log = []; t0 = time.time(); rec = dict(utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), legs={}, stops={})

    async def tap(name, seconds=.1, settle=.35):
        # Match the inventory harness: input always targets this run's exact PID.
        nonlocal d
        d, window = focus_window()
        window.set_input_focus(X.RevertToParent, X.CurrentTime)
        d.sync()
        key(d, name, True)
        try: await asyncio.sleep(seconds)
        finally: key(d, name, False)
        await asyncio.sleep(settle)

    def note(label, **extra):
        s = snap(); e = dict(label=label, t=round(time.time() - t0, 2), state=s['session']['state'], player=s['player']['position'],
                             credits=s['session'].get('credits'), prompt=s.get('interaction', {}).get('prompt'), **extra)
        log.append(e); print(json.dumps(e), flush=True); return s

    async def walk_to(name, target, tol=.3, limit=60):
        started = time.monotonic(); last = 999; stalls = 0; ys = []
        while True:
            p = snap()['player']['position']; ys.append(p[1]); dx = target[0] - p[0]; dz = target[2] - p[2]; dist = math.hypot(dx, dz)
            if dist < tol:
                r = dict(reached=True, position=p, minY=min(ys), maxY=max(ys), seconds=round(time.monotonic() - started, 1))
                if len(target) > 1: r['heightOk'] = abs(p[1] - target[1]) < .15
                rec['legs'][name] = r; return r
            if time.monotonic() - started > limit: raise RuntimeError('timeout walking to %s %s at %s' % (name, target, p))
            stalls = stalls + 1 if abs(last - dist) < .01 else 0
            if stalls >= 6: raise RuntimeError('BLOCKED before %s %s at %s' % (name, target, p))
            last = dist
            await c.command({'action': 'cameraYaw', 'yaw': math.degrees(math.atan2(dx, dz))}); await asyncio.sleep(.06)
            key(d, 'w', True)
            try: await asyncio.sleep(min(1.6, max(.025, (dist - .1) / 3.4)))
            finally: key(d, 'w', False)
            await asyncio.sleep(.08)

    async def route(key_):
        for name, target in ROUTES[key_]:
            await walk_to(name, target); note('walked ' + name)

    focus_trace = []

    async def focus_and_press(name):
        for attempt in range(40):
            current = await c.snapshot()
            focused = current['session']['focused']
            focus_trace.append(dict(target=name, attempt=attempt, frame=current['frame'], focused=focused))
            (OUT / 'city-loop-focus.json').write_text(json.dumps(focus_trace, indent=1))
            if focused == name:
                await tap('Return')
                return
            await tap('Tab', settle=.2)
        raise RuntimeError('could not keyboard-focus %s; observed %s' % (name, [x['focused'] for x in focus_trace[-40:]]))

    async def capture(name):
        await c.command({'action': 'capture', 'name': name}); await asyncio.sleep(1.0)

    async def talk(npc, who):
        s = note('before ' + npc); prompt = s.get('interaction', {}).get('prompt', '')
        assert ('Talk to ' + who) in prompt, 'prompt for %s: %r' % (who, prompt)
        await tap('e'); s = note('E ' + npc); assert s['session']['state'] == 'Dialogue', s['session']
        assert npc in s['session']['spoken'], s['session']['spoken']
        before = s['player']['position']; await tap('w', .4); moved = math.dist(before, snap()['player']['position'])
        assert moved < .04, 'modal movement leak %.3f' % moved
        await capture('dialogue_' + npc)
        await focus_and_press('choice0'); s = note('choice0 ' + npc)
        stop = dict(prompt=prompt, afterChoice=s['session']['state'], modalMoveM=round(moved, 4))
        return stop, s

    # ---------------------------------------------------------------- start
    if snap()['session']['state'] == 'MainMenu':
        for _ in range(8):
            await tap('Return', .12, 1.5)
            if snap()['session']['state'] != 'MainMenu': break
    for _ in range(100):
        if snap()['session']['state'] == 'Play': break
        await asyncio.sleep(.1)
    assert snap()['session']['state'] == 'Play', snap()['session']
    await c.command({'action': 'resize', 'width': 1920, 'height': 1080}); await asyncio.sleep(1.5)
    await c.command({'action': 'timeReset'}); await c.command({'action': 'timePause', 'paused': True})
    await c.command({'action': 'view', 'camera': 'follow'}); await c.command({'action': 'cameraBoom', 'boom': 4}); await c.command({'action': 'reset'}); await asyncio.sleep(1)
    s0 = note('start'); rec['start'] = dict(credits=s0['session']['credits'], quantities=s0['session']['quantities'])

    # Vex at the gate
    rec['stops']['vex'], s = await talk('npc_vex', 'Vex'); await tap('Escape'); assert snap()['session']['state'] == 'Play'
    # Torr at the mission slab
    await route('torr')
    rec['stops']['torr'], s = await talk('npc_torr', 'Torr'); await tap('Escape'); assert snap()['session']['state'] == 'Play'
    # Field Supply porch and door recess (rebuilt shop access)
    await route('field_supply_porch'); await capture('field_supply_recess_leg')
    # Linn on the hill
    await route('linn')
    rec['stops']['linn'], s = await talk('npc_linn', 'Linn'); await tap('Escape'); assert snap()['session']['state'] == 'Play'
    # Mira, Basic General trade
    await route('mira')
    stop, s = await talk('npc_mira', 'Mira')
    assert s['session']['state'] == 'Shop', 'Mira choice0 should open the shop: %s' % s['session']['state']
    before = dict(credits=s['session']['credits'], q=dict(s['session']['quantities']))
    await capture('shop_open')
    await focus_and_press('merchant-tab-buy')
    await focus_and_press('merchant-filter-supplies')
    await select_merchant_item(c, 'water_flask', tap)
    await focus_and_press('merchant-trade'); s = note('buy water flask')
    after_buy = dict(credits=s['session']['credits'], q=dict(s['session']['quantities']))
    assert after_buy['q'].get('water_flask', 0) == before['q'].get('water_flask', 0) + 1, (before, after_buy)
    assert after_buy['credits'] == before['credits'] - 4, (before, after_buy)
    assert after_buy['q'] == dict(before['q'], water_flask=before['q'].get('water_flask', 0) + 1), (before, after_buy)
    await focus_and_press('merchant-tab-sell')
    await focus_and_press('merchant-filter-all')
    await select_merchant_item(c, 'scrap_coil', tap)
    await focus_and_press('merchant-trade'); s = note('sell scrap coil')
    after_sell = dict(credits=s['session']['credits'], q=dict(s['session']['quantities']))
    assert after_sell['q'].get('scrap_coil', 0) == after_buy['q'].get('scrap_coil', 0) - 1, (after_buy, after_sell)
    assert after_sell['credits'] == after_buy['credits'] + 1, (after_buy, after_sell)
    assert after_sell['q'] == dict(after_buy['q'], scrap_coil=after_buy['q'].get('scrap_coil', 0) - 1), (after_buy, after_sell)
    assert s['session']['boughtFlask'] and s['session']['soldScrap'], s['session']
    await capture('shop_after_trade')
    stop.update(before=before, afterBuy=after_buy, afterSell=after_sell, boughtFlask=s['session'].get('boughtFlask'), soldScrap=s['session'].get('soldScrap'))
    rec['stops']['mira'] = stop
    await tap('Escape'); await asyncio.sleep(.3)
    if snap()['session']['state'] != 'Play': await tap('Escape')
    assert snap()['session']['state'] == 'Play', snap()['session']
    await capture('basic_general_sign_after_trade')
    # West row: Tool Exchange display and door, Air + Water door, Relay Works porch
    await route('west_row'); await capture('relay_leg')
    # Lattice travel
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
    await capture('lattice_linked')
    await tap('Escape'); await asyncio.sleep(.3)
    if snap()['session']['state'] != 'Play': await tap('Escape')
    s = note('end')
    rec['final'] = dict(state=s['session']['state'], spoken=s['session']['spoken'], boughtFlask=s['session'].get('boughtFlask'),
                        soldScrap=s['session'].get('soldScrap'), linked=s['session'].get('linked'), visitedHill=s['session'].get('visitedHill'),
                        objective=s['session'].get('objective'), credits=s['session']['credits'], quantities=s['session']['quantities'])
    assert set(['npc_vex', 'npc_torr', 'npc_linn', 'npc_mira']) <= set(s['session']['spoken']), s['session']['spoken']
    rec['complete'] = True; rec['log'] = log
    (OUT / 'city-loop.json').write_text(json.dumps(rec, indent=1)); print('CITY LOOP PASS', flush=True)

if __name__ == '__main__':
    if not os.environ.get('ATHEN_NATIVE_PID'):
        raise SystemExit('Run through unity/tools/run_native.sh with the existing QA run directory.')
    try:
        asyncio.run(main())
    finally:
        d = focus()
        for k in ['w', 'a', 's', 'd', 'e', 'Return', 'Escape', 'Tab', 'Shift_L']: key(d, k, False)
