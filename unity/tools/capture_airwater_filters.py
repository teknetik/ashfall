"""Matched native Air + Water three-filter-bank captures, dwell cost, and real-key traversal (29 Sep 2026, task t_3041b425).

Run against a development player launched by launch_phase1_qa.py (then float_player_window.sh <pid>):
  ATHEN_NATIVE_DIR=<evidence>/<tag>-native ATHEN_NATIVE_PID=<pid> DISPLAY=:0 \\
    uv run --offline --with python-xlib --with pillow python capture_airwater_filters.py <fixed|players|traverse|mem|all> [video-name]

Air + Water building pivot (-20.6, 0.5, -9.0), yaw 90. Building-local +X (screen-right from the avenue) = world +Z, local +Z (avenue) = world +X.
So a fitting at building-local (lx, lz) is at world (-20.6 + lz, -9.0 + lx). Vessels at lx 0.9/1.7/2.5 -> world z -8.1/-7.3/-6.5; front line of the new
fittings lz 3.23 -> world x -17.37; wall plane lz 2.73 -> x -17.87; door reveal lx -0.15 -> z -9.15. Porch top world y 0.5.
Diagnostic cameras never qualify traversal. Player-height views use the real follow camera in first person (1.65 m eye) and are reached
with real keyboard walking (positions are recorded, not assumed). Each stand position is captured at 08:00, 12:00 and 16:00 with the day clock
paused; the 6 s dwell profile runs at noon only. No scene state is written.
"""
import asyncio, json, math, os, subprocess, sys, time
from pathlib import Path
from Xlib import X
from native_client import Client
from desktop_input import focus, key
from capture_tool_exchange_display import OUT, snap, read, shot, profile, walk_to, start_play

HOURS = [8, 12, 16]
FIXED = ['cam_audit_air_water_front', 'cam_audit_air_water_door', 'cam_audit_air_water_side_right', 'cam_audit_air_water_side_left']
# name, stand (world), look-at (world), note. Label plates sit at building-local y 1.14..1.20 (world 1.64..1.70); valve stem local y 2.12 (world 2.62).
PLAYER_VIEWS = [
    ('fp_front_lane', (-13.0, 0.0, -7.3), (-17.5, 1.8, -7.3), 'avenue lane, whole bank from 4.5 m'),
    ('fp_door_approach', (-16.4, 0.5, -9.9), (-17.9, 1.5, -8.0), 'porch in front of the door, bank at the right of frame'),
    ('fp_close_1p6', (-15.8, 0.5, -7.3), (-17.6, 1.7, -7.3), 'porch, 1.6 m from the fittings front (vessel 2)'),
    ('fp_label', (-16.6, 0.5, -8.1), (-17.42, 1.68, -8.1), 'porch, 0.8 m from the FILTER 1 plate'),
    ('fp_joints_shoulder', (-16.5, 0.5, -7.0), (-17.5, 1.45, -7.3), 'porch, straps/cradle/inlet joints of vessel 2'),
    ('fp_valve', (-16.6, 0.5, -6.3), (-17.59, 2.45, -6.24), 'porch, isolation valve, lever and gauge'),
    ('fp_oblique_left', (-15.6, 0.5, -10.3), (-17.6, 1.5, -7.3), 'oblique from the door side'),
    ('fp_oblique_right', (-15.6, 0.5, -4.6), (-17.6, 1.5, -7.3), 'oblique from the far side'),
]
# Route validated on 9 Sep (check_relay_airwater_proximity.py): west lane, north lanes, then south along x=-12 to the Air + Water lane.
APPROACH = [('west_lane', (12, 0, 0)), ('north_west_lane', (12, 0, -22.8)), ('north_east_lane', (-12, 0, -22.8)), ('aw_lane', (-12, 0, -9.0))]
# Traversal legs: (name, target). Entrance/porch clearance: onto the porch, along the whole bank, to the door and off again.
LEGS = [('lane_to_bank', (-13, 0, -7.3)), ('onto_porch_at_vessel2', (-16.4, .5, -7.3)), ('porch_to_valve_end', (-16.4, .5, -6.0)),
        ('porch_back_past_vessels', (-16.4, .5, -8.4)), ('porch_front_of_door', (-16.4, .5, -9.3)), ('porch_close_to_wall_at_door', (-17.05, .5, -9.3)),
        ('porch_beside_bank_tight', (-17.05, .5, -7.3)), ('off_porch_lane', (-13, 0, -9.3)), ('lane_south_of_frontage', (-13, 0, -14.5))]


