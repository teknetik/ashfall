"""Real-input release smoke; QA opt-in must remain inactive in this build."""
import json
import os
import pathlib
import sys
import time
from Xlib import X, protocol
from Xlib.ext import xtest
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'unity/tools'))
from desktop_input import focus, key

OUT = pathlib.Path(os.environ['ATHEN_RELEASE_DIR'])
PID = int(os.environ['ATHEN_NATIVE_PID'])
display = focus()
root = display.screen().root
window = None
for wid in root.get_full_property(display.intern_atom('_NET_CLIENT_LIST'), X.AnyPropertyType).value:
    candidate = display.create_resource_object('window', wid)
    prop = candidate.get_full_property(display.intern_atom('_NET_WM_PID'), X.AnyPropertyType)
    if prop is not None and int(prop.value[0]) == PID:
        window = candidate
        break
assert window is not None
geometry = window.get_geometry()
origin = root.translate_coords(window, 0, 0)
assert (geometry.width, geometry.height) == (1920, 1080)

def capture(name):
    raw = root.get_image(origin.x, origin.y, 1920, 1080, X.ZPixmap, 0xffffffff)
    Image.frombytes('RGB', (1920, 1080), raw.data, 'raw', 'BGRX').save(OUT / (name + '.png'))

def hold(name, seconds):
    key(display, name, True)
    try:
        time.sleep(seconds)
    finally:
        key(display, name, False)
    time.sleep(.2)

capture('spawn')
hold('w', 9.1)
hold('a', 3.6)
hold('w', 1.15)
# Native mouse orbit faces the terminal row; no diagnostic positioning.
xtest.fake_input(display, X.MotionNotify, x=origin.x+960, y=origin.y+520)
display.sync()
time.sleep(.2)
xtest.fake_input(display, X.ButtonPress, 1)
display.sync()
for step in range(1, 13):
    xtest.fake_input(display, X.MotionNotify, x=origin.x+960-round(692*step/12), y=origin.y+520)
    display.sync()
    time.sleep(.06)
xtest.fake_input(display, X.ButtonRelease, 1)
display.sync()
time.sleep(1)
capture('courtyard')
hold('Escape', .1)
capture('pause')
hold('Escape', .1)
xtest.fake_input(display, X.MotionNotify, x=origin.x+960, y=origin.y+540)
display.sync()
for _ in range(12):
    xtest.fake_input(display, X.ButtonPress, 4)
    xtest.fake_input(display, X.ButtonRelease, 4)
    display.sync()
    time.sleep(.08)
time.sleep(.6)
capture('first-person')
guard = OUT / 'guard'
assert sorted(p.name for p in guard.iterdir()) == ['command.json'], 'Release enabled the development QA bridge'
assert json.loads((guard / 'command.json').read_text())['id'] == 'release-must-ignore'
os.kill(PID, 0)
(OUT / 'report.json').write_text(json.dumps({
    'complete': True,
    'process': PID,
    'resolution': [1920, 1080],
    'qaFlagIgnored': True,
    'qaCommandUnconsumed': True,
    'realInput': ['movement from West Gate to terminal courtyard', 'left-drag orbit', 'pause/resume', 'wheel zoom'],
    'screenshots': ['spawn.png', 'courtyard.png', 'pause.png', 'first-person.png'],
    'note': 'Image review is recorded separately; release exposes no player-state diagnostics.'
}, indent=2)+'\n')
window.send_event(protocol.event.ClientMessage(window=window, client_type=display.intern_atom('WM_PROTOCOLS'), data=(32, [display.intern_atom('WM_DELETE_WINDOW'), X.CurrentTime, 0, 0, 0])))
display.sync()
print('Release input sequence complete; QA command ignored; normal window close requested.')
