"""Run existing native checks against an already launched development player.

This script never launches a game or Editor. Root owns build, launch, authoring
app shutdown and release verification. Set ATHEN_NATIVE_DIR to a fresh evidence
folder made by launch_phase1_qa.py; ATHEN_NATIVE_PID defaults to that folder's pid.

Usage: python verify_reference_street.py
       python verify_reference_street.py --steps lighting
       python verify_reference_street.py --collate-only

The default run captures matched views, records one unmeasured 41-point warm-up,
times the next traversal, exercises both porches with real keyboard/mouse input,
profiles the existing city-loop checks separately, and captures night/dawn/noon/
late-day lighting. All subprocess outcomes and missing evidence are retained.
No numeric or Boolean field here is an art-acceptance decision.
"""
import argparse
import asyncio
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / 'unity/tools'
EVIDENCE = ROOT / 'unity/evidence/reference-street/20260909'
sys.path.insert(0, str(TOOLS))


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def read(path):
    return json.loads(path.read_text()) if path.exists() else None


def write(path, data):
    path.write_text(json.dumps(data, indent=2))


def sha(path):
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def identity():
    baseline = read(EVIDENCE / 'baseline.json') or {}
    paths = set(baseline.get('files', {}))
    paths.update(str(p.relative_to(ROOT)) for p in (ROOT / 'art/reference_street_20260909').rglob('*')
                 if p.is_file() and p.suffix in {'.py', '.blend', '.png', '.json'})
    paths.update(str(p.relative_to(ROOT)) for p in (ROOT / 'unity/AthenHill/Assets/AthenHill').rglob('*ReferenceStreet*')
                 if p.is_file())
    # Asset contents, profiles and GUIDs are inside the new revision directory;
    # matching only its folder name would omit the files that actually ship.
    authored = ROOT / 'unity/AthenHill/Assets/AthenHill/Art/ReferenceStreet/20260909'
    paths.update(str(p.relative_to(ROOT)) for p in authored.rglob('*') if p.is_file())
    shader_root = ROOT / 'unity/AthenHill/Assets/AthenHill'
    paths.update(str(p.relative_to(ROOT)) for p in shader_root.rglob('*Reference*')
                 if p.is_file() and p.suffix in {'.shader', '.hlsl', '.cginc', '.cs', '.meta'})
    # level0 alone does not identify material/texture changes packed separately.
    for kind in ['Linux', 'LinuxDevelopment']:
        data = ROOT / 'unity/AthenHill/Builds' / kind / 'AthenHill_Data'
        if not data.is_dir():
            continue
        paths.update(str(p.relative_to(ROOT)) for p in data.iterdir()
                     if p.is_file() and (p.suffix in {'.assets', '.resS', '.resource', '.unity3d'}
                                         or p.name in {'globalgamemanagers', 'boot.config'}))
    return {p: sha(ROOT / p) for p in sorted(paths)}


def is_authoring_process(executable, name):
    """The native player shares Unity's thread name; prefer executable identity."""
    if executable is not None:
        if executable.lower() == 'athenhill.x86_64':
            return False
        # Unity asset-import workers run the Editor binary and remain blockers.
        return executable.lower() in {'unity', 'blender'}
    # A thread-name fallback is only appropriate when /proc/exe is unavailable.
    return name == 'Unity' or name.startswith('Unity Main') or name.lower() == 'blender'


def authoring_processes():
    found = []
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            name = (entry / 'comm').read_text().strip()
            try:
                executable = Path(os.readlink(entry / 'exe')).name.removesuffix(' (deleted)')
            except (FileNotFoundError, PermissionError, ProcessLookupError):
                executable = None
            if is_authoring_process(executable, name):
                found.append({'pid': int(entry.name), 'name': name, 'executable': executable})
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
    return found


def memory_observation(out):
    pid = (out / 'pid').read_text().strip()
    status = Path('/proc') / pid / 'status'
    report = {'utc': utc(), 'pid': int(pid), 'memory': None,
              'residentTextureBytes': None, 'gpuFrameTimeMs': None,
              'note': 'Point observation; GPU process memory includes more than textures.'}
    if status.exists():
        report['memory'] = dict(line.split(':', 1) for line in status.read_text().splitlines()
                                if line.startswith(('VmRSS:', 'VmHWM:', 'VmSize:')))
    try:
        xml = ET.fromstring(subprocess.check_output(['nvidia-smi', '-q', '-x'], text=True, timeout=10))
        gpu = xml.find('gpu')
        process = next((p for p in xml.findall('.//process_info') if p.findtext('pid') == pid), None)
        report.update(gpu=gpu.findtext('product_name'), driver=xml.findtext('driver_version'),
                      totalVram=gpu.findtext('fb_memory_usage/total'),
                      allProcessesGpuMemory=gpu.findtext('fb_memory_usage/used'),
                      nativeGpuMemory=process.findtext('used_memory') if process is not None else None)
    except (OSError, subprocess.SubprocessError, ET.ParseError, AttributeError) as error:
        report['gpuObservationUnavailable'] = str(error)
    return report


