"""Gameplay v2 native QA harness (30 Sep 2026).

Drives the Linux development player through the file-based QA bridge (--athen-qa) for positioning, camera,
captures, profiling and state reads, and through real X11 XTEST keyboard/mouse input for every verb.

Usage (repo root):
  uv run --offline --with python-xlib --with pillow python -c "import sys;sys.path.insert(0,'unity/evidence/gameplay-v2/20260930-native');from qa import *; ..."
  QA_RUN=<run dir> selects the run (one player per run directory; its pid is in <run>/pid).
"""
import base64, hashlib, json, math, os, re, subprocess, sys, time, uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
UNITY = HERE.parents[2]
TOOLS = UNITY / 'tools'
EXE = UNITY / 'AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64'
sys.path.insert(0, str(TOOLS))

RUN = (HERE / os.environ['QA_RUN']).resolve() if os.environ.get('QA_RUN') else None


def use(run):
    global RUN, _win
    RUN = (HERE / run).resolve() if not Path(run).is_absolute() else Path(run)
    _win = None
    return RUN


def pid():
    return int((RUN / 'pid').read_text().strip())


def alive():
    try:
        os.kill(pid(), 0)
        return Path(f'/proc/{pid()}/exe').exists()
    except (ProcessLookupError, FileNotFoundError):
        return False


# ---------------------------------------------------------------- launch / stop
def launch(run, save_dir=None, video=None, background=True, extra=()):
    """Start one development player in a memory-capped systemd scope. Returns its pid."""
    use(run)
    RUN.mkdir(parents=True, exist_ok=True)
    for n in ['command.json', 'ack.json', 'snapshot.json', 'dev-state.json', 'crafting.json', 'environment.json', 'pid']:
        (RUN / n).unlink(missing_ok=True)
    settings = json.loads((UNITY / 'evidence/courtyard/20260908/after-native/settings.json').read_text())['video']
    settings['antiAliasing'] = 32  # High preset default since 30 Sep 2026 (TAA)
    settings.update(video or {})
    enc = base64.b64encode(json.dumps(settings).encode()).decode()
    for vendor, product in [('unknown', 'unknown'), ('Free Column', 'Athen Hill')]:
        folder = RUN / 'config/unity3d' / vendor / product
        folder.mkdir(parents=True, exist_ok=True)
        prefs = folder / 'prefs'
        if not prefs.exists():
            prefs.write_text('<?xml version="1.0" encoding="utf-8"?><unity_prefs version_major="1" version_minor="1">'
                             '<pref name="AthenHill.Settings.v1.QA.Video" type="string">' + enc + '</pref></unity_prefs>')
    args = [str(EXE), '-force-glcore', '-screen-width', '1920', '-screen-height', '1080', '-screen-fullscreen', '0',
            '-logFile', str(RUN / 'Player.log'), '--athen-qa', str(RUN)]
    if background:
        args.append('--athen-qa-background')
    if save_dir:
        args += ['--athen-save-dir', str(Path(save_dir).resolve())]
    args += list(extra)
    quoted = ' '.join("'" + a.replace("'", "'\\''") + "'" for a in args)
    shell = f"echo $$ > '{RUN}/pid'; exec systemd-run --user --scope -q -p MemoryMax=12G -p MemoryHigh=10G {quoted} > '{RUN}/player-stdio.log' 2>&1"
    env = dict(os.environ, XDG_CONFIG_HOME=str(RUN / 'config'))
    subprocess.run(['setsid', '-f', 'bash', '-c', shell], env=env, check=True)
    for _ in range(100):
        if (RUN / 'pid').exists() and (RUN / 'pid').read_text().strip():
            break
        time.sleep(.05)
    (RUN / 'launch.json').write_text(json.dumps(dict(utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), args=args,
                                                      exe_mtime=time.ctime(EXE.stat().st_mtime), pid=pid(), video=settings), indent=1))
    return pid()


