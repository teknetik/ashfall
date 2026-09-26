"""Frame-aware, explicitly software-only QA support; no game source changes."""
import asyncio
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'unity/tools'))
from desktop_input import key
import settings_test_input
from Xlib import X
from Xlib.ext import xtest

OUT = Path(os.environ['ATHEN_NATIVE_DIR'])
REPORT = OUT / 'adapted'
active_display = None


def snapshot():
    return json.loads((OUT / 'snapshot.json').read_text())


async def wait_frames(count=2, timeout=60):
    start_frame = snapshot()['frame']
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        current = snapshot()
        if current['frame'] >= start_frame + count:
            return current
        await asyncio.sleep(.05)
    raise TimeoutError(f'No {count} fresh software frames within {timeout}s, start={start_frame}')


async def until(predicate, timeout=60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        current = snapshot()
        if predicate(current):
            return current
        await wait_frames(1, max(.1, deadline-time.monotonic()))
    raise TimeoutError('Software state predicate was not reached within ' + str(timeout) + 's')


def focus():
    if active_display is None:
        raise RuntimeError('Use the private software session context before input.')
    return active_display


async def tap(d, name, frames=2, settle=2):
    key(d, name, True)
    try:
        await wait_frames(frames)
    finally:
        key(d, name, False)
    return await wait_frames(settle)


class Client:
    def __init__(self, *args, **kwargs):
        self.folder = OUT

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def command(self, value):
        request = dict(value, id=uuid.uuid4().hex)
        tmp = OUT / 'command.tmp'
        tmp.write_text(json.dumps(request))
        tmp.rename(OUT / 'command.json')
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            path = OUT / 'ack.json'
            if path.exists():
                ack = json.loads(path.read_text())
                if ack.get('id') == request['id']:
                    if not ack.get('success'):
                        raise RuntimeError('Native command failed: ' + str(ack))
                    await wait_frames(1)
                    return
            await asyncio.sleep(.05)
        raise TimeoutError('Software command was not acknowledged within 60s: ' + str(value))

    async def call_tool(self, name, args):
        if name == 'set_active_instance':
            return
        if name == 'execute_menu_item':
            menu = args['menu_path']
            if menu.endswith('Write snapshot'):
                await wait_frames(1)
                return
            if menu.endswith('Apply command'):
                await self.command(json.loads((OUT / 'debug-command.json').read_text()))
                return
        if name == 'manage_camera' and args['action'] == 'screenshot':
            await self.command(dict(action='capture', name='adapted-' + args['screenshot_file_name']))
            return
        raise ValueError('Unsupported software test operation: ' + name + str(args))


@contextmanager
def session():
    global active_display
    if os.environ.get('DISPLAY') != ':93' or os.environ.get('XAUTHORITY') != '/tmp/ward-qa-xvfb-20260926/Xauthority':
        raise RuntimeError('Refusing input outside the designated private Xvfb display.')
    pid = int(os.environ['ATHEN_NATIVE_PID'])
    if str(OUT.resolve()) not in Path(f'/proc/{pid}/cmdline').read_bytes().decode().split('\0'):
        raise RuntimeError('Player PID does not belong to this evidence mailbox.')
    REPORT.mkdir(exist_ok=True)
    d = settings_test_input.focus()
    repeat = d.get_keyboard_control().global_auto_repeat
    record = dict(display=':93', pid=pid, originalAutoRepeat=repeat,
                  privateAutoRepeatDuringCheck=False, restored=False)
    try:
        window = settings_test_input.window(d)
        window.configure(x=0, y=0, stack_mode=X.Above)
        window.set_input_focus(X.RevertToParent, X.CurrentTime)
        d.sync()
        for drawable in (d.screen().root, window):
            size = drawable.get_geometry()
            if (size.width, size.height) != (1920, 1080):
                raise RuntimeError('Software check requires full1920x1080 display and window.')
        if d.get_input_focus().focus.id != window.id:
            raise RuntimeError('Private software player lacks focus.')
        record['window'] = dict(id=window.id, x=0, y=0, width=1920, height=1080,
                                focusVerified=True)
        d.change_keyboard_control(auto_repeat_mode=X.AutoRepeatModeOff)
        d.sync()
        active_display = d
        yield d
    finally:
        for name in ['space', 'w', 'a', 's', 'd', 'Shift_L', 'Escape', 'Tab', 'Return', 'e', 'r', '5', '6']:
            key(d, name, False)
        for number in (1, 2, 3, 4, 5):
            xtest.fake_input(d, X.ButtonRelease, number)
        d.change_keyboard_control(auto_repeat_mode=repeat)
        d.sync()
        record['restored'] = d.get_keyboard_control().global_auto_repeat == repeat
        (REPORT / ('input-session-' + str(time.time_ns()) + '.json')).write_text(json.dumps(record, indent=2))
        active_display = None
        d.close()
