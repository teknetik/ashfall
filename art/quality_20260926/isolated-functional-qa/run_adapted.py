"""Run a separately identified frame-aware software functional check."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CHOICES = {'controls': 'adapted-controls.py'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence', type=Path)
    parser.add_argument('check', choices=CHOICES)
    args = parser.parse_args()
    out = args.evidence.resolve()
    launch = json.loads((out / 'launch.json').read_text())
    if not launch.get('profileVerified') or 'llvmpipe' not in launch['actualRenderer'].lower():
        raise RuntimeError('A verified software player is required.')
    os.environ.update(launch['scopedEnvironment'], ATHEN_NATIVE_PID=(out / 'pid').read_text())
    os.environ['ATHEN_EVIDENCE'] = str(out / 'adapted')
    # Fresh-frame waits replace the older UI-snapshot key-hold workaround.
    os.environ.pop('ATHEN_UI_XVFB', None)
    sys.path.insert(0, str(HERE))
    import software_input
    script = HERE / CHOICES[args.check]
    report_path = software_input.REPORT / (args.check + '-harness.json')
    if report_path.exists():
        raise RuntimeError('Preserve previous adapted-check evidence; use a new run for repeats.')
    record = dict(check=args.check, purpose='Adapted software functional check only',
                  originalTestPassed=False, script=str(script),
                  sha256=hashlib.sha256(script.read_bytes()).hexdigest(), complete=False,
                  sharedSupportSha256=hashlib.sha256((HERE/'software_input.py').read_bytes()).hexdigest(),
                  timing='Fresh-frame input barriers; 60s command/frame timeout; private Xvfb key autorepeat off')
    started = time.monotonic()
    try:
        with software_input.session():
            sys.argv = [str(script)]
            runpy.run_path(str(script), run_name='__main__')
        record['complete'] = True
    except BaseException as error:
        record['error'] = str(error)
        raise
    finally:
        software_input.REPORT.mkdir(exist_ok=True)
        record['elapsedSeconds'] = time.monotonic()-started
        report_path.write_text(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
