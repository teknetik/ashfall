"""Launch once; --smoke-leg supervises only its own player and capture child."""
import argparse
import base64
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
TOOLS = Path(__file__).resolve().parent


def save(out, report):
    temporary = out / 'launch-report.tmp'
    temporary.write_text(json.dumps(report, indent=2))
    temporary.replace(out / 'launch-report.json')


def exit_status(code):
    return 128 - code if code < 0 else code


class PlayerExited(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__('Owned native player exited: %s' % code)


class Terminated(Exception):
    pass


def check_player(player):
    code = player.poll()
    if code is not None:
        raise PlayerExited(code)


def stop_owned(process, interrupt=False):
    if process is None:
        return None
    if process.poll() is None:
        process.send_signal(signal.SIGINT if interrupt else signal.SIGTERM)
        try:
            return process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
    return process.wait(timeout=5)


def wait_bridge(player, out, timeout: float = 60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        check_player(player)
        try:
            snapshot = json.loads((out / 'snapshot.json').read_text())
            if 'frame' in snapshot and 'session' in snapshot:
                return
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        time.sleep(.2)
    raise TimeoutError('Native bridge did not start within 60s')


def wait_child(player, child, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        check_player(player)
        code = child.poll()
        if code is not None:
            return exit_status(code)
        time.sleep(.1)
    raise TimeoutError('Owned helper exceeded %ss' % timeout)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence', type=Path)
    parser.add_argument('--capped', action='store_true')
    parser.add_argument('--background', action='store_true')
    parser.add_argument('--display', default=os.environ.get('DISPLAY'))
    parser.add_argument('--smoke-leg', choices=('left', 'right'))
    args = parser.parse_args(argv)
    if not args.display:
        parser.error('DISPLAY is unset; pass --display')
    if args.smoke_leg and args.background:
        parser.error('Real-input smoke cannot use background static capture')
    return args


def launch(args):
    out = args.evidence.resolve()
    # No rotations, reuse of stale snapshots, or global player termination.
    out.mkdir(parents=True, exist_ok=False)
    report: dict = dict(status='starting', complete=False, leg=args.smoke_leg,
                  evidence=str(out), playerPid=None, playerReturncode=None)
    save(out, report)
    player = child = None
    detached = False
    code = 1
    try:
        video = json.loads((ROOT / 'unity/evidence/courtyard/20260908/after-native/settings.json').read_text())['video']
        if args.capped:
            video.update(vSync=True, frameLimit=60)
        encoded = base64.b64encode(json.dumps(video).encode()).decode()
        for vendor, product in [('unknown', 'unknown'), ('Free Column', 'Athen Hill')]:
            folder = out / 'config/unity3d' / vendor / product
            folder.mkdir(parents=True)
            (folder / 'prefs').write_text('<?xml version="1.0" encoding="utf-8"?><unity_prefs version_major="1" version_minor="1"><pref name="AthenHill.Settings.v1.QA.Video" type="string">' + encoded + '</pref></unity_prefs>')
        exe = Path(os.environ.get('ATHEN_PLAYER_EXE') or ROOT / 'unity/AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64')  # override: matched baseline build copy
        arguments = [str(exe), '-force-glcore', '-screen-width', '1920', '-screen-height', '1080', '-screen-fullscreen', '0', '-logFile', str(out / 'Player.log'), '--athen-qa', str(out)]
        if args.background:
            arguments.append('--athen-qa-background')
        env = dict(os.environ, DISPLAY=args.display, XDG_CONFIG_HOME=str(out / 'config'))
        report['playerCommand'] = arguments
        with (out / 'player-stdio.log').open('w') as log:
            player = subprocess.Popen(arguments, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        report['playerPid'] = player.pid
        (out / 'pid').write_text(str(player.pid))
        save(out, report)
        wait_bridge(player, out)
        report['status'] = 'ready'
        save(out, report)
        if not args.smoke_leg:
            detached = True
            code = 0
            report['status'] = 'detached'  # Legacy launch-only mode; not a smoke pass.
        else:
            env.update(ATHEN_NATIVE_DIR=str(out), ATHEN_NATIVE_PID=str(player.pid))
            for name, command, timeout in [
                ('window', ['bash', str(TOOLS / 'float_player_window.sh'), str(player.pid)], 15),
                ('capture', [sys.executable, str(TOOLS / 'capture_basic_general_sign.py'), 'smoke', '--leg', args.smoke_leg], 800),
            ]:
                report['status'] = name
                save(out, report)
                with (out / (name + '-stdio.log')).open('w') as log:
                    child = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                report[name + 'Pid'] = child.pid
                save(out, report)
                code = wait_child(player, child, timeout)
                report[name + 'Returncode'] = child.returncode
                save(out, report)
                if code:
                    break
            report.update(status='passed' if code == 0 else 'failed', complete=code == 0)
    except PlayerExited as exc:
        code = exit_status(exc.code) or 1
        report.update(status='failed', error=str(exc))
    except KeyboardInterrupt:
        code = 130
        report.update(status='failed', error='Interrupted')
    except Terminated:
        code = 143
        report.update(status='failed', error='SIGTERM')
    except Exception as exc:
        code = 124 if isinstance(exc, TimeoutError) else 1
        report.update(status='failed', error=repr(exc))
    finally:
        if not detached:
            # Even a cleanup failure must leave a report and attempt the other PID.
            for name, process in [('child', child), ('player', player)]:
                try:
                    before = process.poll() if process else None
                    report[name + 'ReturncodeBeforeCleanup'] = before
                    report[name + 'StopRequested'] = process is not None and before is None
                    report[name + 'Returncode'] = stop_owned(process, interrupt=name == 'child')
                    if name == 'player' and before is not None and code == 0:
                        code = exit_status(before) or 1
                        report.update(status='failed', complete=False, error='Player exited before cleanup')
                except Exception as exc:
                    report[name + 'CleanupError'] = repr(exc)
                    code = code or 1
                    report.update(status='failed', complete=False)
        report['exitStatus'] = code
        save(out, report)
        print(json.dumps(report), flush=True)
    return code


def main():
    args = parse_args()
    # SIGTERM must also release owned children and persist diagnostics.
    def interrupted(signum, frame):
        raise Terminated
    signal.signal(signal.SIGTERM, interrupted)
    return launch(args)


if __name__ == '__main__':
    sys.exit(main())
