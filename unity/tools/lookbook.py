"""Native lookbook: launch the development player, capture named cameras at set hours, profile, quit.

Usage (from the repo root):
  uv run --offline --with python-xlib --with pillow python unity/tools/lookbook.py OUT \
      [--cams cam_hill,cam_avenue] [--hours 9,13,17.5,21] [--profile 6] [--exe PATH] [--sheet]

OUT must not exist. Every image is 1920x1080 from the real OpenGL player with its saved High video preset.
The day clock is set and paused per hour; the player stays at West Gate (views are fixed review cameras).
--sheet writes a downscaled contact sheet per hour for quick review. Nothing in the scene is changed.
"""
import argparse, asyncio, base64, hashlib, json, os, signal, statistics, subprocess, sys, time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[1]
sys.path.insert(0, str(TOOLS))
DEFAULT_CAMS = ['cam_hill', 'cam_avenue', 'cam_gate', 'cam_grid', 'cam_whompah', 'cam_hero', 'cam_market',
                'cam_westgate_mouth', 'cam_berms_overview', 'cam_depot_approach', 'cam_depot_yard']


def percentile(values, q):
    values = sorted(values)
    return values[min(len(values) - 1, int(q * (len(values) - 1) + .5))] if values else None


def summarize(frames):
    dt = [f['dt'] * 1000 for f in frames if f.get('dt', 0) > 0]
    r = dict(frames=len(dt), averageFps=len(dt) * 1000 / sum(dt), p50Ms=percentile(dt, .5), p95Ms=percentile(dt, .95),
             p99Ms=percentile(dt, .99), maxMs=max(dt))
    for k in ['cpuMs', 'gpuMs', 'draws', 'tris', 'batches', 'setPass']:
        vals = [f[k] for f in frames if f.get(k, -1) > 0]
        r[k] = dict(mean=round(statistics.mean(vals), 3), p95=percentile(vals, .95)) if vals else None
    return r


