"""Real-input Vanguard Hall traversal, Vex regression prompt, moving video and night portal stills (30 Sep 2026).

  ATHEN_NATIVE_DIR=<evidence>/<tag>-native ATHEN_NATIVE_PID=<pid> DISPLAY=:0 \\
    uv run --offline --with python-xlib --with pillow python check_vanguard_hall_traversal.py [video-name]

1. Reset at the west gate; Vex's prompt must be live, E opens his dialogue, movement is blocked while modal, Escape closes it.
2. Walk (real W key, yaw set per step) the retained west-lane route to the plaza south of the hall, then record a moving
   approach: plaza -> front step -> podium terrace -> portal recess at the doors -> terrace east -> off the podium -> east side ->
   back to the front -> west side (outside the relocated salvage) -> rear -> rear service step and podium -> back off -> plaza.
   Any stall (no progress for ~6 steps) raises. Heights are recorded from the player snapshot (podium 0.5, step 0.25).
3. Night check: paused clock at 20:30, first-person stills from the terrace and in the portal recess (city light circuit
   distance culling is exercised by the real player position), then 17:00 first-person stills at the same spots.
No scene state is written; only the development bridge's reset/time/camera commands are used.
"""
import asyncio, json, math, os, subprocess, sys, time
from pathlib import Path
from native_client import Client
from desktop_input import focus, key

OUT = Path(os.environ['ATHEN_NATIVE_DIR'])
PID = int(os.environ.get('ATHEN_NATIVE_PID', '0'))

APPROACH = [('west_stair_approach', (12, 0, 0)), ('west_lane_general_clear', (13, 0, 12)), ('west_lane_mid', (13, 0, -12)),
            ('west_lane_north', (13, 0, -22)), ('plaza_east', (0, 0, -20))]
LEGS = [('plaza_front', (-10, 0, -19.5)), ('front_step', (-10, .25, -23.9)), ('terrace', (-10, .5, -25.3)),
        ('portal_recess', (-10, .5, -27.15)), ('terrace_east', (-4.6, .5, -25.0)), ('off_podium_east', (-3.1, 0, -25.0)),
        ('east_side', (-3.1, 0, -32.6)), ('east_back_to_front', (-3.1, 0, -23.2)), ('front_west', (-19.2, 0, -23.2)),
        ('west_side', (-19.2, 0, -31.0)), ('rear_west', (-19.2, 0, -37.4)), ('rear_mid', (-8.25, 0, -37.4)),
        ('rear_step', (-8.25, .25, -36.35)), ('rear_podium', (-8.25, .5, -35.55)), ('rear_off', (-8.25, 0, -37.6)),
        ('rear_west_return', (-19.2, 0, -37.4)), ('west_return', (-19.2, 0, -23.2)), ('plaza_return', (-10, 0, -20.5))]
STILLS = [('fp_terrace', (-10, .5, -24.9), (-10, 3.2, -27.5)), ('fp_recess', (-10, .5, -26.4), (-10, 2.4, -28.0)),
          ('fp_terrace_lamp_east', (-7.4, .5, -24.7), (-7.55, 3.0, -26.5)), ('fp_plaza', (-10, 0, -17.5), (-10, 6.3, -27.0)),
          ('fp_plaza_oblique', (-3.0, 0, -16.5), (-9.0, 5.5, -27.0))]


def snap(): return json.loads((OUT / 'snapshot.json').read_text())


async def walk_to(c, d, target, tol=.3, limit=45):
    started = time.monotonic(); last = 999; stalls = 0; steps = 0; ys = []
    while True:
        s = snap(); p = s['player']['position']; ys.append(p[1]); dx = target[0] - p[0]; dz = target[2] - p[2]; dist = math.hypot(dx, dz)
        if dist < tol: return dict(reached=True, position=p, samples=steps, minY=min(ys), maxY=max(ys))
        if time.monotonic() - started > limit: raise RuntimeError('timeout walking to %s at %s' % (target, p))
        stalls = stalls + 1 if abs(last - dist) < .01 else 0
        if stalls >= 6: raise RuntimeError('BLOCKED before %s at %s' % (target, p))
        last = dist; steps += 1
        await c.command({'action': 'cameraYaw', 'yaw': math.degrees(math.atan2(dx, dz))}); await asyncio.sleep(.08)
        key(d, 'w', True)
        try: await asyncio.sleep(min(2, max(.025, (dist - .1) / 3.4)))
        finally: key(d, 'w', False)
        await asyncio.sleep(.1)