def wait_menu(timeout=120):
    t = time.monotonic() + timeout
    while time.monotonic() < t:
        if not alive():
            raise RuntimeError('player exited during startup')
        try:
            if read('snapshot.json')['session']['state'] == 'MainMenu':
                break
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            pass
        time.sleep(.2)
    else:
        raise TimeoutError('main menu not reached')
    r = subprocess.run(['bash', str(TOOLS / 'float_player_window.sh'), str(pid())], capture_output=True, text=True, timeout=20)
    time.sleep(1)
    cmd('resize', width=1920, height=1080)
    time.sleep(1.5)
    focus()
    return r.stdout.strip()


def stop(timeout=15):
    """Quit through the bridge (runs OnApplicationQuit save), then make sure the pid is gone."""
    if not alive():
        return 'not running'
    release_all()
    try:
        cmd('quit', timeout=5)
    except Exception as e:
        print('quit command:', e)
    t = time.monotonic() + timeout
    while time.monotonic() < t and alive():
        time.sleep(.2)
    if alive():
        os.kill(pid(), 15)
        time.sleep(3)
        if alive():
            os.kill(pid(), 9)
        return 'killed'
    return 'quit'


# ---------------------------------------------------------------- bridge
def read(name):
    for _ in range(40):
        try:
            return json.loads((RUN / name).read_text())
        except json.JSONDecodeError:
            time.sleep(.02)
    return json.loads((RUN / name).read_text())


def cmd(action, timeout=10, **kw):
    j = dict(kw, action=action, id=uuid.uuid4().hex[:24])
    tmp = RUN / ('command-%s.tmp' % j['id'])
    tmp.write_text(json.dumps(j))
    tmp.rename(RUN / 'command.json')
    t = time.monotonic() + timeout
    while time.monotonic() < t:
        try:
            ack = read('ack.json')
            if ack.get('id') == j['id']:
                if not ack.get('success'):
                    raise RuntimeError('bridge rejected %s: %s' % (action, ack.get('error')))
                time.sleep(.12)
                return ack
        except FileNotFoundError:
            pass
        time.sleep(.03)
    raise TimeoutError('bridge did not acknowledge %s' % j)


def snap():
    return read('snapshot.json')


def dev():
    return read('dev-state.json')


def craft():
    return read('crafting.json')


def ui():
    cmd('uiSnapshot')
    time.sleep(.1)
    return read('ui-layout.json')


def el(layout, name):
    return next((e for e in layout['elements'] if e['name'] == name), None)


def wait(pred, timeout=10, step=.1, what='condition'):
    t = time.monotonic() + timeout
    last = None
    while time.monotonic() < t:
        try:
            last = pred()
            if last:
                return last
        except (KeyError, TypeError, FileNotFoundError, json.JSONDecodeError):
            pass
        time.sleep(step)
    raise TimeoutError('timed out waiting for ' + what)


def state():
    return snap()['session']['state']


def qty(item):
    return snap()['session']['quantities'].get(item)


def settle_frames(n=3, timeout=10):
    f = snap()['frame']
    wait(lambda: snap()['frame'] >= f + n, timeout, what='frames')


def capture(name, layout=True):
    """1920x1080 native capture plus the UI layout at the same moment."""
    from PIL import Image
    path = RUN / (name + '.png')
    path.unlink(missing_ok=True)
    settle_frames(3)
    if layout:
        (RUN / (name + '-layout.json')).write_text(json.dumps(ui(), indent=1))
    cmd('capture', name=name)
    for _ in range(150):
        try:
            with Image.open(path) as im:
                im.load()
                size = im.size
            return dict(name=name, size=size, sha256=hashlib.sha256(path.read_bytes()).hexdigest()[:16])
        except (FileNotFoundError, OSError, SyntaxError):
            time.sleep(.1)
    raise TimeoutError('capture ' + name)


def goto(landmark):
    cmd('goto', landmark=landmark)
    time.sleep(.25)


def view(camera='follow'):
    cmd('view', camera=camera)


def yaw(deg):
    cmd('cameraYaw', yaw=float(deg) % 360)


