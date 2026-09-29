"""Matched native Basic General counter captures, dwell cost and Mira trade route (29 Sep 2026).

Run against a development player launched by launch_phase1_qa.py:
  ATHEN_NATIVE_DIR=<evidence>/<tag>-native ATHEN_NATIVE_PID=<pid> DISPLAY=:0 \
    uv run --offline --with python-xlib --with pillow python capture_basic_general_counter.py <tag-dir> [stills|dwell|trade|all]

Diagnostic cameras never qualify traversal. Player-height views use the real follow camera in first person and
are reached with real keyboard walking (positions are recorded, not assumed). No scene state is written.
"""
import asyncio, hashlib, json, math, os, statistics, sys, time
from pathlib import Path
from PIL import Image
from native_client import Client
from desktop_input import focus, key

OUT = Path(os.environ['ATHEN_NATIVE_DIR'])
FIXED = ['cam_audit_basic_general_front', 'cam_audit_basic_general_door', 'cam_audit_basic_general_side_left', 'cam_audit_basic_general_side_right']
# name, stand position (x,y,z), look-at point, first-person? All at street/porch level; eye height is the game's own 1.65 m.
PLAYER_VIEWS = [
    ('fp_street_centre', (8.0, 0.0, 19.2), (8.0, 1.25, 14.2), 'Mira and both stock bays from the avenue lane'),
    ('fp_street_left', (6.2, 0.0, 18.8), (8.0, 1.25, 14.2), 'left oblique: Mira not in front of the left bay'),
    ('fp_street_right', (9.8, 0.0, 18.8), (8.0, 1.25, 14.2), 'right oblique'),
    ('fp_porch_counter', (8.0, 0.5, 17.4), (8.0, 1.15, 14.2), 'porch interaction pose, counter first person'),
]


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


async def walk_to(c, d, target, tol=.3):
    started = time.monotonic(); last = 999; stalls = 0
    while True:
        s = snap(); p = s['player']['position']; dx = target[0] - p[0]; dz = target[2] - p[2]; dist = math.hypot(dx, dz)
        if dist < tol: return p
        if time.monotonic() - started > 40: raise RuntimeError('timeout walking to %s at %s' % (target, p))
        stalls = stalls + 1 if abs(last - dist) < .01 else 0
        if stalls >= 5: raise RuntimeError('blocked before %s at %s' % (target, p))
        last = dist
        await c.command({'action': 'cameraYaw', 'yaw': math.degrees(math.atan2(dx, dz))}); await asyncio.sleep(.08)
        key(d, 'w', True)
        try: await asyncio.sleep(min(2, max(.025, (dist - .1) / 3.4)))
        finally: key(d, 'w', False)
        await asyncio.sleep(.1)


async def start_play(c, d):
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
    await c.command({'action': 'timeReset'}); await c.command({'action': 'timePause', 'paused': True}); await c.command({'action': 'timeState'})
    await c.command({'action': 'settingsSnapshot'})


async def shot(c, name, sub, extra=None):
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
    stage = sys.argv[2] if len(sys.argv) > 2 else 'all'
    d = focus(); c = Client(); report_path = OUT / 'basic-general-captures.json'
    await start_play(c, d)
    load = os.getloadavg()
    report = dict(purpose=__doc__.strip().splitlines()[0], utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), loadAverage=load,
                  settings=read('settings.json'), environment=read('environment.json'), time=read('time-state.json'), captures=[], dwell=[])
    assert report['settings']['renderScale'] == 1 and report['environment']['actorCount'] >= 9, report['environment']
    if stage in ('stills', 'fixed', 'all'):
        for name in FIXED:
            await c.command({'action': 'view', 'camera': name}); await asyncio.sleep(1.0)
            report['captures'].append(await shot(c, name, 'fixed'))
            report['dwell'].append(dict(view=name, **await profile(c, 6))); print(name, flush=True)
            print(name, flush=True)
        pass
    if stage in ('stills', 'players', 'all'):
        await c.command({'action': 'view', 'camera': 'follow'}); await asyncio.sleep(.5)
        await c.command({'action': 'goto', 'landmark': 'basic_general'}); await asyncio.sleep(.6)
        for name, pos, look, note in PLAYER_VIEWS:
            actual = await walk_to(c, d, pos)
            dx = look[0] - actual[0]; dz = look[2] - actual[2]; dy = look[1] - (actual[1] + 1.65)
            yaw = math.degrees(math.atan2(dx, dz)); pitch = -math.degrees(math.atan2(dy, math.hypot(dx, dz)))
            await c.command({'action': 'cameraBoom', 'boom': 0}); await c.command({'action': 'cameraYaw', 'yaw': yaw}); await c.command({'action': 'cameraPitch', 'pitch': pitch})
            await asyncio.sleep(1.2)
            rec = await shot(c, name, 'player', note); rec.update(standTarget=pos, yaw=yaw, pitch=pitch); report['captures'].append(rec)
            report['dwell'].append(dict(view=name, **await profile(c, 6))); print(name, flush=True)
        await c.command({'action': 'cameraBoom', 'boom': 5})
    if stage in ('mem', 'all'):
        await c.command({'action': 'memorySnapshot'}); report['memory'] = read('memory.json')
    report['complete'] = True
    (OUT / ('basic-general-captures-%s.json' % stage)).write_text(json.dumps(report, indent=2))
    print('done')

asyncio.run(main())
