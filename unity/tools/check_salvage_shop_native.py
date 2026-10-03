"""Native real-input check of the walk-in Salvage shop and the first field order's new step (1 Oct 2026).

Continues a prepared save taken just after the Outer Berms primer (servo, alloy and nanites in the pack, field order 1
at its Report stage), then with real keyboard input: walks from the porch through the open loading bay to the counter,
talks to Brann (quest opening), follows his dialogue to the workbench, fabricates and fits the stabilised grip, uses the
workbench directly, trades at his counter (parts bought, salvage sold, no supplies list), and test-fires the upgraded
pistol on the range so order 1 completes. Captures the review cameras and first-person views at 13:00 and 20:30.

  uv run --offline --with python-xlib --with pillow python unity/tools/check_salvage_shop_native.py OUT
"""
import json, math, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'unity/evidence/gameplay-v2/20260930-reqa2'))
import qa  # noqa: E402

out = Path(sys.argv[1]).resolve(); out.mkdir(parents=True, exist_ok=True)
save = out / 'save'; save.mkdir(exist_ok=True)
items = {'droid_servo_damaged': 1, 'scrap_alloy': 2, 'nanite_residue': 5, 'copper_filament': 3}
(save / 'ward-save.json').write_text(json.dumps({
    'version': 2, 'savedUtc': '2026-10-01T20:00:00Z', 'build': 'qa', 'credits': 40, 'purchases': 0, 'sales': 0,
    'items': [{'itemId': k, 'quantity': v} for k, v in items.items()],
    'crafting': {'known': ['recipe_grip_stabilised_pistol'], 'crafted': [], 'crafts': 0, 'fitted': []},
    'bermsStep': 'Complete', 'hasPistol': True, 'orders': {'index': 0, 'testFired': []},
    'city': {'visitedHill': True, 'boughtFlask': True, 'soldScrap': True, 'linked': True,
             'spoken': ['npc_linn', 'npc_mira', 'npc_torr', 'npc_vex'], 'selectedDestination': ''},
}, indent=1))

checks = []; report = {'checks': checks}


def ok(cond, what, detail=None):
    checks.append({'check': what, 'passed': bool(cond), 'detail': detail})
    print(('PASS ' if cond else 'FAIL ') + what + ('' if detail is None else ' :: ' + json.dumps(detail, default=str)[:300]), flush=True)
    return cond


def inter():
    return qa.snap()['interaction']


# shop root (-18.1, 0, 18), yaw 90: world = (-18.1 + local z, y, 18 - local x)
def W(x, z):
    return [-18.1 + z, 0.5, 18 - x]


PORCH, INSIDE, COUNTER, BENCH = W(-1.35, 2.2), W(-1.35, -1.0), W(0.55, -2.55), W(-1.3, -4.6)


def goto(landmark, at):
    qa.goto(landmark)
    qa.wait(lambda: qa.dist_xz(qa.pos(), at) < .35, 5, what='teleport to ' + landmark)
    time.sleep(.3)