def hypr_geometry(pid):
    env = dict(os.environ); env.setdefault('XDG_RUNTIME_DIR', '/run/user/%d' % os.getuid())
    try:
        subprocess.run(['bash', '-c', "addr=$(hyprctl clients -j | tr -d '\\n ' | sed 's/},{/}\\n{/g' | grep '\"pid\":%d,' | sed 's/.*\"address\":\"\\([^\"]*\\)\".*/\\1/' | head -1); "
                        "hyprctl dispatch \"hl.dsp.window.move({ x = 2500, y = 80, window = 'address:$addr' })\" >/dev/null" % pid], env=env, timeout=10)
        time.sleep(1)
        for c in json.loads(subprocess.run(['hyprctl', 'clients', '-j'], env=env, capture_output=True, text=True, timeout=10).stdout):
            if c.get('pid') == pid: return (c['at'][0], c['at'][1], c['size'][0], c['size'][1])
    except Exception as e:
        print('geometry failed', e, flush=True)
    return None


def window_id(pid):
    from Xlib import display, X
    dp = display.Display(); root = dp.screen().root; atom = dp.intern_atom('_NET_WM_PID')
    stack = [root]
    while stack:
        w = stack.pop()
        try:
            prop = w.get_full_property(atom, X.AnyPropertyType)
            if prop and prop.value and prop.value[0] == pid and w.get_geometry().width >= 800:
                g = w.get_geometry(); t = w.translate_coords(root, 0, 0)
                return dict(id=hex(w.id), x=-t.x, y=-t.y, w=g.width, h=g.height)
            stack.extend(w.query_tree().children)
        except Exception:
            pass
    return None


