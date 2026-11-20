"""Native check of the light budget (art/light_budget_20261120/README.md, phase 2 of the showcase programme, 20 Nov 2026).

The 32-light cap of URP on the Linux OpenGL Core player leaves 30 local lights per camera. The budget keeps the lights
enabled in the rendering camera's view at or under LightBudget.hardCap (28) by design, with pools for the demoted lamps.

1. Continue (kit save), 20:30, budget on: a scripted night walk (spawn apron, avenue, Basic General, courtyard and
   terminals, hall district, market and West Gate, the range, the Salvage and Field Supply interiors, the container
   home) with 360-degree turns: lights enabled in view never exceed 30 (and the budget's own cap); frames captured.
2. The runtime switch: budget off at cam_night_spawn_apron puts more than 30 lights in view (the problem is real),
   on brings it back under the cap; the state is reported in light-budget.json.
3. The light clock is unchanged: at 13:00 and 20:30 the clock's own active-lamp count and lamp strength are identical
   with the budget on and off, night-only lamps are off at 13:00 (fewer lamps wanted than at 20:30).
4. No runtime exceptions.
  ATHEN_EXE=<player> python unity/tools/check_showcase_light_budget.py [OUT]
Needs a development build with LightBudgetQa (light-budget.json in the --athen-qa folder).
"""
import json, math, os, time
import showcase_qa as S
from showcase_qa import qa, ok, note, cap

CAP_URP_LOCAL = 30
ROUTE = [
    ('spawn-avenue', 'west_gate', [(34, 0), (24, 1), (16, 6), (8, 19.6)]),
    ('courtyard-hall', 'field_supply', [(10, -10), (5, -19), (-4, -22), (-10, -19)]),
    ('market-westgate', 'shop_row_e', [(-14, 3), (-27, -4), (-32, -12), (-45, 5), (-56, 1)]),
    ('range', 'checkpoint_approach', [(-62, 3), (-66.5, 4.5)]),
    ('salvage', 'salvage_shop', [(-18.5, 18.6), (-20.4, 18.0)]),
    ('fieldsupply', 'field_supply', [(18.5, -9.4), (20.5, -9.0)]),
    ('home', 'home_inside', []),
]


def lb():
    try:
        return qa.read('light-budget.json')
    except Exception:  # noqa: BLE001
        return {}


def lb_cmd(**kw):
    kw['id'] = os.urandom(6).hex()
    tmp = qa.RUN / 'light-budget-cmd.tmp'
    tmp.write_text(json.dumps(kw)); tmp.rename(qa.RUN / 'light-budget-cmd.json')
    for _ in range(100):
        b = lb()
        if b.get('lastCommand') == kw['id']:
            return b
        time.sleep(.05)
    raise TimeoutError('light budget command not taken: %s' % kw)


def settle(t=1.2):
    time.sleep(t)
    first = lb().get('frame', 0)
    for _ in range(40):
        if lb().get('frame', 0) > first:
            break
        time.sleep(.05)
    return lb()


def turn(samples, tag):
    for k in range(16):
        qa.yaw(k * 22.5); time.sleep(.12)
        b = lb(); samples.append((tag, b.get('inView')))


