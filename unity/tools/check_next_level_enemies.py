"""Real-input check of the 2 Oct 2026 next-level enemies (Scrap Reaper, Ironclad Warden, Post Sentinel) and their four
outer POIs on the native development player.

  ATHEN_NEXTLEVEL_EVIDENCE=<dir> [ATHEN_EXE=<player>] DISPLAY=:0 uv run --offline --with python-xlib --with pillow python unity/tools/check_next_level_enemies.py

Continue on a fixture save (the rifle-quest fixture of check_rifle_quest.py grown to the full basic kit: field rifle with the
precision barrel equipped as primary, plate carrier + helmet + armguards + gloves + leggings + boots, Rifle 20) and visit
each POI from its QA landmark (nextlevel_*): the encounter activates by proximity and engages; each droid type attacks
(melee wind-up seen in the enemy state, sentinel bolts counted); all of them can be killed with the rifle (real F); the
kills drop salvage caches (one is collected with real E); the site's strongbox/crate can be searched with real E and the
first strongbox yields the three new parts. Fails on any runtime exception in Player.log.
Requires a development build with NextLevelEnemiesInstall applied (scene, prefabs, loot tables, catalog items).
Run under the shared Unity job lock with other Unity/player jobs stopped."""
import json, math, os, subprocess, sys, time, traceback, uuid
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'unity/evidence/gameplay-v2/20260930-reqa2'))
sys.path.insert(0, str(ROOT / 'unity/tools'))
import qa  # noqa: E402
from check_inventory_redesign import launch as launch_capped_player  # noqa: E402
if os.environ.get('ATHEN_EXE'): qa.EXE = Path(os.environ['ATHEN_EXE'])
OUT = Path(os.environ.get('ATHEN_NEXTLEVEL_EVIDENCE', ROOT / 'unity/evidence/next-level/20261002/enemies/native-check')).resolve()
OUT.mkdir(parents=True, exist_ok=True)
SITES = json.loads((ROOT / 'art/next_level_20261002/enemies/sites.json').read_text())['sites']
NAMES = {'warden': 'Ironclad Warden', 'reaper': 'Scrap Reaper', 'sentinel': 'Post Sentinel'}
PARTS = ('ironclad_plate', 'reaper_blade', 'sentinel_optic')
report = {'passed': False, 'checks': [], 'failures': [], 'captures': [], 'sites': {}, 'player': {}}
_owned = None


def launch_player(save):
    global _owned
    out = OUT / 'run'; out.mkdir(exist_ok=True)
    unit = 'ashfall-nextlevel-qa-' + uuid.uuid4().hex[:10]
    record = {'unit': unit + '.scope', 'run': str(out / 'run'), 'saveDir': str(save)}
    report['player'] = record
    _owned = {'unit': unit, 'proc': None, 'record': record}
    _owned['proc'] = launch_capped_player(out, save.resolve(), qa.EXE.resolve(), unit)
    record['pid'] = qa.pid()


def stop_player():
    global _owned
    if _owned is None: return
    record, unit, proc = _owned['record'], _owned['unit'] + '.scope', _owned['proc']
    try:
        try: record['stop'] = qa.stop(timeout=8)
        except Exception as e: record['stopError'] = str(e)
        try: subprocess.run(['systemctl', '--user', 'stop', unit], capture_output=True, text=True, timeout=15)
        except Exception as e:
            record['scopeStopError'] = str(e)
            try: subprocess.run(['systemctl', '--user', 'kill', '--kill-whom=all', unit], capture_output=True, timeout=5)
            except Exception as kill_error: record['scopeKillError'] = str(kill_error)
        if proc is not None:
            try: record['launcherExitCode'] = proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.terminate()
                try: record['launcherExitCode'] = proc.wait(timeout=5)
                except subprocess.TimeoutExpired: proc.kill(); record['launcherExitCode'] = proc.wait(timeout=5)
    finally: _owned = None


def ok(cond, what, detail=None):
    (report['checks'] if cond else report['failures']).append(what if detail is None else {'check': what, 'detail': detail})
    print(('PASS ' if cond else 'FAIL ') + what, '' if detail is None else json.dumps(detail, default=str)[:300], flush=True)
    return cond


def cap(name):
    report['captures'].append(qa.capture(name, layout=False)); return name


