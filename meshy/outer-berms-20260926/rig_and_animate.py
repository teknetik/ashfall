#!/usr/bin/env python3
"""Meshy auto-rig + library animations for the Outer Berms worker droid.
Key comes only from MESHY_API_KEY in the environment; task records (no secrets) go to worker-droid/rig.json."""
import json, os, sys, time, urllib.request
from pathlib import Path
KEY = os.environ.get('MESHY_API_KEY') or sys.exit('MESHY_API_KEY is required in the environment')
API = 'https://api.meshy.ai/openapi/v1'
OUT = Path(__file__).parent / 'worker-droid'
# Meshy animation library action ids (GET /openapi/v1/animations/library, 26 Sep 2026)
ACTIONS = {'idle': 89, 'attack': 214, 'hit': 178, 'death': 187}


def call(method, url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, method=method,
                                 headers={'Authorization': f'Bearer {KEY}', 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=120) as r: return json.loads(r.read())


def wait(kind, tid):
    while True:
        t = call('GET', f'{API}/{kind}/{tid}')
        print(kind, tid[:8], t['status'], t.get('progress'), flush=True)
        if t['status'] == 'SUCCEEDED': return t
        if t['status'] in ('FAILED', 'CANCELED', 'EXPIRED'): sys.exit(f'{kind} {t["status"]}: {t.get("task_error")}')
        time.sleep(10)


def fetch(url, name): (OUT / name).write_bytes(urllib.request.urlopen(url, timeout=300).read())


rec = json.loads((OUT / 'rig.json').read_text()) if (OUT / 'rig.json').exists() else {}
src = json.loads((OUT / 'task.json').read_text())
if 'rig_task' not in rec:
    rec.update(source_refine_task=src['refine_task'], height_meters=1.9, actions=ACTIONS)
    rec['rig_task'] = call('POST', f'{API}/rigging', dict(input_task_id=src['refine_task'], height_meters=1.9))['result']
    (OUT / 'rig.json').write_text(json.dumps(rec, indent=2))
rig = wait('rigging', rec['rig_task'])
rec['rig_credits'] = rig.get('consumed_credits')
res = rig['result']
fetch(res['rigged_character_glb_url'], 'rigged.glb')
fetch(res['basic_animations']['walking_glb_url'], 'anim-walk.glb')
fetch(res['basic_animations']['running_glb_url'], 'anim-run.glb')
rec.setdefault('animation_tasks', {})
for name, aid in ACTIONS.items():
    if name not in rec['animation_tasks']:
        rec['animation_tasks'][name] = call('POST', f'{API}/animations', dict(rig_task_id=rec['rig_task'], action_id=aid, post_process=dict(operation_type='change_fps', fps=30)))['result']
        (OUT / 'rig.json').write_text(json.dumps(rec, indent=2))
for name, tid in rec['animation_tasks'].items():
    a = wait('animations', tid)
    rec.setdefault('animation_credits', {})[name] = a.get('consumed_credits')
    fetch(a['result']['animation_glb_url'], f'anim-{name}.glb')
rec['finished'] = time.strftime('%Y-%m-%dT%H:%M:%S'); rec['status'] = 'SUCCEEDED'
(OUT / 'rig.json').write_text(json.dumps(rec, indent=2)); print('DONE')
