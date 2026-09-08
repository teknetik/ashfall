"""Launch the native release, exercise real keys, and save a non-blank screen/log check."""
import datetime
import json
import os
from pathlib import Path
import subprocess
import time
import re
from PIL import ImageGrab, ImageStat

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ['ATHEN_RELEASE_EVIDENCE']) if os.environ.get('ATHEN_RELEASE_EVIDENCE') else ROOT / 'evidence' / 'ward-guard' / datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ-release')
OUT.mkdir(parents=True)
private_config = OUT / 'config'
private_config.mkdir()
xrandr_state = subprocess.check_output(['xrandr', '--current'], text=True)
active = next((line.split()[0] for line in xrandr_state.splitlines() if '*' in line), None)
mode = active or 'x'.join(re.search(r'current (\d+) x (\d+)', xrandr_state).groups())
changed_mode = mode != '1920x1080'
process = None
report = {'complete': False, 'scope': 'Native release launch, input responsiveness, non-blank rendering, no runtime exceptions. Full city-loop assertions run separately in development.'}
try:
    if changed_mode:
        subprocess.run(['xrandr', '--output', 'DP-0', '--mode', '1920x1080'], check=True)
    process = subprocess.Popen([str(ROOT / 'AthenHill/Builds/Linux/AthenHill.x86_64'), '-force-glcore',
        '-screen-fullscreen', '1', '-screen-width', '1920', '-screen-height', '1080',
        '-logFile', str(OUT / 'Player.log'), '--athen-qa', str(OUT)],
        env=dict(os.environ, XDG_CONFIG_HOME=str(private_config)), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    os.environ['ATHEN_NATIVE_PID'] = str(process.pid)
    from desktop_input import focus, key
    time.sleep(5)
    assert process.poll() is None, 'Release exited at startup'
    d = focus()
    start = ImageGrab.grab(); start.save(OUT / 'startup.png')
    assert sum(ImageStat.Stat(start).stddev) > 30, 'Blank release rendering'
    for name, duration in [('e', .1), ('Escape', .1), ('w', .8), ('r', .1)]:
        key(d, name, True)
        try: time.sleep(duration)
        finally: key(d, name, False)
        time.sleep(.25)
        assert process.poll() is None, 'Release exited during keyboard input'
    key(d, 'Escape', True); time.sleep(.1); key(d, 'Escape', False); time.sleep(.5)
    ImageGrab.grab().save(OUT / 'pause.png')
    assert not (OUT / 'snapshot.json').exists(), 'Release must ignore development QA option'
    log = (OUT / 'Player.log').read_text()
    assert 'Exception:' not in log and 'NullReferenceException' not in log
    report['complete'] = True
    print('PASS: native release smoke; evidence:', OUT)
finally:
    if process and process.poll() is None:
        process.terminate(); process.wait(timeout=10)
    if changed_mode:
        subprocess.run(['xrandr', '--output', 'DP-0', '--mode', mode], check=True)
    (OUT / 'report.json').write_text(json.dumps(report, indent=2))