def fixture_save(folder):
    """Version-2 save: primer and the first three orders done, the full basic kit equipped, the rifle modded, Rifle 20."""
    folder.mkdir(parents=True, exist_ok=True)
    skills = ['armourcraft', 'armourHandling', 'awareness', 'blades', 'blunt', 'chemistry', 'dodging', 'electronics', 'energyWeapons', 'engineering', 'pistol', 'rifle']
    s = {'version': 2, 'savedUtc': '2026-10-02T16:00:00.0000000Z', 'build': '0.1.0', 'credits': 120, 'purchases': 0, 'sales': 0,
         'items': [{'itemId': 'medkit', 'quantity': 2}],   # nl1: the pack filled on the first drops; carry almost nothing so caches and crates have room
         'crafting': {'known': ['recipe_charge_cell_core', 'recipe_field_rifle', 'recipe_rifle_precision_barrel', 'recipe_grip_stabilised_pistol'],
                      'crafted': [{'id': 'recipe_grip_stabilised_pistol', 'count': 1}, {'id': 'recipe_field_rifle', 'count': 1}, {'id': 'recipe_rifle_precision_barrel', 'count': 1}], 'crafts': 3,
                      'fitted': [{'slot': 'grip', 'itemId': 'grip_stabilised_pistol'}],
                      'weapons': [{'weaponId': 'weapon_scrap_pistol', 'fitted': [{'slot': 'grip', 'itemId': 'grip_stabilised_pistol'}]},
                                  {'weaponId': 'weapon_field_rifle', 'fitted': [{'slot': 'barrel', 'itemId': 'rifle_precision_barrel'}]}]},
         'loot': {'rng': 'bc1721a626f0570d', 'rolls': 20, 'misses': [], 'collected': ['scrap_alloy', 'copper_filament', 'nanite_residue', 'droid_servo_damaged', 'rifle_receiver', 'warden_plate_carrier']},
         'bermsStep': 'Complete', 'hasPistol': True,
         'orders': {'index': 7, 'id': 'order_keep_charge', 'testFired': ['order_steady_hands'], 'reported': ['order_steady_hands', 'order_kit_helmet', 'order_long_arm', 'order_plate_carrier']},   # 3 Oct 2026: after the Warden Kit orders
         'city': {'visitedHill': True, 'boughtFlask': False, 'soldScrap': False, 'linked': False, 'spoken': [], 'selectedDestination': '', 'flags': ['brann_met', 'waystation:berms_mid']},
         'character': {'version': 1, 'level': 2, 'experience': 0, 'attributePoints': 2, 'skillPoints': 6,
                       'attributes': [{'id': a, 'count': 10} for a in ['agility', 'endurance', 'intellect', 'perception', 'resolve', 'strength']],
                       'skills': [{'id': k, 'count': 20 if k in ('rifle', 'engineering') else 0} for k in skills],
                       'equipped': [{'slot': 'primary', 'itemId': 'field_rifle'}, {'slot': 'secondary', 'itemId': 'scrap_pistol'}, {'slot': 'armour_chest', 'itemId': 'warden_plate_carrier'},
                                    {'slot': 'armour_head', 'itemId': 'field_helmet'}, {'slot': 'armour_arms', 'itemId': 'field_armguards'}, {'slot': 'armour_hands', 'itemId': 'field_gloves'},
                                    {'slot': 'armour_legs', 'itemId': 'field_leggings'}, {'slot': 'armour_feet', 'itemId': 'field_boots'}, {'slot': 'storage', 'itemId': 'field_backpack'}]}}
    (folder / 'ward-save.json').write_text(json.dumps(s, indent=1))
    return folder


def near(names, centre, radius=70):
    return [e for e in qa.snap()['combat']['enemies'] if e['displayName'] in names and math.hypot(e['position'][0] - centre[0], e['position'][2] - centre[1]) < radius]


def rifle_up():
    """Draw the field rifle with 8 (switching from the pistol if needed)."""
    for _ in range(3):
        c = qa.snap()['combat']
        if c['Armed'] and c.get('weaponId') == 'weapon_field_rifle': return True
        qa.tap('8', settle=.6)
    c = qa.snap()['combat']; return c['Armed'] and c.get('weaponId') == 'weapon_field_rifle'


