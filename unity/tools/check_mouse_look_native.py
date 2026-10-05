"""Native check of the always-on mouse look with a real relative mouse (5 Oct 2026, art/ward_home_20261005).

The QA harness drives the mouse with XTEST absolute motion. While the game's cursor is locked, Hyprland gives XWayland
a pointer lock (it warps its own cursor into the window when the window is activated), and an XTEST pointer move then
arrives as one large mouse delta, so the harness makes no XTEST pointer moves while the cursor is locked
(qa.pointer_locked) and XTEST cannot show what a real mouse does. This check puts Hyprland's cursor inside the window, makes no XTEST pointer moves, and creates a temporary
virtual relative mouse through /dev/uinput (it goes through libinput, the compositor and XWayland exactly like a USB
mouse; it is destroyed at the end), then measures:

  1. idle: the camera holds still in play with nothing moving;
  2. a real mouse turns the camera, and the camera stops when the mouse stops;
  3. the vertical axis pitches the camera (and stops);
  4. with the field pack open the mouse moves the pointer, not the camera; closing it gives the camera back;
  5. holding Left Alt frees the pointer and the camera holds still;
  6. in the Outer Berms, with the pistol drawn (2), the real left button fires;
  7. (reported, not judged) an XTEST pointer parked off-centre: how the camera behaves (the QA artefact).

  uv run --offline --with python-xlib --with pillow python unity/tools/check_mouse_look_native.py OUT
"""
import fcntl, json, os, struct, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'unity/evidence/gameplay-v2/20260930-reqa2'))
import qa  # noqa: E402

# The real-mouse path: Hyprland's own cursor sits inside the game window (so the compositor's pointer lock engages, as
# for a player), and the harness makes no synthetic pointer moves at all (see qa.pointer_locked).
_focus = qa.focus
qa.focus = lambda center=True: _focus(center=False)


def cursor_into_window():
    rect, _ = qa.game_window_rect()
    if rect:
        import subprocess
        x, y, w, h = rect
        subprocess.run(['hyprctl', 'dispatch', 'movecursor', str(int(x + w / 2)), str(int(y + h / 2))], capture_output=True, timeout=5)
    return rect

out = Path(sys.argv[1]).resolve(); out.mkdir(parents=True, exist_ok=True)
save = out / 'save'; save.mkdir(exist_ok=True)
(save / 'ward-save.json').write_text(json.dumps({
    'version': 3, 'savedUtc': '2026-10-05T04:00:00Z', 'build': 'qa', 'credits': 50, 'purchases': 0, 'sales': 0,
    'items': [{'itemId': 'medkit', 'quantity': 1}],
    'crafting': {'known': [], 'crafted': [], 'crafts': 0, 'fitted': []},
    'bermsStep': 'Complete', 'hasPistol': True, 'orders': {'index': 0, 'id': 'order_steady_hands', 'testFired': [], 'reported': []},
    'city': {'visitedHill': True, 'boughtFlask': True, 'soldScrap': True, 'linked': True,
             'spoken': ['npc_linn', 'npc_mira', 'npc_torr', 'npc_vex'], 'selectedDestination': '', 'flags': []},
    'character': {'version': 2, 'level': 2, 'experience': 0, 'attributePoints': 0, 'skillPoints': 0,
                  'equipped': [{'slot': 'storage', 'itemId': 'field_backpack'}, {'slot': 'secondary', 'itemId': 'scrap_pistol'}],
                  'modifications': []},
}, indent=1))
checks = []; report = {'checks': checks, 'samples': {}}


def ok(cond, what, detail=None):
    checks.append({'check': what, 'passed': bool(cond), 'detail': detail})
    print(('PASS ' if cond else 'FAIL ') + what + ('' if detail is None else ' :: ' + json.dumps(detail, default=str)[:300]), flush=True)
    return cond


# ---- a virtual relative mouse (legacy uinput API; no third-party modules)
UI_SET_EVBIT, UI_SET_KEYBIT, UI_SET_RELBIT, UI_DEV_CREATE, UI_DEV_DESTROY = 0x40045564, 0x40045565, 0x40045566, 0x5501, 0x5502
EV_SYN, EV_KEY, EV_REL, REL_X, REL_Y, BTN_LEFT, BTN_RIGHT = 0, 1, 2, 0, 1, 0x110, 0x111


