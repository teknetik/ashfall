"""Smoke the fresh release player and ensure --athen-qa is refused."""
import json
import os
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = HERE / 'release-native'
OUT.mkdir(exist_ok=True)
args = [str(ROOT / 'AthenHill/Builds/Linux/AthenHill.x86_64'), '-force-glcore', '-screen-fullscreen', '0', '-screen-width', '1280', '-screen-height', '720', '-logFile', str(OUT / 'Player.log'), '--athen-qa', str(OUT / 'qa-bridge'), '--athen-qa-background']
env = dict(os.environ, DISPLAY=os.environ.get('DISPLAY', ':0'), XDG_CONFIG_HOME=str(OUT / 'config'))
report = {'binary': args[0], 'qa_requested': args[-2], 'checks': []}
with (OUT / 'launcher.log').open('wb') as log:
    proc = subprocess.Popen(args, env=env, stdout=log, stderr=subprocess.STDOUT)
    try:
        time.sleep(35)
        report['alive_after_35s'] = proc.poll() is None
        report['bridge_created'] = (OUT / 'qa-bridge').exists()
        text = (OUT / 'Player.log').read_text(errors='replace') if (OUT / 'Player.log').exists() else ''
        report['runtime_errors'] = [line for line in text.splitlines() if 'Exception:' in line or 'NullReference' in line]
        report['development_qa_log'] = 'QA bridge active' in text or 'Development QA' in text
        report['passed'] = report['alive_after_35s'] and not report['bridge_created'] and not report['runtime_errors'] and not report['development_qa_log']
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        (OUT / 'report.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
if not report['passed']:
    raise SystemExit(1)