async def main():
    video = sys.argv[1] if len(sys.argv) > 1 else 'hall-traversal'
    d = focus(); c = Client(); rec = dict(utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), loadAverage=os.getloadavg(), vex={}, approach={}, legs={}, stills={})
    async def tap(name, seconds=.1, settle=.4):
        key(d, name, True)
        try: await asyncio.sleep(seconds)
        finally: key(d, name, False)
        await asyncio.sleep(settle)
    for _ in range(600):
        if (OUT / 'snapshot.json').exists(): break
        await asyncio.sleep(.1)
    if snap()['session']['state'] == 'MainMenu':
        for _ in range(8):
            await tap('Return', .12, 1.5)
            if snap()['session']['state'] != 'MainMenu': break
    for _ in range(300):
        if snap()['session']['state'] == 'Play': break
        await asyncio.sleep(.1)
    assert snap()['session']['state'] == 'Play', snap()['session']
    await c.command({'action': 'resize', 'width': 1920, 'height': 1080}); await asyncio.sleep(2)
    await c.command({'action': 'timeReset'}); await c.command({'action': 'timePause', 'paused': True})
    await c.command({'action': 'view', 'camera': 'follow'}); await c.command({'action': 'cameraBoom', 'boom': 4}); await c.command({'action': 'reset'}); await asyncio.sleep(1)
    # 1. Vex regression
    s = snap(); rec['vex']['spawn'] = s['player']['position']; rec['vex']['prompt'] = s['interaction']
    assert 'Talk to Vex' in s['interaction']['prompt'], s['interaction']
    await tap('e'); s = snap(); rec['vex']['afterE'] = s['session']['state']
    assert s['session']['state'] == 'Dialogue', s['session']
    before = s['player']['position']; await tap('w', .4); rec['vex']['modalMoveM'] = math.dist(before, snap()['player']['position']); assert rec['vex']['modalMoveM'] < .04
    await tap('Escape'); s = snap(); rec['vex']['afterEscape'] = s['session']['state']; assert s['session']['state'] == 'Play', s['session']
    # 2. On foot to the plaza, then the recorded hall circuit
    for name, pos in APPROACH: rec['approach'][name] = await walk_to(c, d, pos, .35, 70)
    # Moving walkthrough: Wayland-native grim frames of the floated player window (x11grab reads black from XWayland GL windows)
    ff = None; frames = OUT / 'frames'; t_video = None
    geo = hypr_geometry(PID) if PID else None; rec['window'] = geo
    if geo:
        frames.mkdir(exist_ok=True)
        cmd = 'i=0; while :; do grim -t jpeg -q 82 -g "%d,%d %dx%d" %s/f$(printf %%05d $i).jpg; i=$((i+1)); done' % (geo[0], geo[1], geo[2], geo[3], frames)
        ff = subprocess.Popen(['bash', '-c', cmd], start_new_session=True); t_video = time.monotonic()
    try:
        await c.command({'action': 'cameraBoom', 'boom': 3}); await c.command({'action': 'cameraPitch', 'pitch': 6})
        for name, pos in LEGS:
            t0 = time.monotonic(); r = await walk_to(c, d, pos, .3, 45); r['seconds'] = round(time.monotonic() - t0, 2); rec['legs'][name] = r
            print('leg', name, r['position'], flush=True)
    finally:
        if ff:
            os.killpg(ff.pid, 15); ff.wait(timeout=10)
            n = len(list(frames.glob('f*.jpg'))); secs = time.monotonic() - t_video; fps = max(1.0, n / secs)
            rec['videoFrames'] = n; rec['videoSeconds'] = round(secs, 1); rec['videoFps'] = round(fps, 2)
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', '%.3f' % fps, '-i', str(frames / 'f%05d.jpg'), '-vf', 'scale=1280:-2',
                            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22', '-pix_fmt', 'yuv420p', str(OUT / (video + '.mp4'))], check=False)
            for f in frames.glob('f*.jpg'):
                if int(f.stem[1:]) % 20: f.unlink()
    # height checks: podium and steps are walkable surfaces at their authored heights
    for name, want in (('front_step', .25), ('terrace', .5), ('portal_recess', .5), ('rear_step', .25), ('rear_podium', .5)):
        y = rec['legs'][name]['position'][1]; rec['legs'][name]['heightOk'] = abs(y - want) < .12
    # 3. First-person stills (night, then the authored 17:00)
    await c.command({'action': 'cameraBoom', 'boom': 0})
    for hour in (20.5, 17.0):
        await c.command({'action': 'timeSet', 'hour': hour}); await c.command({'action': 'timePause', 'paused': True}); await asyncio.sleep(1.5)
        for name, pos, look in STILLS:
            await walk_to(c, d, pos, .25, 30)
            dx, dz = look[0] - pos[0], look[2] - pos[2]
            await c.command({'action': 'cameraYaw', 'yaw': math.degrees(math.atan2(dx, dz))})
            pitch = -math.degrees(math.atan2(look[1] - (pos[1] + 1.65), math.hypot(dx, dz)))
            await c.command({'action': 'cameraPitch', 'pitch': pitch}); await asyncio.sleep(1.2)
            shot = '%s-h%05.2f' % (name, hour)
            await c.command({'action': 'capture', 'name': shot}); await asyncio.sleep(1.2)
            rec['stills'][shot] = snap()['player']['position']
    await c.command({'action': 'cameraBoom', 'boom': 5}); await c.command({'action': 'timeReset'})
    rec['complete'] = True; rec['finalPlayer'] = snap()['player']; rec['video'] = video + '.mp4' if geo else None
    (OUT / (video + '.json')).write_text(json.dumps(rec, indent=2)); print('traversal ok', flush=True)

asyncio.run(main())