class Mouse:
    def __init__(self):
        self.fd = os.open('/dev/uinput', os.O_WRONLY | os.O_NONBLOCK)
        fcntl.ioctl(self.fd, UI_SET_EVBIT, EV_KEY); fcntl.ioctl(self.fd, UI_SET_KEYBIT, BTN_LEFT); fcntl.ioctl(self.fd, UI_SET_KEYBIT, BTN_RIGHT)
        fcntl.ioctl(self.fd, UI_SET_EVBIT, EV_REL); fcntl.ioctl(self.fd, UI_SET_RELBIT, REL_X); fcntl.ioctl(self.fd, UI_SET_RELBIT, REL_Y)
        os.write(self.fd, struct.pack('80sHHHHi' + 'i' * 256, b'ward-qa-relative-mouse', 0x03, 0x1209, 0x5751, 1, 0, *([0] * 256)))
        fcntl.ioctl(self.fd, UI_DEV_CREATE); time.sleep(1.5)  # libinput and the compositor pick it up

    def _emit(self, typ, code, value):
        os.write(self.fd, struct.pack('llHHi', 0, 0, typ, code, value))

    def move(self, dx, dy, steps=20, pause=.012):
        for _ in range(steps):
            if dx: self._emit(EV_REL, REL_X, dx)
            if dy: self._emit(EV_REL, REL_Y, dy)
            self._emit(EV_SYN, 0, 0); time.sleep(pause)

    def click(self, button=BTN_LEFT):
        self._emit(EV_KEY, button, 1); self._emit(EV_SYN, 0, 0); time.sleep(.08)
        self._emit(EV_KEY, button, 0); self._emit(EV_SYN, 0, 0)

    def close(self):
        try: fcntl.ioctl(self.fd, UI_DEV_DESTROY)
        finally: os.close(self.fd)


def cam():
    c = qa.snap()['camera']; return c['yaw'], c['pitch']


def dyaw(a, b):
    return (b - a + 180) % 360 - 180


def drift(seconds=1.5, n=4):
    """Largest yaw/pitch change between samples over a quiet period."""
    samples = []
    for _ in range(n):
        samples.append(cam()); time.sleep(seconds / n)
    samples.append(cam())
    return max(abs(dyaw(samples[0][0], s[0])) for s in samples), max(abs(s[1] - samples[0][1]) for s in samples), samples


