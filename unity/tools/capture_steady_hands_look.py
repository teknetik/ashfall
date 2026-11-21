#!/usr/bin/env python3
"""Steady Hands bench: look frames only. Opens the bench as found (detached QA job), saves a frame of every bench shot,
closes it, then saves the integration pass's close review cameras (cam_bench_close_*). No input is played.

  ~/.local/state/ward-programme/steady-hands-20261120/native_check.sh bench_look unity/tools/capture_steady_hands_look.py \
      ATHEN_EXE=<build>/AthenHill.x86_64 ATHEN_BENCH_LOOK=always [LOOK_TAG=real0] [LOOK_HOUR=13]

Output: unity/evidence/steady_hands/20261120/look/<tag>/run/*.png and report.json. Written by the orchestrator, 20 Nov 2026.
"""
import os, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TAG = os.environ.get('LOOK_TAG', 'look')
os.environ.setdefault('ATHEN_OUT', str(ROOT / 'unity/evidence/steady_hands/20261120/look' / TAG))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import showcase_qa as S  # noqa: E402
from showcase_qa import qa, ok, note, cap  # noqa: E402

CAMS = [c for c in os.environ.get('LOOK_CAMS', 'cam_bench_close_pistol,cam_bench_close_servo,cam_bench_close_grip,'
                                  'cam_bench_close_materials,cam_bench_close_tools,cam_bench_close_fixtures,'
                                  'cam_bench_close_vise_work,cam_bench_close_mat_low').split(',') if c]


def asm():
    return S.snap().get('assembly') or {}


def body():
    S.launch(run='run')
    S.start(continue_game=False)
    hour = os.environ.get('LOOK_HOUR')
    if hour:
        S.time_set(float(hour)); time.sleep(.5)
    qa.goto('bench_steady_hands'); time.sleep(1.5)
    cap('00-walk-up', layout=False)
    qa.cmd('dev.assembly.open', force=True, fresh=True)
    opened = S.wait_for(lambda: qa.state() == 'Assembly' and asm().get('open'), 10, what='bench open') is not None
    ok(opened, 'the bench opens', {'state': qa.state()})
    time.sleep(2.0)
    cap('01-entry', layout=False)
    shots = (asm().get('camera') or {}).get('shots') or ['work', 'wide', 'vise', 'mat', 'parts', 'card', 'tray', 'press', 'tester', 'room']
    for name in shots:
        qa.cmd('dev.assembly.shot', shot=name); time.sleep(1.2)
        cap('shot-' + name, layout=False)
    qa.cmd('dev.assembly.shot', shot='auto'); time.sleep(.6)
    note('bench light', {'look': os.environ.get('ATHEN_BENCH_LOOK'), 'lights': (S.snap().get('lightBudget') or {})})
    qa.cmd('dev.assembly.close'); time.sleep(1.5)
    for cam in CAMS:
        qa.cmd('view', camera=cam); time.sleep(1.4)
        cap(cam, layout=False)
    qa.cmd('view', camera='follow'); time.sleep(.5)
    cap('99-after', layout=False)


S.run(body)
