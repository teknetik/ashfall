"""One detached native-review run; root owns this sole input operator.

Launch only after a fresh development player is ready and authoring apps are
closed. This process survives a conversation interruption; inspect its recorded
PID and status before issuing any other native inputs. This is not an automation.
"""
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1]).resolve()
STATUS = OUT / 'review-runner-status.json'
assert OUT.is_dir() and (OUT / 'pid').is_file()
assert not STATUS.exists(), 'Preserve prior runner and capture evidence.'
state = {'pid': os.getpid(), 'startedUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'running': True, 'complete': False, 'commands': []}


def save():
    temporary = STATUS.with_suffix('.tmp')
    temporary.write_text(json.dumps(state, indent=2))
    temporary.replace(STATUS)


save()
commands = [
    [sys.executable, str(ROOT/'art/reference_street_20260910/capture_native_iteration.py'), str(OUT),
     '--prop-cameras', 'cam_ground_crate', 'cam_ground_trash', 'cam_ground_scrap'],
    [sys.executable, str(ROOT/'art/reference_street_20260910/capture_asset_passes.py'), str(OUT)],
]
try:
    for command in commands:
        state['phase'] = Path(command[1]).name
        save()
        result = subprocess.run(command, cwd=ROOT, check=False)
        state['commands'].append({'argv': command, 'returncode': result.returncode})
        save()
        if result.returncode:
            raise RuntimeError('Native review failed: ' + state['phase'])
    state['complete'] = True
except Exception as error:
    state['error'] = repr(error)
    raise
finally:
    state['running'] = False
    state['finishedUtc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    save()