async def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else 'all'
    video = sys.argv[2] if len(sys.argv) > 2 else 'approach'
    dwell = os.environ.get('ATHEN_DWELL', '1') == '1'
    d = focus(); c = Client()
    await start_play(c, d, None)
    report = dict(purpose=__doc__.strip().splitlines()[0], utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), loadAverage=os.getloadavg(),
                  settings=read('settings.json'), environment=read('environment.json'), captures=[], dwell=[], hours=HOURS)
    assert report['settings']['renderScale'] == 1 and report['environment']['actorCount'] >= 9, report['environment']

    async def set_hour(h):
        await c.command({'action': 'timeSet', 'hour': float(h)}); await c.command({'action': 'timePause', 'paused': True}); await asyncio.sleep(3)
        await c.command({'action': 'timeState'}); return read('time-state.json')

    if stage in ('fixed', 'all'):
        for h in HOURS:
            ts = await set_hour(h)
            for name in FIXED:
                await c.command({'action': 'view', 'camera': name}); await asyncio.sleep(1.0)
                rec = await shot(c, '%s-h%02d' % (name, h)); rec['lighting'] = ts; report['captures'].append(rec)
                if dwell and h == 12: report['dwell'].append(dict(view=name, **await profile(c, 6)))
                print(name, h, flush=True)
        await c.command({'action': 'view', 'camera': 'follow'})
    if stage in ('players', 'all'):
        await c.command({'action': 'view', 'camera': 'follow'}); await asyncio.sleep(.5)
        await c.command({'action': 'reset'}); await asyncio.sleep(.6)
        await set_hour(12)
        report['approachRoute'] = {}
        for name, pos in APPROACH: report['approachRoute'][name] = await walk_to(c, d, pos, .3, 70)
        for name, pos, look, note in PLAYER_VIEWS:
            actual = (await walk_to(c, d, pos, .3, 70))['position']
            dx = look[0] - actual[0]; dz = look[2] - actual[2]; dy = look[1] - (actual[1] + 1.65)
            yaw = math.degrees(math.atan2(dx, dz)); pitch = -math.degrees(math.atan2(dy, math.hypot(dx, dz)))
            await c.command({'action': 'cameraBoom', 'boom': 0}); await c.command({'action': 'cameraYaw', 'yaw': yaw}); await c.command({'action': 'cameraPitch', 'pitch': pitch})
            await asyncio.sleep(1.2)
            for h in HOURS:
                ts = await set_hour(h)
                rec = await shot(c, '%s-h%02d' % (name, h), note); rec.update(standTarget=pos, yaw=yaw, pitch=pitch, lighting=ts); report['captures'].append(rec)
                if dwell and h == 12: report['dwell'].append(dict(view=name, **await profile(c, 6)))
            print(name, flush=True)
            await c.command({'action': 'cameraBoom', 'boom': 0})
        await c.command({'action': 'cameraBoom', 'boom': 5})
    if stage == 'traverse':
        # Real-input entrance/porch traversal with a recorded moving first-person approach.
        await c.command({'action': 'view', 'camera': 'follow'}); await c.command({'action': 'cameraBoom', 'boom': 4}); await c.command({'action': 'reset'}); await asyncio.sleep(1)
        await set_hour(12)
        report['approachRoute'] = {}
        for name, pos in APPROACH: report['approachRoute'][name] = await walk_to(c, d, pos, .3, 70)
        d2, w = None, None
        root = d.screen().root
        for wid in root.get_full_property(d.intern_atom('_NET_CLIENT_LIST'), X.AnyPropertyType).value:
            ww = d.create_resource_object('window', wid); pid = ww.get_full_property(d.intern_atom('_NET_WM_PID'), X.AnyPropertyType)
            if pid is not None and int(pid.value[0]) == int(os.environ['ATHEN_NATIVE_PID']): w = ww; break
        assert w is not None
        origin = root.translate_coords(w, 0, 0)
        path = OUT / (video + '.mp4'); assert not path.exists(), 'preserve previous recording'
        ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'x11grab', '-framerate', '30', '-video_size', '1920x1080', '-i', os.environ.get('DISPLAY', ':0') + '+%d,%d' % (origin.x, origin.y),
                               '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', str(path)], stdin=subprocess.PIPE)
        await asyncio.sleep(1)
        report['legs'] = {}
        try:
            await c.command({'action': 'cameraBoom', 'boom': 0}); await c.command({'action': 'cameraPitch', 'pitch': 8})
            for name, pos in LEGS:
                t0 = time.monotonic(); r = await walk_to(c, d, pos, .3, 40); r['seconds'] = time.monotonic() - t0; report['legs'][name] = r
                await c.command({'action': 'cameraPitch', 'pitch': 8}); await asyncio.sleep(.4)
                print(name, r['position'], flush=True)
        finally:
            ff.communicate(b'q'); ff.wait(timeout=20)
            await c.command({'action': 'cameraBoom', 'boom': 5})
        report['video'] = path.name
    if stage in ('mem', 'all'):
        await c.command({'action': 'memorySnapshot'}); report['memory'] = read('memory.json')
    report['complete'] = True
    (OUT / ('airwater-captures-%s.json' % stage)).write_text(json.dumps(report, indent=2))
    print('done')

if __name__ == '__main__':
    asyncio.run(main())
