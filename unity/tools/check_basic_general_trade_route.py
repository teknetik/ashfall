"""Real-input Basic General porch route: approach Mira on foot, E dialogue/shop, buy a water flask, sell scrap, close, walk away.

Uses the native development player (ATHEN_NATIVE_DIR / ATHEN_NATIVE_PID). Movement, E, Tab, Return and Escape are real X11 key events.
Only the start position is set with the bridge's goto; the approach to the porch is walked. Records every state and the credit/inventory deltas.
"""
import asyncio, json, math, os, time
from pathlib import Path
from native_client import Client
from desktop_input import focus, key

OUT = Path(os.environ['ATHEN_NATIVE_DIR'])
def snap(): return json.loads((OUT / 'snapshot.json').read_text())


async def main():
    d = focus(); c = Client(); log = []; t0 = time.time()
    async def tap(name, seconds=.1, settle=.3):
        key(d, name, True)
        try: await asyncio.sleep(seconds)
        finally: key(d, name, False)
        await asyncio.sleep(settle)
    def rec(label, **extra):
        s = snap(); e = dict(label=label, t=round(time.time() - t0, 2), state=s['session']['state'], player=s['player']['position'], credits=s['session']['credits'],
                             quantities=s['session']['quantities'], focused=s['session']['focused'], notice=s['session']['notice'], **extra); log.append(e); print(json.dumps(e), flush=True); return s
    async def walk_to(target, tol=.25, limit=40):
        started = time.monotonic(); last = 999; stalls = 0; path = []
        while True:
            p = snap()['player']['position']; path.append(p); dx = target[0] - p[0]; dz = target[2] - p[2]; dist = math.hypot(dx, dz)
            if dist < tol: return dict(reached=True, position=p, samples=len(path))
            if time.monotonic() - started > limit: raise RuntimeError('timeout %s at %s' % (target, p))
            stalls = stalls + 1 if abs(last - dist) < .01 else 0
            if stalls >= 6: raise RuntimeError('BLOCKED before %s at %s' % (target, p))
            last = dist
            await c.command({'action': 'cameraYaw', 'yaw': math.degrees(math.atan2(dx, dz))}); await asyncio.sleep(.08)
            key(d, 'w', True)
            try: await asyncio.sleep(min(2, max(.025, (dist - .1) / 3.4)))
            finally: key(d, 'w', False)
            await asyncio.sleep(.1)
    async def focus_and_press(name):
        for _ in range(40):
            if snap()['session']['focused'] == name: await tap('Return'); return
            await tap('Tab')
        raise RuntimeError('could not keyboard-focus ' + name)

    # start
    if snap()['session']['state'] == 'MainMenu':
        for _ in range(8):
            await tap('Return', .12, 1.5)
            if snap()['session']['state'] != 'MainMenu': break
    assert snap()['session']['state'] == 'Play'
    await c.command({'action': 'view', 'camera': 'follow'}); await c.command({'action': 'cameraBoom', 'boom': 4}); await c.command({'action': 'reset'}); await asyncio.sleep(.6)
    # Route: avenue lane -> front lane -> approach -> porch, all on foot (waypoints from the retained salvage route).
    steps = {}
    for name, target in [('west_stair_approach', (12, 0, 0)), ('hill_tree', (4, 1.5, 0)), ('hill_southwest', (4, 1.5, 4)), ('south_stair_top', (0, 1.5, 4)), ('south_stair_bottom', (0, 0, 12)), ('general_clear_lane', (0, 0, 21)), ('general_front_lane', (8, 0, 21)), ('general_approach', (8, 0, 19)), ('general_porch', (8, .5, 16.8))]:
        steps[name] = await walk_to(target, .3, 60); rec('walked ' + name)
    s = rec('porch before'); before = dict(credits=s['session']['credits'], q=dict(s['session']['quantities']))
    assert math.dist(s['player']['position'], (8, .5, 15.8)) <= 2.4 + .05
    await tap('e'); s = rec('E'); assert s['session']['state'] == 'Dialogue', s['session']
    move_before = s['player']['position']; await tap('w', .4); s2 = snap(); assert math.dist(move_before, s2['player']['position']) < .04, 'modal movement leak'; rec('modal blocks movement')
    await focus_and_press('choice0'); s = rec('choice0'); 
    if s['session']['state'] != 'Shop': await focus_and_press('choice0'); s = rec('choice0 again')
    assert s['session']['state'] == 'Shop', s['session']
    await c.command({'action': 'capture', 'name': 'trade-shop-modal'})
    await focus_and_press('buy0'); s = rec('buy flask'); after_buy = dict(credits=s['session']['credits'], q=dict(s['session']['quantities']))
    await focus_and_press('sell2'); s = rec('sell scrap'); after_sell = dict(credits=s['session']['credits'], q=dict(s['session']['quantities']))
    await tap('Escape'); s = rec('close modal'); assert s['session']['state'] == 'Play', s['session']
    # walk away on foot
    steps['departure'] = await walk_to((8, 0, 19.5), .3, 30); rec('walked away')
    steps['lane'] = await walk_to((12, 0, 21), .3, 30); rec('lane')
    deltas = dict(buyCreditDelta=after_buy['credits'] - before['credits'], sellCreditDelta=after_sell['credits'] - after_buy['credits'],
                  flaskDelta=after_buy['q'].get('water_flask', 0) - before['q'].get('water_flask', 0), scrapDelta=after_sell['q'].get('scrap_coil', 0) - after_buy['q'].get('scrap_coil', 0))
    (OUT / 'mira-trade-route.json').write_text(json.dumps(dict(complete=True, before=before, afterBuy=after_buy, afterSell=after_sell, deltas=deltas, walk=steps, log=log), indent=2))
    print('DELTAS', json.dumps(deltas))

asyncio.run(main())