def percentile(values, p):
    v = sorted(values)
    i = (len(v) - 1) * p
    a = int(i)
    b = min(a + 1, len(v) - 1)
    return v[a] + (v[b] - v[a]) * (i - a)


def summarize(frames):
    if not frames:
        return None
    dt = [v['dt'] * 1000 for v in frames if v.get('dt', 0) > 0]
    if not dt:
        return None
    result = dict(frames=len(dt), seconds=sum(dt) / 1000,
                  averageFps=len(dt) * 1000 / sum(dt), p50Ms=percentile(dt, .5),
                  p95Ms=percentile(dt, .95), p99Ms=percentile(dt, .99), maxMs=max(dt),
                  hitchesOver33ms=sum(v > 33.33 for v in dt), hitchesOver50ms=sum(v > 50 for v in dt))
    for key in ['mainMs', 'renderMs', 'cpuMs', 'gpuMs', 'draws', 'tris', 'batches', 'setPass']:
        values = [v[key] for v in frames if v.get(key, -1) > 0]
        result[key] = dict(samples=len(values), mean=statistics.mean(values),
                           p95=percentile(values, .95), max=max(values)) if values else None
    result['meetsAverageAndP99Target'] = result['averageFps'] >= 60 and result['p99Ms'] <= 16.67
    return result


async def subprocess_check(out, script, args=()):
    logfile = out / ('qa-' + Path(script).stem + '.log')
    assert not logfile.exists(), 'Preserve previous check log: ' + str(logfile)
    script_path = Path(script)
    if not script_path.is_absolute():
        script_path = TOOLS / script_path
    command = [sys.executable, str(script_path), *map(str, args)]
    entry = {'command': command, 'startedUtc': utc(), 'log': logfile.name}
    process = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.PIPE,
                                                   stderr=asyncio.subprocess.STDOUT)
    with logfile.open('wb') as log:
        async for line in process.stdout:
            log.write(line)
            log.flush()
            print(line.decode(errors='replace').rstrip(), flush=True)
    entry.update(finishedUtc=utc(), returncode=await process.wait())
    return entry


async def lighting(out):
    from native_client import Client
    from desktop_input import focus, key
    from PIL import Image
    c = Client()
    d = focus()
    report = {'complete': False, 'hours': [0, 6.5, 12, 17.5], 'views': [],
              'scope': 'Fixed native views; diagnostic placement, no traversal or art acceptance claim.'}
    if read(out / 'snapshot.json')['session']['state'] == 'Paused':
        key(d, 'Escape', True)
        await asyncio.sleep(.08)
        key(d, 'Escape', False)
        await asyncio.sleep(.3)
    try:
        await c.command({'action': 'timePause', 'paused': True})
        for hour in report['hours']:
            await c.command({'action': 'timeSet', 'hour': hour})
            await asyncio.sleep(3)
            await c.command({'action': 'timeState'})
            state = read(out / 'time-state.json')
            for camera in ['cam_audit_field_supply_door', 'cam_audit_finery_door',
                           'cam_audit_finery_side_right', 'cam_courtyard_facade', 'cam_reference_street']:
                focus()
                await c.command({'action': 'view', 'camera': camera})
                await asyncio.sleep(.7)
                name = camera + '-reference-hour-' + str(hour).replace('.', 'p')
                path = out / (name + '.png')
                assert not path.exists(), 'Preserve previous lighting capture.'
                await c.command({'action': 'capture', 'name': name})
                for attempt in range(70):
                    try:
                        with Image.open(path) as im:
                            im.load()
                            dimensions = list(im.size)
                        break
                    except (FileNotFoundError, OSError):
                        await asyncio.sleep(.1)
                else:
                    raise TimeoutError(name)
                assert dimensions == [1920, 1080], dimensions
                report['views'].append(dict(camera=camera, hour=hour, path=path.name,
                                           sha256=sha(path), dimensions=dimensions, lighting=state,
                                           snapshot=read(out / 'snapshot.json')))
                write(out / 'reference-lighting.json', report)
                print('Captured ' + name, flush=True)
        report['complete'] = True
    except Exception as error:
        report['error'] = str(error)
        raise
    finally:
        write(out / 'reference-lighting.json', report)
        await c.command({'action': 'timeReset'})
        await c.command({'action': 'view', 'camera': 'follow'})