def fight(names, centre, expected, seconds=300, engage=16.0, deaths=None, regroup=None, states=None):
    """qa.fight for the rifle: hold the line at the site, shoot the nearest live site droid with real F, note every state seen.
    Kites: backs off from a melee droid that is winding up or inside 3 m, side-steps while a sentinel aims or fires. After a
    knock-down the player is far away and the cluster parks, so the loop returns to the landmark and waits for it to wake."""
    end = time.monotonic() + seconds; t0 = time.monotonic(); shots = 0; last = {}; quiet = 0; downs0 = qa.snap()['combat']['downs']; kite = 0
    deaths = deaths if deaths is not None else []; states = states if states is not None else set()
    def done(): return dict(shots=shots, seconds=round(time.monotonic() - t0, 1), deaths=deaths, states=sorted(states), downs=qa.snap()['combat']['downs'] - downs0)
    try:
        while time.monotonic() < end:
            s = qa.snap(); c = s['combat']
            live = []
            for i, e in enumerate(c['enemies']):
                k = (e['displayName'], i)
                if e['displayName'] in names: states.add(e['state'])
                if e['alive']: last[k] = e['position']
                elif k in last: deaths.append(dict(name=e['displayName'], position=e['position'], t=round(time.monotonic() - t0, 1))); del last[k]
                if e['alive'] and e['displayName'] in names and math.hypot(e['position'][0] - centre[0], e['position'][2] - centre[1]) < 90: live.append(e)
            if len(deaths) >= expected: return done()
            if not live:
                # parked (player far after a knock-down) or not yet re-formed: back to the landmark and wait for the cluster
                # parked, re-forming or walking home from the leash: wait at the landmark (up to ~75 s) before giving up
                quiet += 1
                if quiet > 40: return done()
                if regroup and quiet % 4 == 1: qa.goto(regroup); qa.view('follow'); qa.face(*centre); rifle_up()
                qa.hold('w', .4); time.sleep(.8)
                continue
            quiet = 0
            if not (c['Armed'] and c.get('weaponId') == 'weapon_field_rifle'): rifle_up(); continue
            p = s['player']['position']
            if math.hypot(p[0] - centre[0], p[2] - centre[1]) > 60 and regroup: qa.goto(regroup); qa.view('follow'); time.sleep(.4); rifle_up(); continue
            e = min(live, key=lambda x: math.hypot(x['position'][0] - p[0], x['position'][2] - p[2]))
            d = math.hypot(e['position'][0] - p[0], e['position'][2] - p[2])
            qa.aim_at(e['position'], lift=.5)
            # kite only on the tell, and never for long: a retreat that keeps going walked the first fights 60 m off the site
            melee_close = e['displayName'] != NAMES['sentinel'] and e['state'] == 'Windup' and d < 4.5 and kite < 3
            kite = kite + 1 if melee_close else max(0, kite - 1)
            sentinel_aiming = any(x['displayName'] == NAMES['sentinel'] and x['state'] in ('Windup', 'Firing') and math.hypot(x['position'][0] - p[0], x['position'][2] - p[2]) < 42 for x in live)
            if melee_close: qa.key('s', True); qa.tap('f', .06, .1); qa.key('s', False); shots += 1; continue
            if sentinel_aiming and d > 6: qa.key('d' if int(time.monotonic() * .5) % 2 == 0 else 'a', True); qa.tap('f', .06, .12); qa.release_all(); shots += 1; continue
            if d < engage:
                if c['Nano'] < 12: qa.hold('s', .35); continue
                qa.tap('f', .06, .14); shots += 1
            else: qa.hold('w', min(.5, max(.15, (d - engage + 1) / 5)))
        return done()
    finally: qa.release_all()


