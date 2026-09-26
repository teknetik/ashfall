"""Release-only owned-window render observation. No input, focus or QA backdoor.

Default is a dry run; --launch requires explicit coordinator handoff. Uses only
this child's X11 drawable for GetImage. Never captures the desktop/root window.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[3]
SIGNATURE = 'efb50993780079460b0cbed1363e2166a2de1d9f_1790318179_484952352'


def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for part in iter(lambda: stream.read(1024*1024), b''):
            h.update(part)
    return h.hexdigest()


def hypr(args, env):
    result = subprocess.run(['hyprctl', *args], env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=8)
    if result.returncode:
        raise RuntimeError('hyprctl failed: ' + result.stderr + result.stdout)
    return result.stdout


def window_capture(pid, output):
    # Separate process bounds any blocked X11 request; this method never captures
    # an ancestor, root window or a drawable owned by a different PID.
    from Xlib import X, display
    from PIL import Image, ImageStat
    d = display.Display()
    try:
        root = d.screen().root
        prop = root.get_full_property(d.intern_atom('_NET_CLIENT_LIST'), X.AnyPropertyType)
        windows = ([d.create_resource_object('window', int(w)) for w in prop.value]
                   if prop is not None else root.query_tree().children)
        owned = []
        for window in windows:
            try:
                value = window.get_full_property(d.intern_atom('_NET_WM_PID'), X.AnyPropertyType)
                if value is not None and int(value.value[0]) == pid:
                    g = window.get_geometry()
                    owned.append((g.width*g.height, window, g))
            except Exception:
                continue
        if not owned:
            raise RuntimeError('No X11 client with the exact child PID was found.')
        _, window, geometry = max(owned, key=lambda item: item[0])
        attrs = window.get_attributes()
        record = dict(window=window.id, pid=pid, mapState=attrs.map_state,
                      width=geometry.width, height=geometry.height, depth=geometry.depth,
                      capture='XGetImage of this PID-owned client window only')
        write(output.with_suffix('.window.json'), record)
        if attrs.map_state != X.IsViewable:
            raise RuntimeError('Owned release window is not viewable.')
        if (geometry.width, geometry.height) != (1920, 1080):
            raise RuntimeError('Owned release drawable is not 1920x1080: ' + str(record))
        # Revalidate immediately before reading pixels, in case a window vanished.
        value = window.get_full_property(d.intern_atom('_NET_WM_PID'), X.AnyPropertyType)
        if value is None or int(value.value[0]) != pid:
            raise RuntimeError('Drawable PID changed before capture.')
        reply = window.get_image(0, 0, geometry.width, geometry.height, X.ZPixmap, 0xffffffff)
        if reply is None:
            raise RuntimeError('XGetImage returned no pixels for the owned window.')
        fmt = next(f for f in d.display.info.pixmap_formats if f.depth == geometry.depth)
        visual = next(v for dep in d.screen().allowed_depths for v in dep.visuals
                      if v.visual_id == attrs.visual)
        if (fmt.bits_per_pixel != 32 or d.display.info.image_byte_order != X.LSBFirst
                or (visual.red_mask, visual.green_mask, visual.blue_mask) != (0xff0000, 0xff00, 0xff)):
            raise RuntimeError('Unsupported X11 pixel layout; refusing to misdecode the image.')
        stride = ((geometry.width * fmt.bits_per_pixel + fmt.scanline_pad-1)
                  // fmt.scanline_pad) * (fmt.scanline_pad//8)
        image = Image.frombytes('RGB', (geometry.width, geometry.height), reply.data,
                                'raw', 'BGRX', stride, 1)
        image.save(output)
        stats = ImageStat.Stat(image)
        center = ImageStat.Stat(image.crop((384, 216, 1536, 864)))
        metrics = dict(**record, pixelBytes=len(reply.data), imageSha256=sha(output),
                       mean=stats.mean, stddev=stats.stddev, centerMean=center.mean,
                       centerStddev=center.stddev,
                       nonBlank=sum(stats.stddev)>30 and sum(center.stddev)>15,
                       caveat='Non-blank pixels require human scene review; no input or art acceptance.')
        write(output.with_suffix('.metrics.json'), metrics)
        print(json.dumps(metrics))
    finally:
        d.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--launch', action='store_true')
    parser.add_argument('--capture-pid', type=int, help=argparse.SUPPRESS)
    parser.add_argument('--capture-output', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.capture_pid:
        window_capture(args.capture_pid, args.capture_output)
        return
    if args.output is None:
        parser.error('--output is required')
    out = args.output.resolve()
    exe = ROOT/'unity/AthenHill/Builds/Linux/AthenHill.x86_64'
    qa = out/'qa-request'
    command = [str(exe), '-force-glcore', '-screen-fullscreen', '0',
               '-screen-width', '1920', '-screen-height', '1080',
               '-logFile', str(out/'Player.log'), '--athen-qa', str(qa),
               '--athen-qa-background']
    scoped = dict(DISPLAY=':0', WAYLAND_DISPLAY='wayland-1',
                  HYPRLAND_INSTANCE_SIGNATURE=SIGNATURE,
                  __GLX_VENDOR_LIBRARY_NAME='nvidia', XDG_CONFIG_HOME=str(out/'config'),
                  XDG_CACHE_HOME=str(out/'cache'), XDG_DATA_HOME=str(out/'data'))
    removed = ['LIBGL_ALWAYS_SOFTWARE', 'GALLIUM_DRIVER', 'MESA_LOADER_DRIVER_OVERRIDE',
               'LIBGL_KOPPER_DRI2', 'MESA_VK_DEVICE_SELECT', 'VK_ICD_FILENAMES',
               'VK_DRIVER_FILES', 'ATHEN_NATIVE_PID', 'ATHEN_NATIVE_DIR', 'ATHEN_UI_XVFB',
               'ATHEN_EVIDENCE']
    env = {k:v for k,v in os.environ.items() if k not in removed}
    env.update(scoped)
    report = dict(complete=False, scope='Release static owned-window render observation only',
                  noInput=True, noFocusChanges=True, desktopLocked=True,
                  command=command, scopedEnvironment=scoped, removedOverrides=removed,
                  freshPreferences=True, suppliedPreferences=False, captures=[],
                  renderProfile='Fresh release defaults; actual quality counters unavailable with QA disabled')
    if not args.launch:
        print(json.dumps(report, indent=2))
        return
    if out.exists():
        raise RuntimeError('Use a new evidence directory; no file reuse.')
    if not exe.is_file():
        raise RuntimeError('Release executable is missing.')
    out.mkdir(parents=True)
    for directory in (out/'config', out/'cache', out/'data', qa):
        directory.mkdir()
    write(qa/'command.json', dict(id=uuid.uuid4().hex, action='settingsSnapshot'))
    identity = [exe, exe.parent/'AthenHill_Data/Managed/AthenHill.Runtime.dll',
                exe.parent/'AthenHill_Data/level0', exe.parent/'AthenHill_Data/globalgamemanagers']
    report['buildFiles'] = [dict(path=str(p), bytes=p.stat().st_size, sha256=sha(p))
                            for p in identity if p.exists()]
    write(out/'launch.json', report)
    child = None
    started = time.monotonic()
    try:
        child = subprocess.Popen(command, env=env, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.STDOUT, start_new_session=True)
        report['pid'] = child.pid
        (out/'pid').write_text(str(child.pid))
        deadline = time.monotonic()+90
        owned = []
        while time.monotonic()<deadline:
            if child.poll() is not None:
                raise RuntimeError('Release exited before its window was available.')
            clients = json.loads(hypr(['-j', 'clients'], env))
            owned = [c for c in clients if c.get('pid') == child.pid]
            if owned:
                break
            time.sleep(.25)
        if len(owned) != 1:
            raise RuntimeError('Expected exactly one owned Hyprland client; found ' + str(len(owned)))
        write(out/'owned-client-before.json', owned[0])
        address = owned[0]['address']
        if not re.fullmatch(r'0x[0-9a-fA-F]+', address):
            raise RuntimeError('Invalid compositor client address.')
        dispatches = []
        for action in [f'hl.dsp.window.float({{window="address:{address}",action="set"}})',
                       f'hl.dsp.window.resize({{window="address:{address}",x=1536,y=864}})']:
            # Match ownership again immediately before the only WM mutations.
            current = [c for c in json.loads(hypr(['-j','clients'],env))
                       if c.get('address')==address and c.get('pid')==child.pid]
            if len(current)!=1:
                raise RuntimeError('Owned client identity changed before resizing.')
            dispatches.append(dict(command=action, result=hypr(['dispatch',action],env)))
        write(out/'owned-window-dispatches.json', dispatches)
        for index, delay in enumerate((8, 10, 10), start=1):
            end = time.monotonic()+delay
            while time.monotonic()<end:
                if child.poll() is not None:
                    raise RuntimeError('Release exited before capture.')
                time.sleep(min(.25, max(.01,end-time.monotonic())))
            output = out/f'owned-window-{index:02d}.png'
            capture = subprocess.run([sys.executable, str(Path(__file__).resolve()),
                                      '--capture-pid', str(child.pid), '--capture-output', str(output)],
                                     env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     text=True, timeout=12)
            row = dict(index=index, elapsedSeconds=time.monotonic()-started,
                       returncode=capture.returncode, stdout=capture.stdout, stderr=capture.stderr)
            report['captures'].append(row)
            write(out/f'capture-attempt-{index:02d}.json',row)
            forbidden = [p.name for p in qa.iterdir() if p.name!='command.json']
            if forbidden:
                raise RuntimeError('Release responded to development QA flags: '+str(forbidden))
        report['ownedClientAfter'] = [c for c in json.loads(hypr(['-j','clients'],env)) if c.get('pid')==child.pid]
        log = (out/'Player.log').read_text(errors='replace')
        report['rendererLogLines'] = [l for l in log.splitlines() if re.search(r'Renderer:|Vendor:|Version:|GfxDevice|OpenGL',l)]
        report['errorLines'] = [l for l in log.splitlines() if re.search(r'Exception:|NullReferenceException|Assertion|Shader error|failed to allocate|heap=3',l,re.I)]
        renderer = next((l for l in log.splitlines() if 'Renderer:' in l),'')
        report['normalNvidiaOpenGL'] = 'nvidia' in renderer.lower() and 'zink' not in renderer.lower() and 'llvmpipe' not in renderer.lower() and 'opengl' in log.lower()
        report['developmentQaIgnored'] = not any(p.name!='command.json' for p in qa.iterdir())
        metrics = [json.loads(p.read_text()) for p in sorted(out.glob('owned-window-*.metrics.json'))]
        report['nonBlankOwnedCaptures'] = sum(bool(m['nonBlank']) for m in metrics)
        report['complete'] = (report['normalNvidiaOpenGL'] and report['developmentQaIgnored']
                              and not report['errorLines'] and report['nonBlankOwnedCaptures']>0)
        if not report['complete']:
            report['limitation'] = 'Static render check incomplete/failed; inspect capture and log evidence. No release bridge or desktop capture fallback was used.'
    except BaseException as error:
        report['error'] = str(error)
    finally:
        if child is not None:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=10)
                    report['termination'] = 'SIGTERM to this child only'
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=10)
                    report['termination'] = 'SIGKILL to this child only after timeout'
            report['exitCode'] = child.returncode
        report['elapsedSeconds'] = time.monotonic()-started
        report['processStopped'] = child is None or child.poll() is not None
        write(out/'report.json',report)
        print(json.dumps({k:report.get(k) for k in ('complete','pid','normalNvidiaOpenGL','nonBlankOwnedCaptures','error','limitation','processStopped')}))
    if not report['complete']:
        raise SystemExit(2)


if __name__=='__main__':
    main()