def pitch(deg):
    cmd('cameraPitch', pitch=float(deg))


def devcmd(action, **kw):
    return cmd(action, **kw)


# ---------------------------------------------------------------- real input (XTEST)
_disp = None
_win = None


def _display():
    global _disp
    if _disp is None:
        from Xlib import display
        _disp = display.Display()
    return _disp


def window():
    global _win
    from Xlib import X
    d = _display()
    if _win is not None:
        return _win
    root = d.screen().root
    for wid in root.get_full_property(d.intern_atom('_NET_CLIENT_LIST'), X.AnyPropertyType).value:
        w = d.create_resource_object('window', wid)
        p = w.get_full_property(d.intern_atom('_NET_WM_PID'), X.AnyPropertyType)
        if p is not None and int(p.value[0]) == pid():
            _win = w
            return w
    raise RuntimeError('player window not found for pid %s' % pid())


def focus(center=True):
    from Xlib import X, protocol
    from Xlib.ext import xtest
    d = _display()
    w = window()
    root = d.screen().root
    root.send_event(protocol.event.ClientMessage(window=w, client_type=d.intern_atom('_NET_ACTIVE_WINDOW'), data=(32, [2, X.CurrentTime, 0, 0, 0])),
                    event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
    try:
        w.set_input_focus(X.RevertToParent, X.CurrentTime)
    except Exception:
        pass
    if center:
        g = w.get_geometry()
        o = root.translate_coords(w, 0, 0)
        xtest.fake_input(d, X.MotionNotify, x=o.x + g.width // 2, y=o.y + g.height // 2)
    d.sync()
    time.sleep(.06)
    return d


def _keycode(name):
    from Xlib import XK
    d = _display()
    sym = XK.string_to_keysym(name)
    if not sym:
        raise ValueError('unknown key ' + name)
    return d.keysym_to_keycode(sym)


def key(name, down):
    from Xlib import X
    from Xlib.ext import xtest
    d = _display()
    xtest.fake_input(d, X.KeyPress if down else X.KeyRelease, _keycode(name))
    d.sync()


def tap(name, secs=.08, settle=.22):
    focus()
    key(name, True)
    try:
        time.sleep(secs)
    finally:
        key(name, False)
    time.sleep(settle)


def hold(names, secs):
    names = [names] if isinstance(names, str) else names
    focus()
    for n in names:
        key(n, True)
    try:
        time.sleep(secs)
    finally:
        for n in reversed(names):
            key(n, False)
    time.sleep(.05)


def button(b, down):
    from Xlib import X
    from Xlib.ext import xtest
    d = _display()
    xtest.fake_input(d, X.ButtonPress if down else X.ButtonRelease, b)
    d.sync()


def click_at(px, py, b=1):
    """Click at window-client pixel coordinates."""
    from Xlib import X
    from Xlib.ext import xtest
    d = focus(center=False)
    w = window()
    o = d.screen().root.translate_coords(w, 0, 0)
    xtest.fake_input(d, X.MotionNotify, x=o.x + int(px), y=o.y + int(py))
    d.sync(); time.sleep(.05)
    button(b, True); time.sleep(.06); button(b, False)
    time.sleep(.2)


def release_all():
    try:
        for k in ['w', 'a', 's', 'd', 'e', 'f', 'Shift_L', 'space', 'Return', 'Escape', 'Tab', 'Up', 'Down', '7']:
            key(k, False)
        for b in (1, 2, 3):
            button(b, False)
    except Exception as e:
        print('release_all:', e)


def focus_ui(name, max_tabs=40, key_name='Tab'):
    """Move keyboard focus with Tab (or another key) until the named element has focus."""
    for _ in range(max_tabs):
        if snap()['session']['focused'] == name:
            return True
        tap(key_name, settle=.18)
    raise AssertionError('could not focus %s (focused=%s)' % (name, snap()['session']['focused']))


def activate(name, max_tabs=40):
    focus_ui(name, max_tabs)
    tap('Return', settle=.3)


# ---------------------------------------------------------------- movement
def pos():
    return snap()['player']['position']


def dist_xz(a, b):
    return math.hypot(a[0] - b[0], a[-1] - b[-1])


def face(x, z):
    p = pos()
    yaw(math.degrees(math.atan2(x - p[0], z - p[2])))


def walk_to(x, z, tol=.8, timeout=25, run=False):
    """Real W presses toward a point (camera yaw set through the bridge each step)."""
    t = time.monotonic() + timeout
    while time.monotonic() < t:
        p = pos()
        d = math.hypot(x - p[0], z - p[2])
        if d <= tol:
            return d
        face(x, z)
        hold(['Shift_L', 'w'] if run and d > 4 else 'w', min(.6, max(.12, d / 5.5)))
    raise TimeoutError('walk_to (%.1f, %.1f) stuck at %s' % (x, z, pos()))


# ---------------------------------------------------------------- logs
def log_errors(run=None):
    path = (HERE / run if run else RUN) / 'Player.log'
    if not path.exists():
        return []
    lines = path.read_text(errors='replace').splitlines()
    out = []
    for i, l in enumerate(lines):
        if re.search(r'Exception|NullReference|\bError\b|error CS|Assertion failed|MissingReference|UnassignedReference', l) and 'memorysetup' not in l:
            out.append({'line': i + 1, 'text': l, 'context': lines[i + 1:i + 6]})
    return out


def brief():
    s = snap()
    c = s.get('combat') or {}
    try:
        cr = craft()
    except Exception:
        cr = {}
    q = {k: v for k, v in s['session']['quantities'].items() if v}
    return dict(state=s['session']['state'], notice=s['session']['notice'][:160], prompt=s['interaction']['prompt'],
                credits=s['session']['credits'], items=q, pos=[round(x, 2) for x in s['player']['position']],
                step=c.get('step'), armed=c.get('Armed'), hp=c.get('health'), nano=round(c.get('Nano') or 0, 1),
                order=cr.get('fieldOrder'), stage=cr.get('orderStage'), slots=cr.get('slots'), focused=s['session']['focused'],
                enemies=[(e['displayName'], e['state'], round(e['health']), [round(v, 1) for v in e['position']]) for e in c.get('enemies', [])])


def pp(x):
    print(json.dumps(x, indent=1, ensure_ascii=False))


# ---------------------------------------------------------------- combat (real F / 7; camera aimed through the bridge)
def aim_at(target, lift=.35, yaw_offset=0.0):
    """Point the follow camera at a world point (two passes, since the orbit moves the camera)."""
    for _ in range(2):
        s = snap()
        c = s['camera']['position']
        dx, dz = target[0] - c[0], target[2] - c[2]
        h = math.hypot(dx, dz)
        yaw(math.degrees(math.atan2(dx, dz)) + yaw_offset)
        pitch(max(-35, min(40, math.degrees(math.atan2(c[1] - (target[1] + lift), max(h, .1))))))


def fight(until=None, seconds=120, engage=7.0, profile_name=None, deaths=None, center=None, leash=18, stop_when_clear=None, samples=None, regroup=None, regroups=None):
    """Fight live droids with real F presses until `until(snapshot)` is true. Records death positions in `deaths`."""
    end = time.monotonic() + seconds
    shots = 0
    last = {}
    deaths = deaths if deaths is not None else []
    regroups = regroups if regroups is not None else []
    downs0 = dev()['combat'].get('Downs', 0)
    if profile_name:
        cmd('profileStart')
    t0 = time.monotonic()
    try:
        while time.monotonic() < end:
            s = snap()
            c = s['combat']
            for i, e in enumerate(c['enemies']):
                k = (e['displayName'], i)
                if e['alive']:
                    last[k] = e['position']
                elif k in last:
                    deaths.append(dict(name=e['displayName'], position=e['position'], t=round(time.monotonic() - t0, 1)))
                    del last[k]
            if until and until(s):
                return dict(shots=shots, seconds=round(time.monotonic() - t0, 1), deaths=deaths)
            if samples is not None:
                samples.append(dict(t=round(time.monotonic() - t0, 2), player=s['player']['position'], hp=c['health'], nano=c['Nano'],
                                    enemies=[(e['displayName'], e['state'], e['health'], e['position']) for e in c['enemies'] if e['alive']]))
            if not c['Armed']:
                tap('7', settle=.2)
                continue
            live = [e for e in c['enemies'] if e['alive']]
            if not live:
                if stop_when_clear:
                    return dict(shots=shots, seconds=round(time.monotonic() - t0, 1), deaths=deaths)
                time.sleep(.15)
                continue
            p = s['player']['position']
            e = min(live, key=lambda x: math.hypot(x['position'][0] - p[0], x['position'][2] - p[2]))
            d = math.hypot(e['position'][0] - p[0], e['position'][2] - p[2])
            if center and math.hypot(p[0] - center[0], p[2] - center[1]) > leash and d > engage:
                if regroup and math.hypot(p[0] - center[0], p[2] - center[1]) > 25:
                    goto(regroup)  # knocked down: the Warden patrol drops you at the post; skip the long walk back
                    regroups.append(round(time.monotonic() - t0, 1))
                else:
                    walk_to(center[0], center[1], tol=3, timeout=15)
                continue
            aim_at(e['position'], lift=.5)
            if d < engage:
                if c['Nano'] < 10:
                    hold('s', .4)  # back off while nano refills
                    continue
                tap('f', .06, .2)
                shots += 1
            else:
                hold('w', min(.5, max(.15, (d - engage + 1) / 5)))
        raise TimeoutError('fight did not finish; brief=%s' % brief())
    finally:
        if profile_name:
            cmd('profileStop')
            time.sleep(.4)
            import shutil
            shutil.copy(RUN / 'profile.json', RUN / (profile_name + '.json'))
        release_all()


def summarize_profile(frames):
    def pct(v, q):
        v = sorted(v)
        return v[min(len(v) - 1, int(q * (len(v) - 1) + .5))] if v else None
    dt = [f['dt'] * 1000 for f in frames if f.get('dt', 0) > 0]
    r = dict(frames=len(dt), seconds=round(sum(dt) / 1000, 1), averageFps=round(len(dt) * 1000 / sum(dt), 1), p50Ms=round(pct(dt, .5), 2), p95Ms=round(pct(dt, .95), 2),
             p99Ms=round(pct(dt, .99), 2), maxMs=round(max(dt), 2), over16_67=sum(1 for x in dt if x > 16.67), over33=sum(1 for x in dt if x > 33.3))
    for k in ['cpuMs', 'gpuMs', 'mainMs', 'tris', 'setPass', 'batches', 'draws']:
        vals = [f[k] for f in frames if f.get(k, -1) > 0]
        r[k] = dict(mean=round(sum(vals) / len(vals), 2), p95=round(pct(vals, .95), 2), max=round(max(vals), 2)) if vals else 'unavailable'
    r['states'] = sorted(set(f.get('state') for f in frames))
    return r


def collect_at(x, z, tries=3):
    """Walk next to a cache position and press E (real input). Returns the pack delta and the prompt seen."""
    r = dict(at=(round(x, 2), round(z, 2)))
    for off in [(.9, .9), (-.9, .9), (.9, -.9), (-.9, -.9)][:tries + 1]:
        try:
            walk_to(x + off[0], z + off[1], tol=.5, timeout=10)
        except TimeoutError as e:
            r['walk'] = str(e)
        pr = snap()['interaction']['prompt']
        if 'Collect' in pr:
            break
    r['prompt'] = pr
    q0 = snap()['session']['quantities']
    if 'Collect' in pr:
        tap('e', settle=.4)
    s = snap()
    q1 = s['session']['quantities']
    r['got'] = {k: q1[k] - q0[k] for k in q1 if q1[k] != q0[k]}
    r['notice'] = s['session']['notice'][:200]
    r['promptAfter'] = s['interaction']['prompt']
    return r


def primer(report):
    """Outer Berms primer with real input: approach, locker (E), draw (7), plates (RMB+LMB), first contact and depot (F)."""
    goto('checkpoint_approach'); view('follow'); yaw(270); time.sleep(.3)
    hold('w', 1.3); time.sleep(.4)
    report['approach'] = snap()['combat']['step']
    goto('checkpoint_locker'); time.sleep(.4); tap('e', settle=.4)
    report['locker'] = snap()['combat']['hasPistol']
    tap('7', settle=.4); report['draw'] = snap()['combat']['Armed']
    goto('checkpoint_firingline'); view('follow'); time.sleep(.3)
    for i, (x, z) in enumerate([(-78, 11), (-80.5, 15.5), (-77.5, 20)]):
        for off in [-2.5, -3.5, -1.5, -4.5]:
            if snap()['combat']['targets'] > i:
                break
            p = pos(); yaw(math.degrees(math.atan2(x - p[0], z - p[2])) + off); pitch(2.5); time.sleep(.15)
            focus(); button(3, True); time.sleep(.4); button(1, True); time.sleep(.07); button(1, False); time.sleep(.3); button(3, False); time.sleep(.25)
    report['plates'] = snap()['combat']['targets']
    goto('checkpoint_road'); view('follow'); time.sleep(.4)
    d1 = []
    report['firstContact'] = fight(until=lambda s: s['combat']['step'] == 'Depot', seconds=120, deaths=d1)
    goto('depot_approach'); view('follow'); time.sleep(.4)
    d2 = []
    report['depot'] = fight(until=lambda s: s['combat']['step'] == 'Complete', seconds=240, deaths=d2, center=(-80.6, -36.2), leash=16, regroup='depot_approach')
    report['caches'] = [collect_at(x['position'][0], x['position'][2]) for x in d2]
    goto('checkpoint_road'); time.sleep(.3)
    report['caches'] += [collect_at(x['position'][0], x['position'][2]) for x in d1]
    return report


def fight_foreman(seconds=120, profile_name=None):
    """Real F against the Depot Foreman; backs off (S) while it winds up a strike."""
    def fm():
        return next((e for e in snap()['combat']['enemies'] if e['displayName'] == 'Depot Foreman'), None)
    log = []
    t1 = time.monotonic(); shots0 = snap()['combat']['ShotsFired']; hp_taken = 0; last_hp = snap()['combat']['health']; downs0 = dev()['combat']['Downs']
    if profile_name:
        cmd('profileStart')
    try:
        while time.monotonic() - t1 < seconds:
            s = snap(); c = s['combat']; f = next((e for e in c['enemies'] if e['displayName'] == 'Depot Foreman'), None)
            if c['health'] < last_hp:
                hp_taken += last_hp - c['health']
            last_hp = c['health']
            if f is None or not f['alive']:
                break
            d = dist_xz(s['player']['position'], f['position'])
            log.append((round(time.monotonic() - t1, 2), f['state'], round(f['health']), round(d, 1), round(c['health']), round(c['Nano'])))
            if d > 25:
                goto('depot_yard'); continue
            aim_at(f['position'], lift=1.0)
            if not c['Armed']:
                tap('7', settle=.1); continue
            if f['state'] == 'Windup' and d < 4.0:
                hold('s', .5); continue
            if d > 9:
                hold('w', .3); continue
            if c['Nano'] < 10:
                hold('s', .3); continue
            tap('f', .05, .08)
    finally:
        if profile_name:
            cmd('profileStop'); time.sleep(.3)
            import shutil; shutil.copy(RUN / 'profile.json', RUN / (profile_name + '.json'))
        release_all()
    return dict(seconds=round(time.monotonic() - t1, 1), shots=snap()['combat']['ShotsFired'] - shots0, hpTaken=round(hp_taken),
                downs=dev()['combat']['Downs'] - downs0, foreman=fm(), log=log)
