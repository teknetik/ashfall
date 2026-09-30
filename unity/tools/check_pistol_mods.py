"""Native check of the visible pistol mods: continue a save (copied) with the chosen mods fitted, draw the pistol in the
Berms and capture first-person (hip and aim) and third-person views at noon.

  uv run --offline --with python-xlib --with pillow python unity/tools/check_pistol_mods.py OUT --save SAVE_DIR [--mk2]

--mk2 rewrites the copied save's fitted slots to the Mark II grip/barrel/cell (the original save is never touched).
"""
import argparse, json, shutil, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'unity/evidence/gameplay-v2/20260930-reqa2'))
import qa  # noqa: E402

p = argparse.ArgumentParser(); p.add_argument('out', type=Path); p.add_argument('--save', type=Path, required=True); p.add_argument('--mk2', action='store_true')
a = p.parse_args()
out = a.out.resolve(); out.mkdir(parents=True, exist_ok=False)
save = out / 'save'; shutil.copytree(a.save, save)
if a.mk2:
    f = save / 'ward-save.json'; s = json.loads(f.read_text())
    s['crafting']['fitted'] = [{'slot': 'barrel', 'itemId': 'barrel_lattice_focused'}, {'slot': 'cell', 'itemId': 'cell_overclocked'}, {'slot': 'grip', 'itemId': 'grip_gyro_braced'}]
    f.write_text(json.dumps(s))
qa.launch(out / 'run', save_dir=save)
report = {}
try:
    qa.wait_menu(); qa.focus(); qa.tap('Return'); qa.wait(lambda: qa.state() == 'Play', 30, what='Play after Continue')
    qa.cmd('resize', width=1920, height=1080); time.sleep(2)
    qa.cmd('timeSet', hour=12.5); qa.cmd('timePause', paused=True)
    qa.goto('checkpoint_firingline'); time.sleep(1.5)
    qa.focus(); qa.tap('7', settle=.8)
    report['armed'] = qa.snap()['combat']['Armed']; report['crafting'] = qa.craft()
    # First person, hip and aim.
    qa.cmd('cameraBoom', boom=0.0); qa.yaw(200); qa.pitch(4); time.sleep(1.2)
    qa.capture('fp-hip', layout=False)
    qa.button(3, True); time.sleep(.6); qa.capture('fp-aim', layout=False); qa.button(3, False); time.sleep(.4)
    # Third person from the right side and three-quarter.
    qa.cmd('cameraBoom', boom=2.2); qa.yaw(110); qa.pitch(8); time.sleep(1.2); qa.capture('tp-side', layout=False)
    qa.yaw(160); time.sleep(1); qa.capture('tp-34', layout=False)
    # Fire once to see the muzzle flash leave the new barrel.
    qa.cmd('cameraBoom', boom=0.0); qa.yaw(200); qa.pitch(4); time.sleep(1)
    qa.tap('f', secs=.05, settle=.02); time.sleep(.03); qa.capture('fp-fire', layout=False)
    report['errors'] = qa.log_errors()
finally:
    qa.stop()
(out / 'report.json').write_text(json.dumps(report, indent=1, default=str)); print(json.dumps(report, default=str)[:1500])