def body():
    os.environ['ATHEN_LIGHT_BUDGET'] = '1'
    S.launch(save=S.kit_save(S.OUT / 'save'))
    S.start()
    qa.cmd('dev.weather.set', state='breezy', instant=True)
    b = settle()
    ok(b.get('installed') and b.get('enabled'), 'light budget installed and on at start', {k: b.get(k) for k in ('installed', 'enabled', 'budget')})
    hard = (b.get('budget') or {}).get('hardCap', 28)

    # ---- 3. light clock unchanged by the budget
    clock = {}
    for hour in (13, 20.5):
        S.time_set(hour)
        qa.view('cam_avenue')
        for state in (True, False):
            lb_cmd(enabled=state); b = settle(1.5)
            clock[(hour, state)] = {'circuit': b.get('circuit'), 'lampStrength': b.get('lampStrength'), 'wanted': b.get('wantedInView'), 'inView': b.get('inView')}
    S.report['clock'] = {'%s-%s' % (h, 'on' if s else 'off'): v for (h, s), v in clock.items()}
    same = all(clock[(h, True)]['circuit'] == clock[(h, False)]['circuit'] and clock[(h, True)]['lampStrength'] == clock[(h, False)]['lampStrength'] for h in (13, 20.5))
    ok(same, 'the light clock (active lamps, shadow lamps, strength) is identical with the budget on and off at 13:00 and 20:30', S.report['clock'])
    ok((clock[(13, True)]['circuit'] or {}).get('strength', 1) < .2 and (clock[(20.5, True)]['circuit'] or {}).get('strength', 0) > .9,
       'lamp strength by hour: daytime strength at 13:00, full at 20:30', {h: (clock[(h, True)]['circuit'] or {}).get('strength') for h in (13, 20.5)})
    ok((clock[(13, False)]['circuit'] or {}).get('ActiveLights', 0) < (clock[(20.5, False)]['circuit'] or {}).get('ActiveLights', 0),
       'night-only lamps are off by day (fewer clock lamps active at 13:00)', {h: (clock[(h, False)]['circuit'] or {}).get('ActiveLights') for h in (13, 20.5)})
    lb_cmd(enabled=True)

    # ---- 2. the switch
    S.time_set(20.5)
    qa.view('cam_night_spawn_apron')
    lb_cmd(enabled=False); off = settle(1.5)
    cap('switch-off-cam_night_spawn_apron', layout=False)
    lb_cmd(enabled=True); on = settle(2.0)
    cap('switch-on-cam_night_spawn_apron', layout=False)
    S.report['switch'] = {'off': off, 'on': on}
    ok(not off.get('enabled') and (off.get('inView') or 0) > CAP_URP_LOCAL, 'switch off: more than 30 lights in view at the spawn apron (URP would drop some)', off.get('inView'))
    ok(on.get('enabled') and (on.get('inView') or 99) <= hard, 'switch on: lights in view back under the budget', {'inView': on.get('inView'), 'hardCap': hard})
    qa.view('follow')

    # ---- 1. night walk, budget on
    lb_cmd(enabled=True, reset=True)
    samples = []
    for name, start, points in ROUTE:
        qa.goto(start); qa.view('follow'); qa.pitch(6); time.sleep(1.0)
        for i, (x, z) in enumerate(points):
            deadline = time.time() + 20
            while time.time() < deadline:
                p = qa.pos(); d = math.hypot(x - p[0], z - p[2])
                if d <= .9:
                    break
                qa.face(x, z)
                qa.hold(['Shift_L', 'w'] if d > 4 else 'w', min(.5, max(.12, d / 6)))
                samples.append((name, lb().get('inView')))
            else:
                note('walk %s: did not reach point %d' % (name, i), qa.pos())
        turn(samples, name)
        cap('walk-%s' % name, layout=False)
    run = lb_cmd(dump=True).get('running') or {}
    S.report['walk'] = {'running': run, 'samples': samples}
    worst = max([v for _, v in samples if v is not None] + [run.get('maxInView') or 0])
    ok(worst <= CAP_URP_LOCAL and run.get('framesOver30') == 0, 'night walk with turns: lights enabled in view never above 30 (every frame)',
       {'maxInView': run.get('maxInView'), 'framesOver30': run.get('framesOver30'), 'frames': run.get('frames'), 'maxWanted': run.get('maxWantedInView')})
    ok(run.get('framesOverCap') == 0, 'night walk: never above the budget cap (%d)' % hard, {'framesOverCap': run.get('framesOverCap'), 'hardCuts': run.get('hardCuts')})
    note('walk: lamps the owners wanted in view (what URP would have had to drop from)', {'maxWanted': run.get('maxWantedInView'), 'mean': run.get('meanInView')})


S.run(body)
