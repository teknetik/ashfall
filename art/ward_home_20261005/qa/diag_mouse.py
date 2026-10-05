"""Diagnostic (5 Oct 2026): does a real relative mouse (uinput) reach the camera, in the old and the new builds?

  uv run --offline --with python-xlib --with pillow python art/ward_home_20261005/qa/diag_mouse.py OUT EXE old|new

old (the Field Supply build): left-drag orbit with the cursor free, then aim mode (right mouse; cursor locked, visible).
new: plain motion (cursor locked and hidden), then aim mode. Records the camera yaw and Hyprland's cursor position.
"""
import fcntl, json, os, struct, subprocess, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'unity/evidence/gameplay-v2/20260930-reqa2'))
import qa  # noqa: E402

out = Path(sys.argv[1]).resolve(); out.mkdir(parents=True, exist_ok=True); qa.EXE = Path(sys.argv[2]); mode = sys.argv[3]
save = out / 'save'; save.mkdir(exist_ok=True)
(save / 'ward-save.json').write_text(json.dumps({
    'version': 3, 'savedUtc': '2026-10-05T04:00:00Z', 'build': 'qa', 'credits': 50, 'purchases': 0, 'sales': 0, 'items': [],
    'crafting': {'known': [], 'crafted': [], 'crafts': 0, 'fitted': []}, 'bermsStep': 'Complete', 'hasPistol': True,
    'orders': {'index': 0, 'id': 'order_steady_hands', 'testFired': [], 'reported': []},
    'city': {'visitedHill': True, 'boughtFlask': True, 'soldScrap': True, 'linked': True, 'spoken': ['npc_linn', 'npc_mira', 'npc_torr', 'npc_vex'], 'selectedDestination': '', 'flags': []},
    'character': {'version': 2, 'level': 2, 'experience': 0, 'attributePoints': 0, 'skillPoints': 0,
                  'equipped': [{'slot': 'storage', 'itemId': 'field_backpack'}, {'slot': 'secondary', 'itemId': 'scrap_pistol'}], 'modifications': []}}))
UI_SET_EVBIT, UI_SET_KEYBIT, UI_SET_RELBIT, UI_DEV_CREATE, UI_DEV_DESTROY = 0x40045564, 0x40045565, 0x40045566, 0x5501, 0x5502
EV_SYN, EV_KEY, EV_REL, REL_X, REL_Y, BTN_LEFT, BTN_RIGHT = 0, 1, 2, 0, 1, 0x110, 0x111
res = {'mode': mode}


class Mouse:
    def __init__(self):
        self.fd = os.open('/dev/uinput', os.O_WRONLY | os.O_NONBLOCK)
        for ev, bit in ((UI_SET_EVBIT, EV_KEY), (UI_SET_KEYBIT, BTN_LEFT), (UI_SET_KEYBIT, BTN_RIGHT), (UI_SET_EVBIT, EV_REL), (UI_SET_RELBIT, REL_X), (UI_SET_RELBIT, REL_Y)):
            fcntl.ioctl(self.fd, ev, bit)
        os.write(self.fd, struct.pack('80sHHHHi' + 'i' * 256, b'ward-qa-relative-mouse', 0x03, 0x1209, 0x5751, 1, 0, *([0] * 256)))
        fcntl.ioctl(self.fd, UI_DEV_CREATE); time.sleep(1.5)

    def ev(self, t, c, v): os.write(self.fd, struct.pack('llHHi', 0, 0, t, c, v))

    def move(self, dx, steps=25):
        for _ in range(steps): self.ev(EV_REL, REL_X, dx); self.ev(EV_SYN, 0, 0); time.sleep(.012)

    def button(self, b, down): self.ev(EV_KEY, b, 1 if down else 0); self.ev(EV_SYN, 0, 0); time.sleep(.05)

    def close(self): fcntl.ioctl(self.fd, UI_DEV_DESTROY); os.close(self.fd)


def cursor(): return subprocess.run(['hyprctl', 'cursorpos'], capture_output=True, text=True).stdout.strip()


def yaw(): return qa.snap()['camera']['yaw']


def probe(name, before_hook=None, after_hook=None):
    if before_hook: before_hook()
    time.sleep(.4)
    y0, c0 = yaw(), cursor(); m.move(6); time.sleep(.3); y1, c1 = yaw(), cursor()
    if after_hook: after_hook()
    d = (y1 - y0 + 180) % 360 - 180
    res[name] = {'yaw_delta': round(d, 2), 'cursor_before': c0, 'cursor_after': c1, 'lock': (qa.snap().get('cursor') or {}).get('lockState')}
    print(name, json.dumps(res[name]), flush=True)


m = None
qa.launch(out / 'run', save_dir=save)
try:
    qa.wait_menu(); qa.focus(); qa.tap('Return'); qa.wait(lambda: qa.state() == 'Play', 40, what='Play'); qa.release_all()
    qa.goto('checkpoint_range_reset'); time.sleep(.6); qa.focus(); time.sleep(.5)
    win = subprocess.run(['hyprctl', 'clients', '-j'], capture_output=True, text=True).stdout
    res['window'] = [(c['at'], c['size']) for c in json.loads(win) if 'Athen' in c.get('title', '')]
    m = Mouse()
    if mode == 'old':
        probe('motion_no_button')
        probe('orbit_left_drag', lambda: m.button(BTN_LEFT, True), lambda: m.button(BTN_LEFT, False))
        qa.tap('7', settle=.6)
    else:
        probe('motion_locked')
        qa.tap('2', settle=.6)
    res['armed'] = qa.snap()['combat']['Armed']
    probe('aim_right_held', lambda: m.button(BTN_RIGHT, True), lambda: m.button(BTN_RIGHT, False))
finally:
    if m: m.close()
    print('stop:', qa.stop())
(out / 'diag.json').write_text(json.dumps(res, indent=1))
print(json.dumps(res))