class Run:
    def __init__(self, out):
        self.out = out

    def read(self, name):
        return json.loads((self.out / name).read_text())

    async def command(self, j, timeout=15):
        j = dict(j, id=os.urandom(8).hex())
        tmp = self.out / ('command-%s.tmp' % j['id'])
        tmp.write_text(json.dumps(j)); tmp.rename(self.out / 'command.json')
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                ack = self.read('ack.json')
                if ack.get('id') == j['id']:
                    if not ack.get('success'): raise RuntimeError('rejected %s: %s' % (j, ack.get('error')))
                    return
            except (FileNotFoundError, json.JSONDecodeError): pass
            await asyncio.sleep(.03)
        raise TimeoutError('not acknowledged: %s' % j)

    async def capture(self, name):
        from PIL import Image
        path = self.out / (name + '.png')
        await self.command({'action': 'capture', 'name': name})
        for _ in range(150):
            try:
                with Image.open(path) as im:
                    im.load(); assert im.size == (1920, 1080), im.size
                return dict(name=name, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            except (FileNotFoundError, OSError, SyntaxError): await asyncio.sleep(.1)
        raise TimeoutError(name)


def launch(out, exe):
    video = json.loads((ROOT / 'unity/evidence/courtyard/20260908/after-native/settings.json').read_text())['video']
    encoded = base64.b64encode(json.dumps(video).encode()).decode()
    for vendor, product in [('unknown', 'unknown'), ('Free Column', 'Athen Hill')]:
        folder = out / 'config/unity3d' / vendor / product
        folder.mkdir(parents=True)
        (folder / 'prefs').write_text('<?xml version="1.0" encoding="utf-8"?><unity_prefs version_major="1" version_minor="1">'
                                      '<pref name="AthenHill.Settings.v1.QA.Video" type="string">' + encoded + '</pref></unity_prefs>')
    args = [str(exe), '-force-glcore', '-screen-width', '1920', '-screen-height', '1080', '-screen-fullscreen', '0',
            '-logFile', str(out / 'Player.log'), '--athen-qa', str(out)]
    env = dict(os.environ, XDG_CONFIG_HOME=str(out / 'config'))
    log = (out / 'player-stdio.log').open('w')
    return subprocess.Popen(args, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)


async def start_play(run, player):
    from desktop_input import focus, key
    for _ in range(900):
        if player.poll() is not None: raise RuntimeError('player exited %s' % player.returncode)
        try:
            if 'session' in run.read('snapshot.json'): break
        except (FileNotFoundError, json.JSONDecodeError): pass
        await asyncio.sleep(.1)
    subprocess.run(['bash', str(TOOLS / 'float_player_window.sh'), str(player.pid)], capture_output=True, timeout=20)
    os.environ['ATHEN_NATIVE_PID'] = str(player.pid)  # match the window by process, not title
    d = focus()
    for _ in range(10):
        if run.read('snapshot.json')['session']['state'] != 'MainMenu': break
        key(d, 'Return', True); await asyncio.sleep(.12); key(d, 'Return', False); await asyncio.sleep(1.5)
    for _ in range(300):
        if run.read('snapshot.json')['session']['state'] == 'Play': break
        await asyncio.sleep(.1)
    for k in ['w', 'a', 's', 'd', 'e', 'Return', 'Escape']: key(d, k, False)
    assert run.read('snapshot.json')['session']['state'] == 'Play', run.read('snapshot.json')['session']
    await run.command({'action': 'resize', 'width': 1920, 'height': 1080}); await asyncio.sleep(2)


def contact_sheet(out, names, path, cols=3, width=640):
    from PIL import Image, ImageDraw
    thumbs = []
    for n in names:
        with Image.open(out / (n + '.png')) as im:
            thumbs.append((n, im.convert('RGB').resize((width, width * 9 // 16))))
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * width, rows * (width * 9 // 16 + 22)), (20, 20, 20))
    draw = ImageDraw.Draw(sheet)
    for i, (n, t) in enumerate(thumbs):
        x, y = i % cols * width, i // cols * (width * 9 // 16 + 22)
        sheet.paste(t, (x, y + 22)); draw.text((x + 6, y + 4), n, fill=(230, 220, 200))
    sheet.save(path, quality=88)


async def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('out', type=Path)
    p.add_argument('--cams', default=','.join(DEFAULT_CAMS))
    p.add_argument('--hours', default='9,13,17.5,21')
    p.add_argument('--profile', type=float, default=0, help='seconds of frame timing per hour at the first camera')
    p.add_argument('--exe', type=Path, default=ROOT / 'unity/AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64')
    p.add_argument('--sheet', action='store_true')
    a = p.parse_args()
    out = a.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    cams = [c for c in a.cams.split(',') if c]; hours = [float(h) for h in a.hours.split(',') if h]
    report = dict(utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), exe=str(a.exe),
                  exeMtime=time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(a.exe.stat().st_mtime)),
                  loadAverage=os.getloadavg(), cams=cams, hours=hours, captures=[], profiles={}, errors=[])
    player = launch(out, a.exe); run = Run(out)
    try:
        await start_play(run, player)
        report['environment'] = run.read('environment.json')
        for h in hours:
            await run.command({'action': 'timeSet', 'hour': h}); await run.command({'action': 'timePause', 'paused': True})
            await asyncio.sleep(2.5)
            names = []
            for i, cam in enumerate(cams):
                try:
                    await run.command({'action': 'view', 'camera': cam}); await asyncio.sleep(1.4)
                    if i == 0 and a.profile > 0:
                        await run.command({'action': 'profileStart'}); await asyncio.sleep(a.profile)
                        await run.command({'action': 'profileStop'}); await asyncio.sleep(.3)
                        report['profiles']['%s-h%s' % (cam, h)] = summarize(run.read('profile.json'))
                    name = '%s-h%05.2f' % (cam, h)
                    report['captures'].append(await run.capture(name)); names.append(name)
                except Exception as e:
                    report['errors'].append('%s@%s: %r' % (cam, h, e))
                print('captured', cam, h, flush=True)
            if a.sheet and names: contact_sheet(out, names, out / ('sheet-h%05.2f.jpg' % h))
        await run.command({'action': 'view', 'camera': 'follow'})
        try: await run.command({'action': 'quit'}, timeout=5)
        except Exception: pass
    finally:
        try: player.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(player.pid, signal.SIGTERM)
        report['playerReturncode'] = player.returncode
        (out / 'lookbook.json').write_text(json.dumps(report, indent=2))
        print(json.dumps(dict(captures=len(report['captures']), errors=report['errors'], profiles=report['profiles']), indent=1))


if __name__ == '__main__':
    asyncio.run(main())
