"""Matched native Tool Exchange display/shutter captures, dwell cost and real-key traversal (29 Sep 2026).

Run against a development player launched by launch_phase1_qa.py:
  ATHEN_NATIVE_DIR=<evidence>/<tag>-native ATHEN_NATIVE_PID=<pid> DISPLAY=:0 \\
    uv run --offline --with python-xlib --with pillow python capture_tool_exchange_display.py [stills|traverse|vex|mem|all] [hour]

Diagnostic cameras never qualify traversal. Player-height views use the real follow camera in first person and are reached with
real keyboard walking (positions are recorded, not assumed). `hour` (optional) sets the paused day clock; default is the authored 17:00.
No scene state is written.
"""
import asyncio, hashlib, json, math, os, statistics, sys, time
from pathlib import Path
from PIL import Image
from native_client import Client
from desktop_input import focus, key

OUT = Path(os.environ['ATHEN_NATIVE_DIR'])
FIXED = ['cam_audit_tool_exchange_front', 'cam_audit_tool_exchange_door', 'cam_audit_tool_exchange_side_left', 'cam_audit_tool_exchange_side_right']
# Tool Exchange: building pivot (-20.6, 0.5, 9.0) yaw 90; building-local +Z (avenue) = world +X. Porch top world y 0.5.
# Glass face world x = -18.057; display centre z = 6.85; shutter hardware centre z = 10.03. Eye height is the game's own 1.65 m.
PLAYER_VIEWS = [
    ('fp_front_lane', (-13.0, 0.0, 8.4), (-18.0, 1.5, 8.4), 'avenue lane, frontage from 5 m: display and shutter'),
    ('fp_door_porch', (-16.4, 0.5, 8.4), (-18.0, 1.5, 8.4), 'porch, player height between display and shutter'),
    ('fp_display_close', (-16.45, 0.5, 6.85), (-18.1, 1.9, 6.85), 'porch, 1.6 m from the display glass'),
    ('fp_shutter_close', (-16.45, 0.5, 10.03), (-18.0, 1.4, 10.03), 'porch, 1.6 m from the shutter hardware'),
    ('fp_side_left', (-15.4, 0.5, 5.6), (-18.0, 1.7, 7.0), 'oblique from the display side'),
    ('fp_side_right', (-15.4, 0.5, 12.3), (-18.0, 1.4, 9.8), 'oblique from the shutter side'),
]


# Retained salvage route to the south court, then along the avenue lane (from tools/porch-route.json: east_south -> east_porch_approach).
APPROACH = [('west_stair_approach', (12, 0, 0)), ('hill_tree', (4, 1.5, 0)), ('hill_southwest', (4, 1.5, 4)), ('south_stair_top', (0, 1.5, 4)),
            ('south_stair_bottom', (0, 0, 12)), ('south_court', (0, 0, 28)), ('east_south', (-13, 0, 28)), ('east_porch_approach', (-13, 0, 9))]


def percentile(v, p):
    v = sorted(v); i = (len(v) - 1) * p; a = int(i); b = min(a + 1, len(v) - 1); return v[a] + (v[b] - v[a]) * (i - a)


def summarize(frames):
    dt = [f['dt'] * 1000 for f in frames]
    r = dict(frames=len(dt), seconds=sum(dt) / 1000, averageFps=len(dt) * 1000 / sum(dt), p50Ms=percentile(dt, .5), p95Ms=percentile(dt, .95),
             p99Ms=percentile(dt, .99), maxMs=max(dt), over33=sum(x > 33.33 for x in dt))
    for k in ['mainMs', 'cpuMs', 'gpuMs', 'draws', 'tris', 'batches', 'setPass']:
        vals = [f[k] for f in frames if f.get(k, -1) > 0]
        r[k] = dict(samples=len(vals), mean=statistics.mean(vals), p95=percentile(vals, .95), max=max(vals)) if vals else None
    return r


def snap(): return json.loads((OUT / 'snapshot.json').read_text())
def read(n): return json.loads((OUT / n).read_text())


async def walk_to(c, d, target, tol=.3, limit=40):
    started = time.monotonic(); last = 999; stalls = 0; steps = 0
    while True:
        s = snap(); p = s['player']['position']; dx = target[0] - p[0]; dz = target[2] - p[2]; dist = math.hypot(dx, dz)
        if dist < tol: return dict(reached=True, position=p, samples=steps)
        if time.monotonic() - started > limit: raise RuntimeError('timeout walking to %s at %s' % (target, p))
        stalls = stalls + 1 if abs(last - dist) < .01 else 0
        if stalls >= 6: raise RuntimeError('BLOCKED before %s at %s' % (target, p))
        last = dist; steps += 1
        await c.command({'action': 'cameraYaw', 'yaw': math.degrees(math.atan2(dx, dz))}); await asyncio.sleep(.08)
        key(d, 'w', True)
        try: await asyncio.sleep(min(2, max(.025, (dist - .1) / 3.4)))
        finally: key(d, 'w', False)
        await asyncio.sleep(.1)


