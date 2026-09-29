"""Matched native Basic General counter-face / back-panel captures at 08/12/16 with a noon dwell profile (29 Sep 2026, task t_6f2addb6).

Run against a development player launched by launch_phase1_qa.py (then float_player_window.sh <pid>):
  ATHEN_NATIVE_DIR=<evidence>/<tag>-native ATHEN_NATIVE_PID=<pid> DISPLAY=:0 \\
    uv run --offline --with python-xlib --with pillow python capture_basic_general_face.py [stills|mem|all]

Player-height views use the real follow camera in first person (1.65 m eye) reached with real keyboard walking; the day clock is paused at
each hour. Mira stays at her root (8.0, 0.5, 15.8). No scene state is written.
"""
import asyncio, json, math, os, sys, time
from capture_tool_exchange_display import OUT, read, shot, profile, walk_to, start_play
from native_client import Client
from desktop_input import focus

HOURS = [8, 12, 16]
# name, stand (x,y,z), look-at, note. Counter face front plane about z 14.5, back wall plane about z 13.5, Mira root z 15.8.
PLAYER_VIEWS = [
    ('fp_street_left', (6.2, 0.0, 18.8), (8.0, 1.25, 14.2), 'left oblique from the avenue, Mira clear of the left bay'),
    ('fp_street_right', (9.8, 0.0, 18.8), (8.0, 1.25, 14.2), 'right oblique from the avenue'),
    ('fp_porch_counter', (8.0, 0.5, 17.4), (8.0, 1.15, 14.2), 'porch interaction pose, Mira central'),
    ('fp_face_left', (5.9, 0.5, 16.9), (7.3, 0.95, 14.4), 'porch, oblique onto the left counter-face panel, Mira to the right of frame'),
    ('fp_face_right', (10.1, 0.5, 16.9), (8.7, 0.95, 14.4), 'porch, oblique onto the right counter-face panel'),
    ('fp_back_panel', (8.0, 0.5, 17.4), (8.0, 1.9, 13.6), 'porch, raised look at the central back panel behind Mira'),
]


async def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else 'all'
    d = focus(); c = Client()
    await start_play(c, d, None)
    report = dict(purpose=__doc__.strip().splitlines()[0], utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), loadAverage=os.getloadavg(),
                  settings=read('settings.json'), environment=read('environment.json'), captures=[], dwell=[], hours=HOURS)
    assert report['settings']['renderScale'] == 1 and report['environment']['actorCount'] >= 9, report['environment']

    async def set_hour(h):
        await c.command({'action': 'timeSet', 'hour': float(h)}); await c.command({'action': 'timePause', 'paused': True}); await asyncio.sleep(3)
        await c.command({'action': 'timeState'}); return read('time-state.json')

    if stage in ('stills', 'all'):
        await c.command({'action': 'view', 'camera': 'follow'}); await asyncio.sleep(.5)
        await c.command({'action': 'goto', 'landmark': 'basic_general'}); await asyncio.sleep(.6)
        for name, pos, look, note in PLAYER_VIEWS:
            actual = (await walk_to(c, d, pos, .3, 70))['position']
            dx = look[0] - actual[0]; dz = look[2] - actual[2]; dy = look[1] - (actual[1] + 1.65)
            yaw = math.degrees(math.atan2(dx, dz)); pitch = -math.degrees(math.atan2(dy, math.hypot(dx, dz)))
            await c.command({'action': 'cameraBoom', 'boom': 0}); await c.command({'action': 'cameraYaw', 'yaw': yaw}); await c.command({'action': 'cameraPitch', 'pitch': pitch})
            await asyncio.sleep(1.2)
            for h in HOURS:
                ts = await set_hour(h)
                rec = await shot(c, '%s-h%02d' % (name, h), note); rec.update(standTarget=pos, yaw=yaw, pitch=pitch, lighting=ts); report['captures'].append(rec)
                if h == 12: report['dwell'].append(dict(view=name, **await profile(c, 6)))
            print(name, flush=True)
        await c.command({'action': 'cameraBoom', 'boom': 5})
    if stage in ('mem', 'all'):
        await c.command({'action': 'memorySnapshot'}); report['memory'] = read('memory.json')
    report['complete'] = True
    (OUT / ('face-captures-%s.json' % stage)).write_text(json.dumps(report, indent=2))
    print('done')

if __name__ == '__main__':
    asyncio.run(main())
