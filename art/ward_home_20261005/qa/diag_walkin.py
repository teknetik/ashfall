"""Diagnostic (5 Oct 2026): trace the walk from the home door into the container with real W presses.

  uv run --offline --with python-xlib --with pillow python art/ward_home_20261005/qa/diag_walkin.py OUT
Records position, grounded, camera yaw/pitch, door state and the confine zone every 0.1 s, with captures.
"""
import json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'unity/evidence/gameplay-v2/20260930-reqa2'))
import qa  # noqa: E402

out = Path(sys.argv[1]).resolve(); out.mkdir(parents=True, exist_ok=True)
save = out / 'save'; save.mkdir(exist_ok=True)
(save / 'ward-save.json').write_text(json.dumps({
    'version': 4, 'savedUtc': '2026-10-05T05:00:00Z', 'build': 'qa', 'credits': 50, 'purchases': 0, 'sales': 0, 'items': [],
    'crafting': {'known': [], 'crafted': [], 'crafts': 0, 'fitted': []}, 'bermsStep': 'Complete', 'hasPistol': True,
    'orders': {'index': 0, 'id': 'order_steady_hands', 'testFired': [], 'reported': []},
    'city': {'visitedHill': True, 'boughtFlask': True, 'soldScrap': True, 'linked': True, 'spoken': ['npc_linn', 'npc_mira', 'npc_torr', 'npc_vex'], 'selectedDestination': '',
             'flags': ['home_asked', 'home_leased']},
    'character': {'version': 2, 'level': 2, 'experience': 0, 'attributePoints': 0, 'skillPoints': 0,
                  'equipped': [{'slot': 'storage', 'itemId': 'field_backpack'}, {'slot': 'secondary', 'itemId': 'scrap_pistol'}], 'modifications': []}}))
trace = []


def rec(tag):
    s = qa.snap(); h = s.get('home') or {}
    trace.append({'t': tag, 'pos': [round(v, 3) for v in s['player']['position']], 'grounded': s['player']['grounded'], 'yaw': round(s['camera']['yaw'], 1),
                  'pitch': round(s['camera']['pitch'], 1), 'boom': s['camera']['boom'], 'fp': s['camera']['firstPerson'], 'door': h.get('doorOpen'),
                  'zone': h.get('insideZone'), 'confined': h.get('confined')})
    print(json.dumps(trace[-1]), flush=True)


qa.launch(out / 'run', save_dir=save)
try:
    qa.wait_menu(); qa.focus(); qa.tap('Return'); qa.wait(lambda: qa.state() == 'Play', 40, what='Play'); qa.release_all()
    qa.cmd('timeSet', hour=13); qa.cmd('timePause', paused=True)
    qa.goto('home_door'); time.sleep(1.2); qa.view('follow'); qa.cmd('cameraBoom', boom=3.0); qa.yaw(180); qa.pitch(15); time.sleep(.8)
    rec('start'); qa.capture('walk-00-start', layout=False)
    for i in range(1, 31):
        qa.hold('w', .1); time.sleep(.05); rec('w%02d' % i)
        if i in (5, 10, 15, 20, 30): qa.capture('walk-%02d' % i, layout=False)
    qa.goto('home_inside'); time.sleep(.8); rec('teleport-inside'); qa.capture('inside-teleport', layout=False)
    for i in range(1, 11):
        qa.hold('s', .1); time.sleep(.05); rec('s%02d' % i)
    qa.capture('inside-back', layout=False)
finally:
    print('stop:', qa.stop())
(out / 'trace.json').write_text(json.dumps(trace, indent=1))
