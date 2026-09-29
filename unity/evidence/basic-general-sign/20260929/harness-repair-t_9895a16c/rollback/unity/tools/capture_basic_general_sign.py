"""Matched native Basic General sign captures at three times of day, dwell cost, and a moving-approach video (29 Sep 2026).

Run against a development player launched by launch_phase1_qa.py:
  ATHEN_NATIVE_DIR=<evidence>/<tag>-native ATHEN_NATIVE_PID=<pid> DISPLAY=:0 \\
    uv run --offline --with python-xlib --with pillow python capture_basic_general_sign.py <stills|approach|mem|all> [video-name] [x11-window-id]

Diagnostic cameras never qualify traversal. Player-height views use the real follow camera in first person and are reached with real
keyboard walking (positions are recorded, not assumed). Only the day clock and start position use the bridge. No scene state is written.
Stage `stills` walks the retained salvage route from the west gate to the sign once and captures every view at 12:00 (noon sun),
17:00 (authored dusk) and 20:30 (night, emission), with 6 s dwell timing at the authored hour only.
"""
import asyncio, json, math, os, subprocess, sys, time
from pathlib import Path
from native_client import Client
from desktop_input import focus, key
import hashlib
from PIL import Image
from capture_tool_exchange_display import walk_to, snap, read, profile, OUT

FIXED = ['cam_audit_basic_general_front', 'cam_audit_basic_general_door', 'cam_audit_basic_general_side_left']
HOURS = [('noon', 12.0), ('dusk', 17.0), ('night', 20.5)]
AUTHORED = 'dusk'
# Salvage route from the west gate to the Basic General lane (retained, walked on foot).
APPROACH = [('west_stair_approach', (12, 0, 0)), ('hill_tree', (4, 1.5, 0)), ('hill_southwest', (4, 1.5, 4)), ('south_stair_top', (0, 1.5, 4)),
            ('south_stair_bottom', (0, 0, 12)), ('general_clear_lane', (0, 0, 21)), ('general_front_lane', (8, 0, 21))]
# name, stand position, look-at point, note. Sign face centre is world (8.0, ~3.0, 16.9); eye height is the game's own 1.65 m.
SIGN = (8.0, 3.0, 16.9)
PLAYER_VIEWS = [
    ('fp_sign_far', (8.0, 0.0, 26.0), SIGN, 'south court, 9 m from the sign'),
    ('fp_sign_street', (8.0, 0.0, 20.0), SIGN, 'avenue lane, about 3.5 m from the sign face'),
    ('fp_sign_left', (6.2, 0.0, 18.8), SIGN, 'left oblique from the lane'),
    ('fp_sign_right', (9.8, 0.0, 18.8), SIGN, 'right oblique from the lane'),
    ('fp_sign_porch', (8.0, 0.5, 17.8), SIGN, 'porch at the interaction pose, sign directly overhead-front, about 1 m'),
]


async def shot(c, name, extra=None):
    await c.command({'action': 'capture', 'name': name}); path = OUT / (name + '.png')
    for _ in range(120):
        try:
            with Image.open(path) as im: im.load(); assert im.size == (1920, 1080), im.size
            break
        except (FileNotFoundError, OSError, SyntaxError): await asyncio.sleep(.15)
    else: raise TimeoutError(name)
    s = snap(); assert [s['width'], s['height']] == [1920, 1080], (s['width'], s['height']); assert s['session']['state'] == 'Play'
    return dict(name=name, path=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(), player=s['player'], camera=s.get('camera'), notes=extra)


async def aim(c, actual, look):
    dx = look[0] - actual[0]; dz = look[2] - actual[2]; dy = look[1] - (actual[1] + 1.65)
    yaw = math.degrees(math.atan2(dx, dz)); pitch = -math.degrees(math.atan2(dy, math.hypot(dx, dz)))
    await c.command({'action': 'cameraBoom', 'boom': 0}); await c.command({'action': 'cameraYaw', 'yaw': yaw}); await c.command({'action': 'cameraPitch', 'pitch': pitch})
    return yaw, pitch


async def start(c, d):
    for _ in range(600):
        if (OUT / 'snapshot.json').exists(): break
        await asyncio.sleep(.1)
    async def tap(name, seconds=.12, settle=1.5):
        key(d, name, True)
        try: await asyncio.sleep(seconds)
        finally: key(d, name, False)
        await asyncio.sleep(settle)
    if snap()['session']['state'] == 'MainMenu':
        for _ in range(8):
            await tap('Return')
            if snap()['session']['state'] != 'MainMenu': break
    for _ in range(300):
        if snap()['session']['state'] == 'Play': break
        await asyncio.sleep(.1)
    assert snap()['session']['state'] == 'Play', snap()['session']
    for k in ['w', 'a', 's', 'd', 'e', 'Return', 'Escape']: key(d, k, False)
    await c.command({'action': 'resize', 'width': 1920, 'height': 1080}); await asyncio.sleep(2)
    await c.command({'action': 'timeReset'}); await c.command({'action': 'timePause', 'paused': True}); await c.command({'action': 'timeState'})
    await c.command({'action': 'settingsSnapshot'})


