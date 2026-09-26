"""Opt-in software-rendered functional player on the existing private Xvfb.

This script does not start a display server or change system/desktop settings.
Run only after the coordinating agent has finished GPU timing and handed off.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[3]
DISPLAY_NAME = ':93'
AUTHORITY = '/tmp/ward-qa-xvfb-20260926/Xauthority'
VIDEO = dict(width=1920, height=1080, windowMode=0, preset=3,
             renderPercent=50, shadows=0, antiAliasing=1, textureLimit=2,
             postProcessing=False, vSync=False, frameLimit=30)
SOUND = dict(master=0, music=1, ambience=1, effects=1, muted=False)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence', type=Path)
    parser.add_argument('--launch', action='store_true',
                        help='Actually launch, after the coordinating agent hands off.')
    args = parser.parse_args()
    out = args.evidence.resolve()
    exe = ROOT / 'unity/AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64'
    command = [str(exe), '-force-glcore', '-screen-width', '1920',
               '-screen-height', '1080', '-screen-fullscreen', '0',
               '-logFile', str(out / 'Player.log'), '--athen-qa', str(out),
               '--athen-qa-background']
    scoped = dict(DISPLAY=DISPLAY_NAME, XAUTHORITY=AUTHORITY,
                  LIBGL_ALWAYS_SOFTWARE='1', GALLIUM_DRIVER='llvmpipe',
                  __GLX_VENDOR_LIBRARY_NAME='mesa', XDG_CONFIG_HOME=str(out / 'config'),
                  ATHEN_NATIVE_DIR=str(out), ATHEN_EVIDENCE=str(out), ATHEN_UI_XVFB='1')
    record = dict(purpose='Software functional checks only; no art or performance acceptance',
                  command=command, scopedEnvironment=scoped, video=VIDEO, sound=SOUND,
                  actualRenderer='Unverified until launch', noBatchMode=True)
    if not args.launch:
        print(json.dumps(record, indent=2))
        return
    if out.exists():
        raise RuntimeError('Use a new evidence directory; do not overwrite an earlier run.')
    if not Path(AUTHORITY).is_file():
        raise RuntimeError('Private display authority file is missing. Its contents are never read here.')
    if not exe.is_file():
        raise RuntimeError('Development player executable is missing.')
    out.mkdir(parents=True)
    encoded = {k: base64.b64encode(json.dumps(v).encode()).decode()
               for k, v in [('Video', VIDEO), ('Sound', SOUND)]}
    preferences = '<?xml version="1.0" encoding="utf-8"?><unity_prefs version_major="1" version_minor="1">'
    preferences += ''.join('<pref name="AthenHill.Settings.v1.QA.' + k + '" type="string">' + v + '</pref>'
                           for k, v in encoded.items()) + '</unity_prefs>'
    for vendor, product in [('unknown', 'unknown'), ('Free Column', 'Athen Hill')]:
        folder = out / 'config/unity3d' / vendor / product
        folder.mkdir(parents=True)
        (folder / 'prefs').write_text(preferences)
    identity_files = [exe, exe.parent / 'AthenHill_Data/Managed/AthenHill.Runtime.dll',
                      exe.parent / 'AthenHill_Data/Managed/Assembly-CSharp.dll',
                      exe.parent / 'AthenHill_Data/level0', exe.parent / 'AthenHill_Data/globalgamemanagers']
    record['buildFiles'] = [dict(path=str(p), bytes=p.stat().st_size, sha256=sha(p))
                            for p in identity_files if p.is_file()]
    (out / 'launch.json').write_text(json.dumps(record, indent=2))
    child = subprocess.Popen(command, env=dict(os.environ, **scoped),
                             stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
                             start_new_session=True)
    (out / 'pid').write_text(str(child.pid))
    try:
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            if child.poll() is not None:
                raise RuntimeError('Native player exited during startup; inspect Player.log.')
            if (out / 'snapshot.json').exists() and (out / 'environment.json').exists():
                break
            time.sleep(.2)
        else:
            raise RuntimeError('Native bridge did not start within 120 seconds.')
        environment = json.loads((out / 'environment.json').read_text())
        renderer = environment.get('gpu', '')
        record['actualRenderer'] = renderer
        if not any(name in renderer.lower() for name in ('llvmpipe', 'softpipe')):
            raise RuntimeError('Expected software renderer, received: ' + renderer)
        if environment.get('isBatchMode'):
            raise RuntimeError('Real-input functional run must not be in batch mode.')
        os.environ.update(scoped, ATHEN_NATIVE_PID=str(child.pid))
        # First llvmpipe frames may compile shaders for longer than the ordinary
        # ten-second QA command timeout. This is startup warmup only: tests keep
        # their existing command timeouts, input timings and assertions.
        command_id = uuid.uuid4().hex
        request = out / 'command.tmp'
        request.write_text(json.dumps(dict(action='settingsSnapshot', id=command_id)))
        request.rename(out / 'command.json')
        warmup = []
        warmup_start = time.monotonic()
        deadline = warmup_start + 120
        while time.monotonic() < deadline:
            if child.poll() is not None:
                raise RuntimeError('Native player exited during first-frame warmup.')
            snapshot = json.loads((out / 'snapshot.json').read_text())
            if not warmup or warmup[-1]['frame'] != snapshot['frame']:
                warmup.append(dict(elapsedSeconds=time.monotonic()-warmup_start,
                                   frame=snapshot['frame'], fps=snapshot.get('fps')))
                (out / 'startup-warmup.json').write_text(json.dumps(warmup, indent=2))
            ack_path = out / 'ack.json'
            if ack_path.exists():
                ack = json.loads(ack_path.read_text())
                if ack.get('id') == command_id:
                    if not ack.get('success'):
                        raise RuntimeError('Startup settings command failed: ' + str(ack))
                    break
            time.sleep(.2)
        else:
            raise RuntimeError('Software startup settings command was not acknowledged within 120 seconds.')
        record['startupSettingsWaitSeconds'] = time.monotonic() - warmup_start
        settings = json.loads((out / 'settings.json').read_text())
        actual = {key: settings['video'].get(key) for key in VIDEO}
        if actual != VIDEO or settings['shadowDistance'] != 0 or settings['renderScale'] != .5:
            raise RuntimeError('The functional quality profile was not applied: ' + str(actual))
        record.update(pid=child.pid, actualRenderer=renderer, profileVerified=True)
        (out / 'launch.json').write_text(json.dumps(record, indent=2))
        print(json.dumps(dict(pid=child.pid, evidence=str(out), renderer=renderer)))
    except BaseException as error:
        record.update(pid=child.pid, startupError=str(error))
        (out / 'launch.json').write_text(json.dumps(record, indent=2))
        child.terminate()
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=10)
        raise


if __name__ == '__main__':
    main()
