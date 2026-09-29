"""Matched native Tool Exchange practical-light captures (task t_e14abefb, 29 Sep 2026).

  ATHEN_NATIVE_DIR=<evidence>/<tag>-native ATHEN_NATIVE_PID=<pid> DISPLAY=:0 \\
    uv run --offline --with python-xlib --with pillow python capture_tool_exchange_light.py

Walks once with real keys from the west gate (same retained route as capture_tool_exchange_display.py), then at each player-height view
sets the paused day clock to each hour, captures 1920x1080, and dwells 6 s for a local frame-cost profile. No scene state is written.
"""
import asyncio, json, math, os, time
import capture_tool_exchange_display as base
from capture_tool_exchange_display import OUT, read, shot, profile, walk_to, start_play, APPROACH, PLAYER_VIEWS
from native_client import Client
from desktop_input import focus

HOURS = [float(h) for h in os.environ.get('ATHEN_HOURS', '17,20.5,12').split(',')]
KEEP = ['fp_front_lane', 'fp_door_porch', 'fp_display_close']


async def main():
    d = focus(); c = Client()
    await start_play(c, d, None)
    report = dict(purpose=__doc__.strip().splitlines()[0], utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), loadAverage=os.getloadavg(),
                  settings=read('settings.json'), environment=read('environment.json'), captures=[], dwell=[], hours=HOURS)
    await c.command({'action': 'view', 'camera': 'follow'}); await asyncio.sleep(.5)
    await c.command({'action': 'goto', 'landmark': 'west_gate'}); await asyncio.sleep(.6)
    await c.command({'action': 'reset'}); await asyncio.sleep(.6)
    report['approachRoute'] = {}
    for name, pos in APPROACH:
        report['approachRoute'][name] = await walk_to(c, d, pos, .3, 70)
    for name, pos, look, note in [v for v in PLAYER_VIEWS if v[0] in KEEP]:
        actual = (await walk_to(c, d, pos, .3, 70))['position']
        dx = look[0] - actual[0]; dz = look[2] - actual[2]; dy = look[1] - (actual[1] + 1.65)
        yaw = math.degrees(math.atan2(dx, dz)); pitch = -math.degrees(math.atan2(dy, math.hypot(dx, dz)))
        await c.command({'action': 'cameraBoom', 'boom': 0}); await c.command({'action': 'cameraYaw', 'yaw': yaw}); await c.command({'action': 'cameraPitch', 'pitch': pitch})
        for h in HOURS:
            await c.command({'action': 'timeSet', 'hour': h}); await c.command({'action': 'timePause', 'paused': True}); await asyncio.sleep(1.5)
            tag = '%s-h%s' % (name, ('%g' % h))
            rec = await shot(c, tag, note); rec.update(standTarget=pos, yaw=yaw, pitch=pitch, hour=h); report['captures'].append(rec)
            report['dwell'].append(dict(view=tag, **await profile(c, 6)))
            print(tag, flush=True)
    await c.command({'action': 'timeState'}); report['timeState'] = read('time-state.json')
    report['complete'] = True
    (OUT / 'tool-exchange-light-captures.json').write_text(json.dumps(report, indent=2))
    print('done')

if __name__ == '__main__':
    asyncio.run(main())