async def set_hour(c, hour):
    await c.command({'action': 'timeSet', 'hour': float(hour)}); await c.command({'action': 'timePause', 'paused': True}); await asyncio.sleep(1.0)


async def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else 'all'
    video = sys.argv[2] if len(sys.argv) > 2 else 'approach'; window = sys.argv[3] if len(sys.argv) > 3 else None
    d = focus(); c = Client(); await start(c, d)
    report = dict(purpose=__doc__.strip().splitlines()[0], utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), loadAverage=os.getloadavg(),
                  settings=read('settings.json'), environment=read('environment.json'), time=read('time-state.json'), captures=[], dwell=[], approachRoute={})
    assert report['settings']['renderScale'] == 1 and report['environment']['actorCount'] >= 9, report['environment']
    if stage in ('stills', 'all'):
        for name in FIXED:
            await c.command({'action': 'view', 'camera': name})
            for hn, h in HOURS:
                await set_hour(c, h); report['captures'].append(dict(hour=hn, **await shot(c, '%s-%s' % (name, hn))))
                if hn == AUTHORED: report['dwell'].append(dict(view=name, hour=hn, **await profile(c, 6)))
            print(name, flush=True)
        await c.command({'action': 'view', 'camera': 'follow'}); await asyncio.sleep(.5)
        await c.command({'action': 'reset'}); await asyncio.sleep(.8)
        await set_hour(c, 17.0)
        for name, pos in APPROACH: report['approachRoute'][name] = await walk_to(c, d, pos, .3, 70)
        for name, pos, look, note in PLAYER_VIEWS:
            if pos[2] < 21: await walk_to(c, d, (pos[0], 0.0, 21.0), .3, 70)   # square up on the lane first, then step straight in
            actual = (await walk_to(c, d, pos, .3, 70))['position']
            yaw, pitch = await aim(c, actual, look); await asyncio.sleep(.6)
            for hn, h in HOURS:
                await set_hour(c, h); await c.command({'action': 'cameraPitch', 'pitch': pitch}); await asyncio.sleep(.4)
                rec = await shot(c, '%s-%s' % (name, hn), note); rec.update(hour=hn, standTarget=pos, yaw=yaw, pitch=pitch); report['captures'].append(rec)
                if hn == AUTHORED: report['dwell'].append(dict(view=name, hour=hn, **await profile(c, 6)))
            print(name, flush=True)
        await c.command({'action': 'cameraBoom', 'boom': 5}); await set_hour(c, 17.0)
    if stage in ('approach', 'all'):
        # Moving approach: fresh reset, salvage route on foot, then record the last walk to the porch (diagonal from the south-west, then straight).
        await c.command({'action': 'view', 'camera': 'follow'}); await c.command({'action': 'cameraBoom', 'boom': 4}); await c.command({'action': 'reset'}); await asyncio.sleep(1)
        await set_hour(c, 17.0)
        for name, pos in APPROACH[:-1]: report['approachRoute'][name] = await walk_to(c, d, pos, .3, 70)
        report['approachRoute']['court_start'] = await walk_to(c, d, (3.0, 0, 27.0), .3, 60)
        ff = None
        if window:
            ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'x11grab', '-framerate', '30', '-window_id', window, '-i', os.environ.get('DISPLAY', ':0'),
                                   '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', str(OUT / (video + '.mp4'))], stdin=subprocess.PIPE)
            await asyncio.sleep(1)
        legs = {}
        try:
            await c.command({'action': 'cameraBoom', 'boom': 0}); await c.command({'action': 'cameraPitch', 'pitch': -14})
            for name, pos in [('diagonal_to_lane', (8.0, 0, 20.0)), ('lane_to_porch', (8.0, .5, 17.9))]:
                t0 = time.monotonic(); legs[name] = await walk_to(c, d, pos, .3, 40); legs[name]['seconds'] = time.monotonic() - t0
                await c.command({'action': 'cameraPitch', 'pitch': -14}); await asyncio.sleep(.5)
            await asyncio.sleep(2.0)
        finally:
            if ff: ff.communicate(b'q'); ff.wait(timeout=20)
            await c.command({'action': 'cameraBoom', 'boom': 5})
        report['approachLegs'] = legs; report['video'] = video + '.mp4' if window else None
    if stage in ('mem', 'all'):
        await c.command({'action': 'memorySnapshot'}); report['memory'] = read('memory.json')
    report['complete'] = True
    (OUT / ('basic-general-sign-%s.json' % stage)).write_text(json.dumps(report, indent=2))
    print('done')

if __name__ == '__main__':
    asyncio.run(main())