async def start_play(c, d, hour=None):
    for _ in range(600):
        if (OUT / 'snapshot.json').exists(): break
        await asyncio.sleep(.1)
    if snap()['session']['state'] == 'MainMenu':
        for _ in range(8):
            key(d, 'Return', True); await asyncio.sleep(.12); key(d, 'Return', False); await asyncio.sleep(1.5)
            if snap()['session']['state'] != 'MainMenu': break
    for _ in range(300):
        if snap()['session']['state'] == 'Play': break
        await asyncio.sleep(.1)
    assert snap()['session']['state'] == 'Play', snap()['session']
    for k in ['w', 'a', 's', 'd', 'e', 'Return', 'Escape']: key(d, k, False)
    await c.command({'action': 'resize', 'width': 1920, 'height': 1080}); await asyncio.sleep(2)
    await c.command({'action': 'timeReset'})
    if hour is not None: await c.command({'action': 'timeSet', 'hour': float(hour)})
    await c.command({'action': 'timePause', 'paused': True}); await c.command({'action': 'timeState'})
    await c.command({'action': 'settingsSnapshot'})


async def shot(c, name, extra=None):
    await c.command({'action': 'capture', 'name': name}); path = OUT / (name + '.png')
    for _ in range(80):
        try:
            with Image.open(path) as im: im.load(); assert im.size == (1920, 1080), im.size
            break
        except (FileNotFoundError, OSError): await asyncio.sleep(.1)
    else: raise TimeoutError(name)
    s = snap(); assert [s['width'], s['height']] == [1920, 1080], (s['width'], s['height']); assert s['session']['state'] == 'Play'
    return dict(name=name, path=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(), player=s['player'], camera=s.get('camera'), notes=extra)


async def profile(c, seconds):
    await c.command({'action': 'profileStart'}); await asyncio.sleep(seconds); await c.command({'action': 'profileStop'})
    return summarize(read('profile.json'))


async def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else 'all'
    hour = sys.argv[2] if len(sys.argv) > 2 else None
    suffix = '' if hour is None else '-h%s' % hour
    dwell = os.environ.get('ATHEN_DWELL', '1') == '1'
    d = focus(); c = Client()
    await start_play(c, d, hour)
    report = dict(purpose=__doc__.strip().splitlines()[0], utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), loadAverage=os.getloadavg(),
                  settings=read('settings.json'), environment=read('environment.json'), time=read('time-state.json'), captures=[], dwell=[])
    assert report['settings']['renderScale'] == 1 and report['environment']['actorCount'] >= 9, report['environment']
    if stage in ('stills', 'fixed', 'all'):
        for name in FIXED:
            await c.command({'action': 'view', 'camera': name}); await asyncio.sleep(1.0)
            report['captures'].append(await shot(c, name + suffix))
            if dwell: report['dwell'].append(dict(view=name, **await profile(c, 6)))
            print(name, flush=True)
    if stage in ('stills', 'players', 'all'):
        await c.command({'action': 'view', 'camera': 'follow'}); await asyncio.sleep(.5)
        await c.command({'action': 'goto', 'landmark': 'west_gate'}); await asyncio.sleep(.6)
        # Start at the west gate (reset) and walk the whole way with real keys: hill stairs, south court, then the avenue lane to the frontage.
        await c.command({'action': 'reset'}); await asyncio.sleep(.6)
        report['approachRoute'] = {}
        for name, pos in APPROACH:
            report['approachRoute'][name] = await walk_to(c, d, pos, .3, 70)
        for name, pos, look, note in PLAYER_VIEWS:
            actual = (await walk_to(c, d, pos, .3, 70))['position']
            dx = look[0] - actual[0]; dz = look[2] - actual[2]; dy = look[1] - (actual[1] + 1.65)
            yaw = math.degrees(math.atan2(dx, dz)); pitch = -math.degrees(math.atan2(dy, math.hypot(dx, dz)))
            await c.command({'action': 'cameraBoom', 'boom': 0}); await c.command({'action': 'cameraYaw', 'yaw': yaw}); await c.command({'action': 'cameraPitch', 'pitch': pitch})
            await asyncio.sleep(1.2)
            rec = await shot(c, name + suffix, note); rec.update(standTarget=pos, yaw=yaw, pitch=pitch); report['captures'].append(rec)
            if dwell: report['dwell'].append(dict(view=name, **await profile(c, 6)))
            print(name, flush=True)
            await c.command({'action': 'cameraBoom', 'boom': 0})
        await c.command({'action': 'cameraBoom', 'boom': 5})
    if stage in ('mem', 'all'):
        await c.command({'action': 'memorySnapshot'}); report['memory'] = read('memory.json')
    report['complete'] = True
    (OUT / ('tool-exchange-captures-%s%s.json' % (stage, suffix))).write_text(json.dumps(report, indent=2))
    print('done')

if __name__ == '__main__':
    asyncio.run(main())
