"""Real-input check of the relay-knoll gunner nest after the 2 Oct 2026 next-level combat pass.

  ATHEN_GUNNER_EVIDENCE=<dir> [ATHEN_EXE=<player>] DISPLAY=:0 uv run --offline --with python-xlib --with pillow python unity/tools/check_gunner_separation.py

Carl: "The feral gunners seem to be attached to the other droids?" Cause found in the prefabs: FeralGunnerDroid and
FeralLancerDrone each carried a whole second droid (a worker / scrap drone with its own FeralDroid, Health, collider
and model) as an active child, so every gunner spawned welded to a worker. CombatNextLevelPass.Gunners() removes it.

This check Continues on the rifle fixture save (the Long Arm order, pistol with a stabilised grip), walks to the
relay-knoll approach landmark (28 m east of the nest, inside its 75 m activation and outside the gunners' 30 m aggro),
records the droids near the knoll for 20 s and asserts: exactly three droids at the nest (two gunners, one worker),
no droid is ever closer than 1.5 m to another, and no droid stays stuck at exactly another droid's position. It then
steps in to engage so the health bars show (capture), fights the nest with real F and checks the HUD experience toast
appears on a kill. Fails on any runtime exception in Player.log.
"""
import json, math, os, subprocess, sys, time, traceback, uuid
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'unity/evidence/gameplay-v2/20260930-reqa2'))
sys.path.insert(0, str(ROOT / 'unity/tools'))
import qa  # noqa: E402
from check_inventory_redesign import launch as launch_capped_player  # noqa: E402
if os.environ.get('ATHEN_EXE'): qa.EXE = Path(os.environ['ATHEN_EXE'])
OUT = Path(os.environ.get('ATHEN_GUNNER_EVIDENCE', ROOT / 'unity/evidence/next-level/20261002/combat/gunner-check')).resolve()
OUT.mkdir(parents=True, exist_ok=True)
report = {'passed': False, 'checks': [], 'failures': [], 'captures': [], 'samples': []}
KNOLL_RADIUS = 45.0   # droids within this of the relay-knoll approach count as the nest
MIN_SEPARATION = 1.5


def ok(cond, label, detail=None):
    report['checks'].append({'label': label, 'passed': bool(cond), 'detail': detail})
    if not cond: report['failures'].append(label)
    print(('PASS ' if cond else 'FAIL ') + label + ('' if detail is None else '  ' + json.dumps(detail, default=str)[:300]))
    return bool(cond)


def cap(name):
    p = qa.capture(name); report['captures'].append(str(p)); return p