def collate(out):
    baseline = read(EVIDENCE / 'baseline.json') or {}
    installation = read(EVIDENCE / 'installation.json')
    run = read(out / 'reference-qa-run.json')
    before_hashes = read(out / 'reference-identity-before.json')
    after_hashes = identity()
    write(out / 'reference-identity-after.json', after_hashes)
    preserved = None
    if installation is not None:
        preserved = {k: installation.get(k) for k in
                     ['gameplayPreserved', 'collidersPreserved', 'gameplayBeforeSha256',
                      'gameplayAfterSha256', 'collisionBeforeSha256', 'collisionAfterSha256']}
        preserved['source'] = str((EVIDENCE / 'installation.json').relative_to(ROOT))
        preserved['scope'] = 'Installer comparisons at installation time; unavailable signature hashes remain null.'
        preserved['signatureFiles'] = {}
        for kind in ['gameplay', 'collision']:
            before = EVIDENCE / (kind + '-before.json')
            after = EVIDENCE / (kind + '-after.json')
            a, b = sha(before), sha(after)
            preserved['signatureFiles'][kind] = {
                'beforePath': str(before.relative_to(ROOT)), 'afterPath': str(after.relative_to(ROOT)),
                'beforeSha256': a, 'afterSha256': b, 'identical': a == b if a and b else None}
    documents = {}
    for name in ['warmup-route.json', 'measured-route.json', 'reference-proximity.json',
                 'city-loop.json', 'reference-lighting.json', 'field-captures.json', 'finery-captures.json',
                 'traversal-performance.json', 'interaction-performance.json', 'settings.json', 'environment.json']:
        value = read(out / name)
        documents[name] = {'present': value is not None, 'sha256': sha(out / name),
                           'complete': value.get('complete') if isinstance(value, dict) else None}
    frames = read(out / 'traversal-frames.json')
    interaction = read(out / 'interaction-frames.json')
    issues = []
    log = out / 'Player.log'
    if log.exists():
        pattern = re.compile(r'Exception:|NullReferenceException|MissingReferenceException|Shader error|shader.*(?:failed|unsupported)', re.I)
        issues = [{'line': i, 'text': line[:500]} for i, line in enumerate(log.read_text(errors='replace').splitlines(), 1)
                  if pattern.search(line)]
    settings = read(out / 'settings.json')
    environment = read(out / 'environment.json')
    profile_matches = None
    if settings and environment:
        video = settings.get('video', {})
        profile_matches = (environment.get('width') == 1920 and environment.get('height') == 1080
                           and settings.get('renderScale') == 1 and environment.get('actorCount') == 9
                           and environment.get('api') == 'OpenGLCore' and video.get('vSync') is False
                           and video.get('frameLimit') == 0)
    unchanged = None if before_hashes is None else before_hashes == after_hashes
    release = EVIDENCE / 'release-native/report.json'
    report = dict(utc=utc(), nativeFolder=str(out), run=run, documents=documents,
                  installerPreservation=preserved, settings=settings, environment=environment,
                  measuredProfileMatches=profile_matches, filesUnchangedDuringRun=unchanged,
                  priorBuildComparisons={p: after_hashes.get(p) == h for p, h in baseline.get('files', {}).items()
                                         if p.endswith(('manifest.json', 'packages-lock.json', 'ProjectVersion.txt', 'Assembly-CSharp.dll'))},
                  walking=summarize(frames), modalInteractions=summarize(interaction),
                  actorRoutePreservation=read(EVIDENCE / 'actor-route-preservation.json'),
                  playerLog={'present': log.exists(), 'sha256': sha(log), 'matchedIssues': issues,
                             'noMatchedIssues': not issues if log.exists() else None},
                  releaseSmoke=read(release), memory=read(out / 'reference-memory.json'),
                  visualAcceptance=None,
                  limitations=['Visual scores and user acceptance require native image/motion review.',
                               'Timing applies only to this recorded build, process state and route.',
                               'Submitted triangles include render passes; unavailable counters remain null.',
                               'City-loop diagnostic landmark placement is distinct from real traversal.',
                               'No before/after performance delta is inferred from unmatched prior measurements.'])
    write(out / 'reference-verification.json', report)
    return report