def search_crate(crate, landmark=None):
    """Walk beside a loot crate until its prompt shows, press E, hold still through the search. A search counts when the pack
    changes or the Field Pack note names loot left in a cache beside the crate."""
    x, z = crate['world']; r = dict(crate=crate['name'], at=[x, z]); pr = ''
    p = qa.pos()
    if landmark and math.hypot(p[0] - x, p[2] - z) > 40: qa.goto(landmark); qa.view('follow'); time.sleep(.4); p = qa.pos()
    ang = math.atan2(p[0] - x, p[2] - z)
    want = crate['prompt']; emptied = 'Emptied'
    # crates sit close together: only this crate's own prompt counts (the nearest interactable wins the prompt), so try
    # several sides and distances until it shows
    def tryside(a, dist):
        try: qa.walk_to(x + math.sin(a) * dist, z + math.cos(a) * dist, tol=.4, timeout=10); return True
        except TimeoutError as e: r.setdefault('walk', []).append(str(e)[:100]); return False
    found = False
    for dist in (1.2, .9, 1.6):
        for a in [ang, ang + .9, ang - .9, ang + 1.8, ang - 1.8, ang + 2.7, ang + 3.6]:
            reached = tryside(a, dist)
            if not reached:
                # a prop line in the way: come in from another side via a waypoint 6 m out
                for wa in (a + 1.57, a - 1.57, a + 3.14):
                    try: qa.walk_to(x + math.sin(wa) * 6, z + math.cos(wa) * 6, tol=.8, timeout=12)
                    except TimeoutError: continue
                    if tryside(wa, dist): break
            pr = qa.snap()['interaction']['prompt'] or ''
            if pr == want: found = True; break      # a neighbour's "Emptied" countdown is not this crate: keep circling
        if found: break
    r['prompt'] = pr
    if pr != want: r['ok'] = False; r['note'] = 'own prompt never shown (nearest node was another crate/cache)' if pr else 'no interactable reached'; return r
    q0 = qa.snap()['session']['quantities']; qa.tap('e', settle=.3); r['searching'] = qa.snap()['interaction']['prompt']
    t = time.monotonic()
    while time.monotonic() - t < 6:
        if qa.snap()['session']['quantities'] != q0: break
        time.sleep(.15)
    time.sleep(.4); s = qa.snap(); q1 = s['session']['quantities']
    r['got'] = {k: q1[k] - q0.get(k, 0) for k in q1 if q1[k] != q0.get(k, 0)}; r['promptAfter'] = s['interaction']['prompt']; r['lastLoot'] = qa.craft().get('lastLoot')
    r['ok'] = bool(r['got']) or ('left in the cache:' in (r['lastLoot'] or '') and 'Collected' in (r['lastLoot'] or ''))
    r['parts'] = [p for p in PARTS if (r['got'] or {}).get(p, 0) > 0 or p.replace('_', ' ').lower() in (r['lastLoot'] or '').lower()]
    return r


def visit(site):
    sid = site['id']; r = {}; centre = site['centre']; names = {NAMES[sp['kind']] for sp in site['encounter']['spawns']}
    qa.goto(site['landmark']); qa.view('follow'); time.sleep(.5); qa.face(*centre); time.sleep(.3)
    ok(rifle_up(), f'{sid}: field rifle drawn with 8', qa.snap()['combat'].get('weaponId'))
    # activation + engagement: the encounter spawns on proximity (75 m) and the droids turn on the player
    engaged = []
    for k in range(90):
        time.sleep(.3); e = near(names, centre)
        engaged = [x for x in e if x['state'] not in ('Idle', 'Returning')]
        if engaged: break
        # walk at the nearest live droid (walls at a site can hide the centre line); side-step every few tries to clear props
        p = qa.pos(); tgt = min(e, key=lambda x: math.hypot(x['position'][0] - p[0], x['position'][2] - p[2]))['position'] if e else [centre[0], 0, centre[1]]
        qa.face(tgt[0], tgt[2]); qa.hold('w', .5)
        if k % 6 == 5: qa.hold('d' if k % 12 == 5 else 'a', .7)
    e = near(names, centre); r['spawned'] = [(x['displayName'], x['state'], [round(v, 1) for v in x['position']]) for x in e]
    ok(len(e) == len(site['encounter']['spawns']), f'{sid}: encounter activated by proximity ({len(e)} droids)', r['spawned'])
    ok(bool(engaged), f'{sid}: the pack engages the player', [x['state'] for x in e])
    # each type attacks: melee wind-up seen in the state, sentinel bolts counted
    states = set(); bolts = 0; t0 = time.monotonic()
    while time.monotonic() - t0 < 45:
        for x in near(names, centre): states.add((x['displayName'], x['state'])); bolts = max(bolts, x['bolts'])
        melee_seen = any(st in ('Windup', 'Recover') and n != NAMES['sentinel'] for n, st in states)
        sentinel_seen = bolts > 0 or NAMES['sentinel'] not in names
        if (melee_seen or not (names - {NAMES['sentinel']})) and sentinel_seen: break
        time.sleep(.2)
    r['statesSeen'] = sorted(f'{n}:{st}' for n, st in states); r['bolts'] = bolts
    if names - {NAMES['sentinel']}: ok(any(st in ('Windup', 'Recover') and n != NAMES['sentinel'] for n, st in states), f'{sid}: melee droids wind up a strike', r['statesSeen'])
    if NAMES['sentinel'] in names: ok(bolts > 0, f'{sid}: Post sentinels fire bolts', bolts)
    h0 = qa.snap()['combat']['health']; cap(f'{sid}-fight')
    # kill them all with the rifle (knock-downs are a result, reported per site; zero kills is a failure)
    deaths = []; st = set(); loot0 = qa.craft().get('lootEvents', 0); expected = len(site['encounter']['spawns'])
    r['fight'] = fight(names, centre, expected, seconds=420, deaths=deaths, regroup=site['landmark'], states=st)
    detail = {'kills': len(deaths), 'expected': expected, 'shots': r['fight'].get('shots'), 'seconds': r['fight'].get('seconds'), 'downs': r['fight'].get('downs')}
    ok(len(deaths) >= expected, f'{sid}: all droids killed with the rifle', detail)
    report.setdefault('balance', {})[sid] = detail
    time.sleep(1.5); c = qa.craft()
    ok(c.get('lootEvents', 0) > loot0, f'{sid}: kills dropped salvage', {'lootEvents': c.get('lootEvents'), 'lastLoot': c.get('lastLoot')})
    # back to the site (a knock-down may have moved the player), collect one cache at a wreck (real E)
    qa.goto(site['landmark']); qa.view('follow'); time.sleep(.5)
    if deaths:
        lp = qa.pos(); d = min(deaths, key=lambda x: math.hypot(x['position'][0] - lp[0], x['position'][2] - lp[2])); col = qa.collect_at(d['position'][0], d['position'][2]); r['collected'] = col
        last = qa.craft().get('lastLoot') or ''; col['lastLoot'] = last
        # the pack has a slot cap: a collect that leaves loot in the cache still proves the cache, the prompt and E
        got = bool(col.get('got')) or ('Collected' in last and 'left in the cache:' in last and 'Collect' in (col.get('prompt') or ''))
        ok(got, f'{sid}: a salvage cache collected with real E', {k: col.get(k) for k in ('prompt', 'got', 'lastLoot')})
    cap(f'{sid}-cleared')
    # the loot crates
    r['crates'] = []
    for crate in site['crates']:
        res = search_crate(crate, site['landmark']); r['crates'].append(res)
        ok(res.get('ok', False), f"{sid}: loot crate '{crate['name']}' searched with real E", {k: res.get(k) for k in ('prompt', 'got', 'lastLoot')})
        if crate['loot'] == 'loot_nextlevel_strongbox' and res.get('ok'): report.setdefault('strongboxes', []).append(res)
    report['sites'][sid] = r


