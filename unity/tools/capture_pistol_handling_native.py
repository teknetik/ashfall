"""Native capture of the scrap pistol's handling, bare and with the Stabilised Pistol Grip at each crafted quality
(Steady Hands bench, craft agent, 20 Nov 2026; DESIGN.md section 10, numbers in art/steady_hands_bench_20261120/craft/README.md).

For each configuration (bare, Rough, Standard, Fine) from the same spot at the Warden firing line, in first person:
  1. the grip is set with dev.craft.strip / dev.craft.fit (no bench needed), condition full, rapid-fire heat cooled;
  2. aimed down the sights at plate 1 for 1.6 s: three frames of the idle sway;
  3. the same timed five-shot string (F every INTERVAL s, right mouse held): one frame just after every shot and two
     during the recovery after the last; after every shot the bridge's crafting.json `bench.shot` block is logged (shot
     direction, end point, cone, heat, kick and side kick);
  4. the group: each shot's deviation from the aim line in degrees (yaw, pitch), the widest pair, the mean climb.
The aim is re-applied before every string, so the strings start from the same view.

Needs a development build with the craft agent's dev.craft.* hook in DevBridgeCommands and the `bench` block in NativeQa's
crafting.json (both one-line hooks, owned by the bench agent). Without them the script stops with a clear failure.

  ~/.local/state/ward-programme/steady-hands-20261120/native_check.sh pistol_handling unity/tools/capture_pistol_handling_native.py ATHEN_EXE=...
  (or: ATHEN_EXE=... uv run --offline --with python-xlib --with pillow python unity/tools/capture_pistol_handling_native.py OUT)

Output: report.json (checks, per-shot log, group table), handling.md (the table), frames <config>-*.png.
Environment: HANDLING_INTERVAL (seconds between shots, default 0.32), HANDLING_CONFIGS (comma list, default bare,Rough,Standard,Fine).
"""
import json, math, os, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault('ATHEN_OUT', str(Path(__file__).resolve().parents[2] / 'unity/evidence/steady_hands/20261120/craft/handling'))
import showcase_qa as S  # noqa: E402
from showcase_qa import ok, note, qa  # noqa: E402

INTERVAL = float(os.environ.get('HANDLING_INTERVAL', '.32'))
CONFIGS = [c.strip() for c in os.environ.get('HANDLING_CONFIGS', 'bare,Rough,Standard,Fine').split(',') if c.strip()]
RANGE = 'checkpoint_firingline'
PLATE_CAM = 'cam_checkpoint_plate1'
GRIP = 'grip_stabilised_pistol'
SAVE = S.OUT / 'save'


def bench():
    return (qa.craft() or {}).get('bench') or {}


def shot():
    return bench().get('shot') or {}


def yaw_pitch(d):
    x, y, z = d
    return math.degrees(math.atan2(x, z)), -math.degrees(math.asin(max(-1.0, min(1.0, y))))


def ang(a, b):
    return math.degrees(math.acos(max(-1.0, min(1.0, sum(p * q for p, q in zip(a, b)) / (math.sqrt(sum(p * p for p in a)) * math.sqrt(sum(q * q for q in b)) or 1)))))


def calibrate():
    """Aim from the plate camera: three hip shots from its view; their mean end point is the plate (approximately)."""
    qa.view(PLATE_CAM); time.sleep(.6)
    qa.cmd('dev.craft.heat')
    ends = []
    for _ in range(3):
        n0 = shot().get('ShotsFired', 0)
        qa.focus(); qa.tap('f', secs=.05, settle=.45)
        s = shot()
        if s.get('ShotsFired', 0) > n0:
            ends.append(s['end'])
    qa.view('follow'); time.sleep(.4)
    if not ends:
        return None
    return [sum(e[i] for e in ends) / len(ends) for i in range(3)]


def aim_at(target):
    qa.goto(RANGE); qa.view('follow'); time.sleep(.3)
    qa.cmd('cameraBoom', boom=0.0); time.sleep(.6)
    cam = qa.snap()['camera']['position']
    d = [target[i] - cam[i] for i in range(3)]
    n = math.sqrt(sum(v * v for v in d)) or 1
    y, p = yaw_pitch([v / n for v in d])
    qa.yaw(y); qa.pitch(p); time.sleep(.5)
    return y, p, [v / n for v in d]


def set_grip(config):
    if config == 'bare':
        try:
            qa.cmd('dev.craft.strip', slot='grip')
        except RuntimeError as e:
            if 'empty_slot' not in str(e) and 'refused' not in str(e):
                raise
    else:
        qa.cmd('dev.craft.fit', itemId=GRIP, quality=config)
    qa.cmd('dev.weapon.condition', weaponId='weapon_scrap_pistol', full=True)
    time.sleep(.3)
    b = bench()
    return {'qualities': b.get('qualities'), 'handling': b.get('handling')}


