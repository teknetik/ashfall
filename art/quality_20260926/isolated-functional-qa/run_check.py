"""Run an existing real-XTest check on the private software-rendered QA player.

Changes only the display-specific window focus helper. Assertions and input
durations in the existing checks are unmodified. No system configuration changes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
CHOICES = {'controls': 'controls_check.py', 'city-loop': 'city_loop_check.py',
           'route': 'walk_route.py'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence', type=Path)
    parser.add_argument('check', choices=CHOICES)
    args = parser.parse_args()
    out = args.evidence.resolve()
    launch = json.loads((out / 'launch.json').read_text())
    if not launch.get('profileVerified') or not any(x in launch['actualRenderer'].lower()
                                                  for x in ('llvmpipe', 'softpipe')):
        raise RuntimeError('A verified isolated software player is required.')
    scoped = launch['scopedEnvironment']
    if scoped['DISPLAY'] != ':93' or scoped['XAUTHORITY'] != '/tmp/ward-qa-xvfb-20260926/Xauthority':
        raise RuntimeError('Unexpected display; refusing to send input.')
    pid = int((out / 'pid').read_text())
    os.kill(pid, 0)
    if str(out) not in Path('/proc/' + str(pid) + '/cmdline').read_bytes().decode().split('\0'):
        raise RuntimeError('PID no longer belongs to this evidence run.')
    os.environ.update(scoped, ATHEN_NATIVE_PID=str(pid))
    sys.path.insert(0, str(ROOT / 'unity/tools'))
    import desktop_input
    import settings_test_input
    from Xlib import X
    from Xlib.ext import xtest
    active_display = None

    def focus():
        nonlocal active_display
        d = settings_test_input.focus()
        active_display = d
        root = d.screen().root
        root_size = root.get_geometry()
        if (root_size.width, root_size.height) != (1920, 1080):
            raise RuntimeError('Existing UI coordinates require a 1920x1080 private display.')
        w = settings_test_input.window(d)
        w.configure(x=0, y=0, stack_mode=X.Above)
        w.set_input_focus(X.RevertToParent, X.CurrentTime)
        d.sync()
        size = w.get_geometry()
        if (size.width, size.height) != (1920, 1080):
            raise RuntimeError('Native window must fill the private display for existing pointer checks.')
        if d.get_input_focus().focus.id != w.id:
            raise RuntimeError('Private player did not receive input focus.')
        return d

    desktop_input.focus = focus
    script = ROOT / 'unity/tools' / CHOICES[args.check]
    record = dict(check=args.check, purpose='Software functional checks only',
                  script=str(script), sha256=hashlib.sha256(script.read_bytes()).hexdigest(),
                  assertionsModified=False, inputDurationsModified=False,
                  input='X11 XTest keyboard/mouse on private display :93', complete=False)
    started = time.monotonic()
    report_path = out / (args.check + '-harness.json')
    if report_path.exists():
        raise RuntimeError('Preserve the existing check evidence; use a new run for repeats.')
    try:
        sys.argv = [str(script)]
        runpy.run_path(str(script), run_name='__main__')
        record['complete'] = True
    except BaseException as error:
        record['error'] = str(error)
        raise
    finally:
        if active_display is not None:
            for name in ['space', 'w', 'a', 's', 'd', 'Shift_L', 'Escape', 'Tab', 'Return', 'e', 'r', '5', '6']:
                desktop_input.key(active_display, name, False)
            for number in (1, 2, 3, 4, 5):
                xtest.fake_input(active_display, X.ButtonRelease, number)
            active_display.sync()
            active_display.close()
        record['elapsedSeconds'] = time.monotonic() - started
        report_path.write_text(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