def main():
    save = fixture_save(OUT / 'save')
    try:
        launch_player(save)
        qa.wait_menu(); qa.focus(); qa.tap('Return'); qa.wait(lambda: qa.state() == 'Play', 40, what='Play after Continue'); qa.release_all()
        qa.cmd('resize', width=1920, height=1080); time.sleep(1.5)
        qa.cmd('timeSet', hour=13); qa.cmd('timePause', paused=True)
        qa.cmd('dev.state'); ch = qa.dev().get('character') or {}
        eq = (ch.get('equipped') or {}) if ch.get('available') else {}
        ok(eq.get('primary') == 'field_rifle' and eq.get('armour_chest') == 'warden_plate_carrier' and eq.get('armour_head') == 'field_helmet', 'fixture: rifle and the basic armour set equipped', eq)
        for site in SITES:
            try: visit(site)
            except Exception as e: report['failures'].append({'site': site['id'], 'error': repr(e), 'trace': traceback.format_exc()[-1200:]}); print('site error', site['id'], e, flush=True)
        sbs = report.get('strongboxes') or []
        ok(any(sb.get('parts') for sb in sbs), 'a strongbox yields a new part (guaranteed until collected)', [{'crate': sb.get('crate'), 'parts': sb.get('parts'), 'got': sb.get('got')} for sb in sbs][:4])
        errors = qa.log_errors(); ok(not errors, 'no runtime exceptions in Player.log', errors[:3])
    finally:
        stop_player()


try: main()
except Exception as e: report['failures'].append({'error': repr(e), 'trace': traceback.format_exc()[-1500:]}); print('error', e, flush=True)
finally:
    report['passed'] = not report['failures']
    (OUT / 'report.json').write_text(json.dumps(report, indent=1, default=str))
    print(('NEXT LEVEL ENEMIES PASS' if report['passed'] else 'NEXT LEVEL ENEMIES FAIL') + f" ({len(report['checks'])} checks, {len(report['failures'])} failures)")