def string(config, aim):
    """Idle sway frames, then the timed five-shot string with frames, then the recovery frames."""
    y0, p0, d0 = aim
    qa.yaw(y0); qa.pitch(p0); qa.cmd('dev.craft.heat'); time.sleep(.4)
    shots = []
    qa.focus(); qa.button(3, True)
    try:
        time.sleep(.5)
        for i in range(3):
            S.cap(f'{config}-sway-{i}', layout=False); time.sleep(.45)
        qa.yaw(y0); qa.pitch(p0); time.sleep(.25)
        t0 = time.monotonic()
        for k in range(5):
            wait = t0 + k * INTERVAL - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            n0 = shot().get('ShotsFired', 0)
            qa.tap('f', secs=.04, settle=0)
            t_shot = time.monotonic() - t0
            time.sleep(.05)
            S.cap(f'{config}-shot-{k + 1}', layout=False)
            s = shot()
            fired = s.get('ShotsFired', 0) > n0
            entry = {'k': k + 1, 'fired': fired, 'tSent': round(t_shot, 3), 'tCaptured': round(time.monotonic() - t0, 3)}
            if fired:
                dy, dp = yaw_pitch(s['dir'])
                entry.update({'dir': s['dir'], 'end': s['end'], 'yawDev': round(((dy - y0 + 180) % 360) - 180, 3), 'pitchDev': round(dp - p0, 3),
                              'cone': s.get('lastCone'), 'heatScale': s.get('lastHeatScale'), 'kick': s.get('lastKick'), 'side': s.get('lastSideKick')})
            shots.append(entry)
        time.sleep(.12); S.cap(f'{config}-recover-1', layout=False)
        time.sleep(.3); S.cap(f'{config}-recover-2', layout=False)
        cam = qa.snap()['camera']
        drift = {'yaw': round(((cam['yaw'] - y0 + 180) % 360) - 180, 3), 'pitch': round(cam['pitch'] - p0, 3)}
    finally:
        qa.button(3, False)
    hit = [s for s in shots if s.get('fired')]
    widest = max((ang(a['dir'], b['dir']) for i, a in enumerate(hit) for b in hit[i + 1:]), default=0)
    climb = (sum(s['pitchDev'] for s in hit) / len(hit)) if hit else None
    return {'shots': shots, 'fired': len(hit), 'groupDegrees': round(widest, 3), 'meanPitchDev': None if climb is None else round(climb, 3),
            'firstShotDeviation': round(ang(hit[0]['dir'], d0), 3) if hit else None, 'viewDriftAfter': drift,
            'rattled': shot().get('Rattled'), 'damperTicks': shot().get('DamperTicks')}


def body():
    S.kit_save(SAVE)
    S.launch(save=SAVE)
    S.start()
    qa.cmd('resize', width=1920, height=1080); time.sleep(1.5)
    qa.cmd('timeSet', hour=12.5); qa.cmd('timePause', paused=True)
    try:
        qa.cmd('dev.weather.reset', instant=True)
    except Exception as e:  # noqa: BLE001
        note('weather reset unavailable', str(e))
    if not ok('bench' in (qa.craft() or {}), "crafting.json has the craft agent's `bench` block (NativeQa hook)", list((qa.craft() or {}).keys())):
        return
    try:
        qa.cmd('dev.craft.heat')
    except RuntimeError as e:
        ok(False, 'dev.craft.* reaches CraftDevCommands (DevBridgeCommands hook)', str(e)); return
    qa.goto(RANGE); time.sleep(.8)
    qa.focus(); qa.tap('2', settle=.9)
    if not ok(qa.snap()['combat']['Armed'], 'scrap pistol drawn with 2 at the firing line'):
        return
    target = calibrate()
    ok(target is not None, 'plate located from the plate camera', target)
    if target is None:
        return
    aim = aim_at(target)
    note('aim', {'yaw': aim[0], 'pitch': aim[1]})
    results = {}
    for config in CONFIGS:
        info = set_grip(config)
        ok(config == 'bare' and not (info['qualities'] or {}).get('grip') or (info['qualities'] or {}).get('grip') == config,
           f'{config}: grip slot as wanted', info)
        aim = aim_at(target)
        r = string(config, aim)
        r['handling'] = info['handling']
        results[config] = r
        ok(r['fired'] == 5, f'{config}: five shots fired', [s.get('tSent') for s in r['shots']])
        note(f'{config} group', {k: r[k] for k in ('groupDegrees', 'meanPitchDev', 'firstShotDeviation', 'viewDriftAfter', 'rattled', 'damperTicks')})
    S.report['handling'] = results
    if 'bare' in results and 'Standard' in results:
        b, s = results['bare'], results['Standard']
        ok(b['handling']['sway'] > s['handling']['sway'] and b['handling']['scatterGrowth'] > s['handling']['scatterGrowth'],
           'the grip lowers sway and rapid-fire scatter growth (live numbers)', {'bare': b['handling'], 'Standard': s['handling']})
        note('group widths (degrees; one string each, random scatter included: judge from frames and several runs)',
             {c: results[c]['groupDegrees'] for c in results})
    lines = ['| config | sway ° | kick ° | side ° | recovery s | growth | group ° | mean climb ° | 1st shot dev ° | view drift (yaw, pitch) ° |',
             '|---|---|---|---|---|---|---|---|---|---|']
    for c, r in results.items():
        h = r.get('handling') or {}
        lines.append(f"| {c} | {h.get('sway', 0):.2f} | {h.get('kick', 0):.2f} | {h.get('sideStep', 0):.2f} | {h.get('recovery', 0):.2f} | {h.get('scatterGrowth', 0):.2f} | "
                     f"{r['groupDegrees']:.2f} | {r['meanPitchDev'] if r['meanPitchDev'] is not None else '-'} | {r['firstShotDeviation']} | "
                     f"{r['viewDriftAfter']['yaw']}, {r['viewDriftAfter']['pitch']} |")
    (S.OUT / 'handling.md').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines), flush=True)


S.run(body)