qa.launch(out / 'run', save_dir=save)
try:
    qa.wait_menu(); qa.focus(); qa.tap('Return')
    qa.wait(lambda: qa.state() == 'Play', 40, what='Play after Continue')
    qa.release_all()
    qa.cmd('timeSet', hour=13); qa.cmd('timePause', paused=True)
    c = qa.craft()
    ok(c['fieldOrder'] == 0 and c['orderStage'] == 'Report', 'continued save: order 1 waits for the visit to Brann', {k: c[k] for k in ('fieldOrder', 'orderStage', 'objective')})
    ok('Brann' in (c['objective'] or ''), 'field notes send the player to Brann at Salvage', c['objective'])

    # porch -> through the open bay -> counter, on foot (real W)
    goto('salvage_shop', PORCH); qa.view('follow')
    counter = COUNTER
    qa.face(INSIDE[0], INSIDE[2]); time.sleep(.5)
    qa.capture('porch-bay', layout=False)
    qa.walk_to(INSIDE[0], INSIDE[2], tol=.5)
    qa.capture('walk-in', layout=False)
    qa.walk_to(counter[0], counter[2], tol=.45)
    ok(qa.dist_xz(qa.pos(), counter) < .6, 'walked from the porch through the bay to the counter', {'pos': qa.pos(), 'counter': counter})
    prompt = inter()['prompt']
    ok('Talk to Brann' in prompt, 'Brann offers the E prompt at the counter', prompt)

    # quest dialogue
    qa.tap('e'); qa.wait(lambda: qa.state() == 'Dialogue', 5, what='dialogue')
    i = inter()
    ok(i['npc'] == 'Brann' and i['node'] == 'report_ready', 'Brann opens with the report line', i)
    qa.capture('brann-report')
    ok(qa.craft()['orderStage'] == 'Fabricate', 'talking to Brann moves the order to fabrication', qa.craft()['objective'])
    qa.tap('Return', settle=.5); i = inter()
    ok(i['node'] == 'bench_how', '"Show me the bench." explains the workbench', i)
    qa.capture('brann-bench-how')
    qa.tap('Return', settle=.8)
    ok(qa.state() == 'Fabricator' and inter()['station'] == 'Salvage workbench', '"Use the bench." opens the Salvage workbench', inter())
    qa.capture('workbench-open')

    # fabricate and fit with Enter (the window focuses the order's part)
    qa.tap('Return', settle=.8)
    c = qa.craft(); ok(c['crafts'] >= 1 and (qa.qty('grip_stabilised_pistol') or 0) >= 1, 'Enter fabricates the stabilised grip', {'crafts': c['crafts'], 'grip': qa.qty('grip_stabilised_pistol'), 'notice': qa.snap()['session']['notice']})
    qa.tap('Return', settle=.8)
    c = qa.craft(); ok((c.get('slots') or {}).get('grip') == 'grip_stabilised_pistol', 'Enter fits it to the pistol', c.get('slots'))
    qa.capture('grip-fitted')
    qa.tap('Escape', settle=.5); ok(qa.state() == 'Play', 'Esc closes the workbench')
    c = qa.craft(); ok(c['orderStage'] == 'TestFire', 'order 1 now asks for a test fire', c['objective'])

    # the workbench by itself
    goto('salvage_bench', BENCH)
    prompt = inter()['prompt']; ok('workbench' in prompt.lower(), 'the workbench offers its own E prompt', prompt)
    qa.tap('e', settle=.6); ok(qa.state() == 'Fabricator', 'E at the bench opens the fabricator')
    qa.tap('Escape', settle=.5)

    # trade at Brann's counter: parts and salvage, no supplies
    goto('salvage_counter', COUNTER)
    qa.tap('e'); qa.wait(lambda: qa.state() == 'Dialogue', 5, what='dialogue 2')
    i = inter(); ok(i['node'] == 'steady_test', 'after fitting Brann sends the player to test it', i)
    labels = i['choices'] or []
    qa.activate('choice%d' % next(n for n, l in enumerate(labels) if l.startswith('Show me what you trade')))
    ok(qa.state() == 'Shop' and inter()['shop'] == 'Salvage', 'his counter opens as Salvage', inter())
    lay = qa.ui()
    vis = lambda n: (qa.el(lay, n) or {}).get('visible')
    ok(not vis('supplies-heading') and vis('parts-heading') and vis('salvage-heading'), 'Salvage shows parts and salvage, not supplies', {n: vis(n) for n in ('supplies-heading', 'parts-heading', 'salvage-heading')})
    ok('BRANN' in ((qa.el(lay, 'parts-heading') or {}).get('text') or ''), 'parts heading names Brann', (qa.el(lay, 'parts-heading') or {}).get('text'))
    qa.capture('brann-shop')
    a0, cr0 = qa.qty('scrap_alloy') or 0, qa.snap()['session']['credits']
    qa.activate('buy-part-scrap_alloy')
    ok((qa.qty('scrap_alloy') or 0) == a0 + 1 and qa.snap()['session']['credits'] < cr0, 'bought scrap alloy from Brann', {'alloy': qa.qty('scrap_alloy'), 'credits': qa.snap()['session']['credits']})
    f0, cr1 = qa.qty('copper_filament') or 0, qa.snap()['session']['credits']
    qa.activate('sell-salvage-copper_filament')
    ok((qa.qty('copper_filament') or 0) == f0 - 1 and qa.snap()['session']['credits'] > cr1, 'sold copper filament to Brann', {'filament': qa.qty('copper_filament'), 'credits': qa.snap()['session']['credits'], 'notice': qa.snap()['session']['notice']})
    qa.tap('Escape', settle=.5)

    # interior views (day): review cameras and on-foot first person
    for cam in ['cam_ss_bay', 'cam_ss_counter', 'cam_ss_bench', 'cam_ss_racks', 'cam_ss_brann', 'cam_ss_inside_out']:
        qa.view(cam); time.sleep(.5); qa.capture(cam + '-h13', layout=False)
    qa.view('follow'); goto('salvage_counter', COUNTER)
    qa.cmd('cameraBoom', boom=0.0); qa.face(counter[0] + 0.0, counter[2] - 3.0); qa.pitch(2); time.sleep(1)
    qa.capture('fp-counter-h13', layout=False)
    goto('salvage_bench', BENCH); qa.face(BENCH[0] - 3, BENCH[2]); qa.pitch(24); time.sleep(1)
    qa.capture('fp-bench-h13', layout=False)
    qa.cmd('cameraBoom', boom=3.0)

    # night
    qa.cmd('timeSet', hour=20.5); time.sleep(1.5)
    for cam in ['cam_ss_bay', 'cam_ss_counter', 'cam_ss_bench']:
        qa.view(cam); time.sleep(.5); qa.capture(cam + '-h20.5', layout=False)
    qa.view('cam_nf_salvage'); time.sleep(.5); qa.capture('street-salvage-h20.5', layout=False)
    tag = [e for e in qa.ui()['elements'] if (e.get('text') or '').startswith('Brann') and e.get('visible')]
    ok(not tag, "Brann's nametag does not show through the shop wall from the street", tag[:1])
    qa.cmd('timeSet', hour=13); time.sleep(1)
    qa.view('cam_rollout_salvage_front'); time.sleep(.5); qa.capture('street-salvage-h13', layout=False)
    qa.view('follow')

    # test fire on the range completes order 1
    qa.goto('checkpoint_firingline'); time.sleep(.8)
    qa.focus(); qa.tap('7', settle=.8)
    ok(qa.snap()['combat']['Armed'], 'pistol drawn in the Berms')
    qa.view('cam_checkpoint_plate1'); time.sleep(.3)
    qa.tap('f', secs=.05, settle=1.2)
    qa.wait(lambda: qa.craft()['fieldOrder'] == 1, 8, what='order 1 complete')
    c = qa.craft(); ok(c['fieldOrder'] == 1, 'test fire completes Steady Hands; order 2 begins', {k: c[k] for k in ('fieldOrder', 'orderStage', 'objective')})
    time.sleep(1.5); s = qa.snap()['session']
    report['radio'] = [s.get('radio'), s.get('radioSpeaker')]
    qa.view('follow')
    report['errors'] = qa.log_errors()
    ok(not report['errors'], 'no exceptions in Player.log', report['errors'][:3])
finally:
    print('stop:', qa.stop())
saved = json.loads((save / 'ward-save.json').read_text())
report['savedOrders'] = saved.get('orders'); report['savedFlags'] = (saved.get('city') or {}).get('flags')
ok((saved.get('orders') or {}).get('index') == 1 and (saved.get('orders') or {}).get('id', 'order_kit_helmet') == 'order_kit_helmet' and 'order_steady_hands' in ((saved.get('orders') or {}).get('reported') or []), 'the save records order 2 (Warden Kit: Helm since 3 Oct 2026) and the report visit', saved.get('orders'))
report['passed'] = all(c['passed'] for c in checks)
(out / 'report.json').write_text(json.dumps(report, indent=1, default=str))
print('PASSED' if report['passed'] else 'FAILED', sum(c['passed'] for c in checks), '/', len(checks))
sys.exit(0 if report['passed'] else 1)