mouse = None
qa.launch(out / 'run', save_dir=save)
try:
    qa.wait_menu(); report['window'] = cursor_into_window(); time.sleep(.3); qa.focus(); qa.tap('Return')
    qa.wait(lambda: qa.state() == 'Play', 40, what='Play after Continue')
    qa.release_all(); qa.cmd('timeSet', hour=13); qa.cmd('timePause', paused=True)
    qa.goto('oa_hill'); time.sleep(.5); qa.focus(); time.sleep(.6)
    qa.cmd('cameraPitch', pitch=15); qa.cmd('cameraYaw', yaw=90); time.sleep(.5)
    c = qa.snap()['cursor']; ok(c['lockState'] == 'Locked' and not c['visible'], 'in play the cursor is locked and hidden', c)
    dy0, dp0, s = drift(); report['samples']['idle'] = s
    ok(dy0 < .3 and dp0 < .3, 'idle: the camera holds still with nothing moving (XTEST pointer at the centre)', {'yaw': dy0, 'pitch': dp0})

    mouse = Mouse()
    y0, p0 = cam(); mouse.move(6, 0, steps=30); time.sleep(.25); y1, p1 = cam()
    turned = dyaw(y0, y1)
    ok(abs(turned) > 3, 'a real relative mouse turns the camera', {'before': y0, 'after': y1, 'turned': turned})
    dy1, dp1, s = drift(); report['samples']['after_turn'] = s
    ok(dy1 < .3 and dp1 < .3, 'the camera stops when the real mouse stops', {'yaw drift': dy1, 'pitch drift': dp1})
    y0, p0 = cam(); mouse.move(0, 5, steps=20); time.sleep(.25); y1, p1 = cam()
    ok(abs(p1 - p0) > 2, 'vertical mouse motion pitches the camera', {'before': p0, 'after': p1})
    dy2, dp2, s = drift(); report['samples']['after_pitch'] = s
    ok(dy2 < .3 and dp2 < .3, 'and stops when the mouse stops', {'yaw drift': dy2, 'pitch drift': dp2})

    qa.tap('Tab', settle=.6); y0, p0 = cam(); mouse.move(8, 4, steps=20); time.sleep(.3); y1, p1 = cam()
    c = qa.snap()['cursor']
    ok(qa.state() == 'Inventory' and c['visible'] and abs(dyaw(y0, y1)) < .2 and abs(p1 - p0) < .2, 'with the field pack open the mouse moves the pointer, not the camera', {'cursor': c, 'yaw': dyaw(y0, y1)})
    qa.tap('Escape', settle=.6); time.sleep(.5)
    dy3, dp3, s = drift(); report['samples']['after_pack'] = s
    ok(qa.state() == 'Play' and dy3 < .3 and dp3 < .3, 'closing the pack: cursor locked again and the camera still (no jump, no drift)', {'yaw drift': dy3, 'pitch drift': dp3, 'cursor': qa.snap()['cursor']})
    y0, p0 = cam(); mouse.move(-6, 0, steps=20); time.sleep(.25); y1, _ = cam()
    ok(abs(dyaw(y0, y1)) > 2, 'the mouse turns the camera again after the pack closes', {'turned': dyaw(y0, y1)})

    qa.key('Alt_L', True); time.sleep(.3); y0, _ = cam(); mouse.move(8, 0, steps=20); time.sleep(.3); y1, _ = cam(); c = qa.snap()['cursor']
    qa.key('Alt_L', False); time.sleep(.5)
    ok(c['freed'] and c['visible'] and abs(dyaw(y0, y1)) < .2, 'holding Left Alt frees the pointer and the camera holds still', {'cursor': c, 'yaw': dyaw(y0, y1)})
    dy4, dp4, _ = drift(1.0, 3)
    ok(dy4 < .3 and dp4 < .3, 'releasing Left Alt: no drift', {'yaw drift': dy4, 'pitch drift': dp4})

    qa.goto('checkpoint_range_reset'); time.sleep(.6)
    qa.tap('2', settle=.6); cb = qa.snap()['combat']
    ok(cb['Armed'], '2 draws the scrap pistol in the Berms', {'armed': cb['Armed']})
    shots = cb['ShotsFired']; mouse.click(BTN_LEFT); time.sleep(.5)
    ok(qa.snap()['combat']['ShotsFired'] == shots + 1, 'the real left mouse button fires (no aim needed)', {'before': shots, 'after': qa.snap()['combat']['ShotsFired']})
    qa.tap('2', settle=.4)

    # XTEST artefact, reported only (the harness parks the compositor cursor outside the window to avoid it)
    g = qa.window().get_geometry()
    from Xlib import X
    from Xlib.ext import xtest
    d = qa._display(); o = d.screen().root.translate_coords(qa.window(), 0, 0)
    y0, p0 = cam(); xtest.fake_input(d, X.MotionNotify, x=o.x + g.width // 2 + 150, y=o.y + g.height // 2); d.sync()
    time.sleep(.5); y1, _ = cam(); time.sleep(1.0); y2, _ = cam()
    report['xtestOffCentre'] = {'after0.5s': dyaw(y0, y1), 'after1.5s': dyaw(y0, y2)}
    print('XTEST pointer parked 150 px right of centre: yaw change after 0.5 s', round(dyaw(y0, y1), 1), 'after 1.5 s', round(dyaw(y0, y2), 1), flush=True)
    time.sleep(.5)
    report['errors'] = qa.log_errors()
    ok(not report['errors'], 'no exceptions in Player.log', report['errors'][:3])
finally:
    if mouse: mouse.close()
    print('stop:', qa.stop())
report['passed'] = all(c['passed'] for c in checks)
(out / 'report.json').write_text(json.dumps(report, indent=1, default=str))
print('PASSED' if report['passed'] else 'FAILED', sum(c['passed'] for c in checks), '/', len(checks))
sys.exit(0 if report['passed'] else 1)
