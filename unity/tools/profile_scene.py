"""Profile a native scenario with the Unity profiler and rank CPU markers.

  uv run --offline --with python-xlib --with pillow python unity/tools/profile_scene.py OUT --save SAVE_DIR \
      [--camera cam_depot_fight] [--hour 13] [--seconds 12] [--video antiAliasing=32]

Continues the given save (copied, never modified), switches to a fixed review camera, records a profiler capture
(`-profiler-enable -profiler-log-file`) while idling, quits, then runs Editor/ProfileDump in a batch Editor over
the last frames and prints the top self-time markers per thread. Uses the re-QA harness for launch/input.
"""
import argparse, json, shutil, subprocess, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'unity/evidence/gameplay-v2/20260930-reqa'))
import qa  # noqa: E402

p = argparse.ArgumentParser(); p.add_argument('out', type=Path); p.add_argument('--save', type=Path, required=True)
p.add_argument('--camera', default='cam_depot_fight'); p.add_argument('--hour', type=float, default=13)
p.add_argument('--seconds', type=float, default=12); p.add_argument('--video', default='')
a = p.parse_args()
out = a.out.resolve(); out.mkdir(parents=True, exist_ok=False)
save = out / 'save'; shutil.copytree(a.save, save)
raw = out / 'capture.raw'
video = {k: json.loads(v) for k, v in (kv.split('=') for kv in a.video.split(',') if kv)}
qa.launch(out / 'run', save_dir=save, video=video, extra=['-profiler-enable', '-profiler-log-file', str(raw), '-profiler-maxusedmemory', '268435456'])
try:
    qa.wait_menu(); qa.focus(); qa.tap('Return'); qa.wait(lambda: qa.state() == 'Play', 30, what='Play after Continue')
    qa.cmd('resize', width=1920, height=1080); time.sleep(2)
    qa.cmd('timeSet', hour=a.hour); qa.cmd('timePause', paused=True)
    qa.view(a.camera); time.sleep(4)
    qa.capture('view'); time.sleep(a.seconds)
    qa.cmd('profileStart'); time.sleep(6); qa.cmd('profileStop'); time.sleep(.5)
    prof = qa.summarize_profile(qa.read('profile.json')); (out / 'frame-time.json').write_text(json.dumps(prof, indent=1))
    print('frame time', json.dumps(prof))
finally:
    qa.stop()
U = str(Path.home() / 'Unity/Hub/Editor/6000.6.0f1/Editor/Unity')
subprocess.run(['systemd-run', '--user', '--scope', '-q', '-p', 'MemoryMax=10G', U, '-batchmode', '-nographics', '-projectPath', str(ROOT / 'unity/AthenHill'),
                '-executeMethod', 'AthenHill.Editor.ProfileDump.DumpBatch', '--raw', str(raw), '--out', str(out / 'markers.json'), '--last', '600',
                '-logFile', str(out / 'dump.log')], check=False)
m = json.loads((out / 'markers.json').read_text())
print('frames', m['frames'], 'frameMs', m['frameMs'])
for thread, rows in m['threads'].items():
    print('==', thread); [print(f"  {r['msPerFrame']:7.3f} ms  {r['marker']}") for r in list(rows)[:18]]