async def run_checks(out, steps):
    from native_client import Client
    c = Client()
    path = out / 'reference-qa-run.json'
    assert not path.exists(), 'Use fresh evidence for another run; --collate-only reads the existing run.'
    assert Path('/proc', os.environ['ATHEN_NATIVE_PID']).exists(), 'Native player PID is absent.'
    await c.command({'action': 'settingsSnapshot'})
    session = read(out / 'snapshot.json')['session']
    if 'city-loop' in steps:
        assert session.get('boughtFlask') is False and session.get('soldScrap') is False, 'Use a fresh native session for atomic buy/sell checks.'
    report = {'startedUtc': utc(), 'requestedSteps': steps, 'steps': [], 'complete': False}
    write(path, report)
    write(out / 'reference-identity-before.json', identity())
    try:
        for step in steps:
            print('Starting reference street QA: ' + step, flush=True)
            entry = {'step': step, 'startedUtc': utc(), 'complete': False, 'commands': []}
            report['steps'].append(entry)
            write(path, report)
            if step == 'captures':
                extra = list(dict.fromkeys([*(read(EVIDENCE / 'extra-cameras.json') or []), 'cam_reference_street']))
                after_cameras = out / 'reference-after-extra-cameras.json'
                assert not after_cameras.exists(), 'Preserve previous after-camera manifest.'
                write(after_cameras, extra)
                for family, name in [('field_supply', 'field'), ('finery', 'finery')]:
                    args = [out, '--building', family, '--report', name + '-captures.json']
                    if family == 'field_supply':
                        args += ['--extra', after_cameras]
                    entry['commands'].append(await subprocess_check(out, 'capture_building_pass.py', args))
                    # Distinguish the two capture logs while preserving each.
                    (out / 'qa-capture_building_pass.log').rename(out / ('qa-capture-' + name + '.log'))
                    entry['commands'][-1]['log'] = 'qa-capture-' + name + '.log'
                    assert entry['commands'][-1]['returncode'] == 0, 'Capture subprocess failed.'
            elif step == 'traversal':
                processes = authoring_processes()
                entry['authoringProcessesBeforeMeasurement'] = processes
                assert not processes, 'Close authoring Unity/Blender processes before timing: ' + str(processes)
                write(out / 'reference-memory.json', memory_observation(out))
                entry['commands'].append(await subprocess_check(out, 'check_building_traversal.py', ['--record-warmup']))
                assert entry['commands'][-1]['returncode'] == 0, 'Traversal subprocess failed.'
            elif step == 'porches':
                entry['commands'].append(await subprocess_check(out, ROOT / 'art/reference_street_20260909/check_reference_proximity.py'))
                assert entry['commands'][-1]['returncode'] == 0, 'Porch proximity subprocess failed.'
            elif step == 'city-loop':
                await c.command({'action': 'profileStart'})
                try:
                    entry['commands'].append(await subprocess_check(out, 'city_loop_check.py'))
                finally:
                    await c.command({'action': 'profileStop'})
                    frames = read(out / 'profile.json')
                    write(out / 'interaction-frames.json', frames)
                    write(out / 'interaction-performance.json', {'complete': bool(entry['commands']) and entry['commands'][-1]['returncode'] == 0,
                                                                 'scope': 'Separate city-loop interaction profile.', 'allFrames': summarize(frames)})
                assert entry['commands'][-1]['returncode'] == 0, 'City-loop subprocess failed.'
            elif step == 'lighting':
                await lighting(out)
            entry.update(complete=True, finishedUtc=utc())
            write(path, report)
        report['complete'] = True
    except Exception as error:
        report['error'] = repr(error)
        raise
    finally:
        report['finishedUtc'] = utc()
        write(path, report)
        collate(out)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collate-only', action='store_true')
    parser.add_argument('--steps', default='captures,traversal,porches,city-loop,lighting')
    args = parser.parse_args()
    out = Path(os.environ['ATHEN_NATIVE_DIR']).resolve()
    assert out.is_dir(), 'Launch the development player separately first.'
    os.environ.setdefault('ATHEN_NATIVE_PID', (out / 'pid').read_text().strip())
    os.environ['ATHEN_EVIDENCE'] = str(out)
    if args.collate_only:
        collate(out)
    else:
        steps = args.steps.split(',')
        assert set(steps) <= {'captures', 'traversal', 'porches', 'city-loop', 'lighting'} and len(steps) == len(set(steps))
        asyncio.run(run_checks(out, steps))
