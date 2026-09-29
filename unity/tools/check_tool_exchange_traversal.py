"""Real-input Tool Exchange frontage traversal, Vex prompt and moving-approach video (29 Sep 2026).

  ATHEN_NATIVE_DIR=<evidence>/<tag>-native ATHEN_NATIVE_PID=<pid> DISPLAY=:0 \\
    uv run --offline --with python-xlib --with pillow python check_tool_exchange_traversal.py <video-name> <x11-window-id>

1. Reset at the west gate; Vex's prompt must be live and E must open his dialogue; Escape closes it (real keys). Vex stands at the west gate
   (41.7, 0, -1.5), not at Tool Exchange; this is a regression check of the unchanged NPC root, not proximity to the shop.
2. Walk the retained salvage route to the avenue lane, then record (ffmpeg x11grab of the player window) a moving approach: lane -> display
   -> along the porch past the shutter -> off the porch into the neighbouring lane -> back past the frontage. Any stall raises.
Movement and E/Escape are real X11 key events. Only the start position uses the bridge's reset.
"""
import asyncio, json, math, os, subprocess, sys, time
from pathlib import Path
from native_client import Client
from desktop_input import focus, key
from capture_tool_exchange_display import APPROACH, walk_to, snap, OUT

# Video legs: (name, target). Porch top is y 0.5; the porch collider spans world x -25.08..-14.5, z 5.12..12.88.
LEGS = [('lane_to_display', (-13, 0, 6.85)), ('onto_porch_at_display', (-16.4, .5, 6.85)), ('porch_past_shutter', (-16.4, .5, 10.4)),
        ('porch_north_end', (-16.4, .5, 12.3)), ('off_porch_neighbour_lane', (-13, 0, 14.5)), ('lane_back_past_frontage', (-13, 0, 6.0)),
        ('lane_south_of_frontage', (-13, 0, 3.5))]


async def main():
    video = sys.argv[1] if len(sys.argv) > 1 else 'approach'; window = sys.argv[2] if len(sys.argv) > 2 else None
    d = focus(); c = Client(); rec = dict(utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), loadAverage=os.getloadavg(), vex={}, legs={}, approach={})
    async def tap(name, seconds=.1, settle=.4):
        key(d, name, True)
        try: await asyncio.sleep(seconds)
        finally: key(d, name, False)
        await asyncio.sleep(settle)
    for _ in range(300):
        if (OUT / 'snapshot.json').exists(): break
        await asyncio.sleep(.1)
    if snap()['session']['state'] == 'MainMenu':
        for _ in range(8):
            await tap('Return', .12, 1.5)
            if snap()['session']['state'] != 'MainMenu': break
    assert snap()['session']['state'] == 'Play'
    await c.command({'action': 'resize', 'width': 1920, 'height': 1080}); await asyncio.sleep(2)
    await c.command({'action': 'timeReset'}); await c.command({'action': 'timePause', 'paused': True}); await c.command({'action': 'settingsSnapshot'})
    await c.command({'action': 'view', 'camera': 'follow'}); await c.command({'action': 'cameraBoom', 'boom': 4}); await c.command({'action': 'reset'}); await asyncio.sleep(1)
    # 1. Vex
    s = snap(); rec['vex']['spawn'] = s['player']['position']; rec['vex']['prompt'] = s['interaction']
    assert 'Talk to Vex' in s['interaction']['prompt'], s['interaction']
    await tap('e'); s = snap(); rec['vex']['afterE'] = dict(state=s['session']['state'], npc=s['interaction']['npc'], focused=s['session']['focused'])
    assert s['session']['state'] == 'Dialogue', s['session']
    before = s['player']['position']; await tap('w', .4); rec['vex']['modalMoveM'] = math.dist(before, snap()['player']['position']); assert rec['vex']['modalMoveM'] < .04
    await tap('Escape'); s = snap(); rec['vex']['afterEscape'] = s['session']['state']; assert s['session']['state'] == 'Play', s['session']
    # 2. Salvage route to the avenue lane, on foot.
    for name, pos in APPROACH: rec['approach'][name] = await walk_to(c, d, pos, .3, 70)
    # 3. Moving-approach video.
    ff = None
    if window:
        ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'x11grab', '-framerate', '30', '-window_id', window, '-i', os.environ.get('DISPLAY', ':0'),
                               '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', str(OUT / (video + '.mp4'))], stdin=subprocess.PIPE)
        await asyncio.sleep(1)
    try:
        await c.command({'action': 'cameraBoom', 'boom': 0}); await c.command({'action': 'cameraPitch', 'pitch': 8})
        for name, pos in LEGS:
            t0 = time.monotonic(); r = await walk_to(c, d, pos, .3, 40); r['seconds'] = time.monotonic() - t0; rec['legs'][name] = r
            await c.command({'action': 'cameraPitch', 'pitch': 8}); await asyncio.sleep(.4)
    finally:
        if ff: ff.communicate(b'q'); ff.wait(timeout=20)
        await c.command({'action': 'cameraBoom', 'boom': 5})
    rec['complete'] = True; rec['finalPlayer'] = snap()['player']; rec['video'] = video + '.mp4' if window else None
    (OUT / (video + '.json')).write_text(json.dumps(rec, indent=2)); print('traversal ok', json.dumps(rec['legs'])[:300])

asyncio.run(main())