def fixture_save(folder):
    """The rifle quest's version-2 fixture: primer done, Long Arm order, pistol with a stabilised grip (check_rifle_quest.py)."""
    folder.mkdir(parents=True, exist_ok=True)
    skills = ['armourcraft', 'armourHandling', 'awareness', 'blades', 'blunt', 'chemistry', 'dodging', 'electronics', 'energyWeapons', 'engineering', 'pistol', 'rifle']
    s = {'version': 2, 'savedUtc': '2026-10-02T12:00:00.0000000Z', 'build': '0.1.0', 'credits': 60, 'purchases': 0, 'sales': 0,
         'items': [{'itemId': 'rifle_receiver', 'quantity': 1}, {'itemId': 'scrap_alloy', 'quantity': 12}, {'itemId': 'copper_filament', 'quantity': 6},
                   {'itemId': 'nanite_residue', 'quantity': 8}, {'itemId': 'field_toolkit', 'quantity': 1}, {'itemId': 'droid_servo_damaged', 'quantity': 1},
                   {'itemId': 'water_flask', 'quantity': 1}, {'itemId': 'medkit', 'quantity': 1}],
         'crafting': {'known': ['recipe_charge_cell_core', 'recipe_field_rifle', 'recipe_rifle_precision_barrel', 'recipe_grip_stabilised_pistol'],
                      'crafted': [{'id': 'recipe_grip_stabilised_pistol', 'count': 1}], 'crafts': 1,
                      'fitted': [{'slot': 'grip', 'itemId': 'grip_stabilised_pistol'}],
                      'weapons': [{'weaponId': 'weapon_scrap_pistol', 'fitted': [{'slot': 'grip', 'itemId': 'grip_stabilised_pistol'}]}]},
         'loot': {'rng': 'bc1721a626f0570d', 'rolls': 8, 'misses': [], 'collected': ['scrap_alloy', 'copper_filament', 'nanite_residue', 'droid_servo_damaged', 'rifle_receiver']},
         'bermsStep': 'Complete', 'hasPistol': True,
         'orders': {'index': 5, 'id': 'order_long_arm', 'testFired': ['order_steady_hands'], 'reported': ['order_steady_hands', 'order_kit_helmet']},   # 3 Oct 2026: Long Arm follows the four Warden Kit orders
         'city': {'visitedHill': True, 'boughtFlask': False, 'soldScrap': False, 'linked': False, 'spoken': [], 'selectedDestination': '', 'flags': ['brann_met']},
         'character': {'version': 1, 'level': 1, 'experience': 0, 'attributePoints': 4, 'skillPoints': 12,
                       'attributes': [{'id': a, 'count': 10} for a in ['agility', 'endurance', 'intellect', 'perception', 'resolve', 'strength']],
                       'skills': [{'id': k, 'count': 20 if k in ('rifle', 'engineering') else 0} for k in skills],
                       'equipped': [{'slot': 'armour_chest', 'itemId': 'field_vest'}, {'slot': 'secondary', 'itemId': 'scrap_pistol'}, {'slot': 'storage', 'itemId': 'field_backpack'}]}}
    (folder / 'ward-save.json').write_text(json.dumps(s, indent=1))
    return folder


def near_knoll(snapshot, centre):
    return [e for e in snapshot['combat']['enemies'] if math.hypot(e['position'][0] - centre[0], e['position'][2] - centre[1]) < KNOLL_RADIUS]


def pairwise_min(es):
    best = None
    for i in range(len(es)):
        for j in range(i + 1, len(es)):
            a, b = es[i]['position'], es[j]['position']
            d = math.hypot(a[0] - b[0], a[2] - b[2])
            if best is None or d < best[0]: best = (round(d, 2), es[i]['displayName'], es[j]['displayName'])
    return best


