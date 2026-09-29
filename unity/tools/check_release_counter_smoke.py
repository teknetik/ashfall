"""Release smoke for the Basic General counter pass: windowed launch, real keys, non-blank grim capture, log scan, and proof that the
development bridge is absent (the --athen-qa folder must stay empty)."""
import json, os, subprocess, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1]).resolve(); OUT.mkdir(parents=True)
(OUT / 'config').mkdir()
qa = OUT / 'qa-probe'; qa.mkdir()
exe = ROOT / 'AthenHill/Builds/Linux/AthenHill.x86_64'
p = subprocess.Popen([str(exe), '-force-glcore', '-screen-width', '1920', '-screen-height', '1080', '-screen-fullscreen', '0', '-logFile', str(OUT / 'Player.log'), '--athen-qa', str(qa)],
                     env=dict(os.environ, XDG_CONFIG_HOME=str(OUT / 'config')), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, start_new_session=True)
os.environ['ATHEN_NATIVE_PID'] = str(p.pid)
report = dict(complete=False, pid=p.pid, build=str(exe))
try:
    time.sleep(8)
    assert p.poll() is None, 'release exited at startup'
    sig = sorted(Path('/run/user/1000/hypr').iterdir())[0].name
    env = dict(os.environ, HYPRLAND_INSTANCE_SIGNATURE=sig)
    subprocess.run(['hyprctl', 'dispatch', 'hl.dsp.window.float({ action = "enable", window = "pid:%d" })' % p.pid], env=env, capture_output=True)
    subprocess.run(['hyprctl', 'dispatch', 'hl.dsp.window.resize({ x = 1920, y = 1080, exact = true, window = "pid:%d" })' % p.pid], env=env, capture_output=True)
    time.sleep(2)
    clients = json.loads(subprocess.check_output(['hyprctl', 'clients', '-j'], env=env, text=True))
    w = next(c for c in clients if c['pid'] == p.pid)
    report['window'] = dict(at=w['at'], size=w['size'], title=w['title'])
    from desktop_input import focus, key
    d = focus()
    for name, dur in [('Return', .12), ('Return', .12), ('e', .1), ('Escape', .1), ('w', .8)]:
        key(d, name, True); time.sleep(dur); key(d, name, False); time.sleep(.6)
    time.sleep(2)
    geo = '%d,%d %dx%d' % (w['at'][0], w['at'][1], w['size'][0], w['size'][1])
    shot = OUT / 'release-window.png'
    subprocess.run(['grim', '-g', geo, str(shot)], check=True, env=dict(os.environ, WAYLAND_DISPLAY='wayland-1', XDG_RUNTIME_DIR='/run/user/1000'))
    from PIL import Image, ImageStat
    im = Image.open(shot).convert('RGB'); report['screenshotSize'] = im.size; report['screenshotStddev'] = round(sum(ImageStat.Stat(im).stddev), 1)
    assert report['screenshotStddev'] > 30, 'blank rendering'
    report['stillRunning'] = p.poll() is None
finally:
    if p.poll() is None: p.terminate()
    time.sleep(3)
log = (OUT / 'Player.log').read_text(errors='replace')
report['qaFolderFiles'] = sorted(x.name for x in qa.iterdir())
report['bridgeAbsent'] = not report['qaFolderFiles']
report['logExceptionLines'] = [l[:200] for l in log.splitlines() if ('Exception' in l or 'NullReference' in l or 'shader' in l.lower() and 'error' in l.lower()) and 'GL_' not in l]
report['logHasDevelopmentBuildMarker'] = 'Development' in log[:3000]
report['complete'] = report['bridgeAbsent'] and not report['logExceptionLines']
(OUT / 'report.json').write_text(json.dumps(report, indent=2)); print(json.dumps(report, indent=2))