def main():
    save = fixture_save(OUT / 'save')
    run = OUT / 'run'
    if run.exists():
        raise RuntimeError('evidence run folder already exists: ' + str(run))
    unit = 'ashfall-gunner-qa-' + uuid.uuid4().hex[:10]
    proc = launch_capped_player(OUT, save.resolve(), qa.EXE.resolve(), unit)
    report['player'] = {'unit': unit + '.scope', 'pid': qa.pid()}
    try:
        qa.wait_menu(); qa.focus(); qa.tap('Return'); qa.wait(lambda: qa.state() == 'Play', 40, what='Play after Continue'); qa.release_all()
        qa.cmd('resize', width=1920, height=1080); time.sleep(1.5)
        qa.cmd('timeSet', hour=13); qa.cmd('timePause', paused=True)
        qa.goto('relay_knoll_approach'); qa.view('follow'); time.sleep(.5)
        here = qa.pos(); centre = (here[0], here[2])
        # the nest activates within 75 m; give it a moment to spawn
        qa.wait(lambda: len(near_knoll(qa.snap(), centre)) >= 3, 15, what='relay-knoll droids spawned')
        s = qa.snap(); nest = near_knoll(s, centre)
        names = sorted(e['displayName'] for e in nest)
        ok(names == ['Feral gunner droid', 'Feral gunner droid', 'Feral worker droid'], 'nest is exactly two gunners and one worker (no nested droids)', names)
        # face the nest (west of the approach) and record 20 s of positions
        nearest = min(nest, key=lambda e: math.hypot(e['position'][0] - here[0], e['position'][2] - here[2]))
        qa.face(nearest['position'][0], nearest['position'][2]); time.sleep(.5)
        cap('knoll-approach')
        worst = None; stuck = 0; t0 = time.monotonic()
        while time.monotonic() - t0 < 20:
            s = qa.snap(); es = [e for e in near_knoll(s, centre) if e['alive']]
            m = pairwise_min(es)
            report['samples'].append({'t': round(time.monotonic() - t0, 1), 'droids': [(e['displayName'], e['state'], [round(v, 2) for v in e['position']]) for e in es], 'minSeparation': m})
            if m and (worst is None or m[0] < worst[0]): worst = m
            if m and m[0] < .05: stuck += 1
            time.sleep(.25)
        ok(worst is not None and worst[0] >= MIN_SEPARATION, f'pairwise separation stays >= {MIN_SEPARATION} m over 20 s', {'worst': worst, 'samples': len(report['samples'])})
        ok(stuck == 0, 'no droid ever sits at another droid\'s position', stuck)
        # step in until the gunners engage so their bars (tier-tinted) show, then capture
        qa.tap('7', settle=.6); ok(qa.snap()['combat']['Armed'], 'pistol drawn with 7')
        qa.goto('relay_knoll_approach'); qa.view('follow'); qa.face(centre[0], centre[1]); time.sleep(.3); qa.hold('w', 2.5)   # enemies agent, nl1 fix: the player may be back at the gate here; approach from the landmark instead of a 200 m walk
        qa.wait(lambda: any(e['state'] not in ('Idle', 'Returning') for e in near_knoll(qa.snap(), centre)), 12, what='nest engages')
        time.sleep(.8); s = qa.snap(); engaged = [e for e in near_knoll(s, centre) if e['alive']]
        e0 = max(engaged, key=lambda e: 0 if e['displayName'] != 'Feral gunner droid' else 1)
        qa.face(e0['position'][0], e0['position'][2]); time.sleep(.4)
        cap('knoll-engaged-bars')
        lay = qa.ui(); bars = [x for x in lay['elements'] if x['visible'] and x.get('text') and 'droid' in x['text'].lower()]
        ok(len(bars) >= 1, 'enemy health bar names visible on the HUD', [b['text'] for b in bars][:4])
        # fight with real F; watch the HUD for the experience toast on the first kill
        deaths = []; seen_xp = []
        def until(snapshot):
            lay = qa.ui()
            for x in lay['elements']:
                if x['visible'] and x.get('text') and 'XP' in x['text'] and x['text'] not in seen_xp: seen_xp.append(x['text'])
            return not any(e['alive'] for e in near_knoll(snapshot, centre))
        r = qa.fight(until=until, seconds=200, deaths=deaths, center=(centre[0] - 6, centre[1]), leash=30, regroup='relay_knoll_approach', engage=14.0)
        report['fight'] = r
        ok(len(deaths) >= 1, 'at least one droid put down with real input', {'kills': len(deaths), 'seconds': r.get('seconds')})
        ok(any(t.startswith('+') and 'XP' in t for t in seen_xp) or any('no XP' in t for t in seen_xp), 'experience toast shown on a kill', seen_xp[:4])
        cap('knoll-after-fight')
        errors = qa.log_errors(); ok(not errors, 'no runtime exceptions in Player.log', errors[:3])
    finally:
        try: report['stop'] = qa.stop(timeout=8)
        except Exception as e: report['stopError'] = str(e)
        subprocess.run(['systemctl', '--user', 'stop', unit + '.scope'], capture_output=True, text=True, timeout=15)
    report['passed'] = not report['failures']


if __name__ == '__main__':
    try: main()
    except Exception:
        report['exception'] = traceback.format_exc(); report['failures'].append('exception'); print(report['exception'])
    (OUT / 'report.json').write_text(json.dumps(report, indent=1, default=str))
    print('GUNNER SEPARATION', 'PASS' if report['passed'] else 'FAIL', '-', len(report['checks']), 'checks,', len(report['failures']), 'failures')
    sys.exit(0 if report['passed'] else 1)
